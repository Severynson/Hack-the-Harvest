# corn26: finding 2026 corn from imagery, and what the mask costs

Agent key `corn26`. Code: `corn26.py` (importable), tests: `test_corn26.py`, outputs: `out/`.

## Why

The satellite silage share (`kernelag.state_signal`, recomputed by the `signal` agent) uses the fields that were corn
that year according to the Cropland Data Layer (CDL). The CDL comes out after the season, so a real-time Nov 15
forecast has no corn mask, and every 2019-2025 share assumes a perfect one. For 2026, corn has to be found from
Sentinel-2. This folder builds that corn classifier, measures its error on 2025 (where the CDL is known), replays the
2025 share with the classifier's mask instead of the CDL mask, and writes the 2026 corn calls.

## Run

```bash
.venv/Scripts/python.exe test_models/ownModels/satellite/corn26/corn26.py --workers 15      # about 10 min
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/satellite/corn26/test_corn26.py  # 5 tests
```

It reads only `data/samples/`, `data/s2_series/`, `data/labels/quebec_maize_2023|qc_regions_2023` and
`data/nass/corn_acres_state.csv`, and writes only `out/`. It does not write `data/panel/`. It does not run
`kernelag.state_signal.main()`; it imports `complete_areas`, `series_asof` and `state_table` from it.

## Design (fixed before any result was seen; nothing was tuned)

- **Candidates.** In 2025: every field that was corn in some year from 2019 to 2025. That is 47,948 fields in 150
  sample areas (15 states x 10). 21,692 of them are CDL corn in 2025 (`corn_<fips>` rows with year 2025); the rest
  are negatives (`noncorn25_<fips>`). In 2026 the same 47,948 fields come from `corn26_<fips>`.
- **Features**, per field and year, from clear looks (valid_frac >= 0.5) from May 1 to the cut date
  (`series_asof`):
  - monthly medians of NDVI and NDMI (May to Nov);
  - peak NDVI and its day of year;
  - amplitude (highest minus lowest monthly NDVI median);
  - NDVI medians in 16-day bins starting at day 121.

  Only months and bins that begin by the cut date are used (`features_for`), so 30 features at Nov 15.
- **Model.** `HistGradientBoostingClassifier(learning_rate=0.1, max_iter=200, max_leaf_nodes=15,
  min_samples_leaf=50, l2_regularization=1.0, early_stopping=False, random_state=20261115)`. Missing values are
  handled natively. Threshold 0.5. One pooled model for all states; state is not a feature.
- **Validation.** Leave-one-area-out (150 groups, group = state_fips + cell) and leave-one-state-out (15 groups),
  at Nov 15, Oct 15 and Sep 15.
- **Field silage model.** `kernelag.field_model.make_model` on `MODEL_FEATURES`, fitted on all 3,128 Quebec
  field-years with series (quebec_maize_2023: 318; qc_regions_2023: 2,810; all assessable). Quebec series are
  uncut, the same way `state_signal.fit_field_model` treats training data. No Maryland data and no US sample data
  were used to fit or tune it.
- **Share arithmetic.** `area_totals_from_features` is `kernelag.state_signal.area_totals` line for line, except
  that the evidence is computed once and passed in. It is followed by the unchanged `state_signal.state_table`
  (PPS weights 1/cell_size_acres, area jackknife SE). The test checks that it equals `area_totals`.
- **Cross-check.** The `true_all` 2025 shares below equal the `signal` agent's independently computed 2025 shares
  (`../signal/out/state_satellite_asof_nov.csv`) to 4 decimals in all 15 states: share, called share, SE and field
  counts.

## Results

### 1. Corn classifier, 2025, Nov 15 cut (`out/classifier_cv_by_state.csv`)

These are counts of fields. "Acre ratio" is predicted corn acres divided by CDL corn acres, area-weighted like the
share. Labels come from the CDL, which is itself a classification (a proxy, not field truth).

