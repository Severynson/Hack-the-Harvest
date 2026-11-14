# Gap: is there a downloadable 2026 in-season crop map to use as the corn mask?

Research note for team Kernel, Hack the Harvest. Written Saturday 2026-11-14 (afternoon, Pacific).

## 0. How this was produced, and its limits

- 20 web searches, about 45 pages or files opened, plus three primary data files parsed directly (two FSA workbooks, one WMS capabilities document).
- Convention: plain statements are what the source shows. Anything I derived is prefixed **Inference:**. Numbers I computed myself from a primary file are marked **Computed**.
- PDFs that the fetch tool could not parse (NASS-hosted papers) were read by extracting their text locally. Nothing was installed.
- **Two things I could not do.** (1) I could not test the actual download of the 2026 in-season map. The portal needs a sign-in, and this session's permission policy blocked my follow-up requests to the George Mason server after the first one. A human has to sign in and try. (2) I could not open the full text of Johnson and Mueller 2021 (ScienceDirect returns 403); only its abstract.
- Leads from the brief were treated as unverified. Section 10 lists which were confirmed and which were refuted.

## 1. Bottom line

1. **Yes, a 2026 in-season crop-type map of the US exists.** George Mason University's In-season Cropland Data Layer (ICDL) is served for June, July and August 2026. The public map service lists layers `cdl_2026_06`, `cdl_2026_07`, `cdl_2026_08` (18 layers in all, June to August for 2021 to 2026). Download goes through the CropSmart portal, which needs a free registration. The older portal address cited in the papers (`cloud.csiss.gmu.edu/icrop/`) now returns 404.
2. **It is not a NASS product and it is not the CDL.** It is a random forest trained on labels inferred from past CDLs, with no current-year ground truth. A review co-authored by NASS staff says the product is "already in operation" and "by August ... is expected to reach 80 %-90 % agreement with CDL".
3. **Reported corn accuracy by month** (field polygons in Nebraska and Iowa only, 2022 and 2023): June F1 0.79 to 0.96, July 0.88 to 0.99, August 0.93 to 0.99. No validation exists for California, Idaho, Wisconsin, New York or Pennsylvania.
4. **An independent test is less flattering.** For July 2023, state corn acres from the ICDL were off by -56% to +18% against NASS (North Dakota -29%, Minnesota -22%, Kansas +18%), versus 0 to +12% for a newer open model and -4 to +5% for the final CDL.
5. **NASS itself publishes nothing for 2026.** The 2025 CDL came out on 2026-02-27; the FAQ describes in-season CDL estimates as internal.
6. **New data source found on the way: FSA's 2026 crop acreage file, released 2026-11-10.** It gives corn acres for 2,589 counties, split by the use the farmer reported (grain, silage, seed and others). Total 95.24M acres, which is 98.4% of NASS's 96.78M planted. This is the acreage denominator for a 2026 rollup, and it does not depend on any pixel mask.
7. **FSA "silage" is only 47% of the silage NASS later finds** (2025: 2.92M reported versus 6.21M harvested). In dairy-specialist states FSA sees 93% of it. In the Corn Belt and Lakes states it sees 27%: Kansas 0.1%, Ohio 8%, Illinois 10%, South Dakota 11%, Iowa 12%. That gap is the acreage only a harvest-time signal can find.

**Decision for tonight:** try the ICDL download first (30 minutes, one person). In parallel, build the rollup as a ratio estimate on FSA county corn acres, so the 2026 number stands even if the map download fails.

## 2. Candidates checked

| Candidate | 2026 available? | Resolution | Access | Corn accuracy reported | Verdict |
|---|---|---|---|---|---|
| GMU ICDL via CropSmart | **Yes**: June, July, August 2026 layers listed | 30 m on the portal; 10 m on Zenodo for 2022 and 2023 only | Free sign-in at `cloud.csiss.gmu.edu/cropsmart`; download not tested | June F1 0.79-0.96, July 0.88-0.99, August 0.93-0.99 (Nebraska, Iowa) | Use, after measuring it against CDL 2025 |
| Open Transformer model on HLS (Zhang et al. 2025) | No map; model and code are public, we would run it | 30 m | GitHub + Zenodo (model file 69.9 MB) | Corn F1 above 0.8 by May 11, 2023; state corn bias 0 to +12% in July | Fallback for a few tiles on the Brev GPU |
| NASS CDL 2026 | No. Expected early 2027 | 10 m | n/a | CDL 2025: corn producer's 92.2%, user's 91.2% | Not available |
| NASS CDL 2025 carried forward | It is last year's map | 10 m | NASS download | n/a for 2026 | Wrong fields in rotation country; use only as history |
| NASS ACTIVE viewer | No. It is a viewer for existing CDLs | n/a | Earth Engine app | n/a | Not a mask |
| UMD GLAD maize/soybean | No. 2019 to 2022 only | 10 m | COG files | Maize user's above 91%, producer's above 84% | Not for 2026 |
| CropSight-US (ESSD 18:3069) | No. Ground-truth objects, 2013 to 2023 | field objects | Zenodo | 97.2% label accuracy | Not a map |
| Zenodo 17457566 | No. June to August 2023 | 10 m | 45.3 GB | see ICDL | Backtest material only |
| California DWR statewide crop map | No. Newest found is water year 2023 (search summary only, page not opened) | field polygons | state portal | not checked | Not for 2026 |
| FSA crop acreage data | **Yes**: as of Nov 10, 2026 | county table, not a map | 23.8 MB zip | administrative, 98.4% of NASS planted | Use as the acreage denominator and as a prior |

## 3. The ICDL in detail

### 3.1 What it is

