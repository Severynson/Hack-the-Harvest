"""Quebec maize labels for many years, in the same 17 areas as the 2023 field model (``qcm_<year>``).

Why: the field model is fitted on Quebec 2023 only, so it has never been asked about another season.
FADQ publishes the declared-parcel database (BDPPAD) every year. This builds one label table per year
from it, restricted to the 17 cells (10 km squares) the 2023 model already uses, so a later model can be
fitted on several years and scored on a year it never saw.

Areas: cell 79_515 (``quebec_maize_2023``'s series) plus the 16 cells of ``qc_regions_2023``. Cells are
computed exactly as ``kernelag.s2_series.assign_cells`` computed them for the whole 2023 table: the
representative point of each parcel in EPSG:32618 (the UTM zone that table resolves to), floored to 10 km.
``verify`` recomputes the 2023 cells this way and checks them against ``qc_regions_2023``'s cell column.

Labels: ``kernelag.quebec.label_parcels`` unchanged (grain = MGR, silage = MFO/MFE, single crop, >= 2 ha).
The download uses the requests library's default client headers.

Outputs (named ``qcm_`` so field_model's ``TRAIN_PATTERN = "quebec_maize_*"`` never picks them up):
    data/raw/quebec/BDPPAD_<V|v>03_<year>.zip        FADQ's file, as served (git-ignored folder)
    data/labels/qcm_<year>.parquet                   field_id, parcel_id, year, label, hectares, heat_units,
                                                     cell, geometry (EPSG:4326)
    data/s2_series/qcm_<year>/<cell>_<year>.csv      Sentinel-2 series (kernelag.s2_series; 2023 copied)

2023 is not downloaded again: its labels are the 17-cell subset of ``quebec_maize_2023`` and its series are
copies of the published ``quebec_maize_2023`` and ``qc_regions_2023`` files (Planetary Computer), so the
2023 rows here are identical to the ones the published field model and the feature harness use.

Run from the repository root:
    .venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py verify
    .venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py download --years 2019 2020
    .venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py labels --years 2019 2020 2023
    .venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py copy2023
    KERNEL_S2_SOURCE=earthsearch KERNEL_NO_MANIFEST=1 AGENT_ID=cc-daniel \\
        .venv/Scripts/python.exe -m kernelag.s2_series --fields data/labels/qcm_2019.parquet --cells 0 --parallel 6
    .venv/Scripts/python.exe -I test_models/fieldMultiYear/data_build.py check
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))   # runs as a plain script (also under python -I) from the repo root

from kernelag.paths import data_dir  # noqa: E402
from kernelag.quebec import FILE_URL, LOWERCASE_V_YEARS, MAIZE_GROUPS, label_parcels  # noqa: E402
from kernelag.s2_series import CELL_KM, assign_cells  # noqa: E402

ALL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
CELL_CRS = "EPSG:32618"        # the zone assign_cells chose for the whole 2023 label table
REFERENCE_CELL = "79_515"      # quebec_maize_2023's series cell
REUSED_YEAR = 2023             # built from the published 2023 tables, not downloaded again
COLUMNS = ["field_id", "parcel_id", "year", "label", "hectares", "heat_units", "cell", "geometry"]


def file_url(year: int) -> str:
    return FILE_URL.format(v="v" if year in LOWERCASE_V_YEARS else "V", year=year)


def raw_path(year: int) -> Path:
    return data_dir() / "raw" / "quebec" / Path(file_url(year)).name


def labels_path(year: int) -> Path:
    return data_dir() / "labels" / f"qcm_{year}.parquet"


def series_dir(year: int) -> Path:
    return data_dir() / "s2_series" / f"qcm_{year}"


# ------------------------------------------------------------------------------------------------ areas


def cell_ids(fields) -> pd.Series:
    """10 km cell of each parcel, exactly as assign_cells computes it, but always in EPSG:32618.

    assign_cells picks the UTM zone from the table's own extent; a table of only these 17 cells could
    resolve to a different zone, so the zone is fixed here to the one the 2023 cells were computed in.
    """
    utm = fields.to_crs(CELL_CRS)
    centre = utm.geometry.representative_point()
    size = CELL_KM * 1000
    cells = (centre.x // size).astype(int).astype(str) + "_" + (centre.y // size).astype(int).astype(str)
    return pd.Series(cells.to_numpy(), index=fields.index)


def area_cells() -> list[str]:
    """The 17 cells: 79_515 plus qc_regions_2023's 16."""
    import geopandas as gpd

    regions = gpd.read_parquet(data_dir() / "labels" / "qc_regions_2023.parquet")
    cells = sorted(set(regions["cell"].astype(str)) | {REFERENCE_CELL})
    if len(cells) != 17:
        raise ValueError(f"expected 17 cells, found {len(cells)}: {cells}")
    return cells


