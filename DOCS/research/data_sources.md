# Kernel data sources brief: everything we pull, and why

Compiled 2026-11-15 by cc-varun from the research notes in this folder, the USDA briefing and rep Q&A transcripts, and a link check run the same day. This is the single list the data-harvest agents work from. It adds soil, drought, irrigation, price and thermal sources that the earlier notes did not cover.

**Not yet included:** the organizer sample data in the team JupyterLab. The lab needs a login and has not been read. Section 8 lists what to record from it. Whatever the organizers supply overrides the matching rows here.

## 0. Organizer messages, 14 Nov (these override the rows below)

- **The scoring year is 2025.** The organizers posted the numbers results will be evaluated against: 2025 corn harvested for grain and for silage, by state.
  - Source: `https://quickstats.nass.usda.gov/results/ACC45317-B978-3390-B0A1-BE0EC02A9D63` (CSV at `/data/spreadsheet/<same id>.csv`).
  - Local copy: `data/nass/quickstats_2025_corn_grain_silage_state.csv` (git-ignored; listed in `data/DATA_MANIFEST.tsv`).
  - Content: 92 rows. US total 90,948,000 grain acres and 6,187,000 silage acres. Silage is given for 48 states; grain for 41 states plus an "OTHER STATES" row. Connecticut, Maine, Massachusetts, Nevada, New Hampshire, Rhode Island and Vermont have a silage figure but no separate grain figure.
  - These are the revised 2025 figures, so use this vintage everywhere.
- **What a 2025 target changes:**
  - The 2025 Cropland Data Layer (B2) is the mask; the missing 2026 layer no longer matters for scoring.
  - HLS (C4) covers all of 2025, so it moves up to `P0` as the merged optical series.
  - 2026 becomes the demonstration of the nowcast, not the scored result.
  - The backtest years for fitting are 2024 and earlier; 2025 must stay untouched until the final run.
- **Cropland Data Layer access.** If the direct download fails, use CropScape (`https://nassgeodata.gmu.edu/CropScape/`): define an area, pick the year, download the raster subset or export acreage statistics. The site did not respond to a scripted request on 2026-11-15, so it may need a browser.
- **Resolution.** The 2024 and 2025 layers are 10 m. The organizers point to smaller resampled files (about 1.9 GB) for those two years; use them for backtesting, since earlier years exist only at 30 m.

## 1. What we predict, and what counts as truth

- **Deliverable:** two numbers per state and for the US, acres of corn harvested for grain and acres harvested for silage, before NASS publishes them in January.
- **Truth:** NASS state totals only. The organizers gave no field-level labels (`usda_reps_qa.md`).
- **Bars to clear:**
  - NASS's own forecast is usually within 3% of its final figure (1.8 to 2.5%), and missed by more than 4% last year.
  - "Same as last year" misses state silage acres by 12 to 15% (`README.md`, decision 5).
  - A signal with a stable, explained bias, built on data NASS does not already use, is useful to NASS even if it is less accurate than the survey.
- **What this means for data:** we need four layers, and each has its own sources.

| Layer | Unit | Role | Section |
| --- | --- | --- | --- |
| Targets and baselines | state-year (some county-year) | the truth we are scored on, and the numbers to beat | 3A |
| Field evidence | field, per satellite pass | what happened in each cornfield | 3B, 3C |
| Context | field, county or state-year | why a field or region behaves differently (soil, weather, water, demand, prices) | 3D to 3G |
| Proxy field labels | field | the only way to train and test a field-level call | 3H |

## 2. What affects what

Each row is one factor, the trap or question it answers, and the sources that measure it. Source ids point to section 3.

