"""Does the satellite silage-like share improve state silage acreage? (agent key: sat_eval)

Pre-registered in README.md section 1 (hashed into out/preregistration.sha256 before any score was computed).
Candidates have no fitted parameter: persistence, the three stored base models (report reversion_only, Tier A s3,
Tier B c5b), and each of them multiplied by this year's satellite share ratio r = sh(t) / sh(t-1) (clipped to
[0.5, 2]) at full or half strength. Selection years 2020-2024, 15 sampled states, 15 November; 2025 information.

Run from the repo root:
    .venv/Scripts/python.exe test_models/ownModels/satellite/eval/eval.py --prereg     # once, before scoring
    .venv/Scripts/python.exe test_models/ownModels/satellite/eval/eval.py              # backtest + 2026 forecast
    .venv/Scripts/python.exe test_models/ownModels/satellite/eval/eval.py --recompute-2026   # redo 2026 shares

Writes only test_models/ownModels/satellite/eval/out/. Never writes data/ (in particular never
data/panel/state_satellite.csv).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = HERE / "out"
README = HERE / "README.md"
PREREG_FILE = OUT / "preregistration.sha256"
PREREG_START = "## 1. Pre-registration"
PREREG_END = "<!-- END OF PRE-REGISTRATION -->"

DATA = ROOT / "data"
SAT = ROOT / "test_models" / "ownModels" / "satellite"
SIGNAL_PY = SAT / "signal" / "signal.py"
SIGNAL_OUT = SAT / "signal" / "out"
CORN26_OUT = SAT / "corn26" / "out"
TIER_A = ROOT / "test_models" / "ownModels" / "silage" / "out"
TIER_B = ROOT / "test_models" / "ownModels" / "tierB" / "silage" / "out"

SEL_YEARS = [2020, 2021, 2022, 2023, 2024]
INFO_YEAR = 2025
FORECAST_YEAR = 2026
ASOFS = ("nov", "oct", "sep")
SEED = 20261115
N_BOOT = 10_000
Z80 = 1.2815515655446004  # standard normal 90th percentile
CLIP = (0.5, 2.0)
ASOF_CUTOFF_2026 = "2026-11-15"

BASE_NAMES = {"R": "reversion_only (report; s1_incumbent_H13)", "A": "Tier A s3_fsa_residual",
              "B": "Tier B c5b_residual_fsa_planted_pre_june", "p0": "persistence S(t-1)"}
TIER_A_KEY = "s3_fsa_residual"
TIER_A_R_KEY = "s1_incumbent_H13"
TIER_B_KEY = "c5b_residual_fsa_planted_pre_june"

# name -> base candidate, exponent on r ("snr" = 0.5 x SNR / (1 + SNR)), share column, family
CANDIDATES: dict[str, dict] = {
    "p0": dict(base=None, k=0.0, share=None, family="base"),
    "R": dict(base=None, k=0.0, share=None, family="base"),
    "A": dict(base=None, k=0.0, share=None, family="base"),
    "B": dict(base=None, k=0.0, share=None, family="base"),
    "p1": dict(base="p0", k=1.0, share="sat_share", family="primary"),
    "p2": dict(base="p0", k=0.5, share="sat_share", family="primary"),
    "R2": dict(base="R", k=0.5, share="sat_share", family="primary"),
    "A2": dict(base="A", k=0.5, share="sat_share", family="primary"),
    "B2": dict(base="B", k=0.5, share="sat_share", family="primary"),
    "p1c": dict(base="p0", k=1.0, share="sat_share_calls", family="info_calls"),
    "p2c": dict(base="p0", k=0.5, share="sat_share_calls", family="info_calls"),
    "R2c": dict(base="R", k=0.5, share="sat_share_calls", family="info_calls"),
    "A2c": dict(base="A", k=0.5, share="sat_share_calls", family="info_calls"),
    "B2c": dict(base="B", k=0.5, share="sat_share_calls", family="info_calls"),
    "p2w": dict(base="p0", k="snr", share="sat_share", family="info_snr"),
    "R2w": dict(base="R", k="snr", share="sat_share", family="info_snr"),
    "A2w": dict(base="A", k="snr", share="sat_share", family="info_snr"),
    "B2w": dict(base="B", k="snr", share="sat_share", family="info_snr"),
}
PRIMARY_SAT = [c for c, spec in CANDIDATES.items() if spec["family"] == "primary"]
TIE_ORDER = ["A2", "B2", "R2", "p2", "p1"]
FALLBACK = "A"


# ----------------------------------------------------------------------------------------- pre-registration


def prereg_text(readme: Path = README) -> str:
    """README section 1, from its heading to the end marker, with LF line endings."""
    text = readme.read_text(encoding="utf-8").replace("\r\n", "\n")
    start = text.index(PREREG_START)
    end = text.index(PREREG_END) + len(PREREG_END)
    return text[start:end]


def prereg_hash(readme: Path = README) -> str:
    return hashlib.sha256(prereg_text(readme).encode("utf-8")).hexdigest()


def write_prereg() -> str:
    digest = prereg_hash()
    OUT.mkdir(parents=True, exist_ok=True)
    if PREREG_FILE.exists():
        stored = PREREG_FILE.read_text(encoding="utf-8").split()[0]
        if stored != digest:
            raise SystemExit("preregistration.sha256 exists with a different hash; refusing to overwrite")
        return digest
    PREREG_FILE.write_text(f"{digest}  README.md section 1 (Pre-registration)\n", encoding="utf-8")
    return digest


def check_prereg() -> str:
    if not PREREG_FILE.exists():
        raise SystemExit("no out/preregistration.sha256: run eval.py --prereg before scoring")
    stored = PREREG_FILE.read_text(encoding="utf-8").split()[0]
    digest = prereg_hash()
    if stored != digest:
        raise SystemExit("README section 1 changed after pre-registration; refusing to score")
    return digest


# ----------------------------------------------------------------------------------------------- inputs


def load_states() -> pd.DataFrame:
    summary = pd.read_csv(DATA / "samples" / "sample_summary.csv", dtype={"state_fips": str})
    summary["state_fips"] = summary["state_fips"].str.zfill(2)
    return summary[["state", "state_fips"]].reset_index(drop=True)


def load_truth() -> pd.Series:
    """NASS final silage acres by (state, year): the incumbent's truth file."""
    nass = pd.read_csv(DATA / "nass" / "corn_acres_state.csv", dtype={"state_ansi": str})
    final = nass[(nass["series"] == "silage") & (nass["period"] == "final")]
    if final.duplicated(["state", "year"]).any():
        raise ValueError("duplicate NASS silage finals")
    return final.set_index(["state", "year"])["acres"].astype(float)


