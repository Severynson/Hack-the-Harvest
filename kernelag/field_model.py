"""Field-level silage-or-grain model: train on Quebec declarations, test on the Maryland fields.

Train: Quebec parcels whose farmer declared grain maize or silage maize (``kernelag.quebec``).
Test:  the organizers' 44 labeled Maryland field-years (``kernelag.barc``). Never used for fitting.

The model is the team notebook's: a logistic regression on six pieces of harvest evidence that
do not depend on the calendar, so a model fitted in Quebec can be asked about Maryland:
    max_drop, max_drop_rate   how big and how fast the greenness drop was
    fade_days                 days from clearly green to clearly bare
    green_at_cut              greenness just before the drop, as a share of the season peak
    ndmi_before_cut           canopy moisture just before the drop
    ndti_post                 residue on the first bare looks after the drop

Three checks are reported, each with the confusion matrix and precision and recall for both classes:
    quebec_held_out_blocks    fitted on some 2 km blocks of Quebec parcels, scored on the others
    maryland_always_grain     the trivial baseline on the Maryland test set
    maryland_from_quebec      the Quebec-fitted model on the Maryland test set

A field-year with too few clear looks to find a drop is "not assessable": it is counted, and
scored as grain (the majority class), never guessed from imputed values.

Outputs (``data/models/``): field_model_report.csv, field_model_by_year.csv,
field_model_coefficients.csv, field_model_maryland_predictions.csv

Run: ``python -m kernelag.field_model``
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag.features import build_features
from kernelag.paths import data_dir, record_in_manifest

MODEL_FEATURES = ["max_drop", "max_drop_rate", "fade_days", "green_at_cut", "ndmi_before_cut", "ndti_post"]
DECISION_THRESHOLD = 0.5   # fixed in advance; never tuned on the test set
BLOCK_KM = 2               # size of the spatial blocks held out together inside the training region


def load_series(path: Path) -> pd.DataFrame:
    """Per-field, per-date series from one CSV or a folder of per-cell CSVs."""
    files = sorted(path.glob("*.csv")) if path.is_dir() else [path]
    if not files:
        raise FileNotFoundError(f"no series files in {path}; run kernelag.s2_series first")
    series = pd.concat([pd.read_csv(f, parse_dates=["date"]) for f in files], ignore_index=True)
    series = series.rename(columns={"OBJECTID": "field_id"})
    series["date"] = series["date"].dt.normalize()
    return series.drop_duplicates(["field_id", "year", "date"])


def evidence_table(labels: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """One row per labeled field-year that has a series: label, features, and whether it is assessable."""
    features = build_features(series)
    for column in MODEL_FEATURES:
        if column not in features:
            features[column] = np.nan
    table = labels[["field_id", "year", "label"]].merge(features, on=["field_id", "year"], how="inner")
    table["assessable"] = table["max_drop"].notna()
    table["is_silage"] = (table["label"] == "silage").astype(int)
    return table.reset_index(drop=True)


def make_model():
    """The team notebook's logistic model, unchanged."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(class_weight="balanced", C=0.5, max_iter=1000),
    )


