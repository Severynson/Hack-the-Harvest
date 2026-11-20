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
from fastapi.middleware.gzip import GZipMiddleware
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
# The map data is ~11 MB of JSON; gzip cuts it about 10x, which is most of the first-load wait.
app.add_middleware(GZipMiddleware, minimum_size=2048)


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


@app.get("/api/drought")
def drought_data(fresh: int = 0):
    """Per-state drought term of the headline silage model, for the what-if slider (board/drought.py)."""
    from board.drought import build
    return cached("drought", build, bool(fresh))


@app.get("/api/fields_md")
def fields_md():
    """USDA's labeled Maryland test fields with their greenness series and the caveman call (board/build_fields.py)."""
    return Response(Path(__file__).with_name("fields_md.json").read_bytes(), media_type="application/json")


@app.get("/api/cities")
def cities():
    return Response(Path(__file__).with_name("cities.json").read_bytes(), media_type="application/json")


@app.get("/api/team")
def team():
    return Response(Path(__file__).with_name("team.json").read_bytes(), media_type="application/json")


@app.get("/api/field")
def field_check(lon: float, lat: float, year: int, fips: str = ""):
    """Live: pull every Sentinel-2 picture of a small disc around (lon, lat) for one season and apply the caveman rule."""
    from fastapi.responses import JSONResponse
    if not (-125 < lon < -66 and 24 < lat < 50 and 2017 <= year <= datetime.now(UTC).year):
        return JSONResponse({"error": "Pick a spot in the lower 48 and a year from 2017 on."}, status_code=400)
    try:
        from board.fieldrule import classify_point
    except Exception as error:  # noqa: BLE001
        return JSONResponse({"error": f"Live lookup isn't installed on this server ({error})."}, status_code=503)
    try:
        return classify_point(lon, lat, year, fips or None)
    except ImportError as error:
        return JSONResponse({"error": f"Live lookup isn't installed on this server ({error.name or error})."}, status_code=503)
    except Exception as error:  # noqa: BLE001
        return JSONResponse({"error": f"Couldn't reach the satellite archive: {type(error).__name__}"}, status_code=502)


@app.get("/api/counties")
def counties():
    return Response(Path(__file__).with_name("us_counties.topo.json").read_bytes(), media_type="application/json")


GEO = Path(__file__).with_name("us_states.json")


@app.get("/api/geo")
def geo():
    return Response(GEO.read_bytes(), media_type="application/json")


@app.get("/api/roads")
def roads():
    return Response(Path(__file__).with_name("roads.json").read_bytes(), media_type="application/json")


@app.get("/api/trade")
def trade():
    return Response(Path(__file__).with_name("trade.json").read_bytes(), media_type="application/json")


@app.get("/api/tle")
def tle():
    return Response(Path(__file__).with_name("tle.json").read_bytes(), media_type="application/json")


@app.get("/satellite.min.js")
def satellite_js():
    return Response(Path(__file__).with_name("satellite.min.js").read_bytes(), media_type="text/javascript")


@app.get("/story.js")
def story_js():
    return Response(Path(__file__).with_name("story.js").read_bytes(), media_type="text/javascript")


@app.get("/map.js")
def map_js():
    return Response(Path(__file__).with_name("map.js").read_bytes(), media_type="text/javascript")


PAGE = Path(__file__).with_name("page.html")


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE.read_text()


def rebuild():
    cached("board", build_board, True)
    map_data(fresh=1)
    extras_data(fresh=1)
    try:
        drought_data(fresh=1)
    except Exception as error:  # noqa: BLE001 - the what-if slider is optional
        print(f"drought what-if unavailable: {error}", flush=True)


def auto_refresh(minutes: float, command: str) -> None:
    """Every few minutes run ``command`` (e.g. a git pull) and, if the repo changed, reread every model folder.

    Used by the hosted board (board/deploy) so new results appear without anyone pressing Refresh.
    """
    import subprocess
    import threading
    import time

    root = Path(__file__).resolve().parent.parent

    def head() -> str:
        """HEAD plus the board branch tip, so a change to either one triggers a reread."""
        refs = ["HEAD", "refs/remotes/origin/" + os.environ.get("BOARD_BRANCH", "board")]
        out = subprocess.run(["git", "rev-parse", *refs], cwd=root, capture_output=True, text=True, check=False)
        return out.stdout.strip()

    def loop() -> None:
        while True:
            time.sleep(minutes * 60)
            before = head()
            subprocess.run(command, shell=True, cwd=root, capture_output=True, check=False)
            if head() != before:
                try:
                    rebuild()
                    print(f"{datetime.now(UTC):%H:%M} UTC: new commits, board reread", flush=True)
                except Exception as error:  # noqa: BLE001 - keep serving the last good data
                    print(f"refresh failed: {error}", flush=True)

    threading.Thread(target=loop, daemon=True).start()


@app.get("/api/status")
def status():
    """When the data was last read, for the hosted board's 'updated' line."""
    return {"read_at": (_CACHE.get("board") or {}).get("read_at")}


def refresh_orbits_soon() -> None:
    """Fresh satellite orbits in the background, so the pass times on the map are exact."""
    import threading

    def run() -> None:
        try:
            from board.update_tle import main
            main()
            print("satellite orbits refreshed", flush=True)
        except Exception as error:  # noqa: BLE001
            print(f"satellite orbits not refreshed ({error}); using board/tle.json as is", flush=True)
    threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    refresh_orbits_soon()
    print("Reading model folders...", flush=True)
    rebuild()
    if os.environ.get("BOARD_AUTOPULL"):
        auto_refresh(float(os.environ["BOARD_AUTOPULL"]), os.environ.get("BOARD_PULL_CMD", "git pull --ff-only"))
    print("Ready: open http://localhost:" + os.environ.get("BOARD_PORT", "7870"), flush=True)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("BOARD_PORT", "7870")))
