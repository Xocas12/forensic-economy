"""The proxy elasticity and the growth it is tested against share one price basis.

``docs/known_traps.md`` trap 4: nominal levels and real growth are different quantities and
must never be mixed. The variance floor of :func:`china.analysis.dispersion.proxy_implied_floor`
is ``elasticity**2 * Var(proxy growth)``, tested against reported growth. An elasticity fitted
on nominal levels absorbs the deflator trend, so squared against real growth it raises the
floor and flags honest provinces as too smooth. These tests pin the three things that keep the
two series on one basis: the defaults agree, the elasticity output records its outcome series,
and the floor refuses a mismatch.
"""

from __future__ import annotations

import inspect

import pytest
from china.analysis import dispersion, proxies
from china.clean.schema import SERIES


def _default(fn, name):
    return inspect.signature(fn).parameters[name].default


def test_the_default_elasticity_and_the_default_growth_share_a_price_basis():
    outcome = _default(proxies.proxy_elasticities, "outcome")
    growth = _default(dispersion.growth_series, "series")
    assert proxies.PRICE_BASIS[outcome] == proxies.PRICE_BASIS[growth] == "real"


def test_the_floor_defaults_to_the_growth_series_default():
    assert _default(dispersion.proxy_implied_floor, "series") == _default(
        dispersion.growth_series, "series"
    )


def test_every_price_basis_names_a_schema_series_and_is_nominal_or_real():
    assert set(proxies.PRICE_BASIS) <= set(SERIES)
    assert set(proxies.PRICE_BASIS.values()) == {"nominal", "real"}
    assert proxies.PRICE_BASIS["grp_nominal"] == "nominal"
    assert proxies.PRICE_BASIS["grp_index_preceding_year"] == "real"


def test_the_elasticity_output_records_its_outcome_series_and_price_basis():
    assert {"elasticity", "outcome", "price_basis"} <= set(proxies.ELASTICITY_COLUMNS)
    returns = inspect.getdoc(proxies.proxy_elasticities).split("Returns", 1)[1]
    assert "ELASTICITY_COLUMNS" in returns
    assert "``outcome``" in returns


def test_the_floor_requires_the_elasticity_outcome_to_be_stated():
    parameter = inspect.signature(dispersion.proxy_implied_floor).parameters["elasticity_outcome"]
    assert parameter.kind is parameter.KEYWORD_ONLY
    assert parameter.default is parameter.empty


def test_the_floor_refuses_a_nominal_elasticity_against_real_growth():
    with pytest.raises(ValueError, match="price basis mismatch"):
        dispersion.proxy_implied_floor(None, None, elasticity=1.5, elasticity_outcome="grp_nominal")


def test_the_floor_refuses_a_real_elasticity_against_nominal_growth():
    with pytest.raises(ValueError, match="price basis mismatch"):
        dispersion.proxy_implied_floor(
            None,
            None,
            elasticity=1.0,
            elasticity_outcome="grp_index_preceding_year",
            series="grp_nominal",
        )


def test_the_floor_refuses_a_series_with_no_recorded_price_basis():
    with pytest.raises(ValueError, match="no recorded price basis"):
        dispersion.proxy_implied_floor(
            None, None, elasticity=1.0, elasticity_outcome="electricity_consumption"
        )


@pytest.mark.parametrize(
    ("elasticity_outcome", "series"),
    [
        ("grp_index_preceding_year", "grp_index_preceding_year"),
        ("grp_nominal", "grp_nominal"),
    ],
)
def test_a_matching_price_basis_reaches_the_stub(elasticity_outcome, series):
    with pytest.raises(NotImplementedError):
        dispersion.proxy_implied_floor(
            None,
            None,
            elasticity=1.0,
            elasticity_outcome=elasticity_outcome,
            series=series,
        )
