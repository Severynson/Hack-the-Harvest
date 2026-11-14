# Direct precedent: separating silage maize from grain maize by remote sensing

Team Kernel, Hack the Harvest. Research pass of Saturday 2026-11-14. Topic: every study, thesis, report or operational product that separates silage (forage, whole-plant) maize from grain maize, or maps silage maize specifically, with satellite or aerial data, 2005-2026.

## 0. Bottom line

1. **Direct precedent is thin.** We found exactly one peer-reviewed study whose purpose is silage versus grain maize separation from satellites: Lin et al. 2025 ("TempDiff-SMID", Hohhot, Inner Mongolia). It is a three-condition Sentinel-2 rule; the deciding condition is a fixed calendar threshold, September LSWI <= 0.15 ("the field is already bare and dry in September").
2. **Its headline accuracy is optimistic.** F1 for silage 0.93 on 381 points in a roughly balanced sample, evaluated on the same points the thresholds were tuned on (our inference from the arithmetic, section 3.1). In other years the thresholds had to be re-tuned by hand and silage F1 still fell to 0.82-0.89.
3. **The best-resourced national attempt reported the split as highly uncertain.** Germany's national crop map (Thünen / HU Berlin, Sentinel-1 + Sentinel-2 + Landsat 8, parcel declarations from five states) kept silage and grain maize as separate classes and found their mutual confusion to be among the largest errors on the map; the minority maize class was over-estimated in every state.
4. **Nobody has used radar, a dry-down duration, residue, growing-degree-day timing or dairy context for this split.** All of these are unstudied as silage-versus-grain discriminators in everything we opened. The physics behind "dry-down days" is documented (Meroni et al. 2021: for maize the Sentinel-1 end of season lags the NDVI end of season by 18.6 days on average and coincides with harvest), but it is noisy (mean absolute difference 25.5 days) and has never been used as a classifier feature.
5. **No US study and no agency product was found.** USDA NASS CDL, AAFC's Annual Crop Inventory and the JRC EU crop map each carry one corn/maize class. One Iranian method was tested in Tulare County, California, but it detects silage maize against other crops, not against grain maize.
6. **Coverage caveat.** The session's shared web-search budget ran out after 17 searches (English, Chinese, German, French, Dutch). Portuguese, Spanish and Italian searches, and a dedicated US-academic search, were not run. Claims of the form "nobody has done X" mean "not found in this pass".

## 1. How this pass was done

- 17 web searches completed: English (general, LPIS, biogas, NASS), Chinese (青贮玉米 遥感 识别 / 提取; 青贮玉米 籽粒玉米 区分; 粮改饲 遥感监测; GF-6 / Sentinel-2 by province), German (Silomais Körnermais Fernerkundung), French (maïs ensilage maïs grain télédétection RPG), Dutch (snijmaïs korrelmaïs satelliet BRP), plus six targeted follow-ups on the two silage-specific papers.
- Three further searches (US corn-silage mapping; AAFC / Statistics Canada; dry-down and SAR fusion) were refused because the shared search budget was exhausted. After that only direct fetches of primary sources were used.
- Primary sources were opened and read in full where the host allowed it. PDFs were converted to text locally with the macOS PDF framework (nothing installed). Section 9 lists what was and was not opened.
- "Inference:" marks our own reasoning as opposed to what a source states.

## 2. Summary table

| # | Study | Separates silage from grain? | Region, years | Sensors | Deciding signal | Silage-class accuracy | Earliest usable date |
|---|---|---|---|---|---|---|---|
| A1 | Lin et al. 2025, Agronomy 15(6):1438 (TempDiff-SMID) | Yes, main goal | Hohhot, Inner Mongolia, China; 2023, applied to 2022 and 2021 | Sentinel-2 only | September LSWI <= 0.15 after July maize conditions | 2023: UA 0.9216, PA 0.94, F1 0.9307 (OA 0.9291, kappa 0.8923). 2022: F1 0.8163. 2021: F1 0.8925 | Not tested. Rule needs the September composite; smoothing used data to 31 Oct |
| A2 | Blickensdörfer et al. 2022, RSE 269:112831 | Yes, as two of 24 classes | Germany; 2017, 2018, 2019 | Sentinel-2 + Landsat 8 (5-day), Sentinel-1 monthly, environmental layers | None isolated; random forest on full feature stack | Per-class values only in a figure. Silage among "dominant" classes with UA and PA between 68% and 96%; grain-on-silage error 2.3-2.95% of map area; merged maize UA >= 90%, PA >= 83% | End of season |
| A3 | Zhang et al. 2025, Trans. CSAM (J-CSAM) 2025(5) - not opened | Reportedly yes, as a crop class | Ulan Buh irrigation area, Inner Mongolia | Sentinel-2 NDVI series (per search summary) | NDVI "cliff" in early September | Not obtained | Not obtained |
| B1 | Salehi Shahrabi et al. 2020, IJRS 41(21):8406-8427 | No: silage maize versus other crops | Marvdasht, Abyek, Mashhad (Iran) and Tulare County, California; 2017, 2018 | Sentinel-2 NDVI | Ratio SPGH / LOS (slope from peak greenness to harvest, over season length) | Kappa 0.89 Abyek, 0.80 Marvdasht, 0.90 Mashhad, 0.80 Tulare (2017) | After harvest (needs the harvest point) |
| B2 | Ruf et al. 2021, Land 10(2):128 | No: all maize assumed silage | Trier region, western Germany; 2009, 2016 | RapidEye, one mosaic per year (late August) | Single-date spectra | Sensitivity > 0.99; specificity ~0.97 / ~0.91; kappa ~0.97 / ~0.93 (out-of-bag) | End of August |
| B3 | Di Tommaso et al. 2021, arXiv 2109.06972 (ERL) | No, but quantifies the silage effect | Grand Est, France; 2019 | GEDI lidar + Sentinel-2 | Canopy height | Removing silage from the test set raised accuracy >= 4% in all periods, ~10% in September | n/a |
| C1 | Meroni et al. 2021, RSE 253:112232 | No (maize as one crop) | EU-wide; 2018 | Sentinel-1 VH/VV and Sentinel-2 NDVI | Gap between SAR and optical end of season | Maize EOS: SAR minus NDVI = +18.6 d, MAE 25.5 d, r 0.52 (n = 541) | n/a |
| C2 | WENR "Bouwland Monitoring Service" (Groenmonitor), about 2021 | No (type taken from farmer declarations) | Netherlands; trial 2018-2020 | Sentinel-2 / Landsat 8 NDVI + Sentinel-1 coherence | NDVI fall to ~0.2 with coherence rise | No statistics published | Bi-weekly in season |
| C3 | Shang et al. 2020, Remote Sens. 12(10):1551 (AAFC) | No | Temiskaming Shores, Ontario; 2019 | Sentinel-1 InSAR coherence + VH | Coherence rise > 0.05 with VH drop | Harvest window correct 56% (n = 77); 88% within +-1 cycle (12 d) | In season, 12-day lag |
| C4 | Khabbazan et al. 2019, Remote Sens. 11(16):1887 | No | Flevopolder, Netherlands; 2017 | Sentinel-1 | VH drop and coherence jump at harvest | Qualitative | In season |
| C5 | Holtgrave et al. 2020, Remote Sens. 12(18):2919 (Thünen) | No (maize = maize + biogas + silage maize codes) | Lower Saxony, Germany; 2018 | Sentinel-1 and Sentinel-2 | Correlation of SAR with optical indices | r(VH, NDVI) 0.72 season, 0.81 senescence | n/a |
| D | Agency maps: NASS CDL 2025, AAFC ACI, JRC EU crop map 2018 | No: one corn / maize class each | US, Canada, EU | various | - | CDL corn PA 92.2%, UA 91.2%; JRC maize PA 84.0%, UA 58.5% | - |

