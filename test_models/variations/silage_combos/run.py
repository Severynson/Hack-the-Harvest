"""Silage combinations of Tier A s3_fsa_residual (A-S3) and smoothed_chopping (SC), backtested 2012-2024.

The pre-registration (components, tiers, candidates, metrics, decision rule) is README.md section 1, hashed into
out/preregistration.sha256 before the first scored run. This module implements exactly that text.

Components are produced by importing the owners' code unchanged (no file of theirs is written; bytecode writing is
off): A-S3 and its persistence / reversion references from test_models/ownModels/silage/run.py, Tier B c5b from
test_models/ownModels/tierB/silage/run.py, SC and its variants from kernelag.silage_level.

Outputs (out/): backtest_by_state_year.csv, by_year.csv, summary.csv, comparisons.csv, decision.json,
forecast_2026.csv, forecast_2026_us.csv, interval_coverage.csv, params.csv, reproduction.json, run.json.

Run from the repository root:
    .venv/Scripts/python.exe -B test_models/variations/silage_combos/run.py
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True   # importing the other folders' modules must not leave __pycache__ behind

import argparse  # noqa: E402
import hashlib  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from kernelag import silage_level  # noqa: E402
from kernelag.context import drought as ctx_drought  # noqa: E402
from kernelag.state_model import add_intervals, error_quantiles, interval_coverage  # noqa: E402

OUT = HERE / "out"
DATA = REPO / "data"
QUICKSTATS = DATA / "Quickstats Data"
README = HERE / "README.md"
A_PATH = REPO / "test_models" / "ownModels" / "silage" / "run.py"
B_PATH = REPO / "test_models" / "ownModels" / "tierB" / "silage" / "run.py"
MONTHLY = REPO / "test_models" / "ownModels" / "monthly" / "out" / "monthly_by_state_year.csv"
A_FORECAST_2026 = REPO / "test_models" / "ownModels" / "silage" / "out" / "forecast_2026_all_candidates.csv"
B_FORECAST_2026 = REPO / "test_models" / "ownModels" / "tierB" / "silage" / "out" / "forecast_2026.csv"
STORED_BACKTEST = DATA / "models" / "state_model_backtest.csv"
STORED_FORECAST_2026 = DATA / "models" / "state_forecast_2026.csv"
NOISE_FLOOR_BY_YEAR = REPO / "test_models" / "accuracy" / "noise_floor" / "by_year.csv"
PREREG_START, PREREG_END = "## 1. Pre-registration", "<!-- END OF PRE-REGISTRATION -->"
PREREG2_START, PREREG2_END = "## 1b. Round-2 pre-registration", "<!-- END OF ROUND-2 PRE-REGISTRATION -->"
USDM_GLOB = "usdm_state_weekly_2000_2026.csv*"

ASOFS = ["sep", "oct", "nov"]
PRIMARY = "nov"
TEST_YEARS = list(range(2012, 2025))
FORECAST_YEAR = 2026
RUN_YEARS = list(range(2012, FORECAST_YEAR + 1))   # what the imported models are asked for; 2025 rows are dropped
PERIODS = {"2012-2024": (2012, 2024), "2017-2024": (2017, 2024)}
SELECTION_PERIOD = "2012-2024"
SEED = 20261114
N_BOOT_YEARS, N_BOOT_STATES = 10_000, 2_000
TAU_DROUGHT = silage_level.TAU      # SC's own constant (0.10), reused for the Drought Monitor exposure, not tuned
W_GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.05), 2)
MIN_FIT_YEARS, NULL_W = 3, 0.5
RULE_TOLERANCE = 0.10               # points
TIE = 0.005                         # points: headline tie on mean state WAPE
FLOAT_TOL = 1e-6                    # points: descriptive "beats both" label only (deviation D1)
SENSITIVITY_TAUS = [0.00, 0.05, 0.10, 0.20, 0.30]

# component key -> (tier, description)
COMPONENTS = {
    "A": ("A", "A-S3 s3_fsa_residual"),
    "B": ("B", "Tier B c5b_residual_fsa_planted_pre_june"),
    "SC": ("C", "smoothed_chopping (NASS yield and grain-acre forecasts)"),
    "SC_B": ("B", "SC with last year's final grain acres (NASS yield forecast only)"),
    "SC_L": ("A", "SC smoothed level only (history only)"),
    "SC_A": ("A", "SC with a Drought Monitor D2+ exposure"),
}
TIER_ORDER = {"A": 0, "B": 1, "C": 2}
# candidate -> (role, components used)
CANDIDATES = {
    "v1_geo": ("primary", ["A", "SC"]),
    "v2_topdown": ("primary", ["A", "SC"]),
    "v3_reverse": ("primary (control)", ["A", "SC"]),
    "v4_mean3": ("primary", ["A", "B", "SC"]),
    "v5_chopmult": ("primary", ["A", "SC"]),
    "v5b_chopadd": ("primary (variant of v5)", ["A", "SC"]),
    "v6_topdown_geoUS": ("primary", ["A", "SC"]),
    "v7_mean2": ("exploratory", ["A", "SC"]),
    "v8_geo_fitted": ("exploratory", ["A", "SC"]),
    "v9_topdown_SCB": ("exploratory", ["A", "SC_B"]),
    "v10_topdown_SCL": ("exploratory", ["A", "SC_L"]),
    "v11_topdown_SCA": ("exploratory", ["A", "SC_A"]),
    "v12_geo_SCA": ("exploratory", ["A", "SC_A"]),
    "v13_chopmult_SCA": ("exploratory", ["A", "SC_A"]),
    # round 2 (README section 1b, post hoc)
    "w1_mean2_SCA": ("round 2 (post hoc)", ["A", "SC_A"]),
    "w2_geo_fitted_SCA": ("round 2 (post hoc)", ["A", "SC_A"]),
    "w3_geo_SCA_rescaled": ("round 2 (post hoc)", ["A", "SC_A"]),
    "w4_geo_rescaled": ("round 2 (post hoc)", ["A", "SC"]),
    "w5_SC_A": ("round 2 (post hoc)", ["SC_A"]),
}
REFERENCES = {"A": "A", "B": "B", "SC": "C", "SC_B": "B", "SC_L": "A", "SC_A": "A",
              "s0_persistence": "benchmark", "s1_reversion_only": "A (history only)"}


def tier_of(name: str) -> str:
    if name in CANDIDATES:
        return max((COMPONENTS[c][0] for c in CANDIDATES[name][1]), key=TIER_ORDER.get)
    return REFERENCES[name]


def role_of(name: str) -> str:
    return CANDIDATES[name][0] if name in CANDIDATES else "reference"


# --- pre-registration -------------------------------------------------------------------------------------------

def preregistration_status() -> dict:
    text = README.read_text(encoding="utf-8")
    out = {}
    for key, (start, end, file) in {"round1": (PREREG_START, PREREG_END, "preregistration.sha256"),
                                    "round2": (PREREG2_START, PREREG2_END, "preregistration_round2.sha256")}.items():
        section = text[text.index(start):text.index(end) + len(end)]
        digest = hashlib.sha256(section.encode("utf-8")).hexdigest()
        stored = (OUT / file).read_text(encoding="utf-8").split()[0]
        out[key] = {"sha256_now": digest, "sha256_stored": stored, "unchanged": digest == stored}
    out["unchanged"] = all(v["unchanged"] for v in out.values())
    return out


# --- components ---------------------------------------------------------------------------------------------------

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def tier_a_and_b() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame]:
    """A-S3 (+ its persistence and reversion references) and c5b for every as-of date and year 2012-2026."""
    mod_a = load_module("silage_combos_tier_a", A_PATH)
    mod_b = load_module("silage_combos_tier_b", B_PATH)
    finals, states = mod_a.load_nass_finals()
    fsa = mod_a.load_fsa()
    raw = mod_a.load_season_inputs()
    rma = mod_a.rma_silage_acres(raw["insured"])
    data_b = mod_b.load_all()
    names_a = {"s3_fsa_residual": "A", "s0_persistence": "s0_persistence", "s1_reversion_only": "s1_reversion_only"}
    parts, last_parts = [], []
    for key in ASOFS:
        preds, _, _, rows = mod_a.run_asof(key, finals, states, fsa, raw, rma, RUN_YEARS)
        part = preds[preds["candidate"].isin(list(names_a))].copy()
        part["model"] = part["candidate"].map(names_a)
        parts.append(part.assign(asof=key)[["model", "asof", "year", "state", "pred"]])
        last_parts.append(rows[["state", "year", "S1"]].assign(asof=key))
        preds_b, _, _, _ = mod_b.run_asof(data_b, key, RUN_YEARS)
        part_b = preds_b[preds_b["candidate"] == "c5b_residual_fsa_planted_pre_june"].copy()
        parts.append(part_b.assign(model="B", asof=key)[["model", "asof", "year", "state", "pred"]])
    long = pd.concat(parts, ignore_index=True)
    long = long[long["year"].isin(TEST_YEARS + [FORECAST_YEAR])]
    last = pd.concat(last_parts, ignore_index=True).rename(columns={"S1": "last"})
    last = last.drop_duplicates(["state", "year", "last"])
    if last.duplicated(["state", "year"]).any():
        raise ValueError("last year's acres differ between as-of dates")
    last = last.drop(columns="asof")
    truth = finals[["state", "year", "silage"]].rename(columns={"silage": "actual"})
    truth = truth[truth["year"].isin(TEST_YEARS)]          # 2025 truth is never read into the scoring tables
    return long, last, truth, states, raw["usdm"]


def drought_exposure(history: dict, usdm: pd.DataFrame, asof: str, like: pd.DataFrame,
                     tau: float = TAU_DROUGHT) -> pd.DataFrame:
    """max(0, D2+ share - TAU) x last year's final grain acres, shaped like SC's own exposure table."""
    d = ctx_drought(usdm, asof).pivot(index="year", columns="state", values="drought")
    d = d.reindex(index=like.index, columns=like.columns).fillna(0.0)
    grain = history["grain"]
    years = range(int(min(grain.index.min(), like.index.min())), int(max(grain.index.max(), like.index.max())) + 1)
    grain_last = grain.reindex(years).shift(1).reindex(index=like.index, columns=like.columns).fillna(0.0)
    return (d - tau).clip(lower=0) * grain_last


def sc_variants(states: list[str], usdm: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """SC, SC_B, SC_L and SC_A for every as-of date and year 2012-2026 (2025 dropped), with chopped acres."""
    parts, params = [], []
    for asof in ASOFS:
        history = silage_level.load_history(QUICKSTATS, asof)
        exposure_sc = silage_level.chopping_exposure(history)
        no_grain_forecast = {**history, "grain_asof": history["grain_asof"].iloc[0:0]}
        exposures = {
            "SC": None,                                     # the module's own path, exactly as delivered
            "SC_B": silage_level.chopping_exposure(no_grain_forecast),
            "SC_L": exposure_sc * 0.0,
            "SC_A": drought_exposure(history, usdm, asof, exposure_sc),
        }
        for name, exposure in exposures.items():
            used = exposure_sc if exposure is None else exposure
            for year in TEST_YEARS + [FORECAST_YEAR]:
                pred, prm = silage_level.predict(history, year) if exposure is None \
                    else silage_level.predict(history, year, exposure=exposure)
                pred = pred.reindex(states)
                chopped = prm["gamma"] * used.reindex(index=[year], columns=states).iloc[0].fillna(0.0)
                parts.append(pd.DataFrame({"model": name, "asof": asof, "year": year, "state": states,
                                           "pred": pred.to_numpy(), "chopped": chopped.to_numpy()}))
                params.append({"model": name, "asof": asof, "year": year, **prm,
                               "chopped_acres_48": float(chopped.sum()),
                               "states_with_chopping": int((chopped > 0).sum())})
    return pd.concat(parts, ignore_index=True), params


# --- combinations -------------------------------------------------------------------------------------------------

def combine(w: pd.DataFrame, v8_weight: float, w2_weight: float = NULL_W) -> dict[str, pd.Series]:
    """Every candidate for one as-of date and year. ``w``: index state; columns A, B, SC, SC_B, SC_L, SC_A,
    SC_chop, SC_A_chop (chopped acres of SC and SC_A)."""
    a, sc = w["A"], w["SC"]

    def total(series: pd.Series) -> float:
        return float(series.sum())

    sc_base = sc - w["SC_chop"]
    sca_base = w["SC_A"] - w["SC_A_chop"]
    geo, geo_a = np.sqrt(a * sc), np.sqrt(a * w["SC_A"])
    return {
        "v1_geo": np.sqrt(a * sc),
        "v2_topdown": a * total(sc) / total(a),
        "v3_reverse": sc * total(a) / total(sc),
        "v4_mean3": (a + w["B"] + sc) / 3,
        "v5_chopmult": a * sc / sc_base,
        "v5b_chopadd": a + w["SC_chop"],
        "v6_topdown_geoUS": a * np.sqrt(total(sc) * total(a)) / total(a),
        "v7_mean2": (a + sc) / 2,
        "v8_geo_fitted": np.exp((1 - v8_weight) * np.log(a) + v8_weight * np.log(sc)),
        "v9_topdown_SCB": a * total(w["SC_B"]) / total(a),
        "v10_topdown_SCL": a * total(w["SC_L"]) / total(a),
        "v11_topdown_SCA": a * total(w["SC_A"]) / total(a),
        "v12_geo_SCA": np.sqrt(a * w["SC_A"]),
        "v13_chopmult_SCA": a * w["SC_A"] / sca_base,
        "w1_mean2_SCA": (a + w["SC_A"]) / 2,
        "w2_geo_fitted_SCA": np.exp((1 - w2_weight) * np.log(a) + w2_weight * np.log(w["SC_A"])),
        "w3_geo_SCA_rescaled": geo_a * total(w["SC_A"]) / total(geo_a),
        "w4_geo_rescaled": geo * total(sc) / total(geo),
        "w5_SC_A": w["SC_A"].copy(),
    }


def fit_geo_weight(train: pd.DataFrame, other: str = "SC") -> float:
    """The w in W_GRID minimizing sum abs(A^(1-w) other^w - actual) (smallest w on ties)."""
    log_a, log_sc = np.log(train["A"].to_numpy()), np.log(train[other].to_numpy())
    errors = [np.abs(np.exp((1 - w) * log_a + w * log_sc) - train["actual"].to_numpy()).sum() for w in W_GRID]
    return float(W_GRID[int(np.argmin(errors))])


def v8_weight(wide: pd.DataFrame, asof: str, year: int, other: str = "SC") -> tuple[float, int]:
    """Expanding-window weight for ``year`` from backtest years 2012 <= y < year (never 2025)."""
    train = wide[(wide["asof"] == asof) & (wide["year"] < year) & wide["year"].isin(TEST_YEARS)
                 & wide["actual"].notna()]
    n = int(train["year"].nunique())
    return (fit_geo_weight(train, other) if n >= MIN_FIT_YEARS else NULL_W), n


def build_predictions(components: pd.DataFrame, truth: pd.DataFrame, last: pd.DataFrame
                      ) -> tuple[pd.DataFrame, list[dict]]:
    """All references and candidates in one long table (model, asof, year, state, pred, actual, last)."""
    preds = components.pivot_table(index=["asof", "year", "state"], columns="model", values="pred")
    chop = components.pivot_table(index=["asof", "year", "state"], columns="model", values="chopped")
    wide = preds.join(chop[["SC", "SC_A"]].rename(columns={"SC": "SC_chop", "SC_A": "SC_A_chop"})).reset_index()
    wide = wide.merge(truth, on=["state", "year"], how="left").merge(last, on=["state", "year"], how="left")
    rows, params = [], []
    for (asof, year), w in wide.groupby(["asof", "year"]):
        w = w.set_index("state")
        if w[["A", "B", "SC", "SC_B", "SC_L", "SC_A", "SC_chop", "SC_A_chop"]].isna().any().any():
            raise ValueError(f"missing component prediction in {asof} {year}")
        weight, n_train = v8_weight(wide, asof, year)
        weight2, n_train2 = v8_weight(wide, asof, year, "SC_A")
        params.append({"model": "v8_geo_fitted", "asof": asof, "year": int(year), "w": weight,
                       "train_years": n_train})
        params.append({"model": "w2_geo_fitted_SCA", "asof": asof, "year": int(year), "w": weight2,
                       "train_years": n_train2})
        for name, series in combine(w, weight, weight2).items():
            rows.append(pd.DataFrame({"model": name, "asof": asof, "year": year, "state": series.index,
                                      "pred": series.to_numpy(dtype=float)}))
    candidates = pd.concat(rows, ignore_index=True)
    references = components[["model", "asof", "year", "state", "pred"]]
    out = pd.concat([references, candidates], ignore_index=True)
    out = out.merge(truth, on=["state", "year"], how="left").merge(last, on=["state", "year"], how="left")
    return out, params


# --- scoring ------------------------------------------------------------------------------------------------------

def scored_rows(preds: pd.DataFrame) -> pd.DataFrame:
    part = preds[preds["year"].isin(TEST_YEARS) & preds["actual"].notna() & preds["last"].notna()].copy()
    counts = part.groupby(["asof", "year", "model"]).size().unstack("model")
    if (counts.nunique(axis=1) != 1).any() or part["pred"].isna().any():
        raise ValueError("models are not scored on the same state-years")
    return part


def by_year_table(part: pd.DataFrame) -> pd.DataFrame:
    miss = part["pred"] - part["actual"]
    grouped = part.assign(miss=miss, abs_miss=miss.abs()).groupby(["model", "asof", "year"])
    table = grouped.agg(n_states=("state", "size"), actual=("actual", "sum"), miss=("miss", "sum"),
                        abs_miss=("abs_miss", "sum")).reset_index()
    table["state_wape_pct"] = 100 * table["abs_miss"] / table["actual"]
    table["us_error_pct"] = 100 * table["miss"] / table["actual"]
    table["abs_us_error_pct"] = table["us_error_pct"].abs()
    return table[["model", "asof", "year", "n_states", "state_wape_pct", "us_error_pct", "abs_us_error_pct"]]


def summary_table(by_year: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, asof), group in by_year.groupby(["model", "asof"]):
        for period, (lo, hi) in PERIODS.items():
            g = group[group["year"].between(lo, hi)]
            rows.append({"model": model, "role": role_of(model), "tier": tier_of(model), "asof": asof,
                         "period": period, "n_years": len(g), "mean_state_wape_pct": g["state_wape_pct"].mean(),
                         "mean_abs_us_error_pct": g["abs_us_error_pct"].mean(),
                         "mean_signed_us_error_pct": g["us_error_pct"].mean(),
                         "max_abs_us_error_pct": g["abs_us_error_pct"].max()})
    return pd.DataFrame(rows)


def matrices(part: pd.DataFrame, model: str, asof: str, years: list[int], states: list[str]):
    sub = part[(part["model"] == model) & (part["asof"] == asof)]
    pred = sub.pivot(index="year", columns="state", values="pred").reindex(index=years, columns=states)
    act = sub.pivot(index="year", columns="state", values="actual").reindex(index=years, columns=states)
    return pred.to_numpy(), act.to_numpy()


def per_year_metrics(pred: np.ndarray, act: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """State WAPE and |US| (percent) per year along the first axis; any trailing axes are kept."""
    total = np.nansum(act, axis=-1)
    wape = 100 * np.nansum(np.abs(pred - act), axis=-1) / total
    us = 100 * np.abs(np.nansum(pred - act, axis=-1)) / total
    return wape, us


def bootstrap_intervals(pc, ac, pr, ar) -> dict:
    """Paired 90% intervals of mean(metric(c) - metric(ref)) by resampling years, states, and both."""
    n_years, n_states = pc.shape
    wc, uc = per_year_metrics(pc, ac)
    wr, ur = per_year_metrics(pr, ar)
    out = {}
    rng = np.random.default_rng(SEED)
    year_draws = rng.integers(0, n_years, size=(N_BOOT_YEARS, n_years))
    for metric, d in (("state_wape", wc - wr), ("abs_us", uc - ur)):
        means = d[year_draws].mean(axis=1)
        out[f"{metric}_ci90_years"] = [float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95))]
    rng = np.random.default_rng(SEED)
    state_draws = rng.integers(0, n_states, size=(N_BOOT_STATES, n_states))
    joint_years = rng.integers(0, n_years, size=(N_BOOT_STATES, n_years))
    # (years, draws, states) after fancy indexing on the state axis
    wc_s, uc_s = per_year_metrics(pc[:, state_draws], ac[:, state_draws])
    wr_s, ur_s = per_year_metrics(pr[:, state_draws], ar[:, state_draws])
    for metric, d in (("state_wape", wc_s - wr_s), ("abs_us", uc_s - ur_s)):   # d: (years, draws)
        states_only = d.mean(axis=0)
        joint = np.take_along_axis(d.T, joint_years, axis=1).mean(axis=1)
        out[f"{metric}_ci90_states"] = [float(np.quantile(states_only, 0.05)), float(np.quantile(states_only, 0.95))]
        out[f"{metric}_ci90_joint"] = [float(np.quantile(joint, 0.05)), float(np.quantile(joint, 0.95))]
    return out


def comparisons(part: pd.DataFrame, states: list[str]) -> pd.DataFrame:
    rows = []
    names = list(CANDIDATES) + list(REFERENCES)
    for asof in ASOFS:
        for period, (lo, hi) in PERIODS.items():
            years = list(range(lo, hi + 1))
            refs = {r: matrices(part, r, asof, years, states) for r in ("A", "SC")}
            for name in names:
                pc, ac = matrices(part, name, asof, years, states)
                wc, uc = per_year_metrics(pc, ac)
                for ref, (pr, ar) in refs.items():
                    wr, ur = per_year_metrics(pr, ar)
                    row = {"model": name, "role": role_of(name), "tier": tier_of(name), "vs": ref, "asof": asof,
                           "period": period, "n_years": len(years)}
                    for metric, d in (("state_wape", wc - wr), ("abs_us", uc - ur)):
                        se = float(d.std(ddof=1) / np.sqrt(len(d)))
                        row.update({f"{metric}_mean_diff": float(d.mean()), f"{metric}_se": se,
                                    f"{metric}_mean_plus_2se": float(d.mean() + 2 * se),
                                    f"{metric}_years_better": int((d < -1e-9).sum()),
                                    f"{metric}_years_worse": int((d > 1e-9).sum())})
                    row.update(bootstrap_intervals(pc, ac, pr, ar))
                    rows.append(row)
    table = pd.DataFrame(rows)
    for column in [c for c in table.columns if "_ci90_" in c]:
        table[column] = table[column].map(lambda pair: f"[{pair[0]:+.3f}, {pair[1]:+.3f}]")
    return table


def decide(summary: pd.DataFrame, compared: pd.DataFrame, period: str = SELECTION_PERIOD,
           asof: str = PRIMARY) -> dict:
    """The pre-registered rule (README 1.4)."""
    s = summary[(summary["asof"] == asof) & (summary["period"] == period)].set_index("model")
    c = compared[(compared["asof"] == asof) & (compared["period"] == period)].set_index(["model", "vs"])
    table = {}
    for name in list(CANDIDATES) + list(REFERENCES):
        va, vsc = c.loc[(name, "A")], c.loc[(name, "SC")]
        r1_wape = float(s.loc[name, "mean_state_wape_pct"] - s.loc["A", "mean_state_wape_pct"])
        r1 = bool(r1_wape <= RULE_TOLERANCE and va["abs_us_mean_plus_2se"] < 0)
        r2_us = float(s.loc[name, "mean_abs_us_error_pct"] - s.loc["SC", "mean_abs_us_error_pct"])
        r2 = bool(vsc["state_wape_mean_plus_2se"] < 0 and r2_us <= RULE_TOLERANCE)
        table[name] = {
            "role": role_of(name), "tier": tier_of(name),
            "mean_state_wape": float(s.loc[name, "mean_state_wape_pct"]),
            "mean_abs_us": float(s.loc[name, "mean_abs_us_error_pct"]),
            "mean_signed_us": float(s.loc[name, "mean_signed_us_error_pct"]),
            "R1_wape_minus_A": r1_wape, "R1_abs_us_diff_vs_A_mean_plus_2se": float(va["abs_us_mean_plus_2se"]),
            "R1": r1,
            "R2_wape_diff_vs_SC_mean_plus_2se": float(vsc["state_wape_mean_plus_2se"]), "R2_abs_us_minus_SC": r2_us,
            "R2": r2, "recommended": r1 or r2,
            "beats_both_point_estimates": bool(
                s.loc[name, "mean_state_wape_pct"] <= s.loc["A", "mean_state_wape_pct"] + FLOAT_TOL
                and s.loc[name, "mean_abs_us_error_pct"] <= s.loc["SC", "mean_abs_us_error_pct"] + FLOAT_TOL),
            "beats_both_strict": bool(   # at least as good as the better of A and SC on each metric
                s.loc[name, "mean_state_wape_pct"] <= min(s.loc["A", "mean_state_wape_pct"],
                                                          s.loc["SC", "mean_state_wape_pct"]) + FLOAT_TOL
                and s.loc[name, "mean_abs_us_error_pct"] <= min(s.loc["A", "mean_abs_us_error_pct"],
                                                                s.loc["SC", "mean_abs_us_error_pct"]) + FLOAT_TOL),
        }

    def best(names: list[str]) -> str | None:
        if not names:
            return None
        low = min(table[n]["mean_state_wape"] for n in names)
        tied = [n for n in names if table[n]["mean_state_wape"] <= low + TIE]
        return min(tied, key=lambda n: table[n]["mean_abs_us"])

    recommended = [n for n in CANDIDATES if table[n]["recommended"]]
    primary = [n for n in recommended if table[n]["role"].startswith("primary")]
    round1_x = [n for n in recommended if table[n]["role"] == "exploratory"]
    round2 = [n for n in recommended if table[n]["role"].startswith("round 2")]
    tier_a = [n for n in recommended if table[n]["tier"] == "A" and n in round1_x + primary]
    return {"period": period, "asof": asof, "A_mean_state_wape": float(s.loc["A", "mean_state_wape_pct"]),
            "A_mean_abs_us": float(s.loc["A", "mean_abs_us_error_pct"]),
            "SC_mean_state_wape": float(s.loc["SC", "mean_state_wape_pct"]),
            "SC_mean_abs_us": float(s.loc["SC", "mean_abs_us_error_pct"]),
            "candidates": {n: table[n] for n in CANDIDATES},
            "references_information_only": {n: table[n] for n in REFERENCES},
            "recommended": recommended, "headline_primary": best(primary),
            "best_recommended_exploratory": best(round1_x), "best_recommended_tier_a_round1": best(tier_a),
            "best_recommended_round2_post_hoc": best(round2),
            "beats_both_strict": [n for n in CANDIDATES if table[n]["beats_both_strict"]]}


# --- 2026 forecasts -----------------------------------------------------------------------------------------------

def forecasts(preds: pd.DataFrame, part: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    states_rows, us_rows, coverage = [], [], []
    for (model, asof), now in preds[preds["year"] == FORECAST_YEAR].groupby(["model", "asof"]):
        held = part[(part["model"] == model) & (part["asof"] == asof)].rename(columns={"pred": "predicted"})
        now = now.set_index("state")
        bounds = add_intervals(now["pred"], now["last"], error_quantiles(held), "silage")
        table = pd.DataFrame({"silage": now["pred"], "silage_last_year": now["last"]}).join(bounds)
        states_rows.append(table.reset_index().assign(model=model, asof=asof))
        totals = held.groupby("year")[["actual", "predicted"]].sum()
        q10, q90 = np.quantile(np.log(totals["actual"] / totals["predicted"]), [0.10, 0.90])
        total = float(now["pred"].sum())
        us_rows.append({"model": model, "role": role_of(model), "tier": tier_of(model), "asof": asof,
                        "year": FORECAST_YEAR, "us_silage": total, "us_lo80": total * np.exp(q10),
                        "us_hi80": total * np.exp(q90), "us_last_year_48": float(now["last"].sum()),
                        "backtest_years": int(totals.shape[0])})
        coverage.append({"model": model, "asof": asof, **{f"loyo_coverage_{k}": v
                                                           for k, v in interval_coverage(held).items()}})
    columns = ["model", "asof", "state", "silage", "silage_lo80", "silage_hi80", "silage_lo90", "silage_hi90",
               "silage_last_year"]
    return pd.concat(states_rows, ignore_index=True)[columns], pd.DataFrame(us_rows), pd.DataFrame(coverage)


# --- reproduction checks ------------------------------------------------------------------------------------------

def reproduction(preds: pd.DataFrame, by_year: pd.DataFrame, components: pd.DataFrame) -> dict:
    out = {}
    monthly = pd.read_csv(MONTHLY)
    names = {"s3_fsa_residual": "A", "c5b_residual_fsa_planted_pre_june": "B", "s0_persistence": "s0_persistence",
             "reversion_only_H00": "s1_reversion_only"}
    monthly = monthly[monthly["model"].isin(list(names)) & monthly["asof"].isin(ASOFS)]
    monthly = monthly.assign(model=monthly["model"].map(names))
    merged = monthly.merge(preds, on=["model", "asof", "year", "state"], how="left", suffixes=("_monthly", ""))
    diff = (merged["pred"] - merged["pred_monthly"]).abs()
    out["tier_a_b_vs_monthly_harness"] = {
        m: {"rows": int((merged["model"] == m).sum()), "missing": int(merged.loc[merged["model"] == m, "pred"]
                                                                     .isna().sum()),
            "max_abs_diff_acres": float(diff[merged["model"] == m].max()),
            "truth_max_abs_diff": float((merged.loc[merged["model"] == m, "actual"]
                                         - merged.loc[merged["model"] == m, "actual_monthly"]).abs().max())}
        for m in names.values()}

    sc = by_year[(by_year["model"] == "SC") & (by_year["asof"] == PRIMARY)].set_index("year")
    stored = pd.read_csv(STORED_BACKTEST)
    stored = stored[(stored["scope"] == "all_states") & (stored["series"] == "silage")
                    & (stored["predictor"] == "smoothed_chopping")].set_index("year")
    noise = pd.read_csv(NOISE_FLOOR_BY_YEAR)
    noise = noise[noise["candidate"] == "smoothed_plus_chopping"].set_index("year")
    common_years = stored.index
    out["sc_nov"] = {
        "mean_wape_2012_2024": float(sc["state_wape_pct"].mean()), "documented_2012_2024": [13.23, 3.44],
        "mean_abs_us_2012_2024": float(sc["abs_us_error_pct"].mean()),
        "mean_wape_2017_2024": float(sc.loc[2017:2024, "state_wape_pct"].mean()),
        "mean_abs_us_2017_2024": float(sc.loc[2017:2024, "abs_us_error_pct"].mean()),
        "documented_2017_2024": [12.80, 3.34],
        "max_abs_diff_vs_stored_state_model_backtest_2017_2024": {
            "state_wape": float((sc.loc[common_years, "state_wape_pct"].round(2)
                                 - stored["state_error_pct"]).abs().max()),
            "us_error": float((sc.loc[common_years, "us_error_pct"].round(2)
                               - stored["total_error_pct"]).abs().max())},
        "max_abs_diff_vs_noise_floor_by_year_2012_2024": {
            "state_wape": float((sc["state_wape_pct"] - noise.loc[sc.index, "state_wape_pct"]).abs().max()),
            "abs_us": float((sc["abs_us_error_pct"] - noise.loc[sc.index, "us_abs_error_pct"]).abs().max())},
    }
    stored_2026 = pd.read_csv(STORED_FORECAST_2026)
    stored_2026 = stored_2026[~stored_2026["state"].str.startswith("US")].set_index("state")["silage"]
    mine = preds[(preds["model"] == "SC") & (preds["asof"] == PRIMARY) & (preds["year"] == FORECAST_YEAR)]
    mine = mine.set_index("state")["pred"].round(-2)
    common = mine.index.intersection(stored_2026.index)
    out["sc_2026_nov_vs_data_models_state_forecast_2026"] = {
        "states_compared": len(common), "max_abs_diff_acres_after_rounding": float(
            (mine[common] - stored_2026[common]).abs().max()),
        "sum_48_mine": float(mine.sum()), "sum_stored_states_shown": float(stored_2026.sum())}
    for key, path, column in [("A", A_FORECAST_2026, "s3_fsa_residual"), ("B", B_FORECAST_2026, "silage")]:
        table = pd.read_csv(path)
        folder = table[~table["state"].astype(str).str.startswith("US")].set_index("state")[column]
        mine = preds[(preds["model"] == key) & (preds["asof"] == PRIMARY) & (preds["year"] == FORECAST_YEAR)]
        mine = mine.set_index("state")["pred"].round(-2)
        common = mine.index.intersection(folder.index)
        out[f"{key}_2026_nov_vs_folder"] = {"column": column, "states_compared": len(common),
                                            "max_abs_diff_acres_after_rounding": float(
                                                (mine[common] - folder[common]).abs().max())}
    sc_rows = components[components["model"].isin(["SC", "SC_A", "SC_B", "SC_L"])]
    out["sc_variants_chopped_nonnegative"] = bool((sc_rows["chopped"] >= 0).all())
    out["sc_l_has_no_chopping"] = bool((components.loc[components["model"] == "SC_L", "chopped"] == 0).all())
    return out


def identity_check(components: pd.DataFrame) -> dict:
    """SC prediction = exp(smoothed normal level) + chopped, re-derived from silage_level's private helpers."""
    out = {}
    for asof in ASOFS:
        history = silage_level.load_history(QUICKSTATS, asof)
        exposure = silage_level.chopping_exposure(history)
        worst = 0.0
        for year in TEST_YEARS + [FORECAST_YEAR]:
            pred, prm = silage_level.predict(history, year)
            silage = history["silage"].loc[:year - 1]
            chopped_past = prm["gamma"] * exposure.reindex(index=silage.index, columns=silage.columns).fillna(0.0)
            normal = (silage - chopped_past).clip(lower=silage_level.FLOOR * silage)
            base = np.exp(silage_level._smoothed(np.log(normal), prm["alpha"])).loc[year]
            mine = components[(components["model"] == "SC") & (components["asof"] == asof)
                              & (components["year"] == year)].set_index("state")
            rebuilt = base.reindex(mine.index) + mine["chopped"]
            worst = max(worst, float((rebuilt - mine["pred"]).abs().max()))
        out[asof] = worst
    return {"sc_pred_minus_base_plus_chopped_max_abs_acres": out}


