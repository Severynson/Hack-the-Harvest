#!/usr/bin/env python3
"""Corn acres harvested for silage and for grain, by state and for the US, from what is public in mid-November.

    python3 test_models/danielModel/model.py                  backtest, selection and the 2026 forecast
    python3 test_models/danielModel/model.py --score-2025     held-out comparison with NASS's 2025 acres (written once)
    python3 test_models/danielModel/model.py --earliness      the chosen models scored as of 15 Aug, Sep, Oct and Nov

Needs numpy and out/panel_<asof>.csv from build_panel.py.

Silage. NASS publishes no in-season silage acres, so the number to beat is last year's acres. Each candidate
predicts the change in a state's silage acres against last year (in logs) with one ridge regression pooled over
all states and weighted by silage acres. Features are changes that are public on the forecast date, measured
against their usual value; a missing feature counts as usual. Each feature has a sign written down before
fitting (EXPECTED_SIGN).

Grain. NASS's own latest harvested-for-grain forecast, optionally corrected for its average miss; where NASS
publishes none, planted acres times last year's grain share.

Binary constraint. Every corn field ends as grain or as silage, so the two numbers must add up to the corn
that is harvested. The "reconciled" candidates enforce that: harvested corn is estimated from planted acres,
and the gap is shared between grain and silage in proportion to how uncertain each estimate is.

Honesty rules
- Each test year is predicted by a model fitted on earlier years only (test years FIRST_TEST to 2024).
- 2025 is the organizers' scoring year: it is never used to fit, tune or select. --score-2025 runs once.
- A richer candidate replaces a simpler one only if it wins by more than two standard errors of the
  year-by-year differences. Every candidate tried is logged in out/results.tsv, kept or not.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIRST_TEST, LAST_TEST, SCORE_YEAR, FORECAST_YEAR = 2012, 2024, 2025, 2026   # NASS's grain forecasts are kept from 2012
MAX_LOG_CHANGE = 0.5            # a predicted change beyond about -40% / +65% is cut back
EXPECTED_SIGN = {               # written before fitting: + means "more silage acres than last year"
    "rev": -1, "d_planted": +1, "d_notgrain": +1, "yield_shock": -1, "d_drought": +1, "d_poor": +1,
    "late_plant": +1, "d_mature": -1, "d_rain": -1, "d_gdd": +1, "early_freeze": +1,
    "d_pasture": +1, "d_hay": -1, "d_hayprice": +1, "d_cows": +1, "d_milk": +1,
}
FEATURE_SETS = {                # ordered from simple to rich; selection walks them in this order
    "reversion": ["rev"],
    "nass": ["rev", "d_planted", "d_notgrain", "yield_shock"],
    "stress": ["rev", "d_drought", "d_poor", "d_rain", "late_plant"],
    "forage": ["rev", "d_pasture", "d_hay", "d_hayprice", "d_cows"],
    "nass_stress": ["rev", "d_planted", "yield_shock", "d_drought", "d_poor", "late_plant"],
    "all": list(EXPECTED_SIGN),
}
RIDGE = [1.0, 0.1]              # penalty as a fraction of the number of training rows (features in standard units)
US_SETS = {"us_reversion": ["rev"], "us_drought": ["rev", "d_drought"], "us_condition": ["rev", "d_poor"],
           "us_yield": ["rev", "yield_shock"], "us_stress": ["rev", "d_drought", "d_poor", "late_plant"]}


# --- panel and features ---------------------------------------------------------

def load_panel(asof: str) -> dict:
    panel = {}
    with (OUT / f"panel_{asof}.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            panel[(r["state"], int(r["year"]))] = {k: (float(v) if v != "" else None) for k, v in r.items() if k not in ("state", "year")}
    return panel


def get(panel, state, year, name):
    return panel.get((state, year), {}).get(name)


def mean_of(panel, state, years, name, at_least=1):
    values = [v for y in years if (v := get(panel, state, y, name)) is not None]
    return sum(values) / len(values) if len(values) >= at_least else None


def log_ratio(a, b):
    return math.log(a / b) if a and b and a > 0 and b > 0 else None


def diff(a, b, scale=1.0):
    return (a - b) / scale if a is not None and b is not None else None


def features(panel, s, t) -> dict:
    """Changes public on the forecast date of year t, for state s. None = not available."""
    g = lambda name, year=t: get(panel, s, year, name)  # noqa: E731
    planted_asof, grain_asof = g("planted_asof"), g("grain_asof")
    not_grain = 1 - grain_asof / planted_asof if planted_asof and grain_asof else None
    not_grain_last = 1 - g("grain", t - 1) / g("planted", t - 1) if g("planted", t - 1) and g("grain", t - 1) else None
    usual_planting = mean_of(panel, s, range(t - 3, t), "planted_may20", at_least=2)
    return {
        "rev": log_ratio(g("silage", t - 1), mean_of(panel, s, range(t - 4, t - 1), "silage", at_least=2)),
        "d_planted": log_ratio(planted_asof, g("planted", t - 1)),
        "d_notgrain": diff(not_grain, not_grain_last),
        "yield_shock": log_ratio(g("yield_asof"), mean_of(panel, s, range(t - 3, t), "yield", at_least=2)),
        "d_drought": diff(g("drought_d2"), g("drought_d2", t - 1), 100),
        "d_poor": diff(g("cond_poor"), g("cond_poor", t - 1), 100),
        "late_plant": diff(usual_planting, g("planted_may20"), 100),
        "d_mature": diff(g("mature_sep22"), g("mature_sep22", t - 1), 100),
        "d_rain": log_ratio(g("rain"), g("rain", t - 1)),
        "d_gdd": log_ratio(g("gdd"), g("gdd", t - 1)),
        "early_freeze": g("early_freeze"),
        "d_pasture": diff(g("pasture_poor"), g("pasture_poor", t - 1), 100),
        "d_hay": log_ratio(g("hay_stocks_may"), g("hay_stocks_may", t - 1)),
        "d_hayprice": log_ratio(g("hay_price"), g("hay_price", t - 1)),
        "d_cows": log_ratio(g("milk_cows"), g("milk_cows", t - 1)),
        "d_milk": log_ratio(g("milk_price"), g("milk_price", t - 1)),
    }


def rows_for(panel, years, need_truth=True) -> list[dict]:
    """One row per state-year that has last year's silage (and this year's, when truth is needed)."""
    out = []
    for (s, t), cell in sorted(panel.items()):
        last = get(panel, s, t - 1, "silage")
        if t not in years or not last or (need_truth and not cell.get("silage")):
            continue
        out.append({"state": s, "year": t, "last": last, "actual": cell.get("silage"), **features(panel, s, t)})
    return out


# --- ridge ------------------------------------------------------------------------

def design(rows: list[dict], names: list[str]) -> np.ndarray:
    return np.array([[np.nan if r[n] is None else r[n] for n in names] for r in rows], dtype=float)


def fit_ridge(train: list[dict], names: list[str], penalty: float, target, weight, drift: bool = True):
    """Weighted ridge. Each feature is measured against its usual value in the training years and put in
    standard units; a missing feature counts as usual. ``drift=False`` fixes the constant at zero: in a usual
    year the forecast is last year's acres, and no trend from earlier years is carried forward."""
    x, y = design(train, names), np.array([target(r) for r in train])
    w = np.array([weight(r) for r in train])
    w = w / w.mean()
    seen = ~np.isnan(x)
    wx = np.where(seen, w[:, None], 0.0)
    centre = (wx * np.nan_to_num(x)).sum(0) / np.maximum(wx.sum(0), 1e-12)
    scale = np.sqrt((wx * (np.nan_to_num(x) - centre) ** 2).sum(0) / np.maximum(wx.sum(0), 1e-12))
    scale[scale == 0] = 1.0
    z = np.where(seen, (np.nan_to_num(x) - centre) / scale, 0.0)
    a = np.hstack([np.ones((len(train), 1)) * drift, z])
    ridge = penalty * len(train) * np.eye(a.shape[1])
    ridge[0, 0] = 0.0 if drift else 1.0
    beta = np.linalg.solve(a.T @ (w[:, None] * a) + ridge, a.T @ (w * y))
    return beta, centre, scale


