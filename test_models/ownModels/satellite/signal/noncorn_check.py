"""How silage-like do NON-corn fields look? The sensitivity of the share to a leaky corn mask.

In 2019-2025 the share is computed on Cropland Data Layer corn (a perfect mask, published after the season).
In 2026 the corn fields must be called from imagery, so some non-corn fields will be counted as corn. Their
effect on the share is roughly  leak_rate x (noncorn_share - corn_share), where noncorn_share is the
silage-like share the field model gives to non-corn fields. This script measures noncorn_share on the
2025 negatives (``data/samples/noncorn25_<fips>.parquet``: fields that were corn in some year 2019-2025 but
NOT corn in 2025), with the same estimator, areas and forecast dates as the corn share.

It does not estimate the leak rate (that is the corn classifier's job: test_models/ownModels/satellite/corn26).

Output: out/noncorn25_share.csv  (state, asof, noncorn_share, noncorn_share_calls, noncorn_assessable_share,
corn_share_2025, difference)

Run from the repo root: .venv/Scripts/python.exe -m test_models.ownModels.satellite.signal.noncorn_check
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]   # signal.py shadows the stdlib module
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import pandas as pd  # noqa: E402

from kernelag.field_model import load_series  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402

_spec = importlib.util.spec_from_file_location("satellite_signal", HERE / "signal.py")
sig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sig)


def score_noncorn(path: str, model) -> pd.DataFrame:
    import geopandas as gpd

    path = Path(path)
    series_dir = data_dir() / "s2_series" / path.stem
    sample = sig.complete_sample(gpd.read_parquet(path), series_dir)
    series = load_series(series_dir)
    return pd.concat([sig.state_shares(sample, series, model, asof) for asof in sig.ASOFS], ignore_index=True)


def main() -> None:
    model, _ = sig.fit_allqc_model()
    files = [str(p) for p in sorted((data_dir() / "samples").glob("noncorn25_*.parquet"))]
    with ProcessPoolExecutor(max_workers=15) as pool:
        tables = list(pool.map(score_noncorn, files, [model] * len(files)))
    noncorn = pd.concat(tables, ignore_index=True)
    corn = pd.concat([pd.read_csv(sig.OUT / f"state_satellite_asof_{a}.csv", dtype={"state_fips": str})
                      for a in sig.ASOFS], ignore_index=True)
    corn = corn[corn["year"] == 2025][["state", "asof", "sat_share", "sat_share_calls", "assessable_share"]]
    out = noncorn.rename(columns={"sat_share": "noncorn_share", "sat_share_calls": "noncorn_share_calls",
                                  "assessable_share": "noncorn_assessable_share", "fields": "noncorn_fields",
                                  "share_se": "noncorn_share_se"})
    out = out[["state", "state_fips", "asof", "areas", "noncorn_fields", "noncorn_assessable_share", "noncorn_share",
               "noncorn_share_calls", "noncorn_share_se"]].merge(
        corn.rename(columns={"sat_share": "corn_share_2025", "sat_share_calls": "corn_share_calls_2025",
                             "assessable_share": "corn_assessable_share_2025"}), on=["state", "asof"], how="left")
    out["difference"] = (out["noncorn_share"] - out["corn_share_2025"]).round(4)
    out["difference_calls"] = (out["noncorn_share_calls"] - out["corn_share_calls_2025"]).round(4)
    out.to_csv(sig.OUT / "noncorn25_share.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
