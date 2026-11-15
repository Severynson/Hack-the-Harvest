"""sat_full/stress: the sat_stress index on the full state sample with the CDL mask and the real-time mask P.

Implements README.md section 1 (pre-registered, hash in out/preregistration.sha256). Steps:
    components  per candidate field-year 2016-2026, sat_stress field_components (imported) from looks dated on or
                before 15 Sep; 3,300 series files in parallel; cached in out/cache/field_components.parquet
    index       state medians per mask (CDL, P, P_cdlref, P_nov) x weight (none, pps); prior-years anomalies;
                scales rms and xsd; composite stress -> out/stress.csv
    report      targets, correlations, mask agreement, reading rules, replication check, run.json

Run from the repo root:
    .venv/Scripts/python.exe test_models/variations/sat_full/stress/stress.py [--workers 20] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CORN26_DIR = ROOT / "test_models" / "ownModels" / "satellite" / "corn26"
SAT_STRESS = ROOT / "test_models" / "variations" / "sat_stress"
for p in (ROOT, CORN26_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

import corn26  # noqa: E402
from kernelag import silage_level  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402
from kernelag.state_panel import QUICKSTATS_DIR, load_panel  # noqa: E402
from kernelag.state_signal import complete_areas, series_asof  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SS = _load_module("sat_stress_run", SAT_STRESS / "run.py")   # field_components, _shortfall, drought_change

OUT = HERE / "out"
CACHE = OUT / "cache" / "field_components.parquet"
CALLS = HERE.parent / "corn_mask" / "out" / "corn_calls.parquet"
MONTHLY = ROOT / "test_models" / "ownModels" / "monthly" / "out" / "monthly_by_state_year.csv"
COMBOS = ROOT / "test_models" / "variations" / "silage_combos" / "out" / "backtest_by_state_year.csv"
SS_STRESS = SAT_STRESS / "out" / "stress_by_state_year.csv"
STATES = SS.STATES
STEMS = ("candes", "candpc", "candpc16")
COMPONENTS = SS.COMPONENTS                    # {"peak": -1, "ndmi": -1, "decline": +1}
MIN_VALID = SS.MIN_VALID
MIN_FIELDS = SS.MIN_FIELDS
YEARS = list(range(2016, 2027))
# mask -> (field selection column, reference X source, first year of the mask, first anomaly year)
MASKS = {
    "CDL": ("sel_cdl", "CDL", 2016, 2017),
    "P": ("sel_p_sep", "P", 2017, 2018),
    "P_cdlref": ("sel_p_sep", "CDL", 2017, 2017),
    "P_nov": ("sel_p_nov", "P_nov", 2017, 2018),
}
SELECTION_OF = {"CDL": "sel_cdl", "P": "sel_p_sep", "P_nov": "sel_p_nov"}
LAST_YEAR = {"CDL": 2025, "P": 2026, "P_cdlref": 2026, "P_nov": 2026}
AVAILABLE = {"CDL": "look-ahead (CDL of year t is published after the season)", "P": "Sep 15",
             "P_cdlref": "Sep 15", "P_nov": "Nov 15"}
WEIGHTS = ("none", "pps")
SCALES = ("rms", "xsd")
HEADLINE = {"weight": "none", "scale": "rms"}
WINDOWS = {"W17": list(range(2017, 2025)), "W18": list(range(2018, 2025))}
WINDOW_MASKS = {"W17": ("CDL", "P_cdlref"), "W18": tuple(MASKS)}
TARGETS = ["shortfall", "d_drought", "silage_change"]
INFO_TARGETS = ["shortfall_sep", "shortfall_final", "resid_as3", "resid_reversion", "resid_sc", "resid_sc_a"]
XS = ["stress", "signed_z_peak", "signed_z_ndmi", "signed_z_decline"]
PREREG_START, PREREG_END = "## 1. Pre-registration", "<!-- end of pre-registration -->"


# ------------------------------------------------------------------------------------------ pre-registration

def preregistration_status() -> dict:
    text = (HERE / "README.md").read_text(encoding="utf-8")
    section = text[text.index(PREREG_START):text.index(PREREG_END) + len(PREREG_END)]
    now = hashlib.sha256(section.encode("utf-8")).hexdigest()
    stored = (OUT / "preregistration.sha256").read_text(encoding="utf-8").split()[0]
    return {"sha256_now": now, "sha256_stored": stored, "unchanged": now == stored}


# ------------------------------------------------------------------------------------------ components

def load_samples() -> tuple[pd.DataFrame, dict]:
    """Every candidate field-year of the 15 states (three file types), complete areas only."""
    parts, dropped = [], {}
    cols = ["field_id", "year", "cell", "cell_size_acres", "acres", "draw", "is_corn"]
    for stem in STEMS:
        for fips in STATES:
            sample = pd.read_parquet(data_dir() / "samples" / f"{stem}_{fips}.parquet", columns=cols)
            sample["field_id"] = sample["field_id"].astype(str)
            sample["cell"] = sample["cell"].astype(str)
            folder = data_dir() / "s2_series" / f"{stem}_{fips}"
            keep = set(complete_areas(sample, folder))
            dropped[f"{stem}_{fips}"] = int(sample["cell"].nunique() - len(keep))
            parts.append(sample[sample["cell"].isin(keep)].assign(stem=stem, state_fips=fips))
    return pd.concat(parts, ignore_index=True), dropped


def file_components(task: tuple[str, str, str, int]) -> pd.DataFrame:
    """sat_stress field_components of every field in one series file, looks cut at 15 Sep. Runs in a worker."""
    stem, fips, cell, year = task
    series = corn26.read_series_file(data_dir() / "s2_series" / f"{stem}_{fips}" / f"{cell}_{year}.csv")
    series = series[(series["year"] == year) & (series["valid_frac"] >= MIN_VALID) & series["ndvi"].notna()]
    series = series_asof(series, "sep")
    rows = [{"field_id": fid, **SS.field_components(g)} for fid, g in series.groupby("field_id", sort=False)]
    frame = pd.DataFrame(rows, columns=["field_id", *COMPONENTS, "n_looks"])
    return frame.assign(stem=stem, cell=cell, year=year)


def components(sample: pd.DataFrame, workers: int, force: bool) -> tuple[pd.DataFrame, dict]:
    if CACHE.exists() and not force:
        return pd.read_parquet(CACHE), {"cached": True}
    tasks = [(r.stem, r.state_fips, r.cell, int(r.year))
             for r in sample[["stem", "state_fips", "cell", "year"]].drop_duplicates().itertuples()]
    start = time.time()
    with ProcessPoolExecutor(workers) as pool:
        frames = list(pool.map(file_components, tasks, chunksize=4))
    comp = pd.concat(frames, ignore_index=True)
    comp["year"] = comp["year"].astype(int)
    comp.to_parquet(CACHE, index=False)
    return comp, {"cached": False, "files": len(tasks), "seconds": round(time.time() - start, 1)}


def attach_masks(fields: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Selection columns: CDL corn, and P calls at 15 Sep and 15 Nov from the corn_mask agent."""
    calls = pd.read_parquet(CALLS, columns=["stem", "cell", "field_id", "year", "asof", "is_corn_P"])
    calls["year"] = calls["year"].astype(int)
    calls["stem"] = calls["stem"].str.rsplit("_", n=1).str[0]     # corn_mask stores "candes_06"
    keys = ["stem", "cell", "field_id", "year"]
    out = fields
    for asof in ("sep", "nov"):
        one = calls[calls["asof"] == asof][[*keys, "is_corn_P"]].rename(columns={"is_corn_P": f"p_{asof}"})
        out = out.merge(one, on=keys, how="left", validate="one_to_one")
    for col, src in (("sel_cdl", "is_corn"), ("sel_p_sep", "p_sep"), ("sel_p_nov", "p_nov")):
        out[col] = (out[src] == 1).fillna(False).astype(bool)
    check = {"calls_rows_matched": int(out["p_sep"].notna().sum()),
             "field_years": int(len(out)),
             "p_sep_missing_by_year": out[out["p_sep"].isna()].groupby("year").size().to_dict()}
    return out, check


