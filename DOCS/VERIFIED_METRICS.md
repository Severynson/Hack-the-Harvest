# Verified metrics and baselines

Generated 2026-11-15T08:15Z by `python -m kernelag.report`.

State WAPE = summed absolute state acreage error / summed actual acreage. National error is absolute total error.
Current-vintage inputs make these pseudo real-time replays, not archived-vintage operational tests.

| Target | Predictor | Years | Scope | States (min) | State WAPE % | US absolute error % | Source |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| silage | same_as_last_year | 2017–2024 | all_states | 48 | 14.53 | 4.08 | `data/models/state_model_backtest.csv` |
| silage | reversion_only | 2017–2024 | all_states | 48 | 13.12 | 3.90 | `data/models/state_model_backtest.csv` |
| silage | smoothed_chopping | 2017–2024 | all_states | 48 | 12.80 | 3.34 | `data/models/state_model_backtest.csv` |
| grain | same_as_last_year | 2017–2024 | all_states | 41 | 7.35 | 4.12 | `data/models/state_model_backtest.csv` |
| grain | nass_latest | 2017–2024 | all_states | 41 | 1.66 | 0.82 | `data/models/state_model_backtest.csv` |
| silage | model | 2025 | all_states | 48 | 13.12 | 2.19 | `data/models/state_score_2025.json` |
| silage | same_as_last_year | 2025 | all_states | 48 | 13.96 | 0.32 | `data/models/state_score_2025.json` |
| grain | model | 2025 | all_states | 41 | 1.64 | 0.99 | `data/models/state_score_2025.json` |
| grain | same_as_last_year | 2025 | all_states | 41 | 9.23 | 8.69 | `data/models/state_score_2025.json` |

The stored 2025 score remains separate; no tuning or overwrite in this delivery. Historical validation years also selected the feature set.
NASS-anchored grain is not an independent satellite forecast. Missing satellite rows mean uncomputed, not zero error.

## Maryland research-farm proxy labels

Field-years: 44; distinct field IDs: 34.
Intervals are 90% field-cluster bootstrap intervals; they do not measure national transfer uncertainty.

| Metric | Value | 90% interval |
| --- | ---: | --- |
| silage_precision | 0.667 | 0.462–0.857 |
| silage_recall | 0.833 | 0.636–1.000 |
| false_positive_rate | 0.156 | 0.059–0.280 |
| balanced_accuracy | 0.839 | 0.724–0.934 |
| silage_f1 | 0.741 | 0.556–0.875 |
| accuracy | 0.841 | 0.744–0.929 |

Confusion matrix: TP=10, FP=5, FN=2, TN=27.
Runtime: 0.0145 seconds/field; downloads excluded.
Source: `data/models/field_eval.json`. Binary benchmark rates preserve the historical grain-fallback convention only for scoring.
Operational decisions abstain on missing evidence or a fixed 40–60 uncalibrated score; see the `selective` block and field explorer.

## Prediction-date check

| Date | Field-years | Feature coverage | Not assessable | Uncertain | Binary recall | Operational coverage | Operational roster recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 09-01 | 44 | 0.909 | 4 | 6 | 0.167 | 0.773 | 0.083 |
| 10-01 | 44 | 1.000 | 0 | 0 | 0.917 | 1.000 | 0.917 |
| 11-01 | 44 | 1.000 | 0 | 6 | 0.833 | 0.864 | 0.833 |

Source: `data/models/field_earliness.csv`. Each series is truncated before feature extraction; early drops remain provisional.

## Intervals, bias and forecast

State/US forecast intervals: `data/models/state_forecast_2026.csv`; region/year signed bias: `data/models/state_model_bias.csv`.
Coverage: `data/models/state_model_metrics.json` and `state_score_2025.json`. Historical interval coverage uses leave-one-year-out calibration, including later years.
The offline report displays the forecast, intervals, coverage and bias. `data/models/metrics.json` includes source hashes for audit.

Other team experiments remain separate: `test_models/danielModel/` contains longer-history ridge/boosted models;
`autoresearch/RESULTS.md` documents the Caveman rules, repeated-development caveats and regional transfer checks.
Different histories and inspected cohorts must not be treated as interchangeable independent tests.
