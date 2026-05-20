# Overview

**Loovie BYO** ("Bring Your Own" server) lets you run Loovie's image and single-shot video generation on **any HTTP server you control** that implements [the contract](90-the-contract.md). In the Loovie iOS app it appears as *Your server (BYO)* under image and video quality. Generations run on your hardware, so **Loovie itself charges you nothing for them.** If you rent a GPU (for example, RunPod), that provider charges you for compute.

> **Status: public beta. Free in the app while in beta** (no subscription, no credits). After beta we expect to introduce a small flat-fee "BYO Pass" subscription; generations stay 0 credits forever.
>
> **Privacy.** Your server URL and bearer token live in the Loovie app on your device only, because the app is what calls your server. They are never sent to Loovie's backend servers and are not accessible to Loovie staff. See [`15-terms-and-privacy.md`](15-terms-and-privacy.md).

## Pick a hosting path

| Path | When it fits | Cost | What you need |
|---|---|---|---|
| **1. Your own machine** | You have an NVIDIA GPU with at least 24 GB VRAM and don't mind using the server only when you are on the same network or running a tunnel. | Electricity. | NVIDIA GPU, Linux/Windows/macOS, ~70 GB disk, Python, git, a [HuggingFace token](25-huggingface-and-gated-models.md). |
| **2. RunPod (rented GPU)** | You don't have a GPU, or want the server always reachable from anywhere. | Per-minute GPU pricing from RunPod (Loovie charges nothing). | A RunPod account, a HuggingFace token, ~10 minutes to set up. |
| **3. Your machine + Cloudflare Tunnel** | You have a GPU at home and want to reach it from your phone on cellular without exposing your home IP. | Electricity + a Cloudflare account (free). | Same as path 1 plus a few minutes to set up `cloudflared`. |

Decision rule: have a beefy NVIDIA GPU and want the cheapest option? Path 1 or 3. No GPU? Path 2. On a Mac or older GPU and just want to try it? Path 2 again, with a smaller GPU and a quick stop after.

## GPU compatibility (tested at launch)

- **Image models:** verified on **RTX 4090** and **RTX 5090**.
- **Video models:** verified **only on RTX 5090** at launch. Other GPUs may work but are unverified.

We expect the 4090 to handle the `fast` video variant once we have more time on it; we are not promising that yet.

## What's in the rest of these docs

1. [`10-create-a-loovie-account.md`](10-create-a-loovie-account.md) — make an account in the Loovie iOS app (no web signup).
2. [`15-terms-and-privacy.md`](15-terms-and-privacy.md) — what we store about a BYO generation and what we explicitly do not.
3. [`20-quickstart-your-own-machine.md`](20-quickstart-your-own-machine.md) — install ComfyUI, plug in `comfyui-loovie`, generate locally.
4. [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md) — HuggingFace token + accepting gated model licenses.
5. [`30-runpod.md`](30-runpod.md) — the rented-GPU path, with the Loovie referral link.
6. [`40-cloudflare-tunnel.md`](40-cloudflare-tunnel.md) — make a home server reachable from your phone.
7. [`50-security-and-tokens.md`](50-security-and-tokens.md) — required reading before opening any port.
8. [`60-configure-the-app.md`](60-configure-the-app.md) — paste URL + token into Loovie, pick *Your server (BYO)*.
9. [`70-troubleshooting.md`](70-troubleshooting.md) — symptom-to-fix table.
10. [`80-adding-a-workflow.md`](80-adding-a-workflow.md) — contribute a new workflow.
11. [`85-editing-api-workflows.md`](85-editing-api-workflows.md) — how to author or edit a workflow JSON.
12. [`90-the-contract.md`](90-the-contract.md) — human-readable mirror of the OpenAPI spec.
13. [`MODELS.md`](MODELS.md) — every model the reference implementation pulls, its license, gated status.

## Honest expectations

- **When BYO fails, it is your server, your network, or your hardware.** The Loovie team cannot fix your box. The repo docs are your primary support; a community Discord opens with the `v0.1.0-beta` release (the invite goes in [README → Community](../README.md#community) once live).
- **If the Loovie app misbehaves, that is on us.** Open a bug in the [issues](https://github.com/looviehq/loovie-community/issues) or ping `#bugs` on Discord.
- **The contract may break in minor 0.x bumps.** Pin to a specific tag or commit SHA if you depend on it. See [README](../README.md#beta-api-stability--read-this-before-you-depend-on-the-contract).
