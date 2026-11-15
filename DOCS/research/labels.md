# Public labels and statistical proxies: where silage-versus-grain truth actually exists

Research note for team Kernel, Hack the Harvest. Written Saturday 2026-11-14.
Scope: (1) parcel-level labels, (2) US aggregate proxies for the 2025 and 2026 seasons, (3) how to use them.

## 0. Bottom line

1. **There is no public US parcel-level silage/grain label.** CDL, Crop Sequence Boundaries, California DWR / Land IQ, Washington WSDA and Canada's AAFC inventory all stop at "corn". I checked each one (section 1.4).
2. **The closest substitute is across the border and it is current-season.** Quebec's BDPPAD (La Financière agricole du Québec) publishes declared crop per parcel, with separate codes for grain maize and forage (silage) maize, for 2003 to 2026. The 2026 file was refreshed on Monday 2026-11-09. I read it directly: 42,726 grain-maize parcels and 11,102 forage-maize parcels in 2026. Licence CC-BY 4.0.
3. **Europe has millions more.** Netherlands, Austria, France, Flanders, Wallonia, Denmark, NRW, Brandenburg, Lower Saxony, Slovenia, Slovakia and Bulgaria all carry separate silage and grain maize codes. EuroCrops v2.0 (JRC, June 2026) puts 152 country-year GeoParquet files (2008 to 2023) behind one URL pattern and keeps the native crop code.
4. **Three US county-level proxies exist for the current season or last season**, and one of them is a genuinely new data source for this challenge:
   - USDA RMA Summary of Business, crop year **2026**, by county and insurance **type** ("Grain" 016, "Silage" 026). File last modified 2026-11-09. I read it: 1,242,857 insured silage acres in 481 counties.
   - NASS county estimates for corn silage, crop year **2025**, but only 6 states and 180 counties.
   - FSA Crop Acreage Data, crop year 2026 as of 2026-10-09, with an intended-use column (I could not open the FSA site; evidence is second-hand, see 2.4).
5. **Timing truth exists weekly, by district, for Wisconsin 2026**: "Corn harvested for silage" by Agricultural Statistics District. Use 2026, not 2025: the 2025 reports for weeks ending Oct 5 to Nov 9 were cancelled.

## 0.1 How this was researched, and its limits

- 19 web searches ran (the brief asked for at least 12). A 20th was refused because the shared search budget for this workflow turn was exhausted. Everything after that came from opening known primary URLs directly.
- Several claims were verified by reading the public data file itself rather than a page about it: the RMA zip, both BDPPAD zips, the Dutch WFS, the WSDA pivot table, the EuroCrops v2 mapping table and file index, the AAFC legend CSV. Those are marked **[read from file]**.
- Not reachable from my environment today: `www.fsa.usda.gov` (timeouts), `esmis.nal.usda.gov` and at times `www.rma.usda.gov` / `pubfs-rma.fpac.usda.gov` (DNS failures late in the session). NASS has restructured its website: old `/Publications/...` and `/Statistics_by_State/...` file paths now return 404 and live under `/sites/default/files/...`.
- Not done: no Quick Stats API pull (needs a key), so the NASS item names in section 2 are from memory and flagged. No literature search for US research datasets with silage labels (budget ran out), so "none found" is weak evidence.
- Statements prefixed **Inference:** are mine, not the source's.

---

## 1. Parcel-level labels

### 1.1 Summary table

| Source | Silage code(s) | Grain code(s) | Years | Latest file I confirmed | Licence | Intent or actual use |
|---|---|---|---|---|---|---|
| **Quebec BDPPAD** (FADQ) | group `MAF`; codes `MFO` Maïs fourrager, `MFE` Maïs fourrager option superficie | group and code `MGR` Maïs-grain | 2003-2026 | `BDPPAD_V03_2026.zip`, 170 MB, modified 2026-11-09 | CC-BY 4.0 (Quebec) | Declaration; harvest mode can be changed until mid-September |
| **Netherlands BRP** (RVO / PDOK) | 259 Maïs, snij-; 1935 Maiskolvensilage | 316 Maïs, korrel-; 317 Maïs, corncob mix | 2009-2023 in EuroCrops v2; 2025 definitive on PDOK | `brpgewaspercelen_definitief_2025.gpkg`, 2.93 GB, modified 2026-05-15 | not stated on the pages I opened (a mirror says CC0) | Declaration, reference date 15 May |
| **Austria INVEKOS Schläge** (AMA) | 109 SILOMAIS; 135 GRÜNMAIS | 105 KÖRNERMAIS; 106 MAIS CORN-COB-MIX | 2015-2023 in EuroCrops v2; 2025-2 and 2026-1 files confirmed at source | `inspire_schlaege_2026-1_polygon.gpkg.zip`, 1.26 GB, modified 2026-05-19 | CC-BY-AT 4.0 | Declaration; "-1" summer stock, "-2" winter revision |
| **France RPG** (IGN / ASP) | MIE Maïs ensilage | MIS Maïs | 2007-2025 editions in the feed | metropolitan 2025 edition not confirmed; overseas 2025 confirmed | not opened | Declaration (CAP) |
| **Flanders** (be2) | 201 Silomaïs | 202 Korrelmaïs | 2008-2023 in EuroCrops v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Wallonia** (be3) | 201 Maïs ensilage | 202 Maïs grain | 2015-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Denmark** | 216 Silomajs; 218 Silomajs med græsudlæg | 5 Majs til modenhed; 19 same with grass undersown | 2010-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Germany NRW** (dea) | 411 Silomais | 171 Mais (ohne Silomais) | 2019-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Germany Brandenburg** (de4) | 411 Silomais (als Hauptfutter); 10172 Mais (Biogas) | 10171 Körnermais; 11171 Körnermais und CCM | 2010-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Germany Lower Saxony** | 411 Silomais (als Hauptfutter); 172 Mais (Biogas) | 171 Körnermais einschl. CCM/Mais | 2021 in EuroCrops v1 | EuroCrops v1 | CC BY-SA 4.0 (v1) | Declaration |
| **Slovenia** | 6 koruza za silažo | 5 koruza za zrnje | 2019-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Slovakia** | 10082 Kukurica na siláž; 10084 Kukurica na zeleno | (10080 Kukurica, generic) | 2018-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Bulgaria** | 10260 царевица за силаж | 10259 царевица за зърно | 2014-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| **Czechia** | none found | 434 Kukuřice na zrno; 433 Kukuřice (jinde neuvedená) | 2021-2023 in v2 | via EuroCrops v2 | CC BY 4.0 (via v2) | Declaration |
| Estonia, Spain, Portugal, Ireland, Finland, Tuscany | **no split** (single maize code) | | | | | |
| Switzerland | not verified (nothing opened) | | | | | |

