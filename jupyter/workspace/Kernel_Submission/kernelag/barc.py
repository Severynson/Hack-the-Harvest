"""The organizers' labeled Maryland fields (USDA Beltsville research farm), one row per field-year.

Input: ``04_Evaluation/BARC_Corn.2021-2023.gpkg`` from the starter kit: 83 field polygons with a
``Corn_<year>`` column that is ``Grain``, ``Silage`` or blank. Blank means unlabeled, not a negative.

These 44 labeled field-years (32 grain, 12 silage) are Kernel's field-level TEST set.
They are never used to fit a model.

Output: ``data/labels/barc_2021_2023.parquet``
    field_id, year, label (grain or silage), acres, geometry (EPSG:4326)

Run: ``python -m kernelag.barc``
"""

from __future__ import annotations

import pandas as pd

from kernelag.paths import data_dir, kit_dir, record_in_manifest

KIT_FILE = "04_Evaluation/BARC_Corn.2021-2023.gpkg"
YEARS = [2021, 2022, 2023]
SOURCE_URL = "https://doi.org/10.5281/zenodo.8087301"


def labeled_field_years():
    """Long table of the labeled field-years only."""
    import geopandas as gpd

    fields = gpd.read_file(kit_dir() / KIT_FILE)
    parts = []
    for year in YEARS:
        labeled = fields[fields[f"Corn_{year}"].notna()]
        part = labeled[["geometry"]].copy()
        part["field_id"] = labeled["OBJECTID"].astype(int).to_numpy()
        part["year"] = year
        part["label"] = labeled[f"Corn_{year}"].str.lower().to_numpy()
        part["acres"] = labeled["ACRES"].astype(float).round(2).to_numpy()
        parts.append(part)
    table = pd.concat(parts, ignore_index=True)[["field_id", "year", "label", "acres", "geometry"]]
    return table.to_crs("EPSG:4326")


def main() -> None:
    target = data_dir() / "labels" / "barc_2021_2023.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    table = labeled_field_years()
    table.to_parquet(target)
    record_in_manifest(target, SOURCE_URL)
    print(f"{len(table)} labeled field-years -> {target}")
    print(table.groupby(["year", "label"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
