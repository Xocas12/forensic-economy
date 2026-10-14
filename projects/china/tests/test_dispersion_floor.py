"""The variance floor of the underdispersion test, checked by simulation before it exists.

``china.analysis.dispersion`` is stubs (CONTRACT rule 4), so its floor cannot be called yet.
What can be checked now is the design the stubs document. This file carries that design as a
reference implementation, written from the docstrings of
:func:`~china.analysis.dispersion.proxy_implied_floor` and
:func:`~china.analysis.dispersion.underdispersion_by_province`, holds the stubs to its
signatures, and runs it on synthetic honest provinces whose proxy is an *indicator* of output,
``p = c y + v``, which is what electricity, rail freight, credit and nightlights are. A floor
fit for that job rejects such provinces at the nominal rate. The driver bound the design
replaced, ``elasticity**2 * Var(proxy)``, is run on the same draws to show that they are draws
on which a floor with the wrong size is visible.

The nominal rate holds under conditions the stubs state as preconditions, and the size tests
build them in: ``c`` is the same in the window it is estimated on and the window it tests, and
growth and proxy noise are drawn independently year to year. They also estimate ``c`` on
earlier years that were reported honestly, which is what lets a smoothed report show. The
last three tests take each of these away and pin down what happens, so the stated caveats
cannot drift from what the design does.

When the phase opens and the stubs are implemented, these tests should run against the real
functions in place of the reference, unchanged.

Everything here is synthetic and says so: the years are 2073 to 2096 and every province is
labelled SYNTHETIC. Nothing reads ``data/``.
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest
from china.analysis import dispersion
from forensics_core.dispersion.underdispersion import implied_variance_floor, variance_floor_test
from scipy import stats

ALPHA = 0.05

#: Rejection rates on honest provinces that count as "the nominal rate". Each rate is taken
#: over N_PROVINCES provinces, where the Monte Carlo standard error at 0.05 is under 0.003, so
#: the band is several standard errors wide and the tests do not depend on the seed.
SIZE_BAND = (0.03, 0.07)

N_PROVINCES = 6_200  # 200 synthetic panels of 31 provinces
N_YEARS = 12
TESTED_YEARS = tuple(range(2085, 2085 + N_YEARS))
EARLIER_YEARS = tuple(range(2073, 2073 + N_YEARS))
EARLIER_RANGE = (EARLIER_YEARS[0], EARLIER_YEARS[-1])

#: Honest growth, in percentage points. Synthetic parameters, not estimates of anything.
GROWTH_MEAN, GROWTH_SD = 7.0, 1.2


# --- the documented design, as a reference implementation ------------------------------


def _slope_on_growth(growth: pd.DataFrame, proxy_growth: pd.DataFrame) -> pd.DataFrame:
    """Per province: least-squares slope of proxy growth on growth, its standard error, and
    the variance and covariance it is built from, over the years where both are finite."""
    y = growth.to_numpy(dtype=float)
    p = proxy_growth.to_numpy(dtype=float)
    ok = np.isfinite(y) & np.isfinite(p)
    n = ok.sum(axis=0)
    if (n < 3).any():
        raise ValueError("every province needs at least three years with both series")
    y = np.where(ok, y, np.nan)
    p = np.where(ok, p, np.nan)
    yc = np.nan_to_num(y - np.nanmean(y, axis=0))
    pc = np.nan_to_num(p - np.nanmean(p, axis=0))
    sxx = (yc**2).sum(axis=0)
    sxp = (yc * pc).sum(axis=0)
    slope = sxp / sxx
    resid = np.where(ok, pc - slope * yc, 0.0)
    slope_se = np.sqrt((resid**2).sum(axis=0) / (n - 2) / sxx)
    return pd.DataFrame(
        {
            "slope": slope,
            "slope_se": slope_se,
            "s2": sxx / (n - 1),
            "cov": sxp / (n - 1),
            "n": n,
        },
        index=growth.columns,
    )


def _per_province(value: float | pd.Series, columns: pd.Index) -> np.ndarray:
    if isinstance(value, pd.Series):
        return value.reindex(columns).to_numpy(dtype=float)
    return np.full(len(columns), float(value))


def reference_floor(
    growth: pd.DataFrame,
    proxy_growth: pd.DataFrame,
    *,
    proxy_response: float | pd.Series,
    response_se: float | pd.Series,
    response_years: tuple[int, int],
    response_source: str,
) -> pd.DataFrame:
    """``proxy_implied_floor`` as its docstring specifies it."""
    if not isinstance(response_source, str) or not response_source.strip():
        raise ValueError("response_source must say where proxy_response came from")
    first, last = response_years
    years = np.asarray(growth.index)
    if ((years >= first) & (years <= last)).any():
        raise ValueError(
            f"proxy_response was estimated on {first}-{last}, which overlaps the tested years"
        )
    if not (
        growth.index.equals(proxy_growth.index) and growth.columns.equals(proxy_growth.columns)
    ):
        raise ValueError("growth and proxy_growth must share their index and columns")
    c = _per_province(proxy_response, growth.columns)
    c_se = _per_province(response_se, growth.columns)
    if not (np.isfinite(c).all() and (c > 0).all()):
        raise ValueError("proxy_response must be finite and positive for every province")
    fit = _slope_on_growth(growth, proxy_growth)
    return pd.DataFrame(
        {
            "floor": fit["cov"].to_numpy() / c,
            "s2": fit["s2"].to_numpy(),
            "slope": fit["slope"].to_numpy(),
            "slope_se": fit["slope_se"].to_numpy(),
            "proxy_response": c,
            "response_se": c_se,
            "n": fit["n"].to_numpy(),
        },
        index=growth.columns,
    )


def reference_test(
    growth: pd.DataFrame,
    floors: pd.DataFrame,
    *,
    window: int | None = None,
) -> pd.DataFrame:
    """``underdispersion_by_province`` as its docstring specifies it, full window only."""
    if window is not None:
        raise ValueError("the reference covers the full-window test only")
    se = np.sqrt(floors["slope_se"] ** 2 + floors["response_se"] ** 2)
    statistic = (floors["slope"] - floors["proxy_response"]) / se
    return pd.DataFrame(
        {
            "statistic": statistic,
            "pvalue": stats.t.sf(statistic, floors["n"] - 2),
            "s2": floors["s2"],
            "floor": floors["floor"],
        },
        index=floors.index,
    )


def _signature(fn) -> list[tuple[str, object, object, object]]:
    return [
        (p.name, p.kind, p.default, p.annotation) for p in inspect.signature(fn).parameters.values()
    ] + [("return", None, None, inspect.signature(fn).return_annotation)]


def _design():
    """The reference design, once the stubs are confirmed to document the same one.

    Every test below goes through this, so none of them can pass while the stubs describe a
    different floor from the one being simulated.
    """
    pairs = (
        (dispersion.proxy_implied_floor, reference_floor),
        (dispersion.underdispersion_by_province, reference_test),
    )
    for stub, reference in pairs:
        assert _signature(stub) == _signature(reference), (
            f"{stub.__name__} no longer documents the floor this file checks: "
            f"{_signature(stub)} != {_signature(reference)}"
        )
    return reference_floor, reference_test


# --- synthetic provinces --------------------------------------------------------------------


def _frame(values: np.ndarray, years: tuple[int, ...]) -> pd.DataFrame:
    columns = pd.Index([f"SYNTHETIC-{i:04d}" for i in range(values.shape[1])], name="province")
    return pd.DataFrame(values, index=pd.Index(years, name="year"), columns=columns)


def _indicator_provinces(
    rng: np.random.Generator,
    *,
    response: float,
    noise_sd: float,
    noise_in_levels: bool,
    years: tuple[int, ...] = TESTED_YEARS,
    smoothing: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Real growth, its proxy, and the growth a province reports.

    The proxy is an indicator: ``proxy = response * real + noise``. With ``noise_in_levels``
    the noise sits on the proxy's log level, so its growth carries the difference of two
    draws, as a level shift in the proxy would. ``smoothing`` below 1 pulls the *report*
    toward the mean growth while the proxy keeps tracking real growth: a smoothed report.
    """
    shape = (len(years), N_PROVINCES)
    real = rng.normal(GROWTH_MEAN, GROWTH_SD, size=shape)
    if noise_in_levels:
        noise = np.diff(rng.normal(0.0, noise_sd, size=(len(years) + 1, N_PROVINCES)), axis=0)
    else:
        noise = rng.normal(0.0, noise_sd, size=shape)
    proxy = response * real + noise
    reported = GROWTH_MEAN + smoothing * (real - GROWTH_MEAN)
    return _frame(real, years), _frame(proxy, years), _frame(reported, years)


