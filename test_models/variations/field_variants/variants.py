"""Field classifier variants, selected on Quebec held-out seasons only; Maryland reported once afterwards.

The protocol is pre-registered in README.md (between the PREREGISTRATION markers) and hashed into
out/preregistration.sha256 before anything was scored. ``score`` and ``final`` refuse to run if the block
has changed since.

Commands (from the repository root):
    .venv/Scripts/python.exe -I test_models/variations/field_variants/variants.py build   # features cache
    .venv/Scripts/python.exe -I test_models/variations/field_variants/variants.py score   # selection years only
    .venv/Scripts/python.exe -I test_models/variations/field_variants/variants.py final   # 2025 + Maryland

``score`` reads only the selection years (2019-2024, 2026) and writes out/decision.json. ``final`` refuses to
run before decision.json exists; it scores the 2025 holdout for every candidate and Maryland for f0 and the
adopted candidate, plus response time. No per-field Maryland call is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))   # plain script, also under python -I, from the repo root

from kernelag.evaluate import bootstrap_intervals, cut_off, evaluation_table  # noqa: E402
from kernelag.field_model import MODEL_FEATURES, evidence_table, load_series, make_model  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402

OUT = HERE / "out"
README = HERE / "README.md"
BEGIN, END = "<!-- PREREGISTRATION:BEGIN -->", "<!-- PREREGISTRATION:END -->"
DEFAULT_CACHE = Path("C:/Users/danie/AppData/Local/Temp/claude/dfe35210c43945cb/"
                     "9bd8cc88-21cc-4423-8ecd-0115ef62e1a4/scratchpad/agents/field_variants/cache")
CACHE = Path(os.environ.get("FIELD_VARIANTS_CACHE", DEFAULT_CACHE))
CACHE_VERSION = "v1"

ALL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
SEL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2026]   # every decision is made on these
HOLDOUT = 2025                                            # never selected or tuned on
REF_YEAR = 2023                                           # f0_2023's training year
EXPANDING_YEARS = [2020, 2021, 2022, 2023, 2024, 2026]
ASOF = ["09-15", "10-15", "11-15"]
THRESHOLD = 0.5
LSWI = ["lswi_sep_median", "lswi_sep_min"]
MIN_VALID = 0.5
DRAWS, SEED, INTERVAL = 2000, 0, (0.05, 0.95)
N_TESTS = 6                                               # f1, f2, f3, f4, f6, f7 (Bonferroni reading)
BONF = (0.10 / N_TESTS / 2, 1 - 0.10 / N_TESTS / 2)
COVERAGE_MIN = 0.85
LO_GRID = np.round(np.arange(0.30, 0.5001, 0.02), 2)
HI_GRID = np.round(np.arange(0.50, 0.8001, 0.02), 2)
TIMING_PASSES = 5

XGB_PARAMETERS = {   # test_models/codexFieldBaseline/baseline.py, unchanged
    "n_estimators": 80, "max_depth": 2, "min_child_weight": 8, "learning_rate": 0.05, "subsample": 1.0,
    "colsample_bytree": 1.0, "reg_lambda": 5.0, "objective": "binary:logistic", "eval_metric": "logloss",
    "tree_method": "hist", "n_jobs": 4, "random_state": 42,
}
# Agronomy: silage is chopped green and the whole plant is removed (big fast drop, short fade, green and
# moist at the cut, little residue, dry bare soil in September); grain dries down and leaves stover.
MONOTONE = {"max_drop": 1, "max_drop_rate": 1, "fade_days": -1, "green_at_cut": 1, "ndmi_before_cut": 1,
            "ndti_post": -1, "lswi_sep_median": -1, "lswi_sep_min": -1}

FMY = REPO / "test_models" / "fieldMultiYear" / "out" / "loyo_by_year.csv"
R1_EXPECTED = {2019: 2566, 2020: 2325, 2021: 2598, 2022: 2839, 2023: 3128, 2024: 2938, 2026: 2806}
G1_EXPECTED = {"TP": 877, "FP": 345, "FN": 390, "TN": 1516}
G2_EXPECTED = {"TP": 10, "FP": 5, "FN": 2, "TN": 27}
G3_EXPECTED = {"TP": 10, "FP": 4, "FN": 2, "TN": 28}
KEEP = ["field_id", "parcel_id", "year", "cell", "label", "is_silage", "assessable", *MODEL_FEATURES, *LSWI]


@dataclass(frozen=True)
class Spec:
    name: str
    learner: str               # "logistic" or "xgb"
    lswi: bool = False
    adjust: str | None = None  # None, "year" or "yearcell"
    fixed_year: int | None = None

    @property
    def features(self) -> list[str]:
        return MODEL_FEATURES + (LSWI if self.lswi else [])


SPECS = {s.name: s for s in [
    Spec("f0_2023", "logistic", fixed_year=REF_YEAR),
    Spec("f0_all", "logistic"),
    Spec("f1_xgb_mono", "xgb"),
    Spec("f2_lswi", "logistic", lswi=True),
    Spec("f3_yearmed", "logistic", adjust="year"),
    Spec("f4_yearmed_lswi", "logistic", lswi=True, adjust="year"),
    Spec("f6_yearcellmed", "logistic", adjust="yearcell"),
    Spec("f7_xgb_yearmed_lswi", "xgb", lswi=True, adjust="year"),
]}
CANDIDATES = ["f1_xgb_mono", "f2_lswi", "f3_yearmed", "f4_yearmed_lswi", "f6_yearcellmed", "f7_xgb_yearmed_lswi"]
FOLD_SPECS = ["f0_all", *CANDIDATES]   # fitted on the fold's training years


# ------------------------------------------------------------------------------------- pre-registration


def prereg_block() -> str:
    lines = README.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    stripped = [line.strip() for line in lines]
    if stripped.count(BEGIN) != 1 or stripped.count(END) != 1:
        raise SystemExit("README must hold exactly one BEGIN and one END marker")
    begin, end = stripped.index(BEGIN), stripped.index(END)
    return "\n".join(lines[begin + 1:end]).strip("\n") + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_prereg() -> dict:
    target = OUT / "preregistration.sha256"
    if not target.exists():
        raise SystemExit("no out/preregistration.sha256: freeze the pre-registration before scoring")
    frozen = target.read_text(encoding="utf-8").split()[0]
    current = sha256_bytes(prereg_block().encode("utf-8"))
    if frozen != current:
        raise SystemExit(f"README pre-registration changed since it was frozen ({frozen} -> {current})")
    meta = json.loads((OUT / "preregistration.json").read_text(encoding="utf-8"))
    return {"sha256": frozen, "matches_readme": True, "frozen_utc": meta.get("frozen_utc"),
            "variants_py_sha256": sha256_bytes(Path(__file__).read_bytes())}


# ------------------------------------------------------------------------------------------------- data


def september_stats(series: pd.DataFrame) -> pd.DataFrame:
    """lswi_sep_median and lswi_sep_min per field-year (logic of featureTests/lswi_rule/build.py)."""
    clear = series[(series["valid_frac"] >= MIN_VALID) & series["ndmi"].notna() & (series["date"].dt.month == 9)]
    grouped = clear.assign(field_id=clear["field_id"].astype(str), year=clear["year"].astype(int)).groupby(
        ["field_id", "year"])["ndmi"]
    return pd.DataFrame({"lswi_sep_median": grouped.median(), "lswi_sep_min": grouped.min()}).reset_index()


def lswi_gate(series: pd.DataFrame) -> dict:
    """GL: this port against september_lswi from featureTests/lswi_rule/build.py on the same series."""
    import importlib.util

    path = REPO / "test_models" / "featureTests" / "lswi_rule" / "build.py"
    spec = importlib.util.spec_from_file_location("lswi_rule_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    theirs = module.september_lswi(series).set_index(["field_id", "year"])[LSWI]
    ours = september_stats(series).set_index(["field_id", "year"]).reindex(theirs.index)
    same_nan = bool((ours.isna().to_numpy() == theirs.isna().to_numpy()).all())
    diff = float(np.nanmax(np.abs(ours.to_numpy(float) - theirs.to_numpy(float))))
    return {"rows": len(theirs), "same_nan_pattern": same_nan, "max_abs_diff": diff,
            "reproduced": same_nan and diff < 1e-9}


def assemble(labels: pd.DataFrame, series: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    """Evidence + LSWI for ``series``, left-joined onto the fixed roster ``keys`` (same rows, same order)."""
    evidence = evidence_table(labels, series).drop(columns=["label", "is_silage", "assessable"])
    table = keys.merge(evidence, on=["field_id", "year"], how="left", validate="one_to_one")
    table = table.merge(september_stats(series), on=["field_id", "year"], how="left", validate="one_to_one")
    for column in MODEL_FEATURES + LSWI:
        if column not in table:
            table[column] = np.nan
    table["assessable"] = table["max_drop"].notna()
    return table


def build_year(year: int) -> tuple[pd.DataFrame, dict | None]:
    """All versions (full season and each as-of cut) of one qcm year, with the same rows in the same order."""
    import geopandas as gpd

    data = data_dir()
    labels = gpd.read_parquet(data / "labels" / f"qcm_{year}.parquet")
    series = load_series(data / "s2_series" / f"qcm_{year}")
    roster = evidence_table(labels, series)
    ids = labels["field_id"].astype(str).to_numpy()
    keys = roster[["field_id", "year", "label", "is_silage"]].copy()
    keys["cell"] = keys["field_id"].map(pd.Series(labels["cell"].astype(str).to_numpy(), index=ids))
    keys["parcel_id"] = keys["field_id"].map(pd.Series(labels["parcel_id"].astype(str).to_numpy(), index=ids))
    if keys["cell"].isna().any() or (keys["year"] != year).any():
        raise ValueError(f"qcm_{year}: rows without a cell or with another year")
    parts = []
    for asof in ["full", *ASOF]:
        part = assemble(labels, series if asof == "full" else cut_off(series, asof), keys)
        parts.append(part[KEEP].assign(asof=asof))
    gate = lswi_gate(series) if year == REF_YEAR else None
    return pd.concat(parts, ignore_index=True), gate


def input_digest(year: int) -> str:
    data = data_dir()
    digest = hashlib.sha256(CACHE_VERSION.encode())
    digest.update((data / "labels" / f"qcm_{year}.parquet").read_bytes())
    for path in sorted((data / "s2_series" / f"qcm_{year}").glob("*.csv")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def cached_year(year: int) -> tuple[pd.DataFrame, dict | None, str]:
    digest = input_digest(year)
    table_path, gate_path = CACHE / f"qcm_{year}_{digest}.parquet", CACHE / f"qcm_{year}_{digest}_gate.json"
    if table_path.exists():
        gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.exists() else None
        return pd.read_parquet(table_path), gate, digest
    table, gate = build_year(year)
    CACHE.mkdir(parents=True, exist_ok=True)
    table.to_parquet(table_path, index=False)
    if gate is not None:
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
    return table, gate, digest


def load_years(years: list[int], workers: int = 8) -> tuple[pd.DataFrame, dict | None, dict]:
    with ProcessPoolExecutor(max_workers=min(workers, len(years))) as pool:
        results = list(pool.map(cached_year, years))
    table = pd.concat([r[0] for r in results], ignore_index=True)
    table["field_id"] = table["field_id"].astype(str)
    gate = next((r[1] for r in results if r[1] is not None), None)
    return table, gate, {str(y): r[2] for y, r in zip(years, results)}


def versions(table: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {asof: table[table["asof"] == asof].reset_index(drop=True) for asof in ["full", *ASOF]}
    for asof in ASOF:
        if not (out[asof]["field_id"].to_numpy() == out["full"]["field_id"].to_numpy()).all():
            raise ValueError(f"as-of {asof} rows are not aligned with the full-season rows")
    return out


# --------------------------------------------------------------------------------------- fit and score


def adjusted(spec: Spec, rows: pd.DataFrame) -> pd.DataFrame:
    """The spec's feature matrix; with an adjustment, each feature minus its batch-group median (assessable)."""
    X = rows[spec.features].astype(float).reset_index(drop=True)
    if spec.adjust is None:
        return X
    key = rows["year"].astype(str).to_numpy()
    if spec.adjust == "yearcell":
        key = key + "|" + rows["cell"].astype(str).to_numpy()
    ok = rows["assessable"].to_numpy(bool)
    medians = X[ok].groupby(key[ok]).median()
    return X - medians.reindex(key).to_numpy()


