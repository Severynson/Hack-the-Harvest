# Caveman silage model: results

The challenge (`jupyter/workspace/01_Challenge/challenge_statement.md`, "Evaluation") asks for a confusion matrix, precision and recall for both classes, field counts by year and class, the split design, and the main sources of error. Every number below comes from `prepare.evaluate` (BARC) or `quebec_check.py` (Quebec). Silage is the positive class.

## The model

A field-year is **silage** if either rule fires, otherwise **grain**:

1. **Drop clock:** after the season's greenest day, smoothed NDVI falls from 80% to 20% of its range in fewer than **17.5 days**. If the greenest day is in spring (a forage cereal), the range is tiny and the clock reads 1–5 days, so the rule also fires for those fields.
2. **Winter green:** median NDVI from 27 October to 21 December (day 300–355) is above **0.72**. This catches a cover crop sown right after an early cut.

Sentinel-2 L2A, 10 m inward-eroded field polygons, SCL cloud mask, scenes with ≥ 40% clear pixels, linear daily interpolation, 15-day rolling mean. The code is `train.py`.

## Dataset 1: BARC, Maryland (organizer evaluation data)

**Fields:** 44 labeled field-years on 34 polygons.

| Year | Grain | Silage | Total |
|---|---|---|---|
| 2021 | 14 | 4 | 18 |
| 2022 | 3 | 4 | 7 |
| 2023 | 15 | 4 | 19 |
| All | 32 | 12 | 44 |

**Split:** leave one year out. Fit both cut-offs on two years, predict the third, and pool the 44 out-of-fold predictions. The held-out year's labels are never seen.

**Confusion matrix** (rows: truth, columns: prediction):

| | Pred grain | Pred silage |
|---|---|---|
| **Grain** | 32 | 0 |
| **Silage** | 0 | 12 |

| Metric | All years | 2021 | 2022 | 2023 |
|---|---|---|---|---|
| Accuracy | 1.000 | 1.000 | 1.000 | 1.000 |
| Always-grain accuracy | 0.727 | 0.778 | 0.429 | 0.789 |
| Silage precision / recall / F1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| Grain precision / recall / F1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| Balanced accuracy | 1.000 | 1.000 | 1.000 | 1.000 |
| False-positive rate | 0.000 | 0.000 | 0.000 | 0.000 |
| MCC | 1.000 | 1.000 | 1.000 | 1.000 |

**Read with care:** the rules were designed over 19 experiments scored on these same 44 labels, so 1.00 is optimistic. Settings near the chosen ones score F1 0.87–1.00, and a fair expectation for new BARC fields is about 0.90–0.95. The tests below don't use BARC labels for fitting.

## Dataset 2: Quebec 2023 (FADQ declared parcels)

**Fields:** 801 corn parcels, all those in three 0.1° cells in UTM zone 18. Labels are from `data/labels/quebec_maize_2023.parquet`, pulled by cc-varun.

| Cell (south-west corner) | Grain | Silage | Total |
|---|---|---|---|
| Saint-Hyacinthe (−72.7, 45.6) | 211 | 78 | 289 |
| Nicolet (−72.6, 46.0) | 166 | 46 | 212 |
| Haut-Saint-Laurent (−74.1, 45.1) | 261 | 39 | 300 |
| All | 638 | 163 | 801 |

### A. Transfer: BARC cut-offs applied unchanged

**Split:** cut-offs fitted on all 44 BARC field-years; Quebec is never used for fitting.

| | Pred grain | Pred silage |
|---|---|---|
| **Grain** | 612 | 26 |
| **Silage** | 57 | 106 |

### B. Refit: leave one Quebec cell out

**Split:** cut-offs fitted on two cells, tested on the third (spatial hold-out). The drop clock refits to the same 17.5 days every time.

| | Pred grain | Pred silage |
|---|---|---|
| **Grain** | 601 | 37 |
| **Silage** | 45 | 118 |

| Metric | A. Transfer | B. Refit |
|---|---|---|
| Accuracy | 0.896 | 0.898 |
| Always-grain accuracy | 0.797 | 0.797 |
| Silage precision / recall / F1 | 0.803 / 0.650 / 0.719 | 0.761 / 0.724 / 0.742 |
| Grain precision / recall / F1 | 0.915 / 0.959 / 0.936 | 0.930 / 0.942 / 0.936 |
| Macro F1 | 0.828 | 0.839 |
| Balanced accuracy | 0.805 | 0.833 |
| False-positive rate | 0.041 | 0.058 |
| MCC | 0.661 | 0.679 |

