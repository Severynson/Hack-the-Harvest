# Radar for corn harvest: what Sentinel-1 and other public SAR can and cannot tell us

Research brief for team Kernel, Hack the Harvest. Written Saturday 14 Nov 2026.
Topic: Sentinel-1 (C-band) and other public synthetic aperture radar (SAR) for detecting corn harvest and describing the field afterwards.

Terms used below. VV and VH are the two Sentinel-1 channels (vertical transmit, vertical or horizontal receive). CR is the cross-ratio VH/VV; in decibels it is VH_dB minus VV_dB. Coherence is the similarity of the radar phase between two passes on the same track (0 to 1). A "look" is one satellite acquisition over a field. BBCH is the European crop-stage scale (83 = early dough, 89 = fully ripe, 99 = harvested).

## Bottom line

1. **Radar responds to the cut, optical responds to the browning.** Across 541 grain-maize parcels in the EU (2018), the Sentinel-1 VH/VV end-of-season date fell on harvest (BBCH 99) and came 18.6 days later, on average, than the NDVI end-of-season date, which fell at ripening (BBCH 83) [Me21]. This is direct support for our "dry-down days" signal.
2. **Use VH for the cut date and VH/VV for how green the crop was.** While corn ripens standing, VH stays on its plateau (about -16 dB) but VH/VV fades, because it tracks plant water [Kh19, Vr18]. A change-point on VH/VV or on coherence will fire early on grain corn.
3. **The harvest step is modest and weather can erase it.** The most we can expect is roughly 2 to 7 dB in VH and 3 to 6 dB in VH/VV. In a wet autumn the drop in VH was not observable against moist soil [Kh19]. Rain raises VV and VH together; frost or snow drops both by 4 to 6 dB.
4. **Coverage is thinner than the "6-day" headline.** Checked against the ASF archive today: central Iowa gets one satellite, ascending passes only, 12-day repeat on each of two tracks (19 looks in Aug-Nov 2025, 15 so far in Aug-Nov 2026). One Wisconsin point gets a single track: 9 looks in 3.5 months. Tulare County, California gets 50 to 60 looks over the same months. Six-day coherence pairs do not exist in the Corn Belt.
5. **After harvest, C-band is not a proven way to tell silage stubble from grain residue.** We found no study that tests it. Keep the residue signal on optical indices.
6. **Data access is not the bottleneck.** Earth Engine's Sentinel-1 collection is current to today; NASA's OPERA RTC-S1 product holds both seasons; Planetary Computer is current too but needs an account.
7. **NISAR L-band is public for the 2026 season, not for the 2025 harvest.** It is a strong "where this goes next" point, not something to build on tonight (files are about 6.5 GB each).

## How this was researched, and its limits

- 10 web searches ran before the shared search budget for this workflow was used up; two further searches were refused. Everything after that came from opening known URLs and from querying public data catalogs directly.
- About 50 pages and catalog queries were opened. Five open-access papers were read from their PDFs (Shang 2020, Kavats 2019, Khabbazan 2019, Vreugdenhil 2018, Kraatz 2021) and one conference deck (Jiao and McNairn 2023). Meroni 2021 and Mimić 2025 were read on PubMed Central.
- Numbers marked "fig-read" were read by eye off a published figure (roughly ±0.5 dB). Everything else is quoted from text or tables.
- Live catalog checks (all run 14 Nov 2026): ASF Search API for Sentinel-1 GRD scenes; NASA CMR for OPERA RTC-S1 and NISAR granules; Planetary Computer STAC search.
- Not opened (blocked or paywalled), so not used as evidence: Veloso 2017; Amherdt 2021; the 2026 corn and sunflower paper comparing Sentinel-1 with RADARSAT Constellation; the 2023 maize residue cover paper; Nasrallah 2019; Mandal 2020; the Sen4CAP algorithm document; the Earthdata forum notice on the OPERA outage. Details are in the bibliography.
- We did not find any US Corn Belt study that validates Sentinel-1 corn harvest dates, and none that classifies silage versus grain with radar. With only 10 searches that is a weak negative, not proof of absence.

## 1. What C-band radar sees in a corn field

### 1.1 Numbers through the season

| Stage | VH | VV | VH/VV (CR) | Source |
|---|---|---|---|---|
| Bare soil before emergence | about -19 to -22 dB (Austria, fig-read); about -23 to -24 dB parcel mean in May (Netherlands, fig-read) | VH is "around 12 dB lower than VV" from January to mid-May | about -12 dB (Austria); about -9.5 to -10 dB (Netherlands, fig-read) | [Vr18], [Kh19] |
| Leaf development (BBCH 12-30) | +7 dB | slight rise | +3.5 dB | [Kh19] |
| Stem elongation to tassel (40 cm to 2 m tall) | +4.0 dB | slight rise | +2.43 dB | [Kh19] |
| V3 to V10-V12 | rises | falls with soil moisture | -12 dB to -6 dB | [Vr18] |
| Saturation | plateau once leaf area index passes 2 to 3 and plant water passes 2 kg/m2 | | plateau | [Vr18], [Kh19] |
| Grain fill and ripening, crop standing (BBCH 75-89) | "relatively constant with an average of -16.2 dB" | rises from -9.5 to -7.5 dB | falls about 2 dB | [Kh19] |
| Ripening, crop standing (Austria, R6 reached about 9 Sep) | about -14 to -16 dB for 3 to 4 weeks after R6 (fig-read) | about -8 to -10 dB (fig-read) | decreases "during the ripening phase until harvest" | [Vr18] |
| Harvest | "abrupt decreases ... particularly in VH" | spread between parcels increases | drops | [Kh19], [Vr18] |
| After harvest, wet autumn (Netherlands 2017) | parcel mean about -16 to -17 dB, single parcels down to about -22 dB (fig-read) | about -7 to -8 dB (fig-read) | about -8.5 to -9 dB, from about -6 dB in July-August (fig-read) | [Kh19] |
| Frost or snow cover | drops about 5 to 6 dB (12 Dec 2017, fig-read) | drops about 5 dB (fig-read) | little change | [Kh19] |

