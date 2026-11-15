"""State and US corn acres for silage and for grain, from what is public before NASS's January report.

Silage. NASS publishes no in-season silage figure, so the number to beat is last year's acres.
The model predicts the year-on-year change in a state's silage acres (in logs) from changes that are
public by the ``asof`` date of the same year (``kernelag.state_panel``, ``kernelag.context``):

    reversion     last year's silage against its previous three-year mean (a high year falls back)
    d_planted     change in planted corn acres
    d_not_grain   change in the share of planted acres NASS does not expect to be combined
    d_cows        change in milk cows on 1 January
    d_cattle      change in all cattle on 1 January
    yield_shock   NASS's latest grain-yield forecast against the state's previous three-year mean
    d_price       change in the September corn price
    d_drought     change in the June-to-September share of the state in drought (D2 or worse)
    d_poor        change in the share of corn rated poor or very poor
    d_loss        change in the share of insured corn acres with a weather loss
    rain_anom     May-to-September rain against the state's earlier years
    early_frost   share of the state's corn with a hard freeze before 7 October
    d_mature      change in percent of corn mature in late September

It is one pooled ridge regression for all states, weighted by silage acres, with a missing change
read as "no change". Each year is predicted by a model fitted on earlier years only. Every feature
has a sign we expected before fitting (``EXPECTED_SIGN``); the weights table shows whether the data agree.

Grain. NASS's own latest harvested-for-grain forecast where it publishes one (33 states); elsewhere
the latest planted acres times last year's grain share of planted; failing that, last year's acres.

Which silage feature set is used is decided by a rule fixed in advance, on years up to 2024 only:
the smallest set whose mean state error is within ``SELECTION_TOLERANCE`` points of the best.

Intervals come from the backtest's own errors: quantiles of log(actual / predicted), pooled within
three state size classes. The US interval uses the spread of the backtest's US-total errors.

The scoring year (2025) is excluded from fitting, selection and the backtest. ``--score-2025``
writes the held-out comparison once and refuses to overwrite it.

Outputs (``data/models/``): state_model_backtest.csv, state_model_weights.csv, state_model_bias.csv,
state_model_metrics.json, state_forecast_<year>.csv, state_score_2025.csv

Run: ``python -m kernelag.state_model [--asof sep] [--forecast 2026] [--score-2025]``
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from kernelag.context import ASOF_MONTH
from kernelag.nass import LAST_BASELINE_YEAR
from kernelag.paths import data_dir, record_in_manifest
from kernelag.state_panel import load_panel

# +1: we expect more silage when the feature rises; -1: less.
EXPECTED_SIGN = {
    "reversion": -1, "d_planted": +1, "d_not_grain": +1, "d_cows": +1, "d_cattle": +1,
    "yield_shock": -1, "d_price": -1, "d_drought": +1, "d_poor": +1, "d_loss": +1,
    "rain_anom": -1, "early_frost": +1, "d_mature": -1, "d_sat": +1,
}
SATELLITE_FEATURES = ["d_sat"]      # sampled states only; kept out of "all_public"
FEATURES = [name for name in EXPECTED_SIGN if name not in SATELLITE_FEATURES]
FEATURE_SETS = {
    "reversion_only": ["reversion"],
    "nass_acres": ["reversion", "d_planted", "d_not_grain"],
    "stress": ["reversion", "d_drought", "d_poor", "yield_shock", "d_loss"],
    "all_public": FEATURES,
    "reversion_plus_satellite": ["reversion", "d_sat"],   # scored only when satellite shares exist
}
MIN_FIT_YEARS = 3
RIDGE_PENALTY = 1.0
SELECTION_TOLERANCE = 0.3          # points of mean state error
SCORING_YEAR = LAST_BASELINE_YEAR + 1
INTERVALS = {"80": (0.10, 0.90), "90": (0.05, 0.95)}
Z = {"80": 1.2816, "90": 1.6449}   # normal quantiles, used for the US total only
SIZE_CLASSES = 3

REGIONS = {
    "dairy": ["WISCONSIN", "NEW YORK", "CALIFORNIA", "PENNSYLVANIA", "MICHIGAN", "IDAHO", "VERMONT",
              "WASHINGTON", "NEW MEXICO", "ARIZONA", "OREGON", "UTAH"],
    "plains": ["KANSAS", "NEBRASKA", "SOUTH DAKOTA", "NORTH DAKOTA", "TEXAS", "COLORADO", "OKLAHOMA",
               "MONTANA", "WYOMING"],
    "corn_belt": ["IOWA", "ILLINOIS", "INDIANA", "OHIO", "MINNESOTA", "MISSOURI"],
}


def region_of(state: str) -> str:
    return next((name for name, states in REGIONS.items() if state in states), "other")


# --- features ------------------------------------------------------------------------------------

def add_changes(panel: pd.DataFrame) -> pd.DataFrame:
    """Add last year's values, the target change and the predictor changes to the state-year panel."""
    table = panel.sort_values(["state", "year"]).copy()

    def last(column: str, years_back: int = 1) -> pd.Series:
        """The value ``years_back`` calendar years earlier (missing if that year is absent)."""
        if column not in table:
            return pd.Series(np.nan, index=table.index)
        shifted = table[["state", "year", column]].assign(year=table["year"] + years_back)
        return table[["state", "year"]].merge(shifted, on=["state", "year"], how="left")[column].set_axis(table.index)

    def now(column: str) -> pd.Series:
        return table[column] if column in table else pd.Series(np.nan, index=table.index)

    def mean_of_last_three(column: str) -> pd.Series:
        return pd.concat([last(column, k) for k in (1, 2, 3)], axis=1).mean(axis=1, skipna=False)

    with np.errstate(divide="ignore", invalid="ignore"):
        table["silage_last"] = last("silage")
        table["grain_last"] = last("grain")
        table["planted_last"] = last("planted")
        table["target"] = np.log(table["silage"] / table["silage_last"])
        table["reversion"] = np.log(table["silage_last"] / pd.concat(
            [last("silage", k) for k in (2, 3, 4)], axis=1).mean(axis=1, skipna=False))
        table["d_planted"] = np.log(table["planted_asof"] / table["planted_last"])
        not_grain = 1 - table["grain_asof"] / table["planted_asof"]
        table["d_not_grain"] = not_grain - (1 - table["grain_last"] / table["planted_last"])
        table["d_cows"] = np.log(table["milk_cows"] / last("milk_cows"))
        table["d_cattle"] = np.log(table["cattle"] / last("cattle"))
        table["yield_shock"] = np.log(table["grain_yield_asof"] / mean_of_last_three("grain_yield"))
        table["d_price"] = np.log(table["corn_price_sep"] / last("corn_price_sep"))
    table["d_drought"] = now("drought") - last("drought")
    table["d_poor"] = now("poor_condition") - last("poor_condition")
    table["d_loss"] = now("loss_share") - last("loss_share")
    table["d_mature"] = (now("mature_wk38") - last("mature_wk38")) / 100
    for column in ["rain_anom", "early_frost"]:
        table[column] = now(column)
    # Satellite silage-like share on the state's fixed sample areas. Its level is biased, so only
    # its change is used: in log-odds (fitted) and as a plain ratio (nothing fitted).
    with np.errstate(divide="ignore", invalid="ignore"):
        share, share_last = now("sat_share"), last("sat_share")
        table["d_sat"] = np.log(share / (1 - share)) - np.log(share_last / (1 - share_last))
        table["sat_ratio"] = share / share_last
    return table.replace([np.inf, -np.inf], np.nan)