def predict_ridge(model, rows: list[dict], names: list[str]) -> np.ndarray:
    beta, centre, scale = model
    x = design(rows, names)
    z = np.where(np.isnan(x), 0.0, (np.nan_to_num(x) - centre) / scale)
    return np.clip(beta[0] + z @ beta[1:], -MAX_LOG_CHANGE, MAX_LOG_CHANGE)


# --- silage candidates: each returns {state: predicted acres} for one year ------------------

def silage_same(panel, train, test, **_):
    return {r["state"]: r["last"] for r in test}


def silage_mean3(panel, train, test, **_):
    return {r["state"]: mean_of(panel, r["state"], range(r["year"] - 3, r["year"]), "silage") for r in test}


def silage_ridge(panel, train, test, names, penalty, drift=True):
    model = fit_ridge(train, names, penalty, lambda r: math.log(r["actual"] / r["last"]), lambda r: r["last"], drift)
    return {r["state"]: r["last"] * math.exp(c) for r, c in zip(test, predict_ridge(model, test, names))}


def us_rows(rows: list[dict], names: list[str]) -> list[dict]:
    """One row per year: US silage change and the acre-weighted mean of each state feature."""
    out = []
    for year in sorted({r["year"] for r in rows}):
        rs = [r for r in rows if r["year"] == year]
        last = sum(r["last"] for r in rs)
        row = {"year": year, "last": last, "actual": sum(r["actual"] or 0 for r in rs)}
        for n in names:
            have = [r for r in rs if r[n] is not None]
            row[n] = sum(r["last"] * r[n] for r in have) / sum(r["last"] for r in have) if have else None
        out.append(row)
    return out


