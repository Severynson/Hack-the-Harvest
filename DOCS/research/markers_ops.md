# markers_ops - Operational precedents: agencies that decide per parcel, or replace surveys, with satellite time series

Team Kernel, Hack the Harvest. Research pass written Saturday 2026-11-14.

## 0. Read this first: how the research was done and what is missing

- **Web search was not available.** The shared WebSearch budget for this workflow turn was already exhausted when this agent started, so **zero searches ran** (the brief asked for at least 12). Everything below comes from **directly fetching primary-source URLs and following links from them**. More searches would need a follow-up run or a higher `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`.
- **PDFs were read in full text.** No PDF tool is installed on this machine, so a small standard-library text extractor (kept in the session scratchpad, nothing installed) was used on the Sen4CAP ATBDs, the Sen4CAP Validation Report and two NASS methodology PDFs. Prose and simple tables came out cleanly. Two NASS tables had to be **reconstructed from column order**; they are marked "reconstructed" and should be checked against the PDF before a number goes on a slide.
- **Could not be opened** (so not used as evidence): the two JRC discussion/guidance documents in full text (landing pages only); the EC "Guidance and tools for CAP" wiki (login); EUR-Lex HTML (script shell only - the two regulations were read from the EU Publications Office repository instead); Medium (Sinergise blog posts, 403); MDPI and ScienceDirect papers (403); India MNCFC/FASAL (403); the Austrian AMA page (404); USDA ESMIS (DNS failure). Eurostat and Statistics Netherlands were not attempted for lack of a known primary URL.
- **Not found at all:** court rulings or formal legal challenges against satellite-based parcel decisions, and realised error rates from the post-2023 Area Monitoring System quality reports.
- Statements prefixed **Inference:** are this agent's reasoning, not something a source says.

---

## 1. Bottom line for tonight

1. **The "markers" design is the operational standard, and it is simple.** ESA's Sen4CAP harvest detector is five Boolean markers (NDVI present, NDVI lost, radar-ratio lost, radar-ratio present, coherence up) evaluated weekly; the harvest week is the first week in which all are true. It ran on more than 16 million parcels a year.
2. **Expect about 70-86% of cut dates within one week, 81-91% within two.** That is what Sen4CAP achieved in five of six countries over two seasons. Spain got 53% / 69%.
3. **The Spain failure is our signal.** There, crop senescence made NDVI collapse about two weeks before the real harvest, so the optical marker fired early. Inference: for grain corn the same lag is weeks long and is exactly our "dry-down days" feature; for silage it should be near zero.
4. **A three-way outcome with stated error budgets is how the EU stays defensible.** Green / yellow / red, with initial tolerances of 5% false red and 10-20% false green, and a fixed cascade for yellow parcels (look at images, ask the farmer, then visit). In 2019 only 2.9-11.2% of parcels were flagged after automated processing and at most 1% needed a field visit.
5. **NASS already works this way, and has a visible gap we fill.** The Cropland Data Layer exists to give "supplemental acreage estimates" to the Agricultural Statistics Board, as regression estimates and explicitly not pixel counts. County estimates have been model-based since crop year 2020 and are benchmarked to state totals. But NASS publishes county **corn silage** estimates in only **6 states (180 counties in 2025)** versus 31 states (1,238 counties) for corn grain, and they arrive around the end of May.
6. **What convinced Statistics Canada to drop a survey:** a 28-year back-test showing the model's median error against the final November figure equalled the survey's (4.1% vs 4.1%), an honest note that its worst cases were worse, one season of parallel publication, a model limited to about five predictors, and hard suppression rules (no release when the coefficient of variation exceeds 10%).

---

## 2. (a) EU Common Agricultural Policy: Checks by Monitoring, then the Area Monitoring System

### 2.1 Legal anchors (what the law actually requires)

