"""Month-by-month backtest (15 Jul to 15 Dec) of the four selected state models and their benchmarks.

The four models are FIXED: their own run.py files are imported and called unchanged. Only the as-of mapping is
widened in memory, from 15 Sep / 15 Oct / 15 Nov to six dates (the 15th of July to December):
    - kernelag.context.ASOF_MONTH gains "jul" (7) and "dec" (12); "aug" to "nov" keep their months. Every cut-off
      that reads it (Drought Monitor maps, NASS condition weeks, RMA loss months, NASS report months in
      kernelag.state_panel.public_by, NASS yield-forecast months) then works for the new dates.
    - each model module's ASOF dict (and Tier B silage's own ASOF_MONTH) is replaced in place by the six dates.
No file of the four model folders, of kernelag or of data/ is written.

Models (selected by each folder's pre-registered rule; not re-selected here):
    grain  Tier A  g3_fsa_ratio_multi                 test_models/ownModels/grain/run.py
    grain  Tier B  b7_blend_b5_fsa_level              test_models/ownModels/tierB/grain/run.py
    silage Tier A  s3_fsa_residual                    test_models/ownModels/silage/run.py
    silage Tier B  c5b_residual_fsa_planted_pre_june  test_models/ownModels/tierB/silage/run.py
Benchmarks:
    grain   nass_latest: NASS's latest harvested-for-grain forecast published by the date (June Acreage for 15 Jul;
            Aug/Sep/Oct/Nov Crop Production; 15 Dec = November's), the incumbent's rule as rebuilt in the grain
            folder (grain_run.nass_benchmark). June 2013 is missing from Quick Stats, so its state grain forecasts
            are parsed here from the archived June 2013 Acreage report text (benchmark only).
            g0_persistence: last year's NASS final.
    silage  reversion_only_report_H13 (the report model, NASS finals from 2013, 2017-2024 only),
            reversion_only_H00 (same algorithm on finals from 2000 = Tier A's s1), s0_persistence. All date-free.

FSA: data/fsa/fsa_files.csv with the corrected publication dates (kernelag.fsa.usable_files / latest_file).
A model with no current-year FSA file by the date runs its own fallback path; that year-cell is labelled
"fallback" (fallback_share in the summary = share of years in which that happened).

Outputs (out/): monthly_summary.csv, monthly_by_year.csv, monthly_by_state_year.csv, monthly_vs_nass_ci.csv,
fsa_files_used.csv, fsa_fix_before_after.csv (with --old-fsa-root), reproduction.json.

Run from the repository root:
    .venv/Scripts/python.exe test_models/ownModels/monthly/run.py --old-fsa-root <folder holding fsa/ with the
        pre-fix fsa_files.csv and fsa_corn_state.csv>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import kernelag.context as kctx  # noqa: E402

OWN = REPO / "test_models" / "ownModels"
OUT = HERE / "out"
REPORTS_DIR = OWN / "tierB" / "grain" / "data"
MODULE_PATHS = {
    "grain_a": OWN / "grain" / "run.py",
    "silage_a": OWN / "silage" / "run.py",
    "grain_b": OWN / "tierB" / "grain" / "run.py",
    "silage_b": OWN / "tierB" / "silage" / "run.py",
}
MONTHS = {"jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
ASOF = {key: (month, 15) for key, month in MONTHS.items()}
WITH_FSA = ["aug", "sep", "oct", "nov", "dec"]
AVERAGES = {"avg_jul_dec": list(MONTHS), "avg_aug_dec": WITH_FSA}
YEARS = list(range(2012, 2025))
PERIODS = {"2017-2024": (2017, 2024), "2012-2024": (2012, 2024)}
BOOT, SEED = 10_000, 20261114

MODELS = {
    "g3_fsa_ratio_multi": ("grain", "A", "grain_a"),
    "b7_blend_b5_fsa_level": ("grain", "B", "grain_b"),
    "nass_latest": ("grain", "benchmark: NASS forecast (not independent)", "grain_a"),
    "g0_persistence": ("grain", "benchmark: same as last year", "grain_a"),
    "s3_fsa_residual": ("silage", "A", "silage_a"),
    "c5b_residual_fsa_planted_pre_june": ("silage", "B", "silage_b"),
    "reversion_only_report_H13": ("silage", "benchmark: report model reversion_only", "silage_a"),
    "reversion_only_H00": ("silage", "benchmark: reversion_only on finals from 2000", "silage_a"),
    "s0_persistence": ("silage", "benchmark: same as last year", "silage_a"),
}
SELECTED = ["g3_fsa_ratio_multi", "b7_blend_b5_fsa_level", "s3_fsa_residual", "c5b_residual_fsa_planted_pre_june"]
FSA_MODELS = set(SELECTED)
# The same models under their names in each folder's out/summary.csv (for the reproduction on the old tables).
FOLDER_NAMES = {
    "g3_fsa_ratio_multi": ("grain", "g3_fsa_ratio_multi", "asof"),
    "nass_latest": ("grain", "nass_latest", "asof"),
    "g0_persistence": ("grain", "g0_persistence", "asof"),
    "b7_blend_b5_fsa_level": ("tierB/grain", "b7_blend_b5_fsa_level", "asof"),
    "s3_fsa_residual": ("silage", "s3_fsa_residual", "asof_key"),
    "reversion_only_H00": ("silage", "s1_reversion_only", "asof_key"),
    "reversion_only_report_H13": ("silage", "s1_incumbent_H13", "asof_key"),
    "s0_persistence": ("silage", "s0_persistence", "asof_key"),
    "c5b_residual_fsa_planted_pre_june": ("tierB/silage", "c5b_residual_fsa_planted_pre_june", "asof_key"),
}


# --- the four model modules, imported unchanged ------------------------------------------------------------------

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_modules() -> dict:
    return {key: load_module(f"monthly_{key}", path) for key, path in MODULE_PATHS.items()}


def patch_asof(mods: dict) -> None:
    """Widen the as-of mapping to the six month-15 dates, in memory only (see the module docstring)."""
    for key, month in MONTHS.items():
        if kctx.ASOF_MONTH.get(key, month) != month:
            raise ValueError(f"kernelag.context.ASOF_MONTH[{key}] is not {month}")
    kctx.ASOF_MONTH.update(MONTHS)
    for name, mod in mods.items():
        for key, value in mod.ASOF.items():
            if tuple(value) != ASOF[key]:
                raise ValueError(f"{name}.ASOF[{key}] = {value}, expected {ASOF[key]}")
        mod.ASOF.clear()
        mod.ASOF.update(ASOF)
    tier_b_silage = mods["silage_b"]
    tier_b_silage.ASOF_MONTH.clear()
    tier_b_silage.ASOF_MONTH.update(MONTHS)
    if mods["grain_b"].ASOF_MONTH is not kctx.ASOF_MONTH:
        raise RuntimeError("Tier B grain does not read kernelag.context.ASOF_MONTH")


def load_fsa_from(mod, root: Path | None):
    """The module's own load_fsa(), reading <root>/fsa/ instead of data/fsa/ when ``root`` is given."""
    if root is None:
        return mod.load_fsa()
    saved = mod.DATA
    mod.DATA = root
    try:
        return mod.load_fsa()
    finally:
        mod.DATA = saved


