# danielModel

Throwaway acreage baselines. Standard library only; no install needed. Clean code goes in the repo root.

## state_acres.py: state grain and silage acres from the organizers' Quick Stats file

```
python3 -I test_models/danielModel/state_acres.py [path/to/corn_grain_silage_acres.csv]
```

- **Data:** `jupyter/workspace/02_QuickStats/corn_grain_silage_acres_2012_2025.csv` (NASS survey, state totals; not in git).
- **Truth:** NASS's final state acres, harvested for grain and for silage.
- **Inputs:** only what NASS had published by mid-November of the same year, plus last year's finals.
- **Scoring:** expanding window, each year predicted from earlier years only. Results are in `out/state_metrics.json`.

## us_acres.py: US totals from the research notes

```
python3 -I test_models/danielModel/build_dataset.py   # parse DOCS/research/nass_ops.md tables into data/*.csv
python3 -I test_models/danielModel/us_acres.py        # backtest 2010-2025, write out/metrics.json and out/forecast_2026.csv
```

- **Data:** NASS national history 2000-2025 and the 2026 June and November forecasts, parsed from the notes; nothing typed by hand.

## Limits

- The state file has state totals for 2013-2016, 2018-2021 and 2023-2025 only. 2017 and 2022 are county-level census rows, so 2018 and 2023 have no previous year and are not scored.
- The state file stops at 2025, so there is no 2026 state forecast. Re-run the organizers' downloader with `--end-year 2026` and the script forecasts the open year by itself.
- National silage truth mixes vintages: final for 2000-2022, revised for 2023-2024, first January estimate for 2025.
- Each forecast uses the candidate with the lowest backtest error out of a handful; read small gaps between candidates as noise.
- No satellite, weather, price, FSA or RMA input yet. Those arrive with the data harvest.
