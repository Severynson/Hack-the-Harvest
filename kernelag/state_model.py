"""State silage acres from public November information: does anything beat "same as last year"?

Target: each state's final corn-silage acres. NASS publishes no in-season silage figure, so the
number to beat is last year's acres carried forward.

The model predicts the year-on-year change in a state's silage acres (in logs) from changes that
are public by mid-November of the same year (``kernelag.state_panel``):
    reversion      last year's silage relative to its previous three-year mean (a high year tends to fall back)
    d_planted      change in planted corn acres
    d_not_grain    change in the share of planted acres that NASS does not expect to be combined
    d_cows         change in milk cows on 1 January
    d_cattle       change in all cattle on 1 January
    yield_shock    NASS's latest grain-yield forecast against the state's previous three-year mean
    d_price        change in the September corn price
    drought        share of the state in severe drought, June to September of the same year
    d_rma          change in corn acres insured as silage (states with at least 1,000 such acres)
    d_sat          change in the satellite silage-like share on the state's fixed sample areas
                   (in log-odds; ``kernelag.state_signal``; sampled states only, 2020 on)

"satellite_ratio" is the same idea with nothing fitted: last year's acres times this year's
satellite share over last year's, times the change in planted acres. Results are reported for all
states and for the sampled states alone; a state without a satellite value is read as "no change".

It is one pooled ridge regression for all states, weighted by silage acres, with a missing
change read as "no change". Each year is predicted by a model fitted on earlier years only.

The scoring year (2025) is excluded: nothing here is fitted, selected or reported on it.

Output: ``data/models/state_model_backtest.csv`` and ``state_model_weights.csv``

Run: ``python -m kernelag.state_model``
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from kernelag.nass import LAST_BASELINE_YEAR
from kernelag.paths import data_dir, record_in_manifest

FEATURES = ["reversion", "d_planted", "d_not_grain", "d_cows", "d_cattle", "yield_shock", "d_price"]
FEATURE_SETS = {
    "reversion_only": ["reversion"],
    "nass_acres": ["reversion", "d_planted", "d_not_grain"],
    "all_public": FEATURES,
    "reversion_plus_drought": ["reversion", "drought"],
    "reversion_plus_rma": ["reversion", "d_rma"],
    "reversion_plus_satellite": ["reversion", "d_sat"],
}
MIN_FIT_YEARS = 3
RIDGE_PENALTY = 1.0


def add_changes(panel: pd.DataFrame) -> pd.DataFrame:
    """Add last year's values, the target change and the predictor changes to the state-year panel."""
    table = panel.sort_values(["state", "year"]).copy()

    def last(column: str, years_back: int = 1) -> pd.Series:
        """The value ``years_back`` calendar years earlier (missing if that year is absent)."""
        shifted = table[["state", "year", column]].assign(year=table["year"] + years_back)
        return table[["state", "year"]].merge(shifted, on=["state", "year"], how="left")[column].set_axis(table.index)

    def mean_of_last_three(column: str) -> pd.Series:
        return pd.concat([last(column, k) for k in (1, 2, 3)], axis=1).mean(axis=1, skipna=False)

    table["silage_last"] = last("silage")
    table["target"] = np.log(table["silage"] / table["silage_last"])
    table["reversion"] = np.log(table["silage_last"] / pd.concat(
        [last("silage", k) for k in (2, 3, 4)], axis=1).mean(axis=1, skipna=False))
    table["d_planted"] = np.log(table["planted_asof"] / last("planted"))
    not_grain = 1 - table["grain_asof"] / table["planted_asof"]
    not_grain_last = 1 - last("grain") / last("planted")
    table["d_not_grain"] = not_grain - not_grain_last
    table["d_cows"] = np.log(table["milk_cows"] / last("milk_cows"))
    table["d_cattle"] = np.log(table["cattle"] / last("cattle"))
    table["yield_shock"] = np.log(table["grain_yield_asof"] / mean_of_last_three("grain_yield"))
    table["d_price"] = np.log(table["corn_price_sep"] / last("corn_price_sep"))
    for column in ["drought_summer", "rma_silage"]:
        if column not in table:
            table[column] = np.nan
    table["drought"] = table["drought_summer"]
    table["d_rma"] = np.log(table["rma_silage"] / last("rma_silage")).where(last("rma_silage") >= 1000)
    if "sat_share" not in table:
        table["sat_share"] = np.nan
    logit = np.log(table["sat_share"] / (1 - table["sat_share"]))
    logit_last = last("sat_share").pipe(lambda s: np.log(s / (1 - s)))
    table["d_sat"] = logit - logit_last
    table["sat_ratio"] = table["sat_share"] / last("sat_share")
    return table.replace([np.inf, -np.inf], np.nan)


