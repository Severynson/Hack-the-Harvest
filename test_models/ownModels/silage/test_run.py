"""Tests for test_models/ownModels/silage/run.py: tiers, look-ahead guards, model arithmetic, selection rule.

Run: .venv/Scripts/python.exe -m pytest -q test_models/ownModels/silage/test_run.py
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("silage_own_run", HERE / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)

STATES = ["A", "B"]


def finals_table() -> pd.DataFrame:
    rows = []
    for year in range(2000, 2011):
        for i, state in enumerate(STATES):
            rows.append({"state": state, "year": year, "silage": 100.0 + year - 2000 + 10 * i,
                         "grain": 1000.0 + i, "planted": 1200.0 + i})
    return pd.DataFrame(rows)


# --- tiers -----------------------------------------------------------------------------------------------------

def test_registry_passes_tier_check():
    run.check_tiers()


def test_tier_a_candidate_with_condition_input_is_refused():
    bad = {"x": {"tier": "A", "inputs": ["nass_final_history", "nass_crop_condition"], "eligible": True}}
    with pytest.raises(ValueError, match="nass_crop_condition"):
        run.check_tiers(bad)


def test_tier_b_candidate_cannot_be_eligible():
    bad = {"x": {"tier": "B", "inputs": ["nass_final_history"], "eligible": True}}
    with pytest.raises(ValueError, match="eligible"):
        run.check_tiers(bad)


def test_target_year_finals_are_forbidden_for_tier_a_and_b():
    for tier in ("A", "B", "benchmark"):
        bad = {"x": {"tier": tier, "inputs": ["nass_final_target_year"], "eligible": False}}
        with pytest.raises(ValueError):
            run.check_tiers(bad)


def test_only_tier_a_candidates_are_eligible_and_selection_order_is_eligible():
    eligible = {name for name, spec_ in run.CANDIDATES.items() if spec_["eligible"]}
    assert all(run.CANDIDATES[name]["tier"] == "A" for name in eligible)
    assert set(run.SELECTION_ORDER) | {run.SIMPLEST} == eligible


# --- look-ahead guards -------------------------------------------------------------------------------------------

def test_nass_history_refuses_target_year_and_later():
    hist = run.NassHistory(finals_table(), STATES, 2005, start=2000)
    assert hist.get("silage", 2004)["A"] == 104.0
    with pytest.raises(run.LookAheadError):
        hist.get("silage", 2005)
    with pytest.raises(run.LookAheadError):
        hist.get("grain", 2007)
    assert hist.long("silage")["year"].max() == 2004


def test_nass_history_start_hides_earlier_years():
    hist = run.NassHistory(finals_table(), STATES, 2005, start=2003)
    assert np.isnan(hist.get("silage", 2002)["A"])
    assert hist.get("silage", 2003)["A"] == 103.0


def synthetic_fsa():
    files = pd.DataFrame([
        # crop year 2019 final, 2020 aug, 2020 sep (published after the as-of date), 2020 final
        {"zip_name": "f19", "crop_year": 2019, "data_as_of": "2020-01-02", "assumed_published": "2020-01-07",
         "vintage": "final", "status": "ok", "published_source": "assumed: data date + 5 days"},
        {"zip_name": "a20", "crop_year": 2020, "data_as_of": "2020-08-01", "assumed_published": "2020-08-06",
         "vintage": "aug", "status": "ok", "published_source": "assumed: data date + 5 days"},
        {"zip_name": "s20", "crop_year": 2020, "data_as_of": "2020-09-12", "assumed_published": "2020-09-17",
         "vintage": "sep", "status": "ok", "published_source": "assumed: data date + 5 days"},
        {"zip_name": "c20", "crop_year": 2020, "data_as_of": "2020-09-01", "assumed_published": "2020-09-06",
         "vintage": "sep", "status": "corrupt", "published_source": "assumed: data date + 5 days"},
        {"zip_name": "f20", "crop_year": 2020, "data_as_of": "2021-01-05", "assumed_published": "2021-01-10",
         "vintage": "final", "status": "ok", "published_source": "assumed: data date + 5 days"},
    ])
    index = pd.MultiIndex.from_tuples(
        [(2019, "2020-01-02", s) for s in STATES] + [(2020, "2020-08-01", s) for s in STATES]
        + [(2020, "2020-09-12", s) for s in STATES] + [(2020, "2021-01-05", s) for s in STATES],
        names=["crop_year", "data_as_of", "state"])
    acres = pd.DataFrame({"silage": [50, 60, 55, 66, 70, 80, 999, 999], "grain": [900] * 8,
                          "all": [1000] * 8}, index=index, dtype=float)
    return files, acres


def test_fsa_inputs_never_use_a_later_or_corrupt_file_or_the_own_final():
    files, acres = synthetic_fsa()
    current, prior, meta = run.fsa_inputs(files, acres, date(2020, 9, 15), 2020, STATES)
    assert meta["current_zip"] == "a20"            # sep file published 17 Sep; corrupt file skipped
    assert meta["prior_final_zip"] == "f19"
    assert current.loc["A", "silage"] == 55 and prior.loc["B", "silage"] == 60
    _, _, later = run.fsa_inputs(files, acres, date(2020, 11, 15), 2020, STATES)
    assert later["current_zip"] == "s20"           # never the 2020 final, published in January 2021


def test_fsa_inputs_without_any_file_are_missing():
    files, acres = synthetic_fsa()
    current, prior, meta = run.fsa_inputs(files, acres, date(2020, 7, 15), 2020, STATES)
    assert meta["current_zip"] is None and current["silage"].isna().all()
    assert prior.loc["A", "silage"] == 50


def test_lagged_files_shift_only_assumed_dates():
    files, _ = synthetic_fsa()
    files.loc[0, "published_source"] = "documented"
    out = run.lagged_files(files, 10)
    assert out.loc[0, "assumed_published"] == "2020-01-07"
    assert out.loc[1, "assumed_published"] == "2020-08-11"


# --- model arithmetic --------------------------------------------------------------------------------------------

def test_s3_raw_is_residual_times_last_silage_share_when_not_clipped():
    rows = pd.DataFrame({"F_all_cur": [1100.0], "F_all_prev": [1000.0], "P1": [1200.0],
                         "F_grain_cur": [880.0], "F_grain_prev": [900.0], "G1": [1000.0], "S1": [150.0]})
    planted_hat, grain_hat = 1100 * 1200 / 1000, 880 * 1000 / 900
    residual_hat, residual_last = planted_hat - grain_hat, 1200 - 1000
    expected = residual_hat * 150 / residual_last
    assert run.s3_raw(rows).iloc[0] == pytest.approx(expected)


def test_s3_raw_clips_and_needs_grain_history():
    rows = pd.DataFrame({"F_all_cur": [2000.0, 1000.0], "F_all_prev": [1000.0, 1000.0], "P1": [1200.0, 1200.0],
                         "F_grain_cur": [900.0, 900.0], "F_grain_prev": [900.0, 900.0], "G1": [1000.0, np.nan],
                         "S1": [150.0, 150.0]})
    out = run.s3_raw(rows)
    assert out.iloc[0] == pytest.approx(300.0)      # ratio far above 2 is clipped to 2
    assert np.isnan(out.iloc[1])                    # no NASS grain history: no residual


def test_shrink_weight_finds_both_ends():
    actual = np.array([100.0, 200.0, 300.0])
    perfect_raw = pd.DataFrame({"s1": [150.0, 150.0, 150.0], "raw": actual, "actual": actual})
    useless_raw = pd.DataFrame({"s1": actual, "raw": [10.0, 900.0, 5.0], "actual": actual})
    assert run.fit_shrink_weight(perfect_raw) == 1.0
    assert run.fit_shrink_weight(useless_raw) == 0.0


def test_clipped_log_ratio_floor_and_clip():
    out = run._clipped_log_ratio(pd.Series([1000.0, 10_000.0, 100.0]), pd.Series([400.0, 1000.0, 1000.0]))
    assert np.isnan(out.iloc[0])                    # denominator under 500 acres
    assert out.iloc[1] == pytest.approx(np.log(2)) and out.iloc[2] == pytest.approx(-np.log(2))


# --- scoring and selection ---------------------------------------------------------------------------------------

def test_score_table_wape_and_us_error():
    preds = pd.DataFrame({"candidate": "x", "year": 2020, "pred": [110.0, 80.0], "actual": [100.0, 100.0]})
    row = run.score_table(preds).iloc[0]
    assert row["state_wape_pct"] == pytest.approx(15.0)
    assert row["us_error_pct"] == pytest.approx(-5.0)


def by_year_for(diffs: dict[str, list[float]]) -> pd.DataFrame:
    rows = []
    years = range(2012, 2025)
    for year in years:
        rows.append({"candidate": run.SIMPLEST, "year": year, "state_wape_pct": 14.0, "asof_key": "nov"})
    for name in run.SELECTION_ORDER:
        values = diffs.get(name, [1.0] * len(years))
        for year, d in zip(years, values):
            rows.append({"candidate": name, "year": year, "state_wape_pct": 14.0 + d, "asof_key": "nov"})
    return pd.DataFrame(rows)


def test_selection_keeps_s1_when_nothing_beats_it_by_two_se():
    noisy = [-2.0, 1.5] * 6 + [-1.0]                # better on average, but not by 2 SE
    result = run.select(by_year_for({"s3_fsa_residual": noisy}))
    assert result["selected"] == run.SIMPLEST and result["qualifying"] == []


def test_selection_picks_the_lowest_mean_among_qualifiers():
    steady = [-0.5 + 0.01 * i for i in range(13)]
    steadier = [-0.8 + 0.01 * i for i in range(13)]
    result = run.select(by_year_for({"s2_fsa_ratio_highcov": steady, "s4_reversion_plus_switch": steadier}))
    assert set(result["qualifying"]) == {"s2_fsa_ratio_highcov", "s4_reversion_plus_switch"}
    assert result["selected"] == "s4_reversion_plus_switch"


def test_bootstrap_ci_is_reproducible_and_brackets_the_mean():
    diffs = np.array([-1.0, -0.5, 0.2, -0.8, -0.3])
    lo, hi = run.bootstrap_ci(diffs)
    assert (lo, hi) == run.bootstrap_ci(diffs)
    assert lo < diffs.mean() < hi


# --- real data (skipped if the files are absent) -----------------------------------------------------------------

needs_data = pytest.mark.skipif(not (run.DATA / "models" / "state_model_backtest.csv").exists(),
                                reason="repository data not present")


@needs_data
def test_incumbent_and_persistence_reproduce_exactly():
    finals, states = run.load_nass_finals()
    _, report = run.reproduce_incumbent(finals, states)
    assert report["s1_incumbent_H13"]["exact_to_2dp"]
    assert report["s0_persistence_H13"]["exact_to_2dp"]
    assert report["s1_incumbent_H13"]["mean_state_wape_stored"] == pytest.approx(13.1225)


@needs_data
def test_nass_finals_stop_at_2025_and_cover_48_states():
    finals, states = run.load_nass_finals()
    assert finals["year"].max() == run.MAX_FINAL_YEAR and len(states) == 48
