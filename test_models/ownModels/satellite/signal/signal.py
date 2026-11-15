"""Satellite silage-like shares per state and year on the fixed state sample (agent key: signal).

What it computes, for the 15 sampled states, 2019-2025, as of 15 Nov, 15 Oct and 15 Sep:
    1. The field model (``kernelag.field_model.make_model`` on ``MODEL_FEATURES``) fitted on ALL
       assessable Quebec field-years with series: quebec_maize_2023 + qc_regions_2023 (3,128 rows).
       Its reference scores (Quebec leave-one-cell-out, Maryland transfer) are recomputed and must equal
       the shared field harness (test_models/featureTests/harness.py, arms E2 and E3b, "base").
    2. Every sampled corn field-year (``data/samples/corn_<fips>.parquet``, corn = that year's Cropland
       Data Layer) gets harvest evidence from its Sentinel-2 series cut at the forecast date
       (``kernelag.state_signal.series_asof``) and a probability of silage.
    3. Per sample area and year: assessable corn acres, silage-like acres (acres x probability) and
       called-silage acres (probability >= 0.5), exactly as ``kernelag.state_signal.area_totals``.
    4. Per state and year: the share with ``kernelag.state_signal.share`` (each area divided by its
       ``cell_size_acres``, so every PPS-drawn area counts equally) and the area jackknife SE, on the
       areas whose series are complete for all their years (``kernelag.state_signal.complete_areas``).

Look-ahead: in 2019-2025 the corn fields come from that year's Cropland Data Layer, published after the
season. These shares therefore assume a perfect corn mask; a real-time 2026 share must use corn calls
from imagery, whose error is NOT in these tables (see README).

Public function for the 2026 share (the evaluation agent):
    state_shares(sample_rows, series, model, asof) -> one row per state and year

Outputs (this folder only, never data/panel/):
    out/state_satellite_asof_{nov,oct,sep}.csv          state-year shares
    out/state_satellite_changes_asof_{nov,oct,sep}.csv  year-to-year changes with a same-area jackknife SE
    out/area_totals_asof_{nov,oct,sep}.csv              per area and year totals
    out/field_probabilities_asof_{nov,oct,sep}.parquet  per field-year probability and cut day
    out/field_model_reference.csv, out/field_model_coefficients.csv, out/run_meta.json

Run from the repo root (the module name avoids shadowing the standard-library ``signal``):
    .venv/Scripts/python.exe -m test_models.ownModels.satellite.signal.signal --workers 15
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
# This file shares its name with the standard-library module ``signal``. When it is run as a plain script
# its folder would shadow that module for every later import, so the folder is taken off the import path.
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse  # noqa: E402
import json  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from kernelag.context import ASOF_MONTH  # noqa: E402
from kernelag.features import build_features  # noqa: E402
from kernelag.field_model import (  # noqa: E402
    DECISION_THRESHOLD,
    MODEL_FEATURES,
    evidence_table,
    load_series,
    make_model,
    predict_silage,
    scores,
)
from kernelag.paths import data_dir  # noqa: E402
from kernelag.state_signal import complete_areas, series_asof, share, state_table  # noqa: E402

OUT = HERE / "out"
TRAIN_SETS = ("quebec_maize_2023", "qc_regions_2023")
MARYLAND = "barc_2021_2023"
ASOFS = ("nov", "oct", "sep")
YEARS = list(range(2019, 2026))
# The harness's published "base" numbers this fit must reproduce (test_models/featureTests/results/field_summary.csv).
HARNESS_REFERENCE = {"qc_regions_loco": {"TP": 877, "FP": 345, "FN": 390, "TN": 1516},
                     "maryland_transfer_allqc": {"TP": 10, "FP": 4, "FN": 2, "TN": 28}}
OUTPUT_COLUMNS = ["state", "state_fips", "year", "areas", "fields", "assessable_share", "sat_share",
                  "sat_share_calls", "share_se", "median_cut_doy"]
EXTRA_COLUMNS = ["assessable_areas", "share_se_calls", "median_peak_doy", "corn_fields_assessable", "asof",
                 "asof_date", "last_observation_date"]
FIELD_COLUMNS = ["state_fips", "cell", "field_id", "year", "acres", "assessable", "p_silage", "cut_doy", "peak_doy"]


# ------------------------------------------------------------------------------------------ field model


def series_cells(folder: Path) -> pd.Series:
    """The 10 km cell of each field_id from per-cell file names ``<cell>_<year>.csv`` (as the harness)."""
    parts = []
    for path in sorted(folder.glob("*.csv")):
        ids = pd.read_csv(path, usecols=["field_id"])["field_id"].astype(str).unique()
        parts.append(pd.Series(path.stem.rsplit("_", 1)[0], index=ids))
    cells = pd.concat(parts) if parts else pd.Series(dtype=str)
    return cells[~cells.index.duplicated()]


def training_table(data: Path | None = None) -> pd.DataFrame:
    """Evidence rows of every labeled Quebec field-year with a series, with dataset and 10 km cell."""
    import geopandas as gpd

    data = data or data_dir()
    parts = []
    for name in TRAIN_SETS:
        labels = gpd.read_parquet(data / "labels" / f"{name}.parquet")
        folder = data / "s2_series" / name
        table = evidence_table(labels, load_series(folder))
        cells = series_cells(folder)
        if "cell" in labels:   # the labels' own column wins over file names, as in the harness
            declared = pd.Series(labels["cell"].astype(str).to_numpy(), index=labels["field_id"].astype(str))
            cells = declared[~declared.index.duplicated()].combine_first(cells)
        table["cell"] = table["field_id"].map(cells).fillna(name).astype(str)
        table.insert(0, "dataset", name)
        parts.append(table)
    return pd.concat(parts, ignore_index=True)


def fit_model(train: pd.DataFrame):
    """``make_model()`` fitted on the assessable rows of ``train``."""
    fit_part = train[train["assessable"]]
    return make_model().fit(fit_part[MODEL_FEATURES], fit_part["is_silage"])


def fit_allqc_model(data: Path | None = None):
    """The field model fitted on ALL assessable Quebec field-years (both label sets). Returns (model, train)."""
    train = training_table(data)
    return fit_model(train), train


def maryland_table(data: Path | None = None) -> pd.DataFrame:
    """All 44 Maryland field-years; one without evidence stays in the roster as not assessable (grain)."""
    import geopandas as gpd

    data = data or data_dir()
    labels = gpd.read_parquet(data / "labels" / f"{MARYLAND}.parquet")
    features = build_features(load_series(data / "s2_series" / MARYLAND))
    for column in MODEL_FEATURES:
        if column not in features:
            features[column] = np.nan
    roster = pd.DataFrame(labels[["field_id", "year", "label"]]).assign(field_id=labels["field_id"].astype(str))
    table = roster.merge(features, on=["field_id", "year"], how="left", validate="one_to_one")
    table["assessable"] = table["max_drop"].notna()
    table["is_silage"] = (table["label"] == "silage").astype(int)
    return table


def balanced_accuracy(row: dict) -> float:
    return round((row["TP"] / (row["TP"] + row["FN"]) + row["TN"] / (row["TN"] + row["FP"])) / 2, 3)


def reference_scores(train: pd.DataFrame, model, data: Path | None = None) -> pd.DataFrame:
    """Quebec leave-one-cell-out and Maryland transfer scores of the all-Quebec fit (reference only)."""
    truth = train["is_silage"].to_numpy()
    call = np.zeros(len(train), int)
    cells = train["cell"].to_numpy()
    for cell in sorted(set(cells)):
        held = cells == cell
        call[held] = predict_silage(fit_model(train[~held]), train[held].reset_index(drop=True))[1]
    rows = [{"check": "qc_regions_loco", "n": len(train), "cells": int(len(set(cells))), **scores(truth, call)}]
    maryland = maryland_table(data)
    rows.append({"check": "maryland_transfer_allqc", "n": len(maryland), "cells": np.nan,
                 **scores(maryland["is_silage"].to_numpy(), predict_silage(model, maryland)[1])})
    table = pd.DataFrame(rows)
    table["balanced_accuracy"] = [balanced_accuracy(r) for r in rows]
    table["matches_harness"] = [all(r[k] == v for k, v in HARNESS_REFERENCE[r["check"]].items()) for r in rows]
    return table


# ---------------------------------------------------------------------------------------- state shares


def clean_sample(sample_rows: pd.DataFrame) -> pd.DataFrame:
    """Sample rows as plain columns: text field_id, two-digit state_fips, integer year, no geometry."""
    sample = pd.DataFrame(sample_rows.drop(columns="geometry", errors="ignore")).copy()
    missing = {"field_id", "year", "cell", "cell_size_acres", "state_fips", "acres"} - set(sample.columns)
    if missing:
        raise ValueError(f"sample rows lack columns {sorted(missing)}")
    sample["field_id"] = sample["field_id"].astype(str)
    sample["state_fips"] = sample["state_fips"].astype(str).str.zfill(2)
    sample["cell"] = sample["cell"].astype(str)
    sample["year"] = sample["year"].astype(int)
    if sample.duplicated(["field_id", "year"]).any():
        raise ValueError("duplicate field-year in satellite sample")
    return sample.reset_index(drop=True)


def align_field_ids(series_ids: pd.Series, sample_ids: pd.Series) -> pd.Series:
    """Series field ids written as the sample's text ids.

    ``kernelag.field_model.load_series`` lets pandas read field_id as a number before turning it into text, so
    an id with a leading zero loses it (every CSB id of a state with FIPS 01-09: California 06, Colorado 08) and
    no longer joins the sample. Ids are matched on their digits without leading zeros; ids not in the sample
    become missing and drop out of the join.
    """
    ids = pd.Series(pd.unique(sample_ids.astype(str)))
    digits = ids.str.lstrip("0")
    if digits.duplicated().any():
        raise ValueError("sample field ids collide once leading zeros are removed")
    return series_ids.astype(str).str.lstrip("0").map(dict(zip(digits, ids)))


def field_table(sample: pd.DataFrame, features: pd.DataFrame, model) -> pd.DataFrame:
    """Per sampled field-year: assessable, P(silage), corn, silage-like and called acres.

    The same steps as ``kernelag.state_signal.area_totals`` (checked in test_signal.py): a field-year with no
    drop to read is not assessable and adds nothing to either numerator or denominator.
    """
    features = features.copy()
    for column in MODEL_FEATURES + ["peak_doy", "cut_doy"]:
        if column not in features:
            features[column] = np.nan
    features["field_id"] = features["field_id"].astype(str)
    features["year"] = features["year"].astype(int)
    fields = sample.merge(features, on=["field_id", "year"], how="left")
    fields["assessable"] = fields["max_drop"].notna()
    ok = fields["assessable"].to_numpy()
    fields["p_silage"] = np.nan
    if ok.any():
        fields.loc[ok, "p_silage"] = model.predict_proba(fields.loc[ok, MODEL_FEATURES])[:, 1]
    fields["corn_acres"] = np.where(ok, fields["acres"], 0.0)
    fields["silage_like_acres"] = fields["corn_acres"] * fields["p_silage"].fillna(0.0)
    fields["called_silage_acres"] = fields["corn_acres"] * (fields["p_silage"] >= DECISION_THRESHOLD)
    return fields


def area_table(fields: pd.DataFrame) -> pd.DataFrame:
    """Per state, area and year totals (``kernelag.state_signal.area_totals`` plus state_fips)."""
    grouped = fields.groupby(["state_fips", "cell", "year"])
    totals = grouped.agg(
        cell_size_acres=("cell_size_acres", "first"), fields=("field_id", "size"),
        sampled_acres=("acres", "sum"), corn_acres=("corn_acres", "sum"),
        silage_like_acres=("silage_like_acres", "sum"), called_silage_acres=("called_silage_acres", "sum"),
        median_peak_doy=("peak_doy", "median"), median_cut_doy=("cut_doy", "median"),
        corn_fields_assessable=("assessable", "sum"),
    )
    return totals.reset_index()


def jackknife(areas: pd.DataFrame, statistic) -> float:
    """Leave-one-area-out standard error of ``statistic(areas)``; ``areas`` has one row per area."""
    n = len(areas)
    if n < 2:
        return float("nan")
    left_out = np.array([statistic(areas.drop(index)) for index in areas.index])
    left_out = left_out[np.isfinite(left_out)]
    if len(left_out) < 2:
        return float("nan")
    return float(np.sqrt((n - 1) / n * ((left_out - left_out.mean()) ** 2).sum()))


def state_names() -> dict:
    summary = pd.read_csv(data_dir() / "samples" / "sample_summary.csv", dtype={"state_fips": str})
    return dict(zip(summary["state_fips"].str.zfill(2), summary["state"]))


def state_shares(sample_rows: pd.DataFrame, series: pd.DataFrame, model, asof: str = "nov",
                 detail: bool = False):
    """Per state and year: the satellite silage-like share of the sampled corn acres as of ``asof``.

    sample_rows  one row per field and year to count as corn: field_id, year, cell, cell_size_acres,
                 state_fips, acres (geometry optional). For 2026: the corn26 rows the corn classifier calls
                 corn (is_corn), year 2026. Restrict to complete areas first (``complete_sample``) and use
                 the same areas as the history the share is compared with.
    series       long Sentinel-2 table from ``kernelag.field_model.load_series`` (uncut; it is cut here at
                 the 15th of the ``asof`` month by ``kernelag.state_signal.series_asof``).
    model        a fitted field model, e.g. ``fit_allqc_model()[0]``.
    asof         "nov", "oct" or "sep" (any key of ``kernelag.context.ASOF_MONTH``).

    Returns the state-year table (OUTPUT_COLUMNS + EXTRA_COLUMNS); with ``detail=True`` returns
    ``(table, area_totals, fields)``.
    """
    if asof not in ASOF_MONTH:
        raise ValueError(f"asof must be one of {list(ASOF_MONTH)}")
    sample = clean_sample(sample_rows)
    series = series.copy()
    if len(series):
        series["field_id"] = align_field_ids(series["field_id"], sample["field_id"])
        series["year"] = series["year"].astype(int)
        keys = sample[["field_id", "year"]].drop_duplicates()
        series = series.merge(keys, on=["field_id", "year"], how="inner")
        series = series_asof(series, asof)
    features = build_features(series) if len(series) else pd.DataFrame(columns=["field_id", "year"])
    fields = field_table(sample, features, model)
    totals = area_table(fields)
    last_look = (series.groupby("year")["date"].max().dt.strftime("%Y-%m-%d") if len(series)
                 else pd.Series(dtype=str))
    names = state_names()
    tables = []
    for fips, areas in totals.groupby("state_fips"):
        table = state_table(areas.drop(columns="state_fips"))
        if table.empty:
            continue
        extra = []
        for year in table["year"]:
            year_areas = areas[(areas["year"] == year) & (areas["corn_acres"] > 0)]
            extra.append({
                "share_se_calls": round(jackknife(year_areas, lambda a: share(a, "called_silage_acres")), 4),
                "corn_fields_assessable": int(areas.loc[areas["year"] == year, "corn_fields_assessable"].sum()),
            })
        table = pd.concat([table, pd.DataFrame(extra)], axis=1)
        table.insert(0, "state_fips", fips)
        table.insert(0, "state", names.get(fips, fips))
        tables.append(table)
    columns = OUTPUT_COLUMNS + EXTRA_COLUMNS
    if not tables:
        empty = pd.DataFrame(columns=columns)
        return (empty, totals, fields) if detail else empty
    table = pd.concat(tables, ignore_index=True)
    table["asof"] = asof
    table["asof_date"] = table["year"].map(lambda y: f"{int(y)}-{ASOF_MONTH[asof]:02d}-15")
    table["last_observation_date"] = table["year"].map(last_look)
    table = table[columns].sort_values(["state", "year"]).reset_index(drop=True)
    return (table, totals, fields) if detail else table


def complete_sample(sample_rows: pd.DataFrame, series_dir: Path) -> pd.DataFrame:
    """Only the areas whose series files exist for every one of their years (``complete_areas``)."""
    sample = clean_sample(sample_rows)
    return sample[sample["cell"].isin(complete_areas(sample, Path(series_dir)))].reset_index(drop=True)


def pair_shares(wide: pd.DataFrame, size: pd.Series, column: str, years: tuple[int, int]) -> tuple[float, float]:
    """The share (``kernelag.state_signal.share``) of two years on the areas (rows) of ``wide``."""
    weight = 1.0 / size.reindex(wide.index)
    out = []
    for year in years:
        corn = (wide[("corn_acres", year)] * weight).sum()
        out.append(float((wide[(column, year)] * weight).sum() / corn) if corn > 0 else np.nan)
    return out[0], out[1]


def logit(p: float) -> float:
    return float(np.log(p / (1 - p))) if 0 < p < 1 else np.nan


CHANGES = {
    "d_share": lambda a, b: b - a,
    "d_log_share": lambda a, b: float(np.log(b / a)) if a > 0 and b > 0 else np.nan,
    "d_logit_share": lambda a, b: logit(b) - logit(a),
}


def share_changes(totals: pd.DataFrame) -> pd.DataFrame:
    """Year-to-year change of the share per state on the same areas, with a leave-one-area-out SE.

    The SE leaves each area out of BOTH years at once, so the positive correlation between years that
    comes from reusing the same areas is respected (sqrt(se_a^2 + se_b^2) would ignore it).
    Columns: d_share, d_log_share, d_logit_share (and _calls versions) with their jackknife SEs.
    """
    rows = []
    for fips, state in totals.groupby("state_fips"):
        years = sorted(state["year"].unique())
        for year in years:
            if year - 1 not in years:
                continue
            pair = state[state["year"].isin([year - 1, year])]
            wide = pair.pivot_table(index="cell", columns="year",
                                    values=["corn_acres", "silage_like_acres", "called_silage_acres"],
                                    aggfunc="sum", fill_value=0.0)
            size = pair.groupby("cell")["cell_size_acres"].first()
            wide = wide[(wide["corn_acres"] > 0).any(axis=1)]
            row = {"state_fips": fips, "year": int(year),
                   "areas_both": int((wide["corn_acres"] > 0).all(axis=1).sum()), "areas_either": len(wide)}
            for column, tag in [("silage_like_acres", ""), ("called_silage_acres", "_calls")]:
                for name, change in CHANGES.items():
                    def statistic(w: pd.DataFrame, change=change, column=column) -> float:
                        return change(*pair_shares(w, size, column, (year - 1, year)))

                    row[f"{name}{tag}"] = round(statistic(wide), 5)
                    row[f"se_{name}{tag}"] = round(jackknife(wide, statistic), 5)
            rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------- run


def score_state_file(path: str, model, asofs: tuple[str, ...] = ASOFS) -> dict:
    """All as-of dates for one state file: {asof: (table, totals, fields)} on its complete areas."""
    import geopandas as gpd

    path = Path(path)
    series_dir = data_dir() / "s2_series" / path.stem
    sample = complete_sample(gpd.read_parquet(path), series_dir)
    series = load_series(series_dir)
    return {asof: state_shares(sample, series, model, asof, detail=True) for asof in asofs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=15)
    parser.add_argument("--skip-reference", action="store_true", help="skip the leave-one-cell-out check")
    args = parser.parse_args()
    data = data_dir()
    OUT.mkdir(parents=True, exist_ok=True)

    model, train = fit_allqc_model(data)
    n_fit = int(train["assessable"].sum())
    print(f"field model fitted on {n_fit} assessable Quebec field-years ({len(train)} with series, "
          f"{train['cell'].nunique()} cells)", flush=True)
    logistic = model.named_steps["logisticregression"]
    pd.DataFrame({"feature": MODEL_FEATURES, "weight_per_std": logistic.coef_[0].round(4)}).to_csv(
        OUT / "field_model_coefficients.csv", index=False, lineterminator="\n")
    if not args.skip_reference:
        reference = reference_scores(train, model, data)
        reference.to_csv(OUT / "field_model_reference.csv", index=False, lineterminator="\n")
        print(reference.to_string(index=False), flush=True)
        if not reference["matches_harness"].all():
            raise SystemExit("field model does not reproduce the harness reference; stopping")

    files = [str(p) for p in sorted((data / "samples").glob("corn_*.parquet"))]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(score_state_file, files, [model] * len(files)))

    empty = [Path(f).stem for f, r in zip(files, results) if r["nov"][0].empty]
    if empty:   # e.g. field ids that no longer join the sample; never let a state vanish silently
        raise SystemExit(f"no assessable state-years for {empty}; stopping")
    meta = {"n_train_field_years": len(train), "n_train_assessable": n_fit, "train_sets": list(TRAIN_SETS),
            "features": MODEL_FEATURES, "decision_threshold": DECISION_THRESHOLD, "state_files": len(files),
            "asof": {}}
    for asof in ASOFS:
        tables = [r[asof][0] for r in results if len(r[asof][0])]
        table = pd.concat(tables, ignore_index=True).sort_values(["state", "year"])
        if table.duplicated(["state", "year"]).any():
            raise ValueError("duplicate state-years")
        totals = pd.concat([r[asof][1] for r in results], ignore_index=True)
        fields = pd.concat([r[asof][2] for r in results], ignore_index=True)
        table.to_csv(OUT / f"state_satellite_asof_{asof}.csv", index=False, lineterminator="\n")
        totals.to_csv(OUT / f"area_totals_asof_{asof}.csv", index=False, lineterminator="\n")
        changes = share_changes(totals)
        changes.insert(0, "state", changes["state_fips"].map(state_names()))
        changes.to_csv(OUT / f"state_satellite_changes_asof_{asof}.csv", index=False, lineterminator="\n")
        fields[FIELD_COLUMNS].assign(p_silage=fields["p_silage"].round(4)).to_parquet(
            OUT / f"field_probabilities_asof_{asof}.parquet", index=False)
        meta["asof"][asof] = {"state_years": len(table), "states": int(table["state"].nunique()),
                              "field_years": len(fields), "assessable_field_years": int(fields["assessable"].sum())}
        print(f"\nas of {asof}: {len(table)} state-years", flush=True)
        print(table[OUTPUT_COLUMNS].to_string(index=False), flush=True)
    (OUT / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
