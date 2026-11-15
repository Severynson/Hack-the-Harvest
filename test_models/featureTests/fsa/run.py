"""FSA intended-use silage acres as a state silage signal, scored against the team's incumbent and persistence.

Question: in states where FSA's "intended use = Silage" corn acres cover most of NASS's silage acres, does moving
last year's NASS silage by the FSA year-on-year ratio beat the team's state model? The research note found FSA
useful only where coverage is 75% or more (DOCS/research/gap_fsa_ratio_baseline_2026.md, sections 0 and 3.3).

Method (fixed before any FSA number was scored; README.md repeats it):
    pred(s, t) = S(t-1) * clip(F_nov(t) / F_final(t-1), 0.5, 2.0)     in gated states, then
                 min(pred, R(t))   where R(t) = NASS planted minus harvested-for-grain, as public by mid-November
    every other state keeps the base prediction (the incumbent; variant B: persistence)
    S = NASS silage acres as the incumbent uses them; F = FSA corn planted acres with intended use Silage
    (Forage before crop year 2019); F_final(t-1) under 500 acres falls back to a ratio of 1.
Gates:
    realtime    prior-year coverage F_final(t-1) / S(t-1) >= 0.75 (nothing from year t or later)   [primary]
    fixed_list  NY, ID, CA, AZ, NM, VT, MT (the research list, chosen on 2019-2025 coverage: mild look-ahead)
Scored on the incumbent's backtest years 2017-2024, all 48 states: state WAPE (acre-weighted) per year, its mean
over years, and the US-total error. Paired 90% bootstrap intervals on the change in WAPE, resampling years and,
separately, states. 2025 and 2026 are information only; nothing is fitted, tuned or selected here at all.

Inputs:
    data/fsa/ or data/fsa/raw/          FSA Crop Acreage Data zips or xlsx, downloaded by hand in a browser
                                        (FSA_FILES lists them; the FSA site closes scripted connections)
    kernelag.state_model, state_panel   incumbent "reversion_only", persistence, truth and the residual R
    test_models/danielModel/            second incumbent "nodrift_nass" (model.py, out/panel_nov.csv)
    data/models/state_score_2025.csv    the frozen 2025 incumbent forecast (2025 information row only)
Outputs (test_models/featureTests/fsa/out/):
    results.json          status, incumbent identification, scores, bootstrap intervals, research numbers
    predictions.csv       every scored state-year prediction
    fsa_state_silage.csv  FSA silage-intended acres by state, crop year and vintage (only when files exist)

Nothing is downloaded and no file outside out/ is written.

Run: .venv/Scripts/python.exe test_models/featureTests/fsa/run.py [--boot 10000]
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import re
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / "out"
# data/raw/fsa/ is git-ignored: the full set of FSA zips is about 1.8 GB, too big for the repository.
FSA_DIRS = [REPO / "data" / "fsa", REPO / "data" / "fsa" / "raw", REPO / "data" / "raw" / "fsa"]
DANIEL_MODEL = REPO / "test_models" / "danielModel" / "model.py"
SCORE_2025 = REPO / "data" / "models" / "state_score_2025.csv"
FORECAST_2026 = REPO / "data" / "models" / "state_forecast_2026.csv"
FSA_SITE = "https://www.fsa.usda.gov"
FSA_PAGE = (FSA_SITE + "/tools/informational/freedom-information-act-foia/electronic-reading-room/"
            "frequently-requested/crop-acreage-data")

BACKTEST_YEARS = list(range(2017, 2025))     # the incumbent's backtest years (data/models/state_model_metrics.json)
RELABEL_YEAR = 2019                          # FSA "Forage" became "Silage" (FSA Notice CP-749)
COVERAGE_MIN = 0.75
RATIO_CLIP = (0.5, 2.0)
MIN_PRIOR_FSA_ACRES = 500
FIXED_LIST = ["NEW YORK", "IDAHO", "CALIFORNIA", "ARIZONA", "NEW MEXICO", "VERMONT", "MONTANA"]
SILAGE_USES = {"silage", "forage", "sg", "fg"}   # words in the files; FSA codes kept in case a vintage uses them
BOOT_DRAWS = 10000
SEED = 20261114
CI_LEVELS = (0.05, 0.95)

# The three ordinary GETs made on 2026-11-14 with the default `requests` client (no custom headers), recorded
# here so results.json carries them. The FSA site never answered; no other client or header was tried.
PROBE_LOG = [
    {"url": FSA_PAGE, "result": "ReadTimeout after 40 s"},
    {"url": FSA_SITE + "/sites/default/files/documents/2016_fsa_acres_jan2017_edr32.zip",
     "result": "ReadTimeout after 40 s"},
    {"url": FSA_SITE + "/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip", "result": "ReadTimeout after 40 s"},
]

# Every workbook the method needs, as listed on FSA_PAGE (link text and link read from a saved copy of the page,
# data/fsa/index.html). "final" = the January file after the crop year; "nov" = the in-season file public by
# mid-November; "dec" = 1 Dec 2025, the substitute for the October and November 2025 files that FSA never
# released (government shutdown). "research_file" is the direct file the research note downloaded, where it
# gives one; newer entries on the page lead to a landing page first.
FSA_FILES = [
    {"year": 2016, "vintage": "final", "label": "2016 acreage data as of January 1, 2017",
     "link": "/sites/default/files/documents/2016_fsa_acres_jan2017_edr32.zip"},
    {"year": 2017, "vintage": "final", "label": "2017 acreage data as of January 16, 2018",
     "link": "/sites/default/files/documents/2017_fsa_acres_jan2018.zip"},
    {"year": 2018, "vintage": "final", "label": "2018 acreage data as of January 28, 2019",
     "link": "/sites/default/files/documents/2018_fsa_acres_Jan-2019-kgcr.zip"},
    {"year": 2019, "vintage": "final", "label": "2019 acreage data as of January 1, 2020",
     "link": "/sites/default/files/documents/2019_fsa_acres_jan2020_stlno1.zip"},
    {"year": 2020, "vintage": "final", "label": "2020 acreage data as of January 5, 2021",
     "link": "/sites/default/files/documents/2020_fsa_acres_as_of_010521-BbO60I.zip"},
    {"year": 2021, "vintage": "final", "label": "2021 acreage data as of January 3, 2022",
     "link": "/sites/default/files/documents/2021_fsa_acres_web_as_of_010322.zip"},
    {"year": 2022, "vintage": "final", "label": "2022 acreage data as of January 3, 2023",
     "link": "/sites/default/files/documents/vc8Jn1nR42.zip"},
    {"year": 2023, "vintage": "final", "label": "2023 acreage data as of January 2, 2024",
     "link": "/sites/default/files/documents/3QPVeIgPizDl.zip"},
    {"year": 2024, "vintage": "final", "label": "2024 acreage data as of January 2, 2025",
     "link": "/documents/FnNg0ix5oKdi", "research_file": "/sites/default/files/2025-01/FnNg0ix5oKdi.zip"},
    {"year": 2025, "vintage": "final", "label": "2025 acreage data as of January 12, 2026 (data as of 5 Jan 2026)",
     "link": "/documents/doisjehvqfz9zip", "research_file": "/sites/default/files/2026-01/DoISjehvQfz9.ZIP"},
    {"year": 2017, "vintage": "nov", "label": "2017 acreage data as of November 1, 2017",
     "link": "/sites/default/files/documents/2017_fsa_acres_nov2017gru14.zip"},
    {"year": 2018, "vintage": "nov", "label": "2018 acreage data as of November 1, 2018",
     "link": "/sites/default/files/documents/2018_fsa_acres_Nov_2018_grufs%21.zip"},
    {"year": 2019, "vintage": "nov", "label": "2019 acreage data as of November 1, 2019",
     "link": "/sites/default/files/documents/2019_fsa_acres_nov_2019_ohnot.ZIP"},
    {"year": 2020, "vintage": "nov", "label": "2020 acreage data as of November 10, 2020",
     "link": "/sites/default/files/documents/2020_FSA_Acres_web_as_of_110220-vkfNG6.zip"},
    {"year": 2021, "vintage": "nov", "label": "2021 acreage data as of November 9, 2021",
     "link": "/sites/default/files/documents/2021_fsa_acres_web_as_of_110921.zip"},
    {"year": 2022, "vintage": "nov", "label": "2022 acreage data as of November 1, 2022",
     "link": "/sites/default/files/documents/NEBP1OybFfUr83utFEB2.zip"},
    {"year": 2023, "vintage": "nov", "label": "2023 acreage data as of November 1, 2023",
     "link": "/sites/default/files/documents/XoNdctf9jmvWFGY.zip"},
    {"year": 2024, "vintage": "nov", "label": "2024 acreage data as of November 1, 2024",
     "link": "/documents/kmwmjuc631qpebuukewh"},
    {"year": 2025, "vintage": "dec", "label": "2025 acreage data as of December 9, 2025 (data as of 1 Dec 2025)",
     "link": "/documents/uhya3k5akxvm", "research_file": "/sites/default/files/2025-12/UhYA3k5AKxVM.zip"},
    {"year": 2026, "vintage": "nov", "label": "2026 acreage data as of November 10, 2026 (data as of 5 Nov 2026)",
     "link": "/documents/wrcdk92kc1587mahom35213",
     "research_file": "/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip"},
]

# National corn silage-intended acres per file from the research note's table 2.1, used only to check that this
# parser reads the same numbers once the files are local (a mismatch above 0.1% is flagged, never corrected).
RESEARCH_US_TOTALS = {
    (2016, "final"): 2660075, (2017, "final"): 2672847, (2018, "final"): 2789769, (2019, "final"): 2578805,
    (2020, "final"): 2831376, (2021, "final"): 2778667, (2022, "final"): 2642901, (2023, "final"): 2842347,
    (2024, "final"): 2785954, (2025, "final"): 2919232,
    (2017, "nov"): 2667894, (2018, "nov"): 2782295, (2019, "nov"): 2547231, (2020, "nov"): 2758863,
    (2021, "nov"): 2776606, (2022, "nov"): 2638919, (2023, "nov"): 2835792, (2024, "nov"): 2780809,
    (2025, "dec"): 2885058, (2026, "nov"): 2885863,
}

STATE_CODES = {
    "AL": "ALABAMA", "AK": "ALASKA", "AZ": "ARIZONA", "AR": "ARKANSAS", "CA": "CALIFORNIA", "CO": "COLORADO",
    "CT": "CONNECTICUT", "DE": "DELAWARE", "FL": "FLORIDA", "GA": "GEORGIA", "HI": "HAWAII", "ID": "IDAHO",
    "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA", "KS": "KANSAS", "KY": "KENTUCKY", "LA": "LOUISIANA",
    "ME": "MAINE", "MD": "MARYLAND", "MA": "MASSACHUSETTS", "MI": "MICHIGAN", "MN": "MINNESOTA",
    "MS": "MISSISSIPPI", "MO": "MISSOURI", "MT": "MONTANA", "NE": "NEBRASKA", "NV": "NEVADA",
    "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY", "NM": "NEW MEXICO", "NY": "NEW YORK", "NC": "NORTH CAROLINA",
    "ND": "NORTH DAKOTA", "OH": "OHIO", "OK": "OKLAHOMA", "OR": "OREGON", "PA": "PENNSYLVANIA",
    "RI": "RHODE ISLAND", "SC": "SOUTH CAROLINA", "SD": "SOUTH DAKOTA", "TN": "TENNESSEE", "TX": "TEXAS",
    "UT": "UTAH", "VT": "VERMONT", "VA": "VIRGINIA", "WA": "WASHINGTON", "WV": "WEST VIRGINIA",
    "WI": "WISCONSIN", "WY": "WYOMING",
}

# Transcribed from DOCS/research/gap_fsa_ratio_baseline_2026.md; NOT recomputed here (no FSA file is local).
# Its truth is NASS's first January estimate; the incumbent scores against the revised final, so the
# persistence numbers differ from ours even in shared years.
RESEARCH_REPORTED = {
    "source": "DOCS/research/gap_fsa_ratio_baseline_2026.md, not recomputed",
    "truth": "NASS first January estimate (Crop Production Annual Summary), 48 states",
    "coverage_class_75_plus_2019_2025": {
        "section": "3.3", "state_years": 83, "wape_persistence_pct": 10.5, "wape_fsa_ratio_pct": 9.4,
        "wape_fsa_additive_pct": 9.3, "pearson_r": 0.49, "same_direction": "37 of 49",
        "note": "83 state-years is more than 8 states x 7 years, so the class looks assigned per state-year "
                "(section 6 also names Georgia, Florida and Oregon at about 100%); the note does not say so",
    },
    "named_high_coverage_states": {
        "section_0": ["NEW YORK", "IDAHO", "CALIFORNIA", "ARIZONA", "NEW MEXICO", "VERMONT", "MONTANA"],
        "section_2_3_adds": ["WASHINGTON"],
    },
    "per_year_wape_pct_section_3_1": {
        "columns": ["persistence", "fsa_ratio_nov_file_all_states", "fsa_ratio_only_where_coverage_50_plus"],
        "2017": [13.2, 14.8, 12.2], "2018": [19.6, 24.8, 19.0], "2019": [16.5, 27.2, 19.3],
        "2020": [12.8, 17.8, 10.8], "2021": [16.0, 17.7, 16.9], "2022": [13.6, 14.9, 12.1],
        "2023": [13.4, 15.5, 12.4], "2024": [11.8, 14.4, 12.2], "2025 (1 Dec file)": [15.1, 15.4, 14.8],
        "2017-2025 pooled": [14.6, 18.0, 14.4], "2019-2025 pooled": [14.2, 17.6, 14.1],
    },
    "best_public_baseline_loyo_2020_2025_pct_section_4_3": {
        "persistence": 13.8, "residual_cap": 13.1, "fsa_additive_fitted_pass_through": 13.2,
        "fsa_pass_through_plus_residual_cap": 12.9,
        "fsa_pass_through_where_coverage_50_plus_plus_residual_cap": 12.8,
        "oracle_final_residual_ratio": 8.9,
        "note": "additive form S(t-1) + b * dF with b fitted leave-one-year-out (0.72-0.95), gate coverage >= 50%, "
                "cap on every state; not the ratio rule with a 0.75 gate pre-registered here",
    },
    "benchmark_rows_section_6": {
        "columns": ["2024", "2025", "2019-2025"],
        "same_as_last_year": [11.8, 15.1, 14.2], "fsa_per_state_ratio": [14.4, 15.4, 17.6],
        "best_public_baseline": [11.6, 15.3, "12.8 (2020-2025, leave-one-year-out)"],
        "oracle_final_residual_ratio": [5.3, 6.6, 8.9],
    },
    "residual_cap_section_4_2": "min(S(t-1), R(t)): WAPE 13.7% vs 14.2% (2019-2025), better in 5 of 7 years",
    "fsa_2026": "5 Nov 2026 file: corn Silage 2,885,863 acres, -1.1% vs 2025 final 2,919,232 (section 2.1); "
                "best public baseline implies a 2026 US total of 6,143 thousand acres (section 5.3)",
}


# --- FSA files -----------------------------------------------------------------------------------

def _stem(name: str) -> str:
    """Lower-case file name without extension or a browser's " (1)" suffix, for matching downloads."""
    stem = re.sub(r"\.(zip|xlsx)$", "", unquote(name).lower())
    return re.sub(r"\s*\(\d+\)$", "", stem)


