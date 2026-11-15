#!/usr/bin/env python3
"""Rudimentary corn grain / silage acreage model, US and states (thousand acres).

Truth is NASS's January number. Everything the model sees was public by
mid-November of the same year:
  jun, nov      NASS June and November forecasts of acres harvested for grain
  silage_lag    last year's silage acres

Candidates, next to the baselines they must beat (NASS's November number, same as last year):
  grain  = nov + c * (nov - jun)                    the revision keeps going
  silage = a + b * silage_lag + d * (jun - nov)     acres cut from grain get chopped
  silage = mean of the last five years

Scored with an expanding window: each year is predicted from earlier years only.
The 2026 forecast uses whichever candidate had the lowest backtest error, baselines included.
States get last year's acres scaled by the US change (no state history in the repo yet).
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIRST_TEST_YEAR = 2010  # nine training years before the first scored year
Z90 = 1.645


def read(name):
    with open(HERE / "data" / name) as f:
        return [{k: (float(v) if v.replace(".", "").isdigit() else v or None) for k, v in r.items()} for r in csv.DictReader(f)]


def ols(x, y):
    """Least-squares coefficients for y ~ x (rows of features), by Gauss-Jordan on the normal equations."""
    k = len(x[0])
    a = [[sum(r[i] * r[j] for r in x) for j in range(k)] + [sum(r[i] * t for r, t in zip(x, y))] for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(a[r][i]))
        a[i], a[p] = a[p], a[i]
        for r in range(k):
            if r != i:
                f = a[r][i] / a[i][i]
                a[r] = [v - f * w for v, w in zip(a[r], a[i])]
    return [a[i][k] / a[i][i] for i in range(k)]


# --- models: (training rows, row to predict) -> thousand acres ---------------

def grain_nass_nov(train, r):
    return r["nov"]


def grain_momentum(train, r):
    (c,) = ols([[t["nov"] - t["jun"]] for t in train], [t["jan_grain"] - t["nov"] for t in train])
    return r["nov"] + c * (r["nov"] - r["jun"])


def silage_persistence(train, r):
    return r["silage_lag"]


def silage_mean5(train, r):
    return sum(t["silage"] for t in train[-5:]) / 5


def silage_switch(train, r):
    a, b, d = ols([[1.0, t["silage_lag"], t["jun"] - t["nov"]] for t in train], [t["silage"] for t in train])
    return a + b * r["silage_lag"] + d * (r["jun"] - r["nov"])


MODELS = {
    "jan_grain": {"nass_nov": grain_nass_nov, "momentum": grain_momentum},
    "silage": {"persistence": silage_persistence, "mean5": silage_mean5, "switch": silage_switch},
}


def score(errors, truths):
    n = len(errors)
    return {
        "n": n,
        "mae": round(sum(abs(e) for e in errors) / n, 1),
        "mape_pct": round(100 * sum(abs(e) / t for e, t in zip(errors, truths)) / n, 2),
        "bias": round(sum(errors) / n, 1),
        "rmse": round((sum(e * e for e in errors) / n) ** 0.5, 1),
    }


def main():
    us = read("us_corn_history.csv")
    for prev, row in zip(us, us[1:]):
        row["silage_lag"] = prev["silage"]
    history = [r for r in us[1:] if r["jan_grain"] is not None]
    target_row = us[-1]  # 2026: forecasts known, truth pending

    metrics, per_year, forecast, best = {}, {}, {}, {}
    for target, models in MODELS.items():
        for name, model in models.items():
            tests = [r for r in history if r["year"] >= FIRST_TEST_YEAR]
            preds = {int(r["year"]): model([t for t in history if t["year"] < r["year"]], r) for r in tests}
            errors = [preds[int(r["year"])] - r[target] for r in tests]
            key = f"{target}.{name}"
            metrics[key] = score(errors, [r[target] for r in tests])
            per_year[key] = {y: round(p) for y, p in preds.items()}
            point = model(history, target_row)
            half = Z90 * metrics[key]["rmse"]
            forecast[key] = {"point": round(point), "lo90": round(point - half), "hi90": round(point + half)}
        best[target] = min((f"{target}.{name}" for name in models), key=lambda k: metrics[k]["mae"])

    # States: last year's acres times the US change. Silage is scored on 2024 and 2025; grain has one year, so no score.
    states = read("state_silage.csv")
    us_silage = {int(r["year"]): r["silage"] for r in history}
    for year in (2024, 2025):
        truth = [s[f"silage_{year}"] for s in states]
        last = [s[f"silage_{year - 1}"] for s in states]
        ratio = per_year[best["silage"]][year] / us_silage[year - 1]
        wape = lambda pred: round(100 * sum(abs(p - t) for p, t in zip(pred, truth)) / sum(truth), 1)
        metrics[f"state_silage_{year}"] = {"n_states": len(states), "wape_persistence_pct": wape(last), "wape_scaled_pct": wape([v * ratio for v in last])}

    us_grain, us_silage_2026 = forecast[best["jan_grain"]]["point"], forecast[best["silage"]]["point"]
    silage_ratio = us_silage_2026 / us_silage[2025]
    grain_ratio = us_grain / history[-1]["jan_grain"]
    rows = [["US", us_grain, us_silage_2026]]
    for s in states:
        grain = round(s["grain_2025"] * grain_ratio) if s["grain_2025"] is not None else ""
        rows.append([s["state"], grain, round(s["silage_2025"] * silage_ratio)])

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"backtest_years": [FIRST_TEST_YEAR, int(history[-1]["year"])], "selected": best, "metrics": metrics, "forecast_2026": forecast, "predictions": per_year}, indent=1))
    with open(out / "forecast_2026.csv", "w", newline="") as f:
        csv.writer(f).writerows([["area", "grain_kacres", "silage_kacres"], *rows])

    print(f"backtest {FIRST_TEST_YEAR}-{int(history[-1]['year'])}, thousand acres")
    for key, m in metrics.items():
        print(f"  {key:22s} {m}")
    print("2026 forecast (point, 90% band from backtest RMSE)")
    for key, f in forecast.items():
        print(f"  {key:22s} {f}{'  <- selected' if key in best.values() else ''}")


if __name__ == "__main__":
    main()
