#!/usr/bin/env bash
# ============================================================================
# Loovie Community reference server, container entrypoint.
#
# Responsibilities:
#   1. Validate that LOOVIE_API_TOKEN is set (unless explicitly bound to
#      loopback, which is the only safe unauthenticated configuration).
#   2. Optionally trigger a model download into the mounted models volume
#      when DOWNLOAD_MODELS=1.
#   3. Print a short startup banner so the operator can sanity-check token
#      status, model availability and effective GPU compat at a glance.
#   4. Exec ComfyUI bound to ${COMFYUI_HOST:-0.0.0.0}:${COMFYUI_PORT:-8188}.
# ============================================================================

set -Eeuo pipefail

readonly VERSION="${LOOVIE_SERVER_VERSION:-unknown}"
readonly GIT_SHA="${LOOVIE_GIT_SHA:-unknown}"
readonly COMFYUI_HOME="${COMFYUI_HOME:-/opt/comfyui}"
readonly COMFYUI_HOST="${COMFYUI_HOST:-0.0.0.0}"
readonly COMFYUI_PORT="${COMFYUI_PORT:-8188}"
readonly LOOVIE_KIND="${LOOVIE_KIND:-images}"
readonly MODELS_ROOT="${LOOVIE_MODELS_ROOT:-/runpod-volume/models}"

log()  { printf '[loovie-entrypoint] %s\n' "$*"; }
fail() { printf '[loovie-entrypoint] ERROR: %s\n' "$*" >&2; exit 1; }

# ----------------------------------------------------------------------------
# Banner
# ----------------------------------------------------------------------------
log "Loovie BYO reference server  version=${VERSION}  commit=${GIT_SHA}"
log "Binding to ${COMFYUI_HOST}:${COMFYUI_PORT}"
log "Models root: ${MODELS_ROOT}"
log ""
log "GPU compatibility (tested at release):"
log "  Image models, RTX 4090 and 5090."
log "  Video models, RTX 5090 only."
log "  Other GPUs may work but are unverified at launch."
log ""

# ----------------------------------------------------------------------------
# Token validation
# ----------------------------------------------------------------------------
# A server reachable off the loopback with no token is a hole; the contract
# (see openapi/loovie-server.openapi.yaml) says fail closed for remote
# callers when no token is configured, and we want that to be the default
# without any way to silently nerf it.
if [[ "${COMFYUI_HOST}" != "127.0.0.1" && "${COMFYUI_HOST}" != "::1" && "${COMFYUI_HOST}" != "localhost" ]]; then
  if [[ -z "${LOOVIE_API_TOKEN:-}" ]]; then
    fail "LOOVIE_API_TOKEN is not set and the server is binding to ${COMFYUI_HOST}.
       Remote unauthenticated access is refused by design.
       Generate a token with scripts/new-token.sh and set LOOVIE_API_TOKEN.
       (To run a private loopback-only instance, set COMFYUI_HOST=127.0.0.1.)"
  fi
  log "Token: configured ($(printf '%s' "${LOOVIE_API_TOKEN}" | wc -c | tr -d ' ') chars)."
else
  log "Token: ${LOOVIE_API_TOKEN:+configured}${LOOVIE_API_TOKEN:-NOT configured (allowed because host is loopback)}"
fi
log ""

# ----------------------------------------------------------------------------
# Optional model download
# ----------------------------------------------------------------------------
if [[ "${DOWNLOAD_MODELS:-0}" == "1" ]]; then
  log "DOWNLOAD_MODELS=1, invoking loovie-download-models (kind=${LOOVIE_KIND})."
  if ! /usr/local/bin/loovie-download-models; then
    fail "Model download failed. See the log above; usually this is a missing or unaccepted HuggingFace token (see docs/25-huggingface-and-gated-models.md)."
  fi
else
  log "DOWNLOAD_MODELS is not set; assuming models are already present at ${MODELS_ROOT}."
fi

# ----------------------------------------------------------------------------
# Brief model availability summary
# ----------------------------------------------------------------------------
if [[ -d "${MODELS_ROOT}" ]]; then
  image_files=$(find "${MODELS_ROOT}/diffusion_models" "${MODELS_ROOT}/checkpoints" -maxdepth 1 -name '*.safetensors' 2>/dev/null | wc -l | tr -d ' ')
  video_files=$(find "${MODELS_ROOT}/checkpoints" -maxdepth 1 -name 'ltx-2*' 2>/dev/null | wc -l | tr -d ' ')
  log "Models on disk: ${image_files} image checkpoint(s), ${video_files} video checkpoint(s) under ${MODELS_ROOT}."
else
  log "Models root ${MODELS_ROOT} does not exist yet (will be populated on first DOWNLOAD_MODELS run)."
fi
log ""

# ----------------------------------------------------------------------------
# Hand off to ComfyUI
# ----------------------------------------------------------------------------
cd "${COMFYUI_HOME}"

# `--extra-model-paths-config` makes ComfyUI look for models under the network
# volume rather than only inside the image. Lets a fresh container pick up
# previously-downloaded weights without rebuilding the image.
exec python3 main.py \
  --listen "${COMFYUI_HOST}" \
  --port "${COMFYUI_PORT}" \
  --extra-model-paths-config "${COMFYUI_HOME}/extra_model_paths.yaml" \
  --output-directory "${MODELS_ROOT}/../outputs" \
  --input-directory  "${MODELS_ROOT}/../input"