def silage_topdown(panel, train, test, names, penalty, us_names):
    """State pattern from the state model, level from a model of the US total."""
    states = silage_ridge(panel, train, test, names, penalty)
    us_train, us_test = us_rows(train, us_names), us_rows(test, us_names)
    model = fit_ridge(us_train, us_names, 1.0, lambda r: math.log(r["actual"] / r["last"]), lambda r: 1.0)
    us_total = us_test[0]["last"] * math.exp(predict_ridge(model, us_test, us_names)[0])
    factor = us_total / sum(states.values())
    return {s: v * factor for s, v in states.items()}


# --- grain candidates and the binary reconciliation -------------------------------------

def grain_base(panel, s, t):
    """NASS's latest forecast; else planted acres times last year's grain share; else last year's acres."""
    asof, planted = get(panel, s, t, "grain_asof"), get(panel, s, t, "planted_asof")
    last, planted_last = get(panel, s, t - 1, "grain"), get(panel, s, t - 1, "planted")
    if asof:
        return asof, "nass"
    if planted and last and planted_last:
        return planted * last / planted_last, "share"
    return last, "last"


def nass_bias(panel, years) -> float:
    """Acre-weighted mean of log(final / NASS forecast) over earlier years: NASS's average miss."""
    num = den = 0.0
    for (s, t), cell in panel.items():
        if t in years and cell.get("grain") and cell.get("grain_asof"):
            num += cell["grain"] * math.log(cell["grain"] / cell["grain_asof"])
            den += cell["grain"]
    return num / den if den else 0.0


def grain_predict(panel, t, train_years, corrected: bool) -> dict:
    bias = nass_bias(panel, train_years) if corrected else 0.0
    out = {}
    for (s, year) in panel:
        if year != t:
            continue
        value, how = grain_base(panel, s, t)
        if value:
            out[s] = value * math.exp(bias) if how == "nass" else value
    return out


