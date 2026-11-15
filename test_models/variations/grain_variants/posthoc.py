"""POST HOC variants of A-G3, written after the pre-registered g6-g13 were scored (README section 3).

None of these can be selected: they are reported to show what the pre-registered results suggest trying next.
Run run.py first (this script pairs against its out/by_year.csv). Same harness, same dates, same years.

    ph1_g9_on_g11     g11's state shares, rescaled to g9's national estimate (drought split + national total)
    ph2_g9_on_g8      g8's state values, rescaled to a national estimate that also uses g8's vintage growth
    ph3_g3_hist0910   A-G3 with the 2009 and 2010 FSA final files usable as references (their publication date set
                      to internal save time + 8 days, 2011-09-17; they carry no data date, so the documented rule
                      leaves them unusable). Changes 2012 and 2013 only
    ph4_g9_hist0910   g9 on top of ph3

Outputs (out/): posthoc_by_state_year.csv, posthoc_by_year.csv, posthoc_summary.csv, posthoc_paired.csv,
posthoc_notes.json.

Run from the repository root:
    .venv/Scripts/python.exe test_models/variations/grain_variants/posthoc.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def load_run():
    spec = importlib.util.spec_from_file_location("grain_variants_run", HERE / "run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["grain_variants_run"] = module
    spec.loader.exec_module(module)
    return module


rv = load_run()
POSTHOC = ["ph1_g9_on_g11", "ph2_g9_on_g8", "ph3_g3_hist0910", "ph4_g9_hist0910"]
G9 = "g9_national_reconciliation"
HISTORY_LAG_DAYS = 8


def with_0910_history(files: pd.DataFrame, state: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Copies of the FSA tables in which the 2009 and 2010 final detail files carry a placeholder data date and a
    publication date of internal save time + 8 days (in memory only)."""
    files, state = files.copy(), state.copy()
    notes = {}
    for crop_year, placeholder in [(2009, "2010-01-01"), (2010, "2011-01-01")]:
        mask = (files["crop_year"] == crop_year) & (files["status"] == "ok") & (files["vintage"] == "final")
        if mask.sum() != 1 or files.loc[mask, "data_as_of"].notna().any():
            raise ValueError(f"{crop_year}: expected one undated ok final file")
        saved = pd.Timestamp(files.loc[mask, "internal_saved"].iloc[0]).normalize()
        published = (saved + pd.Timedelta(days=HISTORY_LAG_DAYS)).date().isoformat()
        files.loc[mask, "data_as_of"] = placeholder
        files.loc[mask, "assumed_published"] = published
        smask = (state["crop_year"] == crop_year) & state["data_as_of"].isna() & (state["vintage"] == "final")
        state.loc[smask, "data_as_of"] = placeholder
        notes[crop_year] = {"zip": files.loc[mask, "zip_name"].iloc[0], "internal_saved": str(saved.date()),
                            "assumed_published_posthoc": published, "state_rows": int(smask.sum())}
    return files, state, notes


def rescale(pred: pd.Series, fsa: pd.Series, national: float) -> pd.Series:
    out = pred.copy()
    if np.isfinite(national) and fsa.any():
        out[fsa] = out[fsa] * national / out[fsa].sum()
    return out


