"""Kernel model board: every model in the repo on one page, ranked and compared.

Run from the repository root (no GPU, no language model, no network):
    python board/app.py                 # http://localhost:7870
    BOARD_PORT=9000 python board/app.py

The page rereads the model folders on every refresh (board/sources.py), so a model that finishes
running shows up without restarting anything. To add a model, see board/README.md.
"""

from __future__ import annotations

import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from board.sources import (
    FAMILIES,
    catalog,
    collect,
    field_models,
    state_history,
    state_predictions,
)

app = FastAPI(title="Kernel model board")


def records(frame):
    """DataFrame to JSON-safe records: NaN becomes null."""
    if frame is None or frame.empty:
        return []
    out = frame.astype(object).where(frame.notna(), None).to_dict(orient="records")
    for row in out:
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                row[key] = None
    return out


_CACHE: dict = {}


def cached(key: str, build, fresh: bool):
    """Build once, then reuse until Refresh (fresh=1). Reading every folder takes a moment on a laptop."""
    if fresh or key not in _CACHE:
        _CACHE[key] = build()
    return _CACHE[key]


@app.get("/api/board")
def board(fresh: int = 0):
    return cached("board", build_board, bool(fresh))


def build_board():
    data = collect()
    field, field_problems = field_models()
    return {
        "read_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "families": [*FAMILIES, "not recorded"],
        "models": list(data["models"].values()),
        "backtest": records(data["backtest"]),
        "forecast": records(data["forecast"]),
        "field": records(field),
        "catalog": catalog(),
        "problems": data["problems"] + field_problems,
    }


@app.get("/api/map")
def map_data(fresh: int = 0):
    """Inputs for the map tab: NASS history and context by state-year, and state-level backtest predictions."""
    def build():
        preds = state_predictions()
        preds[["actual", "predicted"]] = preds[["actual", "predicted"]].round(0)
        return {"history": records(state_history()), "state_predictions": records(preds)}
    return cached("map", build, bool(fresh))


@app.get("/api/extras")
def extras_data(fresh: int = 0):
    """County, money, harvest-timing and satellite layers for the map (board/extras.py)."""
    from board.extras import build
    return cached("extras", lambda: build(state_history()), bool(fresh))


@app.get("/api/counties")
def counties():
    return Response(Path(__file__).with_name("us_counties.topo.json").read_bytes(), media_type="application/json")


GEO = Path(__file__).with_name("us_states.json")


@app.get("/api/geo")
def geo():
    return Response(GEO.read_bytes(), media_type="application/json")


@app.get("/map.js")
def map_js():
    return Response(Path(__file__).with_name("map.js").read_bytes(), media_type="text/javascript")


PAGE = Path(__file__).with_name("page.html")


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE.read_text()


if __name__ == "__main__":
    print("Reading model folders...", flush=True)
    cached("board", build_board, True)
    map_data(fresh=1)
    extras_data(fresh=1)
    print("Ready: open http://localhost:" + os.environ.get("BOARD_PORT", "7870"), flush=True)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("BOARD_PORT", "7870")))
