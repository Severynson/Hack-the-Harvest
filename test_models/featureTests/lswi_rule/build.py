"""The published September moisture rule (Lin et al. 2025) as a benchmark call and as field features.

Lin et al. 2025 (Agronomy 15(6):1438, "TempDiff-SMID", Hohhot, Inner Mongolia) is the only
peer-reviewed silage-versus-grain maize classifier we found (DOCS/research/precedent.md 3.1,
optical_harvest.md 3). Their tree first recognises maize (conditions 1 and 2) and then splits it
with one fixed calendar test, condition 3: September LSWI <= 0.15 means silage ("after silage maize
is harvested ... the cultivated land becomes bare land with lower moisture content"), otherwise grain.
Every field here is already known to be maize, so only condition 3 decides silage or grain.

LSWI = (NIR - SWIR1) / (NIR + SWIR1), which is the repo's ``ndmi`` column ((B8A - B11) / (B8A + B11),
reflectance offset already removed by kernelag.s2_series).

The paper's "September" value comes from a Whittaker-smoothed 15-day series whose smoothing parameter
and exact September step are not published (precedent.md, recipe A "Unknowns"). Our literal port,
fixed BEFORE any evaluation and never changed after it:
    lswi_rule_silage = 1 if the median LSWI of the field's clear September looks <= 0.15, else 0
    (clear look = valid_frac >= 0.5; NaN when the field-year has no clear September look)
The median of the month's clear looks is the closest unsmoothed stand-in for a monthly value of a
smoothed series, and is the form already written down in optical_harvest.md 12.5.

Pre-registered model features (at most 2): lswi_sep_median, lswi_sep_min.
Other columns are descriptive only: alternative readings of "September" kept at the SAME 0.15
threshold (min, last clear look, second half of September) so the sensitivity to the unpublished
detail can be reported, and the July / May values behind Lin's maize conditions 1 and 2.

Inputs:  data/s2_series/<dataset>/*.csv (field_id, date, year, valid_frac, ndvi, ndmi, ...)
         data/labels/<dataset>.parquet (Quebec datasets only, for the descriptive rule check)
Outputs (next to this file, in out/):
    features.csv            dataset, field_id, year, lswi_* columns; one row per field-year with a series
    meta.json               the field-feature contract (group "lswi")
    rule_eval_quebec.csv    the rule scored as published on Quebec labels, per cell and pooled
    class_summary_quebec.csv  Quebec-only class comparison of the September values
    calendar_check_quebec.csv Quebec-only check of the rule's premise (cut by September? dry after it?)
Maryland (barc_2021_2023) is a test set: its features are built, but its labels are never read here.

Run from the repository root:
    PYTHONPATH=. .venv/Scripts/python.exe test_models/featureTests/lswi_rule/build.py
    PYTHONPATH=. .venv/Scripts/python.exe test_models/featureTests/lswi_rule/build.py --datasets qc_regions_2023
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag.field_model import load_series, scores
from kernelag.paths import data_dir

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DEFAULT_DATASETS = ["quebec_maize_2023", "qc_regions_2023", "barc_2021_2023"]
QUEBEC_DATASETS = {"quebec_maize_2023", "qc_regions_2023"}   # the only labels this script may read
TEST_ONLY = {"barc_2021_2023"}                                 # features built, labels never opened

LSWI_THRESHOLD = 0.15     # Lin et al. 2025, condition 3; published value, never tuned here
JULY_LSWI_MIN = 0.16      # Lin et al. 2025, condition 2 (maize recognition; descriptive only)
MAY_NDVI_MAX = 0.20       # Lin et al. 2025, condition 1, bare in May (elevation part not available)
JULY_NDVI_MIN = 0.20      # Lin et al. 2025, condition 1, green in July
MIN_VALID = 0.5           # a look counts when at least half the field's pixels were cloud-free
LATE_SEPTEMBER_DAY = 16   # "second half of September", the literal-port guess in precedent.md recipe A

GROUP = "lswi"
RULE_COLUMN = "lswi_rule_silage"
FEATURES = ["lswi_sep_median", "lswi_sep_min"]   # pre-registered before any evaluation
# Same threshold, different readings of "the September value"; reported, never promoted.
SENSITIVITY_RULES = {
    "lswi_rule_sep_min": "lswi_sep_min",
    "lswi_rule_sep_last": "lswi_sep_last",
    "lswi_rule_sep_late": "lswi_sep_late_median",
}
FEATURE_COLUMNS = [
    "lswi_sep_n", "lswi_sep_median", "lswi_sep_min", "lswi_sep_mean", "lswi_sep_last",
    "lswi_sep_late_n", "lswi_sep_late_median", "lswi_jul_median", "lswi_ndvi_may_median",
    "lswi_ndvi_jul_median", RULE_COLUMN, *SENSITIVITY_RULES, "lswi_c1_pass", "lswi_c2_pass",
]


def september_lswi(series: pd.DataFrame) -> pd.DataFrame:
    """Per field-year September LSWI statistics and the published rule call.

    ``series`` needs field_id, year, date (datetime), valid_frac, ndmi and ndvi. A field-year with
    no clear look in a month gets NaN for that month; nothing is interpolated or imputed.
    """
    clear = series[(series["valid_frac"] >= MIN_VALID)].copy()
    clear["field_id"] = clear["field_id"].astype(str)
    clear["year"] = clear["year"].astype(int)
    clear["month"] = clear["date"].dt.month
    keys = ["field_id", "year"]
    base = series.assign(field_id=series["field_id"].astype(str), year=series["year"].astype(int))
    out = base[keys].drop_duplicates().set_index(keys).sort_index()

    sep = clear[(clear["month"] == 9) & clear["ndmi"].notna()].sort_values("date")
    by_field = sep.groupby(keys)["ndmi"]
    out["lswi_sep_n"] = by_field.size()
    out["lswi_sep_median"] = by_field.median()
    out["lswi_sep_min"] = by_field.min()
    out["lswi_sep_mean"] = by_field.mean()
    out["lswi_sep_last"] = by_field.last()   # sorted by date, so the latest clear September look
    late = sep[sep["date"].dt.day >= LATE_SEPTEMBER_DAY].groupby(keys)["ndmi"]
    out["lswi_sep_late_n"] = late.size()
    out["lswi_sep_late_median"] = late.median()
    out[["lswi_sep_n", "lswi_sep_late_n"]] = out[["lswi_sep_n", "lswi_sep_late_n"]].fillna(0).astype(int)

    # Inputs of Lin's maize-recognition conditions, kept only to describe how the full tree would
    # treat fields we already know are maize.
    out["lswi_jul_median"] = clear[(clear["month"] == 7) & clear["ndmi"].notna()].groupby(keys)["ndmi"].median()
    out["lswi_ndvi_may_median"] = clear[(clear["month"] == 5) & clear["ndvi"].notna()].groupby(keys)["ndvi"].median()
    out["lswi_ndvi_jul_median"] = clear[(clear["month"] == 7) & clear["ndvi"].notna()].groupby(keys)["ndvi"].median()

    out[RULE_COLUMN] = threshold_call(out["lswi_sep_median"])
    for rule, statistic in SENSITIVITY_RULES.items():
        out[rule] = threshold_call(out[statistic])
    c1_inputs = out[["lswi_ndvi_may_median", "lswi_ndvi_jul_median"]].notna().all(axis=1)
    c1 = (out["lswi_ndvi_may_median"] <= MAY_NDVI_MAX) & (out["lswi_ndvi_jul_median"] >= JULY_NDVI_MIN)
    out["lswi_c1_pass"] = c1.astype("Int64").where(c1_inputs)
    out["lswi_c2_pass"] = threshold_call(out["lswi_jul_median"], at_or_below=False, threshold=JULY_LSWI_MIN)
    return out.reset_index()[keys + FEATURE_COLUMNS]


def threshold_call(values: pd.Series, *, at_or_below: bool = True, threshold: float = LSWI_THRESHOLD) -> pd.Series:
    """1/0 call from a fixed threshold; missing evidence stays missing (<NA>), never a call."""
    hit = values <= threshold if at_or_below else values >= threshold
    return hit.astype("Int64").where(values.notna())


def load_dataset_series(series_dir: Path) -> pd.DataFrame:
    """All per-cell series CSVs of one dataset, each row tagged with its cell (file name minus year)."""
    parts = [load_series(f).assign(cell=f.stem.rsplit("_", 1)[0]) for f in sorted(series_dir.glob("*.csv"))]
    series = pd.concat(parts, ignore_index=True)
    return series.drop_duplicates(["field_id", "year", "date"])


def build_dataset(name: str, data: Path) -> tuple[pd.DataFrame | None, pd.DataFrame | None, str]:
    """(features, series, reason). Both frames are None when the dataset has no series to read."""
    series_dir = data / "s2_series" / name
    if not series_dir.is_dir() or not any(series_dir.glob("*.csv")):
        return None, None, f"no Sentinel-2 series under data/s2_series/{name}"
    series = load_dataset_series(series_dir)
    features = september_lswi(series).assign(dataset=name)
    features = features.round({c: 4 for c in FEATURE_COLUMNS if features[c].dtype == float})
    return features[["dataset", "field_id", "year", *FEATURE_COLUMNS]], series, ""


def merge_previous(new: pd.DataFrame, rebuilt: list[str], path: Path) -> pd.DataFrame:
    """Keep rows of datasets not rebuilt in this run, so a partial re-run never drops other datasets."""
    if not path.is_file():
        return new
    old = pd.read_csv(path, dtype={"field_id": str})
    old = old[~old["dataset"].isin(rebuilt)]
    if old.empty:
        return new
    for column in [RULE_COLUMN, *SENSITIVITY_RULES, "lswi_c1_pass", "lswi_c2_pass"]:
        old[column] = old[column].astype("Int64")
    return pd.concat([old, new], ignore_index=True) if not new.empty else old


def balanced_accuracy(table: dict) -> float:
    """Mean of silage recall and grain recall; NaN when a class is absent."""
    silage = table["TP"] / (table["TP"] + table["FN"]) if table["TP"] + table["FN"] else np.nan
    grain = table["TN"] / (table["TN"] + table["FP"]) if table["TN"] + table["FP"] else np.nan
    return round((silage + grain) / 2, 3)


def score_rule(group: pd.DataFrame, rule: str) -> dict:
    """The rule scored as published: coverage, confusion matrix on covered rows, and the same with
    uncovered rows scored as grain (the repo's convention for not-assessable fields)."""
    covered = group[group[rule].notna()]
    truth = covered["is_silage"].to_numpy()
    covered_scores = scores(truth, covered[rule].astype(int).to_numpy())
    all_call = group[rule].fillna(0).astype(int).to_numpy()
    all_scores = scores(group["is_silage"].to_numpy(), all_call)
    return {
        "rule": rule, "n_labeled_with_series": len(group), "n_covered": len(covered),
        "coverage": round(len(covered) / len(group), 3) if len(group) else np.nan,
        **{k: covered_scores[k] for k in ["n_silage", "n_grain", "TP", "FP", "FN", "TN", "silage_precision",
                                           "silage_recall", "grain_precision", "grain_recall", "accuracy"]},
        "balanced_accuracy": balanced_accuracy(covered_scores),
        "balanced_accuracy_all_rows": balanced_accuracy(all_scores),
        "silage_share": round(float(truth.mean()), 3) if len(truth) else np.nan,
    }


def september_calendar(clear_dates: pd.DataFrame) -> str:
    """Days of September on which at least one field of the group had a clear look (for the caveat)."""
    days = clear_dates.loc[clear_dates["date"].dt.month == 9, "date"].dt.strftime("%m-%d").unique()
    return " ".join(sorted(days))


def quebec_table(features: pd.DataFrame, cells: pd.DataFrame, data: Path) -> pd.DataFrame:
    """Quebec labels joined to the rule columns and each field-year's cell. Only Quebec labels are read."""
    tables = []
    for name in sorted(QUEBEC_DATASETS & set(features["dataset"])):
        # Plain pandas: only three attribute columns are needed, so the geometry is never decoded.
        labels = pd.read_parquet(data / "labels" / f"{name}.parquet", columns=["field_id", "year", "label"])
        labels = labels.assign(field_id=labels["field_id"].astype(str), year=labels["year"].astype(int))
        tables.append(labels.merge(features[features["dataset"] == name], on=["field_id", "year"], how="inner"))
    table = pd.concat(tables, ignore_index=True).merge(cells, on=["dataset", "field_id", "year"], how="left")
    return table.assign(is_silage=(table["label"] == "silage").astype(int))


def evaluate_quebec(table: pd.DataFrame, clear_dates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score the published rule (and its same-threshold readings) on Quebec labels; nothing is fitted.

    Rows: every cell, each dataset pooled, and all Quebec pooled (dataset "quebec_all").
    """
    pooled = pd.concat([table, table.assign(dataset="quebec_all")], ignore_index=True)
    dates = pd.concat([clear_dates, clear_dates.assign(dataset="quebec_all")], ignore_index=True)
    groups = [(name, "all", part) for name, part in pooled.groupby("dataset")]
    groups += [(name, cell, part) for (name, cell), part in table.groupby(["dataset", "cell"])]
    rows = []
    for dataset, cell, part in groups:
        group_dates = dates[(dates["dataset"] == dataset) & ((cell == "all") | (dates["cell"] == cell))]
        for rule in [RULE_COLUMN, *SENSITIVITY_RULES]:
            rows.append({"dataset": dataset, "cell": cell, **score_rule(part, rule),
                         "september_clear_days": september_calendar(group_dates)})

    summary = []
    for (dataset, label), part in pooled.groupby(["dataset", "label"]):
        row = {"dataset": dataset, "label": label, "n": len(part)}
        for column in ["lswi_sep_median", "lswi_sep_min", "lswi_sep_late_median", "lswi_jul_median"]:
            values = part[column].dropna()
            for name, q in [("q25", 0.25), ("q50", 0.5), ("q75", 0.75)]:
                row[f"{column}_{name}"] = round(float(values.quantile(q)), 3) if len(values) else np.nan
        row["share_sep_median_le_015"] = round(float((part["lswi_sep_median"] <= LSWI_THRESHOLD).mean()), 3)
        row["share_c1_pass"] = round(float(part["lswi_c1_pass"].astype("float").mean()), 3)
        row["share_c2_pass"] = round(float(part["lswi_c2_pass"].astype("float").mean()), 3)
        summary.append(row)
    return pd.DataFrame(rows), pd.DataFrame(summary)


def calendar_check(table: pd.DataFrame, series: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Quebec-only check of the rule's premise: is the field already cut in September, and is it dry then?

    Lin et al. state silage was "fully harvested by 10 September 2023" in Hohhot. Here the cut date is
    kernelag's ``cut_doy`` (first clear look after the biggest NDVI drop, so it trails the real cut by up
    to the gap between clear looks), and the moisture after the cut is LSWI on that same look.
    """
    from kernelag.features import build_features

    cuts = []
    for name, part in series.items():
        cut = build_features(part)[["field_id", "year", "cut_doy"]].dropna()
        clear = part[(part["valid_frac"] >= MIN_VALID)].assign(cut_doy=lambda d: d["date"].dt.day_of_year)
        clear = clear.drop_duplicates(["field_id", "year", "cut_doy"])[["field_id", "year", "cut_doy", "ndmi"]]
        cuts.append(cut.astype({"cut_doy": int}).merge(clear, on=["field_id", "year", "cut_doy"], how="left")
                    .rename(columns={"ndmi": "lswi_at_cut"}).assign(dataset=name))
    table = table.merge(pd.concat(cuts, ignore_index=True), on=["dataset", "field_id", "year"], how="left")
    cut_date = pd.to_datetime(table["year"].astype(str) + "-01-01") + pd.to_timedelta(table["cut_doy"] - 1, unit="D")
    table = table.assign(cut_date=cut_date)
    pooled = pd.concat([table, table.assign(dataset="quebec_all")], ignore_index=True)
    rows = []
    for (dataset, label), part in pooled.groupby(["dataset", "label"]):
        dated = part[part["cut_date"].notna()]
        sep10 = pd.to_datetime(dated["year"].astype(str) + "-09-10")
        sep30 = pd.to_datetime(dated["year"].astype(str) + "-09-30")
        in_september = dated[dated["cut_date"].dt.month == 9]
        rows.append({
            "dataset": dataset, "label": label, "n": len(part), "n_with_cut_date": len(dated),
            "cut_doy_q25": dated["cut_doy"].quantile(0.25), "cut_doy_q50": dated["cut_doy"].median(),
            "cut_doy_q75": dated["cut_doy"].quantile(0.75),
            "share_cut_by_sep10": round(float((dated["cut_date"] <= sep10).mean()), 3),
            "share_cut_by_sep30": round(float((dated["cut_date"] <= sep30).mean()), 3),
            "n_cut_in_september": len(in_september),
            "lswi_at_september_cut_q50": round(float(in_september["lswi_at_cut"].median()), 3),
            "share_september_cut_lswi_le_015": round(float((in_september["lswi_at_cut"] <= LSWI_THRESHOLD).mean()), 3),
        })
    return pd.DataFrame(rows)


def cell_latitudes(data: Path, cells: pd.DataFrame) -> pd.DataFrame:
    """Median latitude of the labeled fields of each Quebec cell, to read the rule against the calendar."""
    import geopandas as gpd

    parts = []
    for name, part in cells.groupby("dataset"):
        labels = gpd.read_parquet(data / "labels" / f"{name}.parquet", columns=["field_id", "geometry"])
        labels = labels[labels["field_id"].astype(str).isin(set(part["field_id"]))]
        points = gpd.GeoSeries(labels.geometry.representative_point(), crs=labels.crs).to_crs(4326)
        lat = pd.DataFrame({"field_id": labels["field_id"].astype(str).to_numpy(), "lat": points.y.to_numpy()})
        merged = lat.merge(part.drop_duplicates("field_id"), on="field_id")
        parts.append(merged.groupby(["dataset", "cell"], as_index=False)["lat"].median())
    return pd.concat(parts, ignore_index=True).rename(columns={"lat": "cell_lat"}).round({"cell_lat": 2})


def write_meta(built: list[str], uncomputed: dict[str, str], path: Path) -> None:
    """The contract's meta.json; datasets built earlier and not rebuilt now are kept."""
    previous = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    datasets = sorted((set(previous.get("datasets_built", [])) - set(uncomputed)) | set(built))
    # Earlier reasons are kept only for the contract's datasets, so a one-off name does not linger.
    old_uncomputed = {k: v for k, v in previous.get("uncomputed", {}).items()
                      if k not in built and k in DEFAULT_DATASETS}
    meta = {
        "group": GROUP,
        "features": FEATURES,
        "rule_column": RULE_COLUMN,
        "description": (
            "Published September moisture rule, Lin et al. 2025 (Agronomy 15(6):1438, TempDiff-SMID, Hohhot): "
            "silage if September LSWI <= 0.15, else grain. LSWI = repo ndmi (B8A, B11). Literal port fixed before "
            "evaluation: rule = median of clear (valid_frac >= 0.5) Sentinel-2 looks dated 1-30 September <= 0.15; "
            "NaN when the field-year has no clear September look. Features: that median and the September minimum. "
            "Calendar-bound by design: the paper's thresholds were re-tuned by hand each year and one harvest "
            "calendar does not transfer across regions."
        ),
        "datasets_built": datasets,
        "uncomputed": {**old_uncomputed, **uncomputed},
        "rule_definition": {"statistic": "median of clear September ndmi looks", "direction": "<=",
                            "threshold": LSWI_THRESHOLD, "min_valid_frac": MIN_VALID, "months": [9]},
        "sensitivity_rule_columns": SENSITIVITY_RULES,
        "registered_before_evaluation": True,
    }
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS)
    args = parser.parse_args()
    data = data_dir()
    OUT.mkdir(parents=True, exist_ok=True)

    built, uncomputed, frames, loaded = [], {}, [], {}
    for name in args.datasets:
        features, series, reason = build_dataset(name, data)
        if features is None:
            print(f"UNCOMPUTED {name}: {reason}")
            uncomputed[name] = reason
            continue
        built.append(name)
        frames.append(features)
        loaded[name] = (features, series)
        print(f"{name}: {len(features)} field-years, {int(features[RULE_COLUMN].notna().sum())} with a clear "
              f"September look")

    empty = pd.DataFrame(columns=["dataset", "field_id", "year", *FEATURE_COLUMNS])
    new = pd.concat(frames, ignore_index=True) if frames else empty
    features_path = OUT / "features.csv"
    merged = merge_previous(new, built + list(uncomputed), features_path)
    # A fixed row order makes a partial rebuild and a full rebuild write the same file.
    merged.sort_values(["dataset", "field_id", "year"]).to_csv(features_path, index=False)
    write_meta(built, uncomputed, OUT / "meta.json")
    print(f"wrote {features_path.relative_to(HERE.parents[2]).as_posix()} and meta.json")
    quebec_check(data, loaded)


def quebec_check(data: Path, loaded: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    """Write the three Quebec-only check files. They always pool every Quebec dataset that has series,
    so a partial rebuild (``--datasets qc_regions_2023``) never shrinks the published comparison."""
    quebec = {}
    for name in sorted(QUEBEC_DATASETS):
        features, series = loaded.get(name) or build_dataset(name, data)[:2]
        if features is not None:
            quebec[name] = (features, series)
    if not quebec:
        print("UNCOMPUTED Quebec rule check: no Quebec series")
        return
    features = pd.concat([f for f, _ in quebec.values()], ignore_index=True)
    cells = pd.concat([s[["field_id", "year", "cell"]].drop_duplicates(["field_id", "year"]).assign(dataset=name)
                       for name, (_, s) in quebec.items()], ignore_index=True)
    clear_dates = pd.concat([s.loc[(s["valid_frac"] >= MIN_VALID) & s["ndmi"].notna(), ["cell", "date"]]
                             .drop_duplicates().assign(dataset=name) for name, (_, s) in quebec.items()],
                            ignore_index=True)
    table = quebec_table(features, cells, data)
    evaluation, summary = evaluate_quebec(table, clear_dates)
    evaluation = evaluation.merge(cell_latitudes(data, cells), on=["dataset", "cell"], how="left")
    evaluation.to_csv(OUT / "rule_eval_quebec.csv", index=False)
    summary.to_csv(OUT / "class_summary_quebec.csv", index=False)
    calendar_check(table, {name: s for name, (_, s) in quebec.items()}).to_csv(
        OUT / "calendar_check_quebec.csv", index=False)
    headline = evaluation[(evaluation["cell"] == "all") & (evaluation["rule"] == RULE_COLUMN)]
    columns = ["dataset", "n_covered", "coverage", "TP", "FP", "FN", "TN", "silage_precision", "silage_recall",
               "balanced_accuracy"]
    print("Published rule on Quebec labels (no fitting, threshold 0.15 as published):")
    print(headline[columns].to_string(index=False))


if __name__ == "__main__":
    main()
