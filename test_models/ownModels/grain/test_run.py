"""Tests for test_models/ownModels/grain/run.py: tiers, the as-of rule, the candidates and the selection rule.

Run: .venv/Scripts/python.exe -m pytest -q test_models/ownModels/grain/test_run.py
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("grain_own_run", HERE / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


# --- synthetic FSA panel ----------------------------------------------------------------------------------------

def _files() -> pd.DataFrame:
    rows = [
        # zip, crop year, data date, published, vintage, status
        ("f23", 2023, "2024-01-02", "2024-01-07", "final", "ok"),
        ("n23", 2023, "2023-11-01", "2023-11-06", "nov", "ok"),
        ("o23", 2023, "2023-10-01", "2023-10-06", "oct", "ok"),
        ("s24", 2024, "2024-09-03", "2024-09-08", "sep", "ok"),
        ("o24", 2024, "2024-10-01", "2024-10-06", "oct", "corrupt"),
        ("n24", 2024, "2024-11-01", "2024-11-06", "nov", "ok"),
        ("f24", 2024, "2025-01-02", "2025-01-07", "final", "ok"),
    ]
    return pd.DataFrame(rows, columns=["zip_name", "crop_year", "data_as_of", "assumed_published", "vintage",
                                       "status"])


def _state() -> pd.DataFrame:
    acres = {  # (zip data date) -> (grain acres A, grain acres B, silage A)
        "2024-01-02": (900.0, 400.0, 50.0), "2023-11-01": (890.0, 395.0, 50.0), "2023-10-01": (880.0, 390.0, 50.0),
        "2024-09-03": (950.0, 0.0, 60.0), "2024-11-01": (990.0, 0.0, 60.0), "2025-01-02": (1000.0, 0.0, 60.0),
    }
    year = {"2024-01-02": 2023, "2023-11-01": 2023, "2023-10-01": 2023, "2024-09-03": 2024, "2024-11-01": 2024,
            "2025-01-02": 2024}
    rows = []
    for day, (ga, gb, sa) in acres.items():
        rows += [(year[day], day, "A", "grain", ga, 10.0), (year[day], day, "B", "grain", gb, 0.0),
                 (year[day], day, "A", "silage", sa, 0.0)]
    return pd.DataFrame(rows, columns=["crop_year", "data_as_of", "state", "intended_use", "planted_acres",
                                       "failed_acres"])


def _finals() -> pd.DataFrame:
    return pd.DataFrame({"year": [2022, 2022, 2023, 2023, 2024, 2024], "state": ["A", "B"] * 3,
                         "grain": [850.0, 380.0, 810.0, 440.0, 1000.0, 500.0], "planted": np.nan})


# --- tiers ------------------------------------------------------------------------------------------------------

def test_registered_candidates_have_expected_tiers():
    assert run.tier_of("g1_fsa_ratio") == "A"
    assert run.tier_of("g4_fsa_plus_stress") == "A"
    assert run.tier_of("g0_persistence") == "A"
    assert run.tier_of("nass_latest") == "X"
    assert set(run.OWN) == {"g1_fsa_ratio", "g2_fsa_planted_share", "g3_fsa_ratio_multi", "g4_fsa_plus_stress",
                            "g5_fsa_ratio_vintage"}


@pytest.mark.parametrize("source", ["nass_crop_condition_progress", "nass_current_year_planted",
                                    "nass_current_year_yield_forecast", "nass_current_year_grain_forecast"])
def test_own_candidate_with_nass_current_year_input_is_refused(source):
    bad = {**run.CANDIDATES, "g9_bad": {"role": "own", "sources": ["fsa_files_published_by_asof", source]}}
    with pytest.raises(ValueError, match="g9_bad"):
        run.check_tiers(bad)


def test_undeclared_source_is_refused():
    bad = {"g9": {"role": "own", "sources": ["mystery_feed"]}}
    with pytest.raises(ValueError, match="undeclared"):
        run.check_tiers(bad)


def test_nass_history_hides_target_year_and_later():
    hist = run.NassHistory(_finals(), 2024)
    assert hist.grain(2023)["A"] == 810.0
    with pytest.raises(PermissionError):
        hist.grain(2024)
    with pytest.raises(PermissionError):
        hist.grain(2025)


# --- as-of rule -------------------------------------------------------------------------------------------------

def test_current_file_is_latest_published_never_later():
    view = run.FsaView(_files(), _state(), date(2024, 10, 15), 2024)
    # October 2024 is corrupt: the September file stands in, never the November one.
    assert view.current()["zip_name"] == "s24"
    view = run.FsaView(_files(), _state(), date(2024, 11, 5), 2024)
    assert view.current()["zip_name"] == "s24"          # November file published 6 Nov
    view = run.FsaView(_files(), _state(), date(2024, 11, 15), 2024)
    assert view.current()["zip_name"] == "n24"


def test_own_final_file_is_never_in_season_input():
    view = run.FsaView(_files(), _state(), date(2025, 2, 1), 2024)
    assert view.current()["zip_name"] == "n24"           # the 2024 final (published Jan 2025) is not used
    assert view.final(2024) is None
    assert view.final(2023)["zip_name"] == "f23"


def test_acres_refuses_a_file_not_usable_on_the_asof_date():
    files = _files()
    view = run.FsaView(files, _state(), date(2024, 9, 15), 2024)
    later = files[files["zip_name"] == "n24"].iloc[0]
    with pytest.raises(PermissionError):
        view.acres(later, "grain")


def test_acres_measures():
    view = run.FsaView(_files(), _state(), date(2024, 11, 15), 2024)
    cur = view.current()
    assert view.acres(cur, "grain")["A"] == 990.0
    assert view.acres(cur, "all")["A"] == 990.0 + 10.0 + 60.0     # planted + failed, every use


def test_closest_reference_file_by_calendar_day():
    view = run.FsaView(_files(), _state(), date(2024, 11, 15), 2024)
    assert view.closest(2023, date(2024, 11, 1))["zip_name"] == "n23"
    assert view.closest(2023, date(2024, 9, 3))["zip_name"] == "o23"   # 28 days from 1 Oct, 63 from 1 Nov


def test_closest_tie_goes_to_the_later_file():
    files = pd.DataFrame([("a", 2023, "2023-10-01", "2023-10-06", "oct", "ok"),
                          ("b", 2023, "2023-10-21", "2023-10-26", "nov", "ok")],
                         columns=["zip_name", "crop_year", "data_as_of", "assumed_published", "vintage", "status"])
    view = run.FsaView(files, _state(), date(2024, 11, 15), 2024)
    assert view.closest(2023, date(2024, 10, 11))["zip_name"] == "b"


# --- candidates -------------------------------------------------------------------------------------------------

def test_guard_falls_back_to_persistence():
    last = pd.Series({"A": 100.0, "B": 200.0, "C": 300.0, "D": 400.0})
    current = pd.Series({"A": 90.0, "B": 0.0, "C": 50.0})
    multiplier = pd.Series({"A": 1.1, "B": 1.0, "C": 10.0, "D": 1.0})
    out = run.guarded(current, multiplier, last)
    assert out.loc["A", "pred"] == pytest.approx(99.0)
    assert list(out["method"]) == ["fsa", "fallback_persistence", "fallback_persistence", "fallback_persistence"]
    assert list(out.loc[["B", "C", "D"], "pred"]) == [200.0, 300.0, 400.0]


def test_g1_ratio_formula_and_fallback_state():
    hist = run.NassHistory(_finals(), 2024)
    view = run.FsaView(_files(), _state(), date(2024, 11, 15), 2024)
    table, used = run.predict_fsa("g1_fsa_ratio", hist, view)
    assert table.loc["A", "pred"] == pytest.approx(990.0 * 810.0 / 900.0)
    assert table.loc["B", "method"] == "fallback_persistence"     # no FSA grain acres for B in 2024
    assert table.loc["B", "pred"] == 440.0
    assert used == {"current": "n24", "current_data_as_of": "2024-11-01", "reference": "f23",
                    "reference_data_as_of": "2024-01-02"}


def test_g5_uses_same_point_of_last_season():
    hist = run.NassHistory(_finals(), 2024)
    view = run.FsaView(_files(), _state(), date(2024, 9, 15), 2024)
    table, used = run.predict_fsa("g5_fsa_ratio_vintage", hist, view)
    assert used["current"] == "s24" and used["reference"] == "o23"
    assert table.loc["A", "pred"] == pytest.approx(950.0 * 810.0 / 880.0)


def test_g3_takes_median_of_available_years():
    hist = run.NassHistory(_finals(), 2024)
    view = run.FsaView(_files(), _state(), date(2024, 11, 15), 2024)
    table, used = run.predict_fsa("g3_fsa_ratio_multi", hist, view)
    assert used["reference"] == "f23"                       # only one usable final file in the synthetic panel
    assert table.loc["A", "pred"] == pytest.approx(990.0 * 810.0 / 900.0)


def test_missing_current_file_means_persistence_everywhere():
    hist = run.NassHistory(_finals(), 2024)
    view = run.FsaView(_files(), _state(), date(2024, 8, 15), 2024)
    table, used = run.predict_fsa("g1_fsa_ratio", hist, view)
    assert used["current"] is None
    assert (table["method"] == "fallback_persistence").all()
    assert table["pred"].tolist() == [810.0, 440.0]


def test_ridge_shrinks_and_has_no_intercept():
    x = np.zeros((20, 2))
    y = np.full(20, 0.3)
    coef, _ = run.fit_ridge(x, y, np.ones(20))
    assert np.allclose(coef, 0.0)                            # no intercept: a constant offset is not absorbed
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 2))
    y = 0.1 * x[:, 0]
    coef, scale = run.fit_ridge(x, y, np.ones(200))
    assert 0 < coef[0] / scale[0] < 0.1 and abs(coef[1]) < 0.01


# --- scoring and selection --------------------------------------------------------------------------------------

def test_paired_ci_is_deterministic_and_centred():
    d = np.array([0.1, 0.2, 0.3, 0.4])
    first, second = run.paired_ci(d, boot=500), run.paired_ci(d, boot=500)
    assert first == second
    assert first[0] == pytest.approx(0.25) and first[1] <= 0.25 <= first[2]


def _by_year(gain: float, noise: float) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(1)
    for year in range(2012, 2025):
        base = 2.0 + rng.normal(scale=0.2)
        for name in run.OWN:
            wape = base + (-gain + rng.normal(scale=noise) if name == "g3_fsa_ratio_multi" else 0.0)
            wape += 0.05 if name in ("g2_fsa_planted_share", "g4_fsa_plus_stress", "g5_fsa_ratio_vintage") else 0.0
            rows.append({"candidate": name, "asof": "nov", "year": year, "state_wape_pct": wape})
    return pd.DataFrame(rows)


def test_selection_keeps_simplest_unless_two_se_better():
    clear = run.select(_by_year(gain=0.5, noise=0.05), "nov")
    assert clear["best"] == "g3_fsa_ratio_multi" and clear["selected"] == "g3_fsa_ratio_multi"
    noisy = run.select(_by_year(gain=0.1, noise=1.0), "nov")
    assert noisy["selected"] == "g1_fsa_ratio"


def test_score_years_wape_and_us_error():
    finals = _finals()
    pred = pd.DataFrame({"candidate": "x", "asof": "nov", "year": 2024, "state": ["A", "B"],
                         "pred": [1100.0, 450.0]})
    row = run.score_years(pred, finals).iloc[0]
    assert row["state_wape_pct"] == pytest.approx(100 * 150 / 1500)
    assert row["us_error_pct"] == pytest.approx(100 * 50 / 1500)


# --- real data (skipped when the panel is absent) ---------------------------------------------------------------

needs_data = pytest.mark.skipif(not (run.DATA / "fsa" / "fsa_files.csv").exists(), reason="FSA panel not built")


@needs_data
def test_real_asof_choices_for_gap_years():
    files, state = run.load_fsa()
    assert run.FsaView(files, state, date(2025, 11, 15), 2025).current()["vintage"] == "sep"   # shutdown
    # Nov 2015 was a truncated download when the backtest was first run; the re-downloaded file now parses.
    assert run.FsaView(files, state, date(2015, 11, 15), 2015).current()["vintage"] == "nov"
    assert run.FsaView(files, state, date(2026, 11, 15), 2026).current()["data_as_of"] == "2026-11-05"
    assert run.FsaView(files, state, date(2012, 11, 15), 2012).final(2011)["vintage"] == "final"


@needs_data
def test_real_finals_cover_41_states_and_exclude_2026():
    finals = run.load_finals()
    assert finals["year"].max() == run.LAST_TRUTH_YEAR
    for year in range(2011, 2026):
        assert run.truth(finals, year).size == 41
