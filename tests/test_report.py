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


def test_comparison_keeps_sampled_scope_and_absolute_total_error():
    rows = pd.DataFrame([
        {"scope": scope, "series": "silage", "predictor": "same_as_last_year", "year": year,
         "n_states": count, "state_error_pct": error, "total_error_pct": total}
        for scope, count, error, year, total in
        [("all_states", 48, 12., 2020, -5.), ("all_states", 48, 14., 2021, 5.),
         ("sampled_states", 10, 8., 2020, 3.)]])
    table = report.comparison_rows({"state_model": {}, "score_2025": {}}, rows)
    all_states = table[table["scope"] == "all_states"].iloc[0]
    assert all_states["state_wape_pct"] == 13
    assert all_states["national_abs_error_pct"] == 5
    assert all_states["minimum_states"] == 48
    assert len(table) == 2
