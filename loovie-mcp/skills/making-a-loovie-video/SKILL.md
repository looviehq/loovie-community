---
name: making-a-loovie-video
description: "Use when the user wants to create a new Loovie video from a brief, story idea, or prompt. Covers the full happy path: new project, pick or generate a character, generate a first frame, generate the video, assemble clips, add music, export."
---

# Making a Loovie video

You are working with the user to produce a finished video on Loovie. The Loovie MCP server is connected as `loovie`. Follow this playbook unless the user steers off it.

## Hard rules

1. **Estimate before you execute.** Every `execute_*` generation tool requires the `approvalToken` returned by the matching `estimate_*` call. Never skip the estimate. If the estimate response returns a `pendingApprovalId` instead of an immediate token, the spend needs explicit approval: call `wait_for_spend_approval` (it streams progress so the connection survives long waits) and tell the user they can approve either by tapping the push notification in their Loovie mobile app or by saying "approve in chat", in which case you call `approve_pending_spend({ pendingApprovalId })`. On approval, pass the returned `originalParams` **as-is** to the matching `execute_*` call — any drift from the approved params fails server-side hash verification and the spend is rejected.
2. **Talk in credits, never dollars.** Quote `estimatedCredits` from the estimate response verbatim. Never invent a USD price.
3. **Poll, don't block.** Generation tools return a `jobId`. Poll `get_job(jobId)` periodically (2s for the first 20s, then 5s thereafter) until `status` is terminal (`completed` / `failed` / `cancelled` / `timeout`). For N parallel jobs, fire all `execute_*` calls in one turn to collect jobIds, then poll each in parallel.
4. **Show your work — and never leave the user with a blank.** When a job completes, call `get_asset_preview` on the resulting asset URL so the user sees the result inline. If the client can't render it inline or you can't fetch the bytes (e.g. the asset host isn't on your runtime's network allowlist), **don't loop on the preview tool** — paste the asset URL as a plain clickable markdown link (`[Stella's first frame](https://…)`) so the user can open it in a browser. Every completed job ends with either an inline preview or a working link, never nothing. If the inline preview failed because the asset host is blocked by the runtime's allowlist, mention that the user can add `api.loovie.app` to their client's network allowlist to get inline previews.
5. **If the user supplies a reference image** (for the first-frame seed, a character, a background): follow the upload recipe in the `creating-a-character-from-photo` skill — upload the original via presigned PUT, downsize only on the `dataBase64` fallback.

## Playbook

### 1. Set the table

- Read `loovie://credits` to know the user's balance up front. If it's low, surface that immediately.
- Read `loovie://library/prompt-craft` once at the start of the session for the prompt checklist.

### 2. Create the project

- Ask the user for a title and short brief if they haven't given one.
- Call `create_project` with the brief. Read the returned `projectId`.

### 3. Pick or make a character

- If the user references an existing character: `list_characters` and pick by name.
- If they want a starter: read `loovie://library/starter-characters` and `clone_character`.
- If they want a new one from a photo: hand off to the `creating-a-character-from-photo` skill.
- If they want a new one from a prompt: `estimate_generate_character_image` → user approves → `execute_generate_character_image` → poll `get_job`. Optionally follow with `execute_generate_character_sheet` to produce a multi-pose reference sheet for stronger consistency in downstream generation — skip when the user doesn't want to spend the extra credits; downstream tools work without it.

### 4. Generate the opening frame

- Compose a prompt that names subject, action, lighting, camera, style, mood (see `loovie://library/prompt-craft`).
- Use `score_prompt` to sanity-check the draft.
- `estimate_generate_first_frame` with the character variation image as reference. Show the credit cost.
- After approval: `execute_generate_first_frame` → poll `get_job` until terminal → `get_asset_preview` so the user can see it.

### 5. Generate the video

- `estimate_generate_video` with the first frame as the start anchor. Pick a `qualityTier` and `durationSec` that fit the user's brief.
- If the user wants the shot to land on a specific closing image, generate an end anchor first (`estimate_generate_last_frame` → approve → `execute_generate_last_frame`) and pass it alongside the first frame.
- After approval: `execute_generate_video` → poll `get_job` until terminal → `get_asset_preview`.

### 6. Assemble the timeline

- Add each generated clip to the project with `add_clip`.
- For multi-clip videos, add transitions between clips with `add_transition` (read `loovie://library/transitions` for options).
- For captions, use `add_caption`. If you need auto-captions from the audio track, call `execute_transcribe_audio` first.
- For background music, browse `loovie://library/music` and call `set_music_track`. If nothing in the library fits, offer to generate a custom track: `estimate_generate_music` → approve → `execute_generate_music` → poll `get_job` → `set_music_track`.

### 7. Export

- Hand off to the `exporting-and-sharing` skill.

## When something fails

- A tool call rejecting the `loovie-spark` quality tier (a `Forbidden` or unavailable error) means Loovie's in-house pipeline isn't enabled for this user or flow — it only supports single-shot video and image generation. Fall back to `standard` (the default tier), or `high` if the user asked for higher quality.
- A `get_job` poll returning `status: 'failed'` should be retried once with the same input. If it fails again, surface the error message to the user and stop — do not silently keep spending credits.
- A `get_job` poll returning `status: 'timeout'` is terminal, not retryable-in-place: surface the job's `error` block and ask the user before starting a new job.
- A `get_job` poll returning `status: 'pending_approval'` means the job is waiting on a credit-spend approval. The user can approve by tapping the push notification in their Loovie mobile app, or in-chat — call `approve_pending_spend` on their say-so. Then continue polling.
- If the user's balance won't cover the estimate, stop and tell them. Do not start the job.
