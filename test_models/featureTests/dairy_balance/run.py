"""County dairy feed-demand balance: does milk cows per corn acre explain silage share, and does it help the state model?

The balance (DOCS/research/dairy_prior.md, sections 5.2 and 8.2) predicts a county's silage share of corn as

    share_c = clip(k_s * milk_cows_c / corn_acres_c, 0.01, 0.98)

where k_s is the state's silage acres per milk cow. Silage is about two-thirds water and is chopped within a
few miles of the cows, so where cows are dense relative to corn, more of the corn should be chopped.

Three tests, each scored against the truth that exists for it:
  1. County cross-section: NASS county silage share by state-year against the balance, scored by R^2 and
     against a naive "every county gets the state share" baseline. A shuffled-cows placebo is reported too,
     because share (silage / corn) and density (cows / corn) share a denominator, which alone creates some
     correlation.
  2. County year over year: do cow-implied changes beat "same acres as last year"?
  3. State deliverable: a state silage candidate built from the county balance, scored exactly like the
     incumbent kernelag.state_model backtest (same panel truth, 48 states, 2017-2024, state WAPE and US
     total error), with a 90% state-cluster bootstrap interval on the WAPE difference. 2025 is info only.

Inputs (local files only; no NASS API key is used):
    data/Quickstats Data/milk_cow_inventory_county_2015_2025.csv        county milk cows: survey (1 Jan, most
                                                                         years, ~35 states) and Census (2017, 2022)
    data/Quickstats Data/corn_silage_harvested_acres_county_2015_2025.csv
    data/Quickstats Data/corn_grain_harvested_acres_county_2015_2025.csv
    data/Quickstats Data/corn_planted_acres_county_2015_2025.csv
    kernelag.state_panel.load_panel, kernelag.state_model               state truth and the incumbent backtest
    data/models/state_model_backtest.csv, state_score_2025.json          stored incumbent results (read only)
    data/labels/quebec_maize_2023.parquet                                descriptive only (silage share by latitude)

Outputs (test_models/featureTests/dairy_balance/out/):
    results.json          every headline number, the pre-registration and the verdict
    county_prior.csv      state_fips, county_fips, year, milk_cows, corn_planted, predicted_silage_share (+ audit)
    cross_section.csv     test 1 per state-year;  county_yoy.csv  test 2 per scheme, state and year
    state_balance.csv     the county balance per state-year;  state_predictions.csv, state_by_year.csv  test 3

Run from the repository root:
    .venv/Scripts/python.exe test_models/featureTests/dairy_balance/run.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / "out"
QUICKSTATS = REPO / "data" / "Quickstats Data"
QUEBEC_LABELS = REPO / "data" / "labels" / "quebec_maize_2023.parquet"
STORED_BACKTEST = REPO / "data" / "models" / "state_model_backtest.csv"
FROZEN_2025 = REPO / "data" / "models" / "state_score_2025.json"

ITEM = {"cows": "CATTLE, COWS, MILK - INVENTORY", "silage": "CORN, SILAGE - ACRES HARVESTED",
        "grain": "CORN, GRAIN - ACRES HARVESTED", "planted": "CORN - ACRES PLANTED"}
STEM = {"cows": "milk_cow_inventory", "silage": "corn_silage_harvested_acres",
        "grain": "corn_grain_harvested_acres", "planted": "corn_planted_acres"}
KEYS = ["state", "county_fips", "year"]
COUNTY_YEARS = list(range(2015, 2026))

SHARE_CLIP = (0.01, 0.98)     # dairy_prior.md 8.3: the prior never says "certainly grain" or "certainly silage"
MIN_COUNTIES = 8              # fewer counties than this and a state-year R^2 means little
CARRY_YEARS = 3               # county corn may be carried forward this many years (county planted 2021 is missing)
LAST_SCORED_YEAR = 2024       # 2025 is reported for information only, never used for a decision
BOOTSTRAP_DRAWS = 2000
PLACEBO_DRAWS = 200
SEED = 0
MAJOR_DAIRY = ["WI", "CA", "ID", "NY", "TX", "MI", "MN", "PA", "NM", "WA", "AZ", "CO", "IA", "OH", "VT"]

# Fixed before any state-level result was computed (test 3). The decision looks only at 2017-2024.
PREREGISTERED = {
    "primary_candidate": "balance_ridge",
    "primary_definition": "kernelag.state_model ridge on [reversion, d_balance]; d_balance = log(county balance "
                          "for this year / last year's silage); same panel, expanding window, MIN_FIT_YEARS, "
                          "weights and missing-as-no-change rule as the incumbent",
    "incumbent": "incumbent_reversion_only (kernelag.state_model selected set, data/models/state_model_backtest.csv)",
    "secondary": ["balance_ratio (unfitted county balance)", "cows_ridge ([reversion, d_cows], state cows)",
                  "cows_ratio (unfitted: last year x state cow change)", "persistence"],
    "metric": "mean over 2017-2024 of yearly state WAPE (48 states); US total error reported beside it",
    "adds_value_rule": "mean delta WAPE vs incumbent < 0 AND upper end of the 90% state-cluster bootstrap "
                       "interval < 0 AND gain > 2 paired-year standard errors (the team's existing rule)",
    "share_clip": list(SHARE_CLIP), "county_corn_carry_years": CARRY_YEARS,
    "bootstrap": f"{BOOTSTRAP_DRAWS} draws, states resampled with replacement (all years kept together), seed {SEED}",
}


# --- reading -------------------------------------------------------------------------------------

def read_county(kind: str, source: str) -> pd.DataFrame:
    """One Quick Stats county item: state, county_fips, year and the value. Withheld (D) values and the
    "other (combined) counties" rows are dropped: missing stays missing."""
    raw = pd.read_csv(QUICKSTATS / f"{STEM[kind]}_county_2015_2025.csv", dtype=str, keep_default_na=False)
    keep = ((raw["source_desc"] == source) & (raw["short_desc"] == ITEM[kind]) & (raw["domain_desc"] == "TOTAL")
            & ~raw["county_code"].isin(["998", ""]))
    rows = raw[keep]
    value = pd.to_numeric(rows["Value"].str.replace(",", "", regex=False).str.strip(), errors="coerce")
    out = pd.DataFrame({"state": rows["state_alpha"].to_numpy(),
                        "county_fips": (rows["state_fips_code"] + rows["county_code"]).to_numpy(),
                        "year": rows["year"].astype(int).to_numpy(), kind: value.to_numpy()}).dropna(subset=[kind])
    if out.duplicated(["county_fips", "year"]).any():
        raise ValueError(f"duplicate county-year rows in {kind} {source}")
    return out


def state_alpha_map() -> dict[str, str]:
    """Quick Stats state name (as in the state panel) to its two-letter code."""
    raw = pd.read_csv(QUICKSTATS / "milk_cow_inventory_state_2000_2026.csv", dtype=str, keep_default_na=False,
                      usecols=["state_name", "state_alpha"])
    raw = raw.drop_duplicates()
    return dict(zip(raw["state_name"], raw["state_alpha"]))


def load_state_table() -> pd.DataFrame:
    """The incumbent's own state-year table (kernelag.state_panel + state_model.add_changes), plus state codes
    and the state ratios the balance needs. Nothing here is refitted or rewritten."""
    from kernelag import state_model
    from kernelag.state_panel import load_panel

    table = state_model.add_changes(load_panel("nov"))
    table["alpha"] = table["state"].map(state_alpha_map())
    if table["alpha"].isna().any():
        raise ValueError(f"unmapped states: {sorted(table.loc[table['alpha'].isna(), 'state'].unique())}")
    with np.errstate(divide="ignore", invalid="ignore"):
        table["k"] = table["silage"] / table["milk_cows"]                      # silage acres per milk cow
        table["share_planted"] = table["silage"] / table["planted"]
        table["share_harvested"] = table["silage"] / (table["silage"] + table["grain"])
    return table.replace([np.inf, -np.inf], np.nan)


def previous_year(table: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """State values of the previous calendar year keyed by (state code, year)."""
    prev = table[["alpha", "year", *columns]].assign(year=table["year"] + 1)
    return prev.rename(columns={"alpha": "state", **{c: f"{c}_prev" for c in columns}})


def carried(long: pd.DataFrame, column: str) -> pd.DataFrame:
    """Each county's latest value at or before every year, at most CARRY_YEARS old, with the year it came from."""
    long = long.assign(source_year=long["year"].astype(float))
    stacked = []
    for name in [column, "source_year"]:
        wide = long.pivot(index=["state", "county_fips"], columns="year", values=name).reindex(columns=COUNTY_YEARS)
        stacked.append(wide.ffill(axis=1, limit=CARRY_YEARS).stack().rename(name))
    out = pd.concat(stacked, axis=1).dropna().reset_index()
    return out.astype({"year": int, "source_year": int})


