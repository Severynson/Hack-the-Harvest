"""Fixed, small slate of state silage acreage models; strictly expanding-year fitting.

Run from the repository root:
    .venv/bin/python test_models/accuracy/state_candidates.py [--force]

This is a retrospective replay, not a pristine held-out test. No outcome from 2025 or later
is scored or used for fitting. Development and reserve summaries remain separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
import xgboost
from sklearn.impute import SimpleImputer
from sklearn.linear_model import HuberRegressor, QuantileRegressor, Ridge
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCES = [REPO / "test_models" / name / "out" / "panel_nov.csv" for name in ("danielModel", "model")]
SOURCE = next((path for path in SOURCES if path.exists()), SOURCES[0])
OUT = HERE / "state"
YEARS = tuple(range(2012, 2025))
CORE = ["reversion", "d_planted", "d_not_grain", "yield_shock"]
CONTEXT = CORE + [
    "d_cows", "d_drought", "d_poor", "d_pasture", "d_hay_stocks", "d_hay_price",
    "d_milk_price", "rain_anomaly", "gdd_anomaly", "hot_days", "early_freeze",
    "late_planting", "maturity", "drought_level", "poor_level", "log_last_acres",
    "last_silage_share", "cow_density", "calendar_year",
]
SLATE = {
    "same_as_last_year": {"kind": "persistence", "features": []},
    "ridge_reversion": {"kind": "ridge", "features": ["reversion"], "alpha": 100.0},
    "ridge_core": {"kind": "ridge", "features": CORE, "alpha": 100.0},
    "ridge_context": {"kind": "ridge", "features": CONTEXT, "alpha": 100.0},
    "lad_core": {"kind": "lad", "features": CORE, "alpha": 0.001},
    "huber_context": {"kind": "huber", "features": CONTEXT, "alpha": 1.0, "epsilon": 1.35},
    "ridge_partial_pool": {"kind": "partial_pool", "features": CORE, "alpha": 100.0, "shrink_years": 10},
    "state_trend": {"kind": "trend", "features": ["reversion"], "alpha": 100.0, "lookback": 5, "trend_weight": 0.25},
    "xgb_depth2": {"kind": "xgb", "features": CONTEXT, "max_depth": 2, "n_estimators": 120, "min_child_weight": 30},
    "xgb_depth3": {"kind": "xgb", "features": CONTEXT, "max_depth": 3, "n_estimators": 160, "min_child_weight": 40},
    "fixed_ensemble": {"kind": "ensemble", "members": ["ridge_core", "lad_core", "xgb_depth2"], "weights": [1/3]*3},
}
REGION = {
    "WI": "dairy", "NY": "dairy", "CA": "dairy", "PA": "dairy", "MI": "dairy", "ID": "dairy",
    "VT": "dairy", "WA": "dairy", "NM": "dairy", "AZ": "dairy", "OR": "dairy", "UT": "dairy",
    "KS": "plains", "NE": "plains", "SD": "plains", "ND": "plains", "TX": "plains", "CO": "plains",
    "OK": "plains", "MT": "plains", "WY": "plains", "IA": "corn_belt", "IL": "corn_belt",
    "IN": "corn_belt", "OH": "corn_belt", "MN": "corn_belt", "MO": "corn_belt",
}
CAVEATS = [
    "Retrospective replay: historical outcomes have already been inspected by the team; reserve is not pristine.",
    "Fixed 11-candidate slate; 2012–2020 development chooses the displayed development winner; 2021–2024 is summarized separately.",
    "No 2025+ outcomes are fitted, scored, or used in selection. Reserve outcomes enter training only in later forecast years.",
    "Current-year final silage, final grain and final yield are never predictors; earlier calendar-year final values supply lags.",
    "The source panel substitutes revised final planted acres before 2018 where historical in-season acres are absent; this is not a vintage-exact replay.",
    "Other source files and lagged finals are current revised vintages. This compares model methods on an existing panel, not historical publication snapshots.",
    "Every available outcome state is retained. A missing lag uses the most recent earlier observed silage; if no earlier value exists, it uses zero and is flagged.",
    "No state satellite feature is present in this source panel. These experiments model silage only and make no grain improvement claim.",
    "Candidate hyperparameters are fixed; no search, reserve-driven retuning, or selection on national total error.",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_lag(table: pd.DataFrame, column: str, years: int) -> pd.Series:
    """Join on calendar year rather than shifting the previous available row."""
    prior = table[["state", "year", column]].rename(columns={column: "lag_value"})
    prior["year"] = prior["year"] + years
    return table[["state", "year"]].merge(prior, on=["state", "year"], how="left", validate="one_to_one")["lag_value"].set_axis(table.index)


def logratio(a: pd.Series, b: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.log(a.where(a > 0) / b.where(b > 0))
    return result.replace([np.inf, -np.inf], np.nan)


def features(raw: pd.DataFrame) -> pd.DataFrame:
    """All transformations are row-local or use exact, strictly earlier-year joins."""
    table = raw.sort_values(["state", "year"]).reset_index(drop=True).copy()
    if table.duplicated(["state", "year"]).any():
        raise ValueError("duplicate state-year in source")
    def lag(name, years=1):
        return exact_lag(table, name, years)

    def prior_mean(name, years):
        return pd.concat([lag(name, k) for k in years], axis=1).mean(axis=1)
    last = lag("silage")
    # Most recent earlier observation is a disclosed persistence fallback, never a future fill.
    earlier = table.groupby("state")["silage"].transform(lambda s: s.shift().ffill())
    table["baseline"] = last.where(last > 0).fillna(earlier).fillna(0.0)
    table["fallback_baseline"] = last.isna() | (last <= 0)
    table["target"] = table["silage"] / last - 1.0
    table.loc[(last <= 0) | last.isna(), "target"] = np.nan
    table["reversion"] = logratio(last, prior_mean("silage", (2, 3, 4)))
    table["d_planted"] = logratio(table["planted_asof"], lag("planted"))
    table["d_not_grain"] = ((1-table["grain_asof"]/table["planted_asof"]) - (1-lag("grain")/lag("planted")))
    table["yield_shock"] = logratio(table["yield_asof"], prior_mean("yield", (1, 2, 3)))
    for feature, name in [("d_cows", "milk_cows"), ("d_hay_stocks", "hay_stocks_may"),
                          ("d_hay_price", "hay_price"), ("d_milk_price", "milk_price")]:
        table[feature] = logratio(table[name], lag(name))
    for feature, name in [("d_drought", "drought_d2"), ("d_poor", "cond_poor"), ("d_pasture", "pasture_poor")]:
        table[feature] = (table[name] - lag(name))/100
    table["rain_anomaly"] = logratio(table["rain"], prior_mean("rain", (1, 2, 3)))
    table["gdd_anomaly"] = logratio(table["gdd"], prior_mean("gdd", (1, 2, 3)))
    table["late_planting"] = (prior_mean("planted_may20", (1, 2, 3)) - table["planted_may20"])/100
    table["maturity"] = table["mature_sep22"]/100
    table["drought_level"] = table["drought_d2"]/100
    table["poor_level"] = table["cond_poor"]/100
    table["log_last_acres"] = np.log(last.where(last > 0))
    table["last_silage_share"] = last/lag("planted")
    table["cow_density"] = table["milk_cows"]/table["planted_asof"]
    table["calendar_year"] = table["year"] - 2000
    # Fixed geographic labels encode only known state identity, not outcomes or fitted clusters.
    for region in ["dairy", "plains", "corn_belt", "other"]:
        table["region_"+region] = (table["state"].map(REGION).fillna("other") == region).astype(float)
    return table.replace([np.inf, -np.inf], np.nan)


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, spec: dict) -> np.ndarray:
    """Relative acreage change; transforms are fitted to training rows only."""
    names = list(spec["features"])
    if spec["kind"] in ("xgb", "partial_pool"):
        names += [c for c in train.columns if c.startswith("region_")]
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    x = imputer.fit_transform(train[names])
    future = imputer.transform(test[names])
    scaler = StandardScaler().fit(x)
    x, future = scaler.transform(x), scaler.transform(future)
    target = train["target"].to_numpy()
    weights = train["baseline"].to_numpy()
    weights = weights/weights.mean()
    kind = spec["kind"]
    if kind == "xgb":
        model = XGBRegressor(objective="reg:absoluteerror", n_estimators=spec["n_estimators"],
                             max_depth=spec["max_depth"], min_child_weight=spec["min_child_weight"],
                             learning_rate=.03, reg_lambda=20, subsample=1, colsample_bytree=1,
                             tree_method="hist", n_jobs=1, random_state=0, verbosity=0)
    elif kind == "huber":
        model = HuberRegressor(alpha=spec["alpha"], epsilon=spec["epsilon"], max_iter=2000, tol=1e-7)
    elif kind == "lad":
        model = QuantileRegressor(quantile=.5, alpha=spec["alpha"], solver="highs")
    else:
        model = Ridge(alpha=spec["alpha"], fit_intercept=False)
    model.fit(x, target, sample_weight=weights)
    predicted = model.predict(future)
    if kind == "partial_pool":
        residuals = train.assign(residual=target-model.predict(x)).groupby("state")["residual"].agg(["mean", "size"])
        bias = residuals["mean"] * residuals["size"]/(residuals["size"] + spec["shrink_years"])
        predicted += test["state"].map(bias).fillna(0.0).to_numpy()
    elif kind == "trend":
        recent = train[train["year"] >= int(test["year"].iloc[0])-spec["lookback"]]
        means = recent.groupby("state")["target"].median().clip(-.1,.1)
        predicted = ((1-spec["trend_weight"])*predicted + spec["trend_weight"]*test["state"].map(means).fillna(0).to_numpy())
    # A broad fixed plausibility constraint prevents tiny-state or sparse-feature explosions.
    return np.clip(predicted, -.5, 1.0)


def evaluate(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions, audit = [], []
    for year in YEARS:
        train = table[(table["year"] < year) & table["target"].notna() & (table["baseline"] > 0)].copy()
        test = table[table["year"] == year].copy()
        assert len(train) and train["year"].max() < year
        cache = {}
        for name, spec in SLATE.items():
            started = time.perf_counter()
            if spec["kind"] == "persistence":
                predicted = test["baseline"].to_numpy()
            elif spec["kind"] == "ensemble":
                predicted = sum(w*cache[member] for w, member in zip(spec["weights"], spec["members"]))
            else:
                change = fit_predict(train, test, spec)
                predicted = test["baseline"].to_numpy()*(1+change)
                predicted = np.where(test["fallback_baseline"], test["baseline"], predicted)
            predicted = np.where(np.isfinite(predicted), np.maximum(predicted,0), test["baseline"])
            cache[name] = predicted
            part = test[["state", "year", "silage", "baseline", "fallback_baseline"]].rename(columns={"silage":"actual"})
            part = part.assign(candidate=name, predicted=predicted)
            predictions.append(part)
            audit.append({"year":year, "candidate":name, "train_min_year":int(train["year"].min()),
                          "train_max_year":int(train["year"].max()), "train_rows":len(train), "prediction_rows":len(test),
                          "seconds":round(time.perf_counter()-started,4)})
        print(f"{year}: {len(test)} states, training through {int(train['year'].max())}", flush=True)
    return pd.concat(predictions,ignore_index=True), pd.DataFrame(audit)


def metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (candidate, year), part in predictions.groupby(["candidate","year"]):
        have=part[part["actual"].notna()].copy()
        errors=have["predicted"]-have["actual"]
        denom=have["actual"].sum()
        rows.append({"candidate":candidate,"year":year,"states":len(have),"prediction_states":len(part),
                     "coverage":len(have)/len(part),"actual_acres":denom,"predicted_acres":have["predicted"].sum(),
                     "state_wape_pct":100*errors.abs().sum()/denom,"us_signed_error_pct":100*errors.sum()/denom,
                     "us_abs_error_pct":100*abs(errors.sum())/denom,
                     "persistence_fallback_states":int(part["fallback_baseline"].sum())})
    return pd.DataFrame(rows)


def summaries(by_year: pd.DataFrame) -> pd.DataFrame:
    parts=[]
    for label, first, last in [("development",2012,2020),("reserve",2021,2024),("all_replay",2012,2024)]:
        subset=by_year[by_year["year"].between(first,last)]
        for candidate, part in subset.groupby("candidate"):
            base=subset[subset["candidate"]=="same_as_last_year"].set_index("year")["state_wape_pct"]
            differences=base-part.set_index("year")["state_wape_pct"]
            parts.append({"period":label,"candidate":candidate,"years":len(part),
                          "mean_state_wape_pct":part["state_wape_pct"].mean(),
                          "mean_us_abs_error_pct":part["us_abs_error_pct"].mean(),
                          "mean_us_signed_error_pct":part["us_signed_error_pct"].mean(),
                          "minimum_state_coverage":part["coverage"].min(),
                          "state_wape_improvement_points":differences.mean(),
                          "paired_year_improvement_se":differences.std(ddof=1)/np.sqrt(len(differences)),
                          "state_target_met_every_year":bool((part["state_wape_pct"]<=2).all()),
                          "us_target_met_every_year":bool((part["us_abs_error_pct"]<=2).all())})
    return pd.DataFrame(parts)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force",action="store_true")
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    signature={"source_sha256":digest(SOURCE),"code_sha256":digest(Path(__file__)),
               "incumbent_metrics_sha256":digest(SOURCE.parent/"metrics.json"),
               "incumbent_backtest_sha256":digest(SOURCE.parent/"backtest_by_year.csv"),
               "versions":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,
                           "scipy":scipy.__version__,"sklearn":sklearn.__version__,"xgboost":xgboost.__version__}}
    manifest=OUT/"run.json"
    if manifest.exists() and not args.force:
        previous=json.loads(manifest.read_text())
        if previous.get("signature")==signature and all((OUT/name).exists() for name in ["predictions.csv","by_year.csv","summary.csv","fit_audit.csv","incumbent_comparison.csv"]):
            print("Unchanged input/code/environment; cached outputs in",OUT)
            print(pd.read_csv(OUT/"summary.csv").to_string(index=False))
            return
    raw=pd.read_csv(SOURCE)
    # Drop future years before feature engineering, preventing accidental access even in diagnostics.
    raw=raw[raw["year"]<=2024].copy()
    table=features(raw)
    predictions,audit=evaluate(table)
    by_year=metrics(predictions)
    summary=summaries(by_year)
    development=summary[summary["period"]=="development"].sort_values("mean_state_wape_pct",kind="stable")
    winner=str(development.iloc[0]["candidate"])
    incumbent_name=json.loads((SOURCE.parent/"metrics.json").read_text())["silage_choice"]
    incumbent=pd.read_csv(SOURCE.parent/"backtest_by_year.csv")
    incumbent=incumbent[(incumbent["target"]=="silage") & (incumbent["candidate"]==incumbent_name)
                        & incumbent["year"].isin(YEARS)].set_index("year")["state_error_pct"]
    comparisons=[]
    for name, part in by_year.groupby("candidate"):
        paired=incumbent-part.set_index("year")["state_wape_pct"]
        se=paired.std(ddof=1)/np.sqrt(paired.notna().sum())
        comparisons.append({"candidate":name,"incumbent":incumbent_name,"years":int(paired.notna().sum()),
                            "incumbent_mean_state_wape_pct":incumbent.mean(),
                            "gain_state_wape_points":paired.mean(),"paired_year_gain_se":se,
                            "passes_existing_two_se_rule":bool(paired.mean()>2*se)})
    signature_note={"signature":signature,"slate":SLATE,"development_winner":winner,
                    "development_years":[2012,2020],"reserve_years":[2021,2024],"caveats":CAVEATS,
                    "metric_definition":"State WAPE = 100 * sum_state(abs(predicted-actual)) / sum_state(actual); US error uses signed sum before taking absolute value."}
    for name,frame in [("predictions",predictions),("by_year",by_year),("summary",summary),("fit_audit",audit),
                       ("incumbent_comparison",pd.DataFrame(comparisons))]:
        frame.to_csv(OUT/(name+".csv"),index=False,float_format="%.8f")
    manifest.write_text(json.dumps(signature_note,indent=2)+"\n")
    print(summary.to_string(index=False))
    print("Development-only winner:",winner)


if __name__=="__main__":
    main()
