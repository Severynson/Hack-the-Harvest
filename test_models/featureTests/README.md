# Field-feature tests: one harness, one decision rule

Do new feature groups, Landsat looks or Sentinel-1 radar make the field model's silage-or-grain calls
better? `harness.py` scores every candidate ("arm") against the field model as it stands
(`kernelag.field_model`: six harvest-evidence features, balanced logistic, threshold 0.5) on the same
rows with the same folds. Every difference is paired. The rule that decides was fixed before any
group was scored (below).

This is exploration code under `test_models/`. Nothing here changes `kernelag/field_model.py` or the
published metrics. `qc_regions_2023` is deliberately not matched by field_model's `TRAIN_PATTERN`.

## Why it is built this way

- **Regional transfer is the main test.** The USDA reps value a signal that "generalizes to other years
  and regions", and they warned against "over-calibrating to one place" (`DOCS/research/usda_reps_qa.md`,
  CLAUDE.md "USDA requirements v1"). So the evaluation that decides (E2) holds out a whole 10 km Quebec cell
  at a time. The single-cell block check (E1) is not enough on its own.
- **Maryland is a locked test set.** A loop that tries many ideas will overfit a small evaluation set.
  Lock a final test split that the loop never sees (`DOCS/research/statistics.md`, bottom line 10).
  The 44 Maryland field-years come from one farm. They are scored (E3) but never used to choose anything.
- **Radar is checked against optical timing, not on its own.** Sentinel-1 VH drops at the physical cut.
  Optical NDVI falls at browning. For EU grain maize, radar's end of season came 18.6 days after NDVI's
  (`DOCS/research/sar_harvest.md`, [Me21]). Silage is cut green, so for silage the two should coincide.
  That is what `radar_lag_days` measures. The radar features come from `kernelag/multisensor.py`.

## Inputs (join key: `field_id` as text, `year` as int)

| Input | Path | Notes |
|---|---|---|
| Labels | `data/labels/{quebec_maize_2023,qc_regions_2023,barc_2021_2023}.parquet` | `label` in {grain, silage}; `qc_regions_2023` has `cell` |
| Sentinel-2 series | `data/s2_series/<dataset>/<cell>_<year>.csv` | read with `kernelag.field_model.load_series` |
| Feature groups | `test_models/featureTests/<group>/out/{features.csv,meta.json}` | contract below |
| Landsat | `data/landsat_series/<dataset>/` + `data/models/landsat_s2_calibration.json` | via `kernelag.multisensor`; the calibration must not list Maryland in `fitted_on` |
| Sentinel-1 | `data/s1_series/<dataset>/` | via `kernelag.multisensor` |

`kernelag.multisensor` is imported lazily. If an input is missing, or the module fails, the arm is
reported **UNCOMPUTED** with the reason. Nothing is guessed.

### Field-feature contract (what a group must write)

- `out/features.csv`: columns `dataset, field_id, year`, then the group's columns, prefixed with the group key.
  One row per field-year that has evidence. Missing values stay NaN.
- `out/meta.json`: `{"group", "features" (at most 3, pre-registered), "rule_column" (0/1 or null),
  "description", "datasets_built", "uncomputed": {dataset: reason}}`.
- The harness checks this contract and does not repair a broken file. Any of these problems makes the
  group's arms UNCOMPUTED, with the problem as the reason: more than 3 features, missing columns,
  duplicate `(dataset, field_id, year)` rows, or a rule column with values other than 0/1. A dataset
  missing from `datasets_built` is UNCOMPUTED with the group's own `uncomputed` reason.
- Group columns are namespaced inside the harness as `g:<group>:<column>`, so a group can never
  overwrite a base column.

## Arms

