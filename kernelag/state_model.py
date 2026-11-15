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
    """Expanding window: each year scored by models fitted on earlier years only, beside same-as-last-year."""
    usable = table[(table["year"] <= last_year) & table["target"].notna() & table["reversion"].notna()]
    years = sorted(usable["year"].unique())
    results = []
    for year in years[MIN_FIT_YEARS:]:
        fit_rows, score_rows = usable[usable["year"] < year], usable[usable["year"] == year]
        results.append({"year": year, "predictor": "same_as_last_year",
                        **state_error(score_rows["silage_last"], score_rows["silage"])})
        for name, features in FEATURE_SETS.items():
            predict = fit_ridge(fit_rows, features)
            predicted = score_rows["silage_last"] * np.exp(predict(score_rows))
            results.append({"year": year, "predictor": name, **state_error(predicted, score_rows["silage"])})
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

    pd.set_option("display.width", 200)
    print(results.pivot(index="year", columns="predictor", values="state_error_pct").to_string())
    print("mean state error:")
    print(results.groupby("predictor")["state_error_pct"].mean().round(2).to_string())
    print("mean absolute error of the US total:")
    print(results.groupby("predictor")["total_error_pct"].apply(lambda s: s.abs().mean()).round(2).to_string())
    print(weights.to_string(index=False))


if __name__ == "__main__":
    main()
