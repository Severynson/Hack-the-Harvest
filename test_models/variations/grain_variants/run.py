"""Grain variants of A-G3 (Tier A FSA ratio model) at the 15th of Jul..Dec, 2012-2024, plus a 2026 forecast.

Pre-registration, method and results: README.md next to this file (section 1 is hashed in out/preregistration.sha256).

A-G3, B-G7 and NASS's forecast come from the monthly harness (test_models/ownModels/monthly/run.py), imported
unchanged and run with its in-memory as-of patch (patch_asof) and the corrected FSA publication dates. The candidates
g6-g13 reuse the grain folder's own helpers (test_models/ownModels/grain/run.py: NassHistory, FsaView, guarded,
_ratio, predict_fsa), also imported unchanged. The only in-memory addition to the harness is registering the new
model names in monthly.MODELS so that monthly.score can score them. No file outside this folder is written.

Inputs (read only): data/fsa/fsa_files.csv, data/fsa/fsa_corn_state.csv (kernelag.fsa as-of helpers), NASS finals
and in-season tables via the grain and Tier B folders, data/drought/usdm_state_weekly_2000_2026.csv
(kernelag.context.drought), test_models/ownModels/monthly/out/monthly_by_state_year.csv (reproduction check only).
Outputs (out/): by_state_year.csv, by_year.csv, summary.csv, paired.csv, decision.json, fitted_params.csv,
forecast_2026.csv, reproduction.json.

Run from the repository root:
    .venv/Scripts/python.exe test_models/variations/grain_variants/run.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import kernelag.context as kctx  # noqa: E402

OUT = HERE / "out"
MONTHLY_PATH = REPO / "test_models" / "ownModels" / "monthly" / "run.py"
MONTHLY_STORED = REPO / "test_models" / "ownModels" / "monthly" / "out" / "monthly_by_state_year.csv"

A_G3, B_G7, NASS, PERSIST = "g3_fsa_ratio_multi", "b7_blend_b5_fsa_level", "nass_latest", "g0_persistence"
CANDIDATES = {
    "g6_net_failed": "A",
    "g7_net_failed_prevented": "A",
    "g8_vintage_growth": "A",
    "g9_national_reconciliation": "A",
    "g10_geo_blend_g3_b7": "B",
    "g11_drought_abandonment": "A",
    "g12_us_bias_corrected": "A",
    "g13_vintage_matched_ratio": "A",
}
TIER_A = [name for name, tier in CANDIDATES.items() if tier == "A"]
REPORTED = [A_G3, B_G7, NASS, PERSIST, *CANDIDATES]
REFERENCES = {A_G3: "A-G3", NASS: "NASS forecast", B_G7: "B-G7"}
PERIODS = {"2012-2024": (2012, 2024), "2017-2024": (2017, 2024)}
PRIMARY = "2012-2024"
# Descriptive only (added after scoring, never used to decide): the years in which A-G3 has all three reference years.
DESCRIPTIVE = {"2014-2024 descriptive": (2014, 2024)}
YEARS = list(range(2012, 2025))
FORECAST_YEAR, FORECAST_KEY = 2026, "nov"
DECISION_DATES = ["nov", "aug", "sep"]
REPORT_DATES = ["aug", "sep", "oct", "nov", "dec"]
US_TOLERANCE = 0.10
MIN_FIT_YEARS = 3
G11_CLIP = (0.8, 1.2)
EARLY_PREFIXES = ("aug", "sep")
TIE = 1e-6          # yearly differences within this many points count as ties (stored tables carry 10 digits)


# --- harness and model modules (imported unchanged) ----------------------------------------------------------------

def load_monthly():
    spec = importlib.util.spec_from_file_location("grain_variants_monthly", MONTHLY_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["grain_variants_monthly"] = module
    spec.loader.exec_module(module)
    return module


def setup():
    """Monthly harness modules with the six-date as-of patch, and every input loaded once."""
    monthly = load_monthly()
    mods = monthly.load_modules()
    monthly.patch_asof(mods)
    for name, tier in CANDIDATES.items():
        monthly.MODELS[name] = ("grain", tier, "grain_a")
    g, b = mods["grain_a"], mods["grain_b"]
    nass_table, june_check = monthly.nass_inseason_with_june_2013(g)
    shared_a = {"finals": g.load_finals(), "inseason": g.nass_inseason_table(), "sources": g.load_stress_sources()}
    files, state = g.load_fsa()
    src = b.Sources()
    ctx = {"monthly": monthly, "g": g, "b": b, "nass_table": nass_table, "june_check": june_check,
           "shared_a": shared_a, "finals": shared_a["finals"], "files": files, "state": state, "src": src,
           "months": list(monthly.MONTHS)}
    ctx["drought"] = {key: kctx.drought(shared_a["sources"]["usdm"], key) for key in ctx["months"]}
    return ctx


def run_base(ctx: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A-G3, persistence, NASS's forecast (run_grain_a) and B-G7 (run_grain_b) at every date, as the harness does."""
    m, g, b = ctx["monthly"], ctx["g"], ctx["b"]
    p1, i1, _ = m.run_grain_a(g, ctx["files"], ctx["state"], ctx["nass_table"], ctx["shared_a"])
    p2, i2 = m.run_grain_b(b, ctx["src"], b.load_fsa())
    return pd.concat(p1 + p2, ignore_index=True), pd.DataFrame(i1 + i2)


