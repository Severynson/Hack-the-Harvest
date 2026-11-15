# NVIDIA Brev runbook for team Kernel (Hack the Harvest, 14-15 Nov 2026)

Researched Saturday 2026-11-14. Scope: instances, prices, access, Launchables, hosting Nemotron, tooling, reliability, and a cost plan for a 60-dollar credit.

Method note. 15 distinct web searches were run before the shared search budget for this workflow turn was exhausted (two further searches, on "Share a Service / public URL" and "idle auto-stop", were refused). Everything after that was done by opening known primary URLs directly. Every claim below carries the URL that was actually opened. Lines starting with "Inference:" are my reasoning, not something a source states. Items that could not be opened are listed in section 12.

---

## 0. Bottom line (read this first)

1. **Brev publishes no fixed price list.** Prices vary by GPU, provider and region and are shown live by `brev search --sort price` and on the console instance cards. Run that command before anything else. With third-party estimates, 60 dollars is roughly 17 h of H100, 30-60 h of L40S, 60-80 h of A10G or 130+ h of L4.
2. **Recommended instance: one single-GPU 48 GB card (L40S class), flagged stoppable, left running continuously for the ~18-20 h**, budget ceiling 2.00 dollars/h (= 40 dollars for 20 h, 20 dollars reserve). If the live L40S price is above about 2.20 dollars/h, drop to a 24 GB A10G or L4 (about 0.45-1.00 dollars/h) and serve a smaller Nemotron.
3. **Do not stop and restart to save money.** A stopped instance restarts only if the same GPU type is free in the same provider and region; if not, the restart fails and the disk is unreachable. Saving 3 h at 1.50 dollars/h is 4.50 dollars; losing the box at 3 a.m. costs the night.
4. **When credits hit zero, Brev pauses stoppable instances and DELETES instances that cannot be paused.** Use `--stoppable`, push to GitHub often, watch the burn-rate indicator.
5. **The demo must not depend on Brev.** Console tunnel URLs require a Brev browser login on first access, so judges cannot open them cold. The judged notebook lives in Keeboh and should read cached artifacts from the repo and call Nemotron through the hosted API, with the Brev endpoint as an optional `base_url` swap.
6. **Nemotron has moved on from the 2025 workshop material.** The current small agent model is Nemotron 3.5 Lightning (30B total / 3B active, released 2026-08-11, tools + thinking). It needs 32 GB VRAM in 4-bit (W4A16) under NIM, so it fits an L40S; on 24 GB cards use Nemotron 3 Nano 4B, Nemotron Nano 9B v2 or Nemotron 3.5 Bolt E4B.
7. **Self-hosting is what removes rate limits** for a multi-agent loop: hosted build.nvidia.com is about 40 requests/min (user-observed), OpenRouter free variants are 20 requests/min and 50 requests/day unless 10 dollars of credits were ever purchased (then 1,000/day).
8. **RAPIDS 26.10 needs Python 3.11 or newer**, while Brev VM mode advertises "Python 3.10+". Build a Python 3.12 venv with uv or use the RAPIDS container. XGBoost's default wheel is now built for CUDA 13; older drivers need `xgboost-cu12`.

---

## 1. Instances, prices, billing, persistence, credits

### 1.1 Prices: what is and is not known

| Source | Date | What it says | Reliability |
|---|---|---|---|
| Brev docs, GPU Instances | opened 2026-11-14 | "Brev bills you per hour for compute time"; billing is per hour and depends on GPU type. No rates listed. | Official, no numbers |
| Brev docs, CLI Search and Discovery | opened 2026-11-14 | Sample `brev search` output: `g5.xlarge A10G 1 24GB 24GB $1.00 2m S R P`; `g5.2xlarge A10G ... $1.20`; `p4d.24xlarge A100 x8 ... $32.77`. | Official but illustrative sample output |
| computecomparison.com/provider/brev-dev | "retrieved 5m ago" on 2026-11-14 | T4 16 GB 0.35; L4 24 GB 0.44; A10G 24 GB 0.75; RTX 4090 0.76; A100 40 GB 1.10; A100 80 GB 2.21; H100 80 GB 3.50 (dollars/h, on-demand, US, no spot). Page says "Prices are estimates", cheapest region, single instance. | Third-party aggregator, medium-low |
| Classmethod article | 2026-01-25 | "General range" estimates: A100 80 GB 1.00-2.00; H100 80 GB 2.00-5.00; L40S 1.00-2.00 dollars/h; the article notes that prices fluctuate. | Third-party, ranges only |
| Miami Mike blog | 2026-08-31 | Prepaid credits drawn down hourly; the rate varies by GPU, provider and region; the console shows the rate on each instance card. No numbers. | Third-party, consistent with docs |

Market context (not Brev): gpuperhour.com on 2026-11-14 showed secure on-demand L40S from 0.97 dollars/h (Massed Compute), A100 80 GB PCIe 0.68, H100 PCIe 2.59 dollars/h.

**What 60 dollars buys (and what 18 h costs), using the numbers above. Verify with `brev search` before committing.**

| GPU | VRAM | Assumed dollars/h | Hours for 60 dollars | Cost of 18 h |
|---|---|---|---|---|
| T4 | 16 GB | 0.35 (third-party) | 171 | 6.30 |
| L4 | 24 GB | 0.44 (third-party) | 136 | 7.90 |
| A10G | 24 GB | 0.75 (third-party) to 1.00 (docs sample) | 80 to 60 | 13.50 to 18.00 |
| L40S | 48 GB | 1.00 to 2.00 (Jan 2026 range) | 60 to 30 | 18.00 to 36.00 |
| A100 80 GB | 80 GB | 1.00 to 2.21 | 60 to 27 | 18.00 to 39.80 |
| H100 | 80 GB | 2.00 to 5.00 (3.50 third-party) | 30 to 12 (17 at 3.50) | 36.00 to 90.00 (63.00 at 3.50) |

GPU catalogue (Brev docs, GPU Types reference): B200, H200, H100, A100 80GB, L40S, L40, L4, RTX 6000 Ada, RTX 4000 Ada, RTX PRO Server 6000, A10G, A16, A6000, A5000, A4000, RTX 5090, T4, V100, P4. The VRAM column as read through the fetch tool gave L4 22, A10G 22, L40S 44, H100 96 GB; the `brev search` sample output shows A10G as 24GB. Treat the nominal values (L4 24, A10G 24, L40S 48, H100 80) as the planning figures and the lower numbers as usable memory.

### 1.2 Billing and lifecycle (Brev docs: GPU Instances, Console Reference)

- Lifecycle: Create -> Running <-> Stopped -> Deleted.
- Running: billed per hour based on GPU type.
- Stopped: GPU is released to the provider pool; no compute charges, but minimal storage costs apply. The amount of the storage charge is not stated.
- Deleted: no charges; instance and all data removed permanently.
- Restart of a stopped instance: Brev tries the same GPU type in the same provider and region. If capacity is unavailable the restart fails and the data stays inaccessible until capacity returns or you delete the instance. The doc advises pushing important work to Git before stopping.
- A stopped instance cannot change GPU type; delete and recreate to switch.
- Out of credits: Brev "pauses any instances that have stop-start ability"; "Instances that cannot be paused are deleted." A further warning follows after 24 hours, after which Brev deletes all remaining resources. Deleted data cannot be recovered.
- Resource limits: an organization "may have a maximum allowed resource usage rate, shown in dollars per hour"; to raise it, email brev-support@nvidia.com. Inference: a brand-new student org may be capped, which can block an H100 or multi-GPU type.
- Console creation flow: Create Instance -> choose GPU type -> name, base image or Launchable, Setup values, disk size -> Create. "Setup typically takes 1-2 minutes."
- Auto-stop on idle: **not mentioned anywhere in the pages opened** (GPU Instances, Console Reference, CLI pages). Inference: assume there is none; a forgotten instance burns until the balance is gone.

### 1.3 Data persistence (Brev docs: GPU Instances, Environments)

| Location | Persists on stop | Persists on delete |
|---|---|---|
| `/home/ubuntu/workspace` | Yes | No |
| `/tmp` | No | No |
| System packages | Yes | No |
| Docker images and containers | Yes | No |

Default user is "ubuntu for most providers"; working directory `/home/ubuntu/workspace`. VM mode ships Ubuntu with Python 3.10+, CUDA Toolkit, cuDNN, NVIDIA drivers, Docker, Docker Compose, NVIDIA Container Toolkit, and JupyterLab when enabled.

### 1.4 Credit redemption flow

- Console -> Billing -> Credits offers "Add funds" and "Redeem a credit code" (Console Reference; steps not described further).
- "Your credit balance is shared across the organization." Redeem while the team organization is selected.
- The balance indicator shows the current balance and, while resources run, an estimated burn rate and remaining hours.
- Auto recharge exists (threshold and amount, needs a saved payment method). Inference: leave it off unless someone wants a card charged.
- The CLI has a `redeem` command (it exists in the brev-cli source tree and is named in brev.nvidia.com/llms.txt under org context) but its syntax is not in any page opened. Use `brev redeem --help`.

