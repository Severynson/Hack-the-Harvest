# Nemotron agent layer: current models, tooling, precedents and a design that does real work

Researched Saturday 2026-11-14 for team Kernel (Hack the Harvest). Scope: the NVIDIA Nemotron prize track ("Use Nemotron Beyond a Chatbot") and the agent layer of plan v2.

**How this was researched.** The shared WebSearch budget for this run was already exhausted, so no search-engine queries were possible. Everything below comes from about 115 pages opened directly by URL (NVIDIA model cards and docs, the live NVIDIA and OpenRouter model APIs, GitHub READMEs, arXiv abstract and full-text pages, vendor blogs) and from links those pages contained. Consequences: (1) coverage of "past Nemotron prize tracks" is thin, because Devpost returned HTTP 403 and I could not search for winner write-ups; (2) every claim marked "title only" or "not opened" is a lead, not evidence. Pages were read through a summarising fetch tool, so long quotes are paraphrased; numbers were copied as returned.

Conventions: "Inference:" marks my reasoning, not a source statement. Confidence is high / medium / low. Sibling reports referenced but not re-verified by me: `brev_ops.md` (GPU sizing, local serving), `models.md` (multiple-comparison caution, VLM-as-labeler evidence).

---

## 0. Bottom line

1. **The 2025 workshop material is stale.** The official "Report Generator" and "RAG agent" tutorials both hard-code Nemotron Nano 9B v2. On OpenRouter today `nvidia/nemotron-nano-9b-v2` and `nvidia/nemotron-nano-9b-v2:free` return an empty endpoint list, and the id is absent from today's `integrate.api.nvidia.com/v1/models` listing. Copy the architecture, not the model string.
2. **Current line-up (Nov 2026):** Nemotron 3 Ultra (550B/55B active), Nemotron 3.5 Super VL (120B/12B, text + image + video), Nemotron 3 Super (120B/12B), Nemotron 3.5 Lightning (30B/3B), Nemotron 3 Nano (30B/3.5B), Nano Omni, Bolt E4B. All expose OpenAI-style tool calling.
3. **Free endpoints that work today on OpenRouter:** `nvidia/nemotron-3.5-super-vl:free` (tools, every `tool_choice` mode, `response_format` and `structured_outputs`, 1M context), `nvidia/nemotron-3-ultra-550b-a55b:free` (tools, no structured output), `nvidia/nemotron-3.5-lightning:free` (tools, no structured output). Free limits: 20 requests/minute; 50 requests/day, or 1,000/day once 10 credits have been bought.
4. **NVIDIA NeMo Agent Toolkit is deprecated** (October 2026, end of life by end of 2026). Do not build on it. Its successors (NeMo Relay, Helix, Fabric) are weeks old. A plain `openai` + `pydantic` tool loop matches both our fixed stack and NVIDIA's own "agent in 200 lines" tutorial.
5. **Agents that write geospatial code live fail.** UnivEARTH (v3, Oct 2026): the best model answers 40.0% of 408 yes/no Earth-observation questions with Google Earth Engine, and its code fails 44.2% of the time. Give the agent typed, pre-tested tools over cached tables. Never let it write Earth Engine or SQL during the demo.
6. **LLM-driven feature discovery works only when a deterministic evaluator gates every proposal** (CAAFE: mean ROC AUC 0.798 to 0.822 on 14 small datasets with GPT-4; only 6 of 14 improved with GPT-3.5). CAAFE itself says its keep/reject test "is not based on statistical tests". On a small labeled set the Index Scout must pre-register each hypothesis, score on a development split only, and confirm once on a locked holdout.
7. **The language model must never produce a number.** Evidence: Program-of-Thoughts gains about 12% over chain-of-thought on numeric tasks; GPT-4-Turbo with retrieval got 81% of FinanceBench questions wrong or refused; an independent audit of the AI Scientist found hallucinated numerical results. Our hard rule ("every number traces to metrics.json or DuckDB") is the right design, and it can be enforced by a linter.
8. **What NVIDIA judges have rewarded:** "real-world applicability, technical execution" and "how effectively they demonstrated agentic AI in action"; winners paired agents with an NVIDIA accelerated library and showed many working tools. Show Nemotron in three sizes, GPU XGBoost or RAPIDS as the evaluate tool, and a measured agent scorecard.

---

## 1. The Nemotron family as of 2026-11-14

### 1.1 Exact ids

Sources: live `GET https://integrate.api.nvidia.com/v1/models` (83 entries), `docs.api.nvidia.com/nim/reference/llm-apis`, build.nvidia.com model cards, OpenRouter provider page and per-model endpoints API. All opened today.

| Model | NVIDIA API id (`https://integrate.api.nvidia.com/v1`) | OpenRouter slug | OpenRouter `:free` today | Hugging Face repo | Released |
|---|---|---|---|---|---|
| Nemotron 3 Ultra | `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia/nemotron-3-ultra-550b-a55b` | yes | `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4` | 2026-06-04 (v1.0 GA) |
| Nemotron 3.5 Super VL | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `nvidia/nemotron-3.5-super-vl` | yes | `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4` (and `-BF16`) | 2026-10-15 (card says "GA" and also "early-access") |
| Nemotron 3 Super | `nvidia/nemotron-3-super-120b-a12b` | `nvidia/nemotron-3-super-120b-a12b` | listed, endpoint list empty | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` (and `-NVFP4`) | 2026-03-11 (v1.0 GA) |
| Nemotron 3.5 Lightning | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning` | yes | `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4` (and `-BF16`) | 2026-08-11 (1.0-preview) |
| Nemotron 3 Nano 30B | docs: `nvidia/nemotron-3-nano-30b-a3b`; today's `/v1/models` listing returned `nvidia/nemotron-nano-3-30b-a3b` (see note) | `nvidia/nemotron-3-nano-30b-a3b` | listed, endpoint list empty | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | 2025-12-15 |
| Nemotron 3 Nano Omni | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | same slug, no paid endpoints | yes (tool-choice flags all false) | `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-{BF16,FP8,NVFP4}` | 2026-04-28 |
| Nemotron 3.5 Bolt E4B | `nvidia/nemotron-3.5-bolt-e4b` | not seen on the provider page | n/a | `nvidia/Nemotron-3.5-Bolt-E4B-BF16` | 2026-10-23 |
| Nemotron Nano 9B v2 | card exists at `nvidia/nvidia-nemotron-nano-9b-v2`, no deprecation banner; **not in today's `/v1/models` listing** | `nvidia/nemotron-nano-9b-v2`: endpoint list empty | endpoint list empty | `nvidia/NVIDIA-Nemotron-Nano-9B-v2` | 2025-08-18 |
| Cosmos Reason | `nvidia/cosmos-reason2-8b` is in `/v1/models`; its card URL now shows "Cosmos3-Nano-Reasoner" | n/a | n/a | `nvidia/Cosmos3-Nano` | 2026-05-31 |

Notes:
- **Id discrepancy for Nano 30B.** The docs page and the model card use `nemotron-3-nano-30b-a3b`; the `/v1/models` listing returned `nemotron-nano-3-30b-a3b` twice, and the card URL built from that string is a 404. Run `GET /v1/models` with our key and copy the string. Low stakes: we do not route to this model.
- Model cards leave `model=""` blank in their hosted samples. The Ultra, Super and Bolt cards give the curl string; for Lightning the cookbook README gives `nvidia/nemotron-3.5-lightning-30b-a3b`.
- A forum thread dated 2026-11-12 is titled "Nemotron 3.5 Super VL: Unexpected Model ID in NVIDIA Build API Response" (title only). Do not assert on the `model` field of responses.
- Other entries in `/v1/models` that matter less: `nvidia/nemotron-3.5-content-safety`, `nvidia/nemotron-3.5-embed-1b`, `nvidia/nemotron-3.5-embed-8b`, `nvidia/nemotron-3-embed-1b`, `nvidia/nemotron-parse-2.0`, `nvidia/llama-3.1-nemotron-ultra-253b-v1`, `nvidia/llama-3.1-nemotron-70b-instruct`.

### 1.2 Capability matrix

From the build.nvidia.com / Hugging Face model cards, plus OpenRouter `supported_parameters`.

| Model | Tool calling | `tool_choice` | Parallel tool calls | JSON-schema structured output | Context | Reasoning control | Recommended sampling | License |
|---|---|---|---|---|---|---|---|---|
| 3 Ultra | Supported; parser `qwen3_coder` | free endpoint: none/auto/required/function; DeepInfra: none/auto only | Not stated | Card: "Not supported". Some paid OpenRouter providers still list `structured_outputs`; free endpoint does not | 1M (default 256k) | `chat_template_kwargs: {"enable_thinking": true/false}`; `medium_effort`; client-side reasoning budget | temperature 1.0, top_p 0.95 | OpenMDW-1.1 |
| 3.5 Super VL | Supported | free endpoint: all four modes | Not stated | Supported; free endpoint lists `response_format` and `structured_outputs` | "Up to 1M" (specification: 262,144) | `enable_thinking`; reasoning returned in `reasoning_content` | text: 1.0 / 0.95; vision: 0.6 / 0.95 | OpenMDW-1.1 |
| 3 Super | Supported; parser `qwen3_coder` | DeepInfra: none/auto; DekaLLM: also required/function | Not stated | "Structured Output: Supported" | 1M (default 256k) | `enable_thinking`; `low_effort: true`; client-side `ThinkingBudgetClient` | 1.0 / 0.95 "across all tasks" | NVIDIA Nemotron Open Model License |
| 3.5 Lightning | Supported | paid endpoints list `tool_choice` | Not stated | Supported on card; free endpoint does not list it | 1M | `enable_thinking` | 1.0 / 0.95 | OpenMDW-1.1 |
| 3 Nano 30B | Supported; parser `qwen3_coder` | Nebius: auto/required/function | Not stated | Card: "Not supported" | 262,144 default, up to 1M | `enable_thinking` (default true) | reasoning on: 1.0 / 1.0; tool calling: 0.6 / 0.95 | NVIDIA Nemotron Open Model License |
| 3 Nano Omni | Supported; parser `qwen3_coder` | free endpoint flags all false | Not stated | Card conflicts with itself | 256k | `enable_thinking`; `reasoning_budget` plus `thinking_token_budget` | thinking: 0.6 / 0.95; instruct: 0.2, top_k 1 | NVIDIA Open Model Agreement |
| 3.5 Bolt E4B | Supported | n/a | **Not supported**: "Restrict generation to a single tool invocation per assistant turn" | Supported | 65,536 | thinking on/off (toggle not documented) | 1.0 / 0.95 | OpenMDW-1.1 |
| Nano 9B v2 | Supported; parser `nemotron_json`, non-streaming plugin | n/a | Not stated | Not stated | 131,072 | `/think` or `/no_think` in the system or user message | n/a | NVIDIA Open Model License |

