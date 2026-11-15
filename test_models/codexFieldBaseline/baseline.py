"""One fixed XGBoost comparison against Kernel's six-feature logistic classifier.

Run from the repository root: ``PYTHONPATH=. .venv/bin/python
test_models/codexFieldBaseline/baseline.py``. This is an exploratory comparison,
not a new claim that Maryland is untouched or that either score is calibrated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, f1_score
from sklearn.model_selection import GroupKFold
from xgboost import XGBClassifier
from xgboost import __version__ as xgb_version

from kernelag.evaluate import evaluation_table
from kernelag.field_model import (
    DECISION_THRESHOLD,
    MODEL_FEATURES,
    TRAIN_PATTERN,
    load_series,
    load_training,
    make_model,
    predict_silage,
    scores,
)
from kernelag.paths import data_dir

SEED = 42
FOLDS = 5
XGB_PARAMETERS = {
    "n_estimators": 80,
    "max_depth": 2,
    "min_child_weight": 8,
    "learning_rate": 0.05,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "reg_lambda": 5.0,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "tree_method": "hist",
    "n_jobs": 4,
    "random_state": SEED,
}


def make_candidate(name: str, truth: np.ndarray):
    if len(np.unique(truth)) != 2:
        raise ValueError("every fit split must contain both harvest classes")
    if name == "logistic":
        return make_model()
    # Class weights use the fitting partition only, including inside each fold.
    weight = float((truth == 0).sum() / (truth == 1).sum())
    return XGBClassifier(**XGB_PARAMETERS, scale_pos_weight=weight)


def metrics(table: pd.DataFrame, score: np.ndarray) -> dict:
    truth = table["is_silage"].to_numpy()
    call = (np.nan_to_num(score, nan=0.0) >= DECISION_THRESHOLD).astype(int)
    ok = np.isfinite(score)
    return {
        **scores(truth, call),
        "silage_f1": round(float(f1_score(truth, call, zero_division=0)), 4),
        "brier_assessable": round(float(brier_score_loss(truth[ok], score[ok])), 4) if ok.any() else None,
        "assessable_fields": int(ok.sum()),
        "assessable_share": round(float(ok.mean()), 4),
    }


def provenance(data: Path) -> tuple[str, list[str]]:
    paths = [Path(__file__).resolve()]
    for source in ["kernelag/field_model.py", "kernelag/features.py", "kernelag/evaluate.py"]:
        paths.append(Path(source).resolve())
    for labels in sorted((data / "labels").glob(TRAIN_PATTERN + ".parquet")):
        folder = data / "s2_series" / labels.stem
        series = sorted(folder.glob("*.csv"))
        if series:
            paths.extend([labels, *series])
    paths.append(data / "labels" / "barc_2021_2023.parquet")
    paths.extend(sorted((data / "s2_series" / "barc_2021_2023").glob("*.csv")))
    signature = hashlib.sha256()
    for path in paths:
        signature.update(str(path.relative_to(Path.cwd())).encode())
        signature.update(hashlib.sha256(path.read_bytes()).digest())
    signature.update(f"xgboost={xgb_version}".encode())
    for package in ["scikit-learn", "numpy", "pandas"]:
        signature.update(f"{package}={version(package)}".encode())
    return signature.hexdigest(), [str(path.relative_to(Path.cwd())) for path in paths]


def run() -> dict:
    data = data_dir()
    train, blocks = load_training(data)
    # Repeated parcel IDs across years must stay together. The first block is
    # used consistently even if a projected boundary moved across a grid edge.
    unique_blocks = blocks.groupby(level=0, sort=False).first()
    groups = unique_blocks.reindex(train["field_id"]).to_numpy()
    if pd.isna(groups).any():
        raise ValueError("every training field needs a spatial block")
    n_blocks = len(np.unique(groups))
    if n_blocks < FOLDS:
        raise ValueError(f"need {FOLDS} spatial blocks; found {n_blocks}")
    splits = list(GroupKFold(n_splits=FOLDS).split(train, groups=groups))
    labels = gpd.read_parquet(data / "labels" / "barc_2021_2023.parquet")
    test = evaluation_table(labels, load_series(data / "s2_series" / "barc_2021_2023"))
    training_years = sorted(int(y) for y in train["year"].unique())
    output = {
        "specification": {
            "features": MODEL_FEATURES,
            "xgboost_parameters": XGB_PARAMETERS,
            "class_imbalance": "balanced logistic; XGBoost negative/positive fit-partition ratio",
            "decision_threshold": DECISION_THRESHOLD,
            "folds": FOLDS,
            "selection": "single fixed comparison; no hyperparameter or threshold search",
        },
        "data": {
            "training_field_years_with_series": len(train),
            "training_assessable": int(train["assessable"].sum()),
            "training_years": training_years,
            "training_spatial_blocks": n_blocks,
            "training_unique_parcels": train["field_id"].nunique(),
            "test_field_years": len(test),
            "test_unique_fields": test["field_id"].nunique(),
            "test_years": sorted(int(y) for y in test["year"].unique()),
        },
        "quebec_spatial_oof": {},
        "maryland_external_reused_cohort": {},
        "caveats": [
            "Maryland was already inspected by the team; this is not a fresh untouched test set",
            "Scores are uncalibrated outputs; Brier is a score diagnostic, not proof of probability calibration",
            "Brier uses assessable rows only; classification metrics retain every row and score unknowns as grain",
            "Quebec folds hold out 2 km blocks but no geographic buffer prevents all neighboring-field dependence",
            "A one-cell training sample and one research farm do not establish national transfer",
            "Field-year metrics are not acreage accuracy and may include repeated fields",
            "No held-out-year result is claimed when only one training year is available",
            "CNN and hybrid training deferred pending more independent labeled regions and years",
        ],
    }
    for name in ["logistic", "xgboost"]:
        oof = np.full(len(train), np.nan)
        for fit_rows, score_rows in splits:
            fit = train.iloc[fit_rows]
            fit = fit[fit["assessable"]]
            model = make_candidate(name, fit["is_silage"].to_numpy())
            model.fit(fit[MODEL_FEATURES], fit["is_silage"])
            oof[score_rows] = predict_silage(model, train.iloc[score_rows])[0]
        output["quebec_spatial_oof"][name] = metrics(train, oof)
        fit = train[train["assessable"]]
        model = make_candidate(name, fit["is_silage"].to_numpy())
        model.fit(fit[MODEL_FEATURES], fit["is_silage"])
        test_score = predict_silage(model, test)[0]
        output["maryland_external_reused_cohort"][name] = metrics(test, test_score)
    for key, table in [("quebec_spatial_oof", train), ("maryland_external_reused_cohort", test)]:
        output[key]["always_grain"] = metrics(table, np.zeros(len(table)))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="repeat the fixed comparison")
    args = parser.parse_args()
    out = Path(__file__).resolve().parent / "out" / "results.json"
    signature, sources = provenance(data_dir())
    if out.exists() and not args.force:
        cached = json.loads(out.read_text())
        if cached.get("input_sha256") == signature:
            print(f"cached: {out}")
            return
    result = run()
    result["input_sha256"] = signature
    result["source_paths"] = sources
    result["versions"] = {"xgboost": xgb_version,
                          **{p: version(p) for p in ["scikit-learn", "numpy", "pandas"]}}
    # Undefined precision for always-grain is missing, never non-standard NaN JSON.
    clean = json.loads(pd.Series([result]).to_json(orient="values", double_precision=8))[0]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(clean, indent=2, allow_nan=False) + "\n")
    for cohort in ["quebec_spatial_oof", "maryland_external_reused_cohort"]:
        for name, row in clean[cohort].items():
            print(f"{cohort} {name}: accuracy={row['accuracy']:.3f} "
                  f"F1={row['silage_f1']:.3f} Brier={row['brier_assessable']:.4f}")
    print(f"results: {out}")


if __name__ == "__main__":
    main()
