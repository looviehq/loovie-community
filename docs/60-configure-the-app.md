# Configure the Loovie app for your BYO server

This is the step-by-step for the *Preferences → BYO server* sheet. It assumes your server is already running and you have a URL plus a bearer token.

## Open the BYO sheet

1. Open the Loovie iOS app.
2. Tap your avatar or the menu → **Preferences**.
3. Scroll to **Connected apps & MCP**.
4. Tap **BYO server**.

If you don't see the **Connected apps & MCP** section, you have not joined the beta yet. Scroll up in Preferences for the **Local Compute (BYO), join the beta** row and tap it once. Force-quit and reopen the app (the feature flag refreshes on app start).

## The header caption

The sheet header carries a persistent caption: *"The Loovie app on your device stores your URL and token (it has to, to talk to your server). They are never sent to Loovie's backend servers and are not accessible to Loovie staff."* Read it once. The privacy guarantee is real and the wording is precise on purpose.

## Fields

| Field | What to paste |
|---|---|
| **Server URL** | The URL of your server: a RunPod proxy URL (`https://<pod-id>-8188.proxy.runpod.net`), a Cloudflare Tunnel hostname (`https://byo.yourdomain.com`), or a LAN address (`http://192.168.x.y:8188`) for same-Wi-Fi use. |
| **Bearer token** | Your `LOOVIE_API_TOKEN`. Generate with `scripts/new-token.sh` if you haven't. |

## Transport consent

The app reacts to your URL automatically.

### If the URL starts with `http://`

A yellow caution appears under the URL field: *"Plain HTTP is unencrypted. Your token may be visible to others on this network."*

A **required checkbox** appears above the Save button: *"I trust this network (for example my own home Wi-Fi). I accept the risk that my token may be visible on this network."*

**Save is disabled until you tick the checkbox.** Tick it only if you are on a network you trust at every hop, your own home Wi-Fi, a wired LAN you own. Don't tick it on café, hotel, conference, corporate, or any other network. See [`50-security-and-tokens.md`](50-security-and-tokens.md).

If you later change the URL to `https://`, the checkbox is cleared automatically.

### If the URL starts with `https://` and the cert is not trusted

A red error appears: *"This server's HTTPS certificate is not trusted (self-signed, expired, or hostname mismatch). The connection may be intercepted."*

A **required checkbox** appears: *"I have verified this server and accept the risk that the HTTPS connection may not be secure."*

Save is disabled until you tick the checkbox. Tick it only if you set up the self-signed cert yourself or otherwise have a reason to trust the connection. The override is per-server, pointing at a different URL re-evaluates.

While either override is active, the generate screen shows a persistent caution banner: *"BYO transport is not fully secure: <http|self-signed cert>. Tap to review."* Tapping deep-links back to this sheet.

## Save

Tap **Save**. The app probes `GET <url>/loovie/capabilities`. Expected results:

| State | What it means |
|---|---|
| **Server reachable** (green) | The server responded with a valid capabilities manifest. You are ready to generate. |
| **Could not reach server: \<reason\>** | Network error, tunnel down, wrong URL, server not running. See [`70-troubleshooting.md`](70-troubleshooting.md). |
| **not a Loovie-compatible server** | The server responded but the body isn't a valid capabilities manifest. Check the `comfyui-loovie` install and that `/loovie/capabilities` returns what `90-the-contract.md` describes. |
| **Server is reachable but has no Loovie image or video workflows** | `comfyui-loovie/config.yaml` doesn't list any image or video workflows, or the model downloader hasn't finished. Check pod logs and `docs/30-runpod.md`. |

> **Important.** *Server reachable* does **not** verify your bearer token, the `/loovie/capabilities` probe is unauthenticated by design. A wrong token only shows up at first generation as **BYO server access denied**. If you see that, come back to this sheet and fix the token.

## Generate

Once saved, go to image or video generation, open the quality picker, and tap **Your server (BYO)**:

- The image picker shows a **Free** badge.
- The video picker shows the same option without a credit badge (BYO video is always free at the Loovie layer).

## If `Your server (BYO)` is missing in the picker

Three possibilities, in order of likelihood:

1. **You're not in the beta.** Go back to Preferences and tap *Local Compute (BYO), join the beta*. Restart the app.
2. **The server didn't advertise that section in `/loovie/capabilities`.** If your server has no image workflows installed, it omits the `images` section and the app hides the image BYO tier. Same for video. Check pod logs.
3. **The server is unreachable.** Reopen the BYO sheet, if it shows red, fix the URL.

## Clear saved server

The **Clear saved server** button removes:

- The URL.
- The bearer token.
- The HTTP risk-acceptance flag (if you ticked it).
- The TLS cert override (if you ticked it).

Once cleared, nothing about your BYO server exists on the device. **There is no copy in Loovie's cloud to delete**, see [`15-terms-and-privacy.md`](15-terms-and-privacy.md).
