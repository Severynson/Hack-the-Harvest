"""Every model in the repository, read into one table so the board can rank and compare them.

Nothing here trains or reruns a model. Each loader reads files a model already wrote, so the board
shows whatever is on disk right now; rerun a model and refresh the page.

Two tables come out:
    backtest   one row per model, target and test year:
               model_id, model, source, target, year, state_error_pct, us_error_pct, n_states, metric
    forecasts  one row per model, target and state for the forecast year:
               model_id, target, state, predicted, lo80, hi80

Definitions (the same ones kernelag.state_model.state_error uses):
    state_error_pct  100 * sum(|predicted - actual|) / sum(actual) over the states, i.e. the share of
                     acres put in the wrong state (WAPE)
    us_error_pct     100 * (sum(predicted) - sum(actual)) / sum(actual), signed
Some folders store these per year; where a folder stores raw predictions the board computes them with
the formula above. Each row says which in the ``metric`` column.

Adding a model: see board/README.md. In short, any folder with a ``board_backtest.csv`` (and optionally
``board_forecast.csv`` and ``board_models.json``) is picked up automatically; ``board.publish`` writes them.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent

# Signal families, matched against a model's name and, where known, its feature names.
FAMILIES = {
    "satellite": ["sat", "ndvi", "sentinel", "field_model"],
    "weather": ["weather", "drought", "rain", "gdd", "frost", "freeze", "stress", "condition", "poor",
                "loss", "context", "physical", "matur", "yield", "hot", "pasture", "planting"],
    "economy": ["price", "dairy", "cow", "cattle", "forage", "hay", "milk"],
    "FSA": ["fsa"],
    "insurance": ["rma", "insur"],
    "NASS current year": [],          # set by a model card; names alone can't tell current from past NASS
    "NASS history": ["same_as_last_year", "persistence", "mean", "rev", "trend", "nass", "planted",
                     "not_grain", "non_grain", "nodrift", "share", "last"],
}
METHODS = [("xgb", "gradient boosting"), ("gbt", "gradient boosting"), ("ridge", "ridge regression"),
           ("huber", "robust regression"), ("lad", "robust regression"), ("regression", "regression"),
           ("ensemble", "ensemble"), ("blend", "ensemble"), ("reconciled", "ensemble"),
           ("topdown", "top-down split")]

# Feature sets the code defines, so the board can show inputs, not just names.
KNOWN_FEATURES = {
    "kernel/reversion_only": ["reversion"],
    "kernel/nass_acres": ["reversion", "d_planted", "d_not_grain"],
    "kernel/stress": ["reversion", "d_drought", "d_poor", "yield_shock", "d_loss"],
    "kernel/all_public": ["reversion", "d_planted", "d_not_grain", "d_cows", "d_cattle", "yield_shock",
                          "d_price", "d_drought", "d_poor", "d_loss", "rain_anom", "early_frost", "d_mature"],
}


def families(name: str, features: list[str] | None = None) -> list[str]:
    """Signal families a model uses, from its name and feature names.

    Words are matched against whole name parts ("rain" matches rain_anom, not grain); keywords with
    an underscore are matched as substrings.
    """
    texts = [name.lower(), *[f.lower() for f in features or []]]
    parts = {p for t in texts for p in re.split(r"[^a-z]+", t) if p}
    joined = " ".join(texts)

    def hit(word: str) -> bool:
        return word in joined if "_" in word else any(p.startswith(word) for p in parts)

    found = [family for family, words in FAMILIES.items() if any(hit(w) for w in words)]
    return found or ["not recorded"]


RULES = ["same_as_last_year", "persistence", "mean", "nass_latest", "trend", "share"]


def method(name: str) -> str:
    low = name.lower()
    found = next((label for key, label in METHODS if key in low), None)
    if found:
        return found
    return "rule (no fitting)" if any(key in low for key in RULES) else "not recorded"


def owner(folder: Path) -> str | None:
    """The agent tag ([cc-daniel] ...) on the last commit that touched the folder, if git is there."""
    try:
        subject = subprocess.run(["git", "log", "-1", "--format=%s", "--", str(folder)], cwd=REPO,
                                 capture_output=True, text=True, timeout=5, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.match(r"\[([^\]]+)\]", subject.strip())
    return match.group(1) if match else None


def state_code(value) -> str:
    """Two-letter code for a state written any way (AL, Alabama, ALABAMA); "US" for national rows."""
    from kernelag.context import STATE_NAMES
    text = str(value).strip().upper()
    if text.startswith("US"):
        return "US"
    if text in STATE_NAMES:
        return text
    by_name = {name: code for code, name in STATE_NAMES.items()}
    return by_name.get(text, str(value))


def errors_from_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    """Per model, target and year: state and US error from state-level predictions.

    Input columns: model, target, year, state, actual, predicted, and optionally asof (sep/oct/nov).
    """
    rows = []
    keys = ["model", "target", "year"] + (["asof"] if "asof" in frame else [])
    for key, g in frame.groupby(keys, dropna=False):
        model, target, year = key[:3]
        asof = key[3] if len(key) > 3 else None
        g = g.dropna(subset=["actual", "predicted"])
        total = g["actual"].sum()
        if total <= 0:
            continue
        miss = g["predicted"] - g["actual"]
        rows.append({"model": model, "target": target, "year": int(year), "n_states": len(g), "asof": asof,
                     "state_error_pct": round(100 * miss.abs().sum() / total, 2),
                     "us_error_pct": round(100 * miss.sum() / total, 2)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- loaders, one per folder

def load_kernel():
    """The main pipeline (kernelag.state_model): backtest per predictor, and the 2026 forecast."""
    out = REPO / "data" / "models"
    parts = []
    for name, asof in [("state_model_backtest.csv", "nov"), ("state_model_backtest_asof_sep.csv", "sep")]:
        if (out / name).exists():
            part = pd.read_csv(out / name)
            parts.append(part.assign(asof=asof))
    bt = pd.concat(parts)
    bt = bt[bt["scope"] == "all_states"].rename(columns={"series": "target", "predictor": "model",
                                                         "total_error_pct": "us_error_pct"})
    bt["metric"] = "stored per year"
    fc = pd.read_csv(out / "state_forecast_2026.csv")
    fc = fc[~fc["state"].str.startswith("US")]
    forecasts = []
    for target in ["silage", "grain"]:
        methods = fc[f"{target}_method"].dropna().unique()
        name = "reversion_only" if target == "silage" else "nass_latest"
        if target == "silage" and len(methods) == 1:
            name = methods[0]
        forecasts.append(pd.DataFrame({"model": name, "target": target, "state": fc["state"],
                                       "predicted": fc[target], "lo80": fc[f"{target}_lo80"],
                                       "hi80": fc[f"{target}_hi80"]}))
    note = {"grain/nass_latest": "Grain rows marked nass_forecast repeat NASS's own November forecast."}
    return "kernel", out, bt, pd.concat(forecasts), note


def load_daniel():
    folder = REPO / "test_models" / "danielModel"
    out = folder / "out"
    ridge = pd.read_csv(out / "backtest_by_year.csv")
    gbt = pd.read_csv(out / "gbt_backtest_by_year.csv").rename(columns={"candidate": "model"})
    gbt["target"] = gbt["model"].str.split("_").str[0]
    bt = pd.concat([ridge.rename(columns={"candidate": "model"}), gbt])
    bt = bt.rename(columns={"states": "n_states"})
    bt["metric"] = "stored per year"
    metrics = json.loads((out / "metrics.json").read_text())
    bt["asof"] = metrics.get("asof")
    f1 = pd.read_csv(out / "forecast_2026.csv")
    f2 = pd.read_csv(out / "forecast_2026_gbt.csv")
    gbt_names = json.loads((out / "gbt_metrics.json").read_text()).get("saved_models", {})
    forecasts = [
        pd.DataFrame({"model": metrics["silage_choice"], "target": "silage", "state": f1["state"],
                      "predicted": f1["silage_acres"], "lo80": f1["silage_lo80"], "hi80": f1["silage_hi80"]}),
        pd.DataFrame({"model": metrics["grain_choice"], "target": "grain", "state": f1["state"],
                      "predicted": f1["grain_acres"], "lo80": f1["grain_lo80"], "hi80": f1["grain_hi80"]}),
        pd.DataFrame({"model": gbt_names.get("silage", "silage_gbt"), "target": "silage", "state": f2["state"],
                      "predicted": f2["silage_acres"], "lo80": f2["silage_lo80"], "hi80": f2["silage_hi80"]}),
    ]
    for kind in ["correction", "independent"]:
        forecasts.append(pd.DataFrame({
            "model": gbt_names.get(f"grain_{kind}", f"grain_gbt_{kind}"), "target": "grain", "state": f2["state"],
            "predicted": f2[f"grain_{kind}_acres"], "lo80": f2[f"grain_{kind}_lo80"],
            "hi80": f2[f"grain_{kind}_hi80"]}))
    feats = pd.read_csv(out / "gbt_importance.csv").groupby("model")["feature"].apply(list).to_dict()
    return "danielModel", folder, bt, pd.concat(forecasts), {}, feats


def slate_features() -> dict:
    """Feature lists from test_models/accuracy/state_candidates.py SLATE, read without importing it.

    Importing that file pulls in scikit-learn and xgboost, which can take many seconds on a laptop, so the
    top-level list/dict assignments are evaluated on their own (no builtins, no imports).
    """
    import ast
    path = REPO / "test_models" / "accuracy" / "state_candidates.py"
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return {}
    names: dict = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if not isinstance(node.value, (ast.List, ast.Dict, ast.BinOp, ast.Tuple, ast.Constant)):
                continue
            try:
                names[node.targets[0].id] = eval(compile(ast.Expression(node.value), str(path), "eval"),
                                                 {"__builtins__": {}}, names)
            except Exception:  # noqa: BLE001, S112 - skip anything that isn't plain data
                continue
    slate = names.get("SLATE", {})
    return {name: list(cfg.get("features", [])) for name, cfg in slate.items() if isinstance(cfg, dict)}


def load_accuracy_state():
    folder = REPO / "test_models" / "accuracy" / "state"
    pred = pd.read_csv(folder / "predictions.csv").rename(columns={"candidate": "model"})
    pred["target"] = "silage"
    bt = errors_from_predictions(pred)
    bt["metric"] = "computed from predictions"
    return "accuracy/state", folder, bt, None, {}, slate_features()


def load_accuracy_national():
    """US-only candidates: no state split, so only the US error exists."""
    folder = REPO / "test_models" / "accuracy" / "national"
    pred = pd.read_csv(folder / "predictions.csv").rename(columns={"candidate": "model"})
    bt = pd.DataFrame({"model": pred["model"], "target": "silage", "year": pred["year"],
                       "n_states": pred["states"], "state_error_pct": float("nan"),
                       "us_error_pct": pred["signed_error_pct"].round(2), "metric": "stored per year (US only)"})
    feats = pd.read_csv(folder / "weights.csv").groupby("candidate")["feature"].apply(
        lambda s: sorted(set(s))).to_dict()
    return "accuracy/national", folder, bt, None, {}, feats


def load_test_model():
    folder = REPO / "test_models" / "testModel"
    d = json.loads((folder / "out" / "state_metrics.json").read_text())
    rows = []
    for target in ["silage", "grain"]:
        for model, years in d.get(target, {}).get("by_year", {}).items():
            for year, m in years.items():
                rows.append({"model": model, "target": target, "year": int(year), "n_states": m.get("n_states"),
                             "state_error_pct": m.get("wape_pct"), "us_error_pct": m.get("us_error_pct"),
                             "metric": "stored per year"})
    fc = pd.read_csv(folder / "out" / "forecast_2026.csv")
    sel = json.loads((folder / "out" / "metrics.json").read_text()).get("selected", {})
    forecasts = []
    for target, col in [("silage", "silage_kacres"), ("grain", "grain_kacres")]:
        name = sel.get(target) or sel.get(f"jan_{target}") or f"us_{target}"
        forecasts.append(pd.DataFrame({"model": f"US model: {name}", "target": target, "state": fc["area"],
                                       "predicted": fc[col] * 1000, "lo80": None, "hi80": None}))
    return "testModel", folder, pd.DataFrame(rows), pd.concat(forecasts), {}


SKIP_DIRS = {"node_modules", "__pycache__", "jupyter", "workspace", "web"}


def find_files(name: str) -> list[Path]:
    """Files called ``name`` anywhere in the repo, skipping hidden folders, environments and big data kits."""
    import os
    hits = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        if name in files:
            hits.append(Path(root) / name)
    return sorted(hits)


def load_plugins():
    """Any folder holding board_backtest.csv and/or board_forecast.csv (written by board.publish)."""
    found = []
    folders = {p.parent for name in ["board_backtest.csv", "board_forecast.csv"] for p in find_files(name)}
    for folder in sorted(folders):
        if any(part.startswith(".") for part in folder.relative_to(REPO).parts):
            continue
        path = folder / "board_backtest.csv"
        columns = ["model", "target", "year", "state_error_pct", "us_error_pct", "n_states", "metric", "asof"]
        bt = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=columns)
        if "state_error_pct" not in bt and {"actual", "predicted"} <= set(bt.columns):
            bt = errors_from_predictions(bt)
            bt["metric"] = "computed from predictions"
        bt = bt.reindex(columns=columns)
        bt["metric"] = bt["metric"].fillna("stored per year")
        fc_path = folder / "board_forecast.csv"
        fc = pd.read_csv(fc_path) if fc_path.exists() else None
        cards_path = folder / "board_models.json"
        cards = json.loads(cards_path.read_text()) if cards_path.exists() else {}
        name = str(folder.relative_to(REPO))
        if name.endswith(("/out", "/board")):
            name = name.rsplit("/", 1)[0]
        name = name.removeprefix("test_models/")
        found.append((name, folder, bt, fc, {}, {}, cards))
    return found


# ---------------------------------------------------------------- field-level (satellite) models

def _f1(p, r):
    return round(2 * p * r / (p + r), 4) if p and r and (p + r) > 0 else None


def field_models() -> tuple[pd.DataFrame, list[str]]:
    """Field classifiers (silage vs grain from the Sentinel-2 series), scored on labeled fields.

    Different folders score on different field sets, so the ``evaluated_on`` column matters more than
    the rank. Columns: source, model, evaluated_on, n_fields, silage_precision, silage_recall, silage_f1,
    accuracy, status, note.
    """
    rows, problems = [], []
    keep = ["silage_precision", "silage_recall", "accuracy"]
    try:
        rep = pd.read_csv(REPO / "data" / "models" / "field_model_report.csv")
        for _, r in rep.iterrows():
            label = "always_grain (baseline)" if "always_grain" in r["check"] else "field_model (logistic)"
            rows.append({"source": "kernel", "model": label, "evaluated_on": r["check"],
                         "n_fields": int(r["n_grain"] + r["n_silage"]), **{k: r.get(k) for k in keep},
                         "silage_f1": _f1(r.get("silage_precision"), r.get("silage_recall")), "status": "",
                         "note": ""})
    except Exception as error:  # noqa: BLE001
        problems.append(f"kernel field model: {error}")
    try:
        res = json.loads((REPO / "test_models" / "codexFieldBaseline" / "out" / "results.json").read_text())
        for check in ["quebec_spatial_oof", "maryland_external_reused_cohort"]:
            for model, m in res.get(check, {}).items():
                if isinstance(m, dict) and "silage_recall" in m:
                    rows.append({"source": "codexFieldBaseline", "model": model, "evaluated_on": check,
                                 "n_fields": m.get("n_grain", 0) + m.get("n_silage", 0),
                                 **{k: m.get(k) for k in keep},
                                 "silage_f1": m.get("silage_f1") or _f1(m.get("silage_precision"), m.get("silage_recall")),
                                 "status": "", "note": ""})
    except Exception as error:  # noqa: BLE001
        problems.append(f"codexFieldBaseline: {error}")
    for ledger in sorted((REPO / "autoresearch" / "ledger").glob("*.tsv")):
        try:
            t = pd.read_csv(ledger, sep="\t")
            for _, r in t.iterrows():
                rows.append({"source": f"autoresearch/{ledger.stem}", "model": str(r.get("commit", "")),
                             "evaluated_on": "autoresearch validation", "n_fields": None,
                             "silage_precision": None, "silage_recall": None, "accuracy": r.get("balanced_acc"),
                             "silage_f1": r.get("val_f1"), "status": r.get("status", ""),
                             "note": str(r.get("description", ""))})
        except Exception as error:  # noqa: BLE001
            problems.append(f"{ledger.name}: {error}")
    for path in find_files("board_field.csv"):
        try:
            t = pd.read_csv(path)
            t["source"] = str(path.parent.relative_to(REPO))
            rows.extend(t.to_dict(orient="records"))
        except Exception as error:  # noqa: BLE001
            problems.append(f"{path}: {error}")
    return pd.DataFrame(rows), problems


LOADERS = [load_kernel, load_daniel, load_accuracy_state, load_accuracy_national, load_test_model]


def state_predictions() -> pd.DataFrame:
    """State-level backtest predictions, where a folder keeps them: model_id, target, year, state, actual,
    predicted, asof. Feeds the map's per-state error layer. Folders that store only yearly totals
    (kernel, danielModel) can't be split by state and are absent here."""
    frames = []
    acc = REPO / "test_models" / "accuracy" / "state" / "predictions.csv"
    if acc.exists():
        t = pd.read_csv(acc).rename(columns={"candidate": "model"})
        t["model_id"] = "accuracy/state/silage/" + t["model"]
        t["target"], t["asof"] = "silage", None
        frames.append(t)
    for path in find_files("board_backtest.csv"):
        t = pd.read_csv(path)
        if not {"actual", "predicted", "state"} <= set(t.columns):
            continue
        name = str(path.parent.relative_to(REPO))
        if name.endswith(("/out", "/board")):
            name = name.rsplit("/", 1)[0]
        name = name.removeprefix("test_models/")
        t["model_id"] = name + "/" + t["target"] + "/" + t["model"].astype(str)
        if "asof" not in t:
            t["asof"] = None
        frames.append(t)
    if not frames:
        return pd.DataFrame(columns=["model_id", "target", "year", "state", "actual", "predicted", "asof"])
    out = pd.concat(frames, ignore_index=True)[["model_id", "target", "year", "state", "actual", "predicted", "asof"]]
    out["state"] = out["state"].map(state_code)
    return out


