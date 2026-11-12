"""Submit-time failures must be legible: preflight model files, reject 4xx.

ComfyUI answers a queued prompt with an opaque `value_not_in_list` when a
checkpoint is missing, and the app used to retry that request until it gave up
(`BYO_SUBMIT_EXHAUSTED`). These tests pin the two layers that replaced it:

* `missing_model_files` finds the absent files before anything is queued, and
* ComfyUI's own prompt rejection is turned into a readable sentence and a 400.
"""

from __future__ import annotations

import json
import types
from typing import Any

import pytest
import yaml

from comfyui_loovie.helpers.model_files import (
    MissingModelFile,
    describe_missing_files,
    missing_model_files,
)
from comfyui_loovie.server.routes import _create_task_handler
from comfyui_loovie.workflow_manager import (
    WorkflowManager,
    WorkflowRejected,
    describe_prompt_rejection,
)

# ---------------------------------------------------------------------
# helpers/model_files.py
# ---------------------------------------------------------------------


PRESENT = {"flux-2-klein-4b.safetensors"}


def _graph(**inputs: Any) -> dict[str, Any]:
    return {
        "20": {"class_type": "UNETLoader", "inputs": inputs},
        "34": {"class_type": "SaveImage", "inputs": {"images": ["20", 0]}},
    }


def test_missing_file_is_reported_with_node_and_folder() -> None:
    missing = missing_model_files(
        _graph(unet_name="hyperflow.gguf"), listing={"diffusion_models": PRESENT}
    )
    assert missing == [
        MissingModelFile(
            node_id="20",
            class_type="UNETLoader",
            input_name="unet_name",
            filename="hyperflow.gguf",
            folders=("diffusion_models", "unet"),
        )
    ]


def test_present_file_is_not_reported() -> None:
    assert (
        missing_model_files(
            _graph(unet_name="flux-2-klein-4b.safetensors"),
            listing={"diffusion_models": PRESENT},
        )
        == []
    )


def test_file_found_in_any_candidate_folder_passes() -> None:
    """`model_name` is shared by upscale and latent-upscale loaders."""

    graph = {"30": {"class_type": "LatentUpscaleModelLoader", "inputs": {"model_name": "up.pt"}}}
    assert (
        missing_model_files(
            graph, listing={"upscale_models": {"up.pt"}, "latent_upscale_models": set()}
        )
        == []
    )
    assert (
        missing_model_files(
            graph, listing={"upscale_models": set(), "latent_upscale_models": {"up.pt"}}
        )
        == []
    )
    assert missing_model_files(
        graph, listing={"upscale_models": set(), "latent_upscale_models": set()}
    )


def test_unknown_folder_is_never_reported() -> None:
    """No answer from ComfyUI means "cannot check", not "missing"."""

    assert (
        missing_model_files(_graph(unet_name="anything.gguf"), listing={"diffusion_models": None})
        == []
    )


def test_without_folder_paths_nothing_is_reported() -> None:
    """The CI stubs have no model registry; the preflight must stay silent."""

    assert missing_model_files(_graph(unet_name="definitely-not-installed.gguf")) == []


def test_non_file_inputs_are_ignored() -> None:
    graph = {
        "10": {
            "class_type": "LoovieTextInput",
            "inputs": {"prompt": "a cat", "negative_prompt": "blurry"},
        },
        "12": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 6}},
    }
    assert missing_model_files(graph, listing={"diffusion_models": set()}) == []


def test_message_names_the_file_and_folder() -> None:
    missing = [
        MissingModelFile("20", "HyperFlowGGUFLoader", "unet_name", "a.gguf", ("diffusion_models",))
    ]
    message = describe_missing_files(missing)
    assert "a.gguf (HyperFlowGGUFLoader)" in message
    assert "ComfyUI/models/diffusion_models/" in message


def test_message_caps_the_list() -> None:
    missing = [
        MissingModelFile(str(i), "UNETLoader", "unet_name", f"{i}.gguf", ("diffusion_models",))
        for i in range(1, 8)
    ]
    message = describe_missing_files(missing, limit=5)
    assert "5.gguf" in message
    assert "6.gguf" not in message
    assert "(+2 more)" in message


