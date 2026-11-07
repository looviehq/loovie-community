#!/usr/bin/env python3
"""List, filter and recommend models for the Loovie BYO server.

The server reads `models.enabled` from `config.yaml`. This helper is read-only:
it prints the catalogue and a ready-to-paste YAML block, so an operator never
has to guess which models their card can run.

Usage:
    python scripts/models.py list
    python scripts/models.py recommend --vram 32
    python scripts/models.py config --video ltx-2.5,pika-flex \
        --image qwen-image-2.1,flux-2-klein --music yue2 \
        --sfx stable-audio-3 --default-video ltx-2.5
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Load the registry module directly. Importing the package would pull in the
# ComfyUI node classes (torch/numpy), which this CLI must not require.
_MODELS_PATH = ROOT / "src" / "comfyui_loovie" / "models.py"
_spec = importlib.util.spec_from_file_location("loovie_models", _MODELS_PATH)
assert _spec and _spec.loader
_models = importlib.util.module_from_spec(_spec)
sys.modules["loovie_models"] = _models
_spec.loader.exec_module(_models)

CATALOG = _models.CATALOG
ModelSpec = _models.ModelSpec


def _variants(spec: ModelSpec) -> str:
    return ", ".join(variant.id for variant in spec.variants)


def _modes(spec: ModelSpec) -> str:
    return ", ".join(spec.capabilities)


def _vram(spec: ModelSpec) -> str:
    if spec.vram_gb is None:
        return "-"
    if spec.recommended_vram_gb is None:
        return f"{spec.vram_gb:g}"
    return f"{spec.vram_gb:g} / {spec.recommended_vram_gb:g}"


def _print_model(spec: ModelSpec) -> None:
    print(f"{spec.id:18} {spec.modality:6}  {_vram(spec):9}  {_modes(spec):28}  {_variants(spec)}")


def cmd_list(_args: argparse.Namespace) -> int:
    print(f"{'id':18} {'kind':6}  {'min/rec':9}  {'modes':28}  variants")
    print("-" * 100)
    for spec in CATALOG:
        _print_model(spec)
    print()
    print(
        "A model is advertised only when its workflow files are registered and "
        "it is enabled in config.yaml."
    )
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    vram = float(args.vram)
    fits = [spec for spec in CATALOG if spec.vram_gb is not None and spec.vram_gb <= vram]
    recommended = [
        spec
        for spec in fits
        if spec.recommended_vram_gb is None or spec.recommended_vram_gb <= vram
    ]
    print(f"GPU: {vram:g} GB")
    print()
    print("Recommended (fits with headroom):")
    for spec in recommended:
        _print_model(spec)
    if not recommended:
        print("  (none)")
    print()
    print("Fits, but tight (expect offload / slower first run):")
    tight = [spec for spec in fits if spec not in recommended]
    for spec in tight:
        _print_model(spec)
    if not tight:
        print("  (none)")
    print()
    print("Does not fit:")
    for spec in CATALOG:
        if spec not in fits:
            _print_model(spec)
    return 0


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def cmd_config(args: argparse.Namespace) -> int:
    video = _split(args.video)
    image = _split(args.image)
    music = _split(args.music)
    sfx = _split(args.sfx)
    known = {spec.id: spec for spec in CATALOG}
    missing = [model for model in [*video, *image, *music, *sfx] if model not in known]
    if missing:
        print(f"Unknown model id(s): {', '.join(missing)}", file=sys.stderr)
        return 2
    for model in [*video, *image, *music, *sfx]:
        workflows = known[model].workflows
        print(
            f"# {model}: register {len(workflows)} workflow(s), e.g. "
            f"{next(iter(workflows.values()))}",
            file=sys.stderr,
        )
    default_video = args.default_video or (video[0] if video else "")
    default_image = args.default_image or (image[0] if image else "")
    default_music = args.default_music or (music[0] if music else "")
    default_sfx = args.default_sfx or (sfx[0] if sfx else "")
    print("models:")
    print("  enabled:")
    print(f"    image: [{', '.join(image)}]")
    print(f"    video: [{', '.join(video)}]")
    print(f"    music: [{', '.join(music)}]")
    print(f"    sfx: [{', '.join(sfx)}]")
    print("  defaults:")
    print(f"    image: {default_image}")
    print(f"    video: {default_video}")
    print(f"    music: {default_music}")
    print(f"    sfx: {default_sfx}")
    print("  switch_policy: auto")
    print("  report_hardware: true")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show the catalogue").set_defaults(func=cmd_list)

    recommend = sub.add_parser("recommend", help="filter the catalogue by GPU VRAM")
    recommend.add_argument("--vram", required=True, help="total GPU VRAM in GB")
    recommend.set_defaults(func=cmd_recommend)

    config = sub.add_parser("config", help="print a ready-to-paste models block")
    config.add_argument("--video", default="", help="comma-separated video model ids")
    config.add_argument("--image", default="", help="comma-separated image model ids")
    config.add_argument("--music", default="", help="comma-separated music model ids")
    config.add_argument("--sfx", default="", help="comma-separated sound-effect model ids")
    config.add_argument("--default-video", default="")
    config.add_argument("--default-image", default="")
    config.add_argument("--default-music", default="")
    config.add_argument("--default-sfx", default="")
    config.set_defaults(func=cmd_config)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