def clip_share(x: np.ndarray | float) -> np.ndarray:
    return np.clip(x, *SHARE_CLIP)


# --- test 1: county cross-section -----------------------------------------------------------------

def cross_section_rows() -> tuple[pd.DataFrame, int]:
    """County rows with share and density for two definitions.

    census_harvested  Census 2017 and 2022: silage / (silage + grain) harvested, Census milk cows (31 Dec).
                      Same source on both sides; every state. Census does not publish planted acres.
    survey_planted    Annual survey: silage / planted (the task's definition), survey milk cows (1 Jan).
                      Only states where NASS publishes county silage (WI, NY, PA, MN, IA, ND, part of CA).
    """
    census = (read_county("silage", "CENSUS").merge(read_county("grain", "CENSUS"), on=KEYS)
              .merge(read_county("cows", "CENSUS"), on=KEYS))
    census = census.assign(panel="census_harvested", corn=census["silage"] + census["grain"])
    survey = (read_county("silage", "SURVEY").merge(read_county("planted", "SURVEY"), on=KEYS)
              .merge(read_county("cows", "SURVEY"), on=KEYS))
    survey = survey.assign(panel="survey_planted", corn=survey["planted"])
    rows = pd.concat([census, survey], ignore_index=True)
    rows = rows[rows["corn"] > 0].copy()
    rows["share"] = rows["silage"] / rows["corn"]
    rows["density"] = rows["cows"] / rows["corn"]
    # A county reporting more silage than planted corn is inconsistent; it is dropped, not repaired.
    inconsistent = int((rows["share"] > 1).sum())
    return rows[rows["share"] <= 1].reset_index(drop=True), inconsistent


def score_state_year(g: pd.DataFrame, k_prev: float, naive_prev: float, rng: np.random.Generator) -> dict:
    """Sums of squared and absolute errors for the balance and the naive state share, in and out of sample."""
    share, density = g["share"].to_numpy(), g["density"].to_numpy()
    silage, corn, cows = g["silage"].to_numpy(), g["corn"].to_numpy(), g["cows"].to_numpy()
    out = {"n_counties": len(g), "silage_sum": silage.sum(), "sst": ((share - share.mean()) ** 2).sum(),
           "r2_linear": float(np.corrcoef(share, density)[0, 1] ** 2) if len(g) > 2 and density.std() > 0 else np.nan}
    # In sample: k and the naive share come from these same counties (the research note's method, an upper bound).
    k_in, naive_in = silage.sum() / cows.sum(), silage.sum() / corn.sum()
    pred_in = clip_share(k_in * density)
    out.update(k_in=k_in, naive_in=naive_in, sse_rule_in=((pred_in - share) ** 2).sum(),
               sse_naive_in=((naive_in - share) ** 2).sum(), abs_rule_in=np.abs(pred_in - share).sum(),
               abs_naive_in=np.abs(naive_in - share).sum(), acre_err_rule_in=np.abs(pred_in * corn - silage).sum(),
               acre_err_naive_in=np.abs(naive_in * corn - silage).sum())
    # Placebo: the same cows shuffled among the state's counties. What survives is the shared-denominator effect.
    placebo = [((clip_share(k_in * rng.permutation(cows) / corn) - share) ** 2).sum() for _ in range(PLACEBO_DRAWS)]
    out["sse_placebo_in"] = float(np.mean(placebo))
    # Out of sample: k and the naive share from last year's NASS state totals (what a forecaster would have).
    out.update(k_prev=k_prev, naive_prev=naive_prev)
    for name, value, column in [("rule", k_prev, "sse_rule_out"), ("naive", naive_prev, "sse_naive_out")]:
        if np.isfinite(value):
            pred = clip_share(value * density) if name == "rule" else np.full_like(share, value)
            out[column] = ((pred - share) ** 2).sum()
            out[f"abs_{name}_out"] = np.abs(pred - share).sum()
            out[f"acre_err_{name}_out"] = np.abs(pred * corn - silage).sum()
        else:
            out[column] = out[f"abs_{name}_out"] = out[f"acre_err_{name}_out"] = np.nan
    return out


