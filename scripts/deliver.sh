#!/usr/bin/env bash
# scripts/deliver.sh TASK_ID -- rebase on origin/main, run the guard, push HEAD to main, retry up to 5 times.
set -eu
: "${AGENT_ID:?export AGENT_ID first}"
task="${1:?usage: deliver.sh TASK_ID}"
cd "$(git rev-parse --show-toplevel)"
log="$(git rev-parse --git-dir)/kernel-metrics.tsv"      # local, never committed
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
rejected=0
for attempt in 1 2 3 4 5; do
  git fetch origin --quiet
  if ! git rebase origin/main --quiet; then
    git rebase --abort
    printf '%s\t%s\t%s\trebase_conflict\t%s\n' "$(stamp)" "$AGENT_ID" "$task" "$rejected" >> "$log"
    echo "deliver: rebase conflict. Rerun 'git rebase origin/main' and resolve it if the file is yours; otherwise write a handoff note." >&2
    exit 1
  fi
  bash scripts/guard.sh origin/main HEAD
  if git push --quiet origin HEAD:main; then
    printf '%s\t%s\t%s\tdelivered\t%s\n' "$(stamp)" "$AGENT_ID" "$task" "$rejected" >> "$log"
    git push --quiet origin --delete "task/$task" 2>/dev/null || true
    echo "delivered $task to main on attempt $attempt"
    exit 0
  fi
  rejected=$((rejected + 1))
done
printf '%s\t%s\t%s\tgave_up\t%s\n' "$(stamp)" "$AGENT_ID" "$task" "$rejected" >> "$log"
echo "deliver: 5 rejected pushes in a row" >&2
exit 1
