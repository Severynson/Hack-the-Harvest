"""Tier B ("NASS-informed") state corn-for-silage harvested acres, backtested 2012-2024 as of 15 Sep / Oct / Nov.

Tier B may use, for target year t, NASS data that is not the acreage answer: NASS in-season planted acres (March
intentions, June Acreage, later planted updates), NASS grain-yield forecasts, NASS weekly crop condition and NASS
1 January milk-cow inventories, plus every Tier A source (FSA crop acreage by intended use, RMA, Drought Monitor).
Forbidden for year t: NASS's harvested-for-grain forecast and anything computed from it, and NASS finals of year t.
The pre-registration (candidates, inputs, selection rule) is README.md section 1, hashed into
out/preregistration.sha256 by ``--prereg`` before the first scored run. This module implements that text.

Candidates: c0_reversion_only (simplest; the incumbent's algorithm on NASS finals from 2000), c0_incumbent_H13
(exact reproduction of kernelag's reversion_only, 2017-2024), persistence, c1-c5, c5b; diagnostics d5_raw,
d5b_raw, d_oracle_final_residual, d5_oracle_planted, d5_oracle_grain (the last three read year-t NASS finals:
measurements of the method, never models).

Run from the repo root:
    .venv/Scripts/python.exe test_models/ownModels/tierB/silage/run.py --check      (reproduction + coverage, no scores)
    .venv/Scripts/python.exe test_models/ownModels/tierB/silage/run.py --prereg     (hash README section 1, once)
    .venv/Scripts/python.exe test_models/ownModels/tierB/silage/run.py              (full backtest, 2026 forecast)
    .venv/Scripts/python.exe test_models/ownModels/tierB/silage/run.py --score-2025 (one time only)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from kernelag import fsa as kfsa  # noqa: E402
from kernelag.context import STATE_NAMES  # noqa: E402
from kernelag.context import drought as ctx_drought  # noqa: E402
from kernelag.context import loss_share as ctx_loss_share  # noqa: E402
from kernelag.context import poor_condition as ctx_poor_condition  # noqa: E402
from kernelag.state_model import add_intervals, error_quantiles, fit_ridge, interval_coverage, region_of  # noqa: E402

OUT = HERE / "out"
DATA = REPO / "data"
QUICKSTATS = DATA / "Quickstats Data"
README = HERE / "README.md"
TIER_A_BY_YEAR = REPO / "test_models" / "ownModels" / "silage" / "out" / "by_year.csv"   # read only
PREREG_START, PREREG_END = "## 1. Pre-registration", "<!-- END OF PRE-REGISTRATION -->"

FIRST_TEST, LAST_TEST = 2012, 2024
PERIODS = {"2012-2024": (2012, 2024), "2017-2024": (2017, 2024), "2018-2024": (2018, 2024)}
SCORING_YEAR, FORECAST_YEAR = 2025, 2026
MAX_FINAL_YEAR = 2025          # NASS finals exist through 2025; any 2026 "YEAR" value in Quick Stats is in-season
ASOF = {"sep": (9, 15), "oct": (10, 15), "nov": (11, 15)}
ASOF_MONTH = {key: month for key, (month, _) in ASOF.items()}
PRIMARY_ASOF = "nov"
H00, H13 = 2000, 2013          # first NASS final year in each history variant
TRAIN_FROM = 2012              # first year with FSA (prior final 2011) and NASS in-season planted (March 2012)
MIN_FIT_YEARS = 3
FIRST_FSA_YEAR = 2011
FSA_FLOOR = 500.0              # acres: an FSA denominator below this is not used
COVERAGE_GATE = 0.75           # FSA silage-intended (final t-1) / NASS silage (t-1) for "high coverage"
CLIP = (0.5, 2.0)
LOG_CLIP = float(np.log(2.0))
W_GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.05), 2)
N_BOOT, SEED = 10_000, 20261114
TIE = 1e-9

# NASS report month of each in-season vintage. Acreage comes out at the end of June; Crop Production between the
# 8th and the 12th of its month, so every vintage of month m is public by the 15th of month m.
REPORT_MONTH = {"mar": 3, "jun": 6, "aug": 8, "sep": 9, "oct": 10, "nov": 11}
PLANTED_PERIODS = {"YEAR - MAR ACREAGE": "mar", "YEAR - JUN ACREAGE": "jun", "YEAR - AUG ACREAGE": "aug",
                   "YEAR - AUG FORECAST": "aug", "YEAR - SEP FORECAST": "sep", "YEAR - OCT ACREAGE": "oct",
                   "YEAR - OCT FORECAST": "oct"}
YIELD_PERIODS = {"YEAR - AUG FORECAST": "aug", "YEAR - SEP FORECAST": "sep", "YEAR - OCT FORECAST": "oct",
                 "YEAR - NOV FORECAST": "nov"}

EXPECTED_SIGN = {"reversion": -1, "d_planted": +1, "d_fsa_nongrain": +1, "yield_shock": -1, "d_drought": +1,
                 "d_poor": +1, "d_loss": +1, "d_cows": +1, "d_fsa_silage_hc": +1}
C1_FEATURES = ["reversion", "d_planted", "d_fsa_nongrain"]
C2_FEATURES = C1_FEATURES + ["yield_shock", "d_drought", "d_poor", "d_loss"]
C3_FEATURES = C1_FEATURES + ["d_cows", "d_fsa_silage_hc"]
C4_FEATURES = C2_FEATURES + ["d_cows", "d_fsa_silage_hc"]
GBT_PARAMS = {"n_estimators": 150, "max_depth": 2, "learning_rate": 0.05, "min_child_weight": 5.0,
              "subsample": 1.0, "colsample_bytree": 1.0, "reg_lambda": 1.0, "tree_method": "exact",
              "n_jobs": 1, "random_state": 0}

# --- independence tiers ---------------------------------------------------------------------------------------

INPUTS = {
    "nass_final_history": ("NASS final state acres (silage, grain, planted) and final grain yield, years before t "
                           "(Quick Stats 'YEAR' rows, data/Quickstats Data/*_2000_2026.csv)", "A"),
    "fsa_acreage": ("FSA crop acreage files published by the as-of date (data/fsa/fsa_corn_state.csv via "
                    "kernelag.fsa.usable_files / latest_file)", "A"),
    "rma_cause_of_loss": ("RMA cause of loss, weather causes, months before the as-of month "
                          "(data/rma/cause_of_loss_corn)", "A"),
    "rma_insured": ("RMA Summary of Business insured acres (data/rma/insured_by_type_corn)", "A"),
    "drought_monitor": ("US Drought Monitor weekly state D2+ share (data/drought/usdm_state_weekly_2000_2026.csv)",
                        "A"),
    "nass_planted_inseason": ("NASS corn planted for all purposes of year t, latest vintage published by the as-of "
                              "date (Quick Stats 'YEAR - MAR/JUN/AUG/OCT ACREAGE', 'YEAR - AUG/SEP/OCT FORECAST')",
                              "B"),
    "nass_yield_forecast": ("NASS corn grain yield forecast of year t, latest of Aug-Nov published by the as-of date",
                            "B"),
    "nass_crop_condition": ("NASS weekly corn condition of year t, weeks 30-36", "B"),
    "nass_milk_cows": ("NASS milk cow inventory on 1 January of t and t-1 (published late January)", "B"),
    "nass_grain_forecast": ("NASS harvested-for-grain forecast of year t, or anything computed from it", "forbidden"),
    "nass_final_target_year": ("NASS final planted and grain acres of year t itself (published with the answer)",
                               "forbidden"),
}
ALLOWED_INPUT_TIERS = {"A": {"A"}, "benchmark": {"A"}, "B": {"A", "B"}, "forbidden": {"A", "B", "forbidden"}}
HISTORY = ["nass_final_history"]
C1_INPUTS = HISTORY + ["nass_planted_inseason", "fsa_acreage"]
STRESS_INPUTS = ["nass_yield_forecast", "drought_monitor", "nass_crop_condition", "rma_cause_of_loss", "rma_insured"]
DAIRY_INPUTS = ["nass_milk_cows"]
CANDIDATES = {
    "persistence": {"tier": "benchmark", "inputs": HISTORY, "eligible": False},
    "c0_incumbent_H13": {"tier": "benchmark", "inputs": HISTORY, "eligible": False},
    "c0_reversion_only": {"tier": "A", "inputs": HISTORY, "eligible": False},
    "c1_planted_fsa_ridge": {"tier": "B", "inputs": C1_INPUTS, "eligible": True, "features": C1_FEATURES},
    "c2_plus_stress": {"tier": "B", "inputs": C1_INPUTS + STRESS_INPUTS, "eligible": True, "features": C2_FEATURES},
    "c3_plus_dairy": {"tier": "B", "inputs": C1_INPUTS + DAIRY_INPUTS, "eligible": True, "features": C3_FEATURES},
    "c4_monotone_gbt": {"tier": "B", "inputs": C1_INPUTS + STRESS_INPUTS + DAIRY_INPUTS, "eligible": True,
                        "features": C4_FEATURES},
    "c5_residual_shrunk": {"tier": "B", "inputs": C1_INPUTS, "eligible": True},
    "c5b_residual_fsa_planted_pre_june": {"tier": "B", "inputs": C1_INPUTS, "eligible": True},
    "d5_raw_residual": {"tier": "B", "inputs": C1_INPUTS, "eligible": False, "diagnostic": True},
    "d5b_raw_residual": {"tier": "B", "inputs": C1_INPUTS, "eligible": False, "diagnostic": True},
    "d_oracle_final_residual": {"tier": "forbidden", "inputs": HISTORY + ["nass_final_target_year"],
                                "eligible": False, "diagnostic": True},
    "d5_oracle_planted": {"tier": "forbidden", "inputs": C1_INPUTS + ["nass_final_target_year"],
                          "eligible": False, "diagnostic": True},
    "d5_oracle_grain": {"tier": "forbidden", "inputs": C1_INPUTS + ["nass_final_target_year"],
                        "eligible": False, "diagnostic": True},
}
SIMPLEST = "c0_reversion_only"
SELECTION_ORDER = ["c1_planted_fsa_ridge", "c5_residual_shrunk", "c5b_residual_fsa_planted_pre_june",
                   "c2_plus_stress", "c3_plus_dairy", "c4_monotone_gbt"]

# Every column a candidate reads, with its source. Written to out/input_columns.csv.
COLUMNS = {
    "S1..S4": ("nass_final_history", "NASS final silage harvested acres of t-1..t-4"),
    "P1, G1": ("nass_final_history", "NASS final planted and grain harvested acres of t-1"),
    "reversion": ("nass_final_history", "log(S1 / mean(S2, S3, S4))"),
    "P_nass": ("nass_planted_inseason", "latest NASS planted (t) whose report month <= as-of month: oct, sep, aug, "
                                        "jun, mar (first that exists)"),
    "d_planted": ("nass_planted_inseason", "log(P_nass / P1)"),
    "F_pf_cur, F_grain_cur, F_silage_cur": ("fsa_acreage", "FSA field corn of the newest crop-year-t file published "
                                            "by d: planted+failed (all uses), planted grain-intended, planted "
                                            "silage-intended (Silage and Forage)"),
    "F_pf_prev, F_grain_prev, F_silage_prev": ("fsa_acreage", "the same from the final (January) file of t-1"),
    "d_fsa_nongrain": ("fsa_acreage", "(1 - F_grain_cur/F_pf_cur) - (1 - F_grain_prev/F_pf_prev); NaN if an F_pf "
                                      "is under 500 acres"),
    "d_fsa_silage_hc": ("fsa_acreage", "clip(log(F_silage_cur/F_silage_prev), -log 2, log 2) only where "
                                       "F_silage_prev >= 500 and F_silage_prev/S1 >= 0.75; else NaN"),
    "yield_shock": ("nass_yield_forecast", "log(latest NASS yield forecast (t) / mean NASS final yield t-1..t-3)"),
    "d_drought": ("drought_monitor", "kernelag.context.drought(t) - drought(t-1): Jun-Sep mean D2+ share to d"),
    "d_poor": ("nass_crop_condition", "kernelag.context.poor_condition(t) - (t-1): weeks 30-36, published by d"),
    "d_loss": ("rma_cause_of_loss", "kernelag.context.loss_share(t) - (t-1): weather-loss acres before d's month "
                                    "/ insured acres"),
    "d_cows": ("nass_milk_cows", "log(milk cows 1 Jan t / milk cows 1 Jan t-1)"),
    "P_hyb": ("nass_planted_inseason", "P_nass if its vintage is June or later, else F_pf_cur x P1 / F_pf_prev"),
    "G_hat": ("fsa_acreage", "P x (F_grain_cur/F_pf_cur) x [(G1/P1) / (F_grain_prev/F_pf_prev)]  (P = P_nass or "
                             "P_hyb); the own grain estimate (b1 form), never NASS's grain forecast"),
    "raw5": ("nass_planted_inseason", "S1 x clip((P - G_hat) / (P1 - G1), 0.5, 2)"),
}
FORBIDDEN_COLUMN_PARTS = ("grain_asof", "nass_latest", "not_grain", "grain_fc", "grain_nov", "grain_forecast")


def check_tiers(candidates: dict = CANDIDATES) -> None:
    """Refuse a candidate whose inputs exceed its tier, an eligible non-Tier-B candidate, or an eligible
    candidate with a forbidden input."""
    for name, spec in candidates.items():
        allowed = ALLOWED_INPUT_TIERS[spec["tier"]]
        for key in spec["inputs"]:
            if INPUTS[key][1] not in allowed:
                raise ValueError(f"{name} is tier {spec['tier']} but uses {key} (tier {INPUTS[key][1]})")
        if spec["eligible"] and (spec["tier"] != "B" or spec.get("diagnostic")):
            raise ValueError(f"{name} is eligible but is tier {spec['tier']} / diagnostic")


def check_columns(columns) -> None:
    """Refuse any model-input column whose name says it comes from NASS's grain forecast."""
    bad = [c for c in columns if any(part in str(c).lower() for part in FORBIDDEN_COLUMN_PARTS)]
    if bad:
        raise ValueError(f"forbidden NASS grain-forecast columns in model rows: {bad}")


