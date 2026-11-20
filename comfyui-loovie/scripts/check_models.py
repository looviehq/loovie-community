#!/usr/bin/env python3
"""Report enabled workflows whose model files are not installed.

The server already rejects a request with `MODEL_FILES_MISSING` before it
queues the job, but that only helps once the app has made a request. This
script runs the same check at startup, so an operator sees what to download
before opening the app.

Usage:
    python scripts/check_models.py
    python scripts/check_models.py --models-root /path/to/ComfyUI/models
    python scripts/check_models.py --all-workflows

Exit status is 0 unless `--strict` is passed and files are missing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DEFAULT_CONFIG = ROOT / "config.yaml"
DEFAULT_MANIFEST = REPO / "docker" / "models.manifest"
CONTAINER_MANIFEST = Path("/opt/comfyui/loovie-models.manifest")


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_MODEL_FILES = _load_module(
    "loovie_model_files", ROOT / "src" / "comfyui_loovie" / "helpers" / "model_files.py"
)
_MODELS = _load_module("loovie_models", ROOT / "src" / "comfyui_loovie" / "models.py")


def _log(message: str) -> None:
    print(f"[loovie-models] {message}")


def _resolve_models_root(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("LOOVIE_MODELS_ROOT")
    if env:
        return Path(env).expanduser()

    # Docs layout: ComfyUI/loovie-community/comfyui-loovie
    for comfy_dir in (REPO.parent, REPO.parent / "ComfyUI", Path.cwd()):
        if (comfy_dir / "main.py").is_file():
            return comfy_dir / "models"
    return None


def _resolve_manifest(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser()
    for candidate in (DEFAULT_MANIFEST, CONTAINER_MANIFEST):
        if candidate.is_file():
            return candidate
    return None


def _manifest_models(path: Path | None) -> dict[str, set[str]]:
    """Map a local filename to the manifest model id(s) that provide it."""

    by_file: dict[str, set[str]] = {}
    if path is None:
        return by_file
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 5:
            continue
        local_name = fields[3].strip()
        model = fields[5].strip() if len(fields) > 5 else ""
        if local_name:
            by_file.setdefault(local_name, set())
            if model:
                by_file[local_name].add(model)
    return by_file


def _folder_listing(models_root: Path) -> dict[str, set[str]]:
    listing: dict[str, set[str]] = {}
    for folders in _MODEL_FILES.MODEL_FILE_INPUTS.values():
        for folder in folders:
            if folder in listing:
                continue
            root = models_root / folder
            names: set[str] = set()
            if root.is_dir():
                for path in root.rglob("*"):
                    if path.is_file():
                        names.add(path.relative_to(root).as_posix())
            listing[folder] = names
    return listing


def _workflow_path(config: Mapping[str, Any], name: str) -> Path:
    entry = config.get("workflows", {}).get(name)
    relative = entry.get("file") if isinstance(entry, Mapping) else None
    if isinstance(relative, str) and relative.strip():
        return ROOT / relative.strip()
    return ROOT / "workflows" / f"{name}.json"


def _enabled_workflows(config: Mapping[str, Any], *, all_workflows: bool) -> dict[str, str]:
    """Workflow name -> owning model id, filtered to enabled models."""

    registered_entries = config.get("workflows")
    registered = (
        {str(name) for name in registered_entries}
        if isinstance(registered_entries, Mapping)
        else set()
    )
    if all_workflows:
        owners = {name: "" for name in registered}
        for spec in _MODELS.CATALOG:
            for workflow in spec.workflows.values():
                if workflow in owners:
                    owners[workflow] = spec.id
        return owners

    owners: dict[str, str] = {}
    for spec in _MODELS.available_models(config, registered):
        for workflow in spec.workflows.values():
            if workflow in registered:
                owners[workflow] = spec.id
    return owners


def check(
    *,
    config_path: Path,
    manifest_path: Path | None,
    models_root: Path,
    all_workflows: bool,
) -> list[dict[str, Any]]:
    try:
        import yaml
    except ImportError:
        _log("PyYAML is not installed; skipping model check.")
        return []

    config = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(config, Mapping):
        _log(f"{config_path} is not a mapping; skipping model check.")
        return []

    listing = _folder_listing(models_root)
    missing_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()

    for name, owner in sorted(_enabled_workflows(config, all_workflows=all_workflows).items()):
        path = _workflow_path(config, name)
        if not path.is_file():
            missing_rows.append(
                {
                    "model": owner,
                    "workflow": name,
                    "filename": path.name,
                    "folders": (),
                    "detail": f"workflow file not found at {path}",
                }
            )
            continue
        try:
            workflow = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            _log(f"Cannot read {path}: {exc}")
            continue
        for item in _MODEL_FILES.missing_model_files(workflow, listing=listing):
            key = (owner, item.filename, item.folders)
            if key in seen:
                continue
            seen.add(key)
            missing_rows.append(
                {
                    "model": owner,
                    "workflow": name,
                    "filename": item.filename,
                    "folders": item.folders,
                    "class_type": item.class_type,
                    "input_name": item.input_name,
                    "detail": "",
                }
            )
    return missing_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-root", help="ComfyUI models directory")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="config.yaml path")
    parser.add_argument("--manifest", help="models.manifest path")
    parser.add_argument(
        "--all-workflows",
        action="store_true",
        help="check every registered workflow, including disabled models",
    )
    parser.add_argument("--strict", action="store_true", help="exit 1 when model files are missing")
    args = parser.parse_args()

    models_root = _resolve_models_root(args.models_root)
    if models_root is None:
        _log("Cannot find ComfyUI/models; pass --models-root or set LOOVIE_MODELS_ROOT.")
        return 0 if not args.strict else 2
    manifest_path = _resolve_manifest(args.manifest)

    missing = check(
        config_path=Path(args.config),
        manifest_path=manifest_path,
        models_root=models_root,
        all_workflows=args.all_workflows,
    )
    if not missing:
        _log(f"All enabled workflow model files are present under {models_root}.")
        return 0

    _log(f"Missing model files under {models_root}:")
    download_models: set[str] = set()
    manifest = _manifest_models(manifest_path)
    for row in missing:
        owner = row["model"] or "(any model)"
        where = f" -> models/{row['folders'][0]}/" if row["folders"] else ""
        detail = row["detail"] or f"[{row.get('class_type')}.{row.get('input_name')}]"
        _log(f"  {owner}: {row['filename']}{where}  {detail}")
        download_models.update(manifest.get(row["filename"], set()))

    if download_models:
        models = ",".join(sorted(download_models))
        _log("Download the missing weights with:")
        _log(f"  LOOVIE_KIND=videos LOOVIE_MODELS={models} bash docker/download_models.sh")
        _log("  (in Docker, run the same downloader as loovie-download-models)")
    _log(
        "See docs/MODELS.md for the full model list and docs/25-huggingface-and-gated-models.md "
        "for gated licences."
    )
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
