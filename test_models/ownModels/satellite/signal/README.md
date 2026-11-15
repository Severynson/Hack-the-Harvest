# Satellite silage-like share per state and year (agent key: `signal`)

The question: for the 15 sampled states, 2019-2025, what share of the sampled corn acres look like silage
harvests to the Quebec-trained field model, as of 15 Nov (and 15 Oct, 15 Sep)? Does that share's year-to-year
change follow NASS's final silage numbers?

**Short answer.** The **level** of the share ranks states correctly: Spearman 0.90 against NASS silage share of
planted across the 15 states. Its bias is consistent and explained: share ≈ 0.22 + 0.60 x NASS share. The
**year-to-year change does not follow NASS.** The pooled Spearman, with each year's median removed, is
negative: -0.21 for the change in log share (90% CI -0.38 to 0.01). Signs agree in 33 of 90 state-years. The
reason is arithmetic, not bad luck. Grain fields that the model calls silage set a floor (the 0.22 intercept).
That floor dilutes a real change in silage to between 7% (Iowa) and 74% (California) of its size. The diluted
change is smaller than the share's own sampling error from 10 areas, so the expected signal-to-noise ratio is
0.39 (median) and 0.82 at best. With this classifier and 10 areas per state, the satellite change cannot
resolve NASS's typical year-to-year moves. Nothing here was used to select or tune anything.

Code: `signal.py` (field model, state shares, the `state_shares` function, run), `diagnostics.py`,
`noncorn_check.py`. Tests: `test_signal.py`. Everything is written under `out/` in this folder. Nothing goes to
`data/panel/`, so the report is unchanged.

## Method

1. **Field model.** `kernelag.field_model.make_model()` (balanced logistic regression, C=0.5) is fitted on
   `MODEL_FEATURES` for all 3,128 assessable Quebec field-years that have series: `quebec_maize_2023` (318) and
   `qc_regions_2023` (2,810), 17 cells. Training and scoring never touch Maryland or the US sample. The
   reference scores (`out/field_model_reference.csv`) match the shared harness exactly
   (`test_models/featureTests/results/field_summary.csv`, base arm):

   | check | TP | FP | FN | TN | balanced accuracy |
   |---|---|---|---|---|---|
   | Quebec leave-one-cell-out (17 cells) | 877 | 345 | 390 | 1516 | 0.753 |
   | Maryland, all-Quebec fit (44 field-years) | 10 | 4 | 2 | 28 | 0.854 |

   Coefficients per standard deviation (`out/field_model_coefficients.csv`): max_drop +0.91, max_drop_rate
   +0.67, ndmi_before_cut +0.38, ndti_post -0.30, fade_days -0.17, green_at_cut -0.04.
