"""Three sensors, one harvest story: Sentinel-2, calibrated Landsat looks, and Sentinel-1 radar.

Why more sensors. The field model (``kernelag.field_model``) reads the harvest from Sentinel-2 alone. In a cloudy
autumn the clear looks around the cut can be weeks apart, so the cut date is uncertain (``cut_gap_days``) and the
drop is blurred. Two other free sensors can fill those gaps:

    Sentinel-2 (MSI, 10-20 m)  the reference; indices as written by ``kernelag.s2_series``.
    Landsat 8/9 (OLI, 30 m)    the same three indices (NDVI, NDMI, NDTI) from similar bands, roughly every 8 days.
                               Extra clear looks shorten the gap around the cut.
    Sentinel-1 (C-band radar)  sees through cloud. VH backscatter comes mostly from the standing canopy, so it
                               falls when the crop is physically cut, not when it browns.

Landsat is calibrated before its looks are mixed with Sentinel-2. The two instruments have slightly different band
responses, pixel sizes and processing, so the same field on the same day gives slightly different index values. The
harvest features hunt for the biggest drop between consecutive looks, so an uncorrected sensor bias between a
Sentinel-2 look and the next Landsat look would masquerade as a greenness drop (or hide a real one). Per index the
correction is fitted on near-simultaneous pairs (same field, within a day, both clear), in one of three modes:
    line      Theil-Sen ``S2 = intercept + slope * Landsat`` (robust to a minority of shadowed or mis-registered pairs),
              used only when the pairs come from at least ``MIN_FIT_DATES`` acquisition dates AND every
              leave-one-date-out slope stays within ``MAX_SLOPE_SPREAD`` of the full slope. Pairs from one date share
              one atmosphere and one crop stage, so a few dates can tilt the line (on the 79_515 training cell three
              dates gave per-date slopes from 0.80 to 1.25) and it would be extrapolated to the green looks it lacks.
    offset    slope 1, intercept median(S2 - Landsat): enough pairs, but not enough dates or a date-unstable slope.
    identity  fewer than ``min_pairs`` pairs: Landsat stays raw and ``calibrated`` is False.
The fit uses the Quebec training datasets only: Maryland is the test set, and fitting anything on it, even a sensor
correction, leaks. A published OLI-to-MSI band adjustment (HLS, Claverie et al. 2018) is the fitting-free alternative;
it needs the bands, which the series do not keep.

Merging guard. A Landsat look a day or two from a Sentinel-2 look can create a "drop" that is really haze on one of
them (a hazy look 2 days after a clear one is not a cut). So a drop of at least ``CROSS_SENSOR_MIN_DROP`` NDVI between
looks from different sensors at most ``CROSS_SENSOR_DAYS`` apart counts only if the next look, within
``CROSS_SENSOR_CONFIRM_DAYS`` (the haze-rebound window of ``kernelag.features.drop_dips``), stays at least halfway down;
otherwise the Landsat look of that pair is dropped. Only Landsat looks are ever removed, so the merged series can only
fall back towards the Sentinel-2-only one.

Radar physics (DOCS/research/sar_harvest.md). VH holds a plateau while the crop stands and falls by roughly 2-7 dB at
the cut, when canopy volume scattering disappears. Silage is cut green, so its optical decline and its radar drop
coincide. Grain corn browns standing for weeks before the combine: across 541 EU grain-maize parcels the radar end of
season came 18.6 days after NDVI's on average [Me21]. So the lag from the optical decline to the radar drop
(``radar_lag_days``) is a cloud-proof form of the dry-down evidence, and VH/VV just before the cut says how much water
the canopy still held. Each radar track (relative orbit) is read on its own: tracks see the field at different
incidence angles and so at different backscatter levels, and a jump from one track to the next is not a cut.

Radar cut rule, amended BEFORE any evaluation (an independent review found the first rule mostly picked up frost,
snow and the season's last look on the Quebec training cell; this amendment uses only sar_harvest.md section 3 and
step 7.3, never labels or Maryland):
    1. frost and snow change backscatter as much as a harvest: looks with a minimum temperature at or below 0 C or
       snow on the ground (``tmin_c``, ``swe_mm`` from ``kernelag.s1_series``) are dropped;
    2. rain raises VV and VH together: a look with at least 5 mm of rain in the 48 h before it (``rain_48h_mm``)
       is skipped too. It may be neither end of a step (before a dry look it fakes a fall, after a cut it hides
       one) nor the confirming look (it lifts a cut field back up); the step then spans the dry looks around it.
       (Written first as "not the before look" only; a descriptive look at the 79_515 training cell showed the
       10-22 look, after 32 mm of rain, failing as the confirmation of early-October cuts, so before any scoring
       the rule was widened to the "never let one flagged look define a step" of sar_harvest.md section 3);
    3. the fall must persist: the next look on the same track must stay at least halfway down. A fall on a track's
       last look cannot be confirmed and does not count, so a field may be "radar-undetected" (NaN);
    4. a fall must be at least 2 dB (Shang's starting rule in sar_harvest.md) to count as a cut;
    5. the track is chosen by evidence first (most usable looks, then the shorter revisit), then by the larger fall.
       Over a 24-day revisit more change piles up between looks than over a 12-day one, so the largest raw fall
       would favour the sparser track and the wider bracket.
Looks with unknown weather are kept: the screen can only remove evidence, never invent it.

Inputs (written by the pullers; join key field_id as text, year as int):
    data/s2_series/<name>/*.csv        field_id, date, year, valid_frac, ndvi, ndmi, ndti
    data/landsat_series/<name>/*.csv   field_id, date, year, valid_frac, ndvi, ndmi, ndti, platform (raw Landsat)
    data/s1_series/<name>/*.csv        field_id, date (local solar), year, valid_frac, vv_db, vh_db, relative_orbit,
                                       orbit_state, platform, and (optional) look weather tmin_c, rain_48h_mm,
                                       swe_mm; GRD sigma-nought from kernelag.s1_series (no account needed)
Outputs:
    data/models/landsat_s2_calibration.json   per-index correction (line, offset or identity), ``--calibrate``
    multisensor_features(...)                 per field-year: the ``kernelag.features`` evidence on the merged
                                              optical looks, look counts per sensor, radar features, and the
                                              optical-radar fusion columns (radar_lag_days, brackets_overlap,
                                              fused_cut_gap_days)

Run: ``python -m kernelag.multisensor --calibrate [--datasets quebec_maize_2023 qc_regions_2023]``
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable

import numpy as np
import pandas as pd

from kernelag.features import build_features
from kernelag.field_model import load_series
from kernelag.paths import data_dir, record_in_manifest

INDICES = ("ndvi", "ndmi", "ndti")
OPTICAL_COLUMNS = ["field_id", "date", "year", "valid_frac", *INDICES, "sensor"]

# Pre-registered radar model features, fixed before any evaluation.
RADAR_FEATURES = ["radar_lag_days", "s1_vh_drop_db", "s1_vhvv_before_db"]
RADAR_COLUMNS = ["s1_n_obs", "s1_n_frozen", "s1_n_wet", "s1_cut_doy", "s1_cut_gap_days", "s1_vh_drop_db", "s1_fade_db",
                 "s1_vhvv_before_db", "s1_orbit"]
FUSION_COLUMNS = ["radar_lag_days", "brackets_overlap", "fused_cut_gap_days"]

CALIBRATION_DATASETS = ("quebec_maize_2023", "qc_regions_2023")   # training data only
TEST_ONLY_DATASETS = ("barc_2021_2023",)                         # Maryland: scored, never fitted on
CALIBRATION_FILE = "landsat_s2_calibration.json"
USABLE_VALID = 0.5        # the clear-sky share kernel_features itself requires of a look
MAX_FIT_PAIRS = 2000      # Theil-Sen builds every pairwise slope (n^2 memory); a seeded subsample keeps it small
MIN_FIT_DATES = 5         # a fitted line needs pairs from at least this many acquisition dates
MAX_SLOPE_SPREAD = 0.05   # and every leave-one-date-out slope within this of the full slope; else offset only
CROSS_SENSOR_DAYS = 3     # looks from different sensors this close: a drop between them must be confirmed
CROSS_SENSOR_MIN_DROP = 0.05   # about twice the calibrated Landsat-S2 residual spread; smaller steps are noise
CROSS_SENSOR_CONFIRM_DAYS = 20  # the confirming look must come this soon: drop_dips' haze-rebound window
FROZEN_TMIN_C = 0.0       # sar_harvest.md section 3: drop looks with Tmin <= 0 C or snow on the ground
WET_RAIN_MM = 5.0         # sar_harvest.md step 7.3: rain in the 48 h before a look; the starting threshold
MIN_CUT_DROP_DB = 2.0     # sar_harvest.md: Shang's rule, a VH fall of more than 2 dB


def _is_test_only(name: str) -> bool:
    return name in TEST_ONLY_DATASETS or name.startswith("barc")


def _normalise_dates(dates: pd.Series) -> pd.Series:
    """Calendar dates at midnight, no time zone, so looks from different files share one day key."""
    parsed = pd.to_datetime(dates)
    if parsed.dt.tz is not None:
        parsed = parsed.dt.tz_localize(None)
    return parsed.dt.normalize()


def load_landsat(name: str) -> pd.DataFrame | None:
    """Raw Landsat looks for one dataset (``data/landsat_series/<name>/``), or None when there are none."""
    folder = data_dir() / "landsat_series" / name
    if not folder.is_dir() or not any(folder.glob("*.csv")):
        return None
    landsat = load_series(folder)   # same reader as Sentinel-2: text ids, dates at midnight, one look per day
    return landsat if len(landsat) else None


def load_radar(name: str) -> pd.DataFrame | None:
    """Sentinel-1 looks for one dataset (``data/s1_series/<name>/``), or None when there are none."""
    folder = data_dir() / "s1_series" / name
    files = sorted(folder.glob("*.csv")) if folder.is_dir() else []
    if not files:
        return None
    s1 = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    if s1.empty:
        return None
    s1["field_id"] = s1["field_id"].astype(str)
    s1["date"] = _normalise_dates(s1["date"])
    if "tmin_c" not in s1 or s1["tmin_c"].isna().all():
        # An older series (or a failed weather request): frost and rain cannot be screened, say so loudly.
        print(f"WARNING {folder}: no look weather (tmin_c, rain_48h_mm, swe_mm); the frost and rain screen is off")
    # Two passes can share a date on different tracks; only the same track twice on one date is a duplicate.
    s1 = s1.sort_values("valid_frac", ascending=False, kind="mergesort")
    s1 = s1.drop_duplicates(["field_id", "year", "date", "relative_orbit"])
    return s1.sort_values(["field_id", "year", "date", "relative_orbit"]).reset_index(drop=True)


def _clear_looks(table: pd.DataFrame, sensor: str, min_valid: float) -> pd.DataFrame:
    """Looks with at least ``min_valid`` clear share, renamed with a sensor suffix for pairing."""
    clear = table[table["valid_frac"] >= min_valid]
    out = pd.DataFrame({
        "field_id": clear["field_id"].astype(str),
        "year": clear["year"].astype(int),
        f"date_{sensor}": _normalise_dates(clear["date"]).astype("datetime64[ns]"),
    })
    for index in INDICES:
        out[f"{index}_{sensor}"] = clear[index].astype(float) if index in clear else np.nan
    return out.dropna(subset=[f"date_{sensor}"])


def match_pairs(s2: pd.DataFrame, landsat: pd.DataFrame, max_days: int = 1, min_valid: float = 0.8) -> pd.DataFrame:
    """Near-simultaneous looks: for each clear Landsat look, the nearest clear S2 look of the same field-year.

    Only pairs at most ``max_days`` apart count, so the crop itself has not changed between the two looks.
    """
    columns = ["field_id", "year", "date_s2", "date_landsat"]
    columns += [f"{index}_{sensor}" for index in INDICES for sensor in ("s2", "landsat")]
    left = _clear_looks(landsat, "landsat", min_valid).sort_values("date_landsat")
    right = _clear_looks(s2, "s2", min_valid).sort_values("date_s2")
    if left.empty or right.empty:
        return pd.DataFrame(columns=columns)
    pairs = pd.merge_asof(left, right, left_on="date_landsat", right_on="date_s2", by=["field_id", "year"],
                          direction="nearest", tolerance=pd.Timedelta(days=max_days))
    pairs = pairs.dropna(subset=["date_s2"])
    return pairs[columns].sort_values(["field_id", "year", "date_landsat"]).reset_index(drop=True)


def _mad(values: np.ndarray) -> float:
    """Median absolute deviation (unscaled); NaN with no values."""
    return float(np.median(np.abs(values - np.median(values)))) if len(values) else float("nan")


def _theil(x: np.ndarray, y: np.ndarray, max_fit_pairs: int) -> tuple[float, float]:
    """Theil-Sen slope and intercept, on a seeded subsample above ``max_fit_pairs`` pairs (n^2 memory)."""
    from scipy.stats import theilslopes

    if len(x) > max_fit_pairs:
        pick = np.random.default_rng(0).choice(len(x), max_fit_pairs, replace=False)
        x, y = x[pick], y[pick]
    # "joint" takes the intercept as median(y - slope * x): the default median(y) - slope * median(x)
    # is dragged by outliers that sit on one side of the line.
    slope, intercept = theilslopes(y, x, method="joint")[:2]
    return float(slope), float(intercept)


def fit_calibration(pairs: pd.DataFrame, min_pairs: int = 30, max_fit_pairs: int = MAX_FIT_PAIRS,
                    min_dates: int = MIN_FIT_DATES, max_slope_spread: float = MAX_SLOPE_SPREAD) -> dict:
    """Per index, the Landsat-to-Sentinel-2 correction in the best mode the evidence supports (see module notes).

    Returns {index: {"mode", "slope", "intercept", "n_pairs", "n_dates", "x_min", "x_p05", "x_p95", "x_max",
    "lodo_slope_min", "lodo_slope_max", "residual_mad", "calibrated"}}.
        identity  fewer than ``min_pairs`` finite pairs: slope 1, intercept 0, ``calibrated`` False;
        offset    slope 1, intercept median(S2 - Landsat);
        line      Theil-Sen, only with pairs from ``min_dates`` or more dates (column ``date_landsat``; without it
                  the dates are unknown and the line is never trusted) and every leave-one-date-out slope within
                  ``max_slope_spread`` of the full one.
    The x range of the pairs is stored so a reader can see where the correction was actually measured.
    """
    dates_all = pd.to_datetime(pairs["date_landsat"]) if "date_landsat" in pairs else None
    fits = {}
    for index in INDICES:
        x_col, y_col = f"{index}_landsat", f"{index}_s2"
        if x_col in pairs and y_col in pairs:
            x = pd.to_numeric(pairs[x_col], errors="coerce").to_numpy(float)
            y = pd.to_numeric(pairs[y_col], errors="coerce").to_numpy(float)
            ok = np.isfinite(x) & np.isfinite(y)
            x, y = x[ok], y[ok]
            dates = dates_all.to_numpy()[ok] if dates_all is not None else None
        else:
            x = y = np.array([], dtype=float)
            dates = None
        n = len(x)
        day_keys = np.unique(dates) if dates is not None and n else np.array([])
        fit = {"mode": "identity", "slope": 1.0, "intercept": 0.0, "n_pairs": int(n), "n_dates": len(day_keys),
               "x_min": float("nan"), "x_p05": float("nan"), "x_p95": float("nan"), "x_max": float("nan"),
               "lodo_slope_min": float("nan"), "lodo_slope_max": float("nan"), "residual_mad": _mad(y - x),
               "calibrated": False}
        if n:
            fit.update(x_min=float(x.min()), x_p05=float(np.quantile(x, 0.05)), x_p95=float(np.quantile(x, 0.95)),
                       x_max=float(x.max()))
        if n < min_pairs:
            fits[index] = fit
            continue
        offset = float(np.median(y - x))
        fit.update(mode="offset", intercept=offset, calibrated=True, residual_mad=_mad(y - x - offset))
        if len(day_keys) >= min_dates and np.unique(x).size >= 2:
            slope, intercept = _theil(x, y, max_fit_pairs)
            # Leave one date out: if dropping any single date moves the slope, the line is one atmosphere's.
            lodo = [_theil(x[dates != day], y[dates != day], max_fit_pairs)[0] for day in day_keys]
            fit.update(lodo_slope_min=float(np.min(lodo)), lodo_slope_max=float(np.max(lodo)))
            stable = np.isfinite(lodo).all() and float(np.max(np.abs(np.subtract(lodo, slope)))) <= max_slope_spread
            if np.isfinite(slope) and np.isfinite(intercept) and stable:
                fit.update(mode="line", slope=slope, intercept=intercept,
                           residual_mad=_mad(y - (intercept + slope * x)))
        fits[index] = fit
    return fits


def fit_calibration_from(names: Iterable[str], max_days: int = 1, min_valid: float = 0.8,
                         min_pairs: int = 30) -> dict:
    """Calibration fitted on the named TRAINING datasets that have both S2 and Landsat series.

    Datasets lacking either series are skipped with an UNCOMPUTED line. Maryland is refused outright.
    """
    names = list(names)
    refused = [name for name in names if _is_test_only(name)]
    if refused:
        raise ValueError(f"refusing to calibrate on test-only dataset(s) {refused}: Maryland is never fitted on")
    found, used = [], []
    for name in names:
        s2_dir = data_dir() / "s2_series" / name
        landsat = load_landsat(name)
        if landsat is None or not s2_dir.is_dir() or not any(s2_dir.glob("*.csv")):
            print(f"UNCOMPUTED {name}: needs both data/s2_series/{name} and data/landsat_series/{name}")
            continue
        pairs = match_pairs(load_series(s2_dir), landsat, max_days, min_valid)
        print(f"{name}: {len(pairs)} Sentinel-2/Landsat pairs within {max_days} day(s), both clear >= {min_valid}")
        if len(pairs):
            found.append(pairs)
            used.append(name)
    pairs = pd.concat(found, ignore_index=True) if found else pd.DataFrame()
    return {
        "method": ("per index: Theil-Sen line (scipy.stats.theilslopes, intercept median(y - slope*x)) of "
                   f"y = Sentinel-2 on x = Landsat only with pairs from >= {MIN_FIT_DATES} dates and every "
                   f"leave-one-date-out slope within {MAX_SLOPE_SPREAD} of the full slope (fitted on a seeded "
                   f"subsample of at most {MAX_FIT_PAIRS} pairs); otherwise offset only (slope 1, intercept "
                   f"median(S2 - Landsat)); identity below {min_pairs} pairs"),
        "window_days": max_days,
        "min_valid": min_valid,
        "fitted_on": used,
        "indices": fit_calibration(pairs, min_pairs),
    }


def _jsonable(value):
    """Plain JSON types; NaN becomes null because strict JSON has no NaN."""
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def load_calibration() -> dict | None:
    """The saved calibration (``data/models/landsat_s2_calibration.json``), or None if never fitted."""
    path = data_dir() / "models" / CALIBRATION_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def apply_calibration(landsat: pd.DataFrame, calibration: dict | None) -> pd.DataFrame:
    """Landsat indices mapped onto the Sentinel-2 scale where a correction (line or offset) exists; others unchanged.

    Accepts the saved file's dict (with "indices") or the bare per-index dict from ``fit_calibration``.
    """
    out = landsat.copy()
    if not calibration:
        return out
    fits = calibration.get("indices", calibration)
    for index in INDICES:
        fit = fits.get(index) or {}
        if index in out and fit.get("calibrated"):
            # Normalised-difference indices live in [-1, 1]; the line must not push a value outside.
            out[index] = (fit["intercept"] + fit["slope"] * out[index].astype(float)).clip(-1.0, 1.0)
    return out


def _optical_looks(table: pd.DataFrame, sensor: str) -> pd.DataFrame:
    """One sensor's looks in the shared optical layout."""
    looks = pd.DataFrame({
        "field_id": table["field_id"].astype(str),
        "date": _normalise_dates(table["date"]),
        "year": table["year"].astype(int),
        "valid_frac": table["valid_frac"].astype(float),
    })
    for index in INDICES:
        looks[index] = table[index].astype(float) if index in table else np.nan
    looks["sensor"] = sensor
    return looks.reset_index(drop=True)


