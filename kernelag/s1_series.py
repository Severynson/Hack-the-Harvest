"""Per-field, per-pass Sentinel-1 radar backscatter series from Microsoft Planetary Computer, with look weather.

Radar sees through cloud, so every pass counts; with Sentinel-2 the cloudy days are lost. For each field and each
satellite pass this gives the field median of the two bands, in decibels:
    vv_db  co-polarised: soil moisture, surface roughness and stalk structure
    vh_db  cross-polarised: volume scattering in the canopy; it falls when the crop is cut
plus ``valid_frac``, the share of the field's pixels the pass covered with valid data, and the pass geometry
(``relative_orbit``, ``orbit_state``, ``platform``). Backscatter depends on the viewing angle, so compare a field with
itself on one relative orbit before comparing across orbits. Notes: DOCS/research/data_access.md, sar_harvest.md.

Source (no account). The default collection is ``sentinel-1-grd`` (Level-1 Ground Range Detected), which Planetary
Computer serves without an account. Its files stay in radar geometry (rows are azimuth lines, columns ground-range
samples) with ground control points (GCPs), and hold uncalibrated amplitudes (DN). Per field and pass:
    1. the field outline is mapped into the image through the scene's GCPs (thin-plate spline);
    2. the median of DN^2 over the field's valid pixels is taken (DN 0 is no data: outside the swath, border noise);
    3. it is calibrated with the product's own lookup tables at the field centre, sigma0 = (DN^2 - noise) / A_sigma^2
       (ESA radiometric calibration with thermal-noise removal), then converted to dB.
So these are sigma-nought values on the ellipsoid, not terrain-flattened gamma-nought; on flat cropland the
difference is a per-track offset (sar_harvest.md section 3). Geolocation uses the GCP heights, which sample the terrain
every 13-19 km: a field that sits h metres above or below that interpolated height is displaced by about
h / tan(incidence) in range (about 1.4 h at 35 degrees). The 10 m inner buffer absorbs small shifts only.

``sentinel-1-rtc`` (terrain-corrected gamma-nought) is NOT read by default: its collection metadata says "A Planetary
Computer account is required to retrieve SAS tokens to read the RTC data" (msft:requires_account). It is used only with
``--collection sentinel-1-rtc`` AND a configured Planetary Computer subscription key (``PC_SDK_SUBSCRIPTION_KEY``),
and it writes to ``data/s1_rtc_series/`` so gamma-nought and sigma-nought never share a file.

Weather per look. Frost and snow drop VV and VH by 4-6 dB and rain raises both, as much as a harvest moves them
(sar_harvest.md section 3), so every row carries the day's weather at the cell centre from Daymet (daily, 1 km, ORNL
DAAC single-pixel API, no account): ``tmin_c`` (daily minimum air temperature), ``swe_mm`` (snow water equivalent on
the ground) and ``rain_48h_mm`` (precipitation in the two days before the pass: the pass day and the day before for an
evening pass, the two previous days for a morning pass). If the weather request fails these stay NaN, never guessed.
``kernelag.multisensor`` drops frozen or snowy looks and never lets a rain-wet look stand before a step.

``date`` is the local solar date at the cell centre, not the UTC date: an evening ascending pass in the western US is
already the next day in UTC. A morning and an evening pass can share one solar date; both rows are kept (use
``load_s1_series``, which keeps them, not ``field_model.load_series``, which does not).

Fields are grouped into the same square cells as the Sentinel-2 pull and each cell-year is cached as its own file
under ``data/s1_series/<fields file>/``, so a stopped run resumes where it left off.

Output columns: field_id, date, year, valid_frac, vv_db, vh_db, relative_orbit, orbit_state, platform, tmin_c,
rain_48h_mm, swe_mm

Run (one cell): ``python -m kernelag.s1_series --fields data/labels/barc_2021_2023.parquet --only-cells=34_432``
"""

from __future__ import annotations

import argparse
import os
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag import s2_series
from kernelag.paths import data_dir, record_in_manifest
from kernelag.s2_series import (
    SEASON,
    STAC_URL,
    assign_cells,
    densest_cells,
    pull_cells_in_parallel,
)

