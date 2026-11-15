# Own silage models: state corn-for-silage acres without current-year NASS information

User directive (2026-11-14): "we cant just use their nass forecast., we should have our own models."

The report's silage model (`reversion_only` in `kernelag/state_model.py`) already uses only past NASS finals.
This folder asks whether **current-year evidence that is not NASS's** (FSA farmer certifications, RMA crop
insurance, the US Drought Monitor) improves on it, under a selection rule fixed before any score was computed.

Code: `run.py` (all models, backtest, selection, 2025 information score, 2026 forecast). Tests: `test_run.py`.
Outputs: `out/`. Nothing outside this folder is written.

---

## 1. Pre-registration (written before any score was computed; not edited afterwards)

The text of this section, from the heading above to the end-of-section marker, is hashed into
`out/preregistration.sha256` by `run.py --prereg` before the first backtest run. Later edits to the README
go below the marker only. Any change of method after scoring is listed in section 7 "Deviations".

### 1.1 Independence tiers (enforced in `run.py`)

- **Tier A "independent".** For target crop year t: NASS FINAL state acres for years before t only (history),
  plus current-year non-NASS public data published by the as-of date: FSA crop acreage (farmer certifications),
  RMA crop insurance (insured acres by type, causes of loss), US Drought Monitor, NOAA weather. Forbidden for
  year t: NASS June Acreage or any planted figure, NASS in-season grain or yield forecasts, NASS crop progress and
  condition, NASS silage harvest pace, and anything built from them (for example the `kernelag.state_panel`
  columns `planted_asof`, `grain_asof`, `grain_yield_asof`, `poor_condition`, `mature_wk38`, `silage_pace`).
- **Tier B.** Tier A plus NASS weekly crop condition or progress (never acreage, never yield forecasts).
  Reported separately; never the headline; not eligible for selection.
- **Benchmarks (not ours).** Persistence ("same as last year") and the incumbent `reversion_only` as stored in
  `data/models/state_model_backtest.csv`.

