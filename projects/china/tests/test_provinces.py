"""The province list: names that drift, rows that are not provinces, units that are not either.

Each of these is a real way to corrupt a provincial sum, and each is asserted against a
concrete value rather than against "does not crash".
"""

from __future__ import annotations

from china.clean.provinces import (
    ATTESTED_REGION_CODES,
    BOUNDARY_CHANGES,
    PROVINCES,
    REBASING_YEARS,
    SUBPROVINCIAL_UNITS,
    canonical_province,
    is_non_province_row,
    is_province,
    normalize_label,
    subprovincial_unit,
)


def test_there_are_thirty_one_provincial_level_units_and_no_duplicates():
    assert len(PROVINCES) == 31
    assert len(set(PROVINCES)) == 31


def test_the_tibet_to_xizang_rename_is_handled_in_both_spellings():
    assert canonical_province("Tibet") == "Xizang"
    assert canonical_province("Xizang") == "Xizang"
    assert canonical_province("Tibet Autonomous Region") == "Xizang"


def test_a_footnote_marker_does_not_create_a_new_province():
    assert canonical_province("Xizang a") == "Xizang"
    assert canonical_province("Inner Mongolia a)") == "Inner Mongolia"


def test_the_two_shan_provinces_do_not_collide():
    assert canonical_province("Shanxi") == "Shanxi"
    assert canonical_province("Shaanxi") == "Shaanxi"
    assert canonical_province("Shannxi") == "Shaanxi"
    assert canonical_province("Shanxi") != canonical_province("Shaanxi")


def test_aggregate_and_residual_rows_are_not_provinces():
    for label in ("National Total", "Not Classified by Region", "Total"):
        assert is_non_province_row(label)
        assert not is_province(label)
        assert canonical_province(label) is None


def test_binhai_new_area_is_recognised_as_sub_provincial_and_never_a_province():
    unit = subprovincial_unit("Binhai New Area")
    assert unit is not None
    assert unit.parent == "Tianjin"
    assert "33.4" in unit.why
    assert not is_province("Binhai New Area")
    assert canonical_province("Binhai New Area") is None


def test_shenzhen_is_the_thirty_second_central_bank_summary_and_not_a_province():
    unit = subprovincial_unit("Shenzhen")
    assert unit is not None and unit.parent == "Guangdong"
    assert not is_province("Shenzhen")


def test_every_sub_provincial_unit_has_a_real_parent():
    for unit in SUBPROVINCIAL_UNITS:
        assert unit.parent in PROVINCES
        assert unit.why.strip()


def test_an_unrecognised_label_returns_none_rather_than_a_guess():
    assert canonical_province("Provinceland") is None
    assert canonical_province("") is None


def test_normalize_label_collapses_whitespace_and_punctuation():
    assert normalize_label("  Inner  Mongolia a) ") == "inner mongolia a"
    assert normalize_label("NOT CLASSIFIED BY REGION") == "not classified by region"
    assert normalize_label("") == ""


def test_boundary_changes_and_rebasings_are_the_ones_the_traps_document_names():
    created = {change.created: change for change in BOUNDARY_CHANGES}
    assert created["Chongqing"].year == 1997
    assert created["Chongqing"].from_parent == "Sichuan"
    assert created["Hainan"].year == 1988
    assert set(REBASING_YEARS) == {2004, 2008, 2013, 2018}


def test_only_the_region_codes_read_from_the_registry_are_hard_coded():
    assert ATTESTED_REGION_CODES == {
        "Beijing": "110000",
        "Tianjin": "120000",
        "Inner Mongolia": "150000",
        "Liaoning": "210000",
    }
    assert all(name in PROVINCES for name in ATTESTED_REGION_CODES)
