# Feature group `gdd`: thermal-time harvest features

## What

This group takes the optical harvest dates that `kernelag.features.build_features` already finds in
the Sentinel-2 series (`peak_doy` and `cut_doy`) and re-states them in growing degree days. Weather
comes from the Open-Meteo historical archive at the centre of each field's 10 km cell.

| column | role | definition |
|---|---|---|
| `gdd_peak_to_cut` | **pre-registered model feature** | cumulative GDD at `cut_doy` minus cumulative GDD at `peak_doy` |
| `gdd_share_at_cut` | **pre-registered model feature** | cumulative GDD at `cut_doy` divided by cumulative GDD from May 1 to Oct 31 of the same cell-year |
| `gdd_at_cut` | descriptive only | cumulative GDD from May 1 to `cut_doy` |
| `gdd_season_may_oct` | descriptive only | cumulative GDD from May 1 to Oct 31 of the cell-year |

The two model features were fixed in `meta.json` and `build.py` before any evaluation was run, and
they were not changed afterwards. `rule_column` is `null`. The research gives its thresholds relative
to black layer, and nothing here observes black layer, so no benchmark rule can be written without
tuning one.

GDD are degC-days in the corn "modified GDD" form: base 10 C, cap 30 C, `(min(Tmax,30) + max(Tmin,10))/2 - 10`.
Both daily temperatures are clipped to 10-30 C, so a cold day adds zero and never subtracts. This
matches the formula above on every day with Tmax >= 10 C. Sums start on May 1 and include the day itself.
1 C-day = 1.8 F-day. If a day has a missing temperature, every cumulative value after it is NaN. In
practice no day was missing.

## Why

`DOCS/research/agronomy.md` (sections 2.3, 2.4 and 11.1) says the difference between silage and grain
is a thermal gap, not a calendar gap:

- Silage is cut at half milk line, about 200 F-days (about 111 C-days) before black layer.
- Dry grain is combined about 150-375 F-days after black layer. The two fates therefore sit about
  350-575 F-days (about 194-319 C-days) apart on the same field.
- Calendar thresholds fail across regions, one of the traps the USDA reps named. The note recommends
  putting the cut date and the dry-down on a thermal clock (section 11.1, items 1 and 3).

`gdd_share_at_cut` puts a cut on a scale with no units, so a cut in a cool place and a cut in a warm
place can be compared. `gdd_peak_to_cut` measures thermal time from peak greenness (near silking) to
the cut. The research expects that to be shorter for silage (UNL: silage starts "45 days or 800 GDD"
after silking, which is about 444 C-days).

## Data sources

- Sentinel-2 field series: `data/s2_series/<dataset>/<cell>_<year>.csv`, read with
  `kernelag.field_model.load_series`. The cell named in the file name sets which weather a field gets.
- Field geometry and ids from `data/labels/<dataset>.parquet`, used only to check that each labeled
  field-year's 10 km cell (computed with `kernelag.s2_series.assign_cells`, EPSG:32618) matches its
  series file. There were 0 mismatches in all three datasets. `qc_regions_2023` names its cells on
  the grid of the full Quebec file (EPSG:32618), not on its own UTM zone, so it is checked on that grid.