Practical reading:
- **Parallel tool calls are documented for no Nemotron 3.x model** and are explicitly unsupported on Bolt. OpenRouter's default for `parallel_tool_calls` is true "for most models". Design for one tool call per turn and still loop over `tool_calls` defensively.
- **Do not depend on `response_format` for structure.** Use a `submit_*` tool whose arguments are the schema, validate with Pydantic, retry once. That works on every model with tool calling. Where JSON-schema output is wanted, the Super VL endpoint is the one free endpoint that lists it; on OpenRouter add `provider: {"require_parameters": true}`.
- Coding-agent harnesses need `chat_template_kwargs: {"force_nonempty_content": true}` on Super, Ultra and Lightning (card note, no explanation given).
- All cards say the weights are ready for commercial use. The hosted API is a "trial service ... governed by the NVIDIA API Trial Terms of Service"; the NIM FAQ says it is "designed to serve evaluation and prototyping needs only".

### 1.3 Free tiers, rate limits, prices

OpenRouter per-model endpoints API, read 2026-11-14:

| Slug | Provider | Context | Max output | Price in / out per 1M tokens | Structured output listed | Uptime last day |
|---|---|---|---|---|---|---|
| `nvidia/nemotron-3.5-super-vl:free` | Nvidia | 1,000,000 | 131,072 | 0 / 0 | yes | 99.4% |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Nvidia | 1,000,000 | 65,536 | 0 / 0 | no | 96.7% (83.3% in the last 30 min) |
| `nvidia/nemotron-3.5-lightning:free` | Nvidia (nvfp4) | 1,000,000 | 65,536 | 0 / 0 | no | 98.3% |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | Nvidia | 256,000 | 65,536 | 0 / 0 | no | 97.2% |
| `nvidia/nemotron-3.5-lightning` (paid) | Darkbloom, Fireworks, DeepInfra, CoreWeave | 262,144 | 32,768 to 235,929 | 0.025 to 0.07 / 0.12 to 0.20 USD | yes | 99.3 to 100% |
| `nvidia/nemotron-3-super-120b-a12b` (paid) | DeepInfra, DekaLLM | 262,144 | 16,384 / 235,929 | 0.075 to 0.08 / 0.40 to 0.45 USD | yes | 99.4 to 99.9% |
| `nvidia/nemotron-3.5-super-vl` (paid) | 10 providers | 262,144 or 1,048,576 | 102,400 to 943,718 | 0.06 to 0.30 / 0.30 to 0.90 USD | most | 99.2 to 100% |
| `nvidia/nemotron-3-ultra-550b-a55b` (paid) | DeepInfra, KT, BaseTen, Venice | 202,800 to 262,144 | 16,384 to 235,929 | 0.40 to 0.625 / 1.76 to 3.125 USD | DeepInfra, KT | 99.8 to 100% |
| `nvidia/nemotron-3-nano-30b-a3b` (paid) | Nebius (fp8) | 262,144 | 235,929 | 0.06 / 0.24 USD | yes | 100% |

Rate limits:
- **OpenRouter free models:** 20 requests/minute. 50 requests/day if fewer than 10 credits were ever purchased; 1,000/day with at least 10. `GET https://openrouter.ai/api/v1/key` returns `free_model_daily_requests` (used, limit, remaining).
- **build.nvidia.com:** no number is published. The FAQ says to check the account menu, that the rate "will vary per model queried and may vary based on the number of concurrent users", and that the free trial may see "extended wait times during periods of high load". A forum thread title mentions "40 -> 200 RPM" (title only, low confidence).
- **Reliability leads (forum thread titles only, Sep to Nov 2026):** "nemotron-3.5-lightning-30b-a3b returns 503/504 timeouts"; "403 Authorization Failed - /v1/models works, but /v1/chat/completions returns 403" (three threads); "Nemotron 3 Ultra 550B: output stops at 16,384 tokens when max_tokens is 40000"; a report of an Ultra thinking loop.

Inference (budget): a full agent day for us is roughly 1,000 calls (Scout 120, Skeptic 300, Reconciler 50, evaluation harness 480). That is the whole free daily quota. On paid Super that volume costs about 0.85 USD (1,000 calls x 6k input + 1k output tokens at 0.075 / 0.40 USD per million). Put 10 to 20 USD on OpenRouter as the fallback; it also lifts the free cap to 1,000/day.

### 1.4 Agentic benchmark numbers from the model cards

Different cards use different benchmark versions and harnesses; compare loosely.

| Model (BF16 column) | Tool and agent benchmarks | Notes for us |
|---|---|---|
| 3 Ultra | TauBench V3 average 70.9 (Airline 81.5, Retail 86.4, Telecom 92.9, Banking 22.6); SWE-Bench Verified 71.9; Terminal Bench 2.1 56.4; BrowseComp 44.4; IFBench 81.7; OmniScience accuracy 24.1, non-hallucination 78.7; RULER 1M 94.7 | Strongest planner; Banking 22.6 shows long policy-heavy chains still break |
| 3.5 Super VL | tau2-bench retail 69.24; SWE-bench Verified 71.10; Terminal-Bench 2.1 66.70; OSWorld-Verified 51.14; CharXiv reasoning 80.82; MMLongBench-Doc 62.82 | Near Ultra on agent tasks at a fraction of the price; reads charts |
| 3 Super | TauBench V2 average 61.15; SWE-Bench (OpenHands) 60.47; **BIRD Bench 41.80**; IFBench 72.56; RULER at 1M 91.75 | BIRD 41.8 (text-to-SQL) is a reason not to let the agent write SQL |
| 3.5 Lightning | tau3-bench Banking 9.28; SWE-bench Verified 51.56; Terminal-Bench 2.1 24.58; BrowseComp 36.97; IFBench (loose) 71.88; AA-Omniscience 17.50 | Use for single-step narration with facts supplied, not for long tool chains |
| 3 Nano 30B | BFCL v4 53.8; TauBench V2 average 49.0; SWE-Bench (OpenHands) 38.8; IFBench 71.5 | Superseded by Lightning |
| 3.5 Bolt E4B | BFCL v3 71.33; Tau2-Bench 63.23; ToolSandbox 61.11; RAGTruth 74.57; GaRAGe 45.03 | Laptop fallback; one tool call per turn |

### 1.5 Local serving (for our "demo runs fully offline" rule)

See `brev_ops.md` section 4 for VRAM tables. Facts I re-opened today:
- **Ollama:** `ollama run nemotron-3.5-lightning` (19 to 25 GB, badges: tools, thinking; MLX build `30b-mlx` 19 GB with 256K context; 891.9K downloads). The Lightning card says Ollama sets context by VRAM: under 24 GB gives 4K, 24 to 48 GB gives 32K, 48 GB and above gives 256K. `ollama run nemotron-3-nano:4b` is 2.8 to 2.9 GB with 256K context, tools and thinking (`4b-mlx` 2.9 GB).
- **vLLM (Lightning NVFP4):** image `vllm/vllm-openai:v0.27.1`; flags `--tool-call-parser qwen3_coder --enable-auto-tool-choice --reasoning-parser nemotron_v3`; Hopper and Ampere run it as W4A16 (`--moe-backend humming`), DGX Spark uses `--moe-backend marlin`. Target "40+ TPS/User" on one H100 at concurrency of 128 or less.
- **llama.cpp (Lightning):** `llama-server -hf ggml-org/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF:Q4_K_M --temp 1.0 --top-p 0.95 -c 40960 --jinja -ngl 99`.
- **Reasoning parser names differ by backend and by card:** vLLM `nemotron_v3`, SGLang `nemotron_3`, TensorRT-LLM `nemotron-v3` (Lightning card) or `nano-v3` (Ultra and Super cards). Nano 30B on vLLM uses `nano_v3` with a plugin file.
- **Brev NIM guide:** recommends "L40S 48GB or A100 80GB"; `brev port-forward my-instance --port 8000:8000`; tunnel URLs need a browser login, so scripts should use port forwarding.

Inference: for the offline demo the safest design is **replay of a recorded agent trace** plus a small local model for live questions. A 4K context (the under-24 GB Ollama tier for Lightning) is too small for a tool loop; on a laptop use `nemotron-3-nano:4b` or the MLX builds.

### 1.6 Leads from the brief: confirmed or refuted

| Lead | Status |
|---|---|
| Nemotron 3 Nano, Super, Ultra exist | Confirmed. Press release 2025-12-15 announced Nano (available) and Super, Ultra ("first half of 2026"); Super shipped 2026-03-11, Ultra 2026-06-04 |
| Nemotron Nano 9B v2 is the workshop model | Confirmed for the 2025 tutorials; **no longer served on OpenRouter** and absent from today's NVIDIA model listing |
| Vision / omni variants | Confirmed: 3.5 Super VL (text, image, video), 3 Nano Omni (text, image, video, audio), Nano 12B v2 VL (cookbook only) |
| Cosmos Reason as a vision reasoner for us | Refuted for our use. The card is now "Cosmos3-Nano-Reasoner": physical AI and robotics, "Function calling: Not supported", no mention of satellite or aerial imagery |
| "Build a Report Generator AI Agent with Nemotron" uses LangGraph and OpenRouter | Confirmed (2025-09-15) |
| NeMo Agent Toolkit as the agent framework | Refuted as a choice: deprecated October 2026 |
| LoRA fine-tuning "within hours" | Partly confirmed: recipes exist, but no wall-clock figures in the pages opened, and the hardware assumed is DGX Station / B300 class |

---

## 2. NVIDIA agent tooling: status and what to use

### 2.1 NeMo Agent Toolkit is deprecated

