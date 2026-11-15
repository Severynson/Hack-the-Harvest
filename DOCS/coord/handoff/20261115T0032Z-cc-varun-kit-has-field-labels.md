# Handoff to cc-daniel: the organizer kit has field labels, and the scoring year is 2025

From cc-varun, 2026-11-15. Details are in `DOCS/research/data_sources.md`, section 0.

## State
- `DOCS/research/usda_reps_qa.md` (yours) says no field-level truth was given. The starter kit contradicts it: `04_Evaluation/BARC_Corn.2021-2023.gpkg` has 44 labeled field-years in Maryland (32 grain, 12 silage; 2021 to 2023). The challenge statement asks for a confusion matrix and precision and recall for both classes on them.
- The organizers posted the acreage scoring table: 2025 state totals for grain and silage (`https://quickstats.nass.usda.gov/results/ACC45317-B978-3390-B0A1-BE0EC02A9D63`). So 2025 is the scored year and must stay out of fitting.
- The kit's Quick Stats file also holds NASS's June acreage and August to November forecast rows for 2012 to 2025.
- All training runs on Keeboh; the workspace holds 10 GB and the submission is a copy of it.

## Next step
- Please correct the "no field-level truth" lines in `usda_reps_qa.md` and the USDA requirements section, or tell me to.
- The lab already has a `Kernel/` folder with a notebook and results on the Maryland fields. If that is yours, say which version is current.

## Risks
- The Maryland labels are one farm; 12 silage field-years is a test set only.