def match_tokens(entry: dict) -> set[str]:
    """Names a download of this entry may carry: the link's file name, the landing-page id, or fsa_<year>_<vintage>."""
    tokens = {f"fsa_{entry['year']}_{entry['vintage']}"}
    for link in (entry["link"], entry.get("research_file", "")):
        if link:
            stem = _stem(link.rsplit("/", 1)[-1])
            tokens.add(stem)
            if stem.endswith("zip"):            # landing-page ids such as "doisjehvqfz9zip" keep the extension
                tokens.add(stem[:-3])
    return tokens


def find_fsa_files(folders: list[Path] | None = None) -> dict[tuple[int, str], Path]:
    """(crop year, vintage) -> local file, for every FSA_FILES entry found in the FSA folders."""
    local = {}
    for folder in folders if folders is not None else FSA_DIRS:
        if folder.is_dir():
            for path in sorted(folder.iterdir()):
                if path.is_file() and path.suffix.lower() in (".zip", ".xlsx"):
                    local.setdefault(_stem(path.name), path)
    found = {}
    for entry in FSA_FILES:
        hit = next((local[t] for t in sorted(match_tokens(entry)) if t in local), None)
        if hit is not None:
            found[(entry["year"], entry["vintage"])] = hit
    return found


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _column_index(ref: str) -> int:
    """Zero-based column of a cell reference such as "AB12"."""
    index = 0
    for letter in re.match(r"[A-Z]+", ref).group(0):
        index = index * 26 + ord(letter) - 64
    return index - 1


