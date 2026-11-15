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

Run: ``python -m kernelag.nass``            (baselines stop at 2024; 2025 is the scoring year)
"""

from __future__ import annotations

import argparse

import pandas as pd

from kernelag.paths import data_dir, kit_dir, record_in_manifest

KIT_FILE = "02_QuickStats/corn_grain_silage_acres_2012_2025.csv"
SOURCE_URL = "https://quickstats.nass.usda.gov/"

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
    "YEAR - SEP FORECAST": "sep",
    "YEAR - OCT FORECAST": "oct",
    "YEAR - NOV FORECAST": "nov",
}

# 2025 is the organizers' scoring year: nothing is fitted or reported on it before the final run.
LAST_BASELINE_YEAR = 2024


def load_kit() -> pd.DataFrame:
    """The organizers' file as text columns, exactly as NASS published the values."""
    return pd.read_csv(kit_dir() / KIT_FILE, dtype=str, keep_default_na=False)


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
    """State survey figures: one row per year, state, series and period."""
    rows = _plain_totals(raw, "STATE")
    rows = rows[rows["source"] == "SURVEY"]
    table = rows.rename(columns={"state_name": "state"})[
        ["year", "state", "state_ansi", "series", "period", "acres"]
    ]
    table = table.drop_duplicates(["year", "state", "series", "period"])
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

    raw = load_kit()
    state = tidy_state(raw)
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