Codes of 10,000 and above in EuroCrops v2 are synthetic: the readme says they are generated when the original dataset has no crop code.

### 1.2 Quebec BDPPAD: the nearest thing to US labels

**What it is.** "Base de données des parcelles et productions agricoles déclarées", polygons of parcels attached to FADQ crop-insurance client files since 2003, with the declared crop per insurance year.

**Access.**
- Landing page: http://www.fadq.qc.ca/documents/donnees/base-de-donnees-des-parcelles-et-productions-agricoles-declarees/ (24 annual ZIPs, 2003 to 2026).
- File pattern: `https://www.fadq.qc.ca/fileadmin/geo4tb/BDPPAD/BDPPAD_V03_<YEAR>.zip`. Three years use a lower-case `v`: `BDPPAD_v03_2022.zip`, `BDPPAD_v03_2013.zip`, `BDPPAD_v03_2012.zip`.
- Format: Shapefile, geographic coordinates, NAD83. One row per parcel.
- Licence: Creative Commons 4.0 Attribution, Quebec version (per the open.canada.ca record, modified 2026-05-27).
- Refresh: the landing page says the current and previous seasons are updated weekly on Mondays. Both the 2025 and 2026 zips carry `Last-Modified: Mon, 09 Nov 2026` and the inner files are named `BDPPAD_v03_AN_<year>_s_20261109.*`.
- User guide (March 2025, 10 pages): https://www.fadq.qc.ca/fileadmin/geo4tb/BDPPAD/bdppad-v03-guide-utilisateur.pdf

**Attributes that matter** (from the guide, Tableau 1, and the DBF header I read):
`AN` (insurance year), `IDANPAR` (parcel-year id), `IDPAR` (geometry id, stable across years), `SUPHEC` (hectares), `GROPRO` / `DESGROPRO` (crop group), `NBPRO` (number of crops in the parcel), `CODPRO1..15`, `DESCODPR1..15`, `PRCSUPPR1..15` (code, description and percent of area for each crop), `VARCUL` (cultivar, and corn heat units after "UTM:").

**Counts [read from file].**

| | 2025 file | 2026 file |
|---|---|---|
| All parcels | 375,103 | 370,322 |
| Group `MGR` Maïs-grain | 39,822 parcels, 284,777 ha | 42,726 parcels, 305,784 ha |
| Group `MAF` Maïs fourrager | 11,144 parcels, 64,614 ha | 11,102 parcels, 65,561 ha |
| Silage share of maize parcels | 21.9% | 20.6% |
| Silage share of maize area | 18.5% | 17.7% |
| Median parcel, grain / silage | 4.6 ha / 4.5 ha | 4.6 ha / 4.5 ha |
| 10th to 90th percentile, grain | 1.2 to 15.8 ha | 1.2 to 15.9 ha |
| 10th to 90th percentile, silage | 1.4 to 11.4 ha | 1.4 to 11.9 ha |
| Share of parcels at 2 ha or more, grain / silage | 80% / 84% | 80% / 83% |

2026 detail by first crop code: `MGR` 42,726 single-crop parcels; `MFO` 7,916 (47,065 ha); `MFE` 3,186 (18,496 ha). Parcels in the `MUL` (multiple crops) group whose largest crop is maize: `MGR` 769, `MFO` 292, `MFE` 135. Sweet corn is separate (`MSF`, `MSG`, `MSE`, `MSP`). Parcels with no crop group: 122,308.

**Intent or actual use.** The guide is explicit that it is a declaration: the crop "doit être considérée comme une déclaration et non comme une vérité terrain". But the timing is better than Europe's: declarations are complete by 1 August, corrections run into September, and "Pour le maïs, l'avoine, le blé et le soya, il est possible d'avoir un changement de mode de récolte (récolté en grain ou en fourrage) jusqu'à la mi-septembre."
**Inference:** a label that can still be switched in mid-September, when silage chopping is under way, is much closer to actual use than a 15 May declaration.

**Known biases, from the guide.**
- Not exhaustive: it covers only land of producers who have been FADQ clients.
- "Depuis 2010, les données des clients assurés seulement pour le foin ou le maïs fourrager sur base de besoin alimentaire ne sont plus compilées". **Inference:** forage maize on pure dairy farms is under-represented, so silage counts are a floor.
- Parcels with crop failure, reseeding or ambiguous multi-crop shares have the crop removed.
- Up to 15 crops can share one polygon without a location inside it. Use `NBPRO = 1`.
- Crop codes are insurance codes and are not guaranteed stable over time.
- `VARCUL` corn heat units are almost empty in the public file: 151 of 42,726 grain parcels in 2026. Do not plan a feature around it.

**Why it transfers better than Europe.** **Inference:** same continent, North American hybrids, corn-soybean rotation in the St. Lawrence lowlands, a large dairy sector, latitude about 45 to 47 N next to New York and Vermont and comparable to Wisconsin, Michigan and Minnesota. Class balance (about 18% silage by area) is far kinder than the US 6%.

### 1.3 Europe

**Netherlands BRP Gewaspercelen.**
- GeoPackage: `https://service.pdok.nl/rvo/gewaspercelen/atom/downloads/brpgewaspercelen_definitief_2025.gpkg` (2,932,801,536 bytes).
- OGC API Features: https://api.pdok.nl/rvo/gewaspercelen/ogc/v1/collections/brpgewas. WFS: `https://service.pdok.nl/rvo/gewaspercelen/wfs/v1_0`, type `brpgewaspercelen:BrpGewas`.
- Attributes: `category`, `gewas`, `gewascode`, `jaar`, `status`. Sample feature: `jaar` 2025, `status` "Definitief".
- The collection description says: "Van elk jaar wordt een dataset gegenereerd van peildatum 15 mei."
- Parcel counts for 2025, by WFS `resultType=hits` **[read from service]**:

| gewascode | name | parcels 2025 |
|---|---|---|
| 259 | Maïs, snij- (silage) | 95,192 |
| 316 | Maïs, korrel- (grain) | 3,992 |
| 317 | Maïs, corncob mix | 1,525 |
| 1935 | Maiskolvensilage (ear silage) | 812 |
| 814 | Maïs, suiker- (sweet) | 395 |
| 2032 | Maïs, energie- | 24 |
| all | every feature, landscape elements included | 2,331,084 |

