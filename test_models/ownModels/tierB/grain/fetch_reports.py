"""NASS state corn PLANTED acres as published in season (June Acreage; Aug-Nov Crop Production), 2012-2026.

Why: Quick Stats keeps NASS's in-season state planted figures only from 2018 (``YEAR - JUN ACREAGE`` and later
periods); for 2012-2017 it holds only March intentions and the final. The original reports are archived on USDA
ESMIS (https://esmis.nal.usda.gov/publication/acreage and .../crop-production). This script downloads them once
into ``data/reports/`` next to this file and parses ONLY the corn PLANTED column of the state tables:

    June Acreage            "Corn Area Planted for All Purposes and Harvested for Grain - States and United States"
                            columns: planted t-1, planted t, harvested t-1, harvested t  -> planted t only
    Crop Production (Aug-Nov) "Selected Crops Area Planted [and Harvested] - States and United States: t"
                            [Includes updates to planted ... area previously published]; corn group, Planted column
                            only; or (later years) the same "Corn Area Planted for All Purposes ..." table

The harvested-for-grain columns sit in the same tables. They are NASS's grain forecast (forbidden as a Tier B
input) and are never read: the parser cuts out the planted column by its character span.

Output: data/nass_planted_inseason.csv (year, state, period, release_date, planted, report, table)
        data/reports_manifest.csv      (file, url, sha256, bytes, release_date, kind)

Run from the repository root:  .venv/Scripts/python.exe test_models/ownModels/tierB/grain/fetch_reports.py
(downloads are skipped for files already present; ``--parse-only`` never touches the network)
"""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPORTS = DATA / "reports"
ESMIS = "https://esmis.nal.usda.gov"
LISTINGS = {"acreage": (f"{ESMIS}/publication/acreage", range(0, 3)),
            "crop-production": (f"{ESMIS}/publication/crop-production", range(0, 18))}
FIRST_YEAR, LAST_YEAR = 2012, 2026
CROP_MONTHS = {8: "aug", 9: "sep", 10: "oct", 11: "nov"}
MONTH_NAMES = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                           "september", "october", "november", "december"], start=1)}
RELEASED = re.compile(r"Released\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})")
TITLE = re.compile(r"^(Corn Area Planted for All Purpose|Selected Crops Area Planted)")
TOC_ENTRY = re.compile(r"\.{4,}\s*\d+\s*$")
NOT_STATES = {"UNITED STATES", "OTHER STATES", "US"}


# --- downloading ------------------------------------------------------------------------------------------------

def _get(url: str) -> bytes:
    import requests
    response = requests.get(url, timeout=90, headers={"User-Agent": "research-client"})
    response.raise_for_status()
    return response.content


def listing_links() -> dict[str, list[str]]:
    """Relative links to every .txt release file on the ESMIS listing pages."""
    found: dict[str, list[str]] = {}
    for kind, (base, pages) in LISTINGS.items():
        links: list[str] = []
        for page in pages:
            html = _get(f"{base}?page={page}").decode("utf-8", "replace")
            links += re.findall(r'href="(/sites/default/release-files/[^"]+\.txt)"', html)
        found[kind] = sorted(set(links))
    return found


def wanted(kind: str, name: str) -> bool:
    """June Acreage and Aug-Nov Crop Production files of FIRST_YEAR..LAST_YEAR, by file name."""
    if kind == "acreage":
        m = re.match(r"(?:Acre-06-\d\d-(\d{4})|acrg06(\d\d))\.txt$", name)
        if not m:
            return False
        year = int(m.group(1)) if m.group(1) else 2000 + int(m.group(2))
        return FIRST_YEAR <= year <= LAST_YEAR
    m = re.match(r"(?:CropProd-(\d\d)-\d\d-(\d{4})\.txt|crop(\d\d)(\d\d)(?:_\d+)?\.txt)$", name)
    if not m:
        return False
    month, year = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), 2000 + int(m.group(4)))
    return month in CROP_MONTHS and FIRST_YEAR <= year <= LAST_YEAR


def download_all() -> list[dict]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for kind, links in listing_links().items():
        for link in links:
            name = link.rsplit("/", 1)[-1]
            if not wanted(kind, name):
                continue
            path = REPORTS / name
            if not path.exists():
                path.write_bytes(_get(ESMIS + link))
            rows.append({"file": name, "url": ESMIS + link, "kind": kind})
    return rows


# --- parsing ----------------------------------------------------------------------------------------------------

def release_date(text: str) -> date | None:
    m = RELEASED.search(text[:4000])
    if not m or m.group(1).lower() not in MONTH_NAMES:
        return None
    return date(int(m.group(3)), MONTH_NAMES[m.group(1).lower()], int(m.group(2)))


def _is_rule(line: str) -> bool:
    s = line.strip()
    return len(s) > 20 and set(s) == {"-"}


def _colons(line: str) -> list[int]:
    return [i for i, ch in enumerate(line) if ch == ":"]


def _number(cell: str) -> float:
    cell = cell.strip().lstrip("<>*")     # a few 2014 cells carry a revision marker before the number
    if not cell or cell.startswith("("):
        return float("nan")
    try:
        return float(cell.replace(",", ""))
    except ValueError:
        return float("nan")


def _state(label: str) -> str:
    label = re.sub(r"\d+/", "", label)
    return re.sub(r"\s+", " ", label.replace(".", " ")).strip().upper()


