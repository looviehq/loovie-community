# Editing API-format workflow JSON

`comfyui-loovie/workflows/` ships **API-format** JSON only. There is no `workflows/ui/` directory. This page is the technical reference for authoring and editing those files.

## Why API format only

ComfyUI workflows have two export formats:

- **UI format**: what the editor saves by default. Includes node positions, group colours, link styles, and other editor state. About 3× the size, irrelevant at runtime, noisy in diffs.
- **API format**: what the server actually executes. Top-level keys are numeric node IDs; each node has `class_type` and `inputs`.

The repo's contract is "the API JSON is the workflow." UI JSON, if you want it for editing, is a local concern, author in the editor, export both formats locally, commit only the API one.

## Exporting API format from ComfyUI

1. In ComfyUI: **Settings** → enable **Dev mode options**.
2. Click the **⋯** menu in the top right.
3. Pick **Save (API Format)**.
4. Save the file with a clear name (e.g. `my-workflow.json`).

You'll know you got it right if the top-level keys are numeric strings (`"1"`, `"2"`, `"3"` …) and each value has a `class_type` and `inputs` object. If you see `pos`, `size`, `color`, `bgcolor`, or `groups`, you exported UI format, go back and pick *Save (API Format)*.

## The Loovie node `class_type`s

The Loovie server scans the workflow JSON by `class_type` and injects request values directly into the matching nodes. **No param maps. No `LOOVIE:` title prefixes. No external config.** The presence of the node is what makes the workflow Loovie-compatible.

| Node `class_type` | Inputs the server injects | Outputs |
|---|---|---|
| `LoovieTextInput` | `prompt`, `negative_prompt` | `PROMPT`, `NEGATIVE` |
| `LoovieSettings` | `aspect_ratio`, `seed` | `WIDTH`, `HEIGHT`, `SEED` |
| `LoovieVideoSettings` | `aspect_ratio`, `resolution`, `duration`, `with_audio`, `seed` | `WIDTH`, `HEIGHT`, `NUM_FRAMES`, `FPS`, `AUDIO_FRAMES`, `AUDIO_FPS`, `AUDIO_ENABLED`, `SEED` |
| `LoovieImageInput` | `image_url_1` … `image_url_N`, `mask_url` | `IMAGES`, `LATENT`, `IMAGE_COUNT`, `MASK`, `HAS_MASK`, plus per-slot variants |
| `LoovieLoraStack` | `lora_name_1`..`lora_name_5`, `strength_1`..`strength_5` | `MODEL`, `CLIP` |
| `LoovieAudioGate` | (gated by `AUDIO_ENABLED` from `LoovieVideoSettings`) | passthrough `AUDIO` |
| `LoovieVideoInput` | `video_url`, `max_frames` | `FRAMES`, `AUDIO`, `FRAME_COUNT`, `WIDTH`, `HEIGHT`, `FPS_INT`, `FPS`, `FIRST_FRAME`, `LAST_FRAME` |

For a complete reference of what each node does internally, see [`comfyui-loovie/README.md`](../comfyui-loovie/README.md).

## Safe edits vs. risky edits

| Edit | Safety |
|---|---|
| Change a numeric input on an existing node (CFG, steps, sampler/scheduler name) | **Safe**, sub-second to diff, low risk of breaking shape. PR-able. |
| Add or replace a LoRA entry | **Safe**, covered by the existing `LoovieLoraStack` slot mechanism. |
| Add a new model checkpoint | **Safe**, but also update [`MODELS.md`](MODELS.md) and the downloader manifest. |
| Add or remove a Loovie node | **Risky**, changes what the server can inject. Test all relevant request shapes (t2i, i2i with refs, etc.). |
| Rewire edges between nodes | **Risky**, easy to silently produce a workflow that runs but produces wrong output. Include a test prompt in the PR. |
| Change the `class_type` of a Loovie node to something custom | **Don't.** The server matches by `class_type`. Custom names are invisible. |

## Re-exporting an existing workflow

ComfyUI's exporter can shuffle node IDs between exports even when no semantic change occurred. To make diffs reviewable:

1. Run the new export through `jq -S '.'` to stabilise key order:

   ```sh
   jq -S '.' my-workflow.json > /tmp/sorted.json && mv /tmp/sorted.json my-workflow.json
   ```

2. Diff against the previous version:

   ```sh
   git diff --no-color comfyui-loovie/workflows/my-workflow.json | head -50
   ```

3. Read the diff. Confirm only the fields you intended to touch changed.

If you see unexpected re-numbering of node IDs across the whole file, you probably accidentally created and deleted a node during the edit. Re-export from a clean editor state.

## Validating the JSON

Just check it parses:

```sh
python -c "import json; json.load(open('comfyui-loovie/workflows/my-workflow.json'))" && echo OK
```

CI runs this on every PR. Beyond JSON syntax, there is no schema validation for ComfyUI workflows themselves, ComfyUI's own loader is the validator at runtime. A workflow that parses as JSON but is structurally broken will fail at first generation; verify locally before opening the PR.

## Locating an existing node in the workflow

If you need to find which node ID corresponds to a `class_type`:

```sh
jq -r 'to_entries | map(select(.value.class_type | startswith("Loovie"))) | .[] | "\(.key): \(.value.class_type)"' \
   comfyui-loovie/workflows/my-workflow.json
```

Or for a specific class:

```sh
jq -r '. | to_entries | map(select(.value.class_type == "LoovieSettings"))' \
   comfyui-loovie/workflows/my-workflow.json
```

## Adding new spec values

If your workflow needs to advertise a new variant, mode, resolution, or aspect ratio that the [OpenAPI spec](../openapi/loovie-server.openapi.yaml) does not already list, **that is a spec change, not a workflow change**. Open a **[Spec change](https://github.com/looviehq/loovie-community/issues/new?template=spec_change.yml)** issue first; bump `info.version` and possibly `schemaVersion`. See the beta API stability note in [the README](../README.md#beta-api-stability--read-this-before-you-depend-on-the-contract).
