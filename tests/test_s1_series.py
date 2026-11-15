"""Sentinel-1: pass grouping, solar dates, GRD calibration, image-space field medians, range registration, look
weather, the RTC account gate and caching, all checked without the network."""

from datetime import UTC, datetime
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from rasterio.control import GroundControlPoint
from rasterio.transform import GCPTransformer
from shapely.geometry import box

from kernelag import s1_series, s2_series
from kernelag.s1_series import (
    COLUMNS,
    NODATA,
    RTC_COLLECTION,
    calibrate_sigma0,
    group_passes,
    image_field_stats,
    load_s1_series,
    look_weather,
    noise_at,
    parse_calibration,
    parse_noise,
    pass_field_medians,
    pass_key,
    shapely_translate,
    shift_scores,
    solar_date,
    to_db,
    to_image,
    track_shift,
    valid_mask,
    vectors_at,
)


def _item(item_id, platform, absolute_orbit, when, bands=("vv", "vh")):
    """A stand-in for a STAC item: only the parts the pass logic reads."""
    props = {"platform": platform, "sat:absolute_orbit": absolute_orbit}
    return SimpleNamespace(id=item_id, properties=props, datetime=when, assets={b: object() for b in bands})


def test_to_db_converts_power_and_refuses_non_positive():
    out = to_db([1.0, 0.1, 0.01, 0.0, -1.0, np.nan])
    assert np.allclose(out[:3], [0.0, -10.0, -20.0])
    assert np.isnan(out[3:]).all()


def test_valid_mask_drops_fill_zero_negative_and_nan():
    values = np.array([0.05, NODATA, 0.0, -0.1, np.nan, np.inf, 1e-4], dtype="float32")
    assert valid_mask(values).tolist() == [True, False, False, False, False, False, True]


def test_solar_date_moves_western_evening_passes_back_a_day():
    assert solar_date(pd.Timestamp("2023-09-01T01:50Z"), -120.0) == pd.Timestamp("2023-08-31")
    assert solar_date(pd.Timestamp("2023-09-01T23:07Z"), -76.9) == pd.Timestamp("2023-09-01")
    # Naive timestamps are read as UTC; a morning pass far east of Greenwich moves forward.
    assert solar_date(datetime(2023, 9, 1, 22, 0), 45.0) == pd.Timestamp("2023-09-02")
    assert solar_date(pd.Timestamp("2023-09-01T23:07Z"), -76.9).tzinfo is None


def test_pass_key_joins_slices_of_one_datatake_and_splits_satellites():
    t = datetime(2021, 7, 1, 23, 7, tzinfo=UTC)
    a1, a2 = _item("a1", "SENTINEL-1A", 38500, t), _item("a2", "SENTINEL-1A", 38500, t)
    b = _item("b", "SENTINEL-1B", 38500, t)   # same orbit number, other satellite: another pass
    assert pass_key(a1) == pass_key(a2) == ("SENTINEL-1A", 38500)
    assert pass_key(b) != pass_key(a1)
    lonely = SimpleNamespace(id="x", properties={"platform": "SENTINEL-1A"}, datetime=t, assets={})
    assert pass_key(lonely) == ("SENTINEL-1A", "item:x")


def test_group_passes_orders_by_time_and_skips_single_band_items():
    day1 = datetime(2023, 7, 1, 23, 7, tzinfo=UTC)
    day2 = datetime(2023, 7, 3, 11, 0, tzinfo=UTC)
    items = [_item("late", "SENTINEL-1A", 2, day2), _item("early_s2", "SENTINEL-1A", 1, day1),
             _item("early_s1", "SENTINEL-1A", 1, day1), _item("vv_only", "SENTINEL-1A", 3, day1, bands=("vv",))]
    passes = group_passes(items)
    assert [[i.id for i in p] for p in passes] == [["early_s2", "early_s1"], ["late"]]


def test_pass_field_medians_on_a_synthetic_grid():
    # Field 1 (left two columns): one fill pixel. Field 2 (right column): only fill. Row 3 is outside.
    zones = np.array([[1, 1, 2], [1, 1, 2], [0, 0, 0]])
    vv = np.array([[0.1, 0.1, NODATA], [0.1, NODATA, NODATA], [5.0, 5.0, 5.0]], dtype="float32")
    # The VH value under the VV fill pixel is valid on its own but must not enter the median.
    vh = np.array([[0.01, 0.1, NODATA], [0.01, 9.9, NODATA], [5.0, 5.0, 5.0]], dtype="float32")
    out = pass_field_medians(vv, vh, zones, np.array(["f1", "f2"]))
    assert out["field_id"].tolist() == ["f1"]           # a field with no valid pixel gives no row
    row = out.iloc[0]
    assert row["valid_frac"] == pytest.approx(0.75)    # the fill pixel counts against coverage
    assert row["vv_db"] == pytest.approx(-10.0, abs=1e-4)
    assert row["vh_db"] == pytest.approx(-20.0, abs=1e-4)   # median of 0.01, 0.1, 0.01; 9.9 is excluded


