"""
Caveman field calls rolled up to state acres, scored against NASS's 2025 final (the organizers' target).

Inputs (main checkout's data/, pulled by cc-daniel / cc-varun):
  data/samples/corn_<fips>.parquet          sampled cornfields per state and year (10 areas per state)
  data/s2_series/corn_<fips>/*_<year>.csv   their Sentinel-2 series (May-Nov)
  data/Quickstats Data/*_state_2000_2026.csv NASS planted (June), grain and silage harvested acres

Rule: the basic caveman drop rule only (silage if NDVI falls 80%->20% of its range in < CUT days),
CUT = 17.5 days, learned on Quebec. No 2025 labels are used anywhere.

Estimators (silage; grain = harvested total - silage):
  direct  share_2025 x harvested total, where total = NASS June 2025 planted x (2024 harvested / 2024 planted)
  change  NASS 2024 final silage x (share_2025 / share_2024), same sample areas both years
  baseline  NASS 2024 final silage (same as last year)

Run: uv run state_rollup.py
"""

import contextlib
import glob
import io
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

with contextlib.redirect_stdout(io.StringIO()):
    import train as T

DATA = Path(__file__).resolve().parents[2] / "hack-the-harvest" / "data"
QS = DATA / "Quickstats Data"
CUT = 17.5
YEARS = (2024, 2025)


def field_calls(path):
    """drop_days per field for one area-year file."""
    d = pd.read_csv(path, dtype={"field_id": str}, parse_dates=["date"])
    d["doy"] = d["date"].dt.dayofyear
    rows = []
    for fid, g in d.groupby("field_id"):
        f = T.season_features(g)
        rows.append({"field_id": fid, "drop_days": f.get("drop_days", np.nan)})
    out = pd.DataFrame(rows)
    name = Path(path).stem  # <cell>_<year>
    out["cell"], out["year"] = name.rsplit("_", 1)[0], int(name.rsplit("_", 1)[1])
    return out


def nass(file, period="YEAR"):
    q = pd.read_csv(QS / file)
    q = q[(q["reference_period_desc"] == period) & (q["agg_level_desc"] == "STATE")]
    q["Value"] = pd.to_numeric(q["Value"].astype(str).str.replace(",", ""), errors="coerce")
    q["state_fips"] = q["state_fips_code"].astype(int).astype(str).str.zfill(2)
    return q.set_index(["state_fips", "year"])["Value"]


def main():
    states = sorted(Path(p).name.split("_")[1] for p in glob.glob(str(DATA / "s2_series" / "corn_??")))
    files = [f for s in states for y in YEARS for f in glob.glob(str(DATA / "s2_series" / f"corn_{s}" / f"*_{y}.csv"))]
    print(f"{len(states)} states, {len(files)} area-year files", flush=True)
    with ProcessPoolExecutor() as ex:
        calls = pd.concat(ex.map(field_calls, files, chunksize=4), ignore_index=True)

    shares = []
    for s in states:
        samp = pd.read_parquet(DATA / "samples" / f"corn_{s}.parquet", columns=["field_id", "year", "cell", "acres"])
        samp["field_id"] = samp["field_id"].astype(str)
        c = calls.merge(samp, on=["field_id", "year", "cell"], how="inner")
        c["silage"] = (c["drop_days"] < CUT).astype(float)  # no measurable drop -> grain
        cell = c.groupby(["year", "cell"]).apply(lambda g: np.average(g["silage"], weights=g["acres"]), include_groups=False)
        for y, v in cell.groupby(level=0):
            shares.append({"state_fips": s, "year": y, "share": v.mean(), "areas": len(v), "fields": int((c["year"] == y).sum())})
    sh = pd.DataFrame(shares).pivot(index="state_fips", columns="year", values="share")

    planted_jun = nass("corn_planted_acres_state_2000_2026.csv", "YEAR - JUN ACREAGE")
    planted = nass("corn_planted_acres_state_2000_2026.csv")
    grain = nass("corn_grain_harvested_acres_state_2000_2026.csv")
    silage = nass("corn_silage_harvested_acres_state_2000_2026.csv")

    rows = []
    for s in sh.index:
        g24, s24 = grain.get((s, 2024), np.nan), silage.get((s, 2024), np.nan)
        total = planted_jun.get((s, 2025), np.nan) * (np.nan_to_num(g24) + s24) / planted.get((s, 2024), np.nan)
        direct = sh.loc[s, 2025] * total
        change = s24 * sh.loc[s, 2025] / sh.loc[s, 2024] if sh.loc[s, 2024] > 0 else np.nan
        rows.append({"state_fips": s, "share_2024": sh.loc[s, 2024], "share_2025": sh.loc[s, 2025],
                     "silage_true": silage.get((s, 2025), np.nan), "grain_true": grain.get((s, 2025), np.nan),
                     "silage_last_year": s24, "grain_last_year": g24,
                     "silage_direct": direct, "grain_direct": total - direct,
                     "silage_change": change, "grain_change": total - change, "harvested_total_est": total})
    r = pd.DataFrame(rows)
    names = pd.read_csv(QS / "corn_silage_harvested_acres_state_2000_2026.csv", usecols=["state_fips_code", "state_name"]).drop_duplicates()
    names["state_fips"] = names["state_fips_code"].astype(int).astype(str).str.zfill(2)
    r = r.merge(names[["state_fips", "state_name"]], on="state_fips")
    r.to_csv(Path(__file__).resolve().parent / "figures" / "state_rollup_2025.csv", index=False)

    def score(kind, crop):
        t = r[f"{crop}_true"]
        p = r[f"{crop}_{kind}"]
        ok = t.notna() & p.notna()
        wape = (p[ok] - t[ok]).abs().sum() / t[ok].sum()
        tot = (p[ok].sum() - t[ok].sum()) / t[ok].sum()
        return wape, tot, int(ok.sum())

    pd.set_option("display.width", 220)
    show = r[["state_name", "share_2024", "share_2025", "silage_true", "silage_last_year", "silage_direct", "silage_change"]].copy()
    for c in ["silage_true", "silage_last_year", "silage_direct", "silage_change"]:
        show[c] = (show[c] / 1000).round(0)
    show[["share_2024", "share_2025"]] = show[["share_2024", "share_2025"]].round(3)
    print("\nSilage acres, thousands (true = NASS 2025 final):")
    print(show.sort_values("silage_true", ascending=False).to_string(index=False))
    print("\n15-state scores against NASS 2025 final (state error = sum |error| / sum true; total = error of the 15-state sum):")
    for crop in ("silage", "grain"):
        for kind, label in [("last_year", "same as last year (NASS 2024)"), ("direct", "caveman share x harvested total"), ("change", "NASS 2024 x caveman change")]:
            w, t, n = score(kind, crop)
            print(f"  {crop:6s} {label:34s} state error {w:6.1%}   total {t:+6.1%}   states {n}")


if __name__ == "__main__":
    main()
