#!/usr/bin/env bash
# Install comfyui-loovie into a ComfyUI checkout.
#
# Usage:
#   COMFY_DIR=/path/to/ComfyUI scripts/install.sh [--copy] [--with-models]
#
# Defaults:
#   - Symlinks this directory into $COMFY_DIR/custom_nodes/loovie. Pass
#     --copy to copy instead (useful for sandboxed environments without
#     symlink permissions).
#   - Does NOT download models. Pass --with-models to seed the baseline
#     set the reference workflows expect.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMFY_DIR="${COMFY_DIR:-${HOME}/ComfyUI}"
MODE="symlink"
WITH_MODELS=0

for arg in "$@"; do
  case "$arg" in
    --copy)         MODE="copy" ;;
    --with-models)  WITH_MODELS=1 ;;
    --help|-h)
      sed -n '2,12p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

if [[ ! -d "$COMFY_DIR" ]]; then
  echo "ERROR: COMFY_DIR=$COMFY_DIR does not exist." >&2
  echo "Set COMFY_DIR to your ComfyUI checkout and rerun." >&2
  exit 1
fi

mkdir -p "$COMFY_DIR/custom_nodes"
TARGET="$COMFY_DIR/custom_nodes/loovie"

if [[ -e "$TARGET" || -L "$TARGET" ]]; then
  echo "Removing existing $TARGET"
  rm -rf "$TARGET"
fi

if [[ "$MODE" == "symlink" ]]; then
  ln -s "$HERE" "$TARGET"
  echo "Symlinked $HERE -> $TARGET"
else
  cp -R "$HERE" "$TARGET"
  echo "Copied $HERE -> $TARGET"
fi

if [[ "$WITH_MODELS" -eq 1 ]]; then
  echo "Model fetching not yet automated. See docs/MODELS.md for the manifest."
fi

echo
echo "Next steps:"
echo "  1. Install Python deps:   pip install -r '$HERE/requirements.txt'"
echo "  2. Set the bearer token:  export LOOVIE_API_TOKEN=\$(openssl rand -hex 32)"
echo "  3. Start ComfyUI:         (cd '$COMFY_DIR' && python main.py --listen 0.0.0.0 --port 8188)"
