# DATA_AUDIT: aaer

Written by `scripts/audit_aaer_panel.py` on 2026-09-26 at commit `5ee7200`. Every number was computed from the file on disk.

**This is not analysis.** CONTRACT rule 4 permits loading, cleaning, counting rows and describing coverage at any phase, and forbids fitting, testing, scoring and estimating until the gate opens. This file does the former only. Nothing in it is a statement about accounting fraud.

## What was acquired

| file | bytes | sha256 (first 16) |
|---|---:|---|
| `data_FraudDetection_JAR2020.csv` | 47,782,071 | `ed4cefd9db2a23d0` |
| `AAER_firm_year.csv` | 33,000 | `ee5f8a49da6d5495` |
| `identifiers.csv` | 1,608,699 | `4af80a02f4ae5209` |

Bao, Y., B. Ke, B. Li, Y. J. Yu and J. Zhang (2020), *Journal of Accounting Research* 58(1), 199-235; replication archive <https://github.com/JarFraud/FraudDetection>. Registry entry `bao_replication`.

## The panel

| quantity | value |
|---|---:|
| firm-years | 146,045 |
| distinct firms (`gvkey`) | 18,444 |
| fiscal years | 25 (1990-2014) |
| rows labelled `misstate = 1` | 964 |
| distinct AAER cases (`p_aaer`) | 412 |
| base rate | 0.6601% |

The base rate is the number that governs everything downstream. At roughly one labelled firm-year in 150, accuracy is worthless as a metric and a detector that predicts "no misstatement" everywhere scores above 99 per cent. This is why CONTRACT rule 10 admits rank metrics only, with the base rate printed beside them.

## Coverage by fiscal year

| fiscal year | firm-years | labelled | base rate |
|---:|---:|---:|---:|
| 1990 | 4,582 | 15 | 0.3274% |
| 1991 | 4,713 | 27 | 0.5729% |
| 1992 | 4,970 | 26 | 0.5231% |
| 1993 | 5,377 | 30 | 0.5579% |
| 1994 | 5,684 | 23 | 0.4046% |
| 1995 | 6,230 | 22 | 0.3531% |
| 1996 | 6,745 | 33 | 0.4893% |
| 1997 | 6,789 | 42 | 0.6186% |
| 1998 | 6,716 | 56 | 0.8338% |
| 1999 | 6,828 | 73 | 1.0691% |
| 2000 | 6,752 | 86 | 1.2737% |
| 2001 | 6,362 | 81 | 1.2732% |
| 2002 | 6,067 | 77 | 1.2692% |
| 2003 | 5,981 | 69 | 1.1537% |
| 2004 | 5,934 | 58 | 0.9774% |
| 2005 | 5,863 | 45 | 0.7675% |
| 2006 | 5,908 | 33 | 0.5586% |
| 2007 | 5,868 | 30 | 0.5112% |
| 2008 | 5,612 | 26 | 0.4633% |
| 2009 | 5,367 | 31 | 0.5776% |
| 2010 | 5,389 | 26 | 0.4825% |
| 2011 | 5,404 | 21 | 0.3886% |
| 2012 | 5,630 | 19 | 0.3375% |
| 2013 | 5,647 | 11 | 0.1948% |
| 2014 | 5,627 | 4 | 0.0711% |

The label density falls away at the end of the panel: 81 labelled rows across 27,697 firm-years in 2010-2014. That is the well-known enforcement lag rather than a fall in misstatement, since an AAER is published years after the fiscal year it concerns. Any train/test split along the time axis inherits it.

## What this panel cannot support

`aaer.features.beneish` needs twelve items per firm-year. This panel supplies 9 of them:

```
present: receivables, sales, cogs, current_assets, total_assets, depreciation, long_term_debt, current_liabilities, income_continuing_ops
```

Three are absent and cannot be recovered from what is here:

| Beneish input | needs | status in this panel |
|---|---|---|
| `ppe_net` | Compustat `ppent` | ppent (only ppegt, gross, is present) |
| `sga` | Compustat `xsga` | xsga |
| `cash_from_operations` | Compustat `oancf` | oancf |

Consequently DSRI, GMI, SGI and LVGI are computable as published; AQI and DEPI only by substituting gross for net property, plant and equipment, which is a different ratio from the one Beneish (1999) estimated his coefficients on; SGAI not at all; and TATA not at all in the cash-flow form implemented here. **A four-component score is not the Beneish M-score** and the published coefficients do not transfer to it. Closing this gap needs Compustat `ppent`, `xsga` and `oancf`, from the SEC Financial Statement Data Sets (2009 onward, free) or from Compustat itself (licensed).

## What has not been done

No detector has been fitted and nothing has been scored. The aaer replication sits behind gate G1, which requires a pre-registered analysis plan that does not yet exist, and `analysis/beneish_baseline.py` still raises `NotImplementedError`. The replication target is an AUC of 0.7428 and an NDCG@1% of 0.0394 for 2003-2005 - and those are the erratum values, which have not been read first-hand because the erratum is paywalled. Until it is read, the target itself is second-hand.

