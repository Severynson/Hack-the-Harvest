# Silage combinations: A-S3 state split + smoothed_chopping US total

Owner key: `silage_combos`. Folder: `test_models/variations/silage_combos/`. Code: `run.py`. Tests: `test_run.py`.
Outputs: `out/`. Nothing outside this folder is written (Python bytecode writing is switched off so that importing
the other folders' modules leaves no `__pycache__` behind).

Goal: one state corn-for-silage forecast that keeps the state split of Tier A `s3_fsa_residual` (A-S3, best state
WAPE) and the US total of Manraj's delivered `smoothed_chopping` (SC, best US error), on the 48 silage states, as of
15 November, with 15 September and 15 October replays.

---

## 1. Pre-registration (written before any candidate score was computed; not edited afterwards)

This section, from its heading to the end-of-section marker, is hashed into `out/preregistration.sha256` before
the first scored run. `run.py` checks the hash on every run and records the result in `out/run.json`. Later text goes
below the marker; any change of method is listed under "Deviations".

### 1.0 What I had seen before writing this

- A-S3 (`test_models/ownModels/silage/README.md`): 2012-2024 state WAPE 13.72% / mean |US| 4.96% / signed US
  -1.65%; 2017-2024 12.52 / 4.00 (12.53 / 4.02 with the corrected FSA publication dates of
  `test_models/ownModels/monthly/`), and its per-year state WAPE table.
- Tier B c5b (`test_models/ownModels/tierB/silage/`): 12.66 / 3.94 on 2017-2024, 13.80 / 4.94 on 2012-2024 (monthly
  harness, corrected dates).
- SC (`kernelag/silage_level.py`, `DOCS/DECISIONS.md`, `test_models/accuracy/noise_floor/by_year.csv`): 2012-2024
  13.23 / 3.44, 2017-2024 12.80 / 3.34, and its per-year state WAPE and |US| errors.
- Therefore the US error of any candidate whose US total equals SC's (v2) or A-S3's (v3) is known in advance from
  those tables; their state WAPE is not. No score of any combination below, and no 2025 number of any of them.
- Availability (counts only, no errors): A-S3 and c5b have all 48 states in every year 2012-2024 at 15 Sep, Oct and
  Nov (monthly harness); SC predicts all 48 states in every year 2012-2026 at those dates; NASS yield forecasts
  exist for about 33 states per year.

### 1.1 Components and their tiers

| Key | What | Current-year inputs | Tier |
|---|---|---|---|
| `A` = A-S3 `s3_fsa_residual` | `test_models/ownModels/silage/run.py` imported unchanged; `run_asof` with today's `data/fsa` tables (corrected publication dates) | FSA crop acreage files published by the date | A |
| `B` = c5b `c5b_residual_fsa_planted_pre_june` | `test_models/ownModels/tierB/silage/run.py` imported unchanged; `load_all` + `run_asof` | FSA files; NASS in-season planted | B |
| `SC` = `smoothed_chopping` | `kernelag.silage_level.load_history(data/Quickstats Data, asof)` + `predict(history, t)`, imported unchanged | NASS in-season grain-YIELD forecast (Aug-Nov Crop Production) and NASS in-season HARVESTED-FOR-GRAIN forecast (the chopping exposure multiplies the yield shortfall by NASS's grain-acre forecast). No Drought Monitor data despite the name | **C** (NASS-informed: the grain-acre forecast is forbidden even in the Tier B folders' definitions) |
| `SC_B` | SC with the grain acres of the exposure replaced by last year's NASS final grain acres G(t-1): exposure from `chopping_exposure` on a copy of the history whose `grain_asof` table is empty (the module then falls back to G(t-1)); alpha and gamma re-chosen by `predict(history, t, exposure=...)` | NASS yield forecast | B |
| `SC_L` | SC's smoothed level only: `predict(history, t, exposure=0)` (gamma has no effect; the first grid value 0 is taken) | none (NASS finals of earlier years) | A |
| `SC_A` | SC with a Drought Monitor exposure: max(0, D(t) - 0.10) x G(t-1), D = `kernelag.context.drought(usdm, asof)` (mean share of the state in D2 or worse, weekly maps 1 June to the earlier of 30 Sep and the as-of date; missing = 0); TAU 0.10 is SC's constant reused, not tuned; alpha and gamma re-chosen by `predict(history, t, exposure=...)` | US Drought Monitor | A |

A candidate's tier is the highest tier of its components (A < B < C). Chopped acres of a SC variant in year t:
chopped = gamma_t x exposure(t), with gamma_t the value `predict` chose for year t; its base = prediction - chopped
(= exp of the smoothed log level of "normal" acres). `run.py` checks prediction = base + chopped.

Truth S(t): NASS final state silage acres as read by A-S3's `load_nass_finals()` (Quick Stats "YEAR", asserted
identical to `data/nass/corn_acres_state.csv`, the incumbent's truth). Scored states per year: the 48 states with
S(t) and S(t-1) (A-S3's `attach_truth`). Every model below is scored on exactly the same state-years.

### 1.2 Candidates (no fitted weights except v8)

P = primary (named in the task); X = exploratory, added because the user asked to "try other variations". All
sums are over the 48 states of that year. Notation: A_s, B_s, SC_s are the component predictions for state s.

| Key | Role | Tier | Definition |
|---|---|---|---|
| `v1_geo` | P | C | sqrt(A_s x SC_s) |
| `v2_topdown` | P | C | A_s x (sum SC / sum A): A-S3's shares, SC's US total |
| `v3_reverse` | P (control) | C | SC_s x (sum A / sum SC): SC's shares, A-S3's US total (expected worse) |
| `v4_mean3` | P | C | (A_s + B_s + SC_s) / 3 |
| `v5_chopmult` | P | C | A_s x SC_s / SCbase_s = A_s x (1 + chopped_s / base_s): SC's year-t drought-chopping factor applied to A-S3 (factor >= 1; exactly 1 where the shortfall is <= 0.10) |
| `v5b_chopadd` | P (variant of v5) | C | A_s + chopped_s: SC's chopped acres added to A-S3 |
| `v6_topdown_geoUS` | P | C | A_s x sqrt(sum SC x sum A) / sum A: A-S3's shares, US total = geometric mean of the two US totals |
| `v7_mean2` | X | C | (A_s + SC_s) / 2 |
| `v8_geo_fitted` | X | C | A_s^(1-w) x SC_s^w; one pooled w on the grid {0, 0.05, ..., 1} minimizing sum abs(pred - S) over the backtest state-years 2012 <= y < t at the same as-of date (expanding); null w = 0.5 with fewer than 3 training years; the 2026 w uses 2012-2024 only |
| `v9_topdown_SCB` | X | B | A_s x (sum SC_B / sum A) |
| `v10_topdown_SCL` | X | A | A_s x (sum SC_L / sum A) |
| `v11_topdown_SCA` | X | A | A_s x (sum SC_A / sum A) |
| `v12_geo_SCA` | X | A | sqrt(A_s x SC_A_s) |
| `v13_chopmult_SCA` | X | A | A_s x SC_A_s / SC_Abase_s (Tier A analogue of v5) |

References (scored and reported, not candidates): A, B, SC, SC_B, SC_L, SC_A, A-S3's `s0_persistence` and
`s1_reversion_only` (finals from 2000).

### 1.3 Metrics

- Test years 2012-2024 (13, selection period) and 2017-2024 (8, reported). As-of 15 Nov (headline), 15 Oct, 15 Sep.
- Per year: state WAPE = 100 x sum abs(pred - S) / sum S; US error = 100 x (sum pred - sum S) / sum S. Summary: mean
  state WAPE, mean |US|, mean signed US.
- Paired comparisons of every candidate against A and against SC, per as-of date and period: d_y = metric(c, y) -
  metric(ref, y) for state WAPE and for |US|; mean, SE = sd(d, ddof 1) / sqrt(n), mean + 2 SE, years better / worse.
  90% bootstrap intervals of the mean difference: (i) years resampled (10,000, seed 20261114); (ii) states resampled
  as clusters, the same draw in every year (2,000, seed 20261114); (iii) years and states resampled jointly (2,000).

### 1.4 Decision rule (mechanical; 15 Nov, 2012-2024)

A candidate is **RECOMMENDED** if either
- (R1) mean WAPE(c) - mean WAPE(A) <= 0.10 points AND mean(|US(c)| - |US(A)|) + 2 SE < 0; or
- (R2) mean(WAPE(c) - WAPE(SC)) + 2 SE < 0 AND mean |US(c)| - mean |US(SC)| <= 0.10 points.

Descriptive label (not part of the rule): "beats both on point estimates" = mean WAPE(c) <= mean WAPE(A) and mean
|US(c)| <= mean |US(SC)|. Headline: among RECOMMENDED primary candidates, the lowest mean state WAPE (ties within
0.005 points: lower mean |US|). RECOMMENDED exploratory candidates are reported with a multiplicity caveat (13
candidates are tested), and the best RECOMMENDED Tier A candidate is named separately. If none is RECOMMENDED, the
answer is "no combination beats the current best under the rule". The same rule on 2017-2024 and at 15 Sep / 15 Oct
is information only.

### 1.5 Forecasts for 2026

Every candidate (and reference) as of 15 Nov 2026, and as of 15 Sep and 15 Oct 2026 where its components exist on
those dates. 80% intervals from that candidate's own 2012-2024 backtest at the same as-of date: state =
`kernelag.state_model.error_quantiles` / `add_intervals` (10th and 90th percentiles of log(S / pred) in three size
classes of S(t-1)); US = 10th and 90th percentiles of the 13 yearly US log errors, applied to the 2026 US total.
Leave-one-year-out coverage of the state intervals (`kernelag.state_model.interval_coverage`) is reported.

### 1.6 What is never done

No 2025 error of anything is computed; 2025 enters nothing of mine (no fit, interval or choice). The imported
component models fit their own parameters on expanding windows, so their 2026 predictions use 2025 finals as
history, unchanged from their folders. No Maryland data. No git writes. A-S3 and c5b regenerated here are compared
with `test_models/ownModels/monthly/out/monthly_by_state_year.csv` (2012-2024, Sep/Oct/Nov); if any differs by
more than 1 acre, the difference is reported in section 2 and the regenerated values are used. SC regenerated
here is compared with its documented 13.23 / 3.44 (2012-2024) and the stored per-year values of
`data/models/state_model_backtest.csv` (2017-2024).

<!-- END OF PRE-REGISTRATION -->

## 1b. Round-2 pre-registration (post hoc: written after the round-1 scores, before any round-2 score)

This section, from its heading to the round-2 end marker, is hashed into `out/preregistration_round2.sha256` before
the first round-2 run. It does not change section 1, its rule or its headline.

Why a round 2 (round-1 facts, 15 Nov, 2012-2024, `out/summary.csv` and `out/decision.json` of the round-1 run):
the rule recommended v1_geo, v4_mean3, v6_topdown_geoUS (primary) and v7_mean2, v8_geo_fitted (exploratory), all
through R1 and all Tier C; none passed R2. The Tier A reference SC_A (SC with a Drought Monitor exposure) scored
13.24 / 3.52 against SC's 13.23 / 3.45, and the geometric blend with it (v12_geo_SCA, Tier A) had the lowest state
WAPE of all (13.08) but missed R1's US test (+0.046). Every candidate whose US total equals SC's has the same paired
US test against A (+0.013), so it cannot pass R1.

Round-2 candidates (all exploratory and post hoc; the same rule of section 1.4 is applied and reported with a
"post hoc" label; none can replace the round-1 headline):

| Key | Tier | Definition |
|---|---|---|
| `w1_mean2_SCA` | A | (A_s + SC_A_s) / 2 |
| `w2_geo_fitted_SCA` | A | A_s^(1-w) x SC_A_s^w, w fitted exactly as v8 (grid 0..1 by 0.05, 2012 <= y < t, same as-of date, null 0.5 with fewer than 3 years, 2026 from 2012-2024) |
| `w3_geo_SCA_rescaled` | A | g_s = sqrt(A_s x SC_A_s), scaled to SC_A's US total: g_s x sum SC_A / sum g |
| `w4_geo_rescaled` | C | g_s = sqrt(A_s x SC_s), scaled to SC's US total: g_s x sum SC / sum g |
| `w5_SC_A` | A | SC_A itself as a candidate (its scores are already known from round 1) |

Information only, no choice: (a) the section 1.4 rule applied to the references; (b) sensitivity of SC_A and of
v12_geo_SCA to the drought threshold TAU_D in {0.00, 0.05, 0.10 (round 1), 0.20, 0.30} at 15 Nov, 2012-2024 and
2017-2024 (state WAPE, mean |US|). Forecasts for 2026 and the Sep/Oct replays as in section 1.5.

<!-- END OF ROUND-2 PRE-REGISTRATION -->

Everything below was written after the scores were computed. `run.py` checks both hashes on every run and refuses to
score if either section changed (`out/run.json`: `"unchanged": true` for round 1 and round 2). Tables are printed
from `out/` by `tables.py`.

## 2. Short answer (15 Nov, 48 states)

- **Under the pre-registered rule, the headline is `v1_geo` = sqrt(A-S3 x SC)** (RECOMMENDED through R1). 2012-2024:
  state WAPE 13.24% / mean |US| 4.15%, against A-S3 13.72 / 4.98 and SC 13.23 / 3.45. Against A-S3 it gains 0.49
  points of state WAPE (90% CI over years [-1.02, -0.10]) and 0.83 points of |US| (+2 SE = -0.09). Against SC it
  ties on state WAPE (+0.01) and is worse on the US total (+0.70). 2017-2024: 12.53 / 3.68 (A-S3 12.53 / 4.02, SC
  12.80 / 3.34).
- **No candidate beats both A-S3 and SC as the task set out.** On 2012-2024 SC is already better than A-S3 on both
  metrics, so "best state split" and "best US total" both belong to SC. A-S3's state advantage exists only on
  2017-2024. RECOMMENDED candidates (`v1_geo`, `v4_mean3`, `v6_topdown_geoUS`, `v7_mean2`, `v8_geo_fitted`) all pass
  through R1 (they beat A-S3). None passes R2 (beat SC on state WAPE by 2 SE).
- **`v2_topdown`** (A-S3 shares, SC total) is not RECOMMENDED. Its US error equals SC's by construction, and the paired
  US test of SC against A-S3 misses the 2 SE bar by 0.013 points. Its state WAPE (13.68) is A-S3's, not SC's.
- Round 2 (post hoc, pre-registered in section 1b before scoring):
  - `w4_geo_rescaled` is the geometric blend scaled to SC's US total (Tier C). It is the only candidate at least as good
    as the better of A-S3 and SC on both metrics: 13.15 / 3.45 on 2012-2024 and 12.58 / 3.34 on 2017-2024. It is not
    RECOMMENDED: the R1 US test gives +0.013 (as for v2), and R2 gives +0.106. On 2017-2024 (information only) it
    passes R2: -0.22 points of WAPE against SC, +2 SE = -0.05, with the US total identical.
  - The best Tier A combination is `w3_geo_SCA_rescaled`, at 13.00 / 3.52 (2012-2024) and 12.35 / 3.65 (2017-2024). It
    is also not RECOMMENDED: its US gain over A-S3 (-1.47 points) has +2 SE = +0.52.
- **SC's label: Tier C (NASS-informed).** Its chopping term multiplies NASS's in-season yield shortfall by NASS's
  in-season harvested-for-grain forecast. The Tier B folders forbid that grain forecast. SC reads no Drought Monitor
  data. The two Tier A or B replacements score almost the same as SC (2012-2024):
  - SC_B, which takes last year's final grain acres instead of NASS's grain forecast (Tier B): 13.23 / 3.56.
  - SC_A, which uses a Drought Monitor D2+ exposure instead of the NASS yield shortfall (Tier A): 13.24 / 3.52.

  So SC's US-total gain does not need current-year NASS data.
- **Bias.** Every A-S3 or SC blend under-predicts the US total: the mean signed error on 2012-2024 is between -1.6% and
  -2.3%, and between -0.8% and -1.4% on 2017-2024. The 2012 drought year (-14% to -22%) drives most of it. The exceptions are v5,
  v5b and v13, which apply a chopping factor on top of A-S3: their signed errors are -0.63, -0.65 and +0.68.
- **2026, as of 15 Nov (US, 48 states, 80% interval):**
  - `v1_geo`: 6.278M [6.090, 6.729]
  - SC: 6.259M [6.106, 6.659]
  - A-S3: 6.298M [6.020, 6.797]
  - Tier A `w3_geo_SCA_rescaled`: 6.428M [6.253, 6.896]

  The Tier A figure is higher because the Drought Monitor puts 2026 drought on Nebraska, Minnesota and South Dakota,
  while NASS's November yield forecast shows no shortfall over 10% there (section 9).

## 3. Reproduction of the components (`out/reproduction.json`)

| Check | Result |
|---|---|
| A-S3 `s3_fsa_residual` regenerated (current `data/fsa`, corrected dates) vs `ownModels/monthly/out/monthly_by_state_year.csv`, 2012-2024, Sep/Oct/Nov, 1,872 state-years | max abs diff 0.05 acre (the monthly file keeps 1 decimal); truth identical |
| Tier B c5b regenerated vs the same file | max abs diff 0.05 acre |
| A-S3 `s0_persistence`, `s1_reversion_only` vs the same file | 0.0 and 0.05 acre |
| SC regenerated with `kernelag.silage_level` (imported, unchanged), 15 Nov | 2012-2024 13.228 / 3.447 (documented 13.23 / 3.44); 2017-2024 12.800 / 3.337 (documented 12.80 / 3.34) |
| SC per year vs `data/models/state_model_backtest.csv` (2017-2024, 2 dp) | identical (max diff 0.00 for state error and US error) |
| SC per year vs `test_models/accuracy/noise_floor/by_year.csv` (2012-2024) | within 0.03 (WAPE) and 0.06 (abs US) points; that replay is a separate implementation |
| SC 2026 (15 Nov) vs `data/models/state_forecast_2026.csv` | identical in all 48 states after rounding to 100 acres |
| A-S3 and c5b 2026 (15 Nov) vs their folders' 2026 tables | identical after rounding to 100 acres |
| SC = exp(smoothed normal level) + chopped (rebuilt from `silage_level` helpers) | max abs diff 0.0 acre at Sep, Oct, Nov |

The 2017-2024 SC truth in the stored backtest is the incumbent's panel. A-S3's loader asserts that the Quick Stats
finals equal `data/nass/corn_acres_state.csv`, so all models here are scored on the same truth and the same 48 states.

## 4. Backtest, 15 November (`out/summary.csv`)

State WAPE = sum abs(pred - actual) / sum actual, averaged over years. abs US = mean absolute error of the 48-state
total. Signed US = mean signed error. All in %.

| Model | Role | Tier | WAPE 12-24 | abs US 12-24 | signed US 12-24 | WAPE 17-24 | abs US 17-24 | signed US 17-24 |
|---|---|---|---|---|---|---|---|---|
| `A` | reference | A | 13.72 | 4.98 | -1.65 | 12.53 | 4.02 | -0.84 |
| `B` | reference | B | 13.80 | 4.94 | -1.58 | 12.66 | 3.94 | -0.73 |
| `SC` | reference | C | 13.23 | 3.45 | -2.16 | 12.80 | 3.34 | -1.32 |
| `SC_B` | reference | B | 13.23 | 3.56 | -2.25 | 12.81 | 3.36 | -1.31 |
| `SC_L` | reference | A | 13.91 | 4.48 | -2.17 | 12.96 | 3.69 | -1.38 |
| `SC_A` | reference | A | 13.24 | 3.52 | -1.81 | 12.57 | 3.65 | -1.06 |
| `s0_persistence` | reference | benchmark | 15.84 | 5.76 | +0.02 | 14.53 | 4.08 | +0.11 |
| `s1_reversion_only` | reference | A (history only) | 14.11 | 4.85 | -1.71 | 13.01 | 3.73 | -0.99 |
| `v1_geo` | primary | C | 13.24 | 4.15 | -1.99 | 12.53 | 3.68 | -1.10 |
| `v2_topdown` | primary | C | 13.68 | 3.45 | -2.16 | 12.60 | 3.34 | -1.32 |
| `v3_reverse` | primary (control) | C | 13.66 | 4.98 | -1.65 | 12.83 | 4.02 | -0.84 |
| `v4_mean3` | primary | C | 13.36 | 4.40 | -1.80 | 12.52 | 3.77 | -0.96 |
| `v5_chopmult` | primary | C | 13.22 | 4.12 | -0.63 | 12.35 | 3.77 | -0.34 |
| `v5b_chopadd` | primary (variant of v5) | C | 13.22 | 4.14 | -0.65 | 12.36 | 3.77 | -0.36 |
| `v6_topdown_geoUS` | primary | C | 13.62 | 4.12 | -1.92 | 12.51 | 3.68 | -1.08 |
| `v7_mean2` | exploratory | C | 13.20 | 4.12 | -1.91 | 12.53 | 3.68 | -1.08 |
| `v8_geo_fitted` | exploratory | C | 13.27 | 3.95 | -2.17 | 12.66 | 3.54 | -1.20 |
| `v9_topdown_SCB` | exploratory | B | 13.68 | 3.56 | -2.25 | 12.59 | 3.36 | -1.31 |
| `v10_topdown_SCL` | exploratory | A | 13.73 | 4.48 | -2.17 | 12.55 | 3.69 | -1.38 |
| `v11_topdown_SCA` | exploratory | A | 13.70 | 3.52 | -1.81 | 12.58 | 3.65 | -1.06 |
| `v12_geo_SCA` | exploratory | A | 13.08 | 4.14 | -1.87 | 12.27 | 3.78 | -0.98 |
| `v13_chopmult_SCA` | exploratory | A | 13.33 | 4.57 | +0.68 | 12.36 | 4.45 | +0.63 |
| `w1_mean2_SCA` | round 2 (post hoc) | A | 13.01 | 4.09 | -1.73 | 12.26 | 3.78 | -0.95 |
| `w2_geo_fitted_SCA` | round 2 (post hoc) | A | 13.09 | 4.01 | -2.08 | 12.36 | 3.74 | -1.01 |
| `w3_geo_SCA_rescaled` | round 2 (post hoc) | A | 13.00 | 3.52 | -1.81 | 12.35 | 3.65 | -1.06 |
| `w4_geo_rescaled` | round 2 (post hoc) | C | 13.15 | 3.45 | -2.16 | 12.58 | 3.34 | -1.32 |
| `w5_SC_A` | round 2 (post hoc) | A | 13.24 | 3.52 | -1.81 | 12.57 | 3.65 | -1.06 |

## 5. Decision (rule 1.4 applied mechanically; `out/decision.json`)

R1: WAPE - A <= 0.10 and the paired |US| difference vs A + 2 SE < 0. R2: paired WAPE difference vs SC + 2 SE < 0 and
|US| - SC <= 0.10. The last column is descriptive (at least as good as the better of A and SC on each metric). Rows
for references apply the rule for information only. Rows starting with `w` are round 2, which is post hoc.

| Model | Tier | WAPE - A | abs US vs A: d+2SE | R1 | WAPE vs SC: d+2SE | abs US - SC | R2 | Decision | <= best of A and SC on both |
|---|---|---|---|---|---|---|---|---|---|
| `A` | A | +0.00 | +0.000 | no | +1.376 | +1.54 | no | (reference) | no |
| `B` | B | +0.08 | +0.168 | no | +1.439 | +1.50 | no | (reference) | no |
| `SC` | C | -0.50 | +0.013 | no | +0.000 | +0.00 | no | (reference) | yes |
| `SC_B` | B | -0.49 | +0.114 | no | +0.069 | +0.11 | no | (reference) | no |
| `SC_L` | A | +0.19 | +0.508 | no | +1.446 | +1.03 | no | (reference) | no |
| `SC_A` | A | -0.48 | +0.521 | no | +0.675 | +0.07 | no | (reference) | no |
| `s0_persistence` | benchmark | +2.12 | +3.486 | no | +4.035 | +2.31 | no | (reference) | no |
| `s1_reversion_only` | A (history only) | +0.38 | +0.490 | no | +1.683 | +1.40 | no | (reference) | no |
| `v1_geo` | C | -0.49 | -0.089 | yes | +0.340 | +0.70 | no | **RECOMMENDED** | no |
| `v2_topdown` | C | -0.04 | +0.013 | no | +1.170 | +0.00 | no | no | no |
| `v3_reverse` | C | -0.07 | +0.000 | no | +1.278 | +1.54 | no | no | no |
| `v4_mean3` | C | -0.36 | -0.038 | yes | +0.597 | +0.95 | no | **RECOMMENDED** | no |
| `v5_chopmult` | C | -0.50 | +0.567 | no | +0.464 | +0.68 | no | no | no |
| `v5b_chopadd` | C | -0.50 | +0.552 | no | +0.457 | +0.69 | no | no | no |
| `v6_topdown_geoUS` | C | -0.10 | -0.082 | yes | +1.129 | +0.68 | no | **RECOMMENDED** | no |
| `v7_mean2` | C | -0.52 | -0.079 | yes | +0.258 | +0.67 | no | **RECOMMENDED** | no |
| `v8_geo_fitted` | C | -0.45 | -0.110 | yes | +0.304 | +0.50 | no | **RECOMMENDED** | no |
| `v9_topdown_SCB` | B | -0.05 | +0.114 | no | +1.157 | +0.11 | no | no | no |
| `v10_topdown_SCL` | A | +0.00 | +0.508 | no | +1.359 | +1.03 | no | no | no |
| `v11_topdown_SCA` | A | -0.02 | +0.521 | no | +1.318 | +0.07 | no | no | no |
| `v12_geo_SCA` | A | -0.64 | +0.046 | no | +0.223 | +0.69 | no | no | no |
| `v13_chopmult_SCA` | A | -0.39 | +1.950 | no | +1.241 | +1.12 | no | no | no |
| `w1_mean2_SCA` | A | -0.72 | +0.109 | no | +0.160 | +0.64 | no | no | no |
| `w2_geo_fitted_SCA` | A | -0.64 | +0.073 | no | +0.208 | +0.56 | no | no | no |
| `w3_geo_SCA_rescaled` | A | -0.72 | +0.521 | no | +0.147 | +0.07 | no | no | no |
| `w4_geo_rescaled` | C | -0.57 | +0.013 | no | +0.106 | +0.00 | no | no | yes |
| `w5_SC_A` | A | -0.48 | +0.521 | no | +0.675 | +0.07 | no | no | no |

Outcome:
- Headline (primary): **`v1_geo`**.
- Best RECOMMENDED round-1 exploratory: `v7_mean2` (13.20 / 4.12). Multiplicity caveat: 14 round-1 candidates were
  tested, and v7 differs from v1 by 0.03 points.
- No Tier A candidate is RECOMMENDED in either round.

The same rule at other dates and on 2017-2024 is information only:

| As of, period | RECOMMENDED under the rule | <= best of A and SC on both |
|---|---|---|
| sep 2012-2024 | `v1_geo`, `v2_topdown`, `v4_mean3`, `v6_topdown_geoUS`, `v7_mean2`, `v8_geo_fitted`, `v9_topdown_SCB`, `w4_geo_rescaled` | `w3_geo_SCA_rescaled`, `w5_SC_A` |
| sep 2017-2024 | `v8_geo_fitted` | none |
| oct 2012-2024 | `v1_geo`, `v2_topdown`, `v4_mean3`, `v6_topdown_geoUS`, `v7_mean2`, `v8_geo_fitted`, `v9_topdown_SCB`, `v12_geo_SCA`, `w2_geo_fitted_SCA`, `w4_geo_rescaled` | `w4_geo_rescaled` |
| oct 2017-2024 | none | none |
| nov 2017-2024 | `w4_geo_rescaled` | none |

## 6. Paired comparisons with 90% bootstrap intervals (`out/comparisons.csv`)

Differences are candidate minus reference, in points; negative is better. Each cell gives the mean difference with
its mean + 2 SE over years, and the years better / worse. The CIs resample years (10,000 draws), states as clusters
with the same draw in every year (2,000), and years x states jointly (2,000). Every joint interval includes 0.

### 6.1 15 Nov, 2012-2024, against A-S3

| Model | WAPE diff | yrs b/w | CI years | CI states | CI joint | abs US diff | yrs b/w | CI years | CI states | CI joint |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_geo` | -0.49 (+2SE +0.10) | 8/5 | [-1.016, -0.095] | [-1.046, -0.087] | [-1.321, +0.079] | -0.83 (+2SE -0.09) | 9/4 | [-1.444, -0.259] | [-1.260, -0.171] | [-1.561, +0.091] |
| `v2_topdown` | -0.04 (+2SE +0.20) | 6/7 | [-0.233, +0.150] | [-0.385, +0.312] | [-0.562, +0.412] | -1.54 (+2SE +0.01) | 9/4 | [-2.857, -0.378] | [-1.798, -0.282] | [-2.580, +0.318] |
| `v3_reverse` | -0.07 (+2SE +0.30) | 6/7 | [-0.362, +0.218] | [-0.874, +0.562] | [-1.051, +0.734] | +0.00 (+2SE +0.00) | 0/0 | [-0.000, +0.000] | [-0.871, +0.586] | [-1.013, +0.760] |
| `v4_mean3` | -0.36 (+2SE +0.09) | 8/5 | [-0.770, -0.065] | [-0.757, -0.073] | [-0.999, +0.053] | -0.59 (+2SE -0.04) | 9/4 | [-1.045, -0.169] | [-0.925, -0.155] | [-1.167, +0.034] |
| `v5_chopmult` | -0.50 (+2SE +0.30) | 5/5 | [-1.265, -0.016] | [-0.758, -0.251] | [-1.387, +0.045] | -0.86 (+2SE +0.57) | 6/4 | [-2.224, -0.008] | [-1.377, -0.423] | [-2.414, +0.060] |
| `v5b_chopadd` | -0.50 (+2SE +0.31) | 5/5 | [-1.284, -0.016] | [-0.755, -0.257] | [-1.406, +0.045] | -0.85 (+2SE +0.55) | 6/4 | [-2.185, -0.012] | [-1.349, -0.422] | [-2.376, +0.058] |
| `v6_topdown_geoUS` | -0.10 (+2SE +0.08) | 7/6 | [-0.256, +0.032] | [-0.246, +0.047] | [-0.370, +0.122] | -0.86 (+2SE -0.08) | 9/4 | [-1.506, -0.267] | [-0.959, -0.275] | [-1.382, +0.044] |
| `v7_mean2` | -0.52 (+2SE +0.15) | 8/5 | [-1.133, -0.087] | [-1.096, -0.108] | [-1.427, +0.074] | -0.86 (+2SE -0.08) | 9/4 | [-1.515, -0.268] | [-1.300, -0.212] | [-1.655, +0.051] |
| `v8_geo_fitted` | -0.45 (+2SE +0.19) | 8/5 | [-1.011, +0.003] | [-1.114, +0.042] | [-1.384, +0.231] | -1.03 (+2SE -0.11) | 9/4 | [-1.795, -0.324] | [-1.469, -0.084] | [-1.795, +0.204] |
| `v9_topdown_SCB` | -0.05 (+2SE +0.20) | 7/6 | [-0.243, +0.148] | [-0.394, +0.307] | [-0.569, +0.411] | -1.43 (+2SE +0.11) | 8/5 | [-2.738, -0.264] | [-1.815, -0.202] | [-2.551, +0.382] |
| `v10_topdown_SCL` | +0.00 (+2SE +0.22) | 8/5 | [-0.156, +0.178] | [-0.181, +0.204] | [-0.318, +0.283] | -0.50 (+2SE +0.51) | 8/5 | [-1.319, +0.269] | [-0.748, +0.422] | [-1.247, +0.635] |
| `v11_topdown_SCA` | -0.02 (+2SE +0.23) | 8/5 | [-0.215, +0.182] | [-0.463, +0.448] | [-0.623, +0.586] | -1.47 (+2SE +0.52) | 10/3 | [-3.220, -0.064] | [-1.951, -0.467] | [-3.070, +0.462] |
| `v12_geo_SCA` | -0.64 (+2SE +0.14) | 9/4 | [-1.349, -0.118] | [-1.252, -0.161] | [-1.692, +0.074] | -0.85 (+2SE +0.05) | 10/3 | [-1.610, -0.180] | [-1.405, -0.167] | [-1.904, +0.147] |
| `v13_chopmult_SCA` | -0.39 (+2SE +1.12) | 8/5 | [-1.687, +0.703] | [-0.716, -0.072] | [-1.870, +0.806] | -0.41 (+2SE +1.95) | 6/7 | [-2.527, +1.224] | [-1.203, -0.034] | [-2.946, +1.221] |
| `w1_mean2_SCA` | -0.72 (+2SE +0.20) | 9/4 | [-1.562, -0.118] | [-1.360, -0.196] | [-1.967, +0.055] | -0.90 (+2SE +0.11) | 10/3 | [-1.773, -0.168] | [-1.489, -0.236] | [-2.125, +0.133] |
| `w2_geo_fitted_SCA` | -0.64 (+2SE +0.19) | 8/5 | [-1.373, -0.057] | [-1.368, -0.049] | [-1.849, +0.225] | -0.97 (+2SE +0.07) | 10/3 | [-1.857, -0.172] | [-1.608, -0.087] | [-2.092, +0.282] |
| `w3_geo_SCA_rescaled` | -0.72 (+2SE +0.30) | 9/4 | [-1.660, -0.049] | [-1.441, -0.099] | [-2.049, +0.179] | -1.47 (+2SE +0.52) | 10/3 | [-3.220, -0.064] | [-2.172, -0.493] | [-3.336, +0.435] |
| `w4_geo_rescaled` | -0.57 (+2SE +0.24) | 9/4 | [-1.302, -0.028] | [-1.203, -0.070] | [-1.613, +0.167] | -1.54 (+2SE +0.01) | 9/4 | [-2.857, -0.378] | [-1.982, -0.282] | [-2.730, +0.306] |
| `w5_SC_A` | -0.48 (+2SE +0.80) | 6/7 | [-1.615, +0.413] | [-1.300, +0.191] | [-2.037, +0.707] | -1.47 (+2SE +0.52) | 10/3 | [-3.220, -0.064] | [-2.427, -0.287] | [-3.642, +0.539] |

### 6.2 15 Nov, 2012-2024, against SC

| Model | WAPE diff | yrs b/w | CI years | CI states | CI joint | abs US diff | yrs b/w | CI years | CI states | CI joint |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_geo` | +0.01 (+2SE +0.34) | 7/6 | [-0.242, +0.287] | [-0.252, +0.311] | [-0.410, +0.506] | +0.70 (+2SE +1.57) | 5/8 | [+0.061, +1.453] | [-0.023, +1.017] | [-0.383, +1.492] |
| `v2_topdown` | +0.45 (+2SE +1.17) | 6/7 | [-0.037, +1.088] | [-0.050, +1.101] | [-0.320, +1.517] | +0.00 (+2SE +0.00) | 0/0 | [-0.000, +0.000] | [-0.416, +0.603] | [-0.630, +0.793] |
| `v3_reverse` | +0.43 (+2SE +1.28) | 7/6 | [-0.114, +1.215] | [+0.171, +0.690] | [-0.241, +1.263] | +1.54 (+2SE +3.09) | 4/9 | [+0.378, +2.857] | [+0.262, +1.770] | [-0.323, +2.614] |
| `v4_mean3` | +0.13 (+2SE +0.60) | 7/6 | [-0.212, +0.530] | [-0.224, +0.564] | [-0.413, +0.809] | +0.95 (+2SE +1.97) | 5/8 | [+0.189, +1.831] | [-0.017, +1.375] | [-0.406, +1.887] |
| `v5_chopmult` | -0.00 (+2SE +0.46) | 7/6 | [-0.372, +0.367] | [-0.488, +0.650] | [-0.651, +0.854] | +0.68 (+2SE +1.84) | 5/8 | [-0.187, +1.624] | [-0.606, +1.096] | [-0.919, +1.503] |
| `v5b_chopadd` | -0.01 (+2SE +0.46) | 7/6 | [-0.373, +0.362] | [-0.488, +0.643] | [-0.657, +0.848] | +0.69 (+2SE +1.85) | 5/8 | [-0.169, +1.633] | [-0.597, +1.123] | [-0.894, +1.521] |
| `v6_topdown_geoUS` | +0.40 (+2SE +1.13) | 6/7 | [-0.121, +1.038] | [-0.134, +1.090] | [-0.406, +1.485] | +0.68 (+2SE +1.49) | 5/8 | [+0.068, +1.376] | [-0.137, +1.318] | [-0.482, +1.754] |
| `v7_mean2` | -0.02 (+2SE +0.26) | 7/6 | [-0.246, +0.202] | [-0.291, +0.283] | [-0.436, +0.444] | +0.67 (+2SE +1.48) | 5/8 | [+0.070, +1.365] | [-0.071, +0.989] | [-0.419, +1.390] |
| `v8_geo_fitted` | +0.04 (+2SE +0.30) | 7/6 | [-0.142, +0.274] | [-0.151, +0.267] | [-0.252, +0.433] | +0.50 (+2SE +1.26) | 5/8 | [-0.020, +1.184] | [+0.056, +0.804] | [-0.316, +1.291] |
| `v9_topdown_SCB` | +0.45 (+2SE +1.16) | 6/7 | [-0.039, +1.077] | [-0.050, +1.089] | [-0.325, +1.499] | +0.11 (+2SE +0.23) | 4/9 | [+0.018, +0.206] | [-0.384, +0.573] | [-0.609, +0.815] |
| `v10_topdown_SCL` | +0.50 (+2SE +1.36) | 6/7 | [-0.073, +1.273] | [-0.075, +1.241] | [-0.366, +1.713] | +1.03 (+2SE +2.38) | 3/10 | [+0.105, +2.209] | [+0.082, +1.831] | [-0.472, +2.677] |
| `v11_topdown_SCA` | +0.47 (+2SE +1.32) | 6/7 | [-0.112, +1.217] | [-0.077, +1.165] | [-0.404, +1.646] | +0.07 (+2SE +1.04) | 6/7 | [-0.726, +0.818] | [-0.749, +0.636] | [-1.255, +0.975] |
| `v12_geo_SCA` | -0.15 (+2SE +0.22) | 7/6 | [-0.438, +0.143] | [-0.403, +0.128] | [-0.641, +0.347] | +0.69 (+2SE +1.55) | 4/9 | [+0.044, +1.411] | [-0.219, +1.072] | [-0.511, +1.513] |
| `v13_chopmult_SCA` | +0.11 (+2SE +1.24) | 8/5 | [-0.765, +1.020] | [-0.568, +1.021] | [-1.027, +1.585] | +1.12 (+2SE +3.18) | 6/7 | [-0.489, +2.773] | [-0.562, +1.762] | [-1.311, +2.588] |
| `w1_mean2_SCA` | -0.22 (+2SE +0.16) | 8/5 | [-0.515, +0.085] | [-0.503, +0.060] | [-0.742, +0.301] | +0.64 (+2SE +1.43) | 3/10 | [+0.042, +1.308] | [-0.321, +1.000] | [-0.593, +1.405] |
| `w2_geo_fitted_SCA` | -0.14 (+2SE +0.21) | 8/5 | [-0.415, +0.139] | [-0.335, +0.090] | [-0.596, +0.308] | +0.56 (+2SE +1.37) | 5/8 | [-0.050, +1.235] | [-0.207, +0.931] | [-0.550, +1.392] |
| `w3_geo_SCA_rescaled` | -0.22 (+2SE +0.15) | 9/4 | [-0.513, +0.076] | [-0.484, +0.075] | [-0.754, +0.289] | +0.07 (+2SE +1.04) | 6/7 | [-0.726, +0.818] | [-0.716, +0.424] | [-1.190, +0.828] |
| `w4_geo_rescaled` | -0.07 (+2SE +0.11) | 8/5 | [-0.211, +0.073] | [-0.293, +0.185] | [-0.409, +0.311] | +0.00 (+2SE +0.00) | 0/0 | [-0.000, +0.000] | [-0.257, +0.283] | [-0.369, +0.392] |
| `w5_SC_A` | +0.01 (+2SE +0.68) | 8/5 | [-0.489, +0.545] | [-0.215, +0.250] | [-0.663, +0.693] | +0.07 (+2SE +1.04) | 6/7 | [-0.726, +0.818] | [-0.741, +0.443] | [-1.302, +0.907] |

### 6.3 15 Nov, 2017-2024, against A-S3

| Model | WAPE diff | yrs b/w | CI years | CI states | CI joint | abs US diff | yrs b/w | CI years | CI states | CI joint |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_geo` | +0.00 (+2SE +0.21) | 3/5 | [-0.162, +0.156] | [-0.270, +0.236] | [-0.379, +0.342] | -0.34 (+2SE +0.40) | 5/3 | [-0.943, +0.212] | [-0.604, +0.066] | [-1.035, +0.292] |
| `v2_topdown` | +0.07 (+2SE +0.38) | 3/5 | [-0.162, +0.321] | [-0.125, +0.269] | [-0.368, +0.417] | -0.68 (+2SE +0.77) | 5/3 | [-1.875, +0.404] | [-0.953, +0.316] | [-1.757, +0.679] |
| `v3_reverse` | +0.30 (+2SE +0.61) | 2/6 | [+0.057, +0.535] | [-0.127, +0.684] | [-0.286, +0.886] | -0.00 (+2SE +0.00) | 0/0 | [-0.000, +0.000] | [-0.378, +0.357] | [-0.581, +0.501] |
| `v4_mean3` | -0.00 (+2SE +0.16) | 3/5 | [-0.135, +0.113] | [-0.226, +0.183] | [-0.336, +0.259] | -0.25 (+2SE +0.31) | 5/3 | [-0.709, +0.177] | [-0.491, +0.023] | [-0.785, +0.239] |
| `v5_chopmult` | -0.18 (+2SE +0.11) | 4/2 | [-0.409, +0.043] | [-0.406, +0.053] | [-0.593, +0.146] | -0.25 (+2SE +0.22) | 4/2 | [-0.654, +0.064] | [-0.548, +0.041] | [-0.819, +0.204] |
| `v5b_chopadd` | -0.17 (+2SE +0.11) | 4/2 | [-0.386, +0.044] | [-0.386, +0.051] | [-0.567, +0.147] | -0.26 (+2SE +0.21) | 4/2 | [-0.641, +0.058] | [-0.529, +0.039] | [-0.796, +0.200] |
| `v6_topdown_geoUS` | -0.02 (+2SE +0.16) | 3/5 | [-0.166, +0.110] | [-0.113, +0.086] | [-0.263, +0.156] | -0.34 (+2SE +0.39) | 5/3 | [-0.945, +0.204] | [-0.633, +0.002] | [-0.964, +0.265] |
| `v7_mean2` | +0.00 (+2SE +0.21) | 3/5 | [-0.162, +0.155] | [-0.268, +0.236] | [-0.379, +0.344] | -0.34 (+2SE +0.39) | 5/3 | [-0.937, +0.202] | [-0.603, +0.061] | [-1.028, +0.285] |
| `v8_geo_fitted` | +0.14 (+2SE +0.47) | 3/5 | [-0.122, +0.395] | [-0.250, +0.464] | [-0.431, +0.648] | -0.48 (+2SE +0.60) | 5/3 | [-1.342, +0.337] | [-0.803, +0.165] | [-1.403, +0.494] |
| `v9_topdown_SCB` | +0.06 (+2SE +0.38) | 4/4 | [-0.172, +0.317] | [-0.132, +0.261] | [-0.379, +0.413] | -0.66 (+2SE +0.81) | 4/4 | [-1.864, +0.434] | [-0.964, +0.313] | [-1.757, +0.670] |
| `v10_topdown_SCL` | +0.03 (+2SE +0.36) | 5/3 | [-0.221, +0.293] | [-0.124, +0.185] | [-0.355, +0.343] | -0.33 (+2SE +0.87) | 5/3 | [-1.288, +0.554] | [-0.729, +0.348] | [-1.328, +0.645] |
| `v11_topdown_SCA` | +0.05 (+2SE +0.45) | 5/3 | [-0.255, +0.361] | [-0.147, +0.241] | [-0.342, +0.460] | -0.37 (+2SE +0.71) | 6/2 | [-1.184, +0.496] | [-1.040, +0.248] | [-1.404, +0.691] |
| `v12_geo_SCA` | -0.25 (+2SE +0.11) | 5/3 | [-0.553, +0.014] | [-0.637, +0.083] | [-0.835, +0.241] | -0.24 (+2SE +0.26) | 6/2 | [-0.617, +0.163] | [-0.687, +0.102] | [-0.926, +0.336] |
| `v13_chopmult_SCA` | -0.17 (+2SE +0.96) | 6/2 | [-0.958, +0.761] | [-0.452, +0.092] | [-1.105, +0.945] | +0.43 (+2SE +1.83) | 4/4 | [-0.586, +1.571] | [-0.486, +0.876] | [-1.082, +1.724] |
| `w1_mean2_SCA` | -0.27 (+2SE +0.10) | 5/3 | [-0.570, -0.003] | [-0.660, +0.074] | [-0.858, +0.229] | -0.24 (+2SE +0.25) | 6/2 | [-0.611, +0.161] | [-0.698, +0.106] | [-0.928, +0.337] |
| `w2_geo_fitted_SCA` | -0.17 (+2SE +0.35) | 4/4 | [-0.595, +0.197] | [-0.623, +0.249] | [-0.866, +0.492] | -0.28 (+2SE +0.48) | 6/2 | [-0.853, +0.345] | [-0.939, +0.202] | [-1.294, +0.524] |
| `w3_geo_SCA_rescaled` | -0.17 (+2SE +0.22) | 5/3 | [-0.472, +0.138] | [-0.595, +0.210] | [-0.788, +0.372] | -0.37 (+2SE +0.71) | 6/2 | [-1.184, +0.496] | [-1.076, +0.226] | [-1.520, +0.649] |
| `w4_geo_rescaled` | +0.06 (+2SE +0.41) | 4/4 | [-0.214, +0.326] | [-0.275, +0.331] | [-0.480, +0.511] | -0.68 (+2SE +0.77) | 5/3 | [-1.875, +0.404] | [-0.950, +0.294] | [-1.785, +0.667] |
| `w5_SC_A` | +0.04 (+2SE +0.68) | 2/6 | [-0.484, +0.489] | [-0.511, +0.522] | [-0.796, +0.855] | -0.37 (+2SE +0.71) | 6/2 | [-1.184, +0.496] | [-1.210, +0.322] | [-1.717, +0.756] |

### 6.4 15 Nov, 2017-2024, against SC

| Model | WAPE diff | yrs b/w | CI years | CI states | CI joint | abs US diff | yrs b/w | CI years | CI states | CI joint |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_geo` | -0.27 (+2SE -0.00) | 6/2 | [-0.482, -0.073] | [-0.474, -0.044] | [-0.628, +0.101] | +0.35 (+2SE +1.06) | 3/5 | [-0.187, +0.928] | [-0.337, +0.478] | [-0.552, +0.866] |
| `v2_topdown` | -0.20 (+2SE +0.04) | 6/2 | [-0.381, -0.006] | [-0.533, +0.174] | [-0.764, +0.335] | +0.00 (+2SE +0.00) | 0/0 | [-0.000, +0.000] | [-0.331, +0.359] | [-0.484, +0.545] |
| `v3_reverse` | +0.03 (+2SE +0.44) | 5/3 | [-0.254, +0.377] | [-0.142, +0.218] | [-0.347, +0.526] | +0.68 (+2SE +2.14) | 3/5 | [-0.404, +1.875] | [-0.357, +0.976] | [-0.674, +1.727] |
| `v4_mean3` | -0.28 (+2SE +0.05) | 6/2 | [-0.535, -0.037] | [-0.539, +0.012] | [-0.730, +0.195] | +0.43 (+2SE +1.33) | 3/5 | [-0.226, +1.175] | [-0.399, +0.611] | [-0.613, +1.140] |
| `v5_chopmult` | -0.45 (+2SE +0.00) | 6/2 | [-0.805, -0.114] | [-0.870, -0.007] | [-1.109, +0.253] | +0.43 (+2SE +1.88) | 3/5 | [-0.594, +1.578] | [-0.624, +0.760] | [-0.925, +1.603] |
| `v5b_chopadd` | -0.44 (+2SE +0.00) | 6/2 | [-0.793, -0.112] | [-0.856, -0.004] | [-1.087, +0.255] | +0.43 (+2SE +1.88) | 3/5 | [-0.594, +1.577] | [-0.610, +0.758] | [-0.915, +1.612] |
| `v6_topdown_geoUS` | -0.29 (+2SE +0.04) | 6/2 | [-0.545, -0.035] | [-0.665, +0.138] | [-0.870, +0.324] | +0.34 (+2SE +1.06) | 3/5 | [-0.200, +0.928] | [-0.405, +0.611] | [-0.629, +1.019] |
| `v7_mean2` | -0.27 (+2SE -0.00) | 6/2 | [-0.483, -0.072] | [-0.473, -0.044] | [-0.631, +0.102] | +0.34 (+2SE +1.07) | 3/5 | [-0.202, +0.937] | [-0.354, +0.475] | [-0.558, +0.872] |
| `v8_geo_fitted` | -0.14 (+2SE -0.01) | 6/2 | [-0.233, -0.045] | [-0.244, -0.026] | [-0.314, +0.044] | +0.21 (+2SE +0.60) | 3/5 | [-0.070, +0.538] | [-0.205, +0.267] | [-0.342, +0.486] |
| `v9_topdown_SCB` | -0.21 (+2SE +0.02) | 6/2 | [-0.375, -0.027] | [-0.535, +0.169] | [-0.753, +0.327] | +0.03 (+2SE +0.13) | 3/5 | [-0.047, +0.104] | [-0.344, +0.351] | [-0.514, +0.520] |
| `v10_topdown_SCL` | -0.25 (+2SE -0.00) | 6/2 | [-0.432, -0.059] | [-0.608, +0.176] | [-0.803, +0.343] | +0.35 (+2SE +0.74) | 2/6 | [+0.059, +0.665] | [-0.252, +0.617] | [-0.444, +0.878] |
| `v11_topdown_SCA` | -0.22 (+2SE +0.26) | 6/2 | [-0.565, +0.174] | [-0.664, +0.226] | [-0.915, +0.513] | +0.31 (+2SE +1.47) | 4/4 | [-0.594, +1.229] | [-0.852, +0.781] | [-1.087, +1.241] |
| `v12_geo_SCA` | -0.53 (+2SE -0.18) | 7/1 | [-0.797, -0.251] | [-0.884, -0.181] | [-1.037, +0.067] | +0.44 (+2SE +1.63) | 3/5 | [-0.431, +1.428] | [-0.600, +0.698] | [-0.858, +1.329] |
| `v13_chopmult_SCA` | -0.44 (+2SE +0.84) | 7/1 | [-1.323, +0.652] | [-1.004, +0.142] | [-1.510, +1.059] | +1.11 (+2SE +3.61) | 4/4 | [-0.611, +3.240] | [-0.398, +1.567] | [-1.079, +3.125] |
| `w1_mean2_SCA` | -0.54 (+2SE -0.19) | 7/1 | [-0.813, -0.263] | [-0.908, -0.196] | [-1.062, +0.055] | +0.44 (+2SE +1.64) | 3/5 | [-0.429, +1.431] | [-0.619, +0.699] | [-0.876, +1.324] |
| `w2_geo_fitted_SCA` | -0.44 (+2SE -0.07) | 6/2 | [-0.718, -0.138] | [-0.775, -0.121] | [-0.929, +0.105] | +0.40 (+2SE +1.54) | 4/4 | [-0.464, +1.340] | [-0.698, +0.685] | [-0.963, +1.221] |
| `w3_geo_SCA_rescaled` | -0.45 (+2SE -0.18) | 8/0 | [-0.658, -0.252] | [-0.827, -0.082] | [-0.968, +0.109] | +0.31 (+2SE +1.47) | 4/4 | [-0.594, +1.229] | [-0.827, +0.669] | [-1.106, +1.173] |
| `w4_geo_rescaled` | -0.22 (+2SE -0.05) | 7/1 | [-0.342, -0.084] | [-0.393, -0.030] | [-0.506, +0.057] | +0.00 (+2SE +0.00) | 0/0 | [-0.000, +0.000] | [-0.174, +0.172] | [-0.259, +0.254] |
| `w5_SC_A` | -0.23 (+2SE +0.21) | 6/2 | [-0.572, +0.107] | [-0.549, +0.069] | [-0.801, +0.323] | +0.31 (+2SE +1.47) | 4/4 | [-0.594, +1.229] | [-0.834, +0.755] | [-1.193, +1.274] |

## 7. Per year, 15 Nov (state WAPE / signed US error, %; `out/by_year.csv`)

| Year | `A` | `SC` | `SC_A` | `v1_geo` | `v7_mean2` | `v12_geo_SCA` | `w3_geo_SCA_rescaled` | `w4_geo_rescaled` |
|---|---|---|---|---|---|---|---|---|
| 2012 | 24.21 / -22.14 | 19.09 / -14.08 | 17.12 / -10.33 | 20.46 / -18.68 | 19.89 / -18.11 | 19.34 / -17.25 | 17.77 / -10.33 | 19.13 / -14.08 |
| 2013 | 16.05 / +2.06 | 15.89 / -1.17 | 18.97 / +0.75 | 15.42 / +0.29 | 15.47 / +0.45 | 17.03 / +1.12 | 17.06 / +0.75 | 15.55 / -1.17 |
| 2014 | 12.73 / -1.57 | 11.83 / -2.55 | 12.62 / -3.77 | 12.21 / -2.10 | 12.25 / -2.06 | 12.27 / -2.75 | 12.32 / -3.77 | 12.15 / -2.55 |
| 2015 | 12.22 / +2.13 | 11.11 / -0.05 | 11.07 / -1.21 | 11.60 / +1.01 | 11.61 / +1.04 | 11.41 / +0.39 | 11.42 / -1.21 | 11.59 / -0.05 |
| 2016 | 12.98 / +4.72 | 11.63 / +0.27 | 11.80 / -0.46 | 12.12 / +2.42 | 12.16 / +2.50 | 11.81 / +2.03 | 11.65 / -0.46 | 11.94 / +0.27 |
| 2017 | 11.25 / -2.83 | 11.55 / -2.91 | 11.28 / -2.32 | 11.33 / -2.87 | 11.33 / -2.87 | 11.12 / -2.59 | 11.11 / -2.32 | 11.34 / -2.91 |
| 2018 | 17.95 / +3.31 | 17.74 / +3.04 | 17.25 / +2.96 | 17.76 / +3.17 | 17.76 / +3.18 | 17.54 / +3.12 | 17.49 / +2.96 | 17.71 / +3.04 |
| 2019 | 14.49 / -7.34 | 14.65 / -6.13 | 14.75 / -7.06 | 14.57 / -6.78 | 14.56 / -6.74 | 14.61 / -7.24 | 14.58 / -7.06 | 14.47 / -6.13 |
| 2020 | 8.40 / -1.51 | 9.78 / -3.85 | 9.48 / -3.73 | 8.78 / -2.71 | 8.77 / -2.68 | 8.69 / -2.64 | 9.18 / -3.73 | 9.30 / -3.85 |
| 2021 | 11.75 / -0.45 | 11.36 / -0.20 | 9.98 / +1.84 | 11.51 / -0.34 | 11.51 / -0.33 | 10.52 / +0.65 | 10.91 / +1.84 | 11.55 / -0.20 |
| 2022 | 14.78 / -7.31 | 15.66 / -5.52 | 15.54 / -5.72 | 15.01 / -6.45 | 15.00 / -6.41 | 14.99 / -6.58 | 15.12 / -5.72 | 15.15 / -5.52 |
| 2023 | 9.90 / +5.21 | 9.51 / +0.41 | 10.38 / +3.45 | 9.40 / +2.76 | 9.40 / +2.81 | 9.73 / +4.29 | 9.51 / +3.45 | 9.12 / +0.41 |
| 2024 | 11.70 / +4.21 | 12.13 / +4.63 | 11.88 / +2.10 | 11.90 / +4.40 | 11.92 / +4.42 | 10.99 / +3.12 | 10.94 / +2.10 | 12.01 / +4.63 |

2012 is the drought year. A-S3 misses it by -22% on the US total. SC's yield-shortfall chopping cuts that to -14%,
and the Drought Monitor chopping (SC_A) to -10%. Most of the 2012-2024 US-total differences come from 2012, which
is why the paired US tests have large standard errors.

## 8. Earliness: 15 September and 15 October (state WAPE / mean |US|; `out/summary.csv`)

| Model | 15 Sep 12-24 | 15 Oct 12-24 | 15 Nov 12-24 | 15 Sep 17-24 | 15 Oct 17-24 | 15 Nov 17-24 |
|---|---|---|---|---|---|---|
| `A` | 13.80 / 5.00 | 13.79 / 5.03 | 13.72 / 4.98 | 12.64 / 4.09 | 12.60 / 4.09 | 12.53 / 4.02 |
| `B` | 13.86 / 4.95 | 13.82 / 4.96 | 13.80 / 4.94 | 12.71 / 3.95 | 12.67 / 3.99 | 12.66 / 3.94 |
| `SC` | 13.35 / 3.85 | 13.25 / 3.44 | 13.23 / 3.45 | 12.79 / 3.51 | 12.81 / 3.37 | 12.80 / 3.34 |
| `SC_B` | 13.39 / 3.85 | 13.25 / 3.47 | 13.23 / 3.56 | 12.83 / 3.47 | 12.82 / 3.42 | 12.81 / 3.36 |
| `SC_L` | 13.91 / 4.48 | 13.91 / 4.48 | 13.91 / 4.48 | 12.96 / 3.69 | 12.96 / 3.69 | 12.96 / 3.69 |
| `SC_A` | 13.29 / 3.73 | 13.24 / 3.52 | 13.24 / 3.52 | 12.54 / 3.68 | 12.57 / 3.65 | 12.57 / 3.65 |
| `s0_persistence` | 15.84 / 5.76 | 15.84 / 5.76 | 15.84 / 5.76 | 14.53 / 4.08 | 14.53 / 4.08 | 14.53 / 4.08 |
| `s1_reversion_only` | 14.11 / 4.85 | 14.11 / 4.85 | 14.11 / 4.85 | 13.01 / 3.73 | 13.01 / 3.73 | 13.01 / 3.73 |
| `v1_geo` | 13.49 / 4.42 | 13.28 / 4.18 | 13.24 / 4.15 | 12.62 / 3.80 | 12.59 / 3.74 | 12.53 / 3.68 |
| `v2_topdown` | 13.74 / 3.85 | 13.74 / 3.44 | 13.68 / 3.45 | 12.70 / 3.51 | 12.65 / 3.37 | 12.60 / 3.34 |
| `v3_reverse` | 13.55 / 5.00 | 13.70 / 5.03 | 13.66 / 4.98 | 12.82 / 4.09 | 12.86 / 4.09 | 12.83 / 4.02 |
| `v4_mean3` | 13.58 / 4.60 | 13.40 / 4.42 | 13.36 / 4.40 | 12.62 / 3.85 | 12.58 / 3.82 | 12.52 / 3.77 |
| `v5_chopmult` | 13.43 / 4.66 | 13.29 / 4.22 | 13.22 / 4.12 | 12.45 / 3.96 | 12.41 / 3.92 | 12.35 / 3.77 |
| `v5b_chopadd` | 13.43 / 4.65 | 13.29 / 4.22 | 13.22 / 4.14 | 12.46 / 3.95 | 12.42 / 3.91 | 12.36 / 3.77 |
| `v6_topdown_geoUS` | 13.73 / 4.42 | 13.69 / 4.16 | 13.62 / 4.12 | 12.64 / 3.79 | 12.59 / 3.73 | 12.51 / 3.68 |
| `v7_mean2` | 13.49 / 4.42 | 13.25 / 4.15 | 13.20 / 4.12 | 12.62 / 3.80 | 12.59 / 3.73 | 12.53 / 3.68 |
| `v8_geo_fitted` | 13.51 / 4.02 | 13.29 / 3.94 | 13.27 / 3.95 | 12.79 / 3.51 | 12.69 / 3.55 | 12.66 / 3.54 |
| `v9_topdown_SCB` | 13.74 / 3.85 | 13.73 / 3.47 | 13.68 / 3.56 | 12.70 / 3.47 | 12.65 / 3.42 | 12.59 / 3.36 |
| `v10_topdown_SCL` | 13.78 / 4.48 | 13.78 / 4.48 | 13.73 / 4.48 | 12.64 / 3.69 | 12.60 / 3.69 | 12.55 / 3.69 |
| `v11_topdown_SCA` | 13.75 / 3.73 | 13.75 / 3.52 | 13.70 / 3.52 | 12.66 / 3.68 | 12.63 / 3.65 | 12.58 / 3.65 |
| `v12_geo_SCA` | 13.17 / 4.25 | 13.12 / 4.16 | 13.08 / 4.14 | 12.36 / 3.83 | 12.33 / 3.82 | 12.27 / 3.78 |
| `v13_chopmult_SCA` | 13.43 / 4.58 | 13.39 / 4.61 | 13.33 / 4.57 | 12.44 / 4.52 | 12.42 / 4.52 | 12.36 / 4.45 |
| `w1_mean2_SCA` | 13.10 / 4.20 | 13.05 / 4.11 | 13.01 / 4.09 | 12.35 / 3.83 | 12.31 / 3.82 | 12.26 / 3.78 |
| `w2_geo_fitted_SCA` | 13.12 / 4.14 | 13.11 / 4.00 | 13.09 / 4.01 | 12.38 / 3.77 | 12.40 / 3.73 | 12.36 / 3.74 |
| `w3_geo_SCA_rescaled` | 13.08 / 3.73 | 13.03 / 3.52 | 13.00 / 3.52 | 12.42 / 3.68 | 12.38 / 3.65 | 12.35 / 3.65 |
| `w4_geo_rescaled` | 13.43 / 3.85 | 13.19 / 3.44 | 13.15 / 3.45 | 12.66 / 3.51 | 12.62 / 3.37 | 12.58 / 3.34 |
| `w5_SC_A` | 13.29 / 3.73 | 13.24 / 3.52 | 13.24 / 3.52 | 12.54 / 3.68 | 12.57 / 3.65 | 12.57 / 3.65 |

From 15 October the blends are within 0.1 point of their 15 November scores. On 15 September, SC's US error
is higher (3.85 against 3.45 in November) because only the August and September yield forecasts exist then. The Tier
A drought versions move less (SC_A 3.73 in September against 3.52 in November). Under the rule on 2012-2024,
`v2_topdown` is RECOMMENDED at 15 Sep and 15 Oct (information only): at those dates SC's US gain over A-S3 clears 2 SE.

## 9. Forecasts for 2026 (`out/forecast_2026.csv`, `out/forecast_2026_us.csv`)

US totals in million acres (48 states), with 80% intervals: the 10th and 90th percentiles of the 13 backtest US
log errors at the same date. The state intervals use size-class quantiles of the backtest log errors
(`kernelag.state_model.error_quantiles`). Their leave-one-year-out coverage is in the last column (nominal 0.80;
90% coverage is in `out/interval_coverage.csv`).

| Model | Tier | 15 Sep 2026 | 15 Oct 2026 | 15 Nov 2026 | LOYO 80% state coverage (Nov) |
|---|---|---|---|---|---|
| `A` | A | 6.296 [6.022, 6.800] | 6.293 [6.020, 6.798] | 6.298 [6.020, 6.797] | 0.788 |
| `B` | B | 6.290 [6.025, 6.763] | 6.283 [6.014, 6.751] | 6.285 [6.013, 6.753] | 0.784 |
| `SC` | C | 6.263 [6.096, 6.674] | 6.259 [6.101, 6.663] | 6.259 [6.106, 6.659] | 0.793 |
| `SC_B` | B | 6.263 [6.100, 6.670] | 6.259 [6.096, 6.661] | 6.260 [6.103, 6.657] | 0.792 |
| `SC_L` | A | 6.270 [6.037, 6.718] | 6.270 [6.037, 6.718] | 6.270 [6.037, 6.718] | 0.787 |
| `SC_A` | A | 6.431 [6.254, 6.904] | 6.428 [6.253, 6.896] | 6.428 [6.253, 6.896] | 0.787 |
| `s0_persistence` | benchmark | 6.187 [5.848, 6.650] | 6.187 [5.848, 6.650] | 6.187 [5.848, 6.650] | 0.795 |
| `s1_reversion_only` | A (history only) | 6.333 [6.086, 6.775] | 6.333 [6.086, 6.775] | 6.333 [6.086, 6.775] | 0.788 |
| `v1_geo` | C | 6.279 [6.091, 6.738] | 6.275 [6.089, 6.732] | 6.278 [6.090, 6.729] | 0.787 |
| `v2_topdown` | C | 6.263 [6.096, 6.674] | 6.259 [6.101, 6.663] | 6.259 [6.106, 6.659] | 0.793 |
| `v3_reverse` | C | 6.296 [6.022, 6.800] | 6.293 [6.020, 6.798] | 6.298 [6.020, 6.797] | 0.787 |
| `v4_mean3` | C | 6.283 [6.083, 6.746] | 6.278 [6.077, 6.731] | 6.281 [6.072, 6.729] | 0.780 |
| `v5_chopmult` | C | 6.303 [6.022, 6.763] | 6.303 [6.025, 6.760] | 6.311 [6.026, 6.758] | 0.788 |
| `v5b_chopadd` | C | 6.303 [6.022, 6.763] | 6.303 [6.024, 6.760] | 6.311 [6.026, 6.758] | 0.788 |
| `v6_topdown_geoUS` | C | 6.279 [6.091, 6.737] | 6.276 [6.089, 6.730] | 6.279 [6.090, 6.728] | 0.788 |
| `v7_mean2` | C | 6.279 [6.091, 6.737] | 6.276 [6.089, 6.730] | 6.279 [6.090, 6.728] | 0.785 |
| `v8_geo_fitted` | C | 6.263 [6.096, 6.674] | 6.268 [6.097, 6.694] | 6.270 [6.097, 6.693] | 0.788 |
| `v9_topdown_SCB` | B | 6.263 [6.100, 6.670] | 6.259 [6.096, 6.661] | 6.260 [6.103, 6.657] | 0.792 |
| `v10_topdown_SCL` | A | 6.270 [6.037, 6.718] | 6.270 [6.037, 6.718] | 6.270 [6.037, 6.718] | 0.788 |
| `v11_topdown_SCA` | A | 6.431 [6.254, 6.904] | 6.428 [6.253, 6.896] | 6.428 [6.253, 6.896] | 0.788 |
| `v12_geo_SCA` | A | 6.359 [6.162, 6.850] | 6.356 [6.164, 6.846] | 6.358 [6.166, 6.845] | 0.788 |
| `v13_chopmult_SCA` | A | 6.526 [6.134, 7.016] | 6.520 [6.130, 7.008] | 6.525 [6.133, 7.006] | 0.787 |
| `w1_mean2_SCA` | A | 6.364 [6.164, 6.853] | 6.360 [6.166, 6.847] | 6.363 [6.168, 6.847] | 0.787 |
| `w2_geo_fitted_SCA` | A | 6.387 [6.202, 6.869] | 6.383 [6.201, 6.861] | 6.385 [6.201, 6.863] | 0.782 |
| `w3_geo_SCA_rescaled` | A | 6.431 [6.254, 6.904] | 6.428 [6.253, 6.896] | 6.428 [6.253, 6.896] | 0.792 |
| `w4_geo_rescaled` | C | 6.263 [6.096, 6.674] | 6.259 [6.101, 6.663] | 6.259 [6.106, 6.659] | 0.793 |
| `w5_SC_A` | A | 6.431 [6.254, 6.904] | 6.428 [6.253, 6.896] | 6.428 [6.253, 6.896] | 0.787 |

15 November 2026, largest states, in thousand acres [80% interval]:

| State | 2025 final | `v1_geo` | `w3_geo_SCA_rescaled` | `A` | `SC` |
|---|---|---|---|---|---|
| Wisconsin | 885 | 833 [688, 1060] | 844 [701, 1068] | 836 [677, 1089] | 830 [694, 1080] |
| New York | 495 | 470 [388, 598] | 475 [395, 601] | 476 [385, 620] | 463 [387, 602] |
| South Dakota | 390 | 426 [351, 542] | 443 [368, 561] | 427 [345, 556] | 424 [355, 552] |
| Minnesota | 360 | 376 [310, 478] | 391 [325, 494] | 373 [302, 486] | 378 [316, 492] |
| California | 370 | 360 [297, 458] | 364 [302, 460] | 354 [286, 461] | 366 [306, 476] |
| Michigan | 340 | 334 [276, 426] | 338 [281, 428] | 336 [272, 438] | 332 [278, 433] |
| Pennsylvania | 315 | 326 [270, 416] | 330 [274, 418] | 326 [264, 424] | 327 [273, 425] |
| Iowa | 250 | 302 [249, 384] | 299 [249, 379] | 298 [241, 388] | 305 [255, 397] |
| Kansas | 230 | 277 [229, 352] | 282 [234, 356] | 278 [225, 362] | 275 [230, 358] |
| Nebraska | 220 | 263 [217, 334] | 303 [252, 383] | 268 [217, 349] | 258 [216, 335] |
| Idaho | 280 | 260 [214, 331] | 263 [219, 333] | 261 [211, 339] | 259 [217, 337] |
| Texas | 245 | 233 [192, 296] | 236 [196, 299] | 239 [193, 311] | 226 [189, 295] |
| Colorado | 200 | 204 [168, 259] | 209 [174, 264] | 199 [161, 259] | 208 [174, 271] |
| North Dakota | 170 | 196 [162, 249] | 202 [168, 256] | 193 [156, 252] | 198 [166, 258] |
| Ohio | 200 | 181 [150, 231] | 182 [152, 231] | 185 [149, 240] | 178 [149, 232] |

Why the Tier A drought versions are higher in 2026:
- SC_A chops 219k acres in 2026 (`out/params.csv`). The largest amounts are Nebraska 88k, Minnesota 29k and South
  Dakota 25k.
- SC chops 13k, because NASS's November yield forecast shows no shortfall over 10% in those states.
- The Drought Monitor measures weather, not crop loss. Irrigated corn does not fail in a dry summer, and about 57%
  of Nebraska's grain acres were irrigated in 2017 (Quick Stats survey: 5.28M of 9.30M).
- This is the known failure mode of the Tier A proxy. SC_A's 2026 US total is 2.7% above SC's. If the drought did
  not cut yields, that gap is over-prediction.

## 10. Sensitivity of the Drought Monitor threshold (information only; `out/sensitivity_drought_tau.csv`)

SC_A and v12_geo_SCA with other D2+ thresholds, 15 Nov, state WAPE / mean |US|:

| TAU_D | SC_A 12-24 | SC_A 17-24 | v12 12-24 | v12 17-24 |
|---|---|---|---|---|
| 0.00 | 13.29 / 3.56 | 12.66 / 3.63 | 13.00 / 4.11 | 12.30 / 3.77 |
| 0.05 | 13.20 / 3.54 | 12.59 / 3.62 | 13.02 / 4.13 | 12.27 / 3.76 |
| 0.10 | 13.24 / 3.52 | 12.57 / 3.65 | 13.08 / 4.14 | 12.27 / 3.78 |
| 0.20 | 13.26 / 3.62 | 12.52 / 3.74 | 13.07 / 4.15 | 12.29 / 3.83 |
| 0.30 | 13.09 / 3.51 | 12.46 / 3.53 | 13.12 / 4.20 | 12.36 / 3.72 |

The Tier A result does not depend on the arbitrary 0.10. Across thresholds, SC_A stays at 13.09-13.29 / 3.51-3.62
on 2012-2024.

## 11. Deviations from the pre-registration

- D1 (descriptive label only): round 1 compared "beats both on point estimates" without a float tolerance. v2's US
  total equals SC's by construction but printed False. A 1e-6-point tolerance was added. A second descriptive label,
  "at least as good as the better of A and SC on each metric" (`beats_both_strict`), was added in round 2. Neither
  label enters the rule.
- D2 (check only): round 1 compared the c5b 2026 forecast with the folder's US-only table, so the check said
  UNCOMPUTED. It now uses the folder's state table `forecast_2026.csv` and matches.
- D3: round 2 (section 1b) was added after the round-1 scores, at the user's request to "try other variations". It
  was hashed before scoring and cannot change the round-1 headline.
- Code: `--components-cache` is a scratch speed-up. The final outputs come from a clean run without it. Its
  `summary.csv` is byte-identical to the cached run's.

## 12. Limitations

- 13 test years and one standard-error rule. The 2SE bar is crossed or missed by hundredths of a point (v1 -0.089;
  v2 and w4 +0.013). With 19 candidates, one of the five RECOMMENDED could pass by chance. Every joint
  years x states 90% interval includes 0.
- The truth is NASS's own state series. The team's noise-floor study (`test_models/accuracy/noise_floor`) puts about
  10 of the 13 points of state error in that series.
- This is a replay with current-vintage Quick Stats, FSA dates from `kernelag.fsa` (corrected, with assumed dates
  before 2025) and today's RMA files (read by A-S3's loader, not used by s3). It is not an archived real-time test.
- Every primary candidate is Tier C, because SC reads NASS's in-season grain-acre and yield forecasts. Only the SC_A
  and SC_L combinations are Tier A, and none of them is RECOMMENDED.
- `v8_geo_fitted` and `w2_geo_fitted_SCA` fit one weight on 2012..t-1, with a null weight of 0.5 in 2012-2014.
  The other candidates fit nothing beyond their component models.
- The Drought Monitor proxy over-chops irrigated states (2026 Nebraska). It is also worse in the year after a big
  drought: SC_A's 2013 state WAPE is 18.97 against SC's 15.89, after it estimated 959k chopped acres for 2012
  (`out/params.csv`), which it subtracts from the level.
- 2025 is never scored here. The component models' 2026 predictions use 2025 finals as history, as in their folders.
- The intervals are retrospective. State leave-one-year-out coverage is 0.78-0.79 for the nominal 80%. The US
  interval rests on 13 yearly errors.

## 13. Run

```
.venv/Scripts/python.exe -B test_models/variations/silage_combos/run.py          # about 5 minutes
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider test_models/variations/silage_combos
.venv/Scripts/python.exe -B test_models/variations/silage_combos/tables.py       # prints the tables above
.venv/Scripts/python.exe -m ruff check --select E,F,W --line-length 120 test_models/variations/silage_combos
```