def verify_cells() -> dict:
    """Recompute the 2023 cells (assign_cells on the whole table, and cell_ids) and match qc_regions_2023."""
    import geopandas as gpd

    whole = gpd.read_parquet(data_dir() / "labels" / "quebec_maize_2023.parquet")
    regions = gpd.read_parquet(data_dir() / "labels" / "qc_regions_2023.parquet")
    utm = assign_cells(whole)
    recomputed = pd.Series(utm["cell"].to_numpy(), index=whole["field_id"].astype(str).to_numpy())
    mine = pd.Series(cell_ids(whole).to_numpy(), index=whole["field_id"].astype(str).to_numpy())
    published = pd.Series(regions["cell"].astype(str).to_numpy(), index=regions["field_id"].astype(str).to_numpy())
    result = {
        "assign_cells_crs": str(utm.crs.to_string()),
        "qc_regions_rows": len(published),
        "assign_cells_matches_qc_regions": int((recomputed.reindex(published.index) == published).sum()),
        "cell_ids_matches_assign_cells": int((mine == recomputed).sum()),
        "whole_2023_rows": len(whole),
        "reference_cell_rows": int((recomputed == REFERENCE_CELL).sum()),
    }
    in_regions = recomputed[recomputed.isin(set(published))]
    result["qc_regions_is_every_parcel_of_its_cells"] = bool(
        set(in_regions.index) == set(published.index))
    return result


# --------------------------------------------------------------------------------------------- download