---

## 2. CLI and access paths

All commands below are copied from the Brev docs pages cited in section 11 unless marked otherwise.

### 2.1 Install and log in

```bash
# macOS
brew install brevdev/homebrew-brev/brev
brev --version

# Linux / WSL (do not run with sudo)
bash -c "$(curl -fsSL https://raw.githubusercontent.com/brevdev/brev-cli/main/bin/install-latest.sh)"
brev --version

# Log in
brev login                          # browser OAuth
brev login --skip-browser           # prints the URL
brev login --token "<TOKEN>"        # headless; copy from https://brev.nvidia.com/settings/cli
brev login --api-key "<API_KEY>"    # org-scoped Brev API key, saved to ~/.brev/credentials.json
```

If the installer prints `Error: Failed to fetch release info from GitHub API.` the GitHub API rate limit was hit (common on shared conference Wi-Fi): `export GITHUB_TOKEN="<TOKEN>"` or `gh auth login`, then re-run.

After login the CLI saves the key at `~/.brev/brev.pem` and manages `~/.brev/ssh_config`, which is included from `~/.ssh/config`, so `ssh <instance-name>` works.

### 2.2 Find and create

```bash
brev search --sort price                                   # all GPUs, cheapest first
brev search --gpu-name L40S --sort price
brev search --stoppable --min-total-vram 40 --sort price   # stoppable, 40 GB or more
brev search --max-boot-time 3 --sort price
brev search --json | jq '.[] | {type, gpu_name, price}'
brev search cpu --min-vcpu 16 --sort price                 # CPU-only boxes for I/O-bound extraction

brev create my-instance --gpu-name A100 --dry-run          # preview, creates nothing
brev create my-instance --type g5.xlarge,g5.2xlarge,g5.4xlarge   # fallback chain, tried in order
brev create my-instance --gpu-name A100 --min-vram 40
brev create my-instance -s @setup.sh                       # startup script from a local file
brev create my-instance --detached                         # do not wait
```

- `brev search` columns: `TYPE GPU COUNT VRAM TOTAL $/HR BOOT FEATURES`. FEATURES codes: **S** stoppable, **R** rebootable, **P** flex ports (firewall rules can be modified).
- `brev create` flags: `--name/-n`, `--type/-t` (comma-separated fallback chain), `--count/-c`, `--parallel/-p`, `--startup-script/-s` (inline or `@file`), `--timeout` (default 300 s), `--detached/-d`, `--dry-run`; the search filters also work on create (`--gpu-name/-g`, `--provider`, `--min-vram/-v`, `--min-total-vram`, `--min-capability`, `--min-disk`, `--max-boot-time`, `--stoppable`, `--rebootable`, `--flex-ports`, `--sort`, `--desc`).
- Smart defaults when no type or filter is given: 20 GB minimum total VRAM, 500 GB minimum disk, compute capability 8.0+, boot under 7 minutes, cheapest first.
- Docs inconsistency: the Quickstart shows `brev create my-instance --gpu "nebius.l40sx1.pcie"` while the CLI reference documents `--type`. Run `brev create --help` on the installed version.
- Per the CI/CD guide, `brev create` can report success even when it has merely stopped waiting for the instance. Confirm with `brev ls` before the next step.

### 2.3 Manage

```bash
brev ls                      # alias: brev list ; brev ls --json (rows under .workspaces)
brev start my-instance
brev stop my-instance        # brev stop --all stops every instance of yours in the org
brev delete my-instance      # irreversible
brev reset my-instance       # clears the container, keeps persistent storage
brev refresh                 # re-sync ~/.brev/ssh_config; run after any restart (IP may change)
brev scale my-instance --gpu A100     # stops and restarts the instance
```

### 2.4 Connect

```bash
brev shell my-instance                 # interactive SSH (alias: brev ssh)
ssh my-instance                        # same, through the managed ssh config
brev exec my-instance "nvidia-smi"     # non-interactive; QUOTE the whole command
brev exec my-instance @setup.sh        # run a local script remotely
brev exec my-instance "nohup python train.py > /dev/null 2>&1 &"
brev open my-instance                  # VS Code (Remote - SSH)
brev open my-instance cursor           # also: windsurf, tmux
brev open --set-default cursor
brev copy ./local-file.txt my-instance:/home/ubuntu/
brev copy -r ./my-project my-instance:/home/ubuntu/
brev copy my-instance:/home/ubuntu/results.csv ./
scp -r -i ~/.brev/brev.pem ./my-folder ubuntu@<instance-ip>:/home/ubuntu/
```

`--host` on shell / exec / open / copy / port-forward targets the host VM instead of the container. Without quotes, `brev exec my-instance python train.py` looks for an instance called `python`.

### 2.5 Ports, Jupyter, public URLs

```bash
# Private: SSH tunnel to your laptop (recommended for APIs; no auth prompt)
brev port-forward my-instance --port 8888:8888     # local:remote, one mapping per command
brev port-forward my-instance --port 8000:8000
ssh -N -L LOCAL_PORT:localhost:REMOTE_PORT my-instance

# JupyterLab on the instance
brev shell my-instance
jupyter lab --no-browser --port=8888               # copy the URL with ?token=...
```

Common ports per the docs: Jupyter 8888, TensorBoard 6006, Streamlit 8501, Gradio 7860.

Three ways to give someone else a URL:

| Path | How | Who can open it | Source |
|---|---|---|---|
| Console tunnel | Instance -> Access -> "Using Tunnels" -> enter port -> Add -> copy URL (looks like `jupyter0-i55ymhsr8.brevlab.com`) | "Tunnels route through Cloudflare and require browser authentication on first access." | Brev Console Reference; RAPIDS deployment docs |
| Launchable network settings | Secure Link protects an HTTP service with Brev authentication; TCP/UDP Ports expose a port or range to all IP addresses or only to the deployer's IP | Secure Link: Brev-authenticated users. TCP port to all IPs: anyone | Brev Launchables concept page |
| `brev ports` (beta) | `brev ports open my-instance 3000 --protocol http --public`; `brev ports open my-instance 8888 --protocol http --authorize me@example.com`; `brev ports ls my-instance`; `brev ports remove my-instance 8080` | Public if `--public` | NVIDIA's own agent skill file in the brev-cli repo; the docs site only documents `brev ports ls` and `brev ports close` as beta |

Inference: for a judge-facing link, only the `--public` port or a TCP port opened to all IPs will work without a Brev account, and both depend on the provider supporting flex ports (FEATURES code P). Treat a public Brev URL as a bonus and keep the demo runnable from Keeboh plus a recorded backup.

### 2.6 Organizations, teammates and coding agents

What the docs state:
- Team page -> "Generate Invite Link"; "The link expires in 7 days." CLI: `brev invite`. Members can have roles changed and be removed.
- Switch org: `brev org ls`, `brev org set my-org` (alias `brev set my-org`).
- Credits are shared across the org.
- Brev API keys: Account Settings -> API Keys -> Create; Name, Access "Read" or "Read & Write", expiry (default 30 days), one organization per key, acts as the creating user, value shown once. Use `brev login --api-key "<key>"` or the `BREV_API_KEY` environment variable, then `brev refresh` for SSH access.
- `brev ssh-key` prints your public key; `brev ssh-key add ~/.ssh/id_rsa.pub` adds another (the Advanced Commands page says extra keys can be added for teammates or CI/CD systems; it does not say whether they reach instances that are already running).
- `brev agent-skill` installs a Brev skill for AI coding agents such as Claude Code.
- NVIDIA's guidance to agents (brev.nvidia.com/llms.txt): inspect with `brev ls` first; treat `brev create` and some `brev start` calls as billable; obtain explicit user approval before creating, starting, stopping, deleting or resetting instances or spending; **`brev shell`, `brev open` and `brev copy` can start stopped instances**, so confirm before using them on stopped resources; use `brev exec` for non-interactive commands.
- `brev grant-ssh` / `enable-ssh` / `register` belong to Brev Connect, which is for hardware you own (DGX Spark and similar), not rented cloud instances.

What the docs do not state: any way for one org member to attach to another member's cloud instance, or which roles can see or stop other members' instances.

Inference (the pattern to use for "several teammates and agents on ONE instance"):
1. One person owns the instance. Teammates send their public SSH keys; the owner appends them to `/home/ubuntu/.ssh/authorized_keys` and shares the IP from `~/.brev/ssh_config`. Plain `ssh ubuntu@<ip>` then works for everyone (the docs themselves show direct `scp -i ~/.brev/brev.pem ... ubuntu@<instance-ip>`, so port 22 on the public IP is the normal path). Test this in the first ten minutes.
2. Each coding agent gets its own clone under `/home/ubuntu/workspace/<agent-name>/` and its own tmux session; the repo stays the only communication channel.
3. Do not give agents a Read & Write Brev API key. Agents that only need to run code use SSH or `brev exec`. If an agent must call the Brev CLI, give it a Read key.
4. If per-person instances are preferred, everyone joins the one org and creates their own small instance against the shared balance, which multiplies the burn rate.

