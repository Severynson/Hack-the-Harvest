"""Which 2026 candidate fields are corn, from Sentinel-2 alone, and what that mask error costs the satellite share.

Why this exists: the satellite silage share (``kernelag.state_signal``) is computed on the fields that
grew corn that year according to the Cropland Data Layer (CDL). The CDL is published after the season,
so a real-time Nov 15 forecast for 2026 has no corn mask. 2026 corn must be identified from imagery,
and every misidentified field changes the share. This module measures that change on 2025, where the
CDL truth is known, and then makes the 2026 calls.

Candidates: every sampled field that was corn in any year 2019-2025 (``data/samples/corn26_<fips>``).
    2025: positives = ``corn_<fips>`` rows with year 2025, negatives = ``noncorn25_<fips>`` (same fields).
    2026: ``corn26_<fips>``; corn status unknown (no 2026 CDL yet).

Features per field-year (``corn_features``), from clear looks (valid_frac >= 0.5) cut at the forecast
date with ``kernelag.state_signal.series_asof``, season May 1 onward:
    ndvi_m05..ndvi_m11, ndmi_m05..ndmi_m11   monthly medians (only months starting by the cut: features_for)
    peak_ndvi, peak_doy                      highest clear-look NDVI and its day of year
    amplitude                                highest minus lowest monthly NDVI median
    ndvi_b00..ndvi_b13                       NDVI medians in 16-day bins from day 121 (May 1), same rule
Calendar features are acceptable for the 2025 cross-validation (train and test share 2025's weather);
the 2026 calls apply a 2025 fit to 2026, so the cross-year recall check (2019-2024 corn fields scored by
the 2025 model) is reported to show how much that calendar transfer costs.

Model (declared before any result was seen, never tuned): sklearn HistGradientBoostingClassifier with
learning_rate 0.1, 200 iterations, 15 leaves, 50 rows per leaf, L2 1.0, no early stopping, fixed seed;
missing features handled natively; threshold 0.5 fixed in advance.

Validation on 2025: leave-one-AREA-out (group = state_fips + cell, 150 groups) and leave-one-STATE-out.

Mask-error replay on 2025 (``mask_replay``): the field silage model is fitted on ALL Quebec labels with
series (quebec_maize_2023 + qc_regions_2023, 3,128 field-years). The state share is then computed from
the 2025 sample with four corn masks:
    true_all    CDL 2025 corn fields (what kernelag.state_signal uses)
    pred_all    fields the leave-one-area-out classifier calls corn, among all 2025 candidates
    true_hist   CDL corn fields among fields that were corn in some year 2019-2024
    pred_hist   classifier corn among fields that were corn in some year 2019-2024: the faithful replay of
                the 2026 pipeline, whose candidate pool cannot contain fields that are corn for the first time
    det_all     CDL corn fields the classifier also calls corn (omission half of the error only)
The share arithmetic is ``kernelag.state_signal.area_totals`` re-implemented on precomputed features
(``area_totals_from_features``; identical code, checked equal in ``test_corn26.py``) followed by
``kernelag.state_signal.state_table`` unchanged. ``pred - true`` is the extra error a 2026 share carries.

Outputs (``out/``):
    classifier_cv_by_state.csv   precision, recall, accuracy, corn-acre ratio per state, asof and scheme
    cross_year_recall.csv        recall of the 2025 leave-one-area-out models on 2019-2024 CDL corn fields
    cv_predictions_2025.csv      field-level cross-validated corn probabilities for every 2025 candidate
    mask_error_2025.csv          per state and asof: shares under the four masks and their differences
    mask_error_summary.csv       mean and SD across states of the differences
    cross_year_omission_replay.csv  per state and year 2019-2025: share on detected CDL corn vs all CDL corn,
                                 the 2025 leave-one-area-out models applied to each year (calendar transfer)
    cross_year_omission_summary.csv mean and SD across states, per year and 2019-2024 pooled
    corn26_calls.csv             state_fips, cell, field_id, year, p_corn, is_corn, acres, n_clear
    corn26_sanity.csv            2026 predicted corn acres vs 2025 sample truth and NASS planted direction
    run_meta.json                settings, counts, timings

Field ids are read as TEXT (``read_series_file``): ``kernelag.field_model.load_series`` drops the leading
zero of California (06...) and Colorado (08...) ids, so with it those two states join no series at all.
Read the CSV outputs with ``dtype={"field_id": str, "state_fips": str, "cell": str}`` for the same reason.

Run from the repository root:
    .venv/Scripts/python.exe test_models/ownModels/satellite/corn26/corn26.py --workers 15
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernelag.features import build_features  # noqa: E402
from kernelag.field_model import DECISION_THRESHOLD as SILAGE_THRESHOLD  # noqa: E402
from kernelag.field_model import MODEL_FEATURES, evidence_table, load_series, make_model  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402
from kernelag.state_signal import complete_areas, series_asof, state_table  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

SCORE_YEAR = 2025
TARGET_YEAR = 2026
HISTORY_YEARS = tuple(range(2019, 2025))   # the years a 2025 candidate pool could know about in real time
ASOFS = ("nov", "oct", "sep")              # Nov 15 is the forecast; Oct 15 and Sep 15 show earliness
MIN_VALID = 0.5                            # clear look, the same floor as kernelag.features
MONTHS = tuple(range(5, 12))               # May..Nov
BIN_START_DOY, BIN_DAYS, N_BINS = 121, 16, 14
CORN_THRESHOLD = 0.5                       # fixed in advance; never tuned
SEED = 20261115
QUEBEC_SETS = ("quebec_maize_2023", "qc_regions_2023")
SAMPLE_COLUMNS = ["field_id", "year", "cell", "cell_size_acres", "state_fips", "county_fips", "acres"]
MASKS = ("true_all", "pred_all", "true_hist", "pred_hist")

CORN_FEATURES = ([f"ndvi_m{m:02d}" for m in MONTHS] + [f"ndmi_m{m:02d}" for m in MONTHS]
                 + ["peak_ndvi", "peak_doy", "amplitude"] + [f"ndvi_b{b:02d}" for b in range(N_BINS)])
CLASSIFIER_SETTINGS = dict(learning_rate=0.1, max_iter=200, max_leaf_nodes=15, min_samples_leaf=50,
                           l2_regularization=1.0, early_stopping=False, random_state=SEED)


# --------------------------------------------------------------------------------------------- data

def states() -> pd.DataFrame:
    """The sampled states: state, state_fips (two digits)."""
    summary = pd.read_csv(data_dir() / "samples" / "sample_summary.csv", dtype={"state_fips": str})
    summary["state_fips"] = summary["state_fips"].str.zfill(2)
    return summary[["state", "state_fips"]].reset_index(drop=True)


def read_sample(stem: str) -> pd.DataFrame:
    """One sample file without its geometry, with text ids."""
    table = pd.read_parquet(data_dir() / "samples" / f"{stem}.parquet", columns=SAMPLE_COLUMNS)
    for column in ["field_id", "cell", "state_fips", "county_fips"]:
        table[column] = table[column].astype(str)
    table["state_fips"] = table["state_fips"].str.zfill(2)
    return table.reset_index(drop=True)


def read_series_file(path: Path) -> pd.DataFrame:
    """``kernelag.field_model.load_series`` for one file, but reading field ids as TEXT.

    ``load_series`` parses ids as integers before casting them to text, which drops the leading zero of
    California (06...) and Colorado (08...) field ids, so none of their series join to the sample.
    """
    series = pd.read_csv(path, parse_dates=["date"], dtype={"field_id": str, "OBJECTID": str})
    series = series.rename(columns={"OBJECTID": "field_id"})
    series["date"] = series["date"].dt.normalize()
    return series.drop_duplicates(["field_id", "year", "date"])


def read_series(folder: Path, years) -> pd.DataFrame:
    """Per-field, per-date series of the given years from a folder of ``<cell>_<year>.csv`` files."""
    years = {int(y) for y in years}
    files = [f for f in sorted(folder.glob("*.csv")) if int(f.stem.rsplit("_", 1)[1]) in years]
    if not files:
        return pd.DataFrame(columns=["field_id", "date", "year", "valid_frac", "ndvi", "ndmi", "ndti"])
    return pd.concat([read_series_file(f) for f in files], ignore_index=True)


def candidates_2025(fips: str) -> pd.DataFrame:
    """Every 2025 candidate field with its CDL label (is_corn) and whether it was corn in 2019-2024.

    Restricted to areas whose series are complete (``kernelag.state_signal.complete_areas``) in both the
    corn and the non-corn folders, so the replay uses the same areas the satellite share would.
    """
    data = data_dir()
    corn = read_sample(f"corn_{fips}")
    negatives = read_sample(f"noncorn25_{fips}")
    areas = set(complete_areas(corn, data / "s2_series" / f"corn_{fips}"))
    if len(negatives):
        areas &= set(complete_areas(negatives, data / "s2_series" / f"noncorn25_{fips}"))
    table = pd.concat([corn[corn["year"] == SCORE_YEAR].assign(is_corn=1), negatives.assign(is_corn=0)],
                      ignore_index=True)
    if table.duplicated(["field_id", "year"]).any():
        raise ValueError(f"state {fips}: a field is both corn and non-corn in {SCORE_YEAR}")
    history = set(corn.loc[corn["year"].isin(HISTORY_YEARS), "field_id"])
    table["history_corn"] = table["field_id"].isin(history).astype(int)
    table = table[table["cell"].isin(areas)].reset_index(drop=True)
    table["group"] = table["state_fips"] + "_" + table["cell"]
    return table


def candidates_2026(fips: str) -> pd.DataFrame:
    """Every 2026 candidate field (corn in any year 2019-2025), corn status unknown."""
    table = read_sample(f"corn26_{fips}")
    folder = data_dir() / "s2_series" / f"corn26_{fips}"
    areas = set(complete_areas(table, folder))
    table = table[table["cell"].isin(areas)].reset_index(drop=True)
    table["group"] = table["state_fips"] + "_" + table["cell"]
    return table


# ----------------------------------------------------------------------------------------- features

def corn_features(series: pd.DataFrame, asof: str = "nov") -> pd.DataFrame:
    """One row per field_id and year: the corn classifier features (module text), cut at ``asof``."""
    keys = ["field_id", "year"]
    empty = pd.DataFrame(columns=keys + CORN_FEATURES + ["n_clear"])
    if series.empty:
        return empty
    s = series_asof(series, asof)
    s = s[(s["valid_frac"] >= MIN_VALID) & s["ndvi"].notna() & (s["date"].dt.month >= MONTHS[0])]
    if s.empty:
        return empty
    doy = s["date"].dt.day_of_year.astype(int)
    s = s.assign(doy=doy, month=s["date"].dt.month.astype(int),
                 bin=((doy - BIN_START_DOY) // BIN_DAYS).clip(0, N_BINS - 1))
    frame = s.groupby(keys).size().rename("n_clear").to_frame()

    def medians(value: str, period: str, labels: list[int], prefix: str) -> pd.DataFrame:
        wide = s.groupby(keys + [period])[value].median().unstack(period).reindex(columns=labels)
        wide.columns = [f"{prefix}{label:02d}" for label in labels]
        return wide

    ndvi_month = medians("ndvi", "month", list(MONTHS), "ndvi_m")
    peak_rows = s.loc[s.groupby(keys)["ndvi"].idxmax().to_numpy(), keys + ["ndvi", "doy"]]
    peak = peak_rows.set_index(keys).rename(columns={"ndvi": "peak_ndvi", "doy": "peak_doy"})
    frame = frame.join([ndvi_month, medians("ndmi", "month", list(MONTHS), "ndmi_m"), peak,
                        medians("ndvi", "bin", list(range(N_BINS)), "ndvi_b")])
    frame["amplitude"] = ndvi_month.max(axis=1) - ndvi_month.min(axis=1)
    return frame.reset_index()[keys + CORN_FEATURES + ["n_clear"]]


def with_corn_features(candidates: pd.DataFrame, series: pd.DataFrame, asof: str) -> pd.DataFrame:
    """Candidates joined to their features; a field with no clear look keeps missing features."""
    features = corn_features(series, asof)
    features["year"] = features["year"].astype(int)
    table = candidates.merge(features, on=["field_id", "year"], how="left", validate="one_to_one")
    table["n_clear"] = table["n_clear"].fillna(0).astype(int)
    return table


def field_evidence(series: pd.DataFrame, asof: str) -> pd.DataFrame:
    """Harvest evidence for the silage model (``kernelag.features.build_features``), cut at ``asof``."""
    keep = ["field_id", "year"] + MODEL_FEATURES + ["peak_doy", "cut_doy"]
    if series.empty:
        return pd.DataFrame(columns=keep)
    features = build_features(series_asof(series, asof))
    for column in keep:
        if column not in features:
            features[column] = np.nan
    features["year"] = features["year"].astype(int)
    return features[keep]


def state_inputs(fips: str, asofs=ASOFS, cross_year: bool = True, field_model_inputs: bool = True) -> dict:
    """Everything one state contributes: 2025 candidates with features per asof, 2019-2024 corn fields
    (for the cross-year check), 2026 candidates, and 2025 harvest evidence per asof. Runs in a worker."""
    data = data_dir()
    candidates = candidates_2025(fips)
    series = pd.concat([read_series(data / "s2_series" / f"corn_{fips}", [SCORE_YEAR]),
                        read_series(data / "s2_series" / f"noncorn25_{fips}", [SCORE_YEAR])], ignore_index=True)
    series = series[series["field_id"].isin(set(candidates["field_id"]))]
    out = {"fips": fips, "last_date_2025": str(series["date"].max().date()) if len(series) else None,
           "corn": {asof: with_corn_features(candidates, series, asof) for asof in asofs}}
    if field_model_inputs:
        out["evidence"] = {asof: field_evidence(series, asof) for asof in asofs}
    if cross_year:
        corn = read_sample(f"corn_{fips}")
        positives = corn[corn["year"].isin(HISTORY_YEARS) & corn["cell"].isin(set(candidates["cell"]))]
        positives = positives.assign(is_corn=1, group=positives["state_fips"] + "_" + positives["cell"])
        past = read_series(data / "s2_series" / f"corn_{fips}", HISTORY_YEARS)
        out["past"] = with_corn_features(positives.reset_index(drop=True), past, "nov")
        if field_model_inputs:
            out["past_evidence"] = field_evidence(past, "nov")
    target = candidates_2026(fips)
    series26 = read_series(data / "s2_series" / f"corn26_{fips}", [TARGET_YEAR])
    out["last_date_2026"] = str(series26["date"].max().date()) if len(series26) else None
    out["target"] = with_corn_features(target, series26, "nov")
    return out


# ----------------------------------------------------------------------------------------- classifier

def make_classifier():
    """The one pre-declared corn classifier (module text)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(**CLASSIFIER_SETTINGS)


