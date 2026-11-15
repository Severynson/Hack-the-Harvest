"""Thermal-time harvest features (feature group "gdd"): the optical cut date expressed in growing degree days.

Why: silage is cut at half milk line, about 200 GDD (F) *before* black layer, while dry grain is
combined about 150-375 GDD (F) *after* it (DOCS/research/agronomy.md, sections 2.4 and 11.1). The
same calendar date is early in one climate and late in another, which is one of the traps the USDA
reps named, so a thermal clock should travel across regions better than a calendar one.

Pre-registered model features (fixed before any evaluation was looked at):
    gdd_peak_to_cut    cumulative GDD at the optical cut_doy minus at the optical peak_doy
    gdd_share_at_cut   cumulative GDD at cut_doy / cumulative GDD from May 1 to Oct 31 (same year and place)
Descriptive only (not model features):
    gdd_at_cut         cumulative GDD from May 1 to cut_doy
    gdd_season_may_oct cumulative GDD from May 1 to Oct 31 of the field's cell-year

GDD are degC-days, base 10 C, cap 30 C (the corn "modified GDD"; 1 C-day = 1.8 F-day). Both daily
temperatures are clipped to 10-30 C, so a cold day adds zero, never negative, thermal time; this equals
``(min(Tmax, 30) + max(Tmin, 10)) / 2 - 10`` whenever Tmax >= 10 C. Cumulative sums start on May 1 and
include the day itself. A missing temperature makes every later cumulative value missing (NaN).

Inputs:
    data/labels/<dataset>.parquet               geometry and ids only, to check each field's 10 km cell
    data/s2_series/<dataset>/<cell>_<year>.csv  Sentinel-2 series; kernelag.features.build_features
                                                gives peak_doy and cut_doy; the file name gives the cell
    Open-Meteo historical archive (ERA5-Land, ERA5 as fallback), daily Tmax/Tmin May 1 - Nov 30, one
    request per cell-year at the 10 km cell centre, cached in test_models/featureTests/gdd/data/
Outputs (test_models/featureTests/gdd/out/):
    features.csv               dataset, field_id, year, gdd_* columns; one row per field-year with a series
    meta.json                  the feature-group contract (pre-registered features, uncomputed datasets)
    optical_dates.csv          the optical peak_doy and cut_doy and the cell behind every row of features.csv
    cells.csv                  one row per dataset cell-year: centre, weather grid point, season GDD
    quebec_class_summary.csv   class medians and univariate ROC AUC, Quebec labels only
    quebec_by_cell.csv         the same per Quebec cell, to show how the calendar shifts between regions

Maryland (barc_2021_2023) is a test set: its features are built, but nothing here reads its labels.

Run from the repo root:
    .venv/Scripts/python.exe test_models/featureTests/gdd/build.py [--datasets ...] [--offline]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:   # run as a plain script from anywhere: make ``kernelag`` importable
    sys.path.insert(0, str(REPO))

GROUP = "gdd"
MODEL_FEATURES = ["gdd_peak_to_cut", "gdd_share_at_cut"]   # pre-registered; never changed after evaluation
DESCRIPTIVE = ["gdd_at_cut", "gdd_season_may_oct"]
FEATURE_COLUMNS = ["gdd_at_cut", "gdd_peak_to_cut", "gdd_share_at_cut", "gdd_season_may_oct"]
KEYS = ["dataset", "field_id", "year"]
DEFAULT_DATASETS = ["quebec_maize_2023", "qc_regions_2023", "barc_2021_2023"]
QUEBEC_DATASETS = ["quebec_maize_2023", "qc_regions_2023"]   # the only labels a class comparison may read
# qc_regions_2023 was sampled with cell ids on the grid of the full Quebec file, not on its own UTM zone.
GRID_SOURCE = {"qc_regions_2023": "quebec_maize_2023"}

API_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_MODELS = ["era5_land", "era5"]   # 0.1 degree land reanalysis first; 0.25 degree ERA5 only if it has gaps
SEASON = ("05-01", "11-30")              # same window as the Sentinel-2 series
SEASON_TOTAL_END = "10-31"               # end of the denominator of gdd_share_at_cut
BASE_C, CAP_C = 10.0, 30.0
CELL_KM = 10
MAX_REQUESTS = 59                        # hard ceiling per run; the full build needs about 24
PAUSE_S = 1.0                            # polite gap between requests to a free public service

DATA = HERE / "data"
OUT = HERE / "out"


# ---------------------------------------------------------------------------------------------
# Thermal time
# ---------------------------------------------------------------------------------------------
def daily_gdd(tmax, tmin) -> np.ndarray:
    """Corn modified GDD in degC-days. NaN in, NaN out."""
    hi = np.clip(np.asarray(tmax, float), BASE_C, CAP_C)
    lo = np.clip(np.asarray(tmin, float), BASE_C, CAP_C)
    return (hi + lo) / 2.0 - BASE_C


def cumulative_gdd(weather: pd.DataFrame) -> pd.Series:
    """Cumulative GDD from May 1, indexed by day of year (that day included). A gap poisons every later day."""
    w = weather.sort_values("date")
    w = w[w["date"].dt.strftime("%m-%d") >= SEASON[0]]
    gdd = daily_gdd(w["tmax_c"].to_numpy(), w["tmin_c"].to_numpy())
    # np.cumsum carries NaN forward, which is what we want: thermal time after a gap is unknown.
    return pd.Series(np.cumsum(gdd), index=w["date"].dt.day_of_year.to_numpy().astype(float), name="cum_gdd")


def season_total(cum: pd.Series, year: int) -> float:
    """Cumulative GDD May 1 - Oct 31 of ``year`` (NaN if that day is missing)."""
    end_doy = float(pd.Timestamp(f"{year}-{SEASON_TOTAL_END}").day_of_year)
    return float(cum.get(end_doy, np.nan))


def thermal_features(base: pd.DataFrame, cums: dict) -> pd.DataFrame:
    """GDD features per field-year from its optical dates and its cell-year's cumulative GDD.

    ``base`` needs field_id, year, cell, peak_doy, cut_doy; ``cums`` maps (cell, year) to cumulative_gdd.
    A field-year without a cut date, a peak date or weather keeps NaN in the affected columns.
    """
    out = base[["field_id", "year"]].copy()
    for column in FEATURE_COLUMNS:
        out[column] = np.nan
    for (cell, year), rows in base.groupby(["cell", "year"]):
        cum = cums.get((cell, int(year)))
        if cum is None:
            continue
        cum = pd.Series(cum.to_numpy(), index=cum.index.astype(float))
        total = season_total(cum, int(year))
        at_cut = cum.reindex(rows["cut_doy"].to_numpy(float)).to_numpy()   # NaN cut_doy -> NaN
        at_peak = cum.reindex(rows["peak_doy"].to_numpy(float)).to_numpy()
        out.loc[rows.index, "gdd_at_cut"] = at_cut
        out.loc[rows.index, "gdd_peak_to_cut"] = at_cut - at_peak
        out.loc[rows.index, "gdd_share_at_cut"] = at_cut / total if total > 0 else np.nan
        out.loc[rows.index, "gdd_season_may_oct"] = total
    return out


# ---------------------------------------------------------------------------------------------
# Cells and weather
# ---------------------------------------------------------------------------------------------
def grid_crs(dataset: str):
    """The UTM CRS whose 10 km grid named this dataset's cells (estimated as kernelag.s2_series.assign_cells does)."""
    import geopandas as gpd

    source = REPO / "data" / "labels" / f"{GRID_SOURCE.get(dataset, dataset)}.parquet"
    return gpd.read_parquet(source, columns=["geometry"]).estimate_utm_crs()


