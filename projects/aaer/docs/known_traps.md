# Known traps — aaer

## 1. Enforcement is selected, not random

The SEC pursues cases that are detectable, large and litigable. A model trained on AAERs
learns *what gets prosecuted*, not *what happens*. Consequences:

- Unflagged firm-years are **unlabeled, not negative**. `forensics_core.labels.pu` (Elkan–Noto,
  bagging PU) treats them that way, but under rank metrics (trap 2) that alone does not get a
  model out of this trap. Elkan–Noto's score is the treat-as-clean classifier's divided by one
  constant, so it ranks firm-years exactly as that classifier does; it is not an arm of the
  rank comparison and is used only for the class prior, the share of misstatement never
  charged. Bagging PU ranks differently only with a nonlinear base classifier, and then because
  it estimates differently, not because it corrects anything. Both assume charged cases are a
  random draw from the misstatements, which is what this trap says is false, so neither undoes
  a selection that depends on the firm. That needs a model of the selection itself.
- Performance measured against AAER labels is performance at predicting enforcement.
  Say so in every table.

## 2. Base rate well under 1 %

Accuracy is meaningless; a model that flags nothing is >99 % accurate. Use rank metrics only
(`forensics_core.eval.metrics`: AUC, average precision, NDCG@k, precision@k), following the
published benchmark's choice of NDCG@k with k = 1 % of test firm-years.

## 3. Label timing

An AAER is issued years after the misstatement. The label attaches to the *misstated* fiscal
years, not to the release year; a temporal split must use the fiscal year of the violation and
must not let information from a release issued after the test-period cutoff leak into
training. (The correction to the published benchmark concerns exactly this kind of leakage;
see `validation_anchors.md`.)

## 4. Restatements and the same firm appearing on both sides of a split

Firms recur. Use grouped splits (`EvalSpec.split = "group_kfold"` with firm as the group) or
strict temporal splits; never random row splits.

## 5. Survivorship and coverage in the free data

The SEC Financial Statement Data Sets contain what was filed in XBRL, with tag heterogeneity
across filers and years. Custom extension tags, restated values appearing in later filings and
missing lagged values for new filers all bias the Beneish components. The `clean` step must
document how each of the twelve required items is mapped to XBRL tags (`docs/data_dictionary.md`)
and how many firm-years are lost at each mapping.

## 6. Industry structure mimics manipulation

The Beneish indices move mechanically with industry (retailers vs banks vs software) and with
the business cycle. Compare within industry-year or include industry-year fixed effects before
attributing an index level to manipulation. Financial firms are usually excluded in the
literature; state whether they are.

## 7. Compustat vs SEC definitions

Items such as "income from continuing operations" and "cash from operations" are defined
differently in Compustat and in XBRL taxonomies. Replication gaps may be definitional.
