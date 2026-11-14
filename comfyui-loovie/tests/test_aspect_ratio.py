"""Aspect-ratio table tests.

Tables get bumped occasionally when a model updates its expected
dimensions; these tests catch accidental drops or off-by-one errors.
Every dimension here must remain a multiple of 8 (LTX) or 32 (generation
dimensions) so the encoder's tile size stays happy.
"""

from __future__ import annotations

import pytest

from comfyui_loovie.helpers.aspect_ratio import (
    IMAGE_DIMENSIONS,
    SUPPORTED_IMAGE_RATIOS,
    TARGET_VIDEO_DIMENSIONS,
    VIDEO_GEN_DIMENSIONS,
    image_dimensions,
    target_video_dimensions,
    video_dimensions,
)

# ---------------------------------------------------------------------
# Image dimensions.
# ---------------------------------------------------------------------


@pytest.mark.parametrize("ratio", list(IMAGE_DIMENSIONS.keys()))
def test_each_known_image_ratio_has_a_dimension(ratio: str) -> None:
    width, height = image_dimensions(ratio)
    assert width > 0 and height > 0
    # All shipped image dimensions are multiples of 32 (FLUX/diffusers constraint).
    assert width % 32 == 0
    assert height % 32 == 0


def test_unknown_image_ratio_falls_back_to_square_default() -> None:
    assert image_dimensions("xx:yy") == (768, 768)


def test_supported_image_ratios_match_the_dimension_table() -> None:
    assert set(SUPPORTED_IMAGE_RATIOS) == set(IMAGE_DIMENSIONS.keys())


# ---------------------------------------------------------------------
# Video dimensions.
# ---------------------------------------------------------------------


@pytest.mark.parametrize("key", list(VIDEO_GEN_DIMENSIONS.keys()))
def test_every_video_gen_pair_resolves(key: tuple[str, str]) -> None:
    aspect, resolution = key
    width, height = video_dimensions(aspect, resolution)
    # LTX 2.3 requires multiples of 8 (latent stride; some shipped values
    # like (1280, 720) are mult-of-8 but not mult-of-32).
    assert width % 8 == 0
    assert height % 8 == 0


def test_unknown_video_pair_falls_back_to_default() -> None:
    assert video_dimensions("xx:yy", "720p") == (960, 544)


@pytest.mark.parametrize("key", list(TARGET_VIDEO_DIMENSIONS.keys()))
def test_target_dimensions_round_down_to_user_visible(key: tuple[str, str]) -> None:
    """The post-crop target is always <= the generation dimensions."""
    gen_w, gen_h = VIDEO_GEN_DIMENSIONS[key]
    tgt_w, tgt_h = TARGET_VIDEO_DIMENSIONS[key]
    assert tgt_w <= gen_w
    assert tgt_h <= gen_h


def test_target_dimensions_fall_back_to_gen_dimensions_when_unknown() -> None:
    """Pair we don't list for crop targets reuses the generation dims."""
    pair = ("xx:yy", "720p")
    assert target_video_dimensions(*pair) == video_dimensions(*pair)


def test_resolution_aliases_default_to_720p() -> None:
    """Calling without explicit resolution should pick a sensible default."""
    width, height = video_dimensions("16:9")
    assert (width, height) == VIDEO_GEN_DIMENSIONS[("16:9", "720p")]


def test_no_resolution_pair_returns_zero_dimensions() -> None:
    """Defensive: no entry in either table ever returns (0,0)."""
    for key in VIDEO_GEN_DIMENSIONS:
        gen = video_dimensions(*key)
        tgt = target_video_dimensions(*key)
        assert gen[0] > 0 and gen[1] > 0
        assert tgt[0] > 0 and tgt[1] > 0


# ---------------------------------------------------------------------
# Resolution-scaled image canvases (MiniMax H3 Image and friends).
# ---------------------------------------------------------------------


@pytest.mark.parametrize("resolution", ["1K", "2K", "4K"])
@pytest.mark.parametrize("ratio", SUPPORTED_IMAGE_RATIOS)
def test_resolution_canvases_stay_on_the_32_px_grid(ratio: str, resolution: str) -> None:
    width, height = image_dimensions(ratio, resolution)
    assert width % 32 == 0
    assert height % 32 == 0
    assert width >= 32 and height >= 32


@pytest.mark.parametrize("resolution,area", [("1K", 1024**2), ("2K", 2048**2), ("4K", 4096**2)])
@pytest.mark.parametrize("ratio", SUPPORTED_IMAGE_RATIOS)
def test_resolution_canvases_track_the_requested_area(
    ratio: str, resolution: str, area: int
) -> None:
    width, height = image_dimensions(ratio, resolution)
    # Rounding each edge to the 32 px grid cannot drift more than ~12%.
    assert area * 0.85 <= width * height <= area * 1.15


@pytest.mark.parametrize("ratio", SUPPORTED_IMAGE_RATIOS)
def test_resolution_canvases_keep_the_aspect_ratio(ratio: str) -> None:
    aspect_w, aspect_h = (int(part) for part in ratio.split(":"))
    width, height = image_dimensions(ratio, "2K")
    assert abs((width / height) - (aspect_w / aspect_h)) < 0.06


def test_auto_resolution_keeps_the_legacy_table() -> None:
    for ratio, expected in IMAGE_DIMENSIONS.items():
        assert image_dimensions(ratio, "auto") == expected


def test_unknown_resolution_falls_back_to_the_legacy_table() -> None:
    assert image_dimensions("1:1", "8K") == IMAGE_DIMENSIONS["1:1"]


def test_unknown_aspect_ratio_falls_back_to_square_at_the_requested_area() -> None:
    assert image_dimensions("xx:yy", "1K") == image_dimensions("1:1", "1K")


def test_unlisted_but_parseable_ratio_still_scales() -> None:
    """21:9 is not in the legacy table but is perfectly usable at 1K/2K/4K."""

    width, height = image_dimensions("21:9", "4K")
    assert (width, height) == (6272, 2688)


def test_square_canvases_are_exact_megapixels() -> None:
    assert image_dimensions("1:1", "1K") == (1024, 1024)
    assert image_dimensions("1:1", "2K") == (2048, 2048)
    assert image_dimensions("1:1", "4K") == (4096, 4096)
