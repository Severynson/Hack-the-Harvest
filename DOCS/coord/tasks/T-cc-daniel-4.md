# T-cc-daniel-4 Trained gradient-boosted acreage models; model folder renamed to danielModel
Paths: test_models/danielModel/ (was test_models/model/), test_models/testModel/ (the earlier baseline, moved there by Daniel), scripts/pull_data.py (one comment)
Depends on: T-cc-daniel-3
Done when: `python3 test_models/danielModel/train_gbt.py` trains the silage and grain models, writes their backtest (test years up to 2024), saved models and the 2026 forecast with ranges into `test_models/danielModel/out/`, and the held-out 2025 score is written once
Status: done
