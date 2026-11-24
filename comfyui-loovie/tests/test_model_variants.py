"""The v2 `models` view and the per-request Pika H3 Flex recipe.

Two layers, tested apart: the manifest (what the app renders) and the
routing (which graph + which recipe a `model` + `variant` request becomes).
`hq` is the 8-evaluation recipe, so it has to be advertised and applied
like any other variant, never special-cased in the app.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from comfyui_loovie.capabilities import build_capabilities_manifest
from comfyui_loovie.server.routes import (
    _apply_model_variant,
    _resolve_workflow_name,
)
from comfyui_loovie.workflow_manager import WorkflowManager

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
OPENAPI_PATH = REPO_ROOT / "openapi" / "loovie-server.openapi.yaml"
H3_WORKFLOWS = ["h3flex-t2v", "h3flex-frames"]

#: The `models:` block from the shipped config.yaml.
MODELS: dict[str, Any] = (yaml.safe_load((PACKAGE_ROOT / "config.yaml").read_text()) or {}).get(
    "models"
) or {}


@pytest.fixture(scope="module")
def capabilities_validator() -> Draft202012Validator:
    spec = yaml.safe_load(OPENAPI_PATH.read_text())
    schema = {
        "$ref": "#/components/schemas/Capabilities",
        "components": spec["components"],
    }
    return Draft202012Validator(schema)


def test_pika_h3_flex_is_advertised_with_three_recipes() -> None:
    manifest = build_capabilities_manifest(H3_WORKFLOWS, version="x", models=MODELS)
    models = manifest["models"]["ss_videos"]
    assert [m["id"] for m in models] == ["pika-h3-flex"]
    pika = models[0]
    assert [v["id"] for v in pika["variants"]] == ["official", "turbo", "hq"]
    labels = {v["id"]: v["label"] for v in pika["variants"]}
    assert labels["hq"] == "HQ"
    assert labels["turbo"] == "Turbo"
    hq = next(v for v in pika["variants"] if v["id"] == "hq")
    # HQ is a full recipe, not a subset: it must not lose a mode the model has.
    assert hq.get("capabilities") is None
    assert pika["audio"] == "always"
    assert "480p" in pika["resolution"] and "768p" in pika["resolution"]
    assert pika["durations"][0] == 5 and pika["durations"][-1] == 15


def test_manifest_matches_the_published_schema(
    capabilities_validator: Draft202012Validator,
) -> None:
    manifest = build_capabilities_manifest(
        [*H3_WORKFLOWS, "flux-3-klein", "ltx25-t2v-fast"],
        version="x",
        models=MODELS,
    )
    capabilities_validator.validate(manifest)


def test_model_is_hidden_until_its_workflows_are_registered() -> None:
    manifest = build_capabilities_manifest(["flux-3-klein"], version="x", models=MODELS)
    assert "models" not in manifest


def test_variant_recipes_are_not_leaked_into_the_manifest() -> None:
    manifest = build_capabilities_manifest(H3_WORKFLOWS, version="x", models=MODELS)
    serialised = json.dumps(manifest)
    # The LoRA file and the step count are routing data, not app data.
    assert "comfyui_bf16" not in serialised
    assert '"steps"' not in serialised


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"model": "pika-h3-flex", "mode": "t2v"}, "h3flex-t2v"),
        (
            {"model": "pika-h3-flex", "mode": "i2v", "start_frame_url": "https://x/1.png"},
            "h3flex-frames",
        ),
        (
            {
                "model": "pika-h3-flex",
                "mode": "fl2v",
                "start_frame_url": "https://x/1.png",
                "end_frame_url": "https://x/2.png",
            },
            "h3flex-frames",
        ),
        # An explicit workflow still wins over the model mapping.
        ({"model": "pika-h3-flex", "workflow": "ltx25-t2v-fast"}, "ltx25-t2v-fast"),
    ],
)
def test_model_routing(body: dict[str, str], expected: str) -> None:
    WorkflowManager.reset()
    assert _resolve_workflow_name(body, "") == expected


def test_unknown_model_falls_through_to_the_legacy_mapping() -> None:
    WorkflowManager.reset()
    body = {"model": "nope", "mode": "t2v", "variant": "fast"}
    assert _resolve_workflow_name(body, "") == "ltx25-t2v-fast"


def test_references_on_a_frame_only_model_are_refused_not_dropped() -> None:
    """Pika H3 Flex is frame-keyed; a reference set must not become a t2v job."""
    WorkflowManager.reset()
    body = {
        "model": "pika-h3-flex",
        "mode": "ref2v",
        "reference_image_urls": ["https://x/1.png"],
    }
    # No pika template, and nothing registered for ref2v either, so the
    # caller gets the "workflow is required" 400 rather than a silent drop.
    assert _resolve_workflow_name(body, "") == ""


@pytest.mark.parametrize(
    ("variant", "steps", "lora", "shift"),
    [
        ("turbo", 4, "minimax_h3_fl2v_turbo_4step_v0.1_comfyui_bf16.safetensors", 6.0),
        ("hq", 8, "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", 6.0),
    ],
)
def test_variant_applies_lora_steps_and_shift(
    variant: str, steps: int, lora: str, shift: float
) -> None:
    WorkflowManager.reset()
    graph = WorkflowManager.get_instance().load_workflow("h3flex-t2v")
    _apply_model_variant(graph, {"model": "pika-h3-flex", "variant": variant})
    lora_node = next(n for n in graph.values() if n["class_type"] == "LoraLoaderModelOnly")
    assert lora_node["inputs"]["lora_name"] == lora
    scheduler = next(n for n in graph.values() if n["class_type"] == "BasicScheduler")
    assert scheduler["inputs"]["steps"] == steps
    shift_node = next(n for n in graph.values() if n["class_type"] == "MiniMaxH3SigmaShift")
    assert shift_node["inputs"]["shift_video"] == shift
    assert shift_node["inputs"]["shift_audio"] == 3.0


def test_official_drops_the_lora_node_and_keeps_the_trunk() -> None:
    WorkflowManager.reset()
    graph = WorkflowManager.get_instance().load_workflow("h3flex-t2v")
    _apply_model_variant(graph, {"model": "pika-h3-flex", "variant": "official"})
    assert not any(n["class_type"] == "LoraLoaderModelOnly" for n in graph.values())
    shift_node = next(n for n in graph.values() if n["class_type"] == "MiniMaxH3SigmaShift")
    # The shift node now reads the trunk loader directly.
    assert shift_node["inputs"]["model"] == ["20", 0]
    scheduler = next(n for n in graph.values() if n["class_type"] == "BasicScheduler")
    assert scheduler["inputs"]["steps"] == 6


def test_missing_variant_uses_the_recipe_marked_default() -> None:
    WorkflowManager.reset()
    graph = WorkflowManager.get_instance().load_workflow("h3flex-t2v")
    _apply_model_variant(graph, {"model": "pika-h3-flex"})
    assert not any(n["class_type"] == "LoraLoaderModelOnly" for n in graph.values())
    scheduler = next(n for n in graph.values() if n["class_type"] == "BasicScheduler")
    assert scheduler["inputs"]["steps"] == 6


def test_ltx_requests_are_untouched() -> None:
    WorkflowManager.reset()
    graph = WorkflowManager.get_instance().load_workflow("h3flex-t2v")
    before = json.dumps(graph, sort_keys=True)
    _apply_model_variant(graph, {"mode": "t2v", "variant": "pro"})
    assert json.dumps(graph, sort_keys=True) == before
