# Gap: US field-level silage / grain labels in California county permit records

Team Kernel, Hack the Harvest. Researched 2026-11-14 (all endpoints queried that day).
Question: which California counties publish field polygons whose pesticide-permit commodity separates corn for forage/fodder (silage) from corn for grain, for 2025 and 2026, and how many corn fields of each kind are there?

## 1. Bottom line

1. The claim "no public US parcel-level silage/grain label exists" is wrong. Three California counties publish permit-site polygons carrying the Department of Pesticide Regulation (DPR) commodity code, which distinguishes corn forage/fodder (code 22005) from corn grain (code 24002): **Kern** (2022 to 2026), **Stanislaus** (2012 to 2026) and **Yolo** (2009 to 2024 only).
2. For 2025 and 2026 the labels are almost entirely one class. 2025: Kern 751 corn-forage sites (48,802 acres) versus 5 corn-grain sites (306 acres); Stanislaus 1,392 distinct corn-forage permit-sites versus 9 listing corn grain (7 of those 9 list both). Usable grain polygons for 2025 and 2026 in these two counties: effectively zero.
3. The only county found with a meaningful number of grain-coded fields is Yolo, and only for 2024: 75 grain sites (5,968 acres), 158 forage/fodder sites (10,887 acres), 60 "human consumption" sites (3,403 acres). Yolo has not published 2025 or 2026.
4. The label is a forward-looking grower declaration on a pesticide permit, not a harvest record. It is sticky (Stanislaus commodity entries on 2026 permits carry start dates from 2000 to 2011), and code 22005 is used as a generic field-corn code in at least one county (Yolo 2023 had zero grain-coded sites although the county reported field corn).
5. Best use tonight: a one-class California silage validation set (about 2,100 declared-silage fields for 2025) plus a direct test of the double-crop trap (in Stanislaus about 96% of corn-forage site rows also list a winter forage), plus Yolo 2024 as a small grain check. Not a balanced training set.

## 2. Direct answer table: 2025 and 2026

Counts are sites (polygons) unless stated. "ac" = acres as declared on the permit.

| County | Public layer | Years | 2025 corn forage/fodder (22005) | 2025 corn grain (24002) | 2026 corn forage/fodder | 2026 corn grain | Data as of |
|---|---|---|---|---|---|---|---|
| Kern | `ag_HistoricalCrops_pub` (one layer per permit year) | 2022 to 2026 | 751 sites, 48,802.02 ac (plus 1 organic site, 1 ac) | 5 sites, 306 ac | 449 sites, 29,972.76 ac (mid-year snapshot) | 0 | 2025 layer refreshed 2026-06-26; 2026 layer refreshed 2026-07-12 |
| Kern | `cy_crops_public_temp` (live, active sites only) | current | n/a | n/a | 313 active sites (plus 1 organic) | 3 sites (all one permit) | refreshed 2026-11-14 |
| Stanislaus | `Crops_Boundaries` layer 0 (polygons, `crop_list`) | 2012 to 2026 | 1,392 distinct (permit, site) | 9 distinct (7 also list corn forage; 2 grain-only, 7 ac and 6 ac) | 1,255 distinct | 8 distinct (7 dual; 1 grain-only, 6 ac) | last edit 2026-04-02 |
| Stanislaus | `Permit_Sites_and_Commodities_Open_Data` table 7 (no geometry) | mostly 2026 | 45 rows (stale remnants) | 0 | 1,899 rows, 75,871.5 planted ac (1,723 rows fully active) | 9 rows, 367 ac | last edit 2026-10-20 |
| Yolo | `Crops_2024` and earlier | 2009 to 2024 | not published | not published | not published | not published | 2024 layer last edit 2025-12-10 |
| Merced | no official layer found; third-party student copy of permit year 2022 | 2022 | n/a | n/a | n/a | n/a | copy dated 2023-04-12 |
| San Joaquin | download page returns HTTP 404 (four URL variants) | formerly 2017 to 2022 | unknown | unknown | unknown | unknown | not opened |
| Tulare | `Tulare_County_Commodity_Map` "Field Crop" polygons, no commodity field | 2021 | n/a | n/a | n/a | n/a | last edit 2021-03-02 |
| Fresno, Kings, Madera, Sacramento, Solano, Glenn | none found | | | | | | searched, not exhaustive |
| Statewide | DPR Pesticide Use Report (section level, one square mile) | to 2024 | not yet | not yet | not yet | not yet | `pur2024.zip` posted 2026-11-09 |

## 3. Kern County (verified in detail)

Base: `https://maps.kerncounty.com/arcgis/rest/services/AgComm` (ArcGIS Server 10.41; max 1,000 records per request; formats JSON and geoJSON; native CRS EPSG:2229).

Services present: `ag_HistoricalCrops_pub`, `PesticideUseReports`, `cy_crops_public_temp`, plus unrelated ones (`ag_service_ITS`, `bound_service`, `County_Trapping_Grid`, `fire_service`, `road_service`, `STR_Service_ITS`, `Trapping_Subgrids`).

Layer ids today (they shift when a year is added, so pin by name, not id):