| Factor | Why it matters | Trap it answers | Sources |
| --- | --- | --- | --- |
| Shape of the drop (cliff or fade) | Silage goes from green to bare in one step; grain browns for weeks first | none; this is the core signal | C1 to C6 |
| Moisture and greenness at the cut | Silage is chopped at about 65% plant water; grain is combined dry | none; core signal | C1 (SWIR bands), C3, C4 |
| Ground left behind | Grain leaves a blanket of stalks; silage leaves short stubble and bare soil | none; core signal | C1 (bands 11, 12), C8 |
| Soil background colour and texture | Bare soil is dark in Maryland and light and sandy in Arizona, so one residue threshold fails across regions | soil colour by region | E1 to E6 |
| Crop clock (heat units, frost) | Texas cuts in early August, Nebraska in October; heat units since planting line the regions up | one calendar for all regions | D1, D2, A5 |
| Cloud cover | Clouds in the harvest week hide the cut | clouds | C2, C5, C6 |
| Soil wetness | Wet soil shifts both the radar signal and the residue index | false harvest signals | D6, D1 (rain) |
| Drought, hail, wind, early frost | A failed grain crop is chopped for silage or abandoned; this is the late switch surveys miss | satellite-only thinking | D4, D5, D8, A9 |
| Irrigation and water regime | Irrigated and rain-fed corn dry down differently | regional timing | E7, D7 |
| Double-cropping | Winter forage then corn in one year gives two green peaks | double crops | B3, B7, H2, H3 |
| Local feed demand | Silage is too heavy to haul far, so it is grown near cattle | none; this is the prior | F1 to F6 |
| Grain demand pull | Ethanol plants and export routes pull corn toward grain | satellite-only thinking | F7, G4 |
| Prices | Milk, corn and hay prices shift the grain-or-silage choice at the margin | satellite-only thinking | G1 to G3 |
| Farmer intent and insurance | What farmers told FSA and RMA they would do; where acres failed | abandoned acres | A7, A8, A9 |
| Where the corn is | Every acreage number starts from a corn mask | none; this is the base layer | B1 to B6 |

## 3. Source catalogue

**Status:** `V` = opened and checked by a research agent on 2026-11-14 (the note is named). `U` = the page or file URL resolved on 2026-11-15, content not inspected. `N` = not opened; named from memory, confirm before use.

**Priority:** `P0` = needed for the first end-to-end acreage number. `P1` = adds a factor the USDA reps named. `P2` = only if time allows.

### 3A. Targets, baselines and official statistics

| Id | Source | What we take | Access | Unit, years | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | NASS Quick Stats API | Corn planted, harvested for grain, harvested for silage: the truth for every backtest year | `https://quickstats.nass.usda.gov/api/api_GET` (key by email; 50,000 rows per request) | state-year; county-year silage in 6 states | V `data_access.md` 2.12 | P0 |
| A2 | NASS Crop Production reports | August to November grain forecasts, and the January Annual Summary; gives NASS's forecast-against-final error | `https://release.nass.usda.gov/reports/crop1126.txt`, `cropan26.txt` (same pattern for other months and years) | state, monthly | V `gap_fsa_ratio_baseline_2026.md` | P0 |
| A3 | NASS June Acreage report | 2026 planted acres, the denominator for the ratio estimate | `https://esmis.nal.usda.gov/sites/default/release-files/795961/acrg0626.txt` | state, 2026 | V `gap_corn_mask_2026.md` | P0 |
| A4 | Census of Agriculture 2017, 2022 | County corn silage and grain acres, county milk cows | Quick Stats with the census source filter | county, every 5 years | V `dairy_prior.md` | P0 |
| A5 | NASS weekly Crop Progress | Percent planted, dented, mature, harvested by state; Wisconsin "harvested for silage" by district | Quick Stats; `https://release.nass.usda.gov/reports/prog3626.txt`; Wisconsin weekly PDFs | state, weekly | V `labels.md`, `statistics.md` | P1 |
| A6 | NASS Crop Progress gridded layers | Gridded progress for the crop clock | `https://www.nass.usda.gov/Research_and_Science/Crop_Progress_Gridded_Layers/index.php` | grid, weekly | U | P2 |
| A7 | FSA Crop Acreage Data | Corn acres by county and intended use (grain, silage); failed and prevented acres if the file carries them (not confirmed in the notes) | `https://www.fsa.usda.gov/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip` (10 Nov 2026 file) | county, 2017 to 2026 | V `gap_fsa_ratio_baseline_2026.md` | P0 |
| A8 | RMA Summary of Business | Insured corn acres by type: grain (016) and silage (026) | `https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/state_county_crop/sobtpu_2026.zip` | county-year | V `labels.md` | P0 |
| A9 | RMA Cause of Loss | Indemnified corn acres by county, month and cause (drought, hail, wind, frost): the public stand-in for abandoned acres | `https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/cause_of_loss/colsom_2026.zip` | county-month | U | P1 |

