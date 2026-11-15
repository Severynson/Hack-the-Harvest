"""Per-field, per-date Sentinel-2 series from Microsoft Planetary Computer (no key needed).

For each field and each clear satellite pass this gives the field median of three indices:
    ndvi  greenness            (B08 - B04) / (B08 + B04)
    ndmi  canopy moisture      (B8A - B11) / (B8A + B11)
    ndti  residue on bare soil (B11 - B12) / (B11 + B12)
plus ``valid_frac``, the share of the field's pixels that were cloud-free that day.

Fields are grouped into square cells so that each download is one small image cube,
and each cell-year is cached as its own file: a stopped run resumes where it left off.

Output columns: field_id, date, year, valid_frac, ndvi, ndmi, ndti, s2_offset

Run (pilot): ``python -m kernelag.s2_series --fields data/labels/quebec_maize_2023.parquet --cells 1``
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag.paths import data_dir, record_in_manifest

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SOURCE_URL = "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"
BANDS = ["B04", "B08", "B8A", "B11", "B12", "SCL"]
# Optional second source: Element 84 Earth Search, the AWS Open Data copy of ESA's reprocessed Collection 1 L2A
# (listed next to Planetary Computer in the organizers' geospatial references). Same bands under common names,
# no signing. Chosen with KERNEL_S2_SOURCE=earthsearch, e.g. when Planetary Computer throttles a large pull.
# Collection 1 is processing baseline 05.x everywhere, so _s2_offset removes the same 1000 counts.
EARTH_SEARCH = {"stac": "https://earth-search.aws.element84.com/v1", "collection": "sentinel-2-c1-l2a",
                "source_url": "https://registry.opendata.aws/sentinel-2-l2a-cogs/",
                "assets": {"B04": "red", "B08": "nir", "B8A": "nir08", "B11": "swir16", "B12": "swir22", "SCL": "scl"}}


MIN_SEASON_SCENES = 10        # fewer Collection 1 scenes than this in a season means that year is not published


def _source() -> str:
    return os.environ.get("KERNEL_S2_SOURCE", "pc").lower()
SEASON = ("05-01", "11-30")   # May catches green-up and the peak; November shows what is left
MAX_SCENE_CLOUD = 70          # loose at scene level; the per-pixel mask does the real cloud work
CLEAR_SCL = [4, 5, 6, 7]      # vegetation, bare soil, water, unclassified
RESOLUTION_M = 20             # native for B8A, B11 and B12
INNER_BUFFER_M = 20           # shrink fields by one pixel so roads and tree lines do not mix in
CELL_KM = 10
DATES_PER_BATCH = 12          # dates fetched together; about 30 MB of memory per batch
READ_THREADS = int(os.environ.get("KERNEL_READ_THREADS", 32))   # reads wait on the network
READ_ATTEMPTS = 3             # tries per batch of dates before the area-year is given up
RETRY_WAIT_S = 20             # wait before the second try; twice that before the third
COLUMNS = ["field_id", "date", "year", "valid_frac", "ndvi", "ndmi", "ndti", "s2_offset"]


def _s2_offset(item) -> int:
    """Sentinel-2 processing baseline 04.00 and later adds 1000 to every reflectance value."""
    try:
        return 1000 if float(item.properties.get("s2:processing_baseline") or 0) >= 4.0 else 0
    except ValueError:
        return 0


def assign_cells(fields, cell_km: int = CELL_KM):
    """Add a ``cell`` id (square grid in the fields' local UTM zone) and return fields in that zone.

    A ``cell`` column that is already there (set by a sampler) is kept as it is.
    """
    utm = fields.to_crs(fields.estimate_utm_crs())
    if "cell" in fields.columns:
        return utm
    centre = utm.geometry.representative_point()
    size = cell_km * 1000
    utm["cell"] = (centre.x // size).astype(int).astype(str) + "_" + (centre.y // size).astype(int).astype(str)
    return utm


def _open_cube(fields_utm, year: int):
    """Find the season's scenes and open them lazily. Returns (items, cube); cube is None without scenes.

    The search signs every file link, and a signed link stops working after a while, so a read
    that fails calls this again to get fresh links.
    """
    import planetary_computer
    from odc.stac import configure_rio, load
    from pystac_client import Client

    bbox = tuple(fields_utm.to_crs("EPSG:4326").total_bounds)

    def search(catalog, collection):
        return list(catalog.search(
            collections=[collection], bbox=bbox,
            datetime=f"{year}-{SEASON[0]}/{year}-{SEASON[1]}",
            query={"eo:cloud_cover": {"lt": MAX_SCENE_CLOUD}},
        ).item_collection())

    earth_search = _source() == "earthsearch"
    items = search(Client.open(EARTH_SEARCH["stac"]), EARTH_SEARCH["collection"]) if earth_search else []
    if earth_search and len(items) < MIN_SEASON_SCENES:
        # Collection 1 has not been published for every year (2022 has 0-2 scenes where a season has 80-170),
        # so that cell-year comes from Planetary Computer; the two agree to about 0.004 NDVI (BARC 2021, 2023).
        print(f"only {len(items)} Collection 1 scenes for {year}; using Planetary Computer for this cell-year",
              flush=True)
        earth_search = False
    if not earth_search:
        items = search(Client.open(STAC_URL, modifier=planetary_computer.sign_inplace), "sentinel-2-l2a")
    if not items:
        return items, None
    configure_rio(cloud_defaults=True)  # skip directory listings on every remote file open
    assets = [EARTH_SEARCH["assets"][b] for b in BANDS] if earth_search else BANDS
    cube = load(items, bands=assets, bbox=bbox, crs=fields_utm.crs, resolution=RESOLUTION_M,
                groupby="solar_day", chunks={})  # lazy: nothing is read yet
    if earth_search:   # back to the band names the rest of this module uses
        cube = cube.rename({EARTH_SEARCH["assets"][b]: b for b in BANDS})
    return items, cube


def _read_dates(cube, dates, fields_utm, year: int):
    """Read some dates of the cube into memory. Returns (data, cube); the cube is new after a retry.

    Remote reads fail now and then (expired link, dropped connection). One failure used to lose
    the whole area, so wait, reopen the cube with fresh links and try again.
    """
    from rasterio.errors import RasterioError

    for attempt in range(1, READ_ATTEMPTS + 1):
        try:
            return cube.sel(time=dates).compute(scheduler="threads", num_workers=READ_THREADS), cube
        except RasterioError as error:
            if attempt == READ_ATTEMPTS:
                raise
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

    offsets = {str(item.datetime.date()): _s2_offset(item) for item in items}
    rows = []
    times = cube.time.values
    for start in range(0, len(times), DATES_PER_BATCH):
        # Reads are slow and independent, so fetch a batch of dates at once on many threads.
        batch, cube = _read_dates(cube, times[start:start + DATES_PER_BATCH], fields_utm, year)
        for t in batch.time.values:
            rows.append(_field_medians(batch.sel(time=t), zones, in_field, field_ids,
                                       pd.Timestamp(t).normalize(), year, offsets))
    rows = [r for r in rows if r is not None]
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(rows, ignore_index=True)[COLUMNS].round({"valid_frac": 3, "ndvi": 4, "ndmi": 4, "ndti": 4})


def _field_medians(scene, zones, in_field, field_ids, date, year, offsets):
    """Field medians of the three indices for one date, or None if no field pixel was clear."""
    offset = offsets.get(str(date.date()), 0)
    raw = {b: scene[b].values.astype("float32").ravel()[in_field] for b in BANDS[:-1]}
    nodata = np.any([raw[b] == 0 for b in raw], axis=0)
    refl = {b: np.clip((raw[b] - offset) / 10000.0, 0, None) for b in raw}
    clear = np.isin(scene["SCL"].values.ravel()[in_field], CLEAR_SCL) & ~nodata
    if not clear.any():
        return None

    with np.errstate(invalid="ignore", divide="ignore"):
        pixels = pd.DataFrame({
            "zone": zones[in_field],
            "clear": clear,
            "ndvi": (refl["B08"] - refl["B04"]) / (refl["B08"] + refl["B04"]),
            "ndmi": (refl["B8A"] - refl["B11"]) / (refl["B8A"] + refl["B11"]),
            "ndti": (refl["B11"] - refl["B12"]) / (refl["B11"] + refl["B12"]),
        })
    valid = pixels.groupby("zone")["clear"].mean().rename("valid_frac")
    median = pixels[pixels["clear"]].groupby("zone")[["ndvi", "ndmi", "ndti"]].median()
    out = pd.concat([valid, median], axis=1).dropna(subset=["ndvi"]).reset_index()
    out["field_id"] = field_ids[out["zone"].to_numpy() - 1]
    out["date"], out["year"], out["s2_offset"] = date, year, offset
    return out.drop(columns="zone")


def series_for_fields(fields, name: str, cells: list[str] | None = None, force: bool = False, *,
                      folder: str = "s2_series", cell_fn=None, columns: list[str] | None = None,
                      source_url: str = SOURCE_URL) -> pd.DataFrame:
    """Series for a table of fields with ``field_id``, ``year`` and geometry. One cached file per cell-year.

    The defaults are the Sentinel-2 pull. The Landsat and Sentinel-1 pullers reuse this loop with
    their own ``folder`` (under ``data/``), ``cell_fn(fields_utm, year)``, ``columns`` and ``source_url``.
    """
    cell_fn = cell_fn or cell_series
    columns = columns or COLUMNS
    out_dir = data_dir() / folder / name
    out_dir.mkdir(parents=True, exist_ok=True)
    utm = assign_cells(fields)
    parts = []
    for (cell, year), group in utm.groupby(["cell", "year"]):
        if cells is not None and cell not in cells:
            continue
        part_file = out_dir / f"{cell}_{year}.csv"
        if part_file.exists() and not force:
            part = pd.read_csv(part_file, parse_dates=["date"])
        else:
            part = cell_fn(group, int(year))
            if len(part) == 0:
                part = pd.DataFrame(columns=columns)   # keep the header so the file reads back
            unfinished = part_file.with_suffix(".part")
            part.to_csv(unfinished, index=False, lineterminator="\n")
            os.replace(unfinished, part_file)          # a stopped run never leaves half a file
            record_in_manifest(part_file, source_url)
        print(f"cell {cell} {year}: {len(group)} fields, {len(part)} field-dates", flush=True)
        parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def densest_cells(fields, n: int, by: str = "label", value: str = "silage") -> list[str]:
    """The ``n`` cells with the most fields of the rarer class, so the sample holds both classes."""
    utm = assign_cells(fields)
    counts = utm[utm[by] == value].groupby("cell").size().sort_values(ascending=False)
    return counts.head(n).index.tolist()


def pull_cells_in_parallel(fields_path: str, cells: list[str], workers: int,
                           module: str = "kernelag.s2_series") -> None:
    """One process per cell, ``workers`` at a time. Finished cell-years are kept, so it resumes.

    ``module`` is the puller to run per cell (``kernelag.landsat_series`` and ``kernelag.s1_series``
    take the same arguments as this one).
    """
    import subprocess
    import sys
    from concurrent.futures import ThreadPoolExecutor

    environment = {**os.environ, "KERNEL_NO_MANIFEST": "1", "KERNEL_READ_THREADS": "16"}

    def run(cell: str) -> str:
        done = subprocess.run([sys.executable, "-m", module, "--fields", fields_path,
                               f"--only-cells={cell}"], capture_output=True, text=True, env=environment)
        lines = [line for line in done.stdout.splitlines() if line.startswith("cell ")]
        return "\n".join(lines) if done.returncode == 0 else f"cell {cell}: FAILED\n{done.stderr[-400:]}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for text in pool.map(run, cells):
            print(text, flush=True)


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
        pull_cells_in_parallel(args.fields, cells, args.parallel)
    source_url = EARTH_SEARCH["source_url"] if _source() == "earthsearch" else SOURCE_URL
    table = series_for_fields(fields, Path(args.fields).stem, cells=chosen, force=args.force, source_url=source_url)
    print(f"{len(table)} field-dates for {table['field_id'].nunique() if len(table) else 0} fields")


if __name__ == "__main__":
    main()
