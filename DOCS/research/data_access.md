# Data access and tooling: per-field time series for 10^4-10^5 polygons in hours

Team Kernel, Hack the Harvest. Research run: Saturday 2026-11-14, about 20:00-20:50 UTC (12:00-12:50 Pacific).

## 0. How this was produced (read first)

- **WebSearch was not available in this run.** The shared per-turn search budget (200 calls across all agents) was already used up, so every search call was refused. The brief's "at least 12 distinct searches" could not be met. If more searching is wanted, send a follow-up message or raise `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`.
- Everything below therefore comes from **about 100 direct fetches of primary pages and public APIs** (Earth Engine catalog and guides, NASS pages, the Planetary Computer STAC and SAS endpoints, Earth Search STAC, NASA CMR-STAC, the ASF search API, PyPI, Copernicus documentation), plus one NASS zip of Excel workbooks that I downloaded and parsed myself.
- WebFetch returns a small model's reading of each page, so page-derived numbers passed through that reader. Numbers marked **(parsed directly)** came from files I parsed with my own script.
- "Inference:" marks my own reasoning. "Not verified" marks things I could not open. Nothing here is cited from memory unless it says so.
- All "as of" statements mean 2026-11-14.

## 1. Bottom line

**Fast path: Google Earth Engine, server-side zonal means, pulled as DataFrames in chunks.** Every collection we need is current in the catalog except two: the Cropland Data Layer stops at 2024 and the AlphaEarth embeddings stop at 2024. The binding constraint is no longer speed, it is the **monthly compute quota introduced on 2026-04-27**: 150 EECU-hours on the default Community tier, 1,000 on the Contributor tier (needs a billing account, not charged).

**Fallback path: STAC plus cloud-optimized GeoTIFFs, no Earth Engine.** Element 84 Earth Search (Sentinel-2 COGs in AWS us-west-2) or Microsoft Planetary Computer (anonymous STAC and anonymous SAS tokens both worked today; storage is in Azure West Europe), loaded with `odc-stac`, reduced with a rasterized zone-id grid and `bincount` (CuPy on the GPU). Realistic for one to three states, not for the whole country in 3 hours.

**Three things that change plan v2:**

1. Sentinel-1 revisit is very uneven across silage country. Eastern Wisconsin had one track every 12 days in fall 2025 with a **24-day hole from Sep 8 to Oct 2**; central Minnesota had a 17-day hole (Sep 7 to Sep 24); the San Joaquin Valley had a pass every 1 to 5 days. A radar-first cut date cannot be the primary measurement everywhere.
2. In California a corn mask built from CDL class 1 alone keeps only about **39%** of corn validation pixels. **58%** of them sit in the double-crop classes 225, 226, 228 and 237.
3. Do not census fields for the state rollup. Wall-to-wall is roughly 1.5 million corn polygons (Inference, section 6). Sample fields per state and use a ratio estimator against NASS planted acres.

## 2. Verified facts

### 2.1 Earth Engine catalog: what is there and how fresh

| Dataset | Asset id | Availability shown on the catalog page | Pixel | Notes |
|---|---|---|---|---|
| Sentinel-2 surface reflectance, harmonized | `COPERNICUS/S2_SR_HARMONIZED` | 2017-03-28 to 2026-11-14 13:11Z | 10 / 20 / 60 m | scale 0.0001; revisit 5 days; baseline shift handled (2.9) |
| Cloud Score+ | `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` | 2015-06-27 to 2026-11-14 08:02Z | 10 m | bands `cs`, `cs_cdf`; thresholds 0.50-0.65 "generally work well"; CC-BY-4.0 |
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | 2014-10-03 to 2026-11-14 12:00Z | 10 m | sigma0 in dB; updated daily; ingested "within two days after they become available" |
| Sentinel-1 GRD, linear power | `COPERNICUS/S1_GRD_FLOAT` | not opened | 10 m | the GRD page says it holds "raw power values (which is updated faster)" |
| OPERA RTC-S1 | `OPERA/RTC/L2_V1/S1` | 2016-04-14 to 2026-11-14 07:03Z | 30 m | gamma0, terrain corrected, per burst; added to the catalog 2026-04-28 |
| HLS Sentinel-2 | `NASA/HLS/HLSS30/v002` | 2015-11-28 to 2026-11-05 23:52Z | 30 m | see lag in 2.7 |
| HLS Landsat | `NASA/HLS/HLSL30/v002` | 2013-04-11 to 2026-11-05 23:58Z | 30 m | |
| Landsat 9 Collection 2 Level 2 | `LANDSAT/LC09/C02/T1_L2` | 2021-10-31 to 2026-11-12 16:27Z | 30 m | scale 2.75e-05, offset -0.2; 16-day revisit |
| gridMET | `IDAHO_EPSCOR/GRIDMET` | 1979-01-01 to 2026-11-11 06:00Z | 4638.3 m | `tmmx`, `tmmn` in Kelvin; `status` = early / provisional / permanent |
| Daymet V4 | `NASA/ORNL/DAYMET_V4` | 1980-01-01 to 2025-12-31 | 1000 m | degrees C; no 2026 |
| PRISM daily | `OREGONSTATE/PRISM/ANd` | 1981-01-01 to 2026-11-10 12:00Z | 4638.3 m | `OREGONSTATE/PRISM/AN81d` is deprecated and ends 2020-12-30 |
| **Cropland Data Layer** | `USDA/NASS/CDL` | 1997-01-01 to **2025-01-01** | 30 m | **latest image is 2024**, data band only; `cultivated` 2013-2023, `confidence` 2008-2023 |
| Crop Sequence Boundaries | `projects/nass-csb/assets/CSB1825_rev23/CSB{ST}1825` | 2018-2025 edition | vector | community catalog, one collection per state (2.4) |
| **AlphaEarth embeddings** | `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` | 2017-01-01 to **2025-01-01** | 10 m | **latest year is 2024**; 64 bands `A00`-`A63`, unit length; CC-BY 4.0 |
| Dynamic World | `GOOGLE/DYNAMICWORLD/V1` | 2015-06-27 to 2026-11-14 11:36Z | 10 m | only for Sentinel-2 scenes with `CLOUDY_PIXEL_PERCENTAGE <= 35%`; has `crops` and `bare` probabilities |
| NAIP | `USDA/NAIP/DOQQ` | 2002-06-15 to 2023-11-17 | 0.6 m listed | no 2024 imagery in Earth Engine |
| OPERA DIST-ANN-HLS | `OPERA/DIST/L3_DIST-ANN-HLS/V1` | 2023-01-01 to 2025-01-01 | 30 m | years 2023 and 2024 only; has `VEG-DIST-DATE` (days since 2020-12-31) |

Other OPERA entries in the catalog: `OPERA/RTC/L2_V1/S1_STATIC`, DSWx-HLS, DSWx-S1. DIST-ALERT is not listed as its own dataset.

### 2.2 Earth Engine quotas, limits and endpoints

| Item | Value | Source page |
|---|---|---|
| Noncommercial tiers, monthly | Community **150 EECU-hours**; Contributor **1,000** (active billing account required, not charged); Partner 100,000 (separate application, "may take several weeks", climate work only) | noncommercial tiers guide |
| Effective date | "Since April 27, 2026, all noncommercial Earth Engine projects have a recurring monthly quota"; resets the first of each month, midnight Pacific; "The quota limits are still gradually rolling out" | same |
| What counts | "Quotas apply to both Batch and Online EECU-hour consumption", including the Python API and Xee | same |
| When exhausted | "restricted mode limits your online and batch concurrency and reduces the number of compute workers" (no numbers given) | same |
| Several projects | Each project has its own quota, but you "may not use multiple noncommercial projects or multiple user accounts to simulate or act as a single application or account" | same |
| Concurrent interactive requests | 40 on the standard endpoint, 40 on the high-volume endpoint | usage guide |
| Request rate | 100 requests/s (6,000/min) per project and per account | usage guide |
| Request payload | "A single query to Earth Engine is limited to 10MB in size" | usage guide |
| Computed result | 100 MiB, system-wide | usage guide |
| Interactive request | must finish within five minutes; responses limited to tens of megabytes | processing environments guide |
| Batch | each task lives at most ten days; 3,000 queued tasks per project; default "2 tasks (on average)" running at once, and noncommercial limits "are set by the noncommercial tier" (no per-tier number published) | both guides |
| Assets | 250 GB, 10,000 assets | usage guide |
| HTTP 429 | client library retries up to five times | usage guide |