Other quantities worth having:

- Sensitivity to plant water. In corn, CR explains 87% of the variance in total vegetation water content with an exponential model (48% linear). VH is the channel most tied to leaf area (R2 = 0.61). VV is the channel tied to soil moisture (R2 = 0.24), because 70 cm rows leave soil visible [Vr18]. Caveat: this rests on two fields of 2.3 and 2.6 ha over two seasons.
- Speckle is not the limit. "About 100 independent looks are available per hectare, resulting in a radiometric precision of 0.5 dB for a parcel of 1 ha" [Kh19]. Inference: a 16 ha (40 acre) field mean is good to about 0.1 dB, so the errors that matter are soil moisture, weather and timing.
- Instrument. Sentinel-1 noise floor "is specified to be -22 dB or better"; radiometric accuracy within 1 dB (3 sigma), stability 0.5 dB (3 sigma) [S1-wiki]. Inference: VH over smooth, dry, bare soil sits near the noise floor, so "VH below about -21 dB" means "nothing left standing" rather than a precise level.
- Coherence. Vegetated fields: below 0.3 to 0.4 with 6-day pairs; after harvest "generally above 0.6" [Kh19]. With 12-day pairs: crop fields 0.2 to 0.3 early and late in the season, forest about 0.2 [Sh20]. A pair that spans tillage or harvest drops below 0.2 [JM23].

### 1.2 Does backscatter separate standing dry corn from harvested corn?

Yes, with conditions. Optical cannot; radar can because the stalks, ears and leaves keep scattering after they turn brown.

- At scale: for 541 EU grain-maize polygons, the CR end-of-season date (50% of the decline) lined up with BBCH 99, harvest, to within -1.2 days against German phenology records. The NDVI date lined up with BBCH 83, ripening. CR was later than NDVI by 18.6 days on average (mean absolute difference 25.5 days, r = 0.52). For common wheat the gap was only 4.1 days [Me21].
- At field level: VH held at its plateau through ripening in both the Dutch and the Austrian studies, then dropped at harvest [Kh19, Vr18].
- In Ontario, a rule on total backscattered power ("span") found 18 of 21 corn harvests (85%) with 12-day Sentinel-1A data [JM23].

Where it fails:

- Wet soil. "The expected reduction in backscatter from the vegetation is not observable against the high and variable backscatter from the moist soil as precipitation events occur throughout the usual harvest period" [Kh19]. In that wet autumn the parcel-mean VH barely moved at harvest (fig-read) while CR still fell about 3 dB.
- Stubble and residue. After the cut, CR "may still respond to crop residues standing in the field such as maize stubble" [Me21].
- Tillage straight after harvest, rain on the acquisition day, frozen ground (section 3).

### 1.3 Does drying of the standing canopy lower the signal before any cut?

- **VH: barely.** Constant at -16.2 dB through BBCH 75 to 89 [Kh19]; flat to slightly rising for a month after R6 in Austria 2017 (fig-read) [Vr18].
- **VH/VV: yes.** It falls as plant water falls and as VV rises (more soil seen through a drying canopy). The Dutch parcels lost about 2 dB of CR in three to four weeks before harvest [Kh19]. In the dry year 2017, Austrian corn CR "has its peak in June and decreases steadily until October" [Vr18].
- **Coherence: yes.** "The coherence may increase steeply before harvesting", attributed to falling plant water and leaf area; the authors had to add a VH threshold to stop false triggers [Ka19].

So a change-point detector on VH/VV or coherence is biased early for grain corn. Run the detector on VH, and keep the VH/VV fade as a feature in its own right: it is the radar version of "fades out" versus "falls off a cliff".

One caution on that feature: part of the Dutch CR decline came from VV rising in a rainy September, not only from the plants drying. A rain-driven VV rise can fake a fade.

## 2. Harvest-detection methods and their published accuracy

| Study | Where, what, when | Data | Rule | Result |
|---|---|---|---|---|
| Kavats et al. 2019 [Ka19] | North Kazakhstan, cereals, 2018; 1,920 fields, 471,903 ha | Sentinel-1B, 12-day pairs | Step-like rise in VV coherence (algorithm parameter epsilon = 0.03), confirmed by VH thresholds of -21 dB and -25 dB; field counted harvested when 70% of its control points are | Mean absolute error 6.5 days, RMSE 8.0 days. Reference dates came from visual reading of optical images |
| Shang et al. 2020 [Sh20] | Northern Ontario, 2019; oats, barley, canola, soybean, spring wheat, peas (no corn); 77 fields for harvest | Sentinel-1, 12-day pairs | Coherence rise greater than 0.05 between consecutive pairs, and VH falls by more than 2 dB, or by less but ends below -19 dB | Harvest: 56% in the correct 12-day window, 88% within one extra cycle. Seeding: 85% and 91% |
| Khabbazan et al. 2019 [Kh19] | Flevoland, Netherlands, 2017; 335 maize parcels (a silage-maize site), plus beet, potato, wheat | Sentinel-1A+B, 6-day, one evening track | Coherence rises by more than 1.5 standard deviations of its vegetated-period value and reaches 0.5 | No maize accuracy given. "Harvest detection proved to be more difficult in all crops apart from wheat"; coherence was needed for beet and potato |
| Jiao, McNairn et al. 2023 [JM23] | Eastern Ontario, 2022; corn and soybean, weekly field visits | Sentinel-1A, 12-day, one track | Corn: span (total power, linear units) is down by more than 0.03 since the previous look and no more than 0.05 above its value on the first date. Tillage: coherence below 0.2 | Corn harvest 18 of 21 (85%) with span, 16 of 21 (76%) with Shannon entropy. Soybean 70%. Soybean tillage 100% when the harvest date is known, 75% without. "No adequate observations and image pairs to determine corn tillage" |
| Mimić et al. 2025 [Mi25] | Vojvodina, Serbia, 2018-2020; 214 maize samples | Sentinel-1 VV and VH, ascending and descending kept separate | Support vector machine and neural network for "harvested or not"; LSTM and random forest for the date | Maize detection accuracy 83.4 to 83.6% (precision 88.7 to 90.2%, recall 79.4 to 80.6%). Date: RMSE 11.4 to 13.3 days, mean absolute error 8.3 to 10.0 days |
| Meroni et al. 2021 [Me21] | EU-wide, 2018; 541 maize polygons | Sentinel-1 VH/VV from Earth Engine (power units), both pass directions; Sentinel-2 NDVI | Double hyperbolic tangent curve fit; end of season at 50% of the decline | CR end of season matches harvest (BBCH 99); 18.6 days later than NDVI on average |
| Amherdt et al. 2021 | Buenos Aires province, corn and soybean, 80 fields | Sentinel-1A+B coherence and VH | Not opened | Search summary only: accuracy "superior to 93%". Low confidence |
| 2026 paper, Int. J. Remote Sensing 47(5) | Corn and sunflower | Sentinel-1 (12-day) against RADARSAT Constellation (4-day) | Not opened | Search summary only: best R2 = 0.88 and RMSE = 7.86 days with the 4-day data. Low confidence |
| Sen4CAP (EU farm-subsidy monitoring) [EUCAP] | EU parcels | Sentinel-1 and Sentinel-2 | Weekly harvest markers; inputs include NDVI, coherence and the VV/VH amplitude ratio | Thresholds and accuracy not verified here |

