# Verification: Model choice (interpretable models, small-label classifiers, foundation embeddings)

Checked 2026-11-14 by an independent fact-checker. Every cited URL was opened directly unless noted.
Web search budget was exhausted during this pass, so negative claims ("no study found", "the only study") could not be re-tested by search.

## Verdict table

| ID | Status | What was checked | Note |
|---|---|---|---|
| models-1 | corrected (minor) | https://library.kab.ac.ug/Record/doaj-art-588b9bec09f54a89a665031dc59ab6b6/Description (MDPI full text still HTTP 403) | All numbers match the abstract. The accuracies are for a three-class map (silage maize, grain maize, other land cover), not a binary silage-vs-grain test. "Only study" not re-tested. Indices and thresholds remain unverified. |
| models-2 | confirmed | https://github.com/interpretml/interpret and https://interpret.ml/docs/python/api/ExplainableBoostingClassifier.html | Table and monotonize quote match exactly. Caveats: table is published by the EBM developers; Adult gap between LR and XGBoost is exactly 0.020; these are large datasets, not a few-hundred-label regime. |
| models-3 | confirmed | https://arxiv.org/html/2604.27195v2, https://www.nature.com/articles/s41586-024-08328-6, https://github.com/PriorLabs/TabPFN | All numbers match. Study: TADPOLE, 530 subjects (371 train / 159 test), TabPFN V2 API family. Whether the N=50 XGBoost was tuned is not stated. p-values 0.114 (LR), 0.618 (RF), 0.660 (tuned XGBoost), 0.716 (LightGBM). |
| models-4 | confirmed | https://scikit-learn.org/stable/modules/calibration.html (scikit-learn 1.9.1) | All four quotes are verbatim. "Wrong choice" is the researcher's reading; the guide says isotonic matches or beats sigmoid only above about 1000 samples. The same page also documents method="temperature" (one parameter). |
| models-5 | confirmed | https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL, https://github.com/ucam-eo/geotessera, https://arxiv.org/abs/2601.00857 | Catalog range, 10 m, 64 bands, GeoTessera 2017-2025 and the Lobell abstract quote all match. Nuances: each year is many tiles, not one image; the benchmark tested yield, tillage and cover crop, not crop type. |
| models-6 | confirmed | https://arxiv.org/html/2608.30392v1 | Table 3 matches every number. Transformer is "trained from scratch"; TabPFN has "no geospatial or agricultural pretraining". Outside the three tasks cited, fine-tuned CropFM was best on YieldSAT Argentina (R2 0.33 vs TabPFN 0.31). |
| models-7 | corrected | https://arxiv.org/html/2610.36857, https://arxiv.org/abs/2610.08810 | Numbers match, but the headline is too broad. Within the US (leave-one-region-out) embeddings beat engineered features, 0.34 vs 0.22-0.27. Harmonic features win only on US-India transfer, three shared classes. Prithvi drop is attributed to phenology-window mismatch. |
| models-8 | confirmed | https://arxiv.org/html/2308.08387v2, https://www.nass.usda.gov/research-and-science/cropland/metadata/metadata-cdl25-fgdc-std-001-1998 | Formula, 25% example, bias quote and adjusted count all match. NASS quote is verbatim in the 2025 CDL metadata. The 8.2% and 75% arithmetic is correct; the 6.4% and 88% input shares were not checked here. |

## Corrected claims

**models-1.** The only published study found on this class pair (Lin et al., Agronomy 15(6):1438, 2025, China) used a decision-rule model on harvest-period temporal differences of Whittaker-smoothed Sentinel-2 data. In a three-class map (silage maize, grain maize, other land cover) it reached overall accuracy 0.9291 (kappa 0.8923) against 0.9043 (0.8511) for a random forest; silage user's accuracy 0.9216, producer's 0.94, F1 0.9307. The same rules gave overall accuracy 0.8621 for 2022 and 0.8816 for 2021. Only the abstract was read, so the indices and thresholds are unverified.

**models-7.** Within-region cross-validation grossly overstates crop-classification skill: AlphaEarth macro F1 was 0.82-0.93 under 10 km spatial block cross-validation in three US counties (Fresno, Bolivar, Finney) but 0.34 under leave-one-region-out across five US counties (Goyal et al., 2017-2023). Under that US leave-one-region-out test the embeddings still beat engineered features (0.34 vs 0.22-0.27). Harmonic features transferred better only across continents, on three shared classes: US-to-India 0.493 vs 0.326, India-to-US 0.389 vs 0.198. The Prithvi crop model fell from mean overall accuracy 0.65 (US) to 0.40 (Europe), with calibration error rising in 7 of 8 paired events; the authors attribute this mainly to observation windows misaligned with local phenology.

## Missed or backwards

1. **Embeddings beat engineered features for transfer inside the US.** Goyal et al. report a 26-55% relative improvement for AlphaEarth over spectral, NDVI and harmonic features under US leave-one-region-out, consistent across six classifiers. The "harmonic transfers better" result is cross-continental only. For a US-only challenge the models-7 headline points the wrong way. https://arxiv.org/html/2610.36857
2. **TabPFN has moved on from the version tested.** The repository default is now TabPFN-3.5 (up to 1,000,000 rows and 20,000 features; 5,000-sample default cap on CPU). The Nature limits (10,000 samples, 500 features) and the independent clinical study both describe v2. Weights for 2.5, 2.6, 3 and 3.5 are non-commercial and need a login or TABPFN_TOKEN. https://github.com/PriorLabs/TabPFN
3. **Adjusted count is unbiased only if tpr and fpr are the same in the target population as in the labeled set** (prior probability shift), and its variance grows when tpr and fpr are close or are estimated from few labels. Rates measured on a few hundred fields in one region may not hold in another state. https://arxiv.org/html/2308.08387v2
4. **The AlphaEarth benchmark cited for weaknesses also reports strengths.** Ma, Shen, Swatantran and Lobell found AlphaEarth models "competitive with purpose-built RS-based models" for yield prediction and county-level tillage mapping when trained on local data. It did not test crop-type or harvest-type classification, so it is indirect evidence either way. https://arxiv.org/abs/2601.00857

## Overall

Every cited source exists and every number that could be checked matches its source; no fabricated citations were found. Two findings need rewording before presentation: models-1 reports three-class accuracies, and models-7 overstates the case against embeddings, since inside the US they transferred better than engineered features. Claims that rest on "no study found" were not re-tested because the search budget ran out.
