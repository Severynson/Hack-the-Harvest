# Does the satellite signal improve state silage acreage? (agent key: `sat_eval`)

Folder: `test_models/ownModels/satellite/eval/`. Code: `eval.py`. Tests: `test_eval.py`. Outputs: `out/`.
Nothing outside this folder is written. `data/panel/state_satellite.csv` is never created.

---

## 1. Pre-registration (written 2026-11-15 before any score was computed; not edited afterwards)

This section, from its heading to the end-of-section marker, is hashed into `out/preregistration.sha256` by
`eval.py --prereg` before the first scored run. `eval.py` refuses to score if the hash differs. Later text goes
below the marker; any change of method is listed under "Deviations".

### 1.0 What I had seen before writing this

- The `signal` agent's README and outputs: the state shares 2019-2025 (its table of `sat_share` by state and
  year as of 15 Nov), and its diagnostics: the year-to-year change of the share is null to negative against NASS
  (pooled Spearman -0.21 [-0.38, 0.01] as of Nov, signs agree in 33 of 90 state-years), expected
  signal-to-noise below 1 in every state (median 0.39). So I expected the satellite candidates to lose before
  writing this.
- The `corn26` agent's README: the corn classifier and its 2025 mask-error replay (Nov: classifier share minus CDL
  share, mean +0.0012, SD 0.0135; the 2026-style pool mean +0.0012, SD 0.0151), and the cross-year omission replay
  (larger errors in Texas, California, Colorado).
- The Tier A and Tier B silage READMEs with their 48-state scores (s3 12.52% and c5b 12.65% state WAPE on
  2017-2024; reversion_only 13.12%), never restricted to the 15 sampled states.
- Input coverage checks only (no outcome computed): the 15 states have rows in every base file for 2020-2024,
  2025 and 2026; the Tier A backtest's `actual` and `last` columns equal NASS final silage S(t) and S(t-1) in
  `data/nass/corn_acres_state.csv` for the 15 states in 2020-2024; the Tier B backtest file repeats every row three
  times with identical values (de-duplicated before use, and the run asserts the copies are identical);
  `corn26/out/corn26_calls.csv` has 10 areas in every state.
- No score of any candidate below on the 15 states, in any year.

### 1.1 Scope and notation

- States: the 15 sampled states of `data/samples/sample_summary.csv` (Wisconsin, New York, South Dakota,
  California, Minnesota, Iowa, Michigan, Pennsylvania, Kansas, Nebraska, Idaho, North Dakota, Colorado, Ohio,
  Texas). Forecast date d = 15 November of t (primary). Earliness: 15 October and 15 September.
- Selection years: t = 2020-2024 (5 years; a change needs t-1, and the shares start in 2019). 2025: information
  only, scored once, never used to select or tune. The stored 2025 report score is not touched.
- S(y): NASS final state silage acres, `data/nass/corn_acres_state.csv` (series silage, period final), the
  incumbent's truth. Truth for year t is S(t); S(t-1) is last year's final.
- sh(t): `sat_share` of `test_models/ownModels/satellite/signal/out/state_satellite_asof_<d>.csv` (probability-
  weighted silage-like share of the sampled corn acres; CDL corn mask in 2019-2025). shc(t): `sat_share_calls`.
- r(t) = clip(sh(t) / sh(t-1), 0.5, 2). rc(t) = the same with shc.
- Base predictions, as stored by their owners (nothing refitted here):
  - R = the report model `reversion_only`. 2020-2024: `s1_incumbent_H13` in
    `test_models/ownModels/silage/out/backtest_by_state_year.csv` (the exact reproduction of
    `data/models/state_model_backtest.csv`; history only, so the same at every as-of date). 2025:
    `data/models/state_score_2025.csv` (`silage`). 2026: `data/models/state_forecast_2026.csv` (`silage`).
  - A = Tier A selected `s3_fsa_residual`. 2020-2024: Tier A backtest at the same as-of key. 2025:
    `test_models/ownModels/silage/out/score_2025_information_only.csv`. 2026: `.../silage/out/forecast_2026.csv`.
  - B = Tier B selected `c5b_residual_fsa_planted_pre_june`. 2020-2024: Tier B backtest
    (`test_models/ownModels/tierB/silage/out/backtest_by_state_year.csv`) at the same as-of key. 2025:
    `.../tierB/silage/out/score_2025_information_only.csv`. 2026: `.../tierB/silage/out/forecast_2026.csv`.

