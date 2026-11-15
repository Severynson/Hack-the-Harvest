"""Tests for the September moisture rule builder (synthetic series only; no real labels are read).

Run from the repository root:
    .venv/Scripts/python.exe -m pytest -q test_models/featureTests/lswi_rule/test_build.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_SPEC = importlib.util.spec_from_file_location("lswi_build", Path(__file__).with_name("build.py"))
build = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build)


def looks(field_id, year, rows):
    """Series rows from (month-day, valid_frac, ndmi[, ndvi]) tuples."""
    out = []
    for row in rows:
        day, valid, ndmi = row[:3]
        ndvi = row[3] if len(row) > 3 else 0.5
        out.append({"field_id": field_id, "year": year, "date": pd.Timestamp(f"{year}-{day}"),
                    "valid_frac": valid, "ndmi": ndmi, "ndvi": ndvi})
    return out


@pytest.fixture()
def series():
    rows = []
    # Cut early: two bare September looks and one green one (the green look is the last).
    rows += looks("A", 2023, [("09-04", 1.0, 0.10), ("09-14", 1.0, 0.12), ("09-29", 1.0, 0.40)])
    # Only cloudy September looks: no clear evidence, so no call.
    rows += looks("B", 2023, [("09-04", 0.3, 0.05), ("08-20", 1.0, 0.30)])
    # Median exactly on the published threshold: the rule is "<= 0.15", so silage.
    rows += looks("C", 2023, [("09-02", 1.0, 0.15), ("09-20", 1.0, 0.15)])
    # Standing green crop all September: grain.
    rows += looks("D", 2023, [("09-04", 1.0, 0.35), ("09-24", 0.9, 0.30)])
    # No September look at all.
    rows += looks("E", 2023, [("08-30", 1.0, 0.05), ("10-01", 1.0, 0.05)])
    # Same id in another year is a separate field-year.
    rows += looks("A", 2022, [("09-10", 1.0, 0.30), ("09-25", 1.0, 0.31)])
    # Maize-condition inputs for field D: bare May, green and moist July.
    rows += looks("D", 2023, [("05-10", 1.0, -0.10, 0.15), ("07-15", 1.0, 0.30, 0.85)])
    return pd.DataFrame(rows)


def by_key(table, field_id, year):
    return table[(table["field_id"] == field_id) & (table["year"] == year)].iloc[0]


def test_published_rule_uses_median_of_clear_september_looks(series):
    table = build.september_lswi(series)
    a = by_key(table, "A", 2023)
    assert a["lswi_sep_n"] == 3
    assert a["lswi_sep_median"] == pytest.approx(0.12)
    assert a["lswi_sep_min"] == pytest.approx(0.10)
    assert a["lswi_sep_last"] == pytest.approx(0.40)
    assert a["lswi_rule_silage"] == 1
    assert a["lswi_rule_sep_min"] == 1
    assert a["lswi_rule_sep_last"] == 0          # the latest look alone would call grain
    assert a["lswi_sep_late_n"] == 1              # only 29 September is in the second half
    assert a["lswi_rule_sep_late"] == 0


def test_threshold_is_inclusive_and_green_september_is_grain(series):
    table = build.september_lswi(series)
    assert by_key(table, "C", 2023)["lswi_rule_silage"] == 1
    assert by_key(table, "D", 2023)["lswi_rule_silage"] == 0
    assert by_key(table, "A", 2022)["lswi_rule_silage"] == 0


def test_no_clear_september_look_gives_no_call(series):
    table = build.september_lswi(series)
    for field_id in ["B", "E"]:
        row = by_key(table, field_id, 2023)
        assert row["lswi_sep_n"] == 0
        assert np.isnan(row["lswi_sep_median"]) and np.isnan(row["lswi_sep_min"])
        assert pd.isna(row["lswi_rule_silage"])
        assert all(pd.isna(row[rule]) for rule in build.SENSITIVITY_RULES)


def test_one_row_per_field_year_and_contract_columns(series):
    table = build.september_lswi(series)
    assert len(table) == 6
    assert not table.duplicated(["field_id", "year"]).any()
    assert set(build.FEATURES) <= set(table.columns)
    assert len(build.FEATURES) <= 2
    assert build.RULE_COLUMN in table.columns
    assert all(column.startswith("lswi_") for column in build.FEATURE_COLUMNS)


def test_maize_conditions_are_descriptive_and_missing_stays_missing(series):
    table = build.september_lswi(series)
    d = by_key(table, "D", 2023)
    assert d["lswi_c1_pass"] == 1 and d["lswi_c2_pass"] == 1
    assert pd.isna(by_key(table, "A", 2023)["lswi_c1_pass"])


def test_scores_and_balanced_accuracy():
    group = pd.DataFrame({
        "is_silage": [1, 1, 0, 0, 0],
        "lswi_rule_silage": pd.array([1, pd.NA, 1, 0, 0], dtype="Int64"),
    })
    row = build.score_rule(group, "lswi_rule_silage")
    assert (row["n_covered"], row["coverage"]) == (4, 0.8)
    assert (row["TP"], row["FP"], row["FN"], row["TN"]) == (1, 1, 0, 2)
    assert row["balanced_accuracy"] == pytest.approx((1.0 + 2 / 3) / 2, abs=1e-3)
    # The uncovered silage field counts as grain when every row is scored.
    assert row["balanced_accuracy_all_rows"] == pytest.approx((0.5 + 2 / 3) / 2, abs=1e-3)


def test_missing_inputs_are_uncomputed(tmp_path):
    features, series, reason = build.build_dataset("nothing_here", tmp_path / "data")
    assert features is None and series is None
    assert "no Sentinel-2 series" in reason


def test_partial_rebuild_keeps_other_datasets(tmp_path, series):
    path = tmp_path / "features.csv"
    first = build.september_lswi(series).assign(dataset="one")
    second = build.september_lswi(series).assign(dataset="two")
    pd.concat([first, second]).to_csv(path, index=False)
    rebuilt = build.september_lswi(series).assign(dataset="two")
    merged = build.merge_previous(rebuilt, ["two"], path)
    assert sorted(merged["dataset"].value_counts().to_dict().items()) == [("one", 6), ("two", 6)]


def test_meta_keeps_contract_keys(tmp_path):
    path = tmp_path / "meta.json"
    build.write_meta(["quebec_maize_2023"], {"other": "no series"}, path)
    meta = json.loads(path.read_text(encoding="utf-8"))
    assert meta["group"] == "lswi"
    assert meta["features"] == ["lswi_sep_median", "lswi_sep_min"]
    assert meta["rule_column"] == "lswi_rule_silage"
    assert meta["datasets_built"] == ["quebec_maize_2023"]
    assert meta["uncomputed"] == {"other": "no series"}
    assert meta["rule_definition"]["threshold"] == 0.15
