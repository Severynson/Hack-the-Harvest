# Kernel: five-minute presentation

Generated 2026-11-15 from test_models/variations outputs (see the results page); supersedes the 08:15Z version.

**Total spoken time: 295 s (limit 300 s).** Seconds per beat are in the headings, timed at about 140 words a minute.
Spine: intent, then switch. Acreage error is mean state WAPE / mean absolute US error unless stated otherwise.
Truth is NASS's final number. Backtests use only files public by each date; 2025 was scored once.

Sources (every number below is read from these files):

- Grain A-G9 (`g9_national_reconciliation`): `test_models/variations/grain_variants/out/forecast_2026.csv` (US row = sum of 41 states), `grain_variants/out/summary.csv`
- Silage B-S6 (`SC_B`), drought scenario A-S7 (`SC_A`): `test_models/variations/silage_combos/out/forecast_2026_us.csv`, `silage_combos/out/interval_coverage.csv`
- 2025 scored once, comparison pair (Tier C): `test_models/variations/submission_preview/out/scorecard.csv`, `data/models/deliverable_2026.csv`
- Satellite: `test_models/variations/sat_full/eval/README.md`. Fade rule: `test_models/variations/fade_rule/out/`
- Field model: `test_models/variations/field_variants/out/holdout_2025.csv`, `field_variants/out/maryland.csv`

## [28 s] Intent, then switch

SCRIPT: USDA asked for corn for grain and corn for silage, per state and for the US, before January. Two forces split them. First, intent: by mid-July farmers certify to FSA what they plan to harvest, and that drives grain. Then the switch: in a bad season, growers chop grain corn for nearby dairies, and that drives silage, though the dairy features we tested added nothing.

VISUAL: One line, two halves. Left: "Intent: FSA certification by mid-July, drives grain". Right: "Switch: bad season, chopped for dairies, drives silage". Small grey caption: "Dairy features: tested, no gain".

## [19 s] The answer

SCRIPT: For 2026, as of today, November 15th, from our own models. Grain: 88.75 million acres, 80% range 87.3 to 90.2. Silage: 6.26 million, range 6.1 to 6.7. Neither uses NASS's acreage forecast. NASS's November grain figure, 88.51, is our benchmark, not our number.

VISUAL: Two hero numbers in Plex Mono, each with a horizontal 80% range bar: grain 88.75M (87.28–90.24M), silage 6.26M (6.10–6.66M). A thin grey tick on the grain bar: "NASS Nov 88.51M (benchmark)". Caption: "As of 15 Nov 2026 · our own models · per-state tables in the notebook".

## [37 s] Grain: intent, measured

SCRIPT: Grain is public FSA certified grain acres times each state's own three-year NASS-to-FSA ratio, plus one national correction. Over 2017 to 2024 we get 1.69% state error and 0.96% on the US total. NASS's November forecast gets 1.66 and 0.82. On states that's a tie; NASS is better on the US total, and over 2012 to 2024. On 2025, scored once, we got 1.62 and NASS 1.64. NASS's current-year inputs didn't improve our grain model: the best version using them scored 1.74, against our 1.69.

VISUAL: Three-row table, state error / |US error|. Row 1: "Ours (A-G9), 2017–24: 1.69% / 0.96%". Row 2: "NASS Nov, 2017–24: 1.66% / 0.82%". Row 3: "2025, scored once: 1.62% vs NASS 1.64%". Footnotes: "2012–24: ours 1.88% / 1.04%, NASS 1.60% / 0.57%" and "NASS's current-year inputs didn't improve our grain model (best Tier B 1.74% vs our Tier A 1.69%, 2017–24)".

## [26 s] Ready by 15 September

SCRIPT: By September 15th our state error is already 1.67%: level with NASS's November forecast, and below NASS's September forecast, 2.53%. Most of that edge is 2017 to 2020; since 2021 NASS's September state numbers have matched its November ones. It can't come sooner: the intent file only exists after the mid-July certification, so in July and August your survey wins.