def load_shares(asof: str) -> pd.DataFrame:
    shares = pd.read_csv(SIGNAL_OUT / f"state_satellite_asof_{asof}.csv", dtype={"state_fips": str})
    if (shares["asof"] != asof).any():
        raise ValueError(f"share file for {asof} carries another as-of key")
    if (pd.to_datetime(shares["last_observation_date"]) > pd.to_datetime(shares["asof_date"])).any():
        raise ValueError("a share uses a look after its as-of date")
    return shares[["state", "year", "sat_share", "sat_share_calls"]]


def load_snr() -> pd.Series:
    diag = pd.read_csv(SIGNAL_OUT / "diagnostics_by_state_asof_nov.csv")
    return diag.set_index("state")["expected_snr"].astype(float)


def _tier_b_backtest() -> pd.DataFrame:
    raw = pd.read_csv(TIER_B / "backtest_by_state_year.csv")
    dedup = raw.drop_duplicates()
    keys = ["state", "year", "asof_key", "candidate"]
    if dedup.duplicated(keys).any():
        raise ValueError("Tier B backtest has conflicting duplicate rows")
    return dedup


def load_bases(states: list[str]) -> pd.DataFrame:
    """Long table state, year, asof, candidate (R, A, B), pred: backtest 2020-2024 (3 dates), 2025, 2026 (Nov)."""
    a = pd.read_csv(TIER_A / "backtest_by_state_year.csv")
    b = _tier_b_backtest()
    parts = []
    for frame, key, name in [(a, TIER_A_R_KEY, "R"), (a, TIER_A_KEY, "A"), (b, TIER_B_KEY, "B")]:
        rows = frame[(frame["candidate"] == key) & frame["year"].isin(SEL_YEARS) & frame["state"].isin(states)]
        rows = rows.drop(columns="asof").rename(columns={"asof_key": "asof"})
        rows = rows[["state", "year", "asof", "pred"]].assign(candidate=name)
        parts.append(rows)
    score_files = {"R": (DATA / "models" / "state_score_2025.csv", "silage"),
                   "A": (TIER_A / "score_2025_information_only.csv", "pred"),
                   "B": (TIER_B / "score_2025_information_only.csv", "pred")}
    for name, (path, column) in score_files.items():
        rows = pd.read_csv(path)
        rows = rows[rows["state"].isin(states)]
        parts.append(pd.DataFrame({"state": rows["state"], "year": INFO_YEAR, "asof": "nov",
                                   "pred": rows[column].astype(float), "candidate": name}))
    forecast_files = {"R": DATA / "models" / "state_forecast_2026.csv", "A": TIER_A / "forecast_2026.csv",
                      "B": TIER_B / "forecast_2026.csv"}
    for name, path in forecast_files.items():
        rows = pd.read_csv(path)
        rows = rows[rows["state"].isin(states)]
        parts.append(pd.DataFrame({"state": rows["state"], "year": FORECAST_YEAR, "asof": "nov",
                                   "pred": rows["silage"].astype(float), "candidate": name}))
    bases = pd.concat(parts, ignore_index=True)
    if bases.duplicated(["state", "year", "asof", "candidate"]).any():
        raise ValueError("duplicate base predictions")
    expected = len(states) * (len(SEL_YEARS) * len(ASOFS) + 2) * 3
    if len(bases) != expected:
        raise ValueError(f"base predictions incomplete: {len(bases)} rows, expected {expected}")
    return bases


