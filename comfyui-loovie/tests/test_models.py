"""Model registry tests: filtering, defaults, workflow routing and validation."""

from __future__ import annotations

import pytest

from comfyui_loovie.models import (
    available_models,
    default_model,
    find_variant,
    legacy_section,
    residency_group,
    resolve_workflow,
    validate_request_values,
)

H3_WORKFLOWS = [
    "pika-flex-t2v-official",
    "pika-flex-t2v-turbo",
    "pika-flex-i2v-official",
    "pika-flex-fl2v-official",
    "pika-flex-ref2v-official",
]


HYPERFLOW_WORKFLOWS = [
    f"hyperflow-h3-flash-{mode}-{variant}"
    for mode in ("t2v", "i2v", "fl2v", "ref2v")
    for variant in ("fast", "flash", "hq")
]


def test_hyperflow_flash_offers_all_h3_modes() -> None:
    models = available_models({}, HYPERFLOW_WORKFLOWS)
    spec = next(m for m in models if m.id == "hyperflow-h3-flash")
    assert spec.capabilities == ("t2v", "i2v", "fl2v", "ref2v")
    assert [v.id for v in spec.variants] == ["fast", "flash", "hq"]
    assert find_variant(spec, None).id == "flash"
    assert find_variant(spec, "fast").id == "fast"
    assert find_variant(spec, "pro").id == "hq"
    assert residency_group(spec, "t2v") == "hyperflow-h3-fl2va"
    assert residency_group(spec, "ref2v") == "hyperflow-h3-ref2va"
    assert spec.audio == "always"
    assert spec.frame_step == 17
    assert spec.frame_offset == 5


def test_hyperflow_flash_variants_route_to_the_step_schedules() -> None:
    models = available_models({}, HYPERFLOW_WORKFLOWS)
    spec = next(m for m in models if m.id == "hyperflow-h3-flash")
    for variant, workflow in (
        ("fast", "hyperflow-h3-flash-t2v-fast"),
        ("flash", "hyperflow-h3-flash-t2v-flash"),
        ("hq", "hyperflow-h3-flash-t2v-hq"),
    ):
        assert spec.workflows[("t2v", variant)] == workflow
        assert find_variant(spec, variant).id == variant


def test_hyperflow_flash_partial_install_narrows_modes() -> None:
    models = available_models({}, ["hyperflow-h3-flash-t2v-flash"])
    spec = next(m for m in models if m.id == "hyperflow-h3-flash")
    assert spec.capabilities == ("t2v",)
    assert [v.id for v in spec.variants] == ["flash"]


def _models(config=None):
    return available_models(
        config,
        [
            "flux-2-klein",
            "ltx23-t2v-fast",
            "ltx23-t2v-pro",
            "ltx23-i2v-fast",
            "ltx23-fl2v-fast",
            *H3_WORKFLOWS,
        ],
    )


def test_unregistered_model_is_not_available() -> None:
    models = available_models({}, ["flux-2-klein"])
    assert [m.id for m in models] == ["flux-2-klein"]


def test_unknown_workflow_does_not_create_a_model() -> None:
    assert available_models({}, ["not-a-real-workflow"]) == []


def test_enabled_list_filters_the_catalogue() -> None:
    config = {"models": {"enabled": {"video": ["pika-flex"], "image": []}}}
    models = _models(config)
    assert [m.id for m in models] == ["pika-flex"]


def test_partial_install_narrows_modes_and_variants() -> None:
    models = available_models({}, ["ltx25-t2v-fast"])
    ltx = next(m for m in models if m.id == "ltx-2.5")
    assert ltx.capabilities == ("t2v",)
    assert [v.id for v in ltx.variants] == ["fast"]


def test_default_model_uses_explicit_config_then_marker() -> None:
    models = _models()
    assert default_model(models, None, "image").id == "flux-2-klein"
    assert default_model(models, None, "video").id == "ltx-2.3"
    config = {"models": {"defaults": {"video": "pika-flex", "image": "flux-2-klein"}}}
    assert default_model(models, config, "video").id == "pika-flex"


def test_legacy_variant_aliases_map_to_model_variants() -> None:
    models = _models()
    pika = next(m for m in models if m.id == "pika-flex")
    assert find_variant(pika, "fast").id == "turbo"
    assert find_variant(pika, "pro").id == "official"
    assert find_variant(pika, None).id == "official"


def test_resolve_workflow_by_model_and_variant() -> None:
    models = _models()
    spec, variant, workflow = resolve_workflow(
        models,
        model_id="pika-flex",
        mode="t2v",
        variant_id="official",
        default_model_id="ltx-2.3",
    )
    assert spec.id == "pika-flex"
    assert variant.id == "official"
    assert workflow == "pika-flex-t2v-official"


def test_resolve_workflow_rejects_unknown_model() -> None:
    with pytest.raises(LookupError, match="MODEL_NOT_ENABLED"):
        resolve_workflow(
            _models(),
            model_id="nope",
            mode="t2v",
            variant_id=None,
            default_model_id="ltx-2.3",
        )


def test_resolve_workflow_rejects_mode_not_supported() -> None:
    with pytest.raises(LookupError, match="MODE_UNSUPPORTED"):
        resolve_workflow(
            _models(),
            model_id="ltx-2.3",
            mode="ref2v",
            variant_id=None,
            default_model_id="ltx-2.3",
        )


def test_resolve_workflow_rejects_unknown_variant() -> None:
    with pytest.raises(LookupError, match="VARIANT_UNSUPPORTED"):
        resolve_workflow(
            _models(),
            model_id="pika-flex",
            mode="t2v",
            variant_id="ultra",
            default_model_id="ltx-2.3",
        )


