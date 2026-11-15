#!/usr/bin/env bash
# Rebuild the one-file board from your local repo and push it to a free Static Hugging Face Space.
# Usage (from the repo root):  bash board/deploy/publish_static.sh YOUR_HF_USERNAME [space-name]
set -euo pipefail
USER_NAME="${1:?give your Hugging Face username}"
SPACE="${2:-kernel-board}"
SPACE_DIR="$HOME/$SPACE-space"

git pull --ff-only || true
python board/export_static.py

if [ ! -d "$SPACE_DIR/.git" ]; then
  git clone "https://huggingface.co/spaces/$USER_NAME/$SPACE" "$SPACE_DIR"
fi
cp board/kernel_board_snapshot.html "$SPACE_DIR/index.html"
cd "$SPACE_DIR"
git add index.html
if git diff --cached --quiet; then echo "No changes to publish."; exit 0; fi
git commit -m "Board snapshot $(date -u +%Y-%m-%dT%H:%MZ)"
git push
echo "Live at https://$USER_NAME-$SPACE.static.hf.space (also https://huggingface.co/spaces/$USER_NAME/$SPACE)"
