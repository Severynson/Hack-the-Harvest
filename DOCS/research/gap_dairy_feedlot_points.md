# Gap closed: dairy and beef-feedlot points outside California, and a cited silage haul distance

Research date: Saturday 2026-11-14. Team Kernel, Hack the Harvest.
Scope: public datasets that give dairy and beef-feedlot locations with herd size in Wisconsin, Minnesota, New York, Pennsylvania, Michigan, Idaho, Texas and Kansas (plus Iowa and Nebraska where found), and published figures for how far corn silage is hauled.
This report complements `dairy_prior.md` in the same folder. It does not repeat the California sources or the county mass balance in that file.

How to read the evidence. Every URL below was opened unless it is marked "not opened". Counts marked "live query" came from ArcGIS count or statistics endpoints on 2026-11-14 and are exact. Numbers marked "page reading" were read from a JSON or HTML page through a summarising fetch tool, so re-run them in code before quoting them to a decimal. Lines that start with "Inference:" are my own reasoning, not the source.

---

## 1. Bottom line

1. **The statement "facility points exist only for California" is wrong.** Minnesota publishes every registered feedlot as a point with head counts by animal class (38,374 points, 28,844 active, 3,007 active sites with dairy cows). Michigan publishes 272 permitted CAFOs with mature-dairy head counts, and 21,301 polygons of the fields that receive their manure. Iowa has 10,690 points with animal units by species. New York has 455 CAFO points but no herd size.
2. **There is a national source.** Climate TRACE publishes 48,331 US cattle operations (22,001 dairy, 26,330 beef) with latitude, longitude and a head capacity, free through an API, licence CC BY 4.0. It answers Wisconsin (332 dairies), Texas (633 dairies, 1,741 beef), Kansas (38 dairies, 415 beef), Nebraska, Idaho and Pennsylvania in one call pattern.
3. **Climate TRACE is a compilation of state registries, not an independent measurement, and its herd sizes are real only where the state published them.** New York rows carry one constant (2,760 head) and Pennsylvania rows another (4,360 head). Treat those as missing.
4. **Beef cattle outnumber dairy cows in the Plains and the western Corn Belt.** In Minnesota's own registry, active sites list 912,307 head in `steer_b` and 497,369 in `heifer_b` (beef slaughter or stock cattle, and feeders or heifers; class labels inferred, and stock cows are included) against 618,498 dairy cows. In Iowa's file beef finishing is 1,741,214 animal units against 263,045 for dairy. A dairy-only map would miss most cattle in Kansas, Nebraska, Iowa and Texas.
5. **A cited haul distance now exists.** North Dakota State University Extension (May 2025): "these opportunities will primarily be limited to farmers operating within a few miles of the new dairy" and "the economics of corn silage falls apart when it must be transported longer distances". University of Missouri Extension (November 2024): "I would not want to haul it more than 20 miles." A peer-reviewed Italian study (Manzone et al. 2020) puts the economic limit at 18 km. A Bavarian state cost table (2007) shows the cost per tonne doubling between 2 km and 10 km.
6. **These figures support the kernel already in the plan** (`exp(-d / 5 km)`, cut at 25 km). Nothing found contradicts it.
7. **Registries see permitted and large operations.** Wisconsin has 332 mapped CAFO dairies against thousands of licensed herds. Far from a mapped dairy is weak evidence for grain. Keep the county herd prior underneath the points.

---

## 2. Coverage by state

| State | Best public point source | Points | Herd size | Dairy and beef separable | Status |
|---|---|---|---|---|---|
| Minnesota | MPCA "Feedlots in Minnesota" (ArcGIS REST) | 38,374 (28,844 active) | Yes, head by class and animal units | Yes | Opened, live queries |
| Michigan | EGLE CAFO 2024 layer, plus CAFO Land Application Fields | 272 points, 21,301 polygons | Yes, `MatureDairyCattle` and other cattle | Yes | Opened, live queries |
| Iowa | "animal_feeding_operations" layer built from the State of Iowa AFO database | 10,690 | Animal units by species, not head | Yes | Opened, live queries |
| New York | DEC "Concentrated Animal Feeding Operations (CAFOs)" | 455 | No, only Large or Medium | No species field | Opened, live queries |
| Wisconsin | Climate TRACE (built from DNR CAFO permits) | 332 dairy, 2,127 beef | Yes, units uncertain (head or animal units) | Yes | API opened |
| Texas | Climate TRACE (built from TCEQ permits) | 633 dairy, 1,741 beef | Yes, permitted maximum | Yes | API opened |
| Kansas | Climate TRACE (built from a 2015 state feedlot report) | 38 dairy, 415 beef | Yes for large sites, defaults for the rest | Yes | API opened |
| Nebraska | Climate TRACE | 183 dairy, 2,557 beef | Not checked | Yes | Table only |
| Idaho | Climate TRACE (data requested by email) | 42 dairy, 1,685 beef | Partly, many defaults (130 head) | Yes | API opened |
| Pennsylvania | Climate TRACE (data requested by email) | 606 dairy, 14 beef | No, constant 4,360 in the rows checked | Yes | API opened |

Per-state counts for Climate TRACE are from its methodology table (page reading). Wisconsin and Kansas totals were cross-checked by paging the API.

Count cross-check against EPA's "NPDES CAFO Permitting Status Report, National Summary, Endyear 2024" (completed 18 July 2025), which gives total CAFOs and CAFOs with federal permits: Wisconsin 346 and 343, Minnesota 1,585 and 905, New York 465 and 0, Pennsylvania 459 and 459, Michigan 292 and 278, Idaho 274 and 0, Texas 1,049 and 523, Kansas 429 and 429, Nebraska 1,228 and 434, Iowa 3,938 and 162, California 1,063 and 117, United States 21,279 and 6,772.
https://www.epa.gov/system/files/documents/2025-09/cafo-status-report-2024.pdf

