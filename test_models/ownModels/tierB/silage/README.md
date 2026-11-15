# Tier B silage: state corn-for-silage acres, NASS-informed (no NASS grain forecast)

Owner key: `tierb_silage`. Folder: `test_models/ownModels/tierB/silage/`. Code: `run.py`. Tests: `test_run.py`.
Outputs: `out/`. Nothing outside this folder is written.

User directives (2026-11-14): "we cant just use their nass forecast., we should have our own models." then "we can
use the nass to train it". The report's silage model (`reversion_only`, `kernelag/state_model.py`) uses only past
NASS finals. Tier A (`test_models/ownModels/silage/`) adds non-NASS current-year data. This folder is **Tier B**:
it may also use current-year NASS inputs that are not the acreage answer (planted acres, yield forecasts, crop
condition, milk cows), and never NASS's harvested-for-grain forecast or anything computed from it.

---

## 1. Pre-registration (written 2026-11-14 before any candidate score was computed; not edited afterwards)

This section, from its heading to the end-of-section marker, is hashed into `out/preregistration.sha256` by
`run.py --prereg` before the first scored run. `run.py` refuses to score if the hash differs. Later text goes below
the marker; any change of method is listed under "Deviations".

### 1.0 What I had seen before writing this

- The incumbent's stored backtest (`data/models/state_model_backtest.csv`), 2017-2024: silage `reversion_only`
  13.12% state WAPE / 3.90% mean |US|, persistence 14.53% / 4.08%; grain NASS November forecast 1.66% / 0.82%,
  grain persistence 7.35% / 4.12%. Reproduced exactly by `run.py --check` (section 2), before writing this.
- The Tier A silage README (`test_models/ownModels/silage/README.md`), with its scores: reversion_only on NASS finals
  from 2000 (`s1`) 14.11% (2012-2024) / 13.01% (2017-2024); its FSA residual blend `s3` (FSA-scaled planted minus
  FSA-ratio grain, shrunk toward s1 with a fitted w, mostly 0.25) 13.72% / 12.52%; its drought/RMA/FSA-silage
  switch ridge `s4` 14.51% / 14.15%; `s4` plus NASS poor/very-poor condition 14.32% / 13.92%; the raw FSA residual
  16.54% / 15.11%; the oracle final residual 8.44% / 9.68%. Its diagnostics: FSA-scaled planted within 0.87% of
  NASS final planted, FSA-ratio grain within 2.15%, the FSA residual misses NASS's final residual by 22%.
- The team's stored silage feature sets quoted there (2017-2024): `nass_acres` (reversion + NASS planted change +
  NASS-grain-forecast non-grain share change) 13.04%, `stress` 13.82%, `all_public` 14.53%.
- The input coverage printed by `run.py --check` (no outcome involved): NASS in-season planted exists for every
  state from 2012, but for **2012-2017 only as the March Prospective Plantings figure**; June Acreage and later
  vintages exist from 2018 (as of 15 Nov: October vintage 2018-2021, September 2022-2023, October/September 2024,
  September 2025-2026). NASS yield forecasts cover about 32 states, crop condition 18 states before 2015 and about
  44 after, FSA high-coverage silage states about 13-18 per year, milk cows all 48 states until 2024 and 31 in 2025-2026.
- No score of any c1-c5 candidate and no 2025 number of any candidate.

### 1.1 Tiers (enforced in `run.py`: `INPUTS`, `CANDIDATES`, `check_tiers`, `check_columns`)

| Tier | Inputs allowed for target year t |
|---|---|
| A | NASS final state numbers of years < t (history); FSA crop acreage files published by the as-of date; RMA; US Drought Monitor; NOAA weather |
| **B (this folder)** | Tier A plus current-year NASS inputs that are not the acreage answer: NASS planted for all purposes (March, June, August, September, October vintages), NASS grain-yield forecasts, NASS weekly crop condition, NASS 1 January milk-cow inventory |
| Forbidden | NASS's harvested-for-grain forecast of year t (any vintage, June Acreage "harvested for grain" included) and anything computed from it: `kernelag.state_model` `nass_latest`, `d_not_grain`; `kernelag.state_panel` `grain_asof`. NASS finals of year t |

Code guards: every candidate declares its inputs; `check_tiers()` refuses a candidate whose inputs exceed its tier
and any eligible candidate that is not Tier B. `check_columns()` refuses model rows with a column named like the
grain forecast. NASS finals are read only through `History`, which raises `LookAheadError` for any year >= t. The
NASS planted loader reads only the item `CORN - ACRES PLANTED` with in-season reference periods; the NASS grain
forecast is read in exactly one function, `reproduce_grain()`, which reproduces the team's grain benchmark and
feeds no model. FSA files come only from `kernelag.fsa.latest_file` / `usable_files`, with an assertion that each
used file was published by the as-of date and that a crop year's own final file is never in-season input.

### 1.2 Data, as-of rule and notation

- t: target year; d: as-of date, primary 15 November of t; earliness runs 15 September and 15 October of t.
- S(y), G(y), P(y): NASS final state silage harvested, grain harvested and planted acres (Quick Stats "YEAR",
  `data/Quickstats Data/*_state_2000_2026.csv`, years <= 2025; identical to the incumbent's truth file
  `data/nass/corn_acres_state.csv` on all 2013-2025 values, checked in code). Y(y): NASS final grain yield.
  History: NASS finals from 2000 ("H00"); "H13" (finals from 2013) only to reproduce the incumbent exactly.
