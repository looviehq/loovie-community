"""image_cache.validate_url and friends, SSRF guards and filename derivation."""

from __future__ import annotations

import pytest

from comfyui_loovie.helpers.image_cache import (
    _url_to_filename,
    validate_url,
)

# ---------------------------------------------------------------------
# Scheme rejection.
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x.png",
        "gopher://example.com/",
        "data:image/png;base64,iVBOR...",
        "javascript:alert(1)",
    ],
)
def test_non_http_schemes_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="scheme"):
        validate_url(url)


def test_http_and_https_are_accepted() -> None:
    validate_url("http://example.com/x.png")
    validate_url("https://example.com/x.png")


# ---------------------------------------------------------------------
# Private/loopback IP rejection.
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x.png",
        "http://10.0.0.5/x.png",
        "http://172.16.0.1/x.png",
        "http://192.168.1.1/x.png",
        "http://169.254.0.1/x.png",
        "http://[::1]/x.png",
        "http://[fe80::1]/x.png",
    ],
)
def test_private_and_loopback_ips_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match=r"private|loopback|link-local|internal"):
        validate_url(url)


def test_public_ip_is_accepted() -> None:
    """A public IPv4 (e.g. Google DNS) must not be flagged."""
    validate_url("https://8.8.8.8/x.png")


def test_domain_name_passes_without_resolving() -> None:
    """We deliberately do not pre-resolve the hostname; OS handles it."""
    validate_url("https://example.com/x.png")
    validate_url("https://huggingface.co/user/model.png")


# ---------------------------------------------------------------------
# Hostname presence.
# ---------------------------------------------------------------------


def test_missing_hostname_is_rejected() -> None:
    with pytest.raises(ValueError, match="hostname"):
        validate_url("http:///nohost.png")


# ---------------------------------------------------------------------
# Filename derivation.
# ---------------------------------------------------------------------


def test_filename_uses_extension_from_url() -> None:
    name = _url_to_filename("https://example.com/cat.jpg")
    assert name.endswith(".jpg")


def test_filename_handles_query_string() -> None:
    name = _url_to_filename("https://example.com/cat.png?signature=abc")
    assert name.endswith(".png")


def test_filename_defaults_to_png_when_extension_unknown() -> None:
    name = _url_to_filename("https://example.com/blob")
    assert name.endswith(".png")


def test_filename_is_deterministic_for_same_url() -> None:
    first = _url_to_filename("https://example.com/cat.jpg")
    second = _url_to_filename("https://example.com/cat.jpg")
    assert first == second


def test_filename_differs_for_different_urls() -> None:
    """Sha256-derived; collisions for distinct URLs would be astonishing."""
    first = _url_to_filename("https://example.com/cat.jpg")
    second = _url_to_filename("https://example.com/dog.jpg")
    assert first != second