Reading against that table: New York's 455 points match EPA's 465. Michigan's 272 match EPA's 292. Kansas's roughly 453 Climate TRACE rows match EPA's 429. Wisconsin's 332 mapped dairies sit inside EPA's 346 CAFOs. Minnesota's registry (38,374) and Iowa's file (10,690) go far below the CAFO threshold, which is why they are the two richest sources.

---

## 3. Source cards

### 3.1 Minnesota: MPCA "Feedlots in Minnesota"

- Service: https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_pca/env_feedlots/MapServer/0
- Layer "Feedlots", point geometry, `maxRecordCount` 2000, query formats JSON, geoJSON and PBF. Geometry is in EPSG:26915, but `latitude` and `longitude` are attributes.
- The catalogue page (gisdata.mn.gov/dataset/env-feedlots) now redirects to https://gis.data.mn.gov/ and was not opened. A search result for that page says the data are refreshed daily and offered as CSV, Shapefile, GeoPackage and File Geodatabase with no access constraint (search snippet, not opened).
- A search result for an MPCA document says sites with more than 50 animal units (10 in shoreland) must register (search snippet, not opened).

Live queries, 2026-11-14:

| Query | Result |
|---|---|
| All features | 38,374 |
| `status_fdlt = 'active'` | 28,844 |
| `status_fdlt = 'inactive'` | 9,530 |
| Active and (`cattle_dl > 0` or `cattle_db > 0`) | 3,007 |
| Active, sum `cattle_dl` | 74,294 |
| Active, sum `cattle_db` | 544,204 |
| Active, sum `steer_b` | 912,307 |
| Active, sum `heifer_b` | 497,369 |
| Active, sum `bovines_au` | 2,733,696.3 |

`primary_stock` counts across all records: Dairy Cattle >1000 lbs 2,518; Dairy Cattle <1000 lbs 230; Dairy Cattle - Heifer 1,052; Dairy Cattle - Calf 730; Beef Cattle - Slaughter/Stock 6,324; Beef Cattle - Feeder/heifer 3,381; Beef Cattle - Cow & calf pair 6,872; Beef Cattle - Calf 1,400; Swine 55-300 lbs 4,710; null 6,024.

Fields that matter: `name`, `latitude`, `longitude`, `county_name`, `status_fdlt`, `cafo_flag`, `primary_stock`, `au_count`, `animal_count`, `bovines_au`, `cattle_dl`, `cattle_db`, `heifer_d`, `calf_d`, `steer_b`, `heifer_b`, `cow_calf_b`, `calf_b`, `last_animal_date`, `open_lot_flag`, `npdes_sds`. The layer also carries owner and contact names, phone numbers and mailing addresses.

Field meaning, checked by arithmetic on two records:
- NexGen Dairy LLC: 813 x 1.0 + 420 x 0.7 + 445 x 0.2 + 767 x 1.4 = 2,269.8, which equals `au_count`. So `cattle_dl` is dairy cattle under 1,000 lb (1.0 animal unit), `cattle_db` is dairy cattle over 1,000 lb (1.4), `heifer_d` 0.7, `calf_d` 0.2.
- Riverview LLP - Riverview Dairy: 11,389 x 1.4 = 15,944.6, which equals `au_count`.
- Inference: `steer_b` is the "Slaughter/Stock" class and `heifer_b` the "Feeder/heifer" class, from the `primary_stock` labels. Not checked by arithmetic.

Caveats:
- The numbers are registered capacity, not inventory. Inference: expect the dairy total to exceed the NASS milk cow inventory; compare before using it as herd size.
- Inactive records keep their animals. "Darnen Dairy LLP" is inactive, last animal date 15 May 2008, and still lists 4,473 dairy cattle. Filter on `status_fdlt = 'active'`.
- One site can have several records at nearly the same coordinates (Riverview Dairy has an active record with 11,389 cows and an inactive record 1 km east with zero).

Recipe (untested sketch, standard ArcGIS paging):

```
https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_pca/env_feedlots/MapServer/0/query
  ?where=status_fdlt='active' AND bovines_au>0
  &outFields=name,latitude,longitude,county_name,cafo_flag,primary_stock,au_count,bovines_au,cattle_dl,cattle_db,heifer_d,calf_d,steer_b,heifer_b,cow_calf_b,calf_b
  &returnGeometry=false&orderByFields=objectid&resultOffset=0&resultRecordCount=2000&f=json
```
Raise `resultOffset` by 2000 until `exceededTransferLimit` is absent.

### 3.2 National: Climate TRACE cattle operations

- API (beta): `https://api.climatetrace.org/v7/sources?gadmId=USA.50_1&subsectors=enteric-fermentation-cattle-operation&limit=100&offset=0`
- Older form that also works: `https://api.climatetrace.org/v6/assets?countries=USA&subsectors=enteric-fermentation-cattle-operation&limit=5`
- Methodology: https://github.com/climatetracecoalition/emissions-methodology/blob/main/Sector-Methodologies/1-Sectors/agriculture/cattle-operations-asset-level/README.md
- Bulk files: https://zenodo.org/records/18379672 (version 5.2.0, published 18 December 2025, `agriculture.zip` 13.1 GB, licence CC BY 4.0; the page says a newer version exists). Too large for tonight; use the API.
- Data page: https://www.climatetrace.org/data says the API is a beta and "we cannot guarantee availability". Python wrapper: https://github.com/climatetracecoalition/climate-trace-tools/tree/main/climate_trace_tools/api

