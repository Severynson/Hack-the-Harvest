### Pre-registration

**Question.** Does fitting the field model on several Quebec seasons, instead of 2023 alone, give better
silage-or-grain calls on a season the model has never seen?

**Data.** `qcm_2019` to `qcm_2026` (labels and Sentinel-2 series in the 17 cells, built by `data_build.py`).
The roster of each year is `kernelag.field_model.evidence_table`: the labeled field-years that have a series
(inner join), 22,026 field-years expected over the eight years. A field-year's area is the label table's
`cell` column. 2026 counts like any other year (declarations dated 2026-11-09, series to 2026-11-12). The
Maryland roster is all 44 field-years of `barc_2021_2023`, read with `kernelag.evaluate.evaluation_table`,
which keeps field-years without evidence.

**Model (fixed; nothing is tuned).** `kernelag.field_model.make_model()` (median imputer, standard scaler,
logistic regression with balanced class weights, C = 0.5) on `MODEL_FEATURES` from
`kernelag.features.build_features`, called silage at `DECISION_THRESHOLD` = 0.5. It is fitted on
assessable rows only (a greenness drop was found); a row that is not assessable is scored as grain. Every
field-year is one row of weight 1. There is no year weighting, no feature selection, no threshold change
and no hyperparameter search. Two training sets are compared:

- **M (multi-year):** every qcm year except the held-out one.
- **S (2023-only):** `qcm_2023`, the current model's year in the same 17 cells (the harness's E3b fit).

**Splits.**

1. **Leave one year out (LOYO, primary).** For each year Y from 2019 to 2026, M is fitted on the other
   seven years and scores year Y. S is fitted once on 2023 and scores every year Y other than 2023. S on
   2023 would be scored on its own training rows: that row is reported as in-sample and left out of every
   comparison.
2. **Leave one area out, pooled over years (supporting).** For each of the 17 cells, a model is fitted on
   the other 16 cells in all eight years and scores the held-out cell in all eight years. Reported pooled
   over the 17 folds and broken down by year.
3. **Leave one year and one area out (supporting, strictest).** For each year Y other than 2023 and each
   cell C: M is fitted on the other seven years in the other 16 cells, S on 2023 in the other 16 cells,
   and both score cell C in year Y. Neither model has seen that season or that area, so the fields that
   recur across years cannot help either one (apart from a parcel whose outline crossed a cell edge).
4. **Maryland transfer (information only, never selection).** Fits on (a) `quebec_maize_2023` (the
   published 318-parcel fit), (b) `qcm_2023` and (c) all eight qcm years each score the 44 Maryland
   field-years. (c) versus (b) also gets a paired bootstrap over Maryland fields, for information.
5. **Coefficient stability.** Fits on each single year (eight fits), on all eight years, and the eight LOYO
   M fits. For each: the logistic weight per standard deviation of each feature (each fit standardises on
   its own training rows) and the intercept. The spread across the eight single-year fits is given as the
   mean, standard deviation, minimum and maximum, and the number of years whose sign matches the
   all-years fit.

**Reproduction gates.** These are checked before any comparison is read.

- G1: S scored leave-one-cell-out on 2023 alone must give TP 877 / FP 345 / FN 390 / TN 1516 (the feature
  harness's E2 base arm).
- G2: fit (a) on Maryland must give TP 10 / FP 5 / FN 2 / TN 27 (`data/models/field_model_report.csv`).
- G3: fit (b) on Maryland must give TP 10 / FP 4 / FN 2 / TN 28 (the harness's E3b base arm).

If a gate fails, every number is still reported, but the decision reads `HELD (gate failed)` with the reason.

**Metrics.** For every split, model and held-out year, and pooled: TP, FP, FN and TN with silage as the
positive class, silage precision, silage recall, balanced accuracy (the mean of silage recall and grain
recall), silage F1, accuracy and false positive rate (`kernelag.evaluate.extended_scores`), plus the number
of field-years and of assessable ones. A pooled metric is computed from the summed confusion counts of the
field-years concerned, not by averaging yearly metrics.

**Primary comparison.** Pooled balanced accuracy of M minus that of S, over the field-years of the seven
held-out years 2019, 2020, 2021, 2022, 2024, 2025 and 2026 (LOYO; the same rows for both models). The
interval is a paired cluster bootstrap that resamples the 17 cells with replacement. Each draw takes every
field-year of a drawn cell in all seven years and scores M and S on the same rows. 2,000 draws, seed 0,
90% percentile interval (5th and 95th percentiles). This is the procedure of `paired_bootstrap` in
`test_models/featureTests/harness.py`. Reported alongside, none of them decisive: the change in silage F1
with its interval, an exact McNemar test, the change in each held-out year with a cell bootstrap inside
that year, and the same paired comparison on split 3.

**Decision rule.**

> **ADOPT the multi-year training set** if the primary change in pooled LOYO balanced accuracy is **above 0**
> and its **90% interval lies entirely above 0** (lower bound > 0). Otherwise **KEEP 2023-only**, written
> `NO IMPROVEMENT SHOWN` when the interval contains 0 and `MULTI-YEAR WORSE` when its upper bound is below 0.
> Splits 2, 3 and 5 and Maryland are supporting evidence and cannot change the decision. Maryland
> (44 field-years, one farm) is never used to choose anything. "Adopt" is this evaluation's recommendation;
> nothing in this folder changes `kernelag/field_model.py` or the published metrics.

**Outputs** (`out/`): `loyo_by_year.csv`, `summary.json`, `coefficients_by_year.csv`, `maryland.csv`, and
`predictions_quebec.csv` (per-row Quebec calls; no per-field Maryland calls are written).
