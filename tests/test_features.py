"""A cliff (silage-like) and a fade (grain-like) must come out with different evidence."""

import numpy as np
import pandas as pd

from kernelag.features import build_features, drop_dips, kernel_features


def _series(points):
    """points: (day of year, ndvi, ndmi, ndti) -> a clear-sky field series for 2023."""
    doy, ndvi, ndmi, ndti = zip(*points)
    dates = pd.Timestamp("2023-01-01") + pd.to_timedelta(np.array(doy) - 1, unit="D")
    return pd.DataFrame({"date": dates, "ndvi": ndvi, "ndmi": ndmi, "ndti": ndti, "valid_frac": 1.0})


# Green one look, bare soil the next, little residue.
CLIFF = _series([(160, 0.5, 0.2, 0.2), (200, 0.9, 0.4, 0.2), (230, 0.88, 0.38, 0.2), (245, 0.85, 0.36, 0.2),
                 (250, 0.2, 0.0, 0.10), (260, 0.2, 0.0, 0.10), (280, 0.2, 0.0, 0.10)])
# Weeks of browning, a late harvest, a residue blanket.
FADE = _series([(160, 0.5, 0.2, 0.2), (200, 0.9, 0.4, 0.2), (230, 0.8, 0.3, 0.2), (250, 0.65, 0.2, 0.2),
                (265, 0.5, 0.1, 0.2), (280, 0.45, 0.05, 0.2), (290, 0.25, 0.0, 0.19), (298, 0.25, 0.0, 0.19)])


def test_cliff_and_fade_differ_in_the_expected_direction():
    cliff, fade = kernel_features(CLIFF), kernel_features(FADE)
    assert cliff["cut_doy"] == 250 and cliff["cut_gap_days"] == 5
    assert cliff["cut_doy"] < fade["cut_doy"]                    # silage is cut earlier
    assert cliff["green_at_cut"] > fade["green_at_cut"]          # and greener
    assert cliff["ndmi_before_cut"] > fade["ndmi_before_cut"]    # and wetter
    assert cliff["drydown_days"] < fade["drydown_days"]          # with little dry-down
    assert cliff["ndti_post"] < fade["ndti_post"]                # and less residue left


def test_a_cloud_dip_is_not_mistaken_for_a_cut():
    noisy = _series([(160, 0.5, 0.2, 0.2), (200, 0.9, 0.4, 0.2), (215, 0.3, 0.1, 0.2), (225, 0.88, 0.38, 0.2),
                     (245, 0.85, 0.36, 0.2), (250, 0.2, 0.0, 0.1), (260, 0.2, 0.0, 0.1)])
    assert kernel_features(noisy)["cut_doy"] == 250
    s = noisy.assign(doy=noisy["date"].dt.day_of_year)
    assert 215 not in drop_dips(s)["doy"].tolist()


def test_too_few_clear_looks_gives_no_features():
    sparse = CLIFF.head(3)
    assert kernel_features(sparse) == {"n_obs": 3}


def test_build_features_gives_one_row_per_field_year():
    ts = pd.concat([CLIFF.assign(field_id="a", year=2023), FADE.assign(field_id="b", year=2023)])
    table = build_features(ts)
    assert table[["field_id", "year"]].values.tolist() == [["a", 2023], ["b", 2023]]
