# Stakeholders and value: who gains what from an earlier, explainable silage-versus-grain estimate

Research report for team Kernel, Hack the Harvest. Written Saturday 2026-11-14.
Topic owner: stakeholders agent. Only this file was written in the project.

## 0. How this was researched, and what that limits

- **WebSearch was not available.** The shared web-search budget for this run was already used up when this agent started (four searches attempted, zero performed). The brief asked for 12 or more searches; none could be run.
- Everything below therefore comes from **primary documents fetched directly by URL** (NASS release server, Cornell LII for statutes and the CFR, California State Water Board, San Joaquin Valley air district, ERS, CDFA, Iowa State, Penn State, FCSM). The 33 sources listed in section 11 were opened and read. Numbers taken from NASS text reports, the Water Board order, Rule 4570, the Iowa custom-rate survey and the FCSM framework were checked against the raw text, not only against a model summary.
- PDFs could not be read by the fetch tool, so a small standard-library text extractor was written to the session scratchpad (`<session scratchpad, not in the repo>`). It is outside the repo and can be deleted.
- **Not opened** (listed in section 12 with reasons): the whole RMA website and ESMIS (DNS failure), eCFR (bot wall), FSA pages (timeouts), DWR/CNRA crop mapping (403), three journal articles (403/404), a CRS report (403). Consequences: **no verified corn-specific crop-insurance liability, no verified soil-loss ratio for silage versus grain, no verified futures price-reaction study, no verified silage share of the California ration.** These gaps are marked where they matter. Do not quote numbers for them on stage.
- Anything prefixed **Inference:** is this agent's arithmetic or reasoning on top of opened sources. Anything marked **from memory, unverified** was not opened.

## 1. Bottom line

1. **The customer is the Agricultural Statistics Board, and the door is already open.** NASS's own November 2026 methodology text says the Board "reviews multiple data sources ... including USDA administrative acreage data, satellite imagery, and objective yield and grower reported data", and that "harvested acres may be revised any time a production forecast is made if there is sufficient data indicating that the intended harvested area has changed" [N2]. Pitch Kernel as one more *indication* for that review, about two months before the first silage number, not as a replacement for the December survey.
2. **The national silage total barely moves; the state map moves a lot.** 2024 to 2025: United States +1 thousand acres (6,207 to 6,208). Same year: Wisconsin +155 (+21%), Texas +105 (+66%), Iowa -90 (-26%), North Dakota -90 (-35%), Kansas -80 (-26%), Nebraska -70 (-25%) [N1]. "Same as last year" misallocates 937 thousand acres, 15% of the total. That is the benchmark to beat, not 94% accuracy.
3. **The class prior is a state fact, not a national one.** Silage share of planted corn in 2025: California 87%, Idaho 65%, New York 52%, Pennsylvania 31%, Wisconsin 21%, Texas 11%, Iowa 1.8%; United States 6.3% [N1]. And 1.3 to 1.7 million planted acres a year are neither grain nor silage.
4. **Grain-market stake.** As of 10 November 2026: 96.8 million acres planted, 88.5 million forecast harvested for grain, so 8.27 million acres will not be combined [N2]. How many were chopped is unpublished until January. Inference: each 100 thousand acres moved between silage and grain is about 18 million bushels; 1 million acres is about 10% of projected ending stocks [N2, W1].
5. **California has a second, brand-new customer.** On 15 September 2026 the State Water Board adopted Order WQ 2026-0028: all Central Valley dairies (about 1,300) must move to measured, reported nitrogen applied and nitrogen removed per crop; the Board says today's reported ratios are "estimates based on broad averaging schemes" [C1, C2]. Nitrogen removed depends directly on whether the whole plant was chopped.

## 2. The numbers that frame the stakes

### 2.1 Where US corn acres go (thousand acres)

| | 2023 | 2024 | 2025 (Jan 2026 estimate) | 2025 (as revised, shown Nov 2026) | 2026 (Nov 1 forecast) |
|---|---|---|---|---|---|
| Planted, all purposes | 94,641 | 90,909 | 98,788 | 98,713 | 96,777 |
| Harvested for grain | 86,506 | 83,046 | 91,258 | 90,948 | 88,506 |
| Harvested for silage | 6,461 | 6,207 | 6,208 | 6,187 | blank until January |
| Planted minus grain | 8,135 | 7,863 | 7,530 | 7,765 | 8,271 |
| Other fates (planted - grain - silage) | 1,674 | 1,656 | 1,322 | 1,578 | unknown |
| Not-for-grain share of planted | 8.60% | 8.65% | 7.62% | 7.87% | 8.55% |

Sources: [N1] for 2023 to 2025 January estimates; [N2] for revised 2025 and the 2026 forecast. The last three rows are Inference (subtraction).

Other verified national figures:
- Corn for grain 2025: yield 186.5 bu/acre, production 17,020,549 thousand bu (January) revised to 16,963,628 thousand bu; 2026 forecast 179.6 bu/acre, 15,893,419 thousand bu [N1, N2].
- Corn silage 2025: yield 21.8 tons/acre, production 135,540 thousand tons, "a record high 136 million tons ... up 8 percent"; revised to 135,090 thousand tons [N1, N2]. 2024: 125,590 thousand tons; 2023: 129,854 thousand tons [N1].
- Inference: about 80% of the not-for-grain acreage is silage (79.4% in 2023, 78.9% in 2024, 82.4% in 2025); the rest is abandoned, grazed, hayed or lost.

### 2.2 State silage area, and how wrong "same as last year" is (thousand acres, [N1])

| State | 2023 | 2024 | 2025 | 2024 to 2025 | 2025 yield t/ac | 2025 tons (000) | Silage share of planted 2025 |
|---|---|---|---|---|---|---|---|
| Wisconsin | 780 | 730 | 885 | +155 (+21%) | 22.0 | 19,470 | 21.3% |
| New York | 430 | 455 | 500 | +45 (+10%) | 17.0 | 8,500 | 51.5% |
| South Dakota | 520 | 410 | 390 | -20 (-5%) | 17.0 | 6,630 | 5.7% |
| California | 350 | 380 | 365 | -15 (-4%) | 27.0 | 9,855 | 86.9% |
| Minnesota | 350 | 380 | 360 | -20 (-5%) | 23.0 | 8,280 | 4.0% |
| Michigan | 320 | 325 | 350 | +25 (+8%) | 22.5 | 7,875 | 14.9% |
| Pennsylvania | 345 | 320 | 315 | -5 (-2%) | 20.0 | 6,300 | 31.2% |
| Idaho | 240 | 265 | 280 | +15 (+6%) | 31.0 | 8,680 | 65.1% |
| Texas | 280 | 160 | 265 | +105 (+66%) | 22.0 | 5,830 | 10.6% |
| Iowa | 380 | 340 | 250 | -90 (-26%) | 25.0 | 6,250 | 1.8% |
| Kansas | 330 | 310 | 230 | -80 (-26%) | 23.0 | 5,290 | 3.4% |
| Nebraska | 280 | 280 | 210 | -70 (-25%) | 21.0 | 4,410 | 2.0% |
| Colorado | 235 | 200 | 200 | 0 | 23.0 | 4,600 | n/a |
| North Dakota | 200 | 260 | 170 | -90 (-35%) | 19.0 | 3,230 | n/a |
| United States | 6,461 | 6,207 | 6,208 | +1 (+0.02%) | 21.8 | 135,540 | 6.3% |

