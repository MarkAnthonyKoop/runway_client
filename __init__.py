"""runway_client — minimal Runway public-API client for the gap-filling flow.

Two-step pipeline: text_to_image → image_to_video, with polling and download.
Designed to consume the JSON shape that `video_composer gaps --json` emits.
"""

from .auth import get_api_key, save_api_key, MissingKey
from .api import RunwayError
from .generate import text_to_image, image_to_video
from .poll import status, wait
from .download import fetch
from .batch import fill_gap, fill_all

__all__ = [
    "get_api_key",
    "save_api_key",
    "MissingKey",
    "RunwayError",
    "text_to_image",
    "image_to_video",
    "status",
    "wait",
    "fetch",
    "fill_gap",
    "fill_all",
]