# ------------------------------------------------------------------------------------------ index

def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, 0.5 * cum[-1])])


def state_x(fields: pd.DataFrame, selection: str, weight: str) -> pd.DataFrame:
    """X(s,t) per component over the selected field-years; missing with fewer than MIN_FIELDS values."""
    sel = fields[fields[selection]]
    rows = []
    for (fips, year), g in sel.groupby(["state_fips", "year"]):
        row = {"state_fips": fips, "year": int(year), "n_fields": len(g)}
        for comp in COMPONENTS:
            ok = g[comp].notna().to_numpy()
            row[f"n_{comp}"] = int(ok.sum())
            if ok.sum() < MIN_FIELDS:
                row[comp] = np.nan
            elif weight == "none":
                row[comp] = float(np.median(g[comp].to_numpy()[ok]))
            else:
                w = (g["acres"] / g["cell_size_acres"]).to_numpy()[ok]
                row[comp] = weighted_median(g[comp].to_numpy()[ok], w)
        rows.append(row)
    return pd.DataFrame(rows)


def anomalies(cur: pd.DataFrame, ref: pd.DataFrame, years: list[int], ref_first: int, first_anom: int,
              scale: str) -> pd.DataFrame:
    """Prior-years anomaly, scale and z per component; composite stress. One row per state x year."""
    grid = pd.MultiIndex.from_product([list(STATES), years], names=["state_fips", "year"]).to_frame(index=False)
    table = grid.merge(cur, on=["state_fips", "year"], how="left")
    refw = ref.pivot(index="year", columns="state_fips", values=list(COMPONENTS))
    for comp in COMPONENTS:
        r = refw[comp] if comp in refw.columns.get_level_values(0) else pd.DataFrame()
        means = []
        for fips, year in zip(table["state_fips"], table["year"]):
            prior = r.loc[(r.index >= ref_first) & (r.index < year), fips].dropna() if fips in r.columns else []
            means.append(float(np.mean(prior)) if len(prior) and year >= first_anom else np.nan)
        table[f"ref_{comp}"] = means
        table[f"anom_{comp}"] = table[comp] - table[f"ref_{comp}"]
        sigma = {}
        for year in years:
            a = table[table["year"].between(first_anom, year)][["year", f"anom_{comp}"]].dropna()
            if year < first_anom or a.empty:
                sigma[year] = np.nan
            elif scale == "rms":
                sigma[year] = float(np.sqrt((a[f"anom_{comp}"] ** 2).mean()))
            else:
                dev = a[f"anom_{comp}"] - a.groupby("year")[f"anom_{comp}"].transform("mean")
                dof = float((a.groupby("year").size() - 1).sum())
                sigma[year] = float(np.sqrt((dev ** 2).sum() / dof)) if dof > 0 else np.nan
        table[f"sigma_{comp}"] = table["year"].map(sigma)
        table[f"z_{comp}"] = table[f"anom_{comp}"] / table[f"sigma_{comp}"]
    table["stress"] = sum(sign * table[f"z_{comp}"] for comp, sign in COMPONENTS.items()) / len(COMPONENTS)
    return table


