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


def county_layers(problems: list) -> dict:
    """Per county (5-digit FIPS): silage acres and milk cows (Census years), and season weather by year."""
    out = {"names": {}, "silage": {}, "milk_cows": {}, "weather": {}, "census_years": []}
    try:
        for key, name, util in [("silage", "corn_silage_harvested_acres_county_2015_2025.csv", "SILAGE"),
                                ("milk_cows", "milk_cow_inventory_county_2015_2025.csv", None)]:
            t = _qs(name)
            t = t[(t["agg_level_desc"] == "COUNTY") & (t["county_code"] != "998") & (t["domain_desc"] == "TOTAL")]
            if util:
                t = t[t["util_practice_desc"] == util]
            t = t.dropna(subset=["v"])
            t["fips"] = t["state_fips_code"].str.zfill(2) + t["county_code"].str.zfill(3)
            for year, g in t.groupby("year"):
                if len(g) > 1000:                      # Census years: near-complete county coverage
                    out[key][int(year)] = {f: float(v) for f, v in zip(g["fips"], g["v"])}
            for f, c, s in zip(t["fips"], t["county_name"], t["state_alpha"]):
                out["names"].setdefault(f, f"{c.title()}, {s}")
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