| Service | id 0 | id 1 | id 2 | id 3 | id 4 |
|---|---|---|---|---|---|
| `ag_HistoricalCrops_pub/MapServer` | kern 2026 | kern 2025 | kern 2024 | kern 2023 | kern 2022 |
| `PesticideUseReports/MapServer` | 2026 PURS | 2025 PURS | 2024 PURS | | |
| `cy_crops_public_temp/MapServer` | cy_crops_public_temp | | | | |

Fields, `ag_HistoricalCrops_pub`: OBJECTID, DT_ACT, P_STATUS, PERMIT, SITEID, S_STATUS, COMM, DT_INACT, PMT_SITE, OP_ACT, OP_INACT, PERMITTEE, MAILING, CITY, STATE, ZIP, AGENT, PMT_YEAR, TOWNSHIP, RANGE, SECTION, ACRES, SYMBOL, FMEUpdate, SHAPE. (PERMITTEE, MAILING, CITY, ZIP, AGENT are personal or business identifiers: drop them.)

Fields, `PesticideUseReports`: APPLIC1 (application date), PLANTED_AM, QUANT_USED, PRODUCT_NA, EPA_REG_NO, APPLMETHOD, TREATED_AM, MERIDIAN/TOWNSHIP/RANGE/SECTION, COMMODITY, SITEID, PMT_SITE, PMT_YEAR, PERMIT, SHAPE. One row per pesticide application, already joined to the field polygon.

Fields, `cy_crops_public_temp`: PERMIT, COMM, COMMODITY, COMM_CODE, SEED_CODE, PMT_SITE, P_STATUS, S_STATUS, DT_ACT, DT_INACT, FMEUpdate, SHAPE. This layer carries the numeric DPR code: 22005 = CORN FOR/FOD, 24002 = CORN, GRAIN, 29119 = CORN, SWEET.

Service metadata says the department built the dataset to locate production agricultural field boundaries more precisely, and that the department "issues annual permits to growers" (document Subject, truncated in the service).

### 3.1 Corn sites by permit year (`ag_HistoricalCrops_pub`, group by COMM where COMM LIKE '%CORN%')

| Permit year | CORN FOR/FOD sites | CORN FOR/FOD acres | CORN, GRAIN sites | CORN, GRAIN acres | CORN, SWEET sites / acres | Other |
|---|---|---|---|---|---|---|
| 2022 | 582 | 37,572.37 | 2 | 150 | 1 / 40 | |
| 2023 | 648 | 44,333.17 | 2 | 146 | 1 / 75 | |
| 2024 | 658 | 44,858.05 | 1 | 64 | 1 / 75 | |
| 2025 | 751 | 48,802.02 | 5 | 306 | 1 / 75 | CORN FOR/FOD-OR: 1 site, 1 ac |
| 2026 (snapshot) | 449 | 29,972.76 | 0 | 0 | 1 / 75 | CORN FOR/FOD-OR: 1 site, 1 ac |

Cross-check: the 2025 figure was obtained twice (f=json and f=pjson) and a third time through a status breakdown that sums to the same totals: P_STATUS 'N' 435 sites / 28,735.28 ac (all 435 have an inactivation date) plus P_STATUS 'A' 316 sites / 20,066.74 ac = 751 sites / 48,802.02 ac. Field size for 2025 corn forage: minimum 3 ac, maximum 240 ac, mean about 65 ac. The 2026 figure likewise: 424 active (27,987.56 ac) plus 25 inactivated (1,985.2 ac) = 449 / 29,972.76 ac.

Whole-layer context: 2025 layer 14,236 sites, 1,013,521.9 ac, permit activation dates 2025-01-01 to 2025-12-17. 2026 layer 9,932 sites, 729,323.1 ac, activation dates 2026-01-01 to 2026-06-11, last refreshed 2026-07-12. So the "kern 2026" layer is a mid-year snapshot and should grow.

Live layer today (`cy_crops_public_temp`, refreshed 2026-11-14, deactivated sites removed): CORN FOR/FOD 313 sites; CORN FOR/FOD-ORGANIC 1; CORN, GRAIN 3; CORN, SWEET 1.

### 3.2 The Kern grain class is not usable

The five 2025 CORN, GRAIN sites:

| Permit | Site | Acres | Status | Note |
|---|---|---|---|---|
| 1505124 | P30E | 20 | inactivated 2025-03-23 | inactivated before the 2025 season: a carry-over, not a 2025 crop |
| 1505591 | 25R810GA | 85 | active | T32S R29E S35 |
| 1505591 | 25HS08RC | 40 | active | T32S R31E S25 |
| 1505591 | 25R819FF | 79 | active | T12N R18W S31 |
| 1505591 | 26R804GA | 82 | active | T32S R29E S35 |

In the 2025 pesticide-use layer the sites of permit 1505591 report under a different commodity: CORN, HUMAN CON on three sites with 196, 256 and 347 application records each, and a single CORN, GRAIN record. Inference: several hundred pesticide application records per 40 to 85 acre field in one year is typical of a research or seed nursery, not commercial grain. The three live 2026 CORN, GRAIN sites are all on that same permit (activated 2026-11-09). Treat Kern as having no commercial grain-corn labels.

