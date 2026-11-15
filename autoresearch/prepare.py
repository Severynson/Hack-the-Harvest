"""
Fixed data preparation and evaluation harness for the silage-vs-grain autoresearch loop.

What it does (run once, cached):
  1. Loads the organizer BARC field polygons + yearly Grain/Silage labels.
  2. Pulls Sentinel-2 L2A scenes (Microsoft Planetary Computer, no account needed)
     over the BARC fields, 1 Mar - 20 Dec, 2021-2023.
  3. For every field and scene: keeps only pixels fully inside the field (polygon
     shrunk inward by EROSION_M), drops cloud/shadow/snow pixels using the SCL band,
     and stores the per-field median of several spectral indices.

Usage:
    uv run prepare.py            # build the cache (~10-20 min, network)
    uv run prepare.py --force    # rebuild

Cache: ~/.cache/autoresearch-silage/

The evaluation (`evaluate`) is the ground-truth metric. Do not modify this file;
experiments edit train.py only.
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

YEARS = (2021, 2022, 2023)
SEASON_START = "03-01"           # MM-DD
SEASON_END = "12-20"
EROSION_M = 10.0                 # shrink each field inward so edge pixels (road, hedge, neighbour) are dropped
MAX_SCENE_CLOUD = 90.0           # skip scenes that are almost fully cloudy at tile level
UTM_CRS = "EPSG:32618"           # Sentinel-2 grid for tile 18SUJ (BARC, Maryland)
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
BANDS = ("B02", "B04", "B08", "B11", "B12", "SCL")
VALID_SCL = (4, 5)               # 4 vegetation, 5 bare soil. Everything else (cloud, shadow, water, snow...) is masked.
POSITIVE = "Silage"

REPO_ROOT = Path(__file__).resolve().parents[1]
LABELS_PATH = REPO_ROOT / "jupyter" / "workspace" / "04_Evaluation" / "BARC_Corn.2021-2023.gpkg"
LABELS_LAYER = "barc_silage_grain_corn20212023"

CACHE_DIR = Path(os.path.expanduser("~")) / ".cache" / "autoresearch-silage"
TS_PATH = CACHE_DIR / "s2_field_timeseries.parquet"
SCENE_DIR = CACHE_DIR / "scenes"         # one small parquet per scene, so a killed build resumes
LABELS_CACHE = CACHE_DIR / "labels.parquet"
FIELDS_CACHE = CACHE_DIR / "fields.parquet"

# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def load_fields() -> gpd.GeoDataFrame:
    fields = gpd.read_file(LABELS_PATH, layer=LABELS_LAYER)
    return fields.to_crs(UTM_CRS)


def build_labels(fields: gpd.GeoDataFrame) -> pd.DataFrame:
    cols = {f"Corn_{y}": y for y in YEARS}
    lab = fields.melt(id_vars=["OBJECTID", "ACRES"], value_vars=list(cols), var_name="col", value_name="harvest_type")
    lab = lab[lab["harvest_type"].isin(["Grain", "Silage"])].copy()
    lab["year"] = lab["col"].map(cols)
    lab["y"] = (lab["harvest_type"] == POSITIVE).astype(int)
    return lab[["OBJECTID", "year", "harvest_type", "y", "ACRES"]].sort_values(["year", "OBJECTID"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Sentinel-2 extraction
# ---------------------------------------------------------------------------


def _search_items(bbox_lonlat, year):
    import planetary_computer as pc
    import pystac_client

    cat = pystac_client.Client.open(STAC_URL, modifier=pc.sign_inplace)
    items = cat.search(
        collections=["sentinel-2-l2a"],
        bbox=list(bbox_lonlat),
        datetime=f"{year}-{SEASON_START}/{year}-{SEASON_END}",
        query={"eo:cloud_cover": {"lt": MAX_SCENE_CLOUD}},
    ).item_collection()
    # One scene per acquisition: Planetary Computer can hold several processing versions; keep the newest.
    best = {}
    for it in items:
        key = (it.datetime.date(), it.properties["s2:mgrs_tile"], it.properties.get("sat:relative_orbit"))
        pb = float(it.properties.get("s2:processing_baseline", "0"))
        if key not in best or pb > best[key][0]:
            best[key] = (pb, it)
    return [v[1] for v in best.values()]


def _field_masks(fields_utm, transform, shape):
    """Per-field boolean masks of pixels whose centre lies inside the eroded polygon."""
    from rasterio.features import rasterize

    masks = {}
    for oid, geom in zip(fields_utm["OBJECTID"], fields_utm.geometry):
        g = geom.buffer(-EROSION_M)
        if g.is_empty:
            continue
        m = rasterize([(g, 1)], out_shape=shape, transform=transform, fill=0, all_touched=False, dtype="uint8").astype(bool)
        if m.any():
            masks[int(oid)] = m
    return masks


def _read_scene(item, bounds_utm):
    """Read all BANDS for the window covering the fields, resampled onto the 10 m grid."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    out, ref = {}, None
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_HTTP_MAX_RETRY="4",
        GDAL_HTTP_RETRY_DELAY="2",
        GDAL_HTTP_TIMEOUT="60",
        GDAL_HTTP_CONNECTTIMEOUT="15",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    ):
        for band in ("B04",) + tuple(b for b in BANDS if b != "B04"):
            with rasterio.open(item.assets[band].href) as src:
                win = from_bounds(*bounds_utm, transform=src.transform).round_offsets().round_lengths()
                if ref is None:
                    ref = (src.window_transform(win), (int(win.height), int(win.width)))
                arr = src.read(
                    1,
                    window=win,
                    out_shape=ref[1],
                    resampling=Resampling.nearest,
                    boundless=True,
                    fill_value=0,
                )
                out[band] = arr
    return out, ref


