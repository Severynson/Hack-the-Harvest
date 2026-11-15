# Grain variants: can a Tier A grain model close A-G3's gap to NASS, and do better in August and September?

Owner key: `grain_variants`. Folder: `test_models/variations/grain_variants/`. Code: `run.py`. Outputs: `out/`.
Nothing outside this folder is written. Nothing is pushed or committed.

## 1. Pre-registration

Written 2026-11-15T09:21Z, before any candidate below was scored. Hash of this section (from the line
`## 1. Pre-registration` to the line `## End of pre-registration`): `out/preregistration.sha256`; a copy of the README
as it stood then: `out/preregistration_README_snapshot.md`.

What had been seen before writing: the scores of A-G3, B-G7 and NASS's forecast in
`test_models/ownModels/monthly/README.md` (including A-G3's documented positive signed US error, +0.64 to +0.85 % at
15 Sep to 15 Dec on 2017-2024), and the definitions of the FSA columns. Definition check (not a score):
`planted_and_failed_acres` = `planted_acres` + `failed_acres` in all 16,233 state rows that have the column (largest
gap 0.01 acre), so FSA `planted_acres`, A-G3's base, already excludes failed acres, and prevented acres were never
planted. g6 and g7 below therefore subtract acres that are not inside A-G3's base; they are kept exactly as the
workflow specified them and their effect is that the base moves with the year's failed (and prevented) acres relative
to the three reference years. Candidate g12 was motivated by the documented signed bias; it is fitted
expanding-window, so every year's correction uses earlier years only, but its choice was not blind.

### 1.1 Base, dates, years, truth

- **A-G3** = `g3_fsa_ratio_multi` of `test_models/ownModels/grain/run.py`: FSA grain-intended planted acres of the
  newest FSA file published by the date x the median over k = 1..3 of NASS final grain(t-k) / FSA grain-intended
  planted in the final file of t-k; guard: multiplier outside (0.25, 4) or no FSA acres -> last year's NASS final;
  no current-year file -> last year's NASS final for every state (fallback).
- It is run through the monthly harness (`test_models/ownModels/monthly/run.py`, imported unchanged: `load_modules`,
  `patch_asof`, `nass_inseason_with_june_2013`, `run_grain_a`, `run_grain_b`, `score`, `paired_ci`) with the
  corrected FSA publication dates (`kernelag.fsa.usable_files` / `latest_file`). Before any candidate is scored, A-G3,
  B-G7 and NASS predictions are checked to equal `monthly/out/monthly_by_state_year.csv` (stored at 0.1 acre).
