# Finish-line delivery

State: rebased Manraj work onto current main; added offline field explorer, metric-generated talk track, evaluation corrections, public county/weather context and fixed XGBoost comparison. All 47 tests and changed-file Ruff checks pass. Firefox verifies field/year selection, keyboard map, weather, offline resources and mobile width.

Resume: `.venv/bin/python -m kernelag.report` and `.venv/bin/python -m kernelag.explorer` rebuild the demo; see README.md. If state satellite data arrive, run `.venv/bin/python -m kernelag.state_panel && .venv/bin/python -m kernelag.state_model --forecast 2026 && .venv/bin/python -m kernelag.report`. Do not overwrite or tune against the stored 2025 score. Earlier replays require dated satellite aggregates.

Risks: field score is uncalibrated; sample acres are not population estimates. CNN/hybrid, field soil/radar/dairy joins and national transfer remain unfinished. The longer-history state candidate improves common-year error only 0.34 points (two SE 0.781); no replacement is supported by that comparison. The latest fetched main has no `data/panel/state_satellite.csv` or state sample series.
