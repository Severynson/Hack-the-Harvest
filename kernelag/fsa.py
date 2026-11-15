"""FSA Crop Acreage Data: corn acres by county, intended use and vintage, from every downloaded workbook.

The Farm Service Agency (FSA) publishes, about monthly from August to January, the acres farmers certified to
it for every crop (corn acreage reports are due 15 July in most counties). Each release is one Excel workbook
with a county-by-crop sheet. These numbers are farmers' own certifications, not NASS survey estimates, so a
Kernel forecast that must not use current-year NASS information may use them, subject to the as-of rule below.

This module reads every archive in ``data/raw/fsa/`` with the Python standard library only (an .xlsx file is a
zip of XML files; the large county sheet is streamed row by row), keeps the field-corn rows (crop CORN without
its sweet-corn and popcorn crop types) and writes three tables.

Inputs:
    data/raw/fsa/*.zip               FSA Crop Acreage Data archives, one .xlsx each, saved by hand from the FSA
                                     page below (about 1.8 GB, git-ignored; the FSA site refuses scripted downloads)
    data/nass/corn_acres_state.csv   NASS final planted acres, used only by the validation (coverage check)

Outputs (``data/fsa/``):
    fsa_files.csv            one row per archive: zip and workbook names, crop year, data date and its source,
                             publication date, its source and the rule that set it, the workbook's internal
                             save time and its source, vintage, sha256, status and reason, US check
                             totals, every CORN crop-type|intended-use label seen with its planted acres, notes
    fsa_corn_county.parquet  state_fips, county_fips, state, county, crop_year, data_as_of, vintage,
                             intended_use, intended_use_raw, irrigation, then planted, failed, prevented,
                             volunteer, not planted and planted-and-failed acres (NaN where a file lacks one)
    fsa_corn_state.csv       the acres summed by state, crop year, data date, vintage and intended use

Status in fsa_files.csv: ``ok`` (loaded); ``summary_only`` (2007-2011 state-by-crop summaries: all-use corn, no
county or intended use; used only as a check); ``corrupt`` (truncated download: fetch it again); ``unusable``
(opened, but the intended-use column is scrambled; seen in the November 2011 file); ``unparsed`` (layout not
understood; reason given).

Intended use: FSA's own label is kept in ``intended_use_raw`` and mapped to ``intended_use`` by ``USE_MAP``.
"Forage" (code FG) is mapped to silage: FSA Notice CP-749 replaced corn intended use Forage with Silage from
the 2019 program year "regardless of the type" (DOCS/research/gap_fsa_ratio_baseline_2026.md, section 2.2).

Dates: ``data_as_of`` comes from the date FSA stamps in the workbook's title rows, else from the inner file
name. ``assumed_published`` is a conservative release date:

    1. the documented release date where one is known (``DOCUMENTED_RELEASES``: the research note above, or the
       FSA page's release label for 2025-2026 files); otherwise
    2. the later of (a) ``data_as_of`` plus ``PUBLICATION_LAG_DAYS`` (8 days, the median of the seven documented
       data-to-release lags, which run from 5 to 11 days) and (b) the day after the workbook's own internal save
       time. A workbook cannot have been posted before FSA last saved it; saved on some day, it is taken as
       posted no earlier than the next.

The internal save time (``internal_saved``) is the xlsx's ``docProps/core.xml`` ``dcterms:modified`` (UTC, whose
calendar date is never earlier than the US local one), else the date-time of the workbook's zip entry (the local
clock of whoever zipped it; for a truncated download, read from its first local file header);
``internal_saved_source`` says which. ``published_rule`` names the input that decided (documented release, data
date + 8 days, or internal save + 1 day) and ``published_source`` says the same in words ("documented" or
"assumed: ...").

Why the rule changed (independent audit, 2026-11-15): the earlier rule, data date + 5 days, used the shortest
documented lag. Reading every archive's internal timestamps showed three files that rule made usable before FSA
had even saved them: 2013 September (data 1 Sep, assumed released 6 Sep, saved 17 Sep), 2013 October (data
1 Oct, assumed 6 Oct, saved 18 Oct) and 2015 September (data 3 Sep, assumed 8 Sep, saved 16 Sep). Each was
input to a 15 September or 15 October backtest forecast that could not have had it. The documented lags are
5, 7, 8, 8, 10, 10 and 11 days (median 8).

As-of rule (use ``usable_files`` or ``latest_file``): a forecast made on date D for crop year t may use only
files with ``assumed_published`` on or before D (unchanged; only the publication dates became later). When a
month is missing (no October or November 2025 file: federal shutdown) the latest earlier file stands in; a later
file never does. A crop year's final (January) file may serve only as history for later crop years.

County codes are FSA administrative codes (state code + county code). They equal Census FIPS codes for almost
every county (two territories are recoded: FSA 14 Guam -> 66, 52 Virgin Islands -> 78); Connecticut moved to
planning regions in the 2026 files.

Run: python -m kernelag.fsa [--workers 12]       parse every archive, write the tables, then validate
     python -m kernelag.fsa --validate           validate the tables already written
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import zipfile
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pandas as pd

from kernelag.paths import REPO, data_dir, record_in_manifest

RAW_DIR = REPO / "data" / "raw" / "fsa"
SOURCE_URL = ("https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/"
              "frequently-requested/crop-acreage-data")
PUBLICATION_LAG_DAYS = 8      # median documented data-to-release lag (DOCUMENTED_RELEASES: 5 to 11 days)
SAVE_TO_POST_DAYS = 1          # a workbook saved on day d is taken as posted no earlier than day d + 1
MIN_GRAIN_SHARE = 0.5          # below this share of grain among field-corn acres a file is flagged unusable
MEASURES = ["planted_acres", "failed_acres", "prevented_acres", "volunteer_acres", "not_planted_acres",
            "planted_and_failed_acres"]

# Release dates documented in DOCS/research/gap_fsa_ratio_baseline_2026.md (section 2.2 and the FSA page labels it
# quotes, which name release dates for 2025-2026 files): data date -> release date.
DOCUMENTED_RELEASES = {
    date(2025, 9, 2): date(2025, 9, 12),      # FSA page (saved: data/fsa/index.html) "as of September 12, 2025"
    date(2025, 12, 1): date(2025, 12, 9),     # research note 1 and 7: released 9 Dec 2025, data as of 1 Dec
    date(2026, 1, 5): date(2026, 1, 12),      # research note: 2025 final released 12 Jan 2026, data as of 5 Jan
    date(2026, 8, 1): date(2026, 8, 12),      # research note 2.2: 2026 releases of 12 Aug, 11 Sep, 9 Oct, 10 Nov
    date(2026, 9, 1): date(2026, 9, 11),
    date(2026, 10, 1): date(2026, 10, 9),
    date(2026, 11, 5): date(2026, 11, 10),
}

# FSA's corn intended-use labels (words from 2012, two-letter codes in 2009-2011) -> Kernel's normalised use.
# Any label not listed here becomes "other"; a blank label becomes "unspecified".
USE_MAP = {
    "grain": "grain", "gr": "grain",
    "silage": "silage", "sg": "silage", "forage": "silage", "fg": "silage",
    "seed": "seed", "sd": "seed",
    "grazing": "grazing", "gz": "grazing",
    "fresh": "other", "fh": "other",
    "processed": "other", "pr": "other",
    "left standing": "other", "ls": "other",
    "green manure": "other", "gm": "other",
    "blank": "unspecified",
}

# The only crop kept. Sweet corn and popcorn are crop types of CORN in the FSA files ("SWEET", "SWEET, BICOLOR",
# "SWEET-WHITE", "POPCORN", "STRAWBERRY POPCORN" ...); they are dropped, as NASS's "corn planted for all purposes"
# leaves them out. Every other type (yellow, white, waxy, high amylose, blue, red, purple, tropical, ornamental,
# corn nuts, grainless forage ...) is kept and summed.
CORN = "CORN"
EXCLUDED_TYPE_WORDS = ("SWEET", "POPCORN")
# A few files (2012 Nov and Dec, 2013 Aug, 2017 Aug) give the crop type as a code instead: SWT sweet, SBI sweet
# bicolor, SWH sweet white, SYE / SYL sweet yellow early / late, POP popcorn, PSN strawberry popcorn (identified
# by matching acres and uses against the named types in neighbouring files of the same crop year).
EXCLUDED_TYPE_CODES = {"SWT", "SBI", "SWH", "SYE", "SYL", "POP", "PSN"}

STATE_NAMES = {
    "01": "ALABAMA", "02": "ALASKA", "04": "ARIZONA", "05": "ARKANSAS", "06": "CALIFORNIA", "08": "COLORADO",
    "09": "CONNECTICUT", "10": "DELAWARE", "11": "DISTRICT OF COLUMBIA", "12": "FLORIDA", "13": "GEORGIA",
    "15": "HAWAII", "16": "IDAHO", "17": "ILLINOIS", "18": "INDIANA", "19": "IOWA", "20": "KANSAS",
    "21": "KENTUCKY", "22": "LOUISIANA", "23": "MAINE", "24": "MARYLAND", "25": "MASSACHUSETTS",
    "26": "MICHIGAN", "27": "MINNESOTA", "28": "MISSISSIPPI", "29": "MISSOURI", "30": "MONTANA",
    "31": "NEBRASKA", "32": "NEVADA", "33": "NEW HAMPSHIRE", "34": "NEW JERSEY", "35": "NEW MEXICO",
    "36": "NEW YORK", "37": "NORTH CAROLINA", "38": "NORTH DAKOTA", "39": "OHIO", "40": "OKLAHOMA",
    "41": "OREGON", "42": "PENNSYLVANIA", "44": "RHODE ISLAND", "45": "SOUTH CAROLINA", "46": "SOUTH DAKOTA",
    "47": "TENNESSEE", "48": "TEXAS", "49": "UTAH", "50": "VERMONT", "51": "VIRGINIA", "53": "WASHINGTON",
    "54": "WEST VIRGINIA", "55": "WISCONSIN", "56": "WYOMING", "60": "AMERICAN SAMOA", "66": "GUAM",
    "69": "NORTHERN MARIANA ISLANDS", "72": "PUERTO RICO", "78": "VIRGIN ISLANDS",
}
# FSA state codes equal FIPS codes for the states; two territories differ (FSA 14 = Guam, 52 = Virgin Islands).
FSA_TO_FIPS = {"14": "66", "52": "78"}
POSTAL = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11",
          "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
          "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30",
          "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
          "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
          "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56", "AS": "60", "GU": "66", "MP": "69",
          "PR": "72", "VI": "78"}

# Header names (lower case, spaces collapsed) -> column role. The first alias found in a header wins.
COLUMN_ALIASES = {
    "state_code": ["state code", "state_fsa_code"],
    "county_code": ["county code", "county_fsa_code"],
    "state_name": ["state", "state name", "state abbrev"],
    "county_name": ["county", "county name"],
    "crop": ["crop", "crop name"],
    "crop_type": ["crop type name", "crop type"],
    "intended_use": ["intended use"],
    "irrigation": ["irrigation practice"],
    "planted_acres": ["planted acres", "planted total", "planted"],
    "volunteer_acres": ["volunteer acres", "volunteer total", "volunteer"],
    "failed_acres": ["failed acres", "failded acres", "failed total", "failed"],   # "Failded": 2012 Oct, Jan files
    "prevented_acres": ["prevented acres", "prevented total", "prevented"],
    "not_planted_acres": ["not planted acres", "not planted total", "not planted"],
    "planted_and_failed_acres": ["planted and failed acres"],
}
# 2011 files give irrigated and non-irrigated acres as separate columns instead of an irrigation-practice column.
SPLIT_COLUMNS = {
    "planted_acres": ("planted acres irrigated", "planted acres non irrigated"),
    "prevented_acres": ("prevented acres irrigated", "prevented acres non irrigated"),
    "failed_acres": ("failed acres irrigated", "failed acres non irrigated"),
    "volunteer_acres": ("volunteer acres irrigated", "volunteer acres non irrigated"),
    "not_planted_acres": ("not planted irrigated", "not planted non-irrigated"),
}

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
          "oct": 10, "nov": 11, "dec": 12}
VINTAGE_BY_MONTH = {7: "aug", 8: "aug", 9: "sep", 10: "oct", 11: "nov", 12: "dec", 1: "final"}
VINTAGE_SHIFT_DAYS = 7
EXCEL_EPOCH = date(1899, 12, 30)
FILE_COLUMNS = ["zip_name", "inner_xlsx", "crop_year", "data_as_of", "date_source", "assumed_published",
                "published_source", "published_rule", "internal_saved", "internal_saved_source", "vintage", "kind",
                "sha256", "status", "reason", "corn_rows", "us_corn_planted", "us_grain_planted", "us_silage_planted",
                "us_corn_planted_and_failed", "counties_with_silage", "us_sweet_pop_planted",
                "us_silage_all_types", "us_all_types_planted_and_failed", "pivot_corn_planted_and_failed",
                "corn_crop_labels", "corn_type_use_labels", "notes"]


# --- small helpers ---------------------------------------------------------------------------------------------

def _norm(value) -> str:
    """Lower case with runs of whitespace (including line breaks inside header cells) collapsed to one space."""
    return " ".join(str(value).split()).lower() if value is not None else ""


def _number(value) -> float:
    """A cell as a float; empty or text cells are NaN."""
    if value is None or value == "":
        return float("nan")
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return float("nan")


def _text(value) -> str:
    """A cell as text with runs of whitespace collapsed (case kept)."""
    return " ".join(str(value).split()) if value is not None else ""


def _cell(row: list, roles: dict[str, int], role: str):
    """The value of the column playing ``role`` in one row, or None when the file has no such column."""
    index = roles.get(role)
    return row[index] if index is not None and index < len(row) else None


def normalise_use(label) -> str:
    """Kernel's intended use for one FSA label: grain, silage, seed, grazing, other or unspecified.

    Grain, Silage (and Forage, its name before 2019), Seed and Grazing map to themselves; Fresh, Processed and
    Left Standing (and any label not in USE_MAP) to other; an empty cell or the word "Blank" to unspecified.
    """
    key = _norm(label)
    if not key:
        return "unspecified"
    return USE_MAP.get(key, "other")


def is_corn(crop) -> bool:
    """True for FSA crop CORN only (not SWEET CORN, POPCORN or any other crop whose name contains 'corn')."""
    return " ".join(str(crop or "").split()).upper() == CORN


def is_field_corn(crop_type) -> bool:
    """False for sweet-corn and popcorn crop types of CORN, True for every other type (blank included)."""
    text = " ".join(str(crop_type or "").split()).upper()
    return text not in EXCLUDED_TYPE_CODES and not any(word in text for word in EXCLUDED_TYPE_WORDS)


def excel_date(serial) -> date | None:
    """A date from an Excel day number (as stored in xlsx cells), or None when the cell is not one."""
    number = _number(serial)
    if np.isnan(number) or not 30000 <= number <= 60000:
        return None
    return EXCEL_EPOCH + timedelta(days=int(number))


def crop_year_from_name(name: str) -> int | None:
    """Crop year from a file name such as 2016_fsa_acres_120216.xlsx or Revised_2012_fsa_acres_dec_2012.xlsx."""
    match = re.search(r"(20\d\d)_fsa", name, re.IGNORECASE)
    return int(match.group(1)) if match else None


def date_from_name(name: str, crop_year: int) -> tuple[date | None, str]:
    """Data date written in an FSA file name, and its precision ("day", "month" or "none").

    Forms seen: MMDDYY (2026_fsa_acres_web_110526), MMDDYYYY (2015_fsa_acres_08032015), month and year
    (2012_fsa_acres_nov_2012, 2011_fsa_acres_detail_sep2011_1). A date must fall between 1 July of the crop
    year and 30 June of the next year; anything else (such as "jan2014" on a 2014 crop-year file, or the
    7-digit "1003016") is rejected rather than guessed.
    """
    stem = re.sub(r"\.xlsx$", "", Path(name).name, flags=re.IGNORECASE).lower()
    earliest, latest = date(crop_year, 7, 1), date(crop_year + 1, 6, 30)

    def plausible(candidate: date) -> bool:
        return earliest <= candidate <= latest

    for digits in re.findall(r"(?<!\d)(\d{8}|\d{6})(?!\d)", stem):
        month, day = int(digits[:2]), int(digits[2:4])
        year = int(digits[4:]) if len(digits) == 8 else 2000 + int(digits[4:])
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if plausible(candidate):
            return candidate, "day"
    for word, year_text in re.findall(r"(?<![a-z])(jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec)"
                                      r"[a-z]*[_\- ]?(20\d\d|\d\d)(?!\d)", stem):
        year = int(year_text) if len(year_text) == 4 else 2000 + int(year_text)
        candidate = date(year, MONTHS[word], 1)
        if plausible(candidate):
            return candidate, "month"
    return None, "none"


def vintage_label(data_as_of: date | None, crop_year: int, final_in_name: bool = False) -> str:
    """aug, sep, oct, nov, dec or final (the January file after the crop year) from the data date.

    The month is read a week after the data date, so a file stamped on the last days of a month counts as the
    next month's release (2017-08-31 is FSA's September 2017 file; 2020-07-31 its August 2020 file).
    """
    if data_as_of is None:
        return "final" if final_in_name else "unknown"
    month_of = data_as_of + timedelta(days=VINTAGE_SHIFT_DAYS)
    if month_of.year > crop_year:
        return "final"
    return VINTAGE_BY_MONTH.get(month_of.month, month_of.strftime("%b").lower())


RULE_DOCUMENTED = "documented release"
RULE_DATA_LAG = f"data date + {PUBLICATION_LAG_DAYS} days"
RULE_SAVED = f"internal save + {SAVE_TO_POST_DAYS} day"


def published_date(data_as_of: date | None, saved: datetime | None = None) -> tuple[date | None, str, str]:
    """Conservative release date, its ``published_source`` text and its ``published_rule``.

    The documented release where one is known; otherwise the later of the data date plus PUBLICATION_LAG_DAYS
    and the day after the workbook's internal save time ``saved`` (when known). The save time decides only when
    it is strictly later: a workbook saved the day before data date + 8 keeps data date + 8.
    """
    if data_as_of is None:
        return None, "unknown (no data date)", "none: no data date"
    if data_as_of in DOCUMENTED_RELEASES:
        return DOCUMENTED_RELEASES[data_as_of], "documented", RULE_DOCUMENTED
    by_lag = data_as_of + timedelta(days=PUBLICATION_LAG_DAYS)
    by_save = saved.date() + timedelta(days=SAVE_TO_POST_DAYS) if saved is not None else None
    if by_save is not None and by_save > by_lag:
        return by_save, f"assumed: workbook saved {saved.date()} + {SAVE_TO_POST_DAYS} day", RULE_SAVED
    return by_lag, f"assumed: data date + {PUBLICATION_LAG_DAYS} days", RULE_DATA_LAG


def core_modified(book: zipfile.ZipFile) -> datetime | None:
    """``dcterms:modified`` from the workbook's docProps/core.xml as a naive UTC date-time (None if absent)."""
    if "docProps/core.xml" not in book.namelist():
        return None
    try:
        root = ElementTree.fromstring(book.read("docProps/core.xml"))
    except ElementTree.ParseError:
        return None
    text = next((e.text for e in root.iter() if _tag(e) == "modified" and e.text), None)
    if text is None:
        return None
    try:
        stamp = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp.astimezone(UTC).replace(tzinfo=None) if stamp.tzinfo else stamp


