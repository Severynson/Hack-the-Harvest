"""Distance-to-dairy features (feature group "dairydist"): how close each maize field is to registered dairy sites.

Why: silage is about two-thirds water, so it is grown close to the cows that eat it. NDSU Extension says
the opportunities are "limited to farmers operating within a few miles of the new dairy", Missouri Extension
would not haul it past 20 miles, and a peer-reviewed transport study puts the economic limit at 18 km
(DOCS/research/gap_dairy_feedlot_points.md, section 4). dairy_prior.md (sections 4.3 and 8) gives silage-shed
radii of 1.5 to 8 km for herds of 300 to 10,000 cows and a 5 km kernel cut at 25 km. A field close to many
dairy farms should be more often silage than a field far from any.

The training set is Quebec and the test set is one Maryland research farm, so the facility source has to
cover Quebec. The source used is the Quebec property assessment roll (role d'evaluation fonciere, MAMH,
2023, CC BY 4.0): every evaluation unit carries a predominant-use code (CUBF, field RL0105A) and a
georeferenced point. CUBF 8122 is "Elevage de bovins laitiers" (NAICS 112120; legacy code 8150) and 8121 is
beef cattle, including the rearing of dairy replacement heifers (legacy 8161), per the official CUBF list.

    dairy site = a 2023 roll unit coded 8122 or 8150, with a building value (RL0403A) above zero and a
                 point that was not rejected (rejet = 0). A farm with several units counts several times.

Pre-registered model features (fixed in this file before any class comparison was computed):
    dairydist_d_dairy_km     km from the field's representative point to the nearest dairy site
    dairydist_n_dairy_18km   number of dairy sites within 18 km (the Manzone et al. economic limit)
Pre-registered benchmark rule:
    dairydist_rule_dairy_1p5km  1 when dairydist_d_dairy_km <= 1.5 km (the smallest silage-shed radius in
                                dairy_prior.md section 4.3: 300 cows, corn on 25% of the land), else 0
Descriptive only (not model features):
    dairydist_d_dairy_any_km     nearest dairy-coded unit with or without buildings (land a dairy farm owns)
    dairydist_d_beef_km, dairydist_n_beef_18km   the same two measures for beef-coded units with buildings
    dairydist_mb_sites_per_ha    local mass balance (dairy_prior.md section 8.2): sum of exp(-d / 5 km) over
                                 dairy sites, divided by the same kernel sum of maize hectares (every
                                 parcel of data/labels/quebec_maize_2023.parquet, labels not read), d <= 25 km
    dairydist_ct_d_dairy_km, dairydist_ct_d_cattle_km, dairydist_ct_n_cattle_18km
                                 Climate TRACE cattle operations (API v7, CC BY 4.0): nearest mature-dairy
                                 point, nearest cattle point of any kind, cattle points within 18 km

Head counts are UNCOMPUTED everywhere: the roll has no herd size, and every Quebec Climate TRACE row carries
one constant capacity per type (an imputed default, not a measurement).

Maryland (barc_2021_2023) is a test set. No public registry of dairy sites comparable to the Quebec roll
exists for it: Climate TRACE has 39 Maryland dairies from state permit lists, the research farm's own herd
is not among them, and the nearest one is about 60 km away. The roll-based columns (both model features and
the rule) are therefore NaN for Maryland, and the harness fills them with its median imputer. The Climate
TRACE columns are built for every dataset. Nothing here reads Maryland labels.

Inputs:
    data/labels/<dataset>.parquet       geometry and ids (Quebec labels only for the class summary)
    https://donneesouvertes.affmunqc.net/role/ROLE2023_FGDB.zip  (407 MB, downloaded once to --cache-dir;
                                        only the cattle-coded units are kept, in data/qc_role_2023_cattle_sites.csv)
    https://api.climatetrace.org/v7/sources  (cattle operations per GADM region, cached in data/)
Outputs (test_models/featureTests/dairy_distance/out/):
    features.csv               dataset, field_id, year, dairydist_* columns (missing stays NaN)
    meta.json                  the feature-group contract plus source counts and checks
    quebec_class_summary.csv   class medians, means and univariate ROC AUC, Quebec labels only
    quebec_by_cell.csv         the same per 10 km Quebec cell (within-region signal, not geography)

Run from the repo root:
    .venv/Scripts/python.exe test_models/featureTests/dairy_distance/build.py [--datasets ...] [--offline]
        [--cache-dir DIR] [--refresh]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:   # run as a plain script from anywhere: make ``kernelag`` importable
    sys.path.insert(0, str(REPO))

GROUP = "dairydist"
MODEL_FEATURES = ["dairydist_d_dairy_km", "dairydist_n_dairy_18km"]   # pre-registered; never changed after evaluation
RULE_COLUMN = "dairydist_rule_dairy_1p5km"
RULE_KM = 1.5
DESCRIPTIVE = ["dairydist_d_dairy_any_km", "dairydist_d_beef_km", "dairydist_n_beef_18km", "dairydist_mb_sites_per_ha",
               "dairydist_ct_d_dairy_km", "dairydist_ct_d_cattle_km", "dairydist_ct_n_cattle_18km"]
ROLE_COLUMNS = [*MODEL_FEATURES, RULE_COLUMN, "dairydist_d_dairy_any_km", "dairydist_d_beef_km",
                "dairydist_n_beef_18km", "dairydist_mb_sites_per_ha"]
CT_COLUMNS = ["dairydist_ct_d_dairy_km", "dairydist_ct_d_cattle_km", "dairydist_ct_n_cattle_18km"]
FEATURE_COLUMNS = [*MODEL_FEATURES, RULE_COLUMN, *DESCRIPTIVE]
KEYS = ["dataset", "field_id", "year"]
DEFAULT_DATASETS = ["quebec_maize_2023", "qc_regions_2023", "barc_2021_2023"]
QUEBEC_DATASETS = ["quebec_maize_2023", "qc_regions_2023"]   # the only labels a class comparison may read
QUEBEC_TRAIN_CELL = "79_515"     # the cell of quebec_maize_2023 that has Sentinel-2 series

CRS = "EPSG:32618"     # UTM 18N: the grid of the Quebec label files and Maryland's own zone; <0.6% scale error
RADIUS_KM = 18.0       # Manzone et al. 2020: economic limit for hauling maize silage
KERNEL_KM, KERNEL_CUT_KM = 5.0, 25.0   # dairy_prior.md section 8.3 and gap_dairy_feedlot_points.md section 5

ROLE_YEAR = 2023       # the label year; the roll in force that year
ROLE_URL = f"https://donneesouvertes.affmunqc.net/role/ROLE{ROLE_YEAR}_FGDB.zip"
ROLE_SITES = HERE / "data" / f"qc_role_{ROLE_YEAR}_cattle_sites.csv"
CUBF_KIND = {"8122": "dairy", "8150": "dairy", "8121": "beef", "8161": "beef"}   # current and legacy codes

CT_URL = "https://api.climatetrace.org/v7/sources"
CT_SUBSECTOR = "enteric-fermentation-cattle-operation"
CT_PAGE = 100
CT_MAX_PAGES = 30
# GADM ids (alphabetical numbering, checked against the row names): the province or state of the fields plus
# every neighbour close enough to hold the nearest point.
CT_REGIONS = {
    "quebec": ["CAN.11_1", "USA.46_1", "USA.30_1", "USA.20_1"],                # Quebec, Vermont, New Hampshire, Maine
    "maryland": ["USA.21_1", "USA.47_1", "USA.39_1", "USA.8_1", "USA.49_1", "USA.9_1"],   # MD, VA, PA, DE, WV, DC
}
REGION_OF = {"quebec_maize_2023": "quebec", "qc_regions_2023": "quebec", "barc_2021_2023": "maryland"}
US_BORDER_LAT = 45.0   # the Quebec - Vermont / New Hampshire / New York line runs close to the 45th parallel

MARYLAND_NOTE = ("roll-based columns UNCOMPUTED (NaN): no public registry of dairy sites comparable to the Quebec "
                 "assessment roll covers Maryland; Climate TRACE lists 39 Maryland dairies from state permit lists, "
                 "not the research farm's own herd. Climate TRACE columns are built.")


# ---------------------------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------------------------
def download(url: str, path: Path) -> Path:
    """Stream one documented public file to ``path`` (kept for later runs)."""
    import requests

    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(part, "wb") as out:
            out.writelines(response.iter_content(chunk_size=1 << 20))
    part.replace(path)
    return path


def select_role_units(units: pd.DataFrame) -> pd.DataFrame:
    """Cattle-coded roll units with their kind and building value; codes outside CUBF_KIND are dropped."""
    out = units.assign(cubf=units["rl0105a"].astype(str).str.strip())
    out = out[out["cubf"].isin(CUBF_KIND)].copy()
    out["kind"] = out["cubf"].map(CUBF_KIND)
    out["building_value"] = pd.to_numeric(out["rl0403a"], errors="coerce")
    out["land_m2"] = pd.to_numeric(out["rl0302a"], errors="coerce")
    return out[["id_provinc", "code_mun", "cubf", "kind", "building_value", "land_m2"]]


def read_role_sites(cache_dir: Path, refresh: bool, offline: bool) -> pd.DataFrame:
    """Cattle-coded units of the Quebec roll with lon/lat (NAD83). Cached as a small CSV in data/."""
    if ROLE_SITES.exists() and not refresh:
        return pd.read_csv(ROLE_SITES, dtype={"id_provinc": str, "code_mun": str, "cubf": str})
    import pyogrio

    archive = cache_dir / Path(ROLE_URL).name
    if not archive.exists():
        if offline:
            raise FileNotFoundError(f"{archive} missing and --offline set")
        print(f"downloading {ROLE_URL} -> {archive}", flush=True)
        download(ROLE_URL, archive)
    gdb = f"/vsizip/{archive.as_posix()}/Role_{ROLE_YEAR}.gdb"
    # The unit table has the use code; the point layer has the location; id_provinc joins them one to one.
    codes = "', '".join(CUBF_KIND)
    units = pyogrio.read_dataframe(gdb, layer="B05EX1_B05V_UNITE_EVALN", read_geometry=False,
                                   columns=["id_provinc", "code_mun", "rl0105a", "rl0302a", "rl0403a"],
                                   where=f"rl0105a IN ('{codes}')")
    points = pyogrio.read_dataframe(gdb, layer="rol_unite_p", columns=["id_provinc", "rejet"])
    points = pd.DataFrame({"id_provinc": points["id_provinc"], "rejet": points["rejet"],
                           "lon": points.geometry.x.round(6), "lat": points.geometry.y.round(6)})   # NAD83
    sites = select_role_units(units).merge(points, on="id_provinc", how="inner")
    ROLE_SITES.parent.mkdir(parents=True, exist_ok=True)
    sites.to_csv(ROLE_SITES, index=False)
    print(f"role {ROLE_YEAR}: {len(units)} cattle-coded units, {len(sites)} with a point -> {ROLE_SITES}", flush=True)
    return sites


def role_point_sets(sites: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The three point sets used: dairy sites (buildings), all dairy-coded units, beef sites (buildings)."""
    located = sites[sites["rejet"].fillna(1).astype(int) == 0]   # a rejected point is not trusted for distance
    built = located["building_value"].fillna(0) > 0
    return {"dairy": located[(located["kind"] == "dairy") & built],
            "dairy_any": located[located["kind"] == "dairy"],
            "beef": located[(located["kind"] == "beef") & built]}


