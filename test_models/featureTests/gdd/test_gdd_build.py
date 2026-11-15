"""Tests for the thermal-time feature builder (test_models/featureTests/gdd/build.py).

Offline and fast: synthetic weather and dates, plus a schema check of the built outputs when they exist.
Run: ``.venv/Scripts/python.exe -m pytest -q test_models/featureTests/gdd/test_gdd_build.py``
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
# Loaded under a unique name: sibling feature groups also have a build.py.
_spec = importlib.util.spec_from_file_location("gdd_build", HERE / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def weather(year: int, tmax: float, tmin: float, start: str = "05-01", end: str = "11-30") -> pd.DataFrame:
    dates = pd.date_range(f"{year}-{start}", f"{year}-{end}", freq="D")
    return pd.DataFrame({"date": dates, "tmax_c": tmax, "tmin_c": tmin})


def test_daily_gdd_caps_and_floors():
    # Hot day: Tmax capped at 30, Tmin floored at 10 -> (30 + 10) / 2 - 10 = 10.
    assert build.daily_gdd(35.0, 5.0) == pytest.approx(10.0)
    assert build.daily_gdd(20.0, 12.0) == pytest.approx(6.0)
    # A cold day adds zero, never negative thermal time.
    assert build.daily_gdd(8.0, 2.0) == pytest.approx(0.0)
    assert np.isnan(build.daily_gdd(np.nan, 12.0))
    # Fahrenheit check from the research note: Tmax 60 F, Tmin 50 F gives about 5 F-days = 2.78 C-days.
    assert build.daily_gdd((60 - 32) / 1.8, 10.0) * 1.8 == pytest.approx(5.0)


def test_cumulative_from_may_first_includes_the_day():
    cum = build.cumulative_gdd(weather(2023, 20.0, 12.0))   # 6 C-days every day
    may1 = pd.Timestamp("2023-05-01").day_of_year
    assert cum[float(may1)] == pytest.approx(6.0)
    assert cum[float(may1 + 9)] == pytest.approx(60.0)
    oct31 = pd.Timestamp("2023-10-31").day_of_year
    assert build.season_total(cum, 2023) == pytest.approx(6.0 * (oct31 - may1 + 1))


def test_cumulative_ignores_days_before_may():
    early = weather(2023, 25.0, 15.0, start="04-20")
    cum = build.cumulative_gdd(early)
    assert cum.index.min() == pd.Timestamp("2023-05-01").day_of_year
    assert cum.iloc[0] == pytest.approx(10.0)


def test_gap_makes_later_cumulative_values_missing():
    w = weather(2023, 20.0, 12.0)
    gap_day = pd.Timestamp("2023-07-01")
    w.loc[w["date"] == gap_day, "tmax_c"] = np.nan
    cum = build.cumulative_gdd(w)
    assert not np.isnan(cum[float(gap_day.day_of_year - 1)])
    assert np.isnan(cum[float(gap_day.day_of_year)])
    assert np.isnan(build.season_total(cum, 2023))


def test_thermal_features_known_values_and_missing_dates():
    cums = {("79_515", 2023): build.cumulative_gdd(weather(2023, 20.0, 12.0))}
    may1 = pd.Timestamp("2023-05-01").day_of_year
    oct31 = pd.Timestamp("2023-10-31").day_of_year
    base = pd.DataFrame({
        "field_id": ["a", "b", "c", "d"], "year": [2023, 2023, 2023, 2023],
        "cell": ["79_515", "79_515", "79_515", "99_999"],
        "peak_doy": [200, 200, np.nan, 200], "cut_doy": [260, np.nan, 260, 260],
    })
    out = build.thermal_features(base, cums).set_index("field_id")
    total = 6.0 * (oct31 - may1 + 1)
    assert out.loc["a", "gdd_at_cut"] == pytest.approx(6.0 * (260 - may1 + 1))
    assert out.loc["a", "gdd_peak_to_cut"] == pytest.approx(6.0 * 60)
    assert out.loc["a", "gdd_share_at_cut"] == pytest.approx(6.0 * (260 - may1 + 1) / total)
    assert out.loc["a", "gdd_season_may_oct"] == pytest.approx(total)
    # No cut date: every cut-based value stays missing.
    assert out.loc["b", ["gdd_at_cut", "gdd_peak_to_cut", "gdd_share_at_cut"]].isna().all()
    # No peak date: only the peak-to-cut gap is missing.
    assert np.isnan(out.loc["c", "gdd_peak_to_cut"]) and not np.isnan(out.loc["c", "gdd_share_at_cut"])
    # No weather for the cell: everything missing, nothing guessed.
    assert out.loc["d", build.FEATURE_COLUMNS].isna().all()


def test_cell_centre_of_training_cell():
    lat, lon = build.cell_centre("79_515", "EPSG:32618")
    assert lat == pytest.approx(46.484, abs=0.01)
    assert lon == pytest.approx(-71.156, abs=0.01)


def test_replace_datasets_keeps_other_datasets():
    old = pd.DataFrame({"dataset": ["x", "y"], "field_id": ["1", "2"], "year": [2023, 2023], "gdd_at_cut": [1.0, 2.0]})
    new = pd.DataFrame({"dataset": ["y"], "field_id": ["3"], "year": [2023], "gdd_at_cut": [5.0]})
    merged = build.replace_datasets(old, [new], ["y"], build.KEYS)
    assert merged["field_id"].tolist() == ["1", "3"]
    assert build.replace_datasets(None, [], ["y"], build.KEYS) is None


def test_preregistered_features_are_fixed():
    assert build.MODEL_FEATURES == ["gdd_peak_to_cut", "gdd_share_at_cut"]
    assert len(build.MODEL_FEATURES) <= 3
    assert all(column.startswith("gdd_") for column in build.FEATURE_COLUMNS)


@pytest.mark.skipif(not (HERE / "out" / "features.csv").exists(), reason="build.py has not been run")
def test_built_outputs_follow_the_contract():
    features = pd.read_csv(HERE / "out" / "features.csv", dtype={"field_id": str})
    assert features.columns.tolist() == [*build.KEYS, *build.FEATURE_COLUMNS]
    assert not features.duplicated(build.KEYS).any()
    meta = json.loads((HERE / "out" / "meta.json").read_text(encoding="utf-8"))
    assert meta["group"] == "gdd"
    assert meta["features"] == build.MODEL_FEATURES
    assert set(meta["datasets_built"]) == set(features["dataset"])
    share = features["gdd_share_at_cut"].dropna()
    assert ((share > 0) & (share < 1.2)).all()   # cuts happen by late October, so the share is near or below 1
