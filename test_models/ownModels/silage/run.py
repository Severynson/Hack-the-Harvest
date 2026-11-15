"""Own state corn-for-silage acreage models that use no current-year NASS information, backtested 2012-2024.

The pre-registration (candidates, inputs, tiers, selection rule) is README.md section 1, hashed in
out/preregistration.sha256 before the first score. This module implements exactly that text.

Tier A inputs for target year t: NASS FINAL state acres of years before t (through ``NassHistory``, which refuses
year t or later), FSA crop acreage files published by the as-of date (through ``kernelag.fsa.latest_file`` /
``usable_files``), RMA insured acres by type and causes of loss, and the US Drought Monitor. Tier B adds NASS weekly
crop condition. ``check_tiers`` refuses a Tier A candidate with any other input.

Candidates (README 1.3): s0_persistence, s1_reversion_only (the incumbent's algorithm via
``kernelag.state_model.fit_ridge``), s2_fsa_ratio_highcov, s3_fsa_residual, s4_reversion_plus_switch,
s5_fsa_silage_share, s6_highcov_plus_switch; Tier B b4_switch_plus_condition; diagnostics d3_raw_residual and
d_oracle_final_residual (uses year-t NASS finals: a ceiling, never a model).

Outputs (out/): backtest_by_state_year.csv, by_year.csv, summary.csv, comparisons.csv, selection.json,
reproduction.json, fitted_params.csv, inputs_used.csv, s3_residual_diagnostics.csv, forecast_2026.csv,
forecast_2026_all_candidates.csv, run.json; post-hoc checks that never feed the selection: by_region.csv,
reference_nass_input_models.csv, sensitivity_publication_lag10.csv (+ _inputs.csv); with --score-2025 (once):
score_2025_information_only.csv/.json.

Run from the repo root:
    .venv/Scripts/python.exe test_models/ownModels/silage/run.py
    .venv/Scripts/python.exe test_models/ownModels/silage/run.py --score-2025     (one time only)
"""

from __future__ import annotations

import argparse
import hashlib
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
from kernelag.context import drought as ctx_drought
from kernelag.context import loss_share as ctx_loss_share
from kernelag.context import poor_condition as ctx_poor_condition
from kernelag.state_model import add_intervals as sm_add_intervals
from kernelag.state_model import (
    error_quantiles,
    fit_ridge,
    interval_coverage,
    region_of,
)

OUT = HERE / "out"
DATA = REPO / "data"
QUICKSTATS = DATA / "Quickstats Data"
README = HERE / "README.md"
PREREG_START, PREREG_END = "## 1. Pre-registration", "<!-- END OF PRE-REGISTRATION -->"

FIRST_TEST, LAST_TEST = 2012, 2024
PERIODS = {"2012-2024": (2012, 2024), "2017-2024": (2017, 2024)}
SCORING_YEAR, FORECAST_YEAR = 2025, 2026
MAX_FINAL_YEAR = 2025          # NASS finals exist through 2025; a 2026 "YEAR" value in Quick Stats is in-season
ASOF = {"sep": (9, 15), "oct": (10, 15), "nov": (11, 15)}
PRIMARY_ASOF = "nov"
H00, H13 = 2000, 2013          # first NASS final year in each history variant
MIN_FIT_YEARS = 3
FSA_FLOOR = 500.0              # acres: a ratio's denominator below this is not used
COVERAGE_GATE = 0.75
CLIP = (0.5, 2.0)
LOG_CLIP = float(np.log(2.0))
W_GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.05), 2)
S3_TRAIN_FROM, S4_TRAIN_FROM = 2012, 2005
FIRST_FSA_YEAR = 2011
N_BOOT, SEED = 10_000, 20261114
TIE = 1e-9                     # WAPE points: a smaller paired difference is a tie (same predictions)
SENSITIVITY_LAG_DAYS = 10      # post-hoc check: FSA files published 10 days after their data date, not 5
STORED_NASS_INPUT_MODELS = ["nass_acres", "stress", "all_public"]   # team models that read year-t NASS figures
SWITCH_FEATURES = ["d_drought", "d_loss", "d_fsa_silage", "d_rma_silage"]
CONDITION_FEATURE = "d_poor"

# --- independence tiers ---------------------------------------------------------------------------------------

INPUTS = {
    "nass_final_history": ("NASS final state acres (silage, grain, planted) for years before t", "A"),
    "fsa_acreage": ("FSA crop acreage files published by the as-of date (farmer certifications)", "A"),
    "rma_insured_by_type": ("RMA Summary of Business insured acres by type (silage type 026)", "A"),
    "rma_cause_of_loss": ("RMA cause of loss, weather causes, months before the as-of month", "A"),
    "drought_monitor": ("US Drought Monitor state D2+ share", "A"),
    "nass_crop_condition": ("NASS weekly corn condition of year t", "B"),
    "nass_final_target_year": ("NASS final planted and grain acres of year t itself", "forbidden"),
}
ALLOWED_INPUT_TIERS = {"A": {"A"}, "benchmark": {"A"}, "B": {"A", "B"}, "forbidden": {"A", "B", "forbidden"}}
HISTORY = ["nass_final_history"]
CANDIDATES = {
    "s0_persistence": {"tier": "benchmark", "inputs": HISTORY, "eligible": False},
    "s1_incumbent_H13": {"tier": "benchmark", "inputs": HISTORY, "eligible": False},
    "s1_reversion_only": {"tier": "A", "inputs": HISTORY, "eligible": True},
    "s2_fsa_ratio_highcov": {"tier": "A", "inputs": HISTORY + ["fsa_acreage"], "eligible": True},
    "s3_fsa_residual": {"tier": "A", "inputs": HISTORY + ["fsa_acreage"], "eligible": True},
    "s4_reversion_plus_switch": {"tier": "A", "eligible": True, "inputs": HISTORY + [
        "fsa_acreage", "rma_insured_by_type", "rma_cause_of_loss", "drought_monitor"]},
    "s5_fsa_silage_share": {"tier": "A", "inputs": HISTORY + ["fsa_acreage"], "eligible": True},
    "s6_highcov_plus_switch": {"tier": "A", "eligible": True, "inputs": HISTORY + [
        "fsa_acreage", "rma_insured_by_type", "rma_cause_of_loss", "drought_monitor"]},
    "b4_switch_plus_condition": {"tier": "B", "eligible": False, "inputs": HISTORY + [
        "fsa_acreage", "rma_insured_by_type", "rma_cause_of_loss", "drought_monitor", "nass_crop_condition"]},
    "d3_raw_residual": {"tier": "A", "inputs": HISTORY + ["fsa_acreage"], "eligible": False, "diagnostic": True},
    "d_oracle_final_residual": {"tier": "forbidden", "inputs": HISTORY + ["nass_final_target_year"],
                                "eligible": False, "diagnostic": True},
}
SELECTION_ORDER = ["s2_fsa_ratio_highcov", "s5_fsa_silage_share", "s3_fsa_residual", "s4_reversion_plus_switch",
                   "s6_highcov_plus_switch"]
