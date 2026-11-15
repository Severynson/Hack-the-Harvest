# Kernel: five-minute presentation

Generated from `data/models/metrics.json` at 2026-11-15T07:50Z. Open `report/index.html` offline.
The talk follows the seven sections from top to bottom. Acreage error is WAPE unless stated otherwise.

## 0:00–0:40 — The answer (mission)

USDA needs corn acreage by harvest use before January. Silage is cut green and wet; grain usually dries first.
Kernel combines a state acreage forecast with a separate satellite test of that physical signal.
Our November forecast is 6.26 million silage acres, with an 80% interval of
5.95 to 6.59 million.
Grain is 88.51 million acres, primarily NASS's own in-season figures.
These totals sum the states shown; missing grain states are excluded.

## 0:40–1:05 — States (usefulness)

Scroll the state table. Each silage forecast has an interval and change from last year.
The state model uses public acreage history and tests additional season context against persistence.
The selected model is `smoothed_chopping`: a smoothed state level (most yearly swings reverse the next year)
plus drought chopping, i.e. grain corn cut for silage when NASS's November yield forecast falls over 10% below trend.
Do not present the satellite classifier as the source of these acreage totals.

## 1:05–2:00 — Can you trust it (technical quality)

We predict each historical year using earlier outcomes, then select the feature set on the historical validation years.
Mean silage state error is 12.80%, versus
14.53% when copying last year.
The separate 2025 score is 13.12%, versus
13.96% for persistence.
For the 2025 national total, signed error is 2.19%, versus
0.32%.
That is a modest validation gain and no held-out silage win. We do not claim otherwise.
The grain advantage comes largely from NASS inputs, not a new satellite discovery.

## 2:00–2:30 — Bias (technical maturity)

Show the signed regional errors: positive means too many predicted acres, negative too few.
State WAPE sums absolute state acreage errors and divides by actual acres; it does not locate individual errors.
Intervals use historical residuals. Historical coverage uses leave-one-year-out calibration,
including later years, so it is a retrospective check rather than operational historical coverage.

## 2:30–3:05 — How early (innovation)

Show the September state comparison and the field earliness curve.
The imagery is truncated before recomputing features; no later scene enters an early call.
Coverage means features can be computed, not confirmed harvest. Unassessable fields count as grain
for scoring only, and provisional calls can change as more imagery arrives.
An early state replay requires its own dated satellite aggregate; it cannot reuse the November file.

## 3:05–4:10 — The field signal (innovation and evidence)

Open `report/fields.html`, choose one real field, and show its NDVI/NDMI curves and provisional cut bracket.
Explain that these satellite features feed the field classifier. Without the state sample aggregate,
they do not yet drive the headline acreage forecast. Return to the acreage report.

The six features describe drop size, speed, fade time, greenness and moisture before the cut, and residue after it.
We fit on 318 Quebec parcels and test on
44 Maryland research-farm field-years from
34 distinct fields. These are proxy labels, not nationwide validation.
Silage precision is 0.667, recall
0.833, false positive rate
0.156. The confusion matrix is
TP=10, FP=5, FN=2, TN=27.
Balanced accuracy is 0.839; silage F1 is
0.741. Operational calls can abstain; scores are not calibrated probabilities.
Confidence intervals resample whole fields, keeping their repeated years together.
Feature extraction plus prediction takes 0.0145 seconds per field
on this machine; imagery downloading is excluded.

## 4:10–5:00 — Limits and next steps (feasibility)

One farm and one Quebec training year cannot establish national performance. Weather, cloud cover,
soil and harvest systems vary. A false positive rate that looks small can overwhelm a rare silage class,
so we do not sum field calls into acres.
The next test is whether paired satellite share changes on the same sampled areas improve state forecasts,
under the existing selection rule and with sampled-state results shown separately.
If the data are missing or the test loses, keep the historical forecast and report that result.
The contribution is a reproducible harvest-evidence test, a usable acreage report, and explicit uncertainty.

## Likely USDA questions

- **Does this beat last year?** Slightly on historical silage validation; not on the separate 2025 score.
- **Is grain independent of NASS?** No. NASS's in-season forecast is the principal grain input.
- **Are these national field accuracy numbers?** No. They are a transfer test on one Maryland research farm.
- **Can I add field probabilities to get acres?** No. Sampling, class prevalence and classifier error require correction.
- **Was 2025 used to tune the model?** The stored 2025 score was generated separately; do not tune on it or overwrite it.
- **Are early results guaranteed to hold?** No. The cutoff is enforced, but noisy partial-season evidence can change.
- **What is still unproven?** Satellite-driven improvement in state acreage error and transfer to other US regions.
