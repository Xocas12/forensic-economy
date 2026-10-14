# Validation anchors — aaer

What a working method must reproduce. Every fact below was read from the source cited during
the scaffolding session; items marked **TO CONFIRM** were not, and must be checked before use.

## Tier 0 — the Beneish M-score must be arithmetically right

The eight coefficients, the intercept and the flag threshold hard-coded in
`aaer.features.beneish` were **confirmed** against the June 1999 working-paper version of

> Beneish, M. D. (1999). "The Detection of Earnings Manipulation." *Financial Analysts
> Journal* 55(5): 24–36.

read at `https://www.calctopia.com/papers/beneish1999.pdf`, Table 3 Panel A, the
**unweighted probit** row. The typeset journal version is behind the publisher's paywall and
was not read.

| Term | Coefficient | t-statistic in the paper |
|---|---|---|
| Constant | −4.840 | −11.01 |
| DSRI | 0.920 | 6.02 |
| GMI | 0.528 | 2.20 |
| AQI | 0.404 | 3.20 |
| SGI | 0.892 | 5.39 |
| DEPI | 0.115 | 0.70 (not significant) |
| SGAI | −0.172 | −0.71 (not significant) |
| TATA | 4.679 | 3.73 |
| LVGI | −0.327 | −1.22 (not significant) |

**Threshold.** The paper states that at relative error costs of 20:1 or 30:1 the model
classifies a firm as a manipulator when the estimated probability exceeds .0376, "a score
greater than −1.78". At 10:1 the cut-off is −1.49 (probability .0685). So −1.78 is not a
universal constant: it encodes an assumed cost ratio, and any table using it should say so.

**Two things not to inherit uncritically.** The same Table 3 reports a WESML (weighted
exogenous sampling maximum likelihood) variant with a different intercept and coefficients;
the code implements the unweighted probit. And the widely quoted "five-variable Beneish
model" is **unverified**: its coefficients are not in the 1999 working paper and appear only
on commercial websites, one of which mislabels a term. Do not implement it from those.

**Unit test that pins the arithmetic.** With every index at 1 and TATA at 0, M = −4.84 + 2.36
= −2.48, below the threshold, so a "neutral" firm is not flagged. This is asserted in
`tests/test_beneish.py`.

## Tier 1 — the published machine-learning benchmark

> Bao, Ke, Li, Yu & Zhang (2020). "Detecting Accounting Fraud in Publicly Traded U.S. Firms
> Using a Machine Learning Approach." *Journal of Accounting Research* 58(1).

**The original numbers are not the target. The corrected ones are.** A 2022 erratum
(*JAR* 60(4): 1635–1646, DOI 10.1111/1475-679X.12454) states that an error in the authors'
posted code "led to an overstatement of model performance metrics": roughly 10 % of firm-years
belonging to serial-fraud cases that span the training period were not recoded to zero.

Corrected performance of the RUSBoost model with 28 raw financial items:

| Test window | AUC | NDCG@1 % | Hits |
|---|---|---|---|
| 2003–2005 | 0.7428 | 0.0394 | 9 |
| 2003–2008 | 0.7228 | 0.0237 | 10 |

**Provenance caveat, and it matters.** These figures were read from Walker (2022) in
*Econ Journal Watch* (`https://econjwatch.org/file_download/1245/WalkerSept2022.pdf`), which
tabulates the erratum; the erratum PDF itself is behind the publisher's paywall (HTTP 403),
and the *original* published AUC and NDCG values were not read from any accessible source.
Walker's own re-runs of the corrected code produced 8 hits in both windows rather than 9 and
10. **TO CONFIRM:** obtain the erratum through the university subscription and replace this
table with figures read from it directly.

**What counts as reproduced.** Matching AUC to within roughly ±0.02 on the same test windows,
under the same protocol (below), using the same labels, before claiming any improvement. Note
that this is not achievable on the free data path without resolving the coverage problem
below.

### Replication protocol

