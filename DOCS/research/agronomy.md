# Agronomy ground truth: regional calendars, dry-down physics and the confusers

Team Kernel, Hack the Harvest. Research note written Saturday 2026-11-14.
Scope: what agronomy says the satellite should see for each corn harvest fate, with sources.

Evidence tags used throughout:

- **[O]** source opened and read in this session (page text or PDF text extracted locally).
- **[S]** seen only as a search-result summary; the page itself was **not opened** (reason given). Treat as low confidence.
- **Inference:** my own reasoning from the sources, not something a source states.

---

## 0. Bottom line (read this first)

1. **The silage/grain difference is a thermal gap, not a calendar gap.** Silage is cut at half milk line, about 42-47 days after silking and roughly 200 GDD *before* black layer. Dry grain is cut roughly 150 GDD (to 25% kernel moisture) to 375 GDD (to 20%) *after* black layer. The two fates are therefore about 350-575 GDD apart for the same field. In calendar days that is 17-24 days in warm states (KY, TN, NC, VA, MD), 33-40 days in WI/MN/MI/NY/PA/ID, and 46-56 days in MT/WY/OR.
2. **Calendar date alone fails in three named places.** (a) The South: Texas grain was 68% harvested on 6 Sep 2025, before Wisconsin silage harvest normally begins (8 Sep). (b) Kansas: grain was 19% harvested by 20 Sep 2025 and 40% by 20 Sep 2026, inside the silage window. (c) California: Sacramento Valley grain corn is combined in September at under 14% moisture while double-cropped silage is chopped September-October.
3. **NASS counts everything that is not whole-plant silage or seed as grain.** High-moisture corn, earlage and snaplage are "grain" for NASS purposes but are cut 2-4 weeks before dry grain. Only the residue left on the ground separates them from silage.
4. **The switchers are the business case.** NASS's June 2022 forecast of grain acres (81.94M) ended 3.2M acres too high (78.7M final); Kansas silage acres went 240K to 420K and Nebraska 260K to 430K in one year. In 2025 the switch went the other way. A September field-level fate monitor sees this months before the January summary.
5. **Drought- and frost-salvage silage is brown at the chop.** "Green at cut" alone will misclassify exactly the fields that switched. Add a moisture index and keep timing and residue as independent evidence.
6. **New public data source for validation:** NASS state weekly Crop Progress reports publish "corn harvested for silage, percent" (Wisconsin by nine districts; Idaho, Oregon, Washington statewide). Wisconsin was 66% chopped on 28 Sep 2025, with districts ranging from 28% to 93%.
7. **Post-harvest behavior is a signal of its own.** NASS Wisconsin, 29 Sep 2025: "Cover crops were planted into the harvested silage fields and manure application was ongoing." In California the silage field is replanted to winter cereal forage from mid-October to early December.
8. **Last year's state silage acres are a good prior only in dairy states.** Year-to-year moves 2023-2025: WI -6%/+21%, CA +9%/-4%, but TX -43%/+66%, IA -11%/-26%, KS -6%/-26%, ND +30%/-35%.

---

## 1. How this was done, and what is not verified

- 24 web searches were run before the shared search budget for this workflow run was exhausted; the rest of the work was done by opening known primary URLs directly (about 60 page or PDF opens). PDFs that the fetcher could not parse were saved locally and their text extracted with the built-in macOS PDF library, so quotes from PDFs below are from the actual document text.
- **Not verified in this session (search budget ran out):** seed corn, popcorn and processing sweet corn harvest calendars; the share of grain fields with stover baling, stalk grazing or fall tillage; a numeric percent residue cover after silage; an explicit irrigation cut-off rule (days before chopping) for California silage; whether published NASS "harvested for grain" acres include seed corn. These are flagged where they appear.
- Three NASS pages returned HTTP 404 and are cited only as [S]: "Corn Acreage Inclusions", the 2022 Census of Agriculture Appendix B, and the Nebraska weekly report of September 2012.

---

## 2. The physiological clock (a)

### 2.1 Stage table

| Stage | Days after silking | Thermal time | Kernel moisture | Whole-plant moisture | Source |
|---|---|---|---|---|---|
| R1 silking | 0 | - | - | - | Nielsen 2021 [O] |
| R2 blister | about 10-12 | 960 GDD to maturity | about 85% | - | Nielsen 2021 [O] |
| R3 milk | about 18-20 | 880 GDD to maturity | about 80% | - | Nielsen 2021 [O] |
| R4 dough | about 24-26 | 670 GDD to maturity | about 70% | - | Nielsen 2021 [O] |
| R5 dent | about 31-33 (Nielsen); 35-42 (Lauer) | 337-360 GDD from full dent to black layer | about 60% | about 73% at early dent | Nielsen 2021; Lauer 2000; Penn State [O] |
| R5.5 half milk line = normal start of silage harvest | 42-47 (Lauer; UW L031); "45 days or 800 growing degree days" for fully irrigated full-season corn (UNL) | about 200 GDD before maturity | not stated | about 66% (target 65-70%) | Lauer 2000; UNL 2023; Nielsen 2021; Penn State [O] |
| R5.75 three-quarter milk line | - | - | - | about 63% | Penn State (UW 1993 table) [O] |
| R6 black layer | 55-60 (Lauer); about 55-65 (Nielsen) | 0 | about 30%, range 25-40% (Nielsen); 32-36% (Idaho BUL 956) | about 60% ("no milkline") | Nielsen 2021; Lauer 2000; Idaho BUL 956; Penn State [O] |
| High-moisture corn harvest | black layer + 0 to 2 weeks; "2 to 3 weeks earlier" than dry grain | - | 24-33%, usually 28-32% | - | UW L062 [O] |
| Dry grain harvest | black layer + 2 to 8+ weeks | about +150 GDD to reach 25%, about +375 GDD to reach 20% | 25% or less recommended (Ohio State); under 22% (Idaho); under 14% (California Sacramento Valley; most of Texas outside the Plains) | - | OSU 2024; Idaho BUL 956; UC 2015; TX profile [O] |

Key source statements:

- Lauer (UW, 24 Aug 2000) [O]: "the predicted start date of silage harvest (half-milkline) occurs 42-47 days after silking"; half milk line is about 13 days before black layer (citing Wiersma et al., 1993); "Silage moisture decreases at an average rate of 0.5% per day during September"; measured county rates 0.4 to 1.0 percentage points per day (1996-1999).
- Penn State (Roth and Heinrichs) [O]: whole-plant target moisture 65-70% horizontal silos, 63-68% conventional tower, 55-60% limited-oxygen, 65% bags; drydown "0.50 to 0.75 percentage units per day"; "Moisture content cannot be determined accurately using the kernel milkline"; silage hybrids "up to 10 days longer than a full-season grain hybrid".
- UW L031 [O]: "Silking date: add 42 to 47 days"; silage hybrids "Relative maturity: 5-10 days later than grain hybrids".
- Iowa State (Barnhart and Elmore, 2008) [O]: start chopping when the most advanced fields reach one-half milk line, finish between one-half milk line and maturity; whole-plant moisture then about 65-70%.
- Nielsen 2021 [O]: plant death at full dent costs about 40% of grain yield, at half milk line about 12% (Carter and Hesterman 1990). So a field chopped at half milk line was *not* a failed grain crop; it was chopped on purpose.

### 2.2 Field dry-down of grain

| Condition | Rate (percentage points of kernel moisture per day) | Source |
|---|---|---|
| Grain maturing in late August | about 0.8 | Nielsen 2018 [O] |
| Grain maturing in mid to late September | about 0.4 | Nielsen 2018 [O] |
| Warm, sunny, windy, dry | more than 1.0 | Nielsen 2018 [O] |
| Cool, cloudy, rainy | can be zero | Nielsen 2018 [O] |
| Mid to late September, favorable | 0.75 to 1.0 | OSU 2024-35 [O] |
| Early to mid October | 0.5 to 0.75 | OSU 2024-35 [O] |
| Late October to early November | 0.25 to 0.5 | OSU 2024-35 [O] |
| Mid November | 0 to 0.25 | OSU 2024-35 [O] |
| Ohio research, warm and dry fall | 0.76 to 0.92; 24-29 GDD per point | OSU 2024-35 [O] |
| Ohio research, cool and wet fall | 0.32 to 0.35; 20-22 GDD per point | OSU 2024-35 [O] |
| Thermal rule, 30% down to 25% | about 30 GDD per point | OSU 2024-35 [O] |
| Thermal rule, 25% down to 20% | about 45 GDD per point | OSU 2024-35 [O] |

Other statements: drying is roughly linear from about 40% down to 15-20% and then tapers (Nielsen 2018 [O]); hybrids one relative-maturity day apart differ by about half a point of moisture on the same date (Nielsen 2018 [O]); below about 20% in the field, losses from lodging and ear drop rise (OSU [O]).

### 2.3 GDD formula

Standard corn growing degree days, base 50 F with an 86 F cap:

```
GDD_day (F) = ( min(Tmax, 86) + max(Tmin, 50) ) / 2 - 50
GDD_day (C) = ( min(Tmax, 30) + max(Tmin, 10) ) / 2 - 10        (1 GDD C = 1.8 GDD F)
```

The Ohio State article's own example ("about 5 GDDs per day (assuming Tmax = 60F, Tmin = 50F)") is consistent with this formula [O]. All GDD figures in this note are Fahrenheit GDD.

### 2.4 The thermal gap between the two fates

Inference (built from the numbers above):

- Silage cut: half milk line, about 200 GDD **before** black layer (Nielsen).
- Grain cut at 25%: black layer at about 30% plus 5 points x 30 GDD = about 150 GDD **after** black layer.
- Grain cut at 20%: a further 5 points x 45 GDD = about 375 GDD after black layer.
- Thermal gap between silage and grain on the same field: **about 350 GDD (grain at 25%) to about 575 GDD (grain at 20%)**; more where grain is field-dried to under 14-15%.
- In calendar days this stretches with the season: at 20-25 GDD per day (August in Texas or Kansas) 350-575 GDD is 2-4 weeks; at 5-10 GDD per day (October in Wisconsin or New York) it is 5-8+ weeks. This matches the handbook gaps in section 2.5.
- Two real-world effects compress the gap: silage hybrids are 5-10 relative-maturity days later than grain hybrids (UW, Penn State), and silage is often planted later (after winter forage, first-cut hay or manure hauling). One effect widens it: grain in dairy regions may be combined early as high-moisture corn.