def fit_ridge(rows: pd.DataFrame, features: list[str]):
    """Weighted ridge on standardized changes. Returns a function that predicts the log change."""
    x = rows[features].fillna(0.0).to_numpy()
    scale = x.std(axis=0)
    scale[scale == 0] = 1.0
    x = x / scale
    y = rows["target"].to_numpy()
    w = rows["silage_last"].to_numpy()
    xtw = x.T * w
    weights = np.linalg.solve(xtw @ x + RIDGE_PENALTY * w.mean() * np.eye(len(features)), xtw @ y)

    def predict(new_rows: pd.DataFrame) -> np.ndarray:
        return (new_rows[features].fillna(0.0).to_numpy() / scale) @ weights

    predict.weights = dict(zip(features, np.round(weights, 4)))
    return predict


def state_error(predicted: pd.Series, actual: pd.Series) -> dict:
    """Share of acres put in the wrong state, and the error of the summed total."""
    miss = predicted - actual
    return {
        "n_states": len(actual),
        "state_error_pct": round(100 * miss.abs().sum() / actual.sum(), 2),
        "total_error_pct": round(100 * miss.sum() / actual.sum(), 2),
    }


def backtest(table: pd.DataFrame, last_year: int = LAST_BASELINE_YEAR) -> pd.DataFrame:
    """Expanding window: each year scored by models fitted on earlier years only, beside same-as-last-year.

    Every predictor is scored twice: on all states, and on the states that have a satellite value
    that year (``scope`` column).
    """
    usable = table[(table["year"] <= last_year) & table["target"].notna() & table["reversion"].notna()]
    years = sorted(usable["year"].unique())
    results = []
    for year in years[MIN_FIT_YEARS:]:
        fit_rows, score_rows = usable[usable["year"] < year], usable[usable["year"] == year]
        predictions = {"same_as_last_year": score_rows["silage_last"]}
        for name, features in FEATURE_SETS.items():
            predict = fit_ridge(fit_rows, features)
            predictions[name] = score_rows["silage_last"] * np.exp(predict(score_rows))
        # Nothing fitted: last year's acres moved by the satellite share and by planted acres.
        ratio = (score_rows["sat_ratio"] * np.exp(score_rows["d_planted"])).fillna(1.0)
        predictions["satellite_ratio"] = score_rows["silage_last"] * ratio

        sampled = score_rows["d_sat"].notna()
        for scope, rows in [("all_states", score_rows.index), ("sampled_states", score_rows.index[sampled])]:
            if len(rows) == 0:
                continue
            for name, predicted in predictions.items():
                results.append({"year": year, "scope": scope, "predictor": name,
                                **state_error(predicted.loc[rows], score_rows.loc[rows, "silage"])})
    return pd.DataFrame(results)


def main() -> None:
    data = data_dir()
    table = add_changes(pd.read_csv(data / "panel" / "state_year.csv"))
    results = backtest(table)

    usable = table[(table["year"] <= LAST_BASELINE_YEAR) & table["target"].notna() & table["reversion"].notna()]
    weights = pd.DataFrame([{"feature": k, "weight_per_std": v}
                            for k, v in fit_ridge(usable, FEATURES).weights.items()])

    out = data / "models"
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in {"state_model_backtest": results, "state_model_weights": weights}.items():
        frame.to_csv(out / f"{name}.csv", index=False, lineterminator="\n")
        record_in_manifest(out / f"{name}.csv", "derived: kernelag.state_model")

    pd.set_option("display.width", 220)
    for scope, part in results.groupby("scope"):
        print(f"== {scope}: state error by year (%), states scored: "
              f"{part.groupby('year')['n_states'].first().to_dict()}")
        print(part.pivot(index="year", columns="predictor", values="state_error_pct").to_string())
        print("mean state error:", part.groupby("predictor")["state_error_pct"].mean().round(2).to_dict())
        print("mean absolute error of the total:",
              part.groupby("predictor")["total_error_pct"].apply(lambda s: s.abs().mean()).round(2).to_dict())
    print(weights.to_string(index=False))


if __name__ == "__main__":
    main()
