# Kernel deck: current slides and proposed rewrite (5-minute pitch)

Each slide appears twice: **CURRENT** is what the deck says now, and **PROPOSED** is the rewrite. A 5-minute slot fits about 9 slides at roughly 30 seconds each, so the proposal merges or cuts several slides. Every number comes from the repo: `autoresearch/RESULTS.md`, the team's own slides, and `DOCS/VERIFIED_METRICS.md`.

**Proposed order (9 slides + 1 backup):**

| # | Slide | Source |
|---|---|---|
| 1 | Title | slide 1 |
| 2 | The problem | merges slides 2, 3, 4 |
| 3 | How a satellite sees a cornfield | **new** |
| 4 | Silage: a cliff. Grain: a fade. | replaces slide 8; its chart is empty |
| 5 | The rule | **new** |
| 6 | Proof: learned in Canada, right in Maryland | **new** |
| 7 | Acres for every state | merges slides 5, 6, 7 |
| 8 | Every call comes with its evidence (Nemotron) | merges slides 9 and 12 |
| 9 | What worked, what didn't + next | merges slides 10, 11, 14 |
| Backup | Keeboh | slide 13, shown only if asked |
| Cut | Pitch advertisement | slide 15 |

---

## SLIDE 1

### CURRENT
EYEBROW: HACK THE HARVEST 2026 · SILAGE OR GRAIN?
HEADER: Kernel (logo)
TEXT: Silage and grain acres for every state, before January.
BOX: TRY IT LIVE ON YOUR COMPUTER · rakd23-kernel-board.hf.space
IMAGE: QR code, top right

### PROPOSED
EYEBROW: HACK THE HARVEST 2026 · SILAGE OR GRAIN?
HEADER: Kernel (logo)
TEXT: Tells silage from grain for any cornfield, from free satellite pictures, months before the official count.
BOX: TRY IT LIVE · rakd23-kernel-board.hf.space
IMAGE: QR code (keep)

---

## SLIDE 2

### CURRENT
HEADER: Farmers report plans in June. Plans change by August. NASS finds out in January.
TIMELINE (4 steps):
- JUNE – JULY: Farmers certify every corn acre, grain or silage, to USDA's FSA by mid-July.
- AUG – OCT: Drought or a hungry dairy turns grain fields into silage.
- HARVEST: The switch finally shows, in the field and from space.
- JANUARY: First official silage acres, after markets have moved.
IMAGE: "This is fine" meme
CALLOUT: Every silage acre makes no grain, and nobody knows until January.

## SLIDE 3

### CURRENT
HEADER: What We Heard from USDA
CARDS (top row): Fields look identical until harvest day · Farmers switch late, and surveys miss it · Every answer must be defended to markets
BIG NUMBERS (bottom row):
- 93%: of harvested corn is grain, so "always grain" looks 93% right
- Jan: first official count of silage acres
- 0: public field-level silage/grain labels in the US
QUOTES ("In their own words", USDA NASS lead, Saturday Q&A):
- "…two numbers… acres of corn for grain, acres of corn for silage."
- "The earlier the better. That's the bottom line."
- "We don't really use satellite data much to do the acreage side."

## SLIDE 4

### CURRENT
TEXT: Farmers tell USDA what every corn acre is for by mid-July. That record is public months before January.
IMAGE: Spider-Man pointing meme

### PROPOSED (one slide replaces 2, 3 and 4)
HEADER: Nobody knows the silage count until January
TIMELINE (keep the 4 steps, shorter):
- JUNE – JULY: Farmers report their plans.
- AUG – OCT: Drought or a hungry dairy changes the plan.
- HARVEST: The real choice shows, in the field and from space.
- JANUARY: The first official silage number arrives, after markets have moved.
BIG NUMBERS (keep 2 of 3):
- 93%: of corn is grain, so a lazy "always grain" guess already looks 93% right
- 0: public field-by-field silage/grain records in the US
QUOTE (keep 1): "The earlier the better. That's the bottom line." (USDA NASS lead)
NOTE: Cut both memes; they take time and say nothing. The "FSA record is public by July" point belongs on slide 7, where it explains the acreage model.

---

## SLIDE 3 (NEW): How a satellite sees a cornfield

