# Dairies and feedlots as a silage prior: location data, haul distance and a feed-demand mass balance

Research note for team Kernel, Hack the Harvest. Compiled Saturday 2026-11-14.

## 0. How this was produced, and what it cannot claim

- **No web searches were possible.** The shared WebSearch budget for this run was already used up when this agent started (0 of the requested 12+ searches executed). Everything below comes from pages and files fetched directly from primary-source URLs, plus my own analysis of the public data files I downloaded. Topics that needed discovery by search (German biogas literature, silage-bunker mapping papers, several state registries) are therefore thin, and are listed as "not opened" in section 10 rather than filled from memory.
- Every number in a "Source says" row was read from the page or file at the URL given, on 2026-11-14. Anything I computed or deduced is prefixed **Inference** or **Own analysis** and names the input files.
- PDFs were read with a small text extractor I wrote for this session (no software installed): `<session scratchpad, not in the repo>`. Downloaded data sits under `<session scratchpad, not in the repo>` (session scratch space, not part of the repo; re-download from the URLs below).
- NASS web addresses: on 2026-11-14 `www.nass.usda.gov` paths either returned 404 or redirected to `sb.nass.usda.gov`. The `sb.nass.usda.gov` addresses below all returned HTTP 200.

## 1. Bottom line

1. **A dairy prior is worth building, but as a mass balance, not as "distance to nearest dairy".** In Wisconsin (Census 2022, 63 counties) milk cows per corn acre explains 87% of the between-county variance in the share of corn chopped for silage, and the one-line rule `share = min(1, k x cows / corn acres)` cuts the county error from 0.112 (state mean) to 0.041 (own analysis).
2. **In California the same prior is nearly useless as a classifier.** 93% of California corn acres were silage in the 2022 Census (county median 97%), dairies in the Central Valley sit a median 1.24 km from the next dairy, and the mass-balance rule does worse than the state mean. The California problem is finding the grain minority (Sacramento Valley and Delta counties), which is a physics job.
3. **One public file gives California dairies with coordinates and herd size**: the Water Boards "Confined Animal Facilities" CSV (updated 2026-11-03, 2.6 MB, no use restrictions): 1,063 active mature-dairy facilities, 1,061 with latitude and longitude, 950 with a herd size, 1.45 million head in total.
4. **There is no national equivalent.** EPA counts 21,279 CAFOs but only 6,772 hold a federal permit, and its table lists Idaho and New York with none. The ECHO download holds 748 dairy-coded permits with current status nationwide (732 with coordinates) against 23,609 licensed dairy herds, and it has no animal counts. Outside California use county herd counts from the Census of Agriculture.
5. **A single national ration does not reproduce NASS silage production.** Corn silage harvested per milk cow runs from 5.8 tons per year in California to 15 to 18 in Wisconsin, Michigan and Minnesota. The coefficient has to be taken per state from last year's NASS totals.
6. **Silage really does not travel**: trucking costs roughly 1 to 2% of the standing crop's value per mile, about ten times the figure for grain, and a 1,000 to 10,000 cow herd can be supplied from a radius of roughly 1 to 8 miles. This is the physical reason the prior works, and a good line for the pitch. These are my derivations from published custom rates; I did not open a published haul-distance figure.
7. **Last year's state total is a soft target.** Silage acres moved a median 8% year to year in dairy states but 25% in Plains and feedlot states (Texas minus 43% then plus 66%), and NASS's own 2025 figures differ between the January 2026 publication and Quick Stats today in 15 of 48 states.

## 2. Location datasets for dairies and feedlots

### 2.1 Verified today

| Source | URL (opened) | Format | Coordinates | Herd size | Licence / access | Vintage | Verdict |
|---|---|---|---|---|---|---|---|
| California Water Boards, CIWQS: "Confined Animal Facilities Regulated by the Water Boards" (a resource of the dataset "Surface Water - Water Quality Regulated Facility Information") | https://data.ca.gov/dataset/surface-water-water-quality-regulated-facility-information ; file on 2026-11-14: https://publish.data.ca.gov/dataset/449407ec-22a5-412b-b934-2cc01481bb06/resource/c16335af-f2dc-41e6-a429-f19edba5b957/download/reg_meas_export_cafo_2026-11-03.csv | CSV, 2.6 MB, 4,856 rows | Yes (`latitude_decimal_degrees`, `longitude_decimal_degrees`) | Yes (`cafo_population`), plus `cafo_type`, `cafo_subtype`, `status`, county, order number | Page lists no restrictions on public use; update frequency irregular | Last updated 2026-11-03 | **Use this for California.** |
| Cal-FF (Stanford RegLab) | https://huggingface.co/datasets/reglab/cal-ff ; code https://github.com/reglab/cal-ff | `facilities.csv` (2,121 rows), plus GeoJSON building footprints | Yes (centroid and bounding box) | No. Has `n_buildings`, `footprint_sq_m`, construction and destruction date bounds | CC0 1.0; addresses redacted | Manuscript dated 2025 | Good cross-check and a herd-size proxy (footprint area). Does not separate dairy from other cattle for most rows. |
| Vista-CA (NASA CMS, ORNL DAAC), doi 10.3334/ORNLDAAC/1726 | https://daac.ornl.gov/NACP/guides/NACP_Vista_CA_CH4_Inventory.html (redirects to the guide PDF) | Shapefiles and KMZ | Yes, EPSG:4326 | No | NASA open data; names and addresses of dairies and feed lots only "through correspondence and approval with the authors" | Built from 2017 Regional Board and 2018 CIWQS data | Superseded by the live CIWQS file. |
| EPA ECHO, ICIS-NPDES national download | https://echo.epa.gov/tools/data-downloads ; file https://echo.epa.gov/files/echodownloads/npdes_downloads.zip (354 MB) | Zip of CSVs | Yes (`GEOCODE_LATITUDE`, `GEOCODE_LONGITUDE` in `ICIS_FACILITIES.csv`) | **No** animal type or count fields | Public, refreshed weekly | Current | Only source with national reach, but covers permit holders only and has no herd size. |
| EPA "NPDES CAFO Permitting Status Report", end of year 2024 | https://www.epa.gov/system/files/documents/2025-09/cafo-status-report-2024.pdf (from https://www.epa.gov/npdes/npdes-cafo-regulations-implementation-status-reports ) | One-page PDF table | No (counts by state) | No | Public | Completed 2025-07-18 | Use to state how incomplete ECHO is. |
| EPA AgSTAR Livestock Anaerobic Digester Database | https://www.epa.gov/agstar/livestock-anaerobic-digester-database ; file https://www.epa.gov/sites/default/files/2020-10/agstar-livestock-ad-database.xlsx | XLSX, 473 projects | No (city, county, state) | Yes for digester farms (`Dairy` column = head feeding the digester) | Public, voluntary reporting | "based on data available through June 2024"; page updated 2026-07-10 | Herd sizes for 343 operating dairy digesters; not a location layer. |
| OpenStreetMap (tag statistics, US extract) | https://taginfo.geofabrik.de/north-america:us/api/4/tag/stats?key=building&value=cowshed | API / PBF | Yes | No | ODbL | 2026-11-13 | **Not usable for dairies**: 1,189 `building=cowshed` objects in the whole US. |
| Wisconsin DNR CAFO permits | https://dnr.wisconsin.gov/topic/CAFO/StatsMap.html ; lookup https://apps.dnr.wi.gov/swampereporting/CAFO/Index | Search form with an export button; statewide map PDF | Page says map points only approximate the main farm location; no coordinate list seen | Not seen | Public | Map file named 2023 | Partly verified: the result table did not load in the fetch, so columns and export format are unconfirmed. |
| Iowa DNR Animal Feeding Operations | https://programs.iowadnr.gov/afoemmp | Search application | Page says it gives active site locations | Page says it gives animal data (detail unconfirmed) | Public | Current | Partly verified; no bulk download seen. |
| Stanford RegLab, "Blind Spots in Environmental Permitting ... Large Dairy Farms in Wisconsin" (Bhaskar, Haslund-Gourley, Treves, Ho; Environmental Challenges, Sept 2026) | https://reglab.stanford.edu/publications/blind-spots-in-environmental-permitting/ | Paper; page says the dataset is public but gives no link | Presumably | Size estimated from barn area | n/a | 2026 | Evidence that permit lists miss large dairies (below). |

