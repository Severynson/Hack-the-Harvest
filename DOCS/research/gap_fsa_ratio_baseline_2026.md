# Gap report: FSA intended-use silage ratio vs "same as last year", and what public November data imply for 2026

Team Kernel, Hack the Harvest. Written Saturday 2026-11-14 by the research agent for gap `gap_fsa_ratio_baseline_2026`.

Scope: (1) does the year-over-year change in FSA intended-use corn silage acres track NASS's state silage changes better than persistence, especially for 2024 and 2025; (2) what do the 10 November 2026 FSA file and the 2026 drought record imply for 2026 silage acres by state; (3) is the 6.6-6.9 million acre band in `nowcast.md` plausible.

How to read this: every number marked "computed" was calculated by me today from the primary files listed in section 9 (27 FSA workbooks, 11 RMA files, about 60 NASS text reports, US Drought Monitor API). Statements marked "Inference:" are my reasoning, not source facts. Nothing here comes from a search snippet alone.

---

## 0. Bottom line

1. **No. A per-state FSA ratio estimate is worse than "same as last year" in every one of the nine years 2017-2025.** State-level error (WAPE, 48 states): 2024 FSA ratio 14.4% vs persistence 11.8%; 2025 FSA ratio 15.4% (16.3% with the final file) vs persistence 15.1%; pooled 2017-2025 18.0% vs 14.6%.
2. **It got the headline swings wrong.** Texas 2025: NASS +53% (revised; +66% first estimate), FSA -16%. Texas 2024: NASS -45%, FSA +7%. Wisconsin 2025: NASS +21%, FSA +9% (right direction, 44% of the size). Of 48 state swings of 40,000 acres or more in 2019-2025, the FSA change caught 5.
3. **Why: FSA "Silage" is an insurance-aligned declaration made at certification, not a harvest record.** It covers 47% of NASS silage acres nationally (2025) and 12% or less in South Dakota, Iowa, Kansas, Nebraska, Ohio, Missouri and Illinois. RMA has zero silage-type insured acres in Kansas, Nebraska, Illinois, Missouri and Kentucky. Where coverage is 75% or more (New York, Idaho, California, Arizona, New Mexico, Vermont, Montana) the FSA ratio does work (WAPE 9.4% vs 10.5%, r = +0.49).
4. **The stronger competitor is NASS's own November "planted minus harvested for grain" residual, and it also fails.** It was revised by +1.61 million acres between November 2022 and January 2023 and by -1.15 million acres between November 2025 and January 2026. The `nowcast.md` method (residual minus last year's other fates) has a mean absolute error of 456,000 acres over 2018-2025 against 279,000 for persistence, and overshot by 875,000 acres in 2025.
5. **Nothing public in November beats persistence by much.** Best combination I could build (FSA pass-through in high-coverage states, capped by the November residual): WAPE 12.8% vs 13.8% (leave-one-year-out, 2020-2025). Knowing the *final* non-grain residual by state would cut the error to 8.9% (5.3% in 2024, 6.6% in 2025). That gap is what a field-level harvest-fate classifier can claim.
6. **2026: public numbers disagree by about 0.7 million acres.** FSA says flat (2,885,863 acres, -1.1% vs final 2025; ratio estimate 6.18M). NASS's November residual says +506,000 non-grain acres (up to 6.71M if it all goes to silage). The drought record (Colorado yield -30%, North Dakota -18%, Kansas -15%, Texas -11%, South Dakota -11%) sits in exactly the states where FSA coverage is lowest. The 6.6-6.9M band is the high scenario, not a neutral sanity band.

---

## 1. Data and method (what was actually done)

| Item | Source | What I used |
|---|---|---|
| FSA Crop Acreage Data | fsa.usda.gov FOIA reading room page (needs a browser user agent; WebFetch times out) | 27 zip/xlsx vintages: final (January) files for crop years 2016-2025; November files for 2017-2024; 2025 files of 1 Aug, 2 Sep, 1 Dec 2025 and 5 Jan 2026; 2026 files of 1 Aug, 1 Sep, 1 Oct and 5 Nov 2026 |
| FSA field used | sheet `county_data`, rows with Crop = CORN, column `Intended Use` = Silage (Forage before 2019), measure = `Planted Acres` | summed by state and county |
| NASS truth | `cropan17.txt` to `cropan26.txt` (Crop Production Annual Summary), `grst0920.txt` to `grst0926.txt` (September Grain Stocks, carries prior-year revisions) | table "Corn for Silage Area Harvested, Yield, and Production - States and United States" |
| NASS forecasts | `crop11YY.txt` (November Crop Production) 2017-2026; `crop09YY`/`crop10YY` tables "Corn Area Planted for All Purposes and Harvested for Grain - States" 2019-2026; `acrg0626.txt`; `crop0826.txt` | planted, harvested for grain, yield forecast by state |
| RMA | `sobtpu_2016.zip` to `sobtpu_2026.zip` (Summary of Business, type/practice/unit), files dated 9 Nov 2026 | commodity 0041, type 026 Silage, net reported acres, plans YP/RP/RPHPE/APH/area plans |
| Drought | US Drought Monitor data services API, state statistics, weekly maps 1 Jun to 10 Nov for 2022, 2024, 2025, 2026 (26 states); NASS Crop Progress `prog3626.txt`, `prog3625.txt`, `prog3622.txt` | percent of state area in D1+/D2+/D3+; corn condition |

Definitions used throughout:

- `S_t(s)`: NASS corn silage area harvested, state `s`, year `t`, 1,000 acres. "Truth" = the first January estimate. "Base" `S_{t-1}` = the prior-year value printed in the same January report (already revised).
- `F_t(s)`: FSA corn planted acres with intended use Silage. Real-time version uses the November file for year `t` (the 1 Dec file for 2025, because the October and November 2025 files were never released) over the final file for `t-1`.
- Persistence: `S_t = S_{t-1}`.
- FSA ratio: `S_t = S_{t-1} * clip(F_t / F_{t-1}, 0.5, 2.0)`; falls back to persistence if `F_{t-1} < 500` acres.
- FSA additive: `S_t = S_{t-1} + b * (F_t - F_{t-1}) / 1000`, `b = 1` or fitted leave-one-year-out.
- Coverage: `F_{t-1} / (1000 * S_{t-1})`.
- NASS residual: `R_t(s) = P_t(s) - G_t(s)` = planted for all purposes minus harvested for grain, as published by November of year `t` (planted from the September or October table, grain from the 1 November forecast where published). Prior-year `R_{t-1}` from the 30 September Grain Stocks revision.
- WAPE = `sum_s |pred - truth| / sum_s truth` over 48 states. I use it instead of MAPE because NASS rounds small states to 1,000 acres.
- Sign agreement: among states with base of 50,000 acres or more whose NASS silage moved 5% or more, share where the predictor moved the same way.

Cross-checks that my parsing is right (two independent sources each):

