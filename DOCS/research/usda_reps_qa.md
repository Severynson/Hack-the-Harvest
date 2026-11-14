# USDA rep Q&A: what the organizers actually want

Recorded 2026-11-14 at Aggie Square by cc-daniel, from two transcribed audio sessions (about 20 minutes each) in which USDA NASS representatives answered team questions. The transcripts are in `DOCS/transcripts/` (`Aggie_Square_2_eng.pdf`, 20 pages; `Voice_261114_132252_eng.pdf`, 17 pages). They name people, so do not quote names in anything public. Quotes are verbatim apart from removed filler words; everything else is paraphrase. The transcription is automatic, so check any number against a second source before it goes on a slide.

This note overrides the topic files wherever they assume the organizers supplied labeled fields.

## What the reps said

**The deliverable**

- "I just need effectively two numbers, for the United States and for each state": acres of corn for grain and acres of corn for silage.
- NASS publishes those numbers in January. The team's value is having them sooner: "the earlier the better". 15 December is useful; 15 November is "two months ahead of time".
- It is a forecast, and it has to come from in-season imagery: by December harvested fields "may look the same".
- Measures of dispersion, confidence intervals and likelihood scenarios are "bonus".
- "Explain why you can get them or why you can't. That's going to be an important component."

**How it is judged**

- No field-level truth was given: "we didn't actually give you field level true false. We only gave you that for like a state." The questions are "can you get to this number" and "how confident are you".
- Both mistakes cost the same: calling grain silage and missing silage each move acres that "need to be there".
- The bar for justification: "would you bet 100 million dollars on your answer?"
- It should generalize "so I can apply it other years", and across regions: "as long as you don't over-calibrate your methodology, it should work out over here".

**NASS's own accuracy**

- Forecast against final is "usually less than 3%, sometimes somewhere between 1.8 and 2.5%". Last year it was "more than 4%" and "markets went wild". The reps did not say which published figure these percentages refer to.

**Why a less accurate signal is still wanted**

- NASS sets its estimate from about six indications, each with its own error. The ones named were survey, remote sensing, import and export records, a secondary survey, models, and FSA and RMA administrative data.
- "If you give me one more signal that is consistent, has a consistent bias or consistent accuracy, that might be as useful as any of these other six that I'm using. It may be more useful if it's based on data that I'm not yet using."
- NASS uses NDVI as a proxy for yield and does not typically use satellite data for acreage.

**How NASS works today**

- A June survey asks farmers whether their corn is for grain or silage, with follow-ups in August, October and November. There are two samples: a list frame (farmers drawn from a register) and an area frame (fields drawn geographically, visited, then confirmed with the farmer).
- NASS sees a running total of failed acres from FSA and RMA. The running total is not public, but both agencies publish abandoned acres periodically.
- History is on Quick Stats (API).

**Traps the reps expect teams to fall into**

- Looking only at the satellite signal and ignoring prices, policy and weather.
- One harvest calendar for every region: Texas harvests in early August, Nebraska in October, and the water regime matters.
- Bare soil after harvest looks different by region (dark in Maryland or Virginia, light and sandy in Arizona; soil texture changes the spectral fingerprint), so a method tuned in one place has to be checked in another.
- Cloud cover, which they expect teams to handle with overlapping imagery and several indices.
- Trying to account for everything: the variables overlap, so look for the strongest signals.

**Data they pointed to**

- RMA and FSA abandoned acres, which "not everybody's going to look into"; weather and insurance information as proxies for abandonment.
- Dairy context, kept simple: distance to dairy, number of dairies in a county or state, average dairy size. Dairies usually buy silage from farms within a radius, because silage is too heavy to haul far.
- A grower who cannot harvest grain in a bad year may sell the crop as silage to a dairy within reach.

**Farmer validation**

- The reps were sceptical of any loop that asks farmers to confirm results: response is low, and farmers "do not adopt what requires more work". What they want is "a methodology that does not depend on public sentiment at all".
- NASS field analysts already do field surveys; one rep suggested those could feed model improvement over time.

## Transcription caveats

- Haul radius: one transcript has the rep answering "120 miles". The same answer says silage is too heavy to haul, and gives 30 to 50 miles as the range where distance stopped mattering in the rep's ethanol-plant thesis. Treat 120 as a transcription error and use the cited haul limits in `gap_dairy_feedlot_points.md`.
- At one point the rep says the team is working "on the yield side". The rest of both sessions makes clear the task is acreage.

## What this changes (cc-daniel's reading, not the reps' words)

1. The target is state and US acreage error against NASS totals. The field classifier is a means; decision 4 in `README.md` (prior-corrected shares, a ratio estimate on planted acres, never sum labels) becomes the centre of the build.
2. The open question in `README.md` is closed: there are no organizer-labeled fields. Field-level precision, recall and false positive rate can only be measured on proxy labels (Quebec BDPPAD, the California permit polygons); quote them as such.
3. The hackathon rubric's Technical Quality line lists precision, recall, false positive rate and response time. That conflicts with "no field-level truth" and is unresolved. Lead with acreage error and intervals; show field-level metrics on proxy labels as support.
4. Evaluate by backtest over several years, holding out whole state-years, and show that the bias is stable. Compare with "same as last year".
5. Silage is the hard number nationally: a 15% miss on 6.187M silage acres is 0.93M acres, about 1% of the 90.948M grain acres (revised 2025 figures). In states where most corn is silage, such as California, grain is the small, hard number.
6. Add signals beyond imagery: abandoned acres, weather and drought, prices, the dairy prior.
7. Prefer within-field change and growing-degree-day timing over absolute thresholds. Both named traps (soil colour, regional calendars) break absolute thresholds.
8. Costs are symmetric, so tune for unbiased totals, not for precision.
9. Drop any farmer-confirmation feature from the product.