What to take from the table:

- With 12-day data, expect timing errors of about 6 to 13 days and detection rates between 56% and 93%. Every study blames the revisit interval first.
- All of it is from Europe, Canada, Kazakhstan or Argentina. None is from the US Corn Belt, and none classifies silage against grain.
- Coherence is the strongest single harvest marker in the European work, but that work had 6-day pairs. With 12-day pairs it works less well and rain breaks it (section 3).
- The simple VH rule from Shang (drop of more than 2 dB, or ending below -19 dB) was tuned on small grains and soybean. Treat the numbers as starting values to re-tune on our labeled fields.

## 3. Confounders and how to normalize

| Confounder | What it does | Evidence | What to do |
|---|---|---|---|
| Rain and soil moisture | Raises VV and VH together; little effect on VH/VV. Lowers coherence | Heavy rain on 16 April "caused an abrupt increase in both VV and VH" with "little or no influence on the VH/VV ratio" [Kh19]. Upward spikes on days with 33.4 mm and 2.9 mm of rain; one rain-hit scene was thrown out [Sh20]. Rain shortly before a pass hid the post-harvest coherence jump [Ka19]. A whole track was dropped because rain fell on its dates [JM23] | Flag looks with rain in the previous 24 to 48 hours; never let one flagged look define a step |
| Frost and snow | Drops VV and VH by 4 to 6 dB, as large as a harvest | "Three sharp decreases in VV and VH on 22 January, 9 February and 12 December 2017 are the result of frost and snow cover" [Kh19]; low coherence under snow and during thaw [Sh20] | Drop looks with minimum temperature at or below 0 C or snow on the ground. Matters for late grain harvest in WI, MN, the Dakotas, NY |
| Dew | Wet leaves raise C-band backscatter | The Dutch team chose the evening pass "to minimize the influence of dew" (morning passes are near 06:50 local, evening near 18:20) [Kh19] | The Iowa and Wisconsin points have evening passes only, which helps. California and the Texas Panhandle also have a descending (morning) track; keep it separate |
| Tillage after harvest | Changes roughness, drops coherence, and gets logged as the harvest | "If, in the 12 day interval after harvesting, disk harrowing is done, the date of disking is registered as the date of harvesting" [Ka19]; coherence below 0.2 marks tillage [JM23] | Report a harvest bracket, not a day |
| Standing residue | Keeps coherence low after harvest, keeps CR up | "Harvest with substantial amount of residue left standing in the field; in which case, there is low coherence even after harvest" [Sh20]; [Me21] | Do not require a coherence rise |
| Row direction | Changes VV on ridged or row-structured bare soil; VH much less | Potato ridges: VV differed between two tracks, "cross-polarized backscatter is less sensitive to ridge geometry" [Kh19] | Prefer VH for levels; compare each field with itself |
| Incidence angle and track | The same field is seen at different angles from different tracks | Central Iowa is seen from track 165 in sub-swath IW1 (near range) and from track 63 in IW3 (far range) [CMR] | Build one series per track; see below |
| Missing scenes | 24-day holes | Track 63 over Iowa skipped 25 Aug 2025 and 27 Aug 2026 [ASF-API]. "Omission of a single image in a time series in the period of ripening can substantially reduce accuracy" [Ka19] | Carry the bracket width as an uncertainty |
| UTC dates | Off-by-one day | Iowa passes are at 00:05 to 00:13 UTC [CMR], which is the evening of the previous local day | Convert to local date before comparing with anything dated locally |
| Sensor change | 2025 Corn Belt scenes are Sentinel-1A; 2026 scenes are Sentinel-1D or 1C | [ASF-API]; for Sentinel-1D "further enhancements and fine-tuning of calibration are expected" [S1D-note] | Do not pool raw dB across years without checking the offset on stable targets |

Normalization, in order of effort:

