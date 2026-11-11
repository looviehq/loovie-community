"""`LoovieReferenceSheet` node: tile ingredient images into one reference sheet.

LTX 2.5's ingredient conditioning reads a *single* reference image that lays
out characters, props and locations together, then the prompt refers to each
element by its position on the sheet. The app sends ingredients as individual
reference images, so this node composes them into one square-ish sheet before
the graph conditions on it.

Cells are resized to a multiple of 32 so the sheet stays on the model's pixel
grid. Missing slots are simply skipped; a caller can send one or many.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps

from ..helpers.image_cache import cache_image
from .loovie_image_input import _input_dir

logger = logging.getLogger("comfyui_loovie.nodes.reference_sheet")

_MAX_SLOTS = 4


def _load_rgb(relative_path: str) -> Image.Image:
    full_path = f"{_input_dir()}/{relative_path}"
    image: Image.Image = Image.open(full_path)
    image = ImageOps.exif_transpose(image) or image
    if image.mode == "I":
        image = image.point(lambda p: p * (1 / 255))
    return image.convert("RGB")


def _fit_cell(image: Image.Image, cell: int) -> Image.Image:
    """Letterbox `image` into a square `cell` without stretching it."""

    image.thumbnail((cell, cell), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (cell, cell), (255, 255, 255))
    x = (cell - image.width) // 2
    y = (cell - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


class LoovieReferenceSheet:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        inputs: dict[str, Any] = {
            "required": {
                "cell_size": ("INT", {"default": 512, "min": 64, "max": 2048, "step": 32}),
                "columns": ("INT", {"default": 2, "min": 1, "max": 4}),
            },
            "optional": {},
        }
        for i in range(1, _MAX_SLOTS + 1):
            inputs["optional"][f"image_url_{i}"] = ("STRING", {"default": ""})
        return inputs

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("SHEET", "COUNT")
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(
        self,
        cell_size: int = 512,
        columns: int = 2,
        **kwargs: object,
    ) -> tuple[object, ...]:
        cell = max(64, int(cell_size) // 32 * 32)
        columns = max(1, min(int(columns), _MAX_SLOTS))

        urls: list[str] = []
        for i in range(1, _MAX_SLOTS + 1):
            raw = kwargs.get(f"image_url_{i}", "")
            if isinstance(raw, str) and raw.strip():
                urls.append(raw.strip())

        if not urls:
            return (
                torch.ones((1, cell, cell, 3), dtype=torch.float32),
                0,
            )

        logger.info("Composing %d ingredient image(s) into a reference sheet", len(urls))
        cells = [_fit_cell(_load_rgb(cache_image(url)), cell) for url in urls]
        rows = math.ceil(len(cells) / columns)
        sheet = Image.new("RGB", (cell * columns, cell * rows), (255, 255, 255))
        for index, image in enumerate(cells):
            x = (index % columns) * cell
            y = (index // columns) * cell
            sheet.paste(image, (x, y))

        arr = np.array(sheet).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr).unsqueeze(0)
        return (tensor, len(cells))


__all__ = ["LoovieReferenceSheet"]