2. **Fields.** Each sampled corn field-year in `data/samples/corn_<fips>.parquet` (148,900 field-years; corn =
   that year's CDL) gets `kernelag.features.build_features` from its Sentinel-2 series. The series is first cut at
   the 15th of the forecast month by `kernelag.state_signal.series_asof`. Every output row's
   `last_observation_date` is on or before its `asof_date`, and a test checks this. Assessable means a drop
   can be read. P(silage) comes from the model.
3. **Areas.** For each area and year (the same steps as `kernelag.state_signal.area_totals`, checked
   in a test): assessable corn acres, silage-like acres (acres x P), and called acres (P >= 0.5).
4. **States.** `kernelag.state_signal.share` divides each area by its `cell_size_acres`, so every area drawn
   with probability proportional to size counts equally. The SE is the leave-one-area-out jackknife
   (`state_table`). Only complete areas are used (`complete_areas`). All 10 areas are complete in every
   state. "areas" = 9 marks a year in which one area had no corn: Idaho 2019, South Dakota 2019, 2020 and 2025.
5. **Changes** (`out/state_satellite_changes_asof_*.csv`): d_share, d_log_share and d_logit_share between
   consecutive years on the same areas. Their jackknife SE leaves an area out of both years at once.

## Outputs (`out/`)

| file | content |
|---|---|
| `state_satellite_asof_{nov,oct,sep}.csv` | state, state_fips, year, areas, fields, assessable_share, sat_share, sat_share_calls, share_se, median_cut_doy, then assessable_areas, share_se_calls, median_peak_doy, corn_fields_assessable, asof, asof_date, last_observation_date (105 state-years each) |
| `state_satellite_changes_asof_*.csv` | year-to-year changes with same-area jackknife SEs |
| `area_totals_asof_*.csv` | per state, area and year totals |
| `field_probabilities_asof_*.parquet` | per field-year: assessable, p_silage, cut_doy, peak_doy |
| `diagnostics_changes.csv`, `diagnostics_by_state_asof_*.csv`, `diagnostics_level*.csv`, `diagnostics_explain.csv`, `diagnostics_summary.json` | section "Diagnostics" |
| `noncorn25_share.csv` | how silage-like non-corn fields look (corn-mask sensitivity) |
| `field_model_reference.csv`, `field_model_coefficients.csv`, `run_meta.json` | field model checks |

### Shares as of 15 Nov (sat_share, probability-weighted)

| state | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | NASS silage/planted (mean 2019-24) |
|---|---|---|---|---|---|---|---|---|
| CALIFORNIA | 0.739 | 0.713 | 0.692 | 0.708 | 0.679 | 0.762 | 0.777 | 0.875 |
| IDAHO | 0.668 | 0.676 | 0.730 | 0.733 | 0.753 | 0.605 | 0.685 | 0.663 |
| NEW YORK | 0.408 | 0.360 | 0.513 | 0.413 | 0.359 | 0.424 | 0.477 | 0.435 |
| PENNSYLVANIA | 0.345 | 0.366 | 0.400 | 0.374 | 0.360 | 0.435 | 0.349 | 0.298 |
| WISCONSIN | 0.361 | 0.313 | 0.319 | 0.305 | 0.370 | 0.325 | 0.317 | 0.225 |
| MICHIGAN | 0.396 | 0.292 | 0.398 | 0.303 | 0.428 | 0.376 | 0.310 | 0.147 |
| COLORADO | 0.309 | 0.312 | 0.297 | 0.349 | 0.341 | 0.322 | 0.339 | 0.144 |
| TEXAS | 0.382 | 0.340 | 0.288 | 0.295 | 0.292 | 0.328 | 0.385 | 0.109 |
| SOUTH DAKOTA | 0.272 | 0.271 | 0.177 | 0.148 | 0.213 | 0.175 | 0.187 | 0.080 |
| NORTH DAKOTA | 0.286 | 0.263 | 0.187 | 0.205 | 0.310 | 0.194 | 0.238 | 0.061 |
| MINNESOTA | 0.294 | 0.354 | 0.254 | 0.256 | 0.331 | 0.192 | 0.236 | 0.051 |
| KANSAS | 0.197 | 0.212 | 0.230 | 0.218 | 0.259 | 0.205 | 0.259 | 0.051 |
| OHIO | 0.262 | 0.224 | 0.298 | 0.327 | 0.336 | 0.246 | 0.254 | 0.051 |
| NEBRASKA | 0.213 | 0.244 | 0.200 | 0.222 | 0.155 | 0.160 | 0.201 | 0.029 |
| IOWA | 0.305 | 0.216 | 0.205 | 0.209 | 0.254 | 0.206 | 0.333 | 0.026 |

Assessable share is 0.994 or more in every state-year as of Nov. The median share SE is 0.036.

## Diagnostics (`diagnostics.py`; information only, no selection)

**Level.** Across states (means of 2019-2024):

| as of | signal | Spearman | Pearson | sat = a + b x NASS share |
|---|---|---|---|---|
| Nov | sat_share | 0.900 | 0.964 | 0.217 + 0.603 x |
| Nov | sat_share_calls | 0.879 | 0.971 | 0.065 + 0.800 x |
| Oct | sat_share | 0.882 | 0.940 | 0.233 + 0.543 x |
| Sep | sat_share | 0.450 | 0.857 | 0.234 + 0.242 x |

The bias has the expected form. The intercept is roughly the false-positive rate on grain fields: Quebec
leave-one-cell-out FPR was 0.185, against an intercept of 0.22 for the probabilities. The slope is
roughly (recall - FPR). Probabilities from a balanced logistic sit near 0.5 more often than calls do, so the
probability share has a higher floor than the called share. The year-by-year cross-state Spearman for Nov
ranges from 0.75 to 0.87.

**Changes, 2020-2025** (15 states x 6 years = 90 state-years; each year's cross-state median removed; 90% CI
from resampling whole states):

| as of | signal | vs d log(NASS silage/planted) | vs d log(NASS silage acres) |
|---|---|---|---|
| Nov | sat_share | -0.209 [-0.382, 0.009] | -0.267 [-0.478, -0.005] |
| Nov | sat_share_calls | -0.124 [-0.329, 0.110] | -0.273 [-0.523, 0.042] |
| Oct | sat_share | -0.260 [-0.400, -0.063] | -0.322 [-0.480, -0.082] |
| Oct | sat_share_calls | -0.238 [-0.466, -0.008] | -0.302 [-0.545, -0.021] |
| Sep | sat_share | -0.107 [-0.264, 0.056] | -0.135 [-0.301, 0.038] |
| Sep | sat_share_calls | -0.268 [-0.428, -0.099] | -0.251 [-0.441, -0.056] |

On 2020-2024 only (2025 left out), Nov sat_share is -0.108 [-0.346, 0.137] against the share and -0.201 against
acres. Without removing year medians the numbers are about the same: -0.222 and -0.255. The log-odds change,
which is what `kernelag.state_model` would use as `d_sat`, gives -0.187 and -0.241. Sign agreement as of
Nov, with year medians removed: 33/90 against the NASS share and 34/90 against NASS acres. Per state it ranges
from 0/6 (California, Minnesota) to 4/6 (Iowa, Michigan).

**Signal-to-noise** (`diagnostics_by_state_asof_nov.csv`):

- The share does move by more than its sampling noise. The SD of d_share across years divided by its same-area
  jackknife SE has a median of 1.59 (range 0.97 Idaho to 3.20 Michigan). The median jackknife SE of d_share is
  0.032; the median SD of d_share is 0.056.
- That movement is not NASS's movement. The sampling SE of d log share is 0.80x the year-to-year SD of
  d log(NASS share) (median; 2.04 Idaho, 1.42 Michigan, 0.35 North Dakota).
- Dilution: if sat = a + b x NASS share, a change of d log(NASS share) moves the satellite share by
  b x NASS/sat x d log(NASS share). The dilution factor is 0.07 in Iowa, 0.09 Nebraska, 0.11 Minnesota and Ohio,
  0.41 Wisconsin, 0.64 New York and 0.74 California. Expected SNR = diluted NASS spread / sampling SE: median
  0.39, maximum 0.82 (California). So even an unbiased-in-change classifier on 10 areas would not see typical
  changes. Part of the realized movement (SNR 1.6) is therefore classifier response to the season.

**What the satellite change moves with** (`diagnostics_explain.csv`, Nov, year medians removed). The strongest
association is May-Sep heat units, d gdd_anom: +0.262 [0.093, 0.408]. NASS's share moves the other way, -0.158.
Drought gives +0.128 for satellite and +0.104 for NASS. Final grain yield gives +0.114 for satellite and -0.152
for NASS. The change in assessability gives -0.033. The change in median cut day gives +0.020. Warmer seasons
look more silage-like to the model: drop size and speed rise. This explains part of the negative sign, not all
of it.

**Earliness.** As of Oct, shares and their diagnostics are close to Nov (mean share 0.353 vs 0.348; level
Spearman 0.88). As of Sep, many fields are not harvested yet. Assessable share drops to 0.65 in New York 2019,
0.74 in New York 2021 and 0.79 in Ohio 2023. The median cut day becomes 248 (Nov: 267.5), and the level slope
falls to 0.24 (Spearman 0.45). The Sep share counts only harvests that happened before 15 September and is
not the same quantity as the Nov share.

## Look-ahead and the corn mask (2026)

In 2019-2025 the fields come from that year's Cropland Data Layer, which is published after the season, so every
share above assumes a **perfect corn mask**. In 2026 the corn fields must be called from imagery
(`test_models/ownModels/satellite/corn26`). The tables above do NOT include that error. `noncorn_check.py`
measures how silage-like non-corn fields look. It uses the 2025 negatives (`noncorn25_*`: fields corn in some
year 2019-2025 but not in 2025), with the same estimator and dates (`out/noncorn25_share.csv`, Nov):

- Non-corn share minus corn share, 2025: Iowa +0.19, Michigan +0.19, Minnesota +0.26, Nebraska +0.19, Ohio
  +0.25, North Dakota +0.15, South Dakota +0.14, Kansas +0.09, Wisconsin +0.05; Pennsylvania -0.02, Texas
  -0.06, Colorado -0.08, New York -0.10, Idaho -0.22, California -0.51 (median +0.09). Soybean leaf drop is a
  big, fast greenness drop, which looks like a silage cut.
- A leak of L (share of the "corn" acres that are not corn) shifts the 2026 share by about L x that difference.
  In the Corn Belt a 10% leak adds about 0.02, the size of a typical year-to-year change (median over states of the median |d_share|: 0.036).
  Because 2025 uses the CDL mask and 2026 uses calls, this shift goes straight into the 2025-to-2026 change. The
  fair comparison is a 2025 share computed with the same classifier's corn calls, cross-fitted. Missed corn
  (false negatives) changes the share only if the missed fields differ in silage-likeness.
- Smoke test of the 2026 interface, NOT a forecast and not saved: with no corn mask at all (every corn26 field,
  i.e. every field that was corn in some year 2019-2025), the Wisconsin 2026 share is 0.435 (SE 0.017), against
  0.317 for CDL corn in 2025. California gives 0.494 against 0.777. An unmasked share mostly measures the crop
  mix.

## Using it for 2026 (evaluation agent)

```python
import importlib.util
from pathlib import Path
import geopandas as gpd
import pandas as pd
from kernelag.field_model import load_series

spec = importlib.util.spec_from_file_location("satellite_signal", "test_models/ownModels/satellite/signal/signal.py")
sig = importlib.util.module_from_spec(spec); spec.loader.exec_module(sig)   # never `import signal` (stdlib name)
model, _ = sig.fit_allqc_model()                                   # the exact model used for 2019-2025 (~20 s)
rows = gpd.read_parquet("data/samples/corn26_55.parquet")
rows = rows[rows["field_id"].isin(corn_ids)]                       # is_corn from the corn classifier
rows = sig.complete_sample(rows, Path("data/s2_series/corn26_55"))   # same 10 areas as the history
series = load_series(Path("data/s2_series/corn26_55"))
table, totals, fields = sig.state_shares(rows, series, model, "nov", detail=True)   # year 2026 row(s)
# 2025 -> 2026 change with a same-area jackknife SE:
hist = pd.read_csv(sig.OUT / "area_totals_asof_nov.csv", dtype={"state_fips": str, "cell": str})
change = sig.share_changes(pd.concat([hist[hist["year"] == 2025], totals], ignore_index=True))
```

`state_shares` accepts several states at once (grouped by state_fips). It cuts the series at the forecast date
itself, so pass the uncut series.

## Limitations

- **Change signal:** negative to null association with NASS changes at every date, and an expected SNR below 1
  in every state. Do not read d_sat as evidence of acreage change without a better classifier (lower false
  positive floor) or many more areas. This is a diagnostic only; nothing was selected or tuned, and 2025 is
  information only. The stored 2025 report score is untouched.
- **Level:** strong across states, but it is ecological (15 points), and the fit uses NASS finals. Turning the
  level into acres would be a calibration on NASS history (Tier question for the evaluation agent).
- **Perfect corn mask in 2019-2025** (above). The 2026 share carries the corn-call error; its size depends on the
  classifier's leak rate, which is not estimated here.
- **Classifier transfer:** trained on Quebec 2023 only, scored on 15 US states and 7 years with different
  calendars (Texas median cut day 207, New York 278). Maryland (one farm) is the only US check.
- **Sampling:** 10 areas per state; same areas every year (changes are paired); the jackknife with 10 areas is
  itself noisy. Field acres are CSB polygon acres, not farmer-reported acres.
- **Bug found in shared code (not edited, not mine to edit):** `kernelag.field_model.load_series` reads
  `field_id` as a number before casting to text. CSB ids of states with FIPS 01-09 (California 06, Colorado 08)
  lose their leading zero and no longer join `data/samples/corn_06/08.parquet`. As written,
  `kernelag.state_signal` would silently drop both states, because every field is "not assessable". This
  folder matches ids on their digits (`signal.align_field_ids`, tested), and `signal.py` refuses to finish if
  any state comes out empty. Any other agent joining these series (corn26 included) must do the same.

## Run

From the repo root:

```bash
.venv/Scripts/python.exe -m test_models.ownModels.satellite.signal.signal --workers 15   # ~6 min, all 3 dates
.venv/Scripts/python.exe -m test_models.ownModels.satellite.signal.noncorn_check          # ~2 min
.venv/Scripts/python.exe -m test_models.ownModels.satellite.signal.diagnostics            # ~3 min
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/satellite/signal/test_signal.py   # 10 tests
```

Use `-m` with the dotted name. The file name `signal.py` would otherwise shadow the standard-library module. The
scripts also take their own folder off `sys.path` for safety.