- Weather: [Open-Meteo historical weather API](https://open-meteo.com/en/docs/historical-weather-api),
  `https://archive-api.open-meteo.com/v1/archive`. It is free and needs no key. I asked for daily
  `temperature_2m_max` and `temperature_2m_min`, May 1 to Nov 30, with local-time days. The model was
  `era5_land` (0.1 degree), with `era5` (0.25 degree) as a fallback that was never needed. That makes
  one request per cell-year at the cell centre: 24 requests in sequence with a 1 s pause, plus one
  manual probe while developing. Results are cached in `data/weather_<epsg>_<cell>_<year>.csv`, and a
  re-run never downloads again. Weather data by Open-Meteo.com (CC BY 4.0), based on Copernicus ERA5-Land.

| dataset | cell-years | field-years with a series | with all GDD features | season GDD May-Oct (C-days) |
|---|---|---|---|---|
| quebec_maize_2023 | 1 (79_515) | 318 | 318 | 1,226 |
| qc_regions_2023 | 16 | 2,810 | 2,810 | 1,053-1,381 |
| barc_2021_2023 | 7 (4 cells, 2021-2023) | 107 (44 labeled; the rest are unlabeled farm fields in the same series files) | 107 | 2,036-2,198 |

## How to run

```bash
.venv/Scripts/python.exe test_models/featureTests/gdd/build.py                 # all three datasets
.venv/Scripts/python.exe test_models/featureTests/gdd/build.py --datasets qc_regions_2023
.venv/Scripts/python.exe test_models/featureTests/gdd/build.py --offline       # cached weather only
.venv/Scripts/python.exe -m pytest -q test_models/featureTests/gdd/test_gdd_build.py
```

A run replaces only the rows of the datasets it was asked for. A dataset without labels or series, or
without any weather, is written to `meta.json` under `uncomputed` with the reason. Missing cell-years
go under `partial`.

Outputs in `out/`: `features.csv` (contract file), `meta.json` (contract file), `optical_dates.csv`
(the `peak_doy`, `cut_doy` and cell behind each row), `cells.csv` (centre, weather grid point,
elevation, season GDD per cell-year), `quebec_class_summary.csv` and `quebec_by_cell.csv`.

## Results (Quebec labels only; descriptive, not a model score)

Univariate ROC AUC with silage as the positive class. An AUC below 0.5 means silage has the lower
values. "separation" is max(AUC, 1 - AUC). "within cells" is the AUC over grain-silage pairs from the
same cell only, which is the per-cell AUCs weighted by their pair counts. Maryland labels were never
read here; the harness scores Maryland.

| group | feature | median grain | median silage | AUC | separation |
|---|---|---|---|---|---|
| quebec_maize_2023 (training cell, 318) | gdd_peak_to_cut | 413.4 | 413.4 | 0.506 | 0.506 |
| | gdd_share_at_cut | 0.914 | 0.914 | 0.504 | 0.504 |
| | cut_doy (calendar) | 272 | 272 | 0.504 | 0.504 |
| qc_regions_2023 (16 cells, 2,810) | gdd_peak_to_cut | 502.7 | 424.7 | 0.420 | 0.580 |
| | gdd_share_at_cut | 0.930 | 0.916 | 0.477 | 0.523 |
| | cut_doy (calendar) | 275 | 272 | 0.473 | 0.527 |
| pooled, 17 cells (3,128) | gdd_peak_to_cut | 489.7 | 424.7 | 0.427 | 0.573 |
| | gdd_share_at_cut | 0.930 | 0.916 | 0.476 | 0.524 |
| | cut_doy (calendar) | 275 | 272 | 0.473 | 0.527 |
| | gdd_at_cut (descriptive) | 1,198 | 1,168 | 0.382 | 0.618 |
| within cells, 17 cells | gdd_peak_to_cut | | | 0.473 | 0.527 |
| | gdd_share_at_cut | | | 0.444 | 0.556 |
| | cut_doy (calendar) | | | 0.444 | 0.556 |

What this shows:

1. **Thermal time does not beat the calendar here.** Within one cell, every field shares one weather
   series. That makes `gdd_share_at_cut` and `gdd_at_cut` exact monotone re-scalings of `cut_doy`, so
   their within-cell AUCs are the same number. Across cells, the calendar loses some signal when cells
   are pooled (0.556 within cells, 0.527 pooled), which is the regional trap at a small scale. Dividing
   by the season total does not recover it: `gdd_share_at_cut` gets 0.524 pooled.
2. **The larger pooled AUCs of the absolute-GDD columns are mostly climate, not harvest timing.** Over
   the 16 regional cells, the silage share of a cell falls as its season GDD rises (Spearman -0.74).
   Cooler cells hold more silage, so `gdd_at_cut` (0.618 pooled, 0.556 within cells) and part of
   `gdd_peak_to_cut` (0.573 pooled, 0.527 within cells) act as a location prior. That prior should
   not be expected to transfer to Maryland, whose season is about 2,040-2,200 C-days against
   1,050-1,380 in Quebec. This is why `gdd_at_cut` is descriptive only.
3. **In the training cell, the optical cut timing carries no class signal** (AUC about 0.50). The cut
   dates there pile up on the few clear Sentinel-2 dates (day 272: 96 grain and 63 silage; day 277:
   44 and 44). A thermal re-statement of the same dates cannot add information.
4. **Physically, the expected gap is barely visible in 2023 Quebec.** The median silage
   `gdd_peak_to_cut` (425 C-days, about 765 F-days) agrees with the UNL "800 GDD after silking" silage
   timing. Grain sits only about 80 C-days later, against the 194-319 C-days the research expects. The
   whole of October 2023 added only 78-111 C-days in the Quebec cells (3-6 days added none), so a late
   grain harvest gains almost no thermal time. The optical "cut" of a grain field may also be its
   senescence drop rather than the combine date.

## Limitations

- One year (2023) and one province for every labeled comparison. Season totals span only 1,053-1,381
  C-days, much narrower than the US range where the calendar trap bites hardest.
- One weather series per 10 km cell, taken from the 0.1 degree ERA5-Land grid point nearest the cell
  centre (cells.csv lists the grid point and its elevation; the 88_527 grid point sits at 7 m near the
  St. Lawrence estuary). No within-cell temperature differences are modelled, and reanalysis
  temperatures are not station observations.
- The features inherit every error of the optical `cut_doy` and `peak_doy`, including dates that
  cluster on clear-sky days and the date uncertainty in `cut_gap_days`.
- No planting date or hybrid maturity rating is used. `heat_units` in the Quebec labels is mostly NaN,
  so GDD start on a fixed May 1 rather than at planting, and a field's GDD to black layer is unknown.
- These are univariate descriptive AUCs. Whether the two pre-registered features improve the field
  model (Quebec held-out blocks, Maryland) is for the shared harness to score. Nothing here was tuned
  on Maryland or on the frozen 2025 state score.
