"""How this project codes ``Dataset.y``, and what the shared harness can measure on that coding.

``docs/data_dictionary.md`` section 6 codes a charged firm-year 1, a firm-year nobody charged 0
(the harness's "presumed clean") and keeps ``NaN`` for firm-years whose status cannot be known
yet. The two ``build_dataset`` contracts say the same. The builders are stubs (CONTRACT rule 4),
so the harness half of this file runs on a synthetic panel coded from section 6's own table:
if the table is changed to a coding the harness cannot score, these tests fail with the
harness's error. No acquired data is read anywhere here.
"""

from __future__ import annotations

import inspect
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from aaer.analysis import beneish_baseline, earnings_bunching, pu_benchmark
from forensics_core.eval.harness import (
    Dataset,
    EvalSpec,
    FunctionDetector,
    SklearnDetector,
    evaluate,
    make_detector,
    transfer,
)
from sklearn.linear_model import LogisticRegression

_DATA_DICTIONARY = Path(__file__).resolve().parents[1] / "docs" / "data_dictionary.md"

#: Synthetic panel: fiscal years, the last temporal training year, and how many of the latest
#: years sit inside the enforcement-lag horizon (unflagged rows there cannot be known yet).
_YEARS = tuple(range(1996, 2008))
_TRAIN_END = 2001
_HORIZON = 2

#: Constructor arguments per PU estimator: one base classifier for every arm, so the arms
#: differ only in how they read the labels, and few bagging rounds to keep the test quick.
_PU_KWARGS = {
    "pu_elkan_noto": {"random_state": 0},
    "pu_bagging": {"random_state": 0, "n_estimators": 10},
}


def _flat(text: str) -> str:
    return " ".join(text.split())


def _section_6() -> str:
    text = _DATA_DICTIONARY.read_text(encoding="utf-8")
    start = text.index("## 6.")
    return text[start : text.index("## 7.", start)]


def _documented_coding() -> dict[str, float]:
    """The ``y`` that section 6's coding table gives each kind of firm-year."""
    rows: dict[str, float] = {}
    for line in _section_6().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[1].strip("`") not in {"1", "0", "NaN"}:
            continue
        rows[cells[0]] = float(cells[1].strip("`"))
    kinds = {
        "charged": [value for row, value in rows.items() if row.startswith("charged")],
        "uncharged": [value for row, value in rows.items() if row.startswith("nobody charged")],
        "unknowable": [value for row, value in rows.items() if "cannot be known" in row],
    }
    for kind, values in kinds.items():
        assert len(values) == 1, (
            f"data_dictionary.md section 6 should have exactly one coding-table row for "
            f"{kind} firm-years; found {len(values)}"
        )
    return {kind: values[0] for kind, values in kinds.items()}


def _firm_years(coding: dict[str, float], *, n_firms: int = 150, seed: int = 0) -> Dataset:
    """A synthetic firm-year panel with ``y`` coded as ``coding`` says.

    One feature carries the signal. Charged firm-years are drawn from it at a rate of a few per
    cent; an uncharged firm-year inside the last ``_HORIZON`` years gets the "cannot be known
    yet" code, every other uncharged firm-year the "nobody charged" code.
    """
    rng = np.random.default_rng(seed)
    firm = np.repeat(np.arange(n_firms), len(_YEARS))
    year = np.tile(np.asarray(_YEARS), n_firms)
    signal = rng.normal(size=firm.size)
    X = pd.DataFrame({"signal": signal, "noise": rng.normal(size=firm.size)})
    charged = rng.random(firm.size) < 1.0 / (1.0 + np.exp(4.0 - 1.5 * signal))
    knowable = year <= max(_YEARS) - _HORIZON
    y = np.where(
        charged,
        coding["charged"],
        np.where(knowable, coding["uncharged"], coding["unknowable"]),
    )
    return Dataset(
        unit_id=pd.Series([f"firm{f}-{t}" for f, t in zip(firm, year, strict=True)]),
        X=X,
        y=pd.Series(y),
        groups=pd.Series(firm),
        time=pd.Series(year),
        meta={"name": "synthetic aaer firm-years", "project": "aaer"},
    )


def _target() -> Dataset:
    """An unlabelled synthetic panel with the same columns, standing in for another project."""
    rng = np.random.default_rng(1)
    X = pd.DataFrame({"signal": rng.normal(size=300), "noise": rng.normal(size=300)})
    return Dataset(
        unit_id=pd.Series([f"unit{i}" for i in range(300)]), X=X, meta={"name": "target"}
    )


def _logit() -> LogisticRegression:
    return LogisticRegression(max_iter=1000)


