#!/usr/bin/env bash
# Once per clone: turn on the guards and create this agent's own files.
set -eu
: "${AGENT_ID:?export AGENT_ID first, for example cc-daniel or cc-varun-brev1}"
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
git config pull.rebase true
git config fetch.prune true
mkdir -p DOCS/coord/status DOCS/coord/handoff DOCS/coord/handshake DOCS/coord/tasks autoresearch/ledger
status="DOCS/coord/status/$AGENT_ID.md"
[ -f "$status" ] || printf '# %s status ledger (append-only, single writer)\n' "$AGENT_ID" > "$status"
git fetch --all --prune --quiet
echo "bootstrap done for $AGENT_ID (hooks on, pull.rebase on). Next: bash scripts/handshake.sh"