Record fields (v7): `id`, `name` (for example `USA_Kansas_OtherBeefCattle_5446`), `assetType` (`enteric_fermentation_maturedairycattle` or `enteric_fermentation_otherbeefcattle`), `centroid.latitude`, `centroid.longitude`, `capacity` and `activity` in "animal head(s)", `capacityFactor`, `year`. There is no state or county field; the state is in the name and in the `gadmId` you asked for. An offset past the end returns `null`.

`gadmId` values that returned the expected state: `USA.13_1` Idaho, `USA.17_1` Kansas, `USA.24_1` Minnesota, `USA.33_1` New York, `USA.39_1` Pennsylvania, `USA.44_1` Texas, `USA.50_1` Wisconsin. Inference: the numbering is alphabetical with the District of Columbia at 9, so Iowa 16, Michigan 23, Nebraska 28, South Dakota 42 (not tested). `limit=100` worked; larger limits were not tested.

What the methodology says (page reading):
- US total 48,331 operations: 26,330 beef and 22,001 dairy.
- Seed data are "individual state concentrated animal feeding operation (CAFO) databases", plus EPA ECHO (accessed February 2024), plus satellite detection with Earth Index (Sentinel-2) and TerraDetect (PlanetScope).
- "Not all state CAFO records give cattle values, but most do." Operations without head counts received USDA state-level means. Where a footprint was available, a regression estimated head, capped at 40,000 (beef) or 4,000 (dairy).
- Beef totals reach 116% of the 2022 Census of Agriculture figure and dairy 61%; the authors suggest dairy-to-beef misclassification and census undercoverage.
- State sources named in its Table S1: Wisconsin DNR CAFO page; New York DEC layer `8f81795a3d1745ab9867d0af872e87a1`; Texas TCEQ permit search (www2.tceq.texas.gov/wq_dpa); Kansas Department of Agriculture "2015 annual feedlot report" (PDF); Nebraska cattle feeders directory and NDEE map portal; Iowa geodata; California CIWQS; Idaho and Pennsylvania "requested by email to state government". Minnesota and Michigan are not listed in Table S1 although Minnesota has 14,948 dairy rows.

Per-state counts from its Table 6 (page reading):

| State | Dairy | Beef |
|---|---|---|
| Wisconsin | 332 | 2,127 |
| Minnesota | 14,948 | 3,857 |
| New York | 131 | 1,010 |
| Pennsylvania | 606 | 14 |
| Michigan | not listed | 16 |
| Idaho | 42 | 1,685 |
| Texas | 633 | 1,741 |
| Kansas | 38 | 415 |
| Nebraska | 183 | 2,557 |
| Iowa | 242 | 3,158 |
| California | 1,831 | 846 |
| Colorado | 79 | 1,532 |
| South Dakota | 34 | 2,116 |
| Oklahoma | 31 | 339 |
| Washington | 676 | 359 |

Inference: Minnesota (14,948) and California (1,831) are 76% of all dairy rows. The other 48 states share about 5,200 dairy points.

What the API returned on 2026-11-14 (page reading, sorted by emissions):

| State | Rows checked | Mix | Capacity |
|---|---|---|---|
| Wisconsin | offset 0 to 99 | 100 dairy | 2,613 to 10,800, median 5,375 |
| Wisconsin | offset 100 to 199 | 100 dairy | 1,451 to 2,589 |
| Wisconsin | offset 300 to 399 | 32 dairy, 68 beef | dairy 390 to 959; beef 21.6 to 1,852 |
| Kansas | offset 0 to 99 | 17 dairy, 83 beef | 4,500 to 100,000, median 24,000 |
| Kansas | offset 200 to 299 | 100 beef | 650 to 2,000 |
| Kansas | offset 300 to 399 | 18 dairy, 82 beef | every dairy row 130; 80 beef rows 77.84 |
| Kansas | offset 500 | empty | total is between 400 and 500 |
| Minnesota | offset 0 to 99 | 97 dairy, 3 beef | 1,450 to 12,000, median 2,454.5 |
| Idaho | offset 0 to 99 | 36 dairy, 64 beef | dairy 130 to 14,000, median 350 |
| Texas | offset 0 to 99 | 21 dairy, 79 beef | 7,200 to 125,000, median 40,000 |
| New York | offset 0 to 99 | 99 dairy, 1 beef | 99 rows exactly 2,760 |
| Pennsylvania | offset 0 to 99 | 100 dairy | all exactly 4,360 |

Reading:
- Texas, Kansas (large sites), Minnesota and Wisconsin carry real, varied capacities.
- New York and Pennsylvania carry one repeated value. Inference: these are imputed, because 606 Pennsylvania dairies at 4,360 head would be 2.6 million cows. Use those states for location only.
- Kansas small sites (77.84 and 130) and Idaho (130) are defaults too.
- The five largest US assets all had confidence "very low" in the v6 response.
- Inference: Wisconsin capacities may be animal units, not head. The Wisconsin row at 43.8678, -88.7179 (9,956) sits where a well-known large dairy near Pickett is located. Not verified.

Cross-check that proves the lineage: Climate TRACE asset `USA_Minnesota_MatureDairyCattle_19048` is at 45.523767, -95.887471 with capacity 11,389. The MPCA layer has "Riverview LLP - Riverview Dairy" at 45.52376713, -95.88747143, active, CAFO, `cattle_db` 11,389. Same site, same number. For Minnesota use MPCA directly; it is newer and has the status flag.

