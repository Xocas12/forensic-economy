"""Read the anchor's rank off a full-panel score table, against a stated comparator set.

This is the last step of the transfer check in :mod:`gosplan.analysis.transfer`: a detector
fitted on a source project scores every row of the gosplan panel, and the question is where
the anchor rows land among the rows that are not the anchor.

It is bookkeeping, not analysis. It fits nothing, estimates nothing and reads no data; it
takes scores someone else produced and counts how many comparator rows sit at or above each
anchor row. Until G3 it is only ever called on synthetic fixtures (CONTRACT rules 4 and 5).

Why this and not ``EvalSpec(split="anchor_holdout")``: that split makes the test fold exactly
the anchor rows. Every one of them is either a positive or unlabelled, so the fold has no
negative to rank against and :func:`forensics_core.eval.harness.evaluate` raises. The
"fitted without seeing the anchor" guarantee does not need that split here either:
:func:`forensics_core.eval.harness.transfer` fits on the source project, so no gosplan row,
anchor or not, is ever in the fit set.

The comparator set is fixed here, before anything is scored: **every row of the full panel
that is not an anchor row**, with no restriction to the anchor's sector or years. That is
what ``docs/validation_anchors.md`` check 1 asks for ("at or near the top when applied blind
to the full panel"). A within-sector ranking would be a different question and is not what
this function answers.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd

__all__ = ["COMPARATOR_SET", "anchor_rank"]

#: The pre-registered comparator set, in words, so that a report can quote it verbatim.
COMPARATOR_SET = "every non-anchor row of the full panel"


def anchor_rank(
    scores: pd.DataFrame,
    anchor_units: Iterable[object],
    *,
    top_k: float = 0.05,
) -> pd.DataFrame:
    """Rank each anchor row against the comparator set.

    Parameters
    ----------
    scores : pandas.DataFrame
        One row per panel unit with columns ``unit_id`` and ``score`` (higher = more
        suspicious), such as :attr:`forensics_core.eval.harness.TransferResult.scores`. It
        must cover the whole panel: a score table that has already been filtered would
        silently shrink the comparator set.
    anchor_units : iterable
        The ``unit_id`` values of the anchor rows, e.g. ``target.unit_id[anchor_mask]``.
    top_k : float, default 0.05
        Fraction of the full panel (anchor plus comparators) counted as "the top".

    Returns
    -------
    pandas.DataFrame
        One row per anchor unit, best-ranked first, with columns:

        ``unit_id``, ``score``;
        ``n_comparators_at_or_above`` -- comparator rows scoring at least as high (ties count
        against the anchor);
        ``rank`` -- ``1 + n_comparators_at_or_above``, the position the row would take among
        the comparators, so that anchor rows do not push one another down;
        ``n_comparators`` -- the size of the comparator set;
        ``top_k_cutoff`` -- ``ceil(top_k * n_panel)``;
        ``in_top_k`` -- ``rank <= top_k_cutoff``.

    Raises
    ------
    ValueError
        If ``scores`` lacks the columns, has duplicate units or non-finite scores, if an
        anchor unit is missing from ``scores``, if there are no anchor rows or no comparator
        rows, or if ``top_k`` is not in (0, 1].
    """
    missing_cols = {"unit_id", "score"} - set(scores.columns)
    if missing_cols:
        raise ValueError(f"scores needs columns unit_id and score; missing {sorted(missing_cols)}")
    if not 0.0 < float(top_k) <= 1.0:
        raise ValueError(f"top_k must be a fraction in (0, 1]; got {top_k!r}")
    units = scores["unit_id"]
    if bool(units.duplicated().any()):
        raise ValueError("scores has duplicate unit_id values")
    values = pd.to_numeric(scores["score"], errors="coerce").to_numpy(dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("scores contains missing or non-finite values")

    anchor = list(dict.fromkeys(anchor_units))
    if not anchor:
        raise ValueError("no anchor units given")
    is_anchor = units.isin(anchor).to_numpy()
    absent = [u for u in anchor if u not in set(units)]
    if absent:
        raise ValueError(f"{len(absent)} anchor units are not in scores, e.g. {absent[:5]}")
    comparator_scores = values[~is_anchor]
    if comparator_scores.size == 0:
        raise ValueError("every row is an anchor row; there is nothing to rank against")

    n_panel = values.size
    cutoff = max(1, math.ceil(float(top_k) * n_panel))
    anchor_scores = values[is_anchor]
    above = np.array([int(np.sum(comparator_scores >= s)) for s in anchor_scores], dtype=int)
    out = pd.DataFrame(
        {
            "unit_id": units.to_numpy()[is_anchor],
            "score": anchor_scores,
            "n_comparators_at_or_above": above,
            "rank": above + 1,
            "n_comparators": int(comparator_scores.size),
            "top_k_cutoff": cutoff,
        }
    )
    out["in_top_k"] = out["rank"] <= cutoff
    return out.sort_values(
        ["rank", "score"], ascending=[True, False], kind="mergesort"
    ).reset_index(drop=True)
