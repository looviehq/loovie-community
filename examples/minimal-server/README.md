# `examples/minimal-server` — FastAPI reference

A small (`~330 LoC`) FastAPI app that implements every endpoint of the [Loovie BYO HTTP contract](../../openapi/loovie-server.openapi.yaml) with placeholder outputs.

**It is not a generation server.** `POST /images/create` and `POST /videos/create` simulate progress and resolve to a 1×1 transparent PNG / minimal MP4 `data:` URL. The point is to let you validate the contract — connectivity, auth, capabilities, polling, timing — before you provision a GPU or wire up a real model pipeline.

## Run it

```sh
pip install -e '.[dev]'
export LOOVIE_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
uvicorn app:app --host 0.0.0.0 --port 8188
```

Then from another shell:

```sh
curl -s localhost:8188/loovie/health | python -m json.tool
curl -s localhost:8188/loovie/capabilities | python -m json.tool

curl -X POST localhost:8188/images/create \
  -H "Authorization: Bearer $LOOVIE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"hello","mode":"t2i"}'
```

The response gives you a `taskId`; poll `GET /images/status?taskId=...` for state transitions. You'll see `pending → processing → success` within ~2 seconds.

## Point the Loovie app at it (smoke test)

You can connect the Loovie iOS app to this server (over a Cloudflare quick tunnel) to confirm the BYO picker shows up, capabilities resolve, and generation completes — useful before committing GPU spend on a real implementation. The actual generated media will be the bundled placeholders, so this is purely a connectivity / UX smoke test.

## Tests

```sh
pip install -e '.[dev]'
pytest
```

The tests cover:

- `/loovie/health` returns `ready`.
- `/loovie/capabilities` returns `schemaVersion: 1` with image + video sections that match the OpenAPI enums.
- Remote requests with no `LOOVIE_API_TOKEN` configured are refused with `401` (fail-closed per `[D11]`).
- Authenticated `POST /images/create` and `POST /videos/create` advance through the lifecycle and resolve to placeholder media whose magic bytes are valid PNG / MP4.
- `end_frame_url` requires `start_frame_url` (per the contract).
- The 3000-character prompt limit is enforced.
- Both upload paths (multipart and JSON) work.

## Contract conformance

CI runs [`schemathesis`](https://schemathesis.readthedocs.io/) against this app on every PR that touches `openapi/**` or `examples/**`. Locally:

```sh
# in one terminal
uvicorn app:app --host 0.0.0.0 --port 8188

# in another
schemathesis run --checks all \
  --base-url http://localhost:8188 \
  ../../openapi/loovie-server.openapi.yaml
```

The placeholder outputs aren't intended to satisfy semantic checks beyond shape conformance — for that you need a real implementation like [`comfyui-loovie/`](../../comfyui-loovie/).

## Implementation notes for new server authors

The whole server is ~330 lines in `app.py`. Worth reading top to bottom; it shows the minimum a Loovie BYO server has to do:

- Two unauthenticated probes (`/loovie/health`, `/loovie/capabilities`) and five authenticated routes.
- A `_check_auth`-style dependency that bypasses on loopback and otherwise demands the configured `LOOVIE_API_TOKEN`. If no token is set and the caller is remote, it returns `401`.
- A task store keyed by an opaque `task_loovie_<12hex>` id with a four-state machine: `pending → processing → success | failed`.
- A `resultJson` field on success containing a JSON-encoded string of `{resultUrls: [...]}` (yes, encoded as a string, per the contract).
- A bearer-token-protected upload endpoint accepting both `multipart/form-data` and `application/json` with `data_base64`.

Roll your own in any stack — Go, Rust, TypeScript, Node, anything that speaks HTTP — and as long as your responses match the OpenAPI, the Loovie app will drive it. The reference ComfyUI implementation in [`comfyui-loovie/`](../../comfyui-loovie/) follows the same contract but is wired to real models.

## Not published

This package is intentionally not published anywhere (no PyPI, no npm). It's a reference you copy-paste-and-adapt.