def _arms() -> dict[str, object]:
    """Every detector the two dataset contracts feed: the PU estimators the benchmark runs,
    the naive arm on the same base classifier, and an unsupervised score as the Beneish
    baseline would be wrapped."""
    arms: dict[str, object] = {
        name: make_detector(name, base_estimator=_logit(), **_PU_KWARGS[name])
        for name in pu_benchmark.PU_ESTIMATORS
    }
    arms["naive"] = SklearnDetector(_logit(), name="naive")
    arms["unsupervised"] = FunctionDetector(lambda X: X["signal"].to_numpy(), name="m_score")
    return arms


def _spec(split: str) -> EvalSpec:
    return EvalSpec(split=split, train_end=_TRAIN_END, n_splits=5, ks=(0.01, 0.05))


def test_section_6_codes_charged_1_uncharged_0_and_keeps_nan_for_unknowable_status():
    coding = _documented_coding()
    assert coding["charged"] == 1.0
    assert coding["uncharged"] == 0.0, "an uncharged firm-year must be coded 0, presumed clean"
    assert math.isnan(coding["unknowable"])
    assert "encode unlabeled rows as `NaN`, not 0" not in _flat(_section_6())


@pytest.mark.parametrize(
    "contract",
    [
        beneish_baseline.build_dataset,
        pu_benchmark.build_dataset,
        earnings_bunching.bunching_by_label,
    ],
    ids=lambda fn: f"{fn.__module__.rsplit('.', 1)[-1]}.{fn.__name__}",
)
def test_every_label_contract_codes_uncharged_firm_years_0_and_reserves_nan(contract):
    doc = _flat(inspect.getdoc(contract) or "")
    assert "not 0" not in doc, "the contract still says uncharged firm-years are NaN, not 0"
    assert re.search(r"\b0 (for|on) (firm-years|one) nobody charged\b", doc), (
        "the contract should code a firm-year nobody charged as 0"
    )
    assert "cannot be known yet" in doc, "NaN should be reserved for status not yet knowable"
    assert "data_dictionary.md`` section 6" in doc


@pytest.mark.parametrize("split", ["temporal", "group_kfold"])
def test_evaluate_scores_every_arm_on_the_same_rows_of_the_documented_coding(split):
    ds = _firm_years(_documented_coding())
    spec = _spec(split)
    reports = {name: evaluate(detector, ds, spec) for name, detector in _arms().items()}

    y = ds.y_values()
    in_test = (ds.time > _TRAIN_END).to_numpy() if split == "temporal" else np.ones(len(ds), bool)
    labelled = ~np.isnan(y)
    expected = set(ds.unit_id[in_test & labelled])
    assert (y[in_test & labelled] == 0.0).sum() > 0, "the uncharged rows should be evaluated"
    assert (in_test & ~labelled).sum() > 0, "the panel should have rows of unknowable status"

    for name, report in reports.items():
        assert not any(fold["skipped"] for fold in report.per_fold), name
        for metric in ("roc_auc", "average_precision", "ndcg@1%", "precision@1%"):
            assert math.isfinite(report.metrics[metric]), (name, metric)
        evaluated = [unit for fold in report.per_fold for unit in fold["test_unit_ids"]]
        assert set(evaluated) == expected, f"{name} was not scored on the labelled test rows"

    folds = {name: [fold["test_unit_ids"] for fold in r.per_fold] for name, r in reports.items()}
    first = folds["naive"]
    for name, rows in folds.items():
        assert rows == first, f"{name} was scored on different rows from the naive arm"


@pytest.mark.parametrize("arm", ["pu_elkan_noto", "naive"])
def test_transfer_calibrates_on_the_charged_and_the_uncharged_source_rows(arm):
    ds = _firm_years(_documented_coding())
    result = transfer(_arms()[arm], ds, _target(), source_spec=_spec("temporal"))

    labelled = ds.labeled()
    base_rate = float(np.mean(labelled.y_values() == 1.0))
    curve = result.calibration
    assert int(curve["n_selected"].max()) == len(labelled)
    assert curve["precision"].iloc[0] == pytest.approx(base_rate)
    assert curve["precision"].min() < 1.0
    assert result.source_report is not None
    assert math.isfinite(result.source_report.metrics["roc_auc"])


def test_coding_every_uncharged_firm_year_nan_leaves_the_harness_nothing_to_measure():
    """The reason section 6 gives for the 0, checked against the pinned harness."""
    ds = _firm_years({"charged": 1.0, "uncharged": float("nan"), "unknowable": float("nan")})
    arms = _arms()
    spec = _spec("temporal")
    for name in (*pu_benchmark.PU_ESTIMATORS, "unsupervised"):
        with pytest.raises(ValueError, match="no fold had both a positive and a negative"):
            evaluate(arms[name], ds, spec)
    with pytest.raises(ValueError, match="needs both classes"):
        evaluate(arms["naive"], ds, spec)
    result = transfer(arms["pu_elkan_noto"], ds, _target())
    assert (result.calibration["precision"] == 1.0).all()
