# NASS operations and the information gap: calendar, methods, revisions, market stakes

Research brief for team Kernel, Hack the Harvest. Written Saturday 2026-11-14.
Topic id: `nass_ops`.

## 0. How this was researched, and what that limits

- **WebSearch was not available.** The shared search budget for this run was already exhausted when this agent started, so zero searches were run (the brief asked for at least 12). Everything below comes from documents fetched directly by URL: NASS report text files, NASS notices, NASS methodology PDFs, the November 2026 WASDE, the CDL FAQ, the US Code, and three press pages reached by site navigation.
- **Every number below was read from an opened document** unless it is marked "Inference:" (my arithmetic or reasoning) or listed in section 16 (could not be opened).
- NASS report text was read from `https://release.nass.usda.gov/reports/<name>.txt`. This host works without a key and is a good programmatic source for the team (see section 15, recipe R1). The usual archive host `esmis.nal.usda.gov` did not resolve from this machine.
- Numbers are in thousand acres ("K") unless stated. "Jan vintage" means as published January 12, 2026; "revised" means as carried in the October 9 and November 10, 2026 Crop Production reports.

## 1. Bottom line

1. **The gap is real and visible in this week's report.** The November 10, 2026 Crop Production table has a line "Corn for silage" whose 2026 cell is blank. The first 2026 silage number arrives with the Crop Production Annual Summary in January 2027. California is not even forecast monthly for grain: it sits inside "Other States" until the annual summary.
2. **The numbers quoted to us are public and correct.** November 10, 2026: 15.9 billion bushels (15,893,419 thousand), 179.6 bu/ac, down 1.6 bu from October; 88.506 million acres harvested for grain. 1.6 x 88.506 = 141.6 million bushels. WASDE-677 states the same 141 million bushel cut.
3. **The January 12, 2026 surprise was acreage, not yield.** Harvested-for-grain rose 1,211K acres against November 2025 (90,047K to 91,258K); production rose 268 million bushels; about 84 percent of that came from acres. Press: corn futures "plunged to the lowest levels since August".
4. **NASS's survey base is thinning.** December Agricultural Survey response rate: 55.7 percent (2020) to 40.2 percent (2025). The in-person June Area Survey disappeared from the Acreage report's stated basis between June 2024 and June 2025.
5. **NASS now says in print that it uses satellites.** Since the August 2026 Crop Production the estimating-procedures paragraph reads: the ASB "reviews multiple data sources ... including USDA administrative acreage data, satellite imagery, and objective yield and grower reported data."
6. **The survey is weakest exactly where silage dominates.** NASS's own coefficient of variation for the ratio "harvested for grain / planted" in 2025: California 23.3 percent, Arizona 38.3, Idaho 18.5, New Mexico 18.2, Utah 14.1, Washington 11.8; Iowa 0.5, Illinois 0.3, US 0.3.
7. **National silage is stable, state silage is not.** 2024 to 2025 the US total moved by 1K acres (6,207K to 6,208K) while 937K acres moved at state level (469K up, 468K down).

## 2. Calendar, and which report carries which number

Dates for 2026 are from the NASS 2026 release calendar file.

| Report | 2026 date | Survey behind it | Corn content | Silage? |
|---|---|---|---|---|
| Prospective Plantings | Mar 31 | March Agricultural Survey, about 73,800 operators, first two weeks of March | Intended plantings: 95,338K | No number (line exists, empty) |
| Acreage | Jun 30 | June Agricultural Survey, about 90,300 operators, first two weeks of June | Planted all purposes 95,343K; to be harvested for grain 87,434K | No |
| Crop Production (monthly) | Aug 12, Sep 11, Oct 9, Nov 10, Dec 10 | Objective yield (10 states) plus the monthly farm operator yield survey (about 6,300 producers in Nov 2026) | Yield and production forecasts; acreage reviewed in Aug and Sep | Line present, current-year cell blank; prior-year final shown |
| Crop Production Annual Summary | Jan 12 (2025 crop) | December Agricultural Survey, about 73,100 operators | Final planted, grain acres, yield, production by state | **Yes: first silage acres, yield, tons, by state** |
| Grain Stocks | Jan 12, Mar 31, Jun 30, Sep 30 | Quarterly Agricultural Survey | Stocks; Sep 30 carries prior-crop revisions | No |
| County Estimates, corn/soybeans/sorghum | May 5 (2025 crop) | December Agricultural Survey plus Row Crops CAPS, small-area model | 31 states for corn grain | **6 states for corn silage** (204 counties for 2024, 180 for 2025) |
| Crop Production Historical Track Records | Apr 8 | none (compilation) | History since 1866, forecast-versus-final tables | Silage series included |
| Crop Progress (weekly) | Apr 6 to Nov 30 | State reporters | Planting, maturity, harvest progress | Not in the national report I opened |
| Cropland Data Layer | not on the ASB calendar | FSA CLU training data, Landsat 8/9 and Sentinel-2 | 2025 CDL released Feb 27, 2026; 2024 CDL Feb 27, 2025; 2023 CDL Jan 31, 2024 | CDL FAQ does not mention silage |

Other 2026 dates: Cattle Jan 30 and Jul 24; Small Grains Summary Sep 30; small-grain county estimates Mar 5 and Dec 18; cotton and cattle county estimates May 12; rice and peanuts May 22.

**Lead time of a mid-November field-level silage estimate** (Inference from the dates above): about 2 months before the first state silage acres, about 3.5 months before the CDL, about 6 months before county silage estimates, which exist for only 6 states.

Revision policy, quoted from the November 10, 2026 Crop Production: "Revisions to planted acres will only be made when either special survey data, administrative data, such as Farm Service Agency certified acreage data, or remote sensing data are available. Harvested acres may be revised any time a production forecast is made if there is sufficient data indicating that the intended harvested area has changed since the last forecast."

## 3. How the numbers are made

### 3.1 Surveys and sample sizes (from the reports' Statistical Methodology sections)

| Survey | Year | Sample | Collection modes as stated |
|---|---|---|---|
| June surveys (Acreage report, June 2024) | 2024 | Area frame: about 9,000 segments of about 1 square mile, enumerated; list frame: about 64,000 operators | "mail, internet, telephone, or personal interview" |
| June Agricultural Survey (Acreage, Jun 30, 2025) | 2025 | about 67,700 operators; no area frame mentioned | "mail, internet, or telephone" |
| June Agricultural Survey (Acreage, Jun 30, 2026) | 2026 | about 90,300 operators; no area frame mentioned | "mail, internet, or telephone" |
| March Agricultural Survey (Prospective Plantings, Mar 31, 2026) | 2026 | about 73,800 operators | "mail, internet, or telephone" |
| Farm operator yield survey (Crop Production, Nov 14, 2025) | 2025 | about 6,690 producers, Oct 25 to Nov 9 | "primarily by telephone" |
| Farm operator yield survey (Crop Production, Nov 10, 2026) | 2026 | about 6,300 producers, Oct 24 to Nov 4 | "primarily by telephone" |
| December Agricultural Survey (Annual Summary, Jan 2026) | 2025 | about 73,100 operators | "mail, internet, telephone, or personal interview" |
| Row Crops County Agricultural Production Survey (CAPS) | 2024 / 2025 | 57,795 / 57,349, in 36 states | not extracted |