Notes: FSA covers only 47% of the silage NASS later reports, and RMA is a floor, so both are covariates, never truth. The 2025 NASS figures exist in two vintages (January 2026 and the 30 September 2026 revision); store the vintage with every number.

### 3B. Where the corn is

| Id | Source | What we take | Access | Unit, years | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | Organizer data (Keeboh lab) | Cropland Data Layer, field boundaries, state totals as supplied | team JupyterLab | to be recorded | not read | P0 |
| B2 | Cropland Data Layer 2025 | Corn mask: classes 1, 225, 226, 228, 237, 241 | `https://www.nass.usda.gov/Research_and_Science/Cropland/Release/` (Earth Engine stops at 2024) | 30 m, 2025 | V `data_access.md` 2.4 | P0 |
| B3 | Cropland Data Layer history | Masks for backtest years, rotation and double-crop history per field | Earth Engine `USDA/NASS/CDL` | 30 m, 2008 to 2024 | V `data_access.md` 2.1 | P0 |
| B4 | Crop Sequence Boundaries | Field polygons | Earth Engine `projects/nass-csb/assets/CSB1825_rev23/CSB{ST}1825` | field, 2018 to 2025 edition | V `data_access.md` 2.4 | P0 |
| B5 | George Mason in-season crop layer 2026 | The only 2026 corn map (June, July, August) | `https://cloud.csiss.gmu.edu/icrop/` (free sign-in; download untested) | 30 m, 2026 | V `gap_corn_mask_2026.md` | P1 |
| B6 | County and district boundaries | Roll-up units | Earth Engine `TIGER/2018/Counties`; district codes from Quick Stats | county | U | P0 |
| B7 | California statewide crop mapping (DWR, Land IQ) | Multi-crop fields in California | `https://data.cnra.ca.gov/dataset/statewide-crop-mapping` | field, California | V `gap_us_field_labels_california.md` | P1 |

### 3C. Satellite time series (field evidence)

| Id | Source | What we take | Access (Earth Engine id unless stated) | Pixel, revisit | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | Sentinel-2 surface reflectance | Red, near-infrared, red-edge and both shortwave-infrared bands; gives NDVI, NDMI, NDTI | `COPERNICUS/S2_SR_HARMONIZED` | 10 to 20 m, 5 days | V `data_access.md` 2.1 | P0 |
| C2 | Cloud Score+ | Per-pixel cloud mask for C1 | `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` | 10 m | V same | P0 |
| C3 | Landsat 8 and 9 | Same indices on a second optical clock; thermal band | `LANDSAT/LC09/C02/T1_L2`, `LANDSAT/LC08/C02/T1_L2` | 30 m, 8 days combined | V (L9), U (L8) | P0 |
| C4 | Harmonized Landsat Sentinel-2 | Merged optical series for backtest years (runs 2 to 3 weeks behind, so not for 2026) | `NASA/HLS/HLSS30/v002`, `NASA/HLS/HLSL30/v002` | 30 m | V `data_access.md` 2.7 | P1 |
| C5 | Sentinel-1 radar | VV and VH backscatter; sees through cloud | `COPERNICUS/S1_GRD`; `OPERA/RTC/L2_V1/S1` | 10 to 30 m, 6 to 12 days per track | V `sar_harvest.md` | P0 |
| C6 | MODIS and VIIRS daily reflectance | Daily greenness to narrow cloud gaps on large fields; MODIS reaches back before Sentinel-2 for long backtests | `MODIS/061/MOD09GQ`, `NASA/VIIRS/002/VNP09GA` | 250 to 500 m, daily | U | P1 |
| C7 | Land surface temperature | Untested idea: bare soil after silage should run warmer by day than a residue blanket | `MODIS/061/MOD11A1`; Landsat thermal band in C3 | 1 km daily; 100 m | U | P2 |
| C8 | EMIT fractional cover | Dry-vegetation fraction as a cross-check on residue | NASA Earthdata, short name `EMITL2BFRCOV` | 60 m, irregular | V `residue.md` | P2 |
| C9 | Dynamic World | Bare and crop probabilities per Sentinel-2 scene | `GOOGLE/DYNAMICWORLD/V1` | 10 m | V `data_access.md` 2.1 | P2 |
| C10 | AlphaEarth annual embeddings | Comparison row only; ends at 2024 | `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` | 10 m, annual | V same | P2 |
| C11 | NISAR L-band radar | Next step, not tonight (about 6.5 GB per file; no 2025 harvest coverage) | Alaska Satellite Facility | n/a | V `sar_harvest.md` | skip |

