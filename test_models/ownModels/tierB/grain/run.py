"""Tier B ("NASS-informed") corn-for-grain harvested acres by state, never using NASS's grain-area forecast.

Pre-registration, method and results: README.md next to this file. In short: NASS's latest in-season planted acres
(June Acreage or a later Crop Production planted column, published by the as-of date) times a grain share of planted.
The share is last year's NASS share (b0), moved by FSA's grain-intended share (b1, b5), or by models trained on NASS
history (b2 ridge, b3 monotone trees, b6 stress ridge on top of b1); b7 blends b5 with an FSA-level estimate.

Inputs (read only): see README section 1.1 for every column and its source.
    data/nass_planted_inseason.csv (this folder; fetch_reports.py)    NASS in-season planted, by release date
    data/nass/corn_acres_state.csv, data/Quickstats Data/*            NASS finals (history, truth), yields
    data/fsa/fsa_files.csv, data/fsa/fsa_corn_state.csv               FSA via kernelag.fsa as-of helpers
    data/drought/, data/rma/, corn condition weekly                    via kernelag.context
Outputs (out/): backtest_by_state_year.csv, by_year.csv, summary.csv, comparisons.csv, selection.json,
    reproduction.json, inputs_audit.json, planted_asof_used.csv, fsa_files_used.csv, fitted_weights.csv,
    earliness.csv, forecast_2026.csv, forecast_2026_all_candidates.csv, intervals.json;
    with --score-2025 once: score_2025_information_only.json / .csv

Run from the repository root:
    .venv/Scripts/python.exe test_models/ownModels/tierB/grain/run.py
    .venv/Scripts/python.exe test_models/ownModels/tierB/grain/run.py --score-2025
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
REPO = HERE.parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from kernelag import fsa as kfsa  # noqa: E402
from kernelag.context import ASOF_MONTH, STATE_NAMES  # noqa: E402
from kernelag.context import drought as usdm_drought  # noqa: E402
from kernelag.context import loss_share as rma_loss_share  # noqa: E402
from kernelag.context import poor_condition as nass_poor_condition  # noqa: E402

OUT = HERE / "out"
DATA = REPO / "data"
QUICKSTATS = DATA / "Quickstats Data"
QS_GRAIN = QUICKSTATS / "corn_grain_harvested_acres_state_2000_2026.csv"
QS_PLANTED = QUICKSTATS / "corn_planted_acres_state_2000_2026.csv"
QS_YIELD = QUICKSTATS / "corn_grain_yield_state_2000_2026.csv"
QS_CONDITION = QUICKSTATS / "corn_condition_weekly_state_2000_2026.csv"
NASS_TABLE = DATA / "nass" / "corn_acres_state.csv"
PLANTED_INSEASON = HERE / "data" / "nass_planted_inseason.csv"
INCUMBENT_BACKTEST = DATA / "models" / "state_model_backtest.csv"
DANIEL_DIR = REPO / "test_models" / "danielModel"

LAST_TRUTH_YEAR = 2025
INCUMBENT_FIRST_YEAR = 2013
SCORING_YEAR = 2025
FORECAST_YEAR = 2026
FIRST_TEST, LAST_TEST = 2012, 2024
FIRST_TRAIN = 2012
PERIODS = {"2012-2024": (2012, 2024), "2017-2024": (2017, 2024)}
PRIMARY = "2012-2024"
ASOF = {"nov": (11, 15), "oct": (10, 15), "sep": (9, 15)}
HEADLINE = "nov"
GUARD = (0.25, 4.0)
RIDGE_PENALTY = 1.0
MIN_FIT_YEARS = 3
MAX_LOG = 0.5
FEATURES = ["d_fsa_share", "yield_shock", "d_drought", "d_poor", "d_loss"]
STRESS = ["yield_shock", "d_drought", "d_poor", "d_loss"]
MONOTONE = {"d_fsa_share": 1, "yield_shock": 1, "d_drought": -1, "d_poor": -1, "d_loss": -1}
GBT_SETTINGS = dict(max_depth=2, max_iter=150, learning_rate=0.05, min_samples_leaf=15, l2_regularization=1.0,
                    early_stopping=False, random_state=0)
BOOT, SEED = 10_000, 20261114
Z80 = 1.2816
SIZE_CLASSES = 3
EXPECTED_BENCHMARKS = {"nass_latest": (1.66, 0.82), "persistence": (7.35, 4.12)}   # 2017-2024, incumbent

# --- tiers: every source carries a tag; own candidates may not declare a forbidden source -----------------------

SOURCES = {
    "nass_final_prior_years": ("A", "NASS final state grain and planted acres and yields of years before t"),
    "fsa_files_published_by_asof": ("A", "FSA crop acreage files published on or before the as-of date"),
    "usdm_drought": ("A", "US Drought Monitor weekly state maps dated on or before the as-of date"),
    "rma_cause_of_loss": ("A", "RMA cause-of-loss and insured corn acres (today's vintage)"),
    "nass_current_year_planted": ("B", "NASS June Acreage / Crop Production state planted acres of year t"),
    "nass_current_year_yield_forecast": ("B", "NASS Aug-Nov state grain yield forecast of year t"),
    "nass_crop_condition": ("B", "NASS weekly corn condition of year t"),
    "nass_current_year_grain_forecast": ("X", "NASS harvested-for-grain forecast of year t (FORBIDDEN for b-models)"),
    "daniel_panel": ("B*", "Daniel's panel: NASS planted (FINAL before 2018: look-ahead), yield forecast, condition"),
}
FORBIDDEN = {"nass_current_year_grain_forecast"}
PLANTED = ["nass_final_prior_years", "nass_current_year_planted"]
FSA = ["fsa_files_published_by_asof"]
STRESS_SOURCES = ["nass_current_year_yield_forecast", "usdm_drought", "nass_crop_condition", "rma_cause_of_loss"]
CANDIDATES = {
    "b0_planted_x_share": {"role": "own", "sources": PLANTED},
    "b1_planted_x_fsa_share": {"role": "own", "sources": PLANTED + FSA},
    "b2_ridge": {"role": "own", "sources": PLANTED + FSA + STRESS_SOURCES},
    "b3_gbt_monotone": {"role": "own", "sources": PLANTED + FSA + STRESS_SOURCES},
    "b5_planted_x_fsa_share_median": {"role": "own", "sources": PLANTED + FSA},
    "b6_b1_plus_stress": {"role": "own", "sources": PLANTED + FSA + STRESS_SOURCES},
    "b7_blend_b5_fsa_level": {"role": "own", "sources": PLANTED + FSA},
    "b4_daniel_gbt_independent": {"role": "reference", "sources": ["daniel_panel", "usdm_drought"]},
    "nass_latest": {"role": "benchmark", "sources": ["nass_final_prior_years", "nass_current_year_planted",
                                                  "nass_current_year_grain_forecast"]},
    "persistence": {"role": "benchmark", "sources": ["nass_final_prior_years"]},
}
ELIGIBLE = ["b0_planted_x_share", "b1_planted_x_fsa_share", "b2_ridge", "b3_gbt_monotone",
            "b5_planted_x_fsa_share_median", "b6_b1_plus_stress", "b7_blend_b5_fsa_level"]
SIMPLEST = "b0_planted_x_share"
NONFITTED = ["b0_planted_x_share", "b1_planted_x_fsa_share", "b5_planted_x_fsa_share_median",
             "b7_blend_b5_fsa_level"]


def check_tiers(candidates: dict = CANDIDATES) -> None:
    """Refuse any own or reference candidate that declares NASS's grain forecast (or an unknown source)."""
    for name, spec in candidates.items():
        unknown = set(spec["sources"]) - set(SOURCES)
        if unknown:
            raise ValueError(f"{name}: undeclared sources {sorted(unknown)}")
        if spec["role"] != "benchmark" and set(spec["sources"]) & FORBIDDEN:
            raise ValueError(f"{name} declares a forbidden source: {sorted(set(spec['sources']) & FORBIDDEN)}")


