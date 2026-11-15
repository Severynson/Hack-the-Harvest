"""Own corn-for-grain harvested acres by state, with no current-year NASS input (Tier A), against NASS's forecast.

The pre-registration, method and results are in README.md next to this file. In short: FSA crop acreage
files (farmers' certifications to the Farm Service Agency, published monthly from August) are scaled to NASS
by last year's ratio of NASS final grain acres to FSA grain-intended acres. Optional stress correction from
the Drought Monitor and RMA crop-insurance losses. Every forecast uses only files published by its as-of date.

Inputs (read only):
    data/fsa/fsa_files.csv, data/fsa/fsa_corn_state.csv           FSA panel (kernelag.fsa), as-of helpers
    data/nass/corn_acres_state.csv                                 NASS finals (truth, 2013-2025) and in-season
                                                                   figures (benchmark only)
    data/Quick Stats Data/corn_grain_harvested_acres_state_2000_2026.csv, corn_planted_acres_state_2000_2026.csv
                                                                   NASS finals before 2013; 2012 benchmark
    data/drought/usdm_state_weekly_2000_2026.csv                   Drought Monitor (kernelag.context.drought)
    data/rma/cause_of_loss_corn/, data/rma/insured_by_type_corn/   RMA (kernelag.context.loss_share)
    test_models/danielModel/out/gbt_backtest_by_year.csv           audited, quoted only
Outputs (out/): backtest_by_state_year.csv, by_year.csv, summary.csv, comparisons.csv, selection.json,
    reproduction.json, inputs_audit.json, fsa_files_used.csv, g4_weights.csv, error_by_coverage.csv,
    forecast_2026.csv, daniel_gbt_audit.json; with --score-2025 once: score_2025_information_only.json/.csv

Run from the repository root:
    .venv/Scripts/python.exe test_models/ownModels/grain/run.py
    .venv/Scripts/python.exe test_models/ownModels/grain/run.py --score-2025
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from kernelag import fsa as kfsa
from kernelag.context import drought as usdm_drought
from kernelag.context import loss_share as rma_loss_share

OUT = HERE / "out"
DATA = REPO / "data"
QUICKSTATS = DATA / "Quickstats Data"
QS_GRAIN = QUICKSTATS / "corn_grain_harvested_acres_state_2000_2026.csv"
QS_PLANTED = QUICKSTATS / "corn_planted_acres_state_2000_2026.csv"
NASS_TABLE = DATA / "nass" / "corn_acres_state.csv"
DANIEL_GBT = REPO / "test_models" / "danielModel" / "out" / "gbt_backtest_by_year.csv"

LAST_TRUTH_YEAR = 2025          # NASS finals exist up to here; Quick Stats "YEAR" rows for 2026 are provisional
INCUMBENT_FIRST_YEAR = 2013     # first year in data/nass/corn_acres_state.csv
SCORING_YEAR = 2025
FORECAST_YEAR = 2026
FIRST_TEST, LAST_TEST = 2012, 2024
FIRST_TRAIN = 2012              # g4 training rows start here (earliest year with a dated t-1 FSA final file)
PERIODS = {"2012-2024": (2012, 2024), "2017-2024": (2017, 2024)}
PRIMARY = "2012-2024"
ASOF = {"nov": (11, 15), "oct": (10, 15), "sep": (9, 15)}
HEADLINE_ASOF = "nov"
GUARD = (0.25, 4.0)
RIDGE_PENALTY = 1.0
MIN_FIT_YEARS = 3
STRESS_FEATURES = ["d_drought", "d_loss"]
BOOT = 10_000
SEED = 20261114
Z80 = 1.2816
SIZE_CLASSES = 3

# --- independence tiers -----------------------------------------------------------------------------------------

TIER_RANK = {"A": 0, "B": 1, "X": 2}
TIER_NAME = {"A": "A (independent)", "B": "B (adds NASS condition/progress)", "X": "not independent"}
SOURCES = {
    "nass_final_prior_years": ("A", "NASS final state grain acres of years before t (history anchor)"),
    "fsa_files_published_by_asof": ("A", "FSA crop acreage files published on or before the as-of date"),
    "usdm_drought": ("A", "US Drought Monitor weekly state maps dated on or before the as-of date"),
    "rma_cause_of_loss": ("A", "RMA cause-of-loss acres, months before the as-of month (today's vintage)"),
    "rma_insured_acres": ("A", "RMA insured corn acres (today's vintage)"),
    "noaa_weather": ("A", "NOAA county weather (not used by any candidate here)"),
    "nass_crop_condition_progress": ("B", "NASS weekly crop condition and progress of year t"),
    "nass_current_year_planted": ("X", "NASS March/June/in-season planted acres of year t"),
    "nass_current_year_grain_forecast": ("X", "NASS in-season harvested-for-grain forecast of year t"),
    "nass_current_year_yield_forecast": ("X", "NASS in-season grain yield forecast of year t"),
}
FSA_SOURCES = ["nass_final_prior_years", "fsa_files_published_by_asof"]
CANDIDATES = {
    "g0_persistence": {"role": "benchmark", "sources": ["nass_final_prior_years"]},
    "g1_fsa_ratio": {"role": "own", "sources": FSA_SOURCES},
    "g2_fsa_planted_share": {"role": "own", "sources": FSA_SOURCES},
    "g3_fsa_ratio_multi": {"role": "own", "sources": FSA_SOURCES},
    "g4_fsa_plus_stress": {"role": "own", "sources": [*FSA_SOURCES, "usdm_drought", "rma_cause_of_loss",
                                                       "rma_insured_acres"]},
    "g5_fsa_ratio_vintage": {"role": "own", "sources": FSA_SOURCES},
    "nass_latest": {"role": "benchmark", "sources": ["nass_final_prior_years", "nass_current_year_planted",
                                                  "nass_current_year_grain_forecast"]},
}
OWN = [name for name, spec in CANDIDATES.items() if spec["role"] == "own"]
SIMPLEST = "g1_fsa_ratio"


def tier_of(name: str, candidates: dict = CANDIDATES) -> str:
    """The highest tier among a candidate's declared sources."""
    tiers = [SOURCES[source][0] for source in candidates[name]["sources"]]
    return max(tiers, key=TIER_RANK.__getitem__)