def _earlier_response(
    earlier_growth: pd.DataFrame, earlier_proxy: pd.DataFrame
) -> tuple[pd.DataFrame, pd.Index]:
    """``c`` per province by least squares on the earlier window, and the provinces it serves.

    A province whose earlier slope is not positive has no floor, and the floor refuses it, so
    it is set aside here as a caller would have to set it aside. With a noisy proxy that is a
    real share of the provinces, which is one cost of estimating ``c`` province by province.
    """
    earlier = _slope_on_growth(earlier_growth, earlier_proxy)
    usable = earlier.index[earlier["slope"] > 0]
    assert len(usable) >= 0.8 * len(earlier), f"only {len(usable)} usable provinces"
    return earlier.loc[usable], usable


def _rejection_rate(result: pd.DataFrame) -> float:
    return float((result["pvalue"] < ALPHA).mean())


def _known_response(floor, growth, proxy, response):
    return floor(
        growth,
        proxy,
        proxy_response=response,
        response_se=0.0,
        response_years=EARLIER_RANGE,
        response_source="synthetic: the response the provinces were drawn with",
    )


def _against_earlier_response(floor, test, growth, proxy, earlier_growth, earlier_proxy):
    """The test with ``c`` estimated per province on the earlier window, its error carried in.

    Returns the test result and the earlier-window fit, for the provinces that have a floor.
    """
    earlier, usable = _earlier_response(earlier_growth, earlier_proxy)
    floors = floor(
        growth[usable],
        proxy[usable],
        proxy_response=earlier["slope"],
        response_se=earlier["slope_se"],
        response_years=EARLIER_RANGE,
        response_source="synthetic: least squares on the earlier window",
    )
    return test(growth[usable], floors), earlier


