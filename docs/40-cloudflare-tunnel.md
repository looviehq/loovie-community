# Reach your home GPU with Cloudflare Tunnel

If your server runs on a machine at home and you want to use it from your phone on cellular, café Wi-Fi, or anywhere else, you need a tunnel. The cleanest free option is [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) (`cloudflared`).

You get:

- **A real HTTPS URL** (no plain HTTP, no router config, no hole punched through your firewall).
- **Zero open inbound ports** on your network, the tunnel is an outbound connection from `cloudflared` to Cloudflare.
- **Free for personal use.**

This page covers two flavours: a one-line **quick tunnel** (ephemeral URL, fastest to try) and a **named tunnel** (stable URL, recommended for daily use).

> **Security tie-in.** A tunnel gives you HTTPS, so the bearer token is not sent in clear over the network you happen to be on. **Still set `LOOVIE_API_TOKEN`**, the tunnel URL is reachable from the public internet by definition, so the token is your only access control. See [`50-security-and-tokens.md`](50-security-and-tokens.md).

## Install `cloudflared`

| Platform | Install |
|---|---|
| macOS (Apple Silicon or Intel) | `brew install cloudflared` |
| Linux (Debian/Ubuntu) | Follow [Cloudflare's apt instructions](https://pkg.cloudflare.com/index.html). Roughly: add the Cloudflare GPG key and apt repo, then `sudo apt install cloudflared`. |
| Linux (other) | Download the static binary from [github.com/cloudflare/cloudflared/releases](https://github.com/cloudflare/cloudflared/releases). |
| Windows | [MSI installer](https://github.com/cloudflare/cloudflared/releases). |

Verify:

```sh
cloudflared --version
```

## Option A, Quick tunnel (ephemeral URL)

Use when you just want to try the setup, demo to a friend, or do a one-off.

In one terminal (keep it open):

```sh
cloudflared tunnel --url http://localhost:8188
```

You will see something like:

```text
Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
https://flat-purple-mountain-9821.trycloudflare.com
```

Copy that URL. In the Loovie app, *Preferences → BYO server*, paste it plus your `LOOVIE_API_TOKEN`. Save.

> Quick-tunnel URLs are **ephemeral**, they change every time you restart `cloudflared`. Fine for trying things, awkward for daily use because you have to re-enter the URL in the app each time. For daily use, set up a named tunnel below.

## Option B, Named tunnel (stable URL on your own domain)

Use when you want a stable URL you can leave configured in the app forever.

You need a domain on Cloudflare (free DNS plan is fine). If you don't have one, register a cheap `.app` or `.dev` domain through any registrar and add it to Cloudflare.

### B.1, Authenticate `cloudflared`

```sh
cloudflared login
```

Opens a browser; pick the domain you want to use. This writes a cert to `~/.cloudflared/`.

### B.2, Create a tunnel

```sh
cloudflared tunnel create loovie-byo
```

Note the tunnel UUID it prints (and the path to the credentials JSON it writes). You'll reference these next.

### B.3, Point a DNS record at it

Pick a subdomain you'll use. For example, `byo.yourdomain.com`:

```sh
cloudflared tunnel route dns loovie-byo byo.yourdomain.com
```

### B.4, Write the tunnel config

Save as `~/.cloudflared/config.yml`:

```yaml
tunnel: <paste the UUID from B.2>
credentials-file: /Users/you/.cloudflared/<UUID>.json

ingress:
  - hostname: byo.yourdomain.com
    service: http://localhost:8188
  - service: http_status:404
```

### B.5, Run the tunnel

```sh
cloudflared tunnel run loovie-byo
```

In the Loovie app, paste `https://byo.yourdomain.com` plus your `LOOVIE_API_TOKEN`. This URL is permanent, leave it configured and it just works.

### B.6, Run as a service (so it survives reboots)

macOS / Linux:

```sh
sudo cloudflared service install
```

This registers a launchd / systemd service. After a reboot the tunnel comes back automatically.

Windows: `cloudflared service install` from an elevated prompt.

## Optional: lock it down further with Cloudflare Access

Out of the box, `byo.yourdomain.com` is reachable from the public internet. Anyone with the URL **and** the bearer token can use your server. The token is the access control.

If you want a second layer (e.g. to restrict the URL to your own Cloudflare-authenticated devices), put [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) in front. Important rule:

> **Scope Access policies to `/images/*` and `/videos/*` only.**
>
> `/loovie/health` and `/loovie/capabilities` are intentionally unauthenticated so the Loovie app can probe before you've configured a bearer token. Putting Access in front of those endpoints breaks the in-app *Server reachable* check.

A typical setup is one Access application matching `byo.yourdomain.com/images/*` and a second matching `byo.yourdomain.com/videos/*`, with the same policy on both. Leave `/loovie/*` un-protected.

## Troubleshooting

- **Tunnel says "connected" but the app shows *Could not reach your BYO server (52x)*** → ComfyUI is not actually running on `localhost:8188`. `curl -s http://localhost:8188/loovie/health` locally first.
- **The app shows *Server reachable* but generation fails with *BYO server access denied*** → the `LOOVIE_API_TOKEN` in your shell does not match what you pasted in the app. Re-export and restart ComfyUI, or update the app.
- **Cloudflare 1033 / "Argo Tunnel Error"** → the tunnel itself is down. Restart `cloudflared` (`brew services restart cloudflared` on macOS, `sudo systemctl restart cloudflared` on Linux).
