"""Silage acres as a smoothed state level plus drought chopping.

Why: about 10 of the 13 points of state silage error are noise in NASS's own state series. A state's
yearly change mostly reverses the next year (``test_models/accuracy/noise_floor``). So the best guess
of next year's "normal" acres is a smoothed level, not last year's figure. On top of that, in a drought
year farmers chop grain corn that will not yield. That one-off jump is visible by November in NASS's
yield forecast:

    forecast_t = exp(EWMA_alpha(log normal acres, years < t)) + chopped_t
    chopped_t  = gamma * max(0, shortfall_t - TAU) * grain acres_t
    shortfall_t = 1 - (NASS in-season yield forecast) / (linear trend of the 10 previous final yields)
    normal acres = past silage acres minus their own chopped acres

``alpha`` (smoothing) and ``gamma`` (share of grain acres chopped per unit of shortfall) are chosen for
each forecast year on earlier years only, by mean state error. ``TAU`` is fixed at 0.10. Grain acres
are NASS's in-season harvested-for-grain forecast where it exists (2012 on), otherwise last year's
final grain acres. History starts in 2000 (team Quick Stats downloads). The idea comes from
``test_models/varunModel/state_signals.py``.

Backtest 2012-2024 (state WAPE / US abs error): same as last year 15.84% / 5.76%,
this method 13.23% / 3.44% (``test_models/accuracy/noise_floor/README.md``).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from kernelag.state_panel import GRAIN_ASOF, YIELD_ASOF, public_by

FIRST_TUNING_YEAR = 2005        # the first years only warm up the smoothed level and the yield trend
ALPHAS = np.round(np.arange(0.20, 0.95, 0.05), 2)
GAMMAS = np.round(np.arange(0.00, 0.21, 0.01), 2)
TAU = 0.10
TREND_YEARS, MIN_TREND_YEARS = 10, 5
FLOOR = 0.3                     # normal acres never drop below 30% of reported acres

GRAIN_PERIOD = {"nov": "YEAR - NOV FORECAST", "oct": "YEAR - OCT FORECAST",
                "sep": "YEAR - SEP FORECAST", "aug": "YEAR - AUG FORECAST", "jun": "YEAR - JUN ACREAGE"}


def _item(folder: Path, stem: str, short: str) -> pd.DataFrame:
    raw = pd.read_csv(folder / f"{stem}_state_2000_2026.csv", dtype=str, keep_default_na=False)
    rows = raw[(raw["agg_level_desc"] == "STATE") & (raw["source_desc"] == "SURVEY")
               & (raw["domain_desc"] == "TOTAL") & (raw["short_desc"] == short)]
    return pd.DataFrame({"year": rows["year"].astype(int), "state": rows["state_name"],
                         "period": rows["reference_period_desc"],
                         "value": pd.to_numeric(rows["Value"].str.replace(",", ""), errors="coerce")}
                        ).dropna(subset=["value"]).drop_duplicates(["year", "state", "period"])


def _wide(table: pd.DataFrame, periods: list[str]) -> pd.DataFrame:
    """Year x state, from the first of ``periods`` that exists for each state-year."""
    out = pd.DataFrame()
    for period in periods:
        out = out.combine_first(table[table["period"] == period].pivot(index="year", columns="state", values="value"))
    return out


def load_history(folder: Path, asof: str = "nov") -> dict[str, pd.DataFrame]:
    """Year x state tables: silage and grain final acres, final yield, in-season yield and grain."""
    silage = _item(folder, "corn_silage_harvested_acres", "CORN, SILAGE - ACRES HARVESTED")
    grain = _item(folder, "corn_grain_harvested_acres", "CORN, GRAIN - ACRES HARVESTED")
    yields = _item(folder, "corn_grain_yield", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")
    grain_periods = public_by([GRAIN_PERIOD[m] for m in GRAIN_ASOF], asof)
    return {"silage": _wide(silage, ["YEAR"]), "grain": _wide(grain, ["YEAR"]),
            "grain_asof": _wide(grain, grain_periods), "yield": _wide(yields, ["YEAR"]),
            "yield_asof": _wide(yields, public_by(YIELD_ASOF, asof))}


def chopping_exposure(history: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """max(0, shortfall - TAU) x grain acres, per year and state (0 where no yield forecast exists)."""
    final = history["yield"]
    years = sorted(set(final.index) | set(history["yield_asof"].index))
    trend = pd.DataFrame(np.nan, index=years, columns=final.columns)
    for year in years:
        past = final.loc[year - TREND_YEARS:year - 1]
        for state in final.columns:
            y = past[state].dropna()
            if len(y) >= MIN_TREND_YEARS:
                trend.loc[year, state] = np.polyval(np.polyfit(y.index, y.to_numpy(), 1), year)
    shortfall = (1 - history["yield_asof"].reindex(index=years, columns=final.columns) / trend).fillna(0.0)
    grain = history["grain_asof"].reindex(index=years, columns=final.columns)
    grain = grain.fillna(history["grain"].shift(1).reindex(index=years, columns=final.columns))
    return (shortfall - TAU).clip(lower=0) * grain.fillna(0.0)


def _smoothed(log_acres: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """Smoothed log level through year t-1, indexed at year t (one row past the last year)."""
    level, rows = None, {}
    for year, x in log_acres.iterrows():
        level = x if level is None else (alpha * x + (1 - alpha) * level).fillna(level).fillna(x)
        rows[year + 1] = level
    return pd.DataFrame(rows).T


def _forecasts(silage: pd.DataFrame, exposure: pd.DataFrame, alpha: float, gamma: float) -> pd.DataFrame:
    chopped = gamma * exposure.reindex(index=silage.index, columns=silage.columns).fillna(0.0)
    normal = (silage - chopped).clip(lower=FLOOR * silage)
    base = np.exp(_smoothed(np.log(normal), alpha))
    return base + gamma * exposure.reindex(index=base.index, columns=base.columns).fillna(0.0)


def _mean_error(pred: pd.DataFrame, silage: pd.DataFrame, years: range) -> float:
    errors = []
    for t in years:
        p, a = pred.loc[t], silage.loc[t]
        ok = p.notna() & a.notna()
        errors.append((p[ok] - a[ok]).abs().sum() / a[ok].sum())
    return float(np.mean(errors))


def predict(history: dict[str, pd.DataFrame], year: int, exposure: pd.DataFrame | None = None) -> tuple[pd.Series, dict]:
    """Silage acres for ``year`` per state, with alpha and gamma chosen on years before ``year`` only."""
    silage = history["silage"].loc[:year - 1]
    exposure = chopping_exposure(history) if exposure is None else exposure
    past = range(FIRST_TUNING_YEAR, year)
    smoothed = {a: np.exp(_smoothed(np.log(silage), a)) for a in ALPHAS}
    alpha = min(ALPHAS, key=lambda a: _mean_error(smoothed[a], silage, past))
    by_gamma = {g: _forecasts(silage, exposure, alpha, g) for g in GAMMAS}
    gamma = min(GAMMAS, key=lambda g: _mean_error(by_gamma[g], silage, past))
    return by_gamma[gamma].loc[year].dropna(), {"alpha": float(alpha), "gamma": float(gamma)}
