"""Loovie H3 reference node.

`MiniMaxH3ReferenceToVideo` takes an autogrow map of individually named
reference images (`ref_images.ref_image_0` …). A ComfyUI graph is static, so a
workflow cannot know at author time how many references a request will carry.
This adapter takes the stacked IMAGES batch + IMAGE_COUNT emitted by
`LoovieImageInput` and builds exactly that many entries, then delegates to the
native H3 reference node. No empty/black placeholders are ever counted as
references.
"""

from __future__ import annotations

from typing import Any


class LoovieH3ReferenceToVideo:
    """Dynamic reference-count adapter for MiniMax H3 Ref2VA."""

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "audio_vae": ("VAE",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "width": ("INT", {"default": 1344, "min": 32, "max": 16384, "step": 32}),
                "height": ("INT", {"default": 768, "min": 32, "max": 16384, "step": 32}),
                "length": ("INT", {"default": 124, "min": 5, "max": 3600, "step": 17}),
                "images": ("IMAGE",),
                "image_count": ("INT", {"default": 0, "min": 0, "max": 9}),
                "ref_image_size": (["match", "max"], {"default": "match"}),
            },
        }

    RETURN_TYPES = ("CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "LATENT")
    FUNCTION = "build"
    CATEGORY = "loovie"

    def build(
        self,
        clip: Any,
        vae: Any,
        audio_vae: Any,
        prompt: str,
        width: int,
        height: int,
        length: int,
        images: Any,
        image_count: int,
        ref_image_size: str = "match",
    ) -> tuple[Any, Any]:
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo

        count = max(0, min(int(image_count), int(images.shape[0]), 9))
        ref_images = {f"ref_image_{index}": images[index : index + 1] for index in range(count)}
        output = MiniMaxH3ReferenceToVideo.execute(
            clip=clip,
            prompt=prompt,
            width=int(width),
            height=int(height),
            length=int(length),
            ref_image_size=ref_image_size,
            vae=vae,
            audio_vae=audio_vae,
            ref_images=ref_images,
        )
        result = output.result
        if not isinstance(result, tuple) or len(result) < 2:
            raise RuntimeError("MiniMaxH3ReferenceToVideo returned no conditioning/latent")
        return (result[0], result[1])


__all__ = ["LoovieH3ReferenceToVideo"]