# --- GRD calibration tables ----------------------------------------------------------------------------------

CALIBRATION_XML = b"""<calibration><calibrationVectorList count="2">
  <calibrationVector><azimuthTime>t</azimuthTime><line>0</line><pixel>0 100</pixel>
    <sigmaNought>600 500</sigmaNought></calibrationVector>
  <calibrationVector><azimuthTime>t</azimuthTime><line>200</line><pixel>0 100</pixel>
    <sigmaNought>700 600</sigmaNought></calibrationVector>
</calibrationVectorList></calibration>"""

NOISE_XML = b"""<noise><noiseRangeVectorList count="2">
  <noiseRangeVector><azimuthTime>t</azimuthTime><line>0</line><pixel>0 100</pixel>
    <noiseRangeLut>100 300</noiseRangeLut></noiseRangeVector>
  <noiseRangeVector><azimuthTime>t</azimuthTime><line>200</line><pixel>0 100</pixel>
    <noiseRangeLut>100 300</noiseRangeLut></noiseRangeVector>
</noiseRangeVectorList><noiseAzimuthVectorList count="2">
  <noiseAzimuthVector><swath>IW1</swath><firstAzimuthLine>0</firstAzimuthLine><firstRangeSample>0</firstRangeSample>
    <lastAzimuthLine>200</lastAzimuthLine><lastRangeSample>49</lastRangeSample><line>0 200</line>
    <noiseAzimuthLut>1.0 2.0</noiseAzimuthLut></noiseAzimuthVector>
  <noiseAzimuthVector><swath>IW2</swath><firstAzimuthLine>0</firstAzimuthLine><firstRangeSample>50</firstRangeSample>
    <lastAzimuthLine>200</lastAzimuthLine><lastRangeSample>100</lastRangeSample><line>0 200</line>
    <noiseAzimuthLut>1.0 1.0</noiseAzimuthLut></noiseAzimuthVector>
</noiseAzimuthVectorList></noise>"""

LEGACY_NOISE_XML = b"""<noise><noiseVectorList count="1">
  <noiseVector><azimuthTime>t</azimuthTime><line>0</line><pixel>0 100</pixel><noiseLut>50 50</noiseLut></noiseVector>
</noiseVectorList></noise>"""


def test_calibration_table_is_interpolated_bilinearly():
    table = parse_calibration(CALIBRATION_XML)
    assert [line for line, _, _ in table] == [0.0, 200.0]
    # Corners exact; the centre is the mean of the four corners.
    np.testing.assert_allclose(vectors_at(table, [0, 200, 100], [0, 100, 50]), [600, 600, 600])
    np.testing.assert_allclose(vectors_at(table, [100], [0]), [650])
    assert np.isnan(vectors_at([], [1], [1])).all()


def test_noise_is_range_times_the_azimuth_block_that_covers_the_point():
    noise = parse_noise(NOISE_XML)
    assert len(noise["range"]) == 2 and len(noise["azimuth"]) == 2
    # Row 100, column 25: range table 150, IW1 azimuth table 1.5 halfway down.
    np.testing.assert_allclose(noise_at(noise, [100, 100], [25, 75]), [150 * 1.5, 250 * 1.0])
    assert np.isnan(noise_at(noise, [300], [25])).all()    # outside every azimuth block: unknown, not zero
    legacy = parse_noise(LEGACY_NOISE_XML)                 # processing baselines before 2.90
    assert legacy["azimuth"] == [] and noise_at(legacy, [10], [10]).tolist() == [50.0]


def test_sigma0_removes_noise_then_divides_by_the_squared_gain():
    sigma0 = calibrate_sigma0([10_000, 10_000, 500], [100, 100, 100], [0, 9_000, 600])
    np.testing.assert_allclose(sigma0[:2], [1.0, 0.1])
    assert np.isnan(to_db(sigma0)[2])                      # noise above the signal: NaN, never a floor


# --- image space: GCP mapping, field medians, registration ---------------------------------------------------

