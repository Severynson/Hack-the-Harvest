# Verification: Public labels and statistical proxies (silage vs grain truth)

Checked 2026-11-14 by an independent fact-check pass. Every source file was downloaded and read directly (shapefile attribute tables, RMA pipe-delimited files, FSA workbook, NASS PDFs). Web search was unavailable (budget used up), so all checks were direct fetches of the cited or official URLs.

## Verdict table

| ID | Status | What was checked | Note |
|---|---|---|---|
| labels-1 | confirmed | BDPPAD_V03_2026.zip and _2025.zip attribute tables; Données Québec catalogue | 2026: 370,322 parcels; MGR 42,726 / 305,784 ha; MAF 11,102 / 65,561 ha (17.65%); codes MFO 7,916 + MFE 3,186. 2025: 39,822 and 11,144. Medians 4.6 / 4.5 ha; 80.5% >= 2 ha. Zip 170,454,098 bytes, modified 9 Nov 2026. Licence CC-BY 4.0 per Données Québec. |
| labels-2 | confirmed | bdppad-v03-guide-utilisateur.pdf (March 2025) | All three quotes are verbatim (sections 1.2, 1.4.2, 1.4.5). The 2010 exclusion covers clients insured only for hay or forage maize on a feed-need basis. 122,308 no-crop parcels in 2026 confirmed. |
| labels-3 | confirmed | sobtpu_2026.zip (8,959,529 bytes, modified 9 Nov 2026) | Grain 87,015,856; Silage 1,242,857 acres in 481 counties, 34 states. 2025: 1,200,580 in 476 counties. Top five states match exactly. |
| labels-4 | corrected | sobtpu_2025/2026; NASS Crop Production 2025 Summary | Ratios hold: 1,200,580 / 6,208,000 = 19.3%; California 94,883 / 365,000 = 26%. IL, NE, KS, MO, KY are zero in both years. Iowa figure is mislabelled: 11,246 in 11 counties is 2026; 2025 is 12,594 in 10 counties. |
| labels-5 | confirmed | rcceqm26.pdf (released 5 June 2026) | 31 / 6 states; silage 204 (2024) and 180 (2025); grain 1,296 and 1,238; median silage harvested CV 2.0% (2025; 1.4% in 2024); CAPS response 39.1% (2025). Counts include "Other Counties" rows. |
| labels-6 | confirmed | WI reports of 14, 21, 28 Sep; 5, 19, 26 Oct; 2, 9 Nov 2026 | Silage 32 / 54 / 75 / 87%; grain 8 / 16 / 24%; 85% dented and 38% mature on 20 Sep; districts 32% (NC) to 65% (SW). Later grain: 42 / 61 / 72%, so medians are about 5.5 weeks apart. |
| labels-7 | confirmed | WI report of 5 Oct 2026 (rendered page); FSA crop acreage page; rfsa data-raw readMe | Special Note exists (it is an image, so text search misses it). FSA lists 2025 releases of 1 Aug, 12 Sep, 9 Dec and 12 Jan 2026 only. The rfsa statement is in data-raw/fsaCropAcreage/readMe.txt, not the main README. |
| labels-8 | corrected | FSA crop acreage page and the 10 Nov 2026 workbook | FSA site opens with a browser user agent. A newer release (10 Nov 2026) exists. Corn has Intended Use = "Silage": 2,885,863 planted acres, 1,409 counties, 47 states; Grain 91,165,479. |

## Corrected claims

**labels-4.** RMA silage-type acres are a floor, not a total. In 2025 they were 1,200,580 acres against 6,208,000 NASS silage acres harvested (19%), and 94,883 against 365,000 in California (26%). Illinois, Nebraska, Kansas, Missouri and Kentucky show zero silage-type acres in both 2025 and 2026, although NASS reports 90,000, 210,000, 230,000, 80,000 and 70,000 silage acres there for 2025. Iowa had 12,594 acres in 10 counties in 2025 and 11,246 in 11 counties in 2026.

**labels-8.** FSA's public county Crop Acreage Data has an Intended Use column, and corn rows carry an explicit "Silage" value for 2026. The latest release is dated 10 November 2026 (data as of 5 November), after the 12 August, 11 September and 9 October releases. It reports 2,885,863 planted acres of corn for silage in 1,409 counties and 47 states, against 91,165,479 acres for grain. That is 2.3 times the RMA silage-type acreage and covers states where RMA shows none (Nebraska 29,518; Iowa 27,698; Kentucky 24,145; Missouri 9,134; Kansas 6,176; Illinois 5,501).

## Missed or understated

1. **FSA is the widest public county proxy for 2026, not RMA.** The 10 November 2026 FSA release has corn silage in 1,409 counties (RMA: 481). It is still a floor: 2,885,863 acres is under half of NASS's roughly 6.2 million. Wisconsin 429,690; New York 495,735; California 282,473. Source: https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/frequently-requested/crop-acreage-data
2. **NASS publishes state-level corn silage for 48 states**, which is the benchmark that sizes the RMA and FSA gaps. Wisconsin 885,000 acres in 2025 against 193,376 RMA silage-type acres (22%). The NASS California overview now shows 370,000 for 2025, not 365,000. Sources: https://esmis.nal.usda.gov/sites/default/release-files/795725/cropan26.txt and https://www.nass.usda.gov/Quick_Stats/Ag_Overview/stateOverview.php?state=CALIFORNIA
3. **2025 is only partly lost for timing.** The 21 September 2026 Wisconsin report still carries a last-year silage value (38% on 20 September 2025), so the 2025 silage curve through late September exists. The Special Note also says five-year averages use imputed 2025 values, so the averages printed in October and November 2026 are not pure survey data. Source: https://www.nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2026/WI-Crop-Progress-10-05-26.pdf
4. **BDPPAD maize counts exclude multi-crop parcels.** In 2026 the MUL group holds another 1,311 parcels with MGR, 476 with MFO and 211 with MFE, with no location inside the parcel. MFE means "maïs fourrager option superficie", an insurance option rather than an agronomic class, and the 2026 file is still revised weekly. Source: https://www.fadq.qc.ca/fileadmin/geo4tb/BDPPAD/BDPPAD_V03_2026.zip

## Overall

Highly trustworthy: every number in the eight findings reproduced exactly from the primary files, and all quoted text was found verbatim. Two findings need edits before presenting: the Iowa figure in labels-4 is the 2026 value, and labels-8 is out of date, because the FSA site is reachable and its 10 November 2026 release confirms an explicit corn "Silage" intended use.
