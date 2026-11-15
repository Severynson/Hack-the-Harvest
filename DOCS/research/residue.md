# Ground left behind: crop residue cover, bare soil and tillage from Sentinel-2 / Landsat / HLS

Research brief for team Kernel, Hack the Harvest (written Sat 2026-11-14).
Topic: can the "blanket of brown stalks" (grain) versus "short stubble and dark bare soil" (silage) be measured from public satellites, how well, and what breaks it.

Conventions used in this file
- "Source says" = number or statement read in a document I opened. "Inference:" = my own reasoning or arithmetic on top of sources.
- "not opened" = I could not open the document (HTTP 403/404 or search-snippet only); treat as low confidence.
- R2 = coefficient of determination against measured residue cover unless stated otherwise. fR / CRC / MRC = fractional or percent crop residue cover.
- Method note: WebFetch could not parse PDFs, so PDFs were downloaded by WebFetch and their text layer extracted locally with macOS PDFKit; every quoted number below was read in that extracted text. The shared WebSearch budget ran out after 22 searches, so four planned searches were not run (listed in section 12).

---

## 1. Bottom line (read this first)

1. The physical contrast is large and well documented. Corn cut for silage leaves about 15% residue cover (Iowa State), 5% (a Best Management Practices factsheet on bmpbooks.com, which I believe is the Ontario BMP series; the publisher is not named in the text I extracted), or 13% / 27% for 6-inch / 12-inch stubble (Univ. of Wisconsin); corn combined for grain leaves 80-95% (Iowa State), 75-95% (NRCS guide), 85% (same BMP factsheet). That is a 60-80 point gap in cover.
2. On dry, vegetation-free soil that gap is worth roughly 0.10 NDTI units (Inference from two published calibrations, section 4). Published broadband residue errors are 12-23 cover points RMSE, so a two-class "bare versus blanket" call is realistic, a continuous residue percentage is not.
3. The same 0.10 NDTI can be produced or erased by things unrelated to harvest type: wet soil (+0.02 to +0.11 in the same field, irrigated versus not), green regrowth (NDTI 0.22 at NDVI 0.3-0.5, above the 0.15 of a full residue blanket), one tillage pass (-0.05), soil background (30% cover corresponds to NDTI 0.033 in Indiana but 0.077-0.080 in Maryland).
4. Therefore "ground left" must be (a) relative, not absolute; (b) gated to dry, non-green, snow-free scenes; (c) taken from the first valid scene after the cut; (d) allowed to be missing; and (e) used asymmetrically: a persistent residue blanket after an early cut is strong evidence of grain ("early is not silage"), while low residue alone is weak evidence of silage because fall tillage, baling and moldboard plowing also produce it.
5. New public data source found: NASA EMIT L2B Fractional Cover (60 m, photosynthetic vegetation / non-photosynthetic vegetation / bare soil fractions unmixed from the instrument's full visible-to-shortwave-infrared spectrum, which spans the 2.1 um cellulose feature; the exact spectral range, about 380-2500 nm, is from memory and was not read on the pages I opened). I verified through the NASA CMR API that granules exist over Tulare County CA, north-west Iowa and central Wisconsin in the fall windows of 2024, 2025 and 2026 (table in section 9). It is sparse in time, so it is a cross-check and demo layer, not a wall-to-wall feature.
6. I found no published study that uses a post-harvest residue index to separate silage from grain corn. The closest (Agronomy 2025, Inner Mongolia) uses an NDVI / LSWI timing rule. Using "ground left" explicitly as a harvest-type signal is a defensible innovation claim, with the caveat that my search was time-boxed.

---

## 2. What is actually left on the ground (measured numbers)

### 2.1 Cover immediately after harvest

| Situation | Residue cover | Source (opened) |
|---|---|---|
| Corn harvested for grain, 60-120 bu/ac | 80% | ISU Extension PM 1901a, Table 1 (adapted from MWPS-45), reviewed Sept 2009 |
| Corn harvested for grain, 120-200 bu/ac | 95% | same |
| Corn harvested for silage | 15% | same |
| Grain sorghum for grain / for silage | 75% / 15% | same |
| Soybeans | 70% | same |
| Corn or small grain "after harvest" | 75-95% of surface covered | NRCS "Corn & Soybeans Crop Residue Management Guide" (WA eFOTG copy); worked example starts at 0.95 |
| Soybean "after harvest" | 65-90% | same |
| Corn 85%, winter wheat 95%, soybeans 30%, silage corn 5% | as listed | "Best Management Practices: Residue Management" factsheet (bmpbooks.com) |
| Silage stubble 6 in | 13% mean (range 9-20%), 0.53 t/ac | Lauer, UW Wisconsin Crop Manager 9(6):45-46, 25 Apr 2002 |
| Silage stubble 12 in | 27% mean (18-41%), 1.05 t/ac | same |
| Silage stubble 18 in (high chop) | 42% mean (25-63%), 1.58 t/ac | same |
| Silage stubble 24 in (very high chop) | 55% mean (32-83%), 2.10 t/ac | same |

Source notes
- ISU PM 1901a adds: "This is only an estimate ... The actual values can vary significantly"; and lists "degree of grazing after harvest", "chopping versus leaving residue unchopped", "soil moisture and weather conditions" among the factors.
- Lauer: about 1 ton of dry matter per foot of stubble height; the author states he was unable to find studies that directly addressed silage cutting height versus cover, so the table is an estimate built from earlier studies (Gregory 1982; Dickey et al. 1985; Smith et al. 1990; Cusicanqui 1998; Lauer et al. 2001).
- Hendrickson (UW Extension, Manitowoc County WI, 1999-2000): describes "erosion prone slopes with limited residue cover" after silage, and rye no-till drilled on 20 Sept into silage stubble. Rye had to reach 18 in (9 May) before the spring residue after shallow disking exceeded 30% (5%, 10%, 34%, 72% for 6, 12, 18, 24 in rye). So a cover crop after silage means green vegetation within weeks of the cut.
- Inference (standing versus flat): the NRCS guide's weight-to-cover table (from RUSLE AH-703, Fig. 5-4) gives 30% cover for 1,000 lb/ac of flat corn residue, 60% for 2,650 lb/ac, 80% for 4,700 lb/ac, 90% for 6,700 lb/ac, 95% for 8,000 lb/ac. Lauer's 6-inch silage stubble is 0.53 t/ac = 1,060 lb/ac but covers only 13%. Standing stubble covers less than half the ground that the same mass lying flat would. After a combine, most of the stover is chopped and spread flat; after a silage chopper only short vertical stubs remain. This is why the contrast in cover is bigger than the contrast in residue mass.

### 2.2 What happens to the grain blanket afterwards (percent of the existing cover that remains after one operation, corn residue)

| Operation | Residue remaining | Source |
|---|---|---|
| Over-winter weathering | 80-95% | NRCS guide (ISU example uses 0.90) |
| Moldboard plow | 0-10% | NRCS guide; ISU PM 1901a |
| Chisel, twisted points | 40-60% | NRCS guide |
| Chisel, straight points | 55-80% | NRCS guide |
| Chisel, sweeps | 65-85% | NRCS guide |
| Offset disk, heavy | 35-45% | NRCS guide |
| Tandem disk after harvest, before other tillage | 80-90% | NRCS guide |
| Knife-type fertilizer applicator / anhydrous applicator | 60-80% / 75-85% | NRCS guide |
| Paraplow | 80-90% (NRCS); 70-90% (ISU) | both |
| Baling stover (spring ground cover) | 45.8% cover versus 88.7% control | 2017 Nebraska Beef Report, via OSU Beef Cattle Letter 12 Sep 2018 (2-year study) |
| Grazing stalks (spring ground cover) | 77.5% cover versus 88.7% control | same |
| Baling, typical practice | "usually more than 30% residue is left ... many striving to leave at least 50%" | UNL CropWatch 2017 |

Inference: grain (95%) followed by a fall chisel with twisted points lands at 38-57%, by a moldboard plow at 0-10%, by baling at about 46%. Grazing barely changes it. So "low residue" has four possible causes besides silage: plow, heavy disk, baling plus tillage, and high soil-disturbance manure incorporation. "High residue" (above about 60%) after a cut has essentially one cause: the crop was combined (or the stover is otherwise still lying there). High-chop silage (18-24 in, 42-55%) overlaps with tilled grain.

Context for how common tillage is: USDA ERS EIB-197 (2018) reports conservation tillage on 65% of corn acres in 2016 (so about 35% of corn acres were conventionally tilled before planting). That is tillage before the corn crop, not after it, and it is not a fall-tillage rate; I did not find a fall-tillage-after-corn rate (search budget exhausted).

---

## 3. Indices and formulas with band names

Band names: Sentinel-2 L2A = B2 (490 nm), B3 (560), B4 (665), B8A (865), B11 (1610), B12 (2190). HLS S30 uses the same names with a leading zero (B02, B03, B04, B8A, B11, B12; 30 m; 2015-11-28 to present). HLS L30 / Landsat 8-9 OLI = B02 blue, B03 green, B04 red, B05 NIR, B06 SWIR1 (1570-1650 nm), B07 SWIR2 (2110-2290 nm); 30 m; 2013-04-11 to present. The Earthdata HLS page says the combined record gives observations "every 1.6 days".

### 3.1 Broadband indices (computable today, wall to wall)

| Index | Formula (Sentinel-2) | Landsat / HLS L30 | Where I read it | Notes |
|---|---|---|---|---|
| NDTI (Normalized Difference Tillage Index; also called NBR2) | (B11 - B12)/(B11 + B12) | (B06 - B07)/(B06 + B07) | Hively 2021 Eq. 2; Li 2025 Table 2; Ding 2020 Table 1; Castaldi 2019 Eq. 2 (as NBR2) | Rises with residue, with wetness and with green vegetation |
| STI (Simple Tillage Index) | B11 / B12 | B06 / B07 | Li 2025 Table 2; Liu 2022 Table 2 | Identity: NDTI = (STI - 1)/(STI + 1). Same information. Ding 2020 uses a different definition (B8A/B12) |
| NDI5 | (B8A - B11)/(B8A + B11) | (B05 - B06)/(B05 + B06) | Li 2025; Ding 2020 | Identity: this is NDMI / LSWI |
| NDI7 | (B8A - B12)/(B8A + B12) | (B05 - B07)/(B05 + B07) | Li 2025; Ding 2020 | Identity: this is NBR |
| NDSVI | (B11 - B4)/(B11 + B4) | (B06 - B04)/(B06 + B04) | Li 2025 (Ding 2020 writes it with the sign flipped) | Senescent vegetation |
| NDRI | (B4 - B12)/(B4 + B12) | (B04 - B07)/(B04 + B07) | Ding 2020 | Best published index in Ding 2020 |
| SRNDI | (B12 - B4)/(B12 + B4) | (B07 - B04)/(B07 + B04) | Li 2025 | Identity: SRNDI = -NDRI |
| MCRC ("modified CRC"; Liu 2022 calls it CRC) | (B11 - B3)/(B11 + B3) | (B06 - B03)/(B06 + B03) | Li 2025; Ding 2020; Liu 2022 | Weakest in both maize studies |
| SGNDI | (B3 - B12)/(B3 + B12) | - | Ding 2020 | |
| DFI (Dead Fuel Index) | 100 x (1 - B12/B11) x (B4/B8A) | 100 x (1 - B07/B06) x (B04/B05) | Ding 2020 (from MODIS) | Contains the NDTI ratio times a red/NIR greenness term |
| 3BI1 "simulated CAI" | 100 x (0.5 x (B2 + B12) - B4) | - | Ding 2020 (proposed) | |
| 3BI2 "simulated LCA" | (B2 - B4)/(B2 - B12) | - | Ding 2020 (proposed) | Best in Ding 2020 (R2cv 0.63) |
| 3BI3 | (B12 - B4)/(B12 + B11) | - | Ding 2020 (proposed) | |
| Brightness | single-band or mean reflectance, e.g. B4 | B04 | Ding 2020 (B4 alone R2cv 0.58, r = 0.75) | Direction depends on soil colour (section 5.3) |
| BSI (Bare Soil Index) | ((B11 + B4) - (B8A + B2)) / ((B11 + B4) + (B8A + B2)) | same with B06, B04, B05, B02 | from memory, NOT verified in an opened source | Use only as a bare-soil covariate |
| SWIRA | broadband SWIR index computable from Landsat 4-9 | - | USGS summary of Lamb et al. 2025 | Formula not shown on the pages I could open |

Implication for our "Index Scout" agent: every index built only from B11 and B12 is the same measurement (NDTI, STI, NBR2, and the residue part of DFI). Genuinely different candidates are the pairings of B12 with red (NDRI / SRNDI) or NIR (NDI7), the pairing of B11 with NIR (NDI5 = NDMI) and plain brightness. Ranking 13 names can hide that there are about 4 independent signals.

### 3.2 Narrow-band (hyperspectral) indices that see cellulose and lignin directly

| Index | Formula | Source |
|---|---|---|
| CAI (Cellulose Absorption Index) | 0.5 x (R2000 + R2200) - R2100 (often x100; bands 10-50 nm wide at about 2030, 2100, 2210 nm) | Hively 2021 Eq. 3; Quemada & Daughtry 2016 Eq. 1; Daughtry 2001 (2015, 2106, 2195 nm; AVIRIS 2031, 2101, 2211 nm) |
| LCA (Lignin-Cellulose Absorption) | 2 x R2210 - (R2100 + R2330) | Hively 2021 Eq. 4 |
| SINDRI | (R2210 - R2260)/(R2210 + R2260); WorldView-3 SWIR6 (2185-2225 nm) and SWIR7 (2235-2285 nm), x100 in Quemada 2018 | Hively 2021 Eq. 5; Quemada 2018 Table 1 |
| SIDRI | R2210 - R2260 (difference form; robust to green vegetation) | Hively 2021 |
| LCPCDI | 2 x R2210 - (R2100 + R2260) | Hively 2021 Eq. 6 |
| Water index WI | WV3 SWIR3 / SWIR5 (1640-1680 / 2145-2185 nm); Landsat equivalent OLI6 / OLI7; RWC = 2.0 x WI - 2.1 | Quemada 2018 Table 1 and Table 2 note; Quemada & Daughtry 2016 |

Why the broad band is weak: Hively 2021: Landsat 8 and Sentinel-2 "each provide two SWIR bands centered at 1600 and 2200 nm. However, the 2200 nm band covers a broad spectral range from 2100 nm to 2300 nm, a wavelength range poorly situated to capture the spectrally narrow ligno-cellulose absorption features."

---

## 4. How well do the indices track measured residue cover

### 4.1 Reported fits

| Study (opened unless noted) | Sensor, place, timing | Index | R2 | RMSE (cover points) | n |
|---|---|---|---|---|---|
| Zheng et al. 2012 (in Zheng dissertation, Virginia Tech 2012) | Landsat TM/ETM+, central Indiana, spring planting season | minNDTI | 0.89 (calibration); 0.87 quoted in abstract | - ; 3 tillage classes > 90% overall accuracy | - |
| Zheng et al. 2013 validation (same dissertation, ch. 3) | Landsat, IA / IN / IL / MD, several years | minNDTI local models | 0.66-0.89 cal; 0.56-0.93 val | 7.8-13 cal; 8.4-15.1 val; 3-class accuracy 0.68-0.86 | 6 datasets |
| same | same | minNDTI regional model CRC = 754.7 x minNDTI + 5.4 | 0.61-0.91 | 9.2-18.8; 3-class accuracy 0.69-0.80 | 6 datasets |
| Hively et al. 2018, Remote Sens. 10:1657 | WorldView-3, Maryland, 14 May 2015, dry soil (7.6-7.9% moisture), NDVI < 0.3 | SINDRI / LCA / NDTI (WV3 bands averaged to Landsat) | 0.94 / 0.92 / 0.84 (2nd-order); NDTI linear 0.77 | 7.15 / 8.40 / 12.00 | 174 |
| Hively et al. 2019, Remote Sens. 11:1857 | Landsat 7 and 8 calibrated on a WV3 residue map, gradient-boosted trees on 6 indices + 6 bands | tillage classes | overall accuracy about 92% (+/-10%); class accuracy 75-99% | - | - |
| Hively et al. 2021, Remote Sens. 13:3718 | field spectra, Beltsville MD, convolved to bands; NDVI < 0.3 | SINDRI / CAI / NDTI (OLI bands) | 0.81 / 0.77 / 0.44 | 0.13 / 0.15 / 0.23 (fraction) | 640 (table caption; the text says 650) |
| same, all NDVI (< 1.0) | same | CAI / SIDRI / SINDRI / NDTI | 0.71 / 0.70 / 0.40 / 0.01 | 0.17 / 0.17 / 0.24 / 0.31 | 916 (text) |
| Lamb et al. 2022, Remote Sens. 14:6128 | field spectra by relative water content class | NDTI at RWC 0-0.1 / 0.1-0.25 / 0.25-0.6 | 0.867 / 0.817 / 0.429 | 0.110 / 0.103 / 0.217 | 135 / 101 / 77 |
| same | by green-vegetation fraction class | NDTI at fGV 0-0.1 / 0.1-0.3 / 0.3-0.6 | 0.396 / 0.003 / 0.002 | 0.261 / 0.299 / 0.196 | - |
| Lamb et al. 2025, Soil & Tillage Research (USGS summary page; full text not opened) | WorldView-3, Maryland, 2015-2022, 895 photos | SINDRI (average of 6 years) / SINDRI (5 years pooled) / SWIRA + WI + NDVI / NDTI + WI + NDVI | 0.869 / 0.795 / 0.767 / 0.654 | 0.111 / 0.141 / 0.144 / 0.174 | 895 |
| Li et al. 2025, Remote Sens. 17:105 | Sentinel-2 L2A (28 Oct 2020), maize, Jilin black-soil region, field photos 20-31 Oct 2020 (right after harvest) | NDTI / STI / NDI7, SRNDI | 0.755 / 0.751 / about 0.72 | 6.74% / 6.93% | 110 |
| same | same | XGBoost / RF / stacking on 7 indices | 0.884 / 0.865 / 0.923 | 4.77% / 4.06% / 3.32% | 73 train, 37 test |
| Ding et al. 2020, Remote Sens. 12:1470 | Sentinel-2B (27 Mar 2018), maize, Changchun, UAV truth 29 Mar 2018 (about 5 months after harvest), 320 x 450 m site | NDRI / NDI7 / STI(B8A/B12) / DFI / NDI5 / NDTI / NDSVI / MCRC | 0.61 / 0.57 / 0.57 / 0.52 / 0.51 / 0.50 / 0.42 / 0.15 (10-fold CV) | 6.7-10.3% | 243 pixels |
| same | same | band B4 alone / B12 alone | 0.58 / 0.07 | 7.2% / 10.9% | 243 |
| Memon et al. 2023, Agronomy 13:2691 (abstract only readable) | Sentinel-2B and Landsat 8, wheat straw, Changshu | NDTI / STI / NDRI | S2: 0.85 / 0.82 / 0.69; L8: 0.77 / 0.80 / 0.56 (abstract headline for S2 NDTI is 0.80) | - | 80 sites |
| Hagen et al. 2020, Land 9:408 (OpTIS) | Landsat 5/7/8 + Sentinel-2A/B + MODIS, 645 Corn Belt counties, spring residue | NDTI + CRC index, HUC8-parameterized | 0.467 (r = 0.683) versus roadside estimates | 21.4 (MAD 17.5); 4-class agreement 42.3%; weighted kappa 0.67 | 827 fields |
| Beeson, Daughtry, Wallander 2020, Remote Sens. 12:2665 (USDA ARS + ERS) | Landsat 5/7/8, 150,000 km2 in SD / ND / MN, 2007-2016, no training data | scaled minNDTI versus ARMS survey fields | 2-class accuracy 61-67% raw, 68-73% with +/-5% tolerance at the 30% line; best method 85%, kappa 0.66 (crop-specific scaling, more than 4 overpasses) | - | > 500,000 fields mapped |
| Azzari et al. 2019, RSE 221:417 (Stanford summary page and Deines 2019 ERL opened; full text not opened) | Landsat 5/7/8 composites + Sentinel-1, random forest, about 5,900 producer fields, North Central US 2005-2016 | low versus high intensity tillage | accuracy 75-79% (84% of conservation and 72% of conventional validation points correct); state totals versus USDA 2006 survey R2 = 0.55 | - | 5,866 |
| Maize RF study, Int. Soil and Water Conservation Research 2024 (not opened: HTTP 403; search snippet only) | Sentinel-2, maize | STI / NDTI | 0.85 / 0.84 | - | - |

Reading across the table: broadband NDTI reaches R2 0.75-0.89 when the scene is dry, bare of green vegetation and close in time to the field measurement, and falls to 0.44-0.50 or lower otherwise. Hively 2021 sums it up: studies using broadband indices "seldom ... produce accuracies exceeding 80%", and accurate NDTI use is "generally limited to settings where residue is fresh, soil and residue moisture contents are below 25%, and GV cover is minimal".

### 4.2 Typical NDTI values and published calibrations

| Item | Value | Source |
|---|---|---|
| Calibration A (WV3 bands averaged to OLI, Maryland, dry): fR(%) = 789.07 x NDTI - 30.774 | adj. r2 > 0.99 on two end-member fields | Quemada et al. 2018, Eq. 1 |
| Calibration B (Landsat TM, central Indiana): CRC(%) = 754.7 x minNDTI + 5.4 | R2 0.89 | Zheng et al. 2012 (dissertation) |
| Local calibrations at other sites | slopes 464.9 to 967.1, intercepts -4.0 to +19.6 | Zheng dissertation, ch. 3 and 4 |
| Mean NDTI, fields with 0-30% residue | 0.069 | Hively 2018, Table 4 |
| Mean NDTI, fields with 30-60% residue | 0.129 | same |
| Mean NDTI, fields with 60-100% residue | 0.153 | same |
| NDTI at 30% / 60% residue (2nd-order fit) | 0.080 / 0.115 | Hively 2018, Table 2 |
| NDTI saturation | 0.142, equal to 82.9% residue | same |
| Mean NDTI, 14 "green" fields (0.3 < NDVI < 0.5) | 0.221 ("outside valid range") | Hively 2018, Table 4 |
| Nearly bare field, dry (RWC 0.04) | NDTI 0.045 | Quemada 2018, field 5 |
| One tillage / planting pass at a Maryland sample | NDTI 0.078 to 0.028 | Zheng dissertation |
| Low-lying wet, dark, high-SOC soils | negative minNDTI | Zheng dissertation |
| Dry bare soil in Sentinel-2 (soil-mapping practice) | NDVI < 0.35 to drop green vegetation, then NBR2 (= NDTI) < 0.05 strict, < 0.075 looser; thresholds 0.025-0.35 tested; non-vegetated pixels were 26.9% of the image, and only 10% of the image passed NBR2 < 0.05 (so roughly a third of the non-vegetated area counted as dry bare soil) | Castaldi et al. 2019 |
| Same idea, Belgium | NDVI < 0.25 then NBR2 < 0.05 | Dvorakova et al. 2023 (not opened: search snippet only) |

Inference (expected NDTI for our two classes on dry soil, by inverting the calibrations):

| Residue cover | NDTI, calibration A (Maryland) | NDTI, calibration B (Indiana) |
|---|---|---|
| 0% | 0.039 | -0.007 |
| 15% (silage, ISU) | 0.058 | 0.013 |
| 30% | 0.077 | 0.033 |
| 60% | 0.115 | 0.072 |
| 85% | 0.147 | 0.105 |
| 90% (grain) | 0.153 | 0.112 |

Inference: silage (15%) versus grain (90%) differ by about 0.095 (A) to 0.099 (B) NDTI units. The offset between the two calibrations at the same cover is about 0.04-0.045, which is almost half of the class gap. Absolute NDTI thresholds therefore do not transfer between regions, soils or sensors; relative scaling within a scene does. All these values come from Landsat-like bands; Sentinel-2 B11/B12 should behave similarly but we should confirm on our own fields.

### 4.3 Signal budget (the one table to show a skeptic)

| Effect | Size in NDTI units | Source |
|---|---|---|
| Silage stubble versus grain blanket, dry soil | about +0.10 | Inference from Quemada 2018 and Zheng 2012; consistent with Hively 2018 class means 0.069 versus 0.153 (difference 0.084) |
| Same field, irrigated wedge versus dry wedge | +0.022 to +0.106 (for example 0.075 to 0.181 in field 2; 0.083 to 0.181 in field 3) | Quemada 2018, Table 2 |
| Green cover at NDVI 0.3-0.5 versus a 60-100% residue field | +0.07 (0.221 versus 0.153) | Hively 2018 |
| One tillage or planting pass | -0.05 | Zheng dissertation |
| Region / soil offset at equal cover | about 0.04-0.045 | Inference from the two calibrations |
| Error of broadband residue estimates | 12-23 cover points RMSE (about 0.015-0.03 NDTI) | Hively 2018; Hively 2021; Hagen 2020; Zheng |

---

## 5. Confounders, quantified where possible

### 5.1 Soil and residue moisture (rain, irrigation, probably manure slurry)
- Quemada & Daughtry 2016 (Remote Sens. 8:660): "For NDTI to reliably assess fR, scene RWC should be relatively dry (RWC < 0.25)". NDTI of soils "increased monotonically as RWC increased"; NDTI of residues was nearly flat up to RWC 0.6, then rose sharply.
- Quemada, Hively, Daughtry, Lamb, Shermeyer 2018 (RSE 206:33-44), ten centre-pivot fields caught mid-irrigation by WorldView-3 on 14 May 2015: in every partially irrigated field NDTI and the water index were significantly higher in the wet wedges; "For five of the fields, mean fR estimated using NDTI was > 100% for the wet wedges"; the wet-to-dry ratio of NDTI-estimated cover was > 2 (about 1.3 for SINDRI). Within-field RMSE of NDTI-based cover: 23.4 points before and 4.5 after their correction (abstract: 22.7 to 4.7); SINDRI 6.0 to 2.2. Mean NDTI-estimated cover in fields 1-8 fell from 68% to 44% after correction.
- Their correction: adjust each SWIR band reflectance by slope x (WI_pixel - WI_driest wedge of the same field), slope 0.971 for the NDTI bands, then recompute NDTI. It needs a drier reference inside the same field and assumes uniform residue. They note the Landsat water index OLI6/OLI7 and the WV3 index were interchangeable (r2 = 0.99).
- Inference (important): OLI6/OLI7 is the simple tillage index, i.e. a monotone transform of NDTI. With only Sentinel-2 or Landsat SWIR bands, a single pixel cannot separate "wet" from "residue"; the correction works only as a within-field or within-neighbourhood relative adjustment, or with outside moisture information (precipitation, SAR, SMAP).
- Lamb et al. 2022: NDTI R2 0.867 and 0.817 for RWC below 0.25, 0.429 for RWC 0.25-0.60.
- Direction is not always the same: in Zheng's Indiana and Iowa data, wet, dark, poorly drained soils produced negative minNDTI and under-estimated residue; in Quemada's irrigated wedges wetness raised NDTI. Either way moisture and soil background move NDTI by as much as the signal.
- Operational fixes that have been used: Gelder et al. 2009 used only Landsat images acquired more than 2 days after precipitation (cited in Quemada 2018). Beeson et al. 2020 masked areas with more than 3 mm of NEXRAD rainfall in the 2 days before the overpass. OpTIS uses PRISM precipitation "to account for soil and crop residue moisture effects". Lamb 2025 adds a water index and NDVI as regression covariates (NDTI + WI + NDVI reaches R2 0.654; SWIRA + WI + NDVI 0.767). Hively 2019: under wet conditions single-band reflectances explained residue better than SWIR indices, so keep raw bands as features.
- Manure: I found no opened source that measures the effect of manure application on NDTI. Inference: slurry wets the surface (NDTI up) and solids with bedding are themselves non-photosynthetic plant material (NDTI up), so both would make a silage field look more like grain. Unverified.

### 5.2 Green vegetation (weeds, volunteer corn, cover crops, California winter forage)
- Hively 2021: NDTI versus residue R2 0.44 with NDVI < 0.3 but 0.01 over the full NDVI range; when NDVI is not limited NDTI correlates with green cover (R2 0.70) and with NDVI (R2 0.85). "applying a threshold of NDVI < 0.3" is the common practice.
- Hively 2018: with the two Landsat-compatible indices "even minimal vegetation is likely to produce a positively biased error in residue prediction"; cites Gelder et al.: NDVI explains the NDTI model residual (R2 0.65) "even with NDVI values below 0.35".
- Lamb 2022: NDTI R2 0.396 at green fraction 0-0.1, 0.003 at 0.1-0.3.
- Zheng: pixels with NDVI > 0.30 at the time of minNDTI were excluded; "High NDTI values (> 0.20) ... are due to the presence of green vegetation".
- Beeson 2020: NDVI > 0.3 masked.
- Consequence for us: a cover crop or winter forage that emerges 2-4 weeks after a silage cut will raise NDTI above the bare-soil level. The valid window after silage can be short; the regreening itself is a separate, useful silage clue.

### 5.3 Soil colour and organic matter
- Daughtry et al. 2001 (lab spectra): mixtures of dry corn residue with dry Barnes soil (Morris MN, a Udic Haploboroll, i.e. a dark Mollisol) showed a "wide range in reflectance factors ... made discrimination relatively easy at most wavelengths. However, for the Codorus and Othello soils, the addition of corn residue generally decreased reflectance across the spectrum." "Crop residues may be brighter or darker than a particular soil depending on moisture content. Thus, discrimination ... using reflectance in any single wavelength band ... would be difficult and would require frequent adjustments of the discrimination thresholds".
- Ding 2020 (black soil, north-east China): red band B4 alone correlates with residue cover at r = 0.75 (R2cv 0.58), better than NDTI (0.50) in that late-winter scene.
- Li 2025 (same black-soil region, right after harvest): NDTI R2 0.755.
- Zheng: "soil moisture and organic carbon can also confound the NDTI signal, which tend to cause underestimation of CRC in low-lying wet and dark areas"; recommends field-level averaging and excluding poorly drained soils.
- Castaldi 2019: "soil albedo decreases with increasing SOC content".
- Inference: on dark Mollisols and dark Central Valley soils fresh residue is much brighter than the soil, so visible/NIR brightness is a second, partly independent residue signal, but its sign flips on light soils. Use brightness only relative to the same field's own bare-soil brightness (for example its spring pre-emergence state) or relative to neighbours on the same soil.

### 5.4 Residue age and weathering
- Cover itself is durable: 80-95% of corn residue cover survives the winter (NRCS). ISU example: 95% after harvest becomes 86% after winter.
- Spectral contrast is less durable: Hively 2018: "The type and decomposition stage of crop residue also affects residue reflectance, impacting the broader Landsat-compatible indices (NDTI) more than the narrow-band indices"; Hively 2021: accurate NDTI use is limited to "settings where residue is fresh".
- Suggestive only: Sentinel-2 NDTI reached R2 0.755 within days of harvest (Li 2025) and 0.50 five months later in the same region (Ding 2020); different sites and methods, so not a controlled comparison.
- I found no week-by-week decay curve for NDTI after harvest. We can measure it on our own grain fields.

### 5.5 Tillage, baling, grazing after harvest
See section 2.2. Beeson 2020: "residue cover is reduced with each operation - never increased". Inference: the earliest valid scene after the cut is the best estimate of what the harvest left; later scenes can only lose residue or gain moisture and green cover.

### 5.6 Snow, shadows, standing residue
- Snow must be masked (standard cloud/snow masks; EMIT documentation notes snow/cloud confusion in its own QC). No residue study I opened works on snow-covered ground.
- Standing residue: Hively 2018 notes that line-point field methods "do not work well with standing residue"; Zheng notes radar has "better capabilities to sense soil moisture and standing corn stalks". Inference: standing senesced grain corn before harvest is itself non-photosynthetic vegetation, so residue indices are high both just before and just after a grain harvest and do not date the grain harvest; for silage the indices drop from a green-canopy value to a bare-soil value at the cut.

### 5.7 Post-harvest irrigation
Covered by the Quemada 2018 centre-pivot experiment (section 5.1): a freshly irrigated low-residue field read as > 100% cover in NDTI. This is the main risk for California silage ground that is pre-irrigated for winter forage.

---

## 6. Timing: how soon, for how long, and the multi-temporal methods

- minNDTI (Zheng, Campbell, de Beurs 2012; validated 2013). Idea: over the spring planting window take the minimum NDTI of the time series; it marks the moment after tillage/planting and before crop emergence, when neither green weeds (which raise NDTI) nor un-tilled residue inflate the value. Requirements stated: observations "at intervals of approximately one or two weeks", NDVI > 0.30 scenes excluded, attention to recent rain and low-lying wet areas; for "double-cropped or irrigated fields with multiple planting dates, additional sequences will be required for each planting date".
- Beeson, Daughtry, Wallander 2020 (the USDA ARS / ERS "untrained" version): for each Landsat scene, convert NDTI to residue cover by linear scaling between the scene's NDTImin and NDTImax, taken as mean minus / plus 3 standard deviations after masking; RCmin = 0%, RCmax = 85% for corn and 65% for soybean (Shelton et al. 1995); masks = cloud/shadow, NEXRAD 2-day rain > 3 mm, NDVI > 0.3; mosaic by minimum over the season; field value = mean over a polygon buffered 30 m inward; QA flag = number of useful dates, results unreliable with fewer than four. Validated against USDA ARMS field-level survey answers (accuracies in section 4.1). Separate scaling by crop type mattered most; by soil texture or slope helped less.
- OpTIS (CTIC, The Nature Conservancy, Regrow, formerly Applied GeoSolutions / Dagan). Hagen et al. 2020: multi-sensor (MODIS Terra/Aqua, Landsat 5/7/8, Sentinel-2A/B) on a 30 m grid; PRISM precipitation for moisture effects; median plant and harvest dates per HUC8 from MODIS NDVI; residue fraction from NDTI and the CRC index in every image, time series analysed to return residue at planting with a certainty level; four classes 0-15, 16-30, 31-50, 51-100%; fields under 10 acres dropped; more than 1.7 million field segments. Validation numbers in section 4.1. Public data (CTIC page and CTIC RFP dated 10 Feb 2026): CONUS row-crop regions, years 2015-2021, version 4.0 released Sept 2023, delivered free through a CTIC visualization tool only at Crop Reporting District and HUC8 scale; tillage categories no-till, conservation (> 30% residue), reduced (15-30%), conventional (< 15%). The RFP ("Viridis View") seeks new providers for 2022-2030 and county scale, and cites a 2026 paper (McGill et al., not opened) on "the challenges in confirming the accuracy of such data".
- Azzari et al. 2019: Landsat composites + Sentinel-1 + about 5,900 producer fields, random forest, 75-79% accuracy; Sentinel-1 "adds relatively little to classification performance beyond what is possible with Landsat".
- Inference for harvest-type use: all of these methods target the spring tillage state and deliberately take a seasonal minimum. We need the opposite end: the state immediately after the cut. So use the first valid scene after the cut (or the minimum of the first two or three within about 2-3 weeks, to shed moisture and regrowth inflation), record the lag in days, and treat anything later than about 30 days as stale.
- The calendar asymmetry matters today (14 Nov): silage fields cut in late Aug-Sep have had many chances for a valid scene; late-October and November grain fields may have none before snow and low sun. For those, "still standing and brown on the last clear scene" already says grain, and the residue feature is simply missing.

---

## 7. SAR and optical fusion for residue and tillage

| Study | Finding |
|---|---|
| Azzari et al. 2019 (Stanford summary page) | Sentinel-1 "adds relatively little" beyond Landsat for tillage classes; overall 75-79% |
| Liu et al. 2022, PLoS One 17(11):e0277425 (Bihar, zero versus conventional tillage, 160 fields) | Sentinel-1 alone 62.3%; Sentinel-2 alone 83.2%; S1 + S2 82.7%; Planet alone 86.6%; all three 87.7%. Sentinel-1 never in the top five features of multi-sensor models |
| Wang, Yuan, Guan et al., EGU24-14253 (abstract) | Sentinel-2 tillage-index time series + soil background reflectance + SMAP soil moisture + Sentinel-1 backscatter, 41,325 ground records over 10 crops in the EU: accuracy 0.78, F1 0.70 for residue presence |
| Borio et al. 2025, JRC143611 (record page) | Sentinel-2 products, especially NDVI, most informative for tillage versus no-tillage; Sentinel-1 "valuable" when optical data are missing; strong class imbalance in the reference data |
| Hagen et al. 2020 (OpTIS) | Optical only, with PRISM precipitation as the moisture control |
| "Improving maize residue cover estimation with the combined use of optical and SAR" (Int. Soil and Water Conservation Research; not opened, snippet only) | S2 + S1 models R2 > 0.8 |

Inference: published evidence says C-band SAR adds little to residue-cover estimation itself. Keep Sentinel-1 for what our plan already uses it for (dating the cut through clouds) and as a wetness flag for optical scenes; do not spend build time on SAR residue features.

---

## 8. Is anyone already separating silage from grain with residue?

- Not found. Closest: "Silage Maize Identification Using a Temporal Difference-Based Model with Sentinel-2 Data" (Agronomy 2025, 15:1438; Hohhot, Inner Mongolia). A transparent rule on 15-day Whittaker-smoothed composites: NDVI in May <= 0.2 and NDVI in July >= 0.2 (and elevation < 1200 m), LSWI in July >= 0.16, LSWI in September <= 0.15 ("the post-harvest moisture decline (bare soil after silage maize harvest) contrasts with the persistent moisture of regular corn"). Overall accuracy 0.9291, kappa 0.8923, F1 0.9307 silage / 0.9112 grain; random forest baseline 0.9043. Transfer to 2022 and 2021: 0.8621 and 0.8816. Feature importance LSWI > NDVI > RENDVI > EVI. Harvest windows there differ by only 5-15 days.
- Relevance: (1) precedent that a two-or-three-threshold rule can beat a random forest on this exact problem; (2) their decisive variable, LSWI, is (NIR - SWIR)/(NIR + SWIR), i.e. our NDMI / NDI5; (3) it is a pure calendar rule, so it would fail the "early is not silage" trap. Our residue feature is the calendar-independent complement.

---

## 9. Hyperspectral sensors with the 2.0-2.3 um features

### 9.1 EMIT L2B Fractional Cover: a ready-made public NPV map (new data source)

Source: NASA Earthdata catalog page for EMITL2BFRCOV V002, the emit-sds-frcov ATBD and user guide on GitHub, and my own NASA CMR API queries on 2026-11-14.

- Product: "EMIT L2B Fractional Cover and Uncertainty 60 m". Seven Cloud Optimized GeoTIFFs per granule: PV, NPV and BARE fractional cover (0-1), their uncertainties, and a QC flag (cloud, urban, water, snow/ice). 60 m pixels, granules about 75 km wide. Coverage: land between about 52 N and 52 S (instrument on the ISS). Temporal extent 2022-08-09 to present; no acquisitions 13 Sep 2022 to 6 Jan 2023.
- Versions: V001 (CMR concept C3911089796-LPCLOUD), 137,361 granules, ends 2026-08-31. V002 (C4303752957-LPCLOUD), catalog page dated 2026-10-09, 135,498 granules on 14 Nov 2026, newest granule 2026-11-14T02:23Z; V002 drops the 80% cloud exclusion. My queries returned V002 granules for October 2026 but none for autumn 2025 over Tulare County, where V001 has six acquisition times, so use V001 for anything up to August 2026.
- Algorithm (ATBD): Monte Carlo spectral unmixing "E(MC)2" of the full surface-reflectance spectrum, brightness-normalized, 20 bootstrap draws with 30 endmembers per class, endmember library from Ochoa et al. 2025 (Remote Sensing of Environment 324:114746). Validation is described against spectral line-point intercept transects; the ATBD gives no error statistics (a search snippet of a ScienceDirect paper claims mean absolute error <= 0.05 for NPV, GV and soil; not opened).
- Known issues (catalog page): pixels at cloud edges and in cloud shadow may be wrongly labelled high NPV; some QC misclassification of water, cloud and snow.
- File names: V002 `EMIT_L2B_FRCOVNPV_002_YYYYMMDDTHHMMSS.tif` (also PV, BARE, PVUNC, NPVUNC, BAREUNC, QC); V001 adds orbit and scene numbers.
- Access: LP DAAC cloud archive with a free Earthdata login. Search without login: `https://cmr.earthdata.nasa.gov/search/granules.json?concept_id=C3911089796-LPCLOUD&bounding_box=W,S,E,N&temporal=START,END&page_size=500`.

Granules I found (CMR bounding-box search; "cloud" is the granule-level cloud_cover attribute; a hit means the footprint intersects the box, not that a given field is covered):

| Area (bounding box W,S,E,N) | Season | Acquisition dates (cloud %) | Version |
|---|---|---|---|
| Tulare County CA (-119.6, 36.0, -119.0, 36.5) | fall 2024 | 27 Sep (0), 11 Oct (8-28), 30 Nov (25) | V001 |
| same | fall 2025 | 18 Aug (2), 22 Aug (5), 30 Sep (3), 4 Oct (16), 27 Nov (82), 1 Dec (27) | V001 |
| same | 2026 | 3 Aug (0), 13 Aug (0), 21 Aug (4) | V001 |
| same | fall 2026 | 5 Oct (0) | V002 |
| North-west Iowa (-96.6, 42.9, -95.8, 43.4) | fall 2025 | 20 Aug (0-12), 28 Sep (0), 2 Oct (0) | V001 |
| same | 2026 | 1 Aug (1), 5 Aug (60), 7 Aug (15) | V001 |
| same | fall 2026 | 3 Oct (14), 9 Oct (45), 13 Oct (26) | V002 |
| Central Wisconsin (-90.9, 44.4, -90.0, 45.0) | fall 2025 | 2 Oct (0) | V001 |
| same | fall 2026 | 3 Oct (72), 11 Oct (72) | V002 |

Why it matters (Inference): in the Midwest in the first days of October, silage ground is bare (BARE high), grain corn is senesced and standing or just combined (NPV high), and anything still green shows as PV. A single EMIT acquisition therefore gives a three-fraction snapshot that is close to a direct silage / grain discriminator, derived from the cellulose-lignin features that Sentinel-2 cannot resolve. A 40-acre field (about 400 m x 400 m) holds roughly 44 EMIT pixels, fewer after an inward buffer, so only fields larger than a few hectares are usable. Revisit is irregular, so this is a validation and storytelling layer.

Minimal demo recipe: pick one or two granules covering labelled or CDL corn fields; download NPV, BARE, PV, QC; mask QC flags; zonal mean per field; plot EMIT NPV fraction against the Sentinel-2 / HLS NDTI of the nearest clear date (within about 5 days); report the rank correlation and show the map.

### 9.2 Other sensors

| Sensor | Facts read on official pages | Feasibility for a demo field |
|---|---|---|
| EnMAP (DLR) | 30 m, 30 km swath, VNIR 420-1000 nm and SWIR 900-2450 nm, 27-day nadir revisit (4 days with 30 degree off-nadir pointing), operational; archive through EOWEB GeoPortal and EOC Geoservice, tasking by proposal through the Instrument Planning Portal (registration) | Possible only if an archive scene happens to cover the field in the right weeks; not checked |
| PRISMA (ASI) | launched 22 March 2019; 30 m hyperspectral VNIR + SWIR and 5 m panchromatic; operational; data requested through the PRISMA portal | Same; not checked. Pepe et al. 2020 / 2022 mapped crop residue and NPV with PRISMA (not opened; snippet reports overall accuracy above 90% for a residue / soil / vegetation decision tree) |
| WorldView-3 SWIR | 3.7 m SWIR, 12 km swath, commercial (Quemada 2018; Hively 2021) | Not public |
| Landsat Next, now "Landsat 10" | USGS and NASA pages: expected launch 2031; 26 bands (21 VSWIR + 5 thermal) versus 11 on Landsat 8/9; 10-20 m for visible to SWIR; crop residue / non-photosynthetic vegetation listed as an application; draft spacecraft RFP posted 18 May 2026. Lamb et al. 2022 recommended band centres 2036 (+/-5), 2097 (+/-14) and 2214 (+/-11) nm for a CAI-type residue index | Future |
| CHIME (Copernicus) | SentiWiki: CHIME-A working launch date 2028, CHIME-B planned 2030; 30 m; 400-2500 nm, more than 200 bands, < 10 nm; 130 km swath; 22-day revisit with one satellite, 11 with two | Future |
| SBG (NASA) | NASA page (updated 9 Mar 2026): "NASA has initiated a new study for the Surface Biology and Geology (SBG) Designated Observable"; no launch date given | Uncertain |

Line for the pitch (how it could be developed further): the broadband proxy we use today has a known ceiling (NDTI R2 0.44-0.84); Landsat 10 and CHIME will carry the cellulose bands that reach R2 0.8-0.94 (SINDRI, CAI), and EMIT already lets us calibrate the proxy against a spectrometer.

---

## 10. A concrete, robust residue feature set for Sentinel-2 / HLS

Design rules derived from the sources
1. Gate the scenes: cloud/shadow free; NDVI < 0.3 (Daughtry 2005 threshold used by Hively, Beeson, Zheng); no snow; no more than 3 mm of rain in the previous 2 days (Beeson 2020) or scene more than 2 days after rain (Gelder 2009). Any gridded daily precipitation product works (OpTIS uses PRISM; Beeson used NEXRAD).
2. Take the first valid scene after the detected cut date, plus the minimum over the first two or three valid scenes within about 21 days (minimum sheds moisture and regrowth inflation; first scene sheds tillage). Store the lag in days.
3. Never use absolute NDTI across regions. Scale within the scene and soil group.
4. Average over the field interior (buffer 20-30 m inward; B11 and B12 are 20 m pixels, HLS is 30 m).
5. Keep NDVI and NDMI of the same scene as covariates, plus raw band reflectances (Hively 2019: single bands carry the signal when wet).
6. Missing is allowed and informative.

Features (one row per field)

| Name | Definition | Expected direction (Inference unless sourced) |
|---|---|---|
| ndti_post_first | field-median NDTI = (B11 - B12)/(B11 + B12) on the first valid scene after the cut | silage low (about 0.01-0.08 dry), grain high (about 0.10-0.16) |
| ndti_post_min3 | minimum of the first three valid post-cut scenes within 21 days | same, less moisture bias |
| rc_pseudo | Beeson scaling: 85 x (NDTI - NDTImin)/(NDTImax - NDTImin), with NDTImin/max = mean -/+ 3 SD (or 2nd/98th percentile) of valid harvested cropland pixels in the same tile-date and soil group | silage below about 30, grain above about 60; thresholds match the standard 30% and 60% conservation-tillage lines |
| ndti_rel_z | ndti_post_first minus the median of harvested corn fields in the same tile-date within about 25-50 km, divided by their MAD | cancels scene-wide moisture, calibration and soil-region offsets |
| d_ndti_cut | ndti_post_first minus NDTI of the last clear scene before the cut | silage: large drop from the green-canopy value; grain: small change (standing dry corn is already NPV). Magnitudes to be measured on labelled fields |
| ndri_post (or srndi) | (B4 - B12)/(B4 + B12) | independent pairing; best index in Ding 2020 |
| ndi7_post | (B8A - B12)/(B8A + B12) | independent pairing; about 0.72 R2 in Li 2025 |
| bright_post_rel | post-cut mean of B4 and B8A minus the field's own bare-soil value (spring pre-emergence scene) or minus neighbours | residue brighter than dark soil; sign flips on light soils |
| ndvi_post, ndmi_post | same scene as ndti_post_first | gate and covariates (green cover, moisture) |
| regreen_30d | NDVI gain within 30-45 days after the cut | cover crop / winter forage after silage |
| lag_days, n_valid_post | days from cut to the scene used; number of valid scenes in 30 days | QA; Beeson: fewer than four useful dates is unreliable |
| wet_flag | rain > 3 mm in prior 2 days, or post-cut B11 reflectance far below neighbours, or Sentinel-1 VV jump | marks scenes where NDTI is inflated |
| residue_missing | 1 if no valid scene within 30 days | late grain harvests will dominate this |

Sketch (pure numpy/pandas logic, sensor-agnostic):

```
valid = (~cloud) & (~snow) & (ndvi < 0.30) & (rain_2day_mm <= 3.0) & (date > cut_date) & (date <= cut_date + 30d)
first = valid scenes sorted by date, take [0]
ndti_post_first = median_interior(ndti[first])
ndti_post_min3  = min(median_interior(ndti[s]) for s in first 3 valid scenes within 21 d)
# per tile-date scaling (Beeson, Daughtry, Wallander 2020)
pool = harvested cropland pixels of the same tile-date and soil group with ndvi < 0.30
lo, hi = pool.mean() - 3*pool.std(), pool.mean() + 3*pool.std()
rc_pseudo = clip(85 * (ndti_post_first - lo) / (hi - lo), 0, 100)
d_ndti_cut = ndti_post_first - median_interior(ndti[last clear scene before cut])
```

How to use it in the transparent rule (third question, only for early cuts):
- early cut AND rc_pseudo < 30 (or NDVI < 0.25-0.35 and NDTI < 0.05-0.075, the published dry-bare-soil thresholds of Castaldi 2019 and Dvorakova 2023) -> silage-like;
- early cut AND rc_pseudo > 60 on a valid dry scene -> early grain (the Texas case, high-moisture corn);
- anything else, or residue_missing = 1 -> leave to the timing and green-at-cut questions and to the calibrated model; send to "needs review" when timing and residue disagree.

Caveat on the scaling: Beeson's method assumes every scene contains both low- and high-residue fields. That holds in the autumn Corn Belt; in a silage-dominated California scene high-residue corn fields are rare, so pool all harvested cropland or fall back to the absolute dry-bare-soil thresholds.

---

## 11. What this means for Kernel

Build tonight
1. Implement the gated, relative "ground left" feature set of section 10 from HLS or Sentinel-2 L2A. It is cheap: two extra bands and a per-tile-date normalisation.
2. Replace "NDTI/STI" in the plan with "NDTI plus one red- or NIR-to-SWIR2 index plus relative brightness". NDTI and STI are the same number.
3. Use residue as the "early is not silage" tie-breaker, not as a primary question, and never let low residue alone turn a late-cut field into silage.
4. Carry residue_missing, lag_days and n_valid_post into the model and into the evidence card ("ground left: observed 6 days after cut on a dry scene" versus "not observable: next clear scene was 34 days later").
5. If Earthdata credentials are available, run the EMIT cross-check on one or two granules (section 9.1) and put the scatter and one map on a slide.
6. Have the Index Scout agent group candidate indices by band pair before ranking, and report that only about four independent signals exist.

What contradicts or sharpens plan v2
- "Ground left = post-harvest residue (NDTI/STI)" is under-specified. Without gating, a freshly irrigated or rained-on bare field reads as full cover (Quemada 2018: > 100% in five of eight fields) and a field with emerging winter forage reads above full cover (Hively 2018: 0.221 versus 0.153).
- OpTIS cannot serve as a field-level feature or as labels: public data are Crop Reporting District and HUC8 aggregates for 2015-2021, describe residue at spring planting, and agree with roadside estimates only at R2 0.47. At most it is a regional prior on how common tillage is.
- SAR-optical fusion for residue is not worth build time (three independent studies show little or no gain); keep SAR for timing.
- Residue does not date a grain harvest (standing dry corn is already NPV), so it cannot replace the radar change point; it complements it.

What to say to USDA statisticians
- "Our fourth number follows the USDA ARS / ERS protocol of Beeson, Daughtry and Wallander (2020): scenes with rain above 3 mm in the prior two days or NDVI above 0.3 are discarded, NDTI is scaled within each scene, and a field needs enough valid dates. That method was checked against ARMS field-level responses: 61-67% raw agreement on the 30% residue line, 85% (kappa 0.66) with crop-specific scaling and more than four overpasses."
- "We do not claim to measure residue percent. Broadband residue estimates carry 12-23 points of error. We only ask which end of a 60-80 point gap a field is on: about 15% after a silage chopper versus 80-95% after a combine (Iowa State PM 1901a; NRCS)."
- "Where it fails: wet or irrigated ground, regrowth and cover crops, fields tilled, baled or plowed before the first clear scene, high-chop silage, snow, and late harvests with no clear scene. In those cases the feature is reported as not observed, and the field leans on timing and green-at-cut."
- "How it improves: NASA's EMIT spectrometer already gives a 60 m non-photosynthetic-vegetation fraction we can calibrate against, and Landsat 10 (2031) and CHIME (2028-2030) will carry the cellulose bands."

---

## 12. Leads checked, and what was not done

| Lead from the brief | Status |
|---|---|
| Zheng et al. minNDTI | Confirmed (dissertation containing the 2012 and 2013 papers opened): R2 0.89; CRC = 754.7 x minNDTI + 5.4; multi-site R2 0.56-0.93 |
| OpTIS public data | Confirmed but limited: CRD and HUC8 only, 2015-2021, spring residue; validation R2 0.467 |
| Azzari 2019 | Confirmed through the Stanford summary and Deines et al. 2019: 75-79%, Sentinel-1 adds little; full text not opened |
| Beeson | 2020 paper opened and used; 2016 Iowa paper (J. Soil Water Conserv. 71:385-395) not opened, search snippet only (Landsat and SPOT 64-92%, AWiFS and Deimos 61-73%) |
| Hively 2018 | Confirmed, plus Hively 2019 and 2021, Lamb 2022, Lamb 2025 (summary) |
| Quemada & Daughtry; Hively corrections | Confirmed with numbers (RWC < 0.25; RMSE 23.4 to 4.5) |
| Residue after silage versus grain (UW, ISU, MSU, NRCS) | UW, ISU, NRCS and a BMP factsheet (bmpbooks.com) confirmed with numbers; the MSU page returned no content |
| Stover baling, stalk grazing | Confirmed (Nebraska 2017 via OSU summary; original PDF returned 404). A 2016 SSSA poster (35% baled, 85% grazed) seen only as a search snippet |
| SAR-optical fusion helps | Mostly refuted for residue cover |
| EMIT / EnMAP / PRISMA for a demo field | EMIT confirmed with a ready-made NPV product and verified granules; EnMAP and PRISMA archives not checked for coverage |
| Landsat Next, CHIME, SBG | Landsat Next is now Landsat 10 (2031); CHIME-A 2028 working date; SBG under a new study, no date |
| DFI, SRNDI, modified CRC | Formulas confirmed (Ding 2020; Li 2025). BSI formula not verified |
| Manure after silage | Not verified: no source found on its spectral effect |

Not done because the shared WebSearch budget ran out (22 searches completed): (1) UC ANR material on the California silage-to-winter-forage timeline, pre-irrigation and lagoon water; (2) fall-tillage rates after corn from ERS / ARMS; (3) McGill et al. 2026 on the accuracy of remote-sensing conservation data; (4) the Illinois cross-scale residue mapping work (airborne hyperspectral to Sentinel-2/HLS) from the Guan group.

---

## 13. Annotated bibliography (URLs I opened unless marked)

Residue amounts
- Lauer, J. 2002. Managing Corn Silage on Highly Erodible Land. Wisconsin Crop Manager 9(6):45-46. https://corn.agronomy.wisc.edu/WCM/W105.aspx - cutting height versus residue mass and cover table.
- Al-Kaisi, M., Hanna, M. Residue Management and Cultural Practices. Iowa State Univ. Extension PM 1901a (reviewed Sept 2009). https://www.mssoy.org/sites/default/files/documents/isu-pm1901a.pdf - Table 1 cover after harvest (grain 80-95%, silage 15%); Table 2 tillage factors.
- NRCS. Corn & Soybeans Crop Residue Management Guide (Washington eFOTG copy). https://efotg.sc.egov.usda.gov/references/public/WA/A.12_Corn&SoybeanCrop_ResidueManagementGuide.pdf - percent residue left by operation; cover-to-weight table; line-transect method (100 points on a 50 ft line, measured after planting).
- Best Management Practices: Residue Management (factsheet). https://bmpbooks.com/media/Residue-Management.pdf - "corn 85%, winter wheat 95%, soybeans 30%, silage corn 5%".
- Hendrickson, S. Evaluation of spring residue cover with winter rye as a cover crop following corn silage. UW Extension. https://extension.soils.wisc.edu/wp-content/uploads/sites/68/2016/07/Hendrickson.pdf
- Ulmer et al., 2017 Nebraska Beef Report, condensed in the OSU Beef Cattle Letter. https://u.osu.edu/beef/2018/09/12/effect-of-corn-residue-grazing-or-baling-on-subsequent-crop-yield-and-nutrient-removal - grazed 77.5%, baled 45.8%, control 88.7%.
- UNL CropWatch 2017. Crop Residue Removal: Impacts on Yield. https://cropwatch.unl.edu/2017/residue-removal-impacts-yield
- USDA ERS 2018. Tillage Intensity and Conservation Cropping in the United States, EIB-197. https://www.ers.usda.gov/publications/pub-details/?pubid=90200 - conservation tillage on 65% of corn acres in 2016.

Residue remote sensing: moisture, vegetation, band choice
- Quemada, M., Daughtry, C.S.T. 2016. Spectral Indices to Improve Crop Residue Cover Estimation under Varying Moisture Conditions. Remote Sens. 8:660. PDF: https://mdpi-res.com/d_attachment/remotesensing/remotesensing-08-00660/article_deploy/remotesensing-08-00660.pdf (the www.mdpi.com HTML page returned 403).
- Quemada, M., Hively, W.D., Daughtry, C.S.T., Lamb, B.T., Shermeyer, J. 2018. Improved crop residue cover estimates obtained by coupling spectral indices for residue and moisture. Remote Sens. Environ. 206:33-44. doi:10.1016/j.rse.2017.12.012. Copy opened: https://forum.step.esa.int/uploads/short-url/ex3dJTOzNIClA1o6DWZhTPTUArL.pdf
- Hively, W.D. et al. 2018. Mapping Crop Residue and Tillage Intensity Using WorldView-3 Satellite Shortwave Infrared Residue Indices. Remote Sens. 10:1657. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-10-01657/article_deploy/remotesensing-10-01657.pdf
- Hively, W.D. et al. 2019. Mapping Crop Residue by Combining Landsat and WorldView-3 Satellite Imagery. Remote Sens. 11:1857. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-11-01857/article_deploy/remotesensing-11-01857.pdf
- Hively, W.D. et al. 2021. Evaluation of SWIR Crop Residue Bands for the Landsat Next Mission. Remote Sens. 13:3718. https://ntrs.nasa.gov/api/citations/20220003090/downloads/remotesensing-Eval%20of%20SWIR%20Crop.pdf
- Lamb, B.T. et al. 2022. Optimizing Landsat Next Shortwave Infrared Bands for Crop Residue Characterization. Remote Sens. 14:6128. https://ntrs.nasa.gov/api/citations/20230014116/downloads/remotesensing-14-06128-v3.pdf
- Lamb, B.T. et al. 2025. Multiyear crop residue cover mapping using narrow-band vs. broad-band shortwave infrared satellite imagery. Soil and Tillage Research, doi:10.1016/j.still.2025.106524. Summary opened: https://www.usgs.gov/publications/multiyear-crop-residue-cover-mapping-using-narrow-band-vs-broad-band-shortwave ; data release (CC0, 895 photos, rasters): https://www.usgs.gov/data/crop-residue-cover-field-photographs-worldview-3-spectral-indices-and-derived-residue-maps
- Daughtry, C.S.T. et al. 2001. Assessing the spatial distribution of plant litter. AVIRIS workshop. https://avng.jpl.nasa.gov/pub/docs/workshops/01_docs/2001Daughtry_web.pdf
- Castaldi, F. et al. 2019. Soil Organic Carbon Mapping Using LUCAS Topsoil Database and Sentinel-2 Data: An Approach to Reduce Soil Moisture and Crop Residue Effects. Remote Sens. 11:2121. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-11-02121/article_deploy/remotesensing-11-02121.pdf

Multi-temporal and operational residue / tillage mapping
- Zheng, B. 2012. Broad-scale Assessment of Crop Residue Management Using Multi-temporal Remote Sensing Imagery. PhD dissertation, Virginia Tech (contains Zheng, Campbell, de Beurs 2012, Remote Sens. Environ. 117:177-183, and the 2013 validation paper). https://vtechworks.lib.vt.edu/items/cfa205bf-f6e6-4bc5-a63f-bf3973364f5e (PDF: https://vtechworks.lib.vt.edu/bitstreams/70ce3a35-5077-4e5a-b45d-164f81d963b2/download)
- Beeson, P.C., Daughtry, C.S.T., Wallander, S.A. 2020. Estimates of Conservation Tillage Practices Using Landsat Archive. Remote Sens. 12:2665. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-12-02665/article_deploy/remotesensing-12-02665.pdf
- Hagen, S.C. et al. 2020. Mapping Conservation Management Practices and Outcomes in the Corn Belt Using the Operational Tillage Information System (OpTIS) and the DNDC Model. Land 9:408. https://mdpi-res.com/d_attachment/land/land-09-00408/article_deploy/land-09-00408-v2.pdf
- CTIC OpTIS page. https://ctic.org/OpTIS ; CTIC "Viridis View" RFP, 10 Feb 2026. https://ctic.org/wp-content/uploads/2026/02/CTIC-Conservation-Trend-Data-RFP-FINAL.pdf
- Azzari, G. et al. 2019. Satellite mapping of tillage practices in the North Central US region from 2005 to 2016. Remote Sens. Environ. 221:417-429. Summary opened: https://fse.fsi.stanford.edu/node/28524 . Described in Deines, Wang, Lobell 2019, Environ. Res. Lett. 14:124038. https://iopscience.iop.org/article/10.1088/1748-9326/ab503b/meta

Sentinel-2-specific residue studies
- Li, J. et al. 2025. Comparative Analysis of Tillage Indices and Machine Learning Algorithms for Maize Residue Cover Prediction. Remote Sens. 17:105. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-17-00105/article_deploy/remotesensing-17-00105.pdf
- Ding, Y. et al. 2020. A Comparison of Estimating Crop Residue Cover from Sentinel-2 Data Using Empirical Regressions and Machine Learning Methods. Remote Sens. 12:1470. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-12-01470/article_deploy/remotesensing-12-01470.pdf
- Memon, M.S. et al. 2023. Evaluating the Efficacy of Sentinel-2B and Landsat-8 for Estimating and Mapping Wheat Straw Cover in Rice-Wheat Fields. Agronomy 13:2691. https://mdpi-res.com/d_attachment/agronomy/agronomy-13-02691/article_deploy/agronomy-13-02691.pdf (abstract only readable)
- Not opened (HTTP 403): Maize crop residue cover mapping using Sentinel-2 MSI data and random forest algorithms, Int. Soil and Water Conservation Research. https://www.sciencedirect.com/science/article/pii/S2095633924000698

SAR and fusion
- Liu, Y. et al. 2022. Using Sentinel-1, Sentinel-2, and Planet satellite data to map field-level tillage practices in smallholder systems. PLoS One 17(11):e0277425. https://pmc.ncbi.nlm.nih.gov/articles/PMC9704639/
- Wang, S. et al. 2024. Detecting Field-level Crop Residue Cover across the EU Using Multi-source Satellite Data and Explainable Machine Learning. EGU24-14253. https://meetingorganizer.copernicus.org/EGU24/EGU24-14253.html
- Borio, D. et al. 2025. Detection of Tillage Practices using Sentinel-1 and 2. JRC143611. https://publications.jrc.ec.europa.eu/repository/handle/JRC143611

Silage versus grain classification
- Silage Maize Identification Using a Temporal Difference-Based Model with Sentinel-2 Data: Insights from a Harvest-Based and Temporally Transferable Approach. Agronomy 2025, 15:1438. https://mdpi-res.com/d_attachment/agronomy/agronomy-15-01438/article_deploy/agronomy-15-01438.pdf

Hyperspectral data and missions
- EMIT L2B Fractional Cover and Uncertainty 60 m V002. https://www.earthdata.nasa.gov/data/catalog/lpcloud-emitl2bfrcov-002 ; ATBD https://github.com/emit-sds/emit-sds-frcov/blob/develop/docs/EMIT_L2B_Fractional_Cover_ATBD.md ; user guide https://github.com/emit-sds/emit-sds-frcov/blob/develop/docs/EMIT_L2B_Fractional_Cover_User_Guide.md ; CMR search endpoint https://cmr.earthdata.nasa.gov/search/granules.json
- EnMAP. https://www.enmap.org/mission/ and https://www.enmap.org/data_access/
- PRISMA. https://www.asi.it/en/earth-science/prisma/
- Landsat 10 (formerly Landsat Next). https://www.usgs.gov/landsat-missions/landsat-10 and https://science.nasa.gov/mission/landsat/landsat-next/
- CHIME. https://sentiwiki.copernicus.eu/web/chime
- SBG. https://science.nasa.gov/earth-science/decadal-surveys/decadal-sbg/
- HLS S30 and L30 v2.0. https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlss30-2.0 and https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlsl30-2.0
