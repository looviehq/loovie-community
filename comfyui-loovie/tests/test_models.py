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
