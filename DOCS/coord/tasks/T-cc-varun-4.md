# T-cc-varun-4 Official-statistics table and the baselines to beat
Paths: kernelag/__init__.py, kernelag/paths.py, kernelag/nass.py, tests/test_nass.py, pyproject.toml, DOCS/DECISIONS.md
Depends on: T-cc-varun-3
Done when: `python -m kernelag.nass` writes the tidy state and county acreage tables and a baselines table (NASS forecast error, same-as-last-year error) for years up to 2024, and `pytest tests/test_nass.py` passes
Status: claimed by cc-varun
