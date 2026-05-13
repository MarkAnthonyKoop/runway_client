"""Batch orchestration: a list of gap specs → a list of downloaded MP4s.

Each gap is a dict (typically from `video_composer.list_gaps`):

    {
        "id": "seg-04",
        "duration": 8.0,
        "prompt": "Slow zoom on weathered hands cupping coins…",
        "context_before": "…",
        "context_after": "…",
        "resolution": [1920, 1080],
    }

For each gap we:
    1. text_to_image(prompt)        → still task
    2. poll until SUCCEEDED         → image URL
    3. image_to_video(image, prompt, duration) → motion task
    4. poll until SUCCEEDED         → video URL
    5. download                     → MP4 path

The result is `{gap_id: Path}`. Failures are surfaced per-gap so a single bad
prompt doesn't sink the batch.
"""

from __future__ import annotations

from pathlib import Path

from . import generate, poll, download
from .api import RunwayError


def _ratio_from_resolution(resolution) -> str:
    w, h = resolution
    return f"{w}:{h}"


def _quantize_duration(d: float) -> int:
    # Runway supports 5s and 10s clips (Gen-4 turbo). Round up.
    return 5 if d <= 5 else 10


def fill_gap(gap: dict, *, image_model: str | None = None,
             video_model: str | None = None,
             progress=print) -> Path:
    ratio = _ratio_from_resolution(gap.get("resolution", [1920, 1080]))
    duration = _quantize_duration(float(gap["duration"]))
    prompt = gap["prompt"].strip()

    progress(f"  {gap['id']}: text_to_image …")
    img_kwargs = {"ratio": ratio}
    if image_model:
        img_kwargs["model"] = image_model
    img_task_id = generate.text_to_image(prompt, **img_kwargs)
    img_task = poll.wait(img_task_id)
    image_url = img_task["output"][0]

    progress(f"  {gap['id']}: image_to_video ({duration}s) …")
    vid_kwargs = {"prompt": prompt, "duration": duration, "ratio": ratio}
    if video_model:
        vid_kwargs["model"] = video_model
    vid_task_id = generate.image_to_video(image_url, **vid_kwargs)
    vid_task = poll.wait(vid_task_id, timeout=900)

    progress(f"  {gap['id']}: downloading …")
    paths = download.fetch(vid_task, name=gap["id"])
    return paths[0]


def fill_all(gaps: list[dict], *, image_model: str | None = None,
             video_model: str | None = None,
             progress=print) -> dict[str, Path | RunwayError]:
    out: dict[str, Path | RunwayError] = {}
    for gap in gaps:
        try:
            out[gap["id"]] = fill_gap(
                gap, image_model=image_model, video_model=video_model,
                progress=progress,
            )
        except RunwayError as e:
            progress(f"  {gap['id']}: FAILED — {e}")
            out[gap["id"]] = e
    return out