- Silage is 94.5% of the 259 + 316 + 317 parcels. **Inference:** the Netherlands is a mirror of California (silage-dominant), useful for testing whether the grain minority is detectable.
- I did not find a 2026 file. A guessed `..._concept_2026.gpkg` URL returned 404, which proves nothing either way.

**Austria INVEKOS Schläge.**
- Metadata record: https://geometadatensuche.inspire.gv.at/metadatensuche/agrarportal/api/records/3650c224-3a03-4796-907b-a37784a656e2 (now titled "INVEKOS Schläge 2026-1", revision date 2026-05-22).
- Downloads: `https://inspire.lfrz.gv.at/009501/ds/inspire_schlaege_2026-1_polygon.gpkg.zip` (1,255,084,858 bytes, modified 2026-05-19) and `..._2025-2_polygon.gpkg.zip` (1,259,234,212 bytes, modified 2026-01-14). EPSG:31287.
- OGC API Features: https://gis.lfrz.gv.at/api/geodata/i009501/ogc/features/v1/
- A Schlag is a contiguous part of a field parcel cultivated for one growing season with one crop. Published twice a year: summer stock "JJJJ-1", winter revision "JJJJ-2".
- Codes: 105 KÖRNERMAIS, 106 MAIS CORN-COB-MIX (CCM), 109 SILOMAIS, 135 GRÜNMAIS, 107 ZUCKERMAIS, 173 SAATMAISVERMEHRUNG.
- **Double-crop codes exist**: 174 WINTERGERSTE / SILOMAIS, 175 WINTERGERSTE / KÖRNERMAIS, 764 GRÜNSCHNITTROGGEN / MAIS, 184 KLEEGRAS / SILOMAIS. **Inference:** this is the only labeled analogue I found for California's winter-forage-then-corn system.
- The attribute name `snar_bezeichnung` comes from a secondary site, not from the GeoPackage. Check it on load.

**France RPG.**
- Download feed: https://data.geopf.fr/telechargement/resource/RPG (349 entries, editions 2007-01-01 to 2025-01-01, formats SHP, GPKG, SQL). Resource names look like `RPG_4-0__GPKG_RGAF09UTM20_R01_2025-01-01`.
- I saw 2025-edition entries for the overseas regions only. The metropolitan (`FXX`) 2025 entry was not on the two feed pages I opened, so treat it as unconfirmed.
- Codes: `MIS` Maïs, `MIE` Maïs ensilage, `MID` Maïs doux.
- Easiest route is EuroCrops v2: `fr_2015.parquet` to `fr_2023.parquet`.

**EuroCrops v1 and HCAT3.**
- GitHub: https://github.com/maja601/EuroCrops. Zenodo: https://zenodo.org/records/8229128. Licence CC BY-SA 4.0. One year per country, mostly 2021 (Denmark 2019, France 2018).
- HCAT3 codes **[read from `hcat_core/HCAT3.csv`]**: `3301010600 grain_maize_corn_popcorn` (parent `3301010000 cereal`) and `3301090400 green_silo_maize` (parent `3301090000 plants_harvested_green`).
- Per-country mapping files live in `csvs/country_mappings/` (for example `at_2021.csv`, `nl_2020.csv`, `fr_2018.csv`, `dk_2019.csv`, `be_vlg_2021.csv`, `de_nrw_2021.csv`, `de_ls_2021.csv`, `de_bb_2023.csv`, `de_BW_2022.csv`, `si_2021.csv`, `cz_2023.csv`).
- **Trap:** HCAT3 puts biogas maize (Lower Saxony 172 "Mais (Biogas)"), Dutch energy maize (2032), sweet corn and corn-cob-mix all under `grain_maize_corn_popcorn`. **Inference:** biogas maize is chopped whole like silage, so the harmonised class mislabels it.

**EuroCrops v2.0 (JRC).**
- Paper: Claverie, Chan et al., Earth System Science Data 18, 4075-4095, published 16 June 2026. https://essd.copernicus.org/articles/18/4075/2026/essd-18-4075-2026.html. "nearly 47 million parcels covering 21 Mha", 2008 to 2023 where available.
- Data: `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/EuroCropsV2/gpqt/<nuts>_<year>.parquet`. Columns `cropfield`, `original_code`, `area_ha`, `geom` (EPSG:3035). Stack files `<nuts>_stack.parquet` link parcels across years (`cf<YEAR>`, `c<YEAR>`).
- Licence CC BY 4.0 (from `copyright.txt` on the FTP).
- Mapping table: https://github.com/Martincccc/EuroCropsV2/blob/main/data/cropcodemapping/eurocrops.csv with columns `nuts, original_code, original_name, translated_name, hcat4_code, hcat4_name, usage_code, usage_name`.
- Coverage **[read from `all_gpqt_files.csv`, 152 files]**:

| Region | Years | Region | Years |
|---|---|---|---|
| at Austria | 2015-2023 | fi Finland | 2020-2023 |
| be2 Flanders | 2008-2023 | fr France | 2015-2023 |
| be3 Wallonia | 2015-2023 | ie Ireland | 2017-2023 |
| bg Bulgaria | 2014-2023 | iti1 Tuscany | 2016-2023 |
| cz Czechia | 2021-2023 | nl Netherlands | 2009-2023 |
| de4 Brandenburg | 2010-2023 | pt Portugal | 2017-2022 |
| dea NRW | 2019-2023 | si Slovenia | 2019-2023 |
| dk Denmark | 2010-2023 | sk Slovakia | 2018-2023 |
| ee Estonia | 2015-2023 | es Spain | 2021-2023 |

- **Trap, verified in the mapping table:** HCAT4 has a single maize class (`3310106000 maize_corn_popcorn`) and moves grain-versus-silage to `usage_code`. The usage code is inconsistent for silage maize:

| Region and code | Name | usage_code |
|---|---|---|
| at 109 | SILOMAIS | 3 Fodder/Forage |
| dk 216 | Silomajs | 3 Fodder/Forage |
| be2 201 | Silomaïs | 3 Fodder/Forage |
| fr MIE | Maïs ensilage | 5 Harvested Green |
| sk 10082 | Kukurica na siláž | 5 Harvested Green |
| nl 259 | Maïs, snij- | **0 No specified use** |
| be3 201 | Maïs ensilage | **0 No specified use** |
| dea 411 | Silomais | **0 No specified use** |
| si 6 | koruza za silažo | **0 No specified use** |
| bg 10260 | царевица за силаж | **0 No specified use** |
| de4 10172, nl 2032 | biogas / energy maize | 4 Energy |

  The paper itself concedes "the distinction between grain and silage maize is not captured as well". **Use `original_code` per region, never `usage_code` or the HCAT class.**

