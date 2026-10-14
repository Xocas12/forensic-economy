# Validation anchors — gosplan

## Read this first: one anchor is not enough, and the project cannot pretend otherwise

This project has **exactly one** validation anchor. A single anchor means any detector will be
fit and validated on the same event. There is no held-out positive, no way to estimate a
false-positive rate from within the project, and therefore a hard ceiling on the strength of
any claim this project can make.

Two consequences, to be written into every result:

1. Detector calibration must come from elsewhere. The `elections`, `aaer` and `china`
   projects supply the score-to-precision mapping; here the score is a **ranking**, not a
   probability. See `docs/method_transfer.md` in the shared library.
2. The honest output is a **bound under a stated assumption** — "reported distortion is at
   least X in sector S over years Y, assuming the padding mechanism resembles the anchor" —
   not a point estimate of aggregate distortion.

## The anchor: the Uzbek cotton affair

**Claim.** Cotton harvest figures for the Uzbek Soviet Socialist Republic were systematically
padded over roughly a decade, exposed in the 1980s, followed by prosecutions and revised
figures.

**Magnitude, from the best accessible academic source.** During **1978–1983**, about
**4.548 million tons** of non-existent raw cotton were reported, for which the state paid
**2.866 billion rubles** (1.178 billion of it in bonuses).

Source: Cucciolla, R. (2017), *Cahiers du monde russe* 58/4, freely readable at
`https://journals.openedition.org/monderusse/10133`, paragraph 23, quoting the Soviet
investigation; corroborated in the author's doctoral thesis at IMT Lucca.

**An internal inconsistency to resolve before using the number.** The same article's
paragraph 11 gives 270,000–340,000 tons per year, which does not reconcile with 4.548 Mt over
six years (that would be about 758,000 t/yr). Both figures are in the same text. Establish
which refers to what — total padding versus a particular subset or period — before treating
either as a target. A Wikipedia figure of 981,000 tons for 1983 alone is **unverified**
against any primary or academic source and must not be used as it stands.

**Direction and window are what the detector must recover:** an upward bias in reported Uzbek
cotton output, concentrated in the late 1970s and early 1980s, ending with the exposure.

## Physical correlates the falsifiers did not control

The anchor is testable only because output was reported while some physical quantities were
recorded independently. What is actually obtainable:

| Correlate | Status | Note |
|---|---|---|
| FAOSTAT seed cotton, USSR | **Verified, and it covers the window, but it is the official figure, not a correlate.** Area code 228, item 328, element 5510: 31 years, 1961–1991, flag A in every year. 1975: 7,864,000 t; 1980: 9,100,000 t; 1983: 9,221,000 t; 1985: 8,755,000 t; 1990: 8,305,000 t | Flag A is FAOSTAT's "Official figure", the value the national authority supplied, so this is the Soviet official series re-published, and it carries whatever padding the vintage it copies carries. A transcription and vintage check, not a measurement (see the next section). Union-level, not republic-level. Cotton lint for the same area carries flag X, "Figure from external organization", only for 1961–1964, and flag A from 1965 |
| FAOSTAT, Uzbekistan | Verified, but **starts in 1992** with no back-cast | Useless for the anchor window; useful for the post-Soviet comparison |
| USDA Foreign Agricultural Service, production supply and distribution | **Verified, and it covers the window.** USSR 1960–1986, Uzbekistan from 1987, twelve attributes including area and yield. USSR production, thousand 480-lb bales: 1978: 11,907; 1980: 12,401; 1983: 9,976; 1985: 12,777 | A Western estimate of the same quantity, and the only machine-readable cotton series covering the window that is not the official figure re-published. Its own inputs may include the official figures, so it is an outside estimate rather than an independent measurement |
| Amu Darya water delivery | **Does not cover the window.** The CAWater-Info Aral database table is 1992–2025 only | The irrigation-withdrawal correlate that the design assumed is not available for 1978–1983 from this source. A different hydrology source must be found or the correlate dropped |
| Ginning capacity, rail freight, textile inputs | Not yet located in machine-readable form | Transcription targets |

**Note what this does to the design.** Of the two value series covering the window, only the
USDA's is an outside estimate. FAOSTAT's re-publishes the official figure, so the comparison
left is the official figure against the USDA estimate, and two measurements of one quantity
cannot say which of them is wrong. The hydrological correlate, which was to be the
*independent* physical check, is currently missing for the anchor period. Both gaps are
findings about feasibility and belong in the project README, not buried here. The next section
sets out what the cotton reconciliation can and cannot be.

## The cotton reconciliation, and why FAOSTAT is not one of its measurements

