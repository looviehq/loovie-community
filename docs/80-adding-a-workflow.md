# Adding a workflow

This is the contribution recipe for adding a new ComfyUI workflow to [`comfyui-loovie/`](../comfyui-loovie/). For example: a different sampler config, a new LoRA stack, or **a different model entirely** (WAN, HunyuanVideo, CogVideoX, SDXL, SD3.5, Stable Cascade, your own fine-tune, anything that runs in ComfyUI). The reference workflows we ship use FLUX.2 Klein and LTX-2.3 because that's what we've tested at launch, but the contract has no opinion on which model your workflow uses, only on the request/response shape.

For implementing the contract in a stack other than ComfyUI (Wan2GP, a hand-rolled FastAPI / Express / Go server, etc.), see [`90-the-contract.md`](90-the-contract.md) instead.

The technical details of editing the workflow JSON live in [`85-editing-api-workflows.md`](85-editing-api-workflows.md). This page is the contributor checklist.

## Before you start

- Read [`90-the-contract.md`](90-the-contract.md) so you know what the server must advertise + accept.
- Read [`85-editing-api-workflows.md`](85-editing-api-workflows.md), short, covers exporting API-format JSON and the required Loovie node `class_type`s.
- Read [`MODELS.md`](MODELS.md) for the model-licence rules. If your workflow introduces a new model, you are also adding a licence row.

## Recipe

### 1. Author the workflow in ComfyUI

Open ComfyUI on your dev machine. Build the workflow in the editor. Save it under a name you'll recognise. Test it end-to-end with the inputs the Loovie app will send: a prompt, an aspect ratio, optional reference images.

### 2. Include the required Loovie node `class_type`s

The route layer injects request values into the workflow by `class_type`. **No param maps, no `LOOVIE:` titles, no path-driven config.** Your workflow must include the relevant nodes:

| If your workflow needs | Include a node with `class_type` |
|---|---|
| Prompt + negative prompt | `LoovieTextInput` |
| Aspect ratio → width/height + seed (image) | `LoovieSettings` |
| Aspect ratio → width/height + duration/audio (video) | `LoovieVideoSettings` |
| Reference images for i2i | `LoovieImageInput` |
| Start frame for i2v or fl2v | `LoovieImageInput` (frame 1) |
| LoRA stack | `LoovieLoraStack` |
| Reference video (advanced cases) | `LoovieVideoInput` |
| Audio toggle for LTX | `LoovieAudioGate` |

The full input/output reference is in [`comfyui-loovie/README.md`](../comfyui-loovie/README.md).

### 3. Export in API format

Settings → enable *Dev mode options* → ⋯ menu → **Save (API Format)**. The exported JSON has numeric node IDs at the top level and per-node `class_type` + `inputs` keys. We do **not** ship UI format (`workflows/ui/`), see [`85-editing-api-workflows.md`](85-editing-api-workflows.md).

Place the JSON at `comfyui-loovie/workflows/<your-workflow-name>.json`.

### 4. Register the workflow in `config.yaml`

Add an entry under `workflows:` with a `max_wait_seconds` budget:

```yaml
workflows:
  # ...
  my-new-workflow:
    file: my-new-workflow.json
    max_wait_seconds: 300
```

### 5. Update capabilities if you advertise new modes/variants/resolutions

`src/comfyui_loovie/capabilities.py` is what generates the `/loovie/capabilities` response. If your workflow introduces a new mode (e.g. a new variant string), make sure it's already in the OpenAPI's closed enums in [`openapi/loovie-server.openapi.yaml`](../openapi/loovie-server.openapi.yaml). If it isn't, you're proposing a spec change, open a separate issue using the **[Spec change](https://github.com/looviehq/loovie-community/issues/new?template=spec_change.yml)** template, and bump `info.version` and `schemaVersion`. See [the beta API stability section of the README](../README.md#beta-api-stability--read-this-before-you-depend-on-the-contract).

### 6. Test locally

Run the server locally per [`20-quickstart-your-own-machine.md`](20-quickstart-your-own-machine.md). Verify:

- `curl http://localhost:8188/loovie/capabilities | jq .` includes your workflow's parameters in `variants` / `aspectRatios` / `durations` / etc.
- A test request (against the minimal example: `curl -X POST http://localhost:8188/images/create -H "Authorization: Bearer $LOOVIE_API_TOKEN" -d '{"prompt":"test", "mode":"t2i", "variant":"<your-variant>"}'`) returns a `taskId` and polling that taskId eventually returns `state: success`.

### 7. Open a PR

Use the **[Workflow contribution](https://github.com/looviehq/loovie-community/issues/new?template=workflow_contribution.yml)** issue template to discuss first if it's a substantial addition, or open a PR directly for a small change.

In your PR description include:

- **What the workflow does** in one sentence.
- **Which models it uses** with HuggingFace repos and licence names. New entries should also be added to [`MODELS.md`](MODELS.md).
- **A test prompt + expected qualitative output.** "A red bicycle in front of a Parisian café → a sharp 1024x576 PNG with the right composition" is fine; we are not asking you to ship reference images.
- **DCO sign-off** on every commit (`git commit -s`). The `dco` status check blocks merges without it.
- **Conventional Commits** on the subject (`feat(comfyui-loovie): add <your-workflow-name>`).

## Support boundary

- **Workflows that ship in `comfyui-loovie/workflows/`** are reviewed and supported by the project (community-supported, best effort, no SLA, see [`CONTRIBUTING.md`](../CONTRIBUTING.md#status-community-supported-beta-no-sla)).
- **Custom workflows you keep locally** are entirely yours. The Discord can help; project maintainers cannot. This is the same boundary as any other ComfyUI custom node.

## Model licence obligations

Every model you add ships with a licence. **You are responsible for confirming the licence permits the use case** before opening the PR. Common landmines:

- "Research only" or "non-commercial" terms on some weights. We do not accept these in `comfyui-loovie/` because BYO users may be commercial.
- Gated HuggingFace repos that require account-level acceptance, those are fine, but document the gating in `MODELS.md` and the downloader manifest.

When in doubt, ask in `#byo-workflows` on Discord before doing the engineering work.
