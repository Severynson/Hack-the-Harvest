# Kernel: technical methodology

Kernel produces an early state acreage forecast and a separate satellite harvest-evidence test. The grain forecast is NASS-anchored. The silage forecast is historical/statistical. Until the state satellite sample is delivered and its ablation passes the existing selection rule, the headline acreage numbers must not be attributed to satellites.

## Data and scope

- State truth is NASS acreage totals, using the current revised vintage. The report uses the existing root pipeline; the longer-history experiments in `test_models/danielModel/` and `test_models/accuracy/` have different year ranges and remain separate.
- Field labels are research proxies: Quebec declared grain/forage parcels for fitting and public Maryland BARC research-farm labels for transfer evaluation. They are not a national organizer field truth set. Repeated field IDs are retained across years and kept together when resampling uncertainty.
- Sentinel-2 polygon medians provide NDVI, NDMI and NDTI with observation-quality flags. Cached series use real field boundaries; pixels are not independent labeled fields. County-level weather is displayed as context, not passed off as field measurements or used by the field classifier.
- Sources and hashes are recorded in `data/DATA_MANIFEST.tsv`, `data/models/metrics.json` and `data/models/field_explorer.json`. Inference uses no private data or synthetic observations.

## State acreage model and evaluation

The silage model predicts log year-on-year acreage change using a pooled acreage-weighted ridge model. Its simplest candidate is reversion after an unusually high or low prior-year acreage. Other candidates add available planted/grain acreage, season stress and, when available, satellite share changes. Missing predictors mean no new evidence, not observed zero crop area.

Each historical forecast fits only earlier outcomes. The existing selection rule chooses the smallest silage feature set within its fixed tolerance of the best historical state error; this rule is not rewritten to obtain a favorable score. The historical backtest years also select the feature set, so they are validation rather than a pristine final test. The stored separate 2025 score is not overwritten or repeatedly optimized.

Grain uses NASS's latest in-season harvested-area forecast where available. Missing forecasts fall back to available planted acres times the previous grain share, then the prior-year grain area. This improves against persistence primarily because it incorporates NASS information; it is not independent satellite accuracy.

For each year, state WAPE is `100 * sum_state(abs(predicted - actual)) / sum_state(actual)`. National absolute percentage error is `100 * abs(sum(predicted) - sum(actual)) / sum(actual)`. Opposing state errors can cancel nationally. Historical summary rows average annual errors; they are not a field-classification accuracy. The US forecasts sum the states with published coverage, leaving missing state values uncomputed rather than silently treating them as observed zeros.

State intervals are empirical log-error quantiles grouped by prior acreage size. US intervals use variation in historical total errors. Historical interval coverage uses leave-one-year-out calibration, including later years, and is explicitly retrospective. Regional/year signed bias is `(predicted - actual) / actual`, aggregated within the reported group. Current revised data and some historical substitute vintages prevent a claim of fully archived-vintage operational accuracy.

## Field classifier, uncertainty and earliness

The field classifier is a class-balanced logistic regression with training-only median imputation and standardization. Its six inputs describe the largest greenness drop, drop speed, green-to-bare fade time, greenness before the drop, canopy moisture before the drop and post-drop residue. Their standardized coefficients are shown as model weights, not causal contributions.

The inferred harvest interval spans the last observation before the largest drop and the first after it. It is a candidate interval, not confirmed harvest. Cloud gaps, senescence and management can produce similar evidence. Feature availability does not prove that a standing crop has been cut. Soil, radar and dairy proximity are not currently field-classifier inputs.

The 0–100 classifier output is an **uncalibrated model score**. Product decisions are `silage-like`, `grain-like`, `uncertain` or `not assessable`. The fixed 40–60 abstention band is an operational convention, not a confidence interval. Missing evidence abstains. No field score should be read as a calibrated probability.

