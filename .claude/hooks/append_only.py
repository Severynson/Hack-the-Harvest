#!/usr/bin/env python3
"""PreToolUse guard for Edit|Write: shared files are append-only; the pinned evaluation harness is frozen."""
import json
import os
import sys

APPEND_ONLY = {"CLAUDE.md", "AGENTS.md", "CHANGELOG.md"}


def deny(message):
    print(message, file=sys.stderr)  # exit code 2 blocks the tool call; stderr goes back to Claude
    sys.exit(2)


try:
    event = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
tool = event.get("tool_name", "")
tool_input = event.get("tool_input") or {}
path = tool_input.get("file_path") or ""
name = os.path.basename(path)
root = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()

if path.replace("\\", "/").endswith("autoresearch/prepare.py") and os.path.exists(
    os.path.join(root, "autoresearch", "prepare.sha256")
):
    deny("Blocked: autoresearch/prepare.py is the frozen evaluation harness. Edit autoresearch/train.py instead.")
# Only the root copies are shared contracts (autoresearch/ generates its own per-session CLAUDE.md).
if name not in APPEND_ONLY or os.path.dirname(os.path.abspath(path)) != os.path.abspath(root):
    sys.exit(0)
if tool == "Write" and os.path.exists(path):
    with open(path, encoding="utf-8") as handle:
        old = handle.read()
    if not tool_input.get("content", "").startswith(old.rstrip("\n")):
        deny(f"Blocked: {name} is append-only. Keep every existing line unchanged and add new text at the end.")
if tool == "Edit":
    if not tool_input.get("new_string", "").startswith(tool_input.get("old_string", "")):
        deny(f"Blocked: {name} is append-only. Use an Edit whose new_string starts with the unchanged old_string.")
sys.exit(0)