def optical_series(s2: pd.DataFrame, landsat: pd.DataFrame | None = None, calibration: dict | None = None,
                   min_valid: float = USABLE_VALID) -> pd.DataFrame:
    """Sentinel-2 and calibrated Landsat looks on one timeline, with at most one look per field and day.

    When both sensors saw a field on the same day the kept look is, in order: a usable one (clear share at
    least ``min_valid`` and an NDVI value), then Sentinel-2 (the reference scale), then the clearer one.
    Without Landsat the Sentinel-2 rows come back unchanged, so features match the Sentinel-2-only path.
    """
    s2_looks = _optical_looks(s2, "s2")
    if landsat is None:
        return s2_looks
    looks = pd.concat([s2_looks, _optical_looks(apply_calibration(landsat, calibration), "landsat")],
                      ignore_index=True)
    looks = looks.assign(_usable=(looks["valid_frac"] >= min_valid) & looks["ndvi"].notna(),
                         _s2=looks["sensor"] == "s2")
    looks = looks.sort_values(["field_id", "year", "date", "_usable", "_s2", "valid_frac"],
                              ascending=[True, True, True, False, False, False], kind="mergesort")
    looks = looks.drop_duplicates(["field_id", "year", "date"]).drop(columns=["_usable", "_s2"])
    return guard_cross_sensor(looks[OPTICAL_COLUMNS].reset_index(drop=True), min_valid)