1. **Per-track anomaly (do this).** For each field and each track, subtract the field's own median over the peak-canopy weeks (about 10 July to 10 August). This removes the incidence-angle, row-direction and soil offsets to first order, and lets tracks be merged on one timeline. Inference: this is our recommendation; the studies above simply used one track [Kh19, JM23] or kept directions separate [Mi25].
2. **Ratios.** "The effect of different incidence angles on backscatter coefficients is attenuated by the use of the VH/VV ratio" [Me21].
3. **Gamma-nought products.** OPERA RTC-S1 and Planetary Computer deliver terrain-flattened gamma-nought. Earth Engine delivers sigma-nought: "Radiometric Terrain Flattening is not being applied due to artifacts on mountain slopes" [GEE-guide]. On flat cropland the difference is a per-track offset, which step 1 already removes. Two studies on flat land skipped angle correction altogether [Sh20, Mi25].
4. **Angle regression.** Fit backscatter against local incidence angle across fields and correct to a reference angle. Inference: standard practice, but no opened source here quantifies it for corn; not needed tonight.

## 4. After harvest: silage stubble versus grain residue

What we were looking for: evidence that C-band backscatter or coherence separates short silage stubble on bare soil from grain stubble under a blanket of residue.

What we found is indirect:

- Residue left standing keeps coherence low after harvest [Sh20]. Inference: a bare silage field should become coherent sooner than a residue-covered grain field, but nobody has tested this, and the Corn Belt only has 12-day pairs.
- CR keeps responding to maize stubble after the cut [Me21].
- Tillage is detectable from coherence (below 0.2) in soybean; for corn there were too few observations to say [JM23].
- One paper on maize residue cover with radar plus optical data could not be opened. Its search summary says radar backscatter alone reached R2 of about 0.54 to 0.59 against residue cover, and about 0.81 to 0.84 when combined with an optical tillage index. Low confidence.
- L-band penetrates deeper and should see less of the residue layer and more of the soil and stalk bases. Inference only.

Conclusion: no published, direct evidence. Treat post-harvest radar as an exploratory feature set and keep "ground left" on optical residue indices.

Features worth letting the Index Scout test, because they are cheap once the table exists:

- Post-cut VH level and VV level (median of two or three dry, unfrozen looks).
- Regrowth: VH/VV rising by more than about 2 dB within 30 to 60 days of the cut. Inference: this would flag winter forage or a cover crop after silage, which is the double-crop fingerprint, without needing clear skies.
- A VV jump after the cut as a tillage or manure-incorporation flag.

## 5. What data exists for Aug-Nov 2025 and Aug-Nov 2026

### 5.1 Constellation timeline

| Satellite | Fact | Source |
|---|---|---|
| Sentinel-1A | Launched 3 April 2014. "Sentinel-1A operations will be terminated on June 29, 2026" | [S1-wiki], [ED-notice] |
| Sentinel-1B | "Unable to deliver radar data since 23 December 2021"; end of mission announced 3 August 2022 | [S1-wiki] |
| Sentinel-1C | Launched 5 December 2024; "fully operational since early May 2025". Moved 9 to 23 June 2026 (no acquisitions) to pair with 1D; resumed 24 June | [S1-wiki], [ED-notice] |
| Sentinel-1D | Launched 4 November 2025; data open to users from 17 April 2026; took over the Sentinel-1A observation plan | [S1D-note], [CDSE-news], [ED-notice] |
| Pattern | One satellite repeats every 12 days; two give "a 6 day exact repeat cycle". The new C+D pattern is shifted by one day relative to the old A+B pattern | [S1-wiki], [ED-notice] |

So the 2025 harvest season was flown by Sentinel-1A and 1C, and the 2026 season by Sentinel-1C and 1D.

### 5.2 What a field actually gets (ASF Search API, GRD scenes, IW mode, queried 14 Nov 2026)

| Point | Season window | Looks | Satellites | Tracks | Repeat on one track |
|---|---|---|---|---|---|
| Central Iowa (42.0 N, 93.6 W) | 1 Aug to 30 Nov 2025 | 19 | 1A only | 63 and 165, both ascending | 12 days; track 63 had two 24-day holes |
| Central Iowa | 1 Aug to 14 Nov 2026 | 15 dates (16 files) | 1D only | 63 and 165, both ascending | 12 days; track 63 had one 24-day hole |
| East-central Wisconsin (44.2 N, 88.5 W) | 1 Aug to 14 Nov 2026 | 9 | 1C only | 19, ascending | strictly 12 days |
| Texas Panhandle, Hartley Co. (35.9 N, 102.5 W) | 1 Aug to 14 Nov 2026 | 24 | 1D (16), 1C (8) | 5 and 78 ascending, 85 descending | 12 days; one 24-day hole |
| Tulare Co., California (36.2 N, 119.3 W) | 1 Aug to 29 Nov 2025 | 60 | 1A (29), 1C (31) | 64 and 137 ascending, 144 descending | 6 days |
| Tulare Co., California | 16 Jun to 13 Nov 2026 | 72 (50 of them from 1 Aug) | 1D (38), 1C (31), 1A (3) | same three | 6 days, a few 12-day holes |

Central Iowa look dates, 2025: 1, 8, 13, 20 Aug; 1, 6, 13, 18, 25, 30 Sep; 7, 12, 19, 24, 31 Oct; 5, 12, 24, 29 Nov.
Central Iowa look dates, 2026: 10, 15, 22 Aug; 3, 8, 15, 20, 27 Sep; 2, 9, 14, 21, 26 Oct; 2, 14 Nov.

Reading the table:

- Where two tracks overlap (Iowa), looks alternate 5 and 7 days apart, but from two different angles. Where only one track covers the field (the Wisconsin point), it is one look every 12 days.
- Same-track pairs, which is what coherence needs, are 12 days apart everywhere we checked outside California.
- Five points are a sample, not a map. Run the same query for every state we score.

### 5.3 Archives

