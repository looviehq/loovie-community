"""Reference VIDEO clips on MiniMax H3 ref2v, through every seam that carries them.

  request `reference_video_urls` (mode ref2v)
    -> `_inject_inputs` (`LoovieReferenceVideoInput.video_url_N`)
    -> `LoovieReferenceVideoInput` (download, decode, resample to 24 fps)
    -> `LoovieH3ReferenceToVideo` (`ref_videos.ref_video_N`)
    -> ComfyUI's `MiniMaxH3ReferenceToVideo`.

The shipped workflow JSON is checked too, so unwiring the node while the
manifest still advertises three fails here.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from comfyui_loovie.capabilities import build_capabilities_manifest
from comfyui_loovie.models import available_models
from comfyui_loovie.nodes.loovie_h3_reference import LoovieH3ReferenceToVideo
from comfyui_loovie.nodes.loovie_reference_video_input import (
    LoovieReferenceVideoInput,
    _resample_to_target_fps,
)
from comfyui_loovie.server.routes import _inject_inputs

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / "workflows"

H3_REF2V_WORKFLOWS = [
    "pika-flex-ref2v-official",
    "pika-flex-ref2v-turbo",
    "hyperflow-h3-flash-ref2v-fast",
    "hyperflow-h3-flash-ref2v-flash",
    "hyperflow-h3-flash-ref2v-hq",
]

ALL_WORKFLOWS = [
    "ltx25-t2v-fast",
    "ltx25-ref2v-fast",
    *H3_REF2V_WORKFLOWS,
    "pika-flex-t2v-official",
    "hyperflow-h3-flash-t2v-flash",
]


def test_h3_models_advertise_three_reference_videos() -> None:
    models = {m.id: m for m in available_models({}, ALL_WORKFLOWS)}
    assert models["pika-flex"].max_reference_videos == 3
    assert models["hyperflow-h3-flash"].max_reference_videos == 3
    assert models["ltx-2.5"].max_reference_videos == 0


def test_manifest_reports_the_video_budget_to_the_app() -> None:
    manifest = build_capabilities_manifest(ALL_WORKFLOWS, version="test")
    videos = {m["id"]: m for m in manifest["models"]["ss_videos"]}
    assert videos["pika-flex"]["maxReferenceVideos"] == 3
    assert videos["hyperflow-h3-flash"]["maxReferenceVideos"] == 3
    assert videos["ltx-2.5"]["maxReferenceVideos"] == 0


def test_injection_hands_the_urls_to_the_video_node_in_ref2v() -> None:
    workflow: dict[str, Any] = {"14": {"class_type": "LoovieReferenceVideoInput", "inputs": {}}}
    _inject_inputs(
        workflow,
        {
            "mode": "ref2v",
            "reference_video_urls": ["https://example.com/a.mp4", "https://example.com/b.mp4"],
        },
    )
    inputs = workflow["14"]["inputs"]
    assert inputs["video_url_1"] == "https://example.com/a.mp4"
    assert inputs["video_url_2"] == "https://example.com/b.mp4"
    assert "video_url_3" not in inputs


def test_injection_ignores_the_video_node_outside_ref2v() -> None:
    workflow: dict[str, Any] = {"14": {"class_type": "LoovieReferenceVideoInput", "inputs": {}}}
    _inject_inputs(
        workflow,
        {"mode": "motion", "reference_video_urls": ["https://example.com/a.mp4"]},
    )
    assert "video_url_1" not in workflow["14"]["inputs"]


def test_video_input_node_contract() -> None:
    assert LoovieReferenceVideoInput.RETURN_NAMES == ("VIDEOS", "VIDEO_COUNT")
    assert set(LoovieReferenceVideoInput.INPUT_TYPES()["optional"]) == {
        "video_url_1",
        "video_url_2",
        "video_url_3",
    }
    assert LoovieReferenceVideoInput().process() == ([], 0)


@pytest.mark.skipif(
    not hasattr(np, "arange"), reason="numpy is stubbed in this environment"
)
def test_resample_converts_to_24_fps_and_caps_at_15_seconds() -> None:
    frames = np.arange(60).reshape(60, 1, 1, 1)
    # 2 s at 30 fps becomes 48 frames at 24 fps.
    assert _resample_to_target_fps(frames, 30.0).shape[0] == 48
    # Already 24 fps: untouched.
    assert _resample_to_target_fps(frames, 24.0).shape[0] == 60
    # 20 s at 24 fps is capped at 15 s.
    long = np.zeros((480, 1, 1, 1))
    assert _resample_to_target_fps(long, 24.0).shape[0] == 360


class _FakeImages:
    shape = (1, 4, 4, 3)

    def __getitem__(self, item: Any) -> Any:
        return [item]


def _fake_h3_module(captured: dict[str, Any]) -> types.ModuleType:
    class FakeReferenceToVideo:
        @classmethod
        def execute(cls, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return types.SimpleNamespace(result=("cond", "latent"))

    module = types.ModuleType("comfy_extras.nodes_minimax_h3")
    module.MiniMaxH3ReferenceToVideo = FakeReferenceToVideo  # type: ignore[attr-defined]
    return module


def _build(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    monkeypatch.setitem(sys.modules, "comfy_extras", types.ModuleType("comfy_extras"))
    monkeypatch.setitem(sys.modules, "comfy_extras.nodes_minimax_h3", _fake_h3_module(captured))
    LoovieH3ReferenceToVideo().build(
        clip=None,
        vae=None,
        audio_vae=None,
        prompt="p",
        width=768,
        height=768,
        length=124,
        images=_FakeImages(),
        image_count=1,
        **kwargs,
    )
    return captured


def test_wrapper_builds_numbered_ref_videos(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _build(monkeypatch, videos=["a", "b"], video_count=2)
    assert captured["ref_videos"] == {"ref_video_1": "a", "ref_video_2": "b"}


def test_wrapper_caps_ref_videos_at_three(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _build(monkeypatch, videos=list("abcde"), video_count=5)
    assert len(captured["ref_videos"]) == 3


def test_wrapper_without_videos_passes_an_empty_map(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _build(monkeypatch)["ref_videos"] == {}


@pytest.mark.parametrize("workflow_name", H3_REF2V_WORKFLOWS)
def test_shipped_ref2v_workflows_wire_the_video_input(workflow_name: str) -> None:
    workflow = json.loads((WORKFLOWS_DIR / f"{workflow_name}.json").read_text())

    video_node = workflow.get("14")
    assert video_node is not None, f"{workflow_name} has no LoovieReferenceVideoInput node"
    assert video_node["class_type"] == "LoovieReferenceVideoInput"

    reference_node = next(
        node for node in workflow.values() if node.get("class_type") == "LoovieH3ReferenceToVideo"
    )
    assert reference_node["inputs"]["videos"] == ["14", 0]
    assert reference_node["inputs"]["video_count"] == ["14", 1]
