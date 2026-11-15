# Kernel submission: corn for grain and silage acres, by state and US

Open `kernel_deliverable.ipynb` and run all cells (about a minute, offline). It is saved with its outputs.

- `kernelag/`: the team package (copied from the repository by `scripts/build_submission.sh`).
- `data/`: the NASS Quick Stats extracts the deliverable needs, and `noise_floor_results.json`.
- `data/models/`: what the notebook writes: `deliverable_2026.csv` (state and US acres, 80% and 90% intervals), `deliverable_comparison.csv` (2017–2025 per state vs NASS final), `deliverable_summary.json`.
- Truth file: `../02_QuickStats/corn_grain_silage_acres_2012_2025.csv` (organizer).

Needs Python 3.11+ with numpy, pandas and requests (requests is imported but not used offline).
Rebuild from the repository: `NB_PYTHON=<python with nbconvert> bash scripts/build_submission.sh`.