def ct_path(gadm: str) -> Path:
    return HERE / "data" / f"climatetrace_cattle_{gadm}.csv"


def parse_ct(rows: list[dict], gadm: str) -> pd.DataFrame:
    """Climate TRACE v7 source rows -> gadm, id, name, kind (dairy/beef), lat, lon, capacity, year."""
    kinds = {"enteric_fermentation_maturedairycattle": "dairy", "enteric_fermentation_otherbeefcattle": "beef"}
    out = [{"gadm": gadm, "id": r.get("id"), "name": r.get("name"),
            "kind": kinds.get(r.get("assetType"), "other"),
            "lat": (r.get("centroid") or {}).get("latitude"), "lon": (r.get("centroid") or {}).get("longitude"),
            "capacity": r.get("capacity"), "year": r.get("year")} for r in rows]
    return pd.DataFrame(out, columns=["gadm", "id", "name", "kind", "lat", "lon", "capacity", "year"])


def fetch_ct(gadm: str) -> pd.DataFrame:
    """Every cattle operation of one GADM region, 100 per request, one request per second."""
    import requests

    rows: list[dict] = []
    for page in range(CT_MAX_PAGES):
        params = {"gadmId": gadm, "subsectors": CT_SUBSECTOR, "limit": CT_PAGE, "offset": page * CT_PAGE}
        response = requests.get(CT_URL, params=params, timeout=90)
        response.raise_for_status()
        batch = response.json() or []   # an offset past the end returns null
        rows += batch
        if len(batch) < CT_PAGE:
            break
        time.sleep(1.0)
    return parse_ct(rows, gadm)