def asof_day(year: int, key: str) -> date:
    return date(year, MONTHS[key], 15)


def fsa_label(files: pd.DataFrame, zip_name: str | None, day: date) -> str | None:
    """'vintage data-date (published date)' of a used FSA file, after checking it was published by ``day``."""
    if zip_name is None or (isinstance(zip_name, float) and np.isnan(zip_name)):
        return None
    row = files[files["zip_name"] == zip_name]
    if len(row) != 1:
        raise ValueError(f"{zip_name}: {len(row)} rows in fsa_files.csv")
    row = row.iloc[0]
    if pd.Timestamp(row["assumed_published"]) > pd.Timestamp(day):
        raise RuntimeError(f"{zip_name} published {row['assumed_published']}, after {day}")
    return f"{row['vintage']} {row['data_as_of']} (published {row['assumed_published']})"


# --- NASS grain benchmark: June 2013 state forecasts from the archived report -------------------------------------

JUNE_TITLE = "Corn Area Planted for All Purposes and Harvested for Grain - States and United States"


def parse_june_grain(path: Path, year: int) -> tuple[pd.Series, float]:
    """State corn harvested-for-grain forecasts (acres) of ``year`` in a NASS June Acreage report, and the US line.

    The table has four number columns (planted t-1, planted t, harvested for grain t-1, harvested for grain t);
    the fourth is the forecast. States marked (NA) have no grain estimate."""
    lines = path.read_text(encoding="latin-1").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(JUNE_TITLE) and "...." not in line]
    if len(starts) != 1:
        raise ValueError(f"{path.name}: {len(starts)} corn planted/harvested tables")
    values, us, header = {}, None, False
    for line in lines[starts[0] + 1:]:
        if f"{year} 1/" in line:
            header = True
        label, colon, cells = line.partition(":")
        if not colon:
            continue
        name = re.sub(r"\d/", "", label).replace(".", "").strip().upper()
        tokens = cells.split()
        if not name or len(tokens) != 4:
            continue
        if name == "UNITED STATES":
            us = float(tokens[3].replace(",", "")) * 1000
            break
        if tokens[3] != "(NA)":
            values[name] = float(tokens[3].replace(",", "")) * 1000
    if not header or us is None:
        raise ValueError(f"{path.name}: forecast column for {year} or US line not found")
    return pd.Series(values, name="acres").rename_axis("state"), us


