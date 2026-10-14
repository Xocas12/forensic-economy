"""The seal must refuse to show the anchor, and must refuse to guess.

Every frame here is synthetic. The Uzbek rows carry obviously fake values, because a fixture
that looked like real cotton output would itself be a small violation of the thing being
tested.

Russian and Uzbek labels are written as escapes, with their transliteration in a comment,
because every source file in this repository is ASCII.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from gosplan.seal import (
    HELD_OUT,
    UNSEAL_DECLARATION,
    UNSEAL_RECORD,
    UNSEAL_TOKEN,
    HeldOut,
    SealedError,
    check_grouping,
    filter_sealed,
    held_out_mask,
    is_sealed,
    unseal,
)
from gosplan.transcribe.schema import FIELD_NAMES
from gosplan.transcribe.validate import validate_rows

_OVERRIDE = "GOSPLAN_SEAL_TEST_OVERRIDE"


def panel() -> pd.DataFrame:
    """A tiny synthetic panel: two republics, two series, six years."""
    rows = []
    for region in ("Uzbek SSR", "Kazakh SSR"):
        for series in ("cotton", "wheat"):
            for year in (1975, 1977, 1980, 1983, 1986, 1990):
                rows.append(
                    {
                        "region": region,
                        "series": series,
                        "year": year,
                        "value": 100.0,  # deliberately flat and fake
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture
def sealed(monkeypatch):
    monkeypatch.delenv(_OVERRIDE, raising=False)
    return None


@pytest.fixture
def unsealed(monkeypatch):
    monkeypatch.setenv(_OVERRIDE, "1")
    return None


# ---------------------------------------------------------------- the seal is on by default


def test_the_anchor_is_sealed_in_this_repository(sealed):
    """The whole programme depends on this being true until G3."""
    assert is_sealed() is True
    assert not UNSEAL_RECORD.exists(), (
        f"{UNSEAL_RECORD} exists, which lifts the seal. It must not be created before G3 is signed."
    )


def test_unseal_refuses_while_the_record_is_absent(sealed):
    with pytest.raises(SealedError, match="the anchor is sealed"):
        unseal(UNSEAL_TOKEN)


def test_unseal_refuses_a_wrong_token(sealed):
    with pytest.raises(SealedError, match="wrong unseal token"):
        unseal("please")


def test_there_is_no_code_path_that_creates_the_unseal_record():
    """Lifting the seal is a human act at G3. If code could write the record, the seal would
    be decoration."""
    import gosplan.seal as seal_module

    source = Path(seal_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("write_text", "open(UNSEAL_RECORD", "touch()", "mkdir"):
        assert forbidden not in source, f"seal.py contains {forbidden!r}"


# ---------------------------------------------------------------- withholding rows


def test_held_out_rows_are_exactly_the_uzbek_cotton_rows_in_window(sealed):
    df = panel()
    mask = held_out_mask(df)
    held = df.loc[mask]
    assert set(held["region"]) == {"Uzbek SSR"}
    assert set(held["series"]) == {"cotton"}
    assert set(held["year"]) == {1977, 1980, 1983}
    # 1975 and 1986 are outside the sealed window; wheat and Kazakh are untouched
    assert len(held) == 3


def test_filter_sealed_drops_them_and_says_how_many(sealed):
    df = panel()
    out, n = filter_sealed(df)
    assert n == 3
    assert len(out) == len(df) - 3
    assert not held_out_mask(out).any()


def test_the_window_is_wider_than_the_affair_itself():
    """1978 to 1983 is the affair; the seal covers 1976 to 1985, because a detector tuned on
    the shoulder years is still tuned around the anchor."""
    assert HELD_OUT.years.start < 1978
    assert HELD_OUT.years.stop - 1 > 1983
    assert HELD_OUT.matches("Uzbek SSR", "cotton", 1977) is True
    assert HELD_OUT.matches("Uzbek SSR", "cotton", 1985) is True
    assert HELD_OUT.matches("Uzbek SSR", "cotton", 1975) is False
    assert HELD_OUT.matches("Uzbek SSR", "cotton", 1986) is False


def test_region_and_series_matching_is_forgiving_about_spelling():
    for region in ("Uzbek SSR", "uzbekistan", "Uzbekskaya SSR", "UZBEK"):
        assert HELD_OUT.matches(region, "seed cotton, unginned", 1980) is True
    assert HELD_OUT.matches("Kazakh SSR", "cotton", 1980) is False
    assert HELD_OUT.matches("Uzbek SSR", "wheat", 1980) is False


def test_a_missing_year_never_matches():
    assert HELD_OUT.matches("Uzbek SSR", "cotton", None) is False
    assert HELD_OUT.matches("Uzbek SSR", "cotton", float("nan")) is False


# ---------------------------------------------------------------- refusing to guess


def test_a_frame_that_cannot_be_checked_is_refused_not_waved_through(sealed):
    """The dangerous case: a table with no region column may itself BE the Uzbek series."""
    df = pd.DataFrame({"year": [1980, 1981], "value": [1.0, 2.0]})
    with pytest.raises(SealedError, match="cannot tell whether this frame"):
        held_out_mask(df)
    with pytest.raises(SealedError, match="cannot tell whether this frame"):
        filter_sealed(df)


def test_declare_clean_is_an_assertion_by_the_caller_not_a_bypass(sealed):
    df = pd.DataFrame({"year": [1980, 1981], "value": [1.0, 2.0]})
    out, n = filter_sealed(df, declare_clean=True)
    assert n == 0
    assert len(out) == 2
    # It does not lift the seal for anything else.
    assert is_sealed() is True
    with pytest.raises(SealedError):
        held_out_mask(pd.DataFrame({"year": [1980]}))


# ---------------------------------------------------------------- aggregate vs breakdown


def test_an_aggregate_that_merely_contains_the_anchor_is_allowed(sealed):
    """A union-level total contains the Uzbek figure but does not reveal it."""
    df = panel()
    check_grouping(df, "year")
    check_grouping(df, ["series", "year"])


def test_a_breakdown_that_isolates_the_anchor_is_refused(sealed):
    df = panel()
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, "region")
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, ["region", "year"])


def test_grouping_by_region_is_fine_once_the_rows_are_withheld(sealed):
    """The intended workflow: filter first, report the count, then group freely."""
    df, n = filter_sealed(panel())
    assert n == 3
    check_grouping(df, ["region", "year"])


def test_grouping_by_region_is_fine_when_no_held_out_rows_are_present(sealed):
    df = panel()
    df = df[df["region"] == "Kazakh SSR"]
    check_grouping(df, "region")


# ---------------------------------------------------------------- the unsealed path


def test_everything_opens_once_the_seal_is_lifted(unsealed):
    df = panel()
    assert is_sealed() is False
    unseal(UNSEAL_TOKEN)
    out, n = filter_sealed(df)
    assert n == 0
    assert len(out) == len(df)
    check_grouping(df, "region")
    # held_out_mask still IDENTIFIES the anchor rows once unsealed, and must: a later task needs it
    # to build the anchor_holdout split. It is filter_sealed that stops withholding them.
    assert held_out_mask(df).sum() == 3


def test_a_wrong_token_still_fails_when_unsealed(unsealed):
    """The token check is about calling the function correctly, not about the seal state."""
    with pytest.raises(SealedError, match="wrong unseal token"):
        unseal("nope")


def test_the_declaration_string_is_what_the_record_must_carry():
    """Pinned so the record cannot be satisfied by an empty or accidental file."""
    assert "G3" in UNSEAL_DECLARATION
    assert "UNSEALED" in UNSEAL_DECLARATION


# ---------------------------------------------------------------- configurability


def test_a_different_held_out_set_can_be_passed_without_touching_the_default(sealed):
    other = HeldOut(series="wheat", region=("kazakh",), years=range(1980, 1982))
    df = panel()
    mask = held_out_mask(df, held_out=other)
    held = df.loc[mask]
    assert set(held["region"]) == {"Kazakh SSR"}
    assert set(held["series"]) == {"wheat"}
    assert set(held["year"]) == {1980}
    # the real seal is unchanged
    assert HELD_OUT.series == "cotton"


# ---------------------------------------------------------------- transcribed tables
#
# The anchor's material arrives as transcribed Russian tables: Cyrillic stubs, a Russian heading
# and its transliteration, plan periods and crop years, tables by oblast. Each case below is one
# of those, read the way the transcription template records it.

USSR_RU = "\u0421\u0421\u0421\u0420"  # SSSR
UZBEK_RU = (
    "\u0423\u0437\u0431\u0435\u043a\u0441\u043a\u0430\u044f \u0421\u0421\u0420"  # Uzbekskaia SSR
)
TURKMEN_RU = "\u0422\u0443\u0440\u043a\u043c\u0435\u043d\u0441\u043a\u0430\u044f \u0421\u0421\u0420"  # Turkmenskaia SSR
CENTRAL_ASIA_RU = (
    "\u0421\u0440\u0435\u0434\u043d\u044f\u044f \u0410\u0437\u0438\u044f"  # Sredniaia Aziia
)
RAW_COTTON_TITLE_RU = (  # Proizvodstvo khlopka-syrtsa
    "\u041f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u043e "
    "\u0445\u043b\u043e\u043f\u043a\u0430-\u0441\u044b\u0440\u0446\u0430"
)
RAW_COTTON_RU = (
    "\u0425\u043b\u043e\u043f\u043e\u043a-\u0441\u044b\u0440\u0435\u0446"  # Khlopok-syrets
)
GRAIN_TITLE_RU = (  # Proizvodstvo zerna
    "\u041f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u043e "
    "\u0437\u0435\u0440\u043d\u0430"
)
WHEAT_RU = "\u041f\u0448\u0435\u043d\u0438\u0446\u0430"  # Pshenitsa
KOLKHOZY_RU = "\u041a\u043e\u043b\u0445\u043e\u0437\u044b"  # Kolkhozy
SOVKHOZY_RU = "\u0421\u043e\u0432\u0445\u043e\u0437\u044b"  # Sovkhozy
THOUSAND_TONNES_RU = "\u0442\u044b\u0441. \u0442"  # tys. t
PAKHTA_UZ = "\u043f\u0430\u0445\u0442\u0430"  # pakhta, Uzbek for cotton
GEORGIA_KA = (
    "\u10e1\u10d0\u10e5\u10d0\u10e0\u10d7\u10d5\u10d4\u10da\u10dd"  # Sakartvelo, Georgian script
)

#: Every unit of the Uzbek SSR, as Russian tables print it, as the Uzbek-language press prints it,
#: and in the Latin spellings a transcriber or a source might use: this project's translit, ISO 9
#: and scholarly (with their diacritics), English, and Uzbek Latin.
UZBEK_SSR_IN_PRINT: dict[str, tuple[str, ...]] = {
    "Uzbek SSR": (
        UZBEK_RU,
        "\u040e\u0437\u0431\u0435\u043a\u0438\u0441\u0442\u043e\u043d \u0421\u0421\u0420",  # O'zbekiston SSR
        "\u0423\u0437\u0421\u0421\u0420",  # UzSSR
        "\u0423\u0437\u0431. \u0421\u0421\u0420",  # Uzb. SSR
        "Uzbekskaya SSR",
        "Uzbekskaja SSR",
        "Narodnoe khoziaistvo Uzbekskoi SSR",
        "O'zbekiston SSR",
        "O\u02bbzbekiston",
        "Usbekische SSR",
        "Uz. SSR",
    ),
    "Karakalpak ASSR": (
        "\u041a\u0430\u0440\u0430\u043a\u0430\u043b\u043f\u0430\u043a\u0441\u043a\u0430\u044f \u0410\u0421\u0421\u0420",
        "\u049a\u043e\u0440\u0430\u049b\u0430\u043b\u043f\u043e\u0493\u0438\u0441\u0442\u043e\u043d \u0410\u0421\u0421\u0420",
        "Karakalpakskaya ASSR",
        "Kara-Kalpak ASSR",
        "Qoraqalpog'iston",
        "Karakalpakstan",
    ),
    "Andijan oblast": (
        "\u0410\u043d\u0434\u0438\u0436\u0430\u043d\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0410\u043d\u0434\u0438\u0436\u043e\u043d \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Andizhanskaya oblast'",
        "Andi\u017eanskaja oblast\u02b9",
        "Andijan",
        "Andijon viloyati",
        "Andidjan",
    ),
    "Bukhara oblast": (
        "\u0411\u0443\u0445\u0430\u0440\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0411\u0443\u0445\u043e\u0440\u043e \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Bukharskaya oblast",
        "Buharskaja oblast\u02b9",
        "Buxarskaja oblast\u02b9",
        "Bukhara",
        "Buxoro viloyati",
    ),
    "Jizzakh oblast": (
        "\u0414\u0436\u0438\u0437\u0430\u043a\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0416\u0438\u0437\u0437\u0430\u0445 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Dzhizakskaya oblast",
        "D\u017eizakskaja oblast\u02b9",
        "Jizzakh",
        "Jizzax viloyati",
        "Djizak",
    ),
    "Kashkadarya oblast": (
        "\u041a\u0430\u0448\u043a\u0430\u0434\u0430\u0440\u044c\u0438\u043d\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u049a\u0430\u0448\u049b\u0430\u0434\u0430\u0440\u0451 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Kashkadar'inskaya oblast",
        "Ka\u0161kadar\u02b9inskaja oblast\u02b9",
        "Kashka-Darya",
        "Qashqadaryo viloyati",
    ),
    "Khorezm oblast": (
        "\u0425\u043e\u0440\u0435\u0437\u043c\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0425\u043e\u0440\u0430\u0437\u043c \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Khorezmskaya oblast",
        "Horezmskaja oblast\u02b9",
        "Xorezmskaja oblast\u02b9",
        "Khwarazm",
        "Xorazm viloyati",
    ),
    "Namangan oblast": (
        "\u041d\u0430\u043c\u0430\u043d\u0433\u0430\u043d\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u041d\u0430\u043c\u0430\u043d\u0433\u0430\u043d \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Namanganskaya oblast",
        "Namangan viloyati",
    ),
    "Navoi oblast": (
        "\u041d\u0430\u0432\u043e\u0438\u0439\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u041d\u0430\u0432\u043e\u0438\u0439 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Navoiyskaya oblast",
        "Navoi",
        "Navoiy viloyati",
    ),
    "Samarkand oblast": (
        "\u0421\u0430\u043c\u0430\u0440\u043a\u0430\u043d\u0434\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0421\u0430\u043c\u0430\u0440\u049b\u0430\u043d\u0434 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Samarkandskaya oblast",
        "Samarqand viloyati",
    ),
    "Surkhandarya oblast": (
        "\u0421\u0443\u0440\u0445\u0430\u043d\u0434\u0430\u0440\u044c\u0438\u043d\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0421\u0443\u0440\u0445\u043e\u043d\u0434\u0430\u0440\u0451 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Surkhandar'inskaya oblast",
        "Surhandar\u02b9inskaja oblast\u02b9",
        "Surxandar\u02b9inskaja oblast\u02b9",
        "Surxondaryo viloyati",
    ),
    "Syrdarya oblast": (
        "\u0421\u044b\u0440\u0434\u0430\u0440\u044c\u0438\u043d\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0421\u0438\u0440\u0434\u0430\u0440\u0451 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Syrdar'inskaya oblast",
        "Syr-Darya",
        "Sirdaryo viloyati",
    ),
    "Tashkent oblast and city": (
        "\u0433. \u0422\u0430\u0448\u043a\u0435\u043d\u0442",
        "\u0422\u043e\u0448\u043a\u0435\u043d\u0442 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Tashkentskaya oblast",
        "Ta\u0161kentskaja oblast\u02b9",
        "g. Tashkent",
    ),
    "Fergana oblast": (
        "\u0424\u0435\u0440\u0433\u0430\u043d\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",
        "\u0424\u0430\u0440\u0493\u043e\u043d\u0430 \u0432\u0438\u043b\u043e\u044f\u0442\u0438",
        "Ferganskaya oblast",
        "Ferghana",
        "Farg'ona viloyati",
        "Farg\u02bbona viloyati",
    ),
}

#: The other fourteen republics and the union, in Russian, and places that are not the anchor
#: but sit next to it on a map or in a string.
NOT_THE_ANCHOR_IN_PRINT: tuple[str, ...] = (
    USSR_RU,
    "\u0420\u0421\u0424\u0421\u0420",  # RSFSR
    "\u0423\u043a\u0440\u0430\u0438\u043d\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Ukrainskaia SSR
    "\u0411\u0435\u043b\u043e\u0440\u0443\u0441\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Belorusskaia SSR
    "\u041a\u0430\u0437\u0430\u0445\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Kazakhskaia SSR
    "\u0413\u0440\u0443\u0437\u0438\u043d\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Gruzinskaia SSR
    "\u0410\u0437\u0435\u0440\u0431\u0430\u0439\u0434\u0436\u0430\u043d\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Azerbaidzhanskaia SSR
    "\u041b\u0438\u0442\u043e\u0432\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Litovskaia SSR
    "\u041c\u043e\u043b\u0434\u0430\u0432\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Moldavskaia SSR
    "\u041b\u0430\u0442\u0432\u0438\u0439\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Latviiskaia SSR
    "\u041a\u0438\u0440\u0433\u0438\u0437\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Kirgizskaia SSR
    "\u0422\u0430\u0434\u0436\u0438\u043a\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Tadzhikskaia SSR
    "\u0410\u0440\u043c\u044f\u043d\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Armianskaia SSR
    TURKMEN_RU,
    "\u042d\u0441\u0442\u043e\u043d\u0441\u043a\u0430\u044f \u0421\u0421\u0420",  # Estonskaia SSR
    "\u0427\u0438\u043c\u043a\u0435\u043d\u0442\u0441\u043a\u0430\u044f \u043e\u0431\u043b\u0430\u0441\u0442\u044c",  # Chimkentskaia oblast, Kazakh SSR
    "Turkmen SSR",
    "Tadzhikskaya SSR",
    "Kuzbass",  # holds "uz" and "uzb" inside a word, which must not count
)

_SYNTHETIC_UNION_VOLUME = "SYNTHETIC FIXTURE, Narodnoe khoziaistvo SSSR"

#: Five periods of the table the issue reproduced: one year either side of the window, a year
#: inside it, and the two plan periods that cover it.
_PERIODS = ("1975", "1976-1980", "1980", "1981-1985", "1985")
_IN_WINDOW = {"1976-1980", "1980", "1981-1985", "1985"}


def transcription_rows(
    cells: list[dict[str, str]],
    *,
    title_ru: str = RAW_COTTON_TITLE_RU,
    title_translit: str = "Proizvodstvo khlopka-syrtsa",
    volume: str = _SYNTHETIC_UNION_VOLUME,
) -> list[dict[str, str]]:
    """Rows in the transcription template's own columns, as ``read_filled`` returns them."""
    rows = []
    for cell in cells:
        row = dict.fromkeys(FIELD_NAMES, "")
        row.update(
            source_id="ia_narkhoz_1985_item",
            volume=volume,
            edition_year="1985",
            page="1",
            table_number="T-28",
            title_ru=title_ru,
            title_translit=title_translit,
            territorial_basis="present_boundaries",
            transcriber="TEST",
            transcription_date="2026-10-14",
            unit=THOUSAND_TONNES_RU,
            currency_basis="not_monetary",
            row_role="data",
            column_role="data",
            confidence="clear",
        )
        row.update(cell)
        row["value"] = row["value"] or row["value_raw"]
        rows.append(row)
    return rows