def open_workbook(path: Path) -> zipfile.ZipFile:
    """The xlsx inside a downloaded FSA file: a zip that holds one workbook, or the workbook itself."""
    outer = zipfile.ZipFile(path)
    if "xl/workbook.xml" in outer.namelist():
        return outer
    inner = [n for n in outer.namelist() if n.lower().endswith(".xlsx") and not n.startswith("__MACOSX")]
    if not inner:
        raise ValueError(f"{path.name}: no .xlsx workbook inside (members: {outer.namelist()[:5]})")
    # One workbook per FSA zip in the research's 27 files; if a vintage ships more, the largest is the detail.
    name = max(inner, key=lambda member: outer.getinfo(member).file_size)
    return zipfile.ZipFile(io.BytesIO(outer.read(name)))


def sheet_rows(book: zipfile.ZipFile, wanted: str = "county_data") -> Iterator[list]:
    """Rows of one worksheet as lists of strings (None for empty cells), read with the standard library only.

    The county sheet is large, so the XML is streamed and each row is freed once read.
    """
    relation = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
    sheets = {s.get("name"): s.get(relation) for s in workbook.iter() if _local_tag(s.tag) == "sheet"}
    name = next((n for n in sheets if n.strip().lower() == wanted), None)
    name = name or next((n for n in sheets if "county" in n.lower()), None)
    if name is None:
        raise ValueError(f"no sheet {wanted!r}; sheets are {list(sheets)}")
    rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    target = next(r.get("Target") for r in rels.iter() if r.get("Id") == sheets[name])
    target = target.lstrip("/")
    target = target if target.startswith("xl/") else f"xl/{target}"

    shared: list[str] = []
    if "xl/sharedStrings.xml" in book.namelist():
        for _, element in ElementTree.iterparse(book.open("xl/sharedStrings.xml")):
            if _local_tag(element.tag) == "si":
                shared.append("".join(t.text or "" for t in element.iter() if _local_tag(t.tag) == "t"))
                element.clear()

    for _, element in ElementTree.iterparse(book.open(target)):
        if _local_tag(element.tag) != "row":
            continue
        cells: dict[int, str | None] = {}
        for cell in element:
            if _local_tag(cell.tag) != "c":
                continue
            kind, value = cell.get("t"), None
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in cell.iter() if _local_tag(t.tag) == "t")
            else:
                raw = next((v.text for v in cell if _local_tag(v.tag) == "v"), None)
                if raw is not None:
                    value = shared[int(raw)] if kind == "s" else raw
            ref = cell.get("r")
            cells[_column_index(ref) if ref else len(cells)] = value
        element.clear()
        yield [cells.get(i) for i in range(max(cells) + 1)] if cells else []


