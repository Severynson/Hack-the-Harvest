"""Test the friend's fade rule: silage if the field goes from green to bare in <= 17 days.

Pre-registered in README.md (between the PREREGISTRATION markers), hashed into preregistration.sha256 before
anything was scored. ``score`` refuses to run if that block has changed.

Commands (from the repository root):
    .venv/Scripts/python.exe -I test_models/variations/fade_rule/fade_rule.py build   # features cache
    .venv/Scripts/python.exe -I test_models/variations/fade_rule/fade_rule.py score   # all results -> out/

Features come from kernelag.features.kernel_features (via kernelag.field_model.evidence_table) unchanged.
The only extra per-field quantity is a diagnostic: how many clear looks lie between the last green look
(NDVI >= 0.6) and the first bare look (NDVI <= 0.4), so we can tell a measured fade from a revisit gap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))   # plain script, also under python -I, from the repo root

from kernelag.evaluate import evaluation_table  # noqa: E402
from kernelag.features import drop_dips  # noqa: E402
from kernelag.field_model import evidence_table, load_series  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402

OUT = HERE / "out"
README = HERE / "README.md"
FV = REPO / "test_models" / "variations" / "field_variants"
BEGIN, END = "<!-- PREREGISTRATION:BEGIN -->", "<!-- PREREGISTRATION:END -->"
DEFAULT_CACHE = Path("C:/Users/danie/AppData/Local/Temp/claude/dfe35210c43945cb/"
                     "9bd8cc88-21cc-4423-8ecd-0115ef62e1a4/scratchpad/agents/fade_rule/cache")
CACHE = Path(os.environ.get("FADE_RULE_CACHE", DEFAULT_CACHE))
CACHE_VERSION = "fade-v1"

YEARS = list(range(2019, 2027))
TUNE_YEARS, LATER_YEARS = list(range(2019, 2025)), [2025, 2026]
R1_MAX_FADE = 17      # "under about 2 1/2 weeks"
R2_MAX_DRYDOWN = 21   # "browns slowly over 3-4 weeks": less than 3 weeks of browning = silage
SWEEP = range(7, 36)
GAP_LARGE = 15        # days; three missed 5-day revisits
LATE_DOY = 274        # 1 October: fades ending after this are frost-like in Quebec
KEEP = ["field_id", "year", "label", "is_silage", "n_obs", "peak_ndvi", "peak_doy", "fade_days", "drydown_days",
        "cut_doy", "cut_gap_days", "max_drop", "max_drop_rate", "green_at_cut", "assessable"]


# ------------------------------------------------------------------------------------- pre-registration


def prereg_block() -> str:
    lines = README.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    stripped = [line.strip() for line in lines]
    begin, end = stripped.index(BEGIN), stripped.index(END)
    return "\n".join(lines[begin + 1:end]).strip("\n") + "\n"


def check_prereg() -> str:
    frozen = (HERE / "preregistration.sha256").read_text(encoding="utf-8").split()[0]
    current = hashlib.sha256(prereg_block().encode("utf-8")).hexdigest()
    if frozen != current:
        raise SystemExit(f"pre-registration changed since it was frozen ({frozen} -> {current})")
    return frozen


# ------------------------------------------------------------------------------------------ features


def fade_bracket(series: pd.DataFrame, min_valid: float = 0.5, season_end_doy: int = 300) -> dict:
    """Diagnostic only: the looks bracketing fade_days, the looks between them, or why there is no fade.

    Same filtering and thresholds as kernel_features (valid looks, drop_dips, peak in day 150-260,
    season after the peak up to day 300, green >= 0.6, bare <= 0.4).
    """
    s = series[(series["valid_frac"] >= min_valid) & series["ndvi"].notna()].sort_values("date")
    s = s.assign(doy=s["date"].dt.day_of_year.astype(int)).reset_index(drop=True)
    s = drop_dips(s)
    if len(s) < 4:
        return {"why_no_fade": "fewer than 4 clear looks"}
    window = s[(s["doy"] >= 150) & (s["doy"] <= 260)]
    if window.empty:
        return {"why_no_fade": "no clear look Jun-mid Sep"}
    ip = int(window["ndvi"].idxmax())
    after = s.loc[ip:][lambda d: d["doy"] <= season_end_doy].reset_index(drop=True)
    if len(after) < 2:
        return {"why_no_fade": "fewer than 2 looks after peak"}
    green = after[after["ndvi"] >= 0.6]
    if green.empty:
        return {"why_no_fade": "never NDVI >= 0.6 at/after peak"}
    g_doy = int(green["doy"].iloc[-1])
    brown = after[(after["doy"] > g_doy) & (after["ndvi"] <= 0.4)]
    if brown.empty:
        return {"why_no_fade": "no look NDVI <= 0.4 before day 300", "green_doy": g_doy}
    b_doy = int(brown["doy"].iloc[0])
    between = after[(after["doy"] > g_doy) & (after["doy"] < b_doy)]
    return {"why_no_fade": "", "green_doy": g_doy, "brown_doy": b_doy, "looks_between": len(between)}


def brackets(series: pd.DataFrame) -> pd.DataFrame:
    rows = [{"field_id": str(f), "year": y, **fade_bracket(g)} for (f, y), g in series.groupby(["field_id", "year"])]
    return pd.DataFrame(rows)


def with_brackets(table: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    for column in KEEP:
        if column not in table:
            table[column] = np.nan
    out = table[KEEP].merge(brackets(series), on=["field_id", "year"], how="left", validate="one_to_one")
    out["why_no_fade"] = out["why_no_fade"].fillna("no series")
    measured = out["fade_days"].notna()
    if not (out.loc[measured, "brown_doy"] - out.loc[measured, "green_doy"] == out.loc[measured, "fade_days"]).all():
        raise ValueError("diagnostic bracket disagrees with kernel_features fade_days")
    return out


def digest(paths: list[Path]) -> str:
    h = hashlib.sha256(CACHE_VERSION.encode())
    for path in paths:
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def build_quebec(year: int) -> pd.DataFrame:
    import geopandas as gpd

    data = data_dir()
    label_path, folder = data / "labels" / f"qcm_{year}.parquet", data / "s2_series" / f"qcm_{year}"
    target = CACHE / f"qcm_{year}_{digest([label_path, *sorted(folder.glob('*.csv'))])}.parquet"
    if target.exists():
        return pd.read_parquet(target)
    labels, series = gpd.read_parquet(label_path), load_series(folder)
    table = with_brackets(evidence_table(labels, series), series)
    CACHE.mkdir(parents=True, exist_ok=True)
    table.to_parquet(target, index=False)
    return table


def build_maryland() -> pd.DataFrame:
    import geopandas as gpd

    data = data_dir()
    label_path, folder = data / "labels" / "barc_2021_2023.parquet", data / "s2_series" / "barc_2021_2023"
    target = CACHE / f"barc_{digest([label_path, *sorted(folder.glob('*.csv'))])}.parquet"
    if target.exists():
        return pd.read_parquet(target)
    labels, series = gpd.read_parquet(label_path), load_series(folder)
    table = with_brackets(evaluation_table(labels, series), series)
    CACHE.mkdir(parents=True, exist_ok=True)
    table.to_parquet(target, index=False)
    return table


def load_all(workers: int = 9) -> tuple[pd.DataFrame, pd.DataFrame]:
    with ProcessPoolExecutor(max_workers=workers) as pool:
        md_future = pool.submit(build_maryland)
        qc = pd.concat(list(pool.map(build_quebec, YEARS)), ignore_index=True)
        md = md_future.result()
    for t in (qc, md):
        t["field_id"] = t["field_id"].astype(str)
    return qc, md


# ------------------------------------------------------------------------------------------- rules


def rule_calls(t: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Per rule: (call 1 = silage / 0 = grain with not-assessable as grain, assessable mask)."""
    r1_ok, r2_ok = t["fade_days"].notna().to_numpy(), t["drydown_days"].notna().to_numpy()
    r1 = (t["fade_days"] <= R1_MAX_FADE).to_numpy() & r1_ok
    r2 = (t["drydown_days"] < R2_MAX_DRYDOWN).to_numpy() & r2_ok
    return {"R1": (r1.astype(int), r1_ok), "R2": (r2.astype(int), r2_ok),
            "R3": ((r1 & r2).astype(int), r1_ok & r2_ok)}