COLLECTION = "sentinel-1-grd"          # default: Planetary Computer serves it with no account
RTC_COLLECTION = "sentinel-1-rtc"      # needs a Planetary Computer account key; opt-in only
COLLECTIONS = (COLLECTION, RTC_COLLECTION)
FOLDERS = {COLLECTION: "s1_series", RTC_COLLECTION: "s1_rtc_series"}   # never mix sigma0 and gamma0 in one file
WEATHER_URL = "https://daymet.ornl.gov/single-pixel/api/data"
SOURCE_URLS = {
    COLLECTION: f"https://planetarycomputer.microsoft.com/dataset/sentinel-1-grd; weather: {WEATHER_URL}",
    RTC_COLLECTION: f"https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc; weather: {WEATHER_URL}",
}
SOURCE_URL = SOURCE_URLS[COLLECTION]
BANDS = ["vv", "vh"]
NODATA = -32768.0             # fill value of the RTC files; also what odc-stac writes outside a scene
RESOLUTION_M = 10             # native pixel spacing of both products
INNER_BUFFER_M = 10           # shrink fields by one pixel so roads and tree lines do not mix in
PASSES_PER_BATCH = 8          # passes fetched together; about 8 MB per pass for a full 10 km cell
PASS_THREADS = 8              # GRD: one thread per pass; each reads two small windows and four XML tables
MAX_SHIFT_PX = 15             # GRD range registration searched over +-150 m (terrain 100 m off at 35 degrees)
MIN_SCORE_PX = 20             # fields smaller than this say little about where their edges are
READ_THREADS = int(os.environ.get("KERNEL_READ_THREADS", "32"))   # RTC reads wait on the network
READ_ATTEMPTS = 3             # tries per batch of passes before the area-year is given up
RETRY_WAIT_S = 20             # wait before the second try; twice that before the third
HTTP_TIMEOUT_S = 120
WEATHER_ATTEMPTS = 4          # Daymet requests per cell-year before the weather screen is switched off
WEATHER_WAIT_S = 15           # wait before the second try; twice that before the third, and so on
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "3", "GDAL_HTTP_RETRY_DELAY": "2"}
WEATHER_COLUMNS = ["tmin_c", "rain_48h_mm", "swe_mm"]
COLUMNS = ["field_id", "date", "year", "valid_frac", "vv_db", "vh_db", "relative_orbit", "orbit_state", "platform",
           *WEATHER_COLUMNS, "range_shift_px"]


