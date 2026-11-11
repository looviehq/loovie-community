"""`LoovieVideoEdit` node: load a source clip and slice it for LTX editing.

LTX 2.5's advanced operations all condition on a source video:

* **edit** uses the whole clip as a guide (full-scene restyle),
* **retake** guides the frames before and after a time window, leaving the
  window itself to be regenerated,
* **extend** guides the context at the head or tail and generates the new
  frames beyond it,
* **motion** uses the reference clip as the motion guide.

`LTXVAddGuide` wants guide batches of ``8n + 1`` frames and a frame index that
is a multiple of 8, so this node exposes slices that are already model-legal,
plus the frame indices the graph should wire into the guide nodes. The arithmetic
is deliberately kept here (instead of in each workflow) so every graph shares
the same rounding behaviour.
"""

from __future__ import annotations

import logging
from pathlib import Path

import torch

from .loovie_video_input import (
    _decode_frames,
    _download,
    _extract_audio,
    _silent_audio,
)

logger = logging.getLogger("comfyui_loovie.nodes.video_edit")

_FRAME_STEP = 8


def _snap_length(value: int) -> int:
    """Largest ``8n + 1`` frame count at or below ``value`` (at least 1)."""

    if value <= 1:
        return 1
    return (value - 1) // _FRAME_STEP * _FRAME_STEP + 1


