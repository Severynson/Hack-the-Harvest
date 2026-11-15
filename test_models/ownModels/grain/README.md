# Own corn-for-grain models (no current-year NASS input)

Owner key: `grain_own`. Folder: `test_models/ownModels/grain/`. Code: `run.py`. Tests: `test_run.py`. Outputs: `out/`.

The user's instruction (2026-11-14): "we cant just use their nass forecast., we should have our own models."
The team report currently passes NASS's November harvested-for-grain forecast through for grain
(`kernelag/state_model.py`, predictor `nass_latest`). This folder builds state corn-for-grain harvested-acres
models that use **no current-year NASS information** and scores them against that NASS forecast.

## 1. Pre-registration (written 2026-11-14, before any score of g1-g5 was computed)

What I had already seen before writing this section, so a reader can judge it:
- The incumbent backtest (`data/models/state_model_backtest.csv`, `state_model_metrics.json`): on 2017-2024
  NASS November (`nass_latest`) has a mean state WAPE of 1.66% and a mean |US| error of 0.82%; "same as last year" has 7.35% and 4.12%.
- The FSA panel agent's coverage table: FSA field-corn planted (final file) / NASS final planted, all states,
  is 0.946-0.979 from 2013 to 2025 and rises over time. The November file is within 0.003 of the final file.
- Daniel's GBT results file (`test_models/danielModel/out/gbt_results.tsv`): `grain_gbt_independent` has 2.553% state WAPE on 2012-2024.
- No FSA-based grain prediction had been computed or scored by me. No 2025 number of any candidate had been looked at.

### 1.1 Independence tiers (enforced in `run.py`: `SOURCES`, `CANDIDATES`, `check_tiers`)

| Tier | Inputs allowed for target year t |
|---|---|
| **A (independent)** | NASS **final** state numbers for years < t only (history anchors); FSA crop acreage files published by the as-of date; RMA cause-of-loss and insured acres; US Drought Monitor; NOAA weather |
| B (reported separately, never the headline) | Tier A plus NASS weekly crop condition and progress (no acreage, no yield forecast). No Tier B candidate is built here |
| Not independent | anything using NASS current-year acreage (March or June planted, in-season planted revisions), NASS in-season grain-area or yield forecasts, NASS silage harvest pace, or columns of `kernelag.state_panel` built from them |
| Benchmarks (not ours) | `nass_latest`: NASS's latest harvested-for-grain forecast by 15 Nov, exactly the incumbent's `nass_latest` (`kernelag.state_model.predict_grain`); `g0_persistence`: last year's NASS final |

Enforcement in code: every input source has a tier tag (`SOURCES`). Every candidate declares its sources
(`CANDIDATES`). `check_tiers()` runs at import and raises if an own candidate declares a source above Tier A.
Candidate functions receive only a `NassHistory` view (finals for years < t; asking for year >= t raises) and an
`FsaView` (only files that `kernelag.fsa.usable_files` admits for that as-of date and crop year). Truth is read only by the scorer.

### 1.2 As-of rule

A forecast "as of D of year t" (D = 15 Sep, 15 Oct or 15 Nov; headline 15 Nov):
- FSA: only files whose `assumed_published` <= D (`kernelag.fsa.usable_files` / `latest_file`: documented
  release date where one exists, else data date + 5 days). The in-season input is the newest crop-year-t
  file published by D. A missing or corrupt month is replaced by the latest earlier file, never a later one
  (15 Nov: 2015 uses October, 2025 uses September). A crop year's final (January) file is used only as history for later crop years.
  Files with no data date (2009 and 2010 finals) have no publication date and are never used.
- Drought Monitor: weekly maps dated <= D (`kernelag.context.drought`, June-September mean share in D2 or worse).
- RMA: losses with month of loss before D's month (`kernelag.context.loss_share`). RMA files are today's
  vintage, so past years' loss shares are slightly more complete than they were on D (mild look-ahead, same caveat as the incumbent).
- NASS: finals of years < t, as Quick Stats stores them today. Those include later revisions (the 30 Sep
  Grain Stocks revision of t-1, and census revisions published years later): a mild look-ahead shared with
  persistence and with the incumbent's truth. For the 15 Sep run the t-1 revision of 30 Sep is not yet public; not corrected.

### 1.3 Candidates (all Tier A except the benchmarks)