def active_feature_sets(table: pd.DataFrame) -> dict[str, list[str]]:
    """The feature sets that can be scored: satellite sets need at least one satellite change."""
    has_satellite = "d_sat" in table and table["d_sat"].notna().any()
    return {name: features for name, features in FEATURE_SETS.items()
            if has_satellite or not set(features) & set(SATELLITE_FEATURES)}


# --- silage model --------------------------------------------------------------------------------

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


def predict_silage(table: pd.DataFrame, year: int, features: list[str]) -> pd.Series:
    """Silage acres for ``year`` per state, from a model fitted on earlier years only."""
    fit_rows = table[(table["year"] < year) & table["target"].notna()]
    rows = table[(table["year"] == year) & table["silage_last"].notna()]
    change = fit_ridge(fit_rows, features)(rows) if features else 0.0
    return pd.Series(rows["silage_last"].to_numpy() * np.exp(change), index=rows["state"].to_numpy())


def predict_grain(table: pd.DataFrame, year: int) -> pd.DataFrame:
    """Grain acres for ``year`` per state and the method used (no fitting involved)."""
    rows = table[table["year"] == year].set_index("state")
    by_share = rows["planted_asof"] * rows["grain_last"] / rows["planted_last"]
    acres = rows["grain_asof"].fillna(by_share).fillna(rows["grain_last"])
    method = np.where(rows["grain_asof"].notna(), "nass_forecast",
                      np.where(by_share.notna(), "planted_x_last_share", "same_as_last_year"))
    return pd.DataFrame({"grain": acres, "grain_method": method}).dropna(subset=["grain"])


