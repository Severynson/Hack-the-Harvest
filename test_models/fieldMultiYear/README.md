# Field model across years (Quebec 2019–2026)

The published field model is fitted on Quebec 2023 only. This folder adds the other years in the same
17 areas, so a model can be fitted on several seasons and scored on a year it never saw (the
held-out-year test the organizers asked for).

## Data (`qcm_<year>`, built by `data_build.py`)

### What it is

- **Source.** FADQ's declared-parcel database (BDPPAD), one zip per year, CC-BY 4.0. The URLs follow
  `kernelag.quebec.FILE_URL` and `LOWERCASE_V_YEARS`. The download uses the `requests` library's default
  client headers, and FADQ served every year with HTTP 200 (2026-11-15).
- **Labels.** `kernelag.quebec.label_parcels`, unchanged: grain = `MGR`, silage = `MFO`/`MFE`, single crop,
  at least 2 ha. A handful of `MGN` parcels each year fall outside these codes and are dropped, as in 2023.
- **Areas.** The same 17 cells as the 2023 model: cell `79_515` (`quebec_maize_2023`'s series) plus the 16
  cells of `qc_regions_2023`. A cell is the representative point of a parcel in EPSG:32618, floored to 10 km.
  That is exactly what `kernelag.s2_series.assign_cells` did for the whole 2023 table. The zone is fixed in
  the code because a table of only these cells would resolve to EPSG:32619. Every labeled parcel whose
  point falls in one of the 17 cells is kept. There is no sampling inside a cell.
- **Check.** `data_build.py verify` recomputes the 2023 cells. 2,889 of 2,889 match `qc_regions_2023`'s
  `cell` column, and the fixed-zone function matches `assign_cells` on all 44,753 parcels of 2023.
  `qc_regions_2023` holds every parcel of its 16 cells, and cell 79_515 has 321 parcels.
- **Names.** Every file is prefixed `qcm_`, so field_model's `TRAIN_PATTERN = "quebec_maize_*"` never picks
  them up and the published metrics do not change.

| Path | Contents |
|---|---|
| `data/raw/quebec/BDPPAD_<V\|v>03_<year>.zip` | FADQ's file as served, 162–172 MB each (git-ignored `data/raw/`) |
| `data/labels/qcm_<year>.parquet` | `field_id` (text, FADQ `IDANPAR`, unique within and across years), `parcel_id` (`IDPAR`), `year`, `label`, `hectares`, `heat_units`, `cell`, `geometry` (EPSG:4326) |
| `data/s2_series/qcm_<year>/<cell>_<year>.csv` | Sentinel-2 series, `kernelag.s2_series` columns |

**2023 is reused, not downloaded again.** `qcm_2023` is the 17-cell subset of `quebec_maize_2023`. Its
series are byte copies of the published `quebec_maize_2023/79_515_2023.csv` and
`qc_regions_2023/<cell>_2023.csv`. So the 2023 rows are the same 3,128 field-years the feature harness's E2
evaluation uses.

### Parcels per year and class (17 cells)

| Year | Labeled maize parcels, all Quebec | In the 17 cells | Grain | Silage | Grain ha | Silage ha | FADQ file date |
|---|---|---|---|---|---|---|---|
| 2019 | 43,859 | 2,644 | 1,579 | 1,065 | 10,961 | 6,433 | 2019-12-21 |
| 2020 | 39,129 | 2,393 | 1,416 | 977 | 9,788 | 6,009 | 2021-04-29 |
| 2021 | 41,830 | 2,660 | 1,566 | 1,094 | 11,217 | 6,569 | 2023-01-09 |
| 2022 | 43,032 | 2,915 | 1,825 | 1,090 | 12,941 | 6,824 | 2024-01-01 |
| 2023 | 44,753 | 3,210 | 1,910 | 1,300 | 13,537 | 8,229 | (published table) |
| 2024 | 43,538 | 2,996 | 1,761 | 1,235 | 12,628 | 8,097 | 2026-01-05 |
| 2025 | 41,142 | 2,888 | 1,553 | 1,335 | 11,361 | 8,863 | 2026-11-09 |
| 2026 | 43,351 | 2,864 | 1,567 | 1,297 | 11,886 | 8,870 | 2026-11-09 |

All 17 cells have parcels in every year. The file date is the snapshot date in the shapefile's name.

### Sentinel-2 series

Pulled with `KERNEL_S2_SOURCE=earthsearch` (Element 84 Earth Search, Collection 1). Earth Search has no
Collection 1 scenes over these cells for 2022 (0 found, 43–45 for 2021), so every 2022 cell fell back to
Planetary Computer on its own, pulled with `--parallel 3`. 2023 is the published Planetary Computer pull
(see above). Every pull finished on the first run, so no cell needed a rerun.

| Year | Source | Cell files | Field-dates | Dates | Fields with series / labeled | Field-years with labels | Silage / grain | Assessable | Last date |
|---|---|---|---|---|---|---|---|---|---|
| 2019 | Earth Search | 17/17 | 65,310 | 72 | 2,566 / 2,644 | 2,566 | 1,030 / 1,536 | 2,563 (99.9%) | 2019-11-29 |
| 2020 | Earth Search | 17/17 | 65,298 | 81 | 2,325 / 2,393 | 2,325 | 948 / 1,377 | 2,309 (99.3%) | 2020-11-21 |
| 2021 | Earth Search | 17/17 | 76,771 | 80 | 2,598 / 2,660 | 2,598 | 1,062 / 1,536 | 2,598 (100%) | 2021-11-28 |
| 2022 | Planetary Computer | 17/17 | 74,034 | 71 | 2,839 / 2,915 | 2,839 | 1,057 / 1,782 | 2,807 (98.9%) | 2022-11-28 |
| 2023 | Planetary Computer (copied) | 17/17 | 79,224 | 71 | 3,128 / 3,210 | 3,128 | 1,267 / 1,861 | 3,128 (100%) | 2023-11-28 |
| 2024 | Earth Search | 17/17 | 88,009 | 84 | 2,938 / 2,996 | 2,938 | 1,213 / 1,725 | 2,938 (100%) | 2024-11-27 |
| 2025 | Earth Search | 17/17 | 85,082 | 84 | 2,826 / 2,888 | 2,826 | 1,306 / 1,520 | 2,826 (100%) | 2025-11-29 |
| 2026 | Earth Search | 17/17 | 88,342 | 79 | 2,806 / 2,864 | 2,806 | 1,266 / 1,540 | 2,806 (100%) | 2026-11-12 |

"Assessable" means `kernelag.field_model.evidence_table` finds a greenness drop. Across the 8 years, 544
labeled fields have no series. 365 of them vanish entirely under the 20 m inner buffer. The rest are also
small: median about 3 ha, against 5.2–5.6 ha for fields with a series. Every scene carries the
1000-count processing-baseline offset (`s2_offset` = 1000). In total there are 22,026 field-years with a
series across the 8 years, 9,149 of them silage.

### Things a model built on this must handle

- **The same field recurs across years.** The 22,570 labeled parcel-years are 12,078 distinct FADQ
  `parcel_id`s. 6,210 of these appear in more than one year, and 1,233 of those switch between grain and
  silage. Holding out a year keeps that year's season unseen, but not its fields. For a test that also
  holds out the field, group folds by `parcel_id` or by cell.
- **Two sources.** 2022 and 2023 come from Planetary Computer, the other years from Earth Search.
  `kernelag.s2_series` reports the two agree to about 0.004 NDVI on the Maryland fields. That agreement
  was not re-checked on these Quebec cells.
- **Two pixel grids in 2023.** Cell 79_515's 2023 series was pulled with the whole 2023 table, in
  EPSG:32618. The other 2023 cells, and every cell in the other years, were pulled from 17-cell tables,
  which resolve to EPSG:32619. Only the 20 m resampling grid differs; the cell ids do not.
- **2025 and 2026 are recent snapshots.** Both files are dated 2026-11-09. Farmers can change the harvest
  mode until mid-September, and FADQ may still revise these files. The 2026 series stops at 2026-11-12.
- **Declarations, not observed harvests.** The limits in `kernelag/quebec.py` apply to every year. Silage
  on farms insured only for feed needs is missing, so silage is under-counted.
- **`heat_units` is nearly empty** (0.1–0.6% filled each year). It is kept only because `label_parcels`
  writes it.
- **Manifest.** Rows for these files are not yet in `data/DATA_MANIFEST.tsv`. The pulls ran with
  `KERNEL_NO_MANIFEST=1` because that file belongs to another owner. Its owner can add them with
  `python3 scripts/pull_data.py manifest`.

### Rebuild

From the repository root (Git Bash):

```bash
.venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py verify
.venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py download      # 7 zips, about 1.2 GB
.venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py labels        # about 10 s a year
.venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py copy2023
for y in 2019 2020 2021 2024 2025 2026; do
  KERNEL_S2_SOURCE=earthsearch KERNEL_NO_MANIFEST=1 AGENT_ID=cc-daniel \
    .venv/Scripts/python.exe -m kernelag.s2_series --fields data/labels/qcm_$y.parquet --cells 0 --parallel 6
done
KERNEL_S2_SOURCE=earthsearch KERNEL_NO_MANIFEST=1 AGENT_ID=cc-daniel \
  .venv/Scripts/python.exe -m kernelag.s2_series --fields data/labels/qcm_2022.parquet --cells 0 --parallel 3
.venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py check
```

Every step skips work that is already done (`--force` rebuilds). On this Windows machine (24 cores),
2026-11-15, each Earth Search year took about 3–5 minutes with two years running at once. 2022 on
Planetary Computer took about 9 minutes with 3 workers.

## Evaluation (`evaluate.py`)

The block between the two markers below is the pre-registration. It was written on 2026-11-15 before any
multi-year model was fitted or scored. `evaluate.py prereg` hashes it (SHA-256 of the UTF-8 text between
the marker lines, LF line endings) into `out/preregistration.sha256` and keeps a frozen copy in
`out/preregistration_frozen.md`. `evaluate.py score` refuses to run if the block no longer matches the hash.

<!-- PREREGISTRATION:BEGIN -->
### Pre-registration

**Question.** Does fitting the field model on several Quebec seasons, instead of 2023 alone, give better
silage-or-grain calls on a season the model has never seen?

**Data.** `qcm_2019` to `qcm_2026` (labels and Sentinel-2 series in the 17 cells, built by `data_build.py`).
The roster of each year is `kernelag.field_model.evidence_table`: the labeled field-years that have a series
(inner join), 22,026 field-years expected over the eight years. A field-year's area is the label table's
`cell` column. 2026 counts like any other year (declarations dated 2026-11-09, series to 2026-11-12). The
Maryland roster is all 44 field-years of `barc_2021_2023`, read with `kernelag.evaluate.evaluation_table`,
which keeps field-years without evidence.

**Model (fixed; nothing is tuned).** `kernelag.field_model.make_model()` (median imputer, standard scaler,
logistic regression with balanced class weights, C = 0.5) on `MODEL_FEATURES` from
`kernelag.features.build_features`, called silage at `DECISION_THRESHOLD` = 0.5. It is fitted on
assessable rows only (a greenness drop was found); a row that is not assessable is scored as grain. Every
field-year is one row of weight 1. There is no year weighting, no feature selection, no threshold change
and no hyperparameter search. Two training sets are compared:

- **M (multi-year):** every qcm year except the held-out one.
- **S (2023-only):** `qcm_2023`, the current model's year in the same 17 cells (the harness's E3b fit).

