"""Where Kernel reads organizer files and writes its own cached outputs.

The same code runs on a laptop (organizer kit copied to ``workspace/``) and on
Keeboh (kit at ``/workspace``). Set ``KERNEL_KIT_DIR`` or ``KERNEL_DATA_DIR`` to override.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def kit_dir() -> Path:
    """Folder that holds the organizer starter kit (``02_QuickStats``, ``04_Evaluation``)."""
    candidates = [os.environ.get("KERNEL_KIT_DIR"), REPO / "workspace", "/workspace", REPO]
    for candidate in candidates:
        if candidate and (Path(candidate) / "02_QuickStats").is_dir():
            return Path(candidate)
    raise FileNotFoundError("organizer kit not found; set KERNEL_KIT_DIR")


def data_dir() -> Path:
    """Folder for cached outputs. Git-ignored; every file is listed in the manifest."""
    path = Path(os.environ.get("KERNEL_DATA_DIR", REPO / "data"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def secret(name: str) -> str:
    """A key from the environment or from ``.env`` (repo root, then the kit folder). Empty if unset.

    ``.env`` is git-ignored and left out of the Keeboh submission. Never print or log the value.
    """
    if os.environ.get(name):
        return os.environ[name]
    for folder in [REPO, Path("/workspace")]:
        env_file = folder / ".env"
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key.strip() == name and not key.startswith("#"):
                return value.strip().strip('"').strip("'")
    return ""


def record_in_manifest(path: Path, source_url: str) -> None:
    """Add or refresh one row of ``data/DATA_MANIFEST.tsv`` (path, bytes, sha256, source, agent, UTC).

    Skipped when ``KERNEL_NO_MANIFEST`` is set: parallel pulls must not rewrite one file at once.
    """
    if os.environ.get("KERNEL_NO_MANIFEST"):
        return
    manifest = data_dir() / "DATA_MANIFEST.tsv"
    header = "path\tbytes\tsha256\tsource_url\tmade_by\tutc"
    try:
        relative = path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        relative = path.as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    agent = os.environ.get("AGENT_ID", "unknown")
    row = f"{relative}\t{path.stat().st_size}\t{digest}\t{source_url}\t{agent}\t{stamp}"

    lines = manifest.read_text(encoding="utf-8").splitlines() if manifest.exists() else [header]
    kept = [line for line in lines if line.split("\t")[0] != relative]
    manifest.write_text("\n".join(kept + [row]) + "\n", encoding="utf-8", newline="\n")
