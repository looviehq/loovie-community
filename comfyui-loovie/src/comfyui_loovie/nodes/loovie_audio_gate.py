"""`LoovieAudioGate` node: choose generated audio, source audio, or silence.

`enabled` mirrors the request's `with_audio` toggle. `keep_original` is the
edit/motion flag: when set and a source AUDIO is wired, the original track is
returned unchanged and the generated track is discarded. Otherwise the
generated AUDIO passes through only when `enabled` is True, so the downstream
CreateVideo / SaveVideo nodes produce a track-less video.
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
                "original_audio": ("AUDIO",),
                "keep_original": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("AUDIO",)
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(
        self,
        enabled: bool,
        audio: Any = None,
        original_audio: Any = None,
        keep_original: bool = False,
    ) -> tuple[Any]:
        if keep_original and original_audio is not None:
            return (original_audio,)
        return (audio if enabled else None,)
