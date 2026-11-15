"""Throwaway scan: do RMA insured-silage acres or "planted minus NASS grain forecast" predict state silage?

Standard library only. Scores years up to 2024; the scoring year 2025 is skipped.
Run from the repo root: python3 -I test_models/manrajModel/signal_scan.py
"""
import collections
import csv
import glob
import gzip
import math

KIT = "jupyter/workspace/02_QuickStats/corn_grain_silage_acres_2012_2025.csv"
TEAM = "data/Quickstats Data/{}_state_2015_2025.csv"
SERIES = {"CORN - ACRES PLANTED": "planted", "CORN, GRAIN - ACRES HARVESTED": "grain",
          "CORN, SILAGE - ACRES HARVESTED": "silage"}
LAST_YEAR = 2024


def opened(path):
    return gzip.open(path, "rt", newline="") if path.endswith(".gz") else open(path, newline="")


def number(text):
    try:
        return float(text.replace(",", "")) or None
    except ValueError:
        return None


acres = collections.defaultdict(dict)          # (state, year) -> {"series|period": acres}
for r in csv.DictReader(open(KIT)):
    if (r["aggregation_level"], r["source"], r["domain"]) == ("STATE", "SURVEY", "TOTAL") \
            and r["short_description"] in SERIES and r["state_name"] != "OTHER STATES" and number(r["value"]):
        acres[(r["state_name"], int(r["year"]))][SERIES[r["short_description"]] + "|" + r["reference_period"]] = number(r["value"])
for stem in ["corn_planted_acres", "corn_grain_harvested_acres", "corn_silage_harvested_acres"]:
    for r in csv.DictReader(open(TEAM.format(stem))):
        if (r["source_desc"], r["domain_desc"]) == ("SURVEY", "TOTAL") and r["short_desc"] in SERIES \
                and r["state_name"] != "OTHER STATES" and number(r["Value"]):
            acres[(r["state_name"], int(r["year"]))].setdefault(
                SERIES[r["short_desc"]] + "|" + r["reference_period_desc"], number(r["Value"]))

rma = collections.defaultdict(float)           # (state, year) -> insured silage acres (type 026)
for path in sorted(glob.glob("data/rma/insured_by_type_corn/*")):
    for r in csv.DictReader(opened(path)):
        if r["reporting_level_type"].strip() == "Acres" and r["type_code"] == "026":
            rma[(r["state_name"].strip().upper(), int(r["commodity_year"]))] += float(r["net_reporting_level_amount"] or 0)


def first(d, series, periods):
    return next((d[f"{series}|{p}"] for p in periods if f"{series}|{p}" in d), None)


rows = []
for (state, year), d in acres.items():
    p = acres.get((state, year - 1), {})
    if year > LAST_YEAR or "silage|YEAR" not in d or "silage|YEAR" not in p:
        continue
    row = {"silage": d["silage|YEAR"], "last": p["silage|YEAR"], "rma": None, "resid": None}
    now, before = rma.get((state, year)), rma.get((state, year - 1))
    if now and before and before > 2000:
        row["rma"] = now / before
    planted = first(d, "planted", ["YEAR - OCT FORECAST", "YEAR - OCT ACREAGE", "YEAR - SEP FORECAST",
                                   "YEAR - AUG FORECAST", "YEAR - AUG ACREAGE", "YEAR - JUN ACREAGE"])
    grain = first(d, "grain", ["YEAR - NOV FORECAST", "YEAR - OCT FORECAST", "YEAR - SEP FORECAST",
                               "YEAR - AUG FORECAST", "YEAR - JUN ACREAGE"])
    if planted and grain and "planted|YEAR" in p and "grain|YEAR" in p:
        row["resid"] = max(p["silage|YEAR"] + (planted - grain) - (p["planted|YEAR"] - p["grain|YEAR"]), 0)
    rows.append(row)


def state_error(predict):
    miss = sum(abs((predict(r) or r["last"]) - r["silage"]) for r in rows)
    return round(100 * miss / sum(r["silage"] for r in rows), 1)


print(f"{len(rows)} state-years up to {LAST_YEAR}; share of silage acres put in the wrong state:")
print("  same as last year            ", state_error(lambda r: r["last"]))
print("  last year x RMA silage ratio ", state_error(lambda r: r["rma"] and r["last"] * r["rma"]))
print("  planted minus NASS grain     ", state_error(lambda r: r["resid"]))

pairs = [(math.log(r["rma"]), math.log(r["silage"] / r["last"]), r["last"]) for r in rows if r["rma"]]
total = sum(w for *_, w in pairs)
mx, my = sum(a * w for a, _, w in pairs) / total, sum(b * w for _, b, w in pairs) / total
corr = sum(w * (a - mx) * (b - my) for a, b, w in pairs) / math.sqrt(
    sum(w * (a - mx) ** 2 for a, _, w in pairs) * sum(w * (b - my) ** 2 for _, b, w in pairs))
print(f"  acre-weighted correlation, change in RMA silage vs change in NASS silage: {corr:.2f} (n={len(pairs)})")
