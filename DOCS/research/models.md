# Model choice for Kernel: interpretable models, small-label time-series classifiers, foundation embeddings

Research agent: `models` | Date: Saturday 2026-11-14 | Scope: which model family to build, which to run only as ablations, and how to prove to NASS statisticians that the simple model is enough.

Method: 30 web searches, about 70 page fetches. Every number below comes from a page that was opened in this session unless it is marked "not opened". Statements that are my own reasoning are prefixed "Inference:". Section 9 lists what could not be opened.

---

## 0. Bottom line

1. **Ship a two-layer transparent model on the four physical features**: a two-question rule (depth-2 tree) for the slide, and a monotone additive model (logistic scorecard or EBM without interactions) for the probabilities. There is direct precedent on this exact task: a published threshold decision tree on harvest-window temporal differences beat a random forest for silage vs grain maize (OA 0.9291 vs 0.9043) and transferred to two other years (0.8621, 0.8816).
2. **Demote XGBoost from "the model" to "one of the challengers"**. On small tabular data the stronger challenger is TabPFN, and the literature says the realistic outcome is a statistical tie. Use the GPU to try to beat the simple model, and report that it did not (or by how little).
3. **Run one foundation-embedding ablation, not a foundation model**: field-mean AlphaEarth 2025 (64-d) or TESSERA 2025 (128-d) plus logistic regression. Both are annual calendar-year products, so a 2026 vector cannot exist before the year ends (the 2025 AlphaEarth layer appears to have been published around March 2026; announcement not opened). That single fact is the strongest argument for our physics features.
4. **Replace isotonic calibration with sigmoid (Platt) or none**, and compute conformal bands from out-of-fold scores per class. scikit-learn's own guidance is that isotonic overfits below about 1000 samples.
5. **Do not "classify and count" when rolling up to county and state**. Use the adjusted count (tpr/fpr corrected) or the probability-sum version, then show the reconciliation factor against NASS. NASS's own CDL metadata says its acreage estimates "are not simple pixel counting but regression estimates".
6. **Evaluate with grouped (leave-one-region-out) folds and bootstrap intervals**. A 2026 AlphaEarth crop study shows the gap: macro F1 0.82-0.93 under block CV, 0.34 under leave-one-region-out.

---

## 1. What this means for Kernel

### 1.1 What the evidence supports in plan v2

| Plan v2 element | Verdict | Evidence |
|---|---|---|
| Four measured physical numbers per field | Keep. This is the core. | Rudin 2019: for structured data with meaningful features there is "often no significant difference in performance between more complex classifiers" and simpler ones. TempDiff-SMID 2025: harvest-timing decision rules beat RF on silage vs grain maize. |
| Transparent two-question rule | Keep, and make it the headline model. | CORELS: rule lists "approximately as accurate as the COMPAS proprietary risk prediction tool". NASS built the CDL with a See5 decision tree from 2007 to 2023. |
| Cut date in GDD and relative to county median | Keep. It is also the defence against the main foundation-model failure mode. | Prithvi-EO-2.0 transfer study 2026: mean overall accuracy "declined from 0.65 in the United States to 0.40 in Europe"; the authors attribute much of the decline to misalignment between the observation window and local crop phenology (paraphrase of the abstract). |
| Conformal "needs review" band | Keep, but class-conditional and from out-of-fold scores. | Angelopoulos and Bates: distribution-free, finite-sample guarantee with "any pre-trained model". |
| Reconcile rollups with NASS | Keep, but correct the misclassification bias first and report the raw gap. | Kloos et al.: classify-and-count bias "does not disappear if the number of observations in the test set increases". |

### 1.2 What the evidence contradicts or weakens in plan v2

1. **"GPU XGBoost with isotonic calibration" as the main model.**
   - scikit-learn calibration guide: isotonic "is more prone to overfitting, especially on small datasets" and suits cases with "greater than ~ 1000 samples"; sigmoid "is most effective for small sample sizes". Our labeled set is small.
   - The same guide: "LogisticRegression is more likely to return well calibrated predictions by itself".
   - InterpretML benchmark: logistic regression matches or beats XGBoost on 3 of 5 datasets (Heart .895 vs .851, Breast .995 vs .992, Telecom .849 vs .828) and EBM matches or beats XGBoost on all 5.
   - Inference: with 4 to 8 monotone physical features and a few hundred labels, boosted trees have almost nothing to add, and they cost us the explanation. Keep XGBoost (monotone, depth 2 or less) as a challenger row in the ablation table.
2. **SHAP as the explanation layer.** Our four features are consequences of one event (the harvest), so they are correlated by construction. Kumar et al. (ICML 2020): interventional SHAP "induces an out-of-distribution problem", conditional SHAP "may attribute influence to features with no interventional effect", and with a correlated duplicate feature two audits "would come out with quantitatively different results". Use the model's own additive terms and counterfactual statements instead.
3. **Nemotron "Index Scout" ranking candidate indices on the labeled set.** Inference: ranking many indices against a small labeled set is a multiple-comparison search; statisticians will ask how the winner was selected. Either fix the four features in advance from the agronomic hypothesis and treat Index Scout as exploratory, or nest the index selection inside the cross-validation folds and confirm on a locked holdout.
4. **The autoresearch loop scored against one fixed small evaluation set.** Inference: many agent-edited `train.py` runs against the same `prepare.py` evaluation is adaptive overfitting to that set. Lock a final holdout that the loop never reads, and report the loop's best score only alongside the one-shot holdout score.
5. **Distance to dairy as a model feature.** A 2026 benchmark by Lobell's group found AlphaEarth embeddings have "limited spatial transferability"; a 2026 RSE-track study found embedding transfer US to India dropped to macro F1 0.326 vs 0.493 for harmonic features. Inference: anything that encodes "where" rather than "what happened in the field" transfers poorly and is hard to defend ("you called it silage because a dairy is nearby"). Keep dairy distance as a prior used in reconciliation, or as a tie-breaker reported with and without, never as the reason for a call.
6. **Foundation embeddings as a possible main signal.** AlphaEarth and TESSERA public embeddings are annual calendar-year products. The Earth Engine catalog lists AlphaEarth availability to 2025-01-01, which I read as the 2025 layer being the latest; TESSERA v1.1 covers 2017-2025. No 2026 layer is listed today. Published agricultural evaluations describe the AlphaEarth product as having "limited time sensitivity" and "low interpretability". They are a good retrospective ablation and a poor operational signal for an early estimate.
7. **Vision LLM as a labeler.** GEOBench-VLM: best model 41.7% on multiple-choice questions overall; crop type classification accuracy 0.2182 for the best model and 0.1818 for GPT-4o. Do not use a VLM to produce labels from chips. Use Nemotron to plan, run and narrate, with every stated number coming from the deterministic pipeline.

### 1.3 Candidates for "a new data source or harvest signal" (Innovation criterion)

- **AlphaEarth / TESSERA annual embeddings as a tested and rejected alternative** (new 2025-2026 data sources; we show what they can and cannot do for harvest type).
- **A "cliff score" shapelet**: the distance between a field's z-normalised NDVI (or VH) subseries and a learned "cliff" template. A shapelet is defined as a "subseries of a series in the training data that is useful in discriminating between classes"; the distance to it is one interpretable number per field. Inference: this is the time-series formalisation of the USDA clue "silage falls off a cliff, grain fades out".
- **TabPFN as the small-data ceiling** (a 2025 Nature model with no geospatial pretraining that matched or beat Earth-observation foundation models on agricultural tasks in a 2026 benchmark).
- **Misclassification-corrected acreage** (adjusted count) as the bridge from field calls to NASS-style totals.

---

## 2. Ranked recommendation for the 20-hour build

Ranking criterion: probability of being defensible in front of NASS statisticians, multiplied by the probability of being finished by Sunday 09:00.