def read_ct(region: str, refresh: bool, offline: bool) -> tuple[pd.DataFrame | None, str]:
    """Climate TRACE points for a region (cached per GADM id). Returns (points or None, problem note)."""
    parts, missing = [], []
    for gadm in CT_REGIONS[region]:
        path = ct_path(gadm)
        if path.exists() and not refresh:
            parts.append(pd.read_csv(path))
            continue
        if offline:
            missing.append(gadm)
            continue
        try:
            table = fetch_ct(gadm)
        except Exception as error:   # noqa: BLE001 - beta API: any failure leaves the columns UNCOMPUTED
            missing.append(f"{gadm} ({type(error).__name__})")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(path, index=False)
        parts.append(table)
        time.sleep(1.0)
    if missing:
        return None, f"Climate TRACE unavailable for {', '.join(missing)}"
    return pd.concat(parts, ignore_index=True), ""


def modal_capacity_share(points: pd.DataFrame) -> dict:
    """Share of rows at the most common capacity, per region and kind: near 1.0 means an imputed constant."""
    out = {}
    for (gadm, kind), part in points.groupby(["gadm", "kind"]):
        counts = part["capacity"].round(2).value_counts()
        out[f"{gadm}/{kind}"] = {"rows": len(part), "modal_capacity": float(counts.index[0]),
                                 "modal_share": round(float(counts.iloc[0] / len(part)), 3)}
    return out


