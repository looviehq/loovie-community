"""Direct server delivery: push a finished render back to Loovie.

When a create request carries a `delivery` block, this server can upload the
result to R2 itself and post the terminal callback with the job-scoped token,
so the job completes even when the phone is closed. The wire contract is the
same one the device uses; only the credential differs.

This is strictly opportunistic. Every failure is recorded on the task so
`/status` can report it, and the device falls back to its own download on the
next drain. A delivery failure never fails a render.

No token is ever logged: only the URL with its query stripped.
"""

from __future__ import annotations

import contextlib
import json
import logging
import mimetypes
import os
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .task_store import TaskStore

logger = logging.getLogger("comfyui_loovie.delivery")

_CALLBACK_BACKOFF_SECONDS: tuple[int, ...] = (2, 10, 30)
_RETRYABLE_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})
_DOWNLOAD_TIMEOUT_SECONDS = 300
_UPLOAD_TIMEOUT_SECONDS = 1800
_CALLBACK_TIMEOUT_SECONDS = 30

_DEFAULT_CONTENT_TYPE = {
    "image": "image/png",
    "video": "video/mp4",
    "music": "audio/mpeg",
    "sfx": "audio/mpeg",
}

# Explicit map for the formats the Loovie upload allowlist accepts. `mimetypes`
# is platform-dependent (for example `.flac` resolves to `audio/x-flac` on some
# systems), and the API rejects anything outside its allowlist, so the extension
# must decide before the platform guess does.
_CONTENT_TYPE_BY_EXTENSION = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mov": "video/quicktime",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
}

# Complete-callback body per kind. Mirrors the device's, so the API's existing
# terminal paths need no special case.
_STORAGE_KEY_FIELD = {
    "image": "imageStorageKey",
    "video": "videoStorageKey",
    "music": "audioStorageKey",
    "sfx": None,
}


def _target(url: str) -> str:
    """The URL without its query, safe to log."""
    return url.split("?", 1)[0]


def _result_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    name = (query.get("filename") or [""])[0]
    if not name:
        name = os.path.basename(parsed.path)
    return name or "result"


def _content_type_for(url: str, kind: str) -> str:
    filename = _result_filename(url)
    extension = os.path.splitext(filename)[1].lower().lstrip(".")
    mapped = _CONTENT_TYPE_BY_EXTENSION.get(extension)
    if mapped:
        return mapped
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    return _DEFAULT_CONTENT_TYPE.get(kind, "application/octet-stream")


def _post_json(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(request, timeout=_CALLBACK_TIMEOUT_SECONDS) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}


def start_success_delivery(task_id: str, result_url: str) -> None:
    """Upload + complete in the background. No-op when no delivery was asked."""
    task = TaskStore.get_instance().get_task(task_id)
    if task is None or not isinstance(task.delivery, dict):
        return
    threading.Thread(
        target=_run,
        args=(task_id, result_url, None, None),
        daemon=True,
        name=f"loovie-delivery-{task_id}",
    ).start()


def start_failure_delivery(task_id: str, fail_code: str | None, fail_msg: str | None) -> None:
    task = TaskStore.get_instance().get_task(task_id)
    if task is None or not isinstance(task.delivery, dict):
        return
    threading.Thread(
        target=_run,
        args=(task_id, None, fail_code or "GENERATION_ERROR", fail_msg or ""),
        daemon=True,
        name=f"loovie-delivery-{task_id}",
    ).start()


def _run(
    task_id: str,
    result_url: str | None,
    fail_code: str | None,
    fail_msg: str | None,
) -> None:
    store = TaskStore.get_instance()
    task = store.get_task(task_id)
    if task is None:
        return
    delivery_block = task.delivery
    if not isinstance(delivery_block, dict):
        return
    delivery: dict[str, Any] = delivery_block
    kind = str(delivery.get("kind") or "")

    if result_url is None:
        # Failure delivery: nothing to upload, just report it.
        store.update_task(task_id, delivery_upload="failed")
        ok = _post_terminal(delivery, task_id, failed=True, fail_code=fail_code, fail_msg=fail_msg)
        store.update_task(task_id, delivery_callback="ok" if ok else "failed")
        return

    if kind not in _DEFAULT_CONTENT_TYPE:
        logger.warning("Delivery: unknown kind=%s task=%s", kind, task_id)
        store.update_task(task_id, delivery_upload="failed")
        return

    store.update_task(task_id, delivery_upload="uploading")
    storage_key = _upload(task_id, kind, result_url, delivery)
    if storage_key is None:
        store.update_task(task_id, delivery_upload="failed")
        return
    store.update_task(
        task_id,
        delivery_upload="ok",
        delivery_storage_key=storage_key,
    )
    ok = _post_terminal(
        delivery,
        task_id,
        failed=False,
        storage_key=storage_key,
        kind=kind,
    )
    store.update_task(task_id, delivery_callback="ok" if ok else "failed")