Limits that shape the pull: Earth Engine allows 150 compute-hours a month on the default tier, so pilot on 200 fields and sample fields per state. Radar gaps reach 24 days in eastern Wisconsin, so date the cut from optical first and use radar to fill cloud gaps.

### 3D. Weather, crop clock and stress

| Id | Source | What we take | Access | Grid, years | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | gridMET | Daily max and min temperature (growing degree days, first frost), rain, vapour pressure deficit | Earth Engine `IDAHO_EPSCOR/GRIDMET` | 4.6 km, 1979 to 3 days ago | V `data_access.md` 2.10 | P0 |
| D2 | PRISM daily | Second temperature source | Earth Engine `OREGONSTATE/PRISM/ANd` | 4.6 km | V same | P2 |
| D3 | Daymet | 1 km temperature for backtests (no 2026) | Earth Engine `NASA/ORNL/DAYMET_V4` | 1 km, to 2025 | V same | P2 |
| D4 | gridMET drought indices | Drought severity per field through the season | Earth Engine `GRIDMET/DROUGHT` | 4.6 km | U | P1 |
| D5 | US Drought Monitor | Weekly share of each state or county in drought | `https://usdmdataservices.unl.edu/api/` | state, county, weekly | V `gap_fsa_ratio_baseline_2026.md` | P1 |
| D6 | SMAP soil moisture | Soil wetness on each satellite date, to flag unreliable radar and residue readings | Earth Engine `NASA/SMAP/SPL4SMGP/008` | 9 km | U | P1 |
| D7 | OpenET | Monthly evapotranspiration: water use and stress | Earth Engine `OpenET/ENSEMBLE/CONUS/GRIDMET/MONTHLY/v2_0` | 30 m, monthly | U | P2 |
| D8 | NOAA Storm Events | Hail, wind and flood events by county and date | `https://www.ncei.noaa.gov/stormevents/` | county, event | U | P2 |

### 3E. Soil and land

| Id | Source | What we take | Access | Grid | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | Per-field bare-soil baseline (derived) | Each field's own bare-soil spectrum from the weeks before the crop emerges; post-harvest readings are compared with it | computed from C1 and C3, no download | field | derived | P0 |
| E2 | UC Davis soil property grids | Soil colour at 10, 25, 50, 75 and 125 cm, plus texture and organic matter | `https://casoilresource.lawr.ucdavis.edu/soil-properties/` | 800 m | U (page lists the colour layers) | P1 |
| E3 | gNATSGO / gSSURGO | Texture, organic matter, drainage class, available water | Earth Engine community catalog `https://gee-community-catalog.org/projects/gnatsgo/`; Soil Data Access `https://sdmdataaccess.sc.egov.usda.gov/` | 10 to 30 m | U | P1 |
| E4 | OpenLandMap | Texture class and organic carbon in one Earth Engine call | `OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02`, `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02` | 250 m | U | P1 |
| E5 | SoilGrids, POLARIS | Alternates to E3 and E4 | `ISRIC/SoilGrids250m/v2_0`; `https://gee-community-catalog.org/projects/polaris/` | 250 m, 30 m | U | P2 |
| E6 | IrrMapper | Irrigated or not, 11 western states | Earth Engine `UMT/Climate/IrrMapper_RF/v1_2` | 30 m, annual | U | P1 |
| E7 | LANID irrigation map | Irrigation for the rest of the country | not located on 2026-11-15 | 30 m | N | P2 |
| E8 | 3DEP elevation | Slope, to correct radar | Earth Engine `USGS/3DEP/10m` | 10 m | U | P2 |

E1 is the main defence against the soil-colour trap: it turns every residue reading into a change within one field, so regional soil colour cancels out. E2 to E5 then explain any bias that remains by region.

### 3F. Demand: dairies, feedlots, ethanol

