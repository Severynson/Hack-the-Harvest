"""Per-field, per-date Landsat 8/9 series from Microsoft Planetary Computer (no key needed).

A second optical clock beside Sentinel-2 (DOCS/research/data_sources.md, row C3): Landsat 8 and 9
together pass every 8 days at 30 m, so they can fill some of the cloudy gaps around the silage cut.
For each field and each clear pass this gives the field median of the same three indices as
kernelag.s2_series:
    ndvi  greenness            (nir08 - red) / (nir08 + red)
    ndmi  canopy moisture      (nir08 - swir16) / (nir08 + swir16)
    ndti  residue on bare soil (swir16 - swir22) / (swir16 + swir22)
plus ``valid_frac``, the share of the field's pixels that were cloud-free that day, and ``platform``
(landsat-8 or landsat-9). Values are raw Landsat reflectance, NOT harmonised to Sentinel-2:
kernelag/multisensor.py calibrates the two sensors against each other later.

Landsat 7 is left out: its scan-line corrector failed in 2003 (stripes of missing pixels) and its
overpass time drifted in its last years. Only Tier 1 scenes are used (the best geolocation).

Fields are grouped into the same 10 km cells as Sentinel-2, and each cell-year is cached as
``data/landsat_series/<fields file>/<cell>_<year>.csv``, so a stopped run resumes where it left off.

Output columns: field_id, date, year, valid_frac, ndvi, ndmi, ndti, platform

Run (pilot): ``python -m kernelag.landsat_series --fields data/labels/quebec_maize_2023.parquet --cells 1``
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag import s2_series
from kernelag.paths import data_dir, record_in_manifest
from kernelag.s2_series import (
    READ_ATTEMPTS,
    READ_THREADS,
    RETRY_WAIT_S,
    SEASON,
    STAC_URL,
    assign_cells,
    densest_cells,
    pull_cells_in_parallel,
)

COLLECTION = "landsat-c2-l2"
SOURCE_URL = "https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2"
PLATFORMS = ["landsat-8", "landsat-9"]
BANDS = ["red", "nir08", "swir16", "swir22", "qa_pixel"]
SCALE, OFFSET = 2.75e-05, -0.2   # Collection 2 Level-2 surface reflectance = DN * SCALE + OFFSET
MAX_SCENE_CLOUD = 70             # as loose as Sentinel-2: the per-pixel QA mask does the real cloud work
CLOUD_BITS = 0b111111            # qa_pixel bits 0-5: fill, dilated cloud, cirrus, cloud, cloud shadow, snow
RESOLUTION_M = 30                # native for every reflectance band used here
INNER_BUFFER_M = 15              # half a pixel, so kept pixels sit inside the field along straight edges;
                                 # a full 30 m pixel would leave 56 of the 321 Quebec training fields empty
DATES_PER_BATCH = 12             # dates fetched together; a cell at 30 m is small, so memory is not the limit
COLUMNS = ["field_id", "date", "year", "valid_frac", "ndvi", "ndmi", "ndti", "platform"]


def clear_mask(qa) -> np.ndarray:
    """True where a ``qa_pixel`` value is clear: no fill, dilated cloud, cirrus, cloud, cloud shadow or snow.

    Water (bit 7) is allowed, as the Sentinel-2 mask keeps water too. Bits 1-5 are the high-confidence calls;
    the medium-confidence bits (8-15) are not masked, and the field median plus ``valid_frac`` absorb what
    slips through, as with Sentinel-2's scene classification.
    """
    return (np.asarray(qa).astype(np.int64) & CLOUD_BITS) == 0


def reflectance(dn) -> np.ndarray:
    """Surface reflectance from Collection 2 Level-2 digital numbers, clipped at 0 as the Sentinel-2 pull is.

    DN 0 is nodata and must be masked by the caller; here it comes out as 0, not as -0.2.
    """
    return np.clip(np.asarray(dn, dtype="float64") * SCALE + OFFSET, 0, None)


def _platforms_by_date(items) -> dict[str, str]:
    """Which satellite took each date (UTC), from the search results.

    Landsat 8 and 9 are 8 days apart and never pass one spot on the same day, but if two names ever share
    a date both are kept, joined with ``+``, rather than one being silently dropped.
    """
    seen: dict[str, set[str]] = {}
    for item in items:
        seen.setdefault(str(item.datetime.date()), set()).add(str(item.properties.get("platform", "")))
    return {day: "+".join(sorted(names)) for day, names in seen.items()}


def _open_cube(fields_utm, year: int, tolerant: bool = False):
    """Find the season's scenes and open them lazily. Returns (items, cube); cube is None without scenes.

    The search signs every file link, and a signed link stops working after a while, so a read
    that fails calls this again to get fresh links. ``tolerant`` reads an unreadable file as no-data
    instead of failing: one corrupt file on the server (seen for a 2022 QA_PIXEL asset) then costs
    one date, not the whole cell-year. A no-data QA pixel has its fill bit set, so nothing there is clear.
    """
    import planetary_computer
    from odc.stac import configure_rio, load
    from pystac_client import Client

    catalog = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    bbox = tuple(fields_utm.to_crs("EPSG:4326").total_bounds)
    items = list(catalog.search(
        collections=[COLLECTION], bbox=bbox,
        datetime=f"{year}-{SEASON[0]}/{year}-{SEASON[1]}",
        query={"platform": {"in": PLATFORMS},
               "landsat:collection_category": {"in": ["T1"]},
               "eo:cloud_cover": {"lt": MAX_SCENE_CLOUD}},
    ).item_collection())
    if not items:
        return items, None
    configure_rio(cloud_defaults=True)  # skip directory listings on every remote file open
    # Landsat pixel centres sit on multiples of 30 m in UTM. odc-stac's default grid puts pixel EDGES there,
    # which would shift every pixel by 15 m under nearest-neighbour resampling; "center" keeps the native grid.
    cube = load(items, bands=BANDS, bbox=bbox, crs=fields_utm.crs, resolution=RESOLUTION_M, anchor="center",
                groupby="solar_day", chunks={}, fail_on_error=not tolerant)  # lazy: nothing is read yet
    return items, cube


def _read_dates(cube, dates, fields_utm, year: int):
    """Read some dates of the cube into memory. Returns (data, cube); the cube is new after a retry.

    Remote reads fail now and then (expired link, dropped connection), so wait, reopen the cube
    with fresh links and try again, exactly as the Sentinel-2 pull does.
    """
    from rasterio.errors import RasterioError

    for attempt in range(1, READ_ATTEMPTS + 1):
        try:
            return cube.sel(time=dates).compute(scheduler="threads", num_workers=READ_THREADS), cube
        except RasterioError as error:
            if attempt == READ_ATTEMPTS:
                # Fresh links did not help, so a file itself is broken: read it as no-data and go on.
                print(f"read failed {READ_ATTEMPTS} times ({type(error).__name__}); reading unreadable files "
                      "as no-data so only their dates are lost", flush=True)
                _, cube = _open_cube(fields_utm, year, tolerant=True)
                return cube.sel(time=dates).compute(scheduler="threads", num_workers=READ_THREADS), cube
            print(f"read failed ({type(error).__name__}), attempt {attempt} of {READ_ATTEMPTS}; reopening",
                  flush=True)
            time.sleep(RETRY_WAIT_S * attempt)
            _, cube = _open_cube(fields_utm, year)


def cell_series(fields_utm, year: int) -> pd.DataFrame:
    """Series for all fields of one cell in one year. ``fields_utm`` needs ``field_id`` and a UTM CRS."""
    from rasterio.features import rasterize

    items, cube = _open_cube(fields_utm, year)
    if cube is None:
        return pd.DataFrame(columns=COLUMNS)

    # Field numbers burned onto the cube grid. Field ids can be strings, so use positions.
    gbox = cube.odc.geobox
    core = fields_utm.geometry.buffer(-INNER_BUFFER_M)
    numbered = [(geom, n + 1) for n, geom in enumerate(core) if not geom.is_empty]
    if not numbered:
        return pd.DataFrame(columns=COLUMNS)
    zones = rasterize(numbered, out_shape=tuple(gbox.shape), transform=gbox.transform, fill=0, dtype="int32").ravel()
    in_field = zones > 0
    field_ids = fields_utm["field_id"].to_numpy()

    platforms = _platforms_by_date(items)
    rows = []
    times = cube.time.values
    for start in range(0, len(times), DATES_PER_BATCH):
        # Reads are slow and independent, so fetch a batch of dates at once on many threads.
        batch, cube = _read_dates(cube, times[start:start + DATES_PER_BATCH], fields_utm, year)
        for t in batch.time.values:
            rows.append(field_medians(batch.sel(time=t), zones, in_field, field_ids,
                                      pd.Timestamp(t).normalize(), year, platforms))
    rows = [r for r in rows if r is not None]
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(rows, ignore_index=True)[COLUMNS].round({"valid_frac": 3, "ndvi": 4, "ndmi": 4, "ndti": 4})


def field_medians(scene, zones, in_field, field_ids, date, year, platforms):
    """Field medians of the three indices for one date, or None if no field pixel was clear.

    ``scene[band].values`` is one date's 2-D array per band (a time slice of the cube, as in kernelag.s2_series);
    ``zones`` is the flattened field number per pixel (0 outside every field) and ``in_field`` is ``zones > 0``.
    """
    raw = {b: np.asarray(scene[b].values).ravel()[in_field] for b in BANDS[:-1]}
    nodata = np.any([raw[b] == 0 for b in raw], axis=0)
    refl = {b: reflectance(raw[b]) for b in raw}
    clear = clear_mask(np.asarray(scene["qa_pixel"].values).ravel()[in_field]) & ~nodata
    if not clear.any():
        return None

    with np.errstate(invalid="ignore", divide="ignore"):
        pixels = pd.DataFrame({
            "zone": zones[in_field],
            "clear": clear,
            "ndvi": (refl["nir08"] - refl["red"]) / (refl["nir08"] + refl["red"]),
            "ndmi": (refl["nir08"] - refl["swir16"]) / (refl["nir08"] + refl["swir16"]),
            "ndti": (refl["swir16"] - refl["swir22"]) / (refl["swir16"] + refl["swir22"]),
        })
    valid = pixels.groupby("zone")["clear"].mean().rename("valid_frac")
    median = pixels[pixels["clear"]].groupby("zone")[["ndvi", "ndmi", "ndti"]].median()
    out = pd.concat([valid, median], axis=1).dropna(subset=["ndvi"]).reset_index()
    out["field_id"] = field_ids[out["zone"].to_numpy() - 1]
    # A date missing from the search results stays empty rather than being guessed.
    out["date"], out["year"], out["platform"] = date, year, platforms.get(str(date.date()))
    return out.drop(columns="zone")


def series_for_fields(fields, name: str, cells: list[str] | None = None, force: bool = False) -> pd.DataFrame:
    """Landsat series for a table of fields with ``field_id``, ``year`` and geometry. One cached file per cell-year.

    The loop, caching and manifest are the Sentinel-2 ones; only the folder, puller and columns differ.
    """
    return s2_series.series_for_fields(fields, name, cells, force, folder="landsat_series", cell_fn=cell_series,
                                       columns=COLUMNS, source_url=SOURCE_URL)


def record_parts(fields, name: str, cells: list[str] | None) -> int:
    """List the cached cell-year files of ``cells`` in the manifest; returns how many were listed.

    Parallel pulls run each cell in a child with KERNEL_NO_MANIFEST set (one manifest, many writers), and the
    parent then only reads those caches, so without this the files would never be listed.
    """
    out_dir, listed = data_dir() / "landsat_series" / name, 0
    for cell, year in assign_cells(fields)[["cell", "year"]].drop_duplicates().itertuples(index=False):
        part = out_dir / f"{cell}_{year}.csv"
        if (cells is None or cell in cells) and part.is_file():
            record_in_manifest(part, SOURCE_URL)
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
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fields = gpd.read_parquet(args.fields)
    if args.only_cells:
        chosen = args.only_cells.split(",")
    else:
        chosen = densest_cells(fields, args.cells) if args.cells > 0 else None
    if args.parallel > 1:
        cells = chosen if chosen is not None else sorted(assign_cells(fields)["cell"].unique())
        pull_cells_in_parallel(args.fields, cells, args.parallel, module="kernelag.landsat_series")
    table = series_for_fields(fields, Path(args.fields).stem, cells=chosen, force=args.force)
    if args.parallel > 1:
        record_parts(fields, Path(args.fields).stem, chosen)
    print(f"{len(table)} field-dates for {table['field_id'].nunique() if len(table) else 0} fields")


if __name__ == "__main__":
    main()