Corn objective yield plots are measured in 10 states: Iowa, Illinois, Indiana, Kansas, Minnesota, Missouri, Nebraska, Ohio, South Dakota, Wisconsin. They are corn-for-grain fields.

Relative standard errors published by NASS: June 2026 corn planted acres 1.3 percent; December 2025 corn production about 1.3 percent (95 percent interval plus or minus 2.6 percent). Over the last decade US survey CVs for corn planted acres ranged 1.0 to 1.3 percent; the target is 1 percent.

**Inference:** the June Area Survey, the in-person area-frame enumeration, is no longer part of the stated basis for June acreage. I found no NASS notice announcing this, and the February 2026 annual methodology still describes a dual frame with the June Area Survey. Treat the status as unconfirmed and ask a NASS mentor.

### 3.2 The Agricultural Statistics Board (ASB) process

From "Annual Crop Production Methodology and Quality Measures" (February 4, 2026):

- Regional Field Offices summarize their own state's survey and submit a recommended estimate; they "see their survey results only".
- "NASS assembles a panel of statisticians to serve as the ASB which reviews the National results and establishes the National estimates." NASS "employs the 'top-down' approach by determining the National estimates first and reconciling the State estimates to the National estimate."
- Each ASB member makes an independent interpretation; "An official National estimate is established only upon ASB consensus."
- The yardstick is "the historical relationship of the survey results to the official estimate ... evaluated over time to determine accuracy and bias using tables and graphs."
- On outside data: "In order to be considered, these data must be deemed to be reliable and come from unbiased sources. Thus, they are often of limited use prior to the end of the season. The most common administrative data are the certified acreage data from USDA's Farm Service Agency."

Estimating-procedures wording changed between seasons:

- November 14, 2025: "National and State level objective yield and grower reported data were reviewed ... Each Regional Field Office submits their analysis of the current situation to the Agricultural Statistics Board (ASB). The ASB uses the survey data and the State analyses to prepare the published November 1 forecasts."
- August 12, October 9 and November 10, 2026: "The Agricultural Statistics Board (ASB) reviews multiple data sources at the National and State level, including USDA administrative acreage data, satellite imagery, and objective yield and grower reported data."

The Regional Field Office sentence is gone from the 2026 Crop Production reports. **Inference:** this is consistent with a reorganization, but I could not open any USDA document on the reorganization (section 16).

### 3.3 Administrative data

- July 31, 2024 NASS notice: before the August Crop Production NASS reviews "all available data, including survey data and the latest information from USDA's Farm Service Agency and Risk Management Agency." August review covers corn; September review covers corn again; October covers canola, dry beans, sunflower.
- August Crop Production reports in 2025 and 2026 both open the corn comment with: "Acreage updates were made based on a thorough review of all available data."
- County estimates: "The planted and harvested acreage models input current year survey expansions, survey standard errors, and administrative data from FSA and RMA." These are Bayesian small-area models, used since the 2020 crop year, benchmarked to the ASB state totals. Published model CVs for county corn silage harvested acres: median 1.4 percent for the 2024 crop and 2.0 percent for 2025; 75th percentile 2.5 percent for 2024.

### 3.4 Remote sensing

From the CDL FAQ:

- Purpose: the program provides "supplemental acreage estimates to the Agricultural Statistics Board for the state's major commodities."
- Method: CDL acreage estimates "are not simple pixel counting but regression estimates using NASS survey data."
- Bias warning: "Pixel counting is usually downward biased when compared to the official estimates."
- Training data: "Agricultural training and validation data are derived from the Farm Service Agency (FSA) Common Land Unit (CLU) Program."
- Sensors and resolution: "Beginning in 2024, the CDL spatial resolution has increased to 10-meters." Landsat 8 and 9 and Sentinel-2A and -2B. 2008 to 2023 CDLs are 30 m.
- Accuracy: "The major crop types for a CDL state will normally have a classification accuracy of 85% to 95%." The page summary also returned 75.4 percent overall crop accuracy for 2025; verify that figure on the page before quoting it.
- The FAQ does not mention silage.

Research titles listed on the NASS Cropland page (titles only; the papers were not opened): "Rapid In-season Mapping of Corn and Soybeans Using Machine-learned Trusted Pixels from Cropland Data Layer" (2021); "Towards Routine Mapping of Crop Emergence within the Season Using the Harmonized Landsat and Sentinel-2 Dataset" (2021); "Preseason crop type prediction using crop sequence boundaries" (2023); a 2025 title on tracking weekly crop progress. No harvest-type or silage-identification title appeared on the two NASS pages I opened. **Inference:** silage-versus-grain mapping is not an advertised NASS product or research line, which supports our innovation claim, but absence on two pages is weak evidence.

Crop Sequence Boundaries, VegScape, Crop-CASMA and CroplandCROS were not individually opened.

## 4. Response rates

### 4.1 December Agricultural Survey, United States (source of the first silage acreage)

Read from five editions of "Annual Crop Production Methodology and Quality Measures"; overlapping years agree across editions.

| Crop year | Sample size | Response rate |
|---|---|---|
| 2020 | 73,135 | 55.7% |
| 2021 | 72,603 | 50.1% |
| 2022 | 72,615 | 48.3% |
| 2023 | 72,239 | 45.8% |
| 2024 | 73,269 | 46.0% |
| 2025 | 73,133 | 40.2% |

A fall of 15.5 points in five years. NASS defines response rate as the proportion of the eligible sample that completed the survey (OMB Guideline 3.2.2).

### 4.2 December 2025 response rate, selected states

| State | 2024 | 2025 |
|---|---|---|
| Iowa | 42.5 | 39.8 |
| Illinois | 42.0 | 37.5 |
| Nebraska | 36.1 | 30.2 |
| Minnesota | 38.8 | 33.5 |
| Indiana | 45.7 | 33.1 |
| Kansas | 35.4 | 31.7 |
| South Dakota | 36.9 | 29.0 |
| North Dakota | 26.6 | 28.0 |
| Wisconsin | 47.5 | 48.6 |
| New York | 43.3 | 44.9 |
| Pennsylvania | 47.5 | 44.3 |
| California | 48.1 | 46.1 |
| Idaho | 45.8 | 40.2 |
| Texas | 49.6 | 43.2 |