# ---------------------------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------------------------
def project_lonlat(lon, lat, source_crs: str = "EPSG:4326") -> np.ndarray:
    """(n, 2) metres in CRS from lon/lat arrays."""
    from pyproj import Transformer

    if len(lon) == 0:
        return np.empty((0, 2))
    to_crs = Transformer.from_crs(source_crs, CRS, always_xy=True)
    x, y = to_crs.transform(np.asarray(lon, float), np.asarray(lat, float))
    return np.c_[x, y]


def nearest_km(fields_xy: np.ndarray, sites_xy: np.ndarray) -> np.ndarray:
    """Distance in km from each field point to the nearest site; NaN when there are no sites."""
    from scipy.spatial import cKDTree

    if len(sites_xy) == 0 or len(fields_xy) == 0:
        return np.full(len(fields_xy), np.nan)
    distance, _ = cKDTree(sites_xy).query(fields_xy)
    return distance / 1000.0


def count_within(fields_xy: np.ndarray, sites_xy: np.ndarray, radius_km: float) -> np.ndarray:
    """Number of sites within ``radius_km`` (boundary included) of each field point."""
    from scipy.spatial import cKDTree

    if len(fields_xy) == 0:
        return np.zeros(0)
    if len(sites_xy) == 0:
        return np.zeros(len(fields_xy))
    return cKDTree(sites_xy).query_ball_point(fields_xy, r=radius_km * 1000.0, return_length=True).astype(float)


