"""POST-HOC diagnostic (not pre-registered, information only): why does the 2026 share jump in the Corn Belt?

Written after the scored run showed 2026 shares far above 2025 in Iowa, Nebraska, Minnesota and South Dakota.
It separates two explanations on the SAME 47,948 candidate fields (every field corn in some year 2019-2025):

- season / imagery: the field model sees the whole 2026 landscape as more silage-like. Then the unmasked share
  (all candidates, no corn mask) rises from 2025 to 2026 as well, and so does the share of fields called non-corn.
- mask composition: the 2026 corn calls pick more silage-like fields. Then the unmasked share moves little.

Shares use exactly the signal agent's estimator (``signal.state_shares``, Nov 15 cut). 2025 pool: CDL corn of 2025
(``corn_<fips>`` rows, year 2025) + 2025 negatives (``noncorn25_<fips>``). 2026 pool: ``corn26_<fips>``.
Writes out/diag_2026_unmasked.csv only. Run from the repo root:
    .venv/Scripts/python.exe test_models/ownModels/satellite/eval/diag_2026.py --workers 15
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import eval as ev  # noqa: E402  (this folder's eval.py)

OUT_FILE = ev.OUT / "diag_2026_unmasked.csv"


def _state(fips: str, model) -> dict:
    import geopandas as gpd

    from kernelag.field_model import load_series

    sig = ev.load_signal_module()
    samples, series_root = ev.DATA / "samples", ev.DATA / "s2_series"
    calls = pd.read_csv(ev.CORN26_OUT / "corn26_calls.csv", dtype={"field_id": str, "state_fips": str, "cell": str})
    calls = calls[calls["state_fips"] == fips]
    corn_ids = set(calls.loc[calls["is_corn"] == 1, "field_id"])

    corn25 = gpd.read_parquet(samples / f"corn_{fips}.parquet")
    corn25 = corn25[corn25["year"] == 2025]
    neg25 = gpd.read_parquet(samples / f"noncorn25_{fips}.parquet")
    pool25 = pd.concat([corn25, neg25], ignore_index=True)
    s_corn = load_series(series_root / f"corn_{fips}")
    s_corn = s_corn[s_corn["year"].astype(int) == 2025]
    series25 = pd.concat([s_corn, load_series(series_root / f"noncorn25_{fips}")], ignore_index=True)

    pool26 = gpd.read_parquet(samples / f"corn26_{fips}.parquet")
    series26 = load_series(series_root / f"corn26_{fips}")
    noncall26 = pool26[~pool26["field_id"].astype(str).isin(corn_ids)]

    out = {"state_fips": fips}
    for tag, rows, series in [("all_2025", pool25, series25), ("all_2026", pool26, series26),
                              ("called_noncorn_2026", noncall26, series26)]:
        table = sig.state_shares(rows, series, model, "nov")
        out[f"share_{tag}"] = float(table["sat_share"].iloc[0])
        out[f"se_{tag}"] = float(table["share_se"].iloc[0])
        out[f"fields_{tag}"] = int(table["fields"].iloc[0])
        out[f"last_obs_{tag}"] = table["last_observation_date"].iloc[0]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=15)
    args = parser.parse_args()
    ev.check_prereg()
    sig = ev.load_signal_module()
    model, _ = sig.fit_allqc_model()
    states = ev.load_states()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_state, fips, model) for fips in states["state_fips"]]
        rows = [f.result() for f in futures]
    diag = states.merge(pd.DataFrame(rows), on="state_fips")
    for tag in ("all_2025", "all_2026", "called_noncorn_2026"):
        if (pd.to_datetime(diag[f"last_obs_{tag}"]) > pd.Timestamp(f"{tag[-4:]}-11-15")).any():
            raise ValueError("a diagnostic share uses a look after 15 Nov")
    nov = ev.load_shares("nov")
    sh25 = nov[nov["year"] == 2025].set_index("state")["sat_share"]
    t26 = pd.read_csv(ev.OUT / "sat_share_2026_asof_nov.csv").set_index("state")["sat_share"]
    replay = ev.pred_hist_2025().set_index("state")["sat_share"]
    neg = pd.read_csv(ev.SIGNAL_OUT / "noncorn25_share.csv")
    neg = neg[neg["asof"] == "nov"].set_index("state") if "asof" in neg else neg.set_index("state")
    diag["share_cdl_corn_2025"] = diag["state"].map(sh25)
    diag["share_pred_hist_2025"] = diag["state"].map(replay)
    diag["share_called_corn_2026"] = diag["state"].map(t26)
    diag["d_masked"] = diag["share_called_corn_2026"] - diag["share_cdl_corn_2025"]
    diag["d_unmasked"] = diag["share_all_2026"] - diag["share_all_2025"]
    if "noncorn_share" in neg:
        diag["share_noncorn_2025"] = diag["state"].map(neg["noncorn_share"])
    diag.round(4).to_csv(OUT_FILE, index=False)
    print(diag[["state", "share_cdl_corn_2025", "share_called_corn_2026", "d_masked", "share_all_2025",
                "share_all_2026", "d_unmasked", "share_called_noncorn_2026"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