def note_for(mask: str, year: int, row: pd.Series, first_anom: int) -> str:
    if mask == "CDL" and year == 2026:
        return "UNCOMPUTED: no 2026 CDL"
    if mask != "CDL" and year == 2016:
        return "UNCOMPUTED: no prior-year model (P starts 2017)"
    if year < first_anom:
        return "no prior year: no anomaly"
    if pd.isna(row["stress"]):
        missing = [c for c in COMPONENTS if pd.isna(row[f"z_{c}"])]
        return "UNCOMPUTED: component missing (" + ", ".join(missing) + ")"
    return ""


def build_index(fields: pd.DataFrame) -> pd.DataFrame:
    xs = {(src, w): state_x(fields, SELECTION_OF[src], w) for src in SELECTION_OF for w in WEIGHTS}
    parts = []
    for mask, (_, ref_src, first_year, first_anom) in MASKS.items():
        cur_src = {"CDL": "CDL", "P": "P", "P_cdlref": "P", "P_nov": "P_nov"}[mask]
        ref_first = 2016 if ref_src == "CDL" else 2017
        years = list(range(first_year, LAST_YEAR[mask] + 1))
        for w in WEIGHTS:
            cur = xs[(cur_src, w)]
            cur = cur[cur["year"].isin(years)]
            for scale in SCALES:
                t = anomalies(cur, xs[(ref_src, w)], years, ref_first, first_anom, scale)
                t.insert(0, "mask", mask)
                t.insert(1, "weight", w)
                t.insert(2, "scale", scale)
                parts.append(t)
    table = pd.concat(parts, ignore_index=True)
    # rows for the years a mask cannot exist (P 2016, CDL 2026), so every state x year x variant is listed
    full = []
    for (mask, w, scale), g in table.groupby(["mask", "weight", "scale"], sort=False):
        grid = pd.DataFrame([(mask, w, scale, f, y) for f in STATES for y in YEARS],
                            columns=["mask", "weight", "scale", "state_fips", "year"])
        full.append(grid.merge(g, on=["mask", "weight", "scale", "state_fips", "year"], how="left"))
    table = pd.concat(full, ignore_index=True)
    table.insert(3, "state", table["state_fips"].map(STATES))
    first = {m: v[3] for m, v in MASKS.items()}
    table["available_from"] = table["mask"].map(AVAILABLE)
    table["note"] = [note_for(r["mask"], int(r["year"]), r, first[r["mask"]]) for _, r in table.iterrows()]
    for c in ["n_fields", *[f"n_{c}" for c in COMPONENTS]]:
        table[c] = table[c].astype("Int64")
    return table.sort_values(["mask", "weight", "scale", "state_fips", "year"]).reset_index(drop=True)