def kernel_sum(fields_xy: np.ndarray, points_xy: np.ndarray, weights: np.ndarray | None = None,
               scale_km: float = KERNEL_KM, cut_km: float = KERNEL_CUT_KM) -> np.ndarray:
    """Sum over points of weight * exp(-d / scale) for d <= cut, per field point."""
    from scipy.spatial import cKDTree

    weights = np.ones(len(points_xy)) if weights is None else np.asarray(weights, float)
    if len(points_xy) == 0:
        return np.zeros(len(fields_xy))
    tree = cKDTree(points_xy)
    out = np.zeros(len(fields_xy))
    for i, neighbours in enumerate(tree.query_ball_point(fields_xy, r=cut_km * 1000.0)):
        if neighbours:
            d = np.hypot(*(points_xy[neighbours] - fields_xy[i]).T) / 1000.0
            out[i] = float(np.sum(weights[neighbours] * np.exp(-d / scale_km)))
    return out


def field_points(fields) -> np.ndarray:
    """Representative point of each field polygon (always inside it), in CRS metres."""
    centre = fields.to_crs(CRS).geometry.representative_point()
    return np.c_[centre.x.to_numpy(), centre.y.to_numpy()]


# ---------------------------------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------------------------------
def load_fields(dataset: str):
    """Fields of one dataset with field_id as text and a ``cell`` column (Quebec) for the summaries."""
    import geopandas as gpd

    path = REPO / "data" / "labels" / f"{dataset}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")
    fields = gpd.read_parquet(path)
    fields["field_id"] = fields["field_id"].astype(str)
    fields["year"] = fields["year"].astype(int)
    if dataset == "quebec_maize_2023":
        from kernelag.s2_series import assign_cells

        fields = fields.assign(cell=assign_cells(fields)["cell"].to_numpy())
    elif "cell" not in fields.columns:
        fields["cell"] = ""
    return fields


def role_features(fields_xy: np.ndarray, sets: dict[str, np.ndarray], maize_xy: np.ndarray | None,
                  maize_ha: np.ndarray | None) -> pd.DataFrame:
    """Roll-based columns for field points; the mass balance needs the maize parcel layer (else NaN)."""
    out = pd.DataFrame(index=range(len(fields_xy)))
    out["dairydist_d_dairy_km"] = nearest_km(fields_xy, sets["dairy"])
    out["dairydist_n_dairy_18km"] = count_within(fields_xy, sets["dairy"], RADIUS_KM)
    out[RULE_COLUMN] = np.where(np.isnan(out["dairydist_d_dairy_km"]), np.nan,
                                (out["dairydist_d_dairy_km"] <= RULE_KM).astype(float))
    out["dairydist_d_dairy_any_km"] = nearest_km(fields_xy, sets["dairy_any"])
    out["dairydist_d_beef_km"] = nearest_km(fields_xy, sets["beef"])
    out["dairydist_n_beef_18km"] = count_within(fields_xy, sets["beef"], RADIUS_KM)
    if maize_xy is None:
        out["dairydist_mb_sites_per_ha"] = np.nan
    else:
        demand = kernel_sum(fields_xy, sets["dairy"])
        supply = kernel_sum(fields_xy, maize_xy, maize_ha)
        with np.errstate(divide="ignore", invalid="ignore"):
            out["dairydist_mb_sites_per_ha"] = np.where(supply > 0, demand / supply, np.nan)
    return out


def ct_features(fields_xy: np.ndarray, ct_xy: dict[str, np.ndarray] | None) -> pd.DataFrame:
    out = pd.DataFrame(index=range(len(fields_xy)))
    if ct_xy is None:
        for column in CT_COLUMNS:
            out[column] = np.nan
        return out
    out["dairydist_ct_d_dairy_km"] = nearest_km(fields_xy, ct_xy["dairy"])
    out["dairydist_ct_d_cattle_km"] = nearest_km(fields_xy, ct_xy["cattle"])
    out["dairydist_ct_n_cattle_18km"] = count_within(fields_xy, ct_xy["cattle"], RADIUS_KM)
    return out


def ct_point_sets(points: pd.DataFrame | None) -> dict[str, np.ndarray] | None:
    if points is None:
        return None
    points = points.dropna(subset=["lat", "lon"])
    dairy = points[points["kind"] == "dairy"]
    return {"dairy": project_lonlat(dairy["lon"], dairy["lat"]), "cattle": project_lonlat(points["lon"], points["lat"])}