def check_tiers(candidates: dict = CANDIDATES) -> None:
    """Refuse any own candidate that declares an input above Tier A."""
    for name, spec in candidates.items():
        unknown = set(spec["sources"]) - set(SOURCES)
        if unknown:
            raise ValueError(f"{name}: undeclared sources {sorted(unknown)}")
        if spec["role"] == "own" and tier_of(name, candidates) != "A":
            bad = [s for s in spec["sources"] if SOURCES[s][0] != "A"]
            raise ValueError(f"{name} is an own (Tier A) candidate but uses {bad}")


check_tiers()


# --- NASS: finals (history and truth) ---------------------------------------------------------------------------

def _quickstats(path: Path, short_desc: str) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = raw[(raw["source_desc"] == "SURVEY") & (raw["domain_desc"] == "TOTAL") & (raw["short_desc"] == short_desc)
               & (raw["state_name"] != "OTHER STATES")]
    return pd.DataFrame({
        "year": rows["year"].astype(int), "state": rows["state_name"], "period": rows["reference_period_desc"],
        "value": pd.to_numeric(rows["Value"].str.replace(",", "").str.strip(), errors="coerce"),
    }).dropna(subset=["value"])


def load_finals() -> pd.DataFrame:
    """NASS final grain and planted acres by state and year (2000-2025): year, state, grain, planted.

    2013-2025 are the incumbent's own values (data/nass/corn_acres_state.csv); earlier years come from the team's
    Quick Stats files, after checking that those equal the incumbent's table wherever both exist.
    """
    incumbent = pd.read_csv(NASS_TABLE)
    incumbent = incumbent[incumbent["period"] == "final"].pivot_table(
        index=["year", "state"], columns="series", values="acres", aggfunc="first")[["grain", "planted"]]
    qs = {}
    for series, path, item in [("grain", QS_GRAIN, "CORN, GRAIN - ACRES HARVESTED"),
                               ("planted", QS_PLANTED, "CORN - ACRES PLANTED")]:
        rows = _quickstats(path, item)
        rows = rows[(rows["period"] == "YEAR") & (rows["year"] <= LAST_TRUTH_YEAR)]
        qs[series] = rows.drop_duplicates(["year", "state"]).set_index(["year", "state"])["value"]
    qs = pd.DataFrame(qs)
    both = incumbent.merge(qs, left_index=True, right_index=True, how="inner", suffixes=("", "_qs"))
    for series in ["grain", "planted"]:
        have = both.dropna(subset=[series, f"{series}_qs"])
        if not np.allclose(have[series], have[f"{series}_qs"]):
            raise ValueError(f"Quick Stats {series} finals differ from data/nass/corn_acres_state.csv")
    grain_states_inc = set(incumbent["grain"].dropna().index.get_level_values("state"))
    grain_states_qs = set(qs["grain"].dropna().index.get_level_values("state"))
    if grain_states_inc != grain_states_qs:
        raise ValueError("grain state sets differ between Quick Stats and the incumbent's table")
    early = qs[qs.index.get_level_values("year") < INCUMBENT_FIRST_YEAR]
    finals = pd.concat([early, incumbent]).reset_index()
    return finals.sort_values(["year", "state"]).reset_index(drop=True)


class NassHistory:
    """NASS finals visible to a forecast of ``target_year``: years before it only."""

    def __init__(self, finals: pd.DataFrame, target_year: int):
        self.target_year = target_year
        self._finals = finals[finals["year"] < target_year]

    def grain(self, year: int) -> pd.Series:
        if year >= self.target_year:
            raise PermissionError(f"NASS {year} is not history for a {self.target_year} forecast")
        rows = self._finals[(self._finals["year"] == year)].dropna(subset=["grain"])
        return rows.set_index("state")["grain"]


def truth(finals: pd.DataFrame, year: int) -> pd.Series:
    """NASS final grain acres of ``year`` by state (scoring only)."""
    rows = finals[finals["year"] == year].dropna(subset=["grain"])
    return rows.set_index("state")["grain"]


# --- FSA view under the as-of rule ------------------------------------------------------------------------------

def asof_date(year: int, key: str) -> date:
    month, day = ASOF[key]
    return date(year, month, day)


def load_fsa() -> tuple[pd.DataFrame, pd.DataFrame]:
    files = pd.read_csv(DATA / "fsa" / "fsa_files.csv")
    state = pd.read_csv(DATA / "fsa" / "fsa_corn_state.csv", dtype={"state_fips": str})
    ok = files[files["status"] == "ok"]
    if ok.dropna(subset=["data_as_of"]).duplicated(["crop_year", "data_as_of"]).any():
        raise ValueError("two parsed FSA files share a crop year and data date")
    return files, state


def _one_year_back(day: date) -> date:
    try:
        return day.replace(year=day.year - 1)
    except ValueError:               # 29 February
        return day.replace(year=day.year - 1, day=28)


