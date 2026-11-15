# model

Corn acres harvested for silage and for grain, by state and for the US, from what is public by mid-November.
Exploratory code (numpy only); every number below is read from `out/`.

```
python3 scripts/pull_data.py quickstats            # once: the long Quick Stats history (needs NASS_QUICKSTATS_API_KEY)
python3 test_models/model/build_panel.py           # out/panel_nov.csv: one row per state and year, 2000 to 2026
python3 test_models/model/model.py                 # backtest, selection, out/forecast_2026.csv
python3 test_models/model/model.py --earliness     # after build_panel.py --asof aug, sep and oct
python3 test_models/model/model.py --score-2025    # the held-out year; refuses to run twice
```

## The deliverable: 2026 (`out/forecast_2026.csv`)

| | Acres | 80% range |
| --- | --- | --- |
| US corn for silage (48 states) | 6.35 M | 6.02 to 6.63 M |
| US corn for grain (41 states) | 88.51 M | 87.66 to 88.73 M |

The file has the same two numbers and ranges for every state. NASS's first 2026 silage acres come in January 2027.

## How accurate it is

"State error" is the share of acres put in the wrong state (sum of absolute state errors over the US total).
"US error" is the error of the US total.

Backtest, 2012 to 2024, each year predicted from earlier years only (`out/backtest_by_year.csv`):

| Target | Method | State error | US error (mean absolute) |
| --- | --- | --- | --- |
| Silage | same as last year | 15.8% | 5.8% |
| Silage | this model | 13.5% | 4.4% |
| Grain | NASS's November forecast | 1.6% | 0.6% |

Held-out year 2025, run once after everything was fixed (`out/score_2025.json`):

| Target | Method | State error | US error |
| --- | --- | --- | --- |
| Silage | same as last year | 14.0% | +0.3% |
| Silage | this model | 13.6% | +2.9% |
| Grain | same as last year | 9.2% | -8.7% |
| Grain | this model (NASS's November forecast) | 1.6% | -1.0% |

Against the 98% goal: grain meets it (99% for the US, 98.4% by state). Silage does not: about 96 to 97% for the US
and 86% by state. In 2025 the US silage total barely moved, so "same as last year" was nearly exact that year.

## The model

- **Silage.** One ridge regression pooled over all states, weighted by silage acres, on the change against last year.
  With no news it predicts last year's acres. Four inputs: how far last year stood above the state's previous three
  years (a high year falls back), the change in planted acres, the change in the share of planted acres NASS does not
  expect to be combined, and NASS's yield forecast against the state's last three years.
- **Grain.** NASS's own latest harvested-for-grain forecast (all 41 grain states in 2026); where NASS publishes none,
  planted acres times last year's grain share. Correcting NASS's average miss did not help.
- **Selection.** 26 silage candidates, the baselines included, all in `out/results.tsv`, kept or not. A richer candidate replaces a simpler one
  only if it wins by more than two standard errors of the year-by-year differences, on test years up to 2024.
- **Season stress** (drought, crop condition, rain, late planting, pasture, hay, milk): 14 of 16 weights have the sign
  written down beforehand (`out/weights.csv`), and with them the 2012 drought miss shrinks from -20% to -11% for the
  US. They do not lower the state error beyond noise, so the chosen model leaves them out.
- **Binary constraint.** Every field ends as grain or silage; grain plus silage is 97 to 98% of planted acres. Forcing
  the two numbers to add up to harvested corn moves the silage state error from 13.5% to 13.4%, inside the noise, and
  makes grain worse, so it is not applied.
- **Earliness** (`out/earliness.csv`). The silage number is as good on 15 August (13.7%) as on 15 November (13.5%).
  Grain improves from 3.0% in August to 1.6% in November as NASS updates its forecast.

## Limits

- 13 test years. The zero-trend rule and the "measured against the usual value" rule were chosen while looking at
  2012 to 2024; 2025 was never used to fit, tune or select.
- Quick Stats keeps NASS's in-season planted acres from 2018 only; for earlier years the final figure stands in
  (0.6% apart on average where both exist). On 2018 to 2024 alone the model scores 13.1% against 14.9%.
- The US totals are sums over the states NASS publishes: 48 for silage, 41 for grain.
- State silage acres move 10 to 20% a year in the large states, partly survey noise, which no model here explains.
- Not used: RMA (insured silage acres do not follow NASS's, and past loss files are today's vintage) and the
  satellite signal, which is still being pulled.

## Files in `out/`

`panel_<asof>.csv` inputs · `results.tsv` every candidate · `backtest_by_year.csv` · `weights.csv` · `metrics.json` ·
`earliness.csv` · `score_2025.json`, `score_2025_states.csv` · `forecast_2026.csv`
