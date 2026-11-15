#!/usr/bin/env bash
# Start the hosted board: model data from the team repo's main branch, board code from the board branch.
# Every BOARD_AUTOPULL minutes the server runs "start.sh sync" again, so new model results show up by themselves.
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/Severynson/Hack-the-Harvest.git}"
DATA_BRANCH="${DATA_BRANCH:-main}"
BOARD_BRANCH="${BOARD_BRANCH:-board}"
DIR="${DIR:-$HOME/hth}"
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

sync_repo() {
  cd "$DIR"
  git fetch --depth 1 origin "+refs/heads/$DATA_BRANCH:refs/remotes/origin/$DATA_BRANCH" \
    "+refs/heads/$BOARD_BRANCH:refs/remotes/origin/$BOARD_BRANCH"
  git reset --hard "origin/$DATA_BRANCH"
  git checkout "origin/$BOARD_BRANCH" -- board
}

if [ "${1:-}" = "sync" ]; then sync_repo; exit 0; fi

if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 --branch "$DATA_BRANCH" "$REPO_URL" "$DIR"
fi
sync_repo
export BOARD_PULL_CMD="bash '$SELF' sync" BOARD_BRANCH
export BOARD_PORT="${PORT:-${BOARD_PORT:-7860}}"
exec python board/app.py
