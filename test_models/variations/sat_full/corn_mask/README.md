# corn_mask: corn from imagery for every candidate field-year 2016-2026, no CDL at prediction time

Question: a real-time forecaster has no Cropland Data Layer (CDL) for the season it forecasts, so the corn fields
under any satellite silage share must be identified from Sentinel-2 alone. How well does the corn26 recipe
(monthly NDVI/NDMI medians, peak, amplitude, 16-day NDVI bins, fixed gradient boosting, threshold 0.5) identify
corn on the full state sample (15 states, 300 areas, 2016-2026) when it is trained only on earlier years, at each
forecast date from 15 July to 15 December?

Code: `corn_mask.py`. Outputs: `out/`. Nothing outside this folder (and the agent scratch folder) is written;
`kernelag/` and `test_models/ownModels/satellite/corn26/` are imported, never modified.

---

## 1. Pre-registration

Written before any feature, classifier or score of this study was computed. The text from the heading above to
the end marker is hashed into `out/preregistration.sha256` before the first fitting run; later notes go below
the marker and never change this section.

### 1.1 Data

- States: the 15 sampled states (FIPS 06 CA, 08 CO, 16 ID, 19 IA, 20 KS, 26 MI, 27 MN, 31 NE, 36 NY, 38 ND,
  39 OH, 42 PA, 46 SD, 48 TX, 55 WI). Maryland is not in this sample and is not used.
- Candidate field-years: `data/samples/candes_<fips>.parquet` (2019-2021, 2023-2026), `candpc_<fips>.parquet`
  (2018, 2022; same field ids as candes) and `candpc16_<fips>.parquet` (2016, 2017; field ids of the 2015-2022
  Crop Sequence Boundaries edition, which differ from the others). Geometry is not read. `is_corn` (that year's
  CDL; NaN for 2026) is the label for training and scoring only; it is never a feature.
- Series: `data/s2_series/<stem>/<cell>_<year>.csv`, read with `field_id` as text through
  `corn26.read_series_file` (never `kernelag.field_model.load_series`, which drops the leading zero of CA/CO ids).
  Every area is checked with `kernelag.state_signal.complete_areas`; an incomplete area would be dropped and
  counted (none expected: 140 and 40 files per folder).
- Known sample caveat (not removable here): the candidate pool is every field that grew corn in ANY CDL year of
  its edition, so for a past year t it contains fields that are corn only in years after t. A real-time pool for
  year t can only contain fields with corn before t. The "history" pool (1.6) measures this; for 2026 the two pools
  coincide (candes = corn in some year 2018-2025, all before 2026).
- Imagery source shift: Earth Search (Collection 1) for 2019-2021 and 2023-2026; Planetary Computer for
  2016-2018 and 2022; 2016 has Sentinel-2A only (about half the looks of other years). Not corrected; reported.

### 1.2 Forecast dates and the cut

- Dates: 15 Jul, 15 Aug, 15 Sep, 15 Oct, 15 Nov, 15 Dec of the crop year (labels jul, aug, sep, oct, nov, dec).
- Cut: `kernelag.state_signal.series_asof` semantics: only looks dated on or before the 15th of the month are
  used. `kernelag.context.ASOF_MONTH` has no jul/dec keys, so this module adds `jul=7` and `dec=12` to that dict
  at run time inside its own processes (no file is edited); `series_asof` and `corn26.features_for` then work
  unchanged. The series run May 1 to Nov 30, so dec equals the full season.
- 2026: the series end about 12-14 Nov 2026 (the pull date). 2026 calls are made at jul..nov. Dec 15 2026 is
  after the data date: "UNCOMPUTED: 15 Dec 2026 is in the future"; its rows carry NaN.

### 1.3 Features (corn26 recipe, imported, unchanged)

`corn26.corn_features(series, asof)` per field-year: clear looks (`valid_frac >= 0.5`, NDVI present) from May 1
to the cut; `ndvi_m05..m11`, `ndmi_m05..m11` monthly medians; `peak_ndvi`, `peak_doy`; `amplitude`;
`ndvi_b00..b13` 16-day NDVI medians from day 121. The model at date d uses `corn26.features_for(d)` (months and
bins starting on or before the cut), and `corn26.fit_classifier` drops a feature with no observed value in the
training rows. A field-year with no clear look keeps all-missing features and is still scored (gradient boosting
routes missing values natively); the count is reported as `n_no_clear_look`.

### 1.4 Classifier (corn26, imported, never tuned)

`corn26.make_classifier()`: sklearn HistGradientBoostingClassifier, learning_rate 0.1, 200 iterations, 15 leaves,
50 rows per leaf, L2 1.0, no early stopping, seed 20261115. Threshold 0.5 (`corn26.CORN_THRESHOLD`). One pooled
model for all 15 states (no state, location or prior-crop feature), no sample weights. A separate model per
forecast date, fitted on training rows whose features are cut at that same date.