def _norm(value) -> str:
    return " ".join(str(value).split()).lower() if value is not None else ""


def _number(value) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return float("nan")


def state_name(value) -> str:
    """Upper-case state name from a name or a two-letter code."""
    text = " ".join(str(value or "").split()).upper()
    return STATE_CODES.get(text, text)


def fsa_silage_by_state(path: Path) -> tuple[pd.Series, dict]:
    """FSA corn planted acres with intended use Silage (Forage before 2019), summed by state, and a parse summary.

    Sheet ``county_data``; the header is the first row naming both "Crop" and "Planted Acres" (row 2 in the
    files the research read). A state with corn but no silage rows has 0 silage acres, not a missing value.
    """
    rows = sheet_rows(open_workbook(path))
    header = None
    for _, row in zip(range(25), rows):
        names = [_norm(cell) for cell in row]
        if "crop" in names and "planted acres" in names:
            header = names
            break
    if header is None:
        raise ValueError(f"{path.name}: no header row with 'Crop' and 'Planted Acres' in the first 25 rows")
    state_key = next((k for k in ("state", "state name", "state abbreviation", "state abbr") if k in header), None)
    if state_key is None or "intended use" not in header:
        raise ValueError(f"{path.name}: header lacks a state or 'Intended Use' column: {header}")
    at = {key: header.index(key) for key in (state_key, "crop", "intended use", "planted acres")}

    silage: dict[str, float] = {}
    corn_states: set[str] = set()
    uses: dict[str, float] = {}
    for row in rows:
        cell = {key: (row[i] if i < len(row) else None) for key, i in at.items()}
        if _norm(cell["crop"]) != "corn":
            continue
        state = state_name(cell[state_key])
        acres = _number(cell["planted acres"])
        if np.isnan(acres):                                # an empty acreage cell adds nothing
            acres = 0.0
        use = " ".join(str(cell["intended use"] or "").split())
        uses[use] = uses.get(use, 0.0) + acres
        corn_states.add(state)
        if use.lower() in SILAGE_USES:
            silage[state] = silage.get(state, 0.0) + acres
    by_state = pd.Series({state: silage.get(state, 0.0) for state in sorted(corn_states)}, dtype=float)
    summary = {"file": path.name, "silage_acres_us": round(float(by_state.sum())),
               "states_with_corn": len(corn_states),
               "corn_acres_by_intended_use": {k: round(v) for k, v in uses.items()}}
    return by_state, summary