def reproduction_check(base: pd.DataFrame) -> dict:
    stored = pd.read_csv(MONTHLY_STORED)
    keys = ["model", "asof", "year", "state"]
    joined = base.merge(stored, on=keys, suffixes=("", "_stored"), how="left", validate="one_to_one")
    if joined["pred_stored"].isna().any():
        raise RuntimeError("base rows missing from monthly/out/monthly_by_state_year.csv")
    out = {}
    for model, part in joined.groupby("model"):
        gap = (part["pred"] - part["pred_stored"]).abs().max()
        out[model] = {"rows": int(len(part)), "max_abs_diff_acres_vs_stored_0p1": float(gap)}
        if gap > 0.051:
            raise RuntimeError(f"{model} does not reproduce the monthly harness (max gap {gap})")
    return out


# --- FSA helpers -------------------------------------------------------------------------------------------------

def years_back(day: date, k: int, g) -> date:
    for _ in range(k):
        day = g._one_year_back(day)
    return day


def grain_measure(view, file: pd.Series | None, minus: tuple[str, ...]) -> pd.Series:
    """Grain-intended planted acres by state in one usable file, minus the listed grain-intended columns."""
    if file is None:
        return pd.Series(dtype=float)
    view.acres(file, "grain")          # PermissionError if the file is not usable on view.asof
    st = view._state
    rows = st[(st["crop_year"] == file["crop_year"]) & (st["data_as_of"] == file["data_as_of"])
              & (st["intended_use"] == "grain")]
    values = rows["planted_acres"].copy()
    for column in minus:
        values = values - rows[column].fillna(0.0)
    return values.groupby(rows["state"]).sum()


def closest_same_month(view, crop_year: int, prefix: str, aim: date) -> pd.Series | None:
    rows = view.usable[(view.usable["crop_year"] == crop_year)
                       & view.usable["vintage"].astype(str).str.startswith(prefix)]
    if rows.empty:
        return None
    dates = pd.to_datetime(rows["data_as_of"])
    order = pd.DataFrame({"d": (dates - pd.Timestamp(aim)).abs().to_numpy(), "date": dates.to_numpy(),
                          "pos": np.arange(len(rows))})
    return rows.iloc[int(order.sort_values(["d", "date"], ascending=[True, False])["pos"].iloc[0])]


def nov_file(view, crop_year: int) -> pd.Series | None:
    rows = view.usable[(view.usable["crop_year"] == crop_year) & (view.usable["vintage"].astype(str) == "nov")]
    return None if rows.empty else rows.sort_values("data_as_of").iloc[-1]


# --- candidates --------------------------------------------------------------------------------------------------