---

## 3. Launchables

### 3.1 What they are (Brev docs, Launchables concept page)

A Launchable is a shareable, reproducible environment configuration that bundles compute, software, code and launch-time inputs into a one-click deploy link; anyone with access deploys an identical environment from it.

| Setting | Options |
|---|---|
| Details | Name (required; "it cannot be changed after the Launchable is created") and description |
| Default hardware | GPU or CPU type, disk storage (GiB), optional location; deployers may pick different compute |
| Runtime | VM Mode (Python, CUDA, Docker; optional Jupyter; optional setup script) / Single Container / Docker Compose (local file or GitHub or GitLab URL) / single-node Kubernetes (beta) |
| Source | None, or "a public repository, notebook, or Markdown file URL". Private repos are not described as supported. |
| Network | Secure Link (name + port, Brev-authenticated) and TCP/UDP ports (all IPs or only the deployer's IP) |
| Launch parameters | Per-deployer values passed as environment variables; Text or Choice; Text can bind an organization secret; names uppercase with underscores, `BREV_` prefix reserved; "Do not store reusable credentials as parameter defaults." |
| View access | "Anyone with the link" (default), "Only my organization", or "Publish to community" |
| Extras | View Metrics (views, deploys); "Copy Markdown Badge" gives a "Launch on Brev" button for a README |

Caveat: parameters are not persistent VM-wide variables; in VM Mode they are not inherited by later SSH sessions.

### 3.2 Create one from our GitHub repo (steps from the docs)

1. Console -> Launchables -> Create Launchable (direct: brev.nvidia.com/launchables/create).
2. Name `kernel-silage-grain` (final; cannot be renamed), description.
3. Default hardware: the same type we run tonight; disk 200 GiB or more.
4. Runtime: VM Mode with Jupyter on, plus a setup script (below); or Docker Compose with the RAPIDS image.
5. Source: the public repo URL. It is cloned on the host at `/home/ubuntu/<repo-name>` (RAPIDS deployment docs).
6. Network: Secure Link on 8888 named `jupyter`; add 8000 if the Nemotron endpoint should be reachable.
7. Launch parameters: `NGC_API_KEY`, `NVIDIA_API_KEY`, `EE_PROJECT` as Text parameters, each bound to an org secret at deploy time.
8. View access: Anyone with the link. Create, then "Copy Markdown Badge" into the README.

Docker Compose recipe from the RAPIDS deployment docs (image tag is their nightly example; pick the stable 26.10 tag in the console's RAPIDS container selector):

```yaml
services:
  jupyter:
    image: "rapidsai/notebooks:26.12a-cuda13-py3.14"
    pull_policy: always
    ulimits:
      memlock: -1
      stack: 67108864
    shm_size: 1g
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - EXTRA_CONDA_PACKAGES # Value comes from a launch parameter of the same name
    ports:
      - "8888:8888" # Expose JupyterLab
    volumes:
      - /home/ubuntu/<name_of_your_github_repo>:/home/rapids/notebooks/<name_of_your_github_repo>
    user: root
    command: jupyter-lab --notebook-dir=/home/rapids/notebooks --ip=0.0.0.0 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.allow_origin='*'
    restart: unless-stopped
```

Notes from the same page: leave "Install Jupyter on the host" off when the container serves JupyterLab; the Launchable may report the build finished one or two minutes before JupyterLab is ready; git is not preinstalled inside the RAPIDS container (`apt update && apt install git -y`); L4 GPUs are suggested for trying things out. A RAPIDS deployment-docs GitHub issue (October 2026, seen in search results only) reports "Open Notebook" staying disabled for a long time after the instance shows Running.

### 3.3 NVIDIA-provided Launchables and workshops relevant to us

| Item | What it is | Verified detail | URL |
|---|---|---|---|
| Build an Agent Workshop | 7 modules, about 14-21 h total, runs in a DevX-Lab container with JupyterLab | Module 1 "Build an Agent" (1-2 h): Report Generation Agent that researches, outlines, writes sections, compiles; LangChain / LangGraph ReAct. Module 2 "Agentic RAG" (2-3 h): IT Help Desk agent with NeMo Retriever embeddings and reranking, FAISS. Module 3 evaluation (RAGAS, LLM-as-judge). Module 5 Deep Agents (planning, sub-agent delegation, file-backed memory). | https://brev.nvidia.com/launchable/deploy?launchableID=env-32kC34ErT9wsqTcJyaKMxBEuhr2 ; repo https://github.com/brevdev/workshop-build-an-agent |
| Report generator blog | The Module 1 design written up | Graph: START -> `topic_research` -> `report_planner` -> `section_author_orchestrator` -> `report_author` -> END, in `code/docgen_agent/agent.py`. Uses `ChatNVIDIA(base_url="https://openrouter.ai/api/v1", model="nvidia/nemotron-nano-9b-v2:free", api_key=os.getenv("OPENROUTER_API_KEY"))` and `llm.bind_tools([tools.search_tavily])`. Needs OpenRouter and Tavily keys. Published 2025-09-15. | https://developer.nvidia.com/blog/build-a-report-generator-ai-agent-with-nvidia-nemotron-on-openrouter |
| RAG agent blog | Agentic retrieval with LangGraph | Listed on the Nemotron developer page; not opened | https://developer.nvidia.com/blog/build-a-rag-agent-with-nvidia-nemotron/ |
| RAPIDS on Brev | Console "Single Container" with the NVIDIA RAPIDS container selector, or the Compose Launchable above | L4 suggested | https://rapids-deployment.readthedocs.io/en/latest/cloud/nvidia/brev/ |
| brevdev/launchables repo | 30 older notebook Launchables | "Accelerate Data Science using NVIDIA RAPIDS" (`rapids_cudf_pandas`, min 1x A10G); many LLM fine-tune notebooks (mostly 1x A10G); repo also holds `nim-quickstart.ipynb`, `RAG_WIth_Local_NIM_V2.ipynb`, `nvidia_nim_agents_llama3.1.ipynb`. No Nemotron or cuML entry in the README table. | https://github.com/brevdev/launchables |
| Nemotron cookbooks | Deployment and agent recipes per model | `usage-cookbook/Nemotron-3.5-Lightning` has `vllm_cookbook.ipynb`, `sglang_cookbook.ipynb`, `trtllm_cookbook.ipynb`, `lora-text2sql`, `OpenScaffoldingResources` (agentic coding tool configs for the hosted API or a local vLLM) | https://github.com/NVIDIA-NeMo/Nemotron |

Caveat: the 2025 report-generator material hard-codes `nvidia/nemotron-nano-9b-v2:free`. That id is not in the OpenRouter free list verified 2026-10-28, so expect to change the model id.

The Launchable deploy pages themselves are JavaScript-only; their default compute and hourly price could not be read.

---

## 4. Running Nemotron on Brev

### 4.1 The Nemotron line-up as of November 2026 (Hugging Face API listing of the nvidia org, opened 2026-11-14)

| Model | Size | Released | Licence | Notes |
|---|---|---|---|---|
| Nemotron 3.5 Bolt E4B | 8B total / 4B effective, Gemma-4-E4B base | 2026-10-23 | OpenMDW-1.1 | GGUF Q4_K_M file 6.18 GB; 64K context |
| Nemotron 3 Nano 4B | 3.97B, compressed from Nano 9B v2 | 2026-03-16 | NVIDIA Nemotron Open Model License | context up to 262K; supported hardware lists A10G |
| Nemotron Nano 9B v2 | 9B | 2025-08-18 | NVIDIA Open Model License | 128K context; test hardware A10G 24 GB |
| Nemotron 3 Nano 30B-A3B | 30B total / 3.5B active, Mamba2-Transformer MoE | 2025-12-15 | NVIDIA Nemotron Open Model License | BF16, FP8, NVFP4 checkpoints; up to 1M context |
| Nemotron 3.5 Lightning 30B-A3B | 30B / 3B active | 2026-08-11 | OpenMDW-1.1 | BF16 and NVFP4; tools and thinking; 1M context |
| Nemotron 3.5 Bolt 74B-A9B-24GB | 74B / 9B active, 2-bit IQ2 | 2026-10-15 | OpenMDW-1.1 | "24GB packed model"; needs a nightly vLLM build |
| Nemotron 3 Super 120B-A12B, 3.5 Super VL, 3 Ultra 550B-A55B | 120B and 550B | 2026 | mixed | multi-GPU only; use hosted |

### 4.2 Which model fits which Brev GPU

| Model | Evidence on memory | T4 16 | L4 / A10G 24 | L40S 48 | A100 80 / H100 80 |
|---|---|---|---|---|---|
| Bolt E4B (Q4_K_M) | GGUF 6.18 GB (HF card) | yes | yes | yes | yes |
| Nemotron 3 Nano 4B | Unsloth: "runs on 5GB"; 4-bit about 3 GB, 8-bit 5 GB. HF card lists A10G as supported. Inference: BF16 weights about 8 GB | yes (Inference) | yes | yes | yes |
| Nemotron Nano 9B v2 (BF16) | 21.9 GiB at READY with 4k context and 32 sequences on an RTX 5090 (forum benchmark); A10G 24 GB is listed test hardware | no | tight; lower `--max-num-seqs` | yes | yes |
| Nemotron 3 Nano 30B, NVFP4 | 21.0 GiB at 4k context / 32 seqs, about 25 GiB at 256 seqs on RTX 5090; the FP8 build did not fit in 32 GB (forum). NIM lists A10G, L40S and A100-40GB among verified GPUs for this model without saying which precision or tensor-parallel profile | no | Inference: marginal on one card; the A10G listing probably means multi-GPU | yes | yes |
| Nemotron 3 Nano 30B, GGUF | Q4_0 18.2 GB, UD-Q4_K_XL 22.8 GB, Q4_K_M 24.6 GB, Q8_0 33.6 GB, BF16 63.2 GB (Unsloth repo); Unsloth guide: 4-bit about 24 GB, 8-bit 36 GB | no | Q4_0 only, small context | yes (Q4 to Q8) | yes |
| Nemotron 3 Nano 30B, BF16 | 58 GB on disk, 120 GB idle VRAM on a B200 because vLLM pre-allocates (Lambda docs) | no | no | no | yes (single GPU) |
| Nemotron 3.5 Lightning, NIM | Minimum VRAM per GPU: BF16 TP1 66 GB; W4A16 TP1 32 GB; NVFP4 TP1 30 GB but Blackwell only. Model cache 19 GB (NVFP4) to 63 GB (BF16). Verified GPUs: L40S (BF16 TP>=2, W4A16 all sizes), A100-80GB, H100, H200, Blackwell. Figures "do not include additional headroom for large KV caches". | no | no | **yes, W4A16** | yes |
| Nemotron 3.5 Lightning, Ollama | `nemotron-3.5-lightning` 19-25 GB; context set by VRAM: under 24 GB -> 4K, 24-48 GB -> 32K, 48 GB+ -> 256K | no | 4K context only | yes (32K) | yes (256K) |
| Bolt 74B-A9B-24GB | Targets under 24 GB at batch 1 / 128K; tested on H100, H200, GB200, RTX 5090, DGX Spark; card is contradictory about Ampere support; needs `vllm/vllm-openai:nightly-...` plus `pip install b12x` | no | untested, risky | untested | possible |

Precision note from the Lightning card: Hopper and Ampere have no FP4 tensor cores, so NVFP4 checkpoints run through a W4A16 path there; Blackwell is not required.

### 4.3 Serving options

**Option A - Ollama (lowest effort, OpenAI-compatible, tools supported)**

```bash
ollama run nemotron-3.5-lightning                                   # validated on Ollama 0.32.9; tools + thinking
ollama run hf.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB:Q4_K_M      # 24 GB cards and below
ollama run hf.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF:UD-Q4_K_XL
```

OpenAI-compatible base URL `http://localhost:11434/v1/`, `api_key='ollama'` (required but ignored). `/v1/chat/completions` supports streaming, JSON mode, tools and reasoning control. Context is changed with a Modelfile (`FROM <model>` + `PARAMETER num_ctx <n>`, then `ollama create`). The Ollama Linux install one-liner was not re-verified today.

**Option B - vLLM (best throughput and concurrency; exact commands from the model cards)**

Nemotron 3 Nano 4B on a 24 GB card:

```bash
pip install -U "vllm>=0.15.1"
wget https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/resolve/main/nano_v3_reasoning_parser.py

vllm serve nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 \
  --served-model-name nemotron3-nano-4B-BF16 \
  --max-num-seqs 8 \
  --tensor-parallel-size 1 \
  --max-model-len 262144 \
  --port 8000 \
  --trust-remote-code \
  --mamba_ssm_cache_dtype float32 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser-plugin nano_v3_reasoning_parser.py \
  --reasoning-parser nano_v3
```

Inference: on 24 GB drop `--max-model-len` to 32768 to keep KV-cache memory small.

Nemotron 3 Nano 30B FP8 (Hopper or Blackwell; 256k context) from the model card:

```bash
pip install -U "vllm>=0.12.0"
wget https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8/resolve/main/nano_v3_reasoning_parser.py

VLLM_USE_FLASHINFER_MOE_FP8=1 \
vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8 \
  --served-model-name model \
  --max-num-seqs 8 \
  --tensor-parallel-size 1 \
  --max-model-len 262144 \
  --port 8000 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser-plugin nano_v3_reasoning_parser.py \
  --reasoning-parser nano_v3 \
  --kv-cache-dtype fp8
```

Nemotron 3.5 Lightning NVFP4 weights on Ampere (A100) through W4A16, image `vllm/vllm-openai:v0.27.1`, from the model card:

```bash
VLLM_HUMMING_MOE_GEMM_TYPE=indexed \
vllm serve --model nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 \
    --moe-backend humming \
    --linear-backend humming \
    --max-num-seqs 256 \
    --max-num-batched-tokens 32768 \
    --enable-prefix-caching \
    --async-scheduling \
    --quantization modelopt_fp4 \
    --mamba-backend flashinfer \
    --mamba-cache-mode align \
    --mamba-ssu-algorithm simple \
    --reasoning-parser nemotron_v3 \
    --tool-call-parser qwen3_coder \
    --enable-auto-tool-choice
```

Nemotron Nano 9B v2 with tool calling (non-streaming parser), vLLM 0.10.1 or newer:

```bash
git clone https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2
vllm serve nvidia/NVIDIA-Nemotron-Nano-9B-v2 \
  --trust-remote-code \
  --mamba_ssm_cache_dtype float32 \
  --enable-auto-tool-choice \
  --tool-parser-plugin "NVIDIA-Nemotron-Nano-9B-v2/nemotron_toolcall_parser_no_streaming.py" \
  --tool-call-parser "nemotron_json"
```

A clean vLLM install pattern (Lambda docs): `curl -LsSf https://astral.sh/uv/install.sh | sh`, `uv venv --python 3.12 --seed`, `source .venv/bin/activate`, `uv pip install vllm --torch-backend=auto`.

Bolt E4B under vLLM: add `--enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4`.

**Option C - NIM container (NGC key; the "NVIDIA stack" story for the Nemotron award)**

From the Brev "Deploying NVIDIA NIMs" guide (use VM Mode; the guide recommends an L40S 48 GB or A100 80 GB) and the NIM quickstart:

```bash
docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi          # GPU visible to Docker?
export NGC_API_KEY=<your-ngc-api-key>
echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
export LOCAL_NIM_CACHE=~/.cache/nim
mkdir -p "$LOCAL_NIM_CACHE"

# Shape of the command (from a working forum run of Nemotron 3 Nano on NIM 2.0.12)
docker run -d --gpus all -p 8000:8000 \
  -e NGC_API_KEY \
  -e NIM_MAX_MODEL_LEN=8192 \
  -v ~/.cache/nim:/opt/nim/.cache \
  nvcr.io/nim/nvidia/nemotron-3-nano:2.0.12

curl -v http://localhost:8000/v1/health/ready
curl -s http://localhost:8000/v1/models
```

- Other knobs seen working: `-e NIM_MODEL_PROFILE=<profile id>` to force a precision profile, `NIM_PASSTHROUGH_ARGS="--max-num-seqs 32"` to cut the sequence cap (the forum author found `NIM_MAX_BATCH_SIZE` did not reach the engine), `-e NIM_SERVED_MODEL_NAME=...`.
- Lightning's NGC catalogue path is `catalog.ngc.nvidia.com/orgs/nim/teams/nvidia/containers/nemotron-3.5-lightning-30b-a3b` and its model id is `nvidia/nemotron-3.5-lightning-30b-a3b`. Inference: the image is `nvcr.io/nim/nvidia/nemotron-3.5-lightning-30b-a3b:<tag>`; look the tag up on NGC, it was not verified.
- The first run downloads the weights, which the Brev guide says can take several minutes; the cache directory makes later starts fast. If Docker gives permission errors, prefix with `sudo`.
- Endpoints: `/v1/chat/completions`, `/v1/completions`, `/v1/models`, `/v1/health/ready`, `/v1/metrics`.
- Licence: Developer Program members get NIM "for prototyping, research, development and testing purposes only"; production "requires an NVIDIA AI Enterprise license".
- Known issue quoted in the forum benchmark: NIM 2.0.12 release notes say NVFP4 profiles can return incorrect output on stop-string and math-conformance checks and recommend BF16 or FP8 where correctness matters.

### 4.4 Tool calling and reasoning control (all backends are OpenAI-compatible)

- vLLM flags: `--enable-auto-tool-choice --tool-call-parser qwen3_coder` for Nemotron 3 Nano, Nano 4B, 3.5 Lightning and Bolt 74B; `gemma4` for Bolt E4B; the `nemotron_json` plugin for Nano 9B v2.
- Recommended sampling for tool calling: temperature 0.6, top_p 0.95. For reasoning: temperature 1.0, top_p 1.0 (Nano) or 0.95 (Lightning).
- Reasoning is ON by default. Turn it off per request with `"chat_template_kwargs": {"enable_thinking": false}` (via `extra_body` in the OpenAI client). `/no_think` works only on Nano 9B v2, not on Nemotron 3. With reasoning on, give a large `max_tokens` (the card suggests about 10,000) because reasoning and answer share the budget.
- Cost of turning reasoning off, one measurement on Nemotron 3 Nano: GSM8K 5.5 points lower, MMLU 12.3 points lower. Inference: keep reasoning on for the analyst and Index Scout agents, off for templated Harvest Story cards.
- build.nvidia.com lists Nemotron 3.5 Lightning as "Function Calling: Supported", "Reasoning: Supported", context 1,048,576 tokens.
- Small-model caution: on NVIDIA's own table Bolt E4B scores BFCL-v3 67.31 and Tau2-Bench 52.32 (Q4_K_M), below Qwen3.5 4B (70.56 / 61.74). Tiny models will mis-call tools more often; validate tool arguments in code.

Illustrative client, assembled from the documented parameters (not copied from one source):

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ.get("NEMOTRON_API_KEY", "not-needed"),
)
MODEL = os.environ.get("NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

tools = [{
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": "Run a read-only SQL query against the field-level results table.",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]},
    },
}]

resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Which five counties have the widest silage review band?"}],
    tools=tools, tool_choice="auto",
    temperature=0.6, top_p=0.95, max_tokens=2048,
    extra_body={"chat_template_kwargs": {"enable_thinking": True}},
)
print(resp.choices[0].message.tool_calls)
```

Switching between hosted and self-hosted is then three environment variables, which is what lets the Keeboh notebook stay independent of Brev.

### 4.5 Expected throughput

| Setup | Result | Source |
|---|---|---|
| Nemotron 3 Nano 30B, NVFP4, NIM 2.0.12, one RTX 5090 (32 GB) | 305 tok/s single stream (median); 305 / 315 / 308 tok/s at about 1k / 14k / 120k context; 128 concurrent chat requests (200 in / 200 out) inside the MLPerf target (p99 TTFT <= 2 s, p99 TPOT <= 100 ms); RAG-shaped load (3,500 in / 500 out) holds 8 concurrent and total throughput "tops out just above 2,100 tok/s"; upstream vLLM 0.27.1 within 3% of NIM | NVIDIA Developer Forum post, 2026-10-02 (one user, one setup, synthetic load) |
| Nemotron Nano 9B v2, BF16, NIM 1.12.2, same card | 73 tok/s single stream; 72 / 45 / 52 tok/s at 1k / 14k / 120k context; crashed with a Mamba-cache IndexError at 16+ concurrent requests | same post |
| Nemotron 3 Nano 30B, BF16, vLLM, 1x B200 | output 610.84 +/- 45.38 tok/s, total 918.01 +/- 68.20 tok/s; mean TTFT 351 ms; mean time per output token 6.37 ms (10 ShareGPT prompts) | Lambda docs |
| Nemotron 3.5 Lightning, 1x H100, interactive profile | design target "40+ TPS/user" at concurrency <= 128 | HF model card |

Inference: an L40S is slower than an RTX 5090 or H100, so plan on roughly 100-200 tok/s single-stream for a 30B-A3B model and a few hundred to a thousand tok/s aggregate under batching. A 150-token Harvest Story card for 5,000 fields is 750k output tokens, which is minutes to tens of minutes self-hosted, against about 2 hours at 40 requests/min hosted. The first minute after READY can run at about half speed (warm-up, per the forum post).

### 4.6 Hosted alternatives

| | build.nvidia.com (NVIDIA API catalogue) | OpenRouter |
|---|---|---|
| Base URL | `https://integrate.api.nvidia.com/v1` | `https://openrouter.ai/api/v1` |
| Nemotron ids | Free endpoints on a probe dated 2026-11-12: `nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-ultra-550b-a55b`, `nvidia/nemotron-3.5-super-vl-120b-a12b`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, `nvidia/nemotron-3.5-bolt-e4b` | Free list verified 2026-10-28: `nvidia/nemotron-3.5-lightning:free` (1M ctx), `nvidia/nemotron-3-ultra-550b-a55b:free` (1M), `nvidia/nemotron-3.5-super-vl:free` (1M), `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` (256K). Nemotron 3 Super is paid only. |
| Limits | Not published officially. Users report "1,000 credits, 40 RPM" (forum post 2026-11-07, plus a string of threads asking for 40 -> 200 RPM); a third-party page states 40 requests/min and 10,000 requests/day. Catalogue churns: ids added and dropped monthly. | Official: `:free` variants 20 requests/min; 50 requests/day if under 10 credits ever purchased, 1,000/day at 10 or more. Check with `GET https://openrouter.ai/api/v1/key` (`free_model_daily_requests`). |
| Terms | "for prototyping, research, development and testing purposes only"; vendor notes inputs and outputs are recorded | Provider-dependent |
| Failure modes | New keys that list models but 404 on chat (forum reports); models listed as free but 404 "not found for account" | 429s from provider capacity as well as from quota |

