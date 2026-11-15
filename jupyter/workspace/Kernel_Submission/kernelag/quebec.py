"""Labeled maize parcels from Quebec's public declared-parcel database (BDPPAD).

Why: the organizers' Maryland labels (44 field-years) are a test set. To train anything
at field level we need many parcels where the farmer declared grain maize or silage maize.
Quebec publishes that per parcel every year since 2003 (La Financiere agricole du Quebec, CC-BY 4.0).

Labels: crop code ``MGR`` (mais-grain) -> grain; ``MFO`` and ``MFE`` (mais fourrager) -> silage.

Limits to state wherever these labels are used:
    - They are declarations to the crop insurer; the harvest mode can be changed until mid-September.
    - Silage on farms insured only for feed needs is not in the file, so silage is under-counted.
    - Quebec is not the US: a model trained here must be checked on the Maryland fields and US state totals.

Output: ``data/labels/quebec_maize_<year>.parquet``
    field_id, parcel_id, year, label, hectares, heat_units, geometry (EPSG:4326)

Run: ``python -m kernelag.quebec --year 2023``
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import pandas as pd

from kernelag.paths import data_dir, record_in_manifest

LANDING_PAGE = "http://www.fadq.qc.ca/documents/donnees/base-de-donnees-des-parcelles-et-productions-agricoles-declarees/"
FILE_URL = "https://www.fadq.qc.ca/fileadmin/geo4tb/BDPPAD/BDPPAD_{v}03_{year}.zip"
LOWERCASE_V_YEARS = {2012, 2013, 2022}   # three files are named with a lower-case "v"

LABELS = {"MGR": "grain", "MFO": "silage", "MFE": "silage"}
MAIZE_GROUPS = ("MGR", "MAF")            # crop groups: grain maize, forage maize
MIN_HECTARES = 2.0                       # smaller parcels hold too few 20 m pixels after the edge buffer


def download(year: int, force: bool = False) -> Path:
    """Fetch one year's zip (about 170 MB) into ``data/raw/quebec/``; skip if already there."""
    import requests

    target = data_dir() / "raw" / "quebec" / f"BDPPAD_V03_{year}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and zipfile.is_zipfile(target) and not force:
        return target
    url = FILE_URL.format(v="v" if year in LOWERCASE_V_YEARS else "V", year=year)
    with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "Mozilla/5.0"}) as response:
        response.raise_for_status()
        with open(target, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
    return target


def label_parcels(parcels, year: int):
    """Keep single-crop grain or silage maize parcels and name the columns Kernel uses.

    ``parcels`` has the BDPPAD columns IDANPAR, IDPAR, SUPHEC, NBPRO, CODPRO1, VARCUL and a geometry.
    Parcels declared with several crops are dropped: their label does not describe the whole field.
    """
    keep = parcels[
        (parcels["NBPRO"].astype(float) == 1)
        & parcels["CODPRO1"].isin(list(LABELS))
        & (parcels["SUPHEC"].astype(float) >= MIN_HECTARES)
    ].copy()
    # The cultivar text carries the hybrid's corn heat units after "UTM:", when the farmer gave them.
    heat_units = keep["VARCUL"].astype("string").str.extract(r"UTM\s*:?\s*(\d{4})", expand=False)
    out = keep[["geometry"]].copy()
    out["field_id"] = keep["IDANPAR"].astype(str).to_numpy()
    out["parcel_id"] = keep["IDPAR"].astype(str).to_numpy()
    out["year"] = year
    out["label"] = keep["CODPRO1"].map(LABELS).to_numpy()
    out["hectares"] = keep["SUPHEC"].astype(float).round(2).to_numpy()
    out["heat_units"] = pd.to_numeric(heat_units, errors="coerce").to_numpy()
    columns = ["field_id", "parcel_id", "year", "label", "hectares", "heat_units", "geometry"]
    return out[columns].reset_index(drop=True)


def read_maize_parcels(zip_path: Path, year: int):
    """Read only the maize rows from the zipped layer, then label them."""
    import geopandas as gpd

    with zipfile.ZipFile(zip_path) as archive:
        layers = [n for n in archive.namelist() if n.lower().endswith((".shp", ".gpkg", ".gdb"))]
    if not layers:
        raise FileNotFoundError(f"no spatial layer found in {zip_path.name}")
    groups = ", ".join(f"'{g}'" for g in MAIZE_GROUPS)
    parcels = gpd.read_file(f"zip://{zip_path.as_posix()}!{layers[0]}", where=f"GROPRO IN ({groups})")
    return label_parcels(parcels, year).to_crs("EPSG:4326")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    target = data_dir() / "labels" / f"quebec_maize_{args.year}.parquet"
    if target.exists() and not args.force:
        print(f"{target} exists; use --force to rebuild")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    labeled = read_maize_parcels(download(args.year), args.year)
    labeled.to_parquet(target)
    record_in_manifest(target, LANDING_PAGE)
    print(f"{len(labeled)} parcels -> {target}")
    print(labeled.groupby("label")["hectares"].agg(["size", "sum"]).round(0).to_string())


if __name__ == "__main__":
    main()
