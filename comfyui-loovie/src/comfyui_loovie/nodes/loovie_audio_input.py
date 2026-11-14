"""`LoovieAudioInput` node: download 1-3 reference audio URLs for H3 ref2va.

MiniMax H3's `ref2va` task takes standalone reference audio alongside reference
images/videos: up to 3 clips, 2-15 s each and 15 s combined, WAV or MP3, 15 MB
each. ComfyUI's `MiniMaxH3ReferenceToVideo` consumes them through an autogrow
`ref_audios` map (`ref_audio_1` …), but a graph is static and cannot know how
many clips a request carries, so this adapter mirrors `LoovieImageInput`:

  - `audio_url_1` … `audio_url_3` are the request's URLs (injected by the route
    layer from `reference_audio_urls`),
  - the node downloads and decodes each one into ComfyUI's AUDIO dict
    (`{"waveform": [1, C, L], "sample_rate": int}`),
  - it returns the list plus its count, which `LoovieH3ReferenceToVideo` turns
    into the numbered `ref_audios` entries.

Returning a LIST (a custom connection type) rather than one output per slot
keeps the graph static: the wrapper builds exactly as many `ref_audio_N` entries
as the request carries, the same way it already does for images.

Nothing here enforces the vendor's 2-15 s / 15 MB window; the app sends each
clip already cut to that window (`audioTrimCut.ts`) and the API validates the
declared lengths before the lease is issued. The node's job is to hand ComfyUI
the audio the request actually asked for.
"""

from __future__ import annotations

import hashlib
import logging
import urllib.request
from pathlib import Path
from typing import Any

from ..helpers.image_cache import validate_url

logger = logging.getLogger("comfyui_loovie.nodes.audio_input")

_MAX_SLOTS = 3
_CACHE_SUBDIR = "loovie_audio_cache"
_AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus")


def _input_dir() -> Path:
    try:
        import folder_paths
    except ImportError:
        return Path("input")
    return Path(folder_paths.get_input_directory())


def _cache_dir() -> Path:
    path = _input_dir() / _CACHE_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _url_to_filename(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    extension = "wav"
    lower = url.lower().split("?", 1)[0]
    for candidate in _AUDIO_EXTENSIONS:
        if lower.endswith(candidate):
            extension = candidate.lstrip(".")
            break
    return f"{digest}.{extension}"


def _download(url: str) -> Path:
    """Fetch `url` into the input cache, reusing a previous copy when present."""
    validate_url(url)
    filepath = _cache_dir() / _url_to_filename(url)
    if filepath.exists() and filepath.stat().st_size > 0:
        return filepath
    logger.info("Downloading reference audio: %s -> %s", url[:80], filepath.name)
    request = urllib.request.Request(url, method="GET")
    request.add_header("User-Agent", "comfyui-loovie/0.1")
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if not data:
        raise ValueError("Downloaded reference audio is empty")
    with open(filepath, "wb") as handle:
        handle.write(data)
    return filepath


def _load_audio(path: Path) -> dict[str, Any]:
    """Decode a file into ComfyUI's AUDIO dict (PyAV, the same loader core uses).

    Imported here rather than at module scope so the package stays importable
    without ComfyUI installed (tests, the capabilities manifest, the CLI).
    """
    from comfy_extras.nodes_audio import load as load_audio_file

    waveform, sample_rate = load_audio_file(str(path))
    return {"waveform": waveform.unsqueeze(0), "sample_rate": int(sample_rate)}


class LoovieAudioInput:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        optional: dict[str, Any] = {}
        for slot in range(1, _MAX_SLOTS + 1):
            optional[f"audio_url_{slot}"] = ("STRING", {"default": ""})
        return {"optional": optional}

    RETURN_TYPES = ("LOOVIE_AUDIO_LIST", "INT")
    RETURN_NAMES = ("AUDIOS", "AUDIO_COUNT")
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(
        self,
        audio_url_1: str = "",
        audio_url_2: str = "",
        audio_url_3: str = "",
    ) -> tuple[list[dict[str, Any]], int]:
        urls = [
            str(url).strip() for url in (audio_url_1, audio_url_2, audio_url_3) if str(url).strip()
        ][:_MAX_SLOTS]
        audios = [_load_audio(_download(url)) for url in urls]
        return audios, len(audios)


__all__ = ["LoovieAudioInput"]