Paid OpenRouter prices as reported by one third-party guide dated 2026-11-12 (not verified at source): Lightning 0.07 / 0.20 dollars per million tokens in / out; Nano 30B 0.06 / 0.24; Ultra 0.60 / 2.40.

### 4.7 LoRA fine-tuning within a few hours

- Unsloth: "Unsloth now supports fine-tuning of all Nemotron models". Nemotron 3 Nano 4B "fits on a free Colab GPU". Nemotron 3 Nano 30B 16-bit LoRA needs "around 60GB VRAM" (an A100 80 GB notebook is provided); the MoE router is left frozen by default; to keep reasoning ability use "at least 75% reasoning and 25% non-reasoning" examples. Training time is not stated.
- NIM serves LoRA adapters for Nemotron 3 Nano (BF16 at all TP sizes, NVFP4 at TP1).
- NVIDIA's Lightning cookbook has a `lora-text2sql` recipe (NeMo Megatron-Bridge) and DGX Station LoRA recipes; no hour or GPU figures on the page opened.
- Brev's own troubleshooting page for Unsloth: reinstall CUDA PyTorch with `pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio`, then `pip install -U unsloth unsloth-zoo`; or use `nvcr.io/nvidia/pytorch:24.09-py3`.
- Inference: a LoRA on Nano 4B over a few hundred examples is feasible in under an hour on an A10G or L4, and a 30B LoRA is feasible on a rented A100 80 GB in a 2-3 h burst (about 2-7 dollars at the 1.00-2.21 dollars/h estimates above). It is still a poor use of tonight: we have no labelled text dataset, the judges asked for interpretable over clever, and prompt plus tools on a stock model already demonstrates the agent pattern. Skip unless everything else is finished.

