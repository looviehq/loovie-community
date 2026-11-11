"""Build the `/loovie/capabilities` manifest from the registered workflows.

The manifest is derived dynamically from the model registry (`models.py`):
enable a model in ``config.yaml`` and its descriptor appears; omit a section
when the server has no workflows for that modality.

Shape (schemaVersion 3)::

    {
      "schemaVersion": 3,
      "version": "0.6.0",
      "hardware": {"gpuName": "RTX 5090", "vramGb": 32},   # optional
      "models": {
        "images":    [ {id, label, capabilities, variants, ...}, ... ],
        "ss_videos": [ {id, label, capabilities, variants, ...}, ... ],
        "music":     [ {id, label, capabilities, variants, ...}, ... ],
        "sfx":       [ {id, label, capabilities, variants, ...}, ... ]
      },
      # OPTIONAL v1 compatibility view, emitted only when the default model can
      # be expressed with the v1 closed enums. Released app builds read these.
      "images":    {...},
      "ss_videos": {...},
      "music":     {...}
    }

`models` is the source of truth. The flat `images`/`ss_videos` blocks are a
compatibility view for app builds from before multi-model BYO; they describe the
default model only, and are OMITTED when it cannot be expressed in v1 (for
example an H3-only server whose only resolution is 480p/768p).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import (
    available_models,
    default_model,
    detect_hardware,
    legacy_section,
    model_descriptor,
    shared_models_config,
)

SCHEMA_VERSION = 3
# Old clients only understand the v2 mode vocabulary. A manifest built for them
# advertises the legacy modes (and the v2 shape) instead of failing their parse.
_V2_VIDEO_MODES = ("t2v", "i2v", "fl2v", "ref2v")

# YuE2 reference: full songs up to ~240s; style prompt cap mirrors the
# app-side 2000-char music prompt bound.
_MUSIC_MAX_DURATION_SECONDS = 240
_MUSIC_PROMPT_CHAR_LIMIT = 2000

# Workflow names that count as music capable.
_MUSIC_WORKFLOW_NAMES = frozenset({"yue2-t2m-fast"})


def _music_section(workflow_names: list[str]) -> dict[str, Any] | None:
    """Text-to-music capabilities. Model-agnostic; unchanged by v2."""

    if not any(name in _MUSIC_WORKFLOW_NAMES for name in workflow_names):
        return None
    return {
        "capabilities": ["t2m"],
        "maxDurationSeconds": _MUSIC_MAX_DURATION_SECONDS,
        "supportsVocals": True,
        "supportsInstrumental": True,
        "promptCharLimit": _MUSIC_PROMPT_CHAR_LIMIT,
    }


def _hardware_section(config: Mapping[str, Any] | None) -> dict[str, Any] | None:
    models_config = shared_models_config(config)
    if models_config.get("report_hardware") is False:
        return None
    override = models_config.get("hardware")
    if isinstance(override, Mapping):
        out = {key: override[key] for key in ("gpuName", "vramGb") if key in override}
        return out or None
    return detect_hardware()


def _for_contract(manifest: dict[str, Any], contract_version: int) -> dict[str, Any]:
    """Downgrade a v3 manifest for a client that only speaks v2.

    The v3 manifest added `edit`/`retake`/`extend`/`motion` to the closed video
    mode enum. A client built before those values existed rejects the WHOLE
    manifest, which reads as "server incompatible" and hides the BYO tier.
    When the caller does not advertise contract 3, advertise only the legacy
    modes (and the v2 shape) so old apps keep working.
    """

    if contract_version >= 3:
        return manifest

    manifest["schemaVersion"] = 2
    for model in manifest.get("models", {}).get("ss_videos", []):
        model["capabilities"] = [
            mode for mode in model.get("capabilities", []) if mode in _V2_VIDEO_MODES
        ]
        for key in (
            "maxSourceVideoSeconds",
            "minSourceVideoSeconds",
            "retakeMaxDurationSeconds",
            "extendMaxDurationSeconds",
            "maxContextSeconds",
            "cameraMotions",
            "supportsKeepOriginalAudio",
        ):
            model.pop(key, None)
    return manifest


def build_capabilities_manifest(
    workflow_names: list[str],
    version: str,
    config: Mapping[str, Any] | None = None,
    contract_version: int = SCHEMA_VERSION,
) -> dict[str, Any]:
    """Return the capabilities manifest for the given workflow set.

    Args:
        workflow_names: Registered workflow ids (see `config.yaml`).
        version: Build version string for telemetry only.
        config: The extension config (``config.yaml``); omitted in tests, in
            which case every catalogue model whose workflows exist is offered.
    """

    specs = available_models(config, workflow_names)
    default_image = default_model(specs, config, "image")
    default_video = default_model(specs, config, "video")
    default_music = default_model(specs, config, "music")
    default_sfx = default_model(specs, config, "sfx")

    image_models = [spec for spec in specs if spec.modality == "image"]
    video_models = [spec for spec in specs if spec.modality == "video"]
    music_models = [spec for spec in specs if spec.modality == "music"]
    sfx_models = [spec for spec in specs if spec.modality == "sfx"]

    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "version": version,
    }

    hardware = _hardware_section(config)
    if hardware is not None:
        manifest["hardware"] = hardware

    if image_models or video_models or music_models or sfx_models:
        models: dict[str, Any] = {}
        if image_models:
            models["images"] = [
                model_descriptor(spec, default=spec is default_image) for spec in image_models
            ]
        if video_models:
            models["ss_videos"] = [
                model_descriptor(spec, default=spec is default_video) for spec in video_models
            ]
        if music_models:
            models["music"] = [
                model_descriptor(spec, default=spec is default_music) for spec in music_models
            ]
        if sfx_models:
            models["sfx"] = [
                model_descriptor(spec, default=spec is default_sfx) for spec in sfx_models
            ]
        manifest["models"] = models

    # Compatibility view for released app builds (v1). Only the default model,
    # and only when every value is inside the v1 closed enums.
    images_legacy = legacy_section(default_image)
    if images_legacy is not None:
        manifest["images"] = images_legacy
    videos_legacy = legacy_section(default_video)
    if videos_legacy is not None:
        manifest["ss_videos"] = videos_legacy
    music_legacy = legacy_section(default_music)
    if music_legacy is not None:
        manifest["music"] = music_legacy

    # Fallback for a custom music workflow that predates the catalogue entry.
    if "music" not in manifest:
        music = _music_section(workflow_names)
        if music is not None:
            manifest["music"] = music

    return _for_contract(manifest, contract_version)


__all__ = ["SCHEMA_VERSION", "build_capabilities_manifest"]
