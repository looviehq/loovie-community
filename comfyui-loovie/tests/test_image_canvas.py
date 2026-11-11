"""Canvas selection and workflow wiring for resolution-scaled image models.

Two invariants live here:

* only models that opt in (`ModelSpec.resolution_scales_canvas`) turn the
  request's `resolution` into a bigger canvas, and
* every shipped image graph carries the `resolution` input the route injects,
  so a null/absent value can never silently fall back to a stale default.

The MiniMax H3 Image graphs get their own assertions because their shape is
unusual: the conditioning node owns the latent, and the reference pictures ride
`images.image_N` instead of the returned LATENT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from comfyui_loovie.models import (
    CATALOG,
    DEFAULT_SCALED_IMAGE_RESOLUTION,
    available_models,
    image_canvas_resolution,
)
from comfyui_loovie.nodes.loovie_image_input import LoovieImageInput
from comfyui_loovie.nodes.loovie_settings import LoovieSettings
from comfyui_loovie.server.routes import _inject_inputs

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / "comfyui-loovie" / "workflows"
H3_T2I = WORKFLOWS / "minimax_h3_image_t2i.json"
H3_I2I = WORKFLOWS / "minimax_h3_image_i2i.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _h3_spec():
    return next(
        spec
        for spec in available_models({}, ["minimax-h3-image-t2i", "minimax-h3-image-i2i"])
        if spec.id == "minimax-h3-image"
    )


def _non_scaling_image_spec():
    return next(
        spec
        for spec in available_models({}, ["krea-2-t2i-turbo", "flux-2-klein"])
        if spec.modality == "image"
    )


# ---------------------------------------------------------------------
# Model -> canvas resolution.
# ---------------------------------------------------------------------


@pytest.mark.parametrize("requested", ["1K", "2K", "4K"])
def test_opted_in_models_honour_the_requested_resolution(requested: str) -> None:
    assert image_canvas_resolution(_h3_spec(), requested) == requested


def test_opted_in_models_default_to_the_mid_canvas() -> None:
    assert image_canvas_resolution(_h3_spec(), None) == DEFAULT_SCALED_IMAGE_RESOLUTION
    assert image_canvas_resolution(_h3_spec(), "") == DEFAULT_SCALED_IMAGE_RESOLUTION


def test_opted_in_models_ignore_an_unknown_resolution() -> None:
    assert image_canvas_resolution(_h3_spec(), "8K") == DEFAULT_SCALED_IMAGE_RESOLUTION


def test_legacy_models_keep_the_fixed_table() -> None:
    assert image_canvas_resolution(_non_scaling_image_spec(), "4K") == "auto"


# ---------------------------------------------------------------------
# Route injection.
# ---------------------------------------------------------------------


def test_route_injects_the_resolution_into_the_settings_node() -> None:
    workflow = _load(H3_T2I)
    _inject_inputs(
        workflow,
        {"prompt": "a fox", "aspect_ratio": "1:1", "seed": 7, "_loovie_image_resolution": "4K"},
    )
    settings = next(n for n in workflow.values() if n["class_type"] == "LoovieSettings")
    assert settings["inputs"]["resolution"] == "4K"
    assert settings["inputs"]["aspect_ratio"] == "1:1"
    assert settings["inputs"]["seed"] == 7


def test_route_leaves_the_canvas_alone_when_no_marker_is_sent() -> None:
    """Music/SFX and hand-built graphs must not gain a surprise canvas scale."""

    workflow = _load(H3_T2I)
    _inject_inputs(workflow, {"prompt": "a fox"})
    settings = next(n for n in workflow.values() if n["class_type"] == "LoovieSettings")
    assert settings["inputs"]["resolution"] == "auto"


def test_loovie_settings_processes_each_resolution() -> None:
    node = LoovieSettings()
    assert node.process("1:1", 1, "2K") == (2048, 2048, 1)
    assert node.process("16:9", 1, "1K") == (1376, 768, 1)
    assert node.process("1:1", 1) == (768, 768, 1)


# ---------------------------------------------------------------------
# Shipped workflow JSON.
# ---------------------------------------------------------------------


def test_every_image_settings_node_declares_a_resolution() -> None:
    for path in sorted(WORKFLOWS.glob("*.json")):
        workflow = _load(path)
        for node in workflow.values():
            if node.get("class_type") != "LoovieSettings":
                continue
            inputs = node["inputs"]
            assert "resolution" in inputs, path.name
            assert inputs["resolution"] in {"auto", "1K", "2K", "4K"}, path.name


def test_minimax_h3_image_t2i_graph_matches_the_distilled_recipe() -> None:
    workflow = _load(H3_T2I)
    by_class = {node["class_type"]: node for node in workflow.values()}

    sampler = by_class["KSampler"]["inputs"]
    assert sampler["steps"] == 6
    assert sampler["cfg"] == 1.0
    assert sampler["sampler_name"] == "euler"
    assert sampler["scheduler"] == "simple"
    assert sampler["denoise"] == 1.0

    assert by_class["UNETLoader"]["inputs"]["unet_name"] == (
        "minimax_h3_image_pruned_int8_convrot.safetensors"
    )
    assert by_class["CLIPLoader"]["inputs"]["type"] == "minimax"
    assert by_class["VAELoader"]["inputs"]["vae_name"] == ("minimax_h3_image_vae_fp16.safetensors")
    # Guidance is 1, so there is no second encode pass: the grounding node owns
    # both the conditioning and the latent.
    assert "LoovieImageInput" not in by_class
    assert "MiniMaxH3ImageConditioning" in by_class


def test_minimax_h3_image_i2i_graph_carries_references_not_a_target_latent() -> None:
    workflow = _load(H3_I2I)
    by_class = {node["class_type"]: node for node in workflow.values()}

    image_input = by_class["LoovieImageInput"]
    assert image_input["inputs"]["latent_type"] == "h3image"

    image_input_id = next(
        node_id for node_id, node in workflow.items() if node["class_type"] == "LoovieImageInput"
    )
    conditioning = by_class["MiniMaxH3ImageConditioning"]["inputs"]
    # IMAGE_N is the transport: LoovieImageInput returns IMAGE_n on slot
    # 2n + 3 (each IMAGE_n/LATENT_n pair), and H3 Image wires all sixteen.
    for index in range(1, 17):
        assert conditioning[f"images.image_{index}"] == [image_input_id, 2 * index + 3]

    # The sampler samples the conditioning node's latent, never an encoded
    # copy of the first picture.
    assert by_class["KSampler"]["inputs"]["latent_image"] == ["30", 1]
    assert by_class["KSampler"]["inputs"]["positive"] == ["30", 0]


def test_image_input_exposes_enough_reference_slots() -> None:
    """Every model's advertised reference count must fit in the node's outputs."""

    slots = [
        name
        for name in LoovieImageInput.RETURN_NAMES
        if name.startswith("IMAGE_") and name[6:].isdigit()
    ]
    widest = max(spec.reference_count for spec in CATALOG if spec.modality == "image")
    assert len(slots) >= widest
    assert len(slots) == len(LoovieImageInput.INPUT_TYPES()["optional"]) - 2  # vae + mask


def _reference_slots(workflow: dict[str, Any]) -> int:
    """How many reference pictures a graph actually wires into its encoder."""

    latent_chain = sum(1 for node in workflow.values() if node["class_type"] == "ReferenceLatent")
    encoded = max(
        (
            sum(1 for key in node["inputs"] if key.startswith("images.image_"))
            for node in workflow.values()
            if "inputs" in node
        ),
        default=0,
    )
    return max(latent_chain, encoded)


@pytest.mark.parametrize(
    ("filename", "model_id"),
    [
        ("flux_2_klein.json", "flux-2-klein"),
        ("flux_3_klein_i2i_distilled.json", "flux-3-klein"),
        ("qwen_image_2_1_i2i_turbo.json", "qwen-image-2.1"),
        ("minimax_h3_image_i2i.json", "minimax-h3-image"),
    ],
)
def test_reference_slots_match_the_catalogue(filename: str, model_id: str) -> None:
    """The graph must carry exactly the count the model advertises."""

    spec = next(spec for spec in CATALOG if spec.id == model_id)
    workflow = _load(WORKFLOWS / filename)
    assert _reference_slots(workflow) == spec.reference_count


def test_route_fills_only_the_slots_the_graph_declares() -> None:
    workflow = _load(H3_I2I)
    urls = [f"https://example.com/{i}.png" for i in range(1, 20)]
    _inject_inputs(workflow, {"prompt": "x", "image_urls": urls})
    image_input = next(n for n in workflow.values() if n["class_type"] == "LoovieImageInput")
    filled = [k for k, v in image_input["inputs"].items() if k.startswith("image_url_") and v]
    assert len(filled) == 16
    assert "image_url_17" not in image_input["inputs"]


def test_route_reserves_the_last_slot_for_a_mask() -> None:
    workflow = _load(H3_I2I)
    urls = [f"https://example.com/{i}.png" for i in range(1, 20)]
    _inject_inputs(
        workflow, {"prompt": "x", "image_urls": urls, "mask_url": "https://example.com/m.png"}
    )
    image_input = next(n for n in workflow.values() if n["class_type"] == "LoovieImageInput")
    filled = [k for k, v in image_input["inputs"].items() if k.startswith("image_url_") and v]
    assert len(filled) == 15
    assert image_input["inputs"]["mask_url"] == "https://example.com/m.png"


def test_resolution_stays_an_optional_input() -> None:
    """A required input would break every older workflow JSON at load time."""

    inputs = LoovieSettings.INPUT_TYPES()
    assert "resolution" in inputs["optional"]
    assert "resolution" not in inputs["required"]
    assert "auto" in inputs["optional"]["resolution"][0]