### 1.5 Training regimes (both computed at every date)

- **P, prior years (headline, the honest real-time version):** for target year t in 2017..2025, train on every
  candidate field-year of years < t (all states, all three file types) with known `is_corn` (expanding window;
  the test year and later years are never seen). 2016 has no prior year: `p_corn_P` is NaN,
  "UNCOMPUTED: no prior year". For information only, a column `p_corn_P_alt` holds 2016 calls from a model
  trained on 2017 alone (NOT real-time; never in a headline number).
- **L, leave-one-year-out (upper bound):** for t in 2016..2025, train on every field-year of the other years of
  2016-2025.
- **2026:** P and L are the same model, trained on all field-years 2016-2025.

### 1.6 Scores

Against the CDL label (a proxy: CDL is itself a classification; NASS gives no field truth). Per regime x date x
year x state, and pooled over the 15 states ("ALL"), using `corn26.call_metrics`: corn precision and recall
(field counts), acre precision and recall, and the predicted/true corn-acre ratio both raw and PPS-weighted (area
weight 1/cell_size_acres, as in `kernelag.state_signal.share`). The **weighted ratio** is the headline ratio.

- Pools: "all" candidates (headline) and "history": fields CDL-corn in at least one earlier labelled year with
  the same field ids (2017: 2016; 2019: 2018; 2020: 2018-2019; ... 2026: 2018-2025; none for 2016 and 2018, whose
  history is NaN). The history pool is the faithful real-time candidate set.
- Diagnostic baseline B0 (not imagery): call corn iff the field was CDL corn in year t-1 (available in real time:
  CDL t-1 is published early in year t). Defined for 2017 and 2019-2025, date-independent. It shows how much the
  imagery adds over crop rotation.
- Headline: regime P at 15 Nov, years 2017-2024 (2025 is information only and reported separately; nothing is
  selected or tuned on any year), per state and ALL: mean precision, mean recall, median |weighted ratio - 1|.
- Failure flag (state x year x date x regime): weighted corn-acre ratio outside [0.90, 1.10], or recall < 0.70, or
  precision < 0.70. A state FAILS at a date if it is flagged in at least half of its scored years 2017-2024.
- P minus L gap (recall, precision, |ratio - 1|): the cost of not having seen the target season's calendar.
- Expectations stated now, before any score: Texas, California and Colorado fail under P (calendar transfer),
  most at 15 Jul and 15 Aug; 2017 under P (trained on sparse 2016 Sentinel-2A looks alone) is weak; recall rises
  with the date until about 15 Sep.

### 1.7 Outputs

- `out/corn_calls.parquet`: stem, state_fips, cell, field_id, year, asof, p_corn_P, is_corn_P, p_corn_L,
  is_corn_L, is_corn_cdl, then acres, cell_size_acres, county_fips, draw, n_clear, history_corn, prev_corn_cdl,
  p_corn_P_alt.
- `out/metrics_by_state_year.csv` (every regime x pool x date x year x state incl. ALL),
  `out/summary_headline.csv`, `out/summary_by_year.csv`, `out/failures.csv`, `out/calls_2026_by_state.csv`,
  `out/run.json`; feature caches `out/cache/features_<asof>.parquet`.

<!-- end of pre-registration -->

---

## 2. Results (run 2026-11-15; pre-registration hash unchanged, checked by the script on every step)

Run: `features` 73 s (3,300 series files, 20 workers), `fit` 465 s (125 fits, 6 dates in parallel x 3 threads),
`report` 10 s. 1,083,954 candidate field-years; all 300 areas complete (0 dropped); 139-207 field-years per year
have no clear look and are still scored. All field-level numbers below are against the CDL, which is a proxy
label, not field truth. "Ratio" is the PPS-weighted predicted/true corn-acre ratio. Means are over 2017-2024;
2025 is information only. By construction P and L are the same model for 2025 (years < 2025 = all other years)
and for 2026.

### 2.1 Headline: P (prior years only), all 15 states pooled

