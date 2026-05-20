"""Shared fixtures for the comfyui-loovie test suite.

Two responsibilities:

1.  **Stub ComfyUI's runtime modules** (`server`, `folder_paths`) so the
    package under test can be imported in a plain CI environment that
    does not have ComfyUI installed. Done at the top so it runs BEFORE
    any test module imports `comfyui_loovie.*`.

2.  **Reset module-level singletons** between tests (`WorkflowManager`,
    `TaskStore`) so each test starts from a known state.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator

import pytest

# ----------------------------------------------------------------------
# Stub ComfyUI runtime modules.
# ----------------------------------------------------------------------


def _install_stub_modules() -> None:
    """Install minimal stand-ins for ComfyUI's runtime modules.

    The package under test imports `server`, `folder_paths`,
    `comfy.cli_args`, plus the heavy ML stack (`torch`, `numpy`, `PIL`)
    at module top-level. None of those exist in a plain CI environment
    and installing real torch just to import a module would balloon CI
    from seconds to minutes. We expose the bare minimum surface area
    the package touches at IMPORT time; tests do not exercise tensor
    logic so the runtime method bodies of the node classes never run.
    """

    # --- ComfyUI runtime stubs ---------------------------------------

    if "server" not in sys.modules:
        server_mod = types.ModuleType("server")

        class _FakeRoutes:
            def get(self, _path: str):
                def _decorator(fn):
                    return fn

                return _decorator

            def post(self, _path: str):
                def _decorator(fn):
                    return fn

                return _decorator

        class _FakePromptServer:
            instance = types.SimpleNamespace(routes=_FakeRoutes(), port=8188)

        server_mod.PromptServer = _FakePromptServer  # type: ignore[attr-defined]
        sys.modules["server"] = server_mod

    if "folder_paths" not in sys.modules:
        fp_mod = types.ModuleType("folder_paths")
        fp_mod.get_input_directory = lambda: "input"  # type: ignore[attr-defined]
        sys.modules["folder_paths"] = fp_mod

    if "comfy" not in sys.modules:
        comfy_mod = types.ModuleType("comfy")
        cli_mod = types.ModuleType("comfy.cli_args")
        cli_mod.args = types.SimpleNamespace(port=8188)  # type: ignore[attr-defined]
        sys.modules["comfy"] = comfy_mod
        sys.modules["comfy.cli_args"] = cli_mod

    # --- ML stack stubs (torch, numpy, Pillow) -----------------------

    if "torch" not in sys.modules:
        torch_mod = types.ModuleType("torch")
        torch_mod.Tensor = type("Tensor", (), {})  # type: ignore[attr-defined]
        torch_mod.float32 = "float32"  # type: ignore[attr-defined]
        torch_mod.zeros = lambda *_a, **_k: None  # type: ignore[attr-defined]
        torch_mod.from_numpy = lambda x: x  # type: ignore[attr-defined]
        torch_mod.cat = lambda *_a, **_k: None  # type: ignore[attr-defined]
        torch_mod.stack = lambda *_a, **_k: None  # type: ignore[attr-defined]
        torch_mod.nn = types.SimpleNamespace(functional=types.SimpleNamespace())  # type: ignore[attr-defined]
        sys.modules["torch"] = torch_mod

    if "numpy" not in sys.modules:
        np_mod = types.ModuleType("numpy")
        np_mod.ndarray = type("ndarray", (), {})  # type: ignore[attr-defined]
        np_mod.float32 = "float32"  # type: ignore[attr-defined]
        np_mod.uint8 = "uint8"  # type: ignore[attr-defined]
        np_mod.array = lambda *_a, **_k: None  # type: ignore[attr-defined]
        np_mod.asarray = lambda *_a, **_k: None  # type: ignore[attr-defined]
        np_mod.zeros = lambda *_a, **_k: None  # type: ignore[attr-defined]
        sys.modules["numpy"] = np_mod

    if "PIL" not in sys.modules:
        pil_mod = types.ModuleType("PIL")
        image_mod = types.ModuleType("PIL.Image")
        image_mod.Image = type("Image", (), {})  # type: ignore[attr-defined]
        image_mod.open = lambda *_a, **_k: None  # type: ignore[attr-defined]
        image_mod.new = lambda *_a, **_k: None  # type: ignore[attr-defined]
        image_ops_mod = types.ModuleType("PIL.ImageOps")
        image_ops_mod.exif_transpose = lambda x: x  # type: ignore[attr-defined]
        pil_mod.Image = image_mod  # type: ignore[attr-defined]
        pil_mod.ImageOps = image_ops_mod  # type: ignore[attr-defined]
        sys.modules["PIL"] = pil_mod
        sys.modules["PIL.Image"] = image_mod
        sys.modules["PIL.ImageOps"] = image_ops_mod


_install_stub_modules()


# ----------------------------------------------------------------------
# Singleton reset.
# ----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons() -> Iterator[None]:
    """Drop module-level singletons between tests."""
    yield
    try:
        from comfyui_loovie.task_store import TaskStore

        TaskStore.reset()
    except Exception:  # pragma: no cover - defensive
        pass

    try:
        from comfyui_loovie.workflow_manager import WorkflowManager

        WorkflowManager.reset()
    except Exception:  # pragma: no cover - defensive
        pass


# ----------------------------------------------------------------------
# Magic-byte fixtures used by validator + image_cache tests.
# ----------------------------------------------------------------------


@pytest.fixture
def png_bytes() -> bytes:
    """Minimal byte sequence that satisfies the PNG magic-bytes check."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 32


@pytest.fixture
def webp_bytes() -> bytes:
    # RIFF<4 bytes size>WEBPVP8...
    return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"VP8 " + b"\x00" * 32


@pytest.fixture
def mp4_bytes() -> bytes:
    # 'ftyp' atom at offset 4. Header size encoded in the first 4 bytes
    # is irrelevant for sniffing; just the offset-4 marker matters.
    return b"\x00\x00\x00\x20ftypisom" + b"\x00" * 32


@pytest.fixture
def webm_bytes() -> bytes:
    # EBML magic.
    return b"\x1a\x45\xdf\xa3" + b"\x00" * 32


@pytest.fixture
def gif_bytes() -> bytes:
    return b"GIF89a" + b"\x00" * 32


@pytest.fixture
def random_bytes() -> bytes:
    """Bytes that do NOT match any supported magic."""
    return b"NotARealImage" * 16
