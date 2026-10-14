"""Positive-unlabeled benchmark against the treat-unflagged-as-clean formulation. STUBS ONLY.

Methods
-------
Elkan, C. and K. Noto (2008). "Learning classifiers from only positive and unlabeled data."
*KDD*: the constant-``c`` correction, ``P(y=1|x) = g(x)/c``, implemented as
:class:`forensics_core.labels.pu.ElkanNotoPU`.

Mordelet, F. and J.-P. Vert (2014). "A bagging SVM to learn from positive and unlabeled
examples." *Pattern Recognition Letters* 37: 201-209: bagging all positives against bootstrap
subsamples of the unlabeled pool, implemented as
:class:`forensics_core.labels.pu.BaggingPU`.

Bao, Y., B. Ke, B. Li, Y. J. Yu and J. Zhang (2020). *JAR* 58(1): 199-235, with the 2022
erratum at *JAR* 60(4): 1635-1646: the published benchmark this module is measured against.

Why the PU framing is the point, not a refinement
-------------------------------------------------
The SEC prosecutes what is detectable, large and litigable. A firm-year with no AAER is a
firm-year nobody charged, which is not the same thing as a clean one (``docs/known_traps.md``,
trap 1). A classifier trained with those rows as negatives is being told that every
undetected misstatement is an example of honesty, and it learns to predict *enforcement*.
Sub-question 3 of ``docs/research_question.md`` asks whether the honest formulation is also the
more powerful one. Either answer is publishable; a null result here is a real finding about how
much the label noise costs.

The target to match, and its provenance caveat
----------------------------------------------
``docs/validation_anchors.md`` Tier 1 gives the **corrected** RUSBoost figures: AUC 0.7428 and
NDCG@1% 0.0394 with 9 hits for the 2003-2005 test window, AUC 0.7228 and NDCG@1% 0.0237 with 10
hits for 2003-2008. Those were read from Walker (2022) in *Econ Journal Watch*, which tabulates
the erratum; the erratum itself is paywalled and was not read, and Walker's own re-runs got 8
hits in both windows. Reproduction means matching AUC to within roughly +/- 0.02 on the same
windows with the same labels, and the coverage problem in ``data/ACCESS_NOTES.md`` means that
is only attempted on the Bao et al. CSV, not on the SEC path.

The original (pre-erratum) figures are **not** the target. Do not compare to them.

The protocol to replicate: per test year, not one pooled fold
-------------------------------------------------------------
The window figures are not the score of one model on a pooled test set. The authors' posted
code (``run_RUSBoost.m`` and ``evaluate.m`` in JarFraud/FraudDetection, read at commit
2d10bc6; ``docs/validation_anchors.md``, "Replication protocol") loops over test years and,
for each test year ``t``:

1. **retrains** on fiscal years :data:`BAO_TRAIN_START` .. ``t - BAO_GAP_YEARS``, i.e. 1991 to
   ``t - 2``, so there is a two-year gap between the last training year and the test year;
2. **recodes serial frauds per test year**: every training row whose ``p_aaer`` is among the
   ``p_aaer`` values of year ``t``'s positives is set to 0 before fitting;
3. **scores year t alone**, with ``k`` for the ``@k`` metrics computed on year ``t``'s row
   count as ``round(BAO_K_FRACTION * n)``, MATLAB ``round``, which rounds halves away from
   zero (:data:`BAO_K_ROUNDING`).

The code stops at per-year output; a window's figure is the **unweighted mean of the per-year
figures** over its years. For AUC that is checked: Walker's per-year AUCs (2003 0.7281, 2004
0.7646, 2005 0.7289, 2006 0.7590, 2007 0.7176, 2008 0.6280; ``data/SOURCES.yaml``,
``ejw_walker_2022``) average to 0.7405 and 0.7210, the Run(1) window figures of his Table 2.
For NDCG@1% the mean is assumed the same way and for hits the window total is assumed to be
the sum; neither is checked against a per-year table. The single ``split="temporal"`` fold of
:class:`forensics_core.eval.harness.EvalSpec` -- train on ``time <= train_end``, test on every
later row pooled, no gap, no window end -- is **not** this design, whatever the harness
docstring says, and a result from it is a different estimand from the 0.7428 target. The
like-for-like run is therefore a loop of per-test-year datasets, one
:func:`~forensics_core.eval.harness.evaluate` call each, with ``k`` passed as the integer
above: the harness turns a float fraction into ``ceil(k * n)``, which is one more than
Bao's ``round`` whenever ``k * n`` has a fractional part strictly between 0 and 0.5.

**Labels for the like-for-like run** (:data:`BAO_LIKE_FOR_LIKE_LABELS`): the ``misstate``
labels of the pinned Bao et al. CSV as they stand, i.e. the authors' ex-post labels, built
from AAERs released through 31 December 2018, years after every test year. That is what
"the same labels" in ``docs/validation_anchors.md`` means. A release-censored variant, which
drops labels whose AAER was released after the test cutoff (``docs/known_traps.md``, trap 3),
is a different measurement; it is reported **separately** and never compared with the 0.7428
target. It needs ``p_aaer`` mapped to release dates first, because the Bao CSV carries none.
"""