def to_db(linear):
    """Linear power to decibels. Zero, negative and missing values give NaN, never a made-up floor."""
    linear = np.asarray(linear, dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(linear > 0, 10.0 * np.log10(np.where(linear > 0, linear, 1.0)), np.nan)


def valid_mask(values) -> np.ndarray:
    """True where a backscatter pixel holds a measurement: finite, positive and not the nodata fill."""
    values = np.asarray(values)
    with np.errstate(invalid="ignore"):
        return np.isfinite(values) & (values > 0) & (values != NODATA)


def solar_date(utc_timestamp, lon: float) -> pd.Timestamp:
    """Local solar date of a UTC time at longitude ``lon`` (degrees east): UTC plus lon/15 hours, at midnight.

    Sentinel-1 passes near 6 am and 6 pm local time, so the UTC date is wrong by a day for evening
    passes in the western US (01:50 UTC at 120 W is 17:50 the day before).
    """
    return _solar_time(utc_timestamp, lon).normalize()


def _solar_time(utc_timestamp, lon: float) -> pd.Timestamp:
    stamp = pd.Timestamp(utc_timestamp)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("UTC").tz_localize(None)
    return stamp + pd.Timedelta(hours=lon / 15.0)


def pass_key(item) -> tuple:
    """One satellite pass: adjacent slices of one datatake share platform and absolute orbit.

    Absolute orbit numbers are counted per satellite, so the platform is part of the key. An item
    without an orbit number stays a pass of its own rather than being merged by guess.
    """
    props = item.properties
    orbit = props.get("sat:absolute_orbit")
    return (props.get("platform", ""), int(orbit) if orbit is not None else f"item:{item.id}")


def group_passes(items) -> list[list]:
    """Items grouped into passes, passes in time order. Items lacking either band are left out."""
    passes: dict[tuple, list] = {}
    for item in items:
        if all(band in item.assets for band in BANDS):
            passes.setdefault(pass_key(item), []).append(item)
    return sorted(passes.values(), key=lambda group: min(item.datetime for item in group))


def _zone_medians(vv, vh, zones) -> pd.DataFrame:
    """Per zone (1-based field position, 0 = outside): pixel count, valid share and the medians of valid pixels.

    A pixel counts only when both bands hold a measurement, so VV and VH always describe the same ground.
    Returns zone, n_px, valid_frac, vv, vh (linear) for zones with at least one valid pixel.
    """
    zones = np.asarray(zones).ravel()
    in_field = zones > 0
    vv = np.asarray(vv, dtype="float64").ravel()[in_field]
    vh = np.asarray(vh, dtype="float64").ravel()[in_field]
    pixels = pd.DataFrame({"zone": zones[in_field], "valid": valid_mask(vv) & valid_mask(vh), "vv": vv, "vh": vh})
    grouped = pixels.groupby("zone")["valid"]
    stats = pd.concat([grouped.size().rename("n_px"), grouped.mean().rename("valid_frac")], axis=1)
    median = pixels[pixels["valid"]].groupby("zone")[["vv", "vh"]].median()
    return pd.concat([stats, median], axis=1).dropna(subset=["vv"]).reset_index()


def pass_field_medians(vv, vh, zones, field_ids) -> pd.DataFrame:
    """Field medians of one pass of linear backscatter. ``zones`` numbers each pixel by field position.

    Returns field_id, valid_frac, vv_db, vh_db for fields with at least one valid pixel. The median is
    taken in linear power and then converted: the dB transform is monotone, so this equals the median
    of dB values (up to averaging the two middle pixels when the count is even).
    """
    out = _zone_medians(vv, vh, zones)
    out["field_id"] = np.asarray(field_ids)[out["zone"].to_numpy() - 1]
    out["vv_db"], out["vh_db"] = to_db(out["vv"]), to_db(out["vh"])
    return out[["field_id", "valid_frac", "vv_db", "vh_db"]]


# --- Sentinel-1 GRD radiometric calibration (lookup tables shipped with each product) -------------------------

def _floats(text: str | None) -> np.ndarray:
    return np.array((text or "").split(), dtype="float64")


def parse_calibration(xml: bytes) -> list[tuple[float, np.ndarray, np.ndarray]]:
    """The sigma-nought calibration vectors of a GRD product: [(line, pixels, A_sigma)], in line order."""
    root = ET.fromstring(xml)
    vectors = [(float(v.findtext("line")), _floats(v.findtext("pixel")), _floats(v.findtext("sigmaNought")))
               for v in root.iter("calibrationVector")]
    return sorted(vectors, key=lambda v: v[0])


def parse_noise(xml: bytes) -> dict:
    """Thermal-noise lookup tables of a GRD product, in DN^2 units.

    Processing baseline 2.90 and later split the noise into a range table and per-sub-swath azimuth tables
    (noise = range x azimuth); older products have one ``noiseVector`` table and no azimuth part.
    """
    root = ET.fromstring(xml)
    ranges = [(float(v.findtext("line")), _floats(v.findtext("pixel")), _floats(v.findtext("noiseRangeLut")))
              for v in root.iter("noiseRangeVector")]
    if not ranges:
        ranges = [(float(v.findtext("line")), _floats(v.findtext("pixel")), _floats(v.findtext("noiseLut")))
                  for v in root.iter("noiseVector")]
    blocks = [(float(v.findtext("firstAzimuthLine")), float(v.findtext("firstRangeSample")),
               float(v.findtext("lastAzimuthLine")), float(v.findtext("lastRangeSample")),
               _floats(v.findtext("line")), _floats(v.findtext("noiseAzimuthLut")))
              for v in root.iter("noiseAzimuthVector")]
    return {"range": sorted(ranges, key=lambda v: v[0]), "azimuth": blocks}


def vectors_at(vectors, rows, cols) -> np.ndarray:
    """Bilinear look-up in a table of vectors: along range within each vector, then across vector lines."""
    rows, cols = np.atleast_1d(np.asarray(rows, float)), np.atleast_1d(np.asarray(cols, float))
    if not vectors:
        return np.full(rows.shape, np.nan)
    lines = np.array([line for line, _, _ in vectors])
    along = np.array([np.interp(cols, pixels, values) for _, pixels, values in vectors])   # (vectors, points)
    return np.array([np.interp(row, lines, along[:, i]) for i, row in enumerate(rows)])


def noise_at(noise: dict, rows, cols) -> np.ndarray:
    """Thermal noise (DN^2) at image positions; NaN where an azimuth table exists but none covers the point."""
    rows, cols = np.atleast_1d(np.asarray(rows, float)), np.atleast_1d(np.asarray(cols, float))
    level = vectors_at(noise["range"], rows, cols)
    if not noise["azimuth"]:
        return level
    azimuth = np.full(rows.shape, np.nan)
    for first_line, first_sample, last_line, last_sample, lines, lut in noise["azimuth"]:
        inside = (rows >= first_line) & (rows <= last_line) & (cols >= first_sample) & (cols <= last_sample)
        inside &= np.isnan(azimuth)
        if inside.any() and len(lines):
            azimuth[inside] = np.interp(rows[inside], lines, lut)
    return level * azimuth


def calibrate_sigma0(dn2, a_sigma, noise) -> np.ndarray:
    """sigma0 (linear) = (DN^2 - noise) / A_sigma^2. Zero or negative after noise removal gives NaN in dB later."""
    dn2, a_sigma, noise = (np.asarray(v, dtype="float64") for v in (dn2, a_sigma, noise))
    return (dn2 - noise) / a_sigma ** 2


def to_image(geom, transformer):
    """A lon/lat outline mapped into GRD image coordinates (x = column, y = row) through the scene's GCPs."""
    import shapely

    def project(x, y):
        rows, cols = transformer.rowcol(np.asarray(x, float), np.asarray(y, float), op=lambda v: v)   # fractional
        return np.asarray(cols, float), np.asarray(rows, float)

    return shapely.transform(geom, project, interleaved=False)


def image_field_stats(vv_dn, vh_dn, shapes, origin: tuple[int, int]) -> pd.DataFrame:
    """Per-field DN^2 medians in one image window. ``shapes`` are (image-space outline, field position).

    ``origin`` is (column, row) of the window's first pixel. GRD GCP positions are sample centres, so pixel
    (row r, column c) covers [c - 0.5, c + 0.5) x [r - 0.5, r + 0.5) in image coordinates.
    Returns zone, n_px, valid_frac, vv, vh (DN^2), centre_row, centre_col.
    """
    from affine import Affine
    from rasterio.features import rasterize

    vv_dn, vh_dn = np.asarray(vv_dn), np.asarray(vh_dn)
    col0, row0 = origin
    zones = rasterize(shapes, out_shape=vv_dn.shape, transform=Affine(1, 0, col0 - 0.5, 0, 1, row0 - 0.5),
                      fill=0, dtype="int32")
    stats = _zone_medians(vv_dn.astype("float64") ** 2, vh_dn.astype("float64") ** 2, zones)
    centres = {n: geom.centroid for geom, n in shapes}
    stats["centre_row"] = [centres[z].y for z in stats["zone"]]
    stats["centre_col"] = [centres[z].x for z in stats["zone"]]
    return stats


def _read_window(src, col0: int, row0: int, width: int, height: int) -> np.ndarray:
    """A window that may run past the image edge; pixels outside the image are 0 (no data)."""
    from rasterio.windows import Window

    out = np.zeros((height, width), dtype="uint16")
    c0, r0 = max(col0, 0), max(row0, 0)
    c1, r1 = min(col0 + width, src.width), min(row0 + height, src.height)
    if c1 > c0 and r1 > r0:
        out[r0 - row0:r1 - row0, c0 - col0:c1 - col0] = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0))
    return out


