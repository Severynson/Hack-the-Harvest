# T-cc-daniel-2 Context data pulls and a tidy data folder
Paths: scripts/pull_data.py, data/, .gitignore (the data rules), DOCS/DECISIONS.md (one appended line)
Depends on: none
Done when: `python3 scripts/pull_data.py all` fills `data/drought`, `data/weather`, `data/rma` and `data/quickstats`; every file under `data/` is tracked, at most 5 MB and listed in `data/DATA_MANIFEST.tsv`; `data/README.md` says what each folder holds
Status: claimed by cc-daniel