Weighted item response rate for corn area harvested for grain, United States: 38.9 percent (2024), 35.6 percent (2025). For corn production: 35.8 and 33.0 percent.

CAPS (county survey) response rate, United States, 2024: 39.7 percent. The 2025 value was not extracted.

### 4.3 Longer history

Johansson, Effland and Coble (farmdoc daily, January 19, 2017): response rates for crop acreage and production surveys were "80-85 percent in the early 1990s" and had "fallen below 60 percent in some cases". Consequence stated there: fewer publishable counties; a county yield needs at least 30 responses, or at least 3 producers representing 25 percent of county acreage. Year-by-year values in that article are in a figure I could not read.

## 5. Where the survey is weakest on the grain share

"Quality Metrics for Corn Area Harvested for Grain", February 4, 2026. The CV is "for the ratio of harvested acres to planted acres", which is the grain share of planted corn.

| State | Item response 2024 | Item response 2025 | CV 2024 | CV 2025 | Silage % of planted 2025 |
|---|---|---|---|---|---|
| Arizona | 80.1 | 28.3 | 18.5 | 38.3 | 73.8 |
| California | 55.2 | 48.1 | 30.8 | 23.3 | 86.9 |
| Idaho | 44.6 | 35.7 | 8.6 | 18.5 | 65.1 |
| New Mexico | 26.8 | 21.9 | 13.3 | 18.2 | 56.2 |
| Utah | 74.9 | 53.7 | 11.3 | 14.1 | 60.0 |
| Washington | 48.7 | 55.7 | 11.2 | 11.8 | 44.5 |
| Oregon | 62.9 | 67.7 | 13.4 | 8.6 | 27.6 |
| New York | 36.6 | 42.0 | 13.4 | 5.0 | 51.5 |
| Pennsylvania | 35.7 | 41.9 | 5.0 | 4.4 | 31.2 |
| Wisconsin | 43.0 | 45.5 | 1.9 | 2.9 | 21.3 |
| Texas | 45.8 | 38.3 | 1.9 | 2.8 | 10.6 |
| Michigan | 48.9 | 39.1 | 1.1 | 2.0 | 14.9 |
| Colorado | 40.8 | 40.0 | 2.1 | 1.3 | 13.3 |
| South Dakota | 35.0 | 29.5 | 0.8 | 1.1 | 5.7 |
| Kansas | 33.7 | 32.5 | 1.2 | 0.8 | 3.4 |
| Iowa | 39.4 | 35.3 | 0.5 | 0.5 | 1.8 |
| Illinois | 39.1 | 38.1 | 0.1 | 0.3 | 0.8 |
| Nebraska | 35.7 | 31.0 | 0.4 | 0.3 | 2.0 |
| United States | 38.9 | 35.6 | 0.3 | 0.3 | 6.3 |

Vermont and Nevada are "(NA)" (no grain estimate). NASS publishes no quality-metrics table for corn silage acreage itself.

A concrete case: the June 30, 2025 Acreage report forecast California corn harvested for grain at 30K; the January 2026 final was 50K.

**Inference:** satellite classification has its highest marginal value in the western and northeastern dairy states, where the survey's own precision on the grain share is 10 to 100 times worse than in the Corn Belt.

## 6. Program changes, 2024 to 2026

| Date | What happened | Source |
|---|---|---|
| Apr 4, 2024 | Program changes after the five-year review (details on a separate page, not opened) | NASS notice |
| Apr 9, 2024 | NASS cancels the July Cattle report, discontinues the Cotton Objective Yield Survey, and discontinues all County Estimates for Crops and Livestock "beginning with the 2024 production year". Reason: "necessary, given appropriated budget levels." | NASS notice |
| Jul 31, 2024 | NASS announces the acreage review using FSA and RMA information ahead of August Crop Production | NASS notice |
| Mar 19, 2025 | NASS reinstates the July Cattle report and County Estimates: 2024 crop for row crops, 2025 crop for small grains. Corn, sorghum, soybean county estimates set for May 6, 2025; July Cattle for July 25, 2025. No reason given. | NASS notice |
| Aug 28, 2025 | NASS discontinues the Mink Survey and the Agricultural Labor Survey as "duplicative and/or no longer necessary" | NASS notice |
| Oct 9, 2025 | Crop Production not released (lapse in appropriations). Crop Progress not released Oct 6, 14, 20, 27, Nov 3, 10. | NASS notice Nov 19, 2025; Track Records footnote |
| Oct 31, 2025 | November Crop Production moved from Nov 10 to Nov 14, 2025; WASDE released with it | NASS notice |
| Nov 19, 2025 | Reschedule list; small-grain county estimates moved from Dec 19, 2025 to Mar 5, 2026 | NASS notice |
| Dec 22, 2025 | Reports rescheduled for the Dec 24 and 26 government closure (notice title only) | NASS notices index |
| Oct 23 and 24, 2026 | NASS corrects September 2026 corn data: "a September processing error involving incorrect acreage weights" for irrigated and non-irrigated objective yield observations in Kansas and Nebraska. Corrected September yields: Kansas 118 (down 3), Nebraska 182 (up 5), US 178.8 (up 0.3). October forecasts unchanged. NASS will "implement additional pre-publication checks". | NASS notices |

The Track Records footnote reads: 'No "Crop Production" report was published in either October 2013 or October 2025.'

Not verified: any NASS-specific element of the 2025 USDA reorganization.

## 7. The 2025 crop: revision trail and the January 12, 2026 surprise

| Release | Planted | Harvested for grain | Yield bu/ac | Production, thousand bu | Silage acres |
|---|---|---|---|---|---|
| Prospective Plantings, Mar 31, 2025 | 95,326 | | | | |
| Acreage, Jun 30, 2025 | 95,203 | 86,774 | | | |
| Crop Production, Aug 12, 2025 | 97,254 | 88,691 | 188.8 | about 16.7 billion | blank |
| Crop Production, Sep 12, 2025 | about 98.7 million | 90,047 | 186.7 | 16,814,371 | blank |
| October 2025 | not published | | | | |
| Crop Production, Nov 14, 2025 | 98,728 | 90,047 | 186.0 | 16,752,193 | blank |
| **Annual Summary, Jan 12, 2026** | **98,788** | **91,258** | **186.5** | **17,020,549** | **6,208** (21.8 t/ac; 135,540 thousand tons) |
| Revised, in Oct 9 and Nov 10, 2026 reports | 98,713 | 90,948 | 186.5 | 16,963,628 | 6,187 (135,090 thousand tons) |