check_tiers()


def tier_label(name: str) -> str:
    if name == "nass_latest":
        return "not Tier B (is NASS's grain forecast)"
    tiers = {SOURCES[s][0] for s in CANDIDATES[name]["sources"]}
    if "B*" in tiers:
        return "B (with look-ahead before 2018)"
    return "B (NASS-informed)" if "B" in tiers else "A (independent)"


# --- NASS finals: history and truth -----------------------------------------------------------------------------

def _quickstats(path: Path, short_desc: str) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = raw[(raw["source_desc"] == "SURVEY") & (raw["domain_desc"] == "TOTAL") & (raw["short_desc"] == short_desc)
               & (raw["state_name"] != "OTHER STATES")]
    return pd.DataFrame({
        "year": rows["year"].astype(int), "state": rows["state_name"].astype(str),
        "period": rows["reference_period_desc"].astype(str),
        "value": pd.to_numeric(rows["Value"].str.replace(",", "").str.strip(), errors="coerce"),
    }).dropna(subset=["value"])


def load_finals() -> pd.DataFrame:
    """NASS final grain and planted acres by state and year (2000-2025): the repo table from 2013, Quick Stats before,
    after checking the two agree wherever both exist."""
    repo = pd.read_csv(NASS_TABLE)
    repo = repo[repo["period"] == "final"].pivot_table(index=["year", "state"], columns="series", values="acres",
                                                       aggfunc="first")[["grain", "planted"]]
    qs = {}
    for series, path, item in [("grain", QS_GRAIN, "CORN, GRAIN - ACRES HARVESTED"),
                               ("planted", QS_PLANTED, "CORN - ACRES PLANTED")]:
        rows = _quickstats(path, item)
        rows = rows[(rows["period"] == "YEAR") & (rows["year"] <= LAST_TRUTH_YEAR)]
        qs[series] = rows.drop_duplicates(["year", "state"]).set_index(["year", "state"])["value"]
    qs = pd.DataFrame(qs)
    both = repo.merge(qs, left_index=True, right_index=True, how="inner", suffixes=("", "_qs"))
    for series in ["grain", "planted"]:
        have = both.dropna(subset=[series, f"{series}_qs"])
        if not np.allclose(have[series], have[f"{series}_qs"]):
            raise ValueError(f"Quick Stats {series} finals differ from {NASS_TABLE}")
    early = qs[qs.index.get_level_values("year") < INCUMBENT_FIRST_YEAR]
    return pd.concat([early, repo]).reset_index().sort_values(["year", "state"]).reset_index(drop=True)


def load_final_yields() -> pd.DataFrame:
    rows = _quickstats(QS_YIELD, "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")
    rows = rows[(rows["period"] == "YEAR") & (rows["year"] <= LAST_TRUTH_YEAR)]
    return rows.drop_duplicates(["year", "state"])[["year", "state", "value"]].rename(columns={"value": "yield"})


class NassHistory:
    """NASS finals visible to a forecast for ``target_year``: years before it only."""

    def __init__(self, finals: pd.DataFrame, yields: pd.DataFrame, target_year: int):
        self.target_year = target_year
        self._finals = finals[finals["year"] < target_year]
        self._yields = yields[yields["year"] < target_year]

    def _check(self, year: int) -> None:
        if year >= self.target_year:
            raise PermissionError(f"NASS {year} is not history for a {self.target_year} forecast")

    def grain(self, year: int) -> pd.Series:
        self._check(year)
        rows = self._finals[self._finals["year"] == year].dropna(subset=["grain"])
        return rows.set_index("state")["grain"]

    def planted(self, year: int) -> pd.Series:
        self._check(year)
        rows = self._finals[self._finals["year"] == year].dropna(subset=["planted"])
        return rows.set_index("state")["planted"]

    def yield_final(self, year: int) -> pd.Series:
        self._check(year)
        rows = self._yields[self._yields["year"] == year]
        return rows.set_index("state")["yield"]


def truth(finals: pd.DataFrame, year: int) -> pd.Series:
    """NASS final grain acres of ``year`` (scoring only)."""
    rows = finals[finals["year"] == year].dropna(subset=["grain"])
    return rows.set_index("state")["grain"]


def asof_date(year: int, key: str) -> date:
    month, day = ASOF[key]
    return date(year, month, day)


# --- current-year NASS inputs that are not the acreage answer ---------------------------------------------------

def load_planted_inseason(path: Path = PLANTED_INSEASON) -> pd.DataFrame:
    table = pd.read_csv(path)
    table["release_date"] = pd.to_datetime(table["release_date"])
    return table


def planted_asof(table: pd.DataFrame, year: int, asof: date) -> pd.DataFrame:
    """Per state, NASS's latest planted acres published on or before ``asof`` in ``year``, with its report."""
    rows = table[(table["year"] == year) & (table["release_date"] <= pd.Timestamp(asof))]
    rows = rows.sort_values("release_date").drop_duplicates("state", keep="last")
    return rows.set_index("state")[["planted", "period", "release_date", "report"]]


