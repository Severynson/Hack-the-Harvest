# nass_ops: independent verification

Checked 2026-11-14 against the primary USDA files. Every number below was read from the source text, not from the research notes.

| ID | Status | Note | URL checked |
|---|---|---|---|
| nass_ops-1 | confirmed | Nov 10, 2026 report: silage 6,187K for 2025, 2026 cell blank. California sits in "Other States"; state estimates deferred to the Crop Production 2026 Summary. CDL FAQ gives Feb 27, 2026. Calendar shows corn county estimates May 5, 2026. | https://release.nass.usda.gov/reports/crop1126.txt |
| nass_ops-2 | confirmed | 15,893,419 thousand bu, 179.6 bu/ac, down 1.6 from 181.2; 88,506K harvested unchanged from October; planted 96,777K. WASDE-677 matches (16,034 to 15,893; stocks 1,849 to 1,758; $4.70 to $4.60). Exact NASS difference is 140.5M bu; 141 is the WASDE-rounded figure. | https://release.nass.usda.gov/reports/crop1126.txt ; https://www.usda.gov/oce/commodity/wasde/wasde1126.txt |
| nass_ops-3 | confirmed | Nov 14, 2025: 98,728 / 90,047 / 186.0 / 16,752,193. Jan 2026: 98,788 / 91,258 / 186.5 / 17,020,549; silage 6,208K, 21.8 t/ac, 135,540K tons. Differences 1,211K acres and 268.4M bu; acreage share 84%. June 2025 Acreage report: 86,774K. | https://release.nass.usda.gov/reports/cropan26.txt ; https://release.nass.usda.gov/reports/crop1125.txt |
| nass_ops-5 | confirmed | US sample and rate match in four editions: 2020 73,135 / 55.7; 2021 72,603 / 50.1; 2022 72,615 / 48.3; 2023 72,239 / 45.8; 2024 73,269 / 46.0; 2025 73,133 / 40.2. Six state rates match. farmdoc 2017 says 80-85% in the early 1990s. | https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02_2026/cranqm26.pdf |
| nass_ops-6 | corrected | All CVs match the table. The headline overreaches: the largest silage states by acres are close to Corn Belt precision (Wisconsin 1.9 / 2.9, South Dakota 0.8 / 1.1). The 17 to 77 times gap against Iowa holds for western states where silage dominates planted corn. | https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02_2026/cranqm26.pdf |
| nass_ops-7 | confirmed | Satellite wording is in the Aug 12, Oct 9 and Nov 10, 2026 reports; absent from July 10, 2026 and Nov 14, 2025. The revision-policy sentence, including "remote sensing data", is unchanged from Nov 2025, so only the estimating-procedures paragraph is new. | https://release.nass.usda.gov/reports/crop0826.txt ; https://release.nass.usda.gov/reports/crop1125.txt |
| nass_ops-8 | confirmed | Recomputed from Track Records: silage min 5,567K (2010), max 7,419K (2012), mean 6,302K, population SD 401K. Share changes 2002 -3.62, 2012 -2.23, 2022 -1.70; mean absolute 0.68 points. Nov to Jan mean absolute 431K, max 1,637K (2022). | https://release.nass.usda.gov/reports/croptr26.txt |
| nass_ops-9 | confirmed | State table matches all ten leaders and all six listed changes. Recomputed gross change: 469K up, 468K down. California 420 / 50 / 365 / 27.0. "Moved between states" means offsetting state changes, not tracked acres. National total since revised to 6,187K. | https://release.nass.usda.gov/reports/cropan26.txt |

## Corrected claim

**nass_ops-6:** NASS's survey precision on the grain share of planted corn (CV of the harvested-for-grain to planted ratio, December Agricultural Survey) is 17 to 77 times worse than Iowa's 0.5 percent in western states where silage dominates planted corn: California 30.8 / 23.3, Arizona 18.5 / 38.3, Idaho 8.6 / 18.5, New Mexico 13.3 / 18.2, Utah 11.3 / 14.1, Washington 11.2 / 11.8 (2024 / 2025). It is not much worse in the states with the most silage acres: Wisconsin 1.9 / 2.9, South Dakota 0.8 / 1.1, New York 13.4 / 5.0. US 0.3 / 0.3.

## Missed or needs care

1. **Precision problem is not where the silage acres are.** Three of the four leading silage states have 2025 CVs of 1.1 to 5.0 percent. The large CVs sit in states with tiny grain acreage (California 50K, Arizona 16K). https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02_2026/cranqm26.pdf
2. **The price forecast fell with the production cut.** WASDE-677 lowered the 2026/27 farm price 10 cents to $4.60 while cutting production 141M bu; feed and residual and exports were each cut 25M bu. Do not present the cut as price-supportive. https://www.usda.gov/oce/commodity/wasde/wasde1126.txt
3. **Revision policy is not new in 2026.** The Nov 14, 2025 report already carried the same sentence on remote sensing data and month-to-month harvested-acre revisions. Only the estimating-procedures paragraph changed in August 2026. https://release.nass.usda.gov/reports/crop1125.txt
4. **A 141M bu move is an ordinary November miss.** The Nov 10, 2026 reliability table puts the 20-year average November-to-final difference at 144M bu (range 4M to 420M), with November above final in 13 of 20 years. https://release.nass.usda.gov/reports/crop1126.txt

## Not verified

- The FSA Crop Acreage Data page timed out three times, so whether the public FSA-578 files split corn by intended use (grain versus silage) remains open. That would be an in-season public silage signal ahead of January.
- The date of the Crop Production 2026 Summary in January 2027: the 2027 calendar page returned no entries.
- The web search budget for this session was exhausted; all checks were direct fetches of the cited files.
