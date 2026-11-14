"""Aspect-ratio to pixel-dimension lookups.

The image table is tuned for the diffusion model checkpoints the
reference workflows ship with (FLUX.2 Klein); `image_dimensions()` can also
scale the canvas to a requested 1K/2K/4K area for models that advertise those
resolutions. The video table maps `(aspect_ratio, resolution)` pairs to
LTX-compatible dimensions (multiples of 32) and a separate post-decode crop
target so the band artefacts LTX 2.3 leaves in the padded rows can be trimmed.
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

#: Image resolutions whose canvas scales with the request instead of using the
#: legacy 768 px table. `auto` keeps the legacy table: the models that were
#: tuned around it (FLUX.2 Klein, Qwen-Image 2.1, Krea 2) render exactly as
#: they did before, while models that advertise 1K/2K/4K (MiniMax H3 Image is
#: trained on 4-16 MP and degrades below 4 MP) get the canvas they expect.
IMAGE_RESOLUTION_AREAS: Final[dict[str, int]] = {
    "1K": 1024 * 1024,
    "2K": 2048 * 2048,
    "4K": 4096 * 4096,
}

IMAGE_RESOLUTIONS: Final[tuple[str, ...]] = ("auto", *IMAGE_RESOLUTION_AREAS)


def _ratio_pair(aspect_ratio: str) -> tuple[int, int] | None:
    """Parse `"16:9"` into `(16, 9)`; None when the value is not a ratio."""
    left, _, right = aspect_ratio.partition(":")
    try:
        width, height = int(left), int(right)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def image_dimensions(aspect_ratio: str, resolution: str = "auto") -> tuple[int, int]:
    """Return (width, height) for `aspect_ratio` at `resolution`.

    `resolution="auto"` returns the legacy fixed table (768 px base). `1K`,
    `2K` and `4K` scale the canvas to 1, 4 and 16 megapixels respectively and
    round every edge to a multiple of 32, which is the grid the shipped image
    models (and MiniMax H3 Image's VAE) require. An unknown ratio falls back
    to 1:1 so the graph always gets a legal pair.
    """
    area = IMAGE_RESOLUTION_AREAS.get(resolution)
    if area is None:
        return IMAGE_DIMENSIONS.get(aspect_ratio, (768, 768))

    pair = _ratio_pair(aspect_ratio) or _ratio_pair("1:1")
    assert pair is not None  # literal "1:1" always parses
    ratio_w, ratio_h = pair
    scale = (area / (ratio_w * ratio_h)) ** 0.5
    width = max(32, round(ratio_w * scale / 32) * 32)
    height = max(32, round(ratio_h * scale / 32) * 32)
    return width, height


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
    ("16:9", "4K"): (3840, 2176),
    ("9:16", "384p"): (384, 672),
    ("9:16", "480p"): (480, 864),
    ("9:16", "540p"): (544, 960),
    ("9:16", "720p"): (720, 1280),
    ("9:16", "768p"): (768, 1344),
    ("9:16", "1080p"): (1088, 1920),
    ("9:16", "2K"): (1440, 2560),
    ("9:16", "4K"): (2176, 3840),
    ("4:3", "384p"): (512, 384),
    ("4:3", "480p"): (640, 480),
    ("4:3", "540p"): (720, 544),
    ("4:3", "720p"): (960, 736),
    ("4:3", "768p"): (1024, 768),
    ("4:3", "1080p"): (1440, 1088),
    ("4:3", "2K"): (1920, 1440),
    ("4:3", "4K"): (2880, 2176),
    ("3:4", "384p"): (384, 512),
    ("3:4", "480p"): (480, 640),
    ("3:4", "540p"): (544, 720),
    ("3:4", "720p"): (736, 960),
    ("3:4", "768p"): (768, 1024),
    ("3:4", "1080p"): (1088, 1440),
    ("3:4", "2K"): (1440, 1920),
    ("3:4", "4K"): (2176, 2880),
    ("1:1", "384p"): (384, 384),
    ("1:1", "480p"): (480, 480),
    ("1:1", "540p"): (544, 544),
    ("1:1", "720p"): (736, 736),
    ("1:1", "768p"): (768, 768),
    ("1:1", "1080p"): (1088, 1088),
    ("1:1", "2K"): (1440, 1440),
    ("1:1", "4K"): (2176, 2176),
}

TARGET_VIDEO_DIMENSIONS: Final[dict[tuple[str, str], tuple[int, int]]] = {
    ("16:9", "384p"): (672, 384),
    ("16:9", "480p"): (864, 480),
    ("16:9", "540p"): (960, 540),
    ("16:9", "720p"): (1280, 720),
    ("16:9", "768p"): (1344, 768),
    ("16:9", "1080p"): (1920, 1080),
    ("16:9", "2K"): (2560, 1440),
    ("16:9", "4K"): (3840, 2160),
    ("9:16", "384p"): (384, 672),
    ("9:16", "480p"): (480, 864),
    ("9:16", "540p"): (540, 960),
    ("9:16", "720p"): (720, 1280),
    ("9:16", "768p"): (768, 1344),
    ("9:16", "1080p"): (1080, 1920),
    ("9:16", "2K"): (1440, 2560),
    ("9:16", "4K"): (2160, 3840),
    ("4:3", "384p"): (512, 384),
    ("4:3", "480p"): (640, 480),
    ("4:3", "540p"): (720, 540),
    ("4:3", "720p"): (960, 720),
    ("4:3", "768p"): (1024, 768),
    ("4:3", "1080p"): (1440, 1080),
    ("4:3", "2K"): (1920, 1440),
    ("4:3", "4K"): (2880, 2160),
    ("3:4", "384p"): (384, 512),
    ("3:4", "480p"): (480, 640),
    ("3:4", "540p"): (540, 720),
    ("3:4", "720p"): (720, 960),
    ("3:4", "768p"): (768, 1024),
    ("3:4", "1080p"): (1080, 1440),
    ("3:4", "2K"): (1440, 1920),
    ("3:4", "4K"): (2160, 2880),
    ("1:1", "384p"): (384, 384),
    ("1:1", "480p"): (480, 480),
    ("1:1", "540p"): (540, 540),
    ("1:1", "720p"): (720, 720),
    ("1:1", "768p"): (768, 768),
    ("1:1", "1080p"): (1080, 1080),
    ("1:1", "2K"): (1440, 1440),
    ("1:1", "4K"): (2160, 2160),
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
