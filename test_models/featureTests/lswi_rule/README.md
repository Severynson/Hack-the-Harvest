# September moisture rule (Lin et al. 2025) as a benchmark and a feature group

Group key `lswi`. Field-feature contract outputs are in `out/features.csv` and `out/meta.json`.

## What

The one published silage-versus-grain maize classifier, run exactly as published on our
Sentinel-2 series:

- **Rule column `lswi_rule_silage`:** 1 (silage) when the September LSWI is <= 0.15, otherwise 0 (grain).
  It is NaN when the field-year has no clear September look.
- **Pre-registered model features (2):** `lswi_sep_median` and `lswi_sep_min`. Both were fixed in
  `build.py` before any label was read.

LSWI = (NIR - SWIR1) / (NIR + SWIR1). That is the repo's `ndmi` column, (B8A - B11) / (B8A + B11), with
the reflectance offset already removed by `kernelag/s2_series.py`.

## Why

- `DOCS/research/precedent.md` 3.1 says Lin et al. 2025 (*Agronomy* 15(6):1438, "TempDiff-SMID", Hohhot,
  Inner Mongolia) is the only peer-reviewed study whose goal is silage-versus-grain separation.
- `DOCS/research/optical_harvest.md` (section 3 and 12.5) names this rule as "the published baseline to
  beat" and asks for it as a baseline row in the metrics table.

### The rule as published

Source: precedent.md 3.1 and recipe A, checked in `precedent.verification.md` and
`optical_harvest.verification.md`.

- **Preprocessing:** Sentinel-2 from 1 April to 31 October with clouds masked. NDVI and LSWI are
  rebuilt at 15-day steps with a Whittaker smoother. The smoothing parameter is not reported.
- **Condition 1:** NDVI_May <= 0.2, NDVI_July >= 0.2 and elevation < 1200 m.
- **Condition 2:** LSWI_July >= 0.16.
- **Condition 3:** LSWI_September <= 0.15. The paper's reason: "after silage maize is harvested ... the
  cultivated land becomes bare land with lower moisture content".