def tau_sensitivity(components: pd.DataFrame, truth: pd.DataFrame, states: list[str]) -> pd.DataFrame:
    """SC_A and v12_geo_SCA at 15 Nov with other drought thresholds (README 1b, information only)."""
    usdm = pd.read_csv(next((DATA / "drought").glob(USDM_GLOB)))
    history = silage_level.load_history(QUICKSTATS, PRIMARY)
    like = silage_level.chopping_exposure(history)
    tier_a = components[(components["model"] == "A") & (components["asof"] == PRIMARY)]
    a = tier_a.set_index(["year", "state"])["pred"]
    actual = truth.set_index(["year", "state"])["actual"]
    rows = []
    for tau in SENSITIVITY_TAUS:
        exposure = drought_exposure(history, usdm, PRIMARY, like, tau)
        for year in TEST_YEARS:
            pred, prm = silage_level.predict(history, year, exposure=exposure)
            sca = pred.reindex(states)
            act = actual.loc[year].reindex(states)
            a_y = a.loc[year].reindex(states)
            for name, p in (("SC_A", sca), ("v12_geo_SCA", np.sqrt(a_y * sca))):
                rows.append({"tau": tau, "model": name, "year": year, "gamma": prm["gamma"],
                             "state_wape_pct": 100 * (p - act).abs().sum() / act.sum(),
                             "us_error_pct": 100 * (p.sum() - act.sum()) / act.sum()})
    table = pd.DataFrame(rows)
    out = []
    for (tau, model), g in table.groupby(["tau", "model"]):
        for period, (lo, hi) in PERIODS.items():
            gg = g[g["year"].between(lo, hi)]
            out.append({"tau": tau, "model": model, "period": period,
                        "mean_state_wape_pct": gg["state_wape_pct"].mean(),
                        "mean_abs_us_error_pct": gg["us_error_pct"].abs().mean(),
                        "mean_signed_us_error_pct": gg["us_error_pct"].mean(),
                        "gamma_range": f"{gg['gamma'].min():.2f}-{gg['gamma'].max():.2f}"})
    return pd.DataFrame(out)


