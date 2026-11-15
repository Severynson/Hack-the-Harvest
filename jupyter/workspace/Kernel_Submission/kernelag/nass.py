"""Official corn acreage: one tidy table, and the baselines Kernel has to beat.

Input: the organizers' Quick Stats file (``02_QuickStats/corn_grain_silage_acres_2012_2025.csv``).
It mixes final figures with NASS's own in-season rows, and plain totals with
irrigated and organic sub-rows. This module keeps only what the acreage target needs.

Outputs (under ``data/nass/``):
    corn_acres_state.csv    year, state, state_ansi, series, period, acres
    corn_acres_county.csv   year, state_ansi, county_ansi, county, series, acres (census years)
    baselines.csv           how far off NASS's forecasts and "same as last year" were

``series`` is planted, grain or silage. ``period`` is ``final`` or the month of an
in-season NASS report (mar, jun, aug, sep, oct, nov).

The kit has no state rows for the census years 2012, 2017 and 2022. The team's Quick Stats
downloads in ``data/Quickstats Data/`` (2015 to 2025) fill 2017 and 2022 with no key. With
``NASS_QUICKSTATS_API_KEY`` in ``.env`` any year still missing (2012) is fetched from the API.

Run: ``python -m kernelag.nass``            (baselines stop at 2024; 2025 is the scoring year)
"""

from __future__ import annotations

import argparse

import pandas as pd

from kernelag.nass_reports import season_rows
from kernelag.paths import data_dir, kit_dir, record_in_manifest, secret

KIT_FILE = "02_QuickStats/corn_grain_silage_acres_2012_2025.csv"
SOURCE_URL = "https://quickstats.nass.usda.gov/"
API_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
API_KEY_NAME = "NASS_QUICKSTATS_API_KEY"   # free key by email form; kept in .env
TEAM_FOLDER = "Quickstats Data"
TEAM_FILES = ["corn_planted_acres", "corn_grain_harvested_acres", "corn_silage_harvested_acres"]

# Quick Stats API column names -> the kit's column names.
KIT_NAMES = {
    "year": "year", "agg_level_desc": "aggregation_level", "state_name": "state_name",
    "state_ansi": "state_ansi", "short_desc": "short_description",
    "reference_period_desc": "reference_period", "Value": "value",
    "source_desc": "source", "domain_desc": "domain",
}

# The three plain totals. Irrigated, non-irrigated and organic sub-rows are left out.
SERIES = {
    "CORN - ACRES PLANTED": "planted",
    "CORN, GRAIN - ACRES HARVESTED": "grain",
    "CORN, SILAGE - ACRES HARVESTED": "silage",
}

# Quick Stats reference periods -> the month of the report they come from.
PERIODS = {
    "YEAR": "final",
    "YEAR - MAR ACREAGE": "mar",
    "YEAR - JUN ACREAGE": "jun",
    "YEAR - AUG FORECAST": "aug",
    "YEAR - AUG ACREAGE": "aug",
    "YEAR - SEP FORECAST": "sep",
    "YEAR - OCT FORECAST": "oct",
    "YEAR - OCT ACREAGE": "oct",
    "YEAR - NOV FORECAST": "nov",
}

# 2025 is the organizers' scoring year: nothing is fitted or reported on it before the final run.
LAST_BASELINE_YEAR = 2024


def load_kit() -> pd.DataFrame:
    """The organizers' file as text columns, exactly as NASS published the values."""
    return pd.read_csv(kit_dir() / KIT_FILE, dtype=str, keep_default_na=False)


def years_without_state_rows(raw: pd.DataFrame) -> list[int]:
    """Years where the kit has no state survey rows (it holds county rows only in census years)."""
    survey = raw[(raw["aggregation_level"] == "STATE") & (raw["source"] == "SURVEY")]
    have = set(survey["year"].astype(int))
    years = raw["year"].astype(int)
    return [year for year in range(years.min(), years.max() + 1) if year not in have]


