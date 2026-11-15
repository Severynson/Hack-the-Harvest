# Feature group `dairydist`: distance from each maize field to dairy farms

## What it is

These are field-level measures of how close each maize parcel is to dairy farms (plus beef farms and Climate TRACE cattle points, which are descriptive only). They follow the FIELD-FEATURE CONTRACT: `out/features.csv` and `out/meta.json`.

| Column | Role | Definition |
|---|---|---|
| `dairydist_d_dairy_km` | **pre-registered model feature** | km from the field's representative point to the nearest Quebec dairy site |
| `dairydist_n_dairy_18km` | **pre-registered model feature** | number of dairy sites within 18 km |
| `dairydist_rule_dairy_1p5km` | **pre-registered benchmark rule** | 1 when the nearest dairy site is within 1.5 km, else 0 |
| `dairydist_d_dairy_any_km` | descriptive | nearest dairy-coded unit, with or without buildings (land owned by a dairy farm) |
| `dairydist_d_beef_km`, `dairydist_n_beef_18km` | descriptive | the same two measures for beef-coded units with buildings |
| `dairydist_mb_sites_per_ha` | descriptive | local mass balance: kernel sum `exp(-d/5 km)` over dairy sites divided by the same kernel sum of maize hectares, cut at 25 km |
| `dairydist_ct_d_dairy_km`, `dairydist_ct_d_cattle_km`, `dairydist_ct_n_cattle_18km` | descriptive | Climate TRACE: nearest mature-dairy point, nearest cattle point of any type, and cattle points within 18 km |

A **dairy site** is a unit of the 2023 Quebec property assessment roll whose predominant-use code (CUBF, field `RL0105A`) is 8122 "Élevage de bovins laitiers" (NAICS 112120; legacy code 8150). The unit must also have a building value (`RL0403A`) above zero and a georeferenced point that was not rejected (`rejet = 0`). Beef units are CUBF 8121 (legacy 8161). The official CUBF list defines 8121 as beef cattle and the rearing of dairy replacement heifers.

## Why

- Silage is about two-thirds water. NDSU Extension says supply is "limited to farmers operating within a few miles of the new dairy", and Missouri Extension would not haul it past 20 miles. Manzone et al. (2020) put the economic limit at **18 km**. Source: `DOCS/research/gap_dairy_feedlot_points.md`, section 4.
- `DOCS/research/dairy_prior.md` gives silage-shed radii of 1.5 to 8 km for herds of 300 to 10,000 cows (section 4.3) and a 5 km kernel cut at 25 km (section 8.3). The 1.5 km rule threshold is the smallest radius in that table: 300 cows, with corn on 25% of the land.
- The same note warns that "distance to the nearest dairy" saturates where dairies are dense, and recommends cows per corn acre instead (sections 1, 7 and 9). The mass-balance column tests that recommendation, but descriptively only.

## The problem this solves, and what it cannot solve

The model trains in Quebec and is tested on one Maryland research farm, so the facility source has to cover Quebec.

- **Climate TRACE** (API v7, CC BY 4.0) does cover Quebec: 579 points in `CAN.11_1` (218 dairy, 361 beef). Every Quebec row has the same capacity for its type (117.08 head for dairy, 10,328.9 for beef). Those are imputed defaults, so the rows give locations only. The dairy points do sit on registered dairies: they are a median 0.67 km from a roll dairy site, and 81% are within 1 km.
- **The Quebec assessment roll** (MAMH, CC BY 4.0) is close to a census. It has 11,176 dairy-coded units with points; 9,382 have buildings and an accepted point. Quebec has a few thousand dairy farms, so one farm usually has several units. The open roll has no herd size.
- **Maryland has no comparable public registry.** Climate TRACE lists 39 Maryland dairies taken from state permit lists. The research farm's own herd is not among them, and the nearest listed dairy is 58.6 to 63.8 km from every BARC field. For the Quebec fields of this group the Climate TRACE distance never exceeds 44.4 km. Filling Maryland from Climate TRACE would therefore put it far outside the training range for a definition that does not match. So the roll-based columns, including both model features and the rule, are **NaN for Maryland** (`uncomputed` in `meta.json`), and the harness fills them with its median imputer. The Climate TRACE columns are built for Maryland.
- **Herd size ("head within 18 km") is UNCOMPUTED** for every dataset, for the reasons above.
- Not used: Statistics Canada Census of Agriculture counts by census subdivision (the roll is finer and complete), and OpenStreetMap (`dairy_prior.md` section 2.2 finds farm-building tags too sparse and untyped).

## Data sources (all public, no login)

- Assessment roll, 2023 georeferenced edition: https://donneesouvertes.affmunqc.net/role/ROLE2023_FGDB.zip (407 MB). The script downloads it once to `--cache-dir`, outside the repository. It reads the layers `B05EX1_B05V_UNITE_EVALN` (use code, values) and `rol_unite_p` (points, NAD83), joined on `id_provinc`. Only the 13,658 cattle-coded units with a point are kept, in `data/qc_role_2023_cattle_sites.csv`, with no addresses and no owner data. Dataset page: https://www.donneesquebec.ca/recherche/dataset/roles-d-evaluation-fonciere-du-quebec
- CUBF code list: https://www.quebec.ca/habitation-territoire/information-fonciere/evaluation-fonciere/manuel/codes-utilisation-biens-fonds (file `CUBF_MEFQ.xlsx`)
- Climate TRACE cattle operations: `https://api.climatetrace.org/v7/sources?subsectors=enteric-fermentation-cattle-operation&gadmId=...`, fetched 100 rows per request, one request per second.
  - Quebec side: Quebec plus Vermont, New Hampshire and Maine.
  - Maryland side: Maryland plus Virginia, Pennsylvania, Delaware, West Virginia and DC.
  - Cached in `data/climatetrace_cattle_<gadm>.csv`.
