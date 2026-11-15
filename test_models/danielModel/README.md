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

# severynModel - caveman

- We only have BARC_Corn.2021-2023.gpkg data with labels silage VS grain for a particular field on a particular year provided by the hackathon organizers. But we can and should add more open source data.
- We can try to construct heuristic model, which is going to predict grain/silage based on the length of the period during which it was growing, and when it was harvest.
  E.g. Planted 60th day of the year, harvest - 120th day of the year. So it was growing for 120-60=60 days.
- And silage is always harvest earlier than grains. So if we observe that in the region with ~the same temperature portion of farms harvest ~over 60 days, but rest of the farms harvest ~over 60 days (let's say we take +- 15-10 days around the textbook date when grain/silage was supposed to be harvest in a rarticular region if it is silage VS grain). And we can iteratively, with ablation study change parameters of our heuristic, and evaluate its accuracy on the known labels for Maryland fields.
- We won't spot the exact moment when corn was planted from satelite images. But we can spot when it begins to grow. Especially if we pull data NDTI and NDVI for historical period with certain frequency for the time of the year which is potentially a season between planting and harvesting the corn. And we can see how these values (NDTI and NDVI) are going to grow steadily until dropping at one moment after the harvest. And the moment when a steady growth of these numbers begin - with noise (ups and downs), but still steadily growing over time - we can capture this moment as a proxy for the moment it was planted (e.g. 15 days after it was planted). So this way we could extract estimated date of planting and almost accurate date of harvest. This way we can get a period during which corn was growing, and based on it estimate did is grow as long as typical silage for a region with its weather and climate, or or a typical grain based on heuristic rules you must find by doing ablation study.

# severynModel - smartman

- We only have BARC_Corn.2021-2023.gpkg data with labels silage VS grain for a particular field on a particular year provided by the hackathon organizers. But we can and should add more open source data.
- We want to try the time series model which will primarily track:
  weather in the region
