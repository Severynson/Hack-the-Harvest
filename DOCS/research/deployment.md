# Deployment, buy-in, landscape and cost: Mission Model Canvas inputs for Kernel

Research pass of 2026-11-14 for team Kernel, Hack the Harvest. Topic: what it takes to move a hackathon prototype into use at USDA NASS, who has to say yes, what already exists, what it would cost, and how an agency would measure success.

Legend: **[R]** = I read the primary document myself (page or PDF opened in this run). **[T]** = read through the fetch tool's extraction of the page (short verbatim quotes, the rest paraphrased by the tool). **Inference:** = my reasoning, not in the source. "Sibling" = another report in this folder; numbers taken from a sibling are marked and were not re-verified here.

---

## 0. Bottom line

1. **There is a defined slot for this inside NASS, and it is not "replace the survey".** Since 2007 the Cropland Data Layer (CDL) team has handed satellite-based acreage estimates to the Agricultural Statistics Board (ASB) and field offices at the monthly production deadlines, as a *supplemental indication*, computed with a regression estimator and never by pixel counting. Kernel should be pitched as one more indication of that kind: the split of corn into grain and silage, which no existing indication provides.
2. **The survey behind the January silage number is thinning, and it is weakest exactly where silage dominates.** The December Agricultural Survey response rate fell from 46.0% (2024) to 40.2% (2025). The coefficient of variation (CV) of the corn harvested-for-grain ratio in 2025 was 38.3% in Arizona, 23.3% in California, 18.5% in Idaho, 18.2% in New Mexico, 14.1% in Utah and 11.8% in Washington, against 0.5% in Iowa and 0.3% nationally. That table is the strongest single argument for mission value.
3. **Federal AI policy now favours our design.** OMB M-25-21 (3 April 2025) says agency policies "should aim to advance using models that are built with less data, require less compute, and are inherently more explainable, where possible", and requires open-source release of AI code where practicable. A statistical indication reviewed by statisticians is not "high-impact AI". The same satellite classifier used to check an individual farmer is: USDA's Risk Management Agency lists its three satellite compliance tools as rights-impacting.
4. **Nothing we could open distinguishes silage from grain.** CDL has one "Corn" class. NASA OPERA DIST flags generic vegetation loss. OpTIS maps tillage and residue. The commercial pages (Planet, EarthDaily, Regrow, Kayrros, SatSure, CropProphet) show no such output.
5. **Cost is people, not compute.** Our order-of-magnitude estimate for a weekly national run is about 5 dollars of CPU (range 1 to 25) and 1 to 2 dollars of LLM inference; 2 to 3 analysts are more than 95% of the annual cost. NASS's own history says the same: the CDL cost 75,000 dollars per state in 2000, of which 50,000 was labour.
6. **Unit names in the brief could not be confirmed.** The NASS organisational chart dated 7 October 2026 shows only the top level: three Offices (Survey Design and Methodology; Data Acquisition and Processing; Analysis and Estimation). No divisions are drawn, so I could not confirm that a "Research and Development Division" or a "Methodology Division" still exists under those names. The public contact for CDL and Crop Sequence Boundaries is the Geospatial Information Branch; name that.

### 0.1 How this pass was done, and its limits

