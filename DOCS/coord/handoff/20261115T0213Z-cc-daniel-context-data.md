# Handoff to cc-varun and cc-manraj: context data is in `data/`, tracked in git

From cc-daniel, 2026-11-15. Details and column notes are in `data/README.md`.

## State
- New public data, 2000 to 2026, all on `main`:
  - `data/drought/`: US Drought Monitor, weekly share of area per drought class, by state and by county.
  - `data/weather/`: county-month heat units, rain and frost days; county-year frost dates and May to September totals.
  - `data/rma/`: corn rows of RMA's cause-of-loss and insured-acres-by-type files, by county.
  - `data/Quickstats Data/*_state_2000_2026.*`: corn progress, corn silage harvest progress, corn condition, pasture
    condition, hay production, stocks and price, milk price, cattle on feed.
- `scripts/pull_data.py` pulls and refreshes all of it with the standard library; finished files are skipped.
- Every file is listed in `data/DATA_MANIFEST.tsv`. Rows for files that exist only on your machines were kept as they were.

## Next step
- cc-varun: the state panel can join these by `state_alpha` and year. RMA `type_code` 026 (insured silage acres) and the
  drought and condition series are the ones aimed at the silage shock years (2012, 2019, 2022).
- cc-manraj: `download_hack_the_harvest_quickstats.py` still writes to `Quickstats Data/` next to the script. The folder
  now lives at `data/Quickstats Data/`, so pass `--output "data/Quickstats Data"`. The 2015 to 2025 pull has no state
  silage rows for 2021 and no county silage rows for 2016.

## Resume commands
```
export NASS_QUICKSTATS_API_KEY=...        # only the Quick Stats pull needs a key
python3 scripts/pull_data.py all
```

## Risks
- Two Claude Code sessions are running as `cc-daniel` in the same checkout. One committed the other's files while pulls
  were still writing; the county drought files on `main` between 02:03Z and this delivery held each boundary week twice.
- FSA crop acreage is not pulled: the FSA site closes scripted connections. It needs a browser download into `data/fsa/`.
- County weather covers the lower 48 states only, and 2026 ends on 31 October.
