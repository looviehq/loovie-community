"""This directory is the loovie-community monorepo, not a ComfyUI custom node.

Install only ``comfyui-loovie/`` into ComfyUI (see docs/20-quickstart-your-own-machine.md).
ComfyUI loads every folder under ``custom_nodes/``; if you cloned the whole repo there
by mistake, this file prevents a hard import error. The pack is skipped because there
is no ``NODE_CLASS_MAPPINGS`` here.
"""
