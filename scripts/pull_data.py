#!/usr/bin/env python3
"""Pull public context data into data/ and keep the folder ready for git.

Standard library only, so it runs on a laptop and on Keeboh without setup.

    python3 scripts/pull_data.py drought      US Drought Monitor: weekly share of each state and county in drought
    python3 scripts/pull_data.py weather      NOAA daily county averages -> heat units, rain and frost dates
    python3 scripts/pull_data.py rma          RMA crop insurance, corn only: cause of loss; insured acres by type
    python3 scripts/pull_data.py quickstats   NASS Quick Stats in-season series (needs NASS_QUICKSTATS_API_KEY)
    python3 scripts/pull_data.py manifest     refresh data/DATA_MANIFEST.tsv and flag files above the repo's 30 MB limit
    python3 scripts/pull_data.py all          every pull, then the manifest

Outputs that already exist are skipped; --force pulls them again. Years: --start-year (2000) to --end-year (this year).
What each folder holds is described in data/README.md.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import gzip
import hashlib
import io
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from kernelag.paths import secret  # noqa: E402  (reads the key from the environment or .env; never prints it)

DATA = REPO / "data"
MANIFEST = DATA / "DATA_MANIFEST.tsv"
MANIFEST_HEADER = "path\tbytes\tsha256\tsource_url\tmade_by\tutc"
GUARD_BYTES = 30_000_000        # scripts/guard.sh rejects larger files
MAX_PLAIN_BYTES = 25_000_000    # tables above this are written as .csv.gz; so are the bulky per-state and per-year sets
USER_AGENT = "Kernel-HackTheHarvest/1.0 (public data pull; github.com/Severynson/Hack-the-Harvest)"

# Postal code -> FIPS code. NOAA's county files use their own state numbers, so FIPS is rebuilt from the postal code.
STATES = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11",
    "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30",
    "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
}

problems: list[str] = []            # everything that did not arrive, printed at the end


# --- shared helpers -----------------------------------------------------------

def fetch(url: str, accept: str | None = None, timeout: int = 60, tries: int = 4) -> bytes:
    """GET a URL. The timeout is per read, so a stalled connection fails fast and is retried."""
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code in (400, 404) or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == tries - 1:
                raise
        time.sleep(2 + 3 * attempt)
    raise RuntimeError("unreachable")


def existing(path: Path) -> Path | None:
    """The file, or its gzipped form, if either is already on disk."""
    for candidate in (path, path.with_name(path.name + ".gz")):
        if candidate.exists():
            return candidate
    return None


def gzip_copy(source: Path, target: Path) -> None:
    """Gzip with no timestamp, so the same content always gives the same bytes."""
    with source.open("rb") as raw, target.open("wb") as out, gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as packed:
        shutil.copyfileobj(raw, packed)


def save_csv(path: Path, header: list[str], rows: list[list], packed: bool = False) -> Path:
    """Write a table as plain CSV, or gzipped when asked to or when it is above the plain-file limit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    with part.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    for old in (path, path.with_name(path.name + ".gz")):
        old.unlink(missing_ok=True)
    if packed or part.stat().st_size > MAX_PLAIN_BYTES:
        final = path.with_name(path.name + ".gz")
        gzip_copy(part, final)
        part.unlink()
    else:
        final = path
        part.replace(final)
    print(f"  saved {final.relative_to(REPO)}  rows {len(rows)}  {final.stat().st_size / 1e6:.2f} MB", flush=True)
    return final


# --- US Drought Monitor --------------------------------------------------------

USDM_API = "https://usdmdataservices.unl.edu/api"


def usdm_rows(level: str, aoi: str, start: date, end: date) -> tuple[list[str], list[list[str]]]:
    url = (f"{USDM_API}/{level}Statistics/GetDroughtSeverityStatisticsByAreaPercent?aoi={aoi}"
           f"&startdate={start.month}/{start.day}/{start.year}&enddate={end.month}/{end.day}/{end.year}&statisticsType=1")
    table = list(csv.reader(io.StringIO(fetch(url, accept="text/csv").decode("utf-8-sig"))))
    return (table[0], table[1:]) if table else ([], [])