def test_resolve_workflow_omitted_model_uses_default() -> None:
    spec, variant, workflow = resolve_workflow(
        _models(),
        model_id=None,
        mode="t2v",
        variant_id="fast",
        default_model_id="ltx-2.3",
    )
    assert spec.id == "ltx-2.3"
    assert variant.id == "fast"
    assert workflow == "ltx23-t2v-fast"


def test_validation_rejects_resolution_and_duration() -> None:
    models = _models()
    pika = next(m for m in models if m.id == "pika-flex")
    official = find_variant(pika, "official")
    assert (
        validate_request_values(
            pika,
            official,
            mode="t2v",
            resolution="1080p",
            duration=8,
        )
        == "RESOLUTION_UNSUPPORTED"
    )
    assert (
        validate_request_values(
            pika,
            official,
            mode="t2v",
            resolution="768p",
            duration=3,
        )
        == "DURATION_UNSUPPORTED"
    )


def test_validation_rejects_references_with_frames_on_h3() -> None:
    pika = next(m for m in _models() if m.id == "pika-flex")
    official = find_variant(pika, "official")
    assert (
        validate_request_values(
            pika,
            official,
            mode="ref2v",
            resolution="768p",
            duration=8,
            reference_count=2,
            has_start_frame=True,
        )
        == "REFERENCES_UNSUPPORTED"
    )


def test_validation_requires_references_for_ref2v() -> None:
    pika = next(m for m in _models() if m.id == "pika-flex")
    official = find_variant(pika, "official")
    assert (
        validate_request_values(
            pika,
            official,
            mode="ref2v",
            resolution="768p",
            duration=8,
            reference_count=0,
        )
        == "REFERENCES_REQUIRED"
    )


def test_validation_rejects_audio_on_silent_model() -> None:
    ltx = next(m for m in _models() if m.id == "ltx-2.3")
    fast = find_variant(ltx, "fast")
    assert (
        validate_request_values(
            ltx,
            fast,
            mode="t2v",
            resolution="720p",
            duration=5,
            with_audio=True,
        )
        is None  # LTX supports audio
    )
    krea = available_models({}, ["krea-2-t2i-turbo"])[0]
    turbo = find_variant(krea, "turbo")
    assert (
        validate_request_values(
            krea,
            turbo,
            mode="t2i",
            with_audio=True,
        )
        == "AUDIO_UNSUPPORTED"
    )


def test_h3_residency_group_depends_on_mode() -> None:
    pika = next(m for m in _models() if m.id == "pika-flex")
    assert residency_group(pika, "t2v") == "h3-fl2va"
    assert residency_group(pika, "ref2v") == "h3-ref2va"


def test_legacy_section_is_none_when_h3_resolutions_are_not_v1_safe() -> None:
    pika = next(m for m in _models() if m.id == "pika-flex")
    assert legacy_section(pika) is None


def test_sfx_duration_is_bounded_and_has_no_v1_view() -> None:
    sfx = available_models({}, ["stable-audio-3-t2s-small"])[0]
    small = find_variant(sfx, "small")
    assert sfx.modality == "sfx"
    assert legacy_section(sfx) is None
    assert validate_request_values(sfx, small, mode="t2s", duration=5) is None
    assert validate_request_values(sfx, small, mode="t2s", duration=1) is None
    assert validate_request_values(sfx, small, mode="t2s", duration=61) == "DURATION_UNSUPPORTED"
    assert validate_request_values(sfx, small, mode="t2s", duration=0) == "DURATION_UNSUPPORTED"


# ---------------------------------------------------------------------
# MiniMax H3 Image.
# ---------------------------------------------------------------------

H3_IMAGE_WORKFLOWS = ["minimax-h3-image-t2i", "minimax-h3-image-i2i"]


def test_minimax_h3_image_offers_text_to_image_and_editing() -> None:
    models = available_models({}, H3_IMAGE_WORKFLOWS)
    spec = next(m for m in models if m.id == "minimax-h3-image")
    assert spec.modality == "image"
    assert spec.capabilities == ("t2i", "i2i")
    assert spec.workflows[("t2i", "default")] == "minimax-h3-image-t2i"
    assert spec.workflows[("i2i", "default")] == "minimax-h3-image-i2i"
    assert find_variant(spec, None).id == "default"
    assert find_variant(spec, "pro") is None
    assert spec.resolutions == ("1K", "2K", "4K")
    assert spec.reference_count == 4
    # Guidance is fixed at 1, so the app must not offer a negative prompt.
    assert spec.supports_negative_prompt is False
    assert spec.residency_group == "h3-image"
    assert spec.min_comfyui == "0.45.0"


def test_minimax_h3_image_scales_the_canvas_with_the_resolution() -> None:
    models = available_models({}, H3_IMAGE_WORKFLOWS)
    spec = next(m for m in models if m.id == "minimax-h3-image")
    assert spec.resolution_scales_canvas is True


def test_minimax_h3_image_partial_install_narrows_modes() -> None:
    models = available_models({}, ["minimax-h3-image-t2i"])
    spec = next(m for m in models if m.id == "minimax-h3-image")
    assert spec.capabilities == ("t2i",)


def test_other_catalogue_models_keep_the_legacy_canvas() -> None:
    """Only models that opt in may resize the canvas from the resolution field."""

    for spec in available_models({}, [*H3_IMAGE_WORKFLOWS, "krea-2-t2i-turbo", "flux-2-klein"]):
        if spec.modality != "image" or spec.id == "minimax-h3-image":
            continue
        assert spec.resolution_scales_canvas is False, spec.id
