"""Extra map layers: counties, dairy, weather, money, harvest timing and where the satellite looks.

Everything is read from files already in the repo (data/Quick Stats exports, data/weather, data/panel,
the BARC field file). Nothing is downloaded. Each block is optional: if its file is missing, that layer
is simply left out and the reason is reported.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from board.sources import REPO

QS = REPO / "data" / "Quickstats Data"


def _qs(name: str) -> pd.DataFrame:
    t = pd.read_csv(QS / name, dtype=str, low_memory=False)
    t["v"] = pd.to_numeric(t["Value"].str.replace(",", "").str.strip(), errors="coerce")
    t["year"] = pd.to_numeric(t["year"], errors="coerce")
    return t


# Milk-cow herd-size classes in the Census, and a typical herd for each when its head count is withheld.
HERD_CLASSES = {"(1 TO 9 HEAD)": 4, "(10 TO 19 HEAD)": 14, "(20 TO 49 HEAD)": 33, "(50 TO 99 HEAD)": 72,
                "(100 TO 199 HEAD)": 140, "(200 TO 499 HEAD)": 300, "(500 OR MORE HEAD)": 1500}


def _fips(t: pd.DataFrame) -> pd.Series:
    return t["state_fips_code"].str.zfill(2) + t["county_code"].str.zfill(3)


def _census_state_totals(name: str, unit: str, extra=None) -> dict:
    """{year: {state_fips: Census total}} from a state-level Quick Stats export."""
    t = _qs(name)
    t = t[(t["agg_level_desc"] == "STATE") & (t["source_desc"] == "CENSUS") & (t["domain_desc"] == "TOTAL")
          & (t["unit_desc"] == unit)].dropna(subset=["v"])
    if extra is not None:
        t = t[extra(t)]
    out: dict = {}
    for (year, st), v in zip(zip(t["year"], t["state_fips_code"].str.zfill(2)), t["v"]):
        out.setdefault(int(year), {})[st] = float(v)
    return out


def _fill_withheld(published: dict, estimate: dict, state_total: dict) -> tuple[dict, list]:
    """Counties the Census withheld ("(D)") get a share of what their state total leaves over.

    ``estimate`` is a rough size per withheld county; it is scaled so the withheld counties of each state
    add up to (state total - published counties). Returns the filled values and the list of estimated FIPS.
    """
    values, estimated = dict(published), []
    by_state: dict = {}
    for f, w in estimate.items():
        if f not in published:
            by_state.setdefault(f[:2], {})[f] = max(float(w), 0.0)
    for st, rough in by_state.items():
        left = state_total.get(st)
        pub = sum(v for f, v in published.items() if f[:2] == st)
        size = sum(rough.values())
        if left is None or size <= 0:
            continue
        left -= pub
        if left <= 0:
            continue
        for f, w in rough.items():
            values[f] = round(left * w / size, 0)
            estimated.append(f)
    return values, sorted(estimated)


def _milk_cows(year_rows: pd.DataFrame, state_total: dict) -> tuple[dict, list]:
    """Census milk cows (head) per county; withheld counties estimated from their farms by herd size."""
    head = year_rows[(year_rows["domain_desc"] == "TOTAL") & (year_rows["unit_desc"] == "HEAD")]
    published = {f: v for f, v in zip(head["fips"], head["v"]) if np.isfinite(v)}
    # Farms per herd-size class are always published, even where the head count is withheld.
    cls = year_rows[(year_rows["domain_desc"] == "INVENTORY OF MILK COWS")].copy()
    cls["klass"] = cls["domaincat_desc"].str.extract(r"(\(.*\))", expand=False)
    ops = cls[cls["unit_desc"] == "OPERATIONS"].pivot_table(index="fips", columns="klass", values="v", aggfunc="first")
    hd = cls[cls["unit_desc"] == "HEAD"].pivot_table(index="fips", columns="klass", values="v", aggfunc="first")
    rough = {}
    for f, row in ops.iterrows():
        n = 0.0
        for k, typical in HERD_CLASSES.items():
            farms = row.get(k)
            if farms is None or not np.isfinite(farms) or farms <= 0:
                continue
            h = hd.at[f, k] if (f in hd.index and k in hd.columns) else np.nan
            n += h if np.isfinite(h) else farms * typical
        rough[f] = n
    return _fill_withheld(published, rough, state_total)


def county_layers(problems: list) -> dict:
    """Per county (5-digit FIPS): silage acres and milk cows (Census years), and season weather by year.

    Only Census rows are used for the census maps: the files also hold farm counts ("operations"),
    irrigated-only acres and January survey estimates, which must not be mixed in. Counties the Census
    withheld to protect individual farms are estimated and listed under ``estimated``.
    """
    out = {"names": {}, "silage": {}, "milk_cows": {}, "weather": {}, "census_years": [],
           "estimated": {"silage": {}, "milk_cows": {}}, "farms": {}}
    try:
        cows = _qs("milk_cow_inventory_county_2015_2025.csv")
        cows = cows[(cows["agg_level_desc"] == "COUNTY") & (cows["county_code"] != "998") & (cows["source_desc"] == "CENSUS")]
        cows["fips"] = _fips(cows)
        cow_tot = _census_state_totals("milk_cow_inventory_state_2015_2025.csv", "HEAD")
        for year, g in cows.groupby("year"):
            vals, est = _milk_cows(g, cow_tot.get(int(year), {}))
            out["milk_cows"][int(year)] = vals
            out["estimated"]["milk_cows"][int(year)] = est
            farms = g[(g["domain_desc"] == "TOTAL") & (g["unit_desc"] == "OPERATIONS")].dropna(subset=["v"])
            out["farms"][int(year)] = {f: int(v) for f, v in zip(farms["fips"], farms["v"])}
        for f, c, s in zip(cows["fips"], cows["county_name"], cows["state_alpha"]):
            out["names"].setdefault(f, f"{c.title()}, {s}")

        sil = _qs("corn_silage_harvested_acres_county_2015_2025.csv")
        sil = sil[(sil["agg_level_desc"] == "COUNTY") & (sil["county_code"] != "998") & (sil["source_desc"] == "CENSUS")
                  & (sil["domain_desc"] == "TOTAL") & (sil["util_practice_desc"] == "SILAGE")
                  & (sil["prodn_practice_desc"] == "ALL PRODUCTION PRACTICES")]
        sil["fips"] = _fips(sil)
        sil_tot = _census_state_totals("corn_silage_harvested_acres_state_2015_2025.csv", "ACRES",
                                       lambda t: (t["util_practice_desc"] == "SILAGE")
                                       & (t["prodn_practice_desc"] == "ALL PRODUCTION PRACTICES")
                                       & (t["statisticcat_desc"] == "AREA HARVESTED"))
        for year, g in sil.groupby("year"):
            published = {f: float(v) for f, v in zip(g["fips"], g["v"]) if np.isfinite(v)}
            # Withheld counties: share the state's leftover acres in proportion to their dairy herd (silage is cow feed).
            withheld = set(g.loc[g["v"].isna(), "fips"])
            herd = out["milk_cows"].get(int(year), {})
            rough = {f: max(herd.get(f, 0.0), 25.0) for f in withheld}
            vals, est = _fill_withheld(published, rough, sil_tot.get(int(year), {}))
            out["silage"][int(year)] = vals
            out["estimated"]["silage"][int(year)] = est
            for f, c, s in zip(g["fips"], g["county_name"], g["state_alpha"]):
                out["names"].setdefault(f, f"{c.title()}, {s}")
        grain = _qs("corn_grain_harvested_acres_county_2015_2025.csv")
        grain = grain[(grain["agg_level_desc"] == "COUNTY") & (grain["county_code"] != "998") & (grain["source_desc"] == "CENSUS")
                      & (grain["domain_desc"] == "TOTAL") & (grain["prodn_practice_desc"] == "ALL PRODUCTION PRACTICES")].dropna(subset=["v"])
        grain["fips"] = _fips(grain)
        out["corn_grain"] = {int(y): {f: float(v) for f, v in zip(g["fips"], g["v"])} for y, g in grain.groupby("year")}
        out["census_years"] = sorted(set(out["silage"]) & set(out["milk_cows"]))
    except Exception as error:  # noqa: BLE001
        problems.append(f"county acres/cows: {error}")
    try:
        frames = []
        for path in sorted((REPO / "data" / "weather" / "county_season").glob("county_season_*.csv")):
            frames.append(pd.read_csv(path, dtype={"fips": str}))
        w = pd.concat(frames)
        w["fips"] = w["fips"].str.zfill(5)
        base = w[w["year"] <= 2025].groupby("fips")[["prcp_may_sep_mm", "gdd_may_sep_c"]].mean()
        w = w.merge(base.add_suffix("_normal"), left_on="fips", right_index=True, how="left")
        out["rain_normal"] = {f: int(round(v)) for f, v in base["prcp_may_sep_mm"].items() if np.isfinite(v)}   # mm, May-Sep
        w["rain_vs_normal"] = w["prcp_may_sep_mm"] / w["prcp_may_sep_mm_normal"] - 1
        w["heat_vs_normal"] = w["gdd_may_sep_c"] / w["gdd_may_sep_c_normal"] - 1
        w = w[w["year"] >= 2016]
        for year, g in w.groupby("year"):
            out["weather"][int(year)] = {f: [_r(a, 3), _r(b, 3), _i(c)] for f, a, b, c in
                                         zip(g["fips"], g["rain_vs_normal"], g["heat_vs_normal"], g["first_fall_frost_doy"])}
        for f, c, s in zip(w["fips"], w["county"], w["state"]):
            out["names"].setdefault(f, f"{c}, {s}")
    except Exception as error:  # noqa: BLE001
        problems.append(f"county weather: {error}")
    return out


def _r(v, n):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


def _i(v):
    return None if v is None or not np.isfinite(v) else int(v)


def state_money(problems: list) -> dict:
    """Per state and year: corn-for-grain production (bu), marketing-year price ($/bu) and their product."""
    out = {}
    try:
        p = _qs("corn_production_state_2015_2025.csv")
        p = p[(p["agg_level_desc"] == "STATE") & (p["domain_desc"] == "TOTAL") & (p["util_practice_desc"] == "GRAIN")
              & (p["prodn_practice_desc"] == "ALL PRODUCTION PRACTICES") & (p["statisticcat_desc"] == "PRODUCTION")
              & (p["unit_desc"] == "BU") & (p["source_desc"] == "SURVEY") & (p["reference_period_desc"] == "YEAR")]
        price = _qs("corn_prices_received_state_2015_2025.csv")
        price = price[(price["agg_level_desc"] == "STATE") & (price["reference_period_desc"] == "MARKETING YEAR")]
        m = p[["state_alpha", "year", "v"]].rename(columns={"v": "bushels"}).merge(
            price[["state_alpha", "year", "v"]].rename(columns={"v": "price"}), on=["state_alpha", "year"], how="outer")
        m = m.dropna(subset=["year"]).drop_duplicates(["state_alpha", "year"])
        m["value"] = m["bushels"] * m["price"]
        for _, r in m.iterrows():
            out.setdefault(r["state_alpha"], {})[int(r["year"])] = {
                "bushels": _r(r["bushels"], 0), "price": _r(r["price"], 2), "value": _r(r["value"], 0)}
    except Exception as error:  # noqa: BLE001
        problems.append(f"crop value: {error}")
    return out


def harvest_timing(problems: list) -> dict:
    """Silage harvest progress by state: the 2026 curve, the 5-year average curve, and the typical 50% date."""
    out = {}
    try:
        t = _qs("corn_silage_harvest_progress_weekly_state_2000_2026.csv")
        t = t[t["agg_level_desc"] == "STATE"].dropna(subset=["v"])
        t["doy"] = pd.to_datetime(t["week_ending"]).dt.day_of_year
        latest = int(t["year"].max())
        for st, g in t.groupby("state_alpha"):
            def half(gy):
                gy = gy.sort_values("doy")
                hit = gy[gy["v"] >= 50]
                if hit.empty:
                    return None
                after = hit.iloc[0]
                before = gy[gy["doy"] < after["doy"]].tail(1)
                if before.empty or after["v"] == before.iloc[0]["v"]:
                    return int(after["doy"])
                b = before.iloc[0]
                return int(round(b["doy"] + (50 - b["v"]) * (after["doy"] - b["doy"]) / (after["v"] - b["v"])))  # noqa: RUF046 (numpy float)
            past = [half(gy) for y, gy in g.groupby("year") if latest - 5 <= y < latest]
            past = [d for d in past if d is not None]
            avg = g[(g["year"] >= latest - 5) & (g["year"] < latest)].assign(wk=lambda d: (d["doy"] // 7) * 7)
            avg_curve = avg.groupby("wk")["v"].mean().round(0)
            now = g[g["year"] == latest].sort_values("doy")
            out[st] = {"typical_half_doy": int(round(np.mean(past))) if past else None, "years_used": len(past),  # noqa: RUF046
                       "latest_year": latest, "half_doy": half(now) if len(now) else None,
                       "latest_pct": _i(now["v"].iloc[-1]) if len(now) else None,
                       "latest_week": now["week_ending"].iloc[-1] if len(now) else None,
                       "curve": [[int(d), int(v)] for d, v in zip(now["doy"], now["v"])],
                       "avg_curve": [[int(d), int(v)] for d, v in avg_curve.items()]}
    except Exception as error:  # noqa: BLE001
        problems.append(f"harvest timing: {error}")
    return out


MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def milk_prices(problems: list) -> dict:
    """Monthly price farmers received for milk ($/cwt) by state, 2016 on: {state: [["2026-09", 18.3], ...]}."""
    out = {}
    try:
        t = _qs("milk_price_received_state_2000_2026.csv")
        t = t[(t["agg_level_desc"] == "STATE") & (t["short_desc"] == "MILK - PRICE RECEIVED, MEASURED IN $ / CWT")
              & t["reference_period_desc"].isin(MONTHS) & (t["year"] >= 2016)].dropna(subset=["v"])
        t["ym"] = t["year"].astype(int).astype(str) + "-" + (t["reference_period_desc"].map(MONTHS.index) + 1).astype(str).str.zfill(2)
        for st, g in t.sort_values("ym").groupby("state_alpha"):
            out[st] = [[ym, float(v)] for ym, v in zip(g["ym"], g["v"])]
    except Exception as error:  # noqa: BLE001
        problems.append(f"milk prices: {error}")
    return out


def satellite(problems: list, history: pd.DataFrame) -> dict:
    """Where the satellite work looks: sample states, labeled test fields, and sample areas once pulled."""
    out = {"sample_states": [], "points": [], "note": ""}
    try:
        h = history[(history["year"] == 2024) & history["silage"].notna()].sort_values("silage", ascending=False)
        out["sample_states"] = h["state"].head(15).tolist()
        out["note"] = ("Sample states follow kernelag.state_sample: the 15 states with the most corn-silage acres "
                       "in 2024.")
    except Exception as error:  # noqa: BLE001
        problems.append(f"sample states: {error}")
    gpkg = REPO / "BARC_Corn.2021-2023.gpkg"
    if gpkg.exists():
        try:
            import geopandas as gpd
            g = gpd.read_file(gpkg).to_crs(5070)
            c = g.geometry.centroid.to_crs(4326)
            out["points"].append({"label": "Test fields (MD)", "count": len(g),
                                  "lon": round(float(c.x.mean()), 4), "lat": round(float(c.y.mean()), 4),
                                  "detail": f"Beltsville, Maryland (BARC): {len(g)} fields with known silage/grain answers, 2021-2023, used to test the satellite field model"})
        except Exception as error:  # noqa: BLE001
            problems.append(f"BARC fields: {type(error).__name__} (install geopandas to show them)")
    summary = REPO / "data" / "samples" / "sample_summary.csv"
    if summary.exists():
        try:
            out["sample_summary"] = pd.read_csv(summary).to_dict(orient="records")
        except Exception as error:  # noqa: BLE001
            problems.append(f"sample summary: {error}")
    return out


def build(history: pd.DataFrame) -> dict:
    problems: list = []
    return {"county": county_layers(problems), "money": state_money(problems), "harvest": harvest_timing(problems),
            "milk": milk_prices(problems),
            "satellite": satellite(problems, history), "problems": problems}


if __name__ == "__main__":
    import json
    import time

    from board.sources import state_history
    t = time.time()
    d = build(state_history())
    print(round(time.time() - t, 1), "s", d["problems"])
    print({k: len(v) for k, v in d["county"].items()}, len(json.dumps(d)) // 1024, "KB")
    print(d["county"]["census_years"], list(d["county"]["weather"])[:3])
    print(d["harvest"].get("WI", {}).get("typical_half_doy"), d["harvest"].get("TX", {}).get("typical_half_doy"))
    print(d["money"].get("IA", {}).get(2024), d["satellite"])
