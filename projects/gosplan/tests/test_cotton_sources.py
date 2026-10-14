"""FAOSTAT's USSR seed cotton is the Soviet official figure re-published, not an outside source.

Area 228, item 328 carries FAOSTAT flag ``A`` in every year 1961-1991, and the bulk file's own
``Flags.csv`` defines ``A`` as "Official figure": the value the national authority supplied.
Counted as a measurement beside the official series it copies, it makes the cotton
reconciliation unable to single out the official series in any year where the two agree,
because whenever two of three measurements of one quantity are equal the third gets the
largest standardised adjustment, whatever the standard deviations.

These tests hold the documents, docstrings, transcription targets and the registry to that
classification, so that a later edit cannot quietly turn the copy back into corroboration.
They read text only: nothing here opens ``data/raw`` or touches the held-out window.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import numpy as np
import pytest
from forensics_core.provenance.manifest import load_sources
from forensics_core.reconcile import reconcile, serial_elimination
from gosplan.acquire import agriculture
from gosplan.transcribe.targets import TARGETS

PROJECT_DIR = Path(__file__).resolve().parents[1]
FAOSTAT_USSR = "faostat_qcl_bulk_europe_ussr"

#: FAOSTAT's own glosses, as ``Production_Crops_Livestock_E_Flags.csv`` in the registered
#: Europe bulk zip prints them.
FAO_OFFICIAL = "Official figure"
FAO_EXTERNAL = "Figure from external organization"

NEGATION = re.compile(r"\b(?:not|no|neither|nor|never)\b|n't\b", re.IGNORECASE)
NAMES_FAO = re.compile(r"\bFAO(?:STAT)?\b")
INDEPENDENT = re.compile(r"\bindependent\b", re.IGNORECASE)

#: Sentences that described the FAOSTAT series as an outside source, or misread its flags.
#: Each was in the tree and is retracted; none may come back in another file.
RETRACTED_CLAIMS = {
    "faostat-vs-usda-as-the-outside-check": r"FAOSTAT (?:against|versus|vs\.?) (?:the )?USDA",
    "two-independent-value-series": r"two independent value series",
    "independent-series-not-a-second-reading": r"independent series rather than a second reading",
    "outside-estimates-of-the-same-quantity": r"outside estimates of the same reported quantity",
    "estimates-by-outside-bodies": r"estimates of the same reported quantity by outside bodies",
    "estimated-by-parties-not-in-control": r"estimated by parties the falsifiers did not control",
    "the-anchors-independent-evidence": r"the anchor's independent evidence",
    "two-crop-sources-as-the-physical-check": r"two crop sources as the only physical check",
    "usda-as-fao-reconciliation-partner": r"reconciliation partner for the FAOSTAT series",
    "usda-estimates-what-fao-reports": r"independent Western estimate of the same quantity FAOSTAT",
    "x-glossed-unofficial": r"\bX\s*=\s*unofficial",
    "flag-glossed-unofficial": r"\bflag\w*\W+(?:\w+\W+){0,6}?unofficial",
    "unofficial-figure": r"\bunofficial figure",
}


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "DATA_STATUS.md").is_file() and (parent / "ROADMAP.md").is_file():
            return parent
    raise AssertionError("no directory above this test holds both DATA_STATUS.md and ROADMAP.md")


def _normalise(text: str) -> str:
    """Join wrapped lines and drop markup, so a line break cannot hide a sentence.

    Adjacent Python string literals (``"... " "..."``) are joined too, since that is how a
    long ``notes=`` string in ``targets.py`` is written.
    """
    text = re.sub(r"\"\s*\n\s*\"", "", text)
    text = text.replace("**", "").replace("``", "").replace("`", "").replace("''", "'")
    return re.sub(r"\s+", " ", text)


def _documents() -> dict[str, str]:
    """Every text in the tree that describes the gosplan cotton sources, normalised."""
    root = _repo_root()
    paths = [
        root / "README.md",
        root / "ROADMAP.md",
        root / "DATA_STATUS.md",
        *sorted(PROJECT_DIR.glob("*.md")),
        *sorted((PROJECT_DIR / "docs").glob("*.md")),
        *sorted((PROJECT_DIR / "data").glob("*.md")),
        PROJECT_DIR / "data" / "SOURCES.yaml",
        *sorted((PROJECT_DIR / "src").rglob("*.py")),
    ]
    texts = {p.relative_to(root).as_posix(): _normalise(p.read_text("utf-8")) for p in paths}
    for notebook in sorted((PROJECT_DIR / "notebooks").glob("*.ipynb")):
        cells = json.loads(notebook.read_text("utf-8"))["cells"]
        joined = "\n".join("".join(cell["source"]) for cell in cells)
        texts[notebook.relative_to(root).as_posix()] = _normalise(joined)
    return texts


DOCUMENTS = _documents()


def _sentences(text: str) -> list[str]:
    """Split on sentence ends and on table-cell bars: a cell is a statement of its own."""
    return [s.strip() for s in re.split(r"(?<=[.;:!?])\s+|\s*\|\s*", text) if s.strip()]


#: The files that carried the claim. A scan that reaches none of them passes everything.
MUST_SCAN = (
    "DATA_STATUS.md",
    "ROADMAP.md",
    "projects/gosplan/README.md",
    "projects/gosplan/docs/validation_anchors.md",
    "projects/gosplan/docs/data_dictionary.md",
    "projects/gosplan/data/ACCESS_NOTES.md",
    "projects/gosplan/data/SOURCES.yaml",
    "projects/gosplan/src/gosplan/acquire/agriculture.py",
    "projects/gosplan/src/gosplan/transcribe/targets.py",
    "projects/gosplan/notebooks/00_data_audit.ipynb",
)


@pytest.mark.parametrize("claim", sorted(RETRACTED_CLAIMS))
def test_a_retracted_claim_about_faostat_is_nowhere_in_the_tree(claim):
    pattern = re.compile(RETRACTED_CLAIMS[claim], re.IGNORECASE)
    hits = {
        name: match.group(0)
        for name, text in DOCUMENTS.items()
        if (match := pattern.search(text)) is not None
    }
    assert not hits, f"{claim}: {hits}"


def test_no_sentence_calls_faostat_independent_without_a_negation():
    """FAOSTAT's flag-A cotton is the official figure; "independent" next to it must be denied."""
    unscanned = [name for name in MUST_SCAN if "FAO" not in DOCUMENTS.get(name, "")]
    assert not unscanned, f"not scanned, or no longer mentions FAOSTAT: {unscanned}"
    offending = [
        (name, sentence)
        for name, text in DOCUMENTS.items()
        for sentence in _sentences(text)
        if NAMES_FAO.search(sentence)
        and INDEPENDENT.search(sentence)
        and not NEGATION.search(sentence)
    ]
    assert not offending, offending