- FSA 10 Nov 2026 file: corn Silage 2,885,863 acres in 1,409 counties; Wisconsin 429,690; New York 495,735; California 282,473. Identical to the independent pass recorded in `labels.verification.md`.
- FSA August 2026 file: corn planted plus failed, all uses = 94,764,645 acres. DTN's 12 Aug 2026 article reports FSA corn at 94.765 million acres.
- RMA 2025 Wisconsin silage-type acres 193,376 and 481 counties with silage-type acres in 2026: both match `labels.verification.md`.
- US Drought Monitor Kansas, map of 1 Sep 2026: 27.76% no drought, 52.39% D1+. K-State eUpdate of 10 Sep 2026: "only 28% of the state is listed as drought-free, with around 53% in the moderate-to-severe drought categories."
- NASS Colorado yield forecast 97 bu/ac on 1 Sep 2026 against 133 in 2025: repeated in the Successful Farming story reprinted by The Prowers Journal on 19 Oct 2026.

---

## 2. The FSA silage series: size, timing, quirks

### 2.1 National totals (computed)

| Crop year | FSA silage-intended, final file (acres) | FSA November file | FSA / NASS | FSA yoy | NASS silage, first Jan estimate (1,000 ac) | NASS latest revision | NASS yoy |
|---|---|---|---|---|---|---|---|
| 2016 | 2,660,075 | | 43.0% | | 6,186 | 6,206 | |
| 2017 | 2,672,847 | 2,667,894 | 41.5% | +0.5% | 6,434 | 6,385 | +4.0% |
| 2018 | 2,789,769 | 2,782,295 | 45.6% | +4.4% | 6,113 | 6,120 | -4.3% |
| 2019 | 2,578,805 | 2,547,231 | 39.1% | -7.6% | 6,587 | 6,615 | +7.6% |
| 2020 | 2,831,376 | 2,758,863 | 42.1% | +9.8% | 6,719 | 6,711 | +1.6% |
| 2021 | 2,778,667 | 2,776,606 | 42.9% | -1.9% | 6,481 | 6,451 | -3.4% |
| 2022 | 2,642,901 | 2,638,919 | 38.5% | -4.9% | 6,860 | 6,851 | +6.4% |
| 2023 | 2,842,347 | 2,835,792 | 43.9% | +7.5% | 6,471 | 6,461 | -5.5% |
| 2024 | 2,785,954 | 2,780,809 | 45.7% | -2.0% | 6,100 | 6,207 | -5.6% |
| 2025 | 2,919,232 | none (1 Dec file: 2,885,058) | 47.0% | +4.8% | 6,208 | 6,187 | +0.0% |
| 2026 | | 2,885,863 (as of 5 Nov) | | -1.1% vs final 2025 | not published | | |

- National year-over-year changes are **negatively** correlated: r = -0.49 over 2017-2025 (n = 9), -0.25 without the 2019 relabel year, -0.18 for 2020-2025. Same sign in 5 of 9 years, and one of those five is 2025 where NASS moved by 1,000 acres.
- RMA silage-type insured acres (1.02M in 2016 to 1.24M in 2026, 15-19% of NASS) behave the same way: r = -0.63 against NASS, same sign in 3 of 9 years.
- Inference: both administrative series follow corn plantings and program enrollment. Realised silage area follows September conditions: a dairy or feedlot needs a tonnage, so in a high-yield year fewer acres fill the bunker and in a poor year more acres are chopped, plus salvage. An intention declared by 15 July cannot see that.

### 2.2 Vintages and dates

- The FSA page labels 2025 and 2026 files by **release date**, not data date. Workbook headers and file names give the data dates: 2026 releases of 12 Aug, 11 Sep, 9 Oct and 10 Nov carry data as of 1 Aug, 1 Sep, 1 Oct and **5 Nov 2026**. A 10 Dec 2026 release is scheduled.
- 2026 within-season path: 2,763,580 (1 Aug) -> 2,845,627 (1 Sep) -> 2,866,666 (1 Oct) -> 2,885,863 (5 Nov).
- November-to-final growth is small in normal years: +0.2% in 2022, 2023 and 2024.
- **There is no October or November 2025 file.** The FSA page states both "were not released due to the Government Shutdown". The like-for-like comparison for November 2026 is therefore ambiguous: +0.03% against the 1 Dec 2025 file, -1.14% against the 5 Jan 2026 final file.
- 2025 was not monotonic: 2,934,931 (2 Sep) -> 2,885,058 (1 Dec) -> 2,919,232 (5 Jan). Kansas alone went from 13,249 acres in the September file to 294 in the December and January files, so records are reclassified late.
- Label change: files through crop year 2018 call the use "Forage"; from 2019 it is "Silage". FSA Notice CP-749 (29 Oct 2018): "Effective with the 2019 program year, corn with an intended use of Forage (FG), for purposes of acreage reporting and NAP, has been replaced with corn with an intended use of Silage (SG), regardless of the type. This allows for improved data matching between FSA and RMA".
- FSA definition (handbook 2-CP, Exhibit 11): Silage = "Intended for use as food for livestock, preserved through fermentation." Grain = "Intended to be harvested as the small, hard seed of a food plant".

### 2.3 Coverage by state (computed; mean of FSA final / NASS, 2019-2025)

| Class | States (NASS 2025 revised silage, 1,000 ac; mean coverage) |
|---|---|
| High, 75% or more | Montana (57; 115%), Arizona (50; 101%), Idaho (280; 100%), New York (495; 94%), New Mexico (59; 94%), Vermont (84; 92%), Washington (99; 85%), California (370; 82%) |
| Middle, 35-75% | North Dakota (170; 70%), Texas (245; 57%, range 48-97%), Wisconsin (885; 49%) |
| Low, under 35% | Colorado (200; 30%), Kentucky (65; 28%), Michigan (340; 25%), Pennsylvania (315; 24%), Indiana (110; 20%), Minnesota (360; 16%), Virginia (95; 16%), Nebraska (220; 12%), Illinois (90; 11%), Iowa (250; 10%), South Dakota (390; 8%), Ohio (200; 8%), Missouri (100; 8%), Kansas (230; 7%, 0.1% in 2025) |

The low class holds about 3.35 million of the 6.4 million acres.

### 2.4 Why coverage is low exactly where switching happens

- The FSA silage code was aligned with RMA's type list in 2019 (CP-749 above). Whether corn can be insured as silage is set county by county: "In grain only or silage only counties, there is only one choice. In Dual Counties ... the insured must decide which acres will be insured as grain, and which will be insured as silage" (AgriSompo, 23 Aug 2023).
- RMA Summary of Business, files of 9 Nov 2026 (computed): corn silage-type (code 026) net insured acres are **zero** in Kansas, Nebraska, Illinois, Missouri, Kentucky, Tennessee, Arkansas, Mississippi, Louisiana, South Carolina, Delaware and Maine in 2026, and were zero in Kansas, Nebraska, Illinois, Missouri and Kentucky in every year 2022-2026. Those five states had 705,000 NASS silage acres in 2025.
- Corn insured as grain can still be chopped: "If corn insured as grain will be harvested for silage, an appraisal must be completed before chopping begins" (fnbsf.com "Insuring Your Success" crop insurance blog, 7 Aug 2026); NDSU Extension gives the same instruction. The acreage record keeps saying grain.
- Not opened: the FSA handbook paragraph that a search result quotes as saying the intended use "shall not be revised" once certified (2-CP; the PDF timed out). Treat that wording as unverified.

