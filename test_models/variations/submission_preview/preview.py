"""Submission preview: every grain x silage combination in the format of kernelag/deliverable.py.

Grain {NASS pass-through, A-G3, g9} x silage {SC, SC_A, SC_B, A-S3, v1_geo} = 15 combinations. For each one:

    out/<combo>/deliverable_2026.csv         2026 state rows + US, grain and silage, 80% (and 90% where the
                                             source has them) intervals
    out/<combo>/deliverable_comparison.csv   2017-2025 vs the organizer CSV truth, exactly as
                                             kernelag.deliverable.compare builds it
    out/<combo>/deliverable_summary.json     kernelag.deliverable.summarize, plus signed US means and the tier

and, over all combinations: out/scorecard_by_year.csv, out/scorecard.csv, out/SCORECARD.md, out/monthly_grid.csv,
out/reproduction.json.

Step 1 rebuilds the CURRENT deliverable in memory with kernelag.deliverable's own functions (nothing under data/ is
written; record_in_manifest is never called) and requires byte-identical deliverable_comparison.csv and
deliverable_2026.csv and an identical deliverable_summary.json (the static "notes" text excepted). If that fails the
script stops before scoring anything.

Candidate predictions (read only):
- NASS pass-through and SC: the reproduced deliverable (2017-2025) and its 2026 table.
- A-G3 (g3_fsa_ratio_multi, 15 Nov, corrected FSA dates): 2017-2024 from ownModels/monthly/out/monthly_by_state_year.csv.
  2025 is recomputed here with the grain folder's own functions (NassHistory, FsaView, predict_fsa: what the monthly
  harness's run_grain_a calls through predict_all). 2026 points and 80% intervals: grain_variants/out/forecast_2026.csv
  (A-G3 reference rows; run through the monthly harness with the corrected dates), checked against the same
  recomputation. ownModels/grain/out/forecast_2026.csv predates the FSA date fix and is only compared.
- g9_national_reconciliation: 2017-2024 from grain_variants/out/by_state_year.csv; 2025 recomputed with
  grain_variants/run.py's national_reconciliation on the recomputed A-G3; 2026 from grain_variants/out/forecast_2026.csv.
- SC_A, SC_B, A-S3 (key "A"), v1_geo: 2017-2024 and 2026 from silage_combos/out/ (backtest_by_state_year.csv,
  forecast_2026.csv, forecast_2026_us.csv). 2025 is not in those files (that folder never ran 2025), so it is
  recomputed here with silage_combos/run.py's own pieces (A-S3's run_asof, kernelag.silage_level.predict with the
  SC_B / SC_A exposures, v1_geo = sqrt(A-S3 x SC)).
Every recomputation is first checked against the saved 2017-2024 (and 2026) rows of the same model.

Tiers: A = no current-year NASS data; B = NASS-informed without NASS's grain forecast; C = uses NASS's grain
forecast. A combination's tier is the weakest of its two parts.

Run from the repository root:
    .venv/Scripts/python.exe -B test_models/variations/submission_preview/preview.py [--lean] [--cache FILE]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True   # importing other folders' modules must not leave __pycache__ behind

import argparse  # noqa: E402
import importlib.util  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from kernelag import deliverable as dlv  # noqa: E402
from kernelag import silage_level, state_model  # noqa: E402
from kernelag.paths import data_dir, kit_dir  # noqa: E402
from kernelag.state_panel import QUICKSTATS_DIR  # noqa: E402

OUT = HERE / "out"
MODELS = REPO / "data" / "models"
STORED_COMPARISON = MODELS / "deliverable_comparison.csv"
STORED_SUMMARY = MODELS / "deliverable_summary.json"
STORED_2026 = MODELS / f"deliverable_{dlv.FORECAST_YEAR}.csv"

TM = REPO / "test_models"
MONTHLY_STATE_YEAR = TM / "ownModels" / "monthly" / "out" / "monthly_by_state_year.csv"
GRAIN_RUN = TM / "ownModels" / "grain" / "run.py"
GRAIN_PRE_FIX_2026 = TM / "ownModels" / "grain" / "out" / "forecast_2026.csv"
GRAIN_PRE_FIX_2025 = TM / "ownModels" / "grain" / "out" / "score_2025_information_only.csv"
GV_RUN = TM / "variations" / "grain_variants" / "run.py"
GV_BACKTEST = TM / "variations" / "grain_variants" / "out" / "by_state_year.csv"
GV_2026 = TM / "variations" / "grain_variants" / "out" / "forecast_2026.csv"
SCB_RUN = TM / "variations" / "silage_combos" / "run.py"
SCB_BACKTEST = TM / "variations" / "silage_combos" / "out" / "backtest_by_state_year.csv"
SCB_2026 = TM / "variations" / "silage_combos" / "out" / "forecast_2026.csv"
SCB_2026_US = TM / "variations" / "silage_combos" / "out" / "forecast_2026_us.csv"

YEARS = list(dlv.YEARS)                                # 2017-2025
BACKTEST = [y for y in YEARS if y <= state_model.LAST_BASELINE_YEAR]   # 2017-2024
INFO_YEAR = 2025
FORECAST_YEAR = dlv.FORECAST_YEAR                      # 2026
US_ROW = "US (sum of states shown)"
ACRE_ROUND = {"predicted": -2, "last": -2, "error_pct": 2, "last_year_error_pct": 2}   # as kernelag.deliverable.run
TOL_ACRES = 0.051                                      # saved tables keep 0.1 acre
TIER_ORDER = {"A": 0, "B": 1, "C": 2}
MONTHS = ["jul", "aug", "sep", "oct", "nov", "dec"]

GRAIN = {   # key -> tier, label, saved-model name
    "NASS": ("C", "NASS's own November harvested-for-grain forecast, passed through (current deliverable)", None),
    "A-G3": ("A", "g3_fsa_ratio_multi: FSA grain-intended acres x median NASS/FSA ratio of 3 years", "g3_fsa_ratio_multi"),
    "g9": ("A", "g9_national_reconciliation: A-G3's FSA states scaled to a national FSA x NASS/FSA ratio",
           "g9_national_reconciliation"),
}
SILAGE = {  # key -> tier, label, model name in silage_combos
    "SC": ("C", "smoothed_chopping (current deliverable; NASS yield and grain-acre forecasts)", "SC"),
    "SC_A": ("A", "SC with a Drought Monitor D2+ exposure (Tier A twin)", "SC_A"),
    "SC_B": ("B", "SC with last year's final grain acres in the exposure (Tier B twin)", "SC_B"),
    "A-S3": ("A", "s3_fsa_residual (A-S3), corrected FSA dates", "A"),
    "v1_geo": ("C", "sqrt(A-S3 x SC)", "v1_geo"),
}
SILAGE_METHOD = {"SC": state_model.SMOOTHED, "SC_A": "SC_A_drought_exposure", "SC_B": "SC_B_last_year_grain",
                 "A-S3": "s3_fsa_residual", "v1_geo": "v1_geo_sqrt_A_S3_x_SC"}


def combo_name(grain: str, silage: str) -> str:
    return f"{grain}__{silage}"


def tier_of(grain: str, silage: str) -> str:
    return max(GRAIN[grain][0], SILAGE[silage][0], key=TIER_ORDER.get)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def csv_text(frame: pd.DataFrame) -> str:
    return frame.to_csv(index=False, lineterminator="\n")


def stored_text(path: Path) -> str:
    """A stored file's text with CRLF turned into LF: kernelag.deliverable writes LF, but the copies on disk carry
    CRLF (converted after writing), so only the line terminator is normalised; every character else must match."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def has_crlf(path: Path) -> bool:
    return b"\r\n" in path.read_bytes()


