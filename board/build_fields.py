"""Bake the USDA Maryland test fields (with their Sentinel-2 greenness and the caveman call) into board/fields_md.json,
and the county winter table into board/winter_vegetation.json. Run once from the repo root of the `main` branch:

    python board/build_fields.py data/satellite/barc_ndvi_2021_2023.parquet data/BARC_Corn.2021-2023.gpkg data/regions/winter_vegetation.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from board.fieldrule import result  # noqa: E402

HERE = Path(__file__).resolve().parent


def main(ndvi_path: str, gpkg_path: str, winter_path: str) -> None:
    nd = pd.read_parquet(ndvi_path)
    nd["year"] = pd.to_datetime(nd["date"]).dt.year
    barc = gpd.read_file(gpkg_path).to_crs(4326)
    lab = barc.melt(id_vars=["OBJECTID", "ACRES", "geometry"], value_vars=["Corn_2021", "Corn_2022", "Corn_2023"], value_name="label")
    lab = lab[lab["label"].isin(["Grain", "Silage"])]
    fields = []
    for _, r in lab.iterrows():
        fid, year = f"barc_{r['OBJECTID']}", int(r["variable"][-4:])
        out = result(nd[(nd["field_id"] == fid) & (nd["year"] == year)], True)
        geom = r["geometry"].simplify(0.00003)
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        c = r["geometry"].centroid
        fields.append({"id": fid, "field": int(r["OBJECTID"]), "year": year, "truth": r["label"].lower(), "acres": round(float(r["ACRES"]), 1),
                       "lon": round(c.x, 5), "lat": round(c.y, 5),
                       "outline": [[[round(x, 5), round(y, 5)] for x, y in p.exterior.coords] for p in polys], **out})
    right = sum(f["call"] == f["truth"] for f in fields)
    (HERE / "fields_md.json").write_text(json.dumps({"source": "USDA ARS Beltsville Agricultural Research Center (organizers' labels); Sentinel-2 L2A via Microsoft Planetary Computer",
                                                    "correct": right, "n": len(fields), "fields": fields}, separators=(",", ":")))
    w = pd.read_csv(winter_path, dtype={"region_id": str})
    (HERE / "winter_vegetation.json").write_text(json.dumps({r: bool(v) for r, v in zip(w["region_id"], w["winter_vegetation"])}, separators=(",", ":")))
    print(f"{right}/{len(fields)} correct; wrote fields_md.json and winter_vegetation.json")


if __name__ == "__main__":
    main(*sys.argv[1:4])
