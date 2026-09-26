"""Turn what :mod:`aaer.acquire` downloaded into tidy tables. No inference happens here.

Three steps, each in its own module and each reporting what it lost rather than hiding it:

``aaer_releases``
    The SEC AAER listing pages -> one row per enforcement release (AAER number, date,
    respondent, release numbers, PDF link). This is the label side.
``fsds``
    The Financial Statement Data Sets quarterly zips -> the SUB, NUM, PRE and TAG tables,
    exactly as the SEC ships them.
``xbrl_map``
    NUM's us-gaap tags -> the twelve items :mod:`aaer.features.beneish` needs, plus their
    lagged values. **This mapping is provisional and mostly unconfirmed**; read that module's
    docstring before using anything it produces.

The two sides do not meet in this package. Joining releases to firm-years needs a CIK for the
respondent, which the listing does not carry -- the release PDFs and the curated datasets
described in ``data/ACCESS_NOTES.md`` are where that identifier comes from. Building that join
is an open task, not a solved one.
"""

from aaer.clean.aaer_releases import ListingParse, load_listing, parse_listing_page
from aaer.clean.bao import (
    BENEISH_ITEMS_ABSENT,
    BENEISH_ITEMS_PRESENT,
    BaoPanel,
    coverage,
    load_bao_panel,
)
from aaer.clean.fsds import FsdsQuarter, iter_fsds_zips, read_fsds_zip, read_quarters
from aaer.clean.xbrl_map import (
    BENEISH_TAG_MAP,
    LagResult,
    MappingResult,
    add_lags,
    map_beneish_items,
    mapping_table,
)

__all__ = [
    "BENEISH_ITEMS_ABSENT",
    "BENEISH_ITEMS_PRESENT",
    "BENEISH_TAG_MAP",
    "BaoPanel",
    "FsdsQuarter",
    "LagResult",
    "ListingParse",
    "MappingResult",
    "add_lags",
    "coverage",
    "iter_fsds_zips",
    "load_bao_panel",
    "load_listing",
    "map_beneish_items",
    "mapping_table",
    "parse_listing_page",
    "read_fsds_zip",
    "read_quarters",
]