def make_xgb(spec: Spec, truth: np.ndarray):
    from xgboost import XGBClassifier

    weight = float((truth == 0).sum() / (truth == 1).sum())
    constraints = "(" + ",".join(str(MONOTONE[f]) for f in spec.features) + ")"
    return XGBClassifier(**XGB_PARAMETERS, scale_pos_weight=weight, monotone_constraints=constraints)


def fit(spec: Spec, rows: pd.DataFrame):
    part = rows[rows["assessable"].to_numpy(bool)]
    X, y = adjusted(spec, part), part["is_silage"].to_numpy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        model = make_model() if spec.learner == "logistic" else make_xgb(spec, y)
        return model.fit(X, y)


def predict(spec: Spec, model, rows: pd.DataFrame) -> np.ndarray:
    """Silage score per row; NaN for rows that are not assessable."""
    probability = np.full(len(rows), np.nan)
    ok = rows["assessable"].to_numpy(bool)
    if ok.any():
        X = adjusted(spec, rows)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            probability[ok] = model.predict_proba(X[ok])[:, 1]
    return probability


def to_call(probability: np.ndarray) -> np.ndarray:
    return (np.nan_to_num(probability, nan=0.0) >= THRESHOLD).astype(int)


# ------------------------------------------------------------------------------- f5: calibrate + abstain


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def band_calls(p: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """1 silage, 0 grain, -1 abstain (inside [lo, hi) or no score)."""
    call = np.full(len(p), -1)
    finite = np.isfinite(p)
    call[finite & (p >= hi)] = 1
    call[finite & (p < lo)] = 0
    return call


def choose_band(truth: np.ndarray, p: np.ndarray) -> dict:
    best = None
    for lo in LO_GRID:
        for hi in HI_GRID:
            call = band_calls(p, lo, hi)
            coverage = float((call >= 0).mean())
            if coverage < COVERAGE_MIN:
                continue
            tp, fp = int(((call == 1) & (truth == 1)).sum()), int(((call == 1) & (truth == 0)).sum())
            precision = tp / (tp + fp) if tp + fp else -1.0
            key = (precision, coverage, -hi, lo)
            if best is None or key > best[0]:
                best = (key, {"lo": float(lo), "hi": float(hi), "coverage": round(coverage, 4),
                              "precision": round(precision, 4)})
    if best is None:
        return {"lo": THRESHOLD, "hi": THRESHOLD, "coverage": None, "precision": None, "note": "no band reached"}
    return best[1]


@dataclass
class Selective:
    base: Spec
    model: object
    calibrator: object
    band: dict

    def score(self, rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        raw = predict(self.base, self.model, rows)
        calibrated = np.full(len(rows), np.nan)
        ok = np.isfinite(raw)
        if ok.any():
            calibrated[ok] = self.calibrator.predict_proba(logit(raw[ok]).reshape(-1, 1))[:, 1]
        return calibrated, band_calls(calibrated, self.band["lo"], self.band["hi"])


def fit_selective(base: Spec, rows: pd.DataFrame) -> Selective:
    """Inner leave-one-year-out within ``rows`` -> Platt calibrator and abstention band; base fitted on all."""
    from sklearn.linear_model import LogisticRegression

    years = rows["year"].to_numpy()
    inner = np.full(len(rows), np.nan)
    for year in sorted(set(years)):
        held = years == year
        inner[held] = predict(base, fit(base, rows[~held]), rows[held])
    ok = np.isfinite(inner)
    truth = rows["is_silage"].to_numpy()
    calibrator = LogisticRegression(C=1e6, max_iter=1000).fit(logit(inner[ok]).reshape(-1, 1), truth[ok])
    calibrated = np.full(len(rows), np.nan)
    calibrated[ok] = calibrator.predict_proba(logit(inner[ok]).reshape(-1, 1))[:, 1]
    return Selective(base, fit(base, rows), calibrator, choose_band(truth, calibrated))


# ---------------------------------------------------------------------------------------------- metrics


def confusion(truth: np.ndarray, call: np.ndarray) -> dict:
    return {"TP": int(((call == 1) & (truth == 1)).sum()), "FP": int(((call == 1) & (truth == 0)).sum()),
            "FN": int(((call == 0) & (truth == 1)).sum()), "TN": int(((call == 0) & (truth == 0)).sum())}


def rates_from(c: dict) -> dict:
    tp, fp, fn, tn = c["TP"], c["FP"], c["FN"], c["TN"]

    def ratio(top: float, bottom: float) -> float:
        return round(top / bottom, 4) if bottom else float("nan")

    recall, grain_recall = ratio(tp, tp + fn), ratio(tn, tn + fp)
    return {"silage_precision": ratio(tp, tp + fp), "silage_recall": recall, "false_positive_rate": ratio(fp, fp + tn),
            "balanced_accuracy": round((recall + grain_recall) / 2, 4), "silage_f1": ratio(2 * tp, 2 * tp + fp + fn),
            "accuracy": ratio(tp + tn, tp + fp + fn + tn), "count_ratio": ratio(tp + fp, tp + fn)}


def metrics(table: pd.DataFrame, call: np.ndarray) -> dict:
    truth = table["is_silage"].to_numpy()
    c = confusion(truth, call)
    return {"n": len(table), "assessable": int(table["assessable"].sum()), "n_silage": int(truth.sum()),
            "decisive": int((call >= 0).sum()), "coverage": round(float((call >= 0).mean()), 4), **c, **rates_from(c)}


def unit_counts(truth: np.ndarray, call: np.ndarray, codes: np.ndarray, n_units: int) -> np.ndarray:
    cells = [(call == 1) & (truth == 1), (call == 1) & (truth == 0), (call == 0) & (truth == 1),
             (call == 0) & (truth == 0)]
    return np.stack([np.bincount(codes, weights=c.astype(float), minlength=n_units) for c in cells], axis=1)


def rate_arrays(counts: np.ndarray) -> dict:
    tp, fp, fn, tn = (counts[..., i] for i in range(4))
    with np.errstate(divide="ignore", invalid="ignore"):
        recall, grain_recall = tp / (tp + fn), tn / (tn + fp)
        return {"balanced_accuracy": (recall + grain_recall) / 2, "silage_f1": 2 * tp / (2 * tp + fp + fn),
                "silage_precision": tp / (tp + fp), "silage_recall": recall, "false_positive_rate": fp / (fp + tn)}


def paired_bootstrap(truth: np.ndarray, base_call: np.ndarray, arm_call: np.ndarray, units: np.ndarray) -> dict:
    """Arm minus base, resampling whole units (same draws as test_models/fieldMultiYear/evaluate.py)."""
    codes, uniques = pd.factorize(pd.Series(units).astype(str))
    n_units = len(uniques)
    picks = np.random.default_rng(SEED).integers(0, n_units, size=(DRAWS, n_units))
    weights = np.stack([np.bincount(row, minlength=n_units) for row in picks]).astype(float)
    base_u, arm_u = unit_counts(truth, base_call, codes, n_units), unit_counts(truth, arm_call, codes, n_units)
    base_d, arm_d = rate_arrays(weights @ base_u), rate_arrays(weights @ arm_u)
    base_p, arm_p = rate_arrays(base_u.sum(0)), rate_arrays(arm_u.sum(0))
    result = {"units": int(n_units)}
    for name in base_d:
        delta = arm_d[name] - base_d[name]
        finite = delta[np.isfinite(delta)]
        result[f"d_{name}"] = round(float(arm_p[name] - base_p[name]), 4)
        result[f"d_{name}_ci90"] = [round(float(q), 4) for q in np.quantile(finite, INTERVAL)] if len(finite) else None
        if name == "balanced_accuracy":
            result["d_balanced_accuracy_bonferroni"] = ([round(float(q), 4) for q in np.quantile(finite, BONF)]
                                                        if len(finite) else None)
    return result


def mcnemar(truth: np.ndarray, base_call: np.ndarray, arm_call: np.ndarray) -> dict:
    from scipy.stats import binomtest

    base_right, arm_right = base_call == truth, arm_call == truth
    base_only, arm_only = int((base_right & ~arm_right).sum()), int((~base_right & arm_right).sum())
    p = binomtest(arm_only, base_only + arm_only, 0.5).pvalue if base_only + arm_only else 1.0
    return {"base_only_right": base_only, "arm_only_right": arm_only, "p": round(float(p), 4)}


# ------------------------------------------------------------------------------------------------ score


def yearly_rows(split: str, model: str, table: pd.DataFrame, call: np.ndarray, years: list[int],
                in_sample: tuple[int, ...] = ()) -> list[dict]:
    rows = []
    for year in years:
        mask = (table["year"] == year).to_numpy()
        rows.append({"split": split, "model": model, "held_out": str(year), "in_sample": year in in_sample,
                     **metrics(table[mask], call[mask])})
    pool = [y for y in years if y not in in_sample]
    mask = table["year"].isin(pool).to_numpy()
    ratios = [r["count_ratio"] for r in rows if not r["in_sample"]]
    rows.append({"split": split, "model": model, "held_out": "pooled", "in_sample": False,
                 **metrics(table[mask], call[mask]), "years_pooled": "+".join(map(str, pool)),
                 "count_ratio_swing": round(max(ratios) - min(ratios), 4) if ratios else float("nan")})
    return rows


def run_loyo(full: pd.DataFrame, asof_tables: dict[str, pd.DataFrame]) -> tuple[dict, dict]:
    """LOYO calls for every spec, full season and as-of; f0_2023 fitted once on 2023."""
    years = full["year"].to_numpy()
    calls = {name: {v: np.zeros(len(full), int) for v in ["full", *ASOF]} for name in SPECS}
    probs = {name: np.full(len(full), np.nan) for name in SPECS}
    for name in FOLD_SPECS:
        spec = SPECS[name]
        for year in SEL_YEARS:
            held = years == year
            model = fit(spec, full[~held])
            probs[name][held] = predict(spec, model, full[held])
            calls[name]["full"][held] = to_call(probs[name][held])
            for asof in ASOF:
                part = asof_tables[asof][held]
                calls[name][asof][held] = to_call(predict(spec, model, part))
    spec = SPECS["f0_2023"]
    model = fit(spec, full[years == REF_YEAR])
    for year in SEL_YEARS:
        held = years == year
        probs["f0_2023"][held] = predict(spec, model, full[held])
        calls["f0_2023"]["full"][held] = to_call(probs["f0_2023"][held])
        for asof in ASOF:
            calls["f0_2023"][asof][held] = to_call(predict(spec, model, asof_tables[asof][held]))
    return calls, probs


def run_strict(full: pd.DataFrame) -> dict:
    years, cells = full["year"].to_numpy(), full["cell"].to_numpy()
    calls = {name: np.zeros(len(full), int) for name in SPECS}
    for name in FOLD_SPECS:
        spec = SPECS[name]
        for year in SEL_YEARS:
            for cell in sorted(set(cells)):
                held = (years == year) & (cells == cell)
                if held.any():
                    model = fit(spec, full[(years != year) & (cells != cell)])
                    calls[name][held] = to_call(predict(spec, model, full[held]))
    spec = SPECS["f0_2023"]
    for cell in sorted(set(cells)):
        model = fit(spec, full[(years == REF_YEAR) & (cells != cell)])
        for year in SEL_YEARS:   # 2023 itself is gate G1 (leave one cell out within 2023)
            held = (years == year) & (cells == cell)
            calls["f0_2023"][held] = to_call(predict(spec, model, full[held]))
    return calls


def run_expanding(full: pd.DataFrame) -> dict:
    years = full["year"].to_numpy()
    calls = {name: np.zeros(len(full), int) for name in FOLD_SPECS}
    for name in FOLD_SPECS:
        spec = SPECS[name]
        for year in EXPANDING_YEARS:
            held = years == year
            model = fit(spec, full[np.isin(years, [y for y in SEL_YEARS if y < year])])
            calls[name][held] = to_call(predict(spec, model, full[held]))
    return calls


def run_f5(base: Spec, full: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    years = full["year"].to_numpy()
    calibrated, call, bands = np.full(len(full), np.nan), np.full(len(full), -1), []
    for year in SEL_YEARS:
        held = years == year
        selective = fit_selective(base, full[~held])
        calibrated[held], call[held] = selective.score(full[held])
        bands.append({"held_out": year, **selective.band})
    return calibrated, call, bands


def compare(full: pd.DataFrame, base_call: np.ndarray, arm_call: np.ndarray, mask: np.ndarray) -> dict:
    truth, cells = full["is_silage"].to_numpy(), full["cell"].to_numpy()
    result = paired_bootstrap(truth[mask], base_call[mask], arm_call[mask], cells[mask])
    if (arm_call[mask] >= 0).all():
        result["mcnemar"] = mcnemar(truth[mask], base_call[mask], arm_call[mask])
    return result


def gate_status(observed: dict, expected: dict) -> dict:
    return {"observed": observed, "expected": expected, "reproduced": observed == expected}


def cmd_build(workers: int) -> None:
    started = time.time()
    table, gate, digests = load_years(ALL_YEARS, workers)
    print(f"cached {len(table)} rows ({table['asof'].value_counts().to_dict()}), GL {gate}, digests {digests}, "
          f"{time.time() - started:.0f} s")


def cmd_score(workers: int) -> None:
    prereg = check_prereg()
    started = time.time()
    table, gl, digests = load_years(SEL_YEARS, workers)
    if (table["year"] == HOLDOUT).any():
        raise SystemExit("the 2025 holdout leaked into the selection table")
    tables = versions(table)
    full = tables["full"]
    years, truth = full["year"].to_numpy(), full["is_silage"].to_numpy()
    sel = np.isin(years, SEL_YEARS)
    print(f"selection roster {len(full)} field-years, {int(truth.sum())} silage, "
          f"{int((~full['assessable']).sum())} not assessable; {time.time() - started:.0f} s", flush=True)

    # Gates R1, GS, G1, GL (pipeline checks only; f0_2023 numbers are already published).
    roster = {int(y): int((years == y).sum()) for y in SEL_YEARS}
    loyo_calls, loyo_probs = run_loyo(full, {a: tables[a] for a in ASOF})
    print(f"LOYO fitted, {time.time() - started:.0f} s", flush=True)
    strict_calls = run_strict(full)
    print(f"strict fitted, {time.time() - started:.0f} s", flush=True)
    expanding_calls = run_expanding(full)
    print(f"expanding fitted, {time.time() - started:.0f} s", flush=True)

    fmy = pd.read_csv(FMY, dtype={"held_out": str})
    fmy = fmy[(fmy["split"] == "loyo") & (fmy["model"] == "S")]
    gs = {}
    for year in SEL_YEARS:
        if year == REF_YEAR:
            continue
        expected = fmy[fmy["held_out"] == str(year)].iloc[0]
        mask = years == year
        gs[str(year)] = gate_status(confusion(truth[mask], loyo_calls["f0_2023"]["full"][mask]),
                                    {k: int(expected[k]) for k in ["TP", "FP", "FN", "TN"]})
    in_ref = years == REF_YEAR
    gates = {"R1": gate_status(roster, R1_EXPECTED),
             "G1": gate_status(confusion(truth[in_ref], strict_calls["f0_2023"][in_ref]), G1_EXPECTED),
             "GS": {"reproduced": all(v["reproduced"] for v in gs.values()), "by_year": gs},
             "GL": gl or {"reproduced": False, "note": "no 2023 gate result"}}
    failed = [k for k, v in gates.items() if not v["reproduced"]]

    # Per-year tables.
    rows = []
    for name in SPECS:
        in_sample = (REF_YEAR,) if name == "f0_2023" else ()
        rows += yearly_rows("loyo", name, full, loyo_calls[name]["full"], SEL_YEARS, in_sample)
        for asof in ASOF:
            rows += yearly_rows(f"asof_{asof}", name, tables[asof], loyo_calls[name][asof], SEL_YEARS, in_sample)
        rows += yearly_rows("strict", name, full, strict_calls[name], SEL_YEARS, in_sample)
        if name in expanding_calls:
            rows += yearly_rows("expanding", name, full, expanding_calls[name], EXPANDING_YEARS)

    # Primary comparisons and supporting ones, against f0_all.
    def pooled(split: str, name: str) -> dict:
        return next(r for r in rows if r["split"] == split and r["model"] == name and r["held_out"] == "pooled")

    comparisons = {}
    exp_mask = np.isin(years, EXPANDING_YEARS)
    for name in CANDIDATES:
        primary = compare(full, loyo_calls["f0_all"]["full"], loyo_calls[name]["full"], sel)
        per_year = {}
        for year in SEL_YEARS:
            mask = years == year
            per_year[str(year)] = compare(full, loyo_calls["f0_all"]["full"], loyo_calls[name]["full"], mask)
        comparisons[name] = {
            "loyo": primary, "loyo_per_year": per_year,
            "strict": compare(full, strict_calls["f0_all"], strict_calls[name], sel),
            "expanding": compare(full, expanding_calls["f0_all"], expanding_calls[name], exp_mask),
            **{f"asof_{a}": compare(tables[a], loyo_calls["f0_all"][a], loyo_calls[name][a], sel) for a in ASOF},
            "swing": pooled("loyo", name)["count_ratio_swing"],
            "swing_f0_all": pooled("loyo", "f0_all")["count_ratio_swing"],
            "years_better_than_f0_all": sum(per_year[str(y)]["d_balanced_accuracy"] > 0 for y in SEL_YEARS),
        }
    ref_mask = sel & ~in_ref
    comparisons["f0_2023_vs_f0_all"] = {
        "note": "information: f0_2023 minus f0_all over the six selection years other than 2023",
        "loyo": compare(full, loyo_calls["f0_all"]["full"], loyo_calls["f0_2023"]["full"], ref_mask)}

    # Decision.
    eligible = {}
    for name in CANDIDATES:
        c = comparisons[name]
        lo = c["loyo"]["d_balanced_accuracy_ci90"][0]
        eligible[name] = {"d_balanced_accuracy": c["loyo"]["d_balanced_accuracy"], "ci90_lo": lo,
                          "ci90": c["loyo"]["d_balanced_accuracy_ci90"], "swing": c["swing"],
                          "swing_f0_all": c["swing_f0_all"],
                          "eligible": bool(c["loyo"]["d_balanced_accuracy"] > 0 and lo > 0
                                           and c["swing"] <= c["swing_f0_all"])}
    winners = [n for n in CANDIDATES if eligible[n]["eligible"]]
    adopted = max(winners, key=lambda n: pooled("loyo", n)["balanced_accuracy"]) if winners else None
    if failed:
        decision = f"HELD (gate failed: {', '.join(failed)})"
    elif adopted:
        decision = f"ADOPT {adopted}"
    else:
        decision = "KEEP f0 (NO IMPROVEMENT SHOWN)"

    # f5 on its base.
    base_name = adopted if adopted and not failed else "f0_all"
    f5_prob, f5_call, f5_bands = run_f5(SPECS[base_name], full)
    rows += yearly_rows("loyo", "f5_cal_abstain", full, f5_call, SEL_YEARS)
    as_grain = np.where(f5_call == 1, 1, 0)
    rows += yearly_rows("loyo_abstain_as_grain", "f5_cal_abstain", full, as_grain, SEL_YEARS)
    f5_pooled = pooled("loyo", "f5_cal_abstain")
    base_pooled = pooled("loyo", base_name)
    f5_vs_base = compare(full, loyo_calls[base_name]["full"], f5_call, sel)
    f5_vs_f0 = compare(full, loyo_calls["f0_all"]["full"], as_grain, sel)
    f5_ok = bool(f5_pooled["coverage"] >= COVERAGE_MIN and f5_vs_base["d_silage_precision"] > 0
                 and f5_vs_base["d_silage_precision_ci90"][0] > 0)
    f5_decision = ("HELD (gate failed)" if failed else
                   f"ADOPT f5 as the selective mode of {base_name}" if f5_ok else "f5 NOT ADOPTED")

    by_year = pd.DataFrame(rows)
    by_year[["d_ba_vs_f0_all", "d_ba_lo", "d_ba_hi"]] = np.nan
    for name in CANDIDATES:
        for row_mask, key in [((by_year["split"] == "loyo") & (by_year["model"] == name), "loyo")]:
            for idx in by_year.index[row_mask]:
                held = by_year.at[idx, "held_out"]
                result = (comparisons[name][key] if held == "pooled" else comparisons[name]["loyo_per_year"][held])
                by_year.loc[idx, ["d_ba_vs_f0_all", "d_ba_lo", "d_ba_hi"]] = [
                    result["d_balanced_accuracy"], *result["d_balanced_accuracy_ci90"]]

    OUT.mkdir(parents=True, exist_ok=True)
    by_year.to_csv(OUT / "selection_by_year.csv", index=False, lineterminator="\n")
    predictions = full[["field_id", "parcel_id", "year", "cell", "label", "assessable"]].copy()
    for name in SPECS:
        predictions[f"p_loyo_{name}"] = np.round(loyo_probs[name], 4)
        predictions[f"call_loyo_{name}"] = loyo_calls[name]["full"]
        predictions[f"call_strict_{name}"] = strict_calls[name]
    predictions["p_loyo_f5_calibrated"] = np.round(f5_prob, 4)
    predictions["call_loyo_f5"] = f5_call
    predictions.to_csv(OUT / "predictions_quebec.csv", index=False, lineterminator="\n")

    summary = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration": prereg, "inputs": digests, "gates": gates, "decision": decision,
        "adopted": adopted if not failed else None, "eligibility": eligible,
        "pooled_loyo": {n: pooled("loyo", n) for n in SPECS},
        "comparisons": comparisons,
        "f5": {"base": base_name, "decision": f5_decision, "pooled": f5_pooled, "base_pooled": base_pooled,
               "vs_base": f5_vs_base, "abstain_as_grain_vs_f0_all": f5_vs_f0, "bands_by_fold": f5_bands},
        "runtime_s": round(time.time() - started, 1),
    }
    (OUT / "decision.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8",
                                       newline="\n")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    show = ["split", "model", "held_out", "n", "TP", "FP", "FN", "TN", "silage_precision", "silage_recall",
            "false_positive_rate", "balanced_accuracy", "silage_f1", "count_ratio", "count_ratio_swing", "coverage"]
    print(by_year.loc[by_year["held_out"] == "pooled", show].to_string(index=False))
    for key, gate in gates.items():
        print(f"{key}: {'REPRODUCED' if gate['reproduced'] else 'NOT REPRODUCED'}")
    for name, e in eligible.items():
        print(f"{name}: dBA {e['d_balanced_accuracy']:+.4f} CI90 {e['ci90']} swing {e['swing']} "
              f"(f0_all {e['swing_f0_all']}) eligible={e['eligible']}")
    print(f"DECISION: {decision}")
    print(f"f5 on {base_name}: coverage {f5_pooled['coverage']}, precision {f5_pooled['silage_precision']} vs "
          f"{base_pooled['silage_precision']}, d {f5_vs_base['d_silage_precision']} "
          f"CI {f5_vs_base['d_silage_precision_ci90']} -> {f5_decision}")
    print(f"done in {time.time() - started:.0f} s")


# ------------------------------------------------------------------------------------------------ final


def maryland_table(spec_needs_lswi: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    import geopandas as gpd

    data = data_dir()
    labels = gpd.read_parquet(data / "labels" / "barc_2021_2023.parquet")
    series = load_series(data / "s2_series" / "barc_2021_2023")
    return md_features(labels, series, spec_needs_lswi), labels, series


def md_features(labels: pd.DataFrame, series: pd.DataFrame, lswi: bool) -> pd.DataFrame:
    """Maryland roster (all 44 field-years) with the features a spec needs; the farm is one 'cell'."""
    table = evaluation_table(labels, series)
    if lswi:
        table = table.merge(september_stats(series), on=["field_id", "year"], how="left", validate="one_to_one")
    for column in LSWI:
        if column not in table:
            table[column] = np.nan
    return table.assign(cell="barc_farm")


def response_seconds(spec: Spec, model, labels: pd.DataFrame, series: pd.DataFrame,
                     selective: Selective | None = None) -> float:
    """Median over passes of seconds per field-year: features (+ spec steps) and prediction, no download/fit."""
    per_field = []
    for _ in range(TIMING_PASSES):
        start = time.perf_counter()
        table = md_features(labels, series, spec.lswi)
        if selective is not None:
            selective.score(table)
        else:
            to_call(predict(spec, model, table))
        per_field.append((time.perf_counter() - start) / len(table))
    return round(float(np.median(per_field)), 5)


def md_result(name: str, trained_on: str, table: pd.DataFrame, call: np.ndarray) -> dict:
    truth = table["is_silage"].to_numpy()
    decisive = call >= 0
    out = {"fit": name, "trained_on": trained_on, **metrics(table, call)}
    if decisive.all():
        out["intervals_90_field_bootstrap"] = bootstrap_intervals(truth, call, groups=table["field_id"].to_numpy())
    else:
        out["complete_roster_silage_recall"] = round(out["TP"] / int(truth.sum()), 4)
        out["intervals_90_field_bootstrap"] = bootstrap_intervals(
            truth[decisive], call[decisive], groups=table["field_id"].to_numpy()[decisive])
    return out


def cmd_final(workers: int) -> None:
    import geopandas as gpd

    prereg = check_prereg()
    decision_path = OUT / "decision.json"
    if not decision_path.exists():
        raise SystemExit("no out/decision.json: run `score` first; final never runs before the decision")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    started = time.time()
    table, _, digests = load_years(ALL_YEARS, workers)
    full = versions(table)["full"]
    years = full["year"].to_numpy()
    sel, hold = np.isin(years, SEL_YEARS), years == HOLDOUT
    train, test = full[sel], full[hold].reset_index(drop=True)

    # 2025 holdout: every candidate fitted on the 7 selection years (f0_2023 on 2023).
    hold_calls, models = {}, {}
    for name, spec in SPECS.items():
        rows = train[train["year"] == REF_YEAR] if spec.fixed_year else train
        models[name] = fit(spec, rows)
        hold_calls[name] = to_call(predict(spec, models[name], test))
    f5_base = decision["f5"]["base"]
    selective = fit_selective(SPECS[f5_base], train)
    _, hold_calls["f5_cal_abstain"] = selective.score(test)
    hold_rows, hold_cmp = [], {}
    everything = np.ones(len(test), bool)
    for name, call in hold_calls.items():
        hold_rows.append({"model": name, **metrics(test, call)})
        if name != "f0_all":
            hold_cmp[name] = compare(test, hold_calls["f0_all"], np.where(call == 1, 1, 0) if name.startswith("f5")
                                     else call, everything)
    print(f"2025 holdout scored, {time.time() - started:.0f} s", flush=True)

    # Maryland: gates, then f0 and the adopted candidate only.
    data = data_dir()
    md, md_labels, md_series = maryland_table()
    published = gpd.read_parquet(data / "labels" / "quebec_maize_2023.parquet")
    train_318 = evidence_table(published, load_series(data / "s2_series" / "quebec_maize_2023"))
    model_318 = fit(SPECS["f0_all"], train_318)
    md_truth = md["is_silage"].to_numpy()
    g2 = confusion(md_truth, to_call(predict(SPECS["f0_all"], model_318, md)))
    g3 = confusion(md_truth, to_call(predict(SPECS["f0_2023"], models["f0_2023"], md)))
    md_gates = {"G2": gate_status(g2, G2_EXPECTED), "G3": gate_status(g3, G3_EXPECTED)}

    adopted = decision.get("adopted")
    md_rows = [md_result("f0_2023", "qcm_2023 (= G3)", md, to_call(predict(SPECS["f0_2023"], models["f0_2023"], md))),
               md_result("f0_all", "7 selection years", md, to_call(predict(SPECS["f0_all"], models["f0_all"], md)))]
    all8 = full
    model_f0_all8 = fit(SPECS["f0_all"], all8)
    md_rows.append(md_result("f0_all", "all 8 years (information)", md,
                             to_call(predict(SPECS["f0_all"], model_f0_all8, md))))
    timing = {"f0": {"seconds_per_field": response_seconds(SPECS["f0_all"], models["f0_all"], md_labels, md_series)}}
    fit_t = time.perf_counter()
    fit(SPECS["f0_all"], train)
    timing["f0"]["fit_seconds"] = round(time.perf_counter() - fit_t, 3)
    if adopted:
        spec = SPECS[adopted]
        md_rows.append(md_result(adopted, "7 selection years", md, to_call(predict(spec, models[adopted], md))))
        md_rows.append(md_result(adopted, "all 8 years (information)", md,
                                 to_call(predict(spec, fit(spec, all8), md))))
        fit_t = time.perf_counter()
        fit(spec, train)
        timing[adopted] = {"seconds_per_field": response_seconds(spec, models[adopted], md_labels, md_series),
                           "fit_seconds": round(time.perf_counter() - fit_t, 3)}
    if decision["f5"]["decision"].startswith("ADOPT"):
        _, call = selective.score(md)
        md_rows.append(md_result("f5_cal_abstain", f"7 selection years, base {f5_base}, band "
                                 f"[{selective.band['lo']}, {selective.band['hi']})", md, call))
        timing["f5_cal_abstain"] = {"seconds_per_field": response_seconds(SPECS[f5_base], None, md_labels,
                                                                          md_series, selective)}

    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(hold_rows).to_csv(OUT / "holdout_2025.csv", index=False, lineterminator="\n")
    pd.DataFrame([{k: v for k, v in r.items() if k != "intervals_90_field_bootstrap"} for r in md_rows]).to_csv(
        OUT / "maryland.csv", index=False, lineterminator="\n")
    final = {"generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "preregistration": prereg,
             "decision_from_score": decision["decision"], "f5_decision": decision["f5"]["decision"],
             "inputs": digests, "holdout_2025": {"rows": hold_rows, "vs_f0_all": hold_cmp,
                                                 "f5_band": selective.band, "f5_base": f5_base},
             "maryland_gates": md_gates, "maryland": md_rows, "response_time": timing,
             "runtime_s": round(time.time() - started, 1)}
    (OUT / "final.json").write_text(json.dumps(final, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    show = ["model", "n", "TP", "FP", "FN", "TN", "silage_precision", "silage_recall", "false_positive_rate",
            "balanced_accuracy", "silage_f1", "count_ratio", "coverage"]
    print(pd.DataFrame(hold_rows)[show].to_string(index=False))
    for name, c in hold_cmp.items():
        print(f"2025 {name}: dBA {c['d_balanced_accuracy']:+.4f} CI90 {c['d_balanced_accuracy_ci90']}")
    for key, gate in md_gates.items():
        print(f"{key}: {'REPRODUCED' if gate['reproduced'] else 'NOT REPRODUCED'} {gate['observed']}")
    md_show = ["fit", "trained_on", "n", "TP", "FP", "FN", "TN", "silage_precision", "silage_recall",
               "false_positive_rate", "balanced_accuracy", "coverage"]
    print(pd.DataFrame(md_rows)[md_show].to_string(index=False))
    print(json.dumps(timing))
    print(f"done in {time.time() - started:.0f} s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["build", "score", "final"])
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    {"build": cmd_build, "score": cmd_score, "final": cmd_final}[args.command](args.workers)


if __name__ == "__main__":
    main()
