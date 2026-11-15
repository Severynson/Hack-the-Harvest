"""Unit tests for the combination formulas and guards (no data beyond the README hash files is read).

Run from the repo root:
    .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider test_models/variations/silage_combos
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("silage_combos_run", HERE / "run.py")
run = importlib.util.module_from_spec(SPEC)
sys.modules["silage_combos_run"] = run
SPEC.loader.exec_module(run)


def frame(chop: float = 0.0) -> pd.DataFrame:
    states = ["S1", "S2", "S3"]
    return pd.DataFrame({"A": [100.0, 200.0, 300.0], "B": [110.0, 190.0, 310.0], "SC": [120.0, 180.0, 330.0],
                         "SC_B": [119.0, 181.0, 329.0], "SC_L": [115.0, 185.0, 320.0],
                         "SC_A": [125.0, 175.0, 335.0], "SC_chop": [chop, 0.0, 0.0],
                         "SC_A_chop": [chop / 2, 0.0, 0.0]}, index=states)


def test_totals_by_construction():
    w = frame(10.0)
    out = run.combine(w, 0.5, 0.5)
    assert out["v2_topdown"].sum() == pytest.approx(w["SC"].sum())
    assert out["v3_reverse"].sum() == pytest.approx(w["A"].sum())
    assert out["v6_topdown_geoUS"].sum() == pytest.approx(np.sqrt(w["SC"].sum() * w["A"].sum()))
    assert out["v9_topdown_SCB"].sum() == pytest.approx(w["SC_B"].sum())
    assert out["v10_topdown_SCL"].sum() == pytest.approx(w["SC_L"].sum())
    assert out["v11_topdown_SCA"].sum() == pytest.approx(w["SC_A"].sum())
    assert out["w3_geo_SCA_rescaled"].sum() == pytest.approx(w["SC_A"].sum())
    assert out["w4_geo_rescaled"].sum() == pytest.approx(w["SC"].sum())
    # shares are A-S3's for the top-down candidates
    assert (out["v2_topdown"] / out["v2_topdown"].sum()).to_numpy() == pytest.approx(
        (w["A"] / w["A"].sum()).to_numpy())


def test_blends():
    w = frame()
    out = run.combine(w, 0.5, 0.25)
    assert out["v1_geo"].to_numpy() == pytest.approx(np.sqrt(w["A"] * w["SC"]).to_numpy())
    assert out["v8_geo_fitted"].to_numpy() == pytest.approx(out["v1_geo"].to_numpy())
    assert out["v7_mean2"].to_numpy() == pytest.approx(((w["A"] + w["SC"]) / 2).to_numpy())
    assert out["v4_mean3"].to_numpy() == pytest.approx(((w["A"] + w["B"] + w["SC"]) / 3).to_numpy())
    assert out["w2_geo_fitted_SCA"].to_numpy() == pytest.approx((w["A"] ** 0.75 * w["SC_A"] ** 0.25).to_numpy())
    assert out["w5_SC_A"].to_numpy() == pytest.approx(w["SC_A"].to_numpy())


def test_chopping_factor():
    w = frame(30.0)
    out = run.combine(w, 0.5)
    factor = out["v5_chopmult"] / w["A"]
    assert factor["S1"] == pytest.approx(120.0 / 90.0)
    assert factor[["S2", "S3"]].to_numpy() == pytest.approx([1.0, 1.0])
    assert out["v5b_chopadd"]["S1"] == pytest.approx(130.0)
    assert (out["v13_chopmult_SCA"] >= w["A"] - 1e-9).all()


def test_fit_geo_weight_extremes():
    w = frame()
    assert run.fit_geo_weight(w.assign(actual=w["SC"])) == 1.0
    assert run.fit_geo_weight(w.assign(actual=w["A"])) == 0.0
    assert run.fit_geo_weight(w.assign(actual=w["A"]), "SC_A") == 0.0


def test_v8_weight_null_and_no_2025():
    rows = []
    for year in [2012, 2013, 2025]:
        rows.append(frame().reset_index(names="state").assign(asof="nov", year=year, actual=lambda d: d["SC"]))
    wide = pd.concat(rows, ignore_index=True)
    weight, n = run.v8_weight(wide, "nov", 2026)
    assert (weight, n) == (run.NULL_W, 2)          # 2025 is never a training year


def test_tiers():
    assert run.tier_of("v1_geo") == "C"
    assert run.tier_of("v4_mean3") == "C"
    assert run.tier_of("v9_topdown_SCB") == "B"
    assert run.tier_of("v12_geo_SCA") == "A"
    assert run.tier_of("w3_geo_SCA_rescaled") == "A"
    assert run.tier_of("w4_geo_rescaled") == "C"


def test_drought_exposure_threshold():
    like = pd.DataFrame(0.0, index=[2020, 2021], columns=["IOWA"])
    history = {"grain": pd.DataFrame({"IOWA": [1000.0, 2000.0]}, index=[2020, 2021])}
    usdm = pd.DataFrame({"MapDate": ["20210706", "20210803"], "StateAbbreviation": ["IA", "IA"], "D2": [30.0, 50.0]})
    exposure = run.drought_exposure(history, usdm, "nov", like, 0.10)
    assert exposure.loc[2021, "IOWA"] == pytest.approx((0.40 - 0.10) * 1000.0)   # mean D2+ 0.40, G(t-1) = 1000
    assert exposure.loc[2020, "IOWA"] == 0.0
    assert run.drought_exposure(history, usdm, "nov", like, 0.50).loc[2021, "IOWA"] == 0.0


def test_preregistration_unchanged():
    assert run.preregistration_status()["unchanged"]
