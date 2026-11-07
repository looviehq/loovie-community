"""Loovie SFX Input node.

The route layer scans the workflow JSON by `class_type` and injects the
sound-effect request fields (prompt, negative prompt, duration, seed) into
this node before submitting the graph to ComfyUI, the same way
`LoovieMusicInput` carries a music request.

Outputs (all consumed by the Stable Audio graph):
  0 `prompt`          STRING — sound-effect description.
  1 `negative_prompt` STRING — characteristics to steer away from.
  2 `duration`        FLOAT  — target seconds.
  3 `seed`            INT.
"""

from __future__ import annotations

from typing import Any


class LoovieSfxInput:
    """Carries a sound-effect request from the HTTP body into the graph."""

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "negative_prompt": ("STRING", {"default": "", "multiline": True}),
                "duration": ("FLOAT", {"default": 5.0, "min": 1.0, "max": 60.0}),
                "seed": ("INT", {"default": -1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "INT")
    RETURN_NAMES = ("prompt", "negative_prompt", "duration", "seed")
    FUNCTION = "build"
    CATEGORY = "loovie"

    def build(
        self,
        prompt: str,
        negative_prompt: str,
        duration: float,
        seed: int,
    ) -> tuple[str, str, float, int]:
        return (
            prompt,
            negative_prompt,
            float(duration),
            int(seed),
        )


__all__ = ["LoovieSfxInput"]
