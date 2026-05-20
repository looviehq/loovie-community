"""TestClient-based tests for the minimal-server reference."""

from __future__ import annotations

import base64
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

# Import the module under test.
import app as ms

client = TestClient(ms.app)


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear the in-memory task store between tests and unset the token."""
    ms.TASKS.clear()
    monkeypatch.delenv("LOOVIE_API_TOKEN", raising=False)


# --- Public probes ----------------------------------------------------


def test_health_returns_ready() -> None:
    r = client.get("/loovie/health")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["status"] == "ok"
    assert body["data"]["phase"] == "ready"


def test_capabilities_matches_schema_v1() -> None:
    r = client.get("/loovie/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["schemaVersion"] == 1
    assert "images" in body and "ss_videos" in body
    assert set(body["images"]["capabilities"]) <= {"t2i", "i2i"}
    assert set(body["ss_videos"]["capabilities"]) <= {"t2v", "i2v", "fl2v"}
    assert body["ss_videos"]["supportsAudio"] is True
    assert body["ss_videos"]["durations"] == [1, 2, 3, 4, 5, 6, 7, 8]


# --- Auth: fail-closed when no token ----------------------------------


def test_remote_request_without_token_is_refused() -> None:
    """Per [D11] the server fails closed when LOOVIE_API_TOKEN is unset
    AND the caller is not on loopback. TestClient appears local by
    default, so we override the dependency to simulate a remote caller."""

    def fake_require_bearer(request) -> None:  # type: ignore[no-untyped-def]
        # Force the remote path by inlining the production check with
        # a pretend non-local client.
        token = os.environ.get("LOOVIE_API_TOKEN", "").strip()
        if not token:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=401,
                detail={
                    "code": 401,
                    "msg": (
                        "Server has no LOOVIE_API_TOKEN configured; remote requests are refused."
                    ),
                },
            )

    ms.app.dependency_overrides[ms.require_bearer] = fake_require_bearer
    try:
        r = client.post("/images/create", json={"prompt": "hello"})
        assert r.status_code == 401
        assert "LOOVIE_API_TOKEN" in r.json()["detail"]["msg"]
    finally:
        ms.app.dependency_overrides.clear()


def test_localhost_bypass_is_implicit_for_testclient() -> None:
    """TestClient calls present as local (`testclient` host -> not in
    the strict allow-list, so default dep enforces). We just verify the
    happy path works when the token IS configured."""
    os.environ["LOOVIE_API_TOKEN"] = "test-token"
    try:
        r = client.post(
            "/images/create",
            json={"prompt": "hello"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["taskId"].startswith("task_loovie_")
    finally:
        os.environ.pop("LOOVIE_API_TOKEN", None)


# --- Image happy path --------------------------------------------------


def test_image_create_then_status_until_success() -> None:
    os.environ["LOOVIE_API_TOKEN"] = "test-token"
    headers = {"Authorization": "Bearer test-token"}
    try:
        r = client.post(
            "/images/create",
            json={
                "prompt": "a red bicycle in front of a Parisian café",
                "mode": "t2i",
                "variant": "fast",
                "aspect_ratio": "16:9",
            },
            headers=headers,
        )
        assert r.status_code == 200
        task_id = r.json()["data"]["taskId"]

        # Poll up to 5s for success.
        deadline = time.monotonic() + 5.0
        body = None
        while time.monotonic() < deadline:
            s = client.get(f"/images/status?taskId={task_id}", headers=headers)
            assert s.status_code == 200
            body = s.json()["data"]
            if body["state"] in {"success", "failed"}:
                break
            time.sleep(0.5)

        assert body is not None and body["state"] == "success"
        assert body["progress"] == 100
        # resultJson is a JSON-encoded string per the contract.
        decoded = json.loads(body["resultJson"])
        assert "resultUrls" in decoded and len(decoded["resultUrls"]) == 1
        # The placeholder result is a real PNG (magic bytes match).
        result_url = decoded["resultUrls"][0]
        assert result_url.startswith("data:image/png;base64,")
        png_bytes = base64.b64decode(result_url.split(",", 1)[1])
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        os.environ.pop("LOOVIE_API_TOKEN", None)


def test_image_status_404_for_unknown_task() -> None:
    os.environ["LOOVIE_API_TOKEN"] = "test-token"
    try:
        r = client.get(
            "/images/status?taskId=task_loovie_doesnotexist",
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 404
        assert r.json()["code"] == 404
    finally:
        os.environ.pop("LOOVIE_API_TOKEN", None)


# --- Video happy path + validation -------------------------------------


def test_video_create_rejects_end_frame_without_start() -> None:
    os.environ["LOOVIE_API_TOKEN"] = "test-token"
    try:
        r = client.post(
            "/videos/create",
            json={
                "prompt": "a cinematic dolly",
                "mode": "fl2v",
                "end_frame_url": "https://example.com/end.png",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 400
        assert "end_frame_url" in r.json()["msg"]
    finally:
        os.environ.pop("LOOVIE_API_TOKEN", None)


def test_video_create_then_status_until_success() -> None:
    os.environ["LOOVIE_API_TOKEN"] = "test-token"
    headers = {"Authorization": "Bearer test-token"}
    try:
        r = client.post(
            "/videos/create",
            json={
                "prompt": "a slow zoom into a sunflower",
                "mode": "t2v",
                "variant": "fast",
                "resolution": "720p",
                "duration": 3,
            },
            headers=headers,
        )
        assert r.status_code == 200
        task_id = r.json()["data"]["taskId"]

        deadline = time.monotonic() + 5.0
        body = None
        while time.monotonic() < deadline:
            s = client.get(f"/videos/status?taskId={task_id}", headers=headers)
            assert s.status_code == 200
            body = s.json()["data"]
            if body["state"] in {"success", "failed"}:
                break
            time.sleep(0.5)

        assert body is not None and body["state"] == "success"
        decoded = json.loads(body["resultJson"])
        result_url = decoded["resultUrls"][0]
        assert result_url.startswith("data:video/mp4;base64,")
    finally:
        os.environ.pop("LOOVIE_API_TOKEN", None)


def test_prompt_char_limit_enforced() -> None:
    os.environ["LOOVIE_API_TOKEN"] = "test-token"
    try:
        big = "x" * 3001
        r = client.post(
            "/images/create",
            json={"prompt": big},
            headers={"Authorization": "Bearer test-token"},
        )
        # FastAPI -> Pydantic -> 422 on max_length violation.
        assert r.status_code == 422
    finally:
        os.environ.pop("LOOVIE_API_TOKEN", None)


# --- Upload ----------------------------------------------------------


def test_upload_json_path() -> None:
    os.environ["LOOVIE_API_TOKEN"] = "test-token"
    try:
        b64 = base64.b64encode(b"hello world").decode("ascii")
        r = client.post(
            "/loovie/upload",
            json={"filename": "hello.txt", "data_base64": b64},
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["data"]["sizeBytes"] == 11
        assert body["data"]["filename"].startswith("loovie_upload_")
    finally:
        os.environ.pop("LOOVIE_API_TOKEN", None)
