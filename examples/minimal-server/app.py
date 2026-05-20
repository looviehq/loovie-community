"""Framework-agnostic reference implementation of the Loovie BYO contract.

Implements every endpoint described in
``openapi/loovie-server.openapi.yaml`` with placeholder outputs so that:

* people writing their own BYO server in any stack can validate
  connectivity, auth, and capability flow before they wire up a real
  generation pipeline;
* CI can run a contract conformance test (schemathesis) against this
  module without provisioning a GPU.

This is *not* a generation server. ``POST /images/create`` and
``POST /videos/create`` return a task id whose later ``success`` state
points at a bundled 1x1 PNG / 1-byte MP4 ``data:`` URI. Real generation
servers replace the placeholder with their actual model output.

Run locally::

    pip install -e '.[dev]'
    export LOOVIE_API_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')"
    uvicorn app:app --host 0.0.0.0 --port 8188

Then verify::

    curl -s localhost:8188/loovie/health | python -m json.tool
    curl -s localhost:8188/loovie/capabilities | python -m json.tool
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# --- Constants ---------------------------------------------------------

VERSION = "0.1.0"
SCHEMA_VERSION = 1
PROMPT_CHAR_LIMIT = 3000
# Tiny, content-addressable placeholders that the device will still
# treat as valid PNG / MP4 (magic bytes are correct).
_PNG_1X1_TRANSPARENT = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
_MP4_MINIMAL = bytes.fromhex(
    "0000001c66747970697336" + "6d" + "00000200" + "697336" + "6d" + "6176633100000008"
)

# --- Auth --------------------------------------------------------------


def _is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost"}


async def require_bearer(request: Request) -> None:
    """Bearer-token enforcement. Localhost bypasses; otherwise the
    configured ``LOOVIE_API_TOKEN`` must match. **Fail-closed when no
    token is configured.**"""
    if _is_local_request(request):
        return
    token = os.environ.get("LOOVIE_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "msg": (
                    "Server has no LOOVIE_API_TOKEN configured; "
                    "remote requests are refused."
                ),
            },
        )
    header = request.headers.get("Authorization", "")
    if header != f"Bearer {token}":
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "Unauthorized"})


# --- Capability manifest ----------------------------------------------

CAPABILITIES: dict[str, Any] = {
    "schemaVersion": SCHEMA_VERSION,
    "version": VERSION,
    "images": {
        "capabilities": ["t2i", "i2i"],
        "referenceCount": 4,
        "resolution": ["720p", "1K", "2K"],
        "variants": ["fast", "pro"],
        "aspectRatios": ["auto", "1:1", "16:9", "9:16", "4:3"],
        "promptCharLimit": PROMPT_CHAR_LIMIT,
    },
    "ss_videos": {
        "capabilities": ["t2v", "i2v", "fl2v"],
        "referenceCount": 1,
        "resolution": ["720p", "1080p"],
        "variants": ["fast", "pro"],
        "aspectRatios": ["auto", "16:9", "9:16", "1:1"],
        "durations": [1, 2, 3, 4, 5, 6, 7, 8],
        "supportsAudio": True,
        "promptCharLimit": PROMPT_CHAR_LIMIT,
    },
}


# --- Task store -------------------------------------------------------


class _Task(BaseModel):
    task_id: str
    kind: Literal["image", "video"]
    state: Literal["pending", "processing", "success", "failed"] = "pending"
    created_at: float
    elapsed_seconds: float = 0.0
    progress: int = 0
    result_url: str | None = None
    fail_code: str | None = None
    fail_msg: str | None = None


TASKS: dict[str, _Task] = {}


def _make_task_id() -> str:
    return f"task_loovie_{uuid.uuid4().hex[:12]}"


def _advance(task: _Task) -> None:
    """Synthetic progression: pending -> processing -> success in a few
    quick steps, with progress bumping up. Real implementations replace
    this with their generation pipeline state."""
    age = time.monotonic() - task.created_at
    task.elapsed_seconds = age
    if task.state in {"success", "failed"}:
        return
    if age < 0.5:
        task.state = "pending"
        task.progress = max(task.progress, 5)
    elif age < 2.0:
        task.state = "processing"
        task.progress = min(95, int(age / 2.0 * 95))
    else:
        task.state = "success"
        task.progress = 100
        task.result_url = (
            "data:image/png;base64,"
            + base64.b64encode(_PNG_1X1_TRANSPARENT).decode("ascii")
            if task.kind == "image"
            else "data:video/mp4;base64,"
            + base64.b64encode(_MP4_MINIMAL).decode("ascii")
        )


# --- Lifespan ---------------------------------------------------------


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    # No background workers here; tasks advance lazily inside /status.
    yield


# --- FastAPI app ------------------------------------------------------

app = FastAPI(
    title="Loovie BYO Reference Server (minimal)",
    version=VERSION,
    description=(
        "Framework-agnostic reference for the Loovie BYO HTTP contract. "
        "Implements every endpoint with placeholder outputs."
    ),
    lifespan=_lifespan,
)


# --- Public probes ----------------------------------------------------


@app.get("/loovie/health", tags=["System"])
async def get_health() -> JSONResponse:
    return JSONResponse(
        {"code": 200, "data": {"version": VERSION, "status": "ok", "phase": "ready", "detail": ""}}
    )


@app.get("/loovie/capabilities", tags=["System"])
async def get_capabilities() -> JSONResponse:
    return JSONResponse({**CAPABILITIES})


# --- Image ------------------------------------------------------------


class ImageCreateRequest(BaseModel):
    prompt: str = Field(..., max_length=PROMPT_CHAR_LIMIT)
    mode: Literal["t2i", "i2i"] | None = None
    variant: Literal["fast", "pro"] | None = None
    aspect_ratio: Literal["auto", "1:1", "16:9", "9:16", "4:3"] | None = None
    image_urls: list[str] | None = None
    mask_url: str | None = None
    seed: int = -1
    negative_prompt: str | None = None
    workflow: str | None = None
    loras: list[dict[str, Any]] | None = None


@app.post("/images/create", tags=["Image"], dependencies=[Depends(require_bearer)])
async def create_image(body: ImageCreateRequest) -> JSONResponse:
    task_id = _make_task_id()
    TASKS[task_id] = _Task(task_id=task_id, kind="image", created_at=time.monotonic())
    return JSONResponse({"code": 200, "data": {"taskId": task_id}})


@app.get("/images/status", tags=["Image"], dependencies=[Depends(require_bearer)])
async def get_image_status(taskId: str) -> JSONResponse:  # noqa: N803
    task = TASKS.get(taskId)
    if not task or task.kind != "image":
        return JSONResponse({"code": 404, "msg": "Task not found"}, status_code=404)
    _advance(task)
    return JSONResponse({"code": 200, "data": _task_to_payload(task)})


# --- Video ------------------------------------------------------------


class VideoCreateRequest(BaseModel):
    prompt: str = Field(..., max_length=PROMPT_CHAR_LIMIT)
    mode: Literal["t2v", "i2v", "fl2v"] | None = None
    variant: Literal["fast", "pro"] | None = None
    aspect_ratio: Literal["auto", "16:9", "9:16", "1:1"] | None = None
    resolution: Literal["720p", "1080p"] | None = None
    duration: int | None = Field(default=None, ge=1)
    start_frame_url: str | None = None
    end_frame_url: str | None = None
    with_audio: bool | None = None
    seed: int = -1


@app.post("/videos/create", tags=["Video"], dependencies=[Depends(require_bearer)])
async def create_video(body: VideoCreateRequest) -> JSONResponse:
    if body.end_frame_url and not body.start_frame_url:
        return JSONResponse(
            {"code": 400, "msg": "end_frame_url requires start_frame_url"}, status_code=400
        )
    task_id = _make_task_id()
    TASKS[task_id] = _Task(task_id=task_id, kind="video", created_at=time.monotonic())
    return JSONResponse({"code": 200, "data": {"taskId": task_id}})


@app.get("/videos/status", tags=["Video"], dependencies=[Depends(require_bearer)])
async def get_video_status(taskId: str) -> JSONResponse:  # noqa: N803
    task = TASKS.get(taskId)
    if not task or task.kind != "video":
        return JSONResponse({"code": 404, "msg": "Task not found"}, status_code=404)
    _advance(task)
    return JSONResponse({"code": 200, "data": _task_to_payload(task)})


# --- Upload -----------------------------------------------------------


@app.post("/loovie/upload", tags=["Upload"], dependencies=[Depends(require_bearer)])
async def upload(
    request: Request,
    file: UploadFile | None = File(None),
    filename: str | None = Form(None),
    data_base64: str | None = Form(None),
) -> JSONResponse:
    if file is not None:
        contents = await file.read()
        stored_name = file.filename or "upload"
    elif filename and data_base64:
        try:
            contents = base64.b64decode(data_base64, validate=True)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=400, detail={"code": 400, "msg": f"invalid base64: {exc}"}
            ) from exc
        stored_name = filename
    else:
        body = await request.body()
        try:
            data = json.loads(body)
            stored_name = data["filename"]
            contents = base64.b64decode(data["data_base64"], validate=True)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": 400, "msg": "expected multipart 'file' or JSON {filename,data_base64}"},
            ) from exc

    size = len(contents)
    # Reference servers would persist to an input store and mint a URL
    # the workflow can fetch. We return a synthetic identifier that is
    # safely opaque to the caller.
    handle = f"loovie_upload_{secrets.token_hex(6)}_{stored_name}"
    url = f"/view?filename={handle}&type=input"
    return JSONResponse(
        {"code": 200, "data": {"filename": handle, "url": url, "sizeBytes": size}}
    )


# --- Helpers ----------------------------------------------------------


def _task_to_payload(task: _Task) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "taskId": task.task_id,
        "state": task.state,
        "progress": task.progress,
        "elapsedSeconds": round(task.elapsed_seconds, 3),
    }
    if task.state == "success":
        payload["resultJson"] = json.dumps({"resultUrls": [task.result_url]})
        payload["totalSeconds"] = round(task.elapsed_seconds, 3)
    elif task.state == "failed":
        payload["failCode"] = task.fail_code or "EXECUTION_ERROR"
        payload["failMsg"] = task.fail_msg or "unknown error"
    return payload
