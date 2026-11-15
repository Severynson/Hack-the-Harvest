"""
Cross-region scoreboard for train.py (fixed; experiments edit train.py only).

Four silage-F1 scores, each on one dataset, never mixed:
  barc_loyo  BARC, leave one year out (the frozen prepare.evaluate)
  q2b        fit on all Quebec parcels, test on the 44 BARC field-years
  b2q        fit on all 44 BARC field-years, test on the 801 Quebec parcels
  q_loco     Quebec, leave one 0.1-degree cell out (spatial hold-out)
score = mean of the four (higher is better).

train.py must expose fit(ts, lab) -> params and predict(ts, keys, params) -> 0/1 array.
keys/lab carry OBJECTID, year and a `group` column (region-year); rules may compare a field
with the other fields of its group, never with their labels.

Run: uv run multi_eval.py
"""

import contextlib
import io
import time

import numpy as np
import pandas as pd

import prepare as P

with contextlib.redirect_stdout(io.StringIO()):
    import quebec_check as Q
    import train as T

t0 = time.time()


def load_quebec():
    par = Q.cell_parcels(Q.DEFAULT_LABELS)
    ts = pd.concat([pd.read_parquet(P.CACHE_DIR / "quebec" / f"{c}_{Q.YEAR}.parquet") for c in Q.CELLS], ignore_index=True)
    lab = pd.DataFrame(par[["OBJECTID", "year", "y", "cell"]]).rename(columns={"cell": "group"})
    return ts, lab.reset_index(drop=True)


def load_barc():
    ts, lab = P.load_data()
    lab = lab[["OBJECTID", "year", "y"]].copy()
    lab["group"] = "barc_" + lab["year"].astype(str)
    return ts, lab


def run(ts_tr, lab_tr, ts_te, lab_te):
    params = T.fit(ts_tr, lab_tr.reset_index(drop=True))
    keys = lab_te[["OBJECTID", "year", "group"]].reset_index(drop=True)
    p = np.asarray(T.predict(ts_te, keys, params), dtype=int)
    return P._scores(lab_te["y"].to_numpy(), p)


def main():
    bts, blab = load_barc()
    qts, qlab = load_quebec()
    res = {}
    overall, _, _ = P.evaluate(T.fit_predict)
    res["barc_loyo"] = overall
    res["q2b"] = run(qts, qlab, bts, blab)
    res["b2q"] = run(bts, blab, qts, qlab)
    oof = []
    for c in sorted(qlab["group"].unique()):
        tr, te = qlab[qlab["group"] != c], qlab[qlab["group"] == c]
        params = T.fit(qts[qts["OBJECTID"].isin(tr["OBJECTID"])], tr.reset_index(drop=True))
        k = te[["OBJECTID", "year", "group"]].reset_index(drop=True)
        oof.append(te.assign(pred=np.asarray(T.predict(qts[qts["OBJECTID"].isin(te["OBJECTID"])], k, params), dtype=int)))
    oof = pd.concat(oof)
    res["q_loco"] = P._scores(oof["y"].to_numpy(), oof["pred"].to_numpy())

    print("---")
    for k, s in res.items():
        print(f"{k:10s} f1 {s['silage_f1']:.4f}  acc {s['accuracy']:.4f}  P {s['silage_precision']:.3f}  R {s['silage_recall']:.3f}  "
              f"tp={s['tp']} fp={s['fp']} fn={s['fn']} tn={s['tn']}")
    score = float(np.mean([s["silage_f1"] for s in res.values()]))
    print(f"multi_score:      {score:.6f}")
    print(f"total_seconds:    {time.time() - t0:.1f}")


if __name__ == "__main__":
    main()
