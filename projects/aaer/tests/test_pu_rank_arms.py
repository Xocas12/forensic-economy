"""Which PU estimators can be an arm of the rank comparison, and what a gap between arms measures.

Sub-question 3 compares positive-unlabeled estimators with the treat-unflagged-as-clean (naive)
arm on rank metrics. An estimator whose score is a monotone transform of a naive classifier's
score can only tie with the naive arm there, or lose by whatever data it held out, so it does
not belong in that comparison. ``aaer.analysis.pu_benchmark`` says which estimators are arms and
which are not, and what a gap between the bagging arm and a naive arm does and does not
measure. These tests check both on a synthetic panel built in this file. No acquired data is
used anywhere here.

Rankings are compared with measures that do not depend on row order among tied scores. A
shallow tree scores 2,000 rows with a handful of distinct values, so a measure that broke ties
by row order would report as a difference what is only the order the rows happen to be in.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from aaer.analysis import pu_benchmark
from forensics_core.eval.harness import DETECTOR_REGISTRY, Dataset, make_detector
from scipy.stats import kendalltau
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.ensemble import BaggingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

#: Firm-years in the synthetic panel; the first half is fitted on, the second half ranked.
N_ROWS = 4000

#: Rounds in every bagged arm here, PU or not: BaggingPU's default.
N_ROUNDS = 50

LINEAR_BASE = LogisticRegression(max_iter=1000)

#: Bases whose fit moves a lot from one sample to the next, so that the mean of many fits is a
#: different model from one fit.
UNSTABLE_BASES = {
    "tree_depth3": DecisionTreeClassifier(max_depth=3, random_state=0),
    "tree_depth4": DecisionTreeClassifier(max_depth=4, random_state=0),
}

#: Bases whose fit moves little, so that the mean of many fits ranks much as one fit does.
#: Naive Bayes is here because it is not linear in the features: what decides whether bagging
#: moves the ranking is the base's instability, not its linearity.
STABLE_BASES = {"logistic": LINEAR_BASE, "naive_bayes": GaussianNB()}

#: Kendall's tau-b against the naive arm below which a ranking counts as different.
DIFFERENT_BELOW = 0.8
#: Kendall's tau-b against the naive arm above which a ranking counts as close to it.
CLOSE_ABOVE = 0.9


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
    """Scores on ``test`` of PU estimator ``name`` and of a single-model naive arm on ``base``.

    The naive arm is one fit of ``base`` on the rows the PU estimator fitted its own classifier
    on: all of ``train``, less any rows the estimator held out of that fit (Elkan-Noto holds out
    a share of both groups to estimate ``c``). With the rows held fixed, a difference in ranking
    comes from the estimator, not from one arm having seen less data than the other.
    """
    arm = make_detector(name, base_estimator=base, random_state=0).fit(train)
    keep = np.ones(len(train), dtype=bool)
    for attribute in ("hold_out_indices_", "hold_out_unlabeled_indices_"):
        keep[np.asarray(getattr(arm.estimator_, attribute, []), dtype=int)] = False
    naive = make_detector("sklearn", estimator=base).fit(train.take(np.flatnonzero(keep)))
    return arm.score(test), naive.score(test)


class _NaiveBalancedBagging(BaseEstimator, ClassifierMixin):
    """Balanced bagging of ``base`` as an ordinary classifier: every 0 is taken as a negative.

    Each round fits ``base`` on every row labelled 1 against as many rows drawn, with
    replacement, from the rows labelled 0, and a row's score is the mean of the rounds' scores
    (``decision_function`` where the base has one, else the probability of class 1). The draws
    are made as ``BaggingPU`` makes them at the pinned forensics-core: one
    ``numpy.random.default_rng(random_state)``, one ``integers(0, n_zeros, size=n_ones)`` per
    round. Nothing in this class knows that the 0s are unlabeled rather than clean.
    """

    def __init__(self, base=None, n_estimators: int = N_ROUNDS, random_state: int = 0) -> None:
        self.base = base
        self.n_estimators = n_estimators
        self.random_state = random_state

    def fit(self, X, y) -> _NaiveBalancedBagging:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y).astype(int)
        ones, zeros = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
        round_labels = np.repeat(np.array([1, 0], dtype=np.int64), ones.size)
        rng = np.random.default_rng(self.random_state)
        self.estimators_ = []
        for _ in range(self.n_estimators):
            drawn = zeros[rng.integers(0, zeros.size, size=ones.size)]
            rows = np.vstack([X[ones], X[drawn]])
            self.estimators_.append(clone(self.base).fit(rows, round_labels))
        self.classes_ = np.array([0, 1])
        return self

    def decision_function(self, X) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        total = np.zeros(X.shape[0])
        for estimator in self.estimators_:
            if hasattr(estimator, "decision_function"):
                total += estimator.decision_function(X)
            else:
                total += estimator.predict_proba(X)[:, 1]
        return total / len(self.estimators_)


def _tau_b(a: np.ndarray, b: np.ndarray) -> float:
    """Kendall's tau-b: a pair tied in either ranking counts as neither agreeing nor not."""
    return float(kendalltau(a, b).statistic)