def _scene_stats(item, bounds_utm, fields_utm, mask_cache):
    bands, (transform, shape) = _read_scene(item, bounds_utm)
    key = (tuple(np.round(transform)[:6]), shape)
    if key not in mask_cache:
        mask_cache[key] = _field_masks(fields_utm, transform, shape)
    masks = mask_cache[key]

    pb = float(item.properties.get("s2:processing_baseline", "0"))
    offset = 1000.0 if pb >= 4.0 else 0.0  # baseline 04.00+ adds +1000 to L2A reflectance DNs
    refl = {b: (bands[b].astype("float32") - offset) / 10000.0 for b in BANDS if b != "SCL"}
    scl = bands["SCL"]
    nodata = bands["B04"] == 0

    def nd(a, b):
        with np.errstate(divide="ignore", invalid="ignore"):
            return (a - b) / (a + b)

    idx = {
        "ndvi": nd(refl["B08"], refl["B04"]),
        "ndmi": nd(refl["B08"], refl["B11"]),       # canopy water
        "ndti": nd(refl["B11"], refl["B12"]),       # crop residue / tillage
        "bsi": nd(refl["B11"] + refl["B04"], refl["B08"] + refl["B02"]),  # bare soil
        "red": refl["B04"],
        "nir": refl["B08"],
        "swir1": refl["B11"],
        "swir2": refl["B12"],
    }
    valid = np.isin(scl, VALID_SCL) & ~nodata
    rows = []
    date = item.datetime.date()
    for oid, m in masks.items():
        n = int(m.sum())
        v = m & valid
        nv = int(v.sum())
        row = {"OBJECTID": oid, "date": date, "n_pixels": n, "valid_frac": nv / n, "scene": item.id}
        for name, arr in idx.items():
            vals = arr[v]
            vals = vals[np.isfinite(vals)]
            row[name] = float(np.median(vals)) if vals.size else np.nan
            if name == "ndvi":
                row["ndvi_p25"] = float(np.percentile(vals, 25)) if vals.size else np.nan
                row["ndvi_p75"] = float(np.percentile(vals, 75)) if vals.size else np.nan
        rows.append(row)
    return rows


def _scene_job(item, bounds_utm, fields_utm, mask_cache):
    out = SCENE_DIR / f"{item.id}.parquet"
    if out.exists():
        return "cached"
    rows = _scene_stats(item, bounds_utm, fields_utm, mask_cache)
    tmp = out.with_suffix(".tmp")
    pd.DataFrame(rows).to_parquet(tmp)
    tmp.rename(out)
    return "new"