def score(truth: np.ndarray, call: np.ndarray) -> dict:
    truth, call = np.asarray(truth).astype(int), np.asarray(call).astype(int)
    tp, fp = int(((call == 1) & (truth == 1)).sum()), int(((call == 1) & (truth == 0)).sum())
    fn, tn = int(((call == 0) & (truth == 1)).sum()), int(((call == 0) & (truth == 0)).sum())

    def ratio(a: float, b: float) -> float:
        return round(a / b, 4) if b else float("nan")

    recall, specificity = ratio(tp, tp + fn), ratio(tn, tn + fp)
    return {"n": len(truth), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "balanced_accuracy": round((recall + specificity) / 2, 4), "silage_precision": ratio(tp, tp + fp),
            "silage_recall": recall, "false_positive_rate": ratio(fp, fp + tn),
            "silage_count_ratio": ratio(tp + fp, tp + fn)}


def rule_rows(region: str, t: pd.DataFrame, by_year: bool) -> list[dict]:
    rows = []
    groups = [("pooled", np.ones(len(t), bool))]
    if by_year:
        groups += [(str(y), (t["year"] == y).to_numpy()) for y in sorted(t["year"].unique())]
    truth = t["is_silage"].to_numpy()
    for name, (call, ok) in rule_calls(t).items():
        for group, mask in groups:
            base = {"region": region, "rule": name, "group": group,
                    "assessable_share": round(float(ok[mask].mean()), 4)}
            rows.append({**base, "scoring": "assessable", **score(truth[mask & ok], call[mask & ok])})
            rows.append({**base, "scoring": "unassessable_as_grain", **score(truth[mask], call[mask])})
    return rows


