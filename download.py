"""Download Runway task outputs to ~/.cache/runway_client/results/."""

from __future__ import annotations

from pathlib import Path

import requests

RESULTS_DIR = Path("~/.cache/runway_client/results").expanduser()


def _ext_from_url(url: str) -> str:
    path = url.split("?", 1)[0]
    if "." in path.rsplit("/", 1)[-1]:
        return "." + path.rsplit(".", 1)[-1]
    return ".mp4"


def fetch(task: dict, dest_dir: Path = RESULTS_DIR, name: str | None = None) -> list[Path]:
    """Download every URL in `task['output']` to `dest_dir`. Returns the saved paths.

    `task` is the dict returned by `poll.wait`. Most jobs produce one output;
    image_to_video can produce multiple if you set `numResults>1`.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    urls = task.get("output") or []
    if not urls:
        raise ValueError(f"task {task.get('id')} has no output urls")

    saved: list[Path] = []
    for i, url in enumerate(urls):
        stem = name or task.get("id", "result")
        suffix = "" if len(urls) == 1 else f"_{i}"
        path = dest_dir / f"{stem}{suffix}{_ext_from_url(url)}"
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if chunk:
                        f.write(chunk)
        saved.append(path)
    return saved
