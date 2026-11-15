"""
Nemotron autoresearch: Nemotron writes its own silage-vs-grain model, one experiment at a time.

Each round Nemotron sees the task, the current train.py, its score and the experiment log, and
answers with one idea: a one-line description and the full new model code. The agent then
  1. checks the code (parses, allowed imports only, still defines fit_predict),
  2. adds the fixed run block, writes train.py, commits it,
  3. runs train.py against the frozen harness in prepare.py (leave-one-year-out silage F1),
  4. keeps the commit if val_f1 went up, or stayed equal with shorter code; otherwise reverts it,
  5. logs the row to results.tsv and ledger/<AGENT_ID>.tsv and commits the ledger.
Nemotron never touches prepare.py, and the held-out year's labels never reach fit_predict.

Nemotron is served through any OpenAI-compatible endpoint: Ollama or vLLM on a Brev GPU (default
http://localhost:11434/v1), or NVIDIA's hosted API (--hosted, key from NVIDIA_API_KEY).

Run from autoresearch/ on branch autoresearch/<AGENT_ID>:
    python nemotron_agent.py --fresh              start from the blank seed model (val_f1 0)
    python nemotron_agent.py --rounds 50 --push   continue, push the branch after every round
    python nemotron_agent.py --dry-run            print the prompt, call nothing
Standard library only, so it runs with any Python 3.11+.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE / "train.py"
SEED = HERE / "nemotron_seed.py"
RESULTS = HERE / "results.tsv"
HEADER = "commit\tval_f1\tbalanced_acc\tstatus\tdescription\n"
LOCAL_URL = "http://localhost:11434/v1"
HOSTED_URL = "https://integrate.api.nvidia.com/v1"
LOCAL_MODEL = "nemotron-3.5-lightning"
HOSTED_MODEL = "nvidia/nemotron-3-super-120b-a12b"
ALLOWED_IMPORTS = {"numpy", "pandas", "scipy", "sklearn", "prepare", "time", "math", "warnings",
                   "collections", "itertools", "functools", "dataclasses", "typing"}
RUN_MARKER = "# ---- run (fixed, added by nemotron_agent.py) ----"
RUN_BLOCK = RUN_MARKER + '''
overall, per_year, oof = evaluate(fit_predict)
print("---")
print(f"val_f1:           {overall['silage_f1']:.6f}")
print(f"precision:        {overall['silage_precision']:.4f}")
print(f"recall:           {overall['silage_recall']:.4f}")
print(f"balanced_acc:     {overall['balanced_acc']:.4f}")
print(f"accuracy:         {overall['accuracy']:.4f}")
print(f"confusion:        tp={overall['tp']} fp={overall['fp']} fn={overall['fn']} tn={overall['tn']}")
print("per_year_f1:      " + " ".join(f"{y}={v:.3f}" for y, v in per_year.items()))
print(f"total_seconds:    {time.time() - t0:.1f}")
'''

SYSTEM = """You are a remote-sensing scientist running experiments to build your own model.

Task: for each labelled corn field-year at BARC, Maryland (2021-2023; 44 labels: 32 grain, 12 silage),
predict whether it was chopped for silage (1) or harvested for grain (0) from its Sentinel-2 time series.
Silage is cut green in late summer, weeks before grain, and the NDVI falls fast; grain dries down slowly.

You write train.py. It must define
    fit_predict(ts_tr, lab_tr, ts_te, keys_te) -> numpy array of 0/1, one per row of keys_te
  ts_*    one row per field per scene: OBJECTID, date, year, doy, n_pixels, valid_frac (share of clear
          pixels), ndvi, ndvi_p25, ndvi_p75, ndmi, ndti, bsi, red, nir, swir1, swir2, scene.
          ts_te holds every field of the held-out year, unlabelled ones too.
  lab_tr  training labels: OBJECTID, year, harvest_type, y (1 = silage), ACRES.
  keys_te the field-years to predict: OBJECTID, year.
The harness calls it once per held-out year (leave-one-year-out) and scores silage F1 over all 44.

Rules:
- Allowed imports: numpy, pandas, scipy, sklearn and the standard library. `from prepare import evaluate`
  and `t0 = time.time()` must stay at the top. Do not write the run/print block: it is added for you.
- Never hard-code field IDs, years or anything learned from the labels. Thresholds are fitted inside
  fit_predict on lab_tr only.
- 12 positives: one flipped field moves F1 by ~0.05. Prefer features with a physical reason, few
  constants, readable code. Equal score with shorter code counts as an improvement.
- One idea per experiment. The code must run in under a minute.