def june_grain_reports() -> dict[int, tuple[pd.Series, float, str]]:
    manifest = pd.read_csv(REPORTS_DIR / "reports_manifest.csv")
    manifest = manifest[(manifest["kind"] == "acreage") & manifest["release_date"].notna()]
    out = {}
    for _, row in manifest.iterrows():
        year = int(str(row["release_date"])[:4])
        if year in YEARS:
            states, us = parse_june_grain(REPORTS_DIR / "reports" / row["file"], year)
            out[year] = (states, us, f"{row['file']} (released {row['release_date']})")
    return out


def nass_inseason_with_june_2013(g) -> tuple[pd.DataFrame, dict]:
    """The grain folder's in-season NASS table plus June 2013 state grain forecasts parsed from the report.
    The parse is checked against Quick Stats / data/nass for every other June 2012-2024."""
    inseason = g.nass_inseason_table()
    parsed = june_grain_reports()
    check = {}
    for year, (states, us, source) in sorted(parsed.items()):
        stored = inseason[(inseason["year"] == year) & (inseason["series"] == "grain")
                          & (inseason["period"] == "jun")].set_index("state")["acres"]
        entry = {"report": source, "n_states_parsed": int(len(states)), "us_line": us,
                 "sum_of_states_minus_us_line": float(states.sum() - us)}
        if len(stored):
            joined = states.to_frame("parsed").join(stored.rename("stored"), how="outer")
            entry.update(n_states_stored=int(stored.notna().sum()),
                         max_abs_diff_acres=float((joined["parsed"] - joined["stored"]).abs().max()),
                         states_missing_either=int(joined.isna().any(axis=1).sum()))
        check[year] = entry
    stored_2013 = inseason[(inseason["year"] == 2013) & (inseason["series"] == "grain") & (inseason["period"] == "jun")]
    if len(stored_2013):
        raise RuntimeError("June 2013 grain forecasts already present; nothing to add")
    states_2013 = parsed[2013][0]
    add = pd.DataFrame({"year": 2013, "state": states_2013.index, "series": "grain", "period": "jun",
                        "acres": states_2013.to_numpy()})
    return pd.concat([inseason, add], ignore_index=True), check


def nass_report_used(inseason: pd.DataFrame, year: int, key: str) -> str:
    """The NASS grain-forecast vintage the benchmark used for ``year`` as of ``key`` and how many states had one."""
    from kernelag.state_panel import GRAIN_ASOF, public_by
    rows = inseason[(inseason["year"] == year) & (inseason["series"] == "grain")]
    for period in public_by(GRAIN_ASOF, key):
        n = int(rows.loc[rows["period"] == period, "state"].nunique())
        if n:
            return f"{period} ({n} states with a NASS grain forecast)"
    return "none (planted x share or last year)"


# --- the four runs -----------------------------------------------------------------------------------------------

def _frame(model: str, key: str, year: int, pred: pd.Series, actual: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"model": model, "asof": key, "year": year, "state": actual.index,
                         "pred": pred.reindex(actual.index).to_numpy(float), "actual": actual.to_numpy(float)})


def run_grain_a(g, files: pd.DataFrame, state: pd.DataFrame, nass_table: pd.DataFrame, shared: dict):
    """g3 (Tier A), persistence and the NASS benchmark at every date."""
    finals, inseason, sources = shared["finals"], shared["inseason"], shared["sources"]
    preds, info, bench_diff = [], [], []
    for key in MONTHS:
        stress = g.stress_features(sources, key)
        table, used, _ = g.predict_all(finals, files, state, stress, inseason, YEARS, key)
        for t in YEARS:
            actual = g.truth(finals, t)
            here = table[table["year"] == t]
            for name in ("g3_fsa_ratio_multi", "g0_persistence"):
                part = here[here["candidate"] == name].set_index("state")
                preds.append(_frame(name, key, t, part["pred"], actual))
            u = next(r for r in used if r["year"] == t and r["candidate"] == "g3_fsa_ratio_multi")
            label = fsa_label(files, u["current"], asof_day(t, key))
            info.append({"model": "g3_fsa_ratio_multi", "asof": key, "year": t, "fallback": label is None,
                         "fsa_file": label, "detail": f"states on the guard fallback: {u['n_fallback']}"})
            info.append({"model": "g0_persistence", "asof": key, "year": t, "fallback": False, "fsa_file": None,
                         "detail": "NASS final of last year"})
            bench = g.nass_benchmark(nass_table, finals, t, key)
            preds.append(_frame("nass_latest", key, t, bench, actual))
            info.append({"model": "nass_latest", "asof": key, "year": t, "fallback": False, "fsa_file": None,
                         "detail": nass_report_used(nass_table, t, key)})
            theirs = here[here["candidate"] == "nass_latest"].set_index("state")["pred"].reindex(bench.index)
            gap = (bench - theirs).abs()
            bench_diff.append({"asof": key, "year": t, "max_abs_diff_acres": float(gap.max()),
                               "states_differing": ",".join(sorted(gap.index[gap > 0])),
                               "state_wape_pct_with_june_2013": float(
                                   100 * (bench - actual).abs().sum() / actual.sum()),
                               "state_wape_pct_grain_folder_table": float(
                                   100 * (theirs - actual).abs().sum() / actual.sum())})
    return preds, info, bench_diff


