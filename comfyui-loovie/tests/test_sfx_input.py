"""LoovieSfxInput contract: the four values the Stable Audio graph consumes."""

from __future__ import annotations

from comfyui_loovie.nodes.loovie_sfx_input import LoovieSfxInput


def test_sfx_input_forwards_prompt_negative_duration_seed() -> None:
    out = LoovieSfxInput().build(
        prompt="rain on a metal roof",
        negative_prompt="music, speech",
        duration=5.5,
        seed=7,
    )
    assert out == ("rain on a metal roof", "music, speech", 5.5, 7)


def test_duration_is_float_and_seed_int() -> None:
    out = LoovieSfxInput().build("x", "", 3, 4)  # type: ignore[arg-type]
    assert isinstance(out[2], float)
    assert isinstance(out[3], int)
