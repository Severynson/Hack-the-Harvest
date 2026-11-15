#!/usr/bin/env bash
# Build the self-contained Keeboh submission folder: jupyter/workspace/Kernel_Submission/
# (Keeboh keeps only the workspace). Copies the kernelag package and the small input files the
# deliverable needs; the notebook runs `kernelag.deliverable --lean` from them, fully offline.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=jupyter/workspace/Kernel_Submission
QS="data/Quickstats Data"
rm -rf "$OUT/kernelag" "$OUT/data"
mkdir -p "$OUT/kernelag" "$OUT/data/nass" "$OUT/data/Quickstats Data"
cp kernelag/*.py "$OUT/kernelag/"
cp data/nass/corn_acres_state.csv "$OUT/data/nass/"
for f in corn_grain_yield_bu_acre_state_2015_2025 corn_silage_yield_tons_acre_state_2015_2025 \
         milk_cow_inventory_state_2015_2025 cattle_calves_inventory_state_2015_2025 \
         corn_prices_received_state_2015_2025 corn_silage_harvested_acres_state_2000_2026 \
         corn_grain_harvested_acres_state_2000_2026 corn_grain_yield_state_2000_2026; do
  cp "$QS/$f.csv" "$OUT/data/Quickstats Data/"
done
cp test_models/accuracy/noise_floor/results.json "$OUT/data/noise_floor_results.json"
# Notebook: written, then executed in place so Keeboh keeps its outputs. NB_PYTHON must have
# nbformat, nbconvert, ipykernel, numpy and pandas (default: the project .venv).
NB_PYTHON="${NB_PYTHON:-.venv/bin/python}"
"$NB_PYTHON" scripts/make_submission_notebook.py
(cd "$OUT" && "$NB_PYTHON" -m nbconvert --to notebook --execute --inplace kernel_deliverable.ipynb)
find "$OUT" -name __pycache__ -prune -exec rm -rf {} +
du -sh "$OUT" | cut -f1 | xargs echo "submission folder size:"
