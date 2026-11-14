# Nowcasting corn silage vs grain: current-year corn mask, earliness vs accuracy, honest real-time simulation

Research note for team Kernel, Hack the Harvest. Written Saturday 2026-11-14.

## 0. How this was produced, and its limits

- **Web search was not available.** The session-wide WebSearch budget (200 calls, shared by all agents) was already exhausted before my first query, so **zero searches were run** (the brief asked for at least 12). Everything below comes from **directly opening primary pages by URL** (NASS reports and pages, arXiv, NASA Earthdata, Copernicus documentation, Google Earth Engine catalog pages, and OpenAlex / Semantic Scholar metadata records for paywalled papers). About 60 pages were opened.
- Consequence: coverage is deep on NASS primary data and thin on "is there any public 2026 in-season crop map" (could not be searched) and on the paywalled papers (abstract-level only). Each gap is flagged where it matters and listed in section 9.
- Convention: plain statements are what the source shows. Anything I derived is prefixed **Inference:**.
- NASS state PDFs could not be parsed by the fetch tool; I read the downloaded PDFs directly, so the numbers in section 4 are transcribed from the report tables themselves.

## 1. Bottom line

1. **There is no 2026 corn mask from NASS and there will not be one before the silage number is published.** CDL 2025 was released 2026-02-27; the CDL release page (last modified 2026-06-12) lists no 2026 or in-season product. NASS's in-season CDL acreage estimates are internal.
2. **Official 2026 silage acres do not exist yet.** In the 2026-11-10 Crop Production report the 2026 "Corn for silage" cell is blank ("estimation period has not yet begun"). The 2025 figure first appeared on 2026-01-12. The 2027 calendar is not posted; expect about 2027-01-12.
3. **Silage chopping is essentially finished by mid-October in the Upper Midwest, about two weeks later in New York.** Wisconsin: 50% about Sep 24 (2024 and 2025), 92% on Oct 13, 2024, 87% on Oct 4, 2026. Minnesota: 98% on Oct 13, 2024. New York: 73% on Oct 13 and 90% on Oct 27, 2024.
4. **Grain harvest is far from finished today.** On Nov 8, 2026 corn-for-grain harvest was 81% in the 18 major states (5-year average 86%): Iowa 72%, Nebraska 74%, South Dakota 68%, Wisconsin 72%, Michigan 61%. Roughly a fifth of grain corn has no cut date yet. A Nov 14 nowcast must classify "still standing" fields rather than drop them.
5. **Lead time over the January number:** Oct 1 = 14.7 weeks, Oct 15 = 12.7 weeks, Nov 1 = 10.3 weeks, Nov 14 = 8.4 weeks.
6. **The 2025 backtest has a hole in its reference data:** weekly Crop Progress was cancelled for the weeks ending Oct 5 through Nov 9, 2025 (lapse in federal funding). There is no official weekly harvest progress for October 2025.
7. **Benchmarks to beat:** national persistence was nearly perfect in 2025 (6,207K to 6,208K acres), but state-level persistence was off by 15.1% of the national total in absolute terms. Skill has to be shown at state level.

## 2. (a) The current-year corn mask

### 2.1 What NASS publishes and when (verified)

| Item | What the source shows | Source |
|---|---|---|
| CDL 2025 release | "The 2025 CDL product was released February 27, 2026." CDL 2023 was released January 31, 2024. | CDL FAQ; CDL "SARS1a" page |
| In-season / preliminary 2026 CDL | None listed. Release page last modified 06/12/2026 lists national CDL at 10 m for 2024 and 2025, 30 m for 2008-2025, and no 2026 product. | CDL Release page |
| Resolution | "Beginning in 2024, the CDL spatial resolution has increased to 10-meters." 2008-2023 are 30 m. | CDL FAQ |
| Inputs for CDL 2025 | Landsat 8 and 9 OLI/TIRS and Sentinel-2A and -2B; "10-day median composites of surface reflectance and NDVI". Training and validation data from the FSA Common Land Unit program. | CDL FAQ |
| Accuracy of CDL 2025 | "75.4% OVERALL CROP ACCURACY, 24.6% ERROR, 0.712 KAPPA". "The Producer's Accuracy is generally 85% to 95% correct for the major crop-specific land cover categories." | CDL FAQ |
| Internal in-season use | "The 2007 CDL product became operational in NASS delivering for the first time in-season acreage estimates". "the internal CDL acreage estimates, which most closely aligned with planted acres, are not simple pixel counting but regression estimates using NASS survey data." | CDL FAQ |
| Pixel counting | "Pixel counting is usually downward biased when compared to the official estimates." Pixel counts "should be considered raw numbers needing bias correction." | CDL FAQ |
| Double crops | Legend code 225 = "Dbl Crop WinWht/Corn"; 26 = "Dbl Crop WinWht/Soybeans". "The CDL Program is currently not equipped to monitor triple or quad cropping practices." | CDL FAQ |
| Confidence layer | 30 m national confidence layer only for 2017-2023. | CDL Release page |
| CDL in Google Earth Engine | `USDA/NASS/CDL` availability "1997-01-01 to 2025-01-01", so the newest year in the public Earth Engine catalog is **2024**, cropland band only ("The 2024 CDL only has the data band"). | Earth Engine catalog |
| Crop Sequence Boundaries (CSB) | 8-year windows; "The 2018-2025 released March 27, 2026"; algorithm on GitHub (`USDA-REE-NASS/crop-sequence-boundaries`); "does not come from producers or agencies like the Farm Service Agency". | CSB page |