Persistence benchmark (Inference, computed from the 48-state table in [N1]):

| Forecast "same as last year" | Sum of absolute state errors | As % of US silage area | Mean absolute % error, 18 states with 100 thousand acres or more | Net US change |
|---|---|---|---|---|
| 2023 to 2024 | 766 thousand acres | 12.3% | 10.4% | -254 |
| 2024 to 2025 | 937 thousand acres | 15.1% | 16.4% | +1 |

The top ten states hold 63.8% of 2025 silage area.

### 2.3 How good is the official November number, and how often is it revised

- NASS on its own November 1 corn forecast: root mean square error 1.3%; 90% interval 2.3%; over the last 20 years the change from the November forecast to the final estimate "averaged 144 million bushels, ranging from 4 million bushels to 420 million bushels"; the November forecast was below final 7 times and above 13 times [N2].
- Revisions after January are real. Between the 11 September and 10 November 2026 reports, the 2025 crop was revised: planted 98,788 to 98,713; harvested for grain 91,258 to 90,948 (-310 thousand acres); grain production -57 million bu; silage 6,208 to 6,187 thousand acres (-21) and 135,540 to 135,090 thousand tons [N1, N2, N3].
- California, medium confidence: the January 2026 summary shows 2025 corn planted 420, grain 50, silage 365 thousand acres [N1]. The NASS State Agriculture Overview drawn from Quick Stats on 14 November 2026 shows planted 450,000, grain 75,000 acres (173 bu, 12,975,000 bu) and silage 370,000 acres (9,990,000 tons) [N6]. Inference: California's 2025 grain area was revised up 50% and planted up 7%. The page layout is ragged; confirm in Quick Stats before quoting.

### 2.4 The grain balance sheet the silage number feeds (WASDE-677, November 2026, [W1])

| Corn, million bu unless noted | 2024/25 | 2025/26 est. | 2026/27 proj. Oct | 2026/27 proj. Nov |
|---|---|---|---|---|
| Area harvested (million acres) | 83.0 | 90.9 | 88.5 | 88.5 |
| Yield (bu/acre) | 179.3 | 186.5 | 181.2 | 179.6 |
| Production | 14,892 | 16,964 | 16,034 | 15,893 |
| Feed and residual | 5,435 | 6,118 | 6,000 | 5,975 |
| Ethanol and by-products | 5,437 | 5,548 | 5,650 | 5,650 |
| Exports | 2,873 | 3,429 | 3,300 | 3,275 |
| Ending stocks | 1,551 | 2,095 | 1,849 | 1,758 |
| Average farm price ($/bu) | 4.24 | 4.16 | 4.70 | 4.60 |

Inference (arithmetic on [N2] and [W1]):
- 100 thousand acres between silage and grain = 18.0 million bu at 179.6 bu/acre, about $83 million at $4.60.
- 1 million acres = 179.6 million bu = 1.13% of 2026 production = 10.2% of projected ending stocks.
- The 2023 to 2025 range of the not-for-grain share (7.6% to 8.7%) applied to 96.8 million planted acres spans about 1.0 million acres.
- NASS's average November-to-final change of 144 million bu is the grain from about 800 thousand acres, about $660 million at $4.60; the largest (420 million bu) about $1.9 billion.
- 2025 silage acres, had they been combined at the national yield, would be about 1.16 billion bu, 6.8% of the grain crop.

No futures price-reaction study was opened. Do not state a cents-per-bushel effect.

### 2.5 Dollar values

| Item | Value | Source |
|---|---|---|
| US corn for grain, value of production 2025 (preliminary) | $70.10 billion at $4.10/bu (2024: $63.40 billion at $4.24; 2023: $70.09 billion at $4.55) | [N4] |
| US corn silage, official price or value | none published: the Crop Values report has no silage line | [N4] |
| Standing silage rule of thumb | 8 to 10 times the price of a bushel of corn per ton at 65% moisture; 10 to 12 times once harvested and stored | [X1] |
| US corn silage 2025, imputed | Inference: 135.54 million tons x $4.10 x (10 to 12) = $5.6 to 6.7 billion stored; $4.4 to 5.6 billion standing | [N1, N4, X1] |
| Buyer-seller bargaining range, Iowa worked example | $22.90 to $33.48 per ton standing (170 bu/acre, $3.25 corn, 23 tons/acre) | [X1] |
| Federal crop insurance, all crops 2024 | more than $192 billion liability, 543 million acres, $10.4 billion premium subsidy; row crops 65% of liability; about 89% of acreage of eight major crops enrolled | [E1] |
| Corn-specific insurance liability | not opened (RMA site unreachable). Do not quote. | - |
| California milk, 2025 | $8.39 billion, California's top commodity; total farm cash receipts $64.7 billion | [C4, N6] |
| Custom silage chopping, Iowa 2026 | $9.20/ton average (range $7.00 to $12.00); corn combining $46.05/acre; complete grain harvest $82.00/acre; earlage or snaplage chopping $84.75/acre | [X2] |

Inference: at 21.8 tons/acre, chopping alone is about $200/acre, 2.4 to 4.4 times the custom revenue of a combined acre. An upper bound for the national chopping bill is $1.25 billion a year (all tons at the Iowa rate; many farms own choppers).

### 2.6 Dairy

| | 2024 | 2025 | Source |
|---|---|---|---|
| US milk cows (thousand, annual average) | 9,345 | 9,498 | [N5] |
| US milk production (million lb) | 225,889 | 231,658 | [N5] |
| California milk cows (thousand) | 1,708 | 1,712 | [N5] |
| California milk production (million lb) | 40,288 | 40,950 (17.7% of US, Inference) | [N5] |
| Wisconsin milk cows / milk | 1,269 / 32,332 | 1,273 / 32,588 | [N5] |
| Idaho, Texas, New York milk cows 2025 | | 714, 696, 642 | [N5] |

- Central Valley: "89 percent of the state's cows and 81 percent of the state's dairy farms" (a 2013-era estimate quoted in [C1], p. 9); about 1,300 dairies under the Central Valley dairy order [C2]. Inference: roughly 1.5 million cows and about $7.5 billion of milk.
- Inference from [N1, N5]: California harvests 9.855 million tons of corn silage for 1.712 million milk cows, 5.76 tons per cow per year, 31.5 lb as fed per cow per day, 9.5 to 11 lb dry matter at 30 to 35% dry matter. If a lactating cow eats about 50 to 55 lb dry matter a day (from memory, unverified), corn silage is roughly a fifth of the ration; heifers, dry cows and storage losses are ignored. The published ration share was not opened.
- US: 135.5 million tons over 9.5 million dairy cows is 14.3 tons per cow, but beef feedlots in Kansas, Nebraska, Texas, Colorado and South Dakota also feed silage (from memory, unverified), so do not present that as a dairy ration figure.