| date | precision | recall | ratio (mean) | median abs(ratio - 1) | states failing (P / L) | 2025 precision / recall / ratio |
| --- | --- | --- | --- | --- | --- | --- |
| 15 Jul | 0.753 | 0.635 | 0.881 | 0.072 | 14 / 14 | 0.796 / 0.710 / 0.906 |
| 15 Aug | 0.818 | 0.736 | 0.926 | 0.069 | 12 / 12 | 0.862 / 0.817 / 0.935 |
| 15 Sep | 0.835 | 0.766 | 0.936 | 0.074 | 11 / 11 | 0.878 / 0.850 / 0.956 |
| 15 Oct | 0.845 | 0.785 | 0.950 | 0.052 | 11 / 10 | 0.890 / 0.879 / 0.972 |
| 15 Nov | 0.848 | 0.795 | 0.965 | 0.031 | 11 / 10 | 0.903 / 0.873 / 0.952 |
| 15 Dec | 0.846 | 0.803 | 0.974 | 0.034 | 9 / 9 | 0.905 / 0.871 / 0.946 |

(`out/summary_headline.csv`, rows regime P, pool all, state ALL; failing counts from the same file.)

- **P vs L (cost of not having seen the target season):** small. Pooled, P minus L is -0.006 to -0.018 in
  precision and -0.019 to -0.031 in recall at every date; median abs(ratio - 1) differs by at most 0.012
  (`out/gap_P_minus_L.csv`). The failures below are failures of the recipe in those states, not of the
  real-time restriction: L fails the same states.
- **2017 under P** (trained on 2016 alone, sparse Sentinel-2A looks) is the weak year, as expected: Nov recall
  0.657, ratio 0.796 (L: 0.761, 0.895). From 2018 on, P is within 0.035 of L in every pooled Nov metric.
- **2016:** P is "UNCOMPUTED: no prior year". Information only (not real-time): trained on 2017 alone, Nov
  precision 0.778, recall 0.735, ratio 0.962; L 2016: 0.798 / 0.772 / 0.972.
- **Recall by date:** rises fastest from 15 Jul to 15 Aug (+0.10) and keeps rising slowly to 15 Dec (0.80); the
  pre-registered expectation "rises until about 15 Sep" was too early. Precision plateaus from 15 Oct (0.85).
- **History pool** (the faithful real-time candidate set, fields with earlier CDL corn): pooled precision and
  recall within 0.01 of the "all" pool (Nov P: precision 0.856, recall 0.799, ratio 0.952, median
  abs(ratio - 1) 0.058 vs 0.031); one state fewer fails at Nov (10 under P).

### 2.2 Per state, P at 15 Nov (2017-2024 means; L in brackets)

| state | precision | recall | ratio | median abs(ratio - 1) | flagged years of 8 | fails |
| --- | --- | --- | --- | --- | --- | --- |
| Iowa | 0.931 (0.937) | 0.936 (0.935) | 1.010 | 0.029 | 0 (0) | no |
| Minnesota | 0.911 (0.919) | 0.881 (0.892) | 1.001 | 0.052 | 0 (0) | no |
| Nebraska | 0.920 (0.924) | 0.871 (0.886) | 0.958 | 0.014 | 1 (1) | no |
| Wisconsin | 0.905 (0.912) | 0.872 (0.901) | 0.977 | 0.045 | 1 (0) | no |
| Ohio | 0.857 (0.872) | 0.885 (0.910) | 1.028 | 0.109 | 5 (3) | yes (L no) |
| Michigan | 0.850 (0.864) | 0.830 (0.848) | 0.990 | 0.128 | 5 (4) | yes |
| Idaho | 0.816 (0.840) | 0.902 (0.908) | 1.171 | 0.160 | 7 (4) | yes |
| South Dakota | 0.837 (0.848) | 0.858 (0.876) | 1.086 | 0.156 | 5 (7) | yes |
| Pennsylvania | 0.857 (0.863) | 0.744 (0.766) | 0.914 | 0.163 | 6 (5) | yes |
| New York | 0.872 (0.886) | 0.758 (0.787) | 0.864 | 0.134 | 6 (5) | yes |
| Kansas | 0.844 (0.847) | 0.708 (0.711) | 0.839 | 0.136 | 6 (7) | yes |
| North Dakota | 0.716 (0.748) | 0.757 (0.803) | 1.211 | 0.204 | 6 (6) | yes |
| Colorado | 0.843 (0.851) | 0.681 (0.718) | 0.856 | 0.161 | 6 (7) | yes |
| California | 0.675 (0.678) | 0.595 (0.643) | 0.950 | 0.049 | 7 (7) | yes |
| Texas | 0.701 (0.722) | 0.484 (0.537) | 0.704 | 0.344 | 8 (8) | yes |

- **Failing states (pre-registered rule) at 15 Nov under P:** California, Colorado, Idaho, Kansas, Michigan,
  New York, North Dakota, Ohio, Pennsylvania, South Dakota, Texas. At 15 Dec Michigan and Ohio drop out. Only the
  Corn Belt core passes: Iowa, Minnesota and Nebraska at every date from 15 Aug, Wisconsin from 15 Sep; at 15 Jul
  only Nebraska passes. Every flagged state-year is in `out/failures.csv`.
