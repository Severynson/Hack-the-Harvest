"""Landsat calibration, optical look merging, radar cut evidence and their fusion, on synthetic series only."""

import json

import numpy as np
import pandas as pd
import pytest

from kernelag.features import build_features
from kernelag.multisensor import (
    INDICES,
    OPTICAL_COLUMNS,
    RADAR_COLUMNS,
    RADAR_FEATURES,
    apply_calibration,
    fit_calibration,
    fit_calibration_from,
    fuse,
    load_calibration,
    load_landsat,
    load_radar,
    main,
    match_pairs,
    multisensor_features,
    optical_series,
    radar_feature_table,
    radar_features,
)
from tests.test_features import CLIFF, FADE


def _dates(doys, year=2023):
    return pd.Timestamp(f"{year}-01-01") + pd.to_timedelta(np.asarray(doys) - 1, unit="D")


def _looks(rows, field_id="a", year=2023):
    """rows: (day of year, valid_frac, ndvi) -> optical looks with ndmi/ndti derived from ndvi."""
    doy, valid, ndvi = (np.asarray(v, dtype=float) for v in zip(*rows))
    return pd.DataFrame({"field_id": field_id, "date": _dates(doy.astype(int), year), "year": year,
                         "valid_frac": valid, "ndvi": ndvi, "ndmi": ndvi - 0.4, "ndti": 0.1 + 0.1 * ndvi})


def _radar(points, field_id="a", orbit=33, year=2023, valid=1.0):
    """points: (day of year, vh_db, vv_db) -> Sentinel-1 looks on one track."""
    doy, vh, vv = zip(*points)
    return pd.DataFrame({"field_id": field_id, "date": _dates(doy, year), "year": year, "valid_frac": valid,
                         "vv_db": vv, "vh_db": vh, "relative_orbit": orbit, "orbit_state": "ascending",
                         "platform": "sentinel-1a"})


def _noisy_pairs(n, slope, intercept, outlier_share=0.2, seed=1, n_dates=8):
    rng = np.random.default_rng(seed)
    data = {"date_landsat": _dates(150 + 8 * (np.arange(n) % n_dates))}
    for index in INDICES:
        x = rng.uniform(-0.2, 0.9, n)
        y = intercept + slope * x + rng.normal(0, 0.01, n)
        bad = rng.permutation(n) < int(outlier_share * n)     # exactly that share are wild
        y[bad] = rng.uniform(-1, 1, bad.sum())
        data[f"{index}_landsat"], data[f"{index}_s2"] = x, y
    return pd.DataFrame(data)


# (1) calibration ---------------------------------------------------------------------------------------------

def test_calibration_recovers_a_known_line_despite_outliers():
    fits = fit_calibration(_noisy_pairs(400, slope=0.93, intercept=0.04))
    for index in INDICES:
        fit = fits[index]
        assert fit["calibrated"] and fit["mode"] == "line" and fit["n_pairs"] == 400 and fit["n_dates"] == 8
        assert fit["lodo_slope_min"] <= fit["slope"] <= fit["lodo_slope_max"]
        assert -0.2 <= fit["x_min"] <= fit["x_p05"] <= fit["x_p95"] <= fit["x_max"] <= 0.9
        assert abs(fit["slope"] - 0.93) < 0.03 and abs(fit["intercept"] - 0.04) < 0.02
        assert fit["residual_mad"] < 0.05     # the clean 80% sit on the line


def test_calibration_slope_from_a_subsample_still_recovers_the_line():
    fits = fit_calibration(_noisy_pairs(900, slope=1.06, intercept=-0.03), max_fit_pairs=300)
    assert fits["ndvi"]["n_pairs"] == 900
    assert abs(fits["ndvi"]["slope"] - 1.06) < 0.04 and abs(fits["ndvi"]["intercept"] + 0.03) < 0.03