def test_the_registry_glosses_faostat_flags_as_the_file_defines_them(sources_yaml):
    entry = {s.id: s for s in load_sources(sources_yaml)}[FAOSTAT_USSR]
    for field in ("notes", "download_plan", "evidence"):
        text = getattr(entry, field) or ""
        assert "unofficial" not in text.lower(), (
            f"{field} still glosses a FAOSTAT flag as unofficial"
        )
    plan = entry.download_plan or ""
    assert f"A={FAO_OFFICIAL}" in plan
    assert f"X={FAO_EXTERNAL}" in plan


def test_the_registry_says_the_ussr_seed_cotton_series_is_the_official_figure(sources_yaml):
    entry = {s.id: s for s in load_sources(sources_yaml)}[FAOSTAT_USSR]
    text = _normalise(" ".join(filter(None, (entry.notes, entry.download_plan, entry.evidence))))
    assert re.search(r"re-publi\w+ of the Soviet official", text, re.IGNORECASE), text


def test_the_faostat_acquirer_docstrings_classify_the_series_as_official():
    module_doc = _normalise(inspect.getdoc(agriculture) or "")
    europe_doc = _normalise(inspect.getdoc(agriculture.faostat_europe) or "")
    assert FAO_OFFICIAL in module_doc
    assert FAO_OFFICIAL in europe_doc and FAO_EXTERNAL in europe_doc
    assert "unofficial" not in europe_doc.lower()