| Archive | What it is | Verified today | Access |
|---|---|---|---|
| Earth Engine `COPERNICUS/S1_GRD` | Sigma-nought in dB, 10 m, VV, VH and an `angle` band. Border and thermal noise removed, calibrated, orthorectified; no terrain flattening | Catalog lists availability from 2014-10-03 to 2026-11-14T12:00:03Z; "The collection is updated daily"; "New assets are ingested within two days after they become available". The page does not name the satellites, so Sentinel-1C and 1D ingestion is not confirmed from the page | Earth Engine account. `COPERNICUS/S1_GRD_FLOAT` holds the same scenes as raw power |
| Planetary Computer `sentinel-1-rtc` | Terrain-corrected gamma-nought, float32, 10 m, cloud-optimized GeoTIFF | STAC search over central Iowa returned 63 scenes from 1 Aug 2025 to 14 Nov 2026, including Sentinel-1D scenes up to 14 Nov 2026. It lacks the 14 Oct 2026 scene that ASF has | "A Planetary Computer account is required to retrieve SAS tokens to read the RTC data" |
| NASA OPERA RTC-S1 (`OPERA_L2_RTC-S1_V1`) | Gamma-nought power, 30 m, one file set per radar burst: VV, VH, mask, local incidence angle; no speckle filter; Copernicus GLO-30 elevation; about 8 MB per GeoTIFF | 2025 season complete over central Iowa (19 dates, Sentinel-1A). 2026 season present with Sentinel-1D up to 14 Nov 2026 | Free Earthdata Login; ASF Vertex, `asf_search`, Earthdata Search. Covers all land north of 60 S; produced routinely since 1 January 2022, on demand back to 14 April 2016 |
| NASA OPERA CSLC-S1 | Coregistered complex images, 5 x 10 m, HDF5; the input for do-it-yourself coherence | Product page opened; coverage and latency are not stated on it | ASF |

OPERA latency, measured on the Iowa granules: 8, 14, 11, 25, 31 and 19 hours for the six most recent looks. The product guide says "generally available within 12 hours". But the Sentinel-1D products for the looks from 28 June to 10 August 2026 carry generation dates of 9 and 10 October 2026, and the 2 October look was generated on 12 October: they were backfilled. (We did not read the generation dates for the looks in between.) Inference: OPERA had no near-real-time Sentinel-1D output during the 2026 silage harvest. That is a reason not to promise OPERA as the operational feed.

## 6. NISAR and other public SAR

NISAR (NASA and ISRO):

- Launched 30 July 2025. 12-day exact repeat, with an "average revisit time of about 6 days" when both pass directions are counted. L-band wavelength 24 cm, S-band 9.4 cm. Science operations began in early January 2026. Data are free and open; L-band is served by the Alaska Satellite Facility, S-band (India and selected sites) by ISRO [NASA-NISAR].
- Releases [NISAR-docs]: sample (beta) products on 23 January and 27 February 2026 covering a subset from 17 October 2025 to 20 January 2026, "up to 8 acquisitions per track"; provisional products from 20 July 2026 for acquisitions from 17 June 2026; validated Level 0 to 2 products from 6 November 2026 for acquisitions from 21 October 2026. A permanent data gap runs from 27 July to 10 August 2026. Older data will be reprocessed in 2027.
- Products relevant to cropland [NISAR-prod]: GCOV, terrain-corrected gamma-nought covariance at 10, 20 or 80 m depending on bandwidth; GSLC and GUNW for coherence work; SME2 soil moisture at 200 m.
- Checked in NASA CMR for central Iowa: at least 22 GCOV acquisition dates between 17 June and 7 October 2026 (the listing was cut off there), on two ascending track-frames at 12-day repeat plus an irregular descending one, with no data from 27 July to 13 August. Files are about 6.2 to 6.7 GB each. The file names carry the polarization token "DHDH"; we did not verify what it denotes.
- Consequence: NISAR saw the 2026 harvest, not the August-September 2025 silage harvest. If our labels are for 2025, NISAR cannot be evaluated against them.

Why L-band matters for corn [Kr21]:

- In a Manitoba test of the planned NISAR crop-area method (the temporal coefficient of variation of backscatter), L-band PALSAR-2 was "far more accurate over corn (96.6%) than Sentinel-1 (73.4%)", while Sentinel-1 was better over soybean (85.6% against 57.0%). Overall Sentinel-1 scored 83.5% and PALSAR-2 73.2%.
- The stated reason: C-band saturates on high-biomass corn, while "L-band backscatter does not saturate until greater biomass accumulation" and is "scattered deeper within the canopy".
- NISAR's requirement is crop area at 1 hectare resolution with accuracy above 80%.
- Inference: the L-band contrast between standing stalks and a cut field should be larger and less weather-prone than at C-band. No opened source measures L-band at corn harvest.

Other public SAR:

- ALOS-2 PALSAR-2 ScanSAR in Earth Engine (`JAXA/ALOS/PALSAR-2/Level2_2/ScanSAR`): an L-band radar; 25 m, terrain-flattened gamma-nought, HH and HV (which polarizations exist varies by scene), listed from 4 August 2014 to 18 October 2026. Conversion: gamma0_dB = 10 x log10(DN squared) - 83.0. The page states neither the revisit nor the coverage over the US, so check a Corn Belt point before counting on it [PALSAR-GEE].
- RADARSAT Constellation, SAOCOM and commercial X-band open-data programs were not researched in this session.

## 7. Recipe: per-field Sentinel-1 time series for 10,000+ fields

### 7.1 Extraction in Earth Engine (primary route)

Sketch, not run in this session.