SIMPLEST = "s1_reversion_only"


def check_tiers(candidates: dict = CANDIDATES) -> None:
    """Refuse any candidate whose inputs exceed its tier, and any eligible candidate that is not Tier A."""
    for name, spec in candidates.items():
        allowed = ALLOWED_INPUT_TIERS[spec["tier"]]
        for key in spec["inputs"]:
            if INPUTS[key][1] not in allowed:
                raise ValueError(f"{name} is tier {spec['tier']} but uses {key} (tier {INPUTS[key][1]})")
        if spec["eligible"] and spec["tier"] != "A":
            raise ValueError(f"{name} is eligible for selection but is tier {spec['tier']}")


class LookAheadError(RuntimeError):
    """A model asked for NASS acres of its own target year or later."""


class NassHistory:
    """NASS final state acres as a forecast for ``target_year`` may see them: years ``start``..t-1 only."""

    def __init__(self, finals: pd.DataFrame, states: list[str], target_year: int, start: int = H00):
        self.t, self.start = target_year, start
        visible = finals[(finals["year"] >= start) & (finals["year"] < target_year)]
        self._wide = {series: visible.pivot(index="state", columns="year", values=series).reindex(states)
                      for series in ("silage", "grain", "planted")}
        self.states = states

    def get(self, series: str, year: int) -> pd.Series:
        if year >= self.t:
            raise LookAheadError(f"{series} {year} requested by a forecast for {self.t}")
        wide = self._wide[series]
        if year in wide.columns:
            return wide[year].astype(float)
        return pd.Series(np.nan, index=pd.Index(self.states, name="state"), dtype=float)

    def long(self, series: str) -> pd.DataFrame:
        """All visible years of one series as rows of state, year, value."""
        return self._wide[series].stack().rename("value").rename_axis(["state", "year"]).reset_index()


# --- loading ----------------------------------------------------------------------------------------------------

def load_nass_finals() -> tuple[pd.DataFrame, list[str]]:
    """NASS final state acres 2000-2025 (Quick Stats "YEAR" values), checked against the incumbent's truth file."""
    items = {"silage": ("corn_silage_harvested_acres_state_2000_2026.csv", "CORN, SILAGE - ACRES HARVESTED"),
             "grain": ("corn_grain_harvested_acres_state_2000_2026.csv", "CORN, GRAIN - ACRES HARVESTED"),
             "planted": ("corn_planted_acres_state_2000_2026.csv", "CORN - ACRES PLANTED")}
    parts = []
    for series, (name, item) in items.items():
        raw = pd.read_csv(QUICKSTATS / name, dtype=str, keep_default_na=False)
        rows = raw[(raw["source_desc"] == "SURVEY") & (raw["reference_period_desc"] == "YEAR")
                   & (raw["short_desc"] == item) & (raw["agg_level_desc"] == "STATE") & (raw["domain_desc"] == "TOTAL")]
        value = pd.to_numeric(rows["Value"].str.replace(",", "").str.strip(), errors="coerce")
        parts.append(pd.DataFrame({"state": rows["state_name"].to_numpy(), "year": rows["year"].astype(int).to_numpy(),
                                   "series": series, "acres": value.to_numpy()}))
    long = pd.concat(parts, ignore_index=True).dropna(subset=["acres"])
    long = long[long["year"] <= MAX_FINAL_YEAR].drop_duplicates(["state", "year", "series"])

    incumbent = pd.read_csv(DATA / "nass" / "corn_acres_state.csv")
    final = incumbent[incumbent["period"] == "final"]
    states = sorted(final.loc[final["series"] == "silage", "state"].unique())
    long = long[long["state"].isin(states)]
    merged = final[["state", "year", "series", "acres"]].merge(long, on=["state", "year", "series"], how="left",
                                                                 suffixes=("_incumbent", "_quickstats"))
    bad = merged[merged["acres_quickstats"].isna() | (merged["acres_incumbent"] != merged["acres_quickstats"])]
    if len(bad):
        raise ValueError(f"Quick Stats finals differ from data/nass/corn_acres_state.csv in {len(bad)} rows")
    wide = long.pivot_table(index=["state", "year"], columns="series", values="acres", aggfunc="first").reset_index()
    return wide, states


def truth(finals: pd.DataFrame, year: int) -> pd.Series:
    """NASS final silage acres of ``year``: used only to score and to diagnose, never by a model for that year."""
    rows = finals[finals["year"] == year].set_index("state")["silage"]
    return rows.astype(float)


def load_fsa() -> tuple[pd.DataFrame, pd.DataFrame]:
    """FSA file table and field-corn planted acres per file and state, columns silage, grain and all uses."""
    files = pd.read_csv(DATA / "fsa" / "fsa_files.csv")
    state = pd.read_csv(DATA / "fsa" / "fsa_corn_state.csv", dtype={"state_fips": str, "data_as_of": str})
    wide = state.pivot_table(index=["crop_year", "data_as_of", "state"], columns="intended_use",
                             values="planted_acres", aggfunc="sum")
    wide = wide.fillna(0.0)   # a use missing for a state in a file it appears in has no acres
    acres = pd.DataFrame({"silage": wide.get("silage", 0.0), "grain": wide.get("grain", 0.0),
                          "all": wide.sum(axis=1)})
    return files, acres


def fsa_file_acres(acres: pd.DataFrame, row: pd.Series | None, states: list[str]) -> pd.DataFrame:
    """Silage, grain and all-use planted acres by state for one FSA file (NaN when there is no file)."""
    empty = pd.DataFrame(np.nan, index=pd.Index(states, name="state"), columns=["silage", "grain", "all"])
    if row is None:
        return empty
    key = (int(row["crop_year"]), str(row["data_as_of"]))
    if key not in acres.index.droplevel("state").unique():
        raise KeyError(f"FSA file {row['zip_name']} ({key}) has status ok but no rows in fsa_corn_state.csv")
    return acres.loc[key].reindex(states)


