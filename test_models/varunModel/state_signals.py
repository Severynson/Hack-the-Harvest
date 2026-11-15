"""Exploration (not part of the clean pipeline): which public November signals cut silage acreage error.

Long backtest on Quick Stats state history, 2000-2024 (2025 is the held-out scoring year and is
never read). Every input is something published by mid-November of the forecast year:
    corn planted (Jun/Aug/Oct acreage), harvested for grain and yield (November forecasts),
    hay production (October forecast, else August), hay stocks (1 May), hay and milk prices
    (January to September), milk cows (1 January), cattle on feed (1 October), last years' silage.

A forecast is ``base * exp(x @ beta)``: a base from silage history plus a pooled, acre-weighted
regression of the log change on the signals. ``beta`` is fitted only on years before the forecast
year (expanding window, as it would have run in real time), so every score is out of sample.

Scores (forecast years 2008-2024 unless stated):
    us_abs     mean absolute error of the US total (sum of states), percent
    us_worst   worst year of that
    in4        years with the US total within 4 percent
    wape       state error weighted by acres: sum |forecast - truth| / sum truth, percent

Run: ``python test_models/varunModel/state_signals.py``
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from kernelag.paths import data_dir

QS = data_dir() / "Quickstats Data"
LAST_YEAR = 2024                 # 2025 is the scoring year: never loaded into this backtest
FIRST_FORECAST = 2008
RIDGE = 2.0                      # mild shrinkage; signals are standardised first
PLAINS = {"KANSAS", "NEBRASKA", "SOUTH DAKOTA", "NORTH DAKOTA", "TEXAS", "COLORADO", "OKLAHOMA"}


def series(file: str, short: str, ref: str | list[str]) -> pd.Series:
    """One Quick Stats item as a (state, year) series. A list of periods means 'first one available'."""
    d = pd.read_csv(QS / file, dtype=str, keep_default_na=False)
    d = d[(d["agg_level_desc"] == "STATE") & (d["short_desc"] == short)]
    d = d.assign(value=pd.to_numeric(d["Value"].str.replace(",", ""), errors="coerce"), year=d["year"].astype(int))
    d = d[d["year"] <= LAST_YEAR]
    refs = [ref] if isinstance(ref, str) else ref
    out = None
    for r in refs:
        s = d[d["reference_period_desc"] == r].groupby(["state_name", "year"])["value"].first()
        out = s if out is None else out.combine_first(s)
    return out


def monthly_mean(file: str, short: str, months: list[str]) -> pd.Series:
    d = pd.read_csv(QS / file, dtype=str, keep_default_na=False)
    d = d[(d["agg_level_desc"] == "STATE") & (d["short_desc"] == short) & d["reference_period_desc"].isin(months)]
    d = d.assign(value=pd.to_numeric(d["Value"].str.replace(",", ""), errors="coerce"), year=d["year"].astype(int))
    return d[d["year"] <= LAST_YEAR].groupby(["state_name", "year"])["value"].mean()


def build_panel() -> pd.DataFrame:
    jan_sep = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP"]
    cols = {
        "silage": series("corn_silage_harvested_acres_state_2000_2026.csv", "CORN, SILAGE - ACRES HARVESTED", "YEAR"),
        "grain": series("corn_grain_harvested_acres_state_2000_2026.csv", "CORN, GRAIN - ACRES HARVESTED", "YEAR"),
        "grain_nov": series("corn_grain_harvested_acres_state_2000_2026.csv", "CORN, GRAIN - ACRES HARVESTED",
                            ["YEAR - NOV FORECAST", "YEAR - OCT FORECAST", "YEAR - SEP FORECAST", "YEAR - AUG FORECAST"]),
        "planted": series("corn_planted_acres_state_2000_2026.csv", "CORN - ACRES PLANTED", "YEAR"),
        "planted_asof": series("corn_planted_acres_state_2000_2026.csv", "CORN - ACRES PLANTED",
                               ["YEAR - OCT ACREAGE", "YEAR - AUG ACREAGE", "YEAR - JUN ACREAGE"]),
        "yield": series("corn_grain_yield_state_2000_2026.csv", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE", "YEAR"),
        "yield_nov": series("corn_grain_yield_state_2000_2026.csv", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE",
                            ["YEAR - NOV FORECAST", "YEAR - OCT FORECAST", "YEAR - SEP FORECAST"]),
        "hay": series("hay_production_state_2000_2026.csv", "HAY - PRODUCTION, MEASURED IN TONS", "YEAR"),
        "alf_fc": series("hay_production_state_2000_2026.csv", "HAY, ALFALFA - PRODUCTION, MEASURED IN TONS",
                         ["YEAR - OCT FORECAST", "YEAR - AUG FORECAST"]),
        "oth_fc": series("hay_production_state_2000_2026.csv", "HAY, (EXCL ALFALFA) - PRODUCTION, MEASURED IN TONS",
                         ["YEAR - OCT FORECAST", "YEAR - AUG FORECAST"]),
        "alf": series("hay_production_state_2000_2026.csv", "HAY, ALFALFA - PRODUCTION, MEASURED IN TONS", "YEAR"),
        "oth": series("hay_production_state_2000_2026.csv", "HAY, (EXCL ALFALFA) - PRODUCTION, MEASURED IN TONS", "YEAR"),
        "hay_stock_may": series("hay_stocks_state_2000_2026.csv", "HAY, ON FARM - STOCKS, MEASURED IN TONS", "FIRST OF MAY"),
        "hay_price": monthly_mean("hay_price_received_state_2000_2026.csv", "HAY - PRICE RECEIVED, MEASURED IN $ / TON", jan_sep),
        "milk_price": monthly_mean("milk_price_received_state_2000_2026.csv", "MILK - PRICE RECEIVED, MEASURED IN $ / CWT", jan_sep),
        "cows": series("milk_cow_inventory_state_2000_2026.csv", "CATTLE, COWS, MILK - INVENTORY", "FIRST OF JAN"),
        "on_feed": series("cattle_on_feed_state_2000_2026.csv", "CATTLE, ON FEED - INVENTORY", "FIRST OF OCT"),
    }
    p = pd.DataFrame(cols).rename_axis(["state", "year"]).reset_index()
    p = p[p["state"] != "OTHER STATES"].sort_values(["state", "year"]).reset_index(drop=True)
    g = p.groupby("state")
    last = lambda c: g[c].shift()                                           # noqa: E731
    p["last"] = last("silage")
    p["mean3"] = g["silage"].transform(lambda s: s.shift().rolling(3).mean())
    p["ewma"] = g["silage"].transform(lambda s: s.ewm(alpha=0.5, adjust=False).mean().shift())
    with np.errstate(divide="ignore", invalid="ignore"):
        # Non-grain acres: this year's November view against last year's November view (same vintage).
        p["res_nov"] = p["planted_asof"] - p["grain_nov"]
        p["x_res"] = np.log(p["res_nov"].clip(lower=1000) / last("res_nov").clip(lower=1000))
        p["x_planted"] = np.log(p["planted_asof"] / last("planted"))
        trend = g["yield"].transform(lambda s: s.shift().rolling(3).mean())
        p["x_yield"] = np.log(p["yield_nov"] / trend)
        p["x_yield_plains"] = p["x_yield"] * p["state"].isin(PLAINS)
        p["x_drought_plains"] = ((p["x_yield"] < np.log(0.9)) & p["state"].isin(PLAINS)).astype(float)
        hay_fc = p["alf_fc"].fillna(0) + p["oth_fc"].fillna(0)
        hay_last = (last("alf").fillna(0) + last("oth").fillna(0))
        p["x_hay"] = np.where((hay_fc > 0) & (hay_last > 0), np.log(hay_fc / hay_last), np.nan)
        p["x_hay_stock"] = np.log(p["hay_stock_may"] / last("hay_stock_may"))
        p["x_hay_price"] = np.log(p["hay_price"] / last("hay_price"))
        p["x_milk_price"] = np.log(p["milk_price"] / last("milk_price"))
        p["x_cows"] = np.log(p["cows"] / last("cows"))
        p["x_on_feed"] = np.log(p["on_feed"] / last("on_feed"))
        p["x_reversion"] = np.log(p["last"] / g["silage"].transform(lambda s: s.shift(2).rolling(3).mean()))
    return p.replace([np.inf, -np.inf], np.nan)


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, base: str, features: list[str]) -> np.ndarray:
    """Acre-weighted ridge on the log change from ``base``; missing signals count as 'no change' (0)."""
    if not features:
        return test[base].to_numpy()
    t = train.dropna(subset=[base, "silage"])
    t = t[t[base] > 0]
    x, xt = t[features].fillna(0).to_numpy(), test[features].fillna(0).to_numpy()
    mu, sd = x.mean(0), x.std(0) + 1e-9
    x, xt = (x - mu) / sd, (xt - mu) / sd
    y = np.log(t["silage"] / t[base]).to_numpy()
    w = np.sqrt(t[base].to_numpy())
    xw, yw = x * w[:, None], y * w
    intercept = np.average(y, weights=w ** 2)
    beta = np.linalg.solve(xw.T @ xw + RIDGE * len(t) / 100 * np.eye(len(features)), xw.T @ (yw - intercept * w))
    return test[base].to_numpy() * np.exp(intercept + xt @ beta)


def backtest(p: pd.DataFrame, base: str, features: list[str], first: int = FIRST_FORECAST) -> pd.DataFrame:
    rows = []
    for year in range(first, LAST_YEAR + 1):
        test = p[(p["year"] == year)].dropna(subset=[base, "silage"])
        train = p[(p["year"] < year) & (p["year"] >= 2003)]
        rows.append(test.assign(forecast=fit_predict(train, test, base, features)))
    return pd.concat(rows)


def score(f: pd.DataFrame, years: range | None = None) -> dict:
    if years is not None:
        f = f[f["year"].isin(years)]
    by = f.groupby("year")
    us = (by["forecast"].sum() / by["silage"].sum() - 1) * 100
    return {"us_abs": round(us.abs().mean(), 2), "us_worst": round(us.abs().max(), 1), "in4": f"{int((us.abs() <= 4).sum())}/{len(us)}",
            "wape": round((f["forecast"] - f["silage"]).abs().sum() / f["silage"].sum() * 100, 2)}


CANDIDATES = {
    "persistence": ("last", []),
    "mean3": ("mean3", []),
    "ewma": ("ewma", []),
    "ewma+drought_plains": ("ewma", ["x_drought_plains"]),
    "ewma+yield_plains": ("ewma", ["x_yield_plains"]),
    "ewma+res": ("ewma", ["x_res"]),
    "ewma+planted": ("ewma", ["x_planted"]),
    "ewma+hay": ("ewma", ["x_hay"]),
    "ewma+hay_stock": ("ewma", ["x_hay_stock"]),
    "ewma+hay_price": ("ewma", ["x_hay_price"]),
    "ewma+milk_price": ("ewma", ["x_milk_price"]),
    "ewma+cows": ("ewma", ["x_cows"]),
    "ewma+on_feed": ("ewma", ["x_on_feed"]),
    "last+reversion": ("last", ["x_reversion"]),
    "ewma+yield_plains+res+planted": ("ewma", ["x_yield_plains", "x_res", "x_planted"]),
    "ewma+yield_plains+hay+planted": ("ewma", ["x_yield_plains", "x_hay", "x_planted"]),
    "ewma+all": ("ewma", ["x_yield_plains", "x_res", "x_planted", "x_hay", "x_hay_stock", "x_cows", "x_milk_price"]),
}


def add_shortfall(p: pd.DataFrame, trend_years: int = 10) -> pd.DataFrame:
    """Yield shortfall = 1 - November yield forecast / linear trend of earlier final yields (0 if above trend)."""
    def trend_value(s: pd.Series) -> pd.Series:
        out = pd.Series(np.nan, index=s.index)
        years, values = s.index.get_level_values("year").to_numpy(), s.to_numpy()
        for i in range(len(s)):
            ok = (years < years[i]) & (years >= years[i] - trend_years) & ~np.isnan(values)
            if ok.sum() >= 4:
                slope, icpt = np.polyfit(years[ok], values[ok], 1)
                out.iloc[i] = icpt + slope * years[i]
        return out

    y = p.set_index(["state", "year"])["yield"]
    p["yield_trend"] = y.groupby(level="state", group_keys=False).apply(trend_value).to_numpy()
    p["shortfall"] = (1 - p["yield_nov"] / p["yield_trend"]).clip(lower=0).fillna(0)
    p["grain_now"] = p["grain_nov"].fillna(p.groupby("state")["grain"].shift())
    return p


def switch_forecast(p: pd.DataFrame, gamma: float, tau: float, alpha: float = 0.5) -> pd.DataFrame:
    """Silage = normal demand (smoothed history with past drought chopping removed) + chopped grain acres.

    chopped_t = gamma * max(0, shortfall_t - tau) * grain acres_t. One number, gamma, says what share
    of grain acres is chopped per unit of yield shortfall above tau.
    """
    out = p.copy()
    out["chopped"] = gamma * (out["shortfall"] - tau).clip(lower=0) * out["grain_now"].fillna(0)
    out["normal"] = (out["silage"] - out["chopped"]).clip(lower=0.3 * out["silage"])
    out["normal_base"] = out.groupby("state")["normal"].transform(lambda s: s.ewm(alpha=alpha, adjust=False).mean().shift())
    out["forecast"] = out["normal_base"] + out["chopped"]
    return out


def switch_backtest(p: pd.DataFrame, tau: float, alpha: float = 0.5, first: int = FIRST_FORECAST) -> pd.DataFrame:
    """gamma picked on years before the forecast year only (grid search on absolute acre error)."""
    grid = np.round(np.arange(0, 0.61, 0.02), 2)
    runs = {g: switch_forecast(p, g, tau, alpha) for g in grid}
    rows = []
    for year in range(first, LAST_YEAR + 1):
        def loss(g: float) -> float:
            r = runs[g]
            r = r[(r["year"] < year) & (r["year"] >= 2003)].dropna(subset=["forecast", "silage"])
            return float((r["forecast"] - r["silage"]).abs().sum())
        g = min(grid, key=loss)
        r = runs[g]
        rows.append(r[r["year"] == year].dropna(subset=["forecast", "silage"]).assign(gamma=g))
    return pd.concat(rows)


def switch_plus_backtest(p: pd.DataFrame, tau: float, features: list[str], alpha: float = 0.5) -> pd.DataFrame:
    """Switch model whose normal-demand part also moves with signals: normal_base * exp(x @ beta) + chopped."""
    grid = np.round(np.arange(0, 0.61, 0.02), 2)
    runs = {g: switch_forecast(p, g, tau, alpha) for g in grid}
    rows = []
    for year in range(FIRST_FORECAST, LAST_YEAR + 1):
        def loss(g: float) -> float:
            r = runs[g]
            r = r[(r["year"] < year) & (r["year"] >= 2003)].dropna(subset=["forecast", "silage"])
            return float((r["forecast"] - r["silage"]).abs().sum())
        g = min(grid, key=loss)
        r = runs[g]
        train = r[(r["year"] < year) & (r["year"] >= 2003)].assign(silage=lambda d: d["normal"])
        test = r[r["year"] == year].dropna(subset=["normal_base", "silage"])
        normal = fit_predict(train, test, "normal_base", features)
        rows.append(test.assign(forecast=normal + test["chopped"], gamma=g))
    return pd.concat(rows)


def main() -> None:
    pd.set_option("display.width", 220)
    p = add_shortfall(build_panel())
    print(f"panel: {p['state'].nunique()} states, {p['year'].min()}-{p['year'].max()}, "
          f"{p['silage'].notna().sum()} silage state-years")
    print("signal coverage 2008-2024:", {c: int(p.loc[p.year >= 2008, c].notna().sum()) for c in p if c.startswith("x_")})
    results, forecasts = {}, {}
    for name, (base, features) in CANDIDATES.items():
        f = backtest(p, base, features)
        forecasts[name] = f
        results[name] = {**score(f), **{f"{k}_17_24": v for k, v in score(f, range(2017, 2025)).items() if k in ("us_abs", "wape")}}
    combo = forecasts["ewma"].copy()
    parts = ["ewma", "mean3", "ewma+yield_plains+res+planted"]
    combo["forecast"] = np.exp(np.mean([np.log(forecasts[k].set_index(["state", "year"])["forecast"]) for k in parts], axis=0))
    results["combo(ewma,mean3,model)"] = {**score(combo), **{f"{k}_17_24": v for k, v in score(combo, range(2017, 2025)).items() if k in ("us_abs", "wape")}}
    for tau in (0.0, 0.05, 0.10):
        for alpha in (0.5, 0.7):
            f = switch_backtest(p, tau, alpha)
            name = f"switch(tau={tau},a={alpha})"
            forecasts[name] = f
            results[name] = {**score(f), **{f"{k}_17_24": v for k, v in score(f, range(2017, 2025)).items() if k in ("us_abs", "wape")},
                             "gamma": f"{f.gamma.min()}-{f.gamma.max()}"}
    for tau in (0.10, 0.15):
        for extra in ([], ["x_milk_price"], ["x_cows"], ["x_milk_price", "x_cows"], ["x_hay"], ["x_planted"],
                      ["x_milk_price", "x_cows", "x_hay"], ["x_milk_price", "x_cows", "x_planted"]):
            f = switch_plus_backtest(p, tau, extra)
            name = f"switch{tau}+" + "+".join(c[2:] for c in extra)
            forecasts[name] = f
            results[name] = {**score(f), **{f"{k}_17_24": v for k, v in score(f, range(2017, 2025)).items() if k in ("us_abs", "wape")},
                             "gamma": f"{f.gamma.min()}-{f.gamma.max()}"}
    table = pd.DataFrame(results).T
    print(table.to_string())
    table.to_csv(data_dir() / "models" / "explore_state_signals.csv", lineterminator="\n")
    best = min(results, key=lambda k: results[k]["us_abs"])
    print("gamma by year for best:", forecasts[best].groupby("year")["gamma"].first().to_dict() if "gamma" in forecasts[best] else "-")
    f = forecasts.get(best, combo)
    by = f.groupby("year")
    print(f"\nUS total error by year, {best}:", ((by['forecast'].sum() / by['silage'].sum() - 1) * 100).round(1).to_dict())
    by = forecasts["persistence"].groupby("year")
    print("US total error by year, persistence:", ((by['forecast'].sum() / by['silage'].sum() - 1) * 100).round(1).to_dict())


if __name__ == "__main__":
    main()
