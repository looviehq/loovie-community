"""HTTP routes implementing the Loovie BYO server contract.

Routes are registered on `PromptServer.instance.routes` at module import,
which means they appear on whatever aiohttp server ComfyUI itself is
running (no separate port, no separate process). The contract is defined
by `openapi/loovie-server.openapi.yaml`.

Auth model (fail-closed):
  - `/loovie/health` and `/loovie/capabilities` are ALWAYS unauthenticated.
  - Every other route requires `Authorization: Bearer <LOOVIE_API_TOKEN>`.
  - Localhost (`127.0.0.1`, `::1`) bypasses auth.
  - If no token is configured, remote requests are REFUSED (401). This is
    intentional: a missing token means the operator hasn't decided to
    expose the server publicly yet.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import uuid
from typing import Any

from aiohttp import web
from aiohttp.multipart import BodyPartReader
from server import PromptServer

from ..capabilities import build_capabilities_manifest
from ..helpers.aspect_ratio import target_video_dimensions, video_dimensions
from ..models import (
    available_models,
    default_model,
    detect_hardware,
    image_canvas_resolution,
    residency_group,
    resolve_workflow,
    shared_models_config,
    validate_request_values,
)
from ..monitor import start_monitor
from ..task_store import TaskState, TaskStore
from ..workflow_manager import WorkflowManager

logger = logging.getLogger("comfyui_loovie.routes")

VERSION = "0.5.0"

# Music prompt cap, mirroring the app-side music DTO bound. Distinct from the
# 3000-char image/video cap so a long style prompt is rejected at the contract
# boundary rather than silently trimmed.
MUSIC_PROMPT_CHAR_LIMIT = 2000

# SFX prompts are short descriptions, not lyric sheets. The cap mirrors the
# app-side SFX DTO bound.
SFX_PROMPT_CHAR_LIMIT = 2000

# Default text-to-music workflow when the request carries no `workflow`.
_DEFAULT_MUSIC_WORKFLOW = "yue2-t2m-fast"

# Default text-to-sound-effect workflow.
_DEFAULT_SFX_WORKFLOW = "stable-audio-3-t2s-small"


# --- auth -------------------------------------------------------------------


def _is_local_request(request: web.Request) -> bool:
    """True if the request comes from the loopback interface."""
    peername = request.transport.get_extra_info("peername") if request.transport else None
    if not peername:
        return False
    host = peername[0]
    return host in ("127.0.0.1", "::1")


def _check_auth(request: web.Request) -> web.Response | None:
    """Validate the bearer token. Returns a 401 response or None on success.

    Fail-closed semantics: remote requests with no configured token are
    refused. Localhost callers always bypass. Public probe endpoints
    (`/loovie/health`, `/loovie/capabilities`) bypass auth at the
    decorator boundary and never reach this function.
    """
    if _is_local_request(request):
        return None

    token = WorkflowManager.get_instance().api_token
    if not token:
        # Fail closed: no token configured but the caller is remote.
        logger.warning(
            "Refusing remote request: LOOVIE_API_TOKEN is not configured (path=%s)",
            request.path,
        )
        return web.json_response(
            {
                "code": 401,
                "msg": "Server has no LOOVIE_API_TOKEN configured; remote requests are refused.",
            },
            status=401,
        )

    header = request.headers.get("Authorization", "")
    if header == f"Bearer {token}":
        return None
    return web.json_response({"code": 401, "msg": "Unauthorized"}, status=401)


# --- helpers ---------------------------------------------------------------


def _resolve_output_base_url(request: web.Request) -> str:
    """Derive the public base URL for `/view?...` result URLs.

    Result URLs must be reachable by the calling device, so we honour
    deployment env vars first (RunPod proxy, an explicit public URL),
    then fall back to the inbound request's host headers, and finally
    to the loopback default.
    """
    runpod_id = os.environ.get("RUNPOD_POD_ID", "").strip()
    if runpod_id:
        return f"https://{runpod_id}-8188.proxy.runpod.net"

    public_url = (os.environ.get("LOOVIE_PUBLIC_URL") or "").strip().rstrip("/")
    if public_url:
        return public_url

    proto = (
        (request.headers.get("X-Forwarded-Proto") or request.scheme or "http").split(",")[0].strip()
    )
    host = (request.headers.get("X-Forwarded-Host") or request.host or "").split(",")[0].strip()
    host_only = host.split(":")[0].lower()
    if host and host_only not in ("127.0.0.1", "localhost", "::1", "[::1]"):
        return f"{proto}://{host}".rstrip("/")

    return WorkflowManager.get_instance().output_base_url


def _redact(url: str) -> str:
    if not isinstance(url, str):
        return url
    return url.split("?", 1)[0]


def _log_safe_body(body: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `body` with prompts/lyrics truncated and URLs redacted."""
    out = dict(body)
    prompt = out.get("prompt")
    if isinstance(prompt, str):
        out["prompt_length"] = len(prompt)
        if len(prompt) > 200:
            out["prompt"] = prompt[:200] + "..."
    # A lyric sheet is user-authored creative text; log its length only.
    lyrics = out.get("lyrics")
    if isinstance(lyrics, str):
        out["lyrics_length"] = len(lyrics)
        out["lyrics"] = f"<{len(lyrics)} chars>"
    if isinstance(out.get("image_urls"), list):
        out["image_urls"] = [_redact(u) for u in out["image_urls"]]
    if isinstance(out.get("reference_image_urls"), list):
        out["reference_image_urls"] = [_redact(u) for u in out["reference_image_urls"]]
    for key in ("mask_url", "start_frame_url", "end_frame_url"):
        v = out.get(key)
        if isinstance(v, str) and v:
            out[key] = _redact(v)
    return out


