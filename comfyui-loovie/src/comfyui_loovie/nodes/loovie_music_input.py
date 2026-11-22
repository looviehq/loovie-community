"""Loovie Music Input node.

The route layer scans the workflow JSON by `class_type` and injects the
music request fields (style prompt, lyrics, instrumental flag, seed,
duration, mode) into this node before submitting the graph to ComfyUI, the
same way `LoovieTextInput` carries the image/video prompt.

Outputs (consumed by the YuE2 graph):
  0 `prompt`       STRING  — music style description. For an instrumental the
                             upstream style directive is folded in (see
                             `_instrumental_style`), because YuE2 is a song
                             model and an empty lyric sheet alone does not stop
                             it singing.
  1 `lyrics`       STRING  — lyric sheet with section tags, EMPTY for an
                             instrumental: nothing is ever sung there, even when
                             a caller sends both a lyric sheet and the flag.
  2 `abc_enabled`  BOOLEAN — False for instrumental (skip the ABC plan).
  3 `seed`         INT.
  4 `duration`     FLOAT   — target seconds (YuE2 treats it as a cap: sampling
                             stops at the end token, so a render can be shorter).
  5 `mode`         STRING  — "full" / "off", INFORMATIONAL ONLY. Do not wire it
                             into a YuE2 node's `mode` input: those combos only
                             accept "full" and "melody", so "off" would fail
                             ComfyUI's queue-time validation. `YuE2GenerateMusic`
                             already forces off mode by itself when `abc` is
                             empty, which is exactly the instrumental path.

Instrumental is best effort on the YuE2 base checkpoint: the directive below is
the recipe upstream publishes for it (multimodal-art-projection/YuE,
`skills/yue2-music/instrumental`), and upstream's own summary records
`absence_of_vocals_checked: false`. A render that must be reliably wordless
needs the instrumental LoRA (Mothersuperior's adapter) loaded in front of the
model, which this reference workflow does not ship.
"""

from __future__ import annotations

import re
from typing import Any

# Upstream's instrumental style directive. The base model is a song model, so
# the style has to say what the render must NOT contain; "instrumental" in the
# style alone is not enough, and neither is an empty lyric sheet.
_INSTRUMENTAL_PREFIX = "Instrumental, "
_INSTRUMENTAL_CONDITIONS = ("no vocals", "no singing", "no choir", "no spoken words")
_INSTRUMENTAL_FALLBACK_STYLE = "expressive instrumental music"


def _instrumental_style(style: str) -> str:
    """Fold the upstream instrumental directive into a style prompt.

    Mirrors `skills/yue2-music/instrumental/scripts/instrumental.py` in
    multimodal-art-projection/YuE: prefix `Instrumental` when the style does not
    already start with it, then append each missing no-vocal condition.
    """

    text = style.strip().rstrip(".,") or _INSTRUMENTAL_FALLBACK_STYLE
    if not re.match(r"^instrumental\b", text, re.I):
        text = _INSTRUMENTAL_PREFIX + text
    lowered = text.lower()
    for condition in _INSTRUMENTAL_CONDITIONS:
        if condition not in lowered:
            text += ", " + condition
            lowered = text.lower()
    return text


class LoovieMusicInput:
    """Carries a music request from the HTTP body into the YuE2 graph."""

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "lyrics": ("STRING", {"default": "", "multiline": True}),
                "instrumental": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": -1}),
                "duration": ("FLOAT", {"default": 120.0, "min": 1.0}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("prompt", "lyrics", "abc_enabled", "seed", "duration", "mode")
    FUNCTION = "build"
    CATEGORY = "loovie"

    def build(
        self,
        prompt: str,
        lyrics: str,
        instrumental: bool,
        seed: int,
        duration: float,
    ) -> tuple[str, str, bool, int, float, str]:
        return (
            _instrumental_style(prompt) if instrumental else prompt,
            "" if instrumental else lyrics,
            not instrumental,
            int(seed),
            float(duration),
            "off" if instrumental else "full",
        )


__all__ = ["LoovieMusicInput"]