### 3.3 Pesticide-use layers (independent second table, same vocabulary)

| Layer | COMMODITY | Application records | Application date range | Layer refreshed |
|---|---|---|---|---|
| 2025 PURS | CORN FOR/FOD | 4,228 | 2025-01-14 to 2025-10-13 | 2026-08-27 |
| 2025 PURS | CORN, HUMAN CON | 799 (3 sites) | | |
| 2025 PURS | CORN, SWEET | 4 (1 site) | | |
| 2025 PURS | CORN, GRAIN | 1 (1 site) | | |
| 2026 PURS | CORN FOR/FOD | 787 | 2026-01-07 to 2026-05-28 | 2026-08-17 |

This confirms the brief's lead: COMMODITY in "2025 PURS" has the values CORN FOR/FOD, CORN, GRAIN, CORN, HUMAN CON and CORN, SWEET. The 2026 use reports stop at late May, so they cannot confirm the 2026 harvest.

### 3.4 Double-crop partners in Kern, 2025 layer

| COMM | Sites | Acres |
|---|---|---|
| WHEAT FOR/FOD | 1,024 | 73,441.4 |
| CORN FOR/FOD | 751 | 48,802.0 |
| WHEAT | 126 | 11,375.8 |
| TRITICALE | 110 | 6,219.4 |
| SORGHUM MILO | 85 | 5,334.2 |
| OAT FOR/FOD | 71 | 3,618.3 |
| SORGHUM FOR/FOD | 56 | 3,689.7 |
| BARLEY | 43 | 2,932.0 |
| SUDANGRASS | 28 | 2,645.7 |
| BARLEY FOR/FOD | 20 | 1,597.7 |
| RYEGRAS FOR/FOD | 7 | 489.4 |

In Kern each crop on a piece of ground is its own polygon, so a winter-forage then corn field appears as two overlapping polygons with different COMM values. Intersect CORN FOR/FOD with the winter forages to get declared double-crop fields. Sorghum forage (56 sites) and sudangrass (28) are look-alike summer forages worth keeping as hard negatives.

### 3.5 Kern caveats

- Permit year is not crop year. 435 of the 751 corn-forage sites in the 2025 layer carry an inactivation date; observed examples include 2025-04-14 and 2025-07-03, which cannot both be post-harvest. Some are carry-overs from 2024.
- P_STATUS and S_STATUS codes are undocumented. Observed: every 'N' row has DT_INACT, no 'A' row does.
- Download page `kernag.com/gis/gis-data.asp`: not opened (connection reset on three attempts). Search-engine summaries of that page say it offers one bundle of all permitted shapes 2021 to 2026, that use reports join to shapes on `Pmt_Site`, that a location may hold a dozen or more simultaneously active polygons, and that the department gives no accuracy guarantee. Low confidence until someone opens it in a browser.
- Kern 2024 crop report (PDF not opened; figure from a search summary): "Silage and Forage" 113,000 harvested acres in 2024 and 111,000 in 2023. The permit layer's FOR/FOD-coded commodities total about 132,000 declared acres for 2025. Same order of magnitude; not a like-for-like check because the report lumps corn with winter forage.

## 4. Stanislaus County

Organisation services root: `https://services.arcgis.com/EeYBJFxLdUojipYa/arcgis/rest/services` (owner account `Gis_Central`, hub `open-data-stancounty-gis.hub.arcgis.com`, hub page "Agricultural Commissioner Open Data").

| Item | URL suffix | Type | Notes |
|---|---|---|---|
| Crops_Boundaries | `/Crops_Boundaries/FeatureServer/0` | polygons | 2012 to 2026; fields site_id, permit_num, permittee, permit_yr, p_eff_date, p_exp_date, status, site_name, loc_narr, is_active, size, size_units, crop_list, CropGrp; last edit 2026-04-02; max 2,000 records; geoJSON supported; CRS EPSG:2227. Layer 1 of the same service was not inspected. |
| Permit Sites and Commodities Open Data | `/Permit_Sites_and_Commodities_Open_Data/FeatureServer/7` | table, no geometry | one row per permit, site and commodity; fields include Permit_Number, Permit_Year, Site_ID, Size, GIS_Acres, M/T/R/S, Cropping_Pattern, Commodity, Comm_Code, Planted_Size, From_Date, To_Date, Site_Active, Commodity_Active; last edit 2026-10-20 |
| Pesticide Use Reports | `/Pesticide_Use_Reports/FeatureServer/2` | table "AllPurs" | not queried |

### 4.1 Counts

Distinct (permit_num, site_id) in `Crops_Boundaries` layer 0 (group-by with returnCountOnly):

| Permit year | crop_list contains CORN FOR/FOD | crop_list contains CORN, GRAIN |
|---|---|---|
| 2025 | 1,392 | 9 |
| 2026 (as of 2026-04-02) | 1,255 | 8 |