def test_too_few_pairs_gives_the_identity_uncalibrated():
    fits = fit_calibration(_noisy_pairs(20, slope=0.8, intercept=0.1), min_pairs=30)
    for index in INDICES:
        assert fits[index]["mode"] == "identity"
        assert fits[index]["slope"] == 1.0 and fits[index]["intercept"] == 0.0
        assert fits[index]["calibrated"] is False and fits[index]["n_pairs"] == 20
    assert fit_calibration(pd.DataFrame())["ndvi"]["n_pairs"] == 0


def test_few_dates_or_a_date_unstable_slope_falls_back_to_an_offset():
    # Three dates (as on the 79_515 training cell): enough pairs, too few atmospheres for a line.
    pairs = _noisy_pairs(300, slope=0.9, intercept=0.05, outlier_share=0.0, n_dates=3)
    few = fit_calibration(pairs)
    assert few["ndvi"]["mode"] == "offset" and few["ndvi"]["slope"] == 1.0 and few["ndvi"]["calibrated"]
    assert few["ndvi"]["intercept"] == pytest.approx(np.median(pairs["ndvi_s2"] - pairs["ndvi_landsat"]))
    assert np.isnan(few["ndvi"]["lodo_slope_min"])                 # no line was tried
    # Five dates, each on its own line over its own NDVI range (as the 79_515 dates were, slopes 0.80 to 1.25):
    # leaving a date out moves the slope, so the line is not trusted.
    tilted = _noisy_pairs(500, slope=0.9, intercept=0.05, outlier_share=0.0, n_dates=5)
    for k, (day, slope) in enumerate(zip(sorted(tilted["date_landsat"].unique()), (0.80, 1.25, 1.07, 0.85, 1.2))):
        on_day = tilted["date_landsat"] == day
        x = np.linspace(0.1 + 0.15 * k, 0.3 + 0.15 * k, on_day.sum())
        tilted.loc[on_day, "ndvi_landsat"], tilted.loc[on_day, "ndvi_s2"] = x, 0.05 + slope * x
    fit = fit_calibration(tilted)["ndvi"]
    assert fit["mode"] == "offset" and fit["lodo_slope_max"] - fit["lodo_slope_min"] > 0.05
    assert fit_calibration(tilted.drop(columns="date_landsat"))["ndmi"]["mode"] == "offset"   # dates unknown


def test_apply_calibration_maps_calibrated_indices_only_and_clips():
    landsat = pd.DataFrame({"ndvi": [0.5, 1.0], "ndmi": [0.2, 0.3], "ndti": [0.1, 0.1]})
    calibration = {"indices": {
        "ndvi": {"slope": 0.9, "intercept": 0.15, "calibrated": True},
        "ndmi": {"slope": 2.0, "intercept": 0.5, "calibrated": False},
    }}
    out = apply_calibration(landsat, calibration)
    assert out["ndvi"].tolist() == pytest.approx([0.6, 1.0])     # 0.15 + 0.9 = 1.05 clipped to 1
    assert out["ndmi"].tolist() == [0.2, 0.3] and out["ndti"].tolist() == [0.1, 0.1]
    assert landsat["ndvi"].tolist() == [0.5, 1.0]                 # input untouched
    assert apply_calibration(landsat, None).equals(landsat)


# (2) pairing ------------------------------------------------------------------------------------------------

