"""A fixed sample of cornfields per state, reused every year, for the state acreage signal.

Why a fixed sample: the field model is biased (it calls some grain fields silage), so the level
of its "silage-like" share cannot be trusted. Its change from one year to the next on the SAME
areas can, because a constant bias cancels. So each state gets a set of 10 km sample areas chosen
once, and every year we look at whichever fields in those areas grew corn that year.

How areas are chosen: with probability proportional to their corn acres (averaged over the
years), by systematic sampling with a fixed random seed. Corn-heavy areas are therefore more
likely to be drawn, and each drawn area then counts equally (see ``kernelag.state_signal``).

Input: NASS Crop Sequence Boundaries 2018-2025 (``kernelag.csb``); a field counts as corn in a
year when its Cropland Data Layer code is corn (1) or a corn double crop (225, 226, 228, 237, 241).
States: the ones with the most corn-silage acres in 2024 (from the organizers' Quick Stats file).

Outputs:
    data/samples/corn_<state fips>.parquet   one row per sampled field and corn year:
        field_id, year, cell, cell_size_acres, state_fips, county_fips, acres, geometry
    data/samples/sample_summary.csv          areas and fields per state and year

Run:
    python -m kernelag.state_sample                    choose the sample (minutes)
    python -m kernelag.state_sample --pull --workers 6 pull Sentinel-2 series for it, states in parallel
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from kernelag.paths import data_dir, record_in_manifest

LAYER = "national1825"
YEARS = list(range(2019, 2026))
CORN_CODES = [1, 225, 226, 228, 237, 241]
CELL_M = 10_000            # sample areas are 10 km squares on the file's equal-area grid
MIN_ACRES = 5.0            # about 2 hectares, the same floor as the training parcels
SEED = 20261115
LAST_YEAR_FOR_CHOOSING_STATES = 2024   # never 2025: that is the scoring year


def silage_states(n_states: int) -> pd.DataFrame:
    """The ``n_states`` states with the most final corn-silage acres in 2024: state, state_fips, acres."""
    from kernelag.nass import load_kit, tidy_state

    state = tidy_state(load_kit())
    rows = state[(state["year"] == LAST_YEAR_FOR_CHOOSING_STATES) & (state["series"] == "silage")
                 & (state["period"] == "final")]
    top = rows.sort_values("acres", ascending=False).head(n_states)
    return pd.DataFrame({"state": top["state"].to_numpy(),
                         "state_fips": top["state_ansi"].astype(str).str.zfill(2).to_numpy(),
                         "silage_acres_2024": top["acres"].to_numpy()})


def corn_filter(state_fips: list[str]) -> str:
    """SQL filter: fields in these states that were corn in at least one of the years."""
    states = ", ".join(f"'{s}'" for s in state_fips)
    codes = ", ".join(str(c) for c in CORN_CODES)
    any_year = " OR ".join(f"CDL{y} IN ({codes})" for y in YEARS)
    return f"STATEFIPS IN ({states}) AND CSBACRES >= {MIN_ACRES} AND ({any_year})"


def cell_of(x: pd.Series, y: pd.Series) -> pd.Series:
    return (x // CELL_M).astype(int).astype(str) + "_" + (y // CELL_M).astype(int).astype(str)


def corn_acres_by_cell(attributes: pd.DataFrame) -> pd.Series:
    """Mean yearly corn acres per cell: the size measure the sample is drawn on."""
    corn = np.column_stack([attributes[f"CDL{y}"].isin(CORN_CODES).to_numpy() for y in YEARS])
    yearly_mean_acres = attributes["CSBACRES"].to_numpy() * corn.mean(axis=1)
    return pd.Series(yearly_mean_acres).groupby(attributes["cell"].to_numpy()).sum()


def systematic_pps(sizes: pd.Series, n: int, rng: np.random.Generator) -> list[str]:
    """Draw ``n`` cells with probability proportional to size: random order, then equal steps."""
    sizes = sizes[sizes > 0]
    if len(sizes) <= n:
        return sizes.index.tolist()
    order = rng.permutation(len(sizes))
    names, cumulative = sizes.index.to_numpy()[order], np.cumsum(sizes.to_numpy()[order])
    step = cumulative[-1] / n
    points = rng.uniform(0, step) + step * np.arange(n)
    picked = names[np.searchsorted(cumulative, points)]
    return list(dict.fromkeys(picked))   # a cell larger than one step can be hit twice; keep it once


def long_by_corn_year(fields) -> "pd.DataFrame":
    """One row per field and year in which the field was corn."""
    parts = []
    for year in YEARS:
        part = fields[fields[f"CDL{year}"].isin(CORN_CODES)]
        parts.append(part[["field_id", "cell", "cell_size_acres", "state_fips", "county_fips", "acres",
                           "geometry"]].assign(year=year))
    return pd.concat(parts, ignore_index=True)


def choose_sample(dataset: Path, states: pd.DataFrame, cells_per_state: int, layer: str = LAYER) -> pd.DataFrame:
    """Choose the areas, read their field outlines, write one file per state. Returns the summary."""
    import pyogrio

    out = data_dir() / "samples"
    out.mkdir(parents=True, exist_ok=True)
    where = corn_filter(states["state_fips"].tolist())
    columns = ["CSBID", "CSBACRES", "STATEFIPS", "CNTYFIPS", "INSIDE_X", "INSIDE_Y"] + [f"CDL{y}" for y in YEARS]
    print("reading field attributes (one pass over the national file)...", flush=True)
    attributes = pyogrio.read_dataframe(dataset, layer=layer, columns=columns, where=where, read_geometry=False)
    attributes["cell"] = cell_of(attributes["INSIDE_X"], attributes["INSIDE_Y"])
    print(f"  {len(attributes)} fields that grew corn in at least one year", flush=True)

    rng = np.random.default_rng(SEED)
    summary = []
    for state in states.itertuples():
        in_state = attributes[attributes["STATEFIPS"] == state.state_fips]
        sizes = corn_acres_by_cell(in_state)
        chosen = systematic_pps(sizes, cells_per_state, rng)
        parts = []
        for cell in chosen:
            cx, cy = (int(v) * CELL_M for v in cell.split("_"))
            fields = pyogrio.read_dataframe(dataset, layer=layer, columns=columns, where=where,
                                            bbox=(cx, cy, cx + CELL_M, cy + CELL_M))
            fields = fields[(cell_of(fields["INSIDE_X"], fields["INSIDE_Y"]) == cell)
                            & (fields["STATEFIPS"] == state.state_fips)]
            fields = fields.rename(columns={"CSBID": "field_id", "CSBACRES": "acres",
                                            "STATEFIPS": "state_fips", "CNTYFIPS": "county_fips"})
            fields["field_id"] = fields["field_id"].astype(str)
            parts.append(fields.assign(cell=cell, cell_size_acres=round(float(sizes[cell]), 1)))
        table = long_by_corn_year(pd.concat(parts, ignore_index=True))
        target = out / f"corn_{state.state_fips}.parquet"
        table.to_parquet(target)
        record_in_manifest(target, "https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/")
        per_year = table.groupby("year").size()
        summary.append({"state": state.state, "state_fips": state.state_fips,
                        "cells_in_state": int((sizes > 0).sum()), "cells_sampled": len(chosen),
                        "fields": table["field_id"].nunique(),
                        **{f"corn_fields_{y}": int(per_year.get(y, 0)) for y in YEARS}})
        print(f"  {state.state}: {len(chosen)} of {int((sizes > 0).sum())} areas, "
              f"{table['field_id'].nunique()} fields, {len(table)} field-years", flush=True)
    summary = pd.DataFrame(summary)
    summary.to_csv(out / "sample_summary.csv", index=False, lineterminator="\n")
    return summary


def pull_series(workers: int) -> None:
    """Pull Sentinel-2 series for every state file, several states at once. Safe to rerun: it resumes."""
    samples = data_dir() / "samples"
    logs = samples / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    files = sorted(samples.glob("corn_*.parquet"))
    environment = {**os.environ, "KERNEL_NO_MANIFEST": "1"}

    def run(path: Path) -> str:
        log = logs / f"{path.stem}.log"
        with open(log, "w") as handle:
            code = subprocess.run([sys.executable, "-m", "kernelag.s2_series", "--fields", str(path), "--cells", "0"],
                                  stdout=handle, stderr=subprocess.STDOUT, env=environment).returncode
        done = len(list((data_dir() / "s2_series" / path.stem).glob("*.csv")))
        return f"{path.stem}: exit {code}, {done} area-years on disk (log: {log})"

    print(f"pulling {len(files)} states with {workers} at a time...", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for line in pool.map(run, files):
            print(" ", line, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--states", type=int, default=15, help="how many top silage states to sample")
    parser.add_argument("--cells", type=int, default=10, help="sample areas per state")
    parser.add_argument("--pull", action="store_true", help="pull satellite series for the chosen sample")
    parser.add_argument("--workers", type=int, default=6, help="states pulled at the same time")
    args = parser.parse_args()

    if args.pull:
        pull_series(args.workers)
        return
    from kernelag.csb import download, unpack

    states = silage_states(args.states)
    print(states.to_string(index=False))
    summary = choose_sample(unpack(download()), states, args.cells)
    pd.set_option("display.width", 220)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