Background on the satellite part: Earth Genome, "Detecting cattle operations" (27 February 2026), https://www.earthgenome.org/works/101---detecting-cattle-operations. As summarised by the fetch tool (not verbatim), it describes lightweight classifiers on SSL4EO ViT-DINO embeddings of Sentinel-2 mosaics, about 1,000 farms and feedlots mapped in Kansas and about 2,000 in Nebraska, a precision target near 90%, and half or fewer valid detections when a model is moved to a distant region. It also proposes a "Bovine Slurry Index" for manure ponds; no formula was on the page as read. The page gives no download. Climate TRACE news item on the same work (24 March 2026): https://climatetrace.org/news/saint-louis-university-s-vasit-sagan-and-derek-tesser-on-mapping-cattle-emissions says concentrated operations are "generally facilities with more than ~1,000 head".

### 3.3 Michigan: EGLE CAFO points and manure application fields

Points:
- Service: https://gisagoegle.state.mi.us/arcgis/rest/services/EGLE/ConcentratedAnimalFeedingOperations/FeatureServer (layer 0 is 2024, layer 1 is 2023, layer 2 is pre-2023). `maxRecordCount` 2000.
- Fields in the 2024 layer: `SiteName`, `PermitNumber`, `PermitStatus`, `ReportYear`, `AnimalType`, `MatureDairyCattle`, `CattleAllExceptMatureDairyCattl`, `VealCalves`, swine and poultry classes, `WasteTotalLiquidGal`, `TotAcresAvailableLandApp`, `CAFOTotalAcresUsed`, `County`, `Latitude`, `Longitude`.

Live statistics, 2024 layer:

| AnimalType | Sites | Mature dairy cattle | Other cattle | Acres used for manure |
|---|---|---|---|---|
| Cattle | 147 | 281,405 | 141,187 | 204,767 |
| Mixed | 4 | 3,296 | 2,610 | 3,707 |
| Swine | 104 | 0 | 0 | 27,761 |
| Chicken | 13 | 0 | 0 | 827 |
| Turkeys | 4 | 0 | 0 | 79 |
| Total | 272 | | | |

Polygons:
- "Concentrated Animal Feeding Operation (CAFO) Land Application Fields", item https://www.arcgis.com/sharing/rest/content/items/f6c9d599a6fa4204a1ffc038e78ec6a2?f=json
- Service: https://services1.arcgis.com/FNjlrOFR0aGJ71Tg/arcgis/rest/services/CAFO_Land_Application_Fields_Public_View/FeatureServer/0
- 21,301 polygons (live count), `maxRecordCount` 1000, JSON only. Attributes: `Permittee`, `PermitNum`, `County`. Modified 2 November 2026.
- The description says EGLE staff digitised field boundaries from Comprehensive Nutrient Management Plan maps between 2020 and 2024; accuracy varies; acreages reflect where waste is applied; the department cautions against management decisions based on the layer. The licence text puts no restriction on use, reproduction or distribution.

Inference:
- 204,767 acres over 147 cattle CAFOs is 1,393 acres per site, or 0.73 acres per mature dairy cow.
- These polygons are fields tied by permit number to a named dairy. Fields that take dairy manure are the likeliest silage fields, so this is a field-level silage prior that needs no distance assumption. Nobody on stage will have seen it.
- Joining `PermitNum` to the point layer gives the real distance from each manured field to its dairy. That distribution is a measured "manure shed" and a public-data check on the haul kernel.

### 3.4 New York: DEC CAFO layer

- Item: https://www.arcgis.com/sharing/rest/content/items/8f81795a3d1745ab9867d0af872e87a1?f=json (created 17 March 2023, modified 2 October 2026).
- Layer: https://services6.arcgis.com/DZHaqZm9cxOD4CWM/arcgis/rest/services/Concentrated_Animal_Feeding_Operations__CAFOs_/FeatureServer/33 (the layer id is 33, not 0).
- Fields: `FACILITY_SIZE`, `SPDES_ID`, `FACILITY_NAME`, `MOREINFO`. No species and no head count.
- Live statistics: 455 points, 271 Large and 184 Medium.
- Licence text (summarised by the fetch tool): credit DEC; "Secondary distribution of the data is not allowed."

Use it for counts within a radius. Do not commit the file to the public repository; fetch it at run time.

### 3.5 Iowa: animal feeding operations layer

- Layer: https://services3.arcgis.com/C5aIa0c3gUMji8fg/ArcGIS/rest/services/animal_feeding_operations/FeatureServer/0
- Description (paraphrased by the fetch tool): medium (300 to 999 animal units) and large (1,000 or more) sites; species values are stored as animal units, not head counts (750 swine over 55 lb at a factor of 0.4 equal 300 animal units); sites under 500 animal units need no permit or manure plan. Last edit May 2024.
- Fields: `FacName`, `Lat`, `Long`, `County`, `TotalAU`, `OpType`, `DairyHol`, `DairyJer`, `DairyHeifH`, `BeefFin`, `BeefFeedCa`, `CowCalf`, swine and poultry classes.
- Live statistics: 10,690 points; `DairyHol` 237,963 animal units; `DairyJer` 25,082; `BeefFin` 1,741,214; `BeefFeedCa` 91,655.
- The hosting organisation was not verified. The official DNR service named in search results is `programs.iowadnr.gov/geospatial/rest/services/Agriculture/AnimalFeedingOperations/MapServer` (not opened).
- Undercount: Investigate Midwest (2026; the URL is dated 15 July) reports that the Environmental Working Group found 15,309 livestock facilities, down to 50 animal units, against roughly 11,000 in the DNR database, and quotes the DNR that its database "does not include all animal feeding operations in the state". https://investigatemidwest.org/2026/07/15/researchers-identify-thousands-more-iowa-livestock-facilities-than-state-database-shows/