def test_match_pairs_respects_the_day_window_and_clear_share():
    s2 = _looks([(100, 1.0, 0.30), (110, 0.6, 0.40), (120, 1.0, 0.50), (130, 0.9, 0.60)])
    landsat = pd.concat([
        _looks([(101, 0.95, 0.31),    # pairs with S2 day 100
                (105, 1.00, 0.35),    # no S2 look within a day
                (110, 1.00, 0.41),    # the S2 look that day is too cloudy
                (120, 0.70, 0.51),    # this Landsat look is too cloudy
                (131, 0.90, 0.61)]),  # pairs with S2 day 130
        _looks([(100, 1.0, 0.3)], field_id="b"),            # another field: never paired with field a
        _looks([(100, 1.0, 0.3)], year=2022),               # another year: never paired
    ], ignore_index=True)
    pairs = match_pairs(s2, landsat)
    assert list(pairs.columns) == ["field_id", "year", "date_s2", "date_landsat", "ndvi_s2", "ndvi_landsat",
                                   "ndmi_s2", "ndmi_landsat", "ndti_s2", "ndti_landsat"]
    assert pairs["date_landsat"].dt.day_of_year.tolist() == [101, 131]
    assert pairs["date_s2"].dt.day_of_year.tolist() == [100, 130]
    assert pairs["ndvi_s2"].tolist() == [0.3, 0.6] and pairs["ndvi_landsat"].tolist() == [0.31, 0.61]

    wider = match_pairs(s2, landsat, max_days=5)
    assert wider["date_landsat"].dt.day_of_year.tolist() == [101, 105, 131]
    looser = match_pairs(s2, landsat, min_valid=0.5)           # S2 day 110 (0.6) and Landsat day 120 (0.7) now pass
    assert looser["date_landsat"].dt.day_of_year.tolist() == [101, 110, 120, 131]


# (3) optical merging ----------------------------------------------------------------------------------------

def test_optical_series_keeps_one_look_per_day_in_preference_order():
    s2 = _looks([(200, 0.3, 0.80), (210, 0.8, 0.70), (220, 0.2, 0.60), (240, 0.9, 0.40), (250, 1.0, np.nan)])
    landsat = _looks([(200, 0.9, 0.81),   # S2 unusable that day: Landsat kept
                      (210, 1.0, 0.71),   # both usable: S2 kept even though Landsat is clearer
                      (220, 0.4, 0.61),   # both unusable: S2 kept
                      (230, 0.7, 0.50),   # Landsat only
                      (250, 0.9, 0.30)])  # S2 has no NDVI that day: Landsat kept
    merged = optical_series(s2, landsat)
    assert list(merged.columns) == OPTICAL_COLUMNS
    by_day = merged.set_index(merged["date"].dt.day_of_year)
    assert by_day["sensor"].to_dict() == {200: "landsat", 210: "s2", 220: "s2", 230: "landsat", 240: "s2",
                                          250: "landsat"}
    assert by_day.loc[200, "valid_frac"] == 0.9 and by_day.loc[220, "valid_frac"] == 0.2


def test_optical_series_applies_the_calibration_to_landsat_looks_only():
    s2 = _looks([(200, 1.0, 0.8)])
    landsat = _looks([(208, 1.0, 0.5)])
    calibration = {"indices": {"ndvi": {"slope": 0.9, "intercept": 0.02, "calibrated": True}}}
    merged = optical_series(s2, landsat, calibration).set_index("sensor")
    assert merged.loc["s2", "ndvi"] == 0.8
    assert merged.loc["landsat", "ndvi"] == pytest.approx(0.47)


def test_an_unconfirmed_cross_sensor_drop_loses_its_landsat_look():
    # Clear Landsat look on day 205, hazy Sentinel-2 look two days later, then back up: haze, not a cut.
    s2 = _looks([(190, 1.0, 0.80), (207, 1.0, 0.70), (217, 1.0, 0.85), (245, 1.0, 0.80), (250, 1.0, 0.20),
                 (260, 1.0, 0.15)])
    landsat = _looks([(205, 1.0, 0.90), (247, 1.0, 0.79), (253, 1.0, 0.18)])
    merged = optical_series(s2, landsat)
    by_day = merged.set_index(merged["date"].dt.day_of_year)["sensor"].to_dict()
    assert 205 not in by_day                               # dropped: 0.90 -> 0.70 two days later never held
    assert by_day[247] == "landsat"                        # 0.80 -> 0.79: below the drop that needs confirming
    assert by_day[253] == "landsat"                        # 0.20 -> 0.18 confirmed low by day 260
    assert (merged["sensor"] == "s2").sum() == len(s2)     # Sentinel-2 looks are never removed
    # A real cut caught by Landsat between Sentinel-2 looks and confirmed afterwards is kept.
    cut = optical_series(_looks([(240, 1.0, 0.82), (250, 1.0, 0.25), (260, 1.0, 0.22)]),
                         _looks([(242, 1.0, 0.30)]))
    assert 242 in cut["date"].dt.day_of_year.tolist()
    # A "confirmation" five weeks later cannot tell haze from a cut: the Landsat look goes.
    late = optical_series(_looks([(207, 1.0, 0.70), (242, 1.0, 0.60)]), _looks([(205, 1.0, 0.90)]))
    assert late["sensor"].tolist() == ["s2", "s2"]


