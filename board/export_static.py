"""Bake the board into one self-contained HTML file that anyone can open: no server, no Python.

    python board/export_static.py                 # writes board/kernel_board_snapshot.html

The page is identical to the live board, with every /api/* answer embedded as of the moment you run
this. Rerun it (and republish the file) after new model results land.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from board import app

HERE = Path(__file__).resolve().parent


def main(out: Path = HERE / "kernel_board_snapshot.html") -> Path:
    snap = {
        "/api/board": app.build_board(),
        "/api/map": app.map_data(fresh=1),
        "/api/extras": app.extras_data(fresh=1),
        "/api/geo": json.loads((HERE / "us_states.json").read_text()),
        "/api/counties": json.loads((HERE / "us_counties.topo.json").read_text()),
        "/api/roads": json.loads((HERE / "roads.json").read_text()),
        "/api/tle": json.loads((HERE / "tle.json").read_text()),
    }
    taken = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    shim = ("<script>window.__SNAP=" + json.dumps(snap, separators=(",", ":")).replace("</", "<\\/") + ";"
            "window.__SNAP_TAKEN=" + json.dumps(taken) + ";"
            "(function(){const real=window.fetch.bind(window);window.fetch=function(u,o){const k=String(u).split('?')[0];"
            "if(k in window.__SNAP)return Promise.resolve(new Response(JSON.stringify(window.__SNAP[k]),"
            "{headers:{'Content-Type':'application/json'}}));return real(u,o)}})();</script>")
    page = (HERE / "page.html").read_text()
    map_js = (HERE / "map.js").read_text().replace("</script", "<\\/script")
    sat_js = (HERE / "satellite.min.js").read_text().replace("</script", "<\\/script")
    page = page.replace('<script src="/satellite.min.js"></script>', "<script>" + sat_js + "</script>")
    page = page.replace('<script src="/map.js"></script>', shim + "<script>" + map_js + "</script>")
    out.write_text(page)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB), data as of {taken}")
    return out


if __name__ == "__main__":
    main()