| Id | Source | What we take | Access | Unit | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Census 2022 herds | Milk cows and cattle on feed per county | Quick Stats (A1) | county | V `dairy_prior.md` | P0 |
| F2 | Climate TRACE | 48,331 US dairy and feedlot points | `https://api.climatetrace.org/v7/sources?subsectors=enteric-fermentation-cattle-operation` | point | V `gap_dairy_feedlot_points.md` | P1 |
| F3 | California Water Boards | 1,061 active dairies, 950 with herd size | `https://data.ca.gov/dataset/surface-water-water-quality-regulated-facility-information` | point | V `dairy_prior.md` | P1 |
| F4 | State registries | Minnesota (38,374 points with head counts), Michigan (272 large operations), Iowa (10,690), Wisconsin | URLs in `gap_dairy_feedlot_points.md` | point | V | P1 |
| F5 | EPA ECHO permits | Permitted large animal operations nationally | `https://echo.epa.gov/tools/data-downloads` | point | V `dairy_prior.md` | P2 |
| F6 | EPA AgSTAR | Dairies with digesters | `https://www.epa.gov/agstar/livestock-anaerobic-digester-database` | point | V | P2 |
| F7 | EIA ethanol plants | Plant locations and capacity: the pull toward grain | `https://atlas.eia.gov/datasets/eia::ethanol-plants` | point | U | P2 |

Features to build: cows per corn acre within a haul radius, number of dairies per county, average dairy size, distance to the nearest dairy. Use the cited haul limits in `gap_dairy_feedlot_points.md`, not the "120 miles" in one transcript.

### 3G. Prices and trade (state-year context)

| Id | Source | What we take | Access | Unit | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | Quick Stats prices received | Monthly corn, milk and hay prices | A1 (confirm item names with `get_param_values`) | state, monthly | N | P1 |
| G2 | ERS Feed Grains Database | Corn supply, use and price history | `https://www.ers.usda.gov/data-products/feed-grains-database` | US, state | U | P2 |
| G3 | AMS Market News | Cash corn bids and hay prices | `https://mymarketnews.ams.usda.gov/` (did not respond on 2026-11-15) | market, weekly | N | P2 |
| G4 | FAS Export Sales | Weekly corn export commitments | `https://apps.fas.usda.gov/esrqs/` | US, weekly | U | P2 |
| G5 | Custom rate and cost studies | Chopping and hauling costs | URLs in `dairy_prior.md` | state | V | P2 |

With one row per state per year, these can only enter the state-level model as two or three ratios (for example milk price over corn price in August). There are too few rows to fit more.

### 3H. Proxy field labels (the only field-level truth)

| Id | Source | What it gives | Access | Size | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | Quebec BDPPAD | Declared grain maize and forage maize parcels | `https://www.fadq.qc.ca/documents/donnees/base-de-donnees-des-parcelles-et-productions-agricoles-declarees/` | 2026: 42,726 grain, 11,102 forage; 2003 to 2026 | V `labels.md` | P0 |
| H2 | Kern County permit sites | Fields declared corn forage or corn grain | `https://maps.kerncounty.com/arcgis/rest/services/AgComm` | 2025: 751 forage, 5 grain; 2022 to 2026 | V `gap_us_field_labels_california.md` | P0 |
| H3 | Stanislaus County permit sites | Same | `https://services.arcgis.com/EeYBJFxLdUojipYa/arcgis/rest/services/Permit_Sites_and_Commodities_Open_Data/FeatureServer/7` | 2025: 1,392 forage, 9 grain; 2012 to 2026 | V same | P0 |
| H4 | Yolo County | Same; the one California source with a usable grain count | `https://gis.yolocounty.gov/ext/rest/services/Public/Agriculture/MapServer` | 2024: 75 grain fields; ends 2024 | V same | P1 |
| H5 | EuroCrops v2 | Parcels with separate silage and grain maize codes across Europe | `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/EuroCropsV2/gpqt/` | 152 country-year files, 2008 to 2023 | V `labels.md` | P1 |
| H6 | Wisconsin weekly silage progress | Not field labels; a label-free check on our cut-date distribution | A5 | district, weekly | V `statistics.md` | P1 |

Limits: California labels are about 99% silage, so they test recall on silage and the double-crop trap, not the grain class. Quebec and Europe are balanced but are another climate and another soil, so a model trained there must be checked against US state totals before we trust it.

## 4. Calibrating by region without over-fitting to one

The reps named over-calibrating to one place as a trap. The data design that avoids it:

1. **Measure change within a field, not absolute values.** Greenness as a share of that field's peak; residue against that field's own bare-soil baseline (E1).
2. **Time by heat units, not dates.** Growing degree days from D1, started at the field's own green-up.
3. **Let the base rate differ by region, not the rule.** One evidence rule everywhere; a prior per state or district from A1, A4, A7, A8 and F1.
4. **Hold out whole state-years.** Fit on some states and years, score on others, and report whether the bias is the same size and sign across them.
5. **Check the leftovers against soil and water.** If errors line up with soil colour (E2), texture (E3, E4) or irrigation (E6), add that variable; if not, leave it out.

## 5. Training data for a fine-tuned Nemotron model

**Recommendation:** fine-tune Nemotron on the field-level call and its explanation, and keep the state acreage numbers in a small statistical model. The reasons:

- **The truth is too thin for a language model at state level.** There is one row per state per year. A language model fine-tuned on a few hundred numeric rows will not beat a regression, and it can state a number that no data supports. The reps' bar is "would you bet 100 million dollars on your answer".
- **Field level has enough rows.** H1 alone gives tens of thousands of labeled parcels a year for 24 years.
- **It gives the Nemotron track a measured result.** The fine-tuned model, the stock model and the simple scorecard are scored on the same held-out parcels, and we show the table whichever way it comes out.

Training rows for the fine-tune:

| Field | Content |
| --- | --- |
| Input | One field-season as text: the per-pass series of NDVI, NDMI, NDTI and radar VH and VV with dates in growing degree days; cloud-gap flags; the bare-soil baseline; soil texture and colour class; drought index; irrigation flag; cows per corn acre nearby |
| Output | The label (silage or grain) and a short reason that cites only values in the input |
| Label source | H1 (main), H5 (more regions), H2 to H4 (US check, never training) |
| Held out | Whole regions and whole years, plus every US field |

Model and compute, from `brev_ops.md` 4.7: Unsloth supports LoRA on all Nemotron models; Nemotron 3 Nano 4B fits on a small GPU; the 30B model needs about 60 GB of GPU memory. No source gives a training time.

Risks to state on the slide: the labels are Canadian and European, so US performance is measured only through state totals and the California silage fields; and a language model reading numbers as text is slower and usually no more accurate than a small tabular model on the same features.

## 6. Harvest plan

Each puller writes one cached file, skips if the file exists, and adds a row to `data/DATA_MANIFEST.tsv` (path, bytes, sha256, source URL). Nothing above 5 MB goes into git.

| Order | Puller | Sources | Output | Needs |
| --- | --- | --- | --- | --- |
| 1 | Official statistics | A1 to A5, A7 to A9, F1, G1 | one tidy table of state-year and county-year figures, with vintage | Quick Stats key |
| 2 | Corn mask and fields | B1 to B4, B6 | sampled corn field polygons per state | organizer data read first |
| 3 | Proxy labels | H1 to H4 | labeled polygons with year and class | none |
| 4 | Pilot time series | C1 to C3, C5, D1 on 200 fields | per-field, per-pass table; measured Earth Engine cost per field | Earth Engine project |
| 5 | Full time series | same, sized from the pilot | same table at scale | pilot result |
| 6 | Context | D4 to D6, E2 to E4, E6, F2 to F4 | one row per field | step 2 |
| 7 | Extras | C6 to C9, D7, D8, G2 to G4, H5 | as needed | time |

## 7. What is not available

- A 2026 Cropland Data Layer (early 2027).
- Field-level silage or grain truth for the US outside three California counties.
- NASS's running total of failed acres (internal); A7 and A9 are the public stand-ins.
- Per-field hybrid maturity and planting date; both are inferred from the satellite series and D1.
- Soil colour at field scale; E2 is 800 m, which is why E1 is derived per field.

## 8. Open items

1. **Organizer lab not read.** Record for each folder: file names, formats, years, states, the field-boundary schema, and whether the state totals match A1.
2. **Which years to backtest.** Sentinel-2 surface reflectance in Earth Engine starts in 2017; MODIS (C6) is the only option before that.
3. **Earth Engine quota.** Step 4 decides how many fields per state we can afford.
4. **Rows marked `N` or `U`** must be opened and their fields checked before a number from them goes on a slide.