| state | n | precision LOAO | recall LOAO | accuracy LOAO | acre ratio LOAO | precision LOSO | recall LOSO | acre ratio LOSO |
|---|---|---|---|---|---|---|---|---|
| **all 15** | 47,948 | **0.910** | **0.902** | **0.915** | **1.003** | 0.884 | 0.837 | 0.985 |
| California | 2,958 | 0.779 | 0.771 | 0.808 | 0.933 | 0.683 | 0.386 | 0.574 |
| Colorado | 2,791 | 0.907 | 0.880 | 0.919 | 0.985 | 0.899 | 0.854 | 0.985 |
| Idaho | 2,285 | 0.913 | 0.965 | 0.944 | 1.055 | 0.769 | 0.976 | 1.398 |
| Iowa | 3,420 | 0.983 | 0.984 | 0.981 | 1.001 | 0.982 | 0.986 | 1.002 |
| Kansas | 3,406 | 0.947 | 0.861 | 0.907 | 0.929 | 0.953 | 0.807 | 0.871 |
| Michigan | 4,240 | 0.927 | 0.931 | 0.943 | 1.044 | 0.879 | 0.939 | 1.079 |
| Minnesota | 3,319 | 0.956 | 0.965 | 0.960 | 1.046 | 0.955 | 0.968 | 1.044 |
| Nebraska | 2,693 | 0.914 | 0.942 | 0.924 | 1.066 | 0.908 | 0.953 | 1.079 |
| New York | 2,447 | 0.838 | 0.792 | 0.861 | 0.881 | 0.900 | 0.633 | 0.635 |
| North Dakota | 2,433 | 0.836 | 0.871 | 0.889 | 1.086 | 0.664 | 0.851 | 1.491 |
| Ohio | 4,934 | 0.953 | 0.954 | 0.966 | 1.014 | 0.952 | 0.948 | 1.003 |
| Pennsylvania | 2,769 | 0.782 | 0.826 | 0.833 | 1.105 | 0.773 | 0.785 | 1.066 |
| South Dakota | 3,097 | 0.942 | 0.890 | 0.914 | 0.938 | 0.929 | 0.896 | 1.011 |
| Texas | 3,018 | 0.830 | 0.783 | 0.834 | 0.991 | 0.638 | 0.293 | 0.457 |
| Wisconsin | 4,138 | 0.961 | 0.963 | 0.960 | 0.979 | 0.954 | 0.962 | 0.986 |

74 candidates (0.15%) have no clear look at all. Earlier cut dates cost little when the model is trained in the
same year:

| cut | precision LOAO | recall LOAO | accuracy LOAO | precision LOSO | recall LOSO |
|---|---|---|---|---|---|
| Nov 15 | 0.910 | 0.902 | 0.915 | 0.884 | 0.837 |
| Oct 15 | 0.904 | 0.902 | 0.912 | 0.880 | 0.833 |
| Sep 15 | 0.894 | 0.876 | 0.897 | 0.855 | 0.813 |

Leave-one-state-out collapses where the calendar differs from every other sampled state: Texas recall 0.29 and
California 0.39. A single calendar does not transfer across regions, which is one of the traps the USDA reps named.

### 2. Mask-error replay on 2025 (the key output; `out/mask_error_2025.csv`, `out/mask_error_summary.csv`)

The state silage-like share is computed four ways with the same field model. Leave-one-area-out corn calls are used,
so no area's corn calls come from a model that saw that area.

- `true_all`: CDL corn. This is what the published pipeline uses.
- `pred_all`: classifier corn among all candidates.
- `pred_hist`: classifier corn among fields that were corn in some year from 2019 to 2024. This is the faithful
  replay of 2026, because a candidate pool built from past CDLs cannot contain a field that is corn for the first
  time.
- `det_all`: CDL corn that the classifier also calls corn. This is the omission half of the error only.

Nov 15, per state:

| state | share (a) CDL | share (b) classifier | b - a | pred_hist - a | ratio b/a | jackknife SE of a |
|---|---|---|---|---|---|---|
| Wisconsin | 0.3168 | 0.3063 | -0.0105 | -0.0086 | 0.967 | 0.0397 |
| New York | 0.4767 | 0.4988 | +0.0221 | +0.0209 | 1.046 | 0.0510 |
| South Dakota | 0.1874 | 0.1936 | +0.0062 | +0.0032 | 1.033 | 0.0306 |
| California | 0.7766 | 0.7729 | -0.0037 | -0.0127 | 0.995 | 0.0508 |
| Minnesota | 0.2360 | 0.2407 | +0.0047 | +0.0068 | 1.020 | 0.0190 |
| Iowa | 0.3329 | 0.3328 | -0.0001 | +0.0003 | 1.000 | 0.0427 |
| Michigan | 0.3104 | 0.3224 | +0.0120 | +0.0113 | 1.039 | 0.0299 |
| Pennsylvania | 0.3491 | 0.3381 | -0.0110 | -0.0096 | 0.969 | 0.0525 |
| Kansas | 0.2592 | 0.2651 | +0.0059 | +0.0045 | 1.023 | 0.0335 |
| Nebraska | 0.2008 | 0.1964 | -0.0044 | -0.0044 | 0.978 | 0.0151 |
| Idaho | 0.6848 | 0.6739 | -0.0109 | -0.0222 | 0.984 | 0.0859 |
| North Dakota | 0.2378 | 0.2673 | +0.0295 | +0.0378 | 1.124 | 0.0384 |
| Colorado | 0.3392 | 0.3165 | -0.0227 | -0.0138 | 0.933 | 0.0842 |
| Ohio | 0.2541 | 0.2487 | -0.0054 | -0.0043 | 0.979 | 0.0206 |
| Texas | 0.3850 | 0.3911 | +0.0061 | +0.0088 | 1.016 | 0.0623 |

Across the 15 states (mean / SD / mean absolute; for ratios, the mean absolute is of ratio - 1):

| cut | b - a (share points) | pred_hist - a | logit(b) - logit(a) | ratio b/a |
|---|---|---|---|---|
| Nov 15 | +0.0012 / 0.0135 / 0.0103 | +0.0012 / 0.0151 / 0.0113 | +0.006 / 0.065 / 0.050 | 1.007 / 0.045 / 0.033 |
| Oct 15 | -0.0003 / 0.0167 / 0.0136 | +0.0001 / 0.0182 / 0.0144 | -0.001 / 0.078 / 0.064 | 1.005 / 0.049 / 0.040 |
| Sep 15 | +0.0015 / 0.0107 / 0.0079 | +0.0023 / 0.0122 / 0.0087 | +0.009 / 0.051 / 0.039 | 1.008 / 0.036 / 0.027 |

How to read it:

- **Bias.** The mask adds almost no average bias. The SD across states is 0.013 to 0.015 share points at Nov 15,
  about 4.5 to 5% of the share as a ratio. `state_model` uses the share change as a log-odds difference (`d_sat`)
  and as a plain ratio (`sat_ratio`). If the ratio were applied directly to silage acres, the 2025-replay mask error
  would be about +/-4.5% (1 SD) of state silage acres.
- **Against the signal.** The `signal` agent's 2020-2025 year-to-year share changes have a mean absolute size of
  0.048 and a median same-area SE of 0.032. So the 2025-replay mask error is about a fifth of the signal and a third
  of its sampling error. Added in quadrature it raises the change SE from 0.032 to about 0.035.
- **Why errors partly cancel.** Acre-weighted mean P(silage) of false-positive fields is above that of true
  positives in 11 of 15 states (false positives 0.26 to 0.58). The exceptions are New York, California, Idaho and
  Colorado. Missed corn also scores above detected corn in 12 of 15 states (exceptions: New York, California,
  Idaho). Adding false positives raises the share and dropping missed corn lowers it, so in 2025 the two halves of
  the error partly cancel.
- **New corn.** Fields that were corn in 2025 but in none of 2019-2024 are 6.7% of 2025 corn fields and 4.2% of corn
  acres. Leaving them out (`true_hist - true_all`) moves the share by +0.0015 on average (SD 0.0047). That is small
  next to the classification error.

### 3. Cross-year transfer: the 2026 error is larger than the 2025 replay (`out/cross_year_*`)

The 2026 calls apply a model fitted on 2025 to 2026. Calendar features do not carry the same meaning across years:
planting dates, drought and frost move. The 2025 cross-validation cannot see this. To measure it, the same
leave-one-area-out 2025 models score each area's CDL corn fields from 2019 to 2024. Those years have no non-corn
series on disk, so only recall and the omission half of the share error (`det - true`) can be replayed. False
positives in other years: UNCOMPUTED, because there are no `noncorn<yy>` series for 2019-2024.