UA = user's accuracy (precision). PA = producer's accuracy (recall).

## 3. Annotated bibliography

### 3.1 A1. Lin et al. 2025 - TempDiff-SMID (the only dedicated study)

- **Citation.** Lin, Z.; Huang, R.; Tan, S.; Yang, L.; Huang, J.; Su, L.; Hu, Z. "Silage Maize Identification Using a Temporal Difference-Based Model with Sentinel-2 Data: Insights from a Harvest-Based and Temporally Transferable Approach." Agronomy 2025, 15, 1438. Published 12 June 2025. DOI https://doi.org/10.3390/agronomy15061438
- **Opened.** Full text PDF: https://mdpi-res.com/d_attachment/agronomy/agronomy-15-01438/article_deploy/agronomy-15-01438.pdf?version=1749740666 (the landing page https://www.mdpi.com/2073-4395/15/6/1438 returns HTTP 403 to our fetcher).
- **Lead check.** The lead "TempDiff-SMID, Lin et al. 2025, Agronomy" is confirmed.
- **Region and years.** Hohhot City, Inner Mongolia, 17,200 km2. Model built for 2023, then applied to 2022 and 2021. Single annual crop; maize sown late April to early May.
- **Agronomy stated by the authors.** Silage maize: about 116 days, harvested at late milk to early dough stage, mid-August to early September; "fully harvested by 10 September 2023". Grain maize: 120-130 days, harvested late September to early October. The authors call this "a 5-15 day difference in harvest windows". Regional statistics quoted: 2024 maize area 3.8159 million mu (about 254,393 ha), of which silage 1.226 million mu (about 81,733 ha), so silage is about one third of maize there.
- **Sensors and preprocessing.** Sentinel-2 only (GEE `COPERNICUS/S2_HARMONIZED`), 1 April to 31 October 2023, cloud-masked, NDVI and LSWI reconstructed at 15-day intervals with a Whittaker smoother (smoothing parameter not reported), 10 m. A DEM supplies elevation.
- **Indices.** NDVI = (NIR - Red) / (NIR + Red). LSWI = (NIR - SWIR) / (NIR + SWIR). The paper does not name the SWIR band; its false-colour composites use "NIR-SWIR1-Red". Inference: Sentinel-2 B8 and B11, which makes LSWI identical to NDMI.
- **Decision rules (their Table 2 and Table 3).** Subscripts are months.
  - Condition 1: NDVI_5 <= 0.2 and NDVI_7 >= 0.2 and elevation < 1200 m (bare after planting in May, green in July, not highland).
  - Condition 2: LSWI_7 >= 0.16 (moist canopy at heading; removes drought-adapted vegetation).
  - Condition 3: LSWI_9 <= 0.15 ("after silage maize is harvested ... the cultivated land becomes bare land with lower moisture content").
  - Silage = C1 and C2 and C3. Grain = C1 and C2 and not C3. Everything else = non-maize.
- **Feature ranking.** Random-forest Gini importance: LSWI > NDVI > RENDVI > EVI. The moisture index ranked above greenness and above the red-edge index.
- **Labels.** 100 silage, 131 grain, 150 non-maize points from field surveys with the Hohhot agro-meteorological stations plus visual interpretation of false-colour time series.
- **Accuracy, 2023 (their Table 5).**

| Class | UA | PA | F1 |
|---|---|---|---|
| Silage maize | 0.9216 | 0.9400 | 0.9307 |
| Grain maize | 0.9219 | 0.9008 | 0.9112 |
| Non-maize | 0.9404 | 0.9467 | 0.9435 |
| Overall | OA 0.9291 | kappa 0.8923 | |

- **Random-forest baseline "SMRF" (their Table 4).** Sentinel-2 L1C median composites for five phases (10 Jun-10 Jul, 10 Jul-10 Aug, 10 Aug-10 Sep, 10 Sep-10 Oct, 10 Oct-10 Nov), 13 bands x 5 = 65 features, 70/30 split. OA 0.9043, kappa 0.8511. Silage UA 0.9231, PA 0.8571, F1 0.8889. Grain UA 0.8571, PA 0.9796, F1 0.9143.
- **Transfer across years (their Table 6), "by adaptively adjusting decision thresholds".** The adjusted threshold values are not reported.

| Year | OA | Kappa | Silage UA | Silage PA | Silage F1 | Grain UA | Grain PA | Grain F1 |
|---|---|---|---|---|---|---|---|---|
| 2023 | 0.9291 | 0.8923 | 0.9216 | 0.9400 | 0.9307 | 0.9219 | 0.9008 | 0.9112 |
| 2022 | 0.8621 | 0.7905 | 0.8064 | 0.8264 | 0.8163 | 0.8625 | 0.8466 | 0.8545 |
| 2021 | 0.8816 | 0.8192 | 0.9000 | 0.8852 | 0.8925 | 0.9338 | 0.7790 | 0.8494 |

