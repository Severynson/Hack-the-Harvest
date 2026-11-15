"""Post-hoc checks for sat_full/stress (written after README section 2 results were seen; nothing here is eligible).

    decomposition   why r(stress, shortfall) fell from sat_stress's 0.43: sample (draw 1 vs 2), reference years,
                    added years 2017-2019
    by_year         cross-state Pearson per year, headline CDL and P
    variants        peak only (-Z_peak) and peak + NDMI (mean of -Z_peak, -Z_ndmi; sat_stress's proposed next
                    pre-registration), all years and 2017-2019 only (years that hypothesis never saw)
    state_agree     per-state agreement of stress P vs CDL, 2018-2024
    y2026           2026 P stress next to the 2025/2026 Drought Monitor D2+ change

Run from the repo root (needs out/cache/field_components.parquet from stress.py):
    .venv/Scripts/python.exe test_models/variations/sat_full/stress/explore.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

import stress as S  # noqa: E402
from kernelag.context import drought  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402

OUT = S.OUT


def fields_table() -> pd.DataFrame:
    sample, _ = S.load_samples()
    comp = pd.read_parquet(S.CACHE)
    fields = sample.merge(comp, on=["stem", "cell", "field_id", "year"], how="left", validate="one_to_one")
    return S.attach_masks(fields)[0]


def cdl_index(fields: pd.DataFrame, years: list[int], ref_first: int, first_anom: int) -> pd.DataFrame:
    x = S.state_x(fields[fields["year"].isin(years)], "sel_cdl", "none")
    t = S.anomalies(x, x, years, ref_first, first_anom, "rms")
    t["state"] = t["state_fips"].map(S.STATES)
    return t


def corr_set(frame: pd.DataFrame, tgt: pd.DataFrame, x: str, label: str, years: list[int]) -> list[dict]:
    g = frame[frame["year"].isin(years)].merge(tgt, on=["state", "year"], how="left")
    return [{"version": label, "years": f"{years[0]}-{years[-1]}", **S.corr_row(g, x, y)}
            for y in S.TARGETS + ["shortfall_final", "resid_as3", "resid_sc"]]


def drought_change_all() -> pd.DataFrame:
    """sat_stress drought_change without its 2024 cap (Jun-Sep D2+ mean minus prior-years mean since 2000)."""
    usdm = pd.read_csv(next((data_dir() / "drought").glob("usdm_state_weekly_2000_2026.csv*")))
    d = drought(usdm, "nov").sort_values(["state", "year"])
    prior = d.groupby("state")["drought"].transform(lambda s: s.shift(1).expanding(min_periods=1).mean())
    return d.assign(d_drought=d["drought"] - prior)[["state", "year", "drought", "d_drought"]]


def main() -> None:
    fields = fields_table()
    tgt, _ = S.targets()
    index = pd.read_csv(OUT / "stress.csv", dtype={"state_fips": str})
    head = index[(index["weight"] == "none") & (index["scale"] == "rms")].copy()
    for comp, sign in S.COMPONENTS.items():
        head[f"signed_z_{comp}"] = sign * head[f"z_{comp}"]
    head["peak_only"] = -head["z_peak"]
    head["peak_ndmi"] = (-head["z_peak"] - head["z_ndmi"]) / 2
    y2024 = list(range(2020, 2025))

    # 1. decomposition
    rows = []
    sub = fields[fields["year"].between(2019, 2024)]
    rows += corr_set(cdl_index(sub[sub["draw"] == 1], list(range(2019, 2025)), 2019, 2020), tgt, "stress",
                     "a draw 1, ref from 2019 (= sat_stress)", y2024)
    rows += corr_set(cdl_index(sub[sub["draw"] == 2], list(range(2019, 2025)), 2019, 2020), tgt, "stress",
                     "b draw 2 only, ref from 2019", y2024)
    rows += corr_set(cdl_index(sub, list(range(2019, 2025)), 2019, 2020), tgt, "stress",
                     "c draws 1+2, ref from 2019", y2024)
    cdl = head[head["mask"] == "CDL"]
    rows += corr_set(cdl, tgt, "stress", "d headline CDL (ref from 2016)", y2024)
    rows += corr_set(cdl, tgt, "stress", "e headline CDL (ref from 2016)", list(range(2017, 2020)))
    rows += corr_set(cdl, tgt, "stress", "f headline CDL (ref from 2016)", list(range(2017, 2025)))
    pd.DataFrame(rows).to_csv(OUT / "posthoc_decomposition.csv", index=False, float_format="%.4f")

    # 2. per-year cross-state correlations
    rows = []
    for mask in ("CDL", "P"):
        g = head[head["mask"] == mask].merge(tgt, on=["state", "year"], how="left")
        for year in range(2017, 2025):
            gy = g[g["year"] == year]
            for y in S.TARGETS:
                ok = gy[["stress", y]].dropna()
                r, p = stats.pearsonr(ok["stress"], ok[y]) if len(ok) >= 5 else (np.nan, np.nan)
                rows.append({"mask": mask, "year": year, "y": y, "n": len(ok), "pearson": r, "p": p,
                             "mean_stress": float(gy["stress"].mean())})
    pd.DataFrame(rows).to_csv(OUT / "posthoc_by_year.csv", index=False, float_format="%.4f")

    # 3. index variants
    rows = []
    for mask, windows in (("CDL", ([2017, 2018, 2019], list(range(2017, 2025)), y2024)),
                          ("P", ([2018, 2019], list(range(2018, 2025)), y2024))):
        g = head[head["mask"] == mask]
        for x in ("stress", "peak_only", "peak_ndmi"):
            for years in windows:
                rows += [{"mask": mask, **r} for r in corr_set(g, tgt, x, x, years)]
    pd.DataFrame(rows).to_csv(OUT / "posthoc_variants.csv", index=False, float_format="%.4f")

    # 4. per-state agreement P vs CDL
    rows = []
    w = head[head["year"].between(2018, 2024)].pivot_table(index=["state", "year"], columns="mask",
                                                          values="stress").reset_index()
    for state, g in w.groupby("state"):
        ok = g[["P", "CDL"]].dropna()
        rows.append({"state": state, "n": len(ok), "pearson": stats.pearsonr(ok["P"], ok["CDL"])[0],
                     "mean_diff_P_minus_CDL": float((ok["P"] - ok["CDL"]).mean()),
                     "mean_abs_diff": float((ok["P"] - ok["CDL"]).abs().mean())})
    pd.DataFrame(rows).sort_values("mean_abs_diff").to_csv(OUT / "posthoc_state_agreement.csv", index=False,
                                                           float_format="%.4f")

    # 5. 2026 (real-time) next to the Drought Monitor
    dc = drought_change_all()
    y26 = head[head["year"].isin([2025, 2026]) & head["mask"].isin(["P", "P_cdlref", "CDL"])]
    y26 = y26.pivot_table(index=["state", "year"], columns="mask", values="stress").reset_index()
    y26 = y26.merge(dc, on=["state", "year"], how="left")
    y26.to_csv(OUT / "posthoc_2025_2026.csv", index=False, float_format="%.4f")
    corr26 = []
    for year in (2025, 2026):
        g = y26[y26["year"] == year]
        for mask in ("P", "P_cdlref", "CDL"):
            ok = g[[mask, "d_drought"]].dropna() if mask in g else pd.DataFrame()
            if len(ok) >= 5:
                r, p = stats.pearsonr(ok[mask], ok["d_drought"])
                corr26.append({"year": year, "mask": mask, "n": len(ok), "pearson_vs_d_drought": r, "p": p})
    pd.DataFrame(corr26).to_csv(OUT / "posthoc_2025_2026_corr.csv", index=False, float_format="%.4f")

    pd.set_option("display.width", 220)
    for name in ("decomposition", "by_year", "variants", "state_agreement", "2025_2026", "2025_2026_corr"):
        t = pd.read_csv(OUT / f"posthoc_{name}.csv")
        print(f"--- {name}")
        cols = [c for c in t.columns if c not in ("spearman_p", "within_year_p", "n_years")]
        print(t[cols].round(3).to_string(max_rows=200))


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()