def _persistent(rng: np.random.Generator, ar: float, sd: float) -> np.ndarray:
    """Stationary AR(1) draws over the tested years with marginal sd ``sd``, per province."""
    shape = (len(TESTED_YEARS), N_PROVINCES)
    innovations = rng.normal(0.0, sd * np.sqrt(1.0 - ar**2), size=shape)
    draws = np.empty(shape)
    draws[0] = rng.normal(0.0, sd, size=N_PROVINCES)
    for t in range(1, shape[0]):
        draws[t] = ar * draws[t - 1] + innovations[t]
    return draws


# --- the tests ------------------------------------------------------------------------------


def test_the_stubs_document_a_covariance_floor_with_a_response_from_outside_the_window():
    _design()
    assert "elasticity" not in inspect.signature(dispersion.proxy_implied_floor).parameters
    with pytest.raises(NotImplementedError, match="outside the tested window"):
        dispersion.proxy_implied_floor(
            None,
            None,
            proxy_response=None,
            response_se=None,
            response_years=None,
            response_source=None,
        )


def test_the_floor_refuses_a_response_estimated_on_the_tested_window():
    floor, _ = _design()
    rng = np.random.default_rng(3301)
    growth, proxy, _ = _indicator_provinces(rng, response=1.0, noise_sd=1.2, noise_in_levels=False)
    kwargs = {
        "proxy_response": 1.0,
        "response_se": 0.1,
        "response_source": "synthetic",
    }
    for overlapping in ((TESTED_YEARS[0], TESTED_YEARS[-1]), (2080, TESTED_YEARS[0])):
        with pytest.raises(ValueError, match="overlaps the tested years"):
            floor(growth, proxy, response_years=overlapping, **kwargs)
    with pytest.raises(ValueError, match="where proxy_response came from"):
        floor(growth, proxy, **{**kwargs, "response_source": "  "}, response_years=EARLIER_RANGE)
    with pytest.raises(ValueError, match="positive"):
        floor(growth, proxy, **{**kwargs, "proxy_response": -1.0}, response_years=EARLIER_RANGE)