def grid_cells(fields, crs) -> pd.Series:
    """The 10 km cell of each field's representative point in ``crs``, the same rule as assign_cells."""
    from kernelag.s2_series import assign_cells

    if "cell" not in fields.columns and fields.estimate_utm_crs() == crs:
        return assign_cells(fields, CELL_KM)["cell"].reset_index(drop=True)   # the pipeline's own function
    # A preset cell column (qc_regions) was named on another file's grid: recompute there to verify it.
    centre = fields.to_crs(crs).geometry.representative_point()
    size = CELL_KM * 1000
    cells = (centre.x // size).astype(int).astype(str) + "_" + (centre.y // size).astype(int).astype(str)
    return cells.reset_index(drop=True)


def count_cell_mismatches(dataset: str, crs, cell_of: pd.DataFrame) -> int:
    """Labeled field-years whose grid cell differs from the series file they came from (ids only, no labels)."""
    import geopandas as gpd

    fields = gpd.read_parquet(REPO / "data" / "labels" / f"{dataset}.parquet", columns=["field_id", "year", "geometry"])
    keys = pd.DataFrame({"field_id": fields["field_id"].astype(str).to_numpy(),
                         "year": fields["year"].astype(int).to_numpy(),
                         "grid_cell": grid_cells(fields, crs).to_numpy()})
    joined = cell_of.merge(keys, on=["field_id", "year"], how="inner")
    return int((joined["cell"] != joined["grid_cell"]).sum())


def cell_centre(cell: str, crs) -> tuple[float, float]:
    """(latitude, longitude) of the centre of the 10 km grid square named ``"<x>_<y>"`` in ``crs``."""
    from pyproj import Transformer

    x, y = (int(part) for part in cell.split("_"))
    size = CELL_KM * 1000
    lon, lat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform((x + 0.5) * size, (y + 0.5) * size)
    return float(lat), float(lon)


def weather_path(epsg: int, cell: str, year: int) -> Path:
    # The EPSG code keeps identical cell names from two UTM zones out of one cache file.
    return DATA / f"weather_{epsg}_{cell}_{year}.csv"


def fetch_weather(lat: float, lon: float, year: int, budget: list[int]) -> pd.DataFrame:
    """Daily Tmax/Tmin for the season from the Open-Meteo archive, one request per model tried.

    ERA5 (0.25 degree) is asked only when ERA5-Land has missing days; gaps left in both stay NaN.
    """
    import requests

    frame = None
    for model in WEATHER_MODELS:
        if budget[0] >= MAX_REQUESTS:
            raise RuntimeError(f"request ceiling of {MAX_REQUESTS} reached")
        if budget[0]:
            time.sleep(PAUSE_S)
        budget[0] += 1
        params = {
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "start_date": f"{year}-{SEASON[0]}", "end_date": f"{year}-{SEASON[1]}",
            "daily": "temperature_2m_max,temperature_2m_min", "timezone": "auto", "models": model,
        }
        response = requests.get(API_URL, params=params, timeout=60)
        response.raise_for_status()
        body = response.json()
        daily = body["daily"]
        frame = pd.DataFrame({
            "date": pd.to_datetime(daily["time"]),
            "tmax_c": pd.to_numeric(pd.Series(daily["temperature_2m_max"], dtype=object), errors="coerce"),
            "tmin_c": pd.to_numeric(pd.Series(daily["temperature_2m_min"], dtype=object), errors="coerce"),
        }).assign(model=model, grid_lat=body.get("latitude"), grid_lon=body.get("longitude"),
                  grid_elevation_m=body.get("elevation"))
        if frame[["tmax_c", "tmin_c"]].notna().all().all():
            break
    return frame


def load_weather(epsg: int, cell: str, year: int, offline: bool, budget: list[int],
                 crs=None) -> tuple[pd.DataFrame | None, str]:
    """Cached weather for one cell-year, downloaded once if allowed. Returns (frame or None, note)."""
    path = weather_path(epsg, cell, year)
    if path.exists():
        return pd.read_csv(path, parse_dates=["date"]), "cached"
    if offline:
        return None, "not cached and --offline"
    import requests

    lat, lon = cell_centre(cell, crs)
    try:
        frame = fetch_weather(lat, lon, year, budget)
    except (requests.RequestException, RuntimeError, KeyError, ValueError) as error:
        # Network, service or format failure: this cell-year stays UNCOMPUTED, never guessed.
        return None, f"download failed: {type(error).__name__}: {error}"
    frame = frame.assign(cell=cell, epsg=epsg, cell_lat=round(lat, 5), cell_lon=round(lon, 5))
    DATA.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, date_format="%Y-%m-%d")
    return frame, "downloaded"