This section is the replication's specification; the G1 analysis plan, when it is written,
carries it over unchanged or says what it changes and why. It was read from the authors'
posted code, `run_RUSBoost.m` and `evaluate.m` in `JarFraud/FraudDetection` at commit
2d10bc6 (the `jarfraud_github_repo` entry in `data/SOURCES.yaml`), not from the paper.

The published figures are **not** one model scored on one pooled test set. For each test year
*t* from 2003 to 2014 the code:

1. **retrains** on fiscal years 1991 to *t* − 2, leaving a **two-year gap** between the last
   training year and the test year;
2. **recodes serial frauds against that test year**: every training row whose `p_aaer` is
   among the `p_aaer` values of year *t*'s positives is set to 0 before fitting;
3. **scores year *t* alone**, with *k* for NDCG@k and the other top-*k* metrics computed on
   year *t*'s firm-years as `round(0.01 * n)`. MATLAB's `round` takes halves away from zero;
   Python's `round` takes them to even, and the shared harness turns a fractional *k* into
   `ceil(k * n)`, which is one more than `round` whenever the fractional part of `0.01 * n`
   is strictly between 0 and 0.5. The replication passes the integer *k* explicitly.

A window figure is the **unweighted mean of the per-year figures** over the window's years.
For AUC this is checked: Walker's per-year AUCs (2003 0.7281, 2004 0.7646, 2005 0.7289,
2006 0.7590, 2007 0.7176, 2008 0.6280) average to 0.7405 and 0.7210, the Run(1) window
figures of his Table 2 (`ejw_walker_2022`). For NDCG@1 % the mean is assumed the same way, and
the window's hits are assumed to be the per-year sum; neither is checked against a per-year
table.

So a single temporal fold — train on everything up to one year, test on every later year
pooled, no gap and no window end, which is what `EvalSpec(split="temporal")` in
`forensics_core` does — is a **different estimand**, and a number from it is not a hit or a
miss against the table above. Retraining for each test year uses fresher data than one frozen
model does, so the two designs need not agree even with the same model and labels, and the
difference is not bounded by anything this repository has measured.

**Labels.** The like-for-like run uses the pinned Bao et al. CSV's `misstate` as it stands:
the authors' **ex-post labels**, built from AAERs released through 31 December 2018, years
after every test year. That is what "the same labels" above means. A **release-censored**
variant, which keeps only violations whose AAER was released by the test cutoff (trap 3 in
`known_traps.md`), is a different and separately reported measurement, never compared with
this table. It cannot be run until `p_aaer` is mapped to release dates, because the Bao CSV
carries none.

`aaer.analysis.pu_benchmark` encodes the same protocol (`BAO_TRAIN_START`, `BAO_GAP_YEARS`,
`BAO_K_FRACTION`, `BAO_K_ROUNDING`, `BAO_LIKE_FOR_LIKE_LABELS`).

## Tier 2 — the coverage problem, stated as numbers

This is a constraint on the project, not a defect in the scaffolding, and it forces a
decision by the user.

- The SEC Financial Statement Data Sets begin at **2009q1**, and that first file is empty by
  design: its README states it "contains data sets with column headings only and no rows".
  The first quarter with actual rows is **2009q2** (22 submissions). The latest available is
  2026q2. Scope is filings submitted from 15 April 2009 onward.
- The AAER research literature, including the Bao et al. training period, concerns violations
  in the 1990s and 2000s.
- The curated Dechow, Ge, Larson & Sloan AAER dataset covers 4,278 releases and 1,816 firm
  misstatement events from 17 May 1982 to 31 December 2021 — and must be **purchased**, not
  merely requested. See `data/ACCESS_NOTES.md`.

The free structured-financials path and the labelled period therefore overlap only from 2009,
in a different enforcement regime from the one the benchmark was built on.

## Tier 3 — the honest-metric requirement

The base rate of AAER firm-years is well under 1 %. Accuracy is meaningless. Every result
must be reported with rank metrics (`forensics_core.eval.metrics`) and the base rate printed
next to them, following the benchmark's own choice of NDCG at k = 1 % of test firm-years.
Unflagged firm-years are unlabeled, not clean; see `known_traps.md`.