def pull_drought(args) -> None:
    """Weekly percent of area in each drought class (None, D0 to D4; cumulative), from 2000."""
    first, last = date(max(args.start_year, 2000), 1, 1), min(date(args.end_year, 12, 31), date.today())
    folder = DATA / "drought"

    state_file = folder / f"usdm_state_weekly_{first.year}_{last.year}.csv"
    if args.force or not existing(state_file):
        header, rows = [], []
        for abbr, fips in STATES.items():
            try:
                head, part = usdm_rows("State", fips, first, last)
            except Exception as error:  # noqa: BLE001  (one state failing must not stop the rest)
                problems.append(f"drought state {abbr}: {error}")
                continue
            header = header or head
            rows += part
        rows.sort(key=lambda r: (r[0], r[1]))
        if rows:
            save_csv(state_file, header, rows)

    def county(abbr: str) -> None:
        target = folder / "county_weekly" / f"usdm_county_weekly_{abbr}_{first.year}_{last.year}.csv"
        if not args.force and existing(target):
            return
        header, rows = [], []
        for block_start in range(first.year, last.year + 1, 9):   # nine-year blocks keep each reply small
            block_end = min(date(block_start + 8, 12, 31), last)
            head, part = usdm_rows("County", abbr, date(block_start, 1, 1), block_end)
            header = header or head
            rows += part
        rows = sorted({tuple(r) for r in rows}, key=lambda r: (r[0], r[1]))   # a week that spans two blocks arrives twice
        if rows:
            save_csv(target, header, rows, packed=True)
        else:
            problems.append(f"drought county {abbr}: no rows returned")

    with ThreadPoolExecutor(3) as pool:
        for abbr, outcome in zip(STATES, pool.map(lambda a: _safely(county, a), STATES)):
            if outcome:
                problems.append(f"drought county {abbr}: {outcome}")


def _safely(function, *call_args) -> str | None:
    try:
        function(*call_args)
    except Exception as error:  # noqa: BLE001
        return f"{type(error).__name__}: {error}"
    return None


# --- Weather: NOAA nClimGrid-Daily county averages ------------------------------

NOAA = "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages"
MISSING = -900.0          # the files mark days that do not exist, or have no data, with -999.99
GDD_BASE, GDD_CAP = 10.0, 30.0     # corn heat units: 50 F base, 86 F cap
HOT_DAY, FROST, HARD_FREEZE = 32.0, 0.0, -2.2   # degrees C (90 F, 32 F, 28 F)
MONTH_COLUMNS = ["fips", "state", "county", "year", "month", "days", "tmax_mean_c", "tmin_mean_c", "prcp_mm",
                 "gdd_c", "hot_days", "frost_days"]
SEASON_COLUMNS = ["fips", "state", "county", "year", "data_through", "last_spring_frost_doy", "first_fall_frost_doy",
                  "first_hard_freeze_doy", "gdd_may_sep_c", "prcp_may_sep_mm"]


def noaa_month(year: int, month: int, variable: str) -> dict[tuple[str, str, str], list[float | None]]:
    """(fips, state, county) -> one value per day for one variable and month; empty if not published yet."""
    url = f"{NOAA}/{year}/{variable}-{year}{month:02d}-cty-scaled.csv"
    try:
        text = fetch(url).decode("latin-1")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {}
        raise
    out = {}
    for line in text.splitlines():
        fields = [f.strip() for f in line.split(",")]
        if len(fields) < 37 or fields[0] != "cty":
            continue
        abbr, _, county = ",".join(fields[2:-34]).partition(":")
        if abbr.strip() not in STATES:
            continue
        fips = STATES[abbr.strip()] + fields[1][-3:]
        days = calendar.monthrange(year, month)[1]
        values = [float(v) for v in fields[-31:][:days]]
        out[(fips, abbr.strip(), county.strip())] = [v if v > MISSING else None for v in values]
    return out


def gdd(tmax: float, tmin: float) -> float:
    high, low = min(max(tmax, GDD_BASE), GDD_CAP), min(max(tmin, GDD_BASE), GDD_CAP)
    return (high + low) / 2 - GDD_BASE


