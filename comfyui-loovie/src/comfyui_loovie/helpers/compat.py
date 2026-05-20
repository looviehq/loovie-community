"""Compatibility shims for upstream ComfyUI / LTX 2.3 quirks.

Each shim is narrowly scoped, idempotent, and safe to drop when upstream
lands a fix. The two shims below address known incompatibilities between
LTX 2.3's text-encoder path and the moving target of the `transformers`
library (Gemma3 rope refactor) and ComfyUI's `LTXAVTEModel` memory
estimator (empty-token edge case).
"""

from __future__ import annotations

import logging

logger = logging.getLogger("comfyui_loovie.compat")


def _patch_ltxav_memory_estimation_for_empty_tokens() -> None:
    """Avoid `ValueError: min() arg is an empty sequence` in LTX-AV TEModel."""
    try:
        from comfy.text_encoders import lt as _lt
    except ImportError:
        logger.debug("comfy.text_encoders.lt not importable; skipping LTX-AV shim")
        return

    cls = getattr(_lt, "LTXAVTEModel", None)
    if cls is None:
        return
    if getattr(cls.memory_estimation_function, "_loovie_patched", False):
        return

    original = cls.memory_estimation_function
    import comfy.model_management

    def patched(self, token_weight_pairs, device=None):  # type: ignore[no-untyped-def]
        constant = 6.0
        if comfy.model_management.should_use_bf16(device):
            constant /= 2.0
        pairs = (
            token_weight_pairs.get("gemma3_12b", []) if isinstance(token_weight_pairs, dict) else []
        )
        if not pairs:
            return 642 * constant * 1024 * 1024
        return original(self, token_weight_pairs, device=device)

    patched._loovie_patched = True  # type: ignore[attr-defined]
    cls.memory_estimation_function = patched
    logger.info("Patched LTXAVTEModel.memory_estimation_function for empty tokens")


def _patch_gemma3_text_config_legacy_rope_attrs() -> None:
    """Expose legacy `rope_local_base_freq` / `rope_scaling` on Gemma3TextConfig.

    Newer `transformers` versions consolidated those instance attributes
    into a single `rope_parameters` dict. The LTX 2.3 Gemma encoder still
    reads the legacy names; this shim installs class-level property
    descriptors that fall back to `rope_parameters` when the legacy
    attribute is absent.
    """
    try:
        from transformers.models.gemma3.configuration_gemma3 import (
            Gemma3TextConfig,
        )
    except ImportError:
        return

    if getattr(Gemma3TextConfig, "_loovie_rope_patched", False):
        return

    def _rope_local_base_freq_get(self):  # type: ignore[no-untyped-def]
        v = self.__dict__.get("rope_local_base_freq")
        if v is not None:
            return v
        params = self.__dict__.get("rope_parameters") or {}
        sliding = params.get("sliding_attention") or {}
        return sliding.get("rope_theta")

    def _rope_local_base_freq_set(self, value):  # type: ignore[no-untyped-def]
        self.__dict__["rope_local_base_freq"] = value

    def _rope_scaling_get(self):  # type: ignore[no-untyped-def]
        v = self.__dict__.get("rope_scaling")
        if v is not None:
            return v
        params = self.__dict__.get("rope_parameters") or {}
        full = params.get("full_attention") or {}
        return full or None

    def _rope_scaling_set(self, value):  # type: ignore[no-untyped-def]
        self.__dict__["rope_scaling"] = value

    Gemma3TextConfig.rope_local_base_freq = property(
        _rope_local_base_freq_get, _rope_local_base_freq_set
    )
    Gemma3TextConfig.rope_scaling = property(_rope_scaling_get, _rope_scaling_set)
    Gemma3TextConfig._loovie_rope_patched = True
    logger.info("Patched Gemma3TextConfig with legacy rope_local_base_freq / rope_scaling")


logger.info("Applying comfyui-loovie compat shims at extension load")
_patch_ltxav_memory_estimation_for_empty_tokens()
_patch_gemma3_text_config_legacy_rope_attrs()
