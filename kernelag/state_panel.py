"""One row per state and year: the acreage targets and everything public by mid-November.

Sources:
    data/nass/corn_acres_state.csv   planted, grain and silage acres with NASS's in-season
                                     figures (``kernelag.nass``; 2012 to 2025)
    data/Quickstats Data/            the team's Quick Stats downloads (2015 to 2025): milk cows and
                                     all cattle on 1 January, corn grain yield with its monthly
                                     forecasts, corn silage yield, monthly corn prices

Columns ("as of" = the latest figure NASS had published by mid-November of that year):
    silage, grain, planted         final acres (the targets; NASS publishes them the next January)
    planted_asof, grain_asof       latest in-season planted acres and harvested-for-grain forecast
    grain_yield, grain_yield_asof  final bushels per acre, and the latest in-season forecast
    silage_yield                   final tons per acre
    milk_cows, cattle              head on 1 January of that year
    corn_price_sep                 price received in September, dollars per bushel
    sat_share, share_se            satellite silage-like share of sampled corn acres and its standard
                                   error (``kernelag.state_signal``; sampled states, 2019 on)

Output: ``data/panel/state_year.csv``

Run: ``python -m kernelag.state_panel``
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from kernelag.paths import data_dir, record_in_manifest

QUICKSTATS_DIR = "Quickstats Data"
SOURCE_URL = "https://quickstats.nass.usda.gov/api"

# Latest first: the first period that exists for a state-year is its "as of" value.
PLANTED_ASOF = ["oct", "sep", "aug", "jun", "mar"]
GRAIN_ASOF = ["nov", "oct", "sep", "aug", "jun"]
YIELD_ASOF = ["YEAR - NOV FORECAST", "YEAR - OCT FORECAST", "YEAR - SEP FORECAST", "YEAR - AUG FORECAST"]


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


def build_panel(acres: pd.DataFrame, folder: Path) -> pd.DataFrame:
    """Join acreage and context into one state-year table."""
    acres = acres.rename(columns={"acres": "value"})
    final = acres[acres["period"] == "final"].pivot(index=["state", "year"], columns="series", values="value")
    panel = final[["silage", "grain", "planted"]].copy()
    planted = acres[acres["series"] == "planted"]
    grain = acres[acres["series"] == "grain"]
    panel["planted_asof"] = latest_available(planted, PLANTED_ASOF)
    panel["grain_asof"] = latest_available(grain, GRAIN_ASOF)

    grain_yield = read_item(folder, "corn_grain_yield_bu_acre", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")
    panel["grain_yield"] = latest_available(grain_yield, ["YEAR"])
    panel["grain_yield_asof"] = latest_available(grain_yield, YIELD_ASOF)
    silage_yield = read_item(folder, "corn_silage_yield_tons_acre", "CORN, SILAGE - YIELD, MEASURED IN TONS / ACRE")
    panel["silage_yield"] = latest_available(silage_yield, ["YEAR"])

    cows = read_item(folder, "milk_cow_inventory", "CATTLE, COWS, MILK - INVENTORY")
    panel["milk_cows"] = latest_available(cows, ["FIRST OF JAN"])
    cattle = read_item(folder, "cattle_calves_inventory", "CATTLE, INCL CALVES - INVENTORY")
    panel["cattle"] = latest_available(cattle, ["FIRST OF JAN"])

    price = read_item(folder, "corn_prices_received", "CORN, GRAIN - PRICE RECEIVED, MEASURED IN $ / BU")
    panel["corn_price_sep"] = latest_available(price, ["SEP"])
    return panel.reset_index().sort_values(["state", "year"]).reset_index(drop=True)


def main() -> None:
    data = data_dir()
    acres = pd.read_csv(data / "nass" / "corn_acres_state.csv")
    panel = build_panel(acres, data / QUICKSTATS_DIR)
    satellite = data / "panel" / "state_satellite.csv"   # from kernelag.state_signal, if it has been run
    if satellite.exists():
        signal = pd.read_csv(satellite)[["state", "year", "sat_share", "share_se", "assessable_share"]]
        panel = panel.merge(signal, on=["state", "year"], how="left")
    target = data / "panel" / "state_year.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(target, index=False, lineterminator="\n")
    record_in_manifest(target, SOURCE_URL)
    print(f"{len(panel)} state-years, {panel['state'].nunique()} states, "
          f"{panel['year'].min()} to {panel['year'].max()} -> {target}")
    print("share of state-years with a value, by column:")
    print(panel.drop(columns=["state", "year"]).notna().groupby(panel["year"]).mean().round(2).to_string())


if __name__ == "__main__":
    main()
