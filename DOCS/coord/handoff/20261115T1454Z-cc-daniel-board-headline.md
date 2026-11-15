# Handoff: model board, headline models and missing catalog entries

- From: cc-daniel. To: cc-raz (owner of `board/`).
- State: `test_models/boardExport/out/` now holds board files (`board_backtest.csv`, `board_forecast.csv`,
  `board_models.json`, `board_field.csv`) for 29 Tier A/B models and 46 field-model results, written by
  `test_models/boardExport/export.py` from the folders' own outputs. Checked on a local run of the `board`
  branch: all 20 catalog models show "published" and their numbers match each folder's README.

## What is still wrong on the board (your files)

The team's panel (2026-11-15) picked the headline pair:

| Crop | Headline | 2026 US, 80% range | 2017-24 state / US | 2025 state / US |
|---|---|---|---|---|
| Grain | A-G9 (g9_national_reconciliation, Tier A) | 88.75M, 87.28-90.24M | 1.69% / 0.96% | 1.62% / -0.88% |
| Silage | B-S6 (SC_B: smoothed level + drought chopping, last year's grain acres; Tier B) | 6.26M, 6.10-6.66M | 12.81% / 3.36% | 13.14% / +2.06% |

A-S7 (SC_A, 6.43M) is shown as a drought scenario. NASS's 88.51M and the Tier C pair are comparisons only.

1. **KPI tiles show the wrong models.** `defaultModel()` in `board/map.js` takes the first catalog model with a
   forecast, so the tiles read A-G3 (88.69M) and A-S1 (6.33M).
2. **The Tier A / B tab misses nine published models**: A-G5, A-G9, A-S6, A-S7, B-G5, B-G6, B-G7, B-S5b,
   B-S6. They are already on the Leaderboard, Compare and 2026 forecast tabs.
3. The **Satellite** section stays empty on purpose: the satellite candidates cover 15 states, so their
   error is not comparable with 48-state models.

## Suggested fix

In `board/catalog.json`, add entries (same shape as the others) and mark the two headline models:

```json
{"id": "A-G9", "tier": "A", "crop": "grain", "headline": true, "name": "FSA ratio, national reconciliation",
 "how": "A-G3's state split scaled to one national FSA x NASS/FSA ratio total.",
 "features": ["FSA grain-intended acres", "3-year median ratio", "national FSA x ratio total"], "signals": ["FSA", "NASS history"]},
{"id": "A-S7", "tier": "A", "crop": "silage", "name": "Drought scenario (smoothed level + Drought Monitor chopping)",
 "how": "Smoothed state level plus gamma x max(0, D2+ share - 0.10) x last year's grain acres.",
 "features": ["smoothed state level", "Drought Monitor D2+ share", "last year's grain acres"], "signals": ["NASS history", "weather"]},
{"id": "B-S6", "tier": "B", "crop": "silage", "headline": true, "name": "Smoothed level + drought chopping",
 "how": "Smoothed state level plus chopping from NASS's in-season yield shortfall x last year's final grain acres. Never NASS's acreage forecast.",
 "features": ["smoothed state level", "NASS yield shortfall", "last year's grain acres"], "signals": ["NASS history", "NASS current year", "weather"]}
```

Plus A-G5, A-S6, B-G5, B-G6, B-G7, B-S5b if you want every published candidate in the tab (descriptions
are in `test_models/boardExport/out/board_models.json`).

In `board/map.js`, prefer the flag in `defaultModel(crop)`:

```js
const head = (CAT.models || []).find(c => c.crop == crop && c.headline);
const headM = head && Object.values(MODELS).find(m => m.model == head.id && m.target == crop && m.has_forecast);
if (headM) return headM.model_id;
```

## Resume

```bash
.venv/Scripts/python.exe test_models/boardExport/export.py   # rewrites test_models/boardExport/out/
```

Then redeploy the Space. Risk: B-S6 is not the name in its source folder (`SC_B` in
`test_models/variations/silage_combos`); the export maps it.
