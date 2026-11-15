# Verification: Nowcasting (current-year corn mask, earliness vs accuracy, real-time simulation)

Checked 2026-11-14 by an independent fact-checker. Every cited URL was opened; PDF tables were read from the downloaded files. Web search was unavailable (session budget used up), so all checks are direct fetches of primary sources.

## Verdict table

| ID | Status | What was checked | Note |
|---|---|---|---|
| nowcast-1 | confirmed | CDL FAQ, CDL release page, Earth Engine USDA/NASS/CDL | FAQ: "The 2025 CDL product was released February 27, 2026"; 2023 released Jan 31, 2024. Release page (modified 06/12/2026) has 10 m national CDL for 2024 and 2025 only. 2025 accuracy 75.4%, kappa 0.712. Earth Engine ends 2025-01-01 (latest layer 2024). "No in-season layer" rests on absence, not an explicit FAQ statement. |
| nowcast-2 | confirmed | crop1126.txt, NASS calendar Jan 2026 and Jan 2027 | Corn for silage 2025 = 6,187K, 2026 blank ("estimation period has not yet begun"). Planted (all purposes) 96,777K, grain 88,506K. Annual Summary Jan 12, 2026, 12:00 ET. January 2027 calendar page lists no reports. Lead times recomputed and correct. |
| nowcast-3 | corrected | WI reports of Sep 30 2024, Oct 15 2024, Sep 29 2025, Oct 5 2026; MN Oct 15 2024; NY Oct 13 and Oct 27 2024 | Two Wisconsin 2024 values are wrong. Original reports give 49% on Sep 22 and 67% on Sep 29, 2024 (not 45% and 64%; 64% is the "last year" column, i.e. 2023). Everything else matches. 50% falls about Sep 22-23, not Sep 24. |
| nowcast-4 | confirmed | prog4526.txt, prog4625.txt | 18 states 81% (74% prior week, average 86%). Iowa 72, Nebraska 74, South Dakota 68, Wisconsin 72, Michigan 61, Ohio 69, Pennsylvania 67, Texas 99. Nov 16, 2025 = 91% (Nebraska 74); Nov 16, 2024 = 98%. |
| nowcast-5 | corrected | WI Oct 5 2026 PDF (full text extracted), WI Oct 13 2026, WI Nov 18 2025, WI index, prog4026, prog4526, prog4625, prog4725 | The gap is real: "last year" columns are (NA) and the Wisconsin index has no links from Oct 6 to Nov 10, 2025. The quoted "special note" and the phrase "imputed estimates for 2025" were not found in the cited PDF or in any of the seven other reports checked. Do not quote them. |
| nowcast-6 | corrected | cropan26.txt acreage plus the progress reports above | Recomputed with the correct 67% for Sep 29, 2024: week ending Oct 6 silage share is 39% (95K vs 148K acres), not 44% (117K); grain share of acres cut by Sep 29 is 23%, not 24%. The other figures hold: 16%, 2.6%, 19.9%, 11.0%. Conclusion unchanged. |
| nowcast-7 | confirmed | cropan26.txt, crop1126.txt | US silage 6,207K (2024), 6,208K (2025). Sum of absolute state changes recomputed from all 48 rows = 937K = 15.1%. State changes match. Revised 2025: 6,187K silage, 90,948K grain (was 91,258K). |
| nowcast-10 | confirmed | SentiWiki S1 mission, Earthdata HLS page, Earth Engine HLSS30, S1_GRD, S2_SR_HARMONIZED | All quotes and dates match. HLS S30 on Earth Engine ends 2026-11-05; S1 GRD and S2 SR run to 2026-11-14. OPERA RTC latency not checked. |

## Corrected claims

**nowcast-3.** Silage chopping finishes by mid-October in the Upper Midwest and about two weeks later in New York. Wisconsin silage harvested in 2024: 49% Sep 22, 67% Sep 29, 80% Oct 6, 92% Oct 13. In 2025: 41% Sep 21, 66% Sep 28. In 2026: 87% Oct 4. Wisconsin grain 2024: 2% Sep 22, 5% Sep 29, 10% Oct 6, 26% Oct 13. Minnesota silage 98% on Oct 13, 2024. New York silage 73% Oct 13 and 90% Oct 27, 2024 (5-year average 83% on Oct 27). Interpolated Wisconsin 2024: 50% about Sep 22-23, 90% about Oct 12.

**nowcast-5.** The 2025 replay has no official weekly harvest progress for October. NASS published no Crop Progress for the weeks ending Oct 5 through Nov 9, 2025: the Wisconsin index shows no report links from Oct 6 to Nov 10, 2025, the Nov 17, 2025 national report prints Nov 9, 2025 as (NA), and every 2026 report prints the "last year" column as (NA). The cause (the federal funding lapse) and any imputation of 2025 into 5-year averages should be stated as the team's understanding, not as a quotation, because the quoted note could not be found.

**nowcast-6.** Inference unchanged: cut date alone cannot separate the classes in early October, and "still standing means grain" is safe in Wisconsin but not in New York. Wisconsin 2024 (730K silage, 2,960K grain acres): of acres cut in the week ending Oct 6, 39% were silage (95K vs 148K); week ending Oct 13, 16%; by Sep 29, 23% of acres already cut were grain. P(silage given standing): Wisconsin 2.6% on Oct 13, 2024; New York 19.9% on Oct 13 and 11.0% on Oct 27, 2024.

## Things the researcher missed

1. **"Last year" columns are not the prior year's published values.** The Sep 29, 2025 Wisconsin report gives 64% silage for last year, while the Sep 30, 2024 report published 67% for Sep 29, 2024. Take each year's numbers from that year's own reports. This is the likely origin of the wrong 64%.
   https://nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2024/WI-Crop-Progress-09-30-24.pdf
2. **Sentinel-1A is scheduled to retire at the end of June 2026.** SentiWiki says "Sentinel-1A end of operations is planned for end of June 2026", so fall 2026 radar is 1C plus 1D, while the fall 2025 replay had 1A plus 1C (1D launched Nov 4, 2025). Orbit geometry and revisit differ between the replay year and the live year.
   https://sentiwiki.copernicus.eu/web/s1-mission
3. **The CDL has no silage class, and since 2024 it is built with an Earth Engine random forest.** The FAQ lists Corn (1), Sweet Corn (12) and Pop or Orn Corn (13) only, and notes that 2024 and newer CDLs use a Google Earth Engine random forest classifier. A current-year corn mask built the same way is methodologically close to what NASS does.
   https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php
4. **2026 silage harvest ran ahead of normal in Wisconsin.** 87% on Oct 4 against a 77% average, and 95% on Oct 11 against 88%. Timing thresholds tuned on 2024 or 2025 will be about a week late for 2026.
   https://nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2026/WI-Crop-Progress-10-13-26.pdf

## Overall

The national and annual figures are reliable: every number from the Annual Summary, the November 2026 Crop Production, the Crop Progress tables, the CDL pages and the satellite latency sources matched the primary source. Two Wisconsin 2024 weekly values were wrong (49% and 67%, not 45% and 64%), which shifts two derived shares in nowcast-6 without changing its conclusion. The verbatim funding-lapse quotation in nowcast-5 could not be found anywhere and should not be presented as a quote, although the reporting gap itself is real.
