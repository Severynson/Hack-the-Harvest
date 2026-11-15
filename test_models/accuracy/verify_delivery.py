"""Audit exported claims against the real cached inputs without rewriting the locked 2025 score."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from kernelag import evaluate, report, state_model
from kernelag.field_model import (
    MODEL_FEATURES,
    load_series,
    load_training,
    make_model,
    predict_silage,
)
from kernelag.paths import data_dir
from kernelag.state_panel import load_panel


def main() -> None:
    data = data_dir()
    models = data / "models"
    metrics = report.gather(models)
    selected = metrics["state_model"]["selected_silage_set"]
    panel = state_model.add_changes(load_panel())
    historical = state_model.backtest_predictions(panel)
    score_path = models / "state_score_2025.json"
    score_hash = hashlib.sha256(score_path.read_bytes()).hexdigest()
    _, reproduced = state_model.score(state_model.forecast(panel, 2025, selected, historical), panel, 2025)
    if reproduced != metrics["score_2025"]:
        raise AssertionError("stored 2025 score does not match the current model/data; do not relabel it")
    if hashlib.sha256(score_path.read_bytes()).hexdigest() != score_hash:
        raise AssertionError("verification must not rewrite the separate 2025 score")
    forecast = state_model.forecast(panel, report.FORECAST_YEAR, selected, historical)
    stored_forecast = pd.read_csv(models / f"state_forecast_{report.FORECAST_YEAR}.csv")
    pd.testing.assert_frame_equal(forecast.reset_index(drop=True), stored_forecast, check_dtype=False)

    train, _ = load_training(data)
    fit = train[train["assessable"]]
    model = make_model().fit(fit[MODEL_FEATURES], fit["is_silage"])
    labels = gpd.read_parquet(data / "labels" / "barc_2021_2023.parquet")
    series = load_series(data / "s2_series" / "barc_2021_2023")
    fields = evaluate.evaluation_table(labels, series)
    probability, calls = predict_silage(model, fields)
    actual_rates = evaluate.extended_scores(fields["is_silage"].to_numpy(), calls)
    if actual_rates != metrics["field_eval"]["rates"]:
        raise AssertionError("exported field rates differ from current training and test data")
    if evaluate.bootstrap_intervals(fields["is_silage"].to_numpy(), calls,
                                    groups=fields["field_id"].to_numpy()) != metrics["field_eval"]["intervals_90"]:
        raise AssertionError("field-cluster confidence intervals are not reproducible")
    if evaluate.selective_summary(fields["is_silage"].to_numpy(), probability) != metrics["field_eval"]["selective"]:
        raise AssertionError("operational abstention results are not reproducible")
    coefficients = pd.read_csv(models / "field_model_coefficients.csv").set_index("feature")["weight_per_std"]
    np.testing.assert_allclose(coefficients.reindex(MODEL_FEATURES),
                               model.named_steps["logisticregression"].coef_[0].round(3))
    pd.testing.assert_frame_equal(evaluate.earliness(model, labels, series),
                                  pd.read_csv(models / "field_earliness.csv"), check_dtype=False)
    exported_comparison = pd.read_csv(models / "verified_metrics.csv")
    pd.testing.assert_frame_equal(report.comparison_rows(metrics, pd.read_csv(models / "state_model_backtest.csv")),
                                  exported_comparison, check_dtype=False)
    saved = json.loads((models / "metrics.json").read_text())
    for name, digest in saved["source_sha256"].items():
        if hashlib.sha256((models / name).read_bytes()).hexdigest() != digest:
            raise AssertionError(f"report source changed after generation: {name}")
    result = {"forecast_reproduced": True, "stored_2025_score_reproduced_without_overwrite": True,
              "field_rates_and_weights_reproduced": True, "earliness_reproduced": True,
              "field_intervals_and_abstentions_reproduced": True,
              "comparison_table_reproduced": True, "report_source_hashes_verified": True,
              "field_years": len(fields), "unique_fields": fields["field_id"].nunique(),
              "selected_silage_set": selected, "stored_2025_sha256": score_hash}
    output = Path(__file__).with_name("delivery_audit.json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