def fetch_state_survey(years: list[int], key: str) -> pd.DataFrame:
    """State survey rows for the three plain series, straight from the Quick Stats API.

    Returned with the kit's column names so it can be stacked under the kit file.
    """
    import requests

    rows = []
    for year in years:
        for item in SERIES:
            params = {
                "key": key, "format": "JSON", "source_desc": "SURVEY", "commodity_desc": "CORN",
                "agg_level_desc": "STATE", "year": year, "short_desc": item,
            }
            response = requests.get(API_URL, params=params, timeout=60)
            if response.status_code != 200:   # never echo the URL: it carries the key
                raise RuntimeError(f"Quick Stats returned HTTP {response.status_code} for {year}, {item}")
            rows.extend(response.json().get("data", []))
    fetched = pd.DataFrame(rows).astype(str).rename(columns=KIT_NAMES)
    return fetched[list(KIT_NAMES.values())] if len(fetched) else fetched


def team_folder_state_rows() -> pd.DataFrame:
    """State survey rows from the team's Quick Stats downloads, with the kit's column names.

    These files use the API's column names and call the state code ``state_fips_code``.
    Empty if the folder is not there.
    """
    parts = []
    for stem in TEAM_FILES:
        path = data_dir() / TEAM_FOLDER / f"{stem}_state_2015_2025.csv"
        if not path.exists():
            continue
        rows = pd.read_csv(path, dtype=str, keep_default_na=False)
        rows = rows[rows["source_desc"] == "SURVEY"].rename(columns={"state_fips_code": "state_ansi"})
        parts.append(rows.rename(columns=KIT_NAMES)[list(KIT_NAMES.values())])
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=list(KIT_NAMES.values()))


def load_with_missing_years(force: bool = False) -> pd.DataFrame:
    """The kit file, then the team's downloads, then the API for any year that still has no state rows.

    Kit rows come first, so they win wherever a figure is in more than one source
    (``tidy_state`` keeps the first row per year, state, series and period).
    API rows are cached in ``data/nass/quickstats_state_fill.csv``.
    """
    raw = pd.concat([load_kit(), team_folder_state_rows()], ignore_index=True).fillna("")
    missing = years_without_state_rows(raw)
    cache = data_dir() / "nass" / "quickstats_state_fill.csv"
    if cache.exists() and not force:
        fill = pd.read_csv(cache, dtype=str, keep_default_na=False)
    else:
        key = secret(API_KEY_NAME)
        if not missing or not key:
            if missing:
                print(f"no {API_KEY_NAME} set: state rows for {missing} stay missing")
            return raw
        fill = fetch_state_survey(missing, key)
        cache.parent.mkdir(parents=True, exist_ok=True)
        fill.to_csv(cache, index=False, lineterminator="\n")
        record_in_manifest(cache, SOURCE_URL + "api")
        print(f"fetched {len(fill)} state rows for {missing}")
    return pd.concat([raw, fill], ignore_index=True).fillna("")


def _plain_totals(raw: pd.DataFrame, level: str) -> pd.DataFrame:
    """Rows for the three plain series at one geographic level, with numeric acres.

    Withheld values such as ``(D)`` are dropped, as the organizers' caveats require.
    """
    rows = raw[
        (raw["aggregation_level"] == level)
        & (raw["domain"] == "TOTAL")
        & raw["short_description"].isin(list(SERIES))
        & raw["reference_period"].isin(list(PERIODS))
    ].copy()
    acres = pd.to_numeric(rows["value"].str.replace(",", "").str.strip(), errors="coerce")
    rows = rows[acres.notna()].copy()
    rows["acres"] = acres[acres.notna()].astype("int64")
    rows["year"] = rows["year"].astype(int)
    rows["series"] = rows["short_description"].map(SERIES)
    rows["period"] = rows["reference_period"].map(PERIODS)
    return rows


def tidy_state(raw: pd.DataFrame) -> pd.DataFrame:
    """State survey figures: one row per year, state, series and period.

    "OTHER STATES" is dropped: it is NASS's combined row for the states its monthly forecasts do not
    list, it has no final figure (the kit stores 0), and so it can be neither a target nor a baseline.
    """
    rows = _plain_totals(raw, "STATE")
    rows = rows[(rows["source"] == "SURVEY") & (rows["state_name"] != "OTHER STATES")]
    table = rows.rename(columns={"state_name": "state"})[
        ["year", "state", "state_ansi", "series", "period", "acres"]
    ]
    table = table.drop_duplicates(["year", "state", "series", "period"])
    return table.sort_values(["year", "state", "series", "period"]).reset_index(drop=True)