# --------------------------------------------------------------------------------------- comparisons


def refit_f0_f1() -> tuple[dict, dict, dict]:
    """f0_all and f1_xgb_mono fitted on the 7 selection years with variants.py's own code and cache.

    Returns per-field calls for Maryland and for 2025 (= leave-2025-out), plus the reproduction gates.
    """
    if str(FV) not in sys.path:
        sys.path.insert(0, str(FV))
    import variants as fv

    table, _, _ = fv.load_years(fv.ALL_YEARS)
    full = fv.versions(table)["full"]
    train = full[full["year"].isin(fv.SEL_YEARS)]
    hold = full[full["year"] == fv.HOLDOUT].reset_index(drop=True)
    md, _, _ = fv.maryland_table()
    md_calls, hold_calls, gates = {}, {}, {}
    stored_md = pd.read_csv(FV / "out" / "maryland.csv")
    stored_hold = pd.read_csv(FV / "out" / "holdout_2025.csv")
    for name in ["f0_all", "f1_xgb_mono"]:
        spec = fv.SPECS[name]
        model = fv.fit(spec, train)
        md_call = fv.to_call(fv.predict(spec, model, md))
        hold_call = fv.to_call(fv.predict(spec, model, hold))
        md_calls[name] = md[["field_id", "year"]].assign(call=md_call)
        hold_calls[name] = hold[["field_id", "year"]].assign(call=hold_call)
        want = stored_md[(stored_md["fit"] == name) & (stored_md["trained_on"] == "7 selection years")].iloc[0]
        got = score(md["is_silage"], md_call)
        want_h = stored_hold[stored_hold["model"] == name].iloc[0]
        got_h = score(hold["is_silage"], hold_call)
        gates[name] = {
            "maryland_reproduced": all(int(want[k]) == got[k] for k in ["TP", "FP", "FN", "TN"]),
            "maryland_counts": {k: got[k] for k in ["TP", "FP", "FN", "TN"]},
            "holdout_2025_reproduced": all(int(want_h[k]) == got_h[k] for k in ["TP", "FP", "FN", "TN"]
                                           if k in want_h),
            "holdout_2025_counts": {k: got_h[k] for k in ["TP", "FP", "FN", "TN"]},
        }
    return md_calls, hold_calls, gates