def harvested_share(panel, s, t):
    """Mean share of planted corn that was harvested as grain or silage in the three years before t."""
    shares = [(c["grain"] + c["silage"]) / c["planted"] for y in range(t - 3, t)
              if (c := panel.get((s, y))) and c.get("grain") and c.get("silage") and c.get("planted")]
    return sum(shares) / len(shares) if shares else None


def reconcile(panel, t, silage: dict, grain: dict, spread: tuple[float, float, float]) -> tuple[dict, dict]:
    """Make grain + silage equal harvested corn, moving each estimate in proportion to its error variance."""
    s_sd, g_sd, t_sd = spread
    silage, grain = dict(silage), dict(grain)
    for s in set(silage) & set(grain):
        share, planted = harvested_share(panel, s, t), get(panel, s, t, "planted_asof")
        if not share or not planted:
            continue
        total = planted * share
        var = [(s_sd * silage[s]) ** 2, (g_sd * grain[s]) ** 2, (t_sd * total) ** 2]
        gap = total - silage[s] - grain[s]
        silage[s] += gap * var[0] / sum(var)
        grain[s] += gap * var[1] / sum(var)
    return silage, grain


def spreads(panel, years, silage_fn) -> tuple[float, float, float]:
    """Relative error (sd of log actual / predicted) of silage, grain and harvested corn over earlier years."""
    logs = {"s": [], "g": [], "t": []}
    for t in years:
        train = rows_for(panel, range(2000, t))
        test = rows_for(panel, [t])
        if len(train) < 100 or not test:
            continue
        silage, grain = silage_fn(panel, train, test), grain_predict(panel, t, range(2000, t), corrected=False)
        for s, pred in silage.items():
            cell = panel[(s, t)]
            logs["s"].append(math.log(cell["silage"] / pred))
            if s in grain and cell.get("grain"):
                logs["g"].append(math.log(cell["grain"] / grain[s]))
            share, planted = harvested_share(panel, s, t), cell.get("planted_asof")
            if share and planted and cell.get("grain"):
                logs["t"].append(math.log((cell["grain"] + cell["silage"]) / (planted * share)))
    return tuple(float(np.std(logs[k])) if logs[k] else 0.1 for k in ("s", "g", "t"))


# --- scoring --------------------------------------------------------------------------

def score(pred: dict, panel, t, name: str) -> dict | None:
    pairs = [(p, panel[(s, t)][name]) for s, p in pred.items() if p and panel.get((s, t), {}).get(name)]
    if not pairs:
        return None
    actual = sum(a for _, a in pairs)
    return {"states": len(pairs), "state_error": 100 * sum(abs(p - a) for p, a in pairs) / actual,
            "us_error": 100 * (sum(p for p, _ in pairs) / actual - 1)}


def summarise(by_year: dict) -> dict:
    years = sorted(by_year)
    state = [by_year[y]["state_error"] for y in years]
    us = [abs(by_year[y]["us_error"]) for y in years]
    return {"years": len(years), "state_error": float(np.mean(state)), "us_abs_error": float(np.mean(us)),
            "us_bias": float(np.mean([by_year[y]["us_error"] for y in years]))}


def beats(candidate: dict, best: dict, key="state_error") -> tuple[bool, float, float]:
    """True if the candidate's yearly errors are lower by more than two standard errors of the differences."""
    years = sorted(set(candidate) & set(best))
    take = (lambda e: abs(e["us_error"])) if key == "us_abs_error" else (lambda e: e["state_error"])
    d = np.array([take(best[y]) - take(candidate[y]) for y in years])
    se = d.std(ddof=1) / math.sqrt(len(d))
    return bool(d.mean() > 2 * se), float(d.mean()), float(se)


# --- experiment runner -----------------------------------------------------------------

