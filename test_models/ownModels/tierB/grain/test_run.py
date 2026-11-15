"""Tests for the Tier B grain models: tier guard, as-of rules, the report parser, the fitting and selection maths,
and that no b-candidate path touches NASS's grain forecast.

Run from the repository root:  .venv/Scripts/python.exe -m pytest -q test_models/ownModels/tierB/grain/test_run.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fetch_reports as fr  # noqa: E402
import run  # noqa: E402

LAYOUT_A = """Corn Area Planted for All Purposes and Harvested for Grain - States and United States:
2011 and 2012
-----------------------------------------------------------------------------------------
                 :   Area planted for all purposes   :     Area harvested for grain
      State      :-----------------------------------------------------------------------
                 :      2011       :      2012       :      2011       :     2012 1/
-----------------------------------------------------------------------------------------
                 :                              1,000 acres
                 :
Alabama .........:        270               290               250               260
Connecticut 2/ ..:         27                28              (NA)              (NA)
                 :
United States ...:     91,921            96,405            83,981            89,129
-----------------------------------------------------------------------------------------
"""

LAYOUT_B = """Selected Crops Area Planted and Harvested - States and United States: 2012
[Includes updates to planted and harvested area previously published]
------------------------------------------------------------------------------------------------
                :       Corn        :      Sorghum      :     Soybeans      : Dry edible beans
      State     :-------------------------------------------------------------------------------
                : Planted :Harvested: Planted :Harvested: Planted :Harvested: Planted :Harvested
------------------------------------------------------------------------------------------------
                :                                  1,000 acres
                :
Alabama ........:    300       270                           340       330
Arizona ........:     75       >42        25        >7                           10.0      10.0
New York .......:  1,170       650                           310       307       10.0       9.6
                :