def zip_entry_time(date_time: tuple | None) -> datetime | None:
    """A zip entry's date-time (``ZipInfo.date_time``), or None for the 1980 placeholder some writers store."""
    if date_time is None or date_time[0] < 2000:
        return None
    try:
        return datetime(*date_time)
    except ValueError:
        return None


def internal_saved(book: zipfile.ZipFile, entry: tuple | None) -> tuple[datetime | None, str]:
    """When FSA last saved the workbook, and from where: core.xml modified (UTC), else the zip entry time."""
    modified = core_modified(book)
    if modified is not None:
        return modified, "docProps/core.xml dcterms:modified (UTC)"
    entry_time = zip_entry_time(entry)
    if entry_time is not None:
        return entry_time, "zip entry date-time (local clock)"
    return None, "none: no core.xml modified time or zip entry time"


# --- reading an xlsx with the standard library -----------------------------------------------------------------

def _tag(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


_COLUMN_CACHE: dict[str, int] = {}


def column_index(ref: str) -> int:
    """Zero-based column of a cell reference such as "AB12"."""
    letters = ref.rstrip("0123456789")
    index = _COLUMN_CACHE.get(letters)
    if index is None:
        index = 0
        for letter in letters:
            index = index * 26 + ord(letter) - 64
        index -= 1
        _COLUMN_CACHE[letters] = index
    return index


def open_workbook(archive: Path) -> tuple[zipfile.ZipFile, str, tuple | None]:
    """The workbook inside an FSA archive (a zip that holds one .xlsx), the workbook's file name and the
    date-time of its zip entry (None when the archive is the workbook itself)."""
    outer = zipfile.ZipFile(archive)
    if "xl/workbook.xml" in outer.namelist():
        return outer, archive.name, None
    inner = [n for n in outer.namelist() if n.lower().endswith(".xlsx") and not n.startswith("__MACOSX")]
    if not inner:
        raise ValueError(f"no .xlsx inside (members: {outer.namelist()[:5]})")
    name = max(inner, key=lambda member: outer.getinfo(member).file_size)
    return zipfile.ZipFile(io.BytesIO(outer.read(name))), name, outer.getinfo(name).date_time


def shared_strings(book: zipfile.ZipFile) -> list[str]:
    """The workbook's shared-string table (cells of type "s" hold an index into it)."""
    strings: list[str] = []
    if "xl/sharedStrings.xml" in book.namelist():
        for _, element in ElementTree.iterparse(book.open("xl/sharedStrings.xml")):
            if _tag(element) == "si":
                strings.append("".join(t.text or "" for t in element.iter() if _tag(t) == "t"))
                element.clear()
    return strings


def sheet_paths(book: zipfile.ZipFile) -> dict[str, str]:
    """Sheet name -> path of its XML part inside the workbook, in workbook order."""
    relation = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {r.get("Id"): r.get("Target") for r in rels.iter() if r.get("Id")}
    paths = {}
    for sheet in workbook.iter():
        if _tag(sheet) == "sheet":
            target = targets[sheet.get(relation)].lstrip("/")
            paths[sheet.get("name")] = target if target.startswith("xl/") else f"xl/{target}"
    return paths


def _cell_value(cell, strings: list[str]):
    kind = cell.get("t")
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.iter() if _tag(t) == "t")
    raw = next((v.text for v in cell if _tag(v) == "v"), None)
    if raw is not None and kind == "s":
        return strings[int(raw)]
    return raw