Notation: N(y) = NASS final grain harvested acres of a state in year y. F_g(file) = FSA field-corn planted
acres with intended use grain (planted acres, which exclude failed acres). F_all(file) = FSA field-corn planted
plus failed acres, every intended use. cur = newest crop-year-t FSA file published by D. fin(y) = final file of crop year y.

| Candidate | Prediction for state s, year t | Fitted? |
|---|---|---|
| `g0_persistence` (benchmark) | N(t-1) | no |
| `g1_fsa_ratio` (simplest own) | F_g(cur) x N(t-1) / F_g(fin(t-1)) | no |
| `g2_fsa_planted_share` | F_all(cur) x N(t-1) / F_all(fin(t-1)) | no |
| `g3_fsa_ratio_multi` | F_g(cur) x median over k = 1..3 of N(t-k) / F_g(fin(t-k)), using the k whose final file is usable (2012: k = 1 only; 2013: k = 1, 2) | no |
| `g4_fsa_plus_stress` | g1 x exp(b . x), x = (d_drought, d_loss): change from t-1 to t in the June-Sep D2+ drought share and in the RMA weather-loss share (drought, heat, irrigation failure, hot wind, hail, wind, frost, freeze over insured acres). b: pooled weighted ridge on log(N(y) / g1(y)) over all state-years y < t from 2012 on at the same as-of date, features scaled by their std (no centring, no intercept), penalty 1.0 x mean weight, weight N(y-1) (the incumbent's `fit_ridge` form). Missing x = 0. Fewer than 3 training years (test years 2012-2014): b = 0, so g4 = g1 | yes, expanding window |
| `g5_fsa_ratio_vintage` (added) | F_g(cur) x N(t-1) / F_g(ref), ref = the usable crop-year t-1 file (in-season or final) whose data date is closest in calendar day to cur's data date shifted back one year (ties: the later file) | no |

Why g5: FSA files fill up over the season (August files hold 0.89-0.98 of final acres). Dividing by last
year's file of the same point in the season cancels that, which matters for the 15 Sep and 15 Oct runs and
for years whose November file is missing (2015, 2025). At 15 Nov it should be close to g1.

Guard, the same for g1-g5: if F(cur) is missing or <= 0, or the reference FSA acres are missing or <= 0, or the
multiplier (N / F_ref, or the g3 median) is outside [0.25, 4.0], that state falls back to N(t-1) (`method = fallback_persistence`).
The bounds are sanity limits chosen without looking at any ratio. Every NASS grain state (41) is
predicted every year, so all candidates are scored on the same states.

"Other States": NASS publishes final grain area for 41 states and none for CT, ME, MA, NH, RI, VT, NV. The
in-season "Other States" row is a NASS grouping of states without an in-season forecast; at final every one of
the 41 states has its own number and "Other States" is 0. So truth is the 41 states and the US total is their
sum (equal to NASS's US figure, e.g. 2025: 90.948 M), exactly as the incumbent scores it. FSA covers all 41 states.

Also audited, not run by me: Daniel's `grain_gbt_independent` (`test_models/danielModel/train_gbt.py`).

### 1.4 Truth, metrics, periods

- Truth: NASS final state grain harvested acres, as the incumbent uses them (`data/nass/corn_acres_state.csv`,
  2013-2025). 2011 and 2012 come from the team's Quick Stats file
  (`data/Quickstats Data/corn_grain_harvested_acres_state_2000_2026.csv`, period YEAR), checked equal to the
  incumbent's table for every state-year 2013-2025. The 2026 "YEAR" rows in that file are NASS's provisional
  November numbers and are never read.
- Per year: state WAPE = sum |pred - actual| / sum actual over the 41 states; US error = (sum pred - sum actual) / sum actual.
  Reported: mean state WAPE over years, mean |US error|, mean signed US error.
- Periods: primary 2012-2024 (13 years); 2017-2024 separately for comparison with the team's numbers. 2025 is
  never used for any backtest fit, for selection or for the interval quantiles. Only the 2026 forecast, being
  an expanding-window forecast, uses 2025 as history (N(2025) as the anchor; for g4, 2025 as one more training year).
- Reproduction check first: g0 must give 7.35% state WAPE and 4.12% |US| on 2017-2024, and `nass_latest` 1.66% and
  0.82%, matching `data/models/state_model_metrics.json`.
- NASS benchmark for 2013-2024: the incumbent's own code (`load_panel` + `add_changes` + `predict_grain`). For
  2012 (absent from the incumbent's table): the same rule rebuilt from the Quick Stats files (latest NASS grain forecast
  published by D; else latest NASS planted published by D x last year's grain share of planted; else last year).
- Comparisons: paired by year, 90% bootstrap interval of the mean yearly difference (10,000 resamples of years,
  seed 20261114), for state WAPE and |US| error, against (a) `nass_latest`, (b) `g0_persistence`, (c) `g1_fsa_ratio`.

### 1.5 Selection rule (mechanical, applied once on the 15 Nov backtest, 2012-2024)

1. Eligible: g1, g2, g3, g4, g5. Simplest: g1 (nothing fitted, one ratio, the grain-intended field itself).
2. best = eligible candidate with the lowest mean state WAPE over 2012-2024.
3. If best is g1, select g1. Otherwise d_y = WAPE(g1, y) - WAPE(best, y) for each year; select best only if
   mean(d) > 2 x sd(d) / sqrt(13); else select g1.
4. The 15 Sep and 15 Oct products are chosen by the same rule on their own backtests (reported as earliness;
   the 15 Nov choice is the headline).
5. The selected 15 Nov model is scored on 2025 once (`out/score_2025_information_only.json`, refuses to
   overwrite; information only, never used to change anything) and gives the 2026 forecast.

### 1.6 Intervals for the 2026 forecast

State 80% interval: prediction x exp(q10, q90) of log(actual / pred) over the selected model's 2012-2024
15 Nov backtest, pooled within three size classes (tertiles of N(t-1) over the backtest rows). US 80% interval:
total x exp(+-1.2816 x RMS of the yearly log(actual US / predicted US)). Coverage is checked leaving one year out.

---

*Everything below was written after the scores were computed. Section 1 above is unchanged, apart from renaming
`nass_nov` to `nass_latest` and one clarification on 2025, both made before any score existed.*

## 2. How to run

```bash
.venv/Scripts/python.exe test_models/ownModels/grain/run.py                # backtest (15 Sep, 15 Oct, 15 Nov), selection, 2026 forecast (~1 min)
.venv/Scripts/python.exe test_models/ownModels/grain/run.py --score-2025   # the one-time 2025 information score (done; refuses to rerun)
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/grain/test_run.py
```

Outputs (`out/`): `backtest_by_state_year.csv` (state, year, asof, candidate, tier, pred, actual, method),
`by_year.csv`, `summary.csv` (candidate x as-of x period), `comparisons.csv` (paired 90% bootstrap intervals),
`selection.json` (rule applied, intervals), `reproduction.json`, `inputs_audit.json` (tier of every source and
candidate), `fsa_files_used.csv` (which FSA file every forecast used), `g4_weights.csv`, `error_by_coverage.csv`,
`forecast_2026.csv`, `daniel_gbt_audit.json`, `score_2025_information_only.json/.csv`.

## 3. Checks before the results

- **Reproduction** (`out/reproduction.json`): on 2017-2024 at 15 Nov, persistence gives 7.35% state WAPE and
  4.12% |US| error, and `nass_latest` 1.66% and 0.82%. That matches `data/models/state_model_metrics.json` exactly.
  The rebuilt NASS benchmark equals the incumbent's own `predict_grain` to the acre (maximum difference 0) for every
  state-year 2014-2024 at all three as-of dates. My 2025 `nass_latest` (1.64%, US -0.99%) equals the grain row of the stored
  `data/models/state_score_2025.json`. That file was read, not written.
- Every candidate predicts all 41 states in every year. The guard fired only for g2: California in 2016 and 2018-2024,
  and Arizona in 2022. Grain is under a quarter of all FSA corn there (mostly silage), so the multiplier fell below 0.25.
- FSA files used at 15 Nov (`out/fsa_files_used.csv`): the November file every year, except 2015 (October; the November
  download is truncated). At 15 Oct, 2020 and 2021 use September (October corrupt or never published). At 15 Sep, 2012
  uses August (the September download is truncated).

## 4. Results

### 4.1 Selection (rule of section 1.5, applied mechanically)

Mean state WAPE at 15 Nov, 2012-2024: g1 2.147, g2 2.241, **g3 1.938**, g4 2.147, g5 2.241. Best = g3. Its paired
gain over g1 is 0.209 points; 2 SE = 0.197. So **`g3_fsa_ratio_multi` is selected**. The margin is narrow: g1 (one
ratio, nothing fitted) is nearly as good, and g3's gain comes mostly from 2013, 2015 and 2023 (in 2023 g1 used the
2022 drought-year ratio alone and was 0.9 points worse). The same rule picks g3 at 15 Oct (gain 0.235 > 0.202) and
at 15 Sep (0.223 > 0.206).

### 4.2 15 Nov backtest, all candidates (state WAPE / mean |US error| / mean signed US error, %)

| Candidate | Tier | 2012-2024 | 2017-2024 |
|---|---|---|---|
| g0_persistence | benchmark (history only) | 6.86 / 4.01 / +0.19 | 7.35 / 4.12 / +0.67 |
| g1_fsa_ratio | A | 2.15 / 1.15 / +0.03 | 1.97 / 0.94 / +0.25 |
| g2_fsa_planted_share | A | 2.24 / 1.19 / -0.00 | 2.06 / 1.01 / +0.24 |
| **g3_fsa_ratio_multi (selected)** | **A** | **1.94 / 1.12 / +0.35** | **1.76 / 1.09 / +0.82** |
| g4_fsa_plus_stress | A | 2.15 / 1.25 / +0.02 | 1.96 / 1.05 / +0.21 |
| g5_fsa_ratio_vintage | A | 2.24 / 1.29 / +0.20 | 1.98 / 0.99 / +0.31 |
| nass_latest (NASS's own forecast) | not independent | 1.61 / 0.58 / +0.45 | 1.66 / 0.82 / +0.72 |
| Daniel `grain_gbt_independent` (quoted from his harness, not re-run) | not independent | 2.55 / 1.61 / n.a. | 2.20 / n.a. / n.a. |

g4: the stress weights have the expected sign (more drought, or more insured weather loss, means fewer grain acres
than FSA intentions imply) but are small (about -1% per standard deviation). The correction does not help: paired
difference vs g1 0.00 points, 90% CI -0.09 to +0.10. g5 helps at no date: 2.24% at 15 Nov, 2.35% at 15 Oct and 2.37% at 15 Sep,
against g1's 2.15%, 2.22% and 2.26%.

### 4.3 Selected model vs the three references (paired by year; 90% bootstrap CI of the mean difference, points; negative = g3 better)

| Reference | Period | State WAPE diff [90% CI] | Years g3 better | abs(US) diff [90% CI] |
|---|---|---|---|---|
| (a) NASS `nass_latest` | 2012-2024 | +0.33 [+0.05, +0.66] | 4 / 13 | +0.54 [+0.20, +0.91] |
| (a) NASS `nass_latest` | 2017-2024 | +0.10 [-0.07, +0.26] | 2 / 8 | +0.27 [-0.02, +0.54] |
| (b) persistence | 2012-2024 | -4.92 [-5.73, -4.12] | 13 / 13 | -2.89 [-4.25, -1.58] |
| (b) persistence | 2017-2024 | -5.59 [-6.57, -4.52] | 8 / 8 | -3.03 [-4.89, -1.27] |
| (c) g1 (simplest own) | 2012-2024 | -0.21 [-0.37, -0.06] | 9 / 13 | -0.03 [-0.43, +0.33] |
| (c) g1 (simplest own) | 2017-2024 | -0.21 [-0.41, -0.05] | 6 / 8 | +0.15 [-0.45, +0.63] |

### 4.4 By year, 15 Nov (state WAPE %, US error %)

| Year | g3 WAPE | NASS WAPE | g1 WAPE | g3 US | NASS US |
|---|---|---|---|---|---|
| 2012 | 3.52 | 1.41 | 3.52 | +1.92 | +0.41 |
| 2013 | 2.41 | 1.64 | 3.08 | -1.34 | -0.28 |
| 2014 | 2.91 | 1.88 | 2.62 | -2.44 | -0.06 |
| 2015 | 1.06 | 1.50 | 1.75 | -0.12 | -0.11 |
| 2016 | 1.19 | 1.19 | 1.19 | -0.03 | +0.09 |
| 2017 | 1.05 | 0.90 | 1.02 | +0.40 | +0.47 |
| 2018 | 1.76 | 1.55 | 1.90 | +0.82 | +0.74 |
| 2019 | 2.18 | 1.81 | 2.42 | +1.88 | +1.02 |
| 2020 | 1.55 | 1.23 | 1.62 | +1.22 | +0.44 |
| 2021 | 1.21 | 1.61 | 1.52 | +0.58 | +0.11 |
| 2022 | 3.28 | 3.62 | 3.21 | +2.69 | +2.70 |
| 2023 | 1.56 | 1.25 | 2.50 | +0.05 | +0.68 |
| 2024 | 1.51 | 1.29 | 1.55 | -1.07 | -0.40 |

The worst years are drought years. In 2012, FSA intentions cannot see abandonment, so g3 is +1.9% at US level. In 2022
g3 and NASS both over-predicted by 2.7%. 2013 and 2014 under-predict (US -1.3% and -2.4%). The 2013 anchor ratios include
2012, when NASS grain acres fell short of FSA grain intentions.

### 4.5 Earliness (selected g3 against NASS's latest forecast published by the same date)

| As of | g3 2012-2024 | NASS 2012-2024 | WAPE diff [90% CI] | g3 2017-2024 | NASS 2017-2024 | WAPE diff [90% CI] |
|---|---|---|---|---|---|---|
| 15 Sep (FSA Sep file) | 2.04 / 1.14 | 2.58 / 0.91 | -0.55 [-1.06, -0.03] | 1.75 / 0.92 | 2.53 / 1.05 | -0.78 [-1.41, -0.19] |
| 15 Oct (FSA Oct file) | 1.99 / 1.10 | 1.76 / 0.70 | +0.22 [-0.13, +0.62] | 1.76 / 0.95 | 1.66 / 0.82 | +0.10 [-0.06, +0.26] |
| 15 Nov (FSA Nov file) | 1.94 / 1.12 | 1.61 / 0.58 | +0.33 [+0.05, +0.66] | 1.76 / 1.09 | 1.66 / 0.82 | +0.10 [-0.07, +0.26] |

Cells are state WAPE / mean |US error| in %; "WAPE diff" is g3 minus NASS. The FSA model is almost as good at 15 Sep as at 15 Nov. At
15 Sep it beats NASS's then-latest state forecast (August or September report). In the incumbent's NASS table, the
October and November state grain-area forecasts are identical in every state-year 2014-2024. September equals
November from 2021 on. So since 2021 NASS's state grain area has not changed after its September report.

### 4.6 States FSA covers poorly (diagnostic only, not used for selection)

Coverage = FSA grain-intended acres in last year's final file / NASS grain acres last year. Lowest medians,
2012-2024: Washington 0.77, Idaho 0.83, Arizona 0.84, Florida 0.85, Oregon 0.86, California 0.86, Pennsylvania 0.89,
Utah 0.91, New York 0.91. The ratio method absorbs a stable coverage level. Coverage that moves from year to year
does hurt it. Pooled 15 Nov errors, 2012-2024:

| Coverage class | State-years | Share of acres | g3 WAPE | NASS WAPE | Persistence WAPE |
|---|---|---|---|---|---|
| >= 0.95 | 402 | 96.4% | 1.84 | 1.49 | 6.78 |
| 0.80-0.95 | 97 | 3.3% | 4.16 | 3.78 | 7.97 |
| < 0.80 | 34 | 0.3% | 7.41 | 11.61 | 17.46 |

In the least-covered states g3 beats NASS's benchmark. NASS publishes no November forecast for most of them, so its
benchmark falls back to planted acres x last year's grain share. The 80% intervals there are wide (small-state class:
-17% to +22%).

### 4.7 2025, information only (computed once, after selection; `out/score_2025_information_only.json`)

As of 15 Nov 2025 only FSA's September 2025 file was public (no October or November file: shutdown). g3:
**1.72% state WAPE, US -1.18%** (89.87 M vs 90.948 M); NASS `nass_latest` 1.64%, US -0.99%; persistence 9.23%,
US -8.69%. 34 of 41 states (0.829) fell inside the 80% intervals. Nothing was changed after this number was seen.

## 5. 2026 forecast (selected g3, as of 15 Nov 2026; `out/forecast_2026.csv`)

Inputs: the FSA file of 5 Nov 2026 (released 10 Nov 2026), ratios from the FSA final files and NASS finals of
2023-2025. No 2026 NASS number is an input. The NASS column is shown only for comparison.

| | g3 forecast | 80% interval | NASS 2025 final | NASS 10 Nov 2026 forecast (comparison only) |
|---|---|---|---|---|
| **US (41 states)** | **88.69 M** | 87.10-90.31 M | 90.948 M | 88.506 M (ours +0.2%) |
| Iowa | 12.78 M | 12.29-13.22 M | 13.15 M | 12.80 M |
| Illinois | 10.85 M | 10.44-11.23 M | 10.95 M | 10.95 M |
| Nebraska | 9.61 M | 9.25-9.95 M | 10.39 M | 9.61 M |
| Minnesota | 8.36 M | 8.04-8.65 M | 8.44 M | 8.30 M |
| Kansas | 6.53 M | 6.28-6.76 M | 6.45 M | 6.55 M |
| South Dakota | 5.91 M | 5.69-6.12 M | 6.35 M | 5.84 M |

Our forecast and NASS's disagree by more than 10% only in small western or low-coverage states: Washington +27%,
Montana -23%, Oregon +20%, Utah +18%, Arizona +18%, California +13%, West Virginia -11%. Together these hold about
0.5% of US grain acres. US interval: +-1.2816 x RMS of the yearly log US errors (RMS 0.0141). The state intervals
had a leave-one-year-out coverage of 0.79 for a nominal 0.80.

The 7 states with no NASS grain figure (CT, ME, MA, NH, RI, VT, NV) hold 24,635 FSA grain-intended acres in the
5 Nov 2026 file. They are left out of the 41-state total, as in NASS's own US total.

## 6. Verdict against NASS

- **Can a NASS-independent model reach NASS's 1.8-2.5% band? Yes.** g3 has 1.94% mean state WAPE on 2012-2024 and
  1.76% on 2017-2024, using only farmers' FSA certifications published by the forecast date plus NASS finals of
  earlier years. That is within or below the band the USDA reps quoted, and 5 points better than "same as last year".
- **Does it beat NASS's November forecast? No.** It is worse by 0.33 points of state WAPE on 2012-2024 (90% CI
  0.05-0.66). On 2017-2024 the gap is 0.10 points (CI -0.07 to +0.26), which cannot be told apart from zero. Its US
  total error is about twice NASS's (1.12% vs 0.58% on 2012-2024).
- **Earlier is where it wins.** At 15 Sep it beats NASS's then-latest forecast (2.04% vs 2.58%; 2017-2024: 1.75%
  vs 2.53%), and it barely degrades from 15 Nov back to 15 Sep.
