"""The USDA deliverable: acres of corn for grain and for silage, per state and for the US, by 15 November.

Two outputs (``data/models/``):

    deliverable_2026.csv        the 2026 numbers with 80% and 90% intervals (from ``state_forecast_2026.csv``)
    deliverable_comparison.csv  for 2017-2025, what we would have said in mid-November of each year next
                                to NASS's final acres in the organizer CSV
                                (``jupyter/workspace/02_QuickStats/corn_grain_silage_acres_2012_2025.csv``),
                                per state and for the US, with "same as last year" as the naive baseline
    deliverable_summary.json    state and US error per year and on average

Every past-year number uses only what was public by mid-November of that year. Each year's silage
parameters come from earlier years only (``kernelag.state_model``, ``kernelag.silage_level``).
2017-2024 is the backtest that also chose the method; 2025 was scored once, after the method was fixed.
Grain is NASS's own November harvested-for-grain forecast where it exists, so the grain number is not an
independent estimate. The truth is the organizer CSV, read here independently of the pipeline's copy.

Run: ``python -m kernelag.deliverable``
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag import silage_level, state_model
from kernelag.paths import data_dir, kit_dir, record_in_manifest
from kernelag.state_panel import QUICKSTATS_DIR, load_panel

ORGANIZER_CSV = Path("02_QuickStats/corn_grain_silage_acres_2012_2025.csv")   # under kernelag.paths.kit_dir()
YEARS = range(2017, 2026)
FORECAST_YEAR = 2026


def organizer_truth(path: Path) -> pd.DataFrame:
    """Final NASS survey acres per state and year from the organizer CSV: year, state, grain, silage."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = raw[(raw["aggregation_level"] == "STATE") & (raw["source"] == "SURVEY")
               & (raw["reference_period"] == "YEAR") & (raw["domain"] == "TOTAL")
               & raw["short_description"].isin(["CORN, GRAIN - ACRES HARVESTED", "CORN, SILAGE - ACRES HARVESTED"])]
    value = pd.to_numeric(rows["value"].str.replace(",", "").str.strip(), errors="coerce")
    table = pd.DataFrame({"year": rows["year"].astype(int), "state": rows["state_name"],
                          "series": rows["crop_use"], "actual": value}).dropna()
    return table.drop_duplicates(["year", "state", "series"]).assign(truth_source="organizer_csv")


def with_census_years(truth: pd.DataFrame, nass_acres: pd.DataFrame) -> pd.DataFrame:
    """Add the state-years the organizer CSV leaves out (it has no state survey rows for the Census
    years 2012, 2017 and 2022) from the pipeline's NASS copy, marked ``truth_source="nass_quickstats"``."""
    final = nass_acres[(nass_acres["period"] == "final") & nass_acres["series"].isin(["grain", "silage"])]
    extra = final.rename(columns={"acres": "actual"})[["year", "state", "series", "actual"]]
    extra = extra.merge(truth[["year", "state", "series"]], how="left", indicator=True)
    extra = extra[extra["_merge"] == "left_only"].drop(columns="_merge").assign(truth_source="nass_quickstats")
    return pd.concat([truth, extra], ignore_index=True)


def our_numbers(table: pd.DataFrame, history: dict, years: range) -> pd.DataFrame:
    """What the delivered method says for each past year: year, state, series, predicted, last."""
    parts = []
    for year in years:
        rows = table[table["year"] == year].set_index("state")
        silage = state_model.predict_silage_by(table, year, state_model.SMOOTHED, history)
        grain = state_model.predict_grain(table, year)
        for series, predicted in [("silage", silage), ("grain", grain["grain"])]:
            part = pd.DataFrame({"predicted": predicted, "last": rows[f"{series}_last"].reindex(predicted.index)})
            if series == "grain":
                part["grain_method"] = grain["grain_method"]
            parts.append(part.rename_axis("state").reset_index().assign(year=year, series=series))
    return pd.concat(parts, ignore_index=True)