def guard_cross_sensor(looks: pd.DataFrame, min_valid: float = USABLE_VALID, max_days: int = CROSS_SENSOR_DAYS,
                       min_drop: float = CROSS_SENSOR_MIN_DROP,
                       confirm_days: int = CROSS_SENSOR_CONFIRM_DAYS) -> pd.DataFrame:
    """Drop Landsat looks whose short cross-sensor NDVI drop is not confirmed by the next look (module notes).

    Among usable looks of one field-year, a fall of at least ``min_drop`` between consecutive looks from different
    sensors at most ``max_days`` apart counts only if the next usable look, at most ``confirm_days`` later, stays at
    least halfway down. A look weeks later cannot tell haze from a cut, so it does not confirm. When the fall is not
    confirmed the Landsat look of the pair goes, so it cannot become the "cut". Sentinel-2 looks are never removed.
    """
    usable = looks[(looks["valid_frac"] >= min_valid) & looks["ndvi"].notna()]
    usable = usable.sort_values(["field_id", "year", "date"], kind="mergesort")
    group = usable.groupby(["field_id", "year"], sort=False)
    before = group[["date", "ndvi", "sensor"]].shift(1)
    after = group[["date", "ndvi"]].shift(-1)
    fall = before["ndvi"] - usable["ndvi"]
    suspect = ((before["sensor"].notna()) & (before["sensor"] != usable["sensor"])
               & ((usable["date"] - before["date"]).dt.days <= max_days) & (fall >= min_drop))
    # NaN (no next look) compares False, so an unconfirmable fall is treated as unconfirmed.
    confirmed = ((after["ndvi"] <= (before["ndvi"] + usable["ndvi"]) / 2)
                 & ((after["date"] - usable["date"]).dt.days <= confirm_days))
    bad = suspect & ~confirmed
    if not bad.any():
        return looks
    # The pair is (previous look, this look); drop whichever of the two is Landsat.
    position = pd.Series(np.arange(len(usable)), index=usable.index)
    pair_landsat = np.where(usable.loc[bad, "sensor"] == "landsat", position[bad], position[bad] - 1)
    drop_index = usable.index[pair_landsat]
    return looks.drop(index=drop_index).reset_index(drop=True)


