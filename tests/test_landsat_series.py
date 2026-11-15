"""Landsat pixels: the QA mask, the reflectance scale and the per-field medians, all without the network."""

from datetime import UTC, datetime
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import box

from kernelag import landsat_series
from kernelag.landsat_series import COLUMNS, clear_mask, field_medians, reflectance

CLEAR_LAND = 21824    # bit 6 (clear) plus low cloud, shadow, snow and cirrus confidence (bits 8, 10, 12, 14)
CLEAR_WATER = 21952   # the same plus bit 7 (water)
FILL = 1              # bit 0: no data in the scene here


def _refl(dn):
    """The published Collection 2 Level-2 scale, written out independently of the module."""
    return max(dn * 2.75e-05 - 0.2, 0.0)


def _index(a, b):
    return (_refl(a) - _refl(b)) / (_refl(a) + _refl(b))


@pytest.mark.parametrize("bit", range(6))
def test_each_cloud_bit_makes_a_pixel_not_clear(bit):
    assert not clear_mask(np.array([1 << bit], dtype="uint16"))[0]
    assert not clear_mask(np.array([CLEAR_LAND | (1 << bit)], dtype="uint16"))[0]


def test_water_and_clear_land_stay_clear():
    assert clear_mask(np.array([CLEAR_LAND, CLEAR_WATER, 1 << 7, 1 << 6], dtype="uint16")).all()
    # Confidence bits alone (8-15) are not masked: only the high-confidence calls in bits 1-5 are.
    assert clear_mask(np.array([0xFF00], dtype="uint16"))[0]


def test_reflectance_is_dn_times_scale_plus_offset_clipped_at_zero():
    dn = np.array([0, 1, 7272, 7273, 10000, 20000, 43636, 65535], dtype="uint16")
    expected = [_refl(int(v)) for v in dn]
    np.testing.assert_allclose(reflectance(dn), expected, rtol=0, atol=1e-12)
    assert reflectance(np.array([20000]))[0] == pytest.approx(0.35, abs=1e-12)
    assert reflectance(np.array([0, 7272])).tolist() == [0.0, 0.0]   # nodata and dark water do not go negative


# Two fields on a 3 x 4 grid; 0 is outside both fields.
ZONES = np.array([[1, 1, 1, 0],
                  [1, 1, 2, 2],
                  [0, 2, 2, 2]])
RED, SWIR16, SWIR22 = 9000, 18000, 14000


def _scene(nir, qa, red=None):
    red = np.full(ZONES.shape, RED) if red is None else red
    bands = {"red": red, "nir08": nir, "swir16": np.full(ZONES.shape, SWIR16),
             "swir22": np.full(ZONES.shape, SWIR22), "qa_pixel": qa}
    return xr.Dataset({b: (("y", "x"), np.asarray(v, dtype="uint16")) for b, v in bands.items()})


def _medians(scene):
    zones = ZONES.ravel()
    return field_medians(scene, zones, zones > 0, np.array(["a", "b"]), pd.Timestamp("2023-08-15"), 2023,
                         {"2023-08-15": "landsat-9"})


def test_field_medians_on_a_two_field_scene():
    nir = np.array([[60000, 25000, 25000, 60000],
                    [26000, 27000, 20000, 60000],
                    [60000, 60000, 0, 22000]])
    red = np.full(ZONES.shape, RED)
    red[0, 1] = 0                                      # field a: one pixel with a nodata band
    qa = np.array([[CLEAR_LAND | 1 << 3, CLEAR_LAND, CLEAR_LAND, CLEAR_LAND],     # a: cloud, nodata, clear
                   [CLEAR_LAND, CLEAR_LAND, CLEAR_WATER, CLEAR_LAND | 1 << 4],    # a: clear x2; b: water, shadow
                   [CLEAR_LAND, 1 << 5, FILL, CLEAR_LAND]])                       # b: snow, fill, clear
    out = _medians(_scene(nir, qa, red)).sort_values("field_id").reset_index(drop=True)

    assert set(out.columns) == set(COLUMNS)
    assert out["field_id"].tolist() == ["a", "b"]
    # a: 3 of 5 pixels clear (the cloud and the nodata pixel drop out); the 60000 cloud value is ignored.
    # b: water and one clear pixel count, shadow, snow and fill do not: 2 of 5.
    assert out["valid_frac"].tolist() == pytest.approx([0.6, 0.4])
    assert out.loc[0, "ndvi"] == pytest.approx(_index(26000, RED))
    assert out.loc[1, "ndvi"] == pytest.approx((_index(20000, RED) + _index(22000, RED)) / 2)
    assert out.loc[0, "ndmi"] == pytest.approx(_index(26000, SWIR16))
    assert out["ndti"].tolist() == pytest.approx([_index(SWIR16, SWIR22)] * 2)
    assert out["platform"].tolist() == ["landsat-9"] * 2
    assert out["year"].tolist() == [2023, 2023]
    assert (out["date"] == pd.Timestamp("2023-08-15")).all()


