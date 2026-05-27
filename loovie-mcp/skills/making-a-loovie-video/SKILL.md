---
name: making-a-loovie-video
description: "Use when the user wants to create a new Loovie video from a brief, story idea, or prompt. Covers the full happy path: new project, pick or generate a character, generate a first frame, generate the video, assemble clips, add music, export."
---

# Making a Loovie video

You are working with the user to produce a finished video on Loovie. The Loovie MCP server is connected as `loovie`. Follow this playbook unless the user steers off it.

## Hard rules

1. **Estimate before you execute.** Every `execute_*` generation tool requires the `approvalToken` returned by the matching `estimate_*` call. Never skip the estimate.
2. **Talk in credits, never dollars.** Quote `estimatedCredits` from the estimate response verbatim. Never invent a USD price.
3. **Poll, don't block.** Generation tools return a `jobId`. Poll `get_job(jobId)` periodically (2s for the first 20s, then 5s thereafter) until `status` is terminal (`completed` / `failed` / `cancelled`). For N parallel jobs, fire all `execute_*` calls in one turn to collect jobIds, then poll each in parallel.
4. **Show your work.** When a job completes, call `get_asset_preview` on the resulting asset URL so the user sees the result inline (Cursor) or as a clickable link (Claude Code / Desktop).

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
- If they want a new one from a photo: hand off to the `character-from-photo` skill.
- If they want a new one from a prompt: `estimate_generate_character_image` → user approves → `execute_generate_character_image` → poll `get_job`. Optionally follow with `execute_generate_character_sheet` to produce a multi-pose reference sheet for stronger consistency in downstream generation — skip when the user doesn't want to spend the extra credits; downstream tools work without it.

### 4. Generate the opening frame

- Compose a prompt that names subject, action, lighting, camera, style, mood (see `loovie://library/prompt-craft`).
- Use `score_prompt` to sanity-check the draft.
- `estimate_generate_first_frame` with the character variation image as reference. Show the credit cost.
- After approval: `execute_generate_first_frame` → poll `get_job` until terminal → `get_asset_preview` so the user can see it.

### 5. Generate the video

- `estimate_generate_video` with the first frame as the start anchor. Pick a `qualityTier` and `durationSec` that fit the user's brief.
- After approval: `execute_generate_video` → poll `get_job` until terminal → `get_asset_preview`.

### 6. Assemble the timeline

- Add each generated clip to the project with `add_clip`.
- For multi-clip videos, add transitions between clips with `add_transition` (read `loovie://library/transitions` for options).
- For captions, use `add_caption`. If you need auto-captions from the audio track, call `execute_transcribe_audio` first.
- For background music, browse `loovie://library/music` and call `set_music_track`.

### 7. Export

- Hand off to the `exporting-and-sharing` skill.

## When something fails

- A tool call returning `isError: true` with a `Forbidden` for `loovie-custom` means the experimental tier is gated for this user. Fall back to `high`.
- A `get_job` poll returning `status: 'failed'` should be retried once with the same input. If it fails again, surface the error message to the user and stop — do not silently keep spending credits.
- A `get_job` poll returning `status: 'pending_approval'` means the job is waiting on a mobile-app credit-spend approval. Tell the user to approve in their Loovie app, then continue polling.
- If the user's balance won't cover the estimate, stop and tell them. Do not start the job.
