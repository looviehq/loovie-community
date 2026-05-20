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
import time
import uuid
from typing import Any

from aiohttp import web
from aiohttp.multipart import BodyPartReader
from server import PromptServer

from ..capabilities import build_capabilities_manifest
from ..helpers.aspect_ratio import target_video_dimensions, video_dimensions
from ..monitor import start_monitor
from ..task_store import TaskState, TaskStore
from ..workflow_manager import WorkflowManager

logger = logging.getLogger("comfyui_loovie.routes")

VERSION = "0.1.0"


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
    """Return a copy of `body` with prompts truncated and URLs redacted."""
    out = dict(body)
    prompt = out.get("prompt")
    if isinstance(prompt, str):
        out["prompt_length"] = len(prompt)
        if len(prompt) > 200:
            out["prompt"] = prompt[:200] + "..."
    if isinstance(out.get("image_urls"), list):
        out["image_urls"] = [_redact(u) for u in out["image_urls"]]
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
    if start_frame and not image_urls:
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
                inputs["num_frames"] = max(1, int(duration_f * fps) + 1)
                inputs["audio_frames"] = max(1, int(duration_f * audio_fps)) if with_audio else 0
            else:
                inputs["num_frames"] = int(body.get("num_frames", inputs.get("num_frames", 121)))
                inputs["audio_frames"] = (
                    int(body.get("audio_frames", inputs.get("audio_frames", 97)))
                    if with_audio
                    else 0
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


def _resolve_workflow_name(body: dict[str, Any], default: str) -> str:
    """Pick the workflow id to run based on the request body.

    Honours an explicit `workflow` field, otherwise maps `mode + variant`
    to a registered LTX 2.3 workflow, otherwise the image-mode mapping,
    otherwise the caller-supplied default.
    """
    explicit = str(body.get("workflow", "") or "").strip()
    if explicit:
        return explicit
    mode = str(body.get("mode", "") or "").strip()
    variant = str(body.get("variant", "") or "").strip()
    if mode and variant:
        return f"ltx23-{mode}-{variant}"
    if mode in ("t2i", "i2i"):
        # Both image modes route through flux-2-klein; t2i simply skips
        # the reference slots.
        return "flux-2-klein"
    return default.strip()


async def _setup_and_submit(
    request: web.Request,
    body: dict[str, Any],
    default_workflow: str,
) -> tuple[Any, web.Response | None]:
    """Validate the body, create the task, submit to ComfyUI, start monitor."""
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return None, web.json_response({"code": 400, "msg": "prompt is required"}, status=400)
    if len(prompt) > 3000:
        return None, web.json_response(
            {"code": 400, "msg": "prompt exceeds 3000 characters"},
            status=400,
        )

    workflow_name = _resolve_workflow_name(body, default_workflow)
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

    store = TaskStore.get_instance()
    task = store.create_task(
        prompt=prompt,
        aspect_ratio=str(body.get("aspect_ratio", "1:1")),
        workflow_name=workflow_name,
    )

    try:
        workflow_json = wf_manager.load_workflow(workflow_name)
        _inject_inputs(workflow_json, body)
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
        "Task created: task_id=%s workflow=%s prompt_id=%s",
        task.task_id,
        workflow_name,
        comfy_prompt_id,
    )
    return task, None


async def _create_task_handler(
    request: web.Request,
    default_workflow: str,
    body: dict[str, Any] | None = None,
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

    task, error = await _setup_and_submit(request, body, default_workflow)
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
    return await _create_task_handler(request, default_workflow="flux-2-klein")


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
            {"code": 400, "msg": "end_frame_url requires start_frame_url"},
            status=400,
        )

    if not body.get("workflow"):
        if start_frame and end_frame:
            body["workflow"] = "ltx23-fl2v-fast"
        elif start_frame:
            body["workflow"] = "ltx23-i2v-fast"
        else:
            body["workflow"] = "ltx23-t2v-fast"

    return await _create_task_handler(request, default_workflow="ltx23-t2v-fast", body=body)


@PromptServer.instance.routes.get("/videos/status")
async def get_video_status(request: web.Request) -> web.Response:
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
    manifest = build_capabilities_manifest(wf_manager.get_workflow_names(), VERSION)
    return web.json_response(manifest)


logger.info(
    "comfyui-loovie routes registered: "
    "POST /images/create, GET /images/status, "
    "POST /videos/create, GET /videos/status, "
    "POST /loovie/upload, "
    "GET /loovie/health, GET /loovie/capabilities"
)