def test_a_date_with_no_clear_field_pixel_gives_nothing():
    nir = np.full(ZONES.shape, 25000)
    qa = np.where(ZONES > 0, CLEAR_LAND | 1 << 3, CLEAR_LAND)   # every field pixel cloudy, outside clear
    assert _medians(_scene(nir, qa)) is None


def test_a_field_with_no_clear_pixel_is_left_out_not_zero():
    nir = np.full(ZONES.shape, 25000)
    qa = np.where(ZONES == 2, FILL, CLEAR_LAND)                 # field b outside the scene footprint
    out = _medians(_scene(nir, qa))
    assert out["field_id"].tolist() == ["a"]
    assert out["valid_frac"].tolist() == [1.0]


def test_platform_by_date_keeps_both_names_if_they_ever_share_a_day():
    def item(day, platform):
        return SimpleNamespace(datetime=datetime(2023, 8, day, 15, 46, tzinfo=UTC), properties={"platform": platform})

    found = landsat_series._platforms_by_date([item(7, "landsat-8"), item(15, "landsat-9"), item(15, "landsat-8")])
    assert found == {"2023-08-07": "landsat-8", "2023-08-15": "landsat-8+landsat-9"}


def test_cells_are_cached_under_their_own_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KERNEL_NO_MANIFEST", "1")
    calls = []

    def fake_cell(fields_utm, year):
        calls.append(year)
        return pd.DataFrame({"field_id": ["7"], "date": [pd.Timestamp("2023-08-15")], "year": [year],
                             "valid_frac": [1.0], "ndvi": [0.8], "ndmi": [0.3], "ndti": [0.1],
                             "platform": ["landsat-9"]})

    monkeypatch.setattr(landsat_series, "cell_series", fake_cell)
    fields = gpd.GeoDataFrame({"field_id": ["7"], "year": [2023]},
                              geometry=[box(-76.85, 39.02, -76.849, 39.021)], crs="EPSG:4326")
    first = landsat_series.series_for_fields(fields, "demo")
    files = list((tmp_path / "landsat_series" / "demo").glob("*_2023.csv"))
    assert len(files) == 1 and pd.read_csv(files[0]).columns.tolist() == COLUMNS
    again = landsat_series.series_for_fields(fields, "demo")   # read back from the cache, not pulled again
    assert calls == [2023] and len(first) == len(again) == 1


def test_parallel_pull_files_get_listed_in_the_manifest(tmp_path, monkeypatch):
    # Children of a parallel pull skip the manifest; the parent lists the cached files afterwards.
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KERNEL_NO_MANIFEST", "1")
    monkeypatch.setattr(landsat_series, "cell_series", lambda fields_utm, year: pd.DataFrame(columns=COLUMNS))
    fields = gpd.GeoDataFrame({"field_id": ["7", "8"], "year": [2023, 2023]},
                              geometry=[box(-76.85, 39.02, -76.849, 39.021), box(-76.30, 39.02, -76.299, 39.021)],
                              crs="EPSG:4326")
    landsat_series.series_for_fields(fields, "demo")      # what the children write, with no manifest rows
    assert not (tmp_path / "DATA_MANIFEST.tsv").exists()
    monkeypatch.delenv("KERNEL_NO_MANIFEST")
    cells = sorted(landsat_series.assign_cells(fields)["cell"].unique())
    assert landsat_series.record_parts(fields, "demo", cells[:1]) == 1
    listed = (tmp_path / "DATA_MANIFEST.tsv").read_text(encoding="utf-8")
    assert f"landsat_series/demo/{cells[0]}_2023.csv" in listed and landsat_series.SOURCE_URL in listed
    assert landsat_series.record_parts(fields, "demo", None) == 2
