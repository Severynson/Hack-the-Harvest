"""Put the Tier A/B acreage models and the field models on the model board (branch `board`).

The board picks up any folder holding board_backtest.csv, board_forecast.csv, board_models.json and
board_field.csv (see board/README.md on that branch). This script only reformats results the models
already wrote; it fits nothing and tunes nothing. Model names are the IDs in board/catalog.json
(A-G3, B-S5b, ...), so the board's Tier A / B tab fills them in.

    .venv/Scripts/python.exe test_models/boardExport/export.py

Sources (all read-only):
    test_models/ownModels/{grain,silage}/out           A-G1..A-G5, A-S1..A-S6
    test_models/ownModels/tierB/{grain,silage}/out     B-G0..B-G7, B-S0..B-S5b
    test_models/variations/grain_variants/out          A-G9 (g9_national_reconciliation)
    test_models/variations/silage_combos/out           A-S7 (SC_A: smoothed level + Drought Monitor chopping)
    test_models/variations/submission_preview/out      2025 state rows for A-G9, A-S3, A-S7
    test_models/featureTests, fieldMultiYear, variations/field_variants   field classifiers on Maryland

2025 rows are information only (scored once after selection); the board holds 2025 out by default.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from kernelag.context import STATE_NAMES  # noqa: E402

TM = REPO / "test_models"
OUT = Path(__file__).resolve().parent / "out"
ASOF = ["sep", "oct", "nov"]
CODE = {name: code for code, name in STATE_NAMES.items()}

# board id -> (target, source csv, name column, name in that file, asof column)
OWN, TB, VAR = TM / "ownModels", TM / "ownModels" / "tierB", TM / "variations"
BACKTESTS = {
    **{k: ("grain", OWN / "grain/out/backtest_by_state_year.csv", "candidate", v, "asof") for k, v in {
        "A-G1": "g1_fsa_ratio", "A-G2": "g2_fsa_planted_share", "A-G3": "g3_fsa_ratio_multi",
        "A-G4": "g4_fsa_plus_stress", "A-G5": "g5_fsa_ratio_vintage"}.items()},
    "A-G9": ("grain", VAR / "grain_variants/out/by_state_year.csv", "model", "g9_national_reconciliation", "asof"),
    **{k: ("silage", OWN / "silage/out/backtest_by_state_year.csv", "candidate", v, "asof_key") for k, v in {
        "A-S1": "s1_reversion_only", "A-S2": "s2_fsa_ratio_highcov", "A-S3": "s3_fsa_residual",
        "A-S4": "s4_reversion_plus_switch", "A-S5": "s5_fsa_silage_share", "A-S6": "s6_highcov_plus_switch"}.items()},
    "A-S7": ("silage", VAR / "silage_combos/out/backtest_by_state_year.csv", "model", "SC_A", "asof"),
    "B-S6": ("silage", VAR / "silage_combos/out/backtest_by_state_year.csv", "model", "SC_B", "asof"),
    **{k: ("grain", TB / "grain/out/backtest_by_state_year.csv", "candidate", v, "asof") for k, v in {
        "B-G0": "b0_planted_x_share", "B-G1": "b1_planted_x_fsa_share", "B-G2": "b2_ridge",
        "B-G3": "b3_gbt_monotone", "B-G4": "b4_daniel_gbt_independent", "B-G5": "b5_planted_x_fsa_share_median",
        "B-G6": "b6_b1_plus_stress", "B-G7": "b7_blend_b5_fsa_level"}.items()},
    **{k: ("silage", TB / "silage/out/backtest_by_state_year.csv", "candidate", v, "asof_key") for k, v in {
        "B-S0": "c0_reversion_only", "B-S1": "c1_planted_fsa_ridge", "B-S2": "c2_plus_stress",
        "B-S3": "c3_plus_dairy", "B-S4": "c4_monotone_gbt", "B-S5": "c5_residual_shrunk",
        "B-S5b": "c5b_residual_fsa_planted_pre_june"}.items()},
}

A, B = ["FSA", "NASS history"], ["FSA", "NASS history", "NASS current year"]
CARDS = {
    "A-G1": (A, "Acres certified to FSA for grain x last year's NASS/FSA grain ratio."),
    "A-G2": (A, "FSA all-corn planted x last year's NASS grain / FSA planted."),
    "A-G3": (A, "Like A-G1 with the median NASS/FSA ratio of the last three years. Selected Tier A grain."),
    "A-G4": (A + ["weather", "insurance"], "A-G1 corrected by drought and insured losses."),
    "A-G5": (A, "Ratio against last year's FSA file from the same point in the season."),
    "A-G9": (A, "Headline grain. A-G3's state split, scaled to one national FSA x NASS/FSA ratio total. Passes the 2 SE rule vs A-G3 (not 3 SE). Ties NASS's November forecast (1.69% vs 1.66% state, 2017-24)."),
    "A-S1": (["NASS history"], "Last year's acres pulled toward the 3-year average."),
    "A-S2": (A, "FSA's silage change where FSA captures >= 75% of silage; A-S1 elsewhere."),
    "A-S3": (A, "(FSA planted - our grain) x last year's silage share of non-grain, blended with A-S1. Selected by the pre-registered rule."),
    "A-S4": (A + ["weather", "insurance"], "A-S1 adjusted by drought, insured losses and FSA changes."),
    "A-S5": (A, "Change in FSA's silage share applied to last year."),
    "A-S6": (A + ["weather", "insurance"], "A-S2 in high-coverage states, A-S4 elsewhere."),
    "A-S7": (["NASS history", "weather"], "Drought scenario, not the headline. Smoothed state level (EWMA in logs) + drought chopping: gamma x max(0, D2+ share - 0.10) x last year's grain acres. Tier A twin of smoothed_chopping; scored post hoc."),
    "B-S6": (["NASS history", "NASS current year", "weather"], "Headline silage. Smoothed state level (EWMA in logs) + drought chopping from NASS's in-season yield shortfall x last year's final grain acres. Uses NASS's yield forecast, never its acreage forecast. Ties the Tier C smoothed_chopping model."),
    "B-G0": (B, "NASS planted x last year's grain share."),
    "B-G1": (B, "NASS planted x this year's FSA grain share x last year's correction."),
    "B-G2": (B + ["weather", "insurance"], "Ridge on FSA share change, yield shock, drought, condition, losses."),
    "B-G3": (B + ["weather", "insurance"], "Monotone boosted trees on the B-G2 inputs."),
    "B-G4": (B + ["weather", "economy"], "Daniel's GBT without NASS's grain forecast (reference)."),
    "B-G5": (B, "B-G1 with the median correction of the last three years."),
    "B-G6": (B + ["weather", "insurance"], "B-G1 corrected by stress signals."),
    "B-G7": (B, "Geometric mean of B-G5 and A-G3. Selected Tier B grain."),
    "B-S0": (["NASS history"], "Reversion, same as A-S1."),
    "B-S1": (B, "Reversion + planted change and FSA non-grain share change."),
    "B-S2": (B + ["weather", "insurance"], "Reversion + yield shock, drought, condition, insured losses."),
    "B-S3": (B + ["economy"], "Reversion + milk-cow change and FSA silage change."),
    "B-S4": (B + ["weather", "economy", "insurance"], "Monotone boosted trees on the B-S2 and B-S3 inputs."),
    "B-S5": (B, "NASS planted - Tier B grain, x last year's silage share."),
    "B-S5b": (B, "B-S5 with FSA-scaled planted where NASS has only March figures. Selected Tier B silage."),
}
METHOD = {"B-G2": "ridge regression", "B-G3": "gradient boosting", "B-G4": "gradient boosting",
          "B-S1": "ridge regression", "B-S2": "ridge regression", "B-S3": "ridge regression",
          "B-S4": "gradient boosting", "B-G7": "ensemble"}


def code(state: str) -> str:
    s = str(state).strip().upper()
    return "US" if s.startswith("US") else CODE.get(s, s)


def backtest_rows() -> pd.DataFrame:
    frames = []
    for model, (target, path, col, name, asof_col) in BACKTESTS.items():
        t = pd.read_csv(path)
        t = t[(t[col] == name) & t[asof_col].isin(ASOF) & t["year"].between(2012, 2024)]
        frames.append(pd.DataFrame({"model": model, "target": target, "year": t["year"].astype(int),
                                    "state": t["state"].map(code), "actual": t["actual"],
                                    "predicted": t["pred"], "asof": t[asof_col]}))
    return pd.concat(frames, ignore_index=True)


def rows_2025() -> pd.DataFrame:
    """State-level 2025 predictions where the folders saved them (information only)."""
    frames = []

    def add(model, target, state, actual, pred):
        t = pd.DataFrame({"model": model, "target": target, "year": 2025, "state": state.map(code),
                          "actual": actual, "predicted": pred, "asof": "nov"})
        frames.append(t[t["state"] != "US"])  # some files carry a national total row; states only

    g = pd.read_csv(OWN / "grain/out/score_2025_information_only.csv")
    g = g[g["candidate"] == "g3_fsa_ratio_multi"]
    add("A-G3", "grain", g["state"], g["actual"], g["pred"])
    for combo, picks in {"g9__SC_A": [("grain", "A-G9"), ("silage", "A-S7")], "g9__A-S3": [("silage", "A-S3")],
                         "g9__SC_B": [("silage", "B-S6")]}.items():
        d = pd.read_csv(VAR / f"submission_preview/out/{combo}/deliverable_comparison.csv")
        for series, model in picks:
            s = d[(d["year"] == 2025) & (d["series"] == series)]
            add(model, series, s["state"], s["actual"], s["predicted"])
    b = pd.read_csv(TB / "grain/out/score_2025_information_only.csv")
    add("B-G7", "grain", b["state"], b["actual"], b["b7_blend_b5_fsa_level"])
    c = pd.read_csv(TB / "silage/out/score_2025_information_only.csv")
    add("B-S5b", "silage", c["state"], c["actual"], c["pred"])
    return pd.concat(frames, ignore_index=True)


def forecast_rows() -> pd.DataFrame:
    rows = []

    def add(model, target, state, pred, lo=None, hi=None):
        rows.append(pd.DataFrame({"model": model, "target": target, "state": pd.Series(state).map(code).values,
                                  "predicted": pd.Series(pred).values,
                                  "lo80": pd.Series(lo).values if lo is not None else float("nan"),
                                  "hi80": pd.Series(hi).values if hi is not None else float("nan")}))

    gv = pd.read_csv(VAR / "grain_variants/out/forecast_2026.csv")
    for model, name in [("A-G3", "g3_fsa_ratio_multi"), ("A-G9", "g9_national_reconciliation")]:
        t = gv[gv["model"] == name]
        add(model, "grain", t["state"], t["pred"], t["lo80"], t["hi80"])
    sa = pd.read_csv(OWN / "silage/out/forecast_2026_all_candidates.csv")
    sa = sa[~sa["state"].str.upper().str.startswith("US")]
    for model in ["A-S1", "A-S2", "A-S4", "A-S5", "A-S6"]:
        add(model, "silage", sa["state"], sa[BACKTESTS[model][3]])
    s3 = pd.read_csv(OWN / "silage/out/forecast_2026.csv")
    add("A-S3", "silage", s3["state"], s3["silage"], s3["silage_lo80"], s3["silage_hi80"])
    scs = pd.read_csv(VAR / "silage_combos/out/forecast_2026.csv")
    uss = pd.read_csv(VAR / "silage_combos/out/forecast_2026_us.csv")
    for model, name in [("A-S7", "SC_A"), ("B-S6", "SC_B")]:
        sc = scs[(scs["model"] == name) & (scs["asof"] == "nov")]
        add(model, "silage", sc["state"], sc["silage"], sc["silage_lo80"], sc["silage_hi80"])
        us = uss[(uss["model"] == name) & (uss["asof"] == "nov")]
        add(model, "silage", ["US"], us["us_silage"], us["us_lo80"], us["us_hi80"])
    ba = pd.read_csv(TB / "grain/out/forecast_2026_all_candidates.csv")
    ba = ba[~ba["state"].str.upper().str.startswith("US")]
    for model in ["B-G0", "B-G1", "B-G2", "B-G3", "B-G5", "B-G6"]:
        add(model, "grain", ba["state"], ba[BACKTESTS[model][3]])
    b7 = pd.read_csv(TB / "grain/out/forecast_2026.csv")
    add("B-G7", "grain", b7["state"], b7["pred"], b7["lo80"], b7["hi80"])
    cu = pd.read_csv(TB / "silage/out/forecast_2026_all_candidates.csv").set_index("candidate")
    for model in ["B-S0", "B-S1", "B-S2", "B-S3", "B-S4", "B-S5"]:
        r = cu.loc[BACKTESTS[model][3]]
        add(model, "silage", ["US"], [r["us_total"]], [r["us_lo80"]], [r["us_hi80"]])
    c5 = pd.read_csv(TB / "silage/out/forecast_2026.csv")
    add("B-S5b", "silage", c5["state"], c5["silage"], c5["silage_lo80"], c5["silage_hi80"])
    return pd.concat(rows, ignore_index=True).round({"predicted": 0, "lo80": 0, "hi80": 0})


def field_rows() -> pd.DataFrame:
    keep = ["model", "evaluated_on", "n_fields", "silage_precision", "silage_recall", "silage_f1",
            "accuracy", "status", "note"]
    md = "Maryland BARC, 44 field-years (proxy labels)"
    frames = []
    s = pd.read_csv(TM / "featureTests/results/field_summary.csv")
    for ev, trained in [("maryland_transfer", "318 Quebec parcels, 2023"), ("maryland_transfer_allqc", "3,128 Quebec parcels, 2023")]:
        t = s[s["evaluation"] == ev]
        frames.append(pd.DataFrame({"model": "feature test: " + t["arm"] + f" ({trained})", "evaluated_on": md,
                                    "n_fields": t["n"], "silage_precision": t["silage_precision"],
                                    "silage_recall": t["silage_recall"], "silage_f1": t["silage_f1"],
                                    "accuracy": t["accuracy"], "status": "feature test",
                                    "note": "balanced accuracy " + t["balanced_accuracy"].astype(str)}))
    m = pd.read_csv(TM / "fieldMultiYear/out/maryland.csv")
    frames.append(pd.DataFrame({"model": "logistic, trained on " + m["trained_on"], "evaluated_on": md,
                                "n_fields": m["n"], "silage_precision": m["silage_precision"],
                                "silage_recall": m["silage_recall"], "silage_f1": m["silage_f1"],
                                "accuracy": m["accuracy"], "status": "fieldMultiYear",
                                "note": "balanced accuracy " + m["balanced_accuracy"].astype(str)}))
    v = pd.read_csv(TM / "variations/field_variants/out/maryland.csv")
    adopted = json.loads((TM / "variations/field_variants/out/decision.json").read_text()).get("adopted")
    frames.append(pd.DataFrame({"model": v["fit"] + " (" + v["trained_on"] + ")", "evaluated_on": md,
                                "n_fields": v["n"], "silage_precision": v["silage_precision"],
                                "silage_recall": v["silage_recall"], "silage_f1": v["silage_f1"],
                                "accuracy": v["accuracy"],
                                "status": v["fit"].map(lambda f: "adopted (pre-registered rule)" if f == adopted else "field variant"),
                                "note": "balanced accuracy " + v["balanced_accuracy"].round(3).astype(str)}))
    h = pd.read_csv(TM / "variations/field_variants/out/holdout_2025.csv")
    frames.append(pd.DataFrame({"model": h["model"] + " (Quebec 2019-2024 fit)",
                                "evaluated_on": "Quebec 2025, 2,826 unseen fields (proxy labels)", "n_fields": h["n"],
                                "silage_precision": h["silage_precision"], "silage_recall": h["silage_recall"],
                                "silage_f1": h["silage_f1"], "accuracy": h["accuracy"],
                                "status": h["model"].map(lambda f: "adopted (pre-registered rule)" if f == adopted else "field variant"),
                                "note": "false-positive rate " + h["false_positive_rate"].round(2).astype(str)
                                        + ", balanced accuracy " + h["balanced_accuracy"].round(3).astype(str)}))
    y = pd.read_csv(TM / "fieldMultiYear/out/loyo_by_year.csv")
    y = y[(y["split"] == "loyo") & (y["model"] == "M")]
    frames.append(pd.DataFrame({"model": "multi-year logistic, held-out year " + y["held_out"].astype(str),
                                "evaluated_on": "Quebec, leave one year out (proxy labels)", "n_fields": y["n"],
                                "silage_precision": y["silage_precision"], "silage_recall": y["silage_recall"],
                                "silage_f1": y["silage_f1"], "accuracy": y["accuracy"], "status": "fieldMultiYear",
                                "note": "balanced accuracy " + y["balanced_accuracy"].astype(str)}))
    return pd.concat(frames, ignore_index=True)[keep]


def check(bt: pd.DataFrame) -> None:
    """The exported rows must reproduce each folder's own per-year scores (ownModels by_year files)."""
    for target, path, col in [("grain", OWN / "grain/out/by_year.csv", "candidate"),
                              ("silage", OWN / "silage/out/by_year.csv", "candidate")]:
        ref = pd.read_csv(path)
        akey = "asof_key" if "asof_key" in ref else "asof"
        for model, (t, _, _, name, _) in BACKTESTS.items():
            if t != target or name not in set(ref[col]) or not model.startswith("A-"):
                continue
            mine = bt[(bt["model"] == model) & (bt["asof"] == "nov") & (bt["year"] <= 2024)]
            wape = mine.groupby("year").apply(lambda g: 100 * (g["predicted"] - g["actual"]).abs().sum() / g["actual"].sum(),
                                              include_groups=False)
            r = ref[(ref[col] == name) & (ref[akey] == "nov")].set_index("year")["state_wape_pct"]
            gap = (wape - r.reindex(wape.index)).abs().max()
            assert gap < 0.01, f"{model}: exported state error differs from {path.name} by {gap:.3f}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bt = pd.concat([backtest_rows(), rows_2025()], ignore_index=True)
    check(bt)
    bt.to_csv(OUT / "board_backtest.csv", index=False)
    fc = forecast_rows()
    fc.to_csv(OUT / "board_forecast.csv", index=False)
    cards = {m: {"signals": s, "description": d, "method": METHOD.get(m, "rule (no fitting)"),
                 "tier": m[0]} for m, (s, d) in CARDS.items()}
    (OUT / "board_models.json").write_text(json.dumps(cards, indent=1))
    fr = field_rows()
    fr.to_csv(OUT / "board_field.csv", index=False)
    print(f"backtest rows {len(bt)} ({bt['model'].nunique()} models), forecast rows {len(fc)}, field rows {len(fr)}")


if __name__ == "__main__":
    main()