def sheet_rows(book: zipfile.ZipFile, path: str, strings: list[str], keep=None) -> Iterator[list]:
    """Rows of one worksheet as lists of cell values (None for empty cells), streamed.

    ``keep(row_element) -> bool`` may reject a row before its cells are decoded (used to skip non-corn rows
    cheaply); rejected rows are not yielded. Processed rows leave the parse tree so memory stays flat.
    """
    parent = None
    for event, element in ElementTree.iterparse(book.open(path), events=("start", "end")):
        tag = _tag(element)
        if event == "start":
            if tag == "sheetData":
                parent = element
            continue
        if tag != "row":
            continue
        if keep is None or keep(element):
            values = {column_index(c.get("r")) if c.get("r") else i: _cell_value(c, strings)
                      for i, c in enumerate(element) if _tag(c) == "c"}
            yield [values.get(i) for i in range(max(values) + 1)] if values else []
        element.clear()
        if parent is not None:
            parent.clear()


def first_rows(book: zipfile.ZipFile, path: str, strings: list[str], count: int) -> list[list]:
    """The first ``count`` rows of a worksheet."""
    rows = []
    for row in sheet_rows(book, path, strings):
        rows.append(row)
        if len(rows) >= count:
            break
    return rows


# --- one archive -----------------------------------------------------------------------------------------------