def run_grain_b(b, src, fsa: tuple[pd.DataFrame, pd.DataFrame]):
    """b7 (Tier B) at every date: the folder's inputs_for + nonfitted, with the given FSA tables."""
    src.files, src.fsa_state = fsa
    preds, info = [], []
    for key in MONTHS:
        for t in YEARS:
            inp, used = b.inputs_for(src, t, key)
            out = b.nonfitted(inp)
            b7, b5, g3 = out["b7_blend_b5_fsa_level"], out["b5_planted_x_fsa_share_median"], out["_g3"]
            actual = b.truth(src.finals, t)
            preds.append(_frame("b7_blend_b5_fsa_level", key, t, b7["pred"], actual))
            label = fsa_label(src.files, used["fsa_current"], asof_day(t, key))
            n_b5_fb = int(b5["method"].astype(str).str.startswith("fallback").sum())
            n_g3_fb = int((g3["method"] != "fsa_level").sum())
            info.append({"model": "b7_blend_b5_fsa_level", "asof": key, "year": t, "fallback": label is None,
                         "fsa_file": label,
                         "detail": f"NASS planted: {used['planted_reports']}; b5 part on b0 fallback in {n_b5_fb} "
                                   f"states, FSA-level part on persistence in {n_g3_fb} states"})
    return preds, info


def run_silage_a(s, fsa, shared: dict):
    """s3 (Tier A), reversion_only (H00 and the report's H13) and persistence at every date."""
    finals, states, raw, rma = shared["finals"], shared["states"], shared["raw"], shared["rma"]
    preds, info = [], []
    files = fsa[0]
    for key in MONTHS:
        table, params, used, rows = s.run_asof(key, finals, states, fsa, raw, rma, YEARS)
        scored = s.attach_truth(table, finals, rows)
        names = {"s3_fsa_residual": "s3_fsa_residual", "s1_reversion_only": "reversion_only_H00",
                 "s0_persistence": "s0_persistence"}
        for candidate, model in names.items():
            part = scored[scored["candidate"] == candidate]
            for t, group in part.groupby("year"):
                group = group.set_index("state")
                preds.append(_frame(model, key, int(t), group["pred"], group["actual"]))
        incumbent = s.attach_truth(shared["incumbent_h13"], finals, rows)
        for t, group in incumbent.groupby("year"):
            group = group.set_index("state")
            preds.append(_frame("reversion_only_report_H13", key, int(t), group["pred"], group["actual"]))
        for t in YEARS:
            u = next(r for r in used if r["year"] == t)
            p = next(r for r in params if r["year"] == t)
            label = fsa_label(files, u["current_zip"], asof_day(t, key))
            info.append({"model": "s3_fsa_residual", "asof": key, "year": t, "fallback": label is None,
                         "fsa_file": label, "detail": f"shrink weight w = {p['s3_w']:.2f} "
                                                      f"({p['s3_train_years']} training years); states with an "
                                                      f"FSA residual: {p['s3_states_with_raw']}"})
            for model, detail in [("reversion_only_H00", "NASS finals from 2000 only"),
                                  ("reversion_only_report_H13", "NASS finals from 2013 only (the report model)"),
                                  ("s0_persistence", "NASS final of last year")]:
                info.append({"model": model, "asof": key, "year": t, "fallback": False, "fsa_file": None,
                             "detail": detail})
    return preds, info


