"""Loader for the Bao et al. (2020) fraud-detection panel.

Source
------
Bao, Y., B. Ke, B. Li, Y. J. Yu and J. Zhang, 2020. "Detecting Accounting Fraud in Publicly
Traded U.S. Firms Using a Machine Learning Approach", *Journal of Accounting Research* 58(1),
199-235. The replication archive is
<https://github.com/JarFraud/FraudDetection>, registry entry ``bao_replication`` in
``data/SOURCES.yaml``.

Three files matter:

``data_FraudDetection_JAR2020.csv``
    One row per firm-year, `gvkey` x `fyear`, carrying 28 raw Compustat items, 14 derived
    ratios, the AAER case number ``p_aaer`` and the binary label ``misstate``.
``AAER_firm_year.csv``
    The AAER case list keyed by CIK and year, with an ``UNDERSTATEMENT`` flag.
``identifiers.csv``
    The `gvkey` x `fyear` key of the panel.

What this module does and does not do
-------------------------------------
It loads, types, validates and describes. It does not fit, score, test or estimate anything:
CONTRACT rule 4 permits "loading, cleaning, counting rows and describing coverage" at any
phase and forbids the rest until the gate opens. :func:`coverage` returns counts, not
findings.

The Beneish gap, stated once here
---------------------------------
:mod:`aaer.features.beneish` needs twelve items per firm-year. This panel supplies nine of
them. Three are absent and cannot be recovered from what is here:

=================== ========================= =========================================
Beneish input       Compustat item            Present?
=================== ========================= =========================================
receivables         ``rect``                  yes
sales               ``sale``                  yes
cogs                ``cogs``                  yes
current_assets      ``act``                   yes
total_assets        ``at``                    yes
depreciation        ``dp``                    yes
long_term_debt      ``dltt``                  yes
current_liabilities ``lct``                   yes
income_continuing   ``ib``                    yes
**ppe_net**         ``ppent``                 **no** - only ``ppegt``, gross of depreciation
**sga**             ``xsga``                  **no**
**cash_from_ops**   ``oancf``                 **no**
=================== ========================= =========================================

So DSRI, GMI, SGI and LVGI are computable from this panel as published; AQI and DEPI only by
substituting gross for net property, plant and equipment, which is a different ratio and not
the one Beneish (1999) estimated his coefficients on; SGAI not at all; and TATA not at all in
the cash-flow form this repository implements. :data:`BENEISH_ITEMS_PRESENT` and
:data:`BENEISH_ITEMS_ABSENT` record that split so that no caller can quietly compute a
four-component number and call it an M-score.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

__all__ = [
    "BAO_FILES",
    "BENEISH_ITEMS_ABSENT",
    "BENEISH_ITEMS_PRESENT",
    "COMPUSTAT_TO_BENEISH",
    "BaoPanel",
    "coverage",
    "load_bao_panel",
]

#: File names in the replication archive, relative to ``data/raw/bao``.
BAO_FILES: dict[str, str] = {
    "panel": "data_FraudDetection_JAR2020.csv",
    "aaer_firm_year": "AAER_firm_year.csv",
    "identifiers": "identifiers.csv",
}

#: Compustat item -> the name :mod:`aaer.features.beneish` expects, for the items present.
COMPUSTAT_TO_BENEISH: dict[str, str] = {
    "rect": "receivables",
    "sale": "sales",
    "cogs": "cogs",
    "act": "current_assets",
    "at": "total_assets",
    "dp": "depreciation",
    "dltt": "long_term_debt",
    "lct": "current_liabilities",
    "ib": "income_continuing_ops",
}

BENEISH_ITEMS_PRESENT: tuple[str, ...] = tuple(COMPUSTAT_TO_BENEISH.values())

#: The three the panel cannot supply, and the Compustat item each would need.
BENEISH_ITEMS_ABSENT: dict[str, str] = {
    "ppe_net": "ppent (only ppegt, gross, is present)",
    "sga": "xsga",
    "cash_from_operations": "oancf",
}


@dataclass(frozen=True)
class BaoPanel:
    """The loaded panel and the counts that describe it.

    Attributes
    ----------
    frame : pandas.DataFrame
        One row per ``gvkey`` x ``fyear``, with the Compustat items renamed to the Beneish
        vocabulary where a mapping exists and every other column left as published.
    n_rows, n_firms, n_years : int
        Shape of the panel.
    year_min, year_max : int
        Fiscal-year range.
    n_positive : int
        Rows with ``misstate == 1``.
    n_aaer_cases : int
        Distinct non-null ``p_aaer`` case numbers.
    """

    frame: pd.DataFrame
    n_rows: int
    n_firms: int
    n_years: int
    year_min: int
    year_max: int
    n_positive: int
    n_aaer_cases: int

    @property
    def base_rate(self) -> float:
        """Share of firm-years labelled as misstatements. A count, not a finding."""
        return self.n_positive / self.n_rows if self.n_rows else float("nan")


def load_bao_panel(data_dir: Path | str, *, rename: bool = True) -> BaoPanel:
    """Read the replication panel and describe it.

    Parameters
    ----------
    data_dir : pathlib.Path or str
        The project ``data`` directory; the panel is read from ``raw/bao`` beneath it.
    rename : bool, default True
        Rename the nine Compustat items that :mod:`aaer.features.beneish` knows about into
        its vocabulary, keeping the originals too. The other columns are untouched.

    Returns
    -------
    BaoPanel

    Raises
    ------
    FileNotFoundError
        If the panel file is not present, naming the acquisition command.
    ValueError
        If the file does not carry the label and key columns this loader assumes.
    """
    root = Path(data_dir) / "raw" / "bao"
    path = root / BAO_FILES["panel"]
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing. Fetch it with "
            "`python -m aaer.acquire --source bao_replication`, or see "
            "data/SOURCES.yaml for the URL."
        )

    frame = pd.read_csv(path)
    required = {"gvkey", "fyear", "misstate", "p_aaer"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path.name} is missing expected column(s): {missing}")

    frame["fyear"] = frame["fyear"].astype(int)
    frame["gvkey"] = frame["gvkey"].astype(int)
    frame["misstate"] = frame["misstate"].astype(int)

    if rename:
        for compustat, beneish in COMPUSTAT_TO_BENEISH.items():
            if compustat in frame.columns:
                frame[beneish] = frame[compustat].astype(float)

    return BaoPanel(
        frame=frame,
        n_rows=len(frame),
        n_firms=int(frame["gvkey"].nunique()),
        n_years=int(frame["fyear"].nunique()),
        year_min=int(frame["fyear"].min()),
        year_max=int(frame["fyear"].max()),
        n_positive=int((frame["misstate"] == 1).sum()),
        n_aaer_cases=int(frame["p_aaer"].dropna().nunique()),
    )


def coverage(panel: BaoPanel) -> pd.DataFrame:
    """Rows, firms and labelled rows per fiscal year.

    Description of the sample, not a result about it: CONTRACT rule 4 permits counting rows
    and describing coverage at any phase.

    Parameters
    ----------
    panel : BaoPanel

    Returns
    -------
    pandas.DataFrame
        One row per fiscal year, with ``n_rows``, ``n_firms``, ``n_positive`` and
        ``base_rate``, ordered by year.
    """
    grouped = panel.frame.groupby("fyear")
    table = pd.DataFrame(
        {
            "n_rows": grouped.size(),
            "n_firms": grouped["gvkey"].nunique(),
            "n_positive": grouped["misstate"].sum(),
        }
    ).reset_index()
    table["base_rate"] = table["n_positive"] / table["n_rows"]
    return table.sort_values("fyear").reset_index(drop=True)