def as_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    """A frame of transcription rows, after checking the validator accepts them as they are."""
    report = validate_rows(rows, name="synthetic")
    assert report.ok, [str(i) for i in report.errors]
    return pd.DataFrame(rows, columns=list(FIELD_NAMES))


def by_republic_table() -> pd.DataFrame:
    """The issue's 15-row table: the union total, Uzbek SSR and Turkmen SSR by period, labels
    in Cyrillic, every column head a period. Values are fake; the total is their sum so the
    validator's total check passes."""
    cells = []
    for period in _PERIODS:
        for label, translit, role, value in (
            (USSR_RU, "SSSR", "total", "2"),
            (UZBEK_RU, "Uzbekskaia SSR", "data", "1"),
            (TURKMEN_RU, "Turkmenskaia SSR", "data", "1"),
        ):
            cells.append(
                {
                    "row_label": label,
                    "row_label_translit": translit,
                    "column_label": period,
                    "period": period,
                    "value_raw": value,
                    "value": value,
                    "row_role": role,
                }
            )
    return as_frame(transcription_rows(cells))


def _kept(frame: pd.DataFrame) -> set[tuple[str, str]]:
    return set(zip(frame["row_label_translit"], frame["period"], strict=True))


def test_cyrillic_labels_and_heading_identify_the_anchor():
    assert HELD_OUT.matches(UZBEK_RU, RAW_COTTON_TITLE_RU, 1980) is True
    assert HELD_OUT.matches(UZBEK_RU, RAW_COTTON_RU, "1980") is True
    assert HELD_OUT.matches(UZBEK_RU, GRAIN_TITLE_RU, 1980) is False
    assert HELD_OUT.matches(TURKMEN_RU, RAW_COTTON_TITLE_RU, 1980) is False


