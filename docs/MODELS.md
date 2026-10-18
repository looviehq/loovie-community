# Models

This page lists every model the **reference implementation** ([`comfyui-loovie/`](../comfyui-loovie/)) ships with, along with its upstream source and licence. Loovie does **not** relicense these models. **You are responsible for accepting each upstream licence before downloading and for honouring its terms when using the model.**

> **You are not required to use these models.** They are the ones we tested and currently ship workflows for. BYO is model-agnostic at the contract level: as long as your workflow's input shape matches what `/images/create`, `/videos/create`, or `/music/create` sends, and its output shape matches what `/{images,videos,music}/status` returns, you can run **any** image, video, or music model you have rights to run. Examples people have used or asked about: WAN 2.x, HunyuanVideo, CogVideoX, Mochi, AnimateDiff variants for video; SDXL, SD3.5, Stable Cascade, Lumina, HiDream for image; ACE-Step, YuE2, MusicGen for music. We don't promise to test all of them, but the contract doesn't care which one you use.

The downloader (`docker/download_models.sh`) reads [`docker/models.manifest`](../docker/models.manifest) and pulls the files from the HuggingFace repos below. Some of these are **gated**, meaning HuggingFace requires you to accept the licence on the web UI while logged in before the download will succeed. See [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md).

> **This list reflects the current `v0.1.x-beta` line.** Adding a model in a PR also means adding it here. If you want to add a new reference workflow built on a different model, see [`80-adding-a-workflow.md`](80-adding-a-workflow.md).

## Image generation

### FLUX 3 Image Klein (distilled)

