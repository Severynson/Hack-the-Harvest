"""The answer: acres of corn for grain and for silage, by state and for the US, as of mid-November.

Pre-registered rule (written on 2026-11-15 before any 2025 estimate was looked at):
    Silage: the predictor with the lowest mean state error in the 2019-2024 backtest
            (``kernelag.state_model.backtest``, all states), fitted on every year up to 2024.
    Grain:  the lowest mean state error in 2019-2024 among
                nass_forecast         NASS's latest in-season harvested-for-grain figure (Nov, else Oct ...)
                nass_forecast_corrected
                                      that figure times the mean ratio of final to in-season grain acres
                                      over all earlier years (NASS's November figure ran above the final
                                      in most years 2013-2024)
                nass_forecast_corrected_by_state
                                      the same with each state's own median ratio over its last five
                                      earlier years (national ratio where a state has fewer than three)
                same_as_last_year     last year's final grain acres
                planted_minus_silage  latest planted acres, minus predicted silage, minus last year's
                                      acres that went to neither (abandoned, grazed, hay)
    Ranges: 80% ranges from the backtest. For states, the 10th and 90th percentiles of
            actual / predicted over all backtest state-years. For the US, the smallest and largest
            actual / predicted US total over the backtest years.
    US:     the sum of the state estimates. States outside NASS's state list are about 10,000 grain
            acres (2023: 86,513 thousand US against 86,506 thousand summed over states).

The estimate is written first. ``--score`` then compares the written file with the organizers'
2025 table, once; it never changes the estimate.

Outputs: ``data/models/final_estimate_<year>.csv`` (one row per state plus ``US TOTAL``),
``final_estimate_<year>_rule.csv`` (the backtest numbers behind each choice),
``final_estimate_<year>_score.csv`` (only with ``--score``).

Run:
    python -m kernelag.final_estimate            write the 2025 estimate
    python -m kernelag.final_estimate --score    compare it with the organizers' 2025 table
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from kernelag.nass import LAST_BASELINE_YEAR
from kernelag.paths import data_dir, record_in_manifest
from kernelag.state_model import FEATURE_SETS, add_changes, backtest, fit_ridge, state_error

TARGET_YEAR = 2025
SCORING_TABLE = "nass/quickstats_2025_corn_grain_silage_state.csv"
BACKTEST_YEARS = range(2019, LAST_BASELINE_YEAR + 1)
GRAIN_PREDICTORS = ["nass_forecast", "nass_forecast_corrected", "nass_forecast_corrected_by_state",
                    "same_as_last_year", "planted_minus_silage"]
MIN_YEARS_FOR_CORRECTION = 3


def with_last_year(table: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Add ``<column>_prev``: the same state's value one calendar year earlier."""
    previous = table[["state", "year"] + columns].assign(year=table["year"] + 1)
    previous = previous.rename(columns={c: f"{c}_prev" for c in columns})
    return table.merge(previous, on=["state", "year"], how="left")


def predict_silage(table: pd.DataFrame, name: str, year: int) -> pd.Series:
    """Silage acres for every state with last year's figure, from a model fitted on earlier years only."""
    rows = table[(table["year"] == year) & table["silage_last"].notna()]
    if name == "same_as_last_year":
        return rows["silage_last"]
    if name == "satellite_ratio":
        return rows["silage_last"] * (rows["sat_ratio"] * np.exp(rows["d_planted"])).fillna(1.0)
    fit_rows = table[(table["year"] < year) & table["target"].notna() & table["reversion"].notna()]
    return rows["silage_last"] * np.exp(fit_ridge(fit_rows, FEATURE_SETS[name])(rows))


