"""Direct server delivery: upload + terminal callback on the user's behalf.

The delivery path is opportunistic: it must never raise, never log the token,
and must leave the task's delivery state accurate enough for the device to
decide whether it still has to download the result.
"""

from __future__ import annotations

from typing import Any

import pytest

from comfyui_loovie import delivery
from comfyui_loovie.capabilities import build_capabilities_manifest
from comfyui_loovie.task_store import TaskStore

ALL_WORKFLOWS = ["flux-2-klein", "yue2-t2m-fast"]


def _task_with_delivery(kind: str = "music") -> str:
    store = TaskStore.get_instance()
    task = store.create_task(prompt="x", aspect_ratio="1:1", workflow_name="w")
    store.update_task(
        task.task_id,
        delivery={
            "kind": kind,
            "uploadUrlEndpoint": "https://api.loovie.app/v1/byo/jobs/job_1/upload-url",
            "completeUrl": f"https://api.loovie.app/v1/byo/{kind}-jobs/job_1/complete",
            "failUrl": f"https://api.loovie.app/v1/byo/{kind}-jobs/job_1/fail",
            "progressUrl": "",
            "token": "secret-token",
            "expiresAt": "2030-01-01T00:00:00.000Z",
        },
        delivery_upload="pending",
        delivery_callback="pending",
    )
    return task.task_id


def test_capabilities_advertise_direct_delivery_for_all_kinds() -> None:
    manifest = build_capabilities_manifest(ALL_WORKFLOWS, "test")
    assert manifest["delivery"] == {
        "directUpload": True,
        "kinds": ["image", "video", "music", "sfx"],
    }


@pytest.mark.parametrize(
    ("url", "kind", "expected"),
    [
        ("http://comfy/view?filename=song.mp3", "music", "audio/mpeg"),
        ("http://comfy/view?filename=song.flac", "music", "audio/flac"),
        ("http://comfy/view?filename=still.png", "image", "image/png"),
        ("http://comfy/view?filename=clip.mp4", "video", "video/mp4"),
        # Unknown extension falls back to the kind's default.
        ("http://comfy/view?filename=result", "sfx", "audio/mpeg"),
    ],
)
def test_content_type_for(url: str, kind: str, expected: str) -> None:
    assert delivery._content_type_for(url, kind) == expected


def test_failure_delivery_posts_the_fail_callback_without_uploading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _task_with_delivery()
    posted: list[tuple[str, dict[str, Any]]] = []

    def fake_post(url: str, _token: str, payload: dict[str, Any]) -> dict[str, Any]:
        posted.append((url, payload))
        return {}

    monkeypatch.setattr(delivery, "_post_json", fake_post)
    delivery._run(task_id, None, "EXECUTION_ERROR", "boom")

    task = TaskStore.get_instance().get_task(task_id)
    assert task is not None
    assert task.delivery_upload == "failed"
    assert task.delivery_callback == "ok"
    assert posted == [
        (
            "https://api.loovie.app/v1/byo/music-jobs/job_1/fail",
            {"failCode": "EXECUTION_ERROR", "failMsg": "boom"},
        )
    ]


def test_success_delivery_uploads_then_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _task_with_delivery()
    completed: list[str] = []

    monkeypatch.setattr(delivery, "_upload", lambda *_a, **_k: "temp/user/byo/job_1/out.mp3")

    def fake_terminal(*_a: Any, **kwargs: Any) -> bool:
        completed.append(str(kwargs.get("storage_key")))
        return True

    monkeypatch.setattr(delivery, "_post_terminal", fake_terminal)
    delivery._run(task_id, "http://comfy/view?filename=song.mp3", None, None)

    task = TaskStore.get_instance().get_task(task_id)
    assert task is not None
    assert task.delivery_upload == "ok"
    assert task.delivery_callback == "ok"
    assert task.delivery_storage_key == "temp/user/byo/job_1/out.mp3"
    assert completed == ["temp/user/byo/job_1/out.mp3"]


def test_success_delivery_marks_upload_failed_and_leaves_callback_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _task_with_delivery()
    monkeypatch.setattr(delivery, "_upload", lambda *_a, **_k: None)

    delivery._run(task_id, "http://comfy/view?filename=song.mp3", None, None)

    task = TaskStore.get_instance().get_task(task_id)
    assert task is not None
    assert task.delivery_upload == "failed"
    # Never reported a callback for a result that was not uploaded.
    assert task.delivery_callback == "pending"


def test_success_delivery_marks_callback_failed_after_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _task_with_delivery()
    monkeypatch.setattr(delivery, "_upload", lambda *_a, **_k: "key")
    monkeypatch.setattr(delivery, "_post_terminal", lambda *_a, **_k: False)

    delivery._run(task_id, "http://comfy/view?filename=song.mp3", None, None)

    task = TaskStore.get_instance().get_task(task_id)
    assert task is not None
    assert task.delivery_upload == "ok"
    assert task.delivery_callback == "failed"
    assert task.delivery_storage_key == "key"


def test_start_delivery_is_a_noop_without_a_delivery_block() -> None:
    store = TaskStore.get_instance()
    task = store.create_task(prompt="x", aspect_ratio="1:1", workflow_name="w")

    delivery.start_success_delivery(task.task_id, "http://comfy/view?filename=a.png")
    delivery.start_failure_delivery(task.task_id, "X", "y")

    assert task.delivery_upload == "none"
    assert task.delivery_callback == "none"
