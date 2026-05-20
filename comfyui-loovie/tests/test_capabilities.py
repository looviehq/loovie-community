"""Capabilities-manifest construction + OpenAPI-conformance tests.

The capabilities response is the single most important contract surface
the server exposes. These tests pin its shape against the published
OpenAPI schema so the response can never drift away from what the
Loovie app expects.
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


@pytest.fixture(scope="module")
def capabilities_validator() -> Draft202012Validator:
    """Build a Draft 2020-12 validator for the `Capabilities` schema.

    The schema uses internal `$ref` to `ImageCapabilities` and
    `VideoCapabilities`. We point the validator at a schema document
    that combines a top-level `$ref` into `Capabilities` with the full
    `components` block alongside, so every `#/components/schemas/X`
    reference resolves against the same document.
    """
    spec = yaml.safe_load(OPENAPI_PATH.read_text())
    schema = {
        "$ref": "#/components/schemas/Capabilities",
        "components": spec["components"],
    }
    return Draft202012Validator(schema)


def _validate(manifest: dict[str, Any], validator: Draft202012Validator) -> None:
    """Raise jsonschema.ValidationError if `manifest` doesn't fit the schema."""
    validator.validate(manifest)


# ---------------------------------------------------------------------
# Section-construction tests.
# ---------------------------------------------------------------------


def test_empty_workflow_set_yields_no_sections() -> None:
    """Both `images` and `ss_videos` are omitted if nothing is registered."""
    manifest = build_capabilities_manifest([], version="test")
    assert manifest["schemaVersion"] == SCHEMA_VERSION
    assert manifest["version"] == "test"
    assert "images" not in manifest
    assert "ss_videos" not in manifest


def test_only_flux_yields_only_images_section() -> None:
    manifest = build_capabilities_manifest(["flux-2-klein"], version="test")
    assert "images" in manifest
    assert "ss_videos" not in manifest
    images = manifest["images"]
    assert set(images["capabilities"]) == {"t2i", "i2i"}
    assert "fast" in images["variants"] and "pro" in images["variants"]


def test_only_ltx_t2v_fast_yields_video_section_with_t2v_fast() -> None:
    manifest = build_capabilities_manifest(["ltx23-t2v-fast"], version="test")
    assert "images" not in manifest
    assert "ss_videos" in manifest
    videos = manifest["ss_videos"]
    assert videos["capabilities"] == ["t2v"]
    assert videos["variants"] == ["fast"]


def test_all_video_modes_are_detected() -> None:
    manifest = build_capabilities_manifest(
        ["ltx23-t2v-fast", "ltx23-i2v-fast", "ltx23-fl2v-pro"],
        version="test",
    )
    videos = manifest["ss_videos"]
    assert set(videos["capabilities"]) == {"t2v", "i2v", "fl2v"}
    assert set(videos["variants"]) == {"fast", "pro"}


def test_full_workflow_set_emits_both_sections() -> None:
    manifest = build_capabilities_manifest(
        [
            "flux-2-klein",
            "ltx23-t2v-fast",
            "ltx23-t2v-pro",
            "ltx23-i2v-fast",
            "ltx23-i2v-pro",
            "ltx23-fl2v-fast",
            "ltx23-fl2v-pro",
        ],
        version="0.1.0",
    )
    assert "images" in manifest and "ss_videos" in manifest
    assert manifest["version"] == "0.1.0"


def test_schema_version_is_one() -> None:
    """The schema version is pinned to 1 until the manifest shape changes."""
    manifest = build_capabilities_manifest(["flux-2-klein"], version="x")
    assert manifest["schemaVersion"] == 1


def test_image_section_uses_closed_enum_values() -> None:
    """The image section only emits values inside the OpenAPI closed enums."""
    manifest = build_capabilities_manifest(["flux-2-klein"], version="x")
    images = manifest["images"]
    assert set(images["capabilities"]) <= {"t2i", "i2i"}
    assert set(images["resolution"]) <= {"720p", "1K", "2K"}
    assert set(images["variants"]) <= {"fast", "pro"}
    assert set(images["aspectRatios"]) <= {"auto", "1:1", "16:9", "9:16", "4:3"}


def test_video_section_uses_closed_enum_values() -> None:
    """The video section only emits values inside the OpenAPI closed enums."""
    manifest = build_capabilities_manifest(["ltx23-t2v-fast", "ltx23-t2v-pro"], version="x")
    videos = manifest["ss_videos"]
    assert set(videos["capabilities"]) <= {"t2v", "i2v", "fl2v"}
    assert set(videos["resolution"]) <= {"720p", "1080p"}
    assert set(videos["variants"]) <= {"fast", "pro"}
    assert set(videos["aspectRatios"]) <= {"auto", "16:9", "9:16", "1:1"}
    assert set(videos["durations"]) <= set(range(1, 9))
    assert isinstance(videos["supportsAudio"], bool)


def test_video_section_has_no_variants_falls_back_to_fast_default() -> None:
    """An unconventional name without 'fast'/'pro' suffix still gets at least 'fast'."""
    # Only the unusual case where the matcher finds a mode but no
    # `-fast` / `-pro` suffix; defensive default kicks in.
    manifest = build_capabilities_manifest(["ltx23-t2v-experimental"], version="x")
    videos = manifest["ss_videos"]
    assert "fast" in videos["variants"]


# ---------------------------------------------------------------------
# OpenAPI conformance test — the load-bearing one.
# ---------------------------------------------------------------------


def test_manifest_conforms_to_openapi_capabilities_schema(
    capabilities_validator: Draft202012Validator,
) -> None:
    """The full manifest validates against the published `Capabilities` schema."""
    manifest = build_capabilities_manifest(
        [
            "flux-2-klein",
            "ltx23-t2v-fast",
            "ltx23-t2v-pro",
            "ltx23-i2v-fast",
            "ltx23-i2v-pro",
            "ltx23-fl2v-fast",
            "ltx23-fl2v-pro",
        ],
        version="0.1.0",
    )
    _validate(manifest, capabilities_validator)


def test_empty_manifest_conforms_to_openapi_schema(
    capabilities_validator: Draft202012Validator,
) -> None:
    """A manifest with neither section still validates (schemaVersion is enough)."""
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
    ],
    ids=["image-only", "t2v-fast", "i2v-pro", "fl2v-both", "image+video"],
)
def test_various_workflow_subsets_all_conform(
    workflow_set: list[str], capabilities_validator: Draft202012Validator
) -> None:
    manifest = build_capabilities_manifest(workflow_set, version="x")
    _validate(manifest, capabilities_validator)