### 2.5 Gap between silage and grain harvest by region

Gap = midpoint of the "most active" grain window minus midpoint of the "most active" silage window in the NASS handbook (section 3), computed by me. "Overlap" = days between the grain "begin" date and the silage "end" date (positive means the two harvests overlap on the calendar).

| State | Silage midpoint | Grain midpoint | Gap (days) | Overlap (days) |
|---|---|---|---|---|
| Wisconsin | 28 Sep | 31 Oct | 33 | 17 |
| Minnesota | 19 Sep | 23 Oct | 34 | 17 |
| Michigan | 23 Sep | 2 Nov | 40 | 45 |
| New York | 20 Sep | 29 Oct | 39 | 8 |
| Pennsylvania | 25 Sep | 2 Nov | 38 | 41 |
| Idaho | 25 Sep | 30 Oct | 35 | 28 |
| South Dakota | 19 Sep | 26 Oct | 37 | 20 |
| North Dakota | 20 Sep | 29 Oct | 39 | 16 |
| Iowa | 7 Sep | 22 Oct | 45 | 4 |
| Ohio | 18 Sep | 31 Oct | 43 | 17 |
| Colorado | 17 Sep | 26 Oct | 39 | 9 |
| California | 23 Sep | 16 Oct | 23 | 91 |
| Texas | 12 Aug | 5 Sep | 24 | 75 |
| New Mexico | 20 Sep | 15 Oct | 25 | 37 |
| Arizona | 16 Oct | 16 Oct | 0 | 91 |
| Kentucky / Tennessee / North Carolina | 12 Sep / 30 Aug / 4 Sep | 1 Oct / 20 Sep / 25 Sep | 19 / 21 / 21 | 39 / 37 / 56 |
| Montana / Wyoming / Oregon | 18 Sep / 20 Sep / 15 Sep | 13 Nov / 5 Nov / 4 Nov | 56 / 46 / 50 | 6 / 6 / -10 |
| Kansas, Nebraska | no silage row in the handbook | 2 Oct / 22 Oct | - | - |

Region notes:

- **Wisconsin, Minnesota, Michigan, New York, Pennsylvania:** gap 33-40 days; silage most active roughly 4 Sep to 13 Oct; grain most active 8 Oct to 25 Nov. Calendar overlap is real (8-45 days), so a field cut on 10 October can be either.
- **Idaho:** silage "from the end of August to mid-October"; earlage "a few weeks to a month after silage corn"; high-moisture corn "from the end of September in the southwest part of the state to the end of October in the south-central section"; dry grain "from late October to as late as the next calendar year", and "In some years it may take until March" (Idaho BUL 956 [O]). Only "Approximately 25% is grown for either high moisture corn or dry grain" of about 300,000 acres.
- **California Central Valley:** see section 5. Single-crop silage planted by early April is chopped in August; grain corn planted late March-April is combined in September at under 14% moisture; double-crop silage planted late May is chopped in September-October. Same-planting-date gap is roughly 4-6 weeks (Inference from two UC cost studies), but silage and grain calendars overlap almost completely because silage is planted later.
- **Texas High Plains:** grain "early September and mid October in the Plains and Cross Timbers", harvested below 25-30% as wet grain or below 20% for farm storage; "Silage is cut when the grain is at about the 50% milk-line maturity stage then delivered to a feed-lot" (Texas crop profile 2003 [O]). Inference: silage mid-August to mid-September, gap about 3-5 weeks.
- **South Texas:** grain "between late June and mid July" in the Lower Valley, South Texas and the Winter Garden; "late June and mid August in the Upper Coast and the Coastal Bend"; harvested "below 14% moisture" (Texas crop profile [O]). Very little silage.
- **Kansas, Nebraska:** the handbook has no silage row. UNL (2023) [O]: silage harvest for fully irrigated full-season corn usually begins "45 days or 800 growing degree days (GDDs) after the tassel/silking growth stage"; drought and heat speed maturity, so the article recommends the kernel milk line and accumulated GDD over the calendar, "especially for drought-impacted corn". Inference: Nebraska silage is most active late August to late September, 4-6 weeks before grain (most active 4 Oct-10 Nov); Kansas grain (most active 10 Sep-25 Oct) overlaps the silage window almost entirely.

---

## 3. NASS "Usual Planting and Harvesting Dates" (b)

Source: USDA NASS, *Field Crops: Usual Planting and Harvesting Dates*, October 2010 release (text file) [O]. https://esmis.nal.usda.gov/sites/default/release-files/vm40xr56k/dv13zw65p/z603r1055/planting-10-29-2010.txt

- Definitions [O]: "Beginning dates indicate when planting or harvesting is about 5 percent complete" and "ending dates when operations are about 95 percent complete"; "The "most active" range indicates when between 15 and 85 percent of the crop is planted or harvested." Dates are "based on 20 years of historical crop progress estimates" plus "the knowledge of industry specialists".
- The ESMIS catalogue lists only two releases, 5 Dec 1997 and 29 Oct 2010, so **2010 is the latest edition** [O]. The 2010 text file does not print a handbook number; the 1997 edition is catalogued as Agricultural Handbook Number 628 [S: search summary of the catalogue record].
- There is **no national corn-for-silage table**; silage appears only in the state tables. **Kansas, Nebraska, Illinois, Missouri, Georgia, Oklahoma, Louisiana and South Carolina have no corn-for-silage row.**

### 3.1 Corn for silage (top silage states plus CA and TX)

Format: begin / most active / end. Acres are 2009 harvested, thousand acres.

| State | 2009 acres | Planting | Harvest |
|---|---|---|---|
| Wisconsin | 850 | Apr 26 / May 2 - May 27 / Jun 4 | Sep 8 / Sep 13 - Oct 13 / Oct 19 |
| New York | 470 | Apr 20 / May 4 - Jun 13 / Jun 20 | Sep 5 / Sep 10 - Oct 1 / Oct 15 |
| Pennsylvania | 420 | Apr 30 / May 10 - May 25 / Jun 30 | Aug 30 / Sep 10 - Oct 10 / Nov 5 |
| California | 385 | Apr 1 / Apr 15 - Aug 1 / Aug 15 | Aug 1 / Aug 15 - Nov 1 / Dec 1 |
| Minnesota | 380 | Apr 22 / Apr 26 - May 19 / May 29 | Aug 27 / Sep 4 - Oct 5 / Oct 14 |
| South Dakota | 250 | Apr 26 / May 2 - May 27 / Jun 10 | Aug 24 / Sep 3 - Oct 5 / Oct 14 |
| Michigan | 220 | Apr 21 / May 1 - May 27 / Jun 6 | Aug 26 / Sep 7 - Oct 10 / Oct 20 |
| Iowa | 220 | Apr 19 / Apr 25 - May 18 / Jun 23 | Aug 15 / Aug 25 - Sep 20 / Sep 25 |
| Idaho | 215 | Apr 21 / May 5 - May 26 / Jun 9 | Sep 1 / Sep 15 - Oct 6 / Oct 27 |
| North Dakota | 170 | Apr 26 / May 2 - May 28 / Jun 4 | Aug 27 / Sep 6 - Oct 5 / Oct 14 |
| Ohio | 170 | Apr 18 / Apr 24 - May 24 / May 30 | Aug 22 / Sep 2 - Oct 4 / Oct 14 |
| New England | 161 | May 5 / May 12 - Jun 9 / Jun 22 | Sep 5 / Sep 14 - Oct 16 / Oct 26 |
| Texas | 140 | Feb 28 / Mar 20 - Apr 29 / May 15 | Jul 5 / Jul 20 - Sep 5 / Oct 1 |
| Virginia | 135 | Apr 5 / Apr 11 - May 20 / May 29 | Aug 12 / Aug 20 - Sep 27 / Oct 5 |
| Indiana | 110 | Apr 20 / May 1 - Jun 1 / Jun 10 | Aug 15 / Aug 25 - Sep 5 / Sep 20 |
| Colorado | 85 | Apr 19 / Apr 28 - May 20 / May 29 | Aug 28 / Sep 5 - Sep 30 / Oct 7 |
| New Mexico | 78 | Apr 15 / Apr 20 - May 10 / May 20 | Sep 1 / Sep 10 - Oct 1 / Nov 1 |
| Washington | 65 | Apr 10 / Apr 20 - May 20 / Jun 1 | Aug 15 / Aug 30 - Oct 15 / Oct 25 |
| Kentucky | 60 | Apr 20 / May 1 - Jun 10 / Jun 25 | Aug 20 / Aug 25 - Sep 30 / Oct 10 |
| North Carolina | 55 | Apr 1 / Apr 10 - Apr 25 / May 20 | Aug 1 / Aug 20 - Sep 20 / Oct 20 |
| Tennessee | 50 | Apr 10 / Apr 15 - May 15 / May 30 | Aug 1 / Aug 10 - Sep 20 / Oct 1 |
| Utah | 47 | May 1 / May 5 - May 25 / Jun 5 | Sep 5 / Sep 20 - Oct 5 / Oct 20 |
| Montana | 45 | Apr 26 / May 4 - May 28 / Jun 4 | Aug 26 / Sep 6 - Oct 1 / Oct 10 |
| Maryland | 40 | Apr 20 / Apr 30 - May 20 / Jun 7 | Aug 24 / Sep 9 - Oct 1 / Oct 14 |
| Florida | 30 | Mar 1 / Mar 15 - Apr 15 / Apr 30 | Jun 1 / Jun 10 - Jul 20 / Aug 10 |
| Arizona | 30 | Mar 15 / Apr 1 - May 15 / Jun 1 | Sep 1 / Oct 1 - Nov 1 / Dec 1 |
| Mississippi | 10 | Mar 17 / Mar 24 - Apr 27 / May 4 | Jul 13 / Jul 19 - Aug 29 / Sep 12 |

### 3.2 Corn for grain (same states, plus the early-harvest South and the Plains)