**Inference:** CDL 2026 will appear around late January to late February 2027, after the January 2027 silage figure. A 2026 nowcast cannot use a current-year NASS mask, and CSB polygons carry crop history only through 2025.

**Inference (practical):** if the pipeline runs in Earth Engine, CDL 2025 has to be uploaded as an asset (or the organizer copy used); the catalog stops at 2024.

**From memory, not verified today:** other corn double-crop codes are 226 (Oats/Corn), 228 (Triticale/Corn), 237 (Barley/Corn). Check the legend; a mask that keeps only code 1 will drop California's winter-forage-then-corn fields.

### 2.2 Mapping the current year without current-year ground truth (literature)

Only abstracts / metadata could be opened for the journal papers (publisher returned HTTP 403).

| Study | Where / when | Inputs and labels | Result as stated | Opened |
|---|---|---|---|---|
| Zhang, Di et al. 2021, Int. J. Appl. Earth Obs. Geoinf. 102:102374 | 12 US Corn Belt states; 49 Landsat-8 scenes, 31 Sentinel-2 tiles | "Trusted pixels" predicted from historical CDL by a neural network label the current-year imagery; "normally 3-4 images per scene"; no field data | In-season corn and soybean maps "expected to reach 85%-95% agreement with CDL as well as field data by mid-July" | Abstract (OpenAlex record) |
| Lin, Zhong, Song, Dong, Lobell, Jin 2022, RSE 274:112994 (arXiv 2110.10275) | US Midwest corn/soybean; Northeast China rice/corn/soybean; Landsat-8 and Sentinel-2 | Transfers the *topology* (relative position of crops in a SWIR1 vs RDEG1 histogram space) from historical years to generate labels; random forest | Corn F1 0.887 "as early as the silking stage", soybean F1 0.851 at flowering, overall accuracy 0.873 in Iowa; Northeast China above 0.85 two and a half months before harvest | arXiv abstract |
| Cai et al. 2018, RSE | Champaign County, Illinois; Landsat 2000-2015; aggregated to Common Land Units; deep neural network | Multi-year training against CDL | 96% overall accuracy against CDL; 95% by late July; SWIR bands outperform visible/NIR | Abstract summary (Semantic Scholar record) |
| Konduri et al. 2020, RSE | Continental US; MODIS NDVI; cluster-then-label trained on CDL | Historical CDL | About 70% pixel-wise accuracy for eight major crops; corn and soybeans reach 90% of year-end accuracy by the end of August | Abstract summary (Semantic Scholar record) |
| Kerner et al. 2022, Science of Remote Sensing 6:100059 | Iowa 2019 (late planting), Illinois 2020; HLS + Sentinel-1; phenology-normalized inputs | Trained on other years | Accuracy 71% / 72% early season, 80% / 84% mid season, 81% / 85% late season (Iowa / Illinois) | Abstract (OpenAlex record) |
| Kerner et al. 2020, KDD Fragile Earth workshop (arXiv 2009.10189) | US Midwest 2019 | Growth-stage normalized 30 m series | 82.8% overall accuracy mid-season (July-September), 85.4% before harvest (September-November) | arXiv abstract |
| Johnson and Mueller 2021, RSE 264:112576 (NASS authors) | not opened | OpenAlex keywords: Cropland Data Layer, historical land cover, Landsat, Sentinel-2, random forest | **not opened: ScienceDirect 403, abstract withheld in OpenAlex and Semantic Scholar** | Metadata only |
| Zhong et al. | not opened | | not opened: no search available | No |

**Inference:** with zero current-year labels, corn vs other reaches roughly 85-95% agreement with CDL in the core Corn Belt by late July to August, and about 81-85% when the test year's phenology is unusual. Our mask is needed by about September 1, after that plateau. The transfer penalty is largest outside the Corn Belt (dairy regions of California, Idaho, the Northeast), which is exactly where silage concentrates, and none of the opened abstracts reports those regions.

**Inference:** the mask's error budget is not small relative to our signal. Silage is 6% of corn acres. A mask with 5-10% commission error can inject as many non-corn fields as there are silage fields. Sorghum for silage (448K acres harvested in 2025, up 46% from 2024 per the Annual Summary) is the most dangerous confuser because it is also chopped green.

### 2.3 Recipe for a 2026 corn mask in 18 hours

1. Unit = CSB 2018-2025 polygon (or the organizer field boundaries).
2. Rotation prior per polygon from the CDL history carried in CSB (corn frequency, corn last year, corn-soy alternation).
3. One classifier per region trained on **2025 imagery with CDL 2025 labels**, applied to **2026 imagery** using features aligned on a growing-degree-day or day-since-greenup axis rather than calendar date (the Kerner et al. normalization idea). July-August composites are enough.
4. Keep only "trusted" polygons (probability above a threshold) for the silage/grain step; report the share of corn acres retained.
5. Scale to official planted acres: state corn planted for 2026 is in the 2026-11-10 Crop Production report (US 96,777K acres). Apply a ratio factor per state and say so, because NASS itself states that pixel counting is biased and that its own CDL estimates are regression estimates.
6. For the 2025 backtest, state openly that using CDL 2025 as the mask is a look-ahead (it was released 2026-02-27 and was trained with full-season imagery and FSA data). If time allows, rerun one state with a 2024-history mask to measure the penalty.

## 3. (b) Early classification and the accuracy-versus-date curve

### 3.1 ELECTS (Russwurm, Courty, Emonet, Lefevre, Tuia, Tavenard; arXiv 1901.10681 v2, Dec 2022; accepted in ISPRS Journal)