def _weather_flags(s: pd.DataFrame, frozen_tmin_c: float, wet_rain_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """(frozen, wet) per look from the optional weather columns; unknown weather flags nothing."""
    def column(name: str) -> np.ndarray:
        if name not in s:
            return np.full(len(s), np.nan)
        return pd.to_numeric(s[name], errors="coerce").to_numpy(float)

    with np.errstate(invalid="ignore"):
        frozen = (column("tmin_c") <= frozen_tmin_c) | (column("swe_mm") > 0)
        wet = column("rain_48h_mm") >= wet_rain_mm
    return frozen, wet


def radar_features(one_field_year_s1: pd.DataFrame, min_valid: float = 0.5, min_looks: int = 4,
                   peak_window: tuple[int, int] = (150, 270), season_end_doy: int = 334,
                   frozen_tmin_c: float = FROZEN_TMIN_C, wet_rain_mm: float = WET_RAIN_MM,
                   min_drop_db: float = MIN_CUT_DROP_DB) -> dict:
    """Radar cut evidence for one field-year. Only the look counts when no track shows a confirmed cut.

    Frozen, snowy and rain-wet looks are set aside first. Per track: the VH peak in the summer window, then the
    biggest look-to-look VH fall after it that is at least ``min_drop_db`` and is confirmed by the next look on the
    track staying at least halfway down (module notes, steps 1-5). Falls are
    taken within one track only, because tracks sit at different backscatter levels. The track with the most usable
    looks wins, then the one with the shorter median revisit, then the bigger fall.
    """
    s = one_field_year_s1
    vh = pd.to_numeric(s["vh_db"], errors="coerce").to_numpy(float)
    s = s[(s["valid_frac"] >= min_valid).to_numpy() & np.isfinite(vh)]
    frozen, wet = _weather_flags(s, frozen_tmin_c, wet_rain_mm)
    wet &= ~frozen
    s = s.assign(doy=pd.to_datetime(s["date"]).dt.day_of_year.astype(int))[~(frozen | wet)]
    if "vv_db" not in s:
        s = s.assign(vv_db=np.nan)
    f: dict = {"s1_n_obs": len(s), "s1_n_frozen": int(frozen.sum()), "s1_n_wet": int(wet.sum())}

    candidates = []
    for orbit, track in s.groupby("relative_orbit", sort=True):
        track = track.sort_values(["doy", "valid_frac"], ascending=[True, False]).drop_duplicates("doy")
        if len(track) < min_looks:
            continue
        doy = track["doy"].to_numpy()
        vh_db = pd.to_numeric(track["vh_db"], errors="coerce").to_numpy(float)
        vv_db = pd.to_numeric(track["vv_db"], errors="coerce").to_numpy(float)
        in_window = np.flatnonzero((doy >= peak_window[0]) & (doy <= peak_window[1]))
        if in_window.size == 0:
            continue
        ip = int(in_window[np.argmax(vh_db[in_window])])
        best_k = None
        for k in range(ip + 1, len(doy)):        # the step from look k - 1 to look k
            if doy[k] > season_end_doy:
                break
            drop = vh_db[k - 1] - vh_db[k]
            confirmed = k + 1 < len(doy) and vh_db[k + 1] <= (vh_db[k - 1] + vh_db[k]) / 2
            if drop >= min_drop_db and confirmed and (
                    best_k is None or drop > vh_db[best_k - 1] - vh_db[best_k]):
                best_k = k
        if best_k is None:
            continue
        k = best_k
        candidates.append({
            "orbit": orbit, "cut_doy": int(doy[k]), "gap": int(doy[k] - doy[k - 1]),
            "drop": float(vh_db[k - 1] - vh_db[k]), "vh_before": float(vh_db[k - 1]),
            "vv_before": float(vv_db[k - 1]), "peak_vh": float(vh_db[ip]),
            "n_looks": len(track), "revisit": float(np.median(np.diff(doy))),
        })
    if not candidates:
        return f
    best = min(candidates, key=lambda c: (-c["n_looks"], c["revisit"], -c["drop"]))
    orbit = best["orbit"]
    f.update(
        s1_cut_doy=best["cut_doy"],
        s1_cut_gap_days=best["gap"],
        s1_vh_drop_db=best["drop"],
        s1_fade_db=best["peak_vh"] - best["vh_before"],         # VH lost while still standing
        s1_vhvv_before_db=best["vh_before"] - best["vv_before"],  # cross-ratio: canopy water just before the cut
        s1_orbit=int(orbit) if isinstance(orbit, int | float | np.number) and np.isfinite(orbit) else orbit,
    )
    return f


def radar_feature_table(s1: pd.DataFrame | None, **kwargs) -> pd.DataFrame:
    """One row of radar features per ``field_id`` and ``year``; keyword arguments go to ``radar_features``."""
    columns = ["field_id", "year", *RADAR_COLUMNS]
    if s1 is None or len(s1) == 0:
        return pd.DataFrame(columns=columns)
    s1 = s1.assign(field_id=s1["field_id"].astype(str))
    rows = [
        {"field_id": field_id, "year": int(year), **radar_features(group, **kwargs)}
        for (field_id, year), group in s1.groupby(["field_id", "year"])
    ]
    return pd.DataFrame(rows).reindex(columns=columns)


def fuse(optical_features: pd.DataFrame, radar_table: pd.DataFrame) -> pd.DataFrame:
    """Optical features with radar features joined on, plus how the two cut dates agree.

    Each sensor brackets its cut as the half-open interval (last look before, first look after]. Two brackets
    overlap only if they share time: touching end to start is no overlap. The overlap, when there is one, is a
    tighter fused bracket. Missing evidence on either side leaves the fusion columns NaN.
    """
    left = optical_features.assign(field_id=optical_features["field_id"].astype(str),
                                   year=optical_features["year"].astype(int))
    right = radar_table.assign(field_id=radar_table["field_id"].astype(str), year=radar_table["year"].astype(int))
    for column in RADAR_COLUMNS:
        if column not in right:
            right[column] = np.nan
    out = left.merge(right[["field_id", "year", *RADAR_COLUMNS]], on=["field_id", "year"], how="left")

    def number(column: str) -> pd.Series:
        if column not in out:
            return pd.Series(np.nan, index=out.index)
        return pd.to_numeric(out[column], errors="coerce").astype(float)

    cut, gap = number("cut_doy"), number("cut_gap_days")
    s1_cut, s1_gap = number("s1_cut_doy"), number("s1_cut_gap_days")
    out["radar_lag_days"] = s1_cut - number("decline_doy")
    start = np.maximum(cut - gap, s1_cut - s1_gap)   # NaN on either side stays NaN
    end = np.minimum(cut, s1_cut)
    known = (start.notna() & end.notna()).to_numpy()
    overlap = (start < end).to_numpy()
    out["brackets_overlap"] = np.where(known, overlap.astype(float), np.nan)
    out["fused_cut_gap_days"] = np.where(known & overlap, end - start, np.nan)
    return out


def _look_counts(optical: pd.DataFrame, min_valid: float = USABLE_VALID) -> pd.DataFrame:
    """Usable looks per field-year from each sensor, after the one-look-per-day merge."""
    usable = (optical["valid_frac"] >= min_valid) & optical["ndvi"].notna()
    counts = optical.assign(n_looks_s2=usable & (optical["sensor"] == "s2"),
                            n_looks_landsat=usable & (optical["sensor"] == "landsat"))
    return counts.groupby(["field_id", "year"], as_index=False)[["n_looks_s2", "n_looks_landsat"]].sum()


def multisensor_features(s2: pd.DataFrame, landsat: pd.DataFrame | None = None, s1: pd.DataFrame | None = None,
                         calibration: dict | None = None, only_s2_field_years: bool = True) -> pd.DataFrame:
    """Per field-year evidence from every sensor given.

    The ``kernelag.features`` evidence is computed on the merged optical looks, so it reads exactly like the
    Sentinel-2-only features when no Landsat is given. ``n_looks_landsat`` is NaN when Landsat was not given
    (not looked for), 0 when it was given but had no usable look. Radar and fusion columns appear when ``s1``
    is given. With ``only_s2_field_years`` (the default) the rows are exactly the field-years of the Sentinel-2
    input, so a Sentinel-2-only model and a merged one are trained and scored on the same fields.
    """
    optical = optical_series(s2, landsat, calibration)
    features = build_features(optical)
    if features.empty:
        features = pd.DataFrame(columns=["field_id", "year"])
    if only_s2_field_years and len(features):
        keys = pd.DataFrame({"field_id": s2["field_id"].astype(str), "year": s2["year"].astype(int)})
        features = features.merge(keys.drop_duplicates(), on=["field_id", "year"], how="inner")
    features = features.merge(_look_counts(optical), on=["field_id", "year"], how="left")
    if landsat is None:
        features["n_looks_landsat"] = np.nan
    if s1 is not None:
        features = fuse(features, radar_feature_table(s1))
    return features


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--calibrate", action="store_true", help="fit the Landsat-to-Sentinel-2 calibration")
    parser.add_argument("--datasets", nargs="+", default=list(CALIBRATION_DATASETS),
                        help="training datasets to fit on (never the Maryland test set)")
    args = parser.parse_args(argv)
    if not args.calibrate:
        parser.print_help()
        return
    try:
        calibration = fit_calibration_from(args.datasets)
    except ValueError as error:
        parser.error(str(error))
    if not calibration["fitted_on"]:
        print("UNCOMPUTED: no training dataset has Sentinel-2/Landsat pairs; no calibration written")
        raise SystemExit(1)

    target = data_dir() / "models" / CALIBRATION_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_jsonable(calibration), indent=2) + "\n", encoding="utf-8", newline="\n")
    record_in_manifest(target, "derived: kernelag.multisensor")

    pd.set_option("display.width", 200)
    print(f"fitted on {calibration['fitted_on']}")
    print(pd.DataFrame(calibration["indices"]).T.to_string())
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