---

## 3. Backtest: FSA ratio vs "same as last year"

### 3.1 State-level error by year (computed; WAPE %, 48 states, truth = first January estimate)

| Year | Persistence | FSA ratio (Nov file) | FSA ratio (final file) | FSA additive, b = 1 | FSA ratio only where coverage 50%+ | NASS Nov residual, ratio | NASS Nov residual, additive | Oracle: final residual ratio |
|---|---|---|---|---|---|---|---|---|
| 2017 | 13.2 | 14.8 | 14.8 | 17.3 | 12.2 | | | 3.6 |
| 2018 | 19.6 | 24.8 | 24.1 | 19.3 | 19.0 | | | 5.2 |
| 2019 | 16.5 | 27.2 | 27.0 | 18.9 | 19.3 | 14.3 | 15.7 | 9.4 |
| 2020 | 12.8 | 17.8 | 19.4 | 11.9 | 10.8 | 17.3 | 23.7 | 12.1 |
| 2021 | 16.0 | 17.7 | 17.6 | 16.3 | 16.9 | 16.2 | 20.3 | 9.7 |
| 2022 | 13.6 | 14.9 | 14.9 | 12.5 | 12.1 | 18.0 | 21.8 | 11.2 |
| 2023 | 13.4 | 15.5 | 15.7 | 12.3 | 12.4 | 12.7 | 22.9 | 7.7 |
| **2024** | **11.8** | **14.4** | 14.3 | 12.1 | 12.2 | 11.2 | 12.9 | 5.3 |
| **2025** | **15.1** | **15.4** (1 Dec file) | 16.3 | 14.9 | 14.8 | 19.0 | 22.0 | 6.6 |
| 2017-2025 | 14.6 | 18.0 | 18.2 | 15.0 | 14.4 | | | 8.0 |
| 2019-2025 | 14.2 | 17.6 | 17.9 | 14.1 | 14.1 | 15.6 | 20.0 | 8.9 |
| 2024-2025 | 13.4 | 14.9 | 15.3 | 13.5 | 13.5 | 15.2 | 17.4 | 5.9 |

Against the revised truth (next January or September revision) the picture is the same: 2024-2025 persistence 13.2%, FSA ratio 14.9%, FSA additive 13.3%.

### 3.2 US-total error of the summed state predictions (computed; 1,000 acres)

| Year | NASS first estimate | Persistence | FSA ratio (Nov) | FSA additive | NASS Nov residual ratio | Oracle final residual ratio |
|---|---|---|---|---|---|---|
| 2017 | 6,434 | -248 | +115 | +226 | | -14 |
| 2018 | 6,113 | +272 | +893 | +382 | | +170 |
| 2019 | 6,587 | -467 | -919 | -710 | +95 | +29 |
| 2020 | 6,719 | -104 | +691 | +76 | +38 | +27 |
| 2021 | 6,481 | +230 | +251 | +175 | +231 | -29 |
| 2022 | 6,860 | -415 | -730 | -555 | -494 | +205 |
| 2023 | 6,471 | +380 | +729 | +573 | -385 | -264 |
| 2024 | 6,100 | +361 | +303 | +299 | +312 | +44 |
| 2025 | 6,208 | -1 | +33 | +98 | +606 | -167 |
| MAE 2019-2025 | | 280 | 522 | 355 | 309 | 110 |

### 3.3 Direction (computed; states with base of 50,000 acres or more)

| Period | n | Pearson r (FSA % change vs NASS % change) | Spearman | Same direction when NASS moved 5%+ |
|---|---|---|---|---|
| 2017-2025 | 225 | +0.16 | +0.22 | 94 of 159 (59%) |
| 2020-2025 | 150 | +0.10 | +0.24 | 63 of 105 (60%) |
| 2024 | 25 | +0.18 | +0.17 | 10 of 19 (53%) |
| 2025 | 25 | +0.17 | +0.32 | 12 of 15 (80%) |

By coverage class, pooled 2019-2025:

| Coverage class | State-years | NASS acres per year (1,000) | WAPE persistence | WAPE FSA ratio | WAPE FSA additive | r | Same direction |
|---|---|---|---|---|---|---|---|
| 75% or more | 83 | 1,595 | 10.5% | 9.4% | 9.3% | +0.49 | 37 of 49 (76%) |
| 35-75% | 56 | 1,448 | 14.8% | 17.5% | 15.9% | +0.09 | 21 of 40 |
| under 35% | 111 | 3,351 | 15.5% | 21.4% | 15.5% | 0.00 | 46 of 82 (56%) |

### 3.4 The named swings (computed)

| Year, state | NASS (1,000 ac) | FSA silage-intended | FSA ratio prediction (error) | Persistence error | NASS Nov residual change / final residual change |
|---|---|---|---|---|---|
| 2025 Wisconsin | 730 -> 885 (+21.2%) | 417,112 -> 455,855 (+9.3%) | 798 (-87) | -155 | +190 / +140 |
| 2025 Texas | 160 -> 265 (+65.6%); revised 245 (+53.1%) | 149,807 -> 125,726 (-16.1%) | 134 (-131) | -105 | +90 / +50 |
| 2024 Texas | 280 -> 155 (-44.6%) | 139,335 -> 149,453 (+7.3%) | 300 (+145) | +125 | +20 / -110 |
| 2024 South Dakota | 520 -> 410 (-21.2%) | 38,240 -> 35,686 (-6.7%) | 485 (+75) | +110 | -40 / -170 |
| 2024 North Dakota | 200 -> 260 (+30.0%) | 138,256 -> 121,400 (-12.2%) | 176 (-84) | -60 | +60 / +60 |
| 2025 Iowa | 340 -> 250 (-26.5%) | 32,964 -> 28,665 (-13.0%) | 296 (+46) | +90 | +100 / -100 |
| 2025 Kansas | 310 -> 230 (-25.8%) | 19,700 -> 294 (-98.5%) | 155 (-75) | +80 | +60 / -150 |
| 2025 Nebraska | 280 -> 210 (-25.0%) | 32,577 -> 24,836 (-23.8%) | 213 (+3) | +70 | -10 / -160 |
| 2025 New York | 455 -> 500 (+9.9%) | 443,656 -> 471,564 (+6.3%) | 484 (-16) | -45 | -50 / +55 |
| 2022 Kansas | 240 -> 420 (+75.0%) | 23,990 -> 26,290 (+9.6%) | 263 (-157) | -180 | +50 / +760 |
| 2022 Nebraska | 260 -> 430 (+65.4%) | 36,632 -> 25,107 (-31.5%) | 178 (-252) | -170 | -40 / +440 |