The README of `NVIDIA/NeMo-Agent-Toolkit` (branch `develop`) opens with: "NVIDIA NeMo Agent Toolkit has been deprecated as of October 2026 and will reach end of life (EOL) by end of year 2026." It tells users to migrate to:
- **NeMo Relay** (`github.com/NVIDIA/NeMo-Relay`): "for observability, middleware, and governance."
- **NeMo Helix** (`github.com/NVIDIA-NeMo/nemo-helix`): "for a unified CLI with evaluation, optimization, and hardening capabilities." Install `uv tool install "nemo-helix[all]"`, then `nemo setup`; Python 3.12 to 3.14; providers OpenRouter, OpenAI, Anthropic, Gemini, NVIDIA Build, local Ollama; 145 stars.
- **NeMo Fabric** (`github.com/NVIDIA/NeMo-Fabric`): "for a consistent interface to run agent harnesses and custom agents." Releases section empty; 75 stars; harness table lists Claude Code, Codex, OpenClaw, OpenHands, LangChain Deep Agents and others, not LangGraph.

Last toolkit version mentioned: 1.5.0 (`pip install nvidia-nat`, Python 3.11 to 3.13, YAML workflows, `nat run`).

Inference: neither the deprecated toolkit nor its weeks-old successors are a sensible dependency for an 18-hour build. Helix also needs Python 3.12+, and our stack is fixed at 3.11.

### 2.2 Other NeMo pieces

| Tool | Status today | Fit for us |
|---|---|---|
| NeMo Guardrails (`NVIDIA-NeMo/Guardrails`) | v0.24.1; `pip install nemoguardrails`; Python 3.11 to 3.13; five rail types (input, dialog, retrieval, execution, output); flows `self check facts`, `self check hallucination`, `check jailbreak`; 7.5k stars | Optional. Our deterministic number-provenance check is stronger than an LLM self-check. Mention under "developed further" |
| NeMo Evaluator (`NVIDIA-NeMo/Evaluator`) | docs v0.3.0; CLI `nel eval run --bench mmlu --model-url https://integrate.api.nvidia.com/v1 --model-id nvidia/nemotron-3-super-120b-a12b --api-key $NVIDIA_API_KEY --repeats 3 --max-problems 100`; "bring your own benchmark" decorators; 360 stars | The `--repeats 3` idiom matches the pass^k practice in section 5. A hand-rolled harness is faster to build tonight |
| NeMo Data Designer (`NVIDIA-NeMo/DataDesigner`) | `pip install data-designer`; default providers NVIDIA Build API, OpenAI, OpenRouter; samplers, LLM columns, validators, LLM judges; 2.4k stars | Stretch: generate varied analyst questions for the evaluation set. Counts as "agent simulation and evaluation" |
| NeMo Switchyard | "an open source model routing library for AI agents" (Rust, 3.5k stars) | Not needed; our routing is a dictionary |
| Nemotron asset hub (`NVIDIA-NeMo/Nemotron`) | cookbooks per model; 11 use-case examples including "Data Science ML Agent" (Nemotron Nano 9B v2 driving RAPIDS cuDF and cuML; `python -m cudf.pandas -m cuml.accel ...`) and "build-your-own-benchmark" | Precedent that NVIDIA itself pairs a Nemotron agent with GPU data-science tools |

### 2.3 The two official workshops (architecture worth copying)

Repo for both: `github.com/brevdev/workshop-build-an-agent` (Apache-2.0, 157 stars, 461 commits). Brev Launchable: `https://brev.nvidia.com/launchable/deploy?launchableID=env-32kC34ErT9wsqTcJyaKMxBEuhr2`. The repo now has seven modules: 1 Build an Agent (report generation), 2 Agentic RAG, 3 Agent Evaluation (RAGAS, LLM-as-judge), 4 Agent Customization (Data Designer, NeMo Gym, GRPO), 5 Deep Agents, 6 Agent Safety, 7 Agent Harnesses and Skills.

**"Build a Report Generator AI Agent with NVIDIA Nemotron on OpenRouter"** (NVIDIA Technical Blog, 2025-09-15, Li, Kraus, Kao)
- Model init: `ChatNVIDIA(base_url="https://openrouter.ai/api/v1", model="nvidia/nemotron-nano-9b-v2:free", api_key=os.getenv("OPENROUTER_API_KEY"))`; tool binding `llm.bind_tools([tools.search_tavily])`.
- Graph: `START -> topic_research -> report_planner -> section_author_orchestrator -> report_author -> END` on a LangGraph `StateGraph(AgentState)`. The researcher is a ReAct loop; each section author first decides whether more research is needed.
- State objects: `ResearcherState`, `SectionWriterState`, `Section(name, description, research, content)`, `AgentState(topic, report_structure, report)`.
- The logs show "Throttling LLM calls". No evaluation is reported.

**"Build a Retrieval-Augmented Generation (RAG) Agent with NVIDIA Nemotron"** (2025-09-23)
- LLM `nvidia/nvidia-nemotron-nano-9b-v2` via `ChatNVIDIA` (temperature 0.6, top_p 0.95, max_tokens 8192); embeddings `llama-3.2-nv-embedqa-1b-v2`; reranker `llama-3_2-nv-rerankqa-1b-v2`.
- Pipeline: `RecursiveCharacterTextSplitter` with chunk 800, overlap 120; FAISS in memory; retriever `k=6`; rerank with `NVIDIARerank`; `create_retriever_tool`; `create_react_agent`.
- The "when to retrieve" behaviour: the retriever is just a tool, and it runs only when the model judges that extra context is needed. System prompt asks for `[KB]` citations and an explicit "I don't know".
- No quantitative evaluation is reported.

**"Create Your Own Bash Computer Use Agent with NVIDIA Nemotron in One Hour"** (2025-10-22)
- "roughly 200 lines of Python code with minimal dependencies" (`openai` only). Outer loop reads input; inner loop calls the model, executes tool calls, repeats until the reply has no tool call. Allowlist of commands enforced in code and reinforced in the prompt; human confirmation per command.

Module 3 file names (evaluation): `evaluate_rag_agent.ipynb`, `evaluate_report_agent.ipynb`, `generate_rag_eval_dataset.ipynb`, `generate_report_eval_dataset.ipynb`, `evaluation_framework.py`.

### 2.4 Brev Launchables

Docs: "A Launchable is a reproducible, shareable environment configuration." It bundles compute (GPU type, disk), one of four runtime modes (VM, single container, Docker Compose, single-node Kubernetes beta), a source (repository, notebook or Markdown URL), network (Secure Link, ports) and launch parameters. Sharing is by link or a "Launch on Brev" Markdown badge; "View Metrics" shows views and deployments. The docs do not say who is billed when someone else deploys.

Inference: a "Launch on Brev" badge in the README is a cheap reproducibility signal for NVIDIA judges. It must not be on the demo path (see `brev_ops.md`).

### 2.5 Fine-tuning Nemotron inside the hackathon

- Official recipes: LoRA on one DGX Station GB300 (one B300 GPU) with NeMo AutoModel; full-weight SFT and GRPO on two Stations; `lora-text2sql` with NeMo Megatron-Bridge; a "Nemotron Post-training Calculator" for runtime and cost. The pages opened give no hyperparameters, wall-clock times or accuracy deltas.
- Prime Intellect Lab blog (2026-07-23): LoRA with reinforcement learning on `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`, 100 steps, batch 32, "less than $5"; accuracy on 32 held-out MATH problems rose from 21.9% (7/32) to 90.6% (29/32).

Inference: fine-tuning is fast and cheap when a verifiable reward and a training set exist. We have neither for agent behaviour, and none of the prize criteria ask for it. Skip; mention as a next step.

---

## 3. What NVIDIA judges have rewarded

Only two primary sources could be opened. Devpost pages (the AWS and NVIDIA "Agentic AI Unleashed" hackathon and its gallery) returned HTTP 403.

**NVIDIA NeMo Agent Toolkit Hackathon** (NVIDIA Technical Blog, 2025-07-17). Stated criteria: "real-world applicability, technical execution" and "how effectively they demonstrated agentic AI in action".

| Place | Project | Pattern that was praised |
|---|---|---|
| 1 | Route Optimization Agent for Intelligent Fleet Management | Several agents (language understanding, constraint extraction, route computation) calling NVIDIA cuOpt, with a "full simulation-to-deployment pipeline" |
| 2 | OpenCodeReview | Orchestration and memory; models swappable by configuration; broad accessibility |
| 3 | AI-Powered Travel Planner | "a large number of tools and an impressive number of features"; local fallback database for API outages |
| Mention | Cyber agent for small indicators of compromise | Modular specialised sub-agents sharing findings |

**Generative AI Agents Developer Contest by NVIDIA and LangChain** (2024). Criteria: real-world application ("impact and novelty of the project in addressing real-world challenges"), technology integration ("how effectively the developer has used NVIDIA's LLM stack and LangChain technologies"), quality of submission ("comprehensiveness and clarity of the project details, instructions, and demo").

Inference, for our pitch:
1. Pair the agent with an NVIDIA accelerated library that does the heavy work (for us: GPU XGBoost or RAPIDS in the evaluate tool), as the first-place project did with cuOpt.
2. Show many real tools working, with a fallback when an API fails.
3. Make the agentic behaviour visible: a plan, tool calls, a result that changes the next step.
4. Give clear run instructions (a Launchable badge, a replayable trace).

---

## 4. Precedents and reliability evidence

### 4.1 Agents for geospatial and Earth-observation analysis