- Any time-series classifier gets a second head that outputs a stopping probability.
- Loss per time step t of T: `L_CER = alpha * L_c - (1 - alpha) * R_e`, with `L_c` cross-entropy and earliness reward `R_e = yhat_t(correct class) * (T - t) / T`. This is weighted by the probability of stopping exactly at t: `D_t = d_t * prod_{i<t}(1 - d_i) + epsilon / T`. The paper uses epsilon = 10; with epsilon = 0 some runs collapsed.
- Earliness is defined as `1 - t/T`.
- Results: BreizhCrops (France, about 608K parcels) 80% overall accuracy using about 32% of the series, typical decision around June 7 (plus or minus 28 days), versus 78-80% for full-series models that decide on Dec 28. BavarianCrops 86% using about 40% of the series. Small African sets were weaker (Ghana 54% versus 61% for a random forest).
- Their Figure 5 is the presentation to copy: accuracy by day of year for **all fields** and for **fields already decided**, with a shaded band for the **number of fields decided**.
- Limitations stated by the authors: needs large annotated datasets; sensitive to class imbalance (rare classes were not predicted correctly); no spatial context.
- Code: https://github.com/marccoru/elects

**Inference for Kernel:** do not train ELECTS. Our labeled set is small and silage is the rare class, which is the stated failure mode. Take the reporting format and a simple stopping rule: a field is "decided" when the calibrated probability is at least tau or at most 1 - tau; otherwise "pending".

### 3.2 How to report the curve (proposed table, one row per as-of date)

| As-of date | Lead time to Jan release | Share of corn fields with a confirmed cut | Share decided | Silage precision / recall / false-positive rate on decided fields | Same metrics on all fields (pending counted by prior) | State acreage error (weighted absolute % vs January) | National error |
|---|---|---|---|---|---|---|---|
| Oct 1 | 14.7 weeks | | | | | | |
| Oct 15 | 12.7 weeks | | | | | | |
| Nov 1 | 10.3 weeks | | | | | | |
| Nov 14 | 8.4 weeks | | | | | | |

Two baselines belong in the same table: "always grain" and "date-only rule". Note that the judging rubric's "Response Time" can be read two ways; report both compute time per 1,000 fields and calendar lead time.

## 4. (d) Timing evidence from NASS

### 4.1 The official calendar

- Crop Production Annual Summary for the 2025 crop: **Monday 2026-01-12, 12:00 ET** (NASS release calendar; the report text says "approved on January 12, 2026").
- 2026 Crop Production dates: Jan 12, Feb 10, Mar 10, Apr 9, May 12, Jun 11, Jul 10, Aug 12, Sep 11, Oct 9, Nov 10, Dec 10. Weekly Crop Progress: Mondays 4:00 PM ET from Apr 6 through Nov 30, 2026.
- The NASS calendar file contains no 2027 events yet. **Inference:** the Annual Summary for the 2026 crop will be released about **2027-01-12** (monthly dates in 2026 fall between the 9th and the 12th). Do not present this as an announced date.
- The annual estimates "are based primarily on surveys conducted during the month of December"; the December Agricultural Survey sampled about 73,100 farm operators for the 2025 crop.
- The national weekly Crop Progress report has **no silage row**. Silage progress is published only in some state reports.

| As-of date | Days to Jan 12 | Weeks |
|---|---|---|
| Oct 1 | 103 | 14.7 |
| Oct 15 | 89 | 12.7 |
| Nov 1 | 72 | 10.3 |
| Nov 14 | 59 | 8.4 |

(The same offsets apply to the 2025 replay against 2026-01-12 and, if the inferred date holds, to 2026 against 2027-01-12.)

### 4.2 Wisconsin (885K silage acres in 2025, the largest silage state)

Corn harvested for silage, percent of silage acres, state level:

| Week ending | 2024 | 2025 | 2026 | 5-year average printed in that report |
|---|---|---|---|---|
| about Sep 14 | not opened | 22 | not opened | |
| about Sep 21-22 | 45 | 41 | not opened | 49 |
| about Sep 27-29 | 64 | 66 | 75 | 68 |
| about Oct 4-6 | 80 | cancelled | 87 | 77 |
| Oct 13 | 92 | cancelled | not opened | 83 |
| about Oct 18-20 | not opened | cancelled | row no longer printed (Oct 18) | |
| Oct 27 | row no longer printed | cancelled | | |

Corn harvested for grain, percent, Wisconsin:

| Week ending | 2024 | 2025 | 2026 |
|---|---|---|---|
| about Sep 28-29 | 5 | 4 | 4 (Sep 27) |
| about Oct 4-6 | 10 | cancelled | 8 |
| about Oct 11-13 | 26 | cancelled | 16 |
| about Oct 18-20 | 44 | cancelled | 24 |
| Oct 27 | 65 | cancelled | |
| Nov 1 | | cancelled | 61 |
| Nov 8 | | cancelled | 72 |
| about Nov 16-17 | 93 | 86 | |

Other details from the same reports: grain moisture at harvest was 21% (Oct 13, 2024), 17% (Oct 27, 2024), 18% (Nov 16, 2025), 20% (Oct 18, 2026). On Sep 28, 2025 corn was 93% dented and 49% mature. The Sep 29, 2025 narrative notes "Cover crops were planted into the harvested silage fields and manure application was ongoing."

Wisconsin also prints the silage row for **nine agricultural districts**. Week ending Sep 28, 2025: NW 62, NC 28, NE 53, WC 62, C 58, EC 68, SW 89, SC 93, SE 75. The spread between south-central (93%) and north-central (28%) in the same week is 65 points.