### 2.7 What leaves the field (the residue and nutrient mechanism)

- Penn State: "Corn silage production leaves little crop residue on the soil" and "can also lead to an increased potential for soil erosion"; it recommends "a winter rye or ryegrass cover crop and reducing or eliminating tillage" [X3].
- Nutrients in the harvested crop, 150 bu grain versus the same field as 25 tons silage, lb/acre: nitrogen 114 versus 259; phosphorus 22 versus 40; potassium 28 versus 230 [X3].
- Iowa State: for normal-yielding corn "grain and stover contribute roughly equal dry matter"; 1 bu of 15% moisture corn is equivalent to 0.135 tons of 65% moisture silage [X1]. Inference: a silage cut removes about twice the dry matter of a grain harvest and leaves stubble only.
- **A numeric soil-loss ratio for silage versus grain was not verified** (three journal pages failed). Say "leaves little residue" with the Penn State citation; do not give a multiple.

## 3. Calendar: when each number exists

| Date (2026 season) | Event | What is known about silage versus grain | Source |
|---|---|---|---|
| 30 June | NASS Acreage | planted corn; harvested-for-grain intentions | [N8] |
| 15 July | FSA acreage report, "a major deadline for most crops" | each field's crop and "intended use" reported to FSA; shared electronically with RMA; not public | [F1, L3] |
| 12 Aug, 11 Sept, 9 Oct, 10 Nov, 10 Dec | NASS Crop Production | grain forecast only; silage cells blank | [N2, N3, N8] |
| 30 Sept (20 Oct in listed states incl. Idaho, Oregon, Washington, New York) | end of insurance period, corn insured as silage | hard regulatory anchor for silage cut dates | [L1] |
| 30 Sept (listed south Texas counties), 31 Oct (listed Washington counties), 10 Dec (everywhere else) | end of insurance period, corn insured as grain | the CFR itself documents "early is not silage" for south Texas | [L1] |
| December | December Agricultural Survey, about 73,100 operators | farmer-reported silage and grain acres | [N1] |
| mid January (12 Jan in 2026) | Crop Production Annual Summary | first official silage acres, yield, tons by state | [N1, N8] |
| late February (27 Feb in 2026) | Cropland Data Layer for the previous season | corn pixels, no silage class | [N9] |
| late February (26 Feb in 2026) | Crop Values | grain value; no silage value | [N4, N8] |
| the following autumn | revisions | 2025 grain area cut 310 thousand acres; silage cut 21 thousand | [N2, N3] |

Consequence for Kernel: the current-year CDL does not exist in November. An operational early estimate needs a corn mask from prior-year CDL plus rotation (Crop Sequence Boundaries) or its own in-season corn classification. Say this plainly in the feasibility section.

## 4. Stakeholder by stakeholder

Evidence grade: **A** = primary source with numbers opened; **B** = primary source, qualitative; **C** = inference or memory, not verified.

### 4.1 USDA NASS (grade A)

- **Who.** The Agricultural Statistics Board, which sets the official estimates; the Regional Field Offices, each of which "submits an estimate and written analysis for their State" [N1]; the NASS research group that produces the Cropland Data Layer and Crop Sequence Boundaries [N9, N10].
- **Job.** Official state and national corn area harvested for grain and for silage, yield and production; monthly grain forecasts August to November; finals in January; revisions later.
- **Pain.** No silage figure exists before January. Monthly reports carry blank silage cells [N2]. Harvested-for-grain area is carried forward from intentions unless "there is sufficient data indicating that the intended harvested area has changed" [N2]. State totals swing 20 to 66% in a year while the national total hides it (section 2.2). January figures are later revised (section 2.3).
- **What an early field-level signal changes.** A state and county "indication" in late October or November: share of corn area cut green, share standing or combined, share neither, each with a standard error, plus per-field evidence an analyst can audit. It slots into the review the Board already describes: "USDA administrative acreage data, satellite imagery, and objective yield and grower reported data" [N2].
- **Stakes.** 6.2 million acres and 135.5 million tons a year with no in-season number [N1]; 8.27 million planted acres in 2026 whose fate is unpublished [N2]; November-to-final changes averaging 144 million bu [N2].
- **Adoption barriers.** Needs an unbiased area estimator with measures of error, not pixel counts. Needs coherence with survey definitions (does "silage" include greenchop, earlage, snaplage?). Small labelled set. Must run every year, the same way. Cloud gaps. Market sensitivity: the number would have to live inside the Board's secure process or be released to everyone at once. Training data inside NASS (FSA field records) is confidential; Kernel must show it works on public inputs only.

### 4.2 WAOB (WASDE) and ERS feed-grains analysts (grade A for numbers, C for process)

- **Who.** The World Agricultural Outlook Board's feed-grains balance-sheet committee and ERS Feed Outlook analysts (committee structure from memory, unverified).
- **Job.** The US corn supply and use table: area harvested, yield, production, feed and residual, ethanol, exports, ending stocks, price [W1].
- **Pain.** Area harvested is the single largest lever on production and is known only as a forecast until January. "Feed and residual" (5,975 million bu projected for 2026/27) absorbs every error, and silage, the direct substitute for grain in rations, has no line in the table [W1]. ERS's sector overview does not mention silage at all [E2].
- **Change.** An earlier check on harvested-for-grain area and a forage-supply indicator that helps interpret feed and residual.
- **Stakes.** 1 million acres = 180 million bu = 10% of projected ending stocks (Inference, section 2.4).
- **Barriers.** WASDE takes US area and production from NASS; the route to WAOB runs through the Board (from memory, unverified).

### 4.3 USDA RMA and crop insurers (grade A for rules, unverified for corn dollars)

- **Who.** RMA compliance and actuarial staff; private insurers' loss adjusters; the data-mining contractor RMA is required to use.
- **Rules that hard-code silage versus grain** (7 CFR 457.113, [L1]):
  - Corn is insurable when "planted for harvest either as grain or as silage" (section 6(b)(1)). Whether a county offers grain rates, silage rates or both is set by the county actuarial documents; where only one type has rates, the other needs a written agreement (section 6(c)).
  - If acreage will be harvested "in a manner other than as you reported", the grower "must notify us before harvest begins" (section 11(c)). Without timely notice, production to count is appraised at not less than the guarantee (section 12(c)(1)(i)(E)). Inference: that leaves no indemnity payable on that acreage.
  - Silage is counted in tons. If appraised grain content is below 4.5 bu per ton of silage, production is reduced 1 percentage point per 0.1 bu shortfall; late-harvested or late-appraised silage is adjusted to "a 65 percent moisture equivalent" (section 12(e)).
  - End of insurance period: silage 30 September (20 October in listed states); grain 10 December (30 September in listed south Texas counties; 31 October in listed Washington counties) (section 8).
  - "Harvest" is defined as "combining, threshing, or picking the insured crop for grain, or cutting for hay, silage, earlage, snaplage, or fodder" (section 1).