| year | acre recall (mean of states) | det - true share: mean / SD / mean abs | ratio det/true: SD |
|---|---|---|---|
| 2019 | 0.865 | +0.0069 / 0.0174 / 0.0106 | 0.048 |
| 2020 | 0.813 | +0.0124 / 0.0270 / 0.0176 | 0.086 |
| 2021 | 0.835 | +0.0178 / 0.0278 / 0.0190 | 0.083 |
| 2022 | 0.812 | +0.0200 / 0.0426 / 0.0289 | 0.131 |
| 2023 | 0.842 | +0.0127 / 0.0438 / 0.0224 | 0.116 |
| 2024 | 0.866 | +0.0038 / 0.0199 / 0.0144 | 0.063 |
| **2019-2024 pooled** | **0.839** | **+0.0123 / 0.0311 / 0.0188** | **0.091** |
| 2025 (same year, LOAO) | 0.924 | -0.0014 / 0.0191 / 0.0122 | 0.037 |

- **Where it breaks.** In other years the omission error is about 1.5 times larger by mean absolute value and 2.5
  times larger by ratio SD. It also becomes biased upward, mean +0.012: unlike 2025, the corn the model misses in
  those years looks more grain-like than the corn it keeps, so the share on detected corn rises. The breakdown is
  concentrated in a few states. Mean absolute omission error over 2019-2024:

  | state | mean abs | acre recall range |
  |---|---|---|
  | Texas | 0.067 | 0.30 to 0.60 |
  | California | 0.060 | 0.66 to 0.85 |
  | Colorado | 0.053 | 0.58 to 0.87 |
  | New York | 0.023 | |
  | Kansas | 0.016 | 0.70 to 0.83 |
  | Pennsylvania | 0.016 | 0.64 to 0.78 |

  Iowa, Minnesota, Nebraska, Ohio, Wisconsin, South Dakota, Michigan, Idaho and North Dakota stay at or below 0.011.
- **Comparison with the signal.** In Texas, California and Colorado this error is as large as a whole typical
  year-to-year share change.

### 4. 2026 calls (`out/corn26_calls.csv`, `out/corn26_sanity.csv`)

The classifier is fitted on all 47,948 2025 candidates (Nov 15 features) and called on the 2026 candidates, with
series cut at Nov 15. The last 2026 look is Nov 9 to Nov 14 depending on the state. 20,479 of 47,948 fields (42.7%)
are called corn; 74 have no clear look.

Sanity check (information only, not used anywhere). The table compares predicted 2026 corn acres in the sample with
2025 cross-validated predicted corn acres, both area-weighted. Pred/pred cancels the classifier's own level bias.

| state | pred 2026 / pred 2025 | NASS planted 2026 Sep / 2025 final |
|---|---|---|
| Texas | 0.70 | 1.00 |
| Colorado | 0.66 | 0.98 |
| Kansas | 0.77 | 1.04 |
| California | 0.85 | 0.88 |
| New York | 1.22 | 1.09 |
| Ohio | 1.20 | 1.01 |
| Idaho | 1.17 | 0.93 |
| Michigan | 1.16 | 0.98 |
| Iowa | 0.97 | 0.98 |
| Wisconsin | 1.00 | 0.96 |

- **Direction.** It agrees with NASS in 8 of 15 states, no better than chance. The classifier's 2026 corn-acre
  changes are not usable as corn-acre estimates.
- **The 30% drops.** The drops in Texas, Colorado and Kansas match the states where cross-year recall collapses
  (section 3). They are a calendar-transfer failure, not a real 30% fall in corn.
- **What the share needs.** The silage share needs only a corn mask whose errors do not bias P(silage). Sections 2
  and 3 bound that.

## What the 2026 forecast should carry

- **Core states.** Iowa, Minnesota, Nebraska, Wisconsin, Ohio, South Dakota, Michigan, Idaho and North Dakota:
  same-year mask error SD 0.013 share points (`pred_all`) to 0.017 (`pred_hist`); log-odds SD 0.066; ratio SD 0.049.
  Cross-year omission mean absolute error 0.011 or less. Add about 0.015 share points (about 0.07 in log-odds, about
  5% in ratio) in quadrature to the share-change SE.
- **Transfer-fragile states.** Texas, California, Colorado and, to a lesser degree, New York, Kansas and
  Pennsylvania: the cross-year omission error alone reaches 0.05 to 0.07 share points, with an upward bias. Their 2026
  satellite share change should be down-weighted or reported as unreliable.