@pytest.mark.parametrize(
    ("region", "series"),
    [
        ("Uzbekskaya SSR", "Khlopok-syrets"),  # the issue's case
        ("Uzbekskaia SSR", "Proizvodstvo khlopka-syrtsa"),  # this project's transliteration
        ("Uzbekskaja SSR", "Proizvodstvo hlopka-syrca"),  # ISO 9, diacritics dropped
        ("Uzbekskaja SSR", "Proizvodstvo xlopka-syrca"),  # scholarly x
        ("Usbekische SSR", "Chlopok"),
        ("O'zbekiston SSR", "paxta"),
        ("Uz. SSR", "seed cotton"),
    ],
)
def test_transliterated_labels_and_headings_identify_the_anchor(region, series):
    assert HELD_OUT.matches(region, series, 1980) is True
    assert HELD_OUT.matches(region, series, 1990) is False


@pytest.mark.parametrize("series", [RAW_COTTON_TITLE_RU, RAW_COTTON_RU, PAKHTA_UZ, "Xlopok"])
def test_cotton_in_russian_and_uzbek_is_the_held_out_series(series):
    assert HELD_OUT.matches("Uzbek SSR", series, 1980) is True


@pytest.mark.parametrize("series", [GRAIN_TITLE_RU, WHEAT_RU, "Proizvodstvo zerna"])
def test_other_series_in_russian_are_not_held_out(series):
    assert HELD_OUT.matches(UZBEK_RU, series, 1980) is False


