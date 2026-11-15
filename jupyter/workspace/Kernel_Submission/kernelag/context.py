"""Season context per state and year: weather, drought, crop stress and harvest pace.

Why: the USDA reps asked for more than acreage history. A grain crop that fails (drought, heat,
hail, early frost) is often chopped for silage instead, and that late switch is what surveys miss.
Every feature here is public before NASS's January report and comes from ``data/``.

Each feature uses only what was public on the 15th of the ``asof`` month (aug, sep, oct or nov),
so the same code replays an earlier forecast date. A feature that is not public yet is missing (NaN).

Features (one row per state and year):
    drought         mean share of the state in drought class D2 or worse, June to September (0 to 1)
    poor_condition  mean share of corn rated poor or very poor, weeks 30 to 36 (0 to 1)
    gdd_anom        May to September corn heat units against the state's own earlier years (ratio - 1)
    rain_anom       May to September rain against the state's own earlier years (ratio - 1)
    early_frost     share of the state's corn (by county) with a hard freeze before 7 October (0 to 1)
    loss_share      insured corn acres with a weather loss so far, over all insured corn acres (0 to 1)
    mature_wk38     percent of corn mature in week 38 (late September): how late the season runs
    silage_pace     percent of silage chopped by week 38, against the state's own earlier years (points)

Caveat: the RMA files are today's vintage. Losses for a given month keep being added for a few
months after it, so ``loss_share`` for past years is slightly more complete than it was that November.

Run: ``python -m kernelag.context``   (prints coverage; ``kernelag.state_panel`` does the join)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from kernelag.paths import data_dir

ASOF_MONTH = {"aug": 8, "sep": 9, "oct": 10, "nov": 11}
FEATURES = ["drought", "poor_condition", "gdd_anom", "rain_anom", "early_frost", "loss_share",
            "mature_wk38", "silage_pace"]

QUICKSTATS_DIR = "Quickstats Data"
DROUGHT_CLASS = "D2"                 # classes are cumulative: D2 means "D2 or worse"
CONDITION_WEEKS = range(30, 37)      # late July to early September: grain fill
PACE_WEEK = 38                       # late September
EARLY_FREEZE_DOY = 280               # 7 October
MIN_EARLIER_YEARS = 3                # an anomaly needs at least this many earlier years
# RMA cause-of-loss codes that can turn a grain crop into silage or an abandoned field.
WEATHER_LOSS_CODES = {
    "11": "drought", "12": "heat", "13": "failure of irrigation supply", "62": "hot wind",
    "21": "hail", "61": "wind", "41": "frost", "42": "freeze",
}

STATE_NAMES = {
    "AL": "ALABAMA", "AK": "ALASKA", "AZ": "ARIZONA", "AR": "ARKANSAS", "CA": "CALIFORNIA",
    "CO": "COLORADO", "CT": "CONNECTICUT", "DE": "DELAWARE", "FL": "FLORIDA", "GA": "GEORGIA",
    "HI": "HAWAII", "ID": "IDAHO", "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA", "KS": "KANSAS",
    "KY": "KENTUCKY", "LA": "LOUISIANA", "ME": "MAINE", "MD": "MARYLAND", "MA": "MASSACHUSETTS",
    "MI": "MICHIGAN", "MN": "MINNESOTA", "MS": "MISSISSIPPI", "MO": "MISSOURI", "MT": "MONTANA",
    "NE": "NEBRASKA", "NV": "NEVADA", "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY", "NM": "NEW MEXICO",
    "NY": "NEW YORK", "NC": "NORTH CAROLINA", "ND": "NORTH DAKOTA", "OH": "OHIO", "OK": "OKLAHOMA",
    "OR": "OREGON", "PA": "PENNSYLVANIA", "RI": "RHODE ISLAND", "SC": "SOUTH CAROLINA",
    "SD": "SOUTH DAKOTA", "TN": "TENNESSEE", "TX": "TEXAS", "UT": "UTAH", "VT": "VERMONT",
    "VA": "VIRGINIA", "WA": "WASHINGTON", "WV": "WEST VIRGINIA", "WI": "WISCONSIN", "WY": "WYOMING",
}


def cutoff(year: pd.Series, asof: str) -> pd.Series:
    """The 15th of the ``asof`` month in each row's year: nothing dated later may be used."""
    return pd.to_datetime({"year": year.astype(int), "month": ASOF_MONTH[asof], "day": 15})


def against_earlier_years(table: pd.DataFrame, column: str, relative: bool) -> pd.Series:
    """A state's value against the mean of its own earlier years (never later ones).

    ``relative`` gives ratio minus one; otherwise the plain difference.
    Rows must be sorted by state and year. Missing until ``MIN_EARLIER_YEARS`` earlier years exist.
    """
    earlier = table.groupby("state")[column].transform(
        lambda s: s.shift(1).expanding(min_periods=MIN_EARLIER_YEARS).mean())
    return table[column] / earlier - 1 if relative else table[column] - earlier


# --- one function per source; each returns state, year and its feature columns -------------------

