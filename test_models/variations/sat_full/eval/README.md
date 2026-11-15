# Satellite silage candidates on the full state sample: do they beat their bases?

Owner key: `eval`. Folder: `test_models/variations/sat_full/eval/`. Code: `eval.py`. Outputs: `out/`. Scratch:
`C:/Users/danie/AppData/Local/Temp/claude/dfe35210c43945cb/9bd8cc88-21cc-4423-8ecd-0115ef62e1a4/scratchpad/agents/eval/`.
Nothing outside these two folders is written. Bytecode writing is off, so importing other folders' modules leaves no
`__pycache__` behind. There are no git writes.

## 1. Pre-registration (written before any candidate or base score was computed; not edited afterwards)

This section, from its heading to the end-of-section marker, is hashed into `out/preregistration.sha256` before
the first scored run. `eval.py` checks the hash on every step and refuses to run if it changed.

### 1.0 What I had seen before writing this

- The three sat_full reports, as their summaries (no candidate score of this task in any of them):
  - `corn_mask`: the real-time imagery corn mask P (prior years only) gives 0.848 / 0.795 precision / recall at
    15 Nov against CDL (pooled), and fails the agent's rule in 11 of 15 states (TX, CO and KS under-call; ND, ID
    over-call). For 2016, P is UNCOMPUTED.
  - `shares`: the change in log silage-like share does not follow NASS's silage change. K0 rho -0.271 (CDL, 15 Nov),
    -0.199 (P); K1 0.020 (CDL), 0.065 (P). The share is diluted (about 0.17 of a true change shows) and its bias
    is unstable from year to year (state SD 0.21-0.30). The share level ranks states (Spearman 0.73-0.86).
  - `stress`: the stress index tracks the Drought Monitor (r 0.375) but not the NASS silage change (r 0.058).
    Only the peak-NDVI part is linked to silage (r 0.235; post hoc).
- The earlier draw-1 round: `test_models/ownModels/satellite/eval/README.md`. A2 = A-S3 x r^0.5 (CDL mask, draw 1,
  2020-2024, 15 Nov) scored 14.09 / 6.15 (15-state WAPE / |total|) against A-S3 at about 10.1 / 4.6. All of its
  `x r^0.5` candidates were 3-4 points of WAPE worse than their bases. I read its candidate and interval
  definitions, which I reuse below.
- `test_models/variations/sat_stress/README.md`: c3a = A-S3 x exp(0.05 x stress) and c3b = SC x exp(0.05 x stress)
  on draw 1, 2020-2024, 15 Nov: 9.94 / 4.11 and 10.06 / 3.06 (15 states), not significant against their bases.
- 48-state base scores: the monthly harness README (A-S3, reversion, persistence at six dates, 2017-2024) and the
  silage_combos README (SC, SC_A, SC_B, 2012-2024 and 2017-2024). I have not computed or seen the 15-state scores of
  any base on 2017-2024 at any date.
- Availability (counts only, no errors):
  - `shares/out/shares.csv` has the dates Aug-Dec (no Jul) for 2016-2026.
  - Missing shares: P 2016 (no prior year), CDL 2026 (no 2026 CDL) and Dec 2026 (future) are UNCOMPUTED. 54 rows
    carry `fallback: assessable_share < 0.5`, almost all in Aug.
  - `stress/out/stress.csv` (weight none, scale rms) has values for CDL 2017-2025 and P 2018-2026, available from
    Sep 15.
  - The monthly harness has A-S3, reversion_only_report_H13 and s0_persistence for 48 states, 2012-2024 (H13
    2017-2024) and all six dates.
  - The silage_combos backtest has SC, SC_A and SC_B for 48 states at Sep, Oct and Nov only, for 2012-2024 and
    2026; it has no 2025.
  - A feasibility run, with no error computed, showed that `ownModels/silage/run.py` `run_asof` and
    `kernelag.silage_level.predict` run for Jul and for 2025 once the as-of map is widened in memory.

### 1.1 Scope

- States: the 15 states of the sample: CA, CO, ID, IA, KS, MI, MN, NE, NY, ND, OH, PA, SD, TX, WI. Maryland is not
  among them; it appears only as one of the other 33 states of the 48-state US total, and there it always keeps
  the base.
- Scored years: 2017-2024 (8). 2025 is information only: it is scored once and enters no choice, fit, interval or
  display selection.