| Instrument | What it says | Source |
|---|---|---|
| Implementing Regulation (EU) 809/2014, **Article 40a** "Checks by monitoring" (inserted 2018) | Regular, systematic observation and assessment of every eligibility condition that Copernicus Sentinel data (or equivalent) can monitor; follow-up where needed; 5% of beneficiaries checked for conditions that cannot be monitored (1-1.25% random, rest risk-based); provisional parcel-level results and warning alerts must reach farmers in time to "address or remedy the situation before the conclusions are drawn in the control report"; field visits only when evidence does not allow a conclusion. | https://www.legislation.gov.uk/eur/2014/809/article/40a |
| Implementing Regulation (EU) 2022/1173, **Article 10** "Area monitoring system" and **Article 11** | Conditions monitorable with Sentinel data are to be covered in 2023-2024 (in 2023 at least basic income support and area-constraint interventions); Member States may run a "cascaded analysis" with other data of equivalent value to reduce "non-conclusively monitored cases"; geotagged photos count as such data and enter the definition of "monitorable" from 1 January 2025; by 1 January 2027 at least 70% of interventions monitorable only by geotagged photo must be covered; farmers must be told which hectares fail so they can amend or add evidence, up to 15 calendar days before the first payment. The regulation never defines "conclusive"; it only uses "non-conclusively monitored cases". | https://publications.europa.eu/resource/cellar/80529bc7-fe57-11ec-b94a-01aa75ed71a1.0006.03/DOC_1 |
| Delegated Regulation (EU) 2022/1172, **Article 5** "Quality assessment of the area monitoring system" | Assessment on a **representative sample of parcels**, checking all eligibility conditions; ground truth from **in-situ visits or same-year imagery**; quantify (a) **errors from incorrect decisions expressed in hectares** and (b) the number of parcels found non-compliant; give **diagnostic information on the sources of incorrect decisions** by intervention and condition; propose remedial actions when deficiencies appear. The reports due by 15 February 2025 and 15 February 2027 must also verify that monitorable conditions were covered in 2024 and 2026. (The Commission's IACS page says the main components are assessed annually.) | https://publications.europa.eu/resource/cellar/81ef3f63-fe58-11ec-b94a-01aa75ed71a1.0006.03/DOC_1 |

### 2.2 The vocabulary (as sources define it)

| Term | Definition in the source | Source |
|---|---|---|
| Signature / signal | "information extracted from Sentinel data for each parcel and date, forming a time series" (parcel statistics: mean, std, min, max, median, quantiles; Sentinel-2 scene-classification histograms; Sentinel-1 backscatter and 6-day coherence) | JRC CbM docs, https://jrc-cbm.readthedocs.io/en/latest/dias4cbm_intro.html and md_overview.html |
| Marker | "an observation of a relevant bio-physical change of state, made on the Sentinel signal, on a given date" (JRC); "a characteristic change of the satellite signal over time that can be linked to a land cover event" (ECA glossary) | JRC CbM docs; ECA SR 04/2020 |
| Event | an observable activity, such as mowing or ploughing | JRC CbM docs |
| Scenario | a sequence of events; in practice one decision tree per land-use or crop group (Slovenia's basic-payment system has **eleven**) | JRC CbM docs; Planet Area Monitoring docs |
| Traffic light | Green = "assessed and confirmed as compliant"; Yellow = "insufficient evidence neither to confirm nor reject"; Red = "assessed and confirmed as definitely non-compliant" | https://docs.planet.com/data/area-monitoring/traffic-light-system/ |

The JRC marker tool has four modules: import parcel statistics, pre-process (resample, interpolate, smooth, drop cloudy observations), detect markers "based on minima and maxima values of band statistics" with "duration, amplitude and period of occurrence" used to reject false positives, then aggregate markers across sensors. Its only worked example is mowing: an NDVI drop plus a coherence increase in a close time window "leading to a more reliable activity detection", with coherence able to "compensate for data gaps in the NDVI time series". The module documentation page is still marked "documentation in progress" and gives no thresholds. Code: https://github.com/ec-jrc/cbm (BSD-3-Clause, 903 commits, built "exclusively on open source components").

Lead, not verified: the JRC discussion documents also describe scheme-specific "lanes". Only their landing pages opened (JRC112913 "Second discussion document on the introduction of monitoring to substitute OTSC", Devos et al. 2018, doi:10.2760/344612; JRC112918 "Technical guidance on the decision to go for substitution of OTSC by monitoring", Devos, Lemoine, Milenov, Fasbender 2018).

### 2.3 Error budgets, follow-up and first results (European Court of Auditors, Special Report 04/2020)

Source: https://op.europa.eu/webpub/eca/special-reports/new-tech-in-agri-monitoring-4-2020/en/

- **Flags:** agencies "assess the parcels/holdings, using a system of coloured flags". A grassland parcel "would be assigned a yellow flag until the Sentinel data indicates that it has been mown", then "its flag status is changed to green" (paras 13-14).
- **Two asymmetric error tolerances, set by the Commission as initial thresholds (para 28):**
  - **False red** (a correct declaration wrongly judged non-compliant): **5%**. The report notes little budget impact because the farmer would likely appeal.
  - **False green** (non-compliance not detected, so overpayment): **10-20%**, expected to be lowered as systems mature.
- **Follow-up cascade for yellow parcels (para 32):** (1) visual check of the images, (2) request information from the farmer, (3) field inspection if still unresolved.
- **Triage by money at stake (para 35):** below EUR 50 at scheme level, no follow-up; between EUR 50 at scheme level and EUR 250 at beneficiary level, follow up a **5% sample** of yellow parcels; above EUR 250, follow up all.
- **Uptake:** one agency in 2018 (Foggia, Italy); 15 of 66 agencies in five Member States in 2019; 28 agencies in 13 Member States planned for 2020.
- **Fears versus outcome:** nearly nine-tenths of surveyed agencies named "too many yellow parcels" as a major drawback (para 32); the Commission's reply was that it "did not materialise".

Table 3 of the report (basic payment scheme, 2019, as reported by the agencies by 7 January 2020):

| Paying agency | Area monitored (ha) | Parcels | Flagged red/yellow after automated processing | Followed up in office | Inspected in the field |
|---|---|---|---|---|---|
| Belgium (Flanders) | 599,545 | 397,568 | 3.5% | 1.5% | 1.0% |
| Denmark | 2,537,188 | 506,717 | 11.2% | 11.1% | 0.1% |
| Italy (6 provinces) | 1,104,491 | 718,692 | 3.3% | 1.0% | unknown |
| Spain (Castile and Leon) | 329,029 | 128,479 | 2.9% | 1.9% | 0.2% |

(Sum, this agent's arithmetic: 1,751,456 parcels on 4,570,253 ha.)

- **Small parcels are a minor share of area:** below 0.5 ha they were 1.9% of parcels but 0.2% of area in Flanders, 5.7% / 0.3% in Denmark, 1.0% / 0.1% in Castile and Leon (para 33).
- **What the auditors criticised (para 29):** the technical guidelines had no minimum sample sizes, selection criteria or reporting rules for quality control. Recommendation 1 asked for a quality-assessment framework by December 2021; Article 5 above is the result.
- **The skeptics inside the system:** 52 of 59 agencies called uncertainty about the Commission's later conformity audit an important obstacle (para 25), and the Commission does not approve methodologies (para 27).

### 2.4 A working traffic-light system: Slovenia, 2021 (Sinergise, now Planet Area Monitoring)

Sources: https://docs.planet.com/data/area-monitoring/traffic-light-system/ and /examples/, plus the marker pages under https://docs.planet.com/data/area-monitoring/markers/. This is vendor documentation; it gives no accuracy figures.

- Rule of the scheme: "if evidence of any farming activity is found among markers and signals for a FOI, then this FOI is assigned a Green", even when the crop differs from the claim.
- **Arable scenario:** 171,365 fields; 155,856 (about 91%) green because the predicted crop group matched the claim.
- **Grassland scenario:** 394,739 fields; "over 360 thousand" consistent with the claim and with at least one mowing detected.
- **Red is held back:** "At the moment Red is not automatically assigned, but this will change in the future." A corn claim with no vegetation and no bare soil ends as: "Since no evidence of farming is found the FOI is assigned Yellow."

Marker recipes from the same documentation:

| Marker | How it works | Numbers given |
|---|---|---|
| Bare soil | Per-observation probability on each valid Sentinel-2 date; "the actual events (ploughing or harvesting) cannot be directly detected in satellite imagery", so they are inferred from effects. **Also fires on non-photosynthetic vegetation from harvest or drying crops.** | Threshold "typically set to 0.8" |
| Greening and harvest | Harvest "is triggered by an abrupt and significant drop of the NDVI value", "often (but not necessarily) followed by a period when bare soil is detected" | None |
| Mowing | Drop and recovery in a vegetation index, at field or pixel level; misses grazing, long cloud gaps and near-threshold drops | From about 10,000 labelled events: mean NDVI drop about 0.15, about 20 days to recover |
| Similarity | Field NDVI series against the per-date mean and standard deviation of **up to 100 neighbours claiming the same crop**; score = mean squared standardised difference, converted to a percentile | Neighbourhood = hexagons 7.7 km across, own hexagon or plus a ring of six |
| Euclidean distance | Mean distance to up to 500 same-crop neighbours inside a crop-specific window | Corn window 15 May - 15 September |
| Homogeneity | Season-level features (for example three-month mean of within-field NDVI standard deviation) give a probability that the field is one crop | Homogeneous if probability above 35 (0-100 scale) |
| Crop group | LSTM on NDVI series trained on farmer declarations, with the training set first filtered by the distance and homogeneity markers because declarations can be wrong; **five-fold so every field is predicted by a model that never saw it** | About 200 crops grouped into 31 groups |

JRC's own field-validity tests (https://jrc-cbm.readthedocs.io/en/latest/uc_foi.html) work on fields with at least 40 pixels and flag "alien" clusters of more than 20 contiguous pixels; a one-field-to-many-objects result "requires interaction with the farmer".

---

## 3. (b) Sen4CAP (ESA): the agricultural-practices product, its harvest markers and its validation

Project documents: https://www.esa-sen4cap.org/resources/technical-documents/

### 3.1 Harvest detection recipe (ATBD for the L4C product, v1.5, 1 April 2021)

Source: https://www.esa-sen4cap.org/wp-content/uploads/files/06_Sen4CAP_DDF_v1.5_AgriPractices.pdf (21 pages, read in full)

**Per-parcel extraction**
- Inner buffer of half a pixel: **5 m for Sentinel-2, 10 m for Sentinel-1 and Landsat-8**.
- Signals: Sentinel-2 and Landsat-8 NDVI; Sentinel-1 **VV and VH backscatter converted to dB**; Sentinel-1 **VV coherence over 6-day pairs**. Statistics: min, mean, max, standard deviation.
- NDVI is kept only when at least **10%** of the parcel's pixels are valid under the cloud mask.
- A parcel needs at least **1 Sentinel-1 pixel** and at least **15 acquisitions** (configurable).

**Weekly aggregation** (ISO weeks starting Monday)
- Backscatter ratio = **VV - VH in dB**. Coherence increase is computed **separately for each orbit**.
- Week values: mean ratio, mean NDVI, max ratio, max coherence, max coherence increase.
- "Backscatter difference" = week-mean ratio minus the mean of the **previous three weeks**.
- NDVI gaps are expected; each empty week carries the nearest previous and nearest next value. Radar gaps "shall not occur".

**The five harvest markers**

| Marker | Meaning | Parameters and defaults (Table 2-1) |
|---|---|---|
| M1 | Vegetation present (NDVI). True from the first week NDVI exceeds the threshold, between the start of the season and the end of the expected harvest window | `OPTTHRVEGCYCLE` = 350 |
| M2 | Vegetation lost (NDVI). A loss threshold and a buffer value are computed from the weekly series, then compared with the previous and next NDVI of each week | `NDVIDW` = 300, `NDVIUP` = 350, `NDVISTEP` = 5, `OPTTHRMIN` = 100, `OPTTHRBUFDEN` = 4 |
| M3 | Vegetation lost (backscatter ratio). Backscatter difference against a threshold derived from the standard deviation of a filtered series; evaluated plus or minus one week when coherence jumps sharply | `AMPTHRMIN` = 0.1 |
| M4 | Vegetation present (backscatter ratio). Weekly maximum ratio against mean minus (standard deviation / `AMPTHRVALDEN`) | `AMPTHRVALDEN` = 2, `STDDEVINAMPTHR` = 0 or 1 |
| M5 | Vegetation lost (coherence). Weekly maximum coherence increase and weekly maximum coherence against thresholds | `COHTHRBASE` = 0.05, `COHTHRHIGH` = 0.15, `COHTHRABS` = 0.75 |

Notes: the NDVI values are on a x1000 scale (the sister ATBDs state `sc_fact = 1000`), so 350 means NDVI 0.35 - the L4C text itself does not say so. A further backscatter parameter, `AMPTHRBREAKDEN` = 6 ("amplitude threshold break denominator"), is listed without being tied to a marker. The table's formula for the `STDDEVINAMPTHR` switch prints "= 0" for both branches, an apparent typo in the source. The ATBD describes M2-M4 in words and leaves the exact inequalities to the open-source code; for M5 the tillage section spells it out: true "if the maximum increase in coherence is greater than the threshold for basic coherence increase or the maximum value of coherence is greater than the threshold for absolute coherence value".

**Decision rule**
- Pre-condition: M1 must be true at least once; otherwise every marker is "NR" and the result is `NO-HARVEST`.
- **Harvest week (`H_WEEK`) = the first week in which all of M1-M5 are true.** None found: `NO-HARVEST`.
- **`H_W_S1`** (added 2019): the same rule **without M2**. Reason given: "because of the cloud cover it can take more time when the loss of vegetation is confirmed from the NDVI data"; the radar-only date is available for the latest week "but the result can be less accurate".

**Reliability attributes written per parcel**
- `S1GAPS` (weeks with no Sentinel-1 at all, whole year), `H_S1GAPS` (inside the expected harvest window), `H_W_S1GAPS` (the **five weeks before** the detected harvest week).
- `H_QUALITY` = 1 warns that radar was missing in that five-week window. "The gaps in the S1 time-series have a strong negative impact on the reliability of the monitoring."

**A warning to users, verbatim:** "the users are advised not to change default values using trial and error approach."

**Other markers in the same product**
- M6-M10 score catch crops, nitrogen-fixing crops and fallow inside a declared period: NDVI presence (`EFANDVITHR` = 325), NDVI growth, no NDVI loss, no radar loss (regression slope over plus or minus two weeks, slope threshold 0.01 with p below 0.05), no coherence jump (`EFACOHCHANGE` = 0.2, `EFACOHVALUE` = 0.7). The combined result is a compliance index with the values STRONG, MODERATE, WEAK, POOR, issued only after the period ends; in-season values are "not final".
- **Tillage** (added 2020): starts the week after harvest; tillage is called when NDVI shows no vegetation and the coherence marker flips from true to false. The ATBD warns that with several coherence drops "the detector likely detects the first drop as tillage application".

### 3.2 Validation results (Validation Report v1.2, 21 May 2021)

Source: https://www.esa-sen4cap.org/wp-content/uploads/files/14_Sen4CAP_VR_v1.2.pdf (224 pages; harvest, mowing, tillage and summary sections read)

**Scale:** national runs in 2018 and 2019, "more than 16 million of parcels were assessed each year, covering around 600.000 km2"; near-real-time in Castile and Leon, Lithuania and the Netherlands in 2019.

**Reference protocol worth copying:** a stratified random sample of **250 parcels per country** "respecting the share of main crops", each interpreted on Planet imagery. Harvest is recorded as an interval: "the period between the date of the last image with the vegetation still present on the parcel and the date of the first image of the parcel with the vegetation lost".

**Harvest week accuracy against Planet interpretation** (share of parcels; "difference" = weeks between detected and reference)

| Difference | CZE 2018 | ITA 2018 | LTU 2018 | NLD 2018 | ROU 2018 | ESP 2018 | CZE 2019 | ITA 2019 | LTU 2019 | NLD 2019 | ROU 2019 | ESP 2019 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Within 1 week | 72% | 76% | 74% | 83% | 70% | 53% | 78% | 70% | 73% | 86% | 69% | 53% |
| Within 2 weeks (cumulative) | 87% | 88% | 89% | 91% | 84% | 69% | 88% | 81% | 87% | 90% | 85% | 69% |
| Within 3 weeks (cumulative) | 93% | 94% | 93% | 94% | 90% | 81% | 94% | 86% | 95% | 90% | 89% | 81% |

France 2019 (Planet, n = 250): 78% within one week, 84% within two, 7% not detected.

The report's conclusion: "except for Spain, the harvest detection method ... is robust and provides the results with accuracy above 70% (if one-week difference between real and detected event is considered) and above 80% (for two-week difference)."

**Summer crops only (the category that contains maize), 2019, Planet reference**

| Country | n | Within 1 week | More than 3 weeks off | Not detected |
|---|---|---|---|---|
| Czechia | 40 | 88% | 0% | 3% |
| Netherlands | 170 | 82% | 3% | 9% |
| Spain (Castile and Leon) | 33 | 79% | 6% | 12% |
| France | 98 | 74% | 9% | 13% |
| Romania | 127 | 69% | 5% | 1% |
| Italy | 51 | 65% | 25% | 8% |

**Against farmer-reported dates:** Castile and Leon 2018, n = 459: 53% within one week, 69% within two, 81% within three, 14% more than three, 5% not detected. Czechia 2019, n = 301: 61% / 78% / 86%. France 2019, n = 181: 65% / 81% / 82%, 11% not detected.

**Failure modes the report names**
- **Senescence read as harvest:** "the detected harvest week is shifted for about 2 weeks as the plant senescence phase is wrongly interpreted as harvest due to the abrupt decrease of NDVI. Another vegetation index with higher sensitivity to the dry ripe cereals' vegetation could be useful." In 2019: "results for winter and spring crops are biased due to the problem with crop senescence stage that is often detected as harvest ... especially in southern countries for cereals." Spanish winter and spring crops: only 48% within one week, 20% more than three weeks off.
- **Radar markers are weaker than optical ones:** for catch-crop markers, "higher accuracy figures for NDVI derived markers (above 80%) and lower figures for SAR derived markers (60 - 70%) ... compensated by the fact that SAR derived markers provide timely and guaranteed information". Example rows (CZE / LTU / NLD / ROU): NDVI presence 91.2 / 96.8 / 90.8 / 89.8%; backscatter "no loss" 77.2 / 78.6 / 77.9 / 43%; VV-coherence marker 67.6 / 32.1 / 67.6 / 66.9%.
- **Reference data are not truth:** farmer-reported harvest dates were confirmed by imagery for "around 75%" of 21 re-checked parcels. Listed reliability factors: radar gaps, errors in farmers' reports, selection bias in interviews, no near-infrared band in the Planet interpretation, "sensitivity of NDVI to plant senescence".
- **Coverage loss from small parcels:** in Castile and Leon 1,208,102 of 1,602,518 declared parcels (75.4%) could be processed for harvest, because "only parcels with at least one S1 inner pixel were processed". The product is specified for parcels larger than 1 ha.
- **Radar density assumed:** "Each parcel is usually covered by 2 to 4 orbits. In average, there are 3 acquisitions each week."
- **Main drivers of accuracy overall:** parcel size, parcel homogeneity, and time-series density.

**Tillage detector (2020), the cautionary tale for post-harvest radar**
- Lithuania, reference = farmers' **geotagged photos** (more than 600 parcels supplied, 350 used): 72% detected before the photo or within one week, 86% within two, 7% not detected.
- Lithuania, parcels declared **no-till** (n = 5,191): tillage was "detected" on **3,529 (68%)**. Reason: the first coherence drop after harvest is read as tillage, so "if other activities occur after the harvest (e.g. harvest residuals management) the detector likely detects this activity".
- Castile and Leon, farmers' reports (n = 33): 33% within one week, 57% within two, 37% more than three weeks off.

### 3.3 Mowing detection (ATBD for the L4B product, v1.3, 26 March 2021): "cliff versus fade", already written down

Source: https://www.esa-sen4cap.org/wp-content/uploads/files/06_Sen4CAP_DDF_v1.3_GrasslandMowing.pdf

- **Radar branch.** Physics as stated: tall vegetation gives low coherence; coherence across the cut is low because the scene changed; coherence between two post-cut images is higher. Detector: fit a straight line to the previous five 6-day coherences, then flag when
  `Cohe(latest) > Cohe_fit + k * sigma`, with `k = sqrt(2) * erfinv(1 - 2*PFA)` and `PFA = 3.0e-7` (k is about 5; this agent's arithmetic), `min_cohe_var = 0.024`. VV and VH are run separately and fused.
  Stated weakness: "rain on the scene and different moisture level between acquisitions" can hide a cut or create a false one.
- **Optical branch.** Two versions:
  - Against a fitted double-logistic curve of unmown growth: `VI(t) < model(t) - k * sigma_t`.
  - Against the last cloud-free value, **both** conditions required:
    `VI(t) < VI(t_cf) - thVI` (`decreasing_abs_th = 0.05`) **and** `VI(t_cf) - VI(t) > R_dec * N_days`.
    The second condition is the key sentence: "Decreasing rates lower Rdec are assumed to be decreasing of the VI due to natural phenology."
  - NDVI below 0.1 is treated as not exploitable; no second event is accepted within 60 days.
- **Fusion.** Optical detections get confidence in (0.5, 1.0); radar detections in (0, 0.5), so optical always outranks radar. The four most confident events per parcel are kept.
- **Validation (Validation Report executive summary).** 2018: "high recall, but ... a too low precision". After tuning for 2019 ("decreased sensitivity to the drying"): recall 68-69% (Castile and Leon, Czechia) to 88% (Italy); precision 51-53% (Romania, Castile and Leon) to 72% (Netherlands) and 76% (Czechia). Southern precision is lower "due to the grassland drying and grazing". Accuracy drops for partially mown parcels because indices are averaged over the parcel.
- The Sen4CAP site links an independent Belgian validation (De Vroey et al., Remote Sensing of Environment, 2022, doi:10.1016/j.rse.2022.113145). Not opened: publisher returned 403.

### 3.4 Bare-soil detection (ATBD v1.1, 29 March 2023): labels without ground truth, and a confidence ladder

Source: https://www.esa-sen4cap.org/wp-content/uploads/files/06_Sen4CAP_DDF_v1.1_BareSoil.pdf (38 pages, read in full)

**Indices (Sentinel-2 band names as written in the ATBD)**
- NDWI = (B8 - B11) / (B8 + B11)
- NDTI, "sometimes called Normalized Burned Ratio 2 (NBR2)" = (B11 - B12) / (B11 + B12)
- BSI = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))
- Model features: parcel means of B2, B3, B4, B8, B11, B12, NDVI, LAI, FAPAR, FCOVER, NDTI, BSI, NDWI.

**Step 1 - make calibration labels by thresholding** ("without the need for field data"; thresholds "defined using field data in Belgium and other tests")

| Label | Default rule |
|---|---|
| Bare soil | NDVI < 0.15 and NDWI < 0 and NDTI < 0.1 and BSI > 0.15 |
| Not bare soil | NDVI > 0.45 and NDWI > 0.3 and NDTI > 0.25 and FCOVER > 0.45 and BSI < 0 |
| Water or snow | NDVI < 0.15 and NDWI > 0.3 |
| Everything else | Unlabelled and dropped |

Only parcels with at least 50 Sentinel-2 pixels are used, over at least three months.

**Step 2 - two small models.** A random forest (**30 trees**) on the optical features for each date; then the same labels are carried to the nearest Sentinel-1 date (at most 3 days away) to train a second random forest on weekly radar features (VV, VH, ratio, VV and VH coherence, ascending and descending). The radar model exists so that the soil state is known "when the S2 is not available".

**Step 3 - period logic with six counters and a "traffic light" confidence**
- Strong detection = model confidence at least 0.8 (optical) or 0.65 (radar) for bare soil; 0.8 / 0.7 for not-bare.
- Windows: `Pshort` = 30 days, `Plong` = 60 days.
- Confidence of a detected period: **Strong** (at least three further strong detections after the first, low noise, clean ending) / **Good** / **Medium** / **Poor** / **Doubtful** (a single strong detection).
- Source inconsistency to be aware of: the definition and the calibration code compute NDWI with B11, but the prediction code listing uses B12 in its place.
- **When the radar period overlaps the optical one, the optical confidence is raised one level** and tagged "_S1".
- The ATBD's own advice: "The time series analysis and marker generations should be as understandable as possible."

### 3.5 Software availability

- Sen4CAP System **version 5.0 was released 6 October 2026** and adds a tillage processor; it supports Sentinel-1C and 1D. Download: https://www.esa-sen4cap.org/download-package-description/
- Minimum hardware for a site of about 90,000 km2: 8 cores, 64 GB RAM, 8 TB disk; national site of about 500,000 km2: 16 cores, 128 GB, 28 TB. Linux server install with a database and SNAP/MAJA pre-processing.
- The L4C ATBD states the time-series scripts are "open source and ... provided on Github"; the ATBDs themselves are CC BY-SA 4.0. The GitHub repository https://github.com/Sen2Agri/Sen2Agri-System (GPL-3.0) references Sen4CAP in its README; this agent did not locate the L4C code inside it.
- Inference: installing the system tonight is not realistic. **Re-implementing the marker logic in a notebook is**, because it is weekly aggregation plus threshold tests.

---

## 4. (c) National implementations with published numbers

| Country / region | What is published | Numbers | Source |
|---|---|---|---|
| Belgium (Flanders), Denmark, Italy (6 provinces), Spain (Castile and Leon) | First checks-by-monitoring results, 2019 | 2.9-11.2% of parcels flagged; at most 1.0% field-inspected (table in 2.3) | ECA SR 04/2020 |
| Italy (Foggia) | First use of the method | Started May 2018, one province | ECA SR 04/2020 |
| Slovenia | Traffic-light system, 2021 | 171,365 arable fields, about 91% green; 394,739 grassland fields | Planet Area Monitoring docs |
| Czechia, Italy, Lithuania, Netherlands, Romania, Spain (CyL), France | Sen4CAP harvest, mowing, practices | Tables in 3.2 and 3.3; crop-type overall accuracy 71-95% in 2018, above 90% in CZ, FR, NL in 2019 | Sen4CAP Validation Report v1.2 |
| Lithuania | Geotagged farmer photos used as reference for tillage | 350 parcels; 86% within two weeks | Sen4CAP Validation Report v1.2 |
| Spain (CyL) | GPS tracks of farm machinery used as reference | More than 1,000 parcels, one week in September 2020; activity type unknown | Sen4CAP Validation Report v1.2 |
| Estonia | Vendor pages only (KappaZeta: mowing, harvesting, ploughing and tillage detection; radar-filled "cloudless NDVI") | No accuracy figures on the pages opened | https://kappazeta.ee/services/agriculture/ |
| Netherlands, Austria, Germany, Denmark (agency pages) | Not opened | - | - |

---

## 5. (d) Statistical agencies that replaced or supplemented surveys

### 5.1 Statistics Canada - the cleanest "survey replaced by a model" case

Sources:
- Method and back-test: https://www.statcan.gc.ca/en/statistical-programs/document/5225_D1_T9_V1 ("Integrated Crop Yield Modelling Using Remote Sensing, Agroclimatic Data and Survey Data")
- Programme page: https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&SDDS=5225
- Field Crop Reporting Series: https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&SDDS=3401

**What was replaced, and when**
- 2015: modelled estimates "were published as a preliminary estimate to the September Farm Survey estimates" (parallel publication).
- "As of fall of 2017 ... The September survey has been replaced with the model-based data, reducing respondent's burden."
- July 2019: model-based yield and production used for Manitoba only. "Beginning in 2020, the July survey was fully replaced by model-based estimates for yields and production." July stocks became model-based from 2025.

**The model**
- Inputs: NDVI from the AVHRR sensor at **1 km**, as three-week moving averages for weeks 18-36; agroclimatic indices from about 478 stations; historical July and November survey yields from 1987; crop-insurance data on later occasions.
- Method: variable selection by LASSO, then robust (MM) regression in SAS. From 80 candidate variables per region, five was found to be the best number to keep; the programme page says "A maximum of five independent variables are included".
- Estimated per Census Agricultural Region, then aggregated with seeded-area weights.

**The evidence that carried the decision** (absolute relative difference from the final November survey yield, 1987-2014)

| Level, 7 major crops | Model: median / 75th / 90th / max | September survey: median / 75th / 90th / max |
|---|---|---|
| National | 4.1 / 6.9 / 13.1 / 39.4 % | 4.1 / 6.4 / 10.3 / 31.5 % |
| Provincial | 5.1 / 8.9 / 14.7 / 44.5 % | 4.4 / 7.4 / 11.5 / 35.5 % |

- Conclusion in the document: the model's estimates "were comparable to those produced by the September survey", but "These extreme relative differences tended to be larger for the model than for the September survey."
- The benchmark was the agency's own final figure, and the comparison was against the **incumbent method's error**, not against perfection.

**Publication and revision rules**
- No release when the model's coefficient of variation exceeds **10%**.
- At least **12 years** of July and November history required.
- A province is suppressed when suppressed regions hold more than 10% of its crop area; same rule nationally.
- Estimates are preliminary until November and then "subject to change for two years".
- Outputs are compared with other yield sources and "Subject-matter experts also review the results to identify any estimates which seem questionable."

### 5.2 Agriculture and Agri-Food Canada - Annual Crop Inventory

Source: https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9
- Decision-tree classification of optical and radar imagery, 30 m (56 m in 2009-2010), every year since 2009, national since 2011.
- Stated standard: it "meets the overall target accuracy of at least 85%".

### 5.3 Australian Bureau of Statistics

Source: https://www.abs.gov.au/statistics/detailed-methodology-information/information-papers/modernising-abs-agricultural-statistics (released 2 March 2023)
- "The ABS has ceased the REACS and the Agricultural Census" (the annual commodity survey and the five-yearly census). The survey's response rate was 68% in 2021-22 against a target of 80%.
- Replacements: levy-payer registers and **satellite crop maps** (a commercial provider maps the ten largest winter crops at paddock level, with yield for wheat, barley and canola; a Queensland map covers sugarcane).
- Validation language: for overlapping periods "the new data sources are mostly within the 95% confidence interval range of the survey-based statistics".
- Conceptual differences are disclosed rather than hidden (the new sources have no farm-size cut-off, the survey had one).

### 5.4 USDA NASS - its own use of remote sensing and models

**(i) The Cropland Data Layer was built to feed the Agricultural Statistics Board.**
Source: https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php
- Purpose: "to use satellite imagery to (1) provide supplemental acreage estimates to the Agricultural Statistics Board for the state's major commodities" and (2) publish the map.
- The internal figures "are not simple pixel counting but regression estimates using NASS survey data" - "an 'Adjusted Census by Satellite'" - meant to "create an unbiased statistical estimator of crop area at the state and county level for internal use".
- History: in-season acreage estimates first went to the October 2007 Crop Report; later to "the August, September and October Crop Reports for corn, soybeans, rice and cotton".
- Warnings to outside users: "Pixel counting is usually downward biased when compared to the official estimates"; pixel totals "should be considered raw numbers needing bias correction"; county pixel summaries "are not official NASS estimates".
- Accuracy: "The Producer's Accuracy is generally 85% to 95% correct for the major crop-specific land cover categories", and published assessments "are inflated somewhat" because validation used buffered data.
- Overall crop accuracy, continental US (the method of assessment changed with the 2024 layer): 2025 **75.4%** (kappa 0.712); 2024 77.5%; 2023 81.6%; 2022 80.9%; 2021 81.6%; 2020 81.3%.
- Training data: Farm Service Agency Common Land Unit records since 2006. Resolution 10 m since 2024. The confidence layer "should not be used as a measure of accuracy".

**(ii) County estimates are already model-based and benchmarked.**
Source: https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/County_Estimates_Row_Crops/06_2026/rcceqm26.pdf (released 5 June 2026)
- "Beginning with the 2020 crop year, model-based county-level estimates were incorporated." Bayesian small-area models for planted acres, harvested acres and yield; acreage models take "current year survey expansions, survey standard errors, and administrative data from FSA and RMA"; yield models add a soil productivity index.
- Estimates are posterior means; uncertainty is the posterior standard deviation, published as a coefficient of variation.
- "These county-level estimates are benchmarked against previously released state-level official estimates"; when a state figure is revised, county models are re-run so that counties "continue to add up".
- Publication standard: a minimum number of reports with both harvested acres and yield, or a minimum share of the county's harvested acres covered; counties that fail are merged into "Other Counties".
- **Coverage (reconstructed table):** corn for grain 31 states, 1,296 counties published in 2024 and 1,238 in 2025; **corn for silage 6 states, 204 counties in 2024 and 180 in 2025**.
- **Precision (reconstructed table), coefficient of variation of published county estimates, 25th / 50th / 75th percentile:**
  - Corn silage harvested acres: 2024 0.8 / 1.4 / 2.5%; 2025 1.2 / 2.0 / 4.3%.
  - Corn grain harvested acres: 2024 0.5 / 0.8 / 1.9%; 2025 1.4 / 3.4 / 9.9%.
- Timing: county survey collection ends mid-January; "estimates for most row crops being released by the end of May".
- County survey (36 states; reconstructed table): sample 57,349 in 2025, response rate 39.1% (57,795 and 39.7% in 2024).

**(iii) How the January number is made.**
Source: https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02_2026/cranqm26.pdf (released 4 February 2026)
- Everything in the Annual Crop Production Summary comes from the **December Agricultural Survey** (reconstructed table): sample 73,133 in 2025, **response rate 40.2%** (73,269 and 46.0% in 2024).
- Target coefficient of variation for US corn planted acres: 1%; achieved 1.0-1.3% over the last decade.
- **"Top-down":** national estimate first, then "ASB members must reexamine the State results and adjust some States to make the sum of the estimates agree with the National estimate".
- How an input is judged: "The historical relationship of the survey results to the official estimate is evaluated over time to determine accuracy and bias using tables and graphs." An official estimate "is established only upon ASB consensus".
- Outside data: "In order to be considered, these data must be deemed to be reliable and come from unbiased sources. Thus, they are often of limited use prior to the end of the season." The most common is Farm Service Agency certified acreage.
- Revision: "open to revision the following year only if new information becomes available", with a last chance after the five-yearly Census.
- Satellite imagery is already inside the survey design: the area frame is "stratified according to intensity of agriculture using satellite imagery".
- **Where the survey is least sure (reconstructed table):** coefficient of variation of the ratio "corn harvested for grain / corn planted". United States 0.3% in both years. Illinois 0.1% (2024) and 0.3% (2025); Iowa 0.5% and 0.5%; Wisconsin 1.9% and 2.9%. **California 30.8% and 23.3%; Arizona 18.5% and 38.3%; Idaho 8.6% and 18.5%; New Mexico 13.3% and 18.2%; New York 13.4% and 5.0%; Washington 11.2% and 11.8%.**
  Inference: the grain-versus-everything-else split is most uncertain precisely in the silage-heavy states.
- The document has no separate quality table for corn silage.

**(iv) National Academies, 2017, "Improving Crop Estimates by Integrating Multiple Data Sources".** Abstract only opened (https://www.nationalacademies.org/publications/24892): the panel was asked how to combine NASS surveys, other agencies' data and field-level farm-equipment data into more precise county estimates "with valid uncertainty measures". The model-based county programme above began three crop years later.

### 5.5 Not opened
India (FASAL, Mahalanobis National Crop Forecast Centre): site returned 403. Eurostat and Statistics Netherlands: no primary URL attempted. Nothing is claimed about them here.

---

## 6. (e) How these programmes communicate uncertainty and handle skeptics

| Practice | Who does it | What it looks like |
|---|---|---|
| Name both error types and give each a budget | EU Commission | 5% false red, 10-20% false green, announced as "initial" and to be tightened |
| Make "we cannot tell" a first-class answer | EU law; Slovenia | "non-conclusively monitored cases"; yellow flag; Red withheld until the system is trusted |
| Fixed escalation for uncertain cases | EU paying agencies | Images, then the farmer, then a visit; money thresholds decide how far to go |
| Tell the affected party early and let them answer | EU law | Provisional results and alerts; amendments allowed until 15 days before payment; geotagged photos accepted as evidence |
| Quality flags travel with each record | Sen4CAP | Gap counts and `H_QUALITY`; five confidence words for bare-soil periods; optical ranked above radar |
| Annual quality assessment on a random sample | EU law (Article 5) | Errors in hectares, causes of wrong decisions listed, remedial plan |
| Suppress rather than publish weak numbers | Statistics Canada; NASS | No release above 10% coefficient of variation; "Other Counties" |
| Publish precision next to the estimate | NASS; Statistics Canada | Coefficients of variation in Quick Stats; quality letters A to F |
| Label early numbers and state the revision rule | Statistics Canada; Sen4CAP; NASS | "preliminary until November", "subject to change for two years"; in-season results "are not final" |
| Compare with the incumbent, admit the tails | Statistics Canada; ABS | Same median error as the survey, larger extremes; "mostly within the 95% confidence interval" |
| Disclose weak reference data | Sen4CAP | Farmer dates confirmed for about 75%; "the real detection accuracy is probably lower" |
| Keep experts in the loop | NASS; Statistics Canada | Board consensus; subject-matter review of model output |

Appeals and court cases: nothing found. The only relevant statement opened is the auditors' remark that a false red has little budget effect because the farmer would likely appeal.

---

## 7. (f) Lessons mapped onto Kernel's plan

| Precedent | What it implies for the v2 plan |
|---|---|
| Sen4CAP five-marker AND rule | Keep the four measured numbers, but **store each as a marker row**: value, date, true/false, and a data-gap flag. The evidence card is then a table a paying agency would recognise. |
| `H_W_S1` versus `H_WEEK` | Report **two cut dates**: optical-confirmed and radar-only provisional. Do not merge them silently. |
| Spain senescence failure | Inference: the gap between the optical loss date and the radar or residue-confirmed cut date is the discriminating feature. Say so explicitly: "the error that hurt Sen4CAP is our signal". |
| Mowing ATBD dual test | Implement "cliff versus fade" as two tests: a minimum drop from the last clear observation **and** a minimum rate per day. Record the number of days between the two observations. |
| Radar markers 60-70% versus optical above 80%; tillage false positives 68%; rain and moisture false alarms | **Challenges the plan's radar-first cut date.** Treat radar as the timely, lower-confidence source and optical as the confirming one; do not use post-harvest radar alone for "ground left". |
| Radar density assumed by Sen4CAP (about 3 acquisitions per week, 6-day coherence) | Inference: US coverage is thinner and coherence is not available off the shelf. Use the VV - VH (dB) ratio from backscatter only; drop the coherence marker; widen weekly windows if needed. |
| Bare-soil thresholds (NDTI below 0.1 for soil, above 0.25 for vegetation) and the Planet marker that fires on dry residue | Inference: residue sits in the unlabelled middle. Generic "bare soil" detectors will not separate chopped-clean silage ground from grain stubble; use NDTI itself, measured only once NDVI is low. |
| Threshold-made calibration labels, then a 30-tree forest per sensor | A defensible way to stretch a small labelled set: rule-label only the unmistakable fields, train on those, and keep the provided labels purely for evaluation. |
| Similarity marker (up to 100 same-crop neighbours, 7.7 km hexagons) | Replace "relative to the county median" with **relative to nearby corn fields**; western counties are too large to be a peer group. |
| Five-fold predictions on declarations | Every reported metric should come from a model that never saw that field. |
| Green / yellow / red, Red withheld | Four states: silage-like, grain-like, inconclusive, **not assessable** (too small, too mixed, too few observations). With about 94% grain, withhold "silage-like" unless two independent markers agree. |
| 2019 results: 3-11% flagged, at most 1% visited | A credible target to state: inconclusive share in the low teens of corn acres or better, reported in acres. |
| Article 5 quality assessment | Report errors **in acres**, on a random sample, with a short list of causes (cloud gap, mixed field, small field, double crop). |
| Sen4CAP coverage loss (75.4% of parcels processed) | Treat not-assessable fields the way NASS treats non-respondents: reweight within county and size class, and show the share. |
| NASS: regression not pixel counts; top-down; benchmarking; "Other Counties"; coefficients of variation | Roll up the same way: ratio-adjust to a control total, reconcile counties to the state, publish a coefficient of variation, suppress thin counties. |
| NASS: "historical relationship ... to determine accuracy and bias" | Call the output an **indication** and show its bias and error against official state silage acres for past years. |
| Statistics Canada: five predictors; Sen4CAP: "relatively simple and fully transparent"; "do not tune by trial and error" | Lead with the two-question rule. Present the boosted model as a challenger and report the difference. Freeze thresholds before looking at the evaluation set; this also constrains the auto-research loop. |
| Statistics Canada needed 28 years and a parallel year | Do not claim survey-grade evidence. Propose a two-season parallel run. |
| EU cascade step 1 is a person looking at image chips | A natural Nemotron job: triage inconclusive fields (image-chip review, neighbour comparison), rank by acres at stake, produce a follow-up list. |
| Geotagged photos became legal evidence in the EU from 2025; Lithuania validated with them | A "request a photo" lane for inconclusive fields is a credible development path, and relevant to a spatial-imagery judge. |

---

## 8. Recipes

### 8.1 Sen4CAP harvest week (as documented)

```
per parcel, inner buffer 5 m (S2) / 10 m (S1):
  ndvi[date]      parcel mean, kept if >= 10% valid pixels
  ratio[date]     VV_dB - VH_dB
  coh[pair]       VV coherence, 6-day pairs, increase computed per orbit
weekly (ISO week):
  ndvi_w, ratio_w            means
  ratio_max_w, coh_max_w, dcoh_max_w
  bs_diff_w = ratio_w - mean(ratio of previous 3 weeks)
  NDVI gap -> carry nearest previous and next value
markers per week:
  M1  ndvi_w > 350 at some week in [season start, harvest window end] -> TRUE onward
  M2  NDVI loss vs computed threshold (bounds 300..350, step 5, min 100, buffer denom 4)
  M3  bs_diff_w vs threshold from std of filtered ratio (floor 0.1); +/-1 week if coherence jump >= 0.15
  M4  ratio_max_w vs (mean - std/2) of filtered ratio
  M5  dcoh_max_w vs 0.05 / 0.15, coh_max_w vs 0.75
decision:
  M1 never TRUE            -> NO-HARVEST, markers "NR"
  first week all TRUE      -> H_WEEK
  same without M2          -> H_W_S1  (radar-only, timelier, less accurate)
quality:
  weeks without any S1 in the 5 weeks before H_WEEK -> H_QUALITY = 1
```

### 8.2 Cliff or fade (Sen4CAP mowing rule, optical branch)

```
cliff if   VI(t_cf) - VI(t) >  thVI              (thVI = 0.05 for mowing)
      and  VI(t_cf) - VI(t) >  R_dec * N_days    (slower declines = natural phenology)
t_cf = last cloud-free observation before t;  N_days = t - t_cf
```
Inference for corn: use a much larger drop than 0.05 (mowing removes a few centimetres of grass, chopping removes the whole canopy) and choose `R_dec` from the labelled fields. Also keep `VI(t_cf) / VI_peak` as "green at cut". When `N_days` exceeds roughly two weeks the rate is not measurable; route to inconclusive.

### 8.3 Kernel marker table (Inference: an adaptation, not a published method)

| Marker | Definition | Analogue |
|---|---|---|
| K1 crop established | Peak NDVI above a threshold inside the season | M1 |
| K2 optical loss | Date, drop, days and rate between last clear pre-loss and first clear post-loss observation; green-at-cut | M2 plus 8.2 |
| K3 radar loss | Week when the VV - VH (dB) weekly mean departs from the trailing three-week mean by more than a multiple of the field's own variability | M3 |
| K4 dry-down gap | Cut date minus the date NDVI or NDMI fell below about half of peak | The Spain failure, used as a feature |
| K5 ground left | NDTI = (B11 - B12)/(B11 + B12) on clear dates after the cut while NDVI is low | Bare-soil ATBD |
| K6 peer timing | Percentile of the cut date among nearby corn fields | Similarity marker |
| K7 context | Distance to dairy; winter-forage double-crop fingerprint | Tie-breakers only |
| Q flags | Longest cloud gap around the cut; radar acquisitions in the five weeks before; field pixel count; within-field NDVI spread | `H_QUALITY`, homogeneity |

### 8.4 Outcome rule with error budgets (Inference)

```
not assessable : too few pixels, or within-field spread too high, or too few observations
silage-like    : K1 and cliff (8.2) with high green-at-cut and K4 near zero
                 [>= 2 independent markers agree]
grain-like     : K1 and fade and (K4 of weeks or K5 residue-like)
inconclusive   : everything else, or a Q flag raised on the deciding marker
budgets        : state a tolerance for "called silage, was grain" and a looser one
                 for "called grain, was silage"; report both, plus the inconclusive
                 share, in acres
confidence     : Strong / Good / Medium / Poor from the number of agreeing markers;
                 raise one level when the second sensor agrees
```

### 8.5 Roll-up the NASS way (from the three NASS documents)

1. Field calls to county: sum assessed acres by class; reweight not-assessable acres within county and field-size class.
2. Ratio-adjust to a control total rather than trusting pixel sums.
3. State first, then make counties add up to the state.
4. Publish a coefficient of variation per county; merge thin counties into "Other counties".
5. Label the November figure an indication; say when it will be revised (after the final Cropland Data Layer and after the January summary).
6. Keep a table of indication versus official for each past year: bias and absolute relative difference.

### 8.6 One-page "Methodology and Quality Measures" for the notebook

Use NASS's own headings so the judges recognise the form: Scope and Purpose; Timeline; Data sources; Field selection and exclusions; Edit and quality flags; Estimators (marker rules, roll-up, benchmarking); Revision policy; Quality metrics (precision, recall, false-positive rate with intervals; inconclusive and not-assessable shares in acres; coefficient of variation by state; back-cast difference from official). Add an ATBD-style parameter table: name, default, what it controls.

---

## 9. What this means for Kernel

**Build in the next 18 hours**
1. Turn the four numbers into a marker table with dates, Booleans and gap flags; render it on the "Harvest Story" card.
2. Add the rate test so "cliff" and "fade" are computed, not eyeballed; store green-at-cut and days between observations.
3. Emit four states and report the inconclusive and not-assessable shares in acres.
4. Keep two cut dates (optical-confirmed, radar-only) and flag missing radar in the five weeks before the cut.
5. Swap the county median for a nearby-corn-fields reference if field counts allow.
6. Roll up with a ratio adjustment, top-down reconciliation, a coefficient of variation and an "Other counties" rule.
7. Back-cast at least 2025 (and 2024 if compute allows) against official state silage acres and show bias and absolute relative difference.
8. Give Nemotron the escalation job for inconclusive fields.

**Say to the NASS statisticians**
- "This is an indication for the Board, not an estimate. Here is its historical relationship to your official number."
- "We do not count pixels. Your own Cropland Data Layer page says pixel counting is biased; we ratio-adjust and benchmark, as your county programme does."
- "Your county silage estimates cover six states and arrive around the end of May. This gives a county indication everywhere corn is grown, in November."
- "The survey's precision on the share of corn harvested for grain is 0.3% nationally but 23-31% in California. That is where a second, independent indication is worth most." (Check the reconstructed table first.)
- "We publish an inconclusive class and a coefficient of variation, and we suppress thin counties."
- "European paying agencies have used the same marker logic at 16 million parcels a year. Where it failed - senescence mistaken for harvest - is the lag we measure on purpose."
- "Statistics Canada needed a 28-year back-test and a parallel season before replacing a survey. We are proposing a parallel run."

**Plan items this research challenges**
- Radar-first cut date (operational evidence ranks radar markers below optical ones, and coherence is doing much of the work in Sen4CAP).
- Post-harvest radar for "ground left" (68% false tillage on no-till parcels).
- County median as the peer reference.
- Presenting summed field acres as an estimate before bias adjustment.
- Threshold tuning by an automated loop on a small labelled set (the Sen4CAP authors warn against trial-and-error tuning; reference labels were themselves wrong about a quarter of the time in one check).
- Leading with the boosted model rather than the rule.

---

## 10. Pitfalls

1. An NDVI drop is not a harvest. Senescence shifted Sen4CAP dates by about two weeks in cereals.
2. Radar-only event detectors have low precision: rain, moisture changes and residue handling all move coherence and backscatter.
3. Small, narrow or mixed fields cannot be assessed; a quarter of parcels dropped out in one region.
4. Corn-mask error propagates: the 2025 Cropland Data Layer's overall crop accuracy is 75.4% under the new assessment method.
5. Reference labels have errors, and a small labelled set gives wide intervals.
6. Do not over-claim equivalence with a survey on one or two seasons of back-casting.

## 11. Open questions

1. Do NASS weekly Crop Progress reports carry corn-silage harvest progress for the states in the evaluation set? (Unverified lead; it would give a weekly official series to validate cut dates.)
2. Which six states have county corn-silage estimates, and can those counties serve as back-cast truth?
3. What false-red and false-green rates did the post-2023 Area Monitoring System quality reports actually record, and are there court rulings on satellite-only evidence? (Nothing opened.)
4. How many Sentinel-1 acquisitions per week do the target states really get, against the roughly three per week Sen4CAP assumed?
5. What validation standards do India's FASAL programme, Eurostat and Statistics Netherlands apply? (Not opened.)

---

## 12. Annotated bibliography (every URL below was opened unless marked)

**EU control system**
- European Court of Auditors, Special Report 04/2020, "Using new imaging technologies to monitor the Common Agricultural Policy". Flags, error tolerances, follow-up cascade, 2019 results, the quality-assessment gap. https://op.europa.eu/webpub/eca/special-reports/new-tech-in-agri-monitoring-4-2020/en/
- Commission Implementing Regulation (EU) 809/2014, Article 40a (retained text). https://www.legislation.gov.uk/eur/2014/809/article/40a
- Commission Implementing Regulation (EU) 2022/1173, Articles 10-11. https://publications.europa.eu/resource/cellar/80529bc7-fe57-11ec-b94a-01aa75ed71a1.0006.03/DOC_1
- Commission Delegated Regulation (EU) 2022/1172, Articles 3-5. https://publications.europa.eu/resource/cellar/81ef3f63-fe58-11ec-b94a-01aa75ed71a1.0006.03/DOC_1
- European Commission, "Managing payments" (IACS overview; early-warning alerts). https://agriculture.ec.europa.eu/common-agricultural-policy/financing-cap/assurance-and-audit/managing-payments_en
- JRC CbM documentation (definitions, marker tool, field tests). https://jrc-cbm.readthedocs.io/en/latest/ ; code https://github.com/ec-jrc/cbm
- JRC112913 and JRC112918 landing pages (abstracts only; full text not opened). https://publications.jrc.ec.europa.eu/repository/handle/JRC112913 ; https://publications.jrc.ec.europa.eu/repository/handle/JRC112918
- Planet (Sinergise) Area Monitoring documentation: traffic-light system, examples, and marker pages. https://docs.planet.com/data/area-monitoring/traffic-light-system/ ; https://docs.planet.com/data/area-monitoring/markers/

**Sen4CAP**
- ATBD, L4C agricultural practices, v1.5 (2021). https://www.esa-sen4cap.org/wp-content/uploads/files/06_Sen4CAP_DDF_v1.5_AgriPractices.pdf
- ATBD, L4B grassland mowing, v1.3 (2021). https://www.esa-sen4cap.org/wp-content/uploads/files/06_Sen4CAP_DDF_v1.3_GrasslandMowing.pdf
- ATBD, bare-soil detection, v1.1 (2023). https://www.esa-sen4cap.org/wp-content/uploads/files/06_Sen4CAP_DDF_v1.1_BareSoil.pdf
- Validation Report v1.2 (2021). https://www.esa-sen4cap.org/wp-content/uploads/files/14_Sen4CAP_VR_v1.2.pdf
- Technical documents index, product descriptions, download page. https://www.esa-sen4cap.org/resources/technical-documents/ ; https://www.esa-sen4cap.org/data-tools/eo-products/ ; https://www.esa-sen4cap.org/download-package-description/

**Statistical agencies**
- Statistics Canada, "Integrated Crop Yield Modelling Using Remote Sensing, Agroclimatic Data and Survey Data". https://www.statcan.gc.ca/en/statistical-programs/document/5225_D1_T9_V1
- Statistics Canada, Model-based Principal Field Crop Estimates (record 5225). https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&SDDS=5225
- Statistics Canada, Field Crop Reporting Series (record 3401). https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&SDDS=3401
- Agriculture and Agri-Food Canada, Annual Crop Inventory. https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9
- Australian Bureau of Statistics, "Modernising ABS Agricultural Statistics" (2023). https://www.abs.gov.au/statistics/detailed-methodology-information/information-papers/modernising-abs-agricultural-statistics
- USDA NASS, Cropland Data Layer FAQ. https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php
- USDA NASS, Annual Crop Production Methodology and Quality Measures (4 February 2026). https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02_2026/cranqm26.pdf
- USDA NASS, Row Crops County Estimates Methodology and Quality Measures (5 June 2026). https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/County_Estimates_Row_Crops/06_2026/rcceqm26.pdf
- USDA NASS, County Agricultural Production Survey guide. https://www.nass.usda.gov/Surveys/Guide_to_NASS_Surveys/County_Agricultural_Production/index.php
- National Academies (2017), "Improving Crop Estimates by Integrating Multiple Data Sources" (abstract only). https://www.nationalacademies.org/publications/24892

**Opened but thin**
- KappaZeta (Estonia), agriculture services and blog: capabilities listed, no accuracy figures. https://kappazeta.ee/services/agriculture/

**Cited by the sources above, not opened by this agent**
- Tamm, Zalite, Voormansik, Talgre (2016), "Relating Sentinel-1 interferometric coherence to mowing events on grasslands", Remote Sensing 8(10), 802 (cited in the L4B ATBD).
- De Vroey et al. (2022), "Mowing detection using Sentinel-1 and Sentinel-2 time series for large scale grassland monitoring", Remote Sensing of Environment, doi:10.1016/j.rse.2022.113145 (linked from the Sen4CAP site; 403).
- Sinergise "Area Monitoring" blog series on Medium (linked from the Planet docs; 403).
