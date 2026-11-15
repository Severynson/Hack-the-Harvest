"""Score a state-year signal (for example Google Trends search interest) against NASS silage acreage changes.

Why: the forums review (README.md beside this file) found no farmer forum that works as an aggregate data
source. The one cheap, public, aggregate proxy left worth testing is state search interest. Before anyone
spends time downloading search data, this script fixes the test in advance, so the result cannot be tuned
after the fact.

Pre-registered test (fixed 2026-11-14, before any search data was seen):
    target   year-on-year change in a state's corn-for-silage harvested acres, log(acres_t / acres_t-1),
             from data/panel/state_year.csv (NASS Quick Stats, built by kernelag.state_panel)
    states   the 20 states with the most silage acres on average over 2017-2024
    years    2017-2024. 2025 is the frozen scoring year and is never read.
    metric   Spearman rank correlation between signal and target after subtracting each year's median from
             both, so a change shared by every state (a drought year, a change in how search data is
             collected) cancels and only the differences between states count
    p-value  two-sided: the share of 5,000 within-year shuffles of the signal across states (seed 0) whose
             |rho| is at least the observed |rho|
    pass     rho > 0 and p < 0.05. Passing only earns the next step: a lower silage error than
             reversion_only in kernelag.state_model's backtest (13.12% mean state error).
Secondary, reported but not used for the pass call: Spearman on the raw values, pooled over all years.

Signal input: a CSV with columns state (full name, any case), year, signal. A missing signal stays NaN and
that state-year is dropped; nothing is imputed. ``--signal builtin:<column>`` scores a panel column instead,
and ``builtin:d_<column>`` its change from the year before (``builtin:d_drought`` is the free baseline).

Google Trends helper: ``--trends-dir`` reads monthly CSVs exported by hand from trends.google.com, one per
state, named <State name>.csv (term "corn silage", region = that state, 2014-01 to 2024-12) and builds:
    anomaly_t = log(mean Aug-Oct interest in year t) - log(mean Aug-Oct interest over years t-3 to t-1)
Google shows too few searches as 0 (or "<1"); those months become NaN. A year needs all three months, and
the reference needs at least two of the three earlier years; otherwise the anomaly is NaN.
Do not pull Trends with scripts: the Explore pages are disallowed to crawlers in trends.google.com/robots.txt.

Output: a JSON summary on stdout; ``--out`` also writes it to a file.

Run: ``.venv/Scripts/python.exe test_models/featureTests/forums/score_state_signal.py --signal builtin:d_drought``
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[3]
PANEL = ROOT / "data" / "panel" / "state_year.csv"
YEARS = list(range(2017, 2025))       # never 2025: that score is frozen
TOP_N = 20
N_PERM = 5000
SEED = 0
HARVEST_MONTHS = (8, 9, 10)           # August to October: chopping season in most silage states
MIN_REFERENCE_YEARS = 2
MONTH_ROW = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?$")


def load_target(panel_path: Path = PANEL, years: list[int] = YEARS, top_n: int = TOP_N) -> pd.DataFrame:
    """Year-on-year log change in silage acres for the largest silage states (state, year, target, silage)."""
    panel = pd.read_csv(panel_path)
    panel = panel[panel["year"] <= max(years)].sort_values(["state", "year"]).copy()
    panel["state"] = panel["state"].str.upper()
    # A change needs both years; a zero or missing year stays NaN rather than becoming a huge jump.
    acres = panel["silage"].where(panel["silage"] > 0)
    previous = acres.groupby(panel["state"]).shift(1)
    previous_year = panel.groupby("state")["year"].shift(1)
    panel["target"] = np.log(acres / previous).where(previous_year == panel["year"] - 1)
    window = panel[panel["year"].isin(years)]
    top = window.groupby("state")["silage"].mean().nlargest(top_n).index
    return window[window["state"].isin(top)][["state", "year", "target", "silage"]].reset_index(drop=True)


def builtin_signal(name: str, panel_path: Path = PANEL) -> pd.DataFrame:
    """A panel column as a signal; a ``d_`` prefix means its change from the previous year."""
    panel = pd.read_csv(panel_path).sort_values(["state", "year"])
    panel["state"] = panel["state"].str.upper()
    column = name[2:] if name.startswith("d_") and name not in panel.columns else name
    if column not in panel.columns:
        raise SystemExit(f"panel has no column {column!r}")
    values = pd.to_numeric(panel[column], errors="coerce")
    if column != name:
        previous_year = panel.groupby("state")["year"].shift(1)
        values = (values - values.groupby(panel["state"]).shift(1)).where(previous_year == panel["year"] - 1)
    return pd.DataFrame({"state": panel["state"], "year": panel["year"], "signal": values})


def read_trends_csv(path: Path) -> pd.Series:
    """Monthly interest from one hand-exported Google Trends CSV; too-few-searches months become NaN."""
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        cells = [cell.strip().strip('"') for cell in line.split(",")]
        match = MONTH_ROW.match(cells[0]) if len(cells) >= 2 else None
        if not match:
            continue                      # header lines ("Category: ...", "Month,corn silage: (...)")
        raw = cells[1].replace("<1", "0")
        value = pd.to_numeric(raw, errors="coerce")
        rows.append((int(match.group(1)), int(match.group(2)), value))
    if not rows:
        raise ValueError(f"{path} holds no dated rows")
    frame = pd.DataFrame(rows, columns=["year", "month", "value"])
    # Weekly exports are averaged to months; Google reports low volume as 0, which is missing, not "no interest".
    frame["value"] = frame["value"].where(frame["value"] > 0)
    monthly = frame.groupby(["year", "month"])["value"].mean()
    return monthly


def trends_anomaly(monthly: pd.Series) -> pd.Series:
    """Pre-registered Aug-Oct anomaly per year: log(this year) - log(mean of the three years before)."""
    season = monthly[monthly.index.get_level_values("month").isin(HARVEST_MONTHS)]
    counts = season.groupby(level="year").count()
    level = season.groupby(level="year").mean().where(counts == len(HARVEST_MONTHS))
    anomaly = {}
    for year in level.index:
        reference = level.reindex([year - 3, year - 2, year - 1])
        if pd.isna(level[year]) or reference.notna().sum() < MIN_REFERENCE_YEARS:
            anomaly[year] = np.nan
        else:
            anomaly[year] = float(np.log(level[year]) - np.log(reference.mean()))
    return pd.Series(anomaly, name="signal", dtype=float)


def trends_signal(folder: Path) -> pd.DataFrame:
    """One anomaly row per state-year from a folder of <State>.csv Trends exports."""
    frames = []
    for path in sorted(folder.glob("*.csv")):
        anomaly = trends_anomaly(read_trends_csv(path))
        frames.append(pd.DataFrame({"state": path.stem.upper(), "year": anomaly.index, "signal": anomaly.values}))
    if not frames:
        raise SystemExit(f"no Trends CSVs in {folder}")
    return pd.concat(frames, ignore_index=True)


def score(signal: pd.DataFrame, target: pd.DataFrame, n_perm: int = N_PERM, seed: int = SEED) -> dict:
    """Pre-registered metric: Spearman on year-demeaned values with a within-year permutation p-value."""
    signal = signal.assign(state=signal["state"].str.upper())
    rows = target.merge(signal[["state", "year", "signal"]], on=["state", "year"], how="inner")
    rows = rows.dropna(subset=["target", "signal"])
    # Year medians come from the rows actually scored, so both series are centred on the same states;
    # a year with fewer than three scored states has no meaningful median and is dropped.
    rows = rows.groupby("year").filter(lambda group: len(group) >= 3)
    result = {"n_state_years": len(rows), "n_states": int(rows["state"].nunique()),
              "years": sorted(int(year) for year in rows["year"].unique())}
    if len(rows) < 10:
        return {**result, "rho": None, "p_value": None, "pass": False,
                "note": "fewer than 10 scored state-years: UNCOMPUTED"}
    centred_target = rows["target"] - rows.groupby("year")["target"].transform("median")
    centred_signal = rows["signal"] - rows.groupby("year")["signal"].transform("median")
    target_rank = rankdata(centred_target)
    signal_rank = rankdata(centred_signal)
    rho = float(np.corrcoef(signal_rank, target_rank)[0, 1])
    # Shuffling the signal inside each year keeps every year's mix of states and only breaks the pairing.
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(rows["year"].to_numpy() == year) for year in result["years"]]
    extreme = 0
    for _ in range(n_perm):
        order = np.arange(len(rows))
        for index in groups:
            order[index] = rng.permutation(index)
        if abs(np.corrcoef(signal_rank[order], target_rank)[0, 1]) >= abs(rho) - 1e-12:
            extreme += 1
    p_value = (extreme + 1) / (n_perm + 1)
    raw = spearmanr(rows["signal"], rows["target"])
    return {**result, "rho": round(rho, 4), "p_value": round(float(p_value), 4),
            "pass": bool(rho > 0 and p_value < 0.05),
            "secondary_raw_pooled_rho": round(float(raw.statistic), 4),
            "secondary_raw_pooled_p": round(float(raw.pvalue), 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--signal", help="CSV with state, year, signal; or builtin:<panel column> / builtin:d_<col>")
    source.add_argument("--trends-dir", type=Path, help="folder of hand-exported Google Trends CSVs, <State>.csv")
    parser.add_argument("--panel", type=Path, default=PANEL)
    parser.add_argument("--out", type=Path, help="also write the JSON summary here")
    args = parser.parse_args()

    if args.trends_dir is not None:
        signal, label = trends_signal(args.trends_dir), f"trends:{args.trends_dir}"
    elif args.signal.startswith("builtin:"):
        signal, label = builtin_signal(args.signal.split(":", 1)[1], args.panel), args.signal
    else:
        signal, label = pd.read_csv(args.signal), args.signal
    summary = {"signal": label, "target": "log change in NASS silage acres, top 20 states, 2017-2024",
               **score(signal, load_target(args.panel))}
    text = json.dumps(summary, indent=1)
    print(text)
    if args.out is not None:
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