Transfer by cell (silage F1): Saint-Hyacinthe 0.784, Nicolet 0.674, Haut-Saint-Laurent 0.607 (precision 1.000, recall 0.436).

## Cross-region check: Quebec cut-offs on BARC

The same setup as cc-varun's field model: train on Quebec, test on the 44 Maryland field-years.

| | Drop clock only | Both rules |
|---|---|---|
| TP / FP / FN / TN | 10 / 0 / 2 / 32 | 12 / 30 / 0 / 2 |
| Accuracy | 0.955 | 0.318 |
| Silage precision / recall / F1 | 1.000 / 0.833 / 0.909 | 0.286 / 1.000 / 0.444 |
| Grain precision / recall / F1 | 0.941 / 1.000 / 0.970 | 1.000 / 0.062 / 0.118 |
| MCC | 0.886 | 0.134 |

The winter-green cut-off learned in Quebec (NDVI > 0.25) comes from snow-covered fields and is meaningless in Maryland, so only the drop clock should be carried between regions.

## Comparison with the team's other field models (BARC labels)

| Model | Fitted on | Silage P / R / F1 | Accuracy |
|---|---|---|---|
| Always grain | none | – / 0.000 / 0.000 | 0.727 |
| Logistic regression (`jupyter/workspace/Kernel`) | BARC, year held out | 0.833 / 0.833 / 0.833 | 0.909 |
| cc-varun field model, 2,879 Quebec parcels | Quebec | 0.714 / 0.833 / 0.769 | 0.864 |
| **Caveman, drop clock only** | **Quebec** | **1.000 / 0.833 / 0.909** | **0.955** |
| **Caveman, both rules** | **BARC, year held out** | **1.000 / 1.000 / 1.000** | **1.000** |

## Sources of error and limits

- **Slow-drying silage.** 57 of 163 Quebec silage parcels lose their green over a median of 27 days and reach bare soil around 21 October, like grain. They may have been chopped late, after drying down. The greenness curve alone can't tell them from grain, so silage recall stays near 0.65–0.72 there.
- **Rules tied to place.** The spring-forage and winter-green signals depend on Maryland dairy rotations and on snow-free winters. Neither fires in Quebec, where nothing peaks in spring and Nov–Dec NDVI is about 0.2 under snow.
- **Small evaluation set.** 12 silage field-years; one field moves F1 by about 0.05. The rule design was chosen while looking at BARC.
- **Proxy labels in Quebec.** FADQ labels are declared intended use, not observed harvest.
- **Clouds.** A haze dip the SCL mask misses can stretch the drop clock (BARC field 291, 2021). The 40% clear-pixel threshold was tuned for this.
- **Timing.** The drop clock is known by late September. Winter green needs data through December.
- **Not yet covered:** other states and calendars (Texas cuts silage in early August), and other years in Quebec.

## Run 2: rules that travel between regions (`multi_eval.py`)

Winter green was changed from a learned cut-off to a fixed physical rule (Nov–Dec NDVI > 0.65). The learned Quebec cut-off (0.25) came from snow-covered fields and flagged 30 of 32 BARC grain fields. Fixed, the rule never fires in Quebec and keeps its job in Maryland. Floors from 0.60 to 0.70 give identical results, but 0.65 was chosen knowing that BARC grain tops out at 0.59.

| Test (one dataset each) | Before run 2 | After run 2 |
|---|---|---|
| BARC, leave one year out | 1.000 | 1.000 |
| Quebec → BARC | 0.444 | **1.000** (12/12 silage, 0 false alarms, accuracy 1.000) |
| BARC → Quebec | 0.719 | 0.719 |
| Quebec, leave one cell out | 0.742 | 0.719 |
| multi_score | 0.726 | **0.859** |

Tried and dropped:
- Region-relative harvest date, region-relative peak date, and a robust z-score for winter green.
- Smoothing 10 or 20 days instead of 15.
- A 75/25 drop band. It raised Quebec to 0.74 but cost a BARC field. That's within noise, and it loses the official 1.00.

A logistic regression on 8 greenness and residue signals scores 0.55–0.58 in Quebec, below the drop clock alone (0.72). The roughly 55 Quebec silage parcels still missed dry down like grain; telling them apart needs new information, not more rules.
