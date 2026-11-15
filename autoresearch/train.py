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

MIN_VALID_FRAC = 0.4       # scene kept for a field if >= this share of its pixels are clear
SMOOTH_DAYS = 15           # centred rolling-mean window on the daily-interpolated NDVI
SPRING_WINDOW = (90, 170)  # DOY range to look for the pre-corn NDVI low (after cover crop / bare soil)
GREENUP_FRAC = 0.5         # green-up = first day NDVI regains this share of (peak - spring low)
HARVEST_FRAC = 0.5         # harvest = first day after peak NDVI falls below low + this share of amplitude
PEAK_WINDOW = (170, 260)   # corn peak is searched only in summer, so a spring cover crop peak is ignored
LATE_WINDOW = (300, 355)   # Nov-Dec: a cover crop sown after an early silage cut is green by now
SECOND_FEATURE = "late_ndvi_neg"  # OR-rule: silage if FEATURE < t1 or SECOND_FEATURE < t2
DROP_HI, DROP_LO = 0.8, 0.2  # drop duration = days from (low + 0.8 amp) to (low + 0.2 amp) after the peak
FEATURE = "drop_days"      # which feature the single threshold rule uses

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
    late = g[(g["valid_frac"] >= MIN_VALID_FRAC) & g["doy"].between(*LATE_WINDOW)]["ndvi"]
    feats = _season_features(g)
    feats["late_ndvi_neg"] = -float(late.median()) if len(late) else np.nan  # negated: rules are "silage if x < thr"
    return feats


def _season_features(g: pd.DataFrame) -> dict:
    s = daily_ndvi(g)
    out = {"greenup_doy": np.nan, "harvest_doy": np.nan, "season_len": np.nan, "drop_days": np.nan}
    if s.empty:
        return out
    summer = s.loc[PEAK_WINDOW[0] : PEAK_WINDOW[1]]
    if summer.empty:
        return out
    peak_doy = int(summer.idxmax())
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
    hi = after[after <= low + DROP_HI * amp]
    lo = after[after <= low + DROP_LO * amp]
    if not hi.empty and not lo.empty:
        out["drop_days"] = int(lo.index[0] - hi.index[0])
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
# Model: OR of two thresholds, fitted greedily on training labels
# ---------------------------------------------------------------------------


def f1(y, p):
    tp = ((y == 1) & (p == 1)).sum()
    fp = ((y == 0) & (p == 1)).sum()
    fn = ((y == 1) & (p == 0)).sum()
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def fit_threshold(x, y, already=None):
    """Best cut: silage if x < thr (OR-ed with `already`). Ties broken by the middle of the best range.
    Returns -inf (rule off) when no cut beats `already` alone."""
    x, y = np.asarray(x, float), np.asarray(y, int)
    already = np.zeros(len(y), bool) if already is None else already
    xf = np.where(np.isfinite(x), x, np.inf)
    cands = np.unique(xf[np.isfinite(xf)])
    cands = (cands[:-1] + cands[1:]) / 2 if len(cands) > 1 else cands
    cands = np.concatenate([[-np.inf], cands])
    scores = np.array([f1(y, (already | (xf < c)).astype(int)) for c in cands])
    best = np.flatnonzero(scores == scores.max())
    return float(np.median(cands[best])) if 0 not in best else -np.inf


def fit_predict(ts_tr, lab_tr, ts_te, keys_te):
    ftr = featurize(ts_tr, lab_tr).merge(lab_tr[["OBJECTID", "year", "y"]], on=["OBJECTID", "year"])
    y = ftr["y"].to_numpy()
    xa, xb = ftr[FEATURE].to_numpy(float), ftr[SECOND_FEATURE].to_numpy(float)
    t1 = fit_threshold(xa, y)
    t2 = fit_threshold(xb, y, already=np.nan_to_num(xa, nan=np.inf) < t1)
    fte = featurize(ts_te, keys_te)
    a = np.nan_to_num(fte[FEATURE].to_numpy(float), nan=np.inf)  # missing -> grain (majority class)
    b = np.nan_to_num(fte[SECOND_FEATURE].to_numpy(float), nan=np.inf)
    return ((a < t1) | (b < t2)).astype(int)


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
