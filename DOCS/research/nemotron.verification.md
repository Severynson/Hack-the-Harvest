# Verification: NVIDIA Nemotron agent layer findings

Checked 2026-11-14 by an independent fact-checker. Every source was opened directly (live APIs via curl, model cards, arXiv, GitHub API). WebSearch was unavailable (session search budget exhausted), so all checks are direct fetches of known URLs.

## Verdict table

| ID | Status | Note | URL checked |
|---|---|---|---|
| nemotron-1 | confirmed | Live listing returns 83 entries with all five ids, plus `nvidia/nemotron-nano-3-30b-a3b` and `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`. Card dates and sizes match (Super 2026-03-11, Ultra 2026-06-04, Lightning 2026-08-11, Super VL 2026-10-15, Bolt 2026-10-23, 8B/4B effective, 65,536 context). | https://integrate.api.nvidia.com/v1/models |
| nemotron-2 | confirmed | `nemotron-nano-9b-v2` and `:free` return `"endpoints":[]`; it is also absent from NVIDIA's own listing. Free Super VL, Ultra, Lightning endpoints match (context, output caps, 1-day uptime 99.4 / 96.7 / 98.3). Ultra 30-minute uptime was 100 at check time (volatile). Rate limits and DeepInfra Super price match. | https://openrouter.ai/api/v1/models/nvidia/nemotron-3.5-super-vl:free/endpoints |
| nemotron-3 | confirmed | Cards: function calling supported on all six; structured output not supported on Ultra and Nano 30B; no card documents parallel tool calls; Bolt says "single tool invocation per assistant turn". Caveats: Bolt context is 64K, not 1M; Super VL vision sampling is temperature 0.6. | https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b |
| nemotron-5 | corrected | Deprecation quote verified; Helix 145 stars, Python 3.12-3.14; Fabric 75 stars. Wrong: Fabric does have releases (v0.6.1, 2026-11-05). Helix is at 0.9.1, Relay at 0.11.1 (245 stars). Bash-agent tutorial date and quote verified; LangGraph is an optional bonus only. | https://github.com/NVIDIA/NeMo-Agent-Toolkit and https://api.github.com/repos/NVIDIA/NeMo-Fabric/releases |
| nemotron-8 | confirmed | v3 dated 2026-10-05; 408 questions. Table 3 matches all four models; Reflexion 40.0 to 64.5 with wrong answers 15.7 to 26.0; 14.2 / 9.6 failure shares; 1723.29 C footnote. Code-failure figures are sums of the paper's error categories, zero-shot only. | https://arxiv.org/html/2504.12110v3 |
| nemotron-10 | corrected | All numbers verified (CAAFE 0.798 to 0.822, 11/14; GPT-3.5 0.806, 6/14, "clearly worse"; 10 iterations; 4:43 min. LLM-FE 1.42 vs 3.47; 0.820 / 0.832 / 0.840; 0.626 / 0.587). "Only when" and "depends on a strong proposer" overreach: Llama-3.1-8B still gains. | https://ar5iv.labs.arxiv.org/html/2305.03403 and https://arxiv.org/html/2503.14434v3 |
| nemotron-11 | confirmed | Both quotes verified verbatim. README tally is 332 indices (12 radar vegetation plus 1 radar geology); the machine-readable JSON on main holds 280 (13 radar). "Literature does not control for this" rests on CAAFE's admission and is an inference. | https://arxiv.org/abs/1506.02629 |
| nemotron-12 | confirmed | PoT "around 12%" over 5 math + 3 financial datasets; FinanceBench 81% on 150 cases; Beel et al. (arXiv 2502.14297) 42% and hallucinated numbers; DSBench 34.12% of 466 tasks. All quotes match abstracts. | https://arxiv.org/abs/2211.12588 |

## Corrected claims

**nemotron-5.** NVIDIA NeMo Agent Toolkit (2,704 stars, last release v1.9.0 on 2026-09-10) is deprecated as of October 2026 with end of life by the end of 2026. Its successors are young, pre-1.0 and thinly adopted, but all three ship releases: NeMo Relay 0.11.1 (245 stars), NeMo Helix 0.9.1 (145 stars, Python 3.12-3.14 only), NeMo Fabric v0.6.1 (75 stars, released 2026-11-05).

**nemotron-10.** In CAAFE and LLM-FE, LLM-proposed features improve tabular models inside loops where each proposal is executed and kept only if a validation score improves; neither paper tests an unscored arm. Proposer strength matters (CAAFE: GPT-4 improved 11 of 14 datasets, GPT-3.5 only 6 of 14), but LLM-FE still gains with a small model (XGBoost accuracy 0.820 to 0.832 with Llama-3.1-8B, 0.840 with GPT-3.5).

## Missed by the researcher

1. Free-tier coverage is narrower than the line-up suggests. Nemotron 3 Super has no `:free` endpoint on OpenRouter (empty list), Bolt E4B is not on OpenRouter at all (404), and Nano 30B is paid only. Each free endpoint has a single provider (Nvidia), so there is no fallback. Paid endpoints mostly cap context at 262,144. https://openrouter.ai/api/v1/models
2. Counter-evidence on LLM feature engineering: Kuken, Purucker and Hutter (2024) find LLMs "are biased toward simple operators, such as addition", under-use grouping and aggregation, and that this can hurt predictive performance (4 LLMs, 27 datasets). https://arxiv.org/abs/2410.17787
3. UnivEARTH v3 shows that grounding moves failures rather than removing them. Injecting collection ids and band names cut Claude's MODIS syntax errors from 29.0% to 15.4% and raised VIIRS accuracy from 38.2% to 61.5%, but the VIIRS wrong-answer rate rose from 8% to 23.1%. Crashes become silent logic errors. https://arxiv.org/html/2504.12110v3
4. Super VL card inconsistencies that matter if images are sent: the Specifications section lists 262,144 tokens of context while the summary says 1M, and recommended sampling for vision is temperature 0.6 (1.0 is for text). https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b

## Overall

Six of eight findings are confirmed against live sources and every quoted number checked out. One factual error (NeMo Fabric does have releases) and one over-strong causal wording (feature discovery "only when" scored, "depends on" a strong proposer) need fixing before presenting. Endpoint uptime, star counts and free-tier limits are point-in-time values and should be re-checked before the demo.
