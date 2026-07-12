---
name: creating-a-character-from-photo
description: Use when the user wants to turn a reference image (a photo, an artwork, a screenshot) into a reusable Loovie character. Walks through upload, character creation, and (optionally) character sheet generation so the character can be used in subsequent video and image jobs.
---

# Creating a character from a photo

You are turning a reference image into a Loovie character. All tools and `loovie://` resources named below live on the `loovie` MCP server; if your client namespaces tools by server, use the `loovie`-qualified names. A character sheet (multi-pose reference) is **optional** but recommended — when present, downstream first-frame and video generation uses it for stronger consistency. When absent, downstream generation falls back to the original variation image. Never block on the sheet.

## Hard rules

1. Two-step approval applies to every spend: `estimate_*` → user approves → `execute_*`.
2. Quote credits, never dollars. Never name internal models.
3. **Uploads go direct to R2.** Bytes never transit the MCP server. If the user gave you a remote URL, you download it locally first, then upload — do not ask the server to fetch on your behalf.
4. **Preserve the original on the primary path.** When the presigned-PUT path is available (most clients with shell access), upload the file at its native resolution — Loovie keeps it in R2 at full quality and reuses it for future variations, character sheets, and re-generations. Only downsize when forced onto the `dataBase64` fallback (the conversation transport can't carry multi-MB binary). Details in step 1 below.

## Playbook

### 1. Get the image into Loovie

All paths end with a `storageKey` you'll pass into the next step.

**Upload the original whenever the presigned-PUT path works.** Loovie stores the bytes you send at full quality in R2 and uses them for downstream variations, character sheets, and re-generations. Resizing pre-upload permanently loses data the user might want for higher-quality work later. The pipeline does its own resize for inference, but that's an internal optimisation; the stored asset stays at whatever resolution you uploaded. **Only downsize when you're forced onto the `dataBase64` fallback** below — that's a separate path with a real wire-cost ceiling.

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

- **No shell access at all** (rare): only then, use `upload_image_for_reference({ url })` or `upload_image_for_reference({ dataBase64, mimeType, filename })` as a fallback. Both are slower and consume MCP transport bandwidth. **For the `dataBase64` variant only, downsize first** — see the recipe below. The base64 path is hard-capped at ~300 KB encoded by most chat clients' context windows; without the downsize a multi-MB source will exhaust the conversation context mid-upload.

- **Chat-attached image** (user dropped an image into the Claude.ai / Claude Desktop / Cursor chat):
  1. The image lives on the agent's filesystem temporarily. Read its bytes via whatever code-execution tool your runtime exposes (e.g. Test Integration / Code Interpreter / Bash).
  2. **If your runtime can curl-PUT to arbitrary HTTPS hosts, upload the original** via the presigned-URL path above — no downsize, full quality stored. R2 SigV4 hosts must be allowlisted; some sandboxed runtimes block them — if the curl PUT fails with a network or allowlist error, treat R2 PUT as blocked and use the fallback below.
  3. **If R2 PUT is blocked**, fall back to `upload_image_for_reference({ dataBase64, mimeType: 'image/jpeg', filename })` with **downsized** bytes per the recipe below. Quality loss is the price of being able to upload at all in restricted runtimes.

#### Downsize recipe (ONLY for the `dataBase64` fallback)

Skip this entirely when using the presigned-PUT path — uploading the original gives Loovie a higher-quality reference for future re-generations. Apply only when the channel itself forces you to (no presigned-PUT egress).

Target: **1024px max on the long edge, JPEG quality 80**. A typical 2 MB phone photo becomes ~150 KB this way, which fits the `dataBase64` ~300 KB context budget. If your downsized image is STILL larger than ~300 KB, stop and ask the user for a smaller source — don't try to push multi-MB base64 through the conversation transport.

- **Python (Pillow / PIL)**:

  ```python
  from PIL import Image
  img = Image.open('/path/to/original')
  img.thumbnail((1024, 1024))  # preserves aspect ratio
  img.convert('RGB').save('/tmp/loovie-ref.jpg', 'JPEG', quality=80)
  ```

- **Bash (ImageMagick)**: `magick /path/to/original -resize 1024x1024\> -quality 80 /tmp/loovie-ref.jpg`
- **Node (sharp)**: `sharp(input).resize({ width: 1024, height: 1024, fit: 'inside' }).jpeg({ quality: 80 }).toFile('/tmp/loovie-ref.jpg')`

Then base64-encode `/tmp/loovie-ref.jpg` and pass to `upload_image_for_reference({ dataBase64, mimeType: 'image/jpeg' })`.

### 2. Create the character shell

- Ask for a name and a one-line description if not given.
- `create_character` with the name, description, and the uploaded image as the initial `original` variation.

### 3. (Optional) Generate a character sheet

- Skip this step entirely if the user doesn't ask for it, or if the credit cost isn't justified for their use case. Downstream tools work without it.
- If you do generate one:
  - `estimate_generate_character_sheet` with the `characterId`. Show the credit cost.
  - After approval: `execute_generate_character_sheet` → poll `get_job` until terminal.
  - The result is a draft variation. Call `confirm_character_variation` to persist it as the canonical character sheet, or `discard_character_variation` if the user doesn't like it.
  - `get_asset_preview` on the sheet URL so the user sees it inline. If it can't render inline (or the asset host isn't reachable from your runtime), give the user the sheet URL as a clickable link instead — don't loop on the preview tool and don't leave them with nothing.

### 4. (Optional) More variations

- If the user wants extra looks (different outfit, different age, etc.): `estimate_add_character_variation` → approve → `execute_add_character_variation` → `confirm_character_variation`.
- If a character sheet exists, prefer it as the reference for clothes/hair consistency; otherwise reference the original variation image.

## When something fails

- Upload failures: retry once. If the second attempt fails, surface the error and stop.
- Character sheet generation that produces a poor result: do NOT re-run it silently. Show the user the preview and ask whether to retry, accept, or skip the sheet entirely.