def silage_candidates() -> dict:
    cands = {"same_as_last_year": (silage_same, {}), "mean_of_last_3": (silage_mean3, {})}
    for set_name, names in FEATURE_SETS.items():
        cands[f"nodrift_{set_name}"] = (silage_ridge, {"names": names, "penalty": 1.0, "drift": False})
    for set_name, names in FEATURE_SETS.items():
        for penalty in RIDGE:
            cands[f"ridge_{set_name}_{penalty}"] = (silage_ridge, {"names": names, "penalty": penalty})
    for us_name, us_names in US_SETS.items():
        cands[f"topdown_{us_name}"] = (silage_topdown, {"names": FEATURE_SETS["reversion"], "penalty": 1.0, "us_names": us_names})
    return cands


def backtest(panel, test_years) -> tuple[dict, dict, dict]:
    """Yearly scores of every candidate ({name: {year: score}}) for silage and grain, and the silage predictions."""
    cands = silage_candidates()
    silage, preds = {name: {} for name in cands}, {name: {} for name in cands}
    grain = {"nass_latest": {}, "nass_corrected": {}}
    for t in test_years:
        train, test = rows_for(panel, range(2000, t)), rows_for(panel, [t])
        for name, (fn, kw) in cands.items():
            preds[name][t] = fn(panel, train, test, **kw)
            silage[name][t] = score(preds[name][t], panel, t, "silage")
        for name, corrected in (("nass_latest", False), ("nass_corrected", True)):
            grain[name][t] = score(grain_predict(panel, t, range(2000, t), corrected), panel, t, "grain")
    return silage, grain, preds


def reconciled(panel, t, silage_fn, silage_pred: dict) -> tuple[dict, dict]:
    """The chosen silage model and NASS's grain forecast, adjusted so they add up to harvested corn."""
    spread = spreads(panel, range(t - 8, t), silage_fn)
    return reconcile(panel, t, silage_pred, grain_predict(panel, t, range(2000, t), corrected=False), spread)


def select(scores: dict, order: list[str], start: str, key="state_error") -> tuple[str, list[dict]]:
    """Walk the candidates in order; a candidate becomes the choice only if it clearly beats the current one."""
    best, log = start, []
    for name in order:
        summary = summarise(scores[name])
        won, gain, se = (False, 0.0, 0.0) if name == start else beats(scores[name], scores[best], key)
        log.append({"candidate": name, **{k: round(v, 3) for k, v in summary.items()}, "gain_vs_current": round(gain, 3),
                    "two_se": round(2 * se, 3), "decision": "start" if name == start else ("keep" if won else "discard")})
        if won:
            best = name
    return best, log


def quantiles(log_errors: list[float]) -> tuple[float, float]:
    return float(np.quantile(log_errors, 0.1)), float(np.quantile(log_errors, 0.9))


def interval_table(panel, pick_fn, name: str, years) -> dict:
    """80% bands from the backtest's own misses: by state size class, and for the US total."""
    pairs, us = [], []
    for t in years:
        pred = pick_fn(t)
        got = [(p, panel[(s, t)][name]) for s, p in pred.items() if p and panel.get((s, t), {}).get(name)]
        pairs += got
        us.append(math.log(sum(a for _, a in got) / sum(p for p, _ in got)))
    cuts = np.quantile([p for p, _ in pairs], [1 / 3, 2 / 3])
    classes = [[math.log(a / p) for p, a in pairs if lo <= p < hi] for lo, hi in ((0, cuts[0]), (cuts[0], cuts[1]), (cuts[1], float("inf")))]
    return {"cuts": [float(c) for c in cuts], "bands": [quantiles(c) for c in classes], "us": quantiles(us)}


def band(table: dict, value: float) -> tuple[float, float]:
    lo, hi = table["bands"][sum(value >= c for c in table["cuts"])]
    return value * math.exp(lo), value * math.exp(hi)


