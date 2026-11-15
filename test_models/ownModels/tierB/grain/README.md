# Tier B ("NASS-informed") corn-for-grain harvested acres by state

Owner key: `tierb_grain`. Folder: `test_models/ownModels/tierB/grain/`. Code: `run.py` (models, backtest, forecast),
`fetch_reports.py` (NASS in-season planted acres from the archived reports). Tests: `test_run.py`. Outputs: `out/`.

User directives (2026-11-14): "we cant just use their nass forecast., we should have our own models." then
"we can use the nass to train it". The team report's grain number is NASS's own November harvested-for-grain forecast
passed through (`kernelag/state_model.py`, predictor `nass_latest`). This folder builds Tier B models: trained on NASS
history, allowed to use current-year NASS inputs that are **not** the acreage answer, never NASS's grain forecast.

## 1. Pre-registration (written 2026-11-14, before any score of b0-b7 was computed)

### 1.0 What I had already seen when writing this section

- The incumbent's benchmark numbers (`data/models/state_model_backtest.csv`): on 2017-2024 NASS November
  (`nass_latest`) 1.66% mean state WAPE and 0.82% mean |US error|; persistence 7.35% / 4.12%.
- The Tier A grain agent's results (`test_models/ownModels/grain/out/summary.csv`, `selection.json`): FSA-only
  candidates; on 2012-2024 at 15 Nov g1 (FSA grain acres x last year's NASS/FSA ratio) 2.15% / 1.15%, g3 (same with
  the median of three years' ratios) 1.94% / 1.12% and selected; the stress correction g4 gained nothing over g1;
  nass_latest 1.61% / 0.58% on 2012-2024. This is why b5 (multi-year median correction) is in the list below.
- Daniel's README (`test_models/danielModel/README.md`): `grain_gbt_independent` 2.6% state / 1.6% |US| on 2012-2024,
  and its 2025 score (1.1% / +0.1%). I saw that 2025 number; nothing here is chosen with it.
- The Tier A audit of Daniel's model (`test_models/ownModels/grain/out/daniel_gbt_audit.json`): its starting value
  uses NASS **final** planted acres for years before 2018 (a look-ahead).
- My own parse of NASS's in-season planted acres (section 2) and its exact match with the repo's table for 2018-2025.
  No prediction of any b-candidate had been computed or scored.

### 1.1 Tier and inputs (every column traced to its source)

Tier B: inputs for target year t may include NASS current-year **planted** acres, NASS **yield** forecasts, NASS weekly
crop **condition** and progress, plus every Tier A source. **Forbidden for year t**: NASS's harvested-for-grain
forecast (June Acreage, Aug-Nov Crop Production) and anything computed from it (`kernelag.state_model` `nass_latest`,
`d_not_grain` / `not_grain`, `kernelag.state_panel.grain_asof`). `run.py` never reads `grain_asof` or a grain-forecast
period for a model; the NASS benchmark is built in a separate function used only for scoring and comparison.

| Symbol / column | Definition | Source (file, function) | As-of rule for date D of year t |
|---|---|---|---|
| G(y) | NASS final corn-for-grain harvested acres, state, year y | `data/nass/corn_acres_state.csv` (period `final`, 2013-2025; the incumbent's truth); 2011-2012 from `data/Quickstats Data/corn_grain_harvested_acres_state_2000_2026.csv` (period `YEAR`), checked equal to the repo table where both exist | history only (y < t); G(t) is the truth, read only by the scorer |
| P(y) | NASS final corn planted acres (all purposes) | same two files, `planted` / `CORN - ACRES PLANTED` | y < t |
| Pa(t, D) | NASS's latest state corn **planted** acres published on or before D: June Acreage (end of June) or the planted column of an Aug/Sep/Oct/Nov Crop Production state table | `data/nass_planted_inseason.csv` in this folder, parsed by `fetch_reports.py` from the archived report text files (ESMIS); equal to `data/nass/corn_acres_state.csv` for every overlapping row 2018-2025 | report release date <= D |
| Fg(file), Fall(file) | FSA field-corn planted acres with intended use grain; FSA field-corn planted + failed acres, all intended uses | `data/fsa/fsa_corn_state.csv`, `data/fsa/fsa_files.csv` | `kernelag.fsa.latest_file(files, D, t)` = newest in-season crop-year-t file published by D ("cur"); fin(y) = the final file of crop year y, used only for y < t and only if `kernelag.fsa.usable_files` admits it |
| sigma(file) | Fg / Fall (FSA grain-intended share of FSA corn planted) | derived | as above |
| s(y) | G(y) / P(y) (NASS grain share of planted) | derived | y < t |
| Ya(t, D) | NASS's latest state grain yield forecast (Aug, Sep, Oct, Nov) published by D | `data/Quickstats Data/corn_grain_yield_state_2000_2026.csv`, periods `YEAR - <MON> FORECAST` (a NASS yield forecast; not computed from the area forecast) | forecast month <= D's month (reports come out before the 15th) |
| Y(y) | NASS final grain yield | same file, period `YEAR` | y < t |
| drought(y) | mean June-Sep share of the state in D2 or worse | `data/drought/usdm_state_weekly_2000_2026.csv` via `kernelag.context.drought` | maps dated <= D |
| poor(y) | mean share of corn rated poor or very poor, weeks 30-36 | `data/Quickstats Data/corn_condition_weekly_state_2000_2026.csv` via `kernelag.context.poor_condition` | weeks ending <= D |
| loss(y) | insured corn acres with a weather loss (drought, heat, irrigation failure, hot wind, hail, wind, frost, freeze) / insured corn acres | `data/rma/cause_of_loss_corn/`, `data/rma/insured_by_type_corn/` via `kernelag.context.loss_share` | month of loss < D's month; RMA files are today's vintage (mild look-ahead, same caveat as the incumbent) |

Features (all "change from t-1 to t", computed at the same as-of date in both years):
- `d_fsa_share` = log sigma(cur) - log sigma(fin(t-1)) (expected sign on the grain share: +)
- `yield_shock` = log(Ya(t) / mean(Y(t-1), Y(t-2), Y(t-3))) (+: a poor yield season means more abandonment and silage)
- `d_drought` = drought(t) - drought(t-1) (-)
- `d_poor` = poor(t) - poor(t-1) (-)
- `d_loss` = loss(t) - loss(t-1) (-)
A missing feature is read as 0 ("no change"). Not used: NOAA weather, livestock inventories, prices (allowed, not needed for the pre-registered set).

### 1.2 Candidates

| Candidate | Prediction for state s, year t, as-of D | Fitted? |
|---|---|---|
| `b0_planted_x_share` (simplest) | Pa(t) x s(t-1) | no |
| `b1_planted_x_fsa_share` | Pa(t) x sigma(cur) x [s(t-1) / sigma(fin(t-1))] | no |
| `b2_ridge` | Pa(t) x s(t-1) x exp(f(x)), f = weighted ridge on the five features (scaled by their std over the training rows, no centring, no intercept, penalty 1.0 x mean weight: the incumbent's `fit_ridge` form), target log(G(y) / (Pa(y) s(y-1))) clipped to +-0.5, weights G(y-1), pooled over states | yes |
| `b3_gbt_monotone` | same target, inputs and weights; `sklearn` `HistGradientBoostingRegressor(max_depth=2, max_iter=150, learning_rate=0.05, min_samples_leaf=15, l2_regularization=1.0, early_stopping=False, random_state=0)`, monotone constraints d_fsa_share +1, yield_shock +1, d_drought -1, d_poor -1, d_loss -1; prediction clipped to +-0.5 | yes |
| `b4_daniel_gbt_independent` (reference only, never selectable) | Daniel's `grain_gbt_independent` (`test_models/danielModel/train_gbt.py`, imported read-only, its own panel `out/panel_nov.csv`), re-scored here on the same truth and years. Known look-ahead: its planted input is NASS **final** planted before 2018 | (his) |
| `b5_planted_x_fsa_share_median` | Pa(t) x sigma(cur) x median over k = 1..3 of [s(t-k) / sigma(fin(t-k))], using the k whose final FSA file is usable (2012: k = 1; 2013: k = 1, 2) | no |
| `b6_b1_plus_stress` | b1 x exp(g(x)), g = the b2 ridge form on (yield_shock, d_drought, d_poor, d_loss), target log(G(y) / b1(y)) clipped to +-0.5 | yes |
| `b7_blend_b5_fsa_level` | sqrt(b5 x g3), g3 = Fg(cur) x median over k = 1..3 of [G(t-k) / Fg(fin(t-k))] (FSA grain acres scaled to NASS: an FSA-level estimate that does not use Pa) | no |

Fitted candidates (b2, b3, b6): expanding window. For test year t the training rows are state-years y with
2012 <= y < t at the same as-of date (2012 is the first year with a usable t-1 FSA final file). With fewer than 3
training years (test years 2012-2014) the candidate returns b1 (b2 and b3: b1 is f with coefficient 1 on d_fsa_share
and 0 elsewhere; b6: g = 0).

Guards (identical for all, chosen without looking at any ratio): if sigma(cur) or sigma(fin) is missing or <= 0, or a
correction factor s/sigma (or its median) is outside [0.25, 4.0], b1/b5/b6 fall back to b0 for that state; g3 falls
back to G(t-1) when Fg is missing or its ratio is outside [0.25, 4.0]; if Pa(t) or s(t-1) is missing, b0 falls back to
G(t-1). Every state with a NASS grain final in t-1 is predicted (41 states every year).

### 1.3 Truth, metrics, periods, benchmarks

- Truth: NASS final state grain acres as the incumbent uses them (above); the US total is the sum of the 41 states.
- Per year: state WAPE = sum |pred - actual| / sum actual; US error = (sum pred - sum actual) / sum actual.
  Reported: mean state WAPE over years, mean |US error|, mean signed US error.
- Periods: primary 2012-2024 (13 years; all inputs exist for every year: Pa from June Acreage 2012 on, FSA from the
  2011 final file on). 2017-2024 reported separately for comparison with the team.
- Benchmarks first, reproduced exactly: NASS November forecast (`nass_latest`) 1.66% / 0.82% and persistence 7.35% /
  4.12% on 2017-2024, from the incumbent's code (`kernelag.state_panel.load_panel`, `kernelag.state_model.add_changes`,
  `predict_grain`); 2012-2013 (absent from the incumbent's table) rebuilt with the same rule from the Quick Stats files
  and checked equal to the incumbent's output for 2014-2024. For silage benchmarks see the silage agents.
- Comparisons: paired by year, 90% bootstrap interval (10,000 resamples of years, seed 20261114) of the mean yearly
  difference in state WAPE and in |US error|, candidate minus (a) `nass_latest`, (b) persistence, (c) b0.

### 1.4 Selection rule (mechanical, applied once on the 15 Nov backtest, 2012-2024)

1. Eligible: b0, b1, b2, b3, b5, b6, b7. Simplest: b0. (b4 is reference only.)
2. best = eligible candidate with the lowest mean state WAPE over 2012-2024.
3. If best is b0, select b0. Otherwise d_y = WAPE(b0, y) - WAPE(best, y); select best only if
   mean(d) > 2 x sd(d) / sqrt(13) (sd with ddof 1); else select b0.
4. The selected model's 15 Sep and 15 Oct backtests are reported as earliness (same specification, inputs as of
   those dates, fitted at the same as-of date). The 15 Nov selection is the headline.
5. The selected model is scored on 2025 once (`out/score_2025_information_only.json`, refuses to overwrite;
   information only, never used to change anything) and gives the 2026 forecast. 2025 is never used for a backtest
   fit, for selection or for interval quantiles; the 2026 forecast, being expanding-window, uses 2025 as history.

### 1.5 Intervals for the 2026 forecast

State 80% interval: prediction x exp(q10, q90) of log(actual / pred) over the selected model's 2012-2024 15 Nov
backtest, pooled within three size classes (tertiles of G(t-1) over the backtest rows). US 80% interval:
total x exp(+-1.2816 x RMS of the yearly log(actual US / predicted US)); the empirical 10%/90% quantiles of the 13
yearly US log errors are reported beside it. Coverage is checked leaving one year out.

---

Everything below section 1 was written after the scores were computed. Section 1 is unchanged: its sha256 is in
`out/preregistration.sha256` and a copy of the file as it stood then is `out/preregistration_README_snapshot.md`.

## 2. Added data: NASS in-season planted acres, 2012-2026 (`fetch_reports.py`)

The Quick Stats files in `data/Quickstats Data/` keep NASS's in-season state planted figures only from 2018. For
2012-2017 they hold March intentions and the January final only. The archived report texts on USDA ESMIS hold what
NASS actually published during each season. `fetch_reports.py` downloaded 76 files into `data/reports/` (15 MB;
URL, release date and sha256 per file in `data/reports_manifest.csv`): June Acreage 2012-2026 and Aug-Nov Crop
Production 2012-2026. It parsed only the corn **planted** column into `data/nass_planted_inseason.csv` (1,680 state
values). Check: all 1,008 state-report values that also exist in `data/nass/corn_acres_state.csv` (2018-2026) are
identical (max difference 0 acres; `out/reproduction.json`). The harvested-for-grain columns of the same tables are
never read: the parser cuts the planted column out by its character span. `test_run.py` tests both table layouts.

The planted figure each forecast used (the latest report published by the as-of date; `out/planted_asof_used.csv`):

| As-of | 2012 | 2013 | 2014-2018 | 2019 | 2020 | 2021 | 2022-2026 |
|---|---|---|---|---|---|---|---|
| 15 Sep | Jun | Jun | Jun | Aug | Jun | Sep | Sep |
| 15 Oct | Oct | Jun | Oct | Oct | Oct | Oct | Sep |
| 15 Nov | Oct | Nov | Oct | Oct | Oct | Oct | Sep |

The October 2013 and October 2025 Crop Production reports were cancelled (federal shutdowns). From 2022 on, the
October and November reports carry no state planted table, so the September figure is the latest one.

## 3. Results

### 3.1 Reproduction (checked before any candidate was compared)

- NASS November forecast (`nass_latest`), 2017-2024: **1.66% / 0.82%** (expected 1.66 / 0.82). Persistence:
  **7.35% / 4.12%** (expected 7.35 / 4.12). Every yearly value equals the incumbent's stored
  `data/models/state_model_backtest.csv` to 0.00 points, with 41 states every year.
- The rebuilt NASS benchmark equals the incumbent's own `predict_grain` for every state-year 2014-2024 at 15 Sep,
  15 Oct and 15 Nov (max difference 0 acres).
- I wrote g3 (the FSA-only estimate inside b7) independently. It matches the Tier A agent's `g3_fsa_ratio_multi`
  within 49 acres in all 533 state-years.

### 3.2 Backtest at 15 Nov (`out/summary.csv`; mean over years)

| Candidate | Tier | State WAPE 2012-2024 | \|US\| 2012-2024 | Signed US 2012-2024 | State WAPE 2017-2024 | \|US\| 2017-2024 | Signed US 2017-2024 |
|---|---|---|---|---|---|---|---|
| nass_latest (NASS's own forecast, benchmark) | not ours | 1.61 | 0.58 | +0.45 | 1.66 | 0.82 | +0.72 |
| **b7_blend_b5_fsa_level (selected)** | B | **1.89** | 1.01 | +0.45 | **1.73** | 1.06 | +0.82 |
| b5_planted_x_fsa_share_median | B | 1.92 | 0.91 | +0.55 | 1.75 | 1.03 | +0.82 |
| b1_planted_x_fsa_share | B | 2.18 | 1.06 | +0.31 | 2.09 | 1.07 | +0.47 |
| b2_ridge | B | 2.18 | 1.09 | +0.27 | 2.11 | 1.18 | +0.44 |
| b6_b1_plus_stress | B | 2.19 | 1.07 | +0.26 | 2.12 | 1.15 | +0.44 |
| b0_planted_x_share (simplest) | B | 2.24 | 1.04 | +0.28 | 2.15 | 1.12 | +0.46 |
| b3_gbt_monotone | B | 2.24 | 0.99 | -0.13 | 2.05 | 0.88 | -0.02 |
| b4_daniel_gbt_independent (reference) | B, look-ahead before 2018 | 2.55 | 1.61 | -0.10 | 2.20 | 1.23 | +0.28 |
| persistence (benchmark) | A | 6.86 | 4.01 | +0.19 | 7.35 | 4.11 | +0.67 |

Yearly values: `out/by_year.csv`. State-level predictions: `out/backtest_by_state_year.csv`.

### 3.3 Selection (pre-registered rule; 15 Nov; 2012-2024)

Best = b7 at 1.894%. Its mean gain over b0 is 0.344 points, against 2 SE = 0.188. **Selected: `b7_blend_b5_fsa_level`**
(`out/selection.json`).

### 3.4 Paired 90% bootstrap intervals for the selected b7 at 15 Nov (b7 minus reference, in points; negative = b7 better)

| Period | Reference | State WAPE difference [90% CI] | \|US\| difference [90% CI] |
|---|---|---|---|
| 2012-2024 | NASS November forecast | +0.29 [+0.04, +0.59] | +0.43 [+0.16, +0.70] |
| 2017-2024 | NASS November forecast | +0.08 [-0.10, +0.24] | +0.24 [-0.05, +0.51] |
| 2012-2024 | persistence | -4.96 [-5.78, -4.16] | -3.00 [-4.37, -1.67] |
| 2017-2024 | persistence | -5.62 [-6.60, -4.54] | -3.06 [-4.92, -1.29] |
| 2012-2024 | b0 | -0.34 [-0.50, -0.20] | -0.03 [-0.41, +0.32] |

All candidates against all three references, at all three dates: `out/comparisons.csv`.

### 3.5 Earliness: the selected model at 15 Sep, 15 Oct and 15 Nov (`out/earliness.csv`, `out/comparisons.csv`)

The specification is the same at each date; the inputs are the ones published by that date. NASS's figure is its own
latest grain forecast at that date.

| Period | As-of | b7 state WAPE | b7 \|US\| | NASS state WAPE | NASS \|US\| | b7 - NASS, state [90% CI] |
|---|---|---|---|---|---|---|
| 2012-2024 | 15 Sep | 2.25 | 0.94 | 2.58 | 0.91 | -0.33 [-0.66, +0.01] |
| 2012-2024 | 15 Oct | 1.93 | 0.92 | 1.76 | 0.70 | +0.17 [-0.12, +0.51] |
| 2012-2024 | 15 Nov | 1.89 | 1.01 | 1.61 | 0.58 | +0.29 [+0.04, +0.59] |
| 2017-2024 | 15 Sep | 2.08 | 1.08 | 2.53 | 1.05 | -0.45 [-0.81, -0.11] |
| 2017-2024 | 15 Oct | 1.72 | 1.00 | 1.66 | 0.82 | +0.06 [-0.10, +0.21] |
| 2017-2024 | 15 Nov | 1.73 | 1.06 | 1.66 | 0.82 | +0.08 [-0.10, +0.24] |

### 3.6 What do the NASS inputs add over FSA alone? (post-hoc, not pre-registered, not used for selection)

b7 is the geometric mean of b5 (NASS planted x FSA share) and g3 (FSA grain acres scaled to NASS; this is Tier A's
selected model). `out/posthoc_selected_vs_fsa_only_g3.csv`, b7 minus g3:

| Period | As-of | g3 state WAPE | b7 state WAPE | State difference [90% CI] | \|US\| difference [90% CI] |
|---|---|---|---|---|---|
| 2012-2024 | 15 Nov | 1.94 | 1.89 | -0.04 [-0.11, +0.01] | -0.11 [-0.29, -0.01] |
| 2017-2024 | 15 Nov | 1.76 | 1.73 | -0.03 [-0.05, -0.01] | -0.03 [-0.06, +0.00] |
| 2012-2024 | 15 Oct | 1.99 | 1.93 | -0.05 [-0.18, +0.05] | -0.18 [-0.42, +0.02] |
| 2012-2024 | 15 Sep | 2.04 | 2.25 | +0.21 [-0.01, +0.44] | -0.20 [-0.55, +0.12] |
| 2017-2024 | 15 Sep | 1.75 | 2.08 | +0.33 [+0.06, +0.63] | +0.16 [-0.00, +0.36] |

So the current-year NASS inputs add a few hundredths of a point at 15 Oct and 15 Nov, and they hurt at 15 Sep. At
15 Sep NASS's planted figure is usually still June's, and the FSA share is not yet settled. Most of the skill comes
from the FSA intended-use certifications.

### 3.7 The fitted candidates

- **b2 (ridge)** is the same as b1 to the second decimal (2.180% vs 2.180%). In the latest fit, the raw coefficient on
  `d_fsa_share` is 0.62, so less than the full FSA change is passed through. The stress coefficients are small.
  Sign check at 15 Nov (`out/fitted_sign_check.csv`, 10 backtest fits each):
  - `d_fsa_share` (+), `d_drought` (-) and `d_poor` (-) had the expected sign in 10 of 10 fits.
  - `yield_shock` had the opposite sign (-) in 10 of 10.
  - `d_loss` had the expected sign in 2 of 10.
  One possible reason, not tested: the model has no intercept. Yields trend up, so `yield_shock` is mostly
  positive, and it may be absorbing b0's average over-prediction (+0.28%).
- **b3 (monotone trees)**: 2.24%, no gain over b0 on 2012-2024. It has the smallest signed US bias (-0.13%), and on
  2017-2024 the best \|US\| among the b-candidates (0.88%).
- **b6 (stress on top of b1)**: 2.19%, no gain over b1. This matches Tier A's g4 finding: drought, condition and
  loss changes add nothing measurable once FSA intended use is known.

### 3.8 b4: Daniel's grain_gbt_independent (reference only)

I re-ran it with his own code and panel and scored it on the same truth: 2.553% / 1.611% on 2012-2024, which equals
his reported 2.553 / 1.61; 2.197% / 1.232% on 2017-2024. It is the weakest model-based candidate on 2012-2024, mostly
because of 2012 (7.98% state, -7.35% US). Its planted input before 2018 is NASS's **final** planted acres (a
look-ahead), so its 2012-2017 numbers are, if anything, flattered. It is not eligible.

### 3.9 2025 (information only, scored once after selection)

b7: **1.66% state WAPE, -1.14% US**. NASS's November forecast: 1.64%, -0.99%. Persistence: 9.23%, -8.69%
(`out/score_2025_information_only.json` / `.csv`). The team's stored 2025 score was not touched.

### 3.10 2026 forecast (as of 15 Nov 2026, b7; `out/forecast_2026.csv`)

**US (41 states): 88.68 M acres of corn for grain, 80% interval 87.26-90.12 M.**

| State | Forecast | 80% interval |
|---|---|---|
| Iowa | 12.78 M | 12.31-13.17 M |
| Illinois | 10.89 M | 10.49-11.22 M |
| Nebraska | 9.61 M | 9.26-9.91 M |
| Minnesota | 8.35 M | 8.04-8.60 M |
| Kansas | 6.52 M | 6.28-6.72 M |
| South Dakota | 5.92 M | 5.70-6.10 M |
| Indiana | 5.12 M | 4.93-5.27 M |
| North Dakota | 4.50 M | 4.33-4.63 M |

All 41 states are in the file. Inputs used:
- NASS planted: 11 Sep 2026 Crop Production (`crop0926_0.txt`).
- FSA: the 5 Nov 2026 file (released 10 Nov) and the 2025 final file (released 12 Jan 2026).
- NASS 2025 finals.

The US totals of the other candidates (`out/forecast_2026_all_candidates.csv`): b0 89.14, b1 89.02, b2 88.65,
b3 88.42, b5 88.66, b6 88.59 M. For context only (not an input): the team report's current grain number,
NASS's November forecast passed through (`data/models/state_forecast_2026.csv`), is 88.51 M.

The state intervals use the q10/q90 of log(actual/pred) within three size classes. The US interval is
+-1.2816 x RMS of the yearly US log errors (RMS 1.26%; the empirical 10%/90% quantiles of the 13 yearly US log
errors are -1.86% / +1.22%). Coverage leaving one year out (`out/intervals.json`): states 0.78 (target 0.80), US
0.77 (13 years).

## 4. Verdict

- **Can we get close to NASS's November forecast without using it? Close, but not equal.**
  - By state, b7 has a mean WAPE of 1.73% on 2017-2024, against NASS's 1.66%. The gap is inside the 90% interval
    (+0.08 [-0.10, +0.24]).
  - On 2012-2024 NASS is clearly better: 1.61% against 1.89% (+0.29 [+0.04, +0.59]).
  - On the US total NASS is better in both periods: \|US\| 0.58% vs 1.01% (2012-2024), 0.82% vs 1.06% (2017-2024).
  - Both have a similar positive US bias (+0.45% on 2012-2024).
- **Earlier is where we win.** At 15 Sep, b7 beats NASS's own September grain forecast by state: 2.25% vs 2.58%
  on 2012-2024, and 2.08% vs 2.53% on 2017-2024 (that interval excludes 0). At 15 Sep, though, the fully
  independent Tier A g3 is better still (2.04% / 1.75%).
- **Why the gap to NASS remains.** At 15 Nov, NASS's forecast already folds in its own harvest survey and FSA data.
  Our planted and FSA-share inputs explain most of the state pattern but not the last 0.1-0.3 points. Trained
  stress models (ridge, monotone trees) add nothing over the ratio estimators: the grain share is set by intended
  use, which FSA already records.
- **Recommendation (my judgement).** If the report must stop passing NASS's grain forecast through, b7 is a
  defensible 15 Nov Tier B grain number, with backtest errors stated as above. Tier A's g3 is nearly as good
  (0.03-0.04 points worse at 15 Nov), fully independent of current-year NASS data, and better at 15 Sep. The extra
  Tier B input (NASS planted acres) buys little.

## 5. Limitations

- **Winner's curse.** Seven eligible candidates; the 2 SE rule only guards against b0. b5 (1.92%) and b7 (1.89%) are
  close. I added b5 and b7 after seeing Tier A's g3 result (disclosed in 1.0). The b7 blend idea is mine; its
  components were pre-registered with it.
- **Early years.** 2012-2014 are b7's worst years (3.47%, 2.36%, 2.44%). In those years the multi-year FSA ratio has
  only one or two years behind it (no usable dated FSA final before 2011).
- **Mild look-aheads**, shared with the NASS and persistence benchmarks:
  - NASS finals as Quick Stats stores them today include later revisions.
  - For the 15 Sep runs, the t-1 revision of 30 Sep is not yet public; this is not corrected.
  - RMA files are today's vintage (they feed only b2, b3 and b6, not b7).
  - Undocumented FSA release dates are assumed to be the data date + 5 days (`kernelag.fsa`).
- **Planted values for 2012-2017** come from my parser of the archived report text. The parser is unit-tested on
  both table layouts and reproduces every 2018-2026 value exactly. The 2012-2017 values have no second source here.
- **2025 FSA input.** The 15 Nov 2025 forecast had only the September 2025 FSA file (the November file was not
  released before 15 Nov). The 2025 information score reflects that.
- **Intervals** rest on 13 backtest years. The US interval covered 10 of 13 years leaving one out.
- **Scope.** Truth is the 41 states with a NASS grain final; the US total is their sum, as the incumbent scores it.
  Silage is out of scope here (see `test_models/ownModels/silage/`).

## 6. Files and how to run

```
.venv/Scripts/python.exe test_models/ownModels/tierB/grain/fetch_reports.py --parse-only   # re-parse the saved reports (no network)
.venv/Scripts/python.exe test_models/ownModels/tierB/grain/run.py                          # backtest, selection, 2026 forecast (~1 min)
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/tierB/grain/test_run.py        # 16 tests
```

Without `--parse-only`, `fetch_reports.py` downloads any report not yet in `data/reports/`. `run.py --score-2025`
refuses to run again because `out/score_2025_information_only.json` exists.

Outputs in `out/`:

| File | What it holds |
|---|---|
| `backtest_by_state_year.csv` | state, year, asof, candidate, pred, actual, method, G_last, tier |
| `by_year.csv`, `summary.csv` | yearly and mean errors |
| `comparisons.csv` | paired 90% bootstrap intervals |
| `selection.json` | the selection rule applied |
| `earliness.csv` | the selected model at each as-of date |
| `posthoc_selected_vs_fsa_only_g3.csv` | b7 against FSA alone (post-hoc) |
| `fitted_weights.csv`, `fitted_sign_check.csv` | fitted coefficients and their signs |
| `inputs_audit.json` | the sources each candidate declares, and input coverage by year |
| `planted_asof_used.csv`, `fsa_files_used.csv` | which planted figure and FSA files each forecast used |
| `reproduction.json` | the benchmark and data checks |
| `intervals.json` | interval method and leave-one-year-out coverage |
| `forecast_2026.csv`, `forecast_2026_all_candidates.csv` | the 2026 forecast |
| `score_2025_information_only.*` | the one 2025 score |
| `preregistration.sha256`, `preregistration_README_snapshot.md` | proof of the pre-registration |
