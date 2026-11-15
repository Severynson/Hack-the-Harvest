# Farmer forums and crowd signals (group key `forums`)

Research only, checked 2026-11-14. This group builds no field feature and has no `out/` folder, so
`test_models/featureTests/harness.py` skips it. The one runnable piece is `score_state_signal.py`, a test
fixed in advance for a state-level signal, Google Trends search interest included.

## The question

Where do US and Canadian corn and dairy farmers talk online about planting and harvest decisions:
chopping silage or combining grain, abandoning a field, switching after drought or hail? Can any of that
talk serve as a timely, public, aggregate data source for state silage and grain acres before NASS's
January report?

## Short answer

**No forum works as a data source.** Five reasons:

1. **Access.** The large US boards block or charge automated readers. `talk.newagtalk.com` and
   `agweb.com` answered our fetch tool with HTTP 403. The Combine Forum redirects automated agents to a
   paid TollBit gateway. Reddit refused our fetch tool outright, and its free Data API is limited to
   non-commercial use. X has charged for every read since February 2026.
2. **Volume.** The boards that are open are small or dead. Agriville's whole "Crop Production & Forage"
   board holds 6,162 posts. The Ontario OntAg "Crop Talk" board's newest thread is from August 2016.
3. **No location.** At most a poster types a home region into a profile. Nothing ties a post to a
   field or a county.
4. **Bias that drifts.** Who posts changes as platforms rise, age and change their API rules. That is
   the opposite of the "consistent bias" the USDA reps asked for.
5. **The reps ruled it out.** They want "a methodology that does not depend on public sentiment at all"
   (`DOCS/research/usda_reps_qa.md`).

**The crowd sources that do work are official, and the repo already has them.** NASS's weekly "corn
harvested for silage" progress comes from more than 5,000 county reporters (extension and FSA staff),
not from farmers. Our Quick Stats pull has it for 25 states, 2014 to 2026. FSA and RMA intended-use
files are covered in `DOCS/research/gap_fsa_ratio_baseline_2026.md`.

**One cheap, public, aggregate proxy is worth one test: state Google Trends interest in "corn silage"
from August to October.** The test is written down in advance in `score_state_signal.py`. Its result
is **UNCOMPUTED**: an agent may not pull the data automatically (reasons under Results). A person can
download the 20 state files by hand in under an hour.

## Ranked sources (value × feasibility)

**Value (V, 1-5):** information about the change in a state's silage acres that NASS does not already
hold. **Feasibility (F, 1-5):** legal access, cheap enough to use, with history back to 2017.

**How each claim was checked:**

- [o]: we opened the page
- [s]: search-result summary only
- [m]: from memory; not verifiable this session