def _http_bytes(href: str) -> bytes:
    import requests

    response = requests.get(href, timeout=HTTP_TIMEOUT_S)
    response.raise_for_status()
    return response.content


def shapely_translate(shape, columns: float):
    """An image-space outline moved along the range (column) axis."""
    from shapely import affinity

    return affinity.translate(shape, xoff=columns)


def shift_scores(vv_dn, vh_dn, shapes, origin: tuple[int, int], shifts) -> np.ndarray:
    """How badly field outlines fit the image at each range shift (lower is better), NaN without evidence.

    Score = median over fields (at least ``MIN_SCORE_PX`` valid pixels) of the within-field interquartile range of
    VV and VH in dB, averaged over the two bands. Speckle gives every field the same spread wherever the outline
    sits; an outline that slips onto a road, ditch, tree line or the next field adds that contrast, so the right
    shift is the one where fields look most uniform.
    """
    from affine import Affine
    from rasterio.features import rasterize

    with np.errstate(divide="ignore", invalid="ignore"):
        db = [np.where(band > 0, 20.0 * np.log10(np.maximum(band, 1)), np.nan).ravel()
              for band in (np.asarray(vv_dn, float), np.asarray(vh_dn, float))]
    valid = np.isfinite(db[0]) & np.isfinite(db[1])
    col0, row0 = origin
    scores = []
    for shift in shifts:
        moved = [(shapely_translate(shape, shift), n) for shape, n in shapes]
        zones = rasterize(moved, out_shape=np.shape(vv_dn), transform=Affine(1, 0, col0 - 0.5, 0, 1, row0 - 0.5),
                          fill=0, dtype="int32").ravel()
        keep = (zones > 0) & valid
        grouped = pd.DataFrame({"zone": zones[keep], "vv": db[0][keep], "vh": db[1][keep]}).groupby("zone")
        big = grouped.size() >= MIN_SCORE_PX
        if not big.any():
            scores.append(np.nan)
            continue
        spread = (grouped.quantile(0.75) - grouped.quantile(0.25))[big]
        scores.append(float(spread[["vv", "vh"]].mean(axis=1).median()))
    return np.array(scores)


def track_shift(score_curves: list[np.ndarray], shifts) -> int:
    """The range shift (columns) with the lowest summed score over a track's passes; 0 without evidence.

    Every pass of one relative orbit sees the cell from the same geometry and the same GCP heights, so one shift
    serves the whole track-season, and summing the passes beats down the speckle in any single score.
    """
    curves = np.array([curve for curve in score_curves if np.isfinite(curve).any()])
    if not len(curves):
        return 0
    total = np.nansum(curves, axis=0)
    total[np.isnan(curves).all(axis=0)] = np.nan
    return int(np.asarray(shifts)[int(np.nanargmin(total))])