def pull_weather(args) -> None:
    """Daily tmax, tmin and rain per county, reduced to one row per county-month and one per county-year."""
    folder = DATA / "weather"
    for year in range(max(args.start_year, 1951), min(args.end_year, date.today().year) + 1):
        month_file = folder / "county_month" / f"county_month_{year}.csv"
        season_file = folder / "county_season" / f"county_season_{year}.csv"
        if not args.force and existing(month_file) and existing(season_file):
            continue
        jobs = [(year, month, variable) for month in range(1, 13) for variable in ("tmax", "tmin", "prcp")]
        try:
            with ThreadPoolExecutor(6) as pool:
                tables = dict(zip(jobs, pool.map(lambda job: noaa_month(*job), jobs)))
        except Exception as error:  # noqa: BLE001
            problems.append(f"weather {year}: {type(error).__name__}: {error}")
            continue
        month_rows, season = [], {}
        for month in range(1, 13):
            tmax, tmin, prcp = (tables[(year, month, v)] for v in ("tmax", "tmin", "prcp"))
            for key in sorted(tmax.keys() & tmin.keys() & prcp.keys()):
                days = [(d + 1, hi, lo, rain) for d, (hi, lo, rain) in enumerate(zip(tmax[key], tmin[key], prcp[key]))
                        if hi is not None and lo is not None and rain is not None]
                if not days:
                    continue
                heat = sum(gdd(hi, lo) for _, hi, lo, _ in days)
                rain_total = sum(rain for *_, rain in days)
                month_rows.append([key[0], key[1], key[2], year, month, len(days),
                                   round(sum(hi for _, hi, _, _ in days) / len(days), 2),
                                   round(sum(lo for _, _, lo, _ in days) / len(days), 2),
                                   round(rain_total, 2), round(heat, 1),
                                   sum(hi >= HOT_DAY for _, hi, _, _ in days), sum(lo <= FROST for _, _, lo, _ in days)])
                s = season.setdefault(key, {"through": None, "spring": None, "fall": None, "hard": None, "gdd": 0.0, "rain": 0.0})
                for day, _, lo, _ in days:
                    doy = date(year, month, day).timetuple().tm_yday
                    s["through"] = date(year, month, day).isoformat()
                    if lo <= FROST and month <= 6:
                        s["spring"] = doy
                    if lo <= FROST and month >= 8 and s["fall"] is None:
                        s["fall"] = doy
                    if lo <= HARD_FREEZE and month >= 8 and s["hard"] is None:
                        s["hard"] = doy
                if 5 <= month <= 9:
                    s["gdd"] += heat
                    s["rain"] += rain_total
        if not month_rows:
            problems.append(f"weather {year}: no county files published")
            continue
        month_rows.sort(key=lambda r: (r[0], r[4]))
        save_csv(month_file, MONTH_COLUMNS, month_rows)
        blank = lambda v: "" if v is None else v  # noqa: E731
        save_csv(season_file, SEASON_COLUMNS,
                 [[k[0], k[1], k[2], year, s["through"], blank(s["spring"]), blank(s["fall"]), blank(s["hard"]),
                   round(s["gdd"], 1), round(s["rain"], 1)] for k, s in sorted(season.items())])


# --- RMA crop insurance (corn only) ---------------------------------------------

RMA = "https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business"
CORN_CODE = "0041"
# Column names follow RMA's record layouts in the same folders:
# COL_Summary_of_Business_with_Month_All_Years.pdf and SOBTPU_External_All_Years.pdf.
CAUSE_OF_LOSS_COLUMNS = [
    "commodity_year", "state_code", "state_abbreviation", "county_code", "county_name", "commodity_code",
    "commodity_name", "insurance_plan_code", "insurance_plan_abbreviation", "coverage_category", "stage_code",
    "cause_of_loss_code", "cause_of_loss_description", "month_of_loss", "month_of_loss_name", "year_of_loss",
    "policies_earning_premium", "policies_indemnified", "net_planted_quantity", "net_endorsed_acres", "liability",
    "total_premium", "producer_paid_premium", "subsidy", "state_private_subsidy", "additional_subsidy",
    "efa_premium_discount", "net_determined_quantity", "indemnity_amount", "loss_ratio",
]
TYPE_PRACTICE_COLUMNS = [
    "commodity_year", "state_code", "state_name", "state_abbreviation", "county_code", "county_name",
    "commodity_code", "commodity_name", "insurance_plan_code", "insurance_plan_abbreviation", "coverage_type_code",
    "coverage_level_percent", "delivery_id", "type_code", "type_name", "practice_code", "practice_name",
    "unit_structure_code", "unit_structure_name", "net_reporting_level_amount", "reporting_level_type",
    "liability_amount", "total_premium_amount", "subsidy_amount", "indemnity_amount", "loss_ratio",
    "endorsed_commodity_reporting_level_amount",
]
RMA_FILES = {   # folder -> (remote folder, file stem, first year, columns, position of the commodity code)
    "cause_of_loss_corn": ("cause_of_loss", "colsom", 1989, CAUSE_OF_LOSS_COLUMNS, 5),
    "insured_by_type_corn": ("state_county_crop", "sobtpu", 1999, TYPE_PRACTICE_COLUMNS, 6),
}