def net_ratio(g, hist, view, last: pd.Series, minus: tuple[str, ...]) -> pd.DataFrame:
    """g6 / g7 (and, with minus=(), an independent rebuild of A-G3)."""
    t = view.crop_year
    cur = view.current()
    if cur is None:
        return g.guarded(pd.Series(dtype=float), pd.Series(dtype=float), last)
    ratios = []
    for k in (1, 2, 3):
        ref = view.final(t - k)
        if ref is None:
            continue
        nass_k = hist.grain(t - k)
        if nass_k.empty:
            continue
        ratios.append(g._ratio(nass_k, grain_measure(view, ref, minus)).reindex(last.index))
    multiplier = pd.concat(ratios, axis=1).median(axis=1, skipna=True) if ratios else pd.Series(dtype=float)
    return g.guarded(grain_measure(view, cur, minus), multiplier, last)


def vintage_growth(g, view, a3: pd.DataFrame, last: pd.Series) -> tuple[pd.DataFrame, dict]:
    """g8: Aug/Sep current file scaled by the median Nov / same-month growth of the previous 3 crop years."""
    t = view.crop_year
    cur = view.current()
    vintage = None if cur is None else str(cur["vintage"])
    if cur is None or not vintage.startswith(EARLY_PREFIXES):
        return a3[["pred", "method"]].assign(growth=np.nan), {"g8_applied": False}
    prefix = "aug" if vintage.startswith("aug") else "sep"
    cur_day = date.fromisoformat(str(cur["data_as_of"]))
    growths, pairs = [], []
    for k in (1, 2, 3):
        early = closest_same_month(view, t - k, prefix, years_back(cur_day, k, g))
        nov = nov_file(view, t - k)
        if early is None or nov is None:
            continue
        growths.append(g._ratio(view.acres(nov, "grain"), view.acres(early, "grain")).reindex(last.index))
        pairs.append(f"{t - k}:{early['data_as_of']}->{nov['data_as_of']}")
    growth = pd.concat(growths, axis=1).median(axis=1, skipna=True) if growths else pd.Series(1.0, index=last.index)
    growth = growth.reindex(last.index).fillna(1.0)
    table = g.guarded(view.acres(cur, "grain"), growth * a3["multiplier"], last)
    fsa_now = view.acres(cur, "grain").reindex(last.index)
    us_growth = float((fsa_now * growth).sum() / fsa_now.sum())
    table = table[["pred", "method"]].assign(growth=growth)
    return table, {"g8_applied": True, "g8_pairs": " ".join(pairs), "g8_us_growth": us_growth}


