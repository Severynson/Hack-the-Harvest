# Dairy feed-demand balance: county test

**Short answer.** The county balance (milk cows per corn acre times the state's silage acres per cow) does tell you
*where* silage is grown inside the upper-Midwest and north-eastern dairy states. Out of sample, pooled over the
major dairy states, it cuts the county share error by about 40% (MAE 0.071 vs 0.114) against giving every county
the state share. It does **not** predict *changes*: county herds move about 2% a year while county silage acres
move about 23%, so "same as last year" wins. And it does **not** improve the state forecast: −0.06 points of state
WAPE against the incumbent, 90% CI −0.37 to +0.25. That fails the pre-registered rule. Keep it as a spatial prior
and a roll-up plausibility check in WI, MI, OH, PA, NY, IN, MD, NJ and MO. Do not add it to the state model. Do not
use it in California, the West or the Plains.

Every number below is from `out/results.json` (run `run.py`, seed 0, 2026-11-14).

## What and why

`DOCS/research/dairy_prior.md` (sections 5.2 and 8.2) proposes

    share_c = clip(k_s x milk_cows_c / corn_acres_c, 0.01, 0.98)

Silage is about two-thirds water and is trucked only a few miles, so counties with many cows per corn acre should
chop more of their corn. The note's evidence is one in-sample fit: Wisconsin, 2022 Census, 63 counties, R² 0.87.
Its fact-check (`dairy_prior.verification.md`, items 2 and 3) adds two warnings. First, k was fitted on the same
counties. Second, NASS's annual Wisconsin county silage estimates swing far more than herds do. This folder tests
the claim at the three levels where truth exists.

## Data (local only, no API key used)

| Need | File (`data/Quickstats Data/`) | What exists |
|---|---|---|
| County milk cows, annual | `milk_cow_inventory_county_2015_2025.csv`, SURVEY, 1 Jan | 2015–2025. 35 states in 2015–2020, 34 in 2021–2024, 25 in 2025 (2025 incomplete). Some counties withheld (D) |
| County milk cows, Census | same file, CENSUS, 31 Dec | 2017 and 2022 only, 50 states. No 2012 Census cows locally, so there is no 2012–2017 pair |
| County silage acres | `corn_silage_harvested_acres_county_2015_2025.csv` | Census 2017 and 2022 for all states. Annual survey only in WI, NY, PA, MN, IA and ND (2015, 2017–2025), plus CA (to 2023). **No 2016 rows** |
| County corn planted | `corn_planted_acres_county_2015_2025.csv` (survey) | 37 states, 2015–2025, **2021 missing**. Shares are carried forward up to 3 years |
| County grain acres | `corn_grain_harvested_acres_county_2015_2025.csv` | Census 2017 and 2022. Survey 2015–2024 |
| State truth and context | `kernelag.state_panel.load_panel("nov")`, the incumbent's own panel | 48 states. Milk cows from 2015 |

Missing: county cattle on feed. The note's 0.09 feedlot weight is therefore not applied, and only milk cows are
used. Withheld (D) values are dropped, never filled.

## Method

**Test 1, county cross-section.** For each state-year with at least 8 counties, there are two truth definitions:

- `census_harvested`: Census silage / (silage + grain), with Census cows. Census publishes no planted acres.
- `survey_planted`: survey silage / survey planted (the requested definition), with survey cows on 1 January.

The balance is scored **out of sample**: k is last year's NASS state silage acres per milk cow. The naive baseline
gives every county last year's state share. The note's in-sample version (k and the state share from the same
counties) is kept as an upper bound. R² is pooled *within state*, so the big differences between states cannot
inflate it. A placebo shuffles the cows among each state's counties. Share and density have the same denominator,
so the placebo shows how much skill would appear from that alone.

**Test 2, county year over year.** This compares three predictions of this year's county silage acres:

- persistence: last year's acres.
- cow_scaled: last year's acres × this year's cows / last year's cows.
- state_k: the balance level from last year's state k and the latest prior county corn.

It is scored on annual survey pairs (2018–2024) and on Census 2017 → 2022 pairs.

**Test 3, state deliverable.** This builds the county balance for every state-year:

1. Take last year's survey county cows and county corn shares. Counties lacking either number, plus withheld
   counties, go into one remainder "county", so the state totals are kept.
2. Calibrate k so the clipped balance reproduces last year's state silage exactly.
3. Re-run it with this year's 1 January state cows and NASS's latest in-season planted acres.

Current-year final silage, grain and yield are never used. The candidates are scored on the incumbent's panel truth,
48 states, 2017–2024, with the incumbent's own expanding-window code (`kernelag.state_model.predict_silage`).
2025 is reported for information only.

**Pre-registered** (fixed in `run.py` before any state result was computed):

- Primary candidate: `balance_ridge`, the incumbent ridge on `[reversion, d_balance]`, where
  `d_balance = log(balance / last year's silage)`.
- It counts as adding value only if all three hold: the mean delta in state WAPE is below 0, the upper end of the
  90% state-cluster bootstrap interval is below 0, and the gain is more than 2 paired-year standard errors.
- Secondary candidates: `balance_ratio` (the unfitted balance), `cows_ridge` (`[reversion, d_cows]`, state cows),
  `cows_ratio` (last year's acres × the state cow change) and persistence.

## Results

### Reproduction of the research note

From the local Quick Stats file, Wisconsin 2022 Census reproduces exactly: 63 counties, R² 0.866,
share = 0.002 + 0.663 × cows per corn acre, k 0.623, MAE 0.041 against 0.112 for the state share.

### Test 1: the balance locates silage inside dairy states, out of sample

| Pooled (within state), county-years | In-sample R² | Out-of-sample R² | Skill vs naive (out) | MAE share, balance vs naive (out) | Acre WAPE, balance vs naive (out) |
|---|---:|---:|---:|---:|---:|
| Census 2017+2022, 31 states, 1,939 | 0.01 | −0.14 | 0.17 | 0.091 vs 0.112 | 45.1% vs 53.7% |
| Census, major dairy states, 959 (13 of the 15 in `MAJOR_DAIRY` have at least 8 counties; NM and AZ do not) | 0.42 | 0.30 | 0.40 | 0.071 vs 0.114 | 29.8% vs 50.2% |
| Annual survey, WI NY PA MN IA, 1,061 | 0.35 | 0.23 | 0.32 | 0.085 vs 0.112 | 33.1% vs 49.8% |

The placebo skill is −2.2 (Census) and −3.8 (survey), far below the real skill. The information is in *which*
county holds the cows, not in the shared denominator. Out of sample, the balance beats the naive share in 18 of 30
Census states.

Census, out of sample, by state (R² / skill vs naive):

- Works (out-of-sample R² > 0.4): WI 0.81 / 0.83; IN 0.73 / 0.74; MI 0.62 / 0.66; OH 0.58 / 0.61;
  PA 0.57 / 0.58; MD 0.56 / 0.58; NJ 0.49 / 0.59; NY 0.47 / 0.48; MO 0.47 / 0.57.
- Partly: MN 0.26 / 0.32; TX 0.21 / 0.66.
- Worse than naive: ID −0.13 / −0.03; ND −0.91 / −0.32; UT −0.41 / −0.41; WA −0.40 / −0.37; IA −0.43 / −0.42;
  NE −0.94 / −0.76; KY −1.12 / −0.42; WV −1.46 / −0.92; CA −2.51 / −2.10; SD −2.64 / −2.16; MT −6.13 / −5.78;
  KS −7.44 / −6.75.

Annual survey, out of sample: WI 0.62 / 0.66 (by year 0.15 to 0.82); MN 0.26 / 0.36; NY 0.24 / 0.29;
IA −0.37 / −0.04; PA −0.59 / −0.28 (PA works on the Census but not on the survey).

Reading: the 87% Wisconsin figure is real but a best case. It holds for both Census years (in-sample r² 0.86 and
0.87), and out of sample on annual data Wisconsin drops to R² 0.62 pooled. The rule fails in three places:

- Plains and feedlot states: silage feeds beef there, so k from milk cows is wrong.
- California and the arid West: dairies saturate or buy feed, as in the note's own finding.
- Iowa: last year's state k is about 1.5 acres per cow against an in-county 1.0, because of feedlot silage.

### Test 2: the balance does not predict county changes

| Scheme | County pairs | Persistence | Cow-scaled | State-k balance | Corr(Δlog silage, Δlog cows) | Median abs Δlog silage / cows |
|---|---:|---:|---:|---:|---:|---:|
| Annual survey 2018–2024 (WI NY PA MN IA ND CA) | 831 | **26.0%** | 26.6% | 31.3% | −0.04 | 0.23 / 0.02 |
| Census 2017 → 2022 (43 states) | 811 | **29.6%** | 29.8% | 49.0% | 0.18 | 0.34 / 0.28 |

The columns are pooled county WAPE. Cow-scaled beats persistence in 15 of 42 annual state-years and 23 of 43 Census
states. Year to year, county silage moves about ten times more than county herds, and the two moves are
uncorrelated. That matches the fact-check's Manitowoc and Barron examples.

### Test 3: the state forecast does not improve

The incumbent (`reversion_only`) and persistence are reproduced to 0.00 points in all 8 years. The comparison is
like for like.

| Candidate (2017–2024, 48 states) | Mean state WAPE | Mean abs US error |
|---|---:|---:|
| incumbent_reversion_only | 13.12% | 3.90% |
| **balance_ridge** (primary) | 13.07% | 4.13% |
| cows_ridge | 13.12% | 4.02% |
| persistence | 14.53% | 4.08% |
| balance_ratio (unfitted) | 14.86% | 4.38% |
| cows_ratio (unfitted) | 14.98% | 4.33% |

| Delta in state WAPE (points) | Mean | 90% CI, states resampled | 90% CI, years resampled | Years better |
|---|---:|---:|---:|---:|
| balance_ridge − incumbent (**primary**) | −0.06 | −0.37 to +0.25 | −0.54 to +0.47 | 5/8 |
| balance_ridge − cows_ridge | −0.05 | −0.30 to +0.18 | −0.35 to +0.24 | 4/8 |
| balance_ratio − cows_ratio | −0.12 | −0.36 to +0.08 | −0.35 to +0.11 | 4/8 |
| balance_ratio − persistence | +0.33 | −0.07 to +0.74 | −0.16 to +0.91 | 3/8 |
| cows_ratio − persistence | +0.45 | +0.14 to +0.77 | +0.09 to +0.90 | 2/8 |
| balance_ratio − incumbent | +1.74 | +0.95 to +2.70 | +0.60 to +2.83 | 1/8 |

The paired-year SE of the primary delta is 0.33. The mean delta is negative, but the 90% interval spans zero and the
gain (0.06) is far below 2 SE (0.66), so the pre-registered rule fails on two of its three parts. In the final
fit, the weights per standard deviation are reversion −0.10 and d_balance +0.10 (the expected sign), against
d_cows +0.03 in `cows_ridge`.

2025, info only (fitted on years up to 2024, never used for a choice):

- State WAPE: balance_ridge 14.17%, recomputed incumbent 14.15% (the stored, frozen score is 14.14%; the stored
  forecast rounds to 100 acres), persistence 13.96%.

### How the county balance differs from the team's state milk cows (`d_cows`)

Without counties at the 0.98 cap, the calibrated county balance is *algebraically identical* to last year's acres
× the state cow change (`test_dairy_balance.py` checks this). The county structure changes the answer only where a
county's corn supply, not its cows, limits silage. Those counties then follow planted acres instead of herd size.

Measured over the scored state-years:

- County structure exists in 223 of 384 state-years, covering 88.5% of silage acres.
- Corn-limited counties carry 6.4% of balance silage, silage-weighted. Only CA, CO and VA exceed 25%.
- The balance differs from the cow ratio by a mean of 2.2% (mean absolute log gap).

So the county balance adds a small planted-acre term to `d_cows`, and nothing measurable beyond it:

- `balance_ridge − cows_ridge` is −0.05 points, and its interval spans zero.
- The team's earlier dairy tests point the same way: `d_cows` inside `all_public` (`kernelag.state_model`), the
  dairy candidates in `test_models/accuracy/national.py` (not selected), and the context set in
  `test_models/accuracy/state_candidates.py` (not promoted).
- **Inference**: d_balance's larger weight probably comes partly from that planted-acre component. The
  `nass_acres` set already carries planted change.

The reason is physical, and it is shown in Test 2. The balance describes how *much* silage a county's herd
needs. The state model has to predict the year-to-year *change*, and herds hardly change. The swings are weather,
price and salvage decisions, which a herd count cannot see.

## Verdict

1. **Spatial prior: yes, regionally.** In WI, MI, OH, PA, NY, IN, MD, NJ and MO, the out-of-sample R² is above 0.4
   and the county share MAE falls by 21% (NJ) to 61% (WI) against the naive share. Use `out/county_prior.csv`
   as a capped tie-breaker (`dairy_prior.md` 8.4) and for the cow-plausibility check of county roll-ups. Do not use
   it in CA, ID, WA or UT, in the Plains (KS, NE, SD, ND, MT), or in IA, KY and WV.
2. **County changes: no.** Persistence wins.
3. **State forecast: no.** There is no detectable gain over the incumbent or over state cows. Do not add it.

## `out/county_prior.csv` (for later field-level use)

- 8,466 rows, 2015–2025, up to 30 states per year.
- `state_fips` (2 digits), `county_fips` (**5 digits**, state + county).
- `year`, `milk_cows` (survey, 1 January of the year).
- `corn_planted`: the latest survey county planted at or before the year, at most 3 years old (2021 uses 2020).
  Its source year is in `corn_planted_year`.
- `predicted_silage_share = clip(k × milk_cows / corn_planted, 0.01, 0.98)`, with `k_acres_per_cow` from the
  previous year's state totals (`k_from_year`).
- 2015 shares are empty because there are no 2014 state cows in the panel.
- Same-year planted acres are published after the season. For a real-time prior, use the previous year's row.

## Why it cannot be tested on Maryland, and what Quebec would need

**Maryland (BARC, test only).** All 34 fields are in Prince George's County (24033). A county prior is therefore
one number per year for every field. It cannot rank fields, and any score built on it is a constant. For that
county, survey milk cows are withheld (D) for 2015–2022, so there is a prior only for 2023 (200 cows, 1,900 planted
acres, share 0.103). No Maryland label was read here.

**Quebec analog.** The truth side exists. The labelled maize parcels (`quebec_maize_2023`, labels only) show that
the silage share climbs with latitude:

| Latitude band | Silage share of parcels |
|---|---:|
| 45.0–45.5 N | 10.5% (13,124 parcels) |
| 45.5–46.0 N | 11.8% |
| 46.0–46.5 N | 22.1% |
| 46.5–47.0 N | 33.4% |
| 47.0–47.5 N | 64.6% |
| 47.5–48.0 N | 89.7% |

The dairy side is missing. It would need:

- dairy cow inventories and corn-for-grain and corn-for-silage areas by census division or consolidated subdivision
  (Statistics Canada, Census of Agriculture 2021),
- the division boundaries, to place each parcel,
- Quebec's previous-year silage area per dairy cow, for k.

Even then, two limits apply:

- Every field in a 10 km cell gets the same prior. The prior could only help across cells (the leave-one-cell-out
  evaluation E2), never inside cell 79_515 (E1). That is the Maryland problem again.
- **Inference**: the northward rise in silage share is also a heat-unit effect, because grain corn does not mature
  there. A Quebec dairy prior would be confounded with climate, so it would need a heat-unit control.

## Limitations

- **Revised data.** The backtest uses today's revised NASS values, not archived publication snapshots.
- **Publication timing.** For the state balance, county distributions are lagged one year because the release dates
  of the January county estimates were not verified. The county prior file uses same-year values; see above.
- **Short feature history.** The balance needs 2015 county data, so `d_balance` enters the fits only from 2016.
  The 2017–2019 fits have 1–3 years of it.
- **Noisy truth.** NASS county silage estimates are themselves noisy, and their coverage changes every year (8 to
  63 counties per state).
- **Census comparison covers only silage counties.** Census lists counties with silage; counties without any are
  absent.
- **Census and survey disagree.** Census and survey levels differ (WI 2022: 787k vs 870k acres), and this affects
  the out-of-sample k.
- **Milk cows only.** Feedlot and beef demand are missing, which is why the Plains fail.

## Run

```sh
.venv/Scripts/python.exe test_models/featureTests/dairy_balance/run.py      # about 12 s; writes out/
.venv/Scripts/python.exe test_models/featureTests/dairy_balance/build.py    # contract stub: meta.json, features.csv
.venv/Scripts/python.exe -m pytest -q test_models/featureTests/dairy_balance/test_dairy_balance.py
```

Outputs:

- `out/results.json`: everything above, plus the pre-registration and data coverage.
- `out/cross_section.csv`, `out/county_yoy.csv`: per state-year detail for Tests 1 and 2.
- `out/state_balance.csv`, `out/state_predictions.csv`, `out/state_by_year.csv`: Test 3.
- `out/county_prior.csv`: the county prior described above.
- `out/meta.json` and `out/features.csv`: the contract stub. It has no field features, and each dataset carries an
  UNCOMPUTED reason.

Nothing outside this folder is written.
