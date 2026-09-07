# forensic-economy

Statistical forensics of strategically reported data — the three **economic-statistics**
projects. One of two project repositories that share the
[`forensics-core`](packages/forensics_core/) method library (a git submodule); the other is
`forensic-elections`.

## The programme

Three of four projects have ground truth; one does not. That asymmetry is the whole design:
methods are developed and scored where truth is knowable, then carried to the Soviet case
where it is not.

| Project | Repository | Labels | Role |
|---|---|---|---|
| `elections` | forensic-elections | Strong (published signatures, replicable prior findings) | Calibrate digit and bunching methods |
| `aaer` | **this repo** | Strong (SEC enforcement actions as positives) | Calibrate supervised / PU learning, benchmark against published AUC |
| `china` | **this repo** | Partial (self-admitted falsification, a statistical-reform discontinuity) | Calibrate cross-source reconciliation against physical proxies |
| `gosplan` | **this repo** | Almost none (one anchor event) | **The target.** Methods validated above are transferred here |

**Unifying hypothesis.** Distortion concentrates at discontinuities in the incentive
function: the 100 % plan-fulfilment bonus threshold, the analyst-consensus EPS, the
provincial growth target. `forensics_core.bunching.notch.scan_candidate_notches` makes
"find the notch, estimate excess mass around it" a first-class operation.

**Second signal, equally weighted.** Fabricated series contain *too little* noise. A reported
yield series with less year-on-year variance than rainfall permits is impossible regardless
of level (`forensics_core.dispersion`).

## The three projects

| | Question | Docs |
|---|---|---|
| `aaer` | Reproduce the Beneish M-score baseline and the Bao et al. (2020) ML benchmark with SEC enforcement releases as labels | [README](projects/aaer/README.md) · [docs](projects/aaer/docs/) |
| `china` | Measure the provincial-sum vs national GDP gap; test provincial series against physical proxies; use the unified-accounting reform as a natural experiment | [README](projects/china/README.md) · [docs](projects/china/docs/) |
| `gosplan` | Bound the volume of reporting distortion in Soviet statistics using methods calibrated above. Mostly transcription, not downloads | [README](projects/gosplan/README.md) · [docs](projects/gosplan/docs/) |

## Layout

```
forensic-economy/
├── config/forensics.toml        contact string (REQUIRED before any fetch) and per-host rate limits
├── packages/forensics_core/     git submodule → forensics-core
├── projects/{aaer,china,gosplan}/
│   ├── README.md                question, data status, current state, next actions
│   ├── data/SOURCES.yaml        the source registry — nothing enters a pipeline without an entry
│   ├── data/ACCESS_NOTES.md     what failed, what is gated, what needs a human
│   ├── data/{raw,interim,processed}/   gitignored; rebuilt by `make data`
│   ├── src/<name>/{acquire,clean,features,analysis}/
│   ├── notebooks/00_data_audit.ipynb
│   ├── docs/{research_question,data_dictionary,validation_anchors,known_traps}.md
│   └── tests/
└── DATA_STATUS.md               source × project × access tier × status
```

## How to run

Requirements: [`uv`](https://docs.astral.sh/uv/), GNU make, git. Python 3.12 is pinned.

```sh
git clone --recurse-submodules <this repo>     # or: make submodule after a plain clone
make setup          # submodule init + uv sync --all-packages + pre-commit hooks
make test
make lint
# Put a real name and email in config/forensics.toml ([http].contact) first — every
# network script refuses to run while the placeholder is in place (SEC EDGAR requires it).
make data           # all three projects; never fabricates; fails loudly per source
make data-aaer      # one project
make validate-sources
```

## Rules the code enforces

1. No invented URLs: sources are verified by an actual fetch (HTTP status, bytes, SHA-256,
   timestamp) or recorded as `unverified` / `blocked` with a reason.
2. Every fetch attempt is logged.
3. No synthetic data under `data/`; fixtures live in `tests/fixtures/` with a `synthetic_` prefix.
4. Fail loudly and continue.
5. Raw data never enters git (`.gitignore` plus a pre-commit hook).
6. Access policies are respected: contact header, per-host rate limits, aggressive caching.
7. "Not found" and "not free" are different statuses.

## Status

Scaffold, shared library, source registries and acquisition pipelines built; free sources
attempted. **No analysis has been run and no findings exist in this tree.** See
[DATA_STATUS.md](DATA_STATUS.md).
