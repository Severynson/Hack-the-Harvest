#!/usr/bin/env bash
# Cheap read of everyone's state through git alone. Run at session start, before each task and before each push.
set -eu
cd "$(git rev-parse --show-toplevel)"
echo "UTC now: $(date -u +%Y-%m-%dT%H:%MZ)   agent: ${AGENT_ID:-UNSET}   branch: $(git rev-parse --abbrev-ref HEAD)"
old=$(git rev-parse -q --verify origin/main || true)
git fetch --all --prune --quiet
new=$(git rev-parse origin/main)
if [ -n "$old" ] && [ "$old" != "$new" ]; then
  echo "== new on main =="
  git log --format='%h %cr %an %s' "$old..$new" | head -15
  echo "== new rules (read before you continue) =="
  git diff "$old" "$new" -- CLAUDE.md AGENTS.md | grep -E '^[+-][^+-]' | head -30 || true
  echo "== board and changelog =="
  git diff --stat "$old" "$new" -- CHANGELOG.md DOCS/coord | tail -10
  bash scripts/guard.sh "$old" "$new" || echo "MAIN IS BROKEN: first agent to see this claims task/fix-main"
fi
echo "== remote branches, newest first =="
git for-each-ref --sort=-committerdate --count=12 \
  --format='%(committerdate:relative)%09%(refname:short)%09%(authorname)%09%(subject)' refs/remotes/origin
echo "== my unmerged commits =="
git log --oneline origin/main..HEAD | head -10
git status -sb | head -5
