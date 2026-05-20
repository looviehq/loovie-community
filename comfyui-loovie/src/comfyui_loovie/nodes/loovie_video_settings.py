"""`LoovieVideoSettings` node: emit WIDTH/HEIGHT/NUM_FRAMES/FPS/audio/seed.

Audio is opt-in: when `with_audio` is False the audio frame budget is
zeroed and the AUDIO_ENABLED switch flips so the graph bypasses the
audio decode entirely.
"""

from __future__ import annotations

import random


class LoovieVideoSettings:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "width": ("INT", {"default": 960, "min": 64, "max": 4096, "step": 32}),
                "height": ("INT", {"default": 544, "min": 64, "max": 4096, "step": 32}),
                "num_frames": ("INT", {"default": 121, "min": 1, "max": 1000}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120}),
                "audio_frames": ("INT", {"default": 97, "min": 0, "max": 1000}),
                "audio_fps": ("INT", {"default": 25, "min": 1, "max": 120}),
                "with_audio": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": -1}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "INT", "INT", "BOOLEAN", "INT")
    RETURN_NAMES = (
        "WIDTH",
        "HEIGHT",
        "NUM_FRAMES",
        "FPS",
        "AUDIO_FRAMES",
        "AUDIO_FPS",
        "AUDIO_ENABLED",
        "SEED",
    )
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(
        self,
        width: int,
        height: int,
        num_frames: int,
        fps: int,
        audio_frames: int,
        audio_fps: int,
        with_audio: bool,
        seed: int,
    ) -> tuple[int, int, int, int, int, int, bool, int]:
        if seed < 0:
            seed = random.randint(0, 2**31 - 1)
        effective_audio_frames = audio_frames if with_audio else 0
        return (
            width,
            height,
            num_frames,
            fps,
            effective_audio_frames,
            audio_fps,
            bool(with_audio),
            seed,
        )