# --- backtest ------------------------------------------------------------------------------------

def state_error(predicted: pd.Series, actual: pd.Series) -> dict:
    """Share of acres put in the wrong state, and the error of the summed total."""
    miss = predicted - actual
    return {
        "n_states": len(actual),
        "state_error_pct": round(100 * miss.abs().sum() / actual.sum(), 2),
        "total_error_pct": round(100 * miss.sum() / actual.sum(), 2),
    }


def backtest_predictions(table: pd.DataFrame, last_year: int = LAST_BASELINE_YEAR) -> pd.DataFrame:
    """Every held-out prediction: year, state, series, predictor, predicted, actual, last.

    Expanding window: each year is predicted from earlier years only, after ``MIN_FIT_YEARS`` years.
    """
    usable = table[(table["year"] <= last_year) & table["target"].notna()]
    years = sorted(usable["year"].unique())[MIN_FIT_YEARS:]
    feature_sets = active_feature_sets(table)
    parts = []
    for year in years:
        truth = table[table["year"] == year].set_index("state")
        silage = {"same_as_last_year": predict_silage(usable, year, [])}
        silage.update({name: predict_silage(usable, year, features) for name, features in feature_sets.items()})
        if len(feature_sets) == len(FEATURE_SETS):   # satellite shares exist
            # Nothing fitted: last year's acres moved by the satellite share and by planted acres.
            ratio = (truth["sat_ratio"] * np.exp(truth["d_planted"].fillna(0.0))).fillna(1.0)
            silage["satellite_ratio"] = (truth["silage_last"] * ratio).dropna()
        grain = {"same_as_last_year": truth["grain_last"].dropna(), "nass_latest": predict_grain(table, year)["grain"]}
        for series, predictions in [("silage", silage), ("grain", grain)]:
            for name, predicted in predictions.items():
                part = pd.DataFrame({"predicted": predicted, "actual": truth[series],
                                     "last": truth[f"{series}_last"]}).dropna()
                part["sampled"] = truth["d_sat"].notna().reindex(part.index).to_numpy()
                parts.append(part.rename_axis("state").reset_index().assign(year=year, series=series, predictor=name))
    columns = ["year", "state", "series", "predictor", "predicted", "actual", "last", "sampled"]
    return pd.concat(parts, ignore_index=True)[columns] if parts else pd.DataFrame(columns=columns)


def backtest(table: pd.DataFrame, last_year: int = LAST_BASELINE_YEAR) -> pd.DataFrame:
    """State error and US-total error per year, series and predictor.

    Scored twice (``scope``): on all states, and on the states with a satellite change that year.
    """
    held_out = backtest_predictions(table, last_year)
    scopes = {"all_states": held_out, "sampled_states": held_out[held_out["sampled"].astype(bool)]}
    rows = [
        {"scope": scope, "year": year, "series": series, "predictor": name,
         **state_error(group["predicted"], group["actual"])}
        for scope, part in scopes.items()
        for (year, series, name), group in part.groupby(["year", "series", "predictor"], sort=False)
    ]
    return pd.DataFrame(rows, columns=["scope", "year", "series", "predictor", "n_states",
                                       "state_error_pct", "total_error_pct"])


