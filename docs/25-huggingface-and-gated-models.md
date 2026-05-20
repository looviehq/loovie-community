# HuggingFace token and gated model agreements

The reference workflows use a handful of models that are **gated** on HuggingFace, meaning HuggingFace requires you (the logged-in user) to accept the upstream licence before you can download them. The download script in this repo fails loudly with a pointer back to this page if any gated download returns 401.

Read this once, do it once, and you are done.

## 1. Create a HuggingFace account

[huggingface.co/join](https://huggingface.co/join). Free, email-only signup.

## 2. Generate a read token

[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → *New token*.

- **Name:** `Loovie BYO` (or whatever helps you find it later).
- **Role:** **Read** is sufficient. Do not pick Write.
- Copy the token (`hf_...`). Treat it like a password. Rotate it from this page whenever you stop using the machine.

## 3. Accept the gated model licences

While logged into HuggingFace, open each of the following pages and click **Agree and access repository**. Each takes about 10 seconds.

> **The exact set of gated models depends on the upstream packagers.** This list reflects what `docker/models.manifest` references at the current `v0.1.x-beta` line. New workflows may add more; the downloader will tell you which one failed and link back here.

| Model | HuggingFace repo | Why we need it | Status |
|---|---|---|---|
| **Gemma-3 text encoder (fp8 scaled)** | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2) | LTX-2.3 video uses Gemma as its text encoder. | Gated by Google. |
| **FLUX.2 Klein** weights, VAE, Qwen-3-4B text encoder | [Comfy-Org/flux2](https://huggingface.co/Comfy-Org/flux2) | Image generation. | Gated by Black Forest Labs. |
| **LTX-2.3 22B fp8 + distilled LoRA + spatial upscaler** | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2) | Video generation. | Lightricks community licence; one-click acceptance. |
| **RealESRGAN 2x** | [xinntao/Real-ESRGAN](https://huggingface.co/xinntao/Real-ESRGAN) | Pro-tier video upscaling. | Public, no acceptance needed. |

If a download fails with `HTTP 401`, the message points back to the exact repo URL. Open it, click *Agree*, re-run.

## 4. Provide the token to your server

### RunPod template

The template declares `HF_TOKEN` as a required secret. Paste the value when you launch the pod. The downloader (which runs as part of the entrypoint when `DOWNLOAD_MODELS=1`) picks it up automatically.

### Docker self-host

```sh
docker run --rm -d \
  --gpus all \
  -p 8188:8188 \
  -e LOOVIE_API_TOKEN="$TOKEN" \
  -e HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  -e DOWNLOAD_MODELS=1 \
  -e LOOVIE_KIND=all \
  -v "$PWD/loovie-volume:/runpod-volume" \
  ghcr.io/looviehq/loovie-server:beta
```

### Bare ComfyUI (your own machine)

Export the token before running the downloader:

```sh
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
bash loovie-community/docker/download_models.sh
```

## 5. What happens when you forget

`docker/download_models.sh` fails fast on the first 401 and prints which model needs acceptance, with a direct link to the HuggingFace repo. Open the link, accept, re-run. Already-downloaded files are skipped on the next run; you don't pay the bandwidth twice.

## Token hygiene

- **Do not commit `HF_TOKEN` to git.** It is a personal credential. Use a `.env` file (gitignored) or pass it via the shell.
- **Rotate it** if you suspect compromise or stop using a machine. Go back to [the tokens page](https://huggingface.co/settings/tokens) and delete the old one.
- **Keep it Read-only.** Loovie's downloader only reads. A Write token gives extra access HuggingFace doesn't need to do downloads.
