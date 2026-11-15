# Month by month: how accurate are the four selected models on the 15th of July to December?

Owner key: `monthly`. Folder: `test_models/ownModels/monthly/`. Code: `run.py`. Tests: `test_run.py`. Outputs: `out/`.

The question (Daniel, 2026-11-15): "can we try testing it on 2017-2024 but the average from testing in each month? ik the
further away from december the higher the error will be because it didnt collect a lot of data that year but i want to
see, lets try and state the state/us accuracys for both".

What this folder does: it runs the four models that were already selected (no re-selection, no tuning) and their
benchmarks as if we had forecast on the 15th of every month from July to December, in every year 2012-2024. For each
model it reports the state error and the US error at each date, and the average over the dates. The headline period
is 2017-2024; 2012-2024 is reported too. It uses the corrected FSA publication dates (`kernelag/fsa.py` after the fix:
documented release date, else the later of data date + 8 days and the day after FSA's own save time). 2025 is not
used anywhere.

How to read the numbers:
- **state %** = state WAPE: the sum of absolute state misses divided by the true total, averaged over the years. It
  measures how well acres are put in the right states.
- **US %** = absolute error of the US total, averaged over the years.
- Lower is better for both. "Accuracy" is 100 minus these, if you prefer.
- Truth = NASS final acres: 41 states for grain, 48 for silage (states with this year's and last year's NASS final).
- **(F)** = fallback: the model had no FSA file for the current year by that date, so it ran its own fallback path
  (below). "(3/8 F)" means 3 of the 8 years were fallbacks.

## 1. Short answer (2017-2024)

| Crop | Model | 15 Jul | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec | Average of the 6 dates | Average Aug-Dec |
|---|---|---|---|---|---|---|---|---|---|
| Grain | Tier A g3 (no current-year NASS) | 7.35 / 4.11 (F) | 4.58 / 3.66 (3/8 F) | 1.75 / 0.92 | 1.76 / 0.95 | 1.77 / 1.08 | 1.77 / 1.12 | **3.16 / 1.97** | **2.33 / 1.55** |
| Grain | Tier B b7 (NASS-informed) | 5.24 / 2.87 (F) | 3.49 / 2.39 (3/8 F) | 2.08 / 1.08 | 1.72 / 1.00 | 1.74 / 1.05 | 1.74 / 1.07 | **2.67 / 1.58** | **2.15 / 1.32** |
| Grain | NASS's own forecast | 4.01 / 1.56 | 3.26 / 1.30 | 2.53 / 1.05 | 1.66 / 0.82 | 1.66 / 0.82 | 1.66 / 0.82 | **2.46 / 1.06** | **2.15 / 0.96** |
| Silage | Tier A s3 | 13.01 / 3.73 (F) | 13.11 / 4.32 (3/8 F) | 12.64 / 4.09 | 12.60 / 4.09 | 12.53 / 4.02 | 12.51 / 3.97 | **12.73 / 4.04** | **12.68 / 4.10** |
| Silage | Tier B c5b | 13.01 / 3.73 (F) | 12.91 / 3.83 (3/8 F) | 12.71 / 3.95 | 12.67 / 3.99 | 12.66 / 3.94 | 12.65 / 3.93 | **12.77 / 3.90** | **12.72 / 3.93** |
| Silage | Report model `reversion_only` | 13.12 / 3.90 | 13.12 / 3.90 | 13.12 / 3.90 | 13.12 / 3.90 | 13.12 / 3.90 | 13.12 / 3.90 | **13.12 / 3.90** | **13.12 / 3.90** |

Cells are **state % / US %**.

What it means:
- **Your expectation holds for July and August only.** On 15 July no FSA file for the year exists yet in any year, so
  the FSA models are just their fallbacks. On 15 August, 2022, 2023 and 2024 had no FSA file yet. In the other years,
  the August file was sometimes incomplete: the 31 Jul 2020 file held 92.2% of the final file's grain-intended acres.
- **From 15 September on, the error stops falling.** Every September file of 2013-2024 already holds at least 98.3%
  of the final file's grain-intended acres (`data/fsa/fsa_files.csv`, `us_grain_planted`; the 2012 September file is
  corrupt), so later files add very little. Tier A grain is 1.75% on 15 Sep and 1.77% on 15 Dec. Silage moves by about 0.1 point from
  September to December.
- **Grain, compared with NASS:** both own models beat NASS's then-latest forecast on 15 September (section 4). From
  15 October NASS is slightly better: by 0.06-0.12 points of state error, and none of those gaps can be told apart
  from zero on 2017-2024. On the US total NASS is better at almost every date. Averaged over the six dates NASS is
  better, because in July and August our models have little or no current-year data. Averaged over August to
  December, Tier B b7 ties NASS on state error (2.15 vs 2.15) but is worse on the US total (1.32 vs 0.96).
