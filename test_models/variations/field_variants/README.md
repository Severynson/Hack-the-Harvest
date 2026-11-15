# Field classifier variants (key `field_variants`)

Can a different field model give better silage-or-grain calls than the current logistic model, judged only
on Quebec seasons it never saw? Maryland is reported once, after the decision, and never used to choose.

## 1. Pre-registration

The block between the two markers is the pre-registration. It was written on 2026-11-15 before any candidate
below was fitted or scored. `variants.py prereg` hashes it (SHA-256 of the UTF-8 text between the marker lines,
LF line endings) into `out/preregistration.sha256` and keeps a frozen copy in `out/preregistration_frozen.md`.
`variants.py score` and `variants.py final` refuse to run if the block no longer matches the hash.

<!-- PREREGISTRATION:BEGIN -->
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
<!-- PREREGISTRATION:END -->

## 2. Results

**Decision (pre-registered rule): ADOPT `f1_xgb_mono`; f5 adopted as its selective mode.** The 2025 holdout
does **not** confirm the gain (−0.003 [−0.014, +0.009]), and the expanding-window split shows none either. Read
the adoption as a small, plausible improvement in field metrics, not a proven one.

**How the run went.** The pre-registration was frozen at 2026-11-15T09:21:49Z (`c79786c5…`), before
`variants.py` was written. `score` ran at 09:28:05Z and `final` at 09:28:59Z. Both runs used the same
`variants.py` (SHA-256 `50826f12…`) and both checked the frozen hash. Every gate reproduced: R1 rosters, G1
877/345/390/1516, GS (f0_2023's counts in all six years), GL (LSWI port, max difference 0) and, in `final`,
Maryland G2 10/5/2/27 and G3 10/4/2/28. The `build` step read the 2025 labels only to build its feature cache,
and printed row counts only. No 2025 result was computed before `out/decision.json` existed. There were no
protocol deviations. `score` takes about 41 s and `final` about 14 s once the cache exists. Building the
cache takes about 75 s.

### Primary: leave one year out over the 7 selection years (19,200 field-years, pooled)

TP/FP/FN/TN with silage as the positive class. The change in BA is measured against f0_all, with a 90%
paired cell-bootstrap interval. Bonferroni is the six-candidate reading. The swing is the max minus the min of
the yearly silage count ratio.

| Model | TP/FP/FN/TN | Precision | Recall | FPR | BA | F1 | Swing | ΔBA vs f0_all [90%] | Bonferroni | Eligible |
|---|---|---|---|---|---|---|---|---|---|---|
| f0_2023 (6 yrs, no 2023) | 4305/1720/2271/7776 | 0.715 | 0.655 | 0.181 | 0.737 | 0.683 | 0.56 | +0.002 [−0.006, +0.009] (info) | | ref |
| **f0_all** | 5430/2517/2413/8840 | 0.683 | 0.692 | 0.222 | 0.735 | 0.688 | 0.82 | — | | comparator |
| **f1_xgb_mono** | 5635/2337/2208/9020 | 0.707 | 0.719 | 0.206 | **0.756** | 0.713 | 0.42 | **+0.021 [+0.015, +0.028]** | [+0.012, +0.031] | **yes (adopted)** |
| f2_lswi | 5368/2492/2475/8865 | 0.683 | 0.684 | 0.219 | 0.733 | 0.684 | 0.83 | −0.003 [−0.005, −0.001] | [−0.006, −0.001] | no |
| f3_yearmed | 5432/2272/2411/9085 | 0.705 | 0.693 | 0.200 | 0.746 | 0.699 | 0.42 | +0.011 [+0.007, +0.015] | [+0.005, +0.017] | yes |
| f4_yearmed_lswi | 5422/2311/2421/9046 | 0.701 | 0.691 | 0.204 | 0.744 | 0.696 | 0.43 | +0.009 [+0.004, +0.013] | [+0.002, +0.015] | yes |
| f6_yearcellmed | 5032/2232/2811/9125 | 0.693 | 0.642 | 0.197 | 0.723 | 0.666 | 0.08 | −0.013 [−0.023, −0.001] | [−0.029, +0.004] | no |
| f7_xgb_yearmed_lswi | 5299/2273/2544/9084 | 0.700 | 0.676 | 0.200 | 0.738 | 0.688 | 0.37 | +0.002 [−0.003, +0.008] | [−0.005, +0.010] | no |

f1 against f0_all, pooled, with 90% intervals:

- F1: +0.025 [+0.018, +0.032]
- Precision: +0.024 [+0.014, +0.034]
- Recall: +0.026 [+0.013, +0.040]
- FPR: −0.016 [−0.028, −0.005]

f1 is ahead in 5 of 7 held-out years (exact McNemar: 1,475 against 1,090 field-years where only one model is
right, p < 0.001). Three candidates were eligible, and the rule adopts the one with the highest pooled BA.

**Per-year BA and silage count ratio (calls / declared), LOYO.**

| Held-out year | f0_2023 BA | f0_all BA | f1 BA | f3 BA | f0_all ratio | f1 ratio | f3 ratio |
|---|---|---|---|---|---|---|---|
| 2019 | 0.681 | 0.675 | 0.704 | 0.721 | 0.87 | 0.93 | 1.16 |
| 2020 | 0.665 | 0.691 | 0.708 | 0.700 | 1.11 | 1.17 | 0.74 |
| 2021 | 0.797 | 0.720 | 0.774 | 0.761 | 1.43 | 1.12 | 1.08 |
| 2022 | 0.666 | 0.692 | 0.756 | 0.691 | 0.61 | 0.93 | 0.82 |
| 2023 | (in-sample) | 0.739 | 0.736 | 0.733 | 1.19 | 1.22 | 1.06 |
| 2024 | 0.808 | 0.817 | 0.810 | 0.816 | 0.82 | 0.81 | 0.96 |
| 2026 | 0.772 | 0.777 | 0.791 | 0.780 | 1.04 | 0.96 | 1.00 |
| Pooled | 0.737 | 0.735 | 0.756 | 0.746 | 1.01 | 1.02 | 0.98 |

### Supporting splits (cannot change the decision): ΔBA vs f0_all [90%]

| Candidate | Strict year + cell | Expanding window (2020-2024, 2026) | As-of Oct 15 | 2025 holdout (after decision) |
|---|---|---|---|---|
| f1_xgb_mono | **+0.021 [+0.015, +0.027]** | −0.001 [−0.009, +0.009] | **+0.016 [+0.008, +0.024]** | −0.003 [−0.014, +0.009] |
| f2_lswi | −0.004 [−0.005, −0.002] | +0.001 [−0.002, +0.004] | −0.001 [−0.003, +0.000] | −0.015 [−0.026, −0.007] |
| f3_yearmed | **−0.027 [−0.041, −0.011]** | +0.022 [+0.010, +0.035] | −0.003 [−0.008, +0.002] | +0.012 [−0.006, +0.031] |
| f4_yearmed_lswi | −0.028 [−0.042, −0.014] | +0.019 [+0.005, +0.032] | −0.005 [−0.010, 0.000] | +0.014 [−0.005, +0.034] |
| f6_yearcellmed | −0.016 [−0.027, −0.003] | +0.011 [−0.006, +0.027] | −0.011 [−0.020, +0.001] | −0.007 [−0.035, +0.025] |
| f7_xgb_yearmed_lswi | −0.017 [−0.026, −0.007] | +0.013 [+0.000, +0.024] | +0.009 [+0.002, +0.017] | +0.006 [−0.013, +0.026] |

The pooled BA of f0_all in these splits is 0.735 (strict), 0.723 (expanding), 0.725 (Oct 15) and 0.751 (2025,
2,826 field-years). On 2025, f0_2023 scores 0.726 and f1 0.748. f1's 2025 silage count ratio is 1.00, against
1.07 for f0_all.

- **Earliness.** At Sep 15 nothing works: pooled BA is 0.52–0.55 for every model, because most Quebec fields
  are not cut yet. Oct 15 gets close to full-season (f0_all 0.725, f1 0.741). Nov 15 is identical to the full
  season, because the features stop at day 300 (27 Oct).
- **f1 needs several training seasons.** In the expanding window it loses in 2020 (one training year) and
  2021 (two). It wins in 2022 (0.760 against 0.692) and 2026 (0.791 against 0.777, fitted on 2019-2024). Its
  count-ratio swing there is 1.04 (2020: 1.84). So the stable count shown in LOYO also depends on having
  several seasons.
- **The season adjustment (f3/f4) needs a large scored batch.** With a whole held-out year as the batch (17
  cells, about 2,700 field-years) it helps: LOYO +0.011, expanding +0.022, and the best 2025 point estimate.
  With one cell-year as the batch (the strict split, about 150 field-years) it hurts (−0.027). Maryland
  supplies 7–19 field-years per year, so f3 was a poor bet for the official metric even though it was
  eligible. The per-cell version (f6) removes real signal, as feared: recall −0.051.
- **The LSWI September features (f2) do not help** across years (−0.003), unlike the +0.006 the earlier
  2023-only harness found.

### f5: calibration plus abstention on f1 (selective mode)

The chosen band is [0.50, 0.76–0.80) in every fold; on the 7 selection years it is [0.50, 0.78). Pooled LOYO
on decisive rows:

| | Value |
|---|---|
| Coverage | 0.866 |
| Precision | 0.889 (f1 itself: 0.707) |
| Recall | 0.479 (0.372 of all declared silage) |
| FPR | 0.035 |
| BA | 0.722 |

The precision gain is +0.182 [+0.156, +0.208], so the f5 rule passes. The price is recall. Abstained rows
scored as grain give BA −0.065 against f0_all, and decisive calls are 0.54 of declared silage. Coverage
falls to 0.75 in 2020. f5 suits a "show only confident silage fields" view. It should **not** feed acreage
counts, because the USDA reps said both error directions cost the same. On 2025: coverage 0.867, precision
0.873, recall 0.573.

### Maryland (44 field-years, one farm, already inspected; reported once, never used to choose)

The intervals are a 90% field-cluster bootstrap (`kernelag.evaluate.bootstrap_intervals`).

| Fit | TP/FP/FN/TN | Precision [90%] | Recall [90%] | FPR [90%] | BA |
|---|---|---|---|---|---|
| Published 318-parcel fit (G2) | 10/5/2/27 | 0.667 | 0.833 | 0.156 | 0.839 |
| f0_2023, qcm_2023 (G3) | 10/4/2/28 | 0.714 [0.50, 0.91] | 0.833 [0.64, 1.00] | 0.125 [0.03, 0.23] | 0.854 |
| f0_all, 7 selection years | 10/1/2/31 | 0.909 [0.75, 1.00] | 0.833 [0.64, 1.00] | 0.031 [0.00, 0.10] | 0.901 |
| **f1_xgb_mono, 7 selection years** | **11/1/1/31** | **0.917 [0.77, 1.00]** | **0.917 [0.77, 1.00]** | **0.031 [0.00, 0.10]** | **0.943** |
| f0_all, all 8 years (information) | 10/1/2/31 | 0.909 | 0.833 | 0.031 | 0.901 |
| f1_xgb_mono, all 8 years (information) | 11/0/1/32 | 1.000 | 0.917 | 0.000 | 0.958 |
| f5 on f1 (band [0.50, 0.78), coverage 0.864) | 5/0/1/32 decisive | 1.000 | 0.833 decisive, 0.417 of all | 0.000 | 0.917 |

- **Where the gain against the published numbers comes from.** Most of it is multi-year training. FP falls
  from 5 to 1 already with f0_all. f1 adds a net one silage field-year caught (FN 2 to 1). The intervals
  overlap almost entirely.

**Response time** (44 Maryland field-years, series in memory, median of 5 passes; features plus prediction;
no imagery download, no fitting):

| Model | Seconds per field | Fit time on 7 seasons (16k rows) |
|---|---|---|
| f0 | 0.0104 | 0.02 s |
| f1 | 0.0108 | 2.6 s |
| f5 | 0.0120 | |

Feature extraction dominates the time per field.

## 3. Limitations

- **The adoption is not confirmed out of sample.** f1's gain is clear in LOYO, the strict split and at Oct 15.
  It is absent in the expanding window and on the 2025 holdout. The cell bootstrap treats the seasons as
  fixed, and seven seasons is few. A season-level interval would be much wider.
- **Multiplicity.** Six candidates were tested. f1, f3 and f4 survive the Bonferroni reading in LOYO. Only f1
  survives the strict split.
- **Labels.** The labels are FADQ crop-insurance declarations, not observed harvests. Silage on farms insured
  only for feed is missing. 2025 and 2026 are snapshots dated 2026-11-09, and the 2026 series ends 2026-11-12.
  The Maryland labels are proxy labels from one research farm. The USDA truth is state totals only, so
  field precision and recall are proxy metrics.
- **Sources.** The data mixes Earth Search years with Planetary Computer years (2022, 2023). This was not
  re-checked here.
- **Quebec only.** Everything is selected on Quebec. Monotone constraints guard the direction of each
  feature's effect but not the calendar shift (the USDA "one calendar" trap). Transfer to US states is
  untested beyond the one Maryland farm.
- **Not computed.** f5 in the strict, expanding and as-of splits (UNCOMPUTED: not pre-registered). Maryland
  as-of results (UNCOMPUTED: not pre-registered, to avoid extra looks at Maryland).
- **No production code changed.** Nothing under `kernelag/` was edited, and the published metrics are
  untouched.

## 4. Run

From the repository root (Git Bash):

```bash
.venv/Scripts/python.exe -I test_models/variations/field_variants/variants.py build   # feature cache, ~75 s
.venv/Scripts/python.exe -I test_models/variations/field_variants/variants.py score   # selection years, ~41 s
.venv/Scripts/python.exe -I test_models/variations/field_variants/variants.py final   # 2025 + Maryland, ~14 s
cd test_models/variations/field_variants/out && sha256sum -c preregistration.sha256
```

The cache goes to the session scratchpad (override with `FIELD_VARIANTS_CACHE`). The runs are deterministic:
fixed folds, XGBoost seed 42 with 4 threads, and bootstrap seed 0.

Outputs in `out/`:

- `decision.json`: gates, eligibility, all comparisons and f5.
- `selection_by_year.csv`: every model, split, year and pooled row.
- `predictions_quebec.csv`: Quebec rows only.
- `final.json`, `holdout_2025.csv` and `maryland.csv`: no per-field Maryland calls.
