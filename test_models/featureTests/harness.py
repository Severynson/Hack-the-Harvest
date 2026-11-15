"""Shared field-level evaluation harness: does a feature group, Landsat or Sentinel-1 improve the field model?

Every candidate ("arm") is scored under one fixed protocol against the field model as it stands
(``kernelag.field_model``: six harvest-evidence features, balanced logistic, threshold 0.5), on the same
rows, with the same folds, so the differences are paired and comparable.

Inputs (join key: field_id as text, year as int)
    data/labels/<dataset>.parquet                    labels: quebec_maize_2023, qc_regions_2023, barc_2021_2023
    data/s2_series/<dataset>/*.csv                   Sentinel-2 series (kernelag.field_model.load_series)
    test_models/featureTests/<group>/out/            feature groups: features.csv + meta.json (contract in README)
    data/landsat_series/<dataset>/, data/s1_series/<dataset>/, data/models/landsat_s2_calibration.json
                                                     Landsat and Sentinel-1, read through kernelag.multisensor
Arms
    base                  MODEL_FEATURES on the Sentinel-2 path (exactly field_model's path)
    base+<group>          MODEL_FEATURES + the group's pre-registered features (missing -> median imputer)
    rule:<group>          the group's 0/1 benchmark call scored directly (missing -> grain)
    optical:s2+landsat    MODEL_FEATURES computed on Sentinel-2 plus calibrated Landsat looks
    base+radar            MODEL_FEATURES + multisensor.RADAR_FEATURES
    all                   every extra source available for the evaluation's datasets
Evaluations
    E1  qc_cell_blocks            Quebec cell 79_515, 5-fold GroupKFold over 2 km blocks (reproduces field_model)
    E2  qc_regions_loco           17 Quebec cells (79_515 + 16 regional), leave one cell out: regional transfer
    E3  maryland_transfer         fit on quebec_maize_2023, score all 44 Maryland field-years (reproduces field_model)
    E3b maryland_transfer_allqc   fit on all 17 Quebec cells, score Maryland
Each arm is compared with base by a paired cluster bootstrap (2 km blocks, cells or fields; 2000 draws,
seed 0) for the change in balanced accuracy and silage F1 with 90% intervals, and an exact McNemar test.
Maryland is a test set only: nothing here is tuned on it, and the decision rule never looks at it.

Outputs (test_models/featureTests/results/): field_results.json, field_summary.csv, field_predictions.csv
(Quebec evaluations only).

Run from the repository root: ``.venv/Scripts/python.exe test_models/featureTests/harness.py``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))   # lets the file run as a plain script from the repo root, no PYTHONPATH

from kernelag.evaluate import extended_scores
from kernelag.features import build_features
from kernelag.field_model import (
    DECISION_THRESHOLD,
    MODEL_FEATURES,
    load_series,
    make_model,
    spatial_blocks,
)
from kernelag.paths import data_dir

TRAIN_SETS = ("quebec_maize_2023", "qc_regions_2023")
TEST_SET = "barc_2021_2023"
DATASETS = (*TRAIN_SETS, TEST_SET)
BLOCK_FOLDS = 5
DRAWS = 2000
SEED = 0
INTERVAL = (0.05, 0.95)          # a 90% interval, as everywhere else in the repo
MAX_GROUP_FEATURES = 3           # the contract caps pre-registered features per group
# Spec names, used only if kernelag.multisensor cannot be imported (the arm is then UNCOMPUTED anyway).
RADAR_FEATURES_SPEC = ["radar_lag_days", "s1_vh_drop_db", "s1_vhvv_before_db"]
# Published numbers (data/models/field_model_report.csv) the base arm must reproduce exactly.
REFERENCE = {"qc_cell_blocks": {"TP": 97, "FP": 53, "FN": 41, "TN": 127},
             "maryland_transfer": {"TP": 10, "FP": 5, "FN": 2, "TN": 27}}
DECISION_RULE = (
    "PRE-REGISTERED DECISION RULE: a feature group IMPROVES the field model only if, on E2 qc_regions_loco "
    "(leave one Quebec cell out), its change in balanced accuracy versus base is > 0 AND the 90% paired "
    "cluster-bootstrap interval (resampling cells) excludes 0. E1 and E3 are supporting evidence only. "
    "Maryland (n=44, one farm) is underpowered and never used for selection.")
SUMMARY_COLUMNS = ["evaluation", "label", "arm", "kind", "status", "n", "assessable", "TP", "FP", "FN", "TN",
                   "silage_precision", "silage_recall", "false_positive_rate", "accuracy", "balanced_accuracy",
                   "silage_f1", "d_balanced_accuracy", "d_balanced_accuracy_lo", "d_balanced_accuracy_hi",
                   "d_silage_f1", "d_silage_f1_lo", "d_silage_f1_hi", "mcnemar_base_only_right",
                   "mcnemar_arm_only_right", "mcnemar_p", "bootstrap_units", "extra_coverage_min", "decision",
                   "reason"]


@dataclass(frozen=True)
class Evaluation:
    key: str
    label: str
    description: str
    train: tuple[str, ...]
    score: tuple[str, ...]
    scheme: str         # "blocks" (GroupKFold), "loco" (leave one cell out) or "fixed" (fit train, score test)
    fold_unit: str      # column that defines the held-out folds
    boot_unit: str      # column resampled by the paired bootstrap


EVALUATIONS = [
    Evaluation("qc_cell_blocks", "E1", "quebec_maize_2023 cell 79_515, 5-fold GroupKFold over 2 km blocks",
               ("quebec_maize_2023",), ("quebec_maize_2023",), "blocks", "block", "block"),
    Evaluation("qc_regions_loco", "E2", "79_515 + 16 regional Quebec cells, leave one cell out (regional transfer)",
               TRAIN_SETS, TRAIN_SETS, "loco", "cell", "cell"),
    Evaluation("maryland_transfer", "E3", "fit on quebec_maize_2023, score all 44 Maryland field-years",
               ("quebec_maize_2023",), (TEST_SET,), "fixed", "", "field_id"),
    Evaluation("maryland_transfer_allqc", "E3b", "fit on all 17 Quebec cells, score all 44 Maryland field-years",
               TRAIN_SETS, (TEST_SET,), "fixed", "", "field_id"),
]


@dataclass
class Arm:
    name: str
    kind: str                                   # "model" or "rule"
    features: list[str] = field(default_factory=list)
    assess: str = "assessable"                  # column saying the field-year has a drop to read
    call: str | None = None                     # 0/1 column for a rule arm
    sources: list[str] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------------------------- data


def series_cells(folder: Path) -> pd.Series:
    """The 10 km cell of each field_id, read from the per-cell file names ``<cell>_<year>.csv``."""
    parts = []
    for path in sorted(folder.glob("*.csv")):
        ids = pd.read_csv(path, usecols=["field_id"])["field_id"].astype(str).unique()
        parts.append(pd.Series(path.stem.rsplit("_", 1)[0], index=ids))
    cells = pd.concat(parts) if parts else pd.Series(dtype=str)
    return cells[~cells.index.duplicated()]


def roster_table(labels: pd.DataFrame, features: pd.DataFrame, keep_all: bool) -> pd.DataFrame:
    """field_model.evidence_table (inner join) or evaluate.evaluation_table (keep_all) from ready features.

    Training sets keep only labeled field-years that have a series, as field_model does. The Maryland test
    roster keeps every labeled field-year; one without evidence is not assessable and scored as grain.
    """
    features = features.copy()
    for column in MODEL_FEATURES:
        if column not in features:
            features[column] = np.nan
    roster = pd.DataFrame(labels[["field_id", "year", "label"]]).assign(field_id=labels["field_id"].astype(str))
    if roster.duplicated(["field_id", "year"]).any():
        raise ValueError("labels must have one row per field-year")
    table = roster.merge(features, on=["field_id", "year"], how="left" if keep_all else "inner",
                         validate="one_to_one")
    table["assessable"] = table["max_drop"].notna()
    table["is_silage"] = (table["label"] == "silage").astype(int)
    return table.reset_index(drop=True)


def load_datasets(data: Path) -> tuple[dict, dict, dict, dict]:
    """Per dataset: the wide evidence table, the raw Sentinel-2 series, its features, and missing reasons."""
    import geopandas as gpd

    wide, series, features, missing = {}, {}, {}, {}
    for name in DATASETS:
        labels_file, folder = data / "labels" / f"{name}.parquet", data / "s2_series" / name
        if not labels_file.is_file():
            missing[name] = f"no labels file labels/{name}.parquet in the data folder"
            continue
        if not folder.is_dir() or not any(folder.glob("*.csv")):
            missing[name] = f"no Sentinel-2 series in data/s2_series/{name}/"
            continue
        labels = gpd.read_parquet(labels_file)
        series[name] = load_series(folder)
        features[name] = build_features(series[name])
        table = roster_table(labels, features[name], keep_all=name == TEST_SET)
        table.insert(0, "dataset", name)
        # Cells drive the leave-one-cell-out folds; the labels' own column wins over file names.
        cells = series_cells(folder)
        if "cell" in labels:
            declared = pd.Series(labels["cell"].astype(str).to_numpy(), index=labels["field_id"].astype(str))
            cells = declared[~declared.index.duplicated()].combine_first(cells)
        table["cell"] = table["field_id"].map(cells).fillna(name).astype(str)
        if name == "quebec_maize_2023":
            # Blocks from the whole label file, exactly as field_model.load_training builds them.
            table["block"] = table["field_id"].map(spatial_blocks(labels)).astype(str)
        wide[name] = table
    return wide, series, features, missing


# -------------------------------------------------------------------------------------- feature groups


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def read_group(meta_path: Path) -> dict:
    """One feature group's meta and table, checked against the FIELD-FEATURE CONTRACT.

    A contract problem makes every arm of the group UNCOMPUTED with the reason; nothing is repaired silently.
    """
    folder = meta_path.parent.parent.name
    group = {"key": folder, "folder": folder, "features": [], "rule": None, "table": None, "problem": None,
             "built": set(), "uncomputed": {}, "description": "", "inputs": {"meta.json": file_digest(meta_path)}}
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        group["problem"] = f"meta.json unreadable ({error})"
        return group
    group.update(key=str(meta.get("group") or folder), description=str(meta.get("description") or ""),
                 features=[str(c) for c in (meta.get("features") or [])], rule=meta.get("rule_column") or None,
                 uncomputed={str(k): str(v) for k, v in (meta.get("uncomputed") or {}).items()})
    if len(group["features"]) > MAX_GROUP_FEATURES:
        group["problem"] = f"contract: {len(group['features'])} pre-registered features (max {MAX_GROUP_FEATURES})"
        return group
    csv = meta_path.parent / "features.csv"
    if not csv.is_file():
        group["problem"] = "out/features.csv missing"
        return group
    group["inputs"]["features.csv"] = file_digest(csv)
    table = pd.read_csv(csv, dtype={"field_id": str, "dataset": str})
    needed = list(dict.fromkeys(["dataset", "field_id", "year", *group["features"],
                                 *([group["rule"]] if group["rule"] else [])]))
    absent = [c for c in needed if c not in table.columns]
    if absent:
        group["problem"] = f"contract: features.csv lacks columns {absent}"
        return group
    # Ids are integers written as text; a float writer would add ".0" and silently match nothing.
    table["field_id"] = table["field_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    table["year"] = pd.to_numeric(table["year"], errors="coerce")
    table = table.dropna(subset=["year"]).astype({"year": int})
    duplicates = int(table.duplicated(["dataset", "field_id", "year"]).sum())
    if duplicates:
        group["problem"] = f"contract: {duplicates} duplicate (dataset, field_id, year) rows in features.csv"
        return group
    for column in needed[3:]:
        table[column] = pd.to_numeric(table[column], errors="coerce")
    if group["rule"]:
        odd = set(table[group["rule"]].dropna().unique()) - {0, 1}
        if odd:
            group["problem"] = f"contract: rule column {group['rule']} has values other than 0/1"
            return group
    group["built"] = {str(d) for d in (meta.get("datasets_built") or table["dataset"].unique())}
    group["table"] = table[needed]
    return group


def discover_groups(groups_dir: Path) -> list[dict]:
    return [read_group(path) for path in sorted(groups_dir.glob("*/out/meta.json"))]


def group_column(group: dict, column: str) -> str:
    return f"g:{group['key']}:{column}"   # namespaced so no group can overwrite a base or another group's column


def add_groups(groups: list[dict], wide: dict, availability: dict) -> None:
    for group in groups:
        source = f"group:{group['key']}"
        availability[source] = {}
        for name in DATASETS:
            if group["problem"]:
                availability[source][name] = group["problem"]
            elif name not in group["built"]:
                availability[source][name] = group["uncomputed"].get(name, f"{name} not in datasets_built")
            elif name not in wide:
                availability[source][name] = "dataset has no base evidence"
            else:
                availability[source][name] = None
                part = group["table"][group["table"]["dataset"] == name].drop(columns="dataset")
                part = part.rename(columns={c: group_column(group, c) for c in part.columns[2:]})
                wide[name] = wide[name].merge(part, on=["field_id", "year"], how="left", validate="one_to_one")


# ---------------------------------------------------------------------------------- Landsat and radar


def add_multisensor(wide: dict, series: dict, features: dict, availability: dict) -> list[str]:
    """Landsat-optical and radar columns via kernelag.multisensor; returns the radar feature names."""
    try:
        from kernelag import multisensor
    except Exception as error:   # noqa: BLE001 - the module is written concurrently; report, never crash
        reason = f"kernelag.multisensor not importable ({type(error).__name__}: {error})"
        availability["radar"] = dict.fromkeys(DATASETS, reason)
        availability["landsat"] = dict.fromkeys(DATASETS, reason)
        return list(RADAR_FEATURES_SPEC)
    radar_features = list(getattr(multisensor, "RADAR_FEATURES", RADAR_FEATURES_SPEC))
    availability["radar"], availability["landsat"] = {}, {}
    radar_tables = {}

    def merge(name: str, frame: pd.DataFrame, columns: list[str], prefix: str) -> None:
        part = frame.assign(field_id=frame["field_id"].astype(str), year=frame["year"].astype(int))
        part = part[["field_id", "year", *columns]].rename(columns={c: prefix + c for c in columns})
        wide[name] = wide[name].merge(part, on=["field_id", "year"], how="left", validate="one_to_one")

    for name in DATASETS:
        if name not in wide:
            availability["radar"][name] = availability["landsat"][name] = "dataset has no base evidence"
            continue
        try:
            s1 = multisensor.load_radar(name)
            if s1 is None:
                availability["radar"][name] = f"no Sentinel-1 series in data/s1_series/{name}/"
            else:
                radar_tables[name] = multisensor.radar_feature_table(s1)
                merge(name, multisensor.fuse(features[name], radar_tables[name]), radar_features, "r:")
                availability["radar"][name] = None
        except Exception as error:   # noqa: BLE001
            availability["radar"][name] = f"radar features failed ({type(error).__name__}: {error})"
        try:
            calibration = multisensor.load_calibration()
            landsat = multisensor.load_landsat(name)
            if calibration is None:
                availability["landsat"][name] = ("no data/models/landsat_s2_calibration.json "
                                                 "(run python -m kernelag.multisensor --calibrate)")
            elif any(TEST_SET in str(d) for d in calibration.get("fitted_on", [])):
                availability["landsat"][name] = "Landsat calibration lists the Maryland test set in fitted_on"
            elif landsat is None:
                availability["landsat"][name] = f"no Landsat series in data/landsat_series/{name}/"
            else:
                optical = multisensor.multisensor_features(series[name], landsat, None, calibration)
                for column in MODEL_FEATURES:
                    if column not in optical:
                        optical[column] = np.nan
                looks = [c for c in ["n_looks_s2", "n_looks_landsat"] if c in optical]
                merge(name, optical, [*MODEL_FEATURES, *looks], "o:")
                if name in radar_tables:   # radar lag measured against the Landsat-densified optical decline
                    merge(name, multisensor.fuse(optical, radar_tables[name]), radar_features, "or:")
                availability["landsat"][name] = None
        except Exception as error:   # noqa: BLE001
            availability["landsat"][name] = f"Landsat optical path failed ({type(error).__name__}: {error})"
        if availability["landsat"][name] is None:
            wide[name]["o:assessable"] = wide[name]["o:max_drop"].notna()
    return radar_features


# ------------------------------------------------------------------------------------------------ arms


def build_arms(groups: list[dict], radar_features: list[str]) -> list[Arm]:
    arms = [Arm("base", "model", list(MODEL_FEATURES), description="field_model path: MODEL_FEATURES on Sentinel-2")]
    for group in groups:
        source = f"group:{group['key']}"
        if group["features"] or (group["problem"] and not group["rule"]):
            arms.append(Arm(f"base+{group['key']}", "model",
                            [*MODEL_FEATURES, *(group_column(group, c) for c in group["features"])],
                            sources=[source], description=group["description"]))
        if group["rule"]:
            arms.append(Arm(f"rule:{group['key']}", "rule", call=group_column(group, group["rule"]),
                            sources=[source], description=f"0/1 benchmark call {group['rule']}"))
    arms.append(Arm("optical:s2+landsat", "model", [f"o:{c}" for c in MODEL_FEATURES], assess="o:assessable",
                    sources=["landsat"], description="MODEL_FEATURES on Sentinel-2 + calibrated Landsat looks"))
    arms.append(Arm("base+radar", "model", [*MODEL_FEATURES, *(f"r:{c}" for c in radar_features)],
                    sources=["radar"], description="MODEL_FEATURES + Sentinel-1 radar features"))
    arms.append(Arm("all", "model", sources=["*"], description="every extra source available for the evaluation"))
    return arms


def resolve_all(evaluation: Evaluation, groups: list[dict], radar_features: list[str],
                availability: dict) -> Arm | str:
    """The 'all' arm for one evaluation: every extra source present for all of its datasets."""
    needed = set(evaluation.train) | set(evaluation.score)

    def ready(source: str) -> bool:
        return all(availability.get(source, {}).get(name, "absent") is None for name in needed)

    landsat, radar = ready("landsat"), ready("radar")
    features = [("o:" if landsat else "") + c for c in MODEL_FEATURES]
    sources = ["landsat"] if landsat else []
    for group in groups:
        if group["features"] and ready(f"group:{group['key']}"):
            features += [group_column(group, c) for c in group["features"]]
            sources.append(f"group:{group['key']}")
    if radar:
        features += [("or:" if landsat else "r:") + c for c in radar_features]
        sources.append("radar")
    if not sources:
        return "no extra evidence source is available for every dataset of this evaluation"
    return Arm("all", "model", features, assess="o:assessable" if landsat else "assessable", sources=sources,
               description="every extra source available for the evaluation")


# ------------------------------------------------------------------------------------ fitting and scoring


def fit_predict(fit_rows: pd.DataFrame, score_rows: pd.DataFrame, features: list[str], assess: str,
                notes: set) -> np.ndarray:
    """P(silage) from field_model's model; NaN where the score row is not assessable (it becomes grain)."""
    fit_part = fit_rows[fit_rows[assess].to_numpy(bool)]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = make_model().fit(fit_part[features], fit_part["is_silage"])
        probability = np.full(len(score_rows), np.nan)
        ok = score_rows[assess].to_numpy(bool)
        if ok.any():
            probability[ok] = model.predict_proba(score_rows.loc[ok, features])[:, 1]
    for warning in caught:
        if "without any observed values" in str(warning.message):
            notes.add("a feature had no observed values in some training fold; the imputer dropped it there")
    return probability


