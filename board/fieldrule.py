"""The caveman field rule from grain-or-silage.ipynb, and a live Sentinel-2 lookup for any point.

Rule 1: silage is chopped in one pass, so a field's greenness (NDVI) falls off a cliff; grain corn fades
over weeks. X = days the smoothed NDVI takes to fall from 80% to 20% of the field's own range after its
peak. Silage if X < 17.5 days (the cut-off learned on 801 Quebec fields, tested on USDA's Maryland fields).
Rule 2 only flips a borderline field (17.5-20.5 days) to silage when it is green again in Nov-Dec and its
county's winters allow a cover crop.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

CUTOFF = 17.5
MIN_CLEAR = 0.4
SMOOTH_DAYS = 15
SPRING = (90, 170)
DROP_FROM, DROP_TO = 0.8, 0.2
WINTER_DAYS = (300, 355)
WINTER_GREEN = 0.65
BORDER_BAND = 3.0
HERE = Path(__file__).resolve().parent


def greenness_line(series: pd.DataFrame) -> pd.Series:
    s = series[series["valid_frac"] >= MIN_CLEAR].dropna(subset=["ndvi"])
    if len(s) < 5:
        return pd.Series(dtype=float)
    s = s.groupby(pd.to_datetime(s["date"]).dt.day_of_year)["ndvi"].median()
    s = s.reindex(np.arange(s.index.min(), s.index.max() + 1)).interpolate()
    return s.rolling(SMOOTH_DAYS, center=True, min_periods=1).mean()


def field_features(series: pd.DataFrame) -> dict:
    out = {"drop_days": None, "winter_ndvi": None, "peak_day": None, "drop_start": None, "drop_end": None, "low": None, "peak": None}
    day = pd.to_datetime(series["date"]).dt.day_of_year
    winter = series[(series["valid_frac"] >= MIN_CLEAR) & day.between(*WINTER_DAYS)]["ndvi"].dropna()
    if len(winter):
        out["winter_ndvi"] = float(winter.median())
    line = greenness_line(series)
    if line.empty:
        return out
    peak_day = int(line.idxmax())
    spring = line.loc[SPRING[0]:min(SPRING[1], peak_day)]
    if spring.empty:
        return out
    low = float(spring.min())
    span = float(line.loc[peak_day]) - low
    after = line.loc[peak_day:]
    start, end = after[after <= low + DROP_FROM * span], after[after <= low + DROP_TO * span]
    out.update(peak_day=peak_day, low=round(low, 3), peak=round(float(line.loc[peak_day]), 3))
    if len(start) and len(end):
        out.update(drop_days=int(end.index[0] - start.index[0]), drop_start=int(start.index[0]), drop_end=int(end.index[0]))
    return out


def decide(f: dict, winter_vegetation: bool) -> tuple[str, str]:
    x = f["drop_days"]
    if x is not None and x < CUTOFF:
        return "silage", f"Greenness fell from 80% to 20% in {x} days: under {CUTOFF:g}, a one-pass chop."
    if x is not None and x < CUTOFF + BORDER_BAND and winter_vegetation and (f["winter_ndvi"] or 0) > WINTER_GREEN:
        return "silage", f"Borderline drop ({x} days) and green again in winter (NDVI {f['winter_ndvi']:.2f}): a cover crop after an early cut."
    if x is None:
        return "grain", "No clear drop in greenness, which is how grain corn dries in the field."
    return "grain", f"Greenness faded over {x} days: {CUTOFF:g} or more means the crop dried in the field before a combine took the grain."


def result(series: pd.DataFrame, winter_vegetation: bool) -> dict:
    f = field_features(series)
    call, why = decide(f, winter_vegetation)
    s = series.copy()
    s["doy"] = pd.to_datetime(s["date"]).dt.day_of_year
    line = greenness_line(series)
    return {"call": call, "why": why, "features": f, "cutoff": CUTOFF,
            "points": [[int(d), round(float(v), 3), round(float(c), 2)] for d, v, c in zip(s["doy"], s["ndvi"], s["valid_frac"]) if np.isfinite(v)],
            "line": [[int(d), round(float(v), 3)] for d, v in line.items() if np.isfinite(v)][::2]}


# ---------------------------------------------------------------- live lookup (needs network + pystac-client, planetary-computer, rasterio)
_WINTER: dict | None = None
_CACHE: dict = {}


def winter_vegetation(fips: str | None) -> bool:
    global _WINTER
    if _WINTER is None:
        p = HERE / "winter_vegetation.json"
        _WINTER = json.loads(p.read_text()) if p.exists() else {}
    return bool(_WINTER.get(fips or "", False))


def download_ndvi(lon: float, lat: float, year: int, radius_m: float = 45.0) -> pd.DataFrame:
    """NDVI of a small disc around (lon, lat) in every Sentinel-2 L2A picture of the season (same recipe as the notebook)."""
    from concurrent.futures import ThreadPoolExecutor

    import planetary_computer
    import pystac_client
    import rasterio
    from pyproj import Transformer
    from rasterio.features import rasterize
    from rasterio.windows import from_bounds
    from shapely.geometry import Point
    from shapely.ops import transform as shp_transform

    point = Point(lon, lat)
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    items = catalog.search(collections=["sentinel-2-l2a"], intersects=point, datetime=f"{year}-03-15/{year}-12-20",
                           query={"eo:cloud_cover": {"lt": 80}}).item_collection()

    def one(item):
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="30", GDAL_HTTP_MAX_RETRY="3"):
            bands = {}
            for name in ("B04", "B08", "SCL"):
                with rasterio.open(item.assets[name].href) as src:
                    if name == "B04":
                        to_src = Transformer.from_crs(4326, src.crs, always_xy=True).transform
                        shape = shp_transform(to_src, point).buffer(radius_m)
                        win = from_bounds(*shape.buffer(20).bounds, transform=src.transform).round_offsets().round_lengths()
                        tr, size = src.window_transform(win), (int(win.height), int(win.width))
                    w = from_bounds(*shape.buffer(20).bounds, transform=src.transform).round_offsets().round_lengths()
                    bands[name] = src.read(1, window=w, out_shape=size, boundless=True, fill_value=0).astype("float32")
        inside = rasterize([(shape, 1)], out_shape=size, transform=tr, fill=0).astype(bool)
        offset = 1000.0 if float(item.properties.get("s2:processing_baseline", "0")) >= 4.0 else 0.0
        red, nir = bands["B04"] - offset, bands["B08"] - offset
        clear = inside & np.isin(bands["SCL"], (4, 5)) & (bands["B04"] > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = (nir - red) / (nir + red)
        values = ndvi[clear & np.isfinite(ndvi)]
        return {"date": item.datetime.date(), "valid_frac": clear.sum() / max(inside.sum(), 1),
                "ndvi": float(np.median(values)) if values.size else np.nan}

    def safe(item):
        try:
            return one(item)
        except Exception:  # noqa: BLE001 - one unreadable picture should not sink the field
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        rows = [r for r in pool.map(safe, items) if r is not None]
    if not rows:
        return pd.DataFrame(columns=["date", "valid_frac", "ndvi"])
    out = pd.DataFrame(rows).sort_values(["date", "valid_frac"]).drop_duplicates("date", keep="last")
    out["date"] = pd.to_datetime(out["date"])
    return out.reset_index(drop=True)


def classify_point(lon: float, lat: float, year: int, fips: str | None) -> dict:
    key = (round(lon, 4), round(lat, 4), int(year))
    if key not in _CACHE:
        series = download_ndvi(lon, lat, year)
        out = result(series, winter_vegetation(fips)) if len(series) else {"call": None, "why": "No usable satellite pictures here."}
        out.update(lon=lon, lat=lat, year=year, pictures=int(len(series)), clear=int((series["valid_frac"] >= MIN_CLEAR).sum()) if len(series) else 0)
        _CACHE[key] = out
    return _CACHE[key]