| System | Year | Design | Reliability evidence |
|---|---|---|---|
| LLM-Geo ("Autonomous GIS", Li and Ning) | 2023 | GPT-4 generates and runs Python for data collection, analysis, mapping; five goals: self-generating, self-organizing, self-verifying, self-executing, self-growing | Three case studies only; authors: "still in its infancy and lacking several important modules such as logging and code testing" |
| GeoAgent (Chen et al.) | 2024 | Code interpreter + static analysis + retrieval inside Monte Carlo Tree Search | Abstract names the failure it targets: hallucinated use of less common libraries; no numbers on the abstract page |
| GeoLLM-Squad | 2025 | Multi-agent; "separates agentic orchestration from geospatial task-solving"; AutoGen + GeoLLM-Engine; includes agriculture | "17% improvement in agentic correctness over state-of-the-art baselines" |
| ThinkGeo | 2025 to 2026 | ReAct loop over a remote-sensing toolset, optical RGB and SAR | 486 tasks, 1,778 expert-verified steps; "notable disparities" between models in tool accuracy and planning consistency |
| Earth-Agent (ICLR 2026) | 2025 to 2026 | MCP-based tool ecosystem for RGB and spectral data | Earth-Bench: 248 tasks, 13,729 images; scores both trajectories and outcomes |
| **UnivEARTH** ("Towards LLM Agents for Earth Observation") | v3 2026-10-05 | Agent writes Google Earth Engine code to answer yes/no questions | See table below |
| **GeoBenchX** | 2025 | LangGraph ReAct agent, 23 fixed geospatial tools including `reject_task`, temperature 0, up to 25 iterations | See table below |
| Google "Geospatial Reasoning" | 2025-04-08 | Gemini-orchestrated LangGraph agent on Vertex AI Agent Engine over Earth Engine, BigQuery, Maps | "still under development"; demo "relied on pre-computed detections" for speed; no accuracy figures |
| Google Earth AI | 2025 to 2026 | Foundation models plus a Gemini reasoning agent | Abstract gives no figures |
| NASA Earth Copilot (with Microsoft) | 2024-11-14 | Azure OpenAI over NASA data (over 100 petabytes) | "proof of concept"; internal testing only; no accuracy discussion |
| TEOChat (ICLR 2025) | 2024 to 2025 | Vision-language assistant for temporal sequences of Earth-observation images | Abstract mentions no crops, Sentinel-2 or harvest tasks |

**UnivEARTH, Table 3 (zero-shot, Python Earth Engine API), 408 yes/no questions from NASA Earth Observatory articles:**