# ---------------------------------------------------------------------------------------------
# One dataset
# ---------------------------------------------------------------------------------------------
def series_with_cells(series_dir: Path) -> pd.DataFrame:
    """All per-cell series files of a dataset, each row tagged with the cell named in its file name."""
    from kernelag.field_model import load_series

    parts = []
    for path in sorted(series_dir.glob("*.csv")):
        cell = path.stem.rsplit("_", 1)[0]   # "<x>_<y>_<year>.csv"
        parts.append(load_series(path).assign(cell=cell))
    series = pd.concat(parts, ignore_index=True)
    return series.drop_duplicates(["field_id", "year", "date"])


def build_dataset(dataset: str, offline: bool, budget: list[int]):
    """Features for one dataset. Returns (features or None, optical dates, cell rows, note on a skip or gap)."""
    from kernelag.features import build_features

    series_dir = REPO / "data" / "s2_series" / dataset
    labels_file = REPO / "data" / "labels" / f"{dataset}.parquet"
    if not labels_file.exists() or not series_dir.is_dir() or not any(series_dir.glob("*.csv")):
        return None, None, [], "no label geometry or no Sentinel-2 series files"

    series = series_with_cells(series_dir)
    cell_of = series[["field_id", "year", "cell"]].drop_duplicates(["field_id", "year"])
    optical = build_features(series.drop(columns="cell"))
    for column in ("peak_doy", "cut_doy"):
        if column not in optical:
            optical[column] = np.nan
    base = optical[["field_id", "year", "peak_doy", "cut_doy"]].merge(cell_of, on=["field_id", "year"], how="left")

    crs = grid_crs(dataset)
    epsg = int(crs.to_epsg())
    mismatches = count_cell_mismatches(dataset, crs, cell_of)
    print(f"{dataset}: {len(base)} field-years with a series in {cell_of['cell'].nunique()} cells "
          f"(grid EPSG:{epsg}; {mismatches} labeled field-years sit in a different cell than their series file)")

    cums, cell_rows, gaps = {}, [], []
    for cell, year in sorted(set(zip(base["cell"], base["year"].astype(int)))):
        lat, lon = cell_centre(cell, crs)
        weather, note = load_weather(epsg, cell, year, offline, budget, crs)
        n_rows = int(((base["cell"] == cell) & (base["year"] == year)).sum())
        row = {"dataset": dataset, "cell": cell, "year": year, "epsg": epsg, "cell_lat": round(lat, 5),
               "cell_lon": round(lon, 5), "n_field_years": n_rows, "weather": note}
        if weather is None:
            gaps.append(f"{cell}/{year}: {note}")
        else:
            cum = cumulative_gdd(weather)
            cums[(cell, year)] = cum
            row.update(model=weather["model"].iloc[0], grid_lat=weather["grid_lat"].iloc[0],
                       grid_lon=weather["grid_lon"].iloc[0], grid_elevation_m=weather["grid_elevation_m"].iloc[0],
                       missing_days=int(weather[["tmax_c", "tmin_c"]].isna().any(axis=1).sum()),
                       gdd_may_oct=round(season_total(cum, year), 1))
        print(f"  {cell} {year}: {note}")
        cell_rows.append(row)

    base = base.assign(dataset=dataset)
    features = thermal_features(base, cums)
    features.insert(0, "dataset", dataset)
    # Reanalysis temperatures carry about 0.1 C; more decimals in the CSV would be float noise.
    features = features.round({"gdd_at_cut": 2, "gdd_peak_to_cut": 2, "gdd_share_at_cut": 4, "gdd_season_may_oct": 2})
    optical_dates = base[["dataset", "field_id", "year", "cell", "peak_doy", "cut_doy"]]
    if gaps and not cums:
        return None, None, cell_rows, f"no weather for any cell-year ({'; '.join(gaps)})"
    return features, optical_dates, cell_rows, (f"partial: weather missing for {'; '.join(gaps)}" if gaps else "")