def test_landsat_only_field_years_are_left_out_by_default():
    s2 = CLIFF.assign(field_id="a", year=2023)
    landsat = pd.concat([_looks([(250, 1.0, 0.2)]), CLIFF.assign(field_id="zzz", year=2023, platform="landsat-8")])
    assert multisensor_features(s2, landsat)["field_id"].tolist() == ["a"]
    both = multisensor_features(s2, landsat, only_s2_field_years=False).set_index("field_id")
    assert both.loc["zzz", "n_looks_s2"] == 0 and both.loc["zzz", "n_looks_landsat"] > 0


def test_without_landsat_features_equal_the_sentinel2_only_path():
    s2 = pd.concat([CLIFF.assign(field_id="a", year=2023), FADE.assign(field_id="b", year=2023)],
                   ignore_index=True)
    pd.testing.assert_frame_equal(build_features(optical_series(s2)), build_features(s2))
    table = multisensor_features(s2)
    pd.testing.assert_frame_equal(table.drop(columns=["n_looks_s2", "n_looks_landsat"]), build_features(s2))
    assert table["n_looks_s2"].tolist() == [7, 8] and table["n_looks_landsat"].isna().all()


def test_a_landsat_look_inside_a_sentinel2_gap_narrows_the_cut_bracket():
    # Sentinel-2 misses the cut: green on day 245, next clear look day 260.
    s2 = CLIFF[CLIFF["date"].dt.day_of_year != 250].assign(field_id="a", year=2023)
    landsat = _looks([(250, 1.0, 0.2)])
    s2_only, both = multisensor_features(s2).iloc[0], multisensor_features(s2, landsat).iloc[0]
    assert (s2_only["cut_doy"], s2_only["cut_gap_days"]) == (260, 15)
    assert (both["cut_doy"], both["cut_gap_days"]) == (250, 5)
    assert both["n_looks_landsat"] == 1 and both["n_looks_s2"] == 6


# (4) radar evidence for silage-like and grain-like fields ---------------------------------------------------

# Cut green: VH holds its plateau, then falls on the look after the optical cliff (CLIFF cut day 250).
SILAGE_S1 = _radar([(160, -18, -10), (172, -16, -9.5), (184, -14.5, -9), (196, -14, -8.5), (208, -14, -8.2),
                    (220, -14.1, -8.2), (232, -14, -8), (244, -14.2, -8), (256, -21.5, -12), (268, -21.8, -12.5),
                    (280, -21, -12)], field_id="silage")
# Browns standing: VH sags for weeks after the optical decline (FADE decline day 265), the combine comes late.
GRAIN_S1 = _radar([(160, -18, -10), (172, -16, -9.5), (184, -14.5, -9), (196, -14, -8.5), (208, -14.2, -8.6),
                   (220, -14.5, -8.8), (232, -15, -9), (244, -15.3, -9), (256, -15.7, -9), (268, -16, -9),
                   (280, -16.3, -9), (292, -22, -13), (304, -22.2, -13)], field_id="grain")


