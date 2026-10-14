"""The transfer check's evaluation path returns the anchor's rank on a synthetic panel.

Everything here is synthetic: invented republics, sectors and years, with a planted anchor
whose feature is shifted upward. No row resembles the held-out series, and nothing reads
``data/``. The path is the one ``gosplan.analysis.transfer`` prescribes: fit on a labelled
source project with :func:`forensics_core.eval.harness.transfer`, score the full target
panel, read each anchor row's rank against every non-anchor row with
:func:`gosplan.anchor_rank.anchor_rank`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from forensics_core.eval.harness import Dataset, EvalSpec, FunctionDetector, evaluate, transfer
from gosplan.anchor_rank import COMPARATOR_SET, anchor_rank

PROJECT_DIR = Path(__file__).resolve().parents[1]


def _synthetic_target(shift: float = 6.0, seed: int = 0):
    """4 republics x 3 sectors x 20 years = 240 rows; 6 anchor rows, feature shifted up."""
    rows = [
        (f"rep_{r}", f"sector_{s}", year)
        for r in "abcd"
        for s in "xyz"
        for year in range(1970, 1990)
    ]
    frame = pd.DataFrame(rows, columns=["republic", "sector", "year"])
    rng = np.random.default_rng(seed)
    frame["x"] = rng.normal(size=len(frame))
    anchor = (
        (frame["republic"] == "rep_a")
        & (frame["sector"] == "sector_x")
        & frame["year"].between(1978, 1983)
    )
    frame.loc[anchor, "x"] += shift
    unit_id = frame["republic"] + ":" + frame["sector"] + ":" + frame["year"].astype(str)
    # gosplan's panel is unlabelled outside the anchor: y is NaN there, never a presumed 0.
    y = pd.Series(np.where(anchor, 1.0, np.nan))
    ds = Dataset(unit_id=unit_id, X=frame[["x"]], y=y, meta={"name": "synthetic_gosplan"})
    return ds, anchor


def _synthetic_source(seed: int = 1) -> Dataset:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=300)
    y = (x + rng.normal(scale=0.5, size=300) > 1.0).astype(float)
    return Dataset(
        unit_id=pd.Series([f"src_{i}" for i in range(300)]),
        X=pd.DataFrame({"x": x}),
        y=pd.Series(y),
        meta={"name": "synthetic_source"},
    )


def _detector() -> FunctionDetector:
    return FunctionDetector(lambda X: X["x"].to_numpy(), "synthetic_x")


def test_the_anchor_holdout_split_cannot_rank_an_anchor_only_mask():
    """Why the path does not go through EvalSpec(split='anchor_holdout')."""
    target, anchor = _synthetic_target()
    spec = EvalSpec(split="anchor_holdout", anchor_mask=anchor, ks=(0.01, 0.05, 0.10))
    with pytest.raises(ValueError, match="no fold had both a positive and a negative"):
        evaluate(_detector(), target, spec)


def test_the_prescribed_path_returns_the_planted_anchors_rank_against_the_full_panel():
    target, anchor = _synthetic_target()
    result = transfer(_detector(), _synthetic_source(), target)
    table = anchor_rank(result.scores, target.unit_id[anchor], top_k=0.05)

    assert COMPARATOR_SET == "every non-anchor row of the full panel"
    assert len(table) == 6
    assert set(table["unit_id"]) == set(target.unit_id[anchor])
    assert (table["n_comparators"] == 240 - 6).all()
    assert (table["top_k_cutoff"] == 12).all()

    # Recompute each rank independently from the raw target scores.
    scores = dict(zip(result.scores["unit_id"], result.scores["score"], strict=True))
    comparators = np.array([scores[u] for u in target.unit_id[~anchor]])
    for _, row in table.iterrows():
        assert row["rank"] == 1 + int(np.sum(comparators >= scores[row["unit_id"]]))

    # The +6 shift puts the planted anchor at the top of the panel.
    assert table["rank"].iloc[0] == 1
    assert table["in_top_k"].all()


def test_an_unshifted_anchor_is_not_reported_at_the_top():
    """The rank moves with the data; it is not 1 by construction."""
    target, anchor = _synthetic_target(shift=0.0)
    result = transfer(_detector(), _synthetic_source(), target)
    table = anchor_rank(result.scores, target.unit_id[anchor])
    assert table["rank"].max() > table["top_k_cutoff"].iloc[0]


def test_anchor_rows_do_not_push_each_other_down_and_ties_count_against_the_anchor():
    scores = pd.DataFrame(
        {"unit_id": ["a1", "a2", "c1", "c2", "c3"], "score": [9.0, 8.0, 8.0, 1.0, 0.0]}
    )
    table = anchor_rank(scores, ["a1", "a2"], top_k=0.2)
    assert table["unit_id"].tolist() == ["a1", "a2"]
    assert table["rank"].tolist() == [1, 2]
    assert table["n_comparators_at_or_above"].tolist() == [0, 1]
    assert table["in_top_k"].tolist() == [True, False]


@pytest.mark.parametrize(
    ("anchor_units", "message"),
    [
        ([], "no anchor units"),
        (["zz"], "not in scores"),
        (["a", "b"], "nothing to rank against"),
    ],
)
def test_anchor_rank_refuses_a_set_it_cannot_rank(anchor_units, message):
    scores = pd.DataFrame({"unit_id": ["a", "b"], "score": [1.0, 0.0]})
    with pytest.raises(ValueError, match=message):
        anchor_rank(scores, anchor_units)


def test_no_project_doc_prescribes_the_anchor_only_holdout():
    """HELD_OUT.md and validation_anchors.md name the full-panel rank, not anchor_holdout."""
    held_out = (PROJECT_DIR / "docs" / "HELD_OUT.md").read_text(encoding="utf-8")
    anchors = (PROJECT_DIR / "docs" / "validation_anchors.md").read_text(encoding="utf-8")
    assert "to build the `anchor_holdout` split" not in held_out
    assert "gosplan.anchor_rank.anchor_rank" in held_out
    flat = " ".join(anchors.split())
    assert "the comparator set is every non-anchor row of the full panel" in flat
