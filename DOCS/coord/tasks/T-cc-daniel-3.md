# T-cc-daniel-3 State and US grain and silage acreage model on the long history
Paths: test_models/model/, scripts/pull_data.py (five more Quick Stats series), data/Quickstats Data/ (the new `*_state_2000_2026` files), data/README.md, data/DATA_MANIFEST.tsv (rows for the new files)
Depends on: T-cc-daniel-2
Done when: `python3 test_models/model/build_panel.py` and `python3 test_models/model/model.py` run from a clean checkout and write the backtest (test years up to 2024), the held-out 2025 score and the 2026 state and US forecast for grain and silage acres with intervals into `test_models/model/out/`
Status: claimed by cc-daniel