For continuity, the binary benchmark keeps the team's original 0.5 threshold and grain fallback for unassessable rows **for scoring only**. `field_eval.json` separately exports operational abstention counts, decisive coverage, performance conditional on decisive fields, and silage recall against the complete roster. Conditional accuracy must always be shown with coverage. The field explorer never presents a missing-evidence fallback as an observed grain field.

Precision is `TP/(TP+FP)`; recall is `TP/(TP+FN)`; false-positive rate is `FP/(FP+TN)`; F1 is `2TP/(2TP+FP+FN)`; balanced accuracy is the mean of silage and grain recall. Ninety-percent percentile bootstrap intervals resample whole field IDs and retain their repeated years. They describe this small farm sample, not uncertainty in national transfer. Runtime is the median time for feature extraction plus prediction per field; imagery downloads are excluded.

Earliness removes every observation after the as-of date **before** extracting features, while preserving all labeled field-years in the denominator. September 1, October 1 and November 1 results are exported in `field_earliness.csv` and summarized in `DOCS/VERIFIED_METRICS.md`. Provisional early calls can change with later observations.

## Satellite-to-state pathway and current dependency

The implemented sampler draws fixed geographic areas with probability proportional to corn area. A field's contribution is acreage-weighted within its sample area, then areas are inverse-size weighted in the state ratio. Sample areas with incomplete year-series are excluded together across years. The aggregate reports all included area/field counts, assessable area counts, assessable-acre coverage, silage-like shares and a jackknife standard error conditional on assessable areas. Coverage retains wholly unassessable included areas in its denominator. The standard error reflects area variation, not classifier bias or national transfer uncertainty.

`kernelag.state_signal --asof nov` truncates imagery at November 15 even when the raw pull extends through November 30. Earlier months write distinct dated files; a November aggregate cannot enter a September replay. Duplicate sample field-years, unmapped states and duplicate state-years are rejected. Missing sample files or wholly unassessable samples produce an explicit UNCOMPUTED result, exit status 2 and no fabricated aggregate. An existing cache is preserved but explicitly not refreshed; inspect its provenance rather than assuming the failed run updated it. The offline presentation does not depend on this optional command succeeding.

The intended model tests share changes on the same sample areas against the existing forecast and persistence, with sampled-state scope reported separately. Stable bias may be reduced by changes; it is not guaranteed to cancel under changing prevalence or assessability. A fixed Quebec classifier trained on later labels and retrospective CDL crop masks make earlier-year tests retrospective signal ablations, not proof of an operational historical forecast.

At the latest documented sync, no state aggregate or raw state sample series was present in the shared repository. A handoff requests the Keeboh artifacts, cutoff/coverage metadata and provenance. Job completion cannot be asserted without a live handle or delivered files. The final demo proceeds with satellite acreage improvement explicitly uncomputed.

## Experiments and final decision

The fixed field XGBoost comparison uses identical Quebec spatial folds and no tuning on Maryland. Bounded state and national experiments fit strictly earlier years, select only on their development years, and keep later historical summaries separate. They log unsuccessful candidates, coverage and source/code hashes. These outcomes have been inspected during development and are not represented as new pristine holdouts.

No experiment currently clears the established promotion evidence while improving the relevant acreage claim. Retain the verified root forecast and the simpler field classifier. Additional feature counts, neural models and a chosen 2% target do not justify test-set tuning, scope changes or claims of national validation.

## Reproduce

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m kernelag.evaluate
.venv/bin/python -m kernelag.state_panel
.venv/bin/python -m kernelag.state_model --forecast 2026
.venv/bin/python -m kernelag.state_model --asof sep
.venv/bin/python -m kernelag.report
.venv/bin/python -m kernelag.explorer
PYTHONPATH=. .venv/bin/python test_models/accuracy/verify_delivery.py
```

Open `report/index.html` and `report/fields.html` directly from disk. Use `DOCS/presentation.md` for the five-minute demonstration and `DOCS/VERIFIED_METRICS.md` for the source-backed numerical table. Setup and optional live-pull requirements are in the root README.
