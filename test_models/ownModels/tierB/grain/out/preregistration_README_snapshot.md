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