def fsa_inputs(files: pd.DataFrame, acres: pd.DataFrame, asof: date, year: int, states: list[str]):
    """In-season FSA acres of ``year`` as of ``asof`` and the final file of ``year - 1``, with what was used."""
    current = kfsa.latest_file(files, asof, year)
    usable = kfsa.usable_files(files, asof, year)
    previous = usable[usable["crop_year"] == year - 1]
    finals = previous[previous["vintage"].astype(str).str.startswith("final")]
    chosen = finals if not finals.empty else previous
    prior = chosen.sort_values("data_as_of").iloc[-1] if not chosen.empty else None
    for row in (current, prior):
        if row is not None and pd.Timestamp(row["assumed_published"]) > pd.Timestamp(asof):
            raise LookAheadError(f"FSA file {row['zip_name']} published after {asof}")
    meta = {"year": year, "asof": asof.isoformat()}
    for label, row in (("current", current), ("prior_final", prior)):
        meta[f"{label}_zip"] = None if row is None else row["zip_name"]
        meta[f"{label}_data_as_of"] = None if row is None else row["data_as_of"]
        meta[f"{label}_published"] = None if row is None else row["assumed_published"]
        meta[f"{label}_vintage"] = None if row is None else row["vintage"]
    return fsa_file_acres(acres, current, states), fsa_file_acres(acres, prior, states), meta


def _read_folder(folder: Path, columns: list[str]) -> pd.DataFrame:
    files = sorted(folder.glob("*.csv*"))
    if not files:
        raise FileNotFoundError(f"no files in {folder}")
    return pd.concat([pd.read_csv(f, dtype=str, usecols=columns) for f in files], ignore_index=True)


def load_season_inputs() -> dict:
    """Raw tables for drought, RMA (losses and insured acres) and, for Tier B only, NASS corn condition."""
    insured = _read_folder(DATA / "rma" / "insured_by_type_corn", [
        "commodity_year", "state_abbreviation", "type_code", "reporting_level_type", "net_reporting_level_amount"])
    cause = _read_folder(DATA / "rma" / "cause_of_loss_corn", [
        "commodity_year", "state_abbreviation", "cause_of_loss_code", "month_of_loss", "net_determined_quantity"])
    usdm = pd.read_csv(next((DATA / "drought").glob("usdm_state_weekly_2000_2026.csv*")))
    condition = pd.read_csv(next(QUICKSTATS.glob("corn_condition_weekly_state_2000_2026.csv*")),
                            dtype=str, keep_default_na=False)
    return {"insured": insured, "cause": cause, "usdm": usdm, "condition": condition}


def rma_silage_acres(insured: pd.DataFrame) -> pd.Series:
    """RMA net reported acres of corn type 026 (Silage) by state and year, all plans summed."""
    from kernelag.context import STATE_NAMES
    rows = insured[(insured["reporting_level_type"].astype(str).str.strip() == "Acres")
                   & (insured["type_code"].astype(str).str.strip() == "026")]
    state = rows["state_abbreviation"].astype(str).str.strip().map(STATE_NAMES)
    acres = pd.to_numeric(rows["net_reporting_level_amount"], errors="coerce")
    year = rows["commodity_year"].astype(int)
    return acres.groupby([state.to_numpy(), year.to_numpy()]).sum().rename_axis(["state", "year"])


def season_features(raw: dict, asof_key: str) -> pd.DataFrame:
    """Drought D2+ share, insured weather-loss share and (Tier B) poor-condition share by state and year."""
    parts = [ctx_drought(raw["usdm"], asof_key), ctx_loss_share(raw["cause"], raw["insured"], asof_key),
             ctx_poor_condition(raw["condition"], asof_key)]
    table = parts[0]
    for part in parts[1:]:
        table = table.merge(part, on=["state", "year"], how="outer")
    return table.set_index(["state", "year"])


# --- the rows every model reads -------------------------------------------------------------------------------

def _clipped_log_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = np.log(numerator / denominator.where(denominator >= FSA_FLOOR))
    return value.replace([np.inf, -np.inf], np.nan).clip(-LOG_CLIP, LOG_CLIP)


def _season_value(season: pd.DataFrame, column: str, states: list[str], year: int) -> pd.Series:
    """One season feature for every state in one year (NaN where absent), in ``states`` order."""
    if column not in season:
        return pd.Series(np.nan, index=pd.Index(states, name="state"))
    return season[column].reindex(pd.MultiIndex.from_product([states, [year]])).droplevel(1)


def build_rows(finals: pd.DataFrame, states: list[str], start: int, years: list[int], asof_key: str,
               fsa: tuple[pd.DataFrame, pd.DataFrame] | None, season: pd.DataFrame | None,
               rma_silage: pd.Series | None) -> tuple[pd.DataFrame, list[dict]]:
    """One row per state and target year with only what a forecast as of ``asof_key`` of that year may use."""
    month, day = ASOF[asof_key]
    frames, used = [], []
    for year in years:
        hist = NassHistory(finals, states, year, start)
        silage = {k: hist.get("silage", year - k) for k in (1, 2, 3, 4)}
        row = pd.DataFrame(index=pd.Index(states, name="state"))
        row["year"] = year
        row["S1"] = silage[1]
        with np.errstate(divide="ignore", invalid="ignore"):
            row["reversion"] = np.log(silage[1] / pd.concat([silage[2], silage[3], silage[4]], axis=1)
                                      .mean(axis=1, skipna=False))
        row["G1"], row["P1"] = hist.get("grain", year - 1), hist.get("planted", year - 1)
        if fsa is not None and year >= FIRST_FSA_YEAR:
            current, prior, meta = fsa_inputs(*fsa, date(year, month, day), year, states)
            used.append(meta | {"asof_key": asof_key})
        else:
            current = prior = pd.DataFrame(np.nan, index=row.index, columns=["silage", "grain", "all"])
        for use in ("silage", "grain", "all"):
            row[f"F_{use}_cur"], row[f"F_{use}_prev"] = current[use], prior[use]
        row["d_fsa_silage"] = _clipped_log_ratio(row["F_silage_cur"], row["F_silage_prev"])
        if season is not None:
            for feature, column in [("d_drought", "drought"), ("d_loss", "loss_share"), ("d_poor", "poor_condition")]:
                row[feature] = (_season_value(season, column, states, year)
                                - _season_value(season, column, states, year - 1)).to_numpy()
        if rma_silage is not None:
            now = rma_silage.reindex(pd.MultiIndex.from_product([states, [year]])).droplevel(1)
            last = rma_silage.reindex(pd.MultiIndex.from_product([states, [year - 1]])).droplevel(1)
            # a state with no silage-type rows has no insured silage acres in that year
            row["d_rma_silage"] = _clipped_log_ratio(now.fillna(0.0), last.fillna(0.0)).to_numpy()
        frames.append(row.reset_index())
    return pd.concat(frames, ignore_index=True), used


# --- models ---------------------------------------------------------------------------------------------------

def with_target(rows: pd.DataFrame, hist: NassHistory) -> pd.DataFrame:
    """``rows`` (all years before hist.t) with the NASS final silage of each row's year as ``actual``."""
    actual = hist.long("silage").rename(columns={"value": "actual"})
    return rows.merge(actual, on=["state", "year"], how="left")