### 3.6 Wisconsin

- DNR CAFO statistics page: https://dnr.wisconsin.gov/topic/CAFO/StatsMap.html links to a permit search (https://apps.dnr.wi.gov/swampereporting/CAFO/Index, filters for region, county, animal type and permittee, an "Export" label, results did not load in the fetch) and to a 2023 statewide map PDF whose points "are an approximation of the operation's main farm location". No coordinate download was confirmed.
- DATCP: https://datcp.wi.gov/Pages/About_Us/PublicRecords.aspx says lists of licensed "dairy producers" can be downloaded through MyDATCP. The MyDATCP page lists "Milk Producer License Holders" as a portal page, not a file; format and fields were not confirmed. A search result for a DATCP slide deck gives 4,662 Grade A milk producers in August 2026 (snippet, not opened).
- Best source tonight: Climate TRACE, 332 dairies and 2,127 beef rows.
- Inference: 332 mapped dairies against several thousand licensed herds means the points cover under a tenth of herds. They cover the large herds that buy or contract the most silage. Small herds grow silage next to their own barns and are invisible here.

### 3.7 Texas

- Climate TRACE: 633 dairy and 1,741 beef. The largest rows are a 125,000-head feedlot at 36.0153, -102.5886 and a 36,000-head dairy at 36.0264, -102.0861.
- Source named by Climate TRACE: TCEQ water quality permit search (not opened). One search found no TCEQ CAFO GIS layer.
- Inside Climate News repository: https://github.com/InsideClimateNews/2023-08-tx-ca-cattle-methane. Its readme says (paraphrased) that Texas permits state the maximum number of animals allowed on site, while California permits list the most recent recorded numbers. `data/tx_dairies_feedlots.csv` is the scraped permit table (authorisation number, permittee, SIC code where 241 is dairy and 211 is feedlot, county, city, site description) with no coordinates or head counts. The `processed_data` files were not opened.

### 3.8 Kansas, Nebraska, Idaho, Pennsylvania

- Kansas: 38 dairy and 415 beef in Climate TRACE; the largest feedlot row is 100,000 head. The state source it names is a 2015 feedlot report, so the list is eleven years old. One search for a KDHE layer returned only Kansas Register permit notices with legal descriptions.
- Nebraska: 183 dairy and 2,557 beef (table only).
- Idaho: 42 dairy and 1,685 beef. EPA counts 274 CAFOs and no federal permits in Idaho, which is why ECHO is empty there. A Mendeley dataset on Idaho dairy and cropland distribution (data.mendeley.com/datasets/43wkpr2hdg/1) has been removed at the author's request. No ISDA layer was found in one search.
- Pennsylvania: 606 dairy and 14 beef, obtained by Climate TRACE by email, no usable herd size. One search found no DEP GIS layer, only individual permit PDFs.

### 3.9 Other leads checked

- CAFOSat (arXiv 2606.00548, submitted 30 May 2026, accepted at a CVPR 2026 workshop): "more than 45,000 image patches spanning 20 states and four major CAFO categories" on NAIP imagery. The abstract page links no data repository. Not usable tonight. https://arxiv.org/abs/2606.00548
- EPA ICIS-NPDES download: the documentation page lists no CAFO animal-count table; facility coordinates are in `ICIS_FACILITIES.csv`. https://echo.epa.gov/tools/data-downloads/icis-npdes-download-summary (consistent with `dairy_prior.md`).
- EPA FRS REST service: a state plus NAICS query returns an error asking for another search key. Not pursued.

---

## 4. Haul distance: what is published

| Source | Year | What it says | Status |
|---|---|---|---|
| NDSU Extension EC2264, Biermacher, "Considerations for Increasing Corn Silage to Support a Large Dairy" | May 2025 | "these opportunities will primarily be limited to farmers operating within a few miles of the new dairy"; "Unlike corn grain, which is more cost-effective to transport longer distances, the economics of corn silage falls apart when it must be transported longer distances"; a 12,500-head dairy "will require about 80,000 tons of corn silage yearly", about 4,624 acres at 17.3 tons per acre | PDF read in full |
| University of Missouri Extension news, quoting state beef nutritionist Eric Bailey | 11 November 2024 | "Due to the amount of moisture per ton, I would not want to haul it more than 20 miles. Freight will get pricey otherwise"; silage is about two parts moisture to one part dry feed; $45 to $50 per ton as fed | Opened |
| Manzone, Airoldi and Calvo, "Transportation of maize silage to biogas plants", Journal of Agricultural Engineering 51(2): 80-90, doi 10.4081/jae.2020.974 | 2020 | Six routes of 6.2 to 58.2 km with tractors and two trailers; the energy balance is positive even at 58.2 km, but the market value of maize silage (52.00 euro per tonne) "limits the convenience of the transportation distance up to 18 km" | Journal page opened |
| Bavarian State Research Centre for Agriculture (LfL), Mitterleitner, Schilcher and Demmel, "NawaRo-Transport" | November 2007 | Cost table by one-way distance (below); transport capacity per unit is still very high up to 4 km, then falls strongly up to about 10 km (my translation of "bis zu 4 Kilometer noch sehr hoch ... bis etwa 10 Kilometer stark nachlässt"); transport can exceed 30% of delivered substrate cost ("von über 30 %"); at 20 km a chopper needs 9 to 13 transport units; distances "bis über 50 km" occur for very large biogas plants | PDF read in full |
| Virginia Cooperative Extension Farm Management Update | 1997 | "$.50 to $.75 per loaded mile per ton" for long hauls | Search snippet, not opened |
| University of Wyoming budget MP-72.5 | 1994 | Silage assumed hauled "within 7 miles of the field" | Search snippet, not opened |
| Penn State "Trading corn silage guide" | n.d. | Worked example uses 3 miles from field to silo | Search snippet; the page did not load the guide |