def test_radar_lag_is_short_for_silage_and_long_for_grain():
    s2 = pd.concat([CLIFF.assign(field_id="silage", year=2023), FADE.assign(field_id="grain", year=2023)],
                   ignore_index=True)
    table = multisensor_features(s2, s1=pd.concat([SILAGE_S1, GRAIN_S1])).set_index("field_id")
    assert set(RADAR_FEATURES) <= set(table.columns)
    silage, grain = table.loc["silage"], table.loc["grain"]

    assert (silage["decline_doy"], silage["s1_cut_doy"], silage["radar_lag_days"]) == (250, 256, 6)
    assert (grain["decline_doy"], grain["s1_cut_doy"], grain["radar_lag_days"]) == (265, 292, 27)
    assert silage["s1_vh_drop_db"] == pytest.approx(7.3) and grain["s1_vh_drop_db"] == pytest.approx(5.7)
    assert grain["s1_fade_db"] == pytest.approx(2.3) and silage["s1_fade_db"] == pytest.approx(0.2)
    assert grain["s1_fade_db"] > silage["s1_fade_db"]                  # grain sags before the cut
    assert silage["s1_vhvv_before_db"] > grain["s1_vhvv_before_db"]    # and is drier just before it
    # Optical (245, 250] and radar (244, 256] share (245, 250]; grain (280, 290] and (280, 292] share 10 days.
    assert (silage["brackets_overlap"], silage["fused_cut_gap_days"]) == (1.0, 5.0)
    assert (grain["brackets_overlap"], grain["fused_cut_gap_days"]) == (1.0, 10.0)


# (5) bracket overlap ----------------------------------------------------------------------------------------

def test_bracket_overlap_is_half_open():
    optical = pd.DataFrame({
        "field_id": ["touch", "touch_back", "partial", "inside", "apart", "no_s1_cut", "no_s1_row", "no_cut"],
        "year": 2023,
        "cut_doy": [20, 30, 20, 20, 20, 20, 20, np.nan],
        "cut_gap_days": [10, 10, 10, 10, 10, 10, 10, np.nan],
        "decline_doy": [15, 15, 15, 15, 15, 15, 15, 15],
    })
    radar = pd.DataFrame({
        "field_id": ["touch", "touch_back", "partial", "inside", "apart", "no_s1_cut", "no_cut"],
        "year": 2023,
        "s1_cut_doy": [30, 20, 25, 18, 8, np.nan, 20],
        "s1_cut_gap_days": [10, 10, 10, 6, 4, np.nan, 10],
    })
    out = fuse(optical, radar).set_index("field_id")
    # (10, 20] and (20, 30] only touch: day 20 belongs to the first bracket, not the second.
    expected = {"touch": (0.0, np.nan), "touch_back": (0.0, np.nan), "partial": (1.0, 5.0),
                "inside": (1.0, 6.0), "apart": (0.0, np.nan), "no_s1_cut": (np.nan, np.nan),
                "no_s1_row": (np.nan, np.nan), "no_cut": (np.nan, np.nan)}
    for field_id, (overlap, gap) in expected.items():
        got = out.loc[field_id, ["brackets_overlap", "fused_cut_gap_days"]].to_numpy(float)
        np.testing.assert_array_equal(got, [overlap, gap], err_msg=field_id)
    assert out.loc["partial", "radar_lag_days"] == 10 and np.isnan(out.loc["no_s1_row", "radar_lag_days"])
    assert len(out) == len(optical)     # left join: every optical row kept, none added


# (6) tracks -------------------------------------------------------------------------------------------------