def compare(ours: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """State rows plus one US row per year and series (US = sum of states with both numbers)."""
    both = ours.merge(truth, on=["year", "state", "series"], how="inner")
    us = both.groupby(["year", "series"], as_index=False).agg(
        predicted=("predicted", "sum"), last=("last", "sum"), actual=("actual", "sum"),
        truth_source=("truth_source", lambda s: "+".join(sorted(set(s)))))
    both = pd.concat([us.assign(state="US (sum of states)"), both], ignore_index=True)
    both["error_pct"] = 100 * (both["predicted"] / both["actual"] - 1)
    both["last_year_error_pct"] = 100 * (both["last"] / both["actual"] - 1)
    columns = ["year", "series", "state", "predicted", "actual", "error_pct", "last", "last_year_error_pct",
               "grain_method", "truth_source"]
    return both.reindex(columns=columns).sort_values(["year", "series", "state"]).reset_index(drop=True)


def summarize(comparison: pd.DataFrame) -> dict:
    """Per series: state WAPE and US error per year, for our numbers and for 'same as last year'."""
    out = {}
    for series, rows in comparison.groupby("series"):
        states = rows[~rows["state"].str.startswith("US")].dropna(subset=["last"])
        us = rows[rows["state"].str.startswith("US")].set_index("year")
        by_year = {}
        for year, part in states.groupby("year"):
            by_year[int(year)] = {
                "states": len(part), "truth": "+".join(sorted(set(part["truth_source"]))),
                "state_wape_pct": round(100 * (part["predicted"] - part["actual"]).abs().sum() / part["actual"].sum(), 2),
                "last_year_state_wape_pct": round(100 * (part["last"] - part["actual"]).abs().sum() / part["actual"].sum(), 2),
                "us_error_pct": round(float(us.loc[year, "error_pct"]), 2),
                "last_year_us_error_pct": round(float(us.loc[year, "last_year_error_pct"]), 2),
            }
        table = pd.DataFrame(by_year).T
        def mean(column: str, years: list[int], table: pd.DataFrame = table) -> float:
            return round(float(table.loc[years, column].abs().mean()), 2)
        backtest = [y for y in by_year if y <= state_model.LAST_BASELINE_YEAR]
        held_out = [y for y in by_year if y > state_model.LAST_BASELINE_YEAR]
        out[series] = {"by_year": by_year}
        for name, years in [("backtest_2017_2024", backtest), ("held_out_2025", held_out)]:
            if years:
                out[series][name] = {c: mean(c, years) for c in table.columns if c not in ("states", "truth")}
                out[series][name]["us_within_3pct_years"] = int((table.loc[years, "us_error_pct"].abs() <= 3).sum())
                out[series][name]["years"] = [int(y) for y in years]
    return out


def deliverable_table(forecast: pd.DataFrame) -> pd.DataFrame:
    keep = ["year", "state"] + [c for c in forecast.columns if c.startswith(("grain", "silage")) and "method" not in c]
    return forecast[keep + ["silage_method", "grain_method"]]


def main() -> None:
    models = data_dir() / "models"
    table = state_model.add_changes(load_panel("nov"))
    history = silage_level.load_history(data_dir() / QUICKSTATS_DIR, "nov")
    organizer = organizer_truth(kit_dir() / ORGANIZER_CSV)
    nass_acres = pd.read_csv(data_dir() / "nass" / "corn_acres_state.csv")
    truth = with_census_years(organizer, nass_acres)
    shared = organizer.merge(nass_acres[nass_acres["period"] == "final"], on=["year", "state", "series"])
    comparison = compare(our_numbers(table, history, YEARS), truth)
    summary = summarize(comparison)
    summary["truth_check"] = {"organizer_rows_also_in_pipeline_copy": len(shared),
                              "rows_that_differ": int((shared["actual"] != shared["acres"]).sum())}
    summary["notes"] = [
        ("Truth: final NASS survey acres from the organizer CSV;"
         " 2017 and 2022 (Census years, no state survey rows in that CSV) from the pipeline's NASS Quick"
         " Stats copy, marked in truth_source."),
        "2017-2024 also chose the method; 2025 was scored once after it was fixed.",
        "Grain uses NASS's own November forecast where published; it is not independent of NASS.",
        "Silage has no NASS in-season figure; the baseline is last year's acres.",
        "Current-vintage inputs: a replay, not archived real-time runs.",
    ]
    forecast = pd.read_csv(models / f"state_forecast_{FORECAST_YEAR}.csv")
    outputs = {
        models / f"deliverable_{FORECAST_YEAR}.csv": deliverable_table(forecast),
        models / "deliverable_comparison.csv": comparison.round({"predicted": -2, "last": -2, "error_pct": 2,
                                                                 "last_year_error_pct": 2}),
    }
    for path, frame in outputs.items():
        frame.to_csv(path, index=False, lineterminator="\n")
        record_in_manifest(path, "derived: kernelag.deliverable")
    summary_path = models / "deliverable_summary.json"
    summary_path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    record_in_manifest(summary_path, "derived: kernelag.deliverable")

    print("truth check:", summary["truth_check"])
    us = forecast[forecast["state"].str.startswith("US")].iloc[0]
    print(f"{FORECAST_YEAR} US: grain {us['grain'] / 1e6:.2f}M acres (80% {us['grain_lo80'] / 1e6:.2f}-"
          f"{us['grain_hi80'] / 1e6:.2f}), silage {us['silage'] / 1e6:.2f}M (80% {us['silage_lo80'] / 1e6:.2f}-"
          f"{us['silage_hi80'] / 1e6:.2f})")
    for series in ["silage", "grain"]:
        print(f"\n{series}: ours vs NASS final (organizer CSV)")
        print(pd.DataFrame(summary[series]["by_year"]).T.to_string())
        for name in ["backtest_2017_2024", "held_out_2025"]:
            print(name, summary[series].get(name))


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
