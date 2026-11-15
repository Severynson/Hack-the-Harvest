# Fade rule: is "green to bare in under 2.5 weeks" a silage classifier?

The claim under test (relayed from a friend, called "100% accurate"): "It went from green to bare in
under about 2 1/2 weeks. A chopper takes the whole green crop at once, while grain corn dries out and
browns slowly over 3-4 weeks before the combine comes."

## 1. Pre-registration

<!-- PREREGISTRATION:BEGIN -->
Written 2026-11-15T14:32Z, before any score of these rules was computed. Its sha256 is in
`preregistration.sha256`; `fade_rule.py score` refuses to run if this block has changed.

**Evidence (reused, not rewritten).** Per field-year features from `kernelag.features.kernel_features`
(full season, `min_valid=0.5`, cloud/haze dips removed by `drop_dips`), through
`kernelag.field_model.evidence_table`:
- `fade_days`: days from the last clearly green look (NDVI >= 0.6) after the June-mid-September peak to
  the first clearly brown/bare look (NDVI <= 0.4) after it, before day-of-year 300. Missing if either look
  does not exist.
- `drydown_days`: days from the first look below 90% of the peak to the biggest single NDVI drop (the cut).
  The existing code sets it to 0 when no look before the cut is below 90% of the peak; that is kept as is.
  Missing only when no drop can be found (fewer than 2 looks after the peak).