- **Integrity mandate** (7 U.S.C. 1515, [L2]): annual reconciliation of producer information between FCIC and FSA; FSA assists monitoring and uses published NASS aggregates to "detect yield disparities or other data anomalies"; the Secretary must use "data mining and data warehousing"; funding of $4 million a year through fiscal 2025 and $6 million a year from fiscal 2026.
- **Pain.** In a drought year, corn insured as grain is chopped. The adjuster must appraise before the chopper arrives, and a field chopped without notice becomes a dispute. Tonnage and grain content vary widely.
- **Change.** A cut-date and green-at-cut flag per insured unit is a triage list: which grain-typed fields were cut green, and when. It protects growers who did give notice and focuses reviews on the few that did not.
- **Stakes.** Program-wide: more than $192 billion liability and $10.4 billion premium subsidy in 2024 [E1]. Corn-specific liability: not opened.
- **Barriers.** Policy-level data are confidential; this is an internal tool, never a public map. Reported type can change legitimately with notice. A false flag costs an adjuster visit, so precision at the top of the list matters more than recall.
- **Unverified lead.** RMA's public Summary of Business files by type and practice may list insured corn acres as grain or silage by county and year. If true, that is a free county-level prior and a second reconciliation target. Not opened (DNS failure). Someone with normal internet should check tonight.

### 4.4 Farm Service Agency (grade B)

- **Who.** County offices that take acreage reports; program compliance staff.
- **Job.** Acreage reports list "crop and crop type or variety", "intended use of the crop", acres, a map, planting dates, shares and irrigation practice; they support crop insurance, safety-net and disaster programs and are used to "verify conservation compliance on highly erodible land and wetlands" [F1].
- **Pain.** Intended use is declared around 15 July; the harvest decision is made in August to October. Nothing records the switch except an insurance notice.
- **Change.** An observed-use layer next to the reported-use layer for spot-check targeting and faster forage-shortfall assessment after drought.
- **Stakes.** Not quantified here: the Livestock Forage Disaster Program, emergency livestock assistance and ARC/PLC pages were not opened (timeouts).
- **Barriers.** 7 U.S.C. 8791 forbids disclosing producer-provided information and USDA's geospatial information about agricultural land, except in "statistical or aggregate form" [L3]. Internal use only.

### 4.5 NRCS and conservation programs (grade B)

- **Who.** Field offices doing highly-erodible-land compliance status reviews; EQIP and CSP practice certification.
- **Job.** Confirm conservation systems are applied on highly erodible cropland and that paid practices (cover crops, residue management) happened.
- **Pain.** Silage "leaves little crop residue on the soil" [X3]. Inference: a grain-to-silage switch on highly erodible land can take a field below the residue level its conservation system assumes, and nothing reports the switch.
- **Change.** A list of fields cut for silage with no green-up afterwards (no cover crop), and the cut date itself, which sets the cover-crop planting window (a September silage cut gives weeks more growth than a November grain harvest).
- **Stakes.** A producer out of compliance on highly erodible land "shall be ineligible for" commodity payments, farm storage loans, disaster payments, FSA loans, conservation payments and the federal share of crop insurance premiums (16 U.S.C. 3811, [L5]). Nutrient removal: 259 versus 114 lb nitrogen and 230 versus 28 lb potassium per acre [X3]. Erosion multiple: not verified.
- **Barriers.** Highly-erodible determinations and field records are not public. The residue index is confounded by soil moisture and tillage.

### 4.6 Dairy farmers, nutritionists and feed buyers (grade A for scale, C for behaviour)

- **Job.** Lock in a year of forage by October; set rations; decide how much hay, grain and by-product to buy.
- **Pain.** No public price and no public inventory. Silage is priced by formula off corn (8 to 10 times the bushel price per ton standing; 10 to 12 stored) [X1]; the Crop Values report has no silage line [N4].
- **Change.** A county and milkshed silage-supply map in October: regional tons harvested versus a normal year, which feeds straight into hay and grain demand.
- **Stakes.** 135.5 million tons, an imputed $5.6 to 6.7 billion stored [N1, X1]; California 9.9 million tons for 1.71 million cows producing $8.39 billion of milk [N1, N5, N6].
- **Barriers.** Each dairy already knows its own fields; the value is only in the regional aggregate. Trust in an unofficial number.

### 4.7 Neighbouring grain farmers who sell standing corn (grade A)

- **Job.** Decide in August whether to sell a field standing to a dairy or take it to grain, and at what price.
- **Pain.** A thin, private, bilateral market. Iowa State's worked example gives a seller minimum of $22.90 and a buyer maximum of $33.48 per ton standing, a 46% spread to bargain over [X1].
- **Change.** Local evidence of how much corn is being chopped this year strengthens whichever side is short.
- **Barriers.** Small transactions; privacy sensitivity about who sold what.

### 4.8 Custom forage harvesters (grade A for rates, C for use)

- **Job.** Route choppers, trucks and packing tractors through a harvest window of a few days per field.
- **Stakes.** $9.20/ton average in Iowa in 2026, $77.40 per hour per head row [X2]; about $200/acre at the national average yield (Inference).
- **Change.** Demand forecasting by county; year-over-year swings of 20% or more in state area (section 2.2) are swings in their book of work.
- **Barriers.** They already know their clients; marginal value.

### 4.9 Grain elevators, ethanol plants and feed mills (grade C)

- **Job.** Originate grain; set local basis.
- **Change.** Early county-level view of bushels that will not be delivered. Inference: Wisconsin's +155 thousand silage acres in 2025 is about 29 million bu, 4.8% of the state's grain crop [N1].
- **Context.** Ethanol is "nearly 45 percent of total corn use"; feed "about 40 percent of total domestic corn use" [E2].
- **Barriers.** Private originators' knowledge; antitrust sensitivity around shared supply intelligence. No primary source on basis effects was opened.

### 4.10 Commodity traders and analysts (grade A for the uncertainty, none for price effects)

- **Job.** Anticipate the January harvested-area and production numbers.
- **Pain.** The November forecast has been above the final 13 times in 20 years, with an average miss of 144 million bu [N2].
- **Change.** A public, reproducible indicator narrows what is otherwise private satellite intelligence.
- **Barriers.** They are also the reason NASS guards release timing. An open method released to all at once is the answer.

### 4.11 Agricultural lenders (grade C)

- Feed inventory is a balance-sheet item on dairies and feedlots; an independent harvested-tons estimate helps verify borrowing bases. No source opened. Leave out of the pitch.

### 4.12 California state agencies (grade A)