def predict_silage(model, table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Probability of silage and the call (1 = silage). Not-assessable rows get NaN and grain."""
    probability = np.full(len(table), np.nan)
    ok = table["assessable"].to_numpy()
    if ok.any():
        probability[ok] = model.predict_proba(table.loc[ok, MODEL_FEATURES])[:, 1]
    call = (np.nan_to_num(probability, nan=0.0) >= DECISION_THRESHOLD).astype(int)
    return probability, call


def scores(truth: np.ndarray, call: np.ndarray) -> dict:
    """Confusion matrix with silage as the positive class, and precision and recall for both classes."""
    tp = int(((call == 1) & (truth == 1)).sum())
    fp = int(((call == 1) & (truth == 0)).sum())
    fn = int(((call == 0) & (truth == 1)).sum())
    tn = int(((call == 0) & (truth == 0)).sum())

    def ratio(top: int, bottom: int) -> float:
        return round(top / bottom, 3) if bottom else float("nan")

    return {
        "n_grain": tn + fp, "n_silage": tp + fn, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "silage_precision": ratio(tp, tp + fp), "silage_recall": ratio(tp, tp + fn),
        "grain_precision": ratio(tn, tn + fn), "grain_recall": ratio(tn, tn + fp),
        "false_positive_rate": ratio(fp, fp + tn), "accuracy": ratio(tp + tn, len(truth)),
    }


def spatial_blocks(labels) -> pd.Series:
    """A block id per field_id: the 2 km square its centre falls in. Neighbours share a block."""
    utm = labels.to_crs(labels.estimate_utm_crs())
    centre = utm.geometry.representative_point()
    size = BLOCK_KM * 1000
    block = (centre.x // size).astype(int).astype(str) + "_" + (centre.y // size).astype(int).astype(str)
    return pd.Series(block.to_numpy(), index=labels["field_id"].to_numpy())


def held_out_block_calls(train: pd.DataFrame, blocks: pd.Series, folds: int = 5) -> np.ndarray:
    """Calls for every training row, each made by a model that never saw that row's block."""
    from sklearn.model_selection import GroupKFold

    groups = blocks.reindex(train["field_id"]).to_numpy()
    call = np.zeros(len(train), int)
    for fit_rows, score_rows in GroupKFold(n_splits=folds).split(train, groups=groups):
        fit_part = train.iloc[fit_rows]
        fit_part = fit_part[fit_part["assessable"]]
        model = make_model().fit(fit_part[MODEL_FEATURES], fit_part["is_silage"])
        call[score_rows] = predict_silage(model, train.iloc[score_rows])[1]
    return call


def main() -> None:
    import geopandas as gpd

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--train-labels", default="labels/quebec_maize_2023.parquet")
    parser.add_argument("--train-series", default="s2_series/quebec_maize_2023")
    parser.add_argument("--test-labels", default="labels/barc_2021_2023.parquet")
    parser.add_argument("--test-series", default="s2_series/barc_2021_2023")
    args = parser.parse_args()
    data = data_dir()

    def resolve(text: str) -> Path:
        return Path(text) if Path(text).exists() else data / text

    train_labels = gpd.read_parquet(resolve(args.train_labels))
    train = evidence_table(train_labels, load_series(resolve(args.train_series)))
    test_labels = gpd.read_parquet(resolve(args.test_labels))
    test = evidence_table(test_labels, load_series(resolve(args.test_series)))
    for name, table, labels in [("train", train, train_labels), ("test", test, test_labels)]:
        print(f"{name}: {len(table)} field-years with a series "
              f"({int(table['is_silage'].sum())} silage, {int((1 - table['is_silage']).sum())} grain), "
              f"{int((~table['assessable']).sum())} not assessable")
    if len(test) < len(test_labels):
        print(f"WARNING: {len(test_labels) - len(test)} test field-years have no series yet")

    report = []
    block_call = held_out_block_calls(train, spatial_blocks(train_labels))
    report.append({"check": "quebec_held_out_blocks", **scores(train["is_silage"].to_numpy(), block_call)})

    fit_part = train[train["assessable"]]
    model = make_model().fit(fit_part[MODEL_FEATURES], fit_part["is_silage"])
    truth = test["is_silage"].to_numpy()
    probability, call = predict_silage(model, test)
    report.append({"check": "maryland_always_grain", **scores(truth, np.zeros(len(test), int))})
    report.append({"check": "maryland_from_quebec", **scores(truth, call)})
    report = pd.DataFrame(report)

    by_year = pd.DataFrame([
        {"year": year, **scores(truth[(test["year"] == year).to_numpy()], call[(test["year"] == year).to_numpy()])}
        for year in sorted(test["year"].unique())
    ])
    logistic = model.named_steps["logisticregression"]
    coefficients = pd.DataFrame({"feature": MODEL_FEATURES, "weight_per_std": logistic.coef_[0].round(3)})
    predictions = test[["field_id", "year", "label", "assessable"]].assign(
        p_silage=np.round(probability, 3), call=np.where(call == 1, "silage", "grain"))

    out = data / "models"
    out.mkdir(parents=True, exist_ok=True)
    tables = {"report": report, "by_year": by_year, "coefficients": coefficients, "maryland_predictions": predictions}
    for name, table in tables.items():
        target = out / f"field_model_{name}.csv"
        table.to_csv(target, index=False, lineterminator="\n")
        record_in_manifest(target, "derived: kernelag.field_model")

    pd.set_option("display.width", 200)
    print(report.to_string(index=False))
    print(by_year.to_string(index=False))
    print(coefficients.to_string(index=False))


if __name__ == "__main__":
    main()
