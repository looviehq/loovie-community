# Loovie BYO — Legal in plain words

This is a plain-language summary, not a contract. The binding documents live at
[https://loovie.app/terms](https://loovie.app/terms) and
[https://loovie.app/privacy](https://loovie.app/privacy).

## What Loovie does in BYO

Loovie provides the user interface (the iOS app) that lets you send prompts to **your own server** and view the results. The Loovie API only mediates job metadata and stores the final media you generate, exactly as it does for any other Loovie generation. **Loovie never receives your server URL or your bearer token.**

## What you are responsible for

- Anything generated on your BYO server. Loovie has no ability to limit, constrain, or moderate what runs on hardware we don't control.
- The license obligations of every model you load on your server (see `docs/MODELS.md` once it ships).
- Operating your server safely: token, HTTPS, network exposure. See [SECURITY.md](SECURITY.md).
- The cost of any GPU you rent (for example, RunPod). Loovie does not charge for BYO generations, but third-party providers will charge you for compute.

## What Loovie supports

- **The Loovie app itself.** If the app misbehaves, open an issue on the Loovie support channels or ping Discord `#bugs`.
- **The published contract** (`openapi/loovie-server.openapi.yaml`) and this repo's reference implementations.

## What Loovie does NOT support

- Troubleshooting your BYO server, your ComfyUI installation, GPU drivers, model downloads, your network, your cloud provider, or workflows you modified. The community can help on Discord; Loovie staff cannot.

## What we store about a BYO generation

We store the same generation metadata and final output media we store for any Loovie generation. The exhaustive list lives at [https://loovie.app/privacy](https://loovie.app/privacy); we summarise it in `docs/15-terms-and-privacy.md` once it ships.

**We do NOT store:**

- Your server URL.
- Your bearer token.
- Intermediate frames or any traffic between the Loovie app and your server.
