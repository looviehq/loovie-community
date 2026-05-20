"""`LoovieSettings` node: aspect ratio + seed -> WIDTH / HEIGHT / SEED."""

from __future__ import annotations

import random

from ..helpers.aspect_ratio import SUPPORTED_IMAGE_RATIOS, image_dimensions


class LoovieSettings:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "aspect_ratio": (SUPPORTED_IMAGE_RATIOS, {"default": "1:1"}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**53}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("WIDTH", "HEIGHT", "SEED")
    FUNCTION = "process"
    CATEGORY = "loovie"

    @classmethod
    def IS_CHANGED(cls, aspect_ratio: str, seed: int) -> float | int:
        # `seed < 0` is the "randomise every run" sentinel. Returning NaN
        # (never equal to itself) forces ComfyUI to re-run the node so a
        # fresh seed is drawn; otherwise the whole graph cache-hits with
        # a stale seed and produces no outputs.
        if seed < 0:
            return float("nan")
        return seed

    def process(self, aspect_ratio: str, seed: int) -> tuple[int, int, int]:
        width, height = image_dimensions(aspect_ratio)
        if seed < 0:
            seed = random.randint(0, 2**53)
        return (width, height, seed)
