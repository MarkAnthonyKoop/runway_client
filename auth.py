"""Discover a Runway API key.

Lookup order (first hit wins):
    1. `RUNWAY_API_KEY` env var
    2. `~/.cache/runway_client/api_key` (plain text)
    3. `/mnt/c/z/personal/phones` (grep "runway")
Raises `MissingKey` with a help message if none found.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "runway_client"
KEY_FILE = CACHE_DIR / "api_key"
PHONES_FILE = Path("/mnt/c/z/personal/phones")


class MissingKey(RuntimeError):
    pass


def _scan_phones(path: Path) -> str | None:
    if not path.exists():
        return None
    pat = re.compile(r"runway[^=:]*[=:]\s*([A-Za-z0-9_\-]+)", re.IGNORECASE)
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None
    m = pat.search(text)
    return m.group(1) if m else None


def get_api_key() -> str:
    key = os.environ.get("RUNWAY_API_KEY", "").strip()
    if key:
        return key
    if KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
        if key:
            return key
    found = _scan_phones(PHONES_FILE)
    if found:
        return found
    raise MissingKey(
        "no Runway API key found.\n"
        "Set $RUNWAY_API_KEY, or write the key to "
        f"{KEY_FILE}, or add a 'runway: <key>' line to {PHONES_FILE}."
    )


def save_api_key(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(key.strip())
    KEY_FILE.chmod(0o600)
    return KEY_FILE