def _grd_item_read(item, core_lonlat) -> dict | None:
    """One GRD slice: field outlines in image space, the padded window of both bands and the lookup tables.

    None when no field outline falls on the slice or the window holds no valid pixel. The window is padded by
    ``MAX_SHIFT_PX`` in range so the outlines can be registered later without another read.
    """
    import rasterio
    from rasterio.transform import GCPTransformer

    with (rasterio.Env(**GDAL_ENV), rasterio.open(item.assets["vv"].href) as vv_src,
          rasterio.open(item.assets["vh"].href) as vh_src):
        transformer = GCPTransformer(vv_src.gcps[0], tps=True)
        shapes = [(shape, n) for geom, n in core_lonlat
                  if not (shape := to_image(geom, transformer)).is_empty and shape.is_valid]
        if not shapes:
            return None
        bounds = np.array([shape.bounds for shape, _ in shapes])
        pad = MAX_SHIFT_PX + 2
        col0, row0 = int(np.floor(bounds[:, 0].min())) - pad, int(np.floor(bounds[:, 1].min())) - 2
        width = int(np.ceil(bounds[:, 2].max())) + pad + 1 - col0
        height = int(np.ceil(bounds[:, 3].max())) + 3 - row0
        if col0 + width <= 0 or row0 + height <= 0 or col0 >= vv_src.width or row0 >= vv_src.height:
            return None
        vv, vh = (_read_window(src, col0, row0, width, height) for src in (vv_src, vh_src))
    if not ((vv > 0) & (vh > 0)).any():
        return None
    tables = {band: (parse_calibration(_http_bytes(item.assets[f"schema-calibration-{band}"].href)),
                     parse_noise(_http_bytes(item.assets[f"schema-noise-{band}"].href))) for band in BANDS}
    return {"shapes": shapes, "origin": (col0, row0), "vv": vv, "vh": vh, "tables": tables}


def _grd_item_stats(read: dict, shift: float) -> pd.DataFrame:
    """Calibrated field medians of one slice read, with the outlines moved ``shift`` columns in range."""
    shapes = [(shapely_translate(shape, shift), n) for shape, n in read["shapes"]]
    stats = image_field_stats(read["vv"], read["vh"], shapes, read["origin"])
    if stats.empty:
        return stats
    rows, cols = stats["centre_row"].to_numpy(), stats["centre_col"].to_numpy()
    for band in BANDS:
        calibration, noise = read["tables"][band]
        stats[f"{band}_db"] = to_db(calibrate_sigma0(stats[band], vectors_at(calibration, rows, cols),
                                                     noise_at(noise, rows, cols)))
    stats["n_valid"] = stats["n_px"] * stats["valid_frac"]
    return stats


def _pass_fields(reads: list[dict], shift: float, field_ids) -> pd.DataFrame | None:
    """One pass: each field from the slice that holds most of its valid pixels (slices of a pass abut)."""
    parts = [part for read in reads if len(part := _grd_item_stats(read, shift))]
    if not parts:
        return None
    best = pd.concat(parts, ignore_index=True).sort_values("n_valid", ascending=False, kind="mergesort")
    best = best.drop_duplicates("zone").sort_values("zone")
    best["field_id"] = np.asarray(field_ids)[best["zone"].to_numpy() - 1]
    return best[["field_id", "valid_frac", "vv_db", "vh_db"]].reset_index(drop=True)


def _with_retries(read_batch, batch, fields_utm, year: int, collection: str):
    """Run ``read_batch(batch)``; on a read error wait, search again for fresh signed links and retry.

    Signed links expire and remote reads fail now and then, so retry the same passes (matched by pass key)
    rather than losing the whole area. Returns (results, batch); the batch has fresh links after a retry.
    """
    import requests
    from rasterio.errors import RasterioError

    for attempt in range(1, READ_ATTEMPTS + 1):
        try:
            return read_batch(batch), batch
        except (RasterioError, requests.RequestException) as error:
            if attempt == READ_ATTEMPTS:
                raise
            print(f"read failed ({type(error).__name__}), attempt {attempt} of {READ_ATTEMPTS}; re-searching",
                  flush=True)
            time.sleep(RETRY_WAIT_S * attempt)
            wanted = {pass_key(items[0]) for items in batch}
            batch = [items for items in _search_passes(fields_utm, year, collection) if pass_key(items[0]) in wanted]


