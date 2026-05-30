---
name: editing-an-existing-project
description: "Use when the user wants to modify a Loovie project that already exists: change clips, captions, music, transitions, picture-in-picture, color grading, or speed. Covers reading project state and making targeted edits with the project's dedicated editor tools."
---

# Editing an existing Loovie project

You are modifying a project the user already has. The MCP server's editor tools are read-modify-write over the project document. Get the current state first, then edit deliberately.

## Hard rules

1. **Read before you write.** Always read `loovie://projects/{id}` first to see the current timeline, clips, captions, music, transitions. Edits are computed against this state, not against your memory of a previous edit.
2. **Use dedicated tools.** Every editing tool below validates against the project schema and is the right way to make its change. There is no JSON Patch escape hatch — if a mutation isn't covered by a dedicated tool today, tell the user the limit instead of inventing a workaround.
3. Quote credits for any AI-driven edit (`ai-morph` transitions, AI VFX, swap, motion-control). Never invent a USD price.
4. **Image uploads: original on presigned PUT, downsize only on the fallback.** Several edit tools take reference images (PiP source, swap target face, AI VFX reference, motion-control frame). For any of these: prefer `request_image_upload_url` → curl PUT → `finalize_image_upload` and **upload the original** — Loovie keeps it in R2 at full quality for future re-use. Only downsize (to 1024px JPEG q80) when R2 PUT is blocked by your runtime and you must fall back to `upload_image_for_reference({ dataBase64 })`. Full recipe in the `character-from-photo` skill.

## Playbook

### 1. Pick the project

- `list_projects` if the user doesn't name one. Default to most recent.
- Read `loovie://projects/{id}` and summarise the timeline back to the user in plain language ("you have 3 clips, no music, default cuts between them") before suggesting changes.

### 2. Make the change

Match the user's intent to a tool:

| User intent | Tool |
|---|---|
| "add this clip / generate a new clip" | `add_clip` (after polling `get_job` until terminal on the generation) |
| "remove this clip" | `remove_clip` |
| "trim a clip" | `trim_clip` (note: today this adjusts timeline placement, not source in/out — source-trim is deferred) |
| "split a clip" | `split_clip` |
| "change the volume on clip N" | `set_clip_volume` (0–100; 100 = unity) |
| "slow / speed up a clip" | `set_clip_speed` |
| "color correction" | `set_clip_color_grading` |
| "add captions" | `add_caption`; if you need transcript first, `execute_transcribe_audio` |
| "edit caption text/timing/style" | `update_caption` |
| "remove a caption" | `delete_caption` |
| "add a picture-in-picture" | `add_pip` |
| "edit the PiP position/size" | `update_pip` |
| "remove a PiP" | `delete_pip` |
| "add a transition between clips" | `add_transition` (see `loovie://library/transitions`; `ai-morph` costs credits) |
| "set background music" | browse `loovie://library/music` → `set_music_track` |
| "add a sound effect" | `search_stock_audio` → `add_stock_audio_to_project` |
| "swap the face in this clip" | `estimate_apply_swap` → approve → `execute_apply_swap` → poll `get_job` |
| "apply motion control" | `estimate_apply_motion_control` → approve → `execute_apply_motion_control` → poll `get_job` |
| "VFX (rain, fire, etc.)" | `estimate_apply_ai_vfx` → approve → `execute_apply_ai_vfx` → poll `get_job` |
| "cut out a subject (transparent overlay)" | `estimate_create_cutout` → approve → `execute_create_cutout` → poll `get_job` |
| "look at alternate takes for a clip" | `list_clip_variants` → `set_active_clip_variant` to choose |
| "apply a LUT / color preset" | **Not supported today.** The clip schema doesn't carry a LUT field yet; tell the user it's deferred. Color tweaks can still be done via `set_clip_color_grading`. |
| "add a keyframe / animation curve" | **Not supported today.** No dedicated tool covers keyframe writes yet; tell the user it's deferred. |

### 3. Confirm the result

- Re-read `loovie://projects/{id}` and summarise what changed.
- For AI edits that produced a new asset, `get_asset_preview` so the user can see it.

## When something fails

- A 422 / validation error from an editor tool means the patch you computed doesn't satisfy the project schema. Re-read the project, recompute, retry once. Do NOT silently delete clips to "fix" a validation error.
- If the user asks for a mutation not in the table above, tell them it's not currently supported via MCP rather than improvising a workaround that may produce an invalid project document.
