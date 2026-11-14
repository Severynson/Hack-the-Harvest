# Verification: Direct precedent (silage vs grain maize by remote sensing)

Checked 2026-11-14 by an independent fact-checker. Every cited source was opened and read (PDF full text for Lin, Blickensdörfer, Shang, Khabbazan, d'Andrimont, AAFC spec; HTML for Meroni and CDL metadata; OpenAlex abstract for Salehi Shahrabi).

Limit: the session's web-search budget was already spent, so no new literature search was possible. Negative claims ("only one study", "unused for classification", "no agency work found") are therefore not independently tested.

## Verdicts

| ID | Status | Note | URL checked |
|---|---|---|---|
| precedent-1 | confirmed | All numbers, thresholds and the "5-15 day" quote match the full text (Tables 2, 4, 5). "Only one study" could not be re-searched; the authors themselves call silage-specific research "limited". | https://mdpi-res.com/d_attachment/agronomy/agronomy-15-01438/article_deploy/agronomy-15-01438.pdf?version=1749740666 |
| precedent-2 | confirmed | Table 6 and Discussion match. Arithmetic checks: 94/100, 118/131, 142/150, 354/381; 102 points predicted silage, so 8 false positives. In-sample scoring is an inference, but a sound one. Adjusted 2021/2022 thresholds and sample sizes are not published. | same PDF |
| precedent-3 | confirmed | Quote and rule match Section 3.2.2 and Table 2. Caveat: the importance ranking comes from a three-class forest (silage, grain, non-maize) and is shown only as a figure, so it does not isolate silage versus grain. | same PDF |
| precedent-4 | confirmed | All figures match. Caveat: 13,111 and 2,104 km2 are parcel-declaration areas for the five states with reference data, not national totals. Grain maize over-estimation "confirmed for all states" is the paper's wording. | https://literatur.thuenen.de/digbib_extern/dn064297.pdf |
| precedent-5 | confirmed | Table values match: 541 polygons, +18.6 days, MAE 25.5, r 0.52; BBCH 83 (+6.5 d) and BBCH 99 (-1.2 d). 562 maize polygons in total, 541 with both retrievals. "Unused for classification" not re-searched. | https://pmc.ncbi.nlm.nih.gov/articles/PMC7841528/ |
| precedent-6 | confirmed | Abstract supports every stated item, including kappas and Marvdasht as training site. Abstract says "maize and other crops" and never mentions grain maize. Full text still unread; thresholds unknown. | https://api.openalex.org/works/doi:10.1080/01431161.2020.1779377 |
| precedent-7 | corrected | Counts and rule are right, but the 77 harvest fields contain no corn. Table 1: oats 23, barley 12, canola 5, soybean 8, spring wheat 22, peas 7. Corn is only named as a regional crop. Khabbazan quote confirmed. | https://mdpi-res.com/d_attachment/remotesensing/remotesensing-12-01551/article_deploy/remotesensing-12-01551.pdf |
| precedent-8 | confirmed | CDL codes and corn 92.2% / 91.2% match (table is headed "statewide" in the national file). AAFC Corn 147 and 85% target match. JRC maize 216, PA 84.0, UA 58.5, January to July match. Agency negatives not re-searched. | https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_CDL25_FGDC-STD-001-1998.htm |

## Corrected claim for precedent-7

Sentinel-1 harvest dating is weaker than our plan assumes, but the main evidence is not from maize. An AAFC rule on coherence and VH found the correct 12-day window for 56% of 77 fields (43 correct, 25 within one cycle, 9 failed) in northern Ontario in 2019. Those fields were oats, barley, canola, soybean, spring wheat and peas; none was corn. The maize-specific evidence is Khabbazan et al. 2019: elevated autumn soil moisture hides the maize harvest drop in backscatter. The same paper says harvest is more readily identified with coherence.

## Missed or backwards

1. The "rule beats random forest" comparison in Lin et al. is not like-for-like. The forest was scored on a 30% hold-out (0.9043 = 104/115 points, 28 silage) and the rule on all 381 points. The 2.5-point gap is within sampling noise. Labels also came partly from visual reading of the same Sentinel-2 harvest signal, so validation is partly circular.
   https://mdpi-res.com/d_attachment/agronomy/agronomy-15-01438/article_deploy/agronomy-15-01438.pdf?version=1749740666
2. Do not present "5-15 days" as the harvest gap. The same paper says silage was fully cut by 10 September 2023 and grain is cut late September to early October, a gap of several weeks. 5-15 days matches the growth-cycle difference (116 versus 120-130 days).
   Same PDF, Sections 2.2 and 3.1.1.
3. Labelled parcels for both uses exist well beyond Germany. The EuroCrops crop taxonomy for EU farmer declarations has separate classes green_silo_maize (3301090400) and grain_maize_corn_popcorn (3301010600).
   https://raw.githubusercontent.com/maja601/EuroCrops/main/hcat_core/HCAT3.csv
4. Eurostat reports the two uses separately: C1500 "Grain maize and corn-cob-mix" and G3000 "Green maize". The JRC map folds both into class 216 (Supplementary Table S17), so the single class is a legend choice and official silage area figures exist to compare against.
   https://arxiv.org/pdf/2105.09261

## Not verified

- FSA crop acreage (form 578) data, which may record intended use (grain or silage) for corn: the FSA page timed out twice, so this lead is unconfirmed.