### PROPOSED
HEADER: A satellite can tell how green a field is
TEXT: Healthy green leaves reflect a lot of invisible near-infrared light and soak up red light. A satellite measures both, and from them we get one **greenness score** per field, called NDVI.
SCALE (draw as a horizontal bar, brown to green):
- 0.2 = bare soil
- 0.5 = half-covered or drying crop
- 0.9 = thick green corn
BULLETPOINTS (where the pictures come from):
- **Sentinel-2**: two European satellites that photograph every field on Earth about **every 5 days**, 10 m per pixel (a 16-acre field is ~650 pixels).
- **Free and public.** No account, no purchase: we download them from Microsoft's Planetary Computer. Any other farm, state or country works the same way.
- **We skip what isn't the field.** Edges (roads, hedges) and cloudy pixels are removed. Each field still had 13–29 clear pictures between June and October.
- **One smooth line per field.** We connect the clear pictures into a day-by-day greenness line and smooth out the noise.

---

## SLIDE 8 → becomes SLIDE 4

### CURRENT
EYEBROW: FIELD-LEVEL CHECK · USDA BELTSVILLE FIELDS, 2021 · GREENNESS (NDVI)
HEADER: Silage: a cliff. Grain: a fade.
CHART: titled "Silage: a cliff. Grain: a fade." The axes and legend are drawn (Greenness NDVI 0.1–0.9; Jun 29 – Oct 7; Silage fields / Grain fields), but **the lines are missing: the chart is empty.**
CARDS:
- SILAGE: 0.80 → 0.22 in five days
- GRAIN: 0.81 → 0.33 over five weeks
- (yellow) Both lose their green around Sep 10. Timing alone fails. The shape is the signal.
FOOTNOTE: Median NDVI of 18 labeled field-years (4 silage, 14 grain), Sentinel-2 L2A, cloud-masked. Dates shown where enough fields were clear. On all 44 Beltsville field-years (2021–2023), a model trained only in Quebec found 10 of 12 silage fields.

### PROPOSED
EYEBROW: REAL FIELDS · USDA BELTSVILLE FARM, MARYLAND, 2021
HEADER: Silage drops off a cliff. Grain fades slowly.
DATA VISUALIZATION (see "Data visualization idea" below): two rows of colored squares, one per farm, one square per week from June to October.
CARDS:
- SILAGE (field 280): green 0.74 → bare 0.27 in **11 days**. A chopper takes the whole green crop in one go and leaves bare ground.
- GRAIN (field 334): 0.70 → 0.31 over **27 days**. The plant turns yellow, then brown, before the combine comes.
- (yellow) Both start losing green in the same week. **When** doesn't tell them apart. **How fast** does.
FOOTNOTE: Weekly averages of the smoothed greenness line, from free Sentinel-2 pictures. Field 280 had 29 clear pictures June–October and field 334 had 15.

---

## SLIDE 5 (NEW): The rule

### PROPOSED
HEADER: One simple rule, a farmer would agree with
TEXT: We call a field **silage** if either is true:
BULLETPOINTS:
- **It went from green to bare in under 2½ weeks** (17.5 days, measured from 80% of its peak greenness down to 20%). Chopping takes everything at once. Grain dries for 3–4 weeks first.
- **It is green again in November–December** (greenness above 0.65): a cover crop was sown right after an early harvest. Grain fields are still brown then. Under snow this rule simply stays quiet.
TEXT: Otherwise: grain.
BOX "How we found 2½ weeks": We took fields where we already knew the answer, tried every cut-off from 1 day up, and kept the one that sorted them best. It came out at **17.5 days in Canada and 17.5 days in Maryland.**
NOTE: The fast-drop rule needs only the season up to harvest, so it calls each field within days of its harvest. In Maryland that's by early October, three months before January.

---

## SLIDE 6 (NEW): Proof

