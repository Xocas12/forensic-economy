# ROADMAP

The order in which this programme gets built, and why that order.

This document is a map, not a specification. Where it summarises `CONTRACT.md`, the contract
wins. Nothing in this file is a result,
and no number in any of these repositories may be cited as one.

## The programme

Statistical forensics of strategically reported data: detecting distortion in numbers produced
by agents with an incentive to distort them. Three repositories:

| Repository | Holds | Role |
|---|---|---|
| [`forensics-core`](https://github.com/Xocas12/forensics-core) | the shared method library | vendored into the other two as the submodule `packages/forensics_core` |
| [`forensic-elections`](https://github.com/Xocas12/forensic-elections) | `projects/elections` | the calibration project for digit and bunching methods |
| [`forensic-economy`](https://github.com/Xocas12/forensic-economy) | `projects/aaer`, `projects/china`, `projects/gosplan` | enforcement labels, provincial statistics, and the transfer target |

**Three projects have ground truth and one does not, and that asymmetry is the whole design.**
Methods are developed and scored where truth is knowable, then carried to the Soviet case where
it is not.

| Project | Labels | Role |
|---|---|---|
| `elections` | strong: three published, replicable signatures | calibrate digit and bunching methods |
| `aaer` | strong but selection-biased: enforcement actions | calibrate supervised and positive-unlabelled learning |
| `china` | partial: admitted episodes and a reform discontinuity | calibrate cross-source reconciliation |
| `gosplan` | almost none: **one** anchor event | **the target** |

**Unifying hypothesis.** Distortion concentrates at discontinuities in the incentive function.
Every project has a notch: the 100 per cent plan-fulfilment bonus, the round vote share, the
analyst consensus, the provincial growth target. The notch catalogue makes that a single experiment run
across four datasets instead of four separate stories.

**Second signal, weighted equally.** Fabricated series contain too little noise. A reported
yield series with less year-on-year variance than rainfall permits is impossible regardless of
its level.

## What each phase can establish

The "cannot establish" column is binding. An artefact from an early phase is not evidence for a
later claim, however suggestive it looks.

| Phase | Establishes | Cannot establish |
|---|---|---|
| **P0** acquisition | what is obtainable, at what cost, with what provenance | anything statistical whatsoever |
| **P1** calibration infrastructure | power as a function of sample size, effect size and aggregation; false-positive behaviour on controls | anything about whether a real dataset is honest |
| **P2** replication | that the implementation reproduces published results where labels are strong | anything about china or gosplan |
| **P3** reconciliation | whether the methods recover the admitted Chinese episodes | Soviet distortion |
| **P4** transfer | a bound under explicitly stated assumptions | a point estimate of aggregate Soviet distortion, or any causal claim |
| **P5** synthesis | what the programme learned, including what failed | |

## The gates

Each gate is a tracking issue in `forensics-core`, signed by the owner. Nothing downstream
starts until it is signed.

| Gate | Signs off that | Unblocks |
|---|---|---|
| **G0** data | the data is in hand or its absence is explained; the money decisions are made | P1 |
| **G1** methods frozen and pre-registered | the calibration infrastructure exists and the analysis plan is committed **before** any project-level result | P2, P3 |
| **G2** replication | elections and aaer hit or missed their published targets, documented either way | P5 |
| **G3** reconciliation | china is done, **and the gosplan anchor is unsealed** | P4 |
| **G4** transfer | the gosplan analysis has run once and been reported | P5 |
| **G5** final report | every claim carries its false-positive behaviour and its assumptions | |

## The held-out anchor

**This is the most important methodological rule in the programme.**

The Uzbek cotton affair, 1978 to 1983, is gosplan's only anchor. With one anchor, any peeking
destroys the claim, because a detector tuned while looking at its only test case is fit and
validated on the same event.

Therefore the cotton series, its physical correlates, and any breakdown that isolates it **must
not be plotted, tested, scored or summarised before G3 is signed.** Acquiring, transcribing and
validating that data is permitted. Looking at its distributional properties is not.

The held-out seal enforces this in code rather than in prose, because the person who breaks the rule will
be someone who forgot it. The seal refuses to return held-out rows without a token that does not
exist until G3 is signed.

## The ideas this roadmap is built around

Five things worth knowing before reading the plan, because most of the work exists to serve
one of them.

1. **The power atlas.** elections has about 95,000 precincts; gosplan
   will have a few hundred sector-years. The most valuable thing the calibration projects can
   hand the target project is not a detector, it is a power curve. If integer-percentage excess
   has no power at n = 300, gosplan cannot use it, and knowing that before P4 saves a phase.
   The aggregation ladder answers the companion question: Soviet data is aggregate, so how much
   power survives aggregation? elections can answer that because it has a real hierarchy.

2. **The injection harness.** gosplan has no labels, so make some: inject a distortion
   of known magnitude into a series believed clean and measure recovery. This is the only way to
   get an operating characteristic on the target's own data shape. The harness is deliberately
   built so an injector is not the estimator run backwards, because otherwise the power curve
   measures self-consistency.

3. **The false-positive budget.** A detector that fires everywhere is
   useless. elections holds the programme's only genuine external controls, two non-Russian
   elections shipped in the same supplement as a replication target. Every claim ships with its
   behaviour on data where nothing should be found, and gosplan inherits that number because it
   cannot compute one of its own.

4. **The `gosplan-env` coupling.** The sibling repository simulates enterprises
   facing a plan, a bonus notch, an audit and a ratchet, and it knows the true quantity behind
   every reported one. That is a detector test bench for exactly the data shape gosplan faces.
   Its own plan scopes this coupling to **estimator robustness and nothing else**, and that
   scope is a feature: a detector that cannot find a distortion the simulator generated will not
   find one in the archives either, which is the strongest negative result available here. No
   number from a simulator is evidence about the historical USSR.

5. **A second, weaker label set.** A case-level dataset of Soviet plan-fraud
   prosecutions, 1943 to 1962, recording reported against actual quantities. It is not a second
   anchor: it is prosecution-selected exactly as the enforcement releases are, and it covers a
   different period. But it may convert gosplan from one anchor to one anchor plus a
   positive-unlabelled label set, which would be a real upgrade to a project whose central
   weakness is having no labels. It should be approached sceptically.


## The gates, as issues

| Gate | Issue |
|---|---|
| G0 | [GATE G0](https://github.com/Xocas12/forensics-core/issues/1) |
| G1 | [GATE G1](https://github.com/Xocas12/forensics-core/issues/2) |
| G2 | [GATE G2](https://github.com/Xocas12/forensics-core/issues/3) |
| G3 | [GATE G3](https://github.com/Xocas12/forensics-core/issues/4) |
| G4 | [GATE G4](https://github.com/Xocas12/forensics-core/issues/5) |
| G5 | [GATE G5](https://github.com/Xocas12/forensics-core/issues/6) |

## Plan for this repository (forensic-economy)

Status is as of the last data audit. "Done" means executed against real data and its output
committed, not that code exists for it.

### aaer

| # | Task | Phase | Status |
|---|---|---|---|
| 1 | Acquire the data and record what actually arrived | P0 | **done for the replication panel** - the Bao et al. (2020) archive is in `data/raw/bao`, checksummed and described in [`projects/aaer/DATA_AUDIT.md`](projects/aaer/DATA_AUDIT.md). The SEC bulk path is still unfetched |
| 2 | Parse the enforcement listing into a structured table | P0 | code written, not run against the live listing |
| 3 | Validate the XBRL tag mapping against real filings | P0 | open - eleven of the twelve mappings are unconfirmed; only `AccountsReceivableNetCurrent` has been seen in a real response |
| 4 | Build the label join, or establish it cannot be built from free sources | P0 | **partly answered** - the Bao archive ships the label already joined to `gvkey` x `fyear`, which sidesteps the name-to-CIK join for that path |
| 5 | Decide the two access questions that determine what aaer can be | P0 | open, needs a human - free SEC 2009+, the Bao panel, or licensed Compustat |
| 6 | Beneish baseline | P2 | blocked behind G1. The panel supplies 9 of the 12 items the M-score needs; `ppent`, `xsga` and `oancf` are absent, so four of the eight components cannot be formed as published. See the audit |
| 7 | Positive-unlabelled benchmark against the corrected published figures | P2 | blocked - the erratum carrying the corrected targets is paywalled and has not been read first-hand |
| 8 | Populate the notch catalogue and test earnings bunching | P2 | blocked behind G1 |

### china

| # | Task | Phase | Status |
|---|---|---|---|
| 1 | Acquire the provincial and national series | P0 | blocked - the provincial GDP tables are published as JPEG photographs, and the query API returns 403 |
| 2 | Choose and pin an OCR back end, gated on the arithmetic checks | P0 | open, and it is the binding constraint: no provincial number can be read by any code in this tree today |
| 3 | Build the Chinese-to-canonical province map from a fetched page | P0 | open - the loader refuses to guess it |
| 4 | Register a provincial boundary shapefile | P1 | open - without it the free nightlights data is unusable |
| 5 | Find a source for provincial growth targets | P1 | open - without it the bunching test degrades to a round-number scan |
| 6 | The gap, proxy, dispersion, reform and bunching analyses | P2 | blocked behind G1 and behind tasks 1-3 |

### gosplan

| # | Task | Phase | Status |
|---|---|---|---|
| 1 | Transcribe the first target twice, independently, and publish the per-digit disagreement rate | P0 | open, needs human eyes. It gates whether any digit test is usable at all |
| 2 | Locate the republic-level yearbook, or write up its absence | P0 | open - not found in any digitised form |
| 3 | Find a pre-1992 hydrological series, or accept the two crop sources as the only physical check | P1 | open |
| 4 | Resolve the internal inconsistency in the anchor magnitude | P1 | open - the source gives an aggregate that its own per-year figures do not reproduce |
| 5 | Loaders for the machine-readable sources the acquirers already fetch | P1 | open - there is no `clean/` package here at all |
| 6 | The plan-fulfilment, hidden-inflation, dispersion and reconciliation analyses | P3+ | blocked. The anchor may not be plotted, tested, scored or summarised before G3, and `src/gosplan/seal.py` enforces that in code |

## Plans in the other repositories

- [forensics-core](https://github.com/Xocas12/forensics-core) - the library, built
- [forensic-elections](https://github.com/Xocas12/forensic-elections) - run; see its `RESULTS.md`

## Working rules

One task, one branch, one pull request, scoped to the files that task needs.

When the plan and the data do not determine a choice, stop and write the question down rather
than picking the reasonable default. Recording an unresolved question is a complete outcome.

The full rules are in [`CONTRACT.md`](CONTRACT.md): thirteen of them, each stating what a
violation looks like concretely and what catches it. The file is identical in all three
repositories, and `test_contract.py` freezes the rule numbers, because `gosplan/seal.py`
cites rule 5 and `eval/harness.py` cites rule 9 by number.

## Where this stands

No analysis has been run in this repository and every module under an `analysis/` directory
still raises `NotImplementedError`. What has changed is that one of the three projects now has
its data: the aaer replication panel is acquired, loaded, tested and described in
[`projects/aaer/DATA_AUDIT.md`](projects/aaer/DATA_AUDIT.md) - 146,045 firm-years, 964 of them
labelled, a base rate of 0.66 per cent.

Describing it is as far as rule 4 allows before the gate opens, and the audit stops there
deliberately. The calibration project in the sibling repository has been run and has a result;
this one has not.
