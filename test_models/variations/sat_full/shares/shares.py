"""Silage-like share per state, year (2016-2026) and forecast date on the full state sample (agent key: shares).

Steps (each reuses its cache unless --force; every step checks the pre-registration hash first):
    prereg     hash README section 1 into out/preregistration.sha256 (only if absent)
    features   kernelag.features.build_features per candidate field-year, cut at 15 Aug..15 Dec
               (multiprocessing, one task per series file) -> out/cache/features/<stem>.parquet
    probs      K0 (logistic, Quebec 2023), K1 (f1_xgb_mono, qcm 2019-2026), K1_xs (K1 without the target
               Quebec season) -> out/cache/probs.parquet
    shares     area totals per mask (CDL, P), shares with kernelag.state_signal.share / jackknife_se, changes
               with a same-area jackknife -> out/shares*.csv, out/changes.csv, out/cache/area_totals.parquet
    diag       D1-D5 of README 1.8 -> out/diag_*.csv
    all        everything above in order

Run from the repo root:
    .venv/Scripts/python.exe test_models/variations/sat_full/shares/shares.py all --workers 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CORN26_DIR = REPO / "test_models" / "ownModels" / "satellite" / "corn26"
VARIANTS_DIR = REPO / "test_models" / "variations" / "field_variants"
for _path in (REPO, CORN26_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from kernelag.context import ASOF_MONTH  # noqa: E402

ASOF_MONTH.setdefault("dec", 12)   # run-time only, inside this program's processes (README 1.2)

import corn26  # noqa: E402
from kernelag.features import build_features  # noqa: E402
from kernelag.field_model import DECISION_THRESHOLD, MODEL_FEATURES  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402
from kernelag.state_signal import complete_areas, jackknife_se, series_asof, share, state_table  # noqa: E402

OUT = HERE / "out"
CACHE = OUT / "cache"
FEATURE_CACHE = CACHE / "features"
README = HERE / "README.md"
BEGIN, END = "<!-- PREREGISTRATION:BEGIN -->", "<!-- PREREGISTRATION:END -->"
SCRATCH = Path("C:/Users/danie/AppData/Local/Temp/claude/dfe35210c43945cb/"
               "9bd8cc88-21cc-4423-8ecd-0115ef62e1a4/scratchpad/agents/shares")
FV_CACHE_THEIRS = SCRATCH.parent / "field_variants" / "cache"
FV_CACHE_MINE = SCRATCH / "fv_cache"
CORN_CALLS = REPO / "test_models" / "variations" / "sat_full" / "corn_mask" / "out" / "corn_calls.parquet"
MONTHLY = REPO / "test_models" / "ownModels" / "monthly" / "out" / "monthly_by_state_year.csv"
PANEL = REPO / "data" / "panel" / "state_year.csv"
EARLIER = REPO / "test_models" / "ownModels" / "satellite" / "signal" / "out"

STATES = {"06": "CALIFORNIA", "08": "COLORADO", "16": "IDAHO", "19": "IOWA", "20": "KANSAS", "26": "MICHIGAN",
          "27": "MINNESOTA", "31": "NEBRASKA", "36": "NEW YORK", "38": "NORTH DAKOTA", "39": "OHIO",
          "42": "PENNSYLVANIA", "46": "SOUTH DAKOTA", "48": "TEXAS", "55": "WISCONSIN"}
PREFIXES = ("candes", "candpc", "candpc16")
ASOFS = ("aug", "sep", "oct", "nov", "dec")
YEARS = tuple(range(2016, 2027))
FUTURE_YEAR = 2026                       # 15 Dec 2026 is after the data date
CLASSIFIERS = ("K0", "K1", "K1_xs")
HEADLINE_CLASSIFIERS = ("K0", "K1")
MASKS = ("CDL", "P")
POOLS = ("1+2", "1")
QCM_YEARS = tuple(range(2019, 2027))
FEATURE_COLUMNS = ["n_obs", *MODEL_FEATURES, "peak_doy", "cut_doy"]
MIN_ASSESSABLE_SHARE, MIN_ASSESSABLE_AREAS = 0.5, 5
K0_GATE = {"n": 3128, "TP": 877, "FP": 345, "FN": 390, "TN": 1516}
BOOT_DRAWS, PERMUTATIONS, SEED = 2000, 10000, 0
WINDOWS = {"CDL": tuple(range(2017, 2025)), "P": tuple(range(2018, 2025))}   # D1 transitions t
COMMON_WINDOW = tuple(range(2018, 2025))
RATIO_YEARS = {"CDL": tuple(range(2016, 2025)), "P": tuple(range(2017, 2025))}  # D3/D4 years
INFO_YEAR = 2025
SHARE_COLUMNS = ["state", "state_fips", "year", "asof", "classifier", "mask", "areas", "fields",
                 "assessable_share", "share", "share_se", "status"]


# ------------------------------------------------------------------------------------- pre-registration


def prereg_block() -> str:
    text = README.read_text(encoding="utf-8").replace("\r\n", "\n")
    start, stop = text.index(BEGIN) + len(BEGIN), text.index(END)
    return text[start:stop]


def prereg_digest() -> str:
    return hashlib.sha256(prereg_block().encode("utf-8")).hexdigest()


def cmd_prereg() -> None:
    target = OUT / "preregistration.sha256"
    digest = prereg_digest()
    if target.exists():
        stored = target.read_text(encoding="utf-8").split()[0]
        print(f"pre-registration already hashed: {stored} ({'unchanged' if stored == digest else 'CHANGED'})")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    target.write_text(f"{digest}  README.md section 1 (between the PREREGISTRATION markers), {stamp}\n",
                      encoding="utf-8", newline="\n")
    print(f"pre-registration hashed: {digest}")


def check_prereg() -> str:
    target = OUT / "preregistration.sha256"
    if not target.exists():
        raise SystemExit("no out/preregistration.sha256: run the prereg step first")
    stored, digest = target.read_text(encoding="utf-8").split()[0], prereg_digest()
    if stored != digest:
        raise SystemExit(f"README section 1 changed after pre-registration ({digest} != {stored}); refusing to run")
    return digest


# ------------------------------------------------------------------------------------------- features


def stems() -> list[str]:
    return [f"{prefix}_{fips}" for prefix in PREFIXES for fips in STATES]


def read_sample(stem: str) -> pd.DataFrame:
    sample = pd.read_parquet(data_dir() / "samples" / f"{stem}.parquet", columns=["field_id", "year", "cell"])
    sample["field_id"] = sample["field_id"].astype(str)
    sample["cell"] = sample["cell"].astype(str)
    return sample


def series_tasks(stem: str) -> tuple[list[str], list[str], list[str]]:
    """Series files of the complete areas of one stem; also the complete and incomplete cells."""
    sample = read_sample(stem)
    folder = data_dir() / "s2_series" / stem
    complete = sorted(complete_areas(sample, folder))
    incomplete = sorted(set(sample["cell"]) - set(complete))
    pairs = sample[sample["cell"].isin(complete)][["cell", "year"]].drop_duplicates()
    files = [str(folder / f"{cell}_{int(year)}.csv") for cell, year in pairs.itertuples(index=False)]
    return sorted(files), complete, incomplete


def features_for_file(path: str) -> pd.DataFrame:
    """Harvest features of every field-year in one series file, at every forecast date (README 1.3)."""
    file = Path(path)
    cell, year = file.stem.rsplit("_", 1)
    series = corn26.read_series_file(file)
    parts = []
    for asof in ASOFS:
        if asof == "dec" and int(year) == FUTURE_YEAR:
            continue   # UNCOMPUTED: 15 Dec 2026 is in the future
        cut = series_asof(series, asof)
        features = build_features(cut) if not cut.empty else pd.DataFrame(columns=["field_id", "year"])
        for column in FEATURE_COLUMNS:
            if column not in features:
                features[column] = np.nan
        features = features[["field_id", "year", *FEATURE_COLUMNS]].copy()
        features["asof"] = asof
        parts.append(features)
    table = pd.concat(parts, ignore_index=True)
    table["field_id"] = table["field_id"].astype(str)
    table["year"] = table["year"].astype(int)
    table[FEATURE_COLUMNS] = table[FEATURE_COLUMNS].astype(float)
    table.insert(0, "cell", cell)
    return table


def cmd_features(workers: int, force: bool) -> dict:
    FEATURE_CACHE.mkdir(parents=True, exist_ok=True)
    plan, info = {}, {"incomplete_cells": {}, "complete_cells": {}}
    for stem in stems():
        files, complete, incomplete = series_tasks(stem)
        info["complete_cells"][stem], info["incomplete_cells"][stem] = len(complete), incomplete
        if force or not (FEATURE_CACHE / f"{stem}.parquet").exists():
            plan[stem] = files
    n_files = sum(len(f) for f in plan.values())
    print(f"features: {len(plan)} stems to compute, {n_files} series files, {workers} workers", flush=True)
    started, done = time.time(), 0
    if plan:
        pending = {stem: [] for stem in plan}
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(features_for_file, f): stem for stem, files in plan.items() for f in files}
            for future in as_completed(futures):
                stem = futures[future]
                pending[stem].append(future.result())
                done += 1
                if len(pending[stem]) == len(plan[stem]):
                    table = pd.concat(pending.pop(stem), ignore_index=True)
                    table.insert(0, "stem", stem)
                    table.to_parquet(FEATURE_CACHE / f"{stem}.parquet", index=False)
                if done % 300 == 0 or done == n_files:
                    print(f"  {done}/{n_files} files, {time.time() - started:.0f} s", flush=True)
    info["features_seconds"] = round(time.time() - started, 1)
    info["series_files"] = n_files
    return info


def load_features() -> pd.DataFrame:
    parts = [pd.read_parquet(FEATURE_CACHE / f"{stem}.parquet") for stem in stems()]
    table = pd.concat(parts, ignore_index=True)
    table["field_id"] = table["field_id"].astype(str)
    return table


# --------------------------------------------------------------------------------------- classifiers


def fit_k0() -> tuple[object, dict]:
    """K0 through the earlier round's signal module, with the Quebec leave-one-cell-out gate (G1)."""
    from kernelag.field_model import predict_silage, scores
    from test_models.ownModels.satellite.signal import signal as sig

    model, train = sig.fit_allqc_model()
    truth, call = train["is_silage"].to_numpy(), np.zeros(len(train), int)
    cells = train["cell"].to_numpy()
    for cell in sorted(set(cells)):
        held = cells == cell
        call[held] = predict_silage(sig.fit_model(train[~held]), train[held].reset_index(drop=True))[1]
    counts = {k: v for k, v in scores(truth, call).items() if k in ("TP", "FP", "FN", "TN")}
    observed = {"n": int(train["assessable"].sum()), **counts}
    return model, {"observed": observed, "expected": K0_GATE, "reproduced": observed == K0_GATE}


