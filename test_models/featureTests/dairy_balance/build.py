"""Field-feature contract for the dairy balance group: it records why no field-level feature is built.

The dairy feed-demand balance is a county quantity (milk cows per corn acre x the state's silage acres per
cow; see run.py and README.md). None of the three field datasets can carry it as a field feature:

    quebec_maize_2023, qc_regions_2023   no Quebec dairy herd or corn area by region is in the repository
    barc_2021_2023                       every field is in one county (Prince George's, MD), so the prior is
                                         one number per year for all fields: it cannot rank them

So this writes the contract files with no pre-registered features and an UNCOMPUTED reason per dataset; the
shared harness (test_models/featureTests/harness.py) then reports the group as not computed instead of
skipping it silently. Nothing here reads labels.

Outputs (test_models/featureTests/dairy_balance/out/):
    features.csv   header only: dataset, field_id, year
    meta.json      {"group": "dairy_balance", "features": [], "rule_column": null, ..., "uncomputed": {...}}

Run from the repository root (idempotent):
    .venv/Scripts/python.exe test_models/featureTests/dairy_balance/build.py [--datasets ...]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DATASETS = ["quebec_maize_2023", "qc_regions_2023", "barc_2021_2023"]
QUEBEC_REASON = ("county dairy balance needs dairy cows and corn area by region; the repository has none for "
                 "Quebec (would need Statistics Canada Census of Agriculture 2021 by census division plus the "
                 "division boundaries); see README")
REASONS = {
    "quebec_maize_2023": QUEBEC_REASON,
    "qc_regions_2023": QUEBEC_REASON,
    "barc_2021_2023": "all 34 fields lie in one county (Prince George's, MD, FIPS 24033): the county prior is a "
                      "single value per year for every field, so it carries no field-level information "
                      "(county_prior.csv has it for 2023 only; milk cows are withheld for 2021-2022)",
}


def write_contract(out: Path, datasets: list[str]) -> dict:
    """Write the header-only features.csv and meta.json; return the meta dictionary."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "features.csv").write_text("dataset,field_id,year\n", encoding="utf-8")
    meta = {
        "group": "dairy_balance",
        "features": [],
        "rule_column": None,
        "description": "County dairy feed-demand balance (DOCS/research/dairy_prior.md 8.2). Tested at county "
                       "and state level in run.py; not a field feature for any labelled dataset.",
        "datasets_built": [],
        "uncomputed": {name: REASONS[name] for name in datasets},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--datasets", nargs="+", default=DATASETS, choices=DATASETS)
    args = parser.parse_args()
    meta = write_contract(OUT, args.datasets)
    for name, reason in meta["uncomputed"].items():
        print(f"UNCOMPUTED {name}: {reason}")
    print(f"wrote {OUT / 'meta.json'} and {OUT / 'features.csv'}")


if __name__ == "__main__":
    main()