Enforcement: every input has a registry entry (source, tier). Every candidate declares its inputs and
`check_tiers()` refuses a Tier A candidate with a Tier B or forbidden input. NASS acres are read only through an
accessor that raises if asked for a year >= t. FSA files are chosen only through `kernelag.fsa.latest_file` /
`usable_files` (published on or before the as-of date; a crop year's own final file never used in-season), and
the run asserts the publication date of every FSA file it uses.

### 1.2 Data and notation

- t: target crop year; d: as-of date. Primary d = 15 November of t (the incumbent's date). Earliness runs:
  15 September and 15 October of t.
- S(y), G(y), P(y): NASS final state acres for silage harvested, grain harvested, planted for all purposes
  (Quick Stats "YEAR" values in `data/Quickstats Data/*_state_2000_2026.csv`; identical to
  `data/nass/corn_acres_state.csv`, the incumbent's truth, on every overlapping 2013-2025 value, checked).
  Used only for y < t. Truth for scoring = S(t). States: the incumbent's 48 states.
- f(d,t): the latest in-season FSA file of crop year t published by d (`kernelag.fsa.latest_file`;
  publication = documented date, else data date + 5 days). A missing or corrupt month falls back to the latest
  earlier file, never a later one. final(t-1): the FSA final (January) file of crop year t-1.
- F_u(file): FSA field-corn planted acres with intended use u, summed by state (`data/fsa/fsa_corn_state.csv`;
  silage includes Forage). F_all: all intended uses.
- I_sil(y): RMA Summary of Business corn type 026 (Silage) net reported acres, state sum over all plans
  (`data/rma/insured_by_type_corn`; endorsement plans carry zero acres).
- L(y,d): share of insured corn acres with a weather loss in months before the as-of month
  (`kernelag.context.loss_share`, causes drought, heat, irrigation failure, hot wind, hail, wind, frost, freeze).
- D(y,d): mean share of the state's area in drought class D2 or worse on weekly maps from 1 June to the earlier of
  30 September and d (`kernelag.context.drought`). Same window in t and t-1.
- Poor(y,d) (Tier B only): NASS weekly share of corn rated poor or very poor, weeks 30-36
  (`kernelag.context.poor_condition`).
- History variants. **H00** (primary): NASS finals from 2000. **H13**: finals from 2013 only, which is the
  incumbent's panel; used only to reproduce the incumbent exactly on 2017-2024.

### 1.3 Candidates

Shared pieces: `fit_ridge` is `kernelag.state_model.fit_ridge` (pooled over states, weights S(y-1),
standardized features, ridge penalty 1 x mean weight, no intercept, missing feature read as 0). "Expanding
window" means fitted on years before the test year only. A fitted parameter needs at least 3 training years;
with fewer it takes its null value (named per candidate).

| Key | Tier | Inputs | Definition |
|---|---|---|---|
| `s0_persistence` | benchmark | S(t-1) | S(t-1) |
| `s1_reversion_only` | A (history only) | S(t-1..t-4) | S(t-1) x exp(beta x rev), rev = log(S(t-1) / mean(S(t-2), S(t-3), S(t-4))); beta by `fit_ridge` on all state-years y < t (expanding). The incumbent's algorithm, run on H00. `s1_incumbent_H13` is the same on H13 (exact reproduction, 2017-2024 only). |
| `s2_fsa_ratio_highcov` | A | S, FSA silage | Gate: F_sil(final(t-1)) >= 500 acres and F_sil(final(t-1)) / S(t-1) >= 0.75 (coverage of year t-1 only). Gated states: S(t-1) x clip(F_sil(f(d,t)) / F_sil(final(t-1)), 0.5, 2). Other states: s1. No fitted parameter beyond s1. |
| `s3_fsa_residual` | A | S, G, P history; FSA all-corn and grain | P_hat = F_all(f(d,t)) x P(t-1) / F_all(final(t-1)); G_hat = F_grain(f(d,t)) x G(t-1) / F_grain(final(t-1)) (the g1 FSA-ratio grain estimate); R_hat = P_hat - G_hat; R(t-1) = P(t-1) - G(t-1); raw = S(t-1) x clip(R_hat / R(t-1), 0.5, 2), which equals R_hat x [S(t-1) / R(t-1)] (last year's silage share of non-grain acres) when not clipped. Needs G(t-1) published (41 states), positive FSA finals and R(t-1) > 0; otherwise s1. Final: s3 = s1^(1-w) x raw^w, with one pooled w in {0, 0.05, ..., 1} minimizing sum abs(pred - S) over training state-years 2012 <= y < t at the same as-of date (expanding; null w = 0). |
| `s4_reversion_plus_switch` | A | S history; drought; RMA loss; FSA silage; RMA silage acres | s1 x exp(b . x), x = [D(t,d) - D(t-1,d); L(t,d) - L(t-1,d); clip(log(F_sil(f(d,t)) / F_sil(final(t-1))), -log 2, log 2); clip(log(I_sil(t) / I_sil(t-1)), -log 2, log 2)]. A log ratio is missing (read as 0) if its denominator is under 500 acres. b by `fit_ridge` on target log(S(y) / s1(y)), s1(y) out-of-sample, training years 2005 <= y < t (expanding; null b = 0). |
| `s5_fsa_silage_share` | A | S, FSA silage and all-corn | Where F_sil(final(t-1)) >= 500: S(t-1) x clip([F_sil / F_all](f(d,t)) / [F_sil / F_all](final(t-1)), 0.5, 2). Other states: s1. Nothing fitted beyond s1. |
| `s6_highcov_plus_switch` | A | union of s2 and s4 | s2's gated states take s2's FSA ratio; all other states take s4. |
| `b4_switch_plus_condition` | **B** | s4 inputs + Poor | s4 with a fifth feature Poor(t,d) - Poor(t-1,d). Reported separately; not eligible. |

Diagnostics, not candidates and not eligible: `d3_raw_residual` (s3 with w = 1); `d_oracle_final_residual`
= S(t-1) x R(t) / R(t-1) with R(t) from NASS's year-t FINAL planted and grain (uses forbidden year-t NASS data;
reported only as the ceiling the research note computed at 8.9%, to show how close s3's FSA residual gets).

### 1.4 Backtest and metrics

- Test years: 2012-2024 (13 years; FSA in-season files exist from crop year 2011 and the first prior final is
  2011's), primary. 2017-2024 reported separately for comparison with the team's numbers. 2025 is never used for
  fitting, selection or tuning in the backtest.
- Per year: state WAPE = sum over states abs(pred - actual) / sum actual (48 states, or all with truth and
  S(t-1)); US error = (sum pred - sum actual) / sum actual. Summary per candidate and period: mean state WAPE,
  mean abs(US error), mean signed US error.
- Comparisons for every candidate: paired yearly differences against (a) the incumbent (`s1_incumbent_H13` on
  2017-2024; `s1_reversion_only` H00 on 2012-2024, since the incumbent cannot be run before 2017), (b)
  `s0_persistence`, (c) the simplest own candidate `s1_reversion_only`. 90% intervals: 10,000 bootstrap resamples
  of years with replacement (seed 20261114), percentile interval of the mean difference.

### 1.5 Selection rule (mechanical)

1. Eligible: s1, s2, s3, s4, s5, s6 (Tier A, history H00, as-of 15 November).
2. Period 2012-2024. For each eligible c other than s1: d_y = WAPE(c, y) - WAPE(s1, y); dbar = mean d_y;
   SE = sd(d_y, ddof 1) / sqrt(13).
3. c qualifies if dbar + 2 SE < 0 (better than s1 by more than two standard errors of the paired differences).
4. Selected: the qualifying candidate with the lowest mean WAPE (ties: order s2, s5, s3, s4, s6). If none
   qualifies, the selected model is s1.
5. The same rule applied on 2017-2024 is reported for information and does not change the choice.

### 1.6 After selection

- Earliness: every candidate rerun as of 15 September and 15 October (FSA, drought and loss inputs at those
  dates, fitted parameters refitted on training years at the same date).
- 2025: one information-only score of the selected candidate, as of 15 November 2025 (latest FSA file then: 2 Sep
  2025, because the October and November 2025 files were never released), fitted on years up to 2024, written to
  `out/score_2025_information_only.csv`. `data/models/state_score_2025.*` is never touched.
- 2026: forecast of the selected candidate by state and US as of 15 November 2026 (FSA file of 5 Nov 2026,
  published 10 Nov), fitted on years up to 2025 (expanding window, as in the backtest). 80% intervals: state =
  10th and 90th percentiles of log(actual / predicted) in three size classes of S(t-1) from the 2012-2024
  backtest (`kernelag.state_model.error_quantiles`); US = 10th and 90th percentiles of the 13 yearly US log
  errors. Leave-one-year-out coverage of the state intervals is reported.

Known look-ahead (accepted, stated): the RMA files are today's vintage (insured acres and losses for past years
are more complete than they were that November); FSA publication dates before 2025 are assumed (data date + 5
days).

<!-- END OF PRE-REGISTRATION -->

Everything below was written after the scores were computed. `run.py` checks the hash of section 1 on every run
and records the result in `out/run.json` (`"unchanged": true`).

## 2. Reproduction (done before any new candidate was scored)

`run.py` rebuilds the incumbent from NASS finals 2013-2025 (history H13) with `kernelag.state_model.fit_ridge` and
compares every year with `data/models/state_model_backtest.csv` (`out/reproduction.json`). The run stops if
either check fails.

| Model | Years | Matches the stored backtest | Mean state WAPE, mine / stored |
|---|---|---|---|
| `reversion_only` (incumbent) | 2017-2024 | all 8 years, state WAPE and US error, to 2 decimals | 13.12 / 13.12 |
| persistence (`same_as_last_year`) | 2017-2024 | all 8 years, to 2 decimals | 14.53 / 14.53 |

The NASS finals used here (Quick Stats 2000-2025) are identical to the incumbent's truth file on every overlapping
value. With history H00 (finals from 2000), the same algorithm fits its one coefficient on more years. It then
scores 13.01% on 2017-2024 (`s1_reversion_only`), against 13.12% on H13.

## 3. Backtest results, as of 15 November

State WAPE = sum of abs(pred - actual) / sum of actual over the 48 states, averaged over years. US = error of the
48-state sum, as a percent of the actual. All numbers are from `out/summary.csv`.

| Candidate | Tier | WAPE 2012-24 | abs US 2012-24 | signed US 2012-24 | WAPE 2017-24 | abs US 2017-24 | signed US 2017-24 |
|---|---|---|---|---|---|---|---|
| `s0_persistence` | benchmark | 15.84 | 5.76 | +0.02 | 14.53 | 4.08 | +0.11 |
| `s1_incumbent_H13` (report model) | benchmark | n/a | n/a | n/a | 13.12 | 3.90 | -0.98 |
| `s1_reversion_only` | A (history only) | 14.11 | 4.85 | -1.71 | 13.01 | 3.73 | -0.99 |
| `s2_fsa_ratio_highcov` | A | 14.33 | 5.07 | -2.08 | 13.03 | 4.12 | -1.45 |
| **`s3_fsa_residual`** | **A** | **13.72** | 4.96 | -1.65 | **12.52** | 4.00 | -0.82 |
| `s4_reversion_plus_switch` | A | 14.51 | 5.39 | -1.82 | 14.15 | 4.17 | -0.32 |
| `s5_fsa_silage_share` | A | 20.03 | 8.23 | +2.30 | 19.72 | 8.22 | +3.32 |
| `s6_highcov_plus_switch` | A | 14.48 | 5.29 | -2.25 | 13.97 | 4.14 | -0.89 |
| `b4_switch_plus_condition` | B (not eligible) | 14.32 | 5.15 | -1.86 | 13.92 | 3.74 | -0.37 |
| `d3_raw_residual` (s3 with w = 1) | diagnostic | 16.54 | 7.50 | -0.20 | 15.11 | 5.78 | +0.21 |
| `d_oracle_final_residual` | diagnostic, forbidden inputs | 8.44 | 2.61 | +1.04 | 9.68 | 3.40 | +2.36 |

Paired comparisons for `s3_fsa_residual`: mean yearly difference in points, with a 90% bootstrap interval over
years. Negative means s3 is better. Source: `out/comparisons.csv`, which has every candidate.

| Period | Against | State WAPE difference [90% CI] | Years better / worse / tied | abs US difference [90% CI] |
|---|---|---|---|---|
| 2017-2024 | (a) incumbent `s1_incumbent_H13` | -0.60 [-0.82, -0.37] | 7 / 1 / 0 | +0.10 [-0.58, +0.83] |
| 2017-2024 | (b) persistence | -2.01 [-2.80, -1.17] | 7 / 1 / 0 | -0.08 [-0.71, +0.55] |
| 2017-2024 | (c) `s1_reversion_only` | -0.49 [-0.74, -0.25] | 7 / 1 / 0 | +0.27 [-0.49, +1.06] |
| 2012-2024 | (a) = (c) `s1_reversion_only` | -0.39 [-0.59, -0.20] | 9 / 1 / 3 | +0.11 [-0.38, +0.64] |
| 2012-2024 | (b) persistence | -2.12 [-3.32, -1.07] | 11 / 2 / 0 | -0.80 [-3.21, +0.97] |

The 3 tied years are 2012-2014. There s3 equals s1 exactly, because w needs 3 training years. Before 2017 the
incumbent cannot be run on its own panel, so comparator (a) is s1 on H00.

The other Tier A candidates against `s1_reversion_only` (2012-2024, WAPE points): s2 +0.23 [-0.17, +0.61], s4
+0.40 [-0.96, +1.61], s5 +5.92 [+4.32, +7.39], s6 +0.37 [-0.85, +1.49]. The Tier B b4 scores +0.21 [-1.10, +1.40].

State WAPE by year (%):

| Year | persistence | incumbent H13 | s1 H00 | s2 | **s3** | s4 | raw residual | oracle |
|---|---|---|---|---|---|---|---|---|
| 2012 | 23.32 | | 24.21 | 24.87 | 24.21 | 17.39 | 22.20 | 9.42 |
| 2013 | 25.35 | | 16.05 | 16.55 | 16.05 | 16.48 | 25.14 | 5.57 |
| 2014 | 14.15 | | 12.73 | 14.57 | 12.73 | 15.42 | 18.05 | 7.12 |
| 2015 | 13.60 | | 13.19 | 14.16 | 12.19 | 13.30 | 13.53 | 5.59 |
| 2016 | 13.23 | | 13.12 | 11.95 | 12.98 | 12.83 | 15.18 | 4.62 |
| 2017 | 12.33 | 12.33 | 12.17 | 12.23 | 11.25 | 14.00 | 11.70 | 4.14 |
| 2018 | 20.25 | 18.82 | 17.88 | 18.83 | 17.95 | 16.81 | 19.34 | 8.09 |
| 2019 | 17.20 | 14.83 | 14.58 | 14.70 | 14.49 | 15.65 | 21.70 | 9.93 |
| 2020 | 12.03 | 9.47 | 9.59 | 9.50 | 8.40 | 10.62 | 13.77 | 11.87 |
| 2021 | 14.43 | 12.35 | 12.31 | 12.66 | 11.72 | 10.04 | 11.98 | 10.68 |
| 2022 | 14.16 | 15.38 | 15.48 | 13.86 | 14.78 | 18.20 | 13.26 | 18.48 |
| 2023 | 13.53 | 9.80 | 9.99 | 10.02 | 9.90 | 15.52 | 16.06 | 8.11 |
| 2024 | 12.34 | 12.00 | 12.11 | 12.43 | 11.70 | 12.36 | 13.07 | 6.11 |

## 4. Selection (rule 1.5 applied mechanically; `out/selection.json`)

| Candidate | Mean WAPE 2012-24 | Mean difference vs s1 | SE | Difference + 2 SE | Qualifies |
|---|---|---|---|---|---|
| s2_fsa_ratio_highcov | 14.33 | +0.23 | 0.25 | +0.72 | no |
| s5_fsa_silage_share | 20.03 | +5.92 | 0.96 | +7.84 | no |
| **s3_fsa_residual** | **13.72** | **-0.39** | **0.12** | **-0.14** | **yes** |
| s4_reversion_plus_switch | 14.51 | +0.40 | 0.81 | +2.02 | no |
| s6_highcov_plus_switch | 14.48 | +0.37 | 0.73 | +1.84 | no |

**Selected: `s3_fsa_residual`** (s1 mean 14.11%). The same rule on 2017-2024, for information only, gives the same
result: s3 is the only candidate that qualifies (difference + 2 SE = -0.18).

## 5. What s3 does, and how close it gets to the oracle

s3 = s1^(1-w) x raw^w. The fitted weight w is 0 in 2012-2014 (fewer than 3 training years), 0.20 in 2015, 0.30
in 2023 and 0.25 in every other year through 2026 (`out/fitted_params.csv`). So s3 moves the incumbent's
prediction a quarter of the way (in logs) toward the FSA non-grain residual estimate.

The oracle uses NASS's final planted and grain acres of the target year itself. Those numbers come out the same
day as the silage answer, so the oracle is a ceiling, not a model. It scores 8.44% (2012-2024), 9.68% (2017-2024)
and 10.86% (2019-2024). The research note's 8.9% is for 2019-2025 against NASS's first January estimates; here the
truth is the latest revised value, and the years differ.

- s3 closes 0.39 of the 5.67 points between s1 and the oracle on 2012-2024 (7%), and 0.49 of 3.34 points on
  2017-2024 (15%).
- The FSA residual on its own (`d3_raw_residual`, w = 1) is worse than persistence: 16.54% against 15.84%.

Why FSA gets so little of the oracle's gain (`out/s3_residual_diagnostics.csv`, the 41 states with a NASS grain
estimate, means over 2012-2024):

- FSA certifications scaled by last year's NASS/FSA ratio get planted acres within 0.87% (sum of absolute errors as
  a share of planted acres) and grain acres within 2.15%.
- The non-grain residual is small: 7.9 million of 91.4 million planted acres (8.6%). A 2.15% grain error equals
  22.4% of the residual. The FSA residual misses NASS's final residual by 22.2% (pooled over 2012-2024), no better
  than last year's residual (21.9%).
- The grain error is a timing problem, not an FSA counting problem. Intended use is declared at the 15 July
  acreage report. Acres certified as grain that are later chopped, grazed or abandoned stay "grain" in FSA
  (research note, section 2.4). That late switch is exactly what the oracle knows and FSA cannot see.
- The blend still helps, because the residual's errors are only partly correlated with the reversion model's
  errors. With w = 0.25, s3 is better than s1 in every region (`out/by_region.csv`, pooled WAPE 2012-2024):
  dairy states 8.46% vs 8.86%, Plains 21.68% vs 22.12%, Corn Belt 17.41% vs 17.69%, others 11.51% vs 11.92%.
  The oracle's own error is lowest in dairy states (1.82%), where silage is most of the residual, and highest in
  the Plains (16.89%), where the residual mixes silage with abandoned acres.

## 6. Earliness, 2025 information score, 2026 forecast

**Earliness** (every candidate rerun with the FSA, drought and loss inputs public on each date, and w refitted at
that date; `out/summary.csv`, column `asof_key`):

| As of | s3 WAPE 2012-24 | s3 WAPE 2017-24 | s3 abs US 2012-24 | s1 WAPE 2012-24 / 2017-24 | FSA file used |
|---|---|---|---|---|---|
| 15 September | 13.81 | 12.64 | 5.01 | 14.11 / 13.01 | September files (August in 2012: September file corrupt) |
| 15 October | 13.79 | 12.61 | 5.01 | 14.11 / 13.01 | October files (September in 2020 and 2021) |
| 15 November | 13.72 | 12.52 | 4.96 | 14.11 / 13.01 | November files (October in 2015; September in 2025) |

Almost all of s3's gain is there by 15 September, two months before the November date. The FSA silage-ratio
candidates lose more when moved earlier (s2: 14.75%, s6: 14.86% at 15 September).

**2025, information only** (`out/score_2025_information_only.csv` and `.json`). Computed once, after selection,
fitted on years up to 2024. The FSA file is the one with data as of 2 September 2025, because the October and
November 2025 files were never released.

| 2025 | State WAPE | US error |
|---|---|---|
| s3_fsa_residual | 14.32% | +4.04% |
| persistence | 13.96% | +0.32% |
| incumbent, stored score (`data/models/state_score_2025.json`, not modified) | 14.14% | +3.06% |

s3 did not beat persistence or the incumbent in 2025. 81% of states fell inside its 80% interval. The largest
misses were overpredictions in Iowa (+102,000 acres), Kansas (+94,000), North Dakota (+82,000), South Dakota
(+81,000) and Nebraska (+76,000), and an underprediction in Wisconsin (-91,000).

**2026 forecast** (`out/forecast_2026.csv`; as of 15 November 2026; FSA file with data as of 5 Nov 2026, published
10 Nov, against the 2025 final file; fitted on years up to 2025). 80% intervals: state intervals from the
size-class quantiles of the 2012-2024 backtest log errors; the US interval from the 10th and 90th percentiles of
the 13 yearly US log errors. Leave-one-year-out coverage of the state intervals: 0.79 at 80%, 0.89 at 90%.

| | 2026 forecast | 80% interval | 2025 NASS |
|---|---|---|---|
| **US (sum of 48 states)** | **6,297,900** | 6,019,900 - 6,796,600 | 6,187,000 |
| Wisconsin | 836,400 | 675,700 - 1,088,800 | 885,000 |
| New York | 476,400 | 384,900 - 620,200 | 495,000 |
| South Dakota | 426,900 | 345,000 - 555,800 | 390,000 |
| Minnesota | 373,300 | 301,600 - 486,000 | 360,000 |
| California | 354,100 | 286,100 - 461,000 | 370,000 |
| Michigan | 336,400 | 271,800 - 438,000 | 340,000 |
| Pennsylvania | 326,100 | 263,500 - 424,500 | 315,000 |
| Iowa | 298,200 | 240,900 - 388,200 | 250,000 |
| Kansas | 278,300 | 224,900 - 362,300 | 230,000 |
| Nebraska | 268,100 | 216,600 - 349,000 | 220,000 |
| Idaho | 260,700 | 210,700 - 339,400 | 280,000 |
| Texas | 238,900 | 193,000 - 311,000 | 245,000 |
| Colorado | 198,900 | 160,700 - 259,000 | 200,000 |
| North Dakota | 193,400 | 156,300 - 251,800 | 170,000 |

US totals of the other candidates for 2026 (`out/forecast_2026_all_candidates.csv`): s1 6,333,200; s2 6,392,100;
s4 6,365,300; s5 6,332,500; s6 6,438,200; persistence 6,187,000; Tier B b4 6,463,800.

## 7. Deviations and post-hoc checks

**Deviations from the pre-registration: none in method.** Two output fixes were made after the first scored run.
Neither changed any prediction, score or selection value (`out/selection.json` is identical to the fourth decimal):

1. `comparisons.csv` listed 2012-2024 rows twice, because comparator (a) and comparator (c) are the same model
   there. The duplicates were removed.
2. `years_better` counted floating-point ties as wins in 2012-2014, where s3 equals s1 because w = 0. Ties are now
   counted separately, and s3 is set to s1 exactly when w = 0.

Post-hoc checks, added after the first scored run. None of them feeds the selection:

- **FSA publication lag of 10 days instead of 5** (`out/sensitivity_publication_lag10.csv`). Only two file choices
  change: at 15 September 2018 the August file replaces the September file, and at 15 November 2021 the September
  file replaces the November file. s3 is unchanged on 2012-2024 (13.72%) and 12.52% becomes 12.53% on 2017-2024.
- **Against the team's stored silage models that read NASS's year-t acreage or yield** (`kernelag.state_model`
  feature sets; for us those inputs are forbidden; `out/reference_nass_input_models.csv`, 2017-2024):

  | Stored model | Its WAPE | s3 minus it [90% CI] | s3 better in |
  |---|---|---|---|
  | `nass_acres` | 13.04 | -0.52 [-0.78, -0.22] | 7 of 8 years |
  | `stress` | 13.82 | -1.29 [-2.85, +0.25] | 4 of 8 |
  | `all_public` | 14.53 | -2.01 [-3.46, -0.57] | 6 of 8 |

  `nass_acres` adds NASS's planted and grain-forecast changes to the reversion model. On the US total it is
  slightly better than s3: 3.87% against 4.00%.
- **By region:** see section 5.

## 8. Verdict

- **Silage has no NASS forecast to replace.** NASS publishes no silage number before January, and the report's
  silage model (`reversion_only`) already uses only past NASS finals. The real question was whether current-year
  evidence from outside NASS adds anything.
- **It adds a little, through one route: s3.** s3 blends the FSA non-grain residual into the reversion model at
  w = 0.25. On 2017-2024 it lowers state error from 13.12% (incumbent) to 12.52%: -0.60 points, 90% CI -0.82 to
  -0.37, better in 7 of 8 years. On 2012-2024 it goes from 14.11% to 13.72% (-0.39 [-0.59, -0.20]). It passes the
  pre-registered two-standard-error rule, its gain is there by 15 September, and it beats the team's model that
  reads NASS's own current-year acreage (`nass_acres`, 13.04%) on state error.
- **It does not improve the US total.** Mean abs US error is 4.00% against the incumbent's 3.90% (2017-2024; the
  CI includes zero). In 2025 (information only) it lost to both persistence and the incumbent.
- **The other routes do not help.** FSA intended-use silage ratios (s2, s5), drought and RMA switch signals (s4,
  s6) and NASS crop condition (b4, Tier B) do not beat the history-only model. s5 is far worse (20%).
- **Most of the gap to the oracle remains** (8.4% on 2012-2024). FSA records July intentions, not harvest fate,
  so it cannot see a late switch from grain to silage. Closing the gap needs a harvest-fate signal, which is what
  the project's field-level satellite work aims at.
- **Suggestion for the report owner** (not done here; this folder edits nothing else): `s3_fsa_residual` is a
  Tier A candidate to replace `reversion_only` for state silage. The gain is modest but steady, and the method
  needs nothing from NASS's current year.

## 9. Limitations

- FSA publication dates before 2025 are assumed (data date + 5 days). The 10-day check above changes almost
  nothing.
- The NASS history values are today's revised finals from Quick Stats, not the values public in November of each
  year. Truth is the latest revised value, not the first January estimate. The incumbent's backtest has the same
  property.
- The RMA files are today's vintage. This affects s4, s6 and b4, not s3.
- s3 needs a NASS grain estimate for year t-1. 41 of the 48 states have one. The 7 others (Connecticut, Maine,
  Massachusetts, Nevada, New Hampshire, Rhode Island, Vermont; about 0.17 million acres) fall back to s1.
- The backtest has only 13 (or 8) test years. The two-standard-error rule treats years as exchangeable. 2012, a
  drought year, dominates the US error (persistence -20%).
- The US 80% interval comes from 13 yearly errors and is coarse. No 90% US interval is given.
- FSA files that are missing or corrupt: September 2012, November 2015 and October 2020 are truncated downloads;
  October 2021 and October-November 2025 were never published; August 2024 was not downloaded. Each forecast falls
  back to the latest earlier file, as the as-of rule requires.
- The oracle and the residual diagnostics use NASS finals of the target year. They measure the models; they are
  not models.

## 10. Files and how to run

From the repository root:

```bash
.venv/Scripts/python.exe test_models/ownModels/silage/run.py               # about 1 minute; rewrites out/
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/silage/test_run.py
.venv/Scripts/python.exe -m ruff check test_models/ownModels/silage/
```

`--score-2025` writes `out/score_2025_information_only.*` once and refuses to overwrite them. It was run once,
after selection.

| File | Content |
|---|---|
| `out/backtest_by_state_year.csv` | state, year, asof, candidate, pred, actual (+ asof_key, last year's acres), 2012-2024, three as-of dates |
| `out/by_year.csv`, `out/summary.csv` | state WAPE and US error per year; means per candidate, period and as-of date |
| `out/comparisons.csv` | paired-year differences with 90% bootstrap intervals against (a), (b) and (c) |
| `out/selection.json` | the selection rule's numbers (primary 2012-2024; 2017-2024 for information) |
| `out/reproduction.json` | incumbent and persistence, year by year, against the stored backtest |
| `out/fitted_params.csv` | per test year and as-of date: s1 beta, s3 w, s4/b4 ridge weights, s2 gated states |
| `out/inputs_used.csv` | the FSA files used for every year and as-of date, with data and publication dates |
| `out/s3_residual_diagnostics.csv`, `out/by_region.csv` | why s3 is far from the oracle; errors by region |
| `out/forecast_2026.csv`, `out/forecast_2026_all_candidates.csv` | 2026 forecast of s3 with intervals; all candidates |
| `out/score_2025_information_only.*` | the one-time 2025 information score |
| `out/sensitivity_publication_lag10*.csv`, `out/reference_nass_input_models.csv` | post-hoc checks |
| `out/preregistration.sha256`, `out/run.json` | pre-registration hash; run metadata and caveats |