def import_variants():
    """field_variants' module with its feature cache redirected to this agent's scratch folder."""
    FV_CACHE_MINE.mkdir(parents=True, exist_ok=True)
    if FV_CACHE_THEIRS.is_dir():
        for path in FV_CACHE_THEIRS.glob("qcm_*"):
            if not (FV_CACHE_MINE / path.name).exists():
                shutil.copy2(path, FV_CACHE_MINE / path.name)
    os.environ["FIELD_VARIANTS_CACHE"] = str(FV_CACHE_MINE)
    if str(VARIANTS_DIR) not in sys.path:
        sys.path.insert(0, str(VARIANTS_DIR))
    import variants

    if Path(variants.CACHE) != FV_CACHE_MINE:
        raise RuntimeError(f"field_variants cache not redirected: {variants.CACHE}")
    return variants


def fit_k1(workers: int) -> tuple[object, dict, dict, object]:
    """K1 on all qcm seasons, K1_xs models (one per left-out season) and the roster gate (G2)."""
    variants = import_variants()
    table, _, digests = variants.load_years(list(QCM_YEARS), workers=min(workers, 8))
    full = table[table["asof"] == "full"].reset_index(drop=True)
    rosters = {int(y): int(n) for y, n in full.groupby("year").size().items()}
    expected = {int(y): int(n) for y, n in variants.R1_EXPECTED.items()}
    gate = {"observed": rosters, "expected": expected,
            "reproduced": all(rosters.get(y) == n for y, n in expected.items()),
            "assessable_fit_rows": int(full["assessable"].sum()), "digests": digests}
    spec = variants.SPECS["f1_xgb_mono"]
    model = variants.fit(spec, full)
    left_out = {year: variants.fit(spec, full[full["year"] != year]) for year in QCM_YEARS}
    return model, left_out, gate, variants


