# Run a Loovie-compatible server on your own machine

This guide walks through the **ComfyUI reference implementation** ([`comfyui-loovie/`](../comfyui-loovie/)). ComfyUI is one ready-to-run option. If you would rather implement the [contract](90-the-contract.md) in a different stack (Diffusers, SD-Next, your own server), skip to [`90-the-contract.md`](90-the-contract.md) and stand up your own endpoints; the Loovie app does not care what is behind the URL as long as the responses match.

## Prerequisites

- **GPU.** NVIDIA, 24 GB VRAM or more (see [GPU compatibility in `30-runpod.md`](30-runpod.md#gpu-compatibility-tested-at-launch); image works on 4090/5090, video tested only on 5090).
- **Disk.** Plan on **at least 100 GB free** for the full reference model set: image models are ~24 GB, video models are ~70 GB (~99 GB downloaded for `LOOVIE_KIND=all`), plus headroom for intermediate decoded outputs, swap files, and ComfyUI's own cache. If you only run `LOOVIE_KIND=images` plan on ~30 GB free, `LOOVIE_KIND=videos` plan on ~80 GB free. See [`MODELS.md`](MODELS.md) for the per-model breakdown.
- **Python.** 3.10, 3.11, or 3.12.
- **git.**
- **A HuggingFace account and read token**: [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md). You will need to accept a gated licence for at least one model. Do this first; the download will fail loudly if you skip it.

## Steps

### 1. Install ComfyUI

We pin to the same upstream ref the Docker image uses (currently `v0.21.1`).

```sh
git clone --branch v0.21.1 --depth 1 https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --extra-index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio
pip install -r requirements.txt
```

### 2. Install the Loovie reference custom-node pack

```sh
cd custom_nodes
git clone https://github.com/looviehq/loovie-community.git loovie-community
ln -s loovie-community/comfyui-loovie loovie

# Required Python deps for the Loovie nodes.
pip install -r loovie-community/comfyui-loovie/requirements.txt
```

You also need the ComfyUI-LTXVideo node pack for LTX-2.3 single-shot video:

```sh
git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git
cd ComfyUI-LTXVideo
git checkout 229437c6b65796d6a7a63ae34be2bd5ba31fa543
pip install -r requirements.txt
cd ..
```

### 3. Download the models

Set your HuggingFace token, then run the downloader from the cloned repo.

`LOOVIE_KIND` is an environment variable read by `docker/download_models.sh` and the container entrypoint. It selects which model sets to pull from HuggingFace:

- `images`: image-generation models only (FLUX.2 Klein + text encoder + VAE). ~24 GB.
- `videos`: video-generation models only (LTX-2.3 + Gemma text encoder + upscaler + LoRA). ~70 GB.
- `all`: both. ~99 GB.

Pick the smallest set you need. The capabilities your server advertises through `/loovie/capabilities` will automatically reflect what you actually have on disk: if you only download images, the video tier won't appear in the Loovie app.

```sh
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export LOOVIE_MODELS_ROOT="$PWD/../models"   # whatever path ComfyUI knows as `models/`
export LOOVIE_KIND=all                       # or `images` or `videos`, see above

bash loovie-community/docker/download_models.sh
```

If you see `401 Unauthorized`, you have not accepted a gated licence yet. Open the offending repo URL on huggingface.co while logged in, click *Agree and access repository*, and re-run. See [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md).

### 4. Generate a strong bearer token

```sh
TOKEN=$(bash loovie-community/scripts/new-token.sh)
echo "$TOKEN"   # copy this; you'll paste it into the Loovie app
export LOOVIE_API_TOKEN="$TOKEN"
```

Keep the token private. Treat it like a password.

### 5. Start ComfyUI

From the ComfyUI directory:

```sh
python main.py --listen 0.0.0.0 --port 8188
```

`--listen 0.0.0.0` makes it reachable from your phone on the same network. **The server is configured to fail closed when `LOOVIE_API_TOKEN` is unset and the bind host is non-loopback**, so this is safe, but make sure the token is exported in the same shell.

### 6. Verify it works

In another terminal:

```sh
curl -s http://localhost:8188/loovie/health | jq .
curl -s http://localhost:8188/loovie/capabilities | jq .
```

You should see the health endpoint return `{"code": 200, "data": {"status": "ok", "phase": "ready", ...}}` and the capabilities endpoint return an `images` and/or `ss_videos` section.

### 7. Connect from your phone

You have two reasonable options:

- **Same Wi-Fi**: find the machine's LAN IP (`ifconfig` on macOS/Linux, `ipconfig` on Windows) and use `http://192.168.x.y:8188` in the Loovie app. The app will ask you to tick a checkbox accepting that *plain HTTP is OK only on networks you trust*. Use this on your own home Wi-Fi only.
- **From anywhere (cellular, café, hotel)**: set up [Cloudflare Tunnel](40-cloudflare-tunnel.md). You get HTTPS automatically.

Then follow [`60-configure-the-app.md`](60-configure-the-app.md) to paste URL and token into the Loovie app.

## macOS or Apple Silicon

ComfyUI runs on macOS, but LTX-2.3 and FLUX.2 are heavy. CPU and MPS are slow enough that video is impractical. For image generation on a high-end M-series Mac, expect roughly the speed of a low-end NVIDIA card. For video, use [RunPod](30-runpod.md).

## Troubleshooting

See [`70-troubleshooting.md`](70-troubleshooting.md). The most common stumbles:

- `401` from `download_models.sh` → revisit [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md).
- The Loovie app shows "Server reachable" but generation fails with `BYO server access denied` → your bearer token in the app does not match the `LOOVIE_API_TOKEN` you exported.
- The `Your server (BYO)` option does not appear in the picker → you have not joined the beta yet (see [`10-create-a-loovie-account.md`](10-create-a-loovie-account.md)) or your server did not advertise that section in `/loovie/capabilities` (check the curl output in step 6).
