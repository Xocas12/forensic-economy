# Research question — gosplan

**Bound the volume of reporting distortion in Soviet economic statistics, with a magnitude and
a sectoral distribution, using methods calibrated on the three projects with ground truth.**

This is the target project. It has almost no labels: one anchor event (the Uzbek cotton
affair), a literature of Western re-estimates (CIA, Bergson, Khanin) that disagree with each
other, and no possibility of confirming any individual figure against an archive from here.

## What this project is, and is not

**It is not primarily a coding problem.** Much of the source material exists only as scanned
Russian-language printed tables. A large share of the work is OCR, transcription, schema
design and reconciliation of definitions across yearbook editions. The pipeline is built for
that: transcription targets with fixed schemas, validation of transcribed tables against
arithmetic identities and against a second transcription, and provenance down to the page.

## Sub-questions

1. **Internal consistency.** Do the published series satisfy the accounting identities they
   claim to (sectoral sums, input-output balances, physical-to-value conversions)? Where they
   do not, `forensics_core.reconcile` locates the nodes needing the largest corrections.
2. **Physical vs value series.** Do value aggregates grow faster than the physical output
   series that should underpin them? This is the hidden-inflation question and the core of the
   Khanin critique; the gap is a finding, not noise.
3. **Notch bunching.** Do reported plan-fulfilment percentages bunch at 100 % (the bonus
   threshold), and does the excess mass vary by sector, year and republic?
4. **Underdispersion.** Are reported harvest and output series smoother than the physical
   drivers (weather, hydrology, freight) permit?
5. **Transfer.** Do detectors calibrated on `elections`, `aaer` and `china` rank the Uzbek
   cotton years and sector at the top when applied blind?

## The driver-free smoothness test: detrending, size and power

For the pre-registration (gate G1). The smoothness test in
`gosplan.analysis.harvest_dispersion.smoothness_of_reported_series` runs
`forensics_core.dispersion.too_smooth_test` on the values left after detrending, and which
detrending is valid depends on how an honest series of that type moves. There is no pre-1992
hydrological driver for the anchor window, so this test is the main underdispersion route
here, and a treatment without power would drop it for the wrong reason.

**Stated choice: `detrend="linear"` for reported harvest and output levels.** These series
are strongly trended. The judgment is that an honest level series is trend plus shocks that do
not persist from year to year; it has to be checked on non-held-out series (other crops, other
republics) before the test is run on anything near the anchor, and the check reported with the
result.

- `"none"` is not used on trended series. It flags any trend: every honest trend-plus-noise
  series below is rejected.
- `"diff"` is not used either. The library documents it as having essentially no power on a
  trend-stationary series (the first differences of trend plus iid noise sit near a von Neumann
  ratio of 3, not 2), and the simulation agrees: it detects at most 0.22 of smoothed series at
  any n here. A non-rejection under it would read as "not too smooth" when the test
  never had a chance.
- The earlier plan to show all three treatments is dropped. Fixing one treatment in advance
  answers the concern it was meant to answer (reporting the one that fires) without putting a
  test that always fires and a test that never does beside the one that works.

**Simulated size and power.** `uv run python scripts/smoothness_size_power.py` (synthetic
series only; 300 replications, 199 permutations, rejection at 0.05). Honest rows are the
test's size, smoothed rows its power. A linear trend of one noise standard deviation per year,
with the noise replaced by a three-point moving average (`ma3`), an AR(1) with rho 0.9
(`ar09`), or shrunk to a tenth of its variance around a local trend by
`forensics_core.inject.inject_smoothing` (`inject`).

| series | honest/smoothed | detrend | n=10 | n=15 | n=20 | n=25 | n=30 |
|---|---|---|---:|---:|---:|---:|---:|
| trend + iid | honest | none | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| trend + iid | honest | linear | 0.01 | 0.03 | 0.05 | 0.02 | 0.02 |
| trend + iid | honest | diff | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| trend + ma3 | smoothed | none | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| trend + ma3 | smoothed | linear | 0.33 | 0.64 | 0.88 | 0.90 | 0.98 |
| trend + ma3 | smoothed | diff | 0.11 | 0.08 | 0.08 | 0.09 | 0.08 |
| trend + ar09 | smoothed | none | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| trend + ar09 | smoothed | linear | 0.22 | 0.59 | 0.82 | 0.93 | 0.98 |
| trend + ar09 | smoothed | diff | 0.04 | 0.04 | 0.04 | 0.02 | 0.04 |
| inject(trend + iid) | smoothed | none | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| inject(trend + iid) | smoothed | linear | 0.30 | 0.65 | 0.88 | 0.96 | 0.98 |
| inject(trend + iid) | smoothed | diff | 0.15 | 0.13 | 0.14 | 0.18 | 0.22 |

How long a transcribed series will be is not known until it is transcribed, so the n is not
fixed here: the pre-registration quotes the `linear` rows at the n actually used. Under
`"linear"` the size stays at or below 0.05 throughout; power is 0.98 at n = 30, 0.82 to 0.88 at
n = 20 and 0.22 to 0.33 at n = 10, so a series of ten years or so cannot carry this test.

## What a result can and cannot claim

With a single anchor, any detector is fit and validated on the same event. The strongest
honest claim is a *bound* — "reported distortion is at least X in sector S over years Y, on
the assumption that the padding mechanism resembles the anchor" — with the assumption stated.
Point estimates of aggregate distortion are not supportable from this design.