def summarise_errors(frame: pd.DataFrame) -> dict:
    """R^2, skill against the naive share and acre errors from summed error terms (one state-year or pooled).

    Pooling sums squared errors over state-years, so R^2 is measured around each state-year's own mean
    (within-state): the large differences between states cannot flatter it. Out-of-sample terms are pooled
    only over state-years that have them, so a missing previous year is never read as a zero error.
    """
    def ratio(sums: pd.Series, a: str, b: str) -> float:
        return float(1 - sums[a] / sums[b]) if sums[b] > 0 else np.nan

    s = frame.sum(numeric_only=True)
    n = s["n_counties"]
    result = {
        "n_counties": int(n),
        "r2_rule_in": ratio(s, "sse_rule_in", "sst"), "skill_vs_naive_in": ratio(s, "sse_rule_in", "sse_naive_in"),
        "placebo_skill_vs_naive_in": ratio(s, "sse_placebo_in", "sse_naive_in"),
        "mae_rule_in": float(s["abs_rule_in"] / n), "mae_naive_in": float(s["abs_naive_in"] / n),
    }
    with_out = frame[frame["sse_rule_out"].notna() & frame["sse_naive_out"].notna()]
    o = with_out.sum(numeric_only=True)
    n_out = o["n_counties"] if len(with_out) else 0
    result.update({
        "n_counties_out": int(n_out),
        "r2_rule_out": ratio(o, "sse_rule_out", "sst") if n_out else np.nan,
        "skill_vs_naive_out": ratio(o, "sse_rule_out", "sse_naive_out") if n_out else np.nan,
        "mae_rule_out": float(o["abs_rule_out"] / n_out) if n_out else np.nan,
        "mae_naive_out": float(o["abs_naive_out"] / n_out) if n_out else np.nan,
        "acre_wape_rule_out_pct": float(100 * o["acre_err_rule_out"] / o["silage_sum"]) if n_out else np.nan,
        "acre_wape_naive_out_pct": float(100 * o["acre_err_naive_out"] / o["silage_sum"]) if n_out else np.nan,
    })
    return result


def cross_section(table: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, dict]:
    rows, inconsistent = cross_section_rows()
    prev = previous_year(table, ["k", "share_planted", "share_harvested"])
    rows = rows.merge(prev, on=["state", "year"], how="left")
    records = []
    for (panel, state, year), g in rows.groupby(["panel", "state", "year"]):
        if len(g) < MIN_COUNTIES or g["cows"].sum() <= 0:
            continue
        naive_column = "share_harvested_prev" if panel == "census_harvested" else "share_planted_prev"
        record = score_state_year(g, float(g["k_prev"].iloc[0]), float(g[naive_column].iloc[0]), rng)
        records.append({"panel": panel, "state": state, "year": int(year), **record})
    per = pd.DataFrame(records)
    metrics = pd.DataFrame([summarise_errors(per.iloc[[i]]) for i in range(len(per))])
    per = pd.concat([per, metrics.drop(columns="n_counties")], axis=1)
    scored = per[per["year"] <= LAST_SCORED_YEAR]
    summary = {"rows_dropped_share_above_1": inconsistent, "min_counties_per_state_year": MIN_COUNTIES}
    for panel, part in scored.groupby("panel"):
        by_state = {}
        for state, g in part.groupby("state"):
            by_state[state] = {"years": sorted(int(y) for y in g["year"]),
                               "mean_r2_linear": float(g["r2_linear"].mean()), **summarise_errors(g)}
        majors = part[part["state"].isin(MAJOR_DAIRY)]
        summary[panel] = {
            "state_years": len(part), "states": int(part["state"].nunique()),
            "pooled_within_state": summarise_errors(part),
            "pooled_major_dairy_states": summarise_errors(majors) if len(majors) else None,
            "states_where_balance_beats_naive_out": int(sum(v["skill_vs_naive_out"] > 0 for v in by_state.values())),
            "states_with_out_of_sample_score": int(sum(np.isfinite(v["skill_vs_naive_out"]) for v in by_state.values())),
            "by_state": by_state,
        }
    summary["reproduction_wi_2022"] = reproduce_wisconsin(rows)
    return per, summary


