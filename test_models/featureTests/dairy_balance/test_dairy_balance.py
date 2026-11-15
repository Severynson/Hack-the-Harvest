"""Unit tests for the dairy balance test (run.py) and its contract stub (build.py). No data files are read.

Run from the repository root:
    .venv/Scripts/python.exe -m pytest -q test_models/featureTests/dairy_balance/test_dairy_balance.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"dairy_balance_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = load("run")
build = load("build")


def test_calibrated_balance_reproduces_last_year():
    rng = np.random.default_rng(1)
    cows, corn = rng.uniform(0, 5000, 30), rng.uniform(1000, 20000, 30)
    target = 0.3 * corn.sum()
    k, status = run.calibrate_k(cows, corn, target)
    assert status == "ok"
    assert run.balance_parts(k, cows, corn).sum() == pytest.approx(target, rel=1e-9)


def test_without_capped_counties_balance_is_the_cow_ratio():
    # Few cows per corn acre: no county reaches the 0.98 cap or sits on the 0.01 floor.
    cows, corn = np.array([100.0, 200.0, 300.0]), np.array([10000.0, 8000.0, 12000.0])
    target = run.balance_parts(5.0, cows, corn).sum()
    k, _ = run.calibrate_k(cows, corn, target)
    r, p = 1.07, 0.9                       # herd up 7%, corn down 10%
    forecast = run.balance_parts(k * r, cows, corn * p).sum()
    assert forecast == pytest.approx(target * r, rel=1e-9)


def test_corn_limited_county_follows_corn_not_cows():
    # One county has far more cows than corn: its silage is capped at 0.98 of its corn.
    cows, corn = np.array([50000.0, 100.0]), np.array([1000.0, 10000.0])
    k, _ = run.calibrate_k(cows, corn, 980.0 + 0.05 * 10000.0)
    capped = run.balance_parts(k * 1.2, cows, corn * 0.5)
    assert capped[0] == pytest.approx(0.98 * 500.0)       # halved corn halves it, more cows do not raise it


def test_calibration_reports_bounds():
    cows, corn = np.array([10.0, 0.0]), np.array([1000.0, 1000.0])
    assert run.calibrate_k(cows, corn, 1.0)[1] == "floor"      # below the 0.01 floor on every county
    assert run.calibrate_k(cows, corn, 1e9)[1] == "capped"     # above what the 0.98 cap allows


def test_pooled_out_of_sample_skips_missing_years():
    base = {"n_counties": 10, "silage_sum": 100.0, "sst": 1.0, "sse_rule_in": 0.5, "sse_naive_in": 1.0,
            "sse_placebo_in": 2.0, "abs_rule_in": 1.0, "abs_naive_in": 2.0, "sse_rule_out": 0.4,
            "sse_naive_out": 0.8, "abs_rule_out": 1.0, "abs_naive_out": 2.0, "acre_err_rule_out": 10.0,
            "acre_err_naive_out": 20.0}
    missing = {**base, "sse_rule_out": np.nan, "sse_naive_out": np.nan, "abs_rule_out": np.nan,
               "abs_naive_out": np.nan, "acre_err_rule_out": np.nan, "acre_err_naive_out": np.nan}
    pooled = run.summarise_errors(pd.DataFrame([base, missing]))
    assert pooled["n_counties"] == 20 and pooled["n_counties_out"] == 10
    assert pooled["r2_rule_out"] == pytest.approx(0.6)          # 1 - 0.4 / 1.0, the missing year not read as 0
    assert pooled["skill_vs_naive_out"] == pytest.approx(0.5)
    assert pooled["skill_vs_naive_in"] == pytest.approx(0.5)


def test_carried_values_expire():
    long = pd.DataFrame({"state": ["WI"], "county_fips": ["55001"], "year": [2015], "planted": [5000.0]})
    out = run.carried(long, "planted").set_index("year")
    assert list(out.index) == [2015, 2016, 2017, 2018]          # CARRY_YEARS = 3
    assert (out["source_year"] == 2015).all()


def test_contract_stub(tmp_path):
    meta = build.write_contract(tmp_path, build.DATASETS)
    assert meta["features"] == [] and meta["datasets_built"] == []
    assert set(meta["uncomputed"]) == set(build.DATASETS)
    assert (tmp_path / "features.csv").read_text(encoding="utf-8").strip() == "dataset,field_id,year"
    assert json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))["group"] == "dairy_balance"