def load_fsa(found: dict[tuple[int, str], Path]) -> tuple[pd.DataFrame, list[dict], dict]:
    """Long table state, year, vintage, fsa_silage_acres for every local file, with parse summaries and errors."""
    parts, summaries, errors = [], [], {}
    for (year, vintage), path in sorted(found.items()):
        try:
            by_state, summary = fsa_silage_by_state(path)
        except (ValueError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as error:
            errors[f"{year}_{vintage}"] = f"{path.name}: {error}"
            continue
        expected = RESEARCH_US_TOTALS.get((year, vintage))
        check = (None if expected is None
                 else abs(summary["silage_acres_us"] - expected) <= 0.001 * expected)
        summaries.append({"year": year, "vintage": vintage, **summary,
                          "research_us_total": expected, "matches_research_within_0_1pct": check})
        parts.append(pd.DataFrame({"state": by_state.index, "year": year, "vintage": vintage,
                                   "fsa_silage_acres": by_state.to_numpy()}))
    columns = ["state", "year", "vintage", "fsa_silage_acres"]
    return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=columns)), summaries, errors


# --- incumbents ------------------------------------------------------------------------------------

def incumbent_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Held-out silage predictions of the root incumbent (reversion_only) and of persistence, 2017-2024.

    Recomputed in memory with kernelag.state_model's own backtest (it writes nothing), plus the NASS
    November residual R = planted (as of) minus harvested-for-grain forecast (as of) from the same panel.
    """
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from kernelag.state_model import add_changes, backtest_predictions
    from kernelag.state_panel import load_panel

    table = add_changes(load_panel("nov"))
    held = backtest_predictions(table)
    silage = held[(held["series"] == "silage") & held["predictor"].isin(["same_as_last_year", "reversion_only"])]
    wide = silage.pivot_table(index=["year", "state"], columns="predictor", values="predicted").reset_index()
    truth = silage.drop_duplicates(["year", "state"])[["year", "state", "actual", "last"]]
    frame = truth.merge(wide, on=["year", "state"]).rename(
        columns={"same_as_last_year": "persistence", "reversion_only": "incumbent_reversion_only"})
    residual = table[["state", "year"]].assign(residual=table["planted_asof"] - table["grain_asof"])
    frame = frame.merge(residual, on=["state", "year"], how="left")
    return frame[frame["year"].isin(BACKTEST_YEARS)].reset_index(drop=True), table


def daniel_nodrift_nass(years: list[int]) -> pd.DataFrame:
    """Held-out predictions of test_models/danielModel's nodrift_nass ridge, recomputed in memory (read-only)."""
    spec = importlib.util.spec_from_file_location("fsa_daniel_model", DANIEL_MODEL)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    panel = model.load_panel("nov")
    rows = []
    for year in years:
        train, test = model.rows_for(panel, range(2000, year)), model.rows_for(panel, [year])
        predicted = model.silage_ridge(panel, train, test, names=model.FEATURE_SETS["nass"], penalty=1.0, drift=False)
        actual = {r["state"]: r["actual"] for r in test}
        rows += [{"year": year, "state": state_name(code), "incumbent_nodrift_nass": value,
                  "actual_daniel": actual[code]} for code, value in predicted.items()]
    return pd.DataFrame(rows)


# --- candidate rules -------------------------------------------------------------------------------

def capped(prediction: pd.Series, residual: pd.Series) -> pd.Series:
    """min(prediction, R) where the November residual is known and positive; unchanged elsewhere.

    A missing prediction stays missing: the cap is a ceiling, never a prediction of its own.
    """
    cap = residual.where(residual > 0)
    return prediction.where(cap.isna() | prediction.isna() | (prediction <= cap), cap)


def fsa_ratio(frame: pd.DataFrame) -> pd.Series:
    """S(t-1) * clip(F_nov(t) / F_final(t-1), 0.5, 2.0); a ratio of 1 where F_final(t-1) is under 500 acres."""
    usable = frame["fsa_prev_final"] >= MIN_PRIOR_FSA_ACRES
    ratio = (frame["fsa_now"] / frame["fsa_prev_final"]).clip(*RATIO_CLIP).where(usable, 1.0)
    return frame["last"] * ratio.where(frame["fsa_now"].notna() & frame["fsa_prev_final"].notna())


def gate(frame: pd.DataFrame, kind: str) -> pd.Series:
    """Which state-years take the FSA prediction."""
    if kind == "fixed_list":
        return frame["state"].isin(FIXED_LIST)
    if kind == "realtime":
        return (frame["fsa_prev_final"] / frame["last"]) >= COVERAGE_MIN
    raise ValueError(kind)


def fsa_candidate(frame: pd.DataFrame, base: str, kind: str) -> pd.Series:
    """The pre-registered candidate: capped FSA ratio in gated states, the base prediction elsewhere."""
    moved = capped(fsa_ratio(frame), frame["residual"])
    use = gate(frame, kind) & moved.notna()
    return moved.where(use, frame[base])


# --- scoring ---------------------------------------------------------------------------------------