**State and Central Valley water boards (dairy nitrogen).** The strongest non-USDA customer found.
- Order WQ 2026-0028, adopted 15 September 2026 on review of the Central Valley dairy general order R5-2013-0122, which covers "approximately 1,300 existing milk cow dairies" [C1, C2].
- A 1,000-cow dairy generates "approximately 365,000 pounds of nitrogen" a year. Dairy manure is nearly 20% of nitrogen applied to Central Valley agricultural land and one third in the San Joaquin Valley and Tulare Lake Basin ([C1], pp. 10-11, citing a 2017 UC Davis study).
- Corn silage is named: "a major commodity commonly grown by dairies as a summer forage crop", needing 200 to 275 lb nitrogen per acre for 28 to 33 tons per acre, against an estimated average manure application of 890 lb nitrogen per acre per year on dairy cropland. Dairies "commonly grow two to three crops at different seasons throughout a year in the same field". About 400,000 acres grew dairy crops with manure in 2007-2008 ([C1], pp. 11-12).
- Compliance metric: nitrogen applied over nitrogen removed in the harvested crop, limit 1.4, a 1.65 trigger, 1.1 for new dairies, and an illustrative step-down to 1.35, 1.3, 1.25 within three, six and nine years ([C1], pp. 20-21, 82, 86).
- The Board's own finding: reported ratios "are estimates based on broad averaging schemes and do not represent accurate individual field calculations"; crops are "harvested on an overlapping basis and not on a per-field basis" ([C1], p. 96).
- New requirement: within two years the Central Valley board must order every dairy to measure and report, through the state GeoTracker database, commodities grown, location and acreage per commodity, assessor's parcel number, yield per commodity, and nitrogen removed as yield times a crop coefficient, annually and as a three-year rolling average ([C1], pp. 97-99).
- **Change.** Nitrogen removed depends on what was taken off: whole plant or grain only (259 versus 114 lb nitrogen per acre in the Penn State comparison [X3]) and on how many crops were harvested. Inference: at a 1.4 limit that is the difference between about 363 and 160 lb of allowable nitrogen per acre. A satellite record of harvest type, cut date and number of harvests per field is an independent check on the reported "R".
- **Barriers.** This is enforcement-adjacent and will be read that way by dairies. Frame it as lower reporting burden and independent confirmation. Yield in tons still has to come from the dairy.

**San Joaquin Valley air district (silage VOC).** Rule 4570, Confined Animal Facilities, adopted 2006, amended 21 October 2010, "to limit emissions of volatile organic compounds"; applies to dairies at 500 milking cows since 22 October 2010 [C3]. Silage measures include covering piles, bulk density of at least 44 lb per cubic foot for corn silage, exposed-face limits (2,150 square feet for one pile), and, as one compliance option, "Harvest silage crop at >=65% moisture for corn" [C3]. That is Kernel's green-at-cut number written into an air rule.

**CDFA.** Milk is the state's top commodity at $8.39 billion in 2025 [C4]; CDFA's fertilizer research programme supplies the corn nitrogen guidelines the Water Board cites [C1].

**DWR.** Crop water use and the statewide field-level crop map: pages returned 403. Unverified lead: DWR publishes field polygons with multi-cropping flags that could validate California double-crop detection.

### 4.13 Carbon and climate MRV (grade B)

- Precedent: CTIC's OpTIS maps tillage, residue cover and winter cover from satellites for the lower 48 states, 2015 to 2021; calculations are at farm-field scale, results are published aggregated to regions and watersheds so that "the privacy of individual producers is fully protected" [O1].
- **Change.** Silage removal is the largest residue-removal event in corn; a harvest-type layer corrects residue-input assumptions in soil-carbon accounting.
- **Barriers.** Project-level verification needs grower consent; Kernel's aggregates are context, not verification.

### 4.14 Researchers and extension (grade B)

- **Change.** An open, reproducible workflow on public inputs and a labelled benchmark for a problem the CDL does not address (it has a corn class and four double-crop corn classes, no silage class [N9]). NASS's Crop Sequence Boundaries give public, non-confidential field polygons with "no personal identifying information", latest set 2018-2025 released 27 March 2026 [N10].
- **Barriers.** None beyond data volume.

### 4.15 International users (grade C)

- GEOGLAM Crop Monitor bulletins "detail in-season crop conditions and anticipated yield outcomes" for the major grains from NDVI, precipitation, temperature and soil moisture; the site says nothing about harvest use [I2]. A silage-versus-grain split is not something AMIS currently consumes.
- The European Union harvested 58.9 million tonnes of grain maize and corn-cob mix from 8.7 million hectares in 2024, and tracks green maize as a separate crop [I1]; the green-maize totals and definition were not opened. Inference: the method transfers to EU green-maize versus grain-maize statistics.
- FEWS NET and food-aid buyers: Inference, low relevance. Leave out of the pitch.

## 5. Opponents and skeptics, and how to answer them

| Skeptic | Their concern | Answer backed by an opened source |
|---|---|---|
| Farmers and farm organisations | Field-level monitoring. The industry's own principles say "farmers should own information originating from their farming operations" and that data should not be used for "anti-competitive activities" such as speculating in commodity markets (2014, updated 2024) [P1]. | Public imagery only, no farmer-reported data. Publish county and state aggregates only, with small-cell suppression. Same posture as the CDL ("in no case are farmer reported data revealed or derivable from the public use Cropland Data Layer" [N9]), CSB (non-confidential, no personal identifiers [N10]) and OpTIS (field-scale calculation, aggregate publication [O1]). |
| USDA lawyers | 7 U.S.C. 8791 bars disclosure of producer-provided information and of "geospatial information otherwise maintained by the Secretary about agricultural land or operations" [L3]; 7 U.S.C. 2276 bars disclosure unless "transformed into a statistical or aggregate form" (penalty up to $10,000 or one year) [L4]; the NASS pledge cites up to 5 years and $250,000 [N11]. | Both statutes carve out statistical or aggregate form "without naming any individual owner, operator, or producer" or "specific data gathering site" [L3]. Design to that carve-out from day one. |
| Statisticians wary of black boxes | Accuracy, bias, repeatability. | Four measured numbers per field and a two-question rule; area estimates with error; a persistence benchmark; a three-way outcome; an honest failure map. Use the federal data-quality vocabulary, co-authored by NASS staff: timeliness ("the length of time between the event ... and their availability"), granularity ("the amount of disaggregation available"), accuracy and reliability, coherence, confidentiality [Q1]. |
| Market participants | An unofficial number moving prices, or early access for some. | Open method, public inputs, one release time for everyone; or delivered only into the Board's process. Present it as an input to the official estimate, not a rival. |
| Insured growers | Satellite "gotcha" on switched fields. | The rule already requires notice before harvest [L1]; a triage list gets the adjuster there in time, which protects the claim of a grower who did give notice. |
| Dairies | A regulator watching fields. | Independent confirmation of crop removal lowers the reporting burden the 2026 order creates [C1]. Keep this as a secondary story with careful wording. |

## 6. Recommended positioning

**Primary beneficiary: USDA NASS, the Agricultural Statistics Board and its Regional Field Offices.** They posed the challenge, they judge it, and their published procedure already has a slot for it.

> Value proposition: "A field-up, auditable indication of corn harvested for silage, for grain, and for neither, by county and state, about two months before the first official silage estimate, built only on public data and reconciled to your own totals."

Secondary beneficiaries, one sentence each:

| Beneficiary | Value proposition |
|---|---|
| WAOB and ERS feed-grains analysts | "An earlier read on harvested-for-grain area, where every 100 thousand acres is 18 million bushels, and the first in-season forage-supply number to explain feed and residual." |
| RMA and crop insurers | "A dated, per-field flag for grain-insured corn that was cut green, so the appraisal the rules require happens before the evidence is in a bunker." |
| California water boards and Central Valley dairies | "Independent, per-field confirmation of what was harvested, when and how many times, for the nitrogen-removed side of the ratio the 2026 dairy order makes every dairy report." |
| Dairy feed buyers, nutritionists, custom harvesters | "The first public map of how much silage each county put up this year, for a 136-million-ton feed that has no published price or inventory." |
| NRCS and conservation partners | "Which fields were stripped of residue by a silage cut and did not green up again, and how many weeks of cover-crop window each cut date left." |
| San Joaquin Valley air district | "Region-wide evidence on whether corn silage is being cut at or above the 65% moisture the VOC rule lists as a mitigation practice." |
| Researchers and extension | "An open benchmark and workflow for a crop-use distinction the Cropland Data Layer does not make." |

## 7. Three hero stories for a five-minute pitch (plus one spare)

**Hero 1. "The 8.3-million-acre question." Use as the opening.**
On 10 November 2026 USDA said farmers planted 96.8 million acres of corn and will combine 88.5 million. That leaves 8.27 million acres. Most were chopped for silage; some were abandoned, grazed or baled. The first official split arrives in mid January. USDA's own record says the November corn forecast ends up an average of 144 million bushels away from final, and as much as 420 million. Every 100 thousand acres we can place correctly is 18 million bushels. We put a number on that gap now.
Sources: [N2]; arithmetic in section 2.4. Caveat: 8.5% not-for-grain is within the 2023 to 2025 range (7.6 to 8.7%); the point is that nobody knows where in that range until January.

**Hero 2. "The total stood still while the map moved." Use for the demo and the metric slide.**
From 2024 to 2025 the national silage area changed by one thousand acres out of 6.2 million. Wisconsin added 155 thousand. Texas added 105 thousand, up 66%. Iowa lost 90 thousand, Kansas 80, Nebraska 70. A forecaster who said "same as last year" would have misplaced 937 thousand acres, 15% of the total. Wisconsin's extra silage alone is about 29 million bushels that never reached an elevator. Our score is whether we beat "same as last year", state by state.
Sources: [N1]; persistence arithmetic in section 2.2.

**Hero 3. "California's nitrogen ledger." Use as the 'who else needs this' close.**
California chops 87% of its corn: 365 thousand acres, about 10 million tons, for 1.7 million cows and $8.4 billion of milk. Two months ago the State Water Board ordered that every Central Valley dairy, about 1,300 of them, report nitrogen applied against nitrogen removed, crop by crop, because today's figures are, in the Board's words, "estimates based on broad averaging schemes". Nitrogen removed is more than double when the whole plant leaves the field. The same harvest map that helps NASS in January is an independent check on that ledger, and the Valley's air rule already names our key number: silage cut at 65% moisture or wetter.
Sources: [N1, N5, N6, C1, C2, C3, X3]. Wording caution: say "independent check", never "enforcement".

**Spare. "The insurance tripwire."**
Federal crop insurance treats grain corn and silage corn as different insured types with different end dates: 30 September for silage in most states, 10 December for grain. Chop a grain-insured field without telling your insurer first and the rule counts production at no less than your guarantee, which means no payment on that field. In a drought that is thousands of fields in a few weeks. A dated "cut green" flag gets the adjuster there in time.
Sources: [L1, L2, E1]. Do not quote a corn liability figure.

## 8. New data sources and harvest signals surfaced by this pass

| Item | Why it is new or useful | Status |
|---|---|---|
| Insurance end-of-period dates by state and county (7 CFR 457.113 section 8) | A public, citable calendar prior: silage 30 Sept or 20 Oct; grain 10 Dec; south Texas grain 30 Sept. Encodes "early is not silage" for Texas in federal regulation. | Verified [L1] |
| The 65% moisture standard | The same threshold appears in insurance (65% moisture equivalent), the Valley air rule (cut at 65% or wetter) and feed pricing (65% basis). Present green-at-cut as a proxy for the one number three institutions already use. | Verified [L1, C3, X1] |
| Grain content threshold, 4.5 bu per ton of silage | Insurance definition of "grain-deficient" silage: a hook for a drought-chopped class. | Verified [L1] |
| Persistence benchmark from NASS state tables | A statistician-native score: beat last year's state totals. | Verified, computed [N1] |
| CDL double-crop corn classes 225, 226, 228, 237 | California silage is typically double-cropped after winter forage. A corn mask built on class 1 alone will miss those fields. | Verified [N9]; check against the provided CDL tonight |
| Crop Sequence Boundaries 2018-2025 | Public, non-confidential field polygons with rotation history. | Verified [N10] |
| California dairy regulatory layers (GeoTracker reporting, about 1,300 regulated dairies) | Public dairy locations for the distance-to-dairy feature and a future validation set of reported commodities per parcel. | Order verified [C1, C2]; the facility list itself not opened |
| RMA Summary of Business by type and practice | Possible county-level insured acres of corn as grain versus silage. | Unverified lead; site unreachable |
| FSA public crop acreage files | Possible county planted acres from acreage reports; unknown whether intended use is published. | Unverified lead; timeouts |
| DWR statewide crop mapping | Possible field-level double-crop flags for California. | Unverified lead; 403 |

## 9. What this means for Kernel

**Build tonight**
1. **Three outcomes in the rollup, not two.** Planted = grain + silage + other. "Other" was 1.3 to 1.7 million acres in each of 2023 to 2025 [N1]. A binary model forced to choose will push failed, grazed or baled corn into silage exactly where drought makes the estimate matter.
2. **Corn mask check.** Confirm the pipeline keeps CDL classes 225, 226, 228 and 237 and drops 12 and 13 [N9]. Test on California first.
3. **State-specific priors and state-specific metrics.** Silage share of planted corn runs from 1.8% in Iowa to 87% in California [N1]. Report precision, recall and false-positive rate by state, and report area bias alongside them. In New York, Idaho and California "always grain" is wrong more often than right.
4. **The persistence table.** One slide: predicted state silage acres versus last year's NASS totals versus "same as last year". The bar to clear is 12 to 15% of acreage misplaced [N1].
5. **An area estimate with an interval,** by county and state, from the labelled sample (bias-adjusted, not raw counts), plus the "needs review" share. Statisticians will ask for the error of the acreage, not of the classifier.
6. **Aggregate-only outputs.** County and state tables with a suppression rule for thin cells; per-field Harvest Story cards shown as an analyst view, not a public layer. State in the notebook that no farmer-reported data is used.
7. **Two derived layers** that turn the classification into money and policy: grain-equivalent bushels (silage acres x county grain yield) for the Midwest; nitrogen removed (acres x yield x coefficient, by harvest type) for California.
8. **Feature explanations anchored in rules:** cut date against the insurance calendar, green-at-cut against 65% moisture.

