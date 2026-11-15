"""The state panel picks the latest in-season figure, and the backtest never sees the future."""

import numpy as np
import pandas as pd

from kernelag import state_model
from kernelag.state_panel import latest_available


def test_latest_available_prefers_the_latest_period():
    table = pd.DataFrame({
        "state": ["A", "A", "B"], "year": [2023, 2023, 2023],
        "period": ["aug", "nov", "aug"], "value": [90.0, 100.0, 50.0],
    })
    asof = latest_available(table, ["nov", "oct", "sep", "aug"])
    assert asof[("A", 2023)] == 100.0 and asof[("B", 2023)] == 50.0


def _panel(years, silage_by_year):
    rows = []
    for state, scale in [("A", 1.0), ("B", 2.0), ("C", 0.5)]:
        for year in years:
            rows.append({
                "state": state, "year": year, "silage": 100.0 * scale * silage_by_year[year],
                "grain": 900.0, "planted": 1000.0, "planted_asof": 1000.0, "grain_asof": 900.0,
                "grain_yield": 180.0, "grain_yield_asof": 180.0, "milk_cows": 50.0, "cattle": 80.0,
                "corn_price_sep": 4.0,
            })
    return pd.DataFrame(rows)


def test_changes_use_the_previous_calendar_year_only():
    years = list(range(2010, 2016))
    panel = _panel(years, {y: 1.0 for y in years})
    panel = panel[~((panel["state"] == "A") & (panel["year"] == 2013))]   # a gap year for state A
    table = state_model.add_changes(panel)
    gap = table[(table["state"] == "A") & (table["year"] == 2014)].iloc[0]
    assert np.isnan(gap["silage_last"]) and np.isnan(gap["target"])       # no 2013, so no "last year"


def test_backtest_excludes_the_scoring_year_and_learns_reversion():
    years = list(range(2010, 2026))
    # Silage alternates high and low around a flat level: last year's deviation always reverses.
    level = {y: (1.2 if y % 2 else 0.8) for y in years}
    table = state_model.add_changes(_panel(years, level))
    results = state_model.backtest(table)

    assert results["year"].max() <= state_model.LAST_BASELINE_YEAR
    silage = results[results["series"] == "silage"]
    mean_error = silage.groupby("predictor")["state_error_pct"].mean()
    assert mean_error["reversion_only"] < mean_error["same_as_last_year"]


def test_selection_prefers_the_smallest_set_within_tolerance():
    def rows(errors):
        return pd.DataFrame([{"scope": "all_states", "year": 2020, "series": "silage", "predictor": name, "state_error_pct": error}
                             for name, error in errors.items()])

    close = rows({"reversion_only": 13.2, "nass_acres": 13.0, "stress": 13.1, "all_public": 14.0})
    assert state_model.select_feature_set(close) == "reversion_only"      # 0.2 worse, but one feature
    clear = rows({"reversion_only": 13.5, "nass_acres": 13.4, "stress": 12.0, "all_public": 12.1})
    assert state_model.select_feature_set(clear) == "stress"


def test_intervals_cover_at_about_their_nominal_rate():
    rng = np.random.default_rng(0)
    n = 3000
    held_out = pd.DataFrame({
        "year": rng.integers(2015, 2025, n), "state": [f"S{i}" for i in range(n)],
        "last": rng.uniform(1e3, 1e6, n), "predicted": 1000.0,
    })
    held_out["actual"] = held_out["predicted"] * np.exp(rng.normal(0, 0.15, n))
    coverage = state_model.interval_coverage(held_out)
    assert abs(coverage["80"] - 0.80) < 0.03 and abs(coverage["90"] - 0.90) < 0.03


def test_forecast_never_fits_on_the_forecast_year_or_later():
    years = list(range(2010, 2026))
    level = {y: (1.2 if y % 2 else 0.8) for y in years}
    table = state_model.add_changes(_panel(years, level))
    before = state_model.predict_silage(table, 2020, ["reversion"])
    changed = table.copy()
    changed.loc[changed["year"] >= 2020, "target"] = 5.0                  # absurd later outcomes
    assert np.allclose(before, state_model.predict_silage(changed, 2020, ["reversion"]))


def test_grain_falls_back_from_nass_forecast_to_share_to_last_year():
    table = pd.DataFrame({
        "state": ["A", "B", "C"], "year": 2024,
        "grain_asof": [900.0, np.nan, np.nan], "planted_asof": [1000.0, 2000.0, np.nan],
        "grain_last": [800.0, 500.0, 300.0], "planted_last": [1000.0, 1000.0, 400.0],
    })
    grain = state_model.predict_grain(table, 2024)
    assert grain["grain"].tolist() == [900.0, 1000.0, 300.0]
    assert grain["grain_method"].tolist() == ["nass_forecast", "planted_x_last_share", "same_as_last_year"]


def test_satellite_rows_stay_uncomputed_without_satellite_shares():
    years = list(range(2010, 2025))
    table = state_model.add_changes(_panel(years, {y: (1.2 if y % 2 else 0.8) for y in years}))
    results = state_model.backtest(table)
    assert set(results["scope"]) == {"all_states"}
    assert not {"reversion_plus_satellite", "satellite_ratio"} & set(results["predictor"])


def test_satellite_change_is_used_when_it_tracks_the_truth():
    years = list(range(2010, 2025))
    rng = np.random.default_rng(3)
    panel = _panel(years, {y: 1.0 for y in years})
    # Each state's silage wanders at random; the satellite share follows it with a constant bias.
    panel["silage"] = panel["silage"] * np.exp(rng.normal(0, 0.15, len(panel)))
    panel["sat_share"] = 0.10 + 0.4 * panel["silage"] / 1000.0
    results = state_model.backtest(state_model.add_changes(panel))
    silage = results[(results["scope"] == "sampled_states") & (results["series"] == "silage")]
    sampled = silage.groupby("predictor")["state_error_pct"].mean()
    assert sampled["reversion_plus_satellite"] < sampled["same_as_last_year"]
    assert sampled["reversion_plus_satellite"] < sampled["reversion_only"]


def test_early_replay_does_not_load_full_season_satellite(tmp_path, monkeypatch):
    from kernelag import state_panel

    (tmp_path / "panel").mkdir()
    (tmp_path / "panel" / "state_satellite.csv").write_text("state,year,sat_share\nA,2024,0.2\n")
    pd.DataFrame({"state": ["A"]}).to_csv(tmp_path / "acres.csv", index=False)
    (tmp_path / "nass").mkdir()
    (tmp_path / "nass" / "corn_acres_state.csv").write_bytes((tmp_path / "acres.csv").read_bytes())
    monkeypatch.setattr(state_panel, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(state_panel, "build_context", lambda *_: None)
    monkeypatch.setattr(state_panel, "build_panel", lambda acres, folder, context, asof, satellite: satellite)
    assert state_panel.load_panel("sep") is None
    assert state_panel.load_panel("nov")["sat_share"].iloc[0] == 0.2
