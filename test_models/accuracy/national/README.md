# National silage acreage: bounded temporal comparison

Run from repository root:

```bash
.venv/bin/python test_models/accuracy/national.py
```

Matching source/input hashes reuse the result; `--force` repeats the same fixed
slate. Outputs are `results.json`, `predictions.csv`, `features.csv`, and
`weights.csv`. No model is promoted by this experiment.

## Design

Twelve fixed candidates test persistence, a three-year mean, dairy demand divided
by a grain-yield proxy, two non-grain residual corrections, three national ridge
regressions, sign-constrained weather regression and two fixed equal-weight
ensembles. There is no hyperparameter or threshold search. The weather and yield
features are weighted by prior silage acres over states with available inputs;
coverage is in `features.csv`. Missing values are imputed from the fitting years
only. Ridge strength is fixed; sign constraints encode the stated physical
expectations before fitting.

Each 2012–2024 prediction uses at least eight earlier national outcomes. Model
selection uses 2012–2020 mean absolute national error only. The later 2021–2024
partition is reported separately; its outcomes do not select the candidate.
All candidates retain the same 48-state silage truth. The residual strategy uses
published grain states and carries other states' silage forward, so missing grain
does not silently shrink the national denominator.

The 2025 and later outcomes are excluded before feature computation. The team
previously inspected outcomes through 2024: these are retrospective temporal
checks, not a new untouched holdout. Historical in-season inputs may also contain
later revisions and final planted-acre stand-ins before 2018. Grain yield is
only a proxy for silage biomass yield, and milk cows omit beef feed demand and
feed substitution. The source panel cannot support a perfect historical-vintage
claim.

## Results

The development-selected candidate is **ridge_weather**. Development mean absolute
national error is **4.675%**, versus **6.352%** for persistence. Later validation
mean error is **4.347%**, versus **4.414%** for persistence. The selected model
has **0 of 4** later years within 2%; its largest later error is **5.365%**.
This does not meet a defensible 2% goal and gives no meaningful later-validation
improvement over persistence.

| Year | Development-selected model | Persistence |
| --- | ---: | ---: |
| 2012 | 13.361% | 20.003% |
| 2013 | 1.109% | 18.306% |
| 2014 | 5.763% | 1.415% |
| 2015 | 1.152% | 1.988% |
| 2016 | 1.104% | 0.500% |
| 2017 | 0.730% | 2.803% |
| 2018 | 5.099% | 4.844% |
| 2019 | 9.136% | 7.235% |
| 2020 | 4.622% | 0.076% |
| 2021 | 3.857% | 1.690% |
| 2022 | 4.341% | 5.839% |
| 2023 | 5.365% | 6.036% |
| 2024 | 3.825% | 4.092% |

For diagnosis only, the physical ensemble has the smallest later mean among this
slate (**2.479%**), with 3 of 4 years within 2% and a **7.327%** maximum error.
It did not win the development selection and must not be promoted because of
that post-hoc later comparison. A mean below 2% would not establish that every
year or every state is within 2% anyway.

## Verification

- Ruff passes for `national.py`.
- Full outcome scope is 48 states in all 13 test years; each fit has at least
  eight earlier national outcomes.
- Replacing silage outcomes from 2018 onward and adding absurd grain forecasts
  from 2025 onward leaves every prediction through 2018 unchanged. This checks
  that a forecast does not use its own or later outcome as a predictor.
- This script adds no dependencies and does not read or rewrite held-out score
  artifacts.
