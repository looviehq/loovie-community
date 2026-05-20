"""Result-file validation helpers.

These guards run on the bytes returned by ComfyUI before they leave the
process boundary. They are deliberately small and dependency-free: a
magic-byte sniff and a size cap are enough to reject the common failure
modes (truncated downloads, wrong MIME, accidentally huge writes).
"""

from __future__ import annotations

from typing import Final

MAX_IMAGE_BYTES: Final[int] = 32 * 1024 * 1024  # 32 MiB
MAX_VIDEO_BYTES: Final[int] = 512 * 1024 * 1024  # 512 MiB

# (mime, magic_prefix) pairs. First match wins.
_IMAGE_MAGIC: Final[tuple[tuple[str, bytes], ...]] = (
    ("image/png", b"\x89PNG\r\n\x1a\n"),
    ("image/jpeg", b"\xff\xd8\xff"),
    ("image/webp", b"RIFF"),  # plus "WEBP" at offset 8; checked below
    ("image/gif", b"GIF87a"),
    ("image/gif", b"GIF89a"),
)

_VIDEO_MAGIC: Final[tuple[tuple[str, bytes], ...]] = (
    ("video/mp4", b"\x00\x00\x00\x18ftyp"),
    ("video/mp4", b"\x00\x00\x00\x20ftyp"),
    ("video/quicktime", b"\x00\x00\x00\x14ftyp"),
    ("video/webm", b"\x1a\x45\xdf\xa3"),
)


def sniff_image_mime(data: bytes) -> str | None:
    """Return an image MIME type if the bytes start with a known magic, else None."""
    for mime, prefix in _IMAGE_MAGIC:
        if not data.startswith(prefix):
            continue
        if mime == "image/webp":
            if len(data) >= 12 and data[8:12] == b"WEBP":
                return mime
            continue
        return mime
    return None


def sniff_video_mime(data: bytes) -> str | None:
    """Return a video MIME type if the bytes start with a known magic, else None."""
    head = data[:32]
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return "video/mp4"
    for mime, prefix in _VIDEO_MAGIC:
        if data.startswith(prefix):
            return mime
    return None


def validate_image_bytes(data: bytes) -> str:
    """Validate `data` as an image. Returns the sniffed MIME or raises."""
    if not data:
        raise ValueError("empty payload")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image too large: {len(data)} bytes (max {MAX_IMAGE_BYTES})")
    mime = sniff_image_mime(data)
    if mime is None:
        raise ValueError("payload does not match a supported image format")
    return mime


def validate_video_bytes(data: bytes) -> str:
    """Validate `data` as a video. Returns the sniffed MIME or raises."""
    if not data:
        raise ValueError("empty payload")
    if len(data) > MAX_VIDEO_BYTES:
        raise ValueError(f"video too large: {len(data)} bytes (max {MAX_VIDEO_BYTES})")
    mime = sniff_video_mime(data)
    if mime is None:
        raise ValueError("payload does not match a supported video format")
    return mime