- **Earliest date.** Not analysed. The deciding rule uses the September value of a series smoothed over 1 April to 31 October. Inference: an operational version could decide in the second half of September in that region, but the paper does not show accuracy for a truncated series.
- **Stated limitations.** Threshold optimisation "relies on empirical adjustments, limiting scalability"; the rule design "imposes certain limitations on automation and cross-regional applicability, particularly in cases where phenological variations occur across years or regions"; a single optical source may fail under heavy cloud; mixed pixels and within-field heterogeneity; Sentinel-1 fusion and automatic change-point detection are proposed as future work; "there are no existing silage maize classification products available for direct comparison".
- **Stated difficulty.** "Similar growth characteristics of silage maize and grain maize, particularly their overlapping growth stages, pose significant challenges for remote sensing-based classification and mapping, unlike the distinct separability typically observed between different crop types." Also: "the narrow harvest window between the two maize varieties complicates field surveys".
- **Our reading (Inference).**
  - The 2023 accuracy is in-sample. The reported values reproduce exactly as 94/100, 118/131 and 142/150 correct (PA) with 102, 128 and 151 predicted (UA), total 354/381 = 0.9291. All 381 points were therefore used for the rule's validation, and the thresholds were set "after iterative threshold optimization" on the same region's samples. No independent test set is described.
  - The comparison with the random forest is not like for like: the forest's figures fit a held-out set of about 115 points (104/115 = 0.9043).
  - The sample is close to balanced (100 silage : 131 grain). Eight of the 102 points called silage were wrong. If all eight were grain, the grain-to-silage false positive rate is 8/131 = 6.1%; at the US prior (about 6% silage among corn acres) a recall of 0.94 with a 6.1% false positive rate gives a precision of about 0.50.
  - Condition 3 is a calendar test of whether the field is already cut. It contains no measure of how green the crop was when cut. It is exactly the "early is not silage" trap in any region where grain is harvested early.
  - A harvest gap of 5-15 days is far shorter than the US Midwest gap. In Hohhot grain maize is itself harvested by early October, which is why one September threshold works there and needs re-tuning each year.

### 3.2 A2. Blickensdörfer et al. 2022 - national German crop maps with silage and grain maize as separate classes

- **Citation.** Blickensdörfer, L.; Schwieder, M.; Pflugmacher, D.; Nendel, C.; Erasmi, S.; Hostert, P. "Mapping of crop types and crop sequences with combined time series of Sentinel-1, Sentinel-2 and Landsat 8 data for Germany." Remote Sensing of Environment 269 (2022) 112831. DOI https://doi.org/10.1016/j.rse.2021.112831
- **Opened.** Full text: https://literatur.thuenen.de/digbib_extern/dn064297.pdf
- **Region and years.** Germany, 2017, 2018 (severe drought), 2019. 24 classes (23 crop classes plus small woody features).
- **Sensors and features.** Sentinel-2 and Landsat 8 images "acquired between March 1st and September 31st" (sic), interpolated to a 5-day series of six bands and three indices (NDVI, SAVI, and NDWI in its green / NIR form, not the SWIR form used elsewhere in this report), 396 features; Sentinel-1 monthly mean VV and VH composites plus RVI = 4 x VH / (VH + VV) and VH/VV, 48 features (12 months); temperature, precipitation, soil moisture and terrain layers. Inference: the text also says the 5-day series has "44 time steps between March 1st and November 30th", which is inconsistent (44 steps x 5 days is about 220 days, 1 March to early October); the optical series most likely ended around the end of September.
- **Algorithm.** Random forest (FORCE), pixel based, 1,000 training and 1,000 validation pixels per class drawn from separate parcels (equal allocation).
- **Labels.** Parcel declarations (LPIS / IACS) from five federal states (Brandenburg, Bavaria, Lower Saxony, Mecklenburg-Vorpommern, Rhineland-Palatinate). Declared area: silage maize 13,111 / 11,812 / 13,552 km2 and grain maize 2,104 / 2,089 / 2,322 km2 in 2017 / 2018 / 2019.
- **Accuracy.** Overall map accuracy 80.41 +- 0.50% (2017), 79.23 +- 0.51% (2018), 77.97 +- 0.53% (2019). Combining optical, SAR and environmental data raised overall accuracy by 6% to 10% over single-sensor models, "in which optical data outperformed SAR". Per-class UA and PA are shown only in their Figure 5 and supplement (not obtained). Text statements:
  - The seven dominant crops, including silage maize, were mapped with UA and PA between 68% and 96%.
  - "The prediction of grain maize on areas referenced as silage maize had a proportionally high class confusion (between 2.3% in 2019 and 2.95% in 2017)" of the map area, the largest single confusion mentioned.
  - "Combining the two maize classes improved the UA and PA to >= 90% and >= 83%."
  - Against agricultural statistics, grain maize was "always overestimated", in all federal states; fodder crops were under-estimated.
- **Stated conclusions.** "the high uncertainties in differentiating silage and grain maize"; "More detailed separation of e.g., maize into different production lines (grain, silage) ... remains challenging. Parcel-based analyses might have the potential to mitigate some of the remaining class confusions."
- **Earliest date.** End of season only.
- **Our reading (Inference).** Grain maize is about 2.4% of the declared area in 2017 (2,104 km2 of roughly 86,000 km2 in their Table 2) and silage maize about 15%. A grain-on-silage error of 2.3-2.95% of the map is therefore about as large as the whole true grain maize area: the minority class was probably mapped with precision near or below 50%, and roughly one fifth of silage area went to grain. Two design choices explain it: equal class allocation in training (which inflates a rare class) and a feature set that sees grain harvest only through monthly Sentinel-1 means. In the US the minority class is silage, so the mirror-image risk is over-predicting silage.

### 3.3 A3. Zhang et al. 2025 (Chinese) - not opened

- **Lead.** "基于NDVI时序特征的作物样本扩充与遥感精细识别" (crop sample expansion and fine crop identification from NDVI time-series features), Transactions of the Chinese Society for Agricultural Machinery 2025(5). URL returned by search: https://www.j-csam.org/html/2025/5/20250535.html
- **Status.** Not opened: the journal host refused or dropped the connection on four attempts. Everything below is from the search engine's summary and is unverified.
- **Search summary.** Study in the Ulan Buh irrigation area (乌兰布和灌域), Inner Mongolia, with field samples of silage maize as a separate crop. Silage maize has a growing period of about four months; NDVI starts to decline at the end of August; harvest begins in early September; NDVI then falls "like a cliff" (断崖式下降), in contrast to the gradual decline of ordinary maize.
- **Use.** Supports the "cliff versus fade" clue qualitatively. Do not cite numbers from it.

### 3.4 B1. Salehi Shahrabi et al. 2020 - automatic silage maize detection, including Tulare County, California

