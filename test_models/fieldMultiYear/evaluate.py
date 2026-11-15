"""Field model across Quebec years: does a multi-year training set beat 2023-only on a season it never saw?

The protocol is pre-registered in README.md (the block between the PREREGISTRATION markers). ``prereg``
hashes that block into ``out/preregistration.sha256`` before anything is scored; ``score`` refuses to run
if the block has changed since.

Model (unchanged): ``kernelag.field_model.make_model()`` on ``MODEL_FEATURES`` from
``kernelag.features.build_features``, threshold ``DECISION_THRESHOLD``; fitted on assessable rows only;
a row that is not assessable is scored as grain (``field_model.predict_silage``).

Training sets
    M   multi-year: every qcm year except the held-out one
    S   2023-only: qcm_2023, the current model's year in the same 17 cells
Splits
    1 loyo     leave one year out (primary): M per held-out year; S fitted on 2023 scores the other years
    2 loao     leave one cell out, pooled over the eight years (supporting)
    3 strict   leave one year AND one cell out: M on the other years and cells, S on 2023 in the other cells
    4 maryland the 44 Maryland field-years, information only (never selection)
    5 coefficients per-year, all-years and LOYO fits: logistic weights per standard deviation
Gates (must reproduce published numbers): G1 S leave-one-cell-out on 2023 = harness E2 base;
G2 quebec_maize_2023 fit on Maryland = field_model_report; G3 qcm_2023 fit on Maryland = harness E3b base.

Decision (pre-registered): ADOPT the multi-year training set if its pooled LOYO balanced accuracy minus
S's, over the seven held-out years other than 2023, is > 0 with the 90% paired cell-bootstrap interval
entirely above 0.

Outputs (test_models/fieldMultiYear/out/): preregistration.sha256, preregistration_frozen.md,
preregistration.json, loyo_by_year.csv, summary.json, coefficients_by_year.csv, maryland.csv,
predictions_quebec.csv (Quebec rows only; no per-field Maryland calls).

Run from the repository root:
    .venv/Scripts/python.exe -I test_models/fieldMultiYear/evaluate.py prereg
    .venv/Scripts/python.exe -I test_models/fieldMultiYear/evaluate.py score
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))   # runs as a plain script (also under python -I) from the repo root

from kernelag.evaluate import evaluation_table, extended_scores  # noqa: E402
from kernelag.field_model import (  # noqa: E402
    DECISION_THRESHOLD,
    MODEL_FEATURES,
    evidence_table,
    load_series,
    make_model,
    predict_silage,
)
from kernelag.paths import data_dir  # noqa: E402

OUT = HERE / "out"
README = HERE / "README.md"
BEGIN, END = "<!-- PREREGISTRATION:BEGIN -->", "<!-- PREREGISTRATION:END -->"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
S_YEAR = 2023                                        # the current model's training year
COMPARE_YEARS = [y for y in YEARS if y != S_YEAR]    # held-out years both models score out of sample
PREFIX = "qcm_"
PUBLISHED_318 = "quebec_maize_2023"                  # the published field model's training set
TEST_SET = "barc_2021_2023"
DRAWS, SEED, INTERVAL = 2000, 0, (0.05, 0.95)        # as test_models/featureTests/harness.py
GATES = {
    "G1": {"what": "S leave-one-cell-out on 2023 alone = feature harness E2 base",
           "expected": {"TP": 877, "FP": 345, "FN": 390, "TN": 1516}},
    "G2": {"what": "quebec_maize_2023 (318-parcel) fit on Maryland = data/models/field_model_report.csv",
           "expected": {"TP": 10, "FP": 5, "FN": 2, "TN": 27}},
    "G3": {"what": "qcm_2023 (2023 all-Quebec, 17 cells) fit on Maryland = feature harness E3b base",
           "expected": {"TP": 10, "FP": 4, "FN": 2, "TN": 28}},
}
METRIC_COLUMNS = ["n", "assessable", "n_silage", "n_grain", "TP", "FP", "FN", "TN", "silage_precision",
                  "silage_recall", "grain_recall", "balanced_accuracy", "silage_f1", "accuracy",
                  "false_positive_rate"]


# ------------------------------------------------------------------------------------- pre-registration


def prereg_block(readme: Path = README) -> str:
    """The text strictly between the marker lines, LF line endings, ending with one newline."""
    lines = readme.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    stripped = [line.strip() for line in lines]
    if stripped.count(BEGIN) != 1 or stripped.count(END) != 1:
        raise SystemExit(f"README must hold exactly one {BEGIN} and one {END} line")
    begin, end = stripped.index(BEGIN), stripped.index(END)
    if end <= begin:
        raise SystemExit("the END marker comes before the BEGIN marker")
    return "\n".join(lines[begin + 1:end]).strip("\n") + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_prereg(force: bool) -> None:
    block = prereg_block()
    digest = sha256_text(block)
    target = OUT / "preregistration.sha256"
    if target.exists() and not force:
        frozen = target.read_text(encoding="utf-8").split()[0]
        if frozen == digest:
            print(f"already frozen, unchanged: {digest}")
            return
        raise SystemExit(f"a different pre-registration is already frozen ({frozen}); not overwriting. "
                         "Changing it after scoring would void the pre-registration.")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "preregistration_frozen.md").write_text(block, encoding="utf-8", newline="\n")
    target.write_text(f"{digest}  preregistration_frozen.md\n", encoding="utf-8", newline="\n")
    scored = [name for name in ("summary.json", "loyo_by_year.csv") if (OUT / name).exists()]
    meta = {"sha256": digest, "bytes": len(block.encode("utf-8")), "source": "README.md, between "
            f"{BEGIN} and {END}", "frozen_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evaluate_py_sha256_at_freeze": sha256_file(Path(__file__)),
            "scored_outputs_present_at_freeze": scored}
    (OUT / "preregistration.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"frozen {digest} ({meta['bytes']} bytes) at {meta['frozen_utc']}")
    if scored:
        print(f"WARNING: scored outputs already exist: {scored}")


def check_prereg() -> dict:
    target = OUT / "preregistration.sha256"
    if not target.exists():
        raise SystemExit("no out/preregistration.sha256: run `evaluate.py prereg` before scoring")
    frozen = target.read_text(encoding="utf-8").split()[0]
    current = sha256_text(prereg_block())
    if frozen != current:
        raise SystemExit(f"the README pre-registration changed since it was frozen ({frozen} -> {current}); "
                         "not scoring")
    meta_path = OUT / "preregistration.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return {"sha256": frozen, "matches_readme": True, "frozen_utc": meta.get("frozen_utc"),
            "evaluate_py_sha256_at_freeze": meta.get("evaluate_py_sha256_at_freeze"),
            "evaluate_py_sha256_at_score": sha256_file(Path(__file__))}


# ------------------------------------------------------------------------------------------------- data


def year_table(year: int) -> pd.DataFrame:
    """field_model.evidence_table for one qcm year, with the label table's cell and parcel_id."""
    import geopandas as gpd

    data = data_dir()
    labels = gpd.read_parquet(data / "labels" / f"{PREFIX}{year}.parquet")
    table = evidence_table(labels, load_series(data / "s2_series" / f"{PREFIX}{year}"))
    ids = labels["field_id"].astype(str).to_numpy()
    table["cell"] = table["field_id"].map(pd.Series(labels["cell"].astype(str).to_numpy(), index=ids))
    table["parcel_id"] = table["field_id"].map(pd.Series(labels["parcel_id"].astype(str).to_numpy(), index=ids))
    if table["cell"].isna().any() or (table["year"] != year).any():
        raise ValueError(f"{PREFIX}{year}: rows without a cell or with another year")
    return table


