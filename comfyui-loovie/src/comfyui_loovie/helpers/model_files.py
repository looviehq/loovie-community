"""Check that a workflow's model files actually exist before submitting it.

ComfyUI validates model file dropdowns when a prompt is queued, so a missing
checkpoint surfaces as an opaque `value_not_in_list` rejection after the app
has already retried a few times. The route layer runs this preflight first, so
the caller gets one actionable answer ("this server is missing X") instead of a
generic "try again".

Folder names follow ComfyUI's `folder_paths` registry. An input may resolve from
more than one folder (upscalers, text encoders); the file is accepted from any
of them. Anything the registry cannot answer — a custom loader with a folder we
do not know, or a test process without ComfyUI — is skipped rather than
reported, so this can never invent a failure.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("comfyui_loovie.helpers.model_files")

#: Loader inputs that name a downloadable model file, and the ComfyUI folders
#: that can satisfy them.
MODEL_FILE_INPUTS: dict[str, tuple[str, ...]] = {
    "unet_name": ("diffusion_models", "unet"),
    "ckpt_name": ("checkpoints",),
    "clip_name": ("text_encoders", "clip"),
    "clip_name1": ("text_encoders", "clip"),
    "clip_name2": ("text_encoders", "clip"),
    "clip_name3": ("text_encoders", "clip"),
    "vae_name": ("vae",),
    "lora_name": ("loras",),
    "control_net_name": ("controlnet",),
    "style_model_name": ("style_models",),
    "upscale_model_name": ("upscale_models",),
    # `UpscaleModelLoader` and `LatentUpscaleModelLoader` both call it
    # `model_name`; either folder can satisfy it.
    "model_name": ("upscale_models", "latent_upscale_models"),
}


@dataclass(frozen=True)
class MissingModelFile:
    """One model file a workflow needs that this server does not have."""

    node_id: str
    class_type: str
    input_name: str
    filename: str
    folders: tuple[str, ...]

    def describe(self) -> str:
        return f"{self.filename} ({self.class_type})"


def _node_sort_key(node_id: str) -> tuple[int, str]:
    return (int(node_id), "") if node_id.isdigit() else (2**31, node_id)


def _folder_listing(folder: str) -> set[str] | None:
    """File names ComfyUI can see in `folder`, or None when it cannot say."""

    try:
        import folder_paths
    except ImportError:  # pragma: no cover - ComfyUI is the only real runtime
        return None
    getter = getattr(folder_paths, "get_filename_list", None)
    if getter is None:  # pragma: no cover - defensive, older ComfyUI builds
        return None
    try:
        return set(getter(folder))
    except Exception:  # an unregistered folder just means "unchecked"
        logger.debug("Folder %s is not registered with ComfyUI; skipping", folder)
        return None


def _is_model_file_input(input_name: str, value: Any) -> bool:
    return input_name in MODEL_FILE_INPUTS and isinstance(value, str) and bool(value.strip())


def missing_model_files(
    workflow: Mapping[str, Any],
    *,
    listing: Mapping[str, set[str] | None] | None = None,
) -> list[MissingModelFile]:
    """Return the model files a workflow needs that are not installed here.

    `listing` lets callers (and tests) inject folder contents; by default each
    folder is resolved through ComfyUI's `folder_paths`.
    """

    resolved: dict[str, set[str] | None] = dict(listing or {})
    missing: list[MissingModelFile] = []

    for node_id in sorted(workflow, key=_node_sort_key):
        node = workflow[node_id]
        if not isinstance(node, Mapping):
            continue
        class_type = str(node.get("class_type", ""))
        inputs = node.get("inputs")
        if not isinstance(inputs, Mapping):
            continue
        for input_name, value in inputs.items():
            if not _is_model_file_input(input_name, value):
                continue
            folders = MODEL_FILE_INPUTS[input_name]
            filename = str(value).strip()
            checked = False
            found = False
            for folder in folders:
                if folder not in resolved:
                    resolved[folder] = _folder_listing(folder)
                names = resolved[folder]
                if names is None:
                    continue
                checked = True
                if filename in names:
                    found = True
                    break
            if checked and not found:
                missing.append(
                    MissingModelFile(
                        node_id=str(node_id),
                        class_type=class_type,
                        input_name=input_name,
                        filename=filename,
                        folders=folders,
                    )
                )

    return missing


def describe_missing_files(missing: Iterable[MissingModelFile], *, limit: int = 5) -> str:
    """One sentence naming what is missing, capped so it stays readable."""

    items = list(missing)
    shown = ", ".join(item.describe() for item in items[:limit])
    extra = "" if len(items) <= limit else f" (+{len(items) - limit} more)"
    primary = sorted({item.folders[0] for item in items})
    where = f" into ComfyUI/models/{primary[0]}/" if len(primary) == 1 else ""
    return (
        f"Model files are not installed on this server: {shown}{extra}."
        f" Download them{where} and retry."
    )