January 2026 against November 2025:

- Planted: +60K.
- Harvested for grain: **+1,211K (+1.3 percent)**.
- Yield: +0.5 bu/ac.
- Production: **+268,356 thousand bu (+1.6 percent)**. Inference: 1,211K x 186.0 = 225 million bu, or 84 percent of the increase, came from acres.
- Silage: first estimate 6,208K, "up slightly"; production "a record high 136 million tons"; yield a record 21.8 t/ac.
- Corn area still left to be harvested at the December survey: 415K in 2025 against 188K in 2024.

June 2025 to January 2026: planted +3,585K (+3.8 percent); harvested for grain +4,484K (+5.2 percent). In the Track Records table, June 2025 planted was 96.4 percent of the annual summary, the lowest ratio in the 2000 to 2025 rows.

The Track Records table prints the June 2025 harvested forecast as 86,744; the Acreage report itself says 86,774. I use the report.

**Inference, with a caution:** the largest June miss in the modern record coincided with the first June estimate whose stated basis had no area frame. That is a coincidence in timing, not a demonstrated cause.

### Market reaction (press, second-hand)

Farm Policy News, University of Illinois (Ryan Hanrahan, January 13, 2026), summarizing Farm Futures and DTN:

- Production a record 17.021 billion bushels, up 269 million from November. Harvested acreage raised 1.3 million acres to 91.3 million. Yield 186.5, up 0.5; trade expectations had been for a cut of about 2 bu/ac.
- 2025-26 ending stocks raised 198 million bushels to 2.227 billion, a seven-year high.
- Farm Futures: corn futures "plunged to the lowest levels since August".
- Jon Prischmann, Blue Creek Commodities and Hedging: the numbers "blindsided" the market and were "very ugly for corn".
- Bryce Knorr, Farm Futures: corn could slip below $4, possibly to $3.35 to $3.70.
- The same summary says USDA raised its average corn price forecast by 10 cents to $4.10. This sits oddly with a larger crop; I could not open the January WASDE to check it.

DTN (Todd Neeley, January 12, 2026): a "surprise"; yield "far above pre-report estimates"; Renewable Fuels Association called it a "sobering wake-up call about the state of the farm economy".

**Not verified:** the size of the futures move in cents per bushel. The Farm Progress article returned HTTP 403.

### Prior-year revision of silage itself

The August 12, 2025 Crop Production carried 2024 silage as 6,100K acres and 123,093 thousand tons. The November 14, 2025 report and the January 2026 summary carry 2024 as 6,207K acres and 125,590 thousand tons. **Inference:** NASS revised 2024 silage up by 107K acres (+1.8 percent) at the end-of-marketing-year review. For 2025 the revision so far is -21K acres (-0.3 percent). The "truth" we reconcile to moves by up to about 2 percent after January.

## 8. The 2026 crop so far

| Release | Planted | Harvested for grain | Yield | Production, thousand bu |
|---|---|---|---|---|
| Prospective Plantings, Mar 31, 2026 | 95,338 | | | |
| Acreage, Jun 30, 2026 | 95,343 | 87,434 | | |
| Crop Production, Aug 12, 2026 | 96,730 | 88,592 | 180.7 | 16,012,964 |
| Crop Production, Sep 11, 2026 (corrected Oct 23) | 96,777 | 88,506 | 178.8 | 15,828,159 |
| Crop Production, Oct 9, 2026 | 96,777 | 88,506 | 181.2 | 16,033,944 |
| **Crop Production, Nov 10, 2026** | **96,777** | **88,506** | **179.6** | **15,893,419** |
| Corn for silage 2026 | blank in every report above | | | |

- June to September 2026: planted +1,434K (+1.5 percent); harvested for grain +1,072K (+1.2 percent).
- November 10, 2026 corn comment: area harvested "unchanged from the previous estimate but down 3 percent from last year"; yield "down 1.6 bushels from the previous forecast and down 6.9 bushels from last year's record high 186.5".
- "Seventy-four percent of the 2026 corn acreage had been harvested by November 1, three percentage points behind the 5-year average." The weather summary says 26 percent of the nation's corn remained in the field on November 1.
- Published reliability: "there is a 90% chance that the final corn production will be between 15.5 billion bushels and 16.3 billion bushels". Root mean square error of the November 1 forecast 1.3 percent; 90 percent interval 2.3 percent. Over 20 years the November forecast differed from final by 144 million bushels on average, range 4 to 420 million; below final 7 times, above 13 times.
- "Other States include Arizona, California, Florida, Montana, New Jersey, New Mexico, Oregon, Utah, West Virginia, and Wyoming. Individual State level estimates will be published in the 'Crop Production 2026 Summary.'"

WASDE-677, November 10, 2026, corn:

| Item | 2024/25 | 2025/26 est. | 2026/27 Oct | 2026/27 Nov |
|---|---|---|---|---|
| Area planted, million acres | 90.9 | 98.7 | 96.8 | 96.8 |
| Area harvested, million acres | 83.0 | 90.9 | 88.5 | 88.5 |
| Yield, bu per harvested acre | 179.3 | 186.5 | 181.2 | 179.6 |
| Production, million bu | 14,892 | 16,964 | 16,034 | 15,893 |
| Feed and residual | 5,435 | 6,118 | 6,000 | 5,975 |
| Ethanol and by-products | 5,437 | 5,548 | 5,650 | 5,650 |
| Exports | 2,873 | 3,429 | 3,300 | 3,275 |
| Ending stocks | 1,551 | 2,095 | 1,849 | 1,758 |
| Average farm price, $/bu | 4.24 | 4.16 | 4.70 | 4.60 |

Narrative: "Corn production is forecast at 15.9 billion bushels, down 141 [million] ... Harvested area for grain remains at 88.5 million acres ... The season-average corn price received by producers is lowered $0.10 per bushel to $4.60." WASDE takes area, yield and production straight from NASS; the rice paragraph in the same issue says "as indicated by the NASS November Crop Production report". Note the price went down with a smaller crop, so there is no simple bushels-to-price rule to quote.

## 9. History 2000 to 2025

Source: Crop Production Historical Track Records, April 2026. "Other fate" is my subtraction, planted minus grain minus silage. "June" is the June Acreage forecast of acres to be harvested for grain; "Jan" is the January Annual Summary. Grain share is harvested for grain divided by planted, each taken from the same report.

