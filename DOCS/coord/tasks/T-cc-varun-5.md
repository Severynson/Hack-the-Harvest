# T-cc-varun-5 Labeled Quebec maize parcels and per-field Sentinel-2 series
Paths: kernelag/quebec.py, kernelag/s2_series.py, kernelag/features.py, tests/test_features.py, tests/test_quebec.py, DOCS/DECISIONS.md, data/DATA_MANIFEST.tsv
Depends on: T-cc-varun-4
Done when: `python -m kernelag.quebec --year 2023` writes the labeled grain and silage parcels, `python -m kernelag.s2_series` writes a per-field, per-date table for a pilot cell, and the tests pass
Status: claimed by cc-varun
