"""`LoovieVideoInput` node: download a video URL, decode frames + audio.

Outputs match the shape of ComfyUI's core `LoadVideo` / `GetVideoComponents`
pair: an IMAGE batch `[N, H, W, 3]` in `[0, 1]`, an AUDIO dict with
`{waveform, sample_rate}`, the source FPS, and the per-frame counts. If
the source has no audio track, a silent stub at the source FPS is
returned so downstream audio-aware nodes never NaN on a missing track.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import urllib.request
from pathlib import Path

import numpy as np
import torch

from ..helpers.image_cache import validate_url

logger = logging.getLogger("comfyui_loovie.nodes.video_input")

_CACHE_SUBDIR = "loovie_video_cache"
_DEFAULT_SAMPLE_RATE = 44100


def _input_dir() -> Path:
    try:
        import folder_paths  # type: ignore[import-not-found]
    except ImportError:
        return Path("input")
    return Path(folder_paths.get_input_directory())


def _cache_dir() -> Path:
    path = _input_dir() / _CACHE_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _url_to_filename(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    ext = "mp4"
    lower = url.lower().split("?", 1)[0]
    for candidate in (".mp4", ".mov", ".webm", ".mkv", ".avi"):
        if lower.endswith(candidate):
            ext = candidate.lstrip(".")
            break
    return f"{digest}.{ext}"


def _download(url: str) -> Path:
    validate_url(url)
    filename = _url_to_filename(url)
    filepath = _cache_dir() / filename
    if filepath.exists() and filepath.stat().st_size > 0:
        return filepath
    logger.info("Downloading video: %s -> %s", url[:80], filename)
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "comfyui-loovie/0.1")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    if not data:
        raise ValueError("Downloaded video is empty")
    with open(filepath, "wb") as f:
        f.write(data)
    return filepath


def _decode_frames(path: Path, max_frames: int) -> tuple[np.ndarray, float]:
    import imageio.v3 as iio

    meta = iio.immeta(str(path), exclude_applied=False)
    fps = float(meta.get("fps") or 24.0)
    frames: list[np.ndarray] = []
    for i, frame in enumerate(iio.imiter(str(path))):
        if max_frames > 0 and i >= max_frames:
            break
        if frame.ndim == 2:
            frame = np.stack([frame] * 3, axis=-1)
        elif frame.shape[-1] == 4:
            frame = frame[..., :3]
        frames.append(frame)
    if not frames:
        raise ValueError(f"No frames decoded from {path}")
    return np.stack(frames, axis=0).astype(np.uint8), fps


def _extract_audio(path: Path) -> dict[str, object] | None:
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-vn", "-f", "f32le", "-acodec", "pcm_f32le",
        "-ar", str(_DEFAULT_SAMPLE_RATE), "-ac", "2", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg audio extract failed (%s); using silent stub", exc)
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    raw = np.frombuffer(result.stdout, dtype=np.float32)
    if raw.size == 0:
        return None
    waveform = raw.reshape(-1, 2).T
    return {
        "waveform": torch.from_numpy(waveform).unsqueeze(0).contiguous(),
        "sample_rate": _DEFAULT_SAMPLE_RATE,
    }


def _silent_audio(num_frames: int, fps: float) -> dict[str, object]:
    duration = max(num_frames / max(fps, 1.0), 0.1)
    samples = int(duration * _DEFAULT_SAMPLE_RATE)
    return {
        "waveform": torch.zeros((1, 2, samples), dtype=torch.float32),
        "sample_rate": _DEFAULT_SAMPLE_RATE,
    }


class LoovieVideoInput:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "video_url": ("STRING", {"default": "", "multiline": False}),
                "max_frames": ("INT", {"default": 121, "min": 1, "max": 2048}),
            },
            "optional": {
                "force_resize_short_side": (
                    "INT",
                    {"default": 0, "min": 0, "max": 4096},
                ),
            },
        }

    RETURN_TYPES = (
        "IMAGE", "AUDIO", "INT", "INT", "INT", "INT", "FLOAT", "IMAGE", "IMAGE",
    )
    RETURN_NAMES = (
        "FRAMES",
        "AUDIO",
        "FRAME_COUNT",
        "WIDTH",
        "HEIGHT",
        "FPS_INT",
        "FPS",
        "FIRST_FRAME",
        "LAST_FRAME",
    )
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(
        self,
        video_url: str,
        max_frames: int = 121,
        force_resize_short_side: int = 0,
    ) -> tuple[object, ...]:
        url = (video_url or "").strip()
        if not url:
            empty = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            silent = _silent_audio(1, 24.0)
            return (empty, silent, 0, 64, 64, 24, 24.0, empty, empty)

        path = _download(url)
        frames_np, fps = _decode_frames(path, max_frames)
        n, h, w, _ = frames_np.shape
        frames_t = torch.from_numpy(frames_np).float().div(255.0)

        if force_resize_short_side and force_resize_short_side > 0:
            short = min(h, w)
            if short != force_resize_short_side:
                scale = force_resize_short_side / short
                new_h = int(round(h * scale / 32) * 32)
                new_w = int(round(w * scale / 32) * 32)
                permuted = frames_t.permute(0, 3, 1, 2)
                resized = torch.nn.functional.interpolate(
                    permuted, size=(new_h, new_w), mode="bilinear", antialias=True
                )
                frames_t = resized.permute(0, 2, 3, 1)
                h, w = new_h, new_w

        audio = _extract_audio(path) or _silent_audio(n, fps)
        first = frames_t[:1]
        last = frames_t[-1:]
        return (frames_t, audio, n, w, h, round(fps), float(fps), first, last)