def feature_table(dataset: str, fields, role_xy, maize, ct_xy) -> pd.DataFrame:
    """One row per field-year: keys, every dairydist_* column (NaN where the source does not apply)."""
    xy = field_points(fields)
    quebec = REGION_OF[dataset] == "quebec"
    if quebec and role_xy is not None:
        role = role_features(xy, role_xy, *(maize if maize is not None else (None, None)))
    else:
        role = pd.DataFrame(np.nan, index=range(len(xy)), columns=ROLE_COLUMNS)
    table = pd.concat([role, ct_features(xy, ct_xy)], axis=1)
    table.insert(0, "year", fields["year"].to_numpy())
    table.insert(0, "field_id", fields["field_id"].to_numpy())
    table.insert(0, "dataset", dataset)
    return table[[*KEYS, *FEATURE_COLUMNS]]


# ---------------------------------------------------------------------------------------------
# Descriptive check on Quebec labels only
# ---------------------------------------------------------------------------------------------
def roc_auc(truth: np.ndarray, score: np.ndarray) -> float:
    """ROC AUC with silage (1) as the positive class and higher values scored as silage; NaN rows dropped."""
    from sklearn.metrics import roc_auc_score

    ok = ~np.isnan(score)
    if len(np.unique(truth[ok])) < 2:
        return float("nan")
    return float(roc_auc_score(truth[ok], score[ok]))


EXPECTED = {   # direction of the hypothesis, written down with the features
    "dairydist_d_dairy_km": "lower = silage", "dairydist_n_dairy_18km": "higher = silage",
    RULE_COLUMN: "1 = silage", "dairydist_d_dairy_any_km": "lower = silage", "dairydist_d_beef_km": "lower = silage",
    "dairydist_n_beef_18km": "higher = silage", "dairydist_mb_sites_per_ha": "higher = silage",
    "dairydist_ct_d_dairy_km": "lower = silage", "dairydist_ct_d_cattle_km": "lower = silage",
    "dairydist_ct_n_cattle_18km": "higher = silage",
}


def describe(table: pd.DataFrame, scope: str) -> list[dict]:
    """Class medians, means and univariate AUC per column for one Quebec scope."""
    rows = []
    truth = (table["label"] == "silage").to_numpy(int)
    for column in FEATURE_COLUMNS:
        if column not in table.columns:
            continue
        values = table[column].to_numpy(float)
        ok = ~np.isnan(values)
        if not ok.any():
            continue
        grain, silage = values[ok & (truth == 0)], values[ok & (truth == 1)]
        auc = roc_auc(truth, values)
        rows.append({
            "scope": scope, "feature": column,
            "role": "model" if column in MODEL_FEATURES else ("rule" if column == RULE_COLUMN else "descriptive"),
            "n_grain": len(grain), "n_silage": len(silage), "n_missing": int((~ok).sum()),
            "median_grain": round(float(np.median(grain)), 3) if len(grain) else np.nan,
            "median_silage": round(float(np.median(silage)), 3) if len(silage) else np.nan,
            "mean_grain": round(float(np.mean(grain)), 3) if len(grain) else np.nan,
            "mean_silage": round(float(np.mean(silage)), 3) if len(silage) else np.nan,
            "auc_silage_positive": round(auc, 4),
            "expected": EXPECTED.get(column, ""),
        })
    return rows