def reproduce_wisconsin(rows: pd.DataFrame) -> dict:
    """The research note's Wisconsin 2022 Census check, recomputed from the local Quick Stats file with its
    exact rule (in-sample k, min(1, k x density), no floor)."""
    g = rows[(rows["panel"] == "census_harvested") & (rows["state"] == "WI") & (rows["year"] == 2022)]
    k = g["silage"].sum() / g["cows"].sum()
    slope, intercept = np.polyfit(g["density"], g["share"], 1)
    return {"n_counties": len(g), "r2_linear": float(np.corrcoef(g["share"], g["density"])[0, 1] ** 2),
            "fit": f"share = {intercept:.3f} + {slope:.3f} x cows per corn acre", "k": float(k),
            "mae_rule": float(np.abs(np.minimum(1, k * g["density"]) - g["share"]).mean()),
            "mae_state_share": float(np.abs(g["silage"].sum() / g["corn"].sum() - g["share"]).mean()),
            "research_note_claim": "63 counties, R^2 0.87 (0.866), share = 0.002 + 0.663x, k 0.623, MAE 0.041 vs 0.112"}


# --- test 2: county year over year ----------------------------------------------------------------

def yoy_rows(table: pd.DataFrame) -> pd.DataFrame:
    """County pairs (last year, this year) with three predictions of this year's silage acres:

    persistence   last year's acres
    cow_scaled    last year's acres x this year's cows / last year's cows (the county's own k, held fixed)
    state_k       clip(k_state(y-1) x cows / corn) x corn, corn = latest county corn at or before y-1
    """
    prev_k = previous_year(table, ["k"])
    frames = []
    # Annual survey (county silage is published only where NASS runs county estimates for it).
    current = read_county("silage", "SURVEY").merge(read_county("cows", "SURVEY"), on=KEYS)
    last = current.assign(year=current["year"] + 1).rename(columns={"silage": "silage_last", "cows": "cows_last"})
    pairs = current.merge(last, on=KEYS)
    corn = carried(read_county("planted", "SURVEY"), "planted")
    corn = corn.assign(year=corn["year"] + 1).rename(columns={"planted": "corn_last"})[[*KEYS, "corn_last"]]
    frames.append(pairs.merge(corn, on=KEYS, how="left").assign(scheme="survey_annual"))
    # Census to Census, 2017 -> 2022, every state: a five-year change.
    census = (read_county("silage", "CENSUS").merge(read_county("cows", "CENSUS"), on=KEYS)
              .merge(read_county("grain", "CENSUS"), on=KEYS))
    c17 = census[census["year"] == 2017].assign(corn_last=lambda d: d["silage"] + d["grain"])
    c17 = c17.rename(columns={"silage": "silage_last", "cows": "cows_last"}).assign(year=2022)
    c22 = census[census["year"] == 2022][[*KEYS, "silage", "cows"]]
    frames.append(c22.merge(c17[[*KEYS, "silage_last", "cows_last", "corn_last"]], on=KEYS)
                  .assign(scheme="census_2017_2022"))
    rows = pd.concat(frames, ignore_index=True).merge(prev_k, on=["state", "year"], how="left")
    rows = rows[(rows["silage_last"] > 0) & (rows["cows_last"] > 0) & (rows["silage"] > 0)].copy()
    rows["persistence"] = rows["silage_last"]
    rows["cow_scaled"] = rows["silage_last"] * rows["cows"] / rows["cows_last"]
    with np.errstate(divide="ignore", invalid="ignore"):
        rows["state_k"] = clip_share(rows["k_prev"] * rows["cows"] / rows["corn_last"]) * rows["corn_last"]
        rows["dlog_silage"] = np.log(rows["silage"] / rows["silage_last"])
        rows["dlog_cows"] = np.log(rows["cows"] / rows["cows_last"])
    rows = rows.replace([np.inf, -np.inf], np.nan)
    # Paired comparison: only pairs where every predictor exists.
    return rows.dropna(subset=["persistence", "cow_scaled", "state_k", "dlog_cows"]).reset_index(drop=True)