def state_history() -> pd.DataFrame:
    """NASS state history and season context from data/panel/state_year.csv (kernelag.state_panel)."""
    path = REPO / "data" / "panel" / "state_year.csv"
    if not path.exists():
        return pd.DataFrame()
    cols = ["state", "year", "silage", "grain", "planted", "milk_cows", "drought", "poor_condition", "rain_anom",
            "gdd_anom", "corn_price_sep", "loss_share"]
    t = pd.read_csv(path)
    t = t[[c for c in cols if c in t.columns]].copy()
    t["state"] = t["state"].map(state_code)
    return t


def catalog() -> dict:
    """Planned models (board/catalog.json): shown as 'awaiting results' until someone publishes them."""
    path = Path(__file__).with_name("catalog.json")
    return json.loads(path.read_text()) if path.exists() else {}


def collect() -> dict:
    """Read every source. A source that fails is reported, not fatal: models are still being built."""
    backtests, forecasts, models, problems = [], [], {}, []
    results = []
    for loader in LOADERS:
        try:
            results.append(loader())
        except Exception as error:  # noqa: BLE001 - one broken folder must not take the board down
            problems.append(f"{loader.__name__}: {type(error).__name__}: {error}")
    try:
        results.extend(load_plugins())
    except Exception as error:  # noqa: BLE001
        problems.append(f"plugins: {type(error).__name__}: {error}")

    for result in results:
        source, folder, bt, fc, notes = result[:5]
        feats = result[5] if len(result) > 5 else {}
        cards = result[6] if len(result) > 6 else {}
        who = owner(folder)
        rel = str(folder.relative_to(REPO))
        bt = bt.copy()
        bt["model_id"] = source + "/" + bt["target"] + "/" + bt["model"].astype(str)
        bt["source"] = source
        backtests.append(bt)
        names = set(zip(bt["target"], bt["model"].astype(str)))
        if fc is not None:
            fc = fc.copy()
            fc["model_id"] = source + "/" + fc["target"] + "/" + fc["model"].astype(str)
            forecasts.append(fc)
            names |= set(zip(fc["target"], fc["model"].astype(str)))
        for target, name in names:
            mid = f"{source}/{target}/{name}"
            card = cards.get(name, {})
            features = card.get("features") or feats.get(name) or KNOWN_FEATURES.get(f"{source}/{name}")
            models[mid] = {
                "model_id": mid, "model": name, "target": target, "source": source, "folder": rel,
                "owner": card.get("owner") or who,
                "signals": card.get("signals") or families(name, features),
                "method": card.get("method") or ("ridge regression" if f"{source}/{name}" in KNOWN_FEATURES
                                                  else method(name)),
                "features": features or [], "description": card.get("description") or notes.get(f"{target}/{name}", ""),
            }

    backtest = pd.concat(backtests, ignore_index=True) if backtests else pd.DataFrame()
    forecast = pd.concat(forecasts, ignore_index=True) if forecasts else pd.DataFrame()
    if not forecast.empty:
        forecast["state"] = forecast["state"].map(state_code)
        forecast = forecast[["model_id", "target", "state", "predicted", "lo80", "hi80"]]
    keep = ["model_id", "source", "model", "target", "year", "state_error_pct", "us_error_pct", "n_states", "metric",
            "asof"]
    backtest = backtest.reindex(columns=keep).sort_values(["model_id", "year"]) if not backtest.empty else backtest
    forecast_ids = set(forecast["model_id"]) if not forecast.empty else set()
    backtest_ids = set(backtest["model_id"]) if not backtest.empty else set()
    for mid, card in models.items():
        card["has_forecast"] = mid in forecast_ids
        card["has_backtest"] = mid in backtest_ids
    return {"backtest": backtest, "forecast": forecast, "models": models, "problems": problems}
