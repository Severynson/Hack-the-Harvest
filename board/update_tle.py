"""Refresh board/tle.json (satellite orbits) from CelesTrak, so pass times on the map are exact.

    python board/update_tle.py

The hosted board runs this at startup. If CelesTrak can't be reached, the old file is kept.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SATS = {"Sentinel-2A": 40697, "Sentinel-2B": 42063, "Sentinel-2C": 60989, "Landsat 9": 49260, "Landsat 8": 39084}
OUT = Path(__file__).with_name("tle.json")


def main() -> bool:
    sats = []
    for name, norad in SATS.items():
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad}&FORMAT=TLE"
        req = urllib.request.Request(url, headers={"User-Agent": "kernel-board/1.0"})
        lines = [x.strip() for x in urllib.request.urlopen(req, timeout=20).read().decode().splitlines() if x.strip()]
        l1 = next(x for x in lines if x.startswith("1 "))
        l2 = next(x for x in lines if x.startswith("2 "))
        sats.append({"name": name, "l1": l1, "l2": l2})
    OUT.write_text(json.dumps({"source": f"CelesTrak GP data, fetched {datetime.now(UTC):%Y-%m-%d %H:%M} UTC", "sats": sats}, indent=1))
    return True


if __name__ == "__main__":
    try:
        main()
        print("tle.json updated")
    except Exception as error:  # noqa: BLE001
        print(f"tle.json not updated ({error}); keeping the old orbits")
