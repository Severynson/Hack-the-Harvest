# autoresearch: silage vs grain (BARC fields)

An LLM runs its own experiments on a fixed evaluation harness, keeps what helps, and throws away what doesn't.

## Task

For each labeled BARC corn field-year (Maryland, 2021-2023; 44 labels: 32 Grain, 12 Silage), predict whether it was **chopped for silage (1)** or **harvested for grain (0)**, using Sentinel-2 time series.

Research direction for the current run (`autoresearch/cc-severyn`): **the caveman model**, a few hand-made rules on season timing:
- green-up date (the steady NDVI rise after the spring low) stands in for planting,
- harvest date = when NDVI collapses after the peak,
- season length = harvest - green-up; silage is cut green, weeks before grain.
Explore the rules and their parameters through ablations: what to detect, how to detect it, how to set the cut. Other timing signals are fair game (NDTI/BSI after harvest, how sharp the drop is, comparison with the other fields that year), as long as the model stays a few readable rules rather than a black box.

## Setup

1. Branch: `autoresearch/<AGENT_ID>` (team protocol in the root `CLAUDE.md`).
2. Read `README.md`, `prepare.py` (fixed: data, cache, `evaluate`), and `train.py` (the file you edit).
3. Data: `~/.cache/autoresearch-silage/` must hold `s2_field_timeseries.parquet` and `labels.parquet`. If it doesn't, run `uv run prepare.py`.
4. `results.tsv` (untracked) and `ledger/<AGENT_ID>.tsv` (tracked) each start with the header row only.

## Rules

**You CAN:** edit `train.py`: features, smoothing, detection logic, rules, thresholds, how thresholds are fitted.

**You CANNOT:**
- Modify `prepare.py` or the evaluation. `autoresearch/prepare.sha256` freezes it.
- Add dependencies beyond `pyproject.toml`.
- Use the held-out year's labels. `evaluate` never hands them over; don't hard-code knowledge of them (for example, OBJECTIDs known to be silage).

**Metric:** `val_f1` = silage F1 pooled over leave-one-year-out predictions on all 44 field-years. **Higher is better.** Always predicting grain scores 0 (accuracy 0.727).

**Overfitting warning:** 12 positives. Each one flipped moves F1 by ~0.04–0.08, so treat gains under ~0.04 as noise unless the code also gets simpler. Prefer rules with a physical reason over tuned constants. Every constant you add costs complexity.

**Simplicity criterion:** all else equal, simpler wins. A rule that is equal or better with less code is kept.

## Output

```
---
val_f1:           0.700000
precision:        ...
recall:           ...
balanced_acc:     ...
accuracy:         ...
confusion:        tp=.. fp=.. fn=.. tn=..
per_year_f1:      2021=... 2022=... 2023=...
total_seconds:    3.2
```

`grep "^val_f1:" run.log`

## Logging

Tab-separated, 5 columns:

```
commit	val_f1	balanced_acc	status	description
```

status: `keep`, `discard` or `crash` (crash rows get 0.000000 / 0.0000). Append each row to `results.tsv` and to `ledger/<AGENT_ID>.tsv`; commit and push the ledger (team protocol).

## Loop

1. Edit `train.py` with one idea.
2. `git commit`
3. `uv run train.py > run.log 2>&1`
4. `grep "^val_f1:\|^balanced_acc:" run.log`; if empty, `tail -n 40 run.log`.
5. Improved → keep the commit. Equal or worse → `git reset --hard HEAD~1`.
6. Log the row (the commit hash is the experiment commit, even if discarded), then commit the ledger on its own and push the branch.

A run takes seconds. Don't stop to ask whether to continue; the human ends the run.