**EuroCropsML.** arXiv:2407.17458 (Scientific Data 12, 664, 2025). 706,683 labeled data points, 176 classes, year 2021, Sentinel-2 L1C per-parcel medians. **Inference:** it is of little use here. From memory (not on the abstract page) its countries are Estonia, Latvia and Portugal, and the v2 mapping shows Estonia and Portugal each have a single maize code.

### 1.4 United States and Canada: checked, no silage attribute

| Dataset | What I verified | Verdict |
|---|---|---|
| **California DWR / Land IQ Statewide Crop Mapping** | Water years 2014, 2016, 2018-2023 final, 2024 provisional (`i15_crop_mapping_2024_provisional_20251208.gdb.zip`). "No restrictions on public use". Legend (Dec 2022): F6 "Corn (field & sweet)"; F16 "[Corn (field and sweet), hybrid sorghum/Sudan grass, grouped for remote sensing]". 2023 metadata: "This dataset includes multicropped fields"; `MAIN_CROP` since 2019; `MAIN_CROP_DATE` "indicates the NDVI peak date for this main season crop"; `MULTIUSE` holds 'Mixed' and 'Double'; all single-cropped fields sit in Class 2. Accuracy 98.4% at class level, 97.4% at subclass level (2023 final). | No silage/grain split, and corn may be lumped with sorghum and sudan. Useful for field polygons, double-crop flags and peak date. |
| DWR legend extras | Special condition **C "GREEN CHOPPED: Grain or field crops harvested early for livestock feed"** and H "HARVESTED CROP". Double crop notation: "(G)F6 indicates irrigated grain followed by field corn". Semi-agricultural class S3 "Dairies", S2 "Livestock feed lot operations". | The legend can express green chop and dairies. I did not confirm that the statewide Land IQ layer populates special conditions or S3 polygons. Worth a 10-minute look. |
| **Washington WSDA Agricultural Land Use 2025** | `2025WSDACropDistribution-gdb.zip`, 90 MB, modified 2026-08-24. Crop types containing corn **[read from the 2025 pivot table]**: "Corn, Field", "Corn, Sweet", "Corn Seed", "Corn, Unknown". Fields include `CropType`, `CropGroup`, `Irrigation`, `RotationCr`, `CoverCrop`, `DoubleCrop`, `InitialSur`, `LastSurvey`. | **No silage corn code.** The "Hay/Silage" group does not contain corn. Irrigated basins are resurveyed every 3-4 years, so a given year is a snapshot. |
| **USDA Crop Sequence Boundaries** | Latest 2018-2025, released 2026-03-27. `NationalCSB_2018-2025_rev23.zip`. The page says CSBs "do not come from producers or agencies like the Farm Service Agency". | Geometry plus CDL history only. Attribute list not opened. |
| **AAFC Annual Crop Inventory** | Latest year 2025, 30 m, Open Government Licence Canada, target accuracy "at least 85%". Legend **[read from CSV]**: code 147 "Corn for grain / Maïs-grain"; no silage class; code 122 "Pasture/forages". | No split. Silage corn is inside class 147. |
| US research datasets with silage labels | None found. | Weak evidence: the search budget ended before a literature pass. |

### 1.5 Street-level imagery precedent

d'Andrimont, Yordanov, Martinez-Sanchez, van der Velde, "Monitoring crop phenology with street-level imagery using computer vision", arXiv:2112.09190 (2021).
- About 400,000 geo-tagged photos, one per second along a 200 km route in Flevoland, Netherlands, monthly from March to October 2018, with side-looking action cameras.
- Detailed phenology observations at 220 parcels, 17 crop types, MobileNet with transfer learning, 160 configurations tried.
- Parcel-level macro F1 of 88.1% for crop type and 86.9% for main phenological stage on an independent set.

**Inference:** this shows the idea works with purpose-collected imagery. It does not show that crowdsourced Mapillary coverage in US corn counties during the four-week silage window is dense enough. Not an 18-hour item. A fair "how it could be developed further" slide: a windshield camera on a milk truck route.

---

## 2. US aggregate proxies

### 2.1 USDA RMA Summary of Business by type: the new data source

**Access.** https://www.rma.usda.gov/tools-reports/summary-of-business/state-county-crop-summary-business
- Type/Practice/Unit Structure files: `https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/state_county_crop/sobtpu_<YEAR>.zip` for 2025, 2026 and 2027.
- `sobtpu_2026.zip`: 8,959,529 bytes, `Last-Modified: Mon, 09 Nov 2026`. `sobtpu_2025.zip`: 8,698,425 bytes, same date.
- Record layout: `.../SOBTPU_External_All_Years.pdf`.
- Coverage-level files without type: `sobcov_<YEAR>.zip`, 1989 to 2027.

**Format, with two gotchas I hit.** Pipe-delimited, no header, **records end with a bare carriage return** (`\r`), 572,912 records in the 2026 file. Fields in order:

1 Commodity Year, 2 State Code, 3 State Name, 4 State Abbreviation, 5 County Code, 6 County Name, 7 Commodity Code, 8 Commodity Name, 9 Insurance Plan Code, 10 Insurance Plan Abbreviation, 11 Coverage Type Code, 12 Coverage Level Percent, 13 Delivery ID, **14 Type Code, 15 Type Name**, 16 Practice Code, 17 Practice Name, 18 Unit Structure Code, 19 Unit Structure Name, **20 Net Reporting Level Amount**, 21 Reporting Level Type, 22 Liability Amount, 23 Total Premium Amount, 24 Subsidy Amount, 25 Indemnity Amount, 26 Loss Ratio, 27 Endorsed Commodity Reporting Level Amount.

Field 27 holds acres under endorsements (SCO, STAX, Margin Protection). Sum field 20 only, or acres are double counted.

**Corn (commodity 0041) by type, crop year 2026 [read from file].**

| Type code | Type name | Rows | Net insured acres | Liability | Indemnity so far |
|---|---|---|---|---|---|
| 016 | **Grain** | 56,402 | 87,015,856 | $63.56 billion | $793.9 million |
| 026 | **Silage** | 3,203 | 1,242,857 | $690.9 million | $46.9 million |
| 341 | White | 1,175 | 230,409 | | |
| 381 | Waxy | 248 | 73,808 | | |
| 383 | Blue | 99 | 9,256 | | |
| 739 | High Amylose | 34 | 6,374 | | |
| 009 | Seed | 27 | 5,318 | | |

**Year on year.**