- **Calendar transfer (as feared):** Texas is the worst state at every date (recall 0.40 at 15 Jul, never above
  0.51; ratio 0.56-0.92 per year at 15 Nov, under-calling every year). California's recall stays near 0.60 from 15 Aug on
  (precision 0.67); its ratio is near 1 only because misses and false positives cancel, so the right acres are not
  the right fields. Colorado and Kansas under-call (ratio 0.84-0.86 at Nov; median abs(ratio - 1) 0.39 and 0.36 at
  15 Jul). North Dakota and Idaho over-call (ratio 1.21 and 1.17). These states also fail under L, so a pooled
  model with one calendar does not fit them even when the target year's other states are seen.
- **Earliness:** at 15 Jul and 15 Aug the mask is not usable outside the Corn Belt core: median abs(ratio - 1)
  0.21-0.42 in Colorado, Kansas, North Dakota, South Dakota and Texas at 15 Aug or earlier
  (`out/summary_headline.csv`). 15 Jul and 15 Aug silage work needs a fallback corn mask (for example last year's
  candidate pool or a non-satellite corn-acre prior), labelled as such.

### 2.3 Diagnostic baseline B0 (last year's CDL corn; not imagery)

Field level, B0 is poor (pooled precision 0.386, recall 0.390: corn-soy rotation means last year's corn field is
usually not corn this year), so the imagery mask is far better at choosing the RIGHT fields, which is what a
silage share needs. At the state acre level, however, B0's ratio is as good or better: pooled median
abs(ratio - 1) 0.035 (P at Nov 0.031), and lower than P at Nov in 10 of 15 states: Colorado (0.043 vs 0.161),
Kansas (0.020 vs 0.136), Michigan (0.008 vs 0.128), Idaho, Minnesota, Ohio, Pennsylvania, New York, South Dakota
and Texas (0.130 vs 0.344); P is lower in California, Iowa, Nebraska and Wisconsin, tied in North Dakota. B0's
years are 2017 and 2019-2024 (2018 has no same-id previous year), P's 2017-2024. Imagery alone does not beat
persistence for state corn acres in this sample.

### 2.4 2026 calls (P = L, trained on 2016-2025), 15 Nov

PPS-weighted predicted 2026 corn acres over 2025 CDL truth (`out/calls_2026_by_state.csv`): Colorado 0.60,
Kansas 0.61, South Dakota 0.83, Texas 0.84, North Dakota 0.89; Pennsylvania 1.23, Ohio 1.14, Idaho 1.11, Michigan
1.09; the Corn Belt core 0.97-1.06. NASS planted (Sep 2026 / 2025 final) is 0.98 for Colorado and 1.04 for
Kansas, so the 40% drops are calendar/transfer failures in the states that fail in 2.2, not a real fall in corn
(the same pattern as corn26). The 2026 series end 13-14 Nov, so the Nov cut is not short of data. 15 Dec 2026:
"UNCOMPUTED: 15 Dec 2026 is in the future" (rows present with NaN).

### 2.5 Limits

- CDL labels are a proxy; field precision/recall measure agreement with another classifier.
- The candidate pool contains future-corn fields for past years (1.1); the history-pool scores bound that effect
  (small, 2.1).
- One pooled model without state or calendar features, as pre-registered; no tuning was done. A per-region model,
  a growing-degree-day calendar or a rotation prior (B0 is informative at the acre level) are untested ideas and
  would need a new pre-registration.
- `out/corn_calls.parquet` is 64 MB (6,503,724 rows = 1,083,954 field-years x 6 dates), above the 30 MB git limit;
  it stays local. Feature caches in `out/cache/` are 264 MB in total.

### 2.6 Files

| file | content |
| --- | --- |
| `out/corn_calls.parquet` | per field-year and date: p_corn and calls for P and L, CDL label, acres, weights, n_clear, history_corn, prev_corn_cdl, p_corn_P_alt (2016 only) |
| `out/metrics_by_state_year.csv` | corn26.call_metrics per regime (P, L, P_alt, B0) x pool x date x year x state (and ALL), with failure flags |
| `out/summary_by_year.csv` | the ALL-state rows of the above |
| `out/summary_headline.csv` | per regime x pool x date x state: 2017-2024 means, flagged years, fails, 2025 information |
| `out/gap_P_minus_L.csv` | P minus L on the headline means |
| `out/failures.csv` | every flagged state-year (P, L) and which rule flagged it |
| `out/calls_2026_by_state.csv` | 2026 PPS-weighted corn acres by state and date vs 2025 truth and NASS planted direction |
| `out/fit_log.csv`, `out/run.json` | every fit (train rows, features, seconds), counts, settings, pre-registration check |
