"""Optional fire-and-forget completion callback.

The Loovie mobile app does NOT require this; it polls
`/{images,videos}/status` to discover task completion. The callback is
provided so operators can wire the server up to additional automation
(e.g. a webhook in their own pipeline) without modifying the monitor.

If `callback_url` is `None` or empty, all calls are no-ops.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request

logger = logging.getLogger("comfyui_loovie.callback_sender")

_BACKOFF_SECONDS: tuple[int, ...] = (2, 10, 30, 90, 300)
_RETRYABLE_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})


def send_callback(
    callback_url: str | None,
    task_id: str,
    state: str,
    *,
    result_url: str | None = None,
    fail_code: str | None = None,
    fail_msg: str | None = None,
) -> None:
    """Schedule a non-blocking, retrying POST.

    No-op when `callback_url` is empty; this lets callers fire the
    callback unconditionally without checking the task record first.
    """
    if not callback_url:
        return

    if state == "success" and result_url:
        payload: dict[str, object] = {
            "data": {
                "taskId": task_id,
                "state": "success",
                "resultJson": json.dumps({"resultUrls": [result_url]}),
            }
        }
    elif state == "failed":
        payload = {
            "data": {
                "taskId": task_id,
                "state": "failed",
                "failCode": fail_code or "GENERATION_ERROR",
                "failMsg": fail_msg or "Unknown error",
            }
        }
    else:
        logger.warning(
            "send_callback: unexpected state=%s for task=%s", state, task_id
        )
        return

    thread = threading.Thread(
        target=_deliver_with_retries,
        args=(callback_url, task_id, state, payload),
        daemon=True,
        name=f"loovie-callback-{task_id}",
    )
    thread.start()


def _deliver_with_retries(
    callback_url: str,
    task_id: str,
    state: str,
    payload: dict[str, object],
) -> None:
    body = json.dumps(payload).encode("utf-8")
    target = callback_url.split("?", 1)[0]
    logger.info(
        "Sending callback: task=%s state=%s url=%s", task_id, state, target
    )

    max_attempts = 1 + len(_BACKOFF_SECONDS)
    for attempt in range(1, max_attempts + 1):
        retryable, summary = _attempt(callback_url, task_id, attempt, body)
        if summary is None:
            return
        if not retryable or attempt == max_attempts:
            logger.error(
                "Callback gave up: task=%s attempt=%d/%d %s",
                task_id, attempt, max_attempts, summary,
            )
            return
        delay = _BACKOFF_SECONDS[attempt - 1]
        logger.warning(
            "Callback attempt %d/%d failed (task=%s): %s; retrying in %ds",
            attempt, max_attempts, task_id, summary, delay,
        )
        time.sleep(delay)


def _attempt(
    callback_url: str,
    task_id: str,
    attempt: int,
    body: bytes,
) -> tuple[bool, str | None]:
    """Single POST attempt. Returns (retryable, error_summary_or_None)."""
    req = urllib.request.Request(
        callback_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.info(
                "Callback delivered: task=%s status=%d attempt=%d",
                task_id, resp.status, attempt,
            )
            return True, None
    except urllib.error.HTTPError as e:
        return e.code in _RETRYABLE_HTTP_STATUS, f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return True, f"network error: {e.reason}"
    except (TimeoutError, OSError) as e:
        return True, f"socket error: {e}"
    except Exception as e:
        return False, f"unexpected error: {e}"