| State | 2009 acres | Planting | Harvest |
|---|---|---|---|
| Wisconsin | 2,930 | Apr 26 / May 2 - May 27 / Jun 4 | Oct 2 / Oct 14 - Nov 17 / Nov 28 |
| New York | 595 | Apr 20 / May 4 - Jun 13 / Jun 20 | Oct 7 / Oct 14 - Nov 14 / Nov 25 |
| Pennsylvania | 920 | Apr 30 / May 10 - May 25 / Jun 15 | Sep 25 / Oct 15 - Nov 20 / Dec 10 |
| California | 160 | Mar 15 / Apr 1 - Jul 1 / Jul 15 | Sep 1 / Oct 1 - Nov 1 / Nov 15 |
| Minnesota | 7,150 | Apr 22 / Apr 26 - May 19 / May 29 | Sep 27 / Oct 8 - Nov 8 / Nov 23 |
| South Dakota | 4,680 | Apr 26 / May 2 - May 27 / Jun 10 | Sep 24 / Oct 6 - Nov 16 / Dec 3 |
| Michigan | 2,090 | Apr 21 / May 1 - May 27 / Jun 6 | Sep 5 / Oct 10 - Nov 25 / Dec 10 |
| Iowa | 13,400 | Apr 19 / Apr 25 - May 18 / May 26 | Sep 21 / Oct 5 - Nov 9 / Nov 21 |
| Idaho | 80 | Apr 21 / May 5 - May 26 / Jun 9 | Sep 29 / Oct 20 - Nov 10 / Nov 24 |
| Nebraska | 8,850 | Apr 19 / Apr 27 - May 15 / May 21 | Sep 18 / Oct 4 - Nov 10 / Nov 20 |
| Kansas | 3,860 | Apr 5 / Apr 15 - May 15 / May 25 | Sep 1 / Sep 10 - Oct 25 / Nov 10 |
| Colorado | 990 | Apr 19 / Apr 28 - May 20 / May 29 | Sep 28 / Oct 8 - Nov 13 / Nov 22 |
| Illinois | 11,800 | Apr 14 / Apr 21 - May 23 / Jun 5 | Sep 14 / Sep 23 - Nov 5 / Nov 20 |
| Missouri | 2,920 | Apr 3 / Apr 11 - May 27 / Jun 12 | Aug 29 / Sep 8 - Nov 3 / Dec 22 |
| Kentucky | 1,150 | Apr 6 / Apr 14 - May 24 / Jun 8 | Sep 1 / Sep 9 - Oct 24 / Nov 10 |
| Tennessee | 590 | Apr 1 / Apr 5 - May 10 / May 25 | Aug 25 / Sep 1 - Oct 10 / Oct 30 |
| North Carolina | 800 | Apr 1 / Apr 10 - Apr 25 / May 15 | Aug 25 / Sep 10 - Oct 10 / Nov 1 |
| Oklahoma | 320 | Mar 21 / Apr 2 - May 8 / May 17 | Aug 20 / Aug 29 - Oct 9 / Oct 20 |
| Arkansas | 410 | Mar 26 / Apr 1 - Apr 26 / May 9 | Aug 16 / Aug 23 - Sep 23 / Oct 6 |
| Mississippi | 695 | Mar 17 / Mar 24 - Apr 27 / May 4 | Aug 11 / Aug 23 - Sep 23 / Oct 7 |
| Georgia | 370 | Mar 14 / Mar 22 - Apr 21 / May 4 | Aug 6 / Aug 16 - Sep 22 / Oct 7 |
| Alabama | 250 | Mar 15 / Mar 25 - Apr 25 / May 18 | Aug 2 / Aug 11 - Sep 20 / Oct 15 |
| Louisiana | 610 | Mar 13 / Mar 19 - Apr 8 / Apr 16 | Jul 31 / Aug 9 - Sep 5 / Sep 12 |
| South Carolina | 320 | Mar 10 / Mar 20 - Apr 20 / May 15 | Jul 25 / Aug 20 - Sep 25 / Oct 10 |
| Florida | 37 | Mar 1 / Mar 15 - Apr 25 / May 5 | Jul 15 / Aug 1 - Sept 10 / Oct 1 |
| Texas | 1,960 | Mar 1 / Mar 8 - May 7 / May 17 | Jul 18 / Aug 1 - Oct 11 / Nov 8 |

Sorghum for silage rows (a confuser where the corn mask is imperfect) [O]: Texas Jul 1 / Jul 15 - Oct 1 / Nov 1 (100K acres); New Mexico Sep 5 / Sep 15 - Oct 10 / Nov 1; Arizona Sep 1 / Oct 1 - Oct 30 / Dec 15; Colorado Sep 1 / Sep 5 - Sep 20 / Sep 30; South Dakota Aug 20 / Sep 2 - Oct 11 / Oct 21; Mississippi Aug 4 / Aug 12 - Sep 16 / Oct 2.

### 3.3 Newer sources (this is the "new data source" finding)

1. **National weekly Crop Progress** (NASS, every Monday in season) [O]: state-level percent "Corn Dented", "Corn Mature" and "Corn Harvested" for 18 states ("These 18 States planted 91% of the 2025 corn acreage"), each with last year, last week, this week and the 2021-2025 average. **It has no corn-silage table.** Example file: https://release.nass.usda.gov/reports/prog3826.txt
2. **State weekly Crop Progress and Condition reports** publish silage harvest progress:
   - **Wisconsin** [O]: rows "Corn dented", "Corn mature", "Corn harvested for grain", "Corn harvested for silage", for nine agricultural districts plus state, last week, last year and 5-year average. Week ending 28 Sep 2025: "Corn silage was 66 percent harvested"; "Corn for grain harvest was 4 percent complete"; "Corn was 49 percent mature". District silage progress that week (my reading of the PDF table by column position): NW 62, NC 28, NE 53, WC 62, C 58, EC 68, SW 89, SC 93, SE 75; state 66; previous week 41; previous year 64; 5-year average 68. Week ending 4 Oct 2026: "Corn for silage harvest was 87 percent complete compared to the average of 77 percent"; grain 8 percent.
   - **Idaho, Oregon, Washington** (Northwest regional report) [O]: rows "Field corn harvested for grain" and "Field corn harvested for silage". Idaho, week ending 29 Sep 2024: silage 43% (previous week 28%, 5-year average 53%); grain zero (5-year average 4%).
   - **California** [O]: narrative only, no percent table. Week ending 8 Sep 2024: "Corn and alfalfa fields were greenchopped. In Tulare County, corn fields were greenchopped and delivered to local dairies." Week ending 20 Oct 2024: "In the San Joaquin Valley, corn for silage and dry bean harvests continued." and "In Tulare County, corn fields were in the final stages of production, with most fields harvested."
   - New York, Pennsylvania, Michigan, Minnesota: not checked (their NASS index pages were stale); likely available through Quick Stats or the current-report links. Open question.
3. **Gap in the 2025 record** [O]: in the national report for the week ending 18 Oct 2026 the "October 18, 2025" comparison column is "(NA)" for every state, and the Wisconsin 2025 index lists 6 Oct to 10 Nov 2025 with no report files. Inference: weekly Crop Progress was not published for about 5 Oct to 16 Nov 2025 (federal funding lapse). The September 2025 silage window is covered; most of the 2025 grain-harvest progress curve is missing.

### 3.4 Season snapshots from the national report

Percent of corn **harvested for grain** [O]:

| State | 6 Sep 2025 | 20 Sep 2025 | 6 Sep 2026 | 20 Sep 2026 | 18 Oct 2026 | 2021-25 avg, 18 Oct |
|---|---|---|---|---|---|---|
| Texas | 68 | 75 | 69 | 77 | 92 | 92 |
| North Carolina | 42 | 72 | 38 | 67 | 91 | 93 |
| Tennessee | 26 | 59 | 30 | 62 | 96 | 85 |
| Kentucky | 15 | 41 | 19 | 46 | 86 | 75 |
| Missouri | 8 | 26 | 14 | 32 | 71 | 71 |
| Kansas | 2 | 19 | 18 | 40 | 70 | 73 |
| Illinois | 2 | 11 | 3 | 16 | 63 | 58 |
| Iowa | 0 | 7 | 0 | 4 | 26 | 50 |
| Nebraska | 0 | 5 | 0 | 7 | 37 | 48 |
| Minnesota | 0 | 1 | 0 | 4 | 38 | 53 |
| Wisconsin | 0 | 1 | 0 | 2 | 24 | 29 |
| Michigan | 0 | 0 | 0 | 0 | 13 | 31 |
| Pennsylvania | 0 | 3 | 0 | 0 | 15 | 25 |
| 18 States | 4 | 10 | 5 | 13 | 44 | 52 |

Percent of corn **mature** on 20 Sep 2025 [O]: Texas 93, Tennessee 90, North Carolina 89, Kentucky 82, Missouri 80, Kansas 68, Illinois 66, Iowa 63, Indiana 52, Ohio 48, Nebraska 44, South Dakota 44, Minnesota 41, Pennsylvania 37, Michigan 30, Wisconsin 26, Colorado 26, North Dakota 18; 18 States 54.

Inference (useful calibration): in Wisconsin in 2025, "dented" passed about 66% around 13 Sep (52% on 6 Sep, 81% on 20 Sep) and silage harvest reached 66% on 28 Sep. Silage progress therefore lagged the dent curve by about two weeks and led the "mature" curve (49% on 28 Sep). That is what the physiology in section 2 predicts (half milk line is 10-15 days after dent and about 13 days before black layer).

---

## 4. "Early is not silage" (c)