def folder_digest(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.glob("*.csv")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def input_digests(data: Path) -> dict:
    out = {}
    for name in [f"{PREFIX}{y}" for y in YEARS] + [PUBLISHED_318, TEST_SET]:
        out[name] = {"labels": sha256_file(data / "labels" / f"{name}.parquet")[:16],
                     "series": folder_digest(data / "s2_series" / name)}
    return out


# --------------------------------------------------------------------------------------- fit and score


def fit(rows: pd.DataFrame):
    """field_model's model on the assessable rows (as field_model.main and the harness do)."""
    part = rows[rows["assessable"].to_numpy(bool)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        return make_model().fit(part[MODEL_FEATURES], part["is_silage"])


def weights(model) -> dict:
    logistic = model.named_steps["logisticregression"]
    return {"intercept": round(float(logistic.intercept_[0]), 4),
            **{f: round(float(w), 4) for f, w in zip(MODEL_FEATURES, logistic.coef_[0])}}


def metrics(table: pd.DataFrame, call: np.ndarray) -> dict:
    truth = table["is_silage"].to_numpy()
    result = extended_scores(truth, np.asarray(call, int))
    result.update(n=len(table), assessable=int(table["assessable"].sum()))
    return {k: result[k] for k in METRIC_COLUMNS}


def counts(result: dict) -> dict:
    return {k: int(result[k]) for k in ("TP", "FP", "FN", "TN")}


# ---------------------------------------------------- paired cluster bootstrap (as featureTests/harness.py)


def group_confusion(truth: np.ndarray, call: np.ndarray, codes: np.ndarray, n_units: int) -> np.ndarray:
    """(units x 4) counts of TP, FP, FN, TN per bootstrap unit."""
    cells = [(call == 1) & (truth == 1), (call == 1) & (truth == 0), (call == 0) & (truth == 1),
             (call == 0) & (truth == 0)]
    return np.stack([np.bincount(codes, weights=c.astype(float), minlength=n_units) for c in cells], axis=1)


def balanced_accuracy_f1(confusion: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tp, fp, fn, tn = (confusion[..., i] for i in range(4))
    with np.errstate(divide="ignore", invalid="ignore"):
        return (tp / (tp + fn) + tn / (tn + fp)) / 2, 2 * tp / (2 * tp + fp + fn)


def paired_bootstrap(truth: np.ndarray, base_call: np.ndarray, arm_call: np.ndarray, units: np.ndarray,
                     draws: int = DRAWS, seed: int = SEED) -> dict:
    """Change (arm minus base) in balanced accuracy and silage F1, resampling whole units.

    Same procedure as ``paired_bootstrap`` in test_models/featureTests/harness.py (copied, not imported,
    so a later edit there cannot change these results). Both are scored on the same resampled rows.
    """
    codes, uniques = pd.factorize(pd.Series(units).astype(str))
    n_units = len(uniques)
    picks = np.random.default_rng(seed).integers(0, n_units, size=(draws, n_units))
    draw_weights = np.stack([np.bincount(row, minlength=n_units) for row in picks]).astype(float)
    base_counts = group_confusion(truth, base_call, codes, n_units)
    arm_counts = group_confusion(truth, arm_call, codes, n_units)
    base_ba, base_f1 = balanced_accuracy_f1(draw_weights @ base_counts)
    arm_ba, arm_f1 = balanced_accuracy_f1(draw_weights @ arm_counts)
    point_base = balanced_accuracy_f1(base_counts.sum(0))
    point_arm = balanced_accuracy_f1(arm_counts.sum(0))
    result = {"units": int(n_units), "draws": int(draws), "seed": int(seed)}
    for i, (name, arm, base) in enumerate([("balanced_accuracy", arm_ba, base_ba), ("silage_f1", arm_f1, base_f1)]):
        delta = arm - base
        finite = np.isfinite(delta)
        result[f"d_{name}"] = round(float(point_arm[i] - point_base[i]), 4)
        result[f"d_{name}_ci90"] = ([round(float(q), 4) for q in np.quantile(delta[finite], INTERVAL)]
                                    if finite.any() else [None, None])
        result[f"{name}_draws_used"] = int(finite.sum())
    return result


def mcnemar_exact(truth: np.ndarray, base_call: np.ndarray, arm_call: np.ndarray) -> dict:
    """Exact McNemar: two-sided binomial test on the field-years only one of the two gets right."""
    from scipy.stats import binomtest

    base_right, arm_right = base_call == truth, arm_call == truth
    base_only, arm_only = int((base_right & ~arm_right).sum()), int((~base_right & arm_right).sum())
    p = binomtest(arm_only, base_only + arm_only, 0.5).pvalue if base_only + arm_only else 1.0
    return {"S_only_right": base_only, "M_only_right": arm_only, "p": round(float(p), 4)}


def decide(comparison: dict, gates_ok: bool, failed: list[str]) -> str:
    """The pre-registered rule, applied to the primary comparison."""
    if not gates_ok:
        return f"HELD (gate failed: {', '.join(failed)})"
    lo, hi = comparison["d_balanced_accuracy_ci90"]
    if lo is None:
        return "HELD (no usable bootstrap draws)"
    if comparison["d_balanced_accuracy"] > 0 and lo > 0:
        return "ADOPT the multi-year training set"
    if hi < 0:
        return "KEEP 2023-only: MULTI-YEAR WORSE"
    return "KEEP 2023-only: NO IMPROVEMENT SHOWN"


# ------------------------------------------------------------------------------------------------ score


def per_year_rows(split: str, model: str, trained_on: str, table: pd.DataFrame, call: np.ndarray,
                  years: list[int], pooled: dict[str, list[int]], in_sample_years: tuple[int, ...] = ()) -> list:
    rows = []
    for year in years:
        mask = (table["year"] == year).to_numpy()
        rows.append({"split": split, "model": model, "trained_on": trained_on, "held_out": str(year),
                     "in_sample": year in in_sample_years, **metrics(table[mask], call[mask])})
    for name, pool in pooled.items():
        mask = table["year"].isin(pool).to_numpy()
        rows.append({"split": split, "model": model, "trained_on": trained_on, "held_out": name,
                     "in_sample": any(y in in_sample_years for y in pool), **metrics(table[mask], call[mask])})
    return rows


def attach_deltas(rows: list, split: str, table: pd.DataFrame, call_m: np.ndarray, call_s: np.ndarray,
                  pooled_name: str) -> dict:
    """Paired M-minus-S change per held-out year and pooled, on the M rows of ``split``."""
    truth, cells = table["is_silage"].to_numpy(), table["cell"].to_numpy()
    out = {}
    for row in rows:
        if row["split"] != split or row["model"] != "M":
            continue
        if row["held_out"] == pooled_name:
            mask = table["year"].isin(COMPARE_YEARS).to_numpy()
        elif row["held_out"].isdigit() and int(row["held_out"]) in COMPARE_YEARS:
            mask = (table["year"] == int(row["held_out"])).to_numpy()
        else:
            continue
        result = paired_bootstrap(truth[mask], call_s[mask], call_m[mask], cells[mask])
        row.update(d_balanced_accuracy_vs_S=result["d_balanced_accuracy"],
                   d_balanced_accuracy_lo=result["d_balanced_accuracy_ci90"][0],
                   d_balanced_accuracy_hi=result["d_balanced_accuracy_ci90"][1],
                   d_silage_f1_vs_S=result["d_silage_f1"], d_silage_f1_lo=result["d_silage_f1_ci90"][0],
                   d_silage_f1_hi=result["d_silage_f1_ci90"][1], bootstrap_cells=result["units"])
        out[row["held_out"]] = result
    return out


def cmd_score(workers: int) -> None:
    import geopandas as gpd

    prereg = check_prereg()
    started = time.time()
    data = data_dir()
    print(f"pre-registration {prereg['sha256'][:16]} matches README; loading {len(YEARS)} years ...", flush=True)
    with ProcessPoolExecutor(max_workers=min(workers, len(YEARS))) as pool:
        tables = list(pool.map(year_table, YEARS))
    qc = pd.concat(tables, ignore_index=True)
    truth, years, cells = qc["is_silage"].to_numpy(), qc["year"].to_numpy(), qc["cell"].to_numpy()
    all_cells = sorted(set(cells))
    print(f"Quebec roster: {len(qc)} field-years, {int(truth.sum())} silage, "
          f"{int((~qc['assessable']).sum())} not assessable, {len(all_cells)} cells, "
          f"{time.time() - started:.0f} s", flush=True)
    roster = {str(y): {"field_years": int((years == y).sum()), "silage": int(truth[years == y].sum()),
                       "grain": int((1 - truth[years == y]).sum()),
                       "not_assessable": int((~qc["assessable"].to_numpy()[years == y]).sum())} for y in YEARS}
    in_s = years == S_YEAR
    compare = np.isin(years, COMPARE_YEARS)
    coefficient_rows = []

    def coef_row(fit_name: str, trained_on: str, rows: pd.DataFrame, model) -> None:
        coefficient_rows.append({"fit": fit_name, "trained_on": trained_on,
                                 "n_fit_rows": int(rows["assessable"].sum()), **weights(model)})

    # Split 1: leave one year out (M) and the 2023-only model (S).
    p_m, c_m = np.full(len(qc), np.nan), np.zeros(len(qc), int)
    for year in YEARS:
        test = years == year
        model = fit(qc[~test])
        p_m[test], c_m[test] = predict_silage(model, qc[test])
        coef_row(f"loyo_without_{year}", "+".join(str(y) for y in YEARS if y != year), qc[~test], model)
    model_s = fit(qc[in_s])
    p_s, c_s = predict_silage(model_s, qc)

    # Gate G1 and split 3's S: 2023 fitted on 16 cells, scoring the 17th in every year.
    p_s3, c_s3 = np.full(len(qc), np.nan), np.zeros(len(qc), int)
    for cell in all_cells:
        held = cells == cell
        model = fit(qc[in_s & ~held])
        p_s3[held], c_s3[held] = predict_silage(model, qc[held])
    g1 = metrics(qc[in_s], c_s3[in_s])

    # Split 2: leave one cell out, all years.
    p_loao, c_loao = np.full(len(qc), np.nan), np.zeros(len(qc), int)
    for cell in all_cells:
        held = cells == cell
        model = fit(qc[~held])
        p_loao[held], c_loao[held] = predict_silage(model, qc[held])

    # Split 3: leave one year and one cell out (M), against S fitted on 2023 in the other 16 cells.
    p_m3, c_m3 = np.full(len(qc), np.nan), np.zeros(len(qc), int)
    for year in COMPARE_YEARS:
        for cell in all_cells:
            score_rows = (years == year) & (cells == cell)
            if not score_rows.any():
                continue
            model = fit(qc[(years != year) & (cells != cell)])
            p_m3[score_rows], c_m3[score_rows] = predict_silage(model, qc[score_rows])
    print(f"Quebec splits fitted, {time.time() - started:.0f} s", flush=True)

    # Split 4: Maryland, information only.
    published = gpd.read_parquet(data / "labels" / f"{PUBLISHED_318}.parquet")
    train_318 = evidence_table(published, load_series(data / "s2_series" / PUBLISHED_318))
    md_labels = gpd.read_parquet(data / "labels" / f"{TEST_SET}.parquet")
    md = evaluation_table(md_labels, load_series(data / "s2_series" / TEST_SET))
    md_truth = md["is_silage"].to_numpy()
    model_318 = fit(train_318)
    model_all = fit(qc)
    md_fits = [("published_318", f"{PUBLISHED_318} (cell 79_515)", train_318, model_318, "G2"),
               ("qcm_2023", "qcm_2023 (17 cells), = S", qc[in_s], model_s, "G3"),
               ("multi_year", "qcm_2019..qcm_2026 (17 cells)", qc, model_all, None)]
    md_calls, md_rows = {}, []
    for name, trained_on, rows, model, gate in md_fits:
        _, call = predict_silage(model, md)
        md_calls[name] = call
        result = metrics(md, call)
        reference = GATES[gate]["expected"] if gate else None
        md_rows.append({"fit": name, "trained_on": trained_on, "n_fit_rows": int(rows["assessable"].sum()),
                        **result, "reference": (f"TP{reference['TP']} FP{reference['FP']} FN{reference['FN']} "
                                                f"TN{reference['TN']}" if reference else ""),
                        "reproduced": (counts(result) == reference) if reference else "",
                        "calls_differing_from_qcm_2023": ""})
    for row in md_rows:
        row["calls_differing_from_qcm_2023"] = int((md_calls[row["fit"]] != md_calls["qcm_2023"]).sum())
    md_vs = paired_bootstrap(md_truth, md_calls["qcm_2023"], md_calls["multi_year"], md["field_id"].to_numpy())

    # Gates.
    gate_results = {"G1": counts(g1), "G2": counts(md_rows[0]), "G3": counts(md_rows[1])}
    gates = {k: {**GATES[k], "observed": v, "reproduced": v == GATES[k]["expected"]} for k, v in gate_results.items()}
    failed = [k for k, v in gates.items() if not v["reproduced"]]

    # Per-year tables.
    pooled7, pooled8 = "pooled_7_years_excl_2023", "pooled_all_8_years"
    rows = []
    rows += per_year_rows("loyo", "M", "the other seven qcm years", qc, c_m, YEARS,
                          {pooled8: YEARS, pooled7: COMPARE_YEARS})
    rows += per_year_rows("loyo", "S", "qcm_2023", qc, c_s, YEARS, {pooled7: COMPARE_YEARS},
                          in_sample_years=(S_YEAR,))
    rows += per_year_rows("loao", "M", "the other 16 cells, all eight years", qc, c_loao, YEARS, {pooled8: YEARS})
    rows += per_year_rows("strict", "M", "the other seven years in the other 16 cells", qc, c_m3, COMPARE_YEARS,
                          {pooled7: COMPARE_YEARS})
    rows += per_year_rows("strict", "S", "qcm_2023 in the other 16 cells", qc, c_s3, COMPARE_YEARS,
                          {pooled7: COMPARE_YEARS})
    rows.append({"split": "gate_G1", "model": "S", "trained_on": "qcm_2023 in the other 16 cells",
                 "held_out": str(S_YEAR), "in_sample": False, **g1})
    loyo_deltas = attach_deltas(rows, "loyo", qc, c_m, c_s, pooled7)
    strict_deltas = attach_deltas(rows, "strict", qc, c_m3, c_s3, pooled7)
    by_year = pd.DataFrame(rows)

    primary = loyo_deltas[pooled7]
    primary["mcnemar"] = mcnemar_exact(truth[compare], c_s[compare], c_m[compare])
    strict_deltas[pooled7]["mcnemar"] = mcnemar_exact(truth[compare], c_s3[compare], c_m3[compare])
    decision = decide(primary, not failed, failed)

    # Split 5: coefficients.
    for year in YEARS:
        part = qc[years == year]
        coef_row(f"single_{year}", str(year), part, model_s if year == S_YEAR else fit(part))
    coef_row("all_years", "+".join(map(str, YEARS)), qc, model_all)
    coef_row("published_318", PUBLISHED_318, train_318, model_318)
    coefficients = pd.DataFrame(coefficient_rows)
    single = coefficients[coefficients["fit"].str.startswith("single_")]
    every = ["intercept", *MODEL_FEATURES]
    all_years = coefficients.loc[coefficients["fit"] == "all_years", every].iloc[0]
    spread = {
        "single_year_mean": single[every].mean(), "single_year_sd": single[every].std(ddof=1),
        "single_year_min": single[every].min(), "single_year_max": single[every].max(),
        "single_year_sign_matches_all_years": (np.sign(single[every]) == np.sign(all_years)).sum(),
    }
    loyo_fits = coefficients[coefficients["fit"].str.startswith("loyo_")]
    spread["loyo_sd"] = loyo_fits[every].std(ddof=1)
    spread_rows = [{"fit": name, "trained_on": "summary of the fits above", "n_fit_rows": np.nan,
                    **{k: round(float(v), 4) for k, v in values.items()}} for name, values in spread.items()]
    coefficients = pd.concat([coefficients, pd.DataFrame(spread_rows)], ignore_index=True)

    # Outputs.
    OUT.mkdir(parents=True, exist_ok=True)
    by_year.to_csv(OUT / "loyo_by_year.csv", index=False, lineterminator="\n")
    coefficients.to_csv(OUT / "coefficients_by_year.csv", index=False, lineterminator="\n")
    pd.DataFrame(md_rows).to_csv(OUT / "maryland.csv", index=False, lineterminator="\n")
    predictions = qc[["field_id", "parcel_id", "year", "cell", "label", "assessable"]].assign(
        p_loyo_M=np.round(p_m, 4), call_loyo_M=c_m, p_S=np.round(p_s, 4), call_S=c_s, S_in_sample=in_s,
        p_loao_M=np.round(p_loao, 4), call_loao_M=c_loao, p_strict_M=np.round(p_m3, 4), call_strict_M=c_m3,
        p_strict_S=np.round(p_s3, 4), call_strict_S=c_s3)
    predictions.loc[in_s, ["p_strict_M", "call_strict_M"]] = np.nan   # 2023 is not a split-3 held-out year
    predictions.to_csv(OUT / "predictions_quebec.csv", index=False, lineterminator="\n")

    def pick(split: str, model: str, held_out: str) -> dict:
        row = by_year[(by_year["split"] == split) & (by_year["model"] == model) & (by_year["held_out"] == held_out)]
        return {k: (v.item() if hasattr(v, "item") else v) for k, v in row.iloc[0][METRIC_COLUMNS].items()}

    summary = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration": prereg,
        "decision_rule": "ADOPT the multi-year training set if pooled LOYO balanced accuracy (M) minus the "
                         "2023-only model's (S), over held-out years " + ", ".join(map(str, COMPARE_YEARS)) +
                         ", is > 0 and its 90% paired cell-bootstrap interval lies entirely above 0.",
        "decision": decision,
        "gates": gates,
        "settings": {"model": "kernelag.field_model.make_model()", "features": MODEL_FEATURES,
                     "threshold": DECISION_THRESHOLD, "not_assessable": "scored grain; not used for fitting",
                     "bootstrap": {"unit": "cell", "draws": DRAWS, "seed": SEED, "interval": list(INTERVAL)},
                     "years": YEARS, "compare_years": COMPARE_YEARS, "cells": all_cells},
        "roster": {"quebec_field_years": len(qc), "by_year": roster, "maryland_field_years": len(md)},
        "primary": {"M_pooled": pick("loyo", "M", pooled7), "S_pooled": pick("loyo", "S", pooled7),
                    **primary},
        "loyo": {"M_pooled_all_8_years": pick("loyo", "M", pooled8), "per_year_vs_S":
                 {k: v for k, v in loyo_deltas.items() if k != pooled7}},
        "loao": {"M_pooled_all_8_years": pick("loao", "M", pooled8)},
        "strict": {"M_pooled": pick("strict", "M", pooled7), "S_pooled": pick("strict", "S", pooled7),
                   **strict_deltas[pooled7],
                   "per_year_vs_S": {k: v for k, v in strict_deltas.items() if k != pooled7}},
        "maryland": {"note": "information only, never used for selection", "fits": md_rows,
                     "multi_year_vs_qcm_2023": md_vs},
        "coefficients": {"spread": {name: {k: round(float(v), 4) for k, v in values.items()}
                                    for name, values in spread.items()}},
        "inputs": input_digests(data),
        "runtime_s": round(time.time() - started, 1),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8",
                                      newline="\n")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 40)
    show = ["split", "model", "held_out", "in_sample", "n", "TP", "FP", "FN", "TN", "silage_precision",
            "silage_recall", "balanced_accuracy", "silage_f1", "d_balanced_accuracy_vs_S",
            "d_balanced_accuracy_lo", "d_balanced_accuracy_hi"]
    print(by_year[[c for c in show if c in by_year]].to_string(index=False))
    print(pd.DataFrame(md_rows).drop(columns=["trained_on"]).to_string(index=False))
    print(coefficients.drop(columns=["trained_on"]).to_string(index=False))
    for key, gate in gates.items():
        print(f"{key} {'REPRODUCED' if gate['reproduced'] else 'NOT REPRODUCED'}: observed {gate['observed']}, "
              f"expected {gate['expected']}")
    print(f"PRIMARY: d balanced accuracy {primary['d_balanced_accuracy']:+.4f} "
          f"90% CI {primary['d_balanced_accuracy_ci90']} ({primary['units']} cells, {DRAWS} draws)")
    print(f"DECISION: {decision}")
    print(f"done in {time.time() - started:.0f} s; outputs in {OUT}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("prereg", help="hash the README pre-registration into out/ (before scoring)")
    freeze.add_argument("--force", action="store_true", help="overwrite a different frozen hash (voids it)")
    run = sub.add_parser("score", help="run every split and write out/")
    run.add_argument("--workers", type=int, default=8, help="processes for building features, one per year")
    args = parser.parse_args()
    if args.command == "prereg":
        cmd_prereg(args.force)
    else:
        cmd_score(args.workers)


if __name__ == "__main__":
    main()
