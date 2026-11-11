# Models

This page lists every model the **reference implementation** ([`comfyui-loovie/`](../comfyui-loovie/)) ships with, along with its upstream source and licence. Loovie does **not** relicense these models. **You are responsible for accepting each upstream licence before downloading and for honouring its terms when using the model.**

> **You are not required to use these models.** They are the ones we tested and currently ship workflows for. BYO is model-agnostic at the contract level: as long as your workflow's input shape matches what `/images/create`, `/videos/create`, or `/music/create` sends, and its output shape matches what `/{images,videos,music}/status` returns, you can run **any** image, video, or music model you have rights to run. Examples people have used or asked about: WAN 2.x, HunyuanVideo, CogVideoX, Mochi, AnimateDiff variants for video; SDXL, SD3.5, Stable Cascade, Lumina, HiDream for image; ACE-Step, YuE2, MusicGen for music; Stable Audio 3, AudioGen for sound effects. We don't promise to test all of them, but the contract doesn't care which one you use.

The downloader (`docker/download_models.sh`) reads [`docker/models.manifest`](../docker/models.manifest) and pulls the files from the HuggingFace repos below. Some of these are **gated**, meaning HuggingFace requires you to accept the licence on the web UI while logged in before the download will succeed. See [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md).

> **This list reflects the current `v0.1.x-beta` line.** Adding a model in a PR also means adding it here. If you want to add a new reference workflow built on a different model, see [`80-adding-a-workflow.md`](80-adding-a-workflow.md).

## Image generation

### FLUX.2 Klein (4B)