**Say to the USDA statisticians**
- "We are not replacing the December Agricultural Survey. We are giving the Board one more indication, about two months earlier, in the place where your methodology statement already lists satellite imagery." [N2]
- "Our benchmark is your own table: does this beat 'same as last year' for each state." [N1]
- "We publish aggregates only, the same way the CDL and CSB do." [N9, N10, L3]
- "We report three outcomes because your own numbers show 1.3 to 1.7 million acres are neither." [N1]
- "Last year's totals are a target with a tolerance, not ground truth: the 2025 grain area was later revised by 310 thousand acres." [N2, N3]

**Contradictions with plan v2**
- The plan has no "other fates" outcome. Add it at least in the rollup.
- The plan reconciles to NASS totals as if they were fixed. They are revised, and California's 2025 figures appear to have moved materially (section 2.3).
- The plan implicitly assumes a current-year corn mask. The current-year CDL arrives in late February [N9]. Either say the prototype is retrospective, or show the in-season mask path.
- Earlage, snaplage and high-moisture corn are legally "harvest" for grain-type corn [L1] and are cut early. They leave stalks. The residue number, not the cut date, has to separate them; say so as a known failure mode. Iowa lists earlage or snaplage chopping as a priced custom operation [X2], so it is not rare.
- Nemotron agents: one memo per customer is more convincing than a general chat. The two with verified demand are a Board indication memo (state table, changes versus last year, fields needing review) and a California nitrogen-removal sheet.

## 10. Formulas and recipes

**Persistence benchmark** (state s, year t):
`WAPE_t = sum_s |A_s,t - A_s,t-1| / sum_s A_s,t`, with A = NASS silage area harvested. 2024: 12.3%. 2025: 15.1%. Kernel's version replaces `A_s,t-1` with its own estimate.

**Three-way reconciliation** (per state or county):
`planted = grain + silage + other`. Scale field-level predictions so the three classes sum to planted area (NASS June Acreage at state level), then compare silage to the January state figure when it arrives. Report the pre-scaling totals too.

**Grain-equivalent bushels:**
`delta_bu = delta_silage_acres x county_grain_yield`. National shorthand for 2026: 179.6 bu/acre, so 100 thousand acres = 18.0 million bu [N2].

**Silage tons from grain yield** [X1]:
`tons_per_acre at 65% moisture = 0.135 x bu_per_acre` (170 bu gives 23 tons).
Moisture adjustment: `value_at_M = value_at_65 x (100 - M) / 35`.

**Imputed silage value** [X1]:
`standing $/ton = k x corn $/bu`, k = 8 (fields under 100 bu) to 10 (over 200 bu); harvested and stored k = 10 to 12.

**Nitrogen removed and allowable application** [C1, X3]:
`R = yield x crop_coefficient` (coefficient = nitrogen content of fresh crop material; the Water Board points to UC Davis coefficients, page not opened). Stand-in from Penn State: silage 259 lb N per 25 tons = 10.4 lb N per ton as fed; grain 114 lb N per 150 bu = 0.76 lb N per bu.
`A_max = 1.4 x R` for existing dairies; 1.1 for new.

**Area estimate from a classified map and a labelled sample** (standard practice, not re-verified in this pass):
`area_k = sum_h W_h x p_hk`, where W_h is the mapped area of predicted class h and p_hk is the share of labelled fields in predicted class h whose true class is k. Standard error from the binomial variance of p_hk within each h.

