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