The grain-listing sites: 7 sites of one permit (5003851; 34, 47, 22, 70, 62, 40, 43 ac) whose crop_list is "CORN FOR/FOD, WHEAT, CORN, GRAIN", so both uses are declared on the same field; plus two grain-only sites in 2025 (7 ac and 6 ac) and one in 2026 (6 ac).

Rows with status 'Issued' and CORN FOR/FOD (not de-duplicated; the layer keeps several permit versions per site, up to 6 rows for one site):

| Permit year | Rows | Sum of size (ac) | Mean size (ac) | Rows that also list a winter forage or small grain | Share |
|---|---|---|---|---|---|
| 2024 | 1,625 | 68,560.6 | 42.2 | 1,581 | 97.3% |
| 2025 | 1,706 | 69,790.8 | 40.9 | 1,643 | 96.3% |
| 2026 | 1,676 | 68,292.0 | 40.7 | 1,609 | 96.0% |

Inference: 1,392 distinct 2025 sites at about 41 ac each is roughly 57,000 declared acres.

Most common crop_list values on issued corn-forage rows (2025): "CORN FOR/FOD, OAT FOR/FOD" 554 rows (19,032 ac); "CORN FOR/FOD, WHEAT FOR/FOD" 397 (17,459 ac); "CORN FOR/FOD, OAT FOR/FOD, SUDANGRASS" 275 (11,551 ac); "CORN FOR/FOD, WHEAT FOR/FOD, SUDANGRASS" 85; corn forage alone 46 rows (1,831 ac). This is the double-crop trap written down by the growers themselves.

The `CropGrp` field is not a label: it reads "FODDER, FORAGE, OR SILAGE" even for a site whose crop_list is "WHEAT, CORN, GRAIN". Parse crop_list.

Table 7, permit year 2026 (snapshot 2026-10-20):

| Commodity | Comm_Code | Rows | Planted acres |
|---|---|---|---|
| CORN FOR/FOD | 22005 | 1,899 | 75,871.5 |
| CORN, GRAIN | 24002 | 9 | 367.0 |
| CORN, HUMAN CON | 29119 | 7 | 2,067.0 |
| CORN, SWEET | 29119 | 6 | 81.0 |
| CORN, SWEET-ORGANIC | 29119 | 1 | 0.1 |

Of the 1,899 corn-forage rows, 1,723 are Issued with site and commodity both active (69,700.7 planted ac). Distinct (permit, site, code) across the three corn codes: 1,448. Earlier permit years in this table hold only remnants (2025: 45 corn-forage rows), so use it for 2026 only and join to polygons on permit number plus site id.

### 4.2 Evidence that declarations are sticky

`From_Date` on the 2026 corn-forage rows ranges from 2000-01-01 to 2011-09-06, and only about half the rows have one. The commodity entry was created up to 26 years ago and has been carried forward at each renewal. `Cropping_Pattern` is "None Specified" on 1,624 of the 1,723 active rows. The record says what the grower is permitted to treat on that site, not what was planted or how it was harvested this year.

## 5. Yolo County (the only grain-coded fields found, 2024 only)

AGOL owner `yoloagoadmin`: "Yolo County Crops YYYY Open Data" for 2009 to 2024 (17 items). County server: `https://gis.yolocounty.gov/ext/rest/services/Public/Agriculture/MapServer`, layers 1 (Crop Permits 2020), 2 (2021), 3 (2022), 16 (2023), 17 (2024). No 2025 or 2026 layer on either host.

2024 layer: `https://services2.arcgis.com/RETsakmE0SJfZXCd/arcgis/rest/services/Crops_2024/FeatureServer/17` (5,531 sites, all status Issued and MostRecYr = 1; last edit 2025-12-10; CRS EPSG:3310; geoJSON supported). Fields include site_id, permit_num, permittee, permit_yr, status, Version, MostRecAll, MostRecYr, is_active, size, crop_list, calc_acres, mtrs.

| Class from crop_list | 2024 sites | 2024 acres | 2023 sites (MostRecYr = 1) | 2023 acres |
|---|---|---|---|---|
| CORN FOR/FOD or ORG CORN FOR FOD (22005) | 158 | 10,887.2 | 122 | 8,599.4 |
| CORN, GRAIN (24002) | 75 | 5,968.3 | 0 | 0 |
| CORN, HUMAN CON or ORG CORN HMN CO (29119) | 60 | 3,403.4 | 36 | 1,533.7 |
| CORN SEED | 10 | 149.0 | 12 | 209.0 |
| Total | 303 | 20,407.9 | 170 | 10,342.1 |

No 2024 or 2023 Yolo site lists two corn classes at once. Nearly every crop_list also contains "UNCULTIVATED AG".

The 2023 layer shows why de-duplication matters: with corn in crop_list it holds 316 rows with status "Revised" and MostRecYr = 0 (superseded versions) against 170 current rows. Counting without the MostRecYr filter gives 372 corn-forage "sites" and 28,445 ac, a threefold overcount.