def build_timeseries(fields_utm: gpd.GeoDataFrame) -> pd.DataFrame:
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    bounds_utm = tuple(fields_utm.total_bounds + np.array([-50, -50, 50, 50]))
    bbox_lonlat = fields_utm.to_crs(4326).total_bounds
    mask_cache, wanted = {}, []
    for year in YEARS:
        items = _search_items(bbox_lonlat, year)
        wanted += [it.id for it in items]
        print(f"{year}: {len(items)} scenes", flush=True)
        done, failed = 0, 0
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(_scene_job, it, bounds_utm, fields_utm, mask_cache): it for it in items}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as e:  # one bad scene should not kill the build; re-run to retry it
                    failed += 1
                    print(f"  skip {futs[fut].id}: {e}", file=sys.stderr, flush=True)
                done += 1
                if done % 20 == 0 or done == len(items):
                    print(f"  {year}: {done}/{len(items)} scenes, {failed} failed", flush=True)
    parts = [pd.read_parquet(SCENE_DIR / f"{i}.parquet") for i in wanted if (SCENE_DIR / f"{i}.parquet").exists()]
    print(f"scenes on disk: {len(parts)}/{len(wanted)}", flush=True)
    ts = pd.concat(parts, ignore_index=True)
    ts["date"] = pd.to_datetime(ts["date"])
    ts["year"] = ts["date"].dt.year
    ts["doy"] = ts["date"].dt.dayofyear
    # Two scenes on one day (overlapping orbits): keep the clearer one.
    ts = ts.sort_values("valid_frac").drop_duplicates(["OBJECTID", "date"], keep="last")
    return ts.sort_values(["OBJECTID", "date"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Runtime API used by train.py
# ---------------------------------------------------------------------------


def load_data():
    """Returns (timeseries, labels).

    timeseries: one row per field per scene for ALL 83 fields (unlabelled ones too):
        OBJECTID, date, year, doy, n_pixels, valid_frac, ndvi, ndvi_p25, ndvi_p75, ndmi, ndti, bsi,
        red, nir, swir1, swir2, scene
    labels: one row per labelled field-year: OBJECTID, year, harvest_type, y (1 = Silage), ACRES
    """
    if not TS_PATH.exists() or not LABELS_CACHE.exists():
        raise SystemExit("Cache missing. Run: uv run prepare.py")
    return pd.read_parquet(TS_PATH), pd.read_parquet(LABELS_CACHE)


def _scores(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, int), np.asarray(y_pred, int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    return {
        "silage_f1": f1,
        "silage_precision": prec,
        "silage_recall": rec,
        "balanced_acc": (rec + spec) / 2,
        "accuracy": (tp + tn) / len(y_true),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def evaluate(fit_predict):
    """Leave-one-year-out evaluation. THE metric.

    fit_predict(ts_train, labels_train, ts_test, keys_test) -> array of 0/1 (1 = Silage),
    one per row of keys_test (OBJECTID, year).

    For each held-out year Y:
      - ts_train / labels_train: only years != Y (labels of Y are never shown).
      - ts_test: the time series of year Y for every field (unlabelled fields included),
        so per-year unsupervised steps (e.g. clustering harvest dates) are allowed.
    Out-of-fold predictions for all 44 field-years are pooled and scored.
    Primary metric: silage_f1 (higher is better).
    """
    ts, labels = load_data()
    preds = []
    for year in YEARS:
        tr_lab = labels[labels["year"] != year]
        te_keys = labels.loc[labels["year"] == year, ["OBJECTID", "year"]].reset_index(drop=True)
        ts_tr = ts[ts["year"] != year]
        ts_te = ts[ts["year"] == year]
        p = np.asarray(fit_predict(ts_tr, tr_lab.reset_index(drop=True), ts_te, te_keys.copy()), dtype=int)
        if p.shape != (len(te_keys),):
            raise ValueError(f"fit_predict returned shape {p.shape}, expected ({len(te_keys)},)")
        preds.append(te_keys.assign(pred=p))
    oof = pd.concat(preds).merge(labels, on=["OBJECTID", "year"])
    overall = _scores(oof["y"], oof["pred"])
    per_year = {int(y): _scores(g["y"], g["pred"])["silage_f1"] for y, g in oof.groupby("year")}
    return overall, per_year, oof


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fields = load_fields()
    labels = build_labels(fields)
    labels.to_parquet(LABELS_CACHE)
    pd.DataFrame(fields.drop(columns="geometry")).to_parquet(FIELDS_CACHE)
    print(f"labels: {len(labels)} field-years, {labels['y'].sum()} silage")
    if TS_PATH.exists() and not args.force:
        print(f"time series cached at {TS_PATH}")
    else:
        ts = build_timeseries(fields)
        ts.to_parquet(TS_PATH)
        print(f"time series: {len(ts)} rows, {ts['OBJECTID'].nunique()} fields, saved {TS_PATH}")