def with_season_rows(state: pd.DataFrame, season: pd.DataFrame) -> pd.DataFrame:
    """Add the open season's rows from NASS's text reports; a figure already in the table wins."""
    ansi = state.drop_duplicates("state").set_index("state")["state_ansi"]
    season = season.assign(state_ansi=season["state"].map(ansi)).dropna(subset=["state_ansi"])
    table = pd.concat([state, season[state.columns]], ignore_index=True)
    table = table.drop_duplicates(["year", "state", "series", "period"], keep="first")
    return table.sort_values(["year", "state", "series", "period"]).reset_index(drop=True)


def tidy_county(raw: pd.DataFrame) -> pd.DataFrame:
    """County figures from the Census of Agriculture years (2012, 2017, 2022)."""
    rows = _plain_totals(raw, "COUNTY")
    rows = rows[(rows["source"] == "CENSUS") & (rows["period"] == "final")]
    table = rows.rename(columns={"county_name": "county"})[
        ["year", "state_ansi", "county_ansi", "county", "series", "acres"]
    ]
    table = table.drop_duplicates(["year", "state_ansi", "county_ansi", "series"])
    return table.sort_values(["year", "state_ansi", "county_ansi", "series"]).reset_index(drop=True)


def _score(predicted: pd.Series, actual: pd.Series) -> dict:
    """Error of state predictions against state truth, over the states that have both."""
    both = pd.concat([predicted.rename("predicted"), actual.rename("actual")], axis=1).dropna()
    if both.empty:
        return {}
    miss = both["predicted"] - both["actual"]
    total = both["actual"].sum()
    return {
        "n_states": len(both),
        "actual_acres": int(total),
        # Share of acres put in the wrong state: sum of absolute state errors over total acres.
        "state_error_pct": round(100 * miss.abs().sum() / total, 2),
        # Error of the summed total; state errors of opposite sign cancel here.
        "total_error_pct": round(100 * miss.sum() / total, 2),
    }


def baselines(state: pd.DataFrame, last_year: int = LAST_BASELINE_YEAR) -> pd.DataFrame:
    """How far off each simple predictor was, per year, against NASS's final figures.

    Predictors:
        nass_<month>         NASS's own in-season figure for grain (jun, aug, sep, oct, nov)
        same_as_last_year    last year's final acres, for grain and for silage
        last_year_share      last year's share of planted acres times this year's June planted acres
    """
    final = state[state["period"] == "final"].pivot(index=["year", "state"], columns="series", values="acres")
    results = []

    def add(year: int, series: str, predictor: str, predicted: pd.Series) -> None:
        if year not in final.index.get_level_values("year"):
            return
        score = _score(predicted, final.loc[year][series])
        if score:
            results.append({"year": year, "series": series, "predictor": predictor, **score})

    years = [y for y in sorted(state["year"].unique()) if y <= last_year]
    for year in years:
        this_year = state[state["year"] == year]

        for month in ["jun", "aug", "sep", "oct", "nov"]:
            report = this_year[(this_year["period"] == month) & (this_year["series"] == "grain")]
            add(year, "grain", f"nass_{month}", report.set_index("state")["acres"])

        if year - 1 not in final.index.get_level_values("year"):
            continue  # the kit has no state rows for census years, so the next year has no "last year"
        previous = final.loc[year - 1]
        june_planted = this_year[(this_year["period"] == "jun") & (this_year["series"] == "planted")]
        june_planted = june_planted.set_index("state")["acres"]
        for series in ["grain", "silage"]:
            add(year, series, "same_as_last_year", previous[series])
            share = previous[series] / previous["planted"]
            add(year, series, "last_year_share", share * june_planted)

    return pd.DataFrame(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="rebuild even if the outputs exist")
    args = parser.parse_args()

    out = data_dir() / "nass"
    out.mkdir(parents=True, exist_ok=True)
    targets = {name: out / f"{name}.csv" for name in ["corn_acres_state", "corn_acres_county", "baselines"]}
    if all(path.exists() for path in targets.values()) and not args.force:
        print("outputs exist; use --force to rebuild")
        return

    raw = load_with_missing_years(force=args.force)
    state = with_season_rows(tidy_state(raw), season_rows())
    tables = {
        "corn_acres_state": state,
        "corn_acres_county": tidy_county(raw),
        "baselines": baselines(state),
    }
    for name, table in tables.items():
        table.to_csv(targets[name], index=False, lineterminator="\n")
        record_in_manifest(targets[name], SOURCE_URL)
        print(f"{name}: {len(table)} rows -> {targets[name]}")


if __name__ == "__main__":
    main()
