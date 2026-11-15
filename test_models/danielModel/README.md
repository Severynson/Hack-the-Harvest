# danielModel

Corn acres harvested for silage and for grain, by state and for the US, from what is public by mid-November.
Exploratory code; every number below is read from `out/`.

Two sets of models share one panel and one scoring harness:

- `train_gbt.py`: **trained gradient-boosted trees** for silage and for grain (numpy and scikit-learn).
- `model.py`: the simple reference, a ridge regression for silage and NASS's own forecast for grain (numpy only).

```
python3 scripts/pull_data.py quickstats                  # once: the long Quick Stats history (needs NASS_QUICKSTATS_API_KEY)
python3 test_models/danielModel/build_panel.py           # out/panel_nov.csv: one row per state and year, 2000 to 2026
python3 test_models/danielModel/model.py                 # reference: backtest, selection, out/forecast_2026.csv
python3 test_models/danielModel/train_gbt.py             # trained models: backtest, saved models, out/forecast_2026_gbt.csv
python3 test_models/danielModel/train_gbt.py --earliness # after build_panel.py --asof aug, sep and oct
```

`--score-2025` on either script writes the held-out comparison once and refuses to run again.

## The deliverable: 2026

| | Trained models (`out/forecast_2026_gbt.csv`) | Reference (`out/forecast_2026.csv`) |
| --- | --- | --- |
| US corn for silage (48 states) | 6.37 M (80% range 6.12 to 6.86 M) | 6.35 M (6.02 to 6.63 M) |
| US corn for grain (41 states) | 88.28 M (86.68 to 90.18 M) | 88.51 M (87.66 to 88.73 M) |

Both files hold the same numbers and ranges for every state. The trained grain number is the "independent" model,
which never sees NASS's grain forecast; the reference grain number is NASS's own November forecast.

## How accurate

"State error" is the share of acres put in the wrong state. "US error" is the error of the US total.

Held-out year 2025 (`out/score_2025.json`, `out/score_2025_gbt.json`). Each model was scored on it once, after its
settings were fixed; the trained models were scored second.

| Target | Method | State error | US error |
| --- | --- | --- | --- |
| Silage | same as last year | 14.0% | +0.3% |
| Silage | reference (ridge) | 13.6% | +2.9% |
| Silage | trained trees | 13.2% | +0.2% |
| Grain | NASS's November forecast | 1.6% | -1.0% |
| Grain | trained, starting from NASS's forecast | 1.2% | -0.5% |
| Grain | trained, without NASS's grain forecast | 1.1% | +0.1% |

Backtest, 2012 to 2024, each year predicted from earlier years only (`out/results.tsv`, `out/gbt_results.tsv`):

| Target | Method | State error | US error (mean absolute) |
| --- | --- | --- | --- |
| Silage | same as last year | 15.8% | 5.8% |
| Silage | reference (ridge) | 13.5% | 4.4% |
| Silage | trained trees | 13.3% | 3.7% |
| Grain | NASS's November forecast | 1.6% | 0.6% |
| Grain | trained, starting from NASS's forecast | 2.5% | 1.5% |
| Grain | trained, without NASS's grain forecast | 2.6% | 1.6% |

How to read the two tables together:

- 2025 is one year; the backtest is thirteen. The trained grain models beat NASS's own forecast in 2025 but are
  less accurate than it on average, so NASS's forecast stays the safer grain number.
- The trained silage model is better than "same as last year" in every table. Against the ridge it is ahead by
  0.2 points by state over thirteen years, which is inside the noise, and ahead on the US total (3.7% against 4.4%).
- Against the 98% goal: NASS's grain forecast meets it by state (98.4% on average). The trained grain models meet
  it in 2025 (98.9% by state) and average 97.4%. Silage reaches it for the US in 2025 only (99.8%; 96.3% on
  average); by state it stays near 87%.

## The models

- **Silage, trained trees.** Boosted trees (depth 2, 150 rounds) on the change in a state's silage acres against last
  year, weighted by acres. Inputs: how far last year stood above the state's norm, NASS's in-season planted acres and
  yield forecast, drought, crop and pasture condition, weather, hay, milk price and herd, plus where the state stands
  (silage share of corn, cows per corn acre). Each input can only push in the direction written down beforehand
  (`EXPECTED_SIGN` in `model.py`). `out/gbt_importance.csv` ranks the inputs: reversion first, then yield and planted acres.
- **Grain, trained without NASS's grain forecast.** Starts from planted acres times last year's grain share and learns
  the correction from drought, crop condition, weather and yield. Drought is its strongest input.
- **Grain, trained from NASS's forecast.** Starts from NASS's latest harvested-for-grain forecast and learns its miss.
- **Reference.** Silage: one pooled ridge regression on four changes. Grain: NASS's latest forecast as it stands.
- **Settings and selection.** Tree settings and the three saved models were fixed in the code before any scoring.
  The reference tried 26 silage candidates under a two-standard-error rule, on test years up to 2024 only.
- **Binary constraint.** Every field ends as grain or silage; grain plus silage is 97 to 98% of planted acres. Forcing
  the two numbers to add up moved the silage state error from 13.5% to 13.4%, inside the noise, so it is not applied.
- **Earliness** (`out/earliness.csv`, `out/gbt_earliness.csv`). Silage is as good on 15 August as on 15 November.
  NASS's own grain forecast is ahead of the trained grain models on every date from August to November.

## Limits

- 13 test years. The zero-trend rule and the "measured against the usual value" rule of the ridge were chosen while
  looking at 2012 to 2024; 2025 was never used to fit, tune or select.
- Quick Stats keeps NASS's in-season planted acres from 2018 only; for earlier years the final figure stands in
  (0.6% apart on average where both exist). On 2018 to 2024 alone the ridge scores 13.1% against 14.9%.
- The US totals are sums over the states NASS publishes: 48 for silage, 41 for grain.
- State silage acres move 10 to 20% a year in the large states, partly survey noise, which no model here explains.
- Not used: RMA (insured silage acres do not follow NASS's, and past loss files are today's vintage) and the
  satellite signal, which is still being pulled.

## Files in `out/`

`panel_<asof>.csv` inputs · reference: `results.tsv`, `backtest_by_year.csv`, `weights.csv`, `metrics.json`,
`earliness.csv`, `score_2025.json`, `score_2025_states.csv`, `forecast_2026.csv` · trained: `gbt_results.tsv`,
`gbt_backtest_by_year.csv`, `gbt_importance.csv`, `gbt_metrics.json`, `gbt_earliness.csv`, `score_2025_gbt.json`,
`forecast_2026_gbt.csv`, and the three saved models (`*.pkl`, scikit-learn)