# ---------------------------------------------------------------------------------------------
# Descriptive check on Quebec labels only
# ---------------------------------------------------------------------------------------------
def roc_auc(truth: np.ndarray, score: np.ndarray) -> float:
    """ROC AUC with silage (1) as the positive class; NaN scores dropped; NaN when a class is empty."""
    from sklearn.metrics import roc_auc_score

    ok = ~np.isnan(score)
    if len(np.unique(truth[ok])) < 2:
        return float("nan")
    return float(roc_auc_score(truth[ok], score[ok]))


def describe(table: pd.DataFrame, group: str) -> list[dict]:
    """Class medians and univariate AUC for the thermal features and the calendar cut_doy."""
    rows = []
    truth = table["is_silage"].to_numpy()
    for column in ["gdd_peak_to_cut", "gdd_share_at_cut", "cut_doy", "gdd_at_cut"]:
        values = table[column].to_numpy(float)
        ok = ~np.isnan(values)
        grain, silage = values[ok & (truth == 0)], values[ok & (truth == 1)]
        auc = roc_auc(truth, values)
        rows.append({
            "group": group, "feature": column,
            "role": "model" if column in MODEL_FEATURES else ("calendar" if column == "cut_doy" else "descriptive"),
            "n_grain": len(grain), "n_silage": len(silage), "n_missing": int((~ok).sum()),
            "median_grain": round(float(np.median(grain)), 3) if len(grain) else np.nan,
            "median_silage": round(float(np.median(silage)), 3) if len(silage) else np.nan,
            "auc_silage_positive": round(auc, 4),
            # Direction-free separation: 0.5 is no signal, 1.0 perfect, whichever way the classes order.
            "separation": round(max(auc, 1 - auc), 4) if not np.isnan(auc) else np.nan,
        })
    return rows