def find_header(rows: list[list]) -> int | None:
    """Index of the header row: the first that names a crop column and a planted-acres column."""
    for index, row in enumerate(rows):
        names = {_norm(cell) for cell in row}
        if names & {"crop", "crop name"} and any(n.startswith("planted") for n in names):
            return index
    return None


def column_roles(header: list) -> dict[str, int]:
    """Column role -> index for one header row (see COLUMN_ALIASES and SPLIT_COLUMNS)."""
    names = [_norm(cell) for cell in header]
    roles: dict[str, int] = {}
    for role, aliases in COLUMN_ALIASES.items():
        hit = next((names.index(alias) for alias in aliases if alias in names), None)
        if hit is not None:
            roles[role] = hit
    # 2010 files call the state code "State" and the postal code "State Abbrev".
    if "state_code" not in roles and "state abbrev" in names and "state" in names:
        roles["state_code"] = names.index("state")
        roles["state_name"] = names.index("state abbrev")
    for role, (irrigated, dry) in SPLIT_COLUMNS.items():
        if irrigated in names and dry in names:
            roles[f"{role}:I"] = names.index(irrigated)
            roles[f"{role}:N"] = names.index(dry)
    return roles


HEADER_WORDS = {"crop", "crop name", "corn", "row labels", "state", "st", "state code"}
US_TOTAL_LABELS = {"us", "u.s.", "united states"}     # national rows in the state-by-crop pivots


def title_rows(rows: list[list]) -> list[list]:
    """The rows above a sheet's column header (where FSA puts the title and its date stamp)."""
    for index, row in enumerate(rows):
        if {_norm(cell) for cell in row} & HEADER_WORDS:
            return rows[:index]
    return rows


def sheet_date(rows: list[list], crop_year: int) -> date | None:
    """The data date FSA stamps (as an Excel day number) in a sheet's title rows, if any."""
    for row in title_rows(rows):
        for cell in row:
            stamp = excel_date(cell)
            if stamp is not None and date(crop_year, 7, 1) <= stamp <= date(crop_year + 1, 6, 30):
                return stamp
    return None


def pivot_corn_total(book: zipfile.ZipFile, path: str, strings: list[str]) -> float:
    """US corn planted-and-failed acres from FSA's own state-by-crop pivot sheet (sum of state rows)."""
    total, corn_col = 0.0, None
    for row in sheet_rows(book, path, strings):
        names = [_norm(cell) for cell in row]
        if corn_col is None:
            if "corn" in names:
                corn_col = names.index("corn")
            continue
        label = names[0] if names else ""
        if not label or "total" in label or label in US_TOTAL_LABELS:
            continue
        total += np.nan_to_num(_number(row[corn_col] if corn_col < len(row) else None))
    return total if corn_col is not None else float("nan")


