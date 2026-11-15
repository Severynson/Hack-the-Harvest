"""Tests for the pre-registered state-signal scorer (score_state_signal.py beside this file).

Checks the hand-exported Google Trends parser, the Aug-Oct anomaly, and that the score finds a planted
signal, ignores a shift shared by every state in a year, and gives a large p-value to noise.

Run: ``.venv/Scripts/python.exe -m pytest -q test_models/featureTests/forums/test_score_state_signal.py``
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("score_state_signal", HERE / "score_state_signal.py")
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)


def write_trends_export(path: Path, values: dict[str, str]) -> None:
    """A file shaped like a Google Trends 'Interest over time' CSV export."""
    lines = ["Category: All categories", "", "Month,corn silage: (Wisconsin)"]
    lines += [f"{month},{value}" for month, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def season(year: int, value: str) -> dict[str, str]:
    return {f"{year}-{month:02d}": value for month in (7, 8, 9, 10)}


def test_trends_anomaly_uses_aug_oct_and_masks_low_volume(tmp_path):
    values = {**season(2016, "10"), **season(2017, "10"), **season(2018, "10"), **season(2019, "20")}
    values["2020-08"], values["2020-09"], values["2020-10"] = "40", "<1", "40"   # one too-few-searches month
    path = tmp_path / "Wisconsin.csv"
    write_trends_export(path, values)
    anomaly = scorer.trends_anomaly(scorer.read_trends_csv(path))
    assert math.isclose(anomaly[2019], math.log(2.0))                 # 20 against a 10 reference
    assert math.isnan(anomaly[2020])                                  # incomplete season stays missing
    assert math.isnan(anomaly[2017])                                  # only one earlier year


def synthetic_target(seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    states = [f"STATE{i}" for i in range(20)]
    rows = [(state, year, rng.normal(0, 0.15)) for state in states for year in range(2017, 2025)]
    return pd.DataFrame(rows, columns=["state", "year", "target"]).assign(silage=1.0)


def test_score_finds_planted_signal_and_ignores_year_shifts():
    target = synthetic_target()
    rng = np.random.default_rng(2)
    year_shift = target["year"].map({year: 5.0 * (year - 2020) for year in range(2017, 2025)})
    signal = target.assign(signal=target["target"] + rng.normal(0, 0.05, len(target)) + year_shift)
    result = scorer.score(signal[["state", "year", "signal"]], target, n_perm=500)
    assert result["n_state_years"] == 160
    assert result["rho"] > 0.8 and result["p_value"] < 0.01 and result["pass"]


def test_score_gives_noise_a_large_p_value():
    target = synthetic_target()
    noise = target.assign(signal=np.random.default_rng(3).normal(size=len(target)))
    result = scorer.score(noise[["state", "year", "signal"]], target, n_perm=500)
    assert result["p_value"] > 0.05 and not result["pass"]


@pytest.mark.skipif(not scorer.PANEL.exists(), reason="data/panel/state_year.csv not present")
def test_builtin_drought_baseline_runs_on_the_repo_panel():
    target = scorer.load_target()
    assert set(target["year"]) <= set(scorer.YEARS)                   # never the frozen 2025 year
    assert target["state"].nunique() == scorer.TOP_N
    result = scorer.score(scorer.builtin_signal("d_drought"), target, n_perm=200)
    assert result["n_state_years"] > 100 and result["rho"] is not None