def _grd_pass_rows(passes, fields_utm, year: int, field_ids) -> list[tuple[list, pd.DataFrame]]:
    """(pass items, field medians) for every GRD pass that saw a field, registered per relative orbit.

    GCP geolocation assumes the GCP grid's terrain height; fields above or below it are displaced in range
    (h / tan(incidence)), by 70-90 m on the Quebec training cell. So the reads are kept, one range shift is
    found per track from the image itself (``shift_scores``), and only then are the field medians taken.
    """
    core = fields_utm.geometry.buffer(-INNER_BUFFER_M).to_crs("EPSG:4326")
    core_lonlat = [(geom, n + 1) for n, geom in enumerate(core) if not geom.is_empty]
    shifts = np.arange(-MAX_SHIFT_PX, MAX_SHIFT_PX + 1)

    def read_pass(items):
        reads = [read for item in items if (read := _grd_item_read(item, core_lonlat)) is not None]
        return reads, [shift_scores(r["vv"], r["vh"], r["shapes"], r["origin"], shifts) for r in reads]

    def read_batch(batch):
        with ThreadPoolExecutor(max_workers=PASS_THREADS) as pool:
            return list(pool.map(read_pass, batch))

    seen = []   # (items, reads, score curves)
    for start in range(0, len(passes), PASSES_PER_BATCH):
        results, batch = _with_retries(read_batch, passes[start:start + PASSES_PER_BATCH], fields_utm, year,
                                       COLLECTION)
        seen += [(items, reads, curves) for items, (reads, curves) in zip(batch, results) if reads]
    by_track: dict = {}
    for items, _, curves in seen:
        by_track.setdefault(items[0].properties.get("sat:relative_orbit"), []).extend(curves)
    track_shifts = {orbit: track_shift(curves, shifts) for orbit, curves in by_track.items()}
    print(f"range shift per relative orbit (10 m columns): {track_shifts}", flush=True)

    out = []
    for items, reads, _ in seen:
        shift = track_shifts[items[0].properties.get("sat:relative_orbit")]
        part = _pass_fields(reads, shift, field_ids)
        if part is not None and len(part):
            out.append((items, part.assign(range_shift_px=shift)))
    return out


# --- Sentinel-1 RTC (account key required) --------------------------------------------------------------------

def _pc_key_configured() -> bool:
    """True when a Planetary Computer subscription key is set. Only the presence is checked, never the value."""
    if os.environ.get("PC_SDK_SUBSCRIPTION_KEY"):
        return True
    try:
        from planetary_computer.settings import Settings

        return bool(Settings.get().subscription_key)
    except (ImportError, OSError, ValueError):   # no package or an unreadable settings file: no usable key
        return False


def _load_pass(pass_items, fields_utm):
    """One RTC pass as a lazy single-plane cube. The slices of a pass tile the ground, so they fuse into one."""
    from odc.stac import load

    bbox = tuple(fields_utm.to_crs("EPSG:4326").total_bounds)
    return load(pass_items, bands=BANDS, bbox=bbox, crs=fields_utm.crs, resolution=RESOLUTION_M,
                groupby=lambda item, parsed, idx: 0, chunks={})   # constant key: one plane; nothing read yet


def _rtc_pass_rows(passes, fields_utm, year: int, field_ids) -> list[tuple[list, pd.DataFrame]]:
    """(pass items, field medians) for every RTC pass, read in batches on threads."""
    import dask
    from odc.stac import configure_rio
    from rasterio.features import rasterize

    configure_rio(cloud_defaults=True)  # skip directory listings on every remote file open
    core = fields_utm.geometry.buffer(-INNER_BUFFER_M)
    numbered = [(geom, n + 1) for n, geom in enumerate(core) if not geom.is_empty]
    zones_by_grid: dict[tuple, np.ndarray] = {}   # every pass shares one grid; rasterize once per grid

    def read_batch(batch):
        cubes = [_load_pass(items, fields_utm) for items in batch]
        return dask.compute(*cubes, scheduler="threads", num_workers=READ_THREADS)

    out = []
    for start in range(0, len(passes), PASSES_PER_BATCH):
        cubes, batch = _with_retries(read_batch, passes[start:start + PASSES_PER_BATCH], fields_utm, year,
                                     RTC_COLLECTION)
        for items, cube in zip(batch, cubes):
            gbox = cube.odc.geobox
            grid = (tuple(gbox.shape), tuple(gbox.transform))
            if grid not in zones_by_grid:
                zones_by_grid[grid] = rasterize(numbered, out_shape=tuple(gbox.shape), transform=gbox.transform,
                                                fill=0, dtype="int32")
            part = pass_field_medians(cube["vv"].values[0], cube["vh"].values[0], zones_by_grid[grid], field_ids)
            if len(part):
                out.append((items, part))
    return out


# --- search, weather, assembly ---------------------------------------------------------------------------------

def _search_passes(fields_utm, year: int, collection: str = COLLECTION) -> list[list]:
    """The season's scenes over the fields, signed and grouped into passes. No cloud filter: radar.

    The RTC collection is refused without an account key: Planetary Computer requires an account to read it.
    """
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown Sentinel-1 collection {collection!r}; use one of {COLLECTIONS}")
    if collection == RTC_COLLECTION and not _pc_key_configured():
        raise RuntimeError("sentinel-1-rtc needs a Planetary Computer account: set PC_SDK_SUBSCRIPTION_KEY, or use "
                           "the default sentinel-1-grd, which needs none")
    import planetary_computer
    from pystac_client import Client

    catalog = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    bbox = tuple(fields_utm.to_crs("EPSG:4326").total_bounds)
    query = {"sar:instrument_mode": {"eq": "IW"}} if collection == COLLECTION else None
    items = catalog.search(collections=[collection], bbox=bbox, query=query,
                           datetime=f"{year}-{SEASON[0]}/{year}-{SEASON[1]}").item_collection()
    return group_passes(items)