| Year | Planted | Grain | Silage | Silage % of planted | Other fate | June grain fcst | Nov grain fcst | Jan grain | Jun minus Jan | Nov minus Jan | June grain share | Jan grain share | Shift, pts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2000 | 79,551 | 72,440 | 6,082 | 7.65 | 1,029 | 73,088 | 73,009 | 72,732 | +356 | +277 | 91.84 | 91.44 | -0.41 |
| 2001 | 75,702 | 68,768 | 6,142 | 8.11 | 792 | 69,261 | 69,191 | 68,808 | +453 | +383 | 91.00 | 90.83 | -0.17 |
| 2002 | 78,894 | 69,330 | 7,122 | 9.03 | 2,442 | 72,081 | 70,541 | 69,313 | +2,768 | +1,228 | 91.30 | 87.68 | -3.62 |
| 2003 | 78,603 | 70,944 | 6,583 | 8.37 | 1,076 | 71,985 | 71,765 | 71,139 | +846 | +626 | 91.04 | 90.35 | -0.69 |
| 2004 | 80,929 | 73,631 | 6,101 | 7.54 | 1,197 | 73,362 | 73,311 | 73,632 | -270 | -321 | 90.61 | 90.98 | +0.38 |
| 2005 | 81,779 | 75,117 | 5,930 | 7.25 | 732 | 74,368 | 74,333 | 75,107 | -739 | -774 | 91.15 | 91.86 | +0.72 |
| 2006 | 78,327 | 70,638 | 6,487 | 8.28 | 1,202 | 72,091 | 71,047 | 70,648 | +1,443 | +399 | 90.83 | 90.20 | -0.64 |
| 2007 | 93,527 | 86,520 | 6,060 | 6.48 | 947 | 85,418 | 86,071 | 86,542 | -1,124 | -471 | 91.96 | 92.46 | +0.50 |
| 2008 | 85,982 | 78,570 | 5,971 | 6.94 | 1,441 | 78,940 | 78,177 | 78,640 | +300 | -463 | 90.40 | 91.46 | +1.07 |
| 2009 | 86,382 | 79,490 | 5,605 | 6.49 | 1,287 | 80,107 | 79,294 | 79,590 | +517 | -296 | 92.04 | 92.03 | -0.01 |
| 2010 | 88,192 | 81,446 | 5,567 | 6.31 | 1,179 | 81,005 | 81,263 | 81,446 | -441 | -183 | 92.19 | 92.35 | +0.17 |
| 2011 | 91,936 | 83,879 | 5,935 | 6.46 | 2,122 | 84,888 | 83,936 | 83,981 | +907 | -45 | 91.99 | 91.36 | -0.63 |
| 2012 | 97,291 | 87,365 | 7,419 | 7.63 | 2,507 | 88,851 | 87,721 | 87,375 | +1,476 | +346 | 92.16 | 89.93 | -2.23 |
| 2013 | 95,365 | 87,461 | 6,271 | 6.58 | 1,633 | 89,135 | 87,232 | 87,668 | +1,467 | -436 | 91.53 | 91.93 | +0.39 |
| 2014 | 90,597 | 83,146 | 6,361 | 7.02 | 1,090 | 83,839 | 83,097 | 83,136 | +703 | -39 | 91.49 | 91.76 | +0.28 |
| 2015 | 88,019 | 80,753 | 6,237 | 7.09 | 1,029 | 81,101 | 80,664 | 80,749 | +352 | -85 | 91.23 | 91.76 | +0.53 |
| 2016 | 94,004 | 86,748 | 6,206 | 6.60 | 1,050 | 86,550 | 86,836 | 86,748 | -198 | +88 | 91.93 | 92.28 | +0.35 |
| 2017 | 90,167 | 82,733 | 6,385 | 7.08 | 1,049 | 83,496 | 83,119 | 82,703 | +793 | +416 | 91.87 | 91.72 | -0.15 |
| 2018 | 88,821 | 81,169 | 6,090 | 6.86 | 1,562 | 81,770 | 81,767 | 81,740 | +30 | +27 | 91.74 | 91.71 | -0.03 |
| 2019 | 89,370 | 80,991 | 6,565 | 7.35 | 1,814 | 83,595 | 81,815 | 81,482 | +2,113 | +333 | 91.16 | 90.84 | -0.32 |
| 2020 | 90,432 | 82,168 | 6,560 | 7.25 | 1,704 | 84,023 | 82,527 | 82,467 | +1,556 | +60 | 91.32 | 90.80 | -0.52 |
| 2021 | 92,901 | 84,988 | 6,451 | 6.94 | 1,462 | 84,495 | 85,085 | 85,388 | -893 | -303 | 91.16 | 91.46 | +0.31 |
| 2022 | 88,162 | 78,705 | 6,851 | 7.77 | 2,606 | 81,940 | 80,844 | 79,207 | +2,733 | +1,637 | 91.12 | 89.42 | -1.70 |
| 2023 | 94,641 | 86,506 | 6,461 | 6.83 | 1,674 | 86,322 | 87,096 | 86,513 | -191 | +583 | 91.74 | 91.41 | -0.33 |
| 2024 | 90,909 | 83,046 | 6,207 | 6.83 | 1,656 | 83,438 | 82,710 | 82,896 | +542 | -186 | 91.21 | 91.50 | +0.29 |
| 2025 | 98,788 | 91,258 | 6,208 | 6.28 | 1,322 | 86,774 | 90,047 | 91,258 | -4,484 | -1,211 | 91.15 | 92.38 | +1.23 |

Notes on the table: planted, grain and silage for 2000 to 2022 are final; 2023 and 2024 are as revised; 2025 is the January vintage. With the later revision, 2025 "other fate" is 98,713 - 90,948 - 6,187 = 1,578K. The Track Records comparison table prints 2020 final harvested as 81,168 while the main table has 82,168; the percent-of-final column confirms 82,168.

Derived statistics (my arithmetic on the table):

- Silage acres 2000 to 2025: minimum 5,567K (2010), mean 6,302K, maximum 7,419K (2012), standard deviation about 401K. Mean absolute year-to-year change 362K; largest rise +1,484K (2011 to 2012); largest fall -1,148K (2012 to 2013).
- Silage share of planted: 6.28 percent (2025, the lowest of the 26 years) to 9.03 percent (2002); mean 7.2 percent.
- Other fates: 732K (2005) to 2,606K (2022); mean 1,446K.
- June forecast against January, harvested for grain: mean absolute gap 1,065K acres, median 766K, maximum 4,484K (2025). Excluding 2025 the mean is 928K. June was above January in 18 of 26 years.
- November forecast against January: mean absolute gap 431K acres, median 340K, maximum 1,637K (2022). Then 2002 (+1,228K) and 2025 (-1,211K).
- **The late switch, measured as the change in grain share between June and January:** mean absolute 0.68 points, about 595K acres. Extremes: 2002 -3.62 points (about -2.87 million acres), 2012 -2.23 points (about -2.17 million), 2022 -1.70 points (about -1.51 million), 2025 +1.23 points (about +1.22 million). The three large negative years are drought years in which grain acres were chopped or abandoned.
- 2012: silage 7,419K against 5,935K in 2011 (+25 percent); grain yield 123.1 bu/ac; silage yield 15.7 t/ac.