@pytest.mark.parametrize("response", [1.0, 1.3])
@pytest.mark.parametrize(
    "noise_in_levels", [False, True], ids=["noise-in-growth", "noise-in-levels"]
)
@pytest.mark.parametrize("noise_sd", [0.3, 0.6, 1.2, 2.4])
def test_the_documented_floor_rejects_honest_indicator_provinces_at_the_nominal_rate(
    noise_sd, noise_in_levels, response
):
    floor, test = _design()
    rng = np.random.default_rng(
        [3302, int(noise_sd * 10), int(noise_in_levels), int(response * 10)]
    )
    growth, proxy, reported = _indicator_provinces(
        rng, response=response, noise_sd=noise_sd, noise_in_levels=noise_in_levels
    )
    assert reported.equals(growth)  # honest: the report is real growth

    known = test(growth, _known_response(floor, growth, proxy, response))
    rate = _rejection_rate(known)
    assert SIZE_BAND[0] <= rate <= SIZE_BAND[1], f"c known exactly: {rate:.4f}"

    # c estimated on the same provinces' earlier years, which do not overlap the tested ones,
    # with its standard error carried into the statistic, and with the provinces' response the
    # same in both windows. It then never rejects more often than nominal; a response that
    # moved between the windows does, and is tested separately below. Once the proxy is
    # noisier than output, twelve earlier years pin c down poorly, some provinces lose their
    # floor altogether, and the test turns conservative: honest provinces are still safe, but
    # power is lost, which is the price of a per-province c.
    earlier_growth, earlier_proxy, _ = _indicator_provinces(
        rng,
        response=response,
        noise_sd=noise_sd,
        noise_in_levels=noise_in_levels,
        years=EARLIER_YEARS,
    )
    earlier, usable = _earlier_response(earlier_growth, earlier_proxy)
    estimated = test(
        growth[usable],
        floor(
            growth[usable],
            proxy[usable],
            proxy_response=earlier["slope"],
            response_se=earlier["slope_se"],
            response_years=EARLIER_RANGE,
            response_source="synthetic: least squares on the earlier window",
        ),
    )
    rate = _rejection_rate(estimated)
    assert rate <= SIZE_BAND[1], f"c estimated on earlier years: {rate:.4f}"
    proxy_growth_noise_sd = noise_sd * (np.sqrt(2.0) if noise_in_levels else 1.0)
    if proxy_growth_noise_sd <= GROWTH_SD:
        assert rate >= SIZE_BAND[0], f"c estimated on earlier years: {rate:.4f}"


def test_the_driver_bound_it_replaced_has_the_wrong_size_on_the_same_draws():
    """The two specifications the old design allowed, through the library's own functions.

    With the true structural elasticity ``1 / c`` the driver bound rejects most honest
    provinces once the proxy is noisy. With the elasticity fitted by least squares of growth
    on the proxy over the tested window, the floor is ``r**2 * s2`` and the statistic is
    ``df / r**2 >= df``, so the p-value is above one half for every province: a test that
    cannot reject, fabricated or not.
    """
    floor, test = _design()
    rng = np.random.default_rng(3303)
    growth, proxy, _ = _indicator_provinces(rng, response=1.0, noise_sd=2.4, noise_in_levels=False)

    documented = _rejection_rate(test(growth, _known_response(floor, growth, proxy, 1.0)))
    assert SIZE_BAND[0] <= documented <= SIZE_BAND[1]

    sample = growth.columns[:310]  # the library tests one series at a time
    structural, fitted = [], []
    for province in sample:
        y, p = growth[province].to_numpy(), proxy[province].to_numpy()
        structural.append(variance_floor_test(y, implied_variance_floor(p, 1.0)).pvalue)
        same_window = np.cov(y, p)[0, 1] / np.var(p, ddof=1)
        fitted.append(variance_floor_test(y, implied_variance_floor(p, same_window)).pvalue)
    assert np.mean(np.asarray(structural) < ALPHA) > 0.5
    assert min(fitted) > 0.5