```python
import ee
ee.Initialize(project="YOUR_PROJECT")

fields = ee.FeatureCollection("projects/YOUR_PROJECT/assets/fields")  # needs a field_id property
fields = fields.map(lambda f: f.buffer(-20))                           # stay off headlands and roads

s1 = (ee.ImageCollection("COPERNICUS/S1_GRD_FLOAT")                    # power units, not dB
      .filterBounds(fields.geometry())
      .filterDate("2025-06-01", "2025-12-01")
      .filter(ee.Filter.eq("instrumentMode", "IW"))
      .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
      .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")))

def per_image(img):
    stats = img.select(["VV", "VH"]).reduceRegions(
        collection=fields.filterBounds(img.geometry()),
        reducer=ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True),
        scale=10, tileScale=4)
    return stats.map(lambda f: f.setGeometry(None).set({
        "t_utc": img.date().format("YYYY-MM-dd'T'HH:mm"),
        "track": img.get("relativeOrbitNumber_start"),
        "pass": img.get("orbitProperties_pass"),
        "platform": img.get("platform_number")}))

table = s1.map(per_image).flatten().filter(ee.Filter.notNull(["VV_mean"]))
ee.batch.Export.table.toDrive(
    collection=table, description="s1_field_ts", fileFormat="CSV",
    selectors=["field_id", "t_utc", "track", "pass", "platform",
               "VV_mean", "VH_mean", "VV_count"]).start()
```

Notes:

- Average power, then convert to dB. `COPERNICUS/S1_GRD` is already in dB, and a mean of dB values is not the dB of the mean. Meroni et al. used the FLOAT collection for this reason.
- Keep `track`. It is the key for every baseline and every same-geometry comparison.
- First sanity check: `s1.aggregate_histogram("platform_number")`. Over the Corn Belt we expect only "A" in 2025 and "D" or "C" in 2026. If 2026 comes back empty, switch to the fallback.
- Shrink polygons inward. Shang shrank by 50 m; our 20 m is a compromise for smaller fields. Drop looks where `VV_count` is below about 50 pixels.
- Split the export by state or by month so several tasks run in parallel.

### 7.2 Fallback: OPERA RTC-S1 from NASA (no Earth Engine needed)

Sketch, not run in this session.

```python
import earthaccess, rasterio
from rasterio.mask import mask

earthaccess.login()                                  # free Earthdata Login
grans = earthaccess.search_data(
    short_name="OPERA_L2_RTC-S1_V1",
    bounding_box=(-93.9, 41.8, -93.3, 42.2),
    temporal=("2025-06-01", "2025-11-30"))
fs = earthaccess.get_fsspec_https_session()

for g in grans:                                      # one granule = one burst on one date
    for url in g.data_links():
        if url.endswith(("_VV.tif", "_VH.tif")):
            with fs.open(url) as fh, rasterio.open(fh) as src:
                # reproject field polygons to src.crs once per burst, then:
                # arr, _ = mask(src, [geom], crop=True, filled=False); arr.mean()
                pass
```

Notes:

- File names look like `OPERA_L2_RTC-S1_T165-352508-IW1_20261114T000504Z_20261114T080551Z_S1D_30_v1.0_VV.tif`: burst ID (track, burst, sub-swath), acquisition time, generation time, satellite, 30 m.
- Some looks have two files with different generation times. Keep the newer one.
- Use the burst ID's track number as the `track` key.
- Values are gamma-nought power: average, then take 10 x log10.
- 30 m pixels: a 4 ha field holds about 45 pixels before the inward buffer, so drop fields under about 2 ha.
- The mask file marks layover and shadow; on flat cropland it rarely matters.

### 7.3 Cut detection for one field

1. Convert to dB: `VV_dB`, `VH_dB`, and `CR_dB = VH_dB - VV_dB`.
2. Per track, take the peak-canopy median over 10 July to 10 August (shift earlier in Texas and the South) and subtract it. Call the results `aVH` and `aCR`. Merge tracks on one timeline.
3. Attach weather to each look: rain in the previous 48 hours and minimum temperature (gridMET, PRISM or ERA5-Land; Kavats used GPM IMERG). Drop frozen looks. Flag wet looks; 5 mm is our starting threshold, to be tuned.
4. Walk forward from 1 August. The cut is the first look where `aVH` is at or below -2 dB, or `VH_dB` is at or below -19 dB, and the next valid look agrees. Both numbers come from Shang's rule on other crops; re-tune them on the labeled fields, for example with a one-split tree.
5. Report a bracket: (last look still high, first look low]. Store the midpoint and the width in days. Intersect with the optical bracket (last clear green or brown scene, first clear scene showing soil or residue) when there is one.
6. If no look qualifies by the end of the series, label the field "radar-undetected". It is either still standing or masked by wet soil. Do not guess.

### 7.4 Features and formulas

| Feature | Formula | Expected for silage / grain | Basis |
|---|---|---|---|
| Cross-ratio | `CR_dB = 10*log10(VH/VV) = VH_dB - VV_dB`; corn runs from about -12 dB (bare) to about -6 dB (peak) | | [Vr18] |
| Radar vegetation index, dual-pol | `RVI = 4*VH / (VV + VH)` in power units | carries the same information as CR | Common form; not checked against an opened source |
| Cut bracket and width | section 7.3 | silage late Aug to Sep, grain Oct to Nov in the Midwest; width 5 to 12 days | [Sh20], [ASF-API] |
| Cut date relative to county median, in growing-degree days | as in our plan, using the bracket midpoint | early / late | plan v2 |
| Radar green-at-cut | `aCR` at the last look before the bracket (CR there minus peak CR) | near 0 dB / about -1 to -3 dB | Inference from [Vr18], [Kh19]; untested on silage versus grain |
| Fade duration | days from `aCR` first staying below -1 dB (smoothed) to the cut midpoint | about 0 / weeks | Inference from [Vr18], [Me21] |
| Dry-down days | cut midpoint minus the date NDVI falls through 50% of its seasonal decline | about 0 / +19 days on average in EU grain maize, widely spread | [Me21]; the silage value is inference |
| Step size | `aVH` after minus before; same for CR | larger when cut green / smaller after a fade | Inference |
| Post-cut levels | median `VH_dB` and `VV_dB` over 2 to 3 dry, unfrozen looks | unknown | exploratory |
| Regrowth flag | CR up by more than 2 dB within 30 to 60 days after the cut | winter forage or cover crop after silage | Inference |
| Coherence (if ever built) | `gamma = abs(mean(s1 * conj(s2))) / sqrt(mean(abs(s1)**2) * mean(abs(s2)**2))` | below 0.3 to 0.4 vegetated; above 0.5 to 0.6 bare and undisturbed; below 0.2 across a tillage or harvest | [Kh19], [JM23] |

