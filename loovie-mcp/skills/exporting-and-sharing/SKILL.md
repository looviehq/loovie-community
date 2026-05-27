---
name: exporting-and-sharing
description: Use when the user wants to render a Loovie project to a final MP4 they can download or share. Covers starting the export, polling status, and surfacing the download URL.
---

# Exporting and sharing

You are turning a Loovie project into a deliverable MP4.

## Hard rules

1. Exports are async. `start_export` returns a `jobId`. Poll `get_export_status(jobId)` (or `get_job(jobId)`) periodically — 5s intervals are fine for exports, they take minutes — until `status` is terminal.
2. The export download URL is presigned and time-limited. Surface it to the user the moment it's ready — don't hold onto it.

## Playbook

### 1. Pick the project
- If the user hasn't named one, `list_projects` and default to most recent.
- Read `loovie://projects/{id}` and summarise what's about to be exported ("3 clips, music set, captions on clips 1 and 2, total runtime ~45s").

### 2. Start the export
- `start_export` with the `projectId` and any quality/resolution options the user gave you. Returns a `jobId`.
- Quote any credit cost up front if the export carries one (most exports today are free at the Loovie layer; check the response).

### 3. Watch it run
- Poll `get_export_status(jobId)` every 5s. Report progress to the user when the status field changes (queued → rendering → uploading → completed). Stop polling on `completed`, `failed`, or `cancelled`.

### 4. Deliver the result
- On success, call `get_export_download_url` (or read the URL from the job result) and present it as a clickable link.
- Optionally `get_asset_preview` to show a thumbnail of the first frame.

### 5. Optional: list past exports
- `list_exports` for the project shows past renders. Useful for "show me my last export" or "redownload yesterday's render".

## When something fails

- `status: 'failed'` with a retryable error: call `retry_export` once.
- `status: 'failed'` with a non-retryable error: surface the error and stop. Do not start a new export silently.
- If the user has no exportable clips on the project, tell them and stop — exports of empty timelines fail.