def daily_weather(lat: float, lon: float, year: int) -> pd.DataFrame | None:
    """Daymet daily weather at one point for one year: date, tmin_c, prcp_mm, swe_mm. None if unavailable.

    One request per cell-year at the cell centre, rounded to 0.01 degree (Daymet's grid is 1 km anyway).
    """
    import requests

    params = {"lat": round(lat, 2), "lon": round(lon, 2), "vars": "tmin,prcp,swe", "years": year, "format": "json"}
    # Parallel pulls hit Daymet at the same moment and it refuses some requests now and then (seen for all
    # 17 Quebec cells in one run), so wait and try again before giving up on the frost and rain screen.
    for attempt in range(1, WEATHER_ATTEMPTS + 1):
        try:
            response = requests.get(WEATHER_URL, params=params, timeout=HTTP_TIMEOUT_S)
            response.raise_for_status()
            data = response.json()["data"]
            days = pd.Timestamp(f"{year}-01-01") + pd.to_timedelta(np.asarray(data["yday"], int) - 1, unit="D")
            return pd.DataFrame({"date": days, "tmin_c": data["tmin (deg c)"], "prcp_mm": data["prcp (mm/day)"],
                                 "swe_mm": data["swe (kg/m^2)"]})
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            if attempt < WEATHER_ATTEMPTS:
                time.sleep(WEATHER_WAIT_S * attempt)
                continue
            print(f"weather UNAVAILABLE for {year} after {WEATHER_ATTEMPTS} tries ({type(error).__name__}); "
                  "tmin_c, rain_48h_mm, swe_mm left NaN", flush=True)
    return None


def look_weather(looks: pd.DataFrame, daily: pd.DataFrame | None) -> pd.DataFrame:
    """Add tmin_c, swe_mm and rain_48h_mm to looks with ``date`` (local) and ``solar_hour``.

    Rain in the 48 hours before the pass: an evening pass (solar hour 12 or later) has seen that day's rain,
    so it is that day plus the day before; a morning pass gets the two previous days. Missing days stay NaN.
    """
    out = looks.copy()
    if daily is None or daily.empty:
        for column in WEATHER_COLUMNS:
            out[column] = np.nan
        return out
    day = daily.set_index(pd.to_datetime(daily["date"]).dt.normalize())
    dates = pd.to_datetime(out["date"]).dt.normalize()
    evening = (out["solar_hour"] >= 12).to_numpy()
    first = dates - pd.to_timedelta(np.where(evening, 1, 2), unit="D")
    second = dates - pd.to_timedelta(np.where(evening, 0, 1), unit="D")
    out["tmin_c"] = day["tmin_c"].reindex(dates).to_numpy()
    out["swe_mm"] = day["swe_mm"].reindex(dates).to_numpy()
    out["rain_48h_mm"] = day["prcp_mm"].reindex(first).to_numpy() + day["prcp_mm"].reindex(second).to_numpy()
    return out


def cell_series(fields_utm, year: int, collection: str = COLLECTION) -> pd.DataFrame:
    """Series for all fields of one cell in one year. ``fields_utm`` needs ``field_id`` and a UTM CRS."""
    core = fields_utm.geometry.buffer(-INNER_BUFFER_M)
    if all(geom.is_empty for geom in core):
        return pd.DataFrame(columns=COLUMNS)
    passes = _search_passes(fields_utm, year, collection)
    if not passes:
        return pd.DataFrame(columns=COLUMNS)
    cell = fields_utm["cell"].iloc[0] if "cell" in fields_utm.columns else "?"
    orbits = sorted({(p[0].properties.get("sat:orbit_state"), p[0].properties.get("sat:relative_orbit"))
                     for p in passes})
    print(f"cell {cell} {year}: {len(passes)} radar passes ({collection}), orbits {orbits}", flush=True)

    bounds = fields_utm.to_crs("EPSG:4326").total_bounds
    lon, lat = float(np.mean(bounds[[0, 2]])), float(np.mean(bounds[[1, 3]]))   # cell centre
    field_ids = fields_utm["field_id"].to_numpy()
    read = _rtc_pass_rows if collection == RTC_COLLECTION else _grd_pass_rows
    rows = []
    for items, part in read(passes, fields_utm, year, field_ids):
        props, when = items[0].properties, min(item.datetime for item in items)
        rows.append(part.assign(date=solar_date(when, lon), solar_hour=_solar_time(when, lon).hour, year=year,
                                relative_orbit=props.get("sat:relative_orbit"),
                                orbit_state=props.get("sat:orbit_state"), platform=props.get("platform")))
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    table = look_weather(pd.concat(rows, ignore_index=True), daily_weather(lat, lon, year))
    return table.reindex(columns=COLUMNS).round({"valid_frac": 3, "vv_db": 3, "vh_db": 3, "tmin_c": 2, "rain_48h_mm": 2,
                                 "swe_mm": 2})