### 7.5 Run time and response time

Inference, not measured:

- 10,000 fields times 20 to 70 looks is 0.2 to 0.7 million rows. As a handful of parallel Earth Engine table exports this is typically tens of minutes to a couple of hours. The OPERA route with ranged reads is similar if requests run in parallel. The pandas step takes seconds.
- Coherence would need complex (SLC or CSLC) processing for every pair. That does not fit in a night.
- Response time for one field = wait for the first low look (up to 5 to 12 days after the cut) + one confirming look (another 5 to 12 days) + archive latency (about 1 to 2 days). That is roughly one to two weeks in Iowa, up to about four weeks on a single-track field, and a few days in California.

## 8. What this means for Kernel

Changes to plan v2:

1. **Signal 1, cut date: keep it, but as a bracket from VH.** Detect on VH per track, confirm on the next look, and carry the bracket width (5 to 12 days depending on the state) into the uncertainty. That is precise enough to place a field against the county median, since silage and grain dates differ by weeks. It is not precise enough to claim harvest weeks.
2. **Signal 2, green-at-cut: add a radar twin.** When clouds hide the last optical scene, the VH/VV level at the last look before the cut still says whether the plant was wet or dry, because VH/VV tracks plant water in corn (R2 = 0.87 in one small study). This speaks to USDA's "clouds hiding the harvest week" trap. It is a hypothesis until the labeled set confirms it.
3. **Signal 3, dry-down days: this is our best-supported radar plus optical signal.** Meroni et al. measured the same gap on 541 grain-maize parcels: radar end of season at harvest, optical end of season at ripening, 18.6 days apart on average. Cite it. Also say that the spread is wide (mean absolute difference 25.5 days) and that nobody has measured it for silage.
4. **Signal 4, ground left: keep it optical.** There is no evidence that C-band separates silage stubble from grain residue. Let the Index Scout test post-cut VH, VV and the regrowth flag, and keep them only if they add lift.
5. **Drop coherence from the build.** Corn Belt pairs are 12 days apart, rain breaks them, and the processing does not fit the time. Mention it as future work, with California (6-day pairs) as the place to start.
6. **Use NISAR as the "where this goes" slide.** Public L-band over the Corn Belt since June 2026, better than C-band on corn in the one comparison we read, too heavy for tonight, and absent for the 2025 harvest.

What to say to the USDA statisticians:

- Each radar number has a physical meaning: VH is how much plant is standing; VH/VV is how wet that plant is.
- The evidence is European and Canadian. We found no Corn Belt validation in the literature, so the labeled set is our validation, and we report precision, recall and false-positive rate by revisit class (5 to 7 day fields against 12-day fields).
- Where it fails: wet soil at harvest, frozen ground, tillage within days of harvest, single-track areas, fields under about 2 ha.
- Inference worth stating: a field still standing in mid-October with a faded VH/VV is already "not silage", so the silage estimate can close in October, about three months before the January report, without waiting for the grain harvest to finish.

## 9. Annotated bibliography

Opened and read:

- **[Me21]** Meroni, d'Andrimont, Vrieling, Fasbender, Lemoine, Rembold, Seguini, Verhegghen (2021). Comparing land surface phenology of major European crops as derived from SAR and multispectral data of Sentinel-1 and -2. Remote Sensing of Environment 253, 112232. https://pmc.ncbi.nlm.nih.gov/articles/PMC7841528/ — EU-wide, 2018, parcels from the LUCAS survey. The source of the 18.6-day radar-after-optical gap for grain maize. The first 100,000 characters of the page were read; the discussion section was not fully reached.
- **[Kh19]** Khabbazan et al. (2019). Crop Monitoring Using Sentinel-1 Data: A Case Study from The Netherlands. Remote Sensing 11(16), 1887. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-11-01887/article_deploy/remotesensing-11-01887.pdf — 335 maize parcels at a silage-maize site, 6-day data. Best source for stage-by-stage dB values, the wet-soil failure, and the coherence rule.
- **[Vr18]** Vreugdenhil et al. (2018). Sensitivity of Sentinel-1 Backscatter to Vegetation Dynamics: An Austrian Case Study. Remote Sensing 10(9), 1396. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-10-01396/article_deploy/remotesensing-10-01396.pdf — In-field plant water measurements for corn. Source of "CR tracks plant water". Only two corn fields. The text and Table 1 disagree on the corn harvest dates.
- **[Sh20]** Shang et al. (2020). Detection of Crop Seeding and Harvest through Analysis of Time-Series Sentinel-1 Interferometric SAR Data. Remote Sensing 12(10), 1551. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-12-01551/article_deploy/remotesensing-12-01551.pdf — Agriculture and Agri-Food Canada. Clear rule, honest 56% result, good discussion of rain, snow, residue and tillage. No corn among the validated fields.
- **[Ka19]** Kavats, Khramov, Sergieieva, Vasyliev (2019). Monitoring Harvesting by Time Series of Sentinel-1 SAR Data. Remote Sensing 11(21), 2496. https://mdpi-res.com/d_attachment/remotesensing/remotesensing-11-02496/article_deploy/remotesensing-11-02496.pdf — Coherence step plus VH thresholds over 1,920 fields. Source of the pre-harvest coherence rise and the tillage confusion.
- **[JM23]** Jiao, McNairn, van der Kooij, Halstead, Davidson, Joosse (2023). Monitoring crop harvest and tillage using Sentinel-1 coherence change detection and polarimetric parameters. ESA PolInSAR and BIOMASS workshop slides. https://polinsar-biomass2023.esa.int/iframe-agenda/files/141-PolInsar_presentation_Xianfeng_Jiao.pdf — The only corn-specific harvest accuracy we could open (85%), from the Canadian government group. Slides, not a paper; small sample.
- **[Mi25]** Mimić et al. (2025). Machine Learning-Based Harvest Date Detection and Prediction Using SAR Data for the Vojvodina Region (Serbia). Sensors. https://pmc.ncbi.nlm.nih.gov/articles/PMC11990955/ — Maize-specific machine-learning results; date errors of 8 to 13 days.
- **[Kr21]** Kraatz et al. (2021). Comparison between Dense L-Band and C-Band SAR Time Series for Crop Area Mapping over a NISAR Calibration-Validation Site. Agronomy 11(2), 273. https://mdpi-res.com/d_attachment/agronomy/agronomy-11-00273/article_deploy/agronomy-11-00273.pdf — L-band against C-band by crop; includes USDA ARS authors.