### 2.2 What the files contain (own analysis of the downloads)

**California CIWQS CAFO file** (`reg_meas_export_cafo_2026-11-03.csv`):

- 4,856 records; 1,889 with `status = Active`, 2,967 `Historical`.
- `cafo_type`: Dairies 3,089; Feedlots 730; Poultry 267; Other 45; Hogs 7; blank 718.
- Active records with `cafo_subtype = "Mature dairy cattle"`: **1,063 unique facilities, 1,061 with coordinates, 950 with `cafo_population` above zero, summing to 1,447,903 head** (85% of the 1,710,000 milk cows NASS reports for 1 January 2026).
- Herd size among those 950: 10th percentile 270, median 1,063, mean 1,524, 90th percentile 3,452, largest 10,115. 84% of the head are on facilities with 1,000 or more.
- By county (active mature-dairy head): Tulare 412,207 (203 facilities), Merced 244,095 (184), Stanislaus 145,616 (154), Kern 137,662 (42), Kings 131,383 (86), Fresno 95,324 (49), San Joaquin 79,318 (82), Madera 70,742 (25).
- 837 of the 1,063 are enrolled under order `R5-2013-0122` (the Central Valley dairy general order).
- Other active categories useful for a feedlot term: 179 records "Feedlots / Heifers (non dairy affiliated)", 69 "Feedlots / Cattle or cow/calf pairs", 49 "Feedlots / Calf feedlots".
- Caveat: `cafo_population` is missing or zero for 113 active dairies, and the column mixes permitted capacity with reported head (not documented on the page). One non-dairy record carries a population of 567,000; filter by subtype.
- Spacing (874 Central Valley Region 5 dairies): nearest-neighbour distance median **1.24 km** (10th percentile 0.42, 90th percentile 3.74). Mature dairy cattle within 10 km of a dairy: median **39,514** (25th percentile 19,478, 75th 73,367).

**Cal-FF `facilities.csv`**: 2,121 facilities. `animal_type`: cattle 1,577; poultry 314; "dairy, cattle" 183; swine 29; unknown 9. Top counties: Tulare 346, Stanislaus 316, Merced 312, Kings 186, Fresno 155, San Joaquin 153. 161 facilities carry a destruction date between 2015 and 2024, which flags closures. Built from Google imagery, ReGrid parcels, CIWQS permits and Environmental Working Group seed locations, with human validation (dataset card).

**Vista-CA**: 15 layers, "over 230,000 entries". Dairies layer 1,715 points; Feed Lots layer 72 points; Digesters 33 polygons. The guide warns the feed-lot layer was built by keyword match on permit names and "is likely not complete". Inference: 1,715 dairies in the 2017-18 source data against 1,063 active mature-dairy facilities today is a 38% drop, so Vista-CA over-states the current dairy map.

**EPA ICIS-NPDES download** (354,496,557 bytes on 2026-11-14):

| Filter | Permit IDs (with coordinates) | Current: latest version effective or administratively continued (with coordinates) | Current plus expired (with coordinates) | Largest states, current only |
|---|---|---|---|---|
| Dairy code (SIC 0241 or NAICS 112120) | 2,902 (2,418) | **748 (732)** | 1,546 (1,458) | TX 208, WI 160, PA 81, CA 50, FL 48, MI 47, KS 36, MN 26 |
| Beef feedlot code (SIC 0211 or NAICS 112112) | 1,684 (1,432) | **752 (747)** | 1,140 (1,122) | KS 252, IA 156, TX 137, MT 68, CA 25, WY 22 |
| Permit component = "CAFO" (any animal) | 6,724 (6,481) | **2,692 (2,612)** | 5,766 (5,617) | NE 479, KS 394, MN 319, TX 295, NY 265, WI 201, PA 181, MO 136, MT 124 |