class FsaView:
    """The FSA files a forecast made on ``asof`` for ``crop_year`` may use (``kernelag.fsa.usable_files``)."""

    def __init__(self, files: pd.DataFrame, state: pd.DataFrame, asof: date, crop_year: int):
        self.asof, self.crop_year = asof, crop_year
        self.usable = kfsa.usable_files(files, asof, crop_year)
        self._state = state
        self._files = files

    def current(self) -> pd.Series | None:
        """Newest in-season file of the crop year published by the as-of date (a missing month is never filled
        by a later file)."""
        return kfsa.latest_file(self._files, self.asof, self.crop_year)

    def final(self, crop_year: int) -> pd.Series | None:
        rows = self.usable[(self.usable["crop_year"] == crop_year)
                           & self.usable["vintage"].astype(str).str.startswith("final")]
        return None if rows.empty else rows.sort_values("data_as_of").iloc[-1]

    def closest(self, crop_year: int, target: date) -> pd.Series | None:
        """The usable file of ``crop_year`` whose data date is closest to ``target`` moved back one year."""
        rows = self.usable[self.usable["crop_year"] == crop_year]
        if rows.empty:
            return None
        aim = pd.Timestamp(_one_year_back(target))
        distance = (pd.to_datetime(rows["data_as_of"]) - aim).abs()
        order = pd.DataFrame({"d": distance.to_numpy(), "date": pd.to_datetime(rows["data_as_of"]).to_numpy()})
        best = order.sort_values(["d", "date"], ascending=[True, False]).index[0]
        return rows.iloc[best]

    def acres(self, file: pd.Series | None, measure: str) -> pd.Series:
        """Acres by state in one usable file: "grain" = planted with intended use grain; "all" = planted plus
        failed, every intended use."""
        if file is None:
            return pd.Series(dtype=float)
        if file["zip_name"] not in set(self.usable["zip_name"]):
            raise PermissionError(f"{file['zip_name']} is not usable for a forecast made on {self.asof}")
        rows = self._state[(self._state["crop_year"] == file["crop_year"])
                           & (self._state["data_as_of"] == file["data_as_of"])]
        if measure == "grain":
            rows = rows[rows["intended_use"] == "grain"]
            values = rows["planted_acres"]
        elif measure == "all":
            values = rows["planted_acres"].fillna(0.0) + rows["failed_acres"].fillna(0.0)
        else:
            raise ValueError(measure)
        return values.groupby(rows["state"]).sum()


# --- candidates -------------------------------------------------------------------------------------------------

def guarded(current: pd.Series, multiplier: pd.Series, last: pd.Series) -> pd.DataFrame:
    """current x multiplier where both are sane, else last year's NASS final (the pre-registered guard)."""
    current = current.reindex(last.index)
    multiplier = multiplier.reindex(last.index)
    ok = (current > 0) & multiplier.between(*GUARD)
    pred = np.where(ok, current * multiplier, last)
    return pd.DataFrame({"pred": pred, "method": np.where(ok, "fsa", "fallback_persistence"),
                         "multiplier": multiplier.to_numpy(), "fsa_current": current.to_numpy()}, index=last.index)


def _ratio(nass: pd.Series, fsa: pd.Series) -> pd.Series:
    fsa = fsa.reindex(nass.index)
    return (nass / fsa.where(fsa > 0)).astype(float)


def predict_fsa(name: str, hist: NassHistory, view: FsaView) -> tuple[pd.DataFrame, dict]:
    """One FSA candidate (g1, g2, g3, g5) for every state with a NASS final last year. Returns the table and the
    files used."""
    t = view.crop_year
    last = hist.grain(t - 1)
    cur = view.current()
    used = {"current": None if cur is None else cur["zip_name"], "current_data_as_of": None if cur is None
            else cur["data_as_of"], "reference": None}
    if cur is None:
        return guarded(pd.Series(dtype=float), pd.Series(dtype=float), last), used
    if name == "g1_fsa_ratio":
        ref = view.final(t - 1)
        multiplier = _ratio(last, view.acres(ref, "grain"))
        current = view.acres(cur, "grain")
    elif name == "g2_fsa_planted_share":
        ref = view.final(t - 1)
        multiplier = _ratio(last, view.acres(ref, "all"))
        current = view.acres(cur, "all")
    elif name == "g3_fsa_ratio_multi":
        ratios, refs = [], []
        for k in (1, 2, 3):
            ref_k = view.final(t - k)
            if ref_k is None:
                continue
            nass_k = hist.grain(t - k)
            if nass_k.empty:
                continue
            ratios.append(_ratio(nass_k, view.acres(ref_k, "grain")).reindex(last.index))
            refs.append(ref_k["zip_name"])
        multiplier = pd.concat(ratios, axis=1).median(axis=1, skipna=True) if ratios else pd.Series(dtype=float)
        current = view.acres(cur, "grain")
        ref = None
        used["reference"] = "|".join(refs)
    elif name == "g5_fsa_ratio_vintage":
        ref = view.closest(t - 1, date.fromisoformat(str(cur["data_as_of"])))
        multiplier = _ratio(last, view.acres(ref, "grain"))
        current = view.acres(cur, "grain")
    else:
        raise ValueError(name)
    if ref is not None:
        used["reference"] = ref["zip_name"]
        used["reference_data_as_of"] = ref["data_as_of"]
    return guarded(current, multiplier, last), used


# --- stress features (Tier A: Drought Monitor, RMA) -------------------------------------------------------------

def _read_folder(folder: Path, columns: list[str]) -> pd.DataFrame:
    files = sorted(folder.glob("*.csv*"))
    if not files:
        raise FileNotFoundError(f"no files in {folder}")
    return pd.concat([pd.read_csv(f, usecols=columns, dtype=str) for f in files], ignore_index=True)


def load_stress_sources() -> dict:
    return {
        "usdm": pd.read_csv(DATA / "drought" / "usdm_state_weekly_2000_2026.csv"),
        "loss": _read_folder(DATA / "rma" / "cause_of_loss_corn", [
            "commodity_year", "state_abbreviation", "cause_of_loss_code", "month_of_loss", "net_determined_quantity"]),
        "insured": _read_folder(DATA / "rma" / "insured_by_type_corn", [
            "commodity_year", "state_abbreviation", "reporting_level_type", "net_reporting_level_amount"]),
    }


