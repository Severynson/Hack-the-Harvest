#!/usr/bin/env bash
# Proves this agent can write to and read from the shared channel. Run on main, twice:
# once to say hello, once more after the other agents ran it, to acknowledge each of them.
set -eu
: "${AGENT_ID:?export AGENT_ID first}"
cd "$(git rev-parse --show-toplevel)"
dir=DOCS/coord/handshake; f="$dir/$AGENT_ID.md"; mkdir -p "$dir"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "run the handshake on main" >&2; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then echo "commit or stash your changes first" >&2; exit 1; fi
git fetch origin --quiet
git rebase origin/main --quiet
if [ ! -f "$f" ]; then
  printf 'hello %s utc=%s host=%s git=%s nonce=%s\n' "$AGENT_ID" "$(now)" "$(hostname -s)" "$(git --version | cut -d' ' -f3)" "$RANDOM$RANDOM" > "$f"
fi
for other in "$dir"/*.md; do
  id=$(basename "$other" .md)
  if [ "$id" = "$AGENT_ID" ] || [ "$id" = "ROLLCALL" ]; then continue; fi
  nonce=$(sed -n '1s/.*nonce=\([0-9]*\).*/\1/p' "$other")
  if ! grep -q "^ack $id nonce=$nonce " "$f"; then
    lag=$(( $(date -u +%s) - $(git log -1 --format=%ct -- "$other") ))
    printf 'ack %s nonce=%s seen=%s lag_s=%s\n' "$id" "$nonce" "$(now)" "$lag" >> "$f"
  fi
done
git add "$f"
git commit -q -m "[$AGENT_ID] handshake" ${COMMIT_TRAILER:+-m "$COMMIT_TRAILER"} || true
for attempt in 1 2 3 4 5; do
  if git push -q origin HEAD:main; then echo "handshake pushed on attempt $attempt"; exit 0; fi
  git fetch origin --quiet && git rebase origin/main --quiet
done
echo "handshake FAILED: 5 rejected pushes" >&2; exit 1
