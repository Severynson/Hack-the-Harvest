"""Checks for corn26.py: the share arithmetic equals kernelag.state_signal, and nothing after the cut is used.

Run: .venv/Scripts/python.exe -m pytest -q test_models/ownModels/satellite/corn26/test_corn26.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import corn26  # noqa: E402
from kernelag import state_signal  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402

FIPS = "36"   # New York: a small state file


def small_state():
    """Two areas of one state's 2025 candidates with their 2025 series (cut at Nov 15)."""
    candidates = corn26.candidates_2025(FIPS)
    cells = sorted(candidates["cell"].unique())[:2]
    candidates = candidates[candidates["cell"].isin(cells)].reset_index(drop=True)
    data = data_dir()
    series = pd.concat([corn26.read_series(data / "s2_series" / f"corn_{FIPS}", [2025]),
                        corn26.read_series(data / "s2_series" / f"noncorn25_{FIPS}", [2025])], ignore_index=True)
    series = series[series["field_id"].isin(set(candidates["field_id"]))]
    return candidates, state_signal.series_asof(series, "nov")


@pytest.fixture(scope="module")
def fitted():
    """A field model fitted on the small Quebec set only (fast); arithmetic does not depend on which fit."""
    import geopandas as gpd
    from kernelag.field_model import MODEL_FEATURES, evidence_table, load_series, make_model

    data = data_dir()
    labels = gpd.read_parquet(data / "labels" / "quebec_maize_2023.parquet")
    train = evidence_table(labels, load_series(data / "s2_series" / "quebec_maize_2023"))
    train = train[train["assessable"]]
    return make_model().fit(train[MODEL_FEATURES], train["is_silage"])


def test_area_totals_match_state_signal(fitted):
    candidates, series = small_state()
    keep = ["field_id", "year", "cell", "cell_size_acres", "acres"]
    for mask in [candidates["is_corn"] == 1, candidates["history_corn"] == 1]:
        sample = candidates.loc[mask.to_numpy(), keep].reset_index(drop=True)
        expected = state_signal.area_totals(sample, series[series["field_id"].isin(set(sample["field_id"]))], fitted)
        evidence = corn26.field_evidence(series, "nov")
        got = corn26.area_totals_from_features(sample, evidence, fitted)
        pd.testing.assert_frame_equal(got.reset_index(drop=True), expected.reset_index(drop=True),
                                      check_dtype=False)
        assert corn26.mask_share(sample, evidence, fitted)["sat_share"] == state_signal.state_table(
            expected).iloc[0]["sat_share"]


def test_corn_features_ignore_looks_after_the_cut():
    _, series = small_state()
    one = series[series["field_id"] == series["field_id"].iloc[0]]
    late = one.iloc[[-1]].assign(date=pd.Timestamp("2025-11-20"), ndvi=0.99, ndmi=0.9, valid_frac=1.0)
    before = corn26.corn_features(one, "nov")
    after = corn26.corn_features(pd.concat([one, late], ignore_index=True), "nov")
    pd.testing.assert_frame_equal(before, after)
    sep = corn26.corn_features(one, "sep")
    assert sep[[c for c in corn26.CORN_FEATURES if c not in corn26.features_for("sep")]].isna().all().all()


def test_features_for_cut_dates():
    assert corn26.features_for("nov")[-1] == "ndvi_b12"          # Nov 9-24 bin starts before Nov 15
    assert "ndvi_m10" not in corn26.features_for("sep")
    assert "ndvi_b09" not in corn26.features_for("sep") and "ndvi_b08" in corn26.features_for("sep")


def test_leading_zero_field_ids_join():
    """California ids start with 0; every sampled 2025 field of one area must find its series."""
    candidates = corn26.candidates_2025("06")
    cell = sorted(candidates["cell"].unique())[0]
    series = corn26.read_series(data_dir() / "s2_series" / "corn_06", [2025])
    corn = candidates[(candidates["cell"] == cell) & (candidates["is_corn"] == 1)]
    assert corn["field_id"].isin(set(series["field_id"])).mean() > 0.95


def test_call_metrics_counts():
    frame = pd.DataFrame({"is_corn": [1, 1, 0, 0], "p": [0.9, 0.2, 0.6, 0.1], "acres": [10.0, 10, 5, 5],
                          "cell_size_acres": [1.0, 1, 1, 1], "n_clear": [5, 5, 5, 0]})
    m = corn26.call_metrics(frame, "p")
    assert (m["TP"], m["FP"], m["FN"], m["TN"]) == (1, 1, 1, 1)
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["n_no_clear_look"] == 1
    assert np.isclose(m["corn_acre_ratio"], 15 / 20)
