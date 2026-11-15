"""`LoovieReferenceVideoInput` node: download 1-3 reference video URLs for H3 ref2v.

MiniMax H3's reference-to-video task takes up to 3 reference clips, 2-15 s each.
ComfyUI's `MiniMaxH3ReferenceToVideo` consumes them through an autogrow
`ref_videos` map (`ref_video_1` ...) of IMAGE frame batches at 24 fps. A graph
is static and cannot know how many clips a request carries, so this adapter
mirrors `LoovieAudioInput`:

  - `video_url_1` ... `video_url_3` are the request's URLs (injected by the
    route layer from `reference_video_urls`, ref2v only),
  - each clip is downloaded and decoded with the same helpers as
    `LoovieVideoInput`, then resampled to 24 fps and capped at 15 s,
  - the node returns the list of frame tensors plus its count, which
    `LoovieH3ReferenceToVideo` turns into the numbered `ref_videos` entries.

Nothing here enforces the vendor's 2-15 s lower bound; the API validates the
declared lengths before the lease is issued. The node hands ComfyUI the clips
the request actually asked for.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import torch

from .loovie_video_input import _decode_frames, _download

logger = logging.getLogger("comfyui_loovie.nodes.reference_video_input")

_MAX_SLOTS = 3
_TARGET_FPS = 24
_MAX_SECONDS = 15
# Upper bound on frames decoded from the source before resampling (15 s at up
# to 120 fps), so a long or high-fps clip cannot exhaust memory.
_MAX_DECODE_FRAMES = _MAX_SECONDS * 120


def _resample_to_target_fps(
    frames: np.ndarray[Any, Any], source_fps: float
) -> np.ndarray[Any, Any]:
    """Pick the nearest source frame for each 24 fps tick, capped at 15 s."""
    count = int(frames.shape[0])
    fps = source_fps if source_fps and source_fps > 0 else float(_TARGET_FPS)
    duration = count / fps
    target_count = max(1, min(math.floor(duration * _TARGET_FPS), _MAX_SECONDS * _TARGET_FPS))
    if abs(fps - _TARGET_FPS) < 1e-3:
        return frames[:target_count]
    indices = np.minimum((np.arange(target_count) * fps / _TARGET_FPS).astype(int), count - 1)
    return frames[indices]


def _load_clip(url: str) -> torch.Tensor:
    """Download `url` and return IMAGE frames `[N, H, W, 3]` in `[0, 1]` at 24 fps."""
    frames_np, fps = _decode_frames(_download(url), _MAX_DECODE_FRAMES)
    resampled = _resample_to_target_fps(frames_np, fps)
    return torch.from_numpy(np.ascontiguousarray(resampled)).float().div(255.0)


class LoovieReferenceVideoInput:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        optional: dict[str, Any] = {}
        for slot in range(1, _MAX_SLOTS + 1):
            optional[f"video_url_{slot}"] = ("STRING", {"default": ""})
        return {"optional": optional}

    RETURN_TYPES = ("LOOVIE_VIDEO_LIST", "INT")
    RETURN_NAMES = ("VIDEOS", "VIDEO_COUNT")
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(
        self,
        video_url_1: str = "",
        video_url_2: str = "",
        video_url_3: str = "",
    ) -> tuple[list[torch.Tensor], int]:
        urls = [
            str(url).strip() for url in (video_url_1, video_url_2, video_url_3) if str(url).strip()
        ][:_MAX_SLOTS]
        videos = [_load_clip(url) for url in urls]
        return videos, len(videos)


__all__ = ["LoovieReferenceVideoInput"]