def test_the_floor_needs_the_slope_test_and_the_response_error_to_hold_its_size():
    """Why the test is on the slope, and why ``response_se`` is required.

    The covariance floor is estimated on the window it bounds, so the chi-square null of the
    library's variance-floor test, which takes the floor as fixed in advance, does not
    describe it: at low proxy noise that test almost never rejects an honest province. And an
    estimated ``c`` passed as though it were exact rejects honest provinces too often.
    """
    floor, test = _design()
    rng = np.random.default_rng(3304)
    growth, proxy, _ = _indicator_provinces(rng, response=1.0, noise_sd=0.3, noise_in_levels=False)
    floors = _known_response(floor, growth, proxy, 1.0)
    assert SIZE_BAND[0] <= _rejection_rate(test(growth, floors)) <= SIZE_BAND[1]
    sample = growth.columns[:310]  # the library tests one series at a time
    chi_square = [
        variance_floor_test(growth[province].to_numpy(), floors.at[province, "floor"]).pvalue
        for province in sample
    ]
    assert np.mean(np.asarray(chi_square) < ALPHA) < 0.01

    earlier_growth, earlier_proxy, _ = _indicator_provinces(
        rng, response=1.0, noise_sd=1.2, noise_in_levels=False, years=EARLIER_YEARS
    )
    growth, proxy, _ = _indicator_provinces(rng, response=1.0, noise_sd=1.2, noise_in_levels=False)
    earlier, usable = _earlier_response(earlier_growth, earlier_proxy)
    growth, proxy = growth[usable], proxy[usable]
    as_if_exact = floor(
        growth,
        proxy,
        proxy_response=earlier["slope"],
        response_se=0.0,
        response_years=EARLIER_RANGE,
        response_source="synthetic: least squares on the earlier window, error dropped",
    )
    assert _rejection_rate(test(growth, as_if_exact)) > SIZE_BAND[1] + 0.02


def test_the_documented_floor_flags_a_smoothed_report_and_not_a_smoothed_economy():
    """The separation the module docstring promises, on a proxy with little noise of its own.

    A report pulled halfway to the mean while the proxy keeps tracking real growth is
    flagged almost every time. An economy that was itself smoothed, report and proxy alike,
    is honest and is rejected at the nominal rate.
    """
    floor, test = _design()
    rng = np.random.default_rng(3305)

    real, proxy, smoothed_report = _indicator_provinces(
        rng, response=1.0, noise_sd=0.3, noise_in_levels=False, smoothing=0.5
    )
    assert not smoothed_report.equals(real)
    flagged = test(smoothed_report, _known_response(floor, smoothed_report, proxy, 1.0))
    assert _rejection_rate(flagged) > 0.9

    smoothed_real = GROWTH_MEAN + 0.5 * (real - GROWTH_MEAN)
    smoothed_proxy = 1.0 * smoothed_real + (proxy - 1.0 * real)  # same proxy noise
    honest = test(smoothed_real, _known_response(floor, smoothed_real, smoothed_proxy, 1.0))
    assert SIZE_BAND[0] <= _rejection_rate(honest) <= SIZE_BAND[1]