def model_probability(evaluation: Evaluation, train: pd.DataFrame, score: pd.DataFrame, arm: Arm,
                      notes: set) -> np.ndarray:
    if evaluation.scheme == "fixed":
        return fit_predict(train, score, arm.features, arm.assess, notes)
    from sklearn.model_selection import GroupKFold

    folds = score[evaluation.fold_unit].to_numpy()
    if evaluation.scheme == "blocks":   # identical to field_model.held_out_block_calls
        splits = GroupKFold(n_splits=BLOCK_FOLDS).split(score, groups=folds)
    else:
        splits = ((np.flatnonzero(folds != unit), np.flatnonzero(folds == unit)) for unit in sorted(set(folds)))
    probability = np.full(len(score), np.nan)
    for fit_rows, score_rows in splits:
        probability[score_rows] = fit_predict(score.iloc[fit_rows], score.iloc[score_rows], arm.features,
                                              arm.assess, notes)
    return probability


def to_call(probability: np.ndarray) -> np.ndarray:
    return (np.nan_to_num(probability, nan=0.0) >= DECISION_THRESHOLD).astype(int)


def group_confusion(truth: np.ndarray, call: np.ndarray, codes: np.ndarray, n_units: int) -> np.ndarray:
    """(units x 4) counts of TP, FP, FN, TN per bootstrap unit."""
    cells = [(call == 1) & (truth == 1), (call == 1) & (truth == 0), (call == 0) & (truth == 1),
             (call == 0) & (truth == 0)]
    return np.stack([np.bincount(codes, weights=c.astype(float), minlength=n_units) for c in cells], axis=1)