def test_a_level_offset_between_tracks_is_not_a_cut():
    # Track 10 sits 5 dB above track 99 (different incidence angle). Interleaved in time, a naive series would
    # show 5 dB "drops" every few days. The real cut (about day 282) is a 3 dB fall on each track.
    high = _radar([(d, -14.0, -8.0) for d in range(160, 281, 12)] + [(292, -17.0, -10.0), (304, -17.0, -10.0)],
                  orbit=10)
    low = _radar([(d, -19.0, -12.0) for d in range(166, 275, 12)] + [(286, -22.2, -14.0), (298, -22.2, -14.0)],
                 orbit=99)
    f = radar_features(pd.concat([high, low], ignore_index=True))
    assert f["s1_n_obs"] == 25 and f["s1_n_frozen"] == 0 and f["s1_n_wet"] == 0
    assert f["s1_vh_drop_db"] == pytest.approx(3.0)       # not the 5 dB jump between tracks
    # Track 10 has 13 usable looks against 12, so its evidence wins although track 99 fell 0.2 dB more.
    assert (f["s1_cut_doy"], f["s1_cut_gap_days"], f["s1_orbit"]) == (292, 12, 10)
    assert f["s1_fade_db"] == pytest.approx(0.0) and f["s1_vhvv_before_db"] == pytest.approx(-6.0)


def test_the_better_sampled_track_wins_over_a_bigger_fall_on_a_sparse_one():
    # A 24-day track piles up more change between looks than a 6-day one; the raw fall must not decide.
    every_24 = _radar([(d, -14.0, -8.0) for d in range(166, 275, 24)] + [(286, -19.0, -10.0), (310, -19.0, -10.0)],
                      orbit=1)
    every_6 = _radar([(d, -15.0, -9.0) for d in range(160, 281, 6)] + [(286, -18.0, -11.0), (292, -18.0, -11.0)],
                     orbit=2)
    f = radar_features(pd.concat([every_24, every_6], ignore_index=True))
    assert (f["s1_orbit"], f["s1_cut_gap_days"], f["s1_cut_doy"]) == (2, 6, 286)
    assert f["s1_vh_drop_db"] == pytest.approx(3.0)


def _weather(track, tmin=10.0, rain=0.0, swe=0.0):
    return track.assign(tmin_c=tmin, rain_48h_mm=rain, swe_mm=swe)


def test_frost_snow_and_the_last_look_never_make_a_cut():
    standing = [(d, -14.0, -8.0) for d in range(160, 305, 12)]                       # 13 looks, no harvest
    # A frozen look on day 316, then snow on 328: both 5 dB down. Neither may count as the cut.
    frozen = _weather(_radar(standing + [(316, -19.0, -13.0), (328, -19.5, -13.5)]))
    frozen.loc[frozen["date"].dt.day_of_year == 316, "tmin_c"] = -4.0
    frozen.loc[frozen["date"].dt.day_of_year == 328, "swe_mm"] = 2.0
    assert radar_features(frozen) == {"s1_n_obs": 13, "s1_n_frozen": 2, "s1_n_wet": 0}
    # The same fall on a mild final look cannot be confirmed by a later one: radar-undetected, not a guess.
    last = _weather(_radar(standing + [(316, -19.0, -13.0)]))
    assert radar_features(last) == {"s1_n_obs": 14, "s1_n_frozen": 0, "s1_n_wet": 0}
    # Without weather columns nothing is screened, but the confirmation rule still holds.
    assert "s1_cut_doy" not in radar_features(_radar(standing + [(316, -19.0, -13.0)]))