**Inference (linear interpolation between weekly values):** Wisconsin silage was 50% harvested about Sep 24 in 2024 and about Sep 23-24 in 2025, and 90% harvested about Oct 12 in 2024. In 2026 it was already 87% on Oct 4.

### 4.3 Minnesota and New York, 2024

| State | Week ending | Silage harvested | 5-year average | Grain harvested | Corn mature |
|---|---|---|---|---|---|
| Minnesota | Oct 6, 2024 | 92 | | 15 | 82 |
| Minnesota | Oct 13, 2024 | 98 | 94 | 43 | 94 |
| New York | Oct 6, 2024 | 60 | | 8 | 39 |
| New York | Oct 13, 2024 | 73 | 64 | 11 | 50 |
| New York | Oct 20, 2024 | 83 | | 19 | 64 |
| New York | Oct 27, 2024 | 90 | 83 | 34 | 80 |

**Inference:** New York (500K silage acres in 2025, more than its 450K grain acres) runs about two weeks behind Wisconsin. In an average year New York is only 83% done on Oct 27, so its 90% point falls in early November.

### 4.4 Grain harvest, 18 major states (national Crop Progress)

| Week ending | 18-state corn harvested | Notable states |
|---|---|---|
| Sep 28, 2025 | 18% (2024: 20%; average 19%) | **Texas 79%**, North Carolina 82%, Tennessee 69%, Kentucky 53%, Missouri 40%, Kansas 29%; Wisconsin 4%, Minnesota 5%, Michigan 7% |
| Nov 16, 2025 | 91% (2024: 98%; average 94%) | Nebraska 74%, North Dakota 80%, Pennsylvania 80%, Michigan 82%, Wisconsin 86% |
| Nov 1, 2026 | 74% | |
| Nov 8, 2026 | **81%** (average 86%; 2025 not available) | Iowa 72%, Nebraska 74%, South Dakota 68%, Wisconsin 72%, Michigan 61%, Ohio 69%, Pennsylvania 67%, Minnesota 88%, Kansas 88%, Illinois 93%, Texas 99% |

"Early is not silage" in numbers: by Sep 28, 2025 Texas had combined 79% of its grain corn while Wisconsin had combined 4%.

### 4.5 The 2025 reference gap

The Wisconsin report of 2026-10-05 carries this note: "Due to a lapse in federal funding in October and November 2025, the Crop Progress reports for the weeks ending October 5, 2025, through November 9, 2025, were canceled. Therefore, previous year estimates for the corresponding weeks will not be available. Five-year average estimates will reflect the years 2021-2025 using published estimates for 2021-2024 and imputed estimates for 2025."

Consequences:
- For the 2025 replay there is no official weekly progress between Sep 28 and Nov 16, 2025. Anchors available: Wisconsin silage 66% on Sep 28, 2025; grain 4% on Sep 28 and 86% on Nov 16, 2025.
- In the 2026 reports the "last year" column is NA for those weeks, and the 5-year averages contain imputed 2025 values.
- **Inference:** a satellite harvest tracker would have been the only public weekly signal for those six weeks. That is a factual, non-polemical value statement for a NASS audience.

### 4.6 States not covered

California, Pennsylvania, Idaho, Michigan, Texas, Iowa, South Dakota, Kansas and Nebraska state reports were **not opened** (no search; each state PDF costs two tool calls). Whether those offices publish a silage row is unverified. California's timing in particular is unverified and matters most because of double cropping.

## 5. What the timing implies (all Inference, computed from the NASS numbers above)

### 5.1 Cut date alone does not separate the classes in the overlap window

Wisconsin 2024, acres harvested during each week (silage acres 730K, grain acres 2,960K from the Annual Summary):

| Period | Silage acres cut | Grain acres cut | Silage share of acres cut |
|---|---|---|---|
| Season to Sep 29 | 467K (64%) | 148K (5%) | 76% |
| Week ending Oct 6 | 117K (16 points) | 148K (5 points) | 44% |
| Week ending Oct 13 | 88K (12 points) | 474K (16 points) | 16% |

So even in Wisconsin, 24% of the corn acres already cut by Sep 29 were grain (high-moisture corn and early fields), and a field cut in the first week of October is close to a coin flip on date alone. This supports keeping green-at-cut, dry-down days and residue as the discriminating measurements, and using date only as a prior.

### 5.2 "Still standing" is informative, and how informative depends on the state

Posterior that a still-standing corn field is silage = remaining silage acres / (remaining silage + remaining grain acres):

| State, as-of date | Silage not yet cut | Grain not yet cut | P(silage given standing) |
|---|---|---|---|
| Wisconsin, Sep 29, 2024 | 36% of 730K = 263K | 95% of 2,960K = 2,812K | 8.5% |
| Wisconsin, Oct 13, 2024 | 8% = 58K | 74% = 2,190K | 2.6% |
| Wisconsin, Sep 28, 2025 | 34% of 885K = 301K | 96% of 3,220K = 3,091K | 8.9% |
| New York, Oct 13, 2024 | 27% of 455K = 123K | 89% of 555K = 494K | 19.9% |
| New York, Oct 27, 2024 | 10% = 45K | 66% = 366K | 11.0% |

"Standing in mid-October means grain" is right 97 times in 100 in Wisconsin and wrong 1 time in 5 in New York. The rule has to be state-specific.

### 5.3 Formula for an acreage nowcast with right-censoring

For state s at as-of date t:

