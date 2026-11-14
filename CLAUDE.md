- In the root folder I want you to implement the clean readable and interpretable version of the project, dirty code for new ideas exploration must be implemented.
- @DOCS/ includes relevant document with the problem statement from the hackathon and clues where to research;
- When you are asked to work in @autoresearch/ - don't write into CHANGELOG.md, becuase you will write experiments' results to @autoresearch/results.tsv. But otherwise - always report changes done in the project in CHANGELOG.md after every major implementation completion








    ## Token economy (strict)
    - Replies: terse bullets, no recaps, no restating the plan, no file dumps.
    - grep / read line ranges; never re-read an unchanged file.
    - Cap output: `| tail -n 30`, quiet flags. Print shapes, counts, `head(5)` — never full JSON/GeoJSON/Parquet.
    - Subagents: off by default. Allowed: one read-only reviewer at each phase gate to check acceptance criteria.

    ## Stack (fixed; adding a library needs a one-line reason in `docs/DECISIONS.md`)
    - Names: product and UI wordmark **Kernel**; Python package `kernelag` (avoids clashing with Jupyter "kernel" tooling); DB `kernel.duckdb`.
    - **Python 3.11 + uv:** earthengine-api, pandas, numpy, scipy, pyarrow, geopandas, shapely, pyproj, ruptures, scikit-learn, xgboost, shap, duckdb, requests, pyyaml, tqdm, pytest, ruff. Optional: cudf/cuml (RAPIDS), pystac-client + planetary-computer + stackstac (fallback).
    - **API:** fastapi, uvicorn, duckdb, openai (OpenAI-compatible client for Ollama / NVIDIA), pydantic, sse-starlette.
    - **Web (Node 20 + pnpm):** Vite, React 18, TypeScript strict, react-router, @deck.gl/core, layers, geo-layers, react, maplibre-gl, react-map-gl/maplibre, @observablehq/plot, d3-scale, d3-format, d3-time-format, @tanstack/react-query, zustand, @radix-ui (via shadcn), tailwindcss v4 + @tailwindcss/vite, clsx, tailwind-merge, cmdk, sonner, @number-flow/react, lucide-react (only icons the shadcn parts use, plus ≤ 8 more), @fontsource/ibm-plex-sans, @fontsource/ibm-plex-mono. Lint/format: biome.
    - **shadcn/ui:** copy in only `button, tabs, tooltip, dialog, slider, toggle-group, skeleton` (`pnpm dlx shadcn@latest add ...`). Then map its CSS variables (`--background, --foreground, --muted, --border, --ring, --primary`...) to our tokens and delete the rest. Dark only. No default shadcn look may survive.
    - **Banned:** Base UI (one primitive library only: Radix), Vaul (desktop app), Magic UI, Aceternity UI, RareUI, 21st.dev imports, MUI, Chakra, Ant, Bootstrap, DaisyUI, Framer Motion, Recharts, Chart.js, Streamlit, gradients, glassmorphism, glow, beams, sparkles, emoji, stock illustrations, lorem ipsum.

    ## Design (summary — full spec in BUILD_PROMPT §8)
    - Minimal, map-first, dark. Data is the decoration. One idea per screen.
    - Type: IBM Plex Sans (UI), IBM Plex Mono (all numbers, tabular). Sizes 12/13/15/20/28. Weights 400/500/600.
    - Tokens only (CSS vars in `web/src/styles/tokens.css`); no raw hex in components.
    - 4/8 px grid, radius 6, 1 px hairlines, no shadows except the drawer.
    - Motion 150–250 ms ease-out, only to show change; honor prefers-reduced-motion.
    - Copy: labels ≤ 6 words, sentence case, numbers over words.
    - AA contrast, visible focus rings, full keyboard use, color never the only cue.

    ## Design resources (user-supplied, curated)
    - **Use:** shadcn/ui https://ui.shadcn.com (restyled parts) · Radix https://www.radix-ui.com (primitives) · cmdk https://cmdk.paco.me (⌘K palette) · Sonner https://sonner.emilkowal.ski (toasts) · NumberFlow https://number-flow.barvian.me (hero numbers).
    - **Reference only, never import:** Beautiful UI https://beautifului.dev (agent thinking states, chat layout) · 21st.dev https://21st.dev (single patterns). Rebuild anything you borrow in our tokens.
    - **Skip:** Base UI, Vaul, Magic UI, Aceternity, RareUI: animated and flashy, or they duplicate Radix.
    - **Skills (P6 only, to save tokens):** `npx skills@latest add emilkowalski/skills`; run `break-ui` (worst-case data) and `review-animations` once each. Don't use `pick-ui-library`: the library choice is already made.

    ## Hard rules
    - Public data only. Never fabricate data or metrics; an uncomputed number shows "—".
    - Every number in the UI traces to `metrics.json`, the exported data files, or the DuckDB file. Nothing is typed by hand.
    - Pipeline stages are cached and resumable (skip if output exists; `--force` to redo).
    - The demo runs fully offline: static data + local LLM.
    - Organizer-provided data (labels, boundaries, region) overrides defaults; record the choice in `docs/DECISIONS.md`.

    ## Commands
    `make setup | check | fields | extract | features | labels | train | export | api | web | demo | test | bench`