### 1.2 Candidates (no fitted parameter anywhere, so every year is out of sample)

Primary (the adoption rule applies):

| Key | Prediction for state s, year t | Its base |
|---|---|---|
| `p0` | S(t-1) (persistence) | - |
| `R` | reversion_only (report) | - |
| `A` | Tier A s3 | - |
| `B` | Tier B c5b | - |
| `p1` | S(t-1) x r(t) | p0 |
| `p2` | S(t-1) x r(t)^0.5 | p0 |
| `R2` | R x r(t)^0.5 | R |
| `A2` | A x r(t)^0.5 | A |
| `B2` | B x r(t)^0.5 | B |

The exponent 0.5 is fixed in advance as a shrinkage toward the base, because the share is noisy.

Information only (never adopted, never used to choose anything):

- Calls: `p1c`, `p2c`, `R2c`, `A2c`, `B2c` = the same formulas with rc(t) instead of r(t).
- Precision-weighted: `p2w`, `R2w`, `A2w`, `B2w` = the half-elastic formulas with the exponent
  k_s = 0.5 x SNR_s / (1 + SNR_s) instead of 0.5, where SNR_s = `expected_snr` of state s in
  `signal/out/diagnostics_by_state_asof_nov.csv` (the diluted NASS change spread divided by the share's sampling
  SE). I use `expected_snr` and not `snr_d_share`, because the latter counts the share's own movement, which the
  signal agent showed is mostly the classifier's response to the season, not NASS's change. SNR_s is computed from
  2019-2025 data including NASS finals of the evaluation years, so these scores are in-sample.
- 2025 real-time replay (scored on 2025 only): the primary satellite formulas with
  r_mask(2025) = clip(sh_pred_hist(2025) / sh(2024), 0.5, 2), where sh_pred_hist(2025) = `sat_share_pred_hist`
  of `corn26/out/mask_error_2025.csv` (the 2025 share with the classifier's leave-one-area-out corn calls on the
  2026-style pool). This is what a real-time 2025 forecast without the CDL would have used.
- 2026 same-mask change (reported next to the forecast, never adopted): r_same(2026) =
  clip(share_2026 / sh_pred_hist(2025), 0.5, 2), so both years of the change carry a classifier mask.

### 1.3 Metrics

- Per year t, over the 15 states: state WAPE(c, t) = 100 x sum_s |c - S(t)| / sum_s S(t); total error
  TOT(c, t) = 100 x (sum_s c - sum_s S(t)) / sum_s S(t); and |TOT|.
- Per candidate, 2020-2024: mean state WAPE, mean |TOT|, mean signed TOT.
- Information: US48(c, t) = error of (c for the 15 states + Tier A s3 for the other 33 states) against the
  48-state NASS total, in percent; Tier A s3 alone is the comparator.
- Paired comparisons at 15 Nov, for each primary satellite candidate against its base (p1 and p2 against p0;
  R2 against R; A2 against A; B2 against B), also for every information candidate against its base, and for
  R, A and B against p0 (context):
  - d_y = WAPE(c, y) - WAPE(base, y), y = 2020-2024; dbar = mean d_y; SE = sd(d_y, ddof 1) / sqrt(5).
  - 90% CI over years: 10,000 bootstrap resamples of the 5 years with replacement (seed 20261115), percentile
    interval of the mean difference.
  - 90% CI over states: 10,000 bootstrap resamples of the 15 states with replacement (seed 20261115); in each
    resample WAPE is recomputed per year over the drawn states, then the 2020-2024 mean difference is taken.
  - The same for |TOT|.
  - Years better / worse / tied (WAPE), and per-state wins: state s is a win if
    sum over 2020-2024 of |c - S| < the same for the base (ties counted separately).

### 1.4 Adoption rule (mechanical; once; 15 November; 2020-2024)

1. A primary satellite candidate c (p1, p2, R2, A2, B2) is adopted over its base only if
   (a) mean WAPE(c) < mean WAPE(base) over 2020-2024, AND (b) dbar + 2 SE < 0.
2. Otherwise the result is "not shown", reported with the point estimate and both CIs. Five years is a short
   record and the rule has little power; a "not shown" is not proof of no effect.