def drought(usdm: pd.DataFrame, asof: str = "nov") -> pd.DataFrame:
    """Mean June-to-September share of the state in D2 or worse, from the weekly Drought Monitor."""
    date = pd.to_datetime(usdm["MapDate"].astype(str), format="%Y%m%d")
    rows = pd.DataFrame({
        "state": usdm["StateAbbreviation"].map(STATE_NAMES), "year": date.dt.year, "date": date,
        "drought": pd.to_numeric(usdm[DROUGHT_CLASS], errors="coerce") / 100,
    }).dropna(subset=["state"])
    rows = rows[rows["date"].dt.month.between(6, 9) & (rows["date"] <= cutoff(rows["year"], asof))]
    return rows.groupby(["state", "year"], as_index=False)["drought"].mean()


def _weekly(quickstats: pd.DataFrame, asof: str) -> pd.DataFrame:
    """Weekly Quick Stats rows as state, year, week, item, value; weeks after the cut-off dropped."""
    rows = pd.DataFrame({
        "state": quickstats["state_name"], "year": quickstats["year"].astype(int),
        "week": pd.to_numeric(quickstats["reference_period_desc"].str.extract(r"WEEK #(\d+)")[0], errors="coerce"),
        "week_ending": pd.to_datetime(quickstats["week_ending"], errors="coerce"),
        "item": quickstats["short_desc"],
        "value": pd.to_numeric(quickstats["Value"].astype(str).str.replace(",", ""), errors="coerce"),
    }).dropna(subset=["week", "week_ending", "value"])
    return rows[rows["week_ending"] <= cutoff(rows["year"], asof)]


def poor_condition(condition: pd.DataFrame, asof: str = "nov") -> pd.DataFrame:
    """Mean share of corn rated poor or very poor over weeks 30 to 36."""
    rows = _weekly(condition, asof)
    rows = rows[rows["item"].str.endswith(("PCT POOR", "PCT VERY POOR")) & rows["week"].isin(CONDITION_WEEKS)]
    per_week = rows.groupby(["state", "year", "week"])["value"].sum()   # poor + very poor
    result = (per_week.groupby(["state", "year"]).mean() / 100).rename("poor_condition")
    return result.reset_index()


def mature_wk38(progress: pd.DataFrame, asof: str = "nov") -> pd.DataFrame:
    """Percent of corn mature in week 38."""
    rows = _weekly(progress, asof)
    rows = rows[rows["item"].str.endswith("PCT MATURE") & (rows["week"] == PACE_WEEK)]
    return rows.groupby(["state", "year"], as_index=False)["value"].mean().rename(columns={"value": "mature_wk38"})


def silage_pace(silage_progress: pd.DataFrame, asof: str = "nov") -> pd.DataFrame:
    """Percent of silage chopped by week 38, minus the state's mean over earlier years."""
    rows = _weekly(silage_progress, asof)
    rows = rows[rows["week"] == PACE_WEEK]
    table = rows.groupby(["state", "year"], as_index=False)["value"].mean().sort_values(["state", "year"])
    table["silage_pace"] = against_earlier_years(table, "value", relative=False)
    return table[["state", "year", "silage_pace"]]


def corn_weights(county_planted: pd.DataFrame) -> pd.Series:
    """Mean planted corn acres per county (five-digit code), used only to weight counties in a state."""
    rows = county_planted[
        (county_planted["source_desc"] == "SURVEY") & (county_planted["short_desc"] == "CORN - ACRES PLANTED")
        & (county_planted["county_code"].astype(str).str.zfill(3) < "900")   # 998 = "other counties"
    ]
    fips = rows["state_fips_code"].astype(str).str.zfill(2) + rows["county_code"].astype(str).str.zfill(3)
    acres = pd.to_numeric(rows["Value"].astype(str).str.replace(",", ""), errors="coerce")
    return acres.groupby(fips.to_numpy()).mean().dropna()


def _state_mean(county_rows: pd.DataFrame, column: str, weights: pd.Series) -> pd.Series:
    """Corn-weighted county mean per state and year; plain mean where no county has a weight."""
    rows = county_rows.dropna(subset=[column]).copy()
    rows["w"] = rows["fips"].map(weights).fillna(0.0)
    has_weight = rows.groupby(["state", "year"])["w"].transform("sum") > 0
    rows.loc[~has_weight, "w"] = 1.0
    rows["wx"] = rows["w"] * rows[column]
    sums = rows.groupby(["state", "year"])[["wx", "w"]].sum()
    return sums["wx"] / sums["w"]


