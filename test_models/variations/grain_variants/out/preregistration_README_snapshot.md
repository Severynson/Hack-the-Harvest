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