def balanced_accuracy_f1(counts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tp, fp, fn, tn = (counts[..., i] for i in range(4))
    with np.errstate(divide="ignore", invalid="ignore"):
        return (tp / (tp + fn) + tn / (tn + fp)) / 2, 2 * tp / (2 * tp + fp + fn)


def paired_bootstrap(truth: np.ndarray, base_call: np.ndarray, arm_call: np.ndarray, units: np.ndarray,
                     draws: int = DRAWS, seed: int = SEED) -> dict:
    """Change versus base in balanced accuracy and F1, resampling whole units (blocks, cells or fields).

    Both arms are scored on the same resampled rows in each draw, so the interval is for the paired
    difference. Resampling whole units keeps neighbours (or a field's repeated years) together. A draw
    with no silage or no grain row has no balanced accuracy and is skipped (the count is reported).
    """
    codes, uniques = pd.factorize(pd.Series(units).astype(str))
    n_units = len(uniques)
    picks = np.random.default_rng(seed).integers(0, n_units, size=(draws, n_units))
    weights = np.stack([np.bincount(row, minlength=n_units) for row in picks]).astype(float)
    base_counts = group_confusion(truth, base_call, codes, n_units)
    arm_counts = group_confusion(truth, arm_call, codes, n_units)
    base_ba, base_f1 = balanced_accuracy_f1(weights @ base_counts)
    arm_ba, arm_f1 = balanced_accuracy_f1(weights @ arm_counts)
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
    """Exact McNemar test: a two-sided binomial test on the field-years only one of the two gets right."""
    from scipy.stats import binomtest

    base_right, arm_right = base_call == truth, arm_call == truth
    base_only, arm_only = int((base_right & ~arm_right).sum()), int((~base_right & arm_right).sum())
    p = binomtest(arm_only, base_only + arm_only, 0.5).pvalue if base_only + arm_only else 1.0
    return {"base_only_right": base_only, "arm_only_right": arm_only, "p": round(float(p), 4)}


def coverage(table: pd.DataFrame, columns: list[str]) -> dict:
    """Share of rows where each extra column has evidence (base columns are left out)."""
    return {c: round(float(table[c].notna().mean()), 3) for c in columns if c not in MODEL_FEATURES}


def run_arm(evaluation: Evaluation, arm: Arm, train: pd.DataFrame, score: pd.DataFrame,
            availability: dict) -> tuple[dict, np.ndarray | None, np.ndarray | None]:
    """Result dict, P(silage) and calls for one arm on one evaluation (None when UNCOMPUTED)."""
    needed = set(evaluation.score) if arm.kind == "rule" else set(evaluation.train) | set(evaluation.score)
    reasons = {f"{source}/{name}": availability.get(source, {}).get(name, f"source {source} unknown")
               for source in arm.sources for name in sorted(needed)}
    reasons = {key: value for key, value in reasons.items() if value is not None}
    base = {"kind": arm.kind, "sources": arm.sources, "description": arm.description}
    if reasons:
        reason = "; ".join(f"{key}: {value}" for key, value in reasons.items())
        return {**base, "status": "UNCOMPUTED", "reason": reason}, None, None
    truth = score["is_silage"].to_numpy()
    notes: set = set()
    if arm.kind == "rule":
        values = score[arm.call]
        probability = values.to_numpy(float)
        call = (values == 1).fillna(False).to_numpy(int)   # no evidence -> grain, as for not-assessable rows
        extra = {"rule_column": arm.call, "coverage_score": round(float(values.notna().mean()), 3)}
        assessable = int(values.notna().sum())
    else:
        probability = model_probability(evaluation, train, score, arm, notes)
        call = to_call(probability)
        extra = {"features": arm.features, "coverage_score": coverage(score, arm.features)}
        if evaluation.scheme == "fixed":
            extra["coverage_train"] = coverage(train, arm.features)
            extra["train_rows_assessable"] = int(train[arm.assess].sum())
        if "o:n_looks_landsat" in score:
            extra["landsat_looks_share"] = round(float((score["o:n_looks_landsat"].fillna(0) > 0).mean()), 3)
        assessable = int(score[arm.assess].sum())
    result = {**base, "status": "ok", "n": len(score), "assessable": assessable, **extra,
              "metrics": extended_scores(truth, call), "notes": sorted(notes)}
    return result, probability, call


# --------------------------------------------------------------------------------------------- driver


def decide(e2: dict | None) -> str:
    """The pre-registered rule, applied to an arm's E2 comparison with base."""
    if not e2 or e2.get("status") != "ok" or "vs_base" not in e2:
        return "UNDECIDED (E2 UNCOMPUTED)"
    delta, (low, high) = e2["vs_base"]["d_balanced_accuracy"], e2["vs_base"]["d_balanced_accuracy_ci90"]
    if low is None:
        return "UNDECIDED (no usable bootstrap draws)"
    if delta > 0 and low > 0:
        return "IMPROVES"
    if high < 0:
        return "WORSE (E2 interval below 0)"
    return "NO IMPROVEMENT SHOWN"


def clean(value):
    """JSON-safe copy: numpy scalars to Python, NaN to null."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [clean(v) for v in (sorted(value) if isinstance(value, set) else value)]
    if isinstance(value, np.integer | np.bool_):
        return value.item()
    if isinstance(value, float | np.floating):
        return None if not np.isfinite(value) else float(value)
    return value


def summary_row(evaluation: Evaluation, arm_name: str, result: dict, decision: str) -> dict:
    metrics, versus = result.get("metrics", {}), result.get("vs_base", {})
    mcnemar = versus.get("mcnemar", {})
    row = {"evaluation": evaluation.key, "label": evaluation.label, "arm": arm_name, "kind": result.get("kind"),
           "status": result["status"], "n": result.get("n"), "assessable": result.get("assessable"),
           **{k: metrics.get(k) for k in SUMMARY_COLUMNS[7:17]},
           "d_balanced_accuracy": versus.get("d_balanced_accuracy"),
           "d_silage_f1": versus.get("d_silage_f1"),
           "mcnemar_base_only_right": mcnemar.get("base_only_right"),
           "mcnemar_arm_only_right": mcnemar.get("arm_only_right"), "mcnemar_p": mcnemar.get("p"),
           "bootstrap_units": versus.get("units"), "decision": decision, "reason": result.get("reason", "")}
    for name in ["balanced_accuracy", "silage_f1"]:
        low, high = versus.get(f"d_{name}_ci90", [None, None])
        row[f"d_{name}_lo"], row[f"d_{name}_hi"] = low, high
    # The thinnest extra column's evidence share: a group that covers few scored rows is mostly imputed.
    shares = result.get("coverage_score")
    shares = list(shares.values()) if isinstance(shares, dict) else [] if shares is None else [shares]
    row["extra_coverage_min"] = min(shares) if shares else None
    return row


def print_table(evaluation: Evaluation, rows: list[dict]) -> None:
    def number(value, digits: int = 3) -> str:
        return "-" if value is None or (isinstance(value, float) and not np.isfinite(value)) else f"{value:.{digits}f}"

    print(f"\n{evaluation.label} {evaluation.key}: {evaluation.description}")
    lines = []
    for row in [r for r in rows if r["status"] == "ok"]:
        has_delta = row["d_balanced_accuracy"] is not None
        lines.append({
            "arm": row["arm"], "TP/FP/FN/TN": f"{row['TP']}/{row['FP']}/{row['FN']}/{row['TN']}",
            "cov": number(row["extra_coverage_min"], 2), "bal_acc": number(row["balanced_accuracy"]),
            "f1": number(row["silage_f1"]),
            "d_bal_acc [90% CI]": (f"{row['d_balanced_accuracy']:+.3f} [{number(row['d_balanced_accuracy_lo'])}, "
                                   f"{number(row['d_balanced_accuracy_hi'])}]") if has_delta else "(reference)",
            "d_f1 [90% CI]": (f"{row['d_silage_f1']:+.3f} [{number(row['d_silage_f1_lo'])}, "
                              f"{number(row['d_silage_f1_hi'])}]") if has_delta else "",
            "McN_p": number(row["mcnemar_p"], 4) if has_delta else ""})
    if lines:
        print(pd.DataFrame(lines).to_string(index=False))
    for row in [r for r in rows if r["status"] != "ok"]:
        print(f"  {row['arm']}: UNCOMPUTED - {row['reason'][:150]}")


def main() -> None:
    import sklearn

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--groups-dir", type=Path, default=HERE, help="folder holding <group>/out/meta.json")
    parser.add_argument("--out-dir", type=Path, default=HERE / "results")
    parser.add_argument("--evaluations", nargs="+", default=[e.key for e in EVALUATIONS],
                        choices=[e.key for e in EVALUATIONS])
    parser.add_argument("--draws", type=int, default=DRAWS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    pd.set_option("display.width", 220)
    print(DECISION_RULE)

    wide, series, features, missing = load_datasets(data_dir())
    availability: dict = {"s2": {name: missing.get(name) for name in DATASETS}}
    for name, table in wide.items():
        print(f"{name}: {len(table)} field-years, {int(table['is_silage'].sum())} silage, "
              f"{int((~table['assessable']).sum())} not assessable, {table['cell'].nunique()} cells")
    for name, reason in missing.items():
        print(f"{name}: UNCOMPUTED ({reason})")

    groups = discover_groups(args.groups_dir)
    add_groups(groups, wide, availability)
    radar_features = add_multisensor(wide, series, features, availability)
    arms = build_arms(groups, radar_features)
    for group in groups:
        print(f"group {group['key']}: features {group['features']}, rule {group['rule']}, "
              f"problem {group['problem'] or 'none'}")
    for source in ["landsat", "radar"]:
        for name, reason in availability[source].items():
            if reason:
                print(f"{source}/{name}: UNCOMPUTED ({reason})")

    results, summary, predictions = {}, [], []
    for evaluation in [e for e in EVALUATIONS if e.key in args.evaluations]:
        needed = set(evaluation.train) | set(evaluation.score)
        lost = {name: missing[name] for name in sorted(needed) if name in missing}
        block = {"label": evaluation.label, "description": evaluation.description, "train": evaluation.train,
                 "score": evaluation.score, "bootstrap_unit": evaluation.boot_unit, "arms": {}}
        if lost:
            for arm in arms:
                block["arms"][arm.name] = {"status": "UNCOMPUTED", "reason": f"datasets missing: {lost}"}
        else:
            score = pd.concat([wide[name] for name in evaluation.score], ignore_index=True)
            train = score if evaluation.scheme != "fixed" else pd.concat([wide[name] for name in evaluation.train],
                                                                          ignore_index=True)
            truth, units = score["is_silage"].to_numpy(), score[evaluation.boot_unit].to_numpy()
            base_call = None
            for arm in arms:
                if arm.name == "all":
                    resolved = resolve_all(evaluation, groups, radar_features, availability)
                    if isinstance(resolved, str):
                        block["arms"]["all"] = {"kind": "model", "status": "UNCOMPUTED", "reason": resolved}
                        continue
                    arm = resolved
                result, probability, call = run_arm(evaluation, arm, train, score, availability)
                if arm.name == "base":
                    base_call = call
                    if evaluation.key in REFERENCE:
                        got = {k: result["metrics"][k] for k in ["TP", "FP", "FN", "TN"]}
                        result["reproduced"] = got == REFERENCE[evaluation.key]
                        result["reference"] = REFERENCE[evaluation.key]
                        print(f"{evaluation.label} base {got} vs reference {REFERENCE[evaluation.key]}: "
                              f"REPRODUCED {'yes' if result['reproduced'] else 'no'}")
                elif call is not None and base_call is not None:
                    result["vs_base"] = {**paired_bootstrap(truth, base_call, call, units, args.draws, args.seed),
                                         "mcnemar": mcnemar_exact(truth, base_call, call)}
                block["arms"][arm.name] = result
                if call is not None and evaluation.score != (TEST_SET,):
                    predictions.append(score[["dataset", "field_id", "year", "cell", "is_silage"]].assign(
                        evaluation=evaluation.key, arm=arm.name, assessable=score[arm.assess].to_numpy(bool)
                        if arm.kind == "model" else score[arm.call].notna().to_numpy(),
                        p_silage=np.round(probability, 4), call=call))
        results[evaluation.key] = block

    decisions = {arm.name: decide(results.get("qc_regions_loco", {}).get("arms", {}).get(arm.name))
                 for arm in arms if arm.name != "base"}
    for evaluation in [e for e in EVALUATIONS if e.key in results]:
        rows = [summary_row(evaluation, name, result, decisions.get(name, ""))
                for name, result in results[evaluation.key]["arms"].items()]
        summary += rows
        print_table(evaluation, rows)

    output = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "decision_rule": DECISION_RULE,
        "settings": {"model": "kernelag.field_model.make_model (median imputer, scaler, balanced logistic C=0.5)",
                     "decision_threshold": DECISION_THRESHOLD, "base_features": MODEL_FEATURES,
                     "block_folds": BLOCK_FOLDS, "draws": args.draws, "seed": args.seed, "interval": INTERVAL,
                     "not_assessable": "scored as grain (field_model.predict_silage semantics)",
                     "versions": {m.__name__: m.__version__ for m in [np, pd, sklearn]}},
        "datasets": {name: ({"field_years": len(t), "silage": int(t["is_silage"].sum()),
                             "not_assessable": int((~t["assessable"]).sum()), "cells": int(t["cell"].nunique())}
                            if (t := wide.get(name)) is not None else {"status": "UNCOMPUTED", "reason": missing[name]})
                     for name in DATASETS},
        "sources": availability,
        "groups": [{k: g[k] for k in ["key", "folder", "features", "rule", "problem", "built", "uncomputed",
                                      "description", "inputs"]} for g in groups],
        "evaluations": results,
        "decisions": decisions,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "field_results.json").write_text(json.dumps(clean(output), indent=1) + "\n", encoding="utf-8")
    table = pd.DataFrame(summary, columns=SUMMARY_COLUMNS)
    counts = ["n", "assessable", "TP", "FP", "FN", "TN", "mcnemar_base_only_right", "mcnemar_arm_only_right",
              "bootstrap_units"]
    table[counts] = table[counts].astype("Int64")   # counts stay integers next to UNCOMPUTED blanks
    table.to_csv(args.out_dir / "field_summary.csv", index=False, lineterminator="\n")
    if predictions:
        pd.concat(predictions, ignore_index=True).to_csv(args.out_dir / "field_predictions.csv", index=False,
                                                         lineterminator="\n")
    print(f"\n{DECISION_RULE}")
    for name, decision in decisions.items():
        print(f"  {name}: {decision}")
    print(f"wrote {args.out_dir.as_posix()}/field_results.json, field_summary.csv, field_predictions.csv")


if __name__ == "__main__":
    main()