@pytest.mark.parametrize(
    ("label", "part"),
    [(label, part) for part, labels in UZBEK_SSR_IN_PRINT.items() for label in labels],
)
def test_every_part_of_the_republic_is_the_anchor_however_it_is_spelled(label, part):
    """A table by oblast is a breakdown of the anchor: each oblast row is the anchor too."""
    assert HELD_OUT.matches(label, RAW_COTTON_TITLE_RU, 1980) is True, part
    assert HELD_OUT.matches(label, "raw cotton", 1980) is True, part
    assert HELD_OUT.matches(label, WHEAT_RU, 1980) is False, part


def test_the_spellings_tested_cover_every_part_the_seal_names():
    from gosplan.seal import UZBEK_SSR_PARTS

    assert set(UZBEK_SSR_IN_PRINT) == set(UZBEK_SSR_PARTS)


@pytest.mark.parametrize("label", NOT_THE_ANCHOR_IN_PRINT)
def test_other_republics_and_the_union_are_not_the_anchor(sealed, label):
    """Read, and read as something else: not merely 'could not tell'."""
    assert HELD_OUT.matches(label, RAW_COTTON_TITLE_RU, 1980) is False
    df = pd.DataFrame({"region": [label], "series": [RAW_COTTON_TITLE_RU], "year": [1980]})
    assert not held_out_mask(df).any()


