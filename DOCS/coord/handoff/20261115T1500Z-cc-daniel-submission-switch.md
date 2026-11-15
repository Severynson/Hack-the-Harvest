# Handoff: switch the Keeboh submission headline to Kernel's own models (A-G9 + B-S6)

- From: cc-daniel. To: whoever uploads to app.keeboh.com, the speaker, and cc-manraj (owner of `T-cc-manraj-submission`).
- Written: 2026-11-15T14:57Z.
- State: the talk is rewritten (`DOCS/presentation.md`, 295 s). The notebook, README and `data/kernel_own/` copies are being
  prepared in parallel; check that they exist before uploading (checklist step 1).
- Headline: grain A-G9 (`g9_national_reconciliation`, Tier A, no current-year NASS data) 88.75M, 80% range 87.28-90.24M;
  silage B-S6 (`SC_B`, Tier B, uses NASS's yield forecast, not its acreage forecast) 6.26M, 80% range 6.10-6.66M.
- Sources: `test_models/variations/grain_variants/out/forecast_2026.csv` (US row = sum of 41 states),
  `grain_variants/out/summary.csv`, `silage_combos/out/forecast_2026_us.csv`, `silage_combos/out/interval_coverage.csv`,
  `submission_preview/out/scorecard.csv`, `data/models/deliverable_2026.csv` (Tier C comparison).

## (a) Submission-page answer (paste into Keeboh)

Paste only after the notebook in Keeboh prints the same numbers (step 3 below). If it does not, use section (d).

> Kernel forecasts 2026 corn-for-grain and corn-for-silage acres for every state and the US as of 15 November, ahead of NASS's January report, using our own models: grain 88.75M acres (80% range 87.28–90.24M) and silage 6.26M acres (80% range 6.10–6.66M). Neither uses NASS's acreage forecast. The story is intent, then switch: farmers certify their intended use to FSA by mid-July, which drives grain; in a bad season growers chop grain corn for nearby dairies, which drives silage (dairy features themselves were tested and added nothing). Grain is public FSA certified grain acres times each state's three-year median NASS/FSA ratio, plus one national reconciliation factor; it uses no current-year NASS data. In a backtest that uses only data public at each date, it matches NASS's November state accuracy (1.69% vs 1.66% mean state error, 2017–2024), reaches 1.67% by 15 September, and on 2025, scored once, had 1.62% against NASS's 1.64%. NASS remains better on the US total (0.82% vs our 0.96%, 2017–2024) and over 2012–2024 (1.60% vs 1.88%). NASS's current-year inputs did not improve our grain model (best NASS-informed version 1.74% vs our 1.69%). Silage is each state's smoothed level plus extra chopping when NASS's in-season yield forecast falls short; it uses NASS's yield forecast, not its acreage forecast (12.8% state and 3.4% US error, 2017–2024; +2.1% US in 2025). An oracle test shows state error cannot fall much below 9.7%, because the published state series itself swings from year to year. In leave-one-year-out backtests, 79% of state results fell inside the 80% ranges, for grain and for silage. A Drought Monitor version (6.43M) is shown only as a scenario: that drought sits over largely irrigated Nebraska corn, where NASS's yield forecast shows no shortfall. We also tested satellite imagery the way it would run live (300 areas, 15 states, 2017–2024): it ranks states (Spearman 0.73–0.86) but misses year-to-year change and made every state silage model 1.6–2.5 points worse, so no forecast uses it. A Sentinel-2 field model scores 0.73 precision and 0.73 recall on 2,826 unseen Quebec 2025 fields against proxy labels; field results are never summed into acres. Every number traces to files in the workspace, and NASS's own November forecast (88.51M grain) is shown only as a benchmark.

## (b) Keeboh upload checklist (app.keeboh.com)

Keeboh keeps only the workspace, so local paths under `jupyter/workspace/` map one to one to Keeboh paths.

1. Locally, confirm the change set is complete before uploading anything (upload all of it or none of it):
   - `ls jupyter/workspace/Kernel_Submission/data/kernel_own/` lists 11 files, including grain_intervals.json.
   - `grep -c "88,749,849\|88.75" jupyter/workspace/Kernel_Submission/kernel_deliverable.ipynb` is not 0, and the
     notebook's first section is "Headline: Kernel's own 2026 forecast (as of 15 Nov)".
   - `head -6 jupyter/workspace/Kernel_Submission/README.md` names A-G9 + B-S6 as the deliverable.
2. Upload or replace in Keeboh, keeping the folder structure:
   - [ ] `Kernel_Submission/kernel_deliverable.ipynb` (replace)
   - [ ] `Kernel_Submission/README.md` (replace)
   - [ ] `Kernel_Submission/data/kernel_own/*` (new folder; all 11 files, including grain_intervals.json)
   - [ ] `Kernel_Submission/data/DATA_MANIFEST.tsv` (replace; it now lists the 11 `kernel_own` files)
   - [ ] `report/index.html`: only if the workspace has it. Checked 14:57Z: there is no `jupyter/workspace/report/`
         and no report under `Kernel_Submission/`, so skip unless someone adds one with the A-G9/B-S6 hero. The repo-root
         `report/index.html` now leads with A-G9 / B-S6 (switched 15:00Z), so it is safe to add if wanted.
   - [ ] `DOCS/presentation.md`: not a Keeboh file. Give it to the speaker (open on the presenting laptop or print it).
3. In Keeboh, open `Kernel_Submission/kernel_deliverable.ipynb` and check, without running the heavy cells:
   - [ ] the headline cell shows US grain **88.75M** (87.28–90.24M) and US silage **6.26M** (6.10–6.66M);
   - [ ] the backtest table shows A-G9 1.69% / 0.96% vs NASS November 1.66% / 0.82% (2017–2024);
   - [ ] the Tier C section is headed "## Comparison: Method" and "## 1. Comparison pair, 2026 (Tier C)" and still
         shows 88.51M grain and 6.26M silage (5.95–6.59M).
   - If the headline cell has no output, run only that cell (it reads the copied CSVs). Run All is also safe: the new cells stand alone.
   - If a path error appears, a `kernel_own` file is missing from the upload: fix it, then recheck.
4. Paste the answer from (a) into the submission page; every number must match what step 3 showed.
5. Append one line to your status ledger with who uploaded what and when (UTC from `bash scripts/sync.sh`).

## (c) Note to cc-manraj (owner of T-cc-manraj-submission)

- The submission headline is switching from the Tier C pair (NASS's November grain forecast passed through, 88.51M,
  + smoothed chopping SC, 6.26M, 5.95–6.59M) to Kernel's own models: A-G9 grain 88.75M and B-S6 silage 6.26M.
- Why: the judges' read was that handing NASS its own number scores close to zero on technical quality and innovation.
  A-G9 uses no current-year NASS data and ties NASS's November state accuracy (1.69% vs 1.66%, 2017–2024); on 2025,
  scored once, it is at 1.62% / −0.88% against NASS's 1.64% / −0.99%. B-S6 drops NASS's grain forecast at no cost
  (12.81% / 3.36% vs SC 12.80% / 3.34%).
- Your Tier C section is kept, not deleted: it is retitled ("## Comparison: Method", "## 1. Comparison pair, 2026 (Tier C)") and its outputs are left untouched. NASS November stays on stage only as the benchmark.
- Files inside your task's paths that change: `Kernel_Submission/kernel_deliverable.ipynb`, `Kernel_Submission/README.md`,
  new `Kernel_Submission/data/kernel_own/`, and `data/DATA_MANIFEST.tsv` (11 new rows).
- Risk for you: `scripts/build_submission.sh` runs `rm -rf "$OUT/data"` and `scripts/make_submission_notebook.py`
  rewrites the notebook. Re-running either would silently delete `data/kernel_own/` and the headline section. Please do
  not rebuild until the headline section and the `kernel_own` copy step are ported into those two scripts.

## (d) Fallback if the upload cannot be verified by 08:15

- Keep the old notebook in Keeboh as it is (Tier C outputs). Do not upload half the change set: the new notebook without
  its `kernel_own` CSVs breaks the headline cell.
- Talk (`DOCS/presentation.md`), beat "The answer" and the grain beat: relabel NASS November (88.51M, the number the old
  notebook prints) as the benchmark, and quote our grain as "our grain model A-G9 = 88.75M (87.28–90.24M), in
  `test_models/variations/grain_variants/out/forecast_2026.csv`, model `g9_national_reconciliation`, US row".
- Silage in the talk: keep 6.26M but with the range the old notebook prints, 5.95–6.59M, and describe it as the smoothed
  chopping model that uses NASS's grain-acre and yield forecasts (backtest 12.80% / 3.34%, 2025 US +2.19%). Drop the
  6.10–6.66M range and the "neither uses NASS's acreage forecast" line. Never show two ranges for the same number.
- Submission page: use (a) with the same three edits (silage range 5.95–6.59M and its method; delete "Neither uses
  NASS's acreage forecast"; change the last sentence to say A-G9 is in the repository file above, not in the workspace).

## Resume

- `bash scripts/sync.sh`, then step 1 of (b). If all three checks pass, do steps 2–5; if not by 08:15, do (d).
