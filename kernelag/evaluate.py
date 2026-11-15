"""Rubric evidence for the field model: error rates with intervals, response time and earliness.

The model is ``kernelag.field_model``'s, fitted on the Quebec declarations and never on Maryland.
The test set is the organizers' labeled Maryland field-years (44: small, one research farm).

Three things are measured on that test set:
    rates       silage precision, recall, false positive rate and accuracy, each with a 90%
                bootstrap interval (field-years resampled with replacement).
    response    seconds to turn one field's finished series into a call (features + model),
                and seconds to fit the model. Downloading imagery is not included.
    earliness   the same test, but each field's series is cut off at an as-of date. A field
                with no harvest drop yet is "not assessable" and scored as grain, as everywhere.

Outputs (``data/models/``): field_eval.json, field_earliness.csv

Run: ``python -m kernelag.evaluate``
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

from kernelag.field_model import (MODEL_FEATURES, evidence_table, load_series, make_model,
                                  predict_silage, scores)
from kernelag.paths import data_dir, record_in_manifest

RATES = ["silage_precision", "silage_recall", "false_positive_rate", "accuracy"]
ASOF_DATES = ["09-01", "09-15", "10-01", "10-15", "11-01", "11-15", "12-31"]   # month-day
BOOTSTRAP_DRAWS = 2000
INTERVAL = (0.05, 0.95)
TIMING_REPEATS = 5


def bootstrap_intervals(truth: np.ndarray, call: np.ndarray, draws: int = BOOTSTRAP_DRAWS,
                        seed: int = 0) -> dict:
    """90% interval per rate: field-years resampled with replacement; undefined draws are skipped."""
    rng = np.random.default_rng(seed)
    samples = {rate: [] for rate in RATES}
    for _ in range(draws):
        rows = rng.integers(0, len(truth), len(truth))
        result = scores(truth[rows], call[rows])
        for rate in RATES:
            if result[rate] == result[rate]:
                samples[rate].append(result[rate])
    return {rate: [round(float(np.quantile(values, q)), 3) for q in INTERVAL] if values else [None, None]
            for rate, values in samples.items()}


def cut_off(series: pd.DataFrame, month_day: str) -> pd.DataFrame:
    """The series as it stood on ``month_day`` of each field's own year: later looks are removed."""
    limit = pd.to_datetime(series["year"].astype(str) + "-" + month_day)
    return series[series["date"] <= limit]


def earliness(model, labels: pd.DataFrame, series: pd.DataFrame, dates: list[str] = ASOF_DATES) -> pd.DataFrame:
    """Rates on the test set when only looks up to each as-of date exist."""
    rows = []
    for month_day in dates:
        table = evidence_table(labels, cut_off(series, month_day))
        _, call = predict_silage(model, table)
        result = scores(table["is_silage"].to_numpy(), call)
        rows.append({"asof": month_day, "field_years": len(table),
                     "assessable_share": round(float(table["assessable"].mean()), 3),
                     **{key: result[key] for key in ["TP", "FP", "FN", "TN", *RATES]}})
    return pd.DataFrame(rows)


def response_time(model, labels: pd.DataFrame, series: pd.DataFrame, repeats: int = TIMING_REPEATS) -> float:
    """Median seconds per field-year for features plus prediction, over ``repeats`` full passes."""
    per_field = []
    for _ in range(repeats):
        start = time.perf_counter()
        table = evidence_table(labels, series)
        predict_silage(model, table)
        per_field.append((time.perf_counter() - start) / len(table))
    return float(np.median(per_field))


def main() -> None:
    import geopandas as gpd

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--train-labels", default="labels/quebec_maize_2023.parquet")
    parser.add_argument("--train-series", default="s2_series/quebec_maize_2023")
    parser.add_argument("--test-labels", default="labels/barc_2021_2023.parquet")
    parser.add_argument("--test-series", default="s2_series/barc_2021_2023")
    args = parser.parse_args()
    data = data_dir()

    train = evidence_table(gpd.read_parquet(data / args.train_labels), load_series(data / args.train_series))
    fit_part = train[train["assessable"]]
    start = time.perf_counter()
    model = make_model().fit(fit_part[MODEL_FEATURES], fit_part["is_silage"])
    fit_seconds = time.perf_counter() - start

    test_labels = gpd.read_parquet(data / args.test_labels)
    test_series = load_series(data / args.test_series)
    test = evidence_table(test_labels, test_series)
    truth = test["is_silage"].to_numpy()
    _, call = predict_silage(model, test)

    by_date = earliness(model, test_labels, test_series)
    result = {
        "train": {"region": "Quebec declared parcels", "field_years": int(len(fit_part)),
                  "silage": int(fit_part["is_silage"].sum())},
        "test": {"region": "Maryland (organizer labels)", "field_years": int(len(test)),
                 "silage": int(truth.sum()), "not_assessable": int((~test["assessable"]).sum())},
        "rates": scores(truth, call),
        "always_grain": scores(truth, np.zeros(len(test), int)),
        "intervals_90": bootstrap_intervals(truth, call),
        "response_seconds_per_field": round(response_time(model, test_labels, test_series), 4),
        "fit_seconds": round(fit_seconds, 3),
        "caveats": ["44 test field-years on one farm: intervals are wide",
                    "response time excludes the imagery download"],
    }

    out = data / "models"
    out.mkdir(parents=True, exist_ok=True)
    (out / "field_eval.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    by_date.to_csv(out / "field_earliness.csv", index=False, lineterminator="\n")
    for name in ["field_eval.json", "field_earliness.csv"]:
        record_in_manifest(out / name, "derived: kernelag.evaluate")

    pd.set_option("display.width", 200)
    print(json.dumps({k: result[k] for k in ["train", "test", "rates", "intervals_90",
                                             "response_seconds_per_field", "fit_seconds"]}, indent=1))
    print(by_date.to_string(index=False))


if __name__ == "__main__":
    main()
