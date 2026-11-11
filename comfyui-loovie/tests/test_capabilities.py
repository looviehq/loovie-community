"""Capabilities-manifest construction + OpenAPI-conformance tests.

The capabilities response is the single most important contract surface
the server exposes. These tests pin the v2 model map, the v1 compatibility
view, and the published OpenAPI schema so the response can never drift.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from comfyui_loovie.capabilities import (
    SCHEMA_VERSION,
    build_capabilities_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "openapi" / "loovie-server.openapi.yaml"

ALL_WORKFLOWS = [
    "flux-2-klein",
    "ltx23-t2v-fast",
    "ltx23-t2v-pro",
    "ltx23-i2v-fast",
    "ltx23-i2v-pro",
    "ltx23-fl2v-fast",
    "ltx23-fl2v-pro",
    "yue2-t2m-fast",
]

H3_WORKFLOWS = [
    "pika-flex-t2v-official",
    "pika-flex-t2v-turbo",
    "pika-flex-i2v-official",
    "pika-flex-fl2v-official",
    "pika-flex-ref2v-official",
]

PIKA_WORKFLOWS = [
    "pika-flex-t2v-official",
    "pika-flex-i2v-official",
    "pika-flex-fl2v-official",
    "pika-flex-ref2v-official",
    "pika-flex-t2v-turbo",
    "pika-flex-i2v-turbo",
    "pika-flex-fl2v-turbo",
    "pika-flex-ref2v-turbo",
    "pika-flex-hd-t2v-hd",
    "pika-flex-hd-i2v-hd",
    "pika-flex-hd-fl2v-hd",
]

PIKA_CONFIG = {
    "models": {
        "enabled": {
            "video": ["pika-flex", "pika-flex-hd"],
            "image": [],
            "music": [],
            "sfx": [],
        },
        "defaults": {"video": "pika-flex"},
        "report_hardware": False,
    }
}

H3_ONLY_CONFIG = {
    "models": {
        "enabled": {"video": ["pika-flex"], "image": []},
        "defaults": {"video": "pika-flex"},
        "report_hardware": False,
    }
}


@pytest.fixture(scope="module")
def capabilities_validator() -> Draft202012Validator:
    spec = yaml.safe_load(OPENAPI_PATH.read_text())
    schema = {
        "$ref": "#/components/schemas/Capabilities",
        "components": spec["components"],
    }
    return Draft202012Validator(schema)


def _validate(manifest: dict[str, Any], validator: Draft202012Validator) -> None:
    validator.validate(manifest)


def test_empty_workflow_set_yields_no_sections() -> None:
    manifest = build_capabilities_manifest([], version="test")
    assert manifest["schemaVersion"] == SCHEMA_VERSION
    assert manifest["version"] == "test"
    for key in ("images", "ss_videos", "music", "models", "hardware"):
        assert key not in manifest


def test_only_flux_yields_images_model_and_legacy_view() -> None:
    manifest = build_capabilities_manifest(["flux-2-klein"], version="test")
    assert "ss_videos" not in manifest
    assert "models" in manifest
    models = manifest["models"]["images"]
    assert [m["id"] for m in models] == ["flux-2-klein"]
    assert models[0]["default"] is True
    assert set(models[0]["capabilities"]) == {"t2i", "i2i"}
    assert models[0]["variants"][0]["id"] == "default"
    # v1 view for released app builds
    assert set(manifest["images"]["capabilities"]) == {"t2i", "i2i"}
    assert manifest["images"]["variants"] == ["fast", "pro"]


def test_only_ltx_t2v_fast_narrows_variants() -> None:
    manifest = build_capabilities_manifest(["ltx23-t2v-fast"], version="test")
    assert "images" not in manifest
    assert "models" in manifest
    video = manifest["models"]["ss_videos"][0]
    assert video["id"] == "ltx-2.3"
    assert video["capabilities"] == ["t2v"]
    assert [v["id"] for v in video["variants"]] == ["fast"]
    # Legacy view must not advertise a pro workflow that is not registered.
    assert manifest["ss_videos"]["variants"] == ["fast"]


def test_all_video_modes_are_detected() -> None:
    manifest = build_capabilities_manifest(
        ["ltx23-t2v-fast", "ltx23-i2v-fast", "ltx23-fl2v-pro"],
        version="test",
    )
    video = manifest["models"]["ss_videos"][0]
    assert set(video["capabilities"]) == {"t2v", "i2v", "fl2v"}
    assert {v["id"] for v in video["variants"]} == {"fast", "pro"}


def test_h3_only_server_has_model_but_no_v1_video_view() -> None:
    """H3's resolution set is not expressible in v1, so old apps hide BYO
    rather than receiving values their closed enums would reject."""

    manifest = build_capabilities_manifest(H3_WORKFLOWS, version="test", config=H3_ONLY_CONFIG)
    assert "ss_videos" not in manifest  # no v1-compatible view
    model = manifest["models"]["ss_videos"][0]
    assert model["id"] == "pika-flex"
    assert set(model["capabilities"]) == {"t2v", "i2v", "fl2v", "ref2v"}
    assert model["resolution"] == ["384p", "480p", "540p", "768p"]
    assert model["audio"] == "always"
    assert model["maxReferenceImages"] == 9
    assert model["referencesExcludeFrames"] is True
    assert model["vramGb"] == 24


def test_default_model_drives_the_legacy_view() -> None:
    manifest = build_capabilities_manifest(
        [*ALL_WORKFLOWS, *H3_WORKFLOWS],
        version="test",
        config={
            "models": {
                "enabled": {
                    "video": ["ltx-2.3", "pika-flex"],
                    "image": ["flux-2-klein"],
                },
                "defaults": {"video": "pika-flex", "image": "flux-2-klein"},
                "report_hardware": False,
            }
        },
    )
    # Pika is the default, so the legacy video view disappears entirely.
    assert "ss_videos" not in manifest
    assert "images" in manifest
    assert len(manifest["models"]["ss_videos"]) == 2


def test_only_yue2_yields_music_model_and_legacy_section() -> None:
    manifest = build_capabilities_manifest(["yue2-t2m-fast"], version="test")
    assert "images" not in manifest
    assert "ss_videos" not in manifest
    assert "models" in manifest
    model = manifest["models"]["music"][0]
    assert model["id"] == "yue2"
    assert model["default"] is True
    assert model["capabilities"] == ["t2m"]
    assert model["supportsVocals"] is True
    assert model["supportsInstrumental"] is True
    assert model["maxDurationSeconds"] == 240
    music = manifest["music"]
    assert music["capabilities"] == ["t2m"]
    assert music["supportsVocals"] is True
    assert music["supportsInstrumental"] is True


def test_pika_h3_flex_workflows_advertise_all_shipped_modes() -> None:
    manifest = build_capabilities_manifest(PIKA_WORKFLOWS, version="test", config=PIKA_CONFIG)
    assert "ss_videos" not in manifest  # 384p/480p/540p/768p is not v1-safe
    flex, hd = manifest["models"]["ss_videos"]
    assert flex["id"] == "pika-flex"
    assert set(flex["capabilities"]) == {"t2v", "i2v", "fl2v", "ref2v"}
    assert {v["id"] for v in flex["variants"]} == {"official", "turbo"}
    assert flex["maxReferenceImages"] == 9
    assert flex["referencesExcludeFrames"] is True
    assert flex["audio"] == "always"
    assert hd["id"] == "pika-flex-hd"
    assert set(hd["capabilities"]) == {"t2v", "i2v", "fl2v"}
    assert {v["id"] for v in hd["variants"]} == {"hd"}


def test_stable_audio_3_yields_sfx_model_and_no_v1_view() -> None:
    manifest = build_capabilities_manifest(["stable-audio-3-t2s-small"], version="test")
    assert "music" not in manifest
    assert "sfx" not in manifest  # v1 has no SFX section
    model = manifest["models"]["sfx"][0]
    assert model["id"] == "stable-audio-3"
    assert model["default"] is True
    assert model["capabilities"] == ["t2s"]
    assert model["maxDurationSeconds"] == 60
    assert model["supportsNegativePrompt"] is True
    assert {v["id"] for v in model["variants"]} == {"small"}


def test_full_workflow_set_emits_all_sections() -> None:
    manifest = build_capabilities_manifest(ALL_WORKFLOWS, version="0.1.0")
    assert "models" in manifest
    assert "images" in manifest and "ss_videos" in manifest and "music" in manifest
    assert manifest["version"] == "0.1.0"


def test_schema_version_is_two() -> None:
    manifest = build_capabilities_manifest(["flux-2-klein"], version="x")
    assert manifest["schemaVersion"] == 2


def test_hardware_is_omitted_when_reporting_is_disabled() -> None:
    manifest = build_capabilities_manifest(
        ["flux-2-klein"], version="x", config={"models": {"report_hardware": False}}
    )
    assert "hardware" not in manifest


def test_hardware_override_is_emitted() -> None:
    manifest = build_capabilities_manifest(
        ["flux-2-klein"],
        version="x",
        config={
            "models": {
                "report_hardware": True,
                "hardware": {"gpuName": "RTX 5090", "vramGb": 32},
            }
        },
    )
    assert manifest["hardware"] == {"gpuName": "RTX 5090", "vramGb": 32}


def test_legacy_sections_stay_inside_v1_closed_enums() -> None:
    manifest = build_capabilities_manifest(ALL_WORKFLOWS, version="x")
    images = manifest["images"]
    assert set(images["capabilities"]) <= {"t2i", "i2i"}
    assert set(images["resolution"]) <= {"720p", "1K", "2K"}
    assert set(images["variants"]) <= {"fast", "pro"}
    assert set(images["aspectRatios"]) <= {"auto", "1:1", "16:9", "9:16", "4:3"}

    videos = manifest["ss_videos"]
    assert set(videos["capabilities"]) <= {"t2v", "i2v", "fl2v"}
    assert set(videos["resolution"]) <= {"720p", "1080p"}
    assert set(videos["variants"]) <= {"fast", "pro"}
    assert set(videos["aspectRatios"]) <= {"auto", "16:9", "9:16", "1:1"}
    assert isinstance(videos["supportsAudio"], bool)


def test_unknown_workflow_does_not_invent_a_model() -> None:
    manifest = build_capabilities_manifest(["ltx23-t2v-experimental"], version="x")
    assert "models" not in manifest
    assert "ss_videos" not in manifest


def test_repo_config_advertises_the_shipped_models() -> None:
    """The checked-in config enables exactly the workflows we ship by default."""

    config = yaml.safe_load((REPO_ROOT / "comfyui-loovie" / "config.yaml").read_text())
    workflows = list(config["workflows"])
    manifest = build_capabilities_manifest(workflows, version="x", config=config)
    assert [m["id"] for m in manifest["models"]["images"]] == [
        "flux-2-klein",
        "qwen-image-2.1",
        "flux-3-klein",
        "krea-2",
        "minimax-h3-image",
    ]
    assert [m["id"] for m in manifest["models"]["ss_videos"]] == [
        "ltx-2.5",
        "pika-flex",
        "pika-flex-hd",
        "hyperflow-h3-flash",
    ]
    assert [m["id"] for m in manifest["models"]["music"]] == ["yue2"]
    assert [m["id"] for m in manifest["models"]["sfx"]] == ["stable-audio-3"]


def test_hyperflow_flash_is_advertised_from_its_workflows() -> None:
    manifest = build_capabilities_manifest(
        [
            f"hyperflow-h3-flash-{mode}-{variant}"
            for mode in ("t2v", "i2v", "fl2v", "ref2v")
            for variant in ("fast", "flash", "hq")
        ],
        version="x",
    )
    model = manifest["models"]["ss_videos"][0]
    assert model["id"] == "hyperflow-h3-flash"
    assert model["capabilities"] == ["t2v", "i2v", "fl2v", "ref2v"]
    assert [v["id"] for v in model["variants"]] == ["fast", "flash", "hq"]
    assert "768p" in model["resolution"]


def test_manifest_conforms_to_openapi_capabilities_schema(
    capabilities_validator: Draft202012Validator,
) -> None:
    manifest = build_capabilities_manifest(ALL_WORKFLOWS, version="0.1.0")
    _validate(manifest, capabilities_validator)


def test_h3_manifest_conforms_to_openapi_schema(
    capabilities_validator: Draft202012Validator,
) -> None:
    manifest = build_capabilities_manifest(H3_WORKFLOWS, version="0.1.0", config=H3_ONLY_CONFIG)
    _validate(manifest, capabilities_validator)


def test_empty_manifest_conforms_to_openapi_schema(
    capabilities_validator: Draft202012Validator,
) -> None:
    manifest = build_capabilities_manifest([], version="x")
    _validate(manifest, capabilities_validator)


@pytest.mark.parametrize(
    "workflow_set",
    [
        ["flux-2-klein"],
        ["ltx23-t2v-fast"],
        ["ltx23-i2v-pro"],
        ["ltx23-fl2v-fast", "ltx23-fl2v-pro"],
        ["flux-2-klein", "ltx23-t2v-fast"],
        ["yue2-t2m-fast"],
        ["stable-audio-3-t2s-small"],
        ["flux-2-klein", "yue2-t2m-fast"],
        ["yue2-t2m-fast", "stable-audio-3-t2s-small"],
        H3_WORKFLOWS,
        PIKA_WORKFLOWS,
    ],
    ids=[
        "image-only",
        "t2v-fast",
        "i2v-pro",
        "fl2v-both",
        "image+video",
        "music",
        "sfx",
        "image+music",
        "music+sfx",
        "h3",
        "pika",
    ],
)
def test_various_workflow_subsets_all_conform(
    workflow_set: list[str], capabilities_validator: Draft202012Validator
) -> None:
    config = (
        H3_ONLY_CONFIG
        if workflow_set == H3_WORKFLOWS
        else (PIKA_CONFIG if workflow_set == PIKA_WORKFLOWS else None)
    )
    manifest = build_capabilities_manifest(workflow_set, version="x", config=config)
    _validate(manifest, capabilities_validator)


def test_minimax_h3_image_is_advertised_from_its_workflows() -> None:
    """The H3 Image entry must describe the canvas the app can actually ask for."""

    manifest = build_capabilities_manifest(
        ["minimax-h3-image-t2i", "minimax-h3-image-i2i"], version="x"
    )
    model = manifest["models"]["images"][0]
    assert model["id"] == "minimax-h3-image"
    assert model["capabilities"] == ["t2i", "i2i"]
    assert model["resolution"] == ["1K", "2K", "4K"]
    assert model["referenceCount"] == 4
    assert model["vramGb"] == 36
    assert model["recommendedVramGb"] == 64
    assert [v["id"] for v in model["variants"]] == ["default"]


def test_minimax_h3_image_manifest_conforms_to_openapi(
    capabilities_validator: Draft202012Validator,
) -> None:
    manifest = build_capabilities_manifest(
        ["minimax-h3-image-t2i", "minimax-h3-image-i2i"], version="0.1.0"
    )
    _validate(manifest, capabilities_validator)
