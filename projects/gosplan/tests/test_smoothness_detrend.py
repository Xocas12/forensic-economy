"""The driver-free smoothness test must default to a detrending that has power on trended levels.

``forensics_core.dispersion.too_smooth_test`` documents that ``detrend="diff"`` has
essentially no power on a trend-stationary series and that ``detrend="none"`` flags any
trend. Reported Soviet harvest and output levels are trended, so the stub must not default to
the first nor offer the second, its plan must not report "none", and the research question
must state the choice with its simulated size and power. Synthetic series only.
"""

from __future__ import annotations

import importlib.util
import inspect
import re
import typing
from pathlib import Path

import numpy as np
from gosplan.analysis import harvest_dispersion
from gosplan.analysis.harvest_dispersion import smoothness_of_reported_series

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "projects" / "gosplan" / "docs" / "research_question.md"
SCRIPT = ROOT / "scripts" / "smoothness_size_power.py"


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_default_detrend_is_linear_not_diff():
    default = inspect.signature(smoothness_of_reported_series).parameters["detrend"].default
    assert default == "linear"


def test_none_is_not_an_allowed_detrend_for_trended_levels():
    hints = typing.get_type_hints(smoothness_of_reported_series)
    assert set(typing.get_args(hints["detrend"])) == {"linear", "diff"}


def test_plan_no_longer_reports_all_three_treatments():
    texts = [
        _flat(inspect.getdoc(smoothness_of_reported_series) or ""),
        _flat(harvest_dispersion.__doc__ or ""),
    ]
    try:
        smoothness_of_reported_series(None, detrend="linear")
    except NotImplementedError as exc:
        texts.append(str(exc))
    for text in texts:
        assert "all three" not in text
        assert "about 2 for independent noise" not in text


def test_research_question_states_detrend_with_size_and_power():
    doc = DOC.read_text(encoding="utf-8")
    assert 'Stated choice: `detrend="linear"`' in doc
    rows = [line for line in doc.splitlines() if line.startswith("| trend + iid | honest |")]
    assert {row.split("|")[3].strip() for row in rows} == {"none", "linear", "diff"}
    assert any(line.startswith("| trend + ar09 | smoothed | linear |") for line in doc.splitlines())


def _load_script():
    spec = importlib.util.spec_from_file_location("smoothness_size_power", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_simulation_shows_only_linear_carries_information_on_trended_levels():
    sim = _load_script()
    series = sim.FAMILIES["levels"]()
    honest = series["trend + iid"][1]
    smoothed = series["trend + ar09"][1]

    def rate(make, detrend):
        return sim.rejection_rate(make, 30, detrend, reps=40, n_perm=99, alpha=0.05, seed=7)

    assert rate(honest, "none") == 1.0  # flags the trend itself
    assert rate(honest, "linear") <= 0.15
    assert rate(smoothed, "linear") >= 0.8
    assert rate(smoothed, "diff") <= 0.2  # documented as powerless here
    assert np.isfinite(rate(honest, "diff"))
