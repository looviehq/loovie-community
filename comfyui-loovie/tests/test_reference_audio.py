"""Reference AUDIO on MiniMax H3 ref2va, through every seam that carries it.

H3 accepts up to three standalone reference audio clips (2-15 s each, 15 s
combined) alongside the reference images, and the vendor requires a picture or a
clip beside it. The community server used to advertise `maxReferenceAudios: 0`
on every video model because nothing consumed the audio; these tests pin the
whole path that now does:

  request `reference_audio_urls`
    -> `_inject_inputs` (`LoovieAudioInput.audio_url_N`)
    -> `LoovieAudioInput` (download + decode to ComfyUI AUDIO)
    -> `LoovieH3ReferenceToVideo` (`ref_audios.ref_audio_N`)
    -> ComfyUI's `MiniMaxH3ReferenceToVideo`.

The last two links are also verified against the SHIPPED workflow JSON, so an
edit that unwires the node while the manifest still advertises three fails here
rather than at a user's first request.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from comfyui_loovie.capabilities import build_capabilities_manifest
from comfyui_loovie.models import (
    available_models,
    find_variant,
    validate_request_values,
)
from comfyui_loovie.nodes.loovie_audio_input import LoovieAudioInput
from comfyui_loovie.nodes.loovie_h3_reference import LoovieH3ReferenceToVideo
from comfyui_loovie.server.routes import _inject_inputs

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / "workflows"

H3_REF2V_WORKFLOWS = [
    "pika-flex-ref2v-official",
    "pika-flex-ref2v-turbo",
    "hyperflow-h3-flash-ref2v-fast",
    "hyperflow-h3-flash-ref2v-flash",
    "hyperflow-h3-flash-ref2v-hq",
]

ALL_WORKFLOWS = [
    "flux-2-klein",
    "ltx23-t2v-fast",
    "ltx25-t2v-fast",
    "ltx25-ref2v-fast",
    *H3_REF2V_WORKFLOWS,
    "pika-flex-t2v-official",
    "hyperflow-h3-flash-t2v-flash",
]


def _models():
    return available_models({}, ALL_WORKFLOWS)


def _video(id_: str):
    return next(m for m in _models() if m.id == id_)


def test_h3_models_advertise_three_reference_audio_clips() -> None:
    """The adapter now consumes audio, so the capability may be advertised."""
    pika = _video("pika-flex")
    hyperflow = _video("hyperflow-h3-flash")

    assert pika.max_reference_audios == 3
    assert hyperflow.max_reference_audios == 3


def test_manifest_reports_the_audio_budget_to_the_app() -> None:
    manifest = build_capabilities_manifest(ALL_WORKFLOWS, version="test")
    videos = {m["id"]: m for m in manifest["models"]["ss_videos"]}

    assert videos["pika-flex"]["maxReferenceAudios"] == 3
    assert videos["hyperflow-h3-flash"]["maxReferenceAudios"] == 3
    # LTX's ref2v graph has no audio-conditioning input, so it stays 0.
    assert videos["ltx-2.5"]["maxReferenceAudios"] == 0


def test_audio_needs_a_picture_or_clip() -> None:
    """MiniMax: audio "cannot be used alone"; audio-only ref2v is a 400."""
    pika = _video("pika-flex")
    official = find_variant(pika, "official")

    assert (
        validate_request_values(
            pika,
            official,
            mode="ref2v",
            resolution="768p",
            duration=8,
            reference_audio_count=1,
        )
        == "REFERENCE_AUDIO_UNSUPPORTED"
    )


def test_audio_alongside_an_image_is_accepted() -> None:
    pika = _video("pika-flex")
    official = find_variant(pika, "official")

    assert (
        validate_request_values(
            pika,
            official,
            mode="ref2v",
            resolution="768p",
            duration=8,
            reference_count=1,
            reference_audio_count=1,
        )
        is None
    )


def test_audio_alongside_a_reference_video_is_accepted() -> None:
    # The shipped graphs do not consume reference clips yet, so model one that
    # advertises them: the rule under test is audio's, not the clip budget's.
    pika = dataclasses.replace(_video("pika-flex"), max_reference_videos=3)
    official = find_variant(pika, "official")

    assert (
        validate_request_values(
            pika,
            official,
            mode="ref2v",
            resolution="768p",
            duration=8,
            reference_count=0,
            reference_video_count=1,
            reference_audio_count=1,
        )
        is None
    )


def test_over_budget_audio_is_rejected() -> None:
    pika = _video("pika-flex")
    official = find_variant(pika, "official")

    assert (
        validate_request_values(
            pika,
            official,
            mode="ref2v",
            resolution="768p",
            duration=8,
            reference_count=1,
            reference_audio_count=4,
        )
        == "REFERENCE_AUDIO_UNSUPPORTED"
    )


def test_reference_audio_outside_ref2v_is_rejected() -> None:
    pika = _video("pika-flex")
    official = find_variant(pika, "official")

    assert (
        validate_request_values(
            pika,
            official,
            mode="t2v",
            resolution="768p",
            duration=8,
            reference_audio_count=1,
        )
        == "REFERENCE_AUDIO_UNSUPPORTED"
    )


def test_model_without_an_audio_conditioning_graph_rejects_audio() -> None:
    ltx = _video("ltx-2.5")
    fast = find_variant(ltx, "fast")

    assert (
        validate_request_values(
            ltx,
            fast,
            mode="ref2v",
            resolution="720p",
            duration=6,
            reference_count=1,
            reference_audio_count=1,
        )
        == "REFERENCE_AUDIO_UNSUPPORTED"
    )


def test_injection_hands_the_urls_to_the_audio_node() -> None:
    workflow: dict[str, Any] = {"13": {"class_type": "LoovieAudioInput", "inputs": {}}}

    _inject_inputs(
        workflow,
        {
            "reference_audio_urls": [
                "https://example.com/a.wav",
                "https://example.com/b.mp3",
            ]
        },
    )

    inputs = workflow["13"]["inputs"]
    assert inputs["audio_url_1"] == "https://example.com/a.wav"
    assert inputs["audio_url_2"] == "https://example.com/b.mp3"
    # Three slots maximum; the validator refuses a fourth before this point.
    assert "audio_url_3" not in inputs


def test_audio_input_node_contract() -> None:
    assert LoovieAudioInput.RETURN_NAMES == ("AUDIOS", "AUDIO_COUNT")
    assert set(LoovieAudioInput.INPUT_TYPES()["optional"]) == {
        "audio_url_1",
        "audio_url_2",
        "audio_url_3",
    }
    # No URLs is a valid request (a text/image-only ref2v).
    assert LoovieAudioInput().process() == ([], 0)


class _FakeImages:
    """Just enough of a ComfyUI IMAGE batch for the wrapper's slicing."""

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


