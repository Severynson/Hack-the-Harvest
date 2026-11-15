#!/usr/bin/env python3
"""One row per state and year, 2000 to 2026: the acres to predict and what was public on the forecast date.

Every input is a file under data/ (see data/README.md). Standard library only.

    python3 test_models/model/build_panel.py [--asof nov]      writes out/panel_<asof>.csv

"As of" means public on the 15th of that month (aug, sep, oct or nov) of the same year. A figure that
was not public yet is left blank, so the same code replays an earlier forecast date.

Columns
    silage, grain, planted       NASS final acres (the targets; first published the next January), up to 2025
    planted_asof                 NASS's latest planted acres on that date (June Acreage or a later report). Quick Stats
                                 keeps those in-season figures from 2018 only; for earlier years the final figure
                                 stands in, which is a small look-ahead (see README)
    grain_asof                   NASS's latest harvested-for-grain forecast on that date (kept from 2012)
    yield, yield_asof            final grain yield and NASS's latest forecast of it (bu / acre)
    milk_cows                    milk cows on 1 January (head)
    drought_d1, drought_d2       mean share of the state in drought class D1 / D2 or worse, June to September (0 to 100)
    cond_poor                    mean percent of corn rated poor or very poor, 20 July to 10 September
    planted_may20                percent of corn planted by about 20 May (low = late planting)
    mature_sep22                 percent of corn mature by about 22 September (low = late season)
    pasture_poor                 mean percent of pasture rated poor or very poor, 15 June to 31 August
    hay_stocks_may               hay on farms on 1 May (tons)
    hay_price, milk_price        mean price received, June to August ($ / ton) and January to August ($ / cwt)
    gdd, rain, hot_days          May to September corn heat units (C-days), rain (mm) and days of 32 C or more,
                                 county values weighted by each county's corn acres
    early_freeze                 share of the state's corn (by county acres) with a hard freeze before 7 October (0 to 1)
"""

from __future__ import annotations

import argparse
import csv
import gzip
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data"
QS = DATA / "Quickstats Data"
YEARS = range(2000, 2027)
LAST_TRUTH_YEAR = 2025                  # for the running year Quick Stats shows provisional figures under "YEAR"
ASOF_MONTH = {"aug": 8, "sep": 9, "oct": 10, "nov": 11}
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
SKIP_STATES = {"OT", "US", ""}          # "OTHER STATES" rows and anything without a postal code
COLUMNS = ["state", "year", "silage", "grain", "planted", "planted_asof", "grain_asof", "yield", "yield_asof",
           "milk_cows", "drought_d1", "drought_d2", "cond_poor", "planted_may20", "mature_sep22", "pasture_poor",
           "hay_stocks_may", "hay_price", "milk_price", "gdd", "rain", "hot_days", "early_freeze"]


def rows(path: Path):
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def quickstats(name: str, short_desc: str):
    """Survey state totals of one item: yields (state, year, reference period, week ending, value)."""
    path = next(p for p in (QS / f"{name}_state_2000_2026.csv", QS / f"{name}_state_2000_2026.csv.gz") if p.exists())
    for r in rows(path):
        if r["short_desc"] != short_desc or r["domain_desc"] != "TOTAL" or r["state_alpha"] in SKIP_STATES:
            continue
        try:
            value = float(r["Value"].replace(",", ""))
        except ValueError:          # withheld cells such as (D)
            continue
        yield r["state_alpha"], int(r["year"]), r["reference_period_desc"], r.get("week_ending", ""), value


def period_month(period: str) -> int | None:
    """Month in which NASS published an in-season figure, from its reference period name.

    March "acreage" is planting intentions, not acres in the ground, so it is not used.
    """
    for name, month in (("JUN", 6), ("AUG", 8), ("SEP", 9), ("OCT", 10), ("NOV", 11)):
        if period.startswith(f"YEAR - {name} "):
            return month
    return None


def finals_and_asof(name: str, short_desc: str, asof_month: int, stand_in: bool = False):
    """(state, year) -> final value, and -> the latest in-season figure published by the as-of month.

    With ``stand_in`` the "YEAR" figure fills in where Quick Stats kept no in-season figure.
    """
    year_value, latest = {}, {}
    for state, year, period, _, value in quickstats(name, short_desc):
        if period == "YEAR":
            year_value[(state, year)] = value
            continue
        month = period_month(period)
        if month and month <= asof_month and month >= latest.get((state, year), (0, 0))[0]:
            latest[(state, year)] = (month, value)
    asof = {key: value for key, (_, value) in latest.items()}
    if stand_in:
        asof = {**year_value, **asof}
    return {key: v for key, v in year_value.items() if key[1] <= LAST_TRUTH_YEAR}, asof