# --- step 1: the current deliverable, rebuilt in memory ------------------------------------------------------------

def reproduce_deliverable(lean: bool) -> dict:
    """kernelag.deliverable.run without its writes: same functions, same order, same rounding."""
    table = dlv.build_table(lean)
    history = silage_level.load_history(data_dir() / QUICKSTATS_DIR, "nov")
    organizer = dlv.organizer_truth(kit_dir() / dlv.ORGANIZER_CSV)
    nass_acres = pd.read_csv(data_dir() / "nass" / "corn_acres_state.csv")
    truth = dlv.with_census_years(organizer, nass_acres)
    shared = organizer.merge(nass_acres[nass_acres["period"] == "final"], on=["year", "state", "series"])
    ours = dlv.our_numbers(table, history, dlv.YEARS)
    comparison = dlv.compare(ours, truth)
    summary = dlv.summarize(comparison)
    summary["truth_check"] = {"organizer_rows_also_in_pipeline_copy": len(shared),
                              "rows_that_differ": int((shared["actual"] != shared["acres"]).sum())}
    held_out = state_model.backtest_predictions(table, history=history)
    forecast = state_model.forecast(table, FORECAST_YEAR, state_model.SMOOTHED, held_out, history)
    table_2026 = dlv.deliverable_table(forecast)

    stored_summary = json.loads(STORED_SUMMARY.read_text(encoding="utf-8"))
    mine_summary = json.loads(json.dumps(summary))
    checks = {
        "deliverable_comparison_csv_text_identical":
            csv_text(comparison.round(ACRE_ROUND)) == stored_text(STORED_COMPARISON),
        "deliverable_2026_csv_text_identical": csv_text(table_2026) == stored_text(STORED_2026),
        "deliverable_summary_json_identical_except_notes":
            {k: v for k, v in stored_summary.items() if k != "notes"} == mine_summary,
        "line_endings": {"stored_files_have_crlf": {p.name: has_crlf(p) for p in
                                                    (STORED_COMPARISON, STORED_2026, STORED_SUMMARY)},
                         "compared_after": "CRLF -> LF only (kernelag.deliverable writes LF); all other bytes equal"},
        "summary_keys_compared": sorted(mine_summary),
        "notes_not_regenerated": "the 'notes' list is static text inside kernelag.deliverable.run",
        "lean_table": lean,
    }
    checks["all_identical"] = all(checks[k] for k in ("deliverable_comparison_csv_text_identical",
                                                      "deliverable_2026_csv_text_identical",
                                                      "deliverable_summary_json_identical_except_notes"))
    return {"table": table, "history": history, "truth": truth, "ours": ours, "comparison": comparison,
            "summary": summary, "table_2026": table_2026, "checks": checks}


# --- step 2: candidate predictions ---------------------------------------------------------------------------------

def recompute_grain(years: list[int]) -> pd.DataFrame:
    """A-G3 and g9 at 15 Nov of ``years`` with the grain folder's and grain_variants' own functions."""
    g = load_module("preview_grain_a", GRAIN_RUN)
    gv = load_module("preview_grain_variants", GV_RUN)
    finals = g.load_finals()
    files, state = g.load_fsa()
    rows = []
    for t in years:
        hist = g.NassHistory(finals, t)
        view = g.FsaView(files, state, g.asof_date(t, "nov"), t)
        a3, used = g.predict_fsa("g3_fsa_ratio_multi", hist, view)
        g9, info = gv.national_reconciliation(g, hist, view, a3)
        for key, frame in (("A-G3", a3), ("g9", g9)):
            rows.append(pd.DataFrame({"key": key, "year": t, "state": frame.index, "pred": frame["pred"].to_numpy(),
                                      "method": frame["method"].to_numpy(), "fsa_current": used["current"],
                                      "fsa_current_data_as_of": used["current_data_as_of"]}))
    return pd.concat(rows, ignore_index=True)


def recompute_silage(years: list[int]) -> pd.DataFrame:
    """A-S3, SC, SC_A, SC_B and v1_geo at 15 Nov of ``years``, built as silage_combos/run.py builds them."""
    scb = load_module("preview_silage_combos", SCB_RUN)
    mod_a = load_module("preview_silage_tier_a", scb.A_PATH)
    finals, states = mod_a.load_nass_finals()
    fsa = mod_a.load_fsa()
    raw = mod_a.load_season_inputs()
    rma = mod_a.rma_silage_acres(raw["insured"])
    preds, _, _, _ = mod_a.run_asof("nov", finals, states, fsa, raw, rma, years)
    a = preds[preds["candidate"] == "s3_fsa_residual"]
    parts = [pd.DataFrame({"key": "A-S3", "year": a["year"].to_numpy(), "state": a["state"].to_numpy(),
                           "pred": a["pred"].to_numpy()})]
    history = silage_level.load_history(scb.QUICKSTATS, "nov")
    exposure_sc = silage_level.chopping_exposure(history)
    no_grain_forecast = {**history, "grain_asof": history["grain_asof"].iloc[0:0]}
    exposures = {"SC": None, "SC_B": silage_level.chopping_exposure(no_grain_forecast),
                 "SC_A": scb.drought_exposure(history, raw["usdm"], "nov", exposure_sc)}
    for key, exposure in exposures.items():
        for year in years:
            pred, _ = silage_level.predict(history, year) if exposure is None \
                else silage_level.predict(history, year, exposure=exposure)
            pred = pred.reindex(states)
            parts.append(pd.DataFrame({"key": key, "year": year, "state": states, "pred": pred.to_numpy()}))
    long = pd.concat(parts, ignore_index=True)
    wide = long.pivot_table(index=["year", "state"], columns="key", values="pred")
    geo = np.sqrt(wide["A-S3"] * wide["SC"]).rename("pred").reset_index().assign(key="v1_geo")
    return pd.concat([long, geo], ignore_index=True)


