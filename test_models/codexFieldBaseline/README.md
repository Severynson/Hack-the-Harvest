# Fixed field-model comparison

Run from the repository root:

```bash
uv pip install --python .venv/bin/python xgboost-cpu
PYTHONPATH=. .venv/bin/python test_models/codexFieldBaseline/baseline.py
```

Outputs `out/results.json`. Matching source hashes and library versions reuse the
cached result; `--force` repeats the same comparison. No search runs.

The script compares Kernel's existing balanced logistic model with one small,
fixed XGBoost classifier on the same six physical harvest-evidence features.
Both use the identical five spatial block folds in Quebec. All repeated years
of a parcel stay in the same block. Class weights come only from each fitting
partition. XGBoost uses 80 depth-two trees, regularization, a fixed seed and at
most four threads; there is no early-stopping selection on a scoring cohort.

Metrics include the confusion matrix, both classes' precision and recall,
silage F1, false positive rate, accuracy and Brier score. Classification metrics
retain all field-years; unassessable rows count as grain for scoring only.
Brier uses assessable rows, whose coverage is reported separately. Always grain
is included as a baseline. Neither model output is a calibrated probability.

Maryland is an external research-farm transfer check, **not a fresh untouched
test set**: the team already inspected this cohort. No Maryland or state-2025
outcome is used to fit, select features, tune hyperparameters or choose a
threshold in this experiment. Do not promote a candidate solely because it wins
on this repeatedly inspected farm.

With the currently available imagery, training covers 318 parcels from one
Quebec cell in one year. Spatial block separation reduces local leakage but
does not prove transfer to independent regions. Neural CNN and hybrid training
remain deferred until independent labeled regions and years support a credible
comparison. No national field accuracy or calibrated acreage claim follows
from this experiment.

## Current fixed comparison

Read from `out/results.json`, using the local 318-parcel training series:

| Cohort | Model | Accuracy | Silage F1 | Brier (assessable) |
| --- | --- | ---: | ---: | ---: |
| Quebec spatial OOF | Logistic | 0.704 | 0.6736 | 0.2020 |
| Quebec spatial OOF | XGBoost | 0.717 | 0.6715 | 0.1893 |
| Maryland reused external cohort | Logistic | 0.841 | 0.7407 | 0.0981 |
| Maryland reused external cohort | XGBoost | 0.818 | 0.7333 | 0.1640 |

XGBoost's Quebec accuracy gain does not improve F1, and its Maryland transfer
check is worse. This one comparison supplies no reason to replace the simpler
logistic model. It does not establish statistical significance in either
direction.
