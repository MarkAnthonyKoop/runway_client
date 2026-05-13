"""Thin HTTP layer for the Runway public API.

We use `requests` directly rather than the `runwayml` SDK to keep the surface
area visible — Runway has versioned the API headers historically and we want
the exact request to be obvious from one file.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from .auth import get_api_key

BASE_URL = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"


class RunwayError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {get_api_key()}",
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def post(path: str, payload: dict) -> dict:
    url = f"{BASE_URL}{path}"
    r = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=60)
    if not r.ok:
        raise RunwayError(
            f"POST {path} -> {r.status_code}: {r.text[:400]}",
            status=r.status_code, body=r.text,
        )
    return r.json()


def get(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    r = requests.get(url, headers=_headers(), timeout=30)
    if not r.ok:
        raise RunwayError(
            f"GET {path} -> {r.status_code}: {r.text[:400]}",
            status=r.status_code, body=r.text,
        )
    return r.json()