# ---------------------------------------------------------------------
# workflow_manager.describe_prompt_rejection
# ---------------------------------------------------------------------


def test_prompt_rejection_names_the_node_and_input() -> None:
    message = describe_prompt_rejection(
        {
            "error": {"type": "prompt_outputs_failed_validation", "message": "Prompt failed"},
            "node_errors": {
                "20": {
                    "class_type": "HyperFlowGGUFLoader",
                    "errors": [
                        {
                            "type": "value_not_in_list",
                            "details": "unet_name: 'x.gguf' not in []",
                        }
                    ],
                }
            },
        }
    )
    assert message == (
        "ComfyUI rejected the workflow: HyperFlowGGUFLoader (20): unet_name: 'x.gguf' not in []"
    )


def test_prompt_rejection_falls_back_to_the_top_level_error() -> None:
    message = describe_prompt_rejection({"error": {"message": "invalid prompt"}})
    assert message == "ComfyUI rejected the workflow: invalid prompt"


def test_prompt_rejection_without_details_still_reads() -> None:
    assert describe_prompt_rejection({}) == "ComfyUI rejected the workflow"


# ---------------------------------------------------------------------
# Route layer: 400 + fail_code instead of a retryable 503.
# ---------------------------------------------------------------------


class _FakeTransport:
    def get_extra_info(self, name: str) -> Any:
        return ("127.0.0.1", 50000) if name == "peername" else None


class _FakeRequest:
    """Just enough of an aiohttp request for the create handler."""

    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body
        self.headers: dict[str, str] = {}
        self.path = "/images/create"
        self.rel_url = types.SimpleNamespace(query={})
        self.scheme = "http"
        self.host = "127.0.0.1"
        self.transport = _FakeTransport()

    async def json(self) -> dict[str, Any]:
        return self._body


def _write_config(tmp_path: Any, graph: dict[str, Any], name: str = "test-t2i") -> None:
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "test.json").write_text(json.dumps(graph))
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "api_token": "",
                "models": {"enabled": {"image": ["test"]}},
                "workflows": {name: {"file": "workflows/test.json"}},
            }
        )
    )


async def _create(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, body: dict[str, Any], graph: dict[str, Any]
) -> Any:
    _write_config(tmp_path, graph)
    monkeypatch.setattr("comfyui_loovie.workflow_manager._package_root", lambda: tmp_path)
    WorkflowManager.reset()
    return await _create_task_handler(
        _FakeRequest(body),
        default_workflow="test-t2i",
        modality="image",
        resolve_name=lambda _body, default: default,
    )


@pytest.mark.asyncio
async def test_missing_model_file_returns_400_model_files_missing(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "comfyui_loovie.helpers.model_files._folder_listing",
        lambda folder: {"installed.safetensors"},
    )
    response = await _create(
        tmp_path,
        monkeypatch,
        {"prompt": "a paper boat"},
        _graph(unet_name="hyperflow_flash.gguf"),
    )
    assert response.status == 400
    body = json.loads(response.body)
    assert body["fail_code"] == "MODEL_FILES_MISSING"
    assert "hyperflow_flash.gguf (UNETLoader)" in body["msg"]


@pytest.mark.asyncio
async def test_comfyui_rejection_returns_400_workflow_rejected(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "comfyui_loovie.helpers.model_files._folder_listing",
        lambda folder: {"installed.safetensors"},
    )

    async def _reject(self: Any, _graph_json: dict[str, Any]) -> str:
        raise WorkflowRejected(
            "ComfyUI rejected the workflow: VAELoader (22): vae_name: 'x' not in []"
        )

    monkeypatch.setattr(WorkflowManager, "submit_workflow", _reject)
    response = await _create(
        tmp_path,
        monkeypatch,
        {"prompt": "a paper boat"},
        _graph(unet_name="installed.safetensors"),
    )
    assert response.status == 400
    body = json.loads(response.body)
    assert body["fail_code"] == "WORKFLOW_REJECTED"
    assert "VAELoader (22)" in body["msg"]
