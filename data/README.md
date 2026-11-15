# Data folder

Public data, tracked in git so a pull brings it (see "Data in git v1" in `CLAUDE.md`; the limit is 30 MB a file).
`DATA_MANIFEST.tsv` has one row per file: bytes, sha256, source, who pulled it and when.
The organizers' starter kit is tracked separately at `jupyter/workspace/`.

## What is where

| Folder | What it holds | Unit, years | Source | Pulled by |
| --- | --- | --- | --- | --- |
| `Quickstats Data/*_2015_2025.csv` | Corn planted, grain and silage acres; yields; production; irrigated acres; corn price; all cattle; milk cows | state and county, yearly (prices monthly), 2015 to 2025 | NASS Quick Stats | `download_hack_the_harvest_quickstats.py` |
| `Quickstats Data/*_state_2000_2026.csv` | In-season series: corn progress, corn silage harvest progress, corn condition, pasture condition, hay production, hay stocks, hay price, milk price, cattle on feed. Long history with every in-season figure: corn planted, grain and silage acres, grain yield, milk cows | state; weekly, monthly or yearly; 2000 to 2026 | NASS Quick Stats | `scripts/pull_data.py quickstats` |
| `drought/` | Share of area in each drought class | state and county, weekly, 2000 to 2026 | US Drought Monitor | `scripts/pull_data.py drought` |
| `weather/county_month/` | Heat units, rain, mean daily high and low, hot days, frost days | county-month, 2000 to 2026 | NOAA nClimGrid-Daily | `scripts/pull_data.py weather` |
| `weather/county_season/` | Last spring frost, first fall frost, first hard freeze, May to September heat units and rain | county-year, 2000 to 2026 | NOAA nClimGrid-Daily | same |
| `rma/cause_of_loss_corn/` | Corn insurance losses by cause (drought, hail, wind, frost and others) and month | county, 2000 to 2026 | RMA Summary of Business | `scripts/pull_data.py rma` |
| `rma/insured_by_type_corn/` | Insured corn acres by type (grain, silage and others) and practice | county, 2000 to 2026 | RMA Summary of Business | same |
| `nass/`, `labels/`, `s2_series/`, `panel/`, `models/` | cc-varun's tidy tables, labels, field series and model outputs; listed in the manifest | | | `kernelag` modules |

## How to read each set

- **Quick Stats.** One row per published number, in the layout of the organizers' file. Keep `source_desc = SURVEY`
  and `domain_desc = TOTAL` for the plain yearly figures; the 2015 to 2025 files also carry census breakdowns by farm
  size and type. The 2000 to 2026 files are state level and survey only, and add a `week_ending` column.
  Corn silage harvest progress starts in 2014 and covers 25 states; corn progress and condition cover 45 states.
- **Drought.** `None`, `D0` to `D4` are percent of area. The classes are cumulative: `D1` is the share in D1 or worse.
- **Weather.** Built from NOAA's daily county averages of high, low and rain. Temperatures in degrees C, rain in mm.
  `gdd_c` is corn heat units with a 10 C base and a 30 C cap (50 F and 86 F). `hot_days` counts highs of 32 C or more,
  `frost_days` lows of 0 C or less. Frost dates are days of the year; a hard freeze is -2.2 C (28 F) or less.
  `data_through` is the last day with data, so 2026 is a part year. `fips` is the usual five-digit county code.
  The lower 48 states only.
- **RMA.** Corn rows (commodity code 0041) of RMA's yearly files, every column kept. Column names follow RMA's record
  layouts: `COL_Summary_of_Business_with_Month_All_Years.pdf` and `SOBTPU_External_All_Years.pdf`. In
  `insured_by_type_corn`, `type_code` 016 is grain and 026 is silage; filter on the code, because the names are upper
  case before 2011. RMA counts insured acres only, so it is a floor, not a total.

## Gzipped files

The per-state county drought files and the yearly RMA files are stored as `.csv.gz` to keep clones small, and so is
any table above 25 MB. pandas reads `.csv.gz` as it is; `gunzip -k file.csv.gz` gives a plain copy to open in an editor.

## Not stored

- Daily county weather: `scripts/pull_data.py weather` reduces it to months and seasons as it downloads. The daily files
  for 2000 to 2026 are about 1 GB; NOAA's folder is linked in the manifest.

## Not pulled yet

- **FSA crop acreage (intended use, failed and prevented acres).** The FSA site closes the connection on scripted downloads.
  Download the files in a browser from the crop acreage data page and put them in `data/fsa/`:
  `https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/frequently-requested/crop-acreage-data`
- **Satellite summaries per county.** These come from the field-series work in `kernelag/s2_series.py`.

## Refreshing

```
python3 scripts/pull_data.py all            # every pull, then the manifest; finished files are skipped
python3 scripts/pull_data.py weather --start-year 1979
```

The Quick Stats pull needs a free key in `NASS_QUICKSTATS_API_KEY` (environment or `.env`). No other pull needs a key.
