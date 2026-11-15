"""Throwaway scan: can anything public by mid-November beat reversion_only on state silage acres?

Same expanding-window backtest as kernelag.state_model (2017 to 2024; 2025 never touched).
Run: .venv/bin/python test_models/manrajModel/silage_scan.py
"""
import numpy as np
import pandas as pd

from kernelag import state_model as sm
from kernelag.paths import data_dir
from kernelag.state_panel import load_panel

QS = data_dir() / "Quickstats Data"


def series(stem, item, periods):
    d = pd.read_csv(QS / f"{stem}_state_2000_2026.csv", dtype=str)
    d = d[(d["short_desc"] == item) & d["reference_period_desc"].isin(periods)]
    d = d.assign(value=pd.to_numeric(d["Value"].str.replace(",", ""), errors="coerce"), year=d["year"].astype(int))
    return d.groupby(["state_name", "year"])["value"].mean().rename_axis(["state", "year"])


table = sm.add_changes(load_panel("nov"))
key = pd.MultiIndex.from_frame(table[["state", "year"]])


def col(s):
    return s.reindex(key).to_numpy()


def lag(s):
    return s.rename(lambda y: y + 1, level="year")


stocks = series("hay_stocks", "HAY, ON FARM - STOCKS, MEASURED IN TONS", ["FIRST OF MAY"])
table["d_hay_stocks"] = np.log(col(stocks) / col(lag(stocks)))
hay_now = series("hay_production", "HAY, (EXCL ALFALFA) - PRODUCTION, MEASURED IN TONS", ["YEAR - AUG FORECAST"])
hay_final = series("hay_production", "HAY, (EXCL ALFALFA) - PRODUCTION, MEASURED IN TONS", ["YEAR"])
table["d_hay_prod"] = np.log(col(hay_now) / col(lag(hay_final)))
alf_now = series("hay_production", "HAY, ALFALFA - PRODUCTION, MEASURED IN TONS", ["YEAR - AUG FORECAST"])
alf_final = series("hay_production", "HAY, ALFALFA - PRODUCTION, MEASURED IN TONS", ["YEAR"])
table["d_alf_prod"] = np.log(col(alf_now) / col(lag(alf_final)))
milk = series("milk_price_received", "MILK - PRICE RECEIVED, MEASURED IN $ / CWT", ["JAN", "FEB", "MAR", "APR", "MAY", "JUN"])
table["d_milk_price"] = np.log(col(milk) / col(lag(milk)))
# Longer and shorter reversion anchors.
sil = table.set_index(["state", "year"])["silage"]
for name, ks in {"rev2": (2,), "rev23": (2, 3), "rev2to6": (2, 3, 4, 5, 6)}.items():
    anchor = np.nanmean([col(sil.rename(lambda y, k=k: y + k, level="year")) for k in ks], axis=0) \
        if False else np.mean([col(sil.rename(lambda y, k=k: y + k, level="year")) for k in ks], axis=0)
    table[name] = np.log(table["silage_last"] / anchor)
table["residual"] = table["planted_asof"] - table["grain_asof"]
# Planted minus grain ("residual") is silage plus abandoned acres. Its change says most where
# silage is most of it, so the change is also weighted by last year's silage share of the residual.
resid_last = table["planted_last"] - table["grain_last"]
with np.errstate(divide="ignore", invalid="ignore"):
    table["d_resid"] = np.log(table["residual"] / resid_last).clip(-1, 1)
    table["sil_frac"] = (table["silage_last"] / resid_last).clip(0, 1)
table["d_resid_w"] = table["d_resid"] * table["sil_frac"]
table["d_resid_w2"] = table["d_resid"] * table["sil_frac"] ** 2
table = table.replace([np.inf, -np.inf], np.nan)

SETS = {
    "reversion_only": ["reversion"],
    "rev2": ["rev2"], "rev23": ["rev23"], "rev2to6": ["rev2to6"], "rev+rev2": ["reversion", "rev2"],
    "rev+hay_stocks": ["reversion", "d_hay_stocks"],
    "rev+hay_prod": ["reversion", "d_hay_prod"],
    "rev+alf_prod": ["reversion", "d_alf_prod"],
    "rev+milk": ["reversion", "d_milk_price"],
    "rev+planted": ["reversion", "d_planted"],
    "rev+not_grain": ["reversion", "d_not_grain"],
    "rev+drought": ["reversion", "d_drought"],
    "rev+resid": ["reversion", "d_resid"],
    "rev+resid_w": ["reversion", "d_resid_w"],
    "rev+resid_w2": ["reversion", "d_resid_w2"],
    "rev+resid_w+planted": ["reversion", "d_resid_w", "d_planted"],
    "rev+forage": ["reversion", "d_hay_stocks", "d_hay_prod", "d_alf_prod"],
}
usable = table[(table["year"] <= sm.LAST_BASELINE_YEAR) & table["target"].notna()]
years = sorted(usable["year"].unique())[sm.MIN_FIT_YEARS:]
rows = []
for year in years:
    truth = table[table["year"] == year].set_index("state")
    preds = {"same_as_last_year": sm.predict_silage(usable, year, [])}
    preds.update({n: sm.predict_silage(usable, year, f) for n, f in SETS.items()})
    cap = truth["residual"].where(truth["residual"] > 0)
    for n in ["same_as_last_year", "reversion_only", "rev+planted"]:
        preds[n + "|cap"] = np.minimum(preds[n], cap.reindex(preds[n].index).fillna(np.inf))
    for n, p in preds.items():
        part = pd.DataFrame({"p": p, "a": truth["silage"]}).dropna()
        rows.append({"year": year, "predictor": n, **sm.state_error(part["p"], part["a"])})
res = pd.DataFrame(rows)
pd.set_option("display.width", 250)
out = res.pivot(index="predictor", columns="year", values="state_error_pct")
out["mean"] = out.mean(axis=1)
out["us_abs"] = res.groupby("predictor")["total_error_pct"].apply(lambda s: s.abs().mean())
print(out.sort_values("mean").round(2).to_string())
print(table[table.year.between(2017, 2024)][["d_hay_stocks", "d_hay_prod", "d_alf_prod", "d_milk_price", "residual"]].notna().mean().round(2).to_dict())