Why code 22005 is not proof of silage: Yolo's 2023 layer has zero CORN, GRAIN sites, yet the county's 2024 crop report states that field corn went from 6,393 acres in 2023 to 17,274 acres in 2024 (press release not opened, HTTP 403; figure from a search summary of it; the report PDF exceeded the fetch size limit). Yolo is not a dairy county. Inference: in 2023 Yolo grain corn was registered under CORN FOR/FOD or CORN, HUMAN CON, and the specific grain code only came into use in 2024. The 2024 permit total (20,408 ac across corn codes) is the same order as the reported 17,274 ac.

Practical reading: a CORN, GRAIN declaration is specific and probably trustworthy as grain; a CORN FOR/FOD declaration is trustworthy as silage only where nearly all corn is silage anyway (Kern, Stanislaus, Merced).

## 6. Other counties and the statewide fallback

- **Merced**: no official open layer found. A third-party copy uploaded by CSU Stanislaus students (`https://services6.arcgis.com/rX5atNlsxFq7LIpv/arcgis/rest/services/Merced_Field_Crop_Commodity_Data/FeatureServer/3`, last edit 2023-04-12) has the permit schema with Commodity and CommCode. Permit year 2022: CORN FOR/FOD 1,779 polygons, 90,488.7 planted ac (91,597.3 GIS ac); CORN, HUMAN CON 44 polygons, 2,633.6 ac; CORN, GRAIN none. Provenance unverified; do not present it as county-published.
- **San Joaquin**: the Agricultural Commissioner "GIS crop data download" page returned HTTP 404 at `www.sjgov.org/department/agcomm/gis-crop-data-dwnld-lookup`, `sjgov.org/department/agcomm2/...`, `www.sanjoaquin.gov/department/agcomm/...` and `.../download-data`. The current department site has no GIS or data-download link; the county GIS download page (`sjmap.org/GISDataDownload.htm`) lists no crop layer. Search-engine summaries say the old page offered yearly crop-layer shapefiles from 2017 (2022 "available by February 2023") under a terms-of-use page, with a disclaimer that crop lines may not match parcels. Not opened: status unknown. Route now: public records request, `stocktonag2@sjgov.org`.
- **Tulare**: `Tulare_County_Commodity_Map_WFL1` has a "Field Crop" polygon layer (SiteNumber, Size, GisAcres, CropPattrn, SiteActive) last edited 2021-03-02 and no commodity field. Field outlines only.
- **Fresno, Kings, Madera, Sacramento, Solano, Glenn**: nothing found through web search or ArcGIS Online item search. A 2004 DPR letter (CACL 2004-003) lists 24 counties that had submitted field-border databases (Butte, El Dorado, Fresno, Glenn, Imperial, Kern, Kings, Madera, Marin, Merced, Napa, Sacramento, San Joaquin, San Luis Obispo, Santa Barbara, Santa Clara, Santa Cruz, Solano, Sonoma, Stanislaus, Sutter, Ventura, Yolo, Yuba; 175,979 sites) and lists Tulare as having no data then. So the polygons exist in most corn counties; they are just not published.
- **Statewide DPR Pesticide Use Report**: `https://files.cdpr.ca.gov/pub/outgoing/pur_archives/` has `pur2024.zip` (285 MB, posted 2026-11-09) and `pur2023.zip` (posted 2025-11-21). CalPIP (`calpip.cdpr.ca.gov`) states 2024 has been added and filters by county, COMTRS (township, range, section) and site/crop. No 2025 or 2026. Resolution is the one-square-mile section; the same three corn codes apply.
- **DWR Statewide Crop Mapping** (`data.ca.gov/dataset/statewide-crop-mapping`): final 2023 and provisional 2024 shapefiles and geodatabases. Lead only: field polygons with crop type; whether it separates silage from grain or records double crops was not verified here.

## 7. What the label actually is

- 3 CCR 6428 (restricted-material permit application) requires, among other items, the location of each property by meridian, township, range and section, and each commodity or crop to be treated. The applicant supplies it.
- 3 CCR 6623 requires the operator to obtain a site identification number from the commissioner for each site before using pesticides for production of an agricultural commodity; the number is valid for the same period as the operator identification number, and the record holds the location, description or map of the site.
- Neither rule requires the declared commodity to match what is eventually harvested. A grower who plants "corn for forage" and then combines it for grain (or the reverse) has no reason to amend the permit unless a pesticide label forces it. Same weakness as declared-use labels elsewhere.
- DPR letter ENF 26-05 / IPM 26-01 (2026-03-09) inactivated 17 commodity codes, including 28078 "Grain" with the suggested replacement "Corn, field dent, (grain crop) (24002)", and renamed 79 codes; counties were asked to update names in CalAgPermits over the following year. Search summaries of DPR's code lists (PDFs fetched but not machine-readable here) say 24002 was "CORN, GRAIN" and becomes "CORN, FIELD, DENT (GRAIN CROP)", and 29119 was "CORN, HUMAN CONSUMPTION" and becomes "CORN, SWEET"; 22005 stays "CORN (FORAGE - FODDER)". Kern and Stanislaus still showed the old names on 2026-11-14. Match on the numeric code where available and on several name spellings otherwise.
- "CORN, HUMAN CON" (29119) is ambiguous before the rename: Stanislaus has 7 rows totalling 2,067 planted acres under it, far too large for sweet corn alone. Exclude it from both classes.