def test_wet_looks_play_no_part_in_a_step_and_a_one_look_dip_is_not_a_cut():
    # Rain lifts day 232 by 3 dB before a dry plateau look: without the screen that is a 3 dB "cut" on day 244.
    points = [(d, -14.0, -8.0) for d in range(160, 230, 12)] + [(232, -11.0, -5.0)]
    points += [(244, -14.0, -8.0), (256, -14.0, -8.0), (268, -20.0, -12.0), (280, -16.5, -9.0), (292, -20.5, -12.0)]
    track = _weather(_radar(points))
    track.loc[track["date"].dt.day_of_year == 232, "rain_48h_mm"] = 20.0
    # Day 280 is wet too and lifted back up: it must not veto the real cut on day 268 as its confirmation.
    track.loc[track["date"].dt.day_of_year == 280, "rain_48h_mm"] = 32.0
    f = radar_features(track)
    assert (f["s1_cut_doy"], f["s1_vh_drop_db"], f["s1_n_wet"], f["s1_n_obs"]) == (268, pytest.approx(6.0), 2, 10)
    unscreened = radar_features(track.drop(columns=["rain_48h_mm"]))
    assert "s1_cut_doy" not in unscreened or unscreened["s1_cut_doy"] != 268
    # Day 208 dips 3.5 dB and bounces straight back: not confirmed, so the real cut still wins.
    dip = _radar([(d, -14.0, -8.0) for d in range(160, 205, 12)] + [(208, -17.5, -9.0), (220, -14.0, -8.0),
                 (232, -14.0, -8.0), (244, -17.0, -9.0), (256, -17.2, -9.0)])
    f = radar_features(dip)
    assert (f["s1_cut_doy"], f["s1_vh_drop_db"]) == (244, pytest.approx(3.0))
    # A confirmed fall smaller than 2 dB is not a cut.
    small = _radar([(d, -14.0, -8.0) for d in range(160, 260, 12)] + [(268, -15.5, -8.5), (280, -15.6, -8.5)])
    assert "s1_cut_doy" not in radar_features(small)


def test_two_tracks_on_the_same_date_survive_loading(tmp_path, monkeypatch):
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path))
    folder = tmp_path / "s1_series" / "demo"
    folder.mkdir(parents=True)
    pd.DataFrame({
        "field_id": [7, 7, 7], "date": ["2023-09-01", "2023-09-01", "2023-09-01"], "year": 2023,
        "valid_frac": [1.0, 0.9, 0.4], "vv_db": [-9.0, -10.0, -11.0], "vh_db": [-15.0, -16.0, -17.0],
        "relative_orbit": [33, 106, 33], "orbit_state": ["ascending", "descending", "ascending"],
        "platform": "sentinel-1a",
    }).to_csv(folder / "79_515_2023.csv", index=False)
    s1 = load_radar("demo")
    assert s1["field_id"].tolist() == ["7", "7"] and s1["relative_orbit"].tolist() == [33, 106]
    assert s1["valid_frac"].tolist() == [1.0, 0.9]                  # the clearer duplicate of track 33 kept
    assert s1["date"].tolist() == [pd.Timestamp("2023-09-01")] * 2
    assert load_radar("missing") is None and load_landsat("missing") is None


# (7) too little radar evidence ------------------------------------------------------------------------------

def test_too_few_looks_gives_only_the_look_count():
    sparse = pd.concat([
        _radar([(200, -14, -8), (212, -14, -8), (260, -21, -12)], orbit=1),
        _radar([(206, -15, -9), (218, -15, -9), (266, -22, -13)], orbit=2),
        _radar([(230, -14, -8), (242, -21, -12)], orbit=1, valid=0.2),        # mostly masked: not counted
    ], ignore_index=True)
    assert radar_features(sparse) == {"s1_n_obs": 6, "s1_n_frozen": 0, "s1_n_wet": 0}
    late = _radar([(d, -14.0, -8.0) for d in (280, 292, 304, 316)])         # nothing in the summer window
    assert radar_features(late) == {"s1_n_obs": 4, "s1_n_frozen": 0, "s1_n_wet": 0}
    table = radar_feature_table(pd.concat([sparse.assign(field_id="x"), late.assign(field_id="y")]))
    assert list(table.columns) == ["field_id", "year", *RADAR_COLUMNS]
    assert table["s1_n_obs"].tolist() == [6, 4] and table["s1_cut_doy"].isna().all()


# CLI: fitted on training datasets only, never Maryland ------------------------------------------------------