def test_the_vocabulary_is_written_in_the_form_labels_are_folded_to():
    """A form that does not survive folding unchanged could never match anything."""
    from gosplan.seal import COTTON, UZBEK_SSR, fold_label

    for form in (*UZBEK_SSR, *COTTON):
        assert "".join(fold_label(form)) == form, form
    assert UZBEK_SSR[0] == "uzbek"  # error messages name the region by its first form


@pytest.mark.parametrize(
    ("period", "held"),
    [
        ("1976-1980", True),
        ("1981-1985", True),
        ("1971-1980", True),
        ("1984/85", True),
        ("1975/76", True),  # a crop year reaching into the window is sealed whole
        ("1985/86", True),
        ("1971-1975", False),
        ("1986-1990", False),
        ("1974/75", False),
        ("1986/87", False),
    ],
)
def test_plan_periods_and_crop_years_that_overlap_the_window_are_held_out(sealed, period, held):
    assert HELD_OUT.matches("Uzbek SSR", "cotton", period) is held
    df = pd.DataFrame({"region": ["Uzbek SSR"], "series": ["raw cotton"], "year": [period]})
    _, n = filter_sealed(df)
    assert n == int(held)
    if held:
        with pytest.raises(SealedError, match="would isolate the held-out anchor"):
            check_grouping(df, ["region", "year"])
    else:
        check_grouping(df, ["region", "year"])


