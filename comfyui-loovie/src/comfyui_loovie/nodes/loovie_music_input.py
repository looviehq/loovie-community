"""Loovie Music Input node.

The route layer scans the workflow JSON by `class_type` and injects the
music request fields (style prompt, lyrics, instrumental flag, seed,
duration, mode) into this node before submitting the graph to ComfyUI, the
same way `LoovieTextInput` carries the image/video prompt.

Outputs (all consumed by the YuE2 graph):
  0 `prompt`       STRING  — music style description.
  1 `lyrics`       STRING  — lyric sheet with section tags.
  2 `abc_enabled`  BOOLEAN — False for instrumental (skip the ABC plan).
  3 `seed`         INT.
  4 `duration`     FLOAT   — target seconds.
  5 `mode`         STRING  — YuE2 planning mode ("full" / "off").
"""

from __future__ import annotations

from typing import Any


class LoovieMusicInput:
    """Carries a music request from the HTTP body into the YuE2 graph."""

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "lyrics": ("STRING", {"default": "", "multiline": True}),
                "instrumental": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": -1}),
                "duration": ("FLOAT", {"default": 120.0, "min": 1.0}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("prompt", "lyrics", "abc_enabled", "seed", "duration", "mode")
    FUNCTION = "build"
    CATEGORY = "loovie"

    def build(
        self,
        prompt: str,
        lyrics: str,
        instrumental: bool,
        seed: int,
        duration: float,
    ) -> tuple[str, str, bool, int, float, str]:
        return (
            prompt,
            lyrics,
            not instrumental,
            int(seed),
            float(duration),
            "off" if instrumental else "full",
        )


__all__ = ["LoovieMusicInput"]
