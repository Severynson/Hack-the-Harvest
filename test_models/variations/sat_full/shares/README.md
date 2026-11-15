# shares: silage-like share per state, year and forecast date on the full state sample

Question: on the full state sample (15 states, 300 areas of 10 km, draws 1 and 2), what share of the corn acres
look silage-like to each of the two pre-registered Quebec field classifiers (K0, K1), per state, year 2016-2026 and
forecast date (15 Aug to 15 Dec), under a CDL corn mask (not real-time) and the imagery corn mask P (real-time)?
Does the year-to-year change of that share follow the change of NASS's final silage acres, is it larger than its
sampling noise, and is its bias stable across years?

Code: `shares.py`. Outputs: `out/`. Nothing outside this folder (and the agent scratch folder
`.../scratchpad/agents/shares/`) is written. `kernelag/`, `test_models/ownModels/satellite/signal/`,
`test_models/ownModels/satellite/corn26/`, `test_models/variations/field_variants/` and
`test_models/variations/sat_full/corn_mask/` are imported or read, never modified.

---

## 1. Pre-registration

Written on 2026-11-15 before any harvest feature, field probability, share or diagnostic of this study was
computed. The text between the two marker lines is hashed (SHA-256 of its UTF-8 bytes, LF line endings) into
`out/preregistration.sha256` before the first computing run; every step of `shares.py` refuses to run if it no
longer matches. Later notes go below the end marker and never change this section.

<!-- PREREGISTRATION:BEGIN -->
### 1.1 Data

- States: the 15 sampled states (FIPS 06 CA, 08 CO, 16 ID, 19 IA, 20 KS, 26 MI, 27 MN, 31 NE, 36 NY, 38 ND,
  39 OH, 42 PA, 46 SD, 48 TX, 55 WI). Maryland is not in the sample and is never used.
- Field-years: every candidate field-year of `data/samples/candes_<fips>.parquet` (2019-2021, 2023-2026),
  `candpc_<fips>.parquet` (2018, 2022) and `candpc16_<fips>.parquet` (2016, 2017; field ids of the 2015-2022 Crop
  Sequence Boundaries edition). Geometry is never read. Area attributes (cell, cell_size_acres, draw, acres) are
  taken from `test_models/variations/sat_full/corn_mask/out/corn_calls.parquet`, which carries them from the same
  files; the number of field-years per stem, cell and year must equal the sample files (gate G0).
- Complete areas only: `kernelag.state_signal.complete_areas` on each stem's sample and series folder. An
  incomplete area is dropped from every year of that state and counted.
- Series: `data/s2_series/<stem>/<cell>_<year>.csv`, read file by file with
  `test_models/ownModels/satellite/corn26/corn26.read_series_file` (field_id as text; same normalisation and
  de-duplication as `kernelag.field_model.load_series`, which is never used on these files).
- Imagery source: Earth Search for 2019-2021 and 2023-2026, Planetary Computer for 2016-2018 and 2022; 2016 has
  Sentinel-2A only. Not corrected. Removing year medians (1.7) absorbs any shift common to all states in a year.

### 1.2 Forecast dates and the cut

- Dates: 15 Aug, 15 Sep, 15 Oct, 15 Nov, 15 Dec of the crop year (labels aug, sep, oct, nov, dec).
- Cut: `kernelag.state_signal.series_asof` (only looks dated on or before the 15th). `kernelag.context.ASOF_MONTH`
  has no dec key; `shares.py` adds `dec = 12` to that dict at run time in its own processes (no file is edited).
  The series run to 30 Nov, so dec is the full season.
- UNCOMPUTED cells (rows present, share NaN, reason in `status`): CDL mask in 2026 (no 2026 CDL); P mask in 2016
  (no prior year to train the corn mask, as in corn_mask); 15 Dec 2026 (in the future; the 2026 series end about
  12-14 Nov 2026).

### 1.3 Harvest features

