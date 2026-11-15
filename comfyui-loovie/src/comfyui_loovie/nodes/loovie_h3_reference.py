"""Loovie H3 reference node.

`MiniMaxH3ReferenceToVideo` takes autogrow maps of individually named
references (`ref_images.ref_image_1` …, `ref_audios.ref_audio_1` …). A ComfyUI
graph is static, so a workflow cannot know at author time how many references a
request will carry. This adapter takes the stacked IMAGES batch + IMAGE_COUNT
from `LoovieImageInput`, and the AUDIO list + AUDIO_COUNT from
`LoovieAudioInput`, then builds exactly that many entries and delegates to the
native H3 reference node. No empty/black placeholders are ever counted as
references.

Reference VIDEO clips (up to 3, 2-15 s each, IMAGE frames at 24 fps) come from
`LoovieReferenceVideoInput` and become the numbered `ref_videos` entries.

Reference AUDIO is a first-class H3 capability (up to 3 clips, 2-15 s each,
15 s combined): the model conditions the generated soundtrack or a performance
on it, so it is what makes lip-sync and voice/timbre references work. The
`audio_vae` input is required for that conditioning; without it H3 only uses the
audio to condition the text encoder. Both graphs wire it from the same
`minimax_h3_audio_vae` loader the generated-audio path uses.
"""

from __future__ import annotations

from typing import Any

_MAX_REFERENCE_AUDIOS = 3
_MAX_REFERENCE_VIDEOS = 3


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
            "optional": {
                # Wired from `LoovieAudioInput`. Optional so a graph that carries
                # no audio-reference node still validates (and older graphs keep
                # loading unchanged).
                "audios": ("LOOVIE_AUDIO_LIST",),
                "audio_count": ("INT", {"default": 0, "min": 0, "max": 3}),
                # Wired from `LoovieReferenceVideoInput`: up to 3 clips as IMAGE
                # frames at 24 fps, handed to `ref_videos`.
                "videos": ("LOOVIE_VIDEO_LIST",),
                "video_count": ("INT", {"default": 0, "min": 0, "max": 3}),
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
        audios: list[dict[str, Any]] | None = None,
        audio_count: int = 0,
        videos: list[Any] | None = None,
        video_count: int = 0,
    ) -> tuple[Any, Any]:
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo

        count = max(0, min(int(image_count), int(images.shape[0]), 9))
        ref_images = {f"ref_image_{index}": images[index : index + 1] for index in range(count)}

        audio_list = list(audios or [])
        audio_total = max(0, min(int(audio_count), len(audio_list), _MAX_REFERENCE_AUDIOS))
        ref_audios = {f"ref_audio_{index + 1}": audio_list[index] for index in range(audio_total)}

        video_list = list(videos or [])
        video_total = max(0, min(int(video_count), len(video_list), _MAX_REFERENCE_VIDEOS))
        ref_videos = {f"ref_video_{index + 1}": video_list[index] for index in range(video_total)}

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
            ref_audios=ref_audios,
            ref_videos=ref_videos,
        )
        result = output.result
        if not isinstance(result, tuple) or len(result) < 2:
            raise RuntimeError("MiniMaxH3ReferenceToVideo returned no conditioning/latent")
        return (result[0], result[1])


__all__ = ["LoovieH3ReferenceToVideo"]
