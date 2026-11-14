# Verification: data_access (checked 2026-11-14)

Independent re-check of the eight data_access findings. Every source was opened or re-queried live; the NASS accuracy workbooks were downloaded and re-parsed. WebSearch was unavailable (session budget exhausted), so all checks are direct fetches of the cited sources.

| ID | Status | Note | URL checked |
|----|--------|------|-------------|
| data_access-1 | confirmed | Tiers page gives the April 27, 2026 start, 150 / 1,000 / 100,000 EECU-hours, billing account without charge, batch plus online counting, restricted mode. Usage page gives 40 concurrent, 100 req/s, 10 MB, 100 MiB, 3,000 tasks. The five-minute limit is on the Processing Environments page. | https://developers.google.com/earth-engine/guides/noncommercial_tiers |
| data_access-2 | confirmed | All end dates reproduced from the catalog pages: S2 SR, S1 GRD, OPERA RTC, Dynamic World and Cloud Score+ to 2026-11-14, gridMET 11-11, Landsat 9 11-12, HLS L30/S30 11-05. CDL and AlphaEarth intervals end 2025-01-01; AlphaEarth page says "available from 2017 to 2024". | https://developers.google.com/earth-engine/datasets/catalog/USDA_NASS_CDL |
| data_access-3 | confirmed | FAQ quotes, release dates (crop years 2016-2025: Jan 26 to Feb 27) and national 75.4% / 0.712 kappa all present. Release page lists 2025_10m_cdls.zip 9.8 GB and 2025_30m_cdls.zip 1.9 GB. "No 2026 mask before early 2027" is an inference, not a NASS statement. | https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php |
| data_access-4 | confirmed | Re-parsed CA workbook: class 1 reference 2,280; double-crop 3,180 (58.2%); union 4,798 correct of 5,460 reference and 5,399 mapped (87.9 / 88.9%). Class-1-only count is 2,124, not 2,122 (still 38.9%). Class 241 is empty in California. | https://www.nass.usda.gov/sites/default/files/Research_and_Science/Cropland/docs/CDL_2025_accuracy_assessments.zip |
| data_access-5 | confirmed | All six state pairs and national 92.2 / 91.2% (999,320 pixels) match the Summary Table sheets. The Grass/Pasture counts (PA 1,830 of 9,792; NY 1,700 of 9,843) use the six-class corn union; class 1 alone is PA 1,624 of 8,832 (18.4%). | https://www.nass.usda.gov/sites/default/files/Research_and_Science/Cropland/docs/CDL_2025_accuracy_assessments.zip |
| data_access-6 | corrected | Site figures reproduce (E. Wisconsin 7 scenes, S1C track 19, 24-day gap Sep 8 to Oct 2; Minnesota 10; Iowa 14; Lancaster 16). "More than tenfold" is not supported: 7 versus 39-52 scenes, 7 versus 23-30 dates. Iowa had one 12-day gap. | ASF search API (URL in finding, plus other points) |
| data_access-7 | corrected | All numbers reproduce (13 items; S2A 2, S2B 5, S2C 6; six scenes 77-98% cloud Sep 12-20; 4 under 20%). But the point lies in the overlap of orbits R069 and R112; one orbit alone gave 6-7 acquisitions, about every 5 days. | Planetary Computer STAC search (URL in finding) |
| data_access-8 | corrected | Collection metadata confirmed (westeurope, usda-cdl to 2021, gridmet to 2020, requires_account true on sentinel-1-rtc). But an anonymous SAS token read Sentinel-1 RTC COGs today (HTTP 206, valid TIFF header). Latest CONUS S2 item is 2026-11-13. | https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc |

## Corrected claims

- **data_access-6**: Sentinel-1 revisit in fall 2025 differed roughly four- to sevenfold between silage regions: every 1-6 days in the San Joaquin Valley (S1A + S1C, up to 3 tracks), 5-7 days in Iowa and Pennsylvania (Iowa with one 12-day gap, Aug 20 to Sep 1), and a single 12-day S1C track in eastern Wisconsin with no acquisition from Sep 8 to Oct 2. Fall 2026 differs: Sentinel-1D has replaced Sentinel-1A.
- **data_access-7**: At a central Iowa point covered by two overlapping orbits, three Sentinel-2 satellites gave 13 acquisitions in 30 days (Sep 5 to Oct 5, 2025), yet six consecutive ones (Sep 12-20) were more than 75% cloudy. Sentinel-2A supplied only 2 of the 13; a single-orbit location gets roughly 5-day sampling.
- **data_access-8**: The Planetary Computer STAC API and SAS token signing still work with no account, and Sentinel-2 L2A is current to 2026-11-13. Storage is in Azure West Europe, its CDL ends 2021 and its gridMET ends 2020. Sentinel-1 RTC is flagged "requires account" in metadata, but anonymous tokens read RTC assets on 2026-11-14.

## Missed or backwards

1. **Sentinel-1D replaced Sentinel-1A in 2026**, so the fall 2025 gap pattern does not carry over. Fall 2026 (Aug 15 to Nov 14): central Iowa and Lancaster are on S1D; central Minnesota is now 16 scenes with a 7-day maximum gap; eastern Wisconsin is still S1C every 12 days. Source: same ASF search API with 2026 dates.
2. **Planetary Computer Sentinel-1 RTC works anonymously today** and is current to 2026-11-14 (11 items over central Iowa since Sep 1, 6 over eastern Wisconsin). This is terrain-corrected gamma0 without an Earth Engine quota. Source: https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc
3. **The HLS stop at 2026-11-05 is upstream at NASA, not an Earth Engine ingestion lag.** NASA CMR returns no HLSS30 or HLSL30 granule over the Midwest after Nov 5, and Planetary Computer HLS over central Iowa ends Oct 25. Switching HLS provider will not help. Source: https://cmr.earthdata.nasa.gov/search/granules.json?short_name=HLSS30&version=2.0
4. **NASS Crop Sequence Boundaries 2018-2025 (released March 27, 2026)** is a national field-polygon product (NationalCSB_2018-2025_rev23.zip) carrying CDL crop per year. It is the obvious polygon source for 10^4-10^5 fields and is absent from these findings. Source: https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php

## Overall

The findings are well sourced: every cited source exists and every number that could be recomputed was reproduced, including the workbook-derived accuracy figures. Three need rewording before presentation: the "more than tenfold" Sentinel-1 ratio, the general "two-to-three-day" Sentinel-2 cadence, and the claim that Planetary Computer Sentinel-1 RTC needs an account.
