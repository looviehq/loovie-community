"""`LoovieSettings` node: aspect ratio + resolution + seed -> WIDTH / HEIGHT / SEED.

`resolution` is optional and defaults to `auto`, which keeps the legacy
768 px image table every shipped graph was tuned around. Models that advertise
a real 1K/2K/4K canvas (MiniMax H3 Image) opt in through
`ModelSpec.resolution_scales_canvas`, and the route layer injects the requested
resolution here; the node then returns a canvas of that area on the 32 px grid.

It stays **optional** on purpose: a required input would make every older
workflow JSON (operator edits included) fail ComfyUI validation with
`required_input_missing`, and the default already means "behave as before".
"""

from __future__ import annotations

import random

from ..helpers.aspect_ratio import IMAGE_RESOLUTIONS, SUPPORTED_IMAGE_RATIOS, image_dimensions


class LoovieSettings:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "aspect_ratio": (SUPPORTED_IMAGE_RATIOS, {"default": "1:1"}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**53}),
            },
            "optional": {
                "resolution": (list(IMAGE_RESOLUTIONS), {"default": "auto"}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("WIDTH", "HEIGHT", "SEED")
    FUNCTION = "process"
    CATEGORY = "loovie"

    @classmethod
    def IS_CHANGED(cls, aspect_ratio: str, seed: int, resolution: str = "auto") -> float | int:
        # `seed < 0` is the "randomise every run" sentinel. Returning NaN
        # (never equal to itself) forces ComfyUI to re-run the node so a
        # fresh seed is drawn; otherwise the whole graph cache-hits with
        # a stale seed and produces no outputs.
        if seed < 0:
            return float("nan")
        return hash((seed, aspect_ratio, resolution))

    def process(
        self, aspect_ratio: str, seed: int, resolution: str = "auto"
    ) -> tuple[int, int, int]:
        width, height = image_dimensions(aspect_ratio, resolution)
        if seed < 0:
            seed = random.randint(0, 2**53)
        return (width, height, seed)
