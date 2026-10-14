"""The replication protocol for the Bao et al. benchmark, as the specification states it.

The published window figures come from a per-test-year loop in the authors' posted code
(``run_RUSBoost.m``, ``evaluate.m``): retrain on 1991 to t - 2, recode serial frauds against
year t's positive cases, score year t alone with k = round(0.01 n), then average over the
window. A single pooled temporal fold with no gap is a different estimand, so the spec must
not describe it as Bao's design. Nothing here computes a result; these tests pin what the
stubs and the docs promise, so the replication cannot quietly drift back to one fold.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from aaer.analysis import pu_benchmark

_AAER = Path(__file__).resolve().parents[1]
_DOCS = _AAER / "docs"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    """Collapse whitespace so a phrase still matches when a line wrap falls inside it."""
    return re.sub(r"\s+", " ", text)


def test_the_protocol_constants_match_the_posted_code():
    assert pu_benchmark.BAO_TRAIN_START == 1991
    assert pu_benchmark.BAO_GAP_YEARS == 2
    assert pu_benchmark.BAO_K_FRACTION == 0.01
    assert pu_benchmark.BAO_K_ROUNDING == "half_away_from_zero"
    assert pu_benchmark.BAO_LIKE_FOR_LIKE_LABELS == "bao_ex_post"


def test_every_window_leaves_room_for_the_gap_after_the_first_training_year():
    for first, last in pu_benchmark.BAO_TEST_WINDOWS:
        assert first <= last
        assert first - pu_benchmark.BAO_GAP_YEARS >= pu_benchmark.BAO_TRAIN_START


def test_run_pu_benchmark_specifies_per_test_year_retraining_not_one_fold():
    doc = _flat(inspect.getdoc(pu_benchmark.run_pu_benchmark) or "")
    assert "for each test year" in doc
    assert "two-year gap" in doc
    assert "p_aaer" in doc and "recode" in doc
    assert "rounded halves away from zero" in doc
    assert "average the per-year metrics" in doc
    assert 'One pooled ``split="temporal"`` fold is not this design' in doc
    # The pre-fix default, which read as one fold, must not come back.
    assert "temporal split matching" not in doc


def test_the_stub_message_names_the_per_year_loop():
    source = inspect.getsource(pu_benchmark.run_pu_benchmark)
    message = _flat(source[source.index("raise NotImplementedError") :])
    assert "per-test-year loop" in message
    assert "1991..t-2" in message
    assert "round(0.01 n)" in message


def test_the_module_states_which_labels_the_like_for_like_run_uses():
    doc = _flat(pu_benchmark.__doc__ or "")
    assert "The protocol to replicate" in doc
    assert "ex-post labels" in doc
    assert "release-censored variant" in doc
    assert "reported **separately**" in doc


def test_validation_anchors_carries_the_replication_protocol():
    text = _flat(_read(_DOCS / "validation_anchors.md"))
    assert "### Replication protocol" in text
    assert "under the same protocol (below), using the same labels" in text
    assert "two-year gap" in text
    assert "recodes serial frauds against that test year" in text
    assert "round(0.01 * n)" in text and "halves away from zero" in text
    assert "unweighted mean of the per-year figures" in text
    assert "ex-post labels" in text
    assert "release-censored" in text
    assert "different estimand" in text


_SINGLE_FOLD_AS_BAO = (
    # pu_benchmark's old default: the harness's one temporal fold, presented as Bao's windows.
    "temporal split matching",
    # The leakage trap was attributed to the erratum, which is about serial-fraud recoding.
    "exactly the leakage the 2022 erratum was about",
    "concerns exactly this kind of leakage",
)


def test_nothing_in_the_project_presents_one_pooled_fold_as_the_published_design():
    files = [
        *sorted(_DOCS.glob("*.md")),
        _AAER / "README.md",
        *sorted((_AAER / "src" / "aaer").rglob("*.py")),
    ]
    offenders = [
        f"{path.relative_to(_AAER)}: {phrase!r}"
        for path in files
        for phrase in _SINGLE_FOLD_AS_BAO
        if phrase in _flat(_read(path))
    ]
    assert not offenders, offenders
