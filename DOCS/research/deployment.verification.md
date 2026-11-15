# Verification: deployment paths at USDA, buy-in, landscape and cost

Checked 2026-11-14 by an independent fact-checker. Every primary source below was opened and read directly (PDF text extracted locally; figures rendered and read; inventory CSVs parsed). WebSearch was unavailable (session search budget exhausted), so nothing here rests on search snippets, and no extra searching for counter-evidence was possible.

## Verdicts

| ID | Status | What was checked | Note |
|---|---|---|---|
| deployment-1 | confirmed | Boryan et al. 2011, Geocarto Int. 26(5), 341-358 (full text + Figure 5) | All quotes verbatim. 2007 first in-season use (13 states, 9 crops, October report). r2 = 0.959 is for one stratum only (Nebraska 2009, stratum 11, >80% cultivated). The paper describes 2009 practice; the CDL FAQ confirms internal estimates are still regression, not pixel counts. |
| deployment-2 | confirmed | NASS cranqm26.pdf, released 4 Feb 2026, pages 6-7 | Every number matches: sample 73,133 (2025; 73,269 in 2024), response 46.0% to 40.2%, all eleven CVs. Wording caveat: the imprecision is in western states. Wisconsin (2.9%) and New York (5.0%) are dairy states with moderate CVs. Arizona was 18.5% in 2024, so state CVs swing year to year. |
| deployment-3 | confirmed | Same document, pages 1 and 4 | All four quotes and the timeline are verbatim. The document also names FSA certified acreage as "the most common administrative data". |
| deployment-4 | confirmed | OMB M-25-21 (3 April 2025), sections 2(b)(i), 3(b)(iii), 4(a), footnote 22, section 5 | Quotes and section numbers correct. Two softeners: the "less data, less compute" line is a "should aim to", not a mandate; the pilot exemption also needs Chief AI Officer certification, central tracking and opt-out where possible. |
| deployment-5 | corrected | 2024 consolidated CSV (both versions) and the 2025 inventory CSV, parsed locally | 2024 facts are right (USDA 89, NASS 10, CDL 2008 with ATO, RMA wording verbatim), but 1,757 rows is a superseded file: the 2024 total is 2,133. A 2025 inventory now exists (see corrected claim). RMA tools were never operational. |
| deployment-6 | confirmed | CDL FAQ; NASA Earthdata and JPL OPERA pages; CTIC OpTIS; Planet Planetary Variables page | CDL codes, no silage class, 27 Feb 2026 release, OPERA 30 m, OpTIS 2015-2021 aggregated, Planet quote: all verified. Not verified: the three-year OPERA baseline (not on pages opened) and the five vendor negatives (not re-opened). Planet also sells a 3 m version. |
| deployment-7 | confirmed | Hanuschak and Mueller, Pecora 15 (text + Figures 2-4); OPM 2026 DC pay table | 750K, 150K, 75K and the 50K/10K/8K split all verified (split is from Figure 4 and sums to 68K, not 75K). The 750K included research costs. GS-13 step 5 = 138,024 dollars confirmed. The compute model is the team's own estimate; its arithmetic is consistent. |
| deployment-8 | confirmed | CSB 2025 metadata; CDL FAQ; Boryan 2011; NASS confidentiality pledge page | All quotes verbatim: 15,973,106 polygons, no PII, public domain, FSA CLU not shared outside NASS, 5 years or 250,000 dollars, single-farm counties combined. The statute protecting FSA data itself is not cited (see missed item 3). |

## Corrected claim

**deployment-5.** USDA lists satellite classifiers in its AI inventory in two governance classes, and the newest inventory keeps the split. In the 2025 Federal Agency AI Use Case Inventory (as of 13 April 2026: 3,611 use cases, USDA 162, 4 USDA high-impact), NASS's Cropland Data Layer is "Not High-impact", deployed, with an authority to operate; Predictive CDL and county corn and soybean yield are also "Not High-impact". RMA's Cover Crop Mapping, Planting Date Detection, and Acreage and Crop Type Validation are "High-impact" and still pre-deployment. In the 2024 inventory (2,133 use cases in the final version, USDA 89, NASS 10) the same tools were "Neither" and "Rights-Impacting" respectively.

## Missed by the researcher

1. **A newer inventory exists.** The 2025 Federal Agency AI Use Case Inventory was published in April 2026 under M-25-21's "high-impact" label. Cite it instead of the 2024 file. It also lists a new pre-deployment USDA use case, "Farm Services Agency (FSA) Acreage Coverage Evaluation". https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory
2. **A second OMB memo covers the LLM part.** M-26-04 (11 December 2025), "Increasing Public Trust in Artificial Intelligence Through Unbiased AI Principles", applies to any LLM an agency procures. The LLM memo component falls under it, not only M-25-21. https://www.whitehouse.gov/wp-content/uploads/2025/12/M-26-04-Increasing-Public-Trust-in-Artificial-Intelligence-Through-Unbiased-AI-Principles-1.pdf
3. **The statute that protects FSA data is 7 U.S.C. 8791** (2008 Farm Bill section 1619). It bars USDA and its cooperators from disclosing producer-provided and related geospatial information, with an exception for statistical or aggregate form. The findings cite only the NASS statutes (7 U.S.C. 2276 and CIPSEA). https://www.law.cornell.edu/uscode/text/7/8791
4. **The real competitor is administrative data, not only the survey.** NASS's own methodology names FSA certified acreage as its most common administrative source, and RMA publishes county Type/Practice/Unit Structure files for 1999-2027. Whether those files carry a corn silage type could not be checked (the RMA file host was unreachable), so confirm before claiming no other source separates silage from grain. https://www.rma.usda.gov/tools-reports/summary-of-business/state-county-crop-summary-business

## Overall

Seven of eight findings hold exactly as stated, with every quoted number and passage found in the primary source. The one correction is a stale edition (the 2024 AI inventory has been superseded by a 2025 one that says the same thing in new labels). The weakest parts are the "no product exists" negative in deployment-6, which rests on vendor pages that were not re-opened, and the team's own compute cost model, which is an estimate rather than a sourced fact.
