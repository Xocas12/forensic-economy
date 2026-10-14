"""The unified-accounting reform at the 2019 data year. **Stubs only: every function raises.**

**The aggregate jump at the reform cannot separate method from misreporting.** The reform
changed the method, and closing the gap was what it was for. The plan as the bureau's deputy
head described it (registry id ``nbs_qa_unified_accounting_plan_2017``) reforms the accounting
entity ('改革核算主体'), the accounting method ('改革核算方法') and the work mechanism
('改革工作机制'), in order to achieve basic alignment of summed regional product with
national product ('实现地区生产总值汇总数据与国内生产总值数据的基本衔接'), and the reason he
gives is that the gap was too large ('差距有些偏大'). Cross-province double counting,
provincial deflators and provincial methods are what unified accounting replaces, so the
mechanical part of the gap is expected to move at 2019 too. The gap is therefore predicted to
contract at 2019 with zero misreporting, and a jump there estimates the **combined effect** of
the method change, the fourth economic census and any misreporting. Removing a pre-reform
estimate of the mechanical part does not fix that: the reform changes the mechanical part
itself, and any error in the estimate passes one for one into what is left. Placebo years and
a break moved by one year do not fix it either, because 2019 is also the year the method
changed.

Any claim about misreporting from the reform has to come from cross-province variation:
:func:`cross_province_reform_contrast` asks whether the reform moved a province's figures more
where its pre-reform growth had outrun its physical proxies, and it rests on a stated model of
how the method and census revisions are themselves distributed across provinces. Without that
model the reform supports no misreporting claim, and the aggregate jump is reported as the
combined effect and nothing narrower.

The dates, verified from the bureau's own question-and-answer page of 27 December 2019
(registry id ``nbs_qa_unified_accounting_2019_12_27``), corroborated by Xinhua on 13 November
2019 and China Daily on 7 January 2020:

* **June 2017** the reform plan is approved by the 36th meeting of the Central Leading Group
  for Comprehensively Deepening Reform;
* **early 2020** unified accounting is implemented, computing the **2019** annual regional
  product;
* before that, a graded system in place since 1985 in which provincial bureaus computed their
  own figures.

**So the break is at the 2019 data year.** Not 2017, which is when a decision was taken about
a future accounting round, and not 2020, which is when the 2019 figures were published. Using
2017 tests whether provinces changed their reporting in anticipation of a reform, which is a
different and much weaker hypothesis, and using it by accident is the most likely way to get
a wrong answer that looks right.

Two further complications from ``docs/known_traps.md``. The reform was announced, piloted and
then applied, and provinces revised their back-series at different times, so the design has to
be tested at plus and minus one year. And the fourth economic census lands in the same window,
which is a rebasing rather than a reporting change. The aggregate series cannot separate the
census, the method change and misreporting from one another at 2019, because all three land in
the same window.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = [
    "REFORM_APPROVAL_YEAR",
    "REFORM_FIRST_DATA_YEAR",
    "REFORM_IMPLEMENTED",
    "break_year_sensitivity",
    "cross_province_reform_contrast",
    "placebo_break_years",
    "reform_discontinuity",
    "vintage_revision_at_reform",
]

#: The 36th meeting of the Central Leading Group approves the plan. **Not the break year.**
REFORM_APPROVAL_YEAR = 2017

#: The first data year computed under unified accounting. **This is the break year.**
REFORM_FIRST_DATA_YEAR = 2019

#: When the reform was executed: the 2019 figures were computed and published in early 2020.
REFORM_IMPLEMENTED = "2020-01"


def reform_discontinuity(
    gap: pd.Series,
    *,
    break_year: int = REFORM_FIRST_DATA_YEAR,
    bandwidth: int = 5,
    polynomial_degree: int = 1,
) -> Any:
    """Estimate the jump in the gap at the reform's first data year.

    A regression-discontinuity-in-time design: fit a local polynomial in the data year on
    each side of ``break_year`` within ``bandwidth`` years, and test the jump at the
    threshold.

    **What the jump is.** The combined effect of the method change, the fourth economic census
    and any misreporting, and nothing narrower. The reform was designed to close the gap (see
    the module docstring), so a contraction at 2019 is predicted with zero misreporting. Read
    as a test for misreporting it has no size: under the null of no misreporting it still
    rejects whenever it has the power to see the method change. The jump bounds the
    misreporting part from above only if the method change and the census each moved the gap
    in the jump's direction. The plan's stated aim supports that for the method change;
    nothing in this project establishes it for the census, so wherever the bound is used that
    assumption is written beside it. A misreporting claim needs
    :func:`cross_province_reform_contrast` and the model it rests on.

    Parameters
    ----------
    gap : pandas.Series
        The gap by data year, from :func:`china.analysis.gap.provincial_national_gap` or
        :func:`china.analysis.gap.gap_in_growth_rates`, within one vintage. Passing the
        ``residual`` column of :func:`china.analysis.gap.mechanical_gap_components` instead
        does not take the method change out: the reform changes the mechanical part itself,
        so a residual built from a pre-reform estimate of it still jumps at 2019, and any
        error in that estimate enters the jump one for one.
    break_year : int, default :data:`REFORM_FIRST_DATA_YEAR`
        The threshold. The default is the verified first data year; passing 2017 tests a
        different hypothesis and the caller should say so.
    bandwidth : int, default 5
        Years each side.
    polynomial_degree : int, default 1
        Order of the local fit. Kept low on purpose: with roughly a decade of annual
        observations a high-order polynomial fits the break rather than the trend.

    Returns
    -------
    forensics_core.TestResult
        ``statistic`` is the estimated jump, ``details`` carry the fitted coefficients, the
        bandwidth, the effective sample each side and the break year used.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    What remains, and it is a design problem before it is a coding one: this test has about
    ten annual observations, so its power is very low and its standard errors need care.
    Decide before running it whether the unit of observation is the year (about ten points) or
    the province-year (about 310, but serially and cross-sectionally dependent), and say which
    in the write-up.
    """
    raise NotImplementedError(
        "needs the gap series; and the unit of observation and inference for a ten-point "
        "annual design must be settled first"
    )


def break_year_sensitivity(
    gap: pd.Series,
    *,
    candidate_years: tuple[int, ...] = (2017, 2018, 2019, 2020),
    bandwidth: int = 5,
) -> pd.DataFrame:
    """Re-run the discontinuity at each candidate break year.

    The specification check ``docs/known_traps.md`` asks for. The reform was announced,
    piloted and applied over several years, and provinces revised back-series at different
    times, so a jump that only exists at exactly one year is a different kind of evidence
    from one that is strongest at 2019 and present either side. Either way the jump at 2019
    is still the combined effect described in :func:`reform_discontinuity`: this check is
    about when the break happened, not what caused it.

    Parameters
    ----------
    gap : pandas.Series
        The gap by data year.
    candidate_years : tuple of int, default (2017, 2018, 2019, 2020)
        Break years to try: the approval year, the year before the first data year, the first
        data year, and the publication year.
    bandwidth : int, default 5
        Years each side.

    Returns
    -------
    pandas.DataFrame
        One row per candidate year with the estimated jump, its p-value and the sample sizes.

    Raises
    ------
    NotImplementedError
        Always.
    """
    raise NotImplementedError("needs reform_discontinuity")


def placebo_break_years(
    gap: pd.Series,
    *,
    placebo_years: tuple[int, ...] = (),
    bandwidth: int = 5,
) -> Any:
    """Compare the jump at the reform against jumps at years where nothing happened.

    Uses :func:`forensics_core.bunching.inference.placebo_test`: the p-value is the share of
    placebo years whose estimated jump is at least as large as the real one.

    A small p-value says that 2019 is unusual, which the method change alone already
    predicts. It does not say that the jump is misreporting, because no placebo year carries a
    method change and 2019 does.

    Parameters
    ----------
    gap : pandas.Series
        The gap by data year.
    placebo_years : tuple of int, optional
        Years to use as placebos. Empty by default and required in practice, because the
        choice is substantive: a placebo year must be one with no census rebasing (2004,
        2008, 2013, 2018) and no boundary change, or it is not a placebo.
    bandwidth : int, default 5
        Years each side.

    Returns
    -------
    forensics_core.TestResult
        With the placebo distribution in ``details``.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    What remains: with roughly a decade of usable years, there may not be enough clean placebo
    years for this test to have any power. Establishing that is itself a result and should be
    reported rather than worked around.
    """
    raise NotImplementedError(
        "needs reform_discontinuity, and a defensible list of placebo years that excludes "
        "census rebasings and boundary changes"
    )


def vintage_revision_at_reform(
    panel: pd.DataFrame,
    *,
    before_vintage: str,
    after_vintage: str,
    series: str = "grp_nominal",
) -> pd.DataFrame:
    """How much each province's history was rewritten across the reform.

    The complement to the discontinuity test, and the one that uses the vintage column for
    what it is for. Rather than asking whether the gap jumps at 2019, this asks how much a
    province's *already published* figures for years before 2019 changed between an edition
    published before the reform and one published after it.

    A revision across the reform is not by itself inflation being given back. Every
    province's back-series is rewritten for the method change and for the census rebasing as
    well, so a large revision says that the province moved, not why. What this table can feed
    is the cross-province comparison in :func:`cross_province_reform_contrast`, and only
    together with that function's stated model of the legitimate revisions.

    Parameters
    ----------
    panel : pandas.DataFrame
        Tidy panel holding both vintages.
    before_vintage, after_vintage : str
        Vintage labels, e.g. ``"csy2015"`` and ``"csy2024"``.
    series : str, default "grp_nominal"
        Series to compare.

    Returns
    -------
    pandas.DataFrame
        One row per province and overlapping data year, with both values, the revision and
        the revision as a share of the earlier value.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    What remains: extraction of at least two editions. The registry already shows what this
    will look like for the one province checked by hand: the 2015 edition reports Liaoning at
    28,626.58 for 2014, and the 2024 edition reports 30,209.4 for 2023, nine years later.
    Reproducing that contrast from extracted tables, rather than from the registry's prose, is
    the acceptance test for the extraction step.
    """
    raise NotImplementedError("needs at least two extracted yearbook vintages in the panel")


def cross_province_reform_contrast(
    revisions: pd.DataFrame,
    excess_growth: pd.DataFrame,
    *,
    revision_model: Any,
) -> Any:
    """Did the reform move a province more where its growth had outrun its proxies?

    The only form of the reform test that can bear on misreporting. The aggregate jump in
    :func:`reform_discontinuity` cannot, because unified accounting was designed to close the
    gap and would close it with no misreporting at all. What can still differ is *which*
    provinces the reform moved. If provinces inflated their reports before the reform and the
    centre's calculation stopped it, a province's figures should come down more at the reform
    where its reported growth had run further ahead of its physical proxies.

    **The model this rests on.** Each province's revision across the reform is the sum of a
    legitimate part, the method change (cross-province double counting removed, provincial
    deflators and methods replaced by the centre's) plus the census rebasing, and a
    misreporting part. The contrast reads the association between revision and excess growth
    as misreporting, so it identifies anything only under the assumption that, once
    ``revision_model`` is accounted for, the legitimate part is unrelated to excess growth.
    That assumption is not free, and it fails in at least two ways the model has to address.
    A province whose output is concentrated in head offices and services can outrun an
    electricity proxy (``docs/known_traps.md``, trap 5) and also lose more to the removal of
    double counting. And the two inputs share their error: residuals taken from an edition
    published before the reform, which is where pre-reform inflation would show, rest on the
    same reported figures that the revisions rewrite, so honest error in a province's
    pre-reform figure enters both, an overstated figure raising its excess growth and then
    being revised down at the reform. Either produces the predicted association with no
    misreporting at all. The model has to say how the legitimate revisions are distributed
    across provinces, which covariates it conditions on, and how it removes the error the two
    inputs share, before the revisions are looked at; it must not be fitted to the revisions it
    is meant to explain. Any error in it passes one for one into the misreporting estimate.
    Hence ``revision_model`` has no default.

    Parameters
    ----------
    revisions : pandas.DataFrame
        How much each province's figures moved across the reform, from
        :func:`vintage_revision_at_reform`, as a share of the earlier value.
    excess_growth : pandas.DataFrame
        Each province's pre-reform growth in excess of what its proxies imply, one value per
        province: the change in its combined residual from
        :func:`china.analysis.proxies.proxy_residuals` across the pre-reform data years the
        revisions cover. The change, not the level: the within-province fit that
        :func:`china.analysis.proxies.proxy_elasticities` defaults to gives each province its
        own intercept, so a residual's level is measured from that province's own fitted
        relationship and averages to zero over the years it was fitted on. Both inputs are on
        ``grp_nominal``, the default series of both functions, so this is excess *nominal*
        growth; pairing it with real growth at provincial deflators mixes the two
        (``docs/known_traps.md``, trap 4).
    revision_model : object
        The stated model of the legitimate revisions: the expected method-change and
        census revision for each province, or the covariates given which the legitimate
        revision is assumed unrelated to ``excess_growth``, with the reason for believing it,
        and how it removes the error that ``revisions`` and ``excess_growth`` share.
        Required, because without it the contrast measures nothing in particular, and which
        model to use is a pre-registration decision that has not been taken.

    Returns
    -------
    forensics_core.TestResult
        ``statistic`` is the association between revision and excess growth net of
        ``revision_model``; ``details`` carry the model as stated, the per-province inputs and
        the number of provinces.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    What remains: two extracted vintages either side of the reform, the proxy residuals, and
    the model, which has not been chosen. Also not chosen, and fixed with the model before the
    revisions are seen: which pre-reform data years form the window, whether the residual's
    change is taken between end points or as a fitted trend, and how the per-year revisions
    are reduced to one value per province. With 31 provinces this contrast has little power,
    and that has to be reported alongside whatever it finds.
    """
    raise NotImplementedError(
        "needs extracted vintages either side of the reform, the proxy residuals, and a stated "
        "model of how the method and census revisions are distributed across provinces; no "
        "such model has been pre-registered"
    )