## 10. States: silage 2023 to 2025 (January 12, 2026 vintage)

| State | Planted 2025 | Grain 2025 | Silage 2023 | Silage 2024 | Silage 2025 | Silage t/ac 2025 | Silage % of planted 2025 | Other 2025 | Change 2024 to 2025 |
|---|---|---|---|---|---|---|---|---|---|
| United States | 98,788 | 91,258 | 6,461 | 6,207 | 6,208 | 21.8 | 6.3 | 1,322 | +1 (0%) |
| Wisconsin | 4,150 | 3,220 | 780 | 730 | 885 | 22.0 | 21.3 | 45 | +155 (+21%) |
| New York | 970 | 450 | 430 | 455 | 500 | 17.0 | 51.5 | 20 | +45 (+10%) |
| South Dakota | 6,850 | 6,350 | 520 | 410 | 390 | 17.0 | 5.7 | 110 | -20 (-5%) |
| California | 420 | 50 | 350 | 380 | 365 | 27.0 | 86.9 | 5 | -15 (-4%) |
| Minnesota | 8,900 | 8,450 | 350 | 380 | 360 | 23.0 | 4.0 | 90 | -20 (-5%) |
| Michigan | 2,350 | 1,980 | 320 | 325 | 350 | 22.5 | 14.9 | 20 | +25 (+8%) |
| Pennsylvania | 1,010 | 680 | 345 | 320 | 315 | 20.0 | 31.2 | 15 | -5 (-2%) |
| Idaho | 430 | 145 | 240 | 265 | 280 | 31.0 | 65.1 | 5 | +15 (+6%) |
| Texas | 2,500 | 2,140 | 280 | 160 | 265 | 22.0 | 10.6 | 95 | +105 (+66%) |
| Iowa | 13,550 | 13,200 | 380 | 340 | 250 | 25.0 | 1.8 | 100 | -90 (-26%) |
| Kansas | 6,850 | 6,500 | 330 | 310 | 230 | 23.0 | 3.4 | 120 | -80 (-26%) |
| Nebraska | 10,750 | 10,450 | 280 | 280 | 210 | 21.0 | 2.0 | 90 | -70 (-25%) |
| Colorado | 1,500 | 1,250 | 235 | 200 | 200 | 23.0 | 13.3 | 50 | 0 |
| Ohio | 3,400 | 3,160 | 160 | 160 | 200 | 22.0 | 5.9 | 40 | +40 (+25%) |
| North Dakota | 4,700 | 4,500 | 200 | 260 | 170 | 19.0 | 3.6 | 30 | -90 (-35%) |
| Indiana | 5,400 | 5,230 | 120 | 130 | 130 | 22.0 | 2.4 | 40 | 0 |
| Virginia | 470 | 350 | 100 | 95 | 100 | 21.0 | 21.3 | 20 | +5 (+5%) |
| Illinois | 11,200 | 11,000 | 90 | 90 | 90 | 20.0 | 0.8 | 110 | 0 |
| Washington | 200 | 110 | 85 | 101 | 89 | 27.0 | 44.5 | 1 | -12 (-12%) |
| Vermont | 95 | n/a | 80 | 85 | 84 | 18.0 | 88.4 | | -1 (-1%) |
| Missouri | 3,800 | 3,660 | 100 | 100 | 80 | 16.0 | 2.1 | 60 | -20 (-20%) |
| Kentucky | 1,520 | 1,420 | 80 | 70 | 70 | 21.0 | 4.6 | 30 | 0 |
| New Mexico | 105 | 44 | 69 | 51 | 59 | 23.0 | 56.2 | 2 | +8 (+16%) |
| Montana | 145 | 75 | 62 | 37 | 57 | 23.0 | 39.3 | 13 | +20 (+54%) |
| Utah | 85 | 33 | 46 | 50 | 51 | 24.0 | 60.0 | 1 | +1 (+2%) |
| Arizona | 65 | 16 | 66 | 50 | 48 | 29.0 | 73.8 | 1 | -2 (-4%) |

- **California 2025, verified:** planted 420K, harvested for grain 50K, silage 365K, 27.0 t/ac, 9,855 thousand tons. Other fate 5K.
- Top ten silage states hold 3,960K acres, 64 percent of the US total.
- **Gross movement 2024 to 2025: 469K acres up and 468K down across states (937K gross) for a national net of +1K.** 2023 to 2024: 766K gross, net -254K.
- NASS record notes for 2025: record-high silage acres in Idaho and Nevada; record-low in Alabama, Connecticut, Massachusetts, Rhode Island, West Virginia.

## 11. Market sensitivity: formulas and worked numbers

All of this section is my arithmetic on published figures.

- Value of 1 cent per bushel: `0.01 x production`. On 15.893 billion bu: $158.9 million. On 16.964 billion bu (2025 revised): $169.6 million. On 17.02 billion: $170.2 million.
- Production effect of an acreage change: `delta_bu = delta_acres_grain x yield`. 100K acres at 179.6 bu/ac = 17.96 million bu, 0.11 percent of the 2026 crop.
- November 2026 yield change: 1.6 bu x 88.506 million acres = 141.6 million bu; at $4.60 that is about $650 million of grain.
- A January-2026-sized acreage revision this year: 1,211K acres x 179.6 = 217.5 million bu, about 1.5 times the November yield change, about $1.0 billion at $4.60.
- Typical November-to-January acreage noise: 431K acres x 179.6 = 77 million bu.
- Typical national silage swing: 362K acres x 179.6 = 65 million bu, 0.4 percent of the crop.
- The 2012 swing: +1,484K silage acres at 123.1 bu/ac is about 183 million bu, 1.7 percent of that year's crop.
- NASS's own November noise floor: RMSE 1.3 percent of 15.893 billion = about 207 million bu.

Honest reading: nationally, the grain-versus-silage split is a second-order term next to planted-acre error and yield. It becomes first-order in drought years (2002, 2012, 2022) and in dairy states at any time.

## 12. Confidentiality