def select_feature_set(results: pd.DataFrame) -> str:
    """The smallest silage feature set within ``SELECTION_TOLERANCE`` points of the best mean state error."""
    silage = results[(results["series"] == "silage") & results["predictor"].isin(list(FEATURE_SETS))
                     & (results["scope"] == "all_states")]
    mean_error = silage.groupby("predictor")["state_error_pct"].mean()
    close = [name for name in FEATURE_SETS
             if name in mean_error.index and mean_error[name] <= mean_error.min() + SELECTION_TOLERANCE]
    return min(close, key=lambda name: len(FEATURE_SETS[name]))   # FEATURE_SETS order breaks ties


def bias_table(held_out: pd.DataFrame, predictors: dict[str, str]) -> pd.DataFrame:
    """Signed error (predicted minus actual, percent of actual acres) by year and by region."""
    rows = []
    for series, name in predictors.items():
        chosen = held_out[(held_out["series"] == series) & (held_out["predictor"] == name)]
        chosen = chosen.assign(region=chosen["state"].map(region_of))
        for label, column in [("year", "year"), ("region", "region")]:
            for key, group in chosen.groupby(column):
                rows.append({"series": series, "predictor": name, "by": label, "group": key,
                             "n": len(group), "signed_error_pct":
                             round(100 * (group["predicted"] - group["actual"]).sum() / group["actual"].sum(), 2)})
    return pd.DataFrame(rows)


# --- intervals -----------------------------------------------------------------------------------

def size_class_edges(last: pd.Series) -> np.ndarray:
    """Acre thresholds that split states into ``SIZE_CLASSES`` equal groups by last year's acres."""
    return np.quantile(last, np.linspace(0, 1, SIZE_CLASSES + 1)[1:-1])


def error_quantiles(held_out: pd.DataFrame) -> dict:
    """Quantiles of log(actual / predicted) per size class, and the class thresholds."""
    edges = size_class_edges(held_out["last"])
    size = np.searchsorted(edges, held_out["last"].to_numpy())
    log_error = np.log(held_out["actual"] / held_out["predicted"]).to_numpy()
    levels = sorted({q for pair in INTERVALS.values() for q in pair})
    return {"edges": edges, "levels": levels,
            "quantiles": {c: np.quantile(log_error[size == c], levels) for c in range(SIZE_CLASSES)}}


def add_intervals(predicted: pd.Series, last: pd.Series, errors: dict, prefix: str) -> pd.DataFrame:
    """Lower and upper bounds per state for each interval in ``INTERVALS``."""
    size = np.searchsorted(errors["edges"], last.reindex(predicted.index).to_numpy())
    out = pd.DataFrame(index=predicted.index)
    for name, (low, high) in INTERVALS.items():
        for bound, level in [("lo", low), ("hi", high)]:
            q = np.array([errors["quantiles"][c][errors["levels"].index(level)] for c in size])
            out[f"{prefix}_{bound}{name}"] = predicted.to_numpy() * np.exp(q)
    return out


def interval_coverage(held_out: pd.DataFrame) -> dict:
    """Share of held-out state-years inside each interval, with the quantiles taken from the other years."""
    inside = {name: [] for name in INTERVALS}
    for year in held_out["year"].unique():
        errors = error_quantiles(held_out[held_out["year"] != year])
        rows = held_out[held_out["year"] == year].set_index("state")
        bounds = add_intervals(rows["predicted"], rows["last"], errors, "x")
        for name in INTERVALS:
            inside[name].extend((rows["actual"] >= bounds[f"x_lo{name}"]) & (rows["actual"] <= bounds[f"x_hi{name}"]))
    return {name: round(float(np.mean(flags)), 3) for name, flags in inside.items()}


def us_log_error_rms(held_out: pd.DataFrame) -> float:
    """Root mean square of the backtest's yearly log(actual US total / predicted US total)."""
    totals = held_out.groupby("year")[["actual", "predicted"]].sum()
    return float(np.sqrt((np.log(totals["actual"] / totals["predicted"]) ** 2).mean()))


# --- forecast ------------------------------------------------------------------------------------

