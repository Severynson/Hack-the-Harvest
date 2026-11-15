#!/usr/bin/env python3
"""Trained gradient-boosted models for the two numbers: corn acres for silage and for grain, by state and US.

    python3 test_models/danielModel/train_gbt.py                 backtest, trained models, 2026 forecast
    python3 test_models/danielModel/train_gbt.py --score-2025    held-out 2025 comparison for these models (written once)
    python3 test_models/danielModel/train_gbt.py --earliness     the saved models replayed as of 15 Aug, Sep, Oct and Nov

Needs numpy and scikit-learn, and out/panel_nov.csv from build_panel.py. Same rules as model.py: every test
year (2012 to 2024) is predicted by a model trained on earlier years only, and 2025 is never used to fit or choose.

Silage    Boosted trees on the change against last year, from every public change and level in the panel
          (NASS's in-season acres and yield, drought, crop and pasture condition, weather, hay, milk, herd).
Grain     Two trained models:
          "correction"   starts from NASS's latest harvested-for-grain forecast and learns its miss;
          "independent"  never sees NASS's grain forecast: planted acres times last year's grain share,
                         corrected by trees on the season's stress. This is the number that is ours alone.

Tree settings were fixed before scoring (SETTINGS); the monotone versions force each input to act in the
direction written down in model.EXPECTED_SIGN.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model as base  # noqa: E402  (the panel, features, baselines and scoring are shared)

OUT = HERE / "out"
SETTINGS = {
    "small": dict(max_depth=2, max_iter=150, learning_rate=0.05, min_samples_leaf=15, l2_regularization=1.0),
    "medium": dict(max_depth=3, max_iter=300, learning_rate=0.03, min_samples_leaf=15, l2_regularization=1.0),
}
LEVELS = ["drought", "poor", "pasture", "share_last", "cows_per_acre"]     # where the state stands this year
SILAGE_FEATURES = list(base.EXPECTED_SIGN) + LEVELS
GRAIN_STRESS = ["d_planted", "yield_shock", "d_drought", "d_poor", "late_plant", "d_mature", "d_rain", "d_gdd",
                "early_freeze", "drought", "poor", "share_last"]
GRAIN_FEATURES = {"correction": ["is_nass", "d_notgrain", "not_grain"] + GRAIN_STRESS, "independent": GRAIN_STRESS}
GRAIN_SIGN = {"yield_shock": +1, "d_drought": -1, "d_poor": -1, "drought": -1, "poor": -1, "early_freeze": -1}


# --- rows ---------------------------------------------------------------------------

def levels(panel, s, t) -> dict:
    g = lambda name, year=t: base.get(panel, s, year, name)  # noqa: E731
    scaled = lambda v: None if v is None else v / 100  # noqa: E731
    planted_last = g("planted", t - 1)
    return {
        "drought": scaled(g("drought_d2")), "poor": scaled(g("cond_poor")), "pasture": scaled(g("pasture_poor")),
        "share_last": g("silage", t - 1) / planted_last if g("silage", t - 1) and planted_last else None,
        "cows_per_acre": g("milk_cows") / planted_last if g("milk_cows") and planted_last else None,
        "not_grain": 1 - g("grain_asof") / g("planted_asof") if g("grain_asof") and g("planted_asof") else None,
    }


def silage_rows(panel, years, need_truth=True) -> list[dict]:
    return [{**r, **levels(panel, r["state"], r["year"])} for r in base.rows_for(panel, years, need_truth)]


def grain_rows(panel, years, kind: str, need_truth=True) -> list[dict]:
    """One row per state-year with a starting value for grain acres ("last") and the truth ("actual")."""
    out = []
    for (s, t), cell in sorted(panel.items()):
        if t not in years or (need_truth and not cell.get("grain")):
            continue
        planted, last, planted_last = cell.get("planted_asof"), base.get(panel, s, t - 1, "grain"), base.get(panel, s, t - 1, "planted")
        share = planted * last / planted_last if planted and last and planted_last else None
        start, how = (share, "share") if kind == "independent" else base.grain_base(panel, s, t)
        if not start:
            continue
        out.append({"state": s, "year": t, "last": start, "actual": cell.get("grain"), "weight": last or start,
                    "is_nass": float(how == "nass"), **base.features(panel, s, t), **levels(panel, s, t)})
    return out


def matrix(rows: list[dict], names: list[str]) -> np.ndarray:
    return np.array([[np.nan if r.get(n) is None else r[n] for n in names] for r in rows], dtype=float)


# --- training -------------------------------------------------------------------------

def train(rows: list[dict], names: list[str], setting: str, signs: dict | None) -> dict:
    """Fit the trees. An input with no value in any training row (NASS's grain forecast before 2012) is left out."""
    names = [n for n in names if any(r.get(n) is not None for r in rows)]
    monotone = [signs.get(n, 0) for n in names] if signs else None
    trees = HistGradientBoostingRegressor(random_state=0, early_stopping=False, monotonic_cst=monotone, **SETTINGS[setting])
    weight = np.array([r.get("weight", r["last"]) for r in rows])
    y = np.clip([math.log(r["actual"] / r["last"]) for r in rows], -base.MAX_LOG_CHANGE, base.MAX_LOG_CHANGE)
    return {"trees": trees.fit(matrix(rows, names), y, sample_weight=weight / weight.mean()), "features": names}


def predict(fitted: dict, rows: list[dict]) -> dict:
    change = np.clip(fitted["trees"].predict(matrix(rows, fitted["features"])), -base.MAX_LOG_CHANGE, base.MAX_LOG_CHANGE)
    return {r["state"]: r["last"] * math.exp(c) for r, c in zip(rows, change)}


CANDIDATES = {     # name -> (target, rows builder, feature names, tree setting, sign constraints)
    "silage_gbt_small": ("silage", silage_rows, SILAGE_FEATURES, "small", None),
    "silage_gbt_small_monotone": ("silage", silage_rows, SILAGE_FEATURES, "small", base.EXPECTED_SIGN),
    "silage_gbt_medium": ("silage", silage_rows, SILAGE_FEATURES, "medium", None),
    "silage_gbt_medium_monotone": ("silage", silage_rows, SILAGE_FEATURES, "medium", base.EXPECTED_SIGN),
    "grain_gbt_correction": ("grain", lambda p, y, need_truth=True: grain_rows(p, y, "correction", need_truth), GRAIN_FEATURES["correction"], "small", GRAIN_SIGN),
    "grain_gbt_independent": ("grain", lambda p, y, need_truth=True: grain_rows(p, y, "independent", need_truth), GRAIN_FEATURES["independent"], "small", GRAIN_SIGN),
    "grain_gbt_independent_medium": ("grain", lambda p, y, need_truth=True: grain_rows(p, y, "independent", need_truth), GRAIN_FEATURES["independent"], "medium", GRAIN_SIGN),
}


def forecast(panel, name: str, year: int):
    """Train on every year before ``year`` and predict it. Returns (model, {state: acres})."""
    _, build, names, setting, signs = CANDIDATES[name]
    fitted = train(build(panel, range(2000, year)), names, setting, signs)
    return fitted, predict(fitted, build(panel, [year], need_truth=False))


def blend(a: dict, b: dict) -> dict:
    return {s: math.sqrt(a[s] * b[s]) for s in a.keys() & b.keys()}


CHOSEN = {"silage": "silage_gbt_small_monotone", "grain_correction": "grain_gbt_correction", "grain_independent": "grain_gbt_independent"}


def earliness() -> None:
    """The saved models and NASS's own grain forecast, backtested with what was public on each date."""
    years = range(base.FIRST_TEST, base.LAST_TEST + 1)
    with (OUT / "gbt_earliness.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["asof", "candidate", "years", "state_error_pct", "us_abs_error_pct", "us_bias_pct"])
        for asof in ("aug", "sep", "oct", "nov"):
            panel = base.load_panel(asof)
            tables = {name: {t: base.score(forecast(panel, name, t)[1], panel, t, label.split("_")[0]) for t in years} for label, name in CHOSEN.items()}
            tables["nass_latest (grain)"] = {t: base.score(base.grain_predict(panel, t, range(2000, t), corrected=False), panel, t, "grain") for t in years}
            for name, table in tables.items():
                m = base.summarise(table)
                writer.writerow([asof, name, m["years"], round(m["state_error"], 2), round(m["us_abs_error"], 2), round(m["us_bias"], 2)])
                print(f"  {asof}  {name:28s} state error {m['state_error']:5.2f}%   |US error| {m['us_abs_error']:5.2f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--score-2025", action="store_true")
    parser.add_argument("--earliness", action="store_true")
    args = parser.parse_args()
    if args.earliness:
        return earliness()
    panel = base.load_panel("nov")
    years = range(base.FIRST_TEST, base.LAST_TEST + 1)
    reference = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    ref_silage, ref_grain, ref_preds = base.backtest(panel, years)
    current = {"silage": reference["silage_base"], "grain": reference["grain_choice"]}

    scores = {name: {} for name in CANDIDATES}
    scores["silage_blend_ridge_gbt"] = {}
    for t in years:
        made = {}
        for name, (target, *_rest) in CANDIDATES.items():
            _, made[name] = forecast(panel, name, t)
            scores[name][t] = base.score(made[name], panel, t, target)
        mixed = blend(ref_preds[current["silage"]][t], made["silage_gbt_small_monotone"])
        scores["silage_blend_ridge_gbt"][t] = base.score(mixed, panel, t, "silage")

    tables = {"silage": {"same_as_last_year": ref_silage["same_as_last_year"], current["silage"]: ref_silage[current["silage"]]},
              "grain": {current["grain"]: ref_grain[current["grain"]]}}
    for name, table in scores.items():
        tables[name.split("_")[0]][name] = table
    log, best = [], dict(current)
    for target, table in tables.items():
        for name, by_year in table.items():
            summary = base.summarise(by_year)
            won, gain, se = (False, 0.0, 0.0) if name in (current[target], "same_as_last_year") else base.beats(by_year, table[current[target]])
            log.append({"target": target, "candidate": name, **{k: round(v, 3) for k, v in summary.items()},
                        "gain_vs_current": round(gain, 3), "two_se": round(2 * se, 3),
                        "decision": "current" if name == current[target] else "baseline" if name == "same_as_last_year" else "better" if won else "not better"})
            if won and gain > 0:
                best[target] = name
    with (OUT / "gbt_results.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(log[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(log)
    with (OUT / "gbt_backtest_by_year.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate", "year", "states", "state_error_pct", "us_error_pct"])
        for name, table in scores.items():
            for year, s in table.items():
                writer.writerow([name, year, s["states"], round(s["state_error"], 2), round(s["us_error"], 2)])
    for row in log:
        print(f"  {row['target']:6s} {row['candidate']:30s} state error {row['state_error']:6.2f}%   |US error| {row['us_abs_error']:5.2f}%   US bias {row['us_bias']:+5.2f}%   {row['decision']}")

    chosen = CHOSEN

    if args.score_2025:
        target_file = OUT / "score_2025_gbt.json"
        if target_file.exists():
            raise SystemExit(f"{target_file.name} already exists: the 2025 comparison is run once")
        result = {}
        for label, name in chosen.items():
            _, pred = forecast(panel, name, base.SCORE_YEAR)
            result[label] = {"candidate": name, **base.score(pred, panel, base.SCORE_YEAR, label.split("_")[0])}
        target_file.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print("2025 held-out score:", json.dumps(result))
        return

    # Train on every year with truth, save the models, and forecast 2026.
    fitted, preds = {}, {}
    for label, name in chosen.items():
        fitted[label], preds[label] = forecast(panel, name, base.FORECAST_YEAR)
        (OUT / f"{name}.pkl").write_bytes(pickle.dumps(fitted[label]))
    # 80% ranges from each model's own misses in the backtest, as in model.py.
    bands = {label: base.interval_table(panel, lambda t, n=name: forecast(panel, n, t)[1], label.split("_")[0], years)
             for label, name in chosen.items()}
    with (OUT / "forecast_2026_gbt.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["state", *[f"{k}_{part}" for k in chosen for part in ("acres", "lo80", "hi80")]])
        for s in sorted(set().union(*[set(p) for p in preds.values()])):
            cells = []
            for k in chosen:
                value = preds[k].get(s)
                cells += [round(value), *map(round, base.band(bands[k], value))] if value else ["", "", ""]
            writer.writerow([s, *cells])
        totals = []
        for k in chosen:
            total = sum(preds[k].values())
            totals += [round(total), round(total * math.exp(bands[k]["us"][0])), round(total * math.exp(bands[k]["us"][1]))]
        writer.writerow(["US (sum of states)", *totals])
    with (OUT / "gbt_importance.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "feature", "importance"])
        for label, name in chosen.items():
            build, names = CANDIDATES[name][1], fitted[label]["features"]
            rows = build(panel, range(2000, base.FORECAST_YEAR))
            y = np.clip([math.log(r["actual"] / r["last"]) for r in rows], -base.MAX_LOG_CHANGE, base.MAX_LOG_CHANGE)
            imp = permutation_importance(fitted[label]["trees"], matrix(rows, names), y, n_repeats=10, random_state=0)
            for n, v in sorted(zip(names, imp.importances_mean), key=lambda kv: -kv[1]):
                writer.writerow([name, n, round(float(v), 4)])
    (OUT / "gbt_metrics.json").write_text(json.dumps({"test_years": [base.FIRST_TEST, base.LAST_TEST], "saved_models": chosen,
        "beats_current": {k: v for k, v in best.items() if v != current[k]}, "rows": log}, indent=1) + "\n", encoding="utf-8")
    print("2026 forecast (US): " + ", ".join(f"{k} {sum(v.values()) / 1e6:.3f}M" for k, v in preds.items()))


if __name__ == "__main__":
    main()
