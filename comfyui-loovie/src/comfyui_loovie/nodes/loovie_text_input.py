"""`LoovieTextInput` node: passthrough for prompt + negative prompt.

The node exists so the route handler can locate it in the workflow
graph by `class_type` and inject the request body's `prompt` and
`negative_prompt` values.
"""

from __future__ import annotations


class LoovieTextInput:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, object]:
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("PROMPT", "NEGATIVE")
    FUNCTION = "process"
    CATEGORY = "loovie"

    def process(self, prompt: str, negative_prompt: str = "") -> tuple[str, str]:
        return (prompt, negative_prompt)
