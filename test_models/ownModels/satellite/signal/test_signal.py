"""Tests for the satellite state-share signal: consistency with kernelag.state_signal, forecast-date cut,
estimator arithmetic and output schema.

Run from the repo root: .venv/Scripts/python.exe -m pytest -q test_models/ownModels/satellite/signal/test_signal.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
# Loaded by path under its own name: "signal" would collide with the standard-library module.
_spec = importlib.util.spec_from_file_location("satellite_signal", HERE / "signal.py")
sig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sig)

from kernelag import state_signal  # noqa: E402
from kernelag.field_model import MODEL_FEATURES, load_series, make_model  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402

STATE = "55"


def toy_model():
    """A model with the field model's form, fitted on random features (fast; only consistency is tested)."""
    rng = np.random.default_rng(0)
    x = pd.DataFrame(rng.normal(size=(200, len(MODEL_FEATURES))), columns=MODEL_FEATURES)
    y = (x["max_drop"] + rng.normal(scale=0.5, size=200) > 0).astype(int)
    return make_model().fit(x, y)


@pytest.fixture(scope="module")
def small_state():
    """One real sample area of Wisconsin, two corn years, with its series."""
    import geopandas as gpd

    path = data_dir() / "samples" / f"corn_{STATE}.parquet"
    folder = data_dir() / "s2_series" / f"corn_{STATE}"
    if not path.exists() or not folder.is_dir():
        pytest.skip("state sample not on disk")
    sample = sig.clean_sample(gpd.read_parquet(path))
    cell = sorted(sample["cell"].unique())[0]
    sample = sample[(sample["cell"] == cell) & sample["year"].isin([2022, 2023])].reset_index(drop=True)
    files = [folder / f"{cell}_{year}.csv" for year in (2022, 2023)]
    series = pd.concat([load_series(f) for f in files], ignore_index=True)
    return sample, series


def test_area_totals_match_kernelag(small_state):
    sample, series = small_state
    model = toy_model()
    cut = state_signal.series_asof(series, "nov")
    reference = state_signal.area_totals(sample.drop(columns="state_fips"), cut, model)
    _, totals, _ = sig.state_shares(sample, series, model, "nov", detail=True)
    columns = ["cell", "year", "fields", "sampled_acres", "corn_acres", "silage_like_acres", "called_silage_acres",
               "median_cut_doy"]
    left = totals[columns].sort_values(["cell", "year"]).reset_index(drop=True)
    right = reference[columns].sort_values(["cell", "year"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right, check_dtype=False)


def test_forecast_date_cut_ignores_later_looks(small_state):
    sample, series = small_state
    model = toy_model()
    late = series["date"] > pd.to_datetime(series["year"].astype(str) + "-10-15")
    scrambled = series.copy()
    scrambled.loc[late, ["ndvi", "ndmi", "ndti"]] = 0.99   # anything after 15 Oct must not matter
    a = sig.state_shares(sample, series, model, "oct")
    b = sig.state_shares(sample, scrambled, model, "oct")
    pd.testing.assert_frame_equal(a, b)
    assert (pd.to_datetime(a["last_observation_date"]) <= pd.to_datetime(a["asof_date"])).all()


def test_leading_zero_ids_join_after_numeric_read():
    sample_ids = pd.Series(["061825011676588", "061825011676598"])
    series_ids = pd.Series(["61825011676588", "61825011676598", "61825000000001"])   # as load_series returns them
    aligned = sig.align_field_ids(series_ids, sample_ids)
    assert aligned.tolist()[:2] == sample_ids.tolist()
    assert pd.isna(aligned.iloc[2])


def test_no_series_means_nothing_assessable(small_state):
    sample, _ = small_state
    table = sig.state_shares(sample, pd.DataFrame(columns=["field_id", "year", "date"]), toy_model(), "nov")
    assert table.empty


def toy_totals() -> pd.DataFrame:
    return pd.DataFrame({
        "state_fips": "99", "cell": ["a", "b", "c", "a", "b", "c"], "year": [2020] * 3 + [2021] * 3,
        "cell_size_acres": [100.0, 200.0, 400.0] * 2,
        "corn_acres": [50.0, 100.0, 100.0, 60.0, 80.0, 120.0],
        "silage_like_acres": [10.0, 30.0, 20.0, 18.0, 16.0, 30.0],
        "called_silage_acres": [0.0, 40.0, 0.0, 20.0, 0.0, 40.0],
    })


def test_share_weights_each_area_by_its_size():
    t = toy_totals()
    y = t[t["year"] == 2020]
    expected = (10 / 100 + 30 / 200 + 20 / 400) / (50 / 100 + 100 / 200 + 100 / 400)
    assert state_signal.share(y) == pytest.approx(expected)


def test_change_jackknife_leaves_area_out_of_both_years():
    t = toy_totals()
    changes = sig.share_changes(t)
    assert len(changes) == 1
    row = changes.iloc[0]

    def d(frame):
        return state_signal.share(frame[frame["year"] == 2021]) - state_signal.share(frame[frame["year"] == 2020])

    assert row["d_share"] == pytest.approx(d(t), abs=1e-5)
    left_out = np.array([d(t[t["cell"] != c]) for c in "abc"])
    se = np.sqrt(2 / 3 * ((left_out - left_out.mean()) ** 2).sum())
    assert row["se_d_share"] == pytest.approx(se, abs=1e-5)
    log_change = np.log(state_signal.share(t[t["year"] == 2021]) / state_signal.share(t[t["year"] == 2020]))
    assert row["d_log_share"] == pytest.approx(log_change, abs=1e-5)


def test_duplicate_field_years_refused(small_state):
    sample, series = small_state
    with pytest.raises(ValueError):
        sig.state_shares(pd.concat([sample, sample.head(1)]), series, toy_model(), "nov")


@pytest.mark.parametrize("asof", sig.ASOFS)
def test_written_outputs_have_the_contract(asof):
    path = sig.OUT / f"state_satellite_asof_{asof}.csv"
    if not path.exists():
        pytest.skip("outputs not built yet")
    table = pd.read_csv(path, dtype={"state_fips": str})
    assert list(table.columns[: len(sig.OUTPUT_COLUMNS)]) == sig.OUTPUT_COLUMNS
    assert not table.duplicated(["state", "year"]).any()
    assert table["year"].between(2019, 2025).all()
    assert table["sat_share"].between(0, 1).all()
    assert (pd.to_datetime(table["last_observation_date"]) <= pd.to_datetime(table["asof_date"])).all()
