"""Post-hoc exploration around the pre-registered sat_stress candidates (README section 3).

Everything here was written AFTER the pre-registered results in out/ were seen. None of it is eligible
for selection; it shows how robust (or fragile) the pre-registered result is. Reads run.py outputs.

Run from the repo root (after run.py):
    .venv/Scripts/python.exe test_models/variations/sat_stress/explore.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (str(ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import run  # noqa: E402  (this folder's run.py)
from kernelag import silage_level  # noqa: E402
from kernelag.paths import data_dir  # noqa: E402
from kernelag.state_panel import QUICKSTATS_DIR  # noqa: E402

OUT = HERE / "out"
SEED = 20261115
N_PERM = 2000
YEARS_ALL, YEARS_FIT = run.SCORE_YEARS, list(range(2021, 2025))


def base_rows() -> pd.DataFrame:
    preds = pd.read_csv(OUT / "predictions_by_state_year.csv")
    rows = preds[preds["candidate"].str.startswith("base_")].copy()
    stress = pd.read_csv(OUT / "stress_by_state_year.csv")
    zs = stress[["state", "year", *[f"z_{c}" for c in run.COMPONENTS]]]
    rows = rows.drop(columns=["candidate", "pred"]).merge(zs, on=["state", "year"], how="left")
    hist = silage_level.load_history(data_dir() / QUICKSTATS_DIR, "nov")
    grain = hist["grain"].stack().reset_index()
    grain.columns = ["year", "state", "grain_last"]
    grain["year"] += 1
    return rows.merge(grain, on=["state", "year"], how="left")


def metrics(g: pd.DataFrame, col: str) -> tuple[float, float]:
    miss = g[col] - g["actual"]
    return 100 * miss.abs().sum() / g["actual"].sum(), 100 * abs(miss.sum()) / g["actual"].sum()


def compare(rows: pd.DataFrame, col: str, years: list[int]) -> dict:
    """Paired yearly differences of WAPE15 and |total15 error| against the base, as in the decision rule."""
    out = {}
    per = []
    for year in years:
        g = rows[rows["year"] == year]
        (w_c, t_c), (w_b, t_b) = metrics(g, col), metrics(g, "base")
        per.append((w_c - w_b, t_c - t_b, w_c, w_b, t_c, t_b))
    d = np.array(per)
    n = len(years)
    for i, name in [(0, "wape15"), (1, "abs_total15")]:
        se = d[:, i].std(ddof=1) / np.sqrt(n)
        out.update({f"{name}_cand": d[:, i + 2 + i].mean(), f"{name}_base": d[:, i + 3 + i].mean(),
                    f"{name}_diff": d[:, i].mean(), f"{name}_se": se, f"{name}_diff_plus_2se": d[:, i].mean() + 2 * se,
                    f"{name}_years_better": int((d[:, i] < 0).sum())})
    return out


def fixed(rows: pd.DataFrame, signal: pd.Series, b: float) -> pd.Series:
    return rows["base"] * np.exp(b * signal.fillna(0.0))


def fitted_additive(rows: pd.DataFrame) -> pd.Series:
    """base + k x max(0, stress) x G(t-1); k >= 0 least squares on (actual - base), years 2020..t-1."""
    x = rows["stress"].clip(lower=0).fillna(0.0) * rows["grain_last"].fillna(0.0)
    pred = rows["base"].copy()
    for year in YEARS_ALL:
        train = rows["year"].between(YEARS_ALL[0], year - 1)
        denom = float((x[train] ** 2).sum())
        k = max(0.0, float((x[train] * (rows.loc[train, "actual"] - rows.loc[train, "base"])).sum()) / denom) \
            if denom > 0 else 0.0
        cur = rows["year"] == year
        pred[cur] = rows.loc[cur, "base"] + k * x[cur]
    return pred


def permutation(rows: pd.DataFrame, b: float, within_year: bool, rng: np.random.Generator) -> dict:
    """Null distribution of the c3 improvements when stress values are shuffled among state-years."""
    obs = compare(rows.assign(p=fixed(rows, rows["stress"], b)), "p", YEARS_ALL)
    w, t = [], []
    for _ in range(N_PERM):
        s = rows["stress"].copy()
        if within_year:
            for _, idx in rows.groupby("year").groups.items():
                s.loc[idx] = rng.permutation(s.loc[idx].to_numpy())
        else:
            s[:] = rng.permutation(s.to_numpy())
        c = compare(rows.assign(p=fixed(rows, s, b)), "p", YEARS_ALL)
        w.append(c["wape15_diff"])
        t.append(c["abs_total15_diff"])
    w, t = np.array(w), np.array(t)
    return {"obs_wape15_diff": obs["wape15_diff"], "p_wape15": float((w <= obs["wape15_diff"]).mean()),
            "obs_abs_total15_diff": obs["abs_total15_diff"],
            "p_abs_total15": float((t <= obs["abs_total15_diff"]).mean())}


def no_2019_stress() -> pd.DataFrame:
    """The same index with 2019 dropped from the reference years (anomalies start in 2021)."""
    fields = pd.read_parquet(OUT / "field_components.parquet")
    table = run.stress_table(fields[fields["year"] >= 2020])
    return table[["state", "year", "stress"]].rename(columns={"stress": "stress_no2019"})


def main() -> None:
    rows_all = base_rows().merge(no_2019_stress(), on=["state", "year"], how="left")
    rng = np.random.default_rng(SEED)
    results, perms, loso = [], [], []
    for (base, asof), rows in rows_all.groupby(["base_name", "asof"]):
        rows = rows.reset_index(drop=True)
        variants = {
            "c3_b0.05_preregistered": (fixed(rows, rows["stress"], 0.05), YEARS_ALL),
            "c3_b0.05_window2021_2024": (fixed(rows, rows["stress"], 0.05), YEARS_FIT),
            "E1_peak_only_b0.05": (fixed(rows, -rows["z_peak"], 0.05), YEARS_ALL),
            "E1_ndmi_only_b0.05": (fixed(rows, -rows["z_ndmi"], 0.05), YEARS_ALL),
            "E1_decline_only_b0.05": (fixed(rows, rows["z_decline"], 0.05), YEARS_ALL),
            "E2_positive_stress_only_b0.05": (fixed(rows, rows["stress"].clip(lower=0), 0.05), YEARS_ALL),
            "E3_b0.025": (fixed(rows, rows["stress"], 0.025), YEARS_ALL),
            "E3_b0.075": (fixed(rows, rows["stress"], 0.075), YEARS_ALL),
            "E3_b0.10": (fixed(rows, rows["stress"], 0.10), YEARS_ALL),
            "E7_additive_chop_fitted_k": (fitted_additive(rows), YEARS_FIT),
            "E9_no2019_reference_b0.05": (fixed(rows, rows["stress_no2019"], 0.05), YEARS_FIT),
            "E10_peak_plus_ndmi_b0.05": (fixed(rows, -(rows["z_peak"] + rows["z_ndmi"]) / 2, 0.05), YEARS_ALL),
        }
        for name, (pred, years) in variants.items():
            results.append({"base": base, "asof": asof, "variant": name, "years": f"{years[0]}-{years[-1]}",
                            **compare(rows.assign(p=pred), "p", years)})
        if asof == "nov":
            for within in (False, True):
                perms.append({"base": base, "asof": asof, "b": 0.05,
                              "shuffle": "within_year_across_states" if within else "all_state_years",
                              "n_perm": N_PERM, **permutation(rows, 0.05, within, rng)})
            for state in sorted(rows["state"].unique()):
                sub = rows[rows["state"] != state]
                c = compare(sub.assign(p=fixed(sub, sub["stress"], 0.05)), "p", YEARS_ALL)
                loso.append({"base": base, "dropped_state": state, "wape15_diff": c["wape15_diff"],
                             "abs_total15_diff": c["abs_total15_diff"]})
    res = pd.DataFrame(results)
    res.to_csv(OUT / "explore_variants.csv", index=False, float_format="%.4f")
    pd.DataFrame(perms).to_csv(OUT / "explore_permutation.csv", index=False, float_format="%.4f")
    lo = pd.DataFrame(loso)
    lo.to_csv(OUT / "explore_leave_one_state_out.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    cols = ["base", "variant", "years", "wape15_cand", "wape15_base", "wape15_diff", "wape15_diff_plus_2se",
            "wape15_years_better", "abs_total15_cand", "abs_total15_base", "abs_total15_diff",
            "abs_total15_diff_plus_2se", "abs_total15_years_better"]
    print(res[res["asof"] == "nov"][cols].round(3).to_string())
    print(pd.DataFrame(perms).round(3).to_string())
    print(lo.groupby("base")[["wape15_diff", "abs_total15_diff"]].agg(["min", "max"]).round(3))


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()
