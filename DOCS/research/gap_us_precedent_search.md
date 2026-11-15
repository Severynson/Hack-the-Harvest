# Gap: US precedent search, Spanish / Portuguese / Italian studies, and parcel-declaration codes

Research note for team Kernel, Hack the Harvest. Written Saturday 2026-11-14 (afternoon).
Scope: closes the gap left by `precedent.md` and `labels.md` - the dedicated US-academic search that was refused for budget, the Spanish / Portuguese / Italian searches that never ran, the Italian / Portuguese / Catalan parcel codes, and a retry of the two unopened papers.

Conventions: "Opened" means I read the source itself (page, API record, or the PDF text extracted locally). "Not opened" means the host refused; the reason is given and confidence is low. "Inference:" marks my own reasoning.

---

## 0. Bottom line

1. **No US study, thesis, extension report or agency paper that separates silage corn from grain corn by remote sensing, with a reported accuracy, was found.** 45 searches in eight languages (English, Spanish, Portuguese, Italian, Chinese, Catalan, French, Persian) plus direct API look-ups. This is absence of evidence, not proof: Google Scholar and ProQuest are not reachable from this environment.
2. **The only US-site precedent is still Salehi Shahrabi et al. 2020 (Tulare County, California; kappa 0.8 in 2017)**, and it is silage maize against other crops, not against grain maize. Its full text is still closed: two API records (OpenAlex, Semantic Scholar) and the publisher's listing as shown in search results agree on the abstract; Semantic Scholar reports `isOpenAccess: false` and no open PDF.
3. **A US voice has told USDA this is feasible, without a number.** NASA Harvest's response to the USDA Request for Information (Docket ERS-2026-0001, dated April 8, 2026, addressed to NASS, OCE-WAOB and ERS) says satellites can give "likely crop usage (e.g., corn silage vs. grain production)" from planting / harvest timing, phenology and management intensity. No accuracy, no citation. That is the gap Kernel fills.
4. **New: a public US field-level label source exists, in California.** Kern County's Department of Agriculture publishes permitted crop field polygons with a commodity name. I queried the public map service: 2025 has 751 fields / 48,802 acres of `CORN FOR/FOD` (corn for forage or fodder) against 5 fields / 306 acres of `CORN, GRAIN`; 2024 has 658 / 44,858 against 1 / 64, plus 1,044 fields / 77,635 acres of `WHEAT FOR/FOD` (the winter forage half of the double crop). This corrects `labels.md` bottom line 1 ("no public US parcel-level silage/grain label") for one county.
5. **The California coding is statewide.** The Department of Pesticide Regulation commodity list (updated 2/2026) has `22005 CORN (FORAGE - FODDER)` and `24002 CORN, FIELD, DENT (GRAIN CROP)` as separate codes. Every county permit and pesticide use report uses them. Which other counties publish the polygons is not confirmed (Stanislaus appears to).
6. **Spanish, Portuguese, Italian: no study separates silage from grain maize.** The closest is a 2025 Mexican paper (Comarca Lagunera) that maps forage maize against sorghum, pecan, cotton and alfalfa - no grain maize class. Nothing for Spain, Portugal, Brazil or Italy.
7. **Parcel declarations:** Italy carries separate codes (AGEA `1` grain versus `108` silage; Lombardy `010` versus `020`), but Lombardy's public layer merges them into one "MAIS" class. Portugal's public 2021 parcel layer has one maize code (`006 MILHO`). Catalonia and Spain have one maize product code (`004` / `4`).
8. **US timing numbers found:** a Wisconsin DNR survey of eight county conservation departments reports an average corn silage harvest date of September 20 against October 13 for corn grain (23 days), and that corn grain is part of dairy rotations in four of the eight counties (so rotation alone does not identify silage).

---

## 1. How this was researched, and its limits

