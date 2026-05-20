"""URL-based image cache.

Downloads HTTP(S) image references into ComfyUI's `input/` directory,
sniffs the magic bytes, and returns a path relative to the input dir
that ComfyUI nodes can pass straight to `LoadImage`. SSRF protections:
the URL must be HTTP(S), and the hostname must not resolve to a
private/loopback/link-local IP.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import urllib.parse
import urllib.request
from pathlib import Path

from ..validators import sniff_image_mime

logger = logging.getLogger("comfyui_loovie.helpers.image_cache")

_CACHE_SUBDIR = "loovie_cache"


def _get_input_dir() -> Path:
    """Resolve ComfyUI's input directory, falling back to `./input`."""
    try:
        import folder_paths
    except ImportError:
        return Path("input")
    return Path(folder_paths.get_input_directory())


def validate_url(url: str) -> None:
    """Reject URLs that would let a caller reach private networks."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme '{parsed.scheme}' not allowed; must be http or https")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        # Hostname is a domain; DNS resolution is the OS's problem.
        return
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        raise ValueError(f"URL points to a private/internal address: {hostname}")


def _cache_dir() -> Path:
    path = _get_input_dir() / _CACHE_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _url_to_filename(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    ext = "png"
    lower = url.lower().split("?", 1)[0]
    for candidate in (".jpg", ".jpeg", ".webp", ".png"):
        if lower.endswith(candidate):
            ext = candidate.lstrip(".")
            break
    return f"{digest}.{ext}"


def _try_local_input_passthrough(url: str) -> str | None:
    """If `url` is a ComfyUI `/view?...&type=input` URL, return the relative path."""
    parsed = urllib.parse.urlparse(url)
    if not parsed.path.endswith("/view"):
        return None
    qs = urllib.parse.parse_qs(parsed.query)
    if qs.get("type", [""])[0] != "input":
        return None
    filename = qs.get("filename", [""])[0]
    if not filename:
        return None
    subfolder = qs.get("subfolder", [""])[0]
    rel = f"{subfolder}/{filename}" if subfolder else filename
    if not (_get_input_dir() / rel).exists():
        return None
    return rel


def cache_image(url: str) -> str:
    """Download `url` into the input directory and return its relative path.

    Magic-byte sniffing rejects payloads that aren't a supported image
    format (PNG / JPEG / WebP / GIF) so a stray HTML error page can't
    pose as `result.png` and crash a downstream node with a cryptic
    decode error.
    """
    local = _try_local_input_passthrough(url)
    if local is not None:
        return local

    validate_url(url)

    filename = _url_to_filename(url)
    filepath = _cache_dir() / filename
    if filepath.exists():
        return f"{_CACHE_SUBDIR}/{filename}"

    logger.info("Downloading image: %s -> %s", url[:80], filename)
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "comfyui-loovie/0.1")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    if not data:
        raise ValueError("Downloaded image is empty")
    if sniff_image_mime(data) is None:
        raise ValueError("Downloaded payload is not a supported image format")
    with open(filepath, "wb") as f:
        f.write(data)
    return f"{_CACHE_SUBDIR}/{filename}"


def cache_images(urls: list[str]) -> list[str]:
    """Cache a list of URLs and return the corresponding relative paths."""
    return [cache_image(u) for u in urls]