def run_silage_b(tb, data: dict, fsa):
    """c5b (Tier B) at every date with the given FSA tables; also returns c0 to check it equals Tier A's s1."""
    data = {**data, "fsa": fsa}
    preds, info, c0 = [], [], []
    for key in MONTHS:
        table, params, used, base = tb.run_asof(data, key, YEARS)
        scored = tb.attach_truth(table, data, base)
        for candidate, sink in [("c5b_residual_fsa_planted_pre_june", preds), ("c0_reversion_only", c0)]:
            part = scored[scored["candidate"] == candidate]
            for t, group in part.groupby("year"):
                group = group.set_index("state")
                sink.append(_frame(candidate, key, int(t), group["pred"], group["actual"]))
        for t in YEARS:
            u = next(r for r in used if r["year"] == t)
            p = next(r for r in params if r["year"] == t)
            label = fsa_label(fsa[0], u["current_zip_name"], asof_day(t, key))
            info.append({"model": "c5b_residual_fsa_planted_pre_june", "asof": key, "year": t,
                         "fallback": label is None, "fsa_file": label,
                         "detail": f"shrink weight w = {p['w5b']:.2f}; states with a residual: "
                                   f"{p['states_with_raw5b']}; NASS planted vintages: {u['nass_planted_vintages']}"})
    return preds, info, c0


def run_all(mods: dict, shared: dict, fsa_root: Path | None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Every model at every date and year with the FSA tables under ``fsa_root`` (None: data/fsa/)."""
    g, s, b, tb = mods["grain_a"], mods["silage_a"], mods["grain_b"], mods["silage_b"]
    files_a, state_a = load_fsa_from(g, fsa_root)
    p1, i1, bench_diff = run_grain_a(g, files_a, state_a, shared["nass_table"], shared["grain_a"])
    p2, i2 = run_grain_b(b, shared["grain_b_src"], load_fsa_from(b, fsa_root))
    p3, i3 = run_silage_a(s, load_fsa_from(s, fsa_root), shared["silage_a"])
    p4, i4, c0 = run_silage_b(tb, shared["silage_b"], load_fsa_from(tb, fsa_root))
    preds = pd.concat(p1 + p2 + p3 + p4, ignore_index=True)
    info = pd.DataFrame(i1 + i2 + i3 + i4)
    s1 = preds[preds["model"] == "reversion_only_H00"].set_index(["asof", "year", "state"])["pred"]
    c0 = pd.concat(c0).set_index(["asof", "year", "state"])["pred"]
    checks = {
        "nass_benchmark_vs_grain_folder_table": {
            "max_abs_diff_acres_years_other_than_2013": max(r["max_abs_diff_acres"] for r in bench_diff
                                                            if r["year"] != 2013),
            "year_2013_by_date": [r for r in bench_diff if r["year"] == 2013],
            "note": "the grain folder's table has no June 2013 grain forecast: there, 15 Jul 2013 is planted x "
                    "share for every state, and at later dates the 9 states without a Crop Production forecast "
                    "are planted x share instead of their June Acreage grain forecast (as in 2012 and 2014-2024)"},
        "tierB_c0_equals_tierA_s1_max_abs_diff_acres": float((c0 - s1.reindex(c0.index)).abs().max()),
    }
    return preds, info, checks


def shared_inputs(mods: dict) -> dict:
    """Inputs that do not depend on the FSA tables, loaded once (after patch_asof)."""
    g, s, b, tb = mods["grain_a"], mods["silage_a"], mods["grain_b"], mods["silage_b"]
    nass_table, june_check = nass_inseason_with_june_2013(g)
    finals_s, states_s = s.load_nass_finals()
    raw = s.load_season_inputs()
    incumbent, incumbent_check = s.reproduce_incumbent(finals_s, states_s)
    return {
        "nass_table": nass_table, "june_check": june_check, "incumbent_check": incumbent_check,
        "grain_a": {"finals": g.load_finals(), "inseason": g.nass_inseason_table(),
                    "sources": g.load_stress_sources()},
        "grain_b_src": b.Sources(),
        "silage_a": {"finals": finals_s, "states": states_s, "raw": raw, "rma": s.rma_silage_acres(raw["insured"]),
                     "incumbent_h13": incumbent},
        "silage_b": tb.load_all(),
    }


# --- scoring -----------------------------------------------------------------------------------------------------

def score(preds: pd.DataFrame, info: pd.DataFrame) -> pd.DataFrame:
    """State WAPE and US error (percent) per model, date and year, with the fallback label and inputs used."""
    if preds["pred"].isna().any():
        bad = preds[preds["pred"].isna()][["model", "asof", "year"]].drop_duplicates()
        raise ValueError(f"missing predictions: {bad.head().to_dict('records')}")
    miss = preds["pred"] - preds["actual"]
    grouped = preds.assign(miss=miss, abs_miss=miss.abs()).groupby(["model", "asof", "year"], sort=False)
    table = grouped.agg(n_states=("state", "size"), actual=("actual", "sum"), miss=("miss", "sum"),
                        abs_miss=("abs_miss", "sum")).reset_index()
    table["state_wape_pct"] = 100 * table["abs_miss"] / table["actual"]
    table["us_error_pct"] = 100 * table["miss"] / table["actual"]
    table = table.merge(info, on=["model", "asof", "year"], how="left", validate="one_to_one")
    table["crop"] = table["model"].map(lambda m: MODELS[m][0])
    table["tier"] = table["model"].map(lambda m: MODELS[m][1])
    order = {m: i for i, m in enumerate(MODELS)}
    table = table.sort_values(["model", "asof", "year"], key=lambda c: c.map(order) if c.name == "model" else (
        c.map(MONTHS) if c.name == "asof" else c))
    return table[["model", "tier", "crop", "asof", "year", "n_states", "state_wape_pct", "us_error_pct", "fallback",
                  "fsa_file", "detail"]].reset_index(drop=True)


def summarise(by_year: pd.DataFrame) -> pd.DataFrame:
    """Mean metrics per model, date and period; plus each model's average over the six dates and over Aug-Dec."""
    rows = []
    for period, (lo, hi) in PERIODS.items():
        part = by_year[by_year["year"].between(lo, hi)]
        for (model, key), group in part.groupby(["model", "asof"], sort=False):
            if len(group) != hi - lo + 1:
                continue                     # the report's H13 reversion model exists for 2017-2024 only
            rows.append({"model": model, "tier": MODELS[model][1], "crop": MODELS[model][0], "asof": key,
                         "period": period, "n_years": len(group),
                         "mean_state_wape_pct": group["state_wape_pct"].mean(),
                         "mean_abs_us_error_pct": group["us_error_pct"].abs().mean(),
                         "mean_signed_us_error_pct": group["us_error_pct"].mean(),
                         "fallback_share": group["fallback"].astype(float).mean(),
                         "fallback_years": " ".join(str(y) for y in group.loc[group["fallback"], "year"]),
                         "worst_year_state_wape_pct": group["state_wape_pct"].max()})
    summary = pd.DataFrame(rows)
    extra = []
    for (model, period), group in summary.groupby(["model", "period"], sort=False):
        for name, keys in AVERAGES.items():
            sub = group[group["asof"].isin(keys)]
            if len(sub) != len(keys):
                continue
            extra.append({"model": model, "tier": MODELS[model][1], "crop": MODELS[model][0], "asof": name,
                          "period": period, "n_years": int(sub["n_years"].iloc[0]),
                          **{c: sub[c].mean() for c in ["mean_state_wape_pct", "mean_abs_us_error_pct",
                                                        "mean_signed_us_error_pct", "fallback_share"]},
                          "fallback_years": "", "worst_year_state_wape_pct": np.nan})
    summary = pd.concat([summary, pd.DataFrame(extra)], ignore_index=True)
    keys = [*MONTHS, *AVERAGES]
    order = {m: i for i, m in enumerate(MODELS)}
    return summary.sort_values(["period", "model", "asof"], key=lambda c: c.map(order) if c.name == "model" else (
        c.map({k: i for i, k in enumerate(keys)}) if c.name == "asof" else c.map({p: i for i, p in enumerate(
            PERIODS)}))).reset_index(drop=True)


def paired_ci(diffs: np.ndarray, boot: int = BOOT, seed: int = SEED) -> tuple[float, float, float]:
    """Mean of paired yearly differences and its 90% bootstrap interval (resampling years); the grain folder's
    method and seed."""
    rng = np.random.default_rng(seed)
    means = diffs[rng.integers(0, len(diffs), size=(boot, len(diffs)))].mean(axis=1)
    return float(diffs.mean()), float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95))