def forecast(table: pd.DataFrame, year: int, feature_set: str, held_out: pd.DataFrame) -> pd.DataFrame:
    """State and US acres for ``year`` with intervals; fitted on years before ``year`` only."""
    silage = predict_silage(table, year, FEATURE_SETS[feature_set])
    if silage.empty:
        raise ValueError(f"no state has silage acres for {year - 1}; cannot forecast {year}")
    rows = table[table["year"] == year].set_index("state")
    out = pd.DataFrame({"silage": silage}).join(predict_grain(table, year), how="left")

    # Grain intervals must match how grain was predicted: without any NASS in-season figure the
    # prediction is last year's acres, whose backtest errors are several times wider.
    in_season = out.loc[out["grain_method"] != "same_as_last_year", "grain"].sum()
    grain_errors = "nass_latest" if in_season >= 0.5 * out["grain"].sum() else "same_as_last_year"
    chosen = {"silage": feature_set, "grain": grain_errors}
    rms = {}
    for series, name in chosen.items():
        errors_rows = held_out[(held_out["series"] == series) & (held_out["predictor"] == name)]
        have = out[series].dropna()
        out = out.join(add_intervals(have, rows[f"{series}_last"], error_quantiles(errors_rows), series))
        rms[series] = us_log_error_rms(errors_rows)
    out = out.rename_axis("state").reset_index().assign(year=year, silage_method=feature_set)

    us = {"state": "US (sum of states shown)", "year": year, "silage_method": feature_set, "grain_method": "sum"}
    for series in chosen:
        total = out[series].sum()
        us[series] = total
        for name in INTERVALS:
            us[f"{series}_lo{name}"] = total * np.exp(-Z[name] * rms[series])
            us[f"{series}_hi{name}"] = total * np.exp(Z[name] * rms[series])
    out = pd.concat([pd.DataFrame([us]), out.sort_values("silage", ascending=False)], ignore_index=True)
    acre_columns = [c for c in out.columns if c.startswith(("silage", "grain")) and not c.endswith("method")]
    out[acre_columns] = out[acre_columns].round(-2)          # NASS publishes to the nearest thousand at best
    ordered = [f"{series}{part}" for series in chosen
               for part in ["", *[f"_{bound}{name}" for name in INTERVALS for bound in ("lo", "hi")]]]
    return out[["year", "state", *ordered, "silage_method", "grain_method"]]


def score(forecast_table: pd.DataFrame, table: pd.DataFrame, year: int) -> tuple[pd.DataFrame, dict]:
    """A forecast beside NASS's final acres for ``year``, and the summary errors."""
    truth = table[table["year"] == year].set_index("state")
    states = forecast_table[~forecast_table["state"].str.startswith("US")].set_index("state")
    compared = states.join(truth[["silage", "grain", "silage_last", "grain_last"]], rsuffix="_actual")
    summary = {}
    for series in ["silage", "grain"]:
        rows = compared.dropna(subset=[series, f"{series}_actual"])
        summary[series] = {
            "model": state_error(rows[series], rows[f"{series}_actual"]),
            "same_as_last_year": state_error(rows[f"{series}_last"], rows[f"{series}_actual"]),
            "inside_80": round(float(((rows[f"{series}_actual"] >= rows[f"{series}_lo80"])
                                      & (rows[f"{series}_actual"] <= rows[f"{series}_hi80"])).mean()), 3),
        }
    return compared.reset_index(), summary


