"""Exploration: is silage acreage error limited by the model or by the data?

Two questions, answered on public NASS state data, 2000-2024 (2025 is never read):

1. How noisy is the target itself?
   - NASS survey vs Census of Agriculture silage acres for the same state and year (2017, 2022).
   - Variance of the yearly log change, split into a national part (common to all states) and a
     state part; the state part's lag-1 autocorrelation tells transient noise (-0.5) from lasting
     change (0). Under a level-plus-noise model, -cov(lag 1) is the transient noise variance.
   - The state error any forecaster must accept if it cannot see that transient part.
   - An oracle that knows each year's true national change: how much would that help?

2. How much do simple, physically motivated forecasts close the remaining gap?
   - same as last year
   - smoothed level (EWMA in logs, smoothing weight chosen on earlier years only)
   - smoothed level + drought chopping: gamma * max(0, yield shortfall - 0.10) * grain acres
     (idea from test_models/varunModel/state_signals.py; gamma chosen on earlier years only)
   Paired with the stored incumbents in test_models/accuracy/state/by_year.csv.

Every forecast for year t uses data up to t-1 plus what NASS publishes by mid-November of t
(November yield forecast, harvested-for-grain forecast). Revised (current-vintage) data; a replay.

Run: .venv/bin/python test_models/accuracy/noise_floor.py
Writes test_models/accuracy/noise_floor/{results.json,by_year.csv}
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
QS = ROOT / "data" / "Quickstats Data"
PANEL = ROOT / "test_models" / "danielModel" / "out" / "panel_nov.csv"
INCUMBENTS = ROOT / "test_models" / "accuracy" / "state" / "by_year.csv"
OUT = Path(__file__).resolve().parent / "noise_floor"
LAST_YEAR = 2024
YEARS = list(range(2012, LAST_YEAR + 1))
ALPHAS = np.round(np.arange(0.2, 0.95, 0.05), 2)
GAMMAS = np.round(np.arange(0.0, 0.21, 0.01), 2)
TAU = 0.10                     # shortfall below which nothing is chopped (fixed, not tuned)
SHORT = "CORN, SILAGE - ACRES HARVESTED"


def quickstats(file: str, source: str) -> pd.DataFrame:
    d = pd.read_csv(QS / file, dtype=str, keep_default_na=False)
    d = d[(d["agg_level_desc"] == "STATE") & (d["short_desc"] == SHORT) & (d["domain_desc"] == "TOTAL")
          & (d["source_desc"] == source) & (d["reference_period_desc"] == "YEAR")]
    d = d.assign(v=pd.to_numeric(d["Value"].str.replace(",", ""), errors="coerce"), year=d["year"].astype(int))
    return d[d["year"] <= LAST_YEAR].pivot_table(index="year", columns="state_name", values="v")


def census_gap() -> dict:
    survey = quickstats("corn_silage_harvested_acres_state_2015_2025.csv", "SURVEY")
    census = quickstats("corn_silage_harvested_acres_state_2015_2025.csv", "CENSUS")
    out = {}
    for year in (2017, 2022):
        both = pd.DataFrame({"s": survey.loc[year], "c": census.loc[year]}).dropna()
        out[str(year)] = {"states": len(both),
                          "state_gap_pct": round(100 * (both.s - both.c).abs().sum() / both.c.sum(), 1),
                          "us_gap_pct": round(100 * (both.s.sum() / both.c.sum() - 1), 1)}
    return out


def decomposition(acres: pd.DataFrame) -> dict:
    change = np.log(acres).diff().iloc[1:]
    size = acres.mean()
    weight = size / size.sum()
    national = change.mul(size).sum(axis=1) / change.notna().mul(size).sum(axis=1)
    state = change.sub(national, axis=0)
    var_total = (change.var() * weight).sum()
    var_state = (state.var() * weight).sum()
    cov1 = pd.Series({s: state[s].autocorr(1) * state[s].var() for s in state})
    rho = cov1 / state.var()
    noise_sd = np.sqrt((-cov1).clip(lower=0))
    floor = 100 * (noise_sd * np.sqrt(2 / np.pi) * weight).sum()   # E|N(0, sd)| summed by acres
    last = acres.shift(1).loc[YEARS]
    truth = acres.loc[YEARS]
    oracle = last.mul(np.exp(national.loc[YEARS]), axis=0)
    wape = lambda p: 100 * float(((p - truth).abs().sum(axis=1) / truth.sum(axis=1)).mean())
    return {"states": acres.shape[1], "years": f"{acres.index.min()}-{acres.index.max()}",
            "national_share_of_change_variance": round(1 - var_state / var_total, 3),
            "state_change_lag1_autocorr": round(float((rho * weight).sum()), 3),
            "transient_noise_sd_log": round(float((noise_sd * weight).sum()), 3),
            "noise_floor_state_wape_pct": round(float(floor), 1),
            "persistence_state_wape_pct": round(wape(last), 2),
            "persistence_plus_oracle_national_change_pct": round(wape(oracle), 2)}


def ewma_base(log_acres: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """Smoothed log level through year t-1, indexed at t."""
    level, rows = None, {}
    for year, x in log_acres.iterrows():
        level = x if level is None else (alpha * x + (1 - alpha) * level).fillna(level).fillna(x)
        rows[year] = level
    return pd.DataFrame(rows).T.shift(1)


def shortfall(panel: pd.DataFrame) -> pd.DataFrame:
    """1 - November yield forecast / linear trend of the 10 previous final yields (0 if no forecast)."""
    yld = panel.pivot(index="year", columns="state", values="yield")
    now = panel.pivot(index="year", columns="state", values="yield_asof")
    trend = pd.DataFrame(index=yld.index, columns=yld.columns, dtype=float)
    for year in yld.index:
        past = yld.loc[year - 10:year - 1]
        for s in yld.columns:
            y = past[s].dropna()
            if len(y) >= 5:
                b = np.polyfit(y.index, y.values, 1)
                trend.loc[year, s] = np.polyval(b, year)
    return (1 - now / trend).fillna(0.0)


def candidates(panel: pd.DataFrame) -> pd.DataFrame:
    acres = panel.pivot(index="year", columns="state", values="silage").loc[:LAST_YEAR]
    grain = panel.pivot(index="year", columns="state", values="grain_asof").loc[:LAST_YEAR]
    grain = grain.fillna(panel.pivot(index="year", columns="state", values="planted_asof").loc[:LAST_YEAR] * 0.9)
    over = (shortfall(panel).loc[:LAST_YEAR] - TAU).clip(lower=0) * grain.fillna(0)
    bases = {a: np.exp(ewma_base(np.log(acres), a)) for a in ALPHAS}
    # chopping-adjusted history: remove past chopped acres before smoothing
    err = lambda p, t: float((p.loc[t] - acres.loc[t]).abs().sum() / acres.loc[t][p.loc[t].notna()].sum())

    rows = []
    for year in YEARS:
        past = range(2005, year)
        alpha = min(ALPHAS, key=lambda a: np.mean([err(bases[a], t) for t in past]))

        def chop_pred(g: float, a: float) -> pd.DataFrame:
            normal = (acres - g * over).clip(lower=0.3 * acres)
            return np.exp(ewma_base(np.log(normal), a)) + g * over

        gamma = min(GAMMAS, key=lambda g: np.mean([err(chop_pred(g, alpha), t) for t in past]))
        preds = {"same_as_last_year": acres.shift(1), "smoothed": bases[alpha],
                 "smoothed_plus_chopping": chop_pred(gamma, alpha)}
        truth = acres.loc[year]
        for name, p in preds.items():
            p = p.loc[year].reindex(truth.index)
            ok = p.notna() & truth.notna()
            rows.append({"year": year, "candidate": name, "alpha": alpha, "gamma": gamma,
                         "state_wape_pct": 100 * (p[ok] - truth[ok]).abs().sum() / truth[ok].sum(),
                         "us_abs_error_pct": 100 * abs(p[ok].sum() / truth[ok].sum() - 1), "states": int(ok.sum())})
    return pd.DataFrame(rows)


def paired(by_year: pd.DataFrame, against: str, metric: str) -> dict:
    t = by_year.pivot(index="year", columns="candidate", values=metric)
    out = {}
    for name in t.columns:
        if name == against:
            continue
        d = (t[against] - t[name]).dropna()
        out[name] = {"mean": round(float(t[name].mean()), 2), "gain_vs_" + against: round(float(d.mean()), 2),
                     "se": round(float(d.std(ddof=1) / np.sqrt(len(d))), 2), "years": len(d)}
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    survey = quickstats("corn_silage_harvested_acres_state_2000_2026.csv", "SURVEY").dropna(axis=1, thresh=20)
    panel = pd.read_csv(PANEL)
    panel = panel[panel["year"] <= LAST_YEAR]
    by_year = candidates(panel)
    inc = pd.read_csv(INCUMBENTS)
    inc = inc[inc["candidate"].isin(["lad_core", "ridge_reversion", "fixed_ensemble"]) & inc["year"].isin(YEARS)]
    inc = inc.rename(columns={"state_wape_pct": "state_wape_pct", "national_abs_error_pct": "us_abs_error_pct"})
    keep = ["year", "candidate", "state_wape_pct", "us_abs_error_pct"]
    both = pd.concat([by_year[keep], inc[[c for c in keep if c in inc]]], ignore_index=True)
    by_year.to_csv(OUT / "by_year.csv", index=False, float_format="%.4f")
    results = {
        "census_vs_survey": census_gap(),
        "decomposition": decomposition(survey),
        "forecast_years": f"{YEARS[0]}-{YEARS[-1]}",
        "state_wape_vs_persistence": paired(both, "same_as_last_year", "state_wape_pct"),
        "state_wape_vs_lad_core": paired(both, "lad_core", "state_wape_pct"),
        "us_abs_error_vs_persistence": paired(both, "same_as_last_year", "us_abs_error_pct"),
        "us_abs_error_vs_lad_core": paired(both, "lad_core", "us_abs_error_pct"),
        "chosen_alpha_by_year": by_year.groupby("year")["alpha"].first().to_dict(),
        "chosen_gamma_by_year": by_year.groupby("year")["gamma"].first().to_dict(),
        "tau_fixed": TAU,
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=1, default=float))
    print(json.dumps({k: results[k] for k in ["census_vs_survey", "decomposition"]}, indent=1))
    for k in ["state_wape_vs_lad_core", "us_abs_error_vs_lad_core"]:
        print(k, json.dumps(results[k]))


if __name__ == "__main__":
    main()