`kernelag.features.build_features` (unchanged) on each field-year's series cut at the date, for every candidate
field-year (not only corn), cached per stem under `out/cache/features/`. Assessable = `max_drop` not NaN
(`kernelag.state_signal.area_totals`). Features are computed in parallel (multiprocessing, at most 20 workers).

### 1.4 Field classifiers (fixed; fitted on Quebec only; never on US data, NASS numbers or Maryland)

- **K0**: `kernelag.field_model.make_model()` (median imputer, scaler, balanced logistic, C = 0.5) on
  `MODEL_FEATURES`, fitted on every assessable field-year of `quebec_maize_2023` + `qc_regions_2023` (17 cells),
  through `test_models/ownModels/satellite/signal/signal.fit_allqc_model`. Gate G1: 3,128 training rows and the
  Quebec leave-one-cell-out confusion counts TP 877 / FP 345 / FN 390 / TN 1516.
- **K1**: `f1_xgb_mono` of `test_models/variations/field_variants/variants.py` (its `SPECS`, `fit` and `predict`,
  imported): XGBoost with fixed settings and monotone constraints on `MODEL_FEATURES`, fitted on every assessable
  full-season field-year of `qcm_2019` ... `qcm_2026`. Its feature cache is redirected to this agent's scratch
  folder (`FIELD_VARIANTS_CACHE`). Gate G2: per-year rosters equal `variants.R1_EXPECTED` (2019-2024, 2026).
- **K1_xs** (sensitivity, information only): K1 refitted without the Quebec season equal to the target year
  (2019-2026; identical to K1 for 2016-2018). K1 and K0 see Quebec labels of the target season for some years
  (K1: 2019-2026; K0: 2023). These are other-region labels, not US truth; K1_xs measures whether that matters.
  It is never a headline.
- Both classifiers are fitted once on full-season Quebec features and applied to US features cut at each date
  (the as-of convention of `kernelag.evaluate` and field_variants split 4). Probability = `predict_proba[:, 1]`
  on assessable rows, NaN otherwise. Nothing is tuned; no threshold enters the share (the 0.5 call share is an
  extra column).

### 1.5 Corn masks

- **CDL** (not real-time): `is_corn_cdl == 1` (that year's Cropland Data Layer), 2016-2025.
- **P** (real-time): `is_corn_P == 1` at the same date as the share (corn_mask regime P: trained on years before
  the target year), 2017-2026 (dec: 2017-2025).

### 1.6 Share per state, year, date, classifier, mask and draw pool

- Per area (cell) and year, over the field-years in the mask: `fields` (count), `sampled_acres` (acres),
  `corn_acres` (acres of assessable field-years), `silage_like_acres` (acres x probability, assessable only),
  `called_silage_acres` (acres with probability >= 0.5), exactly as `kernelag.state_signal.area_totals`.
- `share` = `kernelag.state_signal.share` on those area totals: sum(silage_like_acres / cell_size_acres) /
  sum(corn_acres / cell_size_acres). `share_se` = `kernelag.state_signal.jackknife_se` over the areas with
  corn_acres > 0. `areas` = areas with at least one mask field-year; `fields` = mask field-years;
  `assessable_share` = sum corn_acres / sum sampled_acres (unweighted, as `state_table`). Gate G3: on these totals
  `kernelag.state_signal.state_table` gives the same rounded share and SE.
- Draw pools: **"1+2"** (both draws, 20 areas per state; headline) and **"1"** (draw 1, 10 areas; for comparison
  with the earlier round).
- Fallback label (`status`): "fallback: assessable_share < 0.5" when fewer than half the mask acres have a found
  drop, "fallback: assessable areas < 5" when fewer than 5 areas have assessable corn; otherwise "ok". A
  fallback row keeps its share (information) but a downstream model should use its base forecast there.

### 1.7 Truth

NASS final state silage acres harvested: `actual` of the `s0_persistence` rows of
`test_models/ownModels/monthly/out/monthly_by_state_year.csv` (2012-2024). 2025 (information only) from
`data/panel/state_year.csv` `silage`, which equals the monthly `actual` for 2016-2024 (checked). NASS final grain
acres for the count ratio: `data/panel/state_year.csv` `grain`.

### 1.8 Diagnostics (information only; nothing is fitted to NASS, nothing is selected)

Computed per classifier (K0, K1; K1_xs as sensitivity), mask (CDL, P), date and draw pool.

- **D1 change association.** x = ln share(t) - ln share(t-1) on the same areas, y = ln NASS silage(t) - ln NASS
  silage(t-1). Window: transitions t = 2017-2024 for CDL (8 x 15 = 120), t = 2018-2024 for P (P has no 2016
  share; 105); both masks also on the common window 2018-2024. Each year's median across the 15 states is
  subtracted from x and from y; then the pooled Spearman rho. 90% CI: 2,000 bootstrap draws of whole states
  (seed 0), year medians recomputed on each draw. Two-sided p: 10,000 permutations of x across states within
  each year (seed 0). Sign agreement count (after median removal). Sensitivity: without t = 2018 (the transition
  2017 -> 2018 crosses the field-id edition). 2024 -> 2025 is reported separately (information only).
  Also on the earlier round's own shares (`test_models/ownModels/satellite/signal/out/state_satellite_asof_*.csv`,
  draw 1, CDL, K0, sep/oct/nov) for t = 2020-2024 next to this study's draw-1 and 1+2 shares on the same
  transitions.