- 7 U.S.C. 2276(a): USDA may not disclose covered information "unless such information has been transformed into a statistical or aggregate form" that does not identify the supplier. Subsection (c): violators "shall be fined not more than $10,000 or imprisoned for not more than 1 year, or both."
- NASS confidentiality pledge: information "will be used for statistical purposes only" and "will not be disclosed in identifiable form to anyone other than employees or agents without your consent." It cites 7 U.S.C. 2276 and CIPSEA (Title III of Pub. L. 115-435, 44 U.S.C. Ch. 35): "a jail term of up to 5 years, a fine of up to $250,000, or both."
- Disclosure practice: when only one farm in a county grows a crop, NASS combines it with other counties. County estimates that fail publication standards are published as "Other Counties".
- CDL FAQ: "Please note that in no case are farmer reported data revealed or derivable from the public use Cropland Data Layer."

**Inference for Kernel:** these laws bind USDA and its agents, not a team using public imagery. But NASS could never publish field-level calls built from respondent or FSA data. A map built only from public pixels is legally a different object. Say that on a slide, and present county and state aggregates as the product, with field cards as analyst evidence.

## 13. Who uses these numbers

- **Agricultural Statistics Board:** sets the estimates by consensus; chair appointed April 2024 was Lance Honig (notice title).
- **World Agricultural Outlook Board (WASDE):** uses NASS area, yield and production directly in the US balance sheet; released alongside Crop Production (both dated November 10, 2026; the October 31, 2025 NASS notice lists WASDE as released together with the November 14, 2025 Crop Production report). The WASDE cover lists the Office of the Chief Economist, Agricultural Marketing Service, Farm Service Agency, Economic Research Service and Foreign Agricultural Service.
- **FSA and RMA:** "County yield data resulting from this survey are used by USDA for various programs, including those administered by USDA's Farm Service Agency (FSA) and Risk Management Agency (RMA)." They are also suppliers of the administrative acreage data.
- **Outside users named by NASS:** farm organizations, lenders, insurers, agribusiness, policy makers, commodity buyers.
- ERS use was not separately verified beyond the WASDE cover.

## 14. What this means for Kernel

### Build decisions

1. **Reconcile three buckets, not two.** Planted = grain + silage + other. Other was 1,322K acres in 2025 (1,578K after revision) and 2,606K in 2022. A two-class rollup cannot add up to NASS planted acres. Add an "other or unknown" bucket (abandoned, grazed, failed) even if it is rule-based.
2. **Fix the baseline number.** "Always grain" is right for 92.4 percent of planted acres (91,258 / 98,788), or 93.6 percent of harvested acres. Quote one, name the denominator.
3. **Use state-specific priors.** Silage share runs from 0.8 percent (Illinois) to 87 percent (California). A single national threshold will fail in both directions.
4. **Make the skeptic test the year-to-year change.** Can the model reproduce Wisconsin +155K, Texas +105K, Iowa -90K, Kansas -80K, Nebraska -70K, North Dakota -90K between 2024 and 2025? Dairy distance and rotation are static and cannot; only the in-season measured signals can. This is the cleanest evidence that the four measured numbers carry information.
5. **Treat "still standing in November" as evidence.** 26 percent of corn was unharvested on November 1, 2026, and 415K acres were still standing at the December 2025 survey. Residue features do not exist for those fields. A field that is brown and standing in November is almost surely grain; give it its own state rather than "needs review".
6. **Demo where NASS is weakest.** California, Idaho, New York, Pennsylvania, Wisconsin, plus one Corn Belt state as the "always grain" control. California has no monthly grain forecast at all.
7. **Report an "indication", with a CV.** That is the ASB's word. Show our state indication against the official estimate for 2023, 2024, 2025 as a scatter: this is literally how the ASB judges a data source ("historical relationship ... to the official estimate").
8. **Benchmark, then show both.** NASS benchmarks county model estimates to state totals. Do the same for back-years, and for 2026 show the raw indication with an interval, because there is no 2026 total to benchmark to.
9. **Do not count pixels.** NASS states pixel counting is biased low and uses a regression estimator. Use field-polygon acres times calibrated probability, then a ratio or regression adjustment fitted on back-years.

### What to say to USDA statisticians

- "On November 10 the silage cell for 2026 was blank. Ours is filled, with an interval."
- "Your reports say harvested acres can be revised any month 'if there is sufficient data'. This is a candidate for that data in October and November, instead of January."
- "Last January harvested area moved 1.2 million acres after the November report. At this year's yield that is 217 million bushels, more than this week's 141 million bushel yield change."
- "Your own CV on the grain share is 23 percent in California and 0.3 percent in Illinois. We aim at the first, not the second."
- "The December survey that produces silage acres had a 40 percent response rate in 2025, down from 56 percent in 2020. A satellite indication does not depend on response."
- "Public pixels only. No farmer-reported data in, none derivable out."

### Limits to state honestly

- National silage acres vary little (standard deviation about 0.4 million acres); the national corn balance sheet barely needs us in a normal year.
- Official silage truth is itself revised by up to about 2 percent, and county truth exists for 6 states only, in May.
- We have three years of state truth in hand (2023 to 2025). That is a thin backtest.

## 15. Recipes

**R1. State silage truth without an API key.** Fetch `https://release.nass.usda.gov/reports/cropan26.txt`. Parse the fixed-width table titled "Corn for Silage Area Harvested, Yield, and Production - States and United States: 2023-2025" (state name, then 3 area, 3 yield, 3 production columns). The table "Corn Area Planted for All Purposes and Harvested for Grain" gives planted and grain acres for the same years. `cropan25.txt` should give 2022 to 2024 in the same layout (not opened).

**R2. Long history.** `https://release.nass.usda.gov/reports/croptr26.txt`, table "Corn Area Planted and Harvested, Yield, Production, Utilization, Price, and Value - United States: 1866-2025" for silage acres, yield and tons since 1919, and "Corn Grain Area Harvested with Comparisons" for June, August, September, October, November, annual and final harvested acres.

**R3. Three-bucket reconciliation.** For state s: `other_s = planted_s - grain_s - silage_s`. Our rollup: `silage_hat_s = sum_i p_i x acres_i` over corn fields. Report `silage_hat_s / silage_s` for back-years, and the same for grain. Benchmarked version: multiply `p_i` by `silage_s / silage_hat_s` within state.

**R4. Skeptic chart.** x = NASS change in state silage acres 2024 to 2025, y = our change. One point per state. Add the 45-degree line.

**R5. Monthly file names on the release host.** `crop<MM><YY>.txt` (Crop Production), `cropan<YY>.txt` (annual summary released in January of YY), `acrg06<YY>.txt` (Acreage), `pspl03<YY>.txt` (Prospective Plantings), `croptr<YY>.txt` (Track Records).

## 16. Not verified, and unconfirmed leads

Could not be opened:

- January 2026 WASDE (HTTP 404 at the usda.gov path; archive host did not resolve). The $4.10 price and 2.227 billion stocks figures are second-hand.
- Farm Progress article "Corn plunges after USDA pegs U.S. crop at 17 billion bushels" (HTTP 403). No cents-per-bushel figure for the January 12, 2026 futures move.
- FSA Crop Acreage Data page (three timeouts).
- USDA reorganization memorandum (HTTP 403). No verified statement about NASS regional offices.
- NASS news releases for January 12 and November 10, 2026 (HTTP 404 at the guessed paths).

Leads from memory, not confirmed today. Do not cite them as fact:

- FSA publishes county-level crop acreage files from FSA-578 reports, monthly from August, and I believe they include an "intended use" field that separates grain from silage. If true this is a county-level, in-season, public prior and reconciliation target, and it would matter more than anything else in this brief.
- RMA Summary of Business by type and practice may separate corn insured as silage from corn insured as grain at county level.
- State NASS offices in several dairy states publish weekly "corn chopped for silage" progress, which would give a state-level harvest-window prior for the cut date.
- Which six states receive corn silage county estimates. Quick Stats will show it.

## 17. Annotated bibliography (all opened unless noted)

NASS reports (text):

- Crop Production, November 10, 2026. https://release.nass.usda.gov/reports/crop1126.txt . Forecast, blank 2026 silage cell, revised 2025 figures, estimating-procedures and revision-policy text, reliability table.
- Crop Production 2025 Summary, January 2026 (approved January 12, 2026). https://release.nass.usda.gov/reports/cropan26.txt . First 2025 silage acres by state; California; December Agricultural Survey description.
- Crop Production, November 14, 2025. https://release.nass.usda.gov/reports/crop1125.txt . The pre-January baseline.
- Crop Production, August 12 and September 12, 2025. https://release.nass.usda.gov/reports/crop0825.txt and https://release.nass.usda.gov/reports/crop0925.txt . Acreage updates after June.
- Crop Production, August 12, September 11 and October 9, 2026. https://release.nass.usda.gov/reports/crop0826.txt , https://release.nass.usda.gov/reports/crop0926.txt , https://release.nass.usda.gov/reports/crop1026.txt . 2026 trail; "satellite imagery" wording; reissue notes.
- Acreage, June 30, 2026; June 30, 2025; June 2024. https://release.nass.usda.gov/reports/acrg0626.txt , https://release.nass.usda.gov/reports/acrg0625.txt , https://release.nass.usda.gov/reports/acrg0624.txt . Planted and to-be-harvested-for-grain; change in stated survey basis.
- Prospective Plantings, March 31, 2026. https://release.nass.usda.gov/reports/pspl0326.txt .
- Crop Production Historical Track Records, April 2026. https://release.nass.usda.gov/reports/croptr26.txt . All of section 9.

NASS methodology:

- Annual Crop Production Methodology and Quality Measures, February 4, 2026. https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02_2026/cranqm26.pdf . Response rates by state, CVs, ASB process.
- Earlier editions: https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02-2025/cranqm25.pdf , .../02-2024/cranqm24.pdf , .../02-2023/cranqm23.pdf , .../01_2022/cranqm22.pdf . Response-rate series 2020 to 2024.
- Row Crops County Estimates Methodology and Quality Measures, June 5, 2026. https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/County_Estimates_Row_Crops/06_2026/rcceqm26.pdf . Six silage states, small-area model, FSA and RMA inputs.
- Index pages: https://www.nass.usda.gov/Publications/Methodology_and_Data_Quality/Crop_Production/index.php and https://www.nass.usda.gov/Publications/Methodology_and_Data_Quality/County_Estimates_Row_Crops/index.php .

NASS calendar and notices:

- 2026 release calendar. https://www.nass.usda.gov/Publications/Calendar/2026/NassReleases2026.ics ; https://www.nass.usda.gov/publications/reports-by-release-day .
- Notices index. https://www.nass.usda.gov/Newsroom/Notices/index.php .
- April 9, 2024 (cancellations). https://www.nass.usda.gov/Newsroom/Notices/2024/04-09-2024.php .
- April 4, 2024 (program review). https://www.nass.usda.gov/newsroom/notices/2024/04-04-2024 .
- July 31, 2024 (acreage review). https://www.nass.usda.gov/newsroom/notices/2024/07-31-2024 .
- March 19, 2025 (reinstatement). https://www.nass.usda.gov/newsroom/notices/2025/03-19-2025 .
- August 28, 2025 (Mink and Agricultural Labor surveys). https://www.nass.usda.gov/newsroom/notices/2025/08-28-2025 .
- October 31 and November 19, 2025 (lapse in funding). https://www.nass.usda.gov/newsroom/notices/2025/10-31-2025 , https://www.nass.usda.gov/newsroom/notices/2025/11-19-2025 .
- October 23 and 24, 2026 (September corn correction). https://www.nass.usda.gov/newsroom/notices/2026/10-23-2026 , https://www.nass.usda.gov/newsroom/notices/2026/10-24-2026 .

Other USDA and law:

- WASDE-677, November 10, 2026. https://www.usda.gov/oce/commodity/wasde/wasde1126.txt and https://www.usda.gov/oce/commodity/wasde/wasde1126.pdf .
- Cropland Data Layer FAQ. https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php .
- NASS Cropland / CropScape page. https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php .
- NASS Confidentiality Pledge. https://www.nass.usda.gov/About_NASS/Confidentiality_Pledge/index.php .
- 7 U.S.C. 2276. https://www.law.cornell.edu/uscode/text/7/2276 .

Press and university:

- Hanrahan, R., "USDA Says 2025 Corn Production Hit 17 Billion Bushels, Likely to Keep Prices Low", Farm Policy News, University of Illinois, January 13, 2026. https://farmpolicynews.illinois.edu/2026/01/usda-says-2025-corn-production-hit-17-billion-bushels-likely-to-keep-prices-low/ .
- Neeley, T., "Record 17 Billion Bushel Corn Crop", DTN Ethanol Blog, January 12, 2026. https://www.dtnpf.com/agriculture/web/ag/blogs/ethanol-blog/blog-post/2026/01/12/record-17-billion-bushel-corn-crop .
- Johansson, R., A. Effland and K. Coble, "Falling Response Rates to USDA Crop Surveys: Why It Matters", farmdoc daily (7):9, January 19, 2017. https://farmdocdaily.illinois.edu/2017/01/falling-response-rates-to-usda-crop-surveys.html .
- Not opened (403): https://www.farmprogress.com/marketing/corn-plunges-after-usda-pegs-u-s-crop-at-17-billion-bushels .
