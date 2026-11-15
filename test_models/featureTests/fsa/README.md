# FSA intended-use silage acres as a state silage signal (group `fsa`)

**Status: BLOCKED at the data step, so the FSA rows are UNCOMPUTED.** The FSA site did not answer three ordinary
requests, so no FSA workbook is in the repo. `run.py` is finished and tested. It runs the whole comparison as
soon as a person saves the 20 files listed below. Everything that needs no FSA file is computed and reported
here: the incumbent against persistence, the residual cap on its own, and the most any rule limited to the
high-coverage states could gain.

This is a **state-level** test, not a field feature. It writes no `out/meta.json`, so the field harness
(`test_models/featureTests/harness.py`) does not pick it up.

## What and why

FSA publishes corn planted acres by declared intended use (Grain, Silage; "Forage" before crop year 2019). The
research note `DOCS/research/gap_fsa_ratio_baseline_2026.md` found:

- An FSA ratio applied to every state is worse than "same as last year" in every year from 2017 to 2025 (section 3.1).
- FSA covers 47% of NASS silage acres nationally, and 12% or less in the Plains and Corn Belt (sections 0 and 2.3).
- Where coverage is 75% or more, the FSA ratio does better than persistence: 9.4% against 10.5% WAPE over 83
  state-years in 2019-2025, r = +0.49 (section 3.3).
- Its best public baseline is FSA pass-through in high-coverage states, capped by NASS's November residual:
  12.8% against 13.8% WAPE, leave-one-year-out, 2020-2025 (section 4.3).

So the question here is narrow. Does FSA pass-through in the high-coverage states improve on **the team's own
incumbent state model**, scored the same way the incumbent is scored? The research note only compared FSA with
persistence.

## The incumbent (identified from the repo)

| | Primary | Secondary |
| --- | --- | --- |
| Model | `kernelag.state_model`, selected silage set `reversion_only`: the root report model and the team answer (DOCS/DECISIONS.md, 02:40Z and 03:45Z) | `test_models/danielModel` `nodrift_nass`, kept as the incumbent by `test_models/accuracy/state/README.md` |
| Backtest | Expanding window, each year fitted on earlier years only, 2017-2024 | Same rule; the overlap 2017-2024 is used here |
| States | 48 every year | 48 every year |
| Truth | NASS final silage acres harvested in `data/nass/corn_acres_state.csv`: the latest revised value, **not** the first January estimate the research note uses | The same values: persistence errors are identical, and 0 state-years differ |
| Metric | State WAPE = 100 × Σ\|pred − actual\| / Σ actual for each year, averaged over years; US error = 100 × Σ(pred − actual) / Σ actual | Same |

`run.py` recomputes both incumbents' predictions for each state in memory and writes nothing outside `out/`. The
yearly errors match `data/models/state_model_backtest.csv` exactly, and `nodrift_nass` matches
`test_models/danielModel/out/backtest_by_year.csv`.

## Method (pre-registered; written before any FSA number could be scored)

For state *s* and year *t*:

    pred = S(t-1) × clip(F_nov(t) / F_final(t-1), 0.5, 2.0)     only in gated states
    pred = min(pred, R(t))   where R(t) = NASS planted minus harvested-for-grain, as public by mid-November, > 0
    every other state keeps the base prediction

