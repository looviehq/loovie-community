"""Workflow resolution and shipped-graph integrity for FLUX 3 / MOSS-Image."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from comfyui_loovie.workflow_manager import WorkflowManager

WORKFLOWS = Path(__file__).resolve().parents[1] / "workflows"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"mode": "t2i"}, "flux-3-klein"),
        ({"mode": "i2i"}, "flux-3-klein-edit"),
        ({"mode": "t2i", "image_model": "moss-image"}, "moss-image"),
        ({"mode": "t2v", "variant": "fast"}, "ltx25-t2v-fast"),
        ({"mode": "t2v", "variant": "fast", "image_model": "moss-image"}, "ltx25-t2v-moss-fast"),
        ({"mode": "t2v", "variant": "pro", "image_model": "moss-image"}, "ltx25-t2v-moss-pro"),
        ({"mode": "i2v", "variant": "fast", "image_model": "moss-image"}, "ltx25-i2v-fast"),
        ({"workflow": "moss-image", "mode": "i2i"}, "moss-image"),
    ],
)
def test_resolve_workflow_name(body: dict[str, str], expected: str) -> None:
    from comfyui_loovie.server.routes import _resolve_workflow_name

    assert _resolve_workflow_name(body, "") == expected


def test_negative_prompt_keeps_workflow_default_when_unset() -> None:
    from comfyui_loovie.server.routes import _inject_inputs

    wf = {"1": {"class_type": "LoovieTextInput", "inputs": {"prompt": "", "negative_prompt": "dflt"}}}
    _inject_inputs(wf, {"prompt": "p"})
    assert wf["1"]["inputs"]["negative_prompt"] == "dflt"
    _inject_inputs(wf, {"prompt": "p", "negative_prompt": "mine"})
    assert wf["1"]["inputs"]["negative_prompt"] == "mine"


def test_registered_image_and_moss_workflows_exist() -> None:
    WorkflowManager.reset()
    names = WorkflowManager.get_instance().get_workflow_names()
    for name in ("flux-3-klein", "flux-3-klein-edit", "moss-image", "ltx25-t2v-moss-fast", "ltx25-t2v-moss-pro"):
        assert name in names
    assert "flux-2-klein" not in names


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.json")), ids=lambda p: p.name)
def test_workflow_links_resolve(path: Path) -> None:
    graph = json.loads(path.read_text())
    for node_id, node in graph.items():
        for key, value in node["inputs"].items():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                assert value[0] in graph, f"{path.name}: {node_id}.{key} -> missing node {value[0]}"


def test_moss_t2v_takes_first_frame_from_moss_not_url_input() -> None:
    graph = json.loads((WORKFLOWS / "ltx25_t2v_moss_fast.json").read_text())
    assert not any(n["class_type"] == "LoovieImageInput" for n in graph.values())
    assert graph["25"]["inputs"]["input"] == ["m54", 0]
