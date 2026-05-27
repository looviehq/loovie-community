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

## Playbook

### 1. Get the image into Loovie

All paths end with a `storageKey` you'll pass into the next step.

- **Local file on disk + you have shell access** (Claude Code, Cursor with shell):
  1. `request_image_upload_url({ filename, contentType })` — returns `{ uploadUrl, finalizePath, instructions.curl }`. `uploadUrl` is a presigned R2 PUT URL.
  2. Run the `instructions.curl` command via Bash. The image PUTs straight to R2.
  3. `finalize_image_upload({ ... })` — returns `{ storageKey, imageUrl }`.

- **Remote URL the user gave you** (e.g. an image link they pasted):
  1. **Download it locally first.** `curl -L -o /tmp/loovie-ref.<ext> '<url>'` via Bash.
  2. Then follow the local-file path above — `request_image_upload_url` → curl PUT → `finalize_image_upload`.
  3. Do NOT call `upload_image_for_reference({ url })` to make the server fetch on your behalf. The direct-to-R2 path is the only flow this skill uses when shell is available.

- **Image already exists in the library**: `loovie://library/...` or `list_characters` to find it; reuse its `storageKey`.

- **No shell access at all** (rare): only then, use `upload_image_for_reference({ url })` or `upload_image_for_reference({ dataBase64, mimeType, filename })` as a fallback. Both are slower and consume MCP transport bandwidth.

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
