"""The proxy-free smoothness test must not default to a detrending chosen without evidence.

``forensics_core.dispersion.too_smooth_test`` documents that ``detrend="diff"`` has
essentially no power on stationary or trend-stationary series, while on persistent honest
growth ``"linear"`` and ``"none"`` reject honest provinces. Which one is valid depends on the
persistence of honest growth, so the stub carries no default and the research question states
the open choice with simulated size and power under iid and persistent honest growth.
"""

from __future__ import annotations

import inspect
import re
import typing
from pathlib import Path

from china.analysis.dispersion import smoothness_by_province

DOC = Path(__file__).resolve().parents[1] / "docs" / "research_question.md"


def test_detrend_has_no_default():
    param = inspect.signature(smoothness_by_province).parameters["detrend"]
    assert param.default is inspect.Parameter.empty
    assert param.kind is inspect.Parameter.KEYWORD_ONLY


def test_detrend_is_one_of_the_library_options():
    hints = typing.get_type_hints(smoothness_by_province)
    assert set(typing.get_args(hints["detrend"])) == {"none", "linear", "diff"}


def test_docstring_no_longer_says_about_2_for_independent_noise():
    doc = re.sub(r"\s+", " ", inspect.getdoc(smoothness_by_province) or "")
    assert "about 2 for independent noise" not in doc
    assert "near 3" in doc


def test_research_question_reports_size_under_iid_and_persistent_growth():
    lines = DOC.read_text(encoding="utf-8").splitlines()
    honest = {
        (row.split("|")[1].strip(), row.split("|")[3].strip())
        for row in lines
        if row.startswith("| ") and "| honest |" in row
    }
    for growth in ("iid", "ar07", "rw"):
        for detrend in ("linear", "diff"):
            assert (growth, detrend) in honest
    assert any("detrending is not yet chosen" in line for line in lines)
