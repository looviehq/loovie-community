"""Loovie ComfyUI extension.

Registers HTTP routes implementing the Loovie BYO server contract on
ComfyUI's built-in aiohttp server, plus a small set of `loovie/` category
nodes used by the shipped workflows.

The OpenAPI document at `openapi/loovie-server.openapi.yaml` is the
authoritative description of the HTTP surface.
"""

from __future__ import annotations

from .helpers import compat as _compat  # noqa: F401  install patches at import
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .server import routes as _routes  # noqa: F401  register aiohttp routes

WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
