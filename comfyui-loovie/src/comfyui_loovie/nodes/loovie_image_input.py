"""`LoovieImageInput` node: download 1-10 image URLs and emit ComfyUI tensors.

Outputs a stacked IMAGE batch, an optional VAE-encoded LATENT, the
per-slot IMAGE_N / LATENT_N tensors (used by multi-reference video
workflows), a MASK tensor, and the HAS_MASK boolean. If `vae` is wired
the latents are encoded; otherwise placeholder zero latents are emitted
so the graph still validates.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps

from ..helpers.image_cache import cache_image

logger = logging.getLogger("comfyui_loovie.nodes.image_input")

_MAX_SLOTS = 10
_REF_SLOTS = 4
_TARGET_PIXELS = 1_048_576  # 1 megapixel; matches ImageScaleToTotalPixels


def _input_dir() -> str:
    try:
        import folder_paths  # type: ignore[import-not-found]
    except ImportError:
        return "input"
    return folder_paths.get_input_directory()


def _load_image(relative_path: str) -> tuple[torch.Tensor, torch.Tensor]:
    """Load a PIL-readable file from ComfyUI's input dir into ComfyUI tensors.

    Returns:
        (image_tensor [1, H, W, 3] float32 in [0, 1],
         mask_tensor  [H, W] float32 in [0, 1])
    """
    full_path = f"{_input_dir()}/{relative_path}"
    img = Image.open(full_path)
    img = ImageOps.exif_transpose(img)
    if img.mode == "I":
        img = img.point(lambda p: p * (1 / 255))
    rgb = img.convert("RGB")
    arr = np.array(rgb).astype(np.float32) / 255.0
    image_tensor = torch.from_numpy(arr).unsqueeze(0)
    if "A" in img.getbands():
        alpha = np.array(img.getchannel("A")).astype(np.float32) / 255.0
        mask_tensor = 1.0 - torch.from_numpy(alpha)
    else:
        mask_tensor = torch.zeros((arr.shape[0], arr.shape[1]), dtype=torch.float32)
    return image_tensor, mask_tensor


def _scale_to_total_pixels(
    image_tensor: torch.Tensor, total_pixels: int = _TARGET_PIXELS
) -> torch.Tensor:
    """Scale `image_tensor` to approximately `total_pixels`, multiple of 64."""
    _, h, w, _ = image_tensor.shape
    current = h * w
    if current == 0:
        return image_tensor
    scale = (total_pixels / current) ** 0.5
    new_w = max(64, round(w * scale / 64) * 64)
    new_h = max(64, round(h * scale / 64) * 64)
    if new_w == w and new_h == h:
        return image_tensor
    permuted = image_tensor.permute(0, 3, 1, 2)
    resized = torch.nn.functional.interpolate(
        permuted, size=(new_h, new_w), mode="bilinear", antialias=True
    )
    return resized.permute(0, 2, 3, 1)


class LoovieImageInput:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        inputs: dict[str, dict[str, object]] = {
            "required": {
                "width": ("INT", {"default": 768, "min": 64, "max": 8192, "step": 8}),
                "height": ("INT", {"default": 768, "min": 64, "max": 8192, "step": 8}),
                "latent_type": (["sd3", "flux2"], {"default": "sd3"}),
            },
            "optional": {
                "vae": ("VAE",),
                "mask_url": ("STRING", {"default": ""}),
            },
        }
        for i in range(1, _MAX_SLOTS + 1):
            inputs["optional"][f"image_url_{i}"] = ("STRING", {"default": ""})
        return inputs

    RETURN_TYPES = (
        "IMAGE", "LATENT", "INT", "MASK", "BOOLEAN",
        "IMAGE", "LATENT", "IMAGE", "LATENT",
        "IMAGE", "LATENT", "IMAGE", "LATENT",
    )
    RETURN_NAMES = (
        "IMAGES", "LATENT", "IMAGE_COUNT", "MASK", "HAS_MASK",
        "IMAGE_1", "LATENT_1", "IMAGE_2", "LATENT_2",
        "IMAGE_3", "LATENT_3", "IMAGE_4", "LATENT_4",
    )
    FUNCTION = "process"
    CATEGORY = "loovie"

    def _empty_latent(
        self, latent_type: str, height: int, width: int
    ) -> dict[str, torch.Tensor]:
        try:
            import comfy.model_management  # type: ignore[import-not-found]

            device = comfy.model_management.intermediate_device()
        except ImportError:
            device = torch.device("cpu")
        if latent_type == "flux2":
            samples = torch.zeros(
                [1, 128, height // 16, width // 16], device=device
            )
            return {"samples": samples}
        samples = torch.zeros([1, 16, height // 8, width // 8], device=device)
        return {"samples": samples, "downscale_ratio_spacial": 8}

    def _empty_image(self, height: int = 64, width: int = 64) -> torch.Tensor:
        return torch.zeros((1, height, width, 3), dtype=torch.float32)

    def process(
        self,
        width: int,
        height: int,
        latent_type: str = "sd3",
        vae: Any = None,
        mask_url: str = "",
        **kwargs: object,
    ) -> tuple[object, ...]:
        mask_url = (mask_url or "").strip() if isinstance(mask_url, str) else ""
        max_slots = _MAX_SLOTS - 1 if mask_url else _MAX_SLOTS

        urls: list[str] = []
        for i in range(1, max_slots + 1):
            raw = kwargs.get(f"image_url_{i}", "")
            if isinstance(raw, str) and raw.strip():
                urls.append(raw.strip())

        has_mask = bool(mask_url)
        if has_mask:
            cached = cache_image(mask_url)
            _, mask_loaded = _load_image(cached)
            mask_tensor = (
                mask_loaded.unsqueeze(0)
                if mask_loaded.ndim == 2
                else mask_loaded
            )
        else:
            mask_tensor = torch.zeros((1, height, width), dtype=torch.float32)

        ref_images: list[torch.Tensor] = [self._empty_image() for _ in range(_REF_SLOTS)]
        ref_latents: list[dict[str, torch.Tensor]] = [
            self._empty_latent(latent_type, height, width) for _ in range(_REF_SLOTS)
        ]

        if not urls:
            empty_image = self._empty_image(height, width)
            latent = self._empty_latent(latent_type, height, width)
            return (
                empty_image, latent, 0, mask_tensor, has_mask,
                ref_images[0], ref_latents[0],
                ref_images[1], ref_latents[1],
                ref_images[2], ref_latents[2],
                ref_images[3], ref_latents[3],
            )

        logger.info("Loading %d reference image(s)", len(urls))
        loaded: list[torch.Tensor] = []
        for url in urls:
            cached = cache_image(url)
            img_tensor, _ = _load_image(cached)
            loaded.append(img_tensor)

        for i, tensor in enumerate(loaded[:_REF_SLOTS]):
            scaled = _scale_to_total_pixels(tensor)
            ref_images[i] = scaled
            if vae is not None:
                encoded = vae.encode(scaled[:, :, :, :3])
                ref_latents[i] = {"samples": encoded}

        shapes = {tuple(t.shape[1:]) for t in loaded}
        if len(shapes) == 1:
            stacked = torch.cat(loaded, dim=0)
        else:
            logger.warning(
                "Reference images have mismatched shapes; using the first only"
            )
            stacked = loaded[0]

        if vae is not None:
            first = loaded[0]
            encoded = vae.encode(first[:, :, :, :3])
            if has_mask:
                img_h, img_w = first.shape[1], first.shape[2]
                mask2d = mask_tensor[0] if mask_tensor.ndim == 3 else mask_tensor
                if mask2d.shape[0] != img_h or mask2d.shape[1] != img_w:
                    mask2d = torch.nn.functional.interpolate(
                        mask2d.unsqueeze(0).unsqueeze(0),
                        size=(img_h, img_w),
                        mode="nearest",
                    ).squeeze(0).squeeze(0)
                latent = {"samples": encoded, "noise_mask": mask2d.unsqueeze(0)}
            else:
                latent = {"samples": encoded}
        else:
            latent = {"samples": torch.zeros((1, 4, height // 8, width // 8))}

        return (
            stacked, latent, len(urls), mask_tensor, has_mask,
            ref_images[0], ref_latents[0],
            ref_images[1], ref_latents[1],
            ref_images[2], ref_latents[2],
            ref_images[3], ref_latents[3],
        )
