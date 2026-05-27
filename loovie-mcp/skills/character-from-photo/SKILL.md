---
name: character-from-photo
description: Use when the user wants to turn a reference image (a photo, an artwork, a screenshot) into a reusable Loovie character. Walks through upload, character creation, and (optionally) character sheet generation so the character can be used in subsequent video and image jobs.
---

# Character from a photo

You are turning a reference image into a Loovie character. A character sheet (multi-pose reference) is **optional** but recommended — when present, downstream first-frame and video generation uses it for stronger consistency. When absent, downstream generation falls back to the original variation image. Never block on the sheet.

## Hard rules

1. Two-step approval applies to every spend: `estimate_*` → user approves → `execute_*`.
2. Quote credits, never dollars. Never name internal models.
3. **Uploads go direct to R2.** Bytes never transit the MCP server. If the user gave you a remote URL, you download it locally first, then upload — do not ask the server to fetch on your behalf.
4. **Downsize before you upload.** Reference images don't need to be full resolution; Loovie's pipeline resizes to ~1024px long-edge internally. A 2 MB phone photo wastes bandwidth, can blow past the inline-base64 preview cap, and in chat clients can exhaust the conversation context window. Always preprocess the image first per the "Downsize first" step below.

## Playbook

### 1. Get the image into Loovie

All paths end with a `storageKey` you'll pass into the next step.

#### Downsize first (mandatory for every path)

Before any upload, resize the image to **1024px max on the long edge, JPEG quality 80**. A typical 2 MB phone photo becomes ~150 KB this way, which keeps the wire payload small AND lets `get_asset_preview` render the result inline later (the inline-base64 cap is 800 KiB; full-res photos exceed it).

Pick whichever toolchain your runtime has:

- **Python (Pillow / PIL)**:
  ```python
  from PIL import Image
  img = Image.open('/path/to/original')
  img.thumbnail((1024, 1024))  # preserves aspect ratio
  img.convert('RGB').save('/tmp/loovie-ref.jpg', 'JPEG', quality=80)
  ```
- **Bash (ImageMagick)**: `magick /path/to/original -resize 1024x1024\> -quality 80 /tmp/loovie-ref.jpg`
- **Node (sharp)**: `sharp(input).resize({ width: 1024, height: 1024, fit: 'inside' }).jpeg({ quality: 80 }).toFile('/tmp/loovie-ref.jpg')`

Use the **resized file** (`/tmp/loovie-ref.jpg`) as the input to whichever upload path you take below. If the user's reference is already < 500 KB, skip the resize — it adds no value.

Upload paths:

- **Local file on disk + you have shell access** (Claude Code, Cursor with shell):
  1. `request_image_upload_url({ filename, contentType })` — returns `{ uploadUrl, finalizePath, instructions.curl }`. `uploadUrl` is a presigned R2 PUT URL.
  2. Run the `instructions.curl` command via Bash. The image PUTs straight to R2.
  3. `finalize_image_upload({ ... })` — returns `{ storageKey, imageUrl }`.

- **Remote URL the user gave you** (e.g. an image link they pasted):
  1. **Download it locally first.** `curl -L -o /tmp/loovie-ref.<ext> '<url>'` via Bash.
  2. Then follow the local-file path above — `request_image_upload_url` → curl PUT → `finalize_image_upload`.
  3. Do NOT call `upload_image_for_reference({ url })` to make the server fetch on your behalf. The direct-to-R2 path is the only flow this skill uses when shell is available.

- **Image already exists in the library**: `loovie://library/...` or `list_characters` to find it; reuse its `storageKey`.

- **No shell access at all** (rare): only then, use `upload_image_for_reference({ url })` or `upload_image_for_reference({ dataBase64, mimeType, filename })` as a fallback. Both are slower and consume MCP transport bandwidth. The base64 path is hard-capped at ~300 KB encoded by most chat clients' context windows; the downsize step above is what makes that fit. If the downsized base64 still exceeds ~300 KB, stop and ask the user to share a smaller image or a hosted URL instead — do NOT try to send raw multi-megabyte base64 (it'll exhaust the conversation context).

- **Chat-attached image** (user dropped an image into the Claude.ai / Claude Desktop / Cursor chat):
  1. The image lives on the agent's filesystem temporarily. Read its bytes via whatever code-execution tool your runtime exposes (e.g. Test Integration / Code Interpreter / Bash).
  2. Apply the "Downsize first" step above. **This is the path that benefits most from downsizing** — a typical chat-dropped photo is 2-5 MB, which would otherwise exhaust the conversation context on base64.
  3. If your runtime can curl-PUT to arbitrary HTTPS hosts, use the presigned-URL path (R2 SigV4 hosts must be allowlisted; some sandboxes block them). If R2 is blocked, fall back to `upload_image_for_reference({ dataBase64, mimeType: 'image/jpeg', filename })` with the downsized bytes.

### 2. Create the character shell

- Ask for a name and a one-line description if not given.
- `create_character` with the name, description, and the uploaded image as the initial `original` variation.

### 3. (Optional) Generate a character sheet

- Skip this step entirely if the user doesn't ask for it, or if the credit cost isn't justified for their use case. Downstream tools work without it.
- If you do generate one:
  - `estimate_generate_character_sheet` with the `characterId`. Show the credit cost.
  - After approval: `execute_generate_character_sheet` → poll `get_job` until terminal.
  - The result is a draft variation. Call `confirm_character_variation` to persist it as the canonical character sheet, or `discard_character_variation` if the user doesn't like it.
  - `get_asset_preview` on the sheet URL so the user sees it inline.

### 4. (Optional) More variations

- If the user wants extra looks (different outfit, different age, etc.): `estimate_add_character_variation` → approve → `execute_add_character_variation` → `confirm_character_variation`.
- If a character sheet exists, prefer it as the reference for clothes/hair consistency; otherwise reference the original variation image.

## When something fails

- Upload failures: retry once. If the second attempt fails, surface the error and stop.
- Character sheet generation that produces a poor result: do NOT re-run it silently. Show the user the preview and ask whether to retry, accept, or skip the sheet entirely.