## 8. Recipes

### 8.1 Download (not executed here: shell network access was denied, so test before relying on it)

```python
import requests, geopandas as gpd

def arcgis_polygons(layer_url, where, out_fields, oid="OBJECTID", page=1000):
    """Page by object id; works on old ArcGIS Server (Kern 10.41) and on ArcGIS Online."""
    feats, last = [], -1
    while True:
        r = requests.get(layer_url + "/query", timeout=180, params=dict(
            where=f"({where}) AND {oid} > {last}", outFields=f"{oid},{out_fields}",
            orderByFields=oid, returnGeometry="true", outSR=4326,
            resultRecordCount=page, f="geojson"))
        batch = r.json().get("features", [])
        if not batch:
            break
        feats += batch
        last = max(f["properties"][oid] for f in batch)
    return gpd.GeoDataFrame.from_features(feats, crs=4326)

KERN = "https://maps.kerncounty.com/arcgis/rest/services/AgComm/ag_HistoricalCrops_pub/MapServer"
STAN = "https://services.arcgis.com/EeYBJFxLdUojipYa/arcgis/rest/services/Crops_Boundaries/FeatureServer/0"
YOLO = "https://services2.arcgis.com/RETsakmE0SJfZXCd/arcgis/rest/services/Crops_2024/FeatureServer/17"

# no PERMITTEE / MAILING / AGENT fields: keep personal data out of the public repo
kern25 = arcgis_polygons(KERN + "/1", "COMM LIKE '%CORN%' OR COMM LIKE '%FOR/FOD%' OR COMM IN ('TRITICALE','SUDANGRASS')",
                         "PMT_SITE,COMM,ACRES,P_STATUS,S_STATUS,DT_ACT,DT_INACT,PMT_YEAR")
stan25 = arcgis_polygons(STAN, "permit_yr = 2025 AND crop_list LIKE '%CORN%'",
                         "site_id,permit_num,permit_yr,p_eff_date,status,is_active,size,size_units,crop_list",
                         oid="OBJECTID_1", page=2000)
yolo24 = arcgis_polygons(YOLO, "crop_list LIKE '%CORN%'",
                         "site_id,permit_num,permit_yr,status,MostRecYr,size,size_units,crop_list",
                         oid="OBJECTID_1", page=2000)
```

A single-feature Kern request with `outSR=4326&f=geojson` was verified to return a valid Polygon FeatureCollection (first vertex -119.30481, 35.51077). Paging by `resultOffset` was not tested on Kern, which is why the sketch pages by object id.

### 8.2 Label rule

```python
import re
WINTER = r"(WHEAT|OAT|BARLEY|TRITICALE|RYEGRAS|FORAGE HAY)"

def corn_label(crop_list: str, county: str):
    s = crop_list.upper()
    sil = bool(re.search(r"CORN FOR[ /]?FOD", s))                      # code 22005
    gra = "CORN, GRAIN" in s or "CORN, FIELD" in s                      # code 24002, old and new name
    hum = "CORN, HUMAN" in s or "CORN HMN" in s or "CORN, SWEET" in s   # code 29119
    if gra and not sil and not hum:
        return "grain_declared"
    if sil and not gra and not hum and county in {"KERN", "STANISLAUS", "MERCED"}:
        return "silage_declared"
    return "ambiguous"            # dual declarations, 29119, or 22005 outside dairy counties

def double_crop_declared(crop_list: str) -> bool:
    return bool(re.search(WINTER, crop_list.upper()))
```

Notes: commodity names contain commas ("CORN, GRAIN"), so test for the corn patterns before any split on commas. In Kern `COMM` holds one commodity per polygon, so apply the same tests to `COMM` and derive the double-crop flag by spatial overlap with winter-forage polygons.

### 8.3 Cleaning steps, in order

1. De-duplicate. Stanislaus: keep, per (permit_num, site_id), the row with the latest p_eff_date. Yolo 2020 to 2023: keep MostRecYr = '1'. Kern: one row per PMT_SITE and COMM already.
2. Drop carry-overs. Kern: keep sites with DT_INACT null or later than 1 August of the label year.
3. Confirm corn was planted that year: require at least 50% of the polygon's CDL pixels to be corn (class 1) for the same year. The permit lists what may be treated, not what is in the ground.
4. Optional stronger confirmation in Kern: require at least one use report on that PMT_SITE with COMMODITY = 'CORN FOR/FOD' between March and September of the label year (2025 PURS layer).
5. Shrink polygons by 20 to 30 m before sampling pixels; the counties warn that boundaries are approximate and polygons overlap.
6. Split by permit holder, not by field, if any of this is used for training (fields of one dairy are near-duplicates). Use permit number as the group key, then discard it.

### 8.4 What can and cannot be scored