def _inject_inputs(workflow: dict[str, Any], body: dict[str, Any]) -> None:
    """Walk the workflow JSON and inject API values into Loovie nodes."""
    image_urls = list(body.get("image_urls") or [])
    mask_url = (body.get("mask_url") or "").strip()
    loras = body.get("loras") or []
    # Video request fields are normalised into `image_urls` for the
    # `LoovieImageInput` node so a single graph can serve i2v and fl2v.
    start_frame = (body.get("start_frame_url") or "").strip()
    end_frame = (body.get("end_frame_url") or "").strip()
    reference_urls = [
        str(url).strip() for url in (body.get("reference_image_urls") or []) if str(url).strip()
    ]
    if reference_urls and not start_frame:
        # ref2v: references ride the same image slots as i2i.
        image_urls = reference_urls
    elif start_frame and not image_urls:
        image_urls = [start_frame]
        if end_frame:
            image_urls.append(end_frame)

    for node in workflow.values():
        cls = node.get("class_type", "")
        inputs = node.setdefault("inputs", {})

        if cls == "LoovieTextInput":
            inputs["prompt"] = body.get("prompt", "")
            inputs["negative_prompt"] = body.get("negative_prompt", "")

        elif cls == "LoovieSettings":
            inputs["aspect_ratio"] = body.get("aspect_ratio", "1:1")
            inputs["seed"] = int(body.get("seed", -1))
            # Opt-in models get a real 1K/2K/4K canvas; everything else
            # stays on the legacy table via the node default.
            inputs["resolution"] = str(body.get("_loovie_image_resolution", "auto"))

        elif cls == "LoovieImageInput":
            max_images = 9 if mask_url else 10
            for i, url in enumerate(image_urls[:max_images], 1):
                inputs[f"image_url_{i}"] = url
            if mask_url:
                inputs["mask_url"] = mask_url

        elif cls == "LoovieLoraStack":
            for i, lora in enumerate(loras[:5], 1):
                if not isinstance(lora, dict):
                    continue
                inputs[f"lora_name_{i}"] = str(lora.get("name", ""))
                inputs[f"strength_{i}"] = float(lora.get("strength", 0.8))

        elif cls == "LoovieVideoSettings":
            aspect = body.get("aspect_ratio", "16:9")
            resolution = body.get("resolution", "720p")
            w, h = video_dimensions(aspect, resolution)
            inputs["width"] = int(body.get("width", w))
            inputs["height"] = int(body.get("height", h))

            with_audio = bool(body.get("with_audio", False))
            inputs["with_audio"] = with_audio

            fps = int(body.get("fps", inputs.get("fps", 24)))
            audio_fps = int(body.get("audio_fps", inputs.get("audio_fps", 25)))
            inputs["fps"] = fps
            inputs["audio_fps"] = audio_fps

            duration = body.get("duration")
            if duration is not None:
                duration_f = float(duration)
                frame_step = int(body.get("_loovie_frame_step", 0) or 0)
                frame_offset = int(body.get("_loovie_frame_offset", 0) or 0)
                if frame_step > 0:
                    target = round(duration_f * fps)
                    steps = max(0, round((target - frame_offset) / frame_step))
                    num_frames = frame_step * steps + frame_offset
                else:
                    num_frames = int(duration_f * fps) + 1
                inputs["num_frames"] = max(1, num_frames)
                # The LTX 2.5 graph concatenates a video and an audio latent
                # BEFORE sampling, so the audio latent must always be sized to
                # the clip even when the caller wants a silent render. The
                # `LoovieAudioGate` node drops the audio track after decode;
                # a zero-length latent here is what made silent renders fail
                # with a tensor-size mismatch at the sampler.
                inputs["audio_frames"] = max(1, int(duration_f * audio_fps))
            else:
                inputs["num_frames"] = int(body.get("num_frames", inputs.get("num_frames", 121)))
                inputs["audio_frames"] = int(
                    body.get("audio_frames", inputs.get("audio_frames", 97))
                )
            inputs["seed"] = int(body.get("seed", -1))

        elif cls == "ImageCrop":
            # Crop LTX's padded output back to the user-visible target.
            aspect = body.get("aspect_ratio", "16:9")
            resolution = body.get("resolution", "720p")
            gen_w, gen_h = video_dimensions(aspect, resolution)
            tgt_w, tgt_h = target_video_dimensions(aspect, resolution)
            inputs["width"] = max(1, int(tgt_w))
            inputs["height"] = max(1, int(tgt_h))
            inputs["x"] = max(0, (gen_w - tgt_w) // 2)
            inputs["y"] = max(0, (gen_h - tgt_h) // 2)


def _inject_music_inputs(workflow: dict[str, Any], body: dict[str, Any]) -> None:
    """Inject music-request values into `LoovieMusicInput` nodes.

    The YuE2 reference reads a style prompt and an optional lyric sheet.
    `instrumental` moves the Vocal notes into the Ins voice in the score;
    we pass it through so the graph decides how to realise it.
    """
    prompt = str(body.get("prompt", "") or "")
    lyrics = str(body.get("lyrics", "") or "")
    instrumental = bool(body.get("instrumental", False))

    for node in workflow.values():
        if node.get("class_type", "") != "LoovieMusicInput":
            continue
        inputs = node.setdefault("inputs", {})
        inputs["prompt"] = prompt
        inputs["lyrics"] = lyrics
        inputs["instrumental"] = instrumental
        inputs["seed"] = int(body.get("seed", -1))
        duration = body.get("duration")
        if duration is not None:
            inputs["duration"] = float(duration)


def _inject_sfx_inputs(workflow: dict[str, Any], body: dict[str, Any]) -> None:
    """Inject sound-effect request values into `LoovieSfxInput` nodes."""

    prompt = str(body.get("prompt", "") or "")
    negative_prompt = str(body.get("negative_prompt", "") or "")
    duration = float(body.get("duration", 5) or 5)

    for node in workflow.values():
        if node.get("class_type", "") != "LoovieSfxInput":
            continue
        inputs = node.setdefault("inputs", {})
        inputs["prompt"] = prompt
        inputs["negative_prompt"] = negative_prompt
        inputs["duration"] = duration
        inputs["seed"] = int(body.get("seed", -1))


def _resolve_music_workflow_name(body: dict[str, Any], default: str = "yue2-t2m-fast") -> str:
    """Pick the music workflow id to run.

    Honours an explicit `workflow` field, otherwise uses the caller's default
    (the registered `t2m` workflow, `yue2-t2m-fast`), matching the
    `(body, default)` signature `_setup_and_submit` uses for every modality.
    """
    explicit = str(body.get("workflow", "") or "").strip()
    if explicit:
        return explicit
    return (default or "").strip() or "yue2-t2m-fast"


_MODEL_ERROR_MESSAGES: dict[str, str] = {
    "MODEL_NOT_ENABLED": "That model is not enabled on this server.",
    "MODE_UNSUPPORTED": "That generation mode is not supported by this model.",
    "VARIANT_UNSUPPORTED": "That variant is not supported by this model.",
    "RESOLUTION_UNSUPPORTED": "That resolution is not supported by this model.",
    "ASPECT_RATIO_UNSUPPORTED": "That aspect ratio is not supported by this model.",
    "DURATION_UNSUPPORTED": "That duration is not supported by this model.",
    "AUDIO_UNSUPPORTED": "That model does not generate audio.",
    "REFERENCES_UNSUPPORTED": "That model cannot take those references.",
    "REFERENCES_REQUIRED": "This mode requires at least one reference image.",
    "START_FRAME_REQUIRED": "This mode requires a start frame.",
    "END_FRAME_REQUIRED": "This mode requires an end frame.",
}


class ModelRequestError(Exception):
    """A request that names a model/mode/variant this server cannot serve."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        self.message = message or _MODEL_ERROR_MESSAGES.get(
            code, "Request is not supported by this model."
        )
        super().__init__(self.message)


def _request_mode(body: dict[str, Any], modality: str) -> str:
    """Infer the generation mode from explicit fields, then from inputs."""

    explicit = str(body.get("mode", "") or "").strip()
    if explicit:
        return explicit
    if modality == "music":
        return "t2m"
    if modality == "sfx":
        return "t2s"
    if modality == "image":
        return "i2i" if (body.get("image_urls") or body.get("mask_url")) else "t2i"
    if (
        body.get("reference_image_urls")
        or body.get("reference_video_urls")
        or body.get("image_urls")
    ):
        return "ref2v"
    start = str(body.get("start_frame_url", "") or "").strip()
    end = str(body.get("end_frame_url", "") or "").strip()
    if start and end:
        return "fl2v"
    if start:
        return "i2v"
    return "t2v"


def _legacy_workflow(default: str, mode: str, variant: str) -> str:
    """The pre-v2 `mode + variant` mapping, kept for old app builds."""

    registered = set(WorkflowManager.get_instance().get_workflow_names())
    if mode in ("t2i", "i2i"):
        return "flux-2-klein" if "flux-2-klein" in registered else default.strip()
    suffix = "pro" if variant == "pro" else "fast"
    candidate = f"ltx23-{mode}-{suffix}"
    return candidate if candidate in registered else default.strip()


def _resolve_model_request(
    body: dict[str, Any], default: str, modality: str
) -> tuple[Any, Any, str, str | None]:
    """Resolve a request to (model spec, variant, workflow name, mode).

    An explicit `workflow` is an operator escape hatch and bypasses the
    registry. Otherwise `model` + `variant` are matched against the enabled
    models; omission falls back to the server's default model, which is what
    released app builds rely on.
    """

    explicit = str(body.get("workflow", "") or "").strip()
    if explicit:
        return None, None, explicit, None

    manager = WorkflowManager.get_instance()
    specs = available_models(manager.config, manager.get_workflow_names())
    default_spec = default_model(specs, manager.config, modality)
    mode = _request_mode(body, modality)

    try:
        spec, variant, workflow = resolve_workflow(
            specs,
            model_id=str(body.get("model", "") or ""),
            mode=mode,
            variant_id=str(body.get("variant", "") or ""),
            default_model_id=default_spec.id if default_spec is not None else None,
        )
    except LookupError as exc:
        raise ModelRequestError(str(exc) or "MODE_UNSUPPORTED") from None

    if spec is None or variant is None or workflow is None:
        return (
            None,
            None,
            _legacy_workflow(default, mode, str(body.get("variant", "") or "")),
            mode,
        )
    return spec, variant, workflow, mode


def _resolve_workflow_name(body: dict[str, Any], default: str, modality: str = "video") -> str:
    """Backwards-compatible helper: the workflow id for a request body."""

    return _resolve_model_request(body, default, modality)[2]


# ── model residency / switch policy ────────────────────────────────────────
#
# ComfyUI caches loaded models and evicts under memory pressure, not at a model
# switch. A BYO server that advertises several large models needs a deliberate
# switch: never unload after every generation, never unload while another task
# is running, and only unload when the new group does not fit alongside what is
# already resident.

_switch_lock = threading.Lock()
# group id -> estimated GB it occupies. A dict (not a set + running total) so
# there is no second piece of state to keep in sync.
_resident_groups: dict[str, float] = {}


def _model_gb(spec: Any) -> float:
    value = getattr(spec, "recommended_vram_gb", None) or getattr(spec, "vram_gb", None)
    return float(value or 0.0)


def _hardware_vram_gb(config: dict[str, Any]) -> float | None:
    models_config = shared_models_config(config)
    override = models_config.get("hardware")
    if isinstance(override, dict):
        value = override.get("vramGb")
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    detected = detect_hardware()
    if detected:
        value = detected.get("vramGb")
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _active_task_count() -> int:
    store = TaskStore.get_instance()
    counter = getattr(store, "count_active", None)
    return int(counter()) if callable(counter) else 0


def _unload_all_models() -> None:
    """Ask ComfyUI's model manager to release every resident group.

    Imported lazily: the extension is imported in CI and in tests without
    ComfyUI's heavy runtime. A missing module is a no-op, never an error.
    """

    try:
        import comfy.model_management as model_management

        model_management.unload_all_models()
        model_management.soft_empty_cache()
    except Exception as exc:  # pragma: no cover - depends on ComfyUI
        logger.debug("Model unload skipped: %s", exc)


def _ensure_resident_group(group: str, spec: Any) -> None:
    """Apply `models.switch_policy` before a new group is submitted."""

    if not group:
        return
    manager = WorkflowManager.get_instance()
    policy = str(shared_models_config(manager.config).get("switch_policy", "auto")).lower()
    if policy == "never":
        return

    with _switch_lock:
        if group in _resident_groups:
            return
        # Never evict a group another task is using.
        if _active_task_count() > 0:
            return

        needed = sum(_resident_groups.values()) + _model_gb(spec)
        total = _hardware_vram_gb(manager.config)
        fits = total is not None and total > 0 and needed <= total * 0.85

        if policy == "always" or not fits:
            _unload_all_models()
            _resident_groups.clear()
            logger.info("Model group switch: unloaded previous groups before %s", group)

        _resident_groups[group] = _model_gb(spec)


def _reset_resident_groups() -> None:
    """Test hook: forget what is resident."""

    with _switch_lock:
        _resident_groups.clear()


async def _setup_and_submit(
    request: web.Request,
    body: dict[str, Any],
    default_workflow: str,
    prompt_char_limit: int = 3000,
    resolve_name: Any = None,
    inject: Any = None,
    modality: str = "video",
) -> tuple[Any, web.Response | None]:
    """Validate the body, create the task, submit to ComfyUI, start monitor.

    `resolve_name` and `inject` default to the image/video mapping. The
    music path passes its own resolver + `_inject_music_inputs` so the
    prompt cap can differ from the video cap without a second copy of the
    whole submit flow.
    """

    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return None, web.json_response({"code": 400, "msg": "prompt is required"}, status=400)
    if len(prompt) > prompt_char_limit:
        return None, web.json_response(
            {"code": 400, "msg": f"prompt exceeds {prompt_char_limit} characters"},
            status=400,
        )

    inject = inject or _inject_inputs
    # Explicitly initialised: the `resolve_name` path leaves it unset, and
    # every later use is guarded by `mode is not None`. Keeps the local
    # definitely-assigned for static analyzers too.
    mode: str | None = None

    if resolve_name is not None:
        workflow_name = resolve_name(body, default_workflow)
        spec = None
        variant = None
    else:
        try:
            spec, variant, workflow_name, mode = _resolve_model_request(
                body, default_workflow, modality
            )
        except ModelRequestError as exc:
            return None, web.json_response(
                {"code": 400, "msg": exc.message, "fail_code": exc.code},
                status=400,
            )

    if not workflow_name:
        return None, web.json_response({"code": 400, "msg": "workflow is required"}, status=400)

    wf_manager = WorkflowManager.get_instance()
    if workflow_name not in wf_manager.get_workflow_names():
        available = ", ".join(wf_manager.get_workflow_names()) or "(none configured)"
        return None, web.json_response(
            {
                "code": 400,
                "msg": f"Unknown workflow: {workflow_name}. Available: {available}",
            },
            status=400,
        )

    if spec is not None and variant is not None and mode is not None:
        start = str(body.get("start_frame_url", "") or "").strip()
        end = str(body.get("end_frame_url", "") or "").strip()
        reference_count = len(body.get("reference_image_urls") or [])
        if modality == "image":
            reference_count = len(body.get("image_urls") or [])
        if modality == "video" and not body.get("resolution"):
            body["resolution"] = spec.resolutions[0] if spec.resolutions else "720p"
        if modality == "image":
            body["_loovie_image_resolution"] = image_canvas_resolution(
                spec, str(body.get("resolution", "") or "")
            )

        error_code = validate_request_values(
            spec,
            variant,
            mode=mode,
            resolution=str(body.get("resolution", "") or "") or None,
            aspect_ratio=str(body.get("aspect_ratio", "") or "") or None,
            duration=body.get("duration"),
            reference_count=reference_count,
            with_audio=bool(body.get("with_audio", False)),
            has_start_frame=bool(start),
            has_end_frame=bool(end),
        )
        if error_code:
            return None, web.json_response(
                {
                    "code": 400,
                    "msg": _MODEL_ERROR_MESSAGES.get(
                        error_code, "Request is not supported by this model."
                    ),
                    "fail_code": error_code,
                },
                status=400,
            )

        if len(prompt) > spec.prompt_char_limit:
            return None, web.json_response(
                {
                    "code": 400,
                    "msg": f"prompt exceeds {spec.prompt_char_limit} characters",
                    "fail_code": "PROMPT_TOO_LONG",
                },
                status=400,
            )

        # The manifest's audio policy is authoritative: `always` models cannot
        # be asked for a silent render, and `none` models ignore the flag.
        if spec.audio == "always":
            body["with_audio"] = True
        elif spec.audio == "none":
            body["with_audio"] = False

        if spec.frame_step > 0:
            body["_loovie_frame_step"] = spec.frame_step
            body["_loovie_frame_offset"] = spec.frame_offset

        _ensure_resident_group(residency_group(spec, mode), spec)

    store = TaskStore.get_instance()
    task = store.create_task(
        prompt=prompt,
        aspect_ratio=str(body.get("aspect_ratio", "1:1")),
        workflow_name=workflow_name,
    )

    try:
        workflow_json = wf_manager.load_workflow(workflow_name)
        inject(workflow_json, body)
        comfy_prompt_id = await wf_manager.submit_workflow(workflow_json)
    except FileNotFoundError as exc:
        store.update_task(
            task.task_id,
            state=TaskState.FAILED,
            fail_code="WORKFLOW_NOT_FOUND",
            error_message=str(exc),
        )
        return None, web.json_response({"code": 400, "msg": str(exc)}, status=400)
    except Exception as exc:
        err_msg = str(exc) or exc.__class__.__name__
        store.update_task(
            task.task_id,
            state=TaskState.FAILED,
            fail_code="SUBMISSION_ERROR",
            error_message=err_msg,
        )
        logger.exception("Submission failed for task=%s", task.task_id)
        return None, web.json_response(
            {
                "code": 503,
                "msg": f"Failed to queue generation: {err_msg[:500]}",
                "fail_code": "SUBMISSION_ERROR",
            },
            status=503,
        )

    store.update_task(
        task.task_id,
        comfy_prompt_id=comfy_prompt_id,
        state=TaskState.PROCESSING,
    )

    start_monitor(
        task_id=task.task_id,
        comfy_prompt_id=comfy_prompt_id,
        comfy_api_url=wf_manager.comfy_api_url,
        output_base_url=_resolve_output_base_url(request),
        max_wait_seconds=wf_manager.get_max_wait_seconds(workflow_name),
        poll_interval_seconds=wf_manager.poll_interval_seconds,
    )
    logger.info(
        "Task created: task_id=%s workflow=%s model=%s variant=%s prompt_id=%s",
        task.task_id,
        workflow_name,
        getattr(spec, "id", None),
        getattr(variant, "id", None),
        comfy_prompt_id,
    )
    return task, None


async def _create_task_handler(
    request: web.Request,
    default_workflow: str,
    body: dict[str, Any] | None = None,
    prompt_char_limit: int = 3000,
    resolve_name: Any = None,
    inject: Any = None,
    modality: str = "video",
) -> web.Response:
    auth_error = _check_auth(request)
    if auth_error:
        return auth_error

    if body is None:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"code": 400, "msg": "Invalid JSON body"}, status=400)

    logger.info(
        "Create task: path=%s body=%s",
        request.path,
        json.dumps(_log_safe_body(body), ensure_ascii=False),
    )

    task, error = await _setup_and_submit(
        request,
        body,
        default_workflow,
        prompt_char_limit=prompt_char_limit,
        resolve_name=resolve_name,
        inject=inject,
        modality=modality,
    )
    if error is not None:
        return error

    return web.json_response({"code": 200, "data": {"taskId": task.task_id}})


async def _task_status_handler(request: web.Request) -> web.Response:
    auth_error = _check_auth(request)
    if auth_error:
        return auth_error

    task_id = request.rel_url.query.get("taskId", "").strip()
    if not task_id:
        return web.json_response(
            {"code": 400, "msg": "taskId query parameter is required"},
            status=400,
        )

    task = TaskStore.get_instance().get_task(task_id)
    if task is None:
        return web.json_response({"code": 404, "msg": "Task not found"}, status=404)

    elapsed = round(time.time() - task.created_at, 1)
    data: dict[str, Any] = {
        "taskId": task.task_id,
        "state": task.state.value,
        "progress": task.progress,
        "elapsedSeconds": elapsed,
    }
    if task.progress_total > 0:
        data["step"] = task.progress_step
        data["totalSteps"] = task.progress_total
    if task.current_node:
        data["currentNode"] = task.current_node

    if task.state == TaskState.SUCCESS and task.result_url:
        data["resultJson"] = json.dumps({"resultUrls": [task.result_url]})
        if task.completed_at is not None:
            data["totalSeconds"] = round(task.completed_at - task.created_at, 1)
    elif task.state == TaskState.FAILED:
        data["failCode"] = task.fail_code
        data["failMsg"] = task.error_message
        if task.completed_at is not None:
            data["totalSeconds"] = round(task.completed_at - task.created_at, 1)

    return web.json_response({"code": 200, "data": data})


# --- routes -----------------------------------------------------------------


@PromptServer.instance.routes.post("/images/create")
async def create_image(request: web.Request) -> web.Response:
    """Start an image generation task."""
    return await _create_task_handler(request, default_workflow="flux-2-klein", modality="image")


@PromptServer.instance.routes.get("/images/status")
async def get_image_status(request: web.Request) -> web.Response:
    return await _task_status_handler(request)


@PromptServer.instance.routes.post("/videos/create")
async def create_video(request: web.Request) -> web.Response:
    """Start a single-shot video generation task."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return web.json_response({"code": 400, "msg": "Invalid JSON body"}, status=400)

    start_frame = (body.get("start_frame_url") or "").strip()
    end_frame = (body.get("end_frame_url") or "").strip()
    if end_frame and not start_frame:
        return web.json_response(
            {
                "code": 400,
                "msg": "end_frame_url requires start_frame_url",
                "fail_code": "START_FRAME_REQUIRED",
            },
            status=400,
        )
    references = body.get("reference_image_urls") or []
    if references and (start_frame or end_frame):
        return web.json_response(
            {
                "code": 400,
                "msg": "reference_image_urls cannot be combined with first/last frames",
                "fail_code": "REFERENCES_UNSUPPORTED",
            },
            status=400,
        )

    return await _create_task_handler(
        request,
        default_workflow="ltx23-t2v-fast",
        body=body,
        modality="video",
    )


@PromptServer.instance.routes.get("/videos/status")
async def get_video_status(request: web.Request) -> web.Response:
    return await _task_status_handler(request)


@PromptServer.instance.routes.post("/music/create")
async def create_music(request: web.Request) -> web.Response:
    """Start a text-to-music generation task.

    Required only when `/loovie/capabilities` advertises a `music` section.
    Accepts a style prompt plus an optional lyric sheet; returns a
    `taskId` the caller polls via `/music/status`.
    """
    return await _create_task_handler(
        request,
        default_workflow=_DEFAULT_MUSIC_WORKFLOW,
        prompt_char_limit=MUSIC_PROMPT_CHAR_LIMIT,
        inject=_inject_music_inputs,
        modality="music",
    )


@PromptServer.instance.routes.get("/music/status")
async def get_music_status(request: web.Request) -> web.Response:
    return await _task_status_handler(request)


@PromptServer.instance.routes.post("/sfx/create")
async def create_sfx(request: web.Request) -> web.Response:
    """Start a text-to-sound-effect task.

    Required only when `/loovie/capabilities` advertises an `sfx` section.
    Accepts a short sound description, an optional negative prompt and a
    duration in seconds; returns a `taskId` the caller polls via
    `/sfx/status`.
    """
    return await _create_task_handler(
        request,
        default_workflow=_DEFAULT_SFX_WORKFLOW,
        prompt_char_limit=SFX_PROMPT_CHAR_LIMIT,
        inject=_inject_sfx_inputs,
        modality="sfx",
    )


@PromptServer.instance.routes.get("/sfx/status")
async def get_sfx_status(request: web.Request) -> web.Response:
    return await _task_status_handler(request)


@PromptServer.instance.routes.post("/loovie/upload")
async def upload_reference(request: web.Request) -> web.Response:
    """Stage a reference file in ComfyUI's input directory.

    Accepts either `multipart/form-data` with a `file` field, or JSON
    `{filename, data_base64}`. Returns a `/view?...&type=input` URL the
    caller can pass back to `/images/create` or `/videos/create`.
    """
    auth_error = _check_auth(request)
    if auth_error:
        return auth_error

    import folder_paths

    input_dir = folder_paths.get_input_directory()
    os.makedirs(input_dir, exist_ok=True)

    filename: str | None = None
    data: bytes | None = None

    content_type = request.headers.get("Content-Type", "")
    try:
        if content_type.startswith("multipart/"):
            reader = await request.multipart()
            while True:
                part = await reader.next()
                if part is None:
                    break
                if not isinstance(part, BodyPartReader):
                    continue
                if part.name == "file":
                    filename = part.filename or f"upload_{int(time.time())}.png"
                    data = await part.read(decode=False)
                    break
        else:
            payload = await request.json()
            filename = payload.get("filename") or f"upload_{int(time.time())}.png"
            b64 = payload.get("data_base64", "")
            if not b64:
                return web.json_response(
                    {"code": 400, "msg": "data_base64 is required"}, status=400
                )
            data = base64.b64decode(b64)
    except Exception as exc:
        return web.json_response({"code": 400, "msg": f"Invalid upload: {exc}"}, status=400)

    if not data or not filename:
        return web.json_response({"code": 400, "msg": "No file data received"}, status=400)

    _, ext = os.path.splitext(filename)
    safe_ext = ext.lower() if ext.lower() in (".png", ".jpg", ".jpeg", ".webp") else ".png"
    safe_name = f"loovie_upload_{uuid.uuid4().hex[:12]}{safe_ext}"

    with open(os.path.join(input_dir, safe_name), "wb") as f:
        f.write(data)

    base_url = _resolve_output_base_url(request)
    url = f"{base_url}/view?filename={safe_name}&type=input&subfolder="
    logger.info("Uploaded reference: %s (%d bytes)", safe_name, len(data))

    return web.json_response(
        {
            "code": 200,
            "data": {"filename": safe_name, "url": url, "sizeBytes": len(data)},
        }
    )


# --- public probes ----------------------------------------------------------


@PromptServer.instance.routes.get("/loovie/health")
async def health(_request: web.Request) -> web.Response:
    """Liveness probe. ALWAYS public; never auth-checked."""
    return web.json_response(
        {
            "code": 200,
            "data": {
                "version": VERSION,
                "status": "ok",
                "phase": "ready",
                "detail": "",
            },
        }
    )


@PromptServer.instance.routes.get("/loovie/capabilities")
async def capabilities(_request: web.Request) -> web.Response:
    """Capability manifest probe. ALWAYS public; never auth-checked."""
    wf_manager = WorkflowManager.get_instance()
    manifest = build_capabilities_manifest(
        wf_manager.get_workflow_names(), VERSION, wf_manager.config
    )
    return web.json_response(manifest)


logger.info(
    "comfyui-loovie routes registered: "
    "POST /images/create, GET /images/status, "
    "POST /videos/create, GET /videos/status, "
    "POST /music/create, GET /music/status, "
    "POST /sfx/create, GET /sfx/status, "
    "POST /loovie/upload, "
    "GET /loovie/health, GET /loovie/capabilities"
)
