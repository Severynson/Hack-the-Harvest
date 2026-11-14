# DOCS/coord: how agents coordinate through git

The rules are in the "Multi-agent protocol v1" section of the root `CLAUDE.md`. This folder holds the state.

| Path | Writer | What it holds |
| --- | --- | --- |
| `tasks/<id>.md` | the lead, or an agent using its own prefix `T-<AGENT_ID>-<n>` | One task: paths, dependencies, "Done when", status |
| `status/<AGENT_ID>.md` | that agent only | Append-only ledger: claims, progress, blockers |
| `handoff/<UTC>-<AGENT_ID>-<slug>.md` | that agent only, never edited afterwards | State, next step, exact resume commands, risks |
| `handshake/<AGENT_ID>.md` | that agent only | Handshake hello and acknowledgements |
| `handshake/ROLLCALL.md` | everyone, one line each | Proves concurrent appends merge cleanly |

A task is taken when branch `task/<id>` exists on origin. See who holds what:

```bash
git fetch --all --prune --quiet
git for-each-ref --sort=-committerdate --format='%(committerdate:relative)%09%(refname:short)%09%(authorname)' refs/remotes/origin/task
```
