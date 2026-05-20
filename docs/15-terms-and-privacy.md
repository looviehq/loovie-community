# Terms and privacy in plain words

This is a friendly summary, not a contract. The binding documents live at [loovie.app/terms](https://loovie.app/terms) and [loovie.app/privacy](https://loovie.app/privacy). Where this page and the website disagree, the website wins. This page covers the parts unique to BYO.

## Loovie is a UI provider for BYO

When you use BYO, the Loovie iOS app sends prompts to **your** server and stores the resulting media exactly the way it stores any other Loovie generation. The Loovie backend does not talk to your server; the app does.

## Where your server URL and bearer token live

**In the Loovie app on your device only**, because the app needs them to call your server.

They are:

- **Never sent to Loovie's backend servers.** No request from the device to `api.loovie.app` carries them.
- **Not accessible to Loovie staff.** We cannot read or recover them. We cannot reset them for you.
- **Gone when you uninstall the app or tap *Clear saved server* in Preferences.** There is no copy in our cloud to delete.

If you want to verify this, run a network proxy (Charles, Proxyman, or built-in macOS Wi-Fi sniffer) on your Loovie traffic. You will see calls to `api.loovie.app` carrying job metadata only, and direct calls from the app to whatever server URL you configured.

## What Loovie *does* store about a BYO generation

The same things we store for any Loovie generation, no more:

| What | Why |
|---|---|
| **Prompt text** (and negative prompt, if any) | So you can see, edit and reuse it in your library. |
| **Generation parameters** | `mode`, `variant`, `aspect_ratio`, `resolution`, `duration`, `seed`, `withAudio`, IDs of reference images you used. Required to reproduce and to display correctly. |
| **The final image or video file** | Stored on Loovie's servers, linked to your account. This is what shows up in your Loovie library. |
| **Status, timing, error codes** | Operational. Lets us show progress and surface failures cleanly. |
| **Analytics events** (PostHog) | App usage, BYO outcomes. **No prompts, no media.** Used to improve the app. |

## What we explicitly do **not** store

- **Your BYO server URL.** Never sent to us.
- **Your bearer token.** Never sent to us.
- **Intermediate frames or any traffic between the Loovie app and your server.** That traffic is direct, device-to-server.
- The body of a BYO server failure response beyond a sanitised `failCode` + `failMsg` we need for operational use.

## You are responsible for what you generate

Loovie has no technical ability to limit, constrain, moderate, or supervise what runs on hardware we don't control. Anything your BYO server generates is your responsibility. Comply with applicable law and with the licences of every model you load (see [`MODELS.md`](MODELS.md)).

## Costs

- **Loovie:** nothing for BYO generations during beta. After beta, a flat-fee "BYO Pass" subscription will gate access to the BYO interface in the app. Per-generation costs remain 0 forever.
- **Your compute provider** (e.g. RunPod): bills you separately for GPU time and storage. Loovie is not a party to that.

## Support boundary

- **Loovie app misbehaves?** That is on us. [Open an issue](https://github.com/looviehq/loovie-community/issues) or ping `#bugs` on the Discord.
- **Your BYO server, ComfyUI install, GPU driver, model download, network, or modified workflow?** Community support on Discord (`#byo-help`). Loovie staff cannot help with these.

## Reading the actual legal documents

- [loovie.app/terms](https://loovie.app/terms) — terms of use, including a BYO section that mirrors the points above with the legal phrasing.
- [loovie.app/privacy](https://loovie.app/privacy) — privacy policy, with a BYO section enumerating exactly what is stored and what is not.
- [`SECURITY.md`](../SECURITY.md) — vulnerability reporting and the threat model.
- [`LEGAL.md`](../LEGAL.md) — repo-level plain-language summary (mostly the same content as this file, scoped tighter to liability and the support boundary).
