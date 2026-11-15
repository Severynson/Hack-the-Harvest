"""This season's state corn acres, read from NASS's monthly Crop Production reports (plain text).

The organizer file and the team's Quick Stats folder stop at 2025. NASS's 2026 state figures that
are public by mid-November sit in two text reports:
    crop0926.txt (11 Sep 2026)  area planted for all purposes, area harvested for grain
    crop1126.txt (10 Nov 2026)  area harvested for grain, forecast 1 November

Each report is downloaded once into ``data/nass/reports/`` and parsed from there.

Output rows match ``data/nass/corn_acres_state.csv``: year, state, series, period, acres.

Run: ``python -m kernelag.nass_reports``
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

from kernelag.paths import data_dir, record_in_manifest

REPORTS_URL = "https://release.nass.usda.gov/reports"
SEASON = 2026
# report file -> (table title, {column position among the row's numbers: (series, period)})
TABLES = {
    "crop0926.txt": ("Corn Area Planted for All Purposes and Harvested for Grain",
                     {1: ("planted", "sep"), 3: ("grain", "sep")}),
    "crop1126.txt": ("Corn for Grain Area Harvested, Yield, and Production",
                     {1: ("grain", "nov")}),
}
ROW = re.compile(r"^([A-Z][A-Za-z ]+?)\s*(?:\d/)?\s*\.*:(.*)$")


def report_text(name: str, folder: Path | None = None) -> str:
    """The report's text, downloaded on first use."""
    folder = folder or data_dir() / "nass" / "reports"
    path = folder / name
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        response = requests.get(f"{REPORTS_URL}/{name}", timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)
        record_in_manifest(path, f"{REPORTS_URL}/{name}")
    return path.read_text(encoding="latin-1")


def table_rows(text: str, title: str) -> dict[str, list[float]]:
    """State -> the numbers on its row (thousands), for the first data table with this title.

    "(NA)" and "(D)" cells become NaN. The table of contents repeats the title, so the table is
    the first title that is followed by a line of dashes within three lines.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines)
              if line.startswith(title) and any(set(later.strip()) == {"-"} for later in lines[i + 1:i + 4])]
    if not starts:
        raise ValueError(f"table not found: {title}")
    rows: dict[str, list[float]] = {}
    for line in lines[starts[0] + 4:]:
        match = ROW.match(line)
        if match:
            cells = match.group(2).split()
            rows[match.group(1).strip().upper()] = [
                float("nan") if cell.startswith("(") else float(cell.replace(",", "")) for cell in cells]
            if match.group(1).startswith("United States"):
                break
    return rows


def season_rows(folder: Path | None = None) -> pd.DataFrame:
    """This season's planted and grain acres per state, one row per series and report month."""
    records = []
    for name, (title, columns) in TABLES.items():
        for state, numbers in table_rows(report_text(name, folder), title).items():
            if state in ("UNITED STATES", "OTHER STATES"):   # totals and NASS's combined row
                continue
            for position, (series, period) in columns.items():
                if position < len(numbers) and numbers[position] == numbers[position]:
                    records.append({"year": SEASON, "state": state, "series": series, "period": period,
                                    "acres": int(round(numbers[position] * 1000))})
    return pd.DataFrame(records, columns=["year", "state", "series", "period", "acres"])


def main() -> None:
    rows = season_rows()
    print(rows.groupby(["series", "period"])["acres"].agg(["count", "sum"]).to_string())


if __name__ == "__main__":
    main()
