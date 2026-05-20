# Troubleshooting

When BYO fails, it is almost always your server, your network, or your hardware. The Loovie team cannot fix your box; the docs are your primary support, plus a community Discord that opens with `v0.1.0-beta` (invite in [README → Community](../README.md#community) once live). This page is the symptom-to-fix table.

## Setting up

### "Could not reach your BYO server (520..527 / 530)"

Cloudflare returned a 5xx-class error because the tunnel or the origin is down.

- **Tunnel down.** `cloudflared tunnel info loovie-byo` (named tunnel) or restart `cloudflared` (`brew services restart cloudflared` / `sudo systemctl restart cloudflared`).
- **Origin down.** `curl -s http://localhost:8188/loovie/health` on the machine the server runs on. If that fails, ComfyUI isn't up.

### "Server responded 401 at /loovie/capabilities"

You put authentication in front of the probe path. Don't do that, `/loovie/health` and `/loovie/capabilities` are intentionally public so the app can find the server before the token is configured.

- If you're using Cloudflare Access, scope it to `/images/*` and `/videos/*` only. See [`40-cloudflare-tunnel.md`](40-cloudflare-tunnel.md).

### "Not a Loovie-compatible server" / "Server returned an unknown schema"

The server is reachable, but `/loovie/capabilities` doesn't return a valid manifest.

- **`comfyui-loovie` is too old.** Pull latest and restart ComfyUI.
- **`comfyui-loovie` isn't installed.** Confirm `ComfyUI/custom_nodes/loovie` exists and ComfyUI loaded it (check ComfyUI startup logs for `Loovie:` lines).

### "Server is reachable but has no Loovie image or video workflows installed"

The capabilities manifest is missing the `images` and/or `ss_videos` section. The server only advertises what it can actually run.

- **`comfyui-loovie/config.yaml` does not list any image or video workflows.** Add the ones you want.
- **Models haven't downloaded yet.** On RunPod, watch the pod logs for the downloader. First boot can take 15–40 minutes.

### "Could not reach server: \<some error\>"

Generic network error. Check:

- The URL is correct (paste from the RunPod console, don't retype).
- The server is actually running (curl from another machine).
- Your phone has network connectivity.
- If on Wi-Fi: the phone and the server are on the same network (for LAN setups).

## Generating

### "BYO server access denied"

The server returned `401 Unauthorized`. Your bearer token in the app doesn't match the `LOOVIE_API_TOKEN` configured on the server.

- Reopen *Preferences → BYO server* and paste the correct token.
- If you don't remember the token: regenerate one with `scripts/new-token.sh`, set it on the server, paste in the app.
- The probe endpoint is unauthenticated, so a green "Server reachable" doesn't catch this.

### "Your server reported a problem: \<failCode\>"

Your server failed the generation. This is on your server, not Loovie. The most common failures:

| `failCode` | Cause | Fix |
|---|---|---|
| `EXECUTION_ERROR` | A node in the workflow blew up. | Check ComfyUI logs. Often a missing model file or an out-of-VRAM error. |
| `OUTPUT_MISSING` | Workflow ran but produced no output. | Workflow JSON is broken. Re-export from ComfyUI editor. |
| `HISTORY_MISSING` | The task disappeared from ComfyUI's history. | ComfyUI restarted mid-run; retry. |
| `BYO_INVALID_RESULT` | Server returned a file that isn't a valid image/video. | Workflow output bytes don't match the declared MIME. Verify the final save node and the format. |
| `BYO_TIMEOUT` | Generation exceeded 30 minutes. | Cold model load, undersized GPU, very long video, pro tier on a tight VRAM budget. Use a bigger GPU, a shorter duration, or the `fast` variant. Pre-warm by running once before the real generation. |

### Timed out after 30 minutes

Same as `BYO_TIMEOUT` above. The Loovie API times out after 30 minutes of no terminal state. Most generations finish in well under that; long videos (8 second pro variants, large resolutions) and cold model loads on undersized GPUs are the usual culprits when you hit the cap.

- For LTX-2.3 pro on a 24 GB GPU you may genuinely run out of time on first cold start. Switch to `fast` variant, or use a 48 GB GPU, or pre-warm.

### macOS / Apple Silicon is very slow or OOMs

Expected for the reference workflows. LTX-2.3 and FLUX.2 are heavy and the Metal backend isn't competitive with CUDA for these workloads. Either swap in a lighter image / video model that runs comfortably on your hardware (the contract is model-agnostic; see [`80-adding-a-workflow.md`](80-adding-a-workflow.md)) or use a rented cloud GPU like [RunPod](30-runpod.md).

## In the app

### "Your server (BYO)" doesn't appear in the picker

In order of likelihood:

1. **Not in the beta.** *Preferences → Local Compute (BYO), join the beta* → tap → force-quit → reopen.
2. **The server didn't advertise that section.** If `images` is absent from `/loovie/capabilities`, the image BYO tier is hidden. Same for `ss_videos`. Check the capabilities response.
3. **Server unreachable.** Reopen the BYO sheet; check the green / red status.

### "BYO is paused right now, try again later"

Loovie set a server-side kill switch (`BYO_KILL_SWITCH=true`). We do this only in genuine emergencies (e.g. an in-flight protocol bug needs a temporary stop). It is announced on `#announcements` on the Discord with an ETA.

### The generate screen shows a banner: "Your BYO server isn't being used right now. We've switched to <tier>, which will charge credits."

The app couldn't route the request to your BYO server (flag off, no WS session, server unreachable, or the kill switch is on) and fell back to your previous non-BYO quality tier, **which costs credits**.

- Tap the banner to open the BYO sheet and fix the server.
- The banner stays until you dismiss it or the next successful BYO save.

### The generate screen shows a banner: "BYO transport is not fully secure: <http|self-signed cert>. Tap to review."

You ticked one of the two consent checkboxes when saving your server (plain HTTP or untrusted TLS cert). The banner reminds you it's still active.

- Tap the banner → fix the server (use HTTPS, or fix the cert) → the banner clears on the next successful save.

## Reporting bugs vs. asking for help

- **Reproducible bug in the Loovie app?** [Open an issue](https://github.com/looviehq/loovie-community/issues) using the **Bug report** template.
- **Configuration / "how do I" question?** Discord `#byo-help`. We close pure setup questions on the issue tracker because Discord handles them faster.
- **Security vulnerability?** [Private vulnerability reporting](https://github.com/looviehq/loovie-community/security/advisories/new), not a public issue. See [`SECURITY.md`](../SECURITY.md).
