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
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag.paths import data_dir, record_in_manifest

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SOURCE_URL = "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"
BANDS = ["B04", "B08", "B8A", "B11", "B12", "SCL"]
SEASON = ("05-01", "11-30")   # May catches green-up and the peak; November shows what is left
MAX_SCENE_CLOUD = 70          # loose at scene level; the per-pixel mask does the real cloud work
CLEAR_SCL = [4, 5, 6, 7]      # vegetation, bare soil, water, unclassified
RESOLUTION_M = 20             # native for B8A, B11 and B12
INNER_BUFFER_M = 20           # shrink fields by one pixel so roads and tree lines do not mix in
CELL_KM = 10
DATES_PER_BATCH = 12          # dates fetched together; about 30 MB of memory per batch
READ_THREADS = 32             # remote reads are waiting, not computing, so many threads help


def _s2_offset(item) -> int:
    """Sentinel-2 processing baseline 04.00 and later adds 1000 to every reflectance value."""
    try:
        return 1000 if float(item.properties.get("s2:processing_baseline") or 0) >= 4.0 else 0
    except ValueError:
        return 0


def assign_cells(fields, cell_km: int = CELL_KM):
    """Add a ``cell`` id (square grid in the fields' local UTM zone) and return fields in that zone."""
    utm = fields.to_crs(fields.estimate_utm_crs())
    centre = utm.geometry.representative_point()
    size = cell_km * 1000
    utm["cell"] = (centre.x // size).astype(int).astype(str) + "_" + (centre.y // size).astype(int).astype(str)
    return utm


def cell_series(fields_utm, year: int) -> pd.DataFrame:
    """Series for all fields of one cell in one year. ``fields_utm`` needs ``field_id`` and a UTM CRS."""
    import planetary_computer
    from odc.stac import configure_rio, load
    from pystac_client import Client
    from rasterio.features import rasterize

    catalog = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    bbox = tuple(fields_utm.to_crs("EPSG:4326").total_bounds)
    items = list(catalog.search(
        collections=["sentinel-2-l2a"], bbox=bbox,
        datetime=f"{year}-{SEASON[0]}/{year}-{SEASON[1]}",
        query={"eo:cloud_cover": {"lt": MAX_SCENE_CLOUD}},
    ).item_collection())
    if not items:
        return pd.DataFrame()

    configure_rio(cloud_defaults=True)  # skip directory listings on every remote file open
    cube = load(items, bands=BANDS, bbox=bbox, crs=fields_utm.crs, resolution=RESOLUTION_M,
                groupby="solar_day", chunks={})  # lazy: nothing is read yet

    # Field numbers burned onto the cube grid. Field ids can be strings, so use positions.
    gbox = cube.odc.geobox
    core = fields_utm.geometry.buffer(-INNER_BUFFER_M)
    numbered = [(geom, n + 1) for n, geom in enumerate(core) if not geom.is_empty]
    if not numbered:
        return pd.DataFrame()
    zones = rasterize(numbered, out_shape=tuple(gbox.shape), transform=gbox.transform, fill=0, dtype="int32").ravel()
    in_field = zones > 0
    field_ids = fields_utm["field_id"].to_numpy()

    offsets = {str(item.datetime.date()): _s2_offset(item) for item in items}
    rows = []
    times = cube.time.values
    for start in range(0, len(times), DATES_PER_BATCH):
        # Reads are slow and independent, so fetch a batch of dates at once on many threads.
        batch = cube.isel(time=slice(start, start + DATES_PER_BATCH)).compute(
            scheduler="threads", num_workers=READ_THREADS)
        for t in batch.time.values:
            rows.append(_field_medians(batch.sel(time=t), zones, in_field, field_ids,
                                       pd.Timestamp(t), year, offsets))
    rows = [r for r in rows if r is not None]
    if not rows:
        return pd.DataFrame()
    columns = ["field_id", "date", "year", "valid_frac", "ndvi", "ndmi", "ndti", "s2_offset"]
    return pd.concat(rows, ignore_index=True)[columns].round({"valid_frac": 3, "ndvi": 4, "ndmi": 4, "ndti": 4})


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


def series_for_fields(fields, name: str, cells: list[str] | None = None, force: bool = False) -> pd.DataFrame:
    """Series for a table of fields with ``field_id``, ``year`` and geometry. One cached file per cell-year."""
    out_dir = data_dir() / "s2_series" / name
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
            part = cell_series(group, int(year))
            part.to_csv(part_file, index=False, lineterminator="\n")
            record_in_manifest(part_file, SOURCE_URL)
        print(f"cell {cell} {year}: {len(group)} fields, {len(part)} field-dates")
        parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def densest_cells(fields, n: int, by: str = "label", value: str = "silage") -> list[str]:
    """The ``n`` cells with the most fields of the rarer class, so the sample holds both classes."""
    utm = assign_cells(fields)
    counts = utm[utm[by] == value].groupby("cell").size().sort_values(ascending=False)
    return counts.head(n).index.tolist()


def main() -> None:
    import geopandas as gpd

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fields", required=True, help="GeoParquet with field_id, year, label, geometry")
    parser.add_argument("--cells", type=int, default=1, help="how many cells to pull, densest in silage first")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fields = gpd.read_parquet(args.fields)
    chosen = densest_cells(fields, args.cells)
    table = series_for_fields(fields, Path(args.fields).stem, cells=chosen, force=args.force)
    print(f"{len(table)} field-dates for {table['field_id'].nunique() if len(table) else 0} fields")


if __name__ == "__main__":
    main()