Largest swings, 2019-2025 (NASS state change of 40,000 acres or more; "seen" = same sign and at least a quarter of the size): 48 swings; FSA saw 5 (New York 2020, California 2020, Colorado 2021, Idaho 2022, New York 2025; Wisconsin 2025 misses the threshold by 0.05 thousand acres); the NASS November residual saw 28; the final residual saw 44.

### 3.5 Is there any signal at all in FSA?

- A fitted pass-through helps a little. Leave-one-year-out on 2020-2025 (the stable "Silage" label period), `S_t = S_{t-1} + b * dF`: `b` = 0.46 to 0.73, WAPE 13.2% vs 13.8% for persistence.
- Including 2019 destroys it (slopes near 0, WAPE 14.4% vs 14.2%), because the relabel year moves FSA and NASS in opposite directions.
- Verdict: usable as a prior in the eight high-coverage states; noise elsewhere.

---

## 4. The other public competitors

### 4.1 RMA silage-type insured acres (computed)

- State backtest 2017-2025: RMA ratio WAPE 18.8% vs persistence 14.6%; RMA additive 14.5%. r = +0.15 on 178 state-years.
- 2026: 1,242,549 acres, +3.5% on 2025. Wisconsin -11.3%, New York +6.2%, California -11.7%, Idaho +18.8%, Texas -19.7%, Colorado +44.1%, North Dakota +3.6%, Montana +55.2%, Arizona +41.1%.
- Caveat: all RMA years were read from files dated 9 Nov 2026, so this is not a true real-time vintage test.

### 4.2 NASS's own November residual (computed)

NASS does not forecast silage before January. In the 10 Nov 2026 Crop Production the 2026 cell for "Corn for silage" is blank, under the note "Blank data cells indicate estimation period has not yet begun". It does publish planted and harvested-for-grain area, so anyone can compute the non-grain residual.

| Year | Nov planted | Nov harvested for grain | Nov residual | Final residual (Jan) | Revision Nov -> Jan | NASS silage (first) | Silage / final residual | Other fates (final residual - silage) |
|---|---|---|---|---|---|---|---|---|
| 2017 | 90,429 | 83,119 | 7,310 | 7,464 | +154 | 6,434 | 0.862 | 1,030 |
| 2018 | 89,140 | 81,767 | 7,373 | 7,389 | +16 | 6,113 | 0.827 | 1,276 |
| 2019 | 89,942 | 81,815 | 8,127 | 8,218 | +91 | 6,587 | 0.802 | 1,631 |
| 2020 | 90,978 | 82,527 | 8,451 | 8,352 | -99 | 6,719 | 0.804 | 1,633 |
| 2021 | 93,304 | 85,085 | 8,219 | 7,969 | -250 | 6,481 | 0.813 | 1,488 |
| 2022 | 88,608 | 80,844 | 7,764 | 9,372 | **+1,608** | 6,860 | 0.732 | 2,512 |
| 2023 | 94,868 | 87,096 | 7,772 | 8,128 | +356 | 6,471 | 0.796 | 1,657 |
| 2024 | 90,748 | 82,710 | 8,038 | 7,698 | -340 | 6,100 | 0.792 | 1,598 |
| 2025 | 98,728 | 90,047 | 8,681 | 7,530 | **-1,151** | 6,208 | 0.824 | 1,322 |
| 2026 | 96,777 | 88,506 | 8,271 | pending | | | | |

(1,000 acres. After the 30 Sep 2026 revision, 2025 is planted 98,713, grain 90,948, silage 6,187, residual 7,765, other fates 1,578.)

