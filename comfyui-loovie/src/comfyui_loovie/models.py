"""Model catalogue for the BYO server.

The contract is model-agnostic, but a *server* has to know which models it
actually offers. This module is that registry: it turns the workflows registered
in ``config.yaml`` into a set of model descriptors the capabilities manifest can
publish and the create routes can validate against.

A model is only advertised when at least one of its workflows is registered. A
partially installed model (say, LTX 2.5 fast but not pro) advertises only the
modes/variants whose workflow exists, so the app never offers something the
server cannot run.

Workflow names are deliberately conventional (``ltx25-t2v-fast``,
``pika-flex-ref2v-official``) and every entry can be overridden in
``config.yaml`` under ``models.workflows``. The app never sees a workflow name;
it sees a model id + variant, and the server maps those here.
"""

from __future__ import annotations

import copy
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Any

# Audio policy for a model.
AUDIO_NONE = "none"
AUDIO_OPTIONAL = "optional"
AUDIO_ALWAYS = "always"

# LTX 2.5 advanced video operations. `edit` is a full-clip restyle, `retake`
# regenerates a time window, `extend` lengthens a clip, and `motion` follows a
# reference video. Ingredients reuse `ref2v`. Camera control is a request field
# on any of these modes, not a mode of its own.
VIDEO_MODES = (
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
SOURCE_VIDEO_MODES = ("edit", "retake", "extend", "upscale")
IMAGE_MODES = ("t2i", "i2i")
SFX_MODES = ("t2s",)

# Camera moves the LTX 2.5 prompt conditioning understands. The reference
# implementation turns these into explicit camera language in the prompt.
CAMERA_MOTIONS = (
    "static",
    "dolly_in",
    "dolly_out",
    "dolly_left",
    "dolly_right",
    "jib_up",
    "jib_down",
    "pan_left",
    "pan_right",
    "tilt_up",
    "tilt_down",
    "focus_shift",
)

# V1 closed enums. The legacy compatibility view must stay inside these; an old
# app fails the WHOLE parse on an unknown value.
_V1_VIDEO_MODES = ("t2v", "i2v", "fl2v")
_V1_VIDEO_RESOLUTIONS = ("720p", "1080p")
_V1_VIDEO_ASPECTS = ("auto", "16:9", "9:16", "1:1")
_V1_IMAGE_MODES = ("t2i", "i2i")
_V1_IMAGE_RESOLUTIONS = ("720p", "1K", "2K")
_V1_IMAGE_ASPECTS = ("auto", "1:1", "16:9", "9:16", "4:3")
_V1_VARIANTS = ("fast", "pro")


@dataclass(frozen=True)
class VariantSpec:
    """One user-selectable recipe inside a model."""

    id: str
    label: str
    description: str = ""
    default: bool = False
    draft: bool = False
    # Optional narrowing for this variant only (e.g. Pika HD cannot take refs).
    capabilities: tuple[str, ...] | None = None
    max_reference_images: int | None = None
    # Optional per-variant workflow-name suffix override; defaults to the id.
    workflow_suffix: str | None = None


@dataclass(frozen=True)
class ModelSpec:
    id: str
    modality: str  # "image" | "video" | "music" | "sfx"
    label: str
    description: str
    capabilities: tuple[str, ...]
    variants: tuple[VariantSpec, ...]
    # (mode, variant_id) -> registered workflow name.
    workflows: Mapping[tuple[str, str], str]
    resolutions: tuple[str, ...]
    aspect_ratios: tuple[str, ...]
    durations: tuple[int, ...] = ()
    reference_count: int = 0
    max_reference_images: int = 0
    references_exclude_frames: bool = False
    audio: str = AUDIO_NONE
    # Source-video limits for edit/retake/extend/motion. 0 = unsupported.
    max_source_video_seconds: int = 0
    min_source_video_seconds: int = 0
    retake_max_duration_seconds: int = 0
    extend_max_duration_seconds: int = 0
    max_context_seconds: int = 0
    # Upscale targets and the largest factor the model can apply.
    upscale_resolutions: tuple[str, ...] = ()
    max_upscale_factor: int = 0
    # Camera moves this model can follow; empty = no camera control.
    camera_motions: tuple[str, ...] = ()
    # Whether edit/motion can keep the source clip's audio track.
    supports_keep_original_audio: bool = False
    # Music-only capabilities.
    max_duration_seconds: int = 240
    supports_vocals: bool = True
    supports_instrumental: bool = True
    supports_negative_prompt: bool = True
    # Optional frame-grid constraint (H3: 17n + 5 at 24 fps). 0 disables.
    frame_step: int = 0
    frame_offset: int = 0
    prompt_char_limit: int = 3000
    vram_gb: float | None = None
    recommended_vram_gb: float | None = None
    # Weight group that must be resident for this model. A switch between
    # groups may require an explicit unload; see `switch_policy`.
    residency_group: str = ""
    # v1 fast/pro -> v2 variant id. Used by old app builds and the flat view.
    legacy_variants: Mapping[str, str] = field(default_factory=dict)
    default: bool = False
    recommended: bool = False
    min_comfyui: str | None = None
    # Per-mode residency overrides (H3 FL2VA vs Ref2VA are different checkpoints).
    residency_by_mode: Mapping[str, str] = field(default_factory=dict)


def _grid(
    modes: Iterable[str], variants: Iterable[str], template: str
) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for mode in modes:
        for variant in variants:
            out[(mode, variant)] = template.format(mode=mode, variant=variant)
    return out


def _ltx(model_id: str, prefix: str, generation: str) -> ModelSpec:
    workflows = _grid(
        ("t2v", "i2v", "fl2v"),
        ("fast", "pro"),
        f"{prefix}-{{mode}}-{{variant}}",
    )
    return ModelSpec(
        id=model_id,
        modality="video",
        label=f"LTX {generation}",
        description=(
            "Lightricks LTX video with synchronized audio. "
            "fast is the distilled recipe, pro the two-stage quality recipe."
        ),
        capabilities=("t2v", "i2v", "fl2v"),
        variants=(
            VariantSpec("fast", "Fast", "Distilled, faster."),
            VariantSpec(
                "pro",
                "Pro",
                "Two-stage spatial upscale, highest quality.",
            ),
        ),
        workflows=workflows,
        # LTX 2.5's distilled transformer rejects latents below 540p
        # (tensor-size mismatch at the sampler); 384p/480p are H3 cells.
        resolutions=("540p", "720p", "1080p", "2K"),
        aspect_ratios=("auto", "16:9", "9:16", "1:1", "4:3", "3:4"),
        durations=tuple(range(1, 9)) if generation == "2.3" else tuple(range(2, 11)),
        audio=AUDIO_OPTIONAL,
        vram_gb=24,
        recommended_vram_gb=32,
        residency_group=f"{model_id}-group",
        legacy_variants={"fast": "fast", "pro": "pro"},
        min_comfyui="0.32.0",
    )


def _ltx25() -> ModelSpec:
    """LTX 2.5: generation plus the advanced edit/retake/extend/motion surface.

    The advanced modes are advertised only when their workflow exists, so a
    server that ships only the generation graphs still behaves exactly as it
    did before. Ingredients are `ref2v`; camera control is a request field.
    """

    model_id = "ltx-2.5"
    workflows = {
        ("t2v", "fast"): "ltx25-t2v-fast",
        ("i2v", "fast"): "ltx25-i2v-fast",
        ("fl2v", "fast"): "ltx25-fl2v-fast",
        ("ref2v", "fast"): "ltx25-ref2v-fast",
        ("edit", "fast"): "ltx25-edit-fast",
        ("retake", "fast"): "ltx25-retake-fast",
        ("extend", "fast"): "ltx25-extend-fast",
        ("motion", "fast"): "ltx25-motion-fast",
        ("upscale", "fast"): "ltx25-upscale-fast",
    }
    return ModelSpec(
        id=model_id,
        modality="video",
        label="LTX 2.5",
        description=(
            "Lightricks LTX video with synchronized audio. "
            "fast is the distilled recipe; supports text/image/first-last-frame "
            "generation, ingredient references, editing, retake, extension, "
            "motion control and camera moves."
        ),
        capabilities=VIDEO_MODES,
        variants=(VariantSpec("fast", "Fast", "Distilled, faster.", default=True),),
        workflows=workflows,
        # LTX 2.5's distilled transformer rejects latents below 540p
        # (tensor-size mismatch at the sampler); 384p/480p are H3 cells.
        resolutions=("540p", "720p", "1080p", "2K"),
        aspect_ratios=("auto", "16:9", "9:16", "1:1", "4:3", "3:4"),
        durations=tuple(range(2, 11)),
        reference_count=1,
        max_reference_images=4,
        references_exclude_frames=True,
        audio=AUDIO_OPTIONAL,
        # LTX 2.5 accepts up to ~21 s of source footage. Retake can replace up
        # to 16 s in one pass; extend adds up to 20 s per request.
        max_source_video_seconds=21,
        min_source_video_seconds=3,
        retake_max_duration_seconds=16,
        extend_max_duration_seconds=20,
        max_context_seconds=20,
        upscale_resolutions=("1080p", "2K", "4K"),
        max_upscale_factor=2,
        camera_motions=CAMERA_MOTIONS,
        supports_keep_original_audio=True,
        vram_gb=24,
        recommended_vram_gb=32,
        residency_group=f"{model_id}-group",
        legacy_variants={"fast": "fast", "pro": "fast"},
        min_comfyui="0.43.0",
    )


def _pika(model_id: str, label: str, description: str, *, hd: bool = False) -> ModelSpec:
    variants = (
        (VariantSpec("hd", "HD", "8-step HD recipe; first/last frame only."),)
        if hd
        else (
            VariantSpec(
                "official",
                "Official",
                "Pika's 6-step recipe; best quality, references supported.",
                default=True,
            ),
            VariantSpec(
                "turbo",
                "Turbo",
                "4-step distill; faster, draft-grade on references.",
                draft=True,
            ),
        )
    )
    modes = ("t2v", "i2v", "fl2v") if hd else ("t2v", "i2v", "fl2v", "ref2v")
    workflows: dict[tuple[str, str], str] = {}
    for variant in variants:
        suffix = variant.workflow_suffix or variant.id
        for mode in modes:
            workflows[(mode, variant.id)] = f"{model_id}-{mode}-{suffix}"
    return ModelSpec(
        id=model_id,
        modality="video",
        label=label,
        description=description,
        capabilities=modes,
        variants=variants,
        workflows=workflows,
        resolutions=("384p", "480p", "540p", "768p"),
        aspect_ratios=("auto", "16:9", "9:16", "1:1", "4:3", "3:4"),
        durations=tuple(range(5, 16)),
        max_reference_images=0 if hd else 9,
        references_exclude_frames=not hd,
        audio=AUDIO_ALWAYS,
        frame_step=17,
        frame_offset=5,
        vram_gb=24,
        recommended_vram_gb=32,
        residency_group="h3-fl2va",
        residency_by_mode={"ref2v": "h3-ref2va"},
        legacy_variants={"fast": "hd" if hd else "turbo", "pro": "hd" if hd else "official"},
        min_comfyui="0.43.0",
    )


def _hyperflow_flash() -> ModelSpec:
    """Video Rebirth's 14B few-step distillation of MiniMax H3 (GGUF path)."""

    model_id = "hyperflow-h3-flash"
    workflows = {
        (mode, variant): f"{model_id}-{mode}-{variant}"
        for mode in ("t2v", "i2v", "fl2v", "ref2v")
        for variant in ("fast", "flash", "hq")
    }
    return ModelSpec(
        id=model_id,
        modality="video",
        label="HyperFlow H3 Flash",
        description=(
            "Video Rebirth's 14B distillation of MiniMax H3. "
            "Native audio, first/last-frame and reference-to-video, with a "
            "smaller transformer and lower latency than the full H3 recipes."
        ),
        capabilities=("t2v", "i2v", "fl2v", "ref2v"),
        variants=(
            VariantSpec(
                "fast",
                "Fast",
                "4-step schedule; fastest, draft quality.",
                draft=True,
            ),
            VariantSpec(
                "flash",
                "Flash",
                "6-step schedule; the balanced default.",
                default=True,
            ),
            VariantSpec(
                "hq",
                "HQ",
                "8-step schedule; highest quality, slower.",
            ),
        ),
        workflows=workflows,
        resolutions=("384p", "480p", "540p", "768p"),
        aspect_ratios=("auto", "16:9", "9:16", "1:1", "4:3", "3:4"),
        durations=tuple(range(5, 16)),
        max_reference_images=9,
        references_exclude_frames=True,
        audio=AUDIO_ALWAYS,
        frame_step=17,
        frame_offset=5,
        vram_gb=24,
        recommended_vram_gb=32,
        residency_group="hyperflow-h3-fl2va",
        residency_by_mode={"ref2v": "hyperflow-h3-ref2va"},
        legacy_variants={"fast": "fast", "pro": "hq"},
        min_comfyui="0.43.0",
    )


CATALOG: tuple[ModelSpec, ...] = (
    # ── images ─────────────────────────────────────────────────────────────
    ModelSpec(
        id="flux-2-klein",
        modality="image",
        label="FLUX.2 Klein",
        description="FLUX.2 Klein, text-to-image and multi-reference editing.",
        capabilities=("t2i", "i2i"),
        variants=(VariantSpec("default", "Default", "", default=True),),
        workflows={
            ("t2i", "default"): "flux-2-klein",
            ("i2i", "default"): "flux-2-klein",
        },
        resolutions=("720p", "1K", "2K"),
        aspect_ratios=("auto", "1:1", "16:9", "9:16", "4:3"),
        reference_count=4,
        vram_gb=16,
        recommended_vram_gb=24,
        residency_group="flux2-klein",
        legacy_variants={"fast": "default", "pro": "default"},
        default=True,
    ),
    ModelSpec(
        id="qwen-image-2.1",
        modality="image",
        label="Qwen-Image 2.1",
        description="7B Qwen image model with native 2K output and up to 10 references.",
        capabilities=("t2i", "i2i"),
        variants=(
            VariantSpec("turbo", "Turbo", "8-step distilled.", default=True),
            VariantSpec("base", "Base", "Full 25-step recipe."),
        ),
        workflows=_grid(
            ("t2i", "i2i"),
            ("turbo", "base"),
            "qwen-image-2-1-{mode}-{variant}",
        ),
        resolutions=("1K", "2K"),
        aspect_ratios=("auto", "1:1", "4:3", "3:4", "16:9", "9:16"),
        reference_count=10,
        vram_gb=12,
        recommended_vram_gb=24,
        residency_group="qwen21",
        legacy_variants={"fast": "turbo", "pro": "base"},
        min_comfyui="0.37.0",
    ),
    ModelSpec(
        id="flux-3-klein",
        modality="image",
        label="FLUX 3 Image Klein",
        description="5.6B FLUX 3 Klein with 4K output and multi-reference editing.",
        capabilities=("t2i", "i2i"),
        variants=(
            VariantSpec("distilled", "Distilled", "16-step distilled.", default=True),
            VariantSpec("base", "Base", "Full 50-step recipe."),
        ),
        workflows=_grid(
            ("t2i", "i2i"),
            ("distilled", "base"),
            "flux-3-klein-{mode}-{variant}",
        ),
        resolutions=("1K", "2K", "4K"),
        aspect_ratios=("auto", "1:1", "4:3", "3:4", "16:9", "9:16"),
        reference_count=10,
        vram_gb=12,
        recommended_vram_gb=16,
        residency_group="flux3-klein",
        legacy_variants={"fast": "distilled", "pro": "base"},
        min_comfyui="0.41.0",
    ),
    ModelSpec(
        id="krea-2",
        modality="image",
        label="Krea 2",
        description="Krea 2 text-to-image with a distinctive aesthetic prior. Text to image only.",
        capabilities=("t2i",),
        variants=(
            VariantSpec("turbo", "Turbo", "8-step distilled.", default=True),
            VariantSpec("raw", "RAW", "Full 52-step base."),
        ),
        workflows=_grid(("t2i",), ("turbo", "raw"), "krea-2-{mode}-{variant}"),
        resolutions=("1K", "2K"),
        aspect_ratios=("auto", "1:1", "4:3", "3:4", "16:9", "9:16"),
        vram_gb=16,
        recommended_vram_gb=24,
        residency_group="krea2",
        legacy_variants={"fast": "turbo", "pro": "raw"},
        min_comfyui="0.32.0",
    ),
    ModelSpec(
        id="moss-image",
        modality="image",
        label="MOSS-Image",
        description="5B OpenMOSS image model with layout control and strong text rendering.",
        capabilities=("t2i", "i2i"),
        variants=(
            VariantSpec("sft", "SFT", "Instruction-tuned.", default=True),
            VariantSpec("base", "Base", "Base checkpoint."),
        ),
        workflows=_grid(("t2i", "i2i"), ("sft", "base"), "moss-image-{mode}-{variant}"),
        resolutions=("1K", "2K"),
        aspect_ratios=("auto", "1:1", "4:3", "3:4", "16:9", "9:16"),
        reference_count=4,
        vram_gb=8,
        recommended_vram_gb=16,
        residency_group="moss-image",
        legacy_variants={"fast": "sft", "pro": "base"},
        min_comfyui="0.32.0",
    ),
    ModelSpec(
        id="stable-audio-3",
        modality="sfx",
        label="Stable Audio 3",
        description="Stable Audio 3 Small SFX: short text-to-sound effects and ambience.",
        capabilities=("t2s",),
        variants=(
            VariantSpec(
                "small",
                "Small",
                "Stable Audio 3 Small, 8-step LCM recipe.",
                default=True,
            ),
        ),
        workflows={("t2s", "small"): "stable-audio-3-t2s-small"},
        resolutions=(),
        aspect_ratios=(),
        max_duration_seconds=60,
        supports_negative_prompt=True,
        prompt_char_limit=2000,
        vram_gb=4,
        recommended_vram_gb=8,
        residency_group="stable-audio-3",
        default=True,
    ),
    # ── music / audio ──────────────────────────────────────────────────────
    ModelSpec(
        id="yue2",
        modality="music",
        label="YuE2",
        description=(
            "YuE2 text-to-music: a full song with vocals or an instrumental "
            "render from a style prompt and optional lyric sheet."
        ),
        capabilities=("t2m",),
        variants=(VariantSpec("fast", "Fast", "Reference YuE2 recipe.", default=True),),
        workflows={("t2m", "fast"): "yue2-t2m-fast"},
        resolutions=(),
        aspect_ratios=(),
        max_duration_seconds=240,
        supports_vocals=True,
        supports_instrumental=True,
        prompt_char_limit=2000,
        vram_gb=4,
        recommended_vram_gb=8,
        residency_group="yue2",
        default=True,
    ),
    # ── video ──────────────────────────────────────────────────────────────
    _ltx("ltx-2.3", "ltx23", "2.3"),
    _ltx25(),
    _pika(
        "pika-flex",
        "Pika H3 Flex",
        "MiniMax H3 with Pika's 6-step adapters, native audio and reference-to-video.",
    ),
    _pika(
        "pika-flex-hd",
        "Pika H3 Flex HD",
        "Pika H3 Flex 8-step HD recipe; first/last frame only.",
        hd=True,
    ),
    _hyperflow_flash(),
)


def _available_modes(spec: ModelSpec, registered: set[str]) -> tuple[str, ...]:
    return tuple(mode for mode in spec.capabilities if _available_variants(spec, mode, registered))


def _available_variants(
    spec: ModelSpec, mode: str, registered: set[str]
) -> tuple[VariantSpec, ...]:
    out = []
    for variant in spec.variants:
        if variant.capabilities is not None and mode not in variant.capabilities:
            continue
        workflow = spec.workflows.get((mode, variant.id))
        if workflow and workflow in registered:
            out.append(variant)
    return tuple(out)


def _filter_to_available(spec: ModelSpec, registered: set[str]) -> ModelSpec | None:
    modes = _available_modes(spec, registered)
    if not modes:
        return None
    variants = tuple(
        variant
        for variant in spec.variants
        if any(variant in _available_variants(spec, mode, registered) for mode in modes)
    )
    # Keep only workflows whose mode/variant survived.
    workflows = {
        key: name
        for key, name in spec.workflows.items()
        if key[0] in modes and any(v.id == key[1] for v in variants)
    }
    return replace(spec, capabilities=modes, variants=variants, workflows=workflows)


def _config_models(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not config:
        return {}
    value = config.get("models")
    return value if isinstance(value, Mapping) else {}


def _enabled_ids(config: Mapping[str, Any] | None, modality: str) -> set[str] | None:
    enabled = _config_models(config).get("enabled")
    if not isinstance(enabled, Mapping):
        return None
    values = enabled.get(modality)
    if values is None:
        return None
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return None
    return {str(v).strip() for v in values if str(v).strip()}


def _workflow_overrides(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    overrides = _config_models(config).get("workflows")
    return overrides if isinstance(overrides, Mapping) else {}


def _apply_overrides(spec: ModelSpec, config: Mapping[str, Any] | None) -> ModelSpec:
    override = _workflow_overrides(config).get(spec.id)
    if not isinstance(override, Mapping):
        return spec
    workflows = dict(spec.workflows)
    for key, value in override.items():
        if not isinstance(key, str) or "-" not in key:
            continue
        mode, _, variant = key.partition("-")
        if mode and variant and isinstance(value, str) and value.strip():
            workflows[(mode, variant)] = value.strip()
    return replace(spec, workflows=workflows)


def available_models(
    config: Mapping[str, Any] | None,
    workflow_names: Iterable[str],
) -> list[ModelSpec]:
    """Return the models this server can actually serve, filtered by config.

    A model is available when it is enabled (or no enabled list was given) and at
    least one of its workflows is registered. Its advertised modes/variants are
    narrowed to the workflows that exist, so a partial install never promises
    something it cannot run.
    """

    registered = {str(name) for name in workflow_names}
    out: list[ModelSpec] = []
    for base in CATALOG:
        enabled = _enabled_ids(config, base.modality)
        if enabled is not None and base.id not in enabled:
            continue
        spec = _apply_overrides(base, config)
        filtered = _filter_to_available(spec, registered)
        if filtered is None:
            continue
        out.append(filtered)
    return out


def default_model(
    specs: Iterable[ModelSpec], config: Mapping[str, Any] | None, modality: str
) -> ModelSpec | None:
    models = [spec for spec in specs if spec.modality == modality]
    if not models:
        return None
    defaults = _config_models(config).get("defaults")
    explicit = defaults.get(modality) if isinstance(defaults, Mapping) else None
    if isinstance(explicit, str):
        for spec in models:
            if spec.id == explicit:
                return spec
    for spec in models:
        if spec.default:
            return spec
    return models[0]


def default_variant(spec: ModelSpec) -> VariantSpec:
    for variant in spec.variants:
        if variant.default:
            return variant
    return spec.variants[0]


def find_variant(spec: ModelSpec, variant_id: str | None) -> VariantSpec | None:
    """Resolve a requested variant, accepting the v1 fast/pro aliases."""

    raw = (variant_id or "").strip()
    if not raw:
        return default_variant(spec)
    for variant in spec.variants:
        if variant.id == raw:
            return variant
    legacy = spec.legacy_variants.get(raw)
    if legacy:
        for variant in spec.variants:
            if variant.id == legacy:
                return variant
    return None


def model_descriptor(spec: ModelSpec, *, default: bool) -> dict[str, Any]:
    """The v2 `models.*` entry for one model."""

    descriptor: dict[str, Any] = {
        "id": spec.id,
        "label": spec.label,
        "description": spec.description,
        "default": default,
        "capabilities": list(spec.capabilities),
    }
    if spec.recommended:
        descriptor["recommended"] = True
    if spec.vram_gb is not None:
        descriptor["vramGb"] = spec.vram_gb
    if spec.recommended_vram_gb is not None:
        descriptor["recommendedVramGb"] = spec.recommended_vram_gb
    if spec.modality == "music":
        descriptor["maxDurationSeconds"] = spec.max_duration_seconds
        descriptor["supportsVocals"] = spec.supports_vocals
        descriptor["supportsInstrumental"] = spec.supports_instrumental
        descriptor["promptCharLimit"] = spec.prompt_char_limit
        descriptor["variants"] = [
            {
                "id": variant.id,
                "label": variant.label,
                **({"description": variant.description} if variant.description else {}),
                **({"default": True} if variant.default else {}),
            }
            for variant in spec.variants
        ]
        return descriptor
    if spec.modality == "sfx":
        descriptor["maxDurationSeconds"] = spec.max_duration_seconds
        descriptor["supportsNegativePrompt"] = spec.supports_negative_prompt
        descriptor["promptCharLimit"] = spec.prompt_char_limit
        descriptor["variants"] = [
            {
                "id": variant.id,
                "label": variant.label,
                **({"description": variant.description} if variant.description else {}),
                **({"default": True} if variant.default else {}),
            }
            for variant in spec.variants
        ]
        return descriptor
    if spec.modality == "image":
        descriptor["referenceCount"] = spec.reference_count
    else:
        descriptor["referenceCount"] = 1 if "i2v" in spec.capabilities else 0
        descriptor["maxReferenceImages"] = spec.max_reference_images
        if spec.max_reference_images > 0:
            descriptor["referencesExcludeFrames"] = spec.references_exclude_frames
        descriptor["durations"] = list(spec.durations)
        descriptor["audio"] = spec.audio
        if spec.max_source_video_seconds and any(
            mode in spec.capabilities for mode in (*SOURCE_VIDEO_MODES, "motion")
        ):
            descriptor["maxSourceVideoSeconds"] = spec.max_source_video_seconds
            if spec.min_source_video_seconds:
                descriptor["minSourceVideoSeconds"] = spec.min_source_video_seconds
        if spec.retake_max_duration_seconds and "retake" in spec.capabilities:
            descriptor["retakeMaxDurationSeconds"] = spec.retake_max_duration_seconds
        if spec.extend_max_duration_seconds and "extend" in spec.capabilities:
            descriptor["extendMaxDurationSeconds"] = spec.extend_max_duration_seconds
        if spec.max_context_seconds and (
            "retake" in spec.capabilities or "extend" in spec.capabilities
        ):
            descriptor["maxContextSeconds"] = spec.max_context_seconds
        if spec.upscale_resolutions and "upscale" in spec.capabilities:
            descriptor["upscaleResolutions"] = list(spec.upscale_resolutions)
            if spec.max_upscale_factor:
                descriptor["maxUpscaleFactor"] = spec.max_upscale_factor
        if spec.camera_motions:
            descriptor["cameraMotions"] = list(spec.camera_motions)
        if spec.supports_keep_original_audio:
            descriptor["supportsKeepOriginalAudio"] = True
    descriptor["resolution"] = list(spec.resolutions)
    descriptor["aspectRatios"] = list(spec.aspect_ratios)
    descriptor["promptCharLimit"] = spec.prompt_char_limit
    descriptor["variants"] = [
        {
            "id": variant.id,
            "label": variant.label,
            **({"description": variant.description} if variant.description else {}),
            **({"default": True} if variant.default else {}),
            **({"draft": True} if variant.draft else {}),
            **(
                {"capabilities": list(variant.capabilities)}
                if variant.capabilities is not None
                else {}
            ),
            **(
                {"maxReferenceImages": variant.max_reference_images}
                if variant.max_reference_images is not None
                else {}
            ),
        }
        for variant in spec.variants
    ]
    return descriptor


def _v1_image_section(spec: ModelSpec) -> dict[str, Any] | None:
    modes = [mode for mode in spec.capabilities if mode in _V1_IMAGE_MODES]
    resolutions = [r for r in spec.resolutions if r in _V1_IMAGE_RESOLUTIONS]
    aspects = [a for a in spec.aspect_ratios if a in _V1_IMAGE_ASPECTS]
    available = {variant.id for variant in spec.variants}
    variants = [v for v in _V1_VARIANTS if spec.legacy_variants.get(v) in available]
    if not modes or not resolutions or not aspects or not variants:
        return None
    return {
        "capabilities": modes,
        "referenceCount": spec.reference_count,
        "resolution": resolutions,
        "variants": variants,
        "aspectRatios": aspects,
        "promptCharLimit": spec.prompt_char_limit,
    }


def _v1_video_section(spec: ModelSpec) -> dict[str, Any] | None:
    modes = [mode for mode in spec.capabilities if mode in _V1_VIDEO_MODES]
    resolutions = [r for r in spec.resolutions if r in _V1_VIDEO_RESOLUTIONS]
    aspects = [a for a in spec.aspect_ratios if a in _V1_VIDEO_ASPECTS]
    available = {variant.id for variant in spec.variants}
    variants = [v for v in _V1_VARIANTS if spec.legacy_variants.get(v) in available]
    if not modes or not resolutions or not aspects or not variants or not spec.durations:
        return None
    return {
        "capabilities": modes,
        "referenceCount": 1 if "i2v" in spec.capabilities else 0,
        "resolution": resolutions,
        "variants": variants,
        "aspectRatios": aspects,
        "durations": list(spec.durations),
        "supportsAudio": spec.audio != AUDIO_NONE,
        "promptCharLimit": spec.prompt_char_limit,
    }


def _v1_music_section(spec: ModelSpec) -> dict[str, Any]:
    return {
        "capabilities": ["t2m"],
        "maxDurationSeconds": spec.max_duration_seconds,
        "supportsVocals": spec.supports_vocals,
        "supportsInstrumental": spec.supports_instrumental,
        "promptCharLimit": spec.prompt_char_limit,
    }


def legacy_section(spec: ModelSpec | None) -> dict[str, Any] | None:
    """The v1 flat view for a default model, or None when it cannot be expressed."""

    if spec is None:
        return None
    if spec.modality == "image":
        return _v1_image_section(spec)
    if spec.modality == "music":
        return _v1_music_section(spec)
    if spec.modality == "sfx":
        return None
    return _v1_video_section(spec)


def resolve_model(specs: Iterable[ModelSpec], model_id: str | None) -> ModelSpec | None:
    raw = (model_id or "").strip()
    if not raw:
        return None
    for spec in specs:
        if spec.id == raw:
            return spec
    return None


def resolve_workflow(
    specs: Iterable[ModelSpec],
    *,
    model_id: str | None,
    mode: str,
    variant_id: str | None,
    default_model_id: str | None,
) -> tuple[ModelSpec | None, VariantSpec | None, str | None]:
    """Resolve a request to (model, variant, workflow name).

    Returns ``(None, None, None)`` when no model was named; callers then fall
    back to the legacy default. Raises ``LookupError`` with a stable code when a
    model/variant is named but unusable.
    """

    models = list(specs)
    spec = resolve_model(models, model_id)
    if spec is None:
        if (model_id or "").strip():
            raise LookupError("MODEL_NOT_ENABLED")
        spec = resolve_model(models, default_model_id)
        if spec is None:
            return None, None, None
    if mode not in spec.capabilities:
        raise LookupError("MODE_UNSUPPORTED")
    variant = find_variant(spec, variant_id)
    if variant is None:
        raise LookupError("VARIANT_UNSUPPORTED")
    if variant.capabilities is not None and mode not in variant.capabilities:
        raise LookupError("MODE_UNSUPPORTED")
    workflow = spec.workflows.get((mode, variant.id))
    if not workflow:
        raise LookupError("VARIANT_UNSUPPORTED")
    return spec, variant, workflow


def residency_group(spec: ModelSpec, mode: str) -> str:
    return spec.residency_by_mode.get(mode, spec.residency_group)


def validate_request_values(
    spec: ModelSpec,
    variant: VariantSpec,
    *,
    mode: str,
    resolution: str | None = None,
    aspect_ratio: str | None = None,
    duration: float | int | None = None,
    reference_count: int = 0,
    with_audio: bool = False,
    has_start_frame: bool = False,
    has_end_frame: bool = False,
    has_source_video: bool = False,
    reference_video_count: int = 0,
    retake_start_seconds: float | int | None = None,
    retake_duration_seconds: float | int | None = None,
    extend_side: str | None = None,
    context_seconds: float | int | None = None,
    camera_motion: str | None = None,
    keep_original_audio: bool = False,
) -> str | None:
    """Return a stable error code when a request is outside the model's caps.

    The route layer maps the code to a 400. Every branch is checked here rather
    than in the graph so a bad request never reaches ComfyUI's queue.
    """

    if mode not in spec.capabilities:
        return "MODE_UNSUPPORTED"
    if variant.capabilities is not None and mode not in variant.capabilities:
        return "MODE_UNSUPPORTED"

    if camera_motion and camera_motion not in spec.camera_motions:
        return "CAMERA_MOTION_UNSUPPORTED"

    if keep_original_audio and (
        not spec.supports_keep_original_audio or mode not in ("edit", "motion", "upscale")
    ):
        return "KEEP_ORIGINAL_AUDIO_UNSUPPORTED"

    if mode in SOURCE_VIDEO_MODES and not has_source_video:
        return "SOURCE_VIDEO_REQUIRED"
    if mode not in SOURCE_VIDEO_MODES and mode != "motion" and has_source_video:
        return "SOURCE_VIDEO_UNSUPPORTED"
    if mode == "motion":
        if not has_start_frame:
            return "START_FRAME_REQUIRED"
        if reference_video_count != 1:
            return "REFERENCE_VIDEO_REQUIRED"

    if mode in SOURCE_VIDEO_MODES:
        if not spec.max_source_video_seconds:
            return "SOURCE_VIDEO_UNSUPPORTED"
        if mode == "retake":
            if not spec.retake_max_duration_seconds:
                return "MODE_UNSUPPORTED"
            if retake_start_seconds is None or retake_duration_seconds is None:
                return "RETAKE_RANGE_INVALID"
            try:
                start = float(retake_start_seconds)
                length = float(retake_duration_seconds)
            except (TypeError, ValueError):
                return "RETAKE_RANGE_INVALID"
            if start < 0 or length < 2 or length > spec.retake_max_duration_seconds:
                return "RETAKE_RANGE_INVALID"
            if start + length > spec.max_source_video_seconds:
                return "RETAKE_RANGE_INVALID"
        if mode == "extend":
            if not spec.extend_max_duration_seconds:
                return "MODE_UNSUPPORTED"
            if (extend_side or "end").lower() not in ("start", "end"):
                return "EXTEND_SIDE_INVALID"
            if context_seconds is not None:
                try:
                    context = float(context_seconds)
                except (TypeError, ValueError):
                    return "CONTEXT_UNSUPPORTED"
                if context < 0 or context > spec.max_context_seconds:
                    return "CONTEXT_UNSUPPORTED"
                if duration is not None:
                    try:
                        if context + float(duration) > spec.max_source_video_seconds:
                            return "CONTEXT_UNSUPPORTED"
                    except (TypeError, ValueError):
                        return "DURATION_UNSUPPORTED"
        if mode in ("edit", "retake", "extend") and duration is not None:
            try:
                seconds = float(duration)
            except (TypeError, ValueError):
                return "DURATION_UNSUPPORTED"
            upper = (
                spec.retake_max_duration_seconds
                if mode == "retake"
                else spec.extend_max_duration_seconds
                if mode == "extend"
                else spec.max_source_video_seconds
            )
            if seconds <= 0 or seconds > upper:
                return "DURATION_UNSUPPORTED"
        # Source-video modes carry no first/last-frame or reference-image
        # conditioning in this reference implementation.
        if mode in SOURCE_VIDEO_MODES and (has_start_frame or has_end_frame or reference_count > 0):
            return "REFERENCES_UNSUPPORTED"

    if spec.modality == "music":
        if duration is not None:
            try:
                if float(duration) > spec.max_duration_seconds:
                    return "DURATION_UNSUPPORTED"
            except (TypeError, ValueError):
                return "DURATION_UNSUPPORTED"
        return None

    if spec.modality == "sfx":
        seconds = 5.0 if duration is None else duration
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            return "DURATION_UNSUPPORTED"
        if seconds < 1 or seconds > spec.max_duration_seconds:
            return "DURATION_UNSUPPORTED"
        return None

    if mode == "upscale" and resolution and resolution not in spec.upscale_resolutions:
        return "RESOLUTION_UNSUPPORTED"
    if mode != "upscale" and resolution and resolution not in spec.resolutions:
        return "RESOLUTION_UNSUPPORTED"

    if aspect_ratio and aspect_ratio not in spec.aspect_ratios:
        return "ASPECT_RATIO_UNSUPPORTED"

    # Source-video modes validate their own duration windows above; the
    # generation duration list describes output clips, not retake length.
    if duration is not None and spec.durations and mode not in SOURCE_VIDEO_MODES:
        try:
            seconds = round(float(duration))
        except (TypeError, ValueError):
            return "DURATION_UNSUPPORTED"
        if seconds not in spec.durations:
            return "DURATION_UNSUPPORTED"

    if with_audio and spec.audio == AUDIO_NONE:
        return "AUDIO_UNSUPPORTED"

    max_refs = (
        variant.max_reference_images
        if variant.max_reference_images is not None
        else (spec.max_reference_images or spec.reference_count)
    )
    if reference_count > max_refs:
        return "REFERENCES_UNSUPPORTED"

    if (
        reference_count > 0
        and spec.references_exclude_frames
        and (has_start_frame or has_end_frame)
    ):
        return "REFERENCES_UNSUPPORTED"

    if mode == "ref2v" and reference_count == 0:
        return "REFERENCES_REQUIRED"
    if mode in ("i2v", "fl2v") and not has_start_frame:
        return "START_FRAME_REQUIRED"
    if mode == "fl2v" and not has_end_frame:
        return "END_FRAME_REQUIRED"
    if has_end_frame and not has_start_frame:
        return "START_FRAME_REQUIRED"

    return None


@lru_cache(maxsize=1)
def detect_hardware() -> dict[str, Any] | None:
    """Best-effort GPU name + VRAM. Never raises; None when unknown."""

    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            timeout=2,
            text=True,
        )
    except Exception:
        out = ""
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    # Report the largest card; a multi-GPU ComfyUI still loads one model at a time.
    best: dict[str, Any] | None = None
    for line in lines:
        name, _, memory = line.partition(",")
        try:
            vram = round(float(memory.strip()) / 1024, 1)
        except ValueError:
            continue
        candidate = {"gpuName": name.strip(), "vramGb": vram}
        if best is None or vram > float(best["vramGb"]):
            best = candidate

    # GB10 / unified-memory boxes report `[N/A]` for nvidia-smi's memory.total.
    # Fall back to torch so the app can still show VRAM fit badges.
    if best is None:
        try:
            import torch

            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                best = {
                    "gpuName": str(props.name),
                    "vramGb": round(float(props.total_memory) / (1024**3), 1),
                }
        except Exception:
            best = None

    return best


def shared_models_config(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return _config_models(config)


def copy_catalog() -> list[ModelSpec]:
    """Deep copy of the built-in catalogue (tests / custom tooling)."""

    return [copy.deepcopy(spec) for spec in CATALOG]