- **S**: NASS silage acres as the incumbent uses them (`last` in the incumbent's backtest).
- **F**: FSA corn planted acres with intended use Silage (Forage before 2019), sheet `county_data`, summed by
  state. `F_nov(t)` comes from the in-season file published by mid-November of year *t*. `F_final(t-1)` comes from
  the January file after crop year *t-1*. If `F_final(t-1)` is under 500 acres, the ratio is 1.
- **R**: `planted_asof − grain_asof` from the incumbent's own panel. It exists for 39-41 states. Vermont has none,
  so Vermont is never capped.
- **Gates**:
  - (ii) `realtime`, the **primary** gate: prior-year coverage `F_final(t-1) / S(t-1) ≥ 0.75`. It uses nothing from
    year *t* or later.
  - (i) `fixed_list`: NY, ID, CA, AZ, NM, VT, MT, the list in section 0 of the research note. It was chosen on
    2019-2025 coverage, so it carries a mild look-ahead. Section 2.3 of the same note also puts Washington (85%)
    in this class.
- **Bases**: `incumbent_reversion_only` (primary), persistence (variant B) and `incumbent_nodrift_nass`. Each
  candidate is compared with its own base.
- **Primary comparison**: `fsa_realtime_over_incumbent_reversion_only` minus `incumbent_reversion_only`.
- **Scoring**: years 2017-2024, all 48 states. Reported for each: mean yearly state WAPE, pooled WAPE, mean |US
  error|, and paired 90% bootstrap intervals on the change in WAPE. The bootstrap is run twice, once resampling
  years and once resampling states (10,000 draws, seed 20261114). The team's existing rule also applies: a gain
  counts only above two standard errors of the paired yearly differences.
- **Pre-registered sensitivity**: mean WAPE without 2019, the year FSA relabelled Forage as Silage.
- **Replication row**: `fsa_ratio_all_states`, the research note's plain per-state ratio with no gate and no cap.
  Its job is to show that the parser reproduces the research's headline finding (FSA ratio worse than persistence).
- **2025 and 2026 are information only.** 2025 uses the 1 Dec 2025 file, because no October or November 2025 file
  was released. It sits beside the frozen stored 2025 forecast. Nothing is fitted, tuned or selected anywhere.

## Results computed now (no FSA file needed)

From `out/results.json`, years 2017-2024, 48 states. A negative Δ means the first row is better.

| Predictor | Mean state WAPE | Pooled WAPE | Mean \|US error\| | WAPE without 2019 |
| --- | ---: | ---: | ---: | ---: |
| Persistence | 14.53% | 14.50% | 4.08% | 14.15% |
| Incumbent `reversion_only` | 13.12% | 13.10% | 3.90% | 12.88% |
| Incumbent `nodrift_nass` | 12.78% | 12.76% | 3.28% | 12.53% |

| Comparison | Δ mean WAPE (points) | 90% CI, years | 90% CI, states | Two-SE rule |
| --- | ---: | ---: | ---: | --- |
| `reversion_only` − persistence | −1.41 | −2.28 to −0.53 | −2.25 to −0.73 | passes (gain 1.41, SE 0.57) |
| `nodrift_nass` − persistence | −1.75 | −2.46 to −0.99 | −2.32 to −1.14 | passes (gain 1.75, SE 0.48) |
| `nodrift_nass` − `reversion_only` | −0.34 | −0.89 to +0.31 | −1.00 to +0.40 | fails (SE 0.39; matches DECISIONS.md) |
| Residual cap on the incumbent, fixed-list states only | −0.12 | −0.37 to +0.10 | −0.32 to +0.01 | fails |
| Residual cap on the incumbent, all states | +0.34 | −0.76 to +1.84 | −0.31 to +1.11 | fails |
| Residual cap on persistence, all states | −0.04 | −1.34 to +1.57 | −0.75 to +0.65 | fails |
| **Ceiling**: fixed-list states predicted exactly | −1.65 | −1.91 to −1.36 | −2.83 to −0.69 | (oracle) |
| **Ceiling, capped**: exact, then capped at R | −1.16 | −1.52 to −0.80 | −2.01 to −0.48 | (oracle) |

Context for the fixed-list states (NASS data only):

- They hold 20.2% of actual silage acres and 12.6% of the incumbent's absolute error.
- Pooled WAPE inside those 7 states, 2017-2024: persistence 9.19%, `reversion_only` 8.17%, `nodrift_nass` 7.56%,
  `reversion_only` capped at R 7.54%.
- In 18 of 56 fixed-list state-years, the final silage acres exceed the November residual. In those state-years
  the pre-registered cap would cut even a perfect forecast, so the capped ceiling (−1.16) is well below the exact
  one (−1.65).

## FSA rows

| Row | Value |
| --- | --- |
| `fsa_realtime_over_incumbent_reversion_only` (primary) | UNCOMPUTED: FSA workbooks missing for 2017-2024 (site timed out) |
| `fsa_fixed_list_over_*`, `fsa_realtime_over_persistence` and `fsa_realtime_over_incumbent_nodrift_nass` | UNCOMPUTED, same reason |
| `fsa_ratio_all_states` (replication) | UNCOMPUTED, same reason |
| 2025 and 2026 information rows | UNCOMPUTED, same reason |

### What the research note itself computed (from DOCS/research/gap_fsa_ratio_baseline_2026.md, not recomputed)

These figures use NASS's first January estimate as truth, a different year range and a coverage class defined
for each state-year. They cannot be set beside the tables above as like-for-like numbers.

| Research figure | Value |
| --- | --- |
| FSA ratio, every state, Nov file, 2019-2025 pooled WAPE | 17.6% (persistence 14.2%) |
| Class with coverage ≥ 75%, 2019-2025, 83 state-years | FSA ratio 9.4%, additive 9.3%, persistence 10.5% |
| Best public baseline: additive pass-through with fitted slope, coverage ≥ 50%, residual cap on all states, leave-one-year-out 2020-2025 | 12.8% (persistence 13.8%; residual cap alone 13.1%) |
| Residual cap on persistence, 2019-2025 | 13.7% (persistence 14.2%) |
| 2024 / 2025 rows: same as last year; FSA ratio; best public; oracle residual | 11.8 / 15.1; 14.4 / 15.4; 11.6 / 15.3; 5.3 / 6.6 |
| 2026 file (data as of 5 Nov 2026) | 2,885,863 silage-intended acres, −1.1% against the 2025 final file |

## Verdict

- **The FSA rows are UNCOMPUTED, and nothing is promoted.** The incumbent stays `reversion_only`, with
  `nodrift_nass` kept as a visible alternative, as before.
- **Inference, not a measurement: expect a small effect at best.**
  - Any rule limited to the 7 fixed-list states can gain at most 1.65 points of mean state WAPE over
    `reversion_only`. That figure assumes it predicts those states exactly. With the pre-registered cap the most
    it can gain is 1.16 points.
  - Inside those states the incumbent is already at 8.2% WAPE. The research's FSA ratio scored 9.4% in its 75%+
    class against persistence's 10.5%. Truth, years and class definitions differ, so this is suggestive only.
  - If FSA cut the incumbent's error in those states by the same ~10% relative margin it showed over persistence,
    the gain would be about 0.1 × 1.65 ≈ 0.17 points. That is smaller than the two-SE bar these 8 years can
    resolve: the paired SE between the two incumbents is 0.39 points.
- **The cap needs a second look when the data arrive.** On its own it barely moves the incumbent in the fixed-list
  states (−0.12, CI crosses 0). Across all states it makes the incumbent worse (+0.34), which matches the team's
  earlier decision to keep the cap out (DOCS/DECISIONS.md 03:09Z). In those states it also binds below the truth
  in 18 of 56 state-years. The capped variant stays the primary row as pre-registered, so its ceiling is −1.16.

## To unblock: download these files in a browser

Page: <https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/frequently-requested/crop-acreage-data>

Save each file into `data/fsa/` or `data/fsa/raw/`. Either keep the downloaded name or rename it to
`fsa_<crop year>_<vintage>.zip`. `run.py` matches the page's file names, the landing-page ids, and a " (1)" suffix
a browser adds to a repeat download. The entries marked "landing page" open a page first, and the file link sits
on that page.

| Crop year | Vintage | Link text on the page | Link |
| --- | --- | --- | --- |
| 2016 | final | 2016 acreage data as of January 1, 2017 | `/sites/default/files/documents/2016_fsa_acres_jan2017_edr32.zip` |
| 2017 | final | 2017 acreage data as of January 16, 2018 | `/sites/default/files/documents/2017_fsa_acres_jan2018.zip` |
| 2018 | final | 2018 acreage data as of January 28, 2019 | `/sites/default/files/documents/2018_fsa_acres_Jan-2019-kgcr.zip` |
| 2019 | final | 2019 acreage data as of January 1, 2020 | `/sites/default/files/documents/2019_fsa_acres_jan2020_stlno1.zip` |
| 2020 | final | 2020 acreage data as of January 5, 2021 | `/sites/default/files/documents/2020_fsa_acres_as_of_010521-BbO60I.zip` |
| 2021 | final | 2021 acreage data as of January 3, 2022 | `/sites/default/files/documents/2021_fsa_acres_web_as_of_010322.zip` |
| 2022 | final | 2022 acreage data as of January 3, 2023 | `/sites/default/files/documents/vc8Jn1nR42.zip` |
| 2023 | final | 2023 acreage data as of January 2, 2024 | `/sites/default/files/documents/3QPVeIgPizDl.zip` |
| 2024 | final | 2024 acreage data as of January 2, 2025 | landing page `/documents/FnNg0ix5oKdi` (research file `/sites/default/files/2025-01/FnNg0ix5oKdi.zip`) |
| 2025 | final | 2025 acreage data as of January 12, 2026 (data as of 5 Jan 2026) | landing page `/documents/doisjehvqfz9zip` (research file `/sites/default/files/2026-01/DoISjehvQfz9.ZIP`) |
| 2017 | nov | 2017 acreage data as of November 1, 2017 | `/sites/default/files/documents/2017_fsa_acres_nov2017gru14.zip` |
| 2018 | nov | 2018 acreage data as of November 1, 2018 | `/sites/default/files/documents/2018_fsa_acres_Nov_2018_grufs%21.zip` |
| 2019 | nov | 2019 acreage data as of November 1, 2019 | `/sites/default/files/documents/2019_fsa_acres_nov_2019_ohnot.ZIP` |
| 2020 | nov | 2020 acreage data as of November 10, 2020 | `/sites/default/files/documents/2020_FSA_Acres_web_as_of_110220-vkfNG6.zip` |
| 2021 | nov | 2021 acreage data as of November 9, 2021 | `/sites/default/files/documents/2021_fsa_acres_web_as_of_110921.zip` |
| 2022 | nov | 2022 acreage data as of November 1, 2022 | `/sites/default/files/documents/NEBP1OybFfUr83utFEB2.zip` |
| 2023 | nov | 2023 acreage data as of November 1, 2023 | `/sites/default/files/documents/XoNdctf9jmvWFGY.zip` |
| 2024 | nov | 2024 acreage data as of November 1, 2024 | landing page `/documents/kmwmjuc631qpebuukewh` |
| 2025 | dec | 2025 acreage data as of December 9, 2025 (data as of 1 Dec 2025) | landing page `/documents/uhya3k5akxvm` (research file `/sites/default/files/2025-12/UhYA3k5AKxVM.zip`) |
| 2026 | nov | 2026 acreage data as of November 10, 2026 (data as of 5 Nov 2026) | landing page `/documents/wrcdk92kc1587mahom35213` (research file `/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip`) |

All links are relative to `https://www.fsa.usda.gov`. The list was read from a saved copy of the page,
`data/fsa/index.html`. `out/results.json` (`data_step.files_missing`) holds the same list with full URLs.

**Probe record (2026-11-14):** three GETs with the default `requests` client and no custom headers: the page, the
2016 final zip and the 2026 November zip. Each ended in a read timeout after 40 s. Nothing else was tried, and no
browser user agent was used.

## How to run

```sh
.venv/Scripts/python.exe test_models/featureTests/fsa/run.py            # about 20 s; --boot N changes the draws
.venv/Scripts/python.exe -m pytest -q test_models/featureTests/fsa/test_run.py
```

Outputs in `out/`:

- `results.json`: status, data step, incumbent identification, method, summaries, comparisons with intervals,
  research numbers.
- `predictions.csv`: every state-year prediction that was scored.
- `fsa_state_silage.csv`: FSA acres by state, crop year and vintage. Written only once files are present.

Once the files are present, check `data_step.parse_summaries` first. Each file's national total is compared with
table 2.1 of the research note (`matches_research_within_0_1pct`). The intended-use labels found in each file are
listed there too.

## Limitations

- **Truth vintage.** Both incumbents score against revised NASS finals. The research note scores against the
  first January estimate, so its numbers are not like-for-like with these.
- **Revised history.** The incumbent's own history is revised data, not archived snapshots, as its README says.
  FSA vintages (November over the prior final) are real-time. S(t-1) is the revised value.
- **The residual R.** R uses the incumbent's as-of rule. Before 2018 the planted figure falls back to June or March
  reports. R is a November forecast, not a bound (18 of 56 fixed-list state-years exceed it).
- **Few years.** Eight years make the year bootstrap coarse. The state bootstrap holds years fixed.
- **Real files untested.** The standard-library xlsx reader (no openpyxl in the venv) is tested only on synthetic
  workbooks. The done branch of `run.py` was run end to end on synthetic files in a scratch folder: a plumbing
  check whose numbers mean nothing, because synthetic F was built from the truth. The first real run must pass the
  table 2.1 total check.
- **Late reclassification.** FSA reclassifies records late. For example, Kansas went from 13,249 to 294 acres
  between the September and December 2025 files (research note, section 2.2). There is no November 2025 file.
  The 2020 "November 10" file's name says 110220.
- **Fixed list.** The fixed list carries a mild look-ahead, and the research note's own high-coverage list
  differs between section 0 (7 states) and section 2.3 (adds Washington).