| | 2025 | 2026 | Change |
|---|---|---|---|
| Grain type, net insured acres | 88,968,075 | 87,015,856 | -2.2% |
| Silage type, net insured acres | 1,200,580 | 1,242,857 | +3.5% |
| Counties with silage acres above zero | 476 | 481 | |
| Counties with grain acres above zero | 2,052 | 2,061 | |

**Silage type by state, 2026 (2025 in brackets), top 20 of 34 states.**

| State | Silage acres 2026 (2025) | Grain acres 2026 | Counties with silage | Silage share of the two types |
|---|---|---|---|---|
| NY | 225,236 (211,990) | 456,845 | 39 | 33.0% |
| WI | 171,539 (193,376) | 3,033,793 | 59 | 5.4% |
| ID | 127,575 (107,425) | 54,791 | 20 | 70.0% |
| ND | 116,300 (112,256) | 4,691,665 | 52 | 2.4% |
| CA | 83,464 (94,883) | 34,655 | 10 | 70.7% |
| MT | 70,913 (45,689) | 30,861 | 21 | 69.7% |
| TX | 68,967 (85,917) | 2,224,526 | 23 | 3.0% |
| AZ | 64,017 (45,364) | 17,756 | 3 | 78.3% |
| VT | 45,615 (44,688) | 4,663 | 3 | 90.7% |
| SD | 31,993 (32,614) | 6,414,700 | 33 | 0.5% |
| CO | 28,221 (19,586) | 1,585,304 | 11 | 1.7% |
| GA | 22,445 (19,169) | 475,323 | 20 | 4.5% |
| OR | 22,049 (23,138) | 33,514 | 4 | 39.7% |
| MN | 18,831 (22,233) | 8,431,484 | 45 | 0.2% |
| MI | 15,740 (16,007) | 1,779,034 | 15 | 0.9% |
| NM | 15,252 (15,225) | 34,003 | 6 | 31.0% |
| WA | 13,698 (12,658) | 69,090 | 5 | 16.5% |
| IN | 13,038 (12,347) | 4,516,569 | 5 | 0.3% |
| OH | 11,507 (10,649) | 2,877,450 | 17 | 0.4% |
| IA | 11,246 (12,594) | 12,538,728 | 11 | 0.1% |

Also present with smaller totals: PA, FL, NV, UT, CT, WY, NC, MA, OK, VA, NJ, MD, WV, AL. **Absent altogether:** Illinois, Nebraska, Kansas, Missouri, Kentucky and others have no silage-type acres.

**How to read it.**
- Insured silage acres are about 19% of NASS silage acres nationally for 2025 (1.20 million against the 6.2 million in the brief), and about 26% in California (94,883 against roughly 365,000).
- **Inference:** the silage type is offered only where the county actuarial documents list it, and elsewhere silage corn is insured under the grain type. So the silage column is a **floor** and the grain column is contaminated with silage. Nebraska and Kansas showing zero is the clearest sign.
- **Inference:** the type is chosen by the acreage reporting date in mid-summer. It is intent a few weeks before chopping, later than any European declaration but still not harvest.
- **Inference:** year-on-year changes mix real acreage change with participation change.

**Cause of loss files.** Not opened: `www.rma.usda.gov/tools-reports/summary-of-business/cause-loss` failed with a DNS error on two attempts. I have no verified statement about whether cause-of-loss records carry the type.

### 2.2 NASS county estimates

Source: "Row Crops County Estimates Methodology and Quality Measures", released June 5, 2026. https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/County_Estimates_Row_Crops/06_2026/rcceqm26.pdf

- "Currently, the row crops county estimates program contains 31 states for corn for grain, **6 states for corn for silage**". The six are not named.
- Counties published, "Other Counties" entries included:

| Crop | 2024 | 2025 |
|---|---|---|
| Corn for grain | 1,296 | 1,238 |
| Corn for silage | 204 | 180 |

- Coefficient of variation of published county estimates, 2025, 25th / 50th / 75th percentile: corn silage harvested acres 1.2% / 2.0% / 4.3%; corn silage yield 3.7% / 5.5% / 8.6%; corn grain harvested acres 1.4% / 3.4% / 9.9%. Silage planted is (NA).
- Method: since crop year 2020, Bayesian small-area models. "The planted and harvested acreage models input current year survey expansions, survey standard errors, and administrative data from FSA and RMA." Estimates are benchmarked to the state totals.
- Suppression rule: counties that miss the publication standard are "combined with other counties and published as 'Other Counties' totals". I could not compute a suppression rate without Quick Stats access.
- Timeline: state and national estimates in the Annual Crop Production report "in early January"; county estimates "for most row crops being released by the end of May".
- Survey health: December Agricultural Survey response rate 46.0% (2024) and 40.2% (2025), US, sample about 73,100. Row Crops CAPS, run in 36 states, 39.7% and 39.1%, sample about 57,300. California CAPS sample: 267 in 2025.

**Latest county year is therefore 2025**, published around May-June 2026, for 6 states. For every other state the only county silage figure is the 2022 Census of Agriculture.

The Wisconsin state page still lists county estimate PDFs only up to crop years 2022-2023 ("Corn for Silage", February 23, 2024). **Inference:** newer years are in Quick Stats only.

### 2.3 Weekly progress

**Verified for Wisconsin.** The state "Crop Progress & Condition" report carries a row "Corn harvested for silage" by 9 districts plus the state. List page: https://www.nass.usda.gov/statistics-by-state/wisconsin/publications/crop-progress-and-condition (latest linked report November 9, 2026). File pattern through October: `https://www.nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2026/WI-Crop-Progress-MM-DD-26.pdf`.

Wisconsin 2026, state level, percent:

| Week ending | Dented | Mature | Harvested for silage | Harvested for grain | Source |
|---|---|---|---|---|---|
| Aug 30 | | | 5 | | news report, not opened in NASS PDF |
| Sep 6 | | | 14 | | search summary of the Sep 8 report; PDF not opened |
| Sep 13 | 73 | 26 | 32 | | "last week" column, Sep 21 report |
| Sep 20 | 85 | 38 | 54 | | Sep 21 report |
| Sep 27 | 92 | 54 | 75 | 4 | "last week" column, Oct 5 report |
| Oct 4 | 95 | 72 | 87 | 8 | Oct 5 report |
| Oct 11 | | 89 | | 16 | "last week" column, Oct 19 report |
| Oct 18 | | 94 | | 24 | Oct 19 report |

Five-year average for silage: 42 on Sep 20, 77 on Oct 4. Last year (2025) on Sep 20: 38. Grain moisture at harvest on Oct 18: 20%.

By district:

| District | Silage, Sep 20 | Silage, Oct 4 | Grain, Oct 4 | Grain, Oct 18 |
|---|---|---|---|---|
| NW | 62 | 98 | 15 | 46 |
| NC | 32 | 75 | 5 | 20 |
| NE | 44 | 91 | 2 | 14 |
| WC | 58 | 79 | 11 | 28 |
| C | 53 | 82 | 7 | 21 |
| EC | 54 | 91 | 7 | 20 |
| SW | 65 | 87 | 7 | 20 |
| SC | 63 | 93 | 6 | 24 |
| SE | 59 | 88 | 3 | 15 |

What this says about our hypothesis. **Inference from the table:** half the silage was in around September 19, when 85% of the crop was dented but only 38% mature. Grain reached 24% on October 18 with 94% mature. So in Wisconsin the two harvests are roughly five to six weeks apart at the median, silage sits between dent and black layer exactly as the agronomy says, and the tails overlap in the first half of October. Cut date alone separates most fields but not the overlap; that is where green-at-cut and residue earn their keep.

**The 2025 hole.** Both October reports carry this note: "Due to a lapse in federal funding in October and November 2025, the Crop Progress reports for the weeks ending October 5, 2025, through November 9, 2025, were canceled. Therefore, previous year estimates for the corresponding weeks will not be available." The 2025 silage curve exists through late September; the 2025 grain harvest curve does not.

**Other states and the national report.** Not verified. I could not open a national Crop Progress PDF (old NASS paths 404, ESMIS unreachable), and Quick Stats needs a key. Which states carry a weekly silage series is the first thing to ask the API (recipe in 3.5).

### 2.4 FSA Crop Acreage Data

**Not opened:** `www.fsa.usda.gov` timed out on every attempt (WebFetch and plain curl). What follows comes from the `rfsa` R package by Dylan Turner (NDSU), whose README and release manifest I did open: https://github.com/dylan-turner25/rfsa

- The package compiles "FSA's publicly available crop acreage data" for crop years 2012 to 2026, county level.
- Columns of the full table: `state_cd, county_cd, crop_cd, state, county, fips, crop, fsa_crop_type, intended_use, irrigation_practice, planted_acres, volunteer_acres, failed_acres, prevented_acres, not_planted_acres, planted_and_failed_acres, crop_yr, release_date, ...`. The cleaning script reads the workbook sheet `county_data`.
- The README lists "Intended use categories (e.g., grain, silage, grazing, dry edible)" and prints corn rows for Autauga County, Alabama with `intended_use` "Grain" and "Forage".
- Release manifest **[read from `fsa_acreage_urls.xlsx`]**:

| Release | URL |
|---|---|
| 2026 acreage data as of August 12, 2026 | https://www.fsa.usda.gov/sites/default/files/2026-08/jhIRZDbkVKX5.zip |
| 2026 acreage data as of September 11, 2026 | https://www.fsa.usda.gov/sites/default/files/2026-09/06OAypAHYasf.zip |
| 2026 acreage data as of October 9, 2026 | https://www.fsa.usda.gov/sites/default/files/2026-10/IV4i8vWMYLge.zip |
| 2025 acreage data as of January 12, 2026 | https://www.fsa.usda.gov/sites/default/files/2026-01/DoISjehvQfz9.ZIP |
| 2025 acreage data as of December 9, 2025 | https://www.fsa.usda.gov/sites/default/files/2025-12/UhYA3k5AKxVM.zip |

- The package readme notes there were no October or November 2025 releases because of the government shutdown.
- Intended use code list: `https://www.fsa.usda.gov/sites/default/files/documents/intended_use_codes.pdf` (not opened).
- Landing page: https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/frequently-requested/crop-acreage-data

**What is and is not established.** Established: the public county file has an intended-use column, corn rows are split by it, and a 2026 release dated October 9 exists. Not established by anything I opened: that corn rows carry a value literally called "Silage" in 2026, and how complete it is. A teammate with a browser can settle this in five minutes. If it holds, FSA is the best county prior available: it covers nearly all program-crop acres, where RMA covers a fifth of silage.

### 2.5 Census of Agriculture 2022

**Not opened.** From memory, to be confirmed with the API: Quick Stats holds county-level corn silage acres harvested and milk cow inventory for 2022 under `source_desc=CENSUS`, with "(D)" disclosure suppression in small counties. It is the only all-county silage benchmark, and it is four seasons old.

### 2.6 Quick Stats API

Verified from https://quickstats.nass.usda.gov/api
- Data: `https://quickstats.nass.usda.gov/api/api_GET/` (at most 50,000 records per call).
- Valid values: `.../api/get_param_values/`. Record count: `.../api/get_counts/`.
- A key is emailed after registering an address and accepting the terms.
- Parameters include `source_desc, commodity_desc, class_desc, util_practice_desc, statisticcat_desc, unit_desc, short_desc, agg_level_desc, state_alpha, asd_code, county_code, year, freq_desc, reference_period_desc, week_ending`.
- Operators: `__LE, __LT, __GT, __GE, __LIKE, __NOT_LIKE, __NE`. Formats: JSON, XML, CSV.
- Applications must show a notice that they are not endorsed or certified by NASS.

---

## 3. How to use them

### 3.1 Proof that the signal exists at scale (tonight)

Goal: replace "it works on the small evaluation set" with "the same two-question rule separates tens of thousands of declared parcels".

1. Download `BDPPAD_V03_2025.zip` (or 2026). Keep `NBPRO = 1` and `GROPRO in ('MGR','MAF')`, `SUPHEC >= 2`. Label = 1 when `GROPRO == 'MAF'`. That leaves roughly 40,000 parcels per year.
2. Sample a few thousand, stratified by class, in Montérégie and Centre-du-Québec (south of the St. Lawrence, nearest the US border).
3. Run the existing Kernel feature pipeline unchanged: radar cut date, green-at-cut, dry-down days, residue.
4. Fit the depth-2 tree there. Report precision, recall and false positive rate for silage, plus the two thresholds.
5. Apply the Quebec-fitted rule to the hackathon's US labeled set with no refit. Report the drop. A small drop is the headline; a big drop is the honest "where it fails" slide.

```python
import geopandas as gpd
g = gpd.read_file("BDPPAD_v03_AN_2025_s_20261109.shp",
                  where="NBPRO = 1 AND GROPRO IN ('MGR','MAF') AND SUPHEC >= 2")
g["silage"] = (g["GROPRO"] == "MAF").astype(int)
```

Optional second proof from a silage-dominant system, to mirror California. One line per Dutch class through the public service:

```
https://api.pdok.nl/rvo/gewaspercelen/ogc/v1/collections/brpgewas/items?f=json&limit=1000
# or WFS with a filter on gewascode = 259 (silage) and 316 / 317 (grain, corn-cob-mix)
```

For multi-year, multi-country pulls use EuroCrops v2 and filter on the native code:

```python
import geopandas as gpd
url = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/EuroCropsV2/gpqt/at_2023.parquet"
at = gpd.read_parquet(url)
at = at[at.original_code.astype(str).isin(["105", "109"])]   # 105 grain, 109 silage
```

### 3.2 Domain-shift caveats to state out loud

All of these are **inference** unless a source is named.

| Shift | Why it matters | Mitigation |
|---|---|---|
| Calendar and climate | Quebec and north-west Europe harvest later and wetter than Iowa; California is irrigated and earlier | Express cut date in growing-degree-days and relative to the regional median, as v2 already plans |
| Label is a declaration | Dutch reference date is 15 May; Austrian "-1" is the spring stock; Quebec allows a switch until mid-September (guide) | Prefer Quebec; in Europe prefer the Austrian "-2" winter revision; treat labels as noisy |
| Third classes | Corn-cob-mix, ear silage (NL 1935), biogas and energy maize (DE 172 / 10172, NL 2032), high-moisture grain | Drop them, or show them as a separate "in-between" group on the feature plot |
| Field size | Quebec median 4.5 ha (about 11 acres); Dutch parcels are small | Require 2 ha or more; note that US fields are larger, so pixel noise should be lower there |
| Class prior | Netherlands 94.5% silage by parcel count; Quebec about 18% by area; US about 6% | Report prior-free metrics (recall, false positive rate), then re-weight with the county prior (3.3) |
| Double cropping | California winter forage then corn has no Quebec equivalent | Austrian codes 174, 175, 764; DWR `MULTIUSE` for California geometry |
| Coverage bias | Quebec omits clients insured only for forage maize on a feed-need basis (guide) | Say so; it biases the silage sample toward mixed grain-and-dairy farms |

### 3.3 Weak supervision with county proportions

Targets, in order of preference for a county `c`:

| Target | Season | Coverage | Nature |
|---|---|---|---|
| NASS county estimate, silage acres / (silage + grain acres) | 2025 | 6 states, 180 counties | Official, CV about 2% |
| FSA intended use, silage acres / corn acres | 2026 | Potentially all counties | Unconfirmed, see 2.4 |
| RMA type 026 acres | 2025, 2026 | 481 counties in 34 states | Floor only |
| Census of Agriculture | 2022 | All counties, with suppression | Stale |

Three ways to use a target share `p_c`, simplest first.

**(a) Prior-shift correction. Transparent, one line, no retraining.** For a field score `q` from a model trained at silage prevalence `pi_train`:

```
q' = q * (p_c / pi_train) / [ q * (p_c / pi_train) + (1 - q) * ((1 - p_c) / (1 - pi_train)) ]
```

**(b) Quantile matching.** Within the county, sort fields by score and label the top fields silage until their area share equals `p_c`. Fully explainable, and it reconciles with the county total by construction. Use it for last year, where totals exist; do not use it to claim an early estimate.

**(c) Learning from label proportions, as a regulariser.** With fields `i` of area `a_i` in county `c`:

```
phat_c = sum_i a_i * q_i / sum_i a_i
L = L_supervised(small labeled set) + lambda * sum_c w_c * (phat_c - p_c)^2
```

Hold out whole counties to test the roll-up.

**RMA as a one-sided check, not a target:** predicted silage acres in a county should not fall below insured silage-type acres. Counties where they do are a ready-made error list for the analyst agent.

### 3.4 Validating detected harvest dates against progress curves

For each district `d` and each week ending date `w`:

```
S_d(w) = area of predicted-silage fields in d with detected cut date <= w
         / area of all predicted-silage fields in d
```

Compare `S_d(w)` with the NASS "Corn harvested for silage" percent, and do the same for grain.
- Report mean absolute error in percentage points across weeks, and the shift in days between the two curves at 50%.
- Accept a tolerance of about one week: the NASS number is a reporter's judgement for a week ending Sunday.
- Use 2026 for Wisconsin. For 2025 only the silage curve through late September is usable.
- **Inference:** this checks timing only. A wrong class split can still produce a good-looking curve, so it complements the county share check, it does not replace it.

### 3.5 Recipes for the US proxies

RMA, straight from the zip (note the `\r` record terminator):

```python
import pandas as pd
cols = ["year","st_fips","st_name","st","cty_fips","cty_name","cmdty","cmdty_name","plan","plan_abbr",
        "cov_type","cov_level","delivery","type_code","type_name","prac_code","prac_name","unit_code",
        "unit_name","net_amt","amt_type","liability","premium","subsidy","indemnity","loss_ratio","endorsed_amt"]
d = pd.read_csv("sobtpu_2026.zip", sep="|", header=None, names=cols, lineterminator="\r", dtype=str)
corn = d[d.cmdty == "0041"].assign(net_amt=lambda x: x.net_amt.astype(float))
by = corn[corn.type_code.isin(["016", "026"])].pivot_table(
        index=["st", "cty_fips", "cty_name"], columns="type_name", values="net_amt", aggfunc="sum").fillna(0)
```

Quick Stats. The parameter names are verified; the item names below are **from memory** and must be confirmed with `get_param_values` first:

```
# which corn items exist
https://quickstats.nass.usda.gov/api/get_param_values/?key=KEY&param=short_desc&commodity_desc=CORN

# county silage acres, crop year 2025
.../api/api_GET/?key=KEY&source_desc=SURVEY&commodity_desc=CORN&agg_level_desc=COUNTY&year=2025
    &short_desc=CORN, SILAGE - ACRES HARVESTED&format=CSV

# weekly silage harvest progress, all states, 2025 and 2026
.../api/api_GET/?key=KEY&commodity_desc=CORN&freq_desc=WEEKLY&year__GE=2025
    &short_desc__LIKE=%SILAGE%PROGRESS%&format=CSV

# Census 2022 county silage acres and milk cows
.../api/api_GET/?key=KEY&source_desc=CENSUS&year=2022&agg_level_desc=COUNTY
    &short_desc=CORN, SILAGE - ACRES HARVESTED&format=CSV
```

---

## 4. What this means for Kernel

