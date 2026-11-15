# Model board

One page that shows every model in the repo: a leaderboard by backtest error, side-by-side charts,
the 2026 forecasts and the satellite field models. It reads the files the models already wrote, so
nothing reruns. It needs no GPU, no language model and no network.

```bash
# from the repository root, with the project environment
uv pip install --python .venv/bin/python -r requirements.txt fastapi uvicorn   # once
.venv/bin/python board/app.py                                                  # http://localhost:7870
```

Press **Refresh** on the page after a model finishes a run.

## Tabs

- **Map** (opens first): a US map you can drag, zoom (scroll, double-click, + / −) and click.
  Pick a layer in "Show me"; a box under the map explains it in plain words. Layers: each model's
  2026 forecast, change vs last year, where the models disagree, NASS history (with Play), dairy
  cows and silage acres by county (USDA census 2017/2022), county rain, heat and first frost by year,
  state drought / crop condition / insurance losses, when silage gets chopped (2026 pace vs usual),
  corn crop value and price, where the satellite looks, and backtest error by state. Clicking a state zooms in and
  opens its history, every model's 2026 forecast and which models have called it best. KPI tiles
  on top: US totals, model count, Tier A/B progress, best backtest so far.
- **Tier A / B**: the planned candidates from the tier plan (`board/catalog.json`), grouped by tier
  and crop, under the "bars to clear" (NASS's November forecast, same as last year, our current
  silage model; read from `data/models/state_model_backtest.csv`). Each candidate shows "awaiting
  results" until it is published under its ID, then fills in: years, state and US error, the 2025
  held-out score, the selection rule against the tier's baseline (gain must exceed 2 × the standard
  error of the yearly differences), and its 2026 US total. Switch forecast date (Sep / Oct / Nov 15)
  and backtest years at the top.
- **Leaderboard**: every state-level model for silage or grain, ranked by mean state error over the
  years you pick. Filter by signal (weather, economy, satellite, NASS history), by folder or by name.
  Click a row for its inputs and per-year errors. Tick boxes to compare.
- **Compare**: state error and US error by year for up to 8 ticked models, with a hover readout.
- **2026 forecast**: each model's US total with its 80% range, and every state side by side.
- **Field models (satellite)**: field classifiers scored on labeled fields (precision, recall, F1),
  grouped by the field set they were scored on.
- **Add a model**: the two-line recipe below.

## Metrics

Same definitions as `kernelag.state_model.state_error`:

- **State error %** = 100 × sum(|predicted − actual|) / sum(actual) over the states in a year.
- **US error %** = 100 × (sum(predicted) − sum(actual)) / sum(actual). The leaderboard averages its
  size; the Compare chart shows the sign.

Folders that store raw predictions (`test_models/accuracy/state`) are scored with these formulas;
folders that store per-year errors are shown as stored. Each model's detail panel says which.

## Adding a model

At the end of your script:

```python
from board.publish import publish

publish("test_models/myModel/out",
        predictions=preds,   # columns: model, target, year, state, actual, predicted
        forecast=fc_2026,    # columns: model, target, state, predicted[, lo80, hi80]  ("US" row allowed)
        cards={"ridge_weather": {"signals": ["weather", "NASS history"],
                                 "features": ["reversion", "d_drought", "rain_anom"],
                                 "description": "Ridge on last year's change plus drought and rain."}})
```

For a Tier A/B candidate, use its ID as the model name (`model="A-S2"`, `target="silage"`) and add an
`asof` column (`sep`, `oct` or `nov`) to the predictions if you replay several forecast dates.

This writes `board_backtest.csv`, `board_forecast.csv` and `board_models.json` into that folder. Any
folder with those files is picked up automatically. One folder can hold many models (one `model` name
per row). A field classifier writes `board_field.csv` with `model, evaluated_on, n_fields,
silage_precision, silage_recall, silage_f1, accuracy`.

## Folders read today

`data/models` (kernel pipeline), `test_models/danielModel`, `test_models/accuracy/state`,
`test_models/accuracy/national` (US only), `test_models/testModel`, `test_models/codexFieldBaseline`,
`autoresearch/ledger`. Their loaders are in `board/sources.py`. If a folder changes format, its loader
reports the problem at the top of the page and the rest of the board still loads.

## Map data

State outlines: `board/us_states.json`, pre-projected Albers USA paths built from the npm package
`us-atlas@3` (`states-albers-10m.json`, US Census cartographic boundaries; ISC license, © Michael
Bostock). NASS history and season signals: `data/panel/state_year.csv` (`kernelag.state_panel`).
Everything is local, so the map works offline.

## Sharing it (no server needed)

    python board/export_static.py

writes `board/kernel_board_snapshot.html`: the whole board in one file, with the data as of that
moment. Open it in any browser or host it anywhere. Rerun after new results land.

County and harvest layers come from `board/extras.py` (Quick Stats exports, `data/weather/county_season`,
the BARC field file). County outlines: `board/us_counties.topo.json` from `us-atlas@3` (ISC).
