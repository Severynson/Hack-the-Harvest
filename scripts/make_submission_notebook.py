"""Write jupyter/workspace/Kernel_Submission/kernel_deliverable.ipynb (run by scripts/build_submission.sh).

Every number the notebook shows is computed when it runs, from the files in the submission folder.
"""

from pathlib import Path

import nbformat as nbf

OUT = Path(__file__).resolve().parents[1] / "jupyter" / "workspace" / "Kernel_Submission" / "kernel_deliverable.ipynb"

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    md("""# Kernel: corn for grain and corn for silage, by state and for the US

**What USDA asked for:** two numbers, acres of corn harvested for grain and acres harvested for silage, for
each state and the US, before NASS's January report. This notebook makes the 2026 numbers from data public
by mid-November 2026, then shows how the same method did against NASS's final acres in 2017–2025.

**Runs offline in about a minute.** Inputs are in `data/` here (NASS Quick Stats extracts) plus the
organizer file `../02_QuickStats/corn_grain_silage_acres_2012_2025.csv`. Code is the `kernelag` package
here; full project: the team repository (`kernelag/deliverable.py`, `kernelag/silage_level.py`,
`kernelag/state_model.py`)."""),
    md("""## Method

**Silage** (NASS publishes no in-season figure, so this is our own estimate):

* *Smoothed state level.* Most of a state's yearly swing in silage acres reverses the next year (section 3
  measures it). So next year's normal acres are a smoothed level (exponential smoothing in logs), not last
  year's figure.
* *Drought chopping.* When NASS's November yield forecast falls more than 10% below the state's 10-year
  trend, farmers chop grain corn for silage: `chopped = γ × max(0, shortfall − 0.10) × grain acres`.
* Two parameters (smoothing weight α, chopping rate γ), chosen for each year **on earlier years only**.

**Grain:** NASS's own November harvested-for-grain forecast where it publishes one, so **grain accuracy is
NASS's, not ours**. We also score a grain number of our own that does not use that forecast: in-season
planted acres × last year's grain share.

**Intervals:** quantiles of the backtest's own errors, pooled within three state size classes."""),
    code("""import os, sys
from pathlib import Path

HERE = Path.cwd()
sys.path.insert(0, str(HERE))                                  # the kernelag package next to this notebook
os.environ.setdefault("KERNEL_DATA_DIR", str(HERE / "data"))
if (HERE.parent / "02_QuickStats").is_dir():                   # organizer kit = the workspace root
    os.environ.setdefault("KERNEL_KIT_DIR", str(HERE.parent))

import warnings
import numpy as np
import pandas as pd
from kernelag import deliverable

warnings.filterwarnings("ignore")
np.seterr(all="ignore")
pd.set_option("display.width", 200)
result = deliverable.run(lean=True)      # writes data/models/deliverable_*.csv and deliverable_summary.json
summary, comparison = result["summary"], result["comparison"]
print("truth check (organizer CSV vs our NASS copy):", summary["truth_check"])"""),
    md("## 1. The 2026 answer"),
    code("""f = result["deliverable"]
us = f[f["state"].str.startswith("US")].iloc[0]
pd.DataFrame({
    "acres (millions)": [us["silage"] / 1e6, us["grain"] / 1e6],
    "80% low": [us["silage_lo80"] / 1e6, us["grain_lo80"] / 1e6],
    "80% high": [us["silage_hi80"] / 1e6, us["grain_hi80"] / 1e6],
    "90% low": [us["silage_lo90"] / 1e6, us["grain_lo90"] / 1e6],
    "90% high": [us["silage_hi90"] / 1e6, us["grain_hi90"] / 1e6],
}, index=["Corn for silage, US 2026", "Corn for grain, US 2026"]).round(2)"""),
    code("""states = f[~f["state"].str.startswith("US")][["state", "silage", "silage_lo80", "silage_hi80",
                                                 "grain", "grain_lo80", "grain_hi80", "grain_method"]]
states.set_index("state").sort_values("silage", ascending=False).head(20)"""),
    md("""## 2. How the method did, 2017–2024 and 2025

Truth is NASS's final survey acres from the organizer CSV. That CSV has no state survey rows for the
Census years 2017 and 2022; those two years come from our NASS Quick Stats copy (`truth_source`).

* **State error** = Σ |forecast − actual| over all state-years ÷ Σ actual acres (acreage-weighted, pooled).
* **US error** = Σ over years |US forecast − US actual| ÷ Σ US actual (each year's US total, pooled).

2017–2024 also chose the method, so it is validation, not a clean test. 2025 was scored once, after the
method was fixed."""),
    code("""def pooled(series, years, column="predicted"):
    rows = comparison[(comparison["series"] == series) & comparison["year"].isin(years)].dropna(subset=["last"])
    st, us = rows[~rows["state"].str.startswith("US")], rows[rows["state"].str.startswith("US")]
    err = lambda p, a: 100 * (p - a).abs().sum() / a.sum()
    return {"state-years": len(st), "state error %": err(st[column], st["actual"]),
            "US years": len(us), "US error %": err(us[column], us["actual"])}

table = {}
for label, years in [("2017–2024", range(2017, 2025)), ("2025 held out", [2025])]:
    table[("Silage, Kernel", label)] = pooled("silage", years)
    table[("Silage, last year's acres", label)] = pooled("silage", years, "last")
    table[("Grain, delivered (= NASS Nov forecast)", label)] = pooled("grain", years)
    table[("Grain, ours without NASS forecast", label)] = pooled("grain_without_nass_forecast", years)
    table[("Grain, last year's acres", label)] = pooled("grain", years, "last")
pd.DataFrame(table).T.round(2)"""),
    code("""by_year = pd.DataFrame({
    (s, k): {y: v[k] for y, v in summary[s]["by_year"].items()}
    for s in ["silage", "grain", "grain_without_nass_forecast"]
    for k in ["state_wape_pct", "us_error_pct", "last_year_state_wape_pct", "last_year_us_error_pct"]})
by_year.index.name = "year"
by_year["silage"]"""),
    md("""## 3. What limits accuracy

Measured in the repository's `test_models/accuracy/noise_floor.py` (NASS state survey 2000–2024; 2025 not
read) and copied here as `data/noise_floor_results.json`; the rest is computed from the comparison above."""),
    code("""import json
nf = json.loads((HERE / "data" / "noise_floor_results.json").read_text())
d, cg = nf["decomposition"], nf["census_vs_survey"]
rows = comparison[(comparison["series"] == "silage") & comparison["year"].between(2017, 2024)
                  & ~comparison["state"].str.startswith("US")].copy()
size = rows.groupby("state")["last"].mean()
third = pd.qcut(size.rank(method="first"), 3, labels=["smallest", "middle", "largest"])
rows["third"] = rows["state"].map(third)
points = (rows["predicted"] - rows["actual"]).abs().groupby(rows["third"], observed=True).sum() / rows["actual"].sum() * 100
g = pooled("grain", range(2017, 2025))["state error %"]
own = pooled("grain_without_nass_forecast", range(2017, 2025))["state error %"]
print(f\"Lag-1 autocorrelation of a state's own silage change: {d['state_change_lag1_autocorr']:.2f} (pure noise -0.5)\")
print(f\"Implied state error from that noise alone: about {d['noise_floor_state_wape_pct']:.1f}%\")
print(f\"Share of yearly change common to all states: {d['national_share_of_change_variance']:.2f}\")
print(f\"NASS survey vs Census, state gap: 2017 {cg['2017']['state_gap_pct']}%, 2022 {cg['2022']['state_gap_pct']}%\")
print("Silage error points by state size third, 2017-2024:", points.round(2).to_dict())
print(f"Grain: our own number is {own - g:.2f} points of state error behind NASS's forecast")"""),
    md("""* **Silage state error is mostly noise in NASS's own state series**, and it sits in the big dairy
  states. Every model the team tried (ridge, LAD, Huber, gradient boosting, ensembles) lands near the same
  level; only new data on those states (e.g. a calibrated satellite signal) could move it.
* **The US silage total is where the model helps:** drought chopping turns a national weather shock into acres.
* **Grain** is NASS's November forecast; our own number is close behind it.
* **Satellite classifier** (separate work in the repository): it separates silage from grain fields on the
  Maryland research farm, but its year-to-year drift is too large to move state acreage yet, so it is not
  used in these numbers.
* All replays use current-vintage NASS data, not the figures as published each November."""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3",
                                                               "language": "python"}})
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print(f"wrote {OUT}")
