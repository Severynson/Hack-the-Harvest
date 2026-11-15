#!/usr/bin/env bash
# Nemotron autoresearch on a Brev GPU: serve Nemotron with Ollama, build the data cache, run the loop.
#
# On the Brev instance (terminal in the Jupyter notebook, or `brev shell <instance>`):
#   git clone https://github.com/Severynson/Hack-the-Harvest.git && cd Hack-the-Harvest
#   export AGENT_ID=nemotron-<human>          # e.g. nemotron-daniel
#   bash scripts/brev_nemotron.sh             # ROUNDS=100 NEMOTRON_MODEL=... to override
# Pushing the branch needs git credentials on the instance (gh auth login, or a token remote).
# Resumable: rerunning continues the branch autoresearch/$AGENT_ID where it stopped.
set -euo pipefail
: "${AGENT_ID:?export AGENT_ID=nemotron-<human> first}"
MODEL="${NEMOTRON_MODEL:-nemotron-3.5-lightning}"   # 30B/3B-active; fits one 48 GB+ GPU at full context
ROUNDS="${ROUNDS:-100}"
cd "$(git rev-parse --show-toplevel)"

command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
if ! curl -sf localhost:11434/api/tags >/dev/null; then
  nohup ollama serve >/tmp/ollama.log 2>&1 &
  for _ in $(seq 30); do curl -sf localhost:11434/api/tags >/dev/null && break; sleep 1; done
fi
ollama pull "$MODEL"

command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
cd autoresearch
uv sync -q
uv run prepare.py                                    # cached after the first run (~10-20 min)

branch="autoresearch/$AGENT_ID"
git fetch -q origin
fresh=""
if [ "$(git branch --show-current)" != "$branch" ]; then
  if git show-ref -q "refs/remotes/origin/$branch"; then
    git switch "$branch" 2>/dev/null || git switch -c "$branch" --track "origin/$branch"
  elif git show-ref -q "refs/heads/$branch"; then
    git switch "$branch"
  else
    git switch -c "$branch" origin/main
    fresh="--fresh"
  fi
fi
NEMOTRON_MODEL="$MODEL" python3 nemotron_agent.py $fresh --rounds "$ROUNDS" --push 2>&1 | tee -a nemotron_run.log
