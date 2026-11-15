import numpy as np
import pandas as pd
import pytest

from kernelag import state_signal


def test_november_aggregate_excludes_later_scenes():
    series = pd.DataFrame({"year": [2021, 2021, 2022, 2022],
                           "date": pd.to_datetime(["2021-11-15", "2021-11-30", "2022-09-15", "2022-11-16"])})
    assert state_signal.series_asof(series)["date"].dt.day.tolist() == [15, 15]
    assert state_signal.series_asof(series, "sep")["date"].dt.strftime("%Y-%m-%d").tolist() == ["2022-09-15"]


def test_missing_series_do_not_invent_assessable_acres():
    sample = pd.DataFrame({"field_id": ["a"], "year": [2021], "cell": ["x"],
                           "cell_size_acres": [100.], "acres": [10.]})
    class NoEvidenceModel:
        def predict_proba(self, _):
            raise AssertionError("no evidence should reach the model")
    totals = state_signal.area_totals(sample, pd.DataFrame(), NoEvidenceModel())
    assert totals["sampled_acres"].iloc[0] == 10
    assert totals["corn_acres"].iloc[0] == 0
    assert np.isnan(state_signal.share(totals))
    assert state_signal.state_table(totals).empty
    with pytest.raises(ValueError, match="duplicate"):
        state_signal.area_totals(pd.concat([sample, sample]), pd.DataFrame(), NoEvidenceModel())


def test_coverage_keeps_wholly_unassessable_areas_in_denominator():
    totals = pd.DataFrame({"year": [2021, 2021], "fields": [1, 1], "cell_size_acres": [100., 100.],
                           "sampled_acres": [10., 10.], "corn_acres": [10., 0.],
                           "silage_like_acres": [5., 0.], "called_silage_acres": [10., 0.],
                           "median_peak_doy": [200., np.nan], "median_cut_doy": [250., np.nan]})
    row = state_signal.state_table(totals).iloc[0]
    assert row["assessable_share"] == .5
    assert row["areas"] == 2 and row["assessable_areas"] == 1
    assert row["fields"] == 2


def test_uncomputed_run_fails_explicitly_and_does_not_overwrite_cache(tmp_path, monkeypatch):
    import sys

    monkeypatch.setattr(state_signal, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", ["kernelag.state_signal"])
    (tmp_path / "panel").mkdir()
    target = tmp_path / "panel" / "state_satellite.csv"
    target.write_text("previous cache\n")
    with pytest.raises(SystemExit) as error:
        state_signal.main()
    assert error.value.code == 2
    assert target.read_text() == "previous cache\n"
