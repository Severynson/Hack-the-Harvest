"""Season context uses only what was public on the forecast date, and weights counties by corn."""

import numpy as np
import pandas as pd

from kernelag import context


def test_drought_averages_june_to_september_and_respects_the_cutoff():
    usdm = pd.DataFrame({
        "MapDate": [20220503, 20220607, 20220906, 20220920, 20221004],
        "StateAbbreviation": ["KS"] * 5,
        "D2": [100.0, 20.0, 40.0, 60.0, 100.0],
    })
    november = context.drought(usdm, "nov").set_index("state")["drought"]
    assert np.isclose(november["KANSAS"], 0.40)            # May and October are outside the season
    september = context.drought(usdm, "sep").set_index("state")["drought"]
    assert np.isclose(september["KANSAS"], 0.30)           # 20 September is after the 15th


def _weekly(rows):
    return pd.DataFrame(rows, columns=["state_name", "year", "reference_period_desc", "week_ending", "short_desc", "Value"])


def test_poor_condition_adds_poor_and_very_poor_inside_the_weeks():
    poor, very_poor, good = (f"CORN - CONDITION, MEASURED IN PCT {x}" for x in ("POOR", "VERY POOR", "GOOD"))
    table = _weekly([
        ["IOWA", "2022", "WEEK #31", "2022-08-07", poor, "10"],
        ["IOWA", "2022", "WEEK #31", "2022-08-07", very_poor, "5"],
        ["IOWA", "2022", "WEEK #31", "2022-08-07", good, "60"],
        ["IOWA", "2022", "WEEK #33", "2022-08-21", poor, "25"],
        ["IOWA", "2022", "WEEK #25", "2022-06-26", poor, "90"],      # before week 30
    ])
    assert np.isclose(context.poor_condition(table, "nov")["poor_condition"].iloc[0], 0.20)   # mean of 15 and 25
    assert np.isclose(context.poor_condition(table, "aug")["poor_condition"].iloc[0], 0.15)   # week 33 not out yet


def test_week_38_features_are_missing_before_october():
    item = "CORN - PROGRESS, MEASURED IN PCT MATURE"
    table = _weekly([["IOWA", "2022", "WEEK #38", "2022-09-25", item, "70"]])
    assert context.mature_wk38(table, "oct")["mature_wk38"].tolist() == [70.0]
    assert context.mature_wk38(table, "sep").empty


def test_anomaly_uses_earlier_years_only():
    table = pd.DataFrame({"state": ["A"] * 5, "year": range(2000, 2005), "x": [10.0, 10.0, 10.0, 20.0, 1000.0]})
    anomaly = context.against_earlier_years(table, "x", relative=True)
    assert anomaly.iloc[:3].isna().all()                   # fewer than three earlier years
    assert np.isclose(anomaly.iloc[3], 1.0)                # 20 against a mean of 10; the later 1000 is unseen


def test_weather_weights_counties_by_corn_acres():
    months = pd.DataFrame({
        "fips": ["19001", "19003"] * 4, "state": ["IA"] * 8,
        "year": [2000, 2000, 2001, 2001, 2002, 2002, 2003, 2003], "month": [7] * 8,
        "gdd_c": [100.0, 100.0] * 3 + [100.0, 200.0], "prcp_mm": [50.0] * 8,
    })
    season = pd.DataFrame({"fips": ["19001", "19003"], "state": ["IA", "IA"], "year": [2003, 2003],
                           "first_hard_freeze_doy": [270, 300]})
    weights = pd.Series({"19001": 1.0, "19003": 3.0})
    row = context.weather(months, season, weights, "nov").set_index("year").loc[2003]
    assert np.isclose(row["gdd_anom"], 0.75)               # (100 + 3 * 200) / 4 = 175 against 100
    assert np.isclose(row["early_frost"], 0.25)            # only the small county froze early
    assert np.isnan(context.weather(months, season, weights, "sep").set_index("year").loc[2003, "early_frost"])


def test_loss_share_counts_weather_causes_before_the_asof_month():
    losses = pd.DataFrame({
        "commodity_year": ["2022"] * 4, "state_abbreviation": ["KS"] * 4,
        "cause_of_loss_code": ["11", "31", "11", "21"], "month_of_loss": ["07", "07", "11", "08"],
        "net_determined_quantity": ["100", "500", "900", "50"],
    })
    insured = pd.DataFrame({
        "commodity_year": ["2022", "2022"], "state_abbreviation": ["KS", "KS"],
        "reporting_level_type": ["Acres", "Acres"], "net_reporting_level_amount": ["600", "400"],
    })
    # Drought in July and hail in August count; excess moisture and the November loss do not.
    assert np.isclose(context.loss_share(losses, insured, "nov")["loss_share"].iloc[0], 0.15)
    assert np.isclose(context.loss_share(losses, insured, "aug")["loss_share"].iloc[0], 0.10)