| Where | When grain is combined | Source |
|---|---|---|
| Lower Rio Grande Valley, South Texas, Winter Garden | late June to mid July | Texas crop profile 2003 [O] |
| Texas Upper Coast and Coastal Bend | late June to mid August | Texas crop profile [O] |
| South Central Texas | late July to mid August | Texas crop profile [O] |
| Texas Blacklands | late July to late August | Texas crop profile [O] |
| East Texas | late July to early September | Texas crop profile [O] |
| Edwards Plateau | late August to late September | Texas crop profile [O] |
| Texas Plains and Cross Timbers | early September to mid October | Texas crop profile [O] |
| Texas statewide | begin Jul 18, most active Aug 1 - Oct 11 | Handbook [O] |
| Louisiana | begin Jul 31, most active Aug 9 - Sep 5, end Sep 12 | Handbook [O] |
| South Carolina / Florida | begin Jul 25 / Jul 15 | Handbook [O] |
| Alabama / Georgia / Mississippi / Arkansas | begin Aug 2 / Aug 6 / Aug 11 / Aug 16; most active from Aug 11-23 | Handbook [O] |
| Oklahoma / Tennessee / North Carolina / Missouri | begin Aug 20 / Aug 25 / Aug 25 / Aug 29 | Handbook [O] |
| Kansas / Kentucky | begin Sep 1 | Handbook [O] |

- Texas planting runs "from late January to early May"; the Lower Valley, Winter Garden and South Texas plant "between late January and late February" (Texas profile [O]). Outside the Plains, Texas grain "is harvested below 14% moisture", so it stands dry in the field for weeks before the combine: early date, long dry-down, heavy residue.
- The 2025 season confirms it: 68% of Texas grain was harvested by 6 Sep 2025 and 42% of North Carolina's (section 3.4). Louisiana is normally 95% done by 12 September, four days after Wisconsin silage harvest normally *begins*.
- The Northern High Plains produce "almost two thirds of total Texas corn production" and are irrigated; they behave like Kansas and Nebraska, not like South Texas (Texas profile [O]).
- Inference: in the South the early cut comes with a brown, dry canopy and a blanket of residue. The dry-down gap and the residue feature carry the decision; a calendar threshold tuned on the Midwest calls these fields silage.

---

## 5. The California system (d)

Sources: UC Cooperative Extension cost studies for double-cropped corn silage (southern San Joaquin Valley, 2012), conservation-tillage silage corn (northern San Joaquin Valley, 2015) and field corn for grain (Sacramento Valley and northern San Joaquin Valley, 2015); UC "Managing Dairy Manure in the Central Valley of California" (2005 revision); UC SAREP final report (2003); NASS California weekly reports (2024); NASS annual summaries. All [O].

### 5.1 Acreage

| Year | Planted, all purposes | Harvested for grain | Harvested for silage | Silage yield (tons/acre) |
|---|---|---|---|---|
| 2020 | 440 | 60 | 375 | - |
| 2021 | 400 | 50 | 345 | - |
| 2022 | 370 | 20 | 345 | - |
| 2023 | 400 | 40 | 350 | 26.0 |
| 2024 | 440 | 55 | 380 | 26.0 |
| 2025 | 420 | 50 | 365 | 27.0 |

Thousand acres; NASS Crop Production annual summaries of January 2023 and January 2026 [O]. Silage is 85-93% of planted acres. A classifier that says "always silage" in California scores about 88%; the class imbalance is reversed.

### 5.2 Silage corn calendar

- **Single-cropped silage:** "planting is usually completed by early April for single cropped and then harvested in August" (UC 2012).
- **Double-cropped silage (the typical dairy system):** "Land preparations begin in May immediately after harvest of the winter forage"; "In late May, the Roundup Ready corn is planted"; a pre-plant irrigation of 8 acre-inches in May, then "eight irrigations totaling 40 acre-inches"; "Growing season irrigations start in June and end in September"; "In September the corn is harvested, processed, hauled, and packed into a silage pit by a custom operator"; yield "32 tons per acre at 70% moisture" (UC 2012).
- Northern San Joaquin Valley (UC 2015): "Winter cereal forage crops are harvested from March through April"; "Composted manure is hauled and spread. The field is then pre-irrigated"; "Corn is usually planted from March - May"; "From June to September, seven irrigations totaling 36 acre-inches"; "In September the corn is harvested and hauled to the storage pit by a custom operator".
- The NASS handbook gives a much wider window: silage planting most active 15 Apr - 1 Aug, harvest most active 15 Aug - 1 Nov, ending 1 Dec. NASS weekly reports confirm chopping still under way on 20 Oct 2024 and greenchop in early September.
- **Irrigation before harvest:** silage is irrigated into September, the harvest month; grain corn gets its last of six bi-weekly irrigations in July and is combined in September. I found no explicit "stop irrigating N days before chopping" rule (not verified).
- **Who harvests:** "Normally, non-dairy growers sell the crop standing and the buyer or dairy pays the harvesting cost" (UC 2012 and 2015). A silage field does not have to belong to a dairy.
- **Haul cost:** custom harvest, haul and pack $9.25 per ton plus "$0.20" per ton per mile "for hauls greater than one mile" (UC 2012). Inference: at $45 per ton, 20 miles of hauling costs about 8% of the crop's value and 50 miles about 22%, which is why silage stays within tens of miles of the feeding site.

### 5.3 Share of corn that follows winter forage

- "In recent years (2000-2002), silage corn has been produced on about 345,000 acres statewide. Much of this is grown in a double crop (i.e., two crops per year) rotation with the cool season grass forages" (UC SAREP 2003).
- Survey of ten participating dairies: "Of the manure water acreage 8% was single crop silage corn, 57% double or triple crop silage corn/winter forage, 21% alfalfa, and 14% other" (UC SAREP 2003). Inference: about 88% of the silage-corn area on those dairies (57 of 65) was double- or triple-cropped. This is a small 2003 sample, not a statewide statistic; no statewide share was found.
- UC 2015's model farm double-crops 145 of 150 rented acres with "a winter forage crop followed by corn silage".
- The CDL has dedicated classes that can measure this directly: 225 Dbl Crop WinWht/Corn, 226 Dbl Crop Oats/Corn, 228 Dbl Crop Triticale/Corn, 237 Dbl Crop Barley/Corn (NASS CDL FAQ [O]). NASS notes the CDL "is currently not equipped to monitor triple or quad cropping practices".

### 5.4 What follows silage

- Winter cereal forage "such as barley, oats, triticale or wheat" (UC 2015). "The cereal forages (also referred to as "winter forages") are usually planted in mid- to late fall"; "Sometimes, winter forages are planted earlier in the fall, from mid-September to mid-October"; trial planting dates are mid-October, early November and late November/early December; "as much as 85% of the nitrogen uptake takes place during late February, March and April" (UC manure report).
- Manure: "Commercial fertilizers may be reduced or eliminated with the use of dairy pond water or corral scrapings" (UC 2012); "diluted lagoon water via surface gravity irrigation systems, by which method nearly all lagoon water is applied in California" (UC manure report).
- Satellite expectation (Inference): chop in Aug-Oct, bare or lightly stubbled soil, irrigation and tillage, winter cereal emerging Nov-Dec, canopy peak Feb-Apr, forage chop Mar-Apr, corn again in May. Two green peaks per year on the same field is the fingerprint of the dairy forage system.

### 5.5 Grain corn in California

- Grown in "the Sacramento Valley and northern San Joaquin Valley"; county yields are reported for "Colusa, Glenn, Sacramento, Sutter, and Yolo"; the author team includes the Delta crops advisor for San Joaquin County; a separate study covers the southern San Joaquin Valley (UC 2015 field corn).
- Rotation: "processing tomatoes, alfalfa hay, rice, safflower, sunflower, dry beans and/or wheat". No winter forage; beds are listed the previous October and sprayed as fallow beds from February.
- "Field corn is generally planted from late March through April"; "six post-plant irrigations are applied bi-weekly in May, June, and July"; "The corn crop is allowed to dry down in the field"; "Corn is normally harvested under 14% grain moisture". The operations table puts the combine in September and stubble chopping and discing in October.
- Residue: "the crop residue is chopped with a tractor and flail mower and then a tractor with a stubble disc and roller works the residue into the soil"; "In some situations the stubble is baled and the bales are taken off the field by a custom farmer or dairy operation."
- Inference: California grain and silage cannot be separated by cut date. Separate them by (1) weeks of brown, unirrigated canopy before the cut (grain) versus green and irrigated to the cut (silage); (2) the previous winter's forage peak (silage) versus winter fallow beds (grain); (3) residue in the first scene after the cut, before the October stubble disc.

---

## 6. Other fates and confusers, and how NASS counts them (e)

### 6.1 NASS definitions

From the NASS December Agricultural Survey enumerator training (2023) [O]:

- Planted (two consecutive slide bullets): "Acres planted for all purposes" and "Includes grain, seed, silage, grazed off, or abandoned".
- "Corn harvested for grain - We are looking for all corn harvested other than for seed or silage. The end use does not matter. Can be used for livestock feed, corn starch, corn syrup, ethanol, pet food, etc."
- "All states that ask about corn will ask corn acres harvested for grain and acres harvested for seed in separate questions."
- "Silage: made by chopping up the entire plant packing in a silo, bunker, or plastic bags and allowed to ferment."
- "Acres for all other purposes - Includes grazed off, abandoned, or any other purpose".
- For very low yields, enumerators are told only a few acres may have been "actually harvested to prove yields for insurance purposes" and "the rest would fall under "acres for all other purposes"".

So silage acreage and production are farmer-reported in December and first published in the January annual summary.

NASS "Corn Acreage Inclusions" table (dated 9 Aug 2019) [S: HTTP 404 on open]: corn planted for grain and later switched to silage moves from grain to silage; planted-but-failed counts as planted only; silage harvested acres are "only published at end of season".

### 6.2 Fate table

