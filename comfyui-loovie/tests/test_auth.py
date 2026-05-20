"""Auth-helper tests, the most security-critical code in the package.

The full route layer needs a running aiohttp app to test end-to-end;
these tests cover the two pure helpers (`_is_local_request`,
`_check_auth`) directly with fake `web.Request` objects so we can pin
the fail-closed contract without a server.
"""

from __future__ import annotations

import pytest

# Imports happen inside the test so the conftest stubs are in place
# before `routes` pulls `from server import PromptServer` at module load.


def _make_request(*, peer_host: str | None, auth_header: str | None = None, path: str = "/x"):
    """Build a minimal fake `web.Request` for the auth helpers."""
    from types import SimpleNamespace

    headers = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header

    transport = SimpleNamespace(
        get_extra_info=lambda key: (peer_host, 0) if peer_host else None,
    )
    return SimpleNamespace(
        transport=transport,
        headers=headers,
        path=path,
    )


# ---------------------------------------------------------------------
# _is_local_request
# ---------------------------------------------------------------------


def test_loopback_v4_is_local() -> None:
    from comfyui_loovie.server.routes import _is_local_request

    assert _is_local_request(_make_request(peer_host="127.0.0.1")) is True


def test_loopback_v6_is_local() -> None:
    from comfyui_loovie.server.routes import _is_local_request

    assert _is_local_request(_make_request(peer_host="::1")) is True


def test_public_ip_is_not_local() -> None:
    from comfyui_loovie.server.routes import _is_local_request

    assert _is_local_request(_make_request(peer_host="8.8.8.8")) is False


def test_lan_ip_is_not_local() -> None:
    """A LAN IP is "remote" for auth purposes; only literal loopback bypasses."""
    from comfyui_loovie.server.routes import _is_local_request

    assert _is_local_request(_make_request(peer_host="192.168.1.50")) is False


def test_no_peername_is_not_local() -> None:
    from comfyui_loovie.server.routes import _is_local_request

    assert _is_local_request(_make_request(peer_host=None)) is False


# ---------------------------------------------------------------------
# _check_auth
# ---------------------------------------------------------------------


def test_localhost_bypasses_auth_regardless_of_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """A loopback caller never has to send a Bearer header."""
    from comfyui_loovie.server.routes import _check_auth
    from comfyui_loovie.workflow_manager import WorkflowManager

    monkeypatch.delenv("LOOVIE_API_TOKEN", raising=False)
    WorkflowManager.reset()

    response = _check_auth(_make_request(peer_host="127.0.0.1"))
    assert response is None


def test_remote_with_no_configured_token_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail-closed: no token + remote caller MUST be a 401."""
    from comfyui_loovie.server.routes import _check_auth
    from comfyui_loovie.workflow_manager import WorkflowManager

    monkeypatch.delenv("LOOVIE_API_TOKEN", raising=False)
    monkeypatch.setattr(
        "comfyui_loovie.workflow_manager._package_root",
        # tmp dir with no config -> empty registry, empty token
        lambda: __import__("pathlib").Path("/tmp/no-such-dir-for-config"),
    )
    WorkflowManager.reset()

    response = _check_auth(_make_request(peer_host="8.8.8.8", auth_header=None))
    assert response is not None
    assert response.status == 401


def test_remote_with_matching_bearer_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    from comfyui_loovie.server.routes import _check_auth
    from comfyui_loovie.workflow_manager import WorkflowManager

    monkeypatch.setenv("LOOVIE_API_TOKEN", "supersecret")
    WorkflowManager.reset()

    response = _check_auth(
        _make_request(peer_host="8.8.8.8", auth_header="Bearer supersecret"),
    )
    assert response is None


def test_remote_with_wrong_bearer_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    from comfyui_loovie.server.routes import _check_auth
    from comfyui_loovie.workflow_manager import WorkflowManager

    monkeypatch.setenv("LOOVIE_API_TOKEN", "supersecret")
    WorkflowManager.reset()

    response = _check_auth(
        _make_request(peer_host="8.8.8.8", auth_header="Bearer wrong"),
    )
    assert response is not None
    assert response.status == 401


def test_remote_with_no_authorization_header_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    from comfyui_loovie.server.routes import _check_auth
    from comfyui_loovie.workflow_manager import WorkflowManager

    monkeypatch.setenv("LOOVIE_API_TOKEN", "supersecret")
    WorkflowManager.reset()

    response = _check_auth(_make_request(peer_host="8.8.8.8", auth_header=None))
    assert response is not None
    assert response.status == 401


def test_remote_with_non_bearer_authorization_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The contract only accepts `Bearer <token>`. Basic auth is not allowed."""
    from comfyui_loovie.server.routes import _check_auth
    from comfyui_loovie.workflow_manager import WorkflowManager

    monkeypatch.setenv("LOOVIE_API_TOKEN", "supersecret")
    WorkflowManager.reset()

    response = _check_auth(
        _make_request(peer_host="8.8.8.8", auth_header="Basic dXNlcjpwYXNz"),
    )
    assert response is not None
    assert response.status == 401
