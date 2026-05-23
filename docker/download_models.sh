#!/usr/bin/env bash
# ============================================================================
# Loovie Community reference server, model downloader.
#
# Reads docker/models.manifest (one entry per line) and downloads each model
# into the canonical ComfyUI folder under ${LOOVIE_MODELS_ROOT}/.
#
# Manifest format (tab-separated, comments allowed with '#'):
#
#   kind hf_repo hf_path local_name target_subdir
#
#   kind         = "image" | "video", used to select via LOOVIE_KIND.
#   hf_repo      = HuggingFace repo (e.g. Lightricks/LTX-2.3-fp8).
#   hf_path      = path-in-repo (may include subdirs, e.g. split_files/...).
#   local_name   = ComfyUI filename under target_subdir after download.
#   target_subdir= ComfyUI folder name (diffusion_models, checkpoints,
#                  text_encoders, vae, loras, upscale_models, latent_upscale_models).
#
# Some models are GATED on HuggingFace. The user must accept the model
# license on the HF web UI before the download will succeed; see
# docs/25-huggingface-and-gated-models.md.
# ============================================================================

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly DOCKER_MANIFEST="/opt/comfyui/loovie-models.manifest"
readonly REPO_MANIFEST="${SCRIPT_DIR}/models.manifest"

resolve_models_root() {
  MODELS_ROOT=""
  MODELS_ROOT_SOURCE=""

  if [[ -n "${LOOVIE_MODELS_ROOT:-}" ]]; then
    MODELS_ROOT="${LOOVIE_MODELS_ROOT}"
    MODELS_ROOT_SOURCE="LOOVIE_MODELS_ROOT (you set this explicitly)"
    return
  fi

  # Prefer a local ComfyUI checkout over RunPod volume paths. Dev containers
  # often have both /ComfyUI and /runpod-volume; bare-metal installs should
  # land weights in ComfyUI/models unless you override LOOVIE_MODELS_ROOT.
  local candidate
  for candidate in \
    "$(cd "${SCRIPT_DIR}/../../.." 2>/dev/null && pwd)" \
    "$(cd "${SCRIPT_DIR}/../.." 2>/dev/null && pwd)"; do
    if [[ -n "${candidate}" && -f "${candidate}/main.py" ]]; then
      MODELS_ROOT="${candidate}/models"
      MODELS_ROOT_SOURCE="auto-detected ComfyUI at ${candidate}"
      return
    fi
  done

  if [[ -d "/runpod-volume" ]]; then
    MODELS_ROOT="/runpod-volume/models"
    MODELS_ROOT_SOURCE="auto-detected RunPod network volume (/runpod-volume)"
    return
  fi

  if [[ -d "/workspace" ]]; then
    MODELS_ROOT="/workspace/models"
    MODELS_ROOT_SOURCE="auto-detected RunPod workspace (/workspace)"
    return
  fi

  MODELS_ROOT="/runpod-volume/models"
  MODELS_ROOT_SOURCE="fallback (no ComfyUI or RunPod paths found; set LOOVIE_MODELS_ROOT)"
}

resolve_models_root
readonly MODELS_ROOT
readonly MODELS_ROOT_SOURCE
readonly LOOVIE_KIND="${LOOVIE_KIND:-images}"

log()  { printf '[loovie-download-models] %s\n' "$*"; }
fail() { printf '[loovie-download-models] ERROR: %s\n' "$*" >&2; exit 1; }

resolve_manifest() {
  if [[ -n "${LOOVIE_MODELS_MANIFEST:-}" ]]; then
    printf '%s' "${LOOVIE_MODELS_MANIFEST}"
    return
  fi
  if [[ -f "${DOCKER_MANIFEST}" ]]; then
    printf '%s' "${DOCKER_MANIFEST}"
    return
  fi
  if [[ -f "${REPO_MANIFEST}" ]]; then
    printf '%s' "${REPO_MANIFEST}"
    return
  fi
  fail "Manifest not found. Set LOOVIE_MODELS_MANIFEST, or place models.manifest at ${DOCKER_MANIFEST} (Docker) or ${REPO_MANIFEST} (repo checkout)."
}

MANIFEST="$(resolve_manifest)"
readonly MANIFEST

if [[ ! -f "${MANIFEST}" ]]; then
  fail "Manifest not found: ${MANIFEST}"
fi

# ----------------------------------------------------------------------------
# HF token check up front so we fail fast with a helpful message rather than
# in the middle of a 30GB download.
# ----------------------------------------------------------------------------
HF_TOKEN="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}"
if [[ -z "${HF_TOKEN}" ]]; then
  log "WARNING: HF_TOKEN is not set."
  log "         If any model on the manifest is GATED on HuggingFace, the"
  log "         download will fail with HTTP 401. See"
  log "         docs/25-huggingface-and-gated-models.md for the steps to"
  log "         create a read token and accept gated model licenses."
else
  export HF_TOKEN
  export HUGGING_FACE_HUB_TOKEN="${HF_TOKEN}"
  log "HF_TOKEN is set (${#HF_TOKEN} characters)."
fi

# ----------------------------------------------------------------------------
# Decide which kinds to download.
# ----------------------------------------------------------------------------
declare -a wanted_kinds=()
case "${LOOVIE_KIND}" in
  images)     wanted_kinds=(image) ;;
  videos)     wanted_kinds=(video) ;;
  all)        wanted_kinds=(image video) ;;
  *)          fail "Unknown LOOVIE_KIND='${LOOVIE_KIND}' (expected: images, videos, all)" ;;
esac