- **Pooled guide.** 2019-2024 omission SD 0.031 (ratio SD 0.091). It is not an upper bound, because the commission
  half is missing in those years.
- **Fixed-mask alternative (not done here; it would be a new pre-declared variant).** Use the classifier's mask in
  both years of the change (2025 CV calls and 2026 calls) instead of the CDL in 2025. Part of the classifier bias
  would then cancel. Whether it does: UNCOMPUTED, because there are no non-corn series before 2025 to measure how
  stable the commission error is from year to year.

## Bug found in shared code (not edited; reported)

`kernelag.field_model.load_series` reads `field_id` as a number and then casts it to text. The series CSVs store
California and Colorado ids with a leading zero (`061825...`, `08...`), so that zero is lost and **no California or
Colorado series joins the sample**. In my first run both states had zero clear looks, and `kernelag.state_signal`
run as-is would produce no share for them. `corn26.read_series_file` reads ids as text; the `signal` agent strips
zeros on both sides. Read this folder's CSVs with `dtype={"field_id": str, "state_fips": str, "cell": str}`.

## Reusable functions (`import corn26` with this folder on `sys.path`)

- `candidates_2025(fips)`, `candidates_2026(fips)`, `read_series(folder, years)`, `read_series_file(path)`
- `corn_features(series, asof)`, `features_for(asof)`, `make_classifier()`, `fit_classifier(table, features)`,
  `p_corn(model, table)`, `grouped_cv(table, group_column, features, extra=None)`, `call_metrics(frame, column)`
- `fit_field_model_all_quebec()`, `field_evidence(series, asof)`, `area_totals_from_features(sample, evidence, model)`,
  `mask_share(sample, evidence, model)`, `mask_replay(candidates, evidence, model)`, `omission_replay(...)`

## Outputs

| file | content |
|---|---|
| `out/classifier_cv_by_state.csv` | per cut date x scheme (LOAO, LOSO) x state (and ALL): counts, precision, recall, accuracy, balanced accuracy, acre precision/recall, corn-acre ratio (raw and area-weighted) |
| `out/cv_predictions_2025.csv` | every 2025 candidate x cut date: is_corn (CDL), history_corn, n_clear, p_loao, p_loso, acres |
| `out/mask_error_2025.csv` | per state x cut date: fields, acres, sat_share, sat_share_calls, share_se under true_all / pred_all / true_hist / pred_hist / det_all; differences, log-odds differences, ratios; mean P(silage) of TP / FP / FN acres |
| `out/mask_error_summary.csv` | mean, SD, mean absolute value, min, max across states of every difference |
| `out/cross_year_recall.csv` | per state x year 2019-2025: recall and acre recall of the 2025 LOAO models on CDL corn |
| `out/cross_year_omission_replay.csv`, `out/cross_year_omission_summary.csv` | per state x year: share on detected CDL corn vs all CDL corn; summary per year and 2019-2024 pooled |
| `out/corn26_calls.csv` | state_fips, cell, field_id, year=2026, p_corn, is_corn, acres, n_clear |
| `out/corn26_sanity.csv` | 2025 true / CV-predicted / fitted corn acres, 2026 predicted corn acres (raw and area-weighted), NASS planted 2025 final and 2026 Sep, direction agreement, last 2026 look |
| `out/run_meta.json` | settings and counts. `last_observation_2025` is the raw end of the cached pull (Nov 22-30); every feature is cut at the stated date |

## Limits

- **CDL labels are a proxy.** They are a classification, not field truth. Precision and recall here are against the
  CDL.
- **One year of negatives.** Only 2025 has non-corn series. False positives under cross-year transfer, and the
  year-to-year stability of the mask bias, are UNCOMPUTED.
- **The 2025 replay is the optimistic case.** Train and test share 2025's weather. Section 3 shows that transfer to
  another year is worse in several states.
- **Candidate pool.** The 2026 pool is fields corn in 2019-2025 (7 CDL years); the 2025 replay pool `pred_hist` uses
  2019-2024 (6 years). Fields that are corn for the first time in 2026 are missing from the 2026 calls (in 2025
  first-time corn was 4.2% of corn acres).
- **Not used for scoring.** The 2025 numbers are used only to measure error. Nothing was selected or tuned on them,
  and the stored 2025 report score is untouched.
