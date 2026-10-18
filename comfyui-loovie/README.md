# comfyui-loovie

Reference ComfyUI implementation of the Loovie BYO server contract.

This package is a ComfyUI custom-node extension that registers a small set of
HTTP routes (`/loovie/health`, `/loovie/capabilities`, `/images/create`,
`/images/status`, `/videos/create`, `/videos/status`, `/loovie/upload`) on
ComfyUI's built-in aiohttp server. The Loovie mobile app talks to these
routes directly; the contract is defined by
[`openapi/loovie-server.openapi.yaml`](../openapi/loovie-server.openapi.yaml).

You do not have to use this implementation. Any server that implements the
OpenAPI contract is valid. This one is provided as a working starting point.

## What's in the box

| Endpoint | Auth | Notes |
| --- | --- | --- |
| `GET  /loovie/health` | public | Liveness + readiness phase. |
| `GET  /loovie/capabilities` | public | Manifest derived from installed workflows. |
| `POST /images/create` | bearer | FLUX 3 Klein. Returns a `taskId`. |
| `GET  /images/status` | bearer | Polls a task by id. |
| `POST /videos/create` | bearer | LTX-2.5 single-shot video. Returns a `taskId`. |
| `GET  /videos/status` | bearer | Polls a task by id. |
| `POST /loovie/upload` | bearer | Operator helper for staging reference files. |

Workflows shipped (one JSON per file under `workflows/`):

| Family | Workflow | Modes |
| --- | --- | --- |
| Image | `flux-3-klein` | t2i |
| Image | `flux-3-klein-edit` | i2i (reference images) |
| Image | `moss-image` | t2i (send `image_model: "moss-image"`) |
| Video | `ltx25-t2v-moss-{fast,pro}` | text-to-video with a MOSS-Image first frame (send `image_model: "moss-image"`) |
| Video | `ltx25-t2v-{fast,pro}` | text-to-video |
| Video | `ltx25-i2v-{fast,pro}` | image-to-video |
| Video | `ltx25-fl2v-{fast,pro}` | first+last frame to video |

The capabilities manifest is built dynamically from the workflows you
register in `config.yaml`. Remove an entry to hide that capability from the
app; add a new one to extend the surface.

## Install

```bash
# 1. From your ComfyUI checkout (clone the repo beside custom_nodes/, not inside it)
cd /path/to/ComfyUI
git clone https://github.com/looviehq/loovie-community.git
ln -s ../loovie-community/comfyui-loovie custom_nodes/loovie

# 2. Install Python deps (into ComfyUI's venv)
pip install -r loovie-community/comfyui-loovie/requirements.txt

# 3. Configure the bearer token
export LOOVIE_API_TOKEN="$(openssl rand -hex 32)"

# 4. Start ComfyUI as usual
python main.py --listen 0.0.0.0 --port 8188
```

Or, from a checkout of this repo, run `scripts/install.sh` to symlink the
package into `ComfyUI/custom_nodes/loovie` and (optionally) seed the model
weights the shipped workflows require.

## Security

- Set `LOOVIE_API_TOKEN` to a long random string. If the token is unset,
  the server refuses remote requests (`401 Unauthorized`) and only serves
  loopback callers. `/loovie/health` and `/loovie/capabilities` are
  intentionally public so the app can probe before authenticating.
- Run ComfyUI behind your own tunnel (Cloudflare Tunnel, Tailscale, RunPod
  proxy, etc.). The app and the server share a bearer token chosen by you.
  The Loovie app on the user's device stores the URL and token so it can
  call your server; **they are never sent to Loovie's backend servers and
  are not accessible to Loovie staff.**
- Reference images are downloaded over HTTPS. Private/loopback IPs and
  non-HTTP(S) schemes are refused; downloaded payloads are sniffed for
  PNG/JPEG/WebP magic bytes before being handed to the graph.

## Models

The reference workflows expect the following weights to be present in
`ComfyUI/models/`. Install them once; the workflows reference them by
filename. The exact weight URLs are listed in
[`docs/MODELS.md`](../docs/MODELS.md) (TBD) and `scripts/install.sh` can
fetch a baseline set.

Downloads need `HF_TOKEN` (a HuggingFace read token) set in the environment, and the
licences for `black-forest-labs/flux-3-image-klein-comfy` and `Lightricks/LTX-2.5` accepted
on HuggingFace first. See
[`docs/25-huggingface-and-gated-models.md`](../docs/25-huggingface-and-gated-models.md).

| Workflow | Required model files |
| --- | --- |
| `flux-3-klein`, `flux-3-klein-edit` | FLUX 3 Image Klein (distilled int8), Qwen3-VL 4B text encoder, FLUX.2 VAE |
| `moss-image` | MOSS-Image SFT int8, Qwen3.5 9B text encoder, small FLUX.2 VAE |
| `ltx25-t2v-moss-*` | MOSS-Image files above plus the matching `ltx25-*` files |
| `ltx25-*-fast` | LTX 2.5 distilled int8 transformer, video + audio VAEs, Gemma 4 12B text encoder |
| `ltx25-*-pro` | Same as fast, plus the LTX 2.5 spatial upscaler and RealESRGAN x2plus |

## Extending

- Add a workflow: export from ComfyUI as API-format JSON, drop it under
  `workflows/`, register it in `config.yaml`.
- Add a node: subclass under `src/comfyui_loovie/nodes/`, register it in
  `src/comfyui_loovie/nodes/__init__.py`.
- LLM-based prompt routing, vision routing, and SAM-3 cutout tooling are
  planned for a follow-up release.

## Contributing

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) in the repository root.

Licensed under Apache-2.0. See [`LICENSE`](LICENSE).