@pytest.mark.parametrize(
    ("period", "held"),
    [
        ("1976-1980", True),
        ("1981-1985", True),
        ("1984/85", True),
        ("1975/76", True),
        ("1985/86", True),
        ("1971-1975", False),
        ("1974/75", False),
        ("1986/87", False),
    ],
)
def test_a_transcribed_plan_period_or_crop_year_column_is_held_out(sealed, period, held):
    """The same periods as printed column heads of a Cyrillic by-republic table."""
    df = as_frame(
        transcription_rows(
            [
                {
                    "row_label": label,
                    "column_label": period,
                    "period": period,
                    "value_raw": value,
                    "row_role": role,
                }
                for label, role, value in (
                    (USSR_RU, "total", "2"),
                    (UZBEK_RU, "data", "1"),
                    (TURKMEN_RU, "data", "1"),
                )
            ]
        )
    )
    out, n = filter_sealed(df)
    assert (UZBEK_RU in set(out["row_label"])) is not held
    assert n == (2 if held else 0)  # the Uzbek cell and the union total printed beside it
    if held:
        with pytest.raises(SealedError, match="would isolate the held-out anchor"):
            check_grouping(df, "row_label")
    else:
        check_grouping(df, "row_label")
    check_grouping(out, "row_label")


def test_the_seal_reads_periods_with_the_validators_parser():
    import gosplan.seal as seal_module
    from gosplan.transcribe.validate import period_years

    assert seal_module.period_years is period_years


def test_english_labels_with_plan_periods_are_withheld_and_the_breakdown_refused(sealed):
    """The issue's last case: only the single-year rows used to go, and the by-republic
    breakdown was then allowed with both plan-period cells still in it."""
    rows = [
        {"region": region, "series": "raw cotton", "year": period, "value": 1.0}
        for region in ("Uzbek SSR", "Turkmen SSR")
        for period in _PERIODS
    ]
    df = pd.DataFrame(rows)
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, ["region", "year"])
    out, n = filter_sealed(df)
    assert n == 4
    assert set(out.loc[out["region"] == "Uzbek SSR", "year"]) == {"1975"}
    check_grouping(out, ["region", "year"])