| Fate | What physically happens | When | Left on the field | NASS bucket |
|---|---|---|---|---|
| Whole-plant silage | Forage harvester cuts and chops the entire plant; 17-31 wet tons per acre removed in one pass (2025 state yields: NY 17, WI 22, CA 27, ID 31) | Half milk line, 65-70% whole-plant moisture | Stubble only | Silage |
| Green chop | Whole plant chopped and fed the same day, a strip at a time | California reports it in early September | Stubble; field removed progressively over days or weeks | Inference: silage (NASS Census tables use "corn for silage or greenchop" [S]) |
| High-moisture shelled corn | Combined at "24 percent or greater moisture", usually 28-32%, then ground and ensiled | "2 to 3 weeks earlier" than dry grain; Idaho end of September to end of October | All stover | Grain (end use does not matter) |
| High-moisture ear corn, earlage, snaplage | "snap roll header from a combine attached to a forage harvester, which removes and chops the ear components, leaving the remaining stover in the field" | Idaho: "a few weeks to a month after silage corn"; kernel 28-36% | Stalks and leaves, often grazed | Inference: grain, because it is not "the entire plant" and not seed. Confirm with NASS. |
| Dry grain | Combine | Black layer + 2 to 8+ weeks; Idaho as late as March | All stover, about 90% ground cover | Grain |
| Grain, then stover baled or stalks grazed | Residue removed days to weeks after the combine, or slowly over winter | After grain harvest | Reduced residue | Grain |
| Grain, then fall tillage | Chisel, disc, strip-till or plow | Days to weeks after the combine | See section 8 | Grain |
| Drought-salvage silage | Stressed or barren corn chopped early | July-September in drought areas | Stubble, often cut high (10-12 in) | Silage (switch from intended grain) |
| Frost-salvage silage | Immature corn killed by frost, left to dry to under about 72%, then chopped | Late September-October, northern tier | Stubble | Silage |
| Hail-salvage | Same as drought salvage if chopped | Any time after the storm | Stubble or shredded stalks | Silage if chopped, otherwise other |
| Grazed or hogged down | Cattle turned into standing corn with strip fencing | Late summer to winter | Trampled stalks, gradual loss | Other purposes |
| Cut for hay, dry stover or baleage | Windrowed and baled; NebGuide G1865 advises leaving 8-12 inches of stubble if nitrate is high | Drought years | Windrows then bales | Other purposes ("hay" is listed under other purposes on the NASS form [S]) |
| Abandoned or failed | Nothing harvested; sometimes a few acres cut for an insurance appraisal | - | Standing dead crop, or disced | Other purposes |
| Seed corn | Asked as a separate question from grain | Not verified (lead: on the ear in September) | Not verified | Harvested for seed. Whether published grain acres include it: open question |
| Popcorn | Separate CDL class 13 "Pop or Orn Corn" | Not verified | - | Not verified |
| Sweet corn | Separate CDL class 12 "Sweet Corn"; NASS California weekly reports list sweet corn being harvested in the Central Valley in the weeks ending 8 Sep and 20 Oct 2024 | Not verified for processing regions (lead: green, July-September) | Not verified | Vegetable, not field corn |
| Sorghum or sudangrass silage | Different crop; Texas sorghum silage most active 15 Jul - 1 Oct | Overlaps corn silage | Stubble; sudangrass regrows | Not corn. In 2012 sorghum silage area rose 62% to 363,000 acres |

Sources: UW L062, Idaho BUL 956, NebGuide G1865, Penn State, UMN, NASS California weekly, ERS Feed Outlook Jan 2013, NASS CDL FAQ, Purdue AY-269-W [all O].

Useful detail on the in-between fates:

- UW L062 [O]: desired moisture is 28-32% for high-moisture corn in a bunker or bag, 32-36% for high-moisture ear corn, 35-38% for snaplage; composition by dry matter is grain 100% / 84-94% / 75-80%. The page notes that cattle can graze the corn residue earlier and for a longer window after these harvests (paraphrase).
- Idaho BUL 956 [O]: about 300,000 acres of field corn on the Snake River Plain; "Approximately 25% is grown for either high moisture corn or dry grain ... with the remainder intended as silage or high moisture ear corn (HMEC) known as earlage or snaplage." NASS 2025 for Idaho: 430K planted, 145K grain (34%), 280K silage (65%).

### 6.3 Size of the "other" bucket

Planted minus grain minus silage, from the NASS track record [O]: mean 1.64% of planted acres for 2000-2025, range 0.90% (2005) to 3.10% (2002). Drought years: 2002 3.10%, 2012 2.58%, 2022 2.96%. 2025: 1.34% (1.32M acres). If seed corn is not inside "grain", it sits in this remainder too (open question).

---

## 7. Late switching between grain and silage (f)

### 7.1 Triggers (source statements)

- Missouri G4591, revised November 2025 [O]: "Corn silage can be made from corn planted for silage or as a grain crop. Farmers have several reasons for reconsidering their harvest method. For example, they or a neighbor may have a need for silage that was not anticipated at planting time, or drought may have reduced grain yields substantially so that the value of the crop is greater as silage than as grain."
- Iowa State 2008 [O]: with late planting or late maturity, frost may force a silage harvest; immature corn can be harvested for silage or used in grazing programs (paraphrase).
- Penn State [O]: frosted corn should be left "to dry to at least 72 percent moisture for a horizontal silo".
- NebGuide G1865 [O]: "four consecutive days of severe wilting during silking and pollination can reduce yield 40-50 percent"; salvage options are silage, greenchop, grazing or dry stover; "you can expect to harvest about one ton of silage per acre for each five bushels of corn grain".
- Before salvaging, growers must clear it with crop insurance and FSA (UNL 2012; UMN [O]). Inference: the appraisal step delays the chop and leaves appraisal strips standing.
- **Reverse switch.** Iowa State economist Chad Hart, quoted 21 Jan 2026 [O]: "USDA added 1.3 million acres to corn harvested"; "A lot was originally intended for silage, but, given how great a year it was for production ... that acreage got redirected back into the grain market." Bunkers fill on fewer acres in a high-yield year.

### 7.2 Standing-corn pricing rules

| Rule | Source |
|---|---|
| "valuation of 8 to 10 times the price of a bushel of corn. A factor of 8 to 9 times is used to price silage in the field, and 9 to 10 times to price it in storage" | Missouri G4591 (rev. 11/2025) [O] |
| "Currently, silage priced in the field may be closer to 7 times the price of a bushel of corn." | Missouri G4591 [O] |
| Delivered: "nine to 10 times the price of a bushel of corn if it is delivered to the bunker or pile"; as-fed, not delivered: "a ton of as-fed corn silage is worth five to six times the price of a bushel of corn" | UNL CropWatch, 20 Jul 2012 [O] |
| Minimum: "each ton of silage is worth about five times the current price per bushel of shelled corn plus $2.00 per ton" | NebGuide G1865 (2008) [O] |
| Drought-stressed feed value: 90-100% of normal at 20-40 bu/acre, 80-90% at 0-20 bu/acre, 70-80% for short barren stalks | UNL CropWatch 2012 (after UW W-187) [O] |
| Worked example: 170 bu/acre at $4.20 gives a standing value of $28.53 per wet ton | Missouri G4591 [O] |

Inference: the switch happens when expected grain revenue (bushels x price, less combining, drying and hauling) drops below silage tons x roughly 7-9 x the corn price. With 1 ton per 5 bushels, a field that would make 50 bu/acre yields about 10 tons of silage; drought plus a nearby buyer tips it. The grain-to-silage ratio is roughly constant, so yield loss, not price, is the main trigger, and distance to a feeder is the enabling condition.

### 7.3 How large it gets: national series

USDA NASS, Crop Production Historical Track Records, April 2026 [O]; thousand acres; "other" and shares computed by me.

| Year | Planted | Grain | Silage | Other | Silage % of planted | Other % |
|---|---|---|---|---|---|---|
| 1980 | 84,043 | 72,961 | 9,299 | 1,783 | 11.1 | 2.1 |
| 1983 | 60,207 | 51,479 | 7,808 | 920 | 13.0 | 1.5 |
| 1988 | 67,717 | 58,250 | 8,301 | 1,166 | 12.3 | 1.7 |
| 2001 | 75,702 | 68,768 | 6,142 | 792 | 8.1 | 1.0 |
| 2002 | 78,894 | 69,330 | 7,122 | 2,442 | 9.0 | 3.1 |
| 2010 | 88,192 | 81,446 | 5,567 | 1,179 | 6.3 | 1.3 |
| 2011 | 91,936 | 83,879 | 5,935 | 2,122 | 6.5 | 2.3 |
| 2012 | 97,291 | 87,365 | 7,419 | 2,507 | 7.6 | 2.6 |
| 2013 | 95,365 | 87,461 | 6,271 | 1,633 | 6.6 | 1.7 |
| 2019 | 89,370 | 80,991 | 6,565 | 1,814 | 7.3 | 2.0 |
| 2020 | 90,432 | 82,168 | 6,560 | 1,704 | 7.3 | 1.9 |
| 2021 | 92,901 | 84,988 | 6,451 | 1,462 | 6.9 | 1.6 |
| 2022 | 88,162 | 78,705 | 6,851 | 2,606 | 7.8 | 3.0 |
| 2023 | 94,641 | 86,506 | 6,461 | 1,674 | 6.8 | 1.8 |
| 2024 | 90,909 | 83,046 | 6,207 | 1,656 | 6.8 | 1.8 |
| 2025 | 98,788 | 91,258 | 6,208 | 1,322 | 6.3 | 1.3 |

- 2000-2025 silage area: mean 6.30M acres, standard deviation 0.40M, minimum 5.57M (2010), maximum 7.42M (2012).
- **2012:** silage +1.48M acres (+25%) over 2011. ERS Feed Outlook, 15 Jan 2013 [O]: "Area harvested for corn silage is estimated at 7.4 million acres, up 24 percent from the 2011 estimate and the highest level since 1988"; silage yield 15.4 tons per acre, "down 16 percent". The June 2012 Acreage report expected 88.9M acres for grain [S: NASS release seen in search summary only]; the final is 87.4M, about 1.5M lower.
- **2002:** silage +0.98M (+16%); other 3.1%.
- **2022:** June Acreage report [O]: 89.921M planted and 81.940M expected for grain. Final: 88.162M planted and 78.705M for grain. Grain acres finished **3.2M below the June forecast**; acres not harvested for grain rose from an implied 7.98M to 9.46M even though 1.76M fewer acres were planted.
- farmdoc daily (Darrel Good, 4 Sep 2012) [O]: silage "tends to spike in years of dry weather"; "silage acreage increased by 1.3 million acres in 1980, 2.3 million acres in 1988, and just over one million acres in 2002"; unharvested area rose by 780,000 acres in 1980, 460,000 in 1988 and 1.65 million in 2002.
- DTN (Elaine Kub, 15 Jan 2020) [O]: 2019 was 91% grain, 7.3% silage, 1.8% unharvested; 2.6% was left unharvested in 2012; silage was 10-12% of planted acres in the 1980s against 6-8% recently.

