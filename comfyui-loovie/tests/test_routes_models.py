"""Model-scoped request routing tests (v2)."""

from __future__ import annotations

from comfyui_loovie.server.routes import (
    ModelRequestError,
    _request_mode,
    _resolve_model_request,
)


def test_request_mode_infers_ref2v_from_references() -> None:
    assert (
        _request_mode({"reference_image_urls": ["https://example.com/a.png"]}, "video") == "ref2v"
    )


def test_request_mode_infers_image_edit_from_references() -> None:
    assert _request_mode({"image_urls": ["https://example.com/a.png"]}, "image") == "i2i"
    assert _request_mode({}, "image") == "t2i"
    assert _request_mode({}, "music") == "t2m"
    assert _request_mode({}, "sfx") == "t2s"


def test_model_and_variant_resolve_to_the_registered_workflow() -> None:
    spec, variant, workflow, mode = _resolve_model_request(
        {"model": "ltx-2.5", "variant": "fast", "mode": "t2v"},
        "ltx25-t2v-fast",
        "video",
    )
    assert spec is not None and spec.id == "ltx-2.5"
    assert variant is not None and variant.id == "fast"
    assert workflow == "ltx25-t2v-fast"
    assert mode == "t2v"


def test_legacy_request_uses_the_default_model() -> None:
    spec, variant, workflow, _mode = _resolve_model_request(
        {"variant": "fast", "mode": "t2v"},
        "ltx25-t2v-fast",
        "video",
    )
    assert spec is not None and spec.id == "ltx-2.5"
    assert variant is not None and variant.id == "fast"
    assert workflow == "ltx25-t2v-fast"


def test_unknown_model_raises_a_stable_code() -> None:
    try:
        _resolve_model_request(
            {"model": "nope", "mode": "t2v"},
            "ltx23-t2v-fast",
            "video",
        )
    except ModelRequestError as exc:
        assert exc.code == "MODEL_NOT_ENABLED"
    else:  # pragma: no cover
        raise AssertionError("expected ModelRequestError")


def test_explicit_workflow_is_an_escape_hatch() -> None:
    spec, variant, workflow, mode = _resolve_model_request(
        {"workflow": "my-custom-graph", "mode": "t2v"},
        "ltx23-t2v-fast",
        "video",
    )
    assert spec is None and variant is None
    assert workflow == "my-custom-graph"
    assert mode is None
