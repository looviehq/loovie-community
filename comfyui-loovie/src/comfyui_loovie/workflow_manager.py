"""Workflow template loading and submission to ComfyUI's `/prompt` API.

Singleton that reads `config.yaml`, indexes the registered workflows, and
owns the bearer-token accessor used by the route layer for fail-closed
auth. Workflow JSON templates are cached after first load; each call to
`load_workflow` returns a deep copy so callers can freely mutate the
graph before submitting it.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("comfyui_loovie.workflow_manager")

CONFIG_FILENAME = "config.yaml"


def _package_root() -> Path:
    """Return the package root (the directory containing `config.yaml`)."""
    # src/comfyui_loovie/workflow_manager.py -> repo root (comfyui-loovie/)
    return Path(__file__).resolve().parents[2]


def _detect_comfy_port() -> int | None:
    """Best-effort lookup of ComfyUI's listen port.

    The extension is loaded into ComfyUI's process, so it can read the
    parsed `--port` CLI arg directly. This lets a standalone ComfyUI
    install (no env vars, no reverse proxy) work without configuration.
    """
    try:
        from comfy.cli_args import args  # type: ignore[import-not-found]

        port = getattr(args, "port", None)
        if isinstance(port, int) and port > 0:
            return port
    except Exception:
        pass
    try:
        import server  # type: ignore[import-not-found]

        instance = getattr(server.PromptServer, "instance", None)
        port = getattr(instance, "port", None)
        if isinstance(port, int) and port > 0:
            return port
    except Exception:
        pass
    return None


class WorkflowManager:
    """Singleton config + workflow registry."""

    _instance: WorkflowManager | None = None

    def __init__(self) -> None:
        self._package_dir = _package_root()
        self._config: dict[str, Any] = self._load_config()
        self._template_cache: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> WorkflowManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Drop the singleton (used by tests and on config reload)."""
        cls._instance = None

    # --- URLs -----------------------------------------------------------

    @property
    def comfy_api_url(self) -> str:
        """Internal URL the extension uses to reach ComfyUI's own routes."""
        explicit = self._config.get("comfy_api_url")
        if explicit:
            return str(explicit).rstrip("/")
        env_url = os.environ.get("LOOVIE_COMFY_INTERNAL_URL")
        if env_url:
            return env_url.rstrip("/")
        env_port = os.environ.get("COMFYUI_PORT")
        if env_port:
            return f"http://127.0.0.1:{env_port}"
        port = _detect_comfy_port() or 8188
        return f"http://127.0.0.1:{port}"

    @property
    def output_base_url(self) -> str:
        """Default public-facing base URL returned in result URLs.

        Overridden at request time by the inbound `Host` header or
        deployment env vars (see `server.routes`).
        """
        return str(self._config.get("output_base_url", "http://127.0.0.1:8188"))

    # --- timing ---------------------------------------------------------

    @property
    def max_wait_seconds(self) -> int:
        return int(self._config.get("max_wait_seconds", 300))

    def get_max_wait_seconds(self, workflow_name: str | None) -> int:
        """Per-workflow max-wait override, falling back to the global default."""
        default = self.max_wait_seconds
        if not workflow_name:
            return default
        wf = self._config.get("workflows", {}).get(workflow_name)
        if isinstance(wf, dict):
            override = wf.get("max_wait_seconds")
            if isinstance(override, int) and override > 0:
                return override
        return default

    @property
    def poll_interval_seconds(self) -> int:
        return int(self._config.get("poll_interval_seconds", 2))

    # --- auth -----------------------------------------------------------

    @property
    def api_token(self) -> str:
        """Bearer token used to authorise remote callers.

        Resolution: `LOOVIE_API_TOKEN` env var first, then `config.yaml`.
        An empty string means no token is configured and the server is in
        fail-closed mode (see `server.routes._check_auth`).
        """
        env_tok = (os.environ.get("LOOVIE_API_TOKEN") or "").strip()
        if env_tok:
            return env_tok
        return str(self._config.get("api_token", "")).strip()

    # --- workflow registry ---------------------------------------------

    def _load_config(self) -> dict[str, Any]:
        config_path = self._package_dir / CONFIG_FILENAME
        if not config_path.exists():
            logger.warning(
                "Config file not found at %s; using empty workflow registry",
                config_path,
            )
            return {"workflows": {}}
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{config_path} must contain a YAML mapping")
        data.setdefault("workflows", {})
        return data

    def get_workflow_names(self) -> list[str]:
        return list(self._config.get("workflows", {}).keys())

    def load_workflow(self, workflow_name: str) -> dict[str, Any]:
        """Load a workflow template by registered name and return a deep copy."""
        if workflow_name in self._template_cache:
            return copy.deepcopy(self._template_cache[workflow_name])

        workflows = self._config.get("workflows", {})
        wf_config = workflows.get(workflow_name)
        if not isinstance(wf_config, dict):
            raise ValueError(f"Unknown workflow: {workflow_name}")

        template_path = self._package_dir / wf_config["file"]
        if not template_path.exists():
            raise FileNotFoundError(f"Workflow template not found: {template_path}")

        with open(template_path) as f:
            template = json.load(f)

        self._template_cache[workflow_name] = template
        return copy.deepcopy(template)

    async def submit_workflow(self, workflow_json: dict[str, Any]) -> str:
        """POST a workflow to ComfyUI `/prompt` and return its `prompt_id`.

        Top-level keys starting with `_` are stripped before submission
        (ComfyUI rejects unknown top-level nodes, so a `_meta` doc block
        would crash the queue).
        """
        import aiohttp

        cleaned = {k: v for k, v in workflow_json.items() if not k.startswith("_")}
        payload = {"prompt": cleaned}
        url = f"{self.comfy_api_url}/prompt"

        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp,
        ):
            result = await resp.json()
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI /prompt returned no prompt_id: {result}")
            logger.info("Submitted workflow, prompt_id=%s", prompt_id)
            return str(prompt_id)
