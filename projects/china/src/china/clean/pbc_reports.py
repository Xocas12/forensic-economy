"""Loader for the central bank's regional financial operation reports.

Provincial credit is the hardest series in this project, and it arrives as **prose in a PDF**.
Each year's report page links a main report of about five megabytes plus one three-page
summary per province, and the summary states the year-end loan balance in a sentence. The
verification pass read one of them and quoted it; with the numbers changed to obviously
artificial ones, it looks like this::

    2099 year-end, the province's banking institutions had a domestic and foreign currency
    loan balance of 9.9 trillion yuan, up 111 hundred million from the start of the year,
    a year-on-year increase of 2.2 percent.

Three consequences the project has to live with:

* **Precision is about two significant figures.** "5.5 trillion" is what is published. A test
  that needs the third digit of provincial credit cannot be run on this source.
* **The unit varies within a sentence.** The balance is in trillions, the change in hundreds
  of millions. Both are converted here to the panel's 100 million yuan.
* **The file-to-province mapping is in the link text, not the file name.** The PDFs are named
  with opaque publisher identifiers. The province name is the run of characters between the
  title's opening bracket and the words "financial operation report", and it is in Chinese.

That last point leaves a genuine open question, and this module does not paper over it: it
extracts the Chinese province name mechanically and stops there.
:func:`map_province_names` needs a Chinese-to-canonical mapping supplied by the caller, and
the project does not have one that was read from a source. Building it from the fetched link
text is a one-off task recorded in the README.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from china.clean._html import decode_html, iter_anchors

__all__ = [
    "BALANCE_COLUMNS",
    "SUMMARY_COLUMNS",
    "extract_pdf_text",
    "map_province_names",
    "parse_loan_balances",
    "parse_summary_links",
    "to_panel",
]

# Chinese literals are written as escapes to keep this file ASCII. Each is annotated with its
# romanisation and meaning; all of them appear verbatim in the registry's evidence fields.
_LOAN_BALANCE = "\u5404\u9879\u8d37\u6b3e\u4f59\u989d"  # ge xiang dai kuan yu e, loan balance
_TRILLION = "\u4e07\u4ebf"  # wan yi, 10^12
_HUNDRED_MILLION = "\u4ebf"  # yi, 10^8
_YUAN = "\u5143"  # yuan
_YEAR_END = "\u5e74\u672b"  # nian mo, year-end
_YOY_GROWTH = "\u540c\u6bd4\u589e\u957f"  # tong bi zeng zhang, year-on-year growth
_SUMMARY = "\u6458\u8981"  # zhai yao, summary/abstract
_FINANCIAL_REPORT = "\u91d1\u878d\u8fd0\u884c\u62a5\u544a"  # jin rong yun xing bao gao
_BRACKET_OPEN = "\u300a"  # opening double angle bracket used around Chinese titles
_BRACKET_CLOSE = "\u300b"

#: How many 100 million yuan each published unit is worth.
_UNIT_FACTOR = {_TRILLION: 10_000.0, _HUNDRED_MILLION: 1.0}

_BALANCE_RE = re.compile(
    rf"{_LOAN_BALANCE}\s*([0-9]+(?:\.[0-9]+)?)\s*({_TRILLION}|{_HUNDRED_MILLION}){_YUAN}"
)
_YEAR_RE = re.compile(rf"((?:19|20)[0-9]{{2}}){_YEAR_END}")
_GROWTH_RE = re.compile(rf"{_YOY_GROWTH}\s*(-?[0-9]+(?:\.[0-9]+)?)\s*%")
_TITLE_RE = re.compile(
    rf"{_BRACKET_OPEN}([^{_BRACKET_CLOSE}]*?){_FINANCIAL_REPORT}[^{_BRACKET_CLOSE}]*{_BRACKET_CLOSE}"
)
_FULLWIDTH_PERIOD = "\uff0e"  # the channel numbers some links with a full-width stop
_ORDINAL_RE = re.compile(rf"^\s*(\d+)\s*[.{_FULLWIDTH_PERIOD}]")
_PDF_RE = re.compile(r"\.pdf$", re.IGNORECASE)

#: Columns of the frame :func:`parse_loan_balances` returns.
BALANCE_COLUMNS: tuple[str, ...] = (
    "year",
    "value_100m_yuan",
    "published_figure",
    "published_unit",
    "yoy_growth_pct",
)

#: Columns of the frame :func:`parse_summary_links` returns.
SUMMARY_COLUMNS: tuple[str, ...] = (
    "ordinal",
    "href",
    "link_text",
    "province_zh",
    "is_summary",
)


def extract_pdf_text(path: Path) -> str:
    """Read a report PDF's text.

    A thin wrapper so that the choice of extraction library is made in one place and the
    parsers below can be tested on strings without a PDF anywhere near them.

    Parameters
    ----------
    path : Path
        The PDF.

    Returns
    -------
    str
        Concatenated page text, pages separated by newlines. Pages that yield no text
        contribute an empty string rather than being skipped, so page numbering is preserved.

    Raises
    ------
    ImportError
        If ``pdfplumber`` is not installed.
    """
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject
        raise ImportError("pdfplumber is required to read the report PDFs") from exc
    with pdfplumber.open(path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def parse_loan_balances(text: str) -> pd.DataFrame:
    """Find every published year-end loan balance in a summary's text.

    Parameters
    ----------
    text : str
        Text of one provincial summary, from :func:`extract_pdf_text`.

    Returns
    -------
    pandas.DataFrame
        Columns :data:`BALANCE_COLUMNS`, one row per balance sentence found, in order of
        appearance:

        ``year``
            The year of the nearest preceding "year-end" marker, or ``<NA>`` when there is
            none. Left missing rather than guessed: a balance whose year is unknown is not a
            panel row.
        ``value_100m_yuan``
            The figure converted to the panel's unit. Trillions are multiplied by 10,000.
        ``published_figure`` and ``published_unit``
            What was actually printed, kept so the rounding is visible downstream.
        ``yoy_growth_pct``
            The year-on-year growth stated after the balance, if any.

        An empty frame means no balance sentence matched, which for a main report rather than
        a summary is the expected result.
    """
    rows: list[dict[str, object]] = []
    for match in _BALANCE_RE.finditer(text):
        before = text[: match.start()]
        year_matches = _YEAR_RE.findall(before)
        after = text[match.end() : match.end() + 200]
        growth = _GROWTH_RE.search(after)
        figure = float(match.group(1))
        unit = match.group(2)
        rows.append(
            {
                "year": int(year_matches[-1]) if year_matches else pd.NA,
                "value_100m_yuan": figure * _UNIT_FACTOR[unit],
                "published_figure": figure,
                "published_unit": unit,
                "yoy_growth_pct": float(growth.group(1)) if growth else pd.NA,
            }
        )
    frame = pd.DataFrame(rows, columns=list(BALANCE_COLUMNS))
    frame["year"] = frame["year"].astype("Int64")
    frame["yoy_growth_pct"] = pd.to_numeric(frame["yoy_growth_pct"], errors="coerce")
    return frame


def parse_summary_links(year_html: bytes | str) -> pd.DataFrame:
    """Parse one year's report page into its PDF links, with the province name as published.

    Parameters
    ----------
    year_html : bytes or str
        The year page.

    Returns
    -------
    pandas.DataFrame
        Columns :data:`SUMMARY_COLUMNS`:

        ``ordinal``
            The number the channel prefixes each link with; the main report is 1.
        ``province_zh``
            The characters between the title's opening bracket and "financial operation
            report". For the main report this is the country name rather than a province,
            which is exactly why ``is_summary`` exists.
        ``is_summary``
            True when the link text is marked as a summary. The main report is not.

        Rows whose title does not match the pattern keep an empty ``province_zh`` rather than
        being dropped: an unmatched title is something to look at.
    """
    text = decode_html(year_html) if isinstance(year_html, bytes) else year_html
    rows: list[dict[str, object]] = []
    for anchor in iter_anchors(text):
        if not _PDF_RE.search(anchor.href):
            continue
        ordinal_match = _ORDINAL_RE.match(anchor.text)
        title_match = _TITLE_RE.search(anchor.text)
        rows.append(
            {
                "ordinal": int(ordinal_match.group(1)) if ordinal_match else pd.NA,
                "href": anchor.href,
                "link_text": anchor.text,
                "province_zh": title_match.group(1).strip() if title_match else "",
                "is_summary": _SUMMARY in anchor.text,
            }
        )
    frame = pd.DataFrame(rows, columns=list(SUMMARY_COLUMNS))
    frame["ordinal"] = frame["ordinal"].astype("Int64")
    frame["is_summary"] = frame["is_summary"].astype("boolean")
    return frame


def map_province_names(names: pd.Series, mapping: dict[str, str]) -> pd.Series:
    """Map published Chinese province names onto the project's canonical names.

    The mapping is a required argument and has **no default**. The project has no
    Chinese-to-English province table that was read from a source, and writing one from
    memory would put thirty-one unverified strings at the join between the credit series and
    everything else. Build it once from the ``province_zh`` column of a real fetched year
    page, record it, and pass it in.

    Parameters
    ----------
    names : pandas.Series
        Published names, e.g. the ``province_zh`` column of :func:`parse_summary_links`.
    mapping : dict of str to str
        Published name to canonical name from :data:`china.clean.provinces.PROVINCES`.

    Returns
    -------
    pandas.Series
        Canonical names, with ``<NA>`` wherever the mapping has no entry. Unmapped is left
        visible on purpose: Shenzhen appears among these files and is not a province.

    Raises
    ------
    ValueError
        If ``mapping`` is empty.
    """
    if not mapping:
        raise ValueError(
            "map_province_names needs a Chinese-to-canonical mapping; build it from the "
            "province_zh column of a fetched report page and record it in the data dictionary"
        )
    return names.map(mapping).astype("string")


def to_panel(
    balances: pd.DataFrame,
    *,
    province: str,
    vintage: str,
    source_id: str = "pbc_regional_financial_operation_reports",
) -> pd.DataFrame:
    """Turn one province's parsed balances into tidy panel rows.

    Parameters
    ----------
    balances : pandas.DataFrame
        Output of :func:`parse_loan_balances`, for a single province's summary.
    province : str
        Canonical province name.
    vintage : str
        Vintage label; for these reports the publication year of the report, since a later
        report restates an earlier year.
    source_id : str, default "pbc_regional_financial_operation_reports"
        Registry id to stamp on every row.

    Returns
    -------
    pandas.DataFrame
        Rows in :data:`china.clean.schema.PANEL_COLUMNS`, carrying ``loans_outstanding``.
        Balances with no year are dropped, and the count of dropped rows is in the frame's
        ``attrs["n_dropped_no_year"]``.
    """
    from china.clean.schema import PANEL_COLUMNS, SERIES

    usable = balances.dropna(subset=["year"])
    frame = pd.DataFrame(
        {
            "province": province,
            "year": usable["year"].astype("int64"),
            "series": "loans_outstanding",
            "value": usable["value_100m_yuan"].astype("float64"),
            "unit": SERIES["loans_outstanding"].unit,
            "vintage": vintage,
            "source_id": source_id,
        },
        columns=list(PANEL_COLUMNS),
    )
    frame.attrs["n_dropped_no_year"] = int(len(balances) - len(usable))
    return frame