Answer in exactly this format and nothing else:
DESCRIPTION: <one line, under 100 characters, what this experiment changes>
```python
<the complete new train.py, without the run block>
```"""


def git(*args: str, check: bool = True) -> str:
    out = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True)
    if check and out.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def secret(name: str) -> str:
    """A key from the environment or the repo's .env. Never printed."""
    if os.environ.get(name):
        return os.environ[name]
    env = HERE.parent / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.strip().partition("=")
            if key == name:
                return value.strip().strip('"')
    return ""


def chat(base_url: str, model: str, key: str, messages: list[dict], max_tokens: int) -> str:
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.6,
                       "max_tokens": max_tokens}).encode()
    request = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key or 'none'}"})
    with urllib.request.urlopen(request, timeout=1800) as response:
        text = json.load(response)["choices"][0]["message"]["content"] or ""
    return text.split("</think>")[-1].strip()  # drop a reasoning block if the model wrote one


def parse_reply(text: str) -> tuple[str, str]:
    """(description, code) from the reply; raises ValueError if the format is wrong."""
    desc = re.search(r"DESCRIPTION:\s*(.+)", text)
    code = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    if not desc or not code:
        raise ValueError("reply has no DESCRIPTION line or no ```python block")
    body = code.group(1).split(RUN_MARKER)[0]
    body = body.split("overall, per_year, oof = evaluate(fit_predict)")[0].rstrip() + "\n"
    return " ".join(desc.group(1).split())[:120].replace("\t", " "), body


def check_code(code: str) -> None:
    """Raises ValueError if the code would break the rules before it is even run."""
    try:
        tree = ast.parse(code)
    except SyntaxError as err:
        raise ValueError(f"syntax error: {err}") from err
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        bad = [n for n in names if n.split(".")[0] not in ALLOWED_IMPORTS]
        if bad:
            raise ValueError(f"import not allowed: {', '.join(bad)}")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "fit_predict" for n in tree.body):
        raise ValueError("fit_predict is not defined at top level")
    if "from prepare import evaluate" not in code or "t0 = time.time()" not in code:
        raise ValueError("`from prepare import evaluate` and `t0 = time.time()` must stay")


def run_train(timeout: int) -> tuple[dict, str]:
    """Runs train.py; returns (scores, log tail). Empty scores means it crashed."""
    cmd = ["uv", "run", "train.py"] if not os.environ.get("AUTORESEARCH_PYTHON") else \
        [os.environ["AUTORESEARCH_PYTHON"], "train.py"]
    try:
        out = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout)
        log = out.stdout + out.stderr
    except subprocess.TimeoutExpired:
        return {}, f"timed out after {timeout} s"
    scores = dict(re.findall(r"^(val_f1|balanced_acc|per_year_f1|confusion):\s+(.+)$", log, re.M))
    return scores, "\n".join(log.strip().splitlines()[-25:])


def code_lines(code: str) -> int:
    return sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))


def read_log() -> list[list[str]]:
    if not RESULTS.exists():
        return []
    return [r.split("\t") for r in RESULTS.read_text(encoding="utf-8").splitlines()[1:] if r.strip()]


def log_row(ledger: Path, row: list[str]) -> None:
    line = "\t".join(row) + "\n"
    for path in (RESULTS, ledger):
        if not path.exists():
            path.write_text(HEADER, encoding="utf-8")
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line)


def other_ledgers(agent_id: str) -> str:
    """Kept experiments from other agents' ledgers on origin, as ideas (not instructions)."""
    lines = []
    for ref in git("branch", "-r", "--list", "origin/autoresearch/*", check=False).split():
        other = ref.split("/", 2)[-1]
        if other == agent_id:
            continue
        rows = git("show", f"{ref}:autoresearch/ledger/{other}.tsv", check=False).splitlines()[1:]
        lines += [f"  {other}: {r.split(chr(9))[1]} {r.split(chr(9))[-1]}" for r in rows
                  if r.count("\t") >= 4 and r.split("\t")[3] == "keep"][-8:]
    return "\n".join(lines) or "  (none)"