- **Purpose:** primary text-to-image and image-to-image model for the `loovie-custom` image tier.
- **HuggingFace repos:** [`black-forest-labs/FLUX.2-klein-4B`](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) (UNet), [`Comfy-Org/flux2-dev`](https://huggingface.co/Comfy-Org/flux2-dev) (VAE), [`Comfy-Org/flux2-klein-4B`](https://huggingface.co/Comfy-Org/flux2-klein-4B) (Qwen text encoder).
- **Upstream:** [Black Forest Labs / FLUX](https://github.com/black-forest-labs/flux).
- **Licence:** Black Forest Labs FLUX.2 Klein licence. **Gated on HuggingFace**, accept on the repo page while logged in before downloading. Read the terms.
- **Files:** `flux-2-klein-4b.safetensors`, `flux2-vae.safetensors`, `qwen_3_4b_flux2.safetensors`.
- **Approx size:** ~24 GB combined (includes the VAE and the Qwen-3 text encoder listed below).

### Qwen-3 text encoder for FLUX.2

- **Purpose:** text encoder used by FLUX.2 Klein.
- **HuggingFace repo:** [`Comfy-Org/flux2-klein-4B`](https://huggingface.co/Comfy-Org/flux2-klein-4B) (packaged Qwen encoder for Klein 4B).
- **Upstream:** [Alibaba Cloud Qwen](https://huggingface.co/Qwen).
- **Licence:** Apache-2.0 (Qwen) **but redistributed via the FLUX.2 gated repo**, so you accept the FLUX.2 page in practice.

### Qwen-Image 2.1 (7B)

- **HuggingFace:** `Comfy-Org/Qwen-Image-2.1` (ComfyUI repack).
- **Licence:** Apache-2.0 (Qwen).
- **Modes:** t2i, i2i, up to 10 references.
- **Planning VRAM:** 12 GB minimum, 24 GB recommended for 2K/reference work.
- **ComfyUI:** native since 0.37.0.

### FLUX 3 Image Klein (5.6B)

- **HuggingFace:** `black-forest-labs/flux-3-image-klein-comfy` (gated).
- **Licence:** FLUX Kommunity License. Accept it on that exact HF repo.
- **Modes:** t2i, i2i, up to 4 references in the ComfyUI template (10 in the model card).
- **Planning VRAM:** int8 fits an 8–12 GB card; 16 GB recommended.
- **ComfyUI:** native since 0.41.0.

### Krea 2 (12B)

- **HuggingFace:** `Comfy-Org/Krea-2` (ComfyUI repack).
- **Licence:** Krea AI Community License (gated).
- **Modes:** t2i (+ style reference). **No general i2i/edit path.**
- **Planning VRAM:** 16 GB minimum, 24 GB recommended.
- **ComfyUI:** native.

### MOSS-Image (5B)

- **HuggingFace:** OpenMOSS MOSS-Image / Comfy-Org repack.
- **Licence:** Apache-2.0.
- **Modes:** t2i, i2i, layout control, strong text rendering.
- **Planning VRAM:** 8–12 GB minimum, 16 GB recommended.
- **ComfyUI:** native.

## Video generation (single-shot)

### LTX-2.3 22B (legacy, fast + pro)

- **Purpose:** primary text-to-video / image-to-video / first-and-last-frame-to-video model for the `loovie-custom` video tier.
- **HuggingFace repos:** [`Lightricks/LTX-2.3-fp8`](https://huggingface.co/Lightricks/LTX-2.3-fp8) (main fp8 checkpoint), [`Lightricks/LTX-2.3`](https://huggingface.co/Lightricks/LTX-2.3) (distilled LoRA and spatial upscaler).
- **Licence:** Lightricks LTX community licence. Read the terms, there are restrictions on commercial use depending on the variant. Loovie's `comfyui-loovie/` repo only ships workflows; **your generations are your responsibility** under the LTX licence.
- **Files:** `ltx-2.3-22b-dev-fp8.safetensors` (main fp8 checkpoint), `ltx-2.3-22b-distilled-lora-384.safetensors` (rank-384 distilled LoRA used by the `pro` variant).
- **Approx size:** ~57 GB combined. The main fp8 checkpoint is roughly 22 GB on its own; the distilled LoRA at rank 384 is substantially larger than a typical LoRA because it carries enough capacity to materially change the model's output (closer to a model delta than a stylistic adapter).

### LTX-2.5 22B (default, fast)

- **HuggingFace:** `Lightricks/LTX-2.5` (gated; split pack).
- **Licence:** LTX-2.x Community License. Free for commercial use under $10M
  annual revenue; a paid licence is required above that. Read the terms.
- **Files:** `diffusion_models/ltx-2.5-22b-distilled-transformer-nvfp4.safetensors`,
  `text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors`, the conv video
  VAE and audio VAE, and `latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors`.
  These are the exact names in `comfyui-loovie/workflows/ltx25_*.json` and
  `docker/models.manifest`.
- **Modes:** t2v, i2v, fl2v, ref2v (ingredients), edit, retake, extend and
  motion, with synchronized audio and camera-move prompt conditioning; pro is
  still served by the LTX 2.3 legacy workflows until a 2.5 pro graph lands.
- **Advanced modes:** the shipped `ltx25-{edit,retake,extend,motion}-fast`
  graphs condition on a source clip with ComfyUI's core `LTXVAddGuide` node.
  `ref2v` composes up to four ingredient images into one reference sheet with
  `LoovieReferenceSheet`, repeats the sheet across the clip and applies the
  Ingredients IC-LoRA (`ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors`,
  strength 1.3) through `LoraLoaderModelOnly`. The 2.5 adapter is preferred
  when your HuggingFace account has access to
  `Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients`; swap the `lora_name` in the
  graph. An installed LTXVideo IC-LoRA (union control, ingredients,
  colourisation, …) can also be added through `LoovieLoraStack` for stronger
  identity or structure control on the other modes.
- **Planning VRAM:** 24 GB minimum, 32 GB recommended.
- **ComfyUI:** native LTX 2.5 templates; the shipped `ltx25_*` graphs are
  API-format with the Loovie node injection and were validated on a GB10.

### Pika H3 Flex (MiniMax H3)

- **HuggingFace:** `Pika-Labs/Pika-H3-Flex` adapters + `Comfy-Org/MiniMax-H3`
  base files. Gated/community licence applies to the adapters.
- **Licence:** MiniMax H3 Community License. It has territorial and
  commercial-use conditions; read it before selling outputs.
- **Files:** `minimax_h3_fl2va_pruned_fp8_scaled.safetensors` and
  `minimax_h3_ref2va_pruned_fp8_scaled.safetensors` (20 GB each),
  `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (15.7 GB),
  `minimax_h3_video_vae_fp16.safetensors`,
  `minimax_h3_audio_vae_fp32.safetensors`, and the Pika adapters
  (`pika_h3_flex_fl2va/ref2va_comfy_bf16`, turbo 4-step, HD 8-step; ~2–4 GB).
- **Modes:** t2v, i2v, fl2v, ref2v (up to 9 images, 3 videos, 3 audio clips).
  Local output is 384p / 480p / 540p / 768p (16:9, 9:16, 4:3, 3:4, 1:1),
  5–15 s, 24 fps, `17n + 5` frames, with audio.
- **Variants:** Pika's official 6-step, a 4-step turbo distill (draft quality),
  and an 8-step HD recipe (FL2VA only). The reference graphs use
  `MiniMaxH3ImageToVideo` + `LoraLoaderModelOnly`; `ref2v` uses
  `MiniMaxH3ReferenceToVideo` through the `LoovieH3ReferenceToVideo` adapter
  so the graph carries exactly the references the request supplied (0–9).
- **Planning VRAM:** 24 GB minimum with the low-VRAM attention nodes, 32 GB
  recommended; Pika's own reference run used ~66–69 GB on an H100 for a 5 s
  480p clip, and 9 references add several GB.
- **ComfyUI:** shipped `pika-flex-{t2v,i2v,fl2v,ref2v}-{official,turbo}.json`
  and `pika-flex-hd-{t2v,i2v,fl2v}-hd.json`. The official adapters come from
  `Comfy-Org/MiniMax-H3`; the turbo/HD adapters come from
  `Pika-Labs/Pika-H3-Flex-Turbo-LoRA`.

### HyperFlow H3 Flash (MiniMax H3 distill)

- **HuggingFace:** [`VideoRebirthAI/hyperflow-h3-flash`](https://huggingface.co/VideoRebirthAI/hyperflow-h3-flash)
  (GGUF transforms) + `Comfy-Org/MiniMax-H3` for the shared text encoder and
  VAEs. The **full 8-step HyperFlow LoRA** on the 31B base H3 is a separate
  model (`VideoRebirthAI/hyperflow`) and runs on the official diffusers
  pipeline, **not** in ComfyUI; this catalogue entry is the compressed 14B
  Flash model only.
- **Licence:** MiniMax H3 Community License. It has territorial and
  commercial-use conditions; read it before selling outputs. The licence
  excludes the EU, UK, South Korea and the US without MiniMax's prior
  authorization.
- **Files:** `minimax_h3_fl2va_hyperflow_flash_14b-Q4_K_M.gguf` (~9.1 GB),
  `minimax_h3_ref2va_hyperflow_flash_14b-Q4_K_M.gguf` (~9.2 GB), plus the
  shared `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (15.7 GB),
  `minimax_h3_video_vae_fp16.safetensors` and
  `minimax_h3_audio_vae_fp32.safetensors` from `Comfy-Org/MiniMax-H3`.
- **Modes:** t2v, i2v, fl2v, ref2v (up to 9 images, 3 videos, 3 audio clips).
  384p / 480p / 540p / 768p, 5–15 s, 24 fps, `17n + 5` frames, with audio.
- **Recipe:** three variants sharing one checkpoint: **Fast** (4-step,
  draft), **Flash** (6-step, default) and **HQ** (8-step). No CFG
  (`cfg = 1`).
- **Planning VRAM:** 24 GB minimum, 32 GB recommended. The Q4_K_M Flash
  transformer is ~9 GB instead of the ~20 GB full H3 DiT, but the shared
  text encoder/VAEs dominate the footprint.
- **ComfyUI:** needs `ComfyUI-GGUF` and
  [`ComfyUI-HyperFlow-Flash`](https://github.com/Video-Rebirth/ComfyUI-HyperFlow-Flash)
  (`HyperFlowGGUFLoader` + `HyperFlowSigmas`). The shipped
  `hyperflow-h3-flash-{t2v,i2v,fl2v,ref2v}-{fast,flash,hq}.json` graphs use
  the same `Loovie*` nodes as the Pika H3 workflows. Requires ComfyUI >=
  0.43.0; the repo's current Docker/quickstart pin (`v0.21.1`) predates the
  MiniMax H3 nodes and must be bumped before enabling either H3 family.

### Gemma-3 12B text encoder (fp8 scaled)

- **Purpose:** text encoder used by LTX-2.3. Without it, the video model cannot tokenise prompts.
- **HuggingFace repo:** [`Comfy-Org/ltx-2`](https://huggingface.co/Comfy-Org/ltx-2) (`split_files/text_encoders/...` path in the manifest).
- **Upstream:** [Google Gemma](https://huggingface.co/google/gemma-3-12b-it).
- **Licence:** Google [Gemma Terms of Use](https://ai.google.dev/gemma/terms). **Gated on HuggingFace**, accept on the upstream repo page while logged in before downloading. Read the terms; Gemma has its own acceptable-use policy.
- **Approx size:** ~12 GB.

### LTX-2.3 spatial upscaler (pro tier)

- **Purpose:** spatial upscaling stage used by the LTX-2.3 pro variants.
- **HuggingFace repo:** [`Lightricks/LTX-2.3`](https://huggingface.co/Lightricks/LTX-2.3).
- **Licence:** Lightricks LTX community licence (same as the main LTX checkpoint).
- **Approx size:** ~1 GB.

### RealESRGAN x2plus

- **Purpose:** ESRGAN-class pixel-space 2× refiner used at the end of the LTX-2.3 pro pipeline.
- **HuggingFace repo:** [`2kpr/Real-ESRGAN`](https://huggingface.co/2kpr/Real-ESRGAN).
- **Licence:** BSD-3-Clause (academic-friendly, broad commercial reuse allowed).
- **Approx size:** ~64 MB.

## Sound effects

### Stable Audio 3 Small SFX

- **Role:** short text-to-sound-effect and ambience renders (`t2s`, 1–60
  seconds) from a single prompt and optional negative prompt.
- **Files:** `checkpoints/stable_audio_3_small_sfx.safetensors` plus
  `text_encoders/t5gemma_b_b_ul2.safetensors`.
- **Workflow:** `workflows/stable_audio_3_sfx_small.json` (8-step LCM, MP3
  320 kbps output).
- **Planning VRAM:** 4 GB minimum, 8 GB recommended.

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
| `images` (FLUX.2 Klein bundle) | ~24 GB | 30 GB |
| `videos` (LTX-2.3 main + LoRA + Gemma encoder + upscaler + ESRGAN) | ~70 GB | 80 GB |
| `videos` + Pika H3 Flex + HD | ~166 GB | 180 GB |
| `videos` + Pika H3 Flex + HD + HyperFlow H3 Flash | ~191 GB | 210 GB |
| `music` (YuE2 3B int8) | ~4 GB | 8 GB |
| `sfx` (Stable Audio 3 Small SFX + T5Gemma) | ~3.4 GB | 8 GB |
| `all` (current video manifest + image + audio) | ~225 GB | 245 GB |

Per-file approximate sizes used above: FLUX.2 Klein bundle ~24 GB (main + VAE + Qwen encoder), LTX-2.3 22B main fp8 ~22 GB, LTX-2.3 22B distilled LoRA ~35 GB, Gemma-3 12B fp8 ~12 GB, LTX-2.3 spatial upscaler ~1 GB, RealESRGAN ~64 MB, Pika H3 base + adapters ~46 GB, HyperFlow H3 Flash Q4_K_M transformers ~18 GB plus the shared 15.7 GB text encoder and ~10 GB of VAEs, YuE2 3B int8 ~3.7 GB. These are rough figures from Comfy-Org's published builds; the exact bytes on disk depend on which point release of each repo you fetch. The truthful source of truth is what HuggingFace serves to your token; treat the numbers above as planning aids, not contracts.

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
