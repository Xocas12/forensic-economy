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
REPO = PROJECT.parents[1]
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

#: Every document that describes the china project: its README, its docs, its source, and the
#: two programme-level files that carry a row for it. The retired claims and the label check
#: run over all of these, not only over the files that specify the reform test, because the
#: reform was also listed as ground truth in places that specify nothing.
DOCUMENTS = {
    path.relative_to(REPO).as_posix(): path
    for path in (
        REPO / "README.md",
        REPO / "ROADMAP.md",
        PROJECT / "README.md",
        *sorted((PROJECT / "docs").glob("*.md")),
        *sorted((PROJECT / "src").rglob("*.py")),
    )
}

#: Files the document set must contain, so that a wrong path or an empty glob cannot make the
#: checks below pass by reading nothing.
MUST_COVER = (
    "README.md",
    "ROADMAP.md",
    "projects/china/README.md",
    "projects/china/docs/research_question.md",
    "projects/china/docs/validation_anchors.md",
    "projects/china/src/china/__init__.py",
    "projects/china/src/china/analysis/__init__.py",
    "projects/china/src/china/analysis/reform.py",
)

#: The places that say what china's labels are, each of which must be found and read: the
#: china row of a table with a Labels column, a table row headed Ground truth, and the
#: package docstring.
STATES_THE_LABELS = (
    "README.md",
    "ROADMAP.md",
    "projects/china/README.md",
    "projects/china/src/china/__init__.py",
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


def _label_statements(path: Path) -> list[str]:
    """Every statement in ``path`` of what something's labels or ground truth are.

    Table cells are read by position, because a Labels column states a label without using
    the word; prose is read sentence by sentence after joining lines, so that a statement
    split across a line break is still one statement.
    """
    text = path.read_text(encoding="utf-8")
    statements = []
    header: list[str] | None = None
    for line in text.splitlines():
        row = line.strip()
        if not row.startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if header is None:
            header = [cell.lower() for cell in cells]
        elif set("".join(cells)) <= set("-: "):
            continue
        elif cells[0].lower() == "ground truth":
            statements.append(" ".join(cells[1:]))
        elif "labels" in header and "`china`" in cells:
            statements.append(cells[header.index("labels")])
    prose = " ".join(text.split())
    for sentence in re.split(r"(?<=[.!?;])\s+|\|", prose):
        lowered = sentence.lower()
        if "ground truth" in lowered or re.search(r"\blabels?\b", lowered):
            statements.append(sentence)
    return [" ".join(statement.split()).lower() for statement in statements]


def test_no_document_about_china_makes_a_retired_claim():
    missing = [name for name in MUST_COVER if name not in DOCUMENTS]
    assert missing == [], f"the document set does not reach {missing}"
    found = {
        name: claims
        for name, path in DOCUMENTS.items()
        if (claims := [claim for claim in RETIRED_CLAIMS if claim in _normalised(path)])
    }
    assert found == {}, f"retired claims still made: {found}"


def test_no_document_names_the_reform_as_ground_truth_or_a_label():
    statements = {name: _label_statements(path) for name, path in DOCUMENTS.items()}
    unread = [name for name in STATES_THE_LABELS if not statements[name]]
    assert unread == [], f"no statement of the labels found in {unread}"
    offending = {
        name: [
            statement
            for statement in found
            if ("reform" in statement or "discontinuity" in statement)
            and "not a label" not in statement
        ]
        for name, found in statements.items()
    }
    offending = {name: found for name, found in offending.items() if found}
    assert offending == {}, f"the reform is still given as ground truth or a label: {offending}"


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


def test_the_contrast_names_the_error_its_inputs_share_and_what_excess_growth_is():
    doc = " ".join((inspect.getdoc(reform.cross_province_reform_contrast) or "").split())
    # honest error in a pre-reform figure is both excess growth and its own correction
    assert "the two inputs share their error" in doc
    assert "how it removes the error the two inputs share" in doc
    # one value per province, as a change rather than a level, on the nominal series
    assert "one value per province" in doc
    assert "The change, not the level" in doc
    assert "grp_nominal" in doc
    assert "trap 4" in doc