```
A_silage(s,t) = k_s * [ sum over cut fields ( a_i * p_i )  +  sum over standing fields ( a_i * q_i(t) ) ]

p_i    = calibrated P(silage | measurements at the cut)            (the plan-v2 model)
q_i(t) = pi_s * S_S(t) / [ pi_s * S_S(t) + (1 - pi_s - w_s) * S_G(t) + w_s ]
S_S(t) = share of silage acres not yet harvested at t   (state weekly silage progress where published; else a curve fitted to our own detected silage cuts)
S_G(t) = share of grain acres not yet harvested at t    (weekly Crop Progress, 18 states; or the 9 km gridded layer)
pi_s   = prior silage share of corn acres (last year's NASS state totals)
w_s    = share never harvested (abandoned, grazed, lost); nationally 1.3-1.8% of planted acres in 2024-2025
k_s    = NASS planted corn acres in the state / mapped corn acres (ratio calibration)
```

Optional refinement: multiply the terms in q_i by a likelihood from in-field evidence, the most useful being **days the field has been senesced and still standing** (silage is chopped before or at senescence, so a field that has been brown for two or more weeks and is still standing is grain or abandoned).

### 5.4 State-level persistence benchmark

From the Annual Summary state table (silage area harvested, 1,000 acres):

| State | 2024 | 2025 | Change |
|---|---|---|---|
| Wisconsin | 730 | 885 | +155 |
| New York | 455 | 500 | +45 |
| South Dakota | 410 | 390 | -20 |
| California | 380 | 365 | -15 |
| Minnesota | 380 | 360 | -20 |
| Michigan | 325 | 350 | +25 |
| Pennsylvania | 320 | 315 | -5 |
| Idaho | 265 | 280 | +15 |
| Texas | 160 | 265 | +105 |
| Iowa | 340 | 250 | -90 |
| Kansas | 310 | 230 | -80 |
| Nebraska | 280 | 210 | -70 |
| Ohio | 160 | 200 | +40 |
| Colorado | 200 | 200 | 0 |
| North Dakota | 260 | 170 | -90 |
| United States | 6,207 | 6,208 | +1 |

Sum of absolute state changes across all 48 listed states = 937K acres = **15.1% of the US total**, while the national net change was 0.02%. A nowcast cannot beat persistence nationally for 2025; it can and should beat 15.1% at state level. The large negative changes in Iowa, Kansas, Nebraska and North Dakota coincide with larger grain harvested area in those states in 2025, consistent with silage acreage there being partly a salvage decision.

### 5.5 Top-down accounting check for 2026

| Crop year (vintage) | Planted | Harvested for grain | Planted minus grain | Silage | Other fates |
|---|---|---|---|---|---|
| 2024 (Jan 2026 report) | 90,909 | 83,046 | 7,863 | 6,207 | 1,656 |
| 2025 (Jan 2026 report) | 98,788 | 91,258 | 7,530 | 6,208 | 1,322 |
| 2025 (as printed Nov 10, 2026) | 98,713 | 90,948 | 7,765 | 6,187 | 1,578 |
| 2026 (Nov 1 forecast, Nov 10, 2026) | 96,777 | 88,506 | 8,271 | blank | unknown |

(1,000 acres.) The non-grain residual for 2026 is 8.27M acres, 8.5% of planted, about 0.5M more than 2025. If "other fates" stay inside the 1.3-1.7M range of 2024-2025, the implied 2026 silage area is about **6.6-6.9M acres**. This is an accounting residual from NASS's own published forecasts, not an estimate, and "other fates" is not stable in dry years. It is a free reconciliation band for our bottom-up number.

## 6. (c) Real-time simulation discipline

### 6.1 Data latency (verified statements)

| Source | What the source shows | Note |
|---|---|---|
| HLS v2.0 (NASA LP DAAC) | "accessible to end users with two to three day latency"; "observations every 1.6 days"; Sentinel-2C included; "low-latency HLS products are anticipated to be completed in 2027"; vegetation index products introduced February 2025 | Earthdata HLS page |
| HLS in Earth Engine (`NASA/HLS/HLSS30/v002`) | Availability ends **2026-11-05** when read on 2026-11-14 | Earth Engine copy lagged about 9 days today |
| Sentinel-2 surface reflectance in Earth Engine (`COPERNICUS/S2_SR_HARMONIZED`) | Availability through 2026-11-14 13:11 UTC; nominal revisit 5 days with two satellites, "2-3 days at mid-latitudes"; SCL class 11 = snow/ice, 3 = cloud shadow, 10 = cirrus | Same-day in Earth Engine |
| Sentinel-2 constellation | Sentinel-2C replaced 2A on 2025-01-21; 2A resumed on 2025-03-13 in an extension campaign so that "the Sentinel-2 constellation consists of 3 satellites for 1 year (till 13 March 2026)" | Status after March 2026 not stated on the pages opened |
| Sentinel-1 timeliness | "Products not required in near real-time are available within 24 hours from sensing." | SentiWiki |
| Sentinel-1 GRD in Earth Engine | "The collection is updated daily. New assets are ingested within two days after they become available."; availability through 2026-11-14 12:00 UTC | |
| Sentinel-1 constellation | 12-day repeat with one satellite, 6-day with two. 1A launched 2014-04-03, end of operations planned for end of June 2026. 1B ended (announced 2022-08-03). 1C launched 2024-12-05, "fully operational since early May 2025". 1D launched 2025-11-04, to be fully operational from mid-April 2026 | SentiWiki |
| OPERA RTC-S1 | 30 m posting, distributed by ASF DAAC. **Latency not stated on the pages opened.** | Measure it |
| HLS Fmask bits | bit 1 cloud, bit 3 cloud shadow, bit 4 snow/ice | Earth Engine HLS page |
| NASS weekly Crop Progress | Monday 4:00 PM ET for the week ending Sunday | 1-day latency |

