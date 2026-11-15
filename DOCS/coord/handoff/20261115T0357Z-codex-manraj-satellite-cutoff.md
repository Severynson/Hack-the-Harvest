# To cc-varun: state satellite delivery and cutoff contract

Latest checked origin/main: `2a95dfc` (2026-11-15T03:57Z sync). Its new pull retry/progress logging is preserved. No `data/panel/state_satellite.csv`, state sample parquet, or state sample series exists in this checkout or the fetched main tree. No remote job handle is exposed here, so completion of the Keeboh pull cannot be verified from this session.

Please publish the aggregate plus coverage/provenance, or the sample parquet/summary and series needed to derive it. Needed: sampled state/area/year counts, duplicate checks, assessable-acre coverage, PPS sampling details, and observation dates. A partial pull must use the same complete areas across years; do not manufacture missing observations.

Important: `s2_series.SEASON` runs through November 30. An aggregate for a November 15 forecast must truncate those cached series before extracting features. The comparison branch now fixes this in `kernelag.state_signal`: `--asof nov` enforces November 15 and writes `state_satellite.csv`; `--asof sep` enforces September 15 and writes `state_satellite_asof_sep.csv`. Outputs include the cutoff and last observation dates. Missing samples produce an explicit UNCOMPUTED message and no invented aggregate. Do not use a previously generated full-November aggregate as a November-15 replay.

Commands after the files arrive:

```bash
.venv/bin/python -m kernelag.state_signal --workers 6 --asof nov
.venv/bin/python -m kernelag.state_panel
.venv/bin/python -m kernelag.state_model --forecast 2026
.venv/bin/python -m kernelag.report
```

Preserve the existing selection rule and stored 2025 score. Earlier satellite years use a fixed Quebec-trained classifier and retrospective crop masks, so any successful ablation remains retrospective rather than an archived-vintage operational forecast. The final report remains usable while this dependency is unavailable.
