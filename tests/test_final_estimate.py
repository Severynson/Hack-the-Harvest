"""The final estimate never reads the scoring year's own acres."""

import numpy as np

from kernelag import final_estimate
from kernelag.state_model import add_changes
from tests.test_state_model import _panel


def _table(panel):
    return final_estimate.with_last_year(add_changes(panel), ["grain", "planted", "silage"])


def test_estimate_ignores_the_target_years_final_acres():
    years = list(range(2012, 2026))
    rng = np.random.default_rng(5)
    panel = _panel(years, {y: 1.0 for y in years})
    panel["silage"] = panel["silage"] * np.exp(rng.normal(0, 0.1, len(panel)))
    first, _ = final_estimate.estimate(_table(panel))

    scrambled = panel.copy()
    in_2025 = scrambled["year"] == 2025
    scrambled.loc[in_2025, ["silage", "grain"]] = scrambled.loc[in_2025, ["silage", "grain"]] * 7.0
    second, _ = final_estimate.estimate(_table(scrambled))

    columns = ["silage_acres", "silage_low", "silage_high", "grain_acres", "grain_low", "grain_high"]
    assert (first[columns].to_numpy() == second[columns].to_numpy()).all()
    assert first["state"].iloc[-1] == "US TOTAL"
    assert first.iloc[-1]["silage_acres"] == first.iloc[:-1]["silage_acres"].sum().round(-3) or \
        abs(first.iloc[-1]["silage_acres"] - first.iloc[:-1]["silage_acres"].sum()) <= 3000
