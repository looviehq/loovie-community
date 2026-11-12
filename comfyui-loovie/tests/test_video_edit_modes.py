"""LTX 2.5 advanced video modes: registry, validation, routing and workflows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from comfyui_loovie.models import (
    CAMERA_MOTIONS,
    available_models,
    find_variant,
    model_descriptor,
    validate_request_values,
)
from comfyui_loovie.nodes.loovie_video_edit import _snap_index, _snap_length
from comfyui_loovie.server.routes import _inject_inputs, _request_mode

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / "comfyui-loovie" / "workflows"

LTX25_WORKFLOWS = [
    "ltx25-t2v-fast",
    "ltx25-i2v-fast",
    "ltx25-fl2v-fast",
    "ltx25-ref2v-fast",
    "ltx25-edit-fast",
    "ltx25-retake-fast",
    "ltx25-extend-fast",
    "ltx25-motion-fast",
    "ltx25-upscale-fast",
]


def _ltx25(workflows=None):
    names = workflows or LTX25_WORKFLOWS
    return next(m for m in available_models({}, names) if m.id == "ltx-2.5")


def _variant(spec):
    return find_variant(spec, "fast")


def test_ltx25_advertises_advanced_modes_and_limits() -> None:
    spec = _ltx25()
    assert spec.capabilities == (
        "t2v",
        "i2v",
        "fl2v",
        "ref2v",
        "edit",
        "retake",
        "extend",
        "motion",
        "upscale",
    )
    assert spec.max_source_video_seconds == 21
    assert spec.retake_max_duration_seconds == 16
    assert spec.extend_max_duration_seconds == 20
    assert spec.camera_motions == CAMERA_MOTIONS
    assert spec.max_reference_images == 4
    assert spec.supports_keep_original_audio is True
    assert spec.upscale_resolutions == ("1080p", "2K", "4K")
    assert spec.max_upscale_factor == 2


def test_partial_install_narrows_advanced_modes() -> None:
    spec = _ltx25(["ltx25-t2v-fast", "ltx25-edit-fast"])
    assert spec.capabilities == ("t2v", "edit")
    descriptor = model_descriptor(spec, default=True)
    assert descriptor["capabilities"] == ["t2v", "edit"]
    assert descriptor["maxSourceVideoSeconds"] == 21
    assert descriptor["cameraMotions"] == list(CAMERA_MOTIONS)
    assert descriptor["supportsKeepOriginalAudio"] is True


def test_generation_only_install_keeps_the_old_surface() -> None:
    spec = _ltx25(["ltx25-t2v-fast", "ltx25-i2v-fast", "ltx25-fl2v-fast"])
    assert spec.capabilities == ("t2v", "i2v", "fl2v")
    descriptor = model_descriptor(spec, default=False)
    # Camera control is prompt conditioning, so it survives a generation-only
    # install. The source-video limits only appear with a source-video mode.
    assert descriptor["cameraMotions"] == list(CAMERA_MOTIONS)
    assert "maxSourceVideoSeconds" not in descriptor
    assert "retakeMaxDurationSeconds" not in descriptor
    assert "extendMaxDurationSeconds" not in descriptor


def test_source_video_modes_require_a_source_video() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    for mode in ("edit", "retake", "extend"):
        assert (
            validate_request_values(spec, variant, mode=mode, duration=4) == "SOURCE_VIDEO_REQUIRED"
        )


def test_retake_window_is_bounded() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    assert (
        validate_request_values(
            spec,
            variant,
            mode="retake",
            has_source_video=True,
            retake_start_seconds=1,
            retake_duration_seconds=4,
        )
        is None
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="retake",
            has_source_video=True,
            retake_start_seconds=1,
            retake_duration_seconds=1,
        )
        == "RETAKE_RANGE_INVALID"
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="retake",
            has_source_video=True,
            retake_start_seconds=10,
            retake_duration_seconds=16,
        )
        == "RETAKE_RANGE_INVALID"
    )


def test_extend_side_and_context_are_validated() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    assert (
        validate_request_values(
            spec,
            variant,
            mode="extend",
            has_source_video=True,
            extend_side="end",
            context_seconds=4,
            duration=5,
        )
        is None
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="extend",
            has_source_video=True,
            extend_side="sideways",
            duration=5,
        )
        == "EXTEND_SIDE_INVALID"
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="extend",
            has_source_video=True,
            extend_side="end",
            context_seconds=30,
            duration=5,
        )
        == "CONTEXT_UNSUPPORTED"
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="extend",
            has_source_video=True,
            extend_side="end",
            context_seconds=15,
            duration=10,
        )
        == "CONTEXT_UNSUPPORTED"
    )


def test_motion_requires_a_start_frame_and_exactly_one_reference_video() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    assert (
        validate_request_values(spec, variant, mode="motion", reference_video_count=1)
        == "START_FRAME_REQUIRED"
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="motion",
            has_start_frame=True,
            reference_video_count=0,
        )
        == "REFERENCE_VIDEO_REQUIRED"
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="motion",
            has_start_frame=True,
            reference_video_count=1,
        )
        is None
    )


def test_camera_motion_is_model_scoped() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    assert (
        validate_request_values(spec, variant, mode="t2v", duration=5, camera_motion="dolly_in")
        is None
    )
    assert (
        validate_request_values(spec, variant, mode="t2v", duration=5, camera_motion="orbit")
        == "CAMERA_MOTION_UNSUPPORTED"
    )
    # Models without camera conditioning reject the field entirely.
    pika = next(m for m in available_models({}, ["pika-flex-t2v-official"]) if m.id == "pika-flex")
    assert (
        validate_request_values(
            pika,
            find_variant(pika, "official"),
            mode="t2v",
            duration=8,
            camera_motion="dolly_in",
        )
        == "CAMERA_MOTION_UNSUPPORTED"
    )


def test_upscale_requires_a_source_and_a_supported_target() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    assert (
        validate_request_values(spec, variant, mode="upscale", resolution="1080p")
        == "SOURCE_VIDEO_REQUIRED"
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="upscale",
            has_source_video=True,
            resolution="1080p",
        )
        is None
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="upscale",
            has_source_video=True,
            resolution="4K",
        )
        is None
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="upscale",
            has_source_video=True,
            resolution="720p",
        )
        == "RESOLUTION_UNSUPPORTED"
    )


def test_keep_original_audio_is_limited_to_edit_and_motion() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    assert (
        validate_request_values(
            spec,
            variant,
            mode="edit",
            has_source_video=True,
            keep_original_audio=True,
        )
        is None
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="motion",
            has_start_frame=True,
            reference_video_count=1,
            keep_original_audio=True,
        )
        is None
    )
    for mode in ("t2v", "retake", "extend"):
        kwargs = {
            "mode": mode,
            "keep_original_audio": True,
            "has_source_video": mode in ("retake", "extend"),
        }
        if mode == "retake":
            kwargs.update(retake_start_seconds=0, retake_duration_seconds=2)
        if mode == "extend":
            kwargs.update(extend_side="end", duration=2, context_seconds=1)
        assert validate_request_values(spec, variant, **kwargs) == "KEEP_ORIGINAL_AUDIO_UNSUPPORTED"


def test_source_video_cannot_be_combined_with_frames_or_references() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    assert (
        validate_request_values(
            spec,
            variant,
            mode="edit",
            has_source_video=True,
            has_start_frame=True,
        )
        == "REFERENCES_UNSUPPORTED"
    )
    assert (
        validate_request_values(
            spec,
            variant,
            mode="edit",
            has_source_video=True,
            reference_count=1,
        )
        == "REFERENCES_UNSUPPORTED"
    )


def test_source_video_modes_do_not_use_the_generation_duration_list() -> None:
    spec = _ltx25()
    variant = _variant(spec)
    # 16 s is outside the 2..10 s generation list but legal for retake.
    assert (
        validate_request_values(
            spec,
            variant,
            mode="retake",
            has_source_video=True,
            retake_start_seconds=0,
            retake_duration_seconds=16,
        )
        is None
    )


def test_request_mode_infers_advanced_modes() -> None:
    assert _request_mode({"retake_start_seconds": 1}, "video") == "retake"
    assert _request_mode({"extend_side": "end"}, "video") == "extend"
    assert (
        _request_mode(
            {
                "start_frame_url": "https://example.com/a.png",
                "reference_video_urls": ["https://example.com/a.mp4"],
            },
            "video",
        )
        == "motion"
    )
    assert _request_mode({"source_video_url": "https://example.com/a.mp4"}, "video") == "edit"


def _workflow(name: str) -> dict:
    return json.loads((WORKFLOW_DIR / name).read_text())


def test_camera_motion_is_appended_to_the_prompt() -> None:
    workflow = _workflow("ltx25_t2v_fast.json")
    _inject_inputs(
        workflow,
        {
            "prompt": "a fox in a snowy forest",
            "camera_motion": "dolly_in",
            "mode": "t2v",
        },
    )
    prompt = workflow["10"]["inputs"]["prompt"]
    assert prompt.startswith("a fox in a snowy forest")
    assert "dollies in" in prompt


def test_unknown_camera_motion_leaves_the_prompt_alone() -> None:
    workflow = _workflow("ltx25_t2v_fast.json")
    _inject_inputs(workflow, {"prompt": "a fox", "camera_motion": "orbit"})
    assert workflow["10"]["inputs"]["prompt"] == "a fox"


def test_edit_injection_sets_the_source_and_guide_strength() -> None:
    workflow = _workflow("ltx25_edit_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "edit",
            "prompt": "turn the clip into a watercolour",
            "source_video_url": "https://example.com/source.mp4",
            "source_strength": 0.5,
            "keep_original_audio": True,
            "fps": 24,
        },
    )
    inputs = workflow["12"]["inputs"]
    assert inputs["video_url"] == "https://example.com/source.mp4"
    assert inputs["max_frames"] == 505
    assert inputs["mode"] == "edit"
    assert workflow["36"]["inputs"]["strength"] == 0.5
    assert workflow["50"]["inputs"]["keep_original"] is True
    assert workflow["50"]["inputs"]["original_audio"] == ["12", 4]


def test_motion_uses_the_source_clip_audio_when_asked() -> None:
    workflow = _workflow("ltx25_motion_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "motion",
            "prompt": "the dancer follows the choreography",
            "start_frame_url": "https://example.com/start.png",
            "reference_video_urls": ["https://example.com/motion.mp4"],
            "duration": 2,
            "keep_original_audio": True,
            "fps": 24,
        },
    )
    assert workflow["50"]["inputs"]["keep_original"] is True
    assert workflow["50"]["inputs"]["original_audio"] == ["12", 4]
    assert workflow["12"]["inputs"]["mode"] == "motion"


def test_retake_injection_sets_the_window_and_indices() -> None:
    workflow = _workflow("ltx25_retake_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "retake",
            "prompt": "the character turns left",
            "source_video_url": "https://example.com/source.mp4",
            "retake_start_seconds": 2,
            "retake_duration_seconds": 3,
            "fps": 24,
        },
    )
    inputs = workflow["12"]["inputs"]
    assert inputs["start_seconds"] == 2
    assert inputs["duration_seconds"] == 3
    assert workflow["36"]["inputs"]["frame_idx"] == ["12", 7]
    assert workflow["37"]["inputs"]["frame_idx"] == ["12", 8]


def test_extend_injection_sets_the_side() -> None:
    workflow = _workflow("ltx25_extend_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "extend",
            "prompt": "continue the motion",
            "source_video_url": "https://example.com/source.mp4",
            "extend_side": "start",
            "context_seconds": 5,
            "duration": 4,
            "fps": 24,
        },
    )
    inputs = workflow["12"]["inputs"]
    assert inputs["extend_side"] == "start"
    assert inputs["context_seconds"] == 5
    assert inputs["duration_seconds"] == 4


def test_ingredient_injection_fills_the_reference_sheet() -> None:
    workflow = _workflow("ltx25_ref2v_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "ref2v",
            "prompt": "the detective from the top-left meets the cat from the top-right",
            "reference_image_urls": [
                "https://example.com/a.png",
                "https://example.com/b.png",
            ],
        },
    )
    assert workflow["12"]["inputs"]["image_url_1"] == "https://example.com/a.png"
    assert workflow["12"]["inputs"]["image_url_2"] == "https://example.com/b.png"
    text = workflow["10"]["inputs"]
    assert text["prompt"].startswith("Reference sheet:")
    assert "Generated video: the detective" in text["prompt"]
    # The graph's anti-collage negative prompt survives when the caller omits one.
    assert "collage" in text["negative_prompt"]


def test_explicit_negative_prompt_overrides_the_graph_default() -> None:
    workflow = _workflow("ltx25_ref2v_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "ref2v",
            "prompt": "a cat",
            "negative_prompt": "blurry",
            "reference_image_urls": ["https://example.com/a.png"],
        },
    )
    assert workflow["10"]["inputs"]["negative_prompt"] == "blurry"


def test_ingredient_prompt_already_in_the_two_part_format_is_left_alone() -> None:
    workflow = _workflow("ltx25_ref2v_fast.json")
    prompt = "Reference sheet: a fox.\nGenerated video: the fox runs."
    _inject_inputs(
        workflow,
        {
            "mode": "ref2v",
            "prompt": prompt,
            "reference_image_urls": ["https://example.com/a.png"],
        },
    )
    assert workflow["10"]["inputs"]["prompt"] == prompt


def test_upscale_injection_sets_the_mode_and_keeps_source_audio() -> None:
    workflow = _workflow("ltx25_upscale_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "upscale",
            "prompt": "sharpen and upscale",
            "source_video_url": "https://example.com/source.mp4",
            "resolution": "1080p",
            "duration": 2,
            "fps": 24,
        },
    )
    inputs = workflow["12"]["inputs"]
    assert inputs["video_url"] == "https://example.com/source.mp4"
    assert inputs["mode"] == "upscale"
    assert workflow["27"]["inputs"]["keep_original"] is True
    assert workflow["27"]["inputs"]["original_audio"] == ["12", 4]


def test_motion_injection_uses_the_reference_video() -> None:
    workflow = _workflow("ltx25_motion_fast.json")
    _inject_inputs(
        workflow,
        {
            "mode": "motion",
            "prompt": "the dancer follows the choreography",
            "start_frame_url": "https://example.com/start.png",
            "reference_video_urls": ["https://example.com/motion.mp4"],
            "fps": 24,
            "duration": 2,
        },
    )
    assert workflow["12"]["inputs"]["video_url"] == "https://example.com/motion.mp4"
    assert workflow["12"]["inputs"]["max_frames"] == 49
    assert workflow["15"]["inputs"]["image_url_1"] == "https://example.com/start.png"


@pytest.mark.parametrize(
    "name,required",
    [
        ("ltx25_edit_fast.json", {"LoovieVideoEdit", "LTXVAddGuide", "LoovieVideoSettings"}),
        ("ltx25_retake_fast.json", {"LoovieVideoEdit", "LTXVAddGuide"}),
        ("ltx25_extend_fast.json", {"LoovieVideoEdit", "LTXVAddGuide"}),
        ("ltx25_ref2v_fast.json", {"LoovieReferenceSheet", "LTXVAddGuide"}),
        ("ltx25_motion_fast.json", {"LoovieVideoEdit", "LoovieImageInput", "LTXVAddGuide"}),
        (
            "ltx25_upscale_fast.json",
            {"LoovieVideoEdit", "LTXVLatentUpsampler", "LoovieAudioGate"},
        ),
    ],
)
def test_advanced_workflows_have_the_required_nodes_and_links(
    name: str, required: set[str]
) -> None:
    workflow = _workflow(name)
    classes = {node["class_type"] for node in workflow.values()}
    assert required <= classes
    for node_id, node in workflow.items():
        for input_name, value in node.get("inputs", {}).items():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                assert value[0] in workflow, f"{name}:{node_id}.{input_name} -> {value[0]}"
    assert any(node["class_type"] == "SaveVideo" for node in workflow.values()), (
        f"{name} has no SaveVideo"
    )


def test_config_registers_the_advanced_workflows() -> None:
    config = yaml.safe_load((REPO_ROOT / "comfyui-loovie" / "config.yaml").read_text())
    registered = config["workflows"]
    for name in (
        "ltx25-ref2v-fast",
        "ltx25-edit-fast",
        "ltx25-retake-fast",
        "ltx25-extend-fast",
        "ltx25-motion-fast",
        "ltx25-upscale-fast",
    ):
        assert name in registered
        assert (REPO_ROOT / "comfyui-loovie" / registered[name]["file"]).exists()


def test_snap_helpers_keep_ltx_frame_alignment() -> None:
    assert _snap_length(1) == 1
    assert _snap_length(8) == 1
    assert _snap_length(9) == 9
    assert _snap_length(49) == 49
    assert _snap_length(50) == 49
    assert _snap_index(0) == 0
    assert _snap_index(7) == 0
    assert _snap_index(8) == 8
    assert _snap_index(23) == 16