### PROPOSED
HEADER: Learned in Canada. 44 out of 44 right in Maryland.
TEXT: We learned the rule on **801 cornfields in Quebec, Canada** (the province's own farm records, 2023), then tested it on the **USDA's 44 Maryland field-years** (Beltsville research farm, 2021–2023). It had never seen a single Maryland label.
TABLE:

| Learned on | Tested on | Fields right |
|---|---|---|
| Quebec, Canada (801 fields) | USDA Maryland farm (44 field-years) | **44 / 44 = 100%** (12 of 12 silage, 0 false alarms) |
| Maryland, 2 of 3 years | Maryland, the third year (each year in turn) | **44 / 44 = 100%** |
| Maryland (44) | Quebec, Canada (801) | **718 / 801 = 90%** (guessing "always grain" gets 80%) |
| Team's earlier field model, learned in Quebec | USDA Maryland farm | 37 / 44 = 84% |

BULLETPOINTS:
- **It travels.** The same 2½-week cut-off comes out in both countries, two climates, about 500 miles apart.
- **It makes sense.** A chopper is fast; drying is slow. No black box, nothing to take on faith.
- **It's cheap.** Free pictures, one rule, under a second for every field.
FOOTNOTE (keep it on the slide; judges will ask): The "green in winter" bar (0.65) was set by hand, not learned, and both rules were designed while studying the Maryland fields. With the fast-drop rule alone, learned in Quebec: 42 / 44 in Maryland.

---

## SLIDE 5

### CURRENT
HEADER: Two tiers, 20 candidate models
CARDS:
- A-G3 · Grain, no NASS: Farmers' FSA certifications × the 3-year median NASS/FSA ratio. No current-year NASS data.
- A-S3 · Silage residual: FSA planted minus our grain estimate, × last year's silage share, blended with the 3-year mean.
- Tier B · NASS-informed: Adds NASS planted acres, yield, condition and cows. Grain gains 0.03 points; silage gets worse.
- The bar to beat: NASS. Its November grain forecast: 1.66% state miss, 2017–24. No silage number before January.
BOX (green): We forecast with A-G3 and A-S3. Rules fixed before any score; audits reproduced every number.

## SLIDE 6

### CURRENT
EYEBROW: BACKTEST 2017–2024 · ONLY DATA PUBLISHED BY THAT DATE
HEADER: How far off we are
TABLE:

| Model (lower is better) | Nov 15 · state miss | Nov 15 · US miss | Sep 15 · state miss | 2025 check · state |
|---|---|---|---|---|
| A-G3 grain · no NASS (used) | 1.76% | 1.09% | 1.75% | 1.72% |
| B-G7 grain · NASS-informed | 1.73% | 1.06% | 2.08% | 1.66% |
| NASS's own grain forecast | 1.66% | 0.82% | 2.53% | 1.64% |
| A-S3 silage (used) | 12.52% | 4.00% | 12.63% | 14.32% |

CALLOUTS:
- September: we beat NASS. Our grain miss is 1.75%, NASS's own forecast 2.53%.
- November: a statistical tie with NASS, 1.76% vs 1.66%, using no NASS data from this year.
FOOTNOTE: State miss = sum of state errors ÷ actual acres; US miss = error of the national total. Each year is rebuilt as of that date, scored against NASS's final the next January. A-S3 beat our previous silage model (13.12%) in 7 of 8 years. 2025 scored once.

## SLIDE 7

### CURRENT
EYEBROW: 2026 FORECAST · SHARE OF HARVESTED CORN ACRES
HEADER: 6.6% silage · 93.4% grain
CARDS: US SILAGE 2026: 6.6% (6.30M acres, range 6.02–6.80M) · US GRAIN 2026: 93.4% (88.69M acres, range 87.1–90.3M)
TABLE:

| Top silage states | Silage | Grain | Silage share | 2025 actual |
|---|---|---|---|---|
| United States | 6.30M | 88.69M | 6.6% | 6.4% |
| Wisconsin | 836K | 3.15M | 21.0% | 21.6% |
| New York | 476K | 556K | 46.1% | 53.2% |
| South Dakota | 427K | 5.91M | 6.7% | 5.8% |
| Minnesota | 373K | 8.36M | 4.3% | 4.1% |
| California | 354K | 56K | 86.2% | 83.1% |
| Michigan | 336K | 1.96M | 14.6% | 14.7% |
| Pennsylvania | 326K | 685K | 32.3% | 32.8% |

FOOTNOTE: Share = silage ÷ (silage + grain) harvested acres. Silage: A-S3 (48 states); grain: A-G3 (41 states); 80% ranges. Our grain total is within 0.2% of NASS's November figure (88.51M). Tier B and the submitted file also give 6.6%. 2025 actual = NASS final.

### PROPOSED (one slide replaces 5, 6 and 7)
EYEBROW: THE SAME QUESTION, STATE BY STATE
HEADER: 2026: 6.6% silage, 93.4% grain. In September, not January.
TEXT: Farmers' own July plans (public USDA FSA records) plus last year's patterns give acres for every state.
LEFT (two big numbers): US silage **6.30M acres** (range 6.02–6.80M) · US grain **88.69M acres** (range 87.1–90.3M)
RIGHT TABLE (shortened to 4 rows):

| How far off (lower is better) | In September | In November |
|---|---|---|
| Our grain estimate | **1.75%** | 1.76% |
| NASS's own grain forecast | 2.53% | 1.66% |
| Our silage estimate | 12.6% | 12.5% |

CALLOUT: **September: we beat NASS on grain.** November: a tie, using no NASS data from that year.
NOTE: Drop the "two tiers, 20 candidate models" slide; that level of detail is for questions. Keep the top-states table as a backup slide.
NEXT STEP (say it out loud): the field rule from slide 5 turns into a state number by running it on sample fields in each state. That's how the view from space feeds the acreage forecast.

---

## SLIDE 9 + SLIDE 12 → become SLIDE 8

### CURRENT (slide 9)
HEADER: Every call comes with its evidence
CARDS:
- TOOLS IT CALLS · Curve, signals, call: Typed tools only. Nemotron reads our computed numbers and never invents its own.
- WHAT IT WRITES · One story per field: Plain English a statistician can defend to a market, field by field.
- HOW WE TEST IT · Checked by code: Code flags any number in a story that is not in the tool output.
BANNER: Model behind it found 10 of 12 silage fields it never saw
SIDE CARD: HARVEST STORY · NEMOTRON · Field 280 · 2021 · Silage-like. "Cut around Sep 10 while still 89% green. Greenness fell from 0.81 to 0.29 in about 3 days. The ground afterward looks bare." EVIDENCE: One-step drop 0.51 · Green at cut 89% of peak · Residue after (NDTI) 0.13 · Example from real 2021 data

### CURRENT (slide 12)
EYEBROW: NVIDIA NEMOTRON · HOW WE USED IT
HEADER: NVIDIA: what helped, what hurt
COLUMNS:
- HOW WE USED IT: Nemotron 3 Super writes each Harvest Story · Nano 4B check script for Keeboh's B200 GPU · Brev L4 box: our app plus vLLM for an Explain button · Brev credits pay for every API call
- WHAT WORKED: Typed tools kept numbers honest · Code flags any number not in the facts · Plain English a statistician can defend · Open model: USDA could host it on its own servers · Nano 4B fits a 24 GB L4: no rate limits
- PAIN POINTS: Unclear which model is best for tool calls · Free text can invent numbers; we check each · API key leaked in team chat; we rotated it · vLLM on Brev L4 crashed: no C compiler · Brev links need a login, so the demo runs on Hugging Face
- NEXT: Run Nemotron locally so no farm data leaves USDA · Score all 44 stories: share matching, fields per second · Agent drafts the state acreage memo · Scale features on GPU to a whole state
FOOTNOTE: Code: kernelag/explain.py (stories and number check) · kernelag/nemotron_check.py (Nano 4B on GPU) · kernel_app.py and brev_setup.sh (Brev). Keeboh GPU: one NVIDIA B200, 183 GB.

### PROPOSED
EYEBROW: NVIDIA NEMOTRON
HEADER: Every call comes with a plain-English reason
TEXT: Nemotron reads the numbers our rule computed and writes a short story a statistician can defend. A script checks that every number in the story really came from the data.
SIDE CARD (keep the format, update the numbers to the rule): **Field 280 · 2021 · Silage.** "Greenness held near 0.86 all of August, then fell from 0.74 to 0.27 in 11 days in early September. That's a chopper, not drying. A cover crop greened the field again by November."
BULLETPOINTS (3 only):
- Open model: USDA could run it on its own computers, so no farm data leaves.
- Numbers come from our tools, never from Nemotron itself.
- Next: Nemotron reads the satellite pictures themselves (we're testing this now).
NOTE: Change the banner "found 10 of 12 silage fields it never saw" to "**12 of 12** silage fields, rule learned in Canada", or drop it. Move the pain-points column to the backup slide.

---

## SLIDE 10

### CURRENT
EYEBROW: HONEST REVIEW · KERNEL MODELS, AUDITED
HEADER: What worked, what didn't
COLUMNS:
- WHAT WORKED: Grain ties NASS in November: 1.76% vs 1.66% · Beats NASS in September: 1.75% vs 2.53% · Silage beats our old model in 7 of 8 years · Audits rebuilt every number from raw files
- WHAT DIDN'T: NASS still wins on 2012–2024 and the US total · Ridge and boosted trees added nothing over ratios · NASS's current-year inputs added just 0.03 points · Moisture rule as a field test: 0.68 vs our 0.84
- LIMITATIONS: Silage gains are in the state split, not the US total · Even knowing true non-grain acres, silage misses 8.4% · Field test: 44 field-years, one farm · Satellite state test still running

## SLIDE 11

### CURRENT
HEADER: Long-Term Vision
PHASES:
- PHASE 1 · Two numbers, every state: Grain and silage by state from farmer certifications: tied with NASS in November.
- PHASE 2 · Add the view from space: 300 satellite sample areas in the 15 top silage states, 2016–2026, tests fixed in advance.
- PHASE 3 · A new signal for NASS: An acreage forecast with known error, ready before January 1, next to the surveys.
BANNER (green): NORTH STAR · Silage acres known by October, not January

## SLIDE 14

### CURRENT
HEADER: Every cornfield tells how it was harvested.
TEXT: Surveys ask. Kernel looks.
BOX: TRY IT LIVE: 52 MODELS RANKED SIDE BY SIDE → rakd23-kernel-board.hf.space
IMAGE: Kernel logo, QR code
FOOTER: Team Kernel · Live board: rakd23-kernel-board.hf.space · github.com/Severynson/Hack-the-Harvest

### PROPOSED (one closing slide replaces 10, 11 and 14)
HEADER: Every cornfield tells how it was harvested.
TEXT: Surveys ask. Kernel looks.
THREE COLUMNS:
- WORKS TODAY: Field rule: 44/44 on USDA's Maryland fields, learned in Canada · Grain acres beat NASS in September (1.75% vs 2.53%)
- STILL HARD: 1 in 3 Quebec silage fields dries slowly, like grain, so the rule calls it grain · State silage acres still miss by ~12%
- NEXT: Run the rule on sample fields in the 15 top silage states, so the satellite feeds the state numbers · Add radar, which sees through clouds and tells standing stalks from bare ground
BANNER (green): Silage acres known by October, not January.
BOX: rakd23-kernel-board.hf.space + QR code

---

## SLIDE 13 → BACKUP (show only if asked)

### CURRENT
EYEBROW: KEEBOH · OUR TEAM WORKSPACE
HEADER: Keeboh: what helped, what hurt
COLUMNS:
- HOW WE USED IT: One shared workspace for the team · Starter kit and BARC labels ready at 10:30 · Notebooks pulled three seasons of satellite data · GPU, then submission
- WHAT WORKED: No setup: data and kit already there · Reached satellite data our other tools couldn't · One shared copy of the data and labels · Installed packages survive restarts · .env files stay out of the submission
- PAIN POINTS: No live co-editing: last save wins · Can't download a folder; we zipped it with code · Outputs lost if a notebook isn't saved first · No GitHub sync: moving work was manual · Kit instructions written for PowerShell
- WISH LIST: Real-time co-editing · One-click GitHub sync · Built-in secrets manager · Folder download

### PROPOSED
Keep as is, but move it after the closing slide as a backup. If sponsor feedback is required in the 5 minutes, say one line: "Keeboh got us from zero to satellite data in an hour; we'd love GitHub sync."

## SLIDE 15

### CURRENT
Pitch advertisement ("Want to make a presentation like this one? … Create a presentation (It's free)").

### PROPOSED
Delete it. It's added by the Pitch export, not our content.

---

# DATA VISUALIZATION IDEA (for the new slide 4)

**What to draw:** a "greenness strip" for each farm, one row per farm. Each row is a line of squares, **one square per week**, from the first week of June to the last week of October. That's the corn season only: winter and early spring are left out on purpose, because the rule doesn't need them. Square color = that week's greenness: dark green for 0.9, light green for 0.6, tan for 0.4, brown for 0.2. Write the value small inside each square.

**Marks:**
- **Yellow** square outline = the week of peak greenness.
- **Black box** around the run of squares where greenness drops from its peak level down to bare soil (from 80% of the peak down to 20%).
- Label under each box: "Cliff: 11 days → silage" or "Fade: 27 days → grain".

**Real values to use** (weekly averages of the smoothed greenness line, USDA Beltsville farm, Maryland):

Row 1: **Field 280, 2021, SILAGE** (29 clear pictures June–October)

| Week of | Jun 1 | Jun 8 | Jun 15 | Jun 22 | Jun 29 | Jul 6 | Jul 13 | **Jul 20** | Jul 27 | Aug 3 | Aug 10 | Aug 17 | Aug 24 | **Aug 31** | **Sep 7** | **Sep 14** | Sep 21 | Sep 28 | Oct 5 | Oct 12 | Oct 19 | Oct 26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Greenness | 0.25 | 0.36 | 0.53 | 0.70 | 0.78 | 0.83 | 0.86 | **0.87** | 0.86 | 0.86 | 0.86 | 0.84 | 0.82 | **0.74** | **0.48** | **0.27** | 0.25 | 0.24 | 0.27 | 0.35 | 0.44 | 0.53 |

- Yellow: week of **Jul 20** (peak 0.87).
- Black box: **Aug 31 – Sep 14**, 3 squares (exact drop: Sep 3 to Sep 14 = **11 days**).
- After the box the field goes bare (0.24), then greens again in October (0.53): the cover crop.

Row 2: **Field 334, 2021, GRAIN** (15 clear pictures June–October)

| Week of | Jun 1 | Jun 8 | Jun 15 | Jun 22 | Jun 29 | **Jul 6** | Jul 13 | Jul 20 | Jul 27 | Aug 3 | Aug 10 | Aug 17 | **Aug 24** | **Aug 31** | **Sep 7** | **Sep 14** | **Sep 21** | Sep 28 | Oct 5 | Oct 12 | Oct 19 | Oct 26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Greenness | 0.36 | 0.50 | 0.65 | 0.77 | 0.83 | **0.84** | 0.83 | 0.82 | 0.83 | 0.84 | 0.83 | 0.79 | **0.71** | **0.61** | **0.49** | **0.38** | **0.31** | 0.26 | 0.25 | 0.27 | 0.30 | 0.32 |

- Yellow: week of **Jul 6** (peak 0.84).
- Black box: **Aug 24 – Sep 21**, 5 squares (exact drop: Aug 28 to Sep 24 = **27 days**).
- No green comes back: brown stalks and stubble.

**Optional second pair (same farm, 2023)**, if you want 4 rows:
- **Field 323, 2023, SILAGE.** Peak Aug 3 week (0.89). Box **Aug 31 – Sep 14**: 0.77 → 0.50 → 0.28 (Sep 4 to Sep 14 = **10 days**). Greens again to 0.60 by late October.
- **Field 382, 2023, GRAIN.** Peak Jul 13 week (0.90). Box **Aug 31 – Sep 28**: 0.81 → 0.68 → 0.55 → 0.42 → 0.32 (Sep 6 to Sep 28 = **22 days**).

**Optional Canada pair (for slide 6, shows the same pattern 500 miles north)**, Saint-Hyacinthe, Quebec, 2023, June to early November:
- **Parcel 19737932, SILAGE.** Peak Aug 24 week (0.90). Box **Sep 21 – Sep 28**: 0.75 → 0.51, bare 0.34 by Oct 5 (Sep 24 to Oct 4 = **10 days**).
- **Parcel 19416255, GRAIN.** Peak Jul 13 week (0.89). Box **Sep 21 – Oct 26**: 0.77 → 0.67 → 0.54 → 0.43 → 0.33 → 0.24 (Sep 27 to Oct 27 = **30 days**).

**How the numbers were made:** every clear Sentinel-2 picture of the field (about every 5 days; clouds remove some), cloudy and edge pixels removed, joined into a daily line, smoothed over 15 days, then averaged per week for the squares. The drop length in days comes from the daily line, not the weekly squares.
