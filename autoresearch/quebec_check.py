"""
Out-of-region test of the caveman model (train.py) on Quebec 2023 corn parcels.

Labels: data/labels/quebec_maize_2023.parquet (FADQ declared parcels, grain vs silage), pulled by cc-varun.
Sentinel-2 series: extracted here with the same code as prepare.py (10 m erosion, SCL mask, field medians),
1 Mar - 20 Dec 2023, for every corn parcel in three 0.1-degree cells in UTM zone 18.

Two tests:
  A. transfer: cut-offs fitted on all 44 BARC field-years, applied unchanged to Quebec.
  B. refit:    cut-offs fitted on two Quebec cells, tested on the third (leave one cell out).

Run (main checkout must hold data/labels/quebec_maize_2023.parquet):
    uv run quebec_check.py [--labels PATH]
Not part of the frozen harness; does not change prepare.py or train.py.
"""

import argparse
import contextlib
import io
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

import prepare as P

with contextlib.redirect_stdout(io.StringIO()):
    import train as T  # importing runs the BARC evaluation once; its printout is discarded

CELLS = {  # (lon, lat) of the south-west corner of each 0.1-degree cell
    "saint_hyacinthe": (-72.7, 45.6),
    "nicolet": (-72.6, 46.0),
    "haut_saint_laurent": (-74.1, 45.1),
}
YEAR = 2023
OUT_DIR = P.CACHE_DIR / "quebec"
DEFAULT_LABELS = Path(__file__).resolve().parents[2] / "hack-the-harvest" / "data" / "labels" / "quebec_maize_2023.parquet"


def cell_parcels(labels_path: Path) -> gpd.GeoDataFrame:
    q = gpd.read_parquet(labels_path)
    pt = q.geometry.representative_point()
    q["cx"], q["cy"] = np.floor(pt.x * 10 + 1e-9) / 10, np.floor(pt.y * 10 + 1e-9) / 10
    parts = []
    for name, (cx, cy) in CELLS.items():
        sel = q[np.isclose(q["cx"], cx) & np.isclose(q["cy"], cy)].copy()
        sel["cell"] = name
        parts.append(sel)
    out = pd.concat(parts, ignore_index=True)
    out = out.rename(columns={"field_id": "OBJECTID"})
    out["OBJECTID"] = out["OBJECTID"].astype("int64")
    out["year"] = YEAR
    out["y"] = (out["label"] == "silage").astype(int)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=q.crs)


def pull_cell(name: str, parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    path = OUT_DIR / f"{name}_{YEAR}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    fields_utm = parcels[["OBJECTID", "geometry"]].to_crs(P.UTM_CRS)
    search = P._search_items

    def zone18_only(bbox, year):
        return [it for it in search(bbox, year) if str(it.properties.get("proj:code", it.properties.get("proj:epsg"))).endswith("32618")]

    P._search_items, P.YEARS, P.SCENE_DIR = zone18_only, (YEAR,), OUT_DIR / f"scenes_{name}"
    try:
        ts = P.build_timeseries(fields_utm)
    finally:
        P._search_items = search
    ts.to_parquet(path)
    return ts


def scores(y, p):
    return P._scores(np.asarray(y), np.asarray(p))


def fit(ts, lab):
    return T.fit(ts, lab)


def predict(ts, keys, cuts):
    """Prediction plus which rules fired, for the per-rule report."""
    f = T.featurize(ts, keys)
    out = f[["OBJECTID", "year"]].copy()
    fired = np.zeros(len(f), bool)
    for r, c in cuts.items():
        hit = np.nan_to_num(f[r].to_numpy(float), nan=np.inf) < c
        out[f"r_{r}"] = hit
        fired |= hit
    out["pred"] = fired.astype(int)
    return out


def line(name, s):
    return (f"{name:26s} F1 {s['silage_f1']:.3f}  P {s['silage_precision']:.3f}  R {s['silage_recall']:.3f}  "
            f"acc {s['accuracy']:.3f}  bal {s['balanced_acc']:.3f}  tp={s['tp']} fp={s['fp']} fn={s['fn']} tn={s['tn']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    parcels = cell_parcels(args.labels)
    print(parcels.groupby("cell")["y"].agg(parcels="size", silage="sum").to_string())
    ts = pd.concat([pull_cell(n, g) for n, g in parcels.groupby("cell")], ignore_index=True)
    lab = pd.DataFrame(parcels[["OBJECTID", "year", "y", "cell"]])
    lab["group"] = lab["cell"]

    # A. transfer from BARC
    bts, blab = P.load_data()
    cuts = fit(bts, blab)
    pa = predict(ts, lab, cuts).merge(lab, on=["OBJECTID", "year"])
    print(f"\nA. BARC cut-offs {cuts} applied to Quebec")
    print(line("all cells", scores(pa["y"], pa["pred"])))
    for c, g in pa.groupby("cell"):
        print(line(c, scores(g["y"], g["pred"])))
    print("rule firing (share of parcels):", {k: round(float(pa[k].mean()), 3) for k in pa.columns if k.startswith("r_")})

    # B. refit on Quebec, leave one cell out
    preds = []
    for c in CELLS:
        tr, te = lab[lab["cell"] != c], lab[lab["cell"] == c]
        u = fit(ts[ts["OBJECTID"].isin(tr["OBJECTID"])], tr)
        p = predict(ts[ts["OBJECTID"].isin(te["OBJECTID"])], te, u).merge(te, on=["OBJECTID", "year"])
        preds.append(p)
        print(f"   held out {c}: {u}")
    pb = pd.concat(preds)
    print("\nB. Cut-offs refit on Quebec (leave one cell out)")
    print(line("all cells", scores(pb["y"], pb["pred"])))
    for c, g in pb.groupby("cell"):
        print(line(c, scores(g["y"], g["pred"])))

    feats = T.featurize(ts, lab).merge(lab, on=["OBJECTID", "year"])
    feats["late_ndvi"] = -feats["late_ndvi_neg"]
    print("\nFeature medians by class (Quebec):")
    print(feats.groupby("y")[["drop_days", "late_ndvi"]].median().rename(index={0: "grain", 1: "silage"}).round(3).to_string())
    feats.to_parquet(OUT_DIR / f"features_{YEAR}.parquet")
