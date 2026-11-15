"""Export the real Maryland field test as an offline, selectable map and evidence viewer.

Run ``python -m kernelag.explorer`` after the label and satellite pulls. Scores are
uncalibrated classifier outputs, not probabilities. Acreage tallies describe the
observed research sample only; they are not county/state population estimates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import mapping

from kernelag.evaluate import evaluation_table
from kernelag.field_model import (
    MODEL_FEATURES,
    load_series,
    load_training,
    make_model,
    predict_silage,
)
from kernelag.paths import REPO, data_dir, record_in_manifest

# A transparent abstention band, fixed without optimizing Maryland test outcomes.
UNCERTAIN_LOW, UNCERTAIN_HIGH = 0.4, 0.6
COUNTY_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query"


def fetch_counties(data: Path, force: bool = False) -> Path:
    """Cache public Census boundaries for the demonstration region; never required at runtime."""
    import requests

    target = data / "geography" / "md_counties.geojson"
    if target.exists() and not force:
        return target
    response = requests.get(COUNTY_URL, params={"where": "STATE='24'", "outFields": "GEOID,NAME",
                            "outSR": 4326, "f": "geojson", "geometryPrecision": 5}, timeout=60)
    response.raise_for_status()
    if not response.json().get("features"):
        raise ValueError("Census response contains no county boundaries")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(response.text)
    record_in_manifest(target, response.url)
    return target


def geographic_context(labels, data: Path):
    """Join county by an interior point, then cached county weather; context is not a model input."""
    import geopandas as gpd

    labels = labels.copy()
    labels["county"] = "County not joined"
    labels["county_fips"] = None
    labels["context"] = [{} for _ in range(len(labels))]
    boundaries = data / "geography" / "md_counties.geojson"
    if not boundaries.exists():
        return labels
    counties = gpd.read_file(boundaries).to_crs(labels.crs)
    points = labels[["geometry"]].copy()
    points.geometry = points.geometry.representative_point()
    joined = gpd.sjoin(points, counties[["GEOID", "NAME", "geometry"]], how="left", predicate="within")
    if joined.index.duplicated().any():
        raise ValueError("a field interior point matches multiple counties")
    labels["county"] = joined["NAME"].fillna("County not joined")
    labels["county_fips"] = joined["GEOID"]
    for year in sorted(labels["year"].unique()):
        path = data / "weather" / "county_month" / f"county_month_{year}.csv"
        if not path.exists():
            continue
        weather = pd.read_csv(path, dtype={"fips": str})
        weather = weather[weather["month"].between(5, 9)]
        for county, months in weather.groupby("fips"):
            if set(months["month"]) != {5, 6, 7, 8, 9} or len(months) != 5:
                continue
            context = {"scope": "county May–September context, not field measurements; not used by classifier",
                       "source": str(path.relative_to(data)),
                       "precipitation_mm": float(months["prcp_mm"].sum(min_count=5)),
                       "gdd_c": float(months["gdd_c"].sum(min_count=5)),
                       "hot_days": float(months["hot_days"].sum(min_count=5)),
                       "frost_days": float(months["frost_days"].sum(min_count=5))}
            mask = (labels["year"] == year) & (labels["county_fips"] == county)
            for index in labels.index[mask]:
                labels.at[index, "context"] = context
    return labels


def classification(score: float | None) -> str:
    if score is None or not np.isfinite(score):
        return "not assessable"
    if UNCERTAIN_LOW <= score <= UNCERTAIN_HIGH:
        return "uncertain"
    return "silage-like" if score > UNCERTAIN_HIGH else "grain-like"


def harvest_interval(year: int, features: dict) -> dict:
    """Bracket the largest optical drop; this remains a provisional harvest candidate."""
    cut, gap = features.get("cut_doy"), features.get("cut_gap_days")
    if cut is None or gap is None or not np.isfinite(cut) or not np.isfinite(gap):
        return {"start": None, "end": None}
    end = datetime(year, 1, 1) + timedelta(days=int(cut) - 1)
    return {"start": (end - timedelta(days=int(gap))).strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d")}


def sample_summaries(fields: list[dict]) -> list[dict]:
    """Classified sample acres by year and geography, conserving all acres including unknowns."""
    table = pd.DataFrame([{k: f[k] for k in ["year", "state", "county", "acres", "classification"]}
                          for f in fields])
    rows = []
    if table.empty:
        return rows
    for (year, state, county), part in table.groupby(["year", "state", "county"], dropna=False):
        counts = part.groupby("classification")["acres"].sum()
        rows.append({"year": int(year), "state": state, "county": county,
                     "fields": len(part), "total_acres": round(float(part["acres"].sum()), 2),
                     **{f"{name.replace('-', '_').replace(' ', '_')}_acres":
                        round(float(counts.get(name, 0)), 2) for name in
                        ["silage-like", "grain-like", "uncertain", "not assessable"]}})
    return rows


def export_fields(labels, series: pd.DataFrame, model) -> list[dict]:
    """One real geometry and evidence record per labeled field-year, never silently dropping rows."""
    labels = labels.copy()
    labels["field_id"] = labels["field_id"].astype(str)
    table = evaluation_table(labels, series)
    probability, _ = predict_silage(model, table)
    table = table.merge(labels[["field_id", "year", "acres", "geometry", "county", "county_fips", "context"]],
                        on=["field_id", "year"], validate="one_to_one")
    # The training output calls these probabilities; export them explicitly as scores.
    table["model_score"] = probability
    observation_groups = dict(tuple(series.groupby(["field_id", "year"])))
    fields = []
    for row in table.to_dict("records"):
        field_id, year = row["field_id"], int(row["year"])
        observations = observation_groups.get((field_id, year), series.iloc[:0]).sort_values("date")
        columns = ["date", "ndvi", "ndmi", "ndti", "valid_frac"]
        obs = observations.reindex(columns=columns).copy()
        obs["date"] = obs["date"].dt.strftime("%Y-%m-%d")
        features = {k: v for k, v in row.items() if k not in
                    {"field_id", "year", "label", "is_silage", "assessable", "model_score", "acres", "geometry",
                     "county", "county_fips", "context"}}
        value = row["model_score"]
        fields.append({"field_id": field_id, "year": year, "state": "MARYLAND",
                       "county": row["county"], "county_fips": row["county_fips"],
                       "context": row["context"], "acres": float(row["acres"]),
                       "geometry": mapping(row["geometry"]), "classification": classification(value),
                       "model_score": float(value * 100) if np.isfinite(value) else None,
                       "reference_label": row["label"], "features": features,
                       "harvest_interval": harvest_interval(year, features),
                       "observations": obs.to_dict("records"),
                       "quality": {"observations": len(observations),
                                   "clear_observations": int(((observations["valid_frac"] >= 0.5)
                                                              & observations["ndvi"].notna()).sum())}})
    return fields


def strict_json(value) -> str:
    """Pandas converts numpy scalars and non-finite missing values into portable strict JSON."""
    cleaned = json.loads(pd.Series([value]).to_json(orient="values", double_precision=8))[0]
    return json.dumps(cleaned, ensure_ascii=False, allow_nan=False)


def main() -> None:
    import geopandas as gpd

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=REPO / "report" / "fields.html")
    parser.add_argument("--fetch-counties", action="store_true", help="cache public Census boundaries once")
    parser.add_argument("--force", action="store_true", help="refresh cached county download")
    args = parser.parse_args()
    data = data_dir()
    if args.fetch_counties:
        fetch_counties(data, args.force)
    train, _ = load_training(data)
    fit = train[train["assessable"]]
    model = make_model().fit(fit[MODEL_FEATURES], fit["is_silage"])
    labels_path = data / "labels" / "barc_2021_2023.parquet"
    labels = geographic_context(gpd.read_parquet(labels_path).to_crs("EPSG:4326"), data)
    series_dir = data / "s2_series" / "barc_2021_2023"
    series = load_series(series_dir)
    fields = export_fields(labels, series, model)
    evaluation_file = data / "models" / "field_eval.json"
    payload = {
        "metadata": {"built_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
                     "model": {"class": "balanced logistic regression", "features": MODEL_FEATURES,
                               "sklearn_version": version("scikit-learn"),
                               "weights_per_std": model.named_steps["logisticregression"].coef_[0].tolist(),
                               "code_sha256": hashlib.sha256((REPO / "kernelag" / "field_model.py").read_bytes()).hexdigest()},
                     "train_field_years": len(fit), "train_years": sorted(int(y) for y in fit["year"].unique()),
                     "score_kind": "uncalibrated model score", "uncertain_band": [40, 60],
                     "sources": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [labels_path, *sorted(series_dir.glob("*.csv")),
                                           *sorted((data / "labels").glob("quebec_maize_*.parquet")),
                                           *sorted((data / "s2_series").glob("quebec_maize_*/*.csv")),
                                           *sorted((data / "geography").glob("*.geojson")),
                                           *(data / "weather" / "county_month" / f"county_month_{y}.csv"
                                             for y in labels["year"].unique()
                                             if (data / "weather" / "county_month" / f"county_month_{y}.csv").exists())]},
                     "caveats": ["Research sample only; no county or state population acreage estimate",
                                 "County weather is contextual, not a field measurement or model input; soil and radar are not joined",
                                 "Scores are not calibrated probabilities; 40–60 is a fixed abstention band",
                                 "Largest optical drop is a candidate harvest interval, not confirmed harvest",
                                 "Missing harvest evidence is not a grain observation",
                                 "Single-farm test does not establish geographic transfer"]},
        "fields": fields, "summaries": sample_summaries(fields),
        "evaluation": json.loads(evaluation_file.read_text()) if evaluation_file.exists() else {},
    }
    encoded = strict_json(payload)
    output_data = data / "models" / "field_explorer.json"
    output_data.write_text(encoded + "\n")
    record_in_manifest(output_data, "derived: kernelag.explorer; BARC public research sample")
    template = (REPO / "report" / "field_explorer.template.html").read_text()
    # Prevent data strings from terminating the inline script element.
    embedded = encoded.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    if template.count("__KERNEL_DATA__") != 1:
        raise ValueError("explorer template must contain exactly one data placeholder")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(template.replace("__KERNEL_DATA__", embedded))
    print(f"{len(fields)} field-years -> {args.out}; exported {output_data}")


if __name__ == "__main__":
    main()