def corn_rows(book: zipfile.ZipFile, path: str, strings: list[str], header: list,
              ) -> tuple[pd.DataFrame, dict, list[str]]:
    """Field-corn rows of the county sheet, plus label tallies and all-type check totals.

    Every row whose crop is CORN is tallied by crop type and intended use (``labels``) and counted in the
    all-type totals (the basis of FSA's own pivot and of the research note's figures). Only field-corn rows
    (crop types other than sweet corn and popcorn) are returned. Measures a file does not report stay NaN.
    """
    roles = column_roles(header)
    missing = [r for r in ("state_code", "county_code", "crop", "intended_use") if r not in roles]
    if missing or not ({"planted_acres", "planted_acres:I"} & roles.keys()):
        raise ValueError(f"county sheet lacks columns {missing or ['planted acres']}; header: {header}")
    crop_col = roles["crop"]
    corn_ids = {str(i) for i, s in enumerate(strings) if "CORN" in s.upper()}

    def keep(row_element) -> bool:
        for position, cell in enumerate(row_element):
            ref = cell.get("r")
            if (column_index(ref) if ref else position) != crop_col:
                continue
            if cell.get("t") == "s":                  # shared string: compare the index, no text lookup needed
                raw = next((v.text for v in cell if _tag(v) == "v"), None)
                return raw in corn_ids
            return "CORN" in str(_cell_value(cell, strings) or "").upper()
        return False

    crops: Counter = Counter()          # every crop name containing "corn" -> planted acres
    labels: Counter = Counter()         # "crop type|intended use" -> planted acres, all CORN rows
    totals = Counter()                  # all-type check totals
    notes: list[str] = []
    split = any(":" in role for role in roles)
    records = []
    split_mismatch = 0
    for row in sheet_rows(book, path, strings, keep=keep):
        crop = _text(_cell(row, roles, "crop")).upper()
        planted = np.nan_to_num(_number(_cell(row, roles, "planted_acres")))
        crops[crop] += planted
        if not is_corn(crop):
            continue
        state_code, county_code = _text(_cell(row, roles, "state_code")), _text(_cell(row, roles, "county_code"))
        if not state_code.isdigit() or not county_code.isdigit():
            notes.append(f"skipped corn row without numeric state/county code: {row[:6]}")
            continue
        use_raw = _text(_cell(row, roles, "intended_use"))
        crop_type = _text(_cell(row, roles, "crop_type")).upper()
        labels[f"{crop_type}|{use_raw}"] += planted
        failed = _number(_cell(row, roles, "failed_acres"))
        if split:                                     # 2011: no failed total column, add the two halves
            failed = np.nansum([_number(_cell(row, roles, "failed_acres:I")),
                                _number(_cell(row, roles, "failed_acres:N"))])
        totals["planted_and_failed_all_types"] += planted + np.nan_to_num(failed)
        if normalise_use(use_raw) == "silage":
            totals["silage_all_types"] += planted
        if not is_field_corn(crop_type):
            totals["sweet_pop_planted"] += planted
            continue
        state_fips = FSA_TO_FIPS.get(state_code.zfill(2), state_code.zfill(2))
        base = {"state_fips": state_fips, "county_fips": state_fips + county_code.zfill(3),
                "state_label": _cell(row, roles, "state_name"),
                "county": _text(_cell(row, roles, "county_name")).upper(), "intended_use_raw": use_raw}
        if split:
            parts = []
            for practice in ("I", "N"):
                record = dict(base, irrigation=practice)
                for measure in MEASURES:
                    record[measure] = _number(_cell(row, roles, f"{measure}:{practice}"))
                parts.append(record)
            if abs(np.nansum([parts[0]["planted_acres"], parts[1]["planted_acres"]]) - planted) > 0.05:
                split_mismatch += 1
            records += parts
        else:
            record = dict(base, irrigation=_text(_cell(row, roles, "irrigation")).upper() or None)
            for measure in MEASURES:
                record[measure] = _number(_cell(row, roles, measure))
            records.append(record)
    table = pd.DataFrame.from_records(records, columns=["state_fips", "county_fips", "state_label", "county",
                                                        "intended_use_raw", "irrigation", *MEASURES])
    if split:
        notes.append(f"irrigated and non-irrigated columns melted into irrigation I and N rows "
                     f"({split_mismatch} field-corn rows where I + N differs from the planted total)")
    absent = [m for m in MEASURES if m not in roles and f"{m}:I" not in roles]
    if absent:
        notes.append(f"columns not in this file (left NaN): {', '.join(absent)}")
    uses_seen = {key.split("|", 1)[1] for key in labels}
    unmapped = sorted(label for label in uses_seen if label and _norm(label) not in USE_MAP)
    if unmapped:
        notes.append(f"intended-use labels not in USE_MAP, mapped to other: {unmapped}")
    if len(notes) > 6:
        notes = notes[:6] + [f"... {len(notes) - 6} more notes"]
    return table, {"crops": crops, "labels": labels, "totals": totals}, notes


def summarise(table: pd.DataFrame, crop_year: int, data_as_of: date | None, vintage: str) -> pd.DataFrame:
    """Sum crop types away: one row per county, intended use (raw label) and irrigation practice."""
    if table.empty:
        return table
    table = table.assign(intended_use=table["intended_use_raw"].map(normalise_use))
    keys = ["state_fips", "county_fips", "intended_use", "intended_use_raw", "irrigation"]
    names = table.groupby("county_fips")["county"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "")
    summed = table.groupby(keys, dropna=False)[MEASURES].sum(min_count=1).reset_index()
    summed["county"] = summed["county_fips"].map(names)
    labels = table.groupby("state_fips")["state_label"].agg(lambda s: _text(s.dropna().astype(str).iloc[0]).upper()
                                                            if s.notna().any() else "")
    summed["state"] = summed["state_fips"].map(lambda code: STATE_NAMES.get(code) or labels.get(code, ""))
    summed["crop_year"] = crop_year
    summed["data_as_of"] = pd.Timestamp(data_as_of) if data_as_of else pd.NaT
    summed["vintage"] = vintage
    return summed