---

## 5. Data and tooling on the instance

### 5.1 Python environment and RAPIDS

Facts:
- RAPIDS stable is 26.10 (`cuml-cu12` 26.10.0 uploaded 2026-10-08; `cudf-cu13` 26.10.2 uploaded 2026-10-22); both require Python >= 3.11 and ship as wheels directly on PyPI (`libcuml-cu12` wheel about 99 MB).
- Drivers: CUDA 12 builds need driver 525.60.13 or newer; CUDA 13 builds need 580.65.06 or newer. GPU compute capability 7.0+ (Volta or newer). glibc 2.28+.
- Brev VM mode: "Python 3.10+".

```bash
cd /home/ubuntu/workspace
nvidia-smi                                    # read the driver version first
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 --seed
source .venv/bin/activate

# driver < 580: CUDA 12 stack
uv pip install "cudf-cu12==26.10.*" "cuml-cu12==26.10.*" xgboost-cu12
# driver >= 580.65.06: CUDA 13 stack
# uv pip install "cudf-cu13==26.10.*" "cuml-cu13==26.10.*" xgboost
```

The pip lines are assembled from the PyPI metadata (package names and pins) and the XGBoost install page; the RAPIDS release selector that prints the canonical command did not render through the fetch tool. `cuml-cu13` is assumed to exist by analogy with `cudf-cu13`.

Zero-code-change acceleration:

```python
%load_ext cudf.pandas      # before importing pandas; restart the kernel if pandas is already loaded
%load_ext cuml.accel       # before importing scikit-learn, umap or hdbscan
import pandas as pd
```

```bash
python -m cudf.pandas script.py
python -m cuml.accel script.py
CUML_ACCEL_ENABLED=1 python script.py
python -m cudf.pandas --profile script.py      # shows what fell back to CPU
```