def load_yield_forecasts() -> pd.DataFrame:
    rows = _quickstats(QS_YIELD, "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")
    month = rows["period"].str.extract(r"YEAR - (AUG|SEP|OCT|NOV) FORECAST")[0].map(
        {"AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11})
    rows = rows.assign(month=month).dropna(subset=["month"])
    return rows.drop_duplicates(["year", "state", "month"])[["year", "state", "month", "value"]]


def yield_asof(forecasts: pd.DataFrame, year: int, key: str) -> pd.Series:
    """NASS's latest yield forecast for ``year`` whose report month is on or before the as-of month."""
    rows = forecasts[(forecasts["year"] == year) & (forecasts["month"] <= ASOF_MONTH[key])]
    return rows.sort_values("month").drop_duplicates("state", keep="last").set_index("state")["value"]


def _read_folder(folder: Path, columns: list[str]) -> pd.DataFrame:
    files = sorted(folder.glob("*.csv*"))
    if not files:
        raise FileNotFoundError(f"no files in {folder}")
    return pd.concat([pd.read_csv(f, usecols=columns, dtype=str) for f in files], ignore_index=True)


def load_stress_sources() -> dict:
    return {
        "usdm": pd.read_csv(DATA / "drought" / "usdm_state_weekly_2000_2026.csv"),
        "condition": pd.read_csv(QS_CONDITION, dtype=str, keep_default_na=False),
        "loss": _read_folder(DATA / "rma" / "cause_of_loss_corn", [
            "commodity_year", "state_abbreviation", "cause_of_loss_code", "month_of_loss", "net_determined_quantity"]),
        "insured": _read_folder(DATA / "rma" / "insured_by_type_corn", [
            "commodity_year", "state_abbreviation", "reporting_level_type", "net_reporting_level_amount"]),
    }


def stress_levels(sources: dict, key: str) -> pd.DataFrame:
    """drought, poor, loss by state and year, each using only what was public by the 15th of the as-of month."""
    parts = [usdm_drought(sources["usdm"], key),
             nass_poor_condition(sources["condition"], key).rename(columns={"poor_condition": "poor"}),
             rma_loss_share(sources["loss"], sources["insured"], key).rename(columns={"loss_share": "loss"})]
    table = parts[0]
    for part in parts[1:]:
        table = table.merge(part, on=["state", "year"], how="outer")
    return table


# --- FSA view under the as-of rule ------------------------------------------------------------------------------

def load_fsa() -> tuple[pd.DataFrame, pd.DataFrame]:
    files = pd.read_csv(DATA / "fsa" / "fsa_files.csv")
    state = pd.read_csv(DATA / "fsa" / "fsa_corn_state.csv", dtype={"state_fips": str})
    ok = files[files["status"] == "ok"]
    if ok.dropna(subset=["data_as_of"]).duplicated(["crop_year", "data_as_of"]).any():
        raise ValueError("two parsed FSA files share a crop year and data date")
    return files, state


class FsaView:
    """The FSA files a forecast made on ``asof`` for ``crop_year`` may use (``kernelag.fsa.usable_files``)."""

    def __init__(self, files: pd.DataFrame, state: pd.DataFrame, asof: date, crop_year: int):
        self.asof, self.crop_year = asof, crop_year
        self.usable = kfsa.usable_files(files, asof, crop_year)
        self._files, self._state = files, state

    def current(self) -> pd.Series | None:
        return kfsa.latest_file(self._files, self.asof, self.crop_year)

    def final(self, crop_year: int) -> pd.Series | None:
        if crop_year >= self.crop_year:
            raise PermissionError("a crop year's own final file is never an input for that year")
        rows = self.usable[(self.usable["crop_year"] == crop_year)
                           & self.usable["vintage"].astype(str).str.startswith("final")]
        return None if rows.empty else rows.sort_values("data_as_of").iloc[-1]

    def acres(self, file: pd.Series | None, measure: str) -> pd.Series:
        """"grain": planted acres with intended use grain; "all": planted + failed acres, every intended use."""
        if file is None:
            return pd.Series(dtype=float)
        if file["zip_name"] not in set(self.usable["zip_name"]):
            raise PermissionError(f"{file['zip_name']} is not usable for a forecast made on {self.asof}")
        rows = self._state[(self._state["crop_year"] == file["crop_year"])
                           & (self._state["data_as_of"].astype(str) == str(file["data_as_of"]))]
        if measure == "grain":
            rows = rows[rows["intended_use"] == "grain"]
            values = rows["planted_acres"]
        elif measure == "all":
            values = rows["planted_acres"].fillna(0.0) + rows["failed_acres"].fillna(0.0)
        else:
            raise ValueError(measure)
        return values.groupby(rows["state"]).sum()

    def share(self, file: pd.Series | None) -> pd.Series:
        grain, total = self.acres(file, "grain"), self.acres(file, "all")
        return (grain / total.where(total > 0)).reindex(total.index)


# --- inputs per year and as-of ----------------------------------------------------------------------------------

class Sources:
    """Everything loaded once."""

    def __init__(self):
        self.finals = load_finals()
        self.yields = load_final_yields()
        self.forecasts = load_yield_forecasts()
        self.planted = load_planted_inseason()
        self.files, self.fsa_state = load_fsa()
        raw = load_stress_sources()
        self.stress = {key: stress_levels(raw, key) for key in ASOF}


def _ratio(num: pd.Series, den: pd.Series, index: pd.Index) -> pd.Series:
    num, den = num.reindex(index), den.reindex(index)
    return (num / den.where(den > 0)).astype(float)


def inputs_for(src: Sources, t: int, key: str) -> tuple[pd.DataFrame, dict]:
    """One row per state with a NASS grain final in t-1: every input a b-candidate may use for year ``t`` as of
    ``key``. Never touches NASS's grain forecast or G(t)."""
    day = asof_date(t, key)
    hist = NassHistory(src.finals, src.yields, t)
    g1, p1 = hist.grain(t - 1), hist.planted(t - 1)
    idx = g1.index
    pa = planted_asof(src.planted, t, day)
    view = FsaView(src.files, src.fsa_state, day, t)
    cur = view.current()
    table = pd.DataFrame(index=idx)
    table["G_last"] = g1
    table["P_last"] = p1.reindex(idx)
    table["Pa"] = pa["planted"].reindex(idx)
    table["Pa_report"] = pa["report"].reindex(idx)
    table["Pa_period"] = pa["period"].reindex(idx)
    table["s_last"] = table["G_last"] / table["P_last"]
    table["sig_cur"] = view.share(cur).reindex(idx)
    table["fg_cur"] = view.acres(cur, "grain").reindex(idx)
    corr, lvl, finals_used = [], [], []
    for k in (1, 2, 3):
        fin = view.final(t - k)
        if fin is None:
            continue
        gk, pk = hist.grain(t - k), hist.planted(t - k)
        if gk.empty:
            continue
        s_k = _ratio(gk, pk, idx)
        corr.append((s_k / view.share(fin).reindex(idx)).rename(k))
        lvl.append(_ratio(gk, view.acres(fin, "grain"), idx).rename(k))
        finals_used.append(str(fin["zip_name"]))
        if k == 1:
            table["sig_fin1"] = view.share(fin).reindex(idx)
    table["corr1"] = corr[0] if corr and corr[0].name == 1 else np.nan
    table["corr_med"] = pd.concat(corr, axis=1).median(axis=1, skipna=True) if corr else np.nan
    table["lvl_med"] = pd.concat(lvl, axis=1).median(axis=1, skipna=True) if lvl else np.nan
    if "sig_fin1" not in table:
        table["sig_fin1"] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        table["d_fsa_share"] = np.log(table["sig_cur"] / table["sig_fin1"])
        ymean = pd.concat([hist.yield_final(t - k).rename(k) for k in (1, 2, 3)], axis=1).mean(axis=1, skipna=False)
        table["yield_shock"] = np.log(yield_asof(src.forecasts, t, key).reindex(idx) / ymean.reindex(idx))
    levels = src.stress[key]
    now = levels[levels["year"] == t].set_index("state")
    before = levels[levels["year"] == t - 1].set_index("state")
    table["d_drought"] = now["drought"].reindex(idx) - before["drought"].reindex(idx)
    table["d_poor"] = now["poor"].reindex(idx) - before["poor"].reindex(idx)
    table["d_loss"] = now["loss"].reindex(idx) - before["loss"].reindex(idx)
    table = table.replace([np.inf, -np.inf], np.nan)
    used = {"year": t, "asof": key, "fsa_current": None if cur is None else str(cur["zip_name"]),
            "fsa_current_data_as_of": None if cur is None else str(cur["data_as_of"]),
            "fsa_finals_used": "|".join(finals_used),
            "planted_reports": "|".join(sorted(set(table["Pa_report"].dropna().astype(str))))}
    return table, used


# --- candidates -------------------------------------------------------------------------------------------------

def nonfitted(inp: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """b0, b1, b5, b7 (and the FSA-level g3 inside b7) with their guards; each a frame of pred and method."""
    out = {}
    b0_ok = inp["Pa"].gt(0) & inp["s_last"].gt(0)
    b0 = pd.Series(np.where(b0_ok, inp["Pa"] * inp["s_last"], inp["G_last"]), index=inp.index)
    out["b0_planted_x_share"] = pd.DataFrame({"pred": b0, "method": np.where(b0_ok, "planted_x_share",
                                                                             "fallback_persistence")})

    def with_share(correction: pd.Series, label: str) -> pd.DataFrame:
        ok = (b0_ok & inp["sig_cur"].gt(0) & correction.between(*GUARD))
        pred = np.where(ok, inp["Pa"] * inp["sig_cur"] * correction, b0)
        method = np.where(ok, label, out["b0_planted_x_share"]["method"].radd("fallback_b0:"))
        return pd.DataFrame({"pred": pred, "method": method}, index=inp.index)

    out["b1_planted_x_fsa_share"] = with_share(inp["corr1"], "fsa_share")
    out["b5_planted_x_fsa_share_median"] = with_share(inp["corr_med"], "fsa_share_median")
    g3_ok = inp["fg_cur"].gt(0) & inp["lvl_med"].between(*GUARD)
    g3 = pd.Series(np.where(g3_ok, inp["fg_cur"] * inp["lvl_med"], inp["G_last"]), index=inp.index)
    b5 = out["b5_planted_x_fsa_share_median"]["pred"]
    out["b7_blend_b5_fsa_level"] = pd.DataFrame({
        "pred": np.sqrt(b5 * g3),
        "method": np.where(g3_ok, "blend", "blend_g3_fallback_persistence"),
    }, index=inp.index)
    out["_g3"] = pd.DataFrame({"pred": g3, "method": np.where(g3_ok, "fsa_level", "fallback_persistence")})
    return out


def fit_ridge(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Weighted ridge on std-scaled features, no centring, no intercept (the form of kernelag.state_model.fit_ridge).
    Returns (coefficient per scaled feature, scale)."""
    scale = x.std(axis=0)
    scale[scale == 0] = 1.0
    xs = x / scale
    xtw = xs.T * w
    coef = np.linalg.solve(xtw @ xs + RIDGE_PENALTY * w.mean() * np.eye(x.shape[1]), xtw @ y)
    return coef, scale


def fit_gbt(x: np.ndarray, y: np.ndarray, w: np.ndarray, features: list[str]):
    from sklearn.ensemble import HistGradientBoostingRegressor
    model = HistGradientBoostingRegressor(monotonic_cst=[MONOTONE[f] for f in features], **GBT_SETTINGS)
    return model.fit(x, y, sample_weight=w / w.mean())


def fitted_candidates(table: dict, t: int, key: str, history: NassHistory) -> tuple[dict, list[dict]]:
    """b2, b3, b6 for year ``t``: trained on state-years 2012..t-1 at the same as-of (``table[(y, key)]`` holds each
    year's inputs and non-fitted predictions); fewer than MIN_FIT_YEARS training years -> b1."""
    inp, base = table[(t, key)]["inputs"], table[(t, key)]["preds"]
    b0, b1 = base["b0_planted_x_share"], base["b1_planted_x_fsa_share"]
    train = []
    for y in range(FIRST_TRAIN, t):
        if (y, key) not in table:
            continue
        rows = table[(y, key)]["inputs"].copy()
        preds = table[(y, key)]["preds"]
        rows["actual"] = history.grain(y).reindex(rows.index)
        rows["b0"] = preds["b0_planted_x_share"]["pred"]
        rows["b0_ok"] = preds["b0_planted_x_share"]["method"] == "planted_x_share"
        rows["b1"] = preds["b1_planted_x_fsa_share"]["pred"]
        rows["year"] = y
        train.append(rows.dropna(subset=["actual", "G_last"]))
    years = sorted({int(r["year"].iloc[0]) for r in train if len(r)})
    out, info = {}, []
    if len(years) < MIN_FIT_YEARS:
        for name in ["b2_ridge", "b3_gbt_monotone", "b6_b1_plus_stress"]:
            out[name] = b1.assign(method="fallback_b1:" + b1["method"].astype(str))
            info.append({"year": t, "asof": key, "candidate": name, "train_years": "", "n_train": 0})
        return out, info
    fit = pd.concat(train)
    span = f"{years[0]}-{years[-1]}"

    # b2 / b3: target log(G / (Pa s_last)) on rows where b0 used Pa.
    rows = fit[fit["b0_ok"]]
    x = rows[FEATURES].fillna(0.0).to_numpy(float)
    y = np.clip(np.log(rows["actual"] / rows["b0"]).to_numpy(float), -MAX_LOG, MAX_LOG)
    w = rows["G_last"].to_numpy(float)
    xt = inp[FEATURES].fillna(0.0).to_numpy(float)
    ok_t = (b0["method"] == "planted_x_share").to_numpy()
    coef, scale = fit_ridge(x, y, w)
    change = (xt / scale) @ coef
    out["b2_ridge"] = pd.DataFrame({"pred": np.where(ok_t, b0["pred"] * np.exp(change), b0["pred"]),
                                    "method": np.where(ok_t, "ridge", b0["method"])}, index=inp.index)
    info.append({"year": t, "asof": key, "candidate": "b2_ridge", "train_years": span, "n_train": len(rows),
                 **{f"coef_{f}": float(c) for f, c in zip(FEATURES, coef)},
                 **{f"scale_{f}": float(s) for f, s in zip(FEATURES, scale)}})
    gbt = fit_gbt(x, y, w, FEATURES)
    change = np.clip(gbt.predict(xt), -MAX_LOG, MAX_LOG)
    out["b3_gbt_monotone"] = pd.DataFrame({"pred": np.where(ok_t, b0["pred"] * np.exp(change), b0["pred"]),
                                           "method": np.where(ok_t, "gbt", b0["method"])}, index=inp.index)
    info.append({"year": t, "asof": key, "candidate": "b3_gbt_monotone", "train_years": span, "n_train": len(rows)})

    # b6: target log(G / b1), stress features only.
    rows = fit.dropna(subset=["b1"])
    x = rows[STRESS].fillna(0.0).to_numpy(float)
    y = np.clip(np.log(rows["actual"] / rows["b1"]).to_numpy(float), -MAX_LOG, MAX_LOG)
    coef, scale = fit_ridge(x, y, rows["G_last"].to_numpy(float))
    change = (inp[STRESS].fillna(0.0).to_numpy(float) / scale) @ coef
    out["b6_b1_plus_stress"] = pd.DataFrame({"pred": b1["pred"] * np.exp(change),
                                             "method": "stress_on_" + b1["method"].astype(str)}, index=inp.index)
    info.append({"year": t, "asof": key, "candidate": "b6_b1_plus_stress", "train_years": span, "n_train": len(rows),
                 **{f"coef_{f}": float(c) for f, c in zip(STRESS, coef)},
                 **{f"scale_{f}": float(s) for f, s in zip(STRESS, scale)}})
    return out, info


# --- benchmarks (scoring and comparison only; never an input to a b-candidate) ----------------------------------

QS_PERIOD = {"YEAR - MAR ACREAGE": "mar", "YEAR - JUN ACREAGE": "jun", "YEAR - AUG FORECAST": "aug",
             "YEAR - SEP FORECAST": "sep", "YEAR - OCT FORECAST": "oct", "YEAR - NOV FORECAST": "nov",
             "YEAR - AUG ACREAGE": "aug", "YEAR - SEP ACREAGE": "sep", "YEAR - OCT ACREAGE": "oct"}


def nass_inseason_rows() -> pd.DataFrame:
    """NASS in-season grain-forecast and planted rows as the incumbent stores them, plus 2012 from Quick Stats.
    BENCHMARK ONLY: this table holds NASS's grain forecast."""
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


def nass_benchmark(inseason: pd.DataFrame, finals: pd.DataFrame, year: int, key: str) -> pd.Series:
    """The incumbent's ``nass_latest`` rule (kernelag.state_model.predict_grain): NASS's latest grain forecast
    published by the as-of month; else latest planted x last year's grain share; else last year."""
    from kernelag.state_panel import GRAIN_ASOF, PLANTED_ASOF, latest_available, public_by
    rows = inseason[inseason["year"] == year].rename(columns={"acres": "value"})
    grain = latest_available(rows[rows["series"] == "grain"], public_by(GRAIN_ASOF, key))
    planted = latest_available(rows[rows["series"] == "planted"], public_by(PLANTED_ASOF, key))
    grain = grain.droplevel("year") if len(grain) else pd.Series(dtype=float)
    planted = planted.droplevel("year") if len(planted) else pd.Series(dtype=float)
    last = finals[finals["year"] == year - 1].set_index("state")
    states = last["grain"].dropna().index
    by_share = planted.reindex(states) * last["grain"].reindex(states) / last["planted"].reindex(states)
    return grain.reindex(states).fillna(by_share).fillna(last["grain"].reindex(states))


def incumbent_check(inseason: pd.DataFrame, finals: pd.DataFrame, key: str) -> dict:
    """Max |difference| between the rebuilt benchmark and the incumbent's own predict_grain, 2014-2024."""
    from kernelag.state_model import add_changes, predict_grain
    from kernelag.state_panel import load_panel
    table = add_changes(load_panel(key))
    worst = 0.0
    for year in range(INCUMBENT_FIRST_YEAR + 1, LAST_TEST + 1):
        theirs = predict_grain(table, year)["grain"]
        mine = nass_benchmark(inseason, finals, year, key).reindex(theirs.index)
        worst = max(worst, float((mine - theirs).abs().max()))
    return {"asof": key, "years_compared": f"{INCUMBENT_FIRST_YEAR + 1}-{LAST_TEST}", "max_abs_difference_acres": worst}


def daniel_predictions(years: list[int]) -> tuple[pd.DataFrame, dict]:
    """Daniel's grain_gbt_independent, trained and predicted by his own code (imported read-only; nothing written)."""
    sys.path.insert(0, str(DANIEL_DIR))
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # write nothing into his folder
    try:
        import train_gbt as daniel  # noqa: E402
    finally:
        sys.path.remove(str(DANIEL_DIR))
        sys.dont_write_bytecode = keep
    panel = daniel.base.load_panel("nov")
    parts = []
    for t in years:
        _, pred = daniel.forecast(panel, "grain_gbt_independent", t)
        parts.append(pd.DataFrame({"state": [STATE_NAMES.get(s, s) for s in pred], "pred": list(pred.values()),
                                   "year": t}))
    meta = {"source": "test_models/danielModel/train_gbt.py forecast(panel, 'grain_gbt_independent', t)",
            "panel": "test_models/danielModel/out/panel_nov.csv",
            "look_ahead": "planted_asof is NASS FINAL planted for years before 2018 (build_panel.py stand_in)"}
    return pd.concat(parts, ignore_index=True), meta


# --- scoring ----------------------------------------------------------------------------------------------------

def year_errors(pred: pd.Series, actual: pd.Series) -> dict:
    both = pd.DataFrame({"pred": pred, "actual": actual}).dropna()
    miss = both["pred"] - both["actual"]
    return {"n_states": len(both), "state_wape_pct": 100 * miss.abs().sum() / both["actual"].sum(),
            "us_error_pct": 100 * miss.sum() / both["actual"].sum()}


def by_year_table(backtest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cand, key, year), g in backtest.groupby(["candidate", "asof", "year"]):
        rows.append({"candidate": cand, "asof": key, "year": year,
                     **year_errors(g.set_index("state")["pred"], g.set_index("state")["actual"])})
    return pd.DataFrame(rows)


def summarise(by_year: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, (lo, hi) in PERIODS.items():
        part = by_year[by_year["year"].between(lo, hi)]
        for (cand, key), g in part.groupby(["candidate", "asof"]):
            rows.append({"candidate": cand, "asof": key, "period": period, "tier": tier_label(cand),
                         "role": CANDIDATES[cand]["role"], "n_years": len(g), "n_states": int(g["n_states"].min()),
                         "mean_state_wape_pct": g["state_wape_pct"].mean(),
                         "mean_abs_us_error_pct": g["us_error_pct"].abs().mean(),
                         "mean_signed_us_error_pct": g["us_error_pct"].mean(),
                         "worst_year_state_wape_pct": g["state_wape_pct"].max()})
    return pd.DataFrame(rows)


def paired_ci(diff: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    """Mean of yearly differences and its 90% bootstrap interval (resampling years)."""
    draws = rng.integers(0, len(diff), size=(BOOT, len(diff)))
    means = diff[draws].mean(axis=1)
    return float(diff.mean()), float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95))


def comparisons(by_year: pd.DataFrame, key: str = HEADLINE) -> pd.DataFrame:
    rows = []
    part = by_year[by_year["asof"] == key]
    for period, (lo, hi) in PERIODS.items():
        p = part[part["year"].between(lo, hi)]
        wide_w = p.pivot(index="year", columns="candidate", values="state_wape_pct")
        wide_u = p.pivot(index="year", columns="candidate", values="us_error_pct").abs()
        for cand in wide_w.columns:
            for ref in ["nass_latest", "persistence", SIMPLEST]:
                if cand == ref or ref not in wide_w:
                    continue
                for metric, wide in [("state_wape_pct", wide_w), ("abs_us_error_pct", wide_u)]:
                    pair = wide[[cand, ref]].dropna()
                    mean, lo_ci, hi_ci = paired_ci((pair[cand] - pair[ref]).to_numpy(), np.random.default_rng(SEED))
                    rows.append({"asof": key, "period": period, "candidate": cand, "vs": ref, "metric": metric,
                                 "n_years": len(pair), "mean_diff_pts": mean, "ci90_lo": lo_ci, "ci90_hi": hi_ci,
                                 "ci_excludes_zero": bool(lo_ci > 0 or hi_ci < 0)})
    return pd.DataFrame(rows)


def select(by_year: pd.DataFrame, key: str = HEADLINE) -> dict:
    lo, hi = PERIODS[PRIMARY]
    part = by_year[(by_year["asof"] == key) & by_year["year"].between(lo, hi) & by_year["candidate"].isin(ELIGIBLE)]
    wide = part.pivot(index="year", columns="candidate", values="state_wape_pct")[ELIGIBLE]
    means = wide.mean()
    best = str(means.idxmin())
    result = {"asof": key, "period": PRIMARY, "n_years": len(wide),
              "mean_state_wape_pct": {k: round(float(v), 4) for k, v in means.items()},
              "best": best, "simplest": SIMPLEST}
    if best == SIMPLEST:
        return {**result, "selected": SIMPLEST, "reason": "the simplest candidate is the best"}
    d = (wide[SIMPLEST] - wide[best]).to_numpy()
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    passed = bool(d.mean() > 2 * se)
    return {**result, "mean_gain_vs_simplest_pts": float(d.mean()), "se_pts": se, "two_se_pts": 2 * se,
            "selected": best if passed else SIMPLEST,
            "reason": "beats the simplest candidate by more than 2 SE" if passed else
            "best does not beat the simplest by more than 2 SE"}


# --- intervals --------------------------------------------------------------------------------------------------

def error_model(rows: pd.DataFrame) -> dict:
    """Size-class edges (tertiles of last year's acres) and q10/q90 of log(actual/pred) per class; US RMS."""
    edges = np.quantile(rows["G_last"], [1 / 3, 2 / 3])
    size = np.searchsorted(edges, rows["G_last"].to_numpy())
    logerr = np.log(rows["actual"] / rows["pred"]).to_numpy()
    q = {c: np.quantile(logerr[size == c], [0.10, 0.90]).tolist() for c in range(SIZE_CLASSES)}
    totals = rows.groupby("year")[["actual", "pred"]].sum()
    us_log = np.log(totals["actual"] / totals["pred"]).to_numpy()
    return {"edges": edges.tolist(), "q10_q90_by_size_class": q, "us_rms_log": float(np.sqrt((us_log ** 2).mean())),
            "us_q10_q90_empirical": np.quantile(us_log, [0.10, 0.90]).tolist(), "n_years": len(us_log)}


def bounds(pred: pd.Series, g_last: pd.Series, model: dict) -> pd.DataFrame:
    size = np.searchsorted(np.array(model["edges"]), g_last.reindex(pred.index).to_numpy())
    q = np.array([model["q10_q90_by_size_class"][c] for c in size])
    return pd.DataFrame({"lo80": pred.to_numpy() * np.exp(q[:, 0]), "hi80": pred.to_numpy() * np.exp(q[:, 1])},
                        index=pred.index)


def coverage(rows: pd.DataFrame) -> dict:
    """Leave-one-year-out coverage of the state and US 80% intervals."""
    inside, us_inside = [], []
    for year in sorted(rows["year"].unique()):
        model = error_model(rows[rows["year"] != year])
        held = rows[rows["year"] == year].set_index("state")
        b = bounds(held["pred"], held["G_last"], model)
        inside.extend(((held["actual"] >= b["lo80"]) & (held["actual"] <= b["hi80"])).tolist())
        total, actual = held["pred"].sum(), held["actual"].sum()
        half = Z80 * model["us_rms_log"]
        us_inside.append(bool(total * np.exp(-half) <= actual <= total * np.exp(half)))
    return {"state_80_coverage": float(np.mean(inside)), "us_80_coverage": float(np.mean(us_inside)),
            "n_state_years": len(inside), "n_years": len(us_inside)}


# --- driver -----------------------------------------------------------------------------------------------------

def build_tables(src: Sources, years: list[int], keys: list[str]) -> tuple[dict, list[dict]]:
    """Inputs and non-fitted predictions for every (year, as-of)."""
    table, used = {}, []
    for key in keys:
        for t in years:
            inp, info = inputs_for(src, t, key)
            table[(t, key)] = {"inputs": inp, "preds": nonfitted(inp)}
            used.append(info)
    return table, used


def all_predictions(src: Sources, table: dict, years: list[int], key: str) -> tuple[dict, list[dict]]:
    """Every b-candidate's prediction for each year in ``years`` at one as-of date: {year: {name: frame}}."""
    preds, info = {}, []
    for t in years:
        hist = NassHistory(src.finals, src.yields, t)
        fitted, fit_info = fitted_candidates(table, t, key, hist)
        info.extend(fit_info)
        preds[t] = {**{k: v for k, v in table[(t, key)]["preds"].items() if not k.startswith("_")}, **fitted}
    return preds, info


def backtest_frame(src: Sources, table: dict, preds: dict, inseason: pd.DataFrame, key: str,
                   daniel: pd.DataFrame | None) -> pd.DataFrame:
    parts = []
    for t, by_name in preds.items():
        actual = truth(src.finals, t)
        inp = table[(t, key)]["inputs"]
        frames = dict(by_name)
        frames["persistence"] = pd.DataFrame({"pred": inp["G_last"], "method": "persistence"})
        frames["nass_latest"] = pd.DataFrame({"pred": nass_benchmark(inseason, src.finals, t, key),
                                              "method": "nass_grain_forecast"})
        if daniel is not None and key == HEADLINE:
            d = daniel[daniel["year"] == t].set_index("state")["pred"].reindex(inp.index)
            frames["b4_daniel_gbt_independent"] = pd.DataFrame({
                "pred": d.fillna(inp["G_last"]), "method": np.where(d.notna(), "daniel_gbt", "fallback_persistence")})
        for name, frame in frames.items():
            frame = frame.reindex(inp.index)
            parts.append(pd.DataFrame({"state": inp.index, "year": t, "asof": key, "candidate": name,
                                       "pred": frame["pred"].to_numpy(float), "actual": actual.reindex(inp.index),
                                       "G_last": inp["G_last"].to_numpy(), "method": frame["method"].astype(str)}))
    return pd.concat(parts, ignore_index=True)


def reproduction(by_year: pd.DataFrame) -> dict:
    """The two benchmarks on 2017-2024 against the incumbent's stored numbers."""
    out = {}
    stored = pd.read_csv(INCUMBENT_BACKTEST)
    stored = stored[(stored["scope"] == "all_states") & (stored["series"] == "grain")]
    names = {"nass_latest": "nass_latest", "persistence": "same_as_last_year"}
    for mine, theirs in names.items():
        part = by_year[(by_year["candidate"] == mine) & (by_year["asof"] == "nov")
                       & by_year["year"].between(2017, 2024)]
        rounded = (round(part["state_wape_pct"].round(2).mean(), 2),
                   round(part["us_error_pct"].round(2).abs().mean(), 2))
        ref = stored[stored["predictor"] == theirs].set_index("year")
        per_year = part.set_index("year")
        diffs = {
            "max_abs_diff_state_pct_per_year": float((per_year["state_wape_pct"].round(2)
                                                      - ref["state_error_pct"]).abs().max()),
            "max_abs_diff_us_pct_per_year": float((per_year["us_error_pct"].round(2)
                                                   - ref["total_error_pct"]).abs().max()),
            "n_states_per_year": sorted(set(per_year["n_states"].astype(int))),
        }
        out[mine] = {"expected_state_wape_and_abs_us": list(EXPECTED_BENCHMARKS[mine]), "reproduced": list(rounded),
                     "match": list(rounded) == list(EXPECTED_BENCHMARKS[mine]), **diffs}
    return out


def posthoc_vs_fsa_only(src: Sources, table: dict, by_year: pd.DataFrame, chosen: str, keys: list[str]) -> pd.DataFrame:
    """POST-HOC (not pre-registered, never used for selection): the selected model against g3, the FSA-only Tier A
    estimate inside b7, paired by year. Answers "what do the NASS inputs add over FSA alone?"."""
    rows = []
    for key in keys:
        g3 = pd.DataFrame([{"year": t, **year_errors(table[(t, key)]["preds"]["_g3"]["pred"], truth(src.finals, t))}
                           for t in range(FIRST_TEST, LAST_TEST + 1)])
        mine = by_year[(by_year["candidate"] == chosen) & (by_year["asof"] == key)]
        both = g3.merge(mine, on="year", suffixes=("_g3", "_sel"))
        for period, (lo, hi) in PERIODS.items():
            part = both[both["year"].between(lo, hi)]
            for metric, a, b in [("state_wape_pct", part["state_wape_pct_sel"], part["state_wape_pct_g3"]),
                                 ("abs_us_error_pct", part["us_error_pct_sel"].abs(), part["us_error_pct_g3"].abs())]:
                mean, lo_ci, hi_ci = paired_ci((a - b).to_numpy(), np.random.default_rng(SEED))
                rows.append({"asof": key, "period": period, "candidate": chosen, "vs": "g3_fsa_only (Tier A form)",
                             "metric": metric, "candidate_mean": float(a.mean()), "g3_mean": float(b.mean()),
                             "mean_diff_pts": mean, "ci90_lo": lo_ci, "ci90_hi": hi_ci, "note": "post-hoc"})
    return pd.DataFrame(rows)


def sign_check(fit_info: list[dict]) -> pd.DataFrame:
    """Ridge coefficients (b2, b6) against the signs written down before fitting (MONOTONE)."""
    info = pd.DataFrame(fit_info)
    rows = []
    for (cand, key), g in info[info["candidate"].isin(["b2_ridge", "b6_b1_plus_stress"])].groupby(
            ["candidate", "asof"]):
        for feature, sign in MONOTONE.items():
            col = f"coef_{feature}"
            if col not in g or g[col].isna().all():
                continue
            fitted = g.dropna(subset=[col])
            backtest = fitted[fitted["year"] <= LAST_TEST]
            last = fitted[fitted["year"] == fitted["year"].max()]
            rows.append({"candidate": cand, "asof": key, "feature": feature, "expected_sign": sign,
                         "n_backtest_fits": len(backtest),
                         "n_fits_with_expected_sign": int((np.sign(backtest[col]) == sign).sum()),
                         "coef_per_std_latest_fit": float(last[col].iloc[0]),
                         "latest_fit_year": int(last["year"].iloc[0]),
                         "raw_coef_latest_fit": float(last[col].iloc[0] / last[f"scale_{feature}"].iloc[0])})
    return pd.DataFrame(rows)


def planted_check(src: Sources) -> dict:
    """The parsed in-season planted acres against the repo's NASS table wherever both hold a value."""
    repo = pd.read_csv(NASS_TABLE)
    repo = repo[(repo["series"] == "planted") & ~repo["period"].isin(["final", "mar"])]
    both = src.planted.merge(repo[["year", "state", "period", "acres"]], on=["year", "state", "period"])
    return {"rows_compared": int(len(both)), "years": f"{both['year'].min()}-{both['year'].max()}",
            "max_abs_difference_acres": float((both["planted"] - both["acres"]).abs().max())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score-2025", action="store_true", help="score the selected model on 2025, once")
    parser.add_argument("--skip-daniel", action="store_true", help="do not re-run b4")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    src = Sources()
    keys = ["nov", "oct", "sep"]
    years = list(range(FIRST_TEST, LAST_TEST + 1))
    table, fsa_used = build_tables(src, years + [SCORING_YEAR, FORECAST_YEAR], keys)

    inseason = nass_inseason_rows()
    daniel, daniel_meta = (None, {"skipped": True}) if args.skip_daniel else daniel_predictions(years)
    frames, fit_info, preds_by_key = [], [], {}
    for key in keys:
        preds, info = all_predictions(src, table, years, key)
        preds_by_key[key] = preds
        fit_info.extend(info)
        frames.append(backtest_frame(src, table, preds, inseason, key, daniel))
    backtest = pd.concat(frames, ignore_index=True)
    if backtest["actual"].isna().any():
        raise ValueError("a backtest state-year has no truth")
    by_year = by_year_table(backtest)
    summary = summarise(by_year)
    comps = pd.concat([comparisons(by_year, key) for key in keys], ignore_index=True)
    selection = {key: select(by_year, key) for key in keys}
    chosen = selection[HEADLINE]["selected"]

    repro = {"benchmarks_2017_2024": reproduction(by_year),
             "benchmark_vs_incumbent_code": [incumbent_check(inseason, src.finals, k) for k in keys],
             "planted_inseason_vs_repo_table": planted_check(src)}

    # Earliness: the selected model and the benchmarks at each as-of date.
    early = summary[summary["candidate"].isin([chosen, "nass_latest", "persistence"])].copy()
    early["selected_model"] = chosen

    # Intervals and the 2026 forecast for the selected model.
    sel_rows = backtest[(backtest["candidate"] == chosen) & (backtest["asof"] == HEADLINE)]
    model = error_model(sel_rows)
    cover = coverage(sel_rows)
    f_preds, f_info = all_predictions(src, table, [FORECAST_YEAR], HEADLINE)
    inp26 = table[(FORECAST_YEAR, HEADLINE)]["inputs"]
    fc = f_preds[FORECAST_YEAR][chosen].reindex(inp26.index)
    band = bounds(fc["pred"], inp26["G_last"], model)
    forecast = pd.DataFrame({"state": inp26.index, "year": FORECAST_YEAR, "asof": f"{FORECAST_YEAR}-11-15",
                             "candidate": chosen, "pred": fc["pred"].to_numpy(), "lo80": band["lo80"].to_numpy(),
                             "hi80": band["hi80"].to_numpy(), "method": fc["method"].astype(str).to_numpy(),
                             "planted_asof": inp26["Pa"].to_numpy(), "planted_report": inp26["Pa_report"].to_numpy()})
    total = forecast["pred"].sum()
    half = Z80 * model["us_rms_log"]
    us_row = {"state": "US (sum of 41 states)", "year": FORECAST_YEAR, "asof": f"{FORECAST_YEAR}-11-15",
              "candidate": chosen, "pred": total, "lo80": total * np.exp(-half), "hi80": total * np.exp(half),
              "method": "sum; US interval exp(+-1.2816 x RMS of yearly US log errors)"}
    forecast = pd.concat([pd.DataFrame([us_row]), forecast.sort_values("pred", ascending=False)], ignore_index=True)
    all26 = pd.DataFrame({name: frame.reindex(inp26.index)["pred"] for name, frame in f_preds[FORECAST_YEAR].items()})
    all26.loc["US (sum of 41 states)"] = all26.sum()

    # Write.
    cols = ["state", "year", "asof", "candidate", "pred", "actual", "method", "G_last"]
    backtest.assign(tier=backtest["candidate"].map(tier_label))[cols + ["tier"]].to_csv(
        OUT / "backtest_by_state_year.csv", index=False, lineterminator="\n")
    by_year.to_csv(OUT / "by_year.csv", index=False, lineterminator="\n")
    summary.to_csv(OUT / "summary.csv", index=False, lineterminator="\n")
    comps.to_csv(OUT / "comparisons.csv", index=False, lineterminator="\n")
    early.to_csv(OUT / "earliness.csv", index=False, lineterminator="\n")
    pd.DataFrame(fit_info + f_info).to_csv(OUT / "fitted_weights.csv", index=False, lineterminator="\n")
    sign_check(fit_info + f_info).to_csv(OUT / "fitted_sign_check.csv", index=False, lineterminator="\n")
    posthoc_vs_fsa_only(src, table, by_year, chosen, keys).to_csv(OUT / "posthoc_selected_vs_fsa_only_g3.csv",
                                                                   index=False, lineterminator="\n")
    pd.DataFrame(fsa_used).to_csv(OUT / "fsa_files_used.csv", index=False, lineterminator="\n")
    pa_rows = []
    for (t, key), item in table.items():
        inp = item["inputs"]
        pa_rows.append(pd.DataFrame({"year": t, "asof": key, "state": inp.index, "planted_asof": inp["Pa"].to_numpy(),
                                     "period": inp["Pa_period"].to_numpy(), "report": inp["Pa_report"].to_numpy()}))
    pd.concat(pa_rows).to_csv(OUT / "planted_asof_used.csv", index=False, lineterminator="\n")
    forecast.round({"pred": -2, "lo80": -2, "hi80": -2}).to_csv(OUT / "forecast_2026.csv", index=False,
                                                                 lineterminator="\n")
    all26.round(-2).rename_axis("state").to_csv(OUT / "forecast_2026_all_candidates.csv", lineterminator="\n")
    (OUT / "selection.json").write_text(json.dumps({"selection": selection, "selected_headline": chosen},
                                                   indent=1) + "\n", encoding="utf-8")
    (OUT / "reproduction.json").write_text(json.dumps(repro, indent=1) + "\n", encoding="utf-8")
    (OUT / "intervals.json").write_text(json.dumps({"selected": chosen, "error_model": model,
                                                    "leave_one_year_out": cover}, indent=1) + "\n", encoding="utf-8")
    feature_cover = {}
    for (t, key), item in table.items():
        if key == HEADLINE:
            inp = item["inputs"]
            feature_cover[str(t)] = {c: round(float(inp[c].notna().mean()), 3) for c in ["Pa", "sig_cur", *FEATURES]}
    (OUT / "inputs_audit.json").write_text(json.dumps({
        "candidates": {k: {"role": v["role"], "tier": tier_label(k), "sources": v["sources"]}
                       for k, v in CANDIDATES.items()},
        "sources": {k: {"tier": v[0], "description": v[1]} for k, v in SOURCES.items()},
        "forbidden_for_b_models": sorted(FORBIDDEN),
        "share_of_states_with_input_nov": feature_cover, "daniel_b4": daniel_meta}, indent=1) + "\n", encoding="utf-8")

    pd.set_option("display.width", 200)
    show = summary[summary["asof"] == HEADLINE].sort_values(["period", "mean_state_wape_pct"])
    print(show[["candidate", "period", "n_years", "mean_state_wape_pct", "mean_abs_us_error_pct",
                "mean_signed_us_error_pct"]].round(3).to_string(index=False))
    print("selection:", json.dumps(selection[HEADLINE]))
    print("reproduction:", json.dumps(repro["benchmarks_2017_2024"]))
    print("2026 US:", round(total), "80%:", round(total * np.exp(-half)), round(total * np.exp(half)))

    if args.score_2025:
        target = OUT / "score_2025_information_only.json"
        if target.exists():
            raise SystemExit(f"{target} exists: the 2025 score is computed once and never overwritten")
        p25, _ = all_predictions(src, table, [SCORING_YEAR], HEADLINE)
        inp25 = table[(SCORING_YEAR, HEADLINE)]["inputs"]
        actual = truth(src.finals, SCORING_YEAR).reindex(inp25.index)
        frames25 = {chosen: p25[SCORING_YEAR][chosen]["pred"].reindex(inp25.index),
                    "nass_latest": nass_benchmark(inseason, src.finals, SCORING_YEAR, HEADLINE).reindex(inp25.index),
                    "persistence": inp25["G_last"]}
        result = {"note": "information only; computed once after selection; never used to change anything",
                  "selected": chosen,
                  **{name: year_errors(pred, actual) for name, pred in frames25.items()}}
        states = pd.DataFrame({"state": inp25.index, "actual": actual.to_numpy(),
                               **{name: pred.to_numpy() for name, pred in frames25.items()}})
        states.to_csv(OUT / "score_2025_information_only.csv", index=False, lineterminator="\n")
        target.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print("2025 (information only):", json.dumps(result))


if __name__ == "__main__":
    main()
