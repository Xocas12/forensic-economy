"""Which PU estimators can be an arm of the rank comparison against the naive arm.

Sub-question 3 compares positive-unlabeled estimators with the treat-unflagged-as-clean (naive)
arm on rank metrics. An estimator whose score is a monotone transform of a naive classifier's
score can only tie with the naive arm there, or lose by whatever data it held out, so it does
not belong in that comparison. ``aaer.analysis.pu_benchmark`` says which estimators are arms and
which are not; these tests check both halves of that on a synthetic panel built in this file.
No acquired data is used anywhere here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from aaer.analysis import pu_benchmark
from forensics_core.eval.harness import DETECTOR_REGISTRY, Dataset, make_detector
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

#: Firm-years in the synthetic panel; the first half is fitted on, the second half ranked.
N_ROWS = 4000

LINEAR_BASE = LogisticRegression(max_iter=1000)
NONLINEAR_BASES = {
    "tree_depth3": DecisionTreeClassifier(max_depth=3, random_state=0),
    "tree_depth4": DecisionTreeClassifier(max_depth=4, random_state=0),
}


def _non_scar_panel(seed: int = 0) -> tuple[Dataset, Dataset]:
    """Synthetic firm-years in which whether a misstatement is charged depends on firm size.

    ``size`` has no effect on misstating and a large one on being charged, so the charged
    firm-years are not a random draw from the misstated ones: labelling is not "selected
    completely at random", which is the situation ``docs/known_traps.md`` trap 1 describes.
    ``y`` is 1 on charged firm-years and 0 on every other one. The naive arm reads that 0 as a
    negative; ``PUDetector`` reads it as unlabeled.
    """
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(N_ROWS, 4))
    size = X[:, 0]
    logit_misstated = -3.2 + X[:, 1] + 0.8 * X[:, 2] - 0.5 * X[:, 3] + 0.4 * X[:, 1] * X[:, 2]
    misstated = rng.random(N_ROWS) < 1.0 / (1.0 + np.exp(-logit_misstated))
    p_charged = 1.0 / (1.0 + np.exp(-(-1.8 + 1.6 * size)))
    charged = misstated & (rng.random(N_ROWS) < p_charged)

    # The panel is only a fair test if the selection really depends on the firm.
    big = size > 0
    rate_big = charged[misstated & big].mean()
    rate_small = charged[misstated & ~big].mean()
    assert rate_big > 3 * rate_small, (rate_big, rate_small)

    def part(rows: np.ndarray) -> Dataset:
        frame = pd.DataFrame(X[rows], columns=["size", "x1", "x2", "x3"])
        return Dataset(
            unit_id=np.arange(rows.size),
            X=frame,
            y=pd.Series(charged[rows].astype(float), index=frame.index),
            meta={"name": "synthetic non-SCAR panel"},
        )

    half = N_ROWS // 2
    return part(np.arange(half)), part(np.arange(half, N_ROWS))


@pytest.fixture(scope="module")
def panel() -> tuple[Dataset, Dataset]:
    return _non_scar_panel()


def _arm_and_naive_scores(
    name: str, base, train: Dataset, test: Dataset
) -> tuple[np.ndarray, np.ndarray]:
    """Scores on ``test`` of PU estimator ``name`` and of the naive arm, both built on ``base``.

    The naive arm is fitted on the rows the PU estimator fitted its own classifier on: all of
    ``train``, less any rows the estimator held out of that fit (Elkan-Noto holds out a share
    of both groups to estimate ``c``). With the rows held fixed, a difference in ranking comes
    from the estimator, not from one arm having seen less data than the other.
    """
    arm = make_detector(name, base_estimator=base, random_state=0).fit(train)
    keep = np.ones(len(train), dtype=bool)
    for attribute in ("hold_out_indices_", "hold_out_unlabeled_indices_"):
        keep[np.asarray(getattr(arm.estimator_, attribute, []), dtype=int)] = False
    naive = make_detector("sklearn", estimator=base).fit(train.take(np.flatnonzero(keep)))
    return arm.score(test), naive.score(test)


def _share_of_top_in_common(a: np.ndarray, b: np.ndarray, fraction: float = 0.01) -> float:
    """Share of the top ``fraction`` of rows by ``a`` that are also in the top by ``b``.

    One per cent is the cut-off of the published benchmark's NDCG@k and of precision@k here.
    """
    k = max(1, round(fraction * a.size))
    top_a = set(np.argsort(-a, kind="stable")[:k].tolist())
    top_b = set(np.argsort(-b, kind="stable")[:k].tolist())
    return len(top_a & top_b) / k


@pytest.mark.parametrize(
    "base", [LINEAR_BASE, *NONLINEAR_BASES.values()], ids=["linear", *NONLINEAR_BASES]
)
def test_elkan_noto_ranks_as_the_naive_arm_so_it_is_not_an_arm(panel, base):
    train, test = panel
    pu, naive = _arm_and_naive_scores("pu_elkan_noto", base, train, test)

    # g(x)/c_ with one positive c_: the same order as the naive classifier, to the last row.
    assert spearmanr(pu, naive).statistic == pytest.approx(1.0, abs=1e-12)
    assert _share_of_top_in_common(pu, naive) == 1.0

    assert "pu_elkan_noto" not in pu_benchmark.PU_ESTIMATORS
    assert "pu_elkan_noto" in pu_benchmark.RANK_EQUIVALENT_TO_NAIVE


def test_the_rank_arms_and_the_rank_equivalent_estimators_are_declared_apart():
    assert pu_benchmark.PU_ESTIMATORS, "the comparison needs at least one PU arm"
    assert set(pu_benchmark.PU_ESTIMATORS).isdisjoint(pu_benchmark.RANK_EQUIVALENT_TO_NAIVE)
    for name in pu_benchmark.RANK_EQUIVALENT_TO_NAIVE:
        assert name in DETECTOR_REGISTRY
    # Elkan-Noto stays, for the one quantity where its constant is the point.
    assert pu_benchmark.CLASS_PRIOR_ESTIMATOR == "pu_elkan_noto"
    assert pu_benchmark.CLASS_PRIOR_ESTIMATOR in DETECTOR_REGISTRY


@pytest.mark.parametrize("base_id", sorted(NONLINEAR_BASES))
@pytest.mark.parametrize("name", pu_benchmark.PU_ESTIMATORS)
def test_each_rank_arm_ranks_a_non_scar_panel_differently_from_the_naive_arm(panel, name, base_id):
    train, test = panel
    pu, naive = _arm_and_naive_scores(name, NONLINEAR_BASES[base_id], train, test)

    rho = spearmanr(pu, naive).statistic
    assert rho < 0.9, f"{name} with {base_id} ranks almost as the naive arm does (rho={rho:.4f})"
    in_common = _share_of_top_in_common(pu, naive)
    assert in_common <= 0.5, f"{name} with {base_id} shares {in_common:.0%} of the top 1 per cent"


def test_with_a_linear_base_the_bagging_arm_stays_close_to_the_naive_arm(panel):
    """Why ``naive_supervised_report`` asks for a nonlinear shared base.

    Rebalancing a linear model mostly moves its intercept, and an average of linear scores is
    linear again, so with a linear base the bagging arm is nearly a copy of the naive arm.
    """
    train, test = panel
    pu, naive = _arm_and_naive_scores("pu_bagging", LINEAR_BASE, train, test)

    assert spearmanr(pu, naive).statistic > 0.97
    assert _share_of_top_in_common(pu, naive) >= 0.6