- **Silage:** the FSA models beat the report model's state error from 15 September on (about 12.5-12.7% vs 13.1%), but
  not its US error (about 4.0% vs 3.9%). NASS publishes no in-season silage forecast, so there is no NASS benchmark.

## 2. What each model could see on each date

Every input is cut at the date: FSA files by their corrected publication date (`kernelag.fsa.usable_files` /
`latest_file`); NASS reports by release (June Acreage at the end of June; Crop Production between the 8th and the 12th
of August, September, October and November in every year 2012-2024, `tierB/grain/data/reports_manifest.csv`); NASS
finals of earlier years only; Drought Monitor maps, NASS condition weeks and RMA loss months cut at the 15th.

| Model | What it does when the year's FSA file exists | Fallback when there is none (July always; August 2022-2024) |
|---|---|---|
| Tier A grain `g3_fsa_ratio_multi` | FSA grain-intended acres x median NASS/FSA ratio of the last 3 years | Same as last year (its code's guard) |
| Tier B grain `b7_blend_b5_fsa_level` | sqrt(b5 x g3); b5 = NASS planted x FSA grain share x median correction | b5 becomes NASS's latest planted figure (June Acreage; August Crop Production on 15 Aug 2024) x last year's grain share; g3 becomes last year: b7 = sqrt of the two |
| Tier A silage `s3_fsa_residual` | reversion_only blended with the FSA non-grain residual, weight w fitted on earlier years at the same date | `reversion_only` (finals from 2000) |
| Tier B silage `c5b_residual_fsa_planted_pre_june` | the same with NASS planted (June or later vintage) or FSA-scaled planted | `reversion_only` (finals from 2000) |
| NASS benchmark `nass_latest` | NASS's latest harvested-for-grain forecast published by the date: June Acreage (15 Jul, all 41 states), Aug, Sep, Oct, Nov Crop Production (about 32 states; the others keep their June Acreage number); 15 Dec = November (NASS publishes no December forecast). The October 2013 report was cancelled (shutdown), so 15 Oct 2013 uses September's | none needed |

The FSA file each forecast used (the same file for all four models; `out/fsa_files_used.csv`). "aug 07-31 (pub 08-14)"
means the August file with data as of 31 July, published 14 August:

| Year | 15 Jul | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec |
|---|---|---|---|---|---|---|
| 2012 | none (fallback) | aug 07-31 (pub 08-14) | aug 07-31 (pub 08-14) | oct 10-02 (pub 10-10) | nov 11-05 (pub 11-14) | nov 11-05 (pub 11-14) |
| 2013 | none (fallback) | aug 08-01 (pub 08-09) | aug 08-01 (pub 08-09) | sep 09-01 (pub 09-18) | nov 11-01 (pub 11-09) | dec 12-01 (pub 12-09) |
| 2014 | none (fallback) | aug 08-01 (pub 08-09) | sep 09-01 (pub 09-13) | oct 10-01 (pub 10-15) | nov 11-01 (pub 11-09) | dec 12-01 (pub 12-13) |
| 2015 | none (fallback) | aug 08-03 (pub 08-11) | aug 08-03 (pub 08-11) | oct 10-01 (pub 10-14) | nov 11-02 (pub 11-14) | dec 12-01 (pub 12-09) |
| 2016 | none (fallback) | aug 08-01 (pub 08-10) | sep 09-01 (pub 09-09) | oct 10-03 (pub 10-11) | nov 11-01 (pub 11-09) | dec 12-02 (pub 12-10) |
| 2017 | none (fallback) | aug 08-01 (pub 08-09) | sep 08-31 (pub 09-12) | oct 10-02 (pub 10-11) | nov 11-01 (pub 11-09) | dec 12-01 (pub 12-09) |
| 2018 | none (fallback) | aug 08-01 (pub 08-09) | sep 09-06 (pub 09-14) | oct 10-01 (pub 10-12) | nov 11-01 (pub 11-09) | dec 12-03 (pub 12-11) |
| 2019 | none (fallback) | aug 08-01 (pub 08-09) | sep 09-04 (pub 09-12) | oct 10-01 (pub 10-09) | nov 11-01 (pub 11-09) | dec 12-02 (pub 12-10) |
| 2020 | none (fallback) | aug 07-31 (pub 08-08) | sep 09-01 (pub 09-09) | sep 09-01 (pub 09-09) | nov 11-02 (pub 11-10) | dec 12-01 (pub 12-09) |
| 2021 | none (fallback) | aug 08-02 (pub 08-10) | sep 09-01 (pub 09-09) | sep 09-01 (pub 09-09) | sep 09-01 (pub 09-09) | dec 12-01 (pub 12-09) |
| 2022 | none (fallback) | none (fallback) | sep 09-02 (pub 09-10) | oct 10-03 (pub 10-11) | nov 11-01 (pub 11-09) | dec 12-01 (pub 12-09) |
| 2023 | none (fallback) | none (fallback) | sep 09-01 (pub 09-09) | oct 10-02 (pub 10-10) | nov 11-01 (pub 11-09) | dec 12-01 (pub 12-09) |
| 2024 | none (fallback) | none (fallback) | sep 09-03 (pub 09-11) | oct 10-01 (pub 10-09) | nov 11-01 (pub 11-09) | dec 12-02 (pub 12-10) |

The 2022 August file has data as of 22 August, the 2023 one 9 August (published 17 August under the corrected rule),
and there is no August 2024 file. The 2020 October and 2021 October files are missing or corrupt. The 2021 November file
(data 9 Nov) is dated 17 Nov under the 8-day rule, so 15 Nov 2021 still uses September.

## 3. Full grids, 2017-2024 (headline)

### 3.1 Grain (41 states), state % / US %

| Date | Tier A g3 | Tier B b7 | NASS forecast | Same as last year |
|---|---|---|---|---|
| 15 Jul | 7.35 / 4.11 (F) | 5.24 / 2.87 (F) | 4.01 / 1.56 | 7.35 / 4.11 |
| 15 Aug | 4.58 / 3.66 (3/8 F) | 3.49 / 2.39 (3/8 F) | 3.26 / 1.30 | 7.35 / 4.11 |
| 15 Sep | 1.75 / 0.92 | 2.08 / 1.08 | 2.53 / 1.05 | 7.35 / 4.11 |
| 15 Oct | 1.76 / 0.95 | 1.72 / 1.00 | 1.66 / 0.82 | 7.35 / 4.11 |
| 15 Nov | 1.77 / 1.08 | 1.74 / 1.05 | 1.66 / 0.82 | 7.35 / 4.11 |
| 15 Dec | 1.77 / 1.12 | 1.74 / 1.07 | 1.66 / 0.82 | 7.35 / 4.11 |
| **Average, 6 dates (Jul-Dec)** | **3.16 / 1.97** | **2.67 / 1.58** | **2.46 / 1.06** | 7.35 / 4.11 |
| **Average, 5 dates with FSA (Aug-Dec)** | **2.33 / 1.55** | **2.15 / 1.32** | **2.15 / 0.96** | 7.35 / 4.11 |

Mean signed US error (positive = too many acres): g3 +0.67 (Jul), -0.34 (Aug), +0.64, +0.68, +0.81, +0.85 (Sep-Dec);
b7 +0.74, +0.21, +0.83, +0.75, +0.81, +0.83; NASS +1.37, +1.00, +0.95, +0.72, +0.72, +0.72. From September on, all
three over-predict the US total by about 0.6-0.9% on average.

### 3.2 Silage (48 states), state % / US %

| Date | Tier A s3 | Tier B c5b | Report model `reversion_only` | `reversion_only`, NASS finals from 2000 | Same as last year |
|---|---|---|---|---|---|
| 15 Jul | 13.01 / 3.73 (F) | 13.01 / 3.73 (F) | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |
| 15 Aug | 13.11 / 4.32 (3/8 F) | 12.91 / 3.83 (3/8 F) | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |
| 15 Sep | 12.64 / 4.09 | 12.71 / 3.95 | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |
| 15 Oct | 12.60 / 4.09 | 12.67 / 3.99 | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |
| 15 Nov | 12.53 / 4.02 | 12.66 / 3.94 | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |
| 15 Dec | 12.51 / 3.97 | 12.65 / 3.93 | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |
| **Average, 6 dates (Jul-Dec)** | **12.73 / 4.04** | **12.77 / 3.90** | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |
| **Average, 5 dates with FSA (Aug-Dec)** | **12.68 / 4.10** | **12.72 / 3.93** | 13.12 / 3.90 | 13.01 / 3.73 | 14.53 / 4.08 |

The report model (`kernelag.state_model` `reversion_only`, NASS finals from 2013) can only be backtested for 2017-2024.
The same algorithm on finals from 2000 is the fallback of s3 and c5b, which is why their 15 July cells equal it.
Mean signed US error: s3 -0.99, -1.66, -1.04, -1.05, -0.84, -0.77 (Jul-Dec); c5b -0.99, -1.04, -0.84, -0.79, -0.73,
-0.73; report model -0.98 at every date. All under-predict the US silage total by about 1%.

### 3.3 15 August, split by whether the year's FSA file was out (`out/monthly_split_by_fsa_availability.csv`)

| Years | Tier A g3 | Tier B b7 | NASS | Same as last year |
|---|---|---|---|---|
| 2017-2021 (August FSA file out) | 2.55 / 1.62 | 2.37 / 1.01 | 3.22 / 1.15 | 6.99 / 2.35 |
| 2022-2024 (no file: fallback) | 7.95 / 7.06 | 5.36 / 4.68 | 3.34 / 1.53 | 7.95 / 7.06 |

With its August file, the FSA model is already better than NASS's August state numbers. Without one it is "same as
last year", and that is where the August average comes from. Silage on 15 Aug: s3 13.46 / 4.04 and c5b 13.14 / 3.26 in
2017-2021, against 13.31 / 3.09 for `reversion_only` (finals from 2000) in the same years.

### 3.4 Each year (state %; * = fallback)

| Grain: g3 / b7 / NASS | 15 Jul | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec |
|---|---|---|---|---|---|---|
| 2017 | 5.99* / 4.16* / 3.43 | 1.10 / 1.82 / 3.43 | 1.03 / 1.94 / 3.43 | 1.04 / 0.97 / 0.90 | 1.05 / 0.98 / 0.90 | 1.06 / 0.98 / 0.90 |
| 2018 | 3.68* / 2.81* / 2.22 | 1.70 / 1.93 / 2.22 | 1.68 / 1.93 / 2.22 | 1.74 / 1.76 / 1.55 | 1.76 / 1.77 / 1.55 | 1.78 / 1.77 / 1.55 |
| 2019 | 9.80* / 7.78* / 6.61 | 2.00 / 2.37 / 2.61 | 2.07 / 2.45 / 2.61 | 2.13 / 2.18 / 1.81 | 2.18 / 2.21 / 1.81 | 2.20 / 2.22 / 1.81 |
| 2020 | 8.53* / 6.09* / 4.84 | 6.73 / 4.02 / 4.84 | 1.60 / 2.90 / 4.17 | 1.60 / 1.45 / 1.23 | 1.55 / 1.54 / 1.23 | 1.58 / 1.55 / 1.23 |
| 2021 | 6.97* / 4.44* / 2.99 | 1.24 / 1.71 / 2.99 | 1.24 / 1.19 / 1.61 | 1.24 / 1.19 / 1.61 | 1.24 / 1.19 / 1.61 | 1.21 / 1.18 / 1.61 |
| 2022 | 8.07* / 6.22* / 5.50 | 8.07* / 6.22* / 5.37 | 3.25 / 3.25 / 3.62 | 3.28 / 3.26 / 3.62 | 3.28 / 3.27 / 3.62 | 3.29 / 3.27 / 3.62 |
| 2023 | 9.05* / 6.35* / 3.36 | 9.05* / 6.35* / 3.36 | 1.58 / 1.48 / 1.25 | 1.56 / 1.48 / 1.25 | 1.56 / 1.48 / 1.25 | 1.56 / 1.48 / 1.25 |
| 2024 | 6.73* / 4.07* / 3.10 | 6.73* / 3.50* / 1.29 | 1.56 / 1.49 / 1.29 | 1.51 / 1.46 / 1.29 | 1.51 / 1.46 / 1.29 | 1.50 / 1.46 / 1.29 |

| Silage: s3 / c5b / report `reversion_only` | 15 Jul | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec |
|---|---|---|---|---|---|---|
| 2017 | 12.17* / 12.17* / 12.33 | 11.35 / 11.51 / 12.33 | 11.35 / 11.34 / 12.33 | 11.37 / 11.24 / 12.33 | 11.25 / 11.24 / 12.33 | 11.25 / 11.23 / 12.33 |
| 2018 | 17.88* / 17.88* / 18.82 | 17.97 / 18.00 / 18.82 | 17.92 / 18.13 / 18.82 | 17.95 / 18.18 / 18.82 | 17.95 / 18.16 / 18.82 | 17.96 / 18.14 / 18.82 |
| 2019 | 14.58* / 14.58* / 14.83 | 14.88 / 15.08 / 14.83 | 14.71 / 15.06 / 14.83 | 14.56 / 14.78 / 14.83 | 14.49 / 14.77 / 14.83 | 14.43 / 14.77 / 14.83 |
| 2020 | 9.59* / 9.59* / 9.47 | 11.03 / 8.94 / 9.47 | 8.94 / 8.62 / 9.47 | 8.94 / 8.71 / 9.47 | 8.40 / 8.67 / 9.47 | 8.31 / 8.67 / 9.47 |
| 2021 | 12.31* / 12.31* / 12.35 | 12.07 / 12.17 / 12.35 | 11.85 / 12.12 / 12.35 | 11.75 / 12.12 / 12.35 | 11.75 / 12.09 / 12.35 | 11.73 / 12.04 / 12.35 |
| 2022 | 15.48* / 15.48* / 15.38 | 15.48* / 15.48* / 15.38 | 14.86 / 14.97 / 15.38 | 14.76 / 14.85 / 15.38 | 14.78 / 14.86 / 15.38 | 14.78 / 14.85 / 15.38 |
| 2023 | 9.99* / 9.99* / 9.80 | 9.99* / 9.99* / 9.80 | 9.76 / 9.81 / 9.80 | 9.80 / 9.92 / 9.80 | 9.90 / 9.92 / 9.80 | 9.92 / 9.91 / 9.80 |
| 2024 | 12.11* / 12.11* / 12.00 | 12.11* / 12.11* / 12.00 | 11.78 / 11.66 / 12.00 | 11.70 / 11.58 / 12.00 | 11.70 / 11.59 / 12.00 | 11.70 / 11.59 / 12.00 |

US errors by year are in `out/monthly_by_year.csv` (`us_error_pct`).

## 4. Grain models against NASS at each date (paired by year, 90% bootstrap interval)

Model minus NASS, in points; negative = our model better. 10,000 resamples of years, seed 20261114 (the grain folder's
method). "(k/n)" = years in which our model was better. `out/monthly_vs_nass_ci.csv`.

**2017-2024**

| Date | g3 - NASS, state % | g3 - NASS, US % | b7 - NASS, state % | b7 - NASS, US % |
|---|---|---|---|---|
| 15 Jul | +3.35 [+2.69, +4.07] (0/8) | +2.55 [+0.62, +4.52] (2/8) | +1.23 [+0.88, +1.71] (0/8) | +1.31 [-0.03, +2.74] (2/8) |
| 15 Aug | +1.31 [-0.36, +3.06] (4/8) | +2.36 [+0.61, +4.18] (4/8) | +0.23 [-0.65, +1.16] (5/8) | +1.09 [+0.05, +2.39] (4/8) |
| 15 Sep | **-0.78 [-1.41, -0.19] (6/8)** | -0.13 [-0.50, +0.22] (5/8) | **-0.45 [-0.81, -0.11] (6/8)** | +0.03 [-0.23, +0.29] (5/8) |
| 15 Oct | +0.10 [-0.06, +0.26] (2/8) | +0.13 [-0.12, +0.38] (4/8) | +0.06 [-0.10, +0.21] (2/8) | +0.18 [-0.08, +0.42] (3/8) |
| 15 Nov | +0.11 [-0.06, +0.26] (2/8) | +0.26 [-0.03, +0.53] (3/8) | +0.08 [-0.09, +0.24] (2/8) | +0.24 [-0.05, +0.51] (3/8) |
| 15 Dec | +0.12 [-0.06, +0.28] (2/8) | +0.30 [-0.00, +0.58] (3/8) | +0.08 [-0.10, +0.24] (2/8) | +0.25 [-0.04, +0.53] (3/8) |
| Average, 6 dates | +0.70 [+0.28, +1.16] (1/8) | +0.91 [+0.46, +1.40] (1/8) | +0.21 [-0.05, +0.49] (2/8) | +0.52 [+0.25, +0.82] (1/8) |
| Average, Aug-Dec | +0.17 [-0.25, +0.62] (4/8) | +0.58 [+0.26, +0.90] (2/8) | -0.00 [-0.27, +0.28] (4/8) | +0.36 [+0.17, +0.54] (1/8) |

**2012-2024**

| Date | g3 - NASS, state % | g3 - NASS, US % | b7 - NASS, state % | b7 - NASS, US % |
|---|---|---|---|---|
| 15 Jul | +3.25 [+2.69, +3.81] (0/13) | +2.65 [+1.21, +4.10] (3/13) | +1.26 [+0.94, +1.61] (0/13) | +1.24 [+0.27, +2.24] (3/13) |
| 15 Aug | +1.10 [-0.00, +2.23] (6/13) | +2.22 [+1.06, +3.49] (4/13) | +0.17 [-0.41, +0.80] (8/13) | +0.89 [+0.23, +1.72] (4/13) |
| 15 Sep | -0.29 [-0.84, +0.24] (8/13) | +0.52 [+0.00, +1.07] (6/13) | -0.27 [-0.57, +0.06] (9/13) | +0.16 [-0.04, +0.37] (5/13) |
| 15 Oct | +0.24 [-0.10, +0.63] (5/13) | +0.45 [+0.08, +0.89] (5/13) | +0.17 [-0.12, +0.51] (4/13) | +0.24 [-0.07, +0.57] (5/13) |
| 15 Nov | +0.34 [+0.06, +0.66] (4/13) | +0.54 [+0.20, +0.91] (4/13) | +0.30 [+0.05, +0.60] (3/13) | +0.44 [+0.17, +0.70] (4/13) |
| 15 Dec | +0.32 [+0.05, +0.63] (4/13) | +0.53 [+0.22, +0.85] (4/13) | +0.29 [+0.04, +0.59] (3/13) | +0.43 [+0.17, +0.69] (4/13) |
| Average, 6 dates | +0.83 [+0.48, +1.20] (2/13) | +1.15 [+0.77, +1.56] (1/13) | +0.32 [+0.07, +0.60] (4/13) | +0.56 [+0.35, +0.80] (2/13) |
| Average, Aug-Dec | +0.34 [-0.04, +0.74] (6/13) | +0.85 [+0.50, +1.23] (2/13) | +0.13 [-0.14, +0.44] (7/13) | +0.43 [+0.24, +0.63] (1/13) |

On 2012-2024 the September advantage shrinks and its interval includes zero. This is mostly because 2013 and 2015 lost
their September FSA file under the corrected dates (section 6).

## 5. Full grids, 2012-2024

Grain (state % / US %):

| Date | Tier A g3 | Tier B b7 | NASS forecast | Same as last year |
|---|---|---|---|---|
| 15 Jul | 6.86 / 4.01 (F) | 4.87 / 2.59 (F) | 3.61 / 1.36 | 6.86 / 4.01 |
| 15 Aug | 4.14 / 3.28 (3/13 F) | 3.21 / 1.95 (3/13 F) | 3.04 / 1.06 | 6.86 / 4.01 |
| 15 Sep | 2.29 / 1.43 | 2.31 / 1.07 | 2.58 / 0.91 | 6.86 / 4.01 |
| 15 Oct | 2.00 / 1.15 | 1.93 / 0.94 | 1.76 / 0.70 | 6.86 / 4.01 |
| 15 Nov | 1.94 / 1.11 | 1.90 / 1.01 | 1.60 / 0.57 | 6.86 / 4.01 |
| 15 Dec | 1.92 / 1.10 | 1.89 / 1.01 | 1.60 / 0.57 | 6.86 / 4.01 |
| **Average, 6 dates (Jul-Dec)** | **3.19 / 2.01** | **2.69 / 1.43** | **2.37 / 0.86** | 6.86 / 4.01 |
| **Average, 5 dates with FSA (Aug-Dec)** | **2.46 / 1.61** | **2.25 / 1.19** | **2.12 / 0.76** | 6.86 / 4.01 |

Silage (state % / US %; the report model cannot run before 2017):

| Date | Tier A s3 | Tier B c5b | `reversion_only`, NASS finals from 2000 | Same as last year |
|---|---|---|---|---|
| 15 Jul | 14.11 / 4.85 (F) | 14.11 / 4.85 (F) | 14.11 / 4.85 | 15.84 / 5.76 |
| 15 Aug | 14.12 / 5.16 (3/13 F) | 13.99 / 4.85 (3/13 F) | 14.11 / 4.85 | 15.84 / 5.76 |
| 15 Sep | 13.80 / 5.00 | 13.86 / 4.95 | 14.11 / 4.85 | 15.84 / 5.76 |
| 15 Oct | 13.79 / 5.03 | 13.82 / 4.96 | 14.11 / 4.85 | 15.84 / 5.76 |
| 15 Nov | 13.72 / 4.98 | 13.80 / 4.94 | 14.11 / 4.85 | 15.84 / 5.76 |
| 15 Dec | 13.72 / 4.96 | 13.80 / 4.94 | 14.11 / 4.85 | 15.84 / 5.76 |
| **Average, 6 dates (Jul-Dec)** | **13.88 / 5.00** | **13.90 / 4.92** | 14.11 / 4.85 | 15.84 / 5.76 |
| **Average, 5 dates with FSA (Aug-Dec)** | **13.83 / 5.03** | **13.86 / 4.93** | 14.11 / 4.85 | 15.84 / 5.76 |

## 6. Before and after the FSA publication-date fix

"Before" uses the old dates (data date + 5 days, November 2015 corrupt). The harness was run on the pre-fix tables
(a copy of `data/fsa/` from before the fix) and gives each folder's `out/summary.csv` numbers for all four models at
15 Sep, 15 Oct and 15 Nov: exactly for grain, and within 0.00005 points for silage (those folders write 4 decimals). "After" uses the corrected dates. Cells are
state % / US % / signed US %.

**15 November**

| Model | Period | Before: folder `out/summary.csv` | Before: this harness, pre-fix tables | After: corrected dates | Change (state / US / signed US) |
|---|---|---|---|---|---|
| Tier A grain g3 | 2017-2024 | 1.76 / 1.09 / +0.82 | 1.76 / 1.09 / +0.82 | 1.77 / 1.08 / +0.81 | +0.003 / -0.012 / -0.012 |
| Tier B grain b7 | 2017-2024 | 1.73 / 1.06 / +0.82 | 1.73 / 1.06 / +0.82 | 1.74 / 1.05 / +0.81 | +0.002 / -0.005 / -0.005 |
| Tier A silage s3 | 2017-2024 | 12.52 / 4.00 / -0.82 | 12.52 / 4.00 / -0.82 | 12.53 / 4.02 / -0.84 | +0.004 / +0.022 / -0.022 |
| Tier B silage c5b | 2017-2024 | 12.65 / 3.94 / -0.73 | 12.65 / 3.94 / -0.73 | 12.66 / 3.94 / -0.73 | +0.006 / +0.003 / -0.003 |
| Tier A grain g3 | 2012-2024 | 1.94 / 1.12 / +0.35 | 1.94 / 1.12 / +0.35 | 1.94 / 1.11 / +0.36 | +0.006 / -0.007 / +0.011 |
| Tier B grain b7 | 2012-2024 | 1.89 / 1.01 / +0.45 | 1.89 / 1.01 / +0.45 | 1.90 / 1.01 / +0.45 | +0.005 / +0.006 / +0.006 |
| Tier A silage s3 | 2012-2024 | 13.72 / 4.96 / -1.65 | 13.72 / 4.96 / -1.65 | 13.72 / 4.98 / -1.65 | +0.004 / +0.025 / -0.003 |
| Tier B silage c5b | 2012-2024 | 13.80 / 4.93 / -1.59 | 13.80 / 4.93 / -1.59 | 13.80 / 4.94 / -1.58 | +0.005 / +0.010 / +0.007 |

At 15 Nov the fix changes only two years: 2015 now uses its repaired November file (it used October), and 2021 uses
September (its November file is now dated 17 Nov). Every model moves by less than 0.01 point of state error.

**Other dates, 2017-2024 (state % / US %, before -> after)**

| Model | 15 Jul | 15 Aug | 15 Sep | 15 Oct | 15 Nov | 15 Dec |
|---|---|---|---|---|---|---|
| Tier A grain g3 | unchanged | 3.65/2.55 -> 4.58/3.66 | unchanged | unchanged | 1.76/1.09 -> 1.77/1.08 | unchanged |
| Tier B grain b7 | unchanged | 2.99/1.69 -> 3.49/2.39 | unchanged | unchanged | 1.73/1.06 -> 1.74/1.05 | unchanged |
| Tier A silage s3 | unchanged | 13.08/4.42 -> 13.11/4.32 | 12.63/4.06 -> 12.64/4.09 | 12.61/4.07 -> 12.60/4.09 | 12.52/4.00 -> 12.53/4.02 | unchanged |
| Tier B silage c5b | unchanged | 12.90/4.07 -> 12.91/3.83 | 12.76/3.97 -> 12.71/3.95 | unchanged | 12.65/3.94 -> 12.66/3.94 | unchanged |

The one large change is 15 August: the 2023 August file (data 9 Aug) is now dated 17 Aug, so 2023 falls back to "same
as last year". For g3 that year moves from 1.66% to 9.05% state error. For the silage models a changed input in one
year also changes the fitted weight w of later years at the same date. That is why s3 moves slightly at 15 Sep and
15 Oct in 2017-2024. On 2012-2024, g3 at 15 Sep goes from 2.04 to 2.29 (2013 and 2015 lose their September file and
use August) and at 15 Oct from 1.99 to 2.00. Every changed year-cell is listed by comparing
`out/monthly_by_year_pre_fix_fsa_dates.csv` with `out/monthly_by_year.csv`. Full table: `out/fsa_fix_before_after.csv`.

## 7. Checks (`out/reproduction.json`)

- The four `run.py` files are imported and called unchanged: `predict_all` (grain A), `inputs_for` + `nonfitted`
  (grain B), `run_asof` + `attach_truth` (silage A and B). Only the as-of mapping is widened in memory:
  `kernelag.context.ASOF_MONTH` gains `jul` = 7 and `dec` = 12, and each module's `ASOF` dict (and Tier B silage's
  `ASOF_MONTH`) is replaced in place by the six dates. `patch_asof` refuses to run if a month already there differs.
