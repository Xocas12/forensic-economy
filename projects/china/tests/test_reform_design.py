"""What the reform test may and may not claim, in the code and in the documents.

The unified-accounting reform changed the method in order to close the provincial-sum minus
national gap, so the gap is predicted to contract at the 2019 data year with no misreporting at
all. These tests hold the specification to that: the aggregate jump is described as the
combined effect of method, census and misreporting, any misreporting claim is routed through
the cross-province contrast, and that contrast cannot be called without a stated model of the
legitimate revisions.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest
from china.analysis import reform
from forensics_core.provenance.manifest import load_sources

PROJECT = Path(__file__).resolve().parents[1]
SOURCES_YAML = PROJECT / "data" / "SOURCES.yaml"

#: Every place the reform test is specified. Each must describe the aggregate jump as a
#: combined effect and name the contrast that any misreporting claim has to come from.
SPECIFICATION = {
    "README.md": PROJECT / "README.md",
    "docs/research_question.md": PROJECT / "docs" / "research_question.md",
    "docs/validation_anchors.md": PROJECT / "docs" / "validation_anchors.md",
    "src/china/analysis/reform.py": Path(reform.__file__),
}

#: Claims the specification used to make and must not make again: that the reform is a
#: natural experiment separating method from misreporting, that misreporting shows up as the
#: gap contracting discontinuously at the break, that the mechanical part of the gap has no
#: reason to jump there, and that a revision across the reform is inflation being given back.
RETIRED_CLAIMS = (
    "natural experiment",
    "contract discontinuously",
    "no reason to jump",
    "give it back",
)

#: The registry entry for the deputy head's interview on the 2017 plan, which says what the
#: reform changed and what it was for.
PLAN_SOURCE = "nbs_qa_unified_accounting_plan_2017"

#: Reform the accounting method; achieve basic alignment of summed regional GDP with GDP; the
#: gap is somewhat too large.
PLAN_PHRASES = (
    "改革核算方法",
    "实现地区生产总值汇总数据与国内生产总值数据的基本衔接",
    "差距有些偏大",
)


def _normalised(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


@pytest.mark.parametrize("name", sorted(SPECIFICATION))
def test_the_specification_reports_the_aggregate_jump_as_a_combined_effect(name):
    text = _normalised(SPECIFICATION[name])
    assert "combined effect" in text, f"{name} does not say what the aggregate jump measures"
    assert "cross_province_reform_contrast" in text, (
        f"{name} does not name the contrast a misreporting claim has to come from"
    )
    found = [claim for claim in RETIRED_CLAIMS if claim in text]
    assert found == [], f"{name} still says {found}"


def test_the_cross_province_contrast_cannot_run_without_a_stated_revision_model():
    assert "cross_province_reform_contrast" in reform.__all__
    parameters = inspect.signature(reform.cross_province_reform_contrast).parameters
    model = parameters["revision_model"]
    assert model.kind is inspect.Parameter.KEYWORD_ONLY
    assert model.default is inspect.Parameter.empty
    with pytest.raises(NotImplementedError, match="stated model"):
        reform.cross_province_reform_contrast(None, None, revision_model=None)


def test_the_discontinuity_sends_misreporting_claims_to_the_contrast():
    doc = " ".join((inspect.getdoc(reform.reform_discontinuity) or "").split())
    assert "combined effect" in doc
    assert "as a test for misreporting it has no size" in doc
    assert "cross_province_reform_contrast" in doc


def test_the_reform_aim_is_quoted_from_the_registered_plan_interview():
    sources = {s.id: s for s in load_sources(SOURCES_YAML)}
    assert PLAN_SOURCE in sources
    assert sources[PLAN_SOURCE].status == "verified"
    doc = reform.__doc__ or ""
    assert PLAN_SOURCE in doc
    quoted = re.findall(r"'([^']*[\u4e00-\u9fff][^']*)'", doc)
    # what the reform changed, what it was for, and why: the three facts the argument rests on
    for phrase in PLAN_PHRASES:
        assert phrase in quoted, f"the module should quote {phrase!r} from the plan interview"
    missing = [phrase for phrase in quoted if phrase not in sources[PLAN_SOURCE].evidence]
    assert missing == [], f"quoted but not in the registry's recorded evidence: {missing}"
