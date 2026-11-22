"""Loovie Music Input node tests.

The route layer injects the music request body into this node and the YuE2
graph reads its outputs. These tests pin the output contract so a graph
wired against it (the `mode`/`abc_enabled` split in particular) can never
drift when the body handling changes.
"""

from __future__ import annotations

import json
from pathlib import Path

from comfyui_loovie.nodes.loovie_music_input import LoovieMusicInput

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_music_input_declares_six_outputs() -> None:
    node = LoovieMusicInput()
    assert LoovieMusicInput.RETURN_NAMES == (
        "prompt",
        "lyrics",
        "abc_enabled",
        "seed",
        "duration",
        "mode",
    )
    assert node.build("style", "lyrics", False, 7, 120.0) == (
        "style",
        "lyrics",
        True,
        7,
        120.0,
        "full",
    )


def test_music_input_instrumental_disables_abc_and_sets_mode_off() -> None:
    """Instrumental renders skip the ABC plan and generate without a plan."""
    _, _, abc_enabled, _, _, mode = LoovieMusicInput().build("lofi beat", "", True, -1, 60.0)
    assert abc_enabled is False
    assert mode == "off"


def test_music_input_instrumental_folds_the_upstream_style_directive() -> None:
    """YuE2 is a song model: the style itself has to forbid vocals."""
    style, _, _, _, _, _ = LoovieMusicInput().build("warm lofi piano, 80 bpm", "", True, -1, 60.0)
    assert style.startswith("Instrumental, warm lofi piano, 80 bpm")
    for condition in ("no vocals", "no singing", "no choir", "no spoken words"):
        assert condition in style


def test_music_input_instrumental_never_sings_supplied_lyrics() -> None:
    """The flag wins over a lyric sheet: nothing is sung on an instrumental."""
    _, lyrics, _, _, _, _ = LoovieMusicInput().build(
        "lofi beat", "[Verse]\nsome words", True, -1, 60.0
    )
    assert lyrics == ""


def test_music_input_instrumental_style_is_idempotent() -> None:
    """Re-running the directive never doubles it up."""
    first, _, _, _, _, _ = LoovieMusicInput().build("lofi beat", "", True, -1, 60.0)
    second, _, _, _, _, _ = LoovieMusicInput().build(first, "", True, -1, 60.0)
    assert first == second
    assert second.lower().count("no vocals") == 1


def test_music_input_instrumental_with_empty_style_still_gets_a_style() -> None:
    style, _, _, _, _, _ = LoovieMusicInput().build("", "", True, -1, 60.0)
    assert style.startswith("Instrumental, expressive instrumental music")


def test_music_input_leaves_a_vocal_request_untouched() -> None:
    """Non-instrumental requests pass style and lyrics through verbatim."""
    style, lyrics, abc_enabled, _, _, mode = LoovieMusicInput().build(
        "warm lofi piano", "[Verse]\nwords", False, -1, 60.0
    )
    assert style == "warm lofi piano"
    assert lyrics == "[Verse]\nwords"
    assert abc_enabled is True
    assert mode == "full"


def test_music_input_casts_seed_and_duration() -> None:
    _, _, _, seed, duration, _ = LoovieMusicInput().build("style", "", False, 3, 90)
    assert seed == 3
    assert isinstance(seed, int)
    assert duration == 90.0
    assert isinstance(duration, float)


def test_registered_workflow_injects_into_music_input_node() -> None:
    """The shipped YuE2 graph carries a `LoovieMusicInput` node to inject into."""
    workflow = json.loads((REPO_ROOT / "workflows" / "yue2_t2m_fast.json").read_text())
    classes = {node["class_type"] for node in workflow.values()}
    assert "LoovieMusicInput" in classes