1. **Add Quebec as the external labeled set.** It answers the judges' "small labeled evaluation set" problem with roughly 50,000 declared parcels a year, on this continent, for the season being judged. It is a new data source in the judging rubric's sense.
2. **Add RMA type acres as a county evidence layer.** It is the only verified county-level silage number for crop year 2026 that exists today. Present it as a floor. It also gives the Monday memo real numbers: insured silage acres up 3.5% nationally, California down 12.0%, Idaho up 18.8%.
3. **Show one timing chart:** our detected silage cut dates against the Wisconsin district curves for 2026.
4. **Say this sentence to the NASS statisticians:** NASS's own county models already take FSA and RMA administrative data as inputs and are benchmarked to state totals; our field-level probabilities are a third covariate of the same kind, available months before the survey closes. The source for that is NASS's June 2026 methodology note, and it also reports 39 to 40% survey response rates.
5. **Keep the v2 features.** Nothing here contradicts them. The Wisconsin table supports cut date as the first question and shows why a second question is needed for the October overlap.
6. **Drop any plan to mine WSDA, DWR, CSB or AAFC for silage labels.** They have none. DWR is still worth loading for California double-crop flags.
7. **Do not use EuroCrops harmonised classes.** Filter on native codes.

### What contradicts or constrains the current plan

- "Reconcile with NASS totals" at county level is possible for 2025 in only 6 states. Everywhere else the reconciliation is at state level, or against stale 2022 Census counties. Say so.
- Validation of 2025 grain harvest timing against Crop Progress is impossible for October and early November 2025.
- In California the majority class is silage. "Always silage" would score near 87% there by the brief's numbers. Report minority-class recall per state, not one national accuracy.

---

## 5. Annotated source list

Opened and read unless marked otherwise.

**Quebec**
- FADQ, BDPPAD download page. http://www.fadq.qc.ca/documents/donnees/base-de-donnees-des-parcelles-et-productions-agricoles-declarees/ : 24 annual zips, weekly Monday refresh, licence pointer.
- FADQ, "Guide de l'utilisateur, BDPPAD version 03", March 2025. https://www.fadq.qc.ca/fileadmin/geo4tb/BDPPAD/bdppad-v03-guide-utilisateur.pdf : definitions, declaration timing, biases, attribute table.
- `BDPPAD_V03_2025.zip`, `BDPPAD_V03_2026.zip`: counts in 1.2 read from the DBF.
- Open Government Canada record. https://open.canada.ca/data/en/dataset/1995c916-81e5-4eed-9142-c3763423dfc8 : CC-BY 4.0 Quebec, modified 2026-05-27.

**Europe**
- EuroCrops repository. https://github.com/maja601/EuroCrops and `hcat_core/HCAT3.csv`, `csvs/country_mappings/{at_2021,fr_2018,nl_2020,dk_2019,be_vlg_2021,de_nrw_2021,de_ls_2021}.csv`.
- Claverie, Chan et al. 2026, EuroCrops v2.0, ESSD 18:4075-4095. https://essd.copernicus.org/articles/18/4075/2026/essd-18-4075-2026.html
- JRC FTP. https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/EuroCropsV2/ : `readme.md`, `copyright.txt`, `all_gpqt_files.csv`.
- EuroCrops v2 mapping table. https://github.com/Martincccc/EuroCropsV2/blob/main/data/cropcodemapping/eurocrops.csv
- PDOK BRP collection. https://api.pdok.nl/rvo/gewaspercelen/ogc/v1/collections/brpgewas ; RVO code pages https://www.rvo.nl/gewascodes/316 and https://www.rvo.nl/gewascodes/317
- Austrian INSPIRE record (link in 1.3) and LFRZ OGC API.
- IGN Géoplateforme RPG feed. https://data.geopf.fr/telechargement/resource/RPG
- Reuss et al., EuroCropsML. https://arxiv.org/abs/2407.17458

**United States and Canada, parcel level**
- California Statewide Crop Mapping. https://data.ca.gov/dataset/statewide-crop-mapping ; 2023 final description via https://gispublic.waterboards.ca.gov/portalserver/rest/services/FMMP_and_DWR_Land/MapServer/0 ; DWR "Modified Standard Land Use Legend", December 2022 (linked from the dataset page).
- WSDA Agricultural Land Use. https://agr.wa.gov/Departments/Land-and-Water/Natural-Resources/Agricultural-Land-Use ; 2025 pivot table `https://cms.agr.wa.gov/WSDAKentico/Documents/DO/NRAS/2025WSDACropDataPivotTable.xlsx`.
- NASS Crop Sequence Boundaries. https://www.nass.usda.gov/research-and-science/crop-sequence-boundaries
- AAFC Annual Crop Inventory. https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9 and its class CSV.
- d'Andrimont et al. https://arxiv.org/abs/2112.09190

**United States, aggregates**
- RMA Summary of Business page and `SOBTPU_External_All_Years.pdf` (links in 2.1); `sobtpu_2025.zip`, `sobtpu_2026.zip`.
- NASS, Row Crops County Estimates Methodology and Quality Measures, June 5, 2026 (link in 2.2).
- NASS Wisconsin Crop Progress & Condition, reports of September 21, October 5 and October 19, 2026 (list page in 2.3); Wisconsin county estimates page https://www.nass.usda.gov/statistics-by-state/wisconsin/publications/county-estimates
- NASS Quick Stats API documentation. https://quickstats.nass.usda.gov/api
- `rfsa` package. https://github.com/dylan-turner25/rfsa (README, `data-raw/fsaCropAcreage/`).
- Secondary, for the earliest silage weeks only: https://www.midwestfarmreport.com/2026/09/15/a-third-of-wisconsins-silage-harvest-is-done/
- Secondary, on CAPS: The Peanut Grower, August 28, 2026. https://peanutgrower.com/?p=8294

**Not opened (do not cite as verified)**
- FSA crop acreage data page and files: site timed out.
- RMA cause of loss page: DNS failure.
- National NASS Crop Progress PDFs and ESMIS copies: 404 on old paths, ESMIS unreachable.
- Census of Agriculture 2022 tables.
- Swiss cantonal data, native Danish, Flemish, Walloon and German Länder portals (codes verified only through the EuroCrops mapping tables).
- France RPG licence page.

## 6. Open questions

1. Which six states have corn silage county estimates, and how much acreage sits in "Other Counties"? One Quick Stats call.
2. Which states publish a weekly corn silage harvest series for 2025 and 2026? One Quick Stats call.
3. Does the FSA file of October 9, 2026 split corn by an intended use called silage, and how complete is it?
4. Which season and which source produced the hackathon's "silage-like / grain-like" labels? If they come from FSA or RMA records, our RMA layer is partly the same information and must not be used as a feature when scoring.
5. Does any US research dataset with field-level silage labels exist? Not searched properly.
