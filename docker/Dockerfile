# syntax=docker/dockerfile:1.7

# ============================================================================
# Loovie Community — reference Docker image for a BYO ComfyUI server that
# implements the Loovie BYO contract (openapi/loovie-server.openapi.yaml).
#
# Targets a CUDA 12.4 NVIDIA GPU. amd64-only (no real arm64 GPU compute path
# for ML inference, see Part J §J9 / [D24]). Pins ComfyUI to a tagged release
# and ComfyUI-LTXVideo to a known-good SHA; bump these manually as part of
# release prep, not via Dependabot (Dependabot does not track upstream git).
# ============================================================================

ARG CUDA_VERSION=12.4.1
ARG UBUNTU_VERSION=22.04

# ---- Stage 1: builder ----------------------------------------------------
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu${UBUNTU_VERSION} AS builder

ARG COMFYUI_REF=v0.21.1
ARG COMFYUI_LTX_REF=229437c6b65796d6a7a63ae34be2bd5ba31fa543

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# System deps. ffmpeg is required by ComfyUI for video I/O; git for cloning
# upstream repos at pinned refs; build-essential for any C-extension wheels
# (e.g. tokenizers) that may need to compile from source on this base.
RUN apt-get update && apt-get install --no-install-recommends -y \
        python3 python3-pip python3-venv python3-dev \
        git ca-certificates curl \
        ffmpeg \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv for ComfyUI's Python runtime so we can layer-cache it cleanly.
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --upgrade pip wheel setuptools

# Clone ComfyUI at the pinned ref. Shallow checkout because we only need the
# tree, not history.
RUN git clone --branch "${COMFYUI_REF}" --depth 1 \
        https://github.com/comfyanonymous/ComfyUI.git /opt/comfyui

WORKDIR /opt/comfyui

# Pre-install the official PyTorch CUDA 12.4 wheels first so they layer-cache
# independently of the rest of the requirements.
RUN pip install --extra-index-url https://download.pytorch.org/whl/cu124 \
        torch torchvision torchaudio

RUN pip install -r requirements.txt

# Install the ComfyUI-LTXVideo custom-node pack (LTX-2.3 support).
RUN git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git \
        /opt/comfyui/custom_nodes/ComfyUI-LTXVideo
WORKDIR /opt/comfyui/custom_nodes/ComfyUI-LTXVideo
RUN git checkout "${COMFYUI_LTX_REF}" \
    && pip install -r requirements.txt
WORKDIR /opt/comfyui

# Copy and install the Loovie reference implementation.
# Build context root is the repo root; we copy comfyui-loovie/ into the
# ComfyUI custom_nodes tree under the canonical name `loovie`.
COPY comfyui-loovie /opt/comfyui/custom_nodes/loovie
RUN pip install -e /opt/comfyui/custom_nodes/loovie

# ---- Stage 2: runtime ----------------------------------------------------
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu${UBUNTU_VERSION} AS runtime

ARG VERSION=0.1.0-beta
ARG GIT_SHA=unknown

# OCI labels. `image.source` is what makes GHCR auto-link the image to the
# repo and inherit visibility/license metadata. Required by Part J §J9.
LABEL org.opencontainers.image.source="https://github.com/looviehq/loovie-community"
LABEL org.opencontainers.image.description="Loovie BYO reference server (ComfyUI + FLUX.2 Klein + LTX-2.3 single-shot video)"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.title="loovie-server"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.url="https://loovie.app/byo"
LABEL org.opencontainers.image.documentation="https://github.com/looviehq/loovie-community/tree/main/docs"
LABEL org.opencontainers.image.vendor="Loovie HQ Pty Ltd"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LOOVIE_SERVER_VERSION="${VERSION}" \
    LOOVIE_GIT_SHA="${GIT_SHA}" \
    COMFYUI_PORT=8188 \
    COMFYUI_HOME=/opt/comfyui

RUN apt-get update && apt-get install --no-install-recommends -y \
        python3 python3-venv \
        ffmpeg \
        ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*

# Copy the prepared venv and ComfyUI tree from the builder stage.
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/comfyui /opt/comfyui
ENV PATH="/opt/venv/bin:${PATH}"

# huggingface-cli is what download_models.sh uses; install it into the venv
# so HF gated-model downloads work with an HF_TOKEN env var.
RUN pip install --upgrade "huggingface_hub[cli]>=0.25,<1"

# Bring in the entrypoint, model downloader and the extra-model-paths
# configuration that maps a network volume into ComfyUI's folder names.
COPY docker/entrypoint.sh /usr/local/bin/loovie-entrypoint
COPY docker/download_models.sh /usr/local/bin/loovie-download-models
COPY docker/models.manifest /opt/comfyui/loovie-models.manifest
COPY docker/extra_model_paths.yaml /opt/comfyui/extra_model_paths.yaml
RUN chmod +x /usr/local/bin/loovie-entrypoint /usr/local/bin/loovie-download-models

# Reasonable default for the model cache and ComfyUI's outputs. RunPod
# templates mount /runpod-volume; the extra-model-paths.yaml looks there.
RUN mkdir -p /runpod-volume/models /runpod-volume/outputs /runpod-volume/input

EXPOSE 8188

# Use tini as PID 1 so signals propagate cleanly to ComfyUI and any helper
# children. tini handles SIGTERM -> graceful ComfyUI shutdown.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/loovie-entrypoint"]