def parse_archive(archive: Path) -> tuple[dict, pd.DataFrame]:
    """Parse one FSA archive: its fsa_files.csv row and its corn county rows (empty unless status is ok)."""
    info: dict = {"zip_name": archive.name, "sha256": _sha256(archive), "status": "ok", "reason": "", "notes": ""}
    empty = pd.DataFrame()
    try:
        book, inner, entry = open_workbook(archive)
    except (zipfile.BadZipFile, ValueError) as error:
        member, reason, entry = _corrupt_reason(archive, error)
        saved = zip_entry_time(entry)        # core.xml is out of reach; the first local header still has a time
        info.update(status="corrupt", reason=reason, inner_xlsx=member, kind="unknown", internal_saved=saved,
                    internal_saved_source=("zip entry date-time (local clock; read from the local file header)"
                                           if saved else "none: archive could not be opened"))
        crop_year = crop_year_from_name(member) or crop_year_from_name(archive.name)
        info["crop_year"] = crop_year
        if crop_year:
            when, precision = date_from_name(member, crop_year)
            if when is None:
                when, precision = date_from_name(archive.name, crop_year)
            info.update(data_as_of=when, vintage=vintage_label(when, crop_year),
                        date_source=f"file name ({precision}; archive could not be opened)")
            info["assumed_published"], info["published_source"], info["published_rule"] = published_date(when, saved)
        return info, empty
    info["inner_xlsx"] = inner
    saved, info["internal_saved_source"] = internal_saved(book, entry)
    info["internal_saved"] = saved
    crop_year = crop_year_from_name(inner) or crop_year_from_name(archive.name)
    info["crop_year"] = crop_year
    name_date, precision = date_from_name(inner, crop_year)
    if name_date is None:                              # e.g. 2016_fsa_acres_ddbk6438: try the archive name
        name_date, precision = date_from_name(archive.name, crop_year)

    strings = shared_strings(book)
    sheets = sheet_paths(book)
    first_sheet = next(iter(sheets.values()))
    stamp = sheet_date(first_rows(book, first_sheet, strings, 4), crop_year)
    county_name = next((n for n in sheets if n.strip().lower() == "county_data"), None)
    detail_name = county_name or next((n for n in sheets if n.strip().lower() == "sheet1"), None)
    notes: list[str] = []
    detail_head = first_rows(book, sheets[detail_name], strings, 25) if detail_name is not None else []
    stamp = stamp or sheet_date(detail_head, crop_year)

    # Data date: the sheet stamp first (it carries the day), then the file name.
    if stamp is not None:
        data_as_of, source = stamp, "sheet date stamp"
        if name_date is not None and name_date != stamp:
            notes.append(f"file name gives {name_date} ({precision} precision), sheet stamp {stamp}; stamp used")
    elif name_date is not None:
        data_as_of = name_date
        source = "file name (day)" if precision == "day" else "file name (month only; 1st of month assumed)"
    else:
        data_as_of, source = None, "none: no date in sheet or file name"
    final_in_name = "final" in inner.lower()
    info.update(data_as_of=data_as_of, date_source=source, vintage=vintage_label(data_as_of, crop_year, final_in_name))
    info["assumed_published"], info["published_source"], info["published_rule"] = published_date(data_as_of, saved)
    documented = DOCUMENTED_RELEASES.get(data_as_of) if data_as_of else None
    if documented is not None and saved is not None and saved.date() > documented:
        notes.append(f"workbook saved {saved.date()}, after its documented release {documented}; documented kept")

    header_index = find_header(detail_head)
    if header_index is None:
        # State-by-crop summary workbook: no county detail and no intended use. Keep its corn total as a check.
        info.update(kind="summary", status="summary_only",
                    reason="state-by-crop summary (all-use corn planted+failed and prevented, no county or "
                           "intended use); not loaded")
        info["pivot_corn_planted_and_failed"] = pivot_corn_total(book, first_sheet, strings)
        info["notes"] = "; ".join(notes)
        return info, empty

    info["kind"] = "detail"
    if county_name is not None and first_sheet != sheets[county_name]:
        info["pivot_corn_planted_and_failed"] = pivot_corn_total(book, first_sheet, strings)
    try:
        table, tallies, row_notes = corn_rows(book, sheets[detail_name], strings, detail_head[header_index])
    except (ValueError, KeyError, IndexError, ElementTree.ParseError) as error:
        info.update(status="unparsed", reason=f"county sheet could not be read: {error}", notes="; ".join(notes))
        return info, empty
    notes += row_notes
    _check_state_labels(table, notes)
    county = summarise(table, crop_year, data_as_of, info["vintage"])
    totals = tallies["totals"]

    def us(use: str | None = None) -> float:
        rows = county if use is None else county[county["intended_use"] == use]
        return float(rows["planted_acres"].sum()) if len(rows) else 0.0

    silage = county[(county["intended_use"] == "silage") & (county["planted_acres"] > 0)] if len(county) else county
    info.update(
        corn_rows=len(table),
        us_corn_planted=us(), us_grain_planted=us("grain"), us_silage_planted=us("silage"),
        us_corn_planted_and_failed=(float((county["planted_acres"].fillna(0) + county["failed_acres"].fillna(0)).sum())
                                    if len(county) else 0.0),
        counties_with_silage=int(silage["county_fips"].nunique()) if len(silage) else 0,
        us_sweet_pop_planted=float(totals["sweet_pop_planted"]),
        us_silage_all_types=float(totals["silage_all_types"]),
        us_all_types_planted_and_failed=float(totals["planted_and_failed_all_types"]),
        corn_crop_labels=json.dumps({k: round(v) for k, v in sorted(tallies["crops"].items())}),
        corn_type_use_labels=json.dumps({k: round(v, 1) for k, v in sorted(tallies["labels"].items())}),
        notes="; ".join(notes),
    )
    if county.empty:
        info.update(status="unparsed", reason="no field-corn rows found in the county sheet")
        return info, county
    grain_share = info["us_grain_planted"] / info["us_corn_planted"]
    if grain_share < MIN_GRAIN_SHARE:
        # Seen once (2011, data as of November): all-use totals are fine but the intended-use codes are shuffled.
        info.update(status="unusable", reason=f"intended-use column scrambled in the published file: grain is "
                                              f"{grain_share:.0%} of field-corn planted acres (about 95% in every "
                                              f"other file); left out of the county and state tables")
        return info, empty
    return info, county


