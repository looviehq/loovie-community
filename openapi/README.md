# OpenAPI: the BYO server contract

This directory contains **one normative specification**:

- [`loovie-server.openapi.yaml`](./loovie-server.openapi.yaml), the HTTP API a BYO server must expose to be drivable by the Loovie mobile app.

It is the single source of truth. The reference implementations in [`comfyui-loovie/`](../comfyui-loovie/) and [`examples/minimal-server/`](../examples/minimal-server/) conform to it; anything you write that conforms is equally valid.

## Quick start

The two unauthenticated probes are the fastest way to confirm a server is alive and Loovie-compatible:

```sh
# Liveness/readiness. Returns code 200 + status "ok" once ready.
curl -s http://localhost:8188/loovie/health | jq .

# What this server can do. Drives the BYO picker in the Loovie app.
curl -s http://localhost:8188/loovie/capabilities | jq .
```

A `/loovie/capabilities` response with an `images` section advertises that the server implements `POST /images/create` + `GET /images/status`. A response with `ss_videos` advertises the matching `/videos/*` pair. Servers without a section omit those endpoints entirely.

Authenticated requests use a static bearer token chosen by the operator:

```sh
curl -X POST http://localhost:8188/images/create \
  -H "Authorization: Bearer $LOOVIE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a red bicycle in front of a Parisian café","mode":"t2i"}'
```

Returns `{"code":200,"data":{"taskId":"task_loovie_xxxx"}}`. Poll `/images/status?taskId=…` for progress; on success the response carries `resultJson` (a JSON-encoded string of `{"resultUrls":["<url>"]}`).

## Auth, in two sentences

`Authorization: Bearer <LOOVIE_API_TOKEN>` is required for every remote caller. Localhost (`127.0.0.1`, `::1`) may bypass; if no token is configured the server MUST refuse remote requests (fail closed).

## Tooling

- Lint locally: `npx -y @redocly/cli@latest lint loovie-server.openapi.yaml --extends=recommended-strict`
- Bundle: `npx -y @redocly/cli@latest bundle loovie-server.openapi.yaml -o bundled.yaml`
- Render static docs locally: `npx -y @redocly/cli@latest preview-docs loovie-server.openapi.yaml`
- Runtime contract test (against a running server): `pipx run schemathesis run loovie-server.openapi.yaml --base-url http://localhost:8188`

CI runs the lint on every PR that touches `openapi/**` (see [`.github/workflows/openapi-lint.yml`](../.github/workflows/openapi-lint.yml)) and publishes the rendered spec to GitHub Pages on every push to `main`.

## Versioning

> ⚠️ **Beta API stability, pin your version.** While we are on the `0.x` line, **breaking changes may land in minor bumps.** That includes renaming or removing endpoints, narrowing or replacing enum values, changing field requiredness, and reshaping responses. We document every break in [CHANGELOG.md](../CHANGELOG.md) and reflect it in `info.version` on the spec (and `schemaVersion` on the capabilities manifest when the shape changes). **If you depend on the contract, pin to a specific tag or commit SHA** rather than tracking `main`. Strict semver kicks in at `1.0.0`.

`info.version` follows semver and is independent of any individual implementation's version. The capabilities manifest carries its own `schemaVersion` (currently `1`); it bumps only when the manifest SHAPE changes, adding a new mode to an enum, adding an optional field with a default, removing a field, or changing requiredness.

## Spec extensions

The spec uses two `x-loovie-*` extensions:

- `x-loovie-conditional-endpoints` (top level): documents which path groups are required only when the corresponding `/loovie/capabilities` section is advertised.

If you implement the contract for your own stack, you do not need to honour `x-*` extensions, they are informational.
