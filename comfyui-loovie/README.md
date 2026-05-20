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
| `POST /images/create` | bearer | FLUX.2 Klein. Returns a `taskId`. |
| `GET  /images/status` | bearer | Polls a task by id. |
| `POST /videos/create` | bearer | LTX-2.3 single-shot video. Returns a `taskId`. |
| `GET  /videos/status` | bearer | Polls a task by id. |
| `POST /loovie/upload` | bearer | Operator helper for staging reference files. |

Workflows shipped (one JSON per file under `workflows/`):

| Family | Workflow | Modes |
| --- | --- | --- |
| Image | `flux-2-klein` | t2i, i2i (up to 4 reference images) |
| Video | `ltx23-t2v-{fast,pro}` | text-to-video |
| Video | `ltx23-i2v-{fast,pro}` | image-to-video |
| Video | `ltx23-fl2v-{fast,pro}` | first+last frame to video |

The capabilities manifest is built dynamically from the workflows you
register in `config.yaml`. Remove an entry to hide that capability from the
app; add a new one to extend the surface.

## Install

```bash
# 1. Clone into ComfyUI's custom_nodes directory
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/looviehq/loovie-community.git
ln -s loovie-community/comfyui-loovie loovie

# 2. Install Python deps (into ComfyUI's venv)
pip install -r loovie/requirements.txt

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
  proxy, etc.). The app and the server share a bearer token chosen by you;
  neither the token nor the URL is ever sent to Loovie infrastructure.
- Reference images are downloaded over HTTPS. Private/loopback IPs and
  non-HTTP(S) schemes are refused; downloaded payloads are sniffed for
  PNG/JPEG/WebP magic bytes before being handed to the graph.

## Models

The reference workflows expect the following weights to be present in
`ComfyUI/models/`. Install them once; the workflows reference them by
filename. The exact weight URLs are listed in
[`docs/MODELS.md`](../docs/MODELS.md) (TBD) and `scripts/install.sh` can
fetch a baseline set.

| Workflow | Required model files |
| --- | --- |
| `flux-2-klein` | FLUX.2 Klein UNet, T5-XXL + CLIP-L text encoders, FLUX VAE |
| `ltx23-*-fast` | LTX 2.3 distilled checkpoint, Gemma-3-12B text encoder |
| `ltx23-*-pro` | LTX 2.3 checkpoint + spatial upscaler, Gemma-3-12B text encoder |

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
