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
