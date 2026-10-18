"""Build the `/loovie/capabilities` manifest from the registered workflows.

The manifest is derived dynamically: if you register an `ltx25-fl2v-pro`
workflow, `fl2v` and `pro` show up in the video section. Conversely if no
image workflow is registered, the `images` section is omitted entirely so
the app hides the unsupported BYO tier.

Schema and enum values track `openapi/loovie-server.openapi.yaml`.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1

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
    """Build the `ss_videos` section from installed LTX 2.5 workflows."""
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


def build_capabilities_manifest(workflow_names: list[str], version: str) -> dict[str, Any]:
    """Return the capabilities manifest for the given workflow set.

    Args:
        workflow_names: Registered workflow ids (see `config.yaml`).
        version: Build version string for telemetry only.

    Returns:
        A dict matching the `Capabilities` schema from the OpenAPI spec.
        Sections with no registered workflow family are omitted.
    """
    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "version": version,
    }
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
