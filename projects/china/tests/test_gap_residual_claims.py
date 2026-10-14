"""What the project may say about the residual of the provincial-national gap.

In nominal levels the gap is ``M + D - I - n``: provincial misreporting, cross-province double
counting (``D >= 0``), the centre's informal-economy adjustment (``I >= 0``, which provinces do
not apply, so it narrows the gap) and any overstatement in the national figure. With no
component estimated the residual is neither an upper nor a lower bound on ``M``, and removing
double counting alone understates it. These tests keep the docs and docstrings from saying
otherwise, and keep the informal-economy adjustment on the list of components that
:func:`china.analysis.gap.mechanical_gap_components` has to estimate or bound.

They read text, not results: every analysis function is a stub.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest
from china.analysis import gap

PROJECT = Path(__file__).resolve().parents[1]

#: Every place a reader of the china project gets guidance on what the gap means.
TEXT_FILES = sorted(
    [PROJECT / "README.md", *(PROJECT / "docs").glob("*.md"), *(PROJECT / "src").rglob("*.py")]
)

#: Wording that marks a sentence as denying the bound or conditioning it on stated signs.
QUALIFIERS = re.compile(r"\b(not|neither|nor|never|only if|only under|only beside|unless|assum)")


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.;!?])\s", flat) if s.strip()]


def test_the_text_scan_covers_the_files_that_made_the_claim():
    names = {p.relative_to(PROJECT).as_posix() for p in TEXT_FILES}
    assert {
        "README.md",
        "docs/data_dictionary.md",
        "docs/known_traps.md",
        "src/china/analysis/gap.py",
    } <= names


@pytest.mark.parametrize("path", TEXT_FILES, ids=lambda p: p.relative_to(PROJECT).as_posix())
def test_40_no_unqualified_claim_that_the_residual_bounds_misreporting(path):
    """#40: a bound on misreporting is never asserted without the sign assumptions."""
    offending = [
        s
        for s in _sentences(path.read_text(encoding="utf-8"))
        if re.search(r"\b(upper|lower) bound\b", s, re.I)
        and re.search(r"misreport", s, re.I)
        and not QUALIFIERS.search(s)
    ]
    assert offending == [], f"{path.name} calls the residual a bound unconditionally"


@pytest.mark.parametrize("path", TEXT_FILES, ids=lambda p: p.relative_to(PROJECT).as_posix())
def test_40_no_claim_that_the_residual_can_only_be_bounded(path):
    """#40: "only bounded" implies a bound exists without assumptions, which it does not."""
    text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
    assert not re.search(r"\b(can only be bounded|only bounded)\b", text, re.I)


def test_40_informal_adjustment_is_a_named_component_of_the_gap_module():
    """#40: the module's list of mechanical components includes the informal-economy term."""
    doc = gap.__doc__ or ""
    listed = re.findall(r"^\d+\. \*\*(.+?)\*\*", doc, re.M)
    assert any("informal" in item.lower() for item in listed), listed
    assert any("double counting" in item.lower() for item in listed), listed


def test_40_mechanical_gap_components_must_estimate_the_informal_adjustment():
    """#40: the function's own spec names the term, its sign, and the no-bound rule."""
    doc = inspect.getdoc(gap.mechanical_gap_components) or ""
    flat = re.sub(r"\s+", " ", doc)
    assert "``informal_adjustment``" in doc
    assert "``double_counting``" in doc
    assert re.search(r"narrows the gap", flat)
    assert re.search(r"not as a bound on misreporting", flat)


def test_40_the_stub_message_names_the_informal_adjustment_and_the_sign_rule():
    """#40: what an implementer sees on calling the stub carries the same rule."""
    with pytest.raises(NotImplementedError) as info:
        gap.mechanical_gap_components(None, vintage="2024")
    message = str(info.value)
    assert "informal-economy adjustment" in message
    assert "only bounded" not in message
    assert "sign assumption" in message
