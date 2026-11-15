# autoresearch: silage vs grain

Adapted from Karpathy's autoresearch (LLM pretraining). Same loop, new problem: an agent edits `train.py`, runs it, keeps the change if the score improves and reverts it if not.

Here the problem is field-level silage vs grain on the organizer BARC labels (`jupyter/workspace/04_Evaluation/BARC_Corn.2021-2023.gpkg`).

| File | Role | Who edits |
|---|---|---|
| `prepare.py` | Downloads Sentinel-2 L2A from Planetary Computer, builds per-field cloud-masked time series, defines `evaluate` (leave-one-year-out silage F1) | frozen (`prepare.sha256`) |
| `train.py` | The model: features + rules + fitting | the agent |
| `program.md` | Instructions for the agent | human |
| `results.tsv` | Local experiment log (untracked) | agent |
| `ledger/<AGENT_ID>.tsv` | Same log, tracked and shared with other agents | agent |

```
cd autoresearch
uv sync
uv run prepare.py      # once, ~10-20 min, writes ~/.cache/autoresearch-silage/
uv run train.py        # one experiment, seconds
```

## Data built by prepare.py

- Scenes: Sentinel-2 L2A, tile 18SUJ, 1 Mar – 20 Dec of 2021, 2022 and 2023; scene cloud cover < 90%. Duplicate processing versions are removed (newest kept), and the +1000 reflectance offset of processing baseline 04.00+ is subtracted.
- Pixels: each field polygon is shrunk 10 m inward. Only pixels whose centre lies inside the shrunken polygon count, so edge pixels that mix in roads or neighbouring fields are dropped. Pixels with SCL class other than vegetation (4) or bare soil (5) are masked.
- Per field and scene: median NDVI (plus p25/p75), NDMI, NDTI, BSI and raw red/NIR/SWIR; share of clear pixels (`valid_frac`).
- All 83 fields are extracted, including unlabelled ones, so a rule may compare a field against its neighbours in the same year.

## Evaluation

Leave-one-year-out: train on two years, predict the third, then pool the 44 out-of-fold predictions. The headline number is silage F1; balanced accuracy is also reported. The baseline of always predicting grain scores F1 0 at 72.7% accuracy.

These are proxy labels from one research farm. Field-level scores here say nothing about state acreage error, the organizers' main measure (see the root `CLAUDE.md`, "USDA requirements v1").