def load_tier_a_other(states: list[str]) -> pd.DataFrame:
    """Tier A s3 for the states outside the sample: state, year, asof, pred, actual (backtest, 2025, 2026)."""
    a = pd.read_csv(TIER_A / "backtest_by_state_year.csv")
    rows = a[(a["candidate"] == TIER_A_KEY) & a["year"].isin(SEL_YEARS)]
    rows = rows.drop(columns="asof").rename(columns={"asof_key": "asof"})
    parts = [rows[["state", "year", "asof", "pred", "actual"]]]
    s25 = pd.read_csv(TIER_A / "score_2025_information_only.csv")
    parts.append(pd.DataFrame({"state": s25["state"], "year": INFO_YEAR, "asof": "nov", "pred": s25["pred"],
                               "actual": s25["actual"]}))
    other = pd.concat(parts, ignore_index=True)
    return other[~other["state"].isin(states)].reset_index(drop=True)


def mask_error(column: str = "sat_share") -> tuple[float, pd.Series]:
    """M = RMS over states of m_s = log(share_pred_hist / share_true_all), Nov, 2025 replay; and m_s."""
    replay = pd.read_csv(CORN26_OUT / "mask_error_2025.csv", dtype={"state_fips": str})
    replay = replay[replay["asof"] == "nov"].set_index("state")
    if column == "sat_share":
        pred, true = replay["sat_share_pred_hist"], replay["sat_share_true_all"]
    else:
        pred, true = replay["sat_share_calls_pred_hist"], replay["sat_share_calls_true_all"]
    m = np.log(pred / true)
    return float(np.sqrt((m ** 2).mean())), m


def omission_rms() -> pd.Series:
    """O_s = RMS over 2019-2024 of log(ratio_det_to_true) per state (cross-year missed-corn replay)."""
    rep = pd.read_csv(CORN26_OUT / "cross_year_omission_replay.csv", dtype={"state_fips": str})
    rep = rep[rep["year"].between(2019, 2024)]
    return rep.groupby("state")["ratio_det_to_true"].apply(lambda r: float(np.sqrt((np.log(r) ** 2).mean())))


def pred_hist_2025() -> pd.DataFrame:
    replay = pd.read_csv(CORN26_OUT / "mask_error_2025.csv", dtype={"state_fips": str})
    replay = replay[replay["asof"] == "nov"]
    return replay[["state", "sat_share_pred_hist", "sat_share_calls_pred_hist"]].rename(
        columns={"sat_share_pred_hist": "sat_share", "sat_share_calls_pred_hist": "sat_share_calls"})


# ------------------------------------------------------------------------------------------- candidates


def clip_ratio(num, den):
    return np.clip(np.asarray(num, dtype=float) / np.asarray(den, dtype=float), *CLIP)


def ratios(shares: pd.DataFrame, years) -> pd.DataFrame:
    """r(t) = clip(sh(t) / sh(t-1)) and rc(t) for the given target years: state, year, sat_share, sat_share_calls."""
    wide = shares.set_index(["state", "year"])
    rows = []
    for (state, year), _ in wide.iterrows():
        if year not in years or (state, year - 1) not in wide.index:
            continue
        cur, prev = wide.loc[(state, year)], wide.loc[(state, year - 1)]
        rows.append({"state": state, "year": year,
                     "sat_share": float(clip_ratio(cur["sat_share"], prev["sat_share"])),
                     "sat_share_calls": float(clip_ratio(cur["sat_share_calls"], prev["sat_share_calls"]))})
    return pd.DataFrame(rows)


def exponent(spec, state: str, snr: pd.Series) -> float:
    k = spec["k"]
    if k == "snr":
        value = float(snr[state])
        return 0.5 * value / (1.0 + value)
    return float(k)