# --- main ---------------------------------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--components-cache", type=Path, help="pickle of the component table (scratch use only): "
                        "read if it exists, else written after computing")
    args = parser.parse_args()
    prereg = preregistration_status()
    if not prereg["unchanged"]:
        raise SystemExit("README section 1 differs from out/preregistration.sha256; refusing to score")

    if args.components_cache is not None and args.components_cache.exists():
        components, last, truth, states, sc_params = pd.read_pickle(args.components_cache)
    else:
        long_ab, last, truth, states, usdm = tier_a_and_b()
        sc, sc_params = sc_variants(states, usdm)
        components = pd.concat([long_ab.assign(chopped=0.0), sc], ignore_index=True)
        if args.components_cache is not None:
            pd.to_pickle((components, last, truth, states, sc_params), args.components_cache)
    preds, v8_params = build_predictions(components, truth, last)
    part = scored_rows(preds)
    by_year = by_year_table(part)
    summary = summary_table(by_year)
    compared = comparisons(part, states)
    decision = decide(summary, compared)
    info = {f"{asof}_{period}": decide(summary, compared, period, asof)
            for asof in ASOFS for period in PERIODS if (asof, period) != (PRIMARY, SELECTION_PERIOD)}
    fc_states, fc_us, coverage = forecasts(preds, part)
    checks = reproduction(preds, by_year, components) | identity_check(components)
    sensitivity = tau_sensitivity(components, truth, states)

    columns = ["model", "asof", "year", "state", "pred", "actual", "last"]
    preds.sort_values(["model", "asof", "year", "state"])[columns].to_csv(
        OUT / "backtest_by_state_year.csv", index=False, lineterminator="\n", float_format="%.1f")
    by_year.to_csv(OUT / "by_year.csv", index=False, lineterminator="\n", float_format="%.4f")
    summary.to_csv(OUT / "summary.csv", index=False, lineterminator="\n", float_format="%.4f")
    compared.to_csv(OUT / "comparisons.csv", index=False, lineterminator="\n", float_format="%.4f")
    pd.DataFrame(sc_params + v8_params).to_csv(OUT / "params.csv", index=False, lineterminator="\n",
                                               float_format="%.4f")
    fc_states.round({c: -2 for c in fc_states.columns if c.startswith("silage")}).to_csv(
        OUT / "forecast_2026.csv", index=False, lineterminator="\n", float_format="%.0f")
    fc_us.round({c: -2 for c in fc_us.columns if c.startswith("us_")}).to_csv(
        OUT / "forecast_2026_us.csv", index=False, lineterminator="\n", float_format="%.0f")
    coverage.to_csv(OUT / "interval_coverage.csv", index=False, lineterminator="\n", float_format="%.3f")
    sensitivity.to_csv(OUT / "sensitivity_drought_tau.csv", index=False, lineterminator="\n", float_format="%.4f")
    (OUT / "decision.json").write_text(json.dumps({"primary": decision, "information": info}, indent=1) + "\n",
                                       encoding="utf-8")
    (OUT / "reproduction.json").write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8")
    run_info = {"status": "done", "preregistration": prereg, "states": len(states),
                "test_years": TEST_YEARS, "forecast_year": FORECAST_YEAR, "asof_dates": ASOFS,
                "notes": ["2025 is never scored and enters no fit, interval or choice of this folder",
                          "imported component models fit on their own expanding windows (2026 uses 2025 finals)"]}
    (OUT / "run.json").write_text(json.dumps(run_info, indent=1) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    view = summary[summary["asof"] == PRIMARY].pivot(index="model", columns="period",
                                                    values=["mean_state_wape_pct", "mean_abs_us_error_pct"])
    print(view.round(2).to_string())
    print(json.dumps({k: decision[k] for k in ("recommended", "headline_primary", "best_recommended_exploratory",
                                                "best_recommended_tier_a_round1", "best_recommended_round2_post_hoc",
                                                "beats_both_strict")}, indent=1))
    print(sensitivity.round(2).to_string(index=False))
    print(json.dumps(checks, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
