"""Tests for the Tier B silage models: tier guards, look-ahead guards, arithmetic, selection, outputs.

Run from the repo root: .venv/Scripts/python.exe -m pytest -q test_models/ownModels/tierB/silage/test_run.py
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("tierb_silage_run", HERE / "run.py")
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)


def test_check_tiers_passes_and_refuses_forbidden_inputs():
    run.check_tiers()
    bad = {"x": {"tier": "B", "inputs": ["nass_final_history", "nass_grain_forecast"], "eligible": True}}
    with pytest.raises(ValueError):
        run.check_tiers(bad)
    ineligible = {"x": {"tier": "forbidden", "inputs": ["nass_final_target_year"], "eligible": True}}
    with pytest.raises(ValueError):
        run.check_tiers(ineligible)


def test_no_eligible_candidate_reads_a_forbidden_input():
    for name, spec in run.CANDIDATES.items():
        tiers = {run.INPUTS[key][1] for key in spec["inputs"]}
        if spec["eligible"]:
            assert "forbidden" not in tiers, name


def test_check_columns_refuses_grain_forecast_columns():
    run.check_columns(["S1", "d_planted", "d_fsa_nongrain"])
    for column in ["grain_asof", "d_not_grain", "nass_latest"]:
        with pytest.raises(ValueError):
            run.check_columns(["S1", column])


def test_history_refuses_target_year_and_later():
    finals = pd.DataFrame({"state": ["A", "A", "A"], "year": [2019, 2020, 2021], "silage": [1.0, 2.0, 3.0],
                           "grain": [1.0, 1.0, 1.0], "planted": [2.0, 3.0, 4.0], "yield": [1.0, 1.0, 1.0]})
    hist = run.History(finals, ["A"], 2021)
    assert hist.get("silage", 2020).iloc[0] == 2.0
    with pytest.raises(run.LookAheadError):
        hist.get("silage", 2021)
    assert 2021 not in hist.long("silage")["year"].tolist()


def test_residual_raw_arithmetic():
    rows = pd.DataFrame({"S1": [100.0], "P1": [1000.0], "G1": [800.0], "F_pf_cur": [900.0], "F_grain_cur": [720.0],
                         "F_pf_prev": [950.0], "F_grain_prev": [760.0]})
    planted = pd.Series([1100.0])
    out = run.residual_raw(rows, planted)
    # share_cur = 0.8, share_prev = 0.8, correction = 0.8 / 0.8 = 1 -> grain_hat = 1100 * 0.8 = 880
    assert out["grain_hat"].iloc[0] == pytest.approx(880.0)
    assert out["residual_hat"].iloc[0] == pytest.approx(220.0)
    # residual ratio 220 / 200 = 1.1 -> raw = 110
    assert out["raw"].iloc[0] == pytest.approx(110.0)
    rows.loc[0, "G1"] = np.nan
    assert out.pipe(lambda _: run.residual_raw(rows, planted))["raw"].isna().all()


def test_residual_raw_clips_ratio():
    rows = pd.DataFrame({"S1": [100.0], "P1": [1000.0], "G1": [800.0], "F_pf_cur": [1000.0], "F_grain_cur": [400.0],
                         "F_pf_prev": [1000.0], "F_grain_prev": [800.0]})
    assert run.residual_raw(rows, pd.Series([1000.0]))["raw"].iloc[0] == pytest.approx(200.0)   # clip at 2


def test_hybrid_planted_uses_fsa_only_before_june():
    rows = pd.DataFrame({"P_nass": [1000.0, 1000.0], "P_vintage": ["mar", "jun"], "F_pf_cur": [900.0, 900.0],
                         "F_pf_prev": [1000.0, 1000.0], "P1": [1200.0, 1200.0]})
    hyb = run.hybrid_planted(rows)
    assert hyb.iloc[0] == pytest.approx(900.0 * 1200.0 / 1000.0)
    assert hyb.iloc[1] == 1000.0


def test_latest_vintage_respects_asof_month():
    table = pd.DataFrame({"state": ["A"] * 4, "year": [2020] * 4, "vintage": ["mar", "jun", "sep", "oct"],
                          "value": [1.0, 2.0, 3.0, 4.0]})
    value, vintage = run.latest_vintage(table, 2020, "sep", ["A", "B"])
    assert value["A"] == 3.0 and vintage["A"] == "sep" and np.isnan(value["B"])
    value, vintage = run.latest_vintage(table, 2020, "nov", ["A"])
    assert vintage["A"] == "oct"


def test_fit_shrink_weight_finds_exact_blend():
    c0 = np.array([100.0, 200.0, 300.0])
    raw = np.array([200.0, 100.0, 600.0])
    actual = np.exp(0.75 * np.log(c0) + 0.25 * np.log(raw))
    train = pd.DataFrame({"c0": c0, "raw": raw, "actual": actual})
    assert run.fit_shrink_weight(train, "raw") == 0.25


def test_select_two_standard_error_rule():
    years = list(range(2012, 2025))
    rows = []
    rng = np.random.default_rng(0)
    for y in years:
        base = 14 + rng.normal()
        rows.append({"year": y, "candidate": run.SIMPLEST, "state_wape_pct": base})
        for name in run.SELECTION_ORDER:
            delta = -0.5 if name == "c5_residual_shrunk" else 0.3 * rng.normal()
            rows.append({"year": y, "candidate": name, "state_wape_pct": base + delta})
    by_year = pd.DataFrame(rows).assign(asof_key="nov")
    result = run.select(by_year)
    assert result["selected"] == "c5_residual_shrunk"
    assert result["candidates"]["c5_residual_shrunk"]["qualifies"]


def test_bootstrap_ci_brackets_mean():
    diffs = np.array([-1.0, -0.5, -0.2, 0.1, -0.4])
    lo, hi = run.bootstrap_ci(diffs, n=2000)
    assert lo <= diffs.mean() <= hi


def test_fsa_inputs_never_read_unpublished_or_own_final_files():
    files, acres = run.load_fsa()
    states = ["IOWA", "WISCONSIN", "NEW YORK"]
    for year in range(2012, 2027):
        for key, (month, day) in run.ASOF.items():
            asof = date(year, month, day)
            _, _, meta = run.fsa_inputs(files, acres, asof, year, states)
            if meta["current_zip_name"] is not None:
                assert pd.Timestamp(meta["current_assumed_published"]) <= pd.Timestamp(asof)
                assert not str(meta["current_vintage"]).startswith("final")
                assert pd.Timestamp(meta["current_data_as_of"]).year == year
            if meta["prior_final_zip_name"] is not None:
                assert pd.Timestamp(meta["prior_final_assumed_published"]) <= pd.Timestamp(asof)


OUT = HERE / "out"


@pytest.mark.skipif(not (OUT / "reproduction.json").exists(), reason="run.py has not been run")
def test_benchmarks_reproduced_exactly():
    report = json.loads((OUT / "reproduction.json").read_text(encoding="utf-8"))
    for series in ("silage", "grain"):
        for name, values in report[series].items():
            assert values["exact_to_2dp"], (series, name)
    assert report["silage"]["c0_incumbent_H13"]["mean_state_wape_2017_2024"] == pytest.approx(13.12, abs=0.005)


@pytest.mark.skipif(not (OUT / "backtest_by_state_year.csv").exists(), reason="run.py has not been run")
def test_outputs_have_required_columns_and_no_2025():
    backtest = pd.read_csv(OUT / "backtest_by_state_year.csv")
    assert {"state", "year", "asof", "candidate", "pred", "actual"} <= set(backtest.columns)
    assert backtest["year"].between(2012, 2024).all()
    assert set(backtest["asof_key"]) == {"sep", "oct", "nov"}
    summary = pd.read_csv(OUT / "summary.csv")
    assert {"mean_state_wape_pct", "mean_abs_us_error_pct", "mean_signed_us_error_pct"} <= set(summary.columns)
    forecast = pd.read_csv(OUT / "forecast_2026.csv")
    assert forecast["state"].iloc[0].startswith("US")
    us = forecast.iloc[0]
    assert us["silage_lo80"] <= us["silage"] <= us["silage_hi80"]


@pytest.mark.skipif(not (OUT / "preregistration.sha256").exists(), reason="pre-registration not hashed")
def test_preregistration_unchanged():
    assert run.preregistration_status()["unchanged"]
