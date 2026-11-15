# Decisions
One line per decision, newest at the bottom: `- <UTC> [AGENT_ID] <decision>. Why: <reason>`

- 2026-11-15T00:53Z [cc-varun] Scoring year is 2025; nothing is fitted, tuned or selected on 2025 values. Why: the organizers posted the 2025 state grain and silage acres as the table results are evaluated against (DOCS/research/data_sources.md, section 0.4).
- 2026-11-15T00:53Z [cc-varun] Add library odc-stac (with pystac-client and planetary-computer). Why: the organizer starter notebook and the team's Keeboh notebook already load Sentinel-2 this way, it needs no key, and it is installed on Keeboh.
- 2026-11-15T00:53Z [cc-varun] Field-level training labels come from Quebec's declared-parcel database; the organizers' 44 Maryland field-years are test only. Why: 12 silage field-years on one farm cannot train a model without overfitting.
- 2026-11-15T00:53Z [cc-varun] Per-field Sentinel-2 series are pulled at 20 m with a one-pixel inner buffer. Why: the moisture and residue bands are 20 m native, and it keeps each download small enough for the 10 GB Keeboh workspace.