def _upload(
    task_id: str,
    kind: str,
    result_url: str,
    delivery: dict[str, Any],
) -> str | None:
    endpoint = str(delivery.get("uploadUrlEndpoint") or "")
    token = str(delivery.get("token") or "")
    if not endpoint or not token:
        return None

    temp_path = None
    try:
        # Download first so the presign request carries the real size and a
        # content type inferred from the actual file name.
        suffix = os.path.splitext(_result_filename(result_url))[1] or ""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name
        with (
            urllib.request.urlopen(result_url, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as source,
            open(temp_path, "wb") as sink,
        ):
            shutil.copyfileobj(source, sink)
        size = os.path.getsize(temp_path)
        content_type = _content_type_for(result_url, kind)

        granted = _post_json(
            endpoint,
            token,
            {"contentType": content_type, "sizeBytes": size},
        )
        data = granted.get("data") if isinstance(granted, dict) else None
        if not isinstance(data, dict):
            logger.warning(
                "Delivery: presign refused task=%s body=%s",
                task_id,
                granted.get("error") if isinstance(granted, dict) else granted,
            )
            return None
        upload_url = str(data.get("uploadUrl") or "")
        storage_key = str(data.get("storageKey") or "")
        raw_headers = data.get("headers")
        headers: dict[Any, Any] = raw_headers if isinstance(raw_headers, dict) else {}
        if not upload_url or not storage_key:
            return None

        with open(temp_path, "rb") as handle:
            request = urllib.request.Request(
                upload_url,
                data=handle,
                method="PUT",
                headers={
                    **{str(k): str(v) for k, v in headers.items()},
                    "Content-Length": str(size),
                },
            )
            with urllib.request.urlopen(request, timeout=_UPLOAD_TIMEOUT_SECONDS) as resp:
                resp.read()
        logger.info(
            "Delivery: uploaded task=%s kind=%s bytes=%d",
            task_id,
            kind,
            size,
        )
        return storage_key
    except urllib.error.HTTPError as exc:
        logger.warning("Delivery: upload failed task=%s status=%d", task_id, exc.code)
        return None
    except Exception as exc:  # delivery must never raise
        logger.warning("Delivery: upload error task=%s err=%s", task_id, exc)
        return None
    finally:
        if temp_path:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)


def _post_terminal(
    delivery: dict[str, Any],
    task_id: str,
    *,
    failed: bool,
    storage_key: str | None = None,
    kind: str = "",
    fail_code: str | None = None,
    fail_msg: str | None = None,
) -> bool:
    url = str(delivery.get("failUrl" if failed else "completeUrl") or "")
    token = str(delivery.get("token") or "")
    if not url or not token:
        return False

    if failed:
        payload: dict[str, Any] = {
            "failCode": fail_code or "GENERATION_ERROR",
            "failMsg": (fail_msg or "")[:2048],
        }
    else:
        field = _STORAGE_KEY_FIELD.get(kind)
        payload = {field: storage_key} if field and storage_key else {}

    max_attempts = 1 + len(_CALLBACK_BACKOFF_SECONDS)
    for attempt in range(1, max_attempts + 1):
        try:
            _post_json(url, token, payload)
            logger.info(
                "Delivery: callback delivered task=%s url=%s attempt=%d",
                task_id,
                _target(url),
                attempt,
            )
            return True
        except urllib.error.HTTPError as exc:
            retryable = exc.code in _RETRYABLE_HTTP_STATUS
            logger.warning(
                "Delivery: callback HTTP %d task=%s attempt=%d",
                exc.code,
                task_id,
                attempt,
            )
            if not retryable or attempt == max_attempts:
                return False
        except Exception as exc:
            logger.warning(
                "Delivery: callback error task=%s attempt=%d err=%s",
                task_id,
                attempt,
                exc,
            )
            if attempt == max_attempts:
                return False
        time.sleep(_CALLBACK_BACKOFF_SECONDS[attempt - 1])
    return False
