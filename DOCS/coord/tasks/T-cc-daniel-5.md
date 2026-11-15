# T-cc-daniel-5 Own state acreage models without NASS's grain forecast; FSA parser; Landsat and Sentinel-1 pullers; field feature tests
Paths: kernelag/fsa.py, kernelag/landsat_series.py, kernelag/s1_series.py, kernelag/multisensor.py, kernelag/s2_series.py, tests/test_fsa.py, tests/test_landsat_series.py, tests/test_s1_series.py, tests/test_multisensor.py, test_models/ownModels/grain/, test_models/ownModels/silage/, test_models/ownModels/tierB/, test_models/featureTests/, data/fsa/, data/labels/qc_regions_2023.parquet, data/s2_series/qc_regions_2023/, data/landsat_series/, data/s1_series/, data/models/landsat_s2_calibration.json, data/DATA_MANIFEST.tsv, DOCS/DECISIONS.md
Depends on: none
Done when: `pytest tests` passes and every test_models folder above passes its own tests; each model folder's run.py reproduces its out/summary.csv; independent audits reproduce the selected models' numbers
Status: done