- Truth for scoring: S(t), NASS's latest revised final, the same values the incumbent scores against. States: the
  incumbent's 48 silage states; a year is scored on states with S(t) and S(t-1).
- P_nass(t,d): the latest NASS in-season planted figure of year t whose report month is <= d's month, in the order
  October, September, August, June, March (Quick Stats periods `YEAR - OCT ACREAGE/FORECAST`, `YEAR - SEP FORECAST`,
  `YEAR - AUG ACREAGE/FORECAST`, `YEAR - JUN ACREAGE`, `YEAR - MAR ACREAGE`; identical to the in-season planted rows
  of `data/nass/corn_acres_state.csv`, checked in code). Acreage is released at the end of June and Crop Production
  between the 8th and 12th of its month, so a report of month m is public by the 15th of m (the incumbent's rule).
  Known gap: for 2012-2017 only March exists in the repo.
- FSA (field corn, `data/fsa/fsa_corn_state.csv`): cur = newest crop-year-t file published by d; prev = final
  (January) file of t-1. F_pf = planted + failed acres over all intended uses; F_grain = planted acres with intended
  use grain; F_silage = planted acres with intended use silage (incl. forage).
- Season context (functions of `kernelag.context`, at d): drought = mean June-September share of the state in D2+ on
  maps dated <= d; poor = mean NASS poor + very poor share, weeks 30-36, weeks ending <= d; loss = RMA insured corn
  acres with a weather loss in months before d's month / insured acres (RMA files are today's vintage).
- Milk cows: NASS 1 January inventory of t and t-1 (published end of January of t).

### 1.3 Features (missing read as 0 = "no change", the incumbent's convention)

| Feature | Definition | Input (tier) | Expected sign |
|---|---|---|---|
| reversion | log(S(t-1) / mean(S(t-2), S(t-3), S(t-4))) | NASS finals < t (A) | - |
| d_planted | log(P_nass(t,d) / P(t-1)) | NASS planted (B) | + |
| d_fsa_nongrain | (1 - F_grain/F_pf)(cur) - (1 - F_grain/F_pf)(prev); missing if an F_pf < 500 acres | FSA (A) | + |
| yield_shock | log(latest NASS yield forecast of t published by d / mean(Y(t-1), Y(t-2), Y(t-3))) | NASS yield forecast (B) | - |
| d_drought | drought(t) - drought(t-1) | Drought Monitor (A) | + |
| d_poor | poor(t) - poor(t-1) | NASS condition (B) | + |
| d_loss | loss(t) - loss(t-1) | RMA (A) | + |
| d_cows | log(milk cows 1 Jan t / 1 Jan t-1) | NASS milk cows (B) | + |
| d_fsa_silage_hc | clip(log(F_silage(cur) / F_silage(prev)), -log 2, log 2) where F_silage(prev) >= 500 and F_silage(prev) / S(t-1) >= 0.75 (high coverage); else missing | FSA (A) | + |

d_fsa_nongrain replaces the incumbent's forbidden `d_not_grain` (computed from NASS's grain forecast).

### 1.4 Candidates

Shared: `fit_ridge` is `kernelag.state_model.fit_ridge` (pooled over states, weights S(t-1), features divided by
their std, no intercept, penalty 1 x mean weight, target log(S(y) / S(y-1))). For c1-c5 every fitted parameter is
fitted on state-years TRAIN_FROM = 2012 <= y < t only (the first year with both NASS in-season planted and an FSA
prior final), at the same as-of date, and needs at least 3 training years; with fewer (test years 2012-2014) the
candidate equals c0 exactly.