from __future__ import annotations

import pandas as pd
from forensics_core.eval.harness import Dataset, EvalReport, EvalSpec, TransferResult

#: PU estimators compared, by their name in :data:`forensics_core.eval.harness.DETECTOR_REGISTRY`.
PU_ESTIMATORS: tuple[str, ...] = ("pu_elkan_noto", "pu_bagging")

#: Test windows used by the published benchmark, as inclusive (first, last) test years. Each
#: window is a set of per-year runs whose metrics are averaged, not one pooled test set; see
#: the module docstring, "The protocol to replicate".
BAO_TEST_WINDOWS: tuple[tuple[int, int], ...] = ((2003, 2005), (2003, 2008))

#: First fiscal year of every training set in the published benchmark's per-year loop.
BAO_TRAIN_START: int = 1991

#: Years between the last training year and the test year: test year ``t`` trains on
#: ``BAO_TRAIN_START .. t - BAO_GAP_YEARS``.
BAO_GAP_YEARS: int = 2

#: ``k`` for the ``@k`` metrics as a fraction of the test year's firm-years.
BAO_K_FRACTION: float = 0.01

#: How ``BAO_K_FRACTION * n`` becomes an integer ``k``: MATLAB ``round``, halves away from
#: zero. Not Python's ``round`` (halves to even) and not the harness's ``ceil``.
BAO_K_ROUNDING: str = "half_away_from_zero"

#: The label set of the like-for-like replication: the pinned Bao et al. CSV's ``misstate``
#: as it stands (ex-post, AAERs released through 2018). The release-censored variant is
#: reported separately and is never compared with the published target.
BAO_LIKE_FOR_LIKE_LABELS: str = "bao_ex_post"


def build_dataset(features: pd.DataFrame, labels: pd.DataFrame, *, source: str) -> Dataset:
    """Assemble the firm-year dataset for the PU benchmark.

    Parameters
    ----------
    features : pandas.DataFrame
        Firm-year features. Two provenances are in scope and they must never be silently mixed:
        the 28 raw items of the Bao et al. replication CSV (fiscal years 1990-2014), and the
        items mapped from the SEC Financial Statement Data Sets (2009 onward, and see
        :mod:`aaer.clean.xbrl_map` on how provisional that mapping is).
    labels : pandas.DataFrame
        Labelled violation firm-years, with the serial-fraud identifier that groups releases
        belonging to one case (``p_aaer`` in the Bao et al. files).
    source : str
        ``"bao"`` or ``"fsds"``. Recorded in ``Dataset.meta`` and printed in every report,
        because the two are not comparable.

    Returns
    -------
    Dataset
        ``y`` is 1 on labelled positives and ``NaN`` on the unlabeled remainder;
        :class:`forensics_core.eval.harness.PUDetector` reads ``NaN`` as unlabeled.

    Raises
    ------
    NotImplementedError
        Remaining: decide how serial-fraud cases spanning the train/test boundary are handled.
        Mishandling exactly that is what the 2022 erratum was about.
    """
    raise NotImplementedError(
        "Remaining: fix the serial-fraud recoding rule for cases spanning the split -- the "
        "erratum's error was that about 10 percent of them were not recoded to zero in training."
    )


def naive_supervised_report(ds: Dataset, spec: EvalSpec) -> EvalReport:
    """The comparison arm: unlabeled firm-years treated as negatives.

    This is the formulation the literature mostly uses. It is included to be beaten, or not, on
    the same per-test-year protocol and the same metrics (module docstring, "The protocol to
    replicate").

    Parameters
    ----------
    ds : Dataset
        From :func:`build_dataset`.
    spec : EvalSpec
        Split and metric specification, shared with the PU arm.

    Returns
    -------
    EvalReport

    Raises
    ------
    NotImplementedError
        Remaining: choose the base classifier so that the PU and naive arms differ only in the
        label treatment, not in the model family.
    """
    raise NotImplementedError(
        "Remaining: pick one base classifier shared by both arms so the comparison isolates "
        "the label treatment."
    )


