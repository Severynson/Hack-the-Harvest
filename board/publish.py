"""Put a model on the board: write its results where board/sources.py looks for them.

Call this at the end of your experiment script. It writes up to three small files into ``folder``:
    board_backtest.csv   per model, target and test year: state_error_pct, us_error_pct, n_states
    board_forecast.csv   per model, target and state: predicted, lo80, hi80 (a "US" row is allowed)
    board_models.json    per model: signals, features, method, description, owner

For the Tier A/B candidates, use the id from board/catalog.json as the model name (model="A-S2"), and
add an ``asof`` column (sep, oct or nov) if you replay several forecast dates.

Example (state-level predictions from a backtest loop):

    from board.publish import publish
    publish("test_models/myModel/out",
            predictions=preds,        # columns: model, target, year, state, actual, predicted
            forecast=fc_2026,         # columns: model, target, state, predicted[, lo80, hi80]
            cards={"ridge_weather": {"signals": ["weather", "NASS history"],
                                     "features": ["reversion", "d_drought", "rain_anom"],
                                     "description": "Ridge on last year's change plus drought and rain."}})

If you already have per-year errors, pass ``backtest=`` (model, target, year, state_error_pct,
us_error_pct[, n_states]) instead of ``predictions=``. Refresh the board page to see it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from board.sources import FAMILIES, REPO, errors_from_predictions

TARGETS = {"silage", "grain"}


def _check(frame: pd.DataFrame, needed: set[str], name: str) -> None:
    missing = needed - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")
    bad = set(frame["target"].unique()) - TARGETS
    if bad:
        raise ValueError(f"{name}: target must be 'silage' or 'grain', got {sorted(bad)}")


def publish(folder: str | Path, predictions: pd.DataFrame | None = None, backtest: pd.DataFrame | None = None,
            forecast: pd.DataFrame | None = None, cards: dict | None = None) -> Path:
    folder = Path(folder)
    folder = folder if folder.is_absolute() else REPO / folder
    folder.mkdir(parents=True, exist_ok=True)

    if predictions is not None:
        _check(predictions, {"model", "target", "year", "state", "actual", "predicted"}, "predictions")
        backtest = errors_from_predictions(predictions)
    if backtest is not None:
        _check(backtest, {"model", "target", "year", "us_error_pct"}, "backtest")
        if "asof" in backtest and not set(backtest["asof"].dropna()) <= {"sep", "oct", "nov"}:
            raise ValueError("asof must be sep, oct or nov")
        if "state_error_pct" not in backtest:
            backtest = backtest.assign(state_error_pct=float("nan"))
        backtest.to_csv(folder / "board_backtest.csv", index=False)
    if forecast is not None:
        _check(forecast, {"model", "target", "state", "predicted"}, "forecast")
        forecast = forecast.reindex(columns=["model", "target", "state", "predicted", "lo80", "hi80"])
        forecast.to_csv(folder / "board_forecast.csv", index=False)
    if cards:
        known = set(FAMILIES) | {"not recorded"}
        for name, card in cards.items():
            unknown = set(card.get("signals", [])) - known
            if unknown:
                raise ValueError(f"{name}: signals must be from {sorted(known)}, got {sorted(unknown)}")
        (folder / "board_models.json").write_text(json.dumps(cards, indent=1))
    if backtest is None and forecast is None:
        raise ValueError("nothing to publish: pass predictions=, backtest= or forecast=")
    return folder