- **The bias is consistent and explained.** g3 over-predicts the US total by +0.82% on average over 2017-2024. FSA
  coverage of grain rises over time, so a median of the last three NASS/FSA ratios lags the trend and scales the
  current file up too much. This was not corrected after the fact, because that would be tuning on the backtest.
- **Where it fails: drought abandonment.** FSA intended use is a July statement, so in 2012 and 2022 acres later
  abandoned or chopped are still certified as grain. The pre-registered Drought Monitor + RMA correction (g4) did not
  fix this.
- **Not independent of FSA.** NASS is understood to use FSA administrative acreage in its own area estimates (not
  verified in this task). That would explain why our 2026 number lands within 0.2% of NASS's. The model removes the
  dependence on NASS's current-year survey, not on the farmer certifications both may draw on.
- **Recommendation for the report:** present g3 as the team's own grain number (Tier A), with NASS November beside
  it as the benchmark. Do not claim it beats NASS.

## 7. Limitations

- FSA publication dates are assumed (data date + 5 days) for almost every file before 2025. The tightest case is
  2021: the 9 Nov file is assumed released on 14 Nov. Using the earlier September file instead would move 2021 from 1.21% to 1.24%.
- The truncated FSA downloads (2012 Sep, 2015 Nov, 2020 Oct) force fallbacks to earlier files. Downloading them again
  would change those forecasts (2015 at 15 Nov, 2012 at 15 Sep, 2020 at 15 Oct).
- NASS finals, used both as history anchors and as truth, are today's revised values. These include the 30 Sep Grain
  Stocks revision of t-1 and census revisions published years later. This is a mild look-ahead shared with
  persistence and the incumbent. At 15 Sep, the 30 Sep revision of t-1 is not yet public.
- RMA files are today's vintage (affects g4 only; g4 was not selected).
- 13 backtest years, and the selection margin (0.209 vs 0.197) is narrow; g1 is a near-equivalent simpler alternative.
- Daniel's `grain_gbt_independent` is not independent:
  - Its starting value is NASS's in-season planted acres. Before 2018, `build_panel.py` fills those with NASS's
    final planted acres, which is a look-ahead.
  - It also uses `d_planted` (NASS planted acres), `yield_shock` (NASS's Aug-Nov yield forecast), `cond_poor`
    (NASS crop condition), and `planted_may20` and `mature_sep22` (NASS crop progress).

  Details are in `out/daniel_gbt_audit.json`. Its numbers are quoted from his own harness, not re-run here.
- Intervals are retrospective (pooled by size class over 2012-2024) and exist only for the 15 Nov product.