def run_pu_benchmark(
    ds: Dataset,
    spec: EvalSpec | None = None,
    estimators: tuple[str, ...] = PU_ESTIMATORS,
) -> pd.DataFrame:
    """Score every PU estimator and the naive arm on one dataset.

    The published benchmark's protocol, which this function replicates (module docstring,
    "The protocol to replicate"): for each test year ``t`` in a window of
    :data:`BAO_TEST_WINDOWS`, retrain on fiscal years :data:`BAO_TRAIN_START` ..
    ``t - BAO_GAP_YEARS`` (a two-year gap), recode to 0 every training row whose ``p_aaer`` is
    among year ``t``'s positive cases, score year ``t`` alone with an integer
    ``k = round(BAO_K_FRACTION * n_t)`` rounded halves away from zero, then average the
    per-year metrics over the window. One pooled ``split="temporal"`` fold is not this design.

    Parameters
    ----------
    ds : Dataset
        From :func:`build_dataset`, with the labels named by :data:`BAO_LIKE_FOR_LIKE_LABELS`
        for the like-for-like run.
    spec : EvalSpec, optional
        Metrics for each per-year :func:`~forensics_core.eval.harness.evaluate` call. Its
        split does not choose the training years, which the per-year loop above fixes, and
        its ``ks`` is replaced, per test year, by the integer ``k`` above.
    estimators : tuple of str, default :data:`PU_ESTIMATORS`
        Detector registry names to run.

    Returns
    -------
    pandas.DataFrame
        One row per (estimator, test year) with AUC, average precision, NDCG@1% and
        precision@1%, ``k``, the hits in the top ``k``, the number of test positives and the
        test-year base rate; and one row per (estimator, test window) with the unweighted
        mean of the per-year AUC and NDCG@1% and the summed hits, the aggregation the
        published window figures are read as.

    Raises
    ------
    NotImplementedError
        Remaining: everything below the harness calls -- the estimators exist and are tested
        in forensics_core; what is missing is the dataset and the per-test-year loop.
    """
    raise NotImplementedError(
        "Remaining: build the dataset and the per-test-year loop (train 1991..t-2, recode "
        "serial frauds against year t, score t alone with k = round(0.01 n)), then call "
        "evaluate() per test year and average over each window."
    )


def estimated_class_prior(ds: Dataset, spec: EvalSpec | None = None) -> float:
    """Elkan-Noto estimate of ``P(y=1)``: how much misstatement is never charged.

    The gap between this and the observed AAER rate is an estimate of the enforcement
    selection, and it is arguably the most interesting quantity in the project -- it is the
    closest thing to a measurement of what the labels do not see, which is precisely the
    quantity that has no ground truth at all in the ``gosplan`` case.

    Parameters
    ----------
    ds : Dataset
        From :func:`build_dataset`.
    spec : EvalSpec, optional
        Split used to fit the non-traditional classifier.

    Returns
    -------
    float
        Estimated ``P(y=1)``.

    Raises
    ------
    NotImplementedError
        Remaining: the Elkan-Noto estimator assumes labelling is completely at random given
        ``y``, which enforcement plainly is not. State how far that assumption is violated
        before reporting a number, or report the estimate only as a bound.
    """
    raise NotImplementedError(
        "Remaining: state the selected-completely-at-random violation before reporting a prior."
    )


def transfer_to(source: Dataset, target: Dataset, spec: EvalSpec | None = None) -> TransferResult:
    """Fit on the labelled project and score an unlabelled one, carrying the calibration across.

    This is the programme's whole design in one call: a detector calibrated where ground truth
    exists is scored where it does not, and the source-calibrated score-to-precision curve is
    what makes a target score readable at all
    (:func:`forensics_core.eval.harness.transfer`).

    Parameters
    ----------
    source : Dataset
        A labelled dataset, normally this project's.
    target : Dataset
        An unlabelled dataset from another project.
    spec : EvalSpec, optional
        Split used for the source-side report.

    Returns
    -------
    TransferResult

    Raises
    ------
    NotImplementedError
        Remaining: define the feature correspondence between projects. Transfer is meaningless
        unless the columns mean the same thing on both sides, and for the Soviet data most of
        them do not.
    """
    raise NotImplementedError(
        "Remaining: define and defend the cross-project feature correspondence before transfer."
    )
