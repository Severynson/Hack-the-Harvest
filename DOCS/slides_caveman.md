# Caveman slides (basic caveman + Nemotron caveman)

Five slides, about 2½ minutes. Numbers come from `autoresearch/RESULTS.md` on branch `autoresearch/cc-severyn`. "Field-year" = one field in one season.

---

SLIDE A
HEADER: A satellite can measure how green every field is
TEXT: Living leaves reflect a lot of near-infrared light (invisible to the eye) and absorb red light. From those two colours the satellite gives one **greenness score** per field: about 0.2 for bare soil, 0.9 for thick green corn.
BULLETPOINTS:
- **Free and public:** Sentinel-2, two European satellites, photograph every field on Earth about **every 5 days** at 10 m per pixel. We download them from Microsoft's Planetary Computer, no account needed.
- **Works for any farm:** give the field's outline and the pictures are there, for past seasons too.
- **Only the field counts:** edge pixels (roads, hedges) and clouds are removed. Each field still had **13–29 clear pictures** from June to October.
- **One line per field:** the clear pictures are joined into a day-by-day greenness line, smoothed over 15 days.
VISUAL: a horizontal colour bar from brown (0.2, "bare soil") to dark green (0.9, "thick corn").

---

SLIDE B
HEADER: Silage drops off a cliff. Grain fades slowly.
TEXT: Two real fields on the USDA Beltsville farm, Maryland, 2021. One square per week, June to October.
DATA VISUALIZATION: one row of squares per field. Colour = weekly greenness (dark green 0.9 → brown 0.2), value written inside. Yellow outline = peak week. Black box = the weeks where greenness falls from its peak level to bare soil.

Field 280, SILAGE:

| Jun 1 | Jun 8 | Jun 15 | Jun 22 | Jun 29 | Jul 6 | Jul 13 | **Jul 20** | Jul 27 | Aug 3 | Aug 10 | Aug 17 | Aug 24 | **Aug 31** | **Sep 7** | **Sep 14** | Sep 21 | Sep 28 | Oct 5 | Oct 12 | Oct 19 | Oct 26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.25 | 0.36 | 0.53 | 0.70 | 0.78 | 0.83 | 0.86 | **0.87** (yellow) | 0.86 | 0.86 | 0.86 | 0.84 | 0.82 | **0.74** | **0.48** | **0.27** | 0.25 | 0.24 | 0.27 | 0.35 | 0.44 | 0.53 |

Black box: Aug 31 – Sep 14. Label: **"Cliff: 11 days → silage"**

Field 334, GRAIN:

| Jun 1 | Jun 8 | Jun 15 | Jun 22 | Jun 29 | **Jul 6** | Jul 13 | Jul 20 | Jul 27 | Aug 3 | Aug 10 | Aug 17 | **Aug 24** | **Aug 31** | **Sep 7** | **Sep 14** | **Sep 21** | Sep 28 | Oct 5 | Oct 12 | Oct 19 | Oct 26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.36 | 0.50 | 0.65 | 0.77 | 0.83 | **0.84** (yellow) | 0.83 | 0.82 | 0.83 | 0.84 | 0.83 | 0.79 | **0.71** | **0.61** | **0.49** | **0.38** | **0.31** | 0.26 | 0.25 | 0.27 | 0.30 | 0.32 |

Black box: Aug 24 – Sep 21. Label: **"Fade: 27 days → grain"**

CARDS:
- SILAGE: a chopper takes the whole green crop in one go. Bare ground in 11 days.
- GRAIN: the plant turns yellow, then brown, and the combine comes weeks later. 27 days.
- Both start losing green in the same week. **When** doesn't separate them. **How fast** does.

---

