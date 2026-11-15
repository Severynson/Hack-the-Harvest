#!/usr/bin/env bash
# Run ON the Brev instance (brev shell hacakthon-gpu). Safe to re-run.
#   bash brev_setup.sh            -> app only (CPU models + reports), port 7860
#   bash brev_setup.sh --llm      -> also serve a Nemotron model on the GPU (port 8000) for the "Explain" button
set -euo pipefail

REPO_URL="https://github.com/Severynson/Hack-the-Harvest.git"
cd "$HOME"
[ -d Hack-the-Harvest ] || git clone "$REPO_URL"
cd Hack-the-Harvest
git pull --ff-only || true
[ -f kernel_app.py ] || { echo "kernel_app.py is not in the repo root. Copy it here (brev copy) or push it to GitHub, then re-run."; exit 1; }

command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
[ -d .venv ] || uv venv --python 3.12 .venv
uv pip install -q --python .venv/bin/python -r requirements.txt fastapi uvicorn

if [ "${1:-}" = "--llm" ]; then
  # Separate environment: vLLM brings its own torch/CUDA and must not share the data env.
  [ -d "$HOME/llm" ] || uv venv --python 3.12 "$HOME/llm"
  uv pip install -q --python "$HOME/llm/bin/python" vllm
  tmux kill-session -t llm 2>/dev/null || true
  tmux new-session -d -s llm "$HOME/llm/bin/vllm serve nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 --trust-remote-code --max-model-len 8192 --port 8000 2>&1 | tee ~/llm.log"
  echo "vLLM is loading in tmux session 'llm' (first start downloads the weights). Watch: tail -f ~/llm.log"
  export KERNEL_LLM_BASE_URL="http://localhost:8000/v1"
  export KERNEL_LLM_MODEL="nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16"
fi

tmux kill-session -t kernel 2>/dev/null || true
tmux new-session -d -s kernel "cd $HOME/Hack-the-Harvest && KERNEL_LLM_BASE_URL=${KERNEL_LLM_BASE_URL:-} KERNEL_LLM_MODEL=${KERNEL_LLM_MODEL:-} .venv/bin/python kernel_app.py 2>&1 | tee ~/kernel_app.log"
sleep 8
curl -fsS localhost:7860/api/meta >/dev/null && echo "Kernel app is up on port 7860 (logs: ~/kernel_app.log)" || { echo "App did not start; see ~/kernel_app.log"; exit 1; }
