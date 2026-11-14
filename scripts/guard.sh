#!/usr/bin/env bash
# scripts/guard.sh BASE [HEAD] -- exit 1 if the range BASE..HEAD breaks a repository invariant.
# Used by .githooks/pre-push, scripts/sync.sh, scripts/deliver.sh and .github/workflows/guard.yml.
set -eu
BASE="${1:?usage: guard.sh BASE [HEAD]}"
HEAD_REV="${2:-HEAD}"
max_bytes="${GUARD_MAX_BYTES:-5000000}"
fail=0
err() { echo "ERROR guard: $*" >&2; fail=1; }
for rev in "$BASE" "$HEAD_REV"; do
  git cat-file -e "${rev}^{commit}" 2>/dev/null || { echo "ERROR guard: unknown commit $rev (run git fetch first)" >&2; exit 1; }
done

# 1. Append-only files: existing lines may never be deleted, changed or reordered.
while IFS=$'\t' read -r added deleted path; do
  case "$path" in
    CLAUDE.md|AGENTS.md|CHANGELOG.md|autoresearch/ledger/*.tsv|DOCS/coord/status/*.md|DOCS/coord/handoff/*.md|DOCS/coord/handshake/*.md)
      git cat-file -e "$BASE:$path" 2>/dev/null || continue        # new file: nothing to protect yet
      [ "$deleted" = "0" ] && continue
      if ! git cat-file -e "$HEAD_REV:$path" 2>/dev/null; then
        err "$path is append-only and was deleted"
        continue
      fi
      old=$(git show "$BASE:$path")
      new=$(git show "$HEAD_REV:$path")
      case "$new" in
        "$old"*) ;;                                                # only a missing final newline changed
        *) err "$path is append-only: $deleted existing line(s) deleted or changed" ;;
      esac
      ;;
  esac
done < <(git -c core.quotepath=false diff --numstat --no-renames "$BASE" "$HEAD_REV")

# 2. Frozen evaluation harness (active once autoresearch/prepare.sha256 exists on the base).
if git cat-file -e "$BASE:autoresearch/prepare.sha256" 2>/dev/null; then
  if git diff --name-only "$BASE" "$HEAD_REV" | grep -qE '^autoresearch/prepare\.(py|sha256)$'; then
    git log --format=%s "$BASE..$HEAD_REV" | grep -qF '[eval-change]' \
      || err "autoresearch/prepare.py is frozen (an intended change needs [eval-change] in the commit subject)"
  fi
fi
want=$(git show "$HEAD_REV:autoresearch/prepare.sha256" 2>/dev/null | cut -d' ' -f1)
if [ -n "$want" ]; then
  if command -v sha256sum >/dev/null 2>&1; then
    have=$(git show "$HEAD_REV:autoresearch/prepare.py" | sha256sum | cut -d' ' -f1)
  else
    have=$(git show "$HEAD_REV:autoresearch/prepare.py" | shasum -a 256 | cut -d' ' -f1)
  fi
  [ "$want" = "$have" ] || err "autoresearch/prepare.py does not match autoresearch/prepare.sha256"
fi

# 3. Size and secret tripwires.
while read -r path; do
  [ -n "$path" ] || continue
  size=$(git cat-file -s "$HEAD_REV:$path")
  [ "$size" -le "$max_bytes" ] || err "$path is $size bytes (limit $max_bytes): keep data out of main, list it in data/DATA_MANIFEST.tsv"
done < <(git -c core.quotepath=false diff --name-only --no-renames --diff-filter=AM "$BASE" "$HEAD_REV")
if git diff "$BASE" "$HEAD_REV" | grep -qE '^\+.*(nvapi-[A-Za-z0-9_-]{16,}|BEGIN [A-Z ]*PRIVATE KEY|"private_key"[[:space:]]*:)'; then
  err "possible secret in added lines (if it was ever pushed, rotate the key)"
fi
exit "$fail"