- Silage recall in California: TP / (TP + FN) on declared-silage fields. With n = 751 (Kern 2025) the 95% half-width is about 2 points at 90% recall.
- False-positive rate: only on Yolo 2024 grain-declared fields, FP / (FP + TN) with n = 75. Half-width about 7 points at 10% and about 11 points at 50%; zero false positives in 75 only shows FPR below about 4% (rule of three).
- Double-crop trap: compare the pipeline's rotation fingerprint against `double_crop_declared` on Stanislaus corn-forage sites (about 96% positive, so also report the result on the 46 corn-only rows).
- Precision cannot be estimated from Kern or Stanislaus: there are no negatives.

### 8.5 An administrative timing signal (new data source, Kern only)

The Kern use-report layers give dated pesticide applications per field and commodity (2025 corn forage: 4,228 records from 2025-01-14 to 2025-10-13). For a double-cropped field, the last application reported on CORN FOR/FOD and the first on the following WHEAT FOR/FOD bracket the harvest from public records, independent of satellites. Inference: sparse (not every field is sprayed late) but a credible second witness for a handful of "Harvest Story" cards. `DT_INACT` on the site is a third, weaker date.

## 9. What this means for Kernel

1. Change the stage line. Not "no US labels exist" but: "California counties publish, field by field, what the grower told the Agricultural Commissioner the corn was for. We found about 2,100 fields declared corn-for-forage for 2025 in Kern and Stanislaus. Declared grain is almost absent there, which is what NASS says about California."
2. Say plainly what it is: an administrative declaration of intended use, like an intended-use line on an acreage report, not ground truth. USDA statisticians will respect the distinction and will distrust anyone who blurs it.
3. Use it for three checks tonight, in this order: (a) silage recall on Kern 2025 and Stanislaus 2025, where calendar and dairy-distance signals are weakest; (b) the double-crop trap against Stanislaus crop_list; (c) false-positive rate on Yolo 2024 grain-declared fields with 2024 imagery.
4. Do not fold these into the main training set without care. Two counties of nearly pure silage will teach "California = silage" (a location shortcut), not harvest physics. If used for training, add them with county held out and report the held-out score.
5. Year alignment: 2025 is the complete year for Kern and Stanislaus. 2026 is partial (Kern snapshot July, live layer shows only currently active sites; Stanislaus polygons April, table October). Yolo stops at 2024.
6. Innovation claim that survives scrutiny: "new label source: county pesticide-permit site records, queried live by an agent through public map services", plus the use-report timing signal. A Nemotron tool that, for any California field, looks up the county's declared commodity and reports agreement or disagreement with the satellite call is a real tool integration, not a chatbot.
7. Privacy: every one of these layers carries the permit holder's name; Kern adds mailing address. Never request those fields, never commit them to the public repo, never show a name on a slide.
8. This contradicts nothing in the four-number plan; it gives the plan a California exam it currently lacks, and it will show honestly whether "dry-down days" and "ground left" still work when a winter forage is planted right behind the chopper.

## 10. Annotated bibliography

Opened and read (via WebFetch on 2026-11-14 unless noted):

