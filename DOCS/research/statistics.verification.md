# Verification: statistics findings

Checked 2026-11-14 by an independent fact-checker. Every source was opened; PDFs were text-extracted and the numbers searched directly.

Access notes: `esmis.nal.usda.gov` did not resolve from this machine, so the two NASS Crop Production reports were read from the NASS mirror `release.nass.usda.gov/reports/` (same files). Web search was unavailable (budget exhausted), so all checks are direct page fetches.

## Verdicts

| ID | Status | Note | URL checked |
|---|---|---|---|
| statistics-1 | confirmed | All four FAQ quotes verified verbatim; FAQ also says pixel counts are "raw numbers needing bias correction". Code table lists Corn (1), Sweet Corn (12), Pop or Orn Corn (13), no silage class. Arithmetic checks out; with revised 2025 acres it is 10.12M vs 6.187M, still +64%. | https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php |
| statistics-2 | confirmed | Every number verified in v1 (578, 100, 0.86 to 0.21, n=1,386, 1.9x, 1.8x, about 2.4x, 3,382) and unchanged in v7. The "true" 0.35 is CDL treated as truth (simulation). v7 renames the Olofsson method the "post-stratified estimator". | https://arxiv.org/pdf/2407.13659v1 |
| statistics-4 | confirmed | Table 1 verified: 10% gives 14.7% (EM) and 18.1% (confusion matrix); 90% gives 85.6% and 80.9%; ten replications, 1,000-case test sets, at most 5 EM steps; three assumptions as stated. The team's own start-value simulation was not checkable. | https://dipot.ulb.ac.be/dspace/bitstream/2013/68391/1/Decaestecker_NeuralComp02.pdf |
| statistics-5 | confirmed | 52,641 parcels, 16,964 fields, +0.003 to +0.097 (mean 0.034), 2.8% to 42.2% (mean 21.9%), Kenya 6.6/28.4/42.7% and 0.55 to 0.65 all verified. Paper writes the model as a_r + b_k. Gains are versus unadjusted transfer; versus prior-shift only they are -0.002 to +0.083. | https://arxiv.org/pdf/2109.01246 |
| statistics-6 | confirmed | Verified: RMSE 2.7%, 90% level 4.6%, average 260, smallest 13, largest 813 million bushels, below 8, above 12; soybeans 4.2% and 7.3%; 2026 silage cells blank. The September report was reissued 23 Oct 2026 with corn corrections; reliability figures are the same. | https://release.nass.usda.gov/reports/crop0926.txt |
| statistics-8 | corrected | January 2026 figures verified as quoted, but NASS has since revised 2025. The 10 Nov 2026 Crop Production shows planted 98,713, grain 90,948, silage 6,187. | https://release.nass.usda.gov/reports/cropan26.txt and https://release.nass.usda.gov/reports/crop1126.txt |
| statistics-11 | confirmed | All five quotes verified verbatim on the scikit-learn 1.9.1 page, section 1.16 (1.16.2, 1.16.3.1, 1.16.3.2 and the intro note). | https://scikit-learn.org/stable/modules/calibration.html |
| statistics-12 | confirmed | Wisconsin: 32%, last week 14%, five-year average 21%, nine districts 17% (NC) to 43% (SW). National 11 Oct: 33% vs 39%; TX 89, KS 63, WI 16, IA 14; no silage line; "non-probability", "approximately 3,600 respondents", "subjectively estimate". "No precedent" search claim not checkable. | https://www.wispolitics.com/wp-content/uploads/WI-Crop-Progress-09-14-26.pdf and https://release.nass.usda.gov/reports/prog4126.txt |

## Corrected claim for statistics-8

US corn silage acreage moved 0 to 4% a year over the last two transitions, so carrying last year's number forward is a strong national baseline; a satellite method must show skill at state or county level and in year-to-year change.

- Harvested for silage, thousand acres: 6,461 (2023), 6,207 (2024), 6,187 (2025, revised; originally 6,208 in January 2026).
- Persistence error: +4.1% for 2024 and +0.3% for 2025 against the revised figure (it was -0.02% against the original).
- 2025 revised: planted 98,713, harvested for grain 90,948, so 1,578 thousand acres were neither grain nor silage (it was 1,322 before revision).
- Silage share of grain plus silage: 6.95% (2023) to 6.37% (2025), unchanged by the revision.
- California 2025 (January 2026 state table, not re-published since): 420 planted, 50 grain, 365 silage.

## What the research missed

1. **2025 corn figures were revised.** The November 2026 Crop Production (released 10 Nov 2026) lists 2025 silage at 6,187 thousand acres and 135,090 thousand tons, with planted 98,713 and grain 90,948. Quoting 6,208 to NASS staff would be quoting a superseded number. https://release.nass.usda.gov/reports/crop1126.txt
2. **NASS publishes an acreage reliability figure, and it has no silage row.** The September table covers production only. The June 2026 Acreage report gives corn planted RMSE 1.4% (90% level 2.5%; average difference 1,045 thousand acres, range 144 to 3,585; below final 6 years, above 14). The November 1 corn production RMSE is 1.3% (2.3%). https://release.nass.usda.gov/reports/acrg0626.txt
3. **The cited Lu et al. version is two years old.** v7 (3 July 2025) is retitled "Regression coefficient estimation from remote sensing maps", adds Dan Kluger as author, moves area estimation to Appendix F, calls the Olofsson method the "post-stratified estimator", and proves in Section F.3 that it and PPI give similar intervals. Numbers are unchanged. https://arxiv.org/abs/2407.13659
4. **Saerens EM needs calibrated probabilities, and its likelihood is concave.** Alexandari, Kundaje and Shrikumar (ICML 2020) show EM with bias-corrected calibration beats BBSL and RLLS, and prove the objective is concave, which is the published reason the result does not depend on the starting value. https://arxiv.org/abs/1901.06852

## Overall

All eight sources exist and say what the findings attribute to them; every quoted number was matched against the source text. The one substantive problem is that the 2025 national corn figures in statistics-8 (and reused in the statistics-1 arithmetic) were revised by NASS after January 2026, so the current official 2025 silage figure is 6,187, not 6,208 thousand acres. Conclusions are unaffected, but the revised numbers and the newer Lu et al. version should be the ones presented.
