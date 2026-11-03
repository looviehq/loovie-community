---
name: exporting-and-sharing
description: Use when the user wants to render a Loovie project to a final MP4 they can download or share. Covers starting the export, polling status, and surfacing the download URL.
---

# Exporting and sharing

You are turning a Loovie project into a deliverable MP4. All tools and `loovie://` resources named below live on the `loovie` MCP server; if your client namespaces tools by server, use the `loovie`-qualified names.

## Hard rules

1. Exports are async. `start_export` returns a `jobId`. Poll `get_export_status(jobId)` (or `get_job(jobId)`) periodically — 5s intervals are fine for exports, they take minutes — until `status` is terminal (`completed` / `failed` / `cancelled` / `timeout`).
2. The export download URL is presigned and time-limited. Surface it to the user the moment it's ready — don't hold onto it.

## Playbook

### 1. Pick the project

- If the user hasn't named one, `list_projects` and default to most recent.
- Read `loovie://projects/{id}` and summarise what's about to be exported ("3 clips, music set, captions on clips 1 and 2, total runtime ~45s").

### 2. Start the export

- First run `inspect_project_layout` and tell the user about anything it flags: overlays hidden behind others, overlays that end before the main track, off-frame overlays, captions after the end, a video playing twice.
- `start_export` with the `projectId` and an optional `format` (`mp4` default, or `mov` / `webm` / `gif`). Returns a `jobId`. Resolution and quality are **not** parameters — they come from the project settings, so say that rather than promising a different render size.
- If the response includes `cached: true`, the project hasn't changed since its last successful export — skip polling entirely and go straight to `get_export_download_url`.
- Quote any credit cost up front if the export carries one (check the response; most exports are free at the Loovie layer).

### 3. Watch it run

- Poll `get_export_status(jobId)` every 5s. Report progress to the user when the status field changes (queued → rendering → uploading → completed). Stop polling on `completed`, `failed`, `cancelled`, or `timeout`.

### 4. Deliver the result

- On success, call `get_export_download_url` (or read the URL from the job result) and present it as a clickable link.
- Optionally `get_asset_preview` to show a thumbnail of the first frame.

### 5. Optional: list past exports

- `list_exports` for the project shows past renders. Useful for "show me my last export" or "redownload yesterday's render". It pages with `limit` / `offset`; `pagination.hasMore` says whether there is another page.
- `cancel_export` deletes an export job — an in-flight one is cancelled, a completed one also loses its rendered file. Confirm with the user before calling it.

## When something fails

- `status: 'failed'` with a retryable error: call `retry_export` once.
- `status: 'timeout'`: the render exceeded its window. Call `retry_export` once; if it times out again, surface the error and stop.
- `status: 'failed'` with a non-retryable error: surface the error and stop. Do not start a new export silently.
- If the user wants to abandon a render rather than retry it, `cancel_export` removes the job (and the file, for a completed export). Ask first.
- If the user has no exportable clips on the project, tell them and stop — exports of empty timelines fail.
