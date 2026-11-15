"""Print the README's markdown tables from out/ (reads only; writes nothing).

Run from the repo root: .venv/Scripts/python.exe -B test_models/variations/silage_combos/tables.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent / "out"
ORDER = ["A", "B", "SC", "SC_B", "SC_L", "SC_A", "s0_persistence", "s1_reversion_only",
         "v1_geo", "v2_topdown", "v3_reverse", "v4_mean3", "v5_chopmult", "v5b_chopadd", "v6_topdown_geoUS",
         "v7_mean2", "v8_geo_fitted", "v9_topdown_SCB", "v10_topdown_SCL", "v11_topdown_SCA", "v12_geo_SCA",
         "v13_chopmult_SCA", "w1_mean2_SCA", "w2_geo_fitted_SCA", "w3_geo_SCA_rescaled", "w4_geo_rescaled",
         "w5_SC_A"]
CANDS = [m for m in ORDER if m[0] in "vw"]


def md(df: pd.DataFrame) -> str:
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    return "\n".join([head, sep] + ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)])


def summary(asof: str) -> str:
    s = pd.read_csv(OUT / "summary.csv")
    s = s[s["asof"] == asof]
    rows = []
    for m in ORDER:
        g = s[s["model"] == m].set_index("period")
        r = g.loc["2012-2024"]
        q = g.loc["2017-2024"]
        rows.append([f"`{m}`", r["role"], r["tier"], f"{r['mean_state_wape_pct']:.2f}",
                     f"{r['mean_abs_us_error_pct']:.2f}", f"{r['mean_signed_us_error_pct']:+.2f}",
                     f"{q['mean_state_wape_pct']:.2f}",
                     f"{q['mean_abs_us_error_pct']:.2f}", f"{q['mean_signed_us_error_pct']:+.2f}"])
    return md(pd.DataFrame(rows, columns=["Model", "Role", "Tier", "WAPE 12-24", "abs US 12-24", "signed US 12-24",
                                          "WAPE 17-24", "abs US 17-24", "signed US 17-24"]))


def paired(asof: str, period: str, vs: str, names: list[str]) -> str:
    c = pd.read_csv(OUT / "comparisons.csv")
    c = c[(c["asof"] == asof) & (c["period"] == period) & (c["vs"] == vs)].set_index("model")
    rows = []
    for m in names:
        r = c.loc[m]
        rows.append([f"`{m}`", f"{r['state_wape_mean_diff']:+.2f} (+2SE {r['state_wape_mean_plus_2se']:+.2f})",
                     f"{r['state_wape_years_better']}/{r['state_wape_years_worse']}", r["state_wape_ci90_years"],
                     r["state_wape_ci90_states"], r["state_wape_ci90_joint"],
                     f"{r['abs_us_mean_diff']:+.2f} (+2SE {r['abs_us_mean_plus_2se']:+.2f})",
                     f"{r['abs_us_years_better']}/{r['abs_us_years_worse']}", r["abs_us_ci90_years"],
                     r["abs_us_ci90_states"], r["abs_us_ci90_joint"]])
    return md(pd.DataFrame(rows, columns=["Model", "WAPE diff", "yrs b/w", "CI years", "CI states", "CI joint",
                                          "abs US diff", "yrs b/w", "CI years", "CI states", "CI joint"]))


def decision() -> str:
    d = json.load(open(OUT / "decision.json"))["primary"]
    rows = []
    table = {**d["candidates"], **d["references_information_only"]}
    for m in ORDER:
        r = table[m]
        rows.append([f"`{m}`", r["tier"], f"{r['R1_wape_minus_A']:+.2f}",
                     f"{r['R1_abs_us_diff_vs_A_mean_plus_2se']:+.3f}",
                     "yes" if r["R1"] else "no", f"{r['R2_wape_diff_vs_SC_mean_plus_2se']:+.3f}",
                     f"{r['R2_abs_us_minus_SC']:+.2f}", "yes" if r["R2"] else "no",
                     ("**RECOMMENDED**" if r["recommended"] else "no") if m in CANDS else "(reference)",
                     "yes" if r["beats_both_strict"] else "no"])
    return md(pd.DataFrame(rows, columns=["Model", "Tier", "WAPE - A", "abs US vs A: d+2SE", "R1",
                                          "WAPE vs SC: d+2SE", "abs US - SC", "R2", "Decision",
                                          "<= best of A and SC on both"]))


def info_rules() -> str:
    d = json.load(open(OUT / "decision.json"))["information"]
    rows = [[k.replace("_", " "), ", ".join(f"`{x}`" for x in v["recommended"]) or "none",
             ", ".join(f"`{x}`" for x in v["beats_both_strict"]) or "none"] for k, v in d.items()]
    columns = ["As of, period", "RECOMMENDED under the rule", "<= best of A and SC on both"]
    return md(pd.DataFrame(rows, columns=columns))


def per_year(names: list[str]) -> str:
    b = pd.read_csv(OUT / "by_year.csv")
    b = b[(b["asof"] == "nov") & b["model"].isin(names)]
    w = b.pivot(index="year", columns="model", values="state_wape_pct")[names].round(2)
    u = b.pivot(index="year", columns="model", values="us_error_pct")[names].round(2)
    rows = [[y] + [f"{w.loc[y, m]:.2f} / {u.loc[y, m]:+.2f}" for m in names] for y in w.index]
    return md(pd.DataFrame(rows, columns=["Year"] + [f"`{m}`" for m in names]))


def dates(names: list[str]) -> str:
    s = pd.read_csv(OUT / "summary.csv")
    rows = []
    for m in names:
        row = [f"`{m}`"]
        for period in ["2012-2024", "2017-2024"]:
            for asof in ["sep", "oct", "nov"]:
                r = s[(s["model"] == m) & (s["asof"] == asof) & (s["period"] == period)].iloc[0]
                row.append(f"{r['mean_state_wape_pct']:.2f} / {r['mean_abs_us_error_pct']:.2f}")
        rows.append(row)
    return md(pd.DataFrame(rows, columns=["Model", "15 Sep 12-24", "15 Oct 12-24", "15 Nov 12-24", "15 Sep 17-24",
                                          "15 Oct 17-24", "15 Nov 17-24"]))


def forecast_us() -> str:
    u = pd.read_csv(OUT / "forecast_2026_us.csv")
    cov = pd.read_csv(OUT / "interval_coverage.csv").set_index(["model", "asof"])
    rows = []
    for m in ORDER:
        row = [f"`{m}`", u.loc[u["model"] == m, "tier"].iloc[0]]
        for asof in ["sep", "oct", "nov"]:
            r = u[(u["model"] == m) & (u["asof"] == asof)].iloc[0]
            row.append(f"{r['us_silage'] / 1e6:.3f} [{r['us_lo80'] / 1e6:.3f}, {r['us_hi80'] / 1e6:.3f}]")
        row.append(f"{cov.loc[(m, 'nov'), 'loyo_coverage_80']:.3f}")
        rows.append(row)
    return md(pd.DataFrame(rows, columns=["Model", "Tier", "15 Sep 2026", "15 Oct 2026", "15 Nov 2026",
                                          "LOYO 80% state coverage (Nov)"]))


def forecast_states(names: list[str], top: int = 15) -> str:
    f = pd.read_csv(OUT / "forecast_2026.csv")
    f = f[f["asof"] == "nov"]
    base = f[f["model"] == names[0]].sort_values("silage", ascending=False).head(top)["state"].tolist()
    rows = []
    for st in base:
        row = [st.title(), f"{f[(f['model'] == 'A') & (f['state'] == st)]['silage_last_year'].iloc[0] / 1e3:.0f}"]
        for m in names:
            r = f[(f["model"] == m) & (f["state"] == st)].iloc[0]
            row.append(f"{r['silage'] / 1e3:.0f} [{r['silage_lo80'] / 1e3:.0f}, {r['silage_hi80'] / 1e3:.0f}]")
        rows.append(row)
    return md(pd.DataFrame(rows, columns=["State", "2025 final"] + [f"`{m}`" for m in names]))


def sensitivity() -> str:
    s = pd.read_csv(OUT / "sensitivity_drought_tau.csv")
    rows = []
    for tau in sorted(s["tau"].unique()):
        row = [f"{tau:.2f}"]
        for m in ["SC_A", "v12_geo_SCA"]:
            for period in ["2012-2024", "2017-2024"]:
                r = s[(s["tau"] == tau) & (s["model"] == m) & (s["period"] == period)].iloc[0]
                row.append(f"{r['mean_state_wape_pct']:.2f} / {r['mean_abs_us_error_pct']:.2f}")
        rows.append(row)
    return md(pd.DataFrame(rows, columns=["TAU_D", "SC_A 12-24", "SC_A 17-24", "v12 12-24", "v12 17-24"]))


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    print("## summary nov\n" + summary("nov"))
    print("\n## decision\n" + decision())
    print("\n## information rules\n" + info_rules())
    for vs in ["A", "SC"]:
        print(f"\n## paired nov 2012-2024 vs {vs}\n" + paired("nov", "2012-2024", vs, CANDS))
    for vs in ["A", "SC"]:
        print(f"\n## paired nov 2017-2024 vs {vs}\n" + paired("nov", "2017-2024", vs, CANDS))
    print("\n## per year\n" + per_year(["A", "SC", "SC_A", "v1_geo", "v7_mean2", "v12_geo_SCA",
                                        "w3_geo_SCA_rescaled", "w4_geo_rescaled"]))
    print("\n## dates\n" + dates(ORDER))
    print("\n## forecast us\n" + forecast_us())
    print("\n## forecast states\n" + forecast_states(["v1_geo", "w3_geo_SCA_rescaled", "A", "SC"]))
    print("\n## sensitivity\n" + sensitivity())
