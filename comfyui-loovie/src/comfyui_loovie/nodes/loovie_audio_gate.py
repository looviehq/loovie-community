"""`LoovieAudioGate` node: pass AUDIO through only when enabled.

When `enabled` is False the node emits None, so the downstream
CreateVideo / SaveVideo nodes produce a track-less video. When True the
AUDIO input is passed straight through.
"""

from __future__ import annotations

from typing import Any


class LoovieAudioGate:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("AUDIO",)
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(self, enabled: bool, audio: Any = None) -> tuple[Any]:
        return (audio if enabled else None,)