def build_predictions(bases: pd.DataFrame, last: pd.Series, r: pd.DataFrame, snr: pd.Series,
                      years, asof: str, candidates=CANDIDATES) -> pd.DataFrame:
    """Every candidate for every state and year in ``years`` at ``asof``.

    bases: long R/A/B table; last: S(t-1) by (state, year=t); r: ratios by state, year.
    """
    base_wide = bases[bases["asof"] == asof].pivot_table(index=["state", "year"], columns="candidate",
                                                          values="pred", aggfunc="first")
    r_index = r.set_index(["state", "year"])
    rows = []
    for (state, year) in r_index.index:
        if year not in years:
            continue
        base_values = {"p0": float(last[(state, year)])}
        for name in ("R", "A", "B"):
            base_values[name] = float(base_wide.loc[(state, year), name])
        for name, spec in candidates.items():
            if spec["base"] is None:
                pred, k, ratio, base_pred = base_values[name], 0.0, np.nan, base_values[name]
            else:
                k = exponent(spec, state, snr)
                ratio = float(r_index.loc[(state, year), spec["share"]])
                base_pred = base_values[spec["base"]]
                pred = base_pred * ratio ** k
            rows.append({"state": state, "year": int(year), "asof": asof, "candidate": name,
                         "family": spec["family"], "base": spec["base"] or "", "k": k, "r": ratio,
                         "base_pred": base_pred, "pred": pred, "last": base_values["p0"]})
    return pd.DataFrame(rows)


def attach_truth(bt: pd.DataFrame, truth: pd.Series) -> pd.DataFrame:
    bt = bt.copy()
    bt["actual"] = [truth.get((s, y), np.nan) for s, y in zip(bt["state"], bt["year"])]
    bt["err"] = bt["pred"] - bt["actual"]
    bt["abs_err"] = bt["err"].abs()
    bt["log_err"] = np.log(bt["actual"] / bt["pred"])
    return bt


# ---------------------------------------------------------------------------------------------- metrics


def wape(pred, actual) -> float:
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    return float(100.0 * np.abs(pred - actual).sum() / actual.sum())


def total_error(pred, actual) -> float:
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    return float(100.0 * (pred.sum() - actual.sum()) / actual.sum())


def by_year(bt: pd.DataFrame, other: pd.DataFrame | None = None, truth48: pd.Series | None = None) -> pd.DataFrame:
    """Per candidate, as-of and year: state WAPE, total error over the sample states, US48 error (information)."""
    rows = []
    for (cand, asof, year), g in bt.groupby(["candidate", "asof", "year"]):
        row = {"candidate": cand, "asof": asof, "year": int(year), "states": len(g),
               "wape": wape(g["pred"], g["actual"]), "tot": total_error(g["pred"], g["actual"])}
        row["abs_tot"] = abs(row["tot"])
        if other is not None:
            rest = other[(other["year"] == year) & (other["asof"] == asof)]
            if len(rest):
                us_pred = g["pred"].sum() + rest["pred"].sum()
                us_true = g["actual"].sum() + rest["actual"].sum()
                row["us48"] = 100.0 * (us_pred - us_true) / us_true
                row["us48_states"] = len(g) + len(rest)
        rows.append(row)
    out = pd.DataFrame(rows)
    if "us48" in out:
        out["abs_us48"] = out["us48"].abs()
    return out


def matrices(bt: pd.DataFrame, cand: str, asof: str, years) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """pred and actual as (states x years) arrays for one candidate."""
    g = bt[(bt["candidate"] == cand) & (bt["asof"] == asof) & bt["year"].isin(years)]
    pred = g.pivot(index="state", columns="year", values="pred").sort_index()[list(years)]
    actual = g.pivot(index="state", columns="year", values="actual").sort_index()[list(years)]
    if pred.isna().any().any() or actual.isna().any().any():
        raise ValueError(f"missing predictions for {cand} at {asof}")
    return pred.to_numpy(), actual.to_numpy(), list(pred.index)


def wape_by_year(pred: np.ndarray, actual: np.ndarray) -> np.ndarray:
    return 100.0 * np.abs(pred - actual).sum(axis=0) / actual.sum(axis=0)


def abs_tot_by_year(pred: np.ndarray, actual: np.ndarray) -> np.ndarray:
    return 100.0 * np.abs(pred.sum(axis=0) - actual.sum(axis=0)) / actual.sum(axis=0)


def boot_years(d: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    return float(np.percentile(means, 5)), float(np.percentile(means, 95))


def boot_states(pc: np.ndarray, pb: np.ndarray, actual: np.ndarray, metric, n_boot: int = N_BOOT,
                seed: int = SEED) -> tuple[float, float]:
    """Resample states (rows) with replacement; metric(pred[idx], actual[idx]) per year; mean difference."""
    rng = np.random.default_rng(seed)
    n = pc.shape[0]
    idx = rng.integers(0, n, size=(n_boot, n))
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        rows = idx[i]
        diffs[i] = (metric(pc[rows], actual[rows]) - metric(pb[rows], actual[rows])).mean()
    return float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95))