def _share_of_top_outside_naive_top(arm: np.ndarray, naive: np.ndarray) -> float:
    """Share of the arm's top 1 per cent that the naive arm ranks below its own top 1 per cent.

    A row counts as outside only when the naive arm scores it strictly below the naive arm's
    k-th highest score, and the arm's top takes in every row tied with the arm's own k-th
    score, so the answer does not depend on how either arm's ties fall in row order. One per
    cent is the cut-off of the published benchmark's NDCG@k and of precision@k here.
    """
    k = max(1, round(0.01 * arm.size))
    arm_top = arm >= np.sort(arm)[::-1][k - 1]
    naive_kth = np.sort(naive)[::-1][k - 1]
    return float(np.mean(naive[arm_top] < naive_kth))


@pytest.mark.parametrize(
    "base", [LINEAR_BASE, *UNSTABLE_BASES.values()], ids=["linear", *UNSTABLE_BASES]
)
def test_elkan_noto_ranks_as_the_naive_arm_so_it_is_not_an_arm(panel, base):
    train, test = panel
    pu, naive = _arm_and_naive_scores("pu_elkan_noto", base, train, test)

    # g(x)/c_ with one positive c_: the same order as the naive classifier, to the last row.
    assert _tau_b(pu, naive) == pytest.approx(1.0, abs=1e-12)
    assert _share_of_top_outside_naive_top(pu, naive) == 0.0

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


@pytest.mark.parametrize(
    "base", [LINEAR_BASE, *UNSTABLE_BASES.values()], ids=["linear", *UNSTABLE_BASES]
)
def test_on_scored_rows_the_bagging_arm_is_a_naive_arm_bagged_the_same_way(panel, base):
    """Bagging PU's label treatment on the rows it scores is the naive one.

    ``PUDetector`` scores held-out rows with the plain mean over rounds, and every round is
    an ordinary classifier of the charged rows against a draw of uncharged rows coded 0. The
    out-of-bag scoring that makes the method PU applies to training rows only. So a naive arm
    that is bagged the same way, built here without any PU code, gives the same scores.
    """
    train, test = panel
    pu = make_detector("pu_bagging", base_estimator=base, random_state=0).fit(train)
    bagged_naive = make_detector(
        "sklearn", estimator=_NaiveBalancedBagging(base, random_state=0)
    ).fit(train)

    pu_scores, naive_scores = pu.score(test), bagged_naive.score(test)
    np.testing.assert_allclose(pu_scores, naive_scores, rtol=0.0, atol=1e-12)
    assert _tau_b(pu_scores, naive_scores) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("base_id", sorted(UNSTABLE_BASES))
@pytest.mark.parametrize("name", pu_benchmark.PU_ESTIMATORS)
def test_each_rank_arm_ranks_a_non_scar_panel_differently_from_a_single_model_naive_arm(
    panel, name, base_id
):
    """Each PU arm is not a monotone transform of one naive fit of the same base.

    This does not show a PU effect: the next test gets the same kind of gap from bagging with
    no PU in it, and the one before gets no gap at all from a naive arm bagged the same way.
    """
    train, test = panel
    pu, naive = _arm_and_naive_scores(name, UNSTABLE_BASES[base_id], train, test)

    tau = _tau_b(pu, naive)
    assert tau < DIFFERENT_BELOW, f"{name} with {base_id} ranks close to the naive arm ({tau=:.4f})"


@pytest.mark.parametrize("base_id", sorted(UNSTABLE_BASES))
def test_plain_bagging_with_no_pu_also_ranks_differently_from_a_single_model(panel, base_id):
    """The gap in the previous test comes from ensembling, and needs no PU to appear.

    ``sklearn``'s ``BaggingClassifier`` fits the base on bootstrap samples of all the rows,
    with every uncharged row a negative and no rebalancing, and it clears the same bound.
    """
    train, test = panel
    base = UNSTABLE_BASES[base_id]
    ensemble = BaggingClassifier(clone(base), n_estimators=N_ROUNDS, random_state=0)
    bagged = make_detector("sklearn", estimator=ensemble).fit(train).score(test)
    naive = make_detector("sklearn", estimator=base).fit(train).score(test)

    tau = _tau_b(bagged, naive)
    assert tau < DIFFERENT_BELOW, f"plain bagging of {base_id} ranks close to one fit ({tau=:.4f})"


@pytest.mark.parametrize("base_id", sorted(STABLE_BASES))
def test_with_a_stable_base_the_bagging_arm_stays_close_to_a_single_model(panel, base_id):
    """Whether bagging PU moves the ranking depends on the base's instability.

    Logistic regression and naive Bayes change little from one sample to the next, so the mean
    of many fits ranks much as one fit does. Naive Bayes is not linear in the features, so
    linearity is not what decides it.
    """
    train, test = panel
    pu, naive = _arm_and_naive_scores("pu_bagging", STABLE_BASES[base_id], train, test)

    tau = _tau_b(pu, naive)
    assert tau > CLOSE_ABOVE, f"bagging PU on {base_id} moved the ranking ({tau=:.4f})"