def features_for(asof: str) -> list[str]:
    """The declared features that can exist at the cut: months and 16-day bins starting on or before it."""
    from kernelag.context import ASOF_MONTH

    month = ASOF_MONTH[asof]
    cut_doy = pd.Timestamp(SCORE_YEAR, month, 15).day_of_year
    last_bin = min(N_BINS - 1, (cut_doy - BIN_START_DOY) // BIN_DAYS)
    keep = {f"ndvi_m{m:02d}" for m in MONTHS if m <= month} | {f"ndmi_m{m:02d}" for m in MONTHS if m <= month}
    keep |= {"peak_ndvi", "peak_doy", "amplitude"} | {f"ndvi_b{b:02d}" for b in range(last_bin + 1)}
    return [c for c in CORN_FEATURES if c in keep]


def fit_classifier(table: pd.DataFrame, features: list[str] | None = None):
    """The classifier fitted on ``table``; remembers its feature list in ``features_``.

    A feature with no observed value in the fitting rows is left out (it carries no information and the
    binning cannot handle it); this never happens for ``features_for(asof)`` on the full sample.
    """
    features = [c for c in (features or features_for("nov")) if table[c].notna().any()]
    model = make_classifier().fit(table[features].to_numpy(float), table["is_corn"].to_numpy(int))
    model.features_ = features
    return model


def p_corn(model, table: pd.DataFrame) -> np.ndarray:
    if table.empty:
        return np.array([], float)
    return model.predict_proba(table[model.features_].to_numpy(float))[:, 1]


def grouped_cv(table: pd.DataFrame, group_column: str, features: list[str], extra: pd.DataFrame | None = None
               ) -> tuple[np.ndarray, np.ndarray | None]:
    """Leave-one-group-out P(corn) for every row of ``table``; each row's model never saw its group.

    ``extra`` rows (same group column) are scored by the model that left their group out, too.
    """
    groups = table[group_column].to_numpy()
    probability = np.full(len(table), np.nan)
    extra_probability = np.full(len(extra), np.nan) if extra is not None else None
    for group in sorted(set(groups)):
        held_out = groups == group
        model = fit_classifier(table[~held_out], features)
        probability[held_out] = p_corn(model, table[held_out])
        if extra is not None:
            rows = (extra[group_column] == group).to_numpy()
            if rows.any():
                extra_probability[rows] = p_corn(model, extra[rows])
    return probability, extra_probability


def call_metrics(frame: pd.DataFrame, probability: str) -> dict:
    """Counts, precision/recall/accuracy for corn, and acre ratios (raw and weighted by 1/cell size)."""
    call = (frame[probability] >= CORN_THRESHOLD).to_numpy()
    truth = (frame["is_corn"] == 1).to_numpy()
    acres = frame["acres"].to_numpy(float)
    weighted = acres / frame["cell_size_acres"].to_numpy(float)
    tp, fp = int((call & truth).sum()), int((call & ~truth).sum())
    fn, tn = int((~call & truth).sum()), int((~call & ~truth).sum())

    def ratio(top: float, bottom: float) -> float:
        return round(float(top / bottom), 4) if bottom else float("nan")

    recall, specificity = ratio(tp, tp + fn), ratio(tn, tn + fp)
    return {
        "n": len(frame), "n_corn": tp + fn, "n_no_clear_look": int((frame["n_clear"] == 0).sum()),
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": ratio(tp, tp + fp), "recall": recall, "accuracy": ratio(tp + tn, len(frame)),
        "balanced_accuracy": round((recall + specificity) / 2, 4),
        "acre_precision": ratio(acres[call & truth].sum(), acres[call].sum()),
        "acre_recall": ratio(acres[call & truth].sum(), acres[truth].sum()),
        "corn_acre_ratio_raw": ratio(acres[call].sum(), acres[truth].sum()),
        "corn_acre_ratio": ratio(weighted[call].sum(), weighted[truth].sum()),
    }


# --------------------------------------------------------------------------------------- field model

def fit_field_model_all_quebec() -> tuple[object, pd.DataFrame]:
    """``kernelag.field_model.make_model`` fitted on every assessable field-year of both Quebec label sets.

    Same as the feature-test harness's E3b (``maryland_transfer_allqc``): each set's evidence table
    (labels inner-joined to its series), concatenated; fitted on the assessable rows.
    """
    import geopandas as gpd

    data = data_dir()
    tables = []
    for name in QUEBEC_SETS:
        labels = gpd.read_parquet(data / "labels" / f"{name}.parquet")
        tables.append(evidence_table(labels, load_series(data / "s2_series" / name)).assign(dataset=name))
    train = pd.concat(tables, ignore_index=True)
    fit = train[train["assessable"]]
    return make_model().fit(fit[MODEL_FEATURES], fit["is_silage"]), train


def silage_probability(model, evidence: pd.DataFrame) -> pd.DataFrame:
    """P(silage) per field-year from harvest evidence; NaN where no drop was found (not assessable)."""
    table = evidence.copy()
    table["assessable"] = table["max_drop"].notna()
    table["p_silage"] = np.nan
    ok = table["assessable"].to_numpy()
    if ok.any():
        table.loc[ok, "p_silage"] = model.predict_proba(table.loc[ok, MODEL_FEATURES])[:, 1]
    return table


def area_totals_from_features(sample: pd.DataFrame, features: pd.DataFrame, model) -> pd.DataFrame:
    """``kernelag.state_signal.area_totals`` with the evidence already built (same arithmetic, line by line).

    ``features`` is ``build_features`` output (or ``field_evidence``) for the sample's field-years.
    """
    if sample.duplicated(["field_id", "year"]).any():
        raise ValueError("duplicate field-year in satellite sample")
    features = features.copy()
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
    fields["called_silage_acres"] = fields["corn_acres"] * (fields["p_silage"] >= SILAGE_THRESHOLD)
    grouped = fields.groupby(["cell", "year"])
    totals = grouped.agg(
        cell_size_acres=("cell_size_acres", "first"), fields=("field_id", "size"),
        sampled_acres=("acres", "sum"), corn_acres=("corn_acres", "sum"),
        silage_like_acres=("silage_like_acres", "sum"), called_silage_acres=("called_silage_acres", "sum"),
        median_peak_doy=("peak_doy", "median"), median_cut_doy=("cut_doy", "median"),
    )
    return totals.reset_index()


def mask_share(sample: pd.DataFrame, evidence: pd.DataFrame, model) -> dict:
    """The state's satellite share row (``kernelag.state_signal.state_table``) for one set of corn fields."""
    keep = ["field_id", "year", "cell", "cell_size_acres", "acres"]
    table = state_table(area_totals_from_features(sample[keep], evidence, model))
    if table.empty:
        return {"areas": 0, "fields": 0, "sat_share": np.nan, "sat_share_calls": np.nan, "share_se": np.nan,
                "assessable_share": np.nan}
    row = table.iloc[0]
    return {key: row[key] for key in ["areas", "fields", "sat_share", "sat_share_calls", "share_se",
                                      "assessable_share"]}


def logit(p):
    p = np.asarray(p, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(p / (1 - p))


def mask_replay(candidates: pd.DataFrame, evidence: pd.DataFrame, model, probability: str = "p_loao") -> dict:
    """One state's 2025 shares under the four masks (module text), plus diagnostics of the miscalls."""
    call = candidates[probability] >= CORN_THRESHOLD
    truth = candidates["is_corn"] == 1
    hist = candidates["history_corn"] == 1
    masks = {"true_all": truth, "pred_all": call, "true_hist": truth & hist, "pred_hist": call & hist,
             "det_all": truth & call}
    row: dict = {}
    for name, mask in masks.items():
        result = mask_share(candidates[mask.to_numpy()], evidence, model)
        row[f"fields_{name}"] = int(mask.sum())
        row[f"acres_{name}"] = round(float(candidates.loc[mask, "acres"].sum()), 1)
        for key in ["sat_share", "sat_share_calls", "share_se", "assessable_share"]:
            row[f"{key}_{name}"] = result[key]
    # What the classifier's mistakes look like to the silage model (acre-weighted mean P(silage)).
    scored = candidates.merge(silage_probability(model, evidence)[["field_id", "year", "p_silage"]],
                              on=["field_id", "year"], how="left")
    for name, mask in {"tp": call & truth, "fp": call & ~truth, "fn": ~call & truth}.items():
        part = scored[mask.to_numpy() & scored["p_silage"].notna().to_numpy()]
        row[f"p_silage_{name}"] = (round(float(np.average(part["p_silage"], weights=part["acres"])), 4)
                                   if len(part) else np.nan)
        row[f"acres_{name}"] = round(float(candidates.loc[mask, "acres"].sum()), 1)
    for variant, base in [("pred_all", "true_all"), ("pred_hist", "true_all"), ("true_hist", "true_all"),
                          ("pred_hist", "true_hist"), ("det_all", "true_all")]:
        for key, short in [("sat_share", "share"), ("sat_share_calls", "calls")]:
            a, b = row[f"{key}_{base}"], row[f"{key}_{variant}"]
            label = f"{variant}_minus_{base}"
            row[f"{short}_diff_{label}"] = round(float(b - a), 4)
            if short == "share":
                row[f"logit_diff_{label}"] = round(float(logit(b) - logit(a)), 4)
                row[f"ratio_{label}"] = round(float(b / a), 4) if a else np.nan
    return row


def omission_replay(positives: pd.DataFrame, evidence: pd.DataFrame, model, probability: str = "p_loao") -> dict:
    """Share on the CDL corn fields the classifier detects vs on all CDL corn fields (one state, one year).

    Only the omission half of the mask error: years before 2025 have no non-corn series, so false
    positives cannot be replayed there. For 2025 it equals ``det_all`` minus ``true_all`` in ``mask_replay``.
    """
    detected = (positives[probability] >= CORN_THRESHOLD).to_numpy()
    true_share = mask_share(positives, evidence, model)
    det_share = mask_share(positives[detected], evidence, model)
    a, b = true_share["sat_share"], det_share["sat_share"]
    return {"corn_fields": len(positives), "detected_fields": int(detected.sum()),
            "acre_recall": round(float(positives.loc[detected, "acres"].sum() / positives["acres"].sum()), 4),
            "sat_share_true": a, "sat_share_detected": b, "share_se_true": true_share["share_se"],
            "share_diff_det_minus_true": round(float(b - a), 4),
            "logit_diff_det_minus_true": round(float(logit(b) - logit(a)), 4),
            "ratio_det_to_true": round(float(b / a), 4) if a else np.nan}


# ------------------------------------------------------------------------------------------ outputs

def nass_planted() -> pd.DataFrame:
    """NASS planted acres used only as a direction check: 2025 final and 2026 September."""
    nass = pd.read_csv(data_dir() / "nass" / "corn_acres_state.csv", dtype={"state_ansi": str})
    nass["state_fips"] = nass["state_ansi"].str.zfill(2)
    planted = nass[nass["series"] == "planted"]
    last = planted[(planted["year"] == SCORE_YEAR) & (planted["period"] == "final")]
    now = planted[(planted["year"] == TARGET_YEAR) & (planted["period"] == "sep")]
    return (last.set_index("state_fips")["acres"].rename("nass_planted_2025_final").to_frame()
            .join(now.set_index("state_fips")["acres"].rename("nass_planted_2026_sep"), how="outer"))


def summarize_differences(table: pd.DataFrame) -> pd.DataFrame:
    """Mean, SD, mean absolute value and range across states of every difference column, per asof."""
    columns = [c for c in table.columns if c.startswith(("share_diff_", "calls_diff_", "logit_diff_", "ratio_"))]
    rows = []
    for asof, part in table.groupby("asof", sort=False):
        for column in columns:
            values = part[column].astype(float).dropna()
            centred = values - 1 if column.startswith("ratio_") else values
            rows.append({"asof": asof, "quantity": column, "states": len(values),
                         "mean": round(float(values.mean()), 4), "sd": round(float(values.std(ddof=1)), 4),
                         "mean_abs": round(float(centred.abs().mean()), 4),
                         "min": round(float(values.min()), 4), "max": round(float(values.max()), 4)})
    return pd.DataFrame(rows)


def summarize_omission(table: pd.DataFrame) -> pd.DataFrame:
    """Across states, per year and for 2019-2024 pooled: mean/SD of the omission-only share error."""
    rows = []
    parts = [(str(y), p) for y, p in table.groupby("year")]
    parts.append(("2019-2024 pooled", table[table["cross_year"] == 1]))
    for label, part in parts:
        row = {"year": label, "state_years": len(part),
               "acre_recall_mean": round(float(part["acre_recall"].mean()), 4)}
        for column in ["share_diff_det_minus_true", "logit_diff_det_minus_true", "ratio_det_to_true"]:
            values = part[column].astype(float).dropna()
            centred = values - 1 if column.startswith("ratio_") else values
            row.update({f"{column}_mean": round(float(values.mean()), 4),
                        f"{column}_sd": round(float(values.std(ddof=1)), 4),
                        f"{column}_mean_abs": round(float(centred.abs().mean()), 4)})
        rows.append(row)
    return pd.DataFrame(rows)


def write_csv(frame: pd.DataFrame, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--asof", nargs="+", default=list(ASOFS), choices=list(ASOFS))
    parser.add_argument("--states", nargs="*", default=None, help="state fips subset (default: all sampled)")
    args = parser.parse_args()
    started = time.time()
    asofs = [a for a in ASOFS if a in args.asof]
    if "nov" not in asofs:
        parser.error("nov (the forecast date) is required")
    roster = states()
    if args.states:
        roster = roster[roster["state_fips"].isin([s.zfill(2) for s in args.states])].reset_index(drop=True)
    names = dict(zip(roster["state_fips"], roster["state"]))

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        inputs = list(pool.map(state_inputs, roster["state_fips"], [asofs] * len(roster)))
    print(f"inputs loaded in {time.time() - started:.0f}s", flush=True)

    field_model, quebec = fit_field_model_all_quebec()
    print(f"field model: {len(quebec)} Quebec field-years with series, {int(quebec['assessable'].sum())} "
          f"assessable used to fit; by set {quebec.groupby('dataset').size().to_dict()}", flush=True)

    metric_rows, replay_rows, prediction_parts, cross_year_rows, omission_rows = [], [], [], [], []
    tables: dict[str, pd.DataFrame] = {}
    for asof in asofs:
        table = pd.concat([part["corn"][asof] for part in inputs], ignore_index=True)
        past = pd.concat([part["past"] for part in inputs], ignore_index=True) if asof == "nov" else None
        table["p_loao"], past_p = grouped_cv(table, "group", features_for(asof), extra=past)
        table["p_loso"], _ = grouped_cv(table, "state_fips", features_for(asof))
        tables[asof] = table
        print(f"{asof}: cross-validated {len(table)} candidates in {time.time() - started:.0f}s", flush=True)

        for scheme, column in [("leave_one_area_out", "p_loao"), ("leave_one_state_out", "p_loso")]:
            for fips, part in [("ALL", table)] + list(table.groupby("state_fips")):
                metric_rows.append({"asof": asof, "scheme": scheme, "state_fips": fips,
                                    "state": names.get(fips, "ALL 15 STATES"), **call_metrics(part, column)})
        prediction_parts.append(table[["state_fips", "cell", "field_id", "year", "acres", "cell_size_acres",
                                       "is_corn", "history_corn", "n_clear", "p_loao", "p_loso"]]
                                .assign(asof=asof))
        if past is not None:
            past["p_loao"] = past_p
            call = past["p_loao"] >= CORN_THRESHOLD
            past["called_acres"] = past["acres"] * call
            for (fips, year), part in [(("ALL", y), p) for y, p in past.groupby("year")] + list(
                    past.groupby(["state_fips", "year"])):
                cross_year_rows.append({
                    "state_fips": fips, "state": names.get(fips, "ALL 15 STATES"), "year": int(year),
                    "corn_fields": len(part), "no_clear_look": int((part["n_clear"] == 0).sum()),
                    "recall": round(float((part["p_loao"] >= CORN_THRESHOLD).mean()), 4),
                    "acre_recall": round(float(part["called_acres"].sum() / part["acres"].sum()), 4)})
            for fips, part in [("ALL", table)] + list(table.groupby("state_fips")):
                positives = part[part["is_corn"] == 1]
                cross_year_rows.append({
                    "state_fips": fips, "state": names.get(fips, "ALL 15 STATES"), "year": SCORE_YEAR,
                    "corn_fields": len(positives), "no_clear_look": int((positives["n_clear"] == 0).sum()),
                    "recall": round(float((positives["p_loao"] >= CORN_THRESHOLD).mean()), 4),
                    "acre_recall": round(float((positives["acres"] * (positives["p_loao"] >= CORN_THRESHOLD)).sum()
                                               / positives["acres"].sum()), 4)})
            # Omission-only share replay, every year: the 2025 model applied to other years' corn fields.
            for part in inputs:
                fips = part["fips"]
                years = [(y, past[(past["state_fips"] == fips) & (past["year"] == y)], part["past_evidence"])
                         for y in HISTORY_YEARS]
                years.append((SCORE_YEAR, table[(table["state_fips"] == fips) & (table["is_corn"] == 1)],
                              part["evidence"]["nov"]))
                for year, positives, evidence in years:
                    if positives.empty:
                        continue
                    omission_rows.append({"state": names[fips], "state_fips": fips, "year": int(year),
                                          "cross_year": int(year != SCORE_YEAR),
                                          **omission_replay(positives.reset_index(drop=True), evidence,
                                                            field_model)})

        for part in inputs:
            fips = part["fips"]
            candidates = table[table["state_fips"] == fips].reset_index(drop=True)
            row = mask_replay(candidates, part["evidence"][asof], field_model, "p_loao")
            replay_rows.append({"state": names[fips], "state_fips": fips, "asof": asof, **row})
        print(f"{asof}: mask replay done in {time.time() - started:.0f}s", flush=True)

    metrics = pd.DataFrame(metric_rows)
    write_csv(metrics, "classifier_cv_by_state.csv")
    write_csv(pd.DataFrame(cross_year_rows).sort_values(["state_fips", "year"]), "cross_year_recall.csv")
    predictions = pd.concat(prediction_parts, ignore_index=True)
    predictions[["p_loao", "p_loso"]] = predictions[["p_loao", "p_loso"]].round(4)
    write_csv(predictions, "cv_predictions_2025.csv")
    replay = pd.DataFrame(replay_rows)
    write_csv(replay, "mask_error_2025.csv")
    write_csv(summarize_differences(replay), "mask_error_summary.csv")
    omission = pd.DataFrame(omission_rows)
    write_csv(omission, "cross_year_omission_replay.csv")
    write_csv(summarize_omission(omission), "cross_year_omission_summary.csv")

    # 2026 calls from the classifier fitted on every 2025 candidate (Nov 15 features).
    train = tables["nov"]
    final = fit_classifier(train, features_for("nov"))
    target = pd.concat([part["target"] for part in inputs], ignore_index=True)
    target["p_corn"] = p_corn(final, target).round(4)
    target["is_corn"] = (target["p_corn"] >= CORN_THRESHOLD).astype(int)
    target["year"] = TARGET_YEAR
    calls = target[["state_fips", "cell", "field_id", "year", "p_corn", "is_corn", "acres", "n_clear"]]
    write_csv(calls, "corn26_calls.csv")

    train = train.assign(p_fit=p_corn(final, train))
    weight = 1.0 / train["cell_size_acres"]
    target_weight = 1.0 / target["cell_size_acres"]
    sanity = pd.DataFrame({
        "true_corn_acres_2025": (train["acres"] * train["is_corn"]).groupby(train["state_fips"]).sum(),
        "cv_pred_corn_acres_2025": (train["acres"] * (train["p_loao"] >= CORN_THRESHOLD)).groupby(
            train["state_fips"]).sum(),
        "fit_pred_corn_acres_2025": (train["acres"] * (train["p_fit"] >= CORN_THRESHOLD)).groupby(
            train["state_fips"]).sum(),
        "pred_corn_acres_2026": (target["acres"] * target["is_corn"]).groupby(target["state_fips"]).sum(),
        "weighted_true_2025": (train["acres"] * train["is_corn"] * weight).groupby(train["state_fips"]).sum(),
        "weighted_cv_pred_2025": (train["acres"] * (train["p_loao"] >= CORN_THRESHOLD) * weight).groupby(
            train["state_fips"]).sum(),
        "weighted_pred_2026": (target["acres"] * target["is_corn"] * target_weight).groupby(
            target["state_fips"]).sum(),
        "candidates_2025": train.groupby("state_fips").size(),
        "candidates_2026": target.groupby("state_fips").size(),
        "no_clear_look_2026": (target["n_clear"] == 0).groupby(target["state_fips"]).sum(),
    })
    sanity["ratio_pred26_to_true25"] = sanity["weighted_pred_2026"] / sanity["weighted_true_2025"]
    sanity["ratio_pred26_to_cvpred25"] = sanity["weighted_pred_2026"] / sanity["weighted_cv_pred_2025"]
    sanity = sanity.join(nass_planted(), how="left")
    sanity["nass_ratio_2026_to_2025"] = sanity["nass_planted_2026_sep"] / sanity["nass_planted_2025_final"]
    sanity["direction_agrees_cvpred"] = (np.sign(sanity["ratio_pred26_to_cvpred25"] - 1)
                                         == np.sign(sanity["nass_ratio_2026_to_2025"] - 1))
    sanity["last_observation_2026"] = sanity.index.map({p["fips"]: p["last_date_2026"] for p in inputs})
    sanity.insert(0, "state", sanity.index.map(names))
    sanity = sanity.reset_index(names="state_fips").round(4)
    write_csv(sanity, "corn26_sanity.csv")

    meta = {
        "generated_by": "test_models/ownModels/satellite/corn26/corn26.py",
        "asofs": asofs, "states": roster["state_fips"].tolist(),
        "classifier": "sklearn HistGradientBoostingClassifier", "classifier_settings": CLASSIFIER_SETTINGS,
        "corn_threshold": CORN_THRESHOLD, "corn_features": CORN_FEATURES, "min_valid": MIN_VALID,
        "field_model": "kernelag.field_model.make_model on quebec_maize_2023 + qc_regions_2023",
        "field_model_rows": int(len(quebec)), "field_model_fit_rows": int(quebec["assessable"].sum()),
        "candidates_2025": int(len(tables["nov"])), "corn_2025": int(tables["nov"]["is_corn"].sum()),
        "candidates_2026": int(len(target)),
        "last_observation_2025": {p["fips"]: p["last_date_2025"] for p in inputs},
        "last_observation_2026": {p["fips"]: p["last_date_2026"] for p in inputs},
        "seconds": round(time.time() - started),
    }
    (OUT / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(metrics[metrics["state_fips"] == "ALL"].to_string(index=False))
    print(summarize_differences(replay).to_string(index=False))
    print(f"done in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