- **Purpose:** primary text-to-image and image-to-image model (`flux-3-klein`, `flux-3-klein-edit`). Needs ComfyUI 0.41.0 or newer.
- **HuggingFace repo:** [`black-forest-labs/flux-3-image-klein-comfy`](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy) (diffusion model, Qwen3-VL text encoder, VAE).
- **Upstream:** [Black Forest Labs / FLUX](https://github.com/black-forest-labs/flux).
- **Licence:** FLUX Kommunity License. **Gated on HuggingFace**, accept on the repo page while logged in before downloading. Read the terms, including the commercial-use limits.
- **Files:** `flux3-image-klein-int8-convrot.safetensors` (5.8 GB), `qwen3vl_4b_int8_convrot.safetensors` (4.9 GB), `flux2-vae.safetensors` (0.3 GB).
- **Approx size:** ~11 GB combined.
- **Not included:** the BFL prompt upsampler (`qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors`, 6.7 GB). The shipped workflows send your prompt as written. Add the upsampler to the graph if you want short prompts expanded.

### MOSS-Image (SFT)

- **Purpose:** alternative text-to-image model (`moss-image`) and the first-frame stage of two-stage text-to-video (`ltx23-t2v-moss-{fast,pro}`). Needs ComfyUI 0.41.3 or newer.
- **HuggingFace repo:** [`Comfy-Org/MOSS-Image`](https://huggingface.co/Comfy-Org/MOSS-Image) (diffusion model, Qwen3.5 9B text encoder, small FLUX.2 VAE).
- **Upstream:** [OpenMOSS / MOSS-Image](https://github.com/OpenMOSS/MOSS-Image).
- **Licence:** Apache-2.0.
- **Files:** `moss_image_sft_int8_convrot.safetensors` (5.4 GB), `qwen3.5_9b_w4a8_gptq.safetensors` (7.3 GB), `flux2-vae_small.safetensors` (0.2 GB).
- **Approx size:** ~13 GB combined.

## Video generation (single-shot)

### LTX-2.5 22B distilled (fast + pro)

- **Purpose:** primary text-to-video / image-to-video / first-and-last-frame-to-video model. Needs ComfyUI 0.41 or newer.
- **Why this build:** the ComfyUI int8 + convrot export of the distilled transformer. At 21.5 GB it is half the size of bf16 (42 GB), runs on 24 GB cards (4090) as well as 5090, and avoids the NVFP4 build (18.7 GB), which only pays off on Blackwell and costs quality. The distilled model needs 8 steps at cfg 1 and no separate LoRA.
- **HuggingFace repo:** [`Lightricks/LTX-2.5`](https://huggingface.co/Lightricks/LTX-2.5). **Gated**, accept the licence while logged in before downloading.
- **Licence:** Lightricks LTX licence. Read the terms, there are restrictions on commercial use depending on revenue. **Your generations are your responsibility** under the LTX licence.
- **Files:** `ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors` (21.5 GB), `ltx-2.5-video-vae-bf16.safetensors` (1.5 GB), `ltx-2.5-audio-vae-bf16.safetensors` (0.4 GB).

### Gemma 4 12B text encoder (LTX-2.5, int8)

- **Purpose:** text encoder for LTX-2.5 (includes the projection head LTX needs). Loaded with the `ltxv` CLIP type.
- **HuggingFace repo:** [`Lightricks/LTX-2.5`](https://huggingface.co/Lightricks/LTX-2.5) (`text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors`).
- **Licence:** Google Gemma Terms of Use apply to the underlying model.
- **Approx size:** 15.4 GB.

### LTX-2.5 spatial upscaler (pro tier)

- **Purpose:** 2x latent upscaling stage used by the LTX-2.5 pro variants.
- **File:** `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` from [`Lightricks/LTX-2.5`](https://huggingface.co/Lightricks/LTX-2.5).
- **Approx size:** 1 GB.

### RealESRGAN x2plus

- **Purpose:** ESRGAN-class pixel-space 2× refiner used at the end of the LTX-2.3 pro pipeline.
- **HuggingFace repo:** [`2kpr/Real-ESRGAN`](https://huggingface.co/2kpr/Real-ESRGAN).
- **Licence:** BSD-3-Clause (academic-friendly, broad commercial reuse allowed).
- **Approx size:** ~64 MB.

## Music generation

### YuE2 3B

- **Purpose:** text-to-music for the `t2m` capability. Renders a full song
  (vocals + accompaniment) from a style prompt and optional lyric sheet, or
  instrumental, up to `maxDurationSeconds`.
- **HuggingFace repo:** [`Comfy-Org/YuE2`](https://huggingface.co/Comfy-Org/YuE2)
  (`checkpoints/yue2_3b_int8_convrot.safetensors` path in the manifest).
- **Upstream:** [Multimodal Art Projection / YuE](https://github.com/multimodal-art-projection/YuE).
- **Licence:** **CC BY-NC 4.0** with an additional individual-creator
  permission. Read the [MODEL_LICENSE](https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE).
  **This model is a deliberate exception to the "free for commercial use" bar
  below.** The individual-creator permission lets a person generating on their
  own machine use the model and monetise their own outputs; it does **not**
  grant commercial use by a company. This is why YuE2 ships as a **reference
  workflow for the user's own BYO server** and is not served from
  Loovie-operated infrastructure.
- **Files:** `yue2_3b_int8_convrot.safetensors`.
- **Approx size:** ~3.7 GB.

## Disk budget

These are **downloaded sizes**. Add roughly 5 to 10 GB of headroom for ComfyUI's cache, intermediate decoded outputs, swap files, and OS overhead. Plan a real disk budget that's higher than the downloaded total, especially on cloud-rented disks where you can't grow the volume on demand.

| `LOOVIE_KIND` | Downloaded | Plan for at least |
|---|---|---|
| `images` (FLUX 3 Klein + MOSS-Image bundles) | ~24 GB | 30 GB |
| `videos` (LTX-2.5 distilled int8 + Gemma 4 encoder + VAEs + upscaler + ESRGAN) | ~40 GB | 50 GB |
| `music` (YuE2 3B int8) | ~4 GB | 8 GB |
| `all` (all of the above) | ~68 GB | 80 GB |

Per-file approximate sizes used above: FLUX 3 Klein bundle ~11 GB and MOSS-Image bundle ~13 GB (each main + VAE + text encoder), LTX-2.5 distilled int8 transformer ~21.5 GB, Gemma 4 12B int8 encoder ~15.4 GB, video + audio VAEs ~1.9 GB, LTX-2.5 spatial upscaler ~1 GB, RealESRGAN ~64 MB, YuE2 3B int8 ~3.7 GB. These are rough figures from Comfy-Org's published builds; the exact bytes on disk depend on which point release of each repo you fetch. The truthful source of truth is what HuggingFace serves to your token; treat the numbers above as planning aids, not contracts.

## Adding a new model in a PR

If your workflow contribution ([`80-adding-a-workflow.md`](80-adding-a-workflow.md)) introduces a new model:

1. **Add a row to this file** with: purpose, HuggingFace repo, upstream link, licence name, gated yes/no, approx size.
2. **Add the manifest entry** in [`docker/models.manifest`](../docker/models.manifest) so the downloader picks it up.
3. **Update the disk budget table above.**
4. **Read the upstream licence yourself** and confirm it is OK for inclusion. The bar is roughly: free for commercial use, no "research only" or "non-commercial" clauses, HuggingFace gating is OK as long as the model is publicly accessible after acceptance. YuE2 is the one sanctioned exception to that bar: it ships as a BYO reference workflow only, because the individual-creator permission does not authorise company-operated serving.
5. **Open a [Workflow contribution](https://github.com/looviehq/loovie-community/issues/new?template=workflow_contribution.yml)** so a maintainer can sign off on the licence interpretation before you do the engineering.

## Common questions

**Why are the models packaged under `Comfy-Org/*` instead of their upstream repos?**

Because Comfy-Org ships single-file fp8-scaled variants that ComfyUI can load directly. The upstream repos publish sharded `.safetensors.index.json` sets that need a merge step before they work in ComfyUI's `CLIPLoader`. Pulling from `Comfy-Org/*` skips that step.

**Can I swap in different weights without changing the workflow?**

Sometimes. If the architecture is the same (e.g. another fp8-scaled Gemma-3 12B variant), drop it into the same target subdir and ComfyUI will pick it up. If the architecture differs, you also need to edit the workflow JSON to match.

**Does Loovie cache or proxy these models?**

No. Every download goes directly from your server to HuggingFace. Loovie has nothing to do with the bandwidth or the timing.
