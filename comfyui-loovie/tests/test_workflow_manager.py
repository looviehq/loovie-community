"""WorkflowManager: config loading, token resolution, workflow registry."""

from __future__ import annotations

import pytest

from comfyui_loovie.workflow_manager import WorkflowManager

# ---------------------------------------------------------------------
# api_token resolution.
# ---------------------------------------------------------------------


def test_api_token_from_env_wins_over_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOVIE_API_TOKEN", "from-env")
    WorkflowManager.reset()
    assert WorkflowManager.get_instance().api_token == "from-env"


def test_api_token_falls_back_to_config_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOOVIE_API_TOKEN", raising=False)
    WorkflowManager.reset()
    wm = WorkflowManager.get_instance()
    # The shipped config.yaml may or may not have an api_token; we only
    # assert it's a string (possibly empty), not what its value is.
    assert isinstance(wm.api_token, str)


def test_api_token_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOVIE_API_TOKEN", "  padded  ")
    WorkflowManager.reset()
    assert WorkflowManager.get_instance().api_token == "padded"


def test_api_token_empty_when_both_unset(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """If env + config both lack a token, the property returns empty string."""
    monkeypatch.delenv("LOOVIE_API_TOKEN", raising=False)
    # Point the package root at a tmp dir with no config.yaml so the
    # registry is empty AND api_token has no config fallback.
    monkeypatch.setattr(
        "comfyui_loovie.workflow_manager._package_root",
        lambda: tmp_path,
    )
    WorkflowManager.reset()
    assert WorkflowManager.get_instance().api_token == ""


# ---------------------------------------------------------------------
# Workflow registry.
# ---------------------------------------------------------------------


def test_get_workflow_names_returns_registered_names() -> None:
    WorkflowManager.reset()
    names = WorkflowManager.get_instance().get_workflow_names()
    assert isinstance(names, list)
    # Public ref impl ships at least the flux + ltx23 family.
    assert "flux-2-klein" in names
    assert any(n.startswith("ltx23-") for n in names)


def test_load_workflow_returns_deep_copy() -> None:
    """Mutating the returned template must not leak into the cache."""
    WorkflowManager.reset()
    wm = WorkflowManager.get_instance()
    first = wm.load_workflow("flux-2-klein")
    # Add an arbitrary top-level key.
    first["_test_marker"] = "should-not-leak"
    second = wm.load_workflow("flux-2-klein")
    assert "_test_marker" not in second


def test_load_workflow_raises_on_unknown_name() -> None:
    WorkflowManager.reset()
    with pytest.raises(ValueError, match="Unknown workflow"):
        WorkflowManager.get_instance().load_workflow("does-not-exist")


# ---------------------------------------------------------------------
# max_wait override.
# ---------------------------------------------------------------------


def test_get_max_wait_seconds_uses_per_workflow_override() -> None:
    """If config.yaml lists `max_wait_seconds` on a workflow, it wins."""
    WorkflowManager.reset()
    wm = WorkflowManager.get_instance()
    default = wm.max_wait_seconds
    # Each shipped workflow either has an override or falls back to default;
    # this test just confirms the lookup path returns a positive int.
    actual = wm.get_max_wait_seconds("flux-2-klein")
    assert actual > 0
    assert isinstance(actual, int)
    # And unknown workflows fall back to the default.
    assert wm.get_max_wait_seconds("does-not-exist") == default
    assert wm.get_max_wait_seconds(None) == default


# ---------------------------------------------------------------------
# URL helpers.
# ---------------------------------------------------------------------


def test_comfy_api_url_respects_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOVIE_COMFY_INTERNAL_URL", "http://comfy.internal:9999")
    WorkflowManager.reset()
    assert WorkflowManager.get_instance().comfy_api_url == "http://comfy.internal:9999"


def test_comfy_api_url_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOOVIE_COMFY_INTERNAL_URL", "http://comfy.internal/")
    WorkflowManager.reset()
    assert not WorkflowManager.get_instance().comfy_api_url.endswith("/")


def test_comfy_api_url_falls_back_to_port_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOOVIE_COMFY_INTERNAL_URL", raising=False)
    monkeypatch.setenv("COMFYUI_PORT", "9876")
    WorkflowManager.reset()
    assert "9876" in WorkflowManager.get_instance().comfy_api_url


def test_output_base_url_is_a_string() -> None:
    WorkflowManager.reset()
    assert isinstance(WorkflowManager.get_instance().output_base_url, str)


# ---------------------------------------------------------------------
# Singleton.
# ---------------------------------------------------------------------


def test_get_instance_returns_same_singleton() -> None:
    WorkflowManager.reset()
    assert WorkflowManager.get_instance() is WorkflowManager.get_instance()


def test_reset_drops_singleton() -> None:
    WorkflowManager.reset()
    first = WorkflowManager.get_instance()
    WorkflowManager.reset()
    assert WorkflowManager.get_instance() is not first
