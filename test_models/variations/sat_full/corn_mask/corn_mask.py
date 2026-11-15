"""Corn from imagery for every candidate field-year 2016-2026 (no CDL at prediction time), README section 1.

Implements the pre-registered design in README.md section 1 (hash in out/preregistration.sha256):
    features  corn26.corn_features per field-year at 15 Jul..15 Dec, cached in out/cache/features_<asof>.parquet
    fit       corn26 classifier, regimes P (prior years, headline) and L (leave-one-year-out, upper bound)
    report    metrics per regime x pool x date x year x state, summaries, failures, 2026 state tallies

Run from the repository root (each step skips work whose cache exists unless --force):
    .venv/Scripts/python.exe test_models/variations/sat_full/corn_mask/corn_mask.py all --workers 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CORN26_DIR = ROOT / "test_models" / "ownModels" / "satellite" / "corn26"
for _path in (ROOT, CORN26_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from kernelag.context import ASOF_MONTH  # noqa: E402

# README 1.2: series_asof and corn26.features_for read this dict; jul/dec are added at run time, in-process only.
ASOF_MONTH.setdefault("jul", 7)
ASOF_MONTH.setdefault("dec", 12)

import corn26  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402
from kernelag.state_signal import complete_areas  # noqa: E402

OUT = HERE / "out"
CACHE = OUT / "cache"
ASOFS = ("jul", "aug", "sep", "oct", "nov", "dec")
KINDS = ("candes", "candpc", "candpc16")            # candes/candpc share field ids; candpc16 is another edition
EDITION = {"candes": "e2018", "candpc": "e2018", "candpc16": "e2015"}
LABEL_YEARS = tuple(range(2016, 2026))
TARGET_YEAR = 2026
HEADLINE_YEARS = tuple(range(2017, 2025))
INFO_YEAR = 2025
RATIO_BAND = (0.90, 1.10)
MIN_PRECISION = MIN_RECALL = 0.70
THRESHOLD = corn26.CORN_THRESHOLD
SAMPLE_COLUMNS = ["field_id", "year", "cell", "cell_size_acres", "state_fips", "county_fips", "acres", "draw",
                  "is_corn"]
KEYS = ["stem", "field_id", "year"]
PREREG_START, PREREG_END = "## 1. Pre-registration", "<!-- end of pre-registration -->"
UNCOMPUTED_2016_P = "UNCOMPUTED: no prior year"
UNCOMPUTED_2026_DEC = "UNCOMPUTED: 15 Dec 2026 is in the future"


# ------------------------------------------------------------------------------------------ housekeeping

def preregistration_status() -> dict:
    text = (HERE / "README.md").read_text(encoding="utf-8")
    section = text[text.index(PREREG_START):text.index(PREREG_END) + len(PREREG_END)]
    now = hashlib.sha256(section.encode("utf-8")).hexdigest()
    stored = (OUT / "preregistration.sha256").read_text(encoding="utf-8").split()[0]
    return {"sha256_now": now, "sha256_stored": stored, "unchanged": now == stored}


def roster() -> pd.DataFrame:
    """state, state_fips for the sampled states that have all three candidate files."""
    states = corn26.states()
    have = states["state_fips"].map(lambda f: all((data_dir() / "samples" / f"{k}_{f}.parquet").exists()
                                                  for k in KINDS))
    return states[have].reset_index(drop=True)


def stems() -> list[str]:
    return [f"{kind}_{fips}" for fips in roster()["state_fips"] for kind in KINDS]


def write_csv(frame: pd.DataFrame, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


# ------------------------------------------------------------------------------------------ candidates

def read_candidates(stem: str) -> tuple[pd.DataFrame, dict]:
    """One candidate file without geometry, text ids, restricted to complete areas (README 1.1)."""
    table = pd.read_parquet(data_dir() / "samples" / f"{stem}.parquet", columns=SAMPLE_COLUMNS)
    for column in ["field_id", "cell", "state_fips", "county_fips"]:
        table[column] = table[column].astype(str)
    table["state_fips"] = table["state_fips"].str.zfill(2)
    if table.duplicated(["field_id", "year"]).any():
        raise ValueError(f"{stem}: duplicate field-year")
    areas = set(complete_areas(table, data_dir() / "s2_series" / stem))
    info = {"stem": stem, "rows": len(table), "areas": int(table["cell"].nunique()), "complete_areas": len(areas)}
    table = table[table["cell"].isin(areas)].reset_index(drop=True)
    info["rows_kept"] = len(table)
    table.insert(0, "stem", stem)
    table["edition"] = EDITION[stem.split("_")[0]]
    return table, info


def add_history(table: pd.DataFrame) -> pd.DataFrame:
    """history_corn (CDL corn in an earlier labelled year, same edition) and prev_corn_cdl (CDL corn in t-1).

    NaN where no earlier labelled year with the same field ids exists (2016, 2018).
    """
    out = []
    for _, part in table.groupby("edition"):
        wide = part.pivot_table(index=["state_fips", "field_id"], columns="year", values="is_corn",
                                aggfunc="first")
        years = sorted(part["year"].unique())
        history, previous = {}, {}
        for year in years:
            earlier = [y for y in years if y < year and y in wide.columns and wide[y].notna().any()]
            history[year] = (wide[earlier].max(axis=1) if earlier
                             else pd.Series(np.nan, index=wide.index))
            previous[year] = (wide[year - 1] if (year - 1) in earlier
                              else pd.Series(np.nan, index=wide.index))
        hist = pd.concat(history, names=["year"]).rename("history_corn").reset_index()
        prev = pd.concat(previous, names=["year"]).rename("prev_corn_cdl").reset_index()
        out.append(part.merge(hist, on=["state_fips", "field_id", "year"], how="left", validate="one_to_one")
                   .merge(prev, on=["state_fips", "field_id", "year"], how="left", validate="one_to_one"))
    return pd.concat(out, ignore_index=True)


def all_candidates(workers: int = 1) -> tuple[pd.DataFrame, list[dict]]:
    with ProcessPoolExecutor(max_workers=workers) as pool:
        parts = list(pool.map(read_candidates, stems()))
    table = pd.concat([p[0] for p in parts], ignore_index=True)
    return add_history(table), [p[1] for p in parts]


# ------------------------------------------------------------------------------------------ features

def file_features(task: tuple[str, str]) -> pd.DataFrame:
    """corn26.corn_features of one series file (one area-year) at every forecast date. Runs in a worker."""
    stem, path = task
    series = corn26.read_series_file(Path(path))
    parts = []
    for asof in ASOFS:
        features = corn26.corn_features(series, asof)
        if features.empty:
            continue
        features[corn26.CORN_FEATURES] = features[corn26.CORN_FEATURES].astype("float32")
        features["n_clear"] = features["n_clear"].astype("int16")
        features["year"] = features["year"].astype("int16")
        parts.append(features.assign(asof=asof, stem=stem))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def build_features(workers: int, force: bool) -> dict:
    paths = {asof: CACHE / f"features_{asof}.parquet" for asof in ASOFS}
    if all(p.exists() for p in paths.values()) and not force:
        return {"features": "cached"}
    started = time.time()
    tasks = [(stem, str(f)) for stem in stems() for f in sorted((data_dir() / "s2_series" / stem).glob("*.csv"))]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        frames = [f for f in pool.map(file_features, tasks, chunksize=8) if len(f)]
    features = pd.concat(frames, ignore_index=True)
    del frames
    if features.duplicated(["asof"] + KEYS).any():
        raise ValueError("duplicate field-year features")
    CACHE.mkdir(parents=True, exist_ok=True)
    for asof, part in features.groupby("asof"):
        part.drop(columns="asof").reset_index(drop=True).to_parquet(paths[asof], index=False, compression="zstd")
    info = {"series_files": len(tasks), "feature_rows": int(len(features)),
            "feature_seconds": round(time.time() - started)}
    print(f"features: {info}", flush=True)
    return info


# ------------------------------------------------------------------------------------------ fitting

def fit_asof(task: tuple[str, int, pd.DataFrame]) -> tuple[pd.DataFrame, list[dict]]:
    """Regimes P, L and P_alt at one forecast date (README 1.5). Runs in a worker with ``threads`` threads."""
    from threadpoolctl import threadpool_limits

    asof, threads, candidates = task
    features = pd.read_parquet(CACHE / f"features_{asof}.parquet")
    features["year"] = features["year"].astype(int)
    table = candidates.merge(features, on=KEYS, how="left", validate="one_to_one")
    table["n_clear"] = table["n_clear"].fillna(0).astype(int)
    names = corn26.features_for(asof)
    year = table["year"].to_numpy()
    labelled = np.isin(year, LABEL_YEARS) & table["is_corn"].notna().to_numpy()
    out = {c: np.full(len(table), np.nan) for c in ["p_corn_P", "p_corn_L", "p_corn_P_alt"]}
    log = []

    def run(column: str, train: np.ndarray, test: np.ndarray, label: str) -> None:
        tic = time.time()
        model = corn26.fit_classifier(table[train], names)
        out[column][test] = corn26.p_corn(model, table[test])
        log.append({"asof": asof, "fit": label, "train_rows": int(train.sum()), "test_rows": int(test.sum()),
                    "train_corn_share": round(float(table.loc[train, "is_corn"].mean()), 4),
                    "features": len(model.features_), "seconds": round(time.time() - tic, 1)})
        print(f"  {asof} {label}: train {int(train.sum())} test {int(test.sum())} "
              f"{time.time() - tic:.0f}s", flush=True)

    with threadpool_limits(limits=threads):
        for t in LABEL_YEARS[1:]:
            run("p_corn_P", labelled & (year < t), year == t, f"P_{t}")
        for t in LABEL_YEARS:
            run("p_corn_L", labelled & (year != t), year == t, f"L_{t}")
        if asof != "dec":                                   # README 1.2: Dec 15 2026 is in the future
            run("p_corn_L", labelled, year == TARGET_YEAR, f"PL_{TARGET_YEAR}")
            out["p_corn_P"][year == TARGET_YEAR] = out["p_corn_L"][year == TARGET_YEAR]
        run("p_corn_P_alt", labelled & (year == 2017), year == 2016, "P_alt_2016_from_2017")
    calls = table[KEYS + ["n_clear"]].copy()
    for column, values in out.items():
        calls[column] = np.round(values, 4).astype("float32")
    calls["asof"] = asof
    return calls, log


def fit_all(candidates: pd.DataFrame, workers: int, force: bool) -> dict:
    path = OUT / "corn_calls.parquet"
    if path.exists() and not force:
        return {"fit": "cached"}
    started = time.time()
    keep = candidates[KEYS + ["is_corn"]]
    parallel = min(len(ASOFS), workers)
    threads = max(1, workers // parallel)
    with ProcessPoolExecutor(max_workers=parallel) as pool:
        results = list(pool.map(fit_asof, [(asof, threads, keep) for asof in ASOFS]))
    calls = pd.concat([r[0] for r in results], ignore_index=True)
    log = [row for r in results for row in r[1]]
    calls = calls.merge(candidates, on=KEYS, how="left", validate="many_to_one")
    for regime in ("P", "L"):
        p = calls[f"p_corn_{regime}"]
        calls[f"is_corn_{regime}"] = (p >= THRESHOLD).astype("Int8").where(p.notna())
    calls["is_corn_cdl"] = calls["is_corn"].astype("Int8")
    calls["asof"] = pd.Categorical(calls["asof"], categories=list(ASOFS), ordered=True)
    columns = ["stem", "state_fips", "cell", "field_id", "year", "asof", "p_corn_P", "is_corn_P", "p_corn_L",
               "is_corn_L", "is_corn_cdl", "acres", "cell_size_acres", "county_fips", "draw", "n_clear",
               "history_corn", "prev_corn_cdl", "p_corn_P_alt"]
    calls = calls[columns].sort_values(["asof", "stem", "year", "cell", "field_id"]).reset_index(drop=True)
    calls["year"] = calls["year"].astype("int16")
    for column in ["history_corn", "prev_corn_cdl"]:
        calls[column] = calls[column].astype("Int8")
    calls.to_parquet(path, index=False, compression="zstd")
    write_csv(pd.DataFrame(log), "fit_log.csv")
    info = {"calls_rows": int(len(calls)), "fits": len(log), "fit_seconds": round(time.time() - started),
            "threads_per_fit": threads, "parallel_dates": parallel}
    print(f"fit: {info}", flush=True)
    return info


# ------------------------------------------------------------------------------------------ report

def metric_rows(calls: pd.DataFrame, names: dict) -> pd.DataFrame:
    """corn26.call_metrics per regime x pool x asof x year x state (and ALL 15 states). README 1.6."""
    scored = calls[calls["year"].isin(LABEL_YEARS)].copy()
    scored["is_corn"] = scored["is_corn_cdl"].astype(int)
    regimes = {"P": "p_corn_P", "L": "p_corn_L", "P_alt": "p_corn_P_alt"}
    rows = []
    for pool in ("all", "history"):
        frame = scored if pool == "all" else scored[scored["history_corn"] == 1]
        for asof, by_asof in frame.groupby("asof", observed=True, sort=False):
            jobs = list(regimes.items())
            if asof == "nov":           # B0 is date-independent: computed once, reported under asof "any"
                jobs.append(("B0", "prev_corn_cdl"))
            for regime, column in jobs:
                part = by_asof[by_asof[column].notna()].copy()
                part[column] = part[column].astype(float)
                for year, by_year in part.groupby("year"):
                    groups = [("ALL", by_year)] + list(by_year.groupby("state_fips"))
                    for fips, group in groups:
                        rows.append({"regime": regime, "pool": pool, "asof": "any" if regime == "B0" else asof,
                                     "year": int(year), "state_fips": fips,
                                     "state": names.get(fips, "ALL 15 STATES"),
                                     **corn26.call_metrics(group, column)})
    table = pd.DataFrame(rows)
    ratio = table["corn_acre_ratio"]
    table["flag_ratio"] = ~ratio.between(*RATIO_BAND)
    table["flag_recall"] = table["recall"] < MIN_RECALL
    table["flag_precision"] = table["precision"] < MIN_PRECISION
    table["flagged"] = table[["flag_ratio", "flag_recall", "flag_precision"]].any(axis=1)
    return table


def headline(metrics: pd.DataFrame) -> pd.DataFrame:
    """Per regime x pool x asof x state: 2017-2024 means and failure status, plus 2025 information."""
    rows = []
    for key, part in metrics.groupby(["regime", "pool", "asof", "state_fips", "state"], sort=False):
        years = part[part["year"].isin(HEADLINE_YEARS)]
        info = part[part["year"] == INFO_YEAR]
        row = dict(zip(["regime", "pool", "asof", "state_fips", "state"], key))
        if years.empty:
            row["note"] = "no scored year 2017-2024"
            rows.append(row)
            continue
        deviation = (years["corn_acre_ratio"] - 1).abs()
        row.update({
            "years": len(years), "precision_mean": years["precision"].mean(), "recall_mean": years["recall"].mean(),
            "acre_ratio_mean": years["corn_acre_ratio"].mean(), "abs_ratio_dev_median": deviation.median(),
            "abs_ratio_dev_max": deviation.max(), "flagged_years": int(years["flagged"].sum()),
            "fails": bool(years["flagged"].sum() >= len(years) / 2),
            "flagged_year_list": " ".join(str(y) for y in years.loc[years["flagged"], "year"]),
            "precision_2025": info["precision"].mean() if len(info) else np.nan,
            "recall_2025": info["recall"].mean() if len(info) else np.nan,
            "acre_ratio_2025": info["corn_acre_ratio"].mean() if len(info) else np.nan,
        })
        rows.append(row)
    return pd.DataFrame(rows).round(4)


def gap_table(summary: pd.DataFrame) -> pd.DataFrame:
    """P minus L, per pool x asof x state, on the 2017-2024 headline means."""
    cols = ["precision_mean", "recall_mean", "abs_ratio_dev_median"]
    keys = ["pool", "asof", "state_fips", "state"]
    p = summary[summary["regime"] == "P"].set_index(keys)[cols]
    lo = summary[summary["regime"] == "L"].set_index(keys)[cols]
    gap = (p - lo).add_suffix("_P_minus_L")
    return gap.join(p.add_suffix("_P")).join(lo.add_suffix("_L")).reset_index().round(4)


def calls_2026(calls: pd.DataFrame, names: dict) -> pd.DataFrame:
    """2026 sample corn acres (PPS-weighted) by state and date, next to 2025 truth and 2025 P calls."""
    rows = []
    weight = calls["acres"] / calls["cell_size_acres"]
    calls = calls.assign(w=weight)
    planted = corn26.nass_planted()
    for (asof, fips), part in calls[calls["year"].isin([INFO_YEAR, TARGET_YEAR])].groupby(
            ["asof", "state_fips"], observed=True):
        now, last = part[part["year"] == TARGET_YEAR], part[part["year"] == INFO_YEAR]
        computed = now["p_corn_P"].notna().any()
        pred26 = float((now["w"] * now["is_corn_P"].fillna(0)).sum()) if computed else np.nan
        true25 = float((last["w"] * last["is_corn_cdl"]).sum())
        pred25 = float((last["w"] * last["is_corn_P"].fillna(0)).sum())
        rows.append({
            "asof": asof, "state_fips": fips, "state": names[fips], "candidates_2026": len(now),
            "called_corn_2026": int(now["is_corn_P"].sum()) if computed else np.nan,
            "no_clear_look_2026": int((now["n_clear"] == 0).sum()),
            "weighted_pred_corn_2026": pred26, "weighted_true_corn_2025": true25,
            "weighted_P_pred_corn_2025": pred25,
            "ratio_pred26_to_true25": pred26 / true25 if true25 else np.nan,
            "ratio_pred26_to_pred25": pred26 / pred25 if pred25 else np.nan,
            "history_share_2026": float(now["history_corn"].eq(1).fillna(False).mean()),
            "note": "" if computed else UNCOMPUTED_2026_DEC,
        })
    table = pd.DataFrame(rows)
    table = table.merge(planted.reset_index(names="state_fips"), on="state_fips", how="left")
    table["nass_planted_ratio_2026sep_to_2025"] = table["nass_planted_2026_sep"] / table["nass_planted_2025_final"]
    return table.round(4)


def report() -> dict:
    calls = pd.read_parquet(OUT / "corn_calls.parquet")
    calls["asof"] = calls["asof"].astype(str)
    names = dict(zip(roster()["state_fips"], roster()["state"]))
    metrics = metric_rows(calls, names)
    write_csv(metrics.round(4), "metrics_by_state_year.csv")
    write_csv(metrics[metrics["state_fips"] == "ALL"].round(4), "summary_by_year.csv")
    summary = headline(metrics)
    write_csv(summary, "summary_headline.csv")
    write_csv(gap_table(summary), "gap_P_minus_L.csv")
    flagged = metrics[metrics["flagged"] & metrics["regime"].isin(["P", "L"]) & (metrics["state_fips"] != "ALL")]
    write_csv(flagged[["regime", "pool", "asof", "year", "state_fips", "state", "precision", "recall",
                       "corn_acre_ratio", "flag_ratio", "flag_recall", "flag_precision"]].round(4), "failures.csv")
    write_csv(calls_2026(calls, names), "calls_2026_by_state.csv")
    return {"metric_rows": len(metrics), "flagged_rows_P_L": len(flagged)}


# ------------------------------------------------------------------------------------------ main

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["features", "fit", "report", "all"])
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.workers > 20:
        parser.error("at most 20 workers")
    prereg = preregistration_status()
    if not prereg["unchanged"]:
        raise SystemExit(f"pre-registration changed since it was hashed: {prereg}")
    started = time.time()
    run_path = OUT / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else {}
    run.update({"generated_by": "test_models/variations/sat_full/corn_mask/corn_mask.py",
                "preregistration": prereg, "asofs": list(ASOFS), "classifier_settings": corn26.CLASSIFIER_SETTINGS,
                "threshold": THRESHOLD, "corn_features": corn26.CORN_FEATURES, "min_valid": corn26.MIN_VALID,
                "uncomputed": {"P_2016": UNCOMPUTED_2016_P, "2026_dec": UNCOMPUTED_2026_DEC}})
    if args.step in ("features", "all"):
        run["features_step"] = build_features(args.workers, args.force)
    if args.step in ("fit", "all"):
        candidates, info = all_candidates(min(args.workers, 15))
        run["candidates"] = {"rows": int(len(candidates)), "by_year": candidates.groupby("year").size().to_dict(),
                             "areas_dropped_incomplete": int(sum(i["areas"] - i["complete_areas"] for i in info)),
                             "rows_dropped_incomplete": int(sum(i["rows"] - i["rows_kept"] for i in info))}
        run["fit_step"] = fit_all(candidates, args.workers, args.force)
    if args.step in ("report", "all"):
        run["report_step"] = report()
    run["seconds_last_step"] = round(time.time() - started)
    OUT.mkdir(parents=True, exist_ok=True)
    run_path.write_text(json.dumps(run, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"done in {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