class LookAheadError(RuntimeError):
    """A model asked for NASS finals of its own target year or later, or for a file published after the as-of date."""


class History:
    """NASS finals as a forecast for ``target_year`` may see them: years ``start``..t-1 only."""

    def __init__(self, finals: pd.DataFrame, states: list[str], target_year: int, start: int = H00):
        self.t, self.states = target_year, states
        visible = finals[(finals["year"] >= start) & (finals["year"] < target_year)]
        self._wide = {series: visible.pivot(index="state", columns="year", values=series).reindex(states)
                      for series in ("silage", "grain", "planted", "yield") if series in visible}

    def get(self, series: str, year: int) -> pd.Series:
        if year >= self.t:
            raise LookAheadError(f"{series} {year} requested by a forecast for {self.t}")
        wide = self._wide[series]
        if year in wide.columns:
            return wide[year].astype(float)
        return pd.Series(np.nan, index=pd.Index(self.states, name="state"), dtype=float)

    def long(self, series: str) -> pd.DataFrame:
        return self._wide[series].stack().rename("value").rename_axis(["state", "year"]).reset_index()


# --- loading ----------------------------------------------------------------------------------------------------

def read_quickstats(name: str, item: str) -> pd.DataFrame:
    """State survey totals for one Quick Stats item: state, year, period, value (withheld cells dropped)."""
    raw = pd.read_csv(QUICKSTATS / name, dtype=str, keep_default_na=False)
    rows = raw[(raw["source_desc"] == "SURVEY") & (raw["short_desc"] == item) & (raw["agg_level_desc"] == "STATE")
               & (raw["domain_desc"] == "TOTAL")]
    value = pd.to_numeric(rows["Value"].str.replace(",", "").str.strip(), errors="coerce")
    table = pd.DataFrame({"state": rows["state_name"].to_numpy(), "year": rows["year"].astype(int).to_numpy(),
                          "period": rows["reference_period_desc"].to_numpy(), "value": value.to_numpy()})
    return table.dropna(subset=["value"]).drop_duplicates(["state", "year", "period"])