def weather(county_month: pd.DataFrame, county_season: pd.DataFrame, weights: pd.Series,
            asof: str = "nov") -> pd.DataFrame:
    """Heat-unit and rain anomalies (May to September, or to the last full month) and early hard freeze."""
    last_month = min(9, ASOF_MONTH[asof] - 1)
    months = county_month[county_month["month"].between(5, last_month)].copy()
    months["fips"] = months["fips"].astype(str).str.zfill(5)
    season = months.groupby(["fips", "state", "year"], as_index=False)[["gdd_c", "prcp_mm"]].sum()
    season["state"] = season["state"].map(STATE_NAMES)
    table = pd.DataFrame({
        "gdd": _state_mean(season, "gdd_c", weights), "rain": _state_mean(season, "prcp_mm", weights),
    }).reset_index().sort_values(["state", "year"])
    table["gdd_anom"] = against_earlier_years(table, "gdd", relative=True)
    table["rain_anom"] = against_earlier_years(table, "rain", relative=True)

    freeze = county_season.copy()
    freeze["fips"] = freeze["fips"].astype(str).str.zfill(5)
    freeze["state"] = freeze["state"].map(STATE_NAMES)
    freeze["early"] = (pd.to_numeric(freeze["first_hard_freeze_doy"], errors="coerce") < EARLY_FREEZE_DOY).astype(float)
    early = _state_mean(freeze, "early", weights).rename("early_frost").reset_index()
    if ASOF_MONTH[asof] < 10:          # 7 October has not happened yet
        early["early_frost"] = float("nan")
    return table[["state", "year", "gdd_anom", "rain_anom"]].merge(early, on=["state", "year"], how="outer")


def loss_share(cause_of_loss: pd.DataFrame, insured: pd.DataFrame, asof: str = "nov") -> pd.DataFrame:
    """Insured corn acres with a weather loss in months before the ``asof`` month, over insured acres."""
    losses = cause_of_loss[
        cause_of_loss["cause_of_loss_code"].astype(str).str.strip().str.zfill(2).isin(list(WEATHER_LOSS_CODES))
        & (pd.to_numeric(cause_of_loss["month_of_loss"], errors="coerce") < ASOF_MONTH[asof])
    ]

    def by_state(rows: pd.DataFrame, column: str) -> pd.Series:
        state = rows["state_abbreviation"].astype(str).str.strip().map(STATE_NAMES)
        acres = pd.to_numeric(rows[column], errors="coerce")
        return acres.groupby([state.to_numpy(), rows["commodity_year"].astype(int).to_numpy()]).sum()

    lost = by_state(losses, "net_determined_quantity")
    total = by_state(insured[insured["reporting_level_type"].astype(str).str.strip() == "Acres"],
                     "net_reporting_level_amount")
    share = (lost.reindex(total.index).fillna(0.0) / total.where(total > 0)).rename("loss_share")
    return share.rename_axis(["state", "year"]).reset_index().dropna(subset=["loss_share"])


# --- reading the files and joining ---------------------------------------------------------------

def _read_all(folder: Path, columns: list[str] | None = None, **kwargs) -> pd.DataFrame:
    files = sorted(folder.glob("*.csv*"))
    if not files:
        raise FileNotFoundError(f"no files in {folder}")
    return pd.concat([pd.read_csv(f, usecols=columns, **kwargs) for f in files], ignore_index=True)


def build_context(data: Path | None = None, asof: str = "nov") -> pd.DataFrame:
    """All features joined on state and year, from the files under ``data/``."""
    data = data or data_dir()
    quickstats = data / QUICKSTATS_DIR

    def weekly(name: str) -> pd.DataFrame:
        path = next(quickstats.glob(f"{name}_weekly_state_2000_2026.csv*"))
        return pd.read_csv(path, dtype=str, keep_default_na=False)

    weights = corn_weights(pd.read_csv(quickstats / "corn_planted_acres_county_2015_2025.csv",
                                       dtype=str, keep_default_na=False))
    parts = [
        drought(pd.read_csv(next((data / "drought").glob("usdm_state_weekly_2000_2026.csv*"))), asof),
        poor_condition(weekly("corn_condition"), asof),
        weather(_read_all(data / "weather" / "county_month", dtype={"fips": str}),
                _read_all(data / "weather" / "county_season", dtype={"fips": str}), weights, asof),
        loss_share(
            _read_all(data / "rma" / "cause_of_loss_corn", dtype=str, columns=[
                "commodity_year", "state_abbreviation", "cause_of_loss_code", "month_of_loss",
                "net_determined_quantity"]),
            _read_all(data / "rma" / "insured_by_type_corn", dtype=str, columns=[
                "commodity_year", "state_abbreviation", "reporting_level_type", "net_reporting_level_amount"]),
            asof),
        mature_wk38(weekly("corn_progress"), asof),
        silage_pace(weekly("corn_silage_harvest_progress"), asof),
    ]
    table = parts[0]
    for part in parts[1:]:
        table = table.merge(part, on=["state", "year"], how="outer")
    return table[["state", "year", *FEATURES]].sort_values(["state", "year"]).reset_index(drop=True)


def main() -> None:
    table = build_context()
    print(f"{len(table)} state-years, {table['state'].nunique()} states, {table['year'].min()} to {table['year'].max()}")
    print("states with a value, by year:")
    print(table[table["year"] >= 2012].groupby("year")[FEATURES].count().to_string())


if __name__ == "__main__":
    main()