| Key | Tier | Prediction for state s, year t |
|---|---|---|
| `persistence` | benchmark | S(t-1) |
| `c0_incumbent_H13` | benchmark | kernelag `reversion_only` rebuilt on H13: must equal the stored backtest on 2017-2024 |
| `c0_reversion_only` (simplest) | history only | S(t-1) x exp(beta x reversion), beta by fit_ridge on all state-years 2001 <= y < t of H00 (Tier A's s1) |
| `c1_planted_fsa_ridge` | B | S(t-1) x exp(b . x), x = [reversion, d_planted, d_fsa_nongrain], b by fit_ridge |
| `c2_plus_stress` | B | c1 features + yield_shock, d_drought, d_poor, d_loss; fit_ridge |
| `c3_plus_dairy` | B | c1 features + d_cows, d_fsa_silage_hc; fit_ridge |
| `c4_monotone_gbt` | B | S(t-1) x exp(f(x)), x = the c2 and c3 features (9), f = XGBoost regressor, monotone constraints from the expected signs, fixed settings: 150 trees, depth 2, learning rate 0.05, min_child_weight 5, lambda 1, no subsampling, exact tree method, seed 0, sample weight S(t-1) / mean; target log(S(y) / S(y-1)) |
| `c5_residual_shrunk` | B | see below, planted = P_nass |
| `c5b_residual_fsa_planted_pre_june` | B | c5 with planted = P_nass if its vintage is June or later, else F_pf(cur) x P(t-1) / F_pf(prev) (added after seeing that 2012-2017 have only March; before any score) |

c5 (the residual model). Own grain estimate in the b1 form:
G_hat = P x [F_grain/F_pf](cur) x c, with ratio correction c = [G(t-1) / P(t-1)] / [F_grain/F_pf](prev).
Non-grain residual R_hat = P - G_hat; last year's R(t-1) = P(t-1) - G(t-1).
raw = S(t-1) x clip(R_hat / R(t-1), 0.5, 2), which equals R_hat x [S(t-1) / R(t-1)] (the state's prior silage share
of non-grain acres) when not clipped. Needs G(t-1) (41 states), F_pf(cur) and F_pf(prev) >= 500, F_grain(prev) > 0,
R(t-1) > 0; otherwise raw is missing and c5 = c0 for that state.
c5 = c0^(1-w) x raw^w, with one pooled w in {0, 0.05, ..., 1} minimizing sum |c5 - S| over training state-years
2012 <= y < t (c0 out of sample in each training year); smallest w on ties; null w = 0.

Diagnostics (never eligible): `d5_raw_residual`, `d5b_raw_residual` (raw with w = 1); and three that read NASS's
year-t FINAL planted and grain acres (forbidden; ceilings that measure the method, not models):
`d_oracle_final_residual` = S(t-1) x R(t) / R(t-1) with R(t) = P(t) - G(t) (the research note's 8.9% oracle);
`d5_oracle_planted` = c5 raw with P = P(t) final (isolates the grain-share error); `d5_oracle_grain` = S(t-1) x
clip((P_nass - G(t)) / R(t-1), 0.5, 2) (isolates the planted error). Residual error decomposition per year:
`out/residual_diagnostics.csv`.

### 1.5 Backtest, metrics, comparisons

- Test years 2012-2024 (13; primary). 2017-2024 reported for comparison with the team. 2018-2024 (years with June or
  later NASS planted) reported for information. 2025 is never used for fitting, selection or tuning in the backtest.
- Per year: state WAPE = sum |pred - actual| / sum actual; US error = (sum pred - sum actual) / sum actual over the
  scored states. Per candidate and period: mean state WAPE, mean |US error|, mean signed US error.
- Paired comparisons for every candidate, state WAPE and |US| error: mean yearly difference with a 90% bootstrap
  percentile interval (10,000 resamples of years, seed 20261114), years better / worse, against (a) the incumbent
  `reversion_only` (c0_incumbent_H13 on 2017-2024 and 2018-2024; c0_reversion_only on 2012-2024), (b) persistence,
  (c) c0_reversion_only. Pre-declared, information only: the same paired comparison against Tier A's selected
  `s3_fsa_residual`, read from `test_models/ownModels/silage/out/by_year.csv`.

### 1.6 Selection rule (mechanical; once; 15 November backtest)

1. Eligible: c1, c2, c3, c4, c5, c5b. Simplest: c0_reversion_only.
2. Period 2012-2024. For each eligible c: d_y = WAPE(c, y) - WAPE(c0, y); dbar = mean; SE = sd(d_y, ddof 1) / sqrt(13).
3. c qualifies if dbar + 2 SE < 0.
4. Selected = the qualifying candidate with the lowest mean WAPE (ties: order c1, c5, c5b, c2, c3, c4). If none
   qualifies, the selected model is c0_reversion_only.
5. The same rule on 2017-2024 and 2018-2024 is reported for information and does not change the choice.

### 1.7 After selection

- Earliness: every candidate rerun as of 15 September and 15 October (all inputs at those dates, parameters refitted
  at the same date); reported for the selected model.
- 2025: one information-only score of the selected model as of 15 November 2025 (FSA file of 2 September 2025;
  NASS planted September 2025 because the October 2025 report was cancelled), fitted on years up to 2024, written
  once to `out/score_2025_information_only.*`. `data/models/state_score_2025.*` is never touched.
- 2026: forecast of the selected model by state and US as of 15 November 2026, fitted on years up to 2025. 80%
  intervals: state = prediction x exp(10th, 90th percentile of log(actual / predicted)) in three size classes of
  S(t-1) from the selected model's 2012-2024 15 November backtest (`kernelag.state_model.error_quantiles`); US =
  total x exp(10th, 90th percentile of the 13 yearly US log errors). Leave-one-year-out coverage of the state
  intervals is reported.

Known look-ahead (accepted, stated): NASS finals, milk cows and RMA files are today's vintage; FSA publication dates
before 2025 are assumed (data date + 5 days); for 2026 the latest NASS planted in the repo is September (the
October 2026 report is not in the repo), so the 2026 forecast uses an older planted vintage than it could.

<!-- END OF PRE-REGISTRATION -->

Everything below was written after the scores were computed. `run.py` checks the hash of section 1 on every
run and stops if it changed (`out/run.json`, `"unchanged": true`).

## 2. Benchmark reproduction (done before any candidate was scored)

`run.py --check` rebuilt the team's benchmarks from the same truth the incumbent uses and compared every year with
`data/models/state_model_backtest.csv` (`out/reproduction.json`). The full run stops if the silage check fails.

| Benchmark (2017-2024) | Mine: state WAPE / mean abs US | Stored | All 8 years equal to 2 decimals |
|---|---|---|---|
| silage `reversion_only` (rebuilt on NASS finals from 2013) | 13.12 / 3.90 | 13.12 / 3.90 | yes |
| silage persistence | 14.53 / 4.08 | 14.53 / 4.08 | yes |
| grain NASS November forecast (`nass_latest`) | 1.66 / 0.82 | 1.66 / 0.82 | yes |
| grain persistence | 7.35 / 4.11 | 7.35 / 4.12 | yes (4.11 vs 4.12 is the mean of unrounded vs rounded yearly values) |

Data checks: the Quick Stats finals equal `data/nass/corn_acres_state.csv` on all 1,781 overlapping rows. The Quick
Stats in-season planted rows equal that file's in-season planted rows on all 1,671 overlapping rows. The NASS grain
forecast is read only in `reproduce_grain()`.

## 3. Backtest results, as of 15 November

All numbers come from `out/summary.csv` (means over years, percent). WAPE = state WAPE. US = mean |US error|.
Signed = mean signed US error.

| Candidate | Tier | WAPE 12-24 | US 12-24 | Signed 12-24 | WAPE 17-24 | US 17-24 | Signed 17-24 | WAPE 18-24 |
|---|---|---|---|---|---|---|---|---|
| `persistence` | benchmark | 15.84 | 5.76 | +0.02 | 14.53 | 4.08 | +0.11 | 14.85 |
| `c0_incumbent_H13` (report model) | benchmark | n/a | n/a | n/a | 13.12 | 3.90 | -0.98 | 13.24 |
| `c0_reversion_only` (simplest) | history | 14.11 | 4.85 | -1.71 | 13.01 | 3.73 | -0.99 | 13.13 |
| `c1_planted_fsa_ridge` | B | 14.03 | 5.10 | -1.52 | 12.91 | 4.00 | -0.85 | 13.08 |
| `c2_plus_stress` | B | 13.84 | 4.75 | -2.44 | 13.09 | 3.94 | -1.25 | 13.15 |
| `c3_plus_dairy` | B | 14.11 | 4.92 | -1.78 | 12.89 | 4.00 | -0.96 | 13.03 |
| `c4_monotone_gbt` | B | 14.77 | 5.65 | +0.61 | 14.46 | 4.95 | +2.68 | 14.64 |
| `c5_residual_shrunk` | B | 13.80 | 4.96 | -1.57 | 12.69 | 4.01 | -0.68 | 12.90 |
| **`c5b_residual_fsa_planted_pre_june`** | **B** | **13.80** | 4.93 | -1.59 | **12.65** | 3.94 | -0.73 | **12.86** |
| `d5_raw_residual` (c5, w = 1) | diagnostic | 16.79 | 7.02 | +0.45 | 15.67 | 5.25 | +0.85 | 16.15 |
| `d5b_raw_residual` (c5b, w = 1) | diagnostic | 16.85 | 7.46 | +0.07 | 15.56 | 5.28 | +0.82 | 16.15 |
| `d5_oracle_planted` (true final planted) | diagnostic, forbidden | 16.13 | 7.05 | -0.10 | 14.93 | 5.11 | +0.11 | 15.46 |
| `d5_oracle_grain` (true final grain) | diagnostic, forbidden | 19.07 | 8.55 | +3.94 | 15.29 | 5.26 | +4.48 | 14.22 |
| `d_oracle_final_residual` | diagnostic, forbidden | 8.44 | 2.61 | +1.04 | 9.68 | 3.40 | +2.36 | 10.47 |

State WAPE by year (`out/by_year.csv`). c1-c5b equal c0 exactly in 2012-2014, because they need 3 training years.

| Year | persist. | incumbent | c0 | c1 | c2 | c3 | c4 | c5 | **c5b** | raw c5b | oracle |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2012 | 23.32 | | 24.21 | 24.21 | 24.21 | 24.21 | 24.21 | 24.21 | 24.21 | 23.15 | 9.42 |
| 2013 | 25.35 | | 16.05 | 16.05 | 16.05 | 16.05 | 16.05 | 16.05 | 16.05 | 25.91 | 5.57 |
| 2014 | 14.15 | | 12.73 | 12.73 | 12.73 | 12.73 | 12.73 | 12.73 | 12.73 | 18.05 | 7.12 |
| 2015 | 13.60 | | 13.19 | 13.01 | 13.29 | 12.89 | 13.76 | 12.29 | 12.50 | 12.77 | 5.59 |
| 2016 | 13.23 | | 13.12 | 13.15 | 8.96 | 14.41 | 9.63 | 12.64 | 12.67 | 14.66 | 4.62 |
| 2017 | 12.33 | 12.33 | 12.17 | 11.74 | 12.65 | 11.87 | 13.22 | 11.25 | 11.24 | 11.42 | 4.14 |
| 2018 | 20.25 | 18.82 | 17.88 | 18.16 | 15.07 | 18.34 | 17.34 | 18.16 | 18.16 | 19.92 | 8.09 |
| 2019 | 17.20 | 14.83 | 14.58 | 14.27 | 14.10 | 14.21 | 14.94 | 14.90 | 14.77 | 23.46 | 9.93 |
| 2020 | 12.03 | 9.47 | 9.59 | 9.66 | 11.60 | 9.85 | 11.53 | 8.67 | 8.67 | 15.45 | 11.87 |
| 2021 | 14.43 | 12.35 | 12.31 | 11.65 | 8.38 | 11.50 | 12.68 | 12.04 | 12.04 | 12.61 | 10.68 |
| 2022 | 14.16 | 15.38 | 15.48 | 15.61 | 17.10 | 15.13 | 17.92 | 14.86 | 14.86 | 13.09 | 18.48 |
| 2023 | 13.53 | 9.80 | 9.99 | 10.66 | 12.47 | 9.96 | 15.48 | 10.09 | 9.92 | 16.42 | 8.11 |
| 2024 | 12.34 | 12.00 | 12.11 | 11.52 | 13.31 | 12.23 | 12.58 | 11.59 | 11.59 | 12.07 | 6.11 |

Paired comparisons, 15 November (`out/comparisons.csv`): mean yearly difference in points, 90% bootstrap interval,
years better / worse. Negative = the candidate is better.

| Candidate | vs | Period | State WAPE diff [90% CI] | Better / worse | abs US diff [90% CI] |
|---|---|---|---|---|---|
| **c5b** | incumbent `reversion_only` (H13) | 2017-2024 | -0.47 [-0.68, -0.25] | 7 / 1 | +0.03 [-0.44, +0.60] |
| **c5b** | persistence | 2017-2024 | -1.88 [-2.63, -1.09] | 7 / 1 | -0.14 [-0.84, +0.58] |
| **c5b** | c0 = incumbent algorithm (H00) | 2012-2024 | -0.31 [-0.49, -0.13] | 8 / 2 (3 tied) | +0.09 [-0.28, +0.51] |
| **c5b** | persistence | 2012-2024 | -2.04 [-3.23, -1.01] | 11 / 2 | -0.82 [-3.22, +0.95] |
| c5 | incumbent (H13) | 2017-2024 | -0.43 [-0.67, -0.18] | 6 / 2 | +0.11 [-0.43, +0.79] |
| c5 | c0 | 2012-2024 | -0.30 [-0.50, -0.10] | 7 / 3 | +0.12 [-0.28, +0.60] |
| c1 | c0 | 2012-2024 | -0.08 [-0.23, +0.09] | 5 / 5 | +0.26 [-0.13, +0.71] |
| c2 | c0 | 2012-2024 | -0.27 [-1.24, +0.62] | 4 / 6 | -0.10 [-0.59, +0.38] |
| c3 | c0 | 2012-2024 | -0.00 [-0.21, +0.23] | 6 / 4 | +0.07 [-0.48, +0.65] |
| c4 | c0 | 2012-2024 | +0.67 [-0.19, +1.57] | 2 / 8 | +0.81 [-0.49, +2.19] |
| c4 | incumbent (H13) | 2017-2024 | +1.34 [+0.25, +2.60] | 1 / 7 | +1.04 [-0.97, +3.22] |

Pre-declared information-only comparison against Tier A's selected `s3_fsa_residual` (`out/vs_tierA_s3.csv`, read
from Tier A's own `by_year.csv`): c5b minus s3 = **+0.08 [-0.00, +0.16]** on 2012-2024 (5 better, 8 worse) and
**+0.13 [+0.04, +0.22]** on 2017-2024 (2 better, 6 worse). abs US: -0.03 [-0.19, +0.13] and -0.06 [-0.31, +0.19].
c1, c3 and c4 are also worse than s3, with intervals above zero.

By region (pooled WAPE 2012-2024, `out/by_region.csv`): c5b vs c0: dairy states 8.56 vs 8.86, Plains 21.62 vs 22.12,
Corn Belt 17.60 vs 17.69, other 11.67 vs 11.92. Oracle: 1.82, 16.89, 12.96, 10.41.

Fitted parameters (`out/fitted_params.csv`). c5 and c5b weight w: 0 for 2012-2014, then 0.15 (2015), and 0.25-0.30
from 2016 on; 0.25 for 2026. Ridge weights per standard deviation, fitted for 2026 on 2012-2025: c1 reversion -0.135,
d_planted +0.031, d_fsa_nongrain +0.012. c2 adds yield_shock -0.070, d_drought +0.024, d_poor +0.028 and d_loss -0.023
(the only sign against expectation). c3 adds d_cows +0.017 and d_fsa_silage_hc +0.023. Every effect is small next to
reversion.

## 4. Selection (rule 1.6 applied mechanically; `out/selection.json`)

| Candidate | Mean WAPE 2012-24 | Mean diff vs c0 | SE | diff + 2 SE | Qualifies |
|---|---|---|---|---|---|
| c1_planted_fsa_ridge | 14.03 | -0.08 | 0.10 | +0.12 | no |
| c5_residual_shrunk | 13.80 | -0.30 | 0.13 | -0.05 | yes |
| **c5b_residual_fsa_planted_pre_june** | **13.80** | **-0.31** | **0.11** | **-0.08** | **yes** |
| c2_plus_stress | 13.84 | -0.27 | 0.59 | +0.91 | no |
| c3_plus_dairy | 14.11 | -0.00 | 0.14 | +0.28 | no |
| c4_monotone_gbt | 14.77 | +0.67 | 0.56 | +1.78 | no |

c0 mean: 14.11%. **Selected: `c5b_residual_fsa_planted_pre_june`**: its mean WAPE is 13.800 against c5's 13.805.
The same rule on 2017-2024 and on 2018-2024 is reported for information in `selection.json`.

## 5. How close c5 gets to the oracle, and why

The oracle `S(t-1) x R(t) / R(t-1)` uses NASS's final planted and grain acres of year t. NASS publishes those on
the same day as the silage answer, so the oracle is a ceiling, not a model. Here the truth is NASS's latest revised
final. The research note's 8.9% covers 2019-2025 and is scored against first January estimates.

| Period | Reference | Reference WAPE | c5b | c5 | Oracle | Share of the gap closed by c5b (c5) |
|---|---|---|---|---|---|---|
| 2012-2024 | c0 | 14.11 | 13.80 | 13.80 | 8.44 | 5.4% (5.3%) |
| 2017-2024 | incumbent H13 | 13.12 | 12.65 | 12.69 | 9.68 | 13.6% (12.5%) |
| 2018-2024 | incumbent H13 | 13.24 | 12.86 | 12.90 | 10.47 | 13.7% (12.2%) |
| 2019-2024 (closest to the note) | incumbent H13 | 12.31 | 11.97 | 12.02 | 10.86 | 23.0% (19.6%) |

Why the gap stays (`out/residual_diagnostics.csv`, 41 states with a NASS grain final, 15 November):

1. **The residual is small.** Planted minus grain is 8.6% of planted acres (2012-2024 mean).
2. **c5's residual is P x (1 - g_hat), so planted errors barely matter.** g_hat is the own grain share of planted
   acres. A planted error of e% moves the residual by e%. With NASS March planted, 2012-2017 planted errors average
   3.08% (c5); with FSA-scaled planted (c5b) they average 1.00%; NASS June-or-later planted in 2018-2024 averages
   0.63%. Yet the residual error is about the same in every case: 21.9% (c5), 21.7% (c5b), 21.3% (2018-2024).
   That is why c5 and c5b are almost identical, and why giving the model NASS's true final planted acres
   (`d5_oracle_planted`) only moves the raw residual from 16.79% to 16.13%.
3. **The non-grain share is the whole problem.** A 1-point error in the grain share of planted (0.91 instead of 0.90)
   is an 11% residual error. The FSA in-season non-grain share, corrected by last year's NASS/FSA ratio, misses
   NASS's final residual by 21.5% (2012-2024). Last year's residual misses it by 21.5% too. In 2018-2024 the FSA
   share does slightly worse than last year's residual (21.3% vs 20.5%). FSA records the intended use certified
   in July. Acres certified as grain that are later chopped, grazed or abandoned stay "grain" in FSA. That late
   switch is what the oracle knows.
4. **Giving the model the true grain acres does not reach the oracle either.** `d5_oracle_grain` (NASS in-season
   planted minus final grain) scores 14.22% on 2018-2024 against the oracle's 10.47%. Here a 0.63% planted error is
   a 7% residual error, because the planted error no longer cancels. NASS's final planted and grain acres are
   revised together, and only their difference is precise.
5. **The blend still helps a little.** At w = 0.25 the residual's errors are only partly correlated with the
   reversion model's errors. c5b beats c0 in 8 of the 10 years in which it differs, and in every region.

## 6. Earliness, 2025 information score, 2026 forecast

**Earliness of the selected c5b** (inputs at each date and parameters refitted at that date; `out/summary.csv`):

| As of | WAPE 2012-24 | abs US 2012-24 | WAPE 2017-24 | abs US 2017-24 | WAPE 2018-24 | Inputs that change |
|---|---|---|---|---|---|---|
| 15 September | 13.91 | 4.97 | 12.76 | 3.97 | 12.94 | September FSA file, NASS June/Aug/Sep planted |
| 15 October | 13.82 | 4.96 | 12.67 | 3.99 | 12.88 | October FSA file, NASS October planted where published |
| 15 November | 13.80 | 4.93 | 12.65 | 3.94 | 12.86 | November FSA file |
| c0 (any date) | 14.11 | 4.85 | 13.01 | 3.73 | 13.13 | none |

Most of the gain is already there on 15 September. FSA files used per year and date: `out/inputs_used.csv`.

**2025, information only.** Computed once after selection with `--score-2025`, fitted on years up to 2024, as of
15 November 2025. Inputs: FSA file with data as of 2 September 2025, because the October and November 2025 files
were never released; NASS September planted, because the October 2025 report was cancelled. Files:
`out/score_2025_information_only.csv` and `.json`.

| 2025 | State WAPE | US error | States inside 80% interval |
|---|---|---|---|
| c5b | 14.52% | +3.66% | 83% |
| persistence | 13.96% | +0.32% | |
| incumbent, stored score (`data/models/state_score_2025.json`, not modified) | 14.14% | +3.06% | 81% |
| Tier A s3 (its own README) | 14.32% | +4.04% | |

c5b did not beat persistence or the incumbent in 2025. Largest misses: overpredictions in Iowa (+100,500 acres),
Kansas (+93,400), South Dakota (+80,900), North Dakota (+79,800) and Nebraska (+75,400). Underpredictions in Wisconsin
(-91,500), Texas (-49,200) and New York (-44,400).

**2026 forecast** (`out/forecast_2026.csv`). As of 15 November 2026: FSA file with data as of 5 Nov 2026
(published 10 Nov), NASS September 2026 planted, fitted on 2012-2025, w = 0.25. State 80% intervals use the
size-class log-error quantiles of the 2012-2024 backtest. The US interval uses the 10th and 90th percentiles of the 13
yearly US log errors. Leave-one-year-out coverage of the state intervals: 0.788 at 80%, 0.896 at 90%. In 2026, c5 and
c5b give the same numbers, because the NASS planted vintage is September.

| | 2026 forecast | 80% interval | 2025 NASS final |
|---|---|---|---|
| **US (sum of 48 states)** | **6,285,100** | 6,012,600 - 6,752,800 | 6,187,000 |
| Wisconsin | 835,300 | 672,900 - 1,083,000 | 885,000 |
| New York | 476,600 | 384,000 - 618,000 | 495,000 |
| South Dakota | 427,100 | 344,100 - 553,800 | 390,000 |
| Minnesota | 373,200 | 300,600 - 483,800 | 360,000 |
| California | 350,900 | 282,700 - 455,000 | 370,000 |
| Michigan | 336,300 | 270,900 - 436,100 | 340,000 |
| Pennsylvania | 325,900 | 262,500 - 422,500 | 315,000 |
| Iowa | 298,600 | 240,600 - 387,200 | 250,000 |
| Kansas | 278,700 | 224,500 - 361,400 | 230,000 |
| Nebraska | 269,600 | 217,200 - 349,500 | 220,000 |
| Idaho | 259,100 | 208,700 - 335,900 | 280,000 |
| Texas | 239,200 | 192,700 - 310,100 | 245,000 |
| Colorado | 200,400 | 161,400 - 259,800 | 200,000 |
| North Dakota | 193,700 | 156,000 - 251,200 | 170,000 |

US totals of the other candidates for 2026 (`out/forecast_2026_all_candidates.csv`): c0 6,333,200; c1 6,304,500;
c2 6,467,700; c3 6,354,100; c4 6,541,300; persistence 6,187,000.

**Side result: the own grain estimate** (c5's G_hat, b1 form; `out/own_grain_estimate_scores.csv`, 41 states, 15 Nov).
Information for the grain agents, not a deliverable here. State WAPE: c5b form 2.22% (2012-2024) and 2.09% (2017-2024);
c5 form (NASS March planted before 2018) 2.94% and 2.29%. On 2017-2024 that compares with NASS's November forecast at
1.66% and persistence at 7.35%.

## 7. Verdict

- **Selected Tier B silage model: `c5b_residual_fsa_planted_pre_june`**, chosen by the pre-registered rule. It is
  the incumbent's reversion model blended in logs, a quarter of the way, toward a non-grain residual estimate:
  NASS planted (FSA-scaled where NASS has only March) minus an own grain estimate (planted x FSA grain share x
  last year's NASS/FSA correction). It never reads NASS's grain forecast.
- **It beats the report's silage model on state error:** 12.65% vs 13.12% on 2017-2024 (-0.47 [-0.68, -0.25], 7 of
  8 years better). On 2012-2024 it scores 13.80% vs 14.11% (-0.31 [-0.49, -0.13]). It does not improve the US total
  (3.94% vs 3.90% on 2017-2024; the interval includes zero), and it lost to persistence and the incumbent in 2025.
- **The current-year NASS inputs add nothing measurable for silage.** NASS planted change, the FSA non-grain share
  change (the replacement for `d_not_grain`), the stress block (yield forecast, drought, crop condition, RMA losses)
  and the dairy block (milk cows, FSA silage in high-coverage states) all fail the two-standard-error rule. The
  monotone GBT is worse than c0, significantly so on 2017-2024. The selected Tier B model is slightly *worse* than
  Tier A's s3, which uses no current-year NASS data at all (+0.13 [+0.04, +0.22] on 2017-2024).
- **Recommendation to the report owner** (this folder edits nothing else): for silage, NASS's in-season data is not
  worth the independence it costs. Tier A's s3 is at least as accurate and fully independent. Tier B c5b is a
  cross-check that agrees with it: 2026 US 6,285,100 here against Tier A's 6,297,900.
- **The oracle gap stays because of the non-grain share, not because of planted acres.** FSA's July intended use
  cannot see grain acres that are later chopped or abandoned. NASS's own November grain forecast would be the
  current-year signal for that switch, and it is forbidden here. Closing the gap needs a harvest-fate signal,
  which is what the satellite field work aims at.

## 8. Deviations and limitations

**Deviations from the pre-registration: none in method.** Two output fixes were made after the first scored run.
Neither changed any prediction (`backtest_by_state_year.csv` and `selection.json` are byte-identical before and
after):
1. `summary.csv` listed `c0_incumbent_H13` under 2012-2024 using only its 8 years. A period row now needs every year
   of the period.
2. In `score_2025_information_only.json` the field `fsa_file` shows the 2011 row of the input log (it took the first
   entry), not the 2025 file. The score was not recomputed (one-time rule). The code is fixed for any future use.
   The file actually used for 2025 is the `inputs_used.csv` row with year 2025, as-of nov: data 2 September 2025,
   published 12 September 2025.

Limitations:
- **NASS in-season planted, 2012-2017:** only the March Prospective Plantings figure is in the repo. Quick Stats has
  no state June Acreage before 2018 in the team's pull. I tried to download the 2012-2017 Acreage reports from
  USDA's ESMIS archive, and the session's permission policy blocked the request. I did not retry. c5b's rule exists
  for this reason. It was added after I saw the coverage and before any score.
- NASS finals, milk cows and RMA files are today's vintage, not what was public each November (mild look-ahead,
  shared with the incumbent). Truth is NASS's latest revised final, not the first January estimate. NASS milk-cow
  state estimates cover 31 states in 2025-2026 (48 before).
- FSA publication dates before 2025 are assumed: data date + 5 days.
- For 2026 the latest NASS planted in the repo is the September report. The October 2026 report is not in the repo,
  so the forecast uses an older planted vintage than 15 November allows. Section 5 shows planted error barely
  affects c5b.
- 13 test years (8 for team comparison). c1-c5b equal c0 in 2012-2014, so those 3 years are tied in the paired rule.
  The rule treats years as exchangeable. 2012, the drought year, dominates US error.
- The US 80% interval comes from 13 yearly errors and is coarse. No US 90% interval is given.
- 7 states (CT, ME, MA, NH, RI, VT, NV; about 0.17 M acres) have no NASS grain estimate. c5 and c5b fall back to c0
  there.
- The oracle diagnostics read year-t NASS finals. They measure the method; they are not models.

## 9. Inputs used, by candidate (every column with its source; `out/input_columns.csv`)

| Column | Source (tier) | Used by |
|---|---|---|
| S(t-1..t-4), reversion | NASS final silage acres, years < t, Quick Stats `CORN, SILAGE - ACRES HARVESTED` "YEAR" (A) | all |
| P(t-1), G(t-1) | NASS final planted / grain harvested acres, t-1, Quick Stats "YEAR" (A) | c1-c5b |
| P_nass, d_planted | NASS `CORN - ACRES PLANTED`, in-season periods of year t (B) | c1-c5b |
| F_pf, F_grain, F_silage (cur, prev) | `data/fsa/fsa_corn_state.csv` via `kernelag.fsa.latest_file` / `usable_files` (A) | c1-c5b |
| d_fsa_nongrain | FSA, as above (A) | c1-c4 |
| yield_shock | NASS `CORN, GRAIN - YIELD` forecasts of t (B) and finals of t-1..t-3 (A) | c2, c4 |
| d_drought | `data/drought/usdm_state_weekly_2000_2026.csv` via `kernelag.context.drought` (A) | c2, c4 |
| d_poor | NASS weekly condition, `corn_condition_weekly_state_2000_2026.csv`, `kernelag.context.poor_condition` (B) | c2, c4 |
| d_loss | `data/rma/cause_of_loss_corn` and `insured_by_type_corn` via `kernelag.context.loss_share` (A) | c2, c4 |
| d_cows | NASS `CATTLE, COWS, MILK - INVENTORY` 1 Jan, `milk_cow_inventory_state_2000_2026.csv` (B) | c3, c4 |
| d_fsa_silage_hc | FSA silage-intended, high-coverage gate on S(t-1) (A) | c3, c4 |
| G_hat, raw5 | built from P (NASS or FSA-scaled) and FSA shares; never NASS's grain forecast | c5, c5b |

Not used anywhere in a model: `kernelag.state_panel` `grain_asof`, `kernelag.state_model` `nass_latest` /
`d_not_grain`, Quick Stats `CORN, GRAIN - ACRES HARVESTED` in-season periods (June Acreage harvested-for-grain
included), and the crop1126 grain table.

## 10. Files and how to run

From the repository root:

```bash
.venv/Scripts/python.exe test_models/ownModels/tierB/silage/run.py --check    # reproduction + coverage, no scores
.venv/Scripts/python.exe test_models/ownModels/tierB/silage/run.py            # about 20 s; rewrites out/ (not the 2025 files)
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/tierB/silage/test_run.py
.venv/Scripts/python.exe -m ruff check --select E,F,W --line-length 120 test_models/ownModels/tierB/silage/
```

`--prereg` (already run, refuses a second time) hashed section 1. `--score-2025` (already run once, refuses to
overwrite) wrote the 2025 files.

| File | Content |
|---|---|
| `out/backtest_by_state_year.csv` | state, year, asof, asof_key, candidate, pred, actual, last: 2012-2024, three as-of dates |
| `out/by_year.csv`, `out/summary.csv` | yearly state WAPE and US error; means per candidate, period, as-of date |
| `out/comparisons.csv`, `out/vs_tierA_s3.csv` | paired-year differences with 90% bootstrap intervals |
| `out/selection.json` | the selection rule's numbers (2012-2024; 2017-2024 and 2018-2024 for information) |
| `out/reproduction.json` | silage and grain benchmarks, year by year, against the stored backtest; data checks |
| `out/fitted_params.csv` | per year and as-of date: c0 beta, ridge weights c1-c3, w for c5 / c5b |
| `out/inputs_used.csv`, `out/input_columns.csv` | FSA files and NASS planted vintages used; column registry with sources |
| `out/residual_diagnostics.csv`, `out/own_grain_estimate_scores.csv`, `out/by_region.csv` | why c5 is far from the oracle; own grain estimate; regions |
| `out/forecast_2026.csv`, `out/forecast_2026_all_candidates.csv` | 2026 forecast of c5b with intervals; US totals of all candidates |
| `out/score_2025_information_only.*` | the one-time 2025 information score |
| `out/preregistration.sha256`, `out/run.json` | pre-registration hash; run metadata and caveats |
