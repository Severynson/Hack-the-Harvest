"""The drought term of the headline silage model (B-S6), per state, for the board's what-if slider.

Same definitions as grain-or-silage.ipynb:
    chopped_t   = gamma x max(0, shortfall_t - 0.10) x last year's grain acres
    shortfall_t = 1 - NASS in-season yield forecast / linear trend of the previous 10 final yields
gamma (share of exposed grain acres farmers chop when the crop fails) is re-chosen on past years only.
The slider replaces this year's shortfall with one the user picks and shows how many extra acres get chopped.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from board.sources import REPO

ALPHAS = np.round(np.arange(0.20, 0.95, 0.05), 2)
GAMMAS = np.round(np.arange(0.00, 0.21, 0.01), 2)
QS = REPO / "data" / "Quickstats Data"


def _item(file: str, short_desc: str) -> pd.DataFrame:
    path = QS / file if (QS / file).exists() else REPO / "data" / "nass" / file
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = raw[(raw["agg_level_desc"] == "STATE") & (raw["source_desc"] == "SURVEY") & (raw["domain_desc"] == "TOTAL") & (raw["short_desc"] == short_desc)]
    out = pd.DataFrame({"year": rows["year"].astype(int), "state": rows["state_alpha"], "period": rows["reference_period_desc"],
                        "value": pd.to_numeric(rows["Value"].str.replace(",", ""), errors="coerce")})
    return out.dropna(subset=["value"]).drop_duplicates(["year", "state", "period"])


def _wide(t: pd.DataFrame, periods: list[str]) -> pd.DataFrame:
    out = pd.DataFrame()
    for p in periods:
        out = out.combine_first(t[t["period"] == p].pivot(index="year", columns="state", values="value"))
    return out


def _level(log_acres: pd.DataFrame, alpha: float) -> pd.DataFrame:
    level, rows = None, {}
    for y, x in log_acres.iterrows():
        level = x if level is None else (alpha * x + (1 - alpha) * level).fillna(level).fillna(x)
        rows[y + 1] = level
    return pd.DataFrame(rows).T


def _err(pred: pd.DataFrame, actual: pd.DataFrame, years) -> float:
    e = []
    for t in years:
        if t not in pred.index or t not in actual.index:
            continue
        p, a = pred.loc[t], actual.loc[t]
        ok = p.notna() & a.notna()
        e.append((p[ok] - a[ok]).abs().sum() / a[ok].sum())
    return float(np.mean(e))


def build(year: int = 2026) -> dict:
    with np.errstate(divide="ignore", invalid="ignore"):
        return _build(year)


def _build(year: int) -> dict:
    grain = _item("corn_grain_harvested_acres_state_2000_2026.csv", "CORN, GRAIN - ACRES HARVESTED")
    silage = _item("corn_silage_harvested_acres_state_2000_2026.csv", "CORN, SILAGE - ACRES HARVESTED")
    yld = _item("corn_grain_yield_state_2000_2026.csv", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")
    g_final, s_final, y_final = (_wide(t[t["year"] < year], ["YEAR"]) for t in (grain, silage, yld))
    y_nov = _wide(yld, ["YEAR - NOV FORECAST", "YEAR - OCT FORECAST", "YEAR - SEP FORECAST", "YEAR - AUG FORECAST"])
    years = sorted(set(y_final.index) | set(y_nov.index))
    trend = pd.DataFrame(np.nan, index=years, columns=y_final.columns)
    for y in years:
        past = y_final.loc[y - 10:y - 1]
        for s in y_final.columns:
            v = past[s].dropna()
            if len(v) >= 5:
                trend.loc[y, s] = np.polyval(np.polyfit(v.index, v.to_numpy(), 1), y)
    shortfall = (1 - y_nov.reindex(index=years, columns=trend.columns) / trend).replace([np.inf, -np.inf], np.nan).clip(-1, 1).fillna(0.0)
    grain_prev = g_final.shift(1).reindex(index=years, columns=trend.columns).fillna(0.0)
    exposure = (shortfall - 0.10).clip(lower=0) * grain_prev
    # gamma exactly as B-S6 picks it for `year`: on finals published before `year`
    sil = s_final.loc[:year - 1]
    past = range(2005, year)
    alpha = min(ALPHAS, key=lambda a: _err(np.exp(_level(np.log(sil), a)), sil, past))

    def fc(g):
        chopped = g * exposure.reindex(index=sil.index, columns=sil.columns).fillna(0.0)
        base = np.exp(_level(np.log((sil - chopped).clip(lower=0.3 * sil)), alpha))
        return base + g * exposure.reindex(index=base.index, columns=base.columns).fillna(0.0)
    gamma = float(min(GAMMAS, key=lambda g: _err(fc(g), sil, past)))
    last = g_final.loc[year - 1]
    states = {}
    for s in trend.columns:
        sf = shortfall.loc[year, s] if year in shortfall.index else 0.0
        if np.isfinite(last.get(s, np.nan)):
            states[s] = {"shortfall": round(float(sf), 4), "grain_last": float(last[s]), "trend": round(float(trend.loc[year, s]), 1) if np.isfinite(trend.loc[year, s]) else None,
                         "yield_fc": float(y_nov.loc[year, s]) if year in y_nov.index and s in y_nov.columns and np.isfinite(y_nov.loc[year, s]) else None}
    worst = {}
    for y in years:
        if y >= year or y not in shortfall.index:
            continue
        for s, v in shortfall.loc[y].items():
            if v > worst.get(s, (0, None))[0]:
                worst[s] = (round(float(v), 3), int(y))
    by_year = {int(y): {s: round(float(v), 3) for s, v in shortfall.loc[y].items() if np.isfinite(v)} for y in years if 2005 <= y < year}
    return {"year": year, "gamma": gamma, "by_year": by_year, "alpha": float(alpha), "threshold": 0.10, "states": states,
            "worst": {s: {"shortfall": v, "year": y} for s, (v, y) in worst.items()},
            "note": "Drought term of B-S6 (grain-or-silage.ipynb): gamma x max(0, yield shortfall - 10%) x last year's grain acres."}


if __name__ == "__main__":
    d = build()
    print("gamma", d["gamma"], "alpha", d["alpha"], len(d["states"]), "states")
    print({k: v for k, v in list(d["states"].items())[:4]})
    print(sorted(((v["shortfall"], v["year"], s) for s, v in d["worst"].items()), reverse=True)[:6])