- **Classes:** silage = C1 and C2 and C3. Grain = C1 and C2 but not C3. Anything else is non-maize.
- **Direction:** a *low* September LSWI means silage.
- **For known maize:** C1 and C2 only recognise maize. On fields already known to be maize, only C3
  decides silage versus grain (precedent.md recipe A: "the CDL corn mask replaces C1 and C2, and only C3
  remains").

### Which September statistic

The paper does not say which 15-day step stands for "September", and it does not give the smoothing
parameter (precedent.md recipe A, "Unknowns"). Our literal port, fixed before evaluation:

- **Statistic:** the median of the field's clear looks dated 1 to 30 September. A clear look has
  `valid_frac >= 0.5`.
- **Threshold:** 0.15, with the published `<=` direction.
- **Why the median:** it is the closest unsmoothed stand-in for a monthly value of a smoothed series. It
  is also the form written in optical_harvest.md 12.5 ("median NDMI in the silage window <= 0.15").
- **Sensitivity only:** other readings of "September" are also reported, all at the same 0.15 threshold:
  `lswi_rule_sep_min` (any clear look), `lswi_rule_sep_last` (the latest clear look) and
  `lswi_rule_sep_late` (median from 16 to 30 September, the guess in precedent.md recipe A). They were
  looked at after the rule was registered, so none of them replaces it.

### Fact-check corrections that matter here

- **The 93% is in-sample.** The 2023 OA of 0.9291 reproduces as 354/381, so the tree was scored on every
  sample point after "iterative threshold optimization".
- **"Beat a random forest" is not established.** The forest was scored on a 30% hold-out (104/115), not
  on the same points (optical_harvest.verification.md, item 1; precedent.verification.md, item 1).
  Some labels came from visual reading of the same Sentinel-2 signal.
- **Hohhot's harvest gap is several weeks, not 5-15 days.** Silage there was "fully harvested by
  10 September 2023" and grain is cut from late September to early October. The 5-15 days is the
  growth-cycle difference (precedent.verification.md, item 2).
- **Thresholds were re-tuned by hand for other years.** The re-tuned values for 2022 and 2021 were not
  published, and OA fell to 0.86-0.88.
- **The LSWI importance ranking does not isolate this split.** It comes from a three-class forest
  (silage, grain, non-maize), so it does not show that LSWI separates silage from grain
  (optical_harvest.verification.md, item 2).
- **One harvest calendar fails across regions.** The USDA reps said so (`DOCS/research/usda_reps_qa.md`:
  "One harvest calendar for every region: Texas harvests in early August, Nebraska in October"). Point 7
  of the same notes: prefer within-field change and growing-degree-day timing over absolute thresholds.

## Data

| Dataset | Labels | Series | Field-years built | With a clear September look | Median clear September looks |
|---|---|---|---|---|---|
| quebec_maize_2023 (cell 79_515) | `data/labels/quebec_maize_2023.parquet` | `data/s2_series/quebec_maize_2023/` | 318 | 318 | 2 |
| qc_regions_2023 (16 cells) | `data/labels/qc_regions_2023.parquet` | `data/s2_series/qc_regions_2023/` | 2,810 | 2,810 | 6 |
| barc_2021_2023 (Maryland, TEST ONLY) | not read by this script | `data/s2_series/barc_2021_2023/` | 107 | 107 | 3 |

- **Maryland:** `build.py` builds Maryland features for the harness but never opens Maryland labels. No
  Maryland number is reported here.
- **Labelled parcels without a series:** 79 of the 2,889 qc_regions parcels have no series. They are left
  out of the rule check; the joined table has 2,810 rows.

## How to run

From the repository root:

```bash
PYTHONPATH=. .venv/Scripts/python.exe test_models/featureTests/lswi_rule/build.py            # all three datasets
PYTHONPATH=. .venv/Scripts/python.exe test_models/featureTests/lswi_rule/build.py --datasets qc_regions_2023
.venv/Scripts/python.exe -m pytest -q test_models/featureTests/lswi_rule/test_build.py
```

- **Re-runs:** the script can be re-run and rebuilds only the datasets named with `--datasets`. Rows of
  other datasets stay in `features.csv`.
- **Missing inputs:** a dataset without series prints `UNCOMPUTED <dataset>: <reason>`, and the reason is
  written to `meta.json`.
- **Outputs (`out/`):**
  - `features.csv`: one row per field-year that has a series.
  - `meta.json`: the contract fields plus the rule definition.
  - `rule_eval_quebec.csv`: the rule and its readings scored on Quebec labels, per cell and pooled, with
    each cell's median latitude and its clear September days.
  - `class_summary_quebec.csv`: September and July LSWI quartiles by class, and pass rates of Lin's maize
    conditions.
  - `calendar_check_quebec.csv`: when Quebec fields were cut, and how dry they were right after.

## Results (Quebec only; no fitting; threshold 0.15 as published)

### Published rule `lswi_rule_silage` (silage is the positive class)

| Scope | Covered / labelled | Silage share | TP | FP | FN | TN | Silage precision | Silage recall | Grain recall | Balanced accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| quebec_maize_2023 (79_515) | 318 / 318 | 0.434 | 10 | 10 | 128 | 170 | 0.500 | 0.072 | 0.944 | 0.508 |
| qc_regions_2023 (16 cells) | 2,810 / 2,810 | 0.402 | 182 | 222 | 947 | 1,459 | 0.450 | 0.161 | 0.868 | 0.515 |
| All Quebec (17 cells) | 3,128 / 3,128 | 0.405 | 192 | 232 | 1,075 | 1,629 | 0.453 | 0.152 | 0.875 | 0.513 |

**The published rule is close to chance in Quebec.**

- Balanced accuracy is 0.51.
- Silage precision is 0.45 against a silage share of 0.405.
- The rule finds about one silage field in seven.

Coverage is 100%, so scoring uncovered rows as grain changes nothing. Lin et al. report silage F1 0.93
in-sample in Hohhot.

### Same threshold, other readings of "September" (sensitivity only, not promoted)

| All Quebec | TP | FP | FN | TN | Silage precision | Silage recall | Balanced accuracy |
|---|---|---|---|---|---|---|---|
| median of clear September looks (**registered**) | 192 | 232 | 1,075 | 1,629 | 0.453 | 0.152 | 0.513 |
| minimum (any clear look <= 0.15) | 544 | 589 | 723 | 1,272 | 0.480 | 0.429 | 0.556 |
| latest clear September look | 528 | 577 | 739 | 1,284 | 0.478 | 0.417 | 0.553 |
| median from 16 to 30 September (97% coverage) | 305 | 420 | 916 | 1,395 | 0.421 | 0.250 | 0.509 |

No reading reaches a balanced accuracy of 0.6. The best ones raise silage recall only by raising false
positives at about the same rate.

### Class comparison of the September values (Quebec labels only)

| All Quebec | n | `lswi_sep_median` q25 / q50 / q75 | `lswi_sep_min` q25 / q50 / q75 | Share with median <= 0.15 |
|---|---|---|---|---|
| grain | 1,861 | 0.233 / 0.335 / 0.390 | 0.108 / 0.237 / 0.331 | 0.125 |
| silage | 1,267 | 0.259 / 0.361 / 0.419 | -0.021 / 0.221 / 0.361 | 0.152 |

- **The median points the wrong way.** In Quebec, silage fields are slightly *wetter* than grain fields
  over September as a whole.
- **The minimum is weak.** Its lower tail is lower for silage (q25 -0.02 against 0.11), so it carries some
  separation, but the middle and upper quartiles overlap.

### Why: the calendar premise does not hold in Quebec

| All Quebec | Cut day of year q25 / q50 / q75 | Cut by 10 Sep | Cut by 30 Sep | Cut in September | LSWI on the first look after a September cut (median) | Share of those <= 0.15 |
|---|---|---|---|---|---|---|
| grain | 267 / 275 / 290 | 3.4% | 44.8% | 809 | 0.182 | 39.9% |
| silage | 270 / 272 / 282 | 1.9% | 54.5% | 679 | 0.020 | 72.0% |

The cut date is `kernelag.features` `cut_doy`: the first clear look after the biggest NDVI drop. It
trails the real cut by up to the gap between clear looks. For grain, the biggest drop can be senescence
rather than the combine.

- **Cut timing:** in Hohhot silage was cut by 10 September. In Quebec only 1.9% of silage fields were cut
  by then, and 45% had no detected cut by 30 September.
- **The threshold itself fits bare ground:** when a silage field *was* cut in September, its first look
  after the cut read <= 0.15 72% of the time, against 40% for grain.
- **Conclusion:** the moisture state behind the threshold looks right for bare post-silage ground. The
  fixed calendar window is what fails. This is the regional-calendar failure the reps warned about, and
  the reason optical_harvest.md 12.5 asks for the window to be placed by growing-degree-days or relative
  to the county median.

### The calendar caveat inside one province

Per cell results are in `out/rule_eval_quebec.csv` (rule `lswi_rule_silage`).

- **Range across cells:** silage recall runs from 0.00 to 0.55 across the 17 cells, which span about
  45.2 to 47.5 N.
- **Northern cells call almost nothing silage:** in 81_518, 81_519 and 88_527 (46.7 to 47.5 N), silage
  recall is 0.01 to 0.06 and grain recall is 1.00. Their median cut is about day 282 to 292, which is
  9 to 19 October.
- **Where the rule calls silage, it also calls grain:** in 70_509 and 70_511 (about 46.0 to 46.1 N),
  silage recall reaches 0.44 to 0.55, but grain recall falls to 0.65 and 0.48. Grain there is also cut or
  dry in September, which is precedent.md's "early is not silage" trap.
- **Latitude does not explain it alone:** the southernmost cell, 74_500 (45.15 N), makes no silage call at
  all. Its fields had clear September looks on two days only (4 and 24 September).
- **Few clear looks:** cell 79_515 (the field_model training cell) also had only three clear September
  days (4, 24 and 29 September).

### Lin's maize-recognition conditions on fields known to be maize (descriptive)

| All Quebec | C1 pass (May NDVI <= 0.2, July NDVI >= 0.2; no elevation test) | C2 pass (July LSWI >= 0.16) |
|---|---|---|
| grain | 0.599 | 0.821 |
| silage | 0.489 | 0.767 |

At C1 the full published tree would call 40% of Quebec's declared grain maize and 51% of its declared
silage maize "non-maize". Its fixed thresholds do not port, before the silage/grain split is even reached. Our series start on 1 May, while
the paper's May value comes from a series smoothed from 1 April, so C1 here is approximate.

### Maryland and the model features

- **Maryland:** the harness scores the rule column and the two pre-registered features on Maryland,
  together with the logistic model. This script reports no Maryland number.
- **Expectation:** the features are September calendar values. That breaks the field model's design
  choice of calendar-free evidence (`kernelag/field_model.py` docstring), so transfer from Quebec to
  Maryland is not expected to help. This is a prior, not a measured result.

## Limitations

- **Not smoothed:** no Whittaker smoothing and no 15-day compositing. The median of clear looks stands in
  for the smoothed September value. The paper's smoothing parameter and exact September step are
  unpublished, so a truly literal port is impossible.
- **Possible band difference:** our LSWI uses B8A, the narrow NIR band at 20 m. Lin et al. most likely used
  B8. This is inferred: the paper names only "NIR" and "SWIR1". Absolute values near the 0.15 threshold
  may shift slightly between the two. Not quantified.
- **Field medians, not points:** values are field medians over a 20 m inner buffer. Lin et al. used 10 m
  sample points.
- **Few clear looks in some cells:** cells such as 74_500 and 79_515 have only 2 or 3 clear September
  days. The September statistic then rests on two or three scenes.
- **Approximate cut dates:** the calendar check uses `kernelag.features` `cut_doy`, whose resolution is
  the gap between clear looks. It is descriptive and not a ground-truth harvest date.
- **One season:** Quebec labels cover 2023 only, so cross-year behaviour (where Lin et al. lost 5 to 7
  points even after re-tuning) is not tested.
- **Silage share:** Quebec samples are about 40% silage, against about 6% of US corn acres. At a 6% share
  the same error rates would give a far lower silage precision.
- **Shared code:** `build_features` lives in `kernelag/features.py`, which other agents may edit. If its
  logic changes, `calendar_check_quebec.csv` changes with it. The rule and the features do not depend on
  it.
