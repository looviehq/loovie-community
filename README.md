# Loovie Community

> The open contract and reference servers for the Loovie BYO (Bring Your Own) generation protocol. Run Loovie image and single-shot video generation on your own GPU.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-pre--beta%20scaffold-orange.svg)](CHANGELOG.md)

## Status

**Pre-beta scaffold.** This repo is being assembled in the open. The first usable release will be tagged `v0.1.0-beta`. Until then, the only things that work are the governance files you see here. Track progress in [CHANGELOG.md](CHANGELOG.md) and the [issues](https://github.com/looviehq/loovie-community/issues).

When `v0.1.0-beta` ships, this README will be replaced with the proper hero, quickstart, and repo map. Until then, here's what you can expect:

| Path | What it will be |
|---|---|
| `openapi/` | The normative HTTP contract a BYO server implements (OpenAPI 3.1). |
| `comfyui-loovie/` | Reference ComfyUI implementation (FLUX.2 Klein image + LTX-2.3 single-shot video). |
| `examples/minimal-server/` | A small FastAPI reference for non-ComfyUI implementers. |
| `docker/` | Dockerfile + a public RunPod template (one-click). |
| `docs/` | Setup, security, tunneling, troubleshooting, contribution guides. |

## Why this exists

Loovie is model-agnostic. BYO is the logical end of that: if you have the hardware, your generations should be yours, private, and free at the Loovie layer. The contract is published so anyone can implement a compatible server in any stack; ComfyUI is the reference we ship.

## Contributing

We use **DCO sign-off** (`git commit -s`), not a CLA. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

If you find a vulnerability, **do not file a public issue.** See [SECURITY.md](SECURITY.md).

## Community

Community-supported beta. The dedicated venue is the Loovie Discord — invite link will appear here once the server is open.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Bundled and referenced **models are not ours** — each has its own license. See `docs/MODELS.md` (ships with `v0.1.0-beta`).