- November-to-January revision of the residual: mean absolute 452,000 acres, root mean square 688,000.
- First silage estimate divided by the November residual: 0.715 to 0.884, mean 0.810, standard deviation 0.054. Applied to 8,271: mean 6.70M, one standard deviation 6.25-7.15M, historical min-max 5.92-7.31M.
- The `nowcast.md` arithmetic (November residual minus last year's other fates) backtested:

| Year | Prediction | Error | Persistence error |
|---|---|---|---|
| 2018 | 6,343 | +230 | +272 |
| 2019 | 6,851 | +264 | -467 |
| 2020 | 6,820 | +101 | -104 |
| 2021 | 6,586 | +105 | +230 |
| 2022 | 6,276 | -584 | -415 |
| 2023 | 5,260 | -1,211 | +380 |
| 2024 | 6,381 | +281 | +361 |
| 2025 | 7,083 | +875 | -1 |
| MAE | | 456 | 279 |

- "Other fates" ranged from 1.03M to 2.51M in 2017-2025, not 1.3-1.7M.
- State level: residual methods are worse than persistence (section 3.1). A fitted pass-through of the residual change is only 0.10-0.25 and ties persistence (14.1% vs 14.2%).
- One residual rule does help: **cap** last year's silage at this year's November residual, `min(S_{t-1}, R_t)`. WAPE 13.7% vs 14.2% (2019-2025), better in 5 of 7 years. It is not a hard bound in November (final silage exceeded the November residual in 38 of 336 state-years) but it is one in January (1 of 336).

### 4.3 The best public baseline, and the ceiling

| Method (leave-one-year-out where fitted) | WAPE 2020-2025 |
|---|---|
| Persistence | 13.8% |
| Residual cap | 13.1% |
| FSA additive, fitted pass-through | 13.2% |
| FSA pass-through + residual cap | 12.9% |
| FSA pass-through only where coverage 50%+ (slope 0.72-0.95) + residual cap | **12.8%** |
| Oracle: `S_{t-1} * R_t(final) / R_{t-1}(final)` | 8.9% |

The oracle uses the January planted and grain-harvested areas, which NASS publishes on the same day as silage, so it is not available in November. It shows how much of the state-level silage change is explained once you know how many planted acres did not go to grain: US mean absolute error falls from 280,000 to 110,000 acres. The remaining error is the split between silage and abandonment (silage is 73-86% of the final residual).

### 4.4 The drought trigger (computed)

- Linear relationship between the 1 November yield forecast change and the silage change is weak (r = -0.13, 147 state-years; a fitted rule ties persistence at 14.2%).
- The tail is not weak. State-years 2019-2025 with base of 50,000 acres or more and a November yield forecast 10% or more below the prior year: 13 cases, silage rose in 10 (77%), mean +24.5%, median +9.9%.

| Case | Yield forecast vs prior year | NASS silage | NASS Nov residual change |
|---|---|---|---|
| 2021 North Dakota | -22.3% | 145 -> 250 (+72%) | +110 |
| 2021 South Dakota | -15.4% | 360 -> 500 (+39%) | 0 |
| 2022 Kansas | -17.3% | 240 -> 420 (+75%) | +50 |
| 2022 Nebraska | -13.4% | 260 -> 430 (+65%) | -40 |
| 2022 Texas | -26.6% | 250 -> 260 (+4%) | +70 |
| 2019 Illinois | -14.8% | 100 -> 170 (+70%) | +100 |
| 2019 Indiana | -12.7% | 100 -> 110 (+10%) | +50 |
| 2019 Ohio | -12.8% | 160 -> 170 (+6%) | +10 |
| 2025 New York | -20.1% | 455 -> 500 (+10%) | -50 |
| 2022 Pennsylvania | -16.0% | 300 -> 305 (+2%) | -10 |
| 2024 Virginia | -39.5% | 100 -> 95 (-5%) | -15 |
| 2024 Pennsylvania | -11.5% | 345 -> 320 (-7%) | -45 |
| 2022 Kentucky | -20.3% | 90 -> 70 (-22%) | 0 |

- The five Plains cases sum to +605,000 acres on a base of 1,255,000 (+48%). Eastern cases show no increase.
- Older precedent: Darrel Good (farmdoc daily, 4 Sep 2012) wrote that silage acreage "tends to spike in years of dry weather", rising "by 1.3 million acres in 1980, 2.3 million acres in 1988".
- 2022 is the cleanest "late switcher" year. Kansas +180,000 and Nebraska +170,000 silage acres; FSA intended use said +9.6% and -31.5%; NASS's November residual said +50,000 and -40,000; the January residual said +760,000 and +440,000.

---

## 5. What the November 2026 data imply

### 5.1 The 2026 drought record (two independent sources per claim)

US Drought Monitor, percent of **state area** (not corn area) in D2 or worse, mean of weekly maps 1 Jul - 30 Sep (computed from the API):

| State | 2026 D1+ / D2+ / D3+ | 2025 D2+ | 2022 D2+ | 2026 peak D2+ / D3+ |
|---|---|---|---|---|
| Colorado | 89.3 / 75.9 / 45.5 | 34.9 | 26.2 | 81.6 / 50.8 |
| Oklahoma | 78.5 / 61.9 / 33.6 | 0.0 | 76.4 | 92.4 / 55.4 |
| Nebraska | 70.0 / 46.2 / 15.3 | 4.7 | 54.0 | 61.8 / 25.8 |
| North Carolina | 73.5 / 37.9 / 13.3 | 0.0 | 1.1 | 82.3 / 49.8 |
| South Carolina | 72.9 / 40.7 / 14.4 | 0.0 | 0.6 | 58.0 / 25.4 |
| Minnesota | 64.8 / 33.6 / 1.8 | 0.4 | 2.1 | 52.5 / 4.6 |
| South Dakota | 66.1 / 28.8 / 7.4 | 0.3 | 9.2 | 38.7 / 13.8 |
| North Dakota | 52.4 / 27.3 / 5.8 | 0.0 | 1.4 | 46.0 / 13.7 |
| Texas | 49.9 / 24.9 / 9.4 | 13.0 | 63.4 | 67.8 / 26.4 |
| Wisconsin | 47.1 / 24.3 / 8.3 | 0.0 | 1.1 | 45.4 / 20.3 |
| Kansas | 39.4 / 16.6 / 0.2 | 0.5 | 51.9 | 32.7 / 1.8 |
| Idaho | 75.3 / 55.6 / 34.4 | 45.7 | 16.7 | 61.0 / 37.4 |
| Iowa, Illinois, Indiana, Ohio | D2+ 0.3 / 0.0 / 0.0 / 0.0 | 0.0 / 5.5 / 2.0 / 4.3 | | |
| New York, California, Pennsylvania, Michigan | D2+ 0.4 / 0.7 / 2.8 / 2.3 | 1.2 / 22.4 / 0.6 / 2.1 | | |

NASS corn condition, week ending 6 Sep 2026, percent poor plus very poor (2025 in brackets): North Carolina 55 (5), Colorado 52 (8), North Dakota 48 (8), Kansas 37 (12), Texas 35 (8), South Dakota 26 (7), Nebraska 17 (6), Minnesota 14 (8), Wisconsin 14 (5), Illinois 13 (17), Iowa 6 (5). Eighteen states: 17% poor or very poor and 56% good or excellent, against 9% and 68% in 2025 and 19% and 54% on 28 Aug 2022.

NASS 1 November 2026 yield forecast against 2025: United States 179.6 vs 186.5 bu/ac (-3.7%); Colorado 93 vs 133 (-30.1%); South Carolina -29.7%; Oklahoma -23.8%; North Carolina -18.8%; North Dakota 129 vs 158 (-18.4%); Kansas 124 vs 145 (-14.5%); Texas 120 vs 135 (-11.1%); South Dakota 153 vs 171 (-10.5%); Nebraska -5.2%; Wisconsin -2.1%; Minnesota +1.5%; Iowa +4.3%; Ohio +8.7%; Pennsylvania +10.6%; New York +15.7%.

Field reports of switching in 2026:

- Southeast Colorado (McClave): a grower switched about 95% of his corn acreage to silage (paraphrase), expecting under 50 bu/ac against a usual 200-250; direct quote: "we maybe got two tons an acre on some of those fields" (Successful Farming story reprinted by The Prowers Journal, 19 Oct 2026). One anecdote, not a regional statistic.
- North Dakota: "The 2026 hot dry weather in North Dakota is forcing some producers to decide whether to harvest their corn for grain or for silage" (NDSU Extension EC1343, revised August 2026; repeated by Grain Journal, 25 Aug 2026).
- Nebraska: "Drought is forcing difficult decisions in corn fields across Nebraska" (UNL Beef, 4 Aug 2026).
- South Dakota, southwest Minnesota, northwest Iowa: "crop maturity is advancing more quickly than normal"; many producers expect to chop earlier than usual (fnbsf.com crop insurance blog, 7 Aug 2026).
- Kansas: forage supplies "mostly adequate, although some regions of the state are short" (K-State eUpdate, 10 Sep 2026).

### 5.2 State table for 2026 (computed)

S25 = NASS 2025 silage as revised 30 Sep 2026. dR = change in NASS planted-minus-grain residual, November 2026 forecast against revised 2025. Last column is my inference.

| State | S25 (1,000 ac) | FSA coverage | FSA 2025 final -> Nov 2026 | RMA 2025 -> 2026 | dR (1,000 ac) | Nov yield vs 2025 | D2+ 2026 (2025) | Inference: likely direction |
|---|---|---|---|---|---|---|---|---|
| Wisconsin | 885 | 52% | 458,212 -> 429,690 (-6.2%) | -11.3% | -40 | -2.1% | 24.3 (0.0) | Flat to down; intentions and residual both down, drought salvage is the upside risk |
| New York | 495 | 95% | 472,325 -> 495,735 (+5.0%) | +6.2% | -10 | +15.7% | 0.4 (1.2) | Up 3-5%; residual caps it near 525 |
| South Dakota | 390 | 11% | 41,957 -> 51,700 (+23.2%) | -1.9% | +160 | -10.5% | 28.8 (0.3) | Up; drought trigger met |
| California | 370 | 85% | 312,813 -> 282,473 (-9.7%) | -11.7% | -30 | n/a | 0.7 (22.4) | Down 7-10%; planted 450 -> 395, residual cap 345 |
| Minnesota | 360 | 18% | +1.2% | -15.3% | +40 | +1.5% | 33.6 (0.4) | Flat to slightly up |
| Michigan | 340 | 26% | +0.6% | -1.7% | -20 | -4.5% | 2.3 (2.1) | Flat |
| Pennsylvania | 315 | 30% | +1.6% | -18.8% | -25 | +10.6% | 2.8 (0.6) | Flat to down |
| Idaho | 280 | 104% | 292,581 -> 286,693 (-2.0%) | +18.8% | -10 | -3.3% | 55.6 (45.7) | Flat to down; residual cap 275 |
| Iowa | 250 | 12% | -3.9% | -10.7% | +50 | +4.3% | 0.3 (0.0) | Flat |
| Texas | 245 | 52% | 126,208 -> 117,807 (-6.7%) | -19.7% | +20 | -11.1% | 24.9 (13.0) | Uncertain; intentions down, drought trigger met; FSA had the wrong sign in 2024 and 2025 |
| Kansas | 230 | 0% (7% mean) | 294 -> 6,176 | zero both years | +150 | -14.5% | 16.6 (0.5) | Up; drought trigger met; invisible to FSA and RMA |
| Nebraska | 220 | 11% | 24,836 -> 29,518 (+18.9%) | zero both years | +180 | -5.2% | 46.2 (4.7) | Up; largest residual increase |
| Colorado | 200 | 33% | 66,112 -> 47,369 (-28.3%) | +44.1% | +30 | -30.1% | 75.9 (34.9) | Most uncertain; intentions cut (Weld County 35,701 -> 19,649), salvage chopping reported |
| Ohio | 200 | 8% | +9.1% | +8.1% | -30 | +8.7% | 0.0 (4.3) | Flat to down |
| North Dakota | 170 | 70% | 118,799 -> 121,194 (+2.0%) | +3.6% | +90 | -18.4% | 27.3 (0.0) | Up; drought trigger met |
| Illinois | 90 | 10% | -36.3% | zero | -100 | -6.5% | 0.0 (5.5) | Down |

Other 2026 signals in the FSA file: corn prevented planting in Colorado 282,325 acres (79,530 in 2025); Stanislaus County, California 28,469 -> 12,469; Montana +46% (Valley County 2,714 -> 13,123).

States where the November residual is already below last year's silage, so silage must fall unless NASS cuts grain area: California (370 vs 345), Idaho (280 vs 275), Washington (99 vs 85), Arizona (50 vs 49), Nevada (24 vs 15). Nearly binding: Wisconsin 98%, Utah 98%, Michigan 97%, New York 94%, Pennsylvania 93%.

### 5.3 What each public method says about the US total for 2026 (computed; 1,000 acres; 2025 revised = 6,187)

| Method | 2026 implied | vs 2025 | Backtest record |
|---|---|---|---|
| Best public baseline (FSA pass-through + residual cap) | 6,143 | -0.7% | WAPE 12.8-12.9% (2020-2025) |
| FSA additive, pass-through 1.0 | 6,154 | -0.5% | WAPE 14.1% |
| FSA per-state ratio | 6,180 | -0.1% | WAPE 17.6%, worse than persistence every year |
| Persistence | 6,187 | 0.0% | WAPE 14.2%, US MAE 280 |
| Yield rule, fitted slope | 6,215 | +0.5% | ties persistence |
| NASS residual, half pass-through | 6,440 | +4.1% | WAPE 15.6% |
| NASS residual, per-state ratio | 6,547 | +5.8% | WAPE 15.6% |
| November residual x mean historical share (0.810) | 6,703 | +8.3% | share ranged 0.715-0.884 |
| NASS residual, full pass-through | 6,709 | +8.4% | WAPE 20.0%, US MAE 446 |
| `nowcast.md` band (residual minus 1.3-1.7M other fates) | 6,600-6,900 | +7% to +12% | MAE 456; +875 in 2025, -584 in 2022 |

Inference, as scenarios rather than a point:

- **A. Intentions only** (FSA, RMA, residual cap): 6.14-6.18M. Sees none of the Plains switching.
- **B. Statistical pass-through** (residual slope 0.10-0.25, yield rule): 6.2-6.3M.
- **C. Drought analogs applied to the five trigger states** (Colorado, North Dakota, Kansas, Texas, South Dakota; base 1,235,000 acres): median analog +9.9% gives 6.31M; mean analog +24.5% gives 6.49M; Plains-only analog +48% gives 6.78M.
- **D. Full residual pass-through**: 6.71M.

So public November information brackets 2026 corn silage between about 6.15M and 6.8M acres, a spread of 0.65M (about 10%). A defensible central statement is 6.3-6.5M with the Plains carrying the uncertainty. The 6.6-6.9M band needs 2021/2022-scale switching in every Plains drought state; it is the high case.

### 5.4 Where switching should appear

Inference: South Dakota, Nebraska, Kansas, North Dakota, eastern Colorado, the Texas and Oklahoma Panhandles. Evidence: NASS's own November residual rises by 630,000 acres in the first five plus Texas; yield forecasts are 10-30% below 2025 in five of them; FSA coverage there is 0-33% except North Dakota (70%) and Texas (52%); RMA silage type does not exist in Kansas and Nebraska.

---

## 6. What this means for Kernel

**Opening story.** Do not say nothing shows silage before January. Say: three public numbers exist in November (FSA intended use, 2.89M acres; RMA silage-type insurance, 1.24M; NASS's planted-minus-grain residual, 8.27M) and none of them beats "same as last year" at state level. FSA is a July intention that covers under half the acres. NASS's own residual moved 1.6 million acres between November 2022 and January 2023 and 1.15 million between November 2025 and January 2026. The missing measurement is what happened to each field in September and October.

**NASS's own words support using imagery.** November 2026 Crop Production, methodology: the Agricultural Statistics Board "reviews multiple data sources at the National and State level, including USDA administrative acreage data, satellite imagery, and objective yield and grower reported data." August 2026 revision policy: "Revisions to planted acres will only be made when either special survey data, administrative data, such as Farm Service Agency certified acreage data, or remote sensing data are available." The January summary rests "primarily on surveys conducted during the month of December", a sample of about 73,100 operators.

**Benchmark rows for the notebook** (state WAPE, 48 states, NASS first January estimate):

| Row | 2024 | 2025 | 2019-2025 |
|---|---|---|---|
| Same as last year | 11.8% | 15.1% | 14.2% |
| FSA per-state ratio | 14.4% | 15.4% | 17.6% |
| Best public baseline (FSA pass-through in high-coverage states + residual cap) | 11.6% | 15.3% | 12.8% (2020-2025, leave-one-year-out) |
| Ceiling if non-grain acres were known (oracle residual ratio) | 5.3% | 6.6% | 8.9% |

US total: persistence is off by 280,000 acres on average (4.4%); the oracle by 110,000.

**What satellites add, stated for a statistician.** Kernel measures the quantity the oracle row uses: the share of planted corn that did not go to grain, by state, in November instead of January. Splitting that share into silage and abandoned is the second step (silage is 73-86% of it nationally; 73% in the 2022 drought).

**Demo states.**

- Switch-watch: Kansas or Nebraska (no RMA silage type, FSA coverage 0-11%, residual +150,000 and +180,000, 2022 precedent +75% and +65%), plus South Dakota or North Dakota if labels exist there.
- Control where the administrative prior is good: New York (95%) or Wisconsin (52%, and the largest silage state).
- California: FSA coverage 85%; FSA, RMA and NASS planted area all say down 7-12%; the residual cap is 345,000.

**Challenge to plan v2.** Inference: the 2026 switchers are mostly drought salvage, not planned dairy silage. A field chopped at 2 tons per acre after the canopy has fired has a low peak NDVI, little green left at the cut and a "dry-down" that looks like grain. Green-at-cut and dry-down days will misread it. Cut date (early), residue (NDTI = (B11 - B12) / (B11 + B12) on Sentinel-2, low after chopping) and low peak biomass still work. Consider a third outcome, "non-grain harvest, low biomass", and roll it into the non-grain total. Early harvest is also general in the drought belt this year, so "early relative to county median" matters more than calendar date.

**Use FSA where it is good.** As a county prior and reconciliation target only in high-coverage states (New York, Idaho, California, Arizona, New Mexico, Vermont, Washington, Montana; also Georgia, Florida, Oregon at about 100%). Give it zero weight in Kansas, Nebraska, Iowa, South Dakota, Minnesota, Michigan, Pennsylvania, Ohio, Illinois, Missouri.

**Corrections to numbers in the pitch** (30 Sep 2026 Grain Stocks revision of 2025):

| Item | In the brief | Revised |
|---|---|---|
| US planted | 98.8M | 98.713M |
| US harvested for grain | 91.3M | 90.948M |
| US silage | 6.2M (6,208) | 6.187M |
| US other fates | about 1.3M | 1.578M |
| California | 420K planted, about 365K silage, about 50K grain | 450K planted, 370K silage, 75K grain |
| Texas silage 2025 | | 245K (+53% on 160K); first estimate was 265K |
| US silage 2024 | 6,100 (January 2025) | 6,207 |

---

## 7. Recipes

Scripts and extracted JSON from this run are in the session scratchpad (temporary, copy if needed): `<session scratchpad, not in the repo>` (`scripts/`, `out/`, `nass/`, `zips/`, `rma/`, `usdm/`). They use the Python standard library only.

Download (FSA blocks default agents; newer files sit behind a landing page):

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
# 2026 file released 10 Nov 2026 (data as of 5 Nov)
curl -L -A "$UA" -o fsa_2026_nov.zip https://www.fsa.usda.gov/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip
# 2025 final (5 Jan 2026), 2025 1 Dec, 2024 final, 2023 final
curl -L -A "$UA" -o fsa_2025_final.zip https://www.fsa.usda.gov/sites/default/files/2026-01/DoISjehvQfz9.ZIP
curl -L -A "$UA" -o fsa_2025_dec.zip   https://www.fsa.usda.gov/sites/default/files/2025-12/UhYA3k5AKxVM.zip
curl -L -A "$UA" -o fsa_2024_final.zip https://www.fsa.usda.gov/sites/default/files/2025-01/FnNg0ix5oKdi.zip
curl -L -A "$UA" -o fsa_2023_final.zip https://www.fsa.usda.gov/sites/default/files/documents/3QPVeIgPizDl.zip
# NASS text reports
for f in cropan24 cropan25 cropan26 grst0926 crop1126 crop0926; do curl -L -o $f.txt https://release.nass.usda.gov/reports/$f.txt; done
# RMA (if DNS fails, add: --resolve pubfs-rma.fpac.usda.gov:443:<address from a public resolver>)
curl -L -o sobtpu_2026.zip https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/state_county_crop/sobtpu_2026.zip
# Drought Monitor, one state (FIPS 08 = Colorado)
curl -H "Accept: application/json" "https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=08&startdate=6/1/2026&enddate=11/12/2026&statisticsType=1"
```

FSA silage by state (pandas transcription for the Keeboh notebook; not executed by me, the executed version is `scripts/extract_corn.py`):

```python
import pandas as pd
df = pd.read_excel("2026_fsa_acres_web_110526.xlsx", sheet_name="county_data", header=1, dtype={"State County Code": str})
corn = df[df["Crop"].str.upper().eq("CORN")]
sil = corn[corn["Intended Use"].isin(["Silage", "Forage"])]          # "Forage" before crop year 2019
fsa_state = sil.groupby("State")["Planted Acres"].sum()               # US total 2,885,863 for this file
fsa_county = sil.assign(fips=sil["State County Code"].str.zfill(5)).groupby("fips")["Planted Acres"].sum()
```

Benchmark estimators (`S0` = NASS silage last year in 1,000 acres; `F0`, `F1` = FSA acres; `R1` = this year's November planted minus grain):

```python
ratio      = S0 * (F1 / F0).clip(0.5, 2.0).where(F0 >= 500, 1.0)      # FSA per-state ratio
additive   = S0 + b * (F1 - F0) / 1000                                # b about 0.64 (0.8-0.95 if coverage >= 50%)
best_pub   = pd.concat([additive.where(F0 / (1000 * S0) >= 0.5, S0), R1], axis=1).min(axis=1)
wape       = (pred - truth).abs().sum() / truth.sum()
```

NASS text tables are fixed width with CRLF endings; state rows look like `Kansas ........:   330   310   230 ...`. Take the table whose title starts "Corn for Silage Area Harvested" and read the first three numeric columns (three years). Use `LC_ALL=C grep -a` on these files.

RMA `SOBSCCTPU26.TXT`: pipe-delimited, no header, records end with a bare carriage return. Field 7 = commodity code (0041), field 14 = type code (026), field 15 = type name, field 10 = plan, field 20 = net reported quantity, field 21 = unit ("Acres").

---

## 8. Pitfalls

1. FSA "as of" labels for 2025-2026 are release dates. No October or November 2025 file exists, so there is no like-for-like vintage for the 2026 ratio; Kansas was reclassified from 13,249 to 294 silage acres between the September and December 2025 files.
2. Ratios explode where coverage is low (Kansas 294 -> 6,176 acres is +1,997%). Clip, gate by coverage, or use the additive form.
3. Label is "Forage" through 2018 and "Silage" from 2019. Connecticut county codes changed to planning regions in the 2026 file. `State County Code` has no leading zero.
4. NASS revises: 2024 went from 6,100 to 6,207; Texas 2025 from 265 to 245. Score against both.
5. NASS's November residual is a forecast of intended harvest, not a bound (revised by +1,608 and -1,151 thousand acres in two of the last four years).
6. RMA files end records with a carriage return only (`head` prints the whole file), and the RMA hosts did not resolve on our network DNS at about 13:45 PT.

---

## 9. Open questions

1. Does any public FSA or RMA table record the switch when grain-insured corn is appraised and chopped (cause-of-loss by month, notice-of-loss counts)?
2. How was the 1.6 million acre drop in 2022 grain area split between silage and abandonment by state, and can imagery separate chopped from grazed or hayed fields?
3. Which states are in the organisers' labelled set, and are any in the Plains drought belt?
4. Is the 28% fall in Colorado FSA silage intentions a water-supply effect (prevented planting up from 79,530 to 282,325 acres), and did salvage chopping offset it?
5. Which scenario (6.15M or 6.8M) do Kernel's field-level 2026 predictions support?

---

## 10. Annotated bibliography (all opened today unless marked)

| # | Source | URL | What it gave |
|---|---|---|---|
| 1 | USDA FSA, Crop Acreage Data (FOIA frequently requested) | https://www.fsa.usda.gov/tools/informational/freedom-information-act-foia/electronic-reading-room/frequently-requested/crop-acreage-data | File list, release schedule, shutdown note, all 27 workbooks |
| 2 | FSA 2026 file released 10 Nov 2026 | https://www.fsa.usda.gov/sites/default/files/2026-11/Wrcdk92KC1587MaHom35213.zip | 2,885,863 corn silage acres; state and county detail |
| 3 | FSA 2025 final file (5 Jan 2026) | https://www.fsa.usda.gov/sites/default/files/2026-01/DoISjehvQfz9.ZIP | 2,919,232 acres |
| 4 | FSA Intended Use Codes (2-CP Exhibit 11) | https://www.fsa.usda.gov/sites/default/files/documents/intended_use_codes.pdf | Definitions of Silage, Forage, Grain |
| 5 | FSA Notice CP-749, 29 Oct 2018 | https://www.fsa.usda.gov/Internet/FSA_Notice/cp_749.pdf | Forage replaced by Silage for corn from 2019, to match RMA |
| 6 | NASS Crop Production 2025 Summary (Jan 2026) | https://release.nass.usda.gov/reports/cropan26.txt | State silage 2023-2025; methodology (December Agricultural Survey) |
| 7 | NASS Crop Production Annual Summaries 2016-2024 | https://release.nass.usda.gov/reports/cropan25.txt (also cropan17 to cropan24) | First estimates and revisions |
| 8 | NASS Grain Stocks, 30 Sep 2026 | https://release.nass.usda.gov/reports/grst0926.txt | Revised 2025: silage 6,187; Texas 245; California 450/75/370 |
| 9 | NASS Crop Production, 10 Nov 2026 | https://release.nass.usda.gov/reports/crop1126.txt | Planted 96,777; grain 88,506; yields; blank silage cell; "satellite imagery" in methodology |
| 10 | NASS Crop Production, 11 Sep 2026 | https://release.nass.usda.gov/reports/crop0926.txt | State planted and harvested for grain, 2025 and 2026 |
| 11 | NASS Crop Production, 12 Aug 2026 | https://release.nass.usda.gov/reports/crop0826.txt | Revision policy naming FSA data and remote sensing |
| 12 | NASS November Crop Production 2017-2025 | https://release.nass.usda.gov/reports/crop1125.txt (also crop1117 to crop1124) | November residual history |
| 13 | NASS Crop Progress, 8 Sep 2026 | https://release.nass.usda.gov/reports/prog3626.txt | Corn condition by state; 2025 and 2022 from prog3625, prog3622 |
| 14 | RMA Summary of Business, type/practice/unit | https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/state_county_crop/sobtpu_2026.zip | Silage-type insured acres 2016-2026; zero in Kansas and Nebraska |
| 15 | US Drought Monitor data services | https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=08&startdate=6/1/2026&enddate=11/12/2026&statisticsType=1 | Weekly state drought area |
| 16 | DTN, "Leaning More on FSA Data, NASS Again Boosts Acreage in August Reports", 12 Aug 2026 | https://www.dtnpf.com/agriculture/web/ag/blogs/market-matters-blog/blog-post/2026/08/12/leaning-fsa-data-nass-boosts-acreage | NASS raised corn planted area 1.4M to 96.73M using FSA data; FSA corn 94.765M |
| 17 | farmdoc daily, "Yes, There Are a Lot of Corn Acres", Aug 2025 | https://farmdocdaily.illinois.edu/2025/08/yes-there-are-a-lot-of-corn-acres-evidence-from-fsa-acreage-data.html | FSA corn is 98.5% of NASS planted; no silage analysis |
| 18 | farmdoc daily, Darrel Good, "Questions About Corn Acreage", 4 Sep 2012 | https://farmdocdaily.illinois.edu/2012/09/questions-about-corn-acreage.html | Silage acreage spikes in dry years (1980, 1988) |
| 19 | AgriSompo, "Putting Acreage to Alternate Use", 23 Aug 2023 | https://www.agrisompo.com/stories/posts/putting-acreage-to-alternate-use/ | Grain-only, silage-only and dual counties; notice of loss before chopping |
| 20 | The Prowers Journal (Successful Farming reprint), 19 Oct 2026 | https://theprowersjournal.com/drought-forces-colorado-farmer-to-salvage-corn-for-silage/ | Colorado salvage silage case |
| 21 | NDSU Extension EC1343, revised Aug 2026 | https://www.ndsu.edu/agriculture/extension/publications/what-value-standing-corn-crop-silage | North Dakota grain-or-silage decisions; contact agent before chopping |
| 22 | Grain Journal, 25 Aug 2026 | https://www.grainjournal.com/article/1153173/north-dakota-drought-forces-corn-harvest-decisions | Same, second outlet |
| 23 | UNL Beef, 4 Aug 2026 | https://beef.unl.edu/using-drought-stressed-corn-forage-evaluating-options-and-managing-nitrate-risk/ | Nebraska drought-stressed corn as forage |
| 24 | fnbsf.com, "Insuring Your Success: Will we have an early harvest in 2026?", 7 Aug 2026 (lender crop insurance blog; publisher name inferred from the domain) | https://www.fnbsf.com/blog/will-we-have-an-early-harvest-in-2026/ | Early chopping in South Dakota; appraisal rule |
| 25 | K-State Agronomy eUpdate 1120, 10 Sep 2026 | https://www.agronomy.k-state.edu/eupdates/2026/issue-1120-september-10/small-grain-forages-for-fall.html | Kansas drought extent, forage supply |
| 26 | Team notes | `DOCS/research/labels.verification.md`, `DOCS/research/nowcast.md` | Independent match of FSA and RMA totals; origin of the 6.6-6.9M band |

Not opened (do not cite as fact): USDA "Update of 2019 FSA Acreage Data and FAQs" PDF (HTTP 403); FSA handbook 2-CP full text (timeout); The Silage Report newsletter of 29 Jun 2026 (HTTP 402); RMA Corn Loss Adjustment Handbook.