VISUAL: Line chart of state grain error by as-of date (Jul 15 to Dec 15, 2017–24), A-G9 against NASS's forecast. Callout at Sep 15: "1.67% · NASS Sep 2.53% · NASS Nov 1.66%". Shaded Jul–Aug band: "FSA file missing or partial: NASS leads". Footnote: "Only data public by each date; truth = NASS final".

## [39 s] Silage: the switch

SCRIPT: Silage: NASS publishes nothing until January. Our model takes each state's smoothed normal level, plus extra chopping when NASS's in-season yield forecast falls short. It uses NASS's yield forecast, not its acreage forecast. From 2017 to 2024 it misses states by 12.8% and the US total by 3.4%. In 2025, scored once, the US miss was plus 2.1%. Adding NASS's grain forecast changes nothing. A Drought Monitor version says 6.43 million; it stays a scenario, because that drought sits over largely irrigated Nebraska corn, where NASS's yield forecast shows no shortfall.

VISUAL: Hero 6.26M with range bar 6.10–6.66M. A dashed tick at 6.43M: "Drought scenario (Drought Monitor D2+), 6.25–6.90M". Small line: "Backtest 2017–24: 12.81% state / 3.36% US · 2025: US +2.06% · with NASS's grain forecast: 12.80% / 3.34%".

## [27 s] Honest ranges, and why we can't do better

SCRIPT: Every number carries an 80% range. Leaving out one year at a time, about 79% of state results fell inside it, for grain and for silage. Silage won't get much tighter: even knowing this year's true non-grain acres, state error would still be 9.7%, because the state series itself swings yearly. We're at 12.8%, so any model has about three points left.

VISUAL: Two horizontal bars on one scale (state error, 2017–24): "Oracle, true non-grain acres known: 9.68%" and "Ours (B-S6): 12.81%". Footer: "Leave-one-year-out 80% coverage: grain 0.79, silage 0.79 (backtest, not live)".

## [41 s] What space sees, and what it doesn't

SCRIPT: We tested satellites as they would run live: 300 sample areas, 15 states, with a real-time corn mask. It ranks states well, Spearman 0.73 to 0.86, but it misses the switch: its correlation with NASS's yearly change runs minus 0.27 to plus 0.07. The measured share is about 0.26 plus 0.53 times the true share. Adding it made every state silage model 1.6 to 2.5 points worse, so no forecast has a satellite term. The obvious rule, green to bare in 17 days or less, scores 0.62 balanced accuracy and over-counts silage by about 40%.

VISUAL: Scatter of satellite silage-like share against NASS silage share, fitted line "measured ≈ 0.26 + 0.53 × true". Beside it: "Ranks states: Spearman 0.73–0.86" · "Yearly change: r −0.27 to +0.07" · "Added to models: 1.6–2.5 pts worse" · "Fade rule alone: balanced accuracy 0.618 vs field model 0.790, same 15,552 Quebec field-years; counts silage ×1.41; median fade 12 days silage, 17 grain".

## [33 s] Field check (proxy labels)

SCRIPT: At field level, a Sentinel-2 harvest-timing model trained on Quebec flags chopped fields by October 15th, in about a hundredth of a second per field. On 2,826 Quebec fields from 2025, never used for choosing, it scores 0.73 precision, 0.73 recall and a 0.23 false-positive rate. On a Maryland research farm it found 11 of 12 silage fields, with one false alarm. These are proxy labels, not truth, and we never add fields up into acres.

VISUAL: One field's NDVI curve with its detected cut date. Two count boxes: "Quebec 2025, n=2,826: TP 951 · FP 352 · FN 355 · TN 1,168" and "Maryland, 44 field-years: TP 11 · FP 1 · FN 1 · TN 31". Label: "Proxy labels · never summed into acres".

## [45 s] What we claim, and what we don't