def _snap_index(value: int) -> int:
    """Largest multiple of 8 at or below ``value`` (never negative)."""

    return max(0, value // _FRAME_STEP * _FRAME_STEP)


def _guide_slice(frames: torch.Tensor, begin: int, length: int) -> torch.Tensor:
    """A model-legal guide slice, clamped to the clip."""

    if frames.numel() == 0:
        return frames
    begin = max(0, min(begin, frames.shape[0] - 1))
    end = max(begin + 1, min(begin + length, frames.shape[0]))
    return frames[begin:end]


def _trim_audio(audio: dict[str, object], seconds: float) -> dict[str, object]:
    """Trim or zero-pad an AUDIO dict to exactly `seconds`."""

    if not audio or seconds <= 0:
        return audio
    waveform = audio.get("waveform")
    raw_rate = audio.get("sample_rate")
    try:
        sample_rate = int(float(str(raw_rate))) if raw_rate is not None else 44100
    except (TypeError, ValueError):
        sample_rate = 44100
    if not isinstance(waveform, torch.Tensor) or waveform.ndim != 3:
        return audio
    target = max(1, round(seconds * sample_rate))
    current = waveform.shape[-1]
    if current > target:
        waveform = waveform[..., :target]
    elif current < target:
        pad = torch.zeros(
            (*waveform.shape[:-1], target - current),
            dtype=waveform.dtype,
            device=waveform.device,
        )
        waveform = torch.cat([waveform, pad], dim=-1)
    return {**audio, "waveform": waveform, "sample_rate": sample_rate}


class LoovieVideoEdit:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "video_url": ("STRING", {"default": "", "multiline": False}),
                "max_frames": ("INT", {"default": 505, "min": 1, "max": 2048}),
            },
            "optional": {
                "start_seconds": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 600.0}),
                "duration_seconds": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 600.0}),
                "context_seconds": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 20.0}),
                "extend_side": (["end", "start"], {"default": "end"}),
                "mode": (["edit", "retake", "extend", "motion"], {"default": "edit"}),
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 120.0}),
                "force_resize_short_side": (
                    "INT",
                    {"default": 0, "min": 0, "max": 4096},
                ),
            },
        }

    RETURN_TYPES = (
        "IMAGE",
        "IMAGE",
        "IMAGE",
        "IMAGE",
        "AUDIO",
        "INT",
        "INT",
        "INT",
        "INT",
        "INT",
        "INT",
        "INT",
        "FLOAT",
    )
    RETURN_NAMES = (
        "SOURCE",
        "BEFORE",
        "AFTER",
        "CONTEXT",
        "AUDIO",
        "NUM_FRAMES",
        "TOTAL_FRAMES",
        "BEFORE_INDEX",
        "AFTER_INDEX",
        "EXTEND_INDEX",
        "WIDTH",
        "HEIGHT",
        "FPS",
    )
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(
        self,
        video_url: str,
        max_frames: int = 505,
        start_seconds: float = 0.0,
        duration_seconds: float = 0.0,
        context_seconds: float = 4.0,
        extend_side: str = "end",
        mode: str = "edit",
        fps: float = 24.0,
        force_resize_short_side: int = 0,
    ) -> tuple[object, ...]:
        url = (video_url or "").strip()
        if not url:
            empty = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            silent = _silent_audio(1, 24.0)
            return (
                empty,
                empty,
                empty,
                empty,
                silent,
                1,
                1,
                0,
                0,
                0,
                64,
                64,
                24.0,
            )

        path: Path = _download(url)
        frames_np, source_fps = _decode_frames(path, max_frames)
        effective_fps = float(fps or source_fps or 24.0)

        # Edit and motion render a clip of the requested length; the source
        # may be longer. Retake/extend need the whole source, so only trim for
        # edit and motion.
        if str(mode).lower() in ("edit", "motion") and float(duration_seconds) > 0:
            requested = _snap_length(round(float(duration_seconds) * effective_fps) + 1)
            frames_np = frames_np[:requested]

        # LTX wants 8n+1 frames. Drop trailing frames rather than pad, so the
        # guide always describes real footage.
        num_frames = _snap_length(frames_np.shape[0])
        frames_np = frames_np[:num_frames]
        frames = torch.from_numpy(frames_np).float().div(255.0)

        if force_resize_short_side and force_resize_short_side > 0:
            short = min(frames.shape[1], frames.shape[2])
            if short != force_resize_short_side:
                scale = force_resize_short_side / short
                new_h = max(32, int(round(frames.shape[1] * scale / 32) * 32))
                new_w = max(32, int(round(frames.shape[2] * scale / 32) * 32))
                permuted = frames.permute(0, 3, 1, 2)
                resized = torch.nn.functional.interpolate(
                    permuted, size=(new_h, new_w), mode="bilinear", antialias=True
                )
                frames = resized.permute(0, 2, 3, 1)

        start = _snap_index(round(float(start_seconds) * effective_fps))
        duration = round(float(duration_seconds) * effective_fps)
        extension = _snap_index(duration) if duration > 0 else 0
        end = num_frames - 1 if duration <= 0 else min(num_frames - 1, start + extension)
        end = _snap_index(end)

        # BEFORE ends at `start` (inclusive) and is centred on the boundary so
        # it stays adjacent to the regenerated window.
        before_len = _snap_length(min(start + 1, 25))
        before = _guide_slice(frames, max(0, start - before_len + 1), before_len)
        # AFTER starts at `end` so the regenerated window is [start+1, end-1].
        after_len = _snap_length(min(num_frames - end, 25))
        after = _guide_slice(frames, end, after_len)

        context = _snap_length(round(float(context_seconds) * effective_fps))
        if str(extend_side).lower() == "start":
            context_frames = _guide_slice(frames, 0, context)
            total_frames = _snap_length(context_frames.shape[0] + extension)
            extend_index = _snap_index(max(0, total_frames - context_frames.shape[0]))
        else:
            context_frames = _guide_slice(frames, max(0, num_frames - context), context)
            total_frames = _snap_length(context_frames.shape[0] + extension)
            extend_index = 0

        audio = _extract_audio(path) or _silent_audio(num_frames, effective_fps)
        audio = _trim_audio(audio, num_frames / effective_fps)
        height, width = int(frames.shape[1]), int(frames.shape[2])

        logger.info(
            "Video edit source loaded: frames=%d start=%d end=%d context=%d total=%d",
            num_frames,
            start,
            end,
            context_frames.shape[0],
            total_frames,
        )
        return (
            frames,
            before,
            after,
            context_frames,
            audio,
            num_frames,
            total_frames,
            start,
            end,
            extend_index,
            width,
            height,
            effective_fps,
        )


__all__ = ["LoovieVideoEdit"]