def ci_vs_nass(by_year: pd.DataFrame, boot: int) -> pd.DataFrame:
    """Each grain model (Tier A, Tier B) minus NASS's forecast of the same date, paired by year."""
    rows = []
    for period, (lo, hi) in PERIODS.items():
        part = by_year[by_year["year"].between(lo, hi)].assign(abs_us=lambda d: d["us_error_pct"].abs())
        for metric, column in [("state_wape_pct", "state_wape_pct"), ("abs_us_error_pct", "abs_us")]:
            wide = part.pivot_table(index="year", columns=["model", "asof"], values=column)
            for model in ["g3_fsa_ratio_multi", "b7_blend_b5_fsa_level"]:
                keys = [(k, [k]) for k in MONTHS] + list(AVERAGES.items())
                for name, members in keys:
                    mine = wide[[(model, k) for k in members]].mean(axis=1)
                    nass = wide[[("nass_latest", k) for k in members]].mean(axis=1)
                    d = (mine - nass).to_numpy()
                    mean, lo_ci, hi_ci = paired_ci(d, boot)
                    rows.append({"model": model, "reference": "nass_latest", "asof": name, "period": period,
                                 "metric": metric, "n_years": len(d), "mean_model": float(mine.mean()),
                                 "mean_nass": float(nass.mean()), "mean_diff_pts": mean, "ci90_lo": lo_ci,
                                 "ci90_hi": hi_ci, "years_model_better": int((d < 0).sum())})
    return pd.DataFrame(rows)


