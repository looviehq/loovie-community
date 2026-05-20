"""Background monitor that watches a ComfyUI prompt to completion.

The monitor opens a WebSocket to ComfyUI's `/ws` for real-time progress
updates and falls back to polling `/history/<prompt_id>` if the WS path
is unavailable. The task store is updated as messages arrive; the route
layer reads it via `/images/status` and `/videos/status`.
"""

from __future__ import annotations

import contextlib
import json
import logging
import threading
import time
import urllib.request
import uuid

from .callback_sender import send_callback
from .task_store import TaskState, TaskStore

logger = logging.getLogger("comfyui_loovie.monitor")


def _extract_output_url(outputs: dict, base_url: str, key: str) -> str | None:
    """Find the first `{key}` entry in a ComfyUI history `outputs` dict."""
    for node_output in outputs.values():
        items = node_output.get(key, [])
        if not items:
            continue
        item = items[0]
        filename = item.get("filename", "")
        if not filename:
            continue
        subfolder = item.get("subfolder", "")
        item_type = item.get("type", "output")
        return f"{base_url}/view?filename={filename}&subfolder={subfolder}&type={item_type}"
    return None


def _poll_history(comfy_url: str, prompt_id: str) -> dict | None:
    """Fetch `/history/<prompt_id>`; return the entry or `None`."""
    url = f"{comfy_url}/history/{prompt_id}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if prompt_id in data:
            entry = data[prompt_id]
            return entry if isinstance(entry, dict) else None
    except Exception as exc:
        logger.debug("Poll error for prompt_id=%s: %s", prompt_id, exc)
    return None


def _extract_error(history_entry: dict) -> str | None:
    """Return a human-readable error string from a history entry, or None."""
    status = history_entry.get("status", {})
    if status.get("status_str") != "error":
        return None
    for msg_type, msg_data in status.get("messages", []):
        if msg_type == "execution_error":
            node_type = msg_data.get("node_type", "unknown")
            exception_message = msg_data.get("exception_message", "Unknown error")
            return f"{node_type}: {exception_message}"
    return "execution failed"


def start_monitor(
    *,
    task_id: str,
    comfy_prompt_id: str,
    comfy_api_url: str,
    output_base_url: str,
    max_wait_seconds: int,
    poll_interval_seconds: int,
) -> None:
    """Spawn a daemon thread that drives `task_id` to a terminal state."""
    thread = threading.Thread(
        target=_monitor_loop,
        kwargs={
            "task_id": task_id,
            "comfy_prompt_id": comfy_prompt_id,
            "comfy_api_url": comfy_api_url,
            "output_base_url": output_base_url,
            "max_wait_seconds": max_wait_seconds,
            "poll_interval_seconds": poll_interval_seconds,
        },
        daemon=True,
        name=f"loovie-monitor-{task_id}",
    )
    thread.start()
    logger.info("Monitor started: task_id=%s prompt_id=%s", task_id, comfy_prompt_id)


def _monitor_via_websocket(
    *,
    task_id: str,
    comfy_prompt_id: str,
    comfy_api_url: str,
    output_base_url: str,
    max_wait_seconds: int,
) -> bool:
    """Watch the ComfyUI WebSocket. Returns True when handled, False on bail-out."""
    try:
        import websocket  # type: ignore[import-not-found]
    except ImportError:
        logger.debug("websocket-client not installed; falling back to polling")
        return False

    store = TaskStore.get_instance()
    if store.get_task(task_id) is None:
        return False

    ws_url = comfy_api_url.replace("http://", "ws://").replace("https://", "wss://")
    client_id = uuid.uuid4().hex[:8]
    endpoint = f"{ws_url}/ws?clientId={client_id}"

    try:
        ws = websocket.create_connection(endpoint, timeout=max_wait_seconds)
    except Exception as exc:
        logger.debug("WebSocket connection failed: %s", exc)
        return False

    try:
        ws.settimeout(3)
        deadline = time.time() + max_wait_seconds
        last_history_check = 0.0

        while time.time() < deadline:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                now = time.time()
                if now - last_history_check >= 3:
                    last_history_check = now
                    entry = _poll_history(comfy_api_url, comfy_prompt_id)
                    if entry is not None:
                        _finalize_from_history(
                            task_id, comfy_prompt_id, comfy_api_url, output_base_url
                        )
                        return True
                continue
            except Exception:
                break

            if isinstance(raw, bytes):
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            data = msg.get("data", {}) or {}
            if data.get("prompt_id") != comfy_prompt_id:
                continue

            if msg_type == "progress":
                step = int(data.get("value", 0))
                total = int(data.get("max", 0))
                pct = int((step / total) * 100) if total > 0 else 0
                store.update_task(
                    task_id,
                    progress=pct,
                    progress_step=step,
                    progress_total=total,
                )
            elif msg_type == "executing":
                node = data.get("node")
                if node:
                    store.update_task(task_id, current_node=node)
                else:
                    store.update_task(task_id, progress=100, current_node=None)
                    _finalize_from_history(task_id, comfy_prompt_id, comfy_api_url, output_base_url)
                    return True
            elif msg_type == "execution_error":
                node_type = data.get("node_type", "unknown")
                exception_message = data.get("exception_message", "Unknown error")
                error = f"{node_type}: {exception_message}"
                _mark_failed(task_id, "EXECUTION_ERROR", error)
                return True
    finally:
        with contextlib.suppress(Exception):
            ws.close()

    return False


