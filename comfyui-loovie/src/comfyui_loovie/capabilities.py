"""Build the `/loovie/capabilities` manifest from the registered workflows.

The manifest is derived dynamically: if you register an `ltx25-fl2v-pro`
workflow, `fl2v` and `pro` show up in the video section. Conversely if no
image workflow is registered, the `images` section is omitted entirely so
the app hides the unsupported BYO tier.

Schema and enum values track `openapi/loovie-server.openapi.yaml`.

Two halves, on purpose:

* `models` (schemaVersion 2+) is the per-model view the app renders: one
  entry per selectable model, each with its own recipes (`variants`). This
  is where a model like Pika H3 Flex declares `official`, `turbo` and `hq`,
  so a new recipe is a config change, never an app release.
* `images` / `ss_videos` / `music` are the v1 compatibility view describing
  the default model only. Old app builds read these; they stay until the v1
  line is retired.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 2

# Closed enums from the OpenAPI spec. Keep these in lock-step with the
# `*Resolution`, `*AspectRatio` and `durations` definitions in
# `openapi/loovie-server.openapi.yaml`.
_VIDEO_RESOLUTION: list[str] = ["720p", "1080p"]
_VIDEO_ASPECT_RATIOS: list[str] = ["auto", "16:9", "9:16", "1:1"]
_VIDEO_DURATIONS: list[int] = [1, 2, 3, 4, 5, 6, 7, 8]
_VIDEO_SUPPORTS_AUDIO = True
_VIDEO_REFERENCE_COUNT = 1

_IMAGE_RESOLUTION: list[str] = ["720p", "1K", "2K"]
_IMAGE_ASPECT_RATIOS: list[str] = ["auto", "1:1", "16:9", "9:16", "4:3"]
_IMAGE_REFERENCE_COUNT = 4

# YuE2 reference: full songs up to ~240s; style prompt cap mirrors the
# app-side 2000-char music prompt bound.
_MUSIC_MAX_DURATION_SECONDS = 240
_MUSIC_PROMPT_CHAR_LIMIT = 2000

# Must match the hard cap enforced by the create handlers.
_PROMPT_CHAR_LIMIT = 3000


def _video_section(workflow_names: list[str]) -> dict[str, Any] | None:
    """Build the v1 `ss_videos` view from installed LTX 2.5 workflows."""
    names = set(workflow_names)
    modes: list[str] = []
    if any(n.startswith("ltx25-t2v-") for n in names):
        modes.append("t2v")
    if any(n.startswith("ltx25-i2v-") for n in names):
        modes.append("i2v")
    if any(n.startswith("ltx25-fl2v-") for n in names):
        modes.append("fl2v")
    if not modes:
        return None

    variants: list[str] = []
    if any(n.startswith("ltx25-") and n.endswith("-fast") for n in names):
        variants.append("fast")
    if any(n.startswith("ltx25-") and n.endswith("-pro") for n in names):
        variants.append("pro")
    if not variants:
        variants = ["fast"]

    return {
        "capabilities": modes,
        "referenceCount": _VIDEO_REFERENCE_COUNT,
        "resolution": _VIDEO_RESOLUTION,
        "variants": variants,
        "aspectRatios": _VIDEO_ASPECT_RATIOS,
        "durations": _VIDEO_DURATIONS,
        "supportsAudio": _VIDEO_SUPPORTS_AUDIO,
        "promptCharLimit": _PROMPT_CHAR_LIMIT,
    }


# Workflow names that count as "image" capable. Extend this set if you
# register additional image workflows.
_IMAGE_WORKFLOW_NAMES = frozenset({"flux-3-klein", "flux-3-klein-edit", "moss-image"})


# Workflow names that count as "music" capable. Extend this set if you
# register additional music workflows (e.g. a higher-quality YuE2 variant).
_MUSIC_WORKFLOW_NAMES = frozenset({"yue2-t2m-fast"})


def _image_section(workflow_names: list[str]) -> dict[str, Any] | None:
    """Build the `images` section from installed image workflows."""
    if not any(name in _IMAGE_WORKFLOW_NAMES for name in workflow_names):
        return None
    return {
        "capabilities": ["t2i", "i2i"],
        "referenceCount": _IMAGE_REFERENCE_COUNT,
        "resolution": _IMAGE_RESOLUTION,
        "variants": ["fast", "pro"],
        "aspectRatios": _IMAGE_ASPECT_RATIOS,
        "promptCharLimit": _PROMPT_CHAR_LIMIT,
    }


def _music_section(workflow_names: list[str]) -> dict[str, Any] | None:
    """Build the `music` section from installed music workflows.

    The YuE2 reference renders vocals from a lyric sheet and can also
    render instrumental, so both flags are advertised whenever any music
    workflow is registered.
    """
    if not any(name in _MUSIC_WORKFLOW_NAMES for name in workflow_names):
        return None
    return {
        "capabilities": ["t2m"],
        "maxDurationSeconds": _MUSIC_MAX_DURATION_SECONDS,
        "supportsVocals": True,
        "supportsInstrumental": True,
        "promptCharLimit": _MUSIC_PROMPT_CHAR_LIMIT,
    }


def _model_variant(variant_id: str, variant: dict[str, Any]) -> dict[str, Any]:
    """One `variants[]` entry for the v2 manifest.

    Only manifest fields are forwarded; the recipe itself (`lora`, `steps`,
    `shiftVideo`, `shiftAudio`) is routing data the app never needs.
    """
    entry: dict[str, Any] = {
        "id": variant_id,
        "label": str(variant.get("label") or variant_id),
    }
    description = variant.get("description")
    if description:
        entry["description"] = str(description)
    if variant.get("default"):
        entry["default"] = True
    if variant.get("draft"):
        entry["draft"] = True
    capabilities = variant.get("capabilities")
    if isinstance(capabilities, list) and capabilities:
        entry["capabilities"] = [str(c) for c in capabilities]
    for key in ("maxReferenceImages", "maxReferenceAudios", "maxReferenceVideos"):
        value = variant.get(key)
        if isinstance(value, int) and value >= 0:
            entry[key] = value
    return entry


def _model_entry(model_id: str, model: dict[str, Any]) -> dict[str, Any] | None:
    """Build one `models.ss_videos` entry, or None when it cannot run.

    A model is advertised only when at least one of its `templates`
    workflows is registered, so an uninstalled model never shows up as a
    broken option in the picker.
    """
    variants = model.get("variants")
    if not isinstance(variants, dict) or not variants:
        return None
    capabilities = [str(c) for c in model.get("capabilities") or []]
    if not capabilities:
        return None

    entry: dict[str, Any] = {
        "id": model_id,
        "label": str(model.get("label") or model_id),
        "capabilities": capabilities,
        "referenceCount": int(model.get("referenceCount", _VIDEO_REFERENCE_COUNT)),
        "maxReferenceImages": int(model.get("maxReferenceImages", 0)),
        "resolution": [str(r) for r in model.get("resolution") or _VIDEO_RESOLUTION],
        "variants": [
            _model_variant(str(variant_id), variant)
            for variant_id, variant in variants.items()
            if isinstance(variant, dict)
        ],
        "aspectRatios": [str(r) for r in model.get("aspectRatios") or _VIDEO_ASPECT_RATIOS],
        "durations": [int(d) for d in model.get("durations") or _VIDEO_DURATIONS],
        "audio": str(model.get("audio") or "optional"),
    }
    if not entry["variants"]:
        return None
    for key in ("description",):
        if model.get(key):
            entry[key] = str(model[key])
    for key in ("vramGb", "recommendedVramGb", "promptCharLimit", "maxConcurrency"):
        value = model.get(key)
        if isinstance(value, int) and value > 0:
            entry[key] = value
    if model.get("default"):
        entry["default"] = True
    if model.get("recommended"):
        entry["recommended"] = True
    for key in ("maxReferenceAudios", "maxReferenceVideos", "referencesExcludeFrames"):
        if key in model:
            entry[key] = model[key]
    return entry


def _models_section(
    workflow_names: list[str], models: dict[str, dict[str, Any]] | None
) -> dict[str, Any] | None:
    """Build the v2 `models` map from the configured model entries."""
    if not models:
        return None
    registered = set(workflow_names)
    videos: list[dict[str, Any]] = []
    for model_id, model in models.items():
        if not isinstance(model, dict):
            continue
        templates = model.get("templates")
        template_names = [str(v) for v in templates.values()] if isinstance(templates, dict) else []
        if not template_names or not any(name in registered for name in template_names):
            continue
        entry = _model_entry(str(model_id), model)
        if entry is not None:
            videos.append(entry)
    if not videos:
        return None
    return {"ss_videos": videos}


def build_capabilities_manifest(
    workflow_names: list[str],
    version: str,
    models: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the capabilities manifest for the given workflow set.

    Args:
        workflow_names: Registered workflow ids (see `config.yaml`).
        version: Build version string for telemetry only.
        models: The `models:` block from `config.yaml`. When omitted the
            manifest carries only the v1 view, which keeps the function
            usable by callers (and tests) that have no config at hand.

    Returns:
        A dict matching the `Capabilities` schema from the OpenAPI spec.
        Sections with no registered workflow family are omitted.
    """
    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "version": version,
    }
    model_section = _models_section(workflow_names, models)
    if model_section is not None:
        manifest["models"] = model_section
    images = _image_section(workflow_names)
    if images is not None:
        manifest["images"] = images
    videos = _video_section(workflow_names)
    if videos is not None:
        manifest["ss_videos"] = videos
    music = _music_section(workflow_names)
    if music is not None:
        manifest["music"] = music
    return manifest