def split_by_fsa(by_year: pd.DataFrame) -> pd.DataFrame:
    """Where a date mixes years with and without a current-year FSA file (15 Aug): each selected model on each
    group of years, beside NASS's forecast and persistence on the same years."""
    rows = []
    reference = {"grain": ["nass_latest", "g0_persistence"], "silage": ["reversion_only_H00", "s0_persistence"]}
    for period, (lo, hi) in PERIODS.items():
        part = by_year[by_year["year"].between(lo, hi)]
        for model in SELECTED:
            crop = MODELS[model][0]
            for key in MONTHS:
                mine = part[(part["model"] == model) & (part["asof"] == key)].set_index("year")
                if mine["fallback"].all() or not mine["fallback"].any():
                    continue
                for group, years in [("years with a current-year FSA file", mine.index[~mine["fallback"]]),
                                     ("fallback years (no current-year FSA file)", mine.index[mine["fallback"]])]:
                    row = {"model": model, "crop": crop, "asof": key, "period": period, "group": group,
                           "years": " ".join(str(y) for y in years), "n_years": len(years)}
                    for name in [model, *reference[crop]]:
                        other = part[(part["model"] == name) & (part["asof"] == key)].set_index("year").loc[years]
                        tag = "model" if name == model else name
                        row[f"{tag}_state_wape_pct"] = other["state_wape_pct"].mean()
                        row[f"{tag}_abs_us_error_pct"] = other["us_error_pct"].abs().mean()
                    rows.append(row)
    return pd.DataFrame(rows)


# --- reproduction of the folders' numbers on the pre-fix tables ---------------------------------------------------

def folder_summary(model: str) -> pd.DataFrame:
    folder, candidate, asof_column = FOLDER_NAMES[model]
    table = pd.read_csv(OWN / folder / "out" / "summary.csv")
    table = table[(table["candidate"] == candidate) & table["period"].isin(list(PERIODS))]
    table = table.rename(columns={asof_column: "asof"})
    return table[["asof", "period", "n_years", "mean_state_wape_pct", "mean_abs_us_error_pct",
                  "mean_signed_us_error_pct"]].assign(model=model)


