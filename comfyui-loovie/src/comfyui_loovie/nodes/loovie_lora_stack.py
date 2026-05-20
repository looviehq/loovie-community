"""`LoovieLoraStack` node: chain up to 5 LoRAs onto MODEL + CLIP."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("comfyui_loovie.nodes.lora_stack")

_MAX_LORAS = 5


class LoovieLoraStack:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        inputs: dict[str, Any] = {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
            },
            "optional": {},
        }
        for i in range(1, _MAX_LORAS + 1):
            inputs["optional"][f"lora_name_{i}"] = ("STRING", {"default": ""})
            inputs["optional"][f"strength_{i}"] = (
                "FLOAT",
                {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01},
            )
        return inputs

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("MODEL", "CLIP")
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(self, model: Any, clip: Any, **kwargs: object) -> tuple[Any, Any]:
        import comfy.sd
        import comfy.utils
        import folder_paths

        current_model = model
        current_clip = clip
        for i in range(1, _MAX_LORAS + 1):
            raw_name = kwargs.get(f"lora_name_{i}", "")
            name = raw_name.strip() if isinstance(raw_name, str) else ""
            if not name:
                continue
            raw_strength = kwargs.get(f"strength_{i}", 0.8)
            strength = float(raw_strength) if isinstance(raw_strength, (int, float, str)) else 0.8
            path = folder_paths.get_full_path("loras", name)
            if path is None:
                logger.warning("LoRA not found: %s", name)
                continue
            logger.info("Loading LoRA %d: %s (strength=%.2f)", i, name, strength)
            lora = comfy.utils.load_torch_file(path, safe_load=True)
            current_model, current_clip = comfy.sd.load_lora_for_models(
                current_model, current_clip, lora, strength, strength
            )
        return (current_model, current_clip)
