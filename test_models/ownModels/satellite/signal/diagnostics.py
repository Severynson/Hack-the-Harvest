"""Diagnostics of the satellite silage-like share against NASS final acres (no model selection).

For each forecast date (15 Nov, 15 Oct, 15 Sep) and both share versions (probability-weighted
``sat_share`` and called ``sat_share_calls``):

    changes    per state and year 2020-2025, the change in log satellite share (same areas both years)
               against the change in log NASS final silage share of planted (silage / planted) and
               against the change in log NASS final silage acres:
                 - pooled Spearman over state-years after removing each year's cross-state median
                   (removes a common year effect, e.g. a classifier shift that hits every state alike),
                   with a 90% cluster bootstrap over states; also without removing year medians, and on
                   2020-2024 only (2025 is information only, never used to select anything)
                 - per state: how many years the signs agree (raw and after removing year medians)
    noise      per state: the jackknife SE of the share and of its year-to-year change (areas left out of
               both years at once) against the typical year-to-year change of the share
    explain    what the satellite change and NASS's change move with (drought, rain, heat, final grain
               yield, cut day, assessability), year medians removed
    level      satellite share against NASS silage share of planted across states (expected biased: the
               balanced-weight field model calls a fixed fraction of grain fields silage)

Inputs: out/state_satellite_asof_*.csv and out/state_satellite_changes_asof_*.csv (``signal.py``),
data/nass/corn_acres_state.csv (final acres, exactly as kernelag.state_model uses them).

Outputs: out/diagnostics_changes.csv, out/diagnostics_by_state_asof_{nov,oct,sep}.csv,
out/diagnostics_level.csv, out/diagnostics_level_by_state.csv, out/diagnostics_explain.csv,
out/diagnostics_summary.json

Run from the repo root: .venv/Scripts/python.exe -m test_models.ownModels.satellite.signal.diagnostics
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
# signal.py in this folder shares its name with the standard-library module; keep the folder off the path.
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import pearsonr, rankdata, spearmanr  # noqa: E402

from kernelag.paths import data_dir  # noqa: E402

OUT = HERE / "out"
ASOFS = ("nov", "oct", "sep")
CHANGE_YEARS = list(range(2020, 2026))
PRE_SCORING_YEARS = list(range(2020, 2025))
LEVEL_YEARS = list(range(2019, 2025))      # 2025 kept out of the level summary too (information only)
DRAWS = 2000
SEED = 0
SIGNALS = {"sat_share": "", "sat_share_calls": "_calls"}


def nass_truth() -> pd.DataFrame:
    """Final silage, grain and planted acres per state and year, with silage share of planted and changes."""
    acres = pd.read_csv(data_dir() / "nass" / "corn_acres_state.csv")
    final = acres[acres["period"] == "final"].pivot_table(index=["state", "year"], columns="series",
                                                          values="acres").reset_index()
    final["nass_share"] = final["silage"] / final["planted"]
    final = final.sort_values(["state", "year"])
    last = final[["state", "year", "silage", "nass_share"]].assign(year=final["year"] + 1)
    final = final.merge(last, on=["state", "year"], how="left", suffixes=("", "_last"))
    final["d_log_nass_share"] = np.log(final["nass_share"] / final["nass_share_last"])
    final["d_log_nass_silage"] = np.log(final["silage"] / final["silage_last"])
    return final


def demean_by_year(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        out[column] = frame[column] - frame.groupby("year")[column].transform("median")
    return out


def spearman_with_bootstrap(frame: pd.DataFrame, x: str, y: str, demean: bool) -> dict:
    """Pooled Spearman of x and y; 90% interval from resampling whole states (year medians re-removed)."""
    frame = frame.dropna(subset=[x, y]).reset_index(drop=True)
    data = demean_by_year(frame, [x, y]) if demean else frame
    rho, p = spearmanr(data[x], data[y])
    states = frame["state"].unique()
    xs, ys = frame[x].to_numpy(float), frame[y].to_numpy(float)
    year_codes, _ = pd.factorize(frame["year"])
    rows_of = [np.flatnonzero(frame["state"].to_numpy() == s) for s in states]
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(DRAWS):
        index = np.concatenate([rows_of[k] for k in rng.integers(0, len(states), size=len(states))])
        bx, by, codes = xs[index].copy(), ys[index].copy(), year_codes[index]
        if demean:   # year medians re-removed inside every draw, as in the point estimate
            for code in np.unique(codes):
                rows = codes == code
                bx[rows] -= np.median(bx[rows])
                by[rows] -= np.median(by[rows])
        if np.ptp(bx) > 0 and np.ptp(by) > 0:
            draws.append(np.corrcoef(rankdata(bx), rankdata(by))[0, 1])
    lo, hi = np.quantile(draws, [0.05, 0.95]) if draws else (np.nan, np.nan)
    return {"n": len(frame), "states": len(states), "spearman": round(float(rho), 3), "p_value": round(float(p), 4),
            "ci90_lo": round(float(lo), 3), "ci90_hi": round(float(hi), 3)}


def change_table(asof: str, truth: pd.DataFrame) -> pd.DataFrame:
    changes = pd.read_csv(OUT / f"state_satellite_changes_asof_{asof}.csv", dtype={"state_fips": str})
    levels = pd.read_csv(OUT / f"state_satellite_asof_{asof}.csv", dtype={"state_fips": str})
    levels = levels.sort_values(["state", "year"])
    levels["d_assessable_share"] = levels.groupby("state")["assessable_share"].diff()
    levels.loc[levels.groupby("state")["year"].diff() != 1, "d_assessable_share"] = np.nan
    table = changes.merge(levels[["state", "year", "d_assessable_share"]], on=["state", "year"], how="left")
    return table.merge(truth[["state", "year", "d_log_nass_share", "d_log_nass_silage"]], on=["state", "year"],
                       how="left")


def pooled_rows(asof: str, table: pd.DataFrame) -> list[dict]:
    rows = []
    for signal, tag in SIGNALS.items():
        for change in ["d_log_share", "d_logit_share"]:
            x = f"{change}{tag}"
            for target in ["d_log_nass_share", "d_log_nass_silage", "d_assessable_share"]:
                if target == "d_assessable_share" and change != "d_log_share":
                    continue
                for years_name, years in [("2020-2025", CHANGE_YEARS), ("2020-2024", PRE_SCORING_YEARS)]:
                    for demean in [True, False]:
                        part = table[table["year"].isin(years)]
                        rows.append({"asof": asof, "signal": signal, "change": change, "target": target,
                                     "years": years_name, "year_medians_removed": demean,
                                     **spearman_with_bootstrap(part, x, target, demean)})
    return rows


def by_state(asof: str, table: pd.DataFrame, levels: pd.DataFrame, truth: pd.DataFrame,
             level_slope: float) -> pd.DataFrame:
    """Per state: sign agreement, noise and the change the level fit says the satellite share could show.

    If sat_share = a + b * nass_share across states (``level_rows``), a NASS change of d log(nass_share) moves
    the satellite share by about b * nass_share / sat_share * d log(nass_share) in log terms: the grain fields
    the model calls silage (intercept a) dilute the change. ``expected_snr`` divides that expected
    movement (with NASS's own year-to-year spread) by the satellite change's sampling SE.
    """
    part = table[table["year"].isin(CHANGE_YEARS)].dropna(subset=["d_log_share", "d_log_nass_share"])
    demeaned = demean_by_year(part, ["d_log_share", "d_log_share_calls", "d_log_nass_share", "d_log_nass_silage"])
    rows = []
    for state, rows_state in part.groupby("state"):
        d = demeaned.loc[rows_state.index]
        lv = levels[levels["state"] == state]
        tr = truth[(truth["state"] == state) & truth["year"].isin(CHANGE_YEARS)]

        def agree(frame: pd.DataFrame, x: str, y: str) -> int:
            return int((np.sign(frame[x]) == np.sign(frame[y])).sum())

        rms_se_d = float(np.sqrt((rows_state["se_d_share"] ** 2).mean()))
        rms_se_dlog = float(np.sqrt((rows_state["se_d_log_share"] ** 2).mean()))
        sd_d = float(rows_state["d_share"].std(ddof=1))
        sd_dlog = float(rows_state["d_log_share"].std(ddof=1))
        rows.append({
            "state": state, "years": len(rows_state),
            "sign_agree_share_raw": agree(rows_state, "d_log_share", "d_log_nass_share"),
            "sign_agree_share_demeaned": agree(d, "d_log_share", "d_log_nass_share"),
            "sign_agree_silage_raw": agree(rows_state, "d_log_share", "d_log_nass_silage"),
            "sign_agree_silage_demeaned": agree(d, "d_log_share", "d_log_nass_silage"),
            "sign_agree_calls_share_demeaned": agree(d, "d_log_share_calls", "d_log_nass_share"),
            "spearman_years_share": round(float(spearmanr(rows_state["d_log_share"],
                                                          rows_state["d_log_nass_share"])[0]), 3),
            "median_share_se": round(float(lv["share_se"].median()), 4),
            "rms_se_d_share": round(rms_se_d, 4),
            "sd_d_share": round(sd_d, 4),
            "median_abs_d_share": round(float(rows_state["d_share"].abs().median()), 4),
            "snr_d_share": round(sd_d / rms_se_d, 2) if rms_se_d > 0 else np.nan,
            "rms_se_d_log_share": round(rms_se_dlog, 4),
            "sd_d_log_share": round(sd_dlog, 4),
            "sd_d_log_nass_share": round(float(tr["d_log_nass_share"].std(ddof=1)), 4),
            "sd_d_log_nass_silage": round(float(tr["d_log_nass_silage"].std(ddof=1)), 4),
            "se_d_log_over_sd_nass": round(rms_se_dlog / float(tr["d_log_nass_share"].std(ddof=1)), 2),
            "mean_assessable_share": round(float(lv["assessable_share"].mean()), 3),
            "median_cut_doy": float(lv["median_cut_doy"].median()),
        })
        pre = lv[lv["year"].isin(LEVEL_YEARS)]
        nass_pre = truth[(truth["state"] == state) & truth["year"].isin(LEVEL_YEARS)]["nass_share"].mean()
        dilution = level_slope * nass_pre / float(pre["sat_share"].mean())
        rows[-1]["dilution_factor"] = round(dilution, 3)
        rows[-1]["expected_sd_d_log_sat"] = round(dilution * rows[-1]["sd_d_log_nass_share"], 4)
        rows[-1]["expected_snr"] = round(rows[-1]["expected_sd_d_log_sat"] / rms_se_dlog, 2)
    return pd.DataFrame(rows)


def level_rows(asof: str, levels: pd.DataFrame, truth: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    merged = levels.merge(truth[["state", "year", "nass_share"]], on=["state", "year"], how="left")
    pre = merged[merged["year"].isin(LEVEL_YEARS)]
    means = pre.groupby("state")[["sat_share", "sat_share_calls", "nass_share"]].mean()
    rows = []
    for signal in SIGNALS:
        slope, intercept = np.polyfit(means["nass_share"], means[signal], 1)
        rows.append({"asof": asof, "signal": signal, "scope": "state means 2019-2024", "n": len(means),
                     "spearman": round(float(spearmanr(means[signal], means["nass_share"])[0]), 3),
                     "pearson": round(float(pearsonr(means[signal], means["nass_share"])[0]), 3),
                     "slope": round(float(slope), 3), "intercept": round(float(intercept), 3),
                     "mean_sat": round(float(means[signal].mean()), 3),
                     "mean_nass": round(float(means["nass_share"].mean()), 3)})
        for year, part in merged.groupby("year"):
            rows.append({"asof": asof, "signal": signal, "scope": f"year {int(year)}", "n": len(part),
                         "spearman": round(float(spearmanr(part[signal], part["nass_share"])[0]), 3),
                         "pearson": round(float(pearsonr(part[signal], part["nass_share"])[0]), 3)})
    means = means.reset_index().assign(asof=asof)
    means["sat_minus_nass"] = means["sat_share"] - means["nass_share"]
    return rows, means.round(4)


def context_changes() -> pd.DataFrame:
    """Season context changes per state and year from data/panel/state_year.csv (read only; diagnostics)."""
    panel = pd.read_csv(data_dir() / "panel" / "state_year.csv").sort_values(["state", "year"])
    columns = ["drought", "rain_anom", "gdd_anom", "grain_yield"]
    last = panel[["state", "year", *columns]].assign(year=panel["year"] + 1)
    merged = panel[["state", "year", *columns]].merge(last, on=["state", "year"], how="left", suffixes=("", "_last"))
    out = merged[["state", "year"]].copy()
    for column in ["drought", "rain_anom", "gdd_anom"]:
        out[f"d_{column}"] = merged[column] - merged[f"{column}_last"]
    out["d_log_grain_yield"] = np.log(merged["grain_yield"] / merged["grain_yield_last"])
    return out


EXPLAIN = ["d_drought", "d_rain_anom", "d_gdd_anom", "d_log_grain_yield", "d_median_cut_doy", "d_assessable_share"]


def explain_rows(asof: str, table: pd.DataFrame, levels: pd.DataFrame, context: pd.DataFrame) -> list[dict]:
    """What moves with the satellite change, and with NASS's change? Year medians removed, 2020-2025.

    Diagnostics only: it explains the sign of the satellite change, it selects nothing. Final grain yield
    is NASS's January figure (not available on the forecast date); it is used here only to explain.
    """
    levels = levels.sort_values(["state", "year"])
    cut = levels[["state", "year", "median_cut_doy"]].copy()
    cut["d_median_cut_doy"] = levels.groupby("state")["median_cut_doy"].diff()
    frame = table.merge(context, on=["state", "year"], how="left").merge(
        cut[["state", "year", "d_median_cut_doy"]], on=["state", "year"], how="left")
    frame = frame[frame["year"].isin(CHANGE_YEARS)]
    rows = []
    for x in ["d_log_share", "d_log_share_calls", "d_log_nass_share", "d_log_nass_silage"]:
        for y in EXPLAIN:
            rows.append({"asof": asof, "change": x, "with": y, "years": "2020-2025", "year_medians_removed": True,
                         **spearman_with_bootstrap(frame, x, y, True)})
    return rows


def main() -> None:
    truth = nass_truth()
    pooled, levels_out, per_state_means, explained = [], [], [], []
    context = context_changes()
    summary: dict = {}
    for asof in ASOFS:
        if not (OUT / f"state_satellite_asof_{asof}.csv").exists():
            summary[asof] = "UNCOMPUTED: run signal.py first"
            continue
        levels = pd.read_csv(OUT / f"state_satellite_asof_{asof}.csv", dtype={"state_fips": str})
        table = change_table(asof, truth)
        pooled.extend(pooled_rows(asof, table))
        explained.extend(explain_rows(asof, table, levels, context))
        rows, means = level_rows(asof, levels, truth)
        slope = next(r["slope"] for r in rows if r["signal"] == "sat_share" and r["scope"].startswith("state means"))
        states = by_state(asof, table, levels, truth, slope)
        states.to_csv(OUT / f"diagnostics_by_state_asof_{asof}.csv", index=False, lineterminator="\n")
        levels_out.extend(rows)
        per_state_means.append(means)
        n_years = int(states["years"].sum())
        summary[asof] = {
            "sign_agree_share_demeaned": f"{int(states['sign_agree_share_demeaned'].sum())}/{n_years}",
            "sign_agree_silage_demeaned": f"{int(states['sign_agree_silage_demeaned'].sum())}/{n_years}",
            "median_snr_d_share": float(states["snr_d_share"].median()),
            "median_rms_se_d_share": float(states["rms_se_d_share"].median()),
            "median_sd_d_share": float(states["sd_d_share"].median()),
            "median_se_d_log_over_sd_nass": float(states["se_d_log_over_sd_nass"].median()),
            "level_slope_sat_on_nass": slope,
            "median_expected_snr": float(states["expected_snr"].median()),
            "max_expected_snr": float(states["expected_snr"].max()),
        }
    pooled = pd.DataFrame(pooled)
    explained = pd.DataFrame(explained)
    explained.to_csv(OUT / "diagnostics_explain.csv", index=False, lineterminator="\n")
    pooled.to_csv(OUT / "diagnostics_changes.csv", index=False, lineterminator="\n")
    pd.DataFrame(levels_out).to_csv(OUT / "diagnostics_level.csv", index=False, lineterminator="\n")
    if per_state_means:
        pd.concat(per_state_means).to_csv(OUT / "diagnostics_level_by_state.csv", index=False, lineterminator="\n")
    (OUT / "diagnostics_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 300)
    main_rows = pooled[(pooled["change"] == "d_log_share") & pooled["year_medians_removed"]]
    print(main_rows.to_string(index=False))
    print(explained.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
