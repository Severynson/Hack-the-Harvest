### Pre-registration (field_variants, frozen before scoring)

**Question.** Does any of the candidates below beat the current logistic field model, fitted on several
Quebec seasons, on Quebec seasons it never saw, without making the year-to-year silage count less stable?

**Data.** `data/labels/qcm_<year>.parquet` and `data/s2_series/qcm_<year>/` for 2019 to 2026 (17 cells).
Roster per year: `kernelag.field_model.evidence_table` (labeled field-years with a series, inner join), with
the label table's `cell`. A field-year is "assessable" when a greenness drop is found (`max_drop` not NaN).
Not-assessable rows are never used for fitting and are scored as grain (repository convention), except in
f5, where they abstain. Maryland: all 44 field-years of `barc_2021_2023`, read with
`kernelag.evaluate.evaluation_table` (keeps field-years without evidence).

**Year roles (fixed).**
- **Selection years: 2019, 2020, 2021, 2022, 2023, 2024, 2026** (7 seasons). Every decision is made on these.
- **2025 is a holdout.** The task rules forbid selecting or tuning on 2025, so 2025 enters no fit and no
  score used for the decision. After the decision is written, every candidate is fitted on the 7 selection
  years and scored on 2025 (report only).
- 2026 labels are FADQ's 2026-11-09 snapshot and its series ends 2026-11-12; it counts like any other year.

**Features.**
- `MODEL_FEATURES` = `max_drop, max_drop_rate, fade_days, green_at_cut, ndmi_before_cut, ndti_post`
  (`kernelag.features.build_features`).
- LSWI = `lswi_sep_median`, `lswi_sep_min`: median and minimum of the field-year's `ndmi` over clear looks
  (`valid_frac >= 0.5`, `ndmi` not NaN) dated in September; NaN when there is no clear September look. This
  is the logic of `test_models/featureTests/lswi_rule/build.py` (`september_lswi`), re-implemented here and
  checked against it (gate GL).
- Per-year median adjustment ("season adjustment"): each feature minus the median of that feature over the
  assessable rows of the same year in the same batch. Training rows use their own training year's median.
  Scored rows use the median of their own year in the scored batch. The scored batch is the whole held-out
  year in LOYO, the held-out cell-year in the strict split, the year's Maryland field-years on Maryland. It
  uses only the unlabeled imagery features of that batch, never a label (a transductive adjustment).
  Rationale: the multi-year study showed the season moves balanced accuracy by about 0.14 between years
  while the training set moves it by 0.0025, and the silage-call count swings 0.61-1.42 of declared by year.
  Known risk, stated before scoring: the median also depends on the year's silage share, so the adjustment
  pulls every year's silage share toward the training average. That can hurt a year whose true share moved.