**Inference:**
- For today's nowcast inside Earth Engine, Sentinel-2 SR and Sentinel-1 GRD are current; HLS is not. Pull HLS from LP DAAC if it is needed for the last ten days.
- Radar sampling differs by year: 2022-2024 had one Sentinel-1 satellite (12-day repeat per track), 2025 had two from May, 2026 has two (C and D). A 2024 replay has half the radar density of 2025-2026. Optical sampling may be lower in 2026 than in 2025 if Sentinel-2A stopped in March 2026. Record "days between last clear scene and the cut" as a quality feature so that green-at-cut is not silently biased by gap length.

### 6.2 As-of protocol (recipe)

1. Fix the as-of dates: 2025-10-01, 2025-10-15, 2025-11-01, 2025-11-14.
2. For each source use only acquisitions with `acquisition_date <= as_of - latency`. Suggested latencies: Sentinel-1 GRD 2 days, Sentinel-2 L2A 1 day, HLS 3 days, OPERA RTC 3 days (unverified), NASS weekly progress = last Monday at or before as-of.
3. Every transformation must be causal:
   - no smoothing, harmonic fit or gap filling that uses observations after the as-of date;
   - a cut is "confirmed" only with the number of post-cut observations the detector really needs; with a 6-day radar repeat a cut is typically confirmed 6-12 days later, so an Oct 15 run sees cuts through roughly Oct 3-9;
   - any relative feature (county median cut date, percentile ranks) is recomputed from data available at as-of. Note that the county median of fields already cut is biased early in the season because silage is cut first; a growing-degree-day clock is causal and stable, a mid-season county median is not;
   - thresholds and hyperparameters are frozen before the replay, not tuned on the full season.
4. Things that leak the future if used in the replay: CDL 2025 (released 2026-02-27), CSB 2018-2025 (released 2026-03-27), any label-derived statistic, January 2026 state totals (use them only as the target; the prior is the 2024 state totals).
5. The archive is not what was available in real time (reprocessed baselines, final orbits). Say so; it makes the replay slightly optimistic.
6. In 2026, measure real latency instead of assuming it: compare each asset's acquisition time with its Earth Engine ingestion time.
7. Name the target vintage: the Jan 12, 2026 Annual Summary (US silage 6,208K acres). The same 2025 figure reads 6,187K in the Nov 10, 2026 Crop Production report.

## 7. (e) How official statistics present early numbers

All quoted from the NASS Crop Production report of 2026-11-10 and the Annual Summary of 2026-01-12.

- **Forecast, then estimate, then revision.** "The November 1 production forecast will not be revised; instead, a new forecast will be made each month throughout the growing season. End-of-season estimates are made after harvest." "End-of-season estimates for all other row crops are published in the Annual Crop Production Summary in January." Annual estimates "may be revised the following year, if new information is available that would justify a change" and are reviewed again after the 5-year Census of Agriculture; "No revisions will be made after that date."
- **Remote sensing already has a defined role.** The Agricultural Statistics Board "reviews multiple data sources at the National and State level, including USDA administrative acreage data, satellite imagery, and objective yield and grower reported data." "Revisions to planted acres will only be made when either special survey data, administrative data, such as Farm Service Agency certified acreage data, or remote sensing data are available."
- **Reliability is stated as a track record, not as a model standard error.** "the 'Root Mean Square Error' for the November 1 corn for grain production forecast is 1.3 percent. This means that chances are 2 out of 3 that the current production forecast will not be above or below the final estimate by more than 1.3 percent. Chances are 9 out of 10 (90 percent confidence level) that the difference will not exceed 2.3 percent." Over 20 years the difference averaged 144 million bushels, ranging from 4 to 420 million; the forecast was below final 7 times and above 13 times.
- **Survey error is also stated.** National relative standard error about 1.3% for corn production; the December survey sampled about 73,100 operators.
- **Vintages are real.** 2025 corn as first published on 2026-01-12: planted 98,788K, grain 91,258K, silage 6,208K acres. As printed on 2026-11-10: 98,713K, 90,948K, 6,187K. The silage revision is -21K acres (-0.34%).

**Inference, how to present ours:** copy the form. "Our Oct 15 estimate of state silage acres, replayed on 2025, differed from the January figure by X% (weighted absolute error over N states); the estimate was above the January figure in A states and below in B." With one replay year the honest spread is across states, not across years; say that explicitly instead of quoting a confidence interval we cannot support. Publish each as-of estimate as a dated vintage and never overwrite it.

Not opened: Statistics Canada's model-based crop estimates (HTTP 503), Eurostat or BEA revision policies. They are not cited.

## 8. (f) Nowcast-specific risks

