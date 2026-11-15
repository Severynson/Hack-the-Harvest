"""The tidy step keeps plain totals only, and the baselines are scored as documented."""

import pandas as pd

from kernelag import nass


def _row(year, state, item, period, value, level="STATE", source="SURVEY", domain="TOTAL"):
    return {
        "year": str(year), "aggregation_level": level, "state_name": state, "state_ansi": "01",
        "county_name": "", "county_ansi": "", "short_description": item, "reference_period": period,
        "value": value, "source": source, "domain": domain,
    }


GRAIN, SILAGE, PLANTED = list(nass.SERIES)[1], list(nass.SERIES)[2], list(nass.SERIES)[0]


def test_tidy_state_drops_subrows_and_withheld_values():
    raw = pd.DataFrame([
        _row(2023, "A", GRAIN, "YEAR", "1,000"),
        _row(2023, "A", "CORN, GRAIN, IRRIGATED - ACRES HARVESTED", "YEAR", "400"),
        _row(2023, "A", SILAGE, "YEAR", "(D)"),
        _row(2023, "A", GRAIN, "YEAR - AUG FORECAST", "900"),
        _row(2023, "A", GRAIN, "YEAR", "1,000", source="CENSUS"),
    ])
    table = nass.tidy_state(raw)
    assert table[["series", "period", "acres"]].values.tolist() == [["grain", "aug", 900], ["grain", "final", 1000]]


def test_baselines_score_forecast_and_persistence():
    raw = pd.DataFrame(
        [_row(2022, s, item, "YEAR", v) for s, item, v in [
            ("A", GRAIN, "100"), ("A", SILAGE, "50"), ("A", PLANTED, "200"),
            ("B", GRAIN, "100"), ("B", SILAGE, "50"), ("B", PLANTED, "200"),
        ]]
        + [_row(2023, s, item, "YEAR", v) for s, item, v in [
            ("A", GRAIN, "110"), ("A", SILAGE, "60"), ("B", GRAIN, "90"), ("B", SILAGE, "40"),
        ]]
        + [_row(2023, "A", GRAIN, "YEAR - AUG FORECAST", "99")]
    )
    table = nass.baselines(nass.tidy_state(raw), last_year=2023).set_index(["series", "predictor"])

    silage = table.loc[("silage", "same_as_last_year")]
    assert silage["state_error_pct"] == 20.0   # |50-60| + |50-40| over 100 acres
    assert silage["total_error_pct"] == 0.0    # the two state errors cancel

    august = table.loc[("grain", "nass_aug")]
    assert august["n_states"] == 1 and august["state_error_pct"] == 10.0   # 99 against 110


def test_baselines_never_touch_the_scoring_year():
    raw = pd.DataFrame([_row(y, "A", SILAGE, "YEAR", "50") for y in (2024, 2025)]
                       + [_row(y, "A", PLANTED, "YEAR", "200") for y in (2024, 2025)]
                       + [_row(y, "A", GRAIN, "YEAR", "100") for y in (2024, 2025)])
    table = nass.baselines(nass.tidy_state(raw))
    assert table.empty or table["year"].max() <= nass.LAST_BASELINE_YEAR