def compare_rows(region: str, t: pd.DataFrame, models: dict[str, np.ndarray], groups: list[tuple[str, np.ndarray]]
                 ) -> list[dict]:
    rows = []
    truth = t["is_silage"].to_numpy()
    for rule, (call, ok) in rule_calls(t).items():
        for group, mask in groups:
            for scoring, sel in [("rule_assessable", mask & ok), ("all_rows_unassessable_as_grain", mask)]:
                base = {"region": region, "rule": rule, "group": group, "scoring": scoring}
                rows.append({**base, "model": rule, **score(truth[sel], call[sel])})
                for name, model_call in models.items():
                    rows.append({**base, "model": name, **score(truth[sel], model_call[sel])})
    return rows


# ------------------------------------------------------------------------------------ information only


def sweep(t: pd.DataFrame) -> pd.DataFrame:
    ok = t["fade_days"].notna().to_numpy()
    truth, fade = t["is_silage"].to_numpy(), t["fade_days"].to_numpy()
    rows = []
    for th in SWEEP:
        call = (np.nan_to_num(fade, nan=1e9) <= th).astype(int)
        rows.append({"threshold": th, **{k: v for k, v in score(truth[ok], call[ok]).items()
                                         if k in ("balanced_accuracy", "silage_precision", "silage_recall",
                                                  "false_positive_rate", "silage_count_ratio")}})
    return pd.DataFrame(rows)


def quantiles(t: pd.DataFrame, region: str) -> list[dict]:
    rows = []
    for column in ["fade_days", "drydown_days", "cut_gap_days"]:
        for label in ["silage", "grain"]:
            v = t.loc[t["label"] == label, column].dropna()
            rows.append({"region": region, "feature": column, "label": label, "n": len(v),
                         "missing": int((t["label"] == label).sum() - len(v)),
                         "p25": v.quantile(0.25) if len(v) else np.nan, "median": v.median() if len(v) else np.nan,
                         "p75": v.quantile(0.75) if len(v) else np.nan,
                         "share_le_17": round(float((v <= 17).mean()), 4) if len(v) else np.nan})
    return rows


