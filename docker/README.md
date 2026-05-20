# `docker/` — Loovie BYO reference server image and RunPod template

This directory builds and ships the reference Docker image you can either run yourself or import as a RunPod template. It implements the [Loovie BYO HTTP contract](../openapi/loovie-server.openapi.yaml) using the [`comfyui-loovie/`](../comfyui-loovie/) reference implementation.

> **RunPod bills you for GPU time. Loovie itself charges nothing for BYO generations.** RunPod pricing is per-minute, so if you forget to stop your pod, you keep paying RunPod. Always stop the pod when you are done.

> **GPU compatibility (tested at launch).** Image models verified on RTX 4090 and 5090. Video models verified **only** on RTX 5090 at launch. Other GPUs may work but are unverified.

> **Beta API stability.** This contract may introduce breaking changes between minor versions of the `0.x` line. See the [CHANGELOG](../CHANGELOG.md) and pin to a specific tag or commit SHA if you depend on it.

## Two ways to run

### Option A — RunPod (no hardware required)

You will need a [HuggingFace account and read token](../docs/25-huggingface-and-gated-models.md) and a strong server token from `scripts/new-token.sh`.

1. **Create a RunPod account** — [https://runpod.io?ref=vg16q1rz](https://runpod.io?ref=vg16q1rz). *(Links in this section use the Loovie RunPod referral. It supports Loovie at no extra cost to you.)*
2. **Generate a server token locally**:
   ```sh
   bash scripts/new-token.sh
   ```
   Copy the output.
3. **Deploy the template.** Import `docker/runpod-template.json` in the RunPod console (Settings → Templates → New). A one-click "Deploy to RunPod" button will appear in the docs once the template is published to RunPod's public catalogue.
4. **Pick a GPU.** Per the compat note above: 4090 or 5090 for images; 5090 for video.
5. **Set the two required secrets** when launching:
   - `LOOVIE_API_TOKEN` — the token from step 2.
   - `HF_TOKEN` — your HuggingFace read token.
6. **Wait for first boot** — usually 15–40 minutes while the container downloads the model weights into the attached volume. Subsequent boots reuse the volume and start in under a minute.
7. **Copy the pod's HTTPS proxy URL** (e.g. `https://<pod-id>-8188.proxy.runpod.net`). Open the Loovie iOS app → Preferences → BYO server, and paste the URL plus the token.
8. **Generate.** Image or Video quality → *Your server (BYO)*.
9. **Stop the pod when you are done.** RunPod keeps billing as long as it is running.

### Option B — Self-host (your own NVIDIA GPU)

```sh
# Generate a token (kept on your host, not committed anywhere).
TOKEN=$(bash scripts/new-token.sh)

# Pull the image (or `docker build .` from the repo root).
docker pull ghcr.io/looviehq/loovie-server:beta

# Run, mounting a host directory for the model cache so reboots are fast.
mkdir -p ./loovie-volume/{models,outputs,input}
docker run --rm -d \
  --name loovie-byo \
  --gpus all \
  -p 8188:8188 \
  -v "$PWD/loovie-volume:/runpod-volume" \
  -e LOOVIE_API_TOKEN="$TOKEN" \
  -e HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  -e DOWNLOAD_MODELS=1 \
  -e LOOVIE_KIND=all \
  ghcr.io/looviehq/loovie-server:beta

# Verify it is up.
curl -s http://localhost:8188/loovie/health | jq .
curl -s http://localhost:8188/loovie/capabilities | jq .
```

For phone-to-LAN-server use, see [`docs/20-quickstart-your-own-machine.md`](../docs/20-quickstart-your-own-machine.md) and [`docs/40-cloudflare-tunnel.md`](../docs/40-cloudflare-tunnel.md).

## Security note

**Never expose port 8188 publicly without `LOOVIE_API_TOKEN` set.** The entrypoint refuses to start if the bind host is non-loopback and no token is configured. See [`SECURITY.md`](../SECURITY.md) and [`docs/50-security-and-tokens.md`](../docs/50-security-and-tokens.md).

## Environment variables

| Variable | Required | Default | What it does |
|---|---|---|---|
| `LOOVIE_API_TOKEN` | **yes** for non-loopback binds | — | Static bearer token the app sends. Entrypoint refuses to start if unset and the bind is remote-reachable. |
| `HF_TOKEN` | for gated model downloads | — | HuggingFace read token. Required for Gemma-3 (LTX text encoder) and FLUX.2 weights. See [`docs/25`](../docs/25-huggingface-and-gated-models.md). |
| `DOWNLOAD_MODELS` | no | `0` | Set to `1` to run `loovie-download-models` on container start. |
| `LOOVIE_KIND` | no | `images` | Which model sets to download (`images`, `videos`, `all`). |
| `LOOVIE_MODELS_ROOT` | no | `/runpod-volume/models` | Where models live on disk. |
| `COMFYUI_HOST` | no | `0.0.0.0` | Bind interface. Set to `127.0.0.1` for a loopback-only instance with no token. |
| `COMFYUI_PORT` | no | `8188` | Bind port. |

## Tags

Released tags follow `:vX.Y.Z` (full semver), `:vX.Y` (minor), `:beta` (latest beta), and `sha-<short>` (commit-addressable). **No `:latest` tag during beta** — for ML inference images, `:latest` causes silent breakage. Pin to `:beta` or a specific `:vX.Y.Z` (see [Beta API stability](../README.md#beta-api-stability)).

## Building from source

```sh
cd loovie-community
docker buildx build \
  --platform linux/amd64 \
  --build-arg VERSION="$(git describe --tags --always --dirty)" \
  --build-arg GIT_SHA="$(git rev-parse --short HEAD)" \
  -t loovie-server:dev \
  -f docker/Dockerfile \
  .
```

amd64-only — see [Part J §J9 of the launch plan](../docs/superpowers/.../) for the rationale (no usable arm64 GPU compute path for ML inference at the moment).

## What lives where

| File | Purpose |
|---|---|
| [`Dockerfile`](./Dockerfile) | Multi-stage build: builder layer installs Python deps; runtime layer copies the venv + ComfyUI tree. |
| [`entrypoint.sh`](./entrypoint.sh) | Validates token, optionally invokes the downloader, prints the boot banner, hands off to ComfyUI. |
| [`download_models.sh`](./download_models.sh) | Reads `models.manifest` and downloads the weights via `huggingface-cli`. Fails loudly with a pointer to `docs/25` if HF auth is missing or a gated licence has not been accepted. |
| [`models.manifest`](./models.manifest) | Tab-separated list of `(kind, hf_repo, hf_filename, target_subdir)` entries the downloader reads. Edit this file to add or replace weights. |
| [`extra_model_paths.yaml`](./extra_model_paths.yaml) | ComfyUI config that maps the mounted volume into ComfyUI's `diffusion_models/`, `checkpoints/`, `text_encoders/`, etc. |
| [`runpod-template.json`](./runpod-template.json) | RunPod template you can import directly. |

## Contributing

See [`CONTRIBUTING.md`](../CONTRIBUTING.md). PRs that change the Dockerfile, manifest, or template should include a one-line test plan in the PR description.