def load_s1_series(path: Path) -> pd.DataFrame:
    """Per-field, per-pass radar series from one CSV or a folder of per-cell CSVs.

    Unlike ``field_model.load_series`` this keeps two passes that share a solar date (they differ in
    orbit and viewing angle), dropping only exact repeats of one pass.
    """
    path = Path(path)
    files = sorted(path.glob("*.csv")) if path.is_dir() else [path]
    if not files:
        raise FileNotFoundError(f"no series files in {path}; run kernelag.s1_series first")
    series = pd.concat([pd.read_csv(f, parse_dates=["date"]) for f in files], ignore_index=True)
    series["field_id"] = series["field_id"].astype(str)   # ids are text in label files, numbers in CSVs
    series["date"] = series["date"].dt.normalize()
    return series.drop_duplicates(["field_id", "year", "date", "platform", "relative_orbit"])


def series_for_fields(fields, name: str, cells: list[str] | None = None, force: bool = False,
                      collection: str = COLLECTION) -> pd.DataFrame:
    """Sentinel-1 series for a table of fields with ``field_id``, ``year`` and geometry. One file per cell-year.

    The loop, caching and manifest are the Sentinel-2 ones; the folder, puller, columns and source are Sentinel-1's
    (``data/s1_series/`` for GRD, ``data/s1_rtc_series/`` for RTC). A cached file written by an older puller (other
    columns, e.g. RTC gamma-nought without weather) would be read back as if it were finished, mixing products, so
    it stops the run unless ``force`` asks to replace it.
    """
    if not force:
        out_dir = data_dir() / FOLDERS[collection] / name
        stale = []
        for cell, year in assign_cells(fields)[["cell", "year"]].drop_duplicates().itertuples(index=False):
            part = out_dir / f"{cell}_{year}.csv"
            if (cells is None or cell in cells) and part.is_file():
                with part.open(encoding="utf-8") as handle:
                    if handle.readline().strip().split(",") != COLUMNS:
                        stale.append(part.name)
        if stale:
            raise RuntimeError(f"{len(stale)} cached file(s) in {out_dir} have other columns (an older puller, e.g. "
                               f"RTC without weather): {stale[:5]}; re-run with --force to replace them")
    return s2_series.series_for_fields(fields, name, cells, force, folder=FOLDERS[collection],
                                       cell_fn=partial(cell_series, collection=collection), columns=COLUMNS,
                                       source_url=SOURCE_URLS[collection])


def record_parts(fields, name: str, cells: list[str] | None, folder: str, source_url: str) -> int:
    """List the cached cell-year files of ``cells`` in the manifest; returns how many were listed.

    Parallel pulls run each cell in a child with KERNEL_NO_MANIFEST set (one manifest, many writers), and the
    parent then only reads those caches, so without this the files would never be listed.
    """
    out_dir, listed = data_dir() / folder / name, 0
    for cell, year in assign_cells(fields)[["cell", "year"]].drop_duplicates().itertuples(index=False):
        part = out_dir / f"{cell}_{year}.csv"
        if (cells is None or cell in cells) and part.is_file():
            record_in_manifest(part, source_url)
            listed += 1
    return listed


def main() -> None:
    import geopandas as gpd

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fields", required=True, help="GeoParquet with field_id, year, label, geometry")
    parser.add_argument("--cells", type=int, default=1,
                        help="how many cells to pull, densest in silage first; 0 means every cell")
    parser.add_argument("--only-cells", default="",
                        help="comma-separated cell ids to pull, written as --only-cells=ID,ID; overrides --cells")
    parser.add_argument("--parallel", type=int, default=1, help="cells pulled at the same time")
    parser.add_argument("--collection", choices=COLLECTIONS,
                        default=os.environ.get("KERNEL_S1_COLLECTION", COLLECTION),
                        help="sentinel-1-grd (default, no account) or sentinel-1-rtc (needs PC_SDK_SUBSCRIPTION_KEY)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fields = gpd.read_parquet(args.fields)
    name = Path(args.fields).stem
    if args.only_cells:
        chosen = args.only_cells.split(",")
    else:
        chosen = densest_cells(fields, args.cells) if args.cells > 0 else None
    if args.parallel > 1:
        cells = chosen if chosen is not None else sorted(assign_cells(fields)["cell"].unique())
        os.environ["KERNEL_S1_COLLECTION"] = args.collection   # the per-cell children read it as their default
        pull_cells_in_parallel(args.fields, cells, args.parallel, module="kernelag.s1_series")
    table = series_for_fields(fields, name, cells=chosen, force=args.force, collection=args.collection)
    if args.parallel > 1:
        record_parts(fields, name, chosen, FOLDERS[args.collection], SOURCE_URLS[args.collection])
    print(f"{len(table)} field-passes for {table['field_id'].nunique() if len(table) else 0} fields")


if __name__ == "__main__":
    main()
