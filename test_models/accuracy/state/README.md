# Fixed state silage model comparison

Run from the repository root:

```sh
.venv/bin/python test_models/accuracy/state_candidates.py
```

Unchanged source, code and package versions reuse cached outputs; `--force` repeats the same fixed slate. No production files are changed. The source is `test_models/model/out/panel_nov.csv` (2000–2026); rows after 2024 are dropped before feature engineering. Every forecast year from 2012 through 2024 fits outcomes from strictly earlier years. Each year retains all 48 states. Exact calendar joins construct the lags; missing features use medians fitted to training rows only.

## Result and decision

Keep the existing `nodrift_nass` model. The development-selected LAD model lowers average state WAPE from 13.50% to 13.02% across 2012–2024, but its paired-year gain is only 0.47 percentage points with standard error 0.44. It fails the established improvement threshold of more than two standard errors (0.89 points). Its national total error also worsens. No candidate is promoted.

Values below are averages of yearly errors from `summary.csv`. State WAPE is `100 × sum_state(abs(predicted − actual)) / sum_state(actual)`. National absolute error takes the absolute value after summing state errors, allowing opposite state errors to cancel.

| Candidate | Development state WAPE, 2012–20 | Reserve state WAPE, 2021–24 | Full replay state WAPE, 2012–24 | Full replay national absolute error |
| --- | ---: | ---: | ---: | ---: |
| Same as last year | 16.83% | 13.61% | 15.84% | 5.76% |
| LAD core, development winner | 13.41% | 12.16% | 13.02% | 5.12% |
| Fixed three-model ensemble | 13.54% | 12.25% | 13.14% | 4.45% |
| Huber context | 13.45% | 13.51% | 13.47% | 4.46% |
| Shallow XGB, depth 2 | 14.55% | 12.72% | 13.98% | 5.22% |
| Shallow XGB, depth 3 | 14.21% | 12.37% | 13.64% | 4.81% |

The fixed ensemble gains 0.36 points against the incumbent with standard error 0.31; it also fails the two-standard-error rule. Its composition is fixed in code, not chosen after inspecting reserve performance. The slightly better reserve result of the simple reversion candidate does not justify changing the development selection.

## Frozen slate

Eleven candidates, with no additional search:

- Persistence.
- Reversion-only ridge, core ridge and context ridge; standardized features, penalty 100, no fitted intercept.
- Core LAD: median regression on relative acreage changes, alpha 0.001, weighted by previous silage acres. This directly targets absolute acreage error.
- Context Huber: epsilon 1.35, alpha 1, weighted by previous silage acres.
- Partial pooling: core ridge plus fixed geographic indicators and state residual corrections shrunk by `n / (n + 10)`.
- State trend: 75% reversion prediction and 25% median state change in the preceding five years; state trend capped at ±10%.
- Two XGB models, absolute-error objective, depths 2 and 3, 120 and 160 trees, learning rate 0.03, minimum child weight 30 and 40, lambda 20. Fixed seed, all training rows and columns, one CPU thread. Geographic region and prior acreage/share provide context.
- Equal-acreage-prediction ensemble of core ridge, core LAD and depth-2 XGB.

All fitted changes have the same broad fixed plausibility limit, −50% to +100%. Missing previous-year acreage falls back to the most recent earlier observation (or zero if none exists), with a flag; no state is removed to improve error. The current source requires no such fallback for the scored years.

Core predictors are reversion, change in planted acres, change in the non-grain share and the available grain-yield forecast against earlier yields. Context adds dairy demand, forage supply/prices, drought, crop condition, weather and planting/maturity. Current-year final silage acres, final grain acres and final yield are never used as predictors. Final planted acres enter only through the source panel's documented pre-2018 historical substitute for missing in-season vintages.

## Limits and artifacts

This is a retrospective replay. Historical outcomes have already been inspected by the team; the 2021–2024 reserve is not a pristine holdout. Reserve summaries remain separate, and each reserve year uses only earlier outcomes. No 2025 or later outcome enters fitting, scoring or selection. Existing published 2025 results are not touched.

The source uses revised historical data rather than archived publication snapshots. Before 2018, final planted acreage is a disclosed proxy for the absent in-season vintage. This experiment compares statistical methods on the existing panel; it cannot prove real-time historical accuracy. There is no satellite feature in this panel. Grain models are unchanged and no grain improvement is claimed.

- `predictions.csv`: all 48 states × 13 forecast years × 11 candidates, with actual, predicted and fallback flags.
- `by_year.csv`: state WAPE, signed/absolute national error and coverage for every candidate-year.
- `summary.csv`: separate development, reserve and complete-replay summaries.
- `incumbent_comparison.csv`: paired-year comparison against the stored incumbent and the established two-standard-error threshold. The stored incumbent errors are rounded to two decimals, which slightly limits comparison precision.
- `fit_audit.csv`: training-year bounds, row counts and elapsed time per candidate-year.
- `run.json`: exact slate, source/code/package hashes, development-only winner and caveats.

No result supports a near-perfect silage acreage claim. The best safe conclusion is that robust losses produce a small retrospective gain, with insufficient evidence to replace the established model.