def planted_span(header: list[str], year: int) -> tuple[int, int, int] | None:
    """(state colon, start, end): where the state label ends and the character span of the corn-planted-in-``year``
    column, from the header block.

    Layout A (June Acreage and some later Crop Production): groups "Area planted for all purposes" and "Area
    harvested for grain", sub-columns by year -> the planted group's sub-column labelled ``year``.
    Layout B (Selected Crops): groups by crop, sub-columns "Planted" / "Harvested" -> Corn group, "Planted".
    """
    text_lines = [line for line in header if ":" in line and not _is_rule(line)]
    if len(text_lines) < 2:
        return None
    sub = text_lines[-1]
    sub_colons = _colons(sub)
    for group_line in text_lines[:-1]:
        g = _colons(group_line)
        for a, b in zip(g, g[1:] + [max(len(group_line), len(sub)) + 1]):
            label = group_line[a + 1:b].strip().lower()
            if label == "corn" or label.startswith("area planted"):
                inner = [c for c in sub_colons if a <= c <= b]
                bounds = inner + ([b] if not inner or inner[-1] != b else [])
                for s, e in zip(bounds, bounds[1:]):
                    cell = re.sub(r"\d+/", "", sub[s + 1:e]).strip().lower()
                    if (label == "corn" and cell == "planted") or (label != "corn" and cell == str(year)):
                        return sub_colons[0], s, e
    return None


def parse_report(text: str, year: int) -> tuple[pd.DataFrame, list[str]]:
    """Every state corn-planted value for ``year`` found in one report; and the table titles used."""
    lines = text.splitlines()
    rows, titles = [], []
    i = 0
    while i < len(lines):
        if not TITLE.match(lines[i]) or TOC_ENTRY.search(lines[i]):
            i += 1
            continue
        rules = [j for j in range(i + 1, min(i + 8, len(lines))) if _is_rule(lines[j])]
        if not rules or "States and United States" not in " ".join(x.strip() for x in lines[i:rules[0]]):
            i += 1                          # a table-of-contents entry, or a "Selected States" table
            continue
        start = rules[0]
        end = next((j for j in range(start + 1, min(start + 12, len(lines))) if _is_rule(lines[j])), None)
        if end is None:
            i += 1
            continue
        span = planted_span(lines[start + 1:end], year)
        if span is None:
            i = end
            continue
        k, s, e = span
        titles.append(lines[i].strip())
        j = end + 1
        while j < len(lines) and not _is_rule(lines[j]):
            line = lines[j]
            if len(line) > k and line[k] == ":" and line[:k].strip():
                state = _state(line[:k])
                value = _number(line[s + 1:e])
                if state not in NOT_STATES and value == value:
                    rows.append({"state": state, "planted": value * 1000})
                if state == "UNITED STATES":
                    break
            j += 1
        i = j
    table = pd.DataFrame(rows, columns=["state", "planted"])
    return table.drop_duplicates("state", keep="first"), titles


def parse_all(manifest: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, item in manifest.iterrows():
        text = (REPORTS / item["file"]).read_text(encoding="latin-1")
        released = release_date(text)
        if released is None or not (FIRST_YEAR <= released.year <= LAST_YEAR):
            continue
        period = "jun" if item["kind"] == "acreage" else CROP_MONTHS.get(released.month)
        if period is None or (item["kind"] == "acreage" and released.month != 6):
            continue
        table, titles = parse_report(text, released.year)
        if table.empty:
            continue
        out.append(table.assign(year=released.year, period=period, release_date=released.isoformat(),
                                report=item["file"], table=" | ".join(sorted(set(titles)))))
    cols = ["year", "state", "period", "release_date", "planted", "report", "table"]
    if not out:
        return pd.DataFrame(columns=cols)
    result = pd.concat(out, ignore_index=True)[cols]
    # Two files for one release month (a corrected re-issue): keep the later release.
    result = result.sort_values(["year", "period", "state", "release_date"])
    return result.drop_duplicates(["year", "period", "state"], keep="last").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--parse-only", action="store_true", help="use the files already in data/reports/")
    args = parser.parse_args()
    manifest_path = DATA / "reports_manifest.csv"
    if args.parse_only:
        manifest = pd.read_csv(manifest_path)
    else:
        manifest = pd.DataFrame(download_all())
    manifest = manifest.drop_duplicates("file").reset_index(drop=True)
    shas, sizes, released = [], [], []
    for name in manifest["file"]:
        raw = (REPORTS / name).read_bytes()
        shas.append(hashlib.sha256(raw).hexdigest())
        sizes.append(len(raw))
        rd = release_date(raw.decode("latin-1"))
        released.append(rd.isoformat() if rd else "")
    manifest = manifest.assign(sha256=shas, bytes=sizes, release_date=released)
    manifest = manifest.sort_values(["kind", "release_date", "file"])
    manifest[["file", "url", "kind", "release_date", "sha256", "bytes"]].to_csv(manifest_path, index=False,
                                                                                lineterminator="\n")
    planted = parse_all(manifest)
    planted.to_csv(DATA / "nass_planted_inseason.csv", index=False, lineterminator="\n")
    print(f"{len(manifest)} report files; parsed {len(planted)} state planted values "
          f"({datetime.now():%Y-%m-%d %H:%M})")
    print(planted.groupby(["year", "period"]).agg(n=("state", "size"), total=("planted", "sum")).to_string())


if __name__ == "__main__":
    main()