- On the pre-fix FSA tables the harness reproduces all 51 comparable cells of the folders' summaries (models and
  benchmarks, 15 Sep / Oct / Nov, both periods): the grain models exactly, the silage ones within 0.00005 points (the
  folders' 4-decimal rounding). The only real difference is NASS on 2012-2024, explained in the next point.
- NASS 15 Nov 2017-2024: 1.66% / 0.82%, the incumbent's numbers. 15 Dec equals 15 Nov in every year (maximum
  difference 0).
- June 2013: Quick Stats has no state "harvested for grain" forecast from the June 2013 Acreage report, though the
  report has one. `run.py` parses it from the archived text (`tierB/grain/data/reports/Acre-06-28-2013.txt`; 41
  states, sum = the US line, 89,135,000 acres). The same parser on the other twelve June reports (2012, 2014-2024)
  gives exactly the stored Quick Stats values (difference 0 acres in every state). With it, NASS 15 Jul 2013 is
  3.63% (without it the benchmark would use planted x share: 5.28%). It also gives the 9 small states without a Crop
  Production forecast their June grain number at later 2013 dates, as in every other year. Because of that, NASS's
  2012-2024 means at 15 Sep, Oct and Nov are 0.0025 points lower than in the grain folder's summary. 2017-2024 is
  unchanged.
