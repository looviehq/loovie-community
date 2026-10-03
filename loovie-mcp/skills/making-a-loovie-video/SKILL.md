---
name: making-a-loovie-video
description: "Use when the user wants to create a new Loovie video from a brief, story idea, or prompt. Covers the full happy path: new project, characters and reference material, generating the video (single-shot or multi-shot, with @tag references), assembling clips, adding music, export."
---

# Making a Loovie video

You are working with the user to produce a finished video on Loovie. The Loovie MCP server is connected as `loovie`. Follow this playbook unless the user steers off it.

## Hard rules

1. **Estimate before you execute.** Every `execute_*` generation tool requires the `approvalToken` returned by the matching `estimate_*` call. Never skip the estimate. The estimate also validates the whole request and names each bad field, so fix what it rejects and estimate again instead of guessing.
2. **Talk in credits, never dollars.** Quote the integer `estimatedCredits` from the estimate verbatim. Never invent a price in any currency, and never guess a cost without an estimate.
3. **One approval per spend.** If your client can show MCP confirmation prompts, tell the user the credit cost in your reply and call `execute_*` straight away: the confirmation prompt Loovie shows is the approval, so do not also ask for a "yes" in chat. Only when your client cannot show those prompts do you wait for an explicit "yes" in chat before calling `execute_*`. Holding an `approvalToken` is never approval by itself.
4. **Declined means stop.** If `execute_*` comes back declined, do not retry. Never change spend limits (`set_mcp_spend_preferences`) to get past a refusal or a limit: those are the user's to raise in the Loovie app.
5. **Escalated approvals.** If no prompt could be shown, the result names a `pendingApprovalId`. Tell the user they can tap the push notification in the Loovie app, or say "approve in chat" (then call `approve_pending_spend({ pendingApprovalId })`). Keep calling `wait_for_spend_approval({ pendingApprovalId })` until it returns `approved` (a `timeout` with `stillPending` is not an error, call it again). Then run the matching `execute_*` with the returned `originalParams` exactly as given, or pass `execute: true` to let the wait tool run it. Any drift in params fails server-side verification.
6. **Poll, don't block.** Generation tools return a `jobId`. Poll `get_job(jobId)` (2s for the first 20s, then 5s) until `status` is terminal (`completed` / `failed` / `cancelled` / `timeout`). For video, poll the top-level `jobId`, never `video.id`, which 404s. For N parallel jobs, fire all `execute_*` calls in one turn to collect jobIds, then poll each.
7. **Show your work, and never leave the user with a blank.** When a job completes, call `get_asset_preview` on the resulting asset so the user sees it inline. If the client can't render it inline or you can't fetch the bytes (for example the asset host isn't on your runtime's network allowlist), don't loop on the preview tool: paste the asset URL as a plain clickable markdown link (`[Stella's first frame](https://…)`). Every completed job ends with either an inline preview or a working link. If the preview failed because of the allowlist, mention that the user can add `api.loovie.app` to their client's allowlist for inline previews.
8. **Never surface internal model or provider names.** Talk in tier, variant, duration, resolution and audio terms only.
9. **Uploads take storage keys, never URLs.** Anywhere a tool asks for a `storageKey`, it must come from an upload or the library. If the user supplies a reference image or clip, upload the **original** (presigned PUT, see `creating-a-character-from-photo`). Only downsize when forced onto the `dataBase64` fallback.

## Playbook

### 1. Set the table

- Call `get_credit_balance` (or read `loovie://credits`) to know the balance up front. If it is low, say so immediately.
- Read `loovie://library/prompt-craft` once at the start of the session for the prompt checklist. Clients without resource support can use `browse_library` / `search_library` for the library kinds.
- Call `get_project_defaults` if the user has a project and hasn't stated aspect ratio or similar settings.

### 2. Create the project

- Ask for a title and short brief if they haven't given one.
- Call `create_project` and keep the returned `projectId`. **Pass `projectId` on every generation call that belongs in this project.** If it is omitted, the server creates a brand new project instead of appending to yours.

### 3. Gather references

References are how you keep people, products, places and looks consistent through a clip. Collect them before writing the prompt, because the prompt has to point at them.

If the user wants a new character from a prompt rather than a photo or a starter: `estimate_generate_character_image` → `execute_generate_character_image` → poll `get_job`. Optionally follow with `estimate_generate_character_sheet` → `execute_generate_character_sheet` for a multi-pose sheet, which strengthens consistency downstream. Skip it when the user doesn't want to spend the extra credits, since downstream tools work without it. Starter characters: read `loovie://library/starter-characters` and `clone_character`.

| Reference kind | What it is | Where it comes from |
|---|---|---|
| `character` | A Loovie character (optionally a specific outfit/look) | `list_characters`, `clone_character` for a starter, or the `creating-a-character-from-photo` skill. Pass `sourceId`, plus `variationId` (from `get_character`) to pin a look |
| `asset` | A saved asset such as a product or prop | `list_assets`, `create_asset` |
| `background` | A saved background | `list_backgrounds`, `execute_create_background` |
| `upload` | An image the user supplied | `request_image_upload_url` → curl PUT → `finalize_image_upload`, pass the `storageKey` |
| `style` / `location` | An uploaded image used as the look or the place | Same upload flow, pass the `storageKey` |
| `video` | A reference clip, 2 to 15 s | `request_video_upload_url` → curl PUT → `finalize_video_upload`, pass the `storageKey` plus optional `trimStartMs` / `trimEndMs` |
| `audio` | A reference audio clip | Upload the same way. It needs at least one image or video reference alongside it |

Rules for `references[]` on `estimate_generate_video` / `execute_generate_video`:

- **Up to 7 references.** Each one needs a unique `tag` of 1 to 32 letters, digits or underscores (for example `Maya`, `Sneaker`, `Alley`). Never use `Image1` / `Element1` style names.
- **Point at each reference from the prompt with `@tag`**: `@Maya walks into @Alley holding @Sneaker`. A reference nobody mentions in the prompt is wasted. In multi-shot, mention it in the shot prompt where it appears.
- **Not available on the `basic` tier.** Each tier caps how many references it accepts, and some engines fold a first frame into the same slots. The estimate rejects an over-limit request and names the field. It never silently drops one, so if you get a rejection, trim the list or change tier rather than retrying the same request.
- **A last frame cannot be combined with references on `loovie-spark` / `loovie-spark-max`.** Choose between a start-to-end morph and reference-driven generation.
- To check in advance, call `get_generation_capabilities` with `surface: single_shot_video` (or `multi_shot_video`), the tier, and `hasFirstFrame` / `hasLastFrame` / `hasMultiShot` only when they are really set. Its `references` field says whether references are accepted and the limits (`maxReferences`, image slots, max clips, max audio).
- Prefer a `{ kind: "character" }` reference over the legacy `characterIds` field. `characterIds` only composes characters into a generated first frame, while a reference keeps the character consistent through the whole clip.
- If the user has no reference for a key subject, offer to make one first: `estimate_generate_character_image`, `estimate_generate_image`, or `estimate_create_background`, each followed by its `execute_*`. Don't invent reference ids.

### 4. Choose how to start the clip

Pick the `generationMode` from what the user actually has:

- `text_to_video`: prompt only, plus `references[]` if they have any. The most common path now: references carry consistency, so a separate first-frame step is optional.
- `image_to_video`: the user wants to start from a specific image. Needs `firstFrameStorageKey`. Use `estimate_generate_first_frame` / `execute_generate_first_frame` to make one from a prompt and characters, then pass its storage key.
- `start_end_frames`: a morph between two images. Needs first and last frame keys. If the user wants the shot to land on a specific closing image, make one first with `estimate_generate_last_frame` → `execute_generate_last_frame`. Cannot be combined with references on the Spark tiers.
- `multi_shot`: several shots in one clip (see step 6).

Only set `hasFirstFrame` / `hasLastFrame` on discovery tools when those frames really exist, since setting them speculatively reroutes the options.

### 5. Generate a single-shot video

1. **Pick the tier and settings.** `loovie-spark-max` is the default. With no tier named, estimate on it straight away: no tier menu, and don't default to `high` or `ultra`. The one exception is a high-action scene (fights, stunts, chases, crashes, dancing, crowds in motion, very fast movement). For those, recommend Ultra and show its cost beside the Spark Max cost (the estimate returns it under `alternatives`), then let the user pick. Never switch tiers on your own. Calm, character-driven scenes (talking, walking, reacting) stay on the default. When the user names a constraint ("12 seconds with audio", "1080p"), call `recommend_generation_options` with `surface: video` and surface every row, including `nearMatches` (for example "that tier would work if you turn audio off"). For plain "what are my options" questions use `list_quality_tiers`. Durations and resolutions differ per tier and with audio, so call `get_generation_capabilities` before quoting them.
2. **Write the prompt.** Unless the user said "use my prompt as-is" (then set `promptVerbatim: true`), direct subject motion, camera motion, lighting, camera angle and style, with `@tag` mentions for each reference. When a first or last frame is supplied, direct only motion and camera motion, because the frame already locks style and lighting.
3. **Estimate.** `estimate_generate_video` with `generationMode`, `prompt`, `aspectRatio`, `duration`, `videoQualityTier`, `references`, `withAudio` and the projectId. Read `promptQuality`: if `promptShouldBeRicher` is true, rewrite using `suggestions` and estimate again. No separate `score_prompt` call is needed. Quote `estimatedCredits`.
4. **Execute** with the same params plus `approvalToken`, following the spend rules above, then poll `get_job` and `get_asset_preview`.

Do not set `maxSpeed` unless the user wants a faster render. It is not cheaper, only available on `loovie-spark-max`, and the estimate rejects ineligible combinations with the reason.

### 6. Generate a multi-shot video

- `generationMode: multi_shot`, with the tier in `multiShotQualityTier` (not `videoQualityTier`). The top-level `prompt` is a one or two sentence overview.
- `multiShot.shots[]` takes 2 to 8 shots. Each shot has its own `prompt` (its own subject motion, camera direction and lighting, max 500 characters), `durationSeconds` (1 to 12), and optional `dialogue` and `transitionDescription`. Total length is the sum of the shots.
- Put `@tag` mentions in the shot prompts where each reference appears. Declare the references once in the top-level `references[]`.
- To pin a shot's look, give it a `referenceImageStorageKey`. Shot images are combined into one panel reference for the clip.
- For tighter planning, make a storyboard grid first: `estimate_create_storyboard_grid` → `execute_create_storyboard_grid` → `get_storyboard_grid`, then pass the finished grid as `storyboardGridStorageKey`. **Don't set per-shot `referenceImageStorageKey` together with a storyboard grid.** The grid isn't available on `basic`, and on `high` only with `multiShot.shots[]`.
- Prefer `multiShot.shots[]` over the legacy `simpleMultiShot` flag.

### 7. Assemble the timeline

- Generated clips are appended to the project you passed. If you need to place one manually, use `add_clip`.
- For multi-clip videos, add transitions with `add_transition` (read `loovie://library/transitions` for options).
- For captions, use `add_caption`. For auto-captions from an audio track, run `estimate_transcribe_audio` → `execute_transcribe_audio` first.
- For background music, browse `loovie://library/music` (or `list_music_tracks` / `browse_library`) and call `set_music_track`, or generate one with `estimate_generate_music` → `execute_generate_music`.
- For anything beyond this, hand off to the `editing-an-existing-project` skill.

### 8. Export

- Hand off to the `exporting-and-sharing` skill.

## When something fails

- A tool call rejecting a tier (a `Forbidden` or unavailable error) means that tier isn't enabled for this user or flow. Fall back to the default tier and say so.
- A `get_job` poll returning `status: 'failed'` should be retried once with the same input. If it fails again, surface the error message to the user and stop. Do not silently keep spending credits.
- A `get_job` poll returning `status: 'timeout'` is terminal, not retryable in place: surface the job's `error` block and ask the user before starting a new job.
- A `get_job` poll returning `status: 'pending_approval'`, or an `execute_*` result with a `pendingApprovalId`, means the spend is waiting on approval. Follow hard rule 5.
- If the user's balance won't cover the estimate, stop and tell them. Do not start the job.