FAOSTAT's USSR seed cotton (area 228, item 328, element 5510) carries flag `A` in every year
1961–1991, and the bulk file's own `Flags.csv` defines `A` as "Official figure": the value the
national authority supplied. The series is the Soviet official report as FAO re-published it,
not an estimate made by anyone outside the reporting chain the falsifiers controlled.

Counting it as a measurement beside the official series counts the official report twice, and
that breaks the test in a specific way. Whenever two of three measurements of one quantity are
equal and the third differs, the third receives the largest standardised adjustment, whatever
the three standard deviations are. So in any year where FAO carries the same official vintage
as the table being reconciled, the official series can never be singled out: if serial
elimination removes anything it removes the USDA estimate first, after which the two copies
agree and the test stops.
Their agreement reads as two-source corroboration of the very figure under test. In a year
where FAO carries a different official vintage, the official series can be flagged, but that
verdict reports the statistical office's own revision, not outside evidence. Modelling the copy
as an error perfectly correlated with the official one does not rescue it: that covariance is
singular, and `forensics_core.reconcile` rejects a covariance that is not positive definite.

**Measurements:** the official figure, transcribed from the annuals, and the USDA estimate,
after a lint-to-seed-cotton conversion that is stated with the result (`data_dictionary.md`,
pitfall 3).

**Not a measurement:** FAOSTAT's flag-`A` seed cotton. It is used upstream instead, as a
transcription and vintage check on the transcribed official series. Agreement says the
transcription matches one official vintage; a disagreement is either a transcription error or
a different official vintage, to be settled against the page. Neither is evidence about
padding.

**What two measurements can say.** With only the official figure and the USDA estimate, the two
standardised adjustments are always equal in size and opposite in sign, so the measurement
test cannot say which source is wrong, and whichever one serial elimination removes is decided
by floating-point rounding. The test is then a two-source divergence report: per year, the size
and sign of the gap, and the global test under standard deviations stated in advance, with no
claim about which source is at fault. The USDA series is an outside estimate whose own inputs
may include the official figures, and that limitation goes in the output as well.

**Open question:** whether a third quantity exists that the falsifiers did not control and that
is not computed from the official figure. The candidates raised so far are the USDA's area and
yield components and a physical driver such as a pre-1992 hydrological series. Each needs a
written argument that it is neither the official figure nor derived from it before it enters
the reconciliation. Until one is named and registered, the reconciliation cannot localise the
error, and its report must say so.

## The corpus that makes the project possible at all

**The CIA declassified estimates are reachable, but not from the CIA.** `cia.gov/readingroom`
blocks scripted access outright: the first request is denied with an Akamai-style "Access
Denied" redirect, identical across user agents, headers, cookies and paths, for search pages,
document pages and PDF URLs alike. It is a block, not a rate limit.

The mirror is the path of record: the archive.org collection `ciareadingroom` holds
**973,499 documents** with per-document PDFs and optical-character-recognition text, and is
queryable through the standard archive.org search and metadata APIs. Searches returned 784
hits for "Soviet economy GNP", 328 for "Soviet agricultural statistics cotton" and 33 for
"Soviet economic statistics falsification". Three PDFs were fetched and checksummed.
**Caveat:** it is a third-party upload from October 2024 and its completeness relative to the
CIA's own holdings has not been verified.

**Congressional compendia**, free and confirmed downloadable: *USSR: Measures of Economic
Growth and Development, 1950-80* (Joint Economic Committee, 1982) at archive.org
(32,136,371 bytes); *Soviet Economy in the 1980s: Problems and Prospects* part 1
(43,421,807 bytes; part 2 unconfirmed); *Gorbachev's Economic Plans* (1987), both volumes in
HathiTrust full view. The committee's own site returns 403 to scripts, so archive.org and the
Wayback Machine are the routes.

**Western reconstructions**, verified: the Maddison Project Database 2023 includes a "Former
USSR" series (code SUN, 158 GDP-per-capita observations, 1860 and 1900–2022). Mark Harrison's
Warwick pages host seven downloadable spreadsheets, including 1928–1985 GNP, employment and
capital basic data drawn from Bergson-school and CIA sources, and six annual input–output
matrices for 1940–45. The Penn World Table, checked rather than assumed, contains **no** USSR
series at all.

## What a transferred detector must do here

1. Rank the Uzbek cotton sector in the 1978–1983 window at or near the top when applied blind
   to the full panel.
2. Not rank it top for the wrong reason: the same detector must not fire equally on sectors
   and periods with no independent evidence of padding, and any such firing must be reported
   rather than filtered away.
3. Survive the weighting-scheme robustness check and the currency-reform and boundary-change
   controls in `known_traps.md`. A result that depends on base-year weights is not a result.