**Suppression rule for publication** (Kernel's proposal; NASS thresholds are not public): publish a county cell only when it has at least 10 corn fields and no single field exceeds 60% of the class acreage; otherwise roll up to the agricultural district and mark the cell withheld.

**Which measured number answers whose question** (index formulas are the standard Sentinel-2 definitions; they were not re-verified here):

| Kernel number | Standard formula | Who asks for it |
|---|---|---|
| Cut date (Sentinel-1 VV/VH change point, optical confirmation) | drop in VH and VH/VV after canopy removal | NASS (harvest timing), RMA (before or after notice; against 30 Sept and 10 Dec), custom harvesters, NRCS (cover-crop window) |
| Green-at-cut | NDVI = (B8 - B4) / (B8 + B4); NDMI = (B8A - B11) / (B8A + B11), as a share of seasonal peak | RMA (65% moisture equivalent), air district (65% or wetter), feed buyers (65% pricing basis) |
| Dry-down days | optical browning date to radar cut date | NASS and WAOB (grain versus silage), RMA (drought-chopped grain) |
| Ground left | NDTI = (B11 - B12) / (B11 + B12) after harvest | NRCS (residue), carbon MRV, separates earlage and high-moisture corn from silage |
| Double-crop fingerprint | winter green peak before corn | Water Board (number of harvests per field), California accuracy |
| Distance to dairy | nearest regulated dairy | Water Board, feed market, prior for class |

## 11. Annotated bibliography (all opened on 2026-11-14)

NASS and USDA statistics
- **[N1]** NASS, *Crop Production 2025 Summary*, approved 12 Jan 2026. https://release.nass.usda.gov/reports/cropan26.txt . State and US corn planted, harvested for grain, yield, production 2023-2025; full corn silage table by state; methodology (December Agricultural Survey, about 73,100 operators; Board uses "survey data, administrative data, and the State analysis"); revision policy. The single most useful document for this topic.
- **[N2]** NASS, *Crop Production*, released 10 Nov 2026. https://release.nass.usda.gov/reports/crop1126.txt . 2026 forecast; revised 2025; blank 2026 silage cells; methodology quotes on satellite imagery and revisions; reliability table (RMSE 1.3%, 144 million bu average change).
- **[N3]** NASS, *Crop Production*, released 11 Sept 2026, reissued 23 Oct 2026. https://release.nass.usda.gov/reports/crop0926.txt . "Corn: Acreage updates were made based on a thorough review of all available data"; 2025 still unrevised at that date.
- **[N4]** NASS, *Crop Values 2025 Summary*, Feb 2026. https://release.nass.usda.gov/reports/cpvl0226.txt . Corn grain price and value 2023-2025; no silage line anywhere in the report.
- **[N5]** NASS, *Milk Production*, released 20 Feb 2026. https://release.nass.usda.gov/reports/mkpr0226.txt . Annual 2024 and 2025 cows, yield per cow, production by state.
- **[N6]** NASS, *2025 State Agriculture Overview, California* (Quick Stats as of 14 Nov 2026). https://sb.nass.usda.gov/Quick_Stats/Ag_Overview/stateOverview.php?state=CALIFORNIA . Milk value $8,394,750,000; corn planted 450,000; grain 75,000 acres; silage 370,000 acres, 9,990,000 tons. Layout is ragged; values differ from [N1].
- **[N7]** NASS, *2025 State Agriculture Overview, Wisconsin*. https://sb.nass.usda.gov/Quick_Stats/Ag_Overview/stateOverview.php?state=WISCONSIN . Silage 885,000 acres, 19,470,000 tons; milk $6.81 billion.
- **[N8]** NASS, Reports by release day. https://www.nass.usda.gov/publications/reports-by-release-day . 2026 release dates for Acreage, Crop Production, the Annual Summary, Crop Values.
- **[N9]** NASS, Cropland Data Layer FAQ. https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php . Class list (no silage class; four double-crop corn classes); release dates; 10 m from 2024; training on FSA field data; confidentiality sentence; accuracy caveats.
- **[N10]** NASS, Crop Sequence Boundaries. https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php . Public, non-confidential field polygons; 2018-2025 set released 27 Mar 2026; code on GitHub.
- **[N11]** NASS, Confidentiality pledge. https://www.nass.usda.gov/About_NASS/Confidentiality_Pledge/index.php . Statutes, penalties, aggregate-only publication.
- **[W1]** USDA WAOB, *WASDE-677*, Nov 2026. https://www.usda.gov/oce/commodity/wasde/wasde1126.txt . US corn supply and use table.
- **[E1]** USDA ERS, Crop Insurance at a Glance, updated 23 Sept 2025. https://www.ers.usda.gov/topics/farm-practices-management/risk-management/crop-insurance-at-a-glance . Program totals for 2024; no crop breakdown.
- **[E2]** USDA ERS, Feed Grains Sector at a Glance, updated 7 May 2026. https://www.ers.usda.gov/topics/crops/corn-and-other-feed-grains/feed-grains-sector-at-a-glance . Use shares; no mention of silage.
- **[Q1]** Federal Committee on Statistical Methodology, *A Framework for Data Quality*, FCSM-20-04, Sept 2020. https://nces.ed.gov/fcsm/pdf/FCSM.20.04_A_Framework_for_Data_Quality.pdf . Eleven quality dimensions and definitions; NASS staff among the members.

Law and regulation
- **[L1]** 7 CFR 457.113, Coarse grains crop insurance provisions (Cornell LII). https://www.law.cornell.edu/cfr/text/7/457.113 . Sections 1, 6, 8, 11, 12 on grain versus silage.
- **[L2]** 7 U.S.C. 1515, Program compliance and integrity. https://www.law.cornell.edu/uscode/text/7/1515 . Reconciliation, FSA monitoring, data mining, funding.
- **[L3]** 7 U.S.C. 8791, Information gathering. https://www.law.cornell.edu/uscode/text/7/8791 . Non-disclosure of producer and geospatial information; aggregate exception.
- **[L4]** 7 U.S.C. 2276, Confidentiality of information. https://www.law.cornell.edu/uscode/text/7/2276 .
- **[L5]** 16 U.S.C. 3811, Program ineligibility (highly erodible land). https://www.law.cornell.edu/uscode/text/16/3811 .
- **[F1]** farmers.gov, Crop acreage reports. https://www.farmers.gov/crop-acreage-reports . Required items including intended use; 15 July; FSA-RMA sharing.

California
- **[C1]** State Water Resources Control Board, Order WQ 2026-0028, adopted 15 Sept 2026 (131 pages). https://www.waterboards.ca.gov/board_decisions/adopted_orders/water_quality/2026/wqo2026-0028.pdf . Pages 9-12, 20-21, 29-30, 82, 86, 96-99 used.
- **[C2]** State Water Board notice page for the review of R5-2013-0122. https://www.waterboards.ca.gov/public_notices/petitions/water_quality/r5-2013-0122.html . About 1,300 dairies; timeline; adoption.
- **[C3]** San Joaquin Valley APCD, Rule 4570 Confined Animal Facilities (60 pages). https://ww2.valleyair.org/media/bh4dna44/rule-4570.pdf , linked from https://ww2.valleyair.org/rules-and-planning/current-district-rules-and-regulations/ . Thresholds; silage measures; 65% moisture option.
- **[C4]** CDFA, California Agricultural Production Statistics. https://www.cdfa.ca.gov/Statistics/ . 2025 cash receipts and top commodities.
- **[C5]** Central Valley Water Board, Confined Animal Facilities programme page. https://www.waterboards.ca.gov/centralvalley/water_issues/confined_animal_facilities/ . Navigation only.

Extension and other
- **[X1]** Edwards and Hart, *Pricing Forage in the Field*, Iowa State Ag Decision Maker A1-65, updated Sept 2018. https://www.extension.iastate.edu/agdm/crops/html/a1-65.html .
- **[X2]** Johanns and Hart, *2026 Iowa Farm Custom Rate Survey*, A3-10, revised March 2026 (205 responses). https://www.extension.iastate.edu/agdm/crops/pdf/a3-10.pdf .
- **[X3]** Roth and Heinrichs, *Corn Silage Production and Management*, Penn State Extension, 2001. https://extension.psu.edu/corn-silage-production-and-management .
- **[O1]** CTIC, OpTIS. https://www.ctic.org/OpTIS .
- **[P1]** Ag Data Transparent, Privacy and Security Principles for Farm Data. https://www.agdatatransparent.com/principles .
- **[I1]** Eurostat, Agricultural production - crops (data extracted 27 Oct 2025). https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Agricultural_production_-_crops .
- **[I2]** GEOGLAM Crop Monitor. https://cropmonitor.org/ .

## 12. Not opened, with reasons

| Wanted | URL tried | Result |
|---|---|---|
| RMA Summary of Business, corn liability, county data by type | rma.usda.gov, pubfs-rma.fpac.usda.gov | not opened: DNS lookup failed |
| NASS reports on ESMIS | esmis.nal.usda.gov | not opened: DNS lookup failed (release.nass.usda.gov used instead) |
| eCFR text of 457.113 | ecfr.gov | not opened: redirected to a bot wall (LII used instead) |
| FSA crop acreage data; Livestock Forage Disaster Program | fsa.usda.gov | not opened: timeouts |
| DWR statewide crop mapping | data.cnra.ca.gov, water.ca.gov | not opened: 403 |
| California Agricultural Statistics Review 2023-2024 | cdfa.ca.gov PDF | not opened: file over 10 MB |
| Soil loss under silage versus grain | jswconline.org (two articles), Wiley Agronomy Journal | not opened: 404, 404, 403 |
| California dairy ration composition | journalofdairyscience.org | not opened: 403 |
| CRS crop insurance primer | congress.gov | not opened: 403 |
| UC Davis nitrogen removal coefficients | geisseler.ucdavis.edu | not opened: expired certificate |
| NASS lockup page; January 2027 calendar; Eurostat green maize glossary | nass.usda.gov, ec.europa.eu | not opened: 404, no report names, 404 |

## 13. Open questions

1. Do the RMA type-and-practice files give county insured acres of corn as grain versus silage? If so, it is a county prior and a reconciliation target available months before January.
2. What produced the "silage-like" and "grain-like" labels in the evaluation set (FSA intended use, insurance type, field visits), and do they contain any "other fate" fields?
3. Does the survey definition of "corn for silage" include greenchop, earlage and snaplage? The answer changes how early, residue-leaving cuts should be scored.
4. Is California's 2025 revision (grain 50 to 75 thousand acres) real, and which figure did the organisers hand out as "last year's state totals"?
5. A citable soil-loss comparison for silage versus grain corn.