def cmd_probs(workers: int, force: bool) -> dict:
    target = CACHE / "probs.parquet"
    if target.exists() and not force:
        print("probs: cached")
        return json.loads((CACHE / "probs_gates.json").read_text(encoding="utf-8"))
    started = time.time()
    features = load_features()
    features["assessable"] = features["max_drop"].notna()
    ok = features["assessable"].to_numpy()
    model0, gate0 = fit_k0()
    print(f"K0 gate G1: {'REPRODUCED' if gate0['reproduced'] else 'NOT REPRODUCED'} {gate0['observed']}", flush=True)
    model1, left_out, gate1, variants = fit_k1(workers)
    print(f"K1 gate G2: {'REPRODUCED' if gate1['reproduced'] else 'NOT REPRODUCED'} {gate1['observed']}", flush=True)
    spec = variants.SPECS["f1_xgb_mono"]
    out = features[["stem", "cell", "field_id", "year", "asof", "assessable", "n_obs", "peak_doy", "cut_doy"]].copy()
    p0 = np.full(len(features), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        p0[ok] = model0.predict_proba(features.loc[ok, MODEL_FEATURES])[:, 1]
    out["p_K0"] = p0
    out["p_K1"] = variants.predict(spec, model1, features)
    p_xs = out["p_K1"].to_numpy().copy()
    for year, model in left_out.items():
        rows = (features["year"] == year).to_numpy()
        if rows.any():
            p_xs[rows] = variants.predict(spec, model, features[rows])
    out["p_K1_xs"] = p_xs
    out.to_parquet(target, index=False)
    gates = {"G1_K0": gate0, "G2_K1": gate1, "probs_seconds": round(time.time() - started, 1),
             "field_rows": int(len(out)), "assessable_rows": int(ok.sum())}
    (CACHE / "probs_gates.json").write_text(json.dumps(gates, indent=1, default=str), encoding="utf-8")
    return gates


# ------------------------------------------------------------------------------------------- shares


def load_calls() -> pd.DataFrame:
    columns = ["stem", "state_fips", "cell", "field_id", "year", "asof", "is_corn_P", "is_corn_cdl", "acres",
               "cell_size_acres", "draw"]
    calls = pd.read_parquet(CORN_CALLS, columns=columns)
    calls["asof"] = calls["asof"].astype(str)
    calls = calls[calls["asof"].isin(ASOFS)].reset_index(drop=True)
    calls["year"] = calls["year"].astype(int)
    for column in ("stem", "state_fips", "cell", "field_id"):
        calls[column] = calls[column].astype(str)
    return calls


def gate_sample_counts(calls: pd.DataFrame) -> dict:
    """G0: field-years per stem, cell and year in corn_calls equal the sample files."""
    mine = calls[calls["asof"] == "nov"].groupby(["stem", "cell", "year"]).size()
    theirs = pd.concat({stem: read_sample(stem).groupby(["cell", "year"]).size() for stem in stems()},
                       names=["stem", "cell", "year"])
    joined = pd.concat([mine.rename("calls"), theirs.rename("sample")], axis=1)
    mismatched = int((joined["calls"] != joined["sample"]).sum())
    return {"cell_years": int(len(joined)), "mismatched": mismatched, "reproduced": mismatched == 0,
            "field_years": int(joined["sample"].sum())}


def area_totals_all(calls: pd.DataFrame, probs: pd.DataFrame, complete: dict) -> pd.DataFrame:
    """Per mask, state, year, date and area: kernelag.state_signal.area_totals' columns, per classifier."""
    keep = [(stem, cell) for stem, cells in complete.items() for cell in cells]
    ok_cells = pd.MultiIndex.from_tuples(keep, names=["stem", "cell"])
    calls = calls[pd.MultiIndex.from_frame(calls[["stem", "cell"]]).isin(ok_cells)]
    fields = calls.merge(probs.drop(columns=["cell"]), on=["stem", "field_id", "year", "asof"], how="left",
                         validate="one_to_one")
    fields["assessable"] = fields["assessable"].fillna(False).astype(bool)
    ok = fields["assessable"].to_numpy()
    fields["corn_acres"] = np.where(ok, fields["acres"], 0.0)
    aggregations = {"cell_size_acres": ("cell_size_acres", "first"), "draw": ("draw", "first"),
                    "fields": ("field_id", "size"), "sampled_acres": ("acres", "sum"),
                    "corn_acres": ("corn_acres", "sum"), "median_peak_doy": ("peak_doy", "median"),
                    "median_cut_doy": ("cut_doy", "median")}
    for name in CLASSIFIERS:
        p = fields[f"p_{name}"].to_numpy()
        fields[f"sl_{name}"] = fields["corn_acres"] * np.nan_to_num(p, nan=0.0)
        fields[f"ca_{name}"] = fields["corn_acres"] * (np.nan_to_num(p, nan=0.0) >= DECISION_THRESHOLD)
        aggregations[f"sl_{name}"] = (f"sl_{name}", "sum")
        aggregations[f"ca_{name}"] = (f"ca_{name}", "sum")
    parts = []
    for mask, column in (("CDL", "is_corn_cdl"), ("P", "is_corn_P")):
        chosen = fields[fields[column].fillna(0).astype(int) == 1]
        totals = chosen.groupby(["state_fips", "year", "asof", "cell"]).agg(**aggregations).reset_index()
        totals.insert(0, "mask", mask)
        parts.append(totals)
    return pd.concat(parts, ignore_index=True)


def uncomputed_reason(mask: str, year: int, asof: str) -> str | None:
    if asof == "dec" and year == FUTURE_YEAR:
        return "UNCOMPUTED: 15 Dec 2026 is in the future"
    if mask == "CDL" and year == FUTURE_YEAR:
        return "UNCOMPUTED: no 2026 CDL"
    if mask == "P" and year == YEARS[0]:
        return "UNCOMPUTED: no prior year for the P corn mask"
    return None


def jackknife(num: np.ndarray, den: np.ndarray) -> float:
    """Leave-one-area-out SE of sum(num)/sum(den) (num, den already divided by cell size)."""
    n = len(num)
    if n < 2:
        return float("nan")
    left = (num.sum() - num) / (den.sum() - den)
    return float(np.sqrt((n - 1) / n * ((left - left.mean()) ** 2).sum()))


def share_rows(totals: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mask, fips, asof, year), group in totals.groupby(["mask", "state_fips", "asof", "year"]):
        for pool in POOLS:
            areas = group if pool == "1+2" else group[group["draw"] == 1]
            areas = areas.reset_index(drop=True)
            assessable = areas[areas["corn_acres"] > 0]
            weight = 1.0 / assessable["cell_size_acres"].to_numpy()
            base = {"state": STATES[fips], "state_fips": fips, "year": int(year), "asof": asof, "mask": mask,
                    "draws": pool, "areas": len(areas), "fields": int(areas["fields"].sum()),
                    "assessable_areas": len(assessable),
                    "assessable_share": (float(areas["corn_acres"].sum() / areas["sampled_acres"].sum())
                                         if len(areas) else np.nan),
                    "corn_acres_w": float((areas["corn_acres"] / areas["cell_size_acres"]).sum()),
                    "mask_acres_w": float((areas["sampled_acres"] / areas["cell_size_acres"]).sum()),
                    "median_peak_doy": float(areas["median_peak_doy"].median()),
                    "median_cut_doy": float(areas["median_cut_doy"].median())}
            for name in CLASSIFIERS:
                frame = areas.rename(columns={f"sl_{name}": "silage_like_acres"})
                frame_ok = assessable.rename(columns={f"sl_{name}": "silage_like_acres"})
                ok = len(frame_ok) > 0
                rows.append({**base, "classifier": name,
                             "share": share(frame) if ok else np.nan,
                             "share_se": jackknife_se(frame_ok) if ok else np.nan,
                             "share_calls": share(areas, f"ca_{name}") if ok else np.nan,
                             "share_calls_se": (jackknife(assessable[f"ca_{name}"].to_numpy() * weight,
                                                          assessable["corn_acres"].to_numpy() * weight)
                                                if ok else np.nan)})
    return pd.DataFrame(rows)


def complete_grid(table: pd.DataFrame) -> pd.DataFrame:
    """Every state x year x date x classifier x mask x pool, UNCOMPUTED rows included, with status."""
    index = pd.MultiIndex.from_product([list(STATES), YEARS, ASOFS, CLASSIFIERS, MASKS, POOLS],
                                       names=["state_fips", "year", "asof", "classifier", "mask", "draws"])
    grid = index.to_frame(index=False)
    table = grid.merge(table, on=list(index.names), how="left")
    table["state"] = table["state_fips"].map(STATES)
    status = []
    for row in table.itertuples(index=False):
        reason = uncomputed_reason(row.mask, row.year, row.asof)
        if reason is None and not np.isfinite(row.share):
            reason = "UNCOMPUTED: no assessable mask field-years"
        if reason is None and row.assessable_share < MIN_ASSESSABLE_SHARE:
            reason = f"fallback: assessable_share < {MIN_ASSESSABLE_SHARE}"
        if reason is None and row.assessable_areas < MIN_ASSESSABLE_AREAS:
            reason = f"fallback: assessable areas < {MIN_ASSESSABLE_AREAS}"
        status.append(reason or "ok")
    table["status"] = status
    gone = table["status"].str.startswith("UNCOMPUTED")
    table.loc[gone, ["share", "share_se", "share_calls", "share_calls_se"]] = np.nan
    order = {a: i for i, a in enumerate(ASOFS)}
    return table.sort_values(["draws", "classifier", "mask", "state", "year", "asof"],
                             key=lambda s: s.map(order) if s.name == "asof" else s).reset_index(drop=True)


def change_rows(totals: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    """Every consecutive-year change on the same areas, with the same-area jackknife (README 1.8 D2)."""
    computed = detail[~detail["status"].str.startswith("UNCOMPUTED")]
    have = set(zip(computed["mask"], computed["state_fips"], computed["asof"], computed["draws"],
                   computed["classifier"], computed["year"]))
    rows = []
    for (mask, fips, asof), group in totals.groupby(["mask", "state_fips", "asof"]):
        for pool in POOLS:
            areas = group if pool == "1+2" else group[group["draw"] == 1]
            for year in YEARS[1:]:
                now, before = areas[areas["year"] == year], areas[areas["year"] == year - 1]
                cells = sorted(set(now.loc[now["corn_acres"] > 0, "cell"])
                               | set(before.loc[before["corn_acres"] > 0, "cell"]))
                if not cells:
                    continue
                a = now.set_index("cell").reindex(cells)
                b = before.set_index("cell").reindex(cells)
                size = pd.concat([a["cell_size_acres"], b["cell_size_acres"]], axis=1).bfill(axis=1).iloc[:, 0]
                weight = 1.0 / size.to_numpy()
                den_a = a["corn_acres"].fillna(0).to_numpy() * weight
                den_b = b["corn_acres"].fillna(0).to_numpy() * weight
                for name in CLASSIFIERS:
                    if not {(mask, fips, asof, pool, name, year), (mask, fips, asof, pool, name, year - 1)} <= have:
                        continue
                    num_a = a[f"sl_{name}"].fillna(0).to_numpy() * weight
                    num_b = b[f"sl_{name}"].fillna(0).to_numpy() * weight
                    s_a, s_b = num_a.sum() / den_a.sum(), num_b.sum() / den_b.sum()
                    n = len(cells)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        left_a = (num_a.sum() - num_a) / (den_a.sum() - den_a)
                        left_b = (num_b.sum() - num_b) / (den_b.sum() - den_b)
                        d_left, dl_left = left_a - left_b, np.log(left_a) - np.log(left_b)

                    def se(values: np.ndarray) -> float:
                        values = values[np.isfinite(values)]
                        k = len(values)
                        return float(np.sqrt((k - 1) / k * ((values - values.mean()) ** 2).sum())) if k > 1 else np.nan

                    rows.append({"state": STATES[fips], "state_fips": fips, "year": year, "asof": asof,
                                 "classifier": name, "mask": mask, "draws": pool, "areas_union": n,
                                 "share_prev": s_b, "share": s_a, "d_share": s_a - s_b,
                                 "d_log_share": float(np.log(s_a) - np.log(s_b)),
                                 "se_d_share": se(d_left), "se_d_log_share": se(dl_left)})
    return pd.DataFrame(rows)


def truth_table() -> pd.DataFrame:
    """NASS final silage (and grain) acres for the 15 states, 2015-2025 (README 1.7)."""
    monthly = pd.read_csv(MONTHLY)
    silage = monthly[(monthly["model"] == "s0_persistence")].drop_duplicates(["state", "year"])
    silage = silage[silage["state"].isin(STATES.values())][["state", "year", "actual"]]
    panel = pd.read_csv(PANEL)
    panel = panel[panel["state"].isin(STATES.values())][["state", "year", "silage", "grain"]]
    table = panel.merge(silage, on=["state", "year"], how="left")
    check = table[(table["year"] >= 2016) & (table["year"] <= 2024)]
    if check["actual"].isna().any() or (check["actual"] != check["silage"]).any():
        raise ValueError("data/panel/state_year.csv silage differs from the monthly harness actual 2016-2024")
    table["silage_truth"] = np.where(table["year"] <= 2024, table["actual"], table["silage"])
    table = table[(table["year"] >= 2015) & (table["year"] <= INFO_YEAR)]
    table["nass_share"] = table["silage_truth"] / (table["silage_truth"] + table["grain"])
    return table[["state", "year", "silage_truth", "grain", "nass_share"]].reset_index(drop=True)


def cmd_shares(force: bool) -> dict:
    started = time.time()
    calls = load_calls()
    g0 = gate_sample_counts(calls)
    print(f"G0 sample counts: {'REPRODUCED' if g0['reproduced'] else 'NOT REPRODUCED'} {g0}", flush=True)
    complete = {stem: series_tasks(stem)[1] for stem in stems()}
    totals_path = CACHE / "area_totals.parquet"
    if totals_path.exists() and not force:
        totals = pd.read_parquet(totals_path)
    else:
        probs = pd.read_parquet(CACHE / "probs.parquet")
        probs["field_id"] = probs["field_id"].astype(str)
        totals = area_totals_all(calls, probs, complete)
        totals.to_parquet(totals_path, index=False)
    del calls
    detail = complete_grid(share_rows(totals))
    detail = detail[["state", "state_fips", "year", "asof", "classifier", "mask", "draws", "areas", "fields",
                     "assessable_areas", "assessable_share", "share", "share_se", "share_calls",
                     "share_calls_se", "corn_acres_w", "mask_acres_w", "median_peak_doy", "median_cut_doy",
                     "status"]]
    detail.to_csv(OUT / "shares_detail.csv", index=False, lineterminator="\n", float_format="%.6g")
    for pool, name in (("1+2", "shares.csv"), ("1", "shares_draw1.csv")):
        part = detail[(detail["draws"] == pool) & detail["classifier"].isin(HEADLINE_CLASSIFIERS)]
        part[SHARE_COLUMNS].to_csv(OUT / name, index=False, lineterminator="\n", float_format="%.6g")
    g3 = gate_state_table(totals, detail)
    print(f"G3 state_table: {'REPRODUCED' if g3['reproduced'] else 'NOT REPRODUCED'} {g3}", flush=True)
    changes = change_rows(totals, detail)
    truth = truth_table()
    nass = truth.assign(d_log_nass=truth.groupby("state")["silage_truth"].transform(lambda s: np.log(s).diff()))
    changes = changes.merge(nass[["state", "year", "d_log_nass"]], on=["state", "year"], how="left")
    changes.to_csv(OUT / "changes.csv", index=False, lineterminator="\n", float_format="%.6g")
    return {"G0_sample_counts": g0, "G3_state_table": g3, "shares_seconds": round(time.time() - started, 1),
            "complete_cells": int(sum(len(c) for c in complete.values())), "share_rows": int(len(detail)),
            "change_rows": int(len(changes))}


def gate_state_table(totals: pd.DataFrame, detail: pd.DataFrame) -> dict:
    """G3: kernelag.state_signal.state_table on the K0 totals (draws 1+2) gives the same rounded numbers."""
    mine = detail[(detail["classifier"] == "K0") & (detail["draws"] == "1+2")
                  & ~detail["status"].str.startswith("UNCOMPUTED")].set_index(["mask", "state_fips", "asof", "year"])
    worst, rows = 0.0, 0
    for (mask, fips, asof), group in totals.groupby(["mask", "state_fips", "asof"]):
        frame = group.rename(columns={"sl_K0": "silage_like_acres", "ca_K0": "called_silage_acres"})
        for row in state_table(frame).itertuples(index=False):
            key = (mask, fips, asof, int(row.year))
            if key not in mine.index:
                continue
            ours = mine.loc[key]
            diffs = [abs(round(ours["share"], 4) - row.sat_share), abs(round(ours["share_se"], 4) - row.share_se),
                     abs(round(ours["share_calls"], 4) - row.sat_share_calls),
                     abs(round(ours["assessable_share"], 3) - row.assessable_share),
                     abs(ours["areas"] - row.areas), abs(ours["fields"] - row.fields)]
            worst, rows = max(worst, max(diffs)), rows + 1
    return {"rows_compared": rows, "max_abs_difference": float(worst), "reproduced": worst < 1e-9 and rows > 0}


# ------------------------------------------------------------------------------------------ diagnostics


def ranks(values: np.ndarray) -> np.ndarray:
    from scipy.stats import rankdata

    return rankdata(values)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def centred(matrix: np.ndarray) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return matrix - np.nanmedian(matrix, axis=0, keepdims=True)


def change_association(x: np.ndarray, y: np.ndarray) -> dict:
    """D1 on state x transition matrices: year medians removed, pooled Spearman, state bootstrap, permutation."""
    both = np.isfinite(x) & np.isfinite(y)
    x, y = np.where(both, x, np.nan), np.where(both, y, np.nan)
    cx, cy = centred(x), centred(y)
    valid = np.isfinite(cx) & np.isfinite(cy)
    n = int(valid.sum())
    if n < 5:
        return {"n": n, "rho": np.nan}
    rho = spearman(cx[valid], cy[valid])
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(BOOT_DRAWS):
        pick = rng.integers(0, x.shape[0], x.shape[0])
        bx, by = centred(x[pick]), centred(y[pick])
        ok = np.isfinite(bx) & np.isfinite(by)
        if ok.sum() >= 5:
            boots.append(spearman(bx[ok], by[ok]))
    boots = np.array(boots)
    rx, ry = ranks(cx[valid]), ranks(cy[valid])
    columns = np.nonzero(valid)[1]
    perm_rng = np.random.default_rng(SEED)
    permuted = np.tile(np.arange(n), (PERMUTATIONS, 1))
    for column in np.unique(columns):
        idx = np.nonzero(columns == column)[0]
        permuted[:, idx] = perm_rng.permuted(np.tile(idx, (PERMUTATIONS, 1)), axis=1)
    px = rx[permuted]
    px = px - px.mean(axis=1, keepdims=True)
    ryc = ry - ry.mean()
    rho_perm = (px @ ryc) / (np.sqrt((px ** 2).sum(axis=1)) * np.sqrt((ryc ** 2).sum()))
    p_value = (1 + int((np.abs(rho_perm) >= abs(rho) - 1e-12).sum())) / (1 + PERMUTATIONS)
    return {"n": n, "rho": rho, "ci90_lo": float(np.quantile(boots, 0.05)), "ci90_hi": float(np.quantile(boots, 0.95)),
            "ci95_lo": float(np.quantile(boots, 0.025)), "ci95_hi": float(np.quantile(boots, 0.975)),
            "ci975_lo": float(np.quantile(boots, 0.0125)), "ci975_hi": float(np.quantile(boots, 0.9875)),
            "p_perm": p_value, "sign_agree": int((np.sign(cx[valid]) == np.sign(cy[valid])).sum())}


def matrices(frame: pd.DataFrame, years: tuple[int, ...], x: str, y: str) -> tuple[np.ndarray, np.ndarray]:
    states = sorted(STATES.values())
    wide_x = frame.pivot_table(index="state", columns="year", values=x).reindex(index=states, columns=list(years))
    wide_y = frame.pivot_table(index="state", columns="year", values=y).reindex(index=states, columns=list(years))
    return wide_x.to_numpy(float), wide_y.to_numpy(float)


def diag_change(changes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["classifier", "mask", "asof", "draws"]
    for key, group in changes.groupby(keys):
        info = dict(zip(keys, key))
        windows = {"main": WINDOWS[info["mask"]], "common_2018_2024": COMMON_WINDOW,
                   "no_2018": tuple(t for t in WINDOWS[info["mask"]] if t != 2018), "info_2025": (INFO_YEAR,)}
        for window, years in windows.items():
            x, y = matrices(group, years, "d_log_share", "d_log_nass")
            result = change_association(x, y)
            rows.append({**info, "window": window, "first_t": years[0], "last_t": years[-1], **result})
    order = {a: i for i, a in enumerate(ASOFS)}
    table = pd.DataFrame(rows)
    table["reading"] = np.where(table["window"].eq("main") & table["asof"].eq("nov") & table["draws"].eq("1+2"),
                                np.where(table["ci90_lo"] > 0, "present", "not shown"), "")
    return table.sort_values(["window", "draws", "classifier", "mask", "asof"],
                             key=lambda s: s.map(order) if s.name == "asof" else s).reset_index(drop=True)


def diag_earlier(changes: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """D1 on the earlier round's shares (draw 1, CDL, K0) next to this study's on the same transitions 2020-2024."""
    years = tuple(range(2020, 2025))
    nass = truth.assign(d_log_nass=truth.groupby("state")["silage_truth"].transform(lambda s: np.log(s).diff()))
    rows = []
    for asof in ("sep", "oct", "nov"):
        path = EARLIER / f"state_satellite_asof_{asof}.csv"
        if not path.exists():
            rows.append({"source": "earlier_round", "asof": asof, "rho": np.nan,
                         "note": f"UNCOMPUTED: {path.name} absent"})
            continue
        earlier = pd.read_csv(path).sort_values(["state", "year"])
        earlier["d_log_share"] = earlier.groupby("state")["sat_share"].transform(lambda s: np.log(s).diff())
        earlier = earlier.merge(nass[["state", "year", "d_log_nass"]], on=["state", "year"], how="left")
        rows.append({"source": "earlier_round (signal, draw 1, CDL, K0)", "asof": asof,
                     **change_association(*matrices(earlier, years, "d_log_share", "d_log_nass"))})
        for pool in POOLS:
            part = changes[(changes["classifier"] == "K0") & (changes["mask"] == "CDL") & (changes["asof"] == asof)
                           & (changes["draws"] == pool)]
            rows.append({"source": f"this study (draws {pool}, CDL, K0)", "asof": asof,
                         **change_association(*matrices(part, years, "d_log_share", "d_log_nass"))})
    return pd.DataFrame(rows)


def earlier_share_check(detail: pd.DataFrame) -> dict:
    """Information: this study's draw-1 CDL K0 shares against the earlier round's (2019-2025)."""
    out = {}
    for asof in ("sep", "oct", "nov"):
        path = EARLIER / f"state_satellite_asof_{asof}.csv"
        if not path.exists():
            out[asof] = "UNCOMPUTED: earlier file absent"
            continue
        earlier = pd.read_csv(path)[["state", "year", "sat_share"]]
        mine = detail[(detail["classifier"] == "K0") & (detail["mask"] == "CDL") & (detail["draws"] == "1")
                      & (detail["asof"] == asof)][["state", "year", "share"]]
        joined = earlier.merge(mine, on=["state", "year"]).dropna()
        diff = (joined["share"] - joined["sat_share"]).abs()
        out[asof] = {"n": int(len(joined)), "pearson": float(joined["share"].corr(joined["sat_share"])),
                     "median_abs_diff": float(diff.median()), "max_abs_diff": float(diff.max())}
    return out


def diag_snr(changes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_state, summary = [], []
    keys = ["classifier", "mask", "asof", "draws"]
    for key, group in changes.groupby(keys):
        info = dict(zip(keys, key))
        for window, years in {"main": WINDOWS[info["mask"]], "common_2018_2024": COMMON_WINDOW}.items():
            part = group[group["year"].isin(years)]
            rows = []
            for state, s in part.groupby("state"):
                s = s.dropna(subset=["d_log_share", "se_d_log_share"])
                if len(s) < 3:
                    continue
                rms = float(np.sqrt((s["se_d_log_share"] ** 2).mean()))
                rms_share = float(np.sqrt((s["se_d_share"] ** 2).mean()))
                nass = s["d_log_nass"].dropna()
                rows.append({**info, "window": window, "state": state, "n": len(s),
                             "sd_d_log_share": float(s["d_log_share"].std(ddof=1)), "rms_se_d_log_share": rms,
                             "sd_d_share": float(s["d_share"].std(ddof=1)), "rms_se_d_share": rms_share,
                             "sd_d_log_nass": float(nass.std(ddof=1)) if len(nass) > 2 else np.nan,
                             "snr": float(s["d_log_share"].std(ddof=1)) / rms,
                             "snr_share": float(s["d_share"].std(ddof=1)) / rms_share,
                             "nass_snr": (float(nass.std(ddof=1)) / rms) if len(nass) > 2 else np.nan})
            if not rows:
                continue
            frame = pd.DataFrame(rows)
            by_state.extend(rows)
            summary.append({**info, "window": window, "states": len(frame),
                            "median_rms_se_d_log_share": frame["rms_se_d_log_share"].median(),
                            "median_sd_d_log_share": frame["sd_d_log_share"].median(),
                            "median_sd_d_log_nass": frame["sd_d_log_nass"].median(),
                            "snr_median": frame["snr"].median(), "snr_min": frame["snr"].min(),
                            "snr_max": frame["snr"].max(), "snr_share_median": frame["snr_share"].median(),
                            "snr_share_min": frame["snr_share"].min(), "snr_share_max": frame["snr_share"].max(),
                            "nass_snr_median": frame["nass_snr"].median(), "nass_snr_min": frame["nass_snr"].min(),
                            "nass_snr_max": frame["nass_snr"].max()})
    return pd.DataFrame(summary), pd.DataFrame(by_state)


def diag_ratio(detail: pd.DataFrame, truth: pd.DataFrame,
               ratio_years: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ratio_years = ratio_years or RATIO_YEARS
    table = detail[~detail["status"].str.startswith("UNCOMPUTED")].merge(truth, on=["state", "year"], how="inner")
    table["ratio"] = table["share"] / table["nass_share"]
    table["ratio_calls"] = table["share_calls"] / table["nass_share"]
    summary, by_state, by_year = [], [], []
    keys = ["classifier", "mask", "asof", "draws"]
    for key, group in table.groupby(keys):
        info = dict(zip(keys, key))
        part = group[group["year"].isin(ratio_years[info["mask"]])]
        row = {**info, "first_year": ratio_years[info["mask"]][0], "last_year": ratio_years[info["mask"]][-1]}
        for column in ("ratio", "ratio_calls"):
            stats = part.groupby("state")[column].agg(
                mean="mean", sd_log=lambda s: float(np.log(s).std(ddof=1)), swing=lambda s: float(s.max() - s.min()))
            for state, s in stats.iterrows():
                by_state.append({**info, "measure": column, "state": state, **s.to_dict()})
            year_effect = part.groupby("year")[column].apply(lambda s: float(np.log(s).median()))
            for year, value in year_effect.items():
                by_year.append({**info, "measure": column, "year": int(year), "median_log_ratio": value})
            row.update({f"{column}_mean_median": stats["mean"].median(),
                        f"{column}_sd_log_median": stats["sd_log"].median(),
                        f"{column}_sd_log_max": stats["sd_log"].max(),
                        f"{column}_swing_median": stats["swing"].median(),
                        f"{column}_year_effect_sd": float(year_effect.std(ddof=1))})
        summary.append(row)
    return pd.DataFrame(summary), pd.DataFrame(by_state), pd.DataFrame(by_year)


def diag_level(detail: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    table = detail[~detail["status"].str.startswith("UNCOMPUTED")].merge(truth, on=["state", "year"], how="inner")
    rows = []
    keys = ["classifier", "mask", "asof", "draws"]
    for key, group in table.groupby(keys):
        info = dict(zip(keys, key))
        means = group[group["year"].isin(RATIO_YEARS[info["mask"]])].groupby("state")[["share", "nass_share"]].mean()
        slope, intercept = np.polyfit(means["nass_share"], means["share"], 1)
        rows.append({**info, "states": len(means), "spearman": spearman(means["share"].to_numpy(),
                                                                         means["nass_share"].to_numpy()),
                     "pearson": float(means["share"].corr(means["nass_share"])),
                     "intercept": float(intercept), "slope": float(slope)})
    return pd.DataFrame(rows)


def diag_assessable(detail: pd.DataFrame) -> pd.DataFrame:
    part = detail[(detail["classifier"] == "K0") & ~detail["status"].str.startswith("UNCOMPUTED")]
    part = part[part["year"] <= 2025]
    rows = []
    for (mask, asof, pool), group in part.groupby(["mask", "asof", "draws"]):
        rows.append({"mask": mask, "asof": asof, "draws": pool, "state_years": len(group),
                     "assessable_share_median": group["assessable_share"].median(),
                     "assessable_share_p10": group["assessable_share"].quantile(0.10),
                     "fallback_state_years": int(group["status"].str.startswith("fallback").sum()),
                     "median_cut_doy": group["median_cut_doy"].median()})
    return pd.DataFrame(rows)


def cmd_diag() -> dict:
    detail = pd.read_csv(OUT / "shares_detail.csv", dtype={"state_fips": str})
    changes = pd.read_csv(OUT / "changes.csv", dtype={"state_fips": str})
    truth = truth_table()
    change = diag_change(changes)
    change.to_csv(OUT / "diag_change.csv", index=False, lineterminator="\n", float_format="%.4f")
    diag_earlier(changes, truth).to_csv(OUT / "diag_change_earlier_round.csv", index=False, lineterminator="\n",
                                        float_format="%.4f")
    snr, snr_state = diag_snr(changes)
    snr.to_csv(OUT / "diag_snr.csv", index=False, lineterminator="\n", float_format="%.4f")
    snr_state.to_csv(OUT / "diag_snr_by_state.csv", index=False, lineterminator="\n", float_format="%.4f")
    ratio, ratio_state, ratio_year = diag_ratio(detail, truth)
    ratio.to_csv(OUT / "diag_ratio.csv", index=False, lineterminator="\n", float_format="%.4f")
    ratio_state.to_csv(OUT / "diag_ratio_by_state.csv", index=False, lineterminator="\n", float_format="%.4f")
    ratio_year.to_csv(OUT / "diag_ratio_by_year.csv", index=False, lineterminator="\n", float_format="%.4f")
    diag_level(detail, truth).to_csv(OUT / "diag_level.csv", index=False, lineterminator="\n", float_format="%.4f")
    diag_assessable(detail).to_csv(OUT / "diag_assessable.csv", index=False, lineterminator="\n",
                                   float_format="%.4f")
    head = change[(change["window"] == "main") & (change["draws"] == "1+2")]
    pd.set_option("display.width", 250)
    print(head[["classifier", "mask", "asof", "n", "rho", "ci90_lo", "ci90_hi", "p_perm", "sign_agree",
                "reading"]].to_string(index=False))
    extra_diagnostics(detail, truth, snr_state)
    return {"earlier_share_check": earlier_share_check(detail)}


def extra_diagnostics(detail: pd.DataFrame, truth: pd.DataFrame, snr_state: pd.DataFrame) -> None:
    """NOT pre-registered (added after the first diag run; information only, nothing selected).

    extra_dilution.csv: per state, dilution = b x mean NASS share / mean share (b = D4 cross-state slope), the
        factor by which a change in ln NASS silage share moves ln share if share = a + b x NASS share; and
        expected_snr = dilution x nass_snr (D2), the earlier round's "expected SNR".
    extra_ratio_2017_2024.csv: D3 with CDL on the same years as P (2017-2024), for a like-for-like mask comparison.
    """
    level = diag_level(detail, truth)
    table = detail[~detail["status"].str.startswith("UNCOMPUTED")].merge(truth, on=["state", "year"], how="inner")
    keys = ["classifier", "mask", "asof", "draws"]
    rows = []
    for key, group in table.groupby(keys):
        info = dict(zip(keys, key))
        slope = level.set_index(keys).loc[key, "slope"]
        means = group[group["year"].isin(RATIO_YEARS[info["mask"]])].groupby("state")[["share", "nass_share"]].mean()
        snr = snr_state[(snr_state[keys] == pd.Series(info)).all(axis=1) & (snr_state["window"] == "main")]
        snr = snr.set_index("state")["nass_snr"]
        for state, m in means.iterrows():
            dilution = float(slope * m["nass_share"] / m["share"])
            rows.append({**info, "state": state, "slope": float(slope), "mean_share": m["share"],
                         "mean_nass_share": m["nass_share"], "dilution": dilution,
                         "nass_snr": snr.get(state, np.nan), "expected_snr": dilution * snr.get(state, np.nan)})
    pd.DataFrame(rows).to_csv(OUT / "extra_dilution.csv", index=False, lineterminator="\n", float_format="%.4f")
    common = {mask: tuple(range(2017, 2025)) for mask in MASKS}
    diag_ratio(detail, truth, common)[0].to_csv(OUT / "extra_ratio_2017_2024.csv", index=False, lineterminator="\n",
                                               float_format="%.4f")


# ------------------------------------------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["prereg", "features", "probs", "shares", "diag", "all"])
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.workers > 20:
        parser.error("at most 20 workers")
    if args.step == "prereg":
        cmd_prereg()
        return
    digest = check_prereg()
    OUT.mkdir(parents=True, exist_ok=True)
    run_path, gates_path = OUT / "run.json", OUT / "gates.json"
    run = json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else {}
    gates = json.loads(gates_path.read_text(encoding="utf-8")) if gates_path.exists() else {}
    run.update({"preregistration_sha256": digest, "updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})
    steps = ["features", "probs", "shares", "diag"] if args.step == "all" else [args.step]
    for step in steps:
        if step == "features":
            run["features"] = cmd_features(args.workers, args.force)
        elif step == "probs":
            result = cmd_probs(args.workers, args.force)
            gates.update({k: result[k] for k in ("G1_K0", "G2_K1")})
            run["probs"] = {k: v for k, v in result.items() if k not in ("G1_K0", "G2_K1")}
        elif step == "shares":
            result = cmd_shares(args.force)
            gates.update({k: result[k] for k in ("G0_sample_counts", "G3_state_table")})
            run["shares"] = {k: v for k, v in result.items() if not k.startswith("G")}
        else:
            gates.update(cmd_diag())
        run_path.write_text(json.dumps(run, indent=1, default=str), encoding="utf-8", newline="\n")
        gates_path.write_text(json.dumps(gates, indent=1, default=str), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
