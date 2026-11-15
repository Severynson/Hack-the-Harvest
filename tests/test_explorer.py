import json

import numpy as np
import pandas as pd

from kernelag.explorer import (
    classification,
    harvest_interval,
    sample_summaries,
    strict_json,
)


def test_score_abstains_for_missing_and_ambiguous_evidence():
    assert classification(None) == classification(np.nan) == "not assessable"
    assert classification(0.4) == classification(0.6) == "uncertain"
    assert classification(0.61) == "silage-like"
    assert classification(0.39) == "grain-like"


def test_harvest_bracket_uses_observation_gap():
    assert harvest_interval(2021, {"cut_doy": 274, "cut_gap_days": 10}) == {
        "start": "2021-09-21", "end": "2021-10-01"}
    assert harvest_interval(2021, {"cut_doy": np.nan}) == {"start": None, "end": None}


def test_sample_acres_are_conserved_and_years_stay_separate():
    fields = [{"year": year, "state": "MARYLAND", "county": "County not joined",
               "classification": name, "acres": 10.0} for year, name in
              [(2021, "silage-like"), (2021, "uncertain"), (2021, "not assessable"), (2022, "grain-like")]]
    rows = sample_summaries(fields)
    assert [r["total_acres"] for r in rows] == [30, 10]
    for r in rows:
        assert r["total_acres"] == sum(r[k] for k in
                                     ["silage_like_acres", "grain_like_acres", "uncertain_acres", "not_assessable_acres"])


def test_json_missing_scores_are_null_not_nan():
    encoded = strict_json({"score": np.nan, "count": np.int64(2)})
    assert json.loads(encoded) == {"score": None, "count": 2}
    assert "NaN" not in encoded


def test_context_requires_all_season_months(tmp_path):
    import geopandas as gpd
    from shapely.geometry import box

    from kernelag.explorer import geographic_context

    (tmp_path / "geography").mkdir()
    (tmp_path / "weather" / "county_month").mkdir(parents=True)
    counties = gpd.GeoDataFrame({"GEOID": ["24033"], "NAME": ["Test county"]},
                               geometry=[box(-77, 38, -76, 40)], crs="EPSG:4326")
    counties.to_file(tmp_path / "geography" / "md_counties.geojson", driver="GeoJSON")
    labels = gpd.GeoDataFrame({"year": [2021]}, geometry=[box(-76.9, 39, -76.8, 39.1)], crs="EPSG:4326")
    weather = pd.DataFrame({"fips": "24033", "month": [5, 6, 7, 8, 9], "prcp_mm": 10.,
                            "gdd_c": 100., "hot_days": 2, "frost_days": 0})
    path = tmp_path / "weather" / "county_month" / "county_month_2021.csv"
    weather.iloc[:4].to_csv(path, index=False)
    assert geographic_context(labels, tmp_path).iloc[0]["context"] == {}
    weather.to_csv(path, index=False)
    row = geographic_context(labels, tmp_path).iloc[0]
    assert row["county"] == "Test county"
    assert row["context"]["precipitation_mm"] == 50