- **Citation.** Salehi Shahrabi, H.; Ashourloo, D.; Moeini Rad, A.; Aghighi, H.; Azadbakht, M.; Nematollahi, H. "Automatic silage maize detection based on phenological rules using Sentinel-2 time-series dataset." International Journal of Remote Sensing 41(21), 8406-8427, 2020. DOI https://doi.org/10.1080/01431161.2020.1779377
- **Opened.** Abstract only, through the OpenAlex record https://api.openalex.org/works/doi:10.1080/01431161.2020.1779377 . Publisher page not opened: HTTP 403, and the article is closed access.
- **Region and years.** Marvdasht (training), Abyek and Mashhad in Iran, and "an individual area in USA (Tulare County, California)"; 2017 and 2018.
- **Method.** Sentinel-2 NDVI profiles; Savitzky-Golay filter; linear interpolation to a continuous series; phenological parameters extracted; "the ratio of the slope from the peak greenness to the harvest (SPGH) to the length of the growing season (LOS) was suggested as an appropriate variable for automatic maize detection". No training samples needed at the test sites.
- **Accuracy.** Kappa 0.89 (Abyek), 0.80 (Marvdasht), 0.90 (Mashhad), 0.80 (Tulare) in 2017; "the performance of the second year (2018) is close to those of 2017". A support vector machine "with a large number of training samples" was "analogous" in accuracy; maximum likelihood was worse. Lin et al. 2025 add, second hand, that overall accuracies exceeded 0.90.
- **What it is not.** The classes are silage maize versus other crops. The abstract does not mention grain maize. Inference: in these regions maize is essentially all silage, so the rule detects "maize that is chopped green", which is the same physical signature we want, but it was never asked to reject grain maize.
- **Why it matters.** It is a published, label-free, one-number version of the USDA clue "silage falls off a cliff", normalised by season length, and it transferred from Iran to a California dairy county at kappa 0.80.
- **Not available.** Threshold values, the Tulare reference data, UA / PA.
- **Note.** Lin et al. 2025 expand SPGH as "Spectral-Phenological Growth Height"; the original abstract defines it as the slope from peak greenness to harvest.

### 3.5 B2. Ruf et al. 2021 - "silage maize identification" by regional assumption