**Which endpoint.** The processing-environments guide says the high-volume endpoint (`https://earthengine-highvolume.googleapis.com`) suits "automated, simple queries that don't require aggregation", has less caching, and that complex queries use more EECU-time there; "For complex analyses that need efficient caching, the standard API endpoint may be preferable." Both endpoints have the same 40-request concurrency.
Inference: zonal reductions are aggregations, so run them on the **standard** endpoint and keep the high-volume endpoint for pixel chips (Xee, `computePixels`).

**`reduceRegions`.** Signature: `Image.reduceRegions(collection, reducer, scale, crs, crsTransform, tileScale, maxPixelsPerRegion)`. `tileScale` defaults to 1; "using a larger tileScale (e.g., 2 or 4) may enable computations that run out of memory with the default." Output property names join band and statistic with an underscore when reducers are combined. The best-practices guide warns that a very large or complex collection can trigger "Computed value is too large" and suggests mapping `reduceRegion()` over the features instead. It also says to combine reducers with `sharedInputs`, filter by time and place first, avoid `clip()`, avoid `ee.Algorithms.If()`, and avoid `featureCollection.geometry()` on large collections.

**Straight to pandas.** `ee.data.computeFeatures({'expression': fc, 'fileFormat': 'PANDAS_DATAFRAME'})` pages through the result (default 1,000 per page) and returns a DataFrame. `GEOPANDAS_GEODATAFRAME` is also supported.

**Xee.** v0.1.0 is described as a major refactor with breaking changes; `pip install --upgrade --pre xee`; `xr.open_dataset(ic, engine='ee', **grid)` with `helpers.extract_grid_params(ic)`; the README recommends the high-volume endpoint for reading stored collections.

**Measuring cost.** `ee.profilePrinting()` in Python reports EECU-time per algorithm; the tiers page says to use Cloud Monitoring for project usage. The docs give one calibration point only: "a job which consumes 10 EECU-hours may have an observed runtime of just a few minutes."

### 2.3 Authentication in a headless notebook

- `ee.Authenticate()` modes: `colab`, `notebook`, `localhost`, `gcloud`. In a non-Colab Jupyter the default is `notebook`. The guide says: "If you can use an authentication project (see below), use `auth_mode=notebook`."
- Notebook mode: run the cell, open the printed link on any machine, pick an authentication project (you need Owner, Editor or OAuth Config Editor on it), generate the token, paste the code back. Credentials are stored in `~/.config/earthengine/credentials`.
- `ee.Initialize(project='my-project')` is required. The authentication project does not have to be the compute project.
- Service account (for unattended agents):
  ```python
  credentials = ee.ServiceAccountCredentials('my-service-account@...gserviceaccount.com', '.private-key.json')
  ee.Initialize(credentials, project='my-project')
  ```
  The project must be registered for Earth Engine with the API enabled; the account needs Earth Engine Resource Viewer and possibly Service Usage Consumer. An `invalid_grant` error can be clock skew.
- The repo is public and shared by several agents: **the key file must never be committed.**

### 2.4 Cropland Data Layer and Crop Sequence Boundaries

**Release timing.** "The 2025 CDL product was released February 27, 2026." Earlier releases: 2024 on Feb 27, 2025; 2023 on Jan 31, 2024; 2022 on Jan 30, 2023; 2021 on Feb 14, 2022; 2020 on Feb 1, 2021; 2019 on Feb 5, 2020; 2018 on Feb 15, 2019; 2017 on Jan 26, 2018; 2016 on Feb 3, 2017. The FAQ describes in-season estimates only as "the internal CDL acreage estimates"; the release page mentions no in-season product.
Inference: CDL 2026 will appear between late January and late February 2027. There is no public 2026 corn mask today.

**Resolution and inputs.** "Beginning in 2024, the CDL spatial resolution has increased to 10-meters." The 2024 and 2025 inputs are Harmonized Sentinel-2 Level-2A, Landsat 8 and Landsat 9. Training and validation come from the Farm Service Agency Common Land Unit / 578 data (agriculture) and NLCD (non-agriculture). "Pixel counting is usually downward biased when compared to the official estimates."

**Downloads** (prefix `https://www.nass.usda.gov`):

| File | Size |
|---|---|
| `/sites/default/files/Research_and_Science/Cropland/Release/datasets/2025_10m_cdls.zip` | 9.8 GB |
| `/sites/default/files/Research_and_Science/Cropland/Release/datasets/2025_30m_cdls.zip` (resampled) | 1.9 GB |
| `/sites/default/files/Research_and_Science/Cropland/Release/datasets/2024_10m_cdls.zip` | 9.0 GB |
| `/sites/default/files/Research_and_Science/Cropland/Release/datasets/2025_cultivated_layer.zip` (2021-2025) | 300 MB |
| `/sites/default/files/Research_and_Science/Cropland/Release/datasets/Crop_Frequency_2008-2025.zip` (corn, cotton, soybeans, wheat) | 2.0 GB |
| `/sites/default/files/Research_and_Science/Cropland/docs/CDL_2025_accuracy_assessments.zip` (49 Excel workbooks) | 75 MB |

The 10 m confidence layers "are no longer available for direct download". NASS warns that "confidence values should not be used as a measure of accuracy." The Planetary Computer copy (`usda-cdl`) ends in 2021.

**Corn-related class codes** (Earth Engine class table): 1 Corn; 12 Sweet Corn; 13 Pop or Orn Corn; 225 Dbl Crop WinWht/Corn; 226 Dbl Crop Oats/Corn; 228 Dbl Crop Triticale/Corn; 237 Dbl Crop Barley/Corn; 241 Dbl Crop Corn/Soybeans. No other class name contains "Corn". There is no silage class. "The CDL Program is currently not equipped to monitor triple or quad cropping practices."

**National accuracy** (FAQ): 2025: "75.4% OVERALL CROP ACCURACY, 24.6% ERROR, 0.712 KAPPA"; 2024: 77.5%, kappa 0.733; 2023: 81.6%, kappa 0.788. "The Producer's Accuracy is generally 85% to 95% correct for the major crop-specific land cover categories." From 2016 validation is unbuffered; before that it was "buffered inward 30 meters" and "inflated somewhat".

**Corn accuracy by state, CDL 2025 (parsed directly from the NASS workbooks, "Summary Table" sheet).** Producer's accuracy is the share of reference corn pixels mapped as corn (recall). User's accuracy is the share of mapped corn pixels that are corn in the reference (precision).

| State | Corn (1) producer's | Corn (1) user's | Reference pixels, class 1 | Reference pixels, 225+226+228+237 | Share of corn reference pixels in double-crop classes |
|---|---|---|---|---|---|
| Iowa | 95.8% | 94.2% | 151,721 | 5 | 0.0% |
| Minnesota | 95.9% | 93.5% | 102,125 | 3 | 0.0% |
| Idaho | 94.2% | 90.3% | 5,034 | 372 | 6.9% |
| Texas | 91.2% | 87.0% | 34,529 | 814 | 2.3% |
| Wisconsin | 89.7% | 88.1% | 50,137 | 216 | 0.4% |
| **California** | 86.7% | 82.9% | 2,280 | **3,180** | **58.2%** |
| New York | 72.7% | 80.9% | 9,509 | 330 | 3.4% |
| Pennsylvania | 68.9% | 71.3% | 8,832 | 960 | 9.8% |
| National | 92.2% | 91.2% | 999,320 | 11,702 | 1.2% |

