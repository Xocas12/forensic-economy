# Research question - china

**Measure the gap between summed provincial GDP and reported national GDP, and test whether
provincial series track physical proxies.**

Provincial statistics bureaus historically reported growth that, summed, exceeded the national
figure the National Bureau of Statistics (NBS) published. Part of that gap is methodological
(cross-province double counting, different deflators, rebasing); part has been admitted to be
fabrication (Liaoning 2011 to 2014). The NBS's unified accounting reform, under which the centre
took over provincial GDP calculation from the 2019 data year, does **not** separate the two by
itself. The reform changed the accounting method, and its stated aim was to bring summed
provincial GDP into line with national GDP because the gap was too large
(`nbs_qa_unified_accounting_plan_2017` in `data/SOURCES.yaml`). Double counting, provincial
deflators and provincial methods are what unified accounting replaces, so the mechanical part
of the gap moves at 2019 as well, and the gap is predicted to contract there with zero
misreporting. The aggregate jump at 2019 measures the combined effect of the method change,
the fourth economic census and any misreporting.

Sub-questions:

1. What is the provincial-sum minus national gap, by year, in levels and in growth rates, and
   how much of it is mechanically explained (double counting, deflators, boundary changes)?
2. How much does the gap move at the unified-accounting reform, and did the reform move a
   province's figures more where its pre-reform growth had outrun its physical proxies? The
   first part is reported only as the combined effect of method, census and misreporting
   (`reform.reform_discontinuity`). The second, `reform.cross_province_reform_contrast`, is
   the only part that can bear on misreporting, and it rests on a stated model of how the
   method and census revisions are distributed across provinces, fixed before the revisions
   are seen. Removing a pre-reform estimate of the mechanical component first does not help,
   because the reform changes that component. (The exact effective year is verified from NBS
   sources in `validation_anchors.md`.)
3. Do provincial GDP series track provincial electricity consumption, rail freight, bank
   credit and nightlights, and do the residuals from those relationships concentrate in
   provinces and years that were later revised?
4. Do the flagged provinces show underdispersion (growth too smooth) and bunching at the
   provincial growth target - the two signals that carry to the Soviet case?

This project calibrates `forensics_core.reconcile` (flow conservation between provincial and
national accounts) and `forensics_core.dispersion` against partial ground truth.
