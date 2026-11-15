"""NASS Crop Sequence Boundaries 2018-2025: field outlines with each field's crop per year.

One national file gives both things the state rollup needs: where the cornfields are in each
year (the crop code per year comes from the Cropland Data Layer) and their outlines.

The download is 3.76 GB, so it goes to a scratch folder outside the team workspace
(``KERNEL_SCRATCH_DIR``, default ``/tmp/kernel``). Only small samples are written to ``data/``.

Run: ``python -m kernelag.csb --inspect``     download, unpack, print the layer and its columns
"""

from __future__ import annotations

import argparse
import os
import urllib.request
import zipfile
from pathlib import Path

URL = ("https://www.nass.usda.gov/sites/default/files/Research_and_Science/"
       "Crop-Sequence-Boundaries/datasets/NationalCSB_2018-2025_rev23.zip")
EXPECTED_BYTES = 3_758_023_527   # Content-Length on 2026-11-15


def scratch_dir() -> Path:
    path = Path(os.environ.get("KERNEL_SCRATCH_DIR", "/tmp/kernel"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def download(force: bool = False) -> Path:
    """Fetch the national zip into the scratch folder; skip if a complete copy is there."""
    target = scratch_dir() / "NationalCSB_2018-2025_rev23.zip"
    if target.exists() and target.stat().st_size == EXPECTED_BYTES and not force:
        return target
    request = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    done = 0
    with urllib.request.urlopen(request, timeout=120) as response, open(target, "wb") as handle:
        while chunk := response.read(8 << 20):
            handle.write(chunk)
            done += len(chunk)
            if done % (400 << 20) < (8 << 20):
                print(f"  downloaded {done / 1e9:.1f} of {EXPECTED_BYTES / 1e9:.1f} GB", flush=True)
    if target.stat().st_size != EXPECTED_BYTES:
        print(f"WARNING: got {target.stat().st_size} bytes, expected {EXPECTED_BYTES}")
    return target


def unpack(zip_path: Path) -> Path:
    """Unzip next to the download and return the geodatabase (or other layer file) inside."""
    out = scratch_dir() / "csb"
    if not out.exists() or not any(out.iterdir()):
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(out)
    for pattern in ["**/*.gdb", "**/*.gpkg", "**/*.shp"]:
        found = sorted(out.glob(pattern))
        if found:
            return found[0]
    raise FileNotFoundError(f"no geodatabase, GeoPackage or shapefile found under {out}")


def inspect(dataset: Path) -> None:
    """Print what the sampler needs to know: layers, columns, row count, a few rows."""
    import pyogrio

    print("dataset:", dataset)
    layers = pyogrio.list_layers(dataset)
    print("layers:", layers.tolist())
    layer = layers[0][0]
    info = pyogrio.read_info(dataset, layer=layer)
    print("rows:", info["features"], "| crs:", str(info["crs"])[:60], "| geometry:", info["geometry_type"])
    print("columns:", list(zip(info["fields"].tolist(), info["dtypes"].tolist())))
    rows = pyogrio.read_dataframe(dataset, layer=layer, max_features=5, read_geometry=False)
    print(rows.to_string())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--force", action="store_true", help="download again even if the file is there")
    args = parser.parse_args()
    dataset = unpack(download(force=args.force))
    if args.inspect:
        inspect(dataset)
    else:
        print("ready:", dataset)


if __name__ == "__main__":
    main()
