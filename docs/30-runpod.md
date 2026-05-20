# Run on RunPod (rented GPU)

This is the fastest path if you don't have a beefy NVIDIA GPU at home, or want the server always reachable from anywhere. RunPod rents you a GPU by the minute and gives you an HTTPS URL out of the box.

> **RunPod bills you for GPU time. Loovie itself charges nothing for BYO generations.** RunPod pricing is per-minute, so if you forget to stop your pod, you keep paying RunPod. Always stop the pod when you are done.
>
> **GPU compatibility (tested at launch).** Image models verified on RTX 4090 and 5090. Video models verified **only** on RTX 5090. Other GPUs may work but are unverified.
>
> **Referral disclosure.** Links in this doc use Loovie's RunPod referral (`?ref=vg16q1rz`). Using them supports Loovie at no extra cost to you.

## Step 1 — Create a RunPod account

[Create a RunPod account](https://runpod.io?ref=vg16q1rz). Verify your email. Add a credit card — RunPod is pay-as-you-go.

## Step 2 — Get a HuggingFace token and accept the gated licences

See [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md). You will paste the token into the pod's secrets in step 5. Skipping this step means the first-boot model download fails with `HTTP 401`.

## Step 3 — Generate a server token locally

```sh
git clone https://github.com/looviehq/loovie-community.git
cd loovie-community
bash scripts/new-token.sh
```

Copy the output. You will paste it as `LOOVIE_API_TOKEN` in step 5.

## Step 4 — Deploy the template

Two options:

- **One-click (preferred, once published).** A *Deploy to RunPod* button will appear here once the template lands in RunPod's public catalogue. Until then, use option B.
- **Manual import.** In the RunPod console, *Settings → Templates → New Template*, paste the contents of [`docker/runpod-template.json`](../docker/runpod-template.json), save.

Either way, when launching a pod from this template:

- **Container image:** `ghcr.io/looviehq/loovie-server:beta` (already set by the template).
- **Exposed port:** `8188/http` (already set).
- **Volume:** 80 GB at `/runpod-volume`.

## Step 5 — Pick a GPU and set the secrets

Per the GPU compat note above, pick a GPU your workload supports:

| GPU | VRAM | Image | Video |
|---|---|---|---|
| RTX 4090 | 24 GB | Verified | Unverified at launch |
| RTX 5090 | 32 GB | Verified | Verified |
| A6000 / L40S / A100 | 48 GB | Should work | Should work (untested) |

When launching, set the two required secrets:

- `LOOVIE_API_TOKEN` — the token from step 3.
- `HF_TOKEN` — your HuggingFace read token from step 2.

Leave the other variables at their defaults unless you want to download fewer models:

- `DOWNLOAD_MODELS=1` — auto-download on first boot.
- `LOOVIE_KIND=all` — pull both image and video model sets. Switch to `images` or `videos` for a smaller cache.

## Step 6 — First boot

Click *Deploy* and wait. First boot downloads model weights into the attached volume; this typically takes 15 to 40 minutes depending on GPU class and HuggingFace bandwidth. Watch the pod logs — the entrypoint prints a status banner at the start and a model-availability summary after the downloader runs.

The health endpoint reports phases as the boot progresses:

- `phase: booting_up` — container is starting, ComfyUI not yet up.
- `phase: downloading_models` — downloader is running.
- `phase: ready` — ComfyUI is serving on port 8188.

You can poll it with `curl -s https://<pod-id>-8188.proxy.runpod.net/loovie/health | jq .` from your laptop.

Subsequent boots reuse the volume and start in under a minute. Keep `DOWNLOAD_MODELS=1` even on later boots — the downloader skips files that are already present, so it just verifies and exits.

## Step 7 — Copy the proxy URL into the app

Once `phase: ready`, RunPod exposes the pod at:

```text
https://<pod-id>-8188.proxy.runpod.net
```

In the Loovie app: *Preferences → BYO server*. Paste:

- **Server URL:** the RunPod proxy URL above.
- **Bearer token:** the token from step 3.

Tap *Save*. The app probes `/loovie/capabilities`; you should see *Server reachable* (green).

> **Note:** *Server reachable* does not verify the bearer token. The probe endpoint is unauthenticated by design. A wrong token only shows up at first generation as *BYO server access denied*. If that happens, reopen the BYO sheet and paste the correct token.

Now go to image or video generation and pick *Your server (BYO)*. The image picker shows a **Free** badge.

## Step 8 — Stop the pod when you're done

**RunPod keeps billing as long as the pod is running.** From the RunPod console, click *Stop* (preserves the volume, fast restart later) or *Terminate* (deletes the pod and optionally the volume).

If you only use the server intermittently, stopping and restarting is cheap; resuming from a stopped pod takes about a minute and your model cache is intact.

## Cost notes

- RunPod publishes per-second pricing on the GPU listing pages. A 4090 is typically ~$0.50–$0.70/hour at the time of writing. Verify on RunPod's site; pricing changes.
- Volume storage is billed per-GB-month while the volume exists. An 80 GB volume runs roughly $4–$6/month at current RunPod rates.
- **Loovie does not see and does not bill for any of this.** All of this is between you and RunPod.

## Troubleshooting

- **HTTP 401 from the downloader** → revisit [`25-huggingface-and-gated-models.md`](25-huggingface-and-gated-models.md). The downloader prints which repo needs acceptance.
- **Pod refuses to start with "LOOVIE_API_TOKEN is not set"** → you forgot the secret. Edit the pod, add it, restart.
- **`/loovie/capabilities` missing `ss_videos`** → the video model download didn't finish. Check pod logs for errors during the LTX-2.3 downloads. Often a transient HuggingFace timeout — restart the pod and the downloader will resume.
- **`Your server (BYO)` not visible in the app** → you have not joined the beta yet (see [`10-create-a-loovie-account.md`](10-create-a-loovie-account.md)) or the server is unreachable.

For a fuller table, see [`70-troubleshooting.md`](70-troubleshooting.md).