- Tier B silage's `c0_reversion_only` equals Tier A's `s1_reversion_only` at every date, year and state (difference 0).
- Every FSA file a model used was published on or before the date (checked in `fsa_label`; the folders' own code
  checks this too).
- `test_run.py` (9 tests): the patch; the June 2013 parse and its match with stored years; no FSA file on any 15 July;
  refusal of a file published after the date; g3 in July equals its persistence fallback; NASS December = November;
  scoring and averaging arithmetic.

## 8. How to run and outputs

```bash
.venv/Scripts/python.exe test_models/ownModels/monthly/run.py --old-fsa-root <folder with fsa/fsa_files.csv and fsa/fsa_corn_state.csv from before the fix>   # about 4 min with the before/after run
.venv/Scripts/python.exe test_models/ownModels/monthly/run.py        # corrected dates only (about half the time); before/after then compares with the folders' out/summary.csv
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/monthly/test_run.py
```

The pre-fix tables used here are the fsa_fix agent's backup (copied to this session's scratch folder
`agents/monthly/old_fsa/fsa/`). Scratch can be cleared; the results of that run are kept in `out/`.

| File | Contents |
|---|---|
| `out/monthly_summary.csv` | model, tier, crop, asof (jul..dec, avg_jul_dec, avg_aug_dec), period, n_years, mean_state_wape_pct, mean_abs_us_error_pct, mean_signed_us_error_pct, fallback_share (share of years with no current-year FSA file), fallback_years, worst_year_state_wape_pct |
| `out/monthly_by_year.csv` | per model, date and year: n_states, state_wape_pct, us_error_pct, fallback, FSA file used (with its publication date), detail (guard fallbacks, fitted w, NASS report used) |
| `out/monthly_by_state_year.csv` | every state prediction and the truth |
| `out/monthly_vs_nass_ci.csv` | the paired bootstrap comparisons of section 4 |
| `out/monthly_split_by_fsa_availability.csv` | section 3.3 |
| `out/fsa_files_used.csv` | the FSA file per year and date for each of the four models |
| `out/fsa_fix_before_after.csv`, `out/monthly_by_year_pre_fix_fsa_dates.csv`, `out/reproduction_pre_fix_vs_folders.csv` | section 6 |
| `out/reproduction.json` | section 7 |

## 9. Limitations

- The models are fixed as selected on the 15 Nov backtest. The other dates are earliness checks of the same models, not
  models chosen for those dates. A model built for July (for example from NASS June Acreage alone) could do better
  than these fallbacks. Nothing here was tuned to make that comparison.
- FSA publication dates for files before 2025 are still estimates (documented release where known, else the later of
  data date + 8 days and FSA's save time + 1 day). The August cells depend on them most: 2023 August is dated 17 Aug,
  two days after the forecast date.
- NASS finals of earlier years are today's revised values (a mild look-ahead shared with persistence and with NASS's
  benchmark). RMA and condition data are today's vintage; neither selected grain model uses them, and the silage
  models that read them were not selected.
- Tier B silage takes NASS in-season planted from Quick Stats, which has only the March figure for 2012-2017 (its
  code's known gap; its c5b rule replaces it by FSA-scaled planted). This harness keeps that, since the models are
  fixed.
- 8 headline years (13 in total): the intervals in section 4 are wide, and one year can move an average. 2022 (drought)
  is the worst year for every grain model after August.
- 2025 is not scored here (the frozen 2025 score files are untouched).