@pytest.mark.parametrize(
    "columns",
    [
        {},  # the defaults: a transcription is recognised by its own columns
        {"region_col": "row_label", "series_col": "title_ru", "year_col": "period"},
        {"region_col": "row_label_translit", "series_col": "title_translit", "year_col": "period"},
    ],
)
def test_a_cyrillic_by_republic_table_loses_every_anchor_cell(sealed, columns):
    """The issue's table, withheld 0 of 15 before. Every Uzbek cell in the window goes, with
    the union total printed beside it; the other republic stays whole."""
    df = by_republic_table()
    out, n = filter_sealed(df, **columns)
    kept = _kept(out)
    assert not {("Uzbekskaia SSR", p) for p in _IN_WINDOW} & kept
    assert ("Uzbekskaia SSR", "1975") in kept
    assert {("Turkmenskaia SSR", p) for p in _PERIODS} <= kept
    assert not {("SSSR", p) for p in _IN_WINDOW} & kept
    assert ("SSSR", "1975") in kept
    assert n == 8
    assert not held_out_mask(out, **columns).any()


@pytest.mark.parametrize("by", ["row_label", ["row_label", "period"], "row_label_translit"])
def test_a_cyrillic_by_republic_table_cannot_be_broken_down_by_republic(sealed, by):
    df = by_republic_table()
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, by)
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, by, region_col="row_label", series_col="title_ru", year_col="period")
    out, _ = filter_sealed(df)
    check_grouping(out, by)


def test_a_by_republic_table_may_still_be_aggregated(sealed):
    check_grouping(by_republic_table(), "period")


def test_the_transliterated_columns_alone_are_enough(sealed):
    """A frame carrying only the transliterations is read through them."""
    df = by_republic_table()[["row_label_translit", "title_translit", "period", "value"]]
    cols = {
        "region_col": "row_label_translit",
        "series_col": "title_translit",
        "year_col": "period",
    }
    out, n = filter_sealed(df, **cols)
    assert n == 4
    assert set(out.loc[out["row_label_translit"] == "Uzbekskaia SSR", "period"]) == {"1975"}
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, "row_label_translit", **cols)


def test_a_table_by_oblast_loses_every_oblast_row(sealed):
    """Rows for the Karakalpak ASSR and each oblast, in Russian, under the republic's total."""
    parts = [labels[0] for part, labels in UZBEK_SSR_IN_PRINT.items() if part != "Uzbek SSR"]
    cells = []
    for period in ("1980", "1990"):
        cells.append(
            {
                "row_label": UZBEK_RU,
                "column_label": period,
                "period": period,
                "value_raw": str(len(parts)),
                "row_role": "total",
            }
        )
        cells.extend(
            {"row_label": label, "column_label": period, "period": period, "value_raw": "1"}
            for label in parts
        )
    df = as_frame(transcription_rows(cells))
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, "row_label")
    out, n = filter_sealed(df)
    assert n == len(parts) + 1
    assert set(out["period"]) == {"1990"}
    check_grouping(out, "row_label")


def test_republics_printed_as_columns_are_read_from_the_column_heads(sealed):
    """Products as rows, republics as columns, a heading that names neither."""
    cells = []
    for period in ("1980", "1990"):
        for product in (RAW_COTTON_RU, WHEAT_RU):
            for label, role in ((USSR_RU, "total"), (UZBEK_RU, "data"), (TURKMEN_RU, "data")):
                cells.append(
                    {
                        "row_label": product,
                        "column_label": label,
                        "period": period,
                        "value_raw": "2" if role == "total" else "1",
                        "column_role": role,
                    }
                )
    df = as_frame(
        transcription_rows(
            cells, title_ru="SINTETICHESKAIA TABLITSA", title_translit="Synthetic table"
        )
    )
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, "column_label")
    out, n = filter_sealed(df)
    gone = df.loc[~df.index.isin(out.index), ["row_label", "column_label", "period"]]
    assert sorted(map(tuple, gone.to_numpy())) == sorted(
        [(RAW_COTTON_RU, UZBEK_RU, "1980"), (RAW_COTTON_RU, USSR_RU, "1980")]
    )
    assert n == 2
    check_grouping(out, "column_label")