California double-crop classes in 2025: 225 producer's 66.3% / user's 64.2% (n = 1,297); 226 60.0% / 78.7% (n = 473); 228 66.5% / 70.5% (n = 1,379); 237 45.2% / 87.5% (n = 31).

**Union mask {1, 225, 226, 228, 237, 241} (computed by me from each workbook's error matrix; rows are map classes, columns are reference classes):**

| State | Union producer's | Union user's | Largest omission (reference corn mapped as...) |
|---|---|---|---|
| California | 87.9% (4,798 / 5,460) | 88.9% (4,798 / 5,399) | Winter Wheat 142, Triticale 119, Alfalfa 69, Oats 54 |
| Wisconsin | 89.6% | 88.3% | Grass/Pasture 2,050 (4.1% of corn reference), Soybeans 1,020 |
| Iowa | 95.8% | 94.2% | Grass/Pasture 2,256 (1.5%), Soybeans 1,549 |
| Idaho | 94.9% | 92.8% | Developed/Low Intensity 64, Alfalfa 60 |
| New York | 72.9% | 82.8% | **Grass/Pasture 1,700 (17.3%)** |
| Pennsylvania | 68.4% | 74.5% | **Grass/Pasture 1,830 (18.7%)** |

In California, pixels mapped as class 1 cover 1,976 + 78 + 40 + 28 = 2,122 of the 5,460 corn reference pixels, so a class-1-only mask has about **39%** recall of corn-containing reference pixels. The Texas workbook has a different layout and my union script did not parse it; its Summary Table numbers above are fine.

Inference: the 2024+ validation sample is described as proportional to state size and across categories, so reference-pixel shares approximate area shares in the FSA data. Inference: the New York and Pennsylvania confusion with Grass/Pasture may reflect small fields and contour strips at 10 m; I have no source for the cause.

For comparison, the 2023 state metadata pages (30 m): California corn producer's 74.9%, user's 76.6%, FSA crops overall 80.7%; Iowa corn producer's 94.3%, user's 97.5%, overall 90.5%. From 2024 "metadata is only available at the national-level"; state detail lives in the zip above.

**Crop Sequence Boundaries.**

- Latest edition: 2018-2025, published March 27, 2026. Download: `https://www.nass.usda.gov/sites/default/files/Research_and_Science/Crop-Sequence-Boundaries/datasets/NationalCSB_2018-2025_rev23.zip` (file geodatabase `CSB1825.gdb`, layer `national1825`). Earlier 8-year windows back to 2008-2015 use the same pattern.
- **15,973,106 polygons.** Albers Conical Equal Area, NAD83, standard parallels 29.5 and 45.5, central meridian -96, origin latitude 23, meters (the page does not name an EPSG code; Inference: this is the EPSG:5070 definition).
- Attributes: `CSBID` (state FIPS, start year, end year, 9-digit sequence), `CSBACRES`, `CDL2018` ... `CDL2025` (majority CDL class per year), `STATEFIPS`, `STATEASD`, `ASD`, `CNTY`, `CNTYFIPS`, `INSIDE_X`, `INSIDE_Y`, `Shape_Length`, `Shape_Area`.
- Method: 8 years of CDL, resampled to 10 m, TIGER road and rail lines re-imposed, polygons under 1 hectare merged, boundaries simplified with a 60 m tolerance. Not ownership parcels, not from FSA.
- Earth Engine: per-state collections `projects/nass-csb/assets/CSB1825_rev23/CSB{ST}1825`, for example `CSBAL1825`. The community catalog says the crop attributes are named `CROP18` ... `CROP25` there, which differs from the geodatabase names. Check with `.first().propertyNames().getInfo()`. The 2016-2023 assets no longer resolve.

### 2.5 Sentinel-1: who covers what

**Constellation (Copernicus SentiWiki).** Sentinel-1C launched 5 December 2024, "fully operational since early May 2025". Sentinel-1D launched 4 November 2025, "fully operational starting mid April 2026". "Sentinel-1A end of operations is planned for end of June 2026", after which 1D takes over its scenario. Each satellite repeats every 12 days; two give 6 days.

**Fall 2025 revisit, from the ASF search API (GRD_HD, IW mode, point query, Aug 15 to Nov 15 unless noted).**

| Place | Scenes | Satellites | Tracks | Usual gap | Largest gap |
|---|---|---|---|---|---|
| Eastern Wisconsin (44.05 N, 88.55 W) | 7 | 1C | 19 ascending | 12 days | **24 days, Sep 8 to Oct 2** |
| South-central Wisconsin (43.20 N, 89.40 W) | 20 | 1C 13, 1A 7 | 92, 19 ascending | 1-6 days | 11 days, Oct 26 to Nov 6 |
| Central Minnesota (45.50 N, 94.60 W) | 10 | 1C | 63, 165 ascending | 5-7 days | **17 days, Sep 7 to Sep 24** |
| Central Iowa (42.00 N, 93.65 W) | 14 | 1A | 165, 63 ascending | 5-7 days | 12 days, Aug 20 to Sep 1 |
| Lancaster County, Pennsylvania (40.05 N, 76.30 W) | 16 | 1A | 106, 4 ascending | 5-7 days | 7 days |
| Texas Panhandle (34.80 N, 102.40 W), from Jul 15 | 46 | 1A 36, 1C 10 | 5, 78 ascending; 12, 85 descending | 1-6 days | 7 days |
| San Joaquin Valley (37.00 N, 120.55 W), from Aug 1 | 52 | 1A 26, 1C 26 | 137 ascending; 42, 144 descending | 1-5 days | 5 days |

**Fall 2026.** Eastern Wisconsin: Sentinel-1C track 19 only, exactly every 12 days (8 scenes, Aug 17 to Nov 9). Central Iowa (Planetary Computer STAC): Sentinel-1D only, tracks 165 and 63, 5 and 7 day alternation, with a 12-day gap Nov 2 to Nov 14.

**Product facts.**

- `COPERNICUS/S1_GRD` preprocessing: apply orbit file, GRD border noise removal (applied "as of January 12, 2018"), thermal noise removal, radiometric calibration, terrain correction, then `10*log10(x)`. "Radiometric Terrain Flattening is not being applied due to artifacts on mountain slopes." Bands `VV`, `VH`, `HH`, `HV` in dB and `angle`. Properties: `instrumentMode`, `orbitProperties_pass`, `relativeOrbitNumber_start`, `platform_number`, `transmitterReceiverPolarisation`, `resolution_meters`. The guide says to filter to "a homogeneous subset before starting processing".
- `OPERA/RTC/L2_V1/S1`: gamma0 on a 30 m grid per burst, `mask` band (0 valid, 1 shadow, 2 layover, 3 both, 255 invalid), properties `ORBIT_PASS_DIRECTION`, `TRACK_NUMBER`, `BURST_ID`, `INPUT_L1_SLC_GRANULES`. NASA lists RTC-S1 coverage as "Near Global (all land masses excluding Antarctica)", distributed by ASF.
- Planetary Computer `sentinel-1-rtc` has `msft:requires_account: true` ("A Planetary Computer account is required to retrieve SAS tokens to read the RTC data"). `sentinel-1-grd` does not.
- Earth Search `sentinel-1-grd` is requester-pays.
- Not verified: whether `COPERNICUS/S1_GRD` in Earth Engine carries Sentinel-1C and 1D scenes. The catalog page names no satellites. Check before relying on it (section 5.5).

### 2.6 Sentinel-2: dense in time, but clouds still hide weeks

Central Iowa, tile 15TVG, Sep 5 to Oct 5, 2025 (Planetary Computer STAC): 13 acquisitions from three satellites (2A: 2, 2B: 5, 2C: 6), two relative orbits (69 and 112), gaps of 0 to 5 days, baseline 05.11.

| Date | Satellite | Orbit | Scene cloud % |
|---|---|---|---|
| Sep 5 | 2C | 112 | 67.6 |
| Sep 7 | 2B | 69 | 14.4 |
| Sep 10 | 2B | 112 | 20.1 |
| Sep 12 | 2C | 69 | 80.2 |
| Sep 14 | 2A | 69 | 77.0 |
| Sep 15 | 2C | 112 | 83.4 |
| Sep 17 | 2B | 69 | 94.7 |
| Sep 17 | 2A | 112 | 93.6 |
| Sep 20 | 2B | 112 | 97.6 |
| Sep 22 | 2C | 69 | 25.3 |
| Sep 25 | 2C | 112 | 0.7 |
| Sep 27 | 2B | 69 | 0.0 |
| Oct 2 | 2C | 69 | 0.1 |

Six acquisitions in a row (Sep 12 to Sep 20) were more than 75% cloudy. That is a 12 to 15 day optical blackout in the middle of the silage window even with three satellites. Sentinel-1A passed on Sep 13 and Sep 18 and fills it in Iowa. In eastern Wisconsin the radar hole (Sep 8 to Oct 2) covers the same weeks. Scene-level cloud cover is not field-level cover; this is one tile.

As of today the latest Sentinel-2 L2A item for that tile is 2026-11-11 on both Planetary Computer and Earth Search (baseline 05.13). All three satellites were still delivering in November 2026.

### 2.7 HLS: fine for 2025, about two to three weeks behind right now

| Tile (place) | Latest HLS S30 granule at NASA CMR-STAC on 2026-11-14 | Age |
|---|---|---|
| 15TVG (central Iowa) | 2026-10-25 | 20 days |
| 16TCP (eastern Wisconsin) | 2026-10-31 | 14 days |

The Planetary Computer mirror shows the same last date for 15TVG (S30 on Oct 25, L30 on Oct 23). The Earth Engine collections end 2026-11-05. The Planetary Computer collection text quotes a nominal latency of 1.7 days. Inference: forward processing is backlogged this month; I found no notice explaining it. For a 2026 in-season product use Sentinel-2 L2A directly.

Product facts (NASA Earthdata page): 30 m NBAR, from Sentinel-2A, 2B and 2C; scale factor 0.0001; fill -9999; Fmask fill 255; angle bands scale 0.01; one COG per band; MGRS tiles. Fmask bits: 1 cloud, 2 adjacent to cloud or shadow, 3 cloud shadow, 4 snow/ice, 5 water, 6-7 aerosol level. Asset links are `https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/HLSS30.020/...` plus `s3://lp-prod-protected/...` in us-west-2 (Inference from the bucket name: Earthdata Login needed to read; search is anonymous). STAC collection id at CMR is `HLSS30_2.0`.

Band names differ between the two HLS products. S30: `B04` red, `B8A` narrow NIR, `B11` SWIR1, `B12` SWIR2. L30: `B04` red, `B05` NIR, `B06` SWIR1, `B07` SWIR2. Inference: the Earth Engine copies are already in reflectance units, since the catalog example displays 0.01 to 0.18.

### 2.8 Planetary Computer, Earth Search, Copernicus Data Space

**Planetary Computer (tested today, no account, no key).**

- STAC API `https://planetarycomputer.microsoft.com/api/stac/v1` answered collection and search requests.
- `https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a` returned a token with `msft:expiry` 2026-11-14T20:57:22Z. Inference: roughly 45 to 60 minutes of validity for anonymous callers outside Azure, so re-sign inside long jobs.
- Docs source: "Datasets in the Planetary Computer are anonymously accessible: you don't need to supply a subscription key". Keys give "more favorable" limits; no numbers are published.
- Sign with `planetary_computer.sign(...)` or `pystac_client.Client.open(url, modifier=planetary_computer.sign_inplace)`.

| Collection | Extent | Storage region | Note |
|---|---|---|---|
| `sentinel-2-l2a` | 2015-06-27 to open | westeurope | band keys `B02`..`B12`, `B8A`, `SCL`; items carry no scale or offset metadata |
| `sentinel-1-grd` | 2014-10-10 to open | westeurope | no account needed; includes 1C and 1D items |
| `sentinel-1-rtc` | 2014-10-10 to open | westeurope | **account required** |
| `hls2-s30`, `hls2-l30` | 2020-01-01 to open | westeurope | same lag as NASA |
| `naip` | 2010 to 2025-12-31 | westeurope | California 2024, 2022, 2020 at 0.6 m |
| `usda-cdl` | 2008 to **2021** | westeurope | stale |
| `gridmet` | 1979 to **2020** | westeurope | stale; Zarr |

Not verified: the Hub retirement notice and any Planetary Computer Pro announcement (those pages are JavaScript-only and returned no text).

**Earth Search** (`https://earth-search.aws.element84.com/v1`). Nine collections: `sentinel-2-l2a`, `sentinel-2-c1-l2a`, `sentinel-2-pre-c1-l2a` ("baseline < 05.00"), `sentinel-2-l1c`, `sentinel-1-grd` (requester pays), `landsat-c2-l2`, `naip` (to 2022), two Copernicus DEMs. No HLS. Sentinel-2 COGs are public at `sentinel-cogs.s3.us-west-2.amazonaws.com`; asset keys `red`, `green`, `blue`, `nir`, `nir08`, `rededge1`-`3`, `swir16`, `swir22`, `scl`. The newest item for 15TVG shows `earthsearch:boa_offset_applied: true` and also `raster:bands` scale 0.0001 with offset -0.1 (see the trap in 2.9).

**Copernicus Data Space, free "Copernicus General" quotas.** Sentinel Hub: 10,000 processing units and 10,000 requests per month, 300 per minute, 2 concurrent requests. openEO: 10,000 credits per month, 12 requests per minute. Catalogue and S3: 2,000 requests per minute, 4 concurrent connections, 20 MB/s each, 12 TB per rolling 30 days.
Inference: far too small for 10^4 to 10^5 field time series. Not a path for this weekend.

### 2.9 Sentinel-2 reflectance offset and other optical traps

- Earth Engine: "After 2022-01-25, Sentinel-2 scenes with PROCESSING_BASELINE '04.00' or above have their DN (value) range shifted by 1000. The HARMONIZED collection shifts data in newer scenes to be in the same range as in older scenes." So in `S2_SR_HARMONIZED`, reflectance = DN x 0.0001 for every date.
- Planetary Computer serves the original values and gives no offset field. Every 2025 and 2026 scene is baseline 05.11 or later. Inference: reflectance = (DN - 1000) x 0.0001 there.
- Earth Search trap: the same item says the offset is already applied and also advertises an offset of -0.1. I could not open the collection note that resolves this. Read a dark target (water) before trusting either: values near 1000 mean the shift is still in the data.
- Native 20 m bands: `B5`, `B6`, `B7`, `B8A`, `B11`, `B12`, `SCL`. Native 10 m: `B2`, `B3`, `B4`, `B8`. Reducing at 10 m adds no information to SWIR indices and costs four times the pixels.
- `QA60` is masked out from 2022-01-25 through 2024-02-28 in Earth Engine. Use Cloud Score+ (`cs_cdf >= 0.60`), joined with `linkCollection`.
- Useful properties: `MGRS_TILE`, `SENSING_ORBIT_NUMBER`, `CLOUDY_PIXEL_PERCENTAGE`, `PROCESSING_BASELINE`, `SPACECRAFT_NAME`.
- Landsat Collection 2 Level 2: reflectance = DN x 0.0000275 - 0.2; `QA_PIXEL` bits: 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow, 5 snow, 6 clear.

### 2.10 Weather for growing-degree-days

| Source | Where | Through | Grid | Units |
|---|---|---|---|---|
| gridMET | `IDAHO_EPSCOR/GRIDMET` | 2026-11-11 (3 days behind) | about 4.6 km | `tmmx`, `tmmn` Kelvin |
| PRISM daily | `OREGONSTATE/PRISM/ANd` | 2026-11-10 | about 4.6 km in Earth Engine | degrees C; re-modeled up to 8 times over six months |
| Daymet V4 | `NASA/ORNL/DAYMET_V4` | 2025-12-31 | 1 km | degrees C; good for 2025, absent for 2026 |
| gridMET on Planetary Computer | `gridmet` Zarr | 2020 | | stale |

gridMET covers both seasons with one code path. NASA POWER was not opened in this run.

### 2.11 NAIP for California

Planetary Computer items over San Joaquin County: 2024-06-14, 2022-06-14 and 2020-06-17, all 0.6 m. Earth Engine's NAIP ends 2023-11-17; Earth Search's ends 2022. Inference: June flights predate corn harvest, so NAIP is context (dairies, lagoons, field edges), not a harvest signal.

### 2.12 NASS Quick Stats API

- Endpoints under `https://quickstats.nass.usda.gov/api/`: `api_GET` (data, at most **50,000 records** per request), `get_counts` (row count for a query), `get_param_values`.
- Key by email form. Example: `https://quickstats.nass.usda.gov/api/api_GET/?key=api key&commodity_desc=CORN&year__GE=2012&state_alpha=VA&format=JSON`.
- Parameters include `commodity_desc`, `util_practice_desc`, `statisticcat_desc`, `unit_desc`, `short_desc`, `agg_level_desc`, `state_alpha`, `county_code`, `year`, `reference_period_desc`. Operators `__GE`, `__LE`, `__LIKE`. Formats JSON, CSV, XML.
- No numeric rate limit is published. Required notice: "This product uses the NASS API but is not endorsed or certified by NASS."
- From memory, not verified: `short_desc` values such as `CORN, SILAGE - ACRES HARVESTED` and `CORN, GRAIN - ACRES HARVESTED`. Confirm with `get_param_values`.

### 2.13 Software versions (PyPI and docs, today)

| Package | Latest | Released | Python | Note |
|---|---|---|---|---|
| `cudf-cu12` | 26.10.2 | 2026-10-22 | >= 3.11 | `cudf-cu13` also exists |
| `cuml-cu12` | 26.10.0 | 2026-10-08 | >= 3.11 | `%load_ext cuml.accel` before importing scikit-learn; falls back to CPU when unsupported |
| `cuspatial-cu12` | **25.4.0** | **2025-04-10** | 3.10-3.12 | no release in 19 months |
| `xgboost` | 3.4.1 | 2026-08-15 | **>= 3.12** | GPU: `device="cuda"`, `tree_method="hist"`; docs say "CUDA >= 12.9 is required" |
| `exactextract` | 0.3.0 | 2025-12-01 | >= 3.9 | `pip install exactextract` |

- RAPIDS install docs now live at `https://docs.nvidia.com/datascience/install/`. Requirements: CUDA 12 with driver 525.60.13 or newer, or CUDA 13 with driver 580.65.06 or newer; glibc >= 2.28; GPU compute capability 7.0 or higher. The install selector did not render, so the exact pip line is not verified. From memory: `pip install --extra-index-url=https://pypi.nvidia.com cudf-cu12 cuml-cu12` and `%load_ext cudf.pandas`.
- XGBoost GPU notes: `QuantileDMatrix` for memory, `inplace_predict` when data is on the GPU, and GPU SHAP with `booster.predict(dtrain, pred_contribs=True)` after `booster.set_param({"device": "cuda:0"})`.
- exactextract: two strategies, feature-sequential (default, least memory) and raster-sequential (each pixel read once). Its own benchmark: mean of a 1,555-step grid over 67 Florida counties took "24:20.21" with one chunk per grid and 10 to 13 seconds after rechunking. `max_cells_in_memory` defaults to 30 million.
- xarray-spatial `zonal_stats` needs zones as an integer raster and returns a pandas DataFrame. The page I opened says nothing about GPU backends.
- odc-stac `load`: `groupby="solar_day"`, `chunks={'x': 2048, 'y': 2048}`, `crs="utm"`, `resolution`, `patch_url=pc.sign`, `fail_on_error=False`; overlapping items are fused by copying valid pixels in a deterministic order.

## 3. Formulas with band names

| Quantity | Formula | Sentinel-2 (Earth Engine) | HLS S30 | HLS L30 | Landsat C2 L2 |
|---|---|---|---|---|---|
| NDVI | (NIR - red) / (NIR + red) | `B8`, `B4` | `B8A`, `B04` | `B05`, `B04` | `SR_B5`, `SR_B4` |
| NDMI | (NIR - SWIR1) / (NIR + SWIR1) | `B8A`, `B11` | `B8A`, `B11` | `B05`, `B06` | `SR_B5`, `SR_B6` |
| NDTI (same bands as NBR2) | (SWIR1 - SWIR2) / (SWIR1 + SWIR2) | `B11`, `B12` | `B11`, `B12` | `B06`, `B07` | `SR_B6`, `SR_B7` |
| STI | SWIR1 / SWIR2 | `B11` / `B12` | same | `B06` / `B07` | `SR_B6` / `SR_B7` |

Scale before computing: Sentinel-2 in Earth Engine DN x 0.0001; HLS from NASA DN x 0.0001 (fill -9999); Landsat DN x 0.0000275 - 0.2.

Other quantities:

- **Green at cut** = index at the last clear scene before the cut, divided by the season peak of the same index.
- **Cross ratio** = `VH` / `VV` in linear power, which equals VH_dB - VV_dB.
- **Radar vegetation index** = 4 x `VH` / (`VV` + `VH`), in linear power.
- **Corn growing-degree-days, 86/50 method** = ((min(max(Tmax, 50), 86) + min(max(Tmin, 50), 86)) / 2) - 50 in degrees F. With gridMET: `tmmx` and `tmmn` minus 273.15, clamp each to 10-30 C, average, subtract 10, multiply by 1.8.

The radar vegetation index and the 86/50 method are standard formulas written from memory; neither was re-checked against a source in this run. Average radar backscatter in linear power, then convert to dB.

## 4. Recipes

None of this code was executed. I had no Earth Engine credentials and was told not to install software.

### 4.1 Fast path: Earth Engine to Parquet

```python
import ee, time, pandas as pd
from concurrent.futures import ThreadPoolExecutor

ee.Authenticate(auth_mode='notebook')      # open the printed URL on a laptop, paste the code back
ee.Initialize(project='YOUR_EE_PROJECT')   # standard endpoint on purpose (section 2.2)

CORN = [1, 225, 226, 228, 237, 241]        # flag 12 and 13 separately
S2   = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
CSP  = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')
RED  = (ee.Reducer.mean()
          .combine(ee.Reducer.stdDev(), sharedInputs=True)
          .combine(ee.Reducer.count(),  sharedInputs=True))

def s2_prep(img):
    clear = img.select('cs_cdf').gte(0.60)
    sr = img.select(['B4', 'B8', 'B8A', 'B11', 'B12']).multiply(0.0001)
    idx = ee.Image.cat([
        sr.normalizedDifference(['B8',  'B4']).rename('ndvi'),
        sr.normalizedDifference(['B8A', 'B11']).rename('ndmi'),
        sr.normalizedDifference(['B11', 'B12']).rename('ndti'),
    ]).updateMask(clear)
    return ee.Image(idx.copyProperties(
        img, ['system:time_start', 'MGRS_TILE', 'SENSING_ORBIT_NUMBER', 'SPACECRAFT_NAME']))

def s2_table(fields, bbox, start, end):
    def per_image(img):
        img = ee.Image(img)
        meta = {'t': img.get('system:time_start'), 'tile': img.get('MGRS_TILE'),
                'orb': img.get('SENSING_ORBIT_NUMBER'), 'sat': img.get('SPACECRAFT_NAME')}
        return (img.reduceRegions(collection=fields, reducer=RED, scale=20, tileScale=2)
                   .filter(ee.Filter.notNull(['ndvi_mean']))
                   .map(lambda f: f.setGeometry(None).set(meta)))
    ic = (S2.filterBounds(bbox).filterDate(start, end)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80))
            .linkCollection(CSP, ['cs_cdf']).map(s2_prep))
    return ic.map(per_image).flatten()

def fetch(chunk_id, fields, bbox, start='2025-04-01', end='2025-12-01', tries=4):
    for k in range(tries):
        try:
            df = ee.data.computeFeatures({'expression': s2_table(fields, bbox, start, end),
                                          'fileFormat': 'PANDAS_DATAFRAME'})
            df.drop(columns=['geo'], errors='ignore').to_parquet(f'ts/s2_{chunk_id}.parquet')
            return chunk_id, len(df)
        except Exception:
            time.sleep(5 * 2 ** k)
    return chunk_id, -1
```

Operating notes:

- Chunk 300 to 500 fields that are close together (same county), pass the chunk's bounding box as `ee.Geometry.Rectangle`, run 20 to 30 threads (quota is 40), skip chunks whose Parquet file exists so the job can resume.
- Each request must finish in five minutes and return under 100 MiB. If a chunk times out, halve it or split the date range.
- Fields: either build each chunk from local geometry (300 simplified polygons stay well under the 10 MB payload) or filter the NASS per-state collections server-side by county and crop code.
- Buffer polygons inward by 20 m before reducing (in EPSG:5070 with GeoPandas) and drop fields with fewer than about 10 valid 20 m pixels. `ndvi_stdDev` is a cheap partial-harvest flag.
- `ndvi_count` gives the number of clear pixels per field and date. Keep rows only when it is at least 60 to 70% of the field's maximum count.

### 4.2 Sentinel-1 on the same pattern

```python
S1 = (ee.ImageCollection('COPERNICUS/S1_GRD_FLOAT')          # linear power; page not opened, see 2.1
        .filter(ee.Filter.eq('instrumentMode', 'IW'))
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')))

def s1_per_image(img):
    img = ee.Image(img)
    meta = {'t': img.get('system:time_start'), 'pass': img.get('orbitProperties_pass'),
            'relorb': img.get('relativeOrbitNumber_start'), 'sat': img.get('platform_number')}
    red = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)
    return (img.select(['VV', 'VH']).reduceRegions(collection=fields, reducer=red, scale=20, tileScale=2)
               .filter(ee.Filter.notNull(['VV_mean']))
               .map(lambda f: f.setGeometry(None).set(meta)))
```

- With `COPERNICUS/S1_GRD` (dB) convert first: `ee.Image(10).pow(img.select(['VV', 'VH']).divide(10))`.
- OPERA alternative: `ee.ImageCollection('OPERA/RTC/L2_V1/S1')`, `img.updateMask(img.select('mask').eq(0))`, `scale=30`, metadata `ORBIT_PASS_DIRECTION`, `TRACK_NUMBER`, `BURST_ID`.
- Build one series per field per `relorb`. Never difference across tracks or across ascending and descending passes.

### 4.3 Growing-degree-days from gridMET

```python
gm = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET').filterDate('2025-04-01', '2025-12-01')
def gdd(img):
    tmax = img.select('tmmx').subtract(273.15).clamp(10, 30)
    tmin = img.select('tmmn').subtract(273.15).clamp(10, 30)
    return (tmax.add(tmin).divide(2).subtract(10).multiply(1.8).rename('gdd_f')
                .set('system:time_start', img.get('system:time_start')))
stack = gm.map(gdd).toBands()                       # one band per day
pts = ee.FeatureCollection(centroid_features)       # INSIDE_X / INSIDE_Y from the boundaries
df = ee.data.computeFeatures({'expression': stack.reduceRegions(pts, ee.Reducer.first(), scale=4638.3),
                              'fileFormat': 'PANDAS_DATAFRAME'})
```

The grid is 4.6 km, so one point per county or per 4 km cell is enough. Cumulate client-side.

### 4.4 Radar calendar for any point (no login)

```python
import io, requests, pandas as pd
URL = ('https://api.daac.asf.alaska.edu/services/search/param?platform=Sentinel-1&processingLevel=GRD_HD'
       '&beamMode=IW&intersectsWith=POINT({lon}%20{lat})&start=2025-08-15T00:00:00Z'
       '&end=2025-11-15T00:00:00Z&output=csv&maxResults=250')
cal = pd.read_csv(io.StringIO(requests.get(URL.format(lon=-88.55, lat=44.05), timeout=60).text))
print(cal.columns.tolist())      # granule name, acquisition date, path number, pass direction
```

Run it once per county centroid. The largest gap per county is the honest radar timing resolution for that county.

### 4.5 Fallback path: STAC, odc-stac, zone raster, CuPy

```python
import pystac_client, odc.stac, numpy as np, cupy as cp, rasterio.features

cat = pystac_client.Client.open('https://earth-search.aws.element84.com/v1')
items = cat.search(collections=['sentinel-2-l2a'], bbox=bbox, datetime='2025-04-01/2025-11-30',
                   query={'eo:cloud_cover': {'lt': 80}}).item_collection()
ds = odc.stac.load(items, bands=['red', 'nir08', 'swir16', 'swir22', 'scl'], crs='utm', resolution=20,
                   bbox=bbox, groupby='solar_day', chunks={'x': 2048, 'y': 2048}, fail_on_error=False)

gbox = ds.odc.geobox
shapes = ((g, i + 1) for i, g in enumerate(fields.to_crs(gbox.crs).geometry.buffer(-20)) if not g.is_empty)
zones = cp.asarray(rasterio.features.rasterize(shapes, out_shape=gbox.shape, transform=gbox.affine,
                                               fill=0, dtype='int32')).ravel()
n = int(zones.max()) + 1
for t in ds.time.values:
    sl  = ds.sel(time=t).compute()
    ok  = cp.isin(cp.asarray(sl.scl.values).ravel(), cp.asarray([4, 5, 6, 7]))
    red = cp.asarray(sl.red.values,   dtype=cp.float32).ravel() * 1e-4     # check the offset first (2.9)
    nir = cp.asarray(sl.nir08.values, dtype=cp.float32).ravel() * 1e-4
    ndvi = (nir - red) / (nir + red)
    w = ok & cp.isfinite(ndvi)
    cnt  = cp.bincount(zones, weights=w.astype(cp.float32), minlength=n)
    mean = cp.bincount(zones, weights=cp.where(w, ndvi, 0), minlength=n) / cnt
```

- Planetary Computer variant: `Client.open('https://planetarycomputer.microsoft.com/api/stac/v1', modifier=planetary_computer.sign_inplace)`, bands `B04`, `B8A`, `B11`, `B12`, `SCL`, reflectance = (DN - 1000) x 0.0001.
- The scene-classification values kept above (4 vegetation, 5 not vegetated, 6 water, 7 unclassified) are the standard Sen2Cor legend from memory.
- Sparse fields: use `exactextract` or windowed reads per field instead of whole tiles.

### 4.6 Clean-up that every path needs

```python
df['utc'] = pd.to_datetime(df['t'], unit='ms', utc=True)
df['local_date'] = (df['utc'] + pd.to_timedelta(df['lon'] / 15.0, unit='h')).dt.date   # solar time
df = (df.sort_values('ndvi_count', ascending=False)
        .drop_duplicates(['field_id', 'local_date', 'sat', 'orb']))                    # tile-overlap twins
```

### 4.7 Checks to run before trusting anything

```python
pt = ee.Geometry.Point(-88.55, 44.05)
print(ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(pt)
        .filterDate('2025-09-01', '2025-10-15').aggregate_histogram('platform_number').getInfo())
print(ee.FeatureCollection('projects/nass-csb/assets/CSB1825_rev23/CSBWI1825').first().propertyNames().getInfo())
with ee.profilePrinting():
    fetch('pilot', pilot_fields, pilot_bbox)        # EECU-time for 200 fields
```

## 5. Gotchas checklist

1. **UTC date is not the local date for radar.** Ascending passes over Iowa are at about 00:05 to 00:13 UTC, which is about 19:05 Central Daylight Time on the previous calendar day. Over the San Joaquin Valley, ascending is about 01:59 UTC (18:59 Pacific Daylight Time the day before) and descending about 14:00 UTC (07:00 local). Sentinel-2 passes at about 17:05 to 17:22 UTC, late morning on the same date. Convert to local solar date before computing "dry-down days".
2. **Dawn and dusk passes differ.** Inference: dew at 07:00 changes backscatter, so keep descending and ascending series separate.
3. **Tile overlap and orbit side-lap.** Tile 15TVG is seen from relative orbits 69 and 112. Fields in overlaps get twice the observations at different view angles, and the same datatake can appear in two MGRS tiles. Deduplicate on field, local date, satellite and orbit.
4. **The 1000 shift** (2.9). Right in Earth Engine's harmonized collection, your job on Planetary Computer, ambiguous on Earth Search.
5. **20 m bands.** Reduce at `scale=20`.
6. **dB averaging.** Average power, then take the log.
7. **Border noise.** Earth Engine applies GRD border noise removal, but drop any radar observation whose valid-pixel count is below the field's usual count.
8. **`QA60` gap** 2022-01-25 to 2024-02-28. Use Cloud Score+.
9. **HLS band names** differ between S30 and L30 (2.7).
10. **`platform_number` and `SPACECRAFT_NAME`** documentation lists only older satellites; 1C, 1D and 2C data exist. Check the histogram (4.7).
11. **Class 1 is not "corn" in California** (2.4).
12. **Python version.** `xgboost` 3.4.1 needs Python 3.12 or later; pip silently installs an older release on 3.10 or 3.11. That is fine, `device="cuda"` still works on older 2.x and 3.x releases (from memory).

## 6. Throughput estimates (all Inference; measure in a pilot)

- **Size of the census.** 98.8 million corn acres at something like 60 acres per polygon is roughly 1.5 million corn polygons. The Crop Sequence Boundaries hold 15,973,106 polygons for all crops. A wall-to-wall run is 15 to 150 times the 10^4 to 10^5 envelope.
- **Rows.** 10^5 fields x about 45 clear Sentinel-2 dates plus about 25 radar dates is about 7 million rows, a few hundred megabytes of Parquet. cudf.pandas handles the feature engineering in seconds; the GPU does nothing for the download.
- **Earth Engine wall time.** Chunks of 300 fields over one season typically return in tens of seconds to a few minutes. At 25 threads, 10^4 fields is on the order of 10 minutes and 10^5 fields on the order of 1 to 2 hours, if quota holds.
- **Earth Engine quota.** Unknown cost per field-season. The Community tier is 540,000 EECU-seconds a month: at 5 EECU-seconds per field-season that is 108,000 fields, at 50 it is 10,800. The 200-field pilot answers this in five minutes.
- **Fallback volume.** One Sentinel-2 tile-date at 20 m with five bands is about 270 MB uncompressed. Iowa is about 20 tiles x 60 usable dates, on the order of 150 GB of reads: 25 minutes at 100 MB/s, 90 minutes at 30 MB/s. Thirty states is terabytes. The fallback is a one-to-three-state tool.
- **Where the GPU earns its place.** Zone `bincount` on CuPy, cudf.pandas on the long table, XGBoost training and SHAP. I/O and quota dominate everything else.

## 7. What this means for Kernel

**Decisions for tonight**

1. **Whoever owns the Earth Engine project: check its tier now.** Move it to Contributor (1,000 EECU-hours) if a billing account is available. Do not split work across teammates' projects to stretch quota; the terms forbid it. Then run the 200-field pilot and write the EECU number in the repo.
2. **Extract the labeled evaluation fields first** (Sentinel-2, Sentinel-1, gridMET, April to November). It is small and unblocks modeling within the hour.
3. **Corn mask = CDL 2025 classes {1, 225, 226, 228, 237, 241}**, with 12 and 13 flagged. Use the provided CDL or the NASS zip; Earth Engine stops at 2024.
4. **Replace "radar cut date" with a cut interval.** For every field record the last date it was seen standing and the first date it was seen cut, from whichever sensor saw it. The interval width becomes a feature and the uncertainty. Wide intervals go to the "needs review" band. In California radar will usually win; in eastern Wisconsin optical has to.
5. **State rollups from a stratified field sample**, for example 2,000 fields per focus state by county and field size, with a ratio adjustment to NASS planted acres and a sampling interval. This is the difference between fitting in the quota and not, and it is the kind of estimator the judges use themselves.
6. **Drop AlphaEarth as a 2025-season feature.** The latest layer is 2024. If used at all, call it prior-year context.
7. **Pin the 2026 story honestly.** No CDL 2026 until about February 2027, HLS two to three weeks behind, Sentinel-2 L2A and Sentinel-1 current to within days. A "Monday market memo" for 2026 needs last year's mask plus rotation, and should say so.

**Things to say to USDA statisticians, with numbers**

- "Radar could not time harvest in eastern Wisconsin in 2025: one pass every 12 days and none between September 8 and October 2. We report a cut interval, not a cut date."
- "Three Sentinel-2 satellites gave central Iowa 13 looks in 30 days, but six in a row were over 75% cloud."
- "In California 58% of corn validation pixels are in double-crop classes; class 1 alone finds about 39%. Our mask uses the union, which is 88% / 89% producer's / user's."
- "CDL 2025 corn recall is 96% in Iowa and 69% in Pennsylvania, where 19% of reference corn maps as grass/pasture. We scale to NASS planted acres, we do not count pixels."

**New-signal candidates that are cheap to test**

- Dynamic World `bare` and `crops` probabilities after the cut, as an off-the-shelf "ground left" check (10 m, current, but only scenes under 35% cloud).
- Within-field NDVI standard deviation as a "harvest in progress" flag; large dairies chop over several days.
- A per-county radar revisit map from the ASF API as an explicit "where the method is blind" layer.
- OPERA disturbance dates (`VEG-DIST-DATE`): Earth Engine has annual layers for 2023 and 2024 only. Whether harvest registers as disturbance, and whether DIST-ALERT for 2025 is reachable at LP DAAC, is unverified.

## 8. Not verified in this run

- Whether Earth Engine's `COPERNICUS/S1_GRD` includes Sentinel-1C and 1D scenes.
- Batch-task concurrency per noncommercial tier, and how long noncommercial verification takes for a brand-new project.
- EECU cost per field-season.
- Planetary Computer Hub retirement and Pro announcements; numeric SAS rate limits.
- Earth Search offset semantics for `sentinel-2-l2a` versus `sentinel-2-c1-l2a`.
- NASA POWER; the RAPIDS pip command and `cudf.pandas` magic; `COPERNICUS/S1_GRD_FLOAT` band details; Landsat 8 collection end date.
- Quick Stats `short_desc` strings and county-level silage coverage.
- The cause of the HLS lag and whether it affects all tiles (two Midwest tiles checked; the California response was truncated).
- Which year the labeled evaluation fields belong to, and whether the provided boundaries are the 2018-2025 Crop Sequence Boundaries.

## 9. Annotated bibliography (every URL was opened on 2026-11-14)

**Earth Engine catalog**

- https://developers.google.com/earth-engine/datasets/catalog/USDA_NASS_CDL : availability to 2025-01-01, 30 m, class table, band-year notes.
- https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED : bands, scale, baseline 04.00 statement, `QA60` gap, properties.
- https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_CLOUD_SCORE_PLUS_V1_S2_HARMONIZED : bands, thresholds, `linkCollection` example.
- https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD : bands, properties, ingestion statement, pointer to the FLOAT collection.
- https://developers.google.com/earth-engine/guides/sentinel1 : preprocessing steps, border noise date, no terrain flattening.
- https://developers.google.com/earth-engine/datasets/catalog/OPERA_RTC_L2_V1_S1 and https://developers.google.com/earth-engine/datasets/tags/opera : OPERA products in the catalog.
- https://developers.google.com/earth-engine/datasets/catalog/OPERA_DIST_L3_DIST-ANN-HLS_V1 : years 2023-2024, band list, date encoding.
- https://developers.google.com/earth-engine/datasets/catalog/NASA_HLS_HLSS30_v002 and https://developers.google.com/earth-engine/datasets/catalog/NASA_HLS_HLSL30_v002 : extents, bands, Fmask bits.
- https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC09_C02_T1_L2 : scale, offset, `QA_PIXEL` bits.
- https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_GRIDMET : extent, Kelvin, status property.
- https://developers.google.com/earth-engine/datasets/catalog/NASA_ORNL_DAYMET_V4 ; https://developers.google.com/earth-engine/datasets/catalog/OREGONSTATE_PRISM_ANd ; https://developers.google.com/earth-engine/datasets/catalog/OREGONSTATE_PRISM_AN81d : weather alternatives.
- https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL : availability to 2025-01-01, 64 bands, version note of 2025-11-17.
- https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1 : bands, 35% cloud rule.
- https://developers.google.com/earth-engine/datasets/catalog/USDA_NAIP_DOQQ and https://developers.google.com/earth-engine/datasets/tags/usda : NAIP extent; no boundary dataset in the official catalog.
- https://gee-community-catalog.org/projects/csb/ : per-state boundary assets, attribute names, update dates.

**Earth Engine guides**

- https://developers.google.com/earth-engine/guides/noncommercial_tiers : tiers, dates, restricted mode, multi-project rule.
- https://developers.google.com/earth-engine/guides/usage : concurrency, rate, payload, result and storage limits.
- https://developers.google.com/earth-engine/guides/processing_environments : endpoints, five-minute limit, batch limits.
- https://developers.google.com/earth-engine/guides/best_practices : reduction advice.
- https://developers.google.com/earth-engine/guides/computation_overview : EECU definition, profiler.
- https://developers.google.com/earth-engine/guides/auth and https://developers.google.com/earth-engine/guides/service_account : authentication.
- https://developers.google.com/earth-engine/apidocs/ee-image-reduceregions and https://developers.google.com/earth-engine/apidocs/ee-data-computefeatures : signatures.
- https://developers.google.com/earth-engine/docs/release-notes : quota announcement of 2026-01-20, OPERA entries (first 100,000 characters only).
- https://github.com/google/Xee : Xee README.

**NASS**

- https://www.nass.usda.gov/Research_and_Science/Cropland/Release/index.php : download links and sizes; last modified 06/12/2026.
- https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php : release dates, 10 m from 2024, inputs, accuracy statements, pixel-count bias.
- https://www.nass.usda.gov/sites/default/files/Research_and_Science/Cropland/docs/CDL_2025_accuracy_assessments.zip : 49 workbooks dated 2026-02-20; parsed for nine of them.
- https://www.nass.usda.gov/research-and-science/cropland/metadata/meta ; https://www.nass.usda.gov/research-and-science/cropland/metadata/metadata-ca23 ; https://www.nass.usda.gov/research-and-science/cropland/metadata/metadata-ia23 : 2023 state accuracy; national-only metadata from 2024.
- https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php and https://www.nass.usda.gov/research-and-science/crop-sequence-boundaries/metadata-crop-sequence-boundaries-2025 : release, downloads, polygon count, attributes, method.
- https://quickstats.nass.usda.gov/api : API.

**Radar and HLS sources**

- https://api.daac.asf.alaska.edu/services/search/param (seven point queries for 2025, one for 2026) : acquisition calendars.
- https://sentiwiki.copernicus.eu/web/s1-mission : constellation dates.
- https://www.earthdata.nasa.gov/data/projects/opera : OPERA product list and coverage.
- https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlss30-2.0 : HLS S30 scale, fill, bands.
- https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search (four queries; collection id `HLSS30_2.0`) : latest HLS granules.

**Planetary Computer, Earth Search, Copernicus**

- https://planetarycomputer.microsoft.com/api/stac/v1/collections/{sentinel-2-l2a, sentinel-1-rtc, sentinel-1-grd, hls2-s30, usda-cdl, naip, gridmet} : collection metadata.
- https://planetarycomputer.microsoft.com/api/stac/v1/search (Sentinel-2, HLS, Sentinel-1 and NAIP queries) and one item record : freshness, satellites, cloud cover.
- https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a : anonymous token.
- https://raw.githubusercontent.com/microsoft/PlanetaryComputerDataCatalog/main/docs/concepts/sas.md : token documentation.
- https://earth-search.aws.element84.com/v1/collections , one search, and https://github.com/Element84/earth-search : collections, asset keys, offset fields.
- https://documentation.dataspace.copernicus.eu/Quotas.html : free quotas.

**Software**

- https://pypi.org/project/cudf-cu12/ ; https://pypi.org/project/cuml-cu12/ ; https://pypi.org/project/cuspatial-cu12/ ; https://pypi.org/project/xgboost/ ; https://pypi.org/project/exactextract/ : versions and dates.
- https://docs.nvidia.com/datascience/install/ : RAPIDS requirements (redirect target of docs.rapids.ai/install).
- https://xgboost.readthedocs.io/en/stable/gpu/index.html : GPU parameters, CUDA requirement, SHAP.
- https://isciences.github.io/exactextract/performance.html and https://github.com/isciences/exactextract : strategies and benchmark.
- https://odc-stac.readthedocs.io/en/latest/_api/odc.stac.load.html : `load` parameters.
- https://xarray-spatial.readthedocs.io/en/stable/user_guide/zonal.html : zonal statistics inputs.

**Opened but empty or failed**

- https://planetarycomputer.microsoft.com/docs/overview/about and https://planetarycomputer.microsoft.com/docs/concepts/sas/ : JavaScript-only, no text returned.
- https://github.com/microsoft/PlanetaryComputer : README has no status notice.
- https://raw.githubusercontent.com/microsoft/PlanetaryComputerExamples/main/datasets/sentinel-2-l2a/sentinel-2-l2a-example.ipynb : baseline section not within the part read.
- https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_ca25.htm and `metadata_ia25.htm` : 404.
- https://developers.google.com/earth-engine/apidocs/ee-featurecollection-reduceregions : 404 (the function is on `ee.Image`).

**Reproducing the accuracy tables.** Download the accuracy zip above, open each `NASS_CDL_{ST}25_accuracy.xlsx`, sheet "Summary Table" for the per-class rows and sheet "ERDAS Cut-n-paste" for the error matrix (rows are map classes, columns are reference classes; row sum for class 1 equals the user's-accuracy denominator).