| Risk | Evidence | What to do |
|---|---|---|
| Fields not yet harvested at as-of (right-censoring) | 19% of grain corn unharvested in 18 states on Nov 8, 2026; Iowa 28%, South Dakota 32%, Michigan 39%. On Nov 16, 2025 Nebraska was still at 74% | Three field states: cut and silage-like, cut and grain-like, standing. Standing fields get the hazard prior of section 5.3. Report the standing share next to every estimate |
| Late-chopped silage | New York had 10% of silage unharvested on Oct 27, 2024; its 5-year average on that date is 83% harvested | State-specific survival curves; do not hard-code "after Oct 20 means grain" |
| Early grain | 5% of Wisconsin grain corn was harvested by Sep 29, 2024; Texas 79% by Sep 28, 2025 | Date is a prior, never the classifier |
| Detection lag | 6-day radar repeat plus confirmation plus 1-2 days of data latency | Publish the "cuts visible through" date with each estimate |
| Snow and frost | First hard frost reported in Wisconsin in the week ending Oct 18, 2026; snow flags exist in HLS Fmask (bit 4) and Sentinel-2 SCL (class 11) | Mask snow scenes for residue indices; take residue from the first snow-free clear scene after the cut; rely on radar for the date |
| Missing reference data | Crop Progress cancelled for weeks ending Oct 5 through Nov 9, 2025 | Validate the 2025 replay on Sep 28 and Nov 16 anchors and on 2024 curves |
| Mask look-ahead | CDL 2025 released 2026-02-27 | Disclose; one-state sensitivity run |
| Non-grain, non-silage fates | 1.3-1.7M acres nationally in 2024-2025 | A standing field in January is not grain; keep an "other / never harvested" bucket |
| Changing satellite constellations | Sentinel-1: one satellite 2022-2024, two from May 2025; Sentinel-2: three satellites until at least March 2026 | Gap-length feature; do not pool 2024 with 2025-2026 without it |

How to state the remaining uncertainty on Nov 14: "X% of corn acres had a confirmed cut and were classified from measurements; Y% were still standing and were allocated by the state harvest-progress prior; if every standing field were grain the estimate would be A, if standing fields followed last year's silage share it would be B." That bracket is honest, simple, and needs no distributional assumption.

## 9. New public signals worth using (candidates for the innovation criterion)

1. **Weekly district-level silage harvest progress (Wisconsin, nine districts)** and state-level silage rows (Wisconsin, Minnesota, New York verified). This is an independent, official time series against which our satellite-detected silage cut dates can be validated week by week. URL pattern: `https://nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2025/WI-Crop-Progress-09-29-25.pdf` (index page lists every week).
2. **NASS Crop Progress and Condition Gridded Layers.** 9 km weekly GeoTIFFs, 2015 to present, including `cpc2026.zip`. Corn index = (Harvested + Mature + Dented + Doughing + Silking + Emerged + Planted) / 700, from 0 (0% planted) to 1 (100% harvested). "Fully synthetic representations of confidential, NASS county level survey data" from about 3,600 respondents. Excludes Arizona, California, Florida and Nevada. **Inference:** this gives a sub-state official clock for maturity and grain harvest (a local S_G(t)); once every earlier stage is complete the harvested share is roughly 7 x index - 6, but the index mixes "mature" and "harvested", so treat it as a timing covariate. Weeks cancelled in 2025 are presumably missing (not checked).
3. **Grain moisture at harvest** printed weekly in the Wisconsin and Minnesota reports (17-21% in the weeks read), a public anchor for the dry-down story.
4. **The planted-minus-grain residual** from each monthly Crop Production report as a top-down band (section 5.5).

Unverified leads (pages would not open): FSA Crop Acreage Data (county planted acres by crop released monthly from August; the page timed out three times, so whether it separates grain and silage intent is unknown); RMA Summary of Business silage-type insured acres.

## 10. What this means for Kernel

1. **Reframe the deliverable as a dated nowcast with vintages:** Oct 1, Oct 15, Nov 1, Nov 14, each with lead time in weeks, share of fields decided, and error against the January figure. That one table answers Technical Quality, Mission Alignment and the "value" half of Presentation.
2. **Add a "standing" state to the plan-v2 rule.** Plan v2 assumes every field has a cut date. On Nov 8, 2026 about a fifth of grain corn did not. Standing fields are classified by the survival prior plus "days senesced and still standing"; this turns the censoring problem into evidence.
3. **Replace "cut date relative to the county median" with a causal clock.** The mid-season county median of already-cut fields is biased toward silage dates. Use growing-degree-days to expected maturity, and optionally NASS weekly progress for the state or the 9 km grid.
4. **Keep the non-date measurements; the data justify them.** In Wisconsin's first week of October 2024, 44% of the acres cut were silage and 56% grain. Green-at-cut, dry-down days and residue carry the decision there.
5. **Make priors and thresholds state-specific.** New York is two weeks later than Wisconsin; Texas grain is combined before Wisconsin silage is chopped.
6. **Show skill where it exists.** National persistence was exact in 2025. Report weighted absolute state error against the 15.1% persistence benchmark, and list Wisconsin (+155K), Texas (+105K), Iowa (-90K), North Dakota (-90K) as the states where a nowcast would have mattered.
7. **Be explicit about the mask.** Say "CDL 2025 for the replay (a known look-ahead), prior-year-trained mask plus rotation history for 2026, scaled to NASS planted acres". Include sorghum silage as a named confuser. In Earth Engine, upload CDL 2025.
8. **Speak NASS's language in the pitch.** "Forecast", "estimate", "revision", "chances are 2 out of 3", a dated vintage, the target vintage named. Offer the nowcast as an additional indication for the Agricultural Statistics Board, which already reviews satellite imagery and administrative data, not as a replacement for the December survey.
9. **One sentence that lands:** in 2025 the weekly progress survey could not be run for six weeks in October and November; the satellites kept recording.
10. **Sanity band for the 2026 number:** NASS's own November figures leave 8.27M planted acres not going to grain; with 1.3-1.7M in other fates that implies roughly 6.6-6.9M silage acres. If our bottom-up 2026 number is far outside, explain why before a judge asks.

## 11. Annotated bibliography (every URL below was opened unless marked)

