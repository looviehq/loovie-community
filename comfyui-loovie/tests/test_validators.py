"""Magic-byte / size / MIME validation tests.

Result-file validation runs on the bytes returned by ComfyUI before they
leave the process boundary. Pinning the magic-byte table here prevents
silent regressions when someone adds a new format or tweaks a prefix.
"""

from __future__ import annotations

import pytest

from comfyui_loovie.validators import (
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
    sniff_image_mime,
    sniff_video_mime,
    validate_image_bytes,
    validate_video_bytes,
)

# ---------------------------------------------------------------------
# sniff_image_mime
# ---------------------------------------------------------------------


def test_png_is_recognised(png_bytes: bytes) -> None:
    assert sniff_image_mime(png_bytes) == "image/png"


def test_jpeg_is_recognised(jpeg_bytes: bytes) -> None:
    assert sniff_image_mime(jpeg_bytes) == "image/jpeg"


def test_webp_is_recognised(webp_bytes: bytes) -> None:
    assert sniff_image_mime(webp_bytes) == "image/webp"


def test_gif87a_and_gif89a_are_recognised(gif_bytes: bytes) -> None:
    assert sniff_image_mime(gif_bytes) == "image/gif"
    assert sniff_image_mime(b"GIF87a" + b"\x00" * 16) == "image/gif"


def test_riff_without_webp_marker_is_not_an_image() -> None:
    """A RIFF container that isn't WebP (e.g. WAV) must not be sniffed as image/webp."""
    not_webp = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"\x00" * 16
    assert sniff_image_mime(not_webp) is None


def test_random_bytes_are_not_an_image(random_bytes: bytes) -> None:
    assert sniff_image_mime(random_bytes) is None


def test_truncated_webp_riff_is_rejected() -> None:
    """A RIFF header alone (no WEBP marker at offset 8) is not webp."""
    truncated = b"RIFF\x00\x00\x00\x00"  # 8 bytes, no offset-8 marker
    assert sniff_image_mime(truncated) is None


# ---------------------------------------------------------------------
# sniff_video_mime
# ---------------------------------------------------------------------


def test_mp4_ftyp_is_recognised(mp4_bytes: bytes) -> None:
    assert sniff_video_mime(mp4_bytes) == "video/mp4"


def test_webm_ebml_is_recognised(webm_bytes: bytes) -> None:
    assert sniff_video_mime(webm_bytes) == "video/webm"


def test_random_bytes_are_not_a_video(random_bytes: bytes) -> None:
    assert sniff_video_mime(random_bytes) is None


def test_image_bytes_are_not_misidentified_as_video(png_bytes: bytes) -> None:
    assert sniff_video_mime(png_bytes) is None


# ---------------------------------------------------------------------
# validate_image_bytes
# ---------------------------------------------------------------------


def test_validate_image_returns_mime(png_bytes: bytes) -> None:
    assert validate_image_bytes(png_bytes) == "image/png"


def test_validate_image_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_image_bytes(b"")


def test_validate_image_rejects_oversize(png_bytes: bytes) -> None:
    huge = png_bytes + b"\x00" * (MAX_IMAGE_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        validate_image_bytes(huge)


def test_validate_image_rejects_unknown_format(random_bytes: bytes) -> None:
    with pytest.raises(ValueError, match="does not match"):
        validate_image_bytes(random_bytes)


# ---------------------------------------------------------------------
# validate_video_bytes
# ---------------------------------------------------------------------


def test_validate_video_returns_mime(mp4_bytes: bytes) -> None:
    assert validate_video_bytes(mp4_bytes) == "video/mp4"


def test_validate_video_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_video_bytes(b"")


def test_validate_video_rejects_oversize(mp4_bytes: bytes) -> None:
    huge = mp4_bytes + b"\x00" * (MAX_VIDEO_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        validate_video_bytes(huge)


def test_validate_video_rejects_unknown_format(random_bytes: bytes) -> None:
    with pytest.raises(ValueError, match="does not match"):
        validate_video_bytes(random_bytes)


# ---------------------------------------------------------------------
# Size constants sanity.
# ---------------------------------------------------------------------


def test_size_caps_are_in_a_sensible_range() -> None:
    """A regression guard against accidentally lowering these caps to 0."""
    assert MAX_IMAGE_BYTES > 1 * 1024 * 1024  # at least 1 MiB
    assert MAX_VIDEO_BYTES > 16 * 1024 * 1024  # at least 16 MiB
    assert MAX_VIDEO_BYTES > MAX_IMAGE_BYTES