| Rank | Component | Role | Effort | Why this rank |
|---|---|---|---|---|
| 1 | **Evaluation harness**: grouped folds (leave-one-state or leave-one-county-cluster out), stratified bootstrap 95% intervals, trivial baselines (always grain, date-only, prior-only), per-class precision / recall / FPR, PR-AUC, Brier, latency | Foundation for every claim | 2 h | Without it no model comparison is credible. "Always grain" scores about 94% accuracy nationally, so accuracy alone must never be shown. |
| 2 | **Two-question rule** (exhaustive search over two-question, three-leaf rules on a threshold grid, objective = balanced accuracy or F1 for silage) | Headline model on the slide | 1 h | Smallest hypothesis space, closed-form counterfactuals, matches NASS's own decision-tree history. Inference: with 4 features and about 20 thresholds each there are roughly 100,000 candidate rules, so exhaustive enumeration takes seconds to minutes and lets us say "the best two-question rule on our data, by exhaustive search". |
| 3 | **Monotone additive probability model**: logistic regression on the 4 features (signs fixed by agronomy), optionally rounded to an integer "Silage Score" card; EBM with `interactions=0` as the non-linear version | Calibrated probabilities for rollup, review band, evidence card | 1.5 h | Well calibrated by default (sklearn), explanation is the model (Rudin), EBM matches XGBoost on InterpretML's benchmark. |
| 4 | **Bias-corrected rollup**: probability sums, adjusted count with out-of-fold tpr/fpr, bootstrap interval, then reconciliation factor against NASS state totals | County and state acres | 1.5 h | This is the part statisticians will probe hardest. |
| 5 | **Class-conditional conformal band** from out-of-fold probabilities | "Needs review" flag with a stated coverage | 0.75 h | Cheap, rigorous, honest about small-n coverage variability. |
| 6 | **Challenger row 1: TabPFN** on the same features (v2 weights) | Black-box ceiling at small n | 0.5 h | Strongest small-n tabular model in the literature; if it does not beat the scorecard, that is the proof. |
| 7 | **Challenger row 2: monotone XGBoost on GPU** (depth 2 or less) | Conventional ceiling, GPU use | 0.5 h | Expected by judges; `monotone_constraints` keeps it sane. |
| 8 | **Challenger row 3: MiniRocket (or MultiRocket-Hydra) + ridge on raw NDVI / NDMI / VH series** | "Did hand features lose information?" | 1 h | State of the art for time-series classification, trains in minutes, no feature engineering. |
| 9 | **Challenger row 4: annual foundation embedding + logistic regression** (AlphaEarth 2025 via Earth Engine, or TESSERA 2025 via `geotessera`) | "Would a foundation model do better?" for the 2025 evaluation year only | 1.5-2 h | Novel, cheap, and its limitations (annual, opaque, weak transfer) make our case. |
| 10 | **Weak-label program** (agronomic labeling functions + label model or majority vote) and **active learning** to pick 30-50 fields for manual labeling | More training signal without touching the evaluation labels | 2 h, only if labels are too few to fit rank 3 | Useful but carries a circularity risk (see 4f). |
| Not recommended | Fine-tuning Prithvi-EO-2.0, Galileo, TerraMind, Clay; Presto unless monthly composites already exist; VLM chip labeling | | 3 h or more each | Patch-based or monthly inputs, heavy, opaque, and published evidence says they do not consistently beat simple supervised baselines on crop tasks. |

Monotone directions to impose (Inference, from the USDA clues in the challenge brief):

| Feature | Definition (ours) | Direction for P(silage) |
|---|---|---|
| Relative cut date R | cut date minus county median cut date, or GDD accumulated at cut | decreasing (later means grain) |
| Green-at-cut G | share of peak NDVI / NDMI still present at the last clear scene before the cut | increasing |
| Dry-down days D | optical browning date to radar cut date | decreasing |
| Residue after harvest T | NDTI (or STI) in the first clear post-harvest scene | decreasing (residue blanket means grain) |
| Double-crop flag | winter forage before corn | increasing (tie-breaker) |
| Dairy distance | km to nearest dairy | decreasing (prior only; report with and without) |

---

## 3. Ablation plan: how to prove the simple model suffices

Decision rule to state on the slide: **"We adopt the simplest model whose performance is inside the 95% bootstrap interval of the best challenger, and which is at least as good under leave-one-region-out."**

| ID | Model / variant | Input | What it tests | Expected outcome (Inference) |
|---|---|---|---|---|
| A0a | Always grain | none | Class-imbalance floor | about 94% accuracy nationally, 0% silage recall |
| A0b | Prior only (county silage share, dairy distance) | geography | How much is geography alone | Decent in dairy counties, fails on transfer |
| A0c | Date-only threshold on raw calendar date | 1 feature | "Early is not silage" trap | Fails in Texas-type regions; motivates GDD / county-relative date |
| A1 | Two-question rule | 4 features | Headline | Within a few points of everything below |
| A2 | Monotone logistic scorecard | 4 features | Calibrated simple model | Best or tied on Brier |
| A3 | EBM `interactions=0`, then with pairs | 4-8 features | Does non-linearity or interaction matter | Marginal gain, if any |
| A4 | Monotone XGBoost depth 2 or less (GPU) | 4-8 features | Conventional black box | Tie |
| A5 | TabPFN (v2 weights) | 4-8 features | Best small-n black box | Tie or +1-2 points AUC |
| A6 | MiniRocket + ridge; DTW or TWDTW 1-NN to class prototypes | raw series (NDVI, NDMI, VH, VH/VV) | Did the 4 numbers lose information | Tie in-region, worse on transfer |
| A7 | AlphaEarth 2025 64-d and/or TESSERA 2025 128-d field mean + logistic regression | annual embedding | Foundation model alternative | Competitive in-region for 2025, weak on transfer, unavailable for 2026 |
| A8 | Leave-one-feature-out; add dairy distance; add rotation flag | 3-6 features | Which clue carries the signal | Green-at-cut and dry-down dominate |
| A9 | Label-efficiency curve: n = 20, 50, 100, all (10 repeated grouped subsamples each) | A1, A2, A5 | How few labels are enough | Simple models flatten early |
| A10 | Train Midwest, test California, and the reverse | A1, A2, A5, A7 | Transfer and prevalence flip | Simple physics transfers; embeddings and priors do not |
| A11 | No calibration vs sigmoid vs isotonic; reliability diagram, Brier, ECE | A2, A4, A5 | Calibration choice | Sigmoid or none wins at small n |
| A12 | Rollup: classify-and-count vs probability sum vs adjusted count vs reconciled | field calls | Acreage bias | Classify-and-count overstates silage in grain states and understates it in California |

Reporting template for each row: precision, recall, false positive rate for the silage class; PR-AUC; balanced accuracy; Brier; state-level silage acreage error against NASS 2025; fit time and per-field prediction latency ("Response Time" in the rubric). All with 95% bootstrap intervals and both random-fold and leave-one-region-out numbers side by side.

Paired comparison: bootstrap the difference in the metric between two models over fields (same resamples for both), or McNemar's test on the paired errors. Inference: with a few hundred labels, differences below about 3-5 points will not be significant; say so.

---

## 4. Evidence by topic

### 4a. Inherently interpretable models that compete with boosted trees

| Model | What it is | Key evidence (source) | Use for Kernel |
|---|---|---|---|
| Shallow tree / rule list (CART, CORELS) | A few if-then rules | CORELS (JMLR 2018): rule lists with a "certificate of optimality", "produces optimal rule lists on practical problems in seconds", and "approximately as accurate as the COMPAS proprietary risk prediction tool". Rudin 2019: the COMPAS black box is "equally accurate for recidivism prediction as the very simple three rule" model. | Headline rule. |
| Optimal sparse trees (GOSDT) | Provably optimal small trees | GOSDT (ICML 2020): "optimal decision trees over a variety of objectives including F-score, AUC"; addresses "treatment of imbalanced data and fully optimizing over continuous variables"; "speeds up decision tree construction by several orders of magnitude". | Optional. Inference: for a depth-2 tree on 4 features, brute-force enumeration gives the same optimality claim without a new dependency. |
| Risk scores (RiskSLIM, FasterRisk) | "sparse linear models with integer coefficients" | FasterRisk (NeurIPS 2022): "completes within minutes"; returns "a pool of almost-optimal sparse continuous solutions", each turned into an integer score. Search-level only (not opened in the paper body): RiskSLIM timed out at 900 s on models larger than 1-7 features on several datasets. | "Silage Score" index card: add points, read a probability. The pool of near-optimal cards is a ready-made Rashomon argument. |
| EBM / GA2M (InterpretML) | Additive model, one learned curve per feature, optional pairwise terms | InterpretML benchmark (AUROC): Adult LR .907 / RF .903 / XGB .927 / EBM .928; Heart .895 / .890 / .851 / .898; Breast .995 / .992 / .992 / .995; Telecom .849 / .824 / .828 / .852; Credit fraud .979 / .950 / .981 / .981. The README says EBMs are "as accurate as state-of-the-art techniques like random forests and gradient boosted trees". | Non-linear but exactly explainable probability model. Small-n caution: `validation_size=0.15` holdout and `outer_bags=14` eat data; lower `max_bins`, raise `min_samples_leaf`. |
| Monotone-constrained XGBoost / LightGBM | Boosted trees forced to respect signs | XGBoost docs: `monotone_constraints` with 1 / -1 / 0 per feature, or a dict by feature name; with `hist` / `approx`, constraints "may produce unnecessarily shallow trees" (raise `max_bin`). EBM docs: "it is generally recommended to apply monotonic constraints post-fit using the monotonize function", because boosting can route around a constraint through a correlated feature. | Challenger. The EBM warning applies to us: our features are correlated. |
| Logistic regression on physical features | Linear log-odds | sklearn: "LogisticRegression is more likely to return well calibrated predictions by itself". Rudin 2019 App. B: algorithms "tend to perform similarly, with no algorithm clearly dominating the others" on structured data. | Default probability model. |