def quebec_summary(features: pd.DataFrame, optical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Descriptive comparison per Quebec dataset, pooled, and per cell. Never reads Maryland labels."""
    tables = []
    for dataset in QUEBEC_DATASETS:
        part = features[features["dataset"] == dataset]
        if part.empty:
            continue
        labels = pd.read_parquet(REPO / "data" / "labels" / f"{dataset}.parquet", columns=["field_id", "year", "label"])
        labels = pd.DataFrame({"field_id": labels["field_id"].astype(str).to_numpy(),
                               "year": labels["year"].astype(int).to_numpy(), "label": labels["label"].to_numpy()})
        table = part.merge(labels, on=["field_id", "year"], how="inner").merge(optical, on=KEYS, how="left")
        table["is_silage"] = (table["label"] == "silage").astype(int)
        tables.append(table)
    if not tables:
        return pd.DataFrame(), pd.DataFrame()
    pooled = pd.concat(tables, ignore_index=True)
    rows = []
    for dataset, table in pooled.groupby("dataset"):
        rows += describe(table, dataset)
    rows += describe(pooled, f"quebec_pooled_{pooled['cell'].nunique()}_cells")
    by_cell = []
    for cell, table in pooled.groupby("cell"):
        extra = {"dataset": table["dataset"].iloc[0], "gdd_season_may_oct": table["gdd_season_may_oct"].iloc[0]}
        by_cell += [{**extra, **row} for row in describe(table, cell)]
    by_cell = pd.DataFrame(by_cell).rename(columns={"group": "cell"})
    rows += within_cell_rows(by_cell, f"quebec_within_{pooled['cell'].nunique()}_cells")
    return pd.DataFrame(rows), by_cell


def within_cell_rows(by_cell: pd.DataFrame, group: str) -> list[dict]:
    """AUC over grain-silage pairs from the same cell only: per-cell AUCs weighted by their pair counts.

    Inside one cell every field shares one weather series, so a pooled AUC can be lifted by climate
    differences between cells (where silage is more common) rather than by harvest timing. This row
    removes that between-cell part; 0.5 means no within-cell signal.
    """
    rows = []
    for feature, part in by_cell.dropna(subset=["auc_silage_positive"]).groupby("feature", sort=False):
        pairs = (part["n_grain"] * part["n_silage"]).to_numpy(float)
        auc = float(np.average(part["auc_silage_positive"], weights=pairs)) if pairs.sum() else np.nan
        rows.append({"group": group, "feature": feature, "role": part["role"].iloc[0],
                     "n_grain": int(part["n_grain"].sum()), "n_silage": int(part["n_silage"].sum()),
                     "n_missing": int(part["n_missing"].sum()), "median_grain": np.nan, "median_silage": np.nan,
                     "auc_silage_positive": round(auc, 4),
                     "separation": round(max(auc, 1 - auc), 4) if not np.isnan(auc) else np.nan})
    return rows


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def replace_datasets(previous: pd.DataFrame | None, new: list[pd.DataFrame], rebuilt: list[str],
                     sort_by: list[str]) -> pd.DataFrame | None:
    """Rows of the datasets rebuilt this run replace their old rows; other datasets' rows are kept."""
    keep = [] if previous is None else [previous[~previous["dataset"].isin(rebuilt)]]
    frames = [frame for frame in keep + new if frame is not None and not frame.empty]
    if not frames:
        return None
    merged = pd.concat(frames, ignore_index=True)
    if "field_id" in merged:
        merged["field_id"] = merged["field_id"].astype(str)
    merged["year"] = merged["year"].astype(int)
    return merged.sort_values(sort_by).reset_index(drop=True)


def read_csv_if_any(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path, dtype={"field_id": str}) if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS)
    parser.add_argument("--offline", action="store_true", help="use cached weather only; never download")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    budget = [0]
    built, optical, cell_rows, uncomputed, partial = [], [], [], {}, {}
    for dataset in args.datasets:
        features, dates, cells, note = build_dataset(dataset, args.offline, budget)
        cell_rows += cells
        if features is None:
            uncomputed[dataset] = note
            print(f"UNCOMPUTED {dataset}: {note}")
            continue
        built.append(features)
        optical.append(dates)
        if note:
            partial[dataset] = note
            print(f"PARTIAL {dataset}: {note}")
        print(f"{dataset}: {len(features)} rows, {int(features['gdd_peak_to_cut'].notna().sum())} with gdd_peak_to_cut")
    print(f"weather requests this run: {budget[0]}")

    rebuilt = list(args.datasets)
    features = replace_datasets(read_csv_if_any(OUT / "features.csv"), built, rebuilt, KEYS)
    if features is None:
        features = pd.DataFrame(columns=[*KEYS, *FEATURE_COLUMNS])
    features[[*KEYS, *FEATURE_COLUMNS]].to_csv(OUT / "features.csv", index=False)
    dates = replace_datasets(read_csv_if_any(OUT / "optical_dates.csv"), optical, rebuilt, KEYS)
    if dates is not None:
        dates.to_csv(OUT / "optical_dates.csv", index=False)
    cells = replace_datasets(read_csv_if_any(OUT / "cells.csv"), [pd.DataFrame(cell_rows)], rebuilt,
                             ["dataset", "year", "cell"])
    if cells is not None:
        cells.to_csv(OUT / "cells.csv", index=False)

    meta_path = OUT / "meta.json"
    previous = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta = {
        "group": GROUP,
        "features": MODEL_FEATURES,
        "rule_column": None,
        "description": (
            "Optical harvest dates (kernelag.features peak_doy, cut_doy) expressed in thermal time: corn modified "
            "GDD in degC-days (base 10, cap 30, both temperatures clipped to 10-30), cumulative from May 1, from "
            "Open-Meteo archive daily Tmax/Tmin (ERA5-Land, ERA5 fallback) at each 10 km cell centre. "
            "gdd_peak_to_cut = GDD(cut) - GDD(peak); gdd_share_at_cut = GDD(cut) / GDD(May 1-Oct 31). "
            "Descriptive only: gdd_at_cut, gdd_season_may_oct. No benchmark rule: the research thresholds are "
            "relative to black layer, which no input here observes."
        ),
        "descriptive_columns": DESCRIPTIVE,
        "units": "degC-days (1 degC-day = 1.8 degF-day); gdd_share_at_cut is unitless",
        "weather_source": (f"{API_URL} (models {', '.join(WEATHER_MODELS)}); "
                           "cached in test_models/featureTests/gdd/data/"),
        "datasets_built": sorted(features["dataset"].unique().tolist()),
        "uncomputed": {**{k: v for k, v in previous.get("uncomputed", {}).items() if k not in rebuilt}, **uncomputed},
        "partial": {**{k: v for k, v in previous.get("partial", {}).items() if k not in rebuilt}, **partial},
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if dates is not None:
        summary, by_cell = quebec_summary(features, dates)
        if not summary.empty:
            summary.to_csv(OUT / "quebec_class_summary.csv", index=False)
            by_cell.to_csv(OUT / "quebec_by_cell.csv", index=False)
            with pd.option_context("display.width", 200, "display.max_columns", 20):
                print(summary.to_string(index=False))
    print(f"wrote {OUT / 'features.csv'} ({len(features)} rows) and meta.json")


if __name__ == "__main__":
    main()
