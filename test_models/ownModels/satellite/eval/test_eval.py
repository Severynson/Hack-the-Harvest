"""Tests for the satellite evaluation (agent key: sat_eval)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sat_eval", HERE / "eval.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


def test_preregistration_hash_unchanged():
    assert ev.check_prereg() == ev.PREREG_FILE.read_text(encoding="utf-8").split()[0]
    text = ev.prereg_text()
    assert text.startswith(ev.PREREG_START) and text.endswith(ev.PREREG_END)


def test_clip_ratio_bounds():
    assert ev.clip_ratio(3.0, 1.0) == 2.0
    assert ev.clip_ratio(0.1, 1.0) == 0.5
    assert np.isclose(ev.clip_ratio(0.33, 0.30), 1.1)


def test_ratios_pair_consecutive_years_only():
    shares = pd.DataFrame({"state": ["X"] * 3, "year": [2019, 2020, 2022],
                           "sat_share": [0.2, 0.3, 0.4], "sat_share_calls": [0.1, 0.1, 0.1]})
    r = ev.ratios(shares, [2020, 2021, 2022])
    assert r["year"].tolist() == [2020]  # 2022 has no 2021 share
    assert np.isclose(r["sat_share"].iloc[0], 1.5)


def _toy_inputs():
    bases = pd.DataFrame({"state": ["X"] * 3, "year": [2020] * 3, "asof": ["nov"] * 3,
                          "candidate": ["R", "A", "B"], "pred": [100.0, 110.0, 120.0]})
    last = pd.Series({("X", 2020): 90.0})
    r = pd.DataFrame({"state": ["X"], "year": [2020], "sat_share": [1.44], "sat_share_calls": [0.81]})
    snr = pd.Series({"X": 1.0})
    return bases, last, r, snr


def test_candidate_formulas():
    bases, last, r, snr = _toy_inputs()
    p = ev.build_predictions(bases, last, r, snr, [2020], "nov").set_index("candidate")["pred"]
    assert np.isclose(p["p0"], 90.0)
    assert np.isclose(p["p1"], 90.0 * 1.44)
    assert np.isclose(p["p2"], 90.0 * 1.2)
    assert np.isclose(p["R2"], 100.0 * 1.2)
    assert np.isclose(p["A2"], 110.0 * 1.2)
    assert np.isclose(p["B2"], 120.0 * 1.2)
    assert np.isclose(p["p1c"], 90.0 * 0.81)
    assert np.isclose(p["R2c"], 100.0 * 0.9)
    # SNR 1 -> exponent 0.5 x 1/2 = 0.25
    assert np.isclose(p["A2w"], 110.0 * 1.44 ** 0.25)


def test_wape_and_total_error_by_hand():
    pred, actual = np.array([110.0, 80.0]), np.array([100.0, 100.0])
    assert np.isclose(ev.wape(pred, actual), 15.0)
    assert np.isclose(ev.total_error(pred, actual), -5.0)


def _toy_backtest(shift):
    rows = []
    rng = np.random.default_rng(0)
    for s in range(15):
        for y in ev.SEL_YEARS:
            actual = 1000.0 + 100 * s
            noise = rng.normal(0, 50)
            rows.append({"state": f"S{s:02d}", "year": y, "asof": "nov", "candidate": "base",
                         "pred": actual + noise, "actual": actual})
            rows.append({"state": f"S{s:02d}", "year": y, "asof": "nov", "candidate": "cand",
                         "pred": actual + noise * shift, "actual": actual})
    return pd.DataFrame(rows)


def test_paired_identical_is_zero():
    row = ev.paired(_toy_backtest(1.0), "cand", "base", "nov", n_boot=500)
    assert row["d_wape"] == 0 and row["d_wape_ci90_years_lo"] == 0 and row["d_wape_ci90_states_hi"] == 0
    assert row["years_tied"] == 5 and row["states_tied"] == 15
    assert ev.adoption(row) == (False, "not shown")


def test_paired_uniformly_better_is_adopted():
    row = ev.paired(_toy_backtest(0.5), "cand", "base", "nov", n_boot=500)
    assert row["d_wape"] < 0 and row["d_wape_ci90_years_hi"] < 0 and row["d_wape_ci90_states_hi"] < 0
    assert row["years_better"] == 5 and row["states_better"] == 15
    assert ev.adoption(row) == (True, "adopted")


def test_widened_interval():
    q = (-0.2, 0.0, 0.25)
    lo, hi = ev.widened(100.0, q, 0.0)
    assert np.isclose(lo, 100 * np.exp(-0.2)) and np.isclose(hi, 100 * np.exp(0.25))
    lo2, hi2 = ev.widened(100.0, q, 0.15)
    assert np.isclose(np.log(lo2 / 100), -np.sqrt(0.04 + 0.0225))
    assert np.isclose(np.log(hi2 / 100), np.sqrt(0.0625 + 0.0225))


def test_choose_final_rule():
    assert ev.choose_final({}) == "A"
    assert ev.choose_final({"p1": 10.0, "R2": 9.0}) == "R2"
    assert ev.choose_final({"p2": 9.0, "B2": 9.0}) == "B2"  # tie order A2, B2, R2, p2, p1


def test_tier_b_rows_deduplicated():
    b = ev._tier_b_backtest()
    assert not b.duplicated(["state", "year", "asof_key", "candidate"]).any()


def test_bases_complete_for_sample_states():
    states = ev.load_states()["state"].tolist()
    bases = ev.load_bases(states)
    assert set(bases["candidate"]) == {"R", "A", "B"}
    assert set(bases["year"]) == set(ev.SEL_YEARS) | {ev.INFO_YEAR, ev.FORECAST_YEAR}


def test_2026_shares_cut_at_forecast_date():
    path = ev.OUT / "sat_share_2026_asof_nov.csv"
    if not path.exists():
        pytest.skip("2026 shares not computed yet")
    table = pd.read_csv(path)
    assert len(table) == 15
    assert (pd.to_datetime(table["last_observation_date"]) <= pd.Timestamp("2026-11-15")).all()
    assert (table["year"] == 2026).all()


def test_backtest_shares_never_after_asof():
    for asof in ev.ASOFS:
        ev.load_shares(asof)  # raises if a share used a look after its as-of date