def s1_out_of_sample(rows: pd.DataFrame, finals: pd.DataFrame, states: list[str], start: int):
    """The incumbent's reversion_only prediction for every year in ``rows``, each fitted on earlier years only."""
    preds, params = [], {}
    for year in sorted(rows["year"].unique()):
        hist = NassHistory(finals, states, year, start)
        train = with_target(rows[rows["year"] < year], hist)
        with np.errstate(divide="ignore", invalid="ignore"):
            train["target"] = np.log(train["actual"] / train["S1"])
        train = train[np.isfinite(train["target"])].rename(columns={"S1": "silage_last"})
        test = rows[(rows["year"] == year) & rows["S1"].notna()].rename(columns={"S1": "silage_last"})
        if train.empty:
            change, beta = np.zeros(len(test)), 0.0
        else:
            model = fit_ridge(train, ["reversion"])
            change, beta = model(test), float(model.weights["reversion"])
        params[int(year)] = {"s1_beta_per_std": beta, "s1_train_years": int(train["year"].nunique())}
        preds.append(pd.DataFrame({"state": test["state"].to_numpy(), "year": year,
                                   "pred": test["silage_last"].to_numpy() * np.exp(change)}))
    return pd.concat(preds, ignore_index=True), params


def s3_raw(rows: pd.DataFrame) -> pd.Series:
    """FSA non-grain residual ratio applied to last year's silage (NaN where it cannot be computed)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        planted_hat = rows["F_all_cur"] * rows["P1"] / rows["F_all_prev"]
        grain_hat = rows["F_grain_cur"] * rows["G1"] / rows["F_grain_prev"]
        residual_hat = planted_hat - grain_hat
        residual_last = rows["P1"] - rows["G1"]
        ok = (rows["G1"].notna() & (rows["F_all_prev"] > 0) & (rows["F_grain_prev"] > 0) & (residual_last > 0)
              & rows["F_all_cur"].notna() & rows["F_grain_cur"].notna() & rows["S1"].notna())
        ratio = (residual_hat / residual_last).clip(*CLIP)
    return (rows["S1"] * ratio).where(ok)


def fit_shrink_weight(train: pd.DataFrame) -> float:
    """The w in W_GRID minimizing sum abs(s1^(1-w) raw^w - actual) (smallest w on ties)."""
    errors = [np.abs(np.exp((1 - w) * np.log(train["s1"]) + w * np.log(train["raw"])) - train["actual"]).sum()
              for w in W_GRID]
    return float(W_GRID[int(np.argmin(errors))])


def candidate_predictions(rows: pd.DataFrame, finals: pd.DataFrame, states: list[str], start: int,
                          test_years: list[int]) -> tuple[pd.DataFrame, list[dict]]:
    """Every candidate's prediction for each test year, fitted parameters from earlier years only."""
    s1_all, s1_params = s1_out_of_sample(rows, finals, states, start)
    base = rows.merge(s1_all.rename(columns={"pred": "s1"}), on=["state", "year"], how="left")
    base["raw"] = s3_raw(base)
    out, params = [], []
    for year in test_years:
        hist = NassHistory(finals, states, year, start)
        train = with_target(base[base["year"] < year], hist)
        test = base[(base["year"] == year) & base["S1"].notna()].set_index("state")
        record = {"year": year, **s1_params.get(year, {})}

        # s3: one pooled shrink weight toward s1, fitted on 2012..t-1 at the same as-of date.
        s3_train = train[(train["year"] >= S3_TRAIN_FROM) & train["raw"].notna() & train["s1"].notna()
                         & train["actual"].notna()]
        w = fit_shrink_weight(s3_train) if s3_train["year"].nunique() >= MIN_FIT_YEARS else 0.0
        record.update(s3_w=w, s3_train_years=int(s3_train["year"].nunique()))

        # s4 and b4: pooled ridge on log(actual / s1), training years 2005..t-1.
        switch = {}
        for name, features in [("s4", SWITCH_FEATURES), ("b4", SWITCH_FEATURES + [CONDITION_FEATURE])]:
            fit_rows = train[(train["year"] >= S4_TRAIN_FROM) & train["s1"].notna() & train["actual"].notna()].copy()
            with np.errstate(divide="ignore", invalid="ignore"):
                fit_rows["target"] = np.log(fit_rows["actual"] / fit_rows["s1"])
            fit_rows = fit_rows[np.isfinite(fit_rows["target"])].rename(columns={"S1": "silage_last"})
            if fit_rows["year"].nunique() >= MIN_FIT_YEARS:
                model = fit_ridge(fit_rows, features)
                switch[name] = test["s1"] * np.exp(model(test))
                record.update({f"{name}_{k}": float(v) for k, v in model.weights.items()})
            else:
                switch[name] = test["s1"]
                record.update({f"{name}_{k}": 0.0 for k in features})
            record[f"{name}_train_years"] = int(fit_rows["year"].nunique())
        params.append(record)

        s1 = test["s1"]
        gate = (test["F_silage_prev"] >= FSA_FLOOR) & (test["F_silage_prev"] / test["S1"] >= COVERAGE_GATE) \
            & test["F_silage_cur"].notna()
        fsa_ratio = test["S1"] * (test["F_silage_cur"] / test["F_silage_prev"]).clip(*CLIP)
        s2 = fsa_ratio.where(gate, s1)
        raw = test["raw"]
        s3 = s1 if w == 0 else np.exp((1 - w) * np.log(s1) + w * np.log(raw)).where(raw.notna(), s1)
        share_ok = (test["F_silage_prev"] >= FSA_FLOOR) & (test["F_all_prev"] > 0) & (test["F_all_cur"] > 0) \
            & test["F_silage_cur"].notna()
        with np.errstate(divide="ignore", invalid="ignore"):
            share_ratio = ((test["F_silage_cur"] / test["F_all_cur"])
                           / (test["F_silage_prev"] / test["F_all_prev"])).clip(*CLIP)
        s5 = (test["S1"] * share_ratio).where(share_ok, s1)
        s6 = fsa_ratio.where(gate, switch["s4"])
        preds = {"s0_persistence": test["S1"], "s1_reversion_only": s1, "s2_fsa_ratio_highcov": s2,
                 "s3_fsa_residual": s3, "s4_reversion_plus_switch": switch["s4"], "s5_fsa_silage_share": s5,
                 "s6_highcov_plus_switch": s6, "b4_switch_plus_condition": switch["b4"],
                 "d3_raw_residual": raw.where(raw.notna(), s1)}
        for name, series in preds.items():
            out.append(pd.DataFrame({"state": series.index, "year": year, "candidate": name,
                                     "pred": series.to_numpy(dtype=float)}))
        gated = test.index[gate].tolist()
        record.update(s2_gated_states=";".join(gated), s2_n_gated=len(gated),
                      s3_states_with_raw=int(raw.notna().sum()))
    return pd.concat(out, ignore_index=True), params


