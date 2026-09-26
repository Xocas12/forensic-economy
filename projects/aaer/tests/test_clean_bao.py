"""The Bao et al. (2020) panel loader.

Synthetic fixture only: CONTRACT rule 3 keeps real data out of the test tree, and rule 4
keeps anything inferential out of this layer entirely. What is asserted here is that the
loader reads the shape the archive publishes, types its keys, renames the nine Compustat
items the Beneish implementation knows about, and refuses loudly when the file is absent or
the wrong shape.

The most load-bearing assertion in the file is
:func:`test_the_three_missing_beneish_items_are_named_not_silently_dropped`. The panel cannot
supply net PP&E, SG&A or operating cash flow, so a caller who assumes twelve items gets four
of the eight Beneish components silently wrong. The loader publishes that gap as data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from aaer.clean.bao import (
    BENEISH_ITEMS_ABSENT,
    BENEISH_ITEMS_PRESENT,
    COMPUSTAT_TO_BENEISH,
    load_bao_panel,
)
from aaer.clean.bao import coverage as bao_coverage
from aaer.features.beneish import LAGGED_COLUMNS, REQUIRED_COLUMNS

SYNTHETIC = pd.DataFrame(
    {
        "fyear": [1991, 1991, 1992, 1992, 1993],
        "gvkey": [1001, 1002, 1001, 1002, 1001],
        "p_aaer": [float("nan"), 27.0, float("nan"), 27.0, float("nan")],
        "misstate": [0, 1, 0, 1, 0],
        "rect": [10.0, 20.0, 11.0, 22.0, 12.0],
        "sale": [100.0, 200.0, 110.0, 220.0, 120.0],
        "cogs": [60.0, 120.0, 66.0, 132.0, 72.0],
        "act": [50.0, 100.0, 55.0, 110.0, 60.0],
        "at": [200.0, 400.0, 220.0, 440.0, 240.0],
        "dp": [5.0, 10.0, 5.5, 11.0, 6.0],
        "dltt": [30.0, 60.0, 33.0, 66.0, 36.0],
        "lct": [25.0, 50.0, 27.5, 55.0, 30.0],
        "ib": [8.0, 16.0, 8.8, 17.6, 9.6],
        "ppegt": [80.0, 160.0, 88.0, 176.0, 96.0],
    }
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    root = tmp_path / "raw" / "bao"
    root.mkdir(parents=True)
    SYNTHETIC.to_csv(root / "data_FraudDetection_JAR2020.csv", index=False)
    return tmp_path


def test_the_panel_loads_and_counts_itself(data_dir: Path):
    panel = load_bao_panel(data_dir)
    assert panel.n_rows == 5
    assert panel.n_firms == 2
    assert panel.n_years == 3
    assert (panel.year_min, panel.year_max) == (1991, 1993)
    assert panel.n_positive == 2
    assert panel.n_aaer_cases == 1
    assert panel.base_rate == pytest.approx(2 / 5)


def test_the_keys_are_integers_not_floats(data_dir: Path):
    """A float gvkey joins to nothing and does so silently."""
    frame = load_bao_panel(data_dir).frame
    assert frame["gvkey"].dtype.kind == "i"
    assert frame["fyear"].dtype.kind == "i"
    assert frame["misstate"].dtype.kind == "i"


def test_the_nine_available_items_are_renamed_into_the_beneish_vocabulary(data_dir: Path):
    frame = load_bao_panel(data_dir).frame
    for compustat, beneish in COMPUSTAT_TO_BENEISH.items():
        assert beneish in frame.columns, f"{compustat} was not renamed to {beneish}"
        assert (frame[beneish] == frame[compustat]).all()


def test_renaming_can_be_turned_off(data_dir: Path):
    frame = load_bao_panel(data_dir, rename=False).frame
    assert "receivables" not in frame.columns
    assert "rect" in frame.columns


def test_the_three_missing_beneish_items_are_named_not_silently_dropped(data_dir: Path):
    """The gap between what Beneish needs and what this panel has is published as data."""
    frame = load_bao_panel(data_dir).frame
    needed = {c for c in REQUIRED_COLUMNS}
    assert set(BENEISH_ITEMS_PRESENT) | set(BENEISH_ITEMS_ABSENT) == needed
    for absent in BENEISH_ITEMS_ABSENT:
        assert absent not in frame.columns, (
            f"{absent} is advertised as absent but the loader produced it"
        )
    # and the lagged columns the component function wants are not here either: this panel is
    # one row per firm-year with no lags built
    assert not set(LAGGED_COLUMNS) & set(frame.columns)


def test_coverage_is_one_row_per_year_and_sums_back_to_the_panel(data_dir: Path):
    panel = load_bao_panel(data_dir)
    table = bao_coverage(panel)
    assert list(table["fyear"]) == [1991, 1992, 1993]
    assert table["n_rows"].sum() == panel.n_rows
    assert table["n_positive"].sum() == panel.n_positive
    assert table["base_rate"].between(0, 1).all()


def test_a_missing_file_names_the_acquisition_command(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match=r"aaer\.acquire"):
        load_bao_panel(tmp_path)


def test_a_file_without_the_label_column_is_refused(tmp_path: Path):
    root = tmp_path / "raw" / "bao"
    root.mkdir(parents=True)
    SYNTHETIC.drop(columns=["misstate"]).to_csv(
        root / "data_FraudDetection_JAR2020.csv", index=False
    )
    with pytest.raises(ValueError, match="misstate"):
        load_bao_panel(tmp_path)
