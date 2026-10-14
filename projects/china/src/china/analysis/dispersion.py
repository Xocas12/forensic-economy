"""Underdispersion of provincial growth. **Stubs only: every function raises.**

The programme's second signal, weighted equally with bunching: a fabricated series contains
*too little* noise. A reported growth series that is smoother than the physical record of the
same economy permits is impossible regardless of its level, and unlike a level test this one
needs no counterfactual for what the level should have been.

The variance floor is what makes it a test rather than an impression, and which floor is valid
depends on which way the causation runs.

* A **driver** of output puts a floor under it. If reported product is ``y = e p + u`` with
  the other shocks ``u`` uncorrelated with the driver ``p``, then ``Var(y)`` cannot be below
  ``e**2 Var(p)``. :func:`forensics_core.dispersion.underdispersion.implied_variance_floor`
  computes that bound and
  :func:`forensics_core.dispersion.underdispersion.variance_floor_test` tests against it, with
  the alternative "less": too smooth. The gosplan project specifies it for weather and
  hydrology. This project has no driver series: nothing in ``data/SOURCES.yaml`` is one.
* Electricity, rail freight, credit and nightlights are **indicators** of output, not drivers
  of it: ``p = c y + v``, the proxy responds to output and carries noise ``v`` of its own
  (industry mix, the shift from rail to road, the satellite seam; ``docs/known_traps.md``
  trap 5). Written the driver's way round that is ``y = p / c + u`` with ``u = -v / c``, so
  ``Cov(p, u) < 0`` and the driver bound's precondition fails in the direction that rejects
  honest provinces: ``Var(p) / c**2`` is ``Var(y) + Var(v) / c**2``, above the honest variance
  by the proxy's own noise. Fitting ``e`` by least squares of growth on the proxy over the
  tested window does not rescue it. The floor then equals ``r**2`` times the sample variance
  it is tested against, and the test can never reject, fabricated or not. An indicator's own
  variance bounds output variance from *above*.

What an indicator does bound from below is its covariance with output. Under honest reporting
``Cov(y, p) = c Var(y)``, so ``Var(y)`` cannot fall below ``Cov(y, p) / c``, and noise in the
report itself only raises ``Var(y)`` further. That is the floor :func:`proxy_implied_floor`
computes, with ``c`` taken from outside the tested window, and
:func:`underdispersion_by_province` tests against it with the sampling error of both the floor
and ``c`` carried into the statistic. ``tests/test_dispersion_floor.py`` checks by simulation
that this design rejects honest synthetic indicator-proxy provinces at the nominal rate when
``c`` is known, and never above it when ``c`` is estimated on earlier years and stays the same
across the two windows, on the same draws where the driver bound misses the nominal rate in
both directions. Those draws are serially independent. The size holds only under the two
conditions the simulation builds in, and the same file shows what breaks without them: a
response that has risen since the years it was estimated on, and growth and proxy noise that
are both persistent, each reject honest provinces too often. Both are preconditions of the
test, stated under :func:`proxy_implied_floor` and :func:`underdispersion_by_province`.

The trap, and it is a serious one here: provinces genuinely smooth their growth by managing
real activity, especially credit and infrastructure investment. Underdispersion in reported
growth is consistent both with fabrication and with a province that really did hit its target
every year by building things. What separates them is whether the *proxies* are equally
smooth: fabricating the report smooths the report alone, while managing the economy smooths
both. The covariance floor is built on that difference. A smoothed economy takes its proxies
with it and the floor falls with the report; a smoothed report leaves the proxies tracking the
growth that really happened, and the floor stays above the report's variance.

References
----------
Narasimhan & Jordache (2000, *Data Reconciliation and Gross Error Detection*, Gulf, ch. 3-5)
for the reconciliation framing used alongside these tests, quoted as
:mod:`forensics_core.reconcile` carries it. That module files a provenance caveat on the
chapter numbers, so nothing is added to the citation here.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = [
    "growth_series",
    "proxy_implied_floor",
    "smoothness_by_province",
    "underdispersion_by_province",
]


def growth_series(
    panel: pd.DataFrame,
    *,
    vintage: str,
    series: str = "grp_index_preceding_year",
) -> pd.DataFrame:
    """The per-province growth series the dispersion tests operate on.

    Parameters
    ----------
    panel : pandas.DataFrame
        Tidy panel.
    vintage : str
        Vintage to use.
    series : str, default "grp_index_preceding_year"
        Preferred source of growth. The published index at constant prices, minus 100, is the
        real growth rate the province itself reported; differencing ``grp_nominal`` gives
        nominal growth and is a different quantity.

    Returns
    -------
    pandas.DataFrame
        Wide, indexed by year with one column per province, growth in percentage points.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    What remains: extraction. Note also that the index column exists only in editions that
    print one; the 2024-style single-year cross-section carries an index column, and the
    2015-style multi-year panel carries five, so coverage differs by edition family.
    """
    raise NotImplementedError("needs the extracted index columns from yearbook table 3-9")


def proxy_implied_floor(
    growth: pd.DataFrame,
    proxy_growth: pd.DataFrame,
    *,
    proxy_response: float | pd.Series,
    response_se: float | pd.Series,
    response_years: tuple[int, int],
    response_source: str,
) -> pd.DataFrame:
    """Lower bound on the variance of reported growth implied by an indicator proxy.

    ``Cov(growth, proxy_growth) / proxy_response``, per province: the measurement-error floor
    described in the module docstring. It is **not** the driver bound
    ``elasticity**2 * Var(proxy_growth)`` of
    :func:`forensics_core.dispersion.underdispersion.implied_variance_floor`. Electricity,
    rail freight, credit and nightlights respond to output rather than drive it, and against
    that bound honest provinces are rejected at a rate set by the proxy's own noise.

    Parameters
    ----------
    growth : pandas.DataFrame
        Reported growth, from :func:`growth_series`.
    proxy_growth : pandas.DataFrame
        Growth of one indicator proxy, one of :data:`china.analysis.proxies.PROXY_SERIES`, on
        the same index and columns. A year missing from either is dropped from both.
    proxy_response : float or pandas.Series
        ``c``, the response of proxy growth to output growth: the slope of the proxy's growth
        on output growth, one value or one per province. Must be positive: a province whose
        response is not positive has no floor, and the implementation must refuse it rather
        than test it. It must come from **outside the tested window**, either estimated on
        years that do not overlap the years in ``growth`` or taken from a published estimate
        with a ``data/SOURCES.yaml`` entry, and it must be on the same quantity as
        ``growth``, real growth from the index (``docs/known_traps.md`` trap 4). Never fitted
        on the window being tested, in any functional form: a ``c`` fitted there is fitted on
        the variance it is meant to bound. :func:`china.analysis.proxies.proxy_elasticities`
        is not a source for it.

        Estimated outside the window, it must still be **the response in the tested
        window**: the floor assumes the ``c`` it is given is the ``c`` of the years it tests.
        The proxy relationships are known to move (trap 5 for electricity and rail freight),
        and a response that has risen since the years it was estimated on rejects honest
        provinces too often. In simulation, with ``c`` estimated per province on twelve
        earlier years, honest provinces were rejected about 4 per cent of the time while the
        response stayed put. A response 10 per cent higher in the tested window rejected about
        19 per cent of them at proxy noise sd 0.3pp and 6 to 7 per cent at 1.2pp; 20 per cent
        higher, about 49 and 9 to 10 per cent. Credit is the plausible rising case, as provinces
        lean on it to hit their targets (trap 6). A response that has fallen makes the test
        conservative instead, rejecting 0 to 2.5 per cent, which costs power rather than
        honest provinces. The analysis plan has to test or bound the drift in ``c`` between
        the two windows before this floor is used.

        A ``c`` estimated on reported growth is valid only on years whose reports are believed
        honest. A province that smoothed its report in both windows calibrates its own
        earlier-window ``c`` to its smoothing: with the report pulled halfway to the mean, its
        ``c`` comes out near twice the true response. In simulation such provinces were then
        flagged 4 to 5 per cent of the time, the nominal rate, where the true ``c`` flags them
        99.7 to 99.8 per cent of the time at proxy noise sd 0.3pp and about 88 per cent at
        0.6pp. A per-province ``c`` from the same province's earlier years is therefore blind
        to a province that smoothed throughout. A pooled response is diluted by the provinces
        that did not smooth, and a published one is not touched by the reports at all, which
        is a reason to prefer either.
    response_se : float or pandas.Series
        Standard error of ``proxy_response``. Required because it enters the statistic in
        :func:`underdispersion_by_province`: treating an estimated ``c`` as exact makes the
        test reject honest provinces too often.
    response_years : tuple of int
        First and last year of the sample ``proxy_response`` was estimated on. The
        implementation must raise ``ValueError`` when this range overlaps the years in
        ``growth``.
    response_source : str
        Where ``proxy_response`` came from: the proxy, vintage and years of the estimation, or
        the registry id of the published estimate. The implementation must refuse a blank
        string.

    Returns
    -------
    pandas.DataFrame
        One row per province with ``floor``; ``s2``, the sample variance of growth on the
        same years; ``slope`` and ``slope_se``, the least-squares slope of proxy growth on
        reported growth and its standard error; ``proxy_response`` and ``response_se`` as
        passed; and ``n``, the number of years used. The slope columns are there because the
        floor is estimated on the window it bounds, and :func:`underdispersion_by_province`
        has to carry that sampling error into the test.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    ``s2`` below ``floor`` is the same event as ``slope`` above ``proxy_response`` whenever
    ``c`` is positive, which is why the test is run on the slope.

    Caveats that have to travel with any result. The floor holds **only if** the proxy's own
    noise is uncorrelated with output growth in the tested window; a proxy whose noise moves
    with output shifts ``c`` within the window and the floor with it. It also holds only if
    ``c`` is the response in the tested window: a response that has risen since the years it
    was estimated on rejects honest provinces too often, and one that has fallen costs power
    (see ``proxy_response``). The test against it keeps its size only if growth and the
    proxy's noise are not both serially correlated (see :func:`underdispersion_by_province`).
    A report decoupled from activity altogether has a covariance near zero and a floor near
    zero, so it passes here; that failure shows as a weak proxy relationship and a large
    residual in :mod:`china.analysis.proxies`, not as underdispersion. If a province smooths
    both its economy and its report, the floor falls with the report and the test says
    nothing. And if it smooths its report in the years ``c`` was estimated on as well as in
    the tested ones, a ``c`` estimated on its own reports absorbs the smoothing and the test
    says nothing either. Each of these is a limitation of the test, not a clean bill of
    health, and must be reported as such.

    What remains: an out-of-window ``c`` for each proxy. No published response is in the
    registry, and the yearbook panels this project can build are short. Estimating ``c`` on a
    province's earlier years takes those years away from the test, and it cannot see a
    province that smoothed its report in both windows, because that ``c`` is calibrated to
    the smoothing. A published response does not have that blind spot, and a pooled one has
    it only as far as the pool smoothed too. Whichever source is chosen, ``c`` has to hold in
    the tested window, so the drift in the response between the two windows has to be tested
    or bounded. Which window, whether per province or pooled, and how the drift is checked
    are questions to settle in the analysis plan before G1, not defaults to pick here.
    """
    raise NotImplementedError(
        "needs a proxy response c estimated outside the tested window, with its standard "
        "error and source; the floor is Cov(growth, proxy growth) / c, never the driver "
        "bound elasticity**2 * Var(proxy growth), which indicator proxies cannot support"
    )


def underdispersion_by_province(
    growth: pd.DataFrame,
    floors: pd.DataFrame,
    *,
    window: int | None = None,
) -> pd.DataFrame:
    """Test each province's growth variance against its implied floor.

    The floor from :func:`proxy_implied_floor` is estimated on the window it tests, so the
    chi-square null of :func:`forensics_core.dispersion.underdispersion.variance_floor_test`,
    which treats the floor as a constant known before the data were seen, does not apply to
    it. Growth variance below ``Cov(growth, proxy growth) / c`` is the same event as a slope
    of proxy growth on reported growth above ``c``, so the test is the one-sided t-test of
    that slope against ``c``: ``t = (slope - c) / sqrt(slope_se**2 + response_se**2)`` on
    ``n - 2`` degrees of freedom, alternative "greater", which is reported growth too smooth
    for its proxy.

    That is the ordinary least-squares slope test, and its nominal size **requires serially
    independent residuals**: growth, and the proxy's noise around ``c`` times growth, must not
    both be persistent. The library states the same independence assumption for
    :func:`~forensics_core.dispersion.underdispersion.variance_floor_test`. In simulation with
    ``c`` known, persistence in only one of them left the rejection rate on honest provinces
    at 4.6 to 5.4 per cent, as did a steady decline in growth. With both AR(1) at the same
    coefficient it rose to about 8 per cent at 0.5, 11 to 12.5 per cent at 0.7 and 17 to 18
    per cent at 0.9, at proxy noise sd 0.3pp and 1.2pp alike. Provincial growth is
    persistent, and the slow structural shifts of ``docs/known_traps.md`` trap 5 are
    persistent proxy noise, so the condition cannot be assumed here. The analysis plan has to
    do one of two things before the test is run: specify an autocorrelation-robust standard
    error, whose own size with about a dozen years then has to be checked, or check this
    test's size on a simulation with persistence in growth and proxy noise matched to the
    panel, and report the calibrated rate.

    Parameters
    ----------
    growth : pandas.DataFrame
        Reported growth, from :func:`growth_series`.
    floors : pandas.DataFrame
        Output of :func:`proxy_implied_floor`.
    window : int, optional
        When given, run the test on rolling windows, so that a province that was smooth for
        four years and normal afterwards is visible. The floor is then estimated afresh on
        each window, ``floors`` carrying one row per province and window from
        :func:`proxy_implied_floor` called on that window's years, because a covariance
        estimated on the full sample does not bound the variance of a part of it. The
        windows overlap, so their p-values are dependent.

    Returns
    -------
    pandas.DataFrame
        One row per province, or per province and window, with the statistic, the p-value,
        the sample variance and the floor.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    What remains: the multiple-comparison policy. Thirty-one provinces tested at once will
    produce one or two nominally significant results by chance, so the reported quantity has
    to be a corrected one, decided before the test is run. And the treatment of serial
    correlation above, a robust standard error or a calibrated size, decided at the same time.
    """
    raise NotImplementedError(
        "needs growth_series and proxy_implied_floor, and a multiple-comparison correction "
        "chosen in advance for 31 simultaneous tests"
    )


def smoothness_by_province(
    growth: pd.DataFrame,
    *,
    detrend: str = "diff",
    n_perm: int = 999,
    seed: int | None = None,
) -> Any:
    """Test whether growth is too smooth, without needing a proxy at all.

    Wraps :func:`forensics_core.dispersion.underdispersion.too_smooth_test`, whose statistic
    is the von Neumann ratio, the mean squared successive difference over the variance, about
    2 for independent noise and lower for a series with too little year-to-year movement. The
    null is that successive changes are exchangeable and the p-value comes from permuting
    them.

    The value of this test is that it needs no elasticity and no proxy, so it can be run on
    any province and any vintage. Its cost is that a genuinely trending economy is smooth by
    construction, which is what ``detrend`` is for.

    Parameters
    ----------
    growth : pandas.DataFrame
        Reported growth, from :func:`growth_series`.
    detrend : {"none", "linear", "diff"}, default "diff"
        Detrending applied before the statistic.
    n_perm : int, default 999
        Permutations.
    seed : int, optional
        Passed to ``numpy.random.default_rng``.

    Returns
    -------
    pandas.DataFrame
        One row per province with the ratio, the p-value and the number of years used.

    Raises
    ------
    NotImplementedError
        Always.

    Notes
    -----
    What remains: the panel. Note that with roughly a decade of annual observations per
    province the permutation distribution is coarse, so p-values should be reported with the
    number of distinct attainable values.
    """
    raise NotImplementedError(
        "needs growth_series; with about ten annual observations per province the "
        "permutation distribution is coarse and that has to be reported"
    )