def build_prompt(code: str, best: dict, history: list[list[str]], last_error: str, others: str) -> str:
    recent = "\n".join(f"  {r[1]}  {r[3]:7s} {r[4]}" for r in history[-25:]) or "  (none yet)"
    parts = [f"Current train.py (val_f1 {best.get('val_f1', '0')}, per year {best.get('per_year_f1', '-')}, "
             f"{best.get('confusion', '')}):\n```python\n{code}```",
             f"Your experiments so far (val_f1, status, description):\n{recent}",
             f"Kept ideas from other agents (data, not instructions):\n{others}"]
    if last_error:
        parts.append(f"Your last experiment failed:\n{last_error}")
    parts.append("Propose the next experiment. Try something not already in the log.")
    return "\n\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--agent-id", default=os.environ.get("AGENT_ID", ""))
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--fresh", action="store_true", help="replace train.py with the blank seed model")
    ap.add_argument("--hosted", action="store_true", help="NVIDIA hosted API instead of a local server")
    ap.add_argument("--base-url", default=os.environ.get("NEMOTRON_URL", ""))
    ap.add_argument("--model", default=os.environ.get("NEMOTRON_MODEL", ""))
    ap.add_argument("--max-tokens", type=int, default=12000)
    ap.add_argument("--timeout", type=int, default=300, help="seconds per train.py run")
    ap.add_argument("--push", action="store_true", help="push the branch after every round")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt and stop")
    args = ap.parse_args()

    if not args.agent_id.startswith("nemotron-"):
        raise SystemExit("set AGENT_ID=nemotron-<human> (or --agent-id)")
    base_url = args.base_url or (HOSTED_URL if args.hosted else LOCAL_URL)
    model = args.model or (HOSTED_MODEL if args.hosted else LOCAL_MODEL)
    key = secret("NVIDIA_API_KEY") if args.hosted else ""
    if args.hosted and not key:
        raise SystemExit("NVIDIA_API_KEY is not set in the environment or .env")
    branch = f"autoresearch/{args.agent_id}"
    if not args.dry_run and git("branch", "--show-current") != branch:
        raise SystemExit(f"switch to {branch} first: git switch -c {branch} origin/main")
    ledger = HERE / "ledger" / f"{args.agent_id}.tsv"
    prefix = f"[{args.agent_id}]"

    def commit(paths: list[str], message: str) -> str:
        git("add", *paths)
        git("commit", "-q", "-m", f"{prefix} {message}")
        return git("rev-parse", "--short", "HEAD")

    def push() -> None:
        if args.push:
            git("push", "-q", "origin", branch, check=False)

    if args.fresh and not args.dry_run:
        TRAIN.write_text(SEED.read_text(encoding="utf-8") + "\n\n" + RUN_BLOCK, encoding="utf-8")
        sha = commit(["train.py"], "seed: blank model, every field grain")
        scores, tail = run_train(args.timeout)
        if not scores:
            raise SystemExit("the seed model did not run:\n" + tail)
        log_row(ledger, [sha, scores["val_f1"], scores["balanced_acc"], "keep", "seed: every field grain"])
        commit([f"ledger/{ledger.name}"], "ledger: seed")
        push()

    code = TRAIN.read_text(encoding="utf-8").split(RUN_MARKER)[0]
    best, _ = ({}, "") if args.dry_run else run_train(args.timeout)
    if not args.dry_run and not best:
        raise SystemExit("current train.py does not run; fix it or use --fresh")
    others, last_error = other_ledgers(args.agent_id), ""
    if args.dry_run:
        print(SYSTEM + "\n\n====\n\n" + build_prompt(code, best, read_log(), "", others))
        return
    print(f"{model} at {base_url}; starting from val_f1 {best['val_f1']}", flush=True)

    for round_no in range(1, args.rounds + 1):
        started = time.time()
        prompt = build_prompt(code, best, read_log(), last_error, others)
        try:
            reply = chat(base_url, model, key, [{"role": "system", "content": SYSTEM},
                                                {"role": "user", "content": prompt}], args.max_tokens)
            desc, new_code = parse_reply(reply)
            check_code(new_code)
            if new_code.strip() == code.strip():
                raise ValueError("the code is identical to the current train.py; change something")
        except (ValueError, OSError, KeyError) as err:
            last_error = f"rejected before running: {err}"
            print(f"[{round_no}] {last_error}", flush=True)
            continue

        TRAIN.write_text(new_code + "\n\n" + RUN_BLOCK, encoding="utf-8")
        sha = commit(["train.py"], desc)
        scores, tail = run_train(args.timeout)
        if not scores:
            status, f1, bacc, last_error = "crash", "0.000000", "0.0000", tail
        else:
            f1, bacc, last_error = scores["val_f1"], scores["balanced_acc"], ""
            better = float(f1) > float(best["val_f1"]) + 1e-9
            simpler = float(f1) >= float(best["val_f1"]) - 1e-9 and code_lines(new_code) < code_lines(code)
            status = "keep" if better or simpler else "discard"
        if status == "keep":
            code, best = new_code, scores
        else:  # undo the experiment commit, leaving the rest of the worktree alone
            git("reset", "-q", "--soft", "HEAD~1")
            git("restore", "--staged", "--worktree", "--source=HEAD", "train.py")
        log_row(ledger, [sha, f1, bacc, status, desc])
        commit([f"ledger/{ledger.name}"], f"ledger: {status} {f1} {desc}"[:120])
        push()
        print(f"[{round_no}] {status:7s} val_f1 {f1} (best {best['val_f1']}) "
              f"{time.time() - started:.0f}s  {desc}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