def failure_modes(t: pd.DataFrame, region: str) -> list[dict]:
    """Count R1 errors and not-assessable rows by observable cause."""
    call, ok = rule_calls(t)["R1"]
    truth = t["is_silage"].to_numpy()
    gap_only = (t["looks_between"] == 0).to_numpy()
    late = (t["brown_doy"] > LATE_DOY).to_numpy()
    rows = []

    def add(kind: str, cause: str, mask: np.ndarray) -> None:
        rows.append({"region": region, "kind": kind, "cause": cause, "count": int(mask.sum())})

    fp = ok & (call == 1) & (truth == 0)
    add("FP grain called silage", "all", fp)
    add("FP grain called silage", "no look between green and bare (fade = revisit/cloud gap)", fp & gap_only)
    add("FP grain called silage", "fade measured (>=1 look between)", fp & ~gap_only)
    add("FP grain called silage", f"bare look after day {LATE_DOY} (1 Oct, frost-like)", fp & late)
    add("FP grain called silage", f"bare look on/before day {LATE_DOY} (early fast fade or green harvest)",
        fp & ~late)
    add("FP grain called silage", f"cut_gap_days >= {GAP_LARGE}", fp & (t["cut_gap_days"] >= GAP_LARGE).to_numpy())

    fn = ok & (call == 0) & (truth == 1)
    add("FN silage called grain", "all", fn)
    add("FN silage called grain", "no look between green and bare (fade = revisit/cloud gap)", fn & gap_only)
    add("FN silage called grain", f"no look between and gap > {R1_MAX_FADE} d (clouds hid a fast cut)",
        fn & gap_only & (t["fade_days"] > R1_MAX_FADE).to_numpy())
    add("FN silage called grain", "fade measured (>=1 look between: slow browning before the chop)", fn & ~gap_only)
    add("FN silage called grain", "drydown_days >= 21 (cut late, after browning)",
        fn & (t["drydown_days"] >= R2_MAX_DRYDOWN).to_numpy())
    add("FN silage called grain", "green_at_cut < 0.7 (cut after browning)", fn & (t["green_at_cut"] < 0.7).to_numpy())
    add("FN silage called grain", f"cut_gap_days >= {GAP_LARGE}", fn & (t["cut_gap_days"] >= GAP_LARGE).to_numpy())

    for label in ["silage", "grain"]:
        lab = (t["label"] == label).to_numpy()
        for why in sorted(t.loc[~ok & lab, "why_no_fade"].unique()):
            add(f"not assessable, true {label}", why, ~ok & lab & (t["why_no_fade"] == why).to_numpy())

    correct = ok & (call == truth)
    for name, mask in [("correct", correct), ("wrong", ok & (call != truth))]:
        add(f"R1 {name}, assessable", "no look between green and bare", mask & gap_only)
        add(f"R1 {name}, assessable", "fade measured", mask & ~gap_only)
    return rows


def r1_subsets(t: pd.DataFrame, region: str) -> list[dict]:
    """R1 on observation-quality subsets: does the rule work when the fade is actually seen?"""
    call, ok = rule_calls(t)["R1"]
    truth = t["is_silage"].to_numpy()
    measured = (t["looks_between"] >= 1).to_numpy()
    early = (t["brown_doy"] <= LATE_DOY).to_numpy()
    small_gap = (t["cut_gap_days"] <= 10).to_numpy()
    subsets = [("all assessable", ok), ("fade = revisit/cloud gap (no look between)", ok & ~measured),
               ("fade measured (>=1 look between)", ok & measured),
               (f"fade measured, bare look on/before day {LATE_DOY}", ok & measured & early),
               ("fade measured, cut_gap_days <= 10", ok & measured & small_gap),
               (f"fade measured, bare on/before day {LATE_DOY}, cut_gap_days <= 10", ok & measured & early & small_gap)]
    return [{"region": region, "subset": name, **score(truth[m], call[m])} for name, m in subsets]


# ---------------------------------------------------------------------------------------------- main


def cmd_build() -> None:
    qc, md = load_all()
    print(f"quebec {qc.shape} maryland {md.shape}; fade_days present {qc['fade_days'].notna().mean():.3f}")