def yoy(table: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = yoy_rows(table)
    predictors = ["persistence", "cow_scaled", "state_k"]
    records = []
    for (scheme, state, year), g in rows.groupby(["scheme", "state", "year"]):
        record = {"scheme": scheme, "state": state, "year": int(year), "n_counties": len(g),
                  "actual_acres": g["silage"].sum()}
        for p in predictors:
            record[f"wape_{p}_pct"] = 100 * (g[p] - g["silage"]).abs().sum() / g["silage"].sum()
        record["corr_dlog_silage_cows"] = (float(g["dlog_silage"].corr(g["dlog_cows"])) if len(g) > 2 else np.nan)
        records.append(record)
    per = pd.DataFrame(records)
    summary = {}
    for scheme, part in rows[rows["year"] <= LAST_SCORED_YEAR].groupby("scheme"):
        state_years = per[(per["scheme"] == scheme) & (per["year"] <= LAST_SCORED_YEAR)]
        summary[scheme] = {
            "county_pairs": len(part), "states": sorted(part["state"].unique().tolist()),
            "years": sorted(int(y) for y in part["year"].unique()),
            "pooled_wape_pct": {p: float(100 * (part[p] - part["silage"]).abs().sum() / part["silage"].sum())
                                for p in predictors},
            "state_years": len(state_years),
            "state_years_beating_persistence": {p: int((state_years[f"wape_{p}_pct"]
                                                        < state_years["wape_persistence_pct"]).sum())
                                                for p in predictors[1:]},
            "pooled_corr_dlog_silage_vs_dlog_cows": float(part["dlog_silage"].corr(part["dlog_cows"])),
            "median_abs_dlog_silage": float(part["dlog_silage"].abs().median()),
            "median_abs_dlog_cows": float(part["dlog_cows"].abs().median()),
        }
    return per, summary


# --- test 3: state deliverable --------------------------------------------------------------------

def calibrate_k(cows: np.ndarray, corn: np.ndarray, target: float) -> tuple[float, str]:
    """The acres-per-cow k at which the clipped county balance adds up to ``target`` (last year's state acres).

    Plain silage / cows is not enough: counties at the 0.98 cap cannot take more, so k must rise to make up
    the total. The clipped total is non-decreasing in k, so bisection finds it.
    """
    low, high = SHARE_CLIP

    def total(k: float) -> float:
        return float(np.clip(k * cows, low * corn, high * corn).sum())

    if target <= total(0.0):
        return 0.0, "floor"
    positive = cows > 0
    k_max = float((high * corn[positive] / cows[positive]).max()) if positive.any() else 0.0
    if target >= total(k_max):
        return k_max, "capped"
    a, b = 0.0, k_max
    for _ in range(100):
        middle = (a + b) / 2
        a, b = (middle, b) if total(middle) < target else (a, middle)
    return (a + b) / 2, "ok"


def balance_parts(k: float, cows: np.ndarray, corn: np.ndarray) -> np.ndarray:
    """Silage acres per county under the clipped balance."""
    return np.clip(k * cows, SHARE_CLIP[0] * corn, SHARE_CLIP[1] * corn)


def state_balance(table: pd.DataFrame) -> pd.DataFrame:
    """The county balance for each state and year 2016-2025, from information public before the season ends.

    For year y: county cows and county corn shares of y-1 (survey; corn shares carried at most CARRY_YEARS),
    scaled to the state's 1 January y milk cows and the latest in-season planted acres. Counties without both
    numbers, and withheld counties, form one remainder "county" so the state totals are kept. k is set so the
    balance reproduces y-1's state silage exactly; the forecast is the balance re-run with this year's cows and
    corn. Without any county at the cap this equals last year's acres x the state cow change (cows_ratio): the
    county structure matters only through counties whose corn supply, not cow demand, limits the silage.
    """
    cows = read_county("cows", "SURVEY")
    planted = read_county("planted", "SURVEY")
    state_planted = table[["alpha", "year", "planted"]].rename(columns={"alpha": "state", "planted": "state_planted"})
    planted = planted.merge(state_planted, on=["state", "year"])
    planted["corn_share"] = planted["planted"] / planted["state_planted"]
    shares = carried(planted[[*KEYS, "corn_share"]], "corn_share")
    cows_by = {key: g.set_index("county_fips")["cows"] for key, g in cows.groupby(["state", "year"])}
    shares_by = {key: g.set_index("county_fips")["corn_share"] for key, g in shares.groupby(["state", "year"])}
    rows_by = table.set_index(["alpha", "year"])
    records = []
    for alpha in sorted(table["alpha"].unique()):
        for year in range(2016, 2026):
            record = {"state": rows_by.loc[(alpha, year), "state"], "alpha": alpha, "year": year}
            prev, cur = rows_by.loc[(alpha, year - 1)], rows_by.loc[(alpha, year)]
            silage, planted_prev, cows_prev = prev["silage"], prev["planted"], prev["milk_cows"]
            if not all(np.isfinite(v) and v > 0 for v in [silage, planted_prev, cows_prev]):
                records.append({**record, "method": "missing_state_inputs"})
                continue
            county_cows = cows_by.get((alpha, year - 1), pd.Series(dtype=float))
            county_share = shares_by.get((alpha, year - 1), pd.Series(dtype=float))
            matched = county_cows.index.intersection(county_share.index)
            cows_m = county_cows[matched].to_numpy(float)
            corn_m = county_share[matched].to_numpy(float) * planted_prev
            rest_cows, rest_corn = max(cows_prev - cows_m.sum(), 0.0), max(planted_prev - corn_m.sum(), 0.0)
            cows_all, corn_all = np.append(cows_m, rest_cows), np.append(corn_m, rest_corn)
            k, status = calibrate_k(cows_all, corn_all, silage)
            r = cur["milk_cows"] / cows_prev if np.isfinite(cur["milk_cows"]) else 1.0
            p = cur["planted_asof"] / planted_prev if np.isfinite(cur["planted_asof"]) else 1.0
            parts = balance_parts(k * r, cows_all, corn_all * p)
            at_cap = (k * r * cows_all >= SHARE_CLIP[1] * corn_all * p) & (corn_all > 0)
            records.append({**record, "method": "county" if len(matched) else "state_only", "calibration": status,
                            "silage_last": silage, "balance": parts.sum(), "cows_ratio": silage * r,
                            "k": k, "cow_change": r, "planted_change": p,
                            "n_counties": len(matched), "matched_cow_share": cows_m.sum() / cows_prev,
                            "matched_corn_share": corn_m.sum() / planted_prev,
                            "corn_limited_share": parts[at_cap].sum() / parts.sum()})
    return pd.DataFrame(records)


def state_candidates(table: pd.DataFrame, balance: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Held-out state predictions for 2017-2024 (and 2025, info only) for every candidate."""
    from kernelag import state_model

    table = table.merge(balance[["state", "year", "balance"]], on=["state", "year"], how="left")
    with np.errstate(divide="ignore", invalid="ignore"):
        table["d_balance"] = np.log(table["balance"] / table["silage_last"])
    table = table.replace([np.inf, -np.inf], np.nan)
    usable = table[(table["year"] <= LAST_SCORED_YEAR) & table["target"].notna()]
    years = sorted(usable["year"].unique())[state_model.MIN_FIT_YEARS:]
    parts = []
    for year in [*years, LAST_SCORED_YEAR + 1]:
        # Backtest years use exactly the incumbent's rows; 2025 is fitted on <= 2024 and only reported.
        source = usable if year <= LAST_SCORED_YEAR else table
        truth = table[table["year"] == year].set_index("state")
        predictions = {
            "persistence": truth["silage_last"],
            "incumbent_reversion_only": state_model.predict_silage(source, year, ["reversion"]),
            "balance_ridge": state_model.predict_silage(source, year, ["reversion", "d_balance"]),
            "cows_ridge": state_model.predict_silage(source, year, ["reversion", "d_cows"]),
            "balance_ratio": truth["balance"].fillna(truth["silage_last"]),
            "cows_ratio": truth["silage_last"] * np.exp(truth["d_cows"].fillna(0.0)),
        }
        for name, predicted in predictions.items():
            part = pd.DataFrame({"predicted": predicted, "actual": truth["silage"], "last": truth["silage_last"]})
            parts.append(part.dropna().rename_axis("state").reset_index().assign(year=year, candidate=name))
    out = pd.concat(parts, ignore_index=True)[["year", "state", "candidate", "predicted", "actual", "last"]]
    # Weights of the fits on every year up to 2024, per standardized feature (sign check, not a selection).
    weights = {name: {f: float(w) for f, w in state_model.fit_ridge(usable, features).weights.items()}
               for name, features in [("balance_ridge", ["reversion", "d_balance"]),
                                      ("cows_ridge", ["reversion", "d_cows"]),
                                      ("incumbent_reversion_only", ["reversion"])]}
    return out, weights


def by_year(predictions: pd.DataFrame) -> pd.DataFrame:
    def score(g: pd.DataFrame) -> pd.Series:
        miss = g["predicted"] - g["actual"]
        return pd.Series({"n_states": len(g), "state_wape_pct": 100 * miss.abs().sum() / g["actual"].sum(),
                          "us_error_pct": 100 * miss.sum() / g["actual"].sum()})
    return predictions.groupby(["candidate", "year"])[["predicted", "actual"]].apply(score).reset_index()


def paired_delta(predictions: pd.DataFrame, candidate: str, reference: str, years: list[int],
                 rng: np.random.Generator) -> dict:
    """Mean over years of (candidate - reference) state WAPE, with a 90% state-cluster bootstrap interval,
    a year bootstrap interval and the paired-year standard error."""
    def wide(name: str, column: str) -> pd.DataFrame:
        part = predictions[(predictions["candidate"] == name) & predictions["year"].isin(years)]
        return part.pivot(index="year", columns="state", values=column).sort_index()
    actual = wide(reference, "actual")
    cand = (wide(candidate, "predicted") - wide(candidate, "actual")).abs().reindex_like(actual)
    ref = (wide(reference, "predicted") - actual).abs()
    if actual.isna().any().any() or cand.isna().any().any():
        raise ValueError(f"{candidate} vs {reference}: states differ between candidates")
    a, c, r = actual.to_numpy(), cand.to_numpy(), ref.to_numpy()
    yearly = 100 * (c.sum(1) - r.sum(1)) / a.sum(1)
    n_states = a.shape[1]
    weights = rng.multinomial(n_states, np.full(n_states, 1 / n_states), size=BOOTSTRAP_DRAWS).T
    draws = (100 * ((c @ weights) - (r @ weights)) / (a @ weights)).mean(axis=0)
    year_draws = yearly[rng.integers(0, len(yearly), size=(BOOTSTRAP_DRAWS, len(yearly)))].mean(axis=1)
    se = float(yearly.std(ddof=1) / np.sqrt(len(yearly)))
    return {"candidate": candidate, "reference": reference, "years": [int(y) for y in actual.index],
            "mean_delta_wape_points": float(yearly.mean()),
            "ci90_state_bootstrap": [float(np.percentile(draws, 5)), float(np.percentile(draws, 95))],
            "ci90_year_bootstrap": [float(np.percentile(year_draws, 5)), float(np.percentile(year_draws, 95))],
            "paired_year_se": se, "years_better": int((yearly < 0).sum()),
            "passes_two_se_rule": bool(-yearly.mean() > 2 * se),
            "yearly_delta": {int(y): float(d) for y, d in zip(actual.index, yearly)}}


def state_test(table: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
                                                                        dict]:
    balance = state_balance(table)
    predictions, final_weights = state_candidates(table, balance)
    yearly = by_year(predictions)
    years = sorted(int(y) for y in yearly["year"].unique() if y <= LAST_SCORED_YEAR)
    scored = yearly[yearly["year"].isin(years)]
    summary_by = scored.groupby("candidate").agg(mean_state_wape_pct=("state_wape_pct", "mean"),
                                                 mean_abs_us_error_pct=("us_error_pct", lambda s: s.abs().mean()))

    # The reproduced incumbent and persistence must equal the stored backtest, or nothing is like for like.
    stored = pd.read_csv(STORED_BACKTEST)
    stored = stored[(stored["scope"] == "all_states") & (stored["series"] == "silage")]
    check = {}
    for mine, theirs in [("incumbent_reversion_only", "reversion_only"), ("persistence", "same_as_last_year")]:
        a = scored[scored["candidate"] == mine].set_index("year")["state_wape_pct"]
        b = stored[stored["predictor"] == theirs].set_index("year")["state_error_pct"]
        check[mine] = {"stored_predictor": theirs, "max_abs_diff_points": float((a.round(2) - b).abs().max()),
                       "years_compared": int(b.index.isin(a.index).sum())}
    if max(v["max_abs_diff_points"] for v in check.values()) > 0.011:
        raise RuntimeError(f"incumbent reproduction failed: {check}")

    comparisons = [("balance_ridge", "incumbent_reversion_only"), ("balance_ratio", "incumbent_reversion_only"),
                   ("cows_ridge", "incumbent_reversion_only"), ("balance_ridge", "cows_ridge"),
                   ("balance_ratio", "cows_ratio"), ("balance_ratio", "persistence"),
                   ("cows_ratio", "persistence"), ("incumbent_reversion_only", "persistence")]
    deltas = [paired_delta(predictions, c, r, years, rng) for c, r in comparisons]
    primary = deltas[0]
    adds_value = (primary["mean_delta_wape_points"] < 0 and primary["ci90_state_bootstrap"][1] < 0
                  and primary["passes_two_se_rule"])

    scored_balance = balance[balance["year"].isin(years)]
    truth = predictions[(predictions["candidate"] == "persistence") & predictions["year"].isin(years)]
    acres = truth.set_index(["state", "year"])["actual"]
    coverage = scored_balance.assign(w=acres.reindex(pd.MultiIndex.from_frame(scored_balance[["state", "year"]]))
                                     .to_numpy())
    county_states = coverage[coverage["method"] == "county"]
    gap = np.log(county_states["balance"] / county_states["cows_ratio"])
    info_2025 = yearly[yearly["year"] == LAST_SCORED_YEAR + 1].set_index("candidate")[["state_wape_pct",
                                                                                         "us_error_pct"]]
    frozen = json.loads(FROZEN_2025.read_text(encoding="utf-8"))["silage"] if FROZEN_2025.exists() else None
    summary = {
        "years": years, "states": int(scored["n_states"].min()),
        "truth": "kernelag.state_panel 'silage' (data/nass/corn_acres_state.csv final), as the incumbent",
        "mean_by_candidate": {c: {k: float(v) for k, v in row.items()} for c, row in summary_by.iterrows()},
        "incumbent_reproduction": check,
        "deltas": deltas,
        "primary_adds_value": bool(adds_value),
        "final_fit_weights_per_std": final_weights,
        "balance_coverage": {
            "state_years_with_county_structure": int((scored_balance["method"] == "county").sum()),
            "state_years_total": len(scored_balance),
            "silage_acre_share_in_county_states": float(county_states["w"].sum() / coverage["w"].sum()),
            "median_matched_cow_share": float(county_states["matched_cow_share"].median()),
            "silage_weighted_corn_limited_share": float((county_states["corn_limited_share"] * county_states["w"])
                                                        .sum() / county_states["w"].sum()),
            "states_corn_limited_over_25pct": sorted(county_states.groupby("alpha")["corn_limited_share"].mean()
                                                     .loc[lambda s: s > 0.25].index.tolist()),
            "calibration_status_counts": scored_balance["calibration"].value_counts().to_dict(),
            "county_states_mean_abs_log_gap_balance_vs_cows_ratio": float(gap.abs().mean()),
            "county_states_share_with_gap_over_1pct": float((gap.abs() > 0.01).mean()),
        },
        "info_only_2025": {"note": "fitted on <= 2024; never used for any choice; the stored 2025 score is frozen",
                           "state_wape_pct": info_2025["state_wape_pct"].round(2).to_dict(),
                           "us_error_pct": info_2025["us_error_pct"].round(2).to_dict(),
                           "frozen_stored_score": frozen},
    }
    return balance, predictions, yearly, summary


# --- county prior for field-level use ----------------------------------------------------------------

def county_prior(table: pd.DataFrame) -> pd.DataFrame:
    """The balance per county-year: survey cows on 1 January of the year, the latest county corn planted at
    or before the year (at most CARRY_YEARS old), and k from the previous year's state totals. Missing inputs
    give no row (never a guess)."""
    cows = read_county("cows", "SURVEY")
    corn = carried(read_county("planted", "SURVEY"), "planted").rename(columns={"source_year": "corn_planted_year"})
    prior = cows.merge(corn, on=KEYS).merge(previous_year(table, ["k"]), on=["state", "year"], how="left")
    prior = prior[prior["planted"] > 0]
    prior["predicted_silage_share"] = clip_share(prior["k_prev"] * prior["cows"] / prior["planted"])
    out = pd.DataFrame({"state_fips": prior["county_fips"].str[:2], "county_fips": prior["county_fips"],
                        "year": prior["year"], "milk_cows": prior["cows"], "corn_planted": prior["planted"],
                        "predicted_silage_share": prior["predicted_silage_share"].round(4),
                        "corn_planted_year": prior["corn_planted_year"],
                        "k_acres_per_cow": prior["k_prev"].round(4), "k_from_year": prior["year"] - 1})
    return out.sort_values(["county_fips", "year"]).reset_index(drop=True)


def quebec_descriptive() -> dict | None:
    """Silage share of labelled Quebec maize parcels by half-degree latitude band (labels only, no Maryland).
    It shows that the regional variation the balance would have to explain exists in Quebec too."""
    if not QUEBEC_LABELS.exists():
        return None
    import geopandas as gpd

    labels = gpd.read_parquet(QUEBEC_LABELS)
    lat = labels.geometry.representative_point().y
    band = (np.floor(lat * 2) / 2).rename("band")
    silage = labels["label"].eq("silage")
    table = pd.DataFrame({"band": band, "silage": silage, "ha": labels["hectares"],
                          "silage_ha": labels["hectares"].where(silage, 0.0)})
    grouped = table.groupby("band").agg(parcels=("silage", "size"), silage_share=("silage", "mean"),
                                        ha=("ha", "sum"), silage_ha=("silage_ha", "sum"))
    grouped["silage_share_ha"] = grouped["silage_ha"] / grouped["ha"]
    return {f"{b:.1f}-{b + 0.5:.1f}N": {"parcels": int(r.parcels), "silage_share": round(float(r.silage_share), 3),
                                         "silage_share_by_ha": round(float(r.silage_share_ha), 3)}
            for b, r in grouped.iterrows()}


# --- output ----------------------------------------------------------------------------------------

def clean(value):
    """JSON-safe: numpy scalars to Python, floats rounded, NaN to None."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else round(float(value), 4)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def data_coverage(prior: pd.DataFrame) -> dict:
    survey_cows = read_county("cows", "SURVEY")
    survey_silage = read_county("silage", "SURVEY")
    planted = read_county("planted", "SURVEY")
    return {
        "annual_county_milk_cows": {"source": "NASS survey county estimates, 1 January",
                                    "states_per_year": survey_cows.groupby("year")["state"].nunique().to_dict()},
        "census_county_milk_cows": {"years": [2017, 2022], "states": int(read_county("cows", "CENSUS")["state"]
                                                                         .nunique())},
        "annual_county_silage_states": survey_silage.groupby("state")["year"].apply(
            lambda s: sorted(int(y) for y in s.unique())).to_dict(),
        "county_planted_years": sorted(int(y) for y in planted["year"].unique()),
        "county_planted_states": int(planted["state"].nunique()),
        "gaps": ["no county corn planted for 2021 in the local file (carried forward from 2020 where needed)",
                 "no 2016 county silage survey rows in the local file",
                 "no county cattle-on-feed; the note's 0.09 feedlot weight is not applied (milk cows only)",
                 "county milk cows before 2015 are not in the local files (no 2012 Census pair)"],
        "county_prior_rows": len(prior), "county_prior_years": sorted(int(y) for y in prior["year"].unique()),
    }


def maryland_note(prior: pd.DataFrame) -> dict:
    """The prior for Prince George's County (24033), where every BARC field sits. No labels are read."""
    rows = prior[(prior["county_fips"] == "24033") & prior["year"].between(2021, 2023)]
    return {"county_fips": "24033", "rows": rows[["year", "milk_cows", "corn_planted", "predicted_silage_share"]]
            .to_dict(orient="records"),
            "why_untestable": "all 34 BARC fields are in one county, so the county prior is one number per year "
                              "for every field: it cannot rank fields, and any score built on it is a constant"}


def verdict(cross: dict, changes: dict, state: dict) -> dict:
    """One line per level, derived from the scores (no number typed by hand)."""
    majors = cross["census_harvested"]["pooled_major_dairy_states"]
    works = sorted(s for s, v in cross["census_harvested"]["by_state"].items()
                   if v["skill_vs_naive_out"] is not None and v["r2_rule_out"] > 0.4)
    fails = sorted(s for s, v in cross["census_harvested"]["by_state"].items()
                   if v["skill_vs_naive_out"] is not None and v["skill_vs_naive_out"] < 0)
    beats = {k: [p for p in ["cow_scaled", "state_k"] if v["pooled_wape_pct"][p] < v["pooled_wape_pct"]["persistence"]]
             for k, v in changes.items()}
    primary = state["deltas"][0]
    return {
        "spatial_prior": (f"out-of-sample skill vs naive state share {majors['skill_vs_naive_out']:.2f} pooled over "
                          f"major dairy states; out-of-sample R^2 > 0.4 in {works}; worse than naive in {fails}"),
        "county_changes": ("balance beats persistence" if any(beats.values())
                           else "persistence beats both cow-based predictors in every scheme"),
        "state_forecast": ("adds value under the pre-registered rule" if state["primary_adds_value"] else
                           f"no detectable gain: {primary['candidate']} - {primary['reference']} = "
                           f"{primary['mean_delta_wape_points']:+.2f} points, 90% CI "
                           f"{primary['ci90_state_bootstrap'][0]:+.2f} to {primary['ci90_state_bootstrap'][1]:+.2f}; "
                           "do not add to the state model"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args()
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))   # lets the file run as a plain script from the repo root
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    table = load_state_table()
    cross, cross_summary = cross_section(table, rng)
    county_changes, yoy_summary = yoy(table)
    balance, predictions, yearly, state_summary = state_test(table, rng)
    prior = county_prior(table)

    cross.to_csv(OUT / "cross_section.csv", index=False, float_format="%.6g", lineterminator="\n")
    county_changes.to_csv(OUT / "county_yoy.csv", index=False, float_format="%.6g", lineterminator="\n")
    balance.to_csv(OUT / "state_balance.csv", index=False, float_format="%.6g", lineterminator="\n")
    predictions.to_csv(OUT / "state_predictions.csv", index=False, float_format="%.6g", lineterminator="\n")
    yearly.to_csv(OUT / "state_by_year.csv", index=False, float_format="%.4f", lineterminator="\n")
    prior.to_csv(OUT / "county_prior.csv", index=False, lineterminator="\n")

    results = {
        "group": "dairy_balance",
        "question": "Does the county dairy feed-demand balance (milk cows per corn acre x state silage acres per "
                    "cow) explain county silage share, county changes, or improve the state silage forecast?",
        "preregistration": PREREGISTERED,
        "data_coverage": data_coverage(prior),
        "test1_cross_section": cross_summary,
        "test2_county_year_over_year": yoy_summary,
        "test3_state": state_summary,
        "verdict": verdict(cross_summary, yoy_summary, state_summary),
        "maryland": maryland_note(prior),
        "quebec_silage_share_by_latitude": quebec_descriptive(),
        "uncomputed": {
            "maryland_field_test": "one county (Prince George's, 24033): the prior is constant across the farm",
            "quebec_field_test": "no Quebec dairy herd or corn area by region in the repo (needs Statistics Canada "
                                 "Census of Agriculture 2021 by census division plus division boundaries)",
            "cross_section_out_of_sample_2015": "no 2014 state milk cows in the panel, so no previous-year k",
        },
    }
    (OUT / "results.json").write_text(json.dumps(clean(results), indent=1) + "\n", encoding="utf-8")

    p = state_summary["deltas"][0]
    pooled = {k: cross_summary[k]["pooled_within_state"] for k in ["census_harvested", "survey_planted"]}
    print("WI 2022 reproduction:", clean(cross_summary["reproduction_wi_2022"]))
    for k, v in pooled.items():
        print(f"{k}: R2_in {v['r2_rule_in']:.3f} skill_in {v['skill_vs_naive_in']:.3f} placebo "
              f"{v['placebo_skill_vs_naive_in']:.3f} | R2_out {v['r2_rule_out']:.3f} skill_out "
              f"{v['skill_vs_naive_out']:.3f}")
    print("county YoY pooled WAPE:", {k: clean(v["pooled_wape_pct"]) for k, v in yoy_summary.items()})
    print("state mean WAPE:", {k: round(v["mean_state_wape_pct"], 2)
                               for k, v in state_summary["mean_by_candidate"].items()})
    print(f"primary {p['candidate']} - {p['reference']}: {p['mean_delta_wape_points']:+.2f} points, "
          f"90% CI {p['ci90_state_bootstrap'][0]:+.2f} to {p['ci90_state_bootstrap'][1]:+.2f}; "
          f"adds value: {state_summary['primary_adds_value']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
