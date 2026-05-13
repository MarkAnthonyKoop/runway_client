"""Submit generation tasks to Runway.

Two task types matter for our gap-filling flow:

  * `text_to_image` — produces a still that we then animate.
  * `image_to_video` — animates a still per a motion prompt.

Both return a task id. Use `poll.wait` to block until SUCCEEDED, then
`download.fetch` to pull the result.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from .api import post

DEFAULT_VIDEO_MODEL = "gen4_turbo"
DEFAULT_IMAGE_MODEL = "gen4_image"


def _image_to_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def text_to_image(prompt: str, ratio: str = "1920:1080",
                  model: str = DEFAULT_IMAGE_MODEL, seed: int | None = None) -> str:
    payload: dict = {"promptText": prompt, "model": model, "ratio": ratio}
    if seed is not None:
        payload["seed"] = seed
    resp = post("/text_to_image", payload)
    return resp["id"]


def image_to_video(image: str | Path, prompt: str = "",
                   duration: int = 5, ratio: str = "1920:1080",
                   model: str = DEFAULT_VIDEO_MODEL,
                   seed: int | None = None) -> str:
    if isinstance(image, Path) or (isinstance(image, str) and not image.startswith(("http://", "https://", "data:"))):
        prompt_image = _image_to_data_uri(Path(image))
    else:
        prompt_image = str(image)

    payload: dict = {
        "promptImage": prompt_image,
        "model": model,
        "ratio": ratio,
        "duration": duration,
    }
    if prompt:
        payload["promptText"] = prompt
    if seed is not None:
        payload["seed"] = seed
    resp = post("/image_to_video", payload)
    return resp["id"]
