#!/usr/bin/env python3
"""Rudimentary state corn acreage model on the organizers' Quick Stats file (acres).

Truth is NASS's final state number (reference period YEAR). Everything a model
sees was published by mid-November of the same year:
  planted_asof   latest planted-acres estimate (Oct, Sep, Aug, June, else March)
  grain_asof     latest harvested-for-grain forecast (Nov, Oct, Sep, Aug, else June)
  *_last         last year's final planted, grain and silage acres

Silage candidates: same as last year; last year's share of planted; last year's share of the
not-for-grain acres (planted minus grain); a pooled regression on those two changes.
Grain candidates: same as last year; NASS's own latest forecast; that forecast plus a pooled revision term.

Scored with an expanding window: each year is predicted from earlier years only. Only years
whose previous year is in the file count; 2017 and 2022 are county-only there, so 2018 and 2023 drop out.

With --split half the models learn from the first half of those years and are tested on the second half.

Usage: python3 -I state_acres.py [--split half] [path/to/corn_grain_silage_acres.csv]
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE.parents[1] / "jupyter" / "workspace" / "02_QuickStats" / "corn_grain_silage_acres_2012_2025.csv"
SERIES = {"CORN - ACRES PLANTED": "planted", "CORN, GRAIN - ACRES HARVESTED": "grain", "CORN, SILAGE - ACRES HARVESTED": "silage"}
# Reference periods published by mid-November, latest first.
ASOF = {
    "planted": ["OCT FORECAST", "OCT ACREAGE", "SEP FORECAST", "AUG FORECAST", "AUG ACREAGE", "JUN ACREAGE", "MAR ACREAGE"],
    "grain": ["NOV FORECAST", "OCT FORECAST", "SEP FORECAST", "AUG FORECAST", "JUN ACREAGE"],
}
NEEDS = {"silage": ["silage_last", "planted_last", "planted_asof"], "grain": ["grain_last", "grain_asof", "grain_jun"]}
MIN_TRAIN_YEARS = 2


def load(path):
    """One row per state-year that has a previous year: finals, as-of numbers and last year's finals."""
    cells = defaultdict(dict)  # (state, year) -> {(series, reference period): acres}
    with open(path) as f:
        for r in csv.DictReader(f):
            series = SERIES.get(r["short_description"])
            value = r["value"].replace(",", "").strip()  # suppressed cells such as (D) are skipped
            if series and r["aggregation_level"] == "STATE" and r["source"] == "SURVEY" and r["domain"] == "TOTAL" and value.isdigit():
                cells[(r["state_name"], int(r["year"]))][(series, r["reference_period"].replace("YEAR - ", ""))] = float(value)
    table = {}
    for key, c in cells.items():
        row = {s: c.get((s, "YEAR")) for s in SERIES.values()}
        for s, periods in ASOF.items():
            row[f"{s}_asof"] = next((c[(s, p)] for p in periods if (s, p) in c), None)
        row["grain_jun"] = c.get(("grain", "JUN ACREAGE"))
        table[key] = row
    rows = []
    for (state, year), now in sorted(table.items()):
        last = table.get((state, year - 1))
        if last:
            rows.append({"state": state, "year": year, **now, **{f"{s}_last": last[s] for s in SERIES.values()}})
    return rows


def ols(x, y, w):
    """Weighted least-squares coefficients for y ~ x, by Gauss-Jordan on the normal equations."""
    k = len(x[0])
    a = [[sum(wi * r[i] * r[j] for r, wi in zip(x, w)) for j in range(k)] + [sum(wi * r[i] * t for r, t, wi in zip(x, y, w))] for i in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(a[r][i]))
        a[i], a[p] = a[p], a[i]
        for r in range(k):
            if r != i:
                f = a[r][i] / a[i][i]
                a[r] = [v - f * z for v, z in zip(a[r], a[i])]
    return [a[i][k] / a[i][i] for i in range(k)]


def dot(beta, features):
    return sum(b * v for b, v in zip(beta, features))


def not_for_grain(planted, grain):
    return planted - grain if planted and grain and planted > grain else None


# --- models: (training rows, row to predict) -> acres ------------------------

def silage_persistence(train, r):
    return r["silage_last"]


def silage_planted_share(train, r):
    return r["silage_last"] * r["planted_asof"] / r["planted_last"]


def silage_residual_share(train, r):
    now, last = not_for_grain(r["planted_asof"], r["grain_asof"]), not_for_grain(r["planted_last"], r["grain_last"])
    return r["silage_last"] * now / last if now and last else silage_planted_share(train, r)


