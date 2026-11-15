"""Tests for the FSA state-signal test (test_models/featureTests/fsa/run.py).

Offline and fast: a synthetic FSA workbook built with the standard library, toy frames for the candidate rule
and the bootstrap, and a check of the written results against the stored incumbent backtest when they exist.
Run: ``.venv/Scripts/python.exe -m pytest -q test_models/featureTests/fsa/test_run.py``
"""

from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fsa_run", HERE / "run.py")
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _cell(ref: str, value, shared: list[str]) -> str:
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    if value.startswith("!inline:"):
        return f'<c r="{ref}" t="inlineStr"><is><t>{value[8:]}</t></is></c>'
    shared.append(value)
    return f'<c r="{ref}" t="s"><v>{len(shared) - 1}</v></c>'


def _workbook(rows: list[list], columns: str = "ABCDE") -> bytes:
    """A minimal xlsx with a decoy first sheet and the data on sheet "county_data"."""
    shared: list[str] = []
    xml_rows = []
    for number, row in enumerate(rows, start=1):
        cells = "".join(_cell(f"{columns[i]}{number}", v, shared) for i, v in enumerate(row) if v is not None)
        xml_rows.append(f'<row r="{number}">{cells}</row>')
    sheet = f'<worksheet xmlns="{MAIN}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    strings = "".join(f"<si><t>{s}</t></si>" for s in shared)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/workbook.xml", f'<workbook xmlns="{MAIN}" xmlns:r="{REL}"><sheets>'
                      '<sheet name="state_data" sheetId="1" r:id="rId1"/>'
                      '<sheet name="county_data" sheetId="2" r:id="rId2"/></sheets></workbook>')
        book.writestr("xl/_rels/workbook.xml.rels",
                      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                      '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
                      '<Relationship Id="rId2" Target="/xl/worksheets/sheet2.xml"/></Relationships>')
        book.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{MAIN}"><sheetData/></worksheet>')
        book.writestr("xl/worksheets/sheet2.xml", sheet)
        book.writestr("xl/sharedStrings.xml", f'<sst xmlns="{MAIN}">{strings}</sst>')
    return buffer.getvalue()


def test_parse_counts_corn_silage_and_forage_by_state(tmp_path):
    rows = [
        ["!inline:2026 FSA Crop Acreage Data"],
        ["State", "County", "Crop", "Intended Use", "Planted Acres"],
        ["Wisconsin", "Dane", "CORN", "Silage", 100],
        ["Wisconsin", "Dane", "CORN", "Grain", 500],
        ["Wisconsin", None, "Corn ", "Silage", 250],          # gap in the row, stray space in the crop
        ["New York", "Erie", "CORN", "Forage", 40],          # pre-2019 label
        ["Kansas", "Finney", "CORN", "Grain", 900],          # corn but no silage -> 0, not missing
        ["Iowa", "Story", "SOYBEANS", "Silage", 77],         # not corn
        ["VT", "Addison", "CORN", "Silage", 10],             # two-letter code
    ]
    outer = tmp_path / "fsa_2026_nov.zip"
    with zipfile.ZipFile(outer, "w") as archive:               # FSA ships the workbook inside a zip
        archive.writestr("2026_fsa_acres_web_110526.xlsx", _workbook(rows))
    by_state, summary = run.fsa_silage_by_state(outer)
    assert by_state.to_dict() == {"KANSAS": 0.0, "NEW YORK": 40.0, "VERMONT": 10.0, "WISCONSIN": 350.0}
    assert summary["silage_acres_us"] == 400
    assert summary["corn_acres_by_intended_use"] == {"Silage": 360, "Grain": 1400, "Forage": 40}


def test_parse_rejects_a_workbook_without_the_columns(tmp_path):
    path = tmp_path / "fsa_2020_final.xlsx"
    path.write_bytes(_workbook([["State", "Crop", "Acres"], ["Ohio", "CORN", 5]]))
    with pytest.raises(ValueError, match="Planted Acres"):
        run.fsa_silage_by_state(path)


def test_find_files_matches_page_names_landing_ids_and_canonical_names(tmp_path):
    for name in ["DoISjehvQfz9.ZIP", "fsa_2024_nov.xlsx", "2018_fsa_acres_Nov_2018_grufs!.zip",
                 "2016_fsa_acres_jan2017_edr32 (1).zip", "unrelated.zip", "notes.txt"]:
        (tmp_path / name).write_bytes(b"x")
    found = run.find_fsa_files([tmp_path])
    assert set(found) == {(2025, "final"), (2024, "nov"), (2018, "nov"), (2016, "final")}


def test_every_needed_file_is_listed_once():
    keys = [(e["year"], e["vintage"]) for e in run.FSA_FILES]
    assert len(keys) == len(set(keys)) == 20
    assert {(y, "final") for y in range(2016, 2026)} <= set(keys)
    assert {(y, "nov") for y in range(2017, 2025)} <= set(keys)
    assert {(2025, "dec"), (2026, "nov")} <= set(keys)


