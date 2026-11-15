"""Tests for the distance-to-dairy feature builder (test_models/featureTests/dairy_distance/build.py).

Offline and fast: synthetic points and rows, plus a contract check of the built outputs when they exist.
Run: ``.venv/Scripts/python.exe -m pytest -q test_models/featureTests/dairy_distance/test_dairy_distance.py``
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
# Loaded under a unique name: sibling feature groups also have a build.py.
_spec = importlib.util.spec_from_file_location("dairydist_build", HERE / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def test_nearest_km_and_empty_sites():
    fields = np.array([[0.0, 0.0], [3000.0, 4000.0]])
    sites = np.array([[0.0, 1000.0], [3000.0, 0.0]])
    assert np.allclose(build.nearest_km(fields, sites), [1.0, 4.0])
    assert np.isnan(build.nearest_km(fields, np.empty((0, 2)))).all()   # no evidence stays NaN


def test_count_within_includes_boundary():
    fields = np.array([[0.0, 0.0]])
    sites = np.array([[18000.0, 0.0], [18000.1, 0.0], [5000.0, 0.0]])
    assert build.count_within(fields, sites, 18.0).tolist() == [2.0]
    assert build.count_within(fields, np.empty((0, 2)), 18.0).tolist() == [0.0]


def test_kernel_sum_weights_and_cut():
    fields = np.array([[0.0, 0.0]])
    points = np.array([[0.0, 0.0], [5000.0, 0.0], [26000.0, 0.0]])   # the last one is past the 25 km cut
    total = build.kernel_sum(fields, points, weights=np.array([2.0, 1.0, 100.0]))
    assert total[0] == pytest.approx(2.0 + np.exp(-1.0))


def test_select_role_units_maps_codes_and_drops_others():
    units = pd.DataFrame({"id_provinc": ["a", "b", "c", "d"], "code_mun": ["1"] * 4,
                          "rl0105a": ["8122", "8150", "8121", "8132"], "rl0302a": [1.0, 2.0, 3.0, 4.0],
                          "rl0403a": [100, None, 0, 5]})
    out = build.select_role_units(units)
    assert out["id_provinc"].tolist() == ["a", "b", "c"]
    assert out["kind"].tolist() == ["dairy", "dairy", "beef"]


def test_role_point_sets_need_building_and_accepted_point():
    sites = pd.DataFrame({"kind": ["dairy", "dairy", "dairy", "beef", "beef"],
                          "building_value": [10.0, 0.0, 10.0, 10.0, np.nan],
                          "rejet": [0, 0, 2, 0, 0], "lon": [0.0] * 5, "lat": [0.0] * 5})
    sets = build.role_point_sets(sites)
    assert len(sets["dairy"]) == 1        # building and accepted point
    assert len(sets["dairy_any"]) == 2    # buildings not required, rejected point still dropped
    assert len(sets["beef"]) == 1


def test_parse_ct_and_constant_capacity_flag():
    rows = [{"id": i, "name": f"x{i}", "assetType": "enteric_fermentation_maturedairycattle",
             "centroid": {"latitude": 45.0, "longitude": -72.0}, "capacity": 117.08, "year": 2025} for i in range(4)]
    rows.append({"id": 9, "name": "b", "assetType": "enteric_fermentation_otherbeefcattle",
                 "centroid": {"latitude": 45.1, "longitude": -72.1}, "capacity": 5.0, "year": 2025})
    table = build.parse_ct(rows, "CAN.11_1")
    assert table["kind"].tolist() == ["dairy"] * 4 + ["beef"]
    share = build.modal_capacity_share(table)
    assert share["CAN.11_1/dairy"]["modal_share"] == 1.0   # one value for every row: an imputed default
    assert build.parse_ct([], "USA.9_1").empty


def test_role_features_rule_follows_distance():
    fields = np.array([[0.0, 0.0], [10000.0, 0.0]])
    site = np.array([[1000.0, 0.0]])
    sets = {"dairy": site, "dairy_any": site, "beef": np.empty((0, 2))}
    out = build.role_features(fields, sets, None, None)
    assert out[build.RULE_COLUMN].tolist() == [1.0, 0.0]          # 1 km <= 1.5 km; 9 km is not
    assert out["dairydist_n_dairy_18km"].tolist() == [1.0, 1.0]
    assert out["dairydist_d_beef_km"].isna().all()                 # no beef sites: NaN, not zero distance
    assert out["dairydist_mb_sites_per_ha"].isna().all()           # no maize layer: NaN


def test_replace_datasets_keeps_other_datasets():
    old = pd.DataFrame({"dataset": ["a", "b"], "field_id": ["1", "2"], "year": [2023, 2023]})
    new = pd.DataFrame({"dataset": ["a"], "field_id": ["3"], "year": [2023]})
    out = build.replace_datasets(old, [new], ["a"])
    assert sorted(out["field_id"]) == ["2", "3"]


def test_preregistration_is_within_contract():
    assert 1 <= len(build.MODEL_FEATURES) <= 2
    assert all(c.startswith("dairydist_") for c in [*build.FEATURE_COLUMNS])
    assert build.RULE_COLUMN not in build.MODEL_FEATURES


@pytest.mark.skipif(not (HERE / "out" / "meta.json").exists(), reason="outputs not built yet")
def test_built_outputs_follow_contract():
    meta = json.loads((HERE / "out" / "meta.json").read_text(encoding="utf-8"))
    table = pd.read_csv(HERE / "out" / "features.csv", dtype={"field_id": str})
    assert meta["group"] == "dairydist" and meta["features"] == build.MODEL_FEATURES
    assert meta["rule_column"] == build.RULE_COLUMN
    assert list(table.columns[:3]) == ["dataset", "field_id", "year"]
    assert not table.duplicated(["dataset", "field_id", "year"]).any()
    assert set(table[build.RULE_COLUMN].dropna().unique()) <= {0.0, 1.0}
    assert not table["field_id"].str.endswith(".0").any()
    maryland = table[table["dataset"] == "barc_2021_2023"]
    if len(maryland):   # no registry for Maryland: roll-based columns must stay NaN, never filled
        assert maryland[build.ROLE_COLUMNS].isna().all().all()