def cmd_score() -> None:
    frozen = check_prereg()
    qc, md = load_all()
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Pre-registered scores.
    rules = pd.DataFrame(rule_rows("quebec", qc, by_year=True) + rule_rows("maryland", md, by_year=False))
    rules.to_csv(OUT / "rules_scores.csv", index=False, lineterminator="\n")

    # 2. Same-row comparison with f0_all and f1_xgb_mono.
    pred = pd.read_csv(FV / "out" / "predictions_quebec.csv", usecols=["field_id", "year", "call_loyo_f0_all",
                                                                        "call_loyo_f1_xgb_mono"])
    pred["field_id"] = pred["field_id"].astype(str)
    joined = qc.merge(pred, on=["field_id", "year"], how="inner", validate="one_to_one")
    years7 = sorted(joined["year"].unique())
    groups = [("pooled_7y", np.ones(len(joined), bool))] + [(str(y), (joined["year"] == y).to_numpy()) for y in years7]
    cmp_rows = compare_rows("quebec", joined, {"f0_all": joined["call_loyo_f0_all"].to_numpy(),
                                               "f1_xgb_mono": joined["call_loyo_f1_xgb_mono"].to_numpy()}, groups)
    md_calls, hold_calls, gates = refit_f0_f1()
    mdj = md.copy()
    for name, c in md_calls.items():
        mdj = mdj.merge(c.rename(columns={"call": name}).assign(field_id=lambda d: d["field_id"].astype(str)),
                        on=["field_id", "year"], how="left", validate="one_to_one")
    cmp_rows += compare_rows("maryland", mdj, {k: mdj[k].to_numpy() for k in md_calls},
                             [("all_44", np.ones(len(mdj), bool))])
    q25 = qc[qc["year"] == 2025].copy()
    for name, c in hold_calls.items():
        q25 = q25.merge(c.rename(columns={"call": name}).assign(field_id=lambda d: d["field_id"].astype(str)),
                        on=["field_id", "year"], how="left", validate="one_to_one")
    cmp_rows += compare_rows("quebec_2025_refit_info", q25, {k: q25[k].to_numpy() for k in hold_calls},
                             [("2025", np.ones(len(q25), bool))])
    comparison = pd.DataFrame(cmp_rows)
    comparison.to_csv(OUT / "comparison_same_rows.csv", index=False, lineterminator="\n")

    # 3. Information only: threshold sweep, distributions, failure modes.
    tune = sweep(qc[qc["year"].isin(TUNE_YEARS)])
    best = int(tune.sort_values(["balanced_accuracy", "threshold"], ascending=[False, True]).iloc[0]["threshold"])
    sweep_all = (tune.rename(columns=lambda c: c if c == "threshold" else f"tune_2019_2024_{c}")
                 .merge(sweep(qc[qc["year"].isin(LATER_YEARS)]).rename(
                     columns=lambda c: c if c == "threshold" else f"later_2025_2026_{c}"), on="threshold")
                 .merge(sweep(md).rename(columns=lambda c: c if c == "threshold" else f"maryland_{c}"),
                        on="threshold"))
    sweep_all.to_csv(OUT / "threshold_sweep.csv", index=False, lineterminator="\n")
    later, mdc = qc[qc["year"].isin(LATER_YEARS)], md
    best_rows = {}
    for region, t in [("quebec_2019_2024", qc[qc["year"].isin(TUNE_YEARS)]), ("quebec_2025_2026", later),
                      ("maryland", mdc)]:
        for th in sorted({best, R1_MAX_FADE}):
            ok = t["fade_days"].notna().to_numpy()
            call = (t["fade_days"].to_numpy() <= th).astype(int)
            best_rows[f"{region}_t{th}"] = score(t["is_silage"].to_numpy()[ok], call[ok])
    pd.DataFrame(quantiles(qc, "quebec") + quantiles(md, "maryland")).to_csv(
        OUT / "distributions.csv", index=False, lineterminator="\n")
    pd.DataFrame(failure_modes(qc, "quebec") + failure_modes(md, "maryland")).to_csv(
        OUT / "failure_modes.csv", index=False, lineterminator="\n")
    pd.DataFrame(r1_subsets(qc, "quebec") + r1_subsets(md, "maryland")).to_csv(
        OUT / "r1_subsets.csv", index=False, lineterminator="\n")

    summary = {"generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "preregistration_sha256": frozen,
               "fade_rule_py_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "rows": {"quebec": len(qc), "quebec_by_year": {str(k): int(v) for k, v in qc.groupby("year").size().items()},
                        "quebec_joined_with_predictions": len(joined), "maryland": len(md)},
               "refit_gates": gates, "sweep_best_threshold_on_2019_2024": best, "sweep_best_scores": best_rows}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8", newline="\n")
    print(json.dumps({"refit_gates": gates, "best_threshold": best}, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["build", "score"])
    args = parser.parse_args()
    {"build": cmd_build, "score": cmd_score}[args.command]()


if __name__ == "__main__":
    main()
