# sat_stress: satellite crop stress as a direct silage-chopping signal

Question: does a field-free satellite stress index (no silage classifier, so no false-positive dilution)
improve state corn-for-silage acres when it scales an existing forecast up in stressed years and down in
lush years? Agronomy: drought-stressed corn that will not yield well is chopped for silage instead of
harvested for grain (the same mechanism as the drought term in `smoothed_chopping`), so a stressed canopy in
August and early September should mean more silage acres.

Code: `run.py`. Outputs: `out/`. Nothing outside this folder (and the agent scratch folder) is written;
`kernelag/` is imported, never modified.

---

## 1. Pre-registration

Written before any stress index or score was computed. The text from the heading above to the end marker is
hashed into `out/preregistration.sha256` before the first scoring run; later notes go below the marker.

### 1.1 Data and look-ahead rules

- States: the 15 sampled states (FIPS 06 CA, 08 CO, 16 ID, 19 IA, 20 KS, 26 MI, 27 MN, 31 NE, 36 NY, 38 ND,
  39 OH, 42 PA, 46 SD, 48 TX, 55 WI), about 80% of US silage acres.
- Fields: `data/samples/corn_<fips>.parquet` (10 PPS-drawn 10 km areas per state; corn field-years from that
  year's Cropland Data Layer) and their Sentinel-2 series `data/s2_series/corn_<fips>/<cell>_<year>.csv`, read
  with `field_id` as text (avoids the CA/CO leading-zero bug of `kernelag.field_model.load_series`). Only the
  areas returned by `kernelag.state_signal.complete_areas`. Crop years 2019-2024 only; 2025 files are not read.
- Looks: `valid_frac >= 0.5` and NDVI present, dated on or before 15 September of the crop year. Every look after
  15 September is discarded for every forecast date, so the stress index is the same at 15 Sep, 15 Oct and
  15 Nov (it is available from 15 September). Cloud and haze dips are removed per field-year with
  `kernelag.features.drop_dips` (the team's rule), applied after the 15 September cut.
- Known look-ahead (not removable here): the corn mask is that year's Cropland Data Layer, published after the
  season. A real-time version needs an in-season corn mask.

### 1.2 Stress index (one composite, fixed now)

Per field-year (day-of-year windows of the crop year):

- (a) `peak` = maximum NDVI over looks from 1 June to 15 September (needs >= 3 looks in the window).
- (b) `ndmi` = mean NDMI over looks from 1 August to 15 September (needs >= 2 looks).
- (c) `decline` = `peak` minus the median NDVI of looks from 1 September to 15 September (needs `peak` and
  >= 1 look in the window).

Per state s and year t: X(s,t) = unweighted median over the field-years where the component is defined;
missing if fewer than 50 such field-years.

Anomaly versus PRIOR years only: A(s,t) = X(s,t) - mean(X(s,2019..t-1)); none for 2019 (2020's anomaly rests
on 2019 alone). Scale, using only information available at the forecast date of year t:
sigma_X(t) = root mean square of A(s,y) over the 15 states and 2020 <= y <= t. Z(s,t) = A(s,t) / sigma_X(t).

**stress(s,t) = ( -Z_peak - Z_ndmi + Z_decline ) / 3.**

Expected sign: positive stress (lower peak greenness, drier canopy, earlier browning by mid-September) means
MORE silage. If any component is missing the stress is missing; a candidate then leaves the base unchanged for
that state-year (stress read as 0), and the count of such cases is reported.

### 1.3 Bases (the forecasts being adjusted)

- **A-S3** (`s3_fsa_residual`, Tier A: NASS finals of earlier years, FSA certifications; no current-year NASS).
  Predictions read from `test_models/ownModels/silage/out/backtest_by_state_year.csv` at as-of nov, oct and sep.
- **SC** (`smoothed_chopping`, teammate's delivered method). Regenerated here by importing
  `kernelag.silage_level.load_history` and `predict` (alpha and gamma chosen on earlier years only) for
  2012-2024 at as-of nov, oct and sep. Inputs: NASS finals of earlier years plus NASS's in-season yield
  forecast and in-season grain-acreage forecast of the current year, so it is **Tier B** in the task's labeling
  (and beyond the ownModels Tier B definition, which excludes NASS yield and acreage forecasts). It does not use
  the Drought Monitor. The regeneration must reproduce the stored 2017-2024 per-year state errors in
  `data/models/state_model_backtest.csv` (predictor `smoothed_chopping`) and is reported against the
  documented 2012-2024 13.23% / 3.44%.
- Truth: NASS final state silage acres as the incumbent uses them (`kernelag.state_panel.load_panel`, column
  `silage`), checked against both bases' truth columns.

### 1.4 Candidates (all reported, at nov headline, plus sep and oct)

- `c1_as3_fit`: A-S3 x exp(b_t x stress).
- `c2_sc_fit`: SC x exp(b_t x stress).
  b_t = max(0, weighted least-squares slope without intercept of log(actual / base) on stress), weights = base
  acres, pooled over the 15 states and training years 2020 <= y < t with stress present, same base and same
  as-of date (expanding window; both bases are themselves out-of-sample backtest predictions). The sign
  constraint follows the expected sign (team practice, `EXPECTED_SIGN` in `kernelag.state_model`). Null b = 0
  when there is no training year, so 2020 equals the base; decision window 2021-2024 (4 years).
- `c3a_as3_fixed`: A-S3 x exp(0.05 x stress).
- `c3b_sc_fixed`: SC x exp(0.05 x stress).
  b = 0.05 per unit of stress (about 5% more silage per standard deviation of stress) is fixed now from the
  expected sign and a conservative magnitude, so 2020-2024 are all out of sample; decision window 2020-2024
  (5 years).

### 1.5 Metrics

Per year, over the 15 states: WAPE15 = sum |pred - actual| / sum actual; total15 error = (sum pred - sum actual)
/ sum actual, and its absolute value. Also the US total (48 states, the other 33 states keep the base) and
48-state WAPE, for information. Summaries: means over the decision window and over 2020-2024.

### 1.6 Decision rule (per candidate, against its own base, as of 15 November)

d_y = metric(candidate, y) - metric(base, y) for metric in {WAPE15, |total15 error|}, over the candidate's
decision window; SE = sd(d_y, ddof 1) / sqrt(n). The candidate **improves** on its base if mean(d) + 2 SE < 0
for at least one of the two metrics. Sep and Oct results use the same rule and are reported for information.
Four candidates x two metrics = eight tests on 4-5 years: a pass is weak evidence ("promising"), not grounds for
promotion on its own. Nothing is fitted, tuned or selected on 2025 or on Maryland.

### 1.7 Diagnostics (not candidates, not eligible)

Pearson and Spearman correlations over state-years 2020-2024 of stress with: SC's drought term (the yield
shortfall 1 - in-season yield / 10-year trend, and SC's chopped acres as a share of the SC forecast, at nov);
the change in Drought Monitor D2+ share (Jun-Sep mean minus the state's prior-years mean,
`kernelag.context.drought`, Tier A); the NASS silage change log(S(t) / S(t-1)); and log(actual / base) for both
bases. The same correlations for each single component. The stress table per state-year is written out.

<!-- end of pre-registration -->

## 2. Results (pre-registered analysis)

Run: `run.py` (about 1 minute with 8 workers). The pre-registration hash is checked at start (unchanged).
All numbers come from `out/`; nothing was typed in by hand.

### 2.1 Checks

- **SC regenerated exactly.** Importing `kernelag.silage_level` reproduces the stored per-year 2017-2024
  `smoothed_chopping` state error and total error in `data/models/state_model_backtest.csv` (nov) and
  `..._asof_sep.csv` (sep) with a maximum difference of 0.00 points. The 48-state means are 13.23% / 3.45%
  (2012-2024; documented 13.23 / 3.44, a rounding difference) and 12.80% / 3.34% (2017-2024; documented
  12.80 / 3.34). Per state-year predictions: `out/sc_backtest_by_state_year.csv`.
- **SC tier label: Tier B.** It uses the current year's NASS in-season yield forecast (the drought term) and
  NASS's in-season harvested-for-grain forecast (grain acres to chop). It uses no Drought Monitor input. Strictly,
  this goes beyond the ownModels Tier B definition, which leaves out NASS yield and acreage forecasts.
- **Truth.** The incumbent's panel (2013-2025) and Quick Stats finals agree on all 624 overlapping values (max
  difference 0). A-S3's truth column agrees with the panel on all 585 values for the 15 states.
- **Coverage.** 127,208 sampled corn field-years in 2019-2024, of which 119,330 have all three components.
  Every state-year has at least 420 fields per component, so no 2020-2024 state-year lacks a stress value.

### 2.2 Is the index a real stress signal? (diagnostics, 75 state-years, 2020-2024)

| Stress vs | Pearson r (p) | Spearman (p) |
|---|---|---|
| NASS yield shortfall (SC's drought input, Tier B) | 0.43 (<0.001) | 0.43 (<0.001) |
| SC's chopped acres share | 0.33 (0.004) | 0.30 (0.009) |
| Drought Monitor D2+ change (Tier A) | 0.44 (<0.001) | 0.32 (0.005) |
| NASS silage change log(S(t)/S(t-1)) | 0.16 (0.17) | 0.10 (0.41) |
| A-S3 residual log(actual/A-S3) | 0.24 (0.04) | 0.21 (0.07) |
| SC residual log(actual/SC) | 0.22 (0.056) | 0.21 (0.07) |

The index tracks crop stress (about as well as it tracks the Drought Monitor, and it agrees with NASS's own yield
shortfall without using it). Its link to silage acres is weak but has the expected sign. It carries some
information that SC's NASS-yield drought term does not (r = 0.22 with SC's residual). By component, peak NDVI
and NDMI carry the signal (r = 0.48 and 0.44 with the shortfall). **The decline component is uninformative**
(r = 0.04 with the shortfall, 0.04 with SC's residual). It mostly measures phenology: in 2019, a late-planted
year, the median decline by 15 Sep was 0.07, against 0.11-0.23 in other years.

### 2.3 Candidates on the 15 sampled states, 2020-2024 means (`out/summary_2020_2024.csv`)

| Model | as of | WAPE15 % | abs total15 err % | signed total15 % | 48-state WAPE % | abs US err % |
|---|---|---|---|---|---|---|
| persistence (reference) | - | 11.91 | 3.91 | +0.93 | - | - |
| base A-S3 (Tier A) | Nov 15 | 10.08 | 4.77 | -0.60 | 11.30 | 3.70 |
| c1_as3_fit | Nov 15 | 10.39 | 4.43 | -0.51 | 11.55 | 3.79 |
| **c3a_as3_fixed** | Nov 15 | **9.94** | **4.11** | +0.10 | 11.18 | 3.63 |
| base SC (Tier B) | Nov 15 | 10.49 | 3.99 | -1.67 | 11.69 | 2.92 |
| c2_sc_fit | Nov 15 | 10.57 | 3.54 | -1.46 | 11.75 | 3.13 |
| **c3b_sc_fixed** | Nov 15 | **10.06** | **3.06** | -0.98 | 11.35 | 2.62 |
| base A-S3 | Sep 15 | 10.24 | 4.91 | -0.99 | 11.42 | 3.83 |
| c3a_as3_fixed | Sep 15 | 10.06 | 4.00 | -0.30 | 11.28 | 3.42 |
| base SC | Sep 15 | 10.51 | 4.34 | -1.72 | 11.72 | 3.18 |
| c3b_sc_fixed | Sep 15 | 10.07 | 3.42 | -1.03 | 11.36 | 2.97 |

The Oct 15 rows (in the csv) fall between Sep and Nov. c1 and c2 equal their base in 2020 (no training year).
Fitted b (nov, `out/fitted_b.csv`): A-S3 0.047, 0.087, 0.097, 0.061 and SC 0.069, 0.094, 0.099, 0.073 for
2021-2024. The fitted b always has the expected sign, but it is larger than the fixed 0.05 and overshoots.

### 2.4 Decision rule (`out/decision_tests.csv`)

| Candidate (window) | WAPE15 diff (SE), diff+2SE | abs total15 diff (SE), diff+2SE | years better (WAPE / total) |
|---|---|---|---|
| c1_as3_fit (2021-24) | +0.39 (0.44), +1.26 | -0.43 (0.39), +0.36 | 1/4, 3/4 |
| c2_sc_fit (2021-24) | +0.10 (0.50), +1.10 | -0.56 (0.45), +0.33 | 2/4, 3/4 |
| c3a_as3_fixed (2020-24) | -0.14 (0.15), +0.15 | -0.66 (0.36), +0.06 | 3/5, 4/5 |
| c3b_sc_fixed (2020-24) | -0.43 (0.29), +0.14 | -0.93 (0.53), +0.13 | 4/5, 4/5 |

**No candidate meets the pre-registered rule** (mean difference + 2 SE < 0) at Nov 15, nor at Oct 15 or Sep 15
(the smallest diff+2SE is +0.06). The fixed-b candidates (c3) improve both bases on both metrics on average, at all
three dates. The fitted-b candidates (c1, c2) make the state error worse and the total error better. Five years
(four for the fitted ones) is short. A real gain of this size (0.1 to 0.4 WAPE points) cannot clear 2 SE with this
year-to-year noise.

<!-- results above computed by run.py; section 3 is post hoc -->

## 3. Post-hoc exploration (written after section 2 was seen; none of it is eligible)

`explore.py` produces `out/explore_variants.csv`, `out/explore_permutation.csv` and
`out/explore_leave_one_state_out.csv`. These runs probe how robust the result is; they do not select a model.
Nov 15 values below, given as candidate minus base (negative is better).

| Variant | A-S3: WAPE15 / abs total15 | SC: WAPE15 / abs total15 |
|---|---|---|
| c3 pre-registered (b 0.05, 2020-24) | -0.14 / -0.66 | -0.43 / -0.93 |
| c3 scored on 2021-24 only | -0.12 / -0.47 | -0.21 / -0.49 |
| E9 index without the 2019 reference year (2021-24) | -0.14 / -0.10 | -0.26 / -0.03 |
| E1 peak NDVI only | +0.39 / -0.89 (passes 2 SE on total) | +0.24 / -0.73 (passes) |
| E1 NDMI only | +0.17 / -0.55 | -0.49 / -1.22 |
| E1 decline only | +0.46 / +0.29 | -0.29 / -0.64 |
| E10 peak + NDMI, no decline | +0.01 / -1.07 (passes, 5/5 years) | -0.26 / -1.08 (passes, 5/5 years) |
| E2 positive stress only | +0.09 / -0.36 | -0.26 / -0.61 |
| E3 b = 0.025 | -0.18 (passes 2 SE, 4/5) / -0.46 | -0.29 (passes, 4/5) / -0.46 |
| E3 b = 0.075 | +0.08 / -0.49 | -0.39 / -1.23 |
| E3 b = 0.10 | +0.44 / -0.04 | -0.15 / -0.90 |
| E7 additive chop k x max(0,stress) x G(t-1), k fitted (2021-24) | +0.45 / +0.89 | +0.11 / +0.89 |

Permutation test (2,000 shuffles of the stress values, c3, Nov):

| Shuffle | A-S3 p (WAPE15 / total) | SC p (WAPE15 / total) |
|---|---|---|
| among all 75 state-years | 0.014 / 0.081 | 0.022 / 0.014 |
| within each year, across states | 0.061 / 0.454 | 0.057 / 0.676 |

Leave one state out (c3, Nov): with SC as the base, the WAPE15 gain stays negative whichever state is dropped
(-0.57 to -0.19). With A-S3 it ranges from -0.28 to +0.12. The total-error gain stays negative for both bases
(-1.06 to -0.16).

Reading:

- **The gain in the total error is a year-level effect, and much of it is 2020.** Shuffling stress within years
  (which keeps each year's mean) leaves the total-error gain intact (p = 0.45-0.68). In 2020 every state shows
  positive stress, because the only reference year is 2019, which was late planted and wet. When 2019 is dropped
  as a reference (E9), the total-error gain almost disappears. So this part is not yet evidence of a working
  national signal.
- **The cross-state allocation part is weakly real.** It improves WAPE15, p of about 0.06 with the
  within-year shuffle, for both bases.
- **A smaller b (0.025) would have passed on WAPE15**, and peak + NDMI without decline (E10) would have passed
  on total error. These are post-hoc picks among about 12 variants, so they are hypotheses for a new
  pre-registration, not results. A sensible next pre-registration is stress = mean(-Z_peak, -Z_ndmi), b
  between 0.025 and 0.05, scored on 2025-2026 once they can be scored honestly.
- The structural "chop grain acres" form (E7) and fitted magnitudes overshoot. The data support only a small
  multiplicative nudge, not a chopping model.

## 4. What this means for the team

- **Not promoted.** No pre-registered candidate clears the rule. The best one, c3b (SC x exp(0.05 x stress)), gives
  15-state WAPE 10.06% against 10.49% and an absolute 15-state total error of 3.06% against 3.99% (2020-2024, Nov
  15). The US 48-state absolute error goes from 2.92% to 2.62%. The gain is consistent in sign but within noise.
- **Useful story for judges (innovation and alignment).** NASS uses NDVI for yield, not acreage. Here a Tier A,
  classifier-free satellite stress index agrees with NASS's own yield shortfall (r = 0.43) without using it,
  is ready on 15 September, and nudges silage in the expected direction. It avoids the false-positive dilution
  that sank the classifier share (+4 WAPE points).
- **Do not over-claim.** The evidence covers 5 years and 15 states, the corn mask comes from the Cropland Data Layer
  (look-ahead), the decline component is noise, and the total-error gain depends on 2020.

## 5. Limitations

- Five scoring years (four for the fitted candidates); 15 states. Eight decision tests, no multiplicity
  correction.
- Corn mask = that year's Cropland Data Layer, published after the season (look-ahead). A real-time index needs an
  in-season corn mask (see `test_models/ownModels/satellite/corn26/`). The cost of that mask is not measured here.
- The 2020 anomaly rests on 2019 alone, a late-planting year. This standardization was pre-registered, and its
  weakness showed only afterwards.
- Field medians are unweighted. The sample areas were drawn in proportion to corn acres, so states are summarized
  by their corn-dense areas.
- Sentinel-2 looks dated 15 September are counted at a 15 September forecast. Processing latency (about a day) is
  ignored.
- 2025 (scoring year) and Maryland were not used. A 2026 forecast with the index is UNCOMPUTED: the 2026 fields
  come from a different, imagery-based corn mask (`corn26_<fips>`). Anomalies against the CDL-based 2019-2025
  sample would mix two masks.

## How to run

```bash
.venv/Scripts/python.exe test_models/variations/sat_stress/run.py --workers 8   # pre-registered analysis (~1 min)
.venv/Scripts/python.exe test_models/variations/sat_stress/explore.py           # post-hoc checks (~40 s)
.venv/Scripts/python.exe -m ruff check --select E,F,W --line-length 120 test_models/variations/sat_stress/
```

`run.py` reuses `out/field_components.parquet` if present (`--force` recomputes it) and stops if the README
pre-registration section no longer matches `out/preregistration.sha256`.
