# Is silage error a model problem or a data problem?

Run: `.venv/bin/python -W ignore test_models/accuracy/noise_floor.py` (about 40 s). Writes `results.json` and `by_year.csv`.
Data: NASS Quick Stats state survey 2000–2024 and `test_models/danielModel/out/panel_nov.csv`. 2025 is never read.
Revised (current-vintage) data, so this is a replay, not an archived real-time test.

## 1. The target is noisy

| Check | Value |
| --- | ---: |
| NASS survey vs Census silage acres, state gap, 2017 | 15.6% (US 4.5%) |
| Same, 2022 | 32.1% (US 14.6%) |
| Share of yearly change variance common to all states | 0.11 |
| Lag-1 autocorrelation of a state's own change (noise −0.5, lasting change 0) | −0.40 |
| Implied transient noise in a state's acres (log sd) | 0.127 |
| State error a forecaster must accept from that noise alone | ≈ 10.1% |
| Same as last year, 2012–2024 | 15.84% |
| Same as last year + an oracle that knows each year's true US change | 16.34% |

- Most of a state's yearly change reverses the next year. That is sampling noise or one-off chopping, not a trend.
- Knowing the national swing perfectly does not lower state error. National signals (prices, policy) cannot fix state error; they can only fix the US total.
- Every model the team tried (ridge, LAD, Huber, XGBoost, ensembles, satellite) lands at 13–14%. The floor is about 10%, so about 3 points are left to win at state level.

## 2. What closes the gap

Forecasts for 2012–2024. Each year's two parameters are chosen on earlier years only.

| Candidate | State WAPE | US abs error | Params |
| --- | ---: | ---: | --- |
| Same as last year | 15.84% | 5.76% | none |
| LAD core (`test_models/accuracy/state`, previous best) | 13.02% | 5.12% | regression |
| Smoothed level (EWMA in logs) | 13.91% | 4.48% | α 0.40–0.50 |
| **Smoothed level + drought chopping** | **13.23%** | **3.44%** | α 0.40–0.50, γ 0.04–0.05 |

Drought chopping: `γ × max(0, yield shortfall − 0.10) × grain acres`. The shortfall is NASS's November yield forecast against the state's 10-year linear trend. Drought corn gets chopped for silage instead of combined. The idea comes from `test_models/varunModel/state_signals.py`.

- US total vs LAD core: gain of 1.67 points, SE 0.76, over 13 years. That passes the two-standard-error rule.
- State error vs LAD core: −0.20 points, SE 0.37. No difference.
- On 2017–2024, against the root `kernelag` model (`reversion_only`): state 12.80% vs 13.12% (gain 0.33, SE 0.20), US 3.33% vs 3.90% (gain 0.57, SE 0.31). It is better on both, but under two SE on 8 years.
- The parameters barely move from year to year (α 0.40–0.50, γ 0.04–0.05), which argues against overfitting.

## 3. The classifier

The field classifier is not the bottleneck for the deliverable. The root forecast does not use it, because there is no state satellite table yet.
From `DOCS/coord/status/cc-varun.md` (2026-11-15T05:13Z): on held-out years, the classifier's year-to-year noise is 0.40 in units of true silage share, and the provisional state satellite change has the wrong sign (−0.36, 65 state-years).
That noise is about three times the target's own transient noise. A satellite signal cannot help at state level until the year effect is removed. The cause seen there is grain moisture before the drop, which drifts 0.19 to 0.37 between years.

## Conclusion

- **State error is a data limit.** About 10 of the 13 points are noise in NASS's state silage series itself.
- **The US total is a model limit, and it can be fixed.** Smoothing plus drought chopping cuts US error by about a third.
- **The satellite classifier needs per-year calibration** before it can add anything at state level.