**Splits.**

1. **Leave one year out (LOYO, primary).** For each year Y from 2019 to 2026, M is fitted on the other
   seven years and scores year Y. S is fitted once on 2023 and scores every year Y other than 2023. S on
   2023 would be scored on its own training rows: that row is reported as in-sample and left out of every
   comparison.
2. **Leave one area out, pooled over years (supporting).** For each of the 17 cells, a model is fitted on
   the other 16 cells in all eight years and scores the held-out cell in all eight years. Reported pooled
   over the 17 folds and broken down by year.
3. **Leave one year and one area out (supporting, strictest).** For each year Y other than 2023 and each
   cell C: M is fitted on the other seven years in the other 16 cells, S on 2023 in the other 16 cells,
   and both score cell C in year Y. Neither model has seen that season or that area, so the fields that
   recur across years cannot help either one (apart from a parcel whose outline crossed a cell edge).
4. **Maryland transfer (information only, never selection).** Fits on (a) `quebec_maize_2023` (the
   published 318-parcel fit), (b) `qcm_2023` and (c) all eight qcm years each score the 44 Maryland
   field-years. (c) versus (b) also gets a paired bootstrap over Maryland fields, for information.
5. **Coefficient stability.** Fits on each single year (eight fits), on all eight years, and the eight LOYO
   M fits. For each: the logistic weight per standard deviation of each feature (each fit standardises on
   its own training rows) and the intercept. The spread across the eight single-year fits is given as the
   mean, standard deviation, minimum and maximum, and the number of years whose sign matches the
   all-years fit.