- **D2 signal-to-noise.** Per transition, the same-area jackknife SE of the change (each area left out of both
  years at once; n = areas with corn_acres > 0 in either year; SE = sqrt((n-1)/n x sum (theta_i - mean)^2)), for
  d share and d ln share. Per state over the D1 window: `snr` = SD of d ln share / RMS of its SE; `snr_share` =
  the same on the share scale (the earlier round's measure); `nass_snr` = SD of d ln NASS silage / RMS SE of
  d ln share (what a share moving one-for-one with NASS in log terms would give). Reported: median, min, max
  over states.
- **D3 count-ratio stability.** ratio(t) = share(t) / NASS silage share(t), NASS share = silage / (silage + grain)
  (final acres harvested). Per state over the years 2016-2024 (CDL) or 2017-2024 (P): mean ratio, SD of ln ratio,
  swing (max - min). Summary: median over states. Year effect: per year the median across states of ln ratio, and
  the SD of that across years. The same for the 0.5-call share (the analogue of field_variants' count ratio).
- **D4 level.** Across the 15 states, Spearman and Pearson of the state's mean share over the window years with
  its mean NASS silage share, and the OLS line share = a + b x NASS share (information only; never used to
  predict anything).
- **D5 assessability.** Assessable share and fallback count per date.

### 1.9 Reading rule and expectations (stated before any score)

- Headline cell: Nov 15, draws 1+2, D1 rho for each classifier under the P mask (real-time) and the CDL mask
  (upper bound on mask quality). A change signal is called **"present"** for a classifier and mask only if the
  90% CI lower bound of D1 rho at Nov 15 is above 0; otherwise **"not shown"**. The other dates, the draw-1 pool
  and K1_xs are descriptive. With 2 classifiers x 2 masks the headline has 4 cells; a Bonferroni reading (95% CI
  per cell, information) is also reported.
- Expectations: (E1) Nov CDL K0 rho between -0.30 and +0.20, as in the earlier round (-0.20 to -0.27 on draw 1,
  2020-2024); "not shown". (E2) K1 within 0.15 of K0. (E3) P no better than CDL. (E4) at 15 Aug the found drops are
  mostly pre-harvest noise: rho near 0, and many state-years flagged fallback at Aug and Sep. (E5) twice the
  areas lowers the jackknife SE by about 1/sqrt(2); `nass_snr` median still below 1.5. (E6) median SD of ln count
  ratio above 0.10, higher under P than CDL.

### 1.10 Outputs

- `out/shares.csv`: state, state_fips, year, asof, classifier, mask, areas, fields, assessable_share, share,
  share_se, status. Draws 1+2, classifiers K0 and K1, masks CDL and P, every year 2016-2026 and date aug..dec
  (UNCOMPUTED cells present with NaN).
- `out/shares_draw1.csv`: the same for draw 1.
- `out/shares_detail.csv`: every pool and classifier including K1_xs, plus assessable_areas, share_calls,
  share_calls_se, weighted corn and mask acres, median cut and peak day.
- `out/changes.csv`: every transition (incl. 2025 -> 2026 under P) with d share, d ln share, their same-area
  jackknife SEs and the NASS change where known.
- `out/diag_change.csv` (D1), `out/diag_snr.csv` and `out/diag_snr_by_state.csv` (D2), `out/diag_ratio.csv`,
  `out/diag_ratio_by_state.csv` and `out/diag_ratio_by_year.csv` (D3), `out/diag_level.csv` (D4),
  `out/diag_assessable.csv` (D5), `out/gates.json`, `out/run.json`.
- Caches: `out/cache/features/<stem>.parquet`, `out/cache/probs.parquet`, `out/cache/area_totals.parquet`.
<!-- PREREGISTRATION:END -->

---

## 2. Results (run 2026-11-15; pre-registration hash a6d69758... unchanged, checked by every step)

Run: `features` 2,193 s (3,300 series files, 20 workers), `probs` 25 s, `shares` 126 s, `diag` about 4 min.
1,083,954 candidate field-years, all 900 stem-areas complete (0 dropped). 5,314,024 field-year x date feature
rows; 7,660 field-year x date combinations had no series row at all and count as not assessable. The UNCOMPUTED
cells are as pre-registered: CDL 2026 (120 rows in `shares.csv`), P 2016 (150), 15 Dec 2026 (60).

**Gates (all reproduced, `out/gates.json`).** G0: field-years per stem, cell and year in corn_calls equal the
sample files (3,300 cell-years, 1,083,954 field-years). G1: K0 has 3,128 training rows; Quebec leave-one-cell-out
TP 877 / FP 345 / FN 390 / TN 1516. G2: K1 rosters equal field_variants' R1 (2019-2024, 2026); 21,975
assessable fit rows. G3: `kernelag.state_signal.state_table` on the K0 totals gives identical rounded share, SE,
call share, assessable share, areas and fields (1,485 rows, max difference 0). Information: this study's draw-1
CDL K0 shares equal the earlier round's (Pearson 0.999 or more at sep/oct/nov, median abs difference 0.00004).
D1 run on the earlier round's own shares gives -0.200 at Nov, 2020-2024; the earlier README reported -0.201.

### 2.1 D1: does the change follow NASS? (headline: Nov 15, draws 1+2)

Year medians removed, pooled Spearman of d ln share with d ln NASS silage acres (`out/diag_change.csv`).

| classifier | mask | n | rho | 90% CI | 95% CI | 97.5% CI (strict Bonferroni, 4 cells) | p (perm.) | signs agree | reading |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| K0 | CDL | 120 | -0.271 | -0.432 to -0.069 | -0.459 to -0.026 | -0.491 to 0.008 | 0.003 | 38/120 | not shown |
| K0 | P | 105 | -0.199 | -0.394 to 0.013 | -0.425 to 0.054 | -0.468 to 0.097 | 0.049 | 35/105 | not shown |
| K1 | CDL | 120 | 0.020 | -0.176 to 0.204 | -0.204 to 0.240 | -0.240 to 0.268 | 0.826 | 51/120 | not shown |
| K1 | P | 105 | 0.065 | -0.136 to 0.251 | -0.180 to 0.280 | -0.224 to 0.318 | 0.520 | 52/105 | not shown |
| K1_xs (sensitivity) | CDL / P | 120 / 105 | 0.043 / 0.082 | -0.151 to 0.209 / -0.129 to 0.256 | | | 0.64 / 0.41 | | |

- **A change signal is "not shown" for any classifier or mask.** No cell has a 90% lower bound above 0.
- **K0 moves against NASS.** Under the CDL mask the association is negative, and the 90% and 95% CIs exclude 0
  at Oct-Dec (Oct -0.262, Nov -0.271, Dec -0.270). At Sep (-0.166) only the 90% CI excludes 0; at Aug (-0.162)
  neither does. Under P it is -0.10 to -0.21. This repeats the
  earlier round (-0.20 to -0.27, draw 1, 2020-2024) on twice the areas and eight transitions. Without t = 2018
  (the edition break) the K0 CDL Nov rho is -0.198 (90% CI -0.388 to 0.028).
- **K1 is flat at the harvest dates.** Its rho is 0.02 to 0.12 at Sep-Dec under CDL and 0.04 to 0.19 under P.
  The highest is K1 P Sep, 0.186 (90% CI 0.018 to 0.361, permutation p 0.061). It is not a headline cell, and it is
  one of 20 date x classifier x mask cells, so it is not evidence. At Aug, K1 is clearly negative (CDL -0.347,
  p 0.0002).
- **Common window 2018-2024** (same transitions for both masks): K0 CDL Nov -0.292, K0 P -0.199, K1 CDL 0.040,
  K1 P 0.065. On equal years, P does not lower K1's rho. It makes K0 less negative.
- **Draw 1 alone** (10 areas): K0 CDL Nov -0.212 (90% CI -0.399 to -0.011), K1 CDL -0.006. Doubling the areas
  did not turn the sign. The earlier-round side-by-side table is in `out/diag_change_earlier_round.csv`.
- **K1_xs** (Quebec target season left out of the fit) is within 0.03 of K1 in the main and common windows at
  every date, and within 0.04 without 2018. It is up to 0.13 only on the 15-point 2024 -> 2025 window. The
  same-season Quebec labels do not drive K1.
- **2024 -> 2025 (information only, 15 states):** negative for every headline cell. Nov: K0 CDL -0.33, K0 P
  -0.36, K1 CDL -0.46, K1 P -0.57 (K1 P p 0.026).

### 2.2 D2: signal-to-noise (Nov 15, draws 1+2; `out/diag_snr.csv`, `out/diag_snr_by_state.csv`)

| classifier | mask | median RMS SE of d ln share | median SD of d ln share | snr median (min-max) | snr_share median | nass_snr median (min-max) |
| --- | --- | --- | --- | --- | --- | --- |
| K0 | CDL | 0.078 | 0.202 | 2.14 (0.82-4.14) | 2.33 | 2.20 (0.29-4.06) |
| K0 | P | 0.074 | 0.180 | 1.97 (1.16-4.07) | 2.17 | 2.28 (0.36-3.78) |
| K1 | CDL | 0.065 | 0.142 | 2.39 (0.75-4.17) | 2.32 | 2.74 (0.39-5.50) |
| K1 | P | 0.061 | 0.161 | 2.58 (0.89-4.10) | 2.72 | 2.86 (0.43-5.32) |

- The share moves about twice as much as its sampling noise (snr about 2), so the shares are not just noise.
  That movement does not follow NASS (2.1).
- With 20 areas the median jackknife SE of d ln share is 0.078 (K0 CDL), against 0.108 on draw 1. The ratio is
  0.72, close to 1/sqrt(2) = 0.71 (E5).
- `nass_snr` is about 2.2-2.9, above 1.5. That would mean typical NASS moves are detectable, but only if the share
  moved one-for-one with NASS in log terms. It does not. See the dilution note in 2.6: the expected SNR after
  dilution is about 0.4-0.5 (median).

### 2.3 D3: count-ratio stability (Nov 15, draws 1+2; `out/diag_ratio*.csv`)

ratio = share / NASS silage share of harvested corn. CDL years 2016-2024, P years 2017-2024.

| classifier | mask | median mean ratio | median SD of ln ratio (max) | median swing | year-effect SD | 0.5-call share: median SD ln ratio, year-effect SD |
| --- | --- | --- | --- | --- | --- | --- |
| K0 | CDL | 3.10 | 0.304 (0.518) | 2.91 | 0.167 | 0.363, 0.352 |
| K0 | P | 2.95 | 0.279 (0.462) | 2.90 | 0.176 | 0.454, 0.375 |
| K1 | CDL | 3.21 | 0.216 (0.407) | 1.96 | 0.170 | 0.382, 0.281 |
| K1 | P | 3.09 | 0.206 (0.334) | 2.26 | 0.170 | 0.327, 0.267 |

- **The bias is not stable from year to year.** A state's ratio typically moves by 20-30% (SD of ln ratio) from
  year to year. NASS's own d ln silage has a median SD of 0.21. So the bias wobble is as large as the change it
  would have to reveal.
- **A large part of it is common to all states in a year.** The year-effect SD is 0.15-0.18. The median ln ratio
  across states by year (K0 CDL, Nov) runs 1.30 (2016), 1.25, 1.04, 1.24, 0.97, 1.02, 0.77 (2022), 1.01, 1.06
  (2024). 2016 (Sentinel-2A only) and 2022 (Planetary Computer) stand out. Removing year medians in D1 takes this
  out, but a 2026 forecast cannot remove 2026's year effect without knowing it.
- K1's ratio is steadier than K0's: 0.21 against 0.28-0.30.
- P against CDL on the same years 2017-2024 (`out/extra_ratio_2017_2024.csv`, not pre-registered):
  - K0: 0.279 (P) vs 0.291 (CDL)
  - K1: 0.206 (P) vs 0.204 (CDL)

  So the imagery mask adds no visible instability to the probability share. E6 expected P to be worse; it is not.
  The 0.5-call share is less stable under P for K0 (0.454 vs 0.340).
- Level effect of the mask (Nov, 2017-2025): ln(P share / CDL share) has a median of +0.006 (K0) and -0.008 (K1),
  with an SD of 0.071 and 0.052.

### 2.4 D4: level (`out/diag_level.csv`)

Across the 15 states (mean over the D3 years), Nov 15, draws 1+2:
- K0 CDL: Spearman 0.782, Pearson 0.933, share = 0.258 + 0.527 x NASS share.
- K1 CDL: Spearman 0.861, Pearson 0.951, share = 0.282 + 0.511 x NASS share.
- Under P: K0 0.729 / 0.915; K1 0.843 / 0.924.
- At Aug the level is lost: Spearman 0.13-0.18, slope 0.05-0.10.
- At Sep it is partial: K0 0.14-0.28, K1 0.58-0.63.

The level ranks states, as in the earlier round (0.90, 0.217 + 0.603 x). The intercept of about 0.26 is a floor:
grain fields that look silage-like.

### 2.5 D5: assessability and the fallback label (`out/diag_assessable.csv`)

- Median assessable share by date (CDL): Aug 0.82, Sep 0.99, Oct-Dec 1.00.
- Fallback rows (assessable_share < 0.5), state-years 2016-2025 (CDL / P):
  - Aug: 16 / 4.
  - Sep: 4 / 0.
  - Oct-Dec: 1 / 0 (Michigan 2016).
- E4 was half wrong. At Aug a greenness "drop" is found for most fields, so the pre-registered rule rarely flags
  Aug. But the median "cut" day at Aug 15 is day 217-218 (5-6 Aug), against 266-268 at Nov. The Aug drop is
  pre-harvest noise or senescence, not harvest. That is why the Aug level does not rank states (2.4). **The
  assessable-share rule is not a usable fallback test before harvest.** Treat Aug as a fallback date regardless
  of `status`. Sep is partial (median cut day 246).
- Before harvest, max_drop not NaN does not mean harvest evidence. A cut-date rule (for example, cut day before
  the forecast date minus a margin) would need a new pre-registration.

### 2.6 Why the change cannot follow NASS here (not pre-registered; `out/extra_dilution.csv`)

If share = a + b x NASS share with b about 0.5 and a about 0.26, a change in ln NASS share moves ln share by only
dilution = b x NASS share / share. At Nov (K0 CDL), dilution is:
- 0.045 Iowa, 0.055 Nebraska, 0.081 Minnesota and Ohio
- 0.31 Wisconsin, 0.43 Pennsylvania, 0.56 New York, 0.66 California
- median 0.17

Expected SNR = dilution x nass_snr: median 0.45 (K0 CDL), 0.40 (K0 P), 0.50 (K1 CDL and P). Maximum 1.49 (CA,
K0 CDL). So in 11-13 of 15 states a true NASS move is smaller than the sampling SE. Meanwhile the share moves by
about 2x its SE, so most of the observed movement is the classifier's response to the season, the imagery and
the edition. More areas cannot fix that. A classifier with a lower grain floor (smaller intercept, higher slope)
is the lever.

### 2.7 2025 -> 2026 under P (real-time; `out/changes.csv`, information)

Nov 15, draws 1+2, d ln share (SE):
- Iowa +0.44 (0.07) K0 / +0.47 K1; Nebraska +0.61 / +0.62; South Dakota +0.45 / +0.27; Minnesota +0.30 / +0.30.
- California, New York, Idaho and Texas are within 0.06 of 0 (Idaho K0 -0.052).

The rises are in the grain states, where the silage share is small and dilution is near 0.05. A +0.5 log move
there would be a large real silage change. The pattern looks like a 2026 year effect (season, or a corn-mask
transfer failure: corn_mask found 2026 P corn acres at 0.60 of 2025 in CO and KS). It does not look like silage.
**Do not read these as silage increases.**

### 2.8 Expectations against outcomes

- E1 held: K0 CDL Nov -0.271, inside -0.30 to +0.20; "not shown".
- E2 failed: K1 minus K0 is +0.29 (CDL Nov), outside 0.15. K1 removes the negative association but adds no
  positive one.
- E3 held in substance. K1 P is 0.065 against CDL 0.020 (0.040 on the common window), all indistinguishable from
  0. For K0, P is less negative than CDL; the mask noise plausibly attenuates a negative association. P is never
  positive.
- E4 failed: the fallback rule rarely flags Aug and Sep.
- E5: the SE fell by the expected factor (held). `nass_snr` is above 1.5 (failed), but dilution brings the expected
  SNR to about 0.45.
- E6: the median SD of ln ratio is above 0.10 (held). It is not higher under P on equal years (failed).

### 2.9 What a downstream model can and cannot take from this

- Use the shares as the pre-registered inputs they are: `out/shares.csv` (draws 1+2) and `out/changes.csv` (with
  same-area SEs). For real-time use, only the P mask at Sep-Nov counts.
- On 2017-2024 there is no positive association between the share change and the NASS silage change, for either
  classifier or mask. A model that adds d share to a base forecast should expect no gain. K0 should expect a
  loss, consistent with the earlier round's +4 WAPE points.
- The level is informative: it ranks states, Spearman 0.73-0.86 at Oct-Nov. Its year effect (SD about 0.17) and
  state-specific bias wobble (about 0.2-0.3 in ln) are the obstacles.
- The base silage models (A-S3, SC, SC_A, SC_B, reversion, persistence) were not combined or scored here. This
  task only produces the shares and their diagnostics.

### 2.10 Limitations

- Field-level truth is absent. The CDL mask is itself a classification, and NASS gives state totals only.
- Imagery source shifts (Planetary Computer 2016-2018 and 2022; Sentinel-2A only in 2016) and the CSB edition
  change between 2017 and 2018 are uncorrected. Year-median removal absorbs their common part only.
- K0 and K1 are applied to US features cut at each date but were trained on full-season Quebec features. No
  calendar or region adaptation was done (USDA named this trap).
- The P mask carries corn_mask's failures (TX, CO, KS under-call; ND, ID over-call). D1 under P covers 2018-2024
  only, because P has no 2016.
- The D1 CIs resample 15 states. With 8 transitions the effective sample is small. The permutation test keeps the
  year structure but assumes states are exchangeable within a year.
- Analyses 2.6 and the P/CDL common-year ratio are not pre-registered. They are labelled as such and change no
  pre-registered reading.
- Large caches stay local, above the 30 MB git limit: `out/cache/probs.parquet` (74 MB) and `out/cache/features/`
  (81 MB in 45 files). No git writes were made.