def oracle_predictions(finals: pd.DataFrame, states: list[str], years: list[int]) -> pd.DataFrame:
    """Diagnostic only (forbidden tier): S(t-1) x R(t) / R(t-1) with R from NASS FINAL planted minus grain."""
    rows = []
    for year in years:
        now = finals[finals["year"] == year].set_index("state").reindex(states)        # year-t finals: forbidden
        last = finals[finals["year"] == year - 1].set_index("state").reindex(states)
        r_now, r_last = now["planted"] - now["grain"], last["planted"] - last["grain"]
        ok = r_now.notna() & (r_last > 0)
        pred = (last["silage"] * r_now / r_last).where(ok, np.nan)
        rows.append(pd.DataFrame({"state": states, "year": year, "candidate": "d_oracle_final_residual",
                                  "pred": pred.to_numpy(), "oracle_ok": ok.to_numpy()}))
    return pd.concat(rows, ignore_index=True)


# --- scoring --------------------------------------------------------------------------------------------------

def score_table(preds: pd.DataFrame) -> pd.DataFrame:
    """Per candidate and year: state WAPE (percent), US error (percent, signed) and the number of states."""
    rows = []
    for (name, year), group in preds.groupby(["candidate", "year"], sort=True):
        miss = group["pred"] - group["actual"]
        rows.append({"candidate": name, "year": int(year), "n_states": len(group),
                     "state_wape_pct": 100 * miss.abs().sum() / group["actual"].sum(),
                     "us_error_pct": 100 * miss.sum() / group["actual"].sum()})
    return pd.DataFrame(rows)