def max_gap(mine: pd.DataFrame, saved: pd.DataFrame) -> dict:
    """Largest |difference| between two (year, state, pred) tables on their common rows, and the row counts."""
    joined = saved.merge(mine, on=["year", "state"], how="left", suffixes=("_saved", "_mine"))
    gap = (joined["pred_mine"] - joined["pred_saved"]).abs()
    return {"rows_saved": int(len(saved)), "rows_missing_in_recomputation": int(joined["pred_mine"].isna().sum()),
            "max_abs_diff_acres": float(gap.max()) if len(gap) else float("nan")}


def grain_candidates(recomputed: pd.DataFrame) -> tuple[dict, dict]:
    """Per grain key: predictions 2017-2025 (year, state, pred, method) and 2026 rows; plus checks."""
    monthly = pd.read_csv(MONTHLY_STATE_YEAR)
    gv_back = pd.read_csv(GV_BACKTEST)
    gv_2026 = pd.read_csv(GV_2026)
    saved = {
        "A-G3": monthly[(monthly["model"] == "g3_fsa_ratio_multi") & (monthly["asof"] == "nov")],
        "g9": gv_back[(gv_back["model"] == "g9_national_reconciliation") & (gv_back["asof"] == "nov")],
    }
    checks, out = {}, {}
    for key in ("A-G3", "g9"):
        mine = recomputed[recomputed["key"] == key]
        back = saved[key][saved[key]["year"].isin(BACKTEST)][["year", "state", "pred"]]
        fc = gv_2026[gv_2026["model"] == GRAIN[key][2]]
        fc_states = fc[~fc["state"].str.startswith("US")]
        fc_us = fc[fc["state"].str.startswith("US")].iloc[0]
        check = {"vs_saved_2017_2024": max_gap(mine[mine["year"].isin(BACKTEST)][["year", "state", "pred"]], back),
                 "vs_grain_variants_forecast_2026": max_gap(
                     mine[mine["year"] == FORECAST_YEAR][["year", "state", "pred"]],
                     fc_states.assign(year=FORECAST_YEAR)[["year", "state", "pred"]]),
                 "fsa_file_2025": mine.loc[mine["year"] == INFO_YEAR, "fsa_current"].iloc[0],
                 "fsa_file_2025_data_as_of": mine.loc[mine["year"] == INFO_YEAR, "fsa_current_data_as_of"].iloc[0],
                 "fsa_file_2026": mine.loc[mine["year"] == FORECAST_YEAR, "fsa_current"].iloc[0],
                 "methods_2025": mine.loc[mine["year"] == INFO_YEAR, "method"].value_counts().to_dict()}
        ok = (check["vs_saved_2017_2024"]["max_abs_diff_acres"] <= TOL_ACRES
              and check["vs_saved_2017_2024"]["rows_missing_in_recomputation"] == 0
              and check["vs_grain_variants_forecast_2026"]["max_abs_diff_acres"] <= 0.01   # stored at 10 significant digits
              and check["vs_grain_variants_forecast_2026"]["rows_missing_in_recomputation"] == 0)
        check["recomputation_reproduces_saved"] = bool(ok)
        checks[key] = check
        if not ok:
            raise SystemExit(f"{key}: recomputation does not reproduce the saved rows: {check}")
        method = mine.set_index(["year", "state"])["method"]
        prefix = "g3" if key == "A-G3" else "g9"
        past = pd.concat([back.assign(source="saved"),
                          mine[mine["year"] == INFO_YEAR][["year", "state", "pred"]].assign(source="recomputed")],
                         ignore_index=True)
        past["method"] = [f"{prefix}_{method.get((y, s), 'unknown')}" for y, s in zip(past["year"], past["state"])]
        fc_table = pd.DataFrame({"state": fc_states["state"].to_numpy(), "grain": fc_states["pred"].to_numpy(),
                                 "grain_lo80": fc_states["lo80"].to_numpy(), "grain_hi80": fc_states["hi80"].to_numpy()})
        m26 = mine[mine["year"] == FORECAST_YEAR].set_index("state")["method"]
        fc_table["grain_method"] = [f"{prefix}_{m26.get(s, 'unknown')}" for s in fc_table["state"]]
        us = {"grain": float(fc_us["pred"]), "grain_lo80": float(fc_us["lo80"]), "grain_hi80": float(fc_us["hi80"])}
        out[key] = {"past": past, "fc_states": fc_table, "fc_us": us,
                    "sources": {"2017-2024": f"saved: {back_path(key)}",
                                "2025": "recomputed here (grain folder's predict_fsa"
                                        + (" + grain_variants national_reconciliation" if key == "g9" else "")
                                        + ", corrected FSA dates)",
                                "2026": f"saved: {GV_2026.relative_to(REPO).as_posix()} (points checked against the "
                                        "recomputation; 80% intervals from that file)"}}
    pre_fix = pd.read_csv(GRAIN_PRE_FIX_2026)
    pre_fix = pre_fix[~pre_fix["state"].str.startswith("US")].assign(year=FORECAST_YEAR)[["year", "state", "pred"]]
    a3_26 = recomputed[(recomputed["key"] == "A-G3") & (recomputed["year"] == FORECAST_YEAR)]
    checks["A-G3"]["pre_fix_grain_forecast_2026_vs_recomputed"] = max_gap(a3_26[["year", "state", "pred"]], pre_fix)
    pre25 = pd.read_csv(GRAIN_PRE_FIX_2025)
    pre25 = pre25[pre25["candidate"] == "g3_fsa_ratio_multi"].assign(year=INFO_YEAR)[["year", "state", "pred"]]
    a3_25 = recomputed[(recomputed["key"] == "A-G3") & (recomputed["year"] == INFO_YEAR)]
    checks["A-G3"]["pre_fix_grain_score_2025_vs_recomputed"] = max_gap(a3_25[["year", "state", "pred"]], pre25)
    # those two files keep 6 significant digits: compare at that precision
    for name, mine, theirs in (("pre_fix_2026_vs_recomputed_at_6_significant_digits", a3_26, pre_fix),
                               ("pre_fix_2025_vs_recomputed_at_6_significant_digits", a3_25, pre25)):
        rounded = mine.assign(pred=mine["pred"].map(lambda v: float(f"{v:.6g}")))
        checks["A-G3"][name] = max_gap(rounded[["year", "state", "pred"]], theirs)
    return out, checks


def back_path(key: str) -> str:
    path = MONTHLY_STATE_YEAR if key == "A-G3" else GV_BACKTEST
    return f"{path.relative_to(REPO).as_posix()} (model {GRAIN[key][2]}, asof nov)"


