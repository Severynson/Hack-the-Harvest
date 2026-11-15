import numpy as np
import pandas as pd

from kernelag import evaluate


def test_cut_off_never_keeps_later_looks():
    series = pd.DataFrame({
        "field_id": ["1"] * 4, "year": [2021, 2021, 2022, 2022],
        "date": pd.to_datetime(["2021-09-30", "2021-10-02", "2022-10-01", "2022-11-20"]),
    })
    kept = evaluate.cut_off(series, "10-01")
    assert list(kept["date"].dt.strftime("%Y-%m-%d")) == ["2021-09-30", "2022-10-01"]


def test_bootstrap_interval_brackets_the_point_rate():
    truth = np.array([1] * 10 + [0] * 30)
    call = np.array([1] * 8 + [0] * 2 + [1] * 3 + [0] * 27)
    intervals = evaluate.bootstrap_intervals(truth, call, draws=500)
    low, high = intervals["silage_recall"]
    assert low <= 0.8 <= high and low < high
    low, high = intervals["false_positive_rate"]
    assert low <= 0.1 <= high


def test_earliness_keeps_fields_with_no_early_observations():
    labels = pd.DataFrame({"field_id": ["1", "2"], "year": [2021, 2021],
                           "label": ["silage", "grain"]})
    series = pd.DataFrame({"field_id": ["1"], "year": [2021],
                           "date": pd.to_datetime(["2021-10-10"]),
                           "ndvi": [0.8], "ndmi": [0.3], "ndti": [0.1], "valid_frac": [1.]})
    class NoEvidenceModel:
        def predict_proba(self, _):
            raise AssertionError("no assessable fields should reach the model")
    result = evaluate.earliness(NoEvidenceModel(), labels, series, ["09-01", "11-01"])
    assert result["field_years"].tolist() == [2, 2]
    assert result["not_assessable"].tolist() == [2, 2]
    assert result["FN"].tolist() == [1, 1]
    assert result["TN"].tolist() == [1, 1]


def test_balanced_accuracy_f1_and_abstention_policy():
    truth = np.array([1, 1, 1, 0, 0, 0, 0])
    call = np.array([1, 1, 0, 1, 0, 0, 0])
    rates = evaluate.extended_scores(truth, call)
    assert rates["silage_f1"] == 0.667
    assert rates["balanced_accuracy"] == 0.708
    operational = evaluate.selective_summary(np.array([1, 0, 1, 0]), np.array([np.nan, .5, .9, .1]))
    assert operational["calls"] == ["not assessable", "uncertain", "silage-like", "grain-like"]
    assert operational["coverage"] == .5
    assert operational["complete_roster_silage_recall"] == .5
    assert operational["rates_on_decisive_fields"]["accuracy"] == 1.
