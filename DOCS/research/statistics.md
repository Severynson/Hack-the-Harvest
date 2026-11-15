# Statistics: from an imperfect field classifier and few labels to defensible acreage with uncertainty

Team Kernel, Hack the Harvest. Research note written Saturday 2026-11-14. Audience: the team tonight, and the USDA NASS mathematical statisticians on the judging panel tomorrow.

**How this was produced.** 22 web searches and about 50 page fetches. Where a source was a PDF, its text was extracted locally and read directly. The shared web-search budget ran out near the end, so a few leads could not be chased; they are listed in section 9 and are not used as evidence.

**Verification level used throughout**

| Tag | Meaning |
|---|---|
| [T] | Full text extracted and read directly (strongest) |
| [R] | Page read through the fetch tool's reader. Digits are probably right, but re-check before putting one on a slide |
| [A] | Abstract or catalogue record only |
| [X] | Not opened (reason given). Never used as evidence |

Anything marked **Inference:** is our own reasoning or arithmetic, not a statement from a source.

---

## 0. Bottom line

1. **Never sum hard labels.** Counting fields called "silage" is biased, and the bias changes sign with the base rate: a classifier with 90% recall and 5% false-positive rate over-counts silage by about two thirds where silage is rare (68% at a 6% share; 64% at the 2025 US share of 6.4%), and under-counts it by about 9% where silage is 88% (California). NASS says the same about its own map: pixel counting "is usually downward biased" and its internal acreage numbers are "regression estimates using NASS survey data".
2. **Three numbers, three jobs.** (i) A model-based share per state from prior-shift EM (tight, assumption-heavy). (ii) A label-based interval from adjusted counting or prediction-powered inference (honest, wide with 100-300 labels). (iii) A NASS-style reliability statement from a backtest against published January numbers ("chances are 2 out of 3 ..."). Show all three and say which is which.
3. **Which label-based estimator is valid depends on how the labeled fields were chosen.** Labels picked by class (curated "silage-like" / "grain-like") support only the confusion-matrix-inverse family (adjusted count, BBSE, EM). Labels that are a random sample of the target population support the stratified (Olofsson) estimator and prediction-powered inference, which need no assumption about the model. Find out tonight which one we have.
4. **Our plan's "cut date relative to the county median" breaks across regions.** The county median is itself a function of the silage share (it is the silage date in Tulare County and the grain date in Iowa), so the feature's meaning flips exactly where the base rate flips. Anchor timing to an agronomic clock instead (growing-degree-days, or the state's NASS "dented" and "mature" dates).
5. **Do not use isotonic calibration with 100-300 labels.** scikit-learn's own guidance is that isotonic needs more than about 1,000 calibration samples. Use sigmoid (Platt) scaling, cross-fitted, and Venn-Abers if we want an honest probability interval.
6. **Conformal coverage with few labels is "90%, give or take".** With 30 silage calibration fields the realised coverage for the silage class lands anywhere between about 80% and 97%. Calibrate per class, say the guarantee is an average over fields like the labeled ones, and check coverage by state.
7. **"Same as last year" is a brutal national baseline.** US silage acreage was 6,461, 6,207 and 6,208 thousand acres in 2023, 2024, 2025. Persistence would have missed 2025 by 0.02% and 2024 by 4.1%. Our value has to be shown at state and county level and in year-to-year change, as skill over persistence.
8. **A new, label-free harvest signal exists in NASS's own weekly reports.** Wisconsin publishes "corn harvested for silage" every week by crop reporting district (32% on 13 Sep 2026, districts 17% to 43%). Together with the state grain-harvest progress curve, this gives the true-positive and false-positive rate of the rule "cut before date t" for free, which turns our detected cut-date distribution into a silage share without any field labels. We found no precedent for this.
9. **Benchmark last, and label it.** Raking field probabilities to the same year's NASS totals and then reporting agreement with those totals is circular. Publish the independent estimate first; publish a benchmarked map separately, after the fact.
10. **The autoresearch loop will overfit a 150-field evaluation set.** Lock a final test split that the loop never sees.

---

## 1. What this means for Kernel

### 1.1 Things in plan v2 that should change

| Plan v2 item | Problem | Change |
|---|---|---|
| Cut date "relative to the county median" | **Inference:** the county median depends on the class mix, so the class-conditional distribution of this feature differs between a silage county and a grain county. That violates the one assumption every prior-shift method needs (features given class look the same everywhere). Kluger et al. 2021 call this an "apparent feature shift" caused by composition. | Express the cut date on a composition-free clock: GDD since emergence or since peak greenness, or days relative to the state's NASS 50%-dented and 50%-mature dates. If a regional offset is still needed, estimate it the Kluger way (section 3b), which subtracts the composition term. |
| "GPU XGBoost with isotonic calibration" | scikit-learn: isotonic "is more prone to overfitting, especially on small datasets"; it matches sigmoid only with "greater than ~ 1000 samples". | Sigmoid (Platt) calibration fitted on out-of-fold predictions. Venn-Abers for an interval. Reliability diagram with 5 bins and Wilson bands. |
| "Conformal needs-review band" | The guarantee is marginal, needs exchangeability, and the realised coverage with 30 silage calibration fields ranges about 0.80 to 0.97. | Class-conditional (Mondrian) split conformal, calibration scores from out-of-block predictions, coverage reported by state. Word the claim as in section 4. |
| "County and state rollups reconciled with NASS" | Circular if the reconciliation target is the number we claim to predict. | Two products: an **independent** estimate (prior year used only as the EM starting value) and a **benchmarked** map (raked to official totals once they exist). Report accuracy only for the first. |
| "Transparent two-question rule, then XGBoost" | With about 30 silage labels, a boosted model's advantage over a 2-4 parameter rule is unlikely to be statistically distinguishable. | Run a paired test (McNemar, exact binomial on the discordant pairs). If the lift is not distinguishable, ship the rule and say so. That is the "interpretable beats clever" answer with evidence. |
| Autoresearch loop scoring against the evaluation set | Selecting the best of K experiments on n fields inflates the winner. **Inference (Gaussian maximal bound):** up to about 0.06 to 0.09 in accuracy for n = 150 and K = 20 to 500. | Split the labels once: a development part for the loop, a locked final part scored once. Report the final part only. |
| Precision reported on the evaluation set | Precision depends on prevalence. With TPR 0.90 and FPR 0.05, precision is 0.95 on a balanced evaluation set, 0.54 at the US base rate, 0.99 in California. | Report recall and false-positive rate with Wilson intervals (they transfer), then derive precision at each state's base rate. |
| Dairy distance as a classifier feature plus regional priors | Risk of counting the base rate twice. | **Inference (design suggestion):** treat location information (prior-year state share, dairy proximity) as the prior, and the four measured numbers as the evidence. The Harvest Story card can then read "prior 6%, evidence multiplies the odds by 75, posterior 83%". |

### 1.2 Things in plan v2 that the literature supports

- Four measured numbers and a small transparent model. With few labels this is what the sample size can support.
- State and county rollups checked against NASS. This is the standard sanity check (Kluger et al. 2021 and Wang et al. 2019 both lean on aggregate statistics).
- Reporting where the method fails. NASS's own reports do this with a reliability table; mirror its format (section 3h).

### 1.3 New signals this topic surfaced (for the Innovation score)

1. **Weekly Crop Progress deconvolution** (section 3c): silage share from the detected cut-date distribution, using NASS weekly silage and grain harvest progress as the mixture components. Label-free, explainable, in-season, not circular.
2. **NASS "dented" and "mature" progress dates as the regional clock** for the cut-date feature. Silage is cut near dent; grain is combined after maturity plus dry-down. The clock comes from NASS itself.
3. **District-level validation target**: Wisconsin's weekly "corn harvested for silage" by nine districts lets us validate the *timing* of detected silage cuts weeks before any acreage number exists.

---

## 2. The minimal recipe for tonight

Order matters: steps 1-4 are the defensible core; 5-8 add credibility; 9-10 are stretch.

**Note on the code.** The numpy snippets below were not executed here (no numpy in this environment). Each formula was checked with an equivalent pure-Python simulation; results are in section 5.9.

### Step 0 (15 min). Establish how the labels were sampled

Ask the organisers, or infer from the data: are the labeled fields (a) curated by class, (b) a random sample of some region's cornfields, or (c) unknown? Which states and which year? Is the class mix of the label set close to 50/50 or close to the regional base rate?

- Class-curated or unknown: use steps 2 and 3 (they rely on TPR and FPR, which survive class-based selection).
- Random sample of a defined population: step 4 also applies, for that population only.

### Step 1 (30 min). Split once, score honestly

```python
from sklearn.model_selection import StratifiedGroupKFold
# groups = county FIPS, or a ~50 km tile id, so neighbours never straddle train and test
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=0)
# 1) lock ~30% of the labels (whole groups) as FINAL: never shown to the autoresearch loop
# 2) all model selection, calibration and conformal thresholds use the remaining DEV part,
#    with out-of-fold predictions from `cv`
```

Report every rate with its counts and a Wilson interval:

```python
from statsmodels.stats.proportion import proportion_confint
lo, hi = proportion_confint(count=27, nobs=30, alpha=0.05, method="wilson")   # recall 27/30
```

### Step 2 (30 min). Adjusted count with a confidence interval (works with class-curated labels)

Let `q` be the naive acre-weighted share called silage, `t` the true-positive rate and `f` the false-positive rate measured on labeled fields.

```
pi_hat  = (q - f) / (t - f)                                   # adjusted count (Rogan-Gladen; 2-class BBSE)
Var(pi_hat) ~= [ q(1-q)/N_eff + (1-pi)^2 * f(1-f)/n_grain + pi^2 * t(1-t)/n_silage ] / (t - f)^2
```

```python
import numpy as np
def adjusted_share(yhat_all, acres_all, yhat_lab, y_lab, z=1.96):
    q = np.average(yhat_all, weights=acres_all)
    pos, neg = (y_lab == 1), (y_lab == 0)
    t, f = yhat_lab[pos].mean(), yhat_lab[neg].mean()
    pi = float(np.clip((q - f) / (t - f), 0, 1))
    n_eff = acres_all.sum()**2 / (acres_all**2).sum()
    var = (q*(1-q)/n_eff + (1-pi)**2*f*(1-f)/neg.sum() + pi**2*t*(1-t)/pos.sum()) / (t - f)**2
    se = float(np.sqrt(var))
    return pi, (pi - z*se, pi + z*se), {"q": q, "tpr": t, "fpr": f}
```

**Inference:** the variance is our delta-method derivation; it is the standard Rogan-Gladen form. In our simulation its 95% interval covered 93% (pi = 0.06), 95% (pi = 0.215) and 89% (pi = 0.88) of the time with 50 + 100 labels, so widen it a little or bootstrap the labeled fields by block. Flor et al. 2020 report that naive intervals of this family under-cover and recommend the Lang-Reiczigel interval or a Bayesian one.

What it tells us about where to spend labels (**Inference**, from the formula): where silage is rare, the interval is driven by the false-positive rate, so grain labels matter most; where silage dominates (California), it is driven by recall, so silage labels matter most.

| Scenario at pi = 0.06 | n_silage | n_grain | SE of share | 95% half-width | In US acres (97.5M grain + silage) |
|---|---|---|---|---|---|
| TPR 0.90, FPR 0.05 | 30 | 120 | 0.022 | 0.044 | 4.3M |
| TPR 0.90, FPR 0.05 | 50 | 600 | 0.010 | 0.020 | 2.0M |
| TPR 0.95, FPR 0.01 | 30 | 120 | 0.009 | 0.018 | 1.8M |
| TPR 0.95, FPR 0.01 | 50 | 600 | 0.0045 | 0.009 | 0.9M |

For comparison, the true US silage area is 6.2M acres. With 150 labels the label-based interval is as wide as the quantity itself unless the false-positive rate is near 1%. Say this plainly.

### Step 3 (45 min). Prior-shift EM per state: the model-based share and the adjusted field probabilities

Saerens et al. 2002. Inputs: calibrated probabilities `p` for every cornfield in one region, and `pi_train`, the silage share those probabilities are calibrated to (the class mix of the calibration data).

```
E-step:  p_i' = [ p_i * pi/pi_train ] / [ p_i * pi/pi_train + (1-p_i) * (1-pi)/(1-pi_train) ]
M-step:  pi   = acre-weighted mean of p_i'
```

```python
def em_prior_shift(p, pi_train, acres=None, tol=1e-8, max_iter=1000):
    w = np.ones_like(p) if acres is None else acres
    pi = pi_train
    for _ in range(max_iter):
        num  = p * pi / pi_train
        post = num / (num + (1 - p) * (1 - pi) / (1 - pi_train))
        new  = float(np.average(post, weights=w))
        if abs(new - pi) < tol:
            break
        pi = new
    return pi, post           # regional silage share, prior-corrected field probabilities
```

- Run it per state (or crop reporting district). Start from last year's NASS share if you like; the answer does not depend on the start (Alexandari et al. 2020 prove the likelihood is concave; our simulation gave differences of 1e-9 between starts).
- It is only as good as the calibration and the "same features given class everywhere" assumption. Saerens' own Table 1 shows estimates pulled toward the training prior when the classifier is imperfect (true 10% estimated as 14.7%).
- Field probabilities used on evidence cards and in rollups should be the corrected `post`, not the raw classifier output. Acreage = sum of acres times `post` (never sum of acres times hard label).

Known prior instead of estimated prior (for example a what-if with last year's NASS share): the same E-step formula with `pi` fixed. In odds form: `odds_new = odds_classifier * [pi_new/(1-pi_new)] / [pi_train/(1-pi_train)]`.

| Classifier says (trained 50/50) | US-wide prior 6% | Dairy-state prior 21.5% | California prior 88% |
|---|---|---|---|
| 0.20 | 0.016 | 0.064 | 0.647 |
| 0.50 | 0.060 | 0.215 | 0.880 |
| 0.80 | 0.203 | 0.523 | 0.967 |
| 0.95 | 0.548 | 0.839 | 0.993 |

(**Inference:** our arithmetic. The 21.5% column is what Wisconsin's 2025 share would be if the state row in section 5.1 is right; that row is flagged as unverified.)

### Step 4 (45 min, only if some labels are a random sample of a defined population). Design-based interval

Either the stratified (Olofsson) estimator or prediction-powered inference. Lu, Bates and Wang show they give nearly identical intervals for area.

Stratified, with strata = predicted class by confidence band (for example confident grain, review band, confident silage):

```
share_hat = sum_h W_h * p_h            W_h = acre share of stratum h;  p_h = share of sampled fields in h that are truly silage
SE        = sqrt( sum_h W_h^2 * p_h (1 - p_h) / (n_h - 1) )
acres     = A_total * share_hat  +/-  1.96 * A_total * SE
```

```python
def stratified_share(strata_all, acres_all, strata_lab, y_lab, z=1.96):
    A, est, var = acres_all.sum(), 0.0, 0.0
    for h in np.unique(strata_all):
        W  = acres_all[strata_all == h].sum() / A
        yh = y_lab[strata_lab == h]
        ph = yh.mean()
        est += W * ph
        var += W**2 * ph * (1 - ph) / max(len(yh) - 1, 1)
    se = float(np.sqrt(var))
    return est, (est - z*se, est + z*se)
```

Prediction-powered (PPI, lambda = 1), acre-weighted:

```
share_hat = [acre-weighted mean of p over ALL fields] + [acre-weighted mean of (y - p) over LABELED fields]
Var       = Var(y - p)/n  +  Var(p)/N
```

```python
def ppi_share(y_lab, p_lab, a_lab, p_all, a_all, z=1.96):
    model_part = np.sum(a_all * p_all) / np.sum(a_all)
    r    = y_lab - p_lab
    rect = np.sum(a_lab * r) / np.sum(a_lab)
    n    = len(y_lab)
    var  = (np.sum((a_lab * (r - rect))**2) / np.sum(a_lab)**2 * n / (n - 1)
            + np.sum((a_all * (p_all - model_part))**2) / np.sum(a_all)**2)
    est, se = model_part + rect, float(np.sqrt(var))
    return est, (est - z*se, est + z*se)
```

Library route: `ppi_py.ppi_mean_ci(Y, Yhat, Yhat_unlabeled, alpha=0.1, w=None, w_unlabeled=None)`. Note the default `alpha=0.1` (a 90% interval) and that `lam=None` turns on PPI++ power tuning.

Honest caveats to state: a stratum with zero observed errors gives zero variance, which is false precision. With 0 silage fields found among 120 sampled "grain" fields, the Wilson upper bound on the miss rate is still 3.1%, which at a 93% "grain" stratum weight is 2.9 points of silage share, about half of the 6% we are trying to measure. Sample the review band heavily; that is where omissions live.

### Step 5 (45 min). Calibration that the sample size can support

```python
from sklearn.linear_model import LogisticRegression
# out-of-fold raw scores s_oof for DEV labels from the grouped CV in step 1
platt = LogisticRegression(C=1e6).fit(s_oof.reshape(-1, 1), y_dev)     # sigmoid calibration, 2 parameters
p_cal = platt.predict_proba(s_all.reshape(-1, 1))[:, 1]
pi_train = y_dev.mean()                                                # the prior these probabilities carry
```

Reliability diagram: 5 quantile bins, plot observed share with Wilson bands. Brier skill against the base-rate forecast: `BSS = 1 - BS / (pi*(1-pi))`.

### Step 6 (45 min). Class-conditional conformal sets, which give the "needs review" band

```python
def classwise_thresholds(p_cal, y_cal, alpha=0.10):
    th = {}
    for k in (0, 1):
        s = np.sort(1 - np.where(y_cal == 1, p_cal, 1 - p_cal)[y_cal == k])   # 1 - prob. of the true class
        n = len(s); lvl = int(np.ceil((n + 1) * (1 - alpha)))
        th[k] = np.inf if lvl > n else s[lvl - 1]
    return th

def predict_set(p, th):
    silage_in, grain_in = (1 - p) <= th[1], p <= th[0]
    return np.where(silage_in & grain_in, "review",
           np.where(silage_in, "silage", np.where(grain_in, "grain", "atypical")))
```

- `p_cal` must be out-of-fold (ideally out-of-block) probabilities of labeled fields.
- A class needs at least 9 calibration fields for a finite threshold at alpha = 0.10, and 19 at alpha = 0.05.
- "atypical" (empty set) is useful: it is where abandoned, grazed or hay corn (about 1.3M acres in 2025) should land.

### Step 7 (1-2 h). Weekly-progress cross-check (label-free)

For a state that reports weekly silage progress (Wisconsin verified):

```
G(t)  = our acre-weighted share of corn acres detected as cut by week t
Fs(t) = NASS "corn harvested for silage" progress, 0-1
Fg(t) = NASS "corn harvested" (grain) progress, 0-1
G(t) ~= pi * Fs(t) + (1 - pi) * Fg(t)
pi_hat = sum_t (G - Fg)(Fs - Fg) / sum_t (Fs - Fg)^2
```

```python
def progress_deconvolution(G, Fs, Fg):
    d = Fs - Fg
    return float(np.clip(np.sum((G - Fg) * d) / np.sum(d**2), 0, 1))
```

At a single date this is exactly the adjusted count of step 2 with TPR = Fs(t) and FPR = Fg(t) supplied by NASS. Interval: bootstrap fields by county. Our simulation shows a small bias toward the middle when detected dates are noisier than the reference curves (true 0.06 estimated 0.068; true 0.88 estimated 0.867), so present it as a cross-check, not the headline.

### Step 8 (1-3 h, the most persuasive slide). NASS-style reliability table from a backtest

Run the frozen pipeline on every past state-year we can (2023, 2024, 2025 against the January numbers), without using that year's totals anywhere.

```python
def reliability(est, final):                 # arrays over state-years
    d = 100 * (est - final) / final
    rmse = float(np.sqrt(np.mean(d**2)))
    return {"rmse_pct": rmse, "avg_abs_diff": float(np.mean(np.abs(est - final))),
            "smallest": float(np.min(np.abs(est - final))), "largest": float(np.max(np.abs(est - final))),
            "below_final": int((est < final).sum()), "above_final": int((est > final).sum())}
```

Then compute the same table for the persistence forecast (last year's acres) and report skill = 1 - RMSE_model / RMSE_persistence.

### Step 9 (30 min, after everything else). Benchmarked map

Shift every field's log-odds by one constant per region so acres sum to a target. This is the prior-shift formula again and keeps probabilities inside 0-1.

```python
from scipy.optimize import brentq
def rake_logit(p, acres, target_acres):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    g = lambda lam: np.sum(acres * p*np.exp(lam) / (1 - p + p*np.exp(lam))) - target_acres
    lam = brentq(g, -30, 30)
    return p*np.exp(lam) / (1 - p + p*np.exp(lam)), lam
```

For a two-way table (county by class with both margins known) use iterative proportional fitting: `pip install ipfn`, then `ipfn.ipfn(table, [row_totals, col_totals], [[0], [1]]).iteration()`.

### Step 10 (stretch). Second opinion from a quantification library

`pip install quapy` (docs are for 0.2.3). `qp.method.aggregative.ACC`, `PACC`, `EMQ` (the Saerens EM, also called SLD), and `quapy.method.confidence.AggregativeBootstrap` for intervals. Use only as a cross-check of steps 2 and 3.

---

## 3. Evidence by sub-topic

### 3a. Quantification under class imbalance

**Classify-and-count is biased.** If a rule has true-positive rate `t` and false-positive rate `f`, the expected counted share is `q = pi*t + (1-pi)*f`, which equals `pi` only at `pi* = f / (f + 1 - t)`. Below that prevalence the rare class is over-counted; above it, under-counted.

**Inference (our arithmetic):**

| TPR | FPR | True share | Counted share | Relative bias | Precision at that share |
|---|---|---|---|---|---|
| 0.90 | 0.05 | 0.060 | 0.101 | +68% | 0.54 |
| 0.90 | 0.05 | 0.215 | 0.233 | +8% | 0.83 |
| 0.90 | 0.05 | 0.500 | 0.475 | -5% | 0.95 |
| 0.90 | 0.05 | 0.880 | 0.798 | -9% | 0.99 |
| 0.95 | 0.01 | 0.060 | 0.066 | +11% | 0.86 |
| 0.95 | 0.01 | 0.880 | 0.837 | -5% | 1.00 |

In acres: at the 2025 US share (6.208M of 97.466M grain-plus-silage acres), TPR 0.90 and FPR 0.05 would count 10.15M silage acres, an error of +3.9M. Even TPR 0.95 and FPR 0.01 over-counts by 0.6M (about 10%).

**What the sources show.**

- NASS CDL FAQ [R]: pixel-count summaries "should be considered raw numbers needing bias correction"; "Pixel counting is usually downward biased when compared to the official estimates"; NASS's internal CDL acreage estimates are "regression estimates using NASS survey data". Producer's accuracy is "generally 85% to 95% correct for the major crop-specific land cover categories". The CDL has no silage class (Corn = 1, Sweet Corn = 12, Pop or Orn Corn = 13). The 2025 CDL was released 27 February 2026.
- Lu, Bates, Wang 2024 [T]: in an Iowa maize simulation built on the CDL, a map with accuracy 0.86 gave an imputed maize fraction of 0.21 against a true 0.35. "even a map with high model accuracy can yield biased estimates under naive imputation".
- Saerens, Latinne, Decaestecker 2002 [T]: EM re-estimation of priors from classifier posteriors, compared with the confusion-matrix method (solve `p(called i) = sum_j p(called i | true j) * p(j)`, which is adjusted count). Ringnorm data, classifier trained 50/50, 1,000 test cases, 10 runs:

| True prior | EM estimate | Confusion-matrix estimate |
|---|---|---|
| 10% | 14.7% | 18.1% |
| 20% | 21.4% | 24.2% |
| 30% | 33.0% | 34.4% |
| 50% | 49.2% | 49.0% |
| 70% | 66.8% | 64.8% |
| 90% | 85.6% | 80.9% |

  Both are pulled toward the 50% training prior; EM less so. At most 5 EM iterations were needed. Stated conditions: posteriors "sufficiently well estimated"; the training sample chosen by class and not by features, so within-class densities do not change; and a new data set "large enough". They also give a likelihood-ratio test (chi-square, classes minus 1 degrees of freedom) for whether the priors changed at all.
- Lipton, Wang, Smola 2018 (BBSE) [A]: estimates the target label distribution from a black-box predictor's confusion matrix; works "so long as their confusion matrices are invertible"; even for biased or uncalibrated predictors; assumes `p(x|y)` fixed.
- Alexandari, Kundaje, Shrikumar 2020 [A]: EM needs calibrated probabilities; with bias-corrected calibration it outperforms BBSL and RLLS; the likelihood is concave.
- QuaPy 0.2.3 documentation [R]: CC, ACC, PCC, PACC, EMQ (alias SLD / MLLS), BBSEhard / BBSEsoft, RLLS, HDy, DyS, KDEy, plus Forman's threshold variants (T50, MAX, X, MS, MS2) that stabilise the ACC denominator. ACC options: `method` in {"inversion", "invariant-ratio"}, `solver` in {"exact-raise", "exact-cc", "minimize"}; `val_split` float, int folds, or an explicit `(X, y)`. Intervals: `AggregativeBootstrap` (regions "intervals", "ellipse", ...), and Bayesian variants via `pip install quapy[bayes]`.
- Flor et al. 2020 [R] (the epidemiology twin of adjusted count): Rogan-Gladen estimate `(AP - (1 - Sp)) / (Se - (1 - Sp))`; about 4% of simulated estimates fell outside 0-1; Clopper-Pearson, Blaker, Sterne and Wald-Rogan-Gladen intervals showed "strong under-coverage"; the Lang-Reiczigel interval and a Bayesian interval were close to nominal 95%.

**So what.** Use adjusted count for the label-based interval, EM for the per-state share, and never report a summed hard-label acreage.

### 3b. Label shift across regions, and the Kluger "two shifts"

**Prior-shift correction with a known regional prior** (Saerens eq. 4, adopted by Kluger et al. as "Prior Shift Adjustment"):

```
p_new(k | x)  proportional to  p_train(k | x) * pi_new(k) / pi_train(k)
```

**Kluger, Wang, Lobell 2021, "Two shifts for crop mapping"** [T], Remote Sensing of Environment 262. What it shows:

- Problem: a classifier trained in one region and applied in another loses accuracy because (1) the crop mix differs and (2) the features themselves shift.
- Shift 1, crop mix: re-weight posteriors with the target region's aggregate crop proportions (the formula above). They note Random Forest and neural-network posteriors "can be poorly calibrated".
- Shift 2, features: an additive model for the mean feature vector of crop `k` in region `r`, `mu_rk = alpha_r + beta_k`, with no crop-by-region interaction. With labels in one region only and known class proportions `pi_rk` everywhere: `beta_k` = class means in the training region (its `alpha` set to 0); `alpha_r = xbar_r - sum_k pi_rk * beta_k`; subtract `alpha_r` from every field's features in region `r` before classifying. They state explicitly that composition changes cause *apparent* feature shifts in the regional mean and that the method separates those from true shifts. (The two-step procedure is described in the text; the symbols were lost in our text extraction, so the `alpha_r` formula above is reconstructed from the model statement. Check it against the paper's section 2.2 before coding.)
- Results: Occitanie, France (52,641 parcels, 13 departments, 6 classes) and Western Province, Kenya (16,964 fields, 3 districts). With LDA, the combined correction increased overall accuracy by 0.003 to 0.097 (mean 0.034) across 11 training departments in France, a 2.8% to 42.2% reduction in misclassifications (mean 21.9%); in Kenya the reductions were 6.6%, 28.4% and 42.7%. Also shown to help a Random Forest.
- Limits they report: little benefit when the training region already resembles the target (Tarn); in Kenya accuracy stayed in the 0.55 to 0.65 range and one training region was "not much more accurate than ... always guessing the major class"; the additive model assumes no crop-by-region interaction.

**Wang, Azzari, Lobell 2019** [R] (Stanford record), Remote Sensing of Environment 222: random forests transferred across US Midwest states and years with accuracy "consistently exceeding 80%" when growing degree days were similar, declining as GDD differences grew. A no-label Gaussian mixture reached over 85% in Illinois, Iowa, Indiana and Nebraska and was "sometimes no better than random" in the Dakotas, Wisconsin and Michigan; cluster labels were assigned using county-level crop statistics.

**So what for us (Inference).**

1. Prior-shift methods assume the features of a silage field look the same in California and Wisconsin. Raw calendar dates violate this (Texas grain is combined in summer). GDD-based timing is the direct remedy, and Wang et al. show GDD similarity is what makes transfer work.
2. "Relative to the county median" is the textbook apparent shift: the median moves with the mix. If we want a regional offset, compute it Kluger's way with last year's NASS state shares as `pi_rk`.
3. Test the invariance: train without one state, compare class-conditional feature distributions in the held-out state (even a two-sample plot per feature is enough for the pitch).

### 3c. Weak supervision with aggregate statistics; mixtures and deconvolution

**Precedent for learning from aggregate proportions.**

- La Rosa, Oliveira, Ghamisi 2022 [R] (arXiv 2208.11607): contrastive clustering with class-proportion constraints (LLP-Co), two Brazilian municipalities, proportions from IBGE municipal statistics. With exact proportions, accuracy was 94.1% (Campo Verde) and 90.5% (LEM). With the official census proportions, which differed from the annotated ones (cotton 20.05% in the census against 45.30% in the annotations), Campo Verde fell to 80.5% with cluster swapping (35.0% before re-matching). The method "failed to identify minor classes". A weak precedent for a 6% class.
- Wang, Azzari, Lobell 2019 [R]: unsupervised mixture, clusters named with county statistics (above).
- Kluger et al. 2021 [T]: aggregate statistics used for correction rather than training (above). This is the most robust use and the one we should copy.

**Mixture of harvest dates informed by NASS weekly progress: precedent?** One extended search found none for silage against grain. Adjacent work exists on harvest-date detection and on Gaussian mixtures of phenology metrics, but not this combination. Treat it as our own proposal.

**What makes it feasible (verified).**

- Wisconsin Crop Progress and Condition, released 14 September 2026 [T]: "Corn for silage harvest was 32 percent complete compared to the average of 21 percent." The table lists "Corn harvested for silage" for nine districts and the state.

| Week ending 13 Sep 2026 | NW | NC | NE | WC | C | EC | SW | SC | SE | State | Last week | Last year | 5-yr avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Corn dented (%) | 66 | 40 | 58 | 79 | 65 | 74 | 82 | 80 | 75 | 73 | 57 | 69 | 72 |
| Corn mature (%) | 18 | 14 | 12 | 31 | 19 | 27 | 33 | 28 | 26 | 26 | 14 | 16 | 17 |
| Corn harvested for silage (%) | 40 | 17 | 22 | 41 | 34 | 28 | 43 | 39 | 38 | 32 | 14 | 20 | 21 |

  (Column assignment reconstructed from the PDF's column-ordered text; the state value matches the report's sentence.)
- National Crop Progress, released 13 October 2026 [R]: corn harvested in the 18 states 33% (week ending 11 October), 23% the week before, five-year average 39%, last year "NA". Texas 89%, Kansas 63%, Minnesota 25%, Wisconsin 16% (8% the week before), Iowa 14%. There is no silage line in the national report. Method: "approximately 3,600 respondents" who "subjectively estimate the progress of crops"; a non-probability survey; county reports weighted by NASS county acreage estimates.

**The idea, in one line.** NASS reports silage progress as a share of silage acres and grain progress as a share of grain acres. So the share of all corn acres cut by week t is `G(t) = pi*Fs(t) + (1-pi)*Fg(t)`, and `pi` is the only unknown.

**Inference: caveats.**

- It works where the two curves are separated (Wisconsin: silage mostly done before grain starts) and is ill-conditioned where they overlap (Texas, where grain is 89% harvested by 11 October; California).
- Crop Progress is subjective and not a probability survey, so its curves carry unknown error. Cross-check, not headline.
- The report does not itself say "corn harvested" means grain only. Confirm in the NASS terms and definitions.
- "Last year NA" in the October 2026 report means the October 2025 curve is missing. **Inference (from memory, unverified):** the autumn 2025 federal shutdown. For a 2025 backtest, use the five-year average grain curve or our own detected grain dates.
- Only states that publish silage progress can be used. Wisconsin is verified; other dairy states need checking.

### 3d. Design-based and model-assisted area estimation

**Olofsson et al. 2014 "good practices"** [X: repository copy would not open]. The estimators were verified from two sources that reproduce them: the `mapaccuracy` R package source [R], which implements Olofsson et al. 2013 and 2014, and Lu, Bates, Wang 2024 [T], which states the formula. With map classes `i` as strata, `W_i` the area share of map class `i`, and `n_ij` sampled units with map class `i` and reference class `j`:

```
p_ij          = W_i * n_ij / n_i.                         (error matrix in area proportions)
area share j  = sum_i W_i * n_ij / n_i.                   (error-adjusted area of reference class j)
SE            = sqrt( sum_i W_i^2 * (n_ij/n_i.)(1 - n_ij/n_i.) / (n_i. - 1) )
user's acc_i  = p_ii / p_i.        producer's acc_j = p_jj / p_.j        overall = sum_i p_ii
95% interval  = estimate +/- 1.96 * SE     (multiply by total area for acres)
```

**Two directions of correction (Inference, a framing that helps with statisticians).**

| | "Direct" (condition on the map) | "Inverse" (condition on the truth) |
|---|---|---|
| Uses | P(truth given call): user's accuracy | P(call given truth): TPR and FPR |
| Estimators | Stratified / Olofsson, PPI, regression estimator | Adjusted count, BBSE, EM, Rogan-Gladen |
| Label sample must be | A probability sample of the *target population* (within map strata) | Representative *within each true class*; class mix can be arbitrary |
| Extra assumption | None about the model | Features given class are the same in labels and target |
| Fails when | Labels come from elsewhere or were hand-picked | Regions differ in how silage or grain looks |

**Lu, Bates, Wang 2024** [T] (arXiv 2407.13659 v1, "Quantifying uncertainty in area and regression coefficient estimation from remote sensing maps"; later versions carry the regression-only title and report effective-sample-size gains "up to 17-fold" [A]):

- Iowa maize, CDL-derived map, N = 100,000 map points, n = 100 "ground truth" points, true fraction 0.35. The paper cites 94.2% producer's and 97.2% user's accuracy for maize in Iowa. PPI's effective sample size fell from 578 (10% of points noised) to 100 (pure noise). "The Olofsson confidence intervals and effective sample sizes are nearly identical to those of PPI."
- Brazilian Amazon deforestation 2000-2015, N = 4.4e9 pixels, n = 1,386: Olofsson and PPI gave effective sample sizes 1.9 and 1.8 times n; stratified sampling and stratified PPI about 2.4 times (3,382 effective).
- "If the n ground truth points are obtained by stratified random sampling using the K map land cover classes as the strata, the Olofsson confidence interval is identical to the stratified confidence interval."
- Their recommendation: map producers should release a holdout ground-truth set for calibration.

**Gallego, review of remote sensing methods for crop area estimates** [T] (ISPRS Archives XXXVI-8/W48; complements Gallego 2004 [X] and Carfagna and Gallego 2005 [X]):

- Three families: pixel counting; regression, calibration and small-area estimators; and images as support for area frames.
- On pixel counting: "this type of approaches should not be used unless there is no reasonable alternative. The statistical justification ... is very weak and there is a very high risk that the final estimates come essentially from the a priori belief of the analyst."
- "The regression estimator is unbiased if ground observations are unbiased even if the image classification is biased."
- Relative efficiency "often of the order of 2 with classification accuracy values around 50%". EU medians 1988-92: wheat 2.11, barley 2.04, maize 1.68, oil seeds 1.80, dried pulses 1.77. "An efficiency of 2 means that the accuracy obtained with a sample of 1000 segments and remote sensing is the same as ... 2000 segments without remote sensing."
- USDA "reached the cost-efficiency threshold of remote sensing with the regression estimator on Landsat-TM images in the mid-late 90s".
- A confusion-matrix alternative (Czaplewski and Catts 1992) gave "results that are very close to those of the regression estimator".

**The regression estimator (standard survey-sampling form; NASS-specific details per its FAQ).** With ground-reported acres `y` and classified acres `x` on sampled segments in stratum `h`, and `X_h` the classified mean over all segments:

```
Y_hat_h = N_h * [ ybar_h + b_h * (Xbar_h - xbar_h) ]          Var ~= (1 - r_h^2) * Var(direct expansion)
relative efficiency = 1 / (1 - r^2)
```

**Small area estimation.**

- Battese, Harter, Fuller 1988 [R via the `agridat` documentation of the data; JASA 83:28-36]: 12 north-central Iowa counties, 37 sample segments (each about one square mile, roughly 259 ha), June Enumerative Survey hectares of corn and soybeans, LANDSAT pixel counts from August-September 1978 (about 0.45 ha per pixel). Nested-error model `y_ij = b0 + b1*x1_ij + b2*x2_ij + v_i + e_ij` with county effect `v_i`. Refit reported in the documentation (outlier removed): corn hectares = 51.07 + 0.329 corn pixels - 0.135 soy pixels; county variance 140, residual variance 147.3. The predictor shrinks toward the regression line: `gamma_i = s_v^2 / (s_v^2 + s_e^2 / n_i)`.
- Erciulescu, Cruze, Nandram 2019 [A], JRSS-A 182:283-303: NASS's County Agricultural Production Survey; a hierarchical Bayesian sub-area model combining survey acreage with remote sensing, weather and administrative planted-acreage data; lower coefficients of variation than survey-only estimates; "top-down" benchmarking so that estimates satisfy the county-district-state constraint.
- Fay-Herriot (area level, standard form): `theta_c = gamma_c * direct_c + (1 - gamma_c) * x_c'beta`, `gamma_c = s_u^2 / (s_u^2 + psi_c)`.

**So what.** For the "how it could be developed further" slide: our field probabilities are exactly the kind of auxiliary variable NASS already knows how to use. Summed per segment or county they become the `x` in the regression estimator or the covariate in the county model. We are proposing an input to their machinery, not a replacement for it.

### 3e. Prediction-powered inference

**Angelopoulos, Bates, Fannjiang, Jordan, Zrnic 2023** [A] (arXiv 2301.09633; published in Science): confidence intervals for means, quantiles and regression coefficients that are valid whatever model produced the predictions; demonstrations include remote sensing.

**PPI++ (Angelopoulos, Duchi, Zrnic 2023)** [R] (arXiv 2311.01453 v2):

```
theta_lam = mean_n(Y) + lam * [ mean_N(f(X_unlabeled)) - mean_n(f(X_labeled)) ]
lam*      = Cov(Y, f) / [ (1 + n/N) * Var(f) ]          (clip to 0-1; lam = 1 is plain PPI, lam = 0 is classical)
interval  = theta_lam +/- z * sqrt( Var(Y - lam*f)/n + lam^2 * Var(f)/N )
```

- Claim: intervals that "always improve on classical intervals using only the labeled data". The guarantee is asymptotic.
- Assumption that matters: the labeled pairs are i.i.d. from the same population as the unlabeled fields.
- `ppi_py` source [R]: `ppi_mean_ci(Y, Yhat, Yhat_unlabeled, alpha=0.1, alternative="two-sided", lam=None, coord=None, w=None, w_unlabeled=None, lam_optim_mode="overall")`; sample weights supported; `ppi_distribution_label_shift_ci(...)` gives a confusion-matrix-inverse interval for class shares under label shift, the same idea as our step 2.

**Recent caution** [A]: Shirota 2026 (arXiv 2608.10356) studies when PPI stays valid for spatially dependent finite populations with non-uniform label acquisition, and reports that mean calibration alone does not guarantee valid inference for a slope. Only the abstract was read.

**What n = 150 buys (Inference, our arithmetic).** For a binary share with hard calls, effective sample size ratio = Var(Y) / Var(Y - call):

| True share | TPR | FPR | n_eff / n |
|---|---|---|---|
| 0.06 | 0.90 | 0.05 | 1.1 |
| 0.06 | 0.95 | 0.01 | 4.6 |
| 0.50 | 0.90 | 0.05 | 3.4 |
| 0.88 | 0.90 | 0.05 | 1.2 |

With a rare class and a 5% false-positive rate, the map adds almost nothing to 150 random labels: the classical SE of a 6% share from n = 150 is 0.019 (a 95% interval of plus or minus 3.8 points). Reaching a standard error of 0.3 points (5% of a 6% share) would take roughly 1,400 random labels with the good classifier (TPR 0.95, FPR 0.01) and about 6,300 with no map at all. This is why the label-based interval is honest but wide, and why the backtest (step 8) carries the accuracy claim.

### 3f. Calibration and conformal prediction with 100-300 labels

**Calibration** (scikit-learn 1.9.1 user guide [R]):

- Sigmoid: "most effective for small sample sizes or when the un-calibrated model is under-confident". It "works best if the calibration error is symmetrical", which "can be a problem for highly imbalanced classification problems".
- Isotonic: "more prone to overfitting, especially on small datasets"; performs as well or better than sigmoid "when there is enough data (greater than ~ 1000 samples)". It also "introduces ties", which can change ranking metrics.
- "Ideally, the calibrator is fit on a dataset independent of the training data." Already-fitted model: `CalibratedClassifierCV(estimator=FrozenEstimator(model))`.
- "A lower Brier loss ... does not necessarily mean a better calibrated model." Show a reliability diagram as well.

**Venn-Abers** (Vovk and Petej, UAI 2014 [A]): probability-type predictions built on isotonic regression, "guaranteed to be well calibrated" under the i.i.d. assumption only. In practice the output is a pair of probabilities whose gap widens when calibration data are scarce, which is the honest behaviour we want at this sample size. (The pair-of-probabilities detail is from memory, not from the abstract.)

**Split conformal** (Angelopoulos and Bates tutorial [R]):

```
1 - alpha  <=  P(Y in C(X))  <=  1 - alpha + 1/(n+1)                     (marginal, needs exchangeability)
coverage given the calibration set  ~  Beta(n + 1 - l, l),   l = floor((n+1) * alpha)
```

Their Table 1 (alpha = 0.1, 90% of calibration draws): calibration size needed for coverage within plus or minus epsilon is 22 (0.10), 102 (0.05), 2,491 (0.01), 9,812 (0.005). With n = 1,000 coverage is "typically between .88 and .92".

**Inference (our computation of the same Beta law, 5th to 95th percentile of realised coverage):**

| Calibration fields in the class | alpha = 0.10 | alpha = 0.05 |
|---|---|---|
| 9 | 0.72 to 0.99 | threshold infinite (everything in the set) |
| 19 | 0.77 to 0.98 | 0.85 to 1.00 |
| 30 | 0.81 to 0.97 | 0.91 to 1.00 |
| 50 | 0.83 to 0.96 | 0.91 to 0.99 |
| 100 | 0.85 to 0.95 | 0.91 to 0.98 |
| 150 | 0.86 to 0.94 | 0.92 to 0.98 |
| 300 | 0.87 to 0.93 | 0.93 to 0.97 |

**Class-conditional (Mondrian) conformal** (Ding et al., NeurIPS 2023 [R]; recipe also in the tutorial): one threshold per class, quantile level `ceil((n_y + 1)(1 - alpha)) / n_y`. A class with fewer than `1/alpha - 1` calibration examples gets an infinite threshold (9 examples needed at alpha = 0.1). With 10 examples at 90% there is about a 0.107 probability that class coverage falls below 80%. On ImageNet with about 10 examples per class the class-coverage gap was 7.7 points for classwise against 5.2 for standard; classwise wins once there are roughly 50 to 75 or more per class. With two classes and 30 or more silage labels, classwise is appropriate for us.

**Conformal risk control** (tutorial [R]): for a loss bounded by B and non-increasing in the set-size parameter, choose `lambda_hat = inf{lambda : Rhat(lambda) <= alpha - (B - alpha)/n}`; guarantees expected loss at most alpha (example: B = 1, alpha = 0.1, n = 1,000 gives a target empirical risk of 0.0991). Use it if we prefer to state "at most 10% of silage fields are confidently called grain" as a controlled risk.

**When exchangeability fails** (Barber, Candes, Ramdas, Tibshirani [R], arXiv 2202.13415):

```
coverage  >=  1 - alpha - sum_i w~_i * d_TV( R(Z), R(Z^i) ),      w~_i = w_i / (w_1 + ... + w_n + 1)
```

Unweighted split conformal on non-exchangeable data loses at most the average total-variation distance between the data and the data with point `i` swapped with the test point. They suggest larger weights for calibration points believed closer to the test point, including weights that decay with spatial distance, and note lower weights shrink the effective sample size. Weights must be fixed in advance, not data-dependent.

**What survives with 100-300 spatially clustered labels (Inference).**

- Survives: marginal coverage over fields that are exchangeable with the labeled ones (same regions, same selection process), at the precision in the table above.
- Does not survive: per-state or per-county coverage; coverage in states with no labels; any claim tighter than about plus or minus 5 points.
- Mitigations we can afford: out-of-block calibration scores; coverage reported by state with Wilson intervals; distance-weighted calibration only if labels are spread widely enough.

**Selective classification.** The conformal set already gives it: decide only when the set is a single label; report coverage (share of fields decided) with accuracy on the decided fields, each with a Wilson interval.

### 3g. Honest evaluation with small n

**Intervals for rates** (statsmodels 0.15.0 [R]): `proportion_confint(count, nobs, alpha=0.05, method=...)` with "wilson", "beta" (Clopper-Pearson; guarantees at least nominal coverage, generally conservative), "jeffreys", "agresti_coull", "normal". The default is "normal"; do not use the default near 0 or 1.

**Inference (our computation), 95% intervals:**

| Observed | Wilson | Clopper-Pearson |
|---|---|---|
| Recall 27 of 30 (0.90) | 0.74 to 0.97 | 0.74 to 0.98 |
| Recall 45 of 50 | 0.79 to 0.96 | 0.78 to 0.97 |
| Recall 90 of 100 | 0.83 to 0.95 | 0.82 to 0.95 |
| False-positive rate 6 of 120 (0.05) | 0.023 to 0.105 | 0.019 to 0.106 |
| False-positive rate 2 of 120 | 0.005 to 0.059 | 0.002 to 0.059 |
| False-positive rate 0 of 120 | 0.000 to 0.031 | 0.000 to 0.030 |
| Accuracy 135 of 150 (0.90) | 0.84 to 0.94 | 0.84 to 0.94 |
| Accuracy 270 of 300 | 0.86 to 0.93 | 0.86 to 0.93 |

**Spatial block cross-validation.**

- Roberts et al. 2017 [T], Ecography 40:913-929: random cross-validation gives "artificially low error estimates" on structured data; blocks need "to be substantially larger than the range of the spatial autocorrelation in the model residuals"; for buffered leave-one-out, a buffer where residual autocorrelation reaches zero suffices; assess dependence on the raw data and block "at least as many units as the range of autocorrelation"; blocking can force extrapolation, so check that test blocks are covered by the training range of predictors.
- Ploton et al. 2020 [A] (NASA record of the Nature Communications paper): 11.8 million trees; under standard validation a random forest appeared to explain more than half of the variation; under spatial validation its predictive power was nearly zero.
- Counterpoint to know about [X: not opened]: Wadoux et al. 2021 argue that when the validation data are a probability sample, design-based accuracy estimates are the right tool and spatial cross-validation can be too pessimistic. A NASS statistician may raise this. The safe statement is: blocked CV for model selection, design-based estimation for accuracy whenever a probability sample exists.

**Leakage checklist (Inference).**

1. Fields from the same farm, section or county in both train and test: group the folds.
2. Calibration, thresholds or conformal quantiles fitted on the test fields.
3. "Early" estimates built from full-season time series: truncate every series at the as-of date before computing features.
4. Features built from aggregates that used test labels.
5. The evaluation set reused by the autoresearch loop: the best of K runs is optimistic by up to about `sqrt(p(1-p)/n) * sqrt(2 ln K)`, that is 0.06 (n = 150, K = 20) to 0.086 (n = 150, K = 500) at 90% accuracy. Correlated experiments inflate less, but the direction is certain.
6. Same-year NASS totals used anywhere upstream of a number compared with those totals.

**Metrics that show lift over "always grain".**

| Metric | "Always grain" at 6.4% silage | Why report it |
|---|---|---|
| Accuracy | 0.936 | Only as the baseline to beat |
| Balanced accuracy = (TPR + TNR)/2 | 0.50 | Prevalence-free |
| MCC | 0 | Single number, harsh on trivial rules |
| Silage recall, silage F1 | 0, 0 | The class NASS cares about |
| PR-AUC | Equals prevalence for a random ranker | Always print the prevalence next to it; re-weight negatives to the deployment prevalence (`sample_weight`) |
| Brier skill = 1 - BS / (pi(1-pi)) | 0 | Probability quality against the base-rate forecast (reference Brier 0.060 at pi = 0.064) |

PR-AUC interval: bootstrap within class (keeps class counts) and by block (respects clustering); report the percentile interval.

**Acreage-level metrics against NASS.** Signed percent error per state; RMSE of percent errors (NASS style); counts of states below and above; coverage of our intervals; skill over persistence. Avoid correlation across states: it is dominated by state size and flatters everything.

### 3h. How NASS expresses reliability

Crop Production, September 2026 [R], "Reliability of September 1 Crop Production Forecasts":

- The measure is a root mean square error of the forecast against the final estimate over the latest 20-year period.
- Wording: "Chances are 2 out of 3" that the current corn-for-grain production forecast will not be above or below the final estimate by more than 2.7 percent; "Chances are 9 out of 10 (90 percent confidence level)" that the difference will not exceed 4.6 percent.
- **Inference:** 4.6 / 2.7 = 1.70, consistent with a t multiplier on 19 degrees of freedom (1.729 times an unrounded RMSE), not 1.645. Also inferred: the deviation is expressed as a percentage of the final estimate before squaring and averaging.

| Crop (Sept 1 forecast) | RMSE % | 90% interval % | Avg diff | Smallest | Largest | Years below final | Years above final |
|---|---|---|---|---|---|---|---|
| Corn for grain (million bushels) | 2.7 | 4.6 | 260 | 13 | 813 | 8 | 12 |
| Soybeans (million bushels) | 4.2 | 7.3 | 107 | 8 | 408 | 11 | 9 |
| Sorghum for grain (million bushels) | 10.9 | 18.8 | 22 | 2 | 64 | 8 | 12 |
| Rice (million cwt) | 2.4 | 4.2 | 4 | 1 | 13 | 11 | 9 |
| Peanuts (million pounds) | 8.0 | 13.9 | 344 | 47 | 1,461 | 10 | 10 |
| Upland cotton (thousand bales) | 7.2 | 12.4 | 917 | 2 | 2,444 | 7 | 13 |

Method notes in the same report: objective yield and farm operator surveys ran 25 August to 7 September; objective yield covers states that usually account for 75% of US production; about 7,600 producers interviewed; estimates draw on "USDA administrative acreage data, satellite imagery, objective yield data, and grower-reported data"; planted acres are revised only with special survey, administrative or remote sensing data. The 2026 corn silage cells are blank in this report: the first silage estimate comes with the annual summary.

**How to mirror it.** A slide titled "Reliability of Kernel's November silage estimate", one row per geography, columns exactly as above, plus a persistence row. State the number of state-years. If the backtest has 6 state-years, say "6", not "20".

### 3i. Benchmarking, raking, and the circularity trap

- **Top-down benchmarking is NASS practice**: official county estimates "must add up" to district and state totals (Erciulescu et al. 2019 [A]).
- **Iterative proportional fitting**: `ipfn` (MIT licence; numpy and pandas inputs; `pip install ipfn`) [R].
- **Logit-shift raking for field probabilities (Inference)**: one constant added to every field's log-odds within a region so that acres sum to the target. It is the prior-shift formula with the constant chosen to hit the total, keeps probabilities in 0-1, and preserves the ranking of fields.
- **Ratio benchmarking** for county totals: `A_county_bench = A_county * (T_state / sum of county estimates)`.

**The circularity trap, with a documented precedent.** Gallego's review [T] describes the EU's "rapid estimates of crop area changes" (MARS Activity B): the image analyst could adjust cluster labels by 10% to 30%, so "the result could be adjusted to match the a priori information of the analysis team and it is not clear that remote sensing had an influence on the final estimates of area change"; and "it was improper to speak of standard error of the estimates, because the panel of sites was not a sample in the strict sense". The same programme produced year-t estimates "by applying the estimated area change rate to official statistics for year t-1", which is the legitimate, non-circular way to use prior-year totals.

**Rules for us.**

1. Same-year NASS state totals never enter the independent estimate: not as priors, not as raking targets, not for threshold tuning.
2. Prior-year totals may enter as EM starting values (harmless: the optimum does not depend on the start) or as the base for a change estimate.
3. Any benchmarked map is labelled "benchmarked to NASS" and excluded from accuracy claims.
4. If the labeled fields are from 2025 and "last year's totals" are 2025 totals, the provided totals *are* the target. Use 2024 totals as the prior for a 2025 run.

---

## 4. Sentences that will hold up in front of NASS statisticians

- "We do not count fields. Your own CDL guidance says pixel counts need bias correction, and so do field counts. Our acreage comes from a misclassification-corrected estimator."
- "This interval comes from the labeled sample, not from the model's confidence in itself. With about 150 labeled fields it is wide, and we show it at full width."
- "This second number is model-based: it assumes a silage field looks the same in Wisconsin and in Idaho once timing is expressed in growing-degree-days. Here is the check of that assumption on a held-out state."
- "Reliability, in your format: across N state-years of backtest, the root mean square error of our November estimate against your January number is X percent. Chances are 2 out of 3 that we are within X percent. Carrying last year's number forward gives Y percent."
- "The review band covers about 90% of true silage fields on average over fields like our labeled ones. With 30 silage calibration fields the realised figure could be anywhere from 80% to 97%. It is not a per-state guarantee."
- "Prior-year totals are used only as a starting value. The benchmarked map on this slide is forced to match your totals and is not evidence of accuracy."
- "Where it fails: counties where grain is harvested as early as silage, states where silage is not a separate timing cluster, fields that were abandoned or grazed, and anything hidden by cloud in the harvest window."

---

## 5. Tables of numbers

### 5.1 US corn, Crop Production 2025 Summary (January 2026) [R]

| Thousand acres unless noted | 2023 | 2024 | 2025 |
|---|---|---|---|
| Planted, all purposes | 94,641 | 90,909 | 98,788 |
| Harvested for grain | 86,506 | 83,046 | 91,258 |
| Harvested for silage | 6,461 | 6,207 | 6,208 |
| Silage yield (tons per acre) | 20.1 | 20.2 | 21.8 |
| Silage production (thousand tons) | 129,854 | 125,590 | 135,540 |
| **Derived:** planted minus grain minus silage | 1,674 | 1,656 | 1,322 |
| **Derived:** silage share of grain plus silage | 6.95% | 6.95% | 6.37% |
| **Derived:** persistence error for silage acres | n/a | +4.1% | -0.02% |

California 2025 [R]: 420 planted, 50 harvested for grain, 365 harvested for silage (silage share of grain plus silage 88%). The silage table lists 48 states. Report approved 12 January 2026.

Other state silage rows as returned by the reader (2025, thousand acres): Wisconsin 885, New York 500, South Dakota 390, Minnesota 360, Michigan 350, Pennsylvania 315, Idaho 280, Texas 265, Iowa 250, Kansas 230, Nebraska 210. **Warning:** the Nebraska value conflicts with a press summary seen only as a search snippet (280), and the source server was unreachable for a re-check. Treat this row list as unverified and re-read the table before quoting any state other than California.

### 5.2 Corn harvested (grain), Crop Progress released 13 October 2026 [R]

| Week ending 11 Oct 2026 | This week | Last week | 5-yr average |
|---|---|---|---|
| 18 states | 33% | 23% | 39% |
| Texas | 89% | 82% | 89% |
| Kansas | 63% | 54% | 64% |
| Minnesota | 25% | 12% | 33% |
| Wisconsin | 16% | 8% | 18% |
| Iowa | 14% | 7% | 34% |

"Early is not silage" in one row: Texas grain is 89% harvested when Wisconsin's is 16%.

### 5.3 Wisconsin, week ending 13 September 2026 [T]

See section 3c. State silage harvest 32% (previous week 14%, last year 20%, five-year average 21%); districts 17% to 43%. Later weeks (54% on 20 September, 75% on 27 September) were seen only in search snippets and are not verified.

### 5.4 NASS reliability table

See section 3h.

### 5.5 Saerens et al. 2002, Table 1

See section 3a.

### 5.6 Lu, Bates, Wang 2024

See section 3d.

### 5.7 Ding et al. 2023, class-coverage gap on ImageNet (percentage points; lower is better) [R]

| Score | Avg calibration examples per class | Standard | Classwise | Clustered |
|---|---|---|---|---|
| softmax | 10 | 5.2 | 7.7 | 4.9 |
| softmax | 20 | 5.2 | 5.4 | 3.9 |
| softmax | 50 | 5.3 | 3.4 | 3.1 |
| softmax | 75 | 5.2 | 2.8 | 2.8 |
| APS | 10 | 2.6 | 7.6 | 3.0 |
| APS | 50 | 2.5 | 3.5 | 2.3 |

### 5.8 Gallego: median relative efficiency of remote sensing with the regression estimator, EU 1988-92 [T]

Wheat 2.11, barley 2.04, maize 1.68, oil seeds 1.80, dried pulses 1.77.

### 5.9 Our simulation check of the recipe formulas (pure Python, 300 replications)

Setup: 20,000 fields; one score, grain N(0,1), silage N(2.5,1); classifier calibrated at 50/50 (so TPR about 0.89 and FPR about 0.11 at the 0.5 threshold); adjusted count uses 50 silage + 100 grain class-selected labels; PPI uses 150 random labels.

| True share | Counted share bias | Adjusted count: bias, SD, mean formula SE, 95% coverage | EM: bias, SD | PPI: bias, SD, mean SE, coverage | Classical (150 random labels): SE, coverage |
|---|---|---|---|---|---|
| 0.06 | +0.093 | 0.000, 0.035, 0.037, 0.93 | 0.000, 0.002 | 0.000, 0.012, 0.013, 0.95 | 0.019, 0.93 |
| 0.215 | +0.060 | +0.001, 0.031, 0.033, 0.95 | 0.000, 0.002 | 0.000, 0.020, 0.020, 0.95 | 0.033, 0.94 |
| 0.88 | -0.081 | -0.002, 0.047, 0.048, 0.89 | 0.000, 0.002 | 0.000, 0.017, 0.017, 0.93 | 0.026, 0.94 |

- EM's tiny spread is because the simulated classifier is perfectly calibrated and the label-shift assumption holds exactly. In real data its error is dominated by calibration error and regional differences, which no formula captures. That is what the backtest is for.
- EM started from 0.5 and from 0.9 converged to the same value (difference below 1e-8).
- Weekly-progress deconvolution with detection jitter of about 5-6 days: true 0.06, 0.215, 0.88 estimated 0.068, 0.220, 0.867 (SD about 0.008 with 3,000 fields).
- Class-conditional conformal at alpha = 0.10 with 30 silage and 120 grain calibration fields: mean class coverage 0.90 for both; realised coverage 5th to 95th percentile 0.79 to 0.98 for silage and 0.85 to 0.94 for grain; 4.6% of fields received both labels.
- Logit-shift raking hit its target exactly and kept all probabilities in 0-1.

---

## 6. Method comparison

| Approach | Needs | Gives | Main assumption | Fails when | Explainable in one line | Effort tonight |
|---|---|---|---|---|---|---|
| Classify and count | Hard labels | Biased share | None stated | Always, unless prevalence happens to equal FPR/(FPR+FNR) | "We counted" | 0 h (baseline only) |
| Adjusted count / BBSE | TPR and FPR from labels | Share with interval | Features given class same in labels and target | TPR close to FPR; few labels of the majority class; regional differences | "We corrected the count for our known hit and false-alarm rates" | 0.5 h |
| Prior-shift EM | Calibrated probabilities | Share per region and corrected field probabilities | Same, plus calibration | Poor calibration; composition-dependent features | "Base rate times evidence, with the base rate learned from the region" | 1 h |
| Stratified (Olofsson) / PPI | Random sample of labels from the target | Design-based share with interval | Sampling design only | Labels hand-picked or from elsewhere; zero-error strata | "A random audit of the map" | 1-2 h (plus labeling if we draw a new sample) |
| Weekly-progress deconvolution | Detected cut dates, NASS weekly curves | Label-free share for reporting states | NASS curves accurate; curves separated | Texas-type overlap; cloud-delayed detections; states without silage progress | "NASS tells us how much silage and grain was cut each week; we solve for the mix" | 2-3 h |
| Regression estimator, small-area models | Ground survey on a probability sample | Official-grade estimates | Survey unbiased | No survey | "How NASS already does it" | Not tonight; roadmap slide |
| Class-conditional conformal, Venn-Abers | Out-of-fold calibration scores | Review band, probability interval | Exchangeability | Spatial clustering, unlabeled regions | "Nine times in ten the true answer is in the set" | 1-2 h |
| Raking / IPF | Official totals | Consistent map | Totals are right | Used as evidence of accuracy | "Forced to add up" | 0.5-1 h, last |

---

## 7. Annotated bibliography

| # | Source | Year | Level | URL | Why it matters |
|---|---|---|---|---|---|
| 1 | USDA NASS, Crop Production (September) | 2026 | [R] | https://esmis.nal.usda.gov/sites/default/release-files/796056/crop0926.txt | Reliability table and the "chances are 2 out of 3" wording; methodology; silage cells blank until January |
| 2 | USDA NASS, Crop Production 2025 Summary | 2026 | [R] | https://esmis.nal.usda.gov/sites/default/release-files/795725/cropan26.txt | Corn planted, grain, silage 2023-2025; California row |
| 3 | USDA NASS, Crop Progress (13 Oct 2026) | 2026 | [R] | https://esmis.nal.usda.gov/sites/default/release-files/796104/prog4126.txt | Grain harvest progress by state; no silage line; non-probability, about 3,600 respondents |
| 4 | USDA NASS Wisconsin, Crop Progress and Condition (14 Sep 2026) | 2026 | [T] | https://www.wispolitics.com/wp-content/uploads/WI-Crop-Progress-09-14-26.pdf | Weekly "corn harvested for silage" by district (mirror copy; the nass.usda.gov URL returned 404) |
| 5 | USDA NASS, CropScape and Cropland Data Layer FAQ | 2026 | [R] | https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php | Pixel counting biased; regression estimates; accuracy; no silage class; release dates |
| 6 | Kluger, Wang, Lobell, "Two shifts for crop mapping", RSE 262 | 2021 | [T] | https://arxiv.org/abs/2109.01246 | Prior-shift and feature-shift correction with aggregate statistics |
| 7 | Wang, Azzari, Lobell, "Crop type mapping without field-level labels", RSE 222 | 2019 | [R] | https://fse.fsi.stanford.edu/node/28551 | GDD-similar transfer over 80%; mixture clusters named with county statistics |
| 8 | Saerens, Latinne, Decaestecker, Neural Computation 14(1) | 2002 | [T] | https://dipot.ulb.ac.be/dspace/bitstream/2013/68391/1/Decaestecker_NeuralComp02.pdf | Prior-shift formula, EM, likelihood-ratio test, Table 1 |
| 9 | Lipton, Wang, Smola, BBSE, ICML | 2018 | [A] | https://arxiv.org/abs/1802.03916 | Confusion-matrix-inverse label-shift estimation |
| 10 | Alexandari, Kundaje, Shrikumar, ICML | 2020 | [A] | https://arxiv.org/abs/1901.06852 | EM needs calibration; concave likelihood |
| 11 | QuaPy documentation, methods manual (0.2.3) | 2026 | [R] | https://hlt-isti.github.io/QuaPy/manuals/methods.html | Class names, options, bootstrap intervals |
| 12 | Flor et al., BMC Public Health 20:1135 | 2020 | [R] | https://pmc.ncbi.nlm.nih.gov/articles/PMC7370479/ | Rogan-Gladen estimator; naive intervals under-cover |
| 13 | Lu, Bates, Wang, uncertainty in area estimation from remote sensing maps (v1) | 2024 | [T] | https://arxiv.org/abs/2407.13659v1 | Olofsson and PPI nearly identical for area; Iowa CDL simulation |
| 14 | `mapaccuracy` R package, `olofsson.R` | n.d. | [R] | https://www.rpkg.net/packages/mapaccuracy/R/olofsson.R | Implementation of the Olofsson 2013/2014 estimators |
| 15 | Angelopoulos et al., Prediction-powered inference | 2023 | [A] | https://arxiv.org/abs/2301.09633 | Framework |
| 16 | Angelopoulos, Duchi, Zrnic, PPI++ | 2023 | [R] | https://arxiv.org/html/2311.01453v2 | Estimator, optimal lambda, interval |
| 17 | `ppi_py` source | 2026 | [R] | https://ppi-py.readthedocs.io/en/latest/_modules/ppi_py/ppi.html | API, weights, default alpha 0.1 |
| 18 | Shirota, PPI for spatially dependent finite populations | 2026 | [A] | https://arxiv.org/abs/2608.10356 | Caution on spatial dependence |
| 19 | Angelopoulos, Bates, conformal tutorial | 2021-22 | [R] | https://ar5iv.labs.arxiv.org/html/2107.07511 | Guarantee, Beta law, class-conditional recipe, risk control, diagnostics |
| 20 | Ding et al., class-conditional conformal, NeurIPS | 2023 | [R] | https://ar5iv.labs.arxiv.org/html/2306.09335 | Minimum examples per class; coverage-gap table |
| 21 | Barber, Candes, Ramdas, Tibshirani, beyond exchangeability | 2022-23 | [R] | https://arxiv.org/html/2202.13415v5 | Coverage-gap bound; spatial weights |
| 22 | Vovk, Petej, Venn-Abers predictors, UAI | 2014 | [A] | https://arxiv.org/abs/1211.0025 | Calibration guarantee under i.i.d. |
| 23 | scikit-learn user guide, probability calibration (1.9.1) | 2026 | [R] | https://scikit-learn.org/stable/modules/calibration.html | Sigmoid for small samples; isotonic above about 1,000 |
| 24 | statsmodels `proportion_confint` (0.15.0) | 2026 | [R] | https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html | Wilson and Clopper-Pearson |
| 25 | Roberts et al., Ecography 40:913-929 | 2017 | [T] | https://www.biometrie.uni-freiburg.de/mitarbeiter/dormann/roberts-et-al-2017-ecography.pdf | Block size guidance |
| 26 | Ploton et al., Nature Communications 11:4540 (NASA record) | 2020 | [A] | https://ntrs.nasa.gov/citations/20210016998 | Random CV over half of variance, spatial CV near zero |
| 27 | Gallego, "Review of the main remote sensing methods for crop area estimates", ISPRS Archives XXXVI-8/W48 | about 2006 (year inferred from the volume; no date printed in the text) | [T] | https://www.isprs.org/proceedings/XXXVI/8-W48/65_XXXVI-8-W48.pdf | Pixel counting, regression estimator, relative efficiency, MARS Activity B |
| 28 | Battese, Harter, Fuller data and model (`agridat`) | 1988 | [R] | https://kwstat.github.io/agridat/reference/battese.survey.html | County crop areas from survey plus satellite |
| 29 | Erciulescu, Cruze, Nandram, JRSS-A 182 | 2019 | [A] | https://ideas.repec.org/a/bla/jorssa/v182y2019i1p283-303.html | NASS county model and benchmarking |
| 30 | La Rosa, Oliveira, Ghamisi, crop mapping from regional label proportions | 2022 | [R] | https://arxiv.org/html/2208.11607 | Learning from label proportions; fragile for minority classes |
| 31 | `ipfn` | n.d. | [R] | https://github.com/Dirguis/ipfn | Iterative proportional fitting in Python |

---

## 8. Sources that would not open (not used as evidence)

| Source | Reason |
|---|---|
| Olofsson et al. 2014, RSE 148:42-57 | Repository record missing, file link 403. Formulas verified through items 13 and 14 |
| Boryan et al. 2011, Geocarto 26(5) | NASS PDF link returned 404 |
| NASS report on Battese-Fuller county estimation | 404 |
| Gallego 2004, IJRS 25:3019-3047; Carfagna and Gallego 2005 | Paywalled; publisher page returned empty |
| Ploton et al. 2020 full text | Publisher redirect and repository bot wall; exact R-squared values not confirmed |
| Wadoux et al. 2021, Ecological Modelling 457:109692 | 403 |
| Stehman 2014; Lang and Reiczigel 2014 | Not attempted (search budget) |
| MAPIE documentation (Mondrian page) | 404 at the guessed URL; step 6 does not need the library |
| USDA FSA Crop Acreage Data page | Timed out |

---

## 9. Unverified leads worth ten minutes each

1. **FSA Crop Acreage Data.** From memory, FSA publishes county-level acreage reported on Form 578, updated monthly from August, and the records carry an intended-use field. If the public files separate corn intended for silage from grain, that is an in-season, non-circular, county-level aggregate: the ideal `pi_rk` for sections 3b and 3c and the ideal benchmark. Not verified.
2. **Census of Agriculture county silage acres** (every five years) as a county-level prior or Fay-Herriot covariate. Not verified.
3. **Which states publish weekly silage harvest progress.** Wisconsin is verified. Check Quick Stats for a "corn, silage, progress, pct harvested" item and list the states.
4. **NASS Crop Progress terms and definitions**: confirm "corn harvested" is grain only.
5. **Lang-Reiczigel interval** for the adjusted count, as a better-covering alternative to the delta-method interval in step 2.
6. **Harvest-date detection accuracy**: one search surfaced a 2026 IJRS paper reporting harvest detection "within 5-6 days" with Sentinel-1 VH/VV plus Sentinel-2 FAPAR, and a Planet-based study with RMSE about 5.5 days. Seen only as search summaries.

---

## 10. Open questions

1. How were the labeled fields selected, from which states and which year, and what does "silage-like" mean operationally (ground truth or proxy)?
2. Is the judged task the 2025 season (totals already public, so the provided totals are the target) or 2026 (a real forecast to be checked in January 2027)?
3. Where does the corn mask come from for a truly in-season estimate, given that the 2025 CDL was only released on 27 February 2026?
4. How should the roughly 1.3M planted acres that were neither grain nor silage in 2025 be handled so that planted = grain + silage + other reconciles?
5. Does any public source give silage acreage below state level in the same season?