def silage_candidates(recomputed: pd.DataFrame, deliverable_comparison: pd.DataFrame) -> tuple[dict, dict]:
    """Per silage key except SC: predictions 2017-2025 and 2026 rows; plus checks (SC is checked too)."""
    back = pd.read_csv(SCB_BACKTEST)
    back = back[back["asof"] == "nov"]
    fc = pd.read_csv(SCB_2026)
    fc = fc[fc["asof"] == "nov"]
    fc_us = pd.read_csv(SCB_2026_US)
    fc_us = fc_us[fc_us["asof"] == "nov"]
    monthly = pd.read_csv(MONTHLY_STATE_YEAR)
    checks, out = {}, {}
    for key, (_, _, model) in SILAGE.items():
        mine = recomputed[recomputed["key"] == key]
        saved = back[back["model"] == model]
        check = {"vs_saved_2017_2024": max_gap(mine[mine["year"].isin(BACKTEST)][["year", "state", "pred"]],
                                               saved[saved["year"].isin(BACKTEST)][["year", "state", "pred"]]),
                 "vs_saved_2026": max_gap(mine[mine["year"] == FORECAST_YEAR][["year", "state", "pred"]],
                                          saved[saved["year"] == FORECAST_YEAR][["year", "state", "pred"]])}
        ok = all(c["max_abs_diff_acres"] <= TOL_ACRES and c["rows_missing_in_recomputation"] == 0
                 for c in (check["vs_saved_2017_2024"], check["vs_saved_2026"]))
        if key == "SC":
            dsc = state_rows(deliverable_comparison)
            dsc = dsc[dsc["series"] == "silage"][["year", "state", "predicted"]]
            dsc = dsc.rename(columns={"predicted": "pred"})
            check["vs_deliverable_2017_2025"] = max_gap(mine[mine["year"].isin(YEARS)][["year", "state", "pred"]], dsc)
            ok = ok and check["vs_deliverable_2017_2025"]["max_abs_diff_acres"] <= 1e-6
        if key == "A-S3":
            ms3 = monthly[(monthly["model"] == "s3_fsa_residual") & (monthly["asof"] == "nov")]
            check["vs_monthly_s3_2017_2024"] = max_gap(mine[mine["year"].isin(BACKTEST)][["year", "state", "pred"]],
                                                       ms3[ms3["year"].isin(BACKTEST)][["year", "state", "pred"]])
        check["recomputation_reproduces_saved"] = bool(ok)
        checks[key] = check
        if not ok:
            raise SystemExit(f"{key}: recomputation does not reproduce the saved rows: {check}")
        if key == "SC":
            continue             # the deliverable itself supplies SC
        past = pd.concat([saved[saved["year"].isin(BACKTEST)][["year", "state", "pred"]].assign(source="saved"),
                          mine[mine["year"] == INFO_YEAR][["year", "state", "pred"]].assign(source="recomputed")],
                         ignore_index=True)
        f = fc[fc["model"] == model]
        us = fc_us[fc_us["model"] == model].iloc[0]
        out[key] = {"past": past,
                    "fc_states": f[["state", "silage", "silage_lo80", "silage_hi80", "silage_lo90", "silage_hi90"]]
                    .reset_index(drop=True),
                    "fc_us": {"silage": float(us["us_silage"]), "silage_lo80": float(us["us_lo80"]),
                              "silage_hi80": float(us["us_hi80"])},
                    "sources": {"2017-2024": f"saved: {SCB_BACKTEST.relative_to(REPO).as_posix()} (model {model}, "
                                             "asof nov)",
                                "2025": "recomputed here with silage_combos/run.py's pieces (not in its saved files)",
                                "2026": f"saved: {SCB_2026.relative_to(REPO).as_posix()} and "
                                        f"{SCB_2026_US.relative_to(REPO).as_posix()} (model {model}, asof nov)"}}
    return out, checks


# --- step 3: combinations ------------------------------------------------------------------------------------------