| Model | Correct | Wrong answer | Code failure (sum of the paper's four failure classes) |
|---|---|---|---|
| Claude-4.5-Sonnet | 40.0% | 15.7% | 44.2% |
| Gemini-2.5-Pro | 36.9% | 9.6% | 53.5% |
| GPT-5 | 33.1% | 12.0% | 54.9% |
| DeepSeek-Reasoner | 28.5% | 13.0% | 58.6% |
| Claude-4.5-Haiku | 16.7% | 12.8% | 70.5% |
| Gemini-2.5-Flash | 10.6% | 5.9% | 83.4% |

- With Reflexion (at most two rounds): Claude-4.5-Sonnet 40.0% to 64.5%, but wrong answers rose from 15.7% to 26.0%; GPT-5 33.1% to 59.3%. The authors: "these results remain only marginally above random chance."
- Failure breakdown for Gemini-2.5-Pro: wrong dataset id 14.2%, temporal or spatial mismatch 15.7%, wrong band name 9.6%, syntax or runtime error 10.0%.
- Supplying collection ids and band names: Claude on VIIRS questions, syntax errors 23.5% to 0% and accuracy 38.2% to 61.5%, but wrong answers 8% to 23.1%. Fewer crashes did not mean correct answers.
- Example of a silent numeric error: 1723.29 degrees C returned because a 0.01 scale factor was omitted.
- Authors' conclusion: the bottleneck is domain-specific grounding, not coding ability.

**GeoBenchX, 202 tasks (123 solvable, 79 intentionally unsolvable):**

| Model | Full match on solvable | Correct rejection of unsolvable |
|---|---|---|
| Claude Sonnet 4 | 0.55 | 0.17 |
| o4-mini | 0.51 | 0.90 |
| Claude Sonnet 3.5 | 0.47 | 0.47 |
| GPT-4.1 | 0.42 | 0.43 |
| Gemini 2.5 Pro Preview | 0.39 | 0.55 |
| GPT-4o | 0.38 | 0.62 |

- Even with 23 curated tools, the best model fully solves 55% of solvable tasks.
- Models prefer to answer: the model with the best solve rate rejects only 17% of unsolvable tasks.
- Error types: centroid value used instead of a polygon average; outdated world knowledge; over-reliance on memory instead of dataset values; skipped filtering steps; changing the task to make it solvable; invented thresholds; answering without using tools.
- LLM-as-judge panel agreement with humans on a 50-task check: GPT-4.1 96%, Claude Sonnet 3.5 94%, Gemini 2.5 Pro Preview 88%.
- The authors note that narrower, specialised tools improved accuracy.

What this means: none of these systems reports field-scale crop harvest work, and the measured reliability of code-writing Earth-observation agents is far below what a statistician would accept. The designs that hold up share three properties: fixed tools, a separate orchestrator, and an explicit way to refuse.

### 4.2 LLM-driven feature discovery and "co-scientist" loops

| Work | Loop | Numbers | Caveats (the authors' own unless marked "Inference") |
|---|---|---|---|
| CAAFE (Hollmann, Mueller, Hutter, 2023) | LLM gets a dataset description and 10 rows, returns Python feature code plus an explanation; code runs; feature kept only if validation performance improves; 10 iterations; TabPFN as evaluator | 14 datasets (69 to 2,000 samples). Mean ROC AUC 0.798 to 0.822 with GPT-4; 11 of 14 improved. With GPT-3.5 only 6 of 14 improved (mean 0.806), "clearly worse". About 4:43 minutes per dataset, 90% of it LLM generation | "The testing procedure for adding features is not based on statistical tests"; hallucinated features can look significant; whitelist of operations "does not provide full security"; a bias example (name-ending feature) |
| LLM-FE (Abhyankar, Shojaee, Reddy; TMLR) | Feature engineering as program search; 3 programs per iteration, 20 LLM samples, 3 islands, best programs fed back as in-context examples | Classification mean rank 1.42 versus CAAFE 3.47, OpenFE 3.63, no feature engineering 3.95. XGBoost accuracy 0.820 to 0.840 with GPT-3.5; 0.832 with Llama-3.1-8B. Ablations (normalised score): without domain knowledge 0.626; without evolutionary refinement 0.587 | Outputs should be "expert-reviewable hypotheses rather than directly deployable transformations"; memorisation risk |
| FunSearch (DeepMind, 2023) | LLM proposes programs; an automated evaluator runs and scores them; best programs seed the next round | New cap-set constructions; better bin-packing heuristics | The evaluator exists precisely because proposals are tested rather than trusted; output is code, so the result can be inspected |
| AI co-scientist (Gottweis et al., 2025) | Multi-agent "generating, critiquing and refining hypotheses"; tournament evolution; quality scales with test-time compute | Validated in three biomedical applications with wet-lab follow-up | Inference: the validation came from experiments outside the system, not from the agents |
| The AI Scientist, independent evaluation (Beel, Kan, Baumgart, 2025) | Fully autonomous paper writer | "42% of experiments failed due to coding errors"; "Some papers contained hallucinated numerical results"; USD 6 to 15 per paper | Quality "resembles a rushed undergraduate paper" |
| karpathy/autoresearch (2026) | Agent edits only `train.py`; `prepare.py` fixed; "fixed 5-minute time budget"; about 12 experiments per hour | 100k stars | README: results are "not comparable to other people running on other compute platforms". Inference: one validation metric is reused for every keep-or-discard decision, so the loop can overfit it |

Lessons for the Index Scout:
1. The proposer must be a strong model. GPT-3.5 was "clearly worse" in CAAFE. Use Ultra or Super VL for proposals, not Lightning or Bolt.
2. Feed back the leaderboard and domain context. Removing either hurt LLM-FE most.
3. A handful of evaluations is enough. LLM-FE used 20 samples; CAAFE 10 iterations. Cap the Scout at about 60.
4. Every kept feature carries a text rationale. That is CAAFE's stated interpretability benefit and exactly what "explainable to a skeptic" needs.
5. Nobody in this literature controls for multiple testing. We must.

### 4.3 Hallucinated numbers and multi-agent failure

| Evidence | Number | Mitigation it supports |
|---|---|---|
| Program of Thoughts (Chen et al., TMLR 2023) | "average performance gain over CoT by around 12%" on 5 math and 3 financial QA datasets when computation is delegated to an interpreter | Compute in tools; the model only decides what to compute |
| FinanceBench (2023) | GPT-4-Turbo with retrieval "incorrectly answered or refused to answer 81% of questions" (150 cases) | Retrieval alone does not make numbers right |
| DSBench (2024 to 2025) | Best agent solves 34.12% of 466 data-analysis tasks | Do not hand open-ended analysis to an agent |
| tau-bench (2024) | Function-calling agents such as gpt-4o succeed on under 50% of tasks; pass^8 under 25% in retail | Report repeatability (pass^k), keep chains short |
| MAST, "Why Do Multi-Agent LLM Systems Fail?" (2025) | 7 frameworks, 1,600+ annotated traces, 14 failure modes in 3 categories (system design, inter-agent misalignment, task verification), kappa 0.88; gains over single agents "often minimal" | Few roles, deterministic hand-offs, an explicit verification step |
| Anthropic, "Building effective agents" (2024-12-19) | Recommends "finding the simplest solution possible, and only increasing complexity when needed"; frameworks add layers that "obscure the underlying prompts and responses" | Workflows (predefined code paths) with small agent loops inside |
| Nemotron cards | Ultra OmniScience non-hallucination 78.7; Lightning AA-Omniscience 17.50 | Inference: if "non-hallucination" is a rate, even the flagship gives an unsupported answer about one time in five on that benchmark. The cards do not define the metric |

### 4.4 Adaptive overfitting on a small labeled set

Dwork et al., "Generalization in Adaptive Data Analysis and Holdout Reuse" (2015): reusing a holdout set across many adaptively chosen analyses leads to "overfitting to the holdout set itself"; the paper gives an algorithm for safely validating "a large number of adaptively chosen hypotheses".

Inference: an Index Scout that tries 60 to 2,000 candidate features against a few hundred labeled fields, and keeps the winners, is exactly this situation. `models.md` raises the same objection. The fix is procedural and cheap (section 6.5).

---

## 5. Agent evaluation practice

**Anthropic, "Demystifying evals for AI agents" (2026-01-09):**
- Vocabulary: task, trial, grader, transcript (trace), outcome (final state in the environment), evaluation harness, agent harness, evaluation suite.
- Start with "20-50 simple tasks drawn from real failures".
- Graders: code-based (fast, objective, "Brittle to valid variations"), model-based (flexible, non-deterministic, must be calibrated against humans), human (gold standard, slow).
- It is "often better to grade what the agent produced, not the path it took"; rigid tool-sequence checks are brittle.
- pass@k (at least one success in k) versus pass^k (all k succeed): a 75% per-trial success rate gives about 42% for pass^3.
- "LLM-as-judge graders should be closely calibrated with human experts"; give the judge an "Unknown" option.
- Balance the set: "One-sided evals create one-sided optimization" (test both when a behaviour should and should not occur).
- "Read the transcripts!"

**RAGAS metric definitions (docs, stable):**
- Tool Call Accuracy: "measures how accurately an LLM agent invokes tools compared to expected tool calls"; "Final score = (argument accuracy) x (sequence aligned ? 1 : 0)"; strict order by default, `strict_order=False` for any order.
- Tool Call F1: precision and recall of tool calls against `reference_tool_calls`, "uses unordered matching".
- Agent Goal Accuracy: binary, with or without a reference outcome.
- Topic Adherence: precision, recall, F1 of staying inside reference topics.
- Faithfulness: claims in the response supported by the retrieved context divided by all claims in the response; a variant uses Vectara HHEM-2.1-Open, a small free classifier that runs on CPU.

**NVIDIA tooling:** NeMo Evaluator's quick start runs each benchmark with `--repeats 3`, and its CLI lists `nel compare` and `nel gate` (names only; behaviour not read). The workshop's Module 3 teaches RAGAS plus LLM-as-judge with synthetic test-set notebooks.

**Calibration reference point:** GeoBenchX judges agreed with humans on 88% to 96% of a 50-task sample, depending on the judge model.

---

## 6. Recommended design for Kernel

### 6.1 Principles (each tied to evidence above)

1. **Workflow outside, small ReAct loops inside.** Four roles, fixed hand-offs in code (MAST; Anthropic).
2. **Typed tools over cached tables; no code generation at run time** (UnivEARTH; GeoBenchX; BIRD 41.8).
3. **The model proposes; a deterministic evaluator disposes** (FunSearch; CAAFE; LLM-FE).
4. **No number in prose unless it is a fact id returned by a tool** (PoT; FinanceBench; our hard rule).
5. **Refusal is a first-class outcome** (GeoBenchX rejection accuracy; Anthropic "Unknown").
6. **Everything is logged and replayable** (reproducibility for USDA; offline demo rule).
7. **Where an exhaustive deterministic sweep is cheap, run it and use it as the baseline the agent has to match with fewer calls.** The agent's defensible value is ordering, composition, explanation and abstention, not arithmetic.

### 6.2 Architecture

```
                 kernel.duckdb  +  features.parquet  +  nass_reference.parquet  +  agronomy notes (local)
                        ^                 ^                      ^                        ^
                        |  typed, read-only, pre-tested tools (Pydantic schemas, enums)   |
   +----------------+   |   +-------------------+   +------------------+   +----------------------+
   | Index Scout    |---+---| Skeptic /         |---| Reconciler       |---| Report Writer        |
   | ReAct, <=60    |       | Field Auditor     |   | ReAct, <=12 steps|   | single call per item |
   | evaluations    |       | ReAct, <=8 steps  |   | retrieves only   |   | placeholders only    |
   | pre-registered |       | per field, review |   | when a gap is    |   | + number linter      |
   | hypotheses     |       | band only         |   | unexplained      |   |                      |
   +----------------+       +-------------------+   +------------------+   +----------------------+
        |  ledger.tsv            | audits.jsonl          | reconcile.json         | cards/*.json, report.md
        +------------------------+-----------------------+------------------------+
                         trace.jsonl (every model call and tool call)  ->  replay mode, SSE to the UI
   Evaluation harness: 30-40 tasks x 3 trials -> agent_metrics.json -> one slide
```

Fixed order in code: Scout (once, before the model is frozen) -> model fit (not an LLM) -> Skeptic on the review band -> Reconciler -> Writer. No agent calls another agent.

### 6.3 Model routing

| Role | Primary (NVIDIA API id) | OpenRouter fallback | Why |
|---|---|---|---|
| Scout proposals, Skeptic, Reconciler | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `nvidia/nemotron-3.5-super-vl:free` | Tools, every `tool_choice` mode, structured output, strongest agent scores per dollar, reads charts |
| Second opinion on hard cases; Scout if Super VL stalls | `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia/nemotron-3-ultra-550b-a55b:free` | Best planner; keep `max_tokens` at or below 16,000 |
| Stable alternative if Super VL misbehaves | `nvidia/nemotron-3-super-120b-a12b` | paid, 0.075 / 0.40 USD per million | GA since March 2026 |
| Bulk per-field cards and narration | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning` (paid 0.025 to 0.07 / 0.12 to 0.20 USD) | Cheap and fast; single-step only |
| Offline demo | Ollama `nemotron-3.5-lightning` (24 GB+) or `nemotron-3-nano:4b` | replay of `trace.jsonl` | Project rule: demo runs offline |

Settings: `temperature=1.0, top_p=0.95` (NVIDIA's recommendation for Super, Ultra, Lightning), `seed` fixed, thinking on for planning turns and off (`enable_thinking: false`) for narration, `max_tokens` 4,000 to 16,000, one tool call per turn. Reproducibility comes from the cache, not from temperature 0.

Inference (throughput): at the card's "40+ TPS/User" target and concurrency 128, a self-hosted Lightning on one H100 would write about 10,000 cards of 300 tokens in roughly 10 minutes. On hosted endpoints expect far less; measure before promising a number.

### 6.4 Tool registry

All tools are plain Python functions with Pydantic argument models, read-only access, enumerated choices wherever possible, and a `facts` list in every result.

Result envelope:

```json
{"ok": true,
 "facts": [{"id": "f_0412", "label": "green_at_cut", "value": 0.81,
            "unit": "share of season peak NDVI", "entity": "field:06107-000123",
            "source": "features.parquet@3f9c1a"}],
 "notes": "2 clear Sentinel-2 scenes within 6 days before the cut"}
```

**Index Scout**

| Tool | Arguments | Returns |
|---|---|---|
| `list_measurements` | none | available band tokens, acquisition counts, the four baseline features and their dev-split scores |
| `search_index_catalog` | `query`, `domain` (vegetation, water, soil, burn, radar), `needs` (optical, radar) | catalog entries: acronym, formula, bands, source. Read from the vendored `spectral-indices-dict.json` |
| `propose_and_evaluate_feature` | see schema below | ledger id, grouped-CV scores, observed direction, coverage, redundancy, incremental gain |
| `get_leaderboard` | `top_k` | ranked ledger rows |
| `finalize_shortlist` | `feature_ids` (max 3), `justification` | one-time holdout confirmation; callable once per run |

```json
{"type": "function", "function": {
  "name": "propose_and_evaluate_feature",
  "description": "Register ONE hypothesis about a harvest signal, then score it on the development split with county-grouped cross-validation. The hypothesis and expected direction are written to the ledger before scoring and cannot be edited.",
  "parameters": {"type": "object", "additionalProperties": false,
    "required": ["name", "expression", "temporal_op", "expected_direction", "rationale"],
    "properties": {
      "name": {"type": "string", "maxLength": 40},
      "expression": {"type": "string",
        "description": "Per-date index. Either a catalog acronym (e.g. NDTI) or arithmetic over band tokens B,G,R,RE1,RE2,RE3,N,N2,S1,S2,VV,VH using + - * / and abs, log, sqrt."},
      "temporal_op": {"type": "string", "enum": ["level_pre", "frac_of_peak_pre", "drop_across", "slope_pre", "level_post", "days_from_browning_to_cut", "season_max", "doy_of_max_slope"]},
      "window_days": {"type": "integer", "enum": [10, 15, 20, 30]},
      "anchor": {"type": "string", "enum": ["radar_cut", "optical_cut"]},
      "expected_direction": {"type": "string", "enum": ["higher_in_silage", "lower_in_silage"]},
      "rationale": {"type": "string", "maxLength": 400,
        "description": "Agronomic reason, written before seeing the score."}}}}}
```

Evaluator output facts: `cv_auc_mean`, `cv_auc_sd` (county-grouped folds), `pr_auc`, `direction_observed`, `direction_matches` (bool), `coverage` (share of fields with a valid value), `max_abs_corr_with_kept`, `incremental_auc_over_baseline`, `status` (kept, refuted, redundant, invalid, low_coverage).

**Skeptic / Field Auditor**

| Tool | Arguments | Returns |
|---|---|---|
| `get_field_evidence` | `field_id` | the four numbers, county percentiles, model probability, conformal set, data-quality flags |
| `test_alternative` | `field_id`, `hypothesis` (enum below) | `supported` / `refuted` / `untestable` plus facts |
| `get_neighbors` | `field_id`, `k` (max 10) | nearby fields' calls and distance to nearest dairy |
| `get_timeseries_plot` | `field_id` | path to a PNG of NDVI, NDMI, VH/VV with the cut marked (for the card and the optional vision check) |
| `submit_audit` | `field_id`, `verdict` (uphold, overturn, needs_review), `strongest_alternative`, `evidence_ids` | writes the audit record |

`hypothesis` enum, each backed by a deterministic check (thresholds belong to the agronomy and modeling lanes):

| Value | Check |
|---|---|
| `cloud_gap_hid_cut` | days between the last clear optical scene and the radar cut; if large, green-at-cut is unreliable |
| `early_grain_hot_region` | cut early by calendar but late in growing-degree-days, greenness already low |
| `double_crop_winter_forage` | a spring peak and an earlier cut before corn green-up |
| `abandoned_or_failed` | greenness collapse with no radar structure change, or season peak never reached |
| `high_moisture_corn_or_earlage` | cut shortly after the silage window, residue signal present |
| `partial_or_mixed_field` | bimodal pixel-level cut dates inside the boundary |
| `not_corn` | low CDL confidence or an atypical season curve |
| `radar_artifact_rain` | VV and VH both jump on the change date with no optical change |

**Reconciler**

| Tool | Arguments | Returns |
|---|---|---|
| `rollup` | `level` (county, state), `geo_id`, `year` | predicted silage and grain acres with intervals |
| `get_nass_reference` | `state`, `year`, `item` (silage_acres, grain_acres, planted_acres) | official figure and its publication date |
| `compare_rollup` | `level`, `year` | table of predicted, official, absolute and relative gap |
| `diagnose_gap` | `geo_id` | decomposition: corn area in CDL versus NASS, share of acres in the review band, threshold sensitivity, other fates |
| `try_adjustment` | `kind` (threshold, prior_shift), `params` | re-computed gaps; nothing is saved unless a human accepts |
| `retrieve_agronomy` | `query` | passages from the local note set with source ids |
| `cannot_answer` | `reason` | explicit refusal |

**Report Writer**: no tools. Input is a list of fact objects; output is text with `{{f_0412|pct}}` placeholders.

### 6.5 The four agents

**Index Scout (the piece most likely to count as "a new harvest signal").**
- Loop: read measurements and catalog -> write a hypothesis with expected direction -> tool scores it -> read leaderboard -> next hypothesis. Stop at 60 evaluations or 10 without improvement.
- Pre-registration: the ledger row (name, expression, expected direction, rationale) is written before the score. A feature whose observed direction contradicts the stated expectation is recorded as refuted and cannot be kept, however well it scores.
- Splits: development split only, cross-validation grouped by county (and stratified by state if possible). A holdout split is never loaded by the process the agent drives; `finalize_shortlist` triggers one confirmation run.
- Keep rule (suggested): direction matches; coverage at or above a floor; incremental gain over the four baseline features larger than its fold-to-fold standard deviation; not redundant with a kept feature.
- Brute-force baseline: score every computable catalog index times every temporal operator offline. Report (a) how many of the Scout's evaluations it took to reach a top-decile feature, against random order, and (b) the gap between cross-validated and holdout scores for the shortlist.
- Report to judges: hypotheses tried, kept, refuted, and the holdout result. That count is the multiple-comparison disclosure.

**Skeptic / Field Auditor.**
- Runs only on fields in the conformal review band plus a random sample of confident calls (for a false-alarm rate).
- Chooses which alternatives are worth testing from the evidence, calls the checks, weighs them, and submits `uphold`, `overturn` or `needs_review` with evidence ids.
- Measure: on labeled fields, share of model errors the Skeptic flags (error-catch recall) against share of correct calls it flags (false alarms). If it does not beat "run all eight checks and flag any hit", say so and ship the deterministic version with the agent as narrator.

**Reconciler.**
- Compares rollups with NASS, ranks the largest gaps, diagnoses each with tools, tries at most three adjustments, and writes a reconciliation note.
- Retrieval rule: `retrieve_agronomy` is called only when `diagnose_gap` leaves a gap unexplained. This is the "decides when to retrieve" behaviour; score it on a balanced set of questions that do and do not need retrieval.
- It never changes the model. Adjustments are proposals for a human.

**Report Writer.**
- One call per card or section. The model sees fact ids, labels and rounded values and returns sentences with placeholders. Code renders the numbers.
- Linter: any digit outside a placeholder fails the output; one retry; then a deterministic template.
- The "Monday market memo" is the same code path with a different template. Build it last or not at all; it adds no agentic behaviour.

**Optional stretch: vision second reader.** The Skeptic sends the field's time-series chart to Super VL and asks whether greenness "falls off a cliff" or "fades", then compares with the numeric call. Super VL scores 80.82 on CharXiv reasoning, so expect roughly one chart in five to be misread. Report the agreement rate; never let it change a call. This covers the "multi-modal agents" item on the prize list. `models.md` records that vision models are poor at labelling crop chips; charts are a different and easier input, but unvalidated for us.

### 6.6 Guardrails

| Risk | Guard |
|---|---|
| Invented numbers | Fact-id placeholders and the digit linter; UI reads numbers from data files only |
| Invented formulas | Catalog formulas are read from the vendored JSON; free expressions pass an AST whitelist (band tokens, + - * /, abs, log, sqrt; no names, attributes or imports); denominators get an epsilon |
| Index dredging | Pre-registered direction; evaluation cap; grouped CV; locked holdout touched once; counts disclosed |
| Wrong tool arguments | Pydantic models, enums, ranges; errors returned to the model as tool results, at most two repairs |
| Answering the unanswerable | `cannot_answer` and `needs_review` are valid, scored outcomes |
| Runaway loops and thinking loops | Step caps (8 to 12), `max_tokens` at or below 16,000, wall-clock timeout per call, low or medium reasoning effort on tool turns |
| Endpoint failures | Exponential backoff on 429 and 5xx; provider fallback NVIDIA -> OpenRouter -> local; every response cached by hash of (model, messages, tools) |
| Data damage | DuckDB opened read-only; no write tools; adjustments return results without saving |
| Retrieved text as instructions | Passages are wrapped and labelled as data; the agent has no tool that acts on free text |

### 6.7 Evaluation harness

Tasks in a JSONL file, 30 to 40 to start, three trials each.

| Group | Example | Grader | Metric |
|---|---|---|---|
| Tool selection (10) | "Silage acres we estimate for Tulare County, 2025" -> `rollup(level=county, geo_id=06107, year=2025)` | code: unordered match of (tool, canonical args) | tool-call precision, recall, F1 |
| Outcome (8) | "Which state has the largest gap to NASS?" | code: answer equals the tool-derived truth | goal accuracy |
| Unsolvable (6) | "Silage acres in 2031"; "corn yield in bushels" | code: `cannot_answer` was called | rejection accuracy |
| Retrieval decision (8, half need it) | "Why might a late-September cut still be silage in California?" versus "How many fields are in the review band?" | code: was `retrieve_agronomy` called | retrieval precision and recall |
| Groundedness (all prose outputs) | cards and notes | code: digit linter; plus LLM judge on 20 cards for non-numeric claims, 10 of them also human-scored | un-sourced numerals (target 0); faithfulness; judge-human agreement |
| Repeatability | all tasks x 3 | code | pass^3 |
| Response time | all tasks | timer | p50 and p95 seconds per task, tool calls per task, tokens |
| Scout | ledger | code | evaluations to first top-decile feature versus random; share of expectations confirmed; CV-to-holdout gap |
| Skeptic | labeled fields | code | error-catch recall, false-alarm rate, selective accuracy at fixed coverage |

Output: `agent_metrics.json`, one row appended to a results table per run (same habit as `autoresearch/results.tsv`), and one slide.

### 6.8 Build order (about 12 hours of one lane; cut from the bottom)

| Hours | Deliverable |
|---|---|
| 0 to 1 | Client with provider fallback, cache, trace, replay mode |
| 1 to 3 | Tool registry over DuckDB and the feature table; fact envelope |
| 3 to 5 | Index Scout, ledger, brute-force baseline |
| 5 to 6.5 | Skeptic with three alternative checks first, then the rest |
| 6.5 to 8 | Reconciler; local note retrieval |
| 8 to 9 | Report Writer, linter, field cards |
| 9 to 11 | Evaluation harness, three trials, metrics table |
| 11 to 12 | Record the demo trace, slide, README section with a Launchable badge |
| Stretch | Vision second reader (1 to 1.5 h); Data Designer question generator (0.75 h); NeMo Guardrails input rail on the chat (0.5 h) |

If only six hours are available: client and tools, Scout, Writer with linter, 20-task evaluation.

### 6.9 Demo script (inside the five-minute pitch)

Use replay, not a live endpoint.
1. (20 s) "The model never produces a number. It decides which measurement to run and explains the result."
2. (40 s) Scout ledger scrolling: a hypothesis with its expected direction, the score arriving, one hypothesis refuted because the sign was wrong, the shortlist confirmed once on held-out fields. State the counts.
3. (30 s) Skeptic on one hard field (an early Texas grain field or a California double-crop field): two alternatives tested, one supported, verdict "needs review".
4. (30 s) Reconciler: the county with the largest gap to NASS, the diagnosis, the single retrieved passage it needed.
5. (20 s) Agent scorecard: tool-call F1, rejection accuracy, pass^3, un-sourced numerals = 0, median seconds per answer.
6. (10 s) "Three Nemotron models, routed by task; GPU XGBoost does the scoring; one click reproduces it."

### 6.10 What to tell USDA statisticians

- "Every index the agent tried is in a ledger, with the expected sign written before the score. N tried, M kept, confirmed once on fields the agent never saw."
- "The agent may answer 'cannot determine'. We measured how often it should have and did."
- "We scored the agent the way we score the classifier: accuracy of its tool use, repeatability over three runs, and seconds per answer."
- "Free-form Earth-observation agents get about 40% of yes/no questions right in the latest benchmark. Ours cannot write code; it can only call measurements we tested."

---

## 7. Recipes

Stack note: only `openai`, `pydantic` and `duckdb`, all already in our fixed stack. No LangGraph, no NeMo Agent Toolkit. Vendoring `spectral-indices-dict.json` needs no new library; adding `spyndex` would need a line in `docs/DECISIONS.md`.

### 7.1 Client with fallback, cache and replay

```python
import hashlib, json, os, time
from openai import OpenAI

PROVIDERS = [
    ("nvidia", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("local", "http://localhost:11434/v1", None),   # Ollama's OpenAI-compatible route; not re-verified today
]
MODELS = {
    "plan":  {"nvidia": "nvidia/nemotron-3.5-super-vl-120b-a12b", "openrouter": "nvidia/nemotron-3.5-super-vl:free", "local": "nemotron-3.5-lightning"},
    "hard":  {"nvidia": "nvidia/nemotron-3-ultra-550b-a55b",      "openrouter": "nvidia/nemotron-3-ultra-550b-a55b:free", "local": "nemotron-3.5-lightning"},
    "bulk":  {"nvidia": "nvidia/nemotron-3.5-lightning-30b-a3b",  "openrouter": "nvidia/nemotron-3.5-lightning", "local": "nemotron-3-nano:4b"},
}
CACHE = "agents/cache.jsonl"   # replay source for the judged notebook and the offline demo

def chat(role, messages, tools=None, thinking=True, max_tokens=8000):
    key = hashlib.sha256(json.dumps([role, messages, tools], sort_keys=True, default=str).encode()).hexdigest()
    hit = lookup(CACHE, key)                      # returns the stored assistant message or None
    if hit or os.getenv("KERNEL_REPLAY") == "1":
        return hit
    for name, base_url, env in PROVIDERS:
        if env and not os.getenv(env):
            continue
        client = OpenAI(base_url=base_url, api_key=os.getenv(env) if env else "ollama", timeout=120)
        kwargs = dict(model=MODELS[role][name], messages=messages,
                      temperature=1.0, top_p=0.95, max_tokens=max_tokens, seed=7)
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        if name == "nvidia":
            kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": thinking}}
        for attempt in range(3):
            try:
                msg = client.chat.completions.create(**kwargs).choices[0].message
                store(CACHE, key, name, msg)      # also append to trace.jsonl with latency and token counts
                return msg
            except Exception as err:              # 429, 5xx, 403: back off, then fall through to next provider
                time.sleep(2 ** attempt)
    raise RuntimeError("all providers failed")
```

Notes: `lookup`, `store` and (in 7.4) `format_fact` are small helpers to write; these recipes are sketches, not tested code. On OpenRouter, reasoning is controlled with the `reasoning` / `reasoning_effort` parameters the endpoints list (exact shape not re-verified today). If an endpoint rejects `parallel_tool_calls`, omit it and process `tool_calls` in order.

### 7.2 The loop

```python
def run_agent(role, system, user, tools, registry, max_steps=10):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for step in range(max_steps):
        msg = chat(role, messages, tools=tools)
        messages.append(msg.model_dump(exclude_none=True))     # keep tool_calls and reasoning fields
        if not msg.tool_calls:
            return msg.content, messages
        for call in msg.tool_calls:                            # normally exactly one
            try:
                args = registry[call.function.name].Args.model_validate_json(call.function.arguments)
                result = registry[call.function.name].run(args)
            except Exception as err:
                result = {"ok": False, "error": str(err)[:300]}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
            if call.function.name.startswith(("submit_", "finalize_", "cannot_answer")):
                return result, messages
    return {"ok": False, "error": "step limit"}, messages
```

### 7.3 Expression whitelist for the Scout

```python
import ast
BANDS = {"B", "G", "R", "RE1", "RE2", "RE3", "N", "N2", "S1", "S2", "VV", "VH"}
FUNCS = {"abs", "log", "sqrt"}
OK = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Constant, ast.Load,
      ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.Call)

def check_expression(expr: str) -> None:
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, OK):
            raise ValueError(f"not allowed: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in BANDS | FUNCS:
            raise ValueError(f"unknown token: {node.id}")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in FUNCS):
            raise ValueError("only abs, log, sqrt may be called")
```

### 7.4 Number-provenance linter

```python
import re
PLACEHOLDER = re.compile(r"\{\{f_\d+(\|[a-z0-9_]+)?\}\}")
DIGIT = re.compile(r"\d")

def unsourced_numbers(text: str) -> bool:
    return bool(DIGIT.search(PLACEHOLDER.sub("", text)))

def render(text: str, facts: dict) -> str:
    def sub(match):
        fid, _, fmt = match.group(0)[2:-2].partition("|")
        return format_fact(facts[fid], fmt)        # the only place a number is formatted
    return PLACEHOLDER.sub(sub, text)
```

### 7.5 Evaluation metrics

```python
def tool_call_f1(made, expected):                 # lists of (name, canonical_args_json), unordered
    made, expected = set(made), set(expected)
    tp = len(made & expected)
    p = tp / len(made) if made else 0.0
    r = tp / len(expected) if expected else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0

def pass_hat_k(results_by_task):                  # {task_id: [bool, bool, bool]}
    return sum(all(v) for v in results_by_task.values()) / len(results_by_task)
```

---

## 8. Formulas with band names (seed list for the Scout)

Band tokens follow the Awesome Spectral Indices catalog (opened today): `A, B, G, G1, R, Y, RE1, RE2, RE3, N, N2, S1, S2, T, T1, T2, WV` and radar `HH, HV, VH, VV`. **In this catalog `S1` and `S2` mean shortwave-infrared 1 and 2, not Sentinel-1 and Sentinel-2.** Sentinel-2 mapping (standard designations; the spyndex README confirms only N = B08 and R = B04): B = B2, G = B3, R = B4, RE1 = B5, RE2 = B6, RE3 = B7, N = B8, N2 = B8A, S1 = B11, S2 = B12. Sentinel-1 over the US supplies VV and VH.

Standard definitions, not re-verified against the catalog today; the tool must read formulas from `spectral-indices-dict.json` at run time:

| Index | Formula | What it should show |
|---|---|---|
| NDVI | (N - R) / (N + R) | greenness before the cut |
| NDMI | (N - S1) / (N + S1) | canopy water; silage is cut wet |
| NDRE | (N - RE1) / (N + RE1) | chlorophyll, less saturated than NDVI |
| GCVI | N / G - 1 | chlorophyll |
| PSRI | (R - B) / RE2 | senescence ("fades out" before grain harvest); verify in catalog |
| NDTI | (S1 - S2) / (S1 + S2) | crop residue after harvest |
| STI | S1 / S2 | crop residue after harvest |
| NBR2 | (S1 - S2) / (S1 + S2) | algebraically identical to NDTI: a test that the redundancy check works |
| VH/VV (catalog `VHVVR`) | VH / VV in linear power | canopy volume; drops at harvest |
| DpRVIVV | 4 * VH / (VV + VH) | radar vegetation index; verify in catalog |

Catalog facts: about 333 indices by the fetch tool's tally (the README states no total), including 12 radar vegetation indices (`DPDD, DpRVIHH, DpRVIVV, QpRVI, RFDI, VDDPI, VHVVD, VHVVP, VHVVR, VVVHD, VVVHR, VVVHS`) and `NDPolI`. Inference: `DpRVIHH`, `QpRVI` and `RFDI` need HH or HV and cannot be computed from Sentinel-1 VV + VH; the tool should reject them with a clear error rather than let the model improvise.

Temporal operators (my design, not from a source), applied to a per-date index series with cut date c:

| Operator | Definition |
|---|---|
| `level_pre(d)` | median over [c - d, c - 1] |
| `frac_of_peak_pre(d)` | `level_pre(d)` divided by the season maximum (our "green-at-cut") |
| `drop_across(d)` | median over [c + 1, c + d] minus median over [c - d, c - 1] |
| `slope_pre(d)` | robust slope per day over [c - d, c - 1] ("cliff" versus "fade") |
| `level_post(d)` | median over [c + 5, c + d] (residue versus bare soil) |
| `days_from_browning_to_cut` | cut date minus the date the index first falls below half its peak |
| `season_max`, `doy_of_max_slope` | season descriptors |

Search-space size (Inference): about 40 computable indices of interest x 8 operators x 4 windows is roughly 1,300 candidates. That is small enough to brute-force, which is why the brute-force run is the baseline and the Scout's claim is efficiency and explanation.

---

## 9. What this means for Kernel

**Changes to plan v2**

| Plan item | Verdict | Change |
|---|---|---|
| Index Scout "ranks candidate indices" | Keep, restructure | Pre-registered hypothesis ledger, county-grouped CV on a development split, cap of 60, brute-force baseline, one holdout confirmation, disclosed counts. Without these it is data dredging in front of statisticians |
| Analyst with SQL and map tools | Change | Parameterised query tools, not model-written SQL (BIRD 41.8 for Nemotron 3 Super; UnivEARTH code failures) |
| Per-field "Harvest Story" card | Keep | Lightning for volume; placeholders and digit linter; deterministic template as fallback |
| "Monday market memo" | Demote | Same code path as the Report Writer; no agentic behaviour; build last |
| Skeptic (new) | Add | Enumerated alternative checks; scored by error-catch recall versus false alarms |
| Reconciler (new) | Add | Rollup versus NASS with diagnosis tools; retrieval only for unexplained gaps |
| Framework | Decide now | Raw `openai` + `pydantic` loop. Not NeMo Agent Toolkit (deprecated), not LangGraph (not in our stack) |
| Model | Decide now | Super VL for reasoning and structure, Ultra as second opinion, Lightning for bulk; confirm ids with `GET /v1/models` |
| Demo | Decide now | Replay of a recorded trace; local Ollama model for live questions |

**Contribution to each judging line**
- Technical Quality: an agent scorecard (tool-call F1, rejection accuracy, pass^3, response time) next to the classifier's precision, recall and false-positive rate.
- Innovation: an agent-discovered, pre-registered harvest signal with a holdout confirmation; an agent that is allowed to be wrong and shows it.
- Feasibility and Mission Alignment: the Reconciler speaks NASS's language (state and county acres), and every figure is reproducible.
- Presentation: a replayable trace is a better demo than a chat box.
- Nemotron prize: multi-step plan-and-execute loops, about 15 real tools, retrieval on demand, optional vision second reader, and an evaluation of the agents themselves.

---

## 10. Annotated bibliography (all opened 2026-11-14 unless marked)

**Nemotron models and APIs**
1. NVIDIA model listing API. https://integrate.api.nvidia.com/v1/models (83 entries; exact ids). High.
2. NVIDIA API reference, LLM APIs. https://docs.api.nvidia.com/nim/reference/llm-apis (ids; base URL). High.
3. Nemotron 3 Super card. https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b (GA 2026-03-11; 120B/12B; tools; structured output supported; `enable_thinking`, `low_effort`; 8x H100 minimum). High.
4. Nemotron 3 Ultra card. https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b (2026-06-04; structured output "Not supported"; benchmark table; OpenMDW-1.1). High.
5. Nemotron 3.5 Lightning card. https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b (2026-08-11 preview; benchmarks; OpenMDW-1.1). High.
6. Nemotron 3.5 Super VL card. https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b (2026-10-15; text, image, video; benchmarks). High.
7. Nemotron 3 Nano Omni card. https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning (2026-04-28; weights 62 / 32.8 / 20.9 GB). High.
8. Nemotron 3.5 Bolt E4B card. https://build.nvidia.com/nvidia/nemotron-3.5-bolt-e4b (2026-10-23; single tool call per turn; BFCL v3 71.33). High.
9. Nemotron 3 Nano 30B card. https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b (2025-12-15; BFCL v4 53.8; sampling). High.
10. Nemotron Nano 9B v2 card. https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2 (`/think`, `/no_think`; 131,072 context). High.
11. Cosmos card (now Cosmos3-Nano-Reasoner). https://build.nvidia.com/nvidia/cosmos-reason2-8b (no function calling; physical AI). High.
12. Hugging Face, Nemotron 3 Super. https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16 (benchmarks incl. BIRD 41.80, TauBench V2). High.
13. Hugging Face, Nemotron 3.5 Lightning NVFP4. https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 (serve commands; hardware matrix; Ollama context tiers). High.
14. NVIDIA press release, 2025-12-15. https://nvidianews.nvidia.com/news/nvidia-debuts-nemotron-3-family-of-open-models High.
15. NVIDIA Nemotron developer page. https://developer.nvidia.com/nemotron (family roles; tutorial links). High.
16. OpenRouter NVIDIA provider page. https://openrouter.ai/nvidia (25 slugs). High.
17. OpenRouter endpoints API, e.g. https://openrouter.ai/api/v1/models/nvidia/nemotron-3.5-super-vl:free/endpoints and the same path for `nemotron-3-ultra-550b-a55b`, `nemotron-3.5-lightning`, `nemotron-3-super-120b-a12b`, `nemotron-3-nano-30b-a3b`, `nemotron-3-nano-omni-30b-a3b-reasoning`, `nemotron-nano-9b-v2`, each with and without `:free`. High (live data; will drift).
18. OpenRouter limits. https://openrouter.ai/docs/api-reference/limits High.
19. OpenRouter tool calling. https://openrouter.ai/docs/features/tool-calling High.
20. OpenRouter structured outputs. https://openrouter.ai/docs/features/structured-outputs High.
21. NVIDIA NIM FAQ (forum). https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317 (trial for prototyping; no published rate limit). Medium.
22. NVIDIA Nemotron forum category. https://forums.developer.nvidia.com/c/ai-data-science/nvidia-nemotron/669 (thread titles only). Low.
23. Ollama, nemotron-3-nano. https://ollama.com/library/nemotron-3-nano ; nemotron-3.5-lightning. https://ollama.com/library/nemotron-3.5-lightning High.
24. Unsloth, Nemotron 3 Ultra. https://unsloth.ai/docs/models/nemotron-3-ultra (GGUF sizes; about 40 tokens/s on 4x B200). Medium.

**NVIDIA agent tooling**
25. NeMo Agent Toolkit README. https://raw.githubusercontent.com/NVIDIA/NeMo-Agent-Toolkit/develop/README.md and https://github.com/NVIDIA/NeMo-Agent-Toolkit (deprecation notice). High.
26. NeMo Helix. https://github.com/NVIDIA-NeMo/nemo-helix ; NeMo Fabric. https://github.com/NVIDIA/NeMo-Fabric ; NVIDIA-NeMo organisation. https://github.com/NVIDIA-NeMo High.
27. NeMo Guardrails. https://github.com/NVIDIA-NeMo/Guardrails High.
28. NeMo Evaluator. https://github.com/NVIDIA-NeMo/Evaluator High.
29. NeMo Data Designer. https://github.com/NVIDIA-NeMo/DataDesigner High.
30. Nemotron asset hub. https://github.com/NVIDIA-NeMo/Nemotron ; use-case examples. https://github.com/NVIDIA-NeMo/Nemotron/tree/main/use-case-examples ; Data Science ML Agent. https://github.com/NVIDIA-NeMo/Nemotron/tree/main/use-case-examples/Data%20Science%20ML%20Agent ; Lightning cookbook. https://github.com/NVIDIA-NeMo/Nemotron/tree/main/usage-cookbook/Nemotron-3.5-Lightning ; DGX Station recipes. https://github.com/NVIDIA-NeMo/Nemotron/blob/main/usage-cookbook/Nemotron-3.5-Lightning/dgx-station-recipes/README.md High.
31. Report generator workshop blog, 2025-09-15. https://developer.nvidia.com/blog/build-a-report-generator-ai-agent-with-nvidia-nemotron-on-openrouter/ High.
32. RAG agent workshop blog, 2025-09-23. https://developer.nvidia.com/blog/build-a-rag-agent-with-nvidia-nemotron/ High.
33. Bash agent blog, 2025-10-22. https://developer.nvidia.com/blog/create-your-own-bash-computer-use-agent-with-nvidia-nemotron-in-one-hour/ High.
34. Workshop repo. https://github.com/brevdev/workshop-build-an-agent and https://github.com/brevdev/workshop-build-an-agent/tree/main/code/3-agent-evaluation High.
35. Prime Intellect fine-tuning blog, 2026-07-23. https://developer.nvidia.com/blog/start-customizing-nvidia-nemotron-3-nano-with-prime-intellect-lab-in-minutes/ High.
36. Brev docs: Launchables. https://docs.nvidia.com/brev/concepts/launchables ; deploying NIMs. https://docs.nvidia.com/brev/guides/inference-deployment/deploying-nims High.

**Judging precedents**
37. NeMo Agent Toolkit hackathon winners, 2025-07-17. https://developer.nvidia.com/blog/hackathon-winners-bring-agentic-ai-to-life-with-the-nvidia-nemo-agent-toolkit/ High.
38. NVIDIA and LangChain developer contest. https://www.nvidia.com/en-us/ai-data-science/generative-ai/developer-contest-with-langchain/ High.

**Earth-observation and geospatial agents**
39. Kao et al., "Towards LLM Agents for Earth Observation" (UnivEARTH), v3 2026-10-05. https://arxiv.org/abs/2504.12110 and https://arxiv.org/html/2504.12110 High.
40. Krechetova and Kochedykov, GeoBenchX, 2025. https://arxiv.org/abs/2503.18129 and https://arxiv.org/html/2503.18129 High.
41. Li and Ning, "Autonomous GIS" (LLM-Geo), 2023. https://arxiv.org/abs/2305.06453 High.
42. Chen et al., GeoAgent, 2024. https://arxiv.org/abs/2410.18792 Medium (abstract only).
43. Lee et al., GeoLLM-Squad, 2025. https://arxiv.org/abs/2501.16254 Medium (abstract only).
44. Shabbir et al., ThinkGeo, 2025 to 2026. https://arxiv.org/abs/2505.23752 Medium (abstract only).
45. Feng et al., Earth-Agent, ICLR 2026. https://arxiv.org/abs/2509.23141 Medium (abstract only).
46. Google Research, "Geospatial Reasoning", 2025-04-08. https://research.google/blog/geospatial-reasoning-unlocking-insights-with-generative-ai-and-multiple-foundation-models/ High.
47. Bell et al., Earth AI, 2025 to 2026. https://arxiv.org/abs/2510.18318 Medium (abstract only).
48. Microsoft, NASA Earth Copilot, 2024-11-14. https://blogs.microsoft.com/blog/2024/11/14/from-questions-to-discoveries-nasas-new-earth-copilot-brings-microsoft-ai-capabilities-to-democratize-access-to-complex-data/ High.
49. Irvin et al., TEOChat, ICLR 2025. https://arxiv.org/abs/2410.06234 Medium (abstract only).

**Feature discovery, reliability, evaluation**
50. Hollmann, Mueller, Hutter, CAAFE, 2023. https://arxiv.org/abs/2305.03403 and https://arxiv.org/html/2305.03403 High.
51. Abhyankar, Shojaee, Reddy, LLM-FE, TMLR. https://arxiv.org/abs/2503.14434 and https://arxiv.org/html/2503.14434 High.
52. DeepMind, FunSearch, 2023-12-14. https://deepmind.google/discover/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/ High.
53. Gottweis et al., AI co-scientist, 2025. https://arxiv.org/abs/2502.18864 Medium (abstract only).
54. Beel, Kan, Baumgart, evaluation of the AI Scientist, 2025. https://arxiv.org/abs/2502.14297 High.
55. karpathy/autoresearch. https://github.com/karpathy/autoresearch High.
56. Dwork et al., holdout reuse, 2015. https://arxiv.org/abs/1506.02629 High.
57. Chen et al., Program of Thoughts, TMLR 2023. https://arxiv.org/abs/2211.12588 High.
58. Islam et al., FinanceBench, 2023. https://arxiv.org/abs/2311.11944 High.
59. Jing et al., DSBench, 2024 to 2025. https://arxiv.org/abs/2409.07703 High.
60. Yao et al., tau-bench, 2024. https://arxiv.org/abs/2406.12045 High.
61. Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", 2025. https://arxiv.org/abs/2503.13657 High.
62. Asai et al., Self-RAG, 2023. https://arxiv.org/abs/2310.11511 High.
63. Anthropic, "Demystifying evals for AI agents", 2026-01-09. https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents High.
64. Anthropic, "Building effective agents", 2024-12-19. https://www.anthropic.com/engineering/building-effective-agents High.
65. RAGAS agent metrics. https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/ ; faithfulness. https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ High.
66. Awesome Spectral Indices. https://github.com/awesome-spectral-indices/awesome-spectral-indices ; spyndex. https://github.com/awesome-spectral-indices/spyndex (Montero et al., Scientific Data 10, 197, 2023). High.

---

## 11. Gaps and things not opened

- **No web search was available.** Niche queries in the brief (past "Nemotron prize track" winners, Earth Engine assistants, IBM and ESA Earth-observation agents, LLM-driven spectral-index discovery) could not be pursued. No source was found, in the pages opened, of an LLM agent discovering spectral indices for crop harvest; that absence is not evidence.
- Not opened: `nvidia-aws.devpost.com` and its gallery (HTTP 403); `hack-the-harvest.devpost.com` (403); `hacktheharvest.com` and `.org` (no DNS record); `docs.nvidia.com/nim/large-language-models/latest/function-calling.html` and `structured-generation.html` (rendered empty); the Nature FunSearch article (login redirect; DeepMind's blog used instead); `openrouter.ai/api/v1/models` (returned an unrelated listing; the per-model endpoints API worked).
- Abstract-only sources (items 42 to 45, 47, 49, 53) give no numbers beyond those quoted.
- Forum thread titles (item 22) are leads, not evidence.
- Unknown and worth asking an organiser: which Nemotron access is provided, its rate limit, and whether the Keeboh workspace allows outbound calls to `integrate.api.nvidia.com` and `openrouter.ai`.
- OpenRouter endpoint availability, prices and uptime are live values from this afternoon and can change before the pitch.
