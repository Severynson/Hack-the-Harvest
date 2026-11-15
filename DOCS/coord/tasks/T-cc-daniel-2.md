# T-cc-daniel-2 Context data pulls and a tidy data folder
Paths: scripts/pull_data.py, data/ (drought, weather, rma, the `*_state_2000_2026` Quick Stats files, README.md, manifest rows), DOCS/DECISIONS.md (appended lines)
Depends on: none
Done when: `python3 scripts/pull_data.py all` fills `data/drought`, `data/weather`, `data/rma` and the in-season series in `data/Quickstats Data`; every file under `data/` is tracked, at most 30 MB and listed in `data/DATA_MANIFEST.tsv`; `data/README.md` says what each folder holds
Status: claimed by cc-daniel
