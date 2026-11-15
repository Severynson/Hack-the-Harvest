"""
Caveman model: silage vs grain from how the corn leaves the field.

Started from Severyn's idea (test_models/danielModel/README.md): season length = harvest - green-up.
Ablations showed season length is weak (grain senesces at the same date silage is cut). Two timing
rules survived:
  1. Drop speed: silage is chopped green, so NDVI collapses within ~2 weeks; grain dries down over 3-4.
  2. Re-greening: after an early silage cut a cover crop is sown and is green by Nov-Dec.
A field-year is silage if it drops fast OR re-greens. Both thresholds are learned from training years.

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
LATE_WINDOW = (300, 355)   # Nov-Dec: a cover crop sown after an early silage cut is green by now
DROP_HI, DROP_LO = 0.8, 0.2  # drop duration = days from (low + 0.8 amp) to (low + 0.2 amp) after the peak
RULES = ["drop_days", "late_rel_neg"]
MIN_RULE_PRECISION = 0.7   # a secondary rule may only use cut-offs where >= 70% of the fields it adds are silage  # silage if ANY feature < its cut-off; cut-offs fitted greedily in this order

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
    out = {"drop_days": np.nan, "late_ndvi_neg": np.nan}
    late = g[(g["valid_frac"] >= MIN_VALID_FRAC) & g["doy"].between(*LATE_WINDOW)]["ndvi"]
    if len(late):
        out["late_ndvi_neg"] = -float(late.median())  # negated: rules are "silage if x < thr"
    s = daily_ndvi(g)
    if s.empty:
        return out
    peak_doy = int(s.idxmax())
    spring = s.loc[SPRING_WINDOW[0] : min(SPRING_WINDOW[1], peak_doy)]
    if spring.empty:
        return out
    low, peak = spring.min(), s.loc[peak_doy]
    amp = peak - low
    after = s.loc[peak_doy:]
    hi = after[after <= low + DROP_HI * amp]
    lo = after[after <= low + DROP_LO * amp]
    if not hi.empty and not lo.empty:
        out["drop_days"] = int(lo.index[0] - hi.index[0])
    return out


def featurize(ts: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    """One row per key. `group` (region-year) defaults to the year; relative features compare a field
    with the other fields of its group (no labels involved)."""
    rows = []
    groups = dict(tuple(ts.groupby(["OBJECTID", "year"])))
    grp = keys["group"] if "group" in keys else keys["year"].astype(str)
    for oid, yr, gr in zip(keys["OBJECTID"], keys["year"], grp):
        g = groups.get((oid, yr))
        f = season_features(g) if g is not None else {}
        rows.append({"OBJECTID": oid, "year": yr, "group": gr, **f})
    out = pd.DataFrame(rows)
    # winter green relative to the region-year: snow makes every field dull, cover crops stand out
    out["late_rel_neg"] = out["late_ndvi_neg"] - out.groupby("group")["late_ndvi_neg"].transform("median")
    return out


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
    def score(c):
        new = ~already & (xf < c)
        if already.any() and new.any() and y[new].mean() < MIN_RULE_PRECISION:
            return -1.0  # this cut adds mostly grain: not allowed
        return f1(y, (already | (xf < c)).astype(int))

    scores = np.array([score(c) for c in cands])
    best = np.flatnonzero(scores == scores.max())
    return float(np.median(cands[best])) if 0 not in best else -np.inf


def fit(ts, lab):
    f = featurize(ts, lab).merge(lab[["OBJECTID", "year", "y"]], on=["OBJECTID", "year"])
    y = f["y"].to_numpy()
    fired = np.zeros(len(y), bool)
    cuts = {}
    for r in RULES:
        x = np.nan_to_num(f[r].to_numpy(float), nan=np.inf)  # missing -> rule does not fire
        cuts[r] = fit_threshold(x, y, already=fired)
        fired |= x < cuts[r]
    return cuts


def predict(ts, keys, cuts):
    f = featurize(ts, keys)
    fired = np.zeros(len(f), bool)
    for r, c in cuts.items():
        fired |= np.nan_to_num(f[r].to_numpy(float), nan=np.inf) < c
    return fired.astype(int)


def fit_predict(ts_tr, lab_tr, ts_te, keys_te):
    return predict(ts_te, keys_te, fit(ts_tr, lab_tr))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
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