def national_reconciliation(g, hist, view, a3: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """g9: A-G3's FSA states scaled to the national FSA x median national NASS/FSA ratio."""
    t = view.crop_year
    cur = view.current()
    out = a3[["pred", "method"]].copy()
    if cur is None:
        return out, {"g9_scale": np.nan}
    fsa_states = a3.index[a3["method"] == "fsa"]
    current = view.acres(cur, "grain").reindex(fsa_states)
    ratios = []
    for k in (1, 2, 3):
        ref = view.final(t - k)
        if ref is None:
            continue
        nass_k = hist.grain(t - k).reindex(fsa_states)
        fsa_k = view.acres(ref, "grain").reindex(fsa_states)
        both = nass_k.notna() & fsa_k.gt(0)
        if both.any():
            ratios.append(float(nass_k[both].sum() / fsa_k[both].sum()))
    if not ratios:
        return out, {"g9_scale": np.nan}
    national = float(current.sum()) * float(np.median(ratios))
    scale = national / float(out.loc[fsa_states, "pred"].sum())
    out.loc[fsa_states, "pred"] = out.loc[fsa_states, "pred"] * scale
    return out, {"g9_scale": scale, "g9_us_ratio_median": float(np.median(ratios)), "g9_n_ratio_years": len(ratios)}


def vintage_matched(g, hist, view, last: pd.Series) -> pd.DataFrame:
    """g13: ratio of NASS final to the FSA file of each reference year nearest in data date to the current file."""
    t = view.crop_year
    cur = view.current()
    if cur is None:
        return g.guarded(pd.Series(dtype=float), pd.Series(dtype=float), last)
    cur_day = date.fromisoformat(str(cur["data_as_of"]))
    ratios = []
    for k in (1, 2, 3):
        ref = view.closest(t - k, years_back(cur_day, k - 1, g))
        if ref is None:
            continue
        nass_k = hist.grain(t - k)
        if nass_k.empty:
            continue
        ratios.append(g._ratio(nass_k, view.acres(ref, "grain")).reindex(last.index))
    multiplier = pd.concat(ratios, axis=1).median(axis=1, skipna=True) if ratios else pd.Series(dtype=float)
    return g.guarded(view.acres(cur, "grain"), multiplier, last)


def drought_change(ctx: dict, key: str, t: int, index: pd.Index) -> pd.Series:
    levels = ctx["drought"][key].pivot_table(index="state", columns="year", values="drought")
    now = levels[t].reindex(index) if t in levels.columns else pd.Series(np.nan, index=index)
    refs = [levels[y].reindex(index) for y in (t - 1, t - 2, t - 3) if y in levels.columns]
    before = pd.concat(refs, axis=1).mean(axis=1, skipna=True) if refs else pd.Series(np.nan, index=index)
    return (now - before).fillna(0.0)


def fit_k(train: list[pd.DataFrame]) -> tuple[float, int]:
    """g11's k by weighted least squares of r = actual/A-G3 - 1 on -dD (no intercept), k >= 0."""
    rows = pd.concat(train, ignore_index=True) if train else pd.DataFrame()
    years = int(rows["year"].nunique()) if len(rows) else 0
    if years < MIN_FIT_YEARS:
        return 0.0, years
    w, x, r = rows["weight"].to_numpy(float), rows["dD"].to_numpy(float), rows["r"].to_numpy(float)
    den = float((w * x * x).sum())
    k = -float((w * x * r).sum()) / den if den > 0 else 0.0
    return max(0.0, k), years


def fit_b(history: list[dict]) -> tuple[float, int]:
    """g12's b: median log US ratio of A-G3 to truth over earlier years that had a current-year FSA file."""
    logs = [h["log_us"] for h in history if h["has_file"]]
    if len(logs) < MIN_FIT_YEARS:
        return 0.0, len(logs)
    return float(np.median(logs)), len(logs)


def run_candidates(ctx: dict, base: pd.DataFrame) -> tuple[list, list, list, dict, dict]:
    """Every candidate at every date and year (2012-2024), plus the 2026 Nov forecast rows."""
    m, g = ctx["monthly"], ctx["g"]
    finals, files, state = ctx["finals"], ctx["files"], ctx["state"]
    b7_all = base[base["model"] == B_G7].set_index(["asof", "year", "state"])["pred"]
    a3_harness = base[base["model"] == A_G3].set_index(["asof", "year", "state"])["pred"]
    preds, info, params, checks, forecast = [], [], [], {"a3_rebuild_max_abs_diff_acres": 0.0,
                                                         "a3_vs_harness_max_abs_diff_acres": 0.0}, {}
    for key in ctx["months"]:
        train_k, hist_b = [], []
        years = YEARS + ([FORECAST_YEAR] if key == FORECAST_KEY else [])
        for t in years:
            hist = g.NassHistory(finals, t)
            view = g.FsaView(files, state, g.asof_date(t, key), t)
            last = hist.grain(t - 1)
            a3, used = g.predict_fsa(A_G3, hist, view)
            rebuild = net_ratio(g, hist, view, last, ())
            checks["a3_rebuild_max_abs_diff_acres"] = max(checks["a3_rebuild_max_abs_diff_acres"],
                                                          float((rebuild["pred"] - a3["pred"]).abs().max()))
            has_file = used["current"] is not None
            fsa_states = a3["method"] == "fsa"
            out = {
                "g6_net_failed": net_ratio(g, hist, view, last, ("failed_acres",))["pred"],
                "g7_net_failed_prevented": net_ratio(g, hist, view, last,
                                                     ("failed_acres", "prevented_acres"))["pred"],
                "g13_vintage_matched_ratio": vintage_matched(g, hist, view, last)["pred"],
            }
            g8, g8_info = vintage_growth(g, view, a3, last)
            g9, g9_info = national_reconciliation(g, hist, view, a3)
            out["g8_vintage_growth"], out["g9_national_reconciliation"] = g8["pred"], g9["pred"]
            dD = drought_change(ctx, key, t, a3.index)
            # 2026 uses the parameters fitted on 2012-2024 (frozen); backtest years use 2012..t-1
            k, k_years = fit_k(train_k)
            factor = (1 - k * dD).clip(*G11_CLIP)
            out["g11_drought_abandonment"] = a3["pred"].where(~fsa_states, a3["pred"] * factor)
            b, b_years = fit_b(hist_b)
            out["g12_us_bias_corrected"] = a3["pred"].where(~fsa_states, a3["pred"] * np.exp(-b))
            if t == FORECAST_YEAR:
                inp, _ = ctx["b"].inputs_for(ctx["src"], t, key)
                b7 = ctx["b"].nonfitted(inp)[B_G7]["pred"].reindex(a3.index)
            else:
                b7 = b7_all.loc[(key, t)].reindex(a3.index)
            out["g10_geo_blend_g3_b7"] = np.sqrt(a3["pred"] * b7)
            params.append({"asof": key, "year": t, "fsa_current": used["current"], "fsa_states": int(fsa_states.sum()),
                           "g11_k": k, "g11_train_years": k_years,
                           "g11_us_factor": float((a3["pred"] * factor).where(fsa_states, a3["pred"]).sum()
                                                  / a3["pred"].sum()),
                           "g12_b": b, "g12_train_years": b_years, "g12_factor": float(np.exp(-b)),
                           **g8_info, **g9_info})
            if t == FORECAST_YEAR:
                forecast = {"a3": a3, "out": out, "b7": b7, "used": used, "view": view, "last": last}
                continue
            actual = g.truth(finals, t)
            harness = a3_harness.loc[(key, t)].reindex(actual.index)
            checks["a3_vs_harness_max_abs_diff_acres"] = max(checks["a3_vs_harness_max_abs_diff_acres"], float(
                (harness - a3["pred"].reindex(actual.index)).abs().max()))
            label = m.fsa_label(files, used["current"], m.asof_day(t, key))
            for name, pred in out.items():
                preds.append(m._frame(name, key, t, pred, actual))
                info.append({"model": name, "asof": key, "year": t, "fallback": label is None, "fsa_file": label,
                             "detail": ""})
            # training rows for later years (outcomes of year t are history from t+1 on)
            rows = pd.DataFrame({"pred": a3["pred"], "fsa": fsa_states, "dD": dD,
                                 "weight": last.reindex(a3.index)}).join(actual.rename("actual"), how="inner")
            rows = rows[rows["fsa"] & rows["weight"].gt(0)]
            if len(rows):
                train_k.append(rows.assign(r=rows["actual"] / rows["pred"] - 1, year=t))
            us_pred = float(a3["pred"].reindex(actual.index).sum())
            hist_b.append({"year": t, "has_file": has_file, "log_us": float(np.log(us_pred / actual.sum()))})
    return preds, info, params, checks, forecast


# --- scoring -----------------------------------------------------------------------------------------------------

def summarise(by_year: pd.DataFrame, months: list[str]) -> pd.DataFrame:
    rows = []
    for period, (lo, hi) in {**PERIODS, **DESCRIPTIVE}.items():
        part = by_year[by_year["year"].between(lo, hi)]
        for (model, key), grp in part.groupby(["model", "asof"], sort=False):
            if len(grp) != hi - lo + 1:
                raise ValueError(f"{model} {key} {period}: {len(grp)} years")
            rows.append({"model": model, "tier": CANDIDATES.get(model, "base"), "asof": key, "period": period,
                         "n_years": len(grp), "mean_state_wape_pct": grp["state_wape_pct"].mean(),
                         "mean_abs_us_error_pct": grp["us_error_pct"].abs().mean(),
                         "mean_signed_us_error_pct": grp["us_error_pct"].mean(),
                         "worst_year_state_wape_pct": grp["state_wape_pct"].max(),
                         "fallback_years": " ".join(str(y) for y in grp.loc[grp["fallback"].astype(bool), "year"])})
    summary = pd.DataFrame(rows)
    extra = []
    for (model, period), grp in summary.groupby(["model", "period"], sort=False):
        sub = grp[grp["asof"].isin(REPORT_DATES)]
        extra.append({"model": model, "tier": grp["tier"].iloc[0], "asof": "avg_aug_dec", "period": period,
                      "n_years": int(sub["n_years"].iloc[0]),
                      **{c: sub[c].mean() for c in ["mean_state_wape_pct", "mean_abs_us_error_pct",
                                                    "mean_signed_us_error_pct"]}})
    summary = pd.concat([summary, pd.DataFrame(extra)], ignore_index=True)
    order = {k: i for i, k in enumerate([*months, "avg_aug_dec"])}
    morder = {k: i for i, k in enumerate(REPORTED)}
    return summary.sort_values(["period", "model", "asof"], key=lambda c: c.map(order) if c.name == "asof" else (
        c.map(morder) if c.name == "model" else c)).reset_index(drop=True)


DEFAULT_PAIRS = [(c, r) for c in CANDIDATES for r in (A_G3, NASS)] + [("g10_geo_blend_g3_b7", B_G7), (A_G3, NASS),
                                                                     (B_G7, NASS), (B_G7, A_G3)]


def paired(by_year: pd.DataFrame, monthly, months: list[str], boot: int,
           pairs: list[tuple[str, str]] | None = None) -> pd.DataFrame:
    """Each candidate (and A-G3 / B-G7) minus each reference, paired by year: mean, SE, bars, bootstrap 90%."""
    rows = []
    data = by_year.assign(abs_us=by_year["us_error_pct"].abs())
    pairs = DEFAULT_PAIRS if pairs is None else pairs
    for period, (lo, hi) in PERIODS.items():
        part = data[data["year"].between(lo, hi)]
        for metric, column in [("state_wape_pct", "state_wape_pct"), ("abs_us_error_pct", "abs_us")]:
            wide = part.pivot_table(index="year", columns=["model", "asof"], values=column)
            for key in [*months, "avg_aug_dec"]:
                members = REPORT_DATES if key == "avg_aug_dec" else [key]
                for model, ref in pairs:
                    mine = wide[[(model, k) for k in members]].mean(axis=1)
                    theirs = wide[[(ref, k) for k in members]].mean(axis=1)
                    d = (mine - theirs).to_numpy()
                    se = float(d.std(ddof=1) / np.sqrt(len(d)))
                    mean, lo_ci, hi_ci = monthly.paired_ci(d, boot)
                    rows.append({"model": model, "reference": ref, "asof": key, "period": period, "metric": metric,
                                 "n_years": len(d), "mean_model": float(mine.mean()), "mean_ref": float(theirs.mean()),
                                 "mean_diff_pts": mean, "se": se, "mean_plus_2se": mean + 2 * se,
                                 "mean_plus_3se": mean + 3 * se, "boot90_lo": lo_ci, "boot90_hi": hi_ci,
                                 "years_model_better": int((d < -TIE).sum()),
                                 "years_tied": int((np.abs(d) <= TIE).sum())})
    return pd.DataFrame(rows)


def decide(pair: pd.DataFrame) -> dict:
    """The pre-registered rule (README 1.4) at 15 Nov, 15 Aug and 15 Sep on 2012-2024."""
    p = pair[pair["period"] == PRIMARY]
    result = {}
    for key in DECISION_DATES:
        rows = []
        tested = [(c, A_G3) for c in TIER_A] + [("g10_geo_blend_g3_b7", B_G7)]
        for model, ref in tested:
            st = p[(p["model"] == model) & (p["reference"] == ref) & (p["asof"] == key)
                   & (p["metric"] == "state_wape_pct")].iloc[0]
            us = p[(p["model"] == model) & (p["reference"] == ref) & (p["asof"] == key)
                   & (p["metric"] == "abs_us_error_pct")].iloc[0]
            passes = bool(st["mean_plus_2se"] < 0 and us["mean_diff_pts"] <= US_TOLERANCE)
            rows.append({"model": model, "reference": ref, "tier": CANDIDATES[model],
                         "state_wape": st["mean_model"], "ref_state_wape": st["mean_ref"],
                         "state_diff": st["mean_diff_pts"], "state_diff_plus_2se": st["mean_plus_2se"],
                         "state_diff_plus_3se": st["mean_plus_3se"], "abs_us": us["mean_model"],
                         "ref_abs_us": us["mean_ref"], "abs_us_diff": us["mean_diff_pts"],
                         "years_better": int(st["years_model_better"]), "passes": passes,
                         "also_clears_3se": bool(passes and st["mean_plus_3se"] < 0)})
        tier_a = [r for r in rows if r["tier"] == "A" and r["passes"]]
        winner = min(tier_a, key=lambda r: r["state_wape"])["model"] if tier_a else None
        tier_b = [r for r in rows if r["tier"] == "B" and r["passes"]]
        result[key] = {"tested": rows, "tier_a_winner": winner,
                       "tier_b_option": tier_b[0]["model"] if tier_b else None}
    return result


# --- 2026 forecast -----------------------------------------------------------------------------------------------

def interval_model(ctx: dict, preds: pd.DataFrame, model: str) -> dict:
    """The grain folder's 80% interval method (error_model / bounds / coverage_loyo / us_rms) on ``model``'s
    15 Nov backtest 2012-2024. Added after scoring, as forecast decoration; not a selection input."""
    g = ctx["g"]
    rows = preds[(preds["model"] == model) & (preds["asof"] == FORECAST_KEY)][["year", "state", "pred", "actual"]]
    rows = g.attach_last(rows, ctx["finals"])
    fitted = g.error_model(rows)
    return {"fitted": fitted, "state_80_coverage_loyo": g.coverage_loyo(rows), "us_log_rms": g.us_rms(rows)}


def forecast_table(ctx: dict, fc: dict, recommended: set[str], preds: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    g = ctx["g"]
    a3, last, used = fc["a3"], fc["last"], fc["used"]
    bench = g.nass_benchmark(ctx["nass_table"], ctx["finals"], FORECAST_YEAR, FORECAST_KEY).reindex(a3.index)
    columns = {A_G3: a3["pred"], B_G7: fc["b7"], **fc["out"]}
    rows, intervals = [], {}
    for name, pred in columns.items():
        pred = pred.reindex(a3.index)
        tier = CANDIDATES.get(name, "A" if name == A_G3 else "B")
        note = "recommended" if name in recommended else ("reference" if name in (A_G3, B_G7) else "not recommended")
        lo = hi = pd.Series(np.nan, index=a3.index)
        us_lo = us_hi = np.nan
        if name == A_G3 or name in recommended:
            im = interval_model(ctx, preds, name)
            lo_v, hi_v = g.bounds(pred.to_numpy(), last.reindex(a3.index).to_numpy(), im["fitted"])
            lo, hi = pd.Series(lo_v, index=a3.index), pd.Series(hi_v, index=a3.index)
            us_lo, us_hi = pred.sum() * np.exp(-g.Z80 * im["us_log_rms"]), pred.sum() * np.exp(g.Z80 * im["us_log_rms"])
            intervals[name] = {"state_80_coverage_leave_one_year_out": round(im["state_80_coverage_loyo"], 3),
                               "us_log_error_rms": round(im["us_log_rms"], 5),
                               "size_class_edges_acres": [float(e) for e in im["fitted"]["edges"]],
                               "log_error_q10_q90_by_class": {int(c): [round(float(v), 4) for v in q]
                                                              for c, q in im["fitted"]["q"].items()}}
        for st in a3.index:
            rows.append({"model": name, "tier": tier, "status": note, "state": st, "pred": float(pred[st]),
                         "lo80": float(lo[st]), "hi80": float(hi[st]),
                         "nass_2025_final": float(last[st]), "nass_nov_2026_forecast_reference": float(bench[st])})
        rows.append({"model": name, "tier": tier, "status": note, "state": f"US (sum of {len(a3)} states)",
                     "pred": float(pred.sum()), "lo80": float(us_lo), "hi80": float(us_hi),
                     "nass_2025_final": float(last.sum()), "nass_nov_2026_forecast_reference": float(bench.sum())})
    table = pd.DataFrame(rows)
    table["change_vs_2025_pct"] = 100 * (table["pred"] / table["nass_2025_final"] - 1)
    table["minus_nass_forecast_pct"] = 100 * (table["pred"] / table["nass_nov_2026_forecast_reference"] - 1)
    table["fsa_current_file"] = used["current"]
    table["fsa_current_data_as_of"] = used["current_data_as_of"]
    table["asof"] = f"{FORECAST_YEAR}-11-15"
    return table, intervals


# --- main --------------------------------------------------------------------------------------------------------

def _write(frame: pd.DataFrame, name: str, fmt: str = "%.6g") -> None:
    frame.to_csv(OUT / name, index=False, lineterminator="\n", float_format=fmt)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--boot", type=int, default=10_000)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    ctx = setup()
    m = ctx["monthly"]
    base, base_info = run_base(ctx)
    repro = {"vs_monthly_out_monthly_by_state_year": reproduction_check(base),
             "june_2013_parse": ctx["june_check"].get(2013)}
    preds, info, params, checks, fc = run_candidates(ctx, base)
    repro.update(checks)
    if checks["a3_rebuild_max_abs_diff_acres"] > 1e-6 or checks["a3_vs_harness_max_abs_diff_acres"] > 1e-6:
        raise RuntimeError(f"A-G3 rebuild differs: {checks}")
    keep = base["model"].isin([A_G3, B_G7, NASS, PERSIST])
    all_preds = pd.concat([base[keep], *preds], ignore_index=True)
    all_info = pd.concat([base_info[base_info["model"].isin([A_G3, B_G7, NASS, PERSIST])], pd.DataFrame(info)],
                         ignore_index=True)
    by_year = m.score(all_preds, all_info)
    summary = summarise(by_year, ctx["months"])
    pair = paired(by_year, m, ctx["months"], args.boot)
    decision = decide(pair)
    recommended = {d["tier_a_winner"] for d in decision.values() if d["tier_a_winner"]}
    forecast, intervals = forecast_table(ctx, fc, recommended, all_preds)
    repro["intervals_2026"] = intervals

    _write(all_preds.sort_values(["model", "asof", "year", "state"]), "by_state_year.csv", "%.1f")
    _write(by_year, "by_year.csv", "%.10g")
    _write(summary, "summary.csv")
    _write(pair, "paired.csv")
    _write(pd.DataFrame(params), "fitted_params.csv")
    _write(forecast, "forecast_2026.csv", "%.10g")
    (OUT / "decision.json").write_text(json.dumps(decision, indent=1, default=str) + "\n", encoding="utf-8")
    repro["asof_patch"] = dict(kctx.ASOF_MONTH)
    (OUT / "reproduction.json").write_text(json.dumps(repro, indent=1, default=str) + "\n", encoding="utf-8")

    pd.set_option("display.width", 250)
    for period in PERIODS:
        part = summary[summary["period"] == period]
        grid = part.pivot(index="model", columns="asof", values="mean_state_wape_pct").reindex(
            index=REPORTED, columns=[*ctx["months"], "avg_aug_dec"])
        us = part.pivot(index="model", columns="asof", values="mean_abs_us_error_pct").reindex(
            index=REPORTED, columns=[*ctx["months"], "avg_aug_dec"])
        print(period, "state WAPE\n", grid.round(2).to_string(), "\n", period, "|US|\n", us.round(2).to_string())
    print(json.dumps({k: {"tier_a_winner": v["tier_a_winner"], "tier_b_option": v["tier_b_option"]}
                      for k, v in decision.items()}, indent=1))


if __name__ == "__main__":
    main()