@pytest.mark.parametrize("noise_sd", [0.3, 1.2])
@pytest.mark.parametrize("drift", [0.8, 1.2], ids=["response-fell", "response-rose"])
def test_a_response_that_moved_between_the_windows_shifts_the_size(drift, noise_sd):
    """Why ``c`` has to be the response in the tested window, not only estimated outside it.

    The size test above keeps the provinces' response the same in both windows. Here it is 1
    in the earlier window and ``drift`` in the tested one, and ``c`` is estimated on the
    earlier window as before. A response that rose rejects honest provinces more often than
    nominal, at low and high proxy noise alike. One that fell makes the test conservative.
    """
    floor, test = _design()
    rng = np.random.default_rng([3306, int(drift * 10), int(noise_sd * 10)])
    earlier_growth, earlier_proxy, _ = _indicator_provinces(
        rng, response=1.0, noise_sd=noise_sd, noise_in_levels=False, years=EARLIER_YEARS
    )
    growth, proxy, _ = _indicator_provinces(
        rng, response=drift, noise_sd=noise_sd, noise_in_levels=False
    )
    result, _ = _against_earlier_response(floor, test, growth, proxy, earlier_growth, earlier_proxy)
    rate = _rejection_rate(result)
    if drift > 1:
        assert rate > SIZE_BAND[1], f"response rose to {drift}: {rate:.4f}"
    else:
        assert rate < SIZE_BAND[0], f"response fell to {drift}: {rate:.4f}"


@pytest.mark.parametrize("noise_sd", [0.3, 1.2])
@pytest.mark.parametrize(
    ("growth_ar", "noise_ar"),
    [(0.7, 0.0), (0.0, 0.7), (0.7, 0.7)],
    ids=["persistent-growth", "persistent-proxy-noise", "both-persistent"],
)
def test_the_slope_test_holds_its_size_only_if_growth_and_proxy_noise_are_not_both_persistent(
    growth_ar, noise_ar, noise_sd
):
    """The serial-independence precondition ``underdispersion_by_province`` states.

    Every other test here draws growth and proxy noise independently year to year. With
    ``c`` known, persistence in one of them leaves the size at nominal. Persistence in both
    makes the least-squares standard error of the slope too small, and honest provinces are
    rejected too often.
    """
    floor, test = _design()
    rng = np.random.default_rng([3307, int(growth_ar * 10), int(noise_ar * 10), int(noise_sd * 10)])
    real = GROWTH_MEAN + _persistent(rng, growth_ar, GROWTH_SD)
    growth = _frame(real, TESTED_YEARS)
    proxy = _frame(1.0 * real + _persistent(rng, noise_ar, noise_sd), TESTED_YEARS)
    rate = _rejection_rate(test(growth, _known_response(floor, growth, proxy, 1.0)))
    if growth_ar and noise_ar:
        assert rate > SIZE_BAND[1] + 0.02, f"both persistent: {rate:.4f}"
    else:
        assert SIZE_BAND[0] <= rate <= SIZE_BAND[1], f"one persistent: {rate:.4f}"


def test_a_response_estimated_on_reports_smoothed_in_both_windows_absorbs_the_smoothing():
    """Why a ``c`` estimated on reported growth needs years whose reports are honest.

    A province that pulls its report halfway to the mean in the earlier window as well as the
    tested one gets an earlier-window ``c`` near twice the true response, and against that
    ``c`` it is flagged no more often than an honest province. Against the true ``c`` the
    same reports are flagged almost every time, as in the smoothed-report test above.
    """
    floor, test = _design()
    rng = np.random.default_rng(3308)
    _, earlier_proxy, earlier_report = _indicator_provinces(
        rng,
        response=1.0,
        noise_sd=0.3,
        noise_in_levels=False,
        years=EARLIER_YEARS,
        smoothing=0.5,
    )
    _, proxy, report = _indicator_provinces(
        rng, response=1.0, noise_sd=0.3, noise_in_levels=False, smoothing=0.5
    )
    assert _rejection_rate(test(report, _known_response(floor, report, proxy, 1.0))) > 0.9

    result, earlier = _against_earlier_response(
        floor, test, report, proxy, earlier_report, earlier_proxy
    )
    assert 1.8 < earlier["slope"].median() < 2.2
    assert _rejection_rate(result) <= SIZE_BAND[1]
