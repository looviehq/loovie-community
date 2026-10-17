"""Loovie-category custom nodes used by the shipped workflows.

Each node is a small adapter between the JSON request body and a
diffusion graph. The route layer scans the workflow JSON by
`class_type` and injects request fields into these nodes (`prompt`,
`aspect_ratio`, `image_urls`, `loras`, video settings) before the
graph is submitted to ComfyUI's queue.
"""

from __future__ import annotations

from .loovie_audio_gate import LoovieAudioGate
from .loovie_image_input import LoovieImageInput
from .loovie_lora_stack import LoovieLoraStack
from .loovie_music_input import LoovieMusicInput
from .loovie_settings import LoovieSettings
from .loovie_text_input import LoovieTextInput
from .loovie_video_input import LoovieVideoInput
from .loovie_video_settings import LoovieVideoSettings

NODE_CLASS_MAPPINGS: dict[str, type] = {
    "LoovieSettings": LoovieSettings,
    "LoovieTextInput": LoovieTextInput,
    "LoovieImageInput": LoovieImageInput,
    "LoovieLoraStack": LoovieLoraStack,
    "LoovieVideoSettings": LoovieVideoSettings,
    "LoovieVideoInput": LoovieVideoInput,
    "LoovieAudioGate": LoovieAudioGate,
    "LoovieMusicInput": LoovieMusicInput,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "LoovieSettings": "Loovie Settings",
    "LoovieTextInput": "Loovie Text Input",
    "LoovieImageInput": "Loovie Image Input",
    "LoovieLoraStack": "Loovie LoRA Stack",
    "LoovieVideoSettings": "Loovie Video Settings",
    "LoovieVideoInput": "Loovie Video Input",
    "LoovieAudioGate": "Loovie Audio Gate",
    "LoovieMusicInput": "Loovie Music Input",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
