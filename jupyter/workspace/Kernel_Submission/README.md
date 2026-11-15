# Kernel submission: corn for grain and silage acres, by state and US

**Headline, as of 15 Nov 2026** (top of the notebook, read from `data/kernel_own/`):

- Grain **A-G9** (Tier A, no current-year NASS data): 88.75M acres, 80% range 87.28M to 90.24M.
- Silage **B-S6** (Tier B, uses NASS's yield forecast but not its acreage forecast): 6.26M acres, 80% range 6.10M to 6.66M.
- Comparisons only: NASS's November grain forecast, 88.51M (87.27M to 89.76M), and the team's previous Tier C pair (that forecast passed through + smoothed chopping silage SC, 6.26M, 5.95M to 6.59M), which fills the notebook from "Comparison: Method" down.
- Drought scenario A-S7 (Tier A, Drought Monitor D2+ chopping): silage 6.43M (6.25M to 6.90M). Inflated by drought over largely irrigated Nebraska corn; a scenario, never the headline.
- `data/kernel_own/`: saved results copied from `test_models/variations/` in the team repository: `grain_forecast_2026.csv`, `grain_backtest_summary.csv`, `grain_intervals.json` (interval coverage), `silage_forecast_2026_states.csv`, `silage_forecast_2026_us.csv`, `silage_backtest_summary.csv`, `silage_interval_coverage.csv`, `scorecard_2017_2024_and_2025.csv`, `field_holdout_2025.csv`, `field_maryland.csv` (field model, proxy labels), `fade_rule_comparison.csv`.

Open `kernel_deliverable.ipynb` and run all cells (about a minute, offline). It is saved with its outputs.

- `kernelag/`: the team package (copied from the repository by `scripts/build_submission.sh`).
- `data/`: the NASS Quick Stats extracts the deliverable needs, and `noise_floor_results.json`.
- `data/models/`: what the notebook writes: `deliverable_2026.csv` (state and US acres, 80% and 90% intervals), `deliverable_comparison.csv` (2017–2025 per state vs NASS final), `deliverable_summary.json`.
- Truth file: `../02_QuickStats/corn_grain_silage_acres_2012_2025.csv` (organizer).

Needs Python 3.11+ with numpy, pandas and requests (requests is imported but not used offline).
Rebuild from the repository: `NB_PYTHON=<python with nbconvert> bash scripts/build_submission.sh`.