def quebec_summaries(labelled: pd.DataFrame, province: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pooled summaries per scope, plus per-cell AUC (within one 10 km cell, regional level is held fixed)."""
    rows: list[dict] = []
    for dataset, part in labelled.groupby("dataset"):
        scope = f"{dataset} cell {QUEBEC_TRAIN_CELL}" if dataset == "quebec_maize_2023" else f"{dataset} (all cells)"
        rows += describe(part, scope)
    if province is not None:
        rows += describe(province, "quebec_maize_2023 all parcels (province)")
    by_cell: list[dict] = []
    for (dataset, cell), part in labelled.groupby(["dataset", "cell"]):
        for row in describe(part, f"{dataset} {cell}"):
            by_cell.append({"dataset": dataset, "cell": cell, **{k: v for k, v in row.items() if k != "scope"}})
    by_cell_table = pd.DataFrame(by_cell)
    if not by_cell_table.empty:
        median = (by_cell_table.groupby("feature")["auc_silage_positive"].median().rename("median_within_cell_auc"))
        rows = [{**row, "median_within_cell_auc": round(float(median.get(row["feature"], np.nan)), 4)}
                if row["scope"].startswith("qc_regions") else row for row in rows]
    return pd.DataFrame(rows), by_cell_table


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def replace_datasets(previous: pd.DataFrame | None, new: list[pd.DataFrame], rebuilt: list[str]) -> pd.DataFrame:
    """Rows of rebuilt datasets replace old ones; other datasets' rows are kept (idempotent partial runs)."""
    keep = [] if previous is None else [previous[~previous["dataset"].isin(rebuilt)]]
    frames = [f for f in [*keep, *new] if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=[*KEYS, *FEATURE_COLUMNS])
    return pd.concat(frames, ignore_index=True).sort_values(KEYS).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS)
    parser.add_argument("--offline", action="store_true", help="use cached sources only; no network")
    parser.add_argument("--refresh", action="store_true", help="re-download the sources even when cached")
    parser.add_argument("--cache-dir", type=Path, default=Path(tempfile.gettempdir()) / "kernel_dairydist",
                        help="where the 407 MB roll archive is kept (outside the repository)")
    args = parser.parse_args()
    import geopandas as gpd

    out_dir = HERE / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    uncomputed: dict[str, str] = {}
    partial: dict[str, str] = {}
    checks: dict = {}

    role_xy = None
    try:
        sites = read_role_sites(args.cache_dir, args.refresh, args.offline)
        sets = role_point_sets(sites)
        role_xy = {k: project_lonlat(v["lon"], v["lat"], "EPSG:4269") for k, v in sets.items()}
        checks["role"] = {"source": ROLE_URL, "year": ROLE_YEAR, "cattle_units_with_point": len(sites),
                          **{f"{k}_points": len(v) for k, v in sets.items()}}
    except Exception as error:   # noqa: BLE001 - missing archive, network or format failure: roll columns stay NaN
        print(f"role unavailable: {type(error).__name__}: {error}")
        checks["role"] = {"source": ROLE_URL, "problem": f"{type(error).__name__}: {error}"}

    ct_cache: dict[str, tuple] = {}
    built, tables, labelled_parts = [], [], []
    maize = None
    for dataset in args.datasets:
        try:
            fields = load_fields(dataset)
        except FileNotFoundError as error:
            uncomputed[dataset] = str(error)
            print(f"UNCOMPUTED {dataset}: {error}")
            continue
        region = REGION_OF[dataset]
        if region not in ct_cache:
            points, problem = read_ct(region, args.refresh, args.offline)
            ct_cache[region] = (ct_point_sets(points), problem)
            if points is not None:
                checks[f"climatetrace_{region}"] = {"rows": len(points),
                                                    "by_kind": points["kind"].value_counts().to_dict(),
                                                    "capacity": modal_capacity_share(points)}
                if region == "quebec" and role_xy is not None:
                    # Lineage check: do Climate TRACE's Quebec dairy points sit on farms the roll calls dairy?
                    qc = points[(points["gadm"] == "CAN.11_1") & (points["kind"] == "dairy")]
                    gap = nearest_km(project_lonlat(qc["lon"], qc["lat"]), role_xy["dairy"])
                    checks[f"climatetrace_{region}"]["ct_dairy_to_role_dairy_km"] = {
                        "median": round(float(np.median(gap)), 3),
                        "share_within_1km": round(float(np.mean(gap <= 1)), 3)}
        ct_xy, ct_problem = ct_cache[region]
        if region == "quebec":
            if role_xy is None:
                uncomputed[dataset] = "Quebec assessment roll unavailable: roll-based columns NaN"
            if maize is None and role_xy is not None:
                # Every maize parcel of the full Quebec file, grain or silage alike (labels are not read).
                every = gpd.read_parquet(REPO / "data" / "labels" / "quebec_maize_2023.parquet").to_crs(CRS)
                maize = (field_points(every), every.geometry.area.to_numpy() / 1e4)
            if dataset == "quebec_maize_2023":
                fields = fields[fields["cell"] == QUEBEC_TRAIN_CELL].reset_index(drop=True)
        else:
            uncomputed[dataset] = MARYLAND_NOTE
        if ct_problem:
            partial[dataset] = ct_problem
        table = feature_table(dataset, fields, role_xy, maize, ct_xy)
        tables.append(table)
        built.append(dataset)
        print(f"{dataset}: {len(table)} field-years, model features non-missing "
              f"{int(table[MODEL_FEATURES].notna().all(axis=1).sum())}", flush=True)
        if dataset in QUEBEC_DATASETS:
            labelled_parts.append(table.merge(fields[["field_id", "year", "label", "cell"]], on=["field_id", "year"]))
        if region == "quebec":
            lat = fields.to_crs("EPSG:4326").geometry.representative_point().y
            near = int(((lat - US_BORDER_LAT) * 111.2 < RADIUS_KM).sum())
            checks.setdefault("us_border_edge", {})[dataset] = (
                f"{near} fields lie within {RADIUS_KM:g} km of the 45th parallel; the roll has no US farms, so "
                "their 18 km counts can be low")

    csv = out_dir / "features.csv"
    previous = pd.read_csv(csv, dtype={"field_id": str}) if csv.exists() else None
    features = replace_datasets(previous, tables, built)
    features.to_csv(out_dir / "features.csv", index=False)

    # Province-wide descriptive scope: every Quebec maize parcel, cheap columns only (no mass balance).
    province = None
    if role_xy is not None and "quebec_maize_2023" in built:
        every = load_fields("quebec_maize_2023")
        xy = field_points(every)
        province = pd.concat([role_features(xy, role_xy, None, None),
                              ct_features(xy, ct_cache.get("quebec", (None, ""))[0])], axis=1)
        province["label"] = every["label"].to_numpy()
    if labelled_parts:
        summary, by_cell = quebec_summaries(pd.concat(labelled_parts, ignore_index=True), province)
        summary.to_csv(out_dir / "quebec_class_summary.csv", index=False)
        by_cell.to_csv(out_dir / "quebec_by_cell.csv", index=False)
        print(summary[summary["role"] != "descriptive"][["scope", "feature", "median_grain", "median_silage",
                                                          "auc_silage_positive"]].to_string(index=False))

    all_built = sorted(set(features["dataset"].unique()))
    meta = {
        "group": GROUP,
        "features": MODEL_FEATURES,
        "rule_column": RULE_COLUMN,
        "description": (
            "Distance from each maize field to dairy sites of the Quebec property assessment roll (MAMH role "
            f"d'evaluation fonciere {ROLE_YEAR}, CC BY 4.0): units with CUBF 8122 'Elevage de bovins laitiers' "
            "(legacy 8150), a building value above zero and an accepted point. dairydist_d_dairy_km = km from the "
            "field's representative point to the nearest dairy site; dairydist_n_dairy_18km = dairy sites within "
            f"18 km; rule = 1 when the nearest dairy site is within {RULE_KM:g} km. Distances in {CRS}. Herd size "
            "is UNCOMPUTED (the roll has none). Maryland has no comparable registry: roll-based columns are NaN "
            "there. Climate TRACE columns (descriptive) cover every dataset."),
        "preregistered": "features and rule fixed in build.py before any class comparison was computed (2026-11-14)",
        "descriptive_columns": DESCRIPTIVE,
        "units": "km for *_km; counts of sites for *_18km; dairy sites per kernel-weighted maize hectare for mb",
        "sources": {"role": ROLE_URL, "cubf_list": "https://www.quebec.ca/habitation-territoire/information-fonciere/"
                    "evaluation-fonciere/manuel/codes-utilisation-biens-fonds",
                    "climatetrace": f"{CT_URL}?subsectors={CT_SUBSECTOR}",
                    "climatetrace_regions": [g for ids in CT_REGIONS.values() for g in ids]},
        "checks": checks,
        "datasets_built": all_built,
        "uncomputed": uncomputed,
        "partial": partial,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    for dataset, note in uncomputed.items():
        print(f"UNCOMPUTED {dataset}: {note}")
    print(f"wrote {out_dir / 'features.csv'} ({len(features)} rows) and meta.json")


if __name__ == "__main__":
    main()