Rudin 2019 (Nature Machine Intelligence 1:206-215), the statements worth quoting to judges:
- "It is a myth that there is necessarily a trade-off between accuracy and interpretability."
- "Explanations must be wrong. They cannot have perfect fidelity with respect to the original model."
- Rashomon argument: "Because this set of accurate models is large, it often contains at least one model that is interpretable."

When trees and simple models win on tabular data: Grinsztajn, Oyallon, Varoquaux (NeurIPS 2022), 45 datasets: "tree-based models remain state-of-the-art on medium-sized data" (about 10K samples), with a 20,000 compute-hour hyperparameter search. This is the evidence against putting a neural network on our feature table.

### 4b. TabPFN for small-n tabular data

Source facts (Hollmann et al., Nature 637:319-326, January 2025, read via PMC):
- Designed for "datasets with up to 10,000 samples and 500 features", at most 10 classes natively.
- "In 2.8 s, TabPFN outperforms an ensemble of the strongest baselines tuned for 4 h in a classification setting."
- Normalised ROC AUC: default TabPFN 0.939 vs default CatBoost 0.752; tuned 0.952 vs 0.822.
- Data efficiency: "with half the samples TabPFN still performs as well as the next best method using all samples".
- Calibration: a softmax temperature (default T = 0.9) is applied; no calibration metric is reported in the text that was read.
- Limitations stated: "the inference speed of TabPFN may be slower than highly optimized approaches such as CatBoost".
- These benchmarks are by the model's authors.

Independent small-n evidence:

| Study | Setting | Result |
|---|---|---|
| Ye et al. 2026 (arXiv 2604.27195), clinical, 10 stratified subsets per size | N = 50 training subjects | AUC: TabPFN 0.810, logistic regression 0.791, XGBoost 0.776, LightGBM 0.714 |
| same | N = 500 | TabPFN 0.881, XGBoost 0.860; "all models converged toward similar AUC values ranging from 0.860 to 0.881" |
| same | Full test set (371 train / 159 test) | tuned XGBoost 0.887, RF 0.887, LightGBM 0.886, TabPFN 0.879, LR 0.858; no significant AUC differences (p = 0.114 to 0.716) |
| same | Balanced accuracy at the default 0.5 threshold | TabPFN lowest (0.693 vs XGBoost 0.824); rose from 0.69 to 0.80 at a cross-validated threshold of 0.35 |
| KU Leuven DTAI blog, 2026-09-03, football xG | Learning curve | TabPFN "achieves performance comparable to a converged logistic regression model with as few as 400 shots"; "From 100 shots onwards, TabPFN consistently achieves the lowest Brier score" |
| same | Full data | ECE 0.0041 (TabPFN) vs 0.0042 (XGBoost); AUROC 0.7953 vs 0.7899 |
| Nedungadi et al. 2026 (arXiv 2608.30392), agriculture | 7 datasets | TabPFN "matches or outperforms FMs across several datasets" (see 4e) |

Practicalities (TabPFN GitHub README, opened today):
- `pip install tabpfn`, Python 3.10+, "GPU Recommended"; on CPU "only moderate datasets are feasible".
- Default checkpoint is now TabPFN-3.5. Weights for 2.5 and later are under **non-commercial licenses**; TabPFN-2 weights are "Apache 2.0 with an additional attribution requirement". Select with `TABPFN_MODEL_VERSION` (accepts `v2`, `v2.5`, `v2.6`, `v3`, `v3.5`, `v3.5-fast`).
- First use downloads weights and opens a browser login and licence acceptance; headless environments set `TABPFN_TOKEN`. "TabPFN works offline once the weights are downloaded."
- SHAP-based explanations exist in `tabpfn-extensions`.

Inference: TabPFN is a black-box transformer, so it is our accuracy ceiling, not our model. Tune its decision threshold (the clinical study shows the default threshold is poor under imbalance). For a model a federal agency could adopt, pin the v2 weights and say so.

### 4c. Explanation methods and their pitfalls

| Method | What the source says | Consequence for us |
|---|---|---|
| SHAP / Shapley feature importance | Kumar et al. (ICML 2020). Interventional value functions: "The model f has never seen an example like this in training." Conditional value functions: "may attribute influence to features with no interventional effect". Duplicate correlated feature: two audits "would come out with quantitatively different results". Actionability: a large attribution "does not necessarily imply that changing that feature" changes the outcome. The implicit contrast is the average prediction, which "may not be 'expected' by anyone". | Our features are correlated by construction. Do not present SHAP bars as the reason for a field call. If SHAP is shown for the XGBoost challenger, show it next to the additive model's exact terms. |
| Counterfactual explanations | Wachter, Mittelstadt, Russell (Harvard JOLT 2018): "the smallest change to the world that can be made to obtain a desirable outcome"; serves to understand, to contest, and to know what would need to change; works "without needing to explain the internal logic of the system". | For a rule or a logistic model the counterfactual is closed form: "this field would be called grain if it had been cut 12 days later". Put one on every evidence card. |
| Prototype / nearest-neighbour explanations | TWDTW (Belgiu and Csillik 2018) classifies by distance to class temporal patterns; the aeon documentation describes visualisation tools that show the most discriminating shapelet and its best matches per class (paraphrase). | Show the field's NDVI curve over the silage prototype and the grain prototype. A skeptic can see it. |
| Exact additive explanations | InterpretML: EBMs give exact per-feature contributions and can be edited by domain experts; `explain_local`, `explain_global`, `monotonize`, `remove_terms`. | The explanation is the model, so there is no fidelity gap to defend. |

Counterfactual formulas (Inference, standard algebra):
- Logistic scorecard with logit z(x) = b0 + sum_j b_j x_j and decision threshold tau: the change in feature j alone that flips the call is `delta_x_j = (logit(tau) - z(x)) / b_j`.
- Depth-2 rule: the counterfactual is the signed distance to the nearest threshold on the path, for example "green-at-cut 0.71, rule threshold 0.55, so 0.16 less greenness would flip it".
- Constrain counterfactuals to plausible moves (cut date can be later; residue cannot be negative).

### 4d. Time-series classifiers that are strong at small n