SCRIPT: What we claim: two numbers per state and for the US on November 15th, from our own models. Grain matches NASS's November state accuracy, and gets there by September 15th. Silage misses the US total by 3.4 to 3.6%, and we've shown its floor. What we don't claim: beating NASS, which is better on the US total and over 2012 to 2024, or new data, since FSA is already one of your inputs. Every number was backtested on data public at the time, and 2025 was scored once. Intent gives grain, the switch gives silage: a second reading before January, with no acreage survey.

VISUAL: Two columns. "We claim": two numbers by 15 Nov · NASS's November state accuracy (1.69% vs 1.66%) reached by 15 Sep (1.67%) · silage US miss 3.36% (2017–24) to 3.56% (2012–24) · ranges that held 0.79 in backtest. "We don't claim": beating NASS · new data (FSA is one of NASS's inputs) · satellite in the forecast. Footer: workspace file paths.

## Likely USDA questions

**Q: FSA certified acres are already one of our indications. What is new here?**
A: The data isn't new. What's new is a reproducible model on public FSA files that needs no survey and reaches your November state accuracy by 15 September (1.67% vs 1.66%). It's a cross-check, not a replacement.

**Q: Didn't you pick A-G9 after seeing the 2017–24 results? Isn't that in-sample?**
A: We chose it on 2012–24 under a pre-registered rule (beat the simpler FSA-ratio model, A-G3, by more than twice the year-to-year noise), and it passed only narrowly: it fails a three-times bar, and it fails if 2014 or 2019 is dropped. The only clean test is 2025, scored once: 1.62% vs your 1.64%. That's why we call it a tie, and you are better over 2012–24 (1.60% vs 1.88%).

**Q: Was the September FSA file really public on 15 September?**
A: We dated each FSA file conservatively, later than its data date, and an audit moved some files later still. Our 15 October error is level with our 15 September error, so the parity claim doesn't depend on September timing.

**Q: Your silage model uses NASS's yield forecast, and 12.8% state error is large. Is it really yours, and is it useful?**
A: It uses your yield forecast, not your acreage forecast, and adding your grain forecast changes nothing (12.80% / 3.34% vs 12.81% / 3.36%). Even knowing this year's true non-grain acres exactly gives 9.68% state error, so the state series itself sets the floor. The US miss is 3.36% (2017–24) and +2.06% in 2025.

**Q: Why isn't the drought version your headline? It says 6.43M.**
A: It's inflated by drought over largely irrigated Nebraska corn (about 57% irrigated, 2017 survey), where your yield forecast shows no shortfall. We show it as a scenario, 6.43M (6.25–6.90M), never as our number.

**Q: Why not just hand us our own November forecast plus your silage?**
A: That was our previous deliverable, and it stays in the notebook as a comparison: 88.51M grain (87.27–89.76M) and 6.26M silage (5.95–6.59M). In 2025 its grain miss was 1.64% / −0.99%, against ours at 1.62% / −0.88%.

**Q: You were pointed at dairies. Did you use them?**
A: We tested them: distance to dairies in the field model and dairy demand in the state silage model. Neither added accuracy under our selection rule, so neither is in a forecast.

**Q: So satellites don't work for this?**
A: Our implementation at state level, on 15 November, doesn't: it ranks states (Spearman 0.73–0.86) but its yearly change doesn't track yours (r −0.27 to +0.07), and the measured share is about 0.26 + 0.53 × true. Per-state harvest calendars are the next step, untested; our real-time corn mask fails its own check in 11 of 15 states.

**Q: 11 of 12 on 44 field-years from one farm you had already looked at?**
A: Agreed, that's a sanity check, not a claim. The real test is 2,826 Quebec fields from 2025 never used for choosing: 0.73 precision, 0.73 recall, 0.23 false-positive rate, against proxy labels. We never add fields up into acres.

**Q: Isn't the green-to-bare fade rule enough?**
A: We pre-registered it and tested it on the same 15,552 Quebec field-years: balanced accuracy 0.618 against 0.790 for our field model, and it counts silage 1.41 times too often. Median fade is 12 days for silage and 17 for grain, so the two overlap too much for one threshold.
