# Finish-line priorities

Source: user goal attachment read 2026-11-15. Existing package has real polygons, Sentinel-2 pulls, six physical features, a Quebec logistic model, Maryland validation, public state context, and an offline acreage report. No existing frontend or API is present.

1. Verify the existing evaluation and report: consistent training, complete test roster, repeated-field uncertainty, dated satellite inputs, honest validation labels. Preserve the stored 2025 score.
2. Add an offline field explorer using the existing Python pipeline and real Maryland polygons. Select field-year, inspect raw satellite trajectories, features, observation quality, provisional harvest bracket and uncalibrated score. Show sample acreage tallies with scope and uncertainty; never imply nationwide coverage or calibrated probabilities.
3. Re-run the state satellite comparison when the actual state aggregate or sample series arrives. Keep selection fixed; no tuning on 2025.
4. Only after the core demo works: additional public field context, XGBoost and geographic/year-held-out experiments. Neural networks remain conditional on sufficient independent labels and compute; 318 local training parcels from one cell do not establish national adequacy.

Verification: pipeline tests, report regeneration, field-data schema and aggregation invariants, offline browser desktop/mobile interaction checks. Log unfinished data and research explicitly.
