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
