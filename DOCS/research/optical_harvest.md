# Optical time series: detecting the harvest date and the shape of the decline (cliff versus fade)

Team Kernel, Hack the Harvest. Research note written Saturday 2026-11-14 by the `optical_harvest` research agent.
Scope: how to get a cut date and a "cliff versus fade" shape out of Sentinel-2 / HLS optical time series, what accuracy to expect, and what breaks.

## 0. How to read this note

- Evidence tags used throughout:
  - **[FULL]** full text opened and read (PDFs were read with a local text extractor).
  - **[ABS]** abstract or landing page opened and read.
  - **[NOT OPENED]** only a search-result snippet, a citation inside another paper, or my memory. Treat as low confidence.
- Anything prefixed **Inference:** is my own reasoning, not a statement from a source.
- Research process: 17 web searches with varied wording, about 45 page or PDF fetches. The shared web-search budget for this workflow run ran out at that point (2 further searches were refused), so a few sub-topics could not be chased to a primary source. They are listed in section 14 so nobody mistakes silence for a negative result.
- A few numbers lost their dash in PDF text extraction (for example "2-8 days" extracted as "28 days"). Where that happened it is flagged.

## 1. Bottom line

1. **Optical gives an interval, not a date.** Both USDA-ARS (Feng Gao's WIST algorithm) and the EU's Sen4CAP report a "cut while green" event as the pair of clear observations that bracket it: date = midpoint, uncertainty = half the gap. Copy that.
2. **The interval is days wide in California and weeks wide in the Upper Midwest.** NOAA climatology: 24-26 clear days per month in Fresno and Sacramento in Aug-Sep, against 8-12 in Wisconsin, Iowa and Minnesota in Sep-Oct and 5-7 in November. Radar has to carry the date in the Midwest; optical carries the "how green was it" evidence.
3. **Lead with a moisture index (NDMI = LSWI), not NDVI.** The only published silage-versus-grain optical classifier found (Lin et al. 2025) ranks LSWI above NDVI, red-edge NDVI and EVI, and its whole silage/grain split is one rule: September LSWI <= 0.15. It reached 93% overall accuracy, silage F1 0.93, and beat a random forest.
4. **Grain harvest is almost invisible to NDVI curve features.** By the time the combine arrives the canopy already reads like soil. Curve-fit end-of-season dates miss corn harvest by a year-dependent +3 to +16 days. A NIR/NDVI ratio (NHPI) recovers the grain harvest date to about 6 days MAE at MODIS scale.
5. **Skip BFAST, CCDC/COLD, LandTrendr and double-logistic EOS for dating.** They need years of history and model the annual harvest as normal seasonality. Use pairwise drops on raw clear observations.
6. **Compute drops on raw, strictly masked, field-interior observations and require persistence.** Standard cloud masks alone "significantly overestimate" cut events; smoothing and compositing erase the cliff.

## 2. What this means for Kernel

### 2.1 Changes to plan v2

| Plan v2 item | Verdict from the evidence | Change to make tonight |
|---|---|---|
| (1) Cut date from Sentinel-1 change point "confirmed by optical" | Keep, but optical confirmation is an interval `[t1, t2]`, often 1-3 weeks wide in the Midwest in fall. | Store `t1` (last standing clear look), `t2` (first removed clear look), midpoint, half-width. Intersect with the radar date. If radar falls outside `[t1, t2]`, flag the field. |
| (2) Green-at-cut = share of peak NDVI/NDMI at the last clear scene before the cut | Right idea, two problems: NDVI saturates and falls late; and the "last clear scene" can be stale, which biases green-at-cut high and creates false silage. | Make NDMI the primary index, NDVI secondary. Add `staleness = cut_date - t1` and discount green-at-cut by the pre-cut slope times staleness. Send stale fields (> 10-14 days) to the review band. |
| (3) Dry-down days = optical browning date to radar cut date | Supported. Liu and Diao define mid-senescence (MOS) as NDVI falling to 50% of the senescence amplitude and search for harvest in `[MOS, MOS + 2 months]`. | Define browning = MOS. `drydown_days = max(0, cut - MOS)`; equals 0 when the 50% crossing happens inside the cut interval (a cliff). |
| (4) Ground left (NDTI/STI) | Not researched here in depth. One naming trap found. | In `spyndex` / awesome-spectral-indices, `NDTI` is the *turbidity* index `(R-G)/(R+G)`. The tillage index `(SWIR1-SWIR2)/(SWIR1+SWIR2)` is listed there as `NBR2`. `STI = SWIR1/SWIR2` is listed correctly. |
| Depth-2 tree first | Supported by precedent: a 3-rule tree beat a random forest (OA 0.929 versus 0.904) on silage versus grain maize. | Keep. Report the published LSWI rule as a baseline row in the metrics table. |
| Timing in GDD and relative to county median | Strongly supported: the published calendar-month thresholds had to be re-tuned by hand each year and still dropped from 0.93 to 0.86-0.88. | Keep, and say so in the pitch as the fix for a known weakness of the prior art. |
| (new) Optical grain-harvest date | NHPI = normalized NIR/NDVI, first exceedance of 0.6 after MOS. | Add as a cheap feature and as the optical cross-check on the radar date for grain fields. |
| (new) "Removed earlier than the last three years" | NASA OPERA DIST-ALERT-HLS gives exactly this per 30 m pixel. | Optional feature if 2-4 hours are free. Biased against fields that are chopped every year. Never use it alone. |
| (new) Uncertainty model | NOAA clear-day climatology explains where optical works. | Put the cloud table on the "where it fails" slide; tier fields by interval width. |

### 2.2 Minimal optical feature set, in build order

1. Field-interior median time series of NDVI, NDMI, NIR, NBR2 from HLS (bands common to Landsat and Sentinel-2), raw clear observations only. About 2 hours.
2. Cut interval `[t1, t2]` by largest single-step drop after the summer peak, with a persistence check. About 1-2 hours.
3. `green_at_cut_NDMI`, `green_at_cut_NDVI`, `drop_frac`, `staleness`, `pre_slope`. About 1 hour.
4. `MOS`, `drydown_days`, NHPI harvest date. About 1-2 hours.
5. Window-state fallback: median NDMI in a county-relative window (the Lin et al. rule). About 1 hour. This needs no event detection at all and survives long gaps better than any date feature.
6. Optional: OPERA DIST-ALERT `VEG-ANOM-MAX` and `VEG-DIST-DATE`. 2-4 hours including Earthdata access.

### 2.3 Lines for USDA statisticians

- "We treat the satellite cut date as interval-censored: last look standing, first look removed. USDA-ARS's own WIST algorithm reports the midpoint and half the gap as the uncertainty; the EU CAP monitoring system reports the interval itself."
- "We do not claim day-level dates. With Sentinel-2 alone USDA-ARS measured a mean absolute difference of 4.0 days, RMSE 5.1 days, 6.9% missed and 10.3% false detections on 29 recorded events. With HLS on 28,190 Maryland fields, 94% of terminations were detected and 72% were within two weeks of the farmer-reported date."
- "Our uncertainty is regional by construction: Fresno has 24-26 clear days in August and September, Madison has 9, and 5 in November. In the Midwest radar dates the cut and optical tells us what state the crop was in."
- "Early is not silage. The discriminating quantity is the state of the canopy in the last clear look before removal, not the date."
- "There is a published transparent precedent: a three-rule tree on LSWI and NDVI reached 93% accuracy for silage versus grain maize, but its calendar thresholds needed hand re-tuning each year. We replace the calendar with growing-degree-days and county-relative timing."

## 3. Closest prior art: silage versus grain maize from optical data

| Study | Data and method | Result | Limits |
|---|---|---|---|
| Lin, Huang, Tan, Yang, Huang, Su, Hu (2025), *Agronomy* 15(6):1438, "TempDiff-SMID" **[FULL]** | Sentinel-2 on GEE, Hohhot (Inner Mongolia), 2023. NDVI and LSWI reconstructed at 15-day intervals with a Whittaker smoother (1 Apr-31 Oct). 100 silage, 131 grain, 150 non-maize sample points; 70/30 split for the RF comparison. Three-rule tree: (1) `NDVI_May <= 0.2` and `NDVI_July >= 0.2` and elevation < 1200 m; (2) `LSWI_July >= 0.16`; (3) `LSWI_Sept <= 0.15` means silage, otherwise grain. | 2023: OA 0.9291, kappa 0.8923. Silage UA 0.9216, PA 0.94, F1 0.9307. Grain UA 0.9219, PA 0.9008, F1 0.9112. Random forest on 65 features (13 bands x 5 monthly composites): OA 0.9043, kappa 0.8511, silage F1 0.8889. Gini importance: LSWI > NDVI > RENDVI > EVI. Transfer after "adaptively adjusting decision thresholds": OA 0.8621 (2022), 0.8816 (2021); silage F1 0.8163 and 0.8925. | Silage and grain harvest windows differ by only 5-15 days there (silage mid-Aug to early Sep, "fully harvested by 10 September 2023"; grain late Sep to early Oct). Authors: "current threshold optimization relies on empirical adjustments"; single region; single sensor; cloud and mixed pixels named as risks. Small point sample. |
| Salehi Shahrabi et al. (2020), *Int. J. Remote Sensing* 41(21):8406-8427 **[NOT OPENED: publisher 403, NASA mirror unreachable; described inside Lin et al. 2025, which was read]** | Sentinel-2 NDVI, Savitzky-Golay smoothing, phenological rules, no training data. Key parameter `SPGH/LOS` = slope from peak greenness to harvest divided by length of season. | As reported by Lin et al.: kappa 0.89 (Abyek), 0.80 (Marvdasht), 0.90 (Mashhad), 0.80 (**Tulare, California**), 2017; overall accuracy "consistently exceeding 0.90". | I could not read whether it separates silage from grain maize or silage maize from other crops. Thresholds unknown. Worth 10 minutes if someone has library access: it is a slope-to-harvest ("cliff") feature tested in the largest US dairy county. |

Why this matters: the mission-alignment judges will ask "has anyone done this". The honest answer is: once, in China, with a moisture index in a fixed calendar window, at 93% on a small sample, and it did not transfer across years without re-tuning.

## 4. Rule-based detectors: thresholds actually used in the literature

| Detector | Rule | Numbers | Source |
|---|---|---|---|
| Drop between consecutive clear observations | NDVI drop > 0.2 (i) between consecutive clear observations or (ii) between the current and the second-to-last clear observation; event assigned to the first observation after the event. | Bare ground NDVI <= 0.3, tall grass > 0.65; cut-but-not-removed grass drops only 0.05-0.10; regrowth recovers half the drop in 8-10 days. 96 of 125 events found (77%), 9 false, with extra cloud masking and parcels shrunk by 10 m. | Kolecka et al. 2018 **[FULL]** |
| Drop versus last cloud-free observation (Sen4CAP) | `NDVI(t) < NDVI(t_cf) - th_NDVI` | `th_NDVI` = 0.12 (NL, LT, CZ) or 0.15 (IT, ES, RO); minimum 28 days between detections; maximum detection interval 60 days (if `t - t_cf > 60`, output interval is `[t - 60, t]`). Output is an interval plus a confidence `f(x) = max - (max - min) * exp(-x)`, with `x` = drop minus threshold. | De Vroey et al. 2022 **[FULL, first half]** |
| Steepest pair inside a confirmed downtrend (WIST) | Smooth to daily NDVI (local Savitzky-Golay, min 4 clear obs, max 45-day window); MACD with windows 5, 10, 5 days; downtrend starts where MACD crosses zero downward; accept if mean abs MACD ("momentum") >= 0.01 and NDVI amplitude >= 0.15; then go back to the *unsmoothed* observations and take the adjacent pair with the fastest decrease. | Date = `(t1 + t2)/2`, uncertainty = `(t2 - t1)/2`. | Gao, Anderson, Hively 2020 **[FULL]** |
| Normalized Harvest Phenology Index | `HPI = NIR/NDVI`; normalize 0-1 inside `[MOS, MOS + 2 months]`; harvest = first date NHPI > 0.6. MOS = date NDVI has fallen to 50% of the senescence amplitude. | Corn harvest MAE 6.43 days, R2 0.749 (N = 151 fields); soybean MAE 5.39 days (N = 36), MODIS 500 m. | Liu and Diao 2025 **[FULL]** |
| Fixed-window state threshold | `LSWI_Sept <= 0.15` (silage) | See section 3. | Lin et al. 2025 **[FULL]** |
| Baseline anomaly (DIST-ALERT) | Vegetation fraction below the minimum of all observations in the previous 3 years within +/- 15 days. | Loss >= 10% tracked; >= 50% is the formal "disturbance"; two consecutive detections = "provisional"; confidence >= 400 = "confirmed". | OPERA DIST ATBD and Product Spec **[FULL]** |

Inference: for corn silage the single-step drop should be far larger than the grass thresholds above (full canopy to stubble and soil), so thresholds of 0.12-0.2 NDVI are a floor, not a target. No US corn-specific published threshold was found; fit ours on the labeled set and report it.

"Maximum negative slope" and "drop relative to seasonal amplitude" appear in the literature as WIST's fastest-decrease pair, WIST's amplitude >= 0.15 gate, and Shahrabi's `SPGH/LOS`. I found no source that publishes a slope threshold in NDVI per day for corn.

## 5. Curve fitting and smoothing

| Method | Where used | What the source reports | Lesson |
|---|---|---|---|
| Double logistic plus derivative (inflection points, SOS/EOS at 10% and 90%) | Santana et al. 2025, HLS, Brazil (Mato Grosso and Parana), farm-recorded dates for more than 1,600 soybean fields and several hundred corn fields, first author at CONAB (Brazil's national crop supply and statistics company) **[FULL]** | Corn harvest RMSE 6-15 days (their "RMSE" is a root *median* square error, so robust to outliers); S.D. of bias for EOS 10.76-26.76 days; EOS had to be shifted by a calibrated offset that changed by year for corn: +13, +3, +16, +4 days (2020-2023, Mato Grosso). About 10% of fields had poor double-logistic fits (R2 < 0.8) and were refit with Savitzky-Golay. Index choice (NDVI, EVI, WDRVI, NDWI) did not matter much once offsets were calibrated. | A fitted EOS is the end of senescence, not the harvest. The gap between them is the dry-down wait, which is exactly the thing that differs between silage and grain. Do not use EOS as the cut date. |
| Beck double logistic (pre-peak only) plus linear interpolation post-peak | Liu and Diao 2025 **[FULL]** | Used only for the green-up side; harvest is found with NHPI on the post-peak segment. | Even the authors of a curve-fit planting product do not curve-fit the harvest. |
| Whittaker smoother to 15-day steps | Lin et al. 2025 **[FULL]** | Enough for a window-state rule (September LSWI). | Coarse smoothing is fine when you ask "what state in this window", not "which day". |
| Local Savitzky-Golay, gap-aware (min 4 clear obs, max 45 days; WISE used 5 and 60) | Gao et al. 2020 **[FULL]** | "a large temporal gap will not be filled"; smaller window "can preserve abrupt changes"; the date is finally taken from unsmoothed data. | Smooth only to find the downtrend; read the date and the drop from raw observations. |
| No interpolation, no noise filters | FORCE mowing-detection UDF README (Schwieder et al. 2022 code) **[FULL README]** | Recommends `INTERPOLATE = NONE`, `BELOW_NOISE = 0`, `ABOVE_NOISE = 0` because noise filters "may remove potential mowing events". | Outlier filters treat a real cliff as noise. |
| 10-day compositing | Griffiths et al. 2020 **[ABS]** | "relatively high" omission for parcels with a single mowing event. | Compositing hides single events. Corn has exactly one. |

Senescence-rate metrics that are safe to compute tonight (definitions are mine, assembled from the above): `pre_slope` (NDVI or NDMI change per day over the three clear observations before `t1`), `MOS`, `drydown_days`, `drop_frac`. Asymmetric Gaussian and shape-model fitting: no opened source in this session; not recommended for one-season, gap-ridden series.

## 6. Change-point and break detection: what suits a short, irregular, cloud-gapped series

| Method | What it needs (from its own documentation) | Suitability for one corn season | Source |
|---|---|---|---|
| Pairwise drop on raw clear observations (Kolecka, Sen4CAP, WIST step 3) | Two clear observations bracketing the event. Irregular sampling is handled by construction (compare to the last cloud-free look; cap the interval). | **Best fit.** Transparent, no history, outputs an interval. | Sections 4 and 7 |
| PELT (`ruptures`) | A penalty value; `min_size` (minimum distance between change points, in samples) and `jump` (grid of candidate positions); cost models `l1`, `l2`, `rbf`, linear, autoregressive; average complexity O(CKn). No history is needed, and the documented usage is penalty-based (`predict(pen=3)`), so the number of breaks is not fixed in advance. | Usable. Inference: it works on sample index, not time, so on an irregular series it returns "between observation i and i+1", the same interval as the pairwise rule, with more robustness to one noisy point. With an `l2` cost a fade is split into several small steps, so the number of breaks is itself a crude cliff/fade indicator. | ruptures documentation **[FULL page]** |
| CCDC / COLD | GEE defaults: `minObservations` 6 ("number of observations required to flag a change"), `chiSquareProbability` 0.99, `minNumOfYearsScaler` 1.33, LASSO `lambda` 20; fits harmonic models. | **Poor.** Inference: needs more than a year of history and 6 consecutive post-break looks (weeks to months in a Midwest fall), and the harmonic model absorbs the annual harvest as seasonality. | GEE API reference **[FULL page]** |
| BFAST Monitor | A "stable history period", by default a linear trend plus order-3 harmonic season model, then an OLS-MOSUM monitoring process (`h = 0.25`, `level = 0.05`). | **Poor** for the same reasons. Could flag "harvest earlier than this pixel's seasonal norm" but that is what DIST-ALERT already delivers. | bfast CRAN manual, published 2026-04-01 **[FULL]** |
| BFAST Lite | Multiple breaks in one pass, handles NA; still a season-trend model with harmonics; `h = 0.15` minimal segment size. | Poor for a single season. | bfast CRAN manual **[FULL]** |
| LandTrendr | Works on the "annual" pixel story; records "the year that changes occurred". | **Not applicable** to within-season events. | LT-GEE guide **[FULL page]** |
| OPERA DIST-ALERT | 3 prior years, +/- 15 days, minimum vegetation fraction as baseline. | Product, not an algorithm to implement. See section 8.3. | ATBD **[FULL]** |
| MACD trend detector (WIST) | Daily gap-filled series; windows 5, 10, 5 days. | Good as the "is there a real downtrend" gate. | Gao et al. 2020 **[FULL]** |
| CUSUM, Bayesian online change point | No opened source evaluated them on crop harvest in this session. | Inference: no advantage over the bracketing-interval logic when there is one event per season and 5-15 usable looks. Skip. | none |
| 1D-CNN on NDVI plus SAR features | 64 meadows, 257 events to train and test. | Performance ceiling reference (F1 0.84) but needs event labels we do not have, and is not explainable. | Lobert et al. 2021 **[ABS]** |

## 7. Grassland mowing detection: the closest analog of "cut while green"

| Study | Data | Method | Accuracy | Timing | Notes |
|---|---|---|---|---|---|
| Kolecka et al. 2018, *Remote Sens.* 10(8):1221 **[FULL]** | Sentinel-2 L1C, Canton Aargau (CH); max 46 observations per pixel, 37 after extra masking | NDVI drop > 0.2 between consecutive (or second-to-last) clear observations | 96 of 125 events (77%), 9 false | Assigned to first observation after the cut | Standard ESA cloud mask alone "leads to significant overestimation"; fix was a blue-band threshold (B2 > 1500 DN on L1C) buffered 5 pixels, plus parcels shrunk 10 m. Residual false events "largely explained by field fertilization". "Even weekly cloudy periods may preclude detection." |
| Griffiths et al. 2020, *RSE* **[ABS]** | HLS, 10-day composites, Germany 2016 | Residuals of NDVI against an idealized trajectory | Overall agreement with farm reports; "relatively high" omission for single-cut parcels | Date ranges | About 25% of grassland area not mown. |
| Schwieder et al. 2022, *RSE* 269:112795 **[ABS + code README]** | Sentinel-2 + Landsat 8 data cube, Germany 2017-2020 | Residuals from a hypothetical undisturbed phenology, self-adaptive thresholds | MAPE of event counts 40% (2018), 36% (2019), 35% (2020); 92 and 78 validation parcels | Detected 11, 7 and 6 days after reported mowing | Less sensitive to gaps once >= 16 clear observations in the season, but their distribution matters. Open code: FORCE UDF `mowingDetection` (outputs include max data gap and clear-sky observation count per pixel). |
| Lobert et al. 2021, *RSE* 267:112751 **[ABS]** | Sentinel-1, Sentinel-2, Landsat 8; 64 meadows, 257 events, 2017-2019 | 1D-CNN, all feature combinations | Best F1 0.84 with NDVI + backscatter cross-ratio + 6-day coherence; frequency MAE 0.38 events per year | Date missed by 3.79 days on average | NDVI alone below optical+SAR but "clearly outperformed" SAR-only sets. |
| De Vroey et al. 2022, *RSE* 280:113145 (the Sen4CAP method, toolbox v3.0) **[FULL, first half]** | Sentinel-1 VH coherence (6-day pairs) + Sentinel-2 NDVI (MAJA cloud masks), 6 countries, 803 parcels; Wallonia field campaign 426 parcels, 261 mowing intervals | S2: drop versus last cloud-free NDVI > 0.12-0.15; S1: CFAR on coherence jump (PFA 3.0e-7) | F1 79% on hay meadows; practice classification OA 69% | Outputs intervals; reference built from daily Planet imagery as [last "tall", first "short"] with a 3-day buffer | S2 detections get the higher confidence range [0.5, 1], S1 [0, 0.5]. |
| De Vroey et al. 2023, *Remote Sens.* 15(1):181 **[FULL]** | Same sensors, sub-parcel management units | Same detector after excluding pastures | Precision 93%, detection rate 82% | - | Compares itself to a Sentinel-1 + Sentinel-2 + Landsat 8 CNN approach, probably Lobert et al. ("maximum precision of 86% and a detection rate of 82%"). |
| Gao et al. 2020 (WIST), BARC Maryland **[FULL]** | VENuS (5 m, 2-day) and Sentinel-2 (10 m), 29 recorded events 2019-2020 | Section 4 | VENuS: 0.0% missed, 3.4% false. Sentinel-2: 6.9% missed, 10.3% false | VENuS: bias 0.4, MAD 2.1, RMSE 2.6, mean uncertainty 3.5 days. Sentinel-2: bias 1.4, MAD 4.0, RMSE 5.1, mean uncertainty 6.1 days. Near-real-time lag about 4 days (VENuS) and 8 days (Sentinel-2), excluding data latency | Reported per-event uncertainty 2 to 8 days (dash lost in extraction). Clear pixel-days in the termination period: 14.8% (VENuS), 10.5% (Sentinel-2), "typical for a temperate zone"; gaps > 9 days occurred even at 2-day revisit. |
| Gao et al. 2023, *Science of Remote Sensing* 7:100073 **[ABS]** | HLS v2.0, Maryland and Delmarva, 2020-2021, 28,190 enrolled fields | WIST | 94% of terminations detected | About 49% within 1 week of farmer-reported dates, 72% within 2, 84% within 3, 90% within 4; detectable about one week after the operation; detections after mid-May more reliable than early spring (low NDVI) | Used operationally by USDA, USGS and Maryland Dept. of Agriculture; NASA reports verification time cut by at least 50% **[ABS, NASA Earthdata story]**. |
| Reinermann et al. 2022 **[NOT OPENED: PDF over size limit]** | Sentinel-1 + Sentinel-2 EVI, Germany | - | Snippet only: 60.3% of events, F1 0.64 | - | Low confidence. |

Take-aways for corn: detection of a green cut from optical data sits around F1 0.8 with week-level timing; optical beats SAR alone; the combination is best; clouds produce both misses and false alarms. Corn silage is an easier target than grass in two ways (Inference): the drop is larger, and corn does not regrow, so persistence can be demanded.

## 8. US corn and soybean harvest-date detection, products, and OPERA DIST-ALERT

### 8.1 Harvest-date studies and their error in days

| Source | Sensor and scale | Method | Error | Status |
|---|---|---|---|---|
| Liu and Diao 2025, CropPlantHarvest (ESSD preprint, discussion started 27 Oct 2025) | MODIS MCD43A4, 500 m, 12 Midwest states, 2001-2024 | NHPI threshold 0.6 after MOS | Field level against Beck's Hybrids records 2016-2024: corn harvest MAE 6.43 days, R2 0.749, N = 151; soybean MAE 5.39 days, R2 0.517, N = 36. State level against NASS Crop Progress, 2024: corn harvest MAE < 4 days in 10 of 12 states | **[FULL]** preprint, not yet peer reviewed |
| Santana et al. 2025 | HLS 30 m, Brazil | Double logistic EOS plus calibrated offset | Corn harvest RMSE 6-15 days (root median square error); cites MODIS studies at 11.0 and 17 days for harvest | **[FULL]** |
| Gao et al. 2020, 2023 (WIST) | VENuS, Sentinel-2, HLS | Section 4 | Section 7. Cover-crop termination and BARC "harvest/termination" records, not corn harvest | **[FULL] / [ABS]** |
| A PlanetScope yield study reporting harvest dates detected with RMSE 2.7 days on 20 fields | PlanetScope | Adapted sowing detector | - | **[NOT OPENED: publisher login redirect]** snippet only |
| HLS "WISE" emergence evaluation, 5 Corn Belt states 2018-2020 | HLS | WISE | Emergence, not harvest: field-scale MAD about 7 days, RMSE about 9 days | **[NOT OPENED]** snippet only |

Liu and Diao state the reason NDVI curve features fail for harvest: "when crops remain in the field long after maturity ... the event appears on a VI plateau rather than at a distinct turning point, as over-mature crops exhibit VI values comparable to bare soil." That sentence is the "grain fades out" clue in a citable form.

No CONUS-wide, field-scale corn harvest-date layer for 2025 or 2026 was found.

### 8.2 CropPlantHarvest as a data source

- Zenodo record 16967482, version 2, published 27 Aug 2025, CC BY 4.0, one archive `CropPlantHarvest.zip` (57.5 MB). Four layers: corn planting, corn harvesting, soybean planting, soybean harvesting. Pixel value = day of year. **[ABS]**
- Only "pure crop pixels" at 500 m, Midwest only, ends 2024.
- Inference: useful as (a) a county-level climatology of normal grain-harvest timing for the "relative to county median" feature, and (b) a 2024 backtest target for our own cut-date detector. In dairy counties its corn-harvest layer may show an early mode from silage fields; that is a hypothesis to check, not a finding.

### 8.3 NASA OPERA DIST-ALERT-HLS

| Question | Answer | Source |
|---|---|---|
| What is it | Per-pixel vegetation cover loss and a secondary "generic" spectral anomaly, computed for every HLS scene | Product Spec v1.0 (JPL D-108277, 12 Feb 2024) **[FULL]** |
| Baseline | Minimum vegetation fraction of all observations in the previous three years within a 31-day window (+/- 15 days); a minimum of six historical clear land observations is needed | ATBD **[FULL]**; GLAD page **[FULL page]** |
| Vegetation fraction model | A KNN model on HLS red, NIR, SWIR 1.6 and SWIR 2.1, trained on drone-derived fractional vegetation cover (8 cm drone NDVI linearly translated to cover, then aggregated to 30 m) | ATBD **[FULL]** |
| Does it flag cropland harvest | Only when it is unusual for that pixel. ATBD: "Land use dynamics that are part of an annual practice, for example crop rotations or tilling practices ... will not be flagged as disturbance if they occur within the same temporal window (+/- 15 days) in the previous three years ... very often these regular land changes may be shifted by more than 15 days between years and then they will appear within DIST-ALERT." It is "agnostic to vegetation type" and gives "no attribution of the causes". | ATBD **[FULL]** |
| Thresholds | Loss >= 10% is tracked; >= 50% is the formal disturbance class; status values: first, provisional (two consecutive detections), confirmed (confidence >= 400), finished (two consecutive non-anomalies, or one 15 days or more after the last anomaly) | Product Spec **[FULL]** |
| Useful layers | `VEG-IND` (current vegetation percent, every scene), `VEG-ANOM`, `VEG-ANOM-MAX`, `VEG-HIST`, `VEG-DIST-STATUS`, `VEG-DIST-DATE` (days since 31 Dec 2020), `VEG-DIST-COUNT`, `VEG-DIST-DUR`, `VEG-LAST-DATE`; 19 layers in total | Product Spec **[FULL]** |
| Resolution, tiling, format | 30 m, MGRS tiles 3660 x 3660, one Cloud-Optimized GeoTIFF per layer | Product Spec **[FULL]** |
| Coverage in time | Version 1 covers HLS granules from 1 Jan 2023 onward; collection short name `OPERA_L3_DIST-ALERT-HLS_V1` | Product Spec, Earthdata catalog **[FULL] / [ABS]** |
| Latency | Produced "at the cadence of HLS imagery"; "low latency" but no number in the documents read. HLS itself is listed at 2-3 days latency on a NASA Earthdata page. Confirmation needs later clear looks. | ATBD, NASA Earthdata story **[FULL] / [ABS]** |
| Known failure | Unmasked cloud is read as low vegetation and "marked as vegetation loss"; tracking through later observations removes most of these; relies on HLS Fmask | ATBD **[FULL]** |
| Access | LP DAAC (cloud-hosted, Earthdata login). The annual summary is in Google Earth Engine; I did not confirm an alert collection there. | Earthdata catalog **[ABS]**; GEE listing **[NOT OPENED]** |

Inference on use: a late-August to mid-September `VEG-ANOM` on a CDL corn pixel says "this field lost its canopy earlier than at any time in this 31-day window in the last three years". On a field in corn-soybean rotation that is a strong silage hint. On a dairy farm's continuous silage ground, or California's winter forage then corn cycle, the baseline already contains an early removal and nothing is flagged. So it is a one-sided feature: presence is informative, absence is not. `VEG-IND` is usable everywhere as a ready-made fractional cover series.

## 9. Cloud gaps and interval-censored dates

### 9.1 How often is the sky clear (NOAA NCEI Comparative Climatic Data, data through 2023) **[FULL tables]**

Mean number of clear days per month (the table also gives partly cloudy and cloudy days), and average percent of possible sunshine.

| Station | Clear days Aug | Sep | Oct | Nov | Percent possible sunshine Aug | Sep | Oct | Nov |
|---|---|---|---|---|---|---|---|---|
| Fresno, CA | 26 | 24 | 20 | 12 | 95 | 93 | 86 | 59 |
| Sacramento, CA | 26 | 24 | 19 | 10 | 96 | 93 | 84 | 61 |
| Bakersfield, CA | 26 | 24 | 19 | 12 | - | - | - | - |
| Stockton, CA | 26 | 23 | 19 | 9 | - | - | - | - |
| Des Moines, IA | 11 | 12 | 12 | 7 | 70 | 66 | 59 | 45 |
| Sioux Falls, SD | 12 | 12 | 11 | 7 | 61 | 59 | 57 | 49 |
| Omaha (Eppley), NE | 12 | 12 | 13 | 9 | 74 | 64 | 63 | 49 |
| Peoria, IL | 10 | 11 | 11 | 7 | 63 | 61 | 58 | 41 |
| Minneapolis-St. Paul, MN | 10 | 10 | 10 | 5 | 69 | 62 | 51 | 37 |
| Madison, WI | 9 | 9 | 9 | 5 | 62 | 58 | 50 | 37 |
| Green Bay, WI | 8 | 8 | 7 | 5 | 65 | 57 | 48 | 35 |
| Grand Rapids, MI | 8 | 7 | 6 | 3 | 62 | 57 | 43 | 29 |
| Syracuse, NY | 7 | 7 | 6 | 2 | 57 | 51 | 40 | 25 |
| Amarillo, TX | 14 | 15 | 17 | 15 | 76 | 70 | 74 | 67 |

Periods of record differ by station (for sunshine many end in 1983 or 2009; Sioux Falls sunshine is 2006-2009 only). These are sky-cover climatologies, not satellite clear-pixel counts.

### 9.2 How often does HLS look

- HLS User Guide V2.0 (April 2026 edition): "global land observation every 1.6 days on average" from Landsat 8/9 and Sentinel-2A/B/C. **[FULL]**
- OPERA ATBD: "2-4 day repeat visit cadence globally (Li & Roy, 2017)"; "median revisit rate of < 2 days". **[FULL]**
- Zhou et al. 2025 (IEEE GRSL), HLS V2.0 in 2022: observations every 1.6 days globally, 2.2 days in the tropics; global mean 69 and median 64 cloud-free observations per year. **[ABS]**
- Song et al. 2021 (*Science of Remote Sensing*): Landsat + Sentinel-2 revisit 4-7 days in the US in June-September 2017 and "cloud and shadow reduced clear-view observations by half". **[NOT OPENED: abstract page gave citation only; numbers from snippet]**
- Empirical, Maryland spring 2019-2020: Sentinel-2 clear pixel-days 10.5%, that is one clear look per about 9.5 days. **[FULL, Gao et al. 2020]**
- Schwieder et al. 2022: detection is robust once there are at least 16 clear observations in the season, provided they are well distributed. **[ABS]**

### 9.3 Expected width of the interval that contains the cut

Inference (my calculation, stated so it can be checked): let an HLS acquisition arrive every `s` days and be clear with probability `p`, independently. Gaps between clear looks are `s` times a geometric variable. The gap that happens to contain a randomly timed cut is length-biased, with expected width `s * (2 - p) / p`. Bracket `p` between the clear-day fraction (lower) and percent possible sunshine (upper), and take `s` = 2.5 days.

| Region and month | p range | Expected width of `[t1, t2]` | Half-width |
|---|---|---|---|
| Central Valley, Aug-Sep | 0.80-0.95 | 2.8-3.8 days | +/- 1.4-1.9 days |
| Central Valley, Oct | 0.61-0.86 | 3.3-5.7 days | +/- 1.7-2.8 days |
| Iowa, Nebraska, South Dakota, Sep-Oct | 0.35-0.66 | 5-12 days | +/- 2.5-6 days |
| Wisconsin, Minnesota, Sep-Oct | 0.23-0.62 | 5.6-19 days | +/- 3-10 days |
| Upper Midwest, Nov | 0.17-0.49 | 7.7-27 days | +/- 4-13 days |
| New York, Michigan, Oct-Nov | 0.07-0.43 | 9-69 days | +/- 5-35 days |

Real cloud is autocorrelated (multi-day systems), so long gaps are more common than this independent model says; treat the upper ends as realistic. The Maryland numbers above (mean half-gap 6.1 days with Sentinel-2 alone; 49% within one week with HLS) are consistent with the Midwest rows.

Inference on response time (a judged metric): time from cut to a confirmed optical detection = wait for the first clear look, plus a second look for persistence, plus 2-3 days of HLS latency. With the same model (first look after a random cut = half the length-biased gap, second look = `s / p`): roughly 6-8 days in the Central Valley in Aug-Sep and 1.5-3.5 weeks in the Upper Midwest in Sep-Oct. USDA-ARS measured about one week to first detection with HLS in Maryland.

### 9.4 How to carry the interval as uncertainty

1. Store `t1`, `t2` for every field, not just a date. Report `cut_mid = (t1 + t2)/2` and `cut_unc = (t2 - t1)/2` (WIST). Cap absurd intervals the way Sen4CAP does (`dt_max` = 60 days).
2. Fuse with radar: if the Sentinel-1 change date lies inside `[t1, t2]`, use it and shrink the interval to the radar revisit; if it lies outside, flag the field.
3. Recompute the date-dependent features at both ends of the interval (cut assumed just after `t1`, and just before `t2`, extrapolating the pre-cut slope). If the predicted class flips, the field goes to the "needs review" band regardless of its calibrated probability.
4. In rollups, publish acres by quality tier: interval <= 7 days, 8-14 days, > 14 days, no optical bracket. This turns "clouds hid the harvest week" from an excuse into a column in the table.
5. Inference, a physical bound worth stating: half milk line comes "2 to 3 weeks prior to kernel blacklayer" (Purdue), and grain then needs at least about 6 more days to fall from about 30% to 25% moisture at 0.8 points per day. So a field that is fully green in one clear look and bare in the next, three weeks or less apart, cannot have been combined as dry grain. Above about four weeks the pair alone no longer decides.

## 10. Indices: formulas, band names, and evidence for corn senescence and moisture

### 10.1 Band names

HLS User Guide V2.0, Table 3 **[FULL]**: `L30` (Landsat 8/9): B02 blue, B03 green, B04 red, B05 NIR narrow, B06 SWIR1, B07 SWIR2. `S30` (Sentinel-2A/B/C): B02 blue, B03 green, B04 red, B05/B06/B07 red-edge 1/2/3, B08 NIR broad, B8A NIR narrow, B11 SWIR1, B12 SWIR2. Red-edge bands exist only in S30. Sentinel-2 L2A uses the same numbers (B2, B3, B4, B5, B6, B7, B8, B8A, B11, B12).

HLS masking **[FULL]**: Fmask 4.7; clouds and cloud shadows are dilated by 150 m and labeled "adjacent to cloud"; Fmask classes (cloud, shadow, snow/ice, water, adjacency) are in QA bits 1-5 (bit 2 = adjacent, bit 5 = water in the guide's worked example), aerosol level in bits 6-7.

### 10.2 Formula table

Generic formulas are as listed in the awesome-spectral-indices catalog **[FULL table fetch]** unless marked. N = NIR, R = red, G = green, B = blue, RE1/RE2/RE3 = red edge, S1/S2 = SWIR.

| Index | Formula | Sentinel-2 L2A and HLS S30 | HLS L30 | What it tracks | Use for Kernel |
|---|---|---|---|---|---|
| NDVI | (N - R)/(N + R) | B8A (or B8), B4 | B05, B04 | Green cover; saturates | Secondary green-at-cut; amplitude and MOS |
| EVI2 | g (N - R)/(N + 2.4 R + L) in the catalog; usual constants g = 2.5, L = 1 (constants from memory) | B8A, B4 | B05, B04 | Green biomass, less saturation | Optional |
| kNDVI | (k(N,N) - k(N,R))/(k(N,N) + k(N,R)); commonly simplified to tanh(NDVI^2) (simplification from memory, not opened) | B8A, B4 | B05, B04 | As NDVI, more linear | Optional; no corn-harvest evidence opened |
| NIRv | NDVI x N | B8A, B4 | B05, B04 | Canopy structure x greenness | Optional |
| GCVI (CIgreen) | N/G - 1 (from memory; not in the catalog under this name) | B8A, B3 | B05, B03 | Chlorophyll | Optional |
| NDRE | (N - RE1)/(N + RE1) | B8A, B5 | not available | Chlorophyll, early senescence | Sentinel-2 only |
| CIre | N/RE1 - 1 | B8A, B5 | not available | Chlorophyll | Sentinel-2 only |
| IRECI | (RE3 - R)/(RE1/RE2) | B7, B4, B5, B6 | not available | Canopy chlorophyll | Sentinel-2 only |
| S2REP | 705 + 35 ((RE3 + R)/2 - RE1)/(RE2 - RE1) | B7, B4, B5, B6 | not available | Red-edge position | Sentinel-2 only |
| MTCI | (RE2 - RE1)/(RE1 - R) | B6, B5, B4 | not available | Chlorophyll | Sentinel-2 only |
| **NDMI = LSWI = NDII** | (N - S1)/(N + S1) | B8A, B11 | B05, B06 | Canopy water | **Primary green/wet-at-cut index** |
| NDWI (McFeeters) | (G - N)/(G + N) | B3, B8A | B03, B05 | Open water | Flood check only. Many crop papers say "NDWI" and mean NDMI |
| NMDI | (N - (S1 - S2))/(N + (S1 - S2)) | B8A, B11, B12 | B05, B06, B07 | Vegetation and soil moisture | Optional |
| MSI | S1/N | B11, B8A | B06, B05 | Water stress (inverse) | Redundant with NDMI |
| PSRI | (R - B)/RE2 | B4, B2, B6 | not available | Carotenoid/chlorophyll ratio, senescence | Sentinel-2 only |
| NDSVI | (S1 - R)/(S1 + R) (from memory; not opened) | B11, B4 | B06, B04 | Senescent vegetation | Unverified |
| NBR2 (= tillage "NDTI") | (S1 - S2)/(S1 + S2) | B11, B12 | B06, B07 | Residue versus soil | Ground-left feature. Catalog name is NBR2 |
| STI | S1/S2 | B11, B12 | B06, B07 | Residue versus soil | Ground-left feature |
| HPI / NHPI | N/NDVI, min-max normalized in [MOS, MOS + 2 months] (Liu and Diao 2025) | B8A, B4 | B05, B04 | Standing senescent crop versus residue | Optical grain-harvest date |

Tasseled cap: nothing opened in this session; skip tonight.

### 10.3 Evidence linking indices to corn moisture, dry-down and the silage/grain split

- Lin et al. 2025 **[FULL]**: Gini importance LSWI > NDVI > RENDVI > EVI for silage/grain/other; the authors attribute it to "LSWI's sensitivity to canopy moisture content in the SWIR band".
- Zhou, Zhou, Song, He 2022, *Remote Sens.* 14(3):584 **[FULL]**: field spectrometry over two maize seasons with irrigation treatments. Against canopy water content: NDII (850 and 1650 nm, the NDMI band pair) R2 0.79; WI (900/970) 0.75; NDWI (860/1240) 0.71; NDVI 0.69; OSAVI 0.64. All five are linear with canopy water content over 0.01-0.41 kg m-2 but nonlinear with whole-vegetation water content; NDII, NDVI and OSAVI stop responding above about 0.55 kg m-2 of vegetation water, WI and NDWI(1240) above about 1.12-1.15. Sentinel-2 and Landsat have no usable 970 or 1240 nm band, so NDMI is the best water index available to us.
- Santana et al. 2025 **[FULL]**: EVI needed the smallest EOS adjustment; NDVI and WDRVI "are less effective at the end of the season when senescence begins, as the near-infrared reflectance decreases slowly"; their NIR-SWIR index detects the end of season later because "even after reaching full maturity, there is still water in the plant and grain structure".
- Liu and Diao 2025 **[FULL]**: adding NIR to NDVI is what separates "senescent vegetation" from "exposed crop residues".
- Not found: any study that regresses satellite indices on corn kernel moisture or whole-plant dry matter for harvest timing. A 2026 *Plants* paper on regional maize plant moisture in Gansu (UAV + Sentinel-2 + Sentinel-3) surfaced in search but was **[NOT OPENED]**.

Inference: NDMI saturates at high canopy water, so "share of peak NDMI still present" will sit near 1 through grain fill and then fall with whole-plant dry-down, which is the behavior we want for green-at-cut. It also responds to wet soil after rain, so use it as a ratio to the field's own peak and prefer the field median over several interior pixels.

## 11. Confusers: abrupt optical drops that are not a silage harvest

| Confuser | What the sources say | How to separate (mostly inference) |
|---|---|---|
| Residual cloud and cloud shadow | "single-date cloudy observations cause a sudden drop of NDVI that can be easily confused with mowing events"; standard masking gave considerable overestimation (Kolecka 2018 **[FULL]**). Unmasked cloud is "marked as vegetation loss"; such errors "are not likely to regularly repeat over the same pixels" (OPERA ATBD **[FULL]**). | Use HLS Fmask including the 150 m "adjacent" class; field-interior pixels only; require the next clear look to stay low. Corn does not regrow, so a rebound within two weeks is an artifact. |
| Manure or fertilizer spreading | False mowing detections "largely explained by field fertilization" (Kolecka 2018 **[FULL]**). | Inference: on dairy ground manure usually follows the chop, so it deepens rather than fakes the post-harvest signal; it may make "ground left" look like bare soil. |
| Wind lodging (derecho) | NASA: areas damaged by the 10 Aug 2020 Iowa derecho "had decreased NDVI" (Sentinel-2B on 7 Aug versus Landsat 8 on 11 Aug) **[FULL page]**. Hosseini et al. 2020 mapped damage with Sentinel-1 and used HLS for crop type: 2.59 million acres damaged, 1.99 million corn, 1.087 million corn acres high impact **[ABS via Crossref]**. NASS's own derecho layer used wind-gust polygons intersected with the 2019 CDL and visual interpretation of MODIS NDVI, marked "not official NASS estimates" **[FULL page]**. | Inference: lodging lowers NDVI partially, keeps canopy water (NDMI stays up), leaves no bare soil, and hits whole neighborhoods on one date. Check county-wide synchrony and storm reports. Damaged corn is often salvaged as silage or abandoned, so these fields legitimately belong in "needs review / other fates". |
| Hail, defoliation | Snippets only **[NOT OPENED]**: NDVI differencing between two Sentinel-2 dates is the usual method; one Italian study ranked NDVI last of six indices (65.3% accuracy). | Same logic as lodging: partial drop, biomass remains, spatially coherent swath. |
| Frost kill | No source opened. | Inference: a region-wide step on the first hard-freeze date across corn and soybean alike, plants still standing (no radar change, no residue signal). Test: share of fields in the county dropping in the same interval, plus temperature data. |
| Drought or irrigation cut-off | No source opened. | Inference: a fade over one to three weeks, crop still standing. Shows up as low green-at-cut and long dry-down, that is grain-like, which is the right call. |
| Flooding | No source opened. | Inference: NIR collapses and open-water indices rise; HLS QA water bit. |
| Chemical desiccation | No source opened; not standard practice in US corn (from memory). | Ignore. |
| Double cropping (California) | Lin et al. gate maize with "May NDVI <= 0.2", which assumes bare ground before planting **[FULL]**. | Inference: with winter forage then corn, May is a harvest of the first crop, not bare soil. Pick the summer peak explicitly (after the spring trough), and expect two cuts per year on the same field. |
| Early grain harvest (Texas) | The published silage rule is tied to a calendar month and needed yearly re-tuning **[FULL]**. | Use state-at-removal (green-at-cut), not date. A July Texas grain field is brown at `t1`. |
| High-moisture corn, earlage, snaplage | No source opened (from memory): harvested near black layer for dairy feed, combined or head-chopped, counted as grain. | Inference: intermediate timing and partial residue. Ask the organizers how the labeled set treats them. |

## 12. Recipes

### 12.1 Field time series (raw, strictly masked)

```
for each field polygon:
    interior = polygon buffered inward by 20-30 m for HLS (10 m for native Sentinel-2)
    for each HLS L30/S30 scene from 1 June to 15 December:
        drop pixels flagged cloud, adjacent-to-cloud, cloud shadow, snow (Fmask QA bits)
        keep the scene only if most interior pixels are clear (start with >= 70%)
        store field medians of NDVI, NDMI, NIR, NBR2 and the count of clear pixels
do not interpolate, composite or outlier-filter before event detection
```

### 12.2 Cut interval (WIST logic with Sen4CAP's interval output)

```
peak  = highest 3-observation running median of NDVI in the summer window
soil  = low percentile of NDVI after the last drop (or the pre-emergence minimum)
A     = peak - soil                      # seasonal amplitude; if A < 0.3 -> "no crop signal"
for consecutive clear observations (i, i+1) after the peak date:
    d_i = NDVI_i - NDVI_{i+1}
pick the pair with the largest d_i       # WIST uses fastest rate; Kolecka also checks i versus i+2
accept if d_i >= max(0.15, 0.25 * A)     # 0.15 is WIST's amplitude gate; 0.25*A is a starting guess
      and the next clear observation after t2 is still low (persistence)
t1, t2   = dates of the pair
cut_mid  = (t1 + t2) / 2 ;  cut_unc = (t2 - t1) / 2
if t2 - t1 > 60 days: interval = [t2 - 60, t2]
```

### 12.3 Cliff-versus-fade numbers

```
green_at_cut_NDMI = (NDMI(t1) - NDMI_soil) / (NDMI_peak - NDMI_soil)
green_at_cut_NDVI = (NDVI(t1) - soil) / A
drop_frac         = (NDVI(t1) - NDVI(t2)) / A      # share of the season's amplitude lost in the step holding the cut
pre_slope         = slope per day over the 3 clear observations ending at t1
staleness         = cut_date (radar if available, else cut_mid) - t1
green_at_cut_adj  = max(0, green_at_cut + pre_slope * staleness)   # pre_slope is negative on a fade
MOS               = first date the linearly interpolated NDVI <= peak - 0.5 * A
drydown_days      = max(0, cut_date - MOS)          # 0 when the 50% crossing lies inside [t1, t2]
```

Expected signature (hypothesis to confirm on the labeled set): silage has `green_at_cut` near 1, `drop_frac` above about 0.5, `drydown_days` near 0, `pre_slope` near 0; grain has `green_at_cut` low, `drop_frac` small, `drydown_days` of weeks, a clearly negative `pre_slope`.

### 12.4 Optical grain-harvest date (NHPI)

```
HPI(t)  = NIR(t) / NDVI(t)
window  = [MOS, MOS + 60 days]
NHPI(t) = (HPI(t) - min HPI in window) / (max HPI in window - min HPI in window)
harvest_optical = first observation in the window with NHPI > 0.6
```

The 0.6 threshold was calibrated on MODIS 500 m pixels in the Midwest. Re-check it on our fields at 30 m.

### 12.5 Published baseline to beat (window-state rule)

```
silage if   NDMI_peak >= 0.16
       and  median NDMI in the silage window <= 0.15
```

Lin et al. used calendar September in Hohhot. Our version should place the window by growing-degree-days or relative to the county median. Report both in the metrics table.

### 12.6 Optional formal change point

```
import ruptures as rpt
algo = rpt.Pelt(model="l2", min_size=2, jump=1).fit(post_peak_ndvi_values)
breaks = algo.predict(pen=...)
```

Positions are sample indices; map them back to the dates of the bracketing observations. Tune the penalty on the labeled fields.

## 13. Agronomy constants that calibrate the timing features

| Quantity | Value | Source |
|---|---|---|
| Silage harvest stage | "usually begins around 50% kernel milk which is 42 to 47 days after silking" | UW-Madison Extension, "Timing Silage Harvest" **[FULL page]** |
| Black layer (R6) | "approximately 55 to 60 days" after silking | same |
| Ideal whole-plant moisture | Bunker 65-70%; bag 60-70%; upright stave 60-65%; oxygen-limiting 50-60% | same |
| Whole-plant dry-down | 0.5% per day in September as the planning rate; 0.4-0.7 measured in Wisconsin counties | same |
| Milk line caveat | "The position of the kernel milk-line is not a reliable indicator for determining harvest timing." | same |
| Grain moisture at black layer | about 30% | Purdue (R.L. Nielsen), "Field Drydown of Mature Corn Grain" **[FULL page]** |
| Grain field dry-down | about 0.8 points per day if maturity is reached in late August, about 0.4 if in mid to late September; more than 1 point per day on warm, dry, windy days | same |
| Half milk line to black layer | "2 to 3 weeks" | same |

Inference from these two pages: silage is cut 8-18 days before black layer; grain then needs 6-25 days to reach 25-20% and 19-38 days to reach 15%. For the same field and hybrid the silage cut therefore precedes the grain cut by roughly 2-8 weeks, usually more once the combine queue is added. This is the expected size of "cut date relative to county median" and of `drydown_days`, and it is far larger than the 5-15 day difference that was already enough in Lin et al.

## 14. Leads check, things not verified, open questions

### Leads from the brief

- "Gao et al. HLS-based harvest and emergence work": **partly confirmed**. Emergence (WISE) and cover-crop termination (WIST) by Feng Gao and colleagues are real and USDA-operational. I found no Gao paper that detects corn or soybean *harvest* dates from HLS.
- "Shang et al.": **not confirmed**. No matching harvest-date paper surfaced. (From memory only, not opened: an Agriculture Canada group published Sentinel-1 coherence detection of seeding and harvest; that is radar, not optical.)
- "Crop harvest detection with Sentinel-2 for EU CAP monitoring": **confirmed for mowing** (De Vroey et al. 2022 is the Sen4CAP method). A Sen4CAP harvest marker for arable crops was **not opened**.

### Not verified from a primary source

- Shahrabi et al. 2020 thresholds and whether it targets silage versus grain.
- Reinermann et al. 2022 numbers.
- Song et al. 2021 revisit and "reduced by half" numbers.
- PlanetScope harvest-date accuracy (2.7 days RMSE claim).
- The Nature Communications DIST-ALERT paper (login redirect) and any DIST-ALERT latency figure.
- Hail, frost, flooding, desiccation and irrigation cut-off studies.
- kNDVI simplification, GCVI and NDSVI formulas (memory).
- Soil-moisture sensitivity of NDTI (snippet only).
- HLS collections on Planetary Computer or Earth Engine (not checked here).

### Open questions

1. Where do the labeled silage-like and grain-like fields actually fall on `green_at_cut_NDMI` and `drop_frac`? No US corn threshold exists in the literature read.
2. How many clear HLS looks per field did August-November 2025 really deliver in Wisconsin and in the Central Valley? Count from the catalog instead of trusting the climatology.
3. How are storm-salvaged fields, high-moisture corn and earlage labeled in the evaluation set?
4. Does CropPlantHarvest's corn-harvest layer show an early mode in dairy counties (a free silage hint at 500 m)?
5. Does DIST-ALERT's `VEG-ANOM` add anything once green-at-cut and timing are in the model?

## 15. Annotated bibliography

Closest prior art
- Lin Z., Huang R., Tan S., Yang L., Huang J., Su L., Hu Z. (2025). Silage Maize Identification Using a Temporal Difference-Based Model with Sentinel-2 Data. *Agronomy* 15(6):1438. https://doi.org/10.3390/agronomy15061438 (read via https://mdpi-res.com/d_attachment/agronomy/agronomy-15-01438/article_deploy/agronomy-15-01438.pdf). **[FULL]** The only silage-versus-grain optical classifier found; three-rule LSWI/NDVI tree.
- Salehi Shahrabi H. et al. (2020). Automatic silage maize detection based on phenological rules using Sentinel-2 time-series dataset. *Int. J. Remote Sensing* 41(21):8406-8427. https://doi.org/10.1080/01431161.2020.1779377 **[NOT OPENED]** Includes Tulare County, California.

USDA-ARS termination detection
- Gao F., Anderson M.C., Hively W.D. (2020). Detecting Cover Crop End-Of-Season Using VENuS and Sentinel-2 Satellite Imagery. *Remote Sensing* 12(21):3524. https://doi.org/10.3390/rs12213524 (read via https://mdpi-res.com/d_attachment/remotesensing/remotesensing-12-03524/article_deploy/remotesensing-12-03524.pdf; summary at https://www.usgs.gov/publications/detecting-cover-crop-end-season-using-venms-and-sentinel-2-satellite-imagery). **[FULL]** WIST algorithm, thresholds, error table.
- Gao F., Jennewein J.S., Hively W.D., Soroka A.M., Thieme A., Bradley D., Keppler J., Mirsky S.B., Akumaga U. (2023). Near real-time detection of winter cover crop termination using harmonized Landsat and Sentinel-2 (HLS) to support ecosystem assessment. *Science of Remote Sensing* 7:100073. https://www.usgs.gov/publications/near-real-time-detection-winter-cover-crop-termination-using-harmonized-landsat-and **[ABS]**
- NASA Earthdata (data in action). USDA uses HLS operationally to detect cover crop termination. https://www.earthdata.nasa.gov/learn/data-in-action/usda-uses-hls-snwg-solution-operationally-detect-cover-crop-termination **[FULL page]**

Harvest-date products and studies
- Liu Y., Diao C. (2025). CropPlantHarvest: A 500 m annual dataset of crop planting and harvesting dates (2001-2024) of the U.S. Midwest. ESSD Discussions (preprint). https://essd.copernicus.org/preprints/essd-2025-526/essd-2025-526.pdf **[FULL]**; data https://zenodo.org/records/16967482 **[ABS]**. The NHPI method is credited to an AGU 2024 abstract by Liu, Diao, Yang, Mei, Guo (Landsat and Sentinel-2 on GEE), not opened.
- Santana C.T.C., Adami M., Prudente V.H.R., Garcia A.D.B., Caldas M.M. (2025). Using Harmonized Landsat Sentinel-2 Vegetation Indices to Estimate Sowing and Harvest Dates for Corn and Soybeans in Brazil. *Remote Sensing* 17:2927. https://doi.org/10.3390/rs17172927 (read via https://mdpi-res.com/d_attachment/remotesensing/remotesensing-17-02927/article_deploy/remotesensing-17-02927.pdf). **[FULL]**

OPERA DIST-ALERT and HLS
- OPERA DIST Product Specification v1.0, JPL D-108277, 12 Feb 2024. https://lpdaac.usgs.gov/documents/1766/OPERA_DIST_HLS_Product_Specification_V1.pdf **[FULL]**
- Hansen M.C., Pickens A., Song Z. OPERA DIST product ATBD. https://lpdaac.usgs.gov/documents/1835/OPERA_DIST_ATBD__V1.pdf **[FULL]**
- NASA Earthdata catalog entry. https://www.earthdata.nasa.gov/data/catalog/lpcloud-opera-l3-dist-alert-hls-v1-1 **[ABS]**; UMD GLAD page https://glad.umd.edu/dataset/DIST-ALERT **[FULL page]**
- HLS User Guide V2.0 (April 2026). https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf **[FULL]**
- Zhou Q. et al. (2025). Towards seamless global 30-meter terrestrial monitoring: evaluating 2022 cloud free coverage of HLS V2.0. *IEEE GRSL*. https://www.usgs.gov/publications/towards-seamless-global-30-meter-terrestrial-monitoring-evaluating-2022-cloud-free **[ABS]**

Mowing detection
- Kolecka N. et al. (2018). Regional Scale Mapping of Grassland Mowing Frequency with Sentinel-2 Time Series. *Remote Sensing* 10(8):1221. https://doi.org/10.3390/rs10081221 (read via https://mdpi-res.com/d_attachment/remotesensing/remotesensing-10-01221/article_deploy/remotesensing-10-01221.pdf). **[FULL]**
- Griffiths P., Nendel C., Pickert J., Hostert P. (2020). Towards national-scale characterization of grassland use intensity from integrated Sentinel-2 and Landsat time series. *RSE*. https://eolab.geographie.hu-berlin.de/publication/griffiths_2020/ **[ABS]**
- Schwieder M. et al. (2022). Mapping grassland mowing events across Germany based on combined Sentinel-2 and Landsat 8 time series. *RSE* 269:112795. https://eolab.geographie.hu-berlin.de/publication/schwieder_2022/ **[ABS]**; code https://github.com/davidfrantz/force-udf/tree/main/python/ts/mowingDetection **[FULL README]**
- Lobert F. et al. (2021). Mowing event detection in permanent grasslands. *RSE* 267:112751. https://eolab.geographie.hu-berlin.de/publication/lobert_2021/ **[ABS]**
- De Vroey M. et al. (2022). Mowing detection using Sentinel-1 and Sentinel-2 time series for large scale grassland monitoring. *RSE* 280:113145. https://research.dial.uclouvain.be/handle/2078.5/260919 **[FULL, first half]**
- De Vroey M., Radoux J., Defourny P. (2023). Classifying Sub-Parcel Grassland Management Practices by Optical and Microwave Remote Sensing. *Remote Sensing* 15(1):181. https://www.vliz.be/imisdocs/publications/386035.pdf **[FULL]**

Change-point tools
- Google Earth Engine, `ee.Algorithms.TemporalSegmentation.Ccdc`. https://developers.google.com/earth-engine/apidocs/ee-algorithms-temporalsegmentation-ccdc **[FULL page]**
- bfast R package reference manual (CRAN, 2026-04-01). https://cran.r-project.org/web/packages/bfast/bfast.pdf **[FULL]**
- ruptures documentation, Pelt. https://centre-borelli.github.io/ruptures-docs/user-guide/detection/pelt/ **[FULL page]**
- LT-GEE guide, LandTrendr. https://emapr.github.io/LT-GEE/landtrendr.html **[FULL page]**

Indices and moisture
- awesome-spectral-indices table. https://raw.githubusercontent.com/awesome-spectral-indices/awesome-spectral-indices/main/output/spectral-indices-table.csv **[FULL table fetch]**
- Zhou H., Zhou G., Song X., He Q. (2022). Dynamic Characteristics of Canopy and Vegetation Water Content during an Entire Maize Growing Season in Relation to Spectral-Based Indices. *Remote Sensing* 14(3):584. https://doi.org/10.3390/rs14030584 (read via https://mdpi-res.com/d_attachment/remotesensing/remotesensing-14-00584/article_deploy/remotesensing-14-00584.pdf). **[FULL]**

Clouds
- NOAA NCEI Comparative Climatic Data. Index https://www.ncei.noaa.gov/products/land-based-station/comparative-climatic-data ; sunshine https://www.ncei.noaa.gov/sites/default/files/2024-11/pctpos23.txt ; cloudiness https://www.ncei.noaa.gov/sites/default/files/2024-11/clpcdy23.txt **[FULL tables]**
- Song X.-P., Huang W., Hansen M.C., Potapov P. (2021). An evaluation of Landsat, Sentinel-2, Sentinel-1 and MODIS data for crop type mapping. *Science of Remote Sensing* 3:100018. https://lcluc.umd.edu/documents/song-x-p-huang-w-hansen-mc-potapov-p-2021-evaluation-landsat-sentinel-2-sentinel-1-and **[citation page only]**

Agronomy
- University of Wisconsin-Madison, Corn Agronomy. Timing Silage Harvest. https://corn.agronomy.wisc.edu/Management/L059.aspx **[FULL page]**
- Nielsen R.L., Purdue University. Field Drydown of Mature Corn Grain. https://www.agry.purdue.edu/ext/corn/news/timeless/graindrying.html **[FULL page]**

Confusers
- USDA NASS. Disaster Analysis 2020, Iowa Derecho Wind Damage (metadata). https://www.nass.usda.gov/Research_and_Science/Disaster-Analysis/2020/Iowa_Derecho/Derecho_Iowa_082520_2019CDL_metadata.htm **[FULL page]**
- NASA Scientific Visualization Studio. 2020 Iowa Derecho. https://svs.gsfc.nasa.gov/31341 **[FULL page]**
- Hosseini M. et al. (2020). Evaluating the Impact of the 2020 Iowa Derecho on Corn and Soybean Fields Using Synthetic Aperture Radar. *Remote Sensing* 12(23):3878. https://api.crossref.org/works/10.3390%2FRS12233878 **[ABS]**
