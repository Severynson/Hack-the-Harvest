"""One row per state and year: the acreage targets and everything public by mid-November.

Sources:
    data/nass/corn_acres_state.csv   planted, grain and silage acres with NASS's in-season
                                     figures (``kernelag.nass``; 2012 to 2025)
    data/Quickstats Data/            the team's Quick Stats downloads (2015 to 2025): milk cows and
                                     all cattle on 1 January, corn grain yield with its monthly
                                     forecasts, corn silage yield, monthly corn prices
    kernelag.context                 drought, crop condition, weather, insured losses, harvest pace

Columns ("as of" = the latest figure NASS had published by mid-November of that year):
    silage, grain, planted         final acres (the targets; NASS publishes them the next January)
    planted_asof, grain_asof       latest in-season planted acres and harvested-for-grain forecast
    grain_yield, grain_yield_asof  final bushels per acre, and the latest in-season forecast
    silage_yield                   final tons per acre
    milk_cows, cattle              head on 1 January of that year
    corn_price_sep                 price received in September, dollars per bushel (public from November)
    drought ... silage_pace        season context; see ``kernelag.context`` for each definition

``asof`` (aug, sep, oct or nov) moves the "as of" date earlier: only NASS reports of that month or
before are used. The year after the last acreage year is added as rows with context only, so the
model can make a forecast for the season that is still open.

Output: ``data/panel/state_year.csv``

Run: ``python -m kernelag.state_panel [--asof sep]``
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from kernelag.context import ASOF_MONTH, build_context
from kernelag.context import FEATURES as CONTEXT_FEATURES
from kernelag.paths import data_dir, record_in_manifest

QUICKSTATS_DIR = "Quickstats Data"
SATELLITE_COLUMNS = ["sat_share", "share_se", "assessable_share"]
SOURCE_URL = "https://quickstats.nass.usda.gov/api"

# Latest first: the first period that exists for a state-year is its "as of" value.
PLANTED_ASOF = ["oct", "sep", "aug", "jun", "mar"]
GRAIN_ASOF = ["nov", "oct", "sep", "aug", "jun"]
YIELD_ASOF = ["YEAR - NOV FORECAST", "YEAR - OCT FORECAST", "YEAR - SEP FORECAST", "YEAR - AUG FORECAST"]
REPORT_MONTH = {"mar": 3, "jun": 6, "aug": 8, "sep": 9, "oct": 10, "nov": 11}


def public_by(periods: list[str], asof: str) -> list[str]:
    """The periods whose NASS report is out by the ``asof`` month (reports come out before the 15th)."""
    def month(period: str) -> int:
        return next(m for name, m in REPORT_MONTH.items() if name in period.lower())
    return [p for p in periods if month(p) <= ASOF_MONTH[asof]]


def read_item(folder: Path, file_stem: str, item: str) -> pd.DataFrame:
    """Survey totals for one Quick Stats item: year, state, period, value (withheld values dropped)."""
    raw = pd.read_csv(folder / f"{file_stem}_state_2015_2025.csv", dtype=str, keep_default_na=False)
    rows = raw[(raw["source_desc"] == "SURVEY") & (raw["domain_desc"] == "TOTAL") & (raw["short_desc"] == item)]
    value = pd.to_numeric(rows["Value"].str.replace(",", "").str.strip(), errors="coerce")
    table = pd.DataFrame({
        "year": rows["year"].astype(int), "state": rows["state_name"],
        "period": rows["reference_period_desc"], "value": value,
    }).dropna(subset=["value"])
    return table.drop_duplicates(["year", "state", "period"])


def latest_available(table: pd.DataFrame, periods: list[str]) -> pd.Series:
    """Per state-year, the value from the first of ``periods`` that exists."""
    wide = table[table["period"].isin(periods)].pivot(index=["state", "year"], columns="period", values="value")
    result = pd.Series(float("nan"), index=wide.index)
    for period in periods:
        if period in wide:
            result = result.fillna(wide[period])
    return result


def build_panel(acres: pd.DataFrame, folder: Path, context: pd.DataFrame | None = None,
                asof: str = "nov", satellite: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join acreage, herd, yield, price, season context and the satellite share into one state-year table."""
    acres = acres.rename(columns={"acres": "value"})
    final = acres[acres["period"] == "final"].pivot(index=["state", "year"], columns="series", values="value")
    panel = final.reindex(columns=["silage", "grain", "planted"]).copy()

    # The open season: one more year for every state, holding only what is public so far.
    last_year = int(panel.index.get_level_values("year").max())
    states = panel.index.get_level_values("state").unique()
    open_season = pd.MultiIndex.from_product([states, [last_year + 1]], names=["state", "year"])
    panel = panel.reindex(panel.index.union(open_season))

    planted = acres[acres["series"] == "planted"]
    grain = acres[acres["series"] == "grain"]
    panel["planted_asof"] = latest_available(planted, public_by(PLANTED_ASOF, asof))
    panel["grain_asof"] = latest_available(grain, public_by(GRAIN_ASOF, asof))

    grain_yield = read_item(folder, "corn_grain_yield_bu_acre", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")
    panel["grain_yield"] = latest_available(grain_yield, ["YEAR"])
    panel["grain_yield_asof"] = latest_available(grain_yield, public_by(YIELD_ASOF, asof))
    silage_yield = read_item(folder, "corn_silage_yield_tons_acre", "CORN, SILAGE - YIELD, MEASURED IN TONS / ACRE")
    panel["silage_yield"] = latest_available(silage_yield, ["YEAR"])

    cows = read_item(folder, "milk_cow_inventory", "CATTLE, COWS, MILK - INVENTORY")
    panel["milk_cows"] = latest_available(cows, ["FIRST OF JAN"])
    cattle = read_item(folder, "cattle_calves_inventory", "CATTLE, INCL CALVES - INVENTORY")
    panel["cattle"] = latest_available(cattle, ["FIRST OF JAN"])

    price = read_item(folder, "corn_prices_received", "CORN, GRAIN - PRICE RECEIVED, MEASURED IN $ / BU")
    # The September price is published at the end of October.
    panel["corn_price_sep"] = latest_available(price, ["SEP"]) if ASOF_MONTH[asof] >= 11 else float("nan")

    panel = panel.reset_index()
    if context is not None:
        panel = panel.merge(context[["state", "year", *CONTEXT_FEATURES]], on=["state", "year"], how="left")
    if satellite is not None:
        panel = panel.merge(satellite[["state", "year", *SATELLITE_COLUMNS]], on=["state", "year"], how="left")
    return panel.sort_values(["state", "year"]).reset_index(drop=True)


def load_panel(asof: str = "nov") -> pd.DataFrame:
    """The panel built from the files under ``data/`` (``kernelag.nass`` must have run)."""
    data = data_dir()
    acres = pd.read_csv(data / "nass" / "corn_acres_state.csv")
    satellite_file = data / "panel" / "state_satellite.csv"   # from kernelag.state_signal, if it has been run
    satellite = pd.read_csv(satellite_file) if satellite_file.exists() else None
    return build_panel(acres, data / QUICKSTATS_DIR, build_context(data, asof), asof, satellite)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asof", choices=list(ASOF_MONTH), default="nov")
    args = parser.parse_args()

    panel = load_panel(args.asof)
    suffix = "" if args.asof == "nov" else f"_asof_{args.asof}"
    target = data_dir() / "panel" / f"state_year{suffix}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(target, index=False, lineterminator="\n")
    record_in_manifest(target, SOURCE_URL)
    print(f"{len(panel)} state-years, {panel['state'].nunique()} states, "
          f"{panel['year'].min()} to {panel['year'].max()} -> {target}")
    print("share of state-years with a value, by column:")
    print(panel.drop(columns=["state", "year"]).notna().groupby(panel["year"]).mean().round(2).to_string())


if __name__ == "__main__":
    main()