def compare_to_folders(summary_old: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """The harness on the pre-fix FSA tables against each folder's out/summary.csv (15 Sep, 15 Oct, 15 Nov)."""
    metrics = ["mean_state_wape_pct", "mean_abs_us_error_pct", "mean_signed_us_error_pct"]
    joined = []
    for model in FOLDER_NAMES:
        theirs = folder_summary(model)
        theirs = theirs[theirs["n_years"] == theirs["period"].map(lambda p: PERIODS[p][1] - PERIODS[p][0] + 1)]
        mine = summary_old[summary_old["model"] == model]
        joined.append(theirs.merge(mine[["model", "asof", "period", *metrics]], on=["model", "asof", "period"],
                                   suffixes=("_folder", "_harness_old")))
    joined = pd.concat(joined, ignore_index=True)
    worst = {m: float((joined[f"{m}_folder"] - joined[f"{m}_harness_old"]).abs().max()) for m in metrics}
    return {"cells_compared": int(len(joined)), "max_abs_diff_pts": worst,
            "models": sorted(joined["model"].unique())}, joined


def before_after(summary_new: pd.DataFrame, summary_old: pd.DataFrame | None) -> pd.DataFrame:
    """The four selected models' numbers before and after the FSA publication-date fix, every date and period."""
    metrics = ["mean_state_wape_pct", "mean_abs_us_error_pct", "mean_signed_us_error_pct"]
    new = summary_new[summary_new["model"].isin(SELECTED)][["model", "asof", "period", *metrics]]
    table = new.rename(columns={m: f"{m}_after" for m in metrics})
    if summary_old is not None:
        old = summary_old[summary_old["model"].isin(SELECTED)][["model", "asof", "period", *metrics]]
        table = table.merge(old.rename(columns={m: f"{m}_before_harness" for m in metrics}),
                            on=["model", "asof", "period"], how="left")
    folders = pd.concat([folder_summary(m) for m in SELECTED], ignore_index=True)
    folders = folders[folders["n_years"] == folders["period"].map(lambda p: PERIODS[p][1] - PERIODS[p][0] + 1)]
    table = table.merge(folders[["model", "asof", "period", *metrics]].rename(
        columns={m: f"{m}_before_folder_out" for m in metrics}), on=["model", "asof", "period"], how="left")
    for m in metrics:
        before = f"{m}_before_harness" if summary_old is not None else f"{m}_before_folder_out"
        table[f"{m}_change"] = table[f"{m}_after"] - table[before]
    return table


# --- main --------------------------------------------------------------------------------------------------------

def fsa_files_used(info: pd.DataFrame) -> pd.DataFrame:
    part = info[info["model"].isin(FSA_MODELS)]
    wide = part.pivot(index=["year", "asof"], columns="model", values="fsa_file")
    wide = wide.reindex(columns=SELECTED).reset_index()
    wide["same_file_for_all_four"] = wide[SELECTED].nunique(axis=1, dropna=False) <= 1
    wide["asof"] = pd.Categorical(wide["asof"], categories=list(MONTHS), ordered=True)
    return wide.sort_values(["year", "asof"])


def _write(frame: pd.DataFrame, name: str, fmt: str = "%.6g") -> None:
    frame.to_csv(OUT / name, index=False, lineterminator="\n", float_format=fmt)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old-fsa-root", type=Path, default=None,
                        help="folder holding fsa/fsa_files.csv and fsa/fsa_corn_state.csv from before the FSA fix")
    parser.add_argument("--boot", type=int, default=BOOT)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    mods = load_modules()
    patch_asof(mods)
    shared = shared_inputs(mods)

    preds, info, checks = run_all(mods, shared, None)
    by_year = score(preds, info)
    summary = summarise(by_year)
    ci = ci_vs_nass(by_year, args.boot)

    reproduction = {
        "asof_patch": {"kernelag.context.ASOF_MONTH": dict(kctx.ASOF_MONTH),
                       "module_ASOF": {k: {a: list(v) for a, v in m.ASOF.items()} for k, m in mods.items()}},
        "june_acreage_grain_parse": shared["june_check"],
        "report_reversion_only_H13_vs_stored_backtest": {
            k: {"exact_to_2dp": v["exact_to_2dp"], "mean_state_wape_mine": v["mean_state_wape_mine"],
                "mean_state_wape_stored": v["mean_state_wape_stored"]} for k, v in shared["incumbent_check"].items()},
        **checks,
    }
    nass_nov = summary[(summary["model"] == "nass_latest") & (summary["asof"] == "nov")
                       & (summary["period"] == "2017-2024")].iloc[0]
    nov_years = by_year[(by_year["model"] == "nass_latest") & (by_year["asof"] == "nov")
                        & by_year["year"].between(2017, 2024)]
    reproduction["nass_latest_nov_2017_2024"] = {
        "expected_incumbent_rounded_per_year": [1.66, 0.82],
        "reproduced_rounded_per_year": [round(float(nov_years["state_wape_pct"].round(2).mean()), 2),
                                        round(float(nov_years["us_error_pct"].round(2).abs().mean()), 2)],
        "unrounded": [float(nass_nov["mean_state_wape_pct"]), float(nass_nov["mean_abs_us_error_pct"])]}
    dec = by_year[by_year["model"] == "nass_latest"].pivot(index="year", columns="asof", values="state_wape_pct")
    reproduction["nass_latest_dec_equals_nov_max_abs_diff_pts"] = float((dec["dec"] - dec["nov"]).abs().max())

    summary_old = None
    if args.old_fsa_root is not None:
        preds_old, info_old, checks_old = run_all(mods, shared, args.old_fsa_root)
        by_year_old = score(preds_old, info_old)
        summary_old = summarise(by_year_old)
        reproduction["harness_on_pre_fix_fsa_tables_vs_folder_out_summary"], joined = compare_to_folders(summary_old)
        reproduction["pre_fix_run_checks"] = checks_old
        _write(joined, "reproduction_pre_fix_vs_folders.csv")
        _write(by_year_old, "monthly_by_year_pre_fix_fsa_dates.csv")
    _write(before_after(summary, summary_old), "fsa_fix_before_after.csv")

    _write(summary, "monthly_summary.csv")
    _write(by_year, "monthly_by_year.csv")
    _write(preds.sort_values(["model", "asof", "year", "state"]), "monthly_by_state_year.csv", "%.1f")
    _write(ci, "monthly_vs_nass_ci.csv")
    _write(split_by_fsa(by_year), "monthly_split_by_fsa_availability.csv")
    _write(fsa_files_used(info), "fsa_files_used.csv")
    (OUT / "reproduction.json").write_text(json.dumps(reproduction, indent=1, default=str) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    head = summary[summary["period"] == "2017-2024"].pivot(index="model", columns="asof", values="mean_state_wape_pct")
    print(head.reindex(columns=[*MONTHS, *AVERAGES]).round(2).to_string())
    print(json.dumps({k: v for k, v in reproduction.items() if k not in ("asof_patch", "june_acreage_grain_parse")},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