def predict_grain(table: pd.DataFrame, name: str, year: int, silage: pd.Series) -> pd.Series:
    """Grain acres for every state with last year's figure."""
    rows = table[(table["year"] == year) & table["grain_prev"].notna()]
    if name == "same_as_last_year":
        return rows["grain_prev"]
    if name == "nass_forecast":
        return rows["grain_asof"].fillna(rows["grain_prev"])
    if name.startswith("nass_forecast_corrected"):
        return rows["grain_asof"].fillna(rows["grain_prev"]) * correction(table, year, rows, name.endswith("by_state"))
    other_last = (rows["planted_prev"] - rows["grain_prev"] - rows["silage_prev"]).clip(lower=0)
    planted = rows["planted_asof"].fillna(rows["planted_prev"])
    return (planted - silage.reindex(rows.index).fillna(rows["silage_prev"]) - other_last).clip(lower=0)


def correction(table: pd.DataFrame, year: int, rows: pd.DataFrame, by_state: bool) -> pd.Series:
    """Ratio of final to in-season grain acres, learned from years before ``year`` only."""
    earlier = table[(table["year"] < year) & table["grain"].notna() & table["grain_asof"].notna()]
    yearly = earlier.groupby("year").apply(lambda d: d["grain"].sum() / d["grain_asof"].sum())
    national = float(yearly.mean()) if len(yearly) >= MIN_YEARS_FOR_CORRECTION else 1.0
    factor = pd.Series(national, index=rows.index)
    if by_state:
        ratio = (earlier["grain"] / earlier["grain_asof"]).replace([np.inf, -np.inf], np.nan)
        recent = earlier.assign(ratio=ratio).sort_values("year").groupby("state").tail(5)
        stats = recent.groupby("state")["ratio"].agg(["median", "count"])
        stats = stats[stats["count"] >= MIN_YEARS_FOR_CORRECTION]["median"]
        factor = rows["state"].map(stats).fillna(national)
    return factor


def mean_state_error(predictions: dict, table: pd.DataFrame, truth: str) -> float:
    errors = []
    for year, predicted in predictions.items():
        actual = table.loc[predicted.index, truth].dropna()
        errors.append(state_error(predicted.loc[actual.index], actual)["state_error_pct"])
    return round(float(np.mean(errors)), 2)


def ranges(predictions: dict, table: pd.DataFrame, truth: str) -> tuple[float, float, float, float]:
    """(state low, state high, US low, US high) multipliers from the backtest predictions."""
    state_ratios, us_ratios = [], []
    for predicted in predictions.values():
        actual = table.loc[predicted.index, truth].dropna()
        predicted = predicted.loc[actual.index]
        keep = predicted > 0
        state_ratios += list((actual[keep] / predicted[keep]).to_numpy())
        us_ratios.append(actual.sum() / predicted.sum())
    q10, q90 = np.quantile(state_ratios, [0.1, 0.9])
    return float(q10), float(q90), float(min(us_ratios)), float(max(us_ratios))