- Producer: Center for Spatial Information Science and Systems, George Mason University (Hui Li, Liping Di, Chen Zhang and others). The NASS-co-authored review that describes it acknowledges grants from NSF, USDA NIFA (#2021-67021-34151, #2024-68016-14561) and USDA NASS (#58-3AEU-7-0080).
- Method (Scientific Data 13:750, 2026): training labels come from "stable crop rotation patterns" in six years of CDL history. Two patterns are used: the same crop for six years, or a crop grown every other year. Historical CDL 2016-2021 labels 2022; 2017-2022 labels 2023.
- Classifier: random forest, 100 trees per tile, 1,000 stratified random samples per land-cover class per tile.
- Inputs: Blue, Green, Red, NIR, SWIR1, SWIR2, NDVI, NDWI, stacked as a time series from May to the mapping month. Sentinel-2 and Landsat 8/9 are classified separately; Sentinel-2 is preferred in the mosaic.
- Legend: pixel values "consistent with the CDL classification scheme".
- Schedule: the workflow runs "at the beginning of July, August, and September"; maps are generated "by July 5, August 5, and September 5". The abstract says public delay is "only 5 days". The window was moved from May-July to June-August "to better align with the peak growing season".
- Archived files: `Inseason2023June10m.tif` 16.3 GB, `Inseason2023July10m.tif` 14.9 GB, `Inseason2023Aug10m.tif` 14.2 GB (Zenodo 17457566, CC BY 4.0, EPSG:5070). 2022 files are in Zenodo 17494692 and 17456018.

### 3.2 Is 2026 really there? Evidence

| Evidence | What it shows | Status |
|---|---|---|
| Map service capabilities document `https://cat.csiss.gmu.edu/cgi-bin/wms_cdl_icrop?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1`, retrieved 2026-11-14 | Service title "In-season Cropland Data Layer WMS Service". Layer names: `cdl_2026_08`, `cdl_2026_07`, `cdl_2026_06`, then the same three months for 2025, 2024, 2023, 2022, 2021 | Opened. Layers are listed; I did not render or download them |
| CropSmart web application code (public) | Layer type "In-season Crop Cover Layer"; the download button builds a file name of the form `<year><June|July|August>CropMap30m.tif`, with an area-of-interest clip option; pre-season and May layers show "No downloadable data exists" | Opened. Download itself not tested |
| CropSmart sign-in page text | "CSISS's system data are openly available to all and free of charge." Registration is required | Opened |
| Zhang, C. et al. 2025, RSE 330:114995, co-authored by six NASS staff, hosted on nass.usda.gov | "The production of ICDL is already in operation." "The current year's data is released as early as June and updated monthly through August on iCrop." "By August, the provisional data product is expected to reach 80 %-90 % agreement with CDL." | Opened, full text |
| Li et al. 2026, Scientific Data 13:750 | Automatic runs each July, August, September; "annual maps can also be accessed through the online system http://cloud.csiss.gmu.edu/cropsmart" | Opened |
| Old portal `https://cloud.csiss.gmu.edu/icrop/` | HTTP 404 | Opened; dead |

**Inference:** the 2026 August map was produced around September 5, 2026 and is on the portal. Confidence that the layers exist: high. Confidence that a whole-country or county clip downloads cleanly tonight: medium, untested.

### 3.3 Corn accuracy by month (Scientific Data 13:750, Table values)

Reference: ground-truth field polygons, 313 in 2022 (Nebraska and Iowa) and 205 in 2023 (Nebraska). UA = user's accuracy (1 minus commission), PA = producer's accuracy (1 minus omission). The "CDL" rows are the final CDL scored on the same polygons.

| Year, state | Map | Corn UA | Corn PA | Corn F1 | Overall accuracy in the same row |
|---|---|---|---|---|---|
| 2022 Nebraska | June | 0.673 | 0.952 | 0.789 | 0.807 |
| 2022 Nebraska | July | 0.800 | 0.970 | 0.877 | 0.856 |
| 2022 Nebraska | August | 0.887 | 0.967 | 0.925 | 0.927 |
| 2022 Nebraska | final CDL | 0.949 | 0.997 | 0.972 | 0.916 |
| 2022 Iowa | June | 0.952 | 0.961 | 0.956 | 0.949 |
| 2022 Iowa | July | 0.988 | 0.979 | 0.983 | 0.972 |
| 2022 Iowa | August | 0.985 | 0.982 | 0.983 | 0.978 |
| 2022 Iowa | final CDL | 0.970 | 0.976 | 0.973 | 0.976 |
| 2023 Nebraska | June | 0.850 | 0.937 | 0.891 | 0.906 |
| 2023 Nebraska | July | 0.994 | 0.988 | 0.991 | 0.983 |
| 2023 Nebraska | August | 0.997 | 0.991 | 0.994 | 0.984 |
| 2023 Nebraska | final CDL | 0.979 | 0.988 | 0.983 | 0.976 |

I recomputed F1 from UA and PA for four rows; they match.

Other numbers from the same paper:

- Training-label accuracy for corn: Nebraska 2022 UA 0.811, PA 0.902; Iowa 2022 UA 0.939, PA 0.876; Nebraska 2023 UA 0.990, PA 0.931.
- National corn acres from the August map against NASS: -0.3% (2022) and -0.8% (2023). The final CDL was +1.3% and +1.1%.
- Largest state corn deviations: Kansas -9.5% in 2022; Minnesota -9.4% and Missouri -7.4% in 2023. (One reading of the paper also lists Minnesota -7.7% in 2022.)
- Stated limits: accuracy is uneven across space, time and crop; label quality is uneven because fixed rotation patterns are used everywhere; "variability in satellite imagery quality constrains classification performance in some states, such as Wisconsin and North Dakota".
- **No validation in any dairy state.** Pixel-level validation is Nebraska and Iowa only.

Earlier version (Li et al. 2024, IEEE TGRS 62:4403214, abstract): May, June, July 2022 maps; July corn F1 0.911 (Nebraska) and 0.845 (Iowa). A third party describes that version as 60% to 76% for major crops in May and 81% to 95% in July.

### 3.4 An independent test of the ICDL (Zhang, H.K. et al. 2025, RSE 329:114950)

Authors are at South Dakota State, NASS (Zhengwei Yang), George Mason and Michigan State. The paper compares its own model with the July 2023 ICDL.

State corn planted acres, July 2023, relative difference from NASS statistics (their Table 4):

| State | NASS (10,000 acres) | Transformer | ICDL July | Final CDL |
|---|---|---|---|---|
| North Dakota | 405 | 0% | -29% | -3% |
| Minnesota | 860 | +7% | -22% | +3% |
| South Dakota | 630 | +5% | +7% | +3% |
| Iowa | 1310 | +6% | +2% | -2% |
| Nebraska | 995 | +6% | +13% | +5% |
| Kansas | 575 | +12% | +18% | -1% |
| Missouri | 385 | +11% | -8% | -2% |
| Oklahoma | 39 | +7% | -54% | 0% |
| Arkansas | 85 | +8% | -56% | -4% |

- County crop acres against the final CDL: Transformer 0.96 <= R2 <= 1.00, ICDL 0.86 <= R2 <= 0.96 (six crops, nine states).
- "the ICDL consistently had lower R2 than the 2022 CDL when compared against the 2023 CDL". In plain words: for county acreage, last year's CDL beat the July in-season map.
- Visual problems noted: "a horizontal artificial line in the ICDL map in July", distinct patterns at state boundaries, poor performance in complex landscapes.
- "sweet corn was easily confused with corn".

**Inference:** the two sources do not contradict each other. The July 2023 map of the older pipeline was weak outside the core Corn Belt. The August maps of the newer 10 m pipeline are much better where they were tested. Which pipeline produced the 30 m 2026 files on the portal is not stated anywhere I could open. So the mask must be measured, not assumed (section 9, step 3).

## 4. The open Transformer model as a fallback

Source: Zhang, H.K. et al. 2025, RSE 329:114950 (open access, CC BY).

- Trained on more than 1 million pixel time series, 2016 to 2022, labels from the CDL, 37 crop types, 30 m NASA Harmonized Landsat Sentinel-2 (HLS) data. No compositing: every good observation is used; missing dates are masked in attention.
- Needs two years of HLS as input: the previous year and the current year up to the mapping date.
- Tested on 2023 against the 2023 CDL, with test pixels at least 1.8 km from training pixels.
- Corn reaches F1 above 0.8 by **May 11**, 2023. Soybean May 31, cotton and rice May 26, spring wheat June 25, winter wheat January 6.
- F1 above 0.8 for 15 crop classes by June 30, 20 by July 31, 23 by August 31.
- The date at which corn and soybean reach F1 0.8 moves with latitude: about May 18 in the south, about July 17 in the north.
- "achieved comparable accuracy but one month earlier than publicly available USDA NASS ICDL products".
- Code: `https://github.com/hankui/In-season-crop-type-mapper` (Apache-2.0, TensorFlow). Run: `Pro_load_model_run_tile_v5_1.py [Input_dir] [Output_dir] [HLS_tile] [year] [day_of_year] [batch_size]`; tile names start with "T" (for example T14TPP); default batch 2048.
- Model and samples: `https://zenodo.org/records/14715402`. Model file `v1_70.layer4.METHOD2.BATCH64.LR0.0002.EPOCH30.L20.1.i0.model.h5` is 69.9 MB. Training archives are 8.4 GB and 5.7 GB and are not needed for inference.

**Inference:** this is runnable on a Brev GPU for a handful of HLS tiles (one tile is about 110 km by 110 km). The cost is downloading two years of HLS for each tile. It was only tested for 2023; 2026 would be its fourth year out of training.

## 5. What NASS publishes (verified again today)

| Item | What the source shows | Source |
|---|---|---|
| 2025 CDL | Publication date 2026-02-27, "2025 Edition", 10 m, imagery 2024-10-01 to 2025-12-31, Landsat 8/9 and Sentinel-2A/2B | CDL 2025 metadata |
| CDL corn accuracy 2025 | Producer's 92.2%, user's 91.2% (national) | CDL 2025 metadata |
| Overall | "75.4% OVERALL CROP ACCURACY, 24.6% ERROR, 0.712 KAPPA" | CDL FAQ |
| Release history | 2025 CDL on Feb 27, 2026; 2024 CDL on Feb 27, 2025; 2023 CDL on Jan 31, 2024 | CDL FAQ |
| In-season product | None public. "the internal CDL acreage estimates ... are not simple pixel counting but regression estimates using NASS survey data" | CDL FAQ |
| Pixel counting | "Pixel counting is usually downward biased when compared to the official estimates." | CDL FAQ |
| Classes | Corn (1), Sweet Corn (12), Pop or Orn Corn (13). No silage class | CDL FAQ |
| Cropland page | Lists the 2025 release, a Hawaii CDL (June 12, 2026), the ACTIVE viewer. No 2026 or in-season product | NASS Cropland page |
| ACTIVE | "Agricultural Cropland Tracking & Interactive Visualization Environment", an Earth Engine app "developed at USDA NASS that allows rapid visualization of CDL and crop-specific land cover changes" | RSE 330:114995 |
| Future | "Planning is underway to incorporate these advancements into future operational in-season products." | RSE 330:114995 |

**Inference:** the CDL for 2026 will appear in late January or February 2027.

## 6. How good is a mask built from history alone?

This is the fallback the nowcast note proposed. Three sources now put numbers on it.

### 6.1 Abernethy, Beeson, Boryan, Hunt, Sartore 2023 (NASS; Computers and Electronics in Agriculture 208:107768), full text opened

Pre-season prediction of the coming year's crop from CDL history only, on Crop Sequence Boundary polygons (LightGBM, the "FIELD LGB" column of their Tables 4 to 6), scored against FSA planted-area ground reference. Corn F1 for the field model:

| State | 2016 | 2017 | 2018 |
|---|---|---|---|
| Iowa | 88.5% | 88.4% | 89.5% |
| Illinois | 86.1% | 85.9% | 86.7% |
| Nebraska | 83.8% | 83.2% | 84.1% |
| Minnesota | 83.2% | 82.9% | 84.0% |
| Indiana | 83.1% | 82.9% | 82.6% |
| Ohio | 77.1% | 76.4% | 75.7% |
| Missouri | 72.5% | 75.2% | 76.9% |
| Louisiana | 41.0% | 41.8% | 53.5% |

- The eight states were chosen because CDL principal-crop accuracy was at least 89.5% every year from 2008 to 2016. They are the easy states.
- "All models perform less well in states with more than two major crops."
- No dairy state other than Minnesota is in the study.

### 6.2 Johnson and Mueller 2021 (NASS; RSE 264:112576), abstract only

- Region: Corn Belt and Great Plains. Ten years of 30 m CDL plus Landsat 7/8 and Sentinel-2A/2B. Random forest on Earth Engine. Runs made monthly from April. Tested on 2020 in 50 randomly sampled counties against the 2020 CDL.
- CDL history alone, by midsummer: "corn and soybean consumer and producer agreement above 70% and winter wheat just below 50%".
- Early imagery-based maps were worse, "but improved significantly by July".
- Best case, CDL plus a full season of imagery: "At that point in late September, the corn and soybean agreements were around 85% and winter wheat near 70%."
- **The month-by-month corn table was not opened** (ScienceDirect 403; no open copy found on nass.usda.gov, Agris or Semantic Scholar).

### 6.3 Posch, Kumar, Hoffman, Ganguly 2026 (arXiv 2606.05731), abstract page opened

- HLS time series plus rotation history, 30 m, mapping by early June, in years unseen in training. Ten algorithms, thousands of configurations, year-wise cross-validation.
- Best model (support vector machine): mean F1 **0.59 for Iowa corn** and 0.74 for California almonds over five unseen years.
- "Interannual variation was a major source of uncertainty."
- Not a data product. No map is released.

**Inference:** history alone gives corn F1 of roughly 0.83 to 0.90 in the core Corn Belt and far less elsewhere. Adding current-year imagery through August lifts that to roughly 0.85 to 0.99 depending on place and method. Early June is too early. For a mask needed as of September 1, the August ICDL or an August run of the Transformer sits on the plateau.

### 6.4 Why last year's map is the wrong mask

- USDA ERS (ARMS data): "only about 18 percent of cropland planted to corn in 2010 was in corn continuously over the previous 3 years". The corn-soybean rotation accounts for "the majority of corn and soybean acreage".
- Zhang, H.K. et al. 2025: county crop acres barely move between years (2022 CDL versus 2023 CDL, R2 above 0.95) even though fields rotate.

**Inference:** county totals persist, field identities do not. That is the argument for a ratio estimate: take the acreage from an official table, take only the silage share from the fields we can see.

**Inference (bias warning):** fields that are corn in both 2025 and 2026 are not a random sample of 2026 corn. Continuous corn is common on dairy ground (California double-crops corn after winter forage every year). A mask of "corn last year" will over-sample silage fields and inflate the silage share.

## 7. New data source: FSA crop acreage data, 2026 crop year

### 7.1 What it is

- Page: `https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/frequently-requested/crop-acreage-data`
- 2026 files posted: as of August 12, September 11, October 9 and November 10, 2026. A December 10, 2026 file is scheduled.
- For 2025 the page says: "October 9, 2025 - Crop Acreage Reports were not released due to the Government Shutdown", and the same for November 10, 2025. The 2025 files are August 1, September 12, December 9, 2025 and January 12, 2026.
- Latest file: `https://www.fsa.usda.gov/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip` (23.8 MB) containing `2026_fsa_acres_web_110526.xlsx`.
- Sheets: `plant_and_fail`, `prevent`, `county_summary`, `crop_summary`, `county_data`, `all_farm_count`.
- `county_data` title: "2026 ACRES BY COUNTY BY CROP, CROP TYPE, INTENDED USE, AND IRRIGATION PRACTICE REPORTED TO FARM SERVICE AGENCY". 202,466 rows.
- Columns: State Code, County Code, Crop Code, State, County, State County Code, Crop, Crop Type, Intended Use, Irrigation Practice, Planted Acres, Volunteer Acres, Failed Acres, Prevented Acres, Not Planted Acres, Planted and Failed Acres.
- The page states: "the National Agricultural Statistics Service uses FSA planted acreage data to complement their survey data".

### 7.2 Corn in the 2026 file (**Computed** from `county_data`, rows where Crop = CORN)

| Intended use | Planted acres | Share | Failed | Prevented |
|---|---|---|---|---|
| Grain | 91,165,479 | 95.72% | 145,781 | 1,286,979 |
| Silage | 2,885,863 | 3.03% | 2,632 | 94,062 |
| Seed | 805,955 | 0.85% | 846 | 196 |
| Processed | 254,402 | 0.27% | 4 | 261 |
| Fresh | 119,271 | 0.13% | 93 | 60 |
| Grazing | 8,044 | 0.01% | 0 | 0 |
| Left Standing | 3,668 | 0.00% | 0 | 0 |
| **All corn** | **95,242,688** | 100% | | |

- 2,589 counties report corn. 1,409 counties report some silage-intent corn. In 266 counties silage intent is more than half of corn.
- Crop types: Yellow 97.95%, White 1.07%, Popcorn 0.25%, sweet corn types about 0.35% together.
- 95.24M acres is 98.4% of the 96,777K acres NASS carries as planted for all purposes in the November 10 report.
- Seed, processed and fresh uses add up to about 1.18M acres; popcorn (a crop type, mostly reported as grain) is another 0.24M. **Inference:** these fields are corn in a crop map but behave unlike field corn for grain, so they are a source of false silage calls (seed corn is harvested early; sweet corn is cut green).

### 7.3 FSA silage intent against NASS silage harvested, 2025 (**Computed**)

FSA: `2025_fsa_acres_web_010526.xlsx` (final file, as of January 12, 2026). NASS: Crop Production 2025 Summary, January 2026, silage area harvested. Thousand acres.

| State | NASS silage 2025 | FSA silage intent 2025 | FSA as % of NASS | FSA silage intent 2026 (Nov file) | Change 2026 vs 2025 |
|---|---|---|---|---|---|
| Wisconsin | 885 | 458.2 | 52% | 429.7 | -6.2% |
| New York | 500 | 472.3 | 94% | 495.7 | +5.0% |
| South Dakota | 390 | 42.0 | 11% | 51.7 | +23.2% |
| California | 365 | 312.8 | 86% | 282.5 | -9.7% |
| Minnesota | 360 | 63.6 | 18% | 64.4 | +1.2% |
| Michigan | 350 | 89.5 | 26% | 90.1 | +0.6% |
| Pennsylvania | 315 | 95.0 | 30% | 96.6 | +1.6% |
| Idaho | 280 | 292.6 | 104% | 286.7 | -2.0% |
| Texas | 265 | 126.2 | 48% | 117.8 | -6.7% |
| Iowa | 250 | 28.8 | 12% | 27.7 | -3.9% |
| Kansas | 230 | 0.3 | 0.1% | 6.2 | (tiny base) |
| Nebraska | 210 | 24.8 | 12% | 29.5 | +18.9% |
| Colorado | 200 | 66.1 | 33% | 47.4 | -28.3% |
| Ohio | 200 | 16.5 | 8% | 18.0 | +9.1% |
| North Dakota | 170 | 118.8 | 70% | 121.2 | +2.0% |
| Indiana | 130 | 32.1 | 25% | 30.9 | -3.6% |
| Virginia | 100 | 17.8 | 18% | 16.7 | -6.2% |
| Illinois | 90 | 8.6 | 10% | 5.5 | -36.3% |
| Washington | 89 | 68.3 | 77% | 65.1 | -4.7% |
| Vermont | 84 | 80.2 | 96% | 78.9 | -1.7% |
| **United States** | **6,208** | **2,919.2** | **47.0%** | **2,885.9** | **-1.1%** |

Groups (**Computed**):

- Dairy-specialist group (California, Idaho, New York, Vermont, Arizona, New Mexico, Washington, Nevada, Utah, Connecticut, Maine, Massachusetts, New Hampshire): NASS 1,565K, FSA 1,455K. FSA sees **93%**.
- Corn Belt and Lakes group (Iowa, Illinois, Indiana, Ohio, Minnesota, Nebraska, Kansas, South Dakota, Missouri, North Dakota, Michigan, Wisconsin): NASS 3,345K, FSA 892K. FSA sees **27%**.
- All corn reported to FSA: 97,201K acres in 2025 (final), 95,243K in 2026 (November file).

**Inference:** in the Corn Belt most silage acres are reported to FSA as grain. Either the decision is made late (the USDA speaker's "a dairy neighbor who ran out of feed"), or the farmer simply reports the default use. Both readings lead to the same place: the administrative record cannot see about 3.3M acres of silage, and they sit in the states where our harvest-time signals have the best conditions (large fields, clear grain/silage timing gap).

**Inference:** FSA silage intent is a floor for silage in dairy-specialist states and close to useless as a level in the Corn Belt. As a county feature it is a sharper prior than distance to the nearest dairy, because it is this year's, it is in acres, and it comes from the farmer.

### 7.4 Caveats on the FSA file

- It is what was reported, not what was harvested. NASS silage is harvested acres.
- The November file is not final. The 2025 final file is dated January.
- FSA coverage varies by state. **Computed** against the June 30, 2026 NASS planted estimate: California 342K of 420K (82%), Pennsylvania 932K of 1,020K (91%), Nebraska 10,088K of 10,500K (96%), Texas 2,418K of 2,450K (99%). Several states exceed 100% (New York 112%, Idaho 107%, Wisconsin 105%) because NASS raised planted area after June (US 95,343K in June, 96,777K in November) and the June state figures are the only ones I opened.
- I did not establish whether the county is where the land lies or where the farm is administered. Ask.

## 8. NASS control totals for 2026 (opened today)

| Item | 2025 | 2026 | Source |
|---|---|---|---|
| Corn planted, all purposes (June 30 Acreage) | 98,788K | 95,343K ("down 3 percent") | Acreage, 2026-06-30 |
| Corn to be harvested for grain (June 30) | 91,258K | 87,434K | Acreage, 2026-06-30 |
| Corn planted, all purposes (November 10) | 98,713K | 96,777K | Crop Production, 2026-11-10 |
| Corn harvested for grain (November 10) | 90,948K | 88,506K forecast ("unchanged from the previous estimate") | Crop Production, 2026-11-10 |
| Corn for silage, harvested | 6,187K (6,208K in the January 2026 summary) | blank: "estimation period has not yet begun" | Crop Production, 2026-11-10 |
| Sorghum for silage, harvested | 448K | blank | Crop Production, 2026-11-10 |
| Grain yield | 186.5 bu/ac | 179.6 bu/ac | Crop Production, 2026-11-10 |

State harvested-for-grain forecasts for 2026 (thousand acres, November 10): Iowa 12,800; Illinois 10,950; Nebraska 9,610; Minnesota 8,300; Kansas 6,550; South Dakota 5,840; Indiana 5,160; North Dakota 4,450; Missouri 3,470; Ohio 3,230; Wisconsin 3,100; Texas 2,120; Michigan 1,950; Colorado 1,170; Pennsylvania 710; New York 535; Idaho 125; Washington 125. California is inside "Other States" (484K).

State planted 2026 from the June 30 Acreage report (thousand acres; later revised nationally): California 420; Idaho 370; Wisconsin 3,800; New York 930; Pennsylvania 1,020; Texas 2,450; Iowa 13,000; Illinois 11,100; Nebraska 10,500; Minnesota 8,550; South Dakota 6,300; Kansas 7,050; Michigan 2,250.

**Inference (benchmark to show on stage, not a NASS number):** planted minus harvested for grain is 8,271K acres in 2026 (8.5% of planted) against 7,765K in 2025 (7.9%). In 2025 silage was 6,187K of that 7,765K (79.7%). If that share held, 2026 silage would be about 6.6M acres. This is the "official numbers already imply" line; our estimate should be shown next to it, and next to FSA's 2.89M.

The methodology section of the November report says planted acres are revised when "Farm Service Agency certified acreage data" or remote sensing data are available.

## 9. What this means for Kernel

### 9.1 Decisions

1. **The 2026 headline no longer has to rest on last year's map.** There is a 2026 in-season map (untested download) and there is a 2026 official acreage table (downloaded and parsed).
2. **Build the 2026 rollup as a ratio estimate either way.** Acres come from FSA (county) and NASS (state). The model contributes only the silage share among corn fields. This is the form NASS statisticians use themselves, and it removes pixel-count bias from the argument.
3. **Treat the mask as a measured input.** Its error is a number we compute on 2025, not a number we quote from a paper about Nebraska.
4. **Add two public numbers to every state card:** FSA silage intent 2026, NASS silage 2025. Ours is the third.

### 9.2 Recipe A: use the 2026 ICDL (try first, stop after 30 minutes if stuck)

1. One person registers at `http://cloud.csiss.gmu.edu/cropsmart` and opens "Cropland Data Layers", period "In-season", 2026.
2. Download the August 2026 map, clipped to our counties if the area-of-interest option works. Also take July 2026 for Texas and other early-harvest areas. Expect 30 m, CDL codes, EPSG:5070. Check the legend before trusting it.
3. **Measure it.** Download August 2025 from the same portal. Compare with the 2025 CDL (the organisers' copy or `2025_30m_cdls`) inside our counties: corn producer's and user's agreement, per state. Put that table in the notebook. This is the mask error we state on stage.
4. Corn codes to keep: 1, plus the double-crop corn codes 225, 226, 228, 237, 241 if the in-season legend carries them. Flag 12 (sweet corn) and 13 (popcorn).
5. Field rule: a polygon is corn in 2026 if at least 60% to 70% of its pixels are corn in the August map and its own summer NDVI peak falls between June and September.
6. For Texas-type regions use the July map: grain there can be combined before the August map's imagery ends.

### 9.3 Recipe B: ratio estimate without any wall-to-wall mask

For county c:

- `A_c` = FSA 2026 corn planted acres in county c (all intended uses, or grain plus silage only; say which).
- Sample fields in c that pass a corn check (ICDL, or our own classifier trained on 2025 imagery with CDL 2025 labels).
- `p_c` = acre-weighted share of sampled corn fields our model calls silage, corrected for the classifier's measured false-positive and false-negative rates.
- Silage acres in c = `p_c * A_c`. State = sum over counties, then scaled so that state corn acres match NASS planted.
- Report three buckets: grain, silage, other. NASS's own totals leave 1.3M to 1.6M acres that are neither.
- Uncertainty: bootstrap over fields within county, plus the mask error from Recipe A step 3.

### 9.4 Recipe C: if the ICDL cannot be downloaded

- Run the open Transformer on the HLS tiles that cover the labeled fields and two or three show counties, for day of year about 244 (September 1), with 2025 and 2026 HLS as input.
- Or keep the nowcast note's plan: classifier trained on 2025 imagery with CDL 2025 labels, applied to 2026. Expect corn F1 near 0.85 in the Corn Belt and unknown elsewhere.
- In both cases Recipe B still supplies the acres.

### 9.5 Sentences for the pitch (each backed by a number above)

- "For 2026 we did not reuse last year's crop map. Only about 18% of corn ground was continuous corn in USDA's own survey."
- "Farmers told FSA this summer that 2.9 million acres of corn were for silage. Last year NASS found 6.2 million. In Kansas the paperwork showed 300 acres and the survey found 230,000."
- "NASS's November report already implies 8.3 million acres of corn that will not be combined. It cannot yet say how much of that is silage. We can."
- "Our corn mask for 2026 agrees with the official map on X% of corn in these counties, measured on 2025." (Fill X from Recipe A step 3.)

### 9.6 Contradictions with the current plan

- The plan's fallback said there is no public 2026 corn mask. There is one, with caveats.
- The plan uses distance to the nearest dairy as the tie-breaker. FSA county silage intent is a stronger public prior for 2026 and costs one join.
- The plan rolls up from field calls to acres. Pixel or polygon counting is the method NASS itself calls biased; the ratio form avoids that.

## 10. Leads from the brief: confirmed or refuted

| Lead | Result |
|---|---|
| Zenodo 17457566 holds June-August 2023 at 10 m | Confirmed. Three files, 45.3 GB, CC BY 4.0 |
| NIFA page says maps produced operationally since 2021, delivered through CropScape or CropSmart | NIFA page not opened (host did not resolve). The substance is confirmed elsewhere: the map service lists 2021 to 2026, and the NASS-co-authored review says production is in operation |
| "Look for a 2026 file" | Found as service layers `cdl_2026_06/07/08`. File download untested |
| UMD GLAD 10 m crops | Confirmed as a dataset, refuted as a 2026 source: 2019 to 2022, maize and soybean only |
| NASS `2026_Remote_Sensing_for_Crop_Mapping.pdf` | Confirmed. It is Zhang, C. et al. 2025, RSE 330:114995. The path changed: now under `/sites/default/files/Research_and_Science/Cropland/docs/` |
| ESSD 18:3069 (2026) | Refuted as a map. It is CropSight-US, 124,419 ground-truth field objects for 2013 to 2023 (corn 54,069), from street-view images |
| arXiv 2606.05731 | Confirmed as a paper, refuted as a product. Early-June Iowa corn F1 0.59 |
| Johnson and Mueller 2021, corn accuracy by month | Abstract only. Midsummer above 70% from CDL history; about 85% in late September with imagery. Monthly table not opened |
| Which CDL year the organisers handed out | **Not established.** The event site, the Keeboh post, the Saturday deck and our own briefing notes give no year. The Devpost page returned 403 |

How to settle the CDL year in two minutes: open the provided raster's metadata. A 10 m grid can only be 2024 or 2025 (the CDL is 10 m "beginning in 2024"). Then compare 1,000 random pixels with the official `2025_30m_cdls` or `2024_30m_cdls` download; the right year matches almost everywhere.

## 11. Bonus: a ready-made harvest-date layer and a harvest index

Found while reading the CropSmart application. Outside the mask question, but it counts as a new harvest signal.

- CropSmart lists a "Harvest Date" layer: "CHI-based harvest-date detection on HLS S30 v002 (CHI = B7 / NDVI_narrow, NDVI_narrow = (B8A-B4)/(B8A+B4)) (30m) data". Layer names follow `HARVEST-CORNBELT-30M-ANNUAL_<year>_CORN-SOY`.
- It also lists a "Planting Date" layer: "GDD back-tracking from satellite-detected green-up (Tbase 10 C; corn 250 GDD, soybean 270 GDD) (30m) data". Layer names follow `PLANTING-CORNBELT-30M-ANNUAL_<year>_CORN-SOY`.
- I could not list which years are served.
- Related record: Li and Di, Zenodo 20450938 (May 29, 2026), "A Physically Anchored Framework for Large-Scale Crop Harvest Date Mapping Using Harmonized Landsat-Sentinel Imagery". Enhanced Harvest Phenology Index (EHPI): contrast between Red Edge 3 and narrow-band NDVI, kept un-normalized so that a value of 1 marks the crossover. Field-level error against Beck's field records: mean absolute error 3.08 to 3.57 days for corn, 3.46 to 3.49 for soybean. State level against USDA Crop Progress: 0.99 to 5.98 days. Files: `2022CornBeltHarvestDayMap_PAF.tif` (328 MB), `2023CornBeltHarvestDayMap_PAF.tif` (330 MB), and two small ground-truth archives (about 30 kB each). CC BY 4.0.

Formula with HLS S30 band names:

```
NDVI_narrow = (B8A - B04) / (B8A + B04)      # B8A = narrow NIR 865 nm, B04 = red 665 nm
CHI         = B07 / NDVI_narrow              # B07 = red edge 3, 783 nm
harvest     = first date after peak at which CHI rises through 1
```

**Inference:** CHI in the portal text and EHPI in the Zenodo record are the same idea; I did not see the paper's exact formula. The index is built for combine harvest in the Corn Belt. Nothing says how it behaves on a silage cut. That is a clean experiment for the Index Scout: does CHI cross 1 at the cut for silage as well, and how fast?

**Inference:** the planting-date rule (green-up date minus 250 growing-degree-days, base 10 C) is a one-line way to get the planting date our "cut date in growing-degree-days" number needs.

## 12. Pitfalls

1. The ICDL is a university product trained without ground truth. Validated on 518 polygons in two states. July 2023 state corn acres were off by up to 56%.
2. The download is untested. The address in the papers is dead. Whole-country 10 m files are 14 to 16 GB.
3. A mask of class 1 alone drops California's double-cropped corn. Seed, processed and fresh corn (about 1.18M FSA acres), popcorn (0.24M) and sorghum silage (448K acres in 2025) can look like silage to a harvest-timing model.
4. Last year's CDL as the 2026 mask points at the wrong fields and over-samples continuous corn, which leans toward silage.
5. FSA intended use is not harvested use, undercounts silage by 53% nationally, covers 82% of California's corn, and the November file is not final.
6. June maps are weak (corn user's accuracy 0.673 in Nebraska 2022). August maps can miss corn already combined in Texas.

## 13. Open questions

1. Does the CropSmart download for 2026 work, and which pipeline and legend does the 30 m file use?
2. Which year is the organisers' CDL, and which year are the evaluation labels?
3. How accurate is the in-season map for corn in California, Idaho, Wisconsin, New York and Pennsylvania? Nobody has published it. We can measure it on 2025.
4. Why does FSA record a tenth of Corn Belt silage: late switching, or reporting habit? A NASS judge will know.
5. Are FSA county acres assigned by land location or by administering office?

## 14. Annotated bibliography

Opened = I read the page or file itself.

1. Li, H., Di, L., Zhang, C., Guo, L., Yu, E.G., Shao, B., Liu, Z., Li, H. (2026). Automated 10-m Resolution In-season Crop-type Data Layer Mapping for Contiguous United States. Scientific Data 13:750. DOI 10.1038/s41597-026-07099-1. https://pmc.ncbi.nlm.nih.gov/articles/PMC13184328/ and https://www.nature.com/articles/s41597-026-07099-1 . Opened (both). Method, accuracy tables, limits.
2. George Mason University in-season map service. https://cat.csiss.gmu.edu/cgi-bin/wms_cdl_icrop?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1 . Opened 2026-11-14. Lists 2021 to 2026 June, July, August layers.
3. CropSmart portal. http://cloud.csiss.gmu.edu/cropsmart . Opened (application code only; the page is a script-driven app). Sign-in text, layer descriptions, download naming.
4. Zenodo 17457566. Contiguous United States 10m-resolution In-season Crop-type Data Layer 2023 June-August. https://zenodo.org/records/17457566 . Opened. File list and sizes; description repeats accuracy range 0.807 (June) to 0.984 (August) and label accuracy 0.825 to 0.937.
5. Zhang, C., Kerner, H., Wang, S., Hao, P., Li, Z., Hunt, K.A., Abernethy, J., Zhao, H., Gao, F., Di, L., Guo, C., Liu, Z., Yang, Z., Mueller, R., Boryan, C., Chen, Q., Beeson, P.C., Zhang, H.K., Shen, Y. (2025). Remote sensing for crop mapping: A perspective on current and future crop-specific land cover data products. RSE 330:114995. https://www.nass.usda.gov/sites/default/files/Research_and_Science/Cropland/docs/2026_Remote_Sensing_for_Crop_Mapping.pdf . Opened, full text. ICDL "already in operation"; 80%-90% by August; ACTIVE.
6. Zhang, H.K., Shen, Y., Zhang, X., Li, J., Yang, Z., Xu, Y., Zhang, C., Di, L., Roy, D.P. (2025). Robust and timely within-season conterminous United States crop type mapping using Landsat Sentinel-2 time series and the transformer architecture. RSE 329:114950. https://www.nass.usda.gov/sites/default/files/Research_and_Science/Cropland/docs/In-Season%20Crop%20Mapping%20Transformer-compressed.pdf . Opened, full text. Independent ICDL comparison; open model.
7. In-season crop type mapper code. https://github.com/hankui/In-season-crop-type-mapper . Opened. Model and samples: https://zenodo.org/records/14715402 . Opened.
8. Li, H. et al. (2024). Automated In-Season Crop-Type Data Layer Mapping Without Ground Truth for the Conterminous United States Based on Multisource Satellite Imagery. IEEE TGRS 62:4403214. Abstract at https://research.uaeu.ac.ae/en/publications/automated-in-season-crop-type-data-layer-mapping-without-ground-t/ . Opened (abstract). Full text not opened.
9. USDA NASS. 2025 Cropland Data Layer metadata. https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_CDL25_FGDC-STD-001-1998.htm . Opened.
10. USDA NASS. CDL FAQ. https://www.nass.usda.gov/research-and-science/cropland/sarsfaqs2 . Opened. Cropland page: https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php . Opened.
11. Abernethy, J., Beeson, P., Boryan, C., Hunt, K., Sartore, L. (2023). Preseason crop type prediction using crop sequence boundaries. Computers and Electronics in Agriculture 208:107768. https://www.nass.usda.gov/sites/default/files/Education_and_Outreach/Reports,_Presentations_and_Conferences/Journal_Articles/Preseason%20crop%20type%20prediction%20using%20crop%20sequence%20boundaries.pdf . Opened, full text.
12. Johnson, D.M., Mueller, R. (2021). Pre- and within-season crop type classification trained with archival land cover information. RSE 264:112576. Abstract at https://agris.fao.org/search/en/providers/122535/records/65dfc11563b8185d9caea1c2 . Opened (abstract). Full text not opened: ScienceDirect 403.
13. Posch, A., Kumar, J., Hoffman, F.M., Ganguly, A.R. (2026). Intercomparison of Machine Learning Algorithms for Remote Sensing-based In-season Crop Mapping. arXiv:2606.05731. https://arxiv.org/abs/2606.05731 . Opened (abstract page).
14. UMD GLAD. Mapping crops at 10 m resolution in the United States. https://glad.umd.edu/dataset/mapping-crops-10-m-resolution-united-states . Opened. Li, H., Song, X.-P. et al. (2026), ESSD 18:2227-2249.
15. Zhou, Z., Liu, Y., Diao, C. (2026). CropSight-US. ESSD 18:3069-3097. https://essd.copernicus.org/articles/18/3069/2026/ . Opened. Data: https://doi.org/10.5281/zenodo.15702414 (not opened).
16. USDA FSA. Crop Acreage Data. https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/frequently-requested/crop-acreage-data . Opened. Files parsed: `2026_fsa_acres_web_110526.xlsx` (https://www.fsa.usda.gov/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip) and `2025_fsa_acres_web_010526.xlsx` (https://www.fsa.usda.gov/sites/default/files/2026-01/DoISjehvQfz9.ZIP).
17. USDA NASS. Acreage, June 30, 2026. https://esmis.nal.usda.gov/sites/default/release-files/795961/acrg0626.txt . Opened.
18. USDA NASS. Crop Production, November 10, 2026. https://esmis.nal.usda.gov/sites/default/release-files/796144/crop1126.txt . Opened.
19. USDA NASS. Crop Production 2025 Summary, January 2026. https://esmis.nal.usda.gov/sites/default/release-files/795725/cropan26.txt . Opened (first 100,000 characters, which include the silage table).
20. USDA ERS. While Crop Rotations Are Common, Cover Crops Remain Rare. Amber Waves, March 2013. https://www.ers.usda.gov/amber-waves/2013/march/while-crop-rotations-are-common-cover-crops-remain-rare . Opened.
21. Li, H., Di, L. (2026). A Physically Anchored Framework for Large-Scale Crop Harvest Date Mapping Using Harmonized Landsat-Sentinel Imagery. Zenodo 20450938. https://zenodo.org/records/20450938 . Opened. SSRN version (abstract 6517614) not opened: 403.
22. Hack the Harvest event site. https://hacktheharvest.lovable.app . Opened. Keeboh post: https://sadiestlawrence.substack.com/p/why-we-are-building-keeboh . Opened. Devpost page not opened: 403.
23. Not opened: NIFA project page 1025609 (host did not resolve); California DWR statewide crop mapping (search summary only); ResearchGate copies (403).