def summarise(by_year: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, (lo, hi) in PERIODS.items():
        part = by_year[by_year["year"].between(lo, hi)]
        for (asof, name), group in part.groupby(["asof_key", "candidate"]):
            spec = CANDIDATES[name]
            rows.append({"candidate": name, "asof_key": asof, "period": period, "n_years": len(group),
                         "mean_state_wape_pct": group["state_wape_pct"].mean(),
                         "mean_abs_us_error_pct": group["us_error_pct"].abs().mean(),
                         "mean_signed_us_error_pct": group["us_error_pct"].mean(),
                         "tier": spec["tier"], "eligible": spec["eligible"],
                         "diagnostic": spec.get("diagnostic", False)})
    return pd.DataFrame(rows)


def bootstrap_ci(diffs: np.ndarray, n: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    """90% percentile interval of the mean of paired yearly differences, resampling years."""
    rng = np.random.default_rng(seed)
    draws = diffs[rng.integers(0, len(diffs), size=(n, len(diffs)))].mean(axis=1)
    return float(np.percentile(draws, 5)), float(np.percentile(draws, 95))


def comparisons(by_year: pd.DataFrame, asof_key: str = PRIMARY_ASOF) -> pd.DataFrame:
    part = by_year[by_year["asof_key"] == asof_key]
    wide_wape = part.pivot(index="year", columns="candidate", values="state_wape_pct")
    wide_us = part.pivot(index="year", columns="candidate", values="us_error_pct").abs()
    rows = []
    for period, (lo, hi) in PERIODS.items():
        comparators = {"a_incumbent": "s1_incumbent_H13" if lo >= 2017 else SIMPLEST,
                       "b_persistence": "s0_persistence", "c_simplest_own": SIMPLEST}
        for name in wide_wape.columns:
            for label, other in comparators.items():
                if other == name or other not in wide_wape.columns:
                    continue
                if label == "a_incumbent" and other == SIMPLEST:
                    continue        # before 2017 the incumbent cannot run: (a) is the same model as (c)
                for metric, wide in [("state_wape", wide_wape), ("abs_us_error", wide_us)]:
                    paired = wide.loc[lo:hi, [name, other]].dropna()
                    if paired.empty:
                        continue
                    diff = (paired[name] - paired[other]).to_numpy()
                    ci = bootstrap_ci(diff)
                    rows.append({"candidate": name, "period": period, "comparator_role": label, "comparator": other,
                                 "metric": metric, "n_years": len(diff), "mean_candidate": paired[name].mean(),
                                 "mean_comparator": paired[other].mean(), "mean_diff_points": diff.mean(),
                                 "ci90_lo": ci[0], "ci90_hi": ci[1], "years_better": int((diff < -TIE).sum()),
                                 "years_worse": int((diff > TIE).sum()),
                                 "se_paired": float(diff.std(ddof=1) / np.sqrt(len(diff))) if len(diff) > 1 else np.nan})
    return pd.DataFrame(rows)


def select(by_year: pd.DataFrame, period: str = "2012-2024", asof_key: str = PRIMARY_ASOF) -> dict:
    """The pre-registered two-standard-error rule against s1 (README 1.5)."""
    lo, hi = PERIODS[period]
    part = by_year[(by_year["asof_key"] == asof_key) & by_year["year"].between(lo, hi)]
    wide = part.pivot(index="year", columns="candidate", values="state_wape_pct")
    table = {}
    for name in SELECTION_ORDER:
        diff = (wide[name] - wide[SIMPLEST]).dropna().to_numpy()
        se = float(diff.std(ddof=1) / np.sqrt(len(diff)))
        table[name] = {"mean_wape": float(wide[name].mean()), "mean_diff_vs_s1": float(diff.mean()), "se": se,
                       "upper_2se": float(diff.mean() + 2 * se), "qualifies": bool(diff.mean() + 2 * se < 0),
                       "n_years": len(diff)}
    qualifying = [n for n in SELECTION_ORDER if table[n]["qualifies"]]
    selected = min(qualifying, key=lambda n: (table[n]["mean_wape"], SELECTION_ORDER.index(n))) if qualifying \
        else SIMPLEST
    return {"period": period, "asof_key": asof_key, "s1_mean_wape": float(wide[SIMPLEST].mean()),
            "candidates": table, "qualifying": qualifying, "selected": selected}


# --- pipeline -------------------------------------------------------------------------------------------------

def run_asof(asof_key: str, finals, states, fsa, raw, rma_silage, years_to_predict):
    """All candidates (H00) for the test years, as of ``asof_key`` in each year."""
    season = season_features(raw, asof_key)
    rows, used = build_rows(finals, states, H00, list(range(H00 + 1, max(years_to_predict) + 1)), asof_key,
                            fsa, season, rma_silage)
    preds, params = candidate_predictions(rows, finals, states, H00, years_to_predict)
    preds["asof_key"] = asof_key
    for record in params:
        record["asof_key"] = asof_key
    return preds, params, used, rows


def attach_truth(preds: pd.DataFrame, finals: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """Backtest rows only (years up to LAST_TEST): add the actual and last year's acres."""
    part = preds[preds["year"] <= LAST_TEST].copy()
    actual = finals[["state", "year", "silage"]].rename(columns={"silage": "actual"})
    part = part.merge(actual, on=["state", "year"], how="left")
    part = part.merge(rows[["state", "year", "S1"]].rename(columns={"S1": "last"}), on=["state", "year"], how="left")
    return part[part["actual"].notna() & part["last"].notna()]


def reproduce_incumbent(finals: pd.DataFrame, states: list[str]) -> tuple[pd.DataFrame, dict]:
    """s1 on H13 (the incumbent's panel) and persistence, against data/models/state_model_backtest.csv."""
    rows, _ = build_rows(finals, states, H13, list(range(H13, LAST_TEST + 1)), PRIMARY_ASOF, None, None, None)
    s1, _ = s1_out_of_sample(rows, finals, states, H13)
    s1 = s1[s1["year"].between(2017, LAST_TEST)].assign(candidate="s1_incumbent_H13")
    persistence = rows[rows["year"].between(2017, LAST_TEST) & rows["S1"].notna()]
    persistence = persistence[["state", "year"]].assign(candidate="s0_persistence_H13", pred=persistence["S1"])
    both = pd.concat([s1, persistence], ignore_index=True).merge(
        finals[["state", "year", "silage"]].rename(columns={"silage": "actual"}), on=["state", "year"])
    mine = score_table(both)
    stored = pd.read_csv(DATA / "models" / "state_model_backtest.csv")
    stored = stored[(stored["scope"] == "all_states") & (stored["series"] == "silage")]
    names = {"s1_incumbent_H13": "reversion_only", "s0_persistence_H13": "same_as_last_year"}
    report = {}
    for mine_name, stored_name in names.items():
        a = mine[mine["candidate"] == mine_name].set_index("year")
        b = stored[stored["predictor"] == stored_name].set_index("year")
        joined = a.join(b[["state_error_pct", "total_error_pct"]], how="inner")
        exact = bool((joined["state_wape_pct"].round(2) == joined["state_error_pct"]).all()
                     and (joined["us_error_pct"].round(2) == joined["total_error_pct"]).all()
                     and len(joined) == 8)
        report[mine_name] = {"stored_predictor": stored_name, "years": [int(y) for y in joined.index],
                             "mine_state_wape": joined["state_wape_pct"].round(2).tolist(),
                             "stored_state_wape": joined["state_error_pct"].tolist(),
                             "mine_us_error": joined["us_error_pct"].round(2).tolist(),
                             "stored_us_error": joined["total_error_pct"].tolist(),
                             "mean_state_wape_mine": round(float(joined["state_wape_pct"].mean()), 4),
                             "mean_state_wape_stored": round(float(joined["state_error_pct"].mean()), 4),
                             "exact_to_2dp": exact}
    return s1, report


def preregistration_status() -> dict:
    text = README.read_text(encoding="utf-8")
    section = text[text.index(PREREG_START): text.index(PREREG_END) + len(PREREG_END)]
    now = hashlib.sha256(section.encode("utf-8")).hexdigest()
    stored_file = OUT / "preregistration.sha256"
    stored = stored_file.read_text(encoding="utf-8").split()[0] if stored_file.exists() else None
    return {"sha256_now": now, "sha256_stored": stored, "unchanged": now == stored}


def residual_diagnostics(rows: pd.DataFrame, finals: pd.DataFrame) -> pd.DataFrame:
    """How far the FSA residual (s3's input) is from NASS's final residual, by year (diagnostic, uses year-t finals)."""
    out = []
    for year in range(FIRST_TEST, LAST_TEST + 1):
        part = rows[rows["year"] == year].set_index("state")
        now = finals[finals["year"] == year].set_index("state").reindex(part.index)
        with np.errstate(divide="ignore", invalid="ignore"):
            planted_hat = part["F_all_cur"] * part["P1"] / part["F_all_prev"]
            grain_hat = part["F_grain_cur"] * part["G1"] / part["F_grain_prev"]
        ok = planted_hat.notna() & grain_hat.notna() & now["grain"].notna() & (part["P1"] - part["G1"] > 0)
        residual_true, residual_last = (now["planted"] - now["grain"])[ok], (part["P1"] - part["G1"])[ok]
        residual_hat = (planted_hat - grain_hat)[ok]
        out.append({"year": year, "n_states": int(ok.sum()),
                    "planted_abs_err_pct_of_planted": 100 * (planted_hat[ok] - now["planted"][ok]).abs().sum()
                    / now["planted"][ok].sum(),
                    "grain_abs_err_pct_of_grain": 100 * (grain_hat[ok] - now["grain"][ok]).abs().sum()
                    / now["grain"][ok].sum(),
                    "residual_abs_err_pct_of_residual": 100 * (residual_hat - residual_true).abs().sum()
                    / residual_true.sum(),
                    "persistence_residual_abs_err_pct": 100 * (residual_last - residual_true).abs().sum()
                    / residual_true.sum(),
                    "grain_abs_err_pct_of_residual": 100 * (grain_hat[ok] - now["grain"][ok]).abs().sum()
                    / residual_true.sum(),
                    "residual_sum": float(residual_true.sum()), "planted_sum": float(now["planted"][ok].sum())})
    return pd.DataFrame(out)


def forecast_with_intervals(preds: pd.DataFrame, rows: pd.DataFrame, held_out: pd.DataFrame, name: str,
                            year: int) -> tuple[pd.DataFrame, dict]:
    """State and US forecast of one candidate with 80% (and 90%) intervals from its backtest errors."""
    part = preds[(preds["candidate"] == name) & (preds["year"] == year)].set_index("state")["pred"]
    last = rows[rows["year"] == year].set_index("state")["S1"]
    errors = error_quantiles(held_out)
    bounds = sm_add_intervals(part, last, errors, "silage")
    table = pd.DataFrame({"silage": part}).join(bounds)
    table["silage_last_year"] = last.reindex(table.index)
    totals = held_out.groupby("year")[["actual", "predicted"]].sum()
    us_log = np.log(totals["actual"] / totals["predicted"]).to_numpy()
    q10, q90 = np.quantile(us_log, [0.10, 0.90])
    us_total = float(part.sum())
    us = {"state": "US (sum of 48 states)", "silage": us_total, "silage_lo80": us_total * np.exp(q10),
          "silage_hi80": us_total * np.exp(q90), "silage_last_year": float(last.reindex(part.index).sum())}
    table = pd.concat([pd.DataFrame([us]).set_index("state"), table.sort_values("silage", ascending=False)])
    table = table.reset_index().rename(columns={"index": "state"})
    table.insert(0, "year", year)
    table.insert(2, "candidate", name)
    info = {"us_log_error_q10": float(q10), "us_log_error_q90": float(q90), "n_backtest_years": len(us_log),
            "state_interval_loyo_coverage": interval_coverage(held_out)}
    return table, info


def lagged_files(files: pd.DataFrame, days: int) -> pd.DataFrame:
    """The FSA file table with every assumed publication date moved to data date + ``days`` (documented ones kept)."""
    out = files.copy()
    assumed = out["published_source"].astype(str).str.startswith("assumed") & out["data_as_of"].notna()
    shifted = pd.to_datetime(out.loc[assumed, "data_as_of"]) + pd.Timedelta(days=days)
    out.loc[assumed, "assumed_published"] = shifted.dt.strftime("%Y-%m-%d")
    return out


def lag_sensitivity(finals, states, fsa, raw, rma_silage) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Post-hoc: every candidate rescored with FSA files assumed published 10 days after their data date."""
    files = lagged_files(fsa[0], SENSITIVITY_LAG_DAYS)
    years = list(range(FIRST_TEST, LAST_TEST + 1))
    scored, used_all = [], []
    for asof_key in ASOF:
        preds, _, used, rows = run_asof(asof_key, finals, states, (files, fsa[1]), raw, rma_silage, years)
        scored.append(score_table(attach_truth(preds, finals, rows)).assign(asof_key=asof_key))
        used_all += used
    by_year = pd.concat(scored, ignore_index=True)
    return summarise(by_year).assign(fsa_publication_lag_days=SENSITIVITY_LAG_DAYS), pd.DataFrame(used_all)


def by_region(backtest: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    """Pooled error by region (kernelag.state_model.region_of) and period, as of 15 November."""
    part = backtest[(backtest["asof_key"] == PRIMARY_ASOF) & backtest["candidate"].isin(names)]
    part = part.assign(region=part["state"].map(region_of), miss=part["pred"] - part["actual"])
    rows = []
    for period, (lo, hi) in PERIODS.items():
        window = part[part["year"].between(lo, hi)]
        for (region, name), group in window.groupby(["region", "candidate"]):
            rows.append({"period": period, "region": region, "candidate": name, "state_years": len(group),
                         "acres_per_year": group["actual"].sum() / group["year"].nunique(),
                         "pooled_wape_pct": 100 * group["miss"].abs().sum() / group["actual"].sum(),
                         "pooled_signed_pct": 100 * group["miss"].sum() / group["actual"].sum()})
    return pd.DataFrame(rows)


def stored_reference(by_year: pd.DataFrame, chosen: str) -> pd.DataFrame:
    """The selected model against the team's stored silage models that read year-t NASS figures (2017-2024)."""
    stored = pd.read_csv(DATA / "models" / "state_model_backtest.csv")
    stored = stored[(stored["scope"] == "all_states") & (stored["series"] == "silage")
                    & stored["predictor"].isin(STORED_NASS_INPUT_MODELS)]
    mine = by_year[(by_year["asof_key"] == PRIMARY_ASOF) & (by_year["candidate"] == chosen)].set_index("year")
    rows = []
    for name, group in stored.groupby("predictor"):
        paired = group.set_index("year")[["state_error_pct", "total_error_pct"]].join(mine, how="inner")
        diff = (paired["state_wape_pct"] - paired["state_error_pct"]).to_numpy()
        ci = bootstrap_ci(diff)
        rows.append({"selected": chosen, "stored_model": name, "years": f"{paired.index.min()}-{paired.index.max()}",
                     "n_years": len(diff), "mean_selected_wape": paired["state_wape_pct"].mean(),
                     "mean_stored_wape": paired["state_error_pct"].mean(), "mean_diff_points": diff.mean(),
                     "ci90_lo": ci[0], "ci90_hi": ci[1], "years_better": int((diff < -TIE).sum()),
                     "mean_abs_us_selected": paired["us_error_pct"].abs().mean(),
                     "mean_abs_us_stored": paired["total_error_pct"].abs().mean()})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score-2025", action="store_true", help="write the one-time 2025 information score")
    args = parser.parse_args()
    check_tiers()
    OUT.mkdir(exist_ok=True)
    prereg = preregistration_status()
    if not prereg["unchanged"]:
        print("WARNING: README pre-registration section differs from out/preregistration.sha256")

    finals, states = load_nass_finals()
    fsa = load_fsa()
    raw = load_season_inputs()
    rma_silage = rma_silage_acres(raw["insured"])

    incumbent, reproduction = reproduce_incumbent(finals, states)
    print("reproduction:", json.dumps({k: (v["mean_state_wape_mine"], v["mean_state_wape_stored"], v["exact_to_2dp"])
                                       for k, v in reproduction.items()}))
    if not all(v["exact_to_2dp"] for v in reproduction.values()):
        raise SystemExit("incumbent or persistence not reproduced exactly; stopping before any new candidate")

    test_years = list(range(FIRST_TEST, FORECAST_YEAR + 1))
    all_preds, all_params, all_used, rows_by_asof = [], [], [], {}
    for asof_key in ASOF:
        preds, params, used, rows = run_asof(asof_key, finals, states, fsa, raw, rma_silage, test_years)
        all_preds.append(preds)
        all_params += params
        all_used += used
        rows_by_asof[asof_key] = rows
    preds = pd.concat(all_preds, ignore_index=True)
    oracle = oracle_predictions(finals, states, list(range(FIRST_TEST, LAST_TEST + 1)))
    s1_nov = preds[(preds["candidate"] == SIMPLEST) & (preds["asof_key"] == PRIMARY_ASOF)]
    oracle = oracle.merge(s1_nov[["state", "year", "pred"]].rename(columns={"pred": "s1"}), on=["state", "year"])
    oracle["pred"] = oracle["pred"].where(oracle["oracle_ok"], oracle["s1"])
    oracle_rows = [oracle.drop(columns=["oracle_ok", "s1"]).assign(asof_key=key) for key in ASOF]
    incumbent_rows = [incumbent.assign(asof_key=key) for key in ASOF]   # history only: identical at every date

    backtest = pd.concat([attach_truth(p, finals, rows_by_asof[p["asof_key"].iloc[0]])
                          for p in [*[preds[preds["asof_key"] == k] for k in ASOF], *oracle_rows, *incumbent_rows]],
                         ignore_index=True)
    backtest = backtest[backtest["year"] >= FIRST_TEST]
    counts = backtest.groupby(["asof_key", "year", "candidate"]).size().unstack("candidate")
    full = counts.drop(columns=["s1_incumbent_H13"])
    if (full.nunique(axis=1) != 1).any():
        raise ValueError("candidates were scored on different state sets")
    month_day = {k: f"{m:02d}-{d:02d}" for k, (m, d) in ASOF.items()}
    backtest["asof"] = backtest["year"].astype(str) + "-" + backtest["asof_key"].map(month_day)

    by_year = pd.concat([score_table(group).assign(asof_key=key) for key, group in backtest.groupby("asof_key")],
                        ignore_index=True)
    summary = summarise(by_year)
    compared = comparisons(by_year)
    selection = select(by_year)
    selection_info = select(by_year, "2017-2024")
    chosen = selection["selected"]
    print(f"selected: {chosen}")

    held_out = backtest[(backtest["candidate"] == chosen) & (backtest["asof_key"] == PRIMARY_ASOF)
                        & backtest["year"].between(FIRST_TEST, LAST_TEST)].rename(columns={"pred": "predicted"})
    rows_nov = rows_by_asof[PRIMARY_ASOF]
    forecast, interval_info = forecast_with_intervals(preds[preds["asof_key"] == PRIMARY_ASOF], rows_nov, held_out,
                                                      chosen, FORECAST_YEAR)
    all_2026 = preds[(preds["year"] == FORECAST_YEAR) & (preds["asof_key"] == PRIMARY_ASOF)]
    all_2026 = all_2026.pivot(index="state", columns="candidate", values="pred")
    all_2026.loc["US (sum of 48 states)"] = all_2026.sum()
    used_2026 = [u for u in all_used if u["year"] == FORECAST_YEAR]

    # --- write ---
    columns = ["state", "year", "asof", "candidate", "pred", "actual"]
    backtest.sort_values(["asof", "candidate", "state"])[columns + ["asof_key", "last"]].to_csv(
        OUT / "backtest_by_state_year.csv", index=False, lineterminator="\n", float_format="%.1f")
    by_year.to_csv(OUT / "by_year.csv", index=False, lineterminator="\n", float_format="%.4f")
    summary.to_csv(OUT / "summary.csv", index=False, lineterminator="\n", float_format="%.4f")
    compared.to_csv(OUT / "comparisons.csv", index=False, lineterminator="\n", float_format="%.4f")
    pd.DataFrame(all_params).to_csv(OUT / "fitted_params.csv", index=False, lineterminator="\n", float_format="%.5f")
    pd.DataFrame(all_used).to_csv(OUT / "inputs_used.csv", index=False, lineterminator="\n")
    residual_diagnostics(rows_nov, finals).to_csv(OUT / "s3_residual_diagnostics.csv", index=False,
                                                  lineterminator="\n", float_format="%.3f")
    # Post-hoc checks (README section 7): none of them feeds back into the selection above.
    region_names = ["s0_persistence", SIMPLEST, "s2_fsa_ratio_highcov", chosen, "d3_raw_residual",
                    "d_oracle_final_residual"]
    by_region(backtest, list(dict.fromkeys(region_names))).to_csv(
        OUT / "by_region.csv", index=False, lineterminator="\n", float_format="%.3f")
    stored_reference(by_year, chosen).to_csv(OUT / "reference_nass_input_models.csv", index=False,
                                             lineterminator="\n", float_format="%.4f")
    lag_summary, lag_used = lag_sensitivity(finals, states, fsa, raw, rma_silage)
    lag_summary.to_csv(OUT / "sensitivity_publication_lag10.csv", index=False, lineterminator="\n",
                       float_format="%.4f")
    lag_used.to_csv(OUT / "sensitivity_publication_lag10_inputs.csv", index=False, lineterminator="\n")
    acre_columns = [c for c in forecast.columns if c.startswith("silage")]
    forecast[acre_columns] = forecast[acre_columns].round(-2)
    forecast.to_csv(OUT / "forecast_2026.csv", index=False, lineterminator="\n")
    all_2026.round(-2).reset_index().to_csv(OUT / "forecast_2026_all_candidates.csv", index=False,
                                            lineterminator="\n", float_format="%.0f")
    (OUT / "selection.json").write_text(json.dumps({"primary": selection, "information_2017_2024": selection_info},
                                                   indent=1) + "\n", encoding="utf-8")
    (OUT / "reproduction.json").write_text(json.dumps(reproduction, indent=1) + "\n", encoding="utf-8")
    run_info = {"status": "done", "preregistration": prereg, "selected": chosen,
                "inputs_used_2026": used_2026, "interval_info_2026": interval_info,
                "fsa_files_status": fsa[0]["status"].value_counts().to_dict(),
                "caveats": [("RMA files are today's vintage (insured acres and losses of past years are more "
                             "complete than they were in real time)"),
                            "FSA publication dates before 2025 are assumed: data date + 5 days",
                            "2025 is excluded from the backtest, fitting of backtest years and selection"]}
    (OUT / "run.json").write_text(json.dumps(run_info, indent=1, default=str) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    primary = summary[(summary["asof_key"] == PRIMARY_ASOF)].pivot(
        index="candidate", columns="period", values=["mean_state_wape_pct", "mean_abs_us_error_pct"])
    print(primary.round(2).to_string())
    print(json.dumps(selection, indent=1))
    print(forecast.head(15).to_string(index=False))

    if args.score_2025:
        target = OUT / "score_2025_information_only.csv"
        if target.exists():
            parser.error(f"{target} exists: the 2025 information score is computed once only")
        p25 = preds[(preds["candidate"] == chosen) & (preds["year"] == SCORING_YEAR)
                    & (preds["asof_key"] == PRIMARY_ASOF)].set_index("state")["pred"]
        last25 = rows_nov[rows_nov["year"] == SCORING_YEAR].set_index("state")["S1"]
        bounds = sm_add_intervals(p25, last25, error_quantiles(held_out), "silage")
        actual25 = truth(finals, SCORING_YEAR).reindex(p25.index)
        table = pd.DataFrame({"pred": p25, "actual": actual25, "persistence": last25.reindex(p25.index)}).join(bounds)
        table = table.dropna(subset=["actual"])
        miss, miss_p = table["pred"] - table["actual"], table["persistence"] - table["actual"]
        inside = ((table["actual"] >= table["silage_lo80"]) & (table["actual"] <= table["silage_hi80"])).mean()
        result = {"label": "INFORMATION ONLY: computed once after selection; not used for any choice",
                  "candidate": chosen, "asof": f"{SCORING_YEAR}-11-15",
                  "fsa_files": [u for u in all_used if u["year"] == SCORING_YEAR and u["asof_key"] == PRIMARY_ASOF],
                  "n_states": len(table),
                  "state_wape_pct": float(100 * miss.abs().sum() / table["actual"].sum()),
                  "us_error_pct": float(100 * miss.sum() / table["actual"].sum()),
                  "persistence_state_wape_pct": float(100 * miss_p.abs().sum() / table["actual"].sum()),
                  "persistence_us_error_pct": float(100 * miss_p.sum() / table["actual"].sum()),
                  "inside_80_share": float(inside)}
        table.reset_index().to_csv(target, index=False, lineterminator="\n", float_format="%.1f")
        (OUT / "score_2025_information_only.json").write_text(json.dumps(result, indent=1, default=str) + "\n",
                                                               encoding="utf-8")
        print(json.dumps(result, indent=1, default=str))


if __name__ == "__main__":
    main()