United States ..: 96,946    87,721     6,238     5,016    77,203    75,693    1,733.7   1,690.0
------------------------------------------------------------------------------------------------
"""


# --- tier guard and history -------------------------------------------------------------------------------------

def test_tier_guard_rejects_grain_forecast():
    bad = {"bx": {"role": "own", "sources": ["nass_current_year_planted", "nass_current_year_grain_forecast"]}}
    with pytest.raises(ValueError, match="forbidden"):
        run.check_tiers(bad)
    run.check_tiers()          # the real candidate list passes


def test_no_eligible_candidate_declares_the_grain_forecast():
    for name in run.ELIGIBLE + ["b4_daniel_gbt_independent"]:
        assert "nass_current_year_grain_forecast" not in run.CANDIDATES[name]["sources"]


def test_history_refuses_target_year():
    finals = pd.DataFrame({"year": [2019, 2020], "state": ["IOWA", "IOWA"], "grain": [1.0, 2.0], "planted": [3.0, 4.0]})
    yields = pd.DataFrame({"year": [2019, 2020], "state": ["IOWA", "IOWA"], "yield": [180.0, 190.0]})
    hist = run.NassHistory(finals, yields, 2020)
    assert hist.grain(2019).iloc[0] == 1.0
    for getter in (hist.grain, hist.planted, hist.yield_final):
        with pytest.raises(PermissionError):
            getter(2020)


# --- as-of rules ------------------------------------------------------------------------------------------------

def test_planted_asof_uses_release_date():
    table = pd.DataFrame({
        "year": [2012, 2012], "state": ["IOWA", "IOWA"], "period": ["jun", "oct"],
        "release_date": pd.to_datetime(["2012-06-29", "2012-10-11"]), "planted": [14.0e6, 14.2e6],
        "report": ["a", "b"]})
    assert run.planted_asof(table, 2012, date(2012, 9, 15)).loc["IOWA", "planted"] == 14.0e6
    assert run.planted_asof(table, 2012, date(2012, 10, 15)).loc["IOWA", "planted"] == 14.2e6
    assert run.planted_asof(table, 2012, date(2012, 6, 15)).empty


def test_yield_asof_takes_latest_month_not_after_asof():
    fc = pd.DataFrame({"year": [2020] * 3, "state": ["IOWA"] * 3, "month": [8, 9, 11], "value": [1.0, 2.0, 3.0]})
    assert run.yield_asof(fc, 2020, "oct").loc["IOWA"] == 2.0
    assert run.yield_asof(fc, 2020, "nov").loc["IOWA"] == 3.0


def test_fsa_view_rules():
    files, state = run.load_fsa()
    view = run.FsaView(files, state, date(2020, 11, 15), 2020)
    cur = view.current()
    assert cur is not None and int(cur["crop_year"]) == 2020 and not str(cur["vintage"]).startswith("final")
    with pytest.raises(PermissionError):
        view.final(2020)
    later = files[(files["crop_year"] == 2020) & files["vintage"].astype(str).str.startswith("final")].iloc[0]
    with pytest.raises(PermissionError):
        view.acres(later, "grain")         # published in January 2021: not usable on 15 Nov 2020
    share = view.share(cur)
    assert share.between(0, 1).all()


# --- report parser ----------------------------------------------------------------------------------------------

def test_parser_layout_a_reads_planted_current_year_only():
    table, titles = fr.parse_report(LAYOUT_A, 2012)
    got = table.set_index("state")["planted"]
    assert got.to_dict() == {"ALABAMA": 290_000.0, "CONNECTICUT": 28_000.0}
    assert titles


def test_parser_layout_b_reads_corn_planted_not_harvested():
    table, _ = fr.parse_report(LAYOUT_B, 2012)
    got = table.set_index("state")["planted"]
    assert got.to_dict() == {"ALABAMA": 300_000.0, "ARIZONA": 75_000.0, "NEW YORK": 1_170_000.0}


def test_parser_ignores_table_of_contents_and_other_crops():
    toc = ("Selected Crops Area Planted and Harvested - States and United States: 2012.........  6\n"
           "Rice Area Planted and Harvested - States and United States: 2018.................  7\n")
    table, _ = fr.parse_report(toc, 2012)
    assert table.empty


# --- maths ------------------------------------------------------------------------------------------------------

def test_fit_ridge_matches_closed_form():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 2))
    y = x @ np.array([0.3, -0.2]) + rng.normal(scale=0.01, size=200)
    w = np.ones(200)
    coef, scale = run.fit_ridge(x, y, w)
    xs = x / scale
    expected = np.linalg.solve(xs.T @ xs + 1.0 * np.eye(2), xs.T @ y)
    assert np.allclose(coef, expected)
    assert np.allclose(coef / scale, [0.3, -0.2], atol=0.01)


def test_year_errors():
    pred = pd.Series({"A": 110.0, "B": 90.0})
    actual = pd.Series({"A": 100.0, "B": 100.0})
    e = run.year_errors(pred, actual)
    assert e["state_wape_pct"] == pytest.approx(10.0)
    assert e["us_error_pct"] == pytest.approx(0.0)


def _by_year(best_gain: np.ndarray) -> pd.DataFrame:
    rows = []
    for i, year in enumerate(range(2012, 2025)):
        for name in run.ELIGIBLE:
            value = 2.0 - (best_gain[i] if name == "b7_blend_b5_fsa_level" else 0.0) + 0.01 * run.ELIGIBLE.index(name)
            rows.append({"candidate": name, "asof": "nov", "year": year, "state_wape_pct": value})
    return pd.DataFrame(rows)


def test_selection_two_se_rule():
    steady = run.select(_by_year(np.full(13, 0.3)))
    assert steady["selected"] == "b7_blend_b5_fsa_level"
    noisy = run.select(_by_year(np.array([3.0, -2.9] * 6 + [0.3])))
    assert noisy["best"] == "b7_blend_b5_fsa_level" and noisy["selected"] == run.SIMPLEST


def test_interval_bounds_and_error_model():
    rows = pd.DataFrame({"year": np.repeat([2020, 2021, 2022], 3), "state": list("ABC") * 3,
                         "G_last": [1.0, 5.0, 9.0] * 3, "pred": [1.0, 5.0, 9.0] * 3,
                         "actual": [1.1, 5.0, 8.9, 0.9, 5.1, 9.1, 1.0, 4.9, 9.0]})
    model = run.error_model(rows)
    b = run.bounds(pd.Series({"A": 1.0}), pd.Series({"A": 1.0}), model)
    assert b.loc["A", "lo80"] <= 1.0 <= b.loc["A", "hi80"]


# --- end to end on the repository data (skipped where data are absent) -----------------------------------------

needs_data = pytest.mark.skipif(not run.PLANTED_INSEASON.exists() or not run.NASS_TABLE.exists(),
                                reason="repository data not present")


@pytest.fixture(scope="module")
def sources():
    return run.Sources()


@needs_data
def test_b_paths_never_touch_the_grain_forecast(sources, monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("a b-candidate path read NASS's grain forecast")
    monkeypatch.setattr(run, "nass_inseason_rows", forbidden)
    monkeypatch.setattr(run, "nass_benchmark", forbidden)
    table, _ = run.build_tables(sources, [2015, 2016, 2017, 2018], ["nov"])
    preds, _ = run.all_predictions(sources, table, [2018], "nov")
    assert set(run.ELIGIBLE) <= set(preds[2018])
    inp = table[(2018, "nov")]["inputs"]
    assert not any("grain_asof" in c or "not_grain" in c for c in inp.columns)
    assert len(inp) == 41 and inp["Pa"].notna().all()


@needs_data
def test_planted_inputs_match_repo_table(sources):
    check = run.planted_check(sources)
    assert check["rows_compared"] > 900 and check["max_abs_difference_acres"] == 0.0


@needs_data
def test_training_rows_are_earlier_years_only(sources):
    table, _ = run.build_tables(sources, list(range(2012, 2019)), ["nov"])
    _, info = run.all_predictions(sources, table, [2018], "nov")
    spans = {row["train_years"] for row in info if row["train_years"]}
    assert spans == {"2012-2017"}