3. The 2026 model for the 15 states is the adopted candidate with the lowest 2020-2024 mean WAPE (ties: A2, B2,
   R2, p2, p1). If none is adopted, it is A (Tier A s3) unchanged.
4. Best satellite candidate for the earliness report: the primary satellite candidate with the lowest 2020-2024
   mean WAPE at 15 Nov, whether adopted or not. It is rerun with the 15 Oct and 15 Sep shares and the base at the
   same as-of date (A and B from their owners' backtests at that date; R and p0 do not change), with the same
   metrics and paired comparison. Information only.

### 1.5 2025 (information only)

Every candidate is scored once on 2025 (r(2025) from the CDL-mask shares; bases from their 2025 files), plus the
2025 real-time replay above. Nothing is chosen from these numbers.

### 1.6 2026 forecast

- 2026 shares: the fields of `corn26/out/corn26_calls.csv` with is_corn = 1, joined to
  `data/samples/corn26_<fips>.parquet` (year 2026), restricted to complete areas with `signal.complete_sample`,
  scored by `signal.state_shares(rows, kernelag.field_model.load_series(data/s2_series/corn26_<fips>),
  signal.fit_allqc_model()[0], "nov")`, which cuts every series at 15 Nov 2026. The run asserts every
  last observation date is on or before 2026-11-15. r(2026) = clip(share_2026 / sh(2025), 0.5, 2) (calls:
  the same with the called share).
- Predictions for every candidate (primary and information) for the 15 states.
- 80% intervals. Backtest error: q10, q50, q90 of log(S / c) over the 75 state-years 2020-2024 at 15 Nov
  (candidate c's own). Mask error: m_s = log(sat_share_pred_hist / sat_share_true_all) per state at Nov in
  `corn26/out/mask_error_2025.csv` (calls: the `sat_share_calls_` columns); M = sqrt(mean over the 15 states of
  m_s^2). For a candidate with exponent k on r (1 for p1, 0.5 for p2/R2/A2/B2, k_s for the w variants, 0 for
  p0/R/A/B), w = 1.2816 x k x M. Then lo80 = c x exp(q50 - sqrt((q50 - q10)^2 + w^2)) and
  hi80 = c x exp(q50 + sqrt((q90 - q50)^2 + w^2)). With w = 0 this is c x exp(q10), c x exp(q90).
  Stress columns (information): w_stress = 1.2816 x k x sqrt(M^2 + O_s^2), where O_s = root mean square over
  2019-2024 of log(`ratio_det_to_true`) for state s in `corn26/out/cross_year_omission_replay.csv` (the
  missed-corn error when the 2025 classifier is applied to other years, which the 2025 replay understates).
  Leave-one-year-out coverage of the backtest intervals (quantiles from the other 4 years) is reported.
- US total: the 2026 model for the 15 states (rule 1.4.3) + Tier A s3 (`forecast_2026.csv`) for the other 33
  states. Its 80% interval: Tier A's US interval offsets, log(lo80 / US_A) and log(hi80 / US_A), applied to the
  new total and widened in quadrature by W = 1.2816 x sqrt(sum_s (c_s x k_s x M)^2) / total. The same US total is
  reported for every candidate (information). The 15 states' share of US silage acres is reported for 2025 and
  as the 2019-2024 mean of NASS finals (48 states).

<!-- END OF PRE-REGISTRATION -->

Everything below was written after the scores were computed. `eval.py` checks the section 1 hash on every run and
stops if it changed (`out/run.json`: `"unchanged": true`, sha256 `0f0ab071...6f5cea`).

## 2. Verdict

**No. The satellite signal does not improve state silage acreage. It makes every base model worse, in every one of
the 5 selection years.** None of the five pre-registered satellite candidates passes the adoption rule; all five are
"not shown". The paired differences are not borderline: every 90% interval, over years and over states, lies
entirely on the harmful side. So the 2026 forecast for the 15 states stays Tier A s3, unchanged (rule 1.4.3).

The reason is simple. From 2020 to 2024 the satellite ratio r moves about as much as NASS's own year-to-year change:
log SD 0.20 against 0.19. But it moves the wrong way: the correlation is -0.19 (Pearson) and -0.21 (Spearman). So
multiplying any forecast by r, even at half strength, adds error of the size of the signal itself. This matches the
`signal` agent's diagnosis. A false-positive floor dilutes the real silage change to 7-74% of its size, so the
expected signal-to-noise ratio is below 1 in every state, and the share's movement mostly reflects how the
classifier responds to the season. Five years is a short record (rule 1.4.2), but here the problem is not a lack of
power: the satellite candidates lose in all 5 years.

## 3. Backtest, 15 November, 15 sampled states (`out/summary.csv`, `out/by_year.csv`)

State WAPE = sum |pred - actual| / sum actual over the 15 states. TOT = error of the 15-state total. US48 = the
candidate for the 15 states plus Tier A s3 for the other 33 states, scored against the 48-state NASS total
(information only). All values are percentages.

| Candidate | Mean WAPE 2020-24 | Mean abs TOT | Mean signed TOT | Mean abs US48 | WAPE 2025 (info) | TOT 2025 (info) |
|---|---|---|---|---|---|---|
| p0 persistence | 11.91 | 3.91 | +0.93 | 3.58 | 14.65 | +0.51 |
| R reversion_only (report) | 10.55 | 4.79 | -1.30 | 3.71 | 15.22 | +3.85 |
| **A Tier A s3** | **10.08** | 4.77 | -0.60 | 3.70 | 15.21 | +4.97 |
| B Tier B c5b | 10.09 | 4.64 | -0.56 | 3.60 | 15.16 | +4.29 |
| p1 = S(t-1) x r | 21.56 | 9.00 | +0.52 | 7.58 | 27.38 | +11.47 |
| p2 = S(t-1) x r^0.5 | 15.54 | 5.46 | +0.22 | 4.73 | 19.94 | +5.46 |
| R2 = R x r^0.5 | 14.14 | 5.92 | -2.06 | 4.62 | 20.23 | +9.01 |
| A2 = A x r^0.5 | 14.09 | 6.15 | -1.35 | 4.70 | 20.34 | +10.16 |
| B2 = B x r^0.5 | 13.96 | 5.96 | -1.32 | 4.57 | 20.25 | +9.47 |
| *info:* p1c / p2c (called share) | 38.80 / 22.46 | 9.02 / 5.51 | | | 40.04 / 25.03 | |
| *info:* R2c / A2c / B2c | 21.04 / 20.73 / 20.70 | 5.88 / 5.95 / 5.81 | | | 25.09 / 25.35 / 25.56 | |
| *info:* p2w / R2w / A2w / B2w (precision-weighted) | 12.44 / 10.86 / 10.52 / 10.48 | 4.23 / 5.04 / 5.04 / 4.91 | | | 15.38 / 15.68 / 15.71 / 15.71 | |

State WAPE by year:

| Year | p0 | R | A | B | p1 | p2 | R2 | A2 | B2 | A2w | B2w |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2020 | 10.77 | 8.18 | 6.71 | 6.65 | 13.03 | 10.41 | 10.13 | 9.36 | 9.46 | 7.28 | 7.16 |
| 2021 | 13.54 | 11.38 | 10.90 | 11.32 | 29.23 | 20.97 | 19.13 | 18.78 | 19.19 | 12.68 | 13.10 |
| 2022 | 11.26 | 13.24 | 12.85 | 12.81 | 15.77 | 12.74 | 14.48 | 14.17 | 13.98 | 12.60 | 12.58 |
| 2023 | 12.40 | 9.16 | 9.18 | 9.18 | 30.39 | 20.63 | 13.85 | 15.16 | 14.51 | 9.75 | 9.59 |
| 2024 | 11.56 | 10.79 | 10.77 | 10.50 | 19.38 | 12.97 | 13.13 | 13.00 | 12.67 | 10.27 | 9.98 |
| 2025 (info) | 14.65 | 15.22 | 15.21 | 15.16 | 27.38 | 19.94 | 20.23 | 20.34 | 20.25 | 15.71 | 15.71 |

Correlation of log r with log(S(t) / S(t-1)) across the 15 states, by year: 2020 +0.45, 2021 -0.62, 2022 +0.13,
2023 0.00, 2024 -0.40, 2025 -0.46. Signs agree in 8, 3, 8, 2, 7 and 5 of 15 states. No r value was clipped in
2020-2025.

### Paired comparisons and the adoption rule (`out/comparisons.csv`)

d = candidate minus base, in WAPE points, 2020-2024. CIs are 90% bootstrap intervals (10,000 resamples, seed
20261115). Wins are years or states where the candidate has the lower error.

| Candidate vs base | d WAPE | SE | d + 2 SE | 90% CI over years | 90% CI over states | Years better / worse | States better / worse | d abs TOT [CI years] | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| p1 vs p0 | +9.65 | 3.08 | +15.82 | [+4.95, +14.37] | [+5.50, +14.14] | 0 / 5 | 4 / 11 | +5.09 [+1.70, +9.36] | not shown |
| p2 vs p0 | +3.64 | 1.75 | +7.13 | [+1.07, +6.40] | [+1.30, +6.24] | 1 / 4 | 6 / 9 | +1.55 [-1.18, +4.01] | not shown |
| R2 vs R | +3.59 | 1.19 | +5.97 | [+1.92, +5.43] | [+1.86, +5.44] | 0 / 5 | 3 / 12 | +1.13 [-1.83, +3.85] | not shown |
| A2 vs A | +4.01 | 1.25 | +6.51 | [+2.14, +5.81] | [+2.04, +6.08] | 0 / 5 | 3 / 12 | +1.38 [-1.42, +3.94] | not shown |
| B2 vs B | +3.87 | 1.21 | +6.29 | [+2.15, +5.71] | [+1.90, +5.93] | 0 / 5 | 3 / 12 | +1.32 [-1.55, +3.93] | not shown |
| *info:* A2w vs A | +0.44 | 0.40 | +1.23 | [-0.14, +1.06] | [+0.09, +0.80] | 2 / 3 | 4 / 11 | +0.27 [-0.30, +0.74] | information |
| *info:* B2w vs B | +0.39 | 0.40 | +1.18 | [-0.16, +1.00] | [+0.05, +0.74] | 2 / 3 | 4 / 11 | +0.27 [-0.30, +0.73] | information |
| *info:* R2w vs R | +0.31 | 0.42 | +1.16 | [-0.29, +0.98] | [+0.00, +0.64] | 2 / 3 | 6 / 9 | +0.25 [-0.31, +0.72] | information |
| *info:* p2w vs p0 | +0.53 | 0.48 | +1.48 | [-0.23, +1.30] | [+0.08, +1.02] | 3 / 2 | 6 / 9 | +0.32 [-0.23, +0.78] | information |
| *info:* A2c vs A | +10.65 | 2.46 | +15.56 | [+6.98, +14.23] | [+6.84, +14.94] | 0 / 5 | 1 / 14 | +1.18 [-2.07, +4.51] | information |
| *context:* A vs p0 | -1.83 | 1.01 | +0.19 | [-3.24, -0.22] | [-2.59, -1.16] | 4 / 1 | 13 / 2 | +0.85 [-0.40, +1.95] | information |
| *context:* B vs p0 | -1.81 | 0.98 | +0.15 | [-3.18, -0.25] | [-2.65, -1.09] | 4 / 1 | 14 / 1 | +0.73 [-0.71, +1.84] | information |
| *context:* R vs p0 | -1.36 | 0.93 | +0.50 | [-2.62, +0.11] | [-2.59, -0.27] | 4 / 1 | 12 / 3 | +0.88 [-1.56, +2.62] | information |

- **Adopted: none.** Every primary satellite candidate fails both parts of the rule: its mean WAPE is higher than
  its base's, and d + 2 SE is far above 0.
- The half-elastic candidates win only in California, Iowa and Nebraska (states summed over 2020-2024).
- The precision-weighted variant uses exponents of 0.045 (Iowa) to 0.225 (California). These are small because
  the expected SNR is small (0.10 to 0.82). It does less damage (+0.3 to +0.5 points) but still does not help. Its
  CI over states lies above 0 for A2w and B2w. It is also in-sample (rule 1.2), which flatters it.
- The called share (`sat_share_calls`) is much worse than the probability share (+10.5 points). Its year-to-year
  ratio is noisier.
- On the 15-state total, no satellite candidate beats its base, and persistence has the lowest abs TOT (3.91).
  The base models beat persistence on state WAPE but not on the 15-state total. This is known from the Tier A and
  Tier B READMEs for the 48-state total.

### Earliness, best satellite candidate B2 (rule 1.4.4)

B2 has the lowest 2020-2024 mean WAPE of the five primary satellite candidates, but it was not adopted. Earlier
dates use the signal agent's 15 Oct and 15 Sep shares and Tier B's backtest at the same date:

| As of | B (base) WAPE | B2 WAPE | d [90% CI years] [90% CI states] | Years better | B abs TOT / B2 abs TOT |
|---|---|---|---|---|---|
| 15 Nov | 10.09 | 13.96 | +3.87 [+2.15, +5.71] [+1.90, +5.93] | 0 / 5 | 4.64 / 5.96 |
| 15 Oct | 10.14 | 13.51 | +3.37 [+2.24, +4.55] [+1.60, +5.23] | 0 / 5 | 4.75 / 5.74 |
| 15 Sep | 10.21 | 16.30 | +6.08 [+4.33, +7.97] [+4.65, +7.70] | 0 / 5 | 4.71 / 11.41 |

Earlier is not better. On 15 Sep the share only counts harvests that have already happened, so it is a different
quantity (see the `signal` README).

### 2025, information only (`out/summary.csv`, period 2025)

2025 was scored once and nothing was chosen from it. The satellite candidates lose in 2025 as well: A2 20.34%
against A 15.21%, B2 20.25% against B 15.16%, R2 20.23% against R 15.22%. The base numbers here cover the 15
sampled states, not the stored 48-state score. The real-time replay uses the classifier's corn mask for the 2025
share, which is what a forecaster without the CDL would have had (`*_mask25`). It is no better: A2_mask25 20.88%,
B2_mask25 20.91%, R2_mask25 20.87%, p2_mask25 20.38%. The stored 2025 report score was not touched.

## 4. 2026 forecast (`out/forecast_2026.csv`, `out/sat_share_2026_asof_nov.csv`)

**2026 shares.** The 2026 shares cover the classifier's corn calls (`corn26_calls.csv`, is_corn = 1), all 10 areas in
every state, scored by `signal.state_shares` with the series cut at 15 Nov 2026. The last looks are 9-14 Nov 2026,
and the run asserts none is after 15 Nov. r(2026) = share_2026 / share_2025 (CDL mask in 2025): Nebraska 2.00
(clipped; raw 0.409 / 0.201), Minnesota 1.59, Iowa 1.50, South Dakota 1.38, Michigan 1.36, Wisconsin 1.26, Ohio 1.25,
North Dakota 1.20, Kansas 1.06, Pennsylvania 1.04, California 1.01, Colorado 0.97, New York 0.94, Idaho 0.91,
Texas 0.88.

**Selected 2026 model for the 15 states: A (Tier A s3), unchanged**, because no satellite candidate was adopted.
The intervals below follow rule 1.6: 10th/50th/90th percentiles of A's own log errors on the 15 states in
2020-2024, with leave-one-year-out coverage 0.79. Tier A's own published intervals use 13 years and size classes
and are wider. Use them if you want Tier A's calibration (`test_models/ownModels/silage/out/forecast_2026.csv`).
B2 is shown for information only, with its interval widened by the 2025 mask replay (M = 0.046,
w = 1.2816 x 0.5 x M = 0.030 in log) and a stress interval that adds the cross-year missed-corn error.

| State | NASS 2025 | **A (selected)** | A 80% | r 2026 | B2 (info) | B2 80% (mask-widened) | B2 80% stress | B2, same-mask change |
|---|---|---|---|---|---|---|---|---|
| Wisconsin | 885,000 | **836,400** | 713,600 - 1,029,800 | 1.257 | 936,600 | 767,700 - 1,224,000 | 767,300 - 1,224,500 | 949,600 |
| New York | 495,000 | **476,400** | 406,500 - 586,600 | 0.941 | 462,300 | 378,900 - 604,200 | 377,700 - 605,700 | 452,500 |
| South Dakota | 390,000 | **426,900** | 364,200 - 525,600 | 1.375 | 500,800 | 410,500 - 654,500 | 410,000 - 655,200 | 496,600 |
| California | 370,000 | **354,100** | 302,100 - 436,000 | 1.008 | 352,400 | 288,800 - 460,500 | 286,400 - 463,700 | 355,300 |
| Minnesota | 360,000 | **373,300** | 318,500 - 459,600 | 1.585 | 469,900 | 385,100 - 614,100 | 385,100 - 614,100 | 463,200 |
| Michigan | 340,000 | **336,400** | 287,000 - 414,200 | 1.356 | 391,700 | 321,000 - 511,900 | 320,900 - 512,000 | 384,700 |
| Pennsylvania | 315,000 | **326,100** | 278,200 - 401,500 | 1.041 | 332,500 | 272,500 - 434,500 | 271,900 - 435,200 | 337,100 |
| Idaho | 280,000 | **260,700** | 222,400 - 321,000 | 0.907 | 246,800 | 202,300 - 322,500 | 202,200 - 322,600 | 250,900 |
| Iowa | 250,000 | **298,200** | 254,400 - 367,200 | 1.503 | 366,000 | 300,000 - 478,300 | 300,000 - 478,400 | 365,900 |
| Texas | 245,000 | **238,900** | 203,800 - 294,100 | 0.882 | 224,600 | 184,100 - 293,500 | 176,500 - 303,800 | 222,100 |
| Kansas | 230,000 | **278,300** | 237,500 - 342,700 | 1.060 | 287,000 | 235,200 - 375,000 | 233,500 - 377,200 | 284,500 |
| Nebraska | 220,000 | **268,100** | 228,700 - 330,100 | 2.000 | 381,300 | 312,500 - 498,300 | 312,200 - 498,600 | 381,300 |
| Colorado | 200,000 | **198,900** | 169,700 - 244,900 | 0.974 | 197,800 | 162,100 - 258,400 | 157,200 - 265,000 | 201,900 |
| Ohio | 200,000 | **184,700** | 157,600 - 227,400 | 1.255 | 206,800 | 169,500 - 270,200 | 169,400 - 270,300 | 208,500 |
| North Dakota | 170,000 | **193,400** | 165,000 - 238,100 | 1.201 | 212,200 | 174,000 - 277,400 | 173,400 - 278,100 | 197,100 |
| **15 states** | 4,950,000 | **5,050,800** | | | 5,568,700 | | | 5,551,200 |

**US total, 2026 (selected): 6,297,400 acres, 80% interval 6,019,400 - 6,796,100.** This is A for the 15 states plus
Tier A s3 for the other 33 states, with Tier A's US interval offsets; there is no mask term, because A uses no
satellite input. Tier A's own US row says 6,297,900. The 500-acre difference comes from summing state values that
are rounded to 100 acres. NASS 2025: 6,187,000. **The 15 sampled states hold 80.0% of US silage acres in 2025** and
80.2% on average in 2019-2024 (NASS finals, 48 states). For information, the US totals with the satellite
candidates are 6,815,100 (B2), 6,816,000 (A2), 6,844,400 (R2), 6,677,200 (p2) and 7,273,200 (p1). They are 6-16%
above the selected total because r(2026) is above 1 in 11 of 15 states.

### Why the 2026 ratios are so large (post-hoc diagnostic, not pre-registered: `diag_2026.py`)

I wrote this check after seeing the 2026 shares. It computes the share with no corn mask, on the same 47,948
candidate fields, in 2025 and 2026 (`out/diag_2026_unmasked.csv`):

| State | Called-corn share 2026 minus CDL-corn share 2025 | Unmasked share 2026 minus 2025 | Share of fields called NOT corn in 2026 |
|---|---|---|---|
| Nebraska | +0.208 | +0.128 | 0.413 |
| Iowa | +0.167 | +0.095 | 0.511 |
| Minnesota | +0.138 | +0.078 | 0.530 |
| Michigan | +0.111 | +0.025 | 0.478 |
| Wisconsin | +0.081 | +0.094 | 0.472 |
| South Dakota | +0.070 | +0.073 | 0.409 |
| Ohio | +0.065 | -0.059 | 0.381 |
| Texas | -0.046 | -0.092 | 0.223 |

In the Corn Belt the share rose for the whole landscape, so the field model reads 2026 imagery as more silage-like
everywhere (a season or imagery effect). In Iowa the fields called corn in 2026 look as silage-like as those called
non-corn (0.500 against 0.511). In 2025, CDL corn scored 0.33 and non-corn about 0.52. Either the 2026 mask includes
many soybean fields, or the season changed how corn looks. In both cases, r(2026) here measures season and mask, not
silage. Michigan and Ohio, where the masked share rose much more than the unmasked one, point to mask composition.
The 2025 replay (M = 0.046) does not capture this, so the mask-widened B2 intervals are too narrow. This is one more
reason not to use the satellite candidates in 2026.

## 5. Deviations and checks

- **Method: no deviation.** One code fix came before the first successful run: the Tier A/B backtest files have
  both an `asof` (date) and an `asof_key` column, and renaming the key produced a duplicate column. The run crashed
  while loading the base predictions, before any score was computed.
- **Post-hoc:** `diag_2026.py` and `out/diag_2026_unmasked.csv` (section 4) were added after the scored run. They
  are information only and change no prediction or verdict.
- **Interval note:** rule 1.6 gives A intervals from 75 state-years (2020-2024), narrower than Tier A's own 13-year
  intervals. The US interval uses Tier A's own offsets.
- **Checks in code:** the pre-registration hash; that Tier A's `actual` and `last` equal NASS S(t) and S(t-1) for
  the 15 states; that the Tier B copies are identical before de-duplication; that no share (2019-2026) uses a look
  after its as-of date; and that the base files are complete. A by-hand recomputation of Tier A's 15-state WAPE
  from its own backtest file (10.08) matches `summary.csv`, and so does p1 for Iowa 2023.
- **Tests:** `test_eval.py`, 13 tests: hash unchanged, clipping, consecutive-year ratios, every candidate formula
  by hand, WAPE/TOT by hand, the paired bootstrap (identical and uniformly better toy cases), interval widening by
  hand, the final-model rule with ties, Tier B de-duplication, base completeness, and the 2026 and 2019-2025 as-of
  cuts.

## 6. Limitations

- Only 5 selection years (2020-2024). The rule treats years as exchangeable. The verdict does not depend on it,
  because the satellite candidates lose in all 5 years and in 2025.
- In 2019-2025 the shares use the CDL corn mask (perfect, published after the season). A real-time forecast would
  carry the classifier's mask error as well. The 2025 real-time replay is no better, and 2026 shows a
  landscape-wide shift that the 2025 replay does not measure (section 4).
- The field model is trained on Quebec 2023 only. Its false-positive floor (about 0.2 share points) dilutes real
  silage changes, which is the main reason the ratio has no signal (`signal` README).
- The truth is NASS's latest revised finals, the same values the incumbent scores against. The base predictions
  are taken as their owners stored them; nothing was refitted here. The Tier B backtest file stores every row
  three times (identical values). I de-duplicated it here and did not edit it.
- R's 2025 and 2026 values come from the report's stored files (`data/models/state_score_2025.csv`,
  `state_forecast_2026.csv`). They were read, not modified.
- The precision-weighted variant uses SNRs computed with 2019-2025 data, including NASS finals of the evaluation
  years, so its scores are in-sample.

## 7. Files and how to run

From the repo root:

```bash
.venv/Scripts/python.exe test_models/ownModels/satellite/eval/eval.py --prereg      # done once, before scoring
.venv/Scripts/python.exe test_models/ownModels/satellite/eval/eval.py --workers 15  # ~2 min (2026 shares cached)
.venv/Scripts/python.exe test_models/ownModels/satellite/eval/eval.py --recompute-2026  # recompute 2026 shares
.venv/Scripts/python.exe test_models/ownModels/satellite/eval/diag_2026.py --workers 15  # post-hoc, ~4 min
.venv/Scripts/python.exe -m pytest -q test_models/ownModels/satellite/eval/test_eval.py
```

| File | Content |
|---|---|
| `out/preregistration.sha256` | hash of section 1, written before any score |
| `out/backtest.csv` | state, year, asof, candidate, family, base, k, r, base_pred, pred, last, actual, err, log_err, period (2020-2024 at three dates; 2025; 2025 mask replay) |
| `out/by_year.csv` | per candidate, as-of and year: WAPE, TOT, US48 |
| `out/summary.csv` | means for 2020-2024 and 2025 per candidate and as-of date |
| `out/comparisons.csv` | paired differences with bootstrap CIs over years and over states, wins, adoption verdict |
| `out/forecast_2026.csv` | 2026 predictions for every candidate and state with 80% intervals (backtest, mask-widened, stress), r, shares, same-mask variant; US rows per candidate (`final_model` marks the selected one) |
| `out/sat_share_2026_asof_nov.csv` | 2026 state shares on the classifier's corn calls |
| `out/diag_2026_unmasked.csv` | post-hoc: unmasked shares 2025 and 2026, called-non-corn share |
| `out/run.json` | hash check, adopted list, selected model, M, m_s, O_s, 15-state share of US silage |