Programmatic: `import cudf.pandas; cudf.pandas.install()` and `import cuml; cuml.accel.install()`, both before the libraries they accelerate. cuml.accel "transparently falls back to the original CPU implementation" when something is unsupported; if cuML is not installed correctly the environment variable is silently ignored.

### 5.2 GPU XGBoost

```python
import xgboost
params = {"device": "cuda", "tree_method": "hist"}
Xy = xgboost.QuantileDMatrix(X, y)
booster = xgboost.train(params, Xy)

# sklearn API
# XGBClassifier(tree_method="hist", device="cuda")

# GPU SHAP for the explanation cards
booster.set_param({"device": "cuda:0"})
shap_values = booster.predict(dtrain, pred_contribs=True)
```

The XGBoost GPU page states "CUDA >= 12.9 is required"; the install page says the default Linux wheel is built with CUDA Toolkit 13.x and that `pip install xgboost-cu12` is the "driver-compatibility option" for drivers that support CUDA 12 but not 13. Inference: on a small labelled set CPU XGBoost trains in seconds, so the Keeboh notebook should choose `device = "cuda"` only if a GPU is present and otherwise fall back to CPU without changing results materially.

### 5.3 Geospatial stack

```bash
uv pip install rasterio geopandas pyogrio shapely pyproj rioxarray xarray dask \
               earthengine-api pystac-client odc-stac planetary-computer
```

- rasterio: "Binary distributions (wheels) containing libgdal and its own dependencies are available from the Python Package Index"; the wheels "omit many of GDAL's optional format drivers"; Rasterio 1.4.4+ needs Python 3.10+ and GDAL 3.5+. Inference: GeoTIFF / COG reading over HTTPS, which is what we need, works from the wheel; exotic formats need conda-forge.
- odc-stac: `pip install odc-stac` (or `conda install -c conda-forge odc-stac`); pattern `catalog = pystac_client.Client.open(...)`, `query = catalog.search(...)`, `xx = odc.stac.load(query.items(), bands=[...], resolution=...)`.
- The other packages in the pip line are standard PyPI packages and were not individually re-verified today.
- Earth Engine on a headless box:

```bash
earthengine authenticate --auth_mode=notebook     # open the link on a laptop, paste the code back
```

```python
import ee
ee.Authenticate(auth_mode='notebook')
ee.Initialize(project='my-project')               # a Cloud project with the Earth Engine API enabled is required
```

Credentials land in `~/.config/earthengine/credentials`. Notebook mode needs Owner, Editor or OAuth Config Editor on the authentication project. Inference: copying that credentials file from a laptop to the instance with `brev copy` is the fastest route; never commit it.

### 5.4 Long jobs

```bash
brev open my-instance tmux                 # tmux is installed automatically on the instance
tmux new -s train                          # detach: Ctrl-b d ; reattach: tmux attach -t train
nohup python train.py > logs/train_$(date +%H%M).log 2>&1 &
brev exec my-instance "nohup python train.py > /dev/null 2>&1 &"     # documented pattern
```

Brev's Jupyter guide also says to run Jupyter inside tmux so it survives disconnects. Setup-script output is in `/var/log/brev-workspace.log` on the host (`brev shell my-instance --host`).

### 5.5 GitHub from the instance

Deploy key (no extra software; one repo; read-only unless "Allow write access" is ticked; no expiry; not passphrase-protected):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/kernel_deploy -N "" -C "kernel-brev"     # standard command, not from the page opened
cat ~/.ssh/kernel_deploy.pub
# GitHub: repo -> Settings -> Deploy keys -> Add deploy key -> paste -> tick "Allow write access" -> Add key

cat >> ~/.ssh/config <<'EOF'
Host github.com-kernel
        Hostname github.com
        IdentityFile=/home/ubuntu/.ssh/kernel_deploy
EOF
git clone git@github.com-kernel:OWNER/REPO.git
```

Token route with the GitHub CLI:

```bash
gh auth login --with-token < mytoken.txt     # classic PAT needs at least repo, read:org, gist
export GH_TOKEN=<fine-grained PAT>           # preferred by the gh manual for fine-grained tokens
```

Inference: with several agents committing from one box, set `git config user.name` / `user.email` per clone so commits are attributable, and pull with rebase before every push.

### 5.6 Secrets

- Brev org Secrets (Settings -> Secrets): encrypted, versioned, up to 4 KiB, names immutable; bound to a Launchable Text parameter at deploy time; the parameter name becomes the environment variable name. They "provide values to Launchables at startup" and do not create persistent VM-wide variables.
- Brev's own warnings: do not print values or use `set -x`, because setup output is captured in logs; the workload receives plaintext; anyone with root access, Docker access or access to the receiving process can inspect runtime values; revoking a secret does not remove values already delivered.
- The NIM guide's `echo "export NGC_CLI_API_KEY=..." >> ~/.bashrc` stores the key in plaintext and is flagged there as suitable only for trusted single-user instances. Our instance is multi-user and the repo is public.
- Inference, the working rule: one `~/.kernel.env` file outside every clone, `chmod 600`, `source`d by tmux sessions; `.env*` in `.gitignore`; no keys in notebooks or logs; rotate every key after the event. An NGC key or other workload key is not a Brev credential, and a Brev API key should not be on the instance at all.

---

## 6. Reliability gotchas and the fallback plan

| Gotcha | Evidence | Mitigation |
|---|---|---|
| Stopped instance will not restart | GPU Instances doc: restart needs the same GPU type, provider and region; with no capacity the restart fails and the data is unreachable | Run continuously; push to Git before any stop; treat the disk as disposable |
| Instance stuck in "Waiting" | Troubleshooting doc: request succeeds but never reaches Running; `rpc error: code = Internal desc = context deadline exceeded`; no instance_id or public_ip | Check Activity Logs; delete, wait 30 s, recreate; then try another name or region (doc example: `aws-us-east-1` -> `aws-us-west-2`); support: brev-support@nvidia.com |
| Type out of stock | A Launchable deploy page surfaced in search results carried the notice "This instance type is currently out of stock." (search-result text; the page itself is JavaScript-only) | Use a `--type a,b,c` fallback chain; have a 24 GB plan B |
| Credits run out | Console Reference: stoppable instances paused, others deleted, everything deleted if still empty after the follow-up warning | `--stoppable` only; keep a 10-dollar reserve; watch remaining hours |
| "Created" but not ready | CI/CD guide: `brev create` can report success when it stops waiting; RAPIDS docs: build reported finished before JupyterLab is up | `brev ls`, then `brev exec <name> "nvidia-smi"` before trusting it; raise `--timeout` |
| Silent restart of a stopped box | llms.txt: `brev shell`, `brev open`, `brev copy` can start stopped instances | Delete rather than stop when done; no write-capable Brev key for agents |
| IP changes after restart | Docs: "SSH refused after restart" | `brev refresh` |
| Tunnel URL asks for login | Console Reference | `brev port-forward` for APIs; `brev ports ... --public` (beta) for demos |
| Docker socket permission denied | Common Issues | `sudo chmod 666 /var/run/docker.sock` (grants all host users) or prefix `sudo` |
| GPU not visible to PyTorch | Troubleshooting doc (H100 + Unsloth): CPU-only torch or wrong environment; recommends driver 550+ | Reinstall from the cu124 index or use the NGC PyTorch container |
| CLI install fails on shared network | Docs: GitHub API rate limit | `export GITHUB_TOKEN=...` |
| Org dollars-per-hour cap | Console Reference | Stay on single small GPUs; email support only if blocked |
| Preemption | Not mentioned in the docs opened; the aggregator page says Brev has no spot pricing | Inference: on-demand instances are not documented as preemptible; the real risks are the rows above |

**Fallback ladder if Brev fails at 2 a.m.**
1. Models, metrics and rollups run on the Keeboh GPU (or CPU: the labelled set is small) from feature tables already committed to the repo.
2. Nemotron through build.nvidia.com (`integrate.api.nvidia.com/v1`, about 40 requests/min) with exponential backoff and an on-disk cache keyed by prompt hash.
3. Second provider: OpenRouter `nvidia/nemotron-3.5-lightning:free` at 20 requests/min; a one-time 10-dollar credit purchase lifts the daily cap from 50 to 1,000.
4. Every Nemotron output the demo shows is pre-generated and committed as JSONL, so the notebook and pitch replay from cache with no live endpoint.
5. Recreate rather than repair: `brev create ... -s @setup.sh` plus `git clone` rebuilds the box in minutes if the setup script is kept current.

---

## 7. Cost plan for about 18 hours inside 60 dollars

**Decision rule.** Average burn must stay at or under 2.50 dollars/h (60 / 24 h, leaving margin). Check `brev search --stoppable --min-total-vram 40 --sort price` and pick:

| Live price of a stoppable 48 GB single GPU | Choice | 20 h cost | Reserve | Nemotron served |
|---|---|---|---|---|
| <= 2.00 dollars/h | **L40S (or L40 / A6000 / RTX 6000 Ada 48 GB)** | <= 40 | >= 20 | Nemotron 3.5 Lightning (NIM W4A16 or Ollama) or Nemotron 3 Nano 30B (FP8 / GGUF) |
| 2.00-2.20 | Same instance, capped at 18 h of run time (billing is per instance-hour, so idling the model server saves nothing) | 36-40 | about 20 | same |
| > 2.20 or out of stock | **A10G or L4 24 GB** (third-party 0.44-0.75; docs sample 1.00) | 9-20 | 40+ | Nemotron 3 Nano 4B, Nano 9B v2 or Bolt E4B self-hosted; Lightning and Ultra through the hosted API |
| Any | A100 80 GB or H100 only as a burst of at most 2-3 h | 2-15 for the burst | | 30B BF16, or a LoRA run |

**Schedule (clock times Pacific; adjust to actual start).**

| When | Action | Cumulative spend at 1.50 dollars/h |
|---|---|---|
| Sat 12:30-13:00 | Redeem code into the team org; `brev search`; `brev create` with fallback chain and `--stoppable`; smoke test; add teammates' keys; clone repo; run `setup.sh`; start tmux sessions | 0.75 |
| Sat 13:00-14:00 | Start the Nemotron server; verify a tool call; commit `NEMOTRON_BASE_URL` instructions; begin feature extraction | 2.25 |
| Sat 14:00 - Sun 02:00 | Continuous: autoresearch loop (time-boxed `train.py` runs), Index Scout, bulk Harvest Story generation, rollups. Push artifacts hourly | 20.25 |
| Sun 02:00-05:00 | Freeze. Export features (parquet), model files, calibration tables, Nemotron JSONL to the repo. Rehearse the Keeboh notebook end to end against cached artifacts | 24.75 |
| Sun 05:00-09:00 | Keep the box only if the pitch shows the live endpoint; otherwise delete after the final push | 30.75 |
| After the pitch | `brev delete kernel-gpu`; confirm `brev ls` is empty | |

At 2.00 dollars/h the same schedule costs about 41 dollars. Check the console balance at 18:00, 23:00 and 04:00.

**What stays on Keeboh (the judged notebook must live there).**
- The whole judged narrative: data loading from committed feature tables, the depth-2 rule, GPU XGBoost with isotonic calibration and the conformal review band, precision / recall / false-positive rate / response time on the evaluation set, county and state rollups against NASS totals, figures.
- A handful of live Nemotron calls through the hosted API, with cached outputs as the fallback path.
- Nothing that needs Brev to be alive. Inference: Keeboh's GPU type, outbound network rules and package set are unknown to this research; confirm early that it can reach `integrate.api.nvidia.com` and install `xgboost`.

**What goes on Brev.**
- The rate-limit-free Nemotron endpoint for agent loops and bulk generation.
- The autoresearch loop's repeated training runs and any RAPIDS-scale tabular work.
- Network-bound satellite extraction if laptops are the bottleneck (Inference: this is CPU and I/O work; a `brev search cpu` box is cheaper if the GPU box is saturated).
- The reproducibility artefact: a Launchable built from the public repo with a "Launch on Brev" badge.

---

## 8. Short runbook (copy-paste order)

Type names in angle brackets come from your own `brev search` output.

```bash
# --- laptop, once per teammate ---
brew install brevdev/homebrew-brev/brev && brev --version
brev login
brev org ls && brev org set <team-org>
# owner only: console -> Billing -> Credits -> "Redeem a credit code"; console -> Team -> Generate Invite Link (7-day expiry)