@pytest.mark.parametrize(
    "target",
    [t for t in TARGETS if t.cross_check_source_id == FAOSTAT_USSR],
    ids=lambda t: t.target_id,
)
def test_a_target_cross_checked_against_faostat_says_what_kind_of_check_it_is(target):
    """A disagreement with FAOSTAT is a transcription error or a revision, never corroboration."""
    notes = _normalise(target.notes)
    assert "flag A" in notes and FAO_OFFICIAL in notes, notes
    assert re.search(r"\bvintage\b", notes), "a different official vintage is the other reading"
    for sentence in _sentences(notes):
        assert not (INDEPENDENT.search(sentence) and not NEGATION.search(sentence)), sentence


def _cotton_reconciliation_section() -> str:
    text = (PROJECT_DIR / "docs" / "validation_anchors.md").read_text("utf-8")
    match = re.search(r"^## The cotton reconciliation\b.*?(?=^## |\Z)", text, re.M | re.S)
    assert match, "validation_anchors.md has no section specifying the cotton reconciliation"
    return match.group(0)


def test_the_cotton_reconciliation_does_not_count_faostat_as_a_measurement():
    section = _cotton_reconciliation_section()
    lines = [ln for ln in section.splitlines() if ln.startswith("**Measurements:**")]
    assert len(lines) == 1, "the section must list its measurements on one **Measurements:** line"
    paragraph = section[section.index(lines[0]) :].split("\n\n", 1)[0]
    assert "USDA" in paragraph and "official figure" in paragraph
    assert not NAMES_FAO.search(paragraph), paragraph
    not_a_measurement = re.search(
        r"^\*\*Not a measurement:\*\*(.*?)(?:\n\n|\Z)", section, re.M | re.S
    )
    assert not_a_measurement and "FAOSTAT" in not_a_measurement.group(1)


def test_the_cotton_reconciliation_does_not_claim_two_sources_can_localise_the_error():
    section = _normalise(_cotton_reconciliation_section())
    assert re.search(r"cannot say which (?:source|one|of them) is wrong", section), section
    assert "Open question" in section


def test_the_reasons_the_section_gives_hold_in_the_pinned_library():
    """Each reason is a property of forensics_core.reconcile; check it on synthetic numbers.

    A library bump that changed one of them would leave the section wrong, and this is what
    would say so. The numbers are synthetic: no cotton figure of any source appears here.
    """
    section = _normalise(_cotton_reconciliation_section())
    assert "the third receives the largest standardised adjustment" in section
    assert "always equal in size and opposite in sign" in section
    assert "not positive definite" in section

    one_quantity = np.array([[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]])
    rng = np.random.default_rng(31)
    for _ in range(200):
        reported = rng.uniform(50.0, 150.0)
        # the official figure, its re-publication, and an outside estimate that differs
        y = np.array([reported, reported, reported * rng.uniform(0.5, 1.5)])
        sigma = rng.uniform(0.5, 20.0, size=3)
        z = np.abs(reconcile(y, one_quantity, sigma).standardized_adjustments)
        assert z[2] > z[0] and z[2] > z[1], (y, sigma, z)
        removed = [s.index for s in serial_elimination(y, one_quantity, sigma)]
        assert removed in ([], [2]), (y, sigma, removed)

    two_sources = np.array([[1.0, -1.0]])
    for _ in range(200):
        y = rng.uniform(50.0, 150.0, size=2)
        z = reconcile(y, two_sources, rng.uniform(0.5, 20.0, size=2)).standardized_adjustments
        assert z[0] == pytest.approx(-z[1]), z

    perfectly_correlated_copy = np.array([[4.0, 4.0, 0.0], [4.0, 4.0, 0.0], [0.0, 0.0, 9.0]])
    with pytest.raises(ValueError, match="positive definite"):
        reconcile(np.array([100.0, 100.0, 90.0]), one_quantity, perfectly_correlated_copy)
