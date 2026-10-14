# Research question - china

**Measure the gap between summed provincial GDP and reported national GDP, and test whether
provincial series track physical proxies.**

Provincial statistics bureaus historically reported growth that, summed, exceeded the national
figure the National Bureau of Statistics (NBS) published. Part of that gap is methodological
(cross-province double counting, different deflators, rebasing); part has been admitted to be
fabrication (Liaoning 2011 to 2014). The NBS's unified accounting reform, under which the centre
took over provincial GDP calculation, is a natural experiment: if the gap is partly
misreporting, it should contract discontinuously at the reform.

Sub-questions:

1. What is the provincial-sum minus national gap, by year, in levels and in growth rates, and
   how much of it is mechanically explained (double counting, deflators, boundary changes)?
2. Does the residual gap contract at the unified-accounting reform, and by how much? (The
   exact effective year is verified from NBS sources in `validation_anchors.md`.)
3. Do provincial GDP series track provincial electricity consumption, rail freight, bank
   credit and nightlights, and do the residuals from those relationships concentrate in
   provinces and years that were later revised?
4. Do the flagged provinces show underdispersion (growth too smooth) and bunching at the
   provincial growth target - the two signals that carry to the Soviet case?

This project calibrates `forensics_core.reconcile` (flow conservation between provincial and
national accounts) and `forensics_core.dispersion` against partial ground truth.


## The proxy-free smoothness test: detrending is not yet chosen

For the pre-registration (gate G1). `china.analysis.dispersion.smoothness_by_province` runs
`forensics_core.dispersion.too_smooth_test` on each province's growth after a `detrend` that
has **no default**. Which one is valid depends on how honest provincial growth is generated,
and nobody has checked that:

- if honest growth is iid around a constant mean (or a linear trend), `"linear"` has its
  nominal size and real power, and `"diff"` has almost none;
- if honest growth is persistent (AR(1) with rho 0.7, or a random walk), `"linear"` and
  `"none"` reject most *honest* series by n = 20 to 25, and `"diff"` is the only correctly sized
  option;
- `"none"` also flags any drift in growth over the window, so it is usable only if growth is
  shown to be stationary around a constant mean.

The choice therefore has to be justified from the persistence of honest growth, estimated on
series that are not held out, and stated in the pre-registration with the size and power below
at the n actually used, under both iid and persistent honest growth. Until that check exists
the test is not run.

**Simulated size and power.** `uv run python scripts/smoothness_size_power.py` (synthetic
series only; 300 replications, 199 permutations, rejection at 0.05). Honest rows are size,
smoothed rows power. The smoothed shapes are a three-point moving average (`ma3`), an AR(1)
with rho 0.9 (`ar09`), and `forensics_core.inject.inject_smoothing` with `retain=0.1` applied
to an iid (`inject(iid)`), AR(0.7) (`inject(ar07)`) or random-walk (`inject(rw)`) honest path.

| series | honest/smoothed | detrend | n=10 | n=15 | n=20 | n=25 | n=30 |
|---|---|---|---:|---:|---:|---:|---:|
| iid | honest | none | 0.05 | 0.06 | 0.07 | 0.04 | 0.04 |
| iid | honest | linear | 0.01 | 0.03 | 0.05 | 0.02 | 0.02 |
| iid | honest | diff | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| ar07 | honest | none | 0.53 | 0.75 | 0.89 | 0.92 | 0.96 |
| ar07 | honest | linear | 0.15 | 0.48 | 0.71 | 0.81 | 0.93 |
| ar07 | honest | diff | 0.03 | 0.02 | 0.01 | 0.01 | 0.01 |
| rw | honest | none | 0.69 | 0.90 | 0.94 | 0.98 | 1.00 |
| rw | honest | linear | 0.25 | 0.63 | 0.84 | 0.95 | 0.99 |
| rw | honest | diff | 0.05 | 0.05 | 0.05 | 0.04 | 0.04 |
| ma3 | smoothed | none | 0.62 | 0.79 | 0.93 | 0.97 | 0.98 |
| ma3 | smoothed | linear | 0.32 | 0.62 | 0.89 | 0.94 | 0.98 |
| ma3 | smoothed | diff | 0.07 | 0.08 | 0.06 | 0.07 | 0.08 |
| ar09 | smoothed | none | 0.68 | 0.88 | 0.95 | 0.98 | 0.99 |
| ar09 | smoothed | linear | 0.21 | 0.61 | 0.85 | 0.94 | 0.98 |
| ar09 | smoothed | diff | 0.04 | 0.05 | 0.04 | 0.03 | 0.04 |
| inject(iid) | smoothed | none | 0.62 | 0.83 | 0.94 | 0.98 | 0.98 |
| inject(iid) | smoothed | linear | 0.33 | 0.66 | 0.87 | 0.96 | 0.97 |
| inject(iid) | smoothed | diff | 0.12 | 0.11 | 0.12 | 0.14 | 0.18 |
| inject(ar07) | smoothed | none | 0.92 | 0.99 | 1.00 | 1.00 | 1.00 |
| inject(ar07) | smoothed | linear | 0.66 | 0.98 | 0.99 | 1.00 | 1.00 |
| inject(ar07) | smoothed | diff | 0.39 | 0.70 | 0.79 | 0.86 | 0.92 |
| inject(rw) | smoothed | none | 0.97 | 1.00 | 1.00 | 1.00 | 1.00 |
| inject(rw) | smoothed | linear | 0.70 | 0.96 | 1.00 | 1.00 | 1.00 |
| inject(rw) | smoothed | diff | 0.46 | 0.76 | 0.90 | 0.96 | 0.99 |

At roughly a decade of annual observations per province, even the option with power against
an iid baseline (`"linear"`) detects only 0.21 to 0.33 of smoothed series. A per-province test
at n = 10 is close to powerless whichever treatment the persistence check picks; pooling or
longer panels are what would change that, and that is a design decision for G1, not for this
note.