def _check_state_labels(table: pd.DataFrame, notes: list[str]) -> None:
    """Note a state code whose name in the file does not resemble its expected name (a misread column).

    FSA abbreviates names in some years ("NO CAROLN", "PENSLVANA") and uses postal codes in others, so a
    close spelling or the postal code counts as a match.
    """
    pairs = table[["state_fips", "state_label"]].drop_duplicates()
    for code, label in pairs.itertuples(index=False):
        text, expected = _text(label).upper(), STATE_NAMES.get(code)
        if not text or expected is None:
            continue
        close = SequenceMatcher(None, text, expected).ratio() >= 0.6 or text.split()[0] == expected.split()[0]
        if POSTAL.get(text) != code and not close:
            notes.append(f"state code {code} ({expected}) labelled {text!r}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _corrupt_reason(archive: Path, error: Exception) -> tuple[str, str, tuple | None]:
    """The workbook name in the first zip entry, why the archive cannot be opened (for a truncated download,
    how much of the workbook arrived) and the entry's DOS date-time from its local file header."""
    with archive.open("rb") as handle:
        head = handle.read(30 + 512)
    if head[:4] == b"PK\x03\x04":
        dos_time, dos_date = int.from_bytes(head[10:12], "little"), int.from_bytes(head[12:14], "little")
        entry = ((dos_date >> 9) + 1980, (dos_date >> 5) & 0xF, dos_date & 0x1F,
                 dos_time >> 11, (dos_time >> 5) & 0x3F, (dos_time & 0x1F) * 2)
        compressed = int.from_bytes(head[18:22], "little")
        name_length = int.from_bytes(head[26:28], "little")
        member = head[30:30 + name_length].decode("cp437", "replace")
        size = archive.stat().st_size
        if compressed > size:
            return member, (f"truncated download: {size:,} of the {compressed:,} compressed bytes of the workbook "
                            f"({100 * size / compressed:.0f}%), no zip directory; download it again"), entry
        return member, f"zip directory missing or damaged ({error})", entry
    return "", f"not a zip archive ({error})", None


# --- all archives ----------------------------------------------------------------------------------------------

def parse_all(raw_dir: Path = RAW_DIR, workers: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    """fsa_files table and corn county table for every archive in ``raw_dir`` (parsed in parallel processes)."""
    archives = sorted(p for p in raw_dir.iterdir() if p.is_file() and p.suffix.lower() in (".zip", ".xlsx"))
    with ProcessPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(parse_archive, archives))
    files = pd.DataFrame([info for info, _ in results]).reindex(columns=FILE_COLUMNS)
    for column in ("data_as_of", "assumed_published", "internal_saved"):
        files[column] = pd.to_datetime(files[column])
    files["crop_year"] = files["crop_year"].astype("Int64")
    files = _label_duplicates(files)
    vintage = files.set_index("zip_name")["vintage"]
    parts = [county.assign(vintage=vintage[info["zip_name"]]) for info, county in results if len(county)]
    county = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    files = files.sort_values(["crop_year", "data_as_of", "kind", "zip_name"], na_position="first")
    return files.reset_index(drop=True), county


def _label_duplicates(files: pd.DataFrame) -> pd.DataFrame:
    """Give the later of two same-month detail files of one crop year a distinct vintage (e.g. aug and aug_2)."""
    files = files.copy()
    detail = files[(files["kind"] == "detail") & (files["status"] == "ok")].sort_values("data_as_of")
    for _, group in detail.groupby(["crop_year", "vintage"]):
        for rank, index in enumerate(group.index[1:], start=2):
            files.loc[index, "vintage"] = f"{files.loc[index, 'vintage']}_{rank}"
    return files


def county_table(county: pd.DataFrame) -> pd.DataFrame:
    """Final column order and compact types for fsa_corn_county.parquet."""
    columns = ["state_fips", "county_fips", "state", "county", "crop_year", "data_as_of", "vintage", "intended_use",
               "intended_use_raw", "irrigation", *MEASURES]
    out = county.reindex(columns=columns).sort_values(["crop_year", "data_as_of", "county_fips", "intended_use",
                                                       "intended_use_raw", "irrigation"], na_position="first")
    out["crop_year"] = out["crop_year"].astype("int16")
    out["data_as_of"] = pd.to_datetime(out["data_as_of"]).dt.date
    for column in ["state_fips", "state", "county", "vintage", "intended_use", "intended_use_raw", "irrigation"]:
        out[column] = out[column].astype("category")
    return out.reset_index(drop=True)


def state_table(county: pd.DataFrame) -> pd.DataFrame:
    """Corn acres summed by state, crop year, data date and intended use (NaN where a file lacks a measure)."""
    keys = ["state_fips", "state", "crop_year", "data_as_of", "vintage", "intended_use"]
    frame = county.assign(**{k: county[k].astype(str) if k in ("state_fips", "state", "vintage", "intended_use")
                             else county[k] for k in keys})
    out = frame.groupby(keys, dropna=False, observed=True)[MEASURES].sum(min_count=1).reset_index()
    return out.sort_values(["crop_year", "data_as_of", "state", "intended_use"]).reset_index(drop=True)


# --- the as-of rule --------------------------------------------------------------------------------------------

def usable_files(files: pd.DataFrame, asof: date | str, crop_year: int) -> pd.DataFrame:
    """Files a forecast made on ``asof`` for ``crop_year`` may use (parsed files only): in-season files of that
    crop year published by then, and files of earlier crop years published by then (history). A crop year's
    final file is never in-season input for that same year."""
    asof = pd.Timestamp(asof)
    ok = files[(files["status"] == "ok") & files["assumed_published"].notna()]
    published = pd.to_datetime(ok["assumed_published"])
    in_season = (ok["crop_year"] == crop_year) & ~ok["vintage"].astype(str).str.startswith("final")
    history = ok["crop_year"] < crop_year
    return ok[(published <= asof) & (in_season | history)]


def latest_file(files: pd.DataFrame, asof: date | str, crop_year: int) -> pd.Series | None:
    """The newest in-season file of ``crop_year`` published on or before ``asof`` (None if there is none)."""
    usable = usable_files(files, asof, crop_year)
    current = usable[usable["crop_year"] == crop_year]
    if current.empty:
        return None
    return current.sort_values("data_as_of").iloc[-1]


# --- validation ------------------------------------------------------------------------------------------------

# National corn silage-intended planted acres per file, keyed by data date, from
# DOCS/research/gap_fsa_ratio_baseline_2026.md: table 2.1 (final and November files) and section 2.2 (2025 and
# 2026 in-season files). The note counted every crop type of CORN with intended use Silage or Forage, so the check
# uses ``us_silage_all_types``; ``us_silage_planted`` (field corn only) differs by the sweet-corn and popcorn rows.
RESEARCH_SILAGE_US = {
    date(2017, 1, 4): 2660075, date(2018, 1, 4): 2672847, date(2019, 1, 28): 2789769, date(2020, 1, 2): 2578805,
    date(2021, 1, 5): 2831376, date(2022, 1, 3): 2778667, date(2023, 1, 3): 2642901, date(2024, 1, 2): 2842347,
    date(2025, 1, 2): 2785954, date(2026, 1, 5): 2919232,
    date(2017, 11, 1): 2667894, date(2018, 11, 1): 2782295, date(2019, 11, 1): 2547231, date(2020, 11, 2): 2758863,
    date(2021, 11, 9): 2776606, date(2022, 11, 1): 2638919, date(2023, 11, 1): 2835792, date(2024, 11, 1): 2780809,
    date(2025, 9, 2): 2934931, date(2025, 12, 1): 2885058,
    date(2026, 8, 1): 2763580, date(2026, 9, 1): 2845627, date(2026, 10, 1): 2866666, date(2026, 11, 5): 2885863,
}
# Same note, section 1: the 1 Aug 2026 file's corn planted plus failed, all crop types and uses (DTN: 94.765 M).
RESEARCH_ALL_CORN_PLANTED_FAILED = {date(2026, 8, 1): 94764645}
STATE_DROP_MIN_ACRES = 1000            # state declines are counted only where the earlier value is at least this


def nass_final_planted() -> pd.DataFrame:
    """NASS final corn planted acres by state and year, as kernelag.nass stores them (48 states, 2013 on)."""
    acres = pd.read_csv(data_dir() / "nass" / "corn_acres_state.csv")
    final = acres[(acres["series"] == "planted") & (acres["period"] == "final")]
    return final[["year", "state", "acres"]].rename(columns={"year": "crop_year", "acres": "nass_planted"})


def validate(files: pd.DataFrame, state: pd.DataFrame) -> dict:
    """Checks of the written tables against independent numbers and against themselves.

    1. National silage-intended acres per file vs the research note (same definition: all crop types).
    2. Parser vs FSA's own state-by-crop pivot sheet in the same workbook (corn planted plus failed).
    3. Field-corn planted acres in each vintage over NASS final planted for the crop year (US and state).
    4. Declines between consecutive vintages of one crop year (US and state), which should be rare and small.
    """
    ok = files[files["status"] == "ok"].copy()
    ok["data_as_of"] = pd.to_datetime(ok["data_as_of"]).dt.date

    research = []
    for _, row in ok.iterrows():
        when = row["data_as_of"]
        for label, table, column in (("silage, all types", RESEARCH_SILAGE_US, "us_silage_all_types"),
                                     ("corn planted+failed, all types", RESEARCH_ALL_CORN_PLANTED_FAILED,
                                      "us_all_types_planted_and_failed")):
            if when in table:
                research.append({"data_as_of": str(when), "measure": label, "parsed": round(row[column]),
                                 "research": table[when], "rel_diff": row[column] / table[when] - 1,
                                 "field_corn_silage": round(row["us_silage_planted"])})
    research = pd.DataFrame(research)

    pivot = ok.dropna(subset=["pivot_corn_planted_and_failed"])
    pivot_diff = (pivot["us_all_types_planted_and_failed"] / pivot["pivot_corn_planted_and_failed"] - 1).abs()
    # 2009-2011: separate state-summary workbooks of the same vintage (an unusable detail file's all-use totals
    # are still comparable: only its intended-use column is scrambled).
    summary = files[files["kind"] == "summary"][["crop_year", "vintage", "zip_name", "pivot_corn_planted_and_failed"]]
    detail = files[(files["kind"] == "detail") & files["status"].isin(["ok", "unusable"])]
    pairs = summary.merge(detail[["crop_year", "vintage", "us_all_types_planted_and_failed"]],
                          on=["crop_year", "vintage"], how="inner")
    pairs["rel_diff"] = pairs["us_all_types_planted_and_failed"] / pairs["pivot_corn_planted_and_failed"] - 1

    nass = nass_final_planted()
    by_state = (state.groupby(["crop_year", "data_as_of", "vintage", "state"])["planted_acres"].sum()
                .reset_index())
    merged = by_state.merge(nass, on=["crop_year", "state"], how="inner")
    us = merged.groupby(["crop_year", "vintage"])[["planted_acres", "nass_planted"]].sum()
    coverage_us = (us["planted_acres"] / us["nass_planted"]).unstack("vintage")
    coverage_us = coverage_us.reindex(columns=[v for v in ["aug", "aug_2", "sep", "oct", "nov", "dec", "final"]
                                               if v in coverage_us.columns])
    finals = merged[merged["vintage"] == "final"].assign(
        coverage=lambda f: f["planted_acres"] / f["nass_planted"])

    path = ok[ok["kind"] == "detail"].sort_values(["crop_year", "data_as_of"])
    us_drops = []
    for year, group in path.groupby("crop_year"):
        for column in ("us_corn_planted", "us_silage_planted"):
            values, dates = group[column].to_numpy(), group["data_as_of"].to_numpy()
            for before, after, when in zip(values[:-1], values[1:], dates[1:]):
                if after < before:
                    us_drops.append({"crop_year": year, "measure": column, "data_as_of": str(when),
                                     "change_pct": 100 * (after / before - 1)})
    state_sorted = state.assign(silage=np.where(state["intended_use"] == "silage", state["planted_acres"], 0.0))
    per_file = (state_sorted.groupby(["crop_year", "state", "data_as_of"])[["planted_acres", "silage"]].sum()
                .reset_index().sort_values(["crop_year", "state", "data_as_of"]))
    state_changes = []
    for column in ("planted_acres", "silage"):
        earlier = per_file.groupby(["crop_year", "state"])[column].shift()
        change = per_file[column] / earlier - 1
        valid = earlier >= STATE_DROP_MIN_ACRES
        state_changes.append({"measure": column, "steps": int(valid.sum()),
                              "declines": int((valid & (change < 0)).sum()),
                              "declines_over_1pct": int((valid & (change < -0.01)).sum()),
                              "declines_over_5pct": int((valid & (change < -0.05)).sum()),
                              "largest_decline_pct": float(100 * change[valid].min())})
    return {
        "research": research,
        "research_max_abs_rel_diff": float(research["rel_diff"].abs().max()) if len(research) else None,
        "pivot_max_abs_rel_diff": float(pivot_diff.max()) if len(pivot_diff) else None,
        "pivot_files_compared": len(pivot_diff),
        "summary_vs_detail": pairs,
        "coverage_us": coverage_us,
        "coverage_state": finals,
        "us_drops": pd.DataFrame(us_drops),
        "state_changes": pd.DataFrame(state_changes),
    }


def print_validation(result: dict) -> None:
    """Plain-text summary of ``validate``."""
    print("1) research note totals (all crop types) vs this parser:")
    print(result["research"].to_string(index=False, float_format=lambda v: f"{v:.2e}"))
    print(f"   max |relative difference| = {result['research_max_abs_rel_diff']:.2e}")
    print(f"2) parser vs FSA's own pivot sheet, corn planted+failed ({result['pivot_files_compared']} workbooks): "
          f"max |relative difference| = {result['pivot_max_abs_rel_diff']:.2e}")
    pairs = result["summary_vs_detail"]
    if len(pairs):
        print(f"   separate summary workbooks vs detail workbooks ({len(pairs)} pairs, 2009-2011): "
              f"max |relative difference| = {pairs['rel_diff'].abs().max():.2e}")
    print("3) field-corn planted / NASS final planted, 48 states, by vintage:")
    print(result["coverage_us"].to_string(float_format=lambda v: f"{v:.3f}"))
    coverage = result["coverage_state"]
    summary = coverage.groupby("state")["coverage"].agg(["min", "median", "max"]).sort_values("median")
    print("   final-file state coverage, five lowest and five highest medians:")
    print(pd.concat([summary.head(5), summary.tail(5)]).to_string(float_format=lambda v: f"{v:.3f}"))
    print("4) declines between consecutive vintages, US:")
    drops = result["us_drops"]
    print(drops.to_string(index=False, float_format=lambda v: f"{v:.2f}") if len(drops) else "   none")
    print(f"   by state (earlier value at least {STATE_DROP_MIN_ACRES:,} acres):")
    print(result["state_changes"].to_string(index=False, float_format=lambda v: f"{v:.1f}"))


# --- command line ----------------------------------------------------------------------------------------------

def write_outputs(files: pd.DataFrame, county: pd.DataFrame, out_dir: Path) -> list[Path]:
    """Write the three tables and return their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    county = county_table(county)
    state = state_table(county)
    paths = [out_dir / "fsa_files.csv", out_dir / "fsa_corn_county.parquet", out_dir / "fsa_corn_state.csv"]
    files.to_csv(paths[0], index=False, lineterminator="\n")
    county.to_parquet(paths[1], index=False, compression="zstd")
    state.to_csv(paths[2], index=False, lineterminator="\n", float_format="%.2f")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--raw", type=Path, default=RAW_DIR, help="folder with the FSA archives")
    parser.add_argument("--workers", type=int, default=min(12, os.cpu_count() or 1))
    parser.add_argument("--validate", action="store_true", help="only check the written tables")
    args = parser.parse_args()
    out_dir = data_dir() / "fsa"
    if not args.validate:
        files, county = parse_all(args.raw, args.workers)
        for path in write_outputs(files, county, out_dir):
            record_in_manifest(path, SOURCE_URL)
            print(f"wrote {path.relative_to(REPO)} ({path.stat().st_size / 1e6:.1f} MB)")
        print(files["status"].value_counts().to_string())
    files = pd.read_csv(out_dir / "fsa_files.csv")
    state = pd.read_csv(out_dir / "fsa_corn_state.csv")
    print_validation(validate(files, state))


if __name__ == "__main__":
    main()