def _mark_failed(task_id: str, fail_code: str, message: str) -> None:
    """Record a terminal failure on the task and fire the optional callback."""
    store = TaskStore.get_instance()
    task = store.get_task(task_id)
    store.update_task(
        task_id,
        state=TaskState.FAILED,
        fail_code=fail_code,
        error_message=message,
        completed_at=time.time(),
        progress=100,
    )
    logger.error("Task %s failed: code=%s msg=%s", task_id, fail_code, message)
    if task is not None:
        send_callback(None, task_id, "failed", fail_code=fail_code, fail_msg=message)


def _finalize_from_history(
    task_id: str,
    comfy_prompt_id: str,
    comfy_api_url: str,
    output_base_url: str,
) -> None:
    """Resolve the task from `/history` once ComfyUI signals completion."""
    store = TaskStore.get_instance()
    if store.get_task(task_id) is None:
        return

    for _ in range(5):
        entry = _poll_history(comfy_api_url, comfy_prompt_id)
        if entry is None:
            time.sleep(1)
            continue

        error = _extract_error(entry)
        if error:
            _mark_failed(task_id, "EXECUTION_ERROR", error)
            return

        outputs = entry.get("outputs", {})
        url = _extract_output_url(outputs, output_base_url, "images")
        if url is None:
            url = _extract_output_url(outputs, output_base_url, "videos")
        if url:
            store.update_task(
                task_id,
                state=TaskState.SUCCESS,
                result_url=url,
                completed_at=time.time(),
                progress=100,
            )
            logger.info("Task %s succeeded: result_url=%s", task_id, url)
            send_callback(None, task_id, "success", result_url=url)
            return

        _mark_failed(
            task_id,
            "OUTPUT_MISSING",
            "Workflow completed but no image or video output was produced",
        )
        return

    _mark_failed(
        task_id,
        "HISTORY_MISSING",
        "Execution finished but history was not available",
    )


def _monitor_loop(
    *,
    task_id: str,
    comfy_prompt_id: str,
    comfy_api_url: str,
    output_base_url: str,
    max_wait_seconds: int,
    poll_interval_seconds: int,
) -> None:
    handled = _monitor_via_websocket(
        task_id=task_id,
        comfy_prompt_id=comfy_prompt_id,
        comfy_api_url=comfy_api_url,
        output_base_url=output_base_url,
        max_wait_seconds=max_wait_seconds,
    )
    if handled:
        return

    logger.info("Polling /history for task=%s", task_id)
    store = TaskStore.get_instance()
    deadline = time.time() + max_wait_seconds

    while time.time() < deadline:
        elapsed = max_wait_seconds - (deadline - time.time())
        store.update_task(
            task_id,
            progress=min(95, int((elapsed / max_wait_seconds) * 100)),
        )
        entry = _poll_history(comfy_api_url, comfy_prompt_id)
        if entry is not None:
            _finalize_from_history(task_id, comfy_prompt_id, comfy_api_url, output_base_url)
            return
        time.sleep(poll_interval_seconds)

    _mark_failed(
        task_id,
        "TIMEOUT",
        f"Generation timed out after {max_wait_seconds}s",
    )