# --- owner: pick and create ---
brev search --stoppable --min-total-vram 40 --sort price
brev search --gpu-name A10G --sort price
brev create kernel-gpu --type <L40S_TYPE>,<48GB_FALLBACK>,<A10G_TYPE> --dry-run
brev create kernel-gpu --type <L40S_TYPE>,<48GB_FALLBACK>,<A10G_TYPE> --timeout 600
brev ls
brev exec kernel-gpu "nvidia-smi"

# --- owner: let teammates in (Inference: standard SSH) ---
brev copy ./team_keys.pub kernel-gpu:/home/ubuntu/
brev exec kernel-gpu "cat /home/ubuntu/team_keys.pub >> /home/ubuntu/.ssh/authorized_keys"
grep -A4 kernel-gpu ~/.brev/ssh_config        # read the IP and share it

# --- everyone: connect ---
brev refresh && brev shell kernel-gpu         # owner
ssh ubuntu@<instance-ip>                      # teammates
brev open kernel-gpu cursor                   # or VS Code: brev open kernel-gpu

# --- instance: environment ---
cd /home/ubuntu/workspace && tmux new -s main
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 --seed && source .venv/bin/activate
uv pip install "cudf-cu12==26.10.*" "cuml-cu12==26.10.*" xgboost-cu12
uv pip install rasterio geopandas pyogrio shapely pyproj rioxarray xarray dask earthengine-api pystac-client odc-stac planetary-computer openai
git clone git@github.com-kernel:OWNER/REPO.git   # after the deploy-key steps in 5.5

# --- instance: Nemotron (pick one) ---
ollama run nemotron-3.5-lightning                               # 48 GB card; endpoint http://localhost:11434/v1/
# or NIM / vLLM as in section 4.3; endpoint http://localhost:8000/v1

# --- laptop: reach the endpoint and Jupyter privately ---
brev port-forward kernel-gpu --port 8000:8000
brev port-forward kernel-gpu --port 8888:8888

# --- optional public demo port (beta; needs flex ports) ---
brev ports open kernel-gpu 8501 --protocol http --public
brev ports ls kernel-gpu

# --- end of event ---
brev exec kernel-gpu "cd /home/ubuntu/workspace/REPO && git status --short"
brev delete kernel-gpu && brev ls
```

Minimal `setup.sh` for `brev create -s @setup.sh` or a VM-mode Launchable (Inference: assembled from the commands above; contains no secrets and no `set -x`):

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/workspace
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install "cudf-cu12==26.10.*" "cuml-cu12==26.10.*" xgboost-cu12 \
  rasterio geopandas pyogrio shapely pyproj rioxarray xarray dask \
  earthengine-api pystac-client odc-stac planetary-computer openai jupyterlab
```

---

## 9. What this means for Kernel

1. **Spend the credit on the Nemotron story, not on the classifier.** The classifier trains in seconds on a small labelled set; what a GPU box buys is an unthrottled, self-hosted Nemotron endpoint for the Index Scout, the SQL-and-map analyst and bulk Harvest Story cards. "Self-hosted Nemotron NIM on NVIDIA Brev, called by planning agents with tools" is the sentence the Nemotron award criteria are asking for.
2. **Design every Nemotron call behind three environment variables** (`NEMOTRON_BASE_URL`, `NEMOTRON_MODEL`, `NEMOTRON_API_KEY`) and cache every response. This makes the Keeboh notebook independent of Brev and makes "Response Time" a number we can report for both hosted and self-hosted paths.
3. **Update the plan's model names.** The agents should target Nemotron 3.5 Lightning (hosted id `nvidia/nemotron-3.5-lightning-30b-a3b`); the 2025 workshop code that points at `nemotron-nano-9b-v2:free` will need its model id changed.
4. **For the USDA audience, the deployment note is a feature.** The hosted trial endpoint is for prototyping only and records inputs and outputs; an open-weight Nemotron in a NIM container can run inside an agency boundary. That is an honest "how it could be developed further" line. Production NIM use needs an NVIDIA AI Enterprise licence, which should be said plainly.
5. **Reproducibility deliverable that costs ten minutes:** a Launchable built from the public repo plus a "Launch on Brev" README badge. It answers USDA's "reproducible workflow" request and the Feasibility criterion.
6. **Nothing here contradicts the modelling plan (v2);** it constrains operations: keep one box, keep it running, keep artefacts in Git, keep the judged path on Keeboh.
7. **No new data source or harvest signal comes from this topic.**

---

## 10. Open items to resolve in the first 15 minutes

1. Real prices and stock: `brev search --stoppable --min-total-vram 40 --sort price`.
2. Whether the 60-dollar code is per team or per person, whether several codes stack in one org, and the exact redemption UI (`brev redeem --help`).
3. Whether teammates can reach the owner's instance with keys in `authorized_keys` on the chosen provider.
4. Whether `brev ports open --public` works on the chosen type (needs FEATURES code P).
5. Keeboh: GPU model, outbound access to `integrate.api.nvidia.com` and to a Brev public port, and whether the hackathon-provided Nemotron access has a higher rate limit than the public 40 requests/min.

---

## 11. Annotated bibliography (all opened 2026-11-14 unless noted)