def weekly_mean(name: str, descs: list[str], start: tuple[int, int], end: tuple[int, int], cutoff_month: int):
    """(state, year) -> mean over weeks in [start, end] of the summed items (percent), using weeks public by the cutoff."""
    by_week = defaultdict(float)
    for desc in descs:
        for state, year, _, week, value in quickstats(name, desc):
            if week:
                by_week[(state, year, week)] += value
    sums = defaultdict(list)
    for (state, year, week), value in by_week.items():
        day = date.fromisoformat(week)
        if date(year, *start) <= day <= date(year, *end) and day <= date(year, cutoff_month, 15):
            sums[(state, year)].append(value)
    return {key: sum(v) / len(v) for key, v in sums.items()}


def weekly_at(name: str, desc: str, target: tuple[int, int], cutoff_month: int):
    """(state, year) -> the value in the last week ending on or before the target day (within two weeks of it)."""
    best = {}
    for state, year, _, week, value in quickstats(name, desc):
        if not week:
            continue
        day, goal = date.fromisoformat(week), date(year, *target)
        if day <= goal and (goal - day).days <= 13 and day <= date(year, cutoff_month, 15):
            if (state, year) not in best or day > best[(state, year)][0]:
                best[(state, year)] = (day, value)
    return {key: value for key, (_, value) in best.items()}


def monthly_mean(name: str, desc: str, first: int, last: int, cutoff_month: int):
    """(state, year) -> mean of the monthly values from month `first` to `last`; a month counts as public from the next month on."""
    sums = defaultdict(list)
    for state, year, period, _, value in quickstats(name, desc):
        if period in MONTHS and first <= MONTHS.index(period) + 1 <= min(last, cutoff_month - 1):
            sums[(state, year)].append(value)
    return {key: sum(v) / len(v) for key, v in sums.items()}


def drought(asof_month: int):
    d1, d2 = defaultdict(list), defaultdict(list)
    for r in rows(DATA / "drought" / "usdm_state_weekly_2000_2026.csv"):
        day = date(int(r["MapDate"][:4]), int(r["MapDate"][4:6]), int(r["MapDate"][6:]))
        if date(day.year, 6, 1) <= day <= min(date(day.year, 9, 30), date(day.year, asof_month, 15)):
            d1[(r["StateAbbreviation"], day.year)].append(float(r["D1"]))
            d2[(r["StateAbbreviation"], day.year)].append(float(r["D2"]))
    mean = lambda table: {key: sum(v) / len(v) for key, v in table.items()}  # noqa: E731
    return mean(d1), mean(d2)


def county_corn_acres() -> dict[str, float]:
    """County FIPS -> mean planted corn acres, 2015 to 2025: fixed weights for the state weather averages."""
    acres = defaultdict(list)
    for r in rows(QS / "corn_planted_acres_county_2015_2025.csv"):
        if r["source_desc"] == "SURVEY" and r["agg_level_desc"] == "COUNTY" and r["short_desc"] == "CORN - ACRES PLANTED" and r["county_code"].isdigit():
            try:
                acres[r["state_fips_code"] + r["county_code"]].append(float(r["Value"].replace(",", "")))
            except ValueError:
                pass
    return {fips: sum(v) / len(v) for fips, v in acres.items()}