def estimate(table: pd.DataFrame, year: int = TARGET_YEAR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the pre-registered rule. Returns (estimate table, rule table)."""
    results = backtest(table)
    results = results[results["scope"] == "all_states"]
    silage_errors = results.groupby("predictor")["state_error_pct"].mean().round(2)
    silage_choice = silage_errors.idxmin()

    silage_backtest = {y: predict_silage(table, silage_choice, y) for y in BACKTEST_YEARS}
    grain_backtest = {name: {y: predict_grain(table, name, y, silage_backtest[y]) for y in BACKTEST_YEARS}
                      for name in GRAIN_PREDICTORS}
    grain_errors = pd.Series({name: mean_state_error(p, table, "grain") for name, p in grain_backtest.items()})
    grain_choice = grain_errors.idxmin()

    rule = pd.concat([
        pd.DataFrame({"series": "silage", "predictor": silage_errors.index, "mean_state_error_pct": silage_errors.values}),
        pd.DataFrame({"series": "grain", "predictor": grain_errors.index, "mean_state_error_pct": grain_errors.values}),
    ], ignore_index=True)
    rule["chosen"] = ((rule["series"] == "silage") & (rule["predictor"] == silage_choice)) | \
                     ((rule["series"] == "grain") & (rule["predictor"] == grain_choice))

    silage = predict_silage(table, silage_choice, year)
    grain = predict_grain(table, grain_choice, year, silage)
    s_low, s_high, us_s_low, us_s_high = ranges(silage_backtest, table, "silage")
    g_low, g_high, us_g_low, us_g_high = ranges(grain_backtest[grain_choice], table, "grain")

    out = pd.DataFrame({"state": table.loc[silage.index.union(grain.index), "state"]})
    out["silage_acres"] = silage.round(-3)
    out["silage_low"], out["silage_high"] = (silage * s_low).round(-3), (silage * s_high).round(-3)
    out["grain_acres"] = grain.round(-3)
    out["grain_low"], out["grain_high"] = (grain * g_low).round(-3), (grain * g_high).round(-3)
    out = out.sort_values("state").reset_index(drop=True)
    us = {"state": "US TOTAL", "silage_acres": round(silage.sum(), -3),
          "silage_low": round(silage.sum() * us_s_low, -3), "silage_high": round(silage.sum() * us_s_high, -3),
          "grain_acres": round(grain.sum(), -3),
          "grain_low": round(grain.sum() * us_g_low, -3), "grain_high": round(grain.sum() * us_g_high, -3)}
    out = pd.concat([out, pd.DataFrame([us])], ignore_index=True)
    out.insert(1, "year", year)
    out["silage_method"], out["grain_method"] = silage_choice, grain_choice
    return out, rule


def score(estimate_table: pd.DataFrame, scoring_file) -> pd.DataFrame:
    """Errors of the written estimate against the organizers' table, and of same-as-last-year beside it."""
    truth = pd.read_csv(scoring_file)
    truth["series"] = np.where(truth["Data Item"].str.contains("GRAIN"), "grain", "silage")
    truth["acres"] = pd.to_numeric(truth["Value"].str.replace(",", ""), errors="coerce")
    rows = []
    for series in ["silage", "grain"]:
        actual = truth[truth["series"] == series].set_index("State")["acres"]
        states = estimate_table[estimate_table["state"] != "US TOTAL"].set_index("state")
        both = states.index.intersection(actual.drop(["US TOTAL", "OTHER STATES"], errors="ignore").index)
        result = state_error(states.loc[both, f"{series}_acres"], actual.loc[both])
        us_estimate = estimate_table.set_index("state").loc["US TOTAL", f"{series}_acres"]
        rows.append({"series": series, "states_scored": result["n_states"],
                     "state_error_pct": result["state_error_pct"],
                     "us_estimate": int(us_estimate), "us_actual": int(actual["US TOTAL"]),
                     "us_error_pct": round(100 * (us_estimate - actual["US TOTAL"]) / actual["US TOTAL"], 2),
                     "us_inside_range": bool(estimate_table.set_index("state").loc["US TOTAL", f"{series}_low"]
                                             <= actual["US TOTAL"]
                                             <= estimate_table.set_index("state").loc["US TOTAL", f"{series}_high"]),
                     "states_inside_range_pct": round(100 * float(np.mean(
                         (states.loc[both, f"{series}_low"] <= actual.loc[both])
                         & (actual.loc[both] <= states.loc[both, f"{series}_high"]))), 1)})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score", action="store_true", help="compare the written estimate with the organizers' table")
    args = parser.parse_args()
    data = data_dir()
    target = data / "models" / f"final_estimate_{TARGET_YEAR}.csv"
    pd.set_option("display.width", 220)

    if args.score:
        written = pd.read_csv(target)
        scored = score(written, data / SCORING_TABLE)
        scored.to_csv(data / "models" / f"final_estimate_{TARGET_YEAR}_score.csv", index=False, lineterminator="\n")
        print(scored.to_string(index=False))
        return

    table = with_last_year(add_changes(pd.read_csv(data / "panel" / "state_year.csv")), ["grain", "planted", "silage"])
    out, rule = estimate(table)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(target, index=False, lineterminator="\n")
    rule.to_csv(data / "models" / f"final_estimate_{TARGET_YEAR}_rule.csv", index=False, lineterminator="\n")
    record_in_manifest(target, "derived: kernelag.final_estimate")
    print(rule.to_string(index=False))
    print(out.tail(1).to_string(index=False))


if __name__ == "__main__":
    main()