| Arm | Features | Not assessable |
|---|---|---|
| `base` | `MODEL_FEATURES` on Sentinel-2 (exactly field_model's path) | `max_drop` missing, scored grain |
| `base+<group>` | `MODEL_FEATURES` + the group's pre-registered features; gaps go to the model's median imputer | as base |
| `rule:<group>` | the group's 0/1 call, scored directly; no evidence counts as grain (coverage reported) | n/a |
| `optical:s2+landsat` | `MODEL_FEATURES` on `multisensor.optical_series(S2, calibrated Landsat)` (`o:` columns) | `o:max_drop` missing |
| `base+radar` | `MODEL_FEATURES` + `multisensor.RADAR_FEATURES` (`r:` columns, radar lag against the S2 decline) | as base |
| `all` | every extra source ready for all of the evaluation's datasets: Landsat optical if present (then the radar lag is measured against that decline, `or:` columns), every group, and radar | as its optical path |

The model is always `field_model.make_model()` with `DECISION_THRESHOLD`. Training uses assessable rows
only. A row that is not assessable is scored as grain (`field_model.predict_silage` semantics).

## Evaluations

| Key | Label | Fit | Score | Folds | Bootstrap unit |
|---|---|---|---|---|---|
| `qc_cell_blocks` | E1 | quebec_maize_2023 (cell 79_515, 318 field-years) | same | 5-fold GroupKFold over 2 km blocks (`field_model.spatial_blocks`) | 2 km block |
| `qc_regions_loco` | E2 | 79_515 + 16 regional cells (3,128 field-years) | same | leave one cell out (17 folds) | cell |
| `maryland_transfer` | E3 | quebec_maize_2023 | all 44 Maryland field-years | none | field |
| `maryland_transfer_allqc` | E3b | all 17 Quebec cells | all 44 Maryland field-years | none | field |

- **Rosters.** The Quebec rosters keep the labeled field-years that have a Sentinel-2 series (the inner
  join in `evidence_table`). The Maryland roster keeps all 44 labeled field-years (`evaluate.evaluation_table`).
  The roster is the same for every arm, so a field that has only Landsat or only radar looks is not added.
- **Reproduction gate.** The base arm must give E1 TP 97 / FP 53 / FN 41 / TN 127 and E3 TP 10 / FP 5 /
  FN 2 / TN 27 (`data/models/field_model_report.csv`). The run prints `REPRODUCED yes/no`.
- **Metrics.** For every arm and evaluation: `kernelag.evaluate.extended_scores`, which gives TP, FP, FN,
  TN, silage precision and recall, false positive rate, accuracy, balanced accuracy and silage F1.
- **Comparison with base.** A paired cluster bootstrap gives the change in balanced accuracy and in
  silage F1, with 90% percentile intervals (2,000 draws, seed 0). Each draw resamples whole units and
  scores both arms on the same rows. The draws are identical for every arm of an evaluation. An exact
  McNemar test (`scipy.stats.binomtest` on the field-years only one of the two arms gets right) is
  reported alongside.

## Pre-registered decision rule

> A feature group **IMPROVES** the field model only if, on **E2 `qc_regions_loco`**, its change in
> balanced accuracy versus base is **> 0** and the **90% paired cluster-bootstrap interval (resampling
> cells) excludes 0**. E1 and E3 are supporting evidence only. Maryland (n = 44, one farm) is
> underpowered and is never used for selection.

The harness prints one decision per arm:

- `IMPROVES`
- `NO IMPROVEMENT SHOWN`
- `WORSE (E2 interval below 0)`
- `UNDECIDED (E2 UNCOMPUTED)`

## How to run

From the repository root (no `PYTHONPATH` needed; the script adds the repo root itself):

```bash
.venv/Scripts/python.exe test_models/featureTests/harness.py                       # all evaluations
.venv/Scripts/python.exe test_models/featureTests/harness.py --evaluations qc_regions_loco
.venv/Scripts/python.exe test_models/featureTests/harness.py --groups-dir <dir> --out-dir <dir>   # try a scratch group
```

A full run takes about 30 seconds. The run is idempotent: it reads the current group folders and
multisensor inputs and overwrites `results/`.

Outputs in `results/`:

- `field_results.json`: settings, dataset sizes, per-source availability (with UNCOMPUTED reasons), the
  group contract check and input digests, every arm × evaluation (metrics, coverage, comparison with
  base), and the decisions.
- `field_summary.csv`: one row per evaluation × arm. `extra_coverage_min` is the evidence share of the
  thinnest extra column on the scored rows.
- `field_predictions.csv`: per-row P(silage) and the call, for the Quebec evaluations (E1 and E2) only.
  Maryland per-field calls are not written here.

## Results

Snapshot from the run at 2026-11-15T05:48Z (machine UTC). The feature groups were still being built in
parallel. Re-run the harness for current numbers; `results/` always holds the latest run.

| Evaluation | base TP/FP/FN/TN | balanced accuracy | silage F1 | Reproduced |
|---|---|---|---|---|
| E1 qc_cell_blocks | 97/53/41/127 | 0.704 | 0.674 | yes |
| E2 qc_regions_loco | 877/345/390/1516 | 0.753 | 0.705 | (new evaluation) |
| E3 maryland_transfer | 10/5/2/27 | 0.839 | 0.741 | yes |
| E3b maryland_transfer_allqc | 10/4/2/28 | 0.854 | 0.769 | (new evaluation) |

Arms in that snapshot. Columns are E2 Δ balanced accuracy [90% CI] and the decision:

- `base+lswi`: +0.006 [0.002, 0.010]. **IMPROVES** under the rule. The effect is small (McNemar p = 0.013).
  It is not confirmed on E1 (−0.001 [−0.015, 0.016]) or E3b (−0.016 [−0.047, 0.000]).
- `base+gdd`: +0.001 [−0.004, 0.005]. NO IMPROVEMENT SHOWN. It is better on E1 (+0.021 [0.003, 0.044]),
  which is not the deciding evaluation.
- `rule:lswi`: −0.240 [−0.276, −0.201]. WORSE as a stand-alone call.
- `all` (gdd + lswi): +0.002 [−0.003, 0.007]. NO IMPROVEMENT SHOWN.
- `optical:s2+landsat`: UNCOMPUTED. There was no `data/landsat_series/` and no
  `data/models/landsat_s2_calibration.json` yet.
- `base+radar`: UNCOMPUTED. There was no `data/s1_series/` yet.

## Limitations

- **One year, one province for E2.** All 17 cells are Quebec 2023. A pass on E2 shows transfer across
  Quebec regions, not across years, and not to the US Corn Belt.
- **Few bootstrap units.** E2 resamples only 17 cells, and E1 roughly two dozen 2 km blocks. Percentile
  intervals from so few clusters can under-cover, so treat a lower bound just above 0 as weak evidence.
- **Multiplicity.** Each arm is tested on its own at a one-sided level of about 5% (a 90% two-sided
  interval). With k groups, the chance that at least one passes by luck grows roughly as k × 5%. There is
  no correction; read a single marginal pass in that light.
- **Neighbouring cells.** Cells are arbitrary 10 km squares. Cells 78_515 and 80_516 border 79_515, so
  fields near a shared edge can leak local conditions across folds.
- **Imputation.** Gaps in a group's features go to the median imputer that was fitted on the training
  folds. A group with low coverage is mostly imputed, so check `extra_coverage_min`. Rows that are not
  assessable are scored as grain for this benchmark only; no harvest is implied.
- **Maryland.** E3 and E3b are 44 field-years from one research farm that the team has already inspected
  (see `test_models/codexFieldBaseline/README.md`). The harness never reports Maryland feature
  distributions by label.
- **Tests.** The unit tests for this harness live outside the repo because this agent owned no
  `tests/` path. They check the fast bootstrap against a slow row-resampling reference, McNemar, the
  decision rule, the contract checks, the not-assessable-as-grain path and the two reproductions.