NASS primary data
- Crop Production 2025 Summary (January 2026), text version. US and state corn planted, harvested for grain, silage; methodology; revision policy. https://release.nass.usda.gov/reports/cropan26.txt
- Crop Production, November 10, 2026. 2026 planted and grain forecast, blank 2026 silage cell, revised 2025 values, reliability table, revision policy. https://release.nass.usda.gov/reports/crop1126.txt
- Crop Progress, released 2026-11-09 (week ending Nov 8, 2026). https://release.nass.usda.gov/reports/prog4526.txt
- Crop Progress, released 2025-11-17 (week ending Nov 16, 2025). https://release.nass.usda.gov/reports/prog4625.txt
- Crop Progress, released 2025-09-29 (week ending Sep 28, 2025). https://release.nass.usda.gov/reports/prog3925.txt
- NASS release calendar (November 2026 view; January 2026 view; .ics file with 2026 events only). https://www.nass.usda.gov/data-and-statistics/calendar/release-calendar and https://www.nass.usda.gov/data-and-statistics/calendar/release-calendar.ics
- Release page for the Annual Summary of 2026-01-12. https://www.nass.usda.gov/data-and-statistics/calendar/release/6219
- Reports by release day (2026 dates). https://www.nass.usda.gov/publications/reports-by-release-day
- Wisconsin Crop Progress and Condition index. https://www.nass.usda.gov/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/index.php
- Wisconsin weekly reports read: 2025-09-22, 2025-09-29, 2025-11-18, 2024-10-15, 2024-10-28, 2026-10-05, 2026-10-19 (pattern `.../Wisconsin/Publications/Crop_Progress_&_Condition/<year>/WI-Crop-Progress-<MM-DD-YY>.pdf` under https://nass.usda.gov/sites/default/files/Statistics_by_State/).
- Minnesota weekly report 2024-10-15. https://nass.usda.gov/sites/default/files/Statistics_by_State/Minnesota/Publications/Crop_Progress_&_Condition/2024/MN-Crop-Progress-10-15-24.pdf
- New York weekly reports for weeks ending 2024-10-13 and 2024-10-27. https://www.nass.usda.gov/sites/default/files/Statistics_by_State/New_York/Publications/Crop_Progress_&_Condition/2024/NYCW_1013.pdf and `.../NYCW_1028.pdf`

NASS geospatial products
- CDL FAQ. https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php
- CDL release and download page. https://www.nass.usda.gov/Research_and_Science/Cropland/Release/index.php
- CDL program page. https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php
- Crop Sequence Boundaries. https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php
- Crop Progress and Condition Gridded Layers, index and metadata. https://www.nass.usda.gov/Research_and_Science/Crop_Progress_Gridded_Layers/index.php and https://www.nass.usda.gov/research-and-science/crop-progress-gridded-layers/metadata/metadata-cropprogress

Satellite data latency and constellations
- HLS project page. https://www.earthdata.nasa.gov/data/projects/hls
- Sentinel-1 mission (SentiWiki). https://sentiwiki.copernicus.eu/web/s1-mission
- Sentinel-2 mission (SentiWiki). https://sentiwiki.copernicus.eu/web/s2-mission
- Copernicus Data Space documentation, Sentinel-1 and Sentinel-2. https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel1.html and `.../Sentinel2.html`
- Earth Engine catalog: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD , https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED , https://developers.google.com/earth-engine/datasets/catalog/NASA_HLS_HLSS30_v002 , https://developers.google.com/earth-engine/datasets/catalog/USDA_NASS_CDL
- OPERA RTC-S1 product page (posting and distribution only). https://www.jpl.nasa.gov/go/opera/products/rtc-product/

Papers
- Russwurm et al., ELECTS. https://arxiv.org/abs/1901.10681 (details read in the HTML rendering https://ar5iv.labs.arxiv.org/html/1901.10681)
- Lin et al. 2022. https://arxiv.org/abs/2110.10275 (journal record https://api.openalex.org/works/doi:10.1016/j.rse.2022.112994)
- Kerner et al. 2022. Abstract via https://api.openalex.org/works/doi:10.1016/j.srs.2022.100059 ; workshop precursor https://arxiv.org/abs/2009.10189
- Zhang et al. 2021. Abstract via https://api.openalex.org/works/doi:10.1016/j.jag.2021.102374
- Cai et al. 2018 and Konduri et al. 2020. Abstract summaries via Semantic Scholar records for DOI 10.1016/j.rse.2018.02.045 and 10.1016/j.rse.2020.112048.
- Johnson and Mueller 2021, DOI 10.1016/j.rse.2021.112576. **Not opened** (metadata only via https://api.openalex.org/works/doi:10.1016/j.rse.2021.112576).

Pages that would not open
- esmis.nal.usda.gov (DNS failure); sciencedirect.com (403) for Johnson and Mueller, Lin, Kerner; ui.adsabs.harvard.edu (405); usda.gov WASDE schedule (403); fsa.usda.gov crop acreage data (timeout, three attempts); statcan.gc.ca (503); a guessed Minnesota 2025 report URL (404).

## 12. Open questions

1. Is there any public 2026 in-season US crop-type map (academic or commercial)? Not searchable today. The NASS answer is no.
2. Exact January 2027 release date of the Annual Summary (expected about Jan 12; not on the calendar yet).
3. California silage harvest timing and whether the state report prints a silage row; same for Pennsylvania, Idaho, Michigan, Texas, Iowa, South Dakota, Kansas, Nebraska.
4. Did Sentinel-2A keep acquiring after March 2026, and what is the real OPERA RTC-S1 latency? Both are measurable from the archives in a few minutes.
5. What do Johnson and Mueller (NASS) report for corn accuracy by month? Someone with journal access should read it before the pitch; it is the NASS authors' own answer to the mask question.