### 7.4 Where it happens: state detail for the 2022 drought

Thousand acres; June 2022 Acreage report and January 2023 annual summary [O].

| State | Silage 2021 | Silage 2022 | Change | Grain, June 2022 forecast | Grain, final (Jan 2023) | Difference |
|---|---|---|---|---|---|---|
| Kansas | 240 | 420 | +75% | 5,050 | 4,440 | -610 |
| Nebraska | 260 | 430 | +65% | 9,400 | 8,820 | -580 |
| South Dakota | 500 | 550 | +10% | 5,400 | 5,010 | -390 |
| Texas | 250 | 260 | +4% | 1,900 | 1,610 | -290 |
| Missouri | 70 | 150 | +114% | - | - | - |
| Iowa | 340 | 400 | +18% | - | 12,400 | - |
| Wisconsin | 880 | 880 | 0% | 3,000 | 3,030 | +30 |
| New York | 445 | 440 | -1% | 590 | 575 | -15 |
| California | 345 | 345 | 0% | 20 | 20 | 0 |

Reading: Kansas and Nebraska absorbed drought by chopping (silage up 350K acres between them); Texas absorbed it mostly by abandonment (grain down 290K with silage flat). Dairy states did not move.

### 7.5 State silage acres 2023-2025 and class priors

NASS Crop Production 2025 Summary, 12 Jan 2026 [O]; thousand acres.

| State | Silage 2023 | Silage 2024 | Silage 2025 | 2023 to 2024 | 2024 to 2025 | Silage share of grain + silage, 2025 |
|---|---|---|---|---|---|---|
| Wisconsin | 780 | 730 | 885 | -6% | +21% | 21.6% |
| New York | 430 | 455 | 500 | +6% | +10% | 52.6% |
| South Dakota | 520 | 410 | 390 | -21% | -5% | 5.8% |
| California | 350 | 380 | 365 | +9% | -4% | 88.0% |
| Minnesota | 350 | 380 | 360 | +9% | -5% | 4.1% |
| Michigan | 320 | 325 | 350 | +2% | +8% | 15.0% |
| Pennsylvania | 345 | 320 | 315 | -7% | -2% | 31.7% |
| Idaho | 240 | 265 | 280 | +10% | +6% | 65.9% |
| Texas | 280 | 160 | 265 | -43% | +66% | 11.0% |
| Iowa | 380 | 340 | 250 | -11% | -26% | 1.9% |
| Kansas | 330 | 310 | 230 | -6% | -26% | 3.4% |
| Nebraska | 280 | 280 | 210 | 0% | -25% | 2.0% |
| Colorado | 235 | 200 | 200 | -15% | 0% | - |
| Ohio | 160 | 160 | 200 | 0% | +25% | - |
| North Dakota | 200 | 260 | 170 | +30% | -35% | - |
| United States | 6,461 | 6,207 | 6,208 | -4% | 0% | 6.4% |

2025 state balance sheets (planted / grain / silage / other): Wisconsin 4,150 / 3,220 / 885 / 45; New York 970 / 450 / 500 / 20; Texas 2,500 / 2,140 / 265 / 95 (3.8% other); Kansas 6,850 / 6,500 / 230 / 120; Nebraska 10,750 / 10,450 / 210 / 90; Iowa 13,550 / 13,200 / 250 / 100; Minnesota 8,900 / 8,450 / 360 / 90; Michigan 2,350 / 1,980 / 350 / 20; Pennsylvania 1,010 / 680 / 315 / 15; South Dakota 6,850 / 6,350 / 390 / 110; Idaho 430 / 145 / 280 / 5; California 420 / 50 / 365 / 5.

Note on revisions: the January 2023 summary gave 2022 as 88,579 planted, 79,207 grain, 6,860 silage; the April 2026 track record shows 88,162 / 78,705 / 6,851. NASS totals move after the January report, so reconcile to a stated vintage.

---

## 8. Stubble height and residue (g)

| Item | Number | Source |
|---|---|---|
| Baseline silage cutting height in the UW calculator | 10 in | UW Extension 2025 [O] |
| High-cut heights modelled | 25 in and 40 in | UW Extension 2025 [O] |
| Dry-matter yield at 10 / 25 / 40 in | 8.0 / 7.0 / 6.0 tons DM per acre | UW Extension 2025 [O] |
| Feeding trial contrast | 18 in versus 5 in (Neylon and Kung 2003) | UW Extension 2025 [O] |
| Penn State trial averages | low cut about 6.8 in, high cut about 19.3 in; yield about 7.4% lower | [S: secondary summary, not opened] |
| Drought, to avoid nitrate | raise the cutter "to a height of 10 to 12 inches" | UMN [O] |
| Nitrate location | lower 8-10 inches of the stalk (paraphrase); lower third of stalk 5,524 ppm versus 978 ppm whole plant | NebGuide G1865; UMN [O] |
| Stover for hay in drought | leave 8-12 inches of stubble if nitrate is high (paraphrase) | NebGuide G1865 [O] |
| After silage | silage "leaves little crop residue on the soil"; the guide recommends a winter rye or ryegrass cover crop and less tillage | Penn State [O] |
| After grain | "initial crop cover (approx. 90% for 180-bu. corn, 80% for 45-bu. soybeans)" | Purdue AY-269-W [O] |
| Conservation tillage threshold | "at least 30% of the field surface covered with crop residue after planting" | Purdue AY-269-W [O] |

Cover remaining after one pass of each operation (Purdue AY-269-W Table 1, from Stott, Alberts and Weltz 1995; use the upper end for corn) [O]:

| Operation | Cover remaining |
|---|---|
| Moldboard plow | 3 to 5% |
| Chisel plow, straight points | 50 to 80% |
| Chisel plow, twisted points (disk chisel) | 30 to 60% |
| Knife-type fertilizer applicator | 50 to 80% |
| Disk, 3 inch deep | 40 to 80% |
| Disk, 6 inch deep | 30 to 60% |
| Field cultivator | 50 to 80% |
| Cultivator / disk combination tool | 30 to 60% |
| Winter weathering | 75 to 85% |

Purdue's worked example for corn: 90% x 85% (weathering) x 80% (chisel) x 80% (disk) x 90% (planter) = 44% by planting.

Inference:

- Using the UW slope (1 ton DM per acre per 15 inches), a normal 5-10 in stubble holds roughly 0.3-0.7 tons DM per acre of stalk bases and a 20 in high chop about 1.3 tons, all standing and upright. A grain field keeps its entire stover lying flat. No opened source gives a percent cover after silage, but "little crop residue" against "approx. 90%" is the largest contrast in this note.
- That contrast is perishable. One twisted-point chisel pass takes a grain field from about 90% to 27-54% cover; chisel plus disk can take it to roughly 10-40%; a moldboard plow to 3-5%. Baling and grazing remove residue without soil disturbance. Residue must be read from the first clear scene after the cut, and the lag between cut and residue loss is itself informative (zero lag for silage, days to weeks for tilled grain).
- High-chop silage and drought-salvage silage (10-12 in) leave more upright stubble than normal silage.

---

## 9. Rain-fed versus irrigated: greenness at the chop (h)

- UMN Extension (reviewed 2025) [O]: "Even if the corn looks fired up and dried out, it may still contain over 70% moisture." Where plants have grain developing, growers are told to leave them as long as possible; barren plants with little green tissue are harvested once moisture suits the storage. If plant moisture falls below 70%, silage harvest may need to start (paraphrase).
- Penn State [O]: with drought-stressed corn, delay harvest if moisture is higher than it appears; ensile when the crop "may not resume growth".
- NebGuide G1865 [O]: delay harvest if the corn pollinated and green leaf and stalk tissue remain without a black layer, since rain can still improve it.
- UNL 2023 [O]: drought, heat and short-season hybrids speed maturity; the 45-day / 800 GDD benchmark is for fully irrigated full-season corn.
- University of Florida [S: not opened]: even with brown lower leaves, plants can hold 75-90% water.

Inference for the satellite:

| Situation | Canopy color at the chop | Plant water at the chop | Cut date |
|---|---|---|---|
| Irrigated silage (CA, ID, High Plains pivots) | Green, irrigated to within days or weeks of the chop | 65-70% | On the physiological schedule |
| Rain-fed silage, normal year (WI, NY, PA, MI, MN) | Mostly green; husks and lower leaves starting to dry | 65-70% | On schedule |
| Rain-fed drought salvage (dryland KS, NE, SD, TX, MO) | Fired or brown lower and middle canopy; can look like a senesced grain crop | Still 65-75% or more | Early, sometimes before dent |
| Frost salvage (northern tier) | Bleached within days of the frost | Above 70% until it dries down | 1-3 weeks after the frost |

A visible-and-near-infrared greenness ratio will under-call salvage silage. A shortwave-infrared moisture index should hold up better because the plant is still wet, and the cut still comes early and still leaves bare ground.

---

## 10. Truth table: timing x greenness x residue

T = cut timing; G = green or wet at the last clear look before the cut; D = dry-down gap from canopy browning to the cut; R = ground in the first clear look after the cut. Everything in this table is **Inference** assembled from sections 2-9.