- **Web search was unavailable.** The session's shared WebSearch budget was already used up when this agent started (all three first searches were refused). No search engine was queried by any other route. The brief's target of 12 or more searches was therefore not met.
- Everything below comes from about 80 direct fetches of known or linked URLs (NASS, OMB, Cornell LII, NASA, GitHub, vendor sites), from seven PDFs read page by page, and from the 2024 federal AI inventory CSV downloaded and parsed locally (1,757 rows).
- Consequences: coverage of NASS, OMB and the AI inventory is deep. Coverage of people (judges) and of some vendors is thin, because their pages could not be found without search. usda.gov (main site), Devpost, ARS, FAS and several others refused or failed; they are listed in section 13 and nothing is cited from them.
- The "Leads" in the brief were treated as hints. Several were confirmed, one was contradicted (the division names), and several stay unverified (people's titles, the USDA AI strategy, Descartes Labs and Indigo).

---

## 1. What this means for Kernel

### 1.1 Things to change or add in the next 18 hours

| # | Change | Why (evidence section) | Effort |
|---|---|---|---|
| 1 | Call the output a **"supplemental silage and grain indication for the Agricultural Statistics Board"**; never "replacement for the survey" | 4.2 | wording only |
| 2 | Add the slide **"Where the survey is thinnest"** (table in 8.2). If the provided data cover any of AZ, CA, ID, NM, UT, WA, NY, PA, lead with them | 8.2 | 30 min |
| 3 | Report state results the way NASS judges an indication: **difference from the official estimate, by state and year**, plus a regression-style estimate next to the raw polygon sum (label the raw sum "pixel counting") | 4.2, statistics.md | already planned; rename |
| 4 | Add a **governance cell** at the end of the notebook: one AI-inventory row for Kernel and a short M-25-21 checklist (6.3, 6.4) | 4.5 | 30 min |
| 5 | Keep the "needs review" band and say the RMA sentence: **"Model results will not be used without independent review"** | 4.5 | wording only |
| 6 | Nemotron memos are **drafts for an analyst**, every number read from DuckDB; say so | 4.5 | already the rule in CLAUDE.md |
| 7 | Add a **cost slide** with the assumptions table (section 7) | 7 | 20 min |
| 8 | End the pitch with a **named next step**: a one-season pilot in 3 to 5 dairy states, retrained on NASS's internal labels, judged by its track record against the January estimates | 4.4 | wording only |

### 1.2 Things in plan v2 that this research supports

- Two-question rule plus boosted trees: the CDL itself has been a boosted decision tree (See5, 10 boosting trials) since 2006. **Inference:** NASS geospatial staff can audit a tree model without retraining themselves.
- Reconciling county and state rollups with NASS totals: the ASB works "top-down", sets the national number first and adjusts states to it.
- Conformal "needs review" band: matches how USDA describes safe use of its own satellite models.
- Public data only and an MIT-licensed public repository: matches M-25-21's code-sharing and public-data language.

### 1.3 Things this research contradicts or complicates

- **"Earlier than January" is only true if someone publishes earlier.** Inside the current NASS calendar an internal indication improves precision, not public timing. A public experimental product in November would give the lead time, but a grain-versus-silage number may be market-sensitive (**Inference**). Say which of the two you mean. Lead-time figures are in nowcast.md (8.4 weeks on 14 November).
- **"Farmer level" is a governance trap.** Field-level maps from public data are fine as statistics (the Crop Sequence Boundaries are public domain). Using a field call to act on an individual producer is what turns the tool into rights-impacting AI.
- **Do not name the "Research and Development Division" as the owner without checking.** The current top-level chart shows Offices, and I could not confirm the division names beneath them. Use "the Geospatial Information Branch, the team behind the CDL", or ask Justin Van Wart which unit would own it.
- **The corn mask is a deployment dependency.** The CDL for year N is released in late January or February of N+1 (2025 CDL: 27 February 2026), after the January summary. Inside NASS an in-season CDL and a "Predictive Cropland Data Layer" exist; outside they do not. See nowcast.md and data_access.md (which also shows that in California the mask must include the double-crop classes 225, 226, 228, 237).

---

## 2. The Mission Model Canvas (authoritative definition)

Source: Steve Blank, "The Mission Model Canvas - An Adapted Business Model Canvas for Mission-Driven Organizations", 23 February 2016 [T], written with Alexander Osterwalder ("Alexander Osterwalder and I think we have the answer"); the same article on Strategyzer under Osterwalder's name, 25 February 2016 [T]. The article is written for defense and intelligence problems. The link to the Hacking for Defense class comes from the brief; the class name did not appear in the text as extracted, and h4d.us was not opened.

Why it exists: for organisations where "the primary goal is not to earn money, but to fulfill a mission", "there is no revenue to measure". Osterwalder adds that it was conceived for organisations that have budgets.

Five of the nine Business Model Canvas boxes change; four stay.

| # | Box | Replaces | Definition and guiding questions (quotes are verbatim, short) |
|---|---|---|---|
| 1 | **Beneficiaries** | Customer Segments | "we'll call all the different customer segments and the layers in the defense and intelligence value chain beneficiaries". "mission models are always multi-sided markets". Includes end users and everyone who must be served before the end user benefits: requirement writers, contracting, support organisations, legal. |
| 2 | **Value Propositions** | unchanged | What you are building for each beneficiary. "each beneficiary gets its own separate Value Proposition Canvas". |
| 3 | **Buy-in and Support** | Customer Relationships | "how does the team get 'Buy-In' from all the beneficiaries?" "How to determine who are the critical people to get buy-in from". Whose approval is needed to deploy (legal, policy, procurement), who must be persuaded first, and who provides long-term support and maintenance. The article warns that demanding too much buy-in too early can stall a project (paraphrase). |
| 4 | **Deployment** | Channels | "What constitutes a successful deployment?" What it takes to go from the current MVP to widespread use. "How do we turn a Horizon 3 innovation into something that gets adopted by a Horizon 1 organization?" Measures named: number of users, units in the field, time to fielding. |
| 5 | **Key Activities** | unchanged | Not redefined in the article. |
| 6 | **Key Resources** | unchanged | Not redefined in the article. |
| 7 | **Key Partners** | unchanged | Not redefined in the article. |
| 8 | **Mission Budget / Cost** | Cost Structure | "Cost Structure is changed to Mission Cost/Budget". "you mobilize resources and a budget to solve a particular problem and create value for a set of beneficiaries". The article gives no guiding questions for this box. |
| 9 | **Mission Achievement** (the canvas template labels it "Mission Achievement / Impact Factors") | Revenue Streams | "Mission Achievement is the value you are creating for the sum of all of the beneficiaries / the greater good." "there is only mission achievement if it delivers value to the end beneficiary". Examples: "the number of soldiers saved from roadside bombs", "the number of cyberattacks prevented". "None of these are measured in dollars and cents." |

Note: the words "Impact Factors" do not appear in the article text as extracted; the label is on the canvas graphic, which I did not see. Treat the article's "Mission Achievement" as the definition.

### 2.1 Value Proposition Canvas basics

Source: Strategyzer, "The Value Proposition Canvas" page (copyright 2026) [T].

- Customer side: "Describe one customer segment: the jobs they are trying to get done", what gets in their way (pains) and what they want to achieve (gains). "Map what customers are trying to get done, what gets in their way, and what they want to achieve."
- Value side: "List what you offer, then name the pains it relieves and the gains it creates." (In the wider Strategyzer method these are called products and services, pain relievers and gain creators; the page itself does not use those two labels.)
- Fit: "Fit is a claim until customers confirm it." "Test the matches you drew against evidence, then adjust."
- Link to the Mission Model Canvas (Blank): the Value Proposition Canvas is a plug-in that zooms into the relationship between the value proposition and one beneficiary; make one per beneficiary.

---

## 3. Draft canvas for Kernel

Everything in this section is **Inference** assembled from the evidence in sections 4 to 8. It is a starting point for the team's own canvas, not a finding.

| Box | Kernel |
|---|---|
| **Beneficiaries** | (1) The Agricultural Statistics Board, which sets national and state estimates by consensus. (2) Regional Field Office statisticians, who recommend state estimates and see only their own survey results. (3) The Geospatial Information Branch, which would run and maintain it. (4) Crops Branch and the estimation methodology branch, which must accept the estimator. (5) USDA OCIO and the Chief AI Officer function, which must list and authorise it. (6) Downstream users: dairy and feed buyers, ERS and WAOB analysts, lenders, and possibly RMA (grain versus silage insurance), each of whom gets the January number today. |
| **Value propositions** | ASB: an independent, full-coverage indication of the grain and silage split, with a track record. Field offices: a county map of where the silage is, with a short review queue instead of a pile of imagery. Geospatial branch: a small, auditable extension of the CDL family (same tree models, same public inputs). OCIO: a use case that is easy to approve (public data, open code, explainable, human review). Data users: an earlier or more precise silage number in the states where today's number is least precise. |
| **Buy-in and support** | First yes: the technical lead who set the challenge (Justin Van Wart) and the geospatial team. Then: the ASB Chair and the Office of Analysis and Estimation (they decide whether an indication is used); the methodology office (estimator and disclosure review); OCIO (inventory row, authority to operate); General Counsel only if field-level release is proposed. Long-term support: the Geospatial Information Branch, so the hand-over must be code they can run without us. Evidence that wins buy-in: the "historical relationship of the survey results to the official estimate" is how NASS judges an indication, so a multi-year backtest is the currency. |
| **Deployment** | Stage 0: reproducible notebook on public data (this weekend). Stage 1: one-season pilot in 3 to 5 states inside NASS or under a cooperative agreement, retrained on internal labels (FSA 578 intended use, December survey). Stage 2: delivered as a supplemental indication for the January summary, alongside the survey. Stage 3: three seasons of track record. Stage 4: optional public product (county level first, field level only after disclosure review). Success = used by the ASB for at least one state, on time, for two consecutive seasons. |
| **Key activities** | Weekly ingestion of Sentinel-1, Sentinel-2 and HLS for corn polygons; four numbers per field; classification and calibration; regression estimate against survey totals; review queue; state and county memos; annual re-validation. |
| **Key resources** | Free satellite archives; CDL and Crop Sequence Boundaries; a small labelled set (public) and large confidential label sets inside USDA; 2 to 3 analysts; an authorised compute environment; an open-weights LLM that can be self-hosted. |
| **Key partners** | NASS Geospatial Information Branch; ERS (co-developer of the Crop Sequence Boundaries); ARS SCINet (hosts CroplandCROS); George Mason University CSISS (CropScape, VegScape, Crop-CASMA); NASA Acres (University of Maryland); UC Davis CATS and HMCI (this event); NVIDIA (Nemotron, RAPIDS). |
| **Mission budget / cost** | About 0.5 million dollars a year at national scale, more than 95% labour; under 5,000 dollars a year of cloud and LLM (section 7). Pilot: about 1 analyst-year. |
| **Mission achievement / impact factors** | Lead time gained (weeks before the January summary, if published); error against the final estimate by state and year; reduction of CV in the states where the survey CV exceeds 5%; share of corn acres with a call; review workload; weeks delivered on schedule, including during survey interruptions (section 8). |

### 3.1 Three value proposition canvases (one per key beneficiary)

| | ASB member | Regional Field Office statistician | OCIO / AI governance reviewer |
|---|---|---|---|
| Jobs | Set the national and state estimate for corn grain and silage in 5 to 6 business days; explain the logic to other members | Interpret the state survey, submit a recommended estimate, answer questions from local users | Keep the AI inventory, authorise systems, apply M-25-21 |
| Pains | Response rate 40.2%; CVs do not capture nonrespondents who made "fundamentally different ... harvesting decisions"; external data are "often of limited use prior to the end of the season" | Sees only own state; late switches from grain to silage are invisible until the survey | Opaque models, vendor lock-in, unclear data rights, high-impact determinations |
| Gains | An independent indication with a known historical relationship to the final number | A map and a ranked list of doubtful fields; a draft narrative | A use case that passes review quickly and can be shared across agencies |
| What Kernel offers | State and county indications with a reliability table; top-down reconciliation | Field evidence cards, review queue, county memo | Public data, MIT code, printable rule, human review, monitoring plan |
| Fit still to prove | Track record over several state-years | That review time per flagged field is minutes | That the hosting environment is authorised |

---

## 4. Deployment pathways at USDA NASS

### 4.1 Who would own it

| Fact | Source |
|---|---|
| NASS organisational structure dated 7 October 2026: Office of the Administrator (Administrator, Associate Administrator); Senior Data Scientist; Chair, Agricultural Statistics Board; **Office of Survey Design and Methodology; Office of Data Acquisition and Processing; Office of Analysis and Estimation**. No divisions shown. | NASS OrgChart.pdf [R] |
| Leadership listed: Joseph L. Parsons, Administrator; Dr. Jody McDaniel, Associate Administrator; Troy Joshua, Deputy Administrator, Office of Data Acquisition and Processing; Lance Honig, Chair, Agricultural Statistics Board; Patrick Boyle, Acting Deputy Administrator, Office of Analysis and Estimation; Andrew Dau, Acting Senior Data Scientist. | NASS Biographies page [T] |
| CDL metadata contact: "USDA NASS, Spatial Analysis Research Section". CDL and Crop Sequence Boundaries questions go to the **Geospatial Information Branch (GIB)**, mailbox SM.NASS.RDD.GIB@usda.gov, Room 5029 South Building. | CDL FAQ [T]; CSB metadata 2025 [T] |
| Historical hierarchy: a 2005 internal paper is cited as "NASS/RDD/GIB/SARS", that is Research and Development Division / Geospatial Information Branch / Spatial Analysis Research Section. | Boryan et al. 2011, references [R] |
| Units named as contacts for the annual crop estimates: Crops Branch (estimation); Sampling, Editing, and Imputation Methodology Branch; Summary, Estimation, and Disclosure Methodology Branch. | Crop Production Methodology and Quality Measures, Feb 2026 [R] |
| NASS has a Chief Data Officer, an Evaluation Officer and a Statistical Official, and a Data Governance Board. NASS is "one of the thirteen principal statistical agencies". | NASS Learning Agenda FY2024-2026 [R] |

**Inference:** the chart shows only the top level, so divisions and branches may well continue beneath the three Offices. The mailbox aliases still carry the older abbreviations ("RDD" for the geospatial branch; "SD" and "CSD" for the estimation and survey branches in the February 2026 methodology report), and the Geospatial Information Branch is named in metadata dated 2025-2026. Which Office the branch reports to is not shown on anything I opened. Ask.

### 4.2 How a remote-sensing indication enters the official estimates

From Boryan, Yang, Mueller and Craig 2011 (Geocarto International 26:5, 341-358) [R]:

- "In 2009, the NASS Cropland Data Layer (CDL) program played an important role ... by providing operational in-season acreage estimates to the NASS Agricultural Statistics Board (ASB) and Field Offices (FOs) for 15 crops in 27 states." Estimates were provided "up to six times during the growing season".
- "In 2007, the CDL program provided acreage estimates for 13 states and nine crops to the NASS ASB for the October Crop Production Report. For the first time, remote sensing estimates were used in season for setting the NASS official state acreage estimates, a milestone for the program."
- Deadlines served: "June (winter wheat), August (corn and soybeans), September (...), October (corn, soybeans and all other major field crops) and December (county acreage estimates for major crops)".
- "CDL products created for earlier reporting deadlines are not released to the public."
- Estimator: "Pixel counting estimates, however, consistently underestimate the actual acreage number as compared with NASS official estimates. Therefore, NASS builds a linear regression model": Y = a + bX, with Y the acres reported in June Area Survey segments and X the CDL classified acres, fitted by stratum; it gives "a lower error rate (coefficient of variation) than direct expansion alone or direct pixel counting". The example plot for Nebraska corn 2009 shows Reported = 14.3 + 1.01 x Classified, r2 = 0.959.
- Classifier: See5 decision trees, "boosting algorithm is set to 10 trials". Nebraska 2009 corn: producer's accuracy 97.12%, user's accuracy 98.64%.

From the CDL FAQ [T]: the purpose is to "provide supplemental acreage estimates to the Agricultural Statistics Board"; internal estimates "are not simple pixel counting but regression estimates using NASS survey data".

From the Annual Crop Production Methodology and Quality Measures, released 4 February 2026 [R]:

- Timeline: the December Agricultural Survey has reference date 1 December and "a data collection period of approximately 15 calendar days"; Regional Field Offices "have about 4 or 5 business days to complete editing and analysis"; the ASB "conducts the National review, reconciles State estimates to the National estimates, and prepares the official estimates for release in 5 or 6 business days". The summary "is released at the beginning of January".
- How the estimate is set: "Using the historical relationship of the survey results to the official estimate, RFO staff must interpret the survey results and submit a recommended estimate". "RFO staff see their survey results only and do not have access to other States' results."
- "NASS employs the 'top-down' approach by determining the National estimates first and reconciling the State estimates to the National estimate." "Each ASB member completes an independent interpretation of the survey results ... An official National estimate is established only upon ASB consensus."
- On outside data: "External information (administrative data) is also utilized in this process. In order to be considered, these data must be deemed to be reliable and come from unbiased sources. Thus, they are often of limited use prior to the end of the season. The most common administrative data are the certified acreage data from USDA's Farm Service Agency. However, data from many different sources are utilized."
- Revisions: "Estimates are open to revision the following year only if new information becomes available", then once more after the Census of Agriculture.
- A stated weakness: "the CVs do not capture the effect of possible reporting errors or errors that may arise from nonrespondents making fundamentally different planting or harvesting decisions than respondents".

**Inference, the hand-off calendar for a silage and grain indication:**

| Date (2026 crop) | Event | What Kernel would deliver |
|---|---|---|
| Mid-October | Upper Midwest silage chopping essentially complete (nowcast.md) | First state and county silage indication |
| 10 November | Crop Production (November forecast of corn for grain) | Updated grain-harvested share; "still standing" share |
| About 15 November | Our hackathon vintage | Dated vintage, never overwritten |
| 1 to 15 December | December Agricultural Survey collection | Final indication with reliability table, before RFO analysis |
| Late December | RFO recommendations, then ASB review | Indication on the table next to survey and FSA data |
| About 12 January 2027 (inferred date, see nowcast.md) | Crop Production Annual Summary | Our error is scored against this |

### 4.3 Precedents built with partners

| Product | Partner | What the source says | Source |
|---|---|---|---|
| CropScape (CDL viewer, 2011) | George Mason University, Center for Spatial Information Science and Systems | "The NASS, in cooperation with George Mason University/Centre for Spatial Information Science and Systems, recently released a new interactive visualization portal called CropScape" | Boryan 2011 [R] |
| VegScape | George Mason University CSISS | Developed "in cooperation with the Center for Spatial Information Science and Systems at George Mason University"; hosted at nassgeodata.gmu.edu | NASS Research and Science page [T] |
| Crop-CASMA | Hosted at cloud.csiss.gmu.edu; uses NASA SMAP and MODIS | Web application for soil moisture and vegetation condition | same [T] |
| CroplandCROS (current CDL viewer) | USDA Agricultural Research Service | Developed "in cooperation with the Agricultural Research Service"; hosted at croplandcros.scinet.usda.gov | same [T] |
| Crop Sequence Boundaries | USDA Economic Research Service | "developed in cooperation with the Economic Research Service"; algorithm on GitHub (USDA-REE-NASS/crop-sequence-boundaries); 15,973,106 polygons in the 2018-2025 edition; "public domain and free to redistribute" | CSB page and metadata [T] |
| CDL expansion 1997-2006 | Federal and state agencies, universities | "primarily through partnerships and cooperative agreements with federal and state governments and universities. It was determined, however, that producing CDLs within NASS headquarters was the most efficient means to expand the program." | Boryan 2011 [R] |
| Early CDL | State governments; Florida A&M University; North Dakota State University; FAS and FSA (imagery licences) | "NASS had to partner and resource share with other Federal and State government Agencies in order to continue"; in 1995 "the program was only intact for Craighead county in Arkansas" | Hanuschak and Mueller [R] |
| Disaster analysis | not named | Near-real-time flood and wind assessments with Sentinel-1 SAR, Sentinel-2 and Landsat 8/9 against the 2025 CDL; a "GEE web app" called RAPID V2.0 Beta | NASS Disaster Analysis page [T] |

**Inference:** the pattern is partner first, then in-house. A partner builds or hosts the first version; once it is stable NASS runs it at headquarters. A hand-over package that a small branch can run matters more than a clever service. "GEE" on the disaster page is not spelled out; if it means Google Earth Engine, the geospatial team already works in the tool our pipeline uses.

### 4.4 Mechanisms for a follow-on

| Mechanism | Verified facts | Fit for Kernel (Inference) |
|---|---|---|
| **Cooperative agreement** | 7 U.S.C. 3318 is listed among the regulations guiding NASS as "Contract, grant, and cooperative agreement authorities". NASS describes a "cooperative relationship with universities and State Departments of Agriculture". Reimbursable work for others must be "fully reimbursed" and must "provide useful data not available elsewhere". [T] | The historically normal route for NASS geospatial work. Needs a university or similar partner (UC Davis is in the room). |
| **Pilot inside the agency** | M-25-21 section 4(a)(i): pilots are exempt from the minimum risk practices if "of limited scale and duration" and the Chief AI Officer "has certified that the pilot may go forward". [R] | Fastest if a NASS unit wants it; we supply code and documentation. |
| **Prize competition** | 15 U.S.C. 3719: an agency head may award prizes "to stimulate innovation that has the potential to advance the mission of the respective agency"; cash winners must be US citizens or permanent residents, or entities incorporated and based in the US; the Government may not gain an interest in a participant's intellectual property "without the written consent of the participant", but may negotiate a licence; awards above 1,000,000 dollars need agency-head approval. [T] | This hackathon is the lightweight version. Our code stays ours; MIT licence already grants use. |
| **Challenge.gov** | "The Challenge.gov platform was sunset on March 30, 2026." "Federal agencies will continue to run challenges and prize competitions"; listings moved to USA.gov. [T] | Do not cite Challenge.gov as a live channel. |
| **SBIR / STTR** | SBIR.gov lists Phase I at 50,000 to 275,000 dollars for 6 to 12 months and Phase II at 750,000 to 1.8 million dollars for 24 months. The page does not state the programme's 2026 authorisation status. USDA's own SBIR page was not opened (404). [T] | Requires a US small business. Only relevant if the team incorporates. |
| **CRADA** | Not verified: the ARS Office of Technology Transfer site did not resolve. | Unknown; do not mention. |
| **NASA Acres** | "NASA's consortium designed to bridge the gap from space-to-farm and education-to-impact in U.S. agriculture", "Launched in 2023 ... led and implemented by the University of Maryland", "over 40 projects ... 11 primary organizations ... more than 70 collaborating partners". USDA and NASS are not named on the home page. [T] | A possible research home, not a route into official statistics. |
| **NASA Harvest** | "NASA's Global Food Supply and Agriculture Consortium"; supports GEOGLAM. [T] | Global focus; low relevance. |

NASS's own stated priorities support the ask. Learning Agenda FY2024-2026 [R]: "How can NASS utilize alternative data sources and existing historical datasets to reduce the burden of data collection and enhance their data products?"; "How does NASS leverage its geospatial program to meet new data users demand and support stakeholders?"; "AS NASS continues to assess the potential to integrate precision agricultural and satellite imagery into business processes, NASS seeks to develop data products using alternative data sources without increasing respondent burden"; and "NASS is open to sharing its data with external researchers interested in NASS's research questions".

### 4.5 AI governance: OMB M-25-21 and the USDA inventory

OMB Memorandum M-25-21, "Accelerating Federal Use of AI through Innovation, Governance, and Public Trust", 3 April 2025, signed by the OMB Director; it "rescinds and replaces" M-24-10 [R, all 25 pages].

| Provision | Text | Meaning for Kernel |
|---|---|---|
| 3(b)(iii) | "Agency policies should aim to advance using models that are built with less data, require less compute, and are inherently more explainable, where possible." | Quote this. It is federal policy backing for "interpretable beats clever". |
| 2(b)(i) | "Agencies, where practicable, must also release and maintain AI code as open source software in a public repository" unless restricted by law, risk or contract. Agencies "must proactively share across the Federal Government their custom-developed code - including models and model weights". | Our public MIT repository is the easy case. |
| Overview and footnote 12 | Agencies "must also reuse resources that enable AI adoption, such as agency data, models, code, and assessments of AI performance" and should "explore the possible utility of ... publicly available information, and encourage its use". | Public-data design is aligned. |
| 5, definition of AI | "no system should be considered too simple to qualify as covered AI due to a lack of technical complexity". Excluded: "systems whose behavior is defined only by human-defined rules". | A hand-set two-question rule is not AI under the memo; the learned tree and XGBoost are, so they need an inventory row. |
| 5, high-impact AI | "AI with an output that serves as a principal basis for decisions or actions with legal, material, binding, or significant effect on" an individual's or entity's rights, "access to education, housing, insurance, credit, employment, and other programs", government services, health and safety, critical infrastructure, or strategic assets. | A statistical indication reviewed by a board is not on the presumed-high-impact list in section 6. Checking a producer's insurance or programme claim would be. |
| 4(b) | Minimum practices for high-impact AI: pre-deployment testing; AI impact assessment (purpose and expected benefit with metrics, data quality, costs, independent review, signed risk acceptance); ongoing monitoring; operator training; human oversight; remedies or appeals; public feedback. Deadline 365 days (3 April 2026). | Not required for us, but the impact-assessment headings are a good outline for the write-up. |
| 4(a)(i) | Pilot exemption (limited scale and duration, certified by the Chief AI Officer, tracked centrally). | The route for a first season. |
| 3(a), 3(b)(v) | Each agency designates a Chief AI Officer (may be the CIO or CDO); AI governance board includes "IT, cybersecurity, data, budget, statistics, legal counsel, privacy"; AI use case inventory "at least annually", public. | Statistics is named on the board. Offer the inventory row ready-made. |
| 3(b)(iv) | Agencies "should develop a policy that sets the terms for acceptable use of generative AI" within 270 days. | LLM memos must fit that policy: drafts, public inputs, human review. |
| 2(a), 3(b)(ii) | CFO Act agencies publish an AI Strategy within 180 days and a compliance plan within 180 days. | USDA's documents exist in principle; usda.gov returned 403 so they were not read. |
| Footnotes 22 and 29 | The AI risk process "is separate from, and does not supersede, the authorization process for information systems" under OMB Circular A-130. | An authority to operate is still needed for wherever it runs. |
| 2(d)(ii) | For procured AI: "assessing for overfitting to known test data". | Our locked test split (statistics.md) answers this. |
| 2(c) | "it is the policy of the United States to buy American and to maximize the use of AI products and services that are developed and produced in the United States". | Nemotron is a US vendor's open-weights model; say it can be self-hosted. |

**The 2024 federal AI use case inventory** (OMB's consolidated file on GitHub, downloaded and parsed locally; 1,757 rows in the raw CSV; the repository README, as extracted, states 2,133 use cases as of 23 January 2025, a difference I did not reconcile) [R for the CSV]:

- The 2024 file uses the earlier M-24-10 vocabulary ("rights-impacting", "safety-impacting"); M-25-21 replaced it with "high-impact".
- USDA: 89 use cases. Impact type: 85 "Neither", 4 "Rights-Impacting" (three at RMA, one video-surveillance system). By bureau: Forest Service 29 (plus 3 joint), APHIS 11, **NASS 10**, NRCS 8, OCIO 6, ARS 5, RMA 4, FSIS 3.
- NASS's ten, all "Neither":

| NASS use case | Stage | Initiated | Notes from the inventory |
|---|---|---|---|
| Cropland Data Layer | Operation and Maintenance | 1/1/2008 | "produces supplemental estimates of crop acreage and releases geospatial data products"; developed in-house; has ATO: Yes; system name "See5" |
| Predictive Cropland Data Layer | Operation and Maintenance | 1/1/2021 | "The purpose of this system is to predict crop rotations. Benefits include improving data quality of area-based surveys." Outputs "predictions of the types of crops in specific locations within the Conterminous United States" |
| County-level remotely-sensed corn and soybean yield estimation | Operation and Maintenance | 1/1/2007 (implemented 2014) | County yields from satellite images; cites doi 10.1016/j.rse.2013.10.027 |
| List Frame Deadwood Identification | Operation and Maintenance | 2014 | "Parts of the model were used to create clear rules" |
| Census Propensity Scores via ML | Operation and Maintenance | 2022 | |
| Survey Text Remarks Value Scoring | Operation and Maintenance | 2021 | Human review queue ordered by a model score |
| Survey Outlier Detection Model | Operation and Maintenance | 2022 | Source code public |
| Democratizing Data | Operation and Maintenance | 2021 | With ERS; contractor-built |
| NASS - Naggle 2.0 Automated Editing Tool | Initiated | 6/3/2024 | |
| NASSportal Intranet Bot | Initiated | 7/1/2024 | Chatbot for staff |

- **RMA's three satellite tools are "Rights-Impacting"** (initiated September 2022, "Developed with both contracting and in-house resources", stage "Acquisition and/or Development", no ATO):
  - Planting Date Detection: "find out the planting dates for corn, soybean, and winter wheat on farms in the U.S. Midwest ... using satellite images and models of plant growth ... independently check and confirm the planting dates reported by farmers"; output "an annual map of planting dates ... for crop years 2016-2023".
  - Cover Crop Mapping: state-level maps of cover crops by year, fall and spring.
  - Acreage and Crop Type Validation: "check if the reported sizes of farm fields and the types of crops grown match what is actually seen on the ground".
  - Key risks are written as "Type I and Type II errors", and each entry says: "Model results will not be used without independent review before a potential compliance action takes place."

**Inference:** (a) the same technology sits in two governance classes at USDA depending on use, and the statistical class is the light one; (b) harvest date and harvest end use are missing from both families, so Kernel is a natural sibling of "Predictive Cropland Data Layer" at NASS and of "Planting Date Detection" at RMA; (c) the judging rubric's "False Positive Rate" is the same vocabulary RMA uses for its risks, so report it by class.

### 4.6 IT constraints

| Topic | Verified | Not verified |
|---|---|---|
| FedRAMP | Home page on 2026-11-14: 559 FedRAMP certified services, 39 FedRAMP 20x certified; blog of 2 November 2026 on the first full FedRAMP 20x Class C certification; "Consolidated Rules for 2026". [T] | Statutory text, impact levels, timelines; whether Google Earth Engine, Vertex AI or NVIDIA-hosted endpoints are in an authorised boundary (the Google Cloud compliance page returned no content). |
| Authority to operate | M-25-21 keeps the A-130 authorisation process separate from AI risk acceptance. The CDL entry in the AI inventory says "has ATO: Yes". [R] | What boundary the CDL runs in today. |
| USDA compute | SCINet is "an effort by the USDA Agricultural Research Service" providing high-performance computing clusters, networking and training; accounts are for "ARS scientists/collaborators". CroplandCROS is hosted on the scinet.usda.gov domain. [T] | GPU capacity; whether NASS staff or outside collaborators on a NASS project get accounts. |
| NASS direction | "NASS will adopt enterprise cloud platforms to enable greater access to data for collaboration, enhanced analytics ... and new data sharing capabilities with external stakeholders and researchers." [R] | Which platform. |
| OCIO role | The event's welcome video is from Chris Alvares under a "USDA Office of the Chief Information Officer" banner (event deck). USDA OCIO itself lists 6 AI use cases in the 2024 inventory. [R] | His title; the USDA AI strategy and compliance plan (usda.gov 403). |

**Inference, the portable design:** inputs are public and the model is small, so the whole pipeline can be re-run inside any authorised environment with no data transfer agreement. For the LLM, an open-weights model served inside the boundary avoids sending anything to an outside API. Say "portable" rather than naming a platform.

### 4.7 Confidentiality of field-level outputs

| Statement | Source |
|---|---|
| Pledge: information "will be used for statistical purposes only" and "will not be disclosed in identifiable form to anyone other than employees or agents without your consent"; statutes: 7 U.S.C. 2276 and CIPSEA (Title III of Pub. L. 115-435); penalty "a jail term of up to 5 years, a fine of up to $250,000, or both"; where one farm in a county grows a crop, data are combined with other counties. | NASS Confidentiality Pledge [T] |
| "in no case are farmer reported data revealed or derivable from the public use Cropland Data Layer." | CDL FAQ [T] |
| "The FSA CLU data are confidential data sources and are not provided or shared with anyone outside of NASS." June Area Survey data "are only used internally by NASS and held strictly confidential." | Boryan 2011 [R] |
| Crop Sequence Boundaries: "non-confidential single crop field boundaries"; "does not contain personal identifying information"; data source "does not come from producers or agencies like the Farm Service Agency"; "public domain and free to redistribute". | CSB page and metadata [T] |
| Crop Progress and Condition gridded layers are "fully synthetic representations of confidential, county level data". | NASS page [T] |
| M-25-21 2(b)(iii): models "may reveal sensitive details of the data used to develop them". | [R] |

**Inference:** (1) Field calls derived only from public imagery and public boundaries can be published, as the Crop Sequence Boundaries are. (2) The provided evaluation labels may derive from confidential sources; do not republish them at field level in the public repository unless the organisers say they are public. (3) A model retrained inside NASS on FSA 578 or survey labels is a different object: its field-level outputs and even its weights would need disclosure review before release. (4) County totals from our public model are not subject to NASS suppression rules, but if NASS published them it would apply its own.

---

## 5. Organisers (public information only)

A table of judges' and speakers' public professional roles was left out of the public copy of this note.

**Organisers and their stated goals**

- UC Davis event page [T]: "Hack the Harvest is a two-day hackathon for students from any discipline"; hosted by CATS with USDA, NVIDIA and HMCI; up to 200 students; teams of 5 to 7; "You don't need to know how to code."; "Strong teams mix engineers, data scientists, and business and management thinkers."; the question is "was a cornfield harvested for silage or for grain?"; "That difference is subtle and noisy, and it's easy to miss from far away." Build window 22.5 hours. Contact: Devin Sutherland (HMCI operations and project manager).
- Keeboh [T]: "open-source research platform" meant to "connect curious minds with compute, data, and opportunities"; its "first MVP beta launch" is this hackathon; USDA is "Challenge Provider", NVIDIA "Technology Partner".
- HMCI [T]: flagship project is the Rancho Cordova AI and Robotics Ecosystem, a 5 million dollar, three-year public-private partnership with NVIDIA-aligned workforce training. CATS lists HMCI, Solidigm and Niantic Spatial among its partners.
- Deck: sponsors USDA, NVIDIA, UC Davis, Solidigm, FarmGPU, HMCI; 25 points with Presentation 10; ties go to the higher Presentation score.

---

## 6. Landscape: does anything already tell silage from grain?

| Product | What it is (as opened) | Silage vs grain? | Source |
|---|---|---|---|
| NASS Cropland Data Layer | Annual crop map; 10 m since 2024; 2025 edition released 27 February 2026; corn-related classes: 1 Corn, 12 Sweet Corn, 13 Pop or Orn Corn, 225 Dbl Crop WinWht/Corn, 226 Dbl Crop Oats/Corn, 228 Dbl Crop Triticale/Corn, 237 Dbl Crop Barley/Corn, 241 Dbl Crop Corn/Soybeans | **No** class for silage | CDL FAQ and release page [T] |
| NASS in-season CDL acreage indications | Internal estimates of planted acreage for the ASB; not public | No | Boryan 2011 [R] |
| NASS Predictive Cropland Data Layer | Predicts crop rotations before the season; internal | No | AI inventory [R] |
| NASS Crop Sequence Boundaries | Field polygons with eight years of CDL classes; 15,973,106 polygons | No harvest information | CSB metadata [T] |
| NASS weekly Crop Progress | State percentages; the national report has no silage row; some state reports carry "corn harvested for silage" (Wisconsin verified by a sibling) | Percent of state progress, not acres or fields | labels.md, nowcast.md (sibling) |
| NASS Crop Progress and Condition gridded layers | Synthetic gridded weekly layers for corn, soybeans, cotton, winter wheat, 2015 onward | Not mentioned | NASS page [T] |
| USDA RMA satellite tools | Planting date, cover crops, acreage and crop type validation, Midwest | No harvest tool listed in 2024 | AI inventory [R] |
| NASA OPERA DIST-ALERT / DIST-ANN | 30 m; from HLS (Landsat 8/9, Sentinel-2A/B/C) and a separate Sentinel-1 product; vegetation disturbance = "loss of vegetation percent cover relative to the minimum of the baseline", baseline = "all cloud-free observations from the previous three years within a 31-day window"; validated on 300 sites | Generic vegetation loss; no crop meaning | JPL OPERA page; UMD GLAD page [T] |
| OpTIS (CTIC, Regrow, The Nature Conservancy) | "an automated system to map tillage, residue cover, winter cover, and soil health practices"; 2015-2021; lower 48 states; computed per field but "the privacy of individual producers is fully protected by reporting only spatially-aggregated results" | Not stated | CTIC [T] |
| GEOGLAM Crop Monitor | Monthly crop-condition bulletins "in support of market transparency and early warning" | No | cropmonitor.org [T] |
| NASA Acres, NASA Harvest | Research consortia | Nothing on the pages opened | [T] |
| EU Sen4CAP | ESA project for CAP paying agencies; crop type map, grassland mowing, vegetation status, agricultural practices monitoring; Sentinel-1 and Sentinel-2; pilots in Czech Republic, Italy, Lithuania, Netherlands, Romania, Castilla y Leon | Not stated on the page. In the EU the distinction comes from farmers' declarations (see labels.md, precedent.md) | esa-sen4cap.org [T] |
| Planet Planetary Variables | "cloud-free Crop Biomass data delivered daily at 10 meter resolution"; consistency "can support the identification of key events like harvesting or mowing" | No | planet.com [T] |
| EarthDaily Agro | Crop identification, crop monitoring and yield prediction, "real-time crop market intelligence" | No | earthdaily.com [T] |
| Regrow | MRV platform; "1.7+ billion acres of data and science"; practices in supply chains | No | regrow.ag [T] |
| Kayrros | Home page shows energy, risk and vegetation monitoring; no agriculture content | No | kayrros.com [T] |
| SatSure | India-based; farm-level credit and insurance intelligence, in-season monitoring | No | satsure.co [T] |
| CropProphet | "daily global weather-based crop analytics" for grain traders | No; not satellite based | cropprophet.com [T] |
| USDA FAS Crop Explorer, EU Area Monitoring System, Planet/Sinergise Area Monitoring, Descartes Labs, Indigo | Not opened | Unknown | section 13 |

**What is new about Kernel (Inference, to be phrased carefully):**

1. The target itself. None of the 19 product pages opened offers harvest end use for corn. Say "no operational product that we could find", not "first ever": precedent.md documents one dedicated research study and European crop maps with separate silage and grain maize classes.
2. The combination of an optical browning date with a radar cut date into "dry-down days".
3. Field calls rolled up with a survey-style estimator and reconciled to NASS totals, so the output is in the agency's own units.
4. A per-field evidence card and a review queue, which is what USDA's own entries ask for before any use.

**A candidate extra signal (Inference, untested):** OPERA DIST-ALERT measures vegetation loss against the same field's minimum over the previous three years in a 31-day window. A field chopped for silage in early September that was grain corn or still green in that window in the last three years should trigger; a field harvested for grain at its usual time should not. That makes DIST a ready-made detector of *late switchers*, the case the USDA speaker stressed. It will not fire on fields that are silage every year or that rotate with early-senescing soybeans. I could not open the product specification, so cropland behaviour is unconfirmed. Worth one hour only if a teammate is free.

---

## 7. Operating cost model for weekly national runs (order of magnitude)

### 7.1 Sourced inputs

| Input | Value | Source |
|---|---|---|
| Field polygons, all crops, national CSB 2018-2025 | 15,973,106 | CSB metadata [T] |
| Corn planted, 2025 | 98.8 million acres | task brief; statistics.md (sibling) |
| On-demand CPU | 0.192 dollars per hour for 4 vCPU (Azure D4s v5, East US, Linux) = 0.048 dollars per vCPU-hour; spot 0.0405 per hour = 0.010 per vCPU-hour | Azure Retail Prices API, 2026-11-14 [T] |
| GPU rental | L40S 1.00 to 2.00 dollars per hour; A10G 0.75 to 1.00; H100 2.00 to 5.00 | brev_ops.md (sibling; third-party prices, medium-low reliability) |
| LLM throughput | Nemotron 3 Nano 30B on one RTX 5090: 305 tokens/s single stream; about 2,100 tokens/s total for retrieval-shaped requests (3,500 in, 500 out) | brev_ops.md (sibling; one forum benchmark) |
| Federal salary | GS-13 step 1: 121,785 dollars; GS-13 step 5: 138,024; GS-14 step 1: 143,913; GS-12 step 1: 102,415 (Washington-Baltimore-Arlington, effective January 2026, locality 33.94%) | OPM Salary Table 2026-DCB [R] |
| Historical CDL cost per state | 750,000 dollars (Illinois, 1975, with research); 300,000 (Iowa, 1978); 150,000 (eight states, early 1980s); **75,000 (2000)**. Figure 4, per state in 2000: data 10K, data processing 8K, labour 50K (1983, inflation-adjusted: 60K, 100K, 83K). "Landsat data costs were $300 per Landsat scene" in the early 1980s and peaked at 4,400 dollars per scene | Hanuschak and Mueller [R] |
| Benefit of the CDL to estimates | "a State level estimate with relative sampling error reductions on the order of two to five compared to the ground sample data only" | same [R] |

### 7.2 Assumptions (ours; change them and recompute)

| Symbol | Assumption | Central | Range |
|---|---|---|---|
| N | Corn field polygons per year = corn acres / mean corn polygon size (25 to 40 acres assumed) | 3.5 million | 2.5 to 5 million |
| P | 10 m pixels of corn = 98.8e6 acres x 4,046.86 m2 / 100 m2 | 4.0e9 | fixed |
| a_opt, a_sar | New acquisitions per field per week: optical (Sentinel-2 plus Landsat via HLS), radar (Sentinel-1) | 3 and 1 | 2 to 4; 0.6 to 2 |
| b_opt, b_sar | Values read per pixel: red, NIR, SWIR1, SWIR2, one more band, scene classification mask; VV and VH | 6 and 2 | |
| r | Pixel-values processed per core-second (range read, decompress, mask, per-field mean) | 2e6 | 5e5 to 2e7 |
| k | Overhead factor for whole-tile reads, reprojection, retries, radar preprocessing | 10 | 3 to 30 |
| M | Memos per week: counties with corn plus states plus national | 2,050 | 1,500 to 3,000 |
| t | Tokens per memo, in and out | 3,500 and 500 | |
| F | Fields in the review band needing an evidence card, once per season | 5% of N = 175,000 | 2% to 10% |
| L | Loading on salary for benefits and overhead | 1.4 | 1.3 to 1.6 |

### 7.3 Formulas

```
values_week  = P * (a_opt*b_opt + a_sar*b_sar)            # 4.0e9 * (18 + 2) = 8.0e10
core_hours   = values_week / r / 3600 * k                  # 8.0e10 / 2e6 / 3600 * 10 = 111
cpu_cost     = core_hours * price_vcpu_hour                # 111 * 0.048 = 5.3 dollars
llm_tokens   = M * (t_in + t_out)                          # 2,050 * 4,000 = 8.2e6
gpu_hours    = llm_tokens / tokens_per_second / 3600       # 8.2e6 / 2,100 / 3600 = 1.1
llm_cost     = gpu_hours * price_gpu_hour                  # 1.1 to 2.2 dollars
card_tokens  = F * (1,500 + 150)                           # 2.9e8, once per season
card_cost    = card_tokens / 2,100 / 3600 * price_gpu_hour # 38 GPU-hours = 38 to 76 dollars
storage_GB   = N * weeks * features * 4 bytes / 1e9        # 3.5e6 * 35 * 40 * 4 / 1e9 = 19.6 (before compression)
people_cost  = FTE * salary * L                            # 2.5 * 138,024 * 1.4 = 483,000 dollars per year
```

Exact N for any year, once the boundaries are in DuckDB (class list from data_access.md):

```sql
SELECT count(*) AS n_fields, sum(CSBACRES) AS acres
FROM csb WHERE CDL2025 IN (1, 225, 226, 228, 237, 241);
```

### 7.4 Results

| Item | Central | Low to high | Notes |
|---|---|---|---|
| CPU per weekly national run | about 5 dollars | 1 to 25 (throughput range, overhead fixed at 10); about 65 in the worst corner of both ranges | 111 core-hours on demand; a 100-fold error would still be about 500 dollars |
| CPU per season (35 weekly runs plus one full backfill) | about 400 dollars | 70 to 1,800; about 4,500 in the worst corner | |
| LLM memos per week (self-hosted) | 1 to 2 dollars | | 1.1 GPU-hours |
| LLM memos per season | 40 to 80 dollars | | |
| Evidence cards for the review band, once | 40 to 80 dollars | 15 to 160 | |
| Storage | under 50 GB per season | | cents to a few dollars a month at an assumed 0.02 to 0.03 dollars per GB-month (price not verified today) |
| **All compute, storage and LLM per year** | **under 1,000 dollars** | **up to about 5,000** | |
| People, national operation | about 480,000 dollars | 320,000 to 690,000 | central: 2.5 analysts at GS-13 step 5 with loading 1.4; low: 2 at GS-13 step 1 with 1.3; high: 3 at GS-14 step 1 with 1.6 |
| People, first-season pilot in 3 to 5 states | about 190,000 dollars | | 1 analyst-year |
| Cost per corn field per year | about 0.14 dollars | | 483,000 / 3.5 million |
| Cost per corn acre per year | about 0.005 dollars | | |

Reading: labour is more than 95% of the cost, which matches NASS's own 2000 breakdown (50K of 75K per state) and its conclusion that "Spreading out the labor costs over as many States as possible and having co-funding partners is the key to future cost reductions". Earth Engine commercial pricing could not be read (the page returned no text), so no Earth Engine figure is given.

What is **not** in the model: the one-off cost of security authorisation and documentation; validation fieldwork; the in-season corn mask; management time. These are labour and belong in the people line.

---

## 8. Success metrics an agency would track

### 8.1 Metric set

| Metric | Definition | How NASS expresses the equivalent today | Proposed target (ours) |
|---|---|---|---|
| Lead time gained | Days from our indication to the Crop Production Annual Summary (released "at the beginning of January") | Calendar dates; first silage figure in January | 8 to 12 weeks if published; state clearly when the gain is internal only |
| Error against the final estimate | Percent difference of state silage acres and grain-harvested acres from the January estimate, by state and year; root mean square over the backtest; count of years above and below | "Chances are 2 out of 3 ..." reliability statement in Crop Production (statistics.md, nowcast.md) | Beat state-level persistence (nowcast.md gives the benchmark) |
| Track record | Number of state-years for which indication and final exist | "historical relationship of the survey results to the official estimate" | At least 3 seasons before operational use |
| Precision of the estimate | CV of the regression estimate of the grain-harvested ratio | CV by state (table 8.2) | Halve the CV in states above 5%; CDL history shows gains "on the order of two to five" for acreage |
| Field-level skill | Precision, recall and false positive rate per class on locked labels, with intervals | RMA lists "Type I and Type II errors" as key risks | Report per class with the majority baseline |
| Coverage | Share of corn acres with a valid call; share with no clear optical scene near the cut; share in the review band | Response rate and weighted item response rate | At least 95% called; review band at most 10% |
| Review workload | Fields reviewed per analyst-hour; share of machine calls overturned | Edit and analysis steps by RFO staff | Under 2 minutes per field (to be measured) |
| Timeliness of the run | Hours from last satellite pass to updated county table; pipeline runtime | Fixed release times | Within 24 hours of the weekly cut-off |
| Continuity | Scheduled weekly outputs delivered, including during survey interruptions | Weekly Crop Progress was cancelled for the weeks ending 5 October to 9 November 2025 (labels.md, nowcast.md) | 100% |
| Cost | Dollars and analyst-hours per state per season | Program cost per state (2000: 75,000 dollars) | Section 7 |
| Governance | Inventory row current; annual re-validation done; documented drift checks | M-25-21 ongoing monitoring | Yes or no |

### 8.2 Where the survey is thinnest (the slide)

Source: Annual Crop Production Methodology and Quality Measures, released 4 February 2026, pages 6 and 7 [R]. "Response rate" is for the December Agricultural Survey. "Item response" is the weighted item response rate for corn harvested for grain. "CV" is the coefficient of variation "for the ratio of harvested acres to planted acres" of corn harvested for grain.

| State | Sample 2025 | Response rate 2024 | Response rate 2025 | Item response 2025 | CV 2024 | CV 2025 |
|---|---|---|---|---|---|---|
| Arizona | 374 | 69.1 | 43.6 | 28.3 | 18.5 | **38.3** |
| California | 2,064 | 48.1 | 46.1 | 48.1 | 30.8 | **23.3** |
| Idaho | 1,670 | 45.8 | 40.2 | 35.7 | 8.6 | **18.5** |
| New Mexico | 678 | 48.6 | 42.8 | 21.9 | 13.3 | **18.2** |
| Utah | 736 | 74.6 | 61.0 | 53.7 | 11.3 | **14.1** |
| Washington | 1,548 | 42.3 | 36.4 | 55.7 | 11.2 | **11.8** |
| Montana | 2,139 | 45.9 | 38.8 | 38.4 | 11.5 | 10.1 |
| Oregon | 871 | 47.7 | 43.2 | 67.7 | 13.4 | 8.6 |
| Wyoming | 606 | 56.6 | 42.7 | 35.6 | 6.1 | 6.9 |
| Florida | 789 | 42.5 | 46.9 | 49.4 | 19.8 | 6.9 |
| West Virginia | 550 | 76.6 | 59.5 | 58.3 | 10.9 | 5.8 |
| New York | 1,154 | 43.3 | 44.9 | 42.0 | 13.4 | 5.0 |
| Pennsylvania | 1,443 | 47.5 | 44.3 | 41.9 | 5.0 | 4.4 |
| Wisconsin | 2,141 | 47.5 | 48.6 | 45.5 | 1.9 | 2.9 |
| Texas | 4,382 | 49.6 | 43.2 | 38.3 | 1.9 | 2.8 |
| Michigan | 1,762 | 50.8 | 40.4 | 39.1 | 1.1 | 2.0 |
| South Dakota | 2,606 | 36.9 | 29.0 | 29.5 | 0.8 | 1.1 |
| Minnesota | 2,772 | 38.8 | 33.5 | 31.3 | 0.6 | 0.5 |
| Iowa | 2,903 | 42.5 | 39.8 | 35.3 | 0.5 | 0.5 |
| Illinois | 2,656 | 42.0 | 37.5 | 38.1 | 0.1 | 0.3 |
| Nebraska | 3,200 | 36.1 | 30.2 | 31.0 | 0.4 | 0.3 |
| **United States** | **73,133** | **46.0** | **40.2** | **35.6** | **0.3** | **0.3** |

Other figures from the same document: national sample 73,269 in 2024; target CV for US corn planted acres is 1%; over the last decade the US survey CV for corn ranged from 1.0% to 1.3%.

**Inference:** the high CVs sit in western and north-eastern states where a large and variable share of corn is not harvested for grain. These are the states where a full-coverage satellite split would add the most information per dollar, and where a first pilot should run. In the Corn Belt the survey ratio is already precise to half a percent, so the value there is the county and field detail and the early read, not the state total. Do not claim that satellites beat a 0.3% national CV.

---

## 9. Recipes

### 9.1 An AI use case inventory row for Kernel (columns follow the 2024 federal file)

| Column | Entry |
|---|---|
| Use case name | Corn harvest end-use indication (grain or silage) |
| Topic area | Mission-enabling / statistics |
| Purpose and benefits | Produces a supplemental estimate of corn acres harvested for silage and for grain by county and state from public satellite data, earlier than and independent of the December Agricultural Survey, to support the Agricultural Statistics Board |
| Outputs | Per-field probability with four measured quantities and a review flag; county and state acreage estimates with uncertainty |
| Development stage | Initiated (prototype) |
| Impact type | Not high-impact: output is one of several indications reviewed by statisticians; it is not a principal basis for a decision about any individual or entity |
| Data | Public only: Sentinel-1, Sentinel-2, HLS, CDL, Crop Sequence Boundaries, public NASS totals |
| Custom code and access | Yes; source code publicly available (MIT) |
| Human oversight | Review queue for uncertain fields; no automated action |
| Monitoring | Annual re-validation against the January estimates; drift check on the four quantities |
| Key risks | False positives and false negatives by class; cloud gaps in the harvest week; regional timing; double cropping; corn-mask errors |

### 9.2 M-25-21 checklist for the notebook's last cell

1. Model family: printable two-question rule, then boosted trees. Policy text: "built with less data, require less compute, and are inherently more explainable".
2. Data: public; provenance table with URLs and access dates.
3. Testing: locked test split never used for tuning ("assessing for overfitting to known test data").
4. Metrics against the existing process: difference from the January estimate; CV; precision, recall, false positive rate.
5. Human review: uncertain fields are flagged; "Model results will not be used without independent review".
6. Generative AI: memos are drafts; every number is read from the database; inputs are public.
7. Code: public repository, MIT licence.
8. Limits: where it fails and how uncertain it is.

### 9.3 One-season pilot plan (Inference)

| Month | Step |
|---|---|
| February to March | Agreement (pilot certification or cooperative agreement); choose 3 to 5 states from table 8.2 plus Wisconsin; port code into the authorised environment |
| April to July | Retrain on internal labels for two past seasons; replay those seasons as dated vintages; write the reliability table |
| August to November | Weekly runs; review queue tested by field-office staff in one state |
| December | Indication delivered before RFO analysis |
| January | Score against the Annual Summary; decide go or no-go |

### 9.4 Sentences that should hold up in front of NASS statisticians

1. "NASS has given satellite-based acreage indications to the Agricultural Statistics Board since 2007. We add the one that is missing: what the corn was harvested for."
2. "The December Agricultural Survey behind the January silage number had a 40.2% response rate in 2025, down from 46.0%. Imagery covers every field."
3. "In California the CV of the corn harvested-for-grain ratio was 23.3% in 2025; in Iowa it was 0.5%. We expect to help most where the survey is thinnest, and we do not claim to beat it in Iowa."
4. "We do not count pixels. We report a regression-style estimate next to the raw sum, as the CDL program does."
5. "The model is the same family as the CDL's boosted decision trees, small enough to print."
6. "This is an indication for statisticians, not a decision about a farmer."
7. "At national scale the computing costs a few dollars a week on our estimate. The real cost is two or three analysts."

---

## 10. Pitfalls

1. **Claiming replacement.** NASS's word is "supplemental". The ASB decides by consensus and reconciles states to the national number.
2. **Claiming public lead time that only NASS can grant.** Separate "our public nowcast is N weeks early" from "inside NASS this improves the January estimate".
3. **Using unit names we have not confirmed.** The October 2026 chart shows three Offices at the top level and draws no divisions. Whether the Research and Development Division and Methodology Division named in the brief still exist beneath them is unverified.
4. **Pitching enforcement or "farmer level" action.** That is the rights-impacting class (RMA). Stay with statistics unless asked.
5. **Republishing labels.** The evaluation set may come from confidential sources. Keep field-level labels out of the public repository until the organisers confirm.
6. **Over-precise cost claims.** Our compute figures are estimates with wide ranges; show the assumptions. Earth Engine and storage prices were not verified today.
7. **Quoting people facts that are not verified.** Only the facts in section 5 were opened. In particular, do not attribute the 2013 Field Crops Research paper to the judge by name in the pitch; ask him.

## 11. Open questions (for the USDA table)

1. Which unit would own a silage and grain indication after the 2026 reorganisation, and would it go to the ASB for the January summary or be released as an experimental public product?
2. How were the evaluation labels built (FSA 578 intended use, survey, photo-interpretation), and may field-level labels be shared publicly?
3. Would an early public grain-versus-silage estimate be treated as market-sensitive?
4. Which compute environment is authorised for NASS geospatial work today (the disaster page mentions a "GEE web app"), and does it include GPUs?
5. Are the four other USDA judges from NASS, OCIO or elsewhere?

---

## 12. Annotated bibliography (every URL was opened in this run unless marked)

**Mission Model Canvas**
- Blank, S. (2016-02-23). The Mission Model Canvas - An Adapted Business Model Canvas for Mission-Driven Organizations. https://steveblank.com/2016/02/23/the-mission-model-canvas-an-adapted-business-model-canvas-for-mission-driven-organizations/ [T]. Definitions of the five changed boxes; quotes in section 2.
- Osterwalder, A. (2016-02-25). Same article on Strategyzer. https://www.strategyzer.com/library/the-mission-model-canvas-an-adapted-business-model-canvas-for-mission-driven-organizations [T]. Guiding questions for Deployment and Buy-in.
- Strategyzer. The Value Proposition Canvas. https://www.strategyzer.com/library/the-value-proposition-canvas [T]. Jobs, pains, gains; fit.

**NASS: organisation, process, quality**
- NASS organisational chart, 7 October 2026. https://www.nass.usda.gov/sites/default/files/About_NASS/Org_Chart/OrgChart.pdf [R].
- NASS Biographies. https://www.nass.usda.gov/about-nass/nass-biographies [T].
- NASS agency overview. https://www.nass.usda.gov/About_NASS/index.php [T]. Link list; mission; "cooperative relationship with universities and State Departments of Agriculture".
- **Annual Crop Production Methodology and Quality Measures, released 4 February 2026.** https://www.nass.usda.gov/sites/default/files/Publications/Methodology_and_Data_Quality/Crop_Production/02_2026/cranqm26.pdf [R, 13 pages]. Survey timeline, ASB process, outside data, revision policy, response rates and CVs by state. The most useful single document for the pitch. Index pages: https://www.nass.usda.gov/publications/methodology-and-data-quality and https://www.nass.usda.gov/Publications/Methodology_and_Data_Quality/Crop_Production/index.php [T].
- Agricultural Statistics Board and Lockup. https://www.nass.usda.gov/about-nass/asb-and-lockup [T]. "Market-sensitive ASB reports are compiled and issued under special security conditions known as Lockup."
- NASS Learning Agenda FY2024-2026. https://www.nass.usda.gov/sites/default/files/About_NASS/pdf/learning-agenda-fy2426.pdf [R, 10 pages]. Priority questions on alternative data and the geospatial programme.
- Regulations Guiding NASS. https://www.nass.usda.gov/about-nass/regulations-guiding-nass [T]. 7 U.S.C. 2276, 3318, CIPSEA, DR 1042-042.
- Confidentiality Pledge. https://www.nass.usda.gov/about-nass/confidentiality-pledge [T].
- Assistance to Other Organizations. https://www.nass.usda.gov/about-nass/assistance-to-other-organizations [T].
- NASS research reports by date. https://www.nass.usda.gov/education-and-outreach/reports-presentations-and-conferences/reports-by-date [T]. Author search for the judges; list of remote-sensing reports.

**NASS: geospatial programme**
- **Boryan, C., Yang, Z., Mueller, R., Craig, M. (2011). Monitoring US agriculture: the US Department of Agriculture, National Agricultural Statistics Service, Cropland Data Layer Program. Geocarto International 26(5), 341-358.** https://www.nass.usda.gov/sites/default/files/Education_and_Outreach/Reports,_Presentations_and_Conferences/reports/Monitoring_US_agriculture_USDA-NASS_Cropland_Data_Layer_Program.pdf [R, 19 pages]. How indications reach the ASB; regression estimator; See5; partners; confidentiality of FSA data.
- **Hanuschak, G., Mueller, R. (about 2001-2002). Cost and Benefit Analysis of a Cropland Data Layer.** https://www.nass.usda.gov/sites/default/files/Education_and_Outreach/Reports,_Presentations_and_Conferences/reports/02_09_CostBeneftCDL_Pecora15_GAH.pdf [R, 8 pages]. Cost per state over time; partnership history; sampling-error reductions.
- CDL FAQ. https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php [T]. Release dates, classes, purpose, ground truth, confidentiality. The fetch tool also reported "75.4% OVERALL CROP ACCURACY" for 2025 and 77.5% for 2024; verify before quoting.
- CDL release page. https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php [T].
- Research and Science index. https://www.nass.usda.gov/Research_and_Science/index.php [T]. Partner statements for VegScape, CroplandCROS, CSB.
- Crop Sequence Boundaries. https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php and metadata https://www.nass.usda.gov/research-and-science/crop-sequence-boundaries/metadata-crop-sequence-boundaries-2025 [T]. The page also lists, not opened: "Preseason crop type prediction using crop sequence boundaries" (ScienceDirect S0168169923001564).
- Crop Progress and Condition gridded layers. https://www.nass.usda.gov/research-and-science/crop-progress-gridded-layers [T].
- Disaster Analysis. https://www.nass.usda.gov/research-and-science/disaster-analysis [T].

**Federal AI and IT policy**
- **OMB M-25-21, 3 April 2025.** https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-21-Accelerating-Federal-Use-of-AI-through-Innovation-Governance-and-Public-Trust.pdf [R, 25 pages].
- **2024 Federal AI Use Case Inventory (OMB).** https://github.com/ombegov/2024-Federal-AI-Use-Case-Inventory [T]; data file https://raw.githubusercontent.com/ombegov/2024-Federal-AI-Use-Case-Inventory/main/data/2024_consolidated_ai_inventory_raw.csv [R, parsed locally: 1,757 rows, 89 USDA, 10 NASS].
- FedRAMP. https://www.fedramp.gov/ [T].
- SCINet. https://scinet.usda.gov/ [T].

**Pathways**
- 15 U.S.C. 3719, Prize competitions. https://www.law.cornell.edu/uscode/text/15/3719 [T].
- Challenge.gov. https://www.challenge.gov/ [T]. Sunset notice.
- SBIR.gov. https://www.sbir.gov/ [T]. Phase amounts.
- NASA Acres. https://www.nasaacres.org/ [T]. NASA Harvest. https://www.nasaharvest.org/ [T].

**Cost inputs**
- OPM Salary Table 2026-DCB. https://www.opm.gov/policy-data-oversight/pay-leave/salaries-wages/salary-tables/pdf/2026/DCB.pdf [R].
- Azure Retail Prices API, Standard_D4s_v5, eastus. https://prices.azure.com/api/retail/prices (filter: armRegionName eq 'eastus' and armSkuName eq 'Standard_D4s_v5' and priceType eq 'Consumption') [T].

**Landscape**
- NASA JPL OPERA DIST product suite. https://www.jpl.nasa.gov/go/opera/products/dist-product-suite/ [T]. UMD GLAD DIST-ALERT. https://glad.umd.edu/dataset/DIST-ALERT [T].
- CTIC OpTIS. https://www.ctic.org/OpTIS [T].
- Sen4CAP. https://www.esa-sen4cap.org/ [T].
- GEOGLAM Crop Monitor. https://cropmonitor.org/ [T].
- Planet Planetary Variables. https://www.planet.com/products/planetary-variables/ [T].
- EarthDaily agriculture. https://earthdaily.com/industry/agriculture/ [T]. Regrow. https://www.regrow.ag/ [T]. Kayrros. https://www.kayrros.com/ [T]. SatSure. https://satsure.co/ [T]. CropProphet. https://www.cropprophet.com/ [T].

**People and organisers**
- UC Davis: https://gsm.ucdavis.edu/faculty/hemant-bhargava ; https://gsm.ucdavis.edu/center-analytics-and-technology-society ; https://gsm.ucdavis.edu/center-analytics-and-technology-society/events ; https://gsm.ucdavis.edu/event/hack-harvest [T].
- HMCI: https://hmci.ai/ ; https://hmci.ai/team [T]. Keeboh: https://keeboh.com/ [T].
- Agribusiness Associates: https://www.agribusinessassociates.com/ [T]. Niantic Spatial: https://www.nianticspatial.com/ [T].
- Crossref record for doi 10.1016/j.fcr.2012.11.023: https://api.crossref.org/works/10.1016/j.fcr.2012.11.023 [T].
- Local files: DOCS/Hack the Harvest Saturday Deck.pdf; DOCS/Kernel_USDA_Briefing.pdf [R].

**Sibling reports used for cross-reference (not re-verified):** labels.md, statistics.md, nowcast.md, data_access.md, brev_ops.md, precedent.md.

## 13. Source access log: not opened, not cited as evidence

| Target | Result |
|---|---|
| WebSearch (any query) | refused: session search budget exhausted |
| https://www.usda.gov/ai and https://www.usda.gov/ai/inventory (USDA AI strategy, inventory, compliance plan) | HTTP 403 |
| https://www.nass.usda.gov/About_NASS/Organization/index.php ; CSB 2023 metadata page | HTTP 404 (replaced by the pages cited above) |
| https://lpdaac.usgs.gov/products/opera_l3_dist-alert-hls_v1/ | redirect to a generic page; product specification not read |
| https://ipad.fas.usda.gov/cropexplorer/ (FAS Crop Explorer) | DNS failure |
| https://www.cdo.gov/council-members/ ; https://fedscoop.com/tag/chris-alvares/ | DNS failure; 404 |
| https://www.ars.usda.gov/office-of-technology-transfer/ (CRADA) | DNS failure |
| NIFA SBIR page | HTTP 404 |
| European Commission page on managing CAP payments (Area Monitoring System) ; EUR-Lex Regulation (EU) 2021/2116 | HTTP 429; landing page only |
| https://www.sentinel-hub.com/explore/area-monitoring/ | HTTP 403 |
| https://cloud.google.com/earth-engine/pricing ; https://cloud.google.com/security/compliance/fedramp | page returned no text |
| https://hack-the-harvest.devpost.com/ and /rules | HTTP 403 |
| https://www.hacktheharvest.com/ ; UC Davis CATS team-members page ; GitHub 2025 federal AI inventory | DNS failure; 404; 404 |
| Descartes Labs, Indigo, Hacking for Defense (h4d.us) | not attempted (no known URL worth a guess) |