def paired(bt: pd.DataFrame, cand: str, base: str, asof: str, years=SEL_YEARS, n_boot: int = N_BOOT) -> dict:
    pc, actual, states = matrices(bt, cand, asof, years)
    pb, actual_b, states_b = matrices(bt, base, asof, years)
    if states != states_b or not np.allclose(actual, actual_b):
        raise ValueError("candidate and base cover different state-years")
    wc, wb = wape_by_year(pc, actual), wape_by_year(pb, actual)
    d = wc - wb
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    tc, tb = abs_tot_by_year(pc, actual), abs_tot_by_year(pb, actual)
    dt = tc - tb
    err_c = np.abs(pc - actual).sum(axis=1)
    err_b = np.abs(pb - actual).sum(axis=1)
    tol = 1e-6
    row = {
        "candidate": cand, "base": base, "asof": asof, "years": f"{years[0]}-{years[-1]}",
        "mean_wape": float(wc.mean()), "mean_wape_base": float(wb.mean()),
        "d_wape": float(d.mean()), "se_d_wape": se, "d_wape_plus_2se": float(d.mean() + 2 * se),
    }
    row["d_wape_ci90_years_lo"], row["d_wape_ci90_years_hi"] = boot_years(d, n_boot)
    row["d_wape_ci90_states_lo"], row["d_wape_ci90_states_hi"] = boot_states(pc, pb, actual, wape_by_year, n_boot)
    row.update({
        "years_better": int((d < -tol).sum()), "years_worse": int((d > tol).sum()),
        "years_tied": int((np.abs(d) <= tol).sum()),
        "states_better": int((err_c < err_b - tol).sum()), "states_worse": int((err_c > err_b + tol).sum()),
        "states_tied": int((np.abs(err_c - err_b) <= tol).sum()),
        "mean_abs_tot": float(tc.mean()), "mean_abs_tot_base": float(tb.mean()), "d_abs_tot": float(dt.mean()),
        "se_d_abs_tot": float(dt.std(ddof=1) / np.sqrt(len(dt))),
    })
    row["d_abs_tot_ci90_years_lo"], row["d_abs_tot_ci90_years_hi"] = boot_years(dt, n_boot)
    row["d_abs_tot_ci90_states_lo"], row["d_abs_tot_ci90_states_hi"] = boot_states(
        pc, pb, actual, abs_tot_by_year, n_boot)
    row["states_better_list"] = ";".join(s for s, c, b in zip(states, err_c, err_b) if c < b - tol)
    return row


def adoption(row: dict) -> tuple[bool, str]:
    lower = row["mean_wape"] < row["mean_wape_base"]
    two_se = row["d_wape_plus_2se"] < 0
    if lower and two_se:
        return True, "adopted"
    return False, "not shown"


def choose_final(adopted: dict[str, float]) -> str:
    """Rule 1.4.3: adopted candidate with the lowest mean WAPE (ties in TIE_ORDER); else the fallback A."""
    if not adopted:
        return FALLBACK
    best = min(adopted.values())
    for name in TIE_ORDER:
        if name in adopted and np.isclose(adopted[name], best):
            return name
    raise AssertionError("unreachable")


def best_satellite(summary_nov: dict[str, float]) -> str:
    best = min(summary_nov[c] for c in PRIMARY_SAT)
    for name in TIE_ORDER:
        if np.isclose(summary_nov[name], best):
            return name
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------------------- 2026 shares