def _gcp_transformer():
    """A synthetic scene: column = (lon + 77) * 1e4, row = (lat - 39) * 1e4 (rows run north, as ascending)."""
    gcps = [GroundControlPoint(row=r, col=c, x=-77 + c * 1e-4, y=39 + r * 1e-4)
            for r in (0, 50, 100) for c in (0, 50, 100)]
    return GCPTransformer(gcps, tps=True)


def test_field_outline_maps_into_the_image_and_medians_use_pixel_centres():
    outline = to_image(box(-77 + 10.5e-4, 39 + 5.5e-4, -77 + 20.5e-4, 39 + 15.5e-4), _gcp_transformer())
    np.testing.assert_allclose(outline.bounds, (10.5, 5.5, 20.5, 15.5), atol=1e-6)
    # Window starting at column 5, row 0. Pixel centres of columns 11-20 and rows 6-15 fall inside: 100 pixels.
    vv = np.full((25, 25), 50, dtype="uint16")
    vv[6:16, 6:16] = 100
    vh = vv // 2
    vv[10, 10] = 0                                         # one no-data pixel inside the field
    stats = image_field_stats(vv, vh, [(outline, 1)], origin=(5, 0)).iloc[0]
    assert stats["n_px"] == 100 and stats["valid_frac"] == pytest.approx(0.99)
    assert stats["vv"] == pytest.approx(100.0 ** 2) and stats["vh"] == pytest.approx(50.0 ** 2)   # DN^2
    assert (stats["centre_row"], stats["centre_col"]) == pytest.approx((10.5, 15.5))


def test_registration_finds_the_range_shift_where_fields_look_uniform():
    # A darker field to the west, a brighter one to the east, speckle everywhere (4.4 looks, as in GRD high
    # resolution). The real field sits 3 columns further in range than its outline.
    rng = np.random.default_rng(0)
    mean = np.where(np.arange(60) < 23, 2_500.0, np.where(np.arange(60) < 43, 10_000.0, 90_000.0))
    intensity = mean[None, :] * rng.gamma(4.4, 1 / 4.4, (40, 60))
    vv = np.sqrt(intensity).round().astype("uint16")
    outline = box(19.5, 9.5, 39.5, 29.5)                  # covers columns 20-39 at shift 0; the field is 23-42
    shifts = np.arange(-6, 7)
    scores = shift_scores(vv, vv, [(outline, 1)], origin=(0, 0), shifts=shifts)
    assert shifts[int(np.nanargmin(scores))] == 3
    assert track_shift([scores, scores + 0.1], shifts) == 3
    assert track_shift([np.full(len(shifts), np.nan)], shifts) == 0     # no evidence: no shift
    assert shapely_translate(outline, 3).bounds == (22.5, 9.5, 42.5, 29.5)
    tiny = box(19.5, 9.5, 22.5, 12.5)                      # 9 pixels: too few to judge an edge
    assert np.isnan(shift_scores(vv, vv, [(tiny, 1)], (0, 0), shifts)).all()


# --- weather, gate, caching ----------------------------------------------------------------------------------

def test_rain_window_depends_on_the_pass_time_and_missing_weather_stays_nan():
    daily = pd.DataFrame({"date": pd.date_range("2023-10-01", periods=4), "tmin_c": [5.0, -1.0, 2.0, 3.0],
                          "prcp_mm": [1.0, 2.0, 4.0, 8.0], "swe_mm": [0.0, 3.0, 0.0, 0.0]})
    looks = pd.DataFrame({"date": pd.to_datetime(["2023-10-03", "2023-10-03", "2023-10-01"]),
                          "solar_hour": [18, 6, 18]})
    out = look_weather(looks, daily)
    # Evening pass on the 3rd: rain of the 2nd and 3rd. Morning pass: the 1st and 2nd. The 1st lacks its eve.
    assert out["rain_48h_mm"].tolist()[:2] == [6.0, 3.0] and np.isnan(out["rain_48h_mm"].iloc[2])
    assert out["tmin_c"].tolist() == [2.0, 2.0, 5.0] and out["swe_mm"].tolist() == [0.0, 0.0, 0.0]
    empty = look_weather(looks, None)
    assert empty[["tmin_c", "rain_48h_mm", "swe_mm"]].isna().all().all()


def test_rtc_is_refused_without_an_account_key(monkeypatch):
    monkeypatch.setattr(s1_series, "_pc_key_configured", lambda: False)
    fields = gpd.GeoDataFrame({"field_id": ["7"]}, geometry=[box(0, 0, 1, 1)], crs="EPSG:32618")
    with pytest.raises(RuntimeError, match="account"):
        s1_series._search_passes(fields, 2023, RTC_COLLECTION)      # refused before any request
    with pytest.raises(ValueError, match="unknown"):
        s1_series._search_passes(fields, 2023, "sentinel-1-slc")


