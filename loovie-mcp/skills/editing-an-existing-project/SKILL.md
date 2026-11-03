---
name: editing-an-existing-project
description: "Use when the user wants to modify a Loovie project that already exists: change clips, captions, music, transitions, picture-in-picture, color grading, or speed; extend a clip; or manage the saved backgrounds, music tracks and assets a project uses. Covers reading project state and making targeted edits with the project's dedicated editor tools."
---

# Editing an existing Loovie project

You are modifying a project the user already has. All tools and `loovie://` resources named below live on the `loovie` MCP server; if your client namespaces tools by server, use the `loovie`-qualified names. The server's editor tools are read-modify-write over the project document. Get the current state first, then edit deliberately.

## Hard rules

1. **Read before you write.** Always read `loovie://projects/{id}` first to see the current timeline, clips, captions, music, transitions. Edits are computed against this state, not against your memory of a previous edit.
2. **Use dedicated tools.** Every editing tool below validates against the project schema and is the right way to make its change. There is no JSON Patch escape hatch — if a mutation isn't covered by a dedicated tool today, tell the user the limit instead of inventing a workaround.
3. Quote credits for any AI-driven edit (AI VFX, swap, motion-control, image edits, clip extension). Never invent a price in any currency. Every spend is `estimate_*` then `execute_*`: with MCP confirmation prompts, quote the cost and call `execute_*` straight away (the prompt is the approval); without them, wait for a chat "yes". A declined spend is never retried, and a `pendingApprovalId` is followed with `wait_for_spend_approval`. Transitions, trims and other timeline edits are free. Full flow in `making-a-loovie-video`.
4. **Reference images** (PiP source, swap target face, AI VFX reference, motion-control frame): follow the upload recipe in the `creating-a-character-from-photo` skill. Upload the original via presigned PUT, downsize only on the `dataBase64` fallback.

## Playbook

### 1. Pick the project

- `list_projects` if the user doesn't name one. Default to most recent.
- Read `loovie://projects/{id}` (or call `get_project` / `inspect_project_layout`) and summarise the timeline back to the user in plain language ("you have 3 clips, no music, default cuts between them") before suggesting changes.

### 2. Make the change

Match the user's intent to a tool:

| User intent | Tool |
|---|---|
| "add this clip / generate a new clip" | `add_clip` (after polling `get_job` until terminal on the generation; pass `sequenceOrder` to insert instead of append) |
| "remove this clip" | `remove_clip` |
| "trim a clip" | `trim_clip` (`startTimeMs`/`endTimeMs` are **source** in/out points, milliseconds into the clip's video; the clip keeps its place and later clips shift with the new length) |
| "split a clip" | `split_clip` |
| "change the volume on clip N" | `set_clip_volume` (0–100; 100 = unity) |
| "slow / speed up a clip" | `set_clip_speed` |
| "move / scale / rotate a clip" | `set_clip_transform` |
| "color correction" | `set_clip_color_grading` |
| "add captions" | `add_caption`; if you need transcript first, `execute_transcribe_audio` |
| "edit caption text/timing/style" | `update_caption` |
| "remove a caption" | `delete_caption` |
| "add a picture-in-picture" | `add_pip` |
| "edit the PiP position/size" | `update_pip` |
| "remove a PiP" | `delete_pip` |
| "add a transition between clips" | `add_transition` (see `loovie://library/transitions`; every transition type is free) |
| "set background music" | browse `loovie://library/music` → `set_music_track` |
| "add a sound effect" | `search_stock_audio` → `add_stock_audio_to_project` |
| "swap the face in this clip" | `estimate_apply_swap` → `execute_apply_swap` → poll `get_job` |
| "apply motion control" | `estimate_apply_motion_control` → `execute_apply_motion_control` → poll `get_job` |
| "VFX (rain, fire, etc.)" | `estimate_apply_ai_vfx` → `execute_apply_ai_vfx` → poll `get_job` |
| "cut out a subject (transparent overlay)" | `estimate_create_cutout` → `execute_create_cutout` → poll `get_job` |
| "edit or restyle an image" | `estimate_edit_image` → `execute_edit_image` → poll `get_job`. Pass `entityType` plus one source (`sourceStorageKey`, `sourceImageUri`, or `entityId`) and one change field (`editPrompt`, `poseMatchMode` + `referenceStorageKey`, `styleReferenceStorageKey`, or `backgroundStorageKey`). If the edit shows or names a library character or asset, attach it with `characterIds` / `assetIds` (a text description is not a reference, and `@Name` in the prompt attaches nothing). Leave `aspectRatio` unset (it defaults to `auto`, keeping the source's own ratio) unless the user asked for a different one. Check the `references` list in the estimate before executing. |
| "generate music for the project" | `estimate_generate_music` → `execute_generate_music` → `set_music_track` |
| "change the project's aspect ratio or defaults" | `get_project_defaults`, `update_project_settings` |
| "duplicate or delete a project" | `duplicate_project` / `delete_project` (confirm with the user before deleting) |
| "look at alternate takes for a clip" | `list_clip_variants` → `set_active_clip_variant` to choose |
| "extend a clip with new footage" | `estimate_extend_clip` → `execute_extend_clip` → poll `get_job` (the new clip lands right after the source; extend the returned `clipId` to go further) |
| "remove an alternate take" | `delete_clip_variant` |
| "use a music track I saved / see its details" | `list_music_tracks` → `get_music_track` |
| "delete a saved music track" | `delete_music_track` |
| "edit, duplicate, regenerate or remove a background" | `update_background`, `duplicate_background`, `estimate_regenerate_background` → `execute_regenerate_background`, `delete_background` |
| "rename / describe / remove a saved asset" | `get_asset`, `update_asset`, `delete_asset` |
| "apply a LUT / color preset" | **Not supported today.** The clip schema doesn't carry a LUT field yet; tell the user it's deferred. The `loovie://library/luts` resource lets you *browse* the LUT catalog, but there is no tool to apply one to a clip. Color tweaks can still be done via `set_clip_color_grading`. |
| "add a keyframe / animation curve" | **Not supported today.** `get_schema` documents keyframes, but no dedicated tool writes them yet; tell the user it's deferred. |
| "generate a new clip that features a character, product or place" | Hand off to `making-a-loovie-video`: use `references[]` with `@tag` mentions on `estimate_generate_video` |

`estimate_extend_clip` validates up front and returns a named code instead of an approval token when the request cannot run: `SOURCE_NOT_VIDEO` (an image clip — generate a new video from it instead), `SOURCE_REVERSED`, `SOURCE_TOO_SHORT` (under 1.7 s), `SOURCE_NOT_READY` (still generating), `EXTEND_ALREADY_RUNNING` (wait, then extend the clip it creates), `AUDIO_REFERENCE_INVALID`. It takes `projectId`, `clipId`, `prompt` (the continuation, not what is already in the clip), optional `durationSec` (1–15, default 5), `qualityTier`, `resolution`, and `audioReferences[]` (music, project music, or a character voice). It takes no image or character references: the source clip is the visual reference. Tiers and per-resolution rates come from `get_generation_capabilities({ surface: "extend_clip" })`.

### 3. Confirm the result

- Re-read `loovie://projects/{id}` and summarise what changed.
- After any layout change (transform, PiP, captions, trims), run `inspect_project_layout` and describe its findings in plain language: overlays hidden behind others, overlays that end before the main track, off-frame overlays, captions after the end.
- For AI edits that produced a new asset, the terminal `get_job` already inlines a thumbnail or a signed video URL; `get_asset_preview` is there to re-surface it. If it can't render inline, hand the user the asset URL as a clickable link instead — never end with nothing to view.

## When something fails

- A 422 / validation error from an editor tool means the patch you computed doesn't satisfy the project schema. Re-read the project, recompute, retry once. Do NOT silently delete clips to "fix" a validation error.
- When unsure about the exact shape of a clip, caption, PiP, transition or color grading field, call `get_schema` with that entity name before writing.
- If the user asks for a mutation not in the table above, tell them it's not currently supported via MCP rather than improvising a workaround that may produce an invalid project document.