def _write_pair_dataset(root, name, s2_of_landsat, n_fields=50, ndti_pairs=10,
                        doys=(160, 180, 200, 220, 240, 260)):
    rng = np.random.default_rng(3)
    s2_rows, landsat_rows = [], []
    for i in range(n_fields):
        for doy in doys:
            date = _dates([doy])[0].strftime("%Y-%m-%d")
            raw = {index: float(rng.uniform(-0.1, 0.85)) for index in INDICES}
            s2 = {index: s2_of_landsat[index](raw[index]) for index in INDICES}
            if len(s2_rows) >= ndti_pairs:
                s2["ndti"] = np.nan            # leaves too few NDTI pairs to calibrate
            s2_rows.append({"field_id": 1000 + i, "date": date, "year": 2023, "valid_frac": 1.0, **s2,
                            "s2_offset": 1000})
            landsat_rows.append({"field_id": 1000 + i, "date": date, "year": 2023, "valid_frac": 0.95, **raw,
                                 "platform": "landsat-8"})
    for folder, rows in (("s2_series", s2_rows), ("landsat_series", landsat_rows)):
        (root / folder / name).mkdir(parents=True)
        pd.DataFrame(rows).to_csv(root / folder / name / "79_515_2023.csv", index=False)


def test_calibrate_cli_fits_on_training_data_only(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("KERNEL_NO_MANIFEST", raising=False)
    assert load_calibration() is None
    _write_pair_dataset(tmp_path, "quebec_maize_2023",
                        {"ndvi": lambda x: 0.02 + 0.9 * x, "ndmi": lambda x: -0.01 + 1.05 * x, "ndti": lambda x: x})
    # A wildly different Maryland relation: if it leaked into the fit the slopes would move.
    _write_pair_dataset(tmp_path, "barc_2021_2023",
                        {"ndvi": lambda x: 0.5 + 0.2 * x, "ndmi": lambda x: 0.5 + 0.2 * x, "ndti": lambda x: x})

    main(["--calibrate"])
    printed = capsys.readouterr().out
    assert "UNCOMPUTED qc_regions_2023" in printed and "barc" not in printed

    target = tmp_path / "models" / "landsat_s2_calibration.json"
    text = target.read_text(encoding="utf-8")
    assert "NaN" not in text                                # strict JSON
    saved = json.loads(text)
    assert set(saved) == {"method", "window_days", "min_valid", "fitted_on", "indices"}
    assert saved["fitted_on"] == ["quebec_maize_2023"] and saved["window_days"] == 1 and saved["min_valid"] == 0.8
    ndvi, ndmi, ndti = (saved["indices"][index] for index in INDICES)
    assert ndvi["calibrated"] and ndvi["mode"] == "line" and ndvi["n_pairs"] == 300 and ndvi["n_dates"] == 6
    assert ndvi["slope"] == pytest.approx(0.9) and ndvi["intercept"] == pytest.approx(0.02)
    assert ndmi["slope"] == pytest.approx(1.05) and ndmi["intercept"] == pytest.approx(-0.01)
    assert {key: ndti[key] for key in ("mode", "slope", "intercept", "n_pairs", "calibrated")} == {
        "mode": "identity", "slope": 1.0, "intercept": 0.0, "n_pairs": 10, "calibrated": False}
    assert ndti["lodo_slope_min"] is None                    # NaN is written as null: strict JSON
    assert load_calibration() == saved
    assert "derived: kernelag.multisensor" in (tmp_path / "DATA_MANIFEST.tsv").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="test-only"):
        fit_calibration_from(["quebec_maize_2023", "barc_2021_2023"])
    with pytest.raises(SystemExit):
        main(["--calibrate", "--datasets", "barc_2021_2023"])


def test_calibrate_cli_writes_nothing_without_landsat(tmp_path, monkeypatch):
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path))
    with pytest.raises(SystemExit) as stop:
        main(["--calibrate"])
    assert stop.value.code == 1 and load_calibration() is None