- **Searches run: 45** (the brief asked for at least 12), all but two in "extended" mode. Languages: English 26, Spanish 5, Portuguese 4, Italian 5, Chinese 2, Catalan 1, French 1, Persian 1. Section 9 lists them.
- **Opened and read:** SciELO Mexico (full article), UC Davis CalAg caveats page, Kern County ArcGIS REST service (metadata and five live queries), California DPR commodity list (PDF, text extracted locally), Wisconsin DNR / CADMUS survey summary (PDF, text extracted locally), NASA Harvest RFI response (PDF, text extracted locally), Lombardy SIARL legend (PDF), Lazio crop-code annex (PDF), Catalan DUN 2024 product table (PDF), Catalan open-data dataset metadata (API), EuroCrops mapping CSVs for Portugal and Spain (GitHub raw), EuroCrops v2.0 paper (first 100,000 characters), Quebec BDPPAD user guide (PDF) and download page, OpenAlex / Crossref / Semantic Scholar API records, Zenodo record, University of Illinois lab page.
- **PDFs:** the fetch tool returns PDFs as binary. I extracted text locally with a small standard-library Python script (zlib plus the fonts' ToUnicode maps). Table rows quoted below are from that extraction.
- **Not reachable today:** `tandfonline.com` (HTTP 403), `mdpi.com` (HTTP 403, three URLs), `doaj.org` (403), `fega.gob.es` (connection refused), `kernag.com` (connection reset), `fsa.usda.gov` (timeouts, three URLs), `j-csam.org` (socket hang up), `agroportal.pt` (403), `bandi.regione.lombardia.it` (502), `static.regione.marche.it` (certificate error). IFAP pages return only the navigation menu (content is rendered by script). The Portuguese Portaria PDF downloaded but its text could not be extracted.
- **Not possible here:** Google Scholar, ProQuest Dissertations, CNKI. University repositories were reached only through the general search engine. "None found" for theses is therefore weaker than for journal papers.

---

## 2. Answers to the gap questions

| Question | Answer | Confidence |
|---|---|---|
| Any US study that separates silage from grain corn by remote sensing? | None found. | Medium (absence of evidence) |
| Any US thesis or extension report? | None found. US silage work found is yield estimation (New York), not classification. | Medium-low (no ProQuest access) |
| Any US agency paper? | No method paper. NASA Harvest (April 2026) asserts feasibility to USDA; Wisconsin DNR (2020) assigns silage by rotation class, not by satellite harvest signal; CDL has one corn class. | Medium |
| Any Spanish-language study? | One Mexican study maps forage maize, but not against grain maize. None for Spain. | Medium |
| Any Portuguese-language study (Brazil, Portugal)? | None found. | Medium |
| Any Italian study? | None found. | Medium |
| Italian parcel declarations: separate codes? | Yes (two independent code lists). Public Lombardy layer merges them. | High |
| Portuguese parcel declarations: separate codes? | Public 2021 parcel layer: no, one code `006 MILHO`. Since 2023 IFAP lists separate coupled supports "Milho Grão" and "Milho Silagem"; whether the public parcel layer shows it is unknown. | Medium |
| Catalan parcel declarations: separate codes? | No. One product code `004 BLAT DE MORO`. | High |
| Ulan Buh paper (Zhang et al. 2025, J-CSAM) | Still not opened. | Low |
| Salehi Shahrabi et al. 2020 full text | Still closed. Abstract re-confirmed from three records. | High for the abstract |

---

## 3. Annotated bibliography

### 3.1 United States

**U1. Salehi Shahrabi, Ashourloo, Moeini Rad, Aghighi, Azadbakht, Nematollahi (2020). "Automatic silage maize detection based on phenological rules using Sentinel-2 time-series dataset." International Journal of Remote Sensing 41(21), 8406-8427. DOI 10.1080/01431161.2020.1779377.**
- Opened: OpenAlex record https://api.openalex.org/works/doi:10.1080/01431161.2020.1779377 ; Semantic Scholar record https://api.semanticscholar.org/graph/v1/paper/DOI:10.1080/01431161.2020.1779377 ; Crossref record https://api.crossref.org/works/10.1080/01431161.2020.1779377 (metadata only, no abstract).
- Not opened: full text, https://www.tandfonline.com/doi/abs/10.1080/01431161.2020.1779377 (HTTP 403; closed access; no open copy listed by OpenAlex or Semantic Scholar). A Persian-language search for an open Iranian version found nothing.
- What the abstract shows: three Iranian sites (Marvdasht, Abyek, Mashhad) and "an individual area in the USA (Tulare County, California)"; Marvdasht is the training site, the other three are test sites; Sentinel-2 NDVI for 2017 and 2018; Savitzky-Golay filter, linear interpolation; phenological parameters extracted "for maize and other crops"; proposed variable is "the ratio of the slope from the peak greenness to harvest (SPGH)" to the length of the growing season (LOS); "kappa coefficient values of 0.89, 0.8, 0.9, and 0.8" for Abyek, Marvdasht, Mashhad and Tulare in 2017; 2018 close to 2017; a support vector machine trained with many samples was comparable, maximum likelihood worse.
- What it does not show: the words "grain maize" do not appear in the abstract; no reference data source is named for Tulare; no thresholds; no user's / producer's accuracy.
- Inference: this is a "maize harvested green versus other crops" detector tested in a county where nearly all corn is silage. It does not test silage against grain corn. It does defeat an unqualified "first US test of silage detection from satellites".
- Records: 11 citations (Crossref, Semantic Scholar), 14 (OpenAlex).

**U2. NASA Harvest and NASA Acres researchers (University of Maryland and partners). Response to USDA Request for Information, "RE: Docket ID No. ERS-2026-0001", dated April 8, 2026. Addressed to NASS, OCE-WAOB and ERS. Signatories on the last page include I. Becker-Reshef, A. Whitcraft, E. Benami, M. Humber, C. Justice and R. Rejesus. 4 pages.**
- Opened: https://www.agri-pulse.com/ext/resources/pdfs/NASA-Harvest.pdf (text extracted locally).
- Exact sentence: "EO can provide useful insight on active vs. fallow cropland status as well as crop type and, in some cases, likely crop usage (e.g., corn silage vs. grain production), based on features such as planting/harvest timing, phenology, and management intensity."
- Same paragraph: Landsat and Sentinel-2 models "have achieved accuracies above 80% for multiple crops by mid-summer"; in-season crop type mapping across nine US states comparable with the In-Season Cropland Data Layer "but delivered one month ahead".
- No accuracy and no citation is attached to the silage-versus-grain statement.
- Use: a 2026 statement to the very agency that judges us that the task is plausible and unquantified.

**U3. Wisconsin Department of Natural Resources and The CADMUS Group (September 18, 2020). "Northeast Lakeshore TMDL: Agricultural Practice Summary."**
- Opened: https://dnr.wisconsin.gov/sites/default/files/topic/TMDLs/NEL_ag_survey_summary.pdf (text extracted locally).
- Method: "The Wiscland 2.0 (Wiscland) land cover dataset was used to initially define the type and extent of different crop rotation types". "Six general crop rotation types are represented in the Wiscland dataset in the NE Lakeshore basin: dairy, cash grain (i.e., corn and soybean), continuous corn, potato/vegetable, pasture, and hay." Land and Water Conservation Departments of eight counties were surveyed to check them.
- Findings: "A total of 23 unique dairy crop sequences were reported", "average rotation length of seven years"; "dairy rotations were predominately comprised of two to four years of corn silage followed by three to four years of alfalfa. Corn grain was reported to be a part of dairy rotations by four of the eight counties." Winter wheat, oats and peas appear as transitional crops in some counties.
- Timing: average planting date May 21 (all crops); "The average harvest date for corn grain was October 13th. As expected, the average harvest date for corn silage was earlier, approximately three weeks prior to corn grain (September 20th)." Soybeans October 7.
- Wiscland check: the survey found Wiscland "accurately represents the acres of dairy, cash grain, continuous corn, and continuous hay, but over represents the amount of potato/vegetable and pasture acres".
- Use: (a) a US agency already infers silage from a rotation class, with no satellite harvest signal; (b) US timing numbers; (c) a documented reason why rotation alone is not enough.
- Not checked: the Wiscland 2 user guide (how the rotation classes were derived). The DNR map service describes the layer as "Wiscland2 Level3 Crop Rotation" (search result only).

**U4. UC Davis CalAg, "Data Caveats - California County Crop Dashboard".**
- Opened: https://calag.ucdavis.edu/ca_county_crops_caveats.html
- "Land IQ maps the main-season crop growing on each field, so its acreage is a footprint rather than a harvest." "A field double-cropped with, say, winter grain and summer tomatoes contributes its acres once, to the main crop only."
- "The other seasons are recorded in the mapping and we now measure them, about 388,000 to 498,000 additional acres a year from 2018 onward, or 6 to 8% of the mapped cropped area."
- "More than half of that acreage is winter forage wheat grown ahead of corn silage, which the commissioners report as silage or hay rather than as wheat."
- "In 2023, adding both would have taken statewide wheat from 8% above the Commissioner figure to 122% above it".
- "Corn (and sorghum) grown for silage is counted in Corn / Sorghum throughout the panel." "Stanislaus reports its corn — silage and grain — only inside a combined silage line in 2023–2024." Kern "reports a single 'Silage and Forage' line."
- "The 2014 vintage records no seasons at all, and 2016 records them only as a broad grain-and-hay class, so this measurement begins with 2018."
- Use: a UC Davis product that quantifies the winter-forage-then-corn double crop USDA named as a trap, and shows that even county commissioners merge silage lines. UC Davis judges may know it.

**U5. Kern County Department of Agriculture and Measurement Standards, permitted crop field boundaries.** See section 5.

**U6. California Department of Pesticide Regulation, "Commodity Codes by Name for Permit/Pesticide Use Report (PUR) Programs", updated 2/2026.** See section 5.

**U7. Liu, Diao and co-authors (2025). "A novel Normalized Harvest Phenology Index (NHPI) for corn and soybean harvesting date detection using Landsat and Sentinel-2 imagery on Google Earth Engine." Remote Sensing of Environment. DOI 10.1016/j.rse.2025.115016.**
- Opened: lab news post https://diaorssilab.web.illinois.edu/2025/10/18/a-novel-normalized-harvest-phenology-index-nhpi-for-corn-and-soybean-harvesting-date-detection/ - NHPI "integrates the Normalized Difference Vegetation Index (NDVI) and the Near-Infrared (NIR) reflectance", a NIR-to-NDVI ratio that "amplifies the harvesting signal in its time series"; US Midwest, 2020-2023; Landsat and Sentinel-2 in Google Earth Engine. Silage is not mentioned.
- Not opened: the paper. A search summary gives field-level mean absolute error 4 days and R2 0.85; treat as unverified here (see `optical_harvest.md`, which covers this paper).

**U8. US silage remote sensing that is not classification (search listings only, not opened).**
- Thompson and Ketterings (2024), "Exploring the Use of High-Resolution Satellite Images to Estimate Corn Silage Yield Within Field", Remote Sensing 16(21):4081, https://www.mdpi.com/2072-4292/16/21/4081 - two New York dairy farms, three years, yield.
- Burglewski (2024), RIT master's thesis, "On the Optimization of Sensors for the Remote Sensing of Crop Yield", https://repository.rit.edu/theses/11942/ - corn silage yield, sensor design.
- "Corn grain and silage yield class prediction for zone delineation using high-resolution satellite imagery", Agricultural Systems, https://www.sciencedirect.com/science/article/abs/pii/S0308521X24001598 - yield classes on fields already known to be grain or silage.
- Inference: US academic silage work treats the use as known from the farmer and models yield. It is not a counter-example.

**U9. Negative results.**
- Minnesota Board of Water and Soil Resources / University of Minnesota residue-cover report (2020), https://bwsr.state.mn.us/sites/default/files/2020-11/BWSR_Final_report_Sept2020_Residue_Cover_and_Erosion_Final.pdf : opened, text extracted, the word "silage" does not occur.
- NASS Research and Development Division: no report on silage versus grain utilisation by remote sensing surfaced in two searches restricted to NASS wording. CDL corn classes are Corn (1), Sweet Corn (12), Pop or Orn Corn (13) (already verified in `precedent.md`).
- USDA-ARS Dairy Forage Research Center, UC ANR, Cornell, Penn State, Idaho: nothing on satellite separation of silage and grain surfaced.

### 3.2 Spanish-language

**S1. Delgado-Ramírez, Bolaños-González, Quevedo-Nolasco, López-Pérez, Estrada-Ávalos (2025). "Clasificación Supervisada para el Mapeo del Maíz Forrajero Mediante Teledetección en la Región Lagunera, México." Terra Latinoamericana 43, e2123. DOI 10.28940/terra.v43i.2123.**
- Opened: https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S0187-57792025000100130&lng=pt&nrm=iso&tlng=es
- Area: irrigation modules X (Masitas) and XII (El Porvenir), Irrigation District 017, spring-summer 2021; 14,276.70 ha.
- Data: Sentinel-2 Level-2A, tile T13RFJ, three dates (22 May, 11 June, 26 June 2021), covering tasselling (VT) to milk stage (R3). All 12 bands; NDVI (B8, B4) only to mask bare soil (NDVI 0.08 to 0.10).
- Classes: (1) forage maize, (2) other crops (forage sorghum, pecan, cotton, alfalfa), (3) vacant. **No grain maize class.** No double cropping, no winter crops.
- Ground truth: GPS-delimited plots; module X 92 plots / 764.20 ha (34 forage maize plots / 332.96 ha); module XII 109 plots / 783.49 ha (25 forage maize plots / 306.05 ha); 70 / 30 split.
- Best: Random Forest, 100 trees, 11 June image.

| Module | Overall accuracy | Kappa | Forage maize user's accuracy | Forage maize producer's accuracy |
|---|---|---|---|---|
| X | 79.1% | 0.63 | 90.5% | 75.4% |
| XII | 87.4% | 0.79 | 90.3% | 90.1% |

- Other algorithms on 11 June (module X / XII overall accuracy): RF 20 trees 77.9 / 85.9; maximum likelihood 75.2 / 77.7; minimum distance 44.7 / 69.0; spectral angle mapper 40.4 / 68.0.
- Forage maize covers about 44% of the area (46.5% of module X, 43.9% of module XII in the map).
- Caveat noted while reading: the text says 100% of pixels classified as forage maize were correct, while the matrix gives 90.5%.
- Use: confirms the pattern in `precedent.md` pitfall 6. In a dairy basin all maize is forage, so "forage maize mapping" is maize mapping. Not a silage-versus-grain precedent. The sorghum confusion is relevant for the Texas and Kansas feedyard belt.

**S2. Search listings only (not opened):** "Estimación de Cosecha de Maíz Forrajero mediante índices espectrales derivados de LANDSAT-8 y SENTINEL-2" (Terra Latinoamericana 2023; forage maize biomass, R2 0.66 at 72 days after sowing); "Estimación del coeficiente de cultivo del maíz forrajero por teledetección" (2023). Yield and water use, not classification.

**S3. Spain:** nothing found for Galicia, Cantabria, Lleida or elsewhere. No SIAP (Mexico) method that separates forage from grain maize by satellite surfaced.

### 3.3 Portuguese-language

Nothing found for Brazil or Portugal. Results were agronomy pages, yield-NDVI correlations, and code repositories that map "milho" as one class. The Rio Grande do Sul technical bulletin reports grain and silage maize areas separately (search summary; statistics, not remote sensing).

### 3.4 Italian

**I1.** No study on separating "mais da trinciato / silomais / mais ceroso" from "mais da granella" by satellite was found in five Italian-language searches or two English searches aimed at the Po Valley and Lombardy.

**I2. Croci, M. (Università Cattolica del Sacro Cuore). Zenodo record, "Analysis code for 'Short-stature versus conventional silage corn production systems on commercial dairy farms'", version 1.0, published October 31, 2026. DOI 10.5281/zenodo.23835741.**
- Opened: https://zenodo.org/records/23835741
- 46 paired site-years on commercial dairy farms in the Po Valley, 2023-2024; predictors from Sentinel-2, Sentinel-1, Landsat and ERA5-Land through Google Earth Engine, aligned to phenology with growing degree days; mixed-effects models; leave-one-farm-out validation. Field records embargoed until August 31, 2027.
- Not a classification study. Evidence that Po Valley silage fields with known management exist in a research group that already uses our data sources.

**I3. Maleki, Baghdadi et al. (2024), "Machine Learning-Based Summer Crops Mapping Using Sentinel-1 and Sentinel-2 Images", Remote Sensing 16(23):4548.** Surfaced in the Italian search. Opened the OpenAlex record (https://api.openalex.org/works/doi:10.3390/rs16234548): two sites in France, two years; maize is a single class (best mean F1 93.5% with InceptionTime, 91.1% with XGBoost on Sentinel-1 backscatter plus Sentinel-2 indices). Not relevant to silage versus grain.

### 3.5 Retry of the two unopened papers

**C1. Zhang et al. 2025, "基于NDVI时序特征的作物样本扩充与遥感精细识别", Transactions of the Chinese Society for Agricultural Machinery 2025(5) (Ulan Buh).** Not opened: https://www.j-csam.org/html/2025/5/20250535.html returned "socket hang up" (the earlier agent failed four times). A guessed DOI (10.6041/j.issn.1000-1298.2025.05.035) returns 404 at OpenAlex; an OpenAlex title search returns no match; two Chinese-language searches and one English search did not surface an abstract. A search listing confirms only that a paper with this title is in the 2025 issue 5 table of contents. Status unchanged: do not cite numbers.

**C2. Salehi Shahrabi et al. 2020.** See U1. Abstract confirmed in three records; full text closed.

**C3. Lin, Huang, Tan, Yang, Huang, Su, Hu (2025), "Silage Maize Identification Using a Temporal Difference-Based Model with Sentinel-2 Data", Agronomy 15(6):1438.** Re-checked as a control. Opened the OpenAlex record (https://api.openalex.org/works/doi:10.3390/agronomy15061438); the publisher pages returned HTTP 403 today. The abstract matches `precedent.md`: overall accuracy 0.9291, kappa 0.8923; user's accuracy 0.9216 / 0.9219 / 0.9404 and producer's accuracy 0.94 / 0.9008 / 0.9467 for silage maize, grain maize and other; F1 0.9307 / 0.9112 / 0.9435; random forest baseline 0.9043 and kappa 0.8511; multi-year 0.8621 (2022) and 0.8816 (2021). Authors are from Hangzhou Dianzi University, Zhejiang University and the Hohhot Meteorological Bureau. The abstract opens by citing "the limited research on silage maize classification in China". Thresholds are in `precedent.md` Recipe A.

---

## 4. Parcel-declaration codes

| Jurisdiction | Grain maize | Silage / forage maize | Is the split public at parcel level? | Source (opened) |
|---|---|---|---|---|
| Italy, product codes in the Regione Lazio rural-development annex "Codici colturali per gruppi di coltura" (file dated 2015; columns Codice Prodotto / Codice Uso / Coltura). Code 108 matches the AGEA code "108 SILOMAIS E MAIS CEROSO" seen in a Regione Marche table (search listing only) | `1 / 0  GRANTURCO (MAIS) DA GRANELLA` (Group B, cereals) | `108 / 0  GRANTURCO (MAIS) - INSILATO` (Group A2, forage crops) | Not checked for Lazio | https://www.lazioeuropa.it/app/uploads/2022/04/codici_colturali_m11.pdf |
| Italy, Lombardy SIARL / SISCO farm file | `010 MAIS DA GRANELLA` | `020 SILOMAIS E MAIS CEROSO`; also `390 MAIS DA FORAGGIO` and `110 INSILATI DI CEREALI` under forage | **No.** The published "Carta uso agricolo" groups 010 and 020 into one class "MAIS" (20 m grid, years 2012-2019, dominant use per cadastral parcel) | https://www.cartografia.servizirl.it/metadata/raster/lyr/UTM/ags/doc/Utilizzo_agroforestale_da_dati_SIARL.pdf and https://www.geoportale.regione.lombardia.it/news/-/asset_publisher/80SRILUddraK/content/carta-uso-agricolo-dati-siarl-dal-2012-al-2019 |
| Portugal, IFAP parcel layer 2021 (EuroCrops mapping) | `6 MILHO` | none; "silagem" does not occur in the mapping table | No (one code) | https://raw.githubusercontent.com/maja601/EuroCrops/main/csvs/country_mappings/pt_2021.csv |
| Portugal, IFAP from 2023 | "Milho Grão" coupled support | "Milho Silagem" coupled support (IFAP help menu lists both, each with rules, FAQ and legislation pages) | Unknown; the rules page did not render | https://www.ifap.pt/portal/en/superficies-pagamento-milho-silagem-regras (menu only) |
| Catalonia, DUN 2024 product table | `004 BLAT DE MORO` | none (`247 BARREJA FARRATGERES` and `392 MONGETA I BLAT DE MORO` are mixtures) | No (one code). Open map has columns Cultiu, Varietat, Producte2n (second crop), Seca_Regad, Sist_Regad; no use column; campaigns 2016-2024 | https://agricultura.gencat.cat/web/.content/09-desenvolupament-rural/declaracio-unica-agraria/enllacos-documents/formacio/fitxers-binaris/dun2023-tr-19-productes-dun.pdf and https://analisi.transparenciacatalunya.cat/api/views/yh94-j2n9.json |
| Spain, national 2023 (EuroCrops mapping) | `4 MAÍZ` | none (`326 MAÍZ DULCE`, mixtures, `935 OTRAS FORRAJERAS`) | No (one code) | https://raw.githubusercontent.com/maja601/EuroCrops/main/csvs/country_mappings/es_2023.csv |
| California, DPR commodity codes (permits, pesticide use reports) | `24002 CORN, FIELD, DENT (GRAIN CROP)` | `22005 CORN (FORAGE - FODDER)` | **Yes in Kern County** (section 5) | https://www.cdpr.ca.gov/wp-content/uploads/2025/04/comby_nam.pdf |
| Quebec, BDPPAD (already in `labels.md`) | group `MGR Maïs-grain` | group `MAF Maïs fourrager` | Yes, 2003-2026, CC-BY 4.0 | https://www.fadq.qc.ca/fileadmin/geo4tb/BDPPAD/bdppad-v03-guide-utilisateur.pdf |

Notes.
- Lombardy caveat in the source: the layer "ha valore esclusivamente per scopi divulgativi e comunicativi" and should not be used to compute crop areas. The geoportal page adds: "Questi dati non sono adatti per calcoli numerici di precisione."
- Spain: FEGA's SIEX catalogues include a "Destino del producto" list (search summary of FEGA circular 2/2023). The FEGA site refused connections, so I could not check whether it separates "ensilado" from "grano". Unverified.
- Italy, other regions: Tuscany (ARTEA) publishes "Piani Colturali Grafici" 2017-2026 by province as open data (search listing, not opened); EuroCrops v2.0 lists region ITI1 (Tuscany). Whether code 108 survives there is not checked, and Tuscany is not a silage region.
- Portugal: the EuroCrops v2.0 paper reports that only 42% of Portuguese labels matched its taxonomy and notes the grain / silage distinction "is not captured as well" in its Eurostat comparison.
- Quebec guide, useful details confirmed: declarations are complete by August 1; "Pour le maïs, l'avoine, le blé et le soya, il est possible d'avoir un changement de mode de récolte (récolté en grain ou en fourrage) jusqu'à la mi-septembre"; since 2010 clients insured only for hay or forage maize on a feed-need basis are no longer compiled (so forage maize is under-covered); the production "doit être considérée comme une déclaration et non comme une vérité terrain"; the cultivar field carries corn heat units ("UTM").

---

## 5. New data source: Kern County, California, permitted crop field boundaries

**What it is.** A public ArcGIS map service of agricultural field polygons, one layer per permit year, with the commodity declared on the pesticide permit.
- Service: https://maps.kerncounty.com/arcgis/rest/services/AgComm/ag_HistoricalCrops_pub/MapServer (opened). Description begins "The Kern County Department of Agriculture and Measurement Standards created this dataset" to locate production agricultural field boundaries.
- Layers today: `0` kern 2026, `1` kern 2025, `2` kern 2024, `3` kern 2023, `4` kern 2022.
- Fields: `PMT_SITE`, `PERMIT`, `SITEID`, `COMM` (commodity, 15 characters), `ACRES`, `PMT_YEAR`, `DT_ACT`, `DT_INACT`, `P_STATUS`, `S_STATUS`, `TOWNSHIP`, `RANGE`, `SECTION`, plus permittee name and address fields. Spatial reference WKID 102645 (latest 2229). Maximum 1,000 records per request; statistics, DISTINCT, ORDER BY and pagination are supported.
- Shapefiles: the department's page http://www.kernag.com/gis/gis-data.asp is said to offer "all permitted shapes from 2021 through 2026 (11,667 KB)" and digitising since 1997 (search summary; the page itself reset the connection - not opened).

**What I measured (live statistics queries on 2026-11-14, grouped by `COMM`; "fields" = records, one permit-site polygon each; selected rows).**

| Commodity (`COMM`) | 2024 fields | 2024 acres | 2025 fields | 2025 acres | 2026 fields (layer still filling) | 2026 acres |
|---|---|---|---|---|---|---|
| CORN FOR/FOD | 658 | 44,858.05 | 751 | 48,802.02 | 449 | 29,972.76 |
| CORN, GRAIN | 1 | 64 | 5 | 306 | none returned | - |
| CORN, SWEET | 1 | 75 | 1 | 75 | 1 | 75 |
| CORN FOR/FOD-OR (organic) | none returned | - | 1 | 1 | 1 | 1 |
| WHEAT FOR/FOD | 1,044 | 77,634.64 | not queried | - | 395 | 29,397.51 |
| OAT FOR/FOD | 48 | 2,250.6 | not queried | - | 34 | 1,669 |
| SORGHUM FOR/FOD | 18 | 1,574.75 | not queried | - | 1 | 364 |
| RYEGRAS FOR/FOD | 18 | 1,091.5 | not queried | - | not returned | - |
| BARLEY FOR/FOD | 8 | 494 | not queried | - | 20 | 1,617 |
| TRITICALE | not queried | - | not queried | - | 66 | 3,100.45 |

(The 2025 query filtered on `COMM LIKE '%CORN%'` only; the 2024 and 2026 queries also asked for `%FOR/FOD%`.)

**Commodity names map to state codes.** DPR list, updated 2/2026 (opened, text extracted): `22005 CORN (FORAGE - FODDER)`; `24002 CORN, FIELD, DENT (GRAIN CROP)` (marked "NEW NAME"); `29119 CORN, SWEET`; `15004 CORN, POP (GRAIN CROP)`; `22007 WHEAT (FORAGE - FODDER)` and `29139 WHEAT`; `22006 OAT (FORAGE - FODDER)`; `22004 SORGHUM (FORAGE - FODDER)`; `22008 BARLEY (FORAGE - FODDER)`; `22011 SUDANGRASS`; `24011 TRITICALE`; `22000 FORAGE HAY/SILAGE`. DPR's letter to county commissioners of 03/09/2026 (ENF 26-05, opened: https://www.cdpr.ca.gov/cac-letter/pesticide-use-report-program-commodity-code-updates/) confirms the codes are used on restricted material permits, operator identification numbers and pesticide use reports, and names "Corn, field dent, (grain crop) (24002)".

**Why it matters.**
- It is the only public US field-level source found that labels corn as forage / fodder versus grain. It sits in the state where the balance flips and where the double-crop trap lives.
- The winter forage polygons (wheat, oat, triticale, barley, ryegrass for forage / fodder) give the other half of the double crop for the same fields.
- It is a "new data source" in the judging sense, and it is a California source that UC Davis judges will recognise.

**Caveats.**
- Declared commodity on a pesticide permit, not a harvest record. "Forage - fodder" covers silage, green chop and any whole-plant feed use.
- `DT_ACT` and `DT_INACT` are administrative dates of the permit site, not planting or harvest dates (sample 2025 records show `DT_ACT` in November and December 2025).
- Class balance is the mirror image of the Midwest: 751 to 5 in 2025. It can test silage recall and the double-crop handling; it cannot train or test grain precision.
- The 2026 layer was still filling when queried (449 corn forage fields against 751 in 2025).
- A field can appear as several polygons with different commodities in one year. Inference: overlapping `WHEAT FOR/FOD` and `CORN FOR/FOD` polygons are the double-crop fields; this needs a spatial overlay to confirm.
- One county only. Kern's own crop report merges silage into a "Silage and Forage" line (CalAg, U4).

**Recipe to pull it (no key needed).**

```
BASE = https://maps.kerncounty.com/arcgis/rest/services/AgComm/ag_HistoricalCrops_pub/MapServer
# 1. Confirm layer ids:      GET {BASE}?f=json
# 2. Counts by commodity:    GET {BASE}/1/query?where=COMM LIKE '%CORN%'
#      &outStatistics=[{"statisticType":"count","onStatisticField":"OBJECTID","outStatisticFieldName":"n"},
#                      {"statisticType":"sum","onStatisticField":"ACRES","outStatisticFieldName":"acres"}]
#      &groupByFieldsForStatistics=COMM&returnGeometry=false&f=json
# 3. Polygons, 1,000 per page: GET {BASE}/1/query?where=COMM LIKE 'CORN%' OR COMM LIKE '%FOR/FOD%' OR COMM='TRITICALE'
#      &outFields=PMT_SITE,COMM,ACRES,PMT_YEAR,TOWNSHIP,RANGE,SECTION
#      &outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000   (then resultOffset=1000, 2000, ...)
```
URL-encode the `where` and `outStatistics` values. Drop the permittee name and address fields: they are personal data we do not need.

**Suggested use tonight (Inference).**
1. Pull layer 1 (2025) corn and forage polygons; keep polygons of 10 acres or more.
2. Run the existing feature pipeline on them unchanged.
3. Report silage recall on the `CORN FOR/FOD` fields, split by "has an overlapping winter forage polygon" versus "does not". This is a direct, labelled test of the double-crop trap.
4. Show the 5 `CORN, GRAIN` fields as individual evidence cards, not as a statistic.

---

## 6. US numbers that can serve as priors or thresholds

| Quantity | Value | Where | Source |
|---|---|---|---|
| Average corn silage harvest date | September 20 | NE Wisconsin, 8 counties, survey of conservation departments | U3 |
| Average corn grain harvest date | October 13 | same | U3 |
| Silage-to-grain gap | about 3 weeks (23 days) | same | U3 |
| Average planting date, all crops | May 21 | same | U3 |
| Dairy rotation | 2 to 4 years corn silage, then 3 to 4 years alfalfa; average length 7 years; 23 distinct sequences | same | U3 |
| Corn grain inside dairy rotations | reported by 4 of 8 counties | same | U3 |
| Kern County corn for forage / fodder | 751 fields, 48,802 acres (2025) | Kern County, California | section 5 |
| Kern County corn for grain | 5 fields, 306 acres (2025) | same | section 5 |
| Kern County winter wheat for forage / fodder | 1,044 fields, 77,635 acres (2024) | same | section 5 |
| Double-cropped acres not counted in main-season maps | 388,000 to 498,000 acres a year from 2018, 6 to 8% of mapped cropped area; more than half is winter forage wheat ahead of corn silage | California | U4 |
| Tulare County silage maize detection | kappa 0.8 (2017), versus other crops | Tulare County, California | U1 |

---

## 7. Formulas and recipes referenced

- **NDVI** (Sentinel-2) = (B8 - B4) / (B8 + B4). Used by S1 (soil mask), U1 (the whole method).
- **SPGH / LOS** (U1), reconstructed from the abstract wording, as in `precedent.md` Recipe B: SPGH = (NDVI at peak - NDVI at harvest) / (harvest date - peak date); LOS = harvest date - start-of-season date; feature = SPGH / LOS. Smoothing: Savitzky-Golay, then linear interpolation. Thresholds unpublished in open sources. Inference: this is our "cliff versus fade" clue as one number.
- **NHPI** (U7) = NIR / NDVI, harvest = first date the index crosses a threshold. Inference on bands: NIR = B8A (Sentinel-2) or B5 (Landsat 8 / 9) in the Harmonized Landsat Sentinel-2 product; the lab page does not list bands.
- **TempDiff-SMID** (C3): see `precedent.md` Recipe A (September LSWI <= 0.15 as the deciding condition). Not re-derived here because the publisher blocked the full text today.
- **Rotation class** (U3): dairy rotation = corn years alternating with multi-year alfalfa; cash grain = corn and soybean. Source wording only; Wiscland's derivation not checked.
- **Double-crop flag for California (Inference, uncalibrated):** winter green peak between January and April, a drop in April or May, then a corn peak in July or August. Calibrate the winter peak threshold on Kern fields that carry both a winter forage polygon and a `CORN FOR/FOD` polygon.

---

## 8. What this means for Kernel

**For the pitch.**
1. Do not say "first US test" without a qualifier. Say: "To our knowledge, the first open, field-level test of silage against grain corn on US fields. The published record has one silage-against-other-crops check in Tulare County (2020, kappa 0.8) and one silage-against-grain study in Inner Mongolia (2025, F1 0.93 / 0.91)." That sentence survives a judge who knows either paper.
2. Use the NASA Harvest sentence (April 8, 2026, to NASS) as the opening: USDA has been told usage can be inferred from harvest timing and phenology; nobody has published a US accuracy number.
3. For UC Davis judges, cite their own CalAg figure for the double crop (388,000 to 498,000 acres a year, more than half winter forage wheat ahead of corn silage) and show the Kern County test.

**For the build (next 18 hours).**
4. Add Kern County 2025 as an independent California check (section 5). It costs a few REST calls and turns the "California trap" from a caveat into a measured result.
5. Keep rotation as a tie-breaker only. Wisconsin's own survey found corn grain inside dairy rotations in half the counties.
6. Use September 20 versus October 13 as a sanity check on our cut-date distributions for Wisconsin, and express the cut date relative to the county median as planned.
7. Keep SPGH / LOS as one extra feature in the autoresearch loop; it is the only published feature with a US test site.

**For the "how it could be developed further" slide.**
8. Italy's declarations split silage (108 / 020) from grain (1 / 010), but the open Lombardy layer merges them; Portugal and Spain publish one maize code. The open label sources that do split are the ones in `labels.md` (Quebec, Netherlands, Austria, France and others) plus Kern County.

**What did not change.** Nothing found contradicts the four-number plan. The two published methods use exactly our first two clues (steep fall from peak; early bare field).

---

## 9. Search log (abridged)

| # | Language | Query theme | Result |
|---|---|---|---|
| 1 | EN | corn silage / grain classification, Sentinel-2 or Landsat, US fields | Lin 2025 only |
| 2 | ES | maíz forrajero, maíz grano, teledetección, Sentinel | Lagunera 2025 (S1) |
| 3 | PT | milho silagem, milho grão, sensoriamento remoto | nothing |
| 4 | IT | mais da trinciato / silomais / mais ceroso, telerilevamento | nothing |
| 5 | EN | silage harvest detection, Wisconsin / New York / Pennsylvania / Idaho, thesis | NY yield work only |
| 6 | EN | Tulare / San Joaquin Valley, corn silage, double crop, remote sensing | CalAg page (U4) |
| 7 | EN | NASS Research and Development Division, silage, CDL | nothing |
| 8 | EN | silage versus grain harvest date, Sentinel-1 / HLS, US | nothing US |
| 9 | PT | IFAP milho silagem código | separate supports, no code |
| 10 | IT | AGEA matrice colture, silomais, mais da granella | codes 1 / 108 |
| 11 | CA | DUN mapa de cultius, blat de moro farratger | product table |
| 12 | EN | EuroCrops HCAT green_silo_maize, Portugal / Spain / Italy | mapping files |
| 13 | EN | silage maize / grain maize, Po Valley, Lombardy, double crop | Zenodo record (I2) |
| 14 | IT | Lombardia geoportale uso agricolo SIARL, mais ceroso | SIARL legend |
| 15 | ES | FEGA catálogo productos, maíz forrajero, aprovechamiento | SIEX catalogue exists; site down |
| 16 | ES | Galicia / Lleida / Cantabria, maíz forrajero, Sentinel | nothing for Spain |
| 17 | EN | corn silage versus corn grain, time series, distinguish | nothing US |
| 18 | EN | Kern County crop boundaries, CORN FOR/FOD | service found |
| 19 | EN | FSA crop acreage data, intended use, silage | handbooks only |
| 20-21 | ZH | 乌兰布和, 青贮玉米, 遥感, 农业机械学报 | title in the 2025 issue 5 contents only |
| 22 | EN | "Ulan Buh", silage maize, Transactions of the CSAM | nothing |
| 23 | EN | Salehi Shahrabi 2020 | abstract records |
| 24 | EN | DPR commodity codes, corn forage fodder | code list |
| 25 | EN | thesis, corn silage harvest, Landsat / PlanetScope | nothing |
| 26 | PT | silagem, milho, Sentinel-2, mapeamento, bacia leiteira | nothing |
| 27 | IT | insilato / trinciato, data di raccolta, telerilevamento | nothing |
| 28 | EN | Wisconsin dairy rotation, cash grain, CDL | WI DNR (U3) |
| 29 | EN | NHPI harvest index, silage | NHPI page (U7) |
| 30 | EN | California county permit crop boundaries, other counties | Stanislaus lead |
| 31 | EN | corn silage, crop residue, NDTI, US | nothing on silage |
| 32 | ES | SIEX destino del producto, ensilado | not confirmed |
| 33 | FR | Quebec BDPPAD, maïs-grain, maïs ensilage | guide (already in labels.md) |
| 34 | EN | Statistical Reporting Service / NASS, Landsat, corn for silage | NASA Harvest letter (U2) |
| 35 | EN | San Joaquin Valley, winter forage, triticale, two peaks | nothing dairy-specific |
| 36 | EN | "mapping silage corn", "silage corn fields", US | nothing |
| 37 | IT | AVEPA / AGREA / ARTEA piani colturali open data | Tuscany lead |
| 38 | ES | SIAP, maíz forrajero, imágenes satelitales, tesis | Lagunera again |
| 39 | EN | Wiscland 2 rotation classes, user guide | service description only |
| 40 | FA | Persian title of Salehi Shahrabi | nothing |
| 41 | EN | "Automatic silage maize detection ..." abstract, accuracy, study area | abstract listing |
| 42 | EN | silage, Tulare County, SPGH, kappa | kappa values listing |
| 43 | EN | FSA Crop Acreage Data 2026 file, intended use | FSA site not reachable |
| 44 | PT | IFAP ocupação cultural, milho silagem, Portaria 54-Q/2023 | no code list |
| 45 | EN | silage / grain, CDL "does not distinguish", dairy counties | nothing |

## 10. Sources that could not be opened

- https://www.tandfonline.com/doi/abs/10.1080/01431161.2020.1779377 - HTTP 403 (closed access)
- https://www.mdpi.com/2073-4395/15/6/1438 and its PDF link - HTTP 403
- https://doaj.org/article/588b9bec09f54a89a665031dc59ab6b6 - HTTP 403
- https://www.j-csam.org/html/2025/5/20250535.html - socket hang up
- http://www.kernag.com/gis/gis-data.asp - connection reset (the map service itself was opened)
- https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex - connection refused
- https://www.fsa.usda.gov/... crop acreage data (three URLs) - timeouts
- https://www.ifap.pt/portal/en/superficies-pagamento-milho-silagem-regras - navigation menu only
- https://files.dre.pt/1s/2023/02/04101/0042300449.pdf - downloaded, text not extractable
- https://www.agroportal.pt/alteracoes-portarias-pedido-unico-de-2026/ - HTTP 403
- https://www.bandi.regione.lombardia.it/... Codici_coltura_ammissibili - HTTP 502
- https://static.regione.marche.it/... TABELLA TEMPI_LAVORO AGRICOLO - certificate error
- Stanislaus County Agricultural Commissioner open data hub, ARTEA open data, Wiscland 2 user guide - seen in search listings only