**Rules (thresholds fixed from the friend's words, not tuned).**
- **R1** (the rule as stated): silage iff `fade_days <= 17`; grain iff `fade_days > 17`; missing
  `fade_days` = not assessable.
- **R2** (the "browns slowly over 3-4 weeks" half): silage iff `drydown_days < 21`, else grain; missing
  `drydown_days` = not assessable.
- **R3** (both halves): silage iff R1 says silage AND R2 says silage. Assessable iff R1 and R2 are both
  assessable.

Each rule is scored twice: (a) on its assessable rows only, with the assessable share reported; (b) on all
rows with not-assessable counted as grain. (a) is the headline number; (b) is what an acreage count would see.

**Data.**
- Quebec: labels `data/labels/qcm_<year>.parquet`, 2019-2026, series `data/s2_series/qcm_<year>/`. Rows are
  labeled field-years that have a series (the `evidence_table` roster, the same roster as the f0/f1
  predictions). All 8 years pooled and each year separately.
- Maryland: `data/labels/barc_2021_2023.parquet`, all 44 labeled field-years, series
  `data/s2_series/barc_2021_2023/`, roster from `kernelag.evaluate.evaluation_table`. Test only.

**Metrics** (silage = positive class): confusion counts TP FP FN TN; balanced accuracy
(silage recall + grain recall) / 2; silage precision; silage recall; false-positive rate FP / (FP + TN);
silage count ratio (TP + FP) / (TP + FN), per year, because state acreage depends on counts.

**Comparison on the same field-years.** f0_all and f1_xgb_mono leave-one-year-out calls from
`test_models/variations/field_variants/out/predictions_quebec.csv`, joined on `field_id` + `year`
(7 years; 2025 is not in that file). Scored on exactly the rows where the rule is assessable and a
prediction exists, and again on all joined rows with not-assessable = grain. Maryland: no per-field f0/f1
calls are stored, so f0_all and f1_xgb_mono are refitted on the 7 selection years with `variants.py`'s own
`fit`/`predict` and cached features; the refit is accepted only if it reproduces the stored Maryland
confusion counts in `field_variants/out/maryland.csv` (f0_all TP10 FP1 FN2 TN31, f1 TP11 FP1 FN1 TN31),
then scored on the rule's assessable Maryland rows.

**Decision rules for the verdict.**
- "100% accurate" is supported only if a rule makes zero errors on its assessable rows, in Quebec pooled
  and in Maryland. Any error rejects the literal claim.
- A rule is "competitive" if its balanced accuracy on the same rows is within 0.02 of f1_xgb_mono, in
  Quebec pooled and in Maryland.
- A rule is "count-safe" if its silage count ratio is between 0.90 and 1.10 in every Quebec year
  (score (b), all rows).

**Information only (after the pre-registered scores; never used to change R1-R3).**
- Threshold sweep `fade_days <= t`, t = 7..35 days: best balanced accuracy on Quebec 2019-2024 assessable
  rows, then that t reported on Quebec 2025-2026 and Maryland.
- Medians and interquartile ranges of `fade_days` and `drydown_days` by true class, Quebec and Maryland.
- Failure modes with counts: observation gaps (`cut_gap_days`, and whether any look lies between the
  last green and first bare look, so that `fade_days` is just a revisit or cloud gap), late (frost-like)
  versus early fades, silage cut after browning, and reasons a field-year is not assessable.
<!-- PREREGISTRATION:END -->

## 2. What was run

```
.venv/Scripts/python.exe -I test_models/variations/fade_rule/fade_rule.py build   # 49 s, features cache
.venv/Scripts/python.exe -I test_models/variations/fade_rule/fade_rule.py score   # 10 s, everything in out/
```

- Features: `kernelag.field_model.evidence_table` / `kernelag.evaluate.evaluation_table`, unchanged. The cache
  (scratchpad, `agents/fade_rule/cache/`) only adds a diagnostic: how many clear looks lie between the last
  green and the first bare look (`looks_between`), checked to give exactly the same `fade_days`.
- Rows: Quebec 22,026 field-years (8 years, labeled and with a series); Maryland 44.
- f0_all / f1_xgb_mono: Quebec leave-one-year-out calls from `field_variants/out/predictions_quebec.csv`
  (19,200 rows, 7 years). The Maryland refit reproduced the stored counts exactly (f0_all TP10 FP1 FN2 TN31,
  f1 TP11 FP1 FN1 TN31). Extra, information only: the same refit gives the 2025 leave-out calls and
  reproduced `holdout_2025.csv` exactly (f0_all TP996 FP395 FN310 TN1125, f1 TP951 FP352 FN355 TN1168).
- Outputs (`out/`): `rules_scores.csv`, `comparison_same_rows.csv`, `threshold_sweep.csv`,
  `distributions.csv`, `failure_modes.csv`, `r1_subsets.csv`, `summary.json`.

## 3. Pre-registered results

Silage = positive class. BA = balanced accuracy, FPR = false-positive rate, ratio = silage calls / true silage.

**Quebec, 8 years pooled**

| rule | assessable | scoring | TP | FP | FN | TN | BA | precision | recall | FPR | ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 fade <= 17 d | 0.808 | assessable | 5552 | 5430 | 1881 | 4926 | 0.611 | 0.506 | 0.747 | 0.524 | 1.478 |
| R1 | | n/a = grain | 5552 | 5430 | 3597 | 7447 | 0.593 | 0.506 | 0.607 | 0.422 | 1.200 |
| R2 drydown < 21 d | 0.998 | assessable | 7209 | 8284 | 1924 | 4558 | 0.572 | 0.465 | 0.789 | 0.645 | 1.696 |
| R2 | | n/a = grain | 7209 | 8284 | 1940 | 4593 | 0.572 | 0.465 | 0.788 | 0.643 | 1.693 |
| R3 both | 0.808 | assessable | 4374 | 3684 | 3059 | 6672 | 0.616 | 0.543 | 0.589 | 0.356 | 1.084 |
| R3 | | n/a = grain | 4374 | 3684 | 4775 | 9193 | 0.596 | 0.543 | 0.478 | 0.286 | 0.881 |

**Quebec by year** (R1 BA on assessable rows; silage count ratio with n/a = grain)

| year | R1 assessable | R1 BA | R1 ratio | R2 ratio | R3 ratio |
|---|---|---|---|---|---|
| 2019 | 0.749 | 0.546 | 1.506 | 2.222 | 1.337 |
| 2020 | 0.954 | 0.520 | 1.222 | 2.031 | 1.030 |
| 2021 | 0.844 | 0.679 | 0.728 | 1.284 | 0.445 |
| 2022 | 0.649 | 0.678 | 0.707 | 1.834 | 0.533 |
| 2023 | 0.699 | 0.569 | 1.283 | 1.730 | 0.876 |
| 2024 | 0.901 | 0.692 | 1.189 | 1.565 | 0.857 |
| 2025 | 0.792 | 0.522 | 1.558 | 1.604 | 1.100 |
| 2026 | 0.908 | 0.592 | 1.303 | 1.415 | 0.856 |

**Maryland, 44 field-years**

| rule | assessable | scoring | TP | FP | FN | TN | BA | precision | recall | FPR | ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | 0.955 | assessable | 6 | 14 | 5 | 17 | 0.547 | 0.300 | 0.545 | 0.452 | 1.818 |
| R1 | | n/a = grain | 6 | 14 | 6 | 18 | 0.531 | 0.300 | 0.500 | 0.438 | 1.667 |
| R2 | 1.000 | assessable | 9 | 17 | 3 | 15 | 0.609 | 0.346 | 0.750 | 0.531 | 2.167 |
| R3 | 0.955 | assessable | 6 | 7 | 5 | 24 | 0.660 | 0.462 | 0.545 | 0.226 | 1.182 |
| R3 | | n/a = grain | 6 | 7 | 6 | 25 | 0.641 | 0.462 | 0.500 | 0.219 | 1.083 |

**Same field-years as f0_all and f1_xgb_mono**

| rows | model | TP | FP | FN | TN | BA | precision | recall | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Quebec 7 y, R1-assessable (15,552) | R1 | 4545 | 4402 | 1808 | 4797 | 0.618 | 0.508 | 0.715 | 0.479 |
| | f0_all | 4832 | 1958 | 1521 | 7241 | 0.774 | 0.712 | 0.761 | 0.213 |
| | f1_xgb_mono | 4849 | 1684 | 1504 | 7515 | 0.790 | 0.742 | 0.763 | 0.183 |
| Quebec 7 y, R3-assessable (15,552) | R3 | 3644 | 2978 | 2709 | 6221 | 0.625 | 0.550 | 0.574 | 0.324 |
| Quebec 7 y, all rows (19,200), n/a = grain | R1 | 4545 | 4402 | 3298 | 6955 | 0.596 | 0.508 | 0.580 | 0.388 |
| | f0_all | 5430 | 2517 | 2413 | 8840 | 0.735 | 0.683 | 0.692 | 0.222 |
| | f1_xgb_mono | 5635 | 2337 | 2208 | 9020 | 0.756 | 0.707 | 0.719 | 0.206 |
| Maryland, R1-assessable (42) | R1 | 6 | 14 | 5 | 17 | 0.547 | 0.300 | 0.545 | 0.452 |
| | f0_all | 10 | 1 | 1 | 30 | 0.938 | 0.909 | 0.909 | 0.032 |
| | f1_xgb_mono | 10 | 1 | 1 | 30 | 0.938 | 0.909 | 0.909 | 0.032 |
| Maryland, all 44 | R2 | 9 | 17 | 3 | 15 | 0.609 | 0.346 | 0.750 | 0.531 |
| | f1_xgb_mono | 11 | 1 | 1 | 31 | 0.943 | 0.917 | 0.917 | 0.031 |
| Quebec 2025 (info), R1-assessable (2,237) | R1 | 1007 | 1028 | 73 | 129 | 0.522 | 0.495 | 0.932 | 0.889 |
| | f1_xgb_mono | 880 | 312 | 200 | 845 | 0.773 | 0.738 | 0.815 | 0.270 |

Per year on R1-assessable rows, R1 trails f1_xgb_mono by 0.119 (2021) to 0.224 (2023) BA; R1 is never ahead.

**Pre-registered decisions**
- "100% accurate": **rejected.** Every rule makes thousands of errors in Quebec (R1: 7,311 of 17,789
  assessable field-years wrong) and R1 gets 19 of 42 Maryland field-years wrong.
- Competitive (within 0.02 BA of f1 on the same rows): **no** for all three. R1 is 0.172 behind in Quebec and
  0.391 behind in Maryland; R3 is 0.165 and 0.279 behind.
- Count-safe (ratio 0.90-1.10 every year): **no** for all three (R1 0.707-1.558, R2 1.284-2.222, R3 0.445-1.337).

## 4. Information only (not pre-registered as tests)

**Threshold sweep** (`silage iff fade_days <= t`, assessable rows; `out/threshold_sweep.csv`). Values move in
steps because fade_days is a difference of revisit dates (mostly multiples of 5 days, with 2-3-day
overlaps). Best on Quebec 2019-2024: t = 15 (16 selects the same rows), BA 0.645, ratio 1.211. On 2025-2026
it gives BA 0.574 (TP1867 FP1705 FN398 TN814, ratio 1.577); on Maryland BA 0.579 (TP6 FP12 FN5 TN19). The
friend's 17 gives 0.622 / 0.561 / 0.547 on the same three sets. No threshold in 7-35 reaches 0.65 on the
tuning years or 0.67 on Maryland.

**Distributions** (median [p25, p75] days; `out/distributions.csv`)

| | Quebec silage | Quebec grain | Maryland silage | Maryland grain |
|---|---|---|---|---|
| fade_days | 12 [7, 18] (n 7433) | 17 [12, 22] (n 10356) | 13 [5, 20] (n 11) | 20 [13, 25] (n 31) |
| share fade <= 17 | 0.747 | 0.524 | 0.545 | 0.452 |
| drydown_days | 5 [0, 20] | 15 [3, 27] | 8.5 [0, 26] | 20 [5, 26.25] |
| cut_gap_days | 10 [5, 15] | 12 [7, 17] | 5 [5, 20] | 5 [5, 20] |

The direction the friend describes is real (silage fades faster on average) but the two classes overlap
almost completely: half of Quebec grain field-years also go from NDVI >= 0.6 to <= 0.4 in 17 days or less.

**Failure modes of R1** (`out/failure_modes.csv`, `out/r1_subsets.csv`)
- Grain called silage, Quebec 5,430: 4,235 (78%) reached the bare look after 1 October, when a killing frost
  can brown a standing grain crop in days; 1,195 earlier. Grain fields whose fade ended before 1 October are
  just as fast: 89% have fade_days <= 17 (47% after 1 October). NDVI <= 0.4 is reached by brown standing corn,
  not only by bare soil: the slow 3-4 week drydown the friend describes happens mostly after NDVI is already
  low, so the green-to-brown step itself is fast for grain too. Maryland: 14 (10 before day 274).
- Silage called grain, Quebec 1,881: 940 have no look between the last green and first bare look, i.e.
  clouds or revisits left a gap > 17 days around the cut; 941 show a measured slow fade (>= 1 look in
  between); 567 have drydown_days >= 21 and 270 green_at_cut < 0.7 (cut after browning). 1,392 have
  cut_gap_days >= 15. Maryland: 5 (4 gap-limited).
- Gaps: 9,099 of 17,789 assessable Quebec fades (51%) have no look in between, so fade_days is just the gap
  between two clear looks. Conditioning on a measured fade does not rescue the rule: on fades with >= 1 look
  in between BA is 0.570; with a bare look on/before 1 October and cut_gap_days <= 10 it is 0.494
  (TP400 FP512 FN30 TN31), i.e. chance. (These subsets are selected on the outcome's own timing, so read
  them as diagnostics, not as clean tests.)
- Not assessable (no fade_days): Quebec 4,237 of 22,026 (19.2%): 4,172 have no NDVI <= 0.4 look before day
  300 (1,688 silage, 2,484 grain: late harvest, regrowth, weeds or cover), 51 too few looks after the peak,
  14 never NDVI >= 0.6. Maryland 2 (1 silage, 1 grain), both no bare look before day 300.

## 5. Verdict

The idea is agronomically sound as a tendency (a chopper removes a green crop in one pass; grain corn dies
back first), but as a stand-alone rule on Sentinel-2 NDVI it is far from "100% accurate". On 17,789 Quebec
field-years it scores balanced accuracy 0.611 (precision 0.506, false-positive rate 0.524) and on the 44
Maryland field-years 0.547 (6 of 12 silage found, 14 grain fields wrongly called silage). On the same rows,
the existing f1_xgb_mono model scores 0.790 in Quebec and 0.938 in Maryland. The rule also miscounts
silage by -29% to +56% from year to year, which would wreck state acreage. Tuning the 17-day threshold does
not help (best 0.645 on 2019-2024, falling to 0.574 on 2025-2026). The reasons are physical, not tuning:
NDVI cannot tell a brown standing grain crop from bare soil (both read <= 0.4), and frost or normal
maturity turns grain corn brown about as fast as a chopper clears silage; and with 5-day revisits and
clouds, half the measured "fades" are only the gap between two clear images. Fade speed is already one of
the six inputs of f0/f1 (`fade_days`), next to the drop size, greenness at the cut, canopy moisture and
the post-harvest residue index that separates bare soil from stover.