Agency and catalog pages opened:

- **[S1-wiki]** Copernicus SentiWiki, S1 Mission. https://sentiwiki.copernicus.eu/web/s1-mission
- **[S1D-note]** Sentinel-1D User Data Opening from 17 April 2026 (16 Apr 2026). https://sentinels.copernicus.eu/-/sentinel-1d-user-data-opening-from-17-april-2026
- **[CDSE-news]** Sentinel-1D user data opening and future plans (2 Apr 2026). https://dataspace.copernicus.eu/news/2026-4-2-sentinel-1d-user-data-opening-and-future-plans
- **[ED-notice]** NASA Earthdata: Sentinel-1D Data Are Available for Download at ASF DAAC (June 2026). https://www.earthdata.nasa.gov/data/alerts-outages/sentinel-1d-data-available-download-asf-daac
- **[GEE-cat]** Earth Engine catalog, Sentinel-1 SAR GRD. https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD
- **[GEE-guide]** Earth Engine guide, Sentinel-1 algorithms. https://developers.google.com/earth-engine/guides/sentinel1
- **[PC-STAC]** Planetary Computer STAC collection `sentinel-1-rtc` and a search over central Iowa. https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc
- **[OPERA-guide]** ASF, OPERA RTC for Sentinel-1 Product Guide. https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/
- **[OPERA-CSLC]** JPL, OPERA CSLC product suite. https://www.jpl.nasa.gov/go/opera/products/cslc-product-suite/
- **[ASF-API]** ASF Search API, for example https://api.daac.asf.alaska.edu/services/search/param?platform=Sentinel-1&processingLevel=GRD_HD&beamMode=IW&intersectsWith=POINT(-93.6%2042.0)&start=2026-08-01T00:00:00Z&end=2026-11-14T23:59:59Z&output=csv — change the point and dates to repeat the checks in section 5.2.
- **[CMR]** NASA CMR granule search, for example https://cmr.earthdata.nasa.gov/search/granules.csv?short_name=OPERA_L2_RTC-S1_V1&bounding_box=-93.61,41.99,-93.59,42.01&temporal=2025-08-01T00:00:00Z,2025-11-30T23:59:59Z&page_size=80&sort_key=start_date — the same pattern with `short_name=NISAR_L2_GCOV_PROVISIONAL_V1` and `NISAR_L2_GCOV_V1` gave the NISAR listing.
- **[NISAR-docs]** ASF NISAR Data User Guide, Available NISAR Data. https://nisar-docs.asf.alaska.edu/availability-overview/
- **[NISAR-prod]** ASF NISAR Data User Guide, NISAR Data Products. https://nisar-docs.asf.alaska.edu/products-overview/
- **[NASA-NISAR]** NASA, NISAR mission overview. https://science.nasa.gov/mission/nisar/mission-overview/
- **[PALSAR-GEE]** Earth Engine catalog, PALSAR-2 ScanSAR Level 2.2. https://developers.google.com/earth-engine/datasets/catalog/JAXA_ALOS_PALSAR-2_Level2_2_ScanSAR
- **[EUCAP]** EU CAP Network, markers database (Sen4CAP-derived). https://eu-cap-network.ec.europa.eu/markers-database_en — Confirms the inputs (NDVI, coherence, VV/VH ratio) and weekly harvest markers; gives no thresholds.
- Mullissa et al. (2021), Sentinel-1 analysis-ready data in Earth Engine, code repository. https://github.com/adugnag/gee_s1_ard — Border-noise correction, speckle filters and terrain normalization for Earth Engine, if we want them later. Only the README was read.

Not opened; do not cite these on our slides without reading them first:

- Veloso et al. (2017), Remote Sensing of Environment 199, 415-426. Not opened: the HAL copy is behind bot protection and ScienceDirect returned 403. Known here only through [Kh19], which says it showed that for barley and maize NDVI and VH/VV agreed well with green area index and fresh biomass.
- Amherdt et al. (2021), Int. J. Remote Sensing 42(19), 7313-7331, doi 10.1080/01431161.2021.1957176. Not opened: publisher 403; the repository page did not render.
- Harvest date estimation over corn and sunflower fields using Sentinel-1 and RADARSAT Constellation Mission data, Int. J. Remote Sensing 47(5), 2026. https://www.tandfonline.com/doi/full/10.1080/01431161.2026.2612904 — Not opened: 403.
- Improving maize residue cover estimation with the combined use of optical and SAR remote sensing images. https://www.sciencedirect.com/science/article/pii/S2095633923001004 — Not opened: 403.
- Nasrallah et al. (2019), wheat phenology with Sentinel-1; Mandal et al. (2020), dual-pol radar vegetation index. Not searched for before the search budget ran out. Both concern crops other than corn.
- Sen4CAP algorithm document with the harvest-marker thresholds. Not found.
- Earthdata forum notice on the planned OPERA outage. https://forum.earthdata.nasa.gov/viewtopic.php?p=26213 — Not opened: 404. The outage is inferred from granule generation dates instead.
