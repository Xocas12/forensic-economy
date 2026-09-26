#!/usr/bin/env python
"""Describe the acquired aaer panel and write DATA_AUDIT.md.

This counts rows and describes coverage. It does not fit, score, test or estimate anything:
CONTRACT rule 4 permits the former at any phase and forbids the latter until the gate that
authorises it opens, and that gate is not open. Nothing here is a finding about accounting
fraud.

Usage
-----
    uv run python scripts/audit_aaer_panel.py
"""

from __future__ import annotations

import datetime as _dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "projects" / "aaer" / "data"
OUT = ROOT / "projects" / "aaer" / "DATA_AUDIT.md"


def _sha(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    sys.path.insert(0, str(ROOT / "projects" / "aaer" / "src"))
    from aaer.clean.bao import (
        BAO_FILES,
        BENEISH_ITEMS_ABSENT,
        BENEISH_ITEMS_PRESENT,
        coverage,
        load_bao_panel,
    )

    try:
        panel = load_bao_panel(DATA)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2

    table = coverage(panel)
    raw = DATA / "raw" / "bao"

    lines: list[str] = []
    a = lines.append
    a("# DATA_AUDIT: aaer")
    a("")
    a(
        f"Written by `scripts/audit_aaer_panel.py` on {_dt.date.today().isoformat()} at commit "
        f"`{_git_sha()}`. Every number was computed from the file on disk."
    )
    a("")
    a(
        "**This is not analysis.** CONTRACT rule 4 permits loading, cleaning, counting rows "
        "and describing coverage at any phase, and forbids fitting, testing, scoring and "
        "estimating until the gate opens. This file does the former only. Nothing in it is a "
        "statement about accounting fraud."
    )
    a("")

    a("## What was acquired")
    a("")
    a("| file | bytes | sha256 (first 16) |")
    a("|---|---:|---|")
    for name in BAO_FILES.values():
        path = raw / name
        if path.is_file():
            a(f"| `{name}` | {path.stat().st_size:,} | `{_sha(path)[:16]}` |")
        else:
            a(f"| `{name}` | - | not present |")
    a("")
    a(
        "Bao, Y., B. Ke, B. Li, Y. J. Yu and J. Zhang (2020), *Journal of Accounting Research* "
        "58(1), 199-235; replication archive <https://github.com/JarFraud/FraudDetection>. "
        "Registry entry `bao_replication`."
    )
    a("")

    a("## The panel")
    a("")
    a("| quantity | value |")
    a("|---|---:|")
    a(f"| firm-years | {panel.n_rows:,} |")
    a(f"| distinct firms (`gvkey`) | {panel.n_firms:,} |")
    a(f"| fiscal years | {panel.n_years} ({panel.year_min}-{panel.year_max}) |")
    a(f"| rows labelled `misstate = 1` | {panel.n_positive:,} |")
    a(f"| distinct AAER cases (`p_aaer`) | {panel.n_aaer_cases} |")
    a(f"| base rate | {panel.base_rate:.4%} |")
    a("")
    a(
        "The base rate is the number that governs everything downstream. At roughly one "
        "labelled firm-year in 150, accuracy is worthless as a metric and a detector that "
        'predicts "no misstatement" everywhere scores above 99 per cent. This is why '
        "CONTRACT rule 10 admits rank metrics only, with the base rate printed beside them."
    )
    a("")

    a("## Coverage by fiscal year")
    a("")
    a("| fiscal year | firm-years | labelled | base rate |")
    a("|---:|---:|---:|---:|")
    for _, r in table.iterrows():
        a(f"| {int(r.fyear)} | {int(r.n_rows):,} | {int(r.n_positive)} | {r.base_rate:.4%} |")
    a("")
    last = table.tail(5)
    a(
        f"The label density falls away at the end of the panel: {int(last.n_positive.sum())} "
        f"labelled rows across {int(last.n_rows.sum()):,} firm-years in "
        f"{int(last.fyear.min())}-{int(last.fyear.max())}. That is the well-known enforcement "
        "lag rather than a fall in misstatement, since an AAER is published years after the "
        "fiscal year it concerns. Any train/test split along the time axis inherits it."
    )
    a("")

    a("## What this panel cannot support")
    a("")
    a(
        f"`aaer.features.beneish` needs twelve items per firm-year. This panel supplies "
        f"{len(BENEISH_ITEMS_PRESENT)} of them:"
    )
    a("")
    a("```")
    a("present: " + ", ".join(BENEISH_ITEMS_PRESENT))
    a("```")
    a("")
    a("Three are absent and cannot be recovered from what is here:")
    a("")
    a("| Beneish input | needs | status in this panel |")
    a("|---|---|---|")
    for item, note in BENEISH_ITEMS_ABSENT.items():
        a(f"| `{item}` | Compustat `{note.split()[0]}` | {note} |")
    a("")
    a(
        "Consequently DSRI, GMI, SGI and LVGI are computable as published; AQI and DEPI only "
        "by substituting gross for net property, plant and equipment, which is a different "
        "ratio from the one Beneish (1999) estimated his coefficients on; SGAI not at all; "
        "and TATA not at all in the cash-flow form implemented here. **A four-component "
        "score is not the Beneish M-score** and the published coefficients do not transfer to "
        "it. Closing this gap needs Compustat `ppent`, `xsga` and `oancf`, from the SEC "
        "Financial Statement Data Sets (2009 onward, free) or from Compustat itself (licensed)."
    )
    a("")

    a("## What has not been done")
    a("")
    a(
        "No detector has been fitted and nothing has been scored. The aaer replication sits "
        "behind gate G1, which requires a pre-registered analysis plan that does not yet "
        "exist, and `analysis/beneish_baseline.py` still raises `NotImplementedError`. The "
        "replication target is an AUC of 0.7428 and an NDCG@1% of 0.0394 for 2003-2005 - "
        "and those are the erratum values, which have not been read first-hand because the "
        "erratum is paywalled. Until it is read, the target itself is second-hand."
    )
    a("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(
        f"  {panel.n_rows:,} firm-years, {panel.n_positive:,} labelled, base rate {panel.base_rate:.4%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
