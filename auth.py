"""Discover a Runway API key.

Lookup order (first hit wins):
    1. `RUNWAY_API_KEY` env var
    2. `~/.cache/runway_client/api_key` (plain text)
Raises `MissingKey` with a help message if none found.

(A legacy WSL-era fallback that grepped `/mnt/c/z/personal/phones` was removed
2026-07-30 — that path does not exist on macOS. Use `credanger` or the two
sources above.)
"""

from __future__ import annotations

import os
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "runway_client"
KEY_FILE = CACHE_DIR / "api_key"


class MissingKey(RuntimeError):
    pass


def get_api_key() -> str:
    key = os.environ.get("RUNWAY_API_KEY", "").strip()
    if key:
        return key
    if KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
        if key:
            return key
    raise MissingKey(
        "no Runway API key found.\n"
        f"Set $RUNWAY_API_KEY, or write the key to {KEY_FILE}."
    )


def save_api_key(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(key.strip())
    KEY_FILE.chmod(0o600)
    return KEY_FILE