| Method | Source facts | Interpretability | Use |
|---|---|---|---|
| ROCKET family: MiniRocket, MultiRocket, Hydra | MiniRocket (KDD 2021): "up to 75 times faster on larger datasets" than ROCKET with "essentially the same accuracy"; trains and tests on all 109 UCR datasets "to state-of-the-art accuracy in less than 10 minutes"; features feed "a linear classifier". Hydra: "can be combined with ROCKET and its variants to further improve the accuracy". Bake-off redux (DMKD 2024, 112 UCR + 30 new datasets): "Hydra+MultiROCKET and HIVE-COTEv2, perform significantly better than other approaches". | Low (thousands of random-kernel features) | Challenger A6: the honest test of whether our 4 numbers lost information. |
| catch22 + linear model | 22 features distilled from 4791 hctsa features on 93 datasets (over 147,000 series): "average reduction in classification accuracy of just 7%" with "approximately 1000-fold reduction in computation time". | Medium (named statistical features, not agronomic) | Optional cheap baseline. Inference: our 4 physical features are a domain-specific "catch-4". |
| DTW-kNN, time-weighted DTW | Belgiu and Csillik (RSE 204:509-523, 2018), Sentinel-2 NDVI, Romania / Italy / USA: object-based TWDTW overall accuracies "ranging between 78.05% and 96.19%"; "comparable classification results to RF in Romania and Italy"; RF better in the USA (California) site, attributed to high intra-class spectral variability; TWDTW less sensitive to the number of training samples. | High (prototype curves) | Prototype view on the evidence card; optional 1-NN challenger. The time weight matters for us: plain DTW would warp an October grain harvest onto a September silage cut and erase the very signal we need. |
| Shapelets | aeon docs: a shapelet is a "subseries of a series in the training data that is useful in discriminating between classes"; the transform uses shapelets "as a way to extract features from time series"; RDST extracts minimum distance, location of best match, and an occurrence count. | High (a shapelet is a picture) | The "cliff" shapelet as a signal. Location of best match is a cut-date estimate; minimum distance is "cliff-likeness". |
| Functional PCA | No source opened in this session. | Medium | Inference: first two principal components of the smoothed NDVI curve are a compact alternative to hand features; not worth the time tonight. |
| Deep time-series models trained from scratch (TempCNN, LSTM, Transformer) | BreizhCrops (about 610k labeled series): RF OA 0.77-0.78 vs Transformer 0.80 on the held-out region. Pelletier et al. 2019 (about 620,000 training instances): RF 90.92 +/- 1.22 vs TempCNN 93.45 +/- 0.77; TempCNNs "outperform RF and RNN algorithms by 1 to 3 %". | Low | Not for us. Even with hundreds of thousands of labels the gain over a random forest is 1-3 points; we have hundreds. |

### 4e. Deep and foundation models for satellite time series

Summary table (all numbers from the cited papers; "authors' own" means not independent):

