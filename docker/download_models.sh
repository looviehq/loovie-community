#!/usr/bin/env bash
# ============================================================================
# Loovie Community reference server, model downloader.
#
# Reads docker/models.manifest (one entry per line) and downloads each model
# into the canonical ComfyUI folder under ${LOOVIE_MODELS_ROOT}/.
#
# Manifest format (tab-separated, comments allowed with '#'):
#
#   kind  hf_repo                                       hf_filename                                   target_subdir
#
#   kind         = "image" | "video", used to select via LOOVIE_KIND.
#   hf_repo      = HuggingFace repo (e.g. Comfy-Org/ltx-2).
#   hf_filename  = path-in-repo (huggingface_hub will preserve subdirs).
#   target_subdir= ComfyUI folder name (diffusion_models, checkpoints,
#                  text_encoders, vae, loras, upscale_models, latent_upscale_models).
#
# Some models are GATED on HuggingFace. The user must accept the model
# license on the HF web UI before the download will succeed; see
# docs/25-huggingface-and-gated-models.md.
# ============================================================================

set -Eeuo pipefail

readonly MANIFEST="${LOOVIE_MODELS_MANIFEST:-/opt/comfyui/loovie-models.manifest}"
readonly MODELS_ROOT="${LOOVIE_MODELS_ROOT:-/runpod-volume/models}"
readonly LOOVIE_KIND="${LOOVIE_KIND:-images}"

log()  { printf '[loovie-download-models] %s\n' "$*"; }
fail() { printf '[loovie-download-models] ERROR: %s\n' "$*" >&2; exit 1; }

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

log "LOOVIE_KIND=${LOOVIE_KIND}, downloading kinds: ${wanted_kinds[*]}"
log "Models root: ${MODELS_ROOT}"
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

total=0; downloaded=0; skipped=0; failures=0

while IFS=$'\t' read -r kind repo filename target_subdir; do
  # Skip blanks and comments.
  [[ -z "${kind}" || "${kind}" == \#* ]] && continue

  total=$((total + 1))

  if ! contains "${kind}" "${wanted_kinds[@]}"; then
    log "  [skip kind] ${repo} :: ${filename}"
    skipped=$((skipped + 1))
    continue
  fi

  target_dir="${MODELS_ROOT}/${target_subdir}"
  target_file="${target_dir}/$(basename "${filename}")"

  if [[ -f "${target_file}" ]]; then
    log "  [present]   ${target_subdir}/$(basename "${filename}")"
    skipped=$((skipped + 1))
    continue
  fi

  mkdir -p "${target_dir}"
  log "  [download]  ${repo} :: ${filename} -> ${target_subdir}/"

  # huggingface-cli download writes to a cache by default; we use --local-dir
  # to land the file in the ComfyUI folder layout directly. --local-dir-use-symlinks
  # is deprecated in newer hf-hub; the default is fine.
  if huggingface-cli download "${repo}" "${filename}" \
        --local-dir "${target_dir}" \
        --quiet; then
    downloaded=$((downloaded + 1))
  else
    rc=$?
    log "    failed (exit ${rc}), likely cause: missing HF_TOKEN or unaccepted gated license."
    log "    Open https://huggingface.co/${repo} while logged in, click 'Agree and access repository'."
    failures=$((failures + 1))
  fi
done < "${MANIFEST}"

log ""
log "Manifest summary: total=${total} downloaded=${downloaded} skipped=${skipped} failed=${failures}"

if (( failures > 0 )); then
  fail "${failures} model(s) failed to download. See messages above."
fi

log "Done."
