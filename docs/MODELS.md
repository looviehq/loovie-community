# Models

This page lists every model the **reference implementation** ([`comfyui-loovie/`](../comfyui-loovie/)) ships with, along with its upstream source and licence. Loovie does **not** relicense these models. **You are responsible for accepting each upstream licence before downloading and for honouring its terms when using the model.**

> **You are not required to use these models.** They are the ones we tested and currently ship workflows for. BYO is model-agnostic at the contract level: as long as your workflow's input shape matches what `/images/create` or `/videos/create` sends, and its output shape matches what `/{images,videos}/status` returns, you can run **any** image or video model you have rights to run. Examples people have used or asked about: WAN 2.x, HunyuanVideo, CogVideoX, Mochi, AnimateDiff variants for video; SDXL, SD3.5, Stable Cascade, Lumina, HiDream for image. We don't promise to test all of them, but the contract doesn't care which one you use.

The downloader (`docker/download_models.sh`) reads [`docker/models.manifest`](../docker/models.manifest) and pulls the files from the HuggingFace repos below. Some of these are **gated**, meaning HuggingFace requires you to accept the licence on the web UI while logged in before the download will succeed. See [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md).

> **This list reflects the current `v0.1.x-beta` line.** Adding a model in a PR also means adding it here. If you want to add a new reference workflow built on a different model, see [`80-adding-a-workflow.md`](80-adding-a-workflow.md).

## Image generation

### FLUX.2 Klein (4B)

- **Purpose:** primary text-to-image and image-to-image model for the `loovie-custom` image tier.
- **HuggingFace repo:** [`Comfy-Org/flux2`](https://huggingface.co/Comfy-Org/flux2) (Comfy-Org's packaged-for-ComfyUI build).
- **Upstream:** [Black Forest Labs / FLUX](https://github.com/black-forest-labs/flux).
- **Licence:** Black Forest Labs FLUX.2 Klein licence. **Gated on HuggingFace**, accept on the repo page while logged in before downloading. Read the terms.
- **Files:** `flux-2-klein-4b.safetensors`, `flux2-vae.safetensors`, `qwen_3_4b_flux2.safetensors`.
- **Approx size:** ~24 GB combined.

### Qwen-3 text encoder for FLUX.2

- **Purpose:** text encoder used by FLUX.2 Klein.
- **HuggingFace repo:** [`Comfy-Org/flux2`](https://huggingface.co/Comfy-Org/flux2) (packaged with the rest of the FLUX.2 set).
- **Upstream:** [Alibaba Cloud Qwen](https://huggingface.co/Qwen).
- **Licence:** Apache-2.0 (Qwen) **but redistributed via the FLUX.2 gated repo**, so you accept the FLUX.2 page in practice.

## Video generation (single-shot)

### LTX-2.3 22B (fast + pro)

- **Purpose:** primary text-to-video / image-to-video / first-and-last-frame-to-video model for the `loovie-custom` video tier.
- **HuggingFace repo:** [`Comfy-Org/ltx-2`](https://huggingface.co/Comfy-Org/ltx-2) (Comfy-Org's packaged-for-ComfyUI build of [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video)).
- **Licence:** Lightricks LTX community licence. Read the terms, there are restrictions on commercial use depending on the variant. Loovie's `comfyui-loovie/` repo only ships workflows; **your generations are your responsibility** under the LTX licence.
- **Files:** `ltx-2.3-22b-dev-fp8.safetensors`, `ltx-2.3-22b-distilled-lora-384.safetensors`.
- **Approx size:** ~37 GB combined.

### Gemma-3 12B text encoder (fp8 scaled)

- **Purpose:** text encoder used by LTX-2.3. Without it, the video model cannot tokenise prompts.
- **HuggingFace repo:** [`Comfy-Org/ltx-2`](https://huggingface.co/Comfy-Org/ltx-2) (the merged single-file variant Lightricks ships alongside LTX-2.3).
- **Upstream:** [Google Gemma](https://huggingface.co/google/gemma-3-12b-it).
- **Licence:** Google [Gemma Terms of Use](https://ai.google.dev/gemma/terms). **Gated on HuggingFace**, accept on the upstream repo page while logged in before downloading. Read the terms; Gemma has its own acceptable-use policy.
- **Approx size:** ~13 GB.

### LTX-2.3 spatial upscaler (pro tier)

- **Purpose:** spatial upscaling stage used by the LTX-2.3 pro variants.
- **HuggingFace repo:** [`Comfy-Org/ltx-2`](https://huggingface.co/Comfy-Org/ltx-2).
- **Licence:** Lightricks LTX community licence (same as the main LTX checkpoint).
- **Approx size:** ~700 MB.

### RealESRGAN x2plus

- **Purpose:** ESRGAN-class pixel-space 2× refiner used at the end of the LTX-2.3 pro pipeline.
- **HuggingFace repo:** [`xinntao/Real-ESRGAN`](https://huggingface.co/xinntao/Real-ESRGAN).
- **Licence:** BSD-3-Clause (academic-friendly, broad commercial reuse allowed).
- **Approx size:** ~64 MB.

## Disk budget

| `LOOVIE_KIND` | Approx total |
|---|---|
| `images` | ~24 GB |
| `videos` (fast tier only) | ~50 GB |
| `videos` (with pro upscaler + ESRGAN) | ~52 GB |
| `all` | ~76 GB |

Pre-allocate at least 80 GB if you choose `all`.

## Adding a new model in a PR

If your workflow contribution ([`80-adding-a-workflow.md`](80-adding-a-workflow.md)) introduces a new model:

1. **Add a row to this file** with: purpose, HuggingFace repo, upstream link, licence name, gated yes/no, approx size.
2. **Add the manifest entry** in [`docker/models.manifest`](../docker/models.manifest) so the downloader picks it up.
3. **Update the disk budget table above.**
4. **Read the upstream licence yourself** and confirm it is OK for inclusion. The bar is roughly: free for commercial use, no "research only" or "non-commercial" clauses, HuggingFace gating is OK as long as the model is publicly accessible after acceptance.
5. **Open a [Workflow contribution](https://github.com/looviehq/loovie-community/issues/new?template=workflow_contribution.yml)** so a maintainer can sign off on the licence interpretation before you do the engineering.

## Common questions

**Why are the models packaged under `Comfy-Org/*` instead of their upstream repos?**

Because Comfy-Org ships single-file fp8-scaled variants that ComfyUI can load directly. The upstream repos publish sharded `.safetensors.index.json` sets that need a merge step before they work in ComfyUI's `CLIPLoader`. Pulling from `Comfy-Org/*` skips that step.

**Can I swap in different weights without changing the workflow?**

Sometimes. If the architecture is the same (e.g. another fp8-scaled Gemma-3 12B variant), drop it into the same target subdir and ComfyUI will pick it up. If the architecture differs, you also need to edit the workflow JSON to match.

**Does Loovie cache or proxy these models?**

No. Every download goes directly from your server to HuggingFace. Loovie has nothing to do with the bandwidth or the timing.