| # | Source | URL | What it gave |
|---|---|---|---|
| 1 | Kern County AgComm services folder | https://maps.kerncounty.com/arcgis/rest/services/AgComm | service list, server version 10.41 |
| 2 | Kern historical crops service and layers 0 to 4 | https://maps.kerncounty.com/arcgis/rest/services/AgComm/ag_HistoricalCrops_pub/MapServer | fields, purpose text, all corn counts 2022 to 2026, status and date statistics, geoJSON test |
| 3 | Kern pesticide use reports service, layers 0 and 1 | https://maps.kerncounty.com/arcgis/rest/services/AgComm/PesticideUseReports/MapServer | fields, corn commodity record counts, application date ranges |
| 4 | Kern current-year crops | https://maps.kerncounty.com/arcgis/rest/services/AgComm/cy_crops_public_temp/MapServer/0 | live counts with numeric COMM_CODE, refreshed 2026-11-14 |
| 5 | Stanislaus Crops_Boundaries | https://services.arcgis.com/EeYBJFxLdUojipYa/arcgis/rest/services/Crops_Boundaries/FeatureServer/0 | fields, distinct site counts, crop_list combinations, winter-forage share |
| 6 | Stanislaus Permit Sites and Commodities table | https://services.arcgis.com/EeYBJFxLdUojipYa/arcgis/rest/services/Permit_Sites_and_Commodities_Open_Data/FeatureServer/7 | codes per commodity, 2026 rows, From_Date range, activity flags |
| 7 | ArcGIS Online item search (owner Gis_Central; owner yoloagoadmin; keyword searches) | https://www.arcgis.com/sharing/rest/search | discovery of Stanislaus, Yolo, Tulare and Merced items; absence of others |
| 8 | Yolo Crops 2024 layer | https://services2.arcgis.com/RETsakmE0SJfZXCd/arcgis/rest/services/Crops_2024/FeatureServer/17 | fields, 2024 class counts |
| 9 | Yolo county server, Agriculture service | https://gis.yolocounty.gov/ext/rest/services/Public/Agriculture/MapServer | layers 2020 to 2024; 2023 counts and duplicate structure |
| 10 | Student project using Yolo crop permit layers | https://ic.arc.losrios.edu/~veiszep/40fall2023/Adamson/G350_Adamson_Project2.html | layers represent crop permits per year with crop type, permittee, acres |
| 11 | Merced field crop commodity data (third-party copy) | https://services6.arcgis.com/rX5atNlsxFq7LIpv/arcgis/rest/services/Merced_Field_Crop_Commodity_Data/FeatureServer/3 | 2022 Merced corn counts |
| 12 | Tulare County Commodity Map | https://services2.arcgis.com/bYBANhmQGwSSLC0l/arcgis/rest/services/Tulare_County_Commodity_Map_WFL1/FeatureServer/2 | Field Crop polygons without commodity |
| 13 | 3 CCR 6428, agricultural permit applications | https://law.cornell.edu/regulations/california/3-CCR-6428 | commodity or crop is part of the application |
| 14 | 3 CCR 6623, site identification numbers | https://www.law.cornell.edu/regulations/california/3-CCR-6623 | site id per site before use |
| 15 | DPR letter ENF 26-05 / IPM 26-01, 2026-03-09 | https://www.cdpr.ca.gov/?p=17301 | 17 codes inactivated, 79 renamed, 24002 as grain replacement |
| 16 | DPR letter CACL 2004-003 | https://www.cdpr.ca.gov/cac-letter/cacl-letter-2004-003 | history of county field-border databases, 24 counties, 175,979 sites |
| 17 | DPR pesticide use archive directory | https://files.cdpr.ca.gov/pub/outgoing/pur_archives/ | pur2024.zip posted 2026-11-09 |
| 18 | DPR Pesticide Use Reporting page | https://www.cdpr.ca.gov/pesticide-use-in-california/pesticide-use-reporting/ | 2024 summary data, archive and CalPIP links |
| 19 | CalPIP | https://calpip.cdpr.ca.gov/main.cfm | 2024 added; county, COMTRS and site/crop filters |
| 20 | San Joaquin Agricultural Commissioner home and enforcement pages | https://www.sanjoaquin.gov/department/agcomm | no GIS or download link on the current site |
| 21 | San Joaquin county GIS downloads | https://sjmap.org/GISDataDownload.htm | no crop layer listed |
| 22 | California statewide crop mapping (data.ca.gov mirror) | https://data.ca.gov/dataset/statewide-crop-mapping | final 2023 and provisional 2024 resources |

Not opened (stated so that nobody cites them on trust):

| Source | URL | Reason | What a search summary claimed |
|---|---|---|---|
| Kern GIS data download page | http://www.kernag.com/gis/gis-data.asp | connection reset, three attempts | bundle of permitted shapes 2021 to 2026; join on Pmt_Site; overlapping polygons; no accuracy guarantee |
| San Joaquin GIS crop data download | https://www.sjgov.org/department/agcomm/gis-crop-data-dwnld-lookup (and three variants) | HTTP 404 | yearly crop-layer shapefiles from 2017, terms of use |
| Yolo 2024 crop report press release | https://www.yolocounty.gov/Home/Components/News/News/14068/4918 | HTTP 403 | field corn 6,393 ac in 2023, 17,274 ac in 2024 |
| Yolo 2024 crop report PDF | https://public.destinyhosted.com/yolocdocs/2025/BOS/20251021_3850/15800_Crop_Report_2024_FINAL.pdf | exceeds fetch size limit | |
| Kern 2024 crop report PDF | http://www.kernag.com/dept/news/2025/2024_Kern_County_Crop_Report.pdf | not attempted directly after host resets | silage and forage 113,000 harvested ac (2024) |
| DPR commodity code lists | https://www.cdpr.ca.gov/wp-content/uploads/2025/04/comby_nam.pdf ; https://www.cdpr.ca.gov/wp-content/uploads/2026/03/pur_code_name_changes.pdf | PDF fetched as binary, no PDF reader available | names of codes 22005, 24002, 29119 before and after the 2026 rename |
| NASS California county corn estimates | https://data.nass.usda.gov/Statistics_by_State/California/Publications/County_Estimates/2024/202402CORNCNTY.pdf | DNS failure, and 404 on the www host | |
| California Natural Resources Agency crop mapping page | https://data.cnra.ca.gov/dataset/statewide-crop-mapping | HTTP 403 (mirror on data.ca.gov opened) | |
| Internet Archive copies | web.archive.org | blocked for the fetch tool | |

## 11. Method note and limits

- Every count came from an ArcGIS REST statistics query fetched through WebFetch, which passes the JSON through a small model before returning it. Key totals were re-derived by a second query form (noted above). Re-run the queries in the notebook before quoting any number on stage; each takes seconds.
- Shell network access was denied in this session, so nothing was downloaded and the code in section 8 is unexecuted.
- Acreage sums use the permit's declared size and assume acres; a few Yolo sites use other units (the all-site size sum is implausibly large), so filter on size_units.
- "None found" for a county means not found by web search and ArcGIS Online item search in one session. Several counties run their own map servers that such searches do not index.
- About 115 tool calls, above the suggested range, because most were single-number count queries.