log "LOOVIE_KIND=${LOOVIE_KIND} (override with export LOOVIE_KIND=images|videos|all)"
log "Models root: ${MODELS_ROOT}"
log "  source: ${MODELS_ROOT_SOURCE}"
log "Manifest: ${MANIFEST}"
if [[ -d "/runpod-volume" && "${MODELS_ROOT_SOURCE}" == auto-detected\ ComfyUI* ]]; then
  log "Note: /runpod-volume exists but this run targets ComfyUI/models."
  log "      To use the RunPod volume instead: export LOOVIE_MODELS_ROOT=/runpod-volume/models"
fi
mkdir -p "${MODELS_ROOT}"

# ----------------------------------------------------------------------------
# Disk requirements summary (printed up front, not enforced).
# ----------------------------------------------------------------------------
log ""
log "Approximate disk requirements:"
log "  images          ~24 GB (FLUX.2 Klein + Qwen text encoder + VAE)"
log "  videos          ~70 GB (LTX-2.3 + Gemma text encoder + upscaler + LoRA)"
log "  all             ~99 GB"
log ""

# ----------------------------------------------------------------------------
# Manifest reader.
# ----------------------------------------------------------------------------
contains() {
  local needle="$1"; shift
  for elem in "$@"; do
    if [[ "${elem}" == "${needle}" ]]; then return 0; fi
  done
  return 1
}

resolve_hf_cmd() {
  if command -v hf >/dev/null 2>&1; then
    printf '%s' "hf"
  elif command -v huggingface-cli >/dev/null 2>&1; then
    printf '%s' "huggingface-cli"
  else
    log "Installing huggingface_hub CLI..."
    pip install -q 'huggingface_hub[cli]>=0.25'
    if command -v hf >/dev/null 2>&1; then
      printf '%s' "hf"
    elif command -v huggingface-cli >/dev/null 2>&1; then
      printf '%s' "huggingface-cli"
    else
      fail "Could not install huggingface_hub CLI. Run: pip install 'huggingface_hub[cli]>=0.25'"
    fi
  fi
}

HF_CMD="$(resolve_hf_cmd)"
readonly HF_CMD
log "Using HF CLI: ${HF_CMD}"

# Same contract as apps/comfy/scripts/install.sh dl():
#   dl dest_dir local_name repo repo_path
download_hf_file() {
  local dest_dir="$1" local_name="$2" repo="$3" repo_path="$4"
  local -a token_args=()
  if [[ -n "${HF_TOKEN:-}" ]]; then
    token_args=(--token "${HF_TOKEN}")
  fi
  "${HF_CMD}" download "${repo}" "${repo_path}" --local-dir "${dest_dir}" "${token_args[@]}"
  flatten_download "${dest_dir}" "${repo_path}" "${local_name}"
}

flatten_download() {
  local target_dir="$1" hf_path="$2" local_name="$3"
  local nested="${target_dir}/${hf_path}"
  local dest="${target_dir}/${local_name}"

  if [[ -f "${dest}" ]]; then
    return 0
  fi
  if [[ -f "${nested}" ]]; then
    mv "${nested}" "${dest}"
    local parent
    parent="$(dirname "${nested}")"
    while [[ "${parent}" != "${target_dir}" ]]; do
      rmdir "${parent}" 2>/dev/null || break
      parent="$(dirname "${parent}")"
    done
  fi
}

total=0; downloaded=0; skipped=0; failures=0

while IFS=$'\t' read -r kind repo hf_path local_name target_subdir; do
  # Skip blanks and comments.
  [[ -z "${kind}" || "${kind}" == \#* ]] && continue

  # Back-compat: older 4-column rows: kind, repo, hf_path, target_subdir.
  if [[ -z "${target_subdir}" ]]; then
    target_subdir="${local_name}"
    local_name="$(basename "${hf_path}")"
  fi

  if [[ -z "${repo}" || -z "${hf_path}" || -z "${local_name}" || -z "${target_subdir}" ]]; then
    fail "Bad manifest row (need 5 tab-separated fields): kind=${kind} repo=${repo} hf_path=${hf_path} local_name=${local_name} target_subdir=${target_subdir}"
  fi

  total=$((total + 1))

  if ! contains "${kind}" "${wanted_kinds[@]}"; then
    log "  [skip kind] ${repo} :: ${hf_path}"
    skipped=$((skipped + 1))
    continue
  fi

  target_dir="${MODELS_ROOT}/${target_subdir}"
  target_file="${target_dir}/${local_name}"

  if [[ -f "${target_file}" ]]; then
    log "  [present]   ${target_subdir}/${local_name}"
    skipped=$((skipped + 1))
    continue
  fi

  mkdir -p "${target_dir}"
  log "  [download]  ${repo} :: ${hf_path} -> ${target_subdir}/${local_name}"

  if download_hf_file "${target_dir}" "${local_name}" "${repo}" "${hf_path}"; then
    if [[ -f "${target_file}" ]]; then
      downloaded=$((downloaded + 1))
    else
      log "    failed: expected ${target_file} after download."
      failures=$((failures + 1))
    fi
  else
    rc=$?
    log "    failed (exit ${rc}). Common causes:"
    log "      - HF_TOKEN missing or not passed (re-export and re-run in the same shell)"
    log "      - gated licence not accepted at https://huggingface.co/${repo}"
    failures=$((failures + 1))
  fi
done < "${MANIFEST}"

log ""
log "Manifest summary: total=${total} downloaded=${downloaded} skipped=${skipped} failed=${failures}"

if (( failures > 0 )); then
  fail "${failures} model(s) failed to download. See messages above."
fi

log "Done."
