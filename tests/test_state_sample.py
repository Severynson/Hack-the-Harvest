"""The state sample is drawn in proportion to corn acres, is repeatable, and keeps only corn years."""

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from kernelag import state_sample


def test_systematic_pps_favours_large_cells_and_is_repeatable():
    sizes = pd.Series({"big": 900.0, "a": 25.0, "b": 25.0, "c": 25.0, "d": 25.0, "empty": 0.0})
    hits = sum("big" in state_sample.systematic_pps(sizes, 1, np.random.default_rng(seed)) for seed in range(400))
    assert 330 < hits < 390                                   # expected 90% of draws
    first = state_sample.systematic_pps(sizes, 2, np.random.default_rng(7))
    assert first == state_sample.systematic_pps(sizes, 2, np.random.default_rng(7))
    assert "empty" not in state_sample.systematic_pps(sizes, 10, np.random.default_rng(1))


def _fake_boundaries(path):
    """Three states' worth of square fields on the real file's layout (equal-area metres)."""
    rows, shapes = [], []
    rng = np.random.default_rng(0)
    for i in range(400):
        x, y = rng.uniform(0, 60_000), rng.uniform(0, 60_000)
        shapes.append(box(x, y, x + 300, y + 300))
        years = {f"CDL{year}": int(rng.choice([1, 5, 225])) for year in range(2018, 2026)}
        rows.append({"CSBID": f"55{i:013d}", "CSBACRES": 22.0 if i % 9 else 2.0,
                     "STATEFIPS": "55" if i % 4 else "19", "CNTYFIPS": "001",
                     "INSIDE_X": x + 150, "INSIDE_Y": y + 150, **years})
    gpd.GeoDataFrame(rows, geometry=shapes, crs="EPSG:5070").to_file(path, layer=state_sample.LAYER)


def test_choose_sample_writes_corn_field_years_for_the_chosen_areas(tmp_path, monkeypatch):
    monkeypatch.setenv("KERNEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KERNEL_NO_MANIFEST", "1")
    dataset = tmp_path / "csb.gpkg"
    _fake_boundaries(dataset)
    states = pd.DataFrame({"state": ["WISCONSIN"], "state_fips": ["55"], "silage_acres_2024": [1]})

    summary = state_sample.choose_sample(dataset, states, cells_per_state=3)
    table = gpd.read_parquet(tmp_path / "data" / "samples" / "corn_55.parquet")

    assert summary["cells_sampled"].iloc[0] == 3 and table["cell"].nunique() == 3
    assert set(table["state_fips"]) == {"55"}                 # the other state's fields are left out
    assert table["acres"].min() >= state_sample.MIN_ACRES     # small fields are left out
    assert set(table["year"]) <= set(state_sample.YEARS)      # 2018 is not a sample year
    source = gpd.read_file(dataset, layer=state_sample.LAYER).set_index("CSBID")
    for row in table.sample(20, random_state=0).itertuples():  # every row is a corn year for that field
        assert source.loc[row.field_id, f"CDL{row.year}"] in state_sample.CORN_CODES
    centre = table.geometry.representative_point()             # every field sits inside its area
    assert (state_sample.cell_of(centre.x, centre.y) == table["cell"]).all()