def grain_part(key: str, rep: dict, grains: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """(past rows: year, state, predicted, grain_method), (2026 state rows), (2026 US values), (sources)."""
    if key == "NASS":
        ours = rep["ours"][rep["ours"]["series"] == "grain"]
        past = ours[["year", "state", "predicted", "grain_method"]]
        t = rep["table_2026"]
        cols = ["grain", "grain_lo80", "grain_hi80", "grain_lo90", "grain_hi90"]
        states = t[~t["state"].str.startswith("US")].dropna(subset=["grain"])[["state", *cols, "grain_method"]]
        us_row = t[t["state"].str.startswith("US")].iloc[0]
        return past, states, {c: float(us_row[c]) for c in cols}, {
            "2017-2025": "reproduced kernelag.deliverable (grain series)", "2026": "reproduced deliverable_2026.csv"}
    g = grains[key]
    past = g["past"].rename(columns={"pred": "predicted", "method": "grain_method"})
    return past[["year", "state", "predicted", "grain_method"]], g["fc_states"], g["fc_us"], g["sources"]


def silage_part(key: str, rep: dict, silages: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    if key == "SC":
        ours = rep["ours"][rep["ours"]["series"] == "silage"]
        t = rep["table_2026"]
        cols = ["silage", "silage_lo80", "silage_hi80", "silage_lo90", "silage_hi90"]
        us_row = t[t["state"].str.startswith("US")].iloc[0]
        return ours[["year", "state", "predicted"]], t[~t["state"].str.startswith("US")][["state", *cols]], \
            {c: float(us_row[c]) for c in cols}, {"2017-2025": "reproduced kernelag.deliverable (silage series)",
                                                  "2026": "reproduced deliverable_2026.csv"}
    s = silages[key]
    return s["past"].rename(columns={"pred": "predicted"})[["year", "state", "predicted"]], s["fc_states"], \
        s["fc_us"], s["sources"]


def state_rows(comparison: pd.DataFrame) -> pd.DataFrame:
    """The scored state rows of a comparison table (US rows dropped)."""
    return comparison[~comparison["state"].str.startswith("US")]


def check_states(part: pd.DataFrame, reference: pd.DataFrame, label: str) -> None:
    """The candidate must cover exactly the deliverable's states in every year (same US sum)."""
    for year in YEARS:
        mine = set(part.loc[part["year"] == year, "state"])
        ref = set(reference.loc[reference["year"] == year, "state"])
        if mine != ref or part.loc[part["year"] == year, "predicted"].isna().any():
            raise SystemExit(f"{label} {year}: state set differs from the deliverable's "
                             f"(missing {sorted(ref - mine)}, extra {sorted(mine - ref)})")


def table_2026(grain_states: pd.DataFrame, grain_us: dict, silage_states: pd.DataFrame, silage_us: dict,
               silage_key: str) -> pd.DataFrame:
    """The deliverable's 2026 layout: US row first, then states by silage acres, acres rounded to 100."""
    columns = ["year", "state", "silage", "silage_lo80", "silage_hi80", "silage_lo90", "silage_hi90",
               "grain", "grain_lo80", "grain_hi80", "grain_lo90", "grain_hi90", "silage_method", "grain_method"]
    states = silage_states.merge(grain_states, on="state", how="left")
    extra = set(grain_states["state"]) - set(silage_states["state"])
    if extra:
        raise SystemExit(f"grain states without a silage row in 2026: {sorted(extra)}")
    states = states.assign(year=FORECAST_YEAR, silage_method=SILAGE_METHOD[silage_key])
    us = {"year": FORECAST_YEAR, "state": US_ROW, "silage_method": SILAGE_METHOD[silage_key], "grain_method": "sum",
          **silage_us, **grain_us}
    # stable sort: the deliverable's SC rows already come in its order (descending unrounded acres)
    out = pd.concat([pd.DataFrame([us]), states.sort_values("silage", ascending=False, kind="stable")],
                    ignore_index=True)
    out = out.reindex(columns=columns)
    acre = [c for c in columns if c.startswith(("silage", "grain")) and not c.endswith("method")]
    out[acre] = out[acre].astype(float).round(-2)
    return out


def add_signed_means(summary: dict) -> None:
    """Mean signed US error per period (from the same rounded per-year values summarize averages)."""
    for series in ("grain", "silage"):
        by_year = summary[series]["by_year"]
        for name, years in (("backtest_2017_2024", BACKTEST), ("held_out_2025", [INFO_YEAR])):
            values = [by_year[y]["us_error_pct"] for y in years if y in by_year]
            summary[series][name]["us_error_signed_mean_pct"] = round(float(np.mean(values)), 2)


def build_combo(gkey: str, skey: str, rep: dict, grains: dict, silages: dict) -> dict:
    ours, scored = rep["ours"], state_rows(rep["comparison"])
    gpast, gstates, gus, gsrc = grain_part(gkey, rep, grains)
    spast, sstates, sus, ssrc = silage_part(skey, rep, silages)
    gpast, spast = gpast[gpast["year"].isin(YEARS)], spast[spast["year"].isin(YEARS)]
    check_states(gpast, scored[scored["series"] == "grain"], f"{gkey} grain")
    check_states(spast, scored[scored["series"] == "silage"], f"{skey} silage")
    rows = []
    for series, part in (("grain", gpast), ("silage", spast)):
        last = ours[ours["series"] == series][["year", "state", "last"]]
        part = part.merge(last, on=["year", "state"], how="left", validate="one_to_one")
        rows.append(part.assign(series=series))
    mine = pd.concat(rows, ignore_index=True)
    comparison = dlv.compare(mine, rep["truth"])
    summary = dlv.summarize(comparison)
    add_signed_means(summary)
    name = combo_name(gkey, skey)
    summary["combination"] = {"name": name, "grain": gkey, "silage": skey, "tier": tier_of(gkey, skey),
                              "grain_tier": GRAIN[gkey][0], "silage_tier": SILAGE[skey][0],
                              "grain_model": GRAIN[gkey][1], "silage_model": SILAGE[skey][1],
                              "grain_sources": gsrc, "silage_sources": ssrc}
    summary["truth_check"] = rep["summary"]["truth_check"]
    fc = table_2026(gstates, gus, sstates, sus, skey)
    return {"name": name, "comparison": comparison, "summary": summary, "table_2026": fc}


# --- step 4: scorecard ---------------------------------------------------------------------------------------------

def scorecard_rows(combos: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_year, rows = [], []
    for c in combos:
        s, meta = c["summary"], c["summary"]["combination"]
        for year in YEARS:
            g, si = s["grain"]["by_year"][year], s["silage"]["by_year"][year]
            by_year.append({"combination": c["name"], "tier": meta["tier"], "year": year,
                            "period": "backtest" if year in BACKTEST else "information_only",
                            "grain_state_wape_pct": g["state_wape_pct"], "grain_us_error_pct": g["us_error_pct"],
                            "silage_state_wape_pct": si["state_wape_pct"], "silage_us_error_pct": si["us_error_pct"],
                            "grain_states": g["states"], "silage_states": si["states"], "truth": g["truth"]})
        us = c["table_2026"].iloc[0]
        gb, sb = s["grain"]["backtest_2017_2024"], s["silage"]["backtest_2017_2024"]
        gh, sh = s["grain"]["held_out_2025"], s["silage"]["held_out_2025"]
        rows.append({
            "combination": c["name"], "grain": meta["grain"], "silage": meta["silage"], "tier": meta["tier"],
            "grain_state_wape_2017_2024": gb["state_wape_pct"], "grain_abs_us_2017_2024": gb["us_error_pct"],
            "grain_signed_us_2017_2024": gb["us_error_signed_mean_pct"],
            "silage_state_wape_2017_2024": sb["state_wape_pct"], "silage_abs_us_2017_2024": sb["us_error_pct"],
            "silage_signed_us_2017_2024": sb["us_error_signed_mean_pct"],
            "grain_state_wape_2025": gh["state_wape_pct"], "grain_signed_us_2025": gh["us_error_signed_mean_pct"],
            "silage_state_wape_2025": sh["state_wape_pct"], "silage_signed_us_2025": sh["us_error_signed_mean_pct"],
            "us_grain_2026": us["grain"], "us_grain_2026_lo80": us["grain_lo80"], "us_grain_2026_hi80": us["grain_hi80"],
            "us_silage_2026": us["silage"], "us_silage_2026_lo80": us["silage_lo80"],
            "us_silage_2026_hi80": us["silage_hi80"],
        })
    card = pd.DataFrame(rows)
    card["sum_of_four_2017_2024"] = card[["grain_state_wape_2017_2024", "grain_abs_us_2017_2024",
                                          "silage_state_wape_2017_2024", "silage_abs_us_2017_2024"]].sum(axis=1).round(2)
    card["tier_rank"] = card["tier"].map(TIER_ORDER)
    card = card.sort_values(["sum_of_four_2017_2024", "tier_rank"]).drop(columns="tier_rank").reset_index(drop=True)
    return card, pd.DataFrame(by_year)


# --- step 5: monthly grid ------------------------------------------------------------------------------------------

def monthly_sources() -> dict:
    """(crop, key) -> table asof, year, state, pred, 2017-2024, from the saved monthly-style files."""
    monthly = pd.read_csv(MONTHLY_STATE_YEAR)
    gv = pd.read_csv(GV_BACKTEST)
    scb = pd.read_csv(SCB_BACKTEST)

    def pick(frame, model):
        part = frame[(frame["model"] == model) & frame["year"].isin(BACKTEST)]
        return part[["asof", "year", "state", "pred"]]

    return {("grain", "NASS"): (pick(monthly, "nass_latest"), "monthly: nass_latest"),
            ("grain", "A-G3"): (pick(monthly, "g3_fsa_ratio_multi"), "monthly: g3_fsa_ratio_multi"),
            ("grain", "g9"): (pick(gv, "g9_national_reconciliation"), "grain_variants: g9_national_reconciliation"),
            ("silage", "A-S3"): (pick(monthly, "s3_fsa_residual"), "monthly: s3_fsa_residual"),
            ("silage", "SC"): (pick(scb, "SC"), "silage_combos: SC (Sep-Nov only)"),
            ("silage", "SC_A"): (pick(scb, "SC_A"), "silage_combos: SC_A (Sep-Nov only)"),
            ("silage", "SC_B"): (pick(scb, "SC_B"), "silage_combos: SC_B (Sep-Nov only)"),
            ("silage", "v1_geo"): (pick(scb, "v1_geo"), "silage_combos: v1_geo (Sep-Nov only)")}


def grid_metrics(preds: pd.DataFrame, truth: pd.DataFrame, reference: pd.DataFrame, series: str) -> dict:
    """asof -> (mean state WAPE, mean |US|, mean signed US) over 2017-2024 on the deliverable's states and truth."""
    out = {}
    t = truth[truth["series"] == series][["year", "state", "actual"]]
    for asof in MONTHS:
        part = preds[preds["asof"] == asof]
        if part.empty:
            continue
        wapes, uss = [], []
        for year in BACKTEST:
            ref_states = set(reference.loc[reference["year"] == year, "state"])
            p = part[part["year"] == year]
            if set(p["state"]) != ref_states:
                raise SystemExit(f"monthly grid {series} {asof} {year}: state set differs from the deliverable's")
            j = p.merge(t, on=["year", "state"], how="inner", validate="one_to_one")
            wapes.append(100 * (j["pred"] - j["actual"]).abs().sum() / j["actual"].sum())
            uss.append(100 * (j["pred"].sum() / j["actual"].sum() - 1))
        out[asof] = (float(np.mean(wapes)), float(np.mean(np.abs(uss))), float(np.mean(uss)))
    return out


def monthly_grid(gkey: str, skey: str, truth: pd.DataFrame, scored: pd.DataFrame, sources: dict) -> pd.DataFrame:
    g_pred, g_src = sources[("grain", gkey)]
    s_pred, s_src = sources[("silage", skey)]
    g = grid_metrics(g_pred, truth, scored[scored["series"] == "grain"], "grain")
    s = grid_metrics(s_pred, truth, scored[scored["series"] == "silage"], "silage")
    rows = []
    for asof in MONTHS:
        rows.append({"combination": combo_name(gkey, skey), "date": f"15 {asof.capitalize()}",
                     "grain_state_wape": g.get(asof, (np.nan,) * 3)[0], "grain_abs_us": g.get(asof, (np.nan,) * 3)[1],
                     "grain_signed_us": g.get(asof, (np.nan,) * 3)[2],
                     "silage_state_wape": s.get(asof, (np.nan,) * 3)[0],
                     "silage_abs_us": s.get(asof, (np.nan,) * 3)[1], "silage_signed_us": s.get(asof, (np.nan,) * 3)[2],
                     "grain_source": g_src, "silage_source": s_src})
    frame = pd.DataFrame(rows)
    for label, keys in (("Average Jul-Dec (6 dates)", MONTHS), ("Average Aug-Dec (5 dates)", MONTHS[1:]),
                        ("Average Sep-Nov (3 dates)", ["sep", "oct", "nov"])):
        sub = frame[frame["date"].isin([f"15 {k.capitalize()}" for k in keys])]
        avg = {"combination": combo_name(gkey, skey), "date": label, "grain_source": g_src, "silage_source": s_src}
        for col in ["grain_state_wape", "grain_abs_us", "grain_signed_us", "silage_state_wape", "silage_abs_us",
                    "silage_signed_us"]:
            avg[col] = sub[col].mean() if sub[col].notna().all() else np.nan   # only when every date exists
        frame = pd.concat([frame, pd.DataFrame([avg])], ignore_index=True)
    return frame


# --- step 6: SCORECARD.md ------------------------------------------------------------------------------------------

def fmt_m(value: float) -> str:
    return "n/a" if pd.isna(value) else f"{value / 1e6:.3f}M"


def cell(a: float, b: float) -> str:
    return "n/a" if pd.isna(a) or pd.isna(b) else f"{a:.2f} / {b:.2f}"


def write_markdown(card: pd.DataFrame, grids: list[tuple[str, pd.DataFrame]], rep_checks: dict, grain_checks: dict,
                   silage_checks: dict) -> str:
    best_all = card.iloc[0]["combination"]
    tier_a = card[card["tier"] == "A"]
    best_a = tier_a.iloc[0]["combination"] if len(tier_a) else None
    lines = [
        "# Submission preview: 15 grain x silage combinations",
        "",
        "Generated by `preview.py` (this folder). Truth = the organizer CSV "
        "(`jupyter/workspace/02_QuickStats/corn_grain_silage_acres_2012_2025.csv`, read by "
        "`kernelag.deliverable.organizer_truth`); 2017 and 2022 (Census years, no state survey rows in that CSV) come "
        "from the pipeline's NASS copy, exactly as in the current deliverable. Grain: 41 states; silage: 48 states; "
        "the same states and truth for every combination.",
        "",
        "**Reproduction of the current deliverable** (NASS pass-through + SC, rebuilt in memory with "
        "`kernelag.deliverable`'s functions): "
        f"deliverable_comparison.csv text-identical: **{rep_checks['deliverable_comparison_csv_text_identical']}**; "
        f"deliverable_2026.csv text-identical: **{rep_checks['deliverable_2026_csv_text_identical']}** (every byte "
        "equal once the stored copies' CRLF line endings are read as LF; the deliverable's code writes LF); "
        f"deliverable_summary.json identical (static notes text excepted): "
        f"**{rep_checks['deliverable_summary_json_identical_except_notes']}**. "
        "The `NASS__SC` row below therefore equals `data/models/deliverable_summary.json`.",
        "",
        "Cells: state = mean state WAPE %; US = mean |US total error| % with the mean signed error in brackets "
        "(+ = too many acres). 2025 is shown once, as information (it chose nothing): state WAPE % / signed US error %. "
        "2026 = US total, million acres, with the 80% interval. Tier = weakest part (A: no current-year NASS data; "
        "B: NASS-informed without NASS's grain forecast; C: uses NASS's grain forecast).",
        "",
        "Ranking rule (fixed in `preview.py` before this table was first produced; the components' own 2017-2024 "
        "scores were already known from their folders' READMEs): lowest sum of the four 2017-2024 numbers (grain "
        "state + grain |US| + silage state + silage |US|), equal weights, sum rounded to 0.01; ties broken by the "
        "better tier. Rows are sorted by that sum. **Bold** = best overall and best Tier A. Because the grain and "
        "silage parts are scored separately, a combination's sum is its grain part plus its silage part: the best "
        "combination is the best grain option with the best silage option. Exact ties at 0.01: "
        + ("; ".join(" = ".join(group["combination"]) + f" ({total:.2f}, tiers {' / '.join(group['tier'])})"
                     for total, group in card.groupby("sum_of_four_2017_2024", sort=True) if len(group) > 1)
           or "none") + ".",
        "",
        "| Combination | Grain 2017-24 state / US | Silage 2017-24 state / US | 2025 grain state / US | "
        "2025 silage state / US | 2026 US grain | 2026 US silage | Sum of four | Tier |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in card.iterrows():
        name = r["combination"]
        tags = []
        if name == best_all:
            tags.append("best overall")
        if name == best_a:
            tags.append("best Tier A")
        label = f"**{name}** ({', '.join(tags)})" if tags else name
        b = "**" if tags else ""
        row = [label,
               f"{b}{r['grain_state_wape_2017_2024']:.2f} / {r['grain_abs_us_2017_2024']:.2f} "
               f"({r['grain_signed_us_2017_2024']:+.2f}){b}",
               f"{b}{r['silage_state_wape_2017_2024']:.2f} / {r['silage_abs_us_2017_2024']:.2f} "
               f"({r['silage_signed_us_2017_2024']:+.2f}){b}",
               f"{r['grain_state_wape_2025']:.2f} / {r['grain_signed_us_2025']:+.2f}",
               f"{r['silage_state_wape_2025']:.2f} / {r['silage_signed_us_2025']:+.2f}",
               f"{fmt_m(r['us_grain_2026'])} [{fmt_m(r['us_grain_2026_lo80'])}, {fmt_m(r['us_grain_2026_hi80'])}]",
               f"{fmt_m(r['us_silage_2026'])} [{fmt_m(r['us_silage_2026_lo80'])}, {fmt_m(r['us_silage_2026_hi80'])}]",
               f"{b}{r['sum_of_four_2017_2024']:.2f}{b}", f"{b}{r['tier']}{b}"]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "Per year: `out/scorecard_by_year.csv`. Per combination, in the deliverable's format: "
              "`out/<combination>/deliverable_2026.csv`, `deliverable_comparison.csv`, `deliverable_summary.json`.", ""]

    for title, grid in grids:
        lines += [f"## Monthly grid: {title}", "",
                  f"2017-2024, same states and truth as above. Cells: state % / US % (mean |US|). Grain source: "
                  f"{grid['grain_source'].iloc[0]}; silage source: {grid['silage_source'].iloc[0]}. "
                  "n/a = no saved prediction for that date (averages only where every date exists).", "",
                  "| Date | Grain | Silage |", "|---|---|---|"]
        for _, r in grid.iterrows():
            lines.append(f"| {r['date']} | {cell(r['grain_state_wape'], r['grain_abs_us'])} | "
                         f"{cell(r['silage_state_wape'], r['silage_abs_us'])} |")
        lines.append("")

    lines += ["## Where each number comes from", ""]
    for key, (tier, label, _) in GRAIN.items():
        lines.append(f"- Grain `{key}` (Tier {tier}): {label}.")
    for key, (tier, label, _) in SILAGE.items():
        lines.append(f"- Silage `{key}` (Tier {tier}): {label}.")
    lines += [
        "- NASS pass-through and SC: the reproduced deliverable for 2017-2025 and 2026.",
        "- A-G3 2017-2024: `ownModels/monthly/out/monthly_by_state_year.csv` (corrected FSA dates). g9 2017-2024: "
        "`variations/grain_variants/out/by_state_year.csv`. SC_A, SC_B, A-S3, v1_geo 2017-2024: "
        "`variations/silage_combos/out/backtest_by_state_year.csv`.",
        "- 2025 for g9, SC_A, SC_B, A-S3 and v1_geo is in no saved file (those folders kept 2025 out); for A-G3 only "
        "the grain folder's pre-fix `score_2025_information_only.csv` has it. All six are recomputed here by "
        "importing the owners' code unchanged, after checking that the same recomputation reproduces their saved "
        "2017-2024 and 2026 rows:",
    ]
    for key, c in grain_checks.items():
        lines.append(f"  - {key}: max |diff| vs saved 2017-2024 = {c['vs_saved_2017_2024']['max_abs_diff_acres']:.3f} "
                     f"acre, vs saved 2026 = {c['vs_grain_variants_forecast_2026']['max_abs_diff_acres']:.3f} acre; "
                     f"2025 FSA file {c['fsa_file_2025']} (data {c['fsa_file_2025_data_as_of']}).")
    for key, c in silage_checks.items():
        extra = ""
        if "vs_deliverable_2017_2025" in c:
            extra = f", vs the deliverable 2017-2025 = {c['vs_deliverable_2017_2025']['max_abs_diff_acres']:.6f} acre"
        lines.append(f"  - {key}: max |diff| vs saved 2017-2024 = {c['vs_saved_2017_2024']['max_abs_diff_acres']:.3f} "
                     f"acre, vs saved 2026 = {c['vs_saved_2026']['max_abs_diff_acres']:.3f} acre{extra}.")
    a3 = grain_checks["A-G3"]
    lines += [
        "- 2026 A-G3 and g9 points and 80% intervals: `variations/grain_variants/out/forecast_2026.csv` (run through "
        "the monthly harness with corrected FSA dates; equal to the recomputation). The grain folder's older files "
        "from before the FSA date fix, `forecast_2026.csv` and `score_2025_information_only.csv`, keep 6 significant "
        "digits; rounded to that precision the recomputation equals them (max |diff| "
        f"{a3['pre_fix_2026_vs_recomputed_at_6_significant_digits']['max_abs_diff_acres']:.1f} and "
        f"{a3['pre_fix_2025_vs_recomputed_at_6_significant_digits']['max_abs_diff_acres']:.1f} acres; unrounded "
        f"{a3['pre_fix_grain_forecast_2026_vs_recomputed']['max_abs_diff_acres']:.0f} and "
        f"{a3['pre_fix_grain_score_2025_vs_recomputed']['max_abs_diff_acres']:.0f} acres). So the date fix changes "
        "neither the 2025 nor the 2026 A-G3 numbers at 15 Nov (both use the same FSA file before and after).",
        "- The 2017-2024 means are computed exactly as `kernelag.deliverable.summarize` computes them: the mean of "
        "per-year values already rounded to 0.01. This can differ by 0.01 from a folder's own unrounded mean "
        "(v1_geo silage |US| is 3.69 here, 3.68 in silage_combos: 3.6850 vs 3.6835).",
        "- 2026 silage intervals: SC from the deliverable (state 80/90%, US 80/90%); SC_A, SC_B, A-S3, v1_geo from "
        "silage_combos (state 80/90%, US 80% only). Grain 90% intervals exist only for the NASS pass-through.",
        "",
        "## Caveats",
        "",
        "- 8 backtest years. Differences of a few hundredths of a point between combinations are not distinguishable "
        "from noise; the silage options span about 0.3 point of state WAPE and 0.7 point of |US|.",
        "- The ranking rule weights the four numbers equally; another weighting can reorder close rows.",
        "- A-G3, g9, SC_A, SC_B, A-S3 and v1_geo were selected or tuned on 2012-2024 or 2017-2024 by their own "
        "folders; 2025 entered none of them. The 2025 columns are a single year.",
        "- Monthly grids: SC, SC_A, SC_B and v1_geo have saved predictions for 15 Sep / Oct / Nov only "
        "(silage_combos); NASS, A-G3, g9 and A-S3 have all six dates (monthly and grain_variants folders).",
        "- Current-vintage inputs throughout (a replay, not archived real-time runs), as in the deliverable.",
    ]
    return "\n".join(lines) + "\n"


# --- main ----------------------------------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lean", action="store_true", help="kernelag.deliverable's lean table (same numbers)")
    parser.add_argument("--cache", type=Path, help="pickle of the recomputed candidate tables (scratch use only): "
                        "read if it exists, else written")
    args = parser.parse_args()
    np.seterr(all="ignore")
    OUT.mkdir(parents=True, exist_ok=True)

    rep = reproduce_deliverable(args.lean)
    report = {"step1_reproduce_current_deliverable": rep["checks"]}
    if not rep["checks"]["all_identical"]:
        (OUT / "reproduction.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
        raise SystemExit(f"current deliverable NOT reproduced; stopping: {rep['checks']}")
    print("step 1: current deliverable reproduced exactly")

    years = list(range(2017, FORECAST_YEAR + 1))
    if args.cache is not None and args.cache.exists():
        grain_re, silage_re = pd.read_pickle(args.cache)
    else:
        grain_re, silage_re = recompute_grain(years), recompute_silage(years)
        if args.cache is not None:
            pd.to_pickle((grain_re, silage_re), args.cache)
    grains, grain_checks = grain_candidates(grain_re)
    silages, silage_checks = silage_candidates(silage_re, rep["comparison"])
    report["step2_grain_recomputation"] = grain_checks
    report["step2_silage_recomputation"] = silage_checks
    print("step 2: recomputations reproduce the saved rows")

    combos = [build_combo(g, s, rep, grains, silages) for g in GRAIN for s in SILAGE]
    base = next(c for c in combos if c["name"] == combo_name("NASS", "SC"))
    stored = pd.read_csv(STORED_COMPARISON)
    stored_rows = csv_text(stored[stored["series"].isin(["grain", "silage"])].reset_index(drop=True))
    mine_text = csv_text(pd.read_csv(io.StringIO(csv_text(base["comparison"].round(ACRE_ROUND)))))
    stored_summary = json.loads(STORED_SUMMARY.read_text(encoding="utf-8"))
    base_summary = json.loads(json.dumps(base["summary"]))
    same_summary = all(
        {k: v for k, v in base_summary[s][p].items() if k != "us_error_signed_mean_pct"} == stored_summary[s][p]
        for s in ("grain", "silage") for p in ("backtest_2017_2024", "held_out_2025")) and all(
        base_summary[s]["by_year"] == stored_summary[s]["by_year"] for s in ("grain", "silage"))
    report["step3_baseline_combination_NASS__SC"] = {
        "comparison_equals_stored_grain_and_silage_rows": mine_text == stored_rows,
        "summary_equals_stored_grain_and_silage": bool(same_summary),
        "deliverable_2026_equals_stored": csv_text(base["table_2026"]) == stored_text(STORED_2026),
    }
    if not all(report["step3_baseline_combination_NASS__SC"].values()):
        (OUT / "reproduction.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
        raise SystemExit(f"baseline combination differs from the stored deliverable: "
                         f"{report['step3_baseline_combination_NASS__SC']}")

    for c in combos:
        folder = OUT / c["name"]
        folder.mkdir(parents=True, exist_ok=True)
        c["table_2026"].to_csv(folder / f"deliverable_{FORECAST_YEAR}.csv", index=False, lineterminator="\n")
        c["comparison"].round(ACRE_ROUND).to_csv(folder / "deliverable_comparison.csv", index=False,
                                                 lineterminator="\n")
        (folder / "deliverable_summary.json").write_text(json.dumps(c["summary"], indent=1) + "\n", encoding="utf-8")

    card, by_year = scorecard_rows(combos)
    card.to_csv(OUT / "scorecard.csv", index=False, lineterminator="\n", float_format="%.2f")
    by_year.to_csv(OUT / "scorecard_by_year.csv", index=False, lineterminator="\n", float_format="%.2f")

    sources = monthly_sources()
    best_all = card.iloc[0]
    tier_a = card[card["tier"] == "A"]
    picks = [("recommended = best overall, " + best_all["combination"], best_all["grain"], best_all["silage"])]
    if len(tier_a) and tier_a.iloc[0]["combination"] != best_all["combination"]:
        picks.append(("best Tier A, " + tier_a.iloc[0]["combination"], tier_a.iloc[0]["grain"],
                      tier_a.iloc[0]["silage"]))
    grids = [(title, monthly_grid(g, s, rep["truth"], state_rows(rep["comparison"]), sources))
             for title, g, s in picks]
    for title, grid in grids:   # the 15 Nov row must equal the scorecard's 2017-2024 means
        row = card[card["combination"] == grid["combination"].iloc[0]].iloc[0]
        nov = grid[grid["date"] == "15 Nov"].iloc[0]
        gaps = [abs(nov["grain_state_wape"] - row["grain_state_wape_2017_2024"]),
                abs(nov["grain_abs_us"] - row["grain_abs_us_2017_2024"]),
                abs(nov["silage_state_wape"] - row["silage_state_wape_2017_2024"]),
                abs(nov["silage_abs_us"] - row["silage_abs_us_2017_2024"])]
        report.setdefault("step5_monthly_grid_nov_vs_scorecard_max_gap", {})[title] = float(np.nanmax(gaps))
    pd.concat([g for _, g in grids], ignore_index=True).to_csv(OUT / "monthly_grid.csv", index=False,
                                                               lineterminator="\n", float_format="%.3f")

    (OUT / "SCORECARD.md").write_text(write_markdown(card, grids, rep["checks"], grain_checks, silage_checks),
                                      encoding="utf-8", newline="\n")
    (OUT / "reproduction.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    print(card.drop(columns=[c for c in card.columns if c.startswith("us_")]).to_string(index=False))
    for title, grid in grids:
        print(title)
        print(grid.drop(columns=["grain_source", "silage_source", "combination"]).round(2).to_string(index=False))
    print(json.dumps(report, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