def rma_corn(url: str, columns: list[str], code_at: int) -> tuple[list[str], list[list[str]]]:
    """Corn rows of one yearly RMA file. The files are pipe-delimited with no header row."""
    archive = zipfile.ZipFile(io.BytesIO(fetch(url)))
    rows, width = [], len(columns)
    with archive.open(archive.namelist()[0]) as raw:
        for line in io.TextIOWrapper(raw, encoding="latin-1", newline=None):   # some years end lines with a bare CR
            fields = [f.strip() for f in line.rstrip("\n").split("|")]
            if len(fields) > code_at and fields[code_at] == CORN_CODE:
                rows.append(fields)
                width = max(width, len(fields))
    header = columns + [f"extra_{i}" for i in range(1, width - len(columns) + 1)]
    widths = {len(r) for r in rows}
    if widths and widths != {len(columns)}:
        problems.append(f"rma {url.rsplit('/', 1)[1]}: rows have {sorted(widths)} fields, the layout lists {len(columns)}")
    return header, [r + [""] * (width - len(r)) for r in rows]


def pull_rma(args) -> None:
    for folder, (remote, stem, first_year, columns, code_at) in RMA_FILES.items():
        def one(year: int, folder=folder, remote=remote, stem=stem, columns=columns, code_at=code_at) -> None:
            target = DATA / "rma" / folder / f"{stem}_corn_{year}.csv"
            if not args.force and existing(target):
                return
            url = f"{RMA}/{remote}/{stem}_{year}.zip"
            header, rows = rma_corn(url, columns, code_at)
            if rows:
                save_csv(target, header, rows, packed=True)
            else:
                problems.append(f"rma {stem} {year}: no corn rows")

        years = list(range(max(args.start_year, first_year), min(args.end_year, date.today().year) + 1))
        with ThreadPoolExecutor(2) as pool:
            for year, outcome in zip(years, pool.map(lambda y: _safely(one, y), years)):
                if outcome:
                    problems.append(f"rma {stem} {year}: {outcome}")


# --- NASS Quick Stats in-season series -------------------------------------------

QUICKSTATS_API = "https://quickstats.nass.usda.gov/api/api_GET/"
QUICKSTATS_KEYS = ("NASS_QUICKSTATS_API_KEY", "NASS_API_KEY")
QUICKSTATS_DIR = DATA / "Quickstats Data"     # the folder name kernelag.state_panel reads
# Same columns as the team's earlier downloads (download_hack_the_harvest_quickstats.py), plus week_ending.
QUICKSTATS_FIELDS = [
    "source_desc", "sector_desc", "group_desc", "commodity_desc", "class_desc", "prodn_practice_desc",
    "util_practice_desc", "statisticcat_desc", "unit_desc", "short_desc", "domain_desc", "domaincat_desc",
    "agg_level_desc", "state_alpha", "state_name", "state_fips_code", "county_name", "county_code", "asd_desc",
    "year", "freq_desc", "reference_period_desc", "Value", "CV (%)", "load_time", "week_ending",
]
# File stem -> exact Quick Stats filters (item names checked with get_param_values on 2026-11-15). State level, survey.
QUICKSTATS_SERIES = {
    "corn_progress_weekly": {"commodity_desc": "CORN", "statisticcat_desc": "PROGRESS", "util_practice_desc__NE": "SILAGE"},
    "corn_silage_harvest_progress_weekly": {"commodity_desc": "CORN", "statisticcat_desc": "PROGRESS", "util_practice_desc": "SILAGE"},
    "corn_condition_weekly": {"commodity_desc": "CORN", "statisticcat_desc": "CONDITION"},
    "pasture_condition_weekly": {"commodity_desc": "PASTURELAND", "statisticcat_desc": "CONDITION"},
    "hay_production": {"commodity_desc": "HAY", "statisticcat_desc": "PRODUCTION"},
    "hay_stocks": {"commodity_desc": "HAY", "statisticcat_desc": "STOCKS"},
    "hay_price_received": {"commodity_desc": "HAY", "statisticcat_desc": "PRICE RECEIVED"},
    "milk_price_received": {"commodity_desc": "MILK", "statisticcat_desc": "PRICE RECEIVED"},
    "cattle_on_feed": {"commodity_desc": "CATTLE", "prodn_practice_desc": "ON FEED"},
}


def quickstats_year(filters: dict, year: int, key: str) -> list[dict]:
    query = urllib.parse.urlencode(dict(filters, agg_level_desc="STATE", source_desc="SURVEY", year=year, key=key, format="CSV"))
    try:
        return list(csv.DictReader(io.StringIO(fetch(QUICKSTATS_API + "?" + query, timeout=120).decode("utf-8"))))
    except urllib.error.HTTPError as error:
        if error.code == 400:      # Quick Stats answers "bad request" when a year has no rows
            return []
        raise RuntimeError(f"HTTP {error.code}") from None     # never echo the URL: it carries the key


