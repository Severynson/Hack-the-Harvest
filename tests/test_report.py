import pandas as pd

from kernelag import report


def test_uncomputed_values_show_a_dash():
    assert report.acres(None) == report.DASH
    assert report.number(float("nan"), 1, "%") == report.DASH
    assert report.dig({"a": {"b": 1}}, "a", "c") is None
    assert report.range_bar(None, None, None, 10.0, "silage") == report.DASH


def test_page_renders_with_no_inputs():
    metrics = {"built_utc": "x", "forecast_year": 2026, "us_forecast": {}, "state_model": {},
               "state_model_asof_sep": {}, "score_2025": {}, "field_eval": {}}
    empty = pd.DataFrame()
    tables = {"forecast": pd.DataFrame(columns=["state", "silage"]), "last_silage": pd.Series(dtype=float),
              "backtest": empty, "bias": empty, "earliness": empty, "weights": empty, "curves": empty}
    page = report.render(metrics, tables)
    assert page.startswith("<!doctype html>") and report.DASH in page
    assert "http" not in page.replace("http://www.w3.org", "")     # nothing is fetched from the network