def _toy() -> pd.DataFrame:
    return pd.DataFrame({          # acres, as in the real tables
        "state": ["NEW YORK", "IDAHO", "KANSAS", "MONTANA", "ARIZONA", "WASHINGTON"],
        "last": [500000.0, 200000.0, 300000.0, 300.0, 50000.0, 100000.0],
        "fsa_prev_final": [450000.0, 200000.0, 20000.0, 400.0, 50000.0, 85000.0],
        "fsa_now": [495000.0, 900000.0, 40000.0, 4000.0, np.nan, 93500.0],
        "residual": [520000.0, np.nan, 280000.0, 100.0, 40000.0, np.nan],
        "base": [510000.0, 210000.0, 310000.0, 290.0, 55000.0, 90000.0],
    })


def test_candidate_rule_gates_clips_caps_and_falls_back():
    frame = _toy()
    got = run.fsa_candidate(frame, "base", "realtime")
    # NEW YORK: coverage 0.9, ratio 1.1 -> 550,000, capped at the residual 520,000.
    # IDAHO: coverage 1.0, ratio 4.5 clipped to 2 -> 400,000, no residual.
    # KANSAS: coverage 0.07 -> base. MONTANA: prior FSA under 500 acres -> ratio 1 -> 300, capped at 100.
    # ARIZONA: this year's FSA value missing -> base, never the cap. WASHINGTON: coverage 0.85 -> 110,000.
    assert got.tolist() == pytest.approx([520000.0, 400000.0, 310000.0, 100.0, 55000.0, 110000.0])
    # The fixed list has no Washington, so it keeps the base there.
    fixed = run.fsa_candidate(frame, "base", "fixed_list")
    assert fixed.tolist() == pytest.approx([520000.0, 400000.0, 310000.0, 100.0, 55000.0, 90000.0])


def test_cap_never_invents_a_prediction():
    got = run.capped(pd.Series([np.nan, 10.0, 10.0, 10.0]), pd.Series([5.0, 5.0, np.nan, -3.0]))
    assert np.isnan(got.iloc[0]) and got.iloc[1:].tolist() == [5.0, 10.0, 10.0]


def _panel(scale: float) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for year in range(2017, 2025):
        for state in range(10):
            actual = 1000.0 + 100 * state
            error = rng.normal(0, 100)
            rows.append({"year": year, "state": f"S{state}", "actual": actual,
                         "base": actual + error, "cand": actual + scale * error})
    return pd.DataFrame(rows)


def test_bootstrap_is_zero_for_identical_predictions():
    out = run.paired_bootstrap(_panel(1.0), "cand", "base", draws=500)
    assert out["delta_mean_state_wape_points"] == 0.0
    assert out["ci90_resampling_years"] == [0.0, 0.0] and out["ci90_resampling_states"] == [0.0, 0.0]


def test_bootstrap_sees_a_clearly_better_candidate():
    out = run.paired_bootstrap(_panel(0.5), "cand", "base", draws=500)
    assert out["delta_mean_state_wape_points"] < 0
    assert out["ci90_resampling_years"][1] < 0 and out["ci90_resampling_states"][1] < 0
    assert out["years_candidate_better"] == 8 and out["two_se_rule"]["passes"]


def test_written_results_reproduce_the_stored_incumbent_backtest():
    results_file = HERE / "out" / "results.json"
    stored_file = run.REPO / "data" / "models" / "state_model_backtest.csv"
    if not results_file.is_file() or not stored_file.is_file():
        pytest.skip("run.py has not been run here")
    results = json.loads(results_file.read_text(encoding="utf-8"))
    assert results["status"] in {"done", "partial", "blocked"}
    stored = pd.read_csv(stored_file)
    stored = stored[(stored["scope"] == "all_states") & (stored["series"] == "silage")]
    for ours, theirs in [("incumbent_reversion_only", "reversion_only"), ("persistence", "same_as_last_year")]:
        expected = stored[stored["predictor"] == theirs].set_index("year")["state_error_pct"]
        got = results["summaries"][ours]["by_year_state_wape_pct"]
        assert {int(y): v for y, v in got.items()} == pytest.approx(expected.to_dict(), abs=0.006)
    daniel_file = run.REPO / "test_models" / "danielModel" / "out" / "backtest_by_year.csv"
    if daniel_file.is_file():
        daniel = pd.read_csv(daniel_file)
        daniel = daniel[(daniel["target"] == "silage") & (daniel["candidate"] == "nodrift_nass")
                        & daniel["year"].isin(run.BACKTEST_YEARS)].set_index("year")["state_error_pct"]
        got = results["summaries"]["incumbent_nodrift_nass"]["by_year_state_wape_pct"]
        assert {int(y): v for y, v in got.items()} == pytest.approx(daniel.to_dict(), abs=0.006)
    if results["status"] != "done":
        assert all(str(v).startswith("UNCOMPUTED") for v in results["fsa_rows"].values())