def run(ctx: dict) -> tuple[list, list, dict]:
    m, g = ctx["monthly"], ctx["g"]
    finals, files, state = ctx["finals"], ctx["files"], ctx["state"]
    files2, state2, notes = with_0910_history(files, state)
    preds, info = [], []
    for key in ctx["months"]:
        train_k = []
        for t in rv.YEARS:
            hist = g.NassHistory(finals, t)
            day = g.asof_date(t, key)
            view = g.FsaView(files, state, day, t)
            last = hist.grain(t - 1)
            actual = g.truth(finals, t)
            a3, used = g.predict_fsa(rv.A_G3, hist, view)
            fsa = a3["method"] == "fsa"
            dD = rv.drought_change(ctx, key, t, a3.index)
            k, _ = rv.fit_k(train_k)
            g11 = a3["pred"].where(~fsa, a3["pred"] * (1 - k * dD).clip(*rv.G11_CLIP))
            g8, _ = rv.vintage_growth(g, view, a3, last)
            g9, g9_info = rv.national_reconciliation(g, hist, view, a3)
            national = g9_info["g9_scale"] * float(a3.loc[fsa, "pred"].sum())
            out = {"ph1_g9_on_g11": rescale(g11, fsa, national)}
            cur = view.current()
            if cur is not None and g8["growth"].notna().any():
                grown = (view.acres(cur, "grain").reindex(a3.index) * g8["growth"]).where(fsa)
                national_g8 = g9_info["g9_us_ratio_median"] * float(grown.sum())
                out["ph2_g9_on_g8"] = rescale(g8["pred"], fsa & g8["method"].eq("fsa"), national_g8)
            else:
                out["ph2_g9_on_g8"] = g9["pred"]
            view2 = g.FsaView(files2, state2, day, t)
            ph3, _ = g.predict_fsa(rv.A_G3, hist, view2)
            ph4, _ = rv.national_reconciliation(g, hist, view2, ph3)
            out["ph3_g3_hist0910"], out["ph4_g9_hist0910"] = ph3["pred"], ph4["pred"]
            label = m.fsa_label(files, used["current"], m.asof_day(t, key))
            for name, pred in out.items():
                preds.append(m._frame(name, key, t, pred, actual))
                info.append({"model": name, "asof": key, "year": t, "fallback": label is None, "fsa_file": label,
                             "detail": "post hoc"})
            rows = pd.DataFrame({"pred": a3["pred"], "fsa": fsa, "dD": dD,
                                 "weight": last.reindex(a3.index)}).join(actual.rename("actual"), how="inner")
            rows = rows[rows["fsa"] & rows["weight"].gt(0)]
            if len(rows):
                train_k.append(rows.assign(r=rows["actual"] / rows["pred"] - 1, year=t))
    return preds, info, notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--boot", type=int, default=10_000)
    args = parser.parse_args()
    ctx = rv.setup()
    m = ctx["monthly"]
    for name in POSTHOC:
        m.MODELS[name] = ("grain", "A (post hoc)", "grain_a")
    preds, info, notes = run(ctx)
    ph_preds = pd.concat(preds, ignore_index=True)
    by_year_ph = m.score(ph_preds, pd.DataFrame(info))
    stored = pd.read_csv(rv.OUT / "by_year.csv")
    refs = stored[stored["model"].isin([rv.A_G3, rv.NASS, G9])]
    by_year = pd.concat([refs, by_year_ph], ignore_index=True)
    summary = rv.summarise(by_year, ctx["months"])
    summary = summary[summary["model"].isin(POSTHOC)].assign(tier="A (post hoc)")
    pairs = [(p, r) for p in POSTHOC for r in (rv.A_G3, G9, rv.NASS)]
    pair = rv.paired(by_year, m, ctx["months"], args.boot, pairs)
    rv._write(ph_preds.sort_values(["model", "asof", "year", "state"]), "posthoc_by_state_year.csv", "%.1f")
    rv._write(by_year_ph, "posthoc_by_year.csv", "%.10g")
    rv._write(summary, "posthoc_summary.csv")
    rv._write(pair, "posthoc_paired.csv")
    pd.set_option("display.width", 250)
    for period in rv.PERIODS:
        part = summary[summary["period"] == period]
        cols = [*ctx["months"], "avg_aug_dec"]
        print(period, "state WAPE / |US|")
        print(part.pivot(index="model", columns="asof", values="mean_state_wape_pct")[cols].round(2).to_string())
        print(part.pivot(index="model", columns="asof", values="mean_abs_us_error_pct")[cols].round(2).to_string())
    notes_text = json.dumps({"fsa_2009_2010_history_patch": notes}, indent=1)
    (rv.OUT / "posthoc_notes.json").write_text(notes_text + "\n", encoding="utf-8")
    print(notes)


if __name__ == "__main__":
    main()