def yearly_scores(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """State WAPE and US-total error (percent of actual acres) per year and predictor."""
    rows = []
    for year, group in frame.groupby("year"):
        for column in columns:
            if group[column].isna().any():
                raise ValueError(f"{column} has missing predictions in {year}")
            miss = group[column] - group["actual"]
            rows.append({"year": int(year), "predictor": column, "n_states": len(group),
                         "state_wape_pct": 100 * miss.abs().sum() / group["actual"].sum(),
                         "us_error_pct": 100 * miss.sum() / group["actual"].sum()})
    return pd.DataFrame(rows)


def summarise(scores: pd.DataFrame, frame: pd.DataFrame, column: str) -> dict:
    """Mean yearly WAPE (team convention), pooled WAPE and US error, overall and without the relabel year."""
    mine = scores[scores["predictor"] == column].set_index("year")
    pooled = frame[column].sub(frame["actual"]).abs().sum() / frame["actual"].sum()
    out = {
        "years": [int(y) for y in mine.index],
        "mean_state_wape_pct": round(float(mine["state_wape_pct"].mean()), 3),
        "pooled_state_wape_pct": round(float(100 * pooled), 3),
        "mean_abs_us_error_pct": round(float(mine["us_error_pct"].abs().mean()), 3),
        "mean_us_error_pct": round(float(mine["us_error_pct"].mean()), 3),
        "mean_state_wape_pct_without_2019": round(float(mine.drop(RELABEL_YEAR, errors="ignore")
                                                        ["state_wape_pct"].mean()), 3),
        "by_year_state_wape_pct": {int(y): round(float(v), 2) for y, v in mine["state_wape_pct"].items()},
        "by_year_us_error_pct": {int(y): round(float(v), 2) for y, v in mine["us_error_pct"].items()},
    }
    return out


def paired_bootstrap(frame: pd.DataFrame, candidate: str, base: str, draws: int = BOOT_DRAWS,
                     seed: int = SEED) -> dict:
    """Change in mean yearly state WAPE (candidate minus base, points; negative = candidate better).

    90% percentile intervals from resampling years (8 years: coarse) and, separately, states (one draw of states
    used in every year). Also the team's existing rule: a gain counts only beyond two standard errors of the
    paired yearly differences (test_models/accuracy/state/README.md).
    """
    rng = np.random.default_rng(seed)
    years = sorted(frame["year"].unique())
    states = sorted(frame["state"].unique())

    def grid(column: str) -> np.ndarray:
        return frame.pivot(index="year", columns="state", values=column).reindex(index=years, columns=states).to_numpy()

    actual = grid("actual")
    err_c, err_b = np.abs(grid(candidate) - actual), np.abs(grid(base) - actual)
    if np.isnan(err_c).any() or np.isnan(err_b).any():
        raise ValueError(f"{candidate} or {base} lacks a prediction for some state-year")
    yearly = 100 * (err_c.sum(1) - err_b.sum(1)) / actual.sum(1)
    us_c = np.abs((grid(candidate) - actual).sum(1)) / actual.sum(1)
    us_b = np.abs((grid(base) - actual).sum(1)) / actual.sum(1)

    pick_years = rng.integers(0, len(years), size=(draws, len(years)))
    by_years = yearly[pick_years].mean(1)
    pick_states = rng.integers(0, len(states), size=(draws, len(states)))
    by_states = (100 * (err_c[:, pick_states].sum(2) - err_b[:, pick_states].sum(2))
                 / actual[:, pick_states].sum(2)).mean(0)
    gain = -yearly
    se = float(gain.std(ddof=1) / np.sqrt(len(gain))) if len(gain) > 1 else float("nan")
    return {
        "candidate": candidate, "base": base, "years": [int(y) for y in years], "n_states": len(states),
        "delta_mean_state_wape_points": round(float(yearly.mean()), 3),
        "ci90_resampling_years": [round(float(q), 3) for q in np.quantile(by_years, CI_LEVELS)],
        "ci90_resampling_states": [round(float(q), 3) for q in np.quantile(by_states, CI_LEVELS)],
        "years_candidate_better": int((yearly < 0).sum()),
        "delta_mean_abs_us_error_points": round(float(100 * (us_c - us_b).mean()), 3),
        "two_se_rule": {"gain_points": round(float(gain.mean()), 3), "se_points": round(se, 3),
                        "passes": bool(gain.mean() > 2 * se)},
        "draws": draws, "seed": seed,
    }


# --- assembly --------------------------------------------------------------------------------------

def attach_fsa(frame: pd.DataFrame, fsa: pd.DataFrame) -> pd.DataFrame:
    """Add fsa_now (in-season file of year t) and fsa_prev_final (final file of t-1) to each state-year.

    A state missing from a parsed file has 0 FSA silage acres; a missing file leaves the whole year NaN.
    """
    out = frame.copy()
    out["fsa_now"], out["fsa_prev_final"] = np.nan, np.nan
    for year in out["year"].unique():
        rows = out["year"] == year
        for column, (want_year, vintage) in {"fsa_now": (year, "nov" if year != 2025 else "dec"),
                                             "fsa_prev_final": (year - 1, "final")}.items():
            part = fsa[(fsa["year"] == want_year) & (fsa["vintage"] == vintage)]
            if len(part):
                acres = part.set_index("state")["fsa_silage_acres"]
                out.loc[rows, column] = out.loc[rows, "state"].map(acres).fillna(0.0).to_numpy()
    return out


def missing_file_list(found: dict) -> list[dict]:
    """What a person must download in a browser from FSA_PAGE into data/fsa/ (or data/fsa/raw/)."""
    return [{"crop_year": e["year"], "vintage": e["vintage"], "page_link_text": e["label"],
             "page_link": FSA_SITE + e["link"],
             "direct_file_used_by_research": FSA_SITE + e["research_file"] if e.get("research_file") else None,
             "save_as": unquote(e["link"].rsplit("/", 1)[-1]) if e["link"].lower().endswith(".zip")
             else f"fsa_{e['year']}_{e['vintage']}.zip (or keep the downloaded name)"}
            for e in FSA_FILES if (e["year"], e["vintage"]) not in found]


def info_2025_2026(fsa: pd.DataFrame, table: pd.DataFrame) -> dict:
    """2025 (frozen incumbent forecast beside the candidate) and 2026 implied values: information only."""
    info = {}
    have = {(int(y), v) for y, v in fsa[["year", "vintage"]].drop_duplicates().itertuples(index=False)}
    residual = table[["state", "year"]].assign(residual=table["planted_asof"] - table["grain_asof"])
    if {(2025, "dec"), (2024, "final")} <= have and SCORE_2025.is_file():
        stored = pd.read_csv(SCORE_2025)
        rows = pd.DataFrame({"year": 2025, "state": stored["state"], "actual": stored["silage_actual"],
                             "last": stored["silage_last"], "incumbent_reversion_only": stored["silage"]})
        rows = attach_fsa(rows.merge(residual, on=["state", "year"], how="left"), fsa)
        rows["fsa_realtime"] = fsa_candidate(rows, "incumbent_reversion_only", "realtime")
        rows = rows.dropna(subset=["actual"])
        info["2025"] = {
            "note": "information only; the stored 2025 score is frozen and nothing here is chosen on it. "
                    "FSA input is the 1 Dec 2025 file (released 9 Dec): later than the mid-November cutoff",
            **{c: round(float(100 * (rows[c] - rows["actual"]).abs().sum() / rows["actual"].sum()), 2)
               for c in ["incumbent_reversion_only", "fsa_realtime"]},
        }
    else:
        info["2025"] = "UNCOMPUTED: needs the 2025 1 Dec and 2024 final FSA files"
    if {(2026, "nov"), (2025, "final")} <= have:
        rows = table[table["year"] == 2026][["state", "year"]].merge(
            table[table["year"] == 2025][["state", "silage"]].rename(columns={"silage": "last"}), on="state")
        rows = attach_fsa(rows.merge(residual, on=["state", "year"], how="left"), fsa)
        rows["coverage_prev"] = rows["fsa_prev_final"] / rows["last"]
        rows["fsa_capped"] = capped(fsa_ratio(rows), rows["residual"])
        if FORECAST_2026.is_file():
            stored = pd.read_csv(FORECAST_2026)[["state", "silage"]].rename(columns={"silage": "incumbent_2026"})
            rows = rows.merge(stored, on="state", how="left")
        gated = rows[gate(rows, "realtime")]
        info["2026"] = {"note": "information only: implied 2026 silage acres in realtime-gated states",
                        "rows": gated.drop(columns=["year"]).round(3).to_dict(orient="records")}
    else:
        info["2026"] = "UNCOMPUTED: needs the 2026 November and 2025 final FSA files"
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--boot", type=int, default=BOOT_DRAWS, help="bootstrap draws")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    frame, table = incumbent_frame()
    daniel = daniel_nodrift_nass(BACKTEST_YEARS)
    frame = frame.merge(daniel, on=["year", "state"], how="left", validate="one_to_one")
    truth_mismatch = int(((frame["actual"] - frame["actual_daniel"]).abs() > 0.5).sum())

    # Components that need no FSA file: the residual cap alone, and the most any rule confined to the
    # fixed-list states could gain (their errors set to zero).
    fixed = frame["state"].isin(FIXED_LIST)
    base = frame["incumbent_reversion_only"]
    frame["incumbent_capped_fixed_list"] = capped(base, frame["residual"]).where(fixed, base)
    frame["incumbent_capped_all"] = capped(base, frame["residual"])
    frame["persistence_capped_all"] = capped(frame["persistence"], frame["residual"])
    frame["ceiling_fixed_list_exact"] = frame["actual"].where(fixed, base)
    # The best the pre-registered (capped) rule could do there: a perfect ratio still meets the cap.
    frame["ceiling_fixed_list_capped"] = capped(frame["actual"], frame["residual"]).where(fixed, base)
    cap_cuts_truth = int((fixed & (frame["residual"] > 0) & (frame["actual"] > frame["residual"])).sum())

    found = find_fsa_files()
    fsa, parse_summaries, parse_errors = load_fsa(found)
    frame = attach_fsa(frame, fsa)
    fsa_years = sorted(int(y) for y in frame.loc[frame["fsa_now"].notna() & frame["fsa_prev_final"].notna(),
                                                 "year"].unique())
    fsa_complete = fsa_years == BACKTEST_YEARS

    comparisons = [("incumbent_reversion_only", "persistence"), ("incumbent_nodrift_nass", "persistence"),
                   ("incumbent_nodrift_nass", "incumbent_reversion_only"),
                   ("incumbent_capped_fixed_list", "incumbent_reversion_only"),
                   ("incumbent_capped_all", "incumbent_reversion_only"),
                   ("persistence_capped_all", "persistence"),
                   ("ceiling_fixed_list_exact", "incumbent_reversion_only"),
                   ("ceiling_fixed_list_capped", "incumbent_reversion_only")]
    fsa_rows = {}
    if fsa_complete:
        frame["fsa_ratio_all_states"] = fsa_ratio(frame).fillna(frame["persistence"])   # replication row
        comparisons.append(("fsa_ratio_all_states", "persistence"))
        for kind in ["realtime", "fixed_list"]:
            for base_name in ["incumbent_reversion_only", "persistence", "incumbent_nodrift_nass"]:
                name = f"fsa_{kind}_over_{base_name}"
                frame[name] = fsa_candidate(frame, base_name, kind)
                comparisons.append((name, base_name))
                fsa_rows[name] = {"gated_state_years": int((gate(frame, kind) & fsa_ratio(frame).notna()).sum())}
        primary = "fsa_realtime_over_incumbent_reversion_only"
    else:
        reason = (f"UNCOMPUTED: FSA workbooks missing for backtest years {sorted(set(BACKTEST_YEARS) - set(fsa_years))}"
                  " (the FSA site timed out on ordinary requests; see data_step)")
        primary = None
        for kind in ["realtime", "fixed_list"]:
            for base_name in ["incumbent_reversion_only", "persistence", "incumbent_nodrift_nass"]:
                fsa_rows[f"fsa_{kind}_over_{base_name}"] = reason
        fsa_rows["fsa_ratio_all_states"] = reason

    columns = sorted({c for pair in comparisons for c in pair})
    scores = yearly_scores(frame, columns)
    summaries = {c: summarise(scores, frame, c) for c in columns}
    deltas = [paired_bootstrap(frame, c, b, draws=args.boot) for c, b in comparisons]
    share_fixed = float((frame.loc[fixed, "incumbent_reversion_only"] - frame.loc[fixed, "actual"]).abs().sum()
                        / (frame["incumbent_reversion_only"] - frame["actual"]).abs().sum())
    # How good the bases already are where FSA would act: the bar an FSA ratio has to clear in those states.
    inside = frame[fixed]
    within_fixed = {c: round(float(100 * (inside[c] - inside["actual"]).abs().sum() / inside["actual"].sum()), 2)
                    for c in columns if not c.startswith("ceiling")}

    if fsa_complete:
        verdict_row = next(d for d in deltas if d["candidate"] == primary)
        lo, hi = verdict_row["ci90_resampling_years"]
        verdict = (f"{primary}: {verdict_row['delta_mean_state_wape_points']:+.2f} points of mean state WAPE "
                   f"(90% CI over years {lo:+.2f} to {hi:+.2f}); two-SE rule passes: "
                   f"{verdict_row['two_se_rule']['passes']}")
    else:
        verdict = ("BLOCKED: no FSA workbook is local, so the FSA candidate is UNCOMPUTED. What is computed: the "
                   "incumbent against persistence, the residual cap alone, and the ceiling for any rule confined "
                   "to the fixed-list states (see comparisons).")

    status = "done" if fsa_complete else ("partial" if found else "blocked")
    results = {
        "group": "fsa",
        "status": status,
        "verdict": verdict,
        "primary_comparison": primary,
        "data_step": {
            "status": "OK" if fsa_complete else "BLOCKED",
            "page": FSA_PAGE,
            "probe_2026_11_14": PROBE_LOG,
            "files_found": {f"{y}_{v}": (p.relative_to(REPO) if p.is_relative_to(REPO) else p).as_posix()
                            for (y, v), p in sorted(found.items())},
            "files_missing": missing_file_list(found),
            "parse_summaries": parse_summaries,
            "parse_errors": parse_errors,
            "fsa_backtest_years_available": fsa_years,
        },
        "incumbent": {
            "primary": "kernelag.state_model, selected silage set 'reversion_only' (root report model; "
                       "DOCS/DECISIONS.md 02:40Z and 03:45Z)",
            "secondary": "test_models/danielModel nodrift_nass (kept as incumbent by test_models/accuracy/state)",
            "truth": "NASS final silage acres harvested as stored in data/nass/corn_acres_state.csv (latest revised "
                     "Quick Stats value), not the first January estimate the research note uses",
            "years": BACKTEST_YEARS, "states": 48,
            "metric": "state WAPE = 100 * sum|pred - actual| / sum actual per year, averaged over years; "
                      "US error = 100 * sum(pred - actual) / sum actual",
            "reproduced_stored_backtest": "per-state predictions recomputed in memory; yearly errors equal "
                                          "data/models/state_model_backtest.csv",
            "truth_mismatch_state_years_vs_danielModel": truth_mismatch,
            "residual_states_per_year": int(frame.groupby("year")["residual"].apply(lambda s: (s > 0).sum()).min()),
        },
        "method": {
            "candidate": "S(t-1) * clip(F_nov(t) / F_final(t-1), 0.5, 2.0) in gated states, capped at R(t) > 0; "
                         "other states keep the base; F_final(t-1) < 500 acres -> ratio 1",
            "gates": {"realtime": f"F_final(t-1) / S(t-1) >= {COVERAGE_MIN} (primary)",
                      "fixed_list": FIXED_LIST},
            "bases": ["incumbent_reversion_only (primary)", "persistence (variant B)", "incumbent_nodrift_nass"],
            "fsa_vintage": "in-season file published by mid-November of year t over the final file of t-1; "
                           "2025 uses the 1 Dec 2025 file (information only)",
            "pre_registered_sensitivity": "mean state WAPE without 2019, the Forage-to-Silage relabel year",
        },
        "fsa_rows": fsa_rows,
        "summaries": summaries,
        "comparisons": deltas,
        "fixed_list_share_of_incumbent_abs_error": round(share_fixed, 4),
        "fixed_list_share_of_actual_acres": round(float(inside["actual"].sum() / frame["actual"].sum()), 4),
        "pooled_wape_pct_within_fixed_list_states": within_fixed,
        "fixed_list_state_years_where_actual_exceeds_november_residual": {
            "count": cap_cuts_truth, "of": int(fixed.sum()),
            "meaning": "state-years where the cap would cut even a perfect forecast (NASS data only)"},
        "information_only": info_2025_2026(fsa, table) if len(fsa) else
        {"2025": "UNCOMPUTED: no FSA file", "2026": "UNCOMPUTED: no FSA file"},
        "research_reported_not_recomputed": RESEARCH_REPORTED,
    }

    (OUT / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    keep = ["year", "state", "actual", "last", "residual", "fsa_now", "fsa_prev_final", *columns]
    frame[keep].sort_values(["year", "state"]).to_csv(OUT / "predictions.csv", index=False, lineterminator="\n")
    if len(fsa):
        fsa.sort_values(["year", "vintage", "state"]).to_csv(OUT / "fsa_state_silage.csv", index=False,
                                                             lineterminator="\n")

    print(f"status: {status}; FSA files found {len(found)} of {len(FSA_FILES)}")
    for c in columns:
        s = summaries[c]
        print(f"  {c:48s} mean state WAPE {s['mean_state_wape_pct']:6.2f}%  "
              f"mean |US| {s['mean_abs_us_error_pct']:5.2f}%")
    for d in deltas:
        print(f"  {d['candidate']} - {d['base']}: {d['delta_mean_state_wape_points']:+.2f} pts, "
              f"CI years {d['ci90_resampling_years']}, CI states {d['ci90_resampling_states']}")
    print(verdict)


if __name__ == "__main__":
    main()
