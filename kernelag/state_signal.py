"""The satellite signal per state and year: the share of sampled corn acres that look silage-like.

Steps:
    1. Fit the field model on the Quebec declarations (``kernelag.field_model``).
    2. For every sampled field and corn year (``kernelag.state_sample``), turn its Sentinel-2
       series into harvest evidence and a probability of silage.
    3. Per sample area and year, add up corn acres and "silage-like" acres (acres x probability).
    4. Per state and year, combine the areas into one share.

How areas are combined: areas were drawn with probability proportional to their corn acres
(``cell_size_acres``), so each area's totals are divided by that size before summing:
    share = sum(silage_like_acres / size) / sum(corn_acres / size)

The share's LEVEL is biased, because the field model calls some grain fields silage. Read its
CHANGE between years on the same areas (``kernelag.state_model``) to reduce stable bias.
Bias need not cancel under changes in prevalence, assessability or classifier transfer.

``share_se`` is a jackknife standard error: the spread of the share when each area is left out in turn.
Only areas whose series are complete for all their years are used (``areas`` column), so the step
can be run on an unfinished pull.

Output: ``data/panel/state_satellite.csv``
    state, state_fips, year, areas, fields, assessable_share, sat_share, sat_share_calls, share_se,
    median_peak_doy, median_cut_doy

Run: ``python -m kernelag.state_signal --workers 6``
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag.context import ASOF_MONTH
from kernelag.features import build_features
from kernelag.field_model import (
    DECISION_THRESHOLD,
    MODEL_FEATURES,
    load_series,
    load_training,
    make_model,
)
from kernelag.paths import data_dir, record_in_manifest


def fit_field_model():
    """The field model fitted on every assessable Quebec parcel that has a series, all label years."""
    train, _ = load_training(data_dir())
    train = train[train["assessable"]]
    return make_model().fit(train[MODEL_FEATURES], train["is_silage"]), len(train)


def area_totals(sample: pd.DataFrame, series: pd.DataFrame, model) -> pd.DataFrame:
    """Per sample area and year: corn acres, silage-like acres and counts, from field-level evidence."""
    if sample.duplicated(["field_id", "year"]).any():
        raise ValueError("duplicate field-year in satellite sample")
    features = build_features(series) if not series.empty else pd.DataFrame(columns=["field_id", "year"])
    for column in MODEL_FEATURES + ["peak_doy", "cut_doy"]:
        if column not in features:
            features[column] = np.nan
    fields = sample.merge(features, on=["field_id", "year"], how="left")
    fields["assessable"] = fields["max_drop"].notna()
    ok = fields["assessable"].to_numpy()
    fields["p_silage"] = np.nan
    if ok.any():
        fields.loc[ok, "p_silage"] = model.predict_proba(fields.loc[ok, MODEL_FEATURES])[:, 1]
    fields["corn_acres"] = np.where(ok, fields["acres"], 0.0)
    fields["silage_like_acres"] = fields["corn_acres"] * fields["p_silage"].fillna(0.0)
    fields["called_silage_acres"] = fields["corn_acres"] * (fields["p_silage"] >= DECISION_THRESHOLD)
    grouped = fields.groupby(["cell", "year"])
    totals = grouped.agg(
        cell_size_acres=("cell_size_acres", "first"), fields=("field_id", "size"),
        sampled_acres=("acres", "sum"), corn_acres=("corn_acres", "sum"),
        silage_like_acres=("silage_like_acres", "sum"), called_silage_acres=("called_silage_acres", "sum"),
        median_peak_doy=("peak_doy", "median"), median_cut_doy=("cut_doy", "median"),
    )
    return totals.reset_index()


def series_asof(series: pd.DataFrame, asof: str = "nov") -> pd.DataFrame:
    """Enforce the forecast date even when a cached imagery pull extends through November 30."""
    limit = pd.to_datetime({"year": series["year"].astype(int), "month": ASOF_MONTH[asof], "day": 15})
    return series[series["date"] <= limit].copy()


def share(areas: pd.DataFrame, column: str = "silage_like_acres") -> float:
    """State share from sample areas drawn in proportion to size (see the module text)."""
    weight = 1.0 / areas["cell_size_acres"]
    corn = (areas["corn_acres"] * weight).sum()
    return float((areas[column] * weight).sum() / corn) if corn > 0 else float("nan")


def jackknife_se(areas: pd.DataFrame) -> float:
    """Standard error of the share from leaving out one area at a time."""
    n = len(areas)
    if n < 2:
        return float("nan")
    left_out = np.array([share(areas.drop(index)) for index in areas.index])
    return float(np.sqrt((n - 1) / n * ((left_out - left_out.mean()) ** 2).sum()))


def state_table(totals: pd.DataFrame) -> pd.DataFrame:
    """One row per year from the per-area totals of one state."""
    rows = []
    for year, areas in totals.groupby("year"):
        assessable = areas[areas["corn_acres"] > 0]
        if assessable.empty:
            continue
        rows.append({
            "year": int(year), "areas": len(areas), "assessable_areas": len(assessable),
            "fields": int(areas["fields"].sum()),
            "assessable_share": round(areas["corn_acres"].sum() / areas["sampled_acres"].sum(), 3),
            "sat_share": round(share(areas), 4),
            "sat_share_calls": round(share(areas, "called_silage_acres"), 4),
            "share_se": round(jackknife_se(assessable), 4),
            "median_peak_doy": float(areas["median_peak_doy"].median()),
            "median_cut_doy": float(areas["median_cut_doy"].median()),
        })
    return pd.DataFrame(rows)


def complete_areas(sample: pd.DataFrame, series_dir: Path) -> list[str]:
    """Areas whose series are on disk for every one of their corn years.

    Only these are used, so every year of a state rests on the same areas while a pull is unfinished.
    """
    pairs = sample[["cell", "year"]].drop_duplicates()
    on_disk = pairs.apply(lambda row: (series_dir / f"{row['cell']}_{row['year']}.csv").exists(), axis=1)
    done = on_disk.groupby(pairs["cell"]).all()
    return done[done].index.tolist()


def score_state(sample_file: str, model, asof: str = "nov") -> pd.DataFrame:
    """Everything for one state file; returns its per-year rows (empty if no series were pulled)."""
    import geopandas as gpd

    path = Path(sample_file)
    series_dir = data_dir() / "s2_series" / path.stem
    if not series_dir.is_dir() or not any(series_dir.glob("*.csv")):
        return pd.DataFrame()
    sample = pd.DataFrame(gpd.read_parquet(path).drop(columns="geometry"))
    sample["field_id"] = sample["field_id"].astype(str)
    sample = sample[sample["cell"].isin(complete_areas(sample, series_dir))]
    if sample.empty:
        return pd.DataFrame()
    series = series_asof(load_series(series_dir), asof)
    totals = area_totals(sample, series, model)
    totals.to_csv(data_dir() / "samples" / f"{path.stem}_area_totals_asof_{asof}.csv", index=False, lineterminator="\n")
    table = state_table(totals)
    if table.empty:
        return table
    table["asof_date"] = table["year"].map(lambda y: f"{int(y)}-{ASOF_MONTH[asof]:02d}-15")
    dates = series.groupby("year")["date"].max().dt.strftime("%Y-%m-%d")
    table["last_observation_date"] = table["year"].map(dates)
    table.insert(0, "state_fips", path.stem.split("_")[-1])
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--asof", choices=list(ASOF_MONTH), default="nov")
    args = parser.parse_args()
    data = data_dir()

    files = [str(p) for p in sorted((data / "samples").glob("corn_*.parquet"))]
    if not files:
        parser.exit(2, "UNCOMPUTED: no state sample files; no satellite aggregate written. Existing cache, if any, was not refreshed.\n")
    model, n_train = fit_field_model()
    print(f"field model fitted on {n_train} Quebec parcels", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tables = list(pool.map(score_state, files, [model] * len(files), [args.asof] * len(files)))
    complete = [t for t in tables if len(t)]
    if not complete:
        parser.exit(2, "UNCOMPUTED: no complete, assessable state sample series; no satellite aggregate written. Existing cache, if any, was not refreshed.\n")
    table = pd.concat(complete, ignore_index=True)

    summary = pd.read_csv(data / "samples" / "sample_summary.csv", dtype={"state_fips": str})
    names = dict(zip(summary["state_fips"].str.zfill(2), summary["state"]))
    table.insert(0, "state", table["state_fips"].map(names))
    if table["state"].isna().any() or table.duplicated(["state", "year"]).any():
        raise ValueError("unmapped states or duplicate state-years in satellite aggregate")
    suffix = "" if args.asof == "nov" else f"_asof_{args.asof}"
    target = data / "panel" / f"state_satellite{suffix}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(target, index=False, lineterminator="\n")
    record_in_manifest(target, "derived: kernelag.state_signal")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(table.to_csv(index=False))


if __name__ == "__main__":
    main()