def earliness() -> None:
    """Backtest of the models chosen for mid-November, replayed with what was public on earlier dates."""
    chosen = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    names = {"silage": ["same_as_last_year", chosen["silage_base"]], "grain": [chosen["grain_choice"]]}
    with (OUT / "earliness.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["asof", "target", "candidate", "years", "state_error_pct", "us_abs_error_pct", "us_bias_pct"])
        for asof in ("aug", "sep", "oct", "nov"):
            silage, grain, _ = backtest(load_panel(asof), range(FIRST_TEST, LAST_TEST + 1))
            for target, table in (("silage", silage), ("grain", grain)):
                for name in names[target]:
                    m = summarise(table[name])
                    writer.writerow([asof, target, name, m["years"], round(m["state_error"], 2), round(m["us_abs_error"], 2), round(m["us_bias"], 2)])
                    print(f"  {asof}  {target:6s} {name:20s} state error {m['state_error']:5.2f}%   |US error| {m['us_abs_error']:5.2f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asof", default="nov", choices=["aug", "sep", "oct", "nov"])
    parser.add_argument("--score-2025", action="store_true")
    parser.add_argument("--earliness", action="store_true")
    args = parser.parse_args()
    if args.earliness:
        return earliness()
    panel = load_panel(args.asof)
    test_years = range(FIRST_TEST, LAST_TEST + 1)
    silage, grain, preds = backtest(panel, test_years)
    cands = silage_candidates()

    # Selection, on test years up to 2024 only: first the silage model, then whether the binary constraint helps.
    base_pick, silage_log = select(silage, list(silage), "same_as_last_year")
    base_fn = lambda p, tr, te: cands[base_pick][0](p, tr, te, **cands[base_pick][1])  # noqa: E731
    silage["reconciled"], grain["reconciled"] = {}, {}
    for t in test_years:
        rec_s, rec_g = reconciled(panel, t, base_fn, preds[base_pick][t])
        silage["reconciled"][t], grain["reconciled"][t] = score(rec_s, panel, t, "silage"), score(rec_g, panel, t, "grain")
    silage_pick, extra = select({base_pick: silage[base_pick], "reconciled": silage["reconciled"]}, [base_pick, "reconciled"], base_pick)
    silage_log += extra[1:]
    grain_pick, grain_log = select(grain, list(grain), "nass_latest")

    def base_for(t):
        return base_fn(panel, rows_for(panel, range(2000, t)), rows_for(panel, [t], need_truth=False))

    def silage_for(t):
        return reconciled(panel, t, base_fn, base_for(t))[0] if silage_pick == "reconciled" else base_for(t)

    def grain_for(t):
        if grain_pick == "reconciled":
            return reconciled(panel, t, base_fn, base_for(t))[1]
        return grain_predict(panel, t, range(2000, t), corrected=grain_pick == "nass_corrected")

    OUT.mkdir(exist_ok=True)
    with (OUT / "results.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["target", *silage_log[0]], delimiter="\t")
        writer.writeheader()
        writer.writerows([{"target": "silage", **r} for r in silage_log] + [{"target": "grain", **r} for r in grain_log])
    with (OUT / "backtest_by_year.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["target", "candidate", "year", "states", "state_error_pct", "us_error_pct"])
        for target, table, picks in (("silage", silage, {"same_as_last_year", "mean_of_last_3", silage_pick}), ("grain", grain, {"nass_latest", grain_pick})):
            for name in sorted(picks):
                for year, s in table[name].items():
                    writer.writerow([target, name, year, s["states"], round(s["state_error"], 2), round(s["us_error"], 2)])

    # Weights of the richest state model on all years up to 2024, against the signs expected beforehand.
    train = rows_for(panel, range(2000, SCORE_YEAR))
    beta, _, _ = fit_ridge(train, FEATURE_SETS["all"], 1.0, lambda r: math.log(r["actual"] / r["last"]), lambda r: r["last"], drift=False)
    with (OUT / "weights.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["feature", "weight_per_std", "expected_sign", "agrees", "rows_with_value"])
        for n, b in zip(FEATURE_SETS["all"], beta[1:]):
            writer.writerow([n, round(float(b), 4), EXPECTED_SIGN[n], bool(b * EXPECTED_SIGN[n] > 0), sum(r[n] is not None for r in train)])

    metrics = {"asof": args.asof, "test_years": [FIRST_TEST, LAST_TEST], "silage_choice": silage_pick, "silage_base": base_pick, "grain_choice": grain_pick,
               "silage": {n: summarise(silage[n]) for n in ("same_as_last_year", "mean_of_last_3", silage_pick)},
               "grain": {n: summarise(grain[n]) for n in ("nass_latest", grain_pick)}}
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")

    print(f"silage choice: {silage_pick} (on {base_pick})   grain choice: {grain_pick}   (test years {FIRST_TEST}-{LAST_TEST}, as of {args.asof})")
    for target, table, names in (("silage", silage, ["same_as_last_year", "mean_of_last_3", silage_pick]), ("grain", grain, ["nass_latest", grain_pick])):
        for n in dict.fromkeys(names):
            m = summarise(table[n])
            print(f"  {target:6s} {n:24s} state error {m['state_error']:5.2f}%   |US error| {m['us_abs_error']:5.2f}%   US bias {m['us_bias']:+5.2f}%")

    if args.score_2025:
        target = OUT / "score_2025.json"
        if target.exists():
            raise SystemExit(f"{target.name} already exists: the 2025 comparison is run once")
        preds = {"silage": silage_for(SCORE_YEAR), "grain": grain_for(SCORE_YEAR)}
        baseline = {"silage": silage_same(panel, None, rows_for(panel, [SCORE_YEAR])), "grain": {s: get(panel, s, SCORE_YEAR - 1, "grain") for s, _ in preds["grain"].items()}}
        result = {name: {"model": score(preds[name], panel, SCORE_YEAR, name), "same_as_last_year": score(baseline[name], panel, SCORE_YEAR, name)} for name in preds}
        result["choices"] = {"silage": silage_pick, "silage_base": base_pick, "grain": grain_pick}
        target.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        with (OUT / "score_2025_states.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["state", "silage_pred", "silage_actual", "grain_pred", "grain_actual"])
            for s in sorted(set(preds["silage"]) | set(preds["grain"])):
                cell = panel.get((s, SCORE_YEAR), {})
                writer.writerow([s, round(preds["silage"].get(s) or 0), cell.get("silage") or "", round(preds["grain"].get(s) or 0), cell.get("grain") or ""])
        print("2025 held-out score:", json.dumps(result))
        return

    # 2026 forecast, fitted on every year with truth, with 80% bands from the backtest's misses.
    s_bands = interval_table(panel, silage_for, "silage", test_years)
    g_bands = interval_table(panel, grain_for, "grain", test_years)
    s_pred, g_pred = silage_for(FORECAST_YEAR), grain_for(FORECAST_YEAR)
    with (OUT / f"forecast_{FORECAST_YEAR}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "silage_acres", "silage_lo80", "silage_hi80", "grain_acres", "grain_lo80", "grain_hi80", "grain_source"])
        for s in sorted(set(s_pred) | set(g_pred)):
            sv, gv = s_pred.get(s), g_pred.get(s)
            s_cells = [round(sv), *map(round, band(s_bands, sv))] if sv else ["", "", ""]
            g_cells = [round(gv), *map(round, band(g_bands, gv)), grain_base(panel, s, FORECAST_YEAR)[1]] if gv else ["", "", "", ""]
            writer.writerow([s, *s_cells, *g_cells])
        us_s, us_g = sum(s_pred.values()), sum(g_pred.values())
        writer.writerow(["US (sum of states)", round(us_s), round(us_s * math.exp(s_bands["us"][0])), round(us_s * math.exp(s_bands["us"][1])),
                         round(us_g), round(us_g * math.exp(g_bands["us"][0])), round(us_g * math.exp(g_bands["us"][1])), ""])
    print(f"{FORECAST_YEAR} forecast: silage {us_s / 1e6:.3f}M acres in {len(s_pred)} states, grain {us_g / 1e6:.3f}M acres in {len(g_pred)} states")


if __name__ == "__main__":
    main()