- Fields: geometry and ids from `data/labels/<dataset>.parquet`.
  - quebec_maize_2023 is limited to the 321 parcels of cell 79_515. The cell comes from `kernelag.s2_series.assign_cells`; 318 of those parcels have a Sentinel-2 series.
  - qc_regions_2023: all 2,889 parcels.
  - barc_2021_2023: all 44 field-years.
  - The mass-balance denominator uses every parcel of quebec_maize_2023 (44,753, grain and silage alike); it does not read their labels.
- Distances are computed in EPSG:32618 (UTM 18N), from each field polygon's representative point.

## How to run

```
.venv/Scripts/python.exe test_models/featureTests/dairy_distance/build.py            # downloads what is missing
.venv/Scripts/python.exe test_models/featureTests/dairy_distance/build.py --offline  # cached sources only
.venv/Scripts/python.exe -m pytest -q test_models/featureTests/dairy_distance/test_dairy_distance.py
```

- `--datasets` picks the datasets; the default is all three. A partial run replaces only those datasets' rows.
- `--refresh` downloads the sources again. `--cache-dir` sets where the 407 MB archive is kept.
- Once `data/` is filled, a run takes about 20 s and makes no network requests. The output is byte-identical across runs (features.csv sha256 `3d32eb51...`).

## Results

### Descriptive, Quebec labels only

These come from `out/quebec_class_summary.csv` and `out/quebec_by_cell.csv`. AUC treats silage as positive and higher values as silage. The hypothesis expects AUC below 0.5 for distances (closer means silage) and above 0.5 for counts.

| Scope | Feature | Median grain | Median silage | AUC |
|---|---|---|---|---|
| cell 79_515 (n=321) | `d_dairy_km` | 0.418 | 0.408 | 0.516 |
| cell 79_515 | `n_dairy_18km` | 430 | 412.5 | 0.475 |
| qc_regions (n=2,889, 16 cells) | `d_dairy_km` | 0.695 | 0.574 | 0.445 (median within-cell 0.413) |
| qc_regions | `n_dairy_18km` | 276 | 285 | 0.524 (within-cell 0.475) |
| qc_regions | `mb_sites_per_ha` (descriptive) | 0.027 | 0.035 | 0.586 (within-cell 0.513) |
| province, all 44,753 parcels | `d_dairy_km` | 1.036 | 0.669 | 0.374 |
| province | `n_dairy_18km` | 192 | 183 | 0.483 |

How to read this table:

- The rule calls 100% of cell 79_515 and 87% of qc_regions fields silage. Dairies are everywhere: the median nearest dairy site is 0.4 km in 79_515 and 0.65 km in qc_regions. This is the saturation `dairy_prior.md` warned about.
- Distance carries some signal across the province (AUC 0.374, which is 0.63 in the expected direction). Within one 10 km cell it is weak and inconsistent: per-cell AUCs for `d_dairy_km` run from 0.26 to 0.55, and the training cell 79_515 sits at 0.516, the wrong direction.

### Harness, run with only this group

The run used `harness.py --groups-dir <scratch with only dairy_distance> --out-dir <scratch>`, at harness sha256 `2b32279f...`, 2026-11-15T05:52Z. The base arm reproduced the reference matrices. The rows are copied to `out/harness_group_only.csv`.

| Evaluation | base bal. acc. | base+dairydist | Change [90% CI] | Rule |
|---|---|---|---|---|
| E1 qc_cell_blocks (79_515) | 0.704 | 0.718 | +0.014 [-0.021, 0.049] | 0.500 |
| E2 qc_regions_loco (decision) | 0.753 | 0.753 | -0.000 [-0.006, 0.006] | 0.499 |
| E3 Maryland (features NaN, imputed) | 0.839 | 0.839 | 0 | 0.500 |
| E3b Maryland, all Quebec cells | 0.854 | 0.854 | 0 | 0.500 |

Harness decision: base+dairydist **NO IMPROVEMENT SHOWN**; the rule is **WORSE**. Maryland cannot test this group, because the features are absent there by design.

## Limitations

- **A roll unit is not a farm, and its point is not the barn.** A farm with several units counts several times, and a unit's point is the centre of the lot. Use codes describe the owner's main activity, so rented land shows the owner's use. A farm whose main use is coded otherwise (for example a mixed farm) is not counted.
- **No herd size.** Counts stand in for demand.
- **Border edge.** 77 qc_regions fields (cell 74_500) lie within 18 km of the 45th parallel, and the roll has no US farms, so their 18 km counts can be low (`meta.json` → `checks.us_border_edge`).
- **Years differ.** The roll is the 2023 edition and matches the label year. The Climate TRACE snapshot is labelled 2025, and the Maryland labels are 2021 to 2023.
- **It does not transfer to the US.** No US state publishes a parcel-level farm-type register like Quebec's roll. In the US the options are state permit lists (large operations only), Climate TRACE, or county herd counts (`dairy_prior.md` section 8.2; group `dairy_balance` tests the county balance).
- `EPSG:32618` stretches distances by under 0.6% at the eastern edge of the Quebec data.