def load_signal_module():
    spec = importlib.util.spec_from_file_location("satellite_signal", SIGNAL_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _share_2026_state(fips: str, corn_ids: list[str], model) -> pd.DataFrame:
    import geopandas as gpd

    from kernelag.field_model import load_series

    sig = load_signal_module()
    series_dir = DATA / "s2_series" / f"corn26_{fips}"
    rows = gpd.read_parquet(DATA / "samples" / f"corn26_{fips}.parquet")
    rows = rows[rows["field_id"].astype(str).isin(set(corn_ids)) & (rows["year"] == FORECAST_YEAR)]
    rows = sig.complete_sample(rows, series_dir)
    table = sig.state_shares(rows, load_series(series_dir), model, "nov")
    table["called_corn_fields"] = len(set(corn_ids))
    table["sample_fields_used"] = len(rows)
    return table


def compute_shares_2026(workers: int = 15) -> pd.DataFrame:
    sig = load_signal_module()
    model, _ = sig.fit_allqc_model()
    calls = pd.read_csv(CORN26_OUT / "corn26_calls.csv", dtype={"field_id": str, "state_fips": str, "cell": str})
    calls = calls[(calls["is_corn"] == 1) & (calls["year"] == FORECAST_YEAR)]
    jobs = {fips: g["field_id"].tolist() for fips, g in calls.groupby("state_fips")}
    tables = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {fips: pool.submit(_share_2026_state, fips, ids, model) for fips, ids in jobs.items()}
        for fips, future in futures.items():
            tables.append(future.result())
            print(f"2026 share done for {fips}", flush=True)
    table = pd.concat(tables, ignore_index=True)
    if (table["year"] != FORECAST_YEAR).any():
        raise ValueError("2026 share table has other years")
    if (pd.to_datetime(table["last_observation_date"]) > pd.Timestamp(ASOF_CUTOFF_2026)).any():
        raise ValueError("a 2026 share uses a look after 15 Nov 2026")
    if len(table) != len(jobs):
        raise ValueError("a state produced no 2026 share")
    return table.sort_values("state").reset_index(drop=True)


# -------------------------------------------------------------------------------------------- intervals


def log_error_quantiles(bt: pd.DataFrame, cand: str, years=SEL_YEARS, asof: str = "nov") -> tuple[float, ...]:
    e = bt[(bt["candidate"] == cand) & (bt["asof"] == asof) & bt["year"].isin(years)]["log_err"].to_numpy()
    return tuple(float(np.percentile(e, q)) for q in (10, 50, 90))


def widened(pred: float, q: tuple[float, float, float], w: float) -> tuple[float, float]:
    q10, q50, q90 = q
    lo = pred * np.exp(q50 - np.sqrt((q50 - q10) ** 2 + w ** 2))
    hi = pred * np.exp(q50 + np.sqrt((q90 - q50) ** 2 + w ** 2))
    return float(lo), float(hi)


def loyo_coverage(bt: pd.DataFrame, cand: str, years=SEL_YEARS, asof: str = "nov") -> float:
    g = bt[(bt["candidate"] == cand) & (bt["asof"] == asof) & bt["year"].isin(years)]
    inside = []
    for year in years:
        train = g[g["year"] != year]["log_err"].to_numpy()
        lo, hi = np.percentile(train, 10), np.percentile(train, 90)
        test = g[g["year"] == year]["log_err"].to_numpy()
        inside.extend(((test >= lo) & (test <= hi)).tolist())
    return float(np.mean(inside))


# ------------------------------------------------------------------------------------------------- run


def r4(x):
    return round(float(x), 4) if pd.notna(x) else np.nan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prereg", action="store_true", help="hash README section 1 and stop")
    parser.add_argument("--recompute-2026", action="store_true", help="recompute the 2026 shares")
    parser.add_argument("--workers", type=int, default=15)
    args = parser.parse_args()
    if args.prereg:
        print("pre-registration sha256:", write_prereg())
        return
    digest = check_prereg()
    OUT.mkdir(parents=True, exist_ok=True)

    states_df = load_states()
    states = states_df["state"].tolist()
    truth = load_truth()
    last = pd.Series({(s, y): truth[(s, y - 1)] for s in states for y in SEL_YEARS + [INFO_YEAR, FORECAST_YEAR]})
    bases = load_bases(states)
    snr = load_snr()
    other = load_tier_a_other(states)

    # checks: base files agree with NASS truth where they carry it
    a = pd.read_csv(TIER_A / "backtest_by_state_year.csv")
    a = a[a["state"].isin(states) & a["year"].isin(SEL_YEARS)]
    if not np.allclose(a["actual"], [truth[(s, y)] for s, y in zip(a["state"], a["year"])]):
        raise ValueError("Tier A actual differs from NASS truth")
    if not np.allclose(a["last"], [truth[(s, y - 1)] for s, y in zip(a["state"], a["year"])]):
        raise ValueError("Tier A last differs from NASS S(t-1)")

    # ---------------- backtest (2020-2024, three dates) and 2025 (Nov), CDL-mask shares
    frames = []
    for asof in ASOFS:
        shares = load_shares(asof)
        years = SEL_YEARS + ([INFO_YEAR] if asof == "nov" else [])
        r = ratios(shares, years)
        frames.append(build_predictions(bases, last, r, snr, years, asof))
    bt = attach_truth(pd.concat(frames, ignore_index=True), truth)
    bt["period"] = np.where(bt["year"] == INFO_YEAR, "2025_info", "selection")

    # 2025 real-time replay: classifier-mask share in 2025 over CDL share in 2024
    shares_nov = load_shares("nov")
    sh24 = shares_nov[shares_nov["year"] == 2024].set_index("state")
    ph = pred_hist_2025().set_index("state")
    r_mask = pd.DataFrame({"state": states, "year": INFO_YEAR,
                           "sat_share": [float(clip_ratio(ph.loc[s, "sat_share"], sh24.loc[s, "sat_share"]))
                                         for s in states],
                           "sat_share_calls": [float(clip_ratio(ph.loc[s, "sat_share_calls"],
                                                                sh24.loc[s, "sat_share_calls"])) for s in states]})
    replay_cands = {f"{c}_mask25": dict(CANDIDATES[c], family="info_mask_replay_2025")
                    for c in PRIMARY_SAT + ["p1c", "p2c", "R2c", "A2c", "B2c"]}
    replay = build_predictions(bases, last, r_mask, snr, [INFO_YEAR], "nov", replay_cands)
    replay = attach_truth(replay, truth)
    replay["period"] = "2025_info_mask_replay"
    bt_all = pd.concat([bt, replay], ignore_index=True)

    yearly = by_year(bt_all, other)
    yearly.to_csv(OUT / "by_year.csv", index=False, float_format="%.4f")
    bt_out = bt_all.copy()
    bt_out.to_csv(OUT / "backtest.csv", index=False, float_format="%.4f")

    # ---------------- summary
    summ = []
    families = {**{c: s["family"] for c, s in CANDIDATES.items()}, **{c: s["family"] for c, s in replay_cands.items()}}
    bases_of = {**{c: (s["base"] or "") for c, s in CANDIDATES.items()},
                **{c: (s["base"] or "") for c, s in replay_cands.items()}}
    for (cand, asof), g in yearly.groupby(["candidate", "asof"]):
        for period, years in [("2020-2024", SEL_YEARS), ("2025", [INFO_YEAR])]:
            gg = g[g["year"].isin(years)]
            if gg.empty:
                continue
            summ.append({"candidate": cand, "family": families[cand], "base": bases_of[cand], "asof": asof,
                         "period": period, "years": len(gg), "mean_wape": gg["wape"].mean(),
                         "mean_abs_tot": gg["abs_tot"].mean(), "mean_signed_tot": gg["tot"].mean(),
                         "mean_abs_us48": gg["abs_us48"].mean() if "abs_us48" in gg else np.nan,
                         "mean_signed_us48": gg["us48"].mean() if "us48" in gg else np.nan})
    summary = pd.DataFrame(summ).sort_values(["asof", "period", "family", "candidate"])
    summary.to_csv(OUT / "summary.csv", index=False, float_format="%.4f")

    # ---------------- paired comparisons (Nov, 2020-2024)
    comps = []
    for cand, spec in CANDIDATES.items():
        if spec["base"] is not None:
            comps.append(paired(bt, cand, spec["base"], "nov"))
    for name in ("R", "A", "B"):
        comps.append(paired(bt, name, "p0", "nov"))
    nov_means = summary[(summary["asof"] == "nov") & (summary["period"] == "2020-2024")].set_index(
        "candidate")["mean_wape"].to_dict()
    best = best_satellite(nov_means)
    for asof in ("oct", "sep"):
        comps.append(paired(bt, best, CANDIDATES[best]["base"], asof))
    comparisons = pd.DataFrame(comps)
    adopted_flags, verdicts = [], []
    for row in comps:
        is_primary = CANDIDATES[row["candidate"]]["family"] == "primary" and row["asof"] == "nov"
        if is_primary:
            ok, verdict = adoption(row)
        else:
            ok, verdict = False, "information only"
        adopted_flags.append(ok)
        verdicts.append(verdict)
    comparisons["adopted"] = adopted_flags
    comparisons["verdict"] = verdicts
    comparisons.to_csv(OUT / "comparisons.csv", index=False, float_format="%.4f")
    adopted = {r["candidate"]: r["mean_wape"] for r, ok in zip(comps, adopted_flags) if ok}
    final = choose_final(adopted)

    # ---------------- 2026 shares and forecast
    share_file = OUT / "sat_share_2026_asof_nov.csv"
    if args.recompute_2026 or not share_file.exists():
        table26 = compute_shares_2026(args.workers)
        table26.to_csv(share_file, index=False)
    table26 = pd.read_csv(share_file, dtype={"state_fips": str})
    sh25 = shares_nov[shares_nov["year"] == INFO_YEAR].set_index("state")
    t26 = table26.set_index("state")
    r26 = pd.DataFrame({"state": states, "year": FORECAST_YEAR,
                        "sat_share": [float(clip_ratio(t26.loc[s, "sat_share"], sh25.loc[s, "sat_share"]))
                                      for s in states],
                        "sat_share_calls": [float(clip_ratio(t26.loc[s, "sat_share_calls"],
                                                             sh25.loc[s, "sat_share_calls"])) for s in states]})
    r26_same = pd.DataFrame({"state": states, "year": FORECAST_YEAR,
                             "sat_share": [float(clip_ratio(t26.loc[s, "sat_share"], ph.loc[s, "sat_share"]))
                                           for s in states],
                             "sat_share_calls": [float(clip_ratio(t26.loc[s, "sat_share_calls"],
                                                                  ph.loc[s, "sat_share_calls"])) for s in states]})
    fc = build_predictions(bases, last, r26, snr, [FORECAST_YEAR], "nov")
    fc_same = build_predictions(bases, last, r26_same, snr, [FORECAST_YEAR], "nov").set_index(
        ["state", "candidate"])["pred"]
    m_prob, m_s = mask_error("sat_share")
    m_calls, m_s_calls = mask_error("sat_share_calls")
    o_s = omission_rms()
    quant = {c: log_error_quantiles(bt, c) for c in CANDIDATES}
    cover = {c: loyo_coverage(bt, c) for c in CANDIDATES}
    lo, hi, lo_s, hi_s, ws, same = [], [], [], [], [], []
    for _, row in fc.iterrows():
        spec = CANDIDATES[row["candidate"]]
        mm = m_calls if spec["share"] == "sat_share_calls" else m_prob
        w = Z80 * row["k"] * mm
        w_stress = Z80 * row["k"] * np.sqrt(mm ** 2 + o_s[row["state"]] ** 2)
        a_, b_ = widened(row["pred"], quant[row["candidate"]], w)
        c_, d_ = widened(row["pred"], quant[row["candidate"]], w_stress)
        lo.append(a_), hi.append(b_), lo_s.append(c_), hi_s.append(d_), ws.append(w)
        same.append(fc_same[(row["state"], row["candidate"])] if spec["base"] is not None else np.nan)
    fc["lo80"], fc["hi80"], fc["lo80_stress"], fc["hi80_stress"] = lo, hi, lo_s, hi_s
    fc["mask_w"] = ws
    fc["pred_same_mask_change"] = same
    fc["share_2026"] = [t26.loc[s, "sat_share"] for s in fc["state"]]
    fc["share_calls_2026"] = [t26.loc[s, "sat_share_calls"] for s in fc["state"]]
    fc["share_2025"] = [sh25.loc[s, "sat_share"] for s in fc["state"]]
    fc["share_2025_pred_hist"] = [ph.loc[s, "sat_share"] for s in fc["state"]]
    fc["nass_2025"] = fc["last"]
    fc["q10_log"] = [quant[c][0] for c in fc["candidate"]]
    fc["q50_log"] = [quant[c][1] for c in fc["candidate"]]
    fc["q90_log"] = [quant[c][2] for c in fc["candidate"]]
    fc["loyo_coverage80"] = [cover[c] for c in fc["candidate"]]
    fc["final_model"] = fc["candidate"] == final

    # US totals: candidate for the 15 states + Tier A s3 for the other 33
    fa = pd.read_csv(TIER_A / "forecast_2026.csv")
    us_a = fa[fa["state"].str.startswith("US")].iloc[0]
    fa_states = fa[~fa["state"].str.startswith("US")]
    rest = fa_states[~fa_states["state"].isin(states)]
    if len(fa_states) != 48 or len(rest) != 33:
        raise ValueError("Tier A 2026 forecast does not have 48 states")
    lo_off, hi_off = np.log(us_a["silage_lo80"] / us_a["silage"]), np.log(us_a["silage_hi80"] / us_a["silage"])
    us_rows = []
    for cand, g in fc.groupby("candidate"):
        spec = CANDIDATES[cand]
        mm = m_calls if spec["share"] == "sat_share_calls" else m_prob
        total = g["pred"].sum() + rest["silage"].sum()
        w_us = Z80 * np.sqrt(((g["pred"] * g["k"] * mm) ** 2).sum()) / total
        lo_w = -np.sqrt(lo_off ** 2 + w_us ** 2)
        hi_w = np.sqrt(hi_off ** 2 + w_us ** 2)
        us_rows.append({"state": "US (15 sampled states from candidate + Tier A s3 for 33 others)",
                        "year": FORECAST_YEAR, "asof": "nov", "candidate": cand, "family": spec["family"],
                        "base": spec["base"] or "", "pred": total, "lo80": total * np.exp(lo_w),
                        "hi80": total * np.exp(hi_w), "pred_sample15": g["pred"].sum(),
                        "nass_2025": g["last"].sum() + truth.loc[[(s, 2025) for s in rest["state"]]].sum(),
                        "final_model": cand == final})
    us = pd.DataFrame(us_rows)
    forecast = pd.concat([fc, us], ignore_index=True)
    forecast.to_csv(OUT / "forecast_2026.csv", index=False, float_format="%.4f")

    # 15 states' share of US silage
    s48 = fa_states["state"].tolist()
    share15 = {}
    for year in range(2019, 2026):
        tot48 = sum(truth[(s, year)] for s in s48 if (s, year) in truth.index)
        share15[year] = sum(truth[(s, year)] for s in states) / tot48
    meta = {
        "preregistration_sha256": digest, "unchanged": True,
        "states": states, "selection_years": SEL_YEARS, "info_year": INFO_YEAR,
        "adopted": sorted(adopted), "final_model_2026_sample_states": final,
        "best_satellite_candidate_nov": best,
        "mask_error_M_prob": m_prob, "mask_error_M_calls": m_calls,
        "mask_error_m_s": m_s.round(4).to_dict(), "omission_rms_O_s": o_s.round(4).to_dict(),
        "share15_of_us_silage": {str(k): round(v, 4) for k, v in share15.items()},
        "share15_of_us_silage_mean_2019_2024": round(float(np.mean([share15[y] for y in range(2019, 2025)])), 4),
        "tier_b_backtest_rows_deduplicated": True,
        "n_boot": N_BOOT, "seed": SEED,
    }
    (OUT / "run.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("adopted", "final_model_2026_sample_states",
                                           "best_satellite_candidate_nov")}))


if __name__ == "__main__":
    main()