def load_finals() -> tuple[pd.DataFrame, list[str], dict]:
    """NASS finals 2000-2025 (silage, grain, planted acres; grain yield), checked against the incumbent's truth."""
    items = {"silage": ("corn_silage_harvested_acres_state_2000_2026.csv", "CORN, SILAGE - ACRES HARVESTED"),
             "grain": ("corn_grain_harvested_acres_state_2000_2026.csv", "CORN, GRAIN - ACRES HARVESTED"),
             "planted": ("corn_planted_acres_state_2000_2026.csv", "CORN - ACRES PLANTED"),
             "yield": ("corn_grain_yield_state_2000_2026.csv", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")}
    parts = []
    for series, (name, item) in items.items():
        table = read_quickstats(name, item)
        table = table[(table["period"] == "YEAR") & (table["year"] <= MAX_FINAL_YEAR)]
        parts.append(table.assign(series=series))
    long = pd.concat(parts, ignore_index=True)

    incumbent = pd.read_csv(DATA / "nass" / "corn_acres_state.csv")
    final = incumbent[incumbent["period"] == "final"]
    states = sorted(final.loc[final["series"] == "silage", "state"].unique())
    long = long[long["state"].isin(states)]
    merged = final[["state", "year", "series", "acres"]].merge(
        long.rename(columns={"value": "qs"}), on=["state", "year", "series"], how="left")
    bad = merged[merged["qs"].isna() | (merged["qs"] != merged["acres"])]
    if len(bad):
        raise ValueError(f"Quick Stats finals differ from data/nass/corn_acres_state.csv in {len(bad)} rows")
    wide = long.pivot_table(index=["state", "year"], columns="series", values="value", aggfunc="first").reset_index()
    return wide, states, {"finals_rows_checked": int(len(merged)), "finals_mismatches": 0}


def load_planted_inseason(states: list[str]) -> tuple[pd.DataFrame, dict]:
    """NASS in-season planted acres by state, year and report vintage (never the 'YEAR' final)."""
    table = read_quickstats("corn_planted_acres_state_2000_2026.csv", "CORN - ACRES PLANTED")
    table = table[table["period"].isin(list(PLANTED_PERIODS)) & table["state"].isin(states)]
    table = table.assign(vintage=table["period"].map(PLANTED_PERIODS))
    table = table.drop_duplicates(["state", "year", "vintage"])[["state", "year", "vintage", "value"]]
    incumbent = pd.read_csv(DATA / "nass" / "corn_acres_state.csv")
    inseason = incumbent[(incumbent["series"] == "planted") & (incumbent["period"] != "final")]
    merged = inseason.merge(table, left_on=["state", "year", "period"], right_on=["state", "year", "vintage"],
                            how="left")
    bad = merged[merged["value"].isna() | (merged["value"] != merged["acres"])]
    if len(bad):
        raise ValueError(f"Quick Stats in-season planted differs from corn_acres_state.csv in {len(bad)} rows")
    coverage = table.groupby("year")["vintage"].apply(lambda v: ",".join(sorted(set(v), key=REPORT_MONTH.get)))
    return table, {"planted_inseason_rows_checked": int(len(merged)), "planted_inseason_mismatches": 0,
                   "planted_vintages_by_year": {int(k): v for k, v in coverage.items()}}


def load_yield_forecasts(states: list[str]) -> pd.DataFrame:
    table = read_quickstats("corn_grain_yield_state_2000_2026.csv", "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE")
    table = table[table["period"].isin(list(YIELD_PERIODS)) & table["state"].isin(states)]
    return table.assign(vintage=table["period"].map(YIELD_PERIODS))[["state", "year", "vintage", "value"]]


def load_milk_cows(states: list[str]) -> pd.Series:
    table = read_quickstats("milk_cow_inventory_state_2000_2026.csv", "CATTLE, COWS, MILK - INVENTORY")
    table = table[(table["period"] == "FIRST OF JAN") & table["state"].isin(states)]
    return table.set_index(["state", "year"])["value"]


def load_fsa() -> tuple[pd.DataFrame, pd.DataFrame]:
    """FSA file table, and field-corn acres per file and state: silage, grain, planted (all uses), pf."""
    files = pd.read_csv(DATA / "fsa" / "fsa_files.csv")
    state = pd.read_csv(DATA / "fsa" / "fsa_corn_state.csv", dtype={"state_fips": str, "data_as_of": str})
    planted = state.pivot_table(index=["crop_year", "data_as_of", "state"], columns="intended_use",
                                values="planted_acres", aggfunc="sum").fillna(0.0)
    failed = state.groupby(["crop_year", "data_as_of", "state"])["failed_acres"].sum(min_count=1).fillna(0.0)
    acres = pd.DataFrame({"silage": planted.get("silage", 0.0), "grain": planted.get("grain", 0.0),
                          "planted": planted.sum(axis=1)})
    acres["pf"] = acres["planted"] + failed.reindex(acres.index).fillna(0.0)
    return files, acres


def fsa_file_acres(acres: pd.DataFrame, row: pd.Series | None, states: list[str]) -> pd.DataFrame:
    empty = pd.DataFrame(np.nan, index=pd.Index(states, name="state"), columns=["silage", "grain", "planted", "pf"])
    if row is None:
        return empty
    key = (int(row["crop_year"]), str(row["data_as_of"]))
    if key not in acres.index.droplevel("state").unique():
        raise KeyError(f"FSA file {row['zip_name']} ({key}) has status ok but no rows in fsa_corn_state.csv")
    return acres.loc[key].reindex(states)


def fsa_inputs(files: pd.DataFrame, acres: pd.DataFrame, asof: date, year: int, states: list[str]):
    """Newest crop-year-t FSA file published by ``asof`` and the final file of t-1, with what was used."""
    current = kfsa.latest_file(files, asof, year)
    usable = kfsa.usable_files(files, asof, year)
    previous = usable[usable["crop_year"] == year - 1]
    finals = previous[previous["vintage"].astype(str).str.startswith("final")]
    chosen = finals if not finals.empty else previous
    prior = chosen.sort_values("data_as_of").iloc[-1] if not chosen.empty else None
    for row in (current, prior):
        if row is not None and pd.Timestamp(row["assumed_published"]) > pd.Timestamp(asof):
            raise LookAheadError(f"FSA file {row['zip_name']} published after {asof}")
    if current is not None and (int(current["crop_year"]) != year or str(current["vintage"]).startswith("final")):
        raise LookAheadError(f"FSA file {current['zip_name']} is not an in-season file of {year}")
    meta = {"year": year, "asof": asof.isoformat()}
    for label, row in (("current", current), ("prior_final", prior)):
        for field in ("zip_name", "data_as_of", "assumed_published", "vintage"):
            meta[f"{label}_{field}"] = None if row is None else row[field]
    return fsa_file_acres(acres, current, states), fsa_file_acres(acres, prior, states), meta


def _read_folder(folder: Path, columns: list[str]) -> pd.DataFrame:
    files = sorted(folder.glob("*.csv*"))
    if not files:
        raise FileNotFoundError(f"no files in {folder}")
    return pd.concat([pd.read_csv(f, dtype=str, usecols=columns) for f in files], ignore_index=True)


def load_season_raw() -> dict:
    insured = _read_folder(DATA / "rma" / "insured_by_type_corn", [
        "commodity_year", "state_abbreviation", "type_code", "reporting_level_type", "net_reporting_level_amount"])
    cause = _read_folder(DATA / "rma" / "cause_of_loss_corn", [
        "commodity_year", "state_abbreviation", "cause_of_loss_code", "month_of_loss", "net_determined_quantity"])
    usdm = pd.read_csv(next((DATA / "drought").glob("usdm_state_weekly_2000_2026.csv*")))
    condition = pd.read_csv(next(QUICKSTATS.glob("corn_condition_weekly_state_2000_2026.csv*")),
                            dtype=str, keep_default_na=False)
    return {"insured": insured, "cause": cause, "usdm": usdm, "condition": condition}


def season_features(raw: dict, asof_key: str) -> pd.DataFrame:
    parts = [ctx_drought(raw["usdm"], asof_key), ctx_loss_share(raw["cause"], raw["insured"], asof_key),
             ctx_poor_condition(raw["condition"], asof_key)]
    table = parts[0]
    for part in parts[1:]:
        table = table.merge(part, on=["state", "year"], how="outer")
    return table.set_index(["state", "year"])


def load_all() -> dict:
    finals, states, check_finals = load_finals()
    planted, check_planted = load_planted_inseason(states)
    raw = load_season_raw()
    assert set(STATE_NAMES.values()) >= set(states)
    return {"finals": finals, "states": states, "planted": planted, "yield_fc": load_yield_forecasts(states),
            "cows": load_milk_cows(states), "fsa": load_fsa(), "raw": raw,
            "season": {key: season_features(raw, key) for key in ASOF}, "checks": check_finals | check_planted}


# --- rows: what a forecast as of d of year t may read ---------------------------------------------------------

def latest_vintage(table: pd.DataFrame, year: int, asof_key: str, states: list[str]) -> tuple[pd.Series, pd.Series]:
    """Per state, the value of the latest vintage of ``year`` whose report month <= the as-of month."""
    part = table[table["year"] == year]
    month = part["vintage"].map(REPORT_MONTH)
    part = part[month <= ASOF_MONTH[asof_key]].assign(month=month)
    last = part.sort_values("month").groupby("state").last()
    return last["value"].reindex(states).astype(float), last["vintage"].reindex(states)


def _clipped_log_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = np.log(numerator / denominator.where(denominator >= FSA_FLOOR))
    return value.replace([np.inf, -np.inf], np.nan).clip(-LOG_CLIP, LOG_CLIP)


def _by_state(series: pd.Series | pd.DataFrame, column: str | None, states: list[str], year: int) -> pd.Series:
    if column is not None:
        if column not in series:
            return pd.Series(np.nan, index=pd.Index(states, name="state"))
        series = series[column]
    return series.reindex(pd.MultiIndex.from_product([states, [year]])).droplevel(1).astype(float)


def build_rows(data: dict, asof_key: str, years: list[int], start: int = H00,
               with_inputs: bool = True) -> tuple[pd.DataFrame, list[dict]]:
    """One row per state and target year holding only what a forecast as of ``asof_key`` of that year may use."""
    states, (month, day) = data["states"], ASOF[asof_key]
    season = data["season"][asof_key]
    frames, used = [], []
    for year in years:
        hist = History(data["finals"], states, year, start)
        silage = {k: hist.get("silage", year - k) for k in (1, 2, 3, 4)}
        row = pd.DataFrame(index=pd.Index(states, name="state"))
        row["year"] = year
        row["S1"] = silage[1]
        with np.errstate(divide="ignore", invalid="ignore"):
            row["reversion"] = np.log(silage[1] / pd.concat([silage[2], silage[3], silage[4]], axis=1)
                                      .mean(axis=1, skipna=False))
        row["G1"], row["P1"] = hist.get("grain", year - 1), hist.get("planted", year - 1)
        if with_inputs:
            planted, vintage = latest_vintage(data["planted"], year, asof_key, states)
            row["P_nass"], row["P_vintage"] = planted, vintage
            if year >= FIRST_FSA_YEAR:
                current, prior, meta = fsa_inputs(*data["fsa"], date(year, month, day), year, states)
                n_vint = vintage.value_counts().to_dict()
                used.append(meta | {"asof_key": asof_key, "nass_planted_vintages": json.dumps(n_vint)})
            else:
                current = prior = pd.DataFrame(np.nan, index=row.index, columns=["silage", "grain", "planted", "pf"])
            for use in ("silage", "grain", "pf"):
                row[f"F_{use}_cur"], row[f"F_{use}_prev"] = current[use], prior[use]
            yield_fc, _ = latest_vintage(data["yield_fc"], year, asof_key, states)
            yield_mean = pd.concat([hist.get("yield", year - k) for k in (1, 2, 3)], axis=1).mean(axis=1, skipna=False)
            cows_now = _by_state(data["cows"], None, states, year)
            cows_last = _by_state(data["cows"], None, states, year - 1)
            with np.errstate(divide="ignore", invalid="ignore"):
                row["d_planted"] = np.log(row["P_nass"] / row["P1"])
                ng_cur = 1 - row["F_grain_cur"] / row["F_pf_cur"].where(row["F_pf_cur"] >= FSA_FLOOR)
                ng_prev = 1 - row["F_grain_prev"] / row["F_pf_prev"].where(row["F_pf_prev"] >= FSA_FLOOR)
                row["d_fsa_nongrain"] = ng_cur - ng_prev
                row["yield_shock"] = np.log(yield_fc / yield_mean)
                row["d_cows"] = np.log(cows_now / cows_last)
            gate = (row["F_silage_prev"] >= FSA_FLOOR) & (row["F_silage_prev"] / row["S1"] >= COVERAGE_GATE)
            row["d_fsa_silage_hc"] = _clipped_log_ratio(row["F_silage_cur"], row["F_silage_prev"]).where(gate)
            for feature, column in [("d_drought", "drought"), ("d_loss", "loss_share"), ("d_poor", "poor_condition")]:
                row[feature] = (_by_state(season, column, states, year)
                                - _by_state(season, column, states, year - 1)).to_numpy()
        frames.append(row.replace([np.inf, -np.inf], np.nan).reset_index())
    rows = pd.concat(frames, ignore_index=True)
    check_columns(rows.columns)
    return rows, used


# --- models ---------------------------------------------------------------------------------------------------

def with_target(rows: pd.DataFrame, hist: History) -> pd.DataFrame:
    actual = hist.long("silage").rename(columns={"value": "actual"})
    return rows.merge(actual, on=["state", "year"], how="left")


def c0_out_of_sample(rows: pd.DataFrame, data: dict, start: int) -> tuple[pd.DataFrame, dict]:
    """reversion_only for every year in ``rows``, each fitted on earlier rows only (kernelag fit_ridge)."""
    preds, params = [], {}
    for year in sorted(rows["year"].unique()):
        hist = History(data["finals"], data["states"], year, start)
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
        params[int(year)] = {"c0_beta_per_std": beta}
        preds.append(pd.DataFrame({"state": test["state"].to_numpy(), "year": year,
                                   "pred": test["silage_last"].to_numpy() * np.exp(change)}))
    return pd.concat(preds, ignore_index=True), params


def residual_raw(rows: pd.DataFrame, planted: pd.Series) -> pd.DataFrame:
    """c5 arithmetic: own grain estimate (b1 form), non-grain residual, and S1 x clipped residual ratio."""
    with np.errstate(divide="ignore", invalid="ignore"):
        share_cur = rows["F_grain_cur"] / rows["F_pf_cur"]
        share_prev = rows["F_grain_prev"] / rows["F_pf_prev"]
        correction = (rows["G1"] / rows["P1"]) / share_prev
        grain_hat = planted * share_cur * correction
        residual_hat = planted - grain_hat
        residual_last = rows["P1"] - rows["G1"]
        ok = (rows["G1"].notna() & (rows["P1"] > 0) & (rows["F_pf_cur"] >= FSA_FLOOR)
              & (rows["F_pf_prev"] >= FSA_FLOOR) & (rows["F_grain_prev"] > 0) & (residual_last > 0)
              & rows["F_grain_cur"].notna() & planted.notna() & rows["S1"].notna())
        ratio = (residual_hat / residual_last).clip(*CLIP)
    return pd.DataFrame({"raw": (rows["S1"] * ratio).where(ok), "grain_hat": grain_hat.where(ok),
                         "residual_hat": residual_hat.where(ok)}, index=rows.index)


def hybrid_planted(rows: pd.DataFrame) -> pd.Series:
    """c5b: NASS planted when a June-or-later vintage exists, else FSA planted+failed scaled by last year's ratio."""
    with np.errstate(divide="ignore", invalid="ignore"):
        fsa_scaled = rows["F_pf_cur"] * rows["P1"] / rows["F_pf_prev"].where(rows["F_pf_prev"] >= FSA_FLOOR)
    late = rows["P_vintage"].isin([v for v, m in REPORT_MONTH.items() if m >= 6]) & rows["P_nass"].notna()
    return rows["P_nass"].where(late, fsa_scaled)


def fit_shrink_weight(train: pd.DataFrame, raw_column: str) -> float:
    """The w in W_GRID minimizing sum abs(c0^(1-w) raw^w - actual) (smallest w on ties)."""
    errors = [np.abs(np.exp((1 - w) * np.log(train["c0"]) + w * np.log(train[raw_column])) - train["actual"]).sum()
              for w in W_GRID]
    return float(W_GRID[int(np.argmin(errors))])


def fit_gbt(train: pd.DataFrame, features: list[str]):
    from xgboost import XGBRegressor
    signs = tuple(EXPECTED_SIGN[f] for f in features)
    model = XGBRegressor(objective="reg:squarederror", monotone_constraints=signs, **GBT_PARAMS)
    weight = train["S1"] / train["S1"].mean()
    model.fit(train[features].fillna(0.0).to_numpy(), train["target"].to_numpy(), sample_weight=weight.to_numpy())

    def predict(rows: pd.DataFrame) -> np.ndarray:
        return model.predict(rows[features].fillna(0.0).to_numpy())
    return predict


def candidate_predictions(rows: pd.DataFrame, data: dict,
                          test_years: list[int]) -> tuple[pd.DataFrame, list[dict], pd.DataFrame]:
    """Every candidate for each test year; fitted parameters from earlier years (>= TRAIN_FROM) only."""
    c0_all, c0_params = c0_out_of_sample(rows, data, H00)
    base = rows.merge(c0_all.rename(columns={"pred": "c0"}), on=["state", "year"], how="left")
    r5 = residual_raw(base, base["P_nass"])
    base["raw5"], base["grain_hat5"], base["residual_hat5"] = r5["raw"], r5["grain_hat"], r5["residual_hat"]
    base["P_hyb"] = hybrid_planted(base)
    r5b = residual_raw(base, base["P_hyb"])
    base["raw5b"], base["grain_hat5b"], base["residual_hat5b"] = r5b["raw"], r5b["grain_hat"], r5b["residual_hat"]
    out, params = [], []
    for year in test_years:
        hist = History(data["finals"], data["states"], year, H00)
        train = with_target(base[(base["year"] < year) & (base["year"] >= TRAIN_FROM)], hist)
        train = train[train["actual"].notna() & (train["actual"] > 0) & (train["S1"] > 0) & train["c0"].notna()]
        train = train.assign(target=np.log(train["actual"] / train["S1"]))
        test = base[(base["year"] == year) & base["S1"].notna()].set_index("state")
        n_years = int(train["year"].nunique())
        enough = n_years >= MIN_FIT_YEARS
        record = {"year": year, "train_years": n_years, **c0_params.get(year, {})}
        c0 = test["c0"]
        preds = {"persistence": test["S1"], "c0_reversion_only": c0}
        for name in ("c1_planted_fsa_ridge", "c2_plus_stress", "c3_plus_dairy"):
            features = CANDIDATES[name]["features"]
            if enough:
                model = fit_ridge(train.rename(columns={"S1": "silage_last"}), features)
                preds[name] = test["S1"] * np.exp(model(test))
                record.update({f"{name.split('_')[0]}_{k}": float(v) for k, v in model.weights.items()})
            else:
                preds[name] = c0
        preds["c4_monotone_gbt"] = (test["S1"] * np.exp(fit_gbt(train, C4_FEATURES)(test))) if enough else c0
        for key, raw_col, name in (("w5", "raw5", "c5_residual_shrunk"),
                                   ("w5b", "raw5b", "c5b_residual_fsa_planted_pre_june")):
            fit_rows = train[train[raw_col].notna()]
            w = fit_shrink_weight(fit_rows, raw_col) if fit_rows["year"].nunique() >= MIN_FIT_YEARS else 0.0
            record[key] = w
            raw = test[raw_col]
            preds[name] = c0 if w == 0 else np.exp((1 - w) * np.log(c0) + w * np.log(raw)).where(raw.notna(), c0)
        preds["d5_raw_residual"] = test["raw5"].where(test["raw5"].notna(), c0)
        preds["d5b_raw_residual"] = test["raw5b"].where(test["raw5b"].notna(), c0)
        record.update(states_with_raw5=int(test["raw5"].notna().sum()),
                      states_with_raw5b=int(test["raw5b"].notna().sum()))
        params.append(record)
        for name, series in preds.items():
            out.append(pd.DataFrame({"state": series.index, "year": year, "candidate": name,
                                     "pred": series.to_numpy(dtype=float)}))
    return pd.concat(out, ignore_index=True), params, base


def oracle_predictions(base: pd.DataFrame, data: dict, years: list[int]) -> pd.DataFrame:
    """Diagnostics only (forbidden tier): the method with year-t NASS FINAL planted and/or grain plugged in."""
    finals = data["finals"].set_index(["state", "year"])
    rows = []
    for year in years:
        now = base[(base["year"] == year) & base["S1"].notna()].set_index("state")
        final = finals.reindex(pd.MultiIndex.from_product([now.index, [year]])).droplevel(1)   # year-t finals
        residual_last = now["P1"] - now["G1"]
        oracle = (now["S1"] * (final["planted"] - final["grain"]) / residual_last).where(residual_last > 0)
        planted_oracle = residual_raw(now, final["planted"])["raw"]          # true P(t), own grain share estimate
        grain_ok = now["raw5"].notna() & final["grain"].notna()
        with np.errstate(divide="ignore", invalid="ignore"):
            grain_oracle = (now["S1"] * ((now["P_nass"] - final["grain"]) / residual_last).clip(*CLIP)).where(grain_ok)
        for name, series in [("d_oracle_final_residual", oracle), ("d5_oracle_planted", planted_oracle),
                             ("d5_oracle_grain", grain_oracle)]:
            filled = series.where(series.notna(), now["c0"])
            rows.append(pd.DataFrame({"state": filled.index, "year": year, "candidate": name,
                                      "pred": filled.to_numpy(dtype=float)}))
    return pd.concat(rows, ignore_index=True)


# --- scoring --------------------------------------------------------------------------------------------------

def score_table(preds: pd.DataFrame) -> pd.DataFrame:
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
            if len(group) < hi - lo + 1:      # e.g. the H13 incumbent has no years before 2017
                continue
            spec = CANDIDATES[name]
            rows.append({"candidate": name, "asof_key": asof, "period": period, "n_years": len(group),
                         "mean_state_wape_pct": group["state_wape_pct"].mean(),
                         "mean_abs_us_error_pct": group["us_error_pct"].abs().mean(),
                         "mean_signed_us_error_pct": group["us_error_pct"].mean(),
                         "tier": spec["tier"], "eligible": spec["eligible"],
                         "diagnostic": spec.get("diagnostic", False)})
    return pd.DataFrame(rows)


def bootstrap_ci(diffs: np.ndarray, n: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    draws = diffs[rng.integers(0, len(diffs), size=(n, len(diffs)))].mean(axis=1)
    return float(np.percentile(draws, 5)), float(np.percentile(draws, 95))


def paired_rows(wide_wape: pd.DataFrame, wide_us: pd.DataFrame, name: str, other: str, lo: int, hi: int,
                labels: dict) -> list[dict]:
    rows = []
    for metric, wide in [("state_wape", wide_wape), ("abs_us_error", wide_us)]:
        if name not in wide or other not in wide:
            continue
        paired = wide.loc[lo:hi, [name, other]].dropna()
        if len(paired) < 2:
            continue
        diff = (paired[name] - paired[other]).to_numpy()
        ci = bootstrap_ci(diff)
        rows.append({**labels, "candidate": name, "comparator": other, "metric": metric, "n_years": len(diff),
                     "mean_candidate": paired[name].mean(), "mean_comparator": paired[other].mean(),
                     "mean_diff_points": diff.mean(), "ci90_lo": ci[0], "ci90_hi": ci[1],
                     "se_paired": float(diff.std(ddof=1) / np.sqrt(len(diff))),
                     "years_better": int((diff < -TIE).sum()), "years_worse": int((diff > TIE).sum())})
    return rows


def comparisons(by_year: pd.DataFrame, asof_key: str = PRIMARY_ASOF) -> pd.DataFrame:
    part = by_year[by_year["asof_key"] == asof_key]
    wide_wape = part.pivot(index="year", columns="candidate", values="state_wape_pct")
    wide_us = part.pivot(index="year", columns="candidate", values="us_error_pct").abs()
    rows = []
    for period, (lo, hi) in PERIODS.items():
        comparators = {"a_incumbent_reversion_only": "c0_incumbent_H13" if lo >= 2017 else SIMPLEST,
                       "b_persistence": "persistence", "c_simplest_own": SIMPLEST}
        for name in wide_wape.columns:
            for label, other in comparators.items():
                if other == name or (label == "a_incumbent_reversion_only" and other == SIMPLEST):
                    continue
                rows += paired_rows(wide_wape, wide_us, name, other, lo, hi,
                                    {"period": period, "asof_key": asof_key, "comparator_role": label})
    return pd.DataFrame(rows)


def select(by_year: pd.DataFrame, period: str = "2012-2024", asof_key: str = PRIMARY_ASOF) -> dict:
    """README 1.6: two-standard-error rule against c0 on paired years."""
    lo, hi = PERIODS[period]
    part = by_year[(by_year["asof_key"] == asof_key) & by_year["year"].between(lo, hi)]
    wide = part.pivot(index="year", columns="candidate", values="state_wape_pct")
    table = {}
    for name in SELECTION_ORDER:
        diff = (wide[name] - wide[SIMPLEST]).dropna().to_numpy()
        se = float(diff.std(ddof=1) / np.sqrt(len(diff)))
        table[name] = {"mean_wape": float(wide[name].mean()), "mean_diff_vs_c0": float(diff.mean()), "se": se,
                       "upper_2se": float(diff.mean() + 2 * se), "qualifies": bool(diff.mean() + 2 * se < 0),
                       "n_years": len(diff)}
    qualifying = [n for n in SELECTION_ORDER if table[n]["qualifies"]]
    selected = min(qualifying, key=lambda n: (table[n]["mean_wape"], SELECTION_ORDER.index(n))) if qualifying \
        else SIMPLEST
    return {"period": period, "asof_key": asof_key, "c0_mean_wape": float(wide[SIMPLEST].mean()),
            "candidates": table, "qualifying": qualifying, "selected": selected}


# --- benchmark reproduction -----------------------------------------------------------------------------------

def stored_backtest(series: str) -> pd.DataFrame:
    stored = pd.read_csv(DATA / "models" / "state_model_backtest.csv")
    return stored[(stored["scope"] == "all_states") & (stored["series"] == series)]


def compare_to_stored(mine: pd.DataFrame, stored: pd.DataFrame, names: dict) -> dict:
    report = {}
    for mine_name, stored_name in names.items():
        a = mine[mine["candidate"] == mine_name].set_index("year")
        b = stored[stored["predictor"] == stored_name].set_index("year")
        joined = a.join(b[["state_error_pct", "total_error_pct"]], how="inner").loc[2017:2024]
        exact = bool(len(joined) == 8 and (joined["state_wape_pct"].round(2) == joined["state_error_pct"]).all()
                     and (joined["us_error_pct"].round(2) == joined["total_error_pct"]).all())
        report[mine_name] = {"stored_predictor": stored_name, "years": [int(y) for y in joined.index],
                             "mine_state_wape": joined["state_wape_pct"].round(2).tolist(),
                             "stored_state_wape": joined["state_error_pct"].tolist(),
                             "mine_us_error": joined["us_error_pct"].round(2).tolist(),
                             "stored_us_error": joined["total_error_pct"].tolist(),
                             "mean_state_wape_2017_2024": round(float(joined["state_wape_pct"].mean()), 4),
                             "mean_abs_us_2017_2024": round(float(joined["us_error_pct"].abs().mean()), 4),
                             "stored_mean_state_wape": round(float(joined["state_error_pct"].mean()), 4),
                             "stored_mean_abs_us": round(float(joined["total_error_pct"].abs().mean()), 4),
                             "exact_to_2dp": exact}
    return report


def reproduce_silage(data: dict) -> tuple[pd.DataFrame, dict]:
    """reversion_only on the incumbent's panel (NASS finals from 2013) and persistence, 2017-2024."""
    rows, _ = build_rows(data, PRIMARY_ASOF, list(range(H13, LAST_TEST + 1)), start=H13, with_inputs=False)
    c0, _ = c0_out_of_sample(rows, data, H13)
    c0 = c0[c0["year"].between(2017, LAST_TEST)].assign(candidate="c0_incumbent_H13")
    pers = rows[rows["year"].between(2017, LAST_TEST) & rows["S1"].notna()]
    pers = pers[["state", "year"]].assign(candidate="persistence_H13", pred=pers["S1"])
    truth = data["finals"][["state", "year", "silage"]].rename(columns={"silage": "actual"})
    both = pd.concat([c0, pers], ignore_index=True).merge(truth, on=["state", "year"]).dropna(subset=["actual"])
    report = compare_to_stored(score_table(both), stored_backtest("silage"),
                               {"c0_incumbent_H13": "reversion_only", "persistence_H13": "same_as_last_year"})
    return c0, report


def reproduce_grain() -> dict:
    """Grain benchmarks (NASS latest by 15 Nov, persistence) from data/nass/corn_acres_state.csv, the incumbent's
    rule. The NASS grain forecast is read here only, to reproduce the team's benchmark; no model sees it."""
    acres = pd.read_csv(DATA / "nass" / "corn_acres_state.csv")
    final = acres[acres["period"] == "final"].pivot(index=["state", "year"], columns="series", values="acres")
    rows = []
    for year in range(2017, LAST_TEST + 1):
        now = final.xs(year, level="year")
        last = final.xs(year - 1, level="year").reindex(now.index)
        inseason = acres[(acres["year"] == year) & (acres["period"] != "final")]
        months = inseason["period"].map(REPORT_MONTH)
        inseason = inseason[months <= ASOF_MONTH[PRIMARY_ASOF]].assign(month=months)
        latest = inseason.sort_values("month").groupby(["series", "state"])["acres"].last()
        grain_fc = latest.get("grain", pd.Series(dtype=float)).reindex(now.index)
        planted_fc = latest.get("planted", pd.Series(dtype=float)).reindex(now.index)
        by_share = planted_fc * last["grain"] / last["planted"]
        nass = grain_fc.fillna(by_share).fillna(last["grain"])
        for name, pred in [("grain_nass_latest", nass), ("grain_persistence", last["grain"])]:
            part = pd.DataFrame({"pred": pred, "actual": now["grain"], "last": last["grain"]}).dropna()
            rows.append(part.rename_axis("state").reset_index().assign(year=year, candidate=name))
    return compare_to_stored(score_table(pd.concat(rows, ignore_index=True)), stored_backtest("grain"),
                             {"grain_nass_latest": "nass_latest", "grain_persistence": "same_as_last_year"})


# --- diagnostics ----------------------------------------------------------------------------------------------

def residual_diagnostics(base: pd.DataFrame, data: dict, years: list[int], asof_key: str) -> pd.DataFrame:
    """Why c5 is far from the oracle: errors of planted, own grain estimate and residual against year-t finals."""
    finals = data["finals"].set_index(["state", "year"])
    out = []
    for year in years:
        now = base[(base["year"] == year)].set_index("state")
        final = finals.reindex(pd.MultiIndex.from_product([now.index, [year]])).droplevel(1)
        for label, planted_col, grain_col, residual_col in [("c5", "P_nass", "grain_hat5", "residual_hat5"),
                                                            ("c5b", "P_hyb", "grain_hat5b", "residual_hat5b")]:
            ok = now[residual_col].notna() & final["grain"].notna() & final["planted"].notna()
            n, f = now[ok], final[ok]
            residual = f["planted"] - f["grain"]
            residual_last = n["P1"] - n["G1"]
            out.append({
                "asof_key": asof_key, "year": year, "variant": label, "n_states": int(ok.sum()),
                "planted_vintages": json.dumps(n["P_vintage"].value_counts().to_dict()),
                "planted_err_pct": 100 * (n[planted_col] - f["planted"]).abs().sum() / f["planted"].sum(),
                "grain_err_pct": 100 * (n[grain_col] - f["grain"]).abs().sum() / f["grain"].sum(),
                "grain_signed_pct": 100 * (n[grain_col] - f["grain"]).sum() / f["grain"].sum(),
                "residual_share_of_planted_pct": 100 * residual.sum() / f["planted"].sum(),
                "residual_err_pct": 100 * (n[residual_col] - residual).abs().sum() / residual.sum(),
                "residual_last_year_err_pct": 100 * (residual_last - residual).abs().sum() / residual.sum(),
                "residual_signed_pct": 100 * (n[residual_col] - residual).sum() / residual.sum(),
            })
    return pd.DataFrame(out)


def own_grain_score(base: pd.DataFrame, data: dict, years: list[int]) -> pd.DataFrame:
    """The own grain estimate (b1 form, c5's G_hat) scored as a grain forecast on NASS's 41 grain states."""
    finals = data["finals"].set_index(["state", "year"])
    rows = []
    for year in years:
        now = base[base["year"] == year].set_index("state")
        actual = finals.reindex(pd.MultiIndex.from_product([now.index, [year]])).droplevel(1)["grain"]
        for label, col in [("c5_grain_hat", "grain_hat5"), ("c5b_grain_hat", "grain_hat5b"),
                           ("grain_persistence", "G1")]:
            pred = now[col].where(now[col].notna(), now["G1"])
            ok = actual.notna() & pred.notna()
            miss = pred[ok] - actual[ok]
            rows.append({"year": year, "estimate": label, "n_states": int(ok.sum()),
                         "state_wape_pct": 100 * miss.abs().sum() / actual[ok].sum(),
                         "us_error_pct": 100 * miss.sum() / actual[ok].sum()})
    return pd.DataFrame(rows)


# --- pipeline -------------------------------------------------------------------------------------------------

def run_asof(data: dict, asof_key: str, years_to_predict: list[int]):
    rows, used = build_rows(data, asof_key, list(range(H00 + 1, max(years_to_predict) + 1)))
    preds, params, base = candidate_predictions(rows, data, years_to_predict)
    backtest_years = [y for y in years_to_predict if y <= LAST_TEST]
    if backtest_years:
        preds = pd.concat([preds, oracle_predictions(base, data, backtest_years)], ignore_index=True)
    month, day = ASOF[asof_key]
    preds["asof_key"] = asof_key
    preds["asof"] = [date(int(y), month, day).isoformat() for y in preds["year"]]
    for record in params:
        record["asof_key"] = asof_key
    return preds, params, used, base


def attach_truth(preds: pd.DataFrame, data: dict, base: pd.DataFrame) -> pd.DataFrame:
    part = preds[preds["year"] <= LAST_TEST].copy()
    actual = data["finals"][["state", "year", "silage"]].rename(columns={"silage": "actual"})
    part = part.merge(actual, on=["state", "year"], how="left")
    part = part.merge(base[["state", "year", "S1"]].rename(columns={"S1": "last"}), on=["state", "year"], how="left")
    return part[part["actual"].notna() & part["last"].notna()]


def preregistration_status() -> dict:
    text = README.read_text(encoding="utf-8")
    section = text[text.index(PREREG_START): text.index(PREREG_END) + len(PREREG_END)]
    now = hashlib.sha256(section.encode("utf-8")).hexdigest()
    stored_file = OUT / "preregistration.sha256"
    stored = stored_file.read_text(encoding="utf-8").split()[0] if stored_file.exists() else None
    return {"sha256_now": now, "sha256_stored": stored, "unchanged": now == stored}


def us_interval(held_out: pd.DataFrame, total: float, levels=(0.10, 0.90)) -> tuple[float, float]:
    totals = held_out.groupby("year")[["actual", "pred"]].sum()
    log_error = np.log(totals["actual"] / totals["pred"]).to_numpy()
    q = np.quantile(log_error, levels)
    return float(total * np.exp(q[0])), float(total * np.exp(q[1]))


def forecast_table(preds: pd.DataFrame, base: pd.DataFrame, held_out: pd.DataFrame, name: str,
                   year: int) -> pd.DataFrame:
    """State and US forecast of candidate ``name`` with 80% (and 90% state) intervals from backtest log errors."""
    chosen = preds[(preds["candidate"] == name) & (preds["year"] == year)].set_index("state")["pred"]
    last = base[base["year"] == year].set_index("state")["S1"]
    errors_rows = held_out.rename(columns={"pred": "predicted"})
    bounds = add_intervals(chosen, last, error_quantiles(errors_rows), "silage")
    table = pd.DataFrame({"silage": chosen}).join(bounds).join(last.rename("silage_last_year_nass"))
    table = table.rename_axis("state").reset_index().sort_values("silage", ascending=False)
    total = float(chosen.sum())
    lo80, hi80 = us_interval(held_out, total)
    us = {"state": "US (sum of states shown)", "silage": total, "silage_lo80": lo80, "silage_hi80": hi80,
          "silage_lo90": np.nan, "silage_hi90": np.nan,
          "silage_last_year_nass": float(last.reindex(chosen.index).sum())}
    table = pd.concat([pd.DataFrame([us]), table], ignore_index=True)
    acre_cols = [c for c in table.columns if c.startswith("silage")]
    table[acre_cols] = table[acre_cols].round(-2)
    return table.assign(year=year, candidate=name, asof=date(year, *ASOF[PRIMARY_ASOF]).isoformat())


def check_mode(data: dict) -> None:
    """Reproduction and input coverage only. No candidate is scored."""
    OUT.mkdir(parents=True, exist_ok=True)
    _, silage_report = reproduce_silage(data)
    grain_report = reproduce_grain()
    reproduction = {"silage": silage_report, "grain": grain_report, "data_checks": data["checks"]}
    (OUT / "reproduction.json").write_text(json.dumps(reproduction, indent=1, default=str) + "\n", encoding="utf-8")
    for series, report in [("silage", silage_report), ("grain", grain_report)]:
        for name, r in report.items():
            print(f"{series} {name}: mine {r['mean_state_wape_2017_2024']:.2f} / {r['mean_abs_us_2017_2024']:.2f}, "
                  f"stored {r['stored_mean_state_wape']:.2f} / {r['stored_mean_abs_us']:.2f}, "
                  f"exact={r['exact_to_2dp']}")
    rows, used = build_rows(data, PRIMARY_ASOF, list(range(2010, FORECAST_YEAR + 1)))
    features = ["P_nass", "F_pf_cur", "F_pf_prev"] + C4_FEATURES
    coverage = rows.groupby("year")[features].apply(lambda g: g.notna().mean()).round(2)
    print(coverage.to_string())
    print(rows.groupby("year")["P_vintage"].apply(lambda v: v.value_counts().to_dict()).to_string())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="reproduce benchmarks and print input coverage only")
    parser.add_argument("--prereg", action="store_true", help="hash README section 1 into out/preregistration.sha256")
    parser.add_argument("--score-2025", action="store_true", help="score the selected model on 2025, once")
    args = parser.parse_args()
    check_tiers()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.prereg:
        target = OUT / "preregistration.sha256"
        if target.exists():
            parser.error(f"{target} exists: the pre-registration is hashed once")
        status = preregistration_status()
        target.write_text(f"{status['sha256_now']}  README.md section 1\n", encoding="utf-8")
        print("pre-registration hashed:", status["sha256_now"])
        return

    data = load_all()
    if args.check:
        check_mode(data)
        return

    status = preregistration_status()
    if not status["unchanged"]:
        raise SystemExit(f"pre-registration missing or changed: {status}. Run --prereg first; never edit section 1.")

    c0_h13, silage_report = reproduce_silage(data)
    grain_report = reproduce_grain()
    if not all(r["exact_to_2dp"] for r in silage_report.values()):
        raise SystemExit("silage benchmark reproduction failed; nothing scored")
    reproduction = {"silage": silage_report, "grain": grain_report, "data_checks": data["checks"]}
    (OUT / "reproduction.json").write_text(json.dumps(reproduction, indent=1, default=str) + "\n", encoding="utf-8")

    if args.score_2025:
        score_2025(data)
        return

    test_years = list(range(FIRST_TEST, LAST_TEST + 1))
    all_preds, all_params, all_used, bases, diags, grain_scores = [], [], [], {}, [], []
    for asof_key in ASOF:
        preds, params, used, base = run_asof(data, asof_key, test_years + [FORECAST_YEAR])
        all_preds.append(preds)
        all_params += params
        all_used += used
        bases[asof_key] = base
        diags.append(residual_diagnostics(base, data, test_years, asof_key))
        grain_scores.append(own_grain_score(base, data, test_years).assign(asof_key=asof_key))
    preds = pd.concat(all_preds, ignore_index=True)
    h13 = c0_h13.assign(asof_key=PRIMARY_ASOF, asof=[date(int(y), 11, 15).isoformat() for y in c0_h13["year"]])
    backtest = pd.concat([attach_truth(preds, data, bases[k]) for k in ASOF]
                         + [attach_truth(h13, data, bases[PRIMARY_ASOF])], ignore_index=True)
    backtest = backtest[backtest["year"].between(FIRST_TEST, LAST_TEST)]
    backtest[["state", "year", "asof", "asof_key", "candidate", "pred", "actual", "last"]].sort_values(
        ["asof_key", "candidate", "year", "state"]).to_csv(OUT / "backtest_by_state_year.csv", index=False,
                                                          lineterminator="\n")

    by_year = pd.concat([score_table(g).assign(asof_key=k) for k, g in backtest.groupby("asof_key")],
                        ignore_index=True)
    by_year.to_csv(OUT / "by_year.csv", index=False, lineterminator="\n")
    summary = summarise(by_year)
    summary.to_csv(OUT / "summary.csv", index=False, lineterminator="\n")
    comp = pd.concat([comparisons(by_year, k) for k in ASOF], ignore_index=True)
    comp.to_csv(OUT / "comparisons.csv", index=False, lineterminator="\n")
    selection = select(by_year)
    selection["information_only"] = {p: select(by_year, p) for p in ("2017-2024", "2018-2024")}
    selected = selection["selected"]
    (OUT / "selection.json").write_text(json.dumps(selection, indent=1) + "\n", encoding="utf-8")
    pd.DataFrame(all_params).to_csv(OUT / "fitted_params.csv", index=False, lineterminator="\n")
    pd.DataFrame(all_used).to_csv(OUT / "inputs_used.csv", index=False, lineterminator="\n")
    pd.DataFrame([{"column": k, "input": v[0], "tier": INPUTS[v[0]][1], "source": INPUTS[v[0]][0], "definition": v[1]}
                  for k, v in COLUMNS.items()]).to_csv(OUT / "input_columns.csv", index=False, lineterminator="\n")
    pd.concat(diags, ignore_index=True).to_csv(OUT / "residual_diagnostics.csv", index=False, lineterminator="\n")
    pd.concat(grain_scores, ignore_index=True).to_csv(OUT / "own_grain_estimate_scores.csv", index=False,
                                                       lineterminator="\n")

    # post-hoc, information only: by region, and against Tier A's selected s3 (read from its own output file)
    nov = backtest[backtest["asof_key"] == PRIMARY_ASOF].assign(region=lambda d: d["state"].map(region_of))
    region = nov.groupby(["candidate", "region"]).apply(
        lambda g: pd.Series({"state_years": len(g), "pooled_wape_pct": 100 * (g["pred"] - g["actual"]).abs().sum()
                             / g["actual"].sum()}), include_groups=False).reset_index()
    region.to_csv(OUT / "by_region.csv", index=False, lineterminator="\n")
    tier_a = vs_tier_a(by_year, selected)
    if tier_a is not None:
        tier_a.to_csv(OUT / "vs_tierA_s3.csv", index=False, lineterminator="\n")

    # 2026 forecast of the selected model (and of every candidate, US totals) with intervals
    held = backtest[(backtest["asof_key"] == PRIMARY_ASOF) & (backtest["candidate"] == selected)]
    nov_preds = preds[preds["asof_key"] == PRIMARY_ASOF]
    forecast = forecast_table(nov_preds, bases[PRIMARY_ASOF], held, selected, FORECAST_YEAR)
    forecast.to_csv(OUT / "forecast_2026.csv", index=False, lineterminator="\n")
    totals = []
    for name in CANDIDATES:
        part = nov_preds[(nov_preds["candidate"] == name) & (nov_preds["year"] == FORECAST_YEAR)]
        held_c = backtest[(backtest["asof_key"] == PRIMARY_ASOF) & (backtest["candidate"] == name)]
        if part.empty or held_c["year"].nunique() < 13:
            continue
        lo, hi = us_interval(held_c, float(part["pred"].sum()))
        totals.append({"candidate": name, "us_total": round(float(part["pred"].sum()), -2), "us_lo80": round(lo, -2),
                       "us_hi80": round(hi, -2), "n_states": len(part)})
    pd.DataFrame(totals).to_csv(OUT / "forecast_2026_all_candidates.csv", index=False, lineterminator="\n")
    coverage = interval_coverage(held.rename(columns={"pred": "predicted"}))

    run = {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "preregistration": status,
           "selected": selected, "interval_coverage_leave_one_year_out": coverage,
           "fsa_2026_file": next((u for u in all_used if u["year"] == FORECAST_YEAR and u["asof_key"] == "nov"), None),
           "caveats": ["NASS in-season planted for 2012-2017 is the March Prospective Plantings figure only (no June "
                       "or later state vintage in the repo's Quick Stats pull for those years)",
                       "NASS finals, milk cows and RMA files are today's vintage (mild look-ahead)",
                       "FSA publication dates before 2025 are assumed (data date + 5 days)",
                       "2026 NASS planted is the September vintage: the October 2026 report is not in the repo"]}
    (OUT / "run.json").write_text(json.dumps(run, indent=1, default=str) + "\n", encoding="utf-8")

    pd.set_option("display.width", 220)
    show = summary[summary["asof_key"] == PRIMARY_ASOF].pivot_table(
        index="candidate", columns="period", values=["mean_state_wape_pct", "mean_abs_us_error_pct"]).round(2)
    print(show.to_string())
    print("selected:", selected)
    print(json.dumps({k: {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items()}
                      for k, v in selection["candidates"].items()}, indent=1))
    print(forecast.head(8).to_string(index=False))


def vs_tier_a(by_year: pd.DataFrame, selected: str) -> pd.DataFrame | None:
    if not TIER_A_BY_YEAR.exists():
        return None
    other = pd.read_csv(TIER_A_BY_YEAR)
    other = other[(other["candidate"] == "s3_fsa_residual") & (other["asof_key"] == PRIMARY_ASOF)]
    mine = by_year[by_year["asof_key"] == PRIMARY_ASOF]
    rows = []
    for name in dict.fromkeys([selected, *SELECTION_ORDER]):
        a = mine[mine["candidate"] == name].set_index("year")
        b = other.set_index("year")
        wide_wape = pd.DataFrame({name: a["state_wape_pct"], "tierA_s3_fsa_residual": b["state_wape_pct"]})
        wide_us = pd.DataFrame({name: a["us_error_pct"].abs(), "tierA_s3_fsa_residual": b["us_error_pct"].abs()})
        for period, (lo, hi) in PERIODS.items():
            rows += paired_rows(wide_wape, wide_us, name, "tierA_s3_fsa_residual", lo, hi,
                                {"period": period, "asof_key": PRIMARY_ASOF, "comparator_role": "post_hoc_tierA"})
    return pd.DataFrame(rows)


def score_2025(data: dict) -> None:
    """One information-only score of the selected model on 2025, fitted on years up to 2024. Refuses overwrite."""
    target, summary_file = OUT / "score_2025_information_only.csv", OUT / "score_2025_information_only.json"
    if target.exists() or summary_file.exists():
        raise SystemExit(f"{target} exists: 2025 is scored once")
    selected = json.loads((OUT / "selection.json").read_text(encoding="utf-8"))["selected"]
    preds, params, used, base = run_asof(data, PRIMARY_ASOF, [SCORING_YEAR])
    truth = data["finals"][data["finals"]["year"] == SCORING_YEAR].set_index("state")["silage"]
    held = pd.read_csv(OUT / "backtest_by_state_year.csv")
    held = held[(held["asof_key"] == PRIMARY_ASOF) & (held["candidate"] == selected)]
    table = forecast_table(preds, base, held, selected, SCORING_YEAR)
    states = table[~table["state"].str.startswith("US")].set_index("state")
    exact = preds[(preds["candidate"] == selected)].set_index("state")["pred"]
    pers = base[base["year"] == SCORING_YEAR].set_index("state")["S1"]
    compared = pd.DataFrame({"pred": exact, "actual": truth, "persistence": pers}).join(
        states[["silage_lo80", "silage_hi80"]]).dropna(subset=["pred", "actual"])
    summary = {"candidate": selected, "asof": f"{SCORING_YEAR}-11-15", "fitted_on_years_up_to": SCORING_YEAR - 1,
               "fsa_file": next((u for u in used if u["year"] == SCORING_YEAR), None), "params": params,
               "state_wape_pct": round(float(100 * (compared["pred"] - compared["actual"]).abs().sum()
                                             / compared["actual"].sum()), 2),
               "us_error_pct": round(float(100 * (compared["pred"].sum() - compared["actual"].sum())
                                           / compared["actual"].sum()), 2),
               "persistence_state_wape_pct": round(float(100 * (compared["persistence"] - compared["actual"]).abs()
                                                         .sum() / compared["actual"].sum()), 2),
               "persistence_us_error_pct": round(float(100 * (compared["persistence"].sum() - compared["actual"].sum())
                                                       / compared["actual"].sum()), 2),
               "inside_80": round(float(((compared["actual"] >= compared["silage_lo80"])
                                         & (compared["actual"] <= compared["silage_hi80"])).mean()), 3),
               "note": "information only; computed once after selection; never used for selection or tuning"}
    compared.rename_axis("state").reset_index().to_csv(target, index=False, lineterminator="\n")
    summary_file.write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("params", "fsa_file")}, indent=1))


if __name__ == "__main__":
    main()