| Model | Input and size | Published crop / few-label evidence | Availability for our years | Effort for an ablation tonight |
|---|---|---|---|---|
| **AlphaEarth Foundations** (Brown et al., arXiv 2507.22291, Google DeepMind) | 64-d unit-length embedding per 10 m pixel per calendar year; inputs include Sentinel-2, Sentinel-1, Landsat; CC-BY 4.0 | Authors' own: error reduced "~23.9%" on average at max-trial, "~10.4%" at 10-shot, "~4.18%" at 1-shot vs next best; "Other than Ethiopia crops, all thematic mapping evaluations had > 1.0x reductions in error"; evaluated with kNN and linear probes. Independent: see the three rows below this table. | Earth Engine `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL`, catalog availability 2017-01-01 to 2025-01-01. Inference: by catalog convention the end date is the start of the latest annual image, so the 2025 layer exists and there is no 2026 layer. | 1-1.5 h if Earth Engine authentication works in the notebook: `reduceRegions` mean over field polygons, then logistic regression. |
| **TESSERA** (Feng et al., arXiv 2506.20380, Cambridge) | 128-d annual embedding per 10 m pixel from Sentinel-1 (VV, VH) and Sentinel-2 (10 bands); encoder 45.7M parameters per the text (Table 2 says 30.2M) | Authors' own, Austrian crops (17 classes), F1 by label fraction: 1%: TESSERA 66.15, AlphaEarth 37.22, Presto 32.74; 10%: 78.69 / 48.01 / 43.94; 30%: 82.09 / 56.36 / 57.89 | `geotessera`: "wall-to-wall global v1.1 embeddings for every year from 2017 to 2025"; v2 on request with "no guaranteed turnaround time" | 1-2 h: `pip install geotessera`, `GeoTesseraZarr().read_region(bbox, year=2025)`, field mean, logistic regression. Tile sizes not stated. |
| **Presto** (Tseng et al., arXiv 2304.14065) | Pixel time series, monthly timesteps (1 to 24), Sentinel-1/2 + ERA5 + SRTM + Dynamic World; 0.40M parameters; MIT licence; weights in the repo | CropHarvest mean F1: RF 0.441, MOSAIKS-1DR 0.738, TIML 0.802, PrestoR 0.835; mean AUC: RF 0.803, PrestoR 0.917. "fine-tuning Presto took under 6 minutes on a 2017 MacBook Pro's CPU". | Runs on any year we composite ourselves, including 2026 | 2-3 h because monthly composites of all inputs must be built. Monthly steps blur a 3-6 week harvest-timing difference (Inference). |
| **Galileo** (Tseng et al., arXiv 2502.09356, ICML 2025) | Multimodal space-time ViT; Nano 0.8M, Tiny 5.3M, Base 85.0M parameters; 24 monthly timesteps in pretraining | Linear-probe accuracy, pixel time series (Togo / Brazil / Kenya / Breizhcrops): Presto 75.5 / 98.8 / 84.0 / 63.0; AnySat 73.4 / 76.7 / 75.5 / 66.1; Galileo-Base 74.8 / 99.3 / 84.2 / 73.0 | Any year we composite | 3 h or more. Not recommended. |
| **Prithvi-EO-2.0** (Szwarcman et al., arXiv 2412.02732, NASA / IBM) | HLS 30 m multi-temporal chips; pretrained on "4.2 million global time series samples"; temporal and location embeddings | "outperforms the previous Prithvi-EO model by 8%" on GEO-Bench. Independent 2026 transfer study of its crop classifier: OA 0.65 in the US vs 0.40 in Europe; ECE rose in 7 of 8 paired events; 12-51% of affected scenes confidently mislabeled | Any year | Half a day. 30 m chips do not suit field-level harvest type. Not recommended. |
| **TerraMind** (Jakubik et al., arXiv 2504.11171, ICCV 2025) | "any-to-any generative, multimodal foundation model", nine modalities, patch-based | Claims "beyond state-of-the-art performance" on PANGAEA (authors' own) | Any year | Not feasible tonight. |
| **AnySat, Clay** | Patch / multi-resolution encoders | AnySat: see Galileo row. Clay: no source opened. | | Not recommended. |

Independent evaluations of foundation embeddings in agriculture (the ones that matter for our decision):

1. **"Harvesting AlphaEarth" (Ma, Shen, Swatantran, Lobell; arXiv 2601.00857, Dec 2025; abstract and repository README read, full text not opened).** Tasks: US crop yield, tillage mapping, cover-crop mapping. AEF models are "competitive with purpose-built RS-based models in yield prediction and county-level tillage mapping when trained on local data", but show "limited spatial transferability compared to RS-based models, low interpretability, and limited time sensitivity". The authors conclude "These limitations recommend caution when applying AEF embeddings in agriculture". Tillage and cover crop are management practices read from residue and off-season greenness, which is the closest published analogue to harvest type.
2. **"Evaluating AlphaEarth Embeddings for Crop Classification" (Goyal et al., arXiv 2610.36857, Oct 2026; HTML read).** Five US counties 2017-2023 plus northern India.
   - Leave-one-region-out: embeddings macro F1 0.34 vs 0.22-0.27 for engineered features (spectral, NDVI phenology, harmonics).
   - Block CV inside a county: embeddings 0.82 (Fresno), 0.93 (Bolivar), 0.93 (Finney).
   - Cross-continent transfer: US to India macro F1 harmonic features 0.493 vs embeddings 0.326; India to US 0.389 vs 0.198; transfer gaps -0.27 vs -0.50.
   - US maize F1 0.94 with embeddings; in India spectral features beat embeddings for maize (0.93 vs 0.68).
   - Silage and within-crop subclasses are not addressed.
3. **"Foundation Models Meet Agriculture: Challenges Beyond Pretraining" (Nedungadi, Xiong, Russwurm, Athanasiadis; arXiv 2608.30392, Aug 2026; HTML read).** Seven datasets (yield, phenology, crop classification); models: Galileo, CropFM (Presto architecture), TabPFN, Random Forest, LSTM, Transformer from scratch.
   - AlphaEarth and TESSERA were excluded from the benchmark because their precomputed annual embeddings are temporally misaligned with the datasets (paraphrase of the paper).
   - BreizhCrops France F1: Transformer 0.60, LSTM 0.58, CropFM fine-tuned 0.57, Galileo fine-tuned 0.56, TabPFN 0.55, RF 0.50.
   - CropHarvest Kenya F1: Transformer 0.89 +/- 0.04, LSTM 0.85, RF 0.85, TabPFN 0.84, CropFM frozen 0.83, Galileo frozen 0.70.
   - Phenology Germany MAE (days): Transformer 6.71, TabPFN 7.15, LSTM 8.01, Galileo frozen 8.46, CropFM fine-tuned 8.56, RF 10.50; Galileo fine-tuned collapsed to 53.42.
   - Conclusions quoted: "even under full modality coverage, frozen representations do not consistently outperform simple, unconstrained baselines"; "No single model ranks consistently across datasets."
4. **PANGAEA benchmark (arXiv 2412.04204).** Geospatial foundation models "do not consistently outperform supervised models". Crop datasets, mIoU at 100% labels: PASTIS-R best GFM 36.18 vs UNet 31.60 vs ViT from scratch 38.53; South Sudan crop type 54.03 vs 47.57; AI4SmallFarms best GFM 27.19 vs UNet 46.34. At 10% labels GFMs gain ground (South Sudan 38.44 vs UNet 13.88).
5. **Morocco national crop map on AlphaEarth (arXiv 2611.12681, Nov 2026).** On 64-d embeddings, 3 broad classes, test accuracy: MLP 87.17 +/- 0.42, Random Forest 86.88 +/- 0.08, linear probe 86.66 +/- 0.04, SVM 86.08 +/- 0.24. Inference: on these embeddings the classifier choice is irrelevant; a linear probe is enough for our ablation.
6. **California tomato mapping on AlphaEarth (arXiv 2605.21804, May 2026; abstract read).** Tomato vs non-tomato with a U-Net: F1 99.04%, 4,742 fields per class. It separates a crop from other land cover, not a subclass of a crop; no baseline is reported.

Can annual embeddings encode harvest timing or harvest type?
- What sources show: the Earth Engine tutorial says the dataset "captures the crop phenology along with climatic variables"; the model paper says the architecture supports "continuous time" and arbitrary valid periods, but the released product is one vector per calendar year; the Lobell-group benchmark reports "limited time sensitivity".
- What was not found: any evaluation of silage vs grain, harvest date, or any within-crop harvest-practice subclass using AlphaEarth, TESSERA or Presto embeddings.
- Inference: a whole-plant removal in September followed by weeks of bare soil is a large change in the annual trajectory, so some separation in embedding space is plausible in-region. Two caveats: in California the same calendar year also contains the winter forage crop, so the embedding mixes two crops; and the signal would be entangled with region, which is exactly where embeddings transfer worst.

Evidence that simple features plus classical models rival deep models on crop tasks: rows 2, 3, 4 above, BreizhCrops and Pelletier in 4d, and the direct precedent in 4j. Counter-evidence to state honestly: on CropHarvest's cross-region few-shot tasks a random forest on raw monthly inputs is far behind Presto on F1 (0.441 vs 0.835), although its AUC is much closer (0.803 vs 0.917) and its Brazil F1 of 0.000 sits beside an AUC of 0.941. Inference: that pattern is a decision-threshold failure under shift, not an absence of signal, which is one more reason to calibrate and to tune thresholds per region.

### 4f. Semi-supervised, self-supervised and weak-label options

| Option | Source facts | Fit for Kernel |
|---|---|---|
| Weak-label programs (Snorkel) | Ratner et al. (VLDB 2017): users "write labeling functions that express arbitrary heuristics, which can have unknown accuracies and correlations"; the system "denoises their outputs without access to ground truth"; experts "build models 2.8x faster and increase predictive performance an average 45.5%" vs seven hours of hand labeling; "within an average 3.60% of the predictive performance of large hand-curated training sets". | Good fit: USDA's clues are labeling functions. Use the weak labels for training and keep every provided label for evaluation. |
| Self-training | sklearn: works with any classifier with `predict_proba`; adds pseudo-labels above a `threshold` or the `k_best`; "the calibration of the classifier is important". | Use only with the calibrated logistic model, high threshold (0.9 or more), class-balanced additions, a few rounds. |
| Label propagation / spreading | sklearn: assumes "the structure of unlabeled observations is consistent with the class structure"; LabelSpreading is "often more robust to noise"; the RBF kernel builds a dense matrix that "can lead to prohibitively long running times", use the kNN kernel. | Possible on the 4-feature space within a county. Inference: it will mostly reproduce the logistic boundary. |
| Positive-unlabeled learning | Search results only, not opened: PUL-SITS (Remote Sensing 2021) and DOCC (2021) apply PU learning to satellite time series; a 2024 study used harvester GPS tracks as positives and reported F1 94.4%. | Relevant if we can get certain positives only (for example fields adjacent to dairy silage bunkers) and treat the rest as unlabeled. Low confidence. |
| Co-training of optical and SAR views | No source opened. | Inference: our plan already uses SAR for the cut date and optical for greenness and residue, so agreement between the two views is better used as a quality flag ("optical and radar agree on the cut week") than as a training trick. |

Suggested labeling functions (Inference; each returns SILAGE, GRAIN or ABSTAIN):
1. Cut before county median minus k days and green-at-cut above 0.6: SILAGE.
2. Dry-down days above 21: GRAIN.
3. Post-harvest NDTI above the county 60th percentile (residue blanket): GRAIN.
4. Post-harvest bare-soil signature within 10 days of the cut: SILAGE.
5. Winter forage detected before corn (double crop): SILAGE.
6. Dairy within 15 km and county NASS silage share above 30%: SILAGE (weak).
7. County NASS silage share below 2% and no dairy within 50 km: GRAIN (weak).

Circularity warning (Inference): labeling functions built from the same four features that the classifier consumes can only teach the classifier the rules. That is acceptable if we say so, since the trained model is then a smoothed, calibrated version of the agronomic hypothesis, and the provided labels remain the independent test. Report labeling-function coverage, pairwise conflicts, and each function's accuracy on the provided labels.

### 4g. Active learning: which fields to hand-label

Kaijage, Belgiu, Bijker (Sensors 24(7):2108, 2024), Sentinel-2 NDVI series, random forest committee with vote entropy plus a semi-variogram minimum distance (417.6 m and 529 m):

| Site | Strategy | Labeled samples | Overall accuracy |
|---|---|---|---|
| Netherlands | All samples | 350 | 84% |
| Netherlands | Uncertainty-only active learning | 169 | 82% |
| Netherlands | Spatially explicit active learning | 97 | 80% |
| Netherlands | Random | 97 | 70% |
| Belgium | All samples | 560 | 65% |
| Belgium | Uncertainty-only active learning | 327 | 63% |
| Belgium | Spatially explicit active learning | 223 | 60% |
| Belgium | Random | 223 | 54% |

Reading: at an equal budget (97 or 223 labels), choosing uncertain and spatially separated fields gained 10 and 6 points over random choice.

Recipe for tonight (Inference): rank unlabeled fields by margin |p - 0.5| from the logistic model, drop any within about 500 m of an already chosen field, stratify across states and across the "needs review" band, and take 30-50. Label them from the Sentinel-2 time-lapse and public NAIP imagery where available (public data only, per the challenge rules). Keep these labels out of the evaluation set, because they are not a random sample, or weight them.

### 4h. LLM / VLM labeling of remote-sensing chips

GEOBench-VLM (arXiv 2411.19325):
- Best model LLaVA-OneVision reaches "only 41.7% accuracy on MCQs", about double random guessing.
- Crop type classification accuracy: EarthDial 0.2182, GPT-4o 0.1818, LLaVA-OneVision 0.1455, Qwen2-VL 0.1091. "Models struggle with crop classification."
- Land-use classification is better: EarthDial 0.6623, GPT-4o 0.6525.
- Farm pond change detection: 0.1711 to 0.2105 for all models.

Search-level only (not opened): GeoVision Labeler reported best overall accuracy 0.714 for zero-shot land-cover labeling with a vision LLM plus an LLM classifier; a 2025 Gemini 2.5 paper notes a larger zero-shot gap on EuroSAT for classes such as annual vs permanent crop.

Consequences:
- A VLM looking at a 10 m chip cannot tell silage from grain; even crop type is near chance. Do not use VLM calls as labels or as a model input.
- If the team wants a VLM in the loop, treat it as one more labeling function with a measured accuracy on the provided labels, and expect it to be dropped.
- Nemotron's defensible roles: plan and execute the ablation ladder and write the model card from the logged results; draft labeling functions for human review; turn the deterministic counterfactual and the four numbers into the "Harvest Story" sentence; triage the review band. Every number in generated text must be copied from pipeline output, never produced by the LLM.

### 4i. Calibration, conformal bands, and the field-to-county rollup

**Calibration.** scikit-learn guide: sigmoid "is most effective for small sample sizes"; isotonic "is more prone to overfitting, especially on small datasets" and is for "greater than ~ 1000 samples"; "Using the classifier output of training data to fit the calibrator would thus result in a biased calibrator"; "isotonic regression introduces ties in the predicted probabilities" (it can change AUC). Use out-of-fold predictions for calibration.

**Conformal.** Angelopoulos and Bates (arXiv 2107.07511): sets that are "valid in a distribution-free sense" with "explicit, non-asymptotic" guarantees, usable "with any pre-trained model".
- Class-conditional split conformal (Inference, standard construction; only the tutorial's abstract was re-read today): score s = 1 - p_hat(true class); for each class k take the ceil((n_k + 1)(1 - alpha)) / n_k empirical quantile q_k of its calibration scores; the prediction set for a new field is every class k with 1 - p_hat(k) <= q_k. Two labels in the set, or none, means "needs review".
- Small-n honesty (Inference, from memory of the tutorial's coverage-distribution result; verify before quoting): with n_k = 30 calibration fields and alpha = 0.10, realised coverage is distributed roughly Beta(28, 3), mean 0.90, standard deviation about 0.05. Say "about 90%, give or take 5 points, because we had 30 silage labels".
- Exchangeability fails across regions, so compute the band per region or state it as valid only for regions like the calibration fields.

**Rollup: classify-and-count is biased.** Kloos et al. (arXiv 2308.08387):
- Classify and count: alpha_CC = share of fields predicted positive. E[alpha_CC] = alpha * tpr + (1 - alpha) * fpr. It is "rarely unbiased" and "This bias does not disappear if the number of observations in the test set increases."
- Their example: tpr 0.98, fpr 0.03, true prevalence 10%: 125 predicted for 100 true, a 25% overestimate.
- Adjusted count: alpha_AC = (alpha_CC - fpr) / (tpr - fpr); "The Adjusted Count is an unbiased prevalence estimate." Variance = [alpha * tpr * (1 - tpr) + (1 - alpha) * tnr * (1 - tnr)] / [n * (tpr + tnr - 1)^2], large when tpr and fpr are close.

Illustration for our problem (Inference; the tpr and fpr values are hypothetical, the prevalences come from the challenge brief):

| Region | True silage share | Classifier (tpr 0.85, fpr 0.03) classify-and-count | Bias |
|---|---|---|---|
| US total | 6.2 / (6.2 + 91.3) = 6.4% | 0.064 * 0.85 + 0.936 * 0.03 = 8.2% | +29% (about 8.0M acres instead of 6.2M) |
| California | 365 / (365 + 50) = 88% | 0.88 * 0.85 + 0.12 * 0.03 = 75.1% | -15% |

The same classifier over-counts silage where it is rare and under-counts it where it is common. A single national correction factor cannot fix both; the adjusted count does, state by state.

Uncertainty in the correction is dominated by the label count (Inference): with 30 labeled silage fields and an observed recall of 0.85, the Wilson 95% interval for recall is about 0.68 to 0.94. Propagate it by bootstrapping the labeled set and recomputing tpr, fpr and the adjusted acreage each time.

NASS's own practice (2025 CDL metadata): CDL-based acreage estimates "are not simple pixel counting but regression estimates using NASS survey data", described as "an 'Adjusted Census by Satellite'". Our adjusted count followed by reconciliation is the same idea at field level; say this explicitly.

Area-estimation good practice (Olofsson et al. 2014, RSE 148:42-57): not opened in this session; search results describe the recommendation to estimate area from an error matrix in area proportions with confidence intervals. Low confidence, cite only as background.

### 4j. Direct precedent: silage vs grain maize with decision rules

Lin et al., "Silage Maize Identification Using a Temporal Difference-Based Model with Sentinel-2 Data: Insights from a Harvest-Based and Temporally Transferable Approach", Agronomy 15(6):1438, 2025 (abstract read through a library catalogue mirror; the MDPI page returned HTTP 403):
- Method: Sentinel-2 on Google Earth Engine, Whittaker smoothing, harvest-period differences between silage and grain maize, a decision tree with iteratively optimised thresholds (TempDiff-SMID; paraphrase of the abstract). Search snippet (not in the mirror text): the indices are NDVI and LSWI. Study area in China.
- Accuracy: overall 0.9291, kappa 0.8923. Silage maize user's accuracy 0.9216, producer's accuracy 0.94, F1 0.9307. Grain maize F1 0.9112.
- Against a random forest baseline (SMRF): overall accuracy 0.9043 vs 0.9291, kappa 0.8511 vs 0.8923, in favour of the threshold model.
- Temporal transfer of the same rules: overall accuracy 0.8621 (2022) and 0.8816 (2021).

Why it matters: it is the only source found that addresses our exact class pair, and the interpretable threshold model won. Caveat: one region in China, three classes including "other land cover", and the transfer loss of 5-7 points across years is the size of error we should expect when thresholds are not re-centred, which supports county-relative and GDD-normalised dates.

Also relevant: NASS CDL 2025 metadata lists corn producer's accuracy 92.2% and user's accuracy 91.2%, with no mention of silage; classes are Corn (1), Sweet Corn (12), Pop or Orn Corn (13). Inference: at pixel level about 9% of CDL "corn" is not corn; the error for field-majority labels will be lower, but whatever remains passes straight into the rollup and should be stated.

---

## 5. Recipes

Index definitions used by the features (standard definitions, not re-verified in this session; see the indices report for sources): NDVI = (B8 - B4) / (B8 + B4); NDMI / LSWI = (B8A - B11) / (B8A + B11); NDTI = (B11 - B12) / (B11 + B12); STI = B11 / B12 (Sentinel-2 band names).

### 5.1 Exhaustive two-question rule (best three-leaf rule on a threshold grid)

```python
import numpy as np, itertools
from sklearn.metrics import balanced_accuracy_score

def best_depth2(X, y, names, n_grid=20):
    grids = [np.unique(np.quantile(X[:, j], np.linspace(.05, .95, n_grid))) for j in range(X.shape[1])]
    best = (-1, None)
    for j, tj in ((j, t) for j in range(X.shape[1]) for t in grids[j]):
        left = X[:, j] <= tj
        for side, mask in (("L", left), ("R", ~left)):          # second question on one branch
            for k, tk in ((k, t) for k in range(X.shape[1]) for t in grids[k]):
                sub = mask & (X[:, k] <= tk)
                for labels in itertools.product([0, 1], repeat=3):  # other branch, sub, rest
                    pred = np.where(~mask, labels[0], np.where(sub, labels[1], labels[2]))
                    s = balanced_accuracy_score(y, pred)
                    if s > best[0]:
                        best = (s, (names[j], tj, side, names[k], tk, labels))
    return best
```
This is a sketch, not tested code: about 100,000 metric evaluations for 4 features and a 20-point grid, so vectorise the scoring or coarsen the grid before bootstrapping. Run it inside each grouped fold and on bootstrap resamples; report how often the same two features are chosen and the spread of the thresholds. Stability of the rule is itself evidence.

### 5.2 Monotone logistic scorecard

```python
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
# orient features so that "more silage-like" is positive: [-R, G, -D, -T]
clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight=None))
```
- Check that all four coefficients are positive after orientation; a wrong sign is a data bug or a collinearity warning.
- Keep `class_weight=None` if the probabilities feed the rollup (reweighting distorts calibration); handle imbalance with the decision threshold.
- Integer card: divide coefficients by the smallest one, round, refit the intercept. FasterRisk automates this and returns a pool of near-optimal cards (PyPI name `fasterrisk` from memory, not verified today).

### 5.3 EBM

```python
from interpret.glassbox import ExplainableBoostingClassifier
ebm = ExplainableBoostingClassifier(interactions=0, max_bins=32, min_samples_leaf=5,
                                    outer_bags=14, validation_size=0.15, random_state=0)
ebm.fit(X, y)
for term in range(X.shape[1]):
    ebm.monotonize(term, increasing="auto")   # post-fit, as the docs recommend
```
Defaults per the API page: `interactions="3x"`, `max_bins=1024`, `min_samples_leaf=4`, `outer_bags=14`, `validation_size=0.15`. With a few hundred rows, coarse bins and no interactions give readable, stable shape curves.

### 5.4 Monotone XGBoost on GPU (challenger)

```python
import xgboost as xgb
m = xgb.XGBClassifier(tree_method="hist", device="cuda", max_depth=2, n_estimators=200,
                      learning_rate=0.05, subsample=0.8, max_bin=256,
                      monotone_constraints={"neg_R": 1, "G": 1, "neg_D": 1, "neg_T": 1})
```

### 5.5 TabPFN (challenger)

```python
import os
os.environ["TABPFN_MODEL_VERSION"] = "v2"        # Apache-2.0 + attribution weights
# headless: os.environ["TABPFN_TOKEN"] = "..."   # licence acceptance happens once
from tabpfn import TabPFNClassifier
clf = TabPFNClassifier(); clf.fit(X_tr, y_tr); p = clf.predict_proba(X_te)[:, 1]
```
Tune the decision threshold by grouped CV; the default 0.5 was poor under imbalance in the clinical study.

### 5.6 MiniRocket on raw series (challenger)

```python
from aeon.transformations.collection.convolution_based import MiniRocket
from sklearn.linear_model import RidgeClassifierCV
import numpy as np
# X_ts: (n_fields, n_channels, n_timesteps) on a common 5- or 10-day grid, gap-filled
Z = MiniRocket(random_state=0).fit_transform(X_ts_train)
ridge = RidgeClassifierCV(alphas=np.logspace(-3, 3, 10), class_weight="balanced").fit(Z, y_train)
```
Import path is from memory of the aeon package layout; check it against the installed version.

### 5.7 AlphaEarth embedding ablation (2025 evaluation year only)

```python
import ee; ee.Initialize(project="<gcp-project>")
col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate("2025-01-01", "2026-01-01")
img = col.mosaic()                                   # tutorial caveat: set crs and scale when reducing
tbl = img.reduceRegions(collection=fields_fc, reducer=ee.Reducer.mean(), scale=10, crs="EPSG:4326")
# export tbl -> 64 columns A00..A63 per field; re-normalise each row to unit length;
# LogisticRegression(C=1) with the same grouped folds as every other row
```
Facts from the catalog page: 64 bands A00-A63, 10 m, unit-length vectors, one image per calendar year, CC-BY 4.0, attribution "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind." Main risk: Earth Engine authentication from the hosted notebook.

TESSERA alternative: `geotessera download --bbox '<w,s,e,n>' --year 2025 --output region/` or `GeoTesseraZarr().read_region(bbox, year=2025)`, then the same field mean and logistic regression.

### 5.8 Class-conditional conformal band from out-of-fold probabilities

```python
import numpy as np
def class_quantiles(p_oof, y, alpha=0.10):
    q = {}
    for k in (0, 1):
        s = 1 - np.where(k == 1, p_oof, 1 - p_oof)[y == k]
        n = len(s); level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
        q[k] = np.quantile(s, level, method="higher")
    return q
def predict_set(p, q):
    return [k for k in (0, 1) if 1 - (p if k == 1 else 1 - p) <= q[k]]   # len != 1 -> needs review
```

### 5.9 Bias-corrected acreage rollup

```python
def rollup(p, acres, tpr, fpr, thr):
    cc  = (acres * (p >= thr)).sum() / acres.sum()          # classify and count (biased)
    acc = np.clip((cc - fpr) / (tpr - fpr), 0, 1)           # adjusted count
    return cc * acres.sum(), acc * acres.sum()
# tpr, fpr from out-of-fold predictions on the labeled set (grouped folds), acreage-weighted if field sizes differ a lot
# probabilistic variant: replace (p >= thr) by p, and tpr/fpr by mean p among labeled silage / grain
# interval: bootstrap the labeled set (tpr, fpr) and the fields within the state, 1000 times
# reconciliation: factor_state = NASS_silage_acres / adjusted_acres; publish the factor
```
Estimate tpr and fpr per region if the labels allow it; a pooled estimate assumes the classifier behaves the same in California as in Iowa.

### 5.10 Evidence-card counterfactual

```python
from scipy.special import logit
def flip_delta(z, tau, beta_j):          # change in feature j that moves the call across tau
    return (logit(tau) - z) / beta_j
# "Called SILAGE (p = 0.83). It would be called grain if it had been cut 12 days later,
#  or if greenness at the cut had been 0.48 instead of 0.71."
```

---

## 6. Evaluation protocol

1. **Folds**: grouped by state or by county cluster, never random by field. Show random-fold numbers only next to grouped numbers, to display the gap (Goyal et al. 2026: 0.82-0.93 vs 0.34).
2. **Metrics for the silage class**: precision, recall, false positive rate, PR-AUC, balanced accuracy, Brier score, reliability diagram. Never headline accuracy; "always grain" is about 94% nationally.
3. **Intervals**: stratified bootstrap over fields (1000 resamples), or Wilson intervals for single proportions. With 30 positives, a recall of 0.85 has a 95% interval of roughly 0.68 to 0.94.
4. **Prevalence shift**: report results at the evaluation set's class mix and re-weighted to each state's NASS mix. Precision depends on prevalence; recall and FPR do not (Inference, standard).
5. **Selection hygiene**: thresholds, feature choices and calibration fitted inside folds; a locked holdout touched once.
6. **Response time**: per-field prediction latency for each model and end-to-end time per county. EBM documentation notes predictions reduce to lookups and additions; the rule is a pair of comparisons.
7. **Acreage check**: state silage acres from the adjusted count vs NASS 2025, before and after reconciliation, with the interval.

---

## 7. Talking points for USDA NASS statisticians

1. "Our classifier is a two-question rule and a four-term additive score. The explanation is the model, not an approximation of it." (Rudin 2019.)
2. "You built the CDL with a See5 decision tree from 2007 to 2023 and moved to a random forest for 2025. We are in the same family, one level simpler."
3. "We used the GPU to try to beat the rule with boosted trees, a tabular foundation model, a random-kernel time-series classifier and a satellite foundation embedding. Here is the table, with intervals." (Section 3.)
4. "Foundation embeddings are annual calendar-year summaries. No 2026 layer is listed yet, so they cannot support an in-season estimate. Our four numbers come from scenes acquired around the harvest itself." (State our measured latency once we have it.)
5. "We do not count classified fields. A classifier with 85% recall and a 3% false positive rate would overstate national silage acres by about 29% and understate California by about 15%. We correct with the adjusted count, as your CDL acreage uses regression estimates and not pixel counts."
6. "Where it fails: clouds over the harvest week, high-moisture grain and earlage that look like silage, failed grain chopped late, CDL corn commission error of about 9%, and regions unlike our labeled fields. The review band flags these, and its coverage is about 90% give or take 5 points because we had few silage labels."

---

## 8. Annotated bibliography

Status: O = opened and read (abstract or full text as noted); S = search result only, not opened.

Interpretable models
- Rudin 2019, "Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead", Nature Machine Intelligence 1:206-215. https://arxiv.org/abs/1811.10154 and https://ar5iv.labs.arxiv.org/html/1811.10154 (O, full text). Trade-off myth, fidelity argument, COMPAS vs three-rule model, Rashomon sets.
- Angelino et al. 2018, CORELS, JMLR 18(234). https://arxiv.org/abs/1704.01701 (O, abstract).
- Lin et al. 2020, GOSDT, ICML. https://arxiv.org/abs/2006.08690 (O, abstract).
- Liu et al. 2022, FasterRisk, NeurIPS. https://arxiv.org/abs/2210.05846 (O, abstract).
- InterpretML repository and EBM docs. https://github.com/interpretml/interpret , https://interpret.ml/docs/ebm.html , https://interpret.ml/docs/python/api/ExplainableBoostingClassifier.html (O). Benchmark table, EBM mechanics, monotonize advice.
- XGBoost monotonic constraints tutorial. https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html (O).
- Grinsztajn, Oyallon, Varoquaux 2022. https://arxiv.org/abs/2207.08815 (O, abstract).

TabPFN
- "Accurate predictions on small data with a tabular foundation model", Nature 637:319-326, 2025 (Hollmann et al.; author names from memory, not shown in the text read). https://pmc.ncbi.nlm.nih.gov/articles/PMC11711098/ (O, first 100k characters). The nature.com page redirected to a login.
- TabPFN repository. https://github.com/PriorLabs/TabPFN (O). Versions, licences, token, limits.
- Ye et al. 2026, TabPFN in data-limited clinical prediction. https://arxiv.org/html/2604.27195v2 (O).
- KU Leuven DTAI blog 2026-09-03. https://dtai.cs.kuleuven.be/sports/blog/tabular-foundation-models-for-xg:-can-tabpfn-score-without-training/ (O). Blog, not peer reviewed.

Explanations
- Kumar et al. 2020, ICML. https://ar5iv.labs.arxiv.org/html/2002.11097 (O, full text).
- Wachter, Mittelstadt, Russell 2018. https://arxiv.org/abs/1711.00399 (O, abstract).

Time-series classification
- Dempster, Schmidt, Webb, MiniRocket. https://arxiv.org/abs/2012.08791 (O, abstract). Hydra. https://arxiv.org/abs/2203.13652 (O, abstract).
- Middlehurst, Schafer, Bagnall 2024, Bake off redux. https://arxiv.org/abs/2304.13029 (O, abstract; journal details, Data Mining and Knowledge Discovery 38(4), from a search listing).
- Lubba et al. 2019, catch22. https://arxiv.org/abs/1901.10200 (O, abstract).
- Belgiu and Csillik 2018, RSE 204:509-523. https://research.utwente.nl/en/publications/sentinel-2-cropland-mapping-using-pixel-based-and-object-based-ti (O, abstract; ScienceDirect returned 403).
- aeon shapelet documentation. https://www.aeon-toolkit.org/en/stable/examples/classification/shapelet_based.html (O).
- "BreizhCrops: A Time Series Dataset for Crop Type Mapping". https://ar5iv.labs.arxiv.org/html/1905.11893 (O). "Temporal Convolutional Neural Network for the Classification of Satellite Image Time Series" (cited above as Pelletier et al. 2019; author names for both papers are from memory, not shown in the text read). https://ar5iv.labs.arxiv.org/html/1811.10166 (O).

Foundation models and embeddings
- Brown et al. 2025, AlphaEarth Foundations. https://arxiv.org/abs/2507.22291 , https://arxiv.org/html/2507.22291v2 (O, first 200k characters; per-dataset result tables not extracted).
- Earth Engine catalog and tutorial. https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL , https://developers.google.com/earth-engine/tutorials/community/satellite-embedding-01-introduction (O).
- Ma, Shen, Swatantran, Lobell 2025, Harvesting AlphaEarth. https://arxiv.org/abs/2601.00857 , https://github.com/yuchima8/Harvest_AlphaEarth (O, abstract and README; arXiv HTML returned 404; journal version at sciencedirect.com/science/article/pii/S1569843226001743 not opened).
- Goyal et al. 2026. https://arxiv.org/html/2610.36857 (O).
- Nedungadi et al. 2026. https://arxiv.org/abs/2608.30392 , https://arxiv.org/html/2608.30392v1 (O).
- Kolluru et al. 2026, Prithvi transferability. https://arxiv.org/abs/2610.08810 (O, abstract).
- Shang, Das, Eldawy 2026, GFM benchmark across Iowa, North Carolina, California, Minnesota. https://arxiv.org/abs/2606.29664 (O, abstract; no numbers in the abstract): Prithvi, SpectralGPT and SatMAE degrade sharply under regional shift and mostly predict common crops.
- Feng et al. 2025, TESSERA. https://arxiv.org/html/2506.20380v6 (O, first 100k characters); https://github.com/ucam-eo/geotessera (O).
- Tseng et al. 2023, Presto. https://ar5iv.labs.arxiv.org/html/2304.14065 , https://github.com/nasaharvest/presto (O).
- Tseng et al. 2025, Galileo. https://arxiv.org/html/2502.09356v3 (O, first 100k characters).
- Szwarcman et al., Prithvi-EO-2.0. https://arxiv.org/abs/2412.02732 (O, abstract). Jakubik et al., TerraMind. https://arxiv.org/abs/2504.11171 (O, abstract).
- "PANGAEA: A Global and Inclusive Benchmark for Geospatial Foundation Models". https://arxiv.org/html/2412.04204 (O, first 100k characters).
- Elbarz et al. 2026, Morocco. https://arxiv.org/html/2611.12681 (O). Narimani et al. 2026, California tomato. https://arxiv.org/abs/2605.21804 (O, abstract).

Weak, semi-supervised, active learning, VLM
- Ratner et al. 2017, Snorkel. https://arxiv.org/abs/1711.10160 (O, abstract).
- scikit-learn semi-supervised guide. https://scikit-learn.org/stable/modules/semi_supervised.html (O).
- Kaijage, Belgiu, Bijker 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11014375/ (O).
- "GEOBench-VLM: Benchmarking Vision-Language Models for Geospatial Tasks". https://arxiv.org/html/2411.19325v2 (O).

Calibration, conformal, aggregation, NASS
- scikit-learn calibration guide. https://scikit-learn.org/stable/modules/calibration.html (O).
- Angelopoulos and Bates 2021. https://arxiv.org/abs/2107.07511 (O, abstract).
- Kloos et al. 2023. https://arxiv.org/html/2308.08387v2 (O, first 100k characters).
- USDA NASS 2025 Cropland Data Layer metadata. https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_CDL25_FGDC-STD-001-1998.htm (O).

Direct precedent
- Lin et al. 2025, Agronomy 15(6):1438. https://www.mdpi.com/2073-4395/15/6/1438 (403); abstract read at https://library.kab.ac.ug/Record/doaj-art-588b9bec09f54a89a665031dc59ab6b6/Description (O, catalogue mirror).

---

## 9. Not opened, or opened only in part

| Item | Reason | Effect on confidence |
|---|---|---|
| Agronomy 2025 silage paper, full text | MDPI returned HTTP 403; abstract read through a catalogue mirror | Accuracy numbers medium confidence; indices, thresholds and harvest windows unknown |
| "Harvesting AlphaEarth" full text | arXiv HTML 404, PDF not parseable here | Only qualitative conclusions; no tillage or cover-crop numbers |
| AlphaEarth paper per-dataset tables | In figures / supplement beyond the text read | Only the averaged error reductions are quoted |
| Google Earth announcement of the 2025 embedding layer (X post) | Not opened | 2025 availability rests on the catalog date range plus my reading of the catalog convention; medium |
| Olofsson et al. 2014 | Repository redirect led to an error page | Mentioned as background only; low |
| PU-learning papers (PUL-SITS, DOCC, harvester-trajectory PUL) | Search results only | Low |
| GeoVision Labeler, Gemini 2.5 multispectral zero-shot | Search results only | Low |
| ISPRS 2025 "How effective are foundation models for crop type mapping" | PDF not parseable here | Not used |
| SSRN California AlphaEarth vs seasonal layers comparison (reported in search as favouring embeddings) | HTTP 403 | Possible counter-evidence, unverified |
| TESSERA v2 paper, Clay documentation, functional PCA, co-training | Not searched or not opened | Statements about them are marked as inference |
| Angelopoulos and Bates beyond the abstract | Only the abstract was re-read | Conformal formulas are given from memory and marked as inference |

---

## 10. Open questions

1. How many labeled fields do we have, in which states, and how were they chosen? Every interval in this report scales with that number, and conformal coverage and adjusted-count variance depend on the count per class.
2. What year are the labels? If 2025, the AlphaEarth and TESSERA ablations are possible; if 2026, they are not.
3. Does Earth Engine authentication work from the Keeboh notebook, and does TabPFN's token-gated weight download work there?
4. Do "silage-like" labels include earlage, high-moisture corn, green chop and failed grain chopped late? These sit between the classes on all four features.
5. Is a positive-only label source available (for example fields next to silage bunkers at dairies) that would justify the positive-unlabeled route?