**Candidates (all fixed; no hyperparameter search, no threshold change; threshold 0.5).**
- **f0_2023**: `kernelag.field_model.make_model()` (median imputer, standard scaler, balanced logistic,
  C = 0.5) on `MODEL_FEATURES`, fitted on `qcm_2023` only. Reference (the current model's year).
- **f0_all**: the same model fitted on all training years of the fold. **Comparator of the decision rule.**
- **f1_xgb_mono**: `xgboost.XGBClassifier` with `test_models/codexFieldBaseline/baseline.py`'s fixed
  settings (80 trees, depth 2, min_child_weight 8, learning rate 0.05, subsample 1, colsample 1,
  reg_lambda 5, hist, 4 threads, seed 42), `scale_pos_weight` = grain/silage count of the fit partition,
  missing values handled natively, on `MODEL_FEATURES` with monotone constraints from agronomy
  (silage = chopped green and whole plant removed): max_drop +1, max_drop_rate +1, fade_days -1,
  green_at_cut +1, ndmi_before_cut +1, ndti_post -1.
- **f2_lswi**: f0_all's model on `MODEL_FEATURES` + LSWI.
- **f3_yearmed**: f0_all's model on `MODEL_FEATURES` after the per-year median adjustment.
- **f4_yearmed_lswi**: f0_all's model on `MODEL_FEATURES` + LSWI, all eight adjusted per year.
- **f6_yearcellmed** (extra variation): as f3, but the median is taken per year and cell (Maryland: per year,
  the farm being one area). Risk: a cell's silage share varies more than a year's, so this can remove signal.
- **f7_xgb_yearmed_lswi** (extra variation): f1's booster on f4's eight adjusted features; LSWI constraints
  -1 (silage leaves dry bare soil in September).
- **f5_cal_abstain**: base = the adopted candidate (highest pooled BA among adopted ones) or, if none is
  adopted, f0_all. Within each training set: an inner leave-one-year-out over the training years gives
  out-of-year base scores; a sigmoid (Platt: logistic regression on the logit of the score, C = 1e6) is
  fitted on them; on the same inner calibrated scores an abstention band [lo, hi) is chosen from the grid
  lo in {0.30, 0.32, ..., 0.50}, hi in {0.50, 0.52, ..., 0.80}: abstain if lo <= p < hi, silage if p >= hi,
  grain if p < lo, not-assessable rows abstain. The band maximizes decisive silage precision subject to
  coverage >= 0.85 (ties: higher coverage, then smaller hi, then larger lo). The base model fitted on the
  whole training set is then calibrated and banded on the scored rows. Maryland uses the band and
  calibration from the 7 selection years.

**Splits.**
1. **LOYO (primary).** For each selection year Y: candidates fitted on the other 6 selection years score Y.
   f0_2023 (fitted once on 2023) scores the other 6 selection years; its 2023 row is in-sample and left out.
2. **Strict year-and-cell (supporting).** For each selection year Y and cell C: fitted on the other selection
   years in the other 16 cells, scoring cell C in year Y (f0_2023: 2023 in the other 16 cells; 2023 not
   scored). f5 is not computed here.
3. **Expanding window (supporting).** For Y in 2020, 2021, 2022, 2023, 2024, 2026: fitted on selection years
   before Y, scoring Y. f0_2023 and f5 are not computed here.
4. **As-of (supporting).** Split 1 again, with each scored year's series cut at Sep 15, Oct 15 and Nov 15
   (training on full-season features, as `kernelag.evaluate.earliness`). f5 is not computed here.
5. **2025 holdout (report only, after the decision).** Fitted on the 7 selection years, scoring 2025.
6. **Maryland (report only, after the decision).** f0_2023 (qcm_2023 fit) and f0_all and the adopted
   candidate, fitted on the 7 selection years; for information the same two fitted on all 8 years.

**Gates (checked before any candidate result is read).**
- R1: selection-year rosters equal `test_models/fieldMultiYear` (2566, 2325, 2598, 2839, 3128, 2938, 2806).
- G1: f0_2023 leave-one-cell-out on 2023 alone = TP 877 / FP 345 / FN 390 / TN 1516.
- GS: f0_2023 on each of 2019-2022, 2024, 2026 = the S counts in `test_models/fieldMultiYear/out/loyo_by_year.csv`.
- GL: the LSWI port equals `september_lswi` on `qcm_2023` (same NaN pattern, max abs difference < 1e-9).
- Maryland gates, read only in `final`: G2 published 318-parcel fit = 10/5/2/27; G3 qcm_2023 fit = 10/4/2/28.
If a gate fails, every number is still reported, but the decision reads `HELD (gate failed)`.

**Metrics.** Silage is positive. Per held-out year and pooled over the 7 selection years (from summed
counts): TP, FP, FN, TN, silage precision, silage recall, false positive rate, balanced accuracy (BA, mean of
both recalls), silage F1, accuracy, and the silage count ratio = silage calls / declared silage field-years.
The count-ratio swing = max minus min of the yearly ratio over the 7 selection years. Paired cell bootstrap
against f0_all on the pooled rows: resample the 17 cells with replacement, every field-year of a drawn cell in
all 7 years, both models on the same rows; 2,000 draws, seed 0, 90% percentile interval (5th, 95th).
Intervals for the change in BA (decisive), and for F1, precision, recall and FPR (information). Also: exact
McNemar, the change per held-out year, and a Bonferroni reading for the six candidates f1-f4, f6, f7 (the
0.83rd to 99.17th percentile interval; information, does not change the decision).

**Decision rule.**
> A candidate among f1, f2, f3, f4, f6, f7 is **eligible** if its pooled LOYO BA minus f0_all's is above 0,
> the 90% interval's lower bound is above 0, and its count-ratio swing is not larger than f0_all's.
> **ADOPT** the eligible candidate with the highest pooled LOYO BA. If none is eligible: **KEEP f0**
> (`NO IMPROVEMENT SHOWN`). f5 is judged separately: it is **adopted as the selective mode** if its pooled
> LOYO coverage is >= 0.85 and its decisive silage precision minus its base's full-coverage silage precision
> is above 0 with the 90% paired cell-bootstrap interval above 0. Splits 2-6 never change the decision.
> Maryland (44 field-years, one farm, already inspected by the team) is never used to choose anything.

**Response time.** On the 44 Maryland field-years, series already in memory: seconds per field-year for
features plus prediction (the candidate's own feature steps and adjustment included; imagery download and
model fitting excluded), median of 5 full passes; fit time reported separately.

**Outputs (`out/`).** `selection_by_year.csv`, `decision.json`, `predictions_quebec.csv`, `final.json`,
`holdout_2025.csv`, `maryland.csv` (no per-field Maryland calls).
