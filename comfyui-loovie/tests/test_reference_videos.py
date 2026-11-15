"""Reference VIDEO clips for ref2v: manifest budget and request validation.

`reference_video_urls` means two things by mode. `motion` takes exactly one
guide clip (covered in test_video_edit_modes.py). `ref2v` takes up to the
model's `maxReferenceVideos` clips. A model advertises 0 until its graph
consumes the clips: the two H3 ref2v models advertise 3, LTX 2.5 advertises 0,
and the budget logic is exercised here on models built with `dataclasses.replace`.
"""

from __future__ import annotations

import dataclasses

from comfyui_loovie.capabilities import build_capabilities_manifest
from comfyui_loovie.models import available_models, find_variant, validate_request_values

WORKFLOWS = [
    "ltx25-t2v-fast",
    "ltx25-ref2v-fast",
    "pika-flex-ref2v-official",
    "pika-flex-t2v-official",
]


def _pika(**overrides):
    spec = next(m for m in available_models({}, WORKFLOWS) if m.id == "pika-flex")
    return dataclasses.replace(spec, **overrides)


def _validate(spec, variant_id="official", **kwargs):
    return validate_request_values(
        spec,
        find_variant(spec, variant_id),
        mode=kwargs.pop("mode", "ref2v"),
        resolution="768p",
        duration=8,
        **kwargs,
    )


def test_manifest_always_reports_the_video_budget() -> None:
    manifest = build_capabilities_manifest(WORKFLOWS, version="test")
    for model in manifest["models"]["ss_videos"]:
        assert "maxReferenceVideos" in model
        assert model["maxReferenceVideos"] >= 0


def test_a_model_that_advertises_zero_rejects_reference_clips() -> None:
    ltx = next(m for m in available_models({}, WORKFLOWS) if m.id == "ltx-2.5")
    assert ltx.max_reference_videos == 0
    assert (
        _validate(ltx, "fast", reference_count=1, reference_video_count=1)
        == "REFERENCE_VIDEO_UNSUPPORTED"
    )


def test_clips_up_to_the_budget_are_accepted() -> None:
    spec = _pika(max_reference_videos=3)
    assert _validate(spec, reference_video_count=3) is None
    assert _validate(spec, reference_count=2, reference_video_count=1) is None


def test_clips_over_the_budget_are_rejected() -> None:
    spec = _pika(max_reference_videos=3)
    assert _validate(spec, reference_video_count=4) == "REFERENCE_VIDEO_UNSUPPORTED"


def test_a_variant_can_narrow_the_budget() -> None:
    spec = _pika(max_reference_videos=3)
    turbo = dataclasses.replace(find_variant(spec, "turbo"), max_reference_videos=1)
    spec = dataclasses.replace(
        spec,
        variants=tuple(turbo if v.id == "turbo" else v for v in spec.variants),
    )
    assert _validate(spec, "turbo", reference_video_count=2) == "REFERENCE_VIDEO_UNSUPPORTED"
    assert _validate(spec, "turbo", reference_video_count=1) is None


def test_clips_outside_ref2v_and_motion_are_rejected() -> None:
    spec = _pika(max_reference_videos=3)
    assert (
        _validate(spec, mode="i2v", has_start_frame=True, reference_video_count=1)
        == "REFERENCE_VIDEO_UNSUPPORTED"
    )


def test_clips_and_frames_are_exclusive_where_references_exclude_frames() -> None:
    spec = _pika(max_reference_videos=3)
    assert spec.references_exclude_frames
    assert (
        _validate(spec, reference_video_count=1, has_start_frame=True)
        == "REFERENCES_UNSUPPORTED"
    )