def silage_features(r):
    now, last = not_for_grain(r["planted_asof"], r["grain_asof"]), not_for_grain(r["planted_last"], r["grain_last"])
    shift = now / r["planted_asof"] - last / r["planted_last"] if now and last else 0.0
    return [1.0, math.log(r["planted_asof"] / r["planted_last"]), shift]


def silage_regression(train, r):
    beta = ols([silage_features(t) for t in train], [math.log(t["silage"] / t["silage_last"]) for t in train], [t["silage_last"] for t in train])
    return r["silage_last"] * math.exp(dot(beta, silage_features(r)))


def grain_persistence(train, r):
    return r["grain_last"]


def grain_nass_latest(train, r):
    return r["grain_asof"]


def grain_features(r):
    return [1.0, math.log(r["grain_asof"] / r["grain_jun"])]


def grain_regression(train, r):
    beta = ols([grain_features(t) for t in train], [math.log(t["grain"] / t["grain_asof"]) for t in train], [t["grain_asof"] for t in train])
    return r["grain_asof"] * math.exp(dot(beta, grain_features(r)))


MODELS = {
    "silage": {"persistence": silage_persistence, "planted_share": silage_planted_share, "residual_share": silage_residual_share, "regression": silage_regression},
    "grain": {"persistence": grain_persistence, "nass_latest": grain_nass_latest, "regression": grain_regression},
}


def backtest(rows, target, split):
    """{model: {year: {n_states, wape_pct, us_error_pct}}} plus the rows that were usable."""
    usable = [r for r in rows if all(r[k] for k in NEEDS[target])]
    scored = [r for r in usable if r[target]]
    years = sorted({r["year"] for r in scored})
    first_test = years[len(years) // 2] if split == "half" else years[MIN_TRAIN_YEARS]
    results = {}
    for name, model in MODELS[target].items():
        results[name] = {}
        for year in (y for y in years if y >= first_test):
            # half: learn from the first half of the years only; expanding: from every earlier year
            train = [r for r in scored if r["year"] < (first_test if split == "half" else year)]
            test = [r for r in scored if r["year"] == year]
            pred, truth = [model(train, r) for r in test], [r[target] for r in test]
            results[name][year] = {
                "n_states": len(test),
                "wape_pct": round(100 * sum(abs(p - t) for p, t in zip(pred, truth)) / sum(truth), 2),
                "us_error_pct": round(100 * (sum(pred) - sum(truth)) / sum(truth), 2),
            }
    return results, usable, scored


def summary(per_year):
    n = len(per_year)
    return {
        "years": n,
        "mean_state_wape_pct": round(sum(v["wape_pct"] for v in per_year.values()) / n, 2),
        "mean_abs_us_error_pct": round(sum(abs(v["us_error_pct"]) for v in per_year.values()) / n, 2),
        "mean_us_error_pct": round(sum(v["us_error_pct"] for v in per_year.values()) / n, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", nargs="?", default=DEFAULT_CSV)
    parser.add_argument("--split", choices=["expanding", "half"], default="expanding", help="half: train on the first half of the years, test on the second half")
    args = parser.parse_args()

    rows = load(args.csv)
    out = {"split": args.split}
    for target in MODELS:
        results, usable, scored = backtest(rows, target, args.split)
        summaries = {name: summary(per_year) for name, per_year in results.items()}
        best = min(summaries, key=lambda name: summaries[name]["mean_state_wape_pct"])
        out[target] = {"selected": best, "summary": summaries, "by_year": results}
        train_years = sorted({r["year"] for r in scored} - set(results[best]))
        print(f"{target} ({args.split}): earlier years {train_years}, scored years {sorted(results[best])}, states per year {sorted({v['n_states'] for v in results[best].values()})}")
        for name, s in summaries.items():
            print(f"  {name:15s} state WAPE {s['mean_state_wape_pct']:5.2f}%   |US error| {s['mean_abs_us_error_pct']:5.2f}%   US bias {s['mean_us_error_pct']:+5.2f}%{'   <- lowest WAPE' if name == best else ''}")

        # Forecast any year that has as-of numbers but no final yet (none until the file is re-downloaded past 2025).
        pending = [r for r in usable if not r[target]]
        if pending:
            year = max(r["year"] for r in pending)
            out[target]["forecast"] = {"year": year, "model": best, "acres": {r["state"]: round(MODELS[target][best](scored, r)) for r in pending if r["year"] == year}}
            print(f"  forecast {year}: {len(out[target]['forecast']['acres'])} states, US {sum(out[target]['forecast']['acres'].values()):,.0f} acres")
        else:
            print("  no forecast: the file has no year with as-of numbers and no final")

    (HERE / "out").mkdir(exist_ok=True)
    name = "state_metrics_half.json" if args.split == "half" else "state_metrics.json"
    (HERE / "out" / name).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
