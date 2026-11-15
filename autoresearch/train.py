"""
Caveman model: silage vs grain from growing-season length.

Idea (Severyn, test_models/danielModel/README.md):
  - Green-up date (proxy for planting) = when NDVI starts its steady rise after the spring low.
  - Harvest date = when NDVI collapses after the summer peak.
  - Season length = harvest - green-up. Silage is cut green, weeks before grain, so its season is shorter.
  - Threshold on season length is learned from the training years' labels only.

This is the only file the autoresearch loop edits. Run: uv run train.py
"""

import time

import numpy as np
import pandas as pd

from prepare import evaluate

t0 = time.time()

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------

MIN_VALID_FRAC = 0.6       # scene kept for a field if >= this share of its pixels are clear
SMOOTH_DAYS = 15           # centred rolling-mean window on the daily-interpolated NDVI
SPRING_WINDOW = (90, 170)  # DOY range to look for the pre-corn NDVI low (after cover crop / bare soil)
GREENUP_FRAC = 0.5         # green-up = first day NDVI regains this share of (peak - spring low)
HARVEST_FRAC = 0.5         # harvest = first day after peak NDVI falls below low + this share of amplitude

# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


def daily_ndvi(g: pd.DataFrame) -> pd.Series:
    g = g[g["valid_frac"] >= MIN_VALID_FRAC].dropna(subset=["ndvi"])
    if len(g) < 5:
        return pd.Series(dtype=float)
    s = g.groupby("doy")["ndvi"].median()
    days = np.arange(s.index.min(), s.index.max() + 1)
    s = s.reindex(days).interpolate("linear")
    return s.rolling(SMOOTH_DAYS, center=True, min_periods=1).mean()


def season_features(g: pd.DataFrame) -> dict:
    s = daily_ndvi(g)
    out = {"greenup_doy": np.nan, "harvest_doy": np.nan, "season_len": np.nan}
    if s.empty:
        return out
    peak_doy = int(s.idxmax())
    spring = s.loc[SPRING_WINDOW[0] : min(SPRING_WINDOW[1], peak_doy)]
    if spring.empty:
        return out
    low_doy = int(spring.idxmin())
    low, peak = s.loc[low_doy], s.loc[peak_doy]
    amp = peak - low
    rising = s.loc[low_doy:peak_doy]
    up = rising[rising >= low + GREENUP_FRAC * amp]
    after = s.loc[peak_doy:]
    down = after[after <= low + HARVEST_FRAC * amp]
    if up.empty or down.empty:
        return out
    out["greenup_doy"] = int(up.index[0])
    out["harvest_doy"] = int(down.index[0])
    out["season_len"] = out["harvest_doy"] - out["greenup_doy"]
    return out


def featurize(ts: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = dict(tuple(ts.groupby(["OBJECTID", "year"])))
    for oid, yr in zip(keys["OBJECTID"], keys["year"]):
        g = groups.get((oid, yr))
        f = season_features(g) if g is not None else {}
        rows.append({"OBJECTID": oid, "year": yr, **f})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Model: one threshold on season length, fitted on training labels
# ---------------------------------------------------------------------------


def f1(y, p):
    tp = ((y == 1) & (p == 1)).sum()
    fp = ((y == 0) & (p == 1)).sum()
    fn = ((y == 1) & (p == 0)).sum()
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def fit_threshold(x, y):
    """Best cut: silage if x < thr. Ties broken by the middle of the best range."""
    x, y = np.asarray(x, float), np.asarray(y, int)
    ok = np.isfinite(x)
    cands = np.unique(x[ok])
    cands = (cands[:-1] + cands[1:]) / 2 if len(cands) > 1 else cands
    scores = np.array([f1(y[ok], (x[ok] < c).astype(int)) for c in cands])
    best = np.flatnonzero(scores == scores.max())
    return float(np.median(cands[best]))


def fit_predict(ts_tr, lab_tr, ts_te, keys_te):
    ftr = featurize(ts_tr, lab_tr).merge(lab_tr[["OBJECTID", "year", "y"]], on=["OBJECTID", "year"])
    thr = fit_threshold(ftr["season_len"], ftr["y"])
    fte = featurize(ts_te, keys_te)
    x = fte["season_len"].to_numpy(float)
    return np.where(np.isfinite(x), x < thr, 0).astype(int)  # missing -> grain (majority class)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

overall, per_year, oof = evaluate(fit_predict)
print("---")
print(f"val_f1:           {overall['silage_f1']:.6f}")
print(f"precision:        {overall['silage_precision']:.4f}")
print(f"recall:           {overall['silage_recall']:.4f}")
print(f"balanced_acc:     {overall['balanced_acc']:.4f}")
print(f"accuracy:         {overall['accuracy']:.4f}")
print(f"confusion:        tp={overall['tp']} fp={overall['fp']} fn={overall['fn']} tn={overall['tn']}")
print("per_year_f1:      " + " ".join(f"{y}={v:.3f}" for y, v in per_year.items()))
print(f"total_seconds:    {time.time() - t0:.1f}")