- Dates: the 15th of Aug, Sep, Oct, Nov (headline) and Dec; 15 Jul is reported for completeness (no FSA file exists
  by then in any year, so every Tier A candidate equals A-G3's fallback there). Years 2012-2024. 2025 is never scored
  and never used to fit or select anything. Maryland is not used.
- Truth: NASS final grain acres of the 41 states with this year's and last year's final (`grain_run.truth`, the
  incumbent's values, checked against `data/nass/corn_acres_state.csv` by `grain_run.load_finals`).
- Candidates use the same state set, the same FSA files, the same guard and the same fallback as A-G3 unless stated.
  "FSA states" = states where A-G3 itself used FSA (method `fsa`) in that year and date.

### 1.2 Candidates

| Key | Tier | Definition |
|---|---|---|
| g6_net_failed | A | base = FSA grain-intended planted - grain-intended failed acres (failed NaN -> 0), in the current file and in each reference final file; pred = base(current) x median_k NASS(t-k) / base(final t-k); A-G3's guard |
| g7_net_failed_prevented | A | as g6 with base = planted - failed - prevented (grain intended use; NaN -> 0) |
| g8_vintage_growth | A | only when the newest file is an Aug or Sep vintage (label starts with `aug` / `sep`): FSA grain(current) x growth x A-G3's multiplier; growth(state) = median over k = 1..3 of FSA grain in the Nov-vintage file of t-k / FSA grain in the t-k file of the same vintage month whose data date is closest to the current file's data date moved back k years (ties -> later file); a k with either file missing is skipped; no k -> growth 1; A-G3's guard on growth x multiplier. Any other vintage, or no current file: = A-G3 |
| g9_national_reconciliation | A | A-G3's FSA states scaled by one factor so that their sum = their FSA grain sum x median_k [sum NASS(t-k) / sum FSA grain final(t-k)] over the same states (each k on states with both values); guard-fallback states unchanged; no current file: = A-G3 |
| g10_geo_blend_g3_b7 | **B** | sqrt(A-G3 x B-G7) by state; B-G7 = `b7_blend_b5_fsa_level` from `run_grain_b` (uses NASS's in-season planted acres of year t). Tier B: it cannot replace A-G3; it is compared with A-G3, with B-G7 and with NASS |
| g11_drought_abandonment | A | A-G3 x clip(1 - k x dD, 0.8, 1.2) on FSA states; D = `kernelag.context.drought` (mean Jun-Sep weekly share of the state in D2 "severe" or worse, maps dated on or before the date); dD = D(t) - mean of D(t-1..t-3) at the same date (missing -> 0). k fitted expanding-window per date: weighted least squares of r = actual / A-G3 - 1 on -dD, no intercept, weights = last year's NASS final, rows = FSA states of years 2012..t-1; k = max(0, fit); fewer than 3 training years -> k = 0 |
| g12_us_bias_corrected | A | A-G3 x exp(-b) on FSA states; b = median over years y in 2012..t-1 that had a current-year FSA file at the same date of log(A-G3 US total / NASS US total) (US = sum of the 41 scored states); fewer than 3 such years -> b = 0 |
| g13_vintage_matched_ratio | A | FSA grain(current) x median_k NASS(t-k) / FSA grain(file of t-k with the data date closest to the current file's data date moved back k years, any vintage including final; ties -> later); A-G3's guard; no current file: = A-G3 |

Benchmarks scored beside them: A-G3, B-G7 (Tier B), NASS's latest forecast published by the date (`nass_latest`,
not independent) and last year's final (`g0_persistence`).

### 1.3 Metrics

Per candidate, date and period (2012-2024 for selection, 2017-2024 reported): mean over years of state WAPE
(sum of absolute state misses / true total, %), mean |US error| %, mean signed US error %, worst year. Paired by year
against A-G3 and against NASS at every date: mean difference, SE = sd(ddof 1) / sqrt(n years), mean + 2 SE, mean + 3 SE
(a stricter bar for the multiplicity below), 90% bootstrap interval (10,000 resamples of years, seed 20261114, the
harness's method) and years better. Tier B g10 also against B-G7.

### 1.4 Decision rule

- A Tier A candidate **replaces A-G3** if, on 2012-2024 at 15 Nov, (state WAPE candidate - A-G3) has mean + 2 SE < 0
  **and** its mean |US error| is not worse than A-G3's by more than 0.10 points. If several pass, the lowest mean state
  WAPE wins.
- **Best early-season candidate:** the same rule applied separately at 15 Aug and at 15 Sep (2012-2024); the passing
  candidate with the lowest mean state WAPE at that date. Reported separately from the 15 Nov choice.
- g10 (Tier B) is judged by the same rule against B-G7 and reported as a Tier B option, never as an A-G3 replacement.
- Multiplicity: 7 Tier A candidates at 3 decision dates. Whether a passing candidate also clears mean + 3 SE < 0 is
  reported. No candidate, parameter or rule is changed after scoring; anything added later is labelled post hoc and
  cannot be selected.
- If nothing passes, A-G3 stays and that is the result.

### 1.5 2026 forecast

On 15 Nov 2026 (the 5 Nov 2026 FSA file, published 10 Nov 2026) for A-G3 and every Tier A candidate, with the
recommended ones marked; g10 too, labelled Tier B. Fitted parameters (g11's k, g12's b) are frozen at their values
fitted on 2012-2024; A-G3's ratio uses the 2023-2025 finals as A-G3 does. No 2025 outcome enters any fit.

## End of pre-registration

## 2. Results of the pre-registered candidates

Run 2026-11-15 (`run.py`, about 50 s for the whole backtest). Cells are **state WAPE % / mean |US error| %**, lower is
better. 41 states, NASS final truth. "(3 F)": three years with no current-year FSA file by the date (every Tier A
candidate then equals last year's final): 15 Aug 2022, 2023, 2024.

### 2.1 Decision (README 1.4 rule, 2012-2024)

| Date | Tier A candidate that replaces A-G3 | Why |
|---|---|---|
| **15 Nov** | **g9_national_reconciliation** | state WAPE 1.88 vs 1.94: diff -0.060, mean + 2 SE = **-0.005** < 0; \|US\| 1.04 vs 1.11 (-0.08, better); better in 10 of 13 years. It does **not** clear the stricter mean + 3 SE bar (+0.022) |
| 15 Sep | none | closest: g9 (mean + 2 SE = +0.003), g11 (+0.024), g8 (+0.089) |
| 15 Aug | none | closest: g9 (+0.040), g6 (+0.065); no candidate improves on A-G3 by more than 0.03 point |
| Tier B (g10 vs B-G7) | none at any date | g10 is worse than B-G7 on the state error at 15 Nov (+0.012) and 15 Aug (+0.361) |

So under the pre-registered rule **g9 replaces A-G3 as the Tier A grain model at 15 Nov**, but the margin is thin:
dropping any one year, the rule still passes in 11 of 13 cases and fails without 2014 (+0.003) or without 2019
(+0.005). The gain is small (0.06 point of state WAPE, 0.08 point of US error) and largest in 2024 (1.51 -> 1.16).
g9 also passes the same test at 15 Oct and 15 Dec (mean + 2 SE -0.001 and -0.006); those dates were not decision
dates. **No early-season (Aug/Sep) candidate passes.**

### 2.2 Every candidate at every date

**2012-2024 (selection period)**

| Model | Tier | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec | Avg Aug-Dec |
|---|---|---|---|---|---|---|---|
| A-G3 g3_fsa_ratio_multi (incumbent) | A | 4.14 / 3.28 (3 F) | 2.29 / 1.43 | 2.00 / 1.15 | 1.94 / 1.11 | 1.92 / 1.10 | 2.46 / 1.61 |
| g6_net_failed | A | 4.14 / 3.23 | 2.34 / 1.47 | 2.05 / 1.18 | 2.00 / 1.14 | 1.98 / 1.13 | 2.50 / 1.63 |
| g7_net_failed_prevented | A | 6.44 / 5.21 | 5.24 / 3.82 | 5.07 / 3.54 | 5.01 / 3.47 | 4.99 / 3.44 | 5.35 / 3.89 |
| g8_vintage_growth | A | 4.11 / 3.18 | 2.20 / 1.30 | 2.00 / 1.17 | 1.94 / 1.13 | 1.92 / 1.10 | 2.43 / 1.58 |
| **g9_national_reconciliation** | A | 4.13 / 3.26 | 2.23 / 1.36 | **1.94 / 1.07** | **1.88 / 1.04** | **1.86 / 1.02** | 2.41 / 1.55 |
| g11_drought_abandonment | A | 4.13 / 3.27 | 2.22 / 1.27 | 2.01 / 1.14 | 1.95 / 1.11 | 1.92 / 1.08 | 2.44 / 1.57 |
| g12_us_bias_corrected | A | 4.53 / 3.77 | 2.67 / 1.83 | 2.19 / 1.38 | 2.03 / 1.23 | 2.00 / 1.20 | 2.69 / 1.88 |
| g13_vintage_matched_ratio | A | 4.18 / 3.42 | 2.26 / 1.51 | 2.05 / 1.27 | 1.97 / 1.21 | 1.93 / 1.13 | 2.48 / 1.71 |
| g10_geo_blend_g3_b7 | **B** | 3.57 / 2.61 | 2.22 / 1.25 | 1.94 / 1.04 | 1.91 / 1.06 | 1.90 / 1.05 | 2.31 / 1.40 |
| B-G7 b7_blend_b5_fsa_level | B | 3.21 / 1.95 | 2.31 / 1.07 | 1.93 / 0.94 | 1.90 / 1.01 | 1.89 / 1.01 | 2.25 / 1.19 |
| NASS's forecast (not independent) | - | 3.04 / 1.06 | 2.58 / 0.91 | 1.76 / 0.70 | 1.60 / 0.57 | 1.60 / 0.57 | 2.12 / 0.76 |
| Same as last year | - | 6.86 / 4.01 | 6.86 / 4.01 | 6.86 / 4.01 | 6.86 / 4.01 | 6.86 / 4.01 | 6.86 / 4.01 |

**2017-2024 (reported, not used to decide)**

| Model | Tier | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec | Avg Aug-Dec |
|---|---|---|---|---|---|---|---|
| A-G3 | A | 4.58 / 3.66 (3 F) | 1.75 / 0.92 | 1.76 / 0.95 | 1.77 / 1.08 | 1.77 / 1.12 | 2.33 / 1.55 |
| g6_net_failed | A | 4.58 / 3.57 | 1.79 / 0.96 | 1.80 / 0.99 | 1.81 / 1.11 | 1.82 / 1.15 | 2.36 / 1.55 |
| g7_net_failed_prevented | A | 7.07 / 5.86 | 5.22 / 3.71 | 5.23 / 3.72 | 5.23 / 3.81 | 5.24 / 3.84 | 5.60 / 4.19 |
| g8_vintage_growth | A | 4.72 / 3.98 | 1.78 / 1.08 | 1.76 / 0.99 | 1.77 / 1.10 | 1.77 / 1.12 | 2.36 / 1.65 |
| **g9_national_reconciliation** | A | 4.58 / 3.65 | **1.67 / 0.81** | **1.69 / 0.84** | **1.69 / 0.96** | **1.69 / 1.00** | 2.26 / 1.45 |
| g11_drought_abandonment | A | 4.64 / 3.82 | 1.68 / 0.79 | 1.71 / 0.81 | 1.71 / 0.93 | 1.71 / 0.95 | 2.29 / 1.46 |
| g12_us_bias_corrected | A | 4.81 / 4.05 | 2.07 / 1.29 | 1.83 / 0.96 | 1.79 / 1.02 | 1.79 / 1.05 | 2.46 / 1.67 |
| g13_vintage_matched_ratio | A | 4.82 / 4.13 | 1.87 / 1.23 | 1.82 / 1.14 | 1.80 / 1.21 | 1.77 / 1.16 | 2.42 / 1.77 |
| g10_geo_blend_g3_b7 | **B** | 3.94 / 3.01 | 1.85 / 1.00 | 1.73 / 0.98 | 1.75 / 1.07 | 1.75 / 1.10 | 2.20 / 1.43 |
| B-G7 | B | 3.49 / 2.39 | 2.08 / 1.08 | 1.72 / 1.00 | 1.74 / 1.05 | 1.74 / 1.07 | 2.15 / 1.32 |
| NASS's forecast | - | 3.26 / 1.30 | 2.53 / 1.05 | 1.66 / 0.82 | 1.66 / 0.82 | 1.66 / 0.82 | 2.15 / 0.96 |
| Same as last year | - | 7.35 / 4.11 | 7.35 / 4.11 | 7.35 / 4.11 | 7.35 / 4.11 | 7.35 / 4.11 | 7.35 / 4.11 |

Checks: A-G3, B-G7, NASS and persistence equal the monthly harness to the stored 0.1 acre in all 3,198
state-year-date rows each, and the independent rebuild of A-G3 inside `run.py` equals the grain folder's
`predict_fsa` exactly (`out/reproduction.json`). 15 Jul is in `out/summary.csv` (every Tier A candidate =
persistence there). A descriptive 2014-2024 period (the years in which A-G3 has all three reference years) is also in
`out/summary.csv`: 15 Nov A-G3 1.76 / 1.02, g9 1.69 / 0.93, NASS 1.62 / 0.62.

Mean signed US error at 15 Nov (positive = too many acres): 2012-2024 A-G3 +0.36, g9 +0.37, NASS +0.45;
2017-2024 A-G3 +0.81, g9 +0.83, NASS +0.72. g9 does not remove the positive 2017-2024 bias; it lowers the spread
around it.

### 2.3 Against A-G3, paired by year (2012-2024)

Cell: mean difference in points (mean + 2 SE) [90% bootstrap interval] years better of 13. Negative = better than
A-G3. `out/paired.csv` has every date, both periods and both metrics.

| Candidate, state WAPE | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec |
|---|---|---|---|---|---|
| g6 | +0.01 (+0.06) [-0.03, +0.06] 5 | +0.04 (+0.09) [+0.01, +0.08] 4 | +0.05 (+0.09) [+0.01, +0.09] 4 | +0.06 (+0.10) [+0.02, +0.09] 3 | +0.06 (+0.10) [+0.02, +0.09] 3 |
| g7 | +2.31 (+3.97) [+1.10, +3.74] 1 | +2.95 (+4.42) [+1.89, +4.20] 0 | +3.07 (+4.51) [+2.02, +4.29] 0 | +3.06 (+4.49) [+2.02, +4.27] 0 | +3.07 (+4.49) [+2.03, +4.27] 0 |
| g8 | -0.03 (+0.30) [-0.29, +0.23] 4 | -0.09 (+0.09) [-0.25, +0.04] 6 | -0.00 (+0.00) 1 | +0.00 (+0.00) 0 | identical |
| **g9** | -0.00 (+0.04) [-0.04, +0.03] 6 | -0.06 (+0.00) [-0.11, -0.01] 10 | -0.06 (-0.00) [-0.11, -0.02] 9 | **-0.06 (-0.01) [-0.11, -0.02] 10** | -0.06 (-0.01) [-0.11, -0.02] 10 |
| g10 (B) | -0.57 (-0.18) [-0.87, -0.26] 8 | -0.07 (+0.14) [-0.24, +0.09] 8 | -0.06 (+0.02) [-0.14, -0.01] 9 | -0.03 (+0.02) [-0.08, +0.00] 10 | -0.02 (+0.01) [-0.04, +0.00] 10 |
| g11 | -0.01 (+0.17) [-0.13, +0.14] 5 | -0.07 (+0.02) [-0.15, -0.00] 6 | +0.00 (+0.11) [-0.08, +0.09] 6 | +0.00 (+0.11) [-0.08, +0.09] 6 | -0.00 (+0.10) [-0.08, +0.08] 6 |
| g12 | +0.39 (+0.75) [+0.13, +0.69] 1 | +0.38 (+0.70) [+0.14, +0.65] 3 | +0.19 (+0.41) [+0.04, +0.39] 3 | +0.09 (+0.23) [-0.01, +0.21] 6 | +0.08 (+0.23) [-0.03, +0.21] 6 |
| g13 | +0.04 (+0.41) [-0.23, +0.33] 5 | -0.03 (+0.16) [-0.18, +0.11] 6 | +0.05 (+0.09) [+0.01, +0.08] 5 | +0.03 (+0.06) [+0.01, +0.06] 3 | +0.01 (+0.02) [-0.00, +0.02] 4 |

| Candidate, \|US\| | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec |
|---|---|---|---|---|---|
| g9 | -0.01 [-0.07, +0.04] | -0.08 [-0.17, +0.01] | -0.08 [-0.17, +0.01] | -0.08 [-0.17, +0.01] | -0.08 [-0.17, +0.01] |
| g8 | -0.10 [-0.55, +0.33] | -0.13 [-0.44, +0.13] | +0.02 | +0.01 | 0 |
| g11 | -0.01 [-0.21, +0.19] | -0.16 [-0.36, +0.03] | -0.01 | +0.00 | -0.02 |

On 2017-2024, g9 minus A-G3 at 15 Nov is -0.08 point of state WAPE (7 of 8 years better; mean + 2 SE +0.004, so not significant on 8 years).

### 2.4 Against NASS's own forecast, paired by year

State WAPE, model minus NASS (negative = better than NASS) [90% bootstrap] years better:

| Period | Model | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec |
|---|---|---|---|---|---|---|
| 2012-2024 | A-G3 | +1.10 [-0.00, +2.23] 6/13 | -0.29 [-0.84, +0.24] 8/13 | +0.24 [-0.10, +0.63] 5/13 | +0.34 [+0.06, +0.66] 4/13 | +0.32 [+0.05, +0.63] 4/13 |
| 2012-2024 | g9 | +1.10 [+0.00, +2.23] 6/13 | -0.35 [-0.89, +0.18] 9/13 | +0.18 [-0.14, +0.56] 5/13 | +0.28 [+0.00, +0.60] 4/13 | +0.26 [-0.01, +0.57] 4/13 |
| 2017-2024 | A-G3 | +1.31 [-0.36, +3.06] 4/8 | -0.78 [-1.41, -0.19] 6/8 | +0.10 [-0.06, +0.26] 2/8 | +0.11 [-0.06, +0.26] 2/8 | +0.12 [-0.06, +0.28] 2/8 |
| 2017-2024 | g9 | +1.32 [-0.34, +3.07] 4/8 | **-0.85 [-1.47, -0.29] 7/8** | +0.03 [-0.14, +0.19] 3/8 | **+0.03 [-0.14, +0.18] 3/8** | +0.03 [-0.14, +0.20] 3/8 |

US |error|, g9 minus NASS: 2012-2024 +0.45 at 15 Sep [-0.05, +0.98], +0.46 at 15 Nov [+0.15, +0.80]; 2017-2024
-0.24 at 15 Sep [-0.52, +0.01], +0.14 at 15 Nov [-0.06, +0.36]. What this means:
- **15 Nov, 2017-2024: g9 ties NASS on the state split** (1.69 vs 1.66, interval -0.14 to +0.18) without any
  current-year NASS input. NASS is still better on the US total (0.82 vs 0.96) and over 2012-2024 (1.60 vs 1.88).
  2012-2014 carry most of that gap (A-G3 3.52 / 2.41 / 2.91 vs NASS 1.41 / 1.61 / 1.88): the dated FSA history then
  holds only one or two reference years, and 2012 is the drought year.
- **15 Sep, 2017-2024: g9 beats NASS's September forecast** (1.67 vs 2.53, 7 of 8 years), four months before NASS's
  January number, as A-G3 already did (1.75).
- **15 Aug:** every FSA candidate loses to NASS, because three of the eight recent years have no FSA file by then.

### 2.5 What each candidate did, and why

- **g6 (net of failed):** slightly worse at every date (+0.04 to +0.06). Failed grain acres are 0.04-0.55% of planted
  and FSA's `planted_acres` already excludes them (section 1), so subtracting them again adds noise.
- **g7 (net of failed and prevented):** far worse (5.0% at 15 Nov). Prevented acres were never planted and swing
  from 0.6 M (2021) to 11.3 M (2019): the 2019 US forecast misses by -11.4% and 2021's by +6.6% once 2019's ratio
  enters the three-year median. Prevented planting is not abandonment of planted grain.
- **g8 (vintage growth):** helps in years whose early file was incomplete (15 Sep 2013: 4.90 -> 4.03; 2015:
  2.35 -> 1.75) and hurts from 2016 on (2016: 1.19 -> 1.54): FSA files became complete earlier each year, so growth
  learned from older years over-corrects. Net -0.09 at 15 Sep, not significant. Identical to A-G3 from 15 Oct except
  when the September file was still the newest (2020, 2021).
- **g9 (national reconciliation):** one national scale factor per year, 0.9978 to 1.0054 over 2012-2024. The sum of
  per-state median ratios is a noisier estimate of the total than the median of national ratios; rescaling keeps the
  state split and takes the total from the steadier national ratio. The three-year median national NASS/FSA ratio
  fell from 0.994 (used for 2012) to 0.971 (used for 2024), so this is not a constant correction.
- **g10 (Tier B blend):** lies between its parents; never better than B-G7 at 15 Nov, much worse at 15 Aug.
- **g11 (drought):** k fitted 0.04-0.06 (grain acres fall by 4-6% of the change in severe-drought share), small
  effects of both signs: at 15 Nov it helps 2018, 2020, 2022, 2024 and hurts 2015, 2019, 2023. Not significant at
  any date.
- **g12 (US bias correction):** worse at every date. The bias learned from 2012-2014 (A-G3 then had one or two
  reference years; US errors +1.9, -1.3, -2.4%) raised 15 Nov 2015 by 1.4% and 2016 by 0.6% (15 Sep 2015 by 3.6%). The positive 2017-2024 bias is not
  stable enough over 2012-2024 to correct.
- **g13 (vintage-matched ratio):** worse at 15 Nov (+0.03) and on the US total: Nov-to-Nov ratios inherit last
  year's late-reporting pattern; A-G3's final-file ratio is steadier.

### 2.6 2026 forecast, 15 Nov 2026 (5 Nov 2026 FSA file, published 10 Nov 2026)

US = sum of the 41 states, million acres. 80% intervals use the grain folder's method (size-class quantiles of the
15 Nov 2012-2024 backtest log errors; US: exp(+-1.2816 x RMS of the US log error)), each fitted on that model's own
backtest: leave-one-year-out state coverage 0.792 for both A-G3 and g9; US log RMS 0.0141 (A-G3) and 0.0130 (g9).
Intervals were added after scoring, as decoration of the forecast. NASS's own November 2026 forecast is shown for
comparison only, never as an input.

| State | g9 (recommended) | g9 80% | A-G3 | NASS Nov 2026 forecast | NASS 2025 final | g9 vs 2025 % | g9 vs NASS % |
|---|---|---|---|---|---|---|---|
| **US (41 states)** | **88.750** | 87.284-90.241 | 88.690 | 88.506 | 90.948 | -2.4 | +0.28 |
| Iowa | 12.788 | 12.314-13.206 | 12.779 | 12.800 | 13.150 | -2.8 | -0.09 |
| Illinois | 10.862 | 10.460-11.217 | 10.855 | 10.950 | 10.950 | -0.8 | -0.80 |
| Nebraska | 9.619 | 9.263-9.933 | 9.613 | 9.610 | 10.390 | -7.4 | +0.10 |
| Minnesota | 8.365 | 8.055-8.638 | 8.359 | 8.300 | 8.440 | -0.9 | +0.78 |
| Kansas | 6.533 | 6.291-6.746 | 6.528 | 6.550 | 6.450 | +1.3 | -0.26 |
| South Dakota | 5.914 | 5.695-6.108 | 5.910 | 5.840 | 6.350 | -6.9 | +1.27 |
| Indiana | 5.119 | 4.930-5.286 | 5.116 | 5.160 | 5.240 | -2.3 | -0.79 |
| North Dakota | 4.501 | 4.335-4.648 | 4.498 | 4.450 | 4.490 | +0.3 | +1.15 |
| Missouri | 3.474 | 3.346-3.588 | 3.472 | 3.470 | 3.640 | -4.6 | +0.13 |
| Ohio | 3.232 | 3.113-3.338 | 3.230 | 3.230 | 3.150 | +2.6 | +0.08 |

Every state and every candidate: `out/forecast_2026.csv`. g9's 2026 scale factor is 1.0007, so g9 and A-G3 differ by
60,000 acres in the US total. g11's k (0.053) and g12's b (0.0040) are frozen at their 2012-2024 fits.

## 3. Post hoc variants (written after section 2; none can be selected)

`posthoc.py`, same harness, dates and years. They say what to pre-register next, nothing more.

| Variant | What it is | 15 Sep 2012-2024 | 15 Nov 2012-2024 | 15 Nov 2017-2024 |
|---|---|---|---|---|
| ph1_g9_on_g11 | g11's drought-adjusted state split, rescaled to g9's national total | 2.21 / 1.36 | 1.87 / 1.04 | 1.67 / 0.96 |
| ph2_g9_on_g8 | g8's grown early file, rescaled to a national total that also uses g8's growth | 2.15 / 1.20 | 1.88 / 1.05 | 1.68 / 0.98 |
| ph3_g3_hist0910 | A-G3 with the 2009 and 2010 FSA finals as references (saved 9 Sep 2011, taken as published 17 Sep 2011; they have no data date, so the documented rule leaves them out). Changes 2012-2013 only | 2.23 / 1.42 | 1.89 / 1.10 | 1.77 / 1.08 |
| ph4_g9_hist0910 | g9 with that longer history | 2.17 / 1.34 | **1.83 / 1.02** | 1.69 / 0.96 |

Paired against A-G3 (state WAPE, 2012-2024: mean (mean + 2 SE) years better): ph1 at 15 Sep -0.08 (-0.03) 11/13 and
at 15 Nov -0.07 (-0.03) 10/13; ph4 at 15 Sep -0.12 (-0.01) 11/13 and at 15 Nov -0.12 (-0.02) 11/13; ph2 at 15 Sep
-0.14 (+0.03) 9/13. Against g9 none is distinguishable (`out/posthoc_paired.csv`). Reading: drought shares (g11) may
help the state split once g9 pins the US total, and a full three-year FSA history would close about 0.06 point of the
2012-2024 gap (2013: 2.41 -> 1.83). Both need a fresh pre-registration and, for ph3/ph4, an argued publication date
for the undated 2009-2010 files.

## 4. Limitations

- g9's pass is marginal (mean + 2 SE = -0.005; it fails the mean + 3 SE bar, and fails if 2014 or 2019 is dropped).
  With 7 Tier A candidates the chance that at least one passes the 2 SE bar by luck is not small. Treat g9 as "no
  worse, probably slightly better" than A-G3, not as a proven gain.
- 2017-2024 is inside the selection period; there is no untouched holdout. 2025 was not scored.
- 15 Aug results are dominated by three years without an FSA file by 15 Aug (2022-2024); no Tier A candidate can fix
  that, because there is no current-year input then.
- The state set is the 41 states with a NASS grain final; the US total here is their sum, not NASS's published US.
- NASS's own estimates use FSA data, so FSA-based models are not independent of NASS's final numbers.
- g6 and g7 were tested as specified; they subtract acres that FSA's planted column already excludes.

## 5. Files and how to run

From the repository root:

```bash
export PYTHONDONTWRITEBYTECODE=1    # the imported model modules otherwise refresh __pycache__ in their own folders
.venv/Scripts/python.exe test_models/variations/grain_variants/run.py       # pre-registered candidates (~50 s)
.venv/Scripts/python.exe test_models/variations/grain_variants/posthoc.py   # post hoc variants (~30 s; needs run.py's out/)
.venv/Scripts/python.exe -m ruff check --no-cache --select E,F,W --line-length 120 test_models/variations/grain_variants/
```

| File (out/) | Content |
|---|---|
| preregistration.sha256, preregistration_README_snapshot.md | hash of section 1, and the README as written before scoring |
| by_state_year.csv | every model, date, year and state: pred, actual (acres) |
| by_year.csv | state WAPE and US error per model, date and year; fallback flag and FSA file used |
| summary.csv | means per model, date and period (2012-2024, 2017-2024, descriptive 2014-2024) and the Aug-Dec average |
| paired.csv | every candidate vs A-G3 and vs NASS (g10 also vs B-G7): mean, SE, mean + 2/3 SE, bootstrap 90%, years better / tied |
| decision.json | the README 1.4 rule at 15 Nov, 15 Aug, 15 Sep |
| fitted_params.csv | g11 k, g12 b, g8 growth pairs and US growth, g9 scale and national ratio, per date and year (2026 included) |
| forecast_2026.csv | 15 Nov 2026 forecast of every model by state and US; 80% intervals for A-G3 and g9 |
| reproduction.json | equality with the monthly harness, A-G3 rebuild check, as-of patch, interval fits |
| posthoc_*.csv, posthoc_notes.json | section 3 |