Brev, official
- https://brev.nvidia.com/llms.txt - agent guidance: inspect first, creation is billable, get approval, shell/open/copy can auto-start, command groups including `invite` and `redeem`.
- https://docs.nvidia.com/brev/concepts/gpu-instances - lifecycle, billing rules, restart-capacity warning, persistence table, out-of-credit behaviour.
- https://docs.nvidia.com/brev/reference/gpu-types - GPU catalogue with VRAM; no prices.
- https://docs.nvidia.com/brev/concepts/launchables - full Launchable option set, view access, parameters, badge.
- https://docs.nvidia.com/brev/concepts/environments - VM / container / compose modes, "Python 3.10+", workspace path.
- https://docs.nvidia.com/brev/concepts/brev-connect and https://docs.nvidia.com/brev/cli/brev-connect - Brev Connect is for owned hardware; grant-ssh and register syntax; `brev ports ls/close` beta.
- https://docs.nvidia.com/brev/getting-started/quickstart - install, login, `brev create my-instance --gpu "nebius.l40sx1.pcie"`.
- https://docs.nvidia.com/brev/cli , /cli/cli-overview.md , /cli/getting-started , /cli/instance-creation , /cli/instance-management , /cli/connectivity , /cli/search-discovery , /cli/advanced-commands - command syntax, flags, sample search output, smart defaults.
- https://docs.nvidia.com/brev/guides/console-reference - billing, credits ("Redeem a credit code"), auto recharge, out-of-credit handling, team invite link (7 days), tunnels need browser auth, resource limits.
- https://docs.nvidia.com/brev/guides/api-keys - org-scoped keys, Read vs Read & Write, 30-day default, `BREV_API_KEY`.
- https://docs.nvidia.com/brev/guides/secrets - secret model, roles, warnings.
- https://docs.nvidia.com/brev/guides/ci-cd - GitHub Actions pipeline; create can report success early; always-run delete.
- https://docs.nvidia.com/brev/guides/inference-deployment/deploying-nims - NIM on Brev step by step; L40S 48 GB or A100 80 GB recommended; port-forward vs tunnel.
- https://docs.nvidia.com/brev/guides/development-tools/jupyter-notebooks , /vscode-setup , /file-transfer-scp , /custom-containers - Jupyter, IDE, copy and Docker usage.
- https://docs.nvidia.com/brev/troubleshooting , /troubleshooting/common-issues , /troubleshooting/instances-gpus/instance-stuck-in-waiting-state , /troubleshooting/instances-gpus/gpu-detection-pytorch - failure modes and fixes.
- https://github.com/brevdev/brev-cli (README) and https://raw.githubusercontent.com/brevdev/brev-cli/main/.agents/skills/brev-cli/SKILL.md - install variants, `brev agent-skill`, `brev ports open ... --public`, `brev org set`.
- https://pkg.go.dev/github.com/brevdev/brev-cli/pkg/cmd - command packages incl. `redeem`, `invite`, `ports`, `grantssh`; module v0.6.337 published 2026-10-15.
- https://github.com/brevdev/launchables - README table of notebook Launchables with minimum GPUs.
- https://github.com/brevdev/workshop-build-an-agent - 7-module workshop, Launchable id.
- https://rapids-deployment.readthedocs.io/en/latest/cloud/nvidia/brev/ - RAPIDS on Brev, Compose file, clone path, tunnel URL shape.

Prices, third party
- https://computecomparison.com/provider/brev-dev - per-GPU estimates for Brev.
- https://dev.classmethod.jp/en/articles/nvidia-brev-introduction/ (2026-01-25) - price ranges.
- https://miamimike.ai/nvidia-brev/ (2026-08-31) - prepaid credit model, cost risks.
- https://gpuperhour.com/ - market context, Brev not listed.

Nemotron
- https://huggingface.co/api/models?author=nvidia&search=Nemotron&sort=lastModified&direction=-1&limit=100 - authoritative list of published checkpoints.
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 and .../-FP8 - architecture, vLLM commands, tool parser, reasoning control.
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 - 4B model, A10G support, vLLM command.
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 - hardware paths (W4A16 on Hopper/Ampere), vLLM recipes, Ollama context tiers, llama.cpp command.
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB and .../NVIDIA-Nemotron-3.5-Bolt-E4B-4GB - compressed models, benchmarks, run commands.
- https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2 - A10G test hardware, tool-call plugin, /think controls.
- https://huggingface.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF and https://unsloth.ai/docs/models/nemotron-3 - GGUF sizes, memory guidance, LoRA requirements.
- https://recipes.vllm.ai/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 - vLLM >= 0.17.0, flags, "1x H100/H200 or comparable".
- https://docs.lambda.com/education/large-language-models/deploying-nemotron-3-nano/ - 58 GB weights, 120 GB idle VRAM, 610.84 tok/s on a B200.
- https://docs.nvidia.com/nim/large-language-models/latest/reference/support-matrix.html - NIM profiles, minimum VRAM for Lightning, verified GPUs.
- https://docs.nvidia.com/nim/large-language-models/latest/get-started/quickstart.html - NIM docker run, health and chat endpoints (tag 2.1.6).
- https://forums.developer.nvidia.com/t/nemotron-3-nano-on-one-rtx-5090-with-nim-300-tok-s-flat-to-120k-context-128-concurrent-requests/384859 (2026-10-02) - throughput, memory, run command, known issue.
- https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b - base URL, function calling supported, context length.
- https://docs.api.nvidia.com/nim/docs/product - Developer Program terms: prototyping only; production needs AI Enterprise.
- https://forums.developer.nvidia.com/t/credit-rate-limit-increase-request-build-nvidia-com-free-tier-1-000-5-000-credits-40-200-rpm/388265 (2026-11-07) - user-observed "1,000 credits, 40 RPM".
- https://mvalentsev.github.io/awesome-free-ai-coding/providers/nvidia-nim/ (probe 2026-11-12) - free endpoint ids, 40/min and 10,000/day claim, caveats.
- https://openrouter.ai/docs/api-reference/limits - official free-variant limits.
- https://openrouter.ai/nvidia - list of NVIDIA model slugs.
- https://www.teamday.ai/blog/best-free-ai-models-openrouter-2026 (verified 2026-10-28) - free Nemotron ids.
- https://www.secondtalent.com/resources/every-nemotron-ai-model-explained-compared/ (2026-11-12) - third-party line-up summary and OpenRouter prices; used only where it agreed with the Hugging Face listing.
- https://developer.nvidia.com/topics/ai/nemotron - official line-up, access routes, tutorials.
- https://developer.nvidia.com/blog/build-a-report-generator-ai-agent-with-nvidia-nemotron-on-openrouter (2025-09-15) - agent graph and code.
- https://github.com/NVIDIA-NeMo/Nemotron and .../usage-cookbook/Nemotron-3.5-Lightning - cookbooks.
- https://ollama.com/library/nemotron-3.5-lightning and https://docs.ollama.com/api/openai-compatibility - sizes, badges, OpenAI-compatible API.

Tooling
- https://docs.nvidia.com/datascience/install/ - RAPIDS system requirements.
- https://pypi.org/pypi/cuml-cu12/json , https://pypi.org/pypi/cudf-cu13/json , https://pypi.org/pypi/libcuml-cu12/json - versions, Python requirement, wheel hosting.
- https://docs.nvidia.com/cuml/latest/cuml-accel/ and /usage/ ; https://docs.nvidia.com/cudf/latest/cudf_pandas/usage/ - activation methods.
- https://xgboost.readthedocs.io/en/stable/gpu/index.html and /install.html - GPU parameters, CUDA variants.
- https://rasterio.readthedocs.io/en/stable/installation.html - wheels include libgdal.
- https://odc-stac.readthedocs.io/en/latest/intro.html - install and load pattern.
- https://developers.google.com/earth-engine/guides/auth - headless authentication.
- https://cli.github.com/manual/gh_auth_login and https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys - token and deploy-key routes.

---

## 12. Not opened or not verifiable (confidence low where used)

- https://hack-the-harvest.devpost.com/ and /resources - HTTP 403. The statements that the Nemotron prize is 600 dollars of Brev credits and that Nemotron is optional come from a search-result summary only.
- https://brev.nvidia.com/ and the Launchable deploy pages - JavaScript only; no prices or default compute could be read.
- https://docs.nvidia.com/nim/large-language-models/latest/function-calling.html - returned empty; NIM tool-calling support for Nemotron 3 Nano ("Yes", parallel "Yes") is from a search summary of the 1.15 supported-models page.
- https://openrouter.ai/nvidia/nemotron-3.5-lightning-30b-a3b:free (404) and https://openrouter.ai/api/v1/models (returned unrelated content) - per-model OpenRouter throughput not obtained.
- https://www.digitalocean.com/community/tutorials/nemotron-3-models-run-gpu-droplet - body did not load.
- https://guide.hackutd.co/...nvidia...pdf - 404.
- Searches for Brev idle auto-stop and for a public "Share a Service" flow were not run (search budget exhausted).
- Keeboh: no documentation found or searched.
