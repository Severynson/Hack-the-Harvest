import numpy as np
import pandas as pd

from kernelag import silage_level


def _history(drought_year: int = 2018) -> dict:
    years = range(2000, 2021)
    states = ["A", "B", "C"]
    rng = np.random.default_rng(0)
    noise = pd.DataFrame(np.exp(rng.normal(0, 0.1, (len(years), 3))), index=years, columns=states)
    grain = pd.DataFrame(1_000_000.0, index=years, columns=states)
    yield_final = pd.DataFrame(150.0, index=years, columns=states)
    yield_asof = yield_final.copy()
    yield_asof.loc[[2008, drought_year], "A"] = 90.0       # 40% shortfall in A
    silage = 100_000.0 * noise
    silage.loc[[2008, drought_year], "A"] += 0.05 * 0.30 * 1_000_000   # gamma 0.05 chops that much
    return {"silage": silage, "grain": grain, "grain_asof": grain, "yield": yield_final, "yield_asof": yield_asof}


def test_drought_chopping_is_learned_from_earlier_years():
    history = _history()
    predicted, params = silage_level.predict(history, 2018)
    assert params["gamma"] > 0
    assert predicted["A"] > predicted["B"] + 5_000      # the drought state gets the chopped acres


def test_future_silage_does_not_change_the_forecast():
    history = _history()
    before, _ = silage_level.predict(history, 2015)
    history["silage"].loc[2015:] *= 3
    after, _ = silage_level.predict(history, 2015)
    assert np.allclose(before, after)