def weather(asof_month: int):
    """State means of the county weather tables, weighted by corn acres (plain means where no county has acres)."""
    weights = county_corn_acres()
    last_month = min(9, asof_month - 1)
    acc = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0, 0.0]))   # (state, year) -> fips -> gdd, rain, hot, months
    for year in YEARS:
        path = DATA / "weather" / "county_month" / f"county_month_{year}.csv"
        if not path.exists():
            continue
        for r in rows(path):
            month = int(r["month"])
            if 5 <= month <= last_month:
                cell = acc[(r["state"], year)][r["fips"]]
                cell[0] += float(r["gdd_c"])
                cell[1] += float(r["prcp_mm"])
                cell[2] += float(r["hot_days"]) if month in (7, 8) else 0.0
                cell[3] += 1
    out = {"gdd": {}, "rain": {}, "hot_days": {}, "early_freeze": {}}
    need = last_month - 4
    for key, counties in acc.items():
        full = {f: c for f, c in counties.items() if c[3] == need}
        if not full:
            continue
        w = {f: weights.get(f, 0.0) for f in full}
        if sum(w.values()) == 0:
            w = {f: 1.0 for f in full}
        total = sum(w.values())
        for i, name in enumerate(("gdd", "rain", "hot_days")):
            out[name][key] = sum(w[f] * full[f][i] for f in full) / total
    if asof_month >= 10:        # a freeze before 7 October is known on 15 October
        for year in YEARS:
            path = DATA / "weather" / "county_season" / f"county_season_{year}.csv"
            if not path.exists():
                continue
            hit, total = defaultdict(float), defaultdict(float)
            for r in rows(path):
                if r["data_through"] < f"{year}-10-06":
                    continue
                w = weights.get(r["fips"], 0.0)
                total[r["state"]] += w
                if r["first_hard_freeze_doy"] and int(r["first_hard_freeze_doy"]) < date(year, 10, 7).timetuple().tm_yday:
                    hit[r["state"]] += w
            for state, t in total.items():
                if t > 0:
                    out["early_freeze"][(state, year)] = hit[state] / t
    return out


def build(asof: str) -> list[dict]:
    m = ASOF_MONTH[asof]
    silage, _ = finals_and_asof("corn_silage_harvested_acres", "CORN, SILAGE - ACRES HARVESTED", m)
    grain, grain_asof = finals_and_asof("corn_grain_harvested_acres", "CORN, GRAIN - ACRES HARVESTED", m)
    planted, planted_asof = finals_and_asof("corn_planted_acres", "CORN - ACRES PLANTED", m, stand_in=True)
    yield_final, yield_asof = finals_and_asof("corn_grain_yield", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE", m)
    cows = {(s, y): v for s, y, period, _, v in quickstats("milk_cow_inventory", "CATTLE, COWS, MILK - INVENTORY") if period == "FIRST OF JAN"}
    hay = {(s, y): v for s, y, period, _, v in quickstats("hay_stocks", "HAY, ON FARM - STOCKS, MEASURED IN TONS") if period == "FIRST OF MAY"}
    d1, d2 = drought(m)
    wx = weather(m)
    columns = {
        "silage": silage, "grain": grain, "planted": planted, "planted_asof": planted_asof, "grain_asof": grain_asof,
        "yield": yield_final, "yield_asof": yield_asof, "milk_cows": cows, "drought_d1": d1, "drought_d2": d2,
        "cond_poor": weekly_mean("corn_condition_weekly", ["CORN - CONDITION, MEASURED IN PCT POOR", "CORN - CONDITION, MEASURED IN PCT VERY POOR"], (7, 20), (9, 10), m),
        "planted_may20": weekly_at("corn_progress_weekly", "CORN - PROGRESS, MEASURED IN PCT PLANTED", (5, 20), m),
        "mature_sep22": weekly_at("corn_progress_weekly", "CORN - PROGRESS, MEASURED IN PCT MATURE", (9, 22), m),
        "pasture_poor": weekly_mean("pasture_condition_weekly", ["PASTURELAND - CONDITION, MEASURED IN PCT POOR", "PASTURELAND - CONDITION, MEASURED IN PCT VERY POOR"], (6, 15), (8, 31), m),
        "hay_stocks_may": hay,
        "hay_price": monthly_mean("hay_price_received", "HAY - PRICE RECEIVED, MEASURED IN $ / TON", 6, 8, m),
        "milk_price": monthly_mean("milk_price_received", "MILK - PRICE RECEIVED, MEASURED IN $ / CWT", 1, 8, m),
        **wx,
    }
    states = sorted({s for s, _ in silage} | {s for s, _ in grain})
    table = []
    for state in states:
        for year in YEARS:
            row = {"state": state, "year": year}
            for name in COLUMNS[2:]:
                value = columns[name].get((state, year))
                row[name] = "" if value is None else round(value, 4)
            if any(row[c] != "" for c in ("silage", "grain", "planted", "planted_asof")):
                table.append(row)
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asof", choices=list(ASOF_MONTH), default="nov")
    args = parser.parse_args()
    table = build(args.asof)
    out = HERE / "out" / f"panel_{args.asof}.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(table)
    filled = {c: sum(r[c] != "" for r in table) for c in COLUMNS[2:]}
    print(f"{out.relative_to(HERE.parents[1])}: {len(table)} state-years, {len({r['state'] for r in table})} states")
    print("  filled cells: " + ", ".join(f"{c} {n}" for c, n in filled.items()))


if __name__ == "__main__":
    main()