# ------------------------------------------------------------------------------------------ targets

def _long(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    out = frame.stack().rename(name).reset_index()
    out.columns = ["year", "state", name]
    return out


def targets() -> tuple[pd.DataFrame, dict]:
    folder = data_dir() / QUICKSTATS_DIR
    hist_nov = silage_level.load_history(folder, "nov")
    hist_sep = silage_level.load_history(folder, "sep")
    t = _long(SS._shortfall(hist_nov), "shortfall")
    t = t.merge(_long(SS._shortfall(hist_sep), "shortfall_sep"), on=["year", "state"], how="outer")
    final = {"yield": hist_nov["yield"], "yield_asof": hist_nov["yield"]}
    t = t.merge(_long(SS._shortfall(final), "shortfall_final"), on=["year", "state"], how="outer")
    t = t.merge(SS.drought_change(), on=["state", "year"], how="outer")

    m = pd.read_csv(MONTHLY)
    m = m[m["asof"] == "nov"]
    truth = m[m["model"] == "s3_fsa_residual"][["state", "year", "actual"]]
    last = truth.assign(year=truth["year"] + 1).rename(columns={"actual": "last_actual"})
    t = t.merge(truth, on=["state", "year"], how="outer").merge(last, on=["state", "year"], how="left")
    t["silage_change"] = np.log(t["actual"] / t["last_actual"])
    for model, col in [("s3_fsa_residual", "resid_as3"), ("reversion_only_H00", "resid_reversion")]:
        p = m[m["model"] == model][["state", "year", "pred"]].rename(columns={"pred": f"pred_{col}"})
        t = t.merge(p, on=["state", "year"], how="left")
        t[col] = np.log(t["actual"] / t[f"pred_{col}"])
    c = pd.read_csv(COMBOS)
    c = c[c["asof"] == "nov"]
    for model, col in [("SC", "resid_sc"), ("SC_A", "resid_sc_a")]:
        p = c[c["model"] == model][["state", "year", "pred", "actual"]].rename(
            columns={"pred": f"pred_{col}", "actual": f"actual_{col}"})
        t = t.merge(p, on=["state", "year"], how="left")
        t[col] = np.log(t["actual"] / t[f"pred_{col}"])
    t = t[t["state"].isin(STATES.values())]

    panel = load_panel("nov")[["state", "year", "silage"]]
    chk = t.merge(panel, on=["state", "year"]).dropna(subset=["actual", "silage"])
    combos = t.dropna(subset=["actual", "actual_resid_sc"])
    check = {"truth_vs_panel_rows": int(len(chk)),
             "truth_vs_panel_max_abs_diff": float((chk["actual"] - chk["silage"]).abs().max()),
             "truth_vs_silage_combos_rows": int(len(combos)),
             "truth_vs_silage_combos_max_abs_diff": float((combos["actual"] - combos["actual_resid_sc"]).abs().max())}
    keep = ["state", "year", *TARGETS, *INFO_TARGETS, "actual", "last_actual"]
    return t[keep].sort_values(["state", "year"]).reset_index(drop=True), check


# ------------------------------------------------------------------------------------------ correlations

def corr_row(frame: pd.DataFrame, x: str, y: str) -> dict:
    ok = frame[["year", x, y]].replace([np.inf, -np.inf], np.nan).dropna()
    row = {"x": x, "y": y, "n": int(len(ok)), "n_years": int(ok["year"].nunique())}
    if len(ok) < 5 or ok[x].std() == 0:
        return {**row, "pearson": np.nan, "pearson_p": np.nan, "spearman": np.nan, "spearman_p": np.nan,
                "within_year_r": np.nan, "within_year_p": np.nan}
    pr, pp = stats.pearsonr(ok[x], ok[y])
    sr, sp = stats.spearmanr(ok[x], ok[y])
    dx = ok[x] - ok.groupby("year")[x].transform("mean")
    dy = ok[y] - ok.groupby("year")[y].transform("mean")
    rw = float((dx * dy).sum() / np.sqrt((dx ** 2).sum() * (dy ** 2).sum()))
    dof = len(ok) - 2 - (ok["year"].nunique() - 1)
    pw = float(2 * stats.t.sf(abs(rw) * np.sqrt(dof / max(1e-12, 1 - rw ** 2)), dof)) if dof > 0 else np.nan
    return {**row, "pearson": float(pr), "pearson_p": float(pp), "spearman": float(sr), "spearman_p": float(sp),
            "within_year_r": rw, "within_year_p": pw}


def correlations(index: pd.DataFrame, tgt: pd.DataFrame) -> pd.DataFrame:
    frame = index.merge(tgt, on=["state", "year"], how="left")
    for comp, sign in COMPONENTS.items():
        frame[f"signed_z_{comp}"] = sign * frame[f"z_{comp}"]
    rows = []
    for window, years in WINDOWS.items():
        for (mask, w, scale), g in frame[frame["year"].isin(years)].groupby(["mask", "weight", "scale"]):
            if mask not in WINDOW_MASKS[window]:
                continue
            for x in XS:
                for y in TARGETS + INFO_TARGETS:
                    rows.append({"window": window, "years": f"{years[0]}-{years[-1]}", "mask": mask, "weight": w,
                                 "scale": scale, "target_kind": "target" if y in TARGETS else "information",
                                 **corr_row(g, x, y)})
    return pd.DataFrame(rows)


def mask_agreement(index: pd.DataFrame) -> pd.DataFrame:
    rows = []
    years = WINDOWS["W18"]
    for (w, scale), g in index[index["year"].isin(years)].groupby(["weight", "scale"]):
        ref = g[g["mask"] == "CDL"].set_index(["state_fips", "year"])
        for mask in ("P", "P_cdlref", "P_nov"):
            cur = g[g["mask"] == mask].set_index(["state_fips", "year"])
            for col in ["stress", *[f"z_{c}" for c in COMPONENTS], *COMPONENTS]:
                pair = pd.concat([cur[col].rename("m"), ref[col].rename("cdl")], axis=1).dropna()
                r = float(stats.pearsonr(pair["m"], pair["cdl"])[0]) if len(pair) >= 5 else np.nan
                rows.append({"weight": w, "scale": scale, "mask": mask, "vs": "CDL", "column": col,
                             "years": f"{years[0]}-{years[-1]}", "n": int(len(pair)), "pearson": r,
                             "mean_diff": float((pair["m"] - pair["cdl"]).mean()),
                             "mean_abs_diff": float((pair["m"] - pair["cdl"]).abs().mean())})
    return pd.DataFrame(rows)


def reading_rules(corr: pd.DataFrame, agree: pd.DataFrame) -> pd.DataFrame:
    def get(window, mask, w, scale, y, x="stress"):
        r = corr[(corr["window"] == window) & (corr["mask"] == mask) & (corr["weight"] == w)
                 & (corr["scale"] == scale) & (corr["x"] == x) & (corr["y"] == y)]
        return r.iloc[0] if len(r) else None

    rows = []
    for w in WEIGHTS:
        for scale in SCALES:
            role = "headline" if (w, scale) == (HEADLINE["weight"], HEADLINE["scale"]) else "information"
            for window, masks in WINDOW_MASKS.items():
                for mask in masks:
                    a, b = get(window, mask, w, scale, "shortfall"), get(window, mask, w, scale, "d_drought")
                    c = get(window, mask, w, scale, "silage_change")
                    r1 = bool(a["pearson"] > 0 and a["pearson_p"] < 0.05 and b["pearson"] > 0
                              and b["pearson_p"] < 0.05)
                    r2 = bool(c["pearson"] > 0 and c["pearson_p"] < 0.05)
                    pre = (role == "headline" and mask == "CDL" and window == "W17")
                    rows.append({"rule": "R1", "window": window, "mask": mask, "weight": w, "scale": scale,
                                 "role": "pre-registered" if pre else role, "pass": r1,
                                 "detail": f"r_shortfall={a['pearson']:.3f} (p={a['pearson_p']:.4f}); "
                                           f"r_d_drought={b['pearson']:.3f} (p={b['pearson_p']:.4f})"})
                    rows.append({"rule": "R2", "window": window, "mask": mask, "weight": w, "scale": scale,
                                 "role": "pre-registered" if pre else role, "pass": r2,
                                 "detail": f"r_silage_change={c['pearson']:.3f} (p={c['pearson_p']:.4f}); "
                                           f"within-year r={c['within_year_r']:.3f} (p={c['within_year_p']:.4f})"})
            for mask in ("P", "P_cdlref", "P_nov"):
                ag = agree[(agree["weight"] == w) & (agree["scale"] == scale) & (agree["mask"] == mask)
                           & (agree["column"] == "stress")].iloc[0]
                gaps = {y: get("W18", mask, w, scale, y)["pearson"] - get("W18", "CDL", w, scale, y)["pearson"]
                        for y in TARGETS}
                ok = bool(ag["pearson"] >= 0.80 and all(abs(v) <= 0.10 for v in gaps.values()))
                pre = role == "headline" and mask == "P"
                rows.append({"rule": "R3", "window": "W18", "mask": mask, "weight": w, "scale": scale,
                             "role": "pre-registered" if pre else role, "pass": ok,
                             "detail": f"r(stress,CDL)={ag['pearson']:.3f}; r gap vs CDL: "
                                       + ", ".join(f"{k} {v:+.3f}" for k, v in gaps.items())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------ replication

def replication(fields: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """CDL mask, draw-1 areas, 2019-2024, reference from 2019, rms sigma from 2020, vs sat_stress's table."""
    sub = fields[(fields["draw"] == 1) & fields["year"].between(2019, 2024)]
    x = state_x(sub, "sel_cdl", "none")
    years = list(range(2019, 2025))
    mine = anomalies(x, x, years, 2019, 2020, "rms")
    old = pd.read_csv(SS_STRESS, dtype={"state_fips": str})
    both = mine.merge(old, on=["state_fips", "year"], suffixes=("_new", "_old"))
    summary = {}
    for col in [*COMPONENTS, "stress", *[f"n_{c}" for c in COMPONENTS]]:
        pair = both[[f"{col}_new", f"{col}_old"]].dropna()
        summary[col] = {"n": int(len(pair)), "max_abs_diff": float((pair.iloc[:, 0] - pair.iloc[:, 1]).abs().max()),
                        "pearson": float(stats.pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])[0]) if len(pair) > 2
                        else np.nan}
    keep = ["state_fips", "year", *[f"{c}_{s}" for c in [*COMPONENTS, "stress"] for s in ("new", "old")]]
    return both[keep], summary


# ------------------------------------------------------------------------------------------ main

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--force", action="store_true", help="recompute field components")
    args = parser.parse_args()
    if args.workers > 20:
        raise SystemExit("at most 20 workers")
    prereg = preregistration_status()
    if not prereg["unchanged"]:
        raise SystemExit(f"pre-registration section changed since hashing: {prereg}")
    t0 = time.time()

    sample, dropped = load_samples()
    comp, comp_info = components(sample, args.workers, args.force)
    fields = sample.merge(comp, on=["stem", "cell", "field_id", "year"], how="left", validate="one_to_one")
    fields, mask_check = attach_masks(fields)

    index = build_index(fields)
    num = index.select_dtypes("float").columns
    index[num] = index[num].round(6)
    index.to_csv(OUT / "stress.csv", index=False)

    tgt, truth_check = targets()
    tgt.to_csv(OUT / "targets_state_year.csv", index=False, float_format="%.6f")
    corr = correlations(index, tgt)
    corr.to_csv(OUT / "correlations.csv", index=False, float_format="%.4f")
    agree = mask_agreement(index)
    agree.to_csv(OUT / "mask_agreement.csv", index=False, float_format="%.4f")
    rules = reading_rules(corr, agree)
    rules.to_csv(OUT / "reading_rules.csv", index=False)
    rep, rep_summary = replication(fields)
    rep.to_csv(OUT / "replication_check.csv", index=False, float_format="%.5f")

    sel_counts = fields.groupby("year")[["sel_cdl", "sel_p_sep", "sel_p_nov"]].sum().astype(int)
    looks = fields[fields["sel_cdl"]].groupby("year")["n_looks"].median()
    head = index[(index["weight"] == "none") & (index["scale"] == "rms")]
    run = {"status": "done", "preregistration": prereg, "areas_dropped_incomplete": dropped,
           "components": comp_info, "field_years": int(len(fields)),
           "field_years_with_all_components": int(fields[list(COMPONENTS)].notna().all(axis=1).sum()),
           "mask_check": mask_check, "truth_check": truth_check, "replication": rep_summary,
           "selected_field_years_by_year": sel_counts.to_dict(orient="index"),
           "median_clear_looks_to_sep15_cdl_corn_by_year": looks.to_dict(),
           "headline_stress_missing": head[head["stress"].isna()].groupby(["mask", "note"]).size().reset_index(name="n")
           .to_dict("records"),
           "seconds": round(time.time() - t0, 1)}
    (OUT / "run.json").write_text(json.dumps(run, indent=1, default=str), encoding="utf-8")

    pd.set_option("display.width", 220)
    print(json.dumps({k: run[k] for k in ("components", "mask_check", "truth_check", "replication")}, indent=1,
                     default=str))
    c = corr[(corr["weight"] == "none") & (corr["scale"] == "rms") & (corr["x"] == "stress")
             & (corr["target_kind"] == "target")]
    print(c[["window", "mask", "y", "n", "pearson", "pearson_p", "spearman", "within_year_r", "within_year_p"]]
          .round(3).to_string())
    print(rules[rules["role"] == "pre-registered"].to_string())


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()
