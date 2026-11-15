import pandas as pd

from kernelag import deliverable


def test_census_years_are_filled_and_marked():
    truth = pd.DataFrame({"year": [2018], "state": ["A"], "series": ["silage"], "actual": [100.0],
                          "truth_source": ["organizer_csv"]})
    nass = pd.DataFrame({"year": [2017, 2018], "state": ["A", "A"], "series": ["silage", "silage"],
                         "period": ["final", "final"], "acres": [90.0, 999.0]})
    out = deliverable.with_census_years(truth, nass).set_index("year")
    assert out.loc[2018, "actual"] == 100.0                      # the organizer value wins
    assert out.loc[2017, "truth_source"] == "nass_quickstats"


def test_us_row_is_the_sum_of_states():
    ours = pd.DataFrame({"year": [2020] * 2, "state": ["A", "B"], "series": ["silage"] * 2,
                         "predicted": [110.0, 90.0], "last": [100.0, 100.0]})
    truth = pd.DataFrame({"year": [2020] * 2, "state": ["A", "B"], "series": ["silage"] * 2,
                          "actual": [100.0, 100.0], "truth_source": ["organizer_csv"] * 2})
    table = deliverable.compare(ours, truth)
    us = table[table["state"].str.startswith("US")].iloc[0]
    assert us["predicted"] == 200.0 and us["error_pct"] == 0.0
    summary = deliverable.summarize(table)["silage"]["by_year"][2020]
    assert summary["state_wape_pct"] == 10.0
