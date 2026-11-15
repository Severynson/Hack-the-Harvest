# Handoff to cc-varun: files the state forecast and the report are waiting for

From cc-manraj. Branch `Manraj` is rebased on `main` (f781eb5) and holds the merged state model.

## State
- `kernelag/state_model.py` on `Manraj` is my version with your satellite change ported in: `d_sat`, `sat_ratio`,
  the `reversion_plus_satellite` set, the unfitted `satellite_ratio` predictor and the `scope` column. With no
  `data/panel/state_satellite.csv` the satellite rows are left out, not filled.
- 2026 planted and grain acres per state now come from NASS's September and November text reports
  (`kernelag/nass_reports.py`), so the 2026 grain total is 88,506 thousand acres, not last year's figure.
- `kernelag/evaluate.py`: Maryland rates with 90% intervals, response time, earliness by as-of date.
- Scan of forage, milk price, drought and planted-minus-grain features: none beats `reversion_only` (13.1%) by more
  than 0.1 point (`test_models/manrajModel/silage_scan.py`). The satellite change is the only open lever.

## Needed from Keeboh
- `data/panel/state_satellite.csv` (even partial: sampled states and years that are finished).
- `data/models/field_model_*.csv` from the 20-cell Quebec fit (main holds the 1-cell fit: 10 of 15, 10 of 12).

## Resume commands
```
python -m kernelag.state_panel && python -m kernelag.state_model --forecast 2026
python -m kernelag.evaluate
```

## Risks
- `data/models/state_model_*.csv`, `data/panel/state_year.csv` and `data/nass/*.csv` are rebuilt by my modules; if you
  rebuild them too we conflict. Leave them to `Manraj`, or tell me and I take yours.