- Dates: the 15th of Jul, Aug, Sep, Oct, Nov and Dec. Satellite inputs use only looks dated on or before the date
  (the owners' `series_asof` cut).
- Truth: NASS final state silage acres, the `actual` column of
  `test_models/ownModels/monthly/out/monthly_by_state_year.csv`. For 2025 it comes from A-S3's
  `load_nass_finals()`, which is asserted equal to the monthly `actual` on 2017-2024.

### 1.2 Bases (read; regenerated only where the files lack a date or 2025)

| Key | Display | Tier | Source, 2017-2024 | Jul/Aug/Dec and 2025 |
|---|---|---|---|---|
| `AS3` | A-S3 | A | monthly harness `s3_fsa_residual` (corrected FSA dates), all six dates | 2025 regenerated (G1) |
| `SC` | SC | C (NASS in-season yield and grain-acre forecasts) | silage_combos `SC`, Sep/Oct/Nov | regenerated (G2) |
| `SCA` | SC_A | A (Drought Monitor) | silage_combos `SC_A`, Sep/Oct/Nov | regenerated (G2) |
| `SCB` | SC_B | B (NASS yield forecast) | silage_combos `SC_B`, Sep/Oct/Nov | regenerated (G2) |
| `REV` | reversion | A (history only) | monthly `reversion_only_report_H13` (date-free) | 2025 regenerated (G1) |
| `PER` | persistence | benchmark | monthly `s0_persistence` | 2025 = 2024 NASS final |

Regeneration imports the owners' code unchanged and widens the as-of map in memory only, exactly as the monthly
harness does: `kernelag.context.ASOF_MONTH` gains jul = 7 and dec = 12, and the silage module's `ASOF` dict is
replaced by the six (month, 15) dates.
- G1: `ownModels/silage/run.py` `run_asof(key, ..., years 2012-2025)` gives `s3_fsa_residual` and
  `s0_persistence`. `build_rows(..., H13, 2013-2025, "nov", None, None, None)` with `s1_out_of_sample(..., H13)`
  gives the report reversion. Gate: the regenerated 2017-2024 values equal the monthly file within 1 acre at all six
  dates. If the gate fails, the 2025 values of that base are UNCOMPUTED.
- G2: `kernelag.silage_level.load_history(data/Quickstats Data, asof)` and `predict`. SC uses the module's own
  exposure, SC_B the exposure with an empty `grain_asof`, and SC_A silage_combos' `drought_exposure` (imported),
  for 2017-2025 and 2026 at all six dates. Gate: the regenerated Sep/Oct/Nov values of 2017-2024 and 2026 equal
  the silage_combos file within 1 acre. If the gate fails, the regenerated cells are UNCOMPUTED. Expected by
  construction: at Jul no NASS yield forecast exists, so SC = SC_B = the smoothed level; SC_A at Jul uses Drought
  Monitor maps to Jul 15. Dec equals Nov for SC and SC_B (there is no December NASS report), and SC_A at Dec equals
  Nov because its drought window ends Sep 30.
- Fitted things inside the bases (all expanding windows owned by their folders, test year excluded):
  - A-S3's shrink weight is fitted on 2012 <= y < t at the same date.
  - SC's alpha and gamma are chosen on 2005 <= y < t.
  - The reversion ridge is fitted on y < t.
  - The P corn mask is trained on years < t.
  - The classifiers K0 (Quebec 2023) and K1 (Quebec 2019-2026) are fitted on Quebec, not on any US outcome. K1
    sees same-season Quebec labels; the shares agent's K1_xs check bounds this at 0.03 of rho.
  - My candidates have no fitted parameter.

### 1.3 Satellite candidates (no fitted parameters)

For each base B in {AS3, SCA, SC}, applied to the 15 states only (the other 33 states keep B):

- Share candidates `B_sat_K_m`, for classifier K in {K0, K1} and mask m in {P (headline, real time), CDL (reference,
  not real time)}: pred = B x r^0.5, with r = clip(share(t) / share(t-1), 0.5, 2), at the same date, classifier
  and mask.
  - `share` = column `share` of `shares/out/shares.csv` (draws 1+2, 20 areas per state).
  - The term is available for (state, t, date) only if both the t and t-1 rows have status `ok` and share > 0.
    Otherwise pred = B, and the state-year is a fallback.
  - Jul has no share, so every Jul cell is a fallback. Under P, 2017 is a fallback at every date (the 2016 P share
    is UNCOMPUTED). Under CDL, 2026 is unavailable.
  - Aug is computed wherever the status is `ok`. The shares agent noted that Aug cut dates are pre-harvest, so Aug
    cells are read with that caveat.
- Stress candidates `B_stress_m`, for m in {P, CDL}: pred = B x exp(0.05 x stress(t)).
  - `stress` = `stress/out/stress.csv` rows with weight `none` and scale `rms` (the stress agent's headline), mask m.
  - The index window ends Sep 15. Sep, Oct, Nov and Dec use that same value; Jul and Aug are fallbacks
    (pred = B). A missing value (P 2017, CDL 2026) is a fallback.

That makes 12 share candidates and 6 stress candidates. Only the 9 P-mask candidates are eligible for adoption.

### 1.4 Metrics

For each model, date and year, over the 15 states:
- WAPE15 = 100 x sum |pred - S| / sum S.
- TOT15 = 100 x (sum pred - sum S) / sum S, and its absolute value |TOT15|.
- US48 = 100 x (sum over 48 states of pred - sum S) / sum S, where the other 33 states take the candidate's base
  (bases: themselves), and |US48|.
- Information: WAPE48 over the same 48 states.

Summaries:
- The mean over 2017-2024 for each date.
- "Average Jul-Dec" = the mean of the six date means; "Average Aug-Dec" = the mean of the five date means.
- Fallback count = the number of the 120 state-years (15 x 8) in a cell where the satellite term was unavailable.

### 1.5 Decision rule (mechanical; 15 Nov; 2017-2024; P-mask candidates only)

d_y = metric(c, y) - metric(B, y) over the 8 years (fallback years enter with their actual d_y, which is 0 when
every state falls back); SE = sd(d_y, ddof 1) / sqrt(8).

A candidate c is **ADOPTED** over its base B if either:
- (W) mean d(WAPE15) + 2 SE < 0 AND mean |TOT15|(c) - mean |TOT15|(B) <= 0.10 points; or
- (T) mean d(|TOT15|) + 2 SE < 0 AND mean WAPE15(c) - mean WAPE15(B) <= 0.10 points.

Otherwise it is "not adopted" ("not shown"), reported with its point estimate and CIs.
- Nine eligible candidates x two routes = 18 tests with no multiplicity correction. A single pass is reported with
  that caveat.
- If several candidates are ADOPTED, the 2026 recommendation for each base is the adopted one with the lowest
  15 Nov mean WAPE15.
- Information only (never adoption): the same rule for the CDL candidates (not real time), for the P candidates on
  2018-2024 (the years with a P change), and at the other dates.

### 1.6 Uncertainty and robustness

For every candidate against its base, at 15 Nov, I report 90% percentile intervals of the mean paired difference
(WAPE15 and |TOT15|), with seed 20261115:
- (i) years resampled (10,000 draws);
- (ii) states resampled as clusters, the same draw in every year, with WAPE15 and TOT15 recomputed over the drawn
  states (2,000 draws);
- (iii) years and states jointly (2,000 draws).

Also reported: years better, worse and tied, and per-state wins (sum of |error| over 2017-2024).
- Drop-one-year (8 runs, n = 7) and drop-one-state (15 runs, 14 states recomputed): the rule is re-applied each
  time. This is reported for every ADOPTED candidate and, as information, for all P candidates.

### 1.7 Output grids (the user's format)

Rows: Jul 15, Aug 15, Sep 15, Oct 15, Nov 15, Dec 15, "Average Jul-Dec", "Average Aug-Dec". Columns: models. Each
cell is "WAPE15 % / |TOT15| %" (2017-2024 means).

Marks:
- `*` means the satellite term was unavailable in every state-year of the cell, so the cell equals the base.
- `*n` means it was unavailable in n of the 120 state-years.
- `(F)` or `(k/8 F)` on A-S3-based columns means A-S3 itself ran its no-FSA fallback (monthly harness flag).
- In averages, `*` marks an average containing at least one all-fallback date.

In markdown, the lowest WAPE15 and the lowest |TOT15| of each row are bold, each on its own (ties at 2 decimals are
all bold).

Grids:
- Tier A family, P mask (`out/grid_tierA.csv`): A-S3, A-S3+sat K0, A-S3+sat K1, A-S3+stress, SC_A, SC_A+sat best,
  SC_A+stress, reversion, persistence. "SC_A+sat best" is the K (K0 or K1) with the lower 15 Nov 2017-2024 mean
  WAPE15 under P (ties: K1). This is a display choice only, not an adoption; the other K is in the full table.
- SC family, P mask (`out/grid_sc.csv`): SC, SC+sat K0, SC+sat K1, SC+stress, SC_B, reversion, persistence.
- The same two grids with the CDL mask (`grid_tierA_cdl.csv`, `grid_sc_cdl.csv`, reference), and with
  "WAPE15 / |US48|" cells (`grid_tierA_us48.csv`, `grid_sc_us48.csv`, P mask).
- A full table of every model at every date (`out/summary.csv`) and per year (`out/by_year.csv`).

### 1.8 2026 (ADOPTED candidates only)

As of 15 Nov 2026, and also 15 Sep and 15 Oct 2026, for the 15 states and the US. Bases for 2026 come from the
silage_combos file (Sep/Oct/Nov 2026); P shares and P stress for 2025/2026 come from the owners' files. 80%
intervals:
- State: q10, q50, q90 of log(S / c) over the candidate's own 120 backtest state-years at that date.
- Mask widening:
  - Share candidates: m_s = ln(`corn_acre_ratio`) of `corn_mask/out/metrics_by_state_year.csv` (regime P, pool
    all, year 2025, same date), the 2025 corn-mask replay error. M = sqrt(mean over the 15 states of m_s^2), and
    w_s = 1.2816 x 0.5 x max(|m_s|, M).
  - Stress candidates: Delta_s = stress_P(2025) - stress_CDL(2025), D = its RMS, and
    w_s = 1.2816 x 0.05 x max(|Delta_s|, D).
- lo80 = c x exp(q50 - sqrt((q50 - q10)^2 + w_s^2)) and hi80 = c x exp(q50 + sqrt((q90 - q50)^2 + w_s^2)).
- US: T = the 15 candidate states + 33 base states; u10, u50, u90 of the 8 yearly log(S_US / T) errors (numpy
  linear percentiles); W = sqrt(sum_s (c_s x w_s)^2) / T. lo80 = T x exp(u50 - sqrt((u50 - u10)^2 + W^2)), and hi80
  likewise.
- Leave-one-year-out coverage of the unwidened state intervals is reported.

If nothing is ADOPTED, no 2026 forecast is issued. An information table of the 2026 P-candidate values at 15 Nov,
next to their bases and labelled "not adopted", is written instead.

### 1.9 Expectations (written before scoring)

- E1: no P share candidate is ADOPTED.
- E2: the K0 share candidates worsen the 15 Nov mean WAPE15 by at least 1 point against each base (P and CDL).
- E3: the K1 share candidates change the 15 Nov mean WAPE15 by less than 1 point either way.
- E4: the stress candidates move the 15 Nov mean WAPE15 by less than 0.3 points; none is ADOPTED.
- E5: P and CDL give 15 Nov mean WAPE15 differences within 0.5 points of each other for the same K and base.

### 1.10 What is never done

- No choice, fit or interval uses 2025 or Maryland.
- No file outside this folder and the scratch folder is written; no git writes; `.env` is never read; no network.
- Uncomputed numbers are written as "UNCOMPUTED: reason".

<!-- END OF PRE-REGISTRATION -->

Everything below was written after the scores were computed. `eval.py` checks the section 1 hash at every step;
`out/run.json` records `"unchanged": true` (sha256 24ec68bd…).

## Deviations

- The method has no deviations: candidates, availability rule, metrics, decision rule, CIs, robustness and grids
  are as pre-registered.
- Additions, not pre-registered and changing no reading:
  - `out/diag_factor_vs_residual.csv`, which checks whether the satellite factor points the way of the base's miss.
  - A cross-check of the regenerated 2025 report reversion against the stored
    `data/models/state_score_2025_reversion_only.csv`.
  - The 2026 information table also covers 15 Sep and 15 Oct.
  - The 2018-2024 window was computed at every date, not only at 15 Nov.

## 2. Short answer (15 states, 2017-2024, 15 Nov)

- **Nothing is ADOPTED.** No candidate passes, under either route, among the 9 eligible real-time candidates (18
  tests). The rule would also pass none of the 9 CDL reference candidates, at any date, on 2017-2024 or on
  2018-2024. Leaving out any one year or any one state does not change this (0 of 23 runs per candidate).
- **The share-change candidates make every base worse** (`B x r^0.5`):
  - With the real-time mask P, mean WAPE15 rises by +1.60 to +2.54 points and mean |TOT15| by +1.25 to +2.90.
  - With the CDL mask, WAPE15 rises by +2.05 to +2.88.
  - The 90% CIs over years and over states exclude 0 for every share candidate. The joint CI excludes 0 for every
    one except SC+sat K1 (P), [-0.12, +3.44].
  - Each share candidate is worse than its base in 6-8 of 8 years and in 11-15 of 15 states.
  - The earlier draw-1 round (CDL, 2020-2024) found +3 to +4 points. With twice the areas and 2017-2024, the
    damage is smaller but still large and consistent.
- **The stress candidates do almost nothing** (`B x exp(0.05 x stress)`):
  - With P, the differences are +0.32 (A-S3), +0.26 (SC_A) and +0.07 (SC) points of WAPE15, all worse and none
    significant.
  - With CDL (reference, not real time), they are +0.12, +0.03 and -0.18. The SC -0.18 is the only point gain of
    the 18, with +2 SE = +0.26.
- **Why** (diagnostic, not pre-registered, `out/diag_factor_vs_residual.csv`, 15 Nov):
  - The share factor moves predictions by an RMS of 8-9% (log 0.08-0.09).
  - Its correlation with the base's miss, log(S / B), is -0.15 to -0.20 for K0 and -0.01 to -0.11 for K1. So it
    adds noise of almost half the size of the base error (RMS log miss 0.17-0.18 becomes 0.19-0.22).
  - The stress factor has the right sign (r +0.05 to +0.12) but is tiny (RMS log 0.036), so it cannot move the
    error much either way.
- **Best real-time base on these 15 states: SC_A** (Tier A, Drought Monitor). It has the lowest WAPE15 and the
  lowest |TOT15| of every model in the grids, at every date. At 15 Nov it scores 11.71 / 3.91 against A-S3 11.75 / 4.81, SC 12.07 / 4.10, reversion 12.29 / 4.69
  and persistence 13.53 / 4.34. On the 48-state US total, SC (Tier C) stays better: |US48| 3.34 against SC_A's 3.65.
- **2026:** no satellite forecast is issued, because nothing was adopted.
  - Information only: at 15 Nov 2026 the P share factors would lift the 15-state total by +7.7% (K1) to +10.8% (K0)
    over each base. The drivers are Nebraska (x1.36), South Dakota (up to x1.25), Iowa (x1.25-1.26) and Minnesota
    (x1.16).
  - This is the 2025→2026 share jump that the shares agent judged a year or mask effect, not more silage.
  - The P stress factor would add +1.5%.
- **2025 (information only, scored once):**
  - At 15 Nov, the share candidates are worse again: +1.75 to +5.83 points of WAPE15 under P, and +1.06 to +5.12
    under CDL.
  - The stress candidates are better on all three bases: A-S3 15.21 → 14.97 (P) / 14.83 (CDL); SC_A 12.89 → 12.58 /
    12.10; SC 13.93 → 13.60 / 13.25.
  - This is one year and enters no choice.
- **Pre-registered expectations:**
  - E1 (no P share candidate adopted), E2 (K0 at least 1 point worse) and E5 (P and CDL within 0.5) held.
  - E3 failed: K1 is also clearly worse (+1.6 to +2.6, not within ±1).
  - E4 failed narrowly: A-S3+stress (P) is +0.32, above the 0.3 band. None was adopted, as expected.

## 3. Grids (2017-2024 means; the user's format)

How to read the cells:
- Each cell is **WAPE15 % / |TOT15| %** (15-state WAPE / absolute 15-state total error), or **WAPE15 / |US48|** in
  the US grids. Lower is better.
- **Bold** marks the lowest WAPE and the lowest total error of each row, each on its own.
- `*` means the satellite term was unavailable in every state-year of the cell (the cell equals its base). `*n`
  means it was unavailable in n of the 120 state-years.
- The `*` cases:
  - Jul has no share, and Jul/Aug have no stress, so those cells are all fallback.
  - Under P, 2017 always falls back (15 state-years), because the 2016 P share is UNCOMPUTED; Aug adds 5
    assessability fallbacks.
  - Under CDL, Aug has 21 fallbacks, Sep 5, and Oct-Dec 1 (Michigan 2016 → 2017).
- `(F)` / `(3/8 F)` means A-S3 itself ran its no-FSA fallback (monthly harness: no FSA file by 15 Jul in any year,
  and none by 15 Aug in 2022-2024).
- In the averages, `*` marks an average that contains an all-fallback date.
- SC, SC_A and SC_B at Jul/Aug/Dec are regenerated with their owners' code (gate G2). By construction, SC = SC_B
  at Jul (no NASS yield forecast yet), and Dec = Nov for all three.
- "SC_A+sat best" is K1, which has the lower 15 Nov WAPE15 under P (14.02 against 14.09). This is a display choice
  only.

### 3.1 Tier A family, real-time mask P (`out/grid_tierA.csv`)

| Date | A-S3 | A-S3+sat K0 | A-S3+sat K1 | A-S3+stress | SC_A | SC_A+sat best (K1) | SC_A+stress | reversion | persistence |
|---|---|---|---|---|---|---|---|---|---|
| Jul 15 | 12.25 / 4.56 (F) | 12.25 / 4.56 * (F) | 12.25 / 4.56 * (F) | 12.25 / 4.56 * (F) | **11.93** / **4.24** | **11.93** / **4.24** * | **11.93** / **4.24** * | 12.29 / 4.69 | 13.53 / 4.34 |
| Aug 15 | 12.37 / 5.18 (3/8 F) | 15.52 / 9.40 *20 (3/8 F) | 12.63 / 5.22 *20 (3/8 F) | 12.37 / 5.18 * (3/8 F) | **11.64** / **4.00** | 11.83 / 4.17 *20 | **11.64** / **4.00** * | 12.29 / 4.69 | 13.53 / 4.34 |
| Sep 15 | 11.88 / 4.89 | 17.13 / 11.15 *15 | 12.08 / 4.48 *15 | 12.13 / 4.85 *15 | **11.67** / **3.94** | 12.07 / 4.10 *15 | 11.93 / 4.35 *15 | 12.29 / 4.69 | 13.53 / 4.34 |
| Oct 15 | 11.85 / 4.89 | 13.91 / 5.07 *15 | 13.35 / 5.67 *15 | 12.11 / 4.85 *15 | **11.71** / **3.91** | 13.56 / 5.97 *15 | 11.97 / 4.32 *15 | 12.29 / 4.69 | 13.53 / 4.34 |
| Nov 15 | 11.75 / 4.81 | 14.29 / 6.10 *15 | 13.98 / 6.56 *15 | 12.07 / 4.77 *15 | **11.71** / **3.91** | 14.02 / 6.80 *15 | 11.97 / 4.32 *15 | 12.29 / 4.69 | 13.53 / 4.34 |
| Dec 15 | 11.73 / 4.77 | 14.30 / 5.95 *15 | 14.01 / 6.42 *15 | 12.07 / 4.77 *15 | **11.71** / **3.91** | 14.05 / 6.69 *15 | 11.97 / 4.32 *15 | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Jul-Dec | 11.97 / 4.85 | 14.57 / 7.04 * | 13.05 / 5.48 * | 12.17 / 4.83 * | **11.73** / **3.99** | 12.91 / 5.33 * | 11.90 / 4.26 * | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Aug-Dec | 11.91 / 4.91 | 15.03 / 7.53 | 13.21 / 5.67 | 12.15 / 4.88 * | **11.69** / **3.93** | 13.11 / 5.55 | 11.89 / 4.26 * | 12.29 / 4.69 | 13.53 / 4.34 |

### 3.2 SC family, real-time mask P (`out/grid_sc.csv`)

| Date | SC | SC+sat K0 | SC+sat K1 | SC+stress | SC_B | reversion | persistence |
|---|---|---|---|---|---|---|---|
| Jul 15 | **12.24** / 4.51 | **12.24** / 4.51 * | **12.24** / 4.51 * | **12.24** / 4.51 * | **12.24** / 4.51 | 12.29 / 4.69 | 13.53 / **4.34** |
| Aug 15 | **12.09** / **4.33** | 15.10 / 8.98 *20 | 12.28 / 4.38 *20 | **12.09** / **4.33** * | 12.11 / 4.38 | 12.29 / 4.69 | 13.53 / 4.34 |
| Sep 15 | **12.08** / 4.34 | 16.53 / 10.26 *15 | 12.42 / **4.08** *15 | 12.13 / 4.31 *15 | 12.11 / 4.34 | 12.29 / 4.69 | 13.53 / 4.34 |
| Oct 15 | **12.09** / 4.16 | 13.74 / 4.33 *15 | 13.28 / 5.03 *15 | 12.15 / **4.11** *15 | **12.09** / 4.21 | 12.29 / 4.69 | 13.53 / 4.34 |
| Nov 15 | **12.07** / 4.10 | 14.00 / 5.35 *15 | 13.67 / 5.87 *15 | 12.13 / **4.05** *15 | 12.08 / 4.13 | 12.29 / 4.69 | 13.53 / 4.34 |
| Dec 15 | **12.07** / 4.10 | 14.08 / 5.26 *15 | 13.77 / 5.75 *15 | 12.13 / **4.05** *15 | 12.08 / 4.13 | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Jul-Dec | **12.11** / 4.26 | 14.28 / 6.45 * | 12.94 / 4.94 * | 12.15 / **4.23** * | 12.12 / 4.28 | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Aug-Dec | **12.08** / 4.21 | 14.69 / 6.84 | 13.08 / 5.02 | 12.13 / **4.17** * | 12.09 / 4.24 | 12.29 / 4.69 | 13.53 / 4.34 |

### 3.3 Tier A family, WAPE15 / |US48| (the other 33 states keep the base; `out/grid_tierA_us48.csv`)

| Date | A-S3 | A-S3+sat K0 | A-S3+sat K1 | A-S3+stress | SC_A | SC_A+sat best (K1) | SC_A+stress | reversion | persistence |
|---|---|---|---|---|---|---|---|---|---|
| Jul 15 | 12.25 / **3.73** (F) | 12.25 / **3.73** * (F) | 12.25 / **3.73** * (F) | 12.25 / **3.73** * (F) | **11.93** / 4.01 | **11.93** / 4.01 * | **11.93** / 4.01 * | 12.29 / 3.90 | 13.53 / 4.08 |
| Aug 15 | 12.37 / 4.32 (3/8 F) | 15.52 / 8.07 *20 (3/8 F) | 12.63 / 4.35 *20 (3/8 F) | 12.37 / 4.32 * (3/8 F) | **11.64** / **3.74** | 11.83 / 3.88 *20 | **11.64** / **3.74** * | 12.29 / 3.90 | 13.53 / 4.08 |
| Sep 15 | 11.88 / 4.09 | 17.13 / 9.05 *15 | 12.08 / 4.13 *15 | 12.13 / 4.30 *15 | **11.67** / **3.68** | 12.07 / 3.82 *15 | 11.93 / 4.01 *15 | 12.29 / 3.90 | 13.53 / 4.08 |
| Oct 15 | 11.85 / 4.09 | 13.91 / 4.28 *15 | 13.35 / 5.03 *15 | 12.11 / 4.30 *15 | **11.71** / **3.65** | 13.56 / 5.24 *15 | 11.97 / 3.97 *15 | 12.29 / 3.90 | 13.53 / 4.08 |
| Nov 15 | 11.75 / 4.02 | 14.29 / 5.12 *15 | 13.98 / 5.71 *15 | 12.07 / 4.26 *15 | **11.71** / **3.65** | 14.02 / 5.94 *15 | 11.97 / 3.97 *15 | 12.29 / 3.90 | 13.53 / 4.08 |
| Dec 15 | 11.73 / 3.97 | 14.30 / 5.03 *15 | 14.01 / 5.60 *15 | 12.07 / 4.30 *15 | **11.71** / **3.65** | 14.05 / 5.84 *15 | 11.97 / 3.97 *15 | 12.29 / 3.90 | 13.53 / 4.08 |
| Average Jul-Dec | 11.97 / 4.04 | 14.57 / 5.88 * | 13.05 / 4.76 * | 12.17 / 4.20 * | **11.73** / **3.73** | 12.91 / 4.79 * | 11.90 / 3.95 * | 12.29 / 3.90 | 13.53 / 4.08 |
| Average Aug-Dec | 11.91 / 4.10 | 15.03 / 6.31 | 13.21 / 4.96 | 12.15 / 4.30 * | **11.69** / **3.67** | 13.11 / 4.94 | 11.89 / 3.93 * | 12.29 / 3.90 | 13.53 / 4.08 |

The base |US48| values reproduce the monthly harness and silage_combos 48-state US errors: A-S3 3.73 (Jul) and
4.02 (Nov), reversion 3.90, persistence 4.08, SC 3.34.

### 3.4 SC family, WAPE15 / |US48| (`out/grid_sc_us48.csv`)

| Date | SC | SC+sat K0 | SC+sat K1 | SC+stress | SC_B | reversion | persistence |
|---|---|---|---|---|---|---|---|
| Jul 15 | **12.24** / **3.69** | **12.24** / **3.69** * | **12.24** / **3.69** * | **12.24** / **3.69** * | **12.24** / **3.69** | 12.29 / 3.90 | 13.53 / 4.08 |
| Aug 15 | **12.09** / 3.64 | 15.10 / 7.58 *20 | 12.28 / 3.78 *20 | **12.09** / 3.64 * | 12.11 / **3.59** | 12.29 / 3.90 | 13.53 / 4.08 |
| Sep 15 | **12.08** / 3.51 | 16.53 / 8.09 *15 | 12.42 / 3.65 *15 | 12.13 / 3.83 *15 | 12.11 / **3.47** | 12.29 / 3.90 | 13.53 / 4.08 |
| Oct 15 | **12.09** / **3.37** | 13.74 / 3.62 *15 | 13.28 / 4.30 *15 | 12.15 / 3.66 *15 | **12.09** / 3.42 | 12.29 / 3.90 | 13.53 / 4.08 |
| Nov 15 | **12.07** / **3.34** | 14.00 / 4.37 *15 | 13.67 / 4.96 *15 | 12.13 / 3.60 *15 | 12.08 / 3.36 | 12.29 / 3.90 | 13.53 / 4.08 |
| Dec 15 | **12.07** / **3.34** | 14.08 / 4.30 *15 | 13.77 / 4.86 *15 | 12.13 / 3.60 *15 | 12.08 / 3.36 | 12.29 / 3.90 | 13.53 / 4.08 |
| Average Jul-Dec | **12.11** / **3.48** | 14.28 / 5.28 * | 12.94 / 4.20 * | 12.15 / 3.67 * | 12.12 / **3.48** | 12.29 / 3.90 | 13.53 / 4.08 |
| Average Aug-Dec | **12.08** / **3.44** | 14.69 / 5.59 | 13.08 / 4.31 | 12.13 / 3.67 * | 12.09 / **3.44** | 12.29 / 3.90 | 13.53 / 4.08 |

### 3.5 CDL mask (reference, not real time: the year's CDL is published after the season)

Tier A family (`out/grid_tierA_cdl.csv`):

| Date | A-S3 | A-S3+sat K0 (CDL) | A-S3+sat K1 (CDL) | A-S3+stress (CDL) | SC_A | SC_A+sat best (K1) (CDL) | SC_A+stress (CDL) | reversion | persistence |
|---|---|---|---|---|---|---|---|---|---|
| Jul 15 | 12.25 / 4.56 (F) | 12.25 / 4.56 * (F) | 12.25 / 4.56 * (F) | 12.25 / 4.56 * (F) | **11.93** / **4.24** | **11.93** / **4.24** * | **11.93** / **4.24** * | 12.29 / 4.69 | 13.53 / 4.34 |
| Aug 15 | 12.37 / 5.18 (3/8 F) | 16.17 / 9.58 *21 (3/8 F) | 12.82 / 5.28 *21 (3/8 F) | 12.37 / 5.18 * (3/8 F) | **11.64** / **4.00** | 12.10 / 4.26 *21 | **11.64** / **4.00** * | 12.29 / 4.69 | 13.53 / 4.34 |
| Sep 15 | 11.88 / 4.89 | 17.71 / 11.76 *5 | 12.41 / 4.47 *5 | 11.98 / 5.09 | **11.67** / **3.94** | 12.32 / 4.06 *5 | 11.69 / 4.42 | 12.29 / 4.69 | 13.53 / 4.34 |
| Oct 15 | 11.85 / 4.89 | 14.67 / 6.30 *1 | 13.66 / 5.33 *1 | 11.95 / 5.09 | **11.71** / **3.91** | 13.89 / 5.40 *1 | 11.74 / 4.39 | 12.29 / 4.69 | 13.53 / 4.34 |
| Nov 15 | 11.75 / 4.81 | 14.62 / 6.46 *1 | 14.25 / 6.11 *1 | 11.86 / 5.01 | **11.71** / **3.91** | 14.30 / 6.38 *1 | 11.74 / 4.39 | 12.29 / 4.69 | 13.53 / 4.34 |
| Dec 15 | 11.73 / 4.77 | 14.59 / 6.42 *1 | 14.23 / 6.10 *1 | 11.86 / 4.96 | **11.71** / **3.91** | 14.30 / 6.38 *1 | 11.74 / 4.39 | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Jul-Dec | 11.97 / 4.85 | 15.00 / 7.51 * | 13.27 / 5.31 * | 12.05 / 4.98 * | **11.73** / **3.99** | 13.14 / 5.12 * | 11.75 / 4.31 * | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Aug-Dec | 11.91 / 4.91 | 15.55 / 8.11 | 13.47 / 5.46 | 12.00 / 5.07 * | **11.69** / **3.93** | 13.38 / 5.30 | 11.71 / 4.32 * | 12.29 / 4.69 | 13.53 / 4.34 |

SC family (`out/grid_sc_cdl.csv`):

| Date | SC | SC+sat K0 (CDL) | SC+sat K1 (CDL) | SC+stress (CDL) | SC_B | reversion | persistence |
|---|---|---|---|---|---|---|---|
| Jul 15 | **12.24** / 4.51 | **12.24** / 4.51 * | **12.24** / 4.51 * | **12.24** / 4.51 * | **12.24** / 4.51 | 12.29 / 4.69 | 13.53 / **4.34** |
| Aug 15 | **12.09** / **4.33** | 15.77 / 9.21 *21 | 12.51 / 4.45 *21 | **12.09** / **4.33** * | 12.11 / 4.38 | 12.29 / 4.69 | 13.53 / 4.34 |
| Sep 15 | 12.08 / 4.34 | 17.12 / 10.84 *5 | 12.68 / **4.04** *5 | **11.91** / 4.54 | 12.11 / 4.34 | 12.29 / 4.69 | 13.53 / 4.34 |
| Oct 15 | 12.09 / **4.16** | 14.44 / 5.56 *1 | 13.75 / 4.73 *1 | **11.91** / 4.36 | 12.09 / 4.21 | 12.29 / 4.69 | 13.53 / 4.34 |
| Nov 15 | 12.07 / **4.10** | 14.41 / 5.71 *1 | 14.12 / 5.44 *1 | **11.89** / 4.30 | 12.08 / 4.13 | 12.29 / 4.69 | 13.53 / 4.34 |
| Dec 15 | 12.07 / **4.10** | 14.40 / 5.72 *1 | 14.12 / 5.44 *1 | **11.89** / 4.30 | 12.08 / 4.13 | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Jul-Dec | 12.11 / **4.26** | 14.73 / 6.92 * | 13.24 / 4.77 * | **11.99** / 4.39 * | 12.12 / 4.28 | 12.29 / 4.69 | 13.53 / 4.34 |
| Average Aug-Dec | 12.08 / **4.21** | 15.23 / 7.41 | 13.44 / 4.82 | **11.94** / 4.36 * | 12.09 / 4.24 | 12.29 / 4.69 | 13.53 / 4.34 |

What the grids show:
- The share candidates are worst on 15 Sep (K0 +4.5 to +5.8 points). A plausible reason, not tested here: at an
  early-harvest cut date the share mostly reflects how far harvest or senescence has progressed.
- K1 is nearly neutral at Aug/Sep (+0.2 to +0.7) but degrades by Oct-Dec. K0 is bad at every date.
- The stress candidates equal their bases at Jul/Aug (no index yet) and are flat from Sep to Dec, because one
  Sep 15 value is used.

## 4. Decision at 15 Nov, 2017-2024 (`out/decision.csv`)

The table gives:
- the paired differences, candidate minus base (negative = candidate better), in points;
- their SE over 8 years and the bootstrap 90% CIs of the mean WAPE15 difference (seed 20261115);
- years better/worse/tied and per-state wins/losses (sum of |error| over the 8 years).

Under P, 2017 is always a tie, because its satellite term is unavailable.

| Candidate | Base | WAPE15 c / base | d WAPE (SE) | +2 SE | d abs TOT15 (SE) | +2 SE | 90% CI years (WAPE) | 90% CI states (WAPE) | 90% CI joint (WAPE) | years better/worse/tied | state wins/losses | Result |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-S3+sat K0 | AS3 | 14.29 / 11.75 | +2.54 (0.87) | +4.27 | +1.29 (0.96) | +3.21 | [+1.21, +3.90] | [+1.60, +3.66] | [+0.71, +4.53] | 0/7/1 | 2/13 | not adopted |
| A-S3+sat K1 | AS3 | 13.98 / 11.75 | +2.23 (0.89) | +4.01 | +1.75 (1.25) | +4.26 | [+0.96, +3.72] | [+0.98, +3.49] | [+0.25, +4.31] | 1/6/1 | 3/12 | not adopted |
| A-S3+stress | AS3 | 12.07 / 11.75 | +0.32 (0.17) | +0.67 | -0.04 (0.48) | +0.91 | [+0.07, +0.59] | [-0.13, +0.72] | [-0.31, +0.93] | 2/5/1 | 8/7 | not adopted |
| SC_A+sat K0 | SCA | 14.09 / 11.71 | +2.38 (0.79) | +3.97 | +2.14 (0.63) | +3.40 | [+1.17, +3.64] | [+1.61, +3.28] | [+0.72, +4.31] | 1/6/1 | 1/14 | not adopted |
| SC_A+sat K1 | SCA | 14.02 / 11.71 | +2.31 (0.79) | +3.89 | +2.90 (1.17) | +5.23 | [+1.18, +3.61] | [+1.15, +3.57] | [+0.51, +4.43] | 0/7/1 | 3/12 | not adopted |
| SC_A+stress | SCA | 11.97 / 11.71 | +0.26 (0.22) | +0.70 | +0.41 (0.46) | +1.34 | [-0.10, +0.58] | [-0.35, +0.82] | [-0.54, +1.05] | 2/5/1 | 7/8 | not adopted |
| SC+sat K0 | SC | 14.00 / 12.07 | +1.93 (0.77) | +3.46 | +1.25 (0.95) | +3.14 | [+0.80, +3.17] | [+1.10, +2.89] | [+0.31, +3.76] | 1/6/1 | 2/13 | not adopted |
| SC+sat K1 | SC | 13.67 / 12.07 | +1.60 (0.59) | +2.78 | +1.77 (1.23) | +4.23 | [+0.75, +2.57] | [+0.36, +2.83] | [-0.12, +3.44] | 1/6/1 | 4/11 | not adopted |
| SC+stress | SC | 12.13 / 12.07 | +0.07 (0.22) | +0.50 | -0.05 (0.48) | +0.92 | [-0.27, +0.40] | [-0.46, +0.54] | [-0.69, +0.79] | 3/4/1 | 7/8 | not adopted |
| A-S3+sat K0 (CDL) | AS3 | 14.62 / 11.75 | +2.88 (0.86) | +4.59 | +1.65 (0.99) | +3.62 | [+1.58, +4.24] | [+1.76, +4.16] | [+1.00, +4.96] | 0/8/0 | 3/12 | reference: would not pass |
| A-S3+sat K1 (CDL) | AS3 | 14.25 / 11.75 | +2.51 (0.64) | +3.78 | +1.30 (1.23) | +3.75 | [+1.59, +3.55] | [+1.21, +3.78] | [+0.72, +4.44] | 0/8/0 | 4/11 | reference: would not pass |
| A-S3+stress (CDL) | AS3 | 11.86 / 11.75 | +0.12 (0.18) | +0.48 | +0.20 (0.43) | +1.06 | [-0.18, +0.39] | [-0.37, +0.53] | [-0.55, +0.75] | 2/6/0 | 5/10 | reference: would not pass |
| SC_A+sat K0 (CDL) | SCA | 14.43 / 11.71 | +2.72 (0.86) | +4.45 | +2.19 (0.61) | +3.42 | [+1.40, +4.07] | [+1.82, +3.78] | [+0.92, +4.81] | 1/7/0 | 0/15 | reference: would not pass |
| SC_A+sat K1 (CDL) | SCA | 14.30 / 11.71 | +2.60 (0.78) | +4.16 | +2.47 (0.97) | +4.42 | [+1.48, +3.89] | [+1.58, +3.73] | [+0.95, +4.63] | 0/8/0 | 2/13 | reference: would not pass |
| SC_A+stress (CDL) | SCA | 11.74 / 11.71 | +0.03 (0.23) | +0.48 | +0.48 (0.41) | +1.31 | [-0.33, +0.36] | [-0.60, +0.60] | [-0.81, +0.79] | 3/5/0 | 10/5 | reference: would not pass |
| SC+sat K0 (CDL) | SC | 14.41 / 12.07 | +2.34 (0.87) | +4.09 | +1.61 (0.98) | +3.56 | [+1.05, +3.76] | [+1.45, +3.43] | [+0.53, +4.41] | 1/7/0 | 1/14 | reference: would not pass |
| SC+sat K1 (CDL) | SC | 14.12 / 12.07 | +2.05 (0.56) | +3.17 | +1.34 (1.21) | +3.76 | [+1.24, +2.97] | [+0.84, +3.24] | [+0.43, +3.89] | 0/8/0 | 4/11 | reference: would not pass |
| SC+stress (CDL) | SC | 11.89 / 12.07 | -0.18 (0.22) | +0.26 | +0.20 (0.44) | +1.08 | [-0.53, +0.15] | [-0.73, +0.31] | [-0.96, +0.52] | 4/4/0 | 9/6 | reference: would not pass |

The 90% CIs of the |TOT15| difference (years / states / joint) are in `out/decision.csv`. Every share candidate's
CI is centred well above 0. For example, SC_A+sat K1 has [+1.09, +4.70] / [+0.97, +4.22] / [+0.01, +5.31]. Every
stress candidate's CI straddles 0, for example SC+stress [-0.80, +0.68] / [-0.65, +0.74] / [-0.96, +1.08].

Information windows (`out/comparisons.csv`):
- 2018-2024, the years with a P change, at 15 Nov: the share candidates are +1.82 to +2.90 points worse, and P
  stress is +0.07 to +0.37.
- SC+stress (CDL) at -0.31 (+2 SE +0.11) is the closest any candidate comes to the rule.
- No candidate passes at any of the six dates in either window.

## 5. Robustness (`out/robustness.csv`; P candidates, 15 Nov)

The rule was re-applied with each year left out (8 runs) and each state left out (15 runs). No run passes for
any P candidate (0 of 23 each).

| Candidate | d WAPE15 range over the 23 runs | smallest d + 2 SE |
|---|---|---|
| A-S3+sat K0 / K1 | +2.09 to +2.90 / +1.53 to +2.59 | +3.80 / +2.77 |
| SC_A+sat K0 / K1 | +1.96 to +2.75 / +1.67 to +2.70 | +3.51 / +2.76 |
| SC+sat K0 / K1 | +1.45 to +2.21 / +1.15 to +1.94 | +2.85 / +2.03 |
| A-S3+stress / SC_A+stress / SC+stress | +0.12 to +0.50 / +0.09 to +0.43 / -0.12 to +0.21 | +0.45 / +0.54 / +0.33 |

## 6. Each year at 15 Nov (WAPE15 / signed TOT15; P mask; 2025 information only)

| Year | A-S3 | A-S3+sat K0 | A-S3+sat K1 | A-S3+stress | SC_A | SC_A+sat K1 | SC_A+stress | SC | SC+sat K1 | SC+stress |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | 9.50 / -1.92 | 9.50 / -1.92 | 9.50 / -1.92 | 9.50 / -1.92 | 9.26 / -1.41 | 9.26 / -1.41 | 9.26 / -1.41 | 9.59 / -2.05 | 9.59 / -2.05 | 9.59 / -2.05 |
| 2018 | 19.12 / +4.33 | 24.80 / +5.42 | 20.56 / +2.05 | 20.04 / +5.43 | 18.44 / +3.66 | 19.38 / +1.31 | 19.24 / +4.78 | 18.98 / +3.89 | 19.77 / +1.57 | 19.76 / +4.99 |
| 2019 | 14.91 / -8.28 | 15.01 / -12.68 | 14.62 / -11.04 | 16.02 / -10.09 | 15.28 / -7.53 | 15.40 / -10.29 | 16.26 / -9.42 | 15.55 / -6.94 | 15.40 / -9.73 | 16.53 / -8.83 |
| 2020 | 6.71 / -2.08 | 7.21 / -4.20 | 8.17 / -3.85 | 6.38 / +0.00 | 8.21 / -4.32 | 9.49 / -6.00 | 7.34 / -2.21 | 8.76 / -4.30 | 9.80 / -6.00 | 7.93 / -2.22 |
| 2021 | 10.96 / -2.29 | 16.15 / -1.02 | 12.80 / +3.16 | 10.94 / -0.53 | 8.67 / +0.34 | 12.03 / +6.01 | 9.23 / +2.15 | 10.44 / -2.00 | 12.30 / +3.49 | 10.49 / -0.24 |
| 2022 | 12.85 / -9.17 | 14.40 / -10.66 | 17.61 / -13.97 | 13.27 / -10.01 | 13.62 / -7.79 | 16.71 / -12.35 | 13.28 / -8.61 | 13.43 / -7.83 | 16.72 / -12.60 | 13.11 / -8.66 |
| 2023 | 9.18 / +5.53 | 14.41 / +10.83 | 16.36 / +13.78 | 9.41 / +5.68 | 9.68 / +3.82 | 16.45 / +12.07 | 10.03 / +3.95 | 9.16 / +0.84 | 13.90 / +8.84 | 8.72 / +0.89 |
| 2024 | 10.77 / +4.88 | 12.82 / -2.07 | 12.22 / -2.71 | 11.00 / +4.48 | 10.49 / +2.39 | 13.41 / -5.01 | 11.09 / +1.99 | 10.64 / +4.96 | 11.84 / -2.69 | 10.96 / +4.53 |
| 2025 (info) | 15.21 / +4.97 | 21.04 / +10.27 | 17.48 / +6.98 | 14.97 / +3.89 | 12.89 / +1.58 | 14.64 / +3.44 | 12.58 / +0.57 | 13.93 / +3.02 | 15.77 / +4.96 | 13.60 / +1.99 |

The share factor's worst years:
- 2022: the K1 share falls, so the 15-state totals sink a further 4.6-4.8 points. 2022 uses Planetary Computer
  imagery.
- 2023: the share rises, and the K1 totals reach +8.8% to +13.8%.

My reading, not tested: the shares agent's common year effect (SD 0.17) shows up here as whole-year jumps in every
state at once.

## 7. 2025, information only (`out/info_2025.csv`; scored once, used for nothing)

The 2025 bases are regenerated with their owners' code (gates G1 and G2), and P for 2025 is the real-time replay
(trained on 2016-2024). Cells are WAPE15 / |TOT15| / |US48|.

| Model | Sep 15 | Nov 15 |
|---|---|---|
| A-S3 | 15.21 / 4.97 / 4.04 | 15.21 / 4.97 / 4.04 |
| A-S3+sat K0 | 16.02 / 5.37 / 4.36 | 21.04 / 10.27 / 8.28 |
| A-S3+sat K1 | 14.95 / 5.89 / 4.78 | 17.48 / 6.98 / 5.65 |
| A-S3+stress | 14.97 / 3.89 / 3.18 | 14.97 / 3.89 / 3.18 |
| SC_A | 12.97 / 1.76 / 1.32 | 12.89 / 1.58 / 1.19 |
| SC_A+sat K0 | 13.52 / 2.15 / 1.64 | 17.84 / 6.48 / 5.11 |
| SC_A+sat K1 | 12.29 / 2.66 / 2.04 | 14.64 / 3.44 / 2.68 |
| SC_A+stress | 12.66 / 0.75 / 0.51 | 12.58 / 0.57 / 0.38 |
| SC | 14.06 / 3.08 / 2.25 | 13.93 / 3.02 / 2.19 |
| SC+sat K0 | 14.67 / 3.54 / 2.62 | 19.15 / 8.18 / 6.32 |
| SC+sat K1 | 13.38 / 3.98 / 2.97 | 15.77 / 4.96 / 3.74 |
| SC+stress | 13.73 / 2.05 / 1.42 | 13.60 / 1.99 / 1.36 |
| SC_B | 14.09 / 3.11 / 2.25 | 13.90 / 2.99 / 2.06 |
| reversion | 15.22 / 3.85 / 3.06 | 15.22 / 3.85 / 3.06 |
| persistence | 14.65 / 0.51 / 0.32 | 14.65 / 0.51 / 0.32 |
| A-S3+stress (CDL) | 14.83 / 3.25 / 2.67 | 14.83 / 3.25 / 2.67 |
| SC_A+stress (CDL) | 12.19 / 0.11 / 0.00 | 12.10 / 0.07 / 0.13 |
| SC+stress (CDL) | 13.37 / 1.40 / 0.90 | 13.25 / 1.34 / 0.85 |

For 2025:
- The stress candidates improve every base on all three metrics, under both masks.
- At 15 Sep, K1 improves WAPE15 (SC_A 12.97 → 12.29) but worsens the total. At 15 Nov every share candidate is
  worse.
- One year cannot support adoption: on 2017-2024 the stress gain is not there.
- 2025 was not used to choose anything.

The regenerated 2025 reversion matches the stored `data/models/state_score_2025_reversion_only.csv` within its
100-acre rounding (max 45 acres; truth identical; `out/run.json`).

## 8. 2026

- **No ADOPTED candidate, so no satellite 2026 forecast and no widened interval are issued** (section 1.8). The
  existing 2026 forecasts of the bases (silage_combos `forecast_2026.csv`, the A-S3 and SC folders) stand unchanged.
- Information only (`out/info_2026_by_state.csv`, `out/info_2026_totals.csv`): what the P candidates would have
  said at 15 Nov 2026. The P shares and stress for 2026 are available in all 15 states.

| Model (not adopted) | 15-state total | its base | change | US48 total | base US48 |
|---|---|---|---|---|---|
| A-S3+sat K0 / K1 / stress | 5.574M / 5.439M / 5.126M | 5.051M | +10.4% / +7.7% / +1.5% | 6.821M / 6.686M / 6.372M | 6.298M |
| SC_A+sat K0 / K1 / stress | 5.721M / 5.583M / 5.244M | 5.166M | +10.8% / +8.1% / +1.5% | 6.983M / 6.846M / 6.506M | 6.428M |
| SC+sat K0 / K1 / stress | 5.548M / 5.414M / 5.104M | 5.028M | +10.3% / +7.7% / +1.5% | 6.779M / 6.645M / 6.259M | 6.259M |

- The 2026 share factors (r^0.5) are largest in Nebraska (1.36), South Dakota (1.25 K0 / 1.14 K1), Iowa (1.25 /
  1.26), Minnesota (1.16) and Michigan (1.14 / 1.08).
- The shares agent read the matching 2025→2026 share jumps as a 2026 year effect or a corn-mask transfer failure.
- The stress factor is largest in Colorado (1.19), Texas (1.18) and California (1.11). These are states where the
  P corn mask fails (corn_mask, stress reports).

## 9. Checks (`out/gates.json`, `out/run.json`)

| Gate | Result |
|---|---|
| G0 truth | monthly `actual` = A-S3 `load_nass_finals()` = silage_combos `actual` on 384 state-years 2017-2024 (max diff 0); 48 states in every cell; all 15 states present; 48 states with 2025 truth |
| G1 A-S3 / reversion / persistence regenerated (six dates) vs monthly file, 2017-2024 | 6,912 rows, max diff 0.05 acre (the file keeps 1 decimal): pass, so the 2025 values are used |
| G2 SC / SC_A / SC_B regenerated vs silage_combos, Sep/Oct/Nov 2017-2024 and 2026 | 3,888 rows, max diff 0.05 acre: pass, so the Jul/Aug/Dec and 2025 values are used |
| G2 by construction | SC = SC_B at Jul, Dec = Nov for SC, SC_B and SC_A: max diff 0 |
| Pre-registration hash | unchanged at every step |

No `__pycache__` is written outside this folder (bytecode off); a search for `.pyc` files newer than the hash found
none.

## 10. Limitations

- Only 8 scored years and 15 states. Under P, only 7 years carry a satellite change (2017 falls back). The SEs and
  bootstraps are coarse, and the 18 tests have no multiplicity correction. The failure of the share candidates is
  large and consistent, so this does not change the reading.
- Truth is NASS's final state numbers, which carry their own noise. About 10 of the 13 points of 48-state WAPE are
  NASS series noise (`test_models/accuracy/noise_floor`), which bounds what any signal can gain.
- The shares and stress are taken as delivered by the shares and stress agents (K0, K1, P mask). I did not re-run
  them. Their limitations apply here:
  - the imagery-source shift in 2016-2018 and 2022;
  - 2016 has Sentinel-2A only;
  - the field-id edition change between 2017 and 2018;
  - P fails in TX, CO and KS.
- Aug cut dates are pre-harvest (shares report). The Aug cells use the share wherever its status is `ok`, as
  pre-registered.
- The exponent 0.5, the clip [0.5, 2] and the stress slope 0.05 are fixed by the task and earlier rounds, not
  tuned. A smaller exponent would shrink the damage but cannot help when the share change is uncorrelated or
  anti-correlated with the miss (section 2).
- SC is Tier C (it uses NASS in-season grain-acre forecasts) and SC_B is Tier B. Only A-S3, SC_A and reversion are
  Tier A. SC_A's 15-state advantage over A-S3 on WAPE is small (11.71 against 11.75 at 15 Nov).
- 2025 is scored once as information. Its bases are regenerated, because the stored harness files stop at 2024.

## 11. How to run and files

```
.venv/Scripts/python.exe -B test_models/variations/sat_full/eval/eval.py all --workers 6     # about 50 s
.venv/Scripts/python.exe -m ruff check --select E,F,W --line-length 120 test_models/variations/sat_full/eval/
```

The steps are `prereg | bases | score | all`. `bases` caches `out/cache/bases.parquet`; rerun it with `--force`.
Every step stops if section 1 no longer matches `out/preregistration.sha256`.

| File | Content |
|---|---|
| `out/preregistration.sha256` | hash of section 1 |
| `out/gates.json`, `out/run.json` | gates, expectations E1-E5, the reversion 2025 cross-check, timing |
| `out/cache/bases.parquet`, `as3_fsa_fallback.csv`, `sc_regen_params.csv` | base table (48 states, 2017-2025 + 2026 Sep-Nov) with source per row; A-S3 FSA-fallback flags; regenerated SC alpha/gamma |
| `out/predictions_by_state_year.csv` | every base (48 states) and candidate (15 states) per date and year, with factor and availability |
| `out/by_year.csv` | WAPE15, TOT15, US48, WAPE48 and fallback states per model, date and year (2017-2025) |
| `out/summary.csv` | means per model and date plus the two averages, for 2017-2024 and 2018-2024 |
| `out/decision.csv`, `out/comparisons.csv` | 15 Nov rule with CIs; all dates and both windows (information) |
| `out/robustness.csv` | drop-one-year and drop-one-state reruns of the rule (P candidates) |
| `out/grid_tierA.csv`, `grid_sc.csv`, `grid_tierA_us48.csv`, `grid_sc_us48.csv`, `grid_tierA_cdl.csv`, `grid_sc_cdl.csv` | the grids of section 3 |
| `out/info_2025.csv` | 2025 information scores |
| `out/info_2026_by_state.csv`, `out/info_2026_totals.csv` | 2026 values of the P candidates next to their bases (not adopted) |
| `out/diag_factor_vs_residual.csv` | not pre-registered: correlation and size of the log factor against the base's log miss |