def download(year: int, force: bool = False) -> tuple[Path | None, int | str]:
    """Fetch one year's zip with the requests library's default headers. Returns (path or None, HTTP status)."""
    import requests

    target = raw_path(year)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and zipfile.is_zipfile(target) and not force:
        return target, "cached"
    url = file_url(year)
    unfinished = target.with_suffix(".part")
    with requests.get(url, stream=True, timeout=120) as response:
        if response.status_code != 200:
            return None, response.status_code
        expected = int(response.headers.get("Content-Length") or 0)
        with open(unfinished, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
    size = unfinished.stat().st_size
    if expected and size != expected:
        unfinished.unlink()
        raise OSError(f"{url}: got {size} bytes, server said {expected}")
    if not zipfile.is_zipfile(unfinished):
        unfinished.unlink()
        raise OSError(f"{url}: not a zip file")
    os.replace(unfinished, target)
    return target, 200


# ----------------------------------------------------------------------------------------------- labels


def spatial_layer(zip_path: Path) -> str:
    """The GDAL path of the parcel layer inside the zip (shapefile, GeoPackage or file geodatabase)."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    layers = [n for n in names if n.lower().endswith((".shp", ".gpkg"))]
    gdbs = sorted({n.split(".gdb/")[0] + ".gdb" for n in names if ".gdb/" in n.lower()})
    found = layers or gdbs
    if len(found) != 1:
        raise FileNotFoundError(f"{zip_path.name}: expected one spatial layer, found {found}")
    return f"zip://{zip_path.as_posix()}!{found[0]}"


def read_maize(zip_path: Path, year: int):
    """kernelag.quebec.read_maize_parcels, with the layer found the same way for every year's packaging."""
    import geopandas as gpd

    groups = ", ".join(f"'{g}'" for g in MAIZE_GROUPS)
    parcels = gpd.read_file(spatial_layer(zip_path), where=f"GROPRO IN ({groups})")
    return label_parcels(parcels, year).to_crs("EPSG:4326")


def build_labels(year: int, cells: list[str], force: bool = False) -> pd.DataFrame | None:
    """Label table for one year, restricted to the 17 cells. Returns the table, or None if already there."""
    import geopandas as gpd

    target = labels_path(year)
    if target.exists() and not force:
        print(f"{target.name} exists; use --force to rebuild")
        return gpd.read_parquet(target)
    if year == REUSED_YEAR:
        labeled = gpd.read_parquet(data_dir() / "labels" / "quebec_maize_2023.parquet")
    else:
        zip_path = raw_path(year)
        if not zip_path.exists():
            raise FileNotFoundError(f"{zip_path} missing; run the download step first")
        labeled = read_maize(zip_path, year)
    labeled = labeled.assign(cell=cell_ids(labeled))
    kept = labeled[labeled["cell"].isin(cells)].copy()
    kept["field_id"] = kept["field_id"].astype(str)
    kept["parcel_id"] = kept["parcel_id"].astype(str)
    if not kept["field_id"].is_unique:
        raise ValueError(f"{year}: field_id is not unique ({kept['field_id'].duplicated().sum()} duplicates)")
    kept = kept[COLUMNS].sort_values(["cell", "field_id"]).reset_index(drop=True)
    kept = gpd.GeoDataFrame(kept, geometry="geometry", crs="EPSG:4326")
    target.parent.mkdir(parents=True, exist_ok=True)
    unfinished = target.with_suffix(".part")
    kept.to_parquet(unfinished)
    os.replace(unfinished, target)
    print(f"{year}: {len(labeled)} labeled maize parcels in Quebec, {len(kept)} in the 17 cells -> {target}")
    return kept


def copy_2023_series(cells: list[str], force: bool = False) -> None:
    """2023 series: copies of the published per-cell files (79_515 from quebec_maize_2023, the rest qc_regions)."""
    out = series_dir(REUSED_YEAR)
    out.mkdir(parents=True, exist_ok=True)
    for cell in cells:
        source_set = "quebec_maize_2023" if cell == REFERENCE_CELL else "qc_regions_2023"
        source = data_dir() / "s2_series" / source_set / f"{cell}_{REUSED_YEAR}.csv"
        target = out / source.name
        if target.exists() and not force:
            continue
        shutil.copyfile(source, target)
    print(f"copied {len(cells)} 2023 cell files into {out}")


# ---------------------------------------------------------------------------------------------- reports


def label_summary(years: list[int], cells: list[str]) -> pd.DataFrame:
    """Parcels and hectares per year and class, from the written label files."""
    import geopandas as gpd

    rows = []
    for year in years:
        path = labels_path(year)
        if not path.exists():
            rows.append({"year": year, "status": "UNCOMPUTED (no label file)"})
            continue
        table = gpd.read_parquet(path)
        counts = table.groupby("label")["hectares"].agg(["size", "sum"])
        rows.append({
            "year": year, "status": "ok", "parcels": len(table),
            "grain": int(counts["size"].get("grain", 0)), "silage": int(counts["size"].get("silage", 0)),
            "grain_ha": round(float(counts["sum"].get("grain", 0.0))),
            "silage_ha": round(float(counts["sum"].get("silage", 0.0))),
            "cells_with_parcels": int(table["cell"].nunique()),
            "missing_cells": ",".join(sorted(set(cells) - set(table["cell"]))) or "-",
            "field_id_unique": bool(table["field_id"].is_unique),
        })
    return pd.DataFrame(rows)


def series_summary(years: list[int], cells: list[str]) -> pd.DataFrame:
    """Per year: cell files present, field-dates, fields with a series and labeled fields without one."""
    import geopandas as gpd

    rows = []
    for year in years:
        folder = series_dir(year)
        if not labels_path(year).exists():
            rows.append({"year": year, "status": "UNCOMPUTED (no label file)"})
            continue
        labels = gpd.read_parquet(labels_path(year))
        files = {cell: folder / f"{cell}_{year}.csv" for cell in cells}
        present = {cell: path for cell, path in files.items() if path.exists()}
        parts = [pd.read_csv(path) for path in present.values()]
        series = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["field_id", "date"])
        with_series = set(series["field_id"].astype(str))
        empty = [cell for cell, path in present.items() if len(pd.read_csv(path, usecols=["field_id"])) == 0]
        rows.append({
            "year": year, "status": "ok" if len(present) == len(cells) and not empty else "INCOMPLETE",
            "cell_files": f"{len(present)}/{len(cells)}",
            "missing_cells": ",".join(sorted(set(cells) - set(present))) or "-",
            "empty_cells": ",".join(empty) or "-",
            "field_dates": len(series), "dates": int(series["date"].nunique()) if len(series) else 0,
            "fields_with_series": len(with_series), "labeled_fields": len(labels),
            "labeled_without_series": int((~labels["field_id"].astype(str).isin(with_series)).sum()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["verify", "download", "labels", "copy2023", "summary", "check"])
    parser.add_argument("--years", type=int, nargs="+", default=ALL_YEARS)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    pd.set_option("display.width", 200)

    if args.step == "verify":
        for key, value in verify_cells().items():
            print(f"{key}: {value}")
        print(f"cells: {area_cells()}")
        return
    cells = area_cells()
    if args.step == "download":
        for year in args.years:
            if year == REUSED_YEAR:
                print(f"{year}: reused from quebec_maize_2023, not downloaded")
                continue
            try:
                path, status = download(year, args.force)
            except Exception as error:   # report and go on to the next year; nothing is guessed
                print(f"{year}: FAILED {type(error).__name__}: {error}", flush=True)
                continue
            if path is None:
                print(f"{year}: UNCOMPUTED (HTTP {status} for {file_url(year)})", flush=True)
            else:
                print(f"{year}: {status} {path} ({path.stat().st_size} bytes)", flush=True)
    elif args.step == "labels":
        for year in args.years:
            build_labels(year, cells, args.force)
        print(label_summary(args.years, cells).to_string(index=False))
    elif args.step == "copy2023":
        copy_2023_series(cells, args.force)
    elif args.step == "summary":
        print(label_summary(args.years, cells).to_string(index=False))
    elif args.step == "check":
        print(series_summary(args.years, cells).to_string(index=False))


if __name__ == "__main__":
    main()