def test_a_republic_annual_is_the_anchor_whatever_its_rows_are_called(sealed):
    """In the republic's own annual the region is named on the title page, not in the rows."""
    cells = [
        {"row_label": label, "column_label": period, "period": period, "value_raw": "1"}
        for label in (KOLKHOZY_RU, SOVKHOZY_RU)
        for period in ("1975", "1980")
    ]
    df = as_frame(
        transcription_rows(
            cells, volume="SYNTHETIC FIXTURE, Narodnoe khoziaistvo Uzbekskoi SSR v 1980 g."
        )
    )
    with pytest.raises(SealedError, match="would isolate the held-out anchor"):
        check_grouping(df, ["row_label", "period"])
    out, n = filter_sealed(df)
    assert n == 2
    assert set(out["period"]) == {"1975"}


# ---------------------------------------------------------------- failing closed on values


@pytest.mark.parametrize(
    ("region", "series", "year"),
    [
        (GEORGIA_KA, "raw cotton", 1980),  # a script the seal cannot read
        ("235", "raw cotton", 1980),  # a numeric area code names nothing
        (None, "raw cotton", 1980),
        ("", "raw cotton", 1980),
        ("Uzbek SSR", "328", 1980),  # a numeric item code
        ("Uzbek SSR", None, 1980),
        ("Uzbek SSR", "raw cotton", "IX five-year plan"),
        ("Uzbek SSR", "raw cotton", "1976-80"),  # not a form the validator accepts
        ("Uzbek SSR", "raw cotton", None),
    ],
)
def test_a_row_the_seal_cannot_read_refuses_the_frame(sealed, region, series, year):
    df = pd.DataFrame(
        {
            "region": ["Kazakh SSR", region],
            "series": ["raw cotton", series],
            "year": [1980, year],
            "value": [1.0, 1.0],
        }
    )
    assert HELD_OUT.matches(region, series, year) is False
    with pytest.raises(SealedError, match="cannot tell whether this frame"):
        held_out_mask(df)
    with pytest.raises(SealedError, match="cannot tell whether this frame"):
        filter_sealed(df)
    with pytest.raises(SealedError, match="cannot tell whether this frame"):
        check_grouping(df, ["region", "year"])
    _, n = filter_sealed(df, declare_clean=True)
    assert n == 0


@pytest.mark.parametrize(
    ("region", "series", "year"),
    [
        ("Kazakh SSR", "raw cotton", "IX five-year plan"),
        (GEORGIA_KA, "wheat", 1980),
        ("235", "raw cotton", 1990),
        (None, "wheat", 1980),
        ("Uzbek SSR", "wheat", None),
    ],
)
def test_a_row_ruled_out_by_one_field_needs_nothing_more(sealed, region, series, year):
    """Failing closed is about rows that might be the anchor, not about every blank."""
    df = pd.DataFrame({"region": [region], "series": [series], "year": [year]})
    out, n = filter_sealed(df)
    assert n == 0
    assert len(out) == 1


def test_a_transcription_with_a_blank_stub_is_refused(sealed):
    df = by_republic_table()
    uzbek = df["row_label_translit"] == "Uzbekskaia SSR"
    df.loc[uzbek, "row_label"] = ""
    # The transliteration still names the republic, so those rows are withheld, not guessed at.
    _, n = filter_sealed(df)
    assert n == 8
    df.loc[uzbek, "row_label_translit"] = ""
    with pytest.raises(SealedError, match="cannot tell whether this frame"):
        filter_sealed(df)


def test_unreadable_rows_still_count_as_not_held_out_once_unsealed(unsealed):
    df = pd.DataFrame(
        {"region": [GEORGIA_KA, "Uzbek SSR"], "series": ["cotton"] * 2, "year": [1980] * 2}
    )
    assert held_out_mask(df).tolist() == [False, True]


# ---------------------------------------------------------------- the table's own totals


def test_a_subtotal_that_holds_the_anchor_goes_with_it(sealed):
    cells = []
    for period in ("1975", "1980"):
        for label, role, value in (
            (USSR_RU, "total", "2"),
            (CENTRAL_ASIA_RU, "subtotal", "2"),
            (UZBEK_RU, "data", "1"),
            (TURKMEN_RU, "data", "1"),
        ):
            cells.append(
                {
                    "row_label": label,
                    "column_label": period,
                    "period": period,
                    "value_raw": value,
                    "row_role": role,
                }
            )
    df = as_frame(transcription_rows(cells))
    out, n = filter_sealed(df)
    assert n == 3
    assert set(out.loc[out["period"] == "1980", "row_label"]) == {TURKMEN_RU}
    assert len(out.loc[out["period"] == "1975"]) == 4


def test_a_table_whose_roles_are_unknown_loses_the_whole_period(sealed):
    """Without roles any cell beside an anchor cell may be the total that reveals it."""
    df = by_republic_table().drop(columns=["row_role", "column_role"])
    out, n = filter_sealed(df)
    assert n == 3 * len(_IN_WINDOW)
    assert set(out["period"]) == {"1975"}