def test_key_presence_is_detected_from_the_environment(monkeypatch):
    monkeypatch.setenv("PC_SDK_SUBSCRIPTION_KEY", "not-a-real-key")
    assert s1_series._pc_key_configured() is True


def test_load_keeps_two_passes_on_one_solar_date(tmp_path):
    rows = pd.DataFrame({
        "field_id": [7, 7, 7], "date": ["2023-08-01", "2023-08-01", "2023-08-01"], "year": 2023,
        "valid_frac": 1.0, "vv_db": [-9.0, -10.0, -10.0], "vh_db": [-14.0, -15.0, -15.0],
        "relative_orbit": [106, 4, 4], "orbit_state": ["ascending", "descending", "descending"],
        "platform": "SENTINEL-1A", "tmin_c": 15.0, "rain_48h_mm": 0.0, "swe_mm": 0.0, "range_shift_px": 4,
    })[COLUMNS]
    rows.to_csv(tmp_path / "34_432_2023.csv", index=False)
    series = load_s1_series(tmp_path)
    assert len(series) == 2                            # morning and evening pass kept; the exact repeat dropped
    assert series["field_id"].tolist() == ["7", "7"]
    assert series["date"].dt.strftime("%Y-%m-%d").unique().tolist() == ["2023-08-01"]


def test_series_for_fields_caches_radar_in_its_own_folder(tmp_path, monkeypatch):
    # The S1 wrapper must never fall through to the Sentinel-2 defaults (folder, puller, columns).
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KERNEL_NO_MANIFEST", "1")
    calls = []

    def fake_cell(fields_utm, year, collection):
        calls.append((year, collection))
        return pd.DataFrame([dict.fromkeys(COLUMNS, 1.0) | {"field_id": "7", "date": "2023-08-01", "year": year}])

    monkeypatch.setattr(s1_series, "cell_series", fake_cell)
    assert s1_series.series_for_fields is not s2_series.series_for_fields
    fields = gpd.GeoDataFrame({"field_id": ["7"], "year": [2023]},
                              geometry=[box(-76.85, 39.02, -76.849, 39.021)], crs="EPSG:4326")
    first = s1_series.series_for_fields(fields, "demo")
    again = s1_series.series_for_fields(fields, "demo")              # read back from the cache
    files = list((tmp_path / "s1_series" / "demo").glob("*_2023.csv"))
    assert len(files) == 1 and pd.read_csv(files[0]).columns.tolist() == COLUMNS
    assert calls == [(2023, "sentinel-1-grd")] and len(first) == len(again) == 1
    assert not (tmp_path / "s2_series").exists()
    monkeypatch.setattr(s1_series, "_pc_key_configured", lambda: True)
    s1_series.series_for_fields(fields, "demo", collection=RTC_COLLECTION)
    assert list((tmp_path / "s1_rtc_series" / "demo").glob("*.csv")) and calls[-1] == (2023, RTC_COLLECTION)
    monkeypatch.delenv("KERNEL_NO_MANIFEST")
    assert s1_series.record_parts(fields, "demo", None, "s1_series", s1_series.SOURCE_URL) == 1
    assert "s1_series/demo/" in (tmp_path / "DATA_MANIFEST.tsv").read_text(encoding="utf-8")


def test_a_cache_from_an_older_puller_stops_the_run_unless_forced(tmp_path, monkeypatch):
    # An RTC-era file (no weather columns) must not be read back as a finished GRD cell.
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KERNEL_NO_MANIFEST", "1")
    fields = gpd.GeoDataFrame({"field_id": ["7"], "year": [2023]},
                              geometry=[box(-76.85, 39.02, -76.849, 39.021)], crs="EPSG:4326")
    cell = s1_series.assign_cells(fields)["cell"].iloc[0]
    folder = tmp_path / "s1_series" / "demo"
    folder.mkdir(parents=True)
    (folder / f"{cell}_2023.csv").write_text("field_id,date,year,valid_frac,vv_db,vh_db,relative_orbit,orbit_state,"
                                             "platform\n7,2023-08-01,2023,1.0,-9,-15,4,ascending,SENTINEL-1A\n")
    monkeypatch.setattr(s1_series, "cell_series", lambda fields_utm, year, collection: pd.DataFrame(columns=COLUMNS))
    with pytest.raises(RuntimeError, match="--force"):
        s1_series.series_for_fields(fields, "demo")
    s1_series.series_for_fields(fields, "demo", force=True)
    assert pd.read_csv(folder / f"{cell}_2023.csv").columns.tolist() == COLUMNS