| # | Source | Access, and terms for automated collection | Coverage, volume | Timely | Location | Silage vs grain | V | F | V×F |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NASS state Crop Progress, "corn harvested for silage" | Official, public, Quick Stats API [o: repo file] | 25 states, weekly, 2014-2026 (Wisconsin by 9 districts) | Weekly | State or district | Yes, explicit | 2 | 5 | 10 |
| 2 | Google Trends: "corn silage", "custom chopping", "silage for sale" | Web export by hand is allowed if credited [s]. robots.txt bars crawlers from `/explore?` [o]. The official API is an alpha you apply for [o]. pytrends uses undocumented endpoints: not used | All states, but low-volume months show as 0 [o] | 2 days | State or metro area | Only through the search term | 2 | 3 | 6 |
| 3 | Pro Farmer Crop Tour; DTN Digital Yield Tour | Public articles | 7 states and about 3,200 fields in Aug 2025 [s]. DTN's tour comes from its own model [s] | August | State or district | No; grain yield only | 1 | 4 | 4 |
| 4 | USDA AMS Direct Hay Reports (market data, not a forum) | Public, MARS API [s]. Whether a key is needed: not checked | A few states (NE, TX, NM, WY, ID, ...). Reports list "hay, straw, and silage" trades [s]. Silage lines not seen | Weekly or every two weeks | State or market | Silage trades, where present | 2 | 2 | 4 |
| 5 | FADQ *État des cultures* and ISQ *maïs fourrager* indicators (Quebec) | Public PDFs [o] | Quebec regions, every two weeks, May-Nov. The 2017 bulletin gives grain-corn harvest % only [o]. ISQ's forage-corn harvest-progress table stopped after 2020 [o] | Every two weeks | Region | Partly | 1 | 3 | 3 |
| 6 | Extension silage dry-down reports (Penn State, UW-Madison counties) | Public pages [o] | Penn State: 12 sampling entries in 5 counties in 2026 [o]. One UW county program: 101 samples in 2025 [s] | Weekly | County | Silage timing only, no acres | 1 | 3 | 3 |
| 7 | Agriville (Farms.com, Western Canada) | Readable without login. robots.txt allows most paths [o] | Crop Production & Forage: 1,166 topics, 6,162 posts in total. Dairy board's last post Apr 2021 [o] | Hours | Profile at most | Rarely | 1 | 3 | 3 |
| 8 | AgWeb Crop Comments | 403 to our fetcher [o]. Farmers email comments, editors curate them [s] | Unknown volume. A 2017 page shows comments tagged by county and state, e.g. silage chopped in Floyd County, Iowa [s] | Days | County and state | Sometimes | 2 | 1 | 2 |
| 9 | New AgTalk (largest US row-crop forum) | www robots.txt allows generic bots with a 20 s crawl delay [o]. The forum host returned 403 [o]. Posts "become the sole property of the site operator" [o] | High volume on markets and crops; silage threads few [m] | Hours | Self-typed region on posts [m] | Sometimes | 2 | 1 | 2 |
| 10 | X / Twitter (#harvest25, #plant25, #silage) | Pay per use since Feb 2026, about $0.005 a read, no free tier [s, third-party] | Moderate in season [m] | Minutes | Rarely geotagged | By text | 2 | 1 | 2 |
| 11 | Reddit (r/farming, r/agriculture, r/Dairy) | Our tool could not fetch reddit.com. Free API (OAuth, 100 queries/min) is for non-commercial use; academic access by application [s] | Silage posts rare [m] | Hours | Almost never | Rarely | 1 | 2 | 2 |
| 12 | YouTube farm channels | Data API key (a Google account) needed. A `search.list` call costs 100 of the default 10,000 daily units [s] | A handful of mostly NY/PA/WI dairy vloggers [s] | Days | Channel's home | In titles ("chopping corn silage 2025") | 1 | 2 | 2 |
| 13 | Custom harvester diaries (HPJ "All Aboard Harvest", USCHI) | Public articles [s] | Few crews, mostly wheat. One 2025 chopper-crew interview covers TX-NE silage, with hail-hit corn in Texas [s] | Weekly | Route | Sometimes | 1 | 2 | 2 |
| 14 | DTN "View From the Cab"; Hoard's Dairyman; Farm Progress | Editorial, public | View From the Cab: 2 farms a season (2025 NE and MS; 2026 MD and MN) [s]. Hoard's: expert articles, no public forum found [s]. Farm Progress "Crop Watch": not found [s] | Weekly | Farm | Sometimes | 1 | 2 | 2 |
| 15 | Quebec: La Terre de chez nous / UPA; Agri-Réseau | Public news and documents | No public farmer forum found [s] | Weekly | Region | Sometimes | 1 | 2 | 2 |
| 16 | Farmers Business Network | Reports are for members; community pages returned 403 [o] | Planting-intentions and acreage surveys give national corn totals, no silage split [s] | Mar-Jun | National | No | 1 | 1 | 1 |
| 17 | The Combine Forum | Automated agents are redirected to `tollbit.thecombineforum.com`, a paid gateway for bots [o] | Machinery talk | Hours | Profile | Rarely | 1 | 1 | 1 |
| 18 | Ontario: OntAg (ontag.farms.com); AgriNewsInteractive | OntAg readable [o]. AgriNewsInteractive returned an empty page [o] | OntAg Crop Talk: newest thread Aug 2016 (dead) [o] | n/a | Province | Rarely | 0 | 1 | 0 |

**What Ontario actually offers is official** [s]:

- OMAFA's Field Crop News 2025 season review: about 243,000 acres of corn silage, and grain corn in dry
  areas that the insurer (Agricorp) released and that was then salvaged as forage.
- Grain Farmers of Ontario's weekly grain-corn harvest progress.

Neither is a forum.

## One test per source against NASS state silage acres, 2017-2024

Every test below uses the same target and metric, fixed in `score_state_signal.py`:

- **Target:** log change in NASS silage acres, year on year.
- **States:** the 20 largest silage states (88.0% of US silage acres, 2017-2024).
- **Metric:** Spearman correlation after removing each year's median.
- **p-value:** from within-year shuffles.
- **Pass:** rho > 0 and p < 0.05. A pass only earns the real test: lowering `kernelag.state_model`'s
  silage error below 13.12%.

| Source | Signal per state-year | Status |
|---|---|---|
| NASS silage progress | `silage_pace` (percent chopped by week 38 against the state's earlier years) | **Computed:** rho -0.085, p 0.45, 82 state-years in 11 states. Fails: harvest timing says nothing about the change in acres |
| Google Trends | Aug-Oct "corn silage" interest against the 3 earlier years (`--trends-dir`) | **UNCOMPUTED:** a person has to export the CSVs (steps below) |
| Pro Farmer tour | Tour yield against the 3-year mean | Not worth running: NASS's August yield forecast is already `yield_shock` in the state model |
| AMS hay reports | Count or price of silage trades, Aug-Oct | UNCOMPUTED. First check which states list silage at all |
| FADQ / ISQ (Quebec) | Regional forage-corn harvest progress | Not a US test. In Quebec it could be compared with StatCan forage-corn area, but the series stopped after 2020 |
| Extension dry-down | Date fields reach 65-70% moisture | Timing only. No mechanism links it to acres; not worth running |
| AgWeb Crop Comments | Share of comments mentioning chop or silage, Aug-Oct | Would need manual reading. Likely fewer than 5 comments per state-year: no statistical power |
| AgTalk, X, Reddit, YouTube | Posts mentioning chop or silage, Aug-Oct, by stated region | Needs the operator's permission (AgTalk) or paid or registered API access. The location fields are too sparse for state counts. Not recommended |

## Results

**Forums.** We collected nothing in bulk. We read about 25 pages by hand: index pages, robots.txt
files, terms pages and one sample thread list. We gathered no posts and no personal data.

**Reference signals**, scored on 2026-11-14 with the fixed scorer (top 20 states, 2017-2024, nothing
tuned). They show what a new signal has to beat:

| Signal (already in `data/panel/state_year.csv`) | n | rho | p | Screen |
|---|---|---|---|---|
| `d_drought`: change in June-Sept share of the state in drought D2 or worse | 160 | 0.191 | 0.016 | pass |
| `d_poor_condition`: change in share of corn rated poor or very poor | 152 | 0.253 | 0.002 | pass |
| `silage_pace`: NASS silage harvest pace | 82 | -0.085 | 0.45 | fail |

The first two pass the screen, yet `kernelag.state_model`'s "stress" set, which includes both, did not
beat `reversion_only`:

| Feature set | Mean state error on silage | US total error |
|---|---|---|
| stress | 13.82% | 3.12% |
| reversion_only | 13.12% | 3.90% |

(Source: `data/models/state_model_metrics.json`.) So passing the screen is not enough. A Trends signal
would need rho clearly above 0.25 and information that drought and crop condition do not already carry.

**The size of the target.** The year-on-year change in a state's silage acres is large and noisy:

- median absolute log change 0.095, mean 0.165, 90th percentile 0.43
- 61 of 160 top-20 state-years moved more than 15% (30 up, 31 down)

**Google Trends: UNCOMPUTED.** Every route open to an agent is closed:

- `trends.google.com/robots.txt` bars crawlers from the Explore pages.
- The official Trends API is an alpha that needs an approved application. When granted, it gives
  values scaled the same way across requests, ISO 3166-2 subregions, and a rolling 1,800 days of
  history (about 5 years: 2021 onward, not back to 2017).
- pytrends calls undocumented endpoints. Using it would not be "used as intended".

## How to run

```bash
# tests and lint
.venv/Scripts/python.exe -m pytest -q test_models/featureTests/forums/test_score_state_signal.py
.venv/Scripts/python.exe -m ruff check test_models/featureTests/forums/

# reference signals from the panel
.venv/Scripts/python.exe test_models/featureTests/forums/score_state_signal.py --signal builtin:d_drought
.venv/Scripts/python.exe test_models/featureTests/forums/score_state_signal.py --signal builtin:silage_pace

# any CSV with state, year, signal
.venv/Scripts/python.exe test_models/featureTests/forums/score_state_signal.py --signal my_signal.csv
```

**Google Trends test, done by hand by a person, never scripted:**

1. Open trends.google.com. Search term: `corn silage` (the search term, not the topic). Category: All.
   Web search. Region: United States > the state. Custom time range: 2014-01-01 to 2024-12-31. Over
   11 years Google returns monthly values.
2. Export "Interest over time" to CSV. Save it as `<State name>.csv` (for example `Wisconsin.csv`), all
   20 files in one folder. The 20 states are printed by `load_target()`: Wisconsin, New York,
   South Dakota, Minnesota, California, Pennsylvania, Michigan, Iowa, Kansas, Nebraska, Texas, Idaho,
   North Dakota, Colorado, Ohio, Illinois, Virginia, Indiana, Missouri, Washington.
3. Download each state once, all on the same day, and record the date. Trends adds random noise, so
   values shift a little between downloads.
4. Run `score_state_signal.py --trends-dir <folder> --out trends_result.json`. The primary term is
   fixed as `corn silage`. If you also try "custom chopping" or "silage for sale", label them
   exploratory and divide 0.05 by the number of terms.
5. Credit the data as "Data source: Google Trends (https://www.google.com/trends)", as Google asks.

## Would a forum signal get past the USDA reps' objection?

The reps made two objections to farmer validation (`DOCS/research/usda_reps_qa.md`):

1. Asking farmers gets few answers, and farmers "do not adopt what requires more work".
2. They want "a methodology that does not depend on public sentiment at all".

**Passive forum mining avoids the first objection:** nobody is asked to do anything. **It fails the
second outright:** forum posts are public sentiment, from a self-selected few.

- **Its bias cannot stay consistent.** Who posts on AgTalk, Reddit or X changes from year to year
  for reasons unrelated to corn: platforms age, APIs get priced, moderation changes. A signal with a
  consistent bias was the one thing the reps said they would value.
- **Google Trends is better, but not clean.** It measures what people search for, not what they say.
  But it is still a public-behaviour signal, and its bias shifts too: Google changed how it collects
  Trends data on 1 January 2022, which falls inside our backtest years. Removing each year's median
  cancels that change only if it hit every state in the same proportion.
- **NASS's county reporters are trained observers, not forum posters.** But NASS already uses their
  numbers, and their silage pace carried no acreage information in our screen.

At most, a forum read is colour for the presentation: why farmers chop drought-hit corn, and how crop
insurance shapes that choice. Two sources:

- UW-Madison's "Insurance and Silage" note: corn insured as grain can be chopped for silage and still
  collect an indemnity.
- Missouri Extension: get the insurer's approval before cutting.

That colour is not a model input.

## Recommendation

1. **Do not build a forum scraper.** The terms, the volume, the missing location and the reps'
   objection each rule it out alone.
2. **If someone wants one more cheap test:** a person downloads the 20 Google Trends files by hand and
   runs the fixed scorer. Expect little: search volume for "corn silage" is likely too low outside the
   big dairy states. van der Velde et al. (2012) found state search volume adequate for corn planting
   but too thin for wheat and soybeans. Count the signal only if it passes the screen and then lowers
   the state model's backtest error.
3. **Better use of the same hour:** official semi-structured data that measures acres, not mood:
   - RMA insured corn by type, grain or silage (decision 7 in `DOCS/research/README.md`)
   - FSA intended-use acres
   - after checking which states carry silage lines, AMS Direct Hay Report silage trades as a demand
     signal

## Limitations

- Several pages could not be opened: AgTalk's forum host, AgWeb, Reddit, the FBN community, and X
  search, which needs a login. Their rows rest on robots.txt files, terms pages, search summaries and
  memory, and are marked [s] or [m] in the table.
- Prices for X and YouTube come from third-party pages, not from the official pricing pages.
- The Ontario 2025 silage figures come from a search summary; the review itself was not opened.
- The reference-signal correlations are a screen, not a forecast test. They use the panel as built
  (`kernelag.state_panel` defaults) and never read 2025 or any Maryland data.

## Sources (opened 2026-11-14 unless marked [s])

- AgTalk:
  - robots.txt: https://www.newagtalk.com/robots.txt and https://talk.newagtalk.com/robots.txt
  - posting policy: https://www.newagtalk.com/NAT_Posting_Policy.html
  - forum index (403): https://talk.newagtalk.com/forums/
- AgWeb (403): https://www.agweb.com/news/crops/corn/17-states-17-harvest-reports ;
  [s] https://www.agweb.com/opinion/september-crop-comments-2017
- The Combine Forum (307 to TollBit): https://www.thecombineforum.com/ ;
  https://tollbit.thecombineforum.com/robots.txt
- Agriville: https://www.agriville.com/forum ; https://www.agriville.com/robots.txt
- OntAg: https://ontag.farms.com/forum/categories/crop-talk/listForCategory
- Reddit API terms (2023) [s]: https://www.reddit.com/r/modnews/comments/13wshdp/
- X pay-per-use [s]: https://opentermsarchive.org/en/memos/x-replaces-its-dollar200-entry-level-api-plan-with-a-pay-per-use-model/
- YouTube quota [s]: https://developers.google.com/youtube/v3/determine_quota_cost
- Google Trends:
  - API alpha: https://developers.google.com/search/blog/2025/07/trends-api
  - how the data works: https://support.google.com/trends/answer/4365533
  - credit when reusing [s]: https://support.google.com/trends/answer/4365538
  - robots.txt: https://trends.google.com/robots.txt
  - 2022 collection change [s]: https://link.springer.com/article/10.1007/s44248-024-00013-3
  - van der Velde et al. 2012, *Environmental Research Letters*:
    https://physicsworld.com/a/web-behaviour-could-track-corn-planting-dates/
- NASS Crop Progress:
  - metadata ("non-probability surveys", "more than 5,000 reporters"):
    https://www.nass.usda.gov/Charts_and_Maps/Crop_Progress_&_Condition/Metadata/
  - Wisconsin report, 29 Sep 2025 (statewide narrative and district table, no county comments):
    https://www.wispolitics.com/wp-content/uploads/2025/09/WI-Crop-Progress-09-29-25.pdf
  - repo file: `data/Quickstats Data/corn_silage_harvest_progress_weekly_state_2000_2026.csv`
- Quebec:
  - FADQ bulletin no. 12 (31 Oct 2017): https://www.fadq.qc.ca/fileadmin/fr/bulletins/etat-culture-2017-no-12.pdf
  - ISQ forage-corn table:
    https://statistique.quebec.ca/fr/produit/tableau/mais-fourrager-indicateurs-sur-letat-des-cultures-au-quebec-au-cours-de-la-saison-241120
- Penn State dry-down: https://extension.psu.edu/corn-silage-dry-down-week-of-august-31-2026 ;
  UW county program [s]: https://marinette.extension.wisc.edu/2025/09/02/corn-silage-moisture-monitoring-for-2025
- Pro Farmer [s]: https://www.profarmer.com/about-pro-farmer-crop-tour ;
  DTN [s]: https://www.dtnpf.com/agriculture/web/ag/crops/article/2025/08/08/dtn-digital-yield-tour-forecasts-11 ,
  https://www.dtnpf.com/agriculture/web/ag/news/article/2026/04/12/season-kicks-new-views-cab-2
- FBN [s]: https://www.fbn.com/direct/resources/planting-intentions-report
- HPJ harvester interview [s]: https://hpj.com/?p=170134
- AMS Direct Hay Report, Texas [s]: https://mymarketnews.ams.usda.gov/viewReport/2707
- Ontario 2025 season review [s]: https://fieldcropnews.com/?p=29734
- Insurance and silage:
  - UW-Madison [s]: https://aae.wisc.edu/pdmitchell/wp-content/uploads/sites/15/2019/09/Insurance_and_Silage.pdf
  - Missouri Extension [s]: https://extension.missouri.edu/news/check-with-your-crop-insurance-agent-before-you-cut
