"""Aspect-ratio to pixel-dimension lookups.

The image table is tuned for the diffusion model checkpoints the
reference workflows ship with (FLUX.2 Klein). The video table maps
`(aspect_ratio, resolution)` pairs to LTX-compatible dimensions
(multiples of 32) and a separate post-decode crop target so the band
artefacts LTX 2.3 leaves in the padded rows can be trimmed.
"""

from __future__ import annotations

from typing import Final

IMAGE_DIMENSIONS: Final[dict[str, tuple[int, int]]] = {
    "1:1": (768, 768),
    "4:3": (768, 576),
    "3:4": (576, 768),
    "16:9": (896, 512),
    "9:16": (512, 896),
    "3:2": (768, 512),
    "2:3": (512, 768),
}

SUPPORTED_IMAGE_RATIOS: Final[list[str]] = list(IMAGE_DIMENSIONS.keys())


def image_dimensions(aspect_ratio: str) -> tuple[int, int]:
    """Return (width, height) for `aspect_ratio`, defaulting to 1:1."""
    return IMAGE_DIMENSIONS.get(aspect_ratio, (768, 768))


# LTX-friendly generation dimensions. Multiples of 32 are required by the
# encoder/sampler; the post-decode crop trims back to the user-visible
# target size in `TARGET_VIDEO_DIMENSIONS`.
VIDEO_GEN_DIMENSIONS: Final[dict[tuple[str, str], tuple[int, int]]] = {
    ("16:9", "384p"): (672, 384),
    ("16:9", "480p"): (864, 480),
    ("16:9", "540p"): (960, 544),
    ("16:9", "720p"): (1280, 720),
    ("16:9", "768p"): (1344, 768),
    ("16:9", "1080p"): (1920, 1088),
    ("16:9", "2K"): (2560, 1440),
    ("9:16", "384p"): (384, 672),
    ("9:16", "480p"): (480, 864),
    ("9:16", "540p"): (544, 960),
    ("9:16", "720p"): (720, 1280),
    ("9:16", "768p"): (768, 1344),
    ("9:16", "1080p"): (1088, 1920),
    ("9:16", "2K"): (1440, 2560),
    ("4:3", "384p"): (512, 384),
    ("4:3", "480p"): (640, 480),
    ("4:3", "540p"): (720, 544),
    ("4:3", "720p"): (960, 736),
    ("4:3", "768p"): (1024, 768),
    ("4:3", "1080p"): (1440, 1088),
    ("4:3", "2K"): (1920, 1440),
    ("3:4", "384p"): (384, 512),
    ("3:4", "480p"): (480, 640),
    ("3:4", "540p"): (544, 720),
    ("3:4", "720p"): (736, 960),
    ("3:4", "768p"): (768, 1024),
    ("3:4", "1080p"): (1088, 1440),
    ("3:4", "2K"): (1440, 1920),
    ("1:1", "384p"): (384, 384),
    ("1:1", "480p"): (480, 480),
    ("1:1", "540p"): (544, 544),
    ("1:1", "720p"): (736, 736),
    ("1:1", "768p"): (768, 768),
    ("1:1", "1080p"): (1088, 1088),
    ("1:1", "2K"): (1440, 1440),
}

TARGET_VIDEO_DIMENSIONS: Final[dict[tuple[str, str], tuple[int, int]]] = {
    ("16:9", "384p"): (672, 384),
    ("16:9", "480p"): (864, 480),
    ("16:9", "540p"): (960, 540),
    ("16:9", "720p"): (1280, 720),
    ("16:9", "768p"): (1344, 768),
    ("16:9", "1080p"): (1920, 1080),
    ("16:9", "2K"): (2560, 1440),
    ("9:16", "384p"): (384, 672),
    ("9:16", "480p"): (480, 864),
    ("9:16", "540p"): (540, 960),
    ("9:16", "720p"): (720, 1280),
    ("9:16", "768p"): (768, 1344),
    ("9:16", "1080p"): (1080, 1920),
    ("9:16", "2K"): (1440, 2560),
    ("4:3", "384p"): (512, 384),
    ("4:3", "480p"): (640, 480),
    ("4:3", "540p"): (720, 540),
    ("4:3", "720p"): (960, 720),
    ("4:3", "768p"): (1024, 768),
    ("4:3", "1080p"): (1440, 1080),
    ("4:3", "2K"): (1920, 1440),
    ("3:4", "384p"): (384, 512),
    ("3:4", "480p"): (480, 640),
    ("3:4", "540p"): (540, 720),
    ("3:4", "720p"): (720, 960),
    ("3:4", "768p"): (768, 1024),
    ("3:4", "1080p"): (1080, 1440),
    ("3:4", "2K"): (1440, 1920),
    ("1:1", "384p"): (384, 384),
    ("1:1", "480p"): (480, 480),
    ("1:1", "540p"): (540, 540),
    ("1:1", "720p"): (720, 720),
    ("1:1", "768p"): (768, 768),
    ("1:1", "1080p"): (1080, 1080),
    ("1:1", "2K"): (1440, 1440),
}

_DEFAULT_VIDEO_DIMENSIONS: Final[tuple[int, int]] = (960, 544)


def video_dimensions(aspect_ratio: str, resolution: str = "720p") -> tuple[int, int]:
    """Return the generation dimensions for `(aspect_ratio, resolution)`."""
    return VIDEO_GEN_DIMENSIONS.get((aspect_ratio, resolution), _DEFAULT_VIDEO_DIMENSIONS)


def target_video_dimensions(aspect_ratio: str, resolution: str = "720p") -> tuple[int, int]:
    """Return the post-crop target dimensions; falls back to the gen dims."""
    return TARGET_VIDEO_DIMENSIONS.get(
        (aspect_ratio, resolution),
        video_dimensions(aspect_ratio, resolution),
    )
