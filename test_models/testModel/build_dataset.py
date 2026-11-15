#!/usr/bin/env python3
"""Build the tiny training tables from the fact-checked research notes.

No number is typed by hand: every value is parsed out of a markdown table in
DOCS/research/nass_ops.md (NASS Track Records and Crop Production figures,
thousand acres). Re-run after the notes change.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTE = ROOT / "DOCS" / "research" / "nass_ops.md"
OUT = Path(__file__).resolve().parent / "data"


def table_after(lines, heading):
    """Rows (lists of cell strings) of the first table under `heading`."""
    start = next(i for i, line in enumerate(lines) if line.startswith(heading))
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("|"):
            cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
            if not set(cells[0]) <= set("-: "):  # skip the |---|---| separator
                rows.append(cells)
        elif rows:
            break
    return rows


def num(cell):
    """'98,788' -> 98788; blanks, 'n/a' and prose -> ''."""
    cell = cell.replace(",", "")
    return int(cell) if re.fullmatch(r"\d+", cell) else ""


def write(name, header, rows):
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        csv.writer(f).writerows([header, *rows])
    print(f"{name}: {len(rows)} rows")


def main():
    lines = NOTE.read_text().splitlines()

    # US history 2000-2025: planted, silage, June/Nov forecasts and January estimate of grain acres.
    head, *body = table_after(lines, "## 9. History 2000 to 2025")
    keep = ["Year", "Planted", "Silage", "June grain fcst", "Nov grain fcst", "Jan grain"]
    us = [[num(r[head.index(k)]) for k in keep] for r in body]

    # 2026 so far: the June and November forecasts exist, the January truth does not.
    y2026 = {r[0]: r for r in table_after(lines, "## 8. The 2026 crop so far")}
    june, nov = y2026["Acreage, Jun 30, 2026"], y2026["Crop Production, Nov 10, 2026"]
    us.append([2026, num(nov[1]), "", num(june[2]), num(nov[2]), ""])
    write("us_corn_history.csv", ["year", "planted", "silage", "jun", "nov", "jan_grain"], us)

    # States: three years of silage, one year of planted and grain (January 2026 vintage).
    head, *body = table_after(lines, "## 10. States")
    keep = ["State", "Planted 2025", "Grain 2025", "Silage 2023", "Silage 2024", "Silage 2025"]
    states = [[r[0], *(num(r[head.index(k)]) for k in keep[1:])] for r in body if r[0] != "United States"]
    write("state_silage.csv", ["state", "planted_2025", "grain_2025", "silage_2023", "silage_2024", "silage_2025"], states)


if __name__ == "__main__":
    main()