NDSU: https://www.ndsu.edu/agriculture/sites/default/files/2025-05/EC2264%20Considerations%20for%20Increasing%20Corn%20Silage%20to%20Support%20a%20Large%20Dairy.pdf
Missouri: https://extension.missouri.edu/news/buying-corn-silage-to-feed-beef-cows-in-winter
Manzone et al.: https://www.agroengineering.org/jae/article/view/974
LfL: https://www.lfl.bayern.de/mam/cms07/publikationen/daten/informationen/p_28561.pdf

LfL cost table, euro per tonne fresh matter, one-way farm-to-field distance (2007 prices, silage maize at 32% dry matter, 50 t/ha):

| km | 2 | 4 | 6 | 8 | 10 | 12 | 15 | 20 | 25 | 30 | 35 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tractor with 25 m3 wagon | 1.9 | 2.7 | 3.2 | 4.0 | 4.3 | 4.9 | 5.6 | 7.2 | 8.7 | 10.2 | 11.7 |
| Tractor with 40 m3 wagon | 1.8 | 2.4 | 2.8 | 3.4 | 3.6 | 4.1 | 4.6 | 5.8 | 6.9 | 8.1 | 9.2 |
| Field transfer plus road train | 2.2 | 2.7 | 3.0 | 3.4 | 3.6 | 3.9 | 4.3 | 5.2 | 6.1 | 6.9 | 7.8 |
| Tonnes per hour per unit, 40 m3 | 38.6 | 28.2 | 24.2 | 20.2 | 19.0 | 16.7 | 14.7 | 11.7 | 9.8 | 8.4 | 7.3 |
| Units needed to keep the chopper running, 40 m3 | 3 | 4 | 5 | 5 | 6 | 6 | 7 | 9 | 11 | 12 | 14 |

Inference from the table: cost is close to linear, about 1.35 + 0.224 x km for the 40 m3 wagon and 1.31 + 0.297 x km for the 25 m3 wagon. That is 0.36 to 0.48 euro per tonne per mile, the same order as the $0.49 per ton per mile derived in `dairy_prior.md` from 2026 US custom rates. Each tonne costs twice as much to move 10 km as 2 km, and the number of trucks needed per chopper doubles between 2 km and 10 km and triples by 20 km. The logistics limit bites before the cost limit.

Distance landmarks in both units: 4 km is 2.5 miles; 10 km is 6.2 miles; 18 km is 11.2 miles; 25 km is 15.5 miles; 20 miles is 32 km.

Inference, checking "a few miles" against the NDSU numbers: 4,624 acres is 7.2 square miles. If corn is 40% of the land and the dairy takes half of it, the supply area is 36 square miles, a radius of 3.4 miles (5.5 km).

How the published figures sit against the plan's kernel `exp(-d / 5 km)`, cut at 25 km: the 5 km scale matches the Bavarian finding that capacity holds up to 4 km and NDSU's "a few miles"; the cut sits between the 18 km economic limit and the 20-mile outer statement. No change needed. Widening the cut to 32 km is defensible for feedlot country.

Feedlots: a University of Nebraska extension article (24 September 2019) describes finishing diets with 15% silage on a dry-matter basis as the low-silage case, 45% as the high case, and backgrounding at 75% for 70 days; it says silage is especially useful "when produced on their own acres". https://www.agproud.com/articles/53989-feeding-elevated-levels-of-corn-silage-in-finishing-diets. A search snippet for a Kansas State 2025 report says silage is commonly 5 to 15% of finishing-diet dry matter (not opened).
Inference: a head of feedlot capacity needs far less silage than a dairy cow. Use the weights the team already fitted on NASS state data in `dairy_prior.md` (14.4 tons per milk cow and 1.32 tons per head on feed, about 0.09 cow-equivalents per feedlot head).

---

## 5. Feature recipes

Harmonised table `cattle_points`: `state`, `source`, `lat`, `lon`, `kind` (dairy or beef), `head` (nullable), `head_known` (bool), `active` (bool).

| State | Source | `kind` rule | `head` rule |
|---|---|---|---|
| MN | MPCA | dairy if `cattle_dl + cattle_db > 0`; beef if `steer_b + heifer_b > 0`; a site can be both | dairy = `cattle_dl + cattle_db`; beef = `steer_b + heifer_b` |
| MI | EGLE 2024 | `AnimalType` in (Cattle, Mixed) | dairy = `MatureDairyCattle`; beef or young stock = `CattleAllExceptMatureDairyCattl` |
| IA | AFO layer | `DairyHol + DairyJer > 0`; `BeefFin + BeefFeedCa > 0` | animal units; Inference: divide dairy by 1.4 to approximate head (factor not verified for Iowa) |
| NY | DEC | unknown | null; use counts |
| others | Climate TRACE | from `assetType` | `capacity`, set to null when the same value repeats many times in a state (2,760; 4,360; 130; 77.84) |

Features per field (centroid in an equal-area projection, KD-tree on points):