# --- command line --------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asof", choices=list(ASOF_MONTH), default="nov", help="forecast date: the 15th of this month")
    parser.add_argument("--forecast", type=int, metavar="YEAR", help="write state_forecast_<YEAR>.csv")
    parser.add_argument("--score-2025", action="store_true", help="score the held-out year, once")
    args = parser.parse_args()

    table = add_changes(load_panel(args.asof))
    held_out = backtest_predictions(table)
    all_scopes = backtest(table)
    results = all_scopes[all_scopes["scope"] == "all_states"]
    sampled = all_scopes[(all_scopes["scope"] == "sampled_states") & (all_scopes["series"] == "silage")]
    feature_set = select_feature_set(results)
    chosen = {"silage": feature_set, "grain": "nass_latest"}
    chosen_rows = {s: held_out[(held_out["series"] == s) & (held_out["predictor"] == n)] for s, n in chosen.items()}

    usable = table[(table["year"] <= LAST_BASELINE_YEAR) & table["target"].notna()]
    fitted = fit_ridge(usable, FEATURES).weights
    weights = pd.DataFrame([
        {"feature": name, "weight_per_std": value, "expected_sign": EXPECTED_SIGN[name],
         "sign_ok": bool(value == 0 or np.sign(value) == EXPECTED_SIGN[name]),
         "in_selected_set": name in FEATURE_SETS[feature_set]}
        for name, value in fitted.items()
    ])
    mean_error = results.groupby(["series", "predictor"])[["state_error_pct", "total_error_pct"]].agg(
        state_error_pct=("state_error_pct", "mean"), abs_total_error_pct=("total_error_pct", lambda s: s.abs().mean()))
    metrics = {
        "asof": args.asof, "backtest_years": sorted(int(y) for y in results["year"].unique()),
        "selected_silage_set": feature_set, "selection_tolerance_points": SELECTION_TOLERANCE,
        "mean_errors_pct": {f"{s}.{p}": row.round(2).to_dict() for (s, p), row in mean_error.iterrows()},
        "interval_coverage": {s: interval_coverage(rows) for s, rows in chosen_rows.items()},
        "us_log_error_rms": {s: round(us_log_error_rms(rows), 4) for s, rows in chosen_rows.items()},
        "sampled_states_silage_errors_pct": sampled.groupby("predictor")["state_error_pct"].mean().round(2).to_dict(),
        "caveats": ["RMA loss files are today's vintage, not the vintage of each past November",
                    f"{SCORING_YEAR} is excluded from fitting, selection and this backtest"],
    }

    out = data_dir() / "models"
    out.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.asof == "nov" else f"_asof_{args.asof}"
    frames = {"state_model_backtest": all_scopes, "state_model_weights": weights,
              "state_model_bias": bias_table(held_out, chosen)}
    for name, frame in frames.items():
        frame.to_csv(out / f"{name}{suffix}.csv", index=False, lineterminator="\n")
        record_in_manifest(out / f"{name}{suffix}.csv", "derived: kernelag.state_model")
    metrics_file = out / f"state_model_metrics{suffix}.json"
    metrics_file.write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")
    record_in_manifest(metrics_file, "derived: kernelag.state_model")

    pd.set_option("display.width", 250)
    for series in ["silage", "grain"]:
        part = results[results["series"] == series]
        print(f"\n{series}: state error %, by year")
        print(part.pivot(index="year", columns="predictor", values="state_error_pct").to_string())
        print(mean_error.loc[series].round(2).to_string())
    print(f"\nselected silage set: {feature_set}")
    print(weights.to_string(index=False))
    print("interval coverage (target 0.80 and 0.90):", metrics["interval_coverage"])
    print(frames["state_model_bias"].pivot_table(index=["by", "group"], columns="series", values="signed_error_pct").to_string())

    if args.forecast:
        target = out / f"state_forecast_{args.forecast}{suffix}.csv"
        if args.forecast <= SCORING_YEAR:
            parser.error(f"--forecast is for years after {SCORING_YEAR}; use --score-2025 for the scoring year")
        result = forecast(table, args.forecast, feature_set, held_out)
        result.to_csv(target, index=False, lineterminator="\n")
        record_in_manifest(target, "derived: kernelag.state_model")
        print(f"\nforecast {args.forecast} -> {target}")
        print(result.head(12).to_string(index=False))
        missing = table[(table["year"] == args.forecast)][["planted_asof", "grain_asof"]].isna().all()
        for column in missing[missing].index:
            print(f"NOTE: no {column} rows for {args.forecast}; that input is read as 'no change'")

    if args.score_2025:
        target = out / f"state_score_{SCORING_YEAR}{suffix}.csv"
        if target.exists():
            parser.error(f"{target} exists: the scoring year is scored once. Delete it by hand to redo.")
        compared, summary = score(forecast(table, SCORING_YEAR, feature_set, held_out), table, SCORING_YEAR)
        compared.to_csv(target, index=False, lineterminator="\n")
        record_in_manifest(target, "derived: kernelag.state_model")
        summary_file = out / f"state_score_{SCORING_YEAR}{suffix}.json"
        summary_file.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        record_in_manifest(summary_file, "derived: kernelag.state_model")
        print(f"\nscored {SCORING_YEAR} -> {target}")
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