- **Citation.** Ruf, T.; Gilcher, M.; Udelhoven, T.; Emmerling, C. "Implications of Bioenergy Cropping for Soil: Remote Sensing Identification of Silage Maize Cultivation and Risk Assessment Concerning Soil Erosion and Compaction." Land 2021, 10(2), 128. DOI https://doi.org/10.3390/land10020128
- **Opened.** Full text: https://mdpi-res.com/d_attachment/land/land-10-00128/article_deploy/land-10-00128.pdf?version=1612158011
- **Method.** Binary maize versus non-maize on two RapidEye mosaics (2009, 2016) with a random forest (R `ranger`), reference polygons digitised from Google Earth imagery. Acquisition limited to the end of August because "after August, there is the potential of early harvests". "Grain maize is not cultivated in the study area", so all maize is taken as silage.
- **Accuracy.** Sensitivity > 0.99 both years; specificity about 0.97 (2009) and 0.91 (2016); out-of-bag kappa about 0.97 and 0.93.
- **Area against statistics.** Mapped 7,305 ha (2009) and 8,447 ha (2016); official statistics 9,147 ha and 11,496 ha; differences -20.1% and -26.5%. The authors attribute the gap to pixel-based mapping excluding headlands, wildlife damage and patchy emergence.
- **Use.** An example that a classifier with kappa above 0.9 still missed official area by a fifth to a quarter.
- **Lead check.** The lead "biogas maize mapping in Germany" resolves to this study and to a Weser-Ems Landsat study (Science of the Total Environment 2025, https://www.sciencedirect.com/science/article/pii/S0048969725023071 , not opened). Neither separates silage or biogas maize from grain maize.

### 3.6 B3. Di Tommaso, Wang and Lobell 2021 - silage maize breaks a height-based maize mapper in France

- **Citation.** Di Tommaso, S.; Wang, S.; Lobell, D. B. "Combining GEDI and Sentinel-2 for wall-to-wall mapping of tall and short crops." arXiv:2109.06972 (10 Sep 2021), published in Environmental Research Letters.
- **Opened.** Full text: https://arxiv.org/pdf/2109.06972
- **Setting.** Grand Est, France, 2019; labels from the Registre Parcellaire Graphique (851,090 plots in the region); binary maize versus other crops; also Iowa and Jilin.
- **Finding.** "Local GEDI accuracies in France are overall lower than the other two regions. This appears to arise mainly from the fact that two kinds of maize are grown in France, maize for grain and for silage ... Whereas grain maize is always grown to maturity, and thus has a more reliable seasonality, silage maize is grown for biomass and thus can be sown and harvested at any point in the season." Omitting silage maize from the test set improved accuracy "by 4% or more in all periods", with "September improving 10% most likely due to early harvest of silage maize".
- **Use.** Independent evidence that silage timing is variable and that the canopy disappears early. Inference: loss of canopy height in September is a candidate signal in principle, but GEDI is a sparse sampler and not a field-level tool.

### 3.7 C1. Meroni et al. 2021 - the optical end of season precedes the radar end of season for maize

- **Citation.** Meroni, M.; d'Andrimont, R.; Vrieling, A.; Fasbender, D.; Lemoine, G.; Rembold, F.; Seguini, L.; Verhegghen, A. "Comparing land surface phenology of major European crops as derived from SAR and multispectral data of Sentinel-1 and -2." Remote Sensing of Environment 253 (2021) 112232. DOI https://doi.org/10.1016/j.rse.2020.112232
- **Opened.** Full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC7841528/
- **Setting.** EU-wide, 2018 LUCAS Copernicus polygons, satellite data 1 Aug 2017 to 31 Mar 2019. Maize is one crop (LUCAS B16); grain and silage are not distinguished. 562 maize polygons, 541 with retrievals from both sensors.
- **Method.** Same double hyperbolic tangent model fitted to Sentinel-2 NDVI and to the Sentinel-1 cross ratio CR = VH / VV. SOS50 and EOS50 are the dates at 50% of the green-up and decay amplitudes.
- **Maize results (their Table 3; difference = CR minus NDVI).**

| Metric | r | Mean absolute difference | Mean difference |
|---|---|---|---|
| Start of season (SOS50) | 0.57 | 12.0 days | -0.6 days |
| End of season (EOS50) | 0.52 | 25.5 days | +18.6 days |

- **Ground check, Germany (DWD phenology).** "Both NDVI- and CR-derived EOS50 correspond to late season BBCH stage, 99 (harvest) for CR, and 83 (ripening) for NDVI." Mean offsets in their Table 4: 6.5 days between NDVI EOS50 and BBCH 83, and -1.2 days between CR EOS50 and BBCH 99 (435 ground observations of BBCH 83, 623 of BBCH 99; 65 and 68 satellite polygons).
- **Authors' interpretation.** NDVI falls first because chlorophyll "reduces earlier during ripening"; CR "is more sensitive to vegetation structure and hence declines later when the crop gets harvested". They also note that NDVI drops sharply for crops "harvested when still relatively green (e.g. maize)" while CR "may still respond to crop residues standing in the field such as maize stubble".
- **Limitations stated.** Sentinel-2 top-of-atmosphere data; 2018 was a drought year; DWD stations are within 5 km of the polygons, not on them; single-peak model.
- **Use.** This is the closest published thing to our "dry-down days": an optical browning date and a radar harvest date for the same maize field, with the gap quantified. Inference: BBCH 83 (early dough) is the stage at which silage is chopped, so for silage the two dates should coincide, and for grain they should be weeks apart. The 25.5-day mean absolute difference between two independently fitted curves is the warning: the gap is noisy at field level.

### 3.8 C2. WENR "Bouwland Monitoring Service" (Groenmonitor) - operational maize harvest dating in the Netherlands

- **Source.** Wageningen Environmental Research, "Bouwland Monitoring Service" brochure (Meijninger and Roerink), about 2021. Opened: https://www.groenmonitor.nl/api/file/186
- **Content.** About 250,000 arable parcels on 800,000 ha; maize about 208,000 ha in 2019. NDVI from Sentinel-2A/2B and Landsat 8 (cross-calibrated, cloud-screened with a manual check, pure pixels inside a parcel buffer). Since 2020 Sentinel-1 coherence between consecutive acquisitions (0 = complete change, 1 = no change). "Radar-coherentie en NDVI vullen elkaar goed aan": bare soil has high coherence and low NDVI; a closed crop has NDVI about 0.9 and coherence about 0.2; harvest is called when NDVI reaches about 0.2 and coherence rises quickly.
- **Maize.** Cumulative harvest curves and maps for "snijmais" (silage maize) for 2018, 2019 and 2020. The dry year 2018 shows an exceptionally early harvest. From 1 January 2019 a catch crop must be sown or undersown before 1 October after maize on sand and loess soils; the brochure says this is visible in the 2020 harvest map.
- **What it is not.** No accuracy statistics. No discrimination of silage from grain maize: the crop comes from the parcel registration (BRP).
- **Use.** Operational precedent for fusing an optical index with radar coherence to date maize harvest per parcel. The type call is the part nobody has automated.

### 3.9 C3. Shang et al. 2020 (AAFC) - Sentinel-1 harvest detection accuracy

- **Citation.** Shang, J.; Liu, J.; Poncos, V.; Geng, X.; Qian, B.; Chen, Q.; Dong, T.; Macdonald, D.; Martin, T.; Kovacs, J.; Walters, D. "Detection of Crop Seeding and Harvest through Analysis of Time-Series Sentinel-1 Interferometric SAR Data." Remote Sensing 2020, 12(10), 1551. DOI https://doi.org/10.3390/rs12101551
- **Opened.** Full text: https://mdpi-res.com/d_attachment/remotesensing/remotesensing-12-01551/article_deploy/remotesensing-12-01551.pdf
- **Setting.** Temiskaming Shores, northern Ontario, 2019; oats, barley, soybean, mixed grain, corn, canola, hay; 67 fields with seeding dates and 77 with harvest dates from producers and machine records; 12-day Sentinel-1 pairs.
- **Rule.** Candidate = increase in coherence > 0.05 between consecutive pairs; harvest window 1 August to end of October; accept if VH falls by more than 2 dB over the same period, or falls less than 2 dB but ends below -19 dB; otherwise move to the next candidate.
- **Accuracy.** Seeding 85% correct (57/67). Harvest 56% correct (43/77), a further 25 fields within one acquisition cycle (88% within +-12 days), 9 failures.
- **Failure modes stated.** Rain and soil moisture during harvest; "harvest with substantial amount of residue left standing in the field; in which case, there is low coherence even after harvest"; post-harvest residue removal, tillage at different times, cover crops; multi-day harvests.
- **Use.** Calibrates expectations for a radar cut date: about +-12 days, not day level.

### 3.10 C4. Khabbazan et al. 2019 - Sentinel-1 signature of maize ripening and harvest

- **Citation.** Khabbazan, S.; Vermunt, P.; Steele-Dunne, S.; Ratering Arntz, L.; Marinetti, C.; van der Valk, D.; Iannini, L.; Molijn, R.; Westerdijk, K.; van der Sande, C. "Crop Monitoring Using Sentinel-1 Data: A Case Study from The Netherlands." Remote Sensing 2019, 11(16), 1887.
- **Opened.** Full text: https://mdpi-res.com/d_attachment/remotesensing/remotesensing-11-01887/article_deploy/remotesensing-11-01887.pdf
- **Maize findings (Flevopolder 2017; ground sensors on a silage maize parcel).** During late fruit development and ripening (23 August to mid-September) VH is "relatively constant with an average of -16.2 dB" while VV rises from -9.5 to -7.5 dB, so VH/VV falls, consistent with falling vegetation water content. Harvest between mid-September and mid-October gives "abrupt decreases in backscatter ... particularly in VH". However harvest "is more difficult to detect in the autumn months" because of "elevated soil moisture". "The sudden increase in coherence is a useful indicator of harvest."

### 3.11 C5. Holtgrave et al. 2020 (Thünen) - how well radar tracks optical indices over maize

- **Citation.** Holtgrave, A.-K.; Röder, N.; Ackermann, A.; Erasmi, S.; Kleinschmit, B. "Comparing Sentinel-1 and -2 Data and Indices for Agricultural Land Use Monitoring." Remote Sensing 2020, 12(18), 2919.
- **Opened.** Full text: https://literatur.thuenen.de/digbib_extern/dn062663.pdf
- **Setting.** Lower Saxony, 2018, 22 test sites, 17,857 parcels, about 35,000 ha. The maize class "includes maize, maize for biogas, and silage maize" (IACS codes merged). Latest maize harvest in the test sites: 30 September 2018.
- **Indices (their Table 2).** NDVI = (B8 - B4) / (B8 + B4); NDWI = (B8 - B11) / (B8 + B11); PSRI = (B4 - B2) / B6.
- **Maize correlations (Pearson r).**

| Phase | NDVI vs VH | NDWI vs VH | PSRI vs VH | NDVI vs VH/VV |
|---|---|---|---|---|
| Whole season | 0.72 | 0.71 | -0.72 | 0.56 |
| Growing | 0.70 | 0.69 | -0.69 | 0.61 |
| Green | 0.73 | 0.70 | -0.76 | 0.37 |
| Senescence | 0.81 | 0.83 | -0.81 | 0.74 |

- **Use.** VH carries most of the greenness and canopy-water signal for maize during senescence, which makes it a usable stand-in when cloud hides the optical view. The authors caution the indices are not interchangeable.

### 3.12 D. Agency and benchmark products

| Product | Opened | Maize classes | Relevant numbers |
|---|---|---|---|
| USDA NASS Cropland Data Layer 2025 metadata | https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_CDL25_FGDC-STD-001-1998.htm | Corn (1), Sweet Corn (12), Pop or Orn Corn (13), double-crop classes 225, 226, 228, 237, 241. No silage class; the page does not mention silage | Corn PA 92.2%, UA 91.2%. Training and validation from FSA Common Land Unit / "578 Administrative Data". Random forest in Google Earth Engine, new for 2025. Landsat 8/9 and Sentinel-2 10-day composites |
| AAFC Annual Crop Inventory, ISO 19131 specification | https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/supportdocument_documentdesupport/en/ISO%2019131_AAFC_Annual_Crop_Inventory_Data_Product_Specifications.pdf | One class, Corn (147) | Decision tree; Sentinel-2, Landsat 8/9 and RADARSAT Constellation; target overall accuracy >= 85% at 30 m; trained on provincial crop insurance data |
| JRC EU crop map 2018 (d'Andrimont et al. 2021) | https://ar5iv.labs.arxiv.org/html/2105.09261 | One class, Maize (216, LUCAS B16) | Maize PA 84.0%, UA 58.5% against LUCAS; Sentinel-1 10-day composites 1 January to 31 July only; overall 76.1% for 19 crops |
| EuroCrops (TU Munich, DLR-funded) | https://raw.githubusercontent.com/maja601/EuroCrops/main/hcat_core/HCAT3.csv and https://github.com/maja601/EuroCrops | Two separate codes: `grain_maize_corn_popcorn` 3301010600 and `green_silo_maize` 3301090400 | Harmonised farmer declarations, CC BY-SA 4.0, version 11 on Zenodo (record 8229128). Countries in the file tree: Austria 2021, Flanders 2021, Lower Saxony and North Rhine-Westphalia 2021, Denmark 2019, Estonia 2021, Navarra 2020, France 2018, Croatia 2020, Lithuania 2021, Latvia 2021, Netherlands 2021, Portugal 2021, Romania, Sweden 2021, Slovenia 2021, Slovakia 2021 |
| ZueriCrop (Turkoglu et al. 2021) | https://ar5iv.labs.arxiv.org/html/2102.08820 | One Maize class | Not a precedent |
| Scarlat et al. 2026, EuroCrops-driven Sentinel-2 segmentation | https://arxiv.org/html/2606.00676 | One Maize class ("Corn and corn silage" merged in an external benchmark) | Not a precedent |
| Marais Sicre et al. 2016, early detection of summer crops (France) | https://mdpi-res.com/d_attachment/remotesensing/remotesensing-08-00591/article_deploy/remotesensing-08-00591.pdf | One corn class | Checked because we expected a silage class; there is none |

### 3.13 Leads that could not be confirmed

| Lead | Status |
|---|---|
| Chinese studies using GF-1 / GF-6 and harvest-time difference in Hebei, Heilongjiang, Gansu | Not found in four Chinese-language searches. Only the two Inner Mongolia items (A1, A3) surfaced |
| CAAS work on silage maize area (粮改饲 monitoring) | Not found. A CAAS paper on maize straw-cover types (Trans. CSAE, 2025) surfaced but the host refused the connection; not opened |
| Main-Knorn et al. 2026, GIScience and Remote Sensing 63(1), PlanetScope and Sentinel-2 fusion for maize phenometrics | Abstract opened via https://api.openalex.org/works/doi:10.1080/15481603.2026.2637207 : fusion cut the mean absolute error "by up to 15%" for early stages and about 8% for harvest. A search summary says German codes 171 (grain), 172 (biogas) and 411 (silage) were merged and that silage end-of-season dates were bimodal. Full text not opened (HTTP 403); treat the bimodality claim as unverified |
| Asam et al. 2022, Remote Sensing 14(13):2981, Germany crop types with LPIS | Not opened. Search summary: maize, biogas maize, silage maize and grain maize pooled into one class |
| Austria, Netherlands, France, Belgium LPIS studies that classify silage versus grain | None found. French public RPG groups "maïs grain et ensilage" in one crop group (search summary of the ODR wiki, not opened) |
| USDA ARS or ERS, Statistics Canada, Eurostat work on silage area from remote sensing | Nothing found in the one NASS-directed search that ran; the AAFC / Statistics Canada search was refused for budget |
| Portuguese, Spanish, Italian literature | Not searched (budget) |

## 4. Formulas and recipes

Sentinel-2 band names: B2 blue, B4 red, B6 red edge (740 nm), B8 NIR, B11 SWIR1 (1610 nm).

- NDVI = (B8 - B4) / (B8 + B4)
- LSWI = NDMI = NDWI (Gao) = (B8 - B11) / (B8 + B11)
- PSRI = (B4 - B2) / B6
- Sentinel-1 cross ratio CR = VH / VV (linear units); RVI = 4 x VH / (VH + VV)

### Recipe A. Published baseline: TempDiff-SMID (Lin et al. 2025)

1. Sentinel-2 surface series, 1 April to 31 October, cloud-masked, 15-day composites, Whittaker-smoothed NDVI and LSWI.
2. C1: NDVI(May) <= 0.2 and NDVI(July) >= 0.2 and elevation < 1200 m.
3. C2: LSWI(July) >= 0.16.
4. C3: LSWI(September) <= 0.15.
5. Silage if C1, C2 and C3; grain if C1 and C2 but not C3.

For US use, the CDL corn mask replaces C1 and C2, and only C3 remains. Unknowns: which half-month stands for "September", and the Whittaker parameter. Inference: use the second half of September for a literal port, since the authors state silage was fully harvested by 10 September.

### Recipe B. "Cliff" ratio SPGH / LOS (Salehi Shahrabi et al. 2020), reconstructed from the abstract

1. Sentinel-2 NDVI per field, Savitzky-Golay smoothing, linear interpolation to a continuous series.
2. Find start of season, peak, and harvest (end of season).
3. SPGH = (NDVI at peak - NDVI at harvest) / (harvest date - peak date).
4. LOS = harvest date - start-of-season date.
5. Feature = SPGH / LOS. Large values = steep fall after a short season.

Inference: the abstract gives the definition in words only; the exact formula and the thresholds are in the paywalled text.

### Recipe C. Optical-to-radar end-of-season gap (after Meroni et al. 2021)

1. Fit a double hyperbolic tangent to the field's NDVI series and, separately, to its VH/VV series.
2. EOS50 = date at which the fitted curve has lost 50% of its decay amplitude.
3. Gap = EOS50(VH/VV) - EOS50(NDVI).
4. Published reference for mixed European maize in 2018: mean +18.6 days, mean absolute difference 25.5 days, r 0.52.

Inference: expected near zero for silage, several weeks for grain. Never tested as a classifier.

### Recipe D. Radar harvest window (Shang et al. 2020)

1. Coherence between consecutive Sentinel-1 acquisitions.
2. Candidate = coherence increase > 0.05, searched from 1 August to 31 October.
3. Accept if VH falls > 2 dB across the pair, or falls < 2 dB but ends below -19 dB.
4. Expect the right 12-day window 56% of the time and +-1 window 88% of the time.

### Recipe E. Operational fusion (WENR)

Harvest = NDVI falls to about 0.2 and Sentinel-1 coherence rises from about 0.2 towards bare-soil levels.

## 5. Synthesis

### (a) Which signal families carried the discrimination

| Signal family | Used to separate silage from grain? | Evidence |
|---|---|---|
| Harvest timing, calendar date | Yes; it is the only signal that has worked | Lin et al.: September LSWI threshold. Zhang et al. (unverified): early-September NDVI cliff. Di Tommaso et al.: silage gone by September |
| Canopy moisture index (LSWI / NDMI) at or just after the cut | Yes | Lin et al.: importance LSWI > NDVI > RENDVI > EVI; rule built on LSWI |
| Greenness at the cut (NDVI level before the drop) | Not for silage versus grain | Salehi Shahrabi et al. use the steepness of the NDVI fall, but against other crops |
| Red edge | Tested, weak | Lin et al.: RENDVI ranked third of four |
| SAR backscatter | Not as a discriminator | Blickensdörfer et al. had monthly VV, VH, RVI, VH/VV in the stack and still reported high uncertainty; optical ranked above SAR |
| SAR coherence | No (harvest dating only) | WENR, Shang et al., Khabbazan et al. |
| Post-harvest residue or bare soil (NDTI, STI) | No | Lin et al. describe the post-silage field as bare and dry but measure it with LSWI, not a residue index |
| Season length | Only inside SPGH / LOS | Salehi Shahrabi et al. |
| Canopy height | Incidental | Di Tommaso et al. |
| Context: livestock or dairy density, biogas plants | No | Ruf et al. relate maize share to biogas capacity descriptively, not as a classifier input |

### (b) Dry-down duration, or fusion of an optical browning date with a radar harvest date

Not found for silage versus grain. The nearest work is Meroni et al. 2021, which measures both dates on the same maize polygons and reports the gap, and the WENR service, which fuses NDVI with coherence to date the harvest. Neither turns the interval into a class feature.

### (c) Does anyone say the two are inseparable before harvest?

Not in those words. Lin et al. say the "overlapping growth stages pose significant challenges ... unlike the distinct separability typically observed between different crop types". Blickensdörfer et al. report "high uncertainties in differentiating silage and grain maize" and conclude the split "remains challenging". Every method that worked relied on the harvest itself. Inference: before the silage cut there is no published evidence of separability; a claim of pre-harvest discrimination would need its own proof.

### (d) Transfer across years and regions

- Across years, same region: Lin et al. lose 5-7 points of overall accuracy (0.9291 to 0.8621 and 0.8816) even with thresholds re-tuned by hand, and say the approach limits "cross-regional applicability".
- Across regions, same year: the SPGH / LOS rule trained at Marvdasht reached kappa 0.89, 0.90 and 0.80 at Abyek, Mashhad and Tulare, but for maize versus other crops.
- Across drought and normal years: Blickensdörfer et al. report consistent confusion patterns in 2017-2019 and a larger accuracy drop for maize in the drought years 2018 and 2019.
- Second hand, as cited by Lin et al. (original not opened): a phenology-guided random forest with growing-degree-day features for maize versus soybean in Kansas scored 0.9010 same-year and 0.8230 cross-year.

### (e) Agencies

- USDA NASS: CDL has no silage class; nothing found on remote-sensing silage estimates.
- AAFC: one corn class; AAFC scientists published the Sentinel-1 harvest detection study (C3), with corn among the crops.
- JRC: one maize class in the EU crop map; JRC scientists authored the SAR-versus-optical phenology comparison (C1).
- Thünen Institute (German federal research): the only agency-level map found with the split, reported as highly uncertain (A2).
- Wageningen Environmental Research: operational harvest dating of silage maize (C2).
- CAAS, ERS, ARS, Statistics Canada, Eurostat: nothing found; searches incomplete.

### (f) What is unstudied (in everything we opened)

1. Silage versus grain maize anywhere in the United States.
2. Sentinel-1 (backscatter or coherence) as a discriminator for this split; Lin et al. list it as future work.
3. A dry-down interval between optical senescence and harvest as a feature.
4. Harvest timing expressed in growing-degree days or relative to a county median; every precedent uses fixed calendar thresholds.
5. A residue index after harvest as a discriminator.
6. Distance to dairies or livestock density as a prior.
7. Calibrated probabilities, an abstention band, or precision at a realistic class prior.
8. Earliness: no study reports accuracy as a function of the date the estimate is made.
9. Area estimates for the two uses reconciled with official statistics; the two area comparisons that exist are for all maize or show the minority class over-estimated.

## 6. What this means for Kernel

**The plan survives and the novelty claims are honest**, with this wording: "to our knowledge, after a search in five languages". Specifically new: a US application; a radar-confirmed cut date; timing in growing-degree days and relative to the county; dry-down days; residue; dairy distance; calibrated uncertainty; reconciliation with NASS totals.

**Changes worth making tonight**

1. Add the published rule as a named baseline. Recipe A is four thresholds. Run it on the evaluation set, report silage precision, recall and false positive rate, and put it beside our model. It is the only published competitor, it is interpretable, and its failure outside its home calendar is the cleanest demonstration of why growing-degree-day timing matters.
2. Lead "green at cut" with the moisture index. The one direct study ranks LSWI (= NDMI on B8 and B11) above NDVI and above red edge. Keep NDVI as the second reading.
3. Add SPGH / LOS as a feature and name it. It is the published form of "falls off a cliff", and it was tested in a California dairy county.
4. Loosen the radar cut date. Published harvest detection from Sentinel-1 hits the correct 12-day window 56% of the time and +-1 window 88% of the time, and fails under rain, wet soil and standing residue. Carry a date uncertainty of about +-12 days, let optical scenes bracket the date when they exist, and feed that uncertainty into the "needs review" band.
5. Keep dry-down days, but coarse. The two-sensor end-of-season gap has a mean absolute difference of 25.5 days in the only study that measured it. Use wide bins (for example 0-10, 10-25, over 25 days) and present it as new and noisy.
6. Use VH just before the cut as the cloud fallback for greenness. For maize in senescence, VH correlates with NDVI at r = 0.81 and with NDWI at r = 0.83.
7. Never headline overall accuracy. The national German map shows what balanced training does to a rare class: the confusion alone was about as large as the true minority area. Report silage precision, recall and false positive rate at the real prior, and estimate acres with a calibrated or ratio estimator against NASS totals, not by counting pixels (pixel counts missed official silage maize area by 20-27% in the one study that compared).

**What to say to USDA statisticians**

- The published state of the art for this question is one hand-tuned September threshold validated on 381 points in one Chinese prefecture, with silage at one third of maize. At a 6% prior the same error rates would give a precision near one half.
- The German federal team, with complete parcel declarations and three sensors, reported high uncertainty for this split and over-estimated the minority class in every state.
- No agency product, including the CDL, separates the two uses. Our inputs inherit the CDL corn mask, whose corn accuracy is about 91-92%.
- Our four numbers each map to a documented physical effect: chopping while green (NDVI end of season at early dough), the moisture drop after the cut (LSWI), the radar response at harvest, and residue.

**Development path for the "how it could be developed further" slide**

- EuroCrops holds public, harmonised farmer declarations with separate codes for green silo maize and grain maize, covering 16 countries or regions. For scale, the declarations from five German states used by Blickensdörfer et al. (not all of them public) cover about 13,000 km2 of silage and 2,100 km2 of grain maize. Inference: this is a label set several orders of magnitude larger than the hackathon's, under the same Sentinel-1 and Sentinel-2 coverage, for testing the four numbers and their transfer. Per-country checks are needed, since not every national scheme records the use.

## 7. Pitfalls

1. A fixed calendar threshold is the published method and is exactly the "early is not silage" trap. It needed hand re-tuning between years inside one prefecture.
2. An optical series that stops at the end of September cannot see grain harvest; monthly radar means did not rescue the German map.
3. Balanced training samples inflate the rare class. In the US the rare class is silage.
4. Radar harvest signals fail with rain, wet autumn soil, standing residue, tillage and cover crops; maize stubble can keep the VH/VV ratio up after the cut.
5. Published accuracies are small-sample and partly in-sample. Do not present 93% as a target that an honest held-out test must match.
6. Papers titled "silage maize mapping" usually map maize in regions assumed to be all silage (Trier, Iran, Tulare). They are not evidence of silage-versus-grain separation.

## 8. Open questions

1. The SPGH / LOS thresholds and the Tulare reference data (paywalled text).
2. Whether any US, Canadian, Brazilian, Spanish or Italian study exists; those searches did not run.
3. How NASS and the labeled evaluation set treat high-moisture corn, earlage and snaplage, which are harvested early and wet but are grain products.
4. Whether post-harvest Sentinel-1 coherence (high over a bare chopped field, low where stalks stand) works as a residue proxy. The AAFC failure analysis suggests it; nobody has tested it.
5. Whether the DWD "harvest" stage used by Meroni et al. is mostly silage harvest (Germany grows several times more silage than grain maize), which would change how their 18.6-day gap should be read.

## 9. Source access log

Opened and read (full text unless noted):

- Lin et al. 2025: https://mdpi-res.com/d_attachment/agronomy/agronomy-15-01438/article_deploy/agronomy-15-01438.pdf?version=1749740666
- Blickensdörfer et al. 2022: https://literatur.thuenen.de/digbib_extern/dn064297.pdf
- Di Tommaso et al. 2021: https://arxiv.org/pdf/2109.06972
- Meroni et al. 2021: https://pmc.ncbi.nlm.nih.gov/articles/PMC7841528/
- WENR Bouwland Monitoring Service: https://www.groenmonitor.nl/api/file/186
- Shang et al. 2020: https://mdpi-res.com/d_attachment/remotesensing/remotesensing-12-01551/article_deploy/remotesensing-12-01551.pdf
- Khabbazan et al. 2019: https://mdpi-res.com/d_attachment/remotesensing/remotesensing-11-01887/article_deploy/remotesensing-11-01887.pdf
- Holtgrave et al. 2020: https://literatur.thuenen.de/digbib_extern/dn062663.pdf
- Ruf et al. 2021: https://mdpi-res.com/d_attachment/land/land-10-00128/article_deploy/land-10-00128.pdf?version=1612158011
- NASS CDL 2025 metadata: https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_CDL25_FGDC-STD-001-1998.htm
- AAFC Annual Crop Inventory specification: https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/supportdocument_documentdesupport/en/ISO%2019131_AAFC_Annual_Crop_Inventory_Data_Product_Specifications.pdf
- JRC EU crop map: https://ar5iv.labs.arxiv.org/html/2105.09261
- EuroCrops taxonomy and README: https://raw.githubusercontent.com/maja601/EuroCrops/main/hcat_core/HCAT3.csv , https://github.com/maja601/EuroCrops
- ZueriCrop: https://ar5iv.labs.arxiv.org/html/2102.08820
- Scarlat et al. 2026: https://arxiv.org/html/2606.00676
- Marais Sicre et al. 2016: https://mdpi-res.com/d_attachment/remotesensing/remotesensing-08-00591/article_deploy/remotesensing-08-00591.pdf
- Abstract only: Salehi Shahrabi et al. 2020 (https://api.openalex.org/works/doi:10.1080/01431161.2020.1779377); Main-Knorn et al. 2026 (https://api.openalex.org/works/doi:10.1080/15481603.2026.2637207); Suaza-Medina et al. 2024, maize harvest-date prediction from NDVI and weather, accuracy 92.1%, maize use not stated (https://api.openalex.org/works/doi:10.1080/17538947.2024.2359565)

Not opened:

- Salehi Shahrabi et al. 2020 full text, https://www.tandfonline.com/doi/abs/10.1080/01431161.2020.1779377 : HTTP 403, closed access
- Zhang et al. 2025, https://www.j-csam.org/html/2025/5/20250535.html : connection refused or dropped, four attempts
- Main-Knorn et al. 2026 full text, https://www.tandfonline.com/doi/full/10.1080/15481603.2026.2637207 : HTTP 403
- Asam et al. 2022, https://www.mdpi.com/2072-4292/14/13/2981 : not attempted after HTTP 403 on the publisher host
- Weser-Ems biogas study, https://www.sciencedirect.com/science/article/pii/S0048969725023071 and the Fraunhofer record: bot protection
- Veloso et al. 2017 (Sentinel-1 and Sentinel-2 crop behaviour), https://hal.science/hal-03272371 : bot protection
- CAAS maize straw-cover paper, http://tcsae.org/cn/article/pdf/preview/10.11975/j.issn.1002-6819.202504079.pdf : connection refused

Checked and found irrelevant: Ojeda et al. 2023, Frontiers in Plant Science (crop-model study of silage harvest index, no satellite data), https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2023.1206535/full
