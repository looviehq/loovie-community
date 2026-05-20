# Security and tokens

This is the page to read before you point any port at the internet. It is short on purpose.

## The single most important fact

Your BYO server URL and bearer token live in the **Loovie app on your device only**. The app needs them to call your server, which is why they exist there. They are **never sent to Loovie's backend servers and are not accessible to Loovie staff.** Loovie's backend does not call your server; only the Loovie mobile app does.

If you want to verify, run any HTTP proxy on your phone (Charles, Proxyman, etc.) on the Loovie traffic. Every request to `api.loovie.app` carries job metadata only — no URL, no token, no media bytes. The calls to your BYO server URL go directly from the device to your server.

## What we store about a BYO generation

The same things Loovie stores for any generation: prompt, parameters, the final media file, status, timing. **Not** your URL, **not** your token, **not** intermediate frames, **not** the traffic between the app and your server. Full breakdown in [`15-terms-and-privacy.md`](15-terms-and-privacy.md).

## Tokens

- **Generate one with [`scripts/new-token.sh`](../scripts/new-token.sh).** 32 random bytes, URL-safe. 256 bits of entropy is more than enough for a static bearer token.
- **Treat it like a password.** Don't commit it. Don't paste it in screenshots. Don't share it.
- **Rotate it** when you change machines, share access, or suspect compromise. Change the env in your server and update the app.
- **Don't reuse it** across servers. Each server gets its own token.

The server is configured to **fail closed** when `LOOVIE_API_TOKEN` is unset and the bind host is not loopback. Concretely: if you launch the container with `--network host` or bind `0.0.0.0` and forget the token, the entrypoint refuses to start. There is no fallback to "no auth needed."

## Transport: HTTPS or HTTP

### HTTPS (recommended)

- **RunPod proxy URLs (`https://<pod-id>-8188.proxy.runpod.net`)** are HTTPS by default.
- **Cloudflare Tunnel** (see [`40-cloudflare-tunnel.md`](40-cloudflare-tunnel.md)) gives you HTTPS for free.
- **Your own cert** (Let's Encrypt etc.) on your own domain works fine.

The Loovie app verifies the TLS certificate against the system trust store. If the certificate is invalid (self-signed, expired, hostname mismatch), the app shows a **red checkbox you must tick** to override: *"This server's HTTPS certificate is not trusted. I accept the risk that the connection may be intercepted."* The override is per-server and shows a persistent banner on the generate screen while it is active. Only enable it for a server you can verify some other way (you set up the self-signed cert yourself, you trust your network at every hop, etc.).

### HTTP (only on networks you trust)

If you save an `http://` URL in the app, you have to tick a **yellow checkbox**: *"I trust this network (for example my own home Wi-Fi). I accept the risk that my token may be visible on this network."* Save is disabled until you tick it.

**Only use HTTP on:**

- Your own home Wi-Fi.
- A wired LAN you own.
- Loopback / `localhost`.

**Never use HTTP on:**

- Café, restaurant, or hotel Wi-Fi.
- Conference or co-working Wi-Fi.
- A corporate network you don't own.
- Public Wi-Fi of any kind.

The reason is simple: HTTP is unencrypted, so anyone on the same network with `tcpdump` and a few minutes can see your bearer token. Tunnel it (see option A in [`40-cloudflare-tunnel.md`](40-cloudflare-tunnel.md) — a 30-second `cloudflared tunnel --url http://localhost:8188` gives you HTTPS) instead.

## What Loovie does on its side

When a BYO generation completes, the device uploads the result to a Cloudflare R2 temp key under your user prefix and POSTs a complete-callback to Loovie's API. Those callbacks are authenticated by:

1. **Supabase JWT** on every `/v1/byo/*` route. Anonymous requests are refused.
2. **Job ownership** — the row's `userId` must match the JWT user, or 403.
3. **Storage-key ownership** — the R2 key in the callback must live under your user prefix, or 403.
4. **Durable Object phase gating** — the DO that watches the job re-validates the JWT, the user ID, and the current job phase before applying the callback. Mismatch or late callback is dropped.

There is **no HMAC or request signing** in beta. The worst a holder of your own JWT could do is post a crafted complete-callback for one of their own jobs — which would still be rejected if the file doesn't pass the magic-byte / decode / size / MIME validation (`BYO_INVALID_RESULT`).

## Result-file validation

Before the device uploads a generation result to R2, it checks:

- **Magic bytes** match the declared MIME (PNG / JPEG / WebP for images, MP4 / WebM for video).
- **Decode probe** — the image can be thumbnailed; the video has a parseable container.
- **Size cap** — images ≤ 50 MB, video ≤ 500 MB.
- **MIME allowlist** — only the formats above.

The Loovie API re-checks the magic bytes + size + MIME on the R2 object at the complete-callback boundary (cheap, no decode). Anything failing is rejected with `BYO_INVALID_RESULT`, the job ends in `Failed`, and the user sees *"Your server returned a file that isn't a valid image / video. Check your workflow output."*

**We do not run anti-malware scanning on result files during beta.** The beta threat model is "the operator pwns themselves and their own user, not the Loovie cloud." We will graduate to server-side AV scanning as part of the paid BYO Pass tier. Document this as a known limit, not a surprise.

## Honest residual risks

- **No request signing in beta.** Plan to revisit once the paid tier raises stakes.
- **`i2i` / `i2v` modes fetch URLs your app provides.** The Loovie app authors those URLs, but the server still does the fetch — so don't run your server as root, and don't expose port 8188 on a corporate network without an auth layer in front (Cloudflare Access scoped to `/images/*` + `/videos/*`, see [`40-cloudflare-tunnel.md`](40-cloudflare-tunnel.md)).
- **Plain HTTP on an untrusted network exposes the bearer token.** The yellow checkbox is a real risk, not a formality. Don't tick it on café Wi-Fi.

## Reporting issues

Vulnerabilities go to [`SECURITY.md`](../SECURITY.md) via [GitHub Private Vulnerability Reporting](https://github.com/looviehq/loovie-community/security/advisories/new) (preferred) or `security@loovie.app`. **Do not** post them as public issues.
