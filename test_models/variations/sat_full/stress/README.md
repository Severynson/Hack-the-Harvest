# sat_full/stress: the sat_stress index on the full state sample, with the CDL mask and a real-time mask

Question: the pre-registered satellite stress index of `test_models/variations/sat_stress/` tracked crop stress
on 10 areas per state and 2019-2024 (r = 0.43 with NASS's yield shortfall, 0.44 with the Drought Monitor D2+
change, 0.16 with the NASS silage change, 2020-2024). Does it hold on the full sample (20 areas per state,
2016-2026), and does it survive when the corn fields come from the real-time imagery mask P of
`../corn_mask/` instead of that year's Cropland Data Layer (CDL), which is published after the season?

Code: `stress.py`. Outputs: `out/`. Nothing outside this folder (and the agent scratch folder) is written;
`kernelag/`, `test_models/variations/sat_stress/` and `../corn_mask/` are read or imported, never modified.

---

## 1. Pre-registration

Written before any stress value or correlation of this study was computed (the only numbers seen beforehand
are the sat_stress results above and the corn_mask agent's report). The text from the heading above to the end
marker is hashed into `out/preregistration.sha256` before the first run; `stress.py` stops if it changes. Later
notes go below the marker.

### 1.1 Data and look-ahead rules

- States: the 15 sampled states (FIPS 06 CA, 08 CO, 16 ID, 19 IA, 20 KS, 26 MI, 27 MN, 31 NE, 36 NY, 38 ND,
  39 OH, 42 PA, 46 SD, 48 TX, 55 WI). Maryland is not in the sample and is not used.
- Field-years: every candidate field-year of `data/samples/candes_<fips>.parquet` (2019-2021, 2023-2026),
  `candpc_<fips>.parquet` (2018, 2022) and `candpc16_<fips>.parquet` (2016, 2017; other field ids), 300 areas
  (draw 1 + draw 2). Geometry is not read. Only areas returned by `kernelag.state_signal.complete_areas` are used
  (all 300 expected).
- Series: `data/s2_series/<stem>/<cell>_<year>.csv`, read with `field_id` as text (through
  `corn26.read_series_file`; never `kernelag.field_model.load_series`).
- Looks: `valid_frac >= 0.5` and NDVI present, dated on or before 15 September of the crop year (the
  `kernelag.state_signal.series_asof` rule at sep). Cloud and haze dips removed per field-year with
  `kernelag.features.drop_dips` after the cut. Per field-year components are computed by importing
  `field_components` from `test_models/variations/sat_stress/run.py` unchanged, so the composite is the same.
  Components are computed for every candidate field-year once; masks only select which field-years enter a
  state median.
- Imagery-source caveat (not corrected): Planetary Computer for 2016-2018 and 2022, Earth Search for the other
  years; 2016 has Sentinel-2A only and its series start 1 June (about half the looks), which biases the 2016
  peak NDVI (a maximum over looks) downward. Prior-year anomalies inherit any level shift between sources.

### 1.2 Corn masks (which field-years enter a state median)

- **CDL** (look-ahead reference, as in sat_stress): `is_corn == 1` (that year's CDL), 2016-2025.
  2026: "UNCOMPUTED: no 2026 CDL".
- **P** (headline real-time mask): `is_corn_P == 1` at asof `sep` in `../corn_mask/out/corn_calls.parquet`
  (corn26 recipe, trained on years before t only, features cut at 15 Sep, threshold 0.5), 2017-2026. 2016:
  "UNCOMPUTED: no prior-year model" (`p_corn_P_alt` is not real-time and is not used). Anomalies use prior P
  years only (same mask throughout).
- **P_cdlref** (information): current year from mask P, reference (prior-years mean) from the CDL-mask values of
  earlier years. Earlier CDLs are public before 15 Sep of year t, so this is real-time too, but it mixes two
  masks. It gives 2017 an anomaly (against 2016 CDL). 2017-2026.
- **P_nov** (information): `is_corn_P == 1` at asof `nov` (higher recall), same 15 Sep looks, anomalies against
  prior P_nov years; available from 15 Nov only. 2017-2026.

### 1.3 Index (the sat_stress composite)

- Components per field-year: `peak` = max NDVI 1 Jun-15 Sep (>= 3 looks); `ndmi` = mean NDMI 1 Aug-15 Sep
  (>= 2 looks); `decline` = `peak` minus the median NDVI 1-15 Sep (>= 1 look and `peak` defined).
- X(s,t) = median over the mask's field-years of state s and year t where the component is defined; missing if
  fewer than 50 such field-years. Weighting: **none** (headline: unweighted median, as sat_stress) and **pps**
  (sensitivity: weighted median with weight `acres / cell_size_acres`, the area weight of
  `kernelag.state_signal.share`).
- Anomaly against the state's PRIOR years only: A(s,t) = X(s,t) - mean of X(s,y) over the mask's years y < t
  where X is defined (reference years start in 2016 for CDL and P_cdlref, 2017 for P and P_nov). No anomaly in a
  mask's first year (2016 CDL; 2017 P, P_nov). The CDL 2017 anomaly rests on 2016 alone; the P 2018 anomaly on
  2017 alone.
- Scale, two versions (only information available at 15 Sep of year t):
  - **rms** (headline, the sat_stress rule): sigma(t) = root mean square of A(s,y) over the 15 states and all
    years from the mask's first anomaly year through t.
  - **xsd** (requested "pooled cross-state SD"): sigma(t) = sqrt( sum over y, s of (A(s,y) - Abar(y))^2 /
    sum over y of (n_y - 1) ), years from the first anomaly year through t, Abar(y) = mean of A over the states of
    year y. It is the cross-state SD of the anomalies pooled over years, so a shift common to all states in one
    year (imagery source, look count, an odd reference year) does not inflate it. For the first anomaly year it
    is that year's cross-state SD.
  - Z(s,t) = A(s,t) / sigma(t).
- **stress(s,t) = ( -Z_peak - Z_ndmi + Z_decline ) / 3**; missing if any component is missing (counted).
  Positive = stressed canopy = expected MORE silage.
- Availability by forecast date: the index uses looks up to 15 Sep only, so it exists from 15 Sep; the 15 Oct,
  15 Nov and 15 Dec values equal the 15 Sep value (P_nov from 15 Nov). 15 Jul and 15 Aug: "UNCOMPUTED: the
  index window ends 15 Sep"; the fallback is no stress adjustment (stress read as 0, base unchanged).

### 1.4 Targets (truth tier noted)

- `shortfall`: 1 - NASS in-season corn-grain yield as of 15 Nov / linear trend of the 10 previous final yields
  (`_shortfall` of sat_stress, imported; Tier B, the drought input of SC). Information: the same as of 15 Sep,
  and `shortfall_final` with the final yield (known only after the season).
- `d_drought`: Drought Monitor D2+ share, Jun-Sep mean, minus the state's mean over prior years since 2000
  (`drought_change` of sat_stress, imported; Tier A).
- `silage_change`: log(S(t) / S(t-1)), S = NASS final state silage acres, the `actual` column of
  `test_models/ownModels/monthly/out/monthly_by_state_year.csv` (model `s3_fsa_residual`, asof nov), checked
  against `kernelag.state_panel.load_panel`.
- Diagnostics (information): residuals log(actual / pred) at 15 Nov of A-S3 (`s3_fsa_residual`, monthly harness,
  corrected FSA dates), reversion (`reversion_only_H00`, monthly harness), SC and SC_A
  (`test_models/variations/silage_combos/out/backtest_by_state_year.csv`). Persistence's residual is
  `silage_change`.

### 1.5 Correlations

- Pearson (with p) and Spearman (with p) of stress and of each signed component (-Z_peak, -Z_ndmi, +Z_decline)
  with every target, over state-years of a window: **W17 = 2017-2024** (CDL, P_cdlref) and **W18 = 2018-2024**
  (every mask; the common window for comparing CDL and P). 2025 and 2026 never enter a correlation.
- Within-year Pearson: x and y each demeaned by their year mean over the state-years of the window; p from a
  t test with n - 2 - (years - 1) degrees of freedom. It measures the cross-state signal only and is immune to
  shifts common to a year.
- Mask agreement (W18): Pearson of the stress, of each Z and of each X between P (and P_nov, P_cdlref) and CDL;
  mean X(P) - X(CDL) per component.
- Replication check (not an index version): CDL mask, draw-1 areas only, years 2019-2024, reference from 2019,
  sigma from 2020, compared with `test_models/variations/sat_stress/out/stress_by_state_year.csv` (draw-1 corn
  fields of candes are the old `corn_<fips>` fields). Expect near-identical values.
- Nothing is fitted: the reference means and scales are expanding over prior years (the scale also uses the
  current year's cross-section, available at 15 Sep); the P mask is the corn_mask agent's expanding-window
  model; the shortfall trend uses the 10 previous years.

### 1.6 Reading rules (fixed now; headline variant = weight none, scale rms)

- **R1 (stress signal):** CDL, W17: Pearson r(stress, shortfall) > 0 and r(stress, d_drought) > 0, both
  p < 0.05.
- **R2 (silage link):** CDL, W17: Pearson r(stress, silage_change) > 0 with p < 0.05; also reported within-year.
- **R3 (real-time mask keeps the index):** W18: r(stress_P, stress_CDL) >= 0.80, and for each of the three
  targets |r_P - r_CDL| <= 0.10 (Pearson).
- R1-R3 are also reported for P (W18) and for the other variants as information. Several tests, no multiplicity
  correction: a pass is evidence, not proof.
- Expectations written now: R1 passes (sat_stress 0.43 / 0.44); R2 fails (sat_stress 0.16, p 0.17); decline
  stays uninformative; R3 is uncertain because P under-calls corn in TX, CO, KS and over-calls ND, ID, but an
  anomaly against the same mask's prior years cancels a stable mask bias; 2017 CDL anomalies are distorted by the
  sparse 2016 looks (peak biased low in 2016, so 2017 peak anomalies positive and stress negative in most
  states), which the xsd scale and the within-year correlation partly guard against.

### 1.7 Outputs

- `out/stress.csv`: state, state_fips, year, mask, weight, scale, n_fields, per component n, X, reference mean,
  A, sigma, Z; stress; available_from; note (UNCOMPUTED reasons).
- `out/correlations.csv`, `out/mask_agreement.csv`, `out/reading_rules.csv`, `out/replication_check.csv`,
  `out/targets_state_year.csv`, `out/run.json`; cache `out/cache/field_components.parquet`.

<!-- end of pre-registration -->

---

## 2. Results (pre-registered analysis; run 2026-11-15, hash unchanged, checked by `stress.py` at start)

Run: components 3,300 series files with 20 workers (about 6 min, cached); index and report 55 s. All numbers come
from `out/`; none were typed by hand. "r" is Pearson over state-years unless marked.

### 2.1 Checks

- **Coverage.** 1,083,954 candidate field-years, 0 incomplete areas dropped, 951,993 with all three components.
  The CDL mask selects 41,295-44,591 field-years per year; P (Sep 15 call) 30,809 in 2017 and 34,592-47,850 in
  2018-2026. Every state-year has more than 50 fields per component, so no stress value is missing except by
  design (CDL 2026, P 2016, and each mask's first year: no anomaly). (`out/run.json`)
- **Looks.** Median clear looks per CDL corn field up to 15 Sep: 5 in 2016, 8 in 2017, 14-18 in 2018-2025.
- **Replication of sat_stress.** CDL mask, draw-1 areas, 2019-2024, reference from 2019: the state medians match
  `sat_stress/out/stress_by_state_year.csv` within 0.003 (peak, NDMI) and 0.012 (decline), and the stress within
  0.038 (r = 0.9998, 75 state-years). Its r with the shortfall is 0.426 (sat_stress: 0.43). The code
  reproduces the old index. (`out/replication_check.csv`, `out/posthoc_decomposition.csv` row a)
- **Truth.** The monthly harness silage `actual` equals `kernelag.state_panel.load_panel` (180 values) and the
  silage_combos `actual` (195 values) exactly (max difference 0).

### 2.2 Reading rules (`out/reading_rules.csv`)

| rule | variant | result | detail |
|---|---|---|---|
| R1 stress signal | CDL, 2017-2024 | **fail** | r(shortfall) 0.155 (p 0.093); r(D2+ change) 0.375 (p < 0.001) |
| R2 silage link | CDL, 2017-2024 | **fail** | r(silage change) 0.058 (p 0.53); within-year 0.057 (p 0.55) |
| R3 real-time mask keeps the index | P vs CDL, 2018-2024 | **fail (narrowly)** | r(stress P, stress CDL) 0.871 (needs >= 0.80: met); r gaps shortfall -0.035, D2+ -0.077, silage change -0.101 (limit 0.10) |

Expectations: R1 was expected to pass and did not. The D2+ half holds, but the shortfall half does not. R2 failed,
as expected. The R3 failure rests on 0.001 of the silage-change gap, and the two correlations being compared are
both near zero (0.098 and -0.003). With the xsd scale, R3 would pass (gap -0.099; information only).

### 2.3 Correlations, headline variant (unweighted medians, rms scale; `out/correlations.csv`)

| x | window, mask | shortfall | D2+ change | silage change | within-year: shortfall / D2+ / silage |
|---|---|---|---|---|---|
| stress | 2017-24, CDL (n 119-120) | 0.155 (p 0.09) | 0.375 (<0.001) | 0.058 (0.53) | 0.180 / 0.355 / 0.058 |
| stress | 2018-24, CDL (n 104-105) | 0.135 (0.17) | 0.403 (<0.001) | 0.098 (0.32) | 0.185 / 0.401 / 0.102 |
| stress | 2018-24, **P** (real-time) | 0.100 (0.31) | 0.326 (0.001) | -0.003 (0.97) | 0.163 / 0.313 / -0.006 |
| stress | 2017-24, P_cdlref | 0.122 (0.18) | 0.330 (<0.001) | -0.020 (0.83) | 0.154 / 0.297 / -0.025 |
| stress | 2018-24, P_nov | 0.081 (0.42) | 0.328 (0.001) | -0.002 (0.98) | 0.119 / 0.323 / -0.012 |
| -Z_peak | 2017-24, CDL | 0.276 (0.002) | 0.403 (<0.001) | 0.235 (0.010) | |
| -Z_ndmi | 2017-24, CDL | 0.118 (0.20) | 0.364 (<0.001) | -0.021 (0.82) | |
| +Z_decline | 2017-24, CDL | -0.055 (0.55) | 0.068 (0.46) | -0.089 (0.33) | |
| -Z_peak | 2018-24, P | 0.229 (0.02) | 0.261 (0.007) | 0.185 (0.058) | |

- **The index tracks the Drought Monitor (Tier A) under every mask** (r 0.33-0.40, within-year 0.30-0.40). It is
  only weakly related to NASS's in-season yield shortfall (0.08-0.16; 0.25 with the final-yield shortfall, CDL).
  It is not related to the silage change.
- **Decline is uninformative again** (r -0.06 to 0.09 with every target), as in sat_stress. NDMI follows drought
  but not yield or silage. **Peak NDVI is the only component linked to silage**: -Z_peak has r 0.235 with the
  silage change (p 0.010) and 0.28-0.29 with the A-S3 and SC residuals (CDL, 2017-2024). The composite dilutes it
  with two components that carry no silage signal.
- **Base residuals (information):** the composite's r with log(actual/pred) at 15 Nov is 0.094 for A-S3, 0.111 for
  reversion, 0.122 for SC and 0.051 for SC_A (CDL, 2017-2024). Under P (2018-2024) it is 0.089, 0.125, 0.121 and
  0.064. All p > 0.15.
- **Variants barely matter.** xsd vs rms changes every stress correlation (all targets, all masks) by at most
  0.013. pps weighting raises the CDL correlations by up to 0.03 and lowers the P ones (D2+ 0.270 vs 0.326). The
  cause was not checked: possibly the area weights put more mass on areas where the mask is less reliable.
- **2017 and the pooled cross-state SD (requested).** The CDL 2017 anomaly rests on 2016 alone. Its rms scale
  (0.0138 / 0.0574 / 0.108 for peak / NDMI / decline) and its xsd scale (0.0142 / 0.0548 / 0.0998) are almost equal.
  The 2017 mean stress is -0.244 (rms) and -0.264 (xsd). The 2017 cross-state r with shortfall / D2+ / silage
  change is 0.146 / 0.036 / -0.259 (rms) and 0.134 / 0.013 / -0.282 (xsd). The 2017 values are uninformative under
  either scale.
  The pre-registered mechanism (a low 2016 peak pushing the 2017 peak anomaly up) did not show: the mean 2017 peak
  anomaly is -0.0015. The negative 2017 mean comes from decline (-0.049) and NDMI (+0.022).

### 2.4 Real-time mask P against CDL (`out/mask_agreement.csv`, 2018-2024, headline variant)

- Stress: r = 0.871, mean |P - CDL| = 0.24. State medians agree closely (r 0.92 peak, 0.86 NDMI, 0.92 decline;
  mean |diff| 0.009, 0.033 and 0.021). The z-scores agree less well (r 0.81, 0.81 and 0.91), because the anomaly
  magnifies small level differences.
- By state (`out/posthoc_state_agreement.csv`): r >= 0.94 in 10 states (IA, WI, OH, NE, MN, NY, MI, PA, ID, CA),
  0.87-0.89 in SD and ND, and **0.48 in Kansas, 0.67 in Texas, 0.68 in Colorado**. Those three are the states where
  the corn_mask agent's P under-calls corn (ratio 0.70-0.86).
- **Do not mix masks.** P_cdlref (P this year against CDL-mask prior years) agrees with CDL at r = 0.47 only. The
  mask bias moves z_peak by +0.31 and z_ndmi by +0.50 on average. A real-time index must use the same mask for its
  reference years.
- P_nov (the 15 Nov mask, higher recall) is no better than P (r 0.851 with CDL; correlations within 0.02 of P).

### 2.5 By forecast date, and 2026

| date | stress available | value used |
|---|---|---|
| 15 Jul, 15 Aug | UNCOMPUTED: the index window ends 15 Sep | fallback: no stress adjustment (stress read as 0) |
| 15 Sep, 15 Oct | yes | mask P (Sep 15 call), looks to 15 Sep |
| 15 Nov, 15 Dec | yes | same value (P_nov available, not better) |

2026 (P, real-time, ready since 15 Sep 2026; `out/stress.csv`, `out/posthoc_2025_2026.csv`): the highest values
are Colorado 3.48, Texas 3.30, California 2.11 and Kansas 0.83, against a 2018-2025 P range of about -1.3 to
2.7. Colorado's D2+ share rose by 0.51 over its prior-years mean in 2026, which is consistent. In Texas (D2+ change
-0.01) and California (-0.32) the drought data do not show stress. Across states in 2026, r(stress P, D2+ change)
is 0.13 (p 0.64). Texas, Colorado, Kansas and California are the states where mask P fails, so treat their 2026
values as possible mask artifacts. The 2026 CDL index is UNCOMPUTED (no 2026 CDL).

<!-- section 2 computed by stress.py; section 3 is post hoc -->

## 3. Post-hoc checks (written after section 2 was seen; nothing here is eligible)

`explore.py` writes `out/posthoc_*.csv`.

- **Why the shortfall link fell from 0.43 to 0.16** (`posthoc_decomposition.csv`, 2020-2024, CDL): draw-1 areas
  with the 2019 reference give 0.426 (sat_stress). Draw-2 areas alone give 0.207, both draws 0.262, and the full
  2016+ reference 0.146. About half of the drop is the sample: the first 10 areas per state were a favourable
  draw. The other half comes from the longer reference: 2016-2018 come from Planetary Computer with 5-16 looks, so
  their state means can shift the anomalies of later years. The D2+ link holds throughout (0.44, 0.39, 0.43, 0.36).
  sat_stress's r = 0.43 with the shortfall was partly luck of the draw.
- **2019, the late-planted year, flips the sign** (`posthoc_by_year.csv`): the cross-state r with the shortfall
  is -0.555 (CDL) and -0.683 (P), and the mean stress is -0.50. Late corn has not browned by 15 Sep (low
  decline) and is still moist (high NDMI), so the index reads it as unstressed while yields fell. A
  fixed-calendar window confuses late phenology with health, which is the "one harvest calendar" trap the USDA
  reps named. Other years are mostly positive (2018: 0.66; 2021: 0.50).
- **Peak-only and peak + NDMI** (`posthoc_variants.csv`). Both indices come from sat_stress's own post-hoc list,
  so 2017-2019 are years those hypotheses had not seen (draw-2 areas are also new for 2020-2024):
  - peak only (-Z_peak), CDL 2017-2019: r with silage change 0.309 (p 0.039), A-S3 residual 0.343 (p 0.021), SC
    residual 0.338 (p 0.023), shortfall 0.208 (p 0.17). P 2018-2024: silage change 0.185 (p 0.058), A-S3 residual
    0.273 (p 0.005), SC residual 0.294 (p 0.002).
  - peak + NDMI, CDL 2017-2019: silage change 0.142 (p 0.35), D2+ 0.389 (p 0.008). It tracks drought best but not
    silage.
  - Reading: peak NDVI alone is the candidate worth a new pre-registration (scored on 2026 finals, never on
    2025). Peak is a maximum over looks, so it is sensitive to the 2016-2017 look counts. A per-region calendar
    (peak window by state) is the other change the 2019 result points to.

## 4. What this means for the team

- **The full sample does not confirm the sat_stress index as a yield or silage signal.** It is a robust drought
  signal (r 0.33-0.40 with the Tier A Drought Monitor under every mask). Its link to NASS's yield shortfall falls
  from 0.43 to 0.16 (not significant) when the other 10 areas per state and the years 2017-2019 are added. Its link
  to the silage change is zero. Expect the c3 "small nudge" gains of sat_stress (within noise already) to shrink
  on this sample. Re-scoring c3 on the full sample was not part of this task: "UNCOMPUTED: not requested".
- **The real-time mask is not the bottleneck.** P reproduces the CDL index at r 0.87 overall and >= 0.94 in 10
  states. It fails in Kansas, Texas and Colorado, the states where it fails to find corn.
- **Hypothesis for the next round:** a peak-NDVI-only index with the same mask for every reference year,
  per-region windows, and a fixed small coefficient, pre-registered and scored on 2026.

## 5. Limitations

- Only 7-8 scoring years (2017/2018-2024) and 15 states. Three reading rules plus information variants, with no
  multiplicity correction. 2025 and 2026 are in `stress.csv` but in no correlation.
- The CDL mask is look-ahead. P's 2017 model was trained on 2016 alone (weak, recall 0.66), so P starts its anomalies
  in 2018. The P mask is the corn_mask agent's output and was not re-checked here.
- Imagery-source shift (Planetary Computer 2016-2018 and 2022, Earth Search otherwise) and the low 2016-2017 look
  counts are not corrected. They enter every anomaly through the reference means.
- Unweighted medians summarise each state by its PPS-drawn areas, which over-represent corn-dense areas (pps
  weighting is reported as a sensitivity).
- The yield shortfall at 15 Nov uses NASS's November forecast (Tier B). The silage change and the residuals use
  NASS finals, available after the season.
- Within-year p-values treat state-years as independent after removing year means. Spatially correlated weather
  makes them optimistic.

## How to run

```bash
.venv/Scripts/python.exe test_models/variations/sat_full/stress/stress.py --workers 20   # ~6 min first run, ~1 min cached
.venv/Scripts/python.exe test_models/variations/sat_full/stress/explore.py               # post-hoc checks, ~1 min
.venv/Scripts/python.exe -m ruff check --select E,F,W --line-length 120 test_models/variations/sat_full/stress/
```

`stress.py` reuses `out/cache/field_components.parquet` unless `--force` is passed. It stops if README section 1
no longer matches `out/preregistration.sha256`. It needs `../corn_mask/out/corn_calls.parquet` (local only, 64 MB).
