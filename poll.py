"""Poll a Runway task until terminal state."""

from __future__ import annotations

import time
from typing import Any

from .api import get, RunwayError

TERMINAL_SUCCESS = "SUCCEEDED"
TERMINAL_FAIL = ("FAILED", "CANCELLED")


def status(task_id: str) -> dict:
    return get(f"/tasks/{task_id}")


def wait(task_id: str, *, timeout: float = 600.0, interval: float = 5.0,
         on_update: Any = None) -> dict:
    """Block until the task reaches a terminal state. Returns the final task dict.

    `on_update` is an optional callable: `on_update(task_dict)` called after
    every poll, useful for progress reporting.
    """
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        last = status(task_id)
        if on_update:
            on_update(last)
        s = last.get("status")
        if s == TERMINAL_SUCCESS:
            return last
        if s in TERMINAL_FAIL:
            raise RunwayError(
                f"task {task_id} ended in {s}: {last.get('failure', 'no detail')}",
                body=last,
            )
        time.sleep(interval)
    raise RunwayError(f"task {task_id} timed out after {timeout:.0f}s", body=last)