| Fate | NASS bucket | T | G | D | R | Extra tell-tale | Confused with |
|---|---|---|---|---|---|---|---|
| Planned silage, irrigated | Silage | About 200 GDD before black layer; 4-6 weeks before local grain | High | About zero | Bare soil and short upright stubble | Largest one-day loss of wet biomass (17-31 tons/acre); winter forage or manure irrigation follows | Sweet corn, green chop |
| Planned silage, rain-fed | Silage | Same; WI 13 Sep-13 Oct, NY 10 Sep-1 Oct | High to medium | 0-10 days | Bare soil and stubble | Cover crop green-up or manure within weeks | High-moisture corn |
| Double-crop silage (CA, also AZ) | Silage | Late: September to November | High | About zero | Bare, then winter forage | Winter forage peak Feb-Apr before the corn; planted late May or later | CA grain by date alone |
| Green chop | Silage (inferred) | July-September | High | About zero | Bare, in strips | Field disappears strip by strip over days or weeks | Partial harvest, lodging |
| Drought-salvage silage | Silage | Very early, before or near dent | Low to medium color, moisture still high | Can be weeks of browning before the chop | Bare, taller stubble | Low biomass; drought area; appraisal strips; near a feeder | Southern early grain; abandoned corn |
| Frost-salvage silage | Silage | 1-3 weeks after a killing frost | Low | 1-3 weeks | Bare and stubble | Frost date in weather record; northern tier | Early high-moisture corn |
| High-moisture shelled corn | Grain | Black layer + 0-2 weeks; 2-3 weeks before dry grain | Low to medium | 1-3 weeks | Full residue | Dairy or feedlot region | Late silage |
| Earlage / snaplage | Grain (inferred) | Between silage and dry grain | Medium to low | 1-3 weeks | Stalks left, often grazed | Idaho, dairy and feedlot regions | Silage if residue is not read |
| Dry grain, Corn Belt | Grain | Black layer + 2-8 weeks; Oct-Nov | Low | 2-8 weeks, 150-375+ GDD | About 90% residue cover | Slow fade, then a modest structural change | - |
| Dry grain, South | Grain | July-early September | Low | Weeks (dried to under 14% standing) | Heavy residue | Calendar earlier than northern silage | Silage by date alone |
| Dry grain, California | Grain | September | Low | 6-8 weeks after last irrigation | Residue, flail-chopped and disced in October | No winter forage; tomato, rice, safflower rotation | Double-crop silage by date alone |
| Grain, stover baled or grazed | Grain | As grain | Low | Long | Residue drops after a lag of days to weeks, or slowly over winter | Windrows and bales; cattle | Silage if R is read late |
| Grain, fall tillage | Grain | As grain | Low | Long | 30-80% after chisel, 3-5% after plow, after a lag | Roughness, strip-till bands | Silage if R is read late |
| Grazed or hogged down | Other | No cut event | Low | - | Gradual decline, trampled | Fencing strips | Lodged grain |
| Abandoned or failed | Other | No cut event, or disced | Low | - | Standing dead, or tilled | Drought or flood area | Late grain |
| Seed corn (not verified) | Seed | Lead: early, on the ear | Lead: medium | Short | Stalks left | Lead: male rows removed after pollination, giving a striped field | Earlage |
| Sweet corn | Not field corn | Lead: green, July-September | High | About zero | Stalks left or chopped | CDL class 12 | Silage if the mask is wrong |
| Sorghum or sudan silage | Not corn | July-October | High | About zero | Stubble, sudan regrows | CDL sorghum classes; later planting | Corn silage in the Southern Plains |

The two-question version that survives the table:

1. **Was the crop still green or wet when it was cut** (short dry-down gap)?
2. **Was the ground bare right after** (no residue blanket in the first clear look)?

- Yes and yes: silage.
- No and no: grain.
- Yes and no (green, residue left): high-moisture corn, earlage or snaplage, sweet corn, seed corn. These are grain for NASS, apart from sweet corn, which should be masked.
- No and yes (brown, bare): salvage silage, or grain with immediate tillage or baling. Break the tie with thermal timing relative to local maturity, the lag between cut and bare ground, drought or frost context, and distance to a feeder.

---

## 11. What this means for Kernel

### 11.1 Changes to the four numbers in plan v2

1. **Cut date: express it thermally and locally.** Use GDD (base 50 F, cap 86 F) and report the cut relative to local maturity: the field's own senescence, or the state "mature" curve from NASS Crop Progress. Planned silage should sit about 200 GDD before maturity; dry grain at least 150 GDD after. Keep the county-relative date as a second view. Wisconsin's districts differed by 65 points of silage progress in the same week (28% to 93%), so "relative to county" is essential and "relative to state" is too coarse.
2. **Green at cut: add wet at cut.** Keep the share of peak NDVI at the last clear scene, and add the same ratio for a moisture index (NDMI). Salvage silage looks fired but "may still contain over 70% moisture".
3. **Dry-down gap: this is the most defensible feature; compute it in GDD too.** Expected: silage about 0-100 GDD, high-moisture corn and earlage about 100-250, dry grain 150-375 or more, Southern and Californian field-dried grain far more. It is the one feature that still works where the calendar fails.
4. **Ground left: read it early and record the lag.** Use the first clear scene within about 10-14 days of the cut. Store "days from cut to low residue". Later loss of residue is management (chisel, baling, grazing, manure), not harvest fate.

Index definitions as used in the team plan (standard definitions; not re-verified in this session, confirm against the remote-sensing notes). Sentinel-2 bands: B4 red, B8 or B8A near infrared, B11 SWIR1, B12 SWIR2.

```
NDVI = (B8  - B4 ) / (B8  + B4 )
NDMI = (B8A - B11) / (B8A + B11)
NDTI = (B11 - B12) / (B11 + B12)
STI  =  B11 / B12
green_at_cut = NDVI(last clear scene before cut) / NDVI(season peak)
wet_at_cut   = NDMI(last clear scene before cut) / NDMI(season peak)
drydown_gdd  = GDD(cut date) - GDD(date NDVI first falls below a fixed fraction of peak)
cut_gdd_rel  = GDD(cut date) - GDD(local maturity date)
```

### 11.2 New signals worth one feature each

- **Post-harvest green-up:** NDVI rise within 20-90 days after the cut (cover crop into silage ground; winter forage in California planted mid-October to early December).
- **Previous-winter forage peak:** NDVI peak in February-April followed by a cut in March-April and corn emergence in May-June. In California this is close to a silage label by itself. The CDL double-crop classes 225, 226, 228 and 237 encode part of it.
- **Biomass removed:** silage takes 17-31 wet tons per acre off the field in one pass; grain harvest leaves the stover. The radar change at the cut should be far larger for silage.
- **Distance to a feeder, not only to a dairy.** In Texas "Silage is cut ... then delivered to a feed-lot"; in Idaho silage feeds "the dairy and beef cattle industry". Use dairies plus beef feedlots, with a decay over tens of miles.
- **Drought and frost context** (Drought Monitor class in July-August, first killing frost date) as the switch covariate.
- **Continuous corn** as a weak silage prior: "By raising corn for silage continuously or frequently in a crop rotation, higher quantities of manure can be applied" (Missouri G4591).

### 11.3 Rollup and reconciliation

- Publish three columns per county and state: grain, silage and **other / not harvested** (0.9-3.1% of planted nationally; 3.8% in Texas in 2025). The NASS identity is planted = grain + seed + silage + other.
- Treat last year's state silage acres as a prior with state-specific width: about +/-10-20% for WI, CA, NY, PA, MI, MN, ID; +/-25-75% for KS, NE, TX, SD, IA, MO, ND.
- Name the vintage you reconcile to (January summary versus later revisions).
- Validation that needs no extra labels: compare the model's cumulative distribution of silage cut dates with NASS weekly "corn harvested for silage" (Wisconsin 41% on 21 Sep 2025, 66% on 28 Sep 2025; Idaho) and the grain cut dates with "corn harvested" (Texas 68% on 6 Sep 2025, Kansas 19% on 20 Sep 2025). September 2025 is covered; 5 Oct to 16 Nov 2025 is missing.

### 11.4 What to say to the USDA statisticians

- "We classify the harvest fate the way your December survey defines it: whole plant chopped is silage; anything else harvested is grain, whatever its moisture or end use; the rest is 'all other purposes'."
- "Our clock is thermal. Silage is cut about 200 growing degree days before black layer; grain at least 150 after. That is why Texas in July and Wisconsin in October are both grain."
- "The fields we are least sure about are the ones you most want to know about: drought and frost salvage, high-moisture corn and earlage, and grain fields tilled or baled within days. They go to the review band with the reason attached."
- "In 2022 the June grain-acre forecast ended 3.2 million acres high and Kansas silage rose 75%. In 2025 it went the other way. This method sees the switch in September."
- Honest limits: the corn mask (the CDL for a given year is released in late February of the next year; the 2025 CDL was released 27 Feb 2026, after the 12 Jan 2026 annual summary); cloud gaps around the cut; no verified calendar yet for seed corn, popcorn and processing sweet corn.

---

## 12. Annotated bibliography

Opened and read [O]:

1. USDA NASS (2010). *Field Crops: Usual Planting and Harvesting Dates*, October 2010, text release. https://esmis.nal.usda.gov/sites/default/release-files/vm40xr56k/dv13zw65p/z603r1055/planting-10-29-2010.txt - state windows for corn for grain and corn for silage; definitions of begin (5%), most active (15-85%) and end (95%). Release list: https://esmis.nal.usda.gov/concern/publications/vm40xr56k
2. Lauer, J. (2000). "Predicting Corn Silage Harvest Dates", Wisconsin Corn Agronomy. https://corn.aae.wisc.edu/WCM/W081.aspx - 42-47 days after silking; 13 days before black layer; 0.5 points per day; county drydown rates.
3. UW Corn Agronomy (2006, updated 2014). "Corn Silage". https://corn.agronomy.wisc.edu/Management/L031.aspx - silage hybrids 5-10 RM days later than grain.
4. UW Corn Agronomy (2015). "High Moisture Corn, Ear Corn and Snaplage". https://corn.agronomy.wisc.edu/Management/L062.aspx - moisture targets, composition, "2 to 3 weeks earlier".
5. Nielsen, R.L. (2021). "Grain Fill Stages in Corn", Purdue. https://www.agry.purdue.edu/ext/corn/news/timeless/GrainFill.html - days after silking, GDD to maturity, kernel moisture by stage.
6. Nielsen, R.L. (2018). "Field Drydown of Mature Corn Grain", Purdue. https://agry.purdue.edu/ext/corn/news/timeless/graindrying.html - 0.8 to 0.4 points per day; black layer about 30%.
7. Ortez, O. and Lindsey, A. (2024). "Precipitation, Cooler Weather, and Corn Dry Down", Ohio State C.O.R.N. Newsletter 2024-35. https://agcrops.osu.edu/newsletter/corn-newsletter/2024-35/precipitation-cooler-weather-and-corn-dry-down - rates by month; 30 and 45 GDD per point.
8. Roth, G. and Heinrichs, J. "Corn Silage Production and Management", Penn State Extension. https://extension.psu.edu/corn-silage-production-and-management - moisture by silo type, milk line versus moisture, "little crop residue", cover crops.
9. Barnhart, S. and Elmore, R. (2008). "Deciding Between Grain and Forage Harvest for Late Maturing Corn", Iowa State. https://crops.extension.iastate.edu/cropnews/2008/10/deciding-between-grain-and-forage-harvest-late-maturing-corn
10. Whitney, T. (2023). "Pasture and Forage Minute: Corn Silage Harvest and Storage", UNL CropWatch. https://cropwatch.unl.edu/2023/pasture-and-forage-minute-corn-silage-harvest-and-storage-rejuvenating-thin-alfalfa/ - 45 days or 800 GDD after silking.
11. Stokes, B. and Hines, S. *Field Corn Harvest Recommendations for Idaho*, University of Idaho BUL 956. https://content-hub.uidaho.edu/api/public/content/deb8dac1d08c443cb83b10b4d63e8020?v=3a35e04e - Idaho calendar for silage, earlage, high-moisture corn and dry grain; 25% grain share.
12. *Crop Profile for Corn in Texas* (October 2003). https://ipmdata.ipmcenters.org/documents/cropprofiles/TXcorn.pdf - regional harvest windows; harvest moisture by region; silage to feedlots.
13. Frate, C., Marsh, B., Klonsky, K., De Moura, R. (2012). *Sample Costs to Produce Corn Silage, San Joaquin Valley - South, Double Cropped Planting*, UC Cooperative Extension. https://corn.ucdavis.edu/sites/g/files/dgvnsk14546/files/inline-files/220200.pdf
14. Mitchell, J., Klonsky, K., Stewart, D. (2015). *Sample Costs to Produce Silage Corn, Conservation Tillage, Northern San Joaquin Valley*, UC Cooperative Extension. https://coststudyfiles.ucdavis.edu/uploads/cs_public/a9/c5/a9c55e16-83cf-46f3-86b8-436ae2deb41f/15ctsilagecornsanjoaquinvalleyfinaldraftjuly20.pdf
15. Lundy, M., Leinfelder-Miles, M., Long, R., Klonsky, K., Wright, S., Stewart, D. (2015). *Sample Costs to Produce Field Corn in the Sacramento Valley and Northern San Joaquin Valley*, UC Cooperative Extension. https://corn.ucdavis.edu/sites/g/files/dgvnsk14546/files/inline-files/220198.pdf
16. UC ANR Committee of Experts on Dairy Manure Management (2005 revision). *Managing Dairy Manure in the Central Valley of California*. https://ucanr.edu/sites/groundwater/files/136450.pdf - winter forage planting dates and uptake timing.
17. Pettygrove, G.S., Putnam, D., Meyer, D. (2003). *Integrating Forage Production with Dairy Manure Management in the San Joaquin Valley*, final report, UC SAREP. https://sarep.ucdavis.edu/sites/g/files/dgvnsk9171/files/inline-files/integrating-forage-production-with-dairy-manure_0.pdf - 345,000 acres; 8% single versus 57% double or triple crop.
18. USDA NASS (2023). *NASS Survey Training, Agricultural Survey: December 1, 2023 (Crops APS)*, hosted by NASDA. https://www.nasda.org/wp-content/uploads/2023/10/2023-December-Agricultural-Survey-Enumerator-Training.pdf - definitions of grain, seed, silage and other purposes.
19. USDA NASS (12 Jan 2026). *Crop Production 2025 Summary*. https://esmis.nal.usda.gov/sites/default/release-files/795725/cropan26.txt - state grain and silage tables 2023-2025.
20. USDA NASS (12 Jan 2023). *Crop Production 2022 Summary*. https://esmis.nal.usda.gov/sites/default/release-files/k3569432s/9306v916d/69700b71k/cropan23.txt - state tables 2020-2022. Release list: https://esmis.nal.usda.gov/concern/publications/k3569432s
21. USDA NASS (April 2026). *Crop Production Historical Track Records*. https://esmis.nal.usda.gov/sites/default/release-files/795853/croptr26.txt - national planted, grain and silage series.
22. USDA NASS (30 Jun 2022). *Acreage*. https://esmis.nal.usda.gov/sites/default/release-files/j098zb09z/0z70b374s/7h14bw56w/acrg0622.txt - June 2022 planted and expected grain acres by state.
23. USDA ERS (15 Jan 2013). *Feed Outlook* FDS-13a. https://ers.usda.gov/sites/default/files/_laserfiche/outlooks/36575/34689_fds13a.pdf?v=77789 - 2012 silage area, yield and sorghum silage.
24. Good, D. (4 Sep 2012). "Questions About Corn Acreage", farmdoc daily. https://farmdocdaily.illinois.edu/2012/09/questions-about-corn-acreage.html
25. Kub, E. (15 Jan 2020). "'Final' Harvest Numbers: No Man Left Behind", DTN. https://www.dtnpf.com/agriculture/web/ag/news/article/2020/01/15/final-harvest-numbers-man-left-2
26. Red River Farm Network (21 Jan 2026). "Another Big Corn Crop Forecast in 2026" (Chad Hart). https://www.rrfn.com/2026/01/21/despite-fewer-acres-projected-corn-output-remains-high-in-2026/
27. USDA NASS weekly Crop Progress, national: week ending 6 Sep 2026 https://release.nass.usda.gov/reports/prog3626.txt ; 20 Sep 2026 https://release.nass.usda.gov/reports/prog3826.txt ; 18 Oct 2026 https://release.nass.usda.gov/reports/prog4226.txt
28. USDA NASS Wisconsin Crop Progress and Condition: 29 Sep 2025 https://www.nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2025/WI-Crop-Progress-09-29-25.pdf ; 5 Oct 2026 https://www.nass.usda.gov/sites/default/files/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/2026/WI-Crop-Progress-10-05-26.pdf ; index https://www.nass.usda.gov/Statistics_by_State/Wisconsin/Publications/Crop_Progress_&_Condition/index.php
29. USDA NASS Northwest (Idaho, Oregon, Washington) Crop Progress, week ending 29 Sep 2024. https://www.nass.usda.gov/sites/default/files/Statistics_by_State/Idaho/Publications/Crop_Progress_&_Condition/2024/CW0930.pdf
30. USDA NASS California Crop Progress: 9 Sep 2024 https://www.nass.usda.gov/sites/default/files/Statistics_by_State/California/Publications/Crop_Progress_&_Condition/2024/ca_20240909.pdf ; 21 Oct 2024 https://www.nass.usda.gov/sites/default/files/Statistics_by_State/California/Publications/Crop_Progress_&_Condition/2024/ca_20241021.pdf
31. USDA NASS. CropScape and Cropland Data Layer FAQ. https://www.nass.usda.gov/Research_and_Science/Cropland/sarsfaqs2.php - class codes; release dates; double-crop handling.
32. Stahl, L., Coulter, J., Sheaffer, C., Popp, E., Drewitz, N., Goplen, J. (reviewed 2025). "Harvesting drought-stressed corn for silage", UMN Extension. https://extension.umn.edu/corn-harvest/harvesting-drought-stressed-corn-silage
33. Dorn, T., Anderson, B., Rasby, R. (2008). *The Use and Pricing of Drought-Stressed Corn*, NebGuide G1865. https://extensionpubs.unl.edu/publication/g1865/2012/html/view
34. Tigner, R. (20 Jul 2012). "Feeding Value and Pricing Drought-Stressed Corn Silage", UNL CropWatch. https://cropwatch.unl.edu/feeding-value-and-pricing-drought-stressed-corn-silage-unl-cropwatch-july-20-2012
35. Milhollin, R. (revised 11/2025; original Massey and Horner 2003). *Pricing Corn Silage*, University of Missouri Extension G4591. https://extension.missouri.edu/media/wysiwyg/Extensiondata/Pub/pdf/agguides/crops/g04591.pdf
36. UW Division of Extension (2025). "Corn Silage Cutting Height Calculator: Background and Guide". https://dairy.extension.wisc.edu/articles/corn-silage-cutting-height-calculator-background-and-guide
37. Eck, K. and Brown, D. *Estimating Corn and Soybean Residue Cover*, Purdue AY-269-W. https://www.extension.purdue.edu/extmedia/AY/AY-269-W.pdf

Seen in search summaries only, not opened [S]:

- USDA NASS, "Corn Acreage Inclusions" (9 Aug 2019). https://data.nass.usda.gov/Education_and_Outreach/Understanding_Statistics/Corn%20Acreage%20Inclusions.pdf - not opened: HTTP 404.
- USDA NASS, 2022 Census of Agriculture, Appendix B. https://www.nass.usda.gov/Publications/AgCensus/2022/Full_Report/Volume_1,_Chapter_1_US/usappxb.pdf - not opened: HTTP 404.
- USDA NASS news release, 29 Jun 2012 (88.9M acres expected for grain). https://www.nass.usda.gov/Newsroom/printable/2012/06_29_12.pdf - not opened.
- USDA NASS Nebraska weekly report, September 2012 ("numerous drought damaged corn fields have been chopped for silage or baled for hay"). Not opened: HTTP 404.
- Penn State cutting-height trial averages (6.8 in versus 19.3 in), via a seed-company summary. Not opened.
- University of Florida EDIS on drought-stressed corn moisture. Not opened.

---

## 13. Open questions

1. Do published NASS "harvested for grain" acres include seed corn and earlage or snaplage, or do those sit in the remainder? One sentence from a NASS judge settles the reconciliation identity.
2. How were the "silage-like" and "grain-like" evaluation labels produced? If from farmer-reported intended use, the switchers are mislabeled by construction.
3. Seed corn, popcorn and processing sweet corn: harvest calendars, residue, and whether the provided CDL masks them cleanly (not verified here).
4. How common are stover baling, stalk grazing and fall tillage after grain by region, and how soon after the combine? This sets how long the residue signal can be trusted.
5. Which other states (New York, Pennsylvania, Michigan, Minnesota) publish weekly silage harvest progress, and is it reachable through the Quick Stats API for 2025?
