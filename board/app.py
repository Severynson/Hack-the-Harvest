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
from fastapi.responses import HTMLResponse

from board.sources import FAMILIES, collect, field_models

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


@app.get("/api/board")
def board():
    data = collect()
    field, field_problems = field_models()
    return {
        "read_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "families": [*FAMILIES, "not recorded"],
        "models": list(data["models"].values()),
        "backtest": records(data["backtest"]),
        "forecast": records(data["forecast"]),
        "field": records(field),
        "problems": data["problems"] + field_problems,
    }


PAGE = Path(__file__).with_name("page.html")


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE.read_text()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("BOARD_PORT", "7870")))