**Reproduction gates.** These are checked before any comparison is read.

- G1: S scored leave-one-cell-out on 2023 alone must give TP 877 / FP 345 / FN 390 / TN 1516 (the feature
  harness's E2 base arm).
- G2: fit (a) on Maryland must give TP 10 / FP 5 / FN 2 / TN 27 (`data/models/field_model_report.csv`).
- G3: fit (b) on Maryland must give TP 10 / FP 4 / FN 2 / TN 28 (the harness's E3b base arm).

If a gate fails, every number is still reported, but the decision reads `HELD (gate failed)` with the reason.

**Metrics.** For every split, model and held-out year, and pooled: TP, FP, FN and TN with silage as the
positive class, silage precision, silage recall, balanced accuracy (the mean of silage recall and grain
recall), silage F1, accuracy and false positive rate (`kernelag.evaluate.extended_scores`), plus the number
of field-years and of assessable ones. A pooled metric is computed from the summed confusion counts of the
field-years concerned, not by averaging yearly metrics.

**Primary comparison.** Pooled balanced accuracy of M minus that of S, over the field-years of the seven
held-out years 2019, 2020, 2021, 2022, 2024, 2025 and 2026 (LOYO; the same rows for both models). The
interval is a paired cluster bootstrap that resamples the 17 cells with replacement. Each draw takes every
field-year of a drawn cell in all seven years and scores M and S on the same rows. 2,000 draws, seed 0,
90% percentile interval (5th and 95th percentiles). This is the procedure of `paired_bootstrap` in
`test_models/featureTests/harness.py`. Reported alongside, none of them decisive: the change in silage F1
with its interval, an exact McNemar test, the change in each held-out year with a cell bootstrap inside
that year, and the same paired comparison on split 3.

**Decision rule.**

> **ADOPT the multi-year training set** if the primary change in pooled LOYO balanced accuracy is **above 0**
> and its **90% interval lies entirely above 0** (lower bound > 0). Otherwise **KEEP 2023-only**, written
> `NO IMPROVEMENT SHOWN` when the interval contains 0 and `MULTI-YEAR WORSE` when its upper bound is below 0.
> Splits 2, 3 and 5 and Maryland are supporting evidence and cannot change the decision. Maryland
> (44 field-years, one farm) is never used to choose anything. "Adopt" is this evaluation's recommendation;
> nothing in this folder changes `kernelag/field_model.py` or the published metrics.

**Outputs** (`out/`): `loyo_by_year.csv`, `summary.json`, `coefficients_by_year.csv`, `maryland.csv`, and
`predictions_quebec.csv` (per-row Quebec calls; no per-field Maryland calls are written).
<!-- PREREGISTRATION:END -->

## Results

**Decision: KEEP 2023-only (NO IMPROVEMENT SHOWN).** On the seven seasons neither model saw, the
multi-year model's pooled balanced accuracy is 0.739, against 0.736 for the 2023-only model. The change is
+0.0025, and its 90% interval [−0.0043, +0.0100] contains 0. The rule asked for the whole interval above 0.

**How the run went.** The pre-registration was frozen at 2026-11-15T09:00:00Z
(`out/preregistration.sha256`, `183e74c7…`). Scoring ran at 09:00:45Z. `evaluate.py` had the same hash at
both times, so nothing changed between freezing and scoring, and there were no deviations from the
protocol. All three gates reproduced exactly:

- G1: 877/345/390/1516.
- G2: 10/5/2/27.
- G3: 10/4/2/28.

The roster held 22,026 Quebec field-years, as expected. 51 of them were not assessable and were scored as
grain. A full run takes about 40 s.

### The held-out-year test (split 1, primary)

M is fitted on the other seven years. S is fitted on 2023. Both score the same field-years. Counts are
TP/FP/FN/TN, with silage as the positive class. P/R is silage precision and recall. BA is balanced accuracy.
The interval in the last column resamples cells within that year.

| Held-out year | Field-years | M counts | M P/R | M BA | M F1 | S P/R | S BA | S F1 | M − S BA [90%] |
|---|---|---|---|---|---|---|---|---|---|
| 2019 | 2,566 | 555/294/475/1242 | 0.654/0.539 | 0.674 | 0.591 | 0.695/0.514 | 0.681 | 0.591 | −0.008 [−0.027, +0.014] |
| 2020 | 2,325 | 629/360/319/1017 | 0.636/0.664 | 0.701 | 0.649 | 0.565/0.704 | 0.665 | 0.627 | +0.036 [+0.005, +0.076] |
| 2021 | 2,598 | 892/611/170/925 | 0.593/0.840 | 0.721 | 0.696 | 0.736/0.791 | 0.797 | 0.762 | −0.076 [−0.102, −0.049] |
| 2022 | 2,839 | 488/153/569/1629 | 0.761/0.462 | 0.688 | 0.575 | 0.678/0.463 | 0.666 | 0.550 | +0.022 [+0.010, +0.032] |
| 2023 | 3,128 | 956/507/311/1354 | 0.653/0.755 | 0.741 | 0.700 | in-sample (0.721/0.704) | (0.759) | (0.712) | not compared |
| 2024 | 2,938 | 853/122/360/1603 | 0.875/0.703 | 0.816 | 0.780 | 0.865/0.691 | 0.807 | 0.768 | +0.009 [+0.002, +0.017] |
| 2025 | 2,826 | 996/395/310/1125 | 0.716/0.763 | 0.751 | 0.739 | 0.690/0.735 | 0.726 | 0.712 | +0.026 [+0.014, +0.038] |
| 2026 | 2,806 | 968/324/298/1216 | 0.749/0.765 | 0.777 | 0.757 | 0.753/0.744 | 0.772 | 0.749 | +0.005 [−0.009, +0.019] |
| **Pooled, 7 years without 2023** | 18,898 | 5381/2259/2501/8757 | 0.704/0.683 | **0.739** | 0.693 | 0.710/0.668 | **0.736** | 0.688 | **+0.0025 [−0.0043, +0.0100]** |
| Pooled, all 8 years | 22,026 | 6337/2766/2812/10111 | 0.696/0.693 | 0.739 | 0.694 | | | | |

Pooled over the seven years, silage F1 changes by +0.005 [−0.002, +0.013]. In an exact McNemar test, M alone
is right on 1,036 field-years and S alone on 1,028 (p = 0.88).

### What it means

- **The 2023-only model does carry over to other seasons, at a cost.** On seven unseen seasons it scores
  0.736 pooled. On 2023's own held-out areas (G1) it scores 0.753. So moving to a new year costs about 0.02
  balanced accuracy on average. In the worst years the cost is close to 0.09 (2020: 0.665, 2022: 0.666).
  The organizers' held-out-year test now exists, and this is its answer for the current model.
- **The year matters far more than the training set.** Each model's balanced accuracy moves by about 0.14
  between its best and worst year (S 0.665–0.807, M 0.674–0.816). Adding seven seasons of training data
  moves the pooled number by 0.0025.
- **Multi-year training does not win everywhere.** By year, it is ahead in 2020, 2022, 2024 and 2025 (each
  interval above 0) and clearly behind in 2021 (−0.076). In 2021 it calls 1,503 fields silage where farmers
  declared 1,062. The gains and the 2021 loss roughly cancel. These per-year intervals are supporting
  evidence, not corrected for multiplicity.
- **The fields that recur across years did not flatter the result.** Split 3 holds out the season and the
  area together, so no model has seen any field it scores. It gives the same answer: M 0.739, S 0.737,
  change +0.0019 [−0.0050, +0.0100], McNemar p = 0.91.
- **Holding out an area costs less than holding out a year.** With one cell held out and every year in
  training (split 2), M scores 0.745 pooled over the eight years, against 0.739 with one year held out. On
  2023's held-out cells, M scores 0.743 and the 2023-only model 0.753 (G1).

### Coefficient stability (split 5, `out/coefficients_by_year.csv`)

Weights are per standard deviation of each fit's own training rows.

| | intercept | max_drop | max_drop_rate | fade_days | green_at_cut | ndmi_before_cut | ndti_post |
|---|---|---|---|---|---|---|---|
| All 8 years | −0.045 | 0.507 | 0.283 | −0.405 | 0.063 | 0.515 | −0.784 |
| 2023 only (= S) | −0.006 | 0.907 | 0.671 | −0.173 | −0.044 | 0.380 | −0.298 |
| Single years: mean | −0.050 | 0.495 | 0.324 | −0.260 | 0.067 | 0.467 | −0.832 |
| Single years: SD | 0.102 | 0.272 | 0.264 | 0.199 | 0.329 | 0.404 | 0.380 |
| Single years: range | −0.218 to 0.091 | 0.206 to 0.907 | −0.081 to 0.671 | −0.562 to 0.017 | −0.425 to 0.693 | −0.087 to 1.050 | −1.320 to −0.242 |
| Years with the all-years sign | 5/8 | 8/8 | 6/8 | 7/8 | 4/8 | 7/8 | 8/8 |
| SD over the 8 LOYO fits | 0.010 | 0.053 | 0.043 | 0.051 | 0.029 | 0.045 | 0.067 |

- **A one-year fit depends heavily on its year.** Across the eight single-year fits, a weight's standard
  deviation runs from about half its mean (`max_drop`, `ndti_post`) to several times its mean
  (`green_at_cut`).
- **Two features keep their sign every year.** A big greenness drop always points to silage, and a high
  residue index after the cut always points to grain.
- **`green_at_cut` is unreliable.** Its sign flips in half the years.
- **2023 is an outlier.** It gives the largest weights of any year on drop size (0.907) and drop speed
  (0.671). Its residue weight (−0.298) is the second smallest, after 2021's (−0.242).
- **Multi-year fits are stable, but that did not help.** The fits barely change with the year left out
  (standard deviation 0.01–0.07). That stability did not turn into better calls on the held-out years.

### Maryland transfer (split 4, information only; `out/maryland.csv`)

| Fit | Training field-years (assessable) | TP/FP/FN/TN | Silage P/R | BA | Reproduces |
|---|---|---|---|---|---|
| Published, `quebec_maize_2023` (318 parcels) | 318 | 10/5/2/27 | 0.667/0.833 | 0.839 | yes (G2) |
| 2023 all-Quebec, `qcm_2023` (= S) | 3,128 | 10/4/2/28 | 0.714/0.833 | 0.854 | yes (G3) |
| Multi-year, all 8 qcm years | 21,975 | 10/1/2/31 | 0.909/0.833 | 0.901 | (new) |

- **Three Maryland field-years change call** between the 2023-only and the multi-year fit. All three go
  from a false silage call to a correct grain call.
- **The bootstrap gain is small in absolute terms.** Over the 34 Maryland fields, the gain is +0.047
  [+0.014, +0.096].
- **This does not change the decision.** Maryland is one farm with 44 field-years, and the team has
  already inspected it. The pre-registered rule never looks at it.
- **The two test sets disagree.** The Quebec held-out years show no gain while Maryland shows one. With
  only three changed calls, that is not evidence either way.

### Not pre-registered: the silage count by year

This is a descriptive reading of the confusion counts above. It was added after scoring and is not part
of the decision. For state acreage, what matters is how many fields a model calls silage, compared with how
many are silage. That ratio swings widely from year to year:

| Model | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Pooled (7 years) |
|---|---|---|---|---|---|---|---|---|---|
| M (year held out) | 0.82 | 1.04 | 1.42 | 0.61 | 1.15 | 0.80 | 1.07 | 1.02 | 0.97 |
| S (2023-only) | 0.74 | 1.25 | 1.08 | 0.68 | (0.98 in-sample) | 0.80 | 1.07 | 0.99 | 0.94 |

Each cell is the number of silage calls divided by the number of declared silage field-years.

- **In a single season, either model's silage count can be off by 25–40%.** Pooled over the years, both
  come close to the declared total.
- **Multi-year training does not narrow the swing.** It is wider in 2021 and 2022.
- **This is the year-to-year risk that matters for acreage.** Field-level balanced accuracy hides it,
  because within one year most of the errors go the same way.

### Limitations

- **The interval treats the years as fixed.** It resamples the 17 cells, and that many clusters can
  under-cover. The year-to-year variation, from −0.076 to +0.036 by year, is not in the interval at all.
  With only seven held-out years, a year-level interval would be much wider. A different set of seasons
  could tip the result either way.
- **More years also means more rows.** M trains on about six times as many rows as S (about 19,000 against
  3,128), so this test cannot tell "more seasons" apart from "more data".
- **Sources and years are mixed together.** S is trained on Planetary Computer data (2023). Six of its
  seven test years come from Earth Search; only 2022 comes from Planetary Computer, like 2023. Agreement between the two
  sources was not re-checked on these cells.
- **Labels.** They are crop-insurance declarations, not observed harvests, and silage on farms insured only
  for feed is missing. The 2025 and 2026 files are snapshots dated 2026-11-09 and may be revised. The 2026
  series ends 2026-11-12.
- **Quebec only.** The only check outside Quebec is Maryland's 44 field-years.
- **Line endings.** The files in `data/s2_series/qc_regions_2023/` were rewritten with CRLF line endings
  after `qcm_2023` was copied from them. File by file, the content is identical once the carriage returns
  are stripped, and G1 reproduces, so the 2023 rows are unaffected.

### Run

From the repository root:

```bash
.venv/Scripts/python.exe -I test_models/fieldMultiYear/evaluate.py prereg   # freezes once; refuses to overwrite a different hash
.venv/Scripts/python.exe -I test_models/fieldMultiYear/evaluate.py score    # about 40 s; checks the hash first
cd test_models/fieldMultiYear/out && sha256sum -c preregistration.sha256    # verifies the frozen copy
```

The run is deterministic: fixed folds, no random fitting, and bootstrap seed 0. `out/summary.json` holds the
gates, the primary comparison, the per-year and split-3 deltas, Maryland, the coefficient spread, the input
digests and the pre-registration check. `out/predictions_quebec.csv` holds every Quebec row's scores under
each split.