1. `d_dairy_km`, `d_feedlot_km`: distance to the nearest active dairy and nearest beef site.
2. `cows_5km`, `cows_10km`, `cows_20km`, `cows_32km`: sum of `head` within each radius. Where `head_known` is false, also keep `n_sites_10km`.
3. Demand pressure (the plan's local mass balance, now with points outside California):
   `E_j = 14.4 x dairy_head_j + 1.32 x beef_head_j` (tons per year)
   `K(d) = exp(-d / 5 km)` for `d <= 25 km`, else 0
   `pressure_i = sum_j E_j K(d_ij) / (yield_tons_per_acre x sum_k corn_acres_k K(d_ik))`
   `prior_silage_i = min(1, pressure_i)`
4. Michigan only: `in_cafo_manure_field` = 1 if the field intersects a land-application polygon whose `PermitNum` joins to a cattle CAFO.
5. For XGBoost, constrain `prior_silage` to be monotone increasing and `d_dairy_km` monotone decreasing so the story stays explainable.

Climate TRACE pager (untested sketch):

```python
import requests
def ct_state(gadm, sub="enteric-fermentation-cattle-operation"):
    out, off = [], 0
    while True:
        r = requests.get("https://api.climatetrace.org/v7/sources",
                         params=dict(gadmId=gadm, subsectors=sub, limit=100, offset=off), timeout=60).json()
        if not r: break
        out += r; off += 100
    return out
```

Sanity checks to run before trusting the table: row counts against section 2; Riverview Dairy at 45.5238, -95.8875 with 11,389 cows; Kansas total between 400 and 500; New York 455.

---

## 6. Failure modes and honest limits

1. **Capacity is not inventory.** Minnesota and Texas numbers are registered or permitted maxima. Inactive Minnesota records still show animals.
2. **Large operations only, outside Minnesota and Iowa.** Wisconsin, New York, Michigan, Pennsylvania and Kansas lists stop at the CAFO threshold. A field far from every mapped dairy can still feed a 120-cow herd next door.
3. **Imputed herd sizes.** Constants in New York, Pennsylvania, Idaho and small Kansas sites. A model that trusts them will see fake 4,360-cow dairies.
4. **Stale and patchy lists.** Kansas rests on a 2015 report. Idaho has 42 mapped dairies against 274 CAFOs in EPA's table. Iowa's database misses about 4,000 facilities according to the Environmental Working Group.
5. **A static prior cannot see the year.** Drought salvage, a dairy that closes, a feedlot that contracts new acres: none appear. `dairy_prior.verification.md` already shows Wisconsin county silage acres moving by a factor of two between years. Keep this a tie-breaker behind the measured harvest signals.
6. **Clustered dairies carry no information.** Where dairies sit a median 1.24 km apart (Central Valley, per `dairy_prior.md`), every field is near one. Expect the same in the Texas Panhandle, the Magic Valley and eastern Wisconsin. Demand over local corn acres still varies; plain distance does not.
7. **Licence and privacy.** New York forbids redistribution. The Minnesota layer has owner names, phone numbers and mailing addresses; drop those columns before anything goes to a public repository or a slide. Climate TRACE needs attribution and its API is a beta.
8. **My own reading limits.** Per-state Climate TRACE counts and the row statistics came through a summarising tool. Exact counts came only from the ArcGIS endpoints.

---

## 7. What this means for Kernel

Build tonight, in this order:
1. Find out which states the labelled evaluation fields are in. That decides which registry matters. If any are in Minnesota, the MPCA layer gives a complete test of the dairy clue, small herds included.
2. Write `cattle_points` (section 5). Minnesota and Michigan take minutes each. Climate TRACE needs one paged loop per state.
3. Compute `prior_silage` with the kernel already in the plan and add `d_dairy_km` and `d_feedlot_km`. Run the depth-2 rule and XGBoost with and without these columns and report precision, recall and false positive rate both ways. If the prior does not move the numbers, say so on stage; that is an honest result.
4. Put one map on a slide: fields coloured by predicted class with dairies and feedlots as circles sized by herd. Minnesota is the cleanest state for it.
5. Feed the nearest facility into the Harvest Story card: "2.1 km from a registered dairy, 11,389 cows (MPCA)". This is a tool call for the Nemotron analyst, not a chatbot answer.
6. If Michigan is in scope, test the manure-field polygons as a prior and measure field-to-dairy distances from them.

What changes in the plan:
- "Distance to the nearest dairy" becomes "local cattle feed demand over local corn acres, dairies and feedlots together". Feedlots enter at about 0.09 cow-equivalents per head.
- The fallback to county herd counts stays, but only as the base layer. Points now rank fields inside a county in Minnesota, Michigan, Iowa, Wisconsin, Texas, Kansas and Nebraska.
- New York and Pennsylvania get count-based features only.

What to say to USDA statisticians:
- "Silage is two-thirds water. NDSU Extension says the economics fall apart with distance and suppliers sit within a few miles; Missouri Extension would not haul it past 20 miles; a peer-reviewed transport study puts the limit at 18 kilometres."
- "We use public regulatory registries: Minnesota's feedlot registry, Michigan's CAFO permits, and Climate TRACE's national compilation. They list capacity, not inventory, and mostly large operations, so we use them as a tie-breaker and we show the result with and without them."
- "In the Plains the cattle are in feedlots, so a dairy-only map would be wrong. Minnesota's registry lists more beef capacity than dairy cows."

---

## 8. Annotated bibliography

Opened and used:
1. MPCA Feedlots layer (ArcGIS REST). https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_pca/env_feedlots/MapServer/0 . Schema, counts, sums, sample records.
2. Climate TRACE API. https://api.climatetrace.org/v7/sources?gadmId=USA.50_1&subsectors=enteric-fermentation-cattle-operation&limit=100 . Seven states sampled.
3. Climate TRACE cattle operations methodology. https://github.com/climatetracecoalition/emissions-methodology/blob/main/Sector-Methodologies/1-Sectors/agriculture/cattle-operations-asset-level/README.md (raw: https://raw.githubusercontent.com/climatetracecoalition/emissions-methodology/main/Sector-Methodologies/1-Sectors/agriculture/cattle-operations-asset-level/README.md). US totals, state table, state sources, imputation rules.
4. Climate TRACE Emissions Inventory, Zenodo record 18379672. https://zenodo.org/records/18379672 . Version, file sizes, licence.
5. Climate TRACE data page. https://www.climatetrace.org/data . API status, wrapper, licence.
6. climate-trace-tools API wrapper. https://github.com/climatetracecoalition/climate-trace-tools/tree/main/climate_trace_tools/api . Endpoint and parameter names.
7. Earth Genome, "Detecting cattle operations". https://www.earthgenome.org/works/101---detecting-cattle-operations . Method, Kansas and Nebraska counts, precision target.
8. Climate TRACE interview with Sagan and Tesser. https://climatetrace.org/news/saint-louis-university-s-vasit-sagan-and-derek-tesser-on-mapping-cattle-emissions . Scope of "concentrated operations".
9. Michigan EGLE CAFO service. https://gisagoegle.state.mi.us/arcgis/rest/services/EGLE/ConcentratedAnimalFeedingOperations/FeatureServer . Schema and statistics.
10. Michigan EGLE CAFO Land Application Fields. https://www.arcgis.com/sharing/rest/content/items/f6c9d599a6fa4204a1ffc038e78ec6a2?f=json and https://services1.arcgis.com/FNjlrOFR0aGJ71Tg/arcgis/rest/services/CAFO_Land_Application_Fields_Public_View/FeatureServer . Metadata, limits, count.
11. New York DEC CAFO layer. https://www.arcgis.com/sharing/rest/content/items/8f81795a3d1745ab9867d0af872e87a1?f=json and https://services6.arcgis.com/DZHaqZm9cxOD4CWM/arcgis/rest/services/Concentrated_Animal_Feeding_Operations__CAFOs_/FeatureServer/33 . Schema, licence, counts.
12. Iowa animal feeding operations layer. https://services3.arcgis.com/C5aIa0c3gUMji8fg/ArcGIS/rest/services/animal_feeding_operations/FeatureServer/0 . Schema and statistics.
13. Investigate Midwest on the Iowa undercount. https://investigatemidwest.org/2026/07/15/researchers-identify-thousands-more-iowa-livestock-facilities-than-state-database-shows/ .
14. EPA NPDES CAFO Permitting Status Report, Endyear 2024. https://www.epa.gov/system/files/documents/2025-09/cafo-status-report-2024.pdf . State counts.
15. Wisconsin DNR CAFO statistics page. https://dnr.wisconsin.gov/topic/CAFO/StatsMap.html .
16. Wisconsin DATCP public records and MyDATCP list page. https://datcp.wi.gov/Pages/About_Us/PublicRecords.aspx ; https://mydatcp.wi.gov/SiteMap/BrowseService/SG_d7c9053b-82c1-e211-b39f-0050568c06ae?Key=Services_Group .
17. Inside Climate News repository. https://github.com/InsideClimateNews/2023-08-tx-ca-cattle-methane .
18. NDSU Extension EC2264. URL in section 4.
19. University of Missouri Extension news, 11 November 2024. URL in section 4.
20. Manzone, Airoldi, Calvo 2020. URL in section 4.
21. LfL "NawaRo-Transport", November 2007. URL in section 4.
22. University of Nebraska extension article on silage in finishing diets. https://www.agproud.com/articles/53989-feeding-elevated-levels-of-corn-silage-in-finishing-diets .
23. CAFOSat preprint. https://arxiv.org/abs/2606.00548 .
24. EPA ICIS-NPDES download summary. https://echo.epa.gov/tools/data-downloads/icis-npdes-download-summary .

Not opened, or opened without the needed content:
- Minnesota Geospatial Commons landing page for `env-feedlots`: redirects to https://gis.data.mn.gov/ . Download formats and "refreshed daily" are from a search snippet.
- MPCA registration threshold document: search snippet only.
- Wisconsin DNR CAFO permit search: dynamic page, results did not load.
- TCEQ permit search, Kansas 2015 feedlot report, Nebraska feeders directory and NDEE portal, Iowa geodata page: named in the Climate TRACE source table, not opened.
- DOAJ record for Manzone et al.: HTTP 403 (the journal page was opened instead).
- Penn State "Trading corn silage guide": the fetch returned unrelated content.
- Virginia 1997 newsletter and Wyoming 1994 budget: search snippets only.
- Kansas State 2025 Cattlemen's Day report on silage inclusion: search snippet only.
- BTAA geoportal pages for the Michigan layers: browser check or HTTP 404 (the ArcGIS item was opened instead).
- NASS Wisconsin dairy herd count PDF (data.nass.usda.gov): host not found.
- Mendeley Idaho dairy dataset: removed by the author.
- Inside Climate News `processed_data` files: not opened.

Search log: 22 web searches (English and German), including state registry names, Climate TRACE, Earth Genome, haul distance, custom rates, biogas transport distance, national CAFO image datasets and feedlot silage use.