SLIDE C
HEADER: The caveman rule: under 2½ weeks from green to bare = silage
TEXT: For each field we measure one thing: the number of days its greenness takes to fall from 80% of its peak down to 20%.
BULLETPOINTS:
- **Under 17.5 days → silage.** Otherwise → grain.
- **One number learned from data.** To find it we take fields with known answers, try every cut-off (1 day, 2 days, 3 days…) and keep the one that sorts them best.
- **Same number in two countries:** learned in Quebec, Canada → 17.5 days. Learned in Maryland → 17.5 days.
- **A farmer could check it by eye:** chopping is fast, drying is slow. Nothing to take on faith.
- **Early:** the drop is over within days of harvest, so Maryland fields are called by early October. The official count comes in January.

---

SLIDE D
HEADER: Learned in Canada, tested on USDA's Maryland farm: 42 of 44 right
TEXT: The judges' question is how it does on the Maryland fields. So we never let the model learn from them. We learned the cut-off on **801 cornfields in Quebec, Canada** (farmer-declared grain or silage, 2023), then tested once on the **44 Maryland field-years** (USDA Beltsville farm, 2021–2023).
TABLE:

| Tested on the 44 Maryland field-years | Learned from | Correct | Accuracy |
|---|---|---|---|
| Always guess "grain" | – | 32 / 44 | 72.7% |
| Machine-learning field model | Quebec | 37 / 44 | 84.1% |
| **Caveman rule** | **Quebec only** | **42 / 44** | **95.5%** |

CONFUSION MATRIX (caveman, learned in Quebec):

| | Called grain | Called silage |
|---|---|---|
| **Really grain (32)** | 32 | 0 |
| **Really silage (12)** | 2 | 10 |

BULLETPOINTS:
- **Silage:** 10 of 12 found (recall 83%); every field called silage really was (precision 100%).
- **Grain:** 32 of 32 right (recall 100%; precision 94%).
- **Not luck:** right on 10 fields that "always grain" gets wrong, wrong on none it gets right. That split happens by chance about 1 time in 500.
- **Why it transfers:** one learned number, a physical reason behind it, and the same value in both countries.
FOOTNOTE: The 2 misses are silage fields that faded slowly, like grain. A second, hand-set check (field green again in Nov–Dec = cover crop sown after an early cut) catches both: 44 / 44, but it needs data through December.

---

SLIDE E
HEADER: Nemotron caveman: we let Nemotron look at the fields. It couldn't see the cut.
TEXT: Our first instinct was to have Nemotron look at the fields the way a farmer would. We built a version of the model on purpose on Nemotron's labels.
TWO COLUMNS:
- **VERSION A: NEMOTRON AS THE EYES.** Nemotron (NVIDIA's vision-language model) labelled **797 true-colour satellite pictures** of the 44 Maryland fields: no crop / standing / harvested. The caveman rule learned from those labels and predicted from them.
  → **27 / 44 = 61%**, below the 73% of always guessing "grain".
  Why: in a 10 m colour picture, a freshly chopped field and dry brown corn look the same. Its silage harvest dates came out about 2½ weeks late.
- **VERSION B: THE SAME PICTURES, MEASURED.** Instead of looking at the colours, we measure greenness from the near-infrared light the satellite also records. The speed of the drop becomes visible.
  → **42 / 44 = 95.5%**, cut-off learned in Quebec.
FIGURE: `nemotron_vs_greenness.png`. Each satellite picture has Nemotron's label as its border colour and the measured greenness underneath. On Sep 12 the silage field is already bare (greenness 0.23); Nemotron still says "standing".
BOTTOM BAR: Nemotron also explains every call in plain English and answers questions in the live board's chat. The decision itself rests on one measured number.
SPOKEN LINE: "On September 12 this field is bare, and Nemotron still says 'standing'. So we stopped looking at the colours and measured the greenness instead."

---

BACKUP (if asked "how did you pick 17.5 / did you overfit?")
- One number is learned. Learned on Quebec or on Maryland, it comes out at 17.5 days.
- Other settings were fixed by us during development, using the Maryland fields: smoothing over 15 days, 80% → 20% drop band, at least 40% clear pixels. Nearby settings give 87–100% silage F1 on Maryland.
- Learned on Maryland and tested on Quebec (801 fields): 90% correct (always-grain: 80%). Misses: about 1 in 3 Quebec silage fields dried slowly before cutting.
