# Verification: stakeholders (who gains what from an earlier, explainable silage-versus-grain estimate)

Checked 2026-11-14 by an independent fact-check pass. Every cited URL was opened; PDFs were text-extracted locally.
Web search was unavailable (session budget exhausted), so all checks are direct fetches of primary sources.

## Headline

All eight sources exist and say what the researcher quoted. The one systematic problem: the 2025 figures in
stakeholders-3 and stakeholders-4 come from the January 2026 Annual Summary, but NASS revised 2025 corn and
silage on 30 September 2026 (Grain Stocks). The researcher's own stakeholders-1 already quotes the revised US
total (6,187), so the findings mix two vintages. Use the revised numbers below in front of NASS.

## Verdict table

| ID | Status | What was checked | Note |
|---|---|---|---|
| stakeholders-1 | corrected (wording) | crop1126.txt, cropan26.txt, CDL FAQ, WI Crop Progress 5 Oct 2026 | All numbers confirmed (approved 12 Jan 2026; DAS about 73,100 operators; 2025 silage 6,187 / 135,090; 2026 cells blank; CDL 27 Feb 2026). But NASS does publish in-season silage harvest progress at state level (Wisconsin: 87% complete, 5 Oct 2026). Say "no in-season silage acreage, yield or production estimate". |
| stakeholders-2 | confirmed | crop1126.txt, Statistical Methodology | Both quotes are verbatim, including "remote sensing data" for planted-acre revisions. The text is generic to field-crop forecasts, not silage-specific. |
| stakeholders-3 | corrected | cropan26.txt; grst0926.txt (revised 2025) | January figures match, but 2025 was revised 30 Sep 2026: US 6,187; Texas 245 (+53%, not +66%); Nebraska 220. Revised persistence error is 864 thousand acres (14.0%), not 937 (15.1%). 2024 figure of 766 (12.3%) reproduces. |
| stakeholders-4 | corrected | cropan26.txt; grst0926.txt; crop1126.txt | Revised 2025: California 370/450 = 82% (not 87%); New York 51%; Texas 10%; Iowa 1.8%; US 6.3%. Residual 2025 = 98,713 - 90,948 - 6,187 = 1,578 thousand, not 1,322. Range becomes 1.6 to 1.7 million acres. |
| stakeholders-5 | confirmed | crop1126.txt; WASDE-677 PDF | Planted 96,777, harvested 88,506, yield 179.6, production 15,893 million bu; RMSE 1.3%; average change 144 million bu (4 to 420); above final 13 of 20; WASDE-677 ending stocks 1,758. The 8.27 million acres includes abandonment, not only silage. |
| stakeholders-9 | confirmed | wqo2026-0028.pdf (text extracted) | Adopted 15 Sep 2026; about 1,300 dairies; A/R 1.4, 1.1 for new herd; 13267 orders within two years; GeoTracker; 200 to 275 lb N; 890 lb/acre. "Broad averaging schemes" is the order citing the CVDRMP report. Order never mentions satellite or remote sensing: "customer" is inference. |
| stakeholders-12 | confirmed | LII 7 USC 8791 and 2276; CDL FAQ; CSB page; ctic.org/optis; agdatatransparent.com | Statute text, penalty, CDL quote, CSB and OpTIS statements all verified; principles 2014, updated 2024. Caveat: 8791 covers producer-provided and linked USDA geospatial data (FSA 578/CLU labels), not classifications from public imagery. |
| stakeholders-13 | corrected | CDL FAQ | Five double-crop corn classes, not four: 241 Dbl Crop Corn/Soybeans was omitted. No silage class: confirmed. Release dates range from first week of January (2010 CDL) to 27 Feb (2024, 2025 CDLs). 10 m from 2024 and "85% to 95%" confirmed. |

## Corrected numbers to use

Revised 2025 corn for silage, thousand acres (Grain Stocks, 30 Sep 2026), against 2024:

| State | 2024 | 2025 January | 2025 revised | Change 2024 to revised 2025 |
|---|---|---|---|---|
| United States | 6,207 | 6,208 | 6,187 | -0.3% |
| Wisconsin | 730 | 885 | 885 | +21% |
| Texas | 160 | 265 | 245 | +53% |
| Iowa | 340 | 250 | 250 | -26% |
| North Dakota | 260 | 170 | 170 | -35% |
| Kansas | 310 | 230 | 230 | -26% |
| Nebraska | 280 | 210 | 220 | -21% |
| California | 380 | 365 | 370 | -3% |
| New York | 455 | 500 | 495 | +9% |

Fifteen states were revised (also Arizona, Indiana, Kentucky, Michigan, Mississippi, Missouri, New Jersey, Oregon,
Utah, Virginia, Washington).

Persistence ("same as last year") error, sum of absolute state changes:

- 2023 to 2024: 766 thousand acres, 12.3% of the US total (reproduced)
- 2024 to 2025, January vintage: 937 thousand, 15.1% (reproduced)
- 2024 to 2025, revised vintage: 864 thousand, 14.0% (use this one)

Revised 2025 US corn: planted 98,713; harvested for grain 90,948; silage 6,187; residual 1,578 thousand acres.

## What the researcher missed

1. NASS revised 2025 corn and silage on 30 Sep 2026. The January-to-September revision itself moved 15 state
   silage figures by up to 20 thousand acres each, which is a direct measure of how uncertain the December
   survey number is. https://release.nass.usda.gov/reports/grst0926.txt
2. NASS state offices publish weekly corn silage harvest progress in season (Wisconsin, 5 Oct 2026: 87%
   complete against a 77% average). It is a free timing signal and weakens "nothing in season".
   https://www.nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2026/WI-Crop-Progress-10-05-26.pdf
3. CDL class 241 (Dbl Crop Corn/Soybeans) is a fifth double-crop corn class; a corn mask built from the four
   listed classes will drop those pixels. The same FAQ reports 2025 overall crop accuracy of 75.4%.
   https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php
4. The California order relies entirely on dairy-reported data in GeoTracker and never mentions satellite or
   remote sensing, and its "broad averaging" criticism is quoted from the CVDRMP monitoring report. The Water
   Board is a plausible user, not a declared one.
   https://www.waterboards.ca.gov/board_decisions/adopted_orders/water_quality/2026/wqo2026-0028.pdf

## Not verified

- FSA Crop Acreage Data page timed out on three attempts, so whether the public file splits corn by intended
  use (grain versus silage) is unchecked.
- The order number "WQ 2026-0028" appears in the URL file name; the cover-page text did not extract, so the
  number was not read from the document body.