def test_wrapper_builds_numbered_ref_audios(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setitem(sys.modules, "comfy_extras", types.ModuleType("comfy_extras"))
    monkeypatch.setitem(sys.modules, "comfy_extras.nodes_minimax_h3", _fake_h3_module(captured))

    node = LoovieH3ReferenceToVideo()
    audios = [{"waveform": "a"}, {"waveform": "b"}]
    result = node.build(
        clip=None,
        vae=None,
        audio_vae=None,
        prompt="a voice",
        width=768,
        height=768,
        length=124,
        images=_FakeImages(),
        image_count=1,
        audios=audios,
        audio_count=2,
    )

    assert result == ("cond", "latent")
    # 1-based ordinals, matching the `<Audio j>` tags the prompt uses.
    assert captured["ref_audios"] == {
        "ref_audio_1": {"waveform": "a"},
        "ref_audio_2": {"waveform": "b"},
    }


def test_wrapper_caps_ref_audios_at_three(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setitem(sys.modules, "comfy_extras", types.ModuleType("comfy_extras"))
    monkeypatch.setitem(sys.modules, "comfy_extras.nodes_minimax_h3", _fake_h3_module(captured))

    node = LoovieH3ReferenceToVideo()
    node.build(
        clip=None,
        vae=None,
        audio_vae=None,
        prompt="p",
        width=768,
        height=768,
        length=124,
        images=_FakeImages(),
        image_count=0,
        audios=[{"waveform": n} for n in range(5)],
        audio_count=5,
    )

    assert len(captured["ref_audios"]) == 3


@pytest.mark.parametrize("workflow_name", H3_REF2V_WORKFLOWS)
def test_shipped_ref2v_workflows_wire_the_audio_input(workflow_name: str) -> None:
    workflow = json.loads((WORKFLOWS_DIR / f"{workflow_name}.json").read_text())

    audio_node = workflow.get("13")
    assert audio_node is not None, f"{workflow_name} has no LoovieAudioInput node"
    assert audio_node["class_type"] == "LoovieAudioInput"

    reference_node = next(
        node for node in workflow.values() if node.get("class_type") == "LoovieH3ReferenceToVideo"
    )
    # The manifest advertises three slots; the graph must actually take them.
    assert reference_node["inputs"]["audios"] == ["13", 0]
    assert reference_node["inputs"]["audio_count"] == ["13", 1]
