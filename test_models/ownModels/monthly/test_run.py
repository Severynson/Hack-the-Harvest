"""Tests for the month-by-month harness (fast: no full backtest).

Run from the repository root:
    .venv/Scripts/python.exe -m pytest -q test_models/ownModels/monthly/test_run.py
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("monthly_harness", HERE / "run.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

from kernelag import fsa as kfsa  # noqa: E402
import kernelag.context as kctx  # noqa: E402


@pytest.fixture(scope="module")
def mods():
    loaded = harness.load_modules()
    harness.patch_asof(loaded)
    return loaded


def test_patch_widens_every_asof_mapping(mods):
    for key, month in harness.MONTHS.items():
        assert kctx.ASOF_MONTH[key] == month
    for mod in mods.values():
        assert dict(mod.ASOF) == harness.ASOF
    assert dict(mods["silage_b"].ASOF_MONTH) == harness.MONTHS
    harness.patch_asof(mods)            # a second call is harmless
    assert dict(mods["grain_a"].ASOF) == harness.ASOF


def test_patch_refuses_a_changed_month(mods):
    mods["grain_a"].ASOF["sep"] = (9, 30)
    try:
        with pytest.raises(ValueError):
            harness.patch_asof(mods)
    finally:
        mods["grain_a"].ASOF["sep"] = (9, 15)


def test_june_2013_grain_forecasts_parse_and_add_up():
    path = harness.REPORTS_DIR / "reports" / "Acre-06-28-2013.txt"
    states, us = harness.parse_june_grain(path, 2013)
    assert len(states) == 41
    assert us == 89_135_000
    assert states.sum() == us
    assert states["IOWA"] == 13_500_000
    assert "CONNECTICUT" not in states.index          # (NA): no grain estimate


def test_june_parse_equals_stored_values_in_other_years(mods):
    table = mods["grain_a"].nass_inseason_table()
    for year, name in [(2012, "Acre-06-29-2012.txt"), (2014, "Acre-06-30-2014.txt"), (2019, "acrg0619.txt")]:
        parsed, _ = harness.parse_june_grain(harness.REPORTS_DIR / "reports" / name, year)
        stored = table[(table["year"] == year) & (table["series"] == "grain") & (table["period"] == "jun")]
        stored = stored.set_index("state")["acres"]
        assert set(parsed.index) == set(stored.index)
        assert np.allclose(parsed.reindex(stored.index), stored)


def test_no_current_year_fsa_file_on_15_july():
    files = pd.read_csv(harness.REPO / "data" / "fsa" / "fsa_files.csv")
    for year in harness.YEARS:
        assert kfsa.latest_file(files, date(year, 7, 15), year) is None


def test_fsa_label_refuses_a_file_published_after_the_date():
    files = pd.DataFrame({"zip_name": ["x.zip"], "vintage": ["aug"], "data_as_of": ["2020-08-01"],
                          "assumed_published": ["2020-08-16"]})
    assert harness.fsa_label(files, None, date(2020, 8, 15)) is None
    with pytest.raises(RuntimeError):
        harness.fsa_label(files, "x.zip", date(2020, 8, 15))
    assert "published 2020-08-16" in harness.fsa_label(files, "x.zip", date(2020, 8, 16))


def test_g3_in_july_is_its_own_persistence_fallback_and_nass_december_is_november(mods):
    g = mods["grain_a"]
    finals = g.load_finals()
    files, state = g.load_fsa()
    stress = g.stress_features(g.load_stress_sources(), "jul")
    table, used, _ = g.predict_all(finals, files, state, stress, g.nass_inseason_table(), [2017], "jul")
    g3 = table[table["candidate"] == "g3_fsa_ratio_multi"].set_index("state")["pred"]
    g0 = table[table["candidate"] == "g0_persistence"].set_index("state")["pred"]
    assert np.allclose(g3, g0.reindex(g3.index))
    assert next(u for u in used if u["candidate"] == "g3_fsa_ratio_multi")["current"] is None
    inseason = g.nass_inseason_table()
    assert np.allclose(g.nass_benchmark(inseason, finals, 2017, "dec"), g.nass_benchmark(inseason, finals, 2017, "nov"))
    assert harness.nass_report_used(inseason, 2017, "jul").startswith("jun")


def test_score_and_averages():
    preds = pd.DataFrame({"model": "g3_fsa_ratio_multi", "asof": "nov", "year": 2020, "state": ["A", "B"],
                          "pred": [110.0, 90.0], "actual": [100.0, 100.0]})
    info = pd.DataFrame([{"model": "g3_fsa_ratio_multi", "asof": "nov", "year": 2020, "fallback": False,
                          "fsa_file": "nov", "detail": ""}])
    row = harness.score(preds, info).iloc[0]
    assert row["state_wape_pct"] == pytest.approx(10.0)
    assert row["us_error_pct"] == pytest.approx(0.0)

    rows = []
    for key, value in zip(harness.MONTHS, [6.0, 5.0, 4.0, 3.0, 2.0, 1.0]):
        for year in range(2017, 2025):
            rows.append({"model": "g3_fsa_ratio_multi", "asof": key, "year": year, "state_wape_pct": value,
                         "us_error_pct": -value, "fallback": key == "jul"})
    summary = harness.summarise(pd.DataFrame(rows))
    summary = summary[summary["period"] == "2017-2024"].set_index("asof")
    assert summary.loc["avg_jul_dec", "mean_state_wape_pct"] == pytest.approx(3.5)
    assert summary.loc["avg_aug_dec", "mean_state_wape_pct"] == pytest.approx(3.0)
    assert summary.loc["avg_jul_dec", "fallback_share"] == pytest.approx(1 / 6)
    assert summary.loc["jul", "fallback_share"] == 1.0
    assert summary.loc["nov", "mean_signed_us_error_pct"] == pytest.approx(-2.0)


def test_paired_ci_brackets_the_mean():
    mean, lo, hi = harness.paired_ci(np.array([0.1, 0.3, -0.2, 0.4, 0.0]), boot=2000)
    assert lo <= mean <= hi
    assert mean == pytest.approx(0.12)