Of the CAFO-component permits, 1,086 carry a dairy code, 848 a feedlot code and 4,860 neither, so animal type is unknown for 72% of them. There are no animal-count fields in the download (confirmed against the field list at https://echo.epa.gov/tools/data-downloads/icis-npdes-download-summary). An expired permit can still be an operating farm, so the expired rows are usable as candidate points but need a check against imagery. Idaho has no current dairy-coded or CAFO-component permit in the file; New York has one dairy-coded permit (terminated) but 265 current and 363 expired CAFO-component permits with no animal code.

**EPA CAFO status report, end of 2024** (total CAFOs / CAFOs with NPDES permits): United States **21,279 / 6,772**; California 1,063 / 117; Wisconsin 346 / 343; Idaho 274 / 0; New York 465 / 0; Texas 1,049 / 523; Iowa 3,938 / 162; Minnesota 1,585 / 905; Kansas 429 / 429; Nebraska 1,228 / 434; Pennsylvania 459 / 459; Michigan 292 / 278; New Mexico 171 / 21; Washington 140 / 23; Colorado 217 / 112; South Dakota 437 / 174. The footnote explains why: only CAFOs that discharge need a federal permit, so "the portion of CAFOs that need NPDES coverage can vary from State to State." (EPA's California total of 1,063 CAFOs of all animal types happens to equal my count of 1,063 active mature-dairy facilities in the CIWQS file; they are different quantities.)

**Wisconsin gap** (RegLab 2026 page): farms above 1,000 animal units, roughly 714 adult dairy cows, must apply for a permit; about 30% of farms appear to cross that threshold but lack permits. Counts and accuracy figures are not on the page; the full article (ScienceDirect pii S266701002600209X) was not opened.

**Two EPA products disagree on New York.** The status table lists New York with 465 CAFOs and no NPDES permits, while the ICIS file carries 265 New York CAFO-component permits with current status. I could not resolve this today; treat New York ECHO points as candidate locations only.

**AgSTAR**: 400 operational and 73 under-construction projects; 343 operational projects list dairy. Of 134 projects with co-digestion text, none mention silage, corn or crops. Inference: the German mechanism in which biogas plants pull in silage maize does not operate at visible scale in the US; US digesters are not a non-dairy silage sink worth modelling.

**OpenStreetMap, US extract, 2026-11-13**: `building=cowshed` 1,189; `building=barn` 63,694; `landuse=farmyard` 136,454; `man_made=silo` 133,122; `building=farm_auxiliary` 42,892. Worldwide `building=cowshed` 35,983. Against 23,609 licensed US dairy herds this is far too sparse and untyped.

### 2.3 Not verified today (no URL given on purpose)

HIFLD (the hub page is a script-only application and returned nothing readable); Minnesota MPCA "Feedlots in Minnesota" (the Geospatial Commons address now redirects to a new hub home page, and the MPCA page sits behind a browser check); New York DEC CAFO list (HTTP 403); Washington WSDA dairy programme (404); California CDFA dairy statistics page (404); Texas TCEQ (page opened at https://www.tceq.texas.gov/permitting/wastewater/cafo but it offers no list or map; it names the Dairy Outreach Program Area counties Bosque, Comanche, Erath, Hamilton, Hopkins, Johnson, Rains and Wood); Idaho ISDA, Pennsylvania, Michigan EGLE, New Mexico NMED and Kansas KDHE registries. For those states the practical fallback today is ECHO points (where the state issues federal permits) plus county herd counts.

Related method papers, opened as abstract or summary pages only:

- Ho, Handan-Nader and Liu, "Deep Learning to Map Concentrated Animal Feeding Operations", Nature Sustainability, April 2019 (https://reglab.stanford.edu/publications/deep-learning-to-map-cafos/): North Carolina poultry; the summary page reports 589 additional poultry CAFOs, a 15% increase over the baseline list. Poultry, not dairy.
- Robinson, Chugg, Anderson, Lavista Ferres and Ho, "Mapping industrial poultry operations at scale with deep learning and aerial imagery", arXiv:2112.10988 (https://arxiv.org/abs/2112.10988): NAIP 1 m imagery across the continental US, validated on 10 hand-labelled California counties. Poultry barns only.

## 3. Herd and crop statistics

### 3.1 State level (NASS Quick Stats "2025 State Agriculture Overview", as shown on 2026-11-14)

URL pattern: `https://sb.nass.usda.gov/Quick_Stats/Ag_Overview/stateOverview.php?state=CALIFORNIA`. I downloaded all 48 contiguous states. Milk cows and cattle on feed are 1 January 2026 inventories; crop rows are the 2025 crop. "n/p" means the row is not on the page.

| State | Milk cows | Cattle on feed | Corn planted (ac) | Silage (ac) | Yield (t/ac) | Silage (tons) | Silage share of planted | Tons per milk cow | Silage acres per milk cow |
|---|---|---|---|---|---|---|---|---|---|
| Wisconsin | 1,285,000 | 240,000 | 4,150,000 | 885,000 | 22 | 19,470,000 | 21.3% | 15.2 | 0.689 |
| California | 1,710,000 | 500,000 | 450,000 | 370,000 | 27 | 9,990,000 | 82.2% | 5.8 | 0.216 |
| Idaho | 725,000 | 355,000 | 430,000 | 280,000 | 31 | 8,680,000 | 65.1% | 12.0 | 0.386 |
| New York | 650,000 | n/p | 970,000 | 495,000 | 17 | 8,415,000 | 51.0% | 12.9 | 0.762 |
| Minnesota | 455,000 | 350,000 | 8,900,000 | 360,000 | 23 | 8,280,000 | 4.0% | 18.2 | 0.791 |
| Michigan | 460,000 | 135,000 | 2,350,000 | 340,000 | 22.5 | 7,650,000 | 14.5% | 16.6 | 0.739 |
| South Dakota | 240,000 | 435,000 | 6,850,000 | 390,000 | 17 | 6,630,000 | 5.7% | 27.6 | 1.625 |
| Pennsylvania | 455,000 | n/p | 1,010,000 | 315,000 | 20 | 6,300,000 | 31.2% | 13.8 | 0.692 |
| Iowa | 245,000 | 1,180,000 | 13,550,000 | 250,000 | 25 | 6,250,000 | 1.8% | 25.5 | 1.020 |
| Texas | 705,000 | 2,540,000 | 2,500,000 | 245,000 | 22 | 5,390,000 | 9.8% | 7.6 | 0.348 |
| Kansas | 225,000 | 2,480,000 | 6,800,000 | 230,000 | 23 | 5,290,000 | 3.4% | 23.5 | 1.022 |
| Nebraska | 50,000 | 2,800,000 | 10,700,000 | 220,000 | 21 | 4,620,000 | 2.1% | 92.4 | 4.400 |
| Colorado | 210,000 | 920,000 | 1,490,000 | 200,000 | 23 | 4,600,000 | 13.4% | 21.9 | 0.952 |
| Ohio | 255,000 | 160,000 | 3,400,000 | 200,000 | 22 | 4,400,000 | 5.9% | 17.3 | 0.784 |
| Washington | 235,000 | 275,000 | 225,000 | 99,000 | 27 | 2,673,000 | 44.0% | 11.4 | 0.421 |
| Arizona | 195,000 | 212,000 | 65,000 | 50,000 | 29 | 1,450,000 | 76.9% | 7.4 | 0.256 |
| New Mexico | 230,000 | n/p | 105,000 | 59,000 | 23 | 1,357,000 | 56.2% | 5.9 | 0.257 |

Also on the pages: Texas sorghum silage 210,000 acres and 3,885,000 tons; Kansas sorghum silage 140,000 acres and 2,170,000 tons; California haylage excluding alfalfa 125,000 acres and 1,588,000 tons. Sum over the 48 pages: 6,187,000 silage acres, 135.09 million tons, 21.8 tons per acre. Twelve states hold 71% of the silage acres (WI, NY, SD, CA, MN, MI, PA, ID, IA, TX, KS, NE).

**The NASS numbers themselves moved.** The January 2026 "Crop Production 2025 Summary" (https://sb.nass.usda.gov/Publications/Todays_Reports/reports/cropan26.pdf) gives California 2025 as 420,000 acres planted, 50,000 harvested for grain and 365,000 for silage (the figures in our brief). Quick Stats on 2026-11-14 shows 450,000, 75,000 and 370,000. For silage acres, 15 of 48 states differ between the two: Mississippi minus 33%, Missouri plus 25%, Oregon plus 17%, Indiana minus 15%, Washington plus 11%, Texas minus 7.5% (265,000 to 245,000). The absolute changes sum to 125,000 acres, 2.0% of the US total. I did not find when or why the figures were revised.

### 3.2 Licensed herds (NASS "Milk Production", released 2026-02-20)

https://sb.nass.usda.gov/Publications/Todays_Reports/reports/mkpr0226.pdf. Licensed dairy herds 2024 and 2025: United States 24,645 and **23,609**; California 995 and 960; Wisconsin 5,520 and 5,375; Idaho 350 and 350; New York 2,880 and 2,760; Texas 290 and 280; Pennsylvania 4,680 and 4,360; Minnesota 1,690 and 1,605; Michigan 845 and 825; Washington 280 and 280; New Mexico 95 and 90; Kansas 160 and 130. US 2025 annual average 9,498 thousand milk cows and 24,390 lb of milk per cow. Inference: 402 cows per licensed herd on average.

### 3.3 County level (2022 Census of Agriculture)

Verified URL pattern (California is FIPS 06, Wisconsin 55):

- Table 11, cattle inventory including milk cows by herd-size class: `https://sb.nass.usda.gov/Publications/AgCensus/2022/Full_Report/Volume_1,_Chapter_2_County_Level/California/st06_2_011_011.pdf`
- Table 25, field crops including corn for grain: `.../California/st06_2_025_025.pdf`
- Table 26, forage and silage including "corn for silage or greenchop" and "sorghum for silage or greenchop": `.../California/st06_2_026_026.pdf`

Quick Stats API (https://quickstats.nass.usda.gov/api): base `https://quickstats.nass.usda.gov/api/api_GET/?key=YOUR_KEY&...&format=json|csv|xml`; parameters include `source_desc` (CENSUS or SURVEY), `commodity_desc`, `class_desc`, `statisticcat_desc`, `short_desc`, `agg_level_desc`, `state_alpha`, `year`; `/api/get_param_values/` lists valid values; limit 50,000 records per request; the key is free by email. The item names I would query (`CATTLE, COWS, MILK - INVENTORY`, `CORN, SILAGE - ACRES HARVESTED`, `CORN, GRAIN - ACRES HARVESTED`, `CATTLE, ON FEED - INVENTORY`) match the row labels on the overview pages but were not tested against the API; confirm with `get_param_values`.

Census 2022 headline figures read from the PDFs:

| | California | Wisconsin |
|---|---|---|
| Farms with milk cows, 2022 (2017) | 1,117 (1,653) | 6,216 (9,037) |
| Milk cows, 2022 (2017) | 1,688,202 (1,750,329) | 1,264,272 (1,280,395) |
| Farms with 500+ cows, and their cows | 723 farms, 1,657,610 cows (98%) | 615 farms, 706,794 cows (56%) |
| Farms with 1 to 9 cows | 256 | 706 |
| Corn for silage or greenchop: farms, acres, tons | 1,525; 483,437; 12,251,111 | 5,582; 787,423; 16,167,200 |
| Corn for grain: farms, acres | 234; 34,512 | 20,142; (state acres cell not parsed) |
| Sorghum for silage: acres | 25,742 | not read |

California counties, corn silage acres 2022: Tulare 117,066; Merced 98,715; San Joaquin 51,836; Kings 49,906; Stanislaus 49,163; Kern 36,155; Fresno 27,389; Madera 21,400; Sacramento 14,358; Imperial 5,993. Note that the Census reports 483,437 California silage acres for 2022 while the annual survey figures for 2023 to 2025 are 350,000 to 380,000. I did not open the 2022 survey estimate, so I cannot say how much of that gap is year and how much is method.

## 4. Economics and physics of moving silage

### 4.1 What the custom-rate surveys say

| Source (year, respondents) | URL | Silage rates | Grain or other hauling rates |
|---|---|---|---|
| Ohio Farm Custom Rates 2026 (343 respondents), Ward, Richer, Barker, Bennett | https://farmoffice.osu.edu/sites/aglaw/files/site-library/farmmgtpdf/Ohio%20Farm%20Custom%20Rate%20Summary%202026%20August%204.pdf | Chop, haul, fill **$10.68 per ton** (n=5, range 7.00 to 14.40); **silage trucking $146.25 per hour per truck** (n=4, range 110 to 175, median 150); packing bunker $149 per hour | Grain farm to market $0.19 per bushel at 23.4 miles one way (n=69); field to farm $0.10 per bushel at 12.8 miles one way |
| 2026 Nebraska Agricultural Custom Rates Report (108 responses) | https://cap.unl.edu/sites/unl.edu.ianr.agecon.center-for-ag-profitability/files/media/file/2026-nebraska-custom-rates-report_ada.pdf | **Hauling silage by truck $150 per hour** (n=3, range 100 to 250); chopping, hauling, filling and packing $13.38 per ton (n=4, range 10 to 15); chopping and hauling $11.50 per ton (n=3, range 9 to 13) | Grain truck to storage or elevator $0.16 per bushel; extra $0.07 per bushel beyond 13.4 miles; baled hay or stalks, 20-ton loads, $5.28 per loaded mile |
| 2026 Iowa Farm Custom Rate Survey, ISU Ag Decision Maker A3-10 (205 responses) | https://www.extension.iastate.edu/agdm/crops/pdf/a3-10.pdf | Silage chopping $9.20 per ton (n=10, range 7.00 to 12.00) | Grain by truck, 5 miles one way $0.135 per bushel; 25 miles one way $0.200 per bushel |
| 2025 Land Rental and Custom Rates for Colorado (more than 235 respondents), Beiermann and Tranel, April 2026 | https://abm.extension.colostate.edu/wp-content/uploads/sites/61/2026/04/2025-CustomRates-Final.pdf | Silage chopping and hauling: Eastern region $10.00 to 12.50 per ton (median 10.00); Western region $20.00 to 26.00 (median 23.00) | Hauling corn or sorghum $0.25 to 0.45 per bushel (median 0.30) |
| UC Cooperative Extension, "Sample Costs to Produce Silage Corn, Conservation Tillage, Northern San Joaquin Valley", 2015 | https://coststudyfiles.ucdavis.edu/uploads/cs_public/a9/c5/a9c55e16-83cf-46f3-86b8-436ae2deb41f/15ctsilagecornsanjoaquinvalleyfinaldraftjuly20.pdf | "The custom rate for harvesting and hauling is $10.35 per ton. Additional per ton charges of $2.40 are incurred for hauls greater than one mile, which is included." Bagging adds $7.65 per ton. Yield 32 tons per acre at 70% moisture (range 24 to 38); price $48 per ton "based on the 2013 market" | n/a |

Pricing and practice:

- ISU Ag Decision Maker A1-65, "Pricing Forage in the Field" (updated September 2018), https://www.extension.iastate.edu/agdm/crops/html/a1-65.html: a ton of standing silage is usually worth 8 to 10 times the price of a bushel of corn; one bushel of 15% corn equals 0.135 tons of 65% moisture silage (170 bushels gives 23 tons); custom chopping, hauling and storing taken as $10.00 per ton; the page says a considerable hauling distance adds cost and affects the agreed value.
- UW-Madison Extension, M. Lippert, "Pricing corn silage" (2022), https://dairy.extension.wisc.edu/articles/pricing-corn-silage/: rules of thumb 7 to 10 times the corn price, or 25 to 33% of the hay price; silage harvest costs about $120 per acre more than grain harvest at comparable yield.
- Wisconsin Corn Agronomy blog (3 Sept 2013), http://wisccorn.blogspot.com/2013/09/B045.html: corn at $4 to $7 per bushel corresponds to corn silage at $28 to $51 per wet ton.
- Penn State Extension, Roth and Heinrichs, "Corn Silage Production and Management", https://extension.psu.edu/corn-silage-production-and-management: "Corn silage has some disadvantages, however. It is difficult to market and transport very far." The same passage lists silage as a use "for salvage of stressed or damaged cornfields". Recommended harvest moisture 65 to 70% for horizontal silos; drydown 0.50 to 0.75 points per day.
- UC 2015 study: "Normally, nondairy growers sell the crop standing and the buyer or dairy pays the harvesting costs." The study farm double-crops 145 of 150 rented acres: winter cereal forage "harvested from March through April", corn planted in May, chopped in September.
- Storage loss, Penn State "From Harvest to Feed: Understanding Silage Management" (updated 2023-03-08), https://extension.psu.edu/from-harvest-to-feed-understanding-silage-management: covered bunkers in a Kansas trial recovered almost 90% of dry matter after 180 days (about 10% loss); uncovered silage lost about 75% in the top 10 inches; target density 14 lb dry matter per cubic foot; corn silage in 81 surveyed bunkers averaged 34% dry matter.

### 4.2 Who grows the silage

USDA ERS, MacDonald, Law and Mosheim, "Consolidation in U.S. Dairy Farming", ERR-274, July 2020, https://www.ers.usda.gov/media/8927/err-274.pdf, Table 5 (2016 survey, conventional farms). Purchased share of feed expenses: all farms 53.6%; weighted by cows 70.6%; herds of 10 to 49 cows 44.3%; 200 to 499 cows 63.9%; 1,000 to 1,999 cows 80.1%; more than 1,999 cows **82.7%**. Farms that purchase all feed: 3.1% of farms, 13.7% of cows, **21.1% of herds above 1,999 cows**. Table 6: homegrown feed cost falls from $5.19 per hundredweight of milk in the smallest class to $1.59 in the largest. The report also notes that by 2017 nearly 2,000 farms with 1,000 or more cows held 55% of US cows, and that licensed herds fell from 74,100 in 2002 to 34,187 in 2019. Caveat: "feed" here includes grain and protein, not only silage.

Inference from the Census counts in 3.3: California had 1,525 farms harvesting corn silage but only 861 farms with ten or more milk cows, so at least 664 silage-growing farms (44%) were not dairies. In Wisconsin the counts are close (5,582 silage farms, 5,510 farms with ten or more milk cows). Reading: in California a large part of the silage is grown by neighbours and sold standing; in Wisconsin it is mostly grown by the cattle farm itself. Either way the field is near the cows.

### 4.3 Derived transport numbers (Inference, with assumptions stated)

- **Cost per ton per one-way mile** = (hourly truck rate x 2 / average speed) / payload. With $148 per hour (Ohio and Nebraska 2026), 30 mph and a 20-ton load: **about $0.49**. With 35 mph and 24 tons: $0.35. With 25 mph and a 12-ton straight truck: $0.99. Speed and payload are my assumptions, not survey values. Cross-check: the UC flat surcharge of $2.40 per ton for hauls beyond one mile equals about 5 miles at $0.49.
- **Share of crop value per mile.** Standing silage at 8 to 10 times an assumed $4.20 corn price is $34 to $42 per ton, so $0.49 is about 1.2 to 1.5% of value per mile (0.8 to 2.9% across the range above). Grain: $0.19 to $0.20 per bushel for 23 to 25 miles is about 0.19% of a $4.20 bushel per mile on average, and the marginal Iowa figure (5 to 25 miles adds $0.065) is 0.08% per mile. **Silage is roughly 6 to 19 times more distance-sensitive than grain per dollar of crop, about ten times as a round figure.**
- **Mass.** US 2025 silage yield 21.8 tons per acre against 186.5 bushels x 56 lb = 5.2 tons of grain: 4.2 times the tonnage per acre. At 20 tons per load that is 1.1 truckloads per acre nationally, 1.35 in California (27 t/ac) and 1.55 in Idaho (31 t/ac). A 100-acre field is 110 to 155 loads, moved at about 65% water.
- **Distance bands.** Trucking reaches 10% of standing value at about 7 to 9 miles, equals the whole chop-haul-fill fee ($10.68 to $13.38 per ton) at about 22 to 27 miles, and reaches 50% of standing value at about 35 to 43 miles. I read that as: routine hauls within about 5 miles, a practical limit around 15 to 25 miles, and little beyond. **No published "typical haul is X miles" statement was opened**; treat these bands as medium-to-low confidence.
- **Silage-shed radius.** A herd of H cows needs k x H acres (k from section 3.1). If corn occupies a fraction c of the land and the herd takes a fraction f of it, radius in miles = sqrt(k x H / (pi x 640 x c x f)). With f = 0.5:

| Herd | State k | Corn 10% of land | Corn 25% of land |
|---|---|---|---|
| 300 cows | Wisconsin 0.69 | 1.4 mi (2.3 km) | 0.9 mi (1.5 km) |
| 1,000 cows | Wisconsin 0.69 | 2.6 mi (4.2 km) | 1.7 mi (2.7 km) |
| 3,000 cows | Wisconsin 0.69 | 4.5 mi (7.3 km) | 2.9 mi (4.6 km) |
| 10,000 cows | Wisconsin 0.69 | 8.3 mi (13.3 km) | 5.2 mi (8.4 km) |
| 1,000 cows | California 0.22 | 1.5 mi (2.4 km) | 0.9 mi (1.5 km) |
| 3,000 cows | California 0.22 | 2.6 mi (4.1 km) | 1.6 mi (2.6 km) |
| 10,000 cows | California 0.22 | 4.7 mi (7.5 km) | 3.0 mi (4.8 km) |

## 5. Feed-demand mass balance: does herd times ration reproduce NASS?

### 5.1 State level (own analysis of the 48 overview pages; 31 states publish both milk cows and silage)

- Silage tons = a x milk cows: a = 10.7 tons per cow per year, R squared 0.59. California is over-predicted by 84%, Wisconsin under-predicted by 29%.
- Silage tons = a x milk cows + b x cattle on feed: a = 10.0, b = 1.0, R squared 0.63.
- Same model without California, Texas, New Mexico and Arizona (27 states): **a = 14.4 tons per milk cow, b = 1.32 tons per head on feed, R squared 0.92.**
- The four south-western dry-lot states sit at 5.8 to 7.7 tons per milk cow.

Answers for the five states in the brief (tons of corn silage harvested per milk cow per year, and the equivalent pounds per cow per day as harvested):

| State | Tons per cow | lb per cow per day | Reading |
|---|---|---|---|
| Wisconsin | 15.2 (12.8 in the 2022 Census) | 83 | Matches a corn-silage-heavy ration plus young stock and storage loss. |
| New York | 12.9 | 71 | Same pattern; lower yield (17 t/ac) means more acres per cow (0.76). |
| Idaho | 12.0 | 66 | Same pattern; 355,000 cattle on feed also draw on it. |
| California | 5.8 (7.3 in the 2022 Census) | 32 | Half the northern figure. 1.71 million cows at the northern 14.4 tons would need about 24.6 million tons, or 912,000 acres at 27 t/ac, against 370,000 actual. |
| Texas | 7.6 before feedlots | 42 | With 2.54 million cattle on feed the two-term northern model predicts 13.5 million tons against 5.39 million actual. Texas also cut 3.9 million tons of sorghum silage. |

Inference (ration arithmetic, not from an opened source): one milk cow in inventory stands for about 0.85 lactating cows, 0.15 dry cows and roughly 0.9 replacement heifers. At about 57, 20 and 18 lb of corn silage as fed per day respectively, and 12% loss between field and feed bunk, that is about 77 lb per day or 14 tons per year, which is what the northern states show. California's lower figure is consistent with the double-crop system in the UC study (winter cereal forage ahead of corn) and with other forages and by-products, but I did not open a California ration source.

**Verdict: herd times one national ration does not approximate NASS silage production. Herd times a state coefficient taken from last year's NASS totals does, by construction, and that coefficient is itself a sanity check: it should land between about 0.2 and 0.8 silage acres per milk cow in dairy states.**

### 5.2 County level (own analysis, 2022 Census Tables 11, 25 and 26)

| Test | Wisconsin | California |
|---|---|---|
| Counties with all values disclosed | 64 (63 with grain acres) | 14 (10 with grain acres) |
| Milk cows against corn silage acres, Pearson r | 0.964 | 0.964 |
| Silage acres per milk cow (sum over counties) | 0.623 | 0.291 |
| County silage share of corn acres: range, median | 0.02 to 0.76, 0.18 | 0.50 to 0.99, 0.97 |
| Silage share against milk cows per corn acre | r = 0.931, **R squared 0.87**; share = 0.002 + 0.663 x cows per corn acre; Spearman 0.89 | r = 0.27, R squared 0.07; Spearman 0.73 |
| Mean absolute error of `min(1, k x cows / corn acres)` | **0.041** (k = 0.623) | 0.160 (k = 0.297) |
| Mean absolute error of "every county = state share" | 0.112 (state share 0.204) | 0.098 (state share 0.940) |

Wisconsin examples: Kewaunee 0.50 silage share at 0.84 cows per corn acre; Brown 0.53 at 0.81; Rock 0.05 at 0.12; Waukesha 0.02 at 0.10. California examples: Tulare 0.99, Kings 0.99, Merced 0.96, San Joaquin 0.78, Glenn 0.50, and San Bernardino with 53,074 cows but 1,650 silage acres (dairies that buy feed). The raw cows-against-acres correlation of 0.96 is partly a size effect (big farming counties have more of everything); the share-against-density test is the honest one, and it passes in Wisconsin and fails in California.

### 5.3 How stable is "last year's state total"? (January 2026 summary, 2023 to 2025)

| State | 2023 | 2024 | 2025 | Year-to-year change |
|---|---|---|---|---|
| California | 350 | 380 | 365 | +9%, -4% |
| Wisconsin | 780 | 730 | 885 | -6%, +21% |
| Idaho | 240 | 265 | 280 | +10%, +6% |
| New York | 430 | 455 | 500 | +6%, +10% |
| Pennsylvania | 345 | 320 | 315 | -7%, -2% |
| Texas | 280 | 160 | 265 | -43%, +66% |
| Kansas | 330 | 310 | 230 | -6%, -26% |
| Nebraska | 280 | 280 | 210 | 0%, -25% |
| Iowa | 380 | 340 | 250 | -11%, -26% |
| South Dakota | 520 | 410 | 390 | -21%, -5% |
| North Dakota | 200 | 260 | 170 | +30%, -35% |
| United States | 6,461 | 6,207 | 6,208 | -3.9%, 0.0% |

(thousand acres). Own analysis: mean absolute change 9.9% and median 7.7% across twelve dairy states; mean 24.0% and median 25.0% across ten Plains and feedlot states; across all 48 states the median is 9.9% and the 90th percentile 40%. Inference: herds change by a few percent a year, so the swings are not demand. They fit weather and price decisions (drought-stressed grain corn chopped as salvage), which the Penn State page names as a use of silage. The herd-based figure is a demand floor; the rest is opportunistic and only the imagery can see it.

## 6. Literature on proximity, bunkers and biogas

Honest status: nothing opened today tests distance to dairies or livestock density as a predictor in a remote-sensing classification of silage against grain corn, maps silage bunkers, piles or bags from imagery, or quantifies the German biogas effect.

- Csikos et al. 2019, Sustainability 11(9), 2500 (biogas plant density and silage maize in Germany): not opened, the publisher returned HTTP 403. No numbers are quoted from it.
- A Humboldt University FORLand working paper on silage maize near biogas plants in Brandenburg: not opened, the working-paper page sits behind a bot check.
- Duren et al. 2019, Nature 575, 180-184 (California methane super-emitters), cited in the Vista-CA guide: not opened.
- The county results in 5.2 are, as far as I could establish today, the only quantitative evidence in this note for cattle density predicting silage share, and they are my own computation rather than a published result.

## 7. Pitfalls

1. **Geography shortcut.** A model given dairy distance can score well by learning "Central Valley means silage" and "Corn Belt means grain" without looking at the field. In California the prior alone is 93% right and teaches the judges nothing.
2. **Saturation.** Where cows per corn acre is high (California 2 to 4 cows per corn acre against 0.1 to 0.9 in Wisconsin), every corn field is near demand and distance stops discriminating.
3. **Dairies also buy feed, and some buy all of it.** San Bernardino and Sonoma have tens of thousands of cows and almost no silage acres. 21% of the largest herds bought all feed in 2016.
4. **Non-dairy silage.** Feedlots (1.3 tons per head on feed in the northern fit), cow-calf and backgrounding (South Dakota and North Dakota sit far above any dairy coefficient), and salvage chopping. Digesters are not a factor in the US.
5. **Stale and incomplete maps.** California farms with milk cows fell from 1,653 to 1,117 between 2017 and 2022 and Wisconsin from 9,037 to 6,216; US licensed herds fell 4.2% in 2025 alone. Permit lists miss about 30% of large Wisconsin dairies. ECHO has no current dairy-coded permit in Idaho or New York.
6. **Herd-size semantics.** `cafo_population` may be permitted capacity; Census "milk cows" excludes heifers; ECHO has no counts. Mixing them changes k by tens of percent.
7. **Moving targets.** State silage totals swing by a quarter in Plains states and NASS revises its own figures.

## 8. Recommended prior

### 8.1 Definitions

- `E_j` = cow-equivalents at facility j = milk cows + 0.09 x cattle on feed. The 0.09 is 1.32 / 14.4 from the 27-state fit in 5.1.
- `k_s` = state silage acres per cow-equivalent = last year's NASS corn silage acres / state cow-equivalents. Values from section 3.1 (milk cows only): California 0.216, Idaho 0.386, Washington 0.421, Texas 0.348, Wisconsin 0.689, New York 0.762, Pennsylvania 0.692, Michigan 0.739, Minnesota 0.791.
- `K(d) = exp(-d / d0)` for `d <= d_max`, else 0, with **d0 = 5 km** and **d_max = 25 km**.

### 8.2 Three levels

**County (use everywhere, needs only NASS tables):**

    pi_c = clip( k_s * E_c / corn_acres_c , 0.01, 0.98 )

`E_c` from Census 2022 Table 11 (plus cattle on feed where published), `corn_acres_c` from the CDL. Evidence: Wisconsin R squared 0.87, error 0.041 against 0.112.

**Field, local mass balance (use where facility points with herd sizes exist, i.e. California today):**

    D_i = sum over facilities j of  E_j * K(d_ij)        (demand reaching field i)
    C_i = sum over corn fields f of  acres_f * K(d_if)    (corn supply competing for it)
    pi_i = clip( k_s * D_i / C_i , 0.01, 0.98 )

This is the county formula with a moving, distance-weighted window, so a judge can read it as "within a few miles of this field there are N cows needing A acres of silage, and B acres of corn". A plain 10 km window (cows within 10 km over corn acres within 10 km) is an acceptable first version.

**Where points exist but herd sizes do not (ECHO, Cal-FF, Wisconsin DNR):** set `E_j` = county milk cows / number of points in the county, or share the county herd in proportion to building footprint area (Cal-FF `footprint_sq_m`).

### 8.3 Parameter values and where they come from

| Parameter | Value | Test range | Basis |
|---|---|---|---|
| d0, distance scale | 5 km | 3, 5, 8 km | Silage-shed radii of 1.5 to 8 km for 300 to 10,000 cows (4.3); UC surcharge for hauls beyond one mile; trucking at $146 to $150 per hour |
| d_max, cut-off | 25 km (about 15 miles) | 15 to 40 km | Trucking equals the whole chopping fee at about 22 to 27 miles (4.3, inference) |
| Herd exponent | 1.0 (demand linear in cows) | fixed | Acres needed are proportional to cows; radius then scales with the square root of herd |
| Feedlot weight | 0.09 cow-equivalents per head on feed | 0 to 0.15 | 1.32 / 14.4 from the 27-state fit; weak in Texas |
| k_s | last year's NASS silage acres / state cow-equivalents | three-year mean in Plains states | Section 3.1; volatility in 5.3 |
| Clip | 0.01 to 0.98 | fixed | Keeps the prior from ever deciding alone |

### 8.4 Keeping it an honest tie-breaker

    logit(p_final) = logit(p_physics) + lambda * clip( logit(pi_i) - logit(pi_state), -1.5, +1.5 )

- `lambda = 0` is the physics-only model and is always reported beside the combined one. Start at `lambda = 0.5` and choose it by cross-validation blocked by county.
- Apply the prior only to fields whose physics score falls inside the "needs review" band; fields with a clear cut date, green-at-cut and residue signal are never moved.
- Subtracting the state logit means the prior only shifts fields within a state. It cannot teach the model "California means silage".
- `k_s` comes from last year's NASS data, never from this year's labels.
- Report a three-row ablation on the evaluation set, by state: physics only, prior only, combined, each with precision, recall and false-positive rate for the silage class. If the combined row is not better outside California, drop the prior from the classifier and keep it for the roll-up check.
- Show both numbers on the per-field evidence card ("field signals 0.62, neighbourhood feed demand 0.18, combined 0.47, flagged for review").

### 8.5 Recipes

California points:

    import pandas as pd
    df = pd.read_csv(CAFO_CSV_URL)                      # link on the data.ca.gov page above
    d = df[(df.status == "Active") & (df.cafo_subtype == "Mature dairy cattle")]
    d = (d.sort_values("cafo_population", ascending=False)
           .drop_duplicates("facility_id")
           .dropna(subset=["latitude_decimal_degrees", "longitude_decimal_degrees"]))
    # 1,061 points; fill missing herd with the county median or the Census county mean

ECHO points (no herd size): from `npdes_downloads.zip` read `NPDES_SICS.csv` (keep `SIC_CODE` 0241 dairy, 0211 feedlot), `NPDES_NAICS.csv` (112120, 112112) and `NPDES_PERM_COMPONENTS.csv` (`COMPONENT_TYPE_DESC == "CAFO"`, keyed by `EXTERNAL_PERMIT_NMBR`); join to `ICIS_FACILITIES.csv` on `NPDES_ID` for coordinates; keep `PERMIT_STATUS_CODE` in EFF, ADC, EXP from `ICIS_PERMITS.csv`. `ICIS_PERMITS.csv` contains NUL bytes; strip them before parsing.

Kernel sums: project to an equal-area CRS, build a KD-tree on facility points, query each field centroid within 25 km, sum `E_j * exp(-d / 5 km)`; do the same over corn-field centroids weighted by acres.

Cow-plausibility check on the roll-up: for each county, predicted silage acres x state yield / county milk cows should fall between about 5 and 18 tons per cow in dairy counties; list the counties outside that band in the notebook.

## 9. What this means for Kernel

**Build tonight**

1. Load the California CIWQS file and compute herd-weighted demand per field. It is the only source with coordinates and herd sizes, it is current to 3 November, and it takes minutes.
2. Add the county prior for every state from Census 2022 Tables 11 and 26 (Quick Stats key, or the PDF pattern in 3.3) and use it for the county and state roll-up check.
3. Add the cow-plausibility check to the reconciliation step. It is an independent, explainable test of the roll-up that does not use imagery.
4. Keep the prior out of the main classifier. Wire it in through the capped log-odds term in 8.4 and publish the ablation.

**Change in the plan**

- "Distance to the nearest dairy" should be replaced by local cows per local corn acre. In the Central Valley the nearest dairy is a median 1.24 km from the next one, so plain distance carries almost no information exactly where our demo is.
- In California, describe the prior as a reconciliation check. The discriminating geography there is the reverse: grain corn sits in San Joaquin (22% of corn acres), Glenn (50%), Sacramento and the Delta.
- For Texas and the Plains, do not lean on last year's state total. Say so in the limitations slide.

**Say to the USDA judges**

- "Silage is two-thirds water. Trucking it costs about one to two percent of its value per mile, about ten times grain, so a thousand-cow herd draws its silage from a couple of miles. That is why cattle density predicts silage: in Wisconsin it explains 87% of the county-to-county variation in silage share in your own 2022 Census."
- "We use that only to break ties and to check our totals, and we show the model with it switched off."
- "Our county totals are checked against the cows: tons of silage per cow should land where your state figures put it."
- "Your own 2025 state figures moved between January and now in 15 states, so we report agreement with NASS as a band."

**Innovation angle**: a herd-weighted feed-demand surface from a public regulatory file, and a mass-balance audit of the roll-up, are both "a new data source" in the judging sense and neither needs a model.

## 10. Sources

Opened and read on 2026-11-14 (file sizes are what was downloaded):

1. California State Water Resources Control Board, "Surface Water - Water Quality Regulated Facility Information" (CIWQS), data.ca.gov. https://data.ca.gov/dataset/surface-water-water-quality-regulated-facility-information . CAFO CSV, 2,687,007 bytes.
2. Magesh et al., "Cal-FF: A Comprehensive Dataset of Factory Farms in California Compiled Using Computer Vision and Human Validation", 2025. https://huggingface.co/datasets/reglab/cal-ff and https://github.com/reglab/cal-ff .
3. Hopkins, Rafiq and Duren, "Sources of Methane Emissions (Vista-CA), State of California, USA", ORNL DAAC, 2019. https://daac.ornl.gov/NACP/guides/NACP_Vista_CA_CH4_Inventory.html .
4. US EPA, ECHO data downloads and ICIS-NPDES download summary. https://echo.epa.gov/tools/data-downloads ; https://echo.epa.gov/tools/data-downloads/icis-npdes-download-summary ; https://echo.epa.gov/files/echodownloads/npdes_downloads.zip .
5. US EPA Office of Water, "NPDES CAFO Permitting Status Report: National Summary, Endyear 2024". https://www.epa.gov/system/files/documents/2025-09/cafo-status-report-2024.pdf .
6. US EPA AgSTAR Livestock Anaerobic Digester Database. https://www.epa.gov/agstar/livestock-anaerobic-digester-database .
7. OpenStreetMap taginfo. https://taginfo.openstreetmap.org/api/4/tag/stats?key=building&value=cowshed and the Geofabrik US instance.
8. Wisconsin DNR, CAFO statistics and map. https://dnr.wisconsin.gov/topic/CAFO/StatsMap.html .
9. Iowa DNR Animal Feeding Operations application. https://programs.iowadnr.gov/afoemmp .
10. Stanford RegLab publication pages. https://reglab.stanford.edu/publications/ ; https://reglab.stanford.edu/publications/blind-spots-in-environmental-permitting/ ; https://reglab.stanford.edu/publications/deep-learning-to-map-cafos/ .
11. Robinson et al., arXiv:2112.10988. https://arxiv.org/abs/2112.10988 .
12. USDA NASS, 2025 State Agriculture Overview pages. https://sb.nass.usda.gov/Quick_Stats/Ag_Overview/stateOverview.php?state=CALIFORNIA (and 47 other states).
13. USDA NASS, "Crop Production 2025 Summary", January 2026. https://sb.nass.usda.gov/Publications/Todays_Reports/reports/cropan26.pdf .
14. USDA NASS, "Milk Production", 20 February 2026. https://sb.nass.usda.gov/Publications/Todays_Reports/reports/mkpr0226.pdf .
15. USDA NASS, 2022 Census of Agriculture, county tables 11, 25 and 26 for California and Wisconsin. https://sb.nass.usda.gov/Publications/AgCensus/2022/Full_Report/Volume_1,_Chapter_2_County_Level/Wisconsin/st55_2_026_026.pdf (and the siblings named in 3.3).
16. USDA NASS Quick Stats API documentation. https://quickstats.nass.usda.gov/api .
17. USDA ERS, ERR-274, "Consolidation in U.S. Dairy Farming", 2020. https://www.ers.usda.gov/media/8927/err-274.pdf .
18. Ohio State University Extension, "Ohio Farm Custom Rates 2026". https://farmoffice.osu.edu/farm-management/custom-rates-and-machinery-costs .
19. University of Nebraska, "2026 Nebraska Agricultural Custom Rates Report". https://cap.unl.edu/customrates/ .
20. Iowa State University, Ag Decision Maker A3-10 (2026 Iowa Farm Custom Rate Survey) and A1-65 (Pricing Forage in the Field). https://www.extension.iastate.edu/agdm/crops/pdf/a3-10.pdf ; https://www.extension.iastate.edu/agdm/crops/html/a1-65.html .
21. Colorado State University Extension, "2025 Land Rental & Custom Rates for Colorado Farms & Ranches". https://abm.extension.colostate.edu/custom-rates-survey/ .
22. UC Cooperative Extension, 2015 silage corn cost study, northern San Joaquin Valley. https://coststudies.ucdavis.edu/current (listing) and the PDF in 4.1.
23. UW-Madison Extension, "Pricing corn silage". https://dairy.extension.wisc.edu/articles/pricing-corn-silage/ .
24. Wisconsin Corn Agronomy blog, 3 September 2013. http://wisccorn.blogspot.com/2013/09/B045.html .
25. Penn State Extension, "Corn Silage Production and Management" and "From Harvest to Feed: Understanding Silage Management". https://extension.psu.edu/corn-silage-production-and-management ; https://extension.psu.edu/from-harvest-to-feed-understanding-silage-management .
26. Texas CEQ, CAFO permitting page. https://www.tceq.texas.gov/permitting/wastewater/cafo .

Not opened (so not used as evidence): Nature Sustainability full text of the 2019 CAFO paper (login redirect); MDPI Sustainability 11(9) 2500 (HTTP 403); Journal of Dairy Science review, doi 10.3168/jds.2017-13080 (HTTP 403); HIFLD hub (script-only page); Minnesota MPCA feedlot pages (browser check, moved dataset address); New York DEC CAFO page (403); Washington WSDA and California CDFA dairy pages (404); Central Valley Water Board confined-animal page (empty response); Michigan State pricing articles (empty response); Texas A&M custom rates (403); Humboldt University working-paper list (bot check). No extension source giving corn silage intake per cow per day was opened, and no published statement of a typical or maximum haul distance in miles was opened.