def pull_quickstats(args) -> None:
    key = next((secret(name) for name in QUICKSTATS_KEYS if secret(name)), "")
    if not key:
        problems.append("quickstats: no key; set NASS_QUICKSTATS_API_KEY in the environment or in .env")
        return
    first, last = args.start_year, min(args.end_year, date.today().year)
    for stem, filters in QUICKSTATS_SERIES.items():
        target = QUICKSTATS_DIR / f"{stem}_state_{first}_{last}.csv"
        if not args.force and existing(target):
            continue
        rows, failed = [], False
        for year in range(first, last + 1):
            try:
                records = quickstats_year(filters, year, key)
            except Exception as error:  # noqa: BLE001
                problems.append(f"quickstats {stem} {year}: {error}")
                failed = True
                continue
            if len(records) >= 50000:
                problems.append(f"quickstats {stem} {year}: reply hit the 50,000-row limit and may be cut short")
            rows += [[record.get(field, "") for field in QUICKSTATS_FIELDS] for record in records]
            time.sleep(0.2)
        if rows and not failed:
            save_csv(target, QUICKSTATS_FIELDS, rows)
        elif not rows:
            problems.append(f"quickstats {stem}: no rows")


# --- Manifest ------------------------------------------------------------------------

SKIP_NAMES = {".DS_Store", "README.md", MANIFEST.name}


def source_for(relative: str) -> str:
    """Where a data file came from, worked out from its path so the manifest never depends on run order."""
    name = relative.rsplit("/", 1)[1]
    stem = name.split(".csv")[0]
    if relative.startswith("data/drought/county_weekly/"):
        return f"{USDM_API}/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi={stem.split('_')[3]}"
    if relative.startswith("data/drought/"):
        return f"{USDM_API}/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent"
    if relative.startswith("data/weather/"):
        return f"{NOAA}/{stem.rsplit('_', 1)[1]}/ (tmax, tmin, prcp; *-cty-scaled.csv; reduced by scripts/pull_data.py)"
    for folder, (remote, prefix, *_rest) in RMA_FILES.items():
        if relative.startswith(f"data/rma/{folder}/"):
            return f"{RMA}/{remote}/{prefix}_{stem.rsplit('_', 1)[1]}.zip (corn rows only)"
    if relative.startswith("data/Quickstats Data/"):
        for series, filters in QUICKSTATS_SERIES.items():
            if stem.startswith(series + "_state_"):
                return f"{QUICKSTATS_API} ({', '.join(f'{k}={v}' for k, v in filters.items())}; state, survey)"
        return f"{QUICKSTATS_API} (download_hack_the_harvest_quickstats.py)"
    return ""


def data_files() -> list[Path]:
    return sorted(p for p in DATA.rglob("*") if p.is_file() and p.name not in SKIP_NAMES and not p.name.endswith(".part"))


def write_manifest(args) -> None:
    """One row per file under data/; rows for files that are not on this machine are kept."""
    lines = MANIFEST.read_text(encoding="utf-8").splitlines() if MANIFEST.exists() else [MANIFEST_HEADER]
    old = {line.split("\t")[0]: line.split("\t") for line in lines[1:] if line.strip()}
    stamp, agent = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), os.environ.get("AGENT_ID", "unknown")
    for path in data_files():
        relative = path.relative_to(REPO).as_posix()
        size, digest = path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()
        row = old.get(relative)
        if row and len(row) >= 3 and row[1] == str(size) and row[2] == digest:
            continue
        source = source_for(relative) or (row[3] if row and len(row) > 3 else "")
        old[relative] = [relative, str(size), digest, source, agent, stamp]
        if size > GUARD_BYTES:
            problems.append(f"manifest: {relative} is {size / 1e6:.0f} MB, above the 30 MB limit; keep it out of git")
    MANIFEST.write_text("\n".join([MANIFEST_HEADER] + ["\t".join(row) for row in old.values()]) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"  manifest: {len(old)} rows")


COMMANDS = {"drought": pull_drought, "weather": pull_weather, "rma": pull_rma, "quickstats": pull_quickstats,
            "manifest": write_manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=[*COMMANDS, "all"])
    parser.add_argument("--start-year", type=int, default=2000)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    parser.add_argument("--force", action="store_true", help="pull again even if the output exists")
    args = parser.parse_args()
    steps = ["drought", "weather", "rma", "quickstats", "manifest"] if args.command == "all" else [args.command]
    for step in steps:
        print(f"== {step}", flush=True)
        COMMANDS[step](args)
    if problems:
        print(f"== {len(problems)} problem(s)")
        for line in problems:
            print("  " + line)
        sys.exit(1)


if __name__ == "__main__":
    main()
