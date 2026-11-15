"""Fixed national-silage acreage slate; earlier-year fits, temporal development/validation.

Run ``.venv/bin/python test_models/accuracy/national.py`` from the repository root.
The 2025 and later outcomes are excluded before any feature computation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "model" / "out" / "panel_nov.csv"
OUT = HERE / "national"
MIN_TRAIN, FIRST_TEST, LAST_TEST, LAST_DEVELOPMENT = 8, 2012, 2024, 2020
MAX_LOG_CHANGE = 0.5
RIDGE = 1.0
BASE_FEATURES = ["reversion", "d_planted", "yield_shock", "d_cows"]
WEATHER_FEATURES = [*BASE_FEATURES, "d_drought", "d_poor", "d_rain", "early_freeze"]
SIGNS = {"reversion": -1, "d_planted": 1, "yield_shock": -1, "d_cows": 1,
         "d_drought": 1, "d_poor": 1, "d_rain": -1, "early_freeze": 1, "d_non_grain": 1}
CANDIDATES = ["persistence", "mean3", "dairy_divided_by_yield", "dairy_half_yield",
              "non_grain_other3", "non_grain_other5", "ridge_base", "ridge_weather",
              "ridge_non_grain", "signed_weather", "ensemble_base_weather", "ensemble_physical"]


def positive_log_ratio(top: float, bottom: float) -> float:
    return float(np.log(top / bottom)) if np.isfinite(top) and np.isfinite(bottom) and top > 0 and bottom > 0 else np.nan


def national_rows(panel: pd.DataFrame) -> pd.DataFrame:
    """Current inputs use their public-as-of columns; all outcome-derived inputs are lagged."""
    years = {int(y): part.set_index("state") for y, part in panel.groupby("year")}
    states = sorted(years[min(years)].index)
    if len(states) != 48:
        raise ValueError("national experiment requires the full 48-state silage scope")
    for year, part in years.items():
        if sorted(part.index) != states or part["silage"].isna().any():
            raise ValueError(f"missing state silage truth in {year}; refusing to change scope")

    rows = []
    for year in sorted(years):
        if any(y not in years for y in range(year - 4, year)):
            continue
        current, prior = years[year], years[year - 1]
        last = float(prior["silage"].sum())
        weights = prior["silage"] / last
        row = {"year": year, "states": 48, "actual": float(current["silage"].sum()), "last": last}
        row["target"] = positive_log_ratio(row["actual"], last)
        prior3 = float(np.mean([years[y]["silage"].sum() for y in range(year - 3, year)]))
        earlier3 = float(np.mean([years[y]["silage"].sum() for y in range(year - 4, year - 1)]))
        row["mean3"] = prior3
        row["reversion"] = positive_log_ratio(last, earlier3)
        row["d_planted"] = positive_log_ratio(current["planted_asof"].sum(min_count=48),
                                               prior["planted"].sum(min_count=48))
        row["d_cows"] = positive_log_ratio(current["milk_cows"].sum(min_count=48),
                                            prior["milk_cows"].sum(min_count=48))
        previous_yield = pd.concat([years[y]["yield"] for y in range(year - 3, year)], axis=1).mean(axis=1)
        state_yield_shock = np.log(current["yield_asof"] / previous_yield).replace([np.inf, -np.inf], np.nan)
        state_features = {
            "yield_shock": state_yield_shock,
            "d_drought": (current["drought_d2"] - prior["drought_d2"]) / 100,
            "d_poor": (current["cond_poor"] - prior["cond_poor"]) / 100,
            "d_rain": np.log(current["rain"] / prior["rain"]).replace([np.inf, -np.inf], np.nan),
            "early_freeze": current["early_freeze"],
        }
        for name, values in state_features.items():
            ok = values.notna()
            coverage = float(weights[ok].sum())
            row[f"{name}_coverage"] = coverage
            row[name] = float((values[ok] * weights[ok]).sum() / coverage) if coverage > 0 else np.nan
        row["dairy_divided_by_yield"] = last * np.exp(np.clip(row["d_cows"] - row["yield_shock"],
                                                             -MAX_LOG_CHANGE, MAX_LOG_CHANGE))
        row["dairy_half_yield"] = last * np.exp(np.clip(row["d_cows"] - 0.5 * row["yield_shock"],
                                                       -MAX_LOG_CHANGE, MAX_LOG_CHANGE))

        # Residual estimates operate on the 41 published grain states, then carry
        # the other states' silage acres forward. Missing grain never means zero.
        grain_states = prior.index[prior["grain"].notna() & prior["planted"].gt(0)]
        planted_now = current.loc[grain_states, "planted_asof"]
        grain_now = current.loc[grain_states, "grain_asof"]
        fallback = planted_now * prior.loc[grain_states, "grain"] / prior.loc[grain_states, "planted"]
        grain_prediction = grain_now.fillna(fallback)
        if planted_now.isna().any() or grain_prediction.isna().any():
            raise ValueError(f"cannot construct full-scope residual predictor for {year}")
        row["residual_grain_states"] = len(grain_states)
        row["residual_observed_grain_states"] = int(grain_now.notna().sum())
        row["residual_grain_forecast_silage_coverage"] = float(weights.reindex(grain_states)[grain_now.notna()].sum())
        residual = float((planted_now - grain_prediction).sum())
        last_residual = float((prior.loc[grain_states, "planted"] - prior.loc[grain_states, "grain"]).sum())
        row["d_non_grain"] = positive_log_ratio(residual, last_residual)
        other_states_last = last - float(prior.loc[grain_states, "silage"].sum())
        for n in [3, 5]:
            earlier = [years[y].reindex(grain_states) for y in range(year - n, year) if y in years]
            fractions = [(p["planted"] - p["grain"] - p["silage"]).sum(min_count=len(grain_states)) /
                         p["planted"].sum(min_count=len(grain_states)) for p in earlier]
            fractions = [f for f in fractions if np.isfinite(f)]
            expected_other = float(np.mean(fractions)) * float(planted_now.sum()) if fractions else np.nan
            prediction = residual - expected_other + other_states_last
            row[f"non_grain_other{n}"] = (max(prediction, 0.0) if np.isfinite(prediction) else np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def regression(train: pd.DataFrame, score: pd.Series, names: list[str], signed: bool = False) -> tuple[float, dict]:
    """Standardization and missing-value imputation use fitting years only; no drift term."""
    x = train[names].to_numpy(float)
    centre = np.array([np.nanmean(x[:, j]) if np.isfinite(x[:, j]).any() else 0 for j in range(x.shape[1])])
    scale = np.array([np.nanstd(x[:, j]) if np.isfinite(x[:, j]).any() else 1 for j in range(x.shape[1])])
    scale[scale < 1e-12] = 1
    z = np.where(np.isfinite(x), (x - centre) / scale, 0)
    target = train["target"].to_numpy(float)
    augmented = np.vstack([z, np.sqrt(RIDGE * len(train)) * np.eye(len(names))])
    rhs = np.r_[target, np.zeros(len(names))]
    if signed:
        signs = np.array([SIGNS[n] for n in names])
        solution = lsq_linear(augmented * signs, rhs, bounds=(0, np.inf))
        if not solution.success:
            raise RuntimeError("sign-constrained solve failed")
        beta = solution.x * signs
    else:
        beta = np.linalg.lstsq(augmented, rhs, rcond=None)[0]
    raw = score[names].to_numpy(float)
    value = float(np.where(np.isfinite(raw), (raw - centre) / scale, 0) @ beta)
    result = float(score["last"] * np.exp(np.clip(value, -MAX_LOG_CHANGE, MAX_LOG_CHANGE)))
    return result, dict(zip(names, beta.tolist(), strict=True))


def metrics(rows: pd.DataFrame) -> dict:
    error = rows["abs_error_pct"]
    return {"years": len(rows), "mean_abs_error_pct": float(error.mean()),
            "max_abs_error_pct": float(error.max()), "years_at_or_below_2pct": int(error.le(2).sum()),
            "mean_signed_error_pct": float(rows["signed_error_pct"].mean())}


def run(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    # Explicit filter also protects callers passing the full panel into this function.
    panel = panel[panel["year"] <= LAST_TEST].copy()
    national = national_rows(panel)
    predictions, coefficients = [], []
    for _, row in national[national["year"].between(FIRST_TEST, LAST_TEST)].iterrows():
        year = int(row["year"])
        train = national[national["year"] < year]
        if len(train) < MIN_TRAIN:
            raise ValueError(f"only {len(train)} earlier fit years for {year}")
        values = {"persistence": float(row["last"]), "mean3": float(row["mean3"]),
                  **{name: float(row[name]) for name in CANDIDATES[2:6]}}
        for name, names, signed in [("ridge_base", BASE_FEATURES, False),
                                     ("ridge_weather", WEATHER_FEATURES, False),
                                     ("ridge_non_grain", [*BASE_FEATURES, "d_non_grain"], False),
                                     ("signed_weather", WEATHER_FEATURES, True)]:
            values[name], weights = regression(train, row, names, signed)
            coefficients.extend({"year": year, "candidate": name, "feature": f, "coefficient_std": b}
                                for f, b in weights.items())
        values["ensemble_base_weather"] = (values["ridge_base"] + values["ridge_weather"]) / 2
        values["ensemble_physical"] = (values["persistence"] + values["dairy_half_yield"] +
                                        values["non_grain_other3"]) / 3
        for name in CANDIDATES:
            predicted = values[name]
            error = 100 * (predicted / row["actual"] - 1) if np.isfinite(predicted) else np.nan
            predictions.append({"year": year, "candidate": name, "states": 48, "train_years": len(train),
                                "actual": float(row["actual"]), "predicted": predicted,
                                "signed_error_pct": error, "abs_error_pct": abs(error),
                                "partition": "development" if year <= LAST_DEVELOPMENT else "later_validation"})
    predictions = pd.DataFrame(predictions)
    develop = predictions[predictions["partition"] == "development"]
    dev_errors = develop.groupby("candidate")["abs_error_pct"].mean()
    # Candidate order is a fixed simplicity tie-break; later outcomes do not select.
    selected = min(CANDIDATES, key=lambda name: (dev_errors.get(name, np.inf), CANDIDATES.index(name)))
    result = {
        "target": "national silage acreage absolute percentage error <= 2%",
        "states": 48, "candidates": CANDIDATES, "selected_on_2012_2020": selected,
        "selection_rule": "minimum development-year mean absolute US error; fixed slate order breaks ties",
        "minimum_earlier_fit_years": MIN_TRAIN, "maximum_outcome_year_read": LAST_TEST,
        "development_years": [2012, 2020], "later_validation_years": [2021, 2024],
        "results": {partition: {name: metrics(part[part["candidate"] == name]) for name in CANDIDATES}
                    for partition, part in predictions.groupby("partition")},
        "caveats": [
            "All evaluations are retrospective: the team previously inspected outcomes through 2024",
            "The later 2021–2024 partition is excluded from this slate's candidate selection, not globally untouched",
            "No 2025 or later truth is used for fitting, tuning or selection",
            "Historical planted_asof may contain final-vintage stand-ins before 2018; not a fully vintage-correct replay",
            "The current November panel may include later revisions to historical contextual data",
            "Grain yield is a proxy for silage biomass yield; dairy inventory omits beef and feed substitutes",
            "Other/abandoned acres are inferred from prior final planted, grain and silage totals",
            "Pre-2012 grain residual uses last year's grain share of current planted acres; observed grain-asof is absent",
            "Context averages use prior silage-acre weights over available states; feature coverage is exported",
            "Full national outcome scope stays 48 states for every year and candidate",
            "A mean error below 2% would not imply every year or state is within 2%",
        ],
    }
    return predictions, national, pd.DataFrame(coefficients), result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    signature = hashlib.sha256(SOURCE.read_bytes() + Path(__file__).read_bytes()).hexdigest()
    out = OUT / "results.json"
    if out.exists() and not args.force and json.loads(out.read_text()).get("source_sha256") == signature:
        print(f"cached: {out}")
        return
    panel = pd.read_csv(SOURCE)
    predictions, national, coefficients, result = run(panel)
    result["source_sha256"] = signature
    result["source"] = str(SOURCE.relative_to(HERE.parents[1]))
    result["versions"] = {p: version(p) for p in ["numpy", "pandas", "scipy"]}
    OUT.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUT / "predictions.csv", index=False)
    national.to_csv(OUT / "features.csv", index=False)
    coefficients.to_csv(OUT / "weights.csv", index=False)
    clean = json.loads(pd.Series([result]).to_json(orient="values", double_precision=8))[0]
    out.write_text(json.dumps(clean, indent=2, allow_nan=False) + "\n")
    selected = result["selected_on_2012_2020"]
    print(f"selected on 2012–2020: {selected}")
    for phase in ["development", "later_validation"]:
        print(phase)
        for name in CANDIDATES:
            r = result["results"][phase][name]
            print(f"  {name}: mean {r['mean_abs_error_pct']:.3f}%, max {r['max_abs_error_pct']:.3f}%, "
                  f"<=2% {r['years_at_or_below_2pct']}/{r['years']}")


if __name__ == "__main__":
    main()
