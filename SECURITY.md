# Security Policy

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Preferred: [report a vulnerability privately](https://github.com/looviehq/loovie-community/security/advisories/new) using GitHub's Private Vulnerability Reporting. We monitor this channel.

Backup: email `security@loovie.app`. PGP key fingerprint will be published here once available.

## Supported versions

This project is in public beta. Only the latest minor of the `0.x` line is supported. We will publish security fixes against that line and tag releases accordingly. There is no extended support for older minors during beta.

## Response timeline

This is a free, community-supported beta. We aim to:

- Acknowledge your report within **5 business days**.
- Provide a remediation timeline within **14 days** of acknowledgement.

We will be transparent if we cannot meet these targets. Critical vulnerabilities affecting the Loovie cloud service or our published container images will be prioritised over reference-implementation-only issues.

## Scope

**In scope:**

- The OpenAPI contract (`openapi/loovie-server.openapi.yaml`) — design flaws that allow privilege escalation, auth bypass, or unintended data exposure.
- The reference ComfyUI implementation (`comfyui-loovie/`) — auth bypass, RCE, SSRF, path traversal, denial of service, dependency vulnerabilities not yet flagged by Dependabot.
- The minimal FastAPI example (`examples/minimal-server/`) — same as above.
- The Docker image and RunPod template (`docker/`) — base-image vulnerabilities not flagged by Trivy, insecure defaults.

**Out of scope:**

- Issues that require the operator to misconfigure their own server (e.g. exposing port 8188 publicly with no `LOOVIE_API_TOKEN` set — the server fails closed by default, so disabling that is a configuration choice, not a vulnerability).
- Denial of service achievable only by submitting unreasonable prompt sizes, abusing your own GPU, or running models you installed yourself.
- Vulnerabilities in models you load (FLUX.2 Klein, LTX-2.3, etc.) — those are governed by their own upstream projects.
- Loovie's mobile app or commercial backend — report those to `security@loovie.app` separately; that is a different codebase.

## Threat model (operators)

If you run a BYO server:

- **Always set `LOOVIE_API_TOKEN`** for any deployment reachable off the loopback. The server is configured to refuse remote requests when no token is set (fail closed).
- The server's attack surface, given a valid token, is: prompts and parameters in, media files out. The `i2i` / `i2v` modes ask the server to fetch URLs you provide; the Loovie app authors those URLs, but operators should not run the server as root, and should not expose port 8188 on shared corporate networks without an authentication layer in front (e.g. Cloudflare Access scoped to `/images/*` and `/videos/*`).
- Use HTTPS for anything not on loopback or a network you fully control. The Loovie app requires explicit user consent on plain HTTP or untrusted certificates.

## Threat model (Loovie side)

Your BYO server URL and bearer token are held by the Loovie app on your device, because the app is what calls your server. They are **never sent to Loovie's backend servers and are not accessible to Loovie staff**. Callbacks from the device to Loovie's API are authenticated and bound to the originating user, and they carry no information about your server URL or token. Result files uploaded to Loovie are validated (magic bytes, MIME, size) before they are finalised; anything failing is rejected with `BYO_INVALID_RESULT`.

## Result-file scanning

For the public beta, we validate result files via magic-byte sniff, MIME allowlist, size cap, and decode probe. We do **not** run anti-malware scanning on uploaded result files during beta — the threat model is that an operator's misbehaving server attacks itself or its own user, not the Loovie cloud. We will graduate to server-side AV scanning as part of the post-beta paid tier; this will be documented when it ships.

## Coordinated disclosure

We follow coordinated disclosure. We will work with you on a disclosure timeline and credit you in the changelog (with your consent) once a fix is released. Public disclosure before a fix is not in anyone's interest, including yours.

## Out-of-band channels

For unusual situations (active exploitation, contact failure), reach out via the Loovie Discord to any maintainer privately. Do not post the vulnerability publicly.