def stress_features(sources: dict, asof_key: str) -> pd.DataFrame:
    """d_drought and d_loss by state and year: the as-of-year level minus the previous year's (same as-of)."""
    levels = usdm_drought(sources["usdm"], asof_key).merge(
        rma_loss_share(sources["loss"], sources["insured"], asof_key), on=["state", "year"], how="outer")
    previous = levels.assign(year=levels["year"] + 1)
    table = levels.merge(previous, on=["state", "year"], how="left", suffixes=("", "_last"))
    table["d_drought"] = table["drought"] - table["drought_last"]
    table["d_loss"] = table["loss_share"] - table["loss_share_last"]
    return table[["state", "year", *STRESS_FEATURES]]


def fit_ridge(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Weighted ridge on std-scaled features, no centring, no intercept (as kernelag.state_model.fit_ridge).
    Returns (coefficients per scaled feature, scale)."""
    scale = x.std(axis=0)
    scale[scale == 0] = 1.0
    xs = x / scale
    xtw = xs.T * w
    coef = np.linalg.solve(xtw @ xs + RIDGE_PENALTY * w.mean() * np.eye(x.shape[1]), xtw @ y)
    return coef, scale


def g4_predict(g1_rows: pd.DataFrame, stress: pd.DataFrame, finals: pd.DataFrame, t: int) -> tuple[pd.DataFrame, dict]:
    """g1 x exp(b . x), b fitted on state-years before ``t`` (from FIRST_TRAIN) at the same as-of date.

    ``g1_rows``: year, state, pred, method for g1 (all years computed so far, same as-of)."""
    hist = NassHistory(finals, t)
    with_x = g1_rows.merge(stress, on=["state", "year"], how="left")
    with_x[STRESS_FEATURES] = with_x[STRESS_FEATURES].fillna(0.0)
    train = []
    for year in range(FIRST_TRAIN, t):
        rows = with_x[with_x["year"] == year].set_index("state")
        if rows.empty:
            continue
        actual = hist.grain(year).reindex(rows.index)
        weight = hist.grain(year - 1).reindex(rows.index)
        train.append(rows.assign(actual=actual, weight=weight).dropna(subset=["actual", "weight", "pred"]))
    years = sorted({int(y) for part in train for y in part["year"]})
    target = with_x[with_x["year"] == t].set_index("state")
    info = {"year": t, "train_years": f"{years[0]}-{years[-1]}" if years else "", "n_train_years": len(years)}
    if len(years) < MIN_FIT_YEARS:
        info.update({f"b_{f}": 0.0 for f in STRESS_FEATURES})
        return target.assign(pred=target["pred"])[["pred", "method"]], info
    fit = pd.concat(train)
    coef, scale = fit_ridge(fit[STRESS_FEATURES].to_numpy(float), np.log(fit["actual"] / fit["pred"]).to_numpy(),
                            fit["weight"].to_numpy(float))
    change = (target[STRESS_FEATURES].to_numpy(float) / scale) @ coef
    info.update({f"b_{f}": float(c) for f, c in zip(STRESS_FEATURES, coef)})
    info.update({f"scale_{f}": float(s) for f, s in zip(STRESS_FEATURES, scale)})
    return target.assign(pred=target["pred"] * np.exp(change))[["pred", "method"]], info


# --- NASS benchmark (not ours) ----------------------------------------------------------------------------------

QS_PERIOD = {"YEAR - MAR ACREAGE": "mar", "YEAR - JUN ACREAGE": "jun", "YEAR - AUG FORECAST": "aug",
             "YEAR - SEP FORECAST": "sep", "YEAR - OCT FORECAST": "oct", "YEAR - NOV FORECAST": "nov",
             "YEAR - AUG ACREAGE": "aug", "YEAR - SEP ACREAGE": "sep", "YEAR - OCT ACREAGE": "oct"}


def nass_inseason_table() -> pd.DataFrame:
    """NASS in-season rows (series, period) as the incumbent stores them, plus 2012 rebuilt from Quick Stats."""
    acres = pd.read_csv(NASS_TABLE)
    acres = acres[acres["period"] != "final"]
    extra = []
    for series, path, item in [("grain", QS_GRAIN, "CORN, GRAIN - ACRES HARVESTED"),
                               ("planted", QS_PLANTED, "CORN - ACRES PLANTED")]:
        rows = _quickstats(path, item)
        rows = rows[(rows["year"] < INCUMBENT_FIRST_YEAR) & rows["period"].isin(list(QS_PERIOD))]
        part = pd.DataFrame({"year": rows["year"], "state": rows["state"], "series": series,
                             "period": rows["period"].map(QS_PERIOD), "acres": rows["value"]})
        extra.append(part.drop_duplicates(["year", "state", "series", "period"]))
    return pd.concat([acres[["year", "state", "series", "period", "acres"]], *extra], ignore_index=True)


def nass_benchmark(inseason: pd.DataFrame, finals: pd.DataFrame, year: int, asof_key: str) -> pd.Series:
    """The incumbent's ``nass_latest`` rule (kernelag.state_model.predict_grain): NASS's latest grain forecast
    published by the as-of month; else latest planted x last year's grain share of planted; else last year."""
    from kernelag.state_panel import (
        GRAIN_ASOF,
        PLANTED_ASOF,
        latest_available,
        public_by,
    )
    rows = inseason[inseason["year"] == year].rename(columns={"acres": "value"})
    grain_asof = latest_available(rows[rows["series"] == "grain"], public_by(GRAIN_ASOF, asof_key))
    planted_asof = latest_available(rows[rows["series"] == "planted"], public_by(PLANTED_ASOF, asof_key))
    grain_asof = grain_asof.droplevel("year") if len(grain_asof) else pd.Series(dtype=float)
    planted_asof = planted_asof.droplevel("year") if len(planted_asof) else pd.Series(dtype=float)
    last = finals[finals["year"] == year - 1].set_index("state")
    states = last["grain"].dropna().index
    by_share = planted_asof.reindex(states) * last["grain"].reindex(states) / last["planted"].reindex(states)
    return grain_asof.reindex(states).fillna(by_share).fillna(last["grain"].reindex(states))


def incumbent_benchmark_check(inseason: pd.DataFrame, finals: pd.DataFrame, asof_key: str) -> dict:
    """Compare the rebuilt benchmark with the incumbent's own predict_grain wherever the incumbent is complete."""
    from kernelag.state_model import add_changes, predict_grain
    from kernelag.state_panel import load_panel
    table = add_changes(load_panel(asof_key))
    worst, years = 0.0, []
    for year in range(INCUMBENT_FIRST_YEAR + 1, LAST_TEST + 1):
        theirs = predict_grain(table, year)["grain"]
        mine = nass_benchmark(inseason, finals, year, asof_key).reindex(theirs.index)
        worst = max(worst, float((mine - theirs).abs().max()))
        years.append(year)
    return {"asof": asof_key, "years_compared": f"{years[0]}-{years[-1]}", "max_abs_difference_acres": worst}


# --- backtest ---------------------------------------------------------------------------------------------------

def predict_all(finals: pd.DataFrame, files: pd.DataFrame, state: pd.DataFrame, stress: pd.DataFrame,
                inseason: pd.DataFrame, years: list[int], asof_key: str) -> tuple[pd.DataFrame, list, list]:
    """Every candidate's prediction for every year in ``years`` at one as-of date."""
    parts, used_rows, g4_info = [], [], []
    g1_all = []
    for t in years:
        hist = NassHistory(finals, t)
        view = FsaView(files, state, asof_date(t, asof_key), t)
        last = hist.grain(t - 1)
        parts.append(pd.DataFrame({"state": last.index, "pred": last.to_numpy(), "method": "persistence",
                                   "candidate": "g0_persistence", "year": t}))
        for name in ["g1_fsa_ratio", "g2_fsa_planted_share", "g3_fsa_ratio_multi", "g5_fsa_ratio_vintage"]:
            table, used = predict_fsa(name, hist, view)
            table = table.rename_axis("state").reset_index().assign(candidate=name, year=t)
            parts.append(table)
            used_rows.append({"year": t, "asof": asof_key, "candidate": name, **used,
                              "n_fallback": int((table["method"] != "fsa").sum())})
            if name == "g1_fsa_ratio":
                g1_all.append(table[["year", "state", "pred", "method"]])
        g4, info = g4_predict(pd.concat(g1_all, ignore_index=True), stress, finals, t)
        parts.append(g4.rename_axis("state").reset_index().assign(candidate="g4_fsa_plus_stress", year=t))
        g4_info.append({"asof": asof_key, **info})
        if t <= LAST_TRUTH_YEAR:
            bench = nass_benchmark(inseason, finals, t, asof_key)
            parts.append(pd.DataFrame({"state": bench.index, "pred": bench.to_numpy(), "method": "nass",
                                       "candidate": "nass_latest", "year": t}))
    out = pd.concat(parts, ignore_index=True)
    out["asof"] = asof_key
    out["tier"] = out["candidate"].map(lambda n: TIER_NAME[tier_of(n)])
    return out, used_rows, g4_info


def score_years(predictions: pd.DataFrame, finals: pd.DataFrame) -> pd.DataFrame:
    """State WAPE and US error per candidate, as-of date and year (percent)."""
    rows = []
    for (candidate, asof_key, year), group in predictions.groupby(["candidate", "asof", "year"], sort=False):
        actual = truth(finals, year)
        pred = group.set_index("state")["pred"].reindex(actual.index)
        if pred.isna().any():
            raise ValueError(f"{candidate} {year} {asof_key}: no prediction for {list(pred[pred.isna()].index)}")
        miss = pred - actual
        rows.append({"candidate": candidate, "asof": asof_key, "year": int(year), "n_states": len(actual),
                     "state_wape_pct": 100 * miss.abs().sum() / actual.sum(),
                     "us_error_pct": 100 * miss.sum() / actual.sum()})
    return pd.DataFrame(rows)


def summarise(by_year: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, (first, last) in PERIODS.items():
        part = by_year[by_year["year"].between(first, last)]
        for (candidate, asof_key), group in part.groupby(["candidate", "asof"], sort=False):
            rows.append({"candidate": candidate, "asof": asof_key, "period": period,
                         "tier": TIER_NAME[tier_of(candidate)], "role": CANDIDATES[candidate]["role"],
                         "n_years": len(group), "n_states": int(group["n_states"].iloc[0]),
                         "mean_state_wape_pct": group["state_wape_pct"].mean(),
                         "mean_abs_us_error_pct": group["us_error_pct"].abs().mean(),
                         "mean_signed_us_error_pct": group["us_error_pct"].mean(),
                         "worst_year_state_wape_pct": group["state_wape_pct"].max()})
    return pd.DataFrame(rows)


def paired_ci(diffs: np.ndarray, boot: int = BOOT, seed: int = SEED) -> tuple[float, float, float]:
    """Mean of paired yearly differences and its 90% bootstrap interval (resampling years)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diffs), size=(boot, len(diffs)))
    means = diffs[idx].mean(axis=1)
    return float(diffs.mean()), float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95))


def comparisons(by_year: pd.DataFrame, boot: int) -> pd.DataFrame:
    rows = []
    references = ["nass_latest", "g0_persistence", SIMPLEST]
    for period, (first, last) in PERIODS.items():
        part = by_year[by_year["year"].between(first, last)]
        for asof_key in part["asof"].unique():
            here = part[part["asof"] == asof_key]
            wape = here.pivot(index="year", columns="candidate", values="state_wape_pct")
            us = here.pivot(index="year", columns="candidate", values="us_error_pct").abs()
            for candidate in [*OWN, "g0_persistence"]:
                for reference in references:
                    if candidate == reference or reference not in wape:
                        continue
                    for metric, table in [("state_wape_pct", wape), ("abs_us_error_pct", us)]:
                        d = (table[candidate] - table[reference]).dropna().to_numpy()
                        mean, lo, hi = paired_ci(d, boot)
                        rows.append({"candidate": candidate, "reference": reference, "asof": asof_key,
                                     "period": period, "metric": metric, "n_years": len(d),
                                     "mean_diff_pts": mean, "ci90_lo": lo, "ci90_hi": hi,
                                     "years_candidate_better": int((d < 0).sum())})
    return pd.DataFrame(rows)


def select(by_year: pd.DataFrame, asof_key: str) -> dict:
    """The pre-registered rule: best eligible mean state WAPE, kept only if it beats g1 by more than 2 SE."""
    first, last = PERIODS[PRIMARY]
    part = by_year[(by_year["asof"] == asof_key) & by_year["year"].between(first, last)]
    wape = part.pivot(index="year", columns="candidate", values="state_wape_pct")[OWN]
    means = wape.mean()
    best = str(means.idxmin())
    result = {"asof": asof_key, "period": PRIMARY, "n_years": len(wape),
              "mean_state_wape_pct": {k: round(float(v), 4) for k, v in means.items()}, "best": best,
              "simplest": SIMPLEST}
    if best == SIMPLEST:
        result.update({"selected": SIMPLEST, "reason": "the best candidate is the simplest one"})
        return result
    d = (wape[SIMPLEST] - wape[best]).to_numpy()
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    result.update({"mean_gain_vs_simplest_pts": float(d.mean()), "se_pts": se, "two_se_pts": 2 * se})
    if d.mean() > 2 * se:
        result.update({"selected": best, "reason": "beats the simplest candidate by more than 2 SE"})
    else:
        result.update({"selected": SIMPLEST, "reason": f"{best} is not better than {SIMPLEST} by more than 2 SE"})
    return result


# --- intervals --------------------------------------------------------------------------------------------------

def attach_last(rows: pd.DataFrame, finals: pd.DataFrame) -> pd.DataFrame:
    last = finals[["year", "state", "grain"]].assign(year=finals["year"] + 1).rename(columns={"grain": "last"})
    return rows.merge(last, on=["year", "state"], how="left")


def error_model(rows: pd.DataFrame) -> dict:
    """Size-class edges (tertiles of last year's acres) and the 10% / 90% quantiles of log(actual / pred)."""
    edges = np.quantile(rows["last"], np.linspace(0, 1, SIZE_CLASSES + 1)[1:-1])
    size = np.searchsorted(edges, rows["last"].to_numpy())
    log_error = np.log(rows["actual"] / rows["pred"]).to_numpy()
    return {"edges": edges, "q": {c: np.quantile(log_error[size == c], [0.10, 0.90]) for c in range(SIZE_CLASSES)}}


def bounds(pred: np.ndarray, last: np.ndarray, model: dict) -> tuple[np.ndarray, np.ndarray]:
    size = np.searchsorted(model["edges"], last)
    lo = np.array([model["q"][c][0] for c in size])
    hi = np.array([model["q"][c][1] for c in size])
    return pred * np.exp(lo), pred * np.exp(hi)


def coverage_loyo(rows: pd.DataFrame) -> float:
    inside = []
    for year in rows["year"].unique():
        model = error_model(rows[rows["year"] != year])
        test = rows[rows["year"] == year]
        lo, hi = bounds(test["pred"].to_numpy(), test["last"].to_numpy(), model)
        inside.extend((test["actual"].to_numpy() >= lo) & (test["actual"].to_numpy() <= hi))
    return float(np.mean(inside))


def us_rms(rows: pd.DataFrame) -> float:
    totals = rows.groupby("year")[["actual", "pred"]].sum()
    return float(np.sqrt((np.log(totals["actual"] / totals["pred"]) ** 2).mean()))


# --- Daniel's GBT audit -----------------------------------------------------------------------------------------

def daniel_audit() -> dict:
    audit = {
        "model": "grain_gbt_independent (test_models/danielModel/train_gbt.py)",
        "verdict": "not independent (uses NASS current-year planted acres and NASS current-year yield forecasts); "
                   "also uses NASS crop condition and progress",
        "inputs_used": {
            "starting value 'last'": "planted_asof x grain(t-1) / planted(t-1): planted_asof is NASS's latest "
                                     "in-season planted acres (June Acreage or later); for years before 2018 "
                                     "build_panel.py fills it with NASS's FINAL planted acres (stand_in=True): "
                                     "current-year NASS and a look-ahead",
            "d_planted": "log(planted_asof / planted(t-1)): NASS current-year planted acres",
            "yield_shock": "log(yield_asof / mean yield of 3 earlier years): NASS Aug-Nov grain yield forecast",
            "d_poor, poor": "cond_poor: NASS weekly crop condition (Tier B source)",
            "late_plant": "planted_may20: NASS weekly crop progress (Tier B source)",
            "d_mature": "mature_sep22: NASS weekly crop progress (Tier B source)",
            "d_drought, drought": "drought_d2: US Drought Monitor (Tier A)",
            "d_rain, d_gdd, early_freeze": "NOAA weather (Tier A)",
            "share_last": "silage(t-1) / planted(t-1): NASS finals of t-1 (Tier A history)",
        },
        "tier": "not independent",
    }
    if DANIEL_GBT.exists():
        rows = pd.read_csv(DANIEL_GBT)
        rows = rows[rows["candidate"] == "grain_gbt_independent"]
        audit["reported_backtest"] = {
            "source": str(DANIEL_GBT.relative_to(REPO)).replace("\\", "/"),
            "years": f"{int(rows['year'].min())}-{int(rows['year'].max())}",
            "mean_state_wape_pct": round(float(rows["state_error_pct"].mean()), 3),
            "mean_abs_us_error_pct": round(float(rows["us_error_pct"].abs().mean()), 3),
            "mean_state_wape_pct_2017_2024": round(float(rows[rows["year"] >= 2017]["state_error_pct"].mean()), 3),
            "note": "Daniel's own harness and panel (not re-run here); quoted only",
        }
    return audit


# --- main -------------------------------------------------------------------------------------------------------

def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(OUT / name, index=False, lineterminator="\n", float_format="%.6g")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score-2025", action="store_true", help="score the selected model on 2025, once")
    parser.add_argument("--boot", type=int, default=BOOT)
    parser.add_argument("--skip-incumbent-check", action="store_true",
                        help="do not re-run the incumbent's panel to verify the NASS benchmark")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    finals = load_finals()
    files, state = load_fsa()
    inseason = nass_inseason_table()
    sources = load_stress_sources()
    test_years = list(range(FIRST_TEST, LAST_TEST + 1))

    all_predictions, used_all, g4_all = [], [], []
    for asof_key in ASOF:
        stress = stress_features(sources, asof_key)
        predictions, used, g4_info = predict_all(finals, files, state, stress, inseason, test_years, asof_key)
        all_predictions.append(predictions)
        used_all += used
        g4_all += g4_info
    predictions = pd.concat(all_predictions, ignore_index=True)
    actual = pd.concat([truth(finals, y).rename("actual").reset_index().assign(year=y) for y in test_years])
    predictions = predictions.merge(actual, on=["state", "year"], how="left")
    by_year = score_years(predictions, finals)
    summary = summarise(by_year)

    # Reproduction of the incumbent's numbers (2017-2024, as of 15 Nov; the incumbent rounds each year first).
    nov = by_year[(by_year["asof"] == "nov") & by_year["year"].between(2017, 2024)]
    reproduction = {}
    for name, expected in [("g0_persistence", (7.35, 4.12)), ("nass_latest", (1.66, 0.82))]:
        part = nov[nov["candidate"] == name]
        got = (round(float(part["state_wape_pct"].round(2).mean()), 2),
               round(float(part["us_error_pct"].round(2).abs().mean()), 2))
        reproduction[name] = {"expected_state_wape_and_abs_us": expected, "reproduced": got,
                              "match": got == expected}
    if not args.skip_incumbent_check:
        reproduction["benchmark_vs_incumbent_code"] = [incumbent_benchmark_check(inseason, finals, k) for k in ASOF]
    (OUT / "reproduction.json").write_text(json.dumps(reproduction, indent=1) + "\n", encoding="utf-8")

    selection = {k: select(by_year, k) for k in ASOF}
    compare = comparisons(by_year, args.boot)
    chosen = selection[HEADLINE_ASOF]["selected"]

    # Intervals from the selected model's 15 Nov backtest (2012-2024).
    rows = attach_last(predictions[(predictions["candidate"] == chosen) & (predictions["asof"] == HEADLINE_ASOF)],
                       finals)
    model = error_model(rows)
    interval = {"state_80_coverage_leave_one_year_out": round(coverage_loyo(rows), 3),
                "us_log_error_rms": round(us_rms(rows), 5),
                "size_class_edges_acres": [float(e) for e in model["edges"]],
                "log_error_q10_q90_by_class": {int(c): [round(float(v), 4) for v in q] for c, q in model["q"].items()}}

    # Coverage diagnostic (not used for selection): FSA grain-intended acres in last year's final over NASS.
    cover = []
    for t in test_years:
        view = FsaView(files, state, asof_date(t, HEADLINE_ASOF), t)
        ref = view.final(t - 1)
        cov = (view.acres(ref, "grain") / NassHistory(finals, t).grain(t - 1)).rename("coverage")
        cover.append(cov.rename_axis("state").reset_index().assign(year=t))
    cover = pd.concat(cover)
    cover["coverage_class"] = pd.cut(cover["coverage"], [-np.inf, 0.8, 0.95, np.inf],
                                     labels=["<0.80", "0.80-0.95", ">=0.95"]).astype(str)
    diag = predictions[(predictions["asof"] == HEADLINE_ASOF)
                       & predictions["candidate"].isin([chosen, "nass_latest", "g0_persistence"])].merge(
        cover, on=["state", "year"], how="left")
    error_by_cov = []
    for (candidate, cls), g in diag.groupby(["candidate", "coverage_class"]):
        error_by_cov.append({"candidate": candidate, "coverage_class": cls, "state_years": len(g),
                             "states": g["state"].nunique(),
                             "pooled_wape_pct": 100 * (g["pred"] - g["actual"]).abs().sum() / g["actual"].sum(),
                             "signed_pct": 100 * (g["pred"] - g["actual"]).sum() / g["actual"].sum(),
                             "share_of_acres_pct": 100 * g["actual"].sum() / diag[diag["candidate"] == candidate][
                                 "actual"].sum()})

    # 2026 forecast with the selected model, as of 15 Nov 2026 (inputs published by then).
    forecast_years = list(range(FIRST_TEST, FORECAST_YEAR + 1))
    stress_nov = stress_features(sources, HEADLINE_ASOF)
    full, used_fc, g4_fc = predict_all(finals, files, state, stress_nov, inseason, forecast_years, HEADLINE_ASOF)
    g4_all += [{**info, "asof": "nov (2026 forecast fit, 2012-2025)"} for info in g4_fc
               if info["year"] == FORECAST_YEAR]
    fc = full[(full["candidate"] == chosen) & (full["year"] == FORECAST_YEAR)].copy()
    last_2025 = truth(finals, LAST_TRUTH_YEAR)
    fc["nass_2025_final"] = fc["state"].map(last_2025)
    fc["lo80"], fc["hi80"] = bounds(fc["pred"].to_numpy(), fc["nass_2025_final"].to_numpy(), model)
    fc_used = next(u for u in used_fc if u["year"] == FORECAST_YEAR and u["candidate"] == (
        chosen if chosen != "g4_fsa_plus_stress" else "g1_fsa_ratio"))
    total = fc["pred"].sum()
    rms = interval["us_log_error_rms"]
    us_row = {"state": "US (sum of 41 states)", "pred": total, "lo80": total * np.exp(-Z80 * rms),
              "hi80": total * np.exp(Z80 * rms), "nass_2025_final": last_2025.sum(), "method": "sum"}
    forecast = pd.concat([pd.DataFrame([us_row]), fc.sort_values("pred", ascending=False)], ignore_index=True)
    forecast = forecast.assign(year=FORECAST_YEAR, candidate=chosen, asof=str(asof_date(FORECAST_YEAR, "nov")),
                               fsa_current_file=fc_used["current"], fsa_current_data_as_of=fc_used["current_data_as_of"],
                               fsa_reference_file=fc_used.get("reference"))
    forecast["change_vs_2025_pct"] = 100 * (forecast["pred"] / forecast["nass_2025_final"] - 1)
    # Comparison only (never an input): NASS's own 15 Nov 2026 benchmark, the incumbent's nass_latest rule.
    nass_2026 = nass_benchmark(inseason, finals, FORECAST_YEAR, HEADLINE_ASOF)
    forecast["nass_latest_2026_benchmark"] = forecast["state"].map(nass_2026)
    forecast.loc[0, "nass_latest_2026_benchmark"] = nass_2026.sum()
    forecast["ours_minus_nass_pct"] = 100 * (forecast["pred"] / forecast["nass_latest_2026_benchmark"] - 1)
    forecast = forecast[["year", "state", "pred", "lo80", "hi80", "nass_2025_final", "change_vs_2025_pct",
                         "nass_latest_2026_benchmark", "ours_minus_nass_pct", "method", "candidate", "asof",
                         "fsa_current_file", "fsa_current_data_as_of", "fsa_reference_file"]]

    # Outputs.
    keep = ["state", "year", "asof", "candidate", "tier", "pred", "actual", "method"]
    _write(predictions[keep].sort_values(["asof", "candidate", "year", "state"]), "backtest_by_state_year.csv")
    _write(by_year, "by_year.csv")
    _write(summary, "summary.csv")
    _write(compare, "comparisons.csv")
    _write(pd.DataFrame(used_all), "fsa_files_used.csv")
    _write(pd.DataFrame(g4_all), "g4_weights.csv")
    _write(pd.DataFrame(error_by_cov), "error_by_coverage.csv")
    _write(forecast, "forecast_2026.csv")
    (OUT / "selection.json").write_text(json.dumps({"selection": selection, "intervals": interval}, indent=1) + "\n",
                                        encoding="utf-8")
    (OUT / "inputs_audit.json").write_text(json.dumps({
        "sources": {k: {"tier": v[0], "what": v[1]} for k, v in SOURCES.items()},
        "candidates": {k: {**v, "tier": TIER_NAME[tier_of(k)]} for k, v in CANDIDATES.items()},
    }, indent=1) + "\n", encoding="utf-8")
    (OUT / "daniel_gbt_audit.json").write_text(json.dumps(daniel_audit(), indent=1) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    print(json.dumps(reproduction, indent=1))
    print(summary.round(3).to_string(index=False))
    print(json.dumps(selection, indent=1))
    print(json.dumps(interval, indent=1))
    print(forecast.head(12).round(0).to_string(index=False))

    if args.score_2025:
        score_2025(finals, files, state, sources, inseason, chosen, model)


def score_2025(finals, files, state, sources, inseason, chosen: str, model: dict) -> None:
    """The selected 15 Nov model on 2025, once (information only; never used to change anything)."""
    target = OUT / "score_2025_information_only.json"
    if target.exists():
        raise SystemExit(f"{target} exists: the 2025 information score is computed once")
    years = list(range(FIRST_TEST, SCORING_YEAR + 1))
    full, used, _ = predict_all(finals, files, state, stress_features(sources, HEADLINE_ASOF), inseason, years,
                                HEADLINE_ASOF)
    actual = truth(finals, SCORING_YEAR)
    result = {"label": "information only: computed once after selection; not used for fitting, selection or "
                       "intervals", "selected_candidate": chosen, "asof": str(asof_date(SCORING_YEAR, "nov")),
              "fsa_file_used": next(u for u in used if u["year"] == SCORING_YEAR and u["candidate"] == (
                  chosen if chosen != "g4_fsa_plus_stress" else "g1_fsa_ratio"))}
    per_state = []
    for name in [chosen, "nass_latest", "g0_persistence"]:
        rows = full[(full["candidate"] == name) & (full["year"] == SCORING_YEAR)].set_index("state")
        pred = rows["pred"].reindex(actual.index)
        miss = pred - actual
        result[name] = {"n_states": int(pred.notna().sum()),
                        "state_wape_pct": round(float(100 * miss.abs().sum() / actual.sum()), 3),
                        "us_error_pct": round(float(100 * miss.sum() / actual.sum()), 3),
                        "us_pred": round(float(pred.sum())), "us_actual": round(float(actual.sum()))}
        per_state.append(pd.DataFrame({"state": actual.index, "candidate": name, "pred": pred.to_numpy(),
                                       "actual": actual.to_numpy()}))
    sel = full[(full["candidate"] == chosen) & (full["year"] == SCORING_YEAR)].set_index("state")
    last = finals[finals["year"] == SCORING_YEAR - 1].set_index("state")["grain"]
    lo, hi = bounds(sel["pred"].reindex(actual.index).to_numpy(), last.reindex(actual.index).to_numpy(), model)
    result[chosen]["inside_80_share"] = round(float(np.mean((actual.to_numpy() >= lo) & (actual.to_numpy() <= hi))), 3)
    target.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    _write(pd.concat(per_state, ignore_index=True), "score_2025_information_only.csv")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
