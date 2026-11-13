# Local BYO server helpers: ComfyUI + comfyui-loovie.
#
# Configure paths and the port in .byo-server.env (gitignored); see
# .byo-server.env.example. Everything can also be overridden per invocation:
#
#   make restart COMFY_DIR=/models/ComfyUI COMFY_PYTHON=/models/.comfy-venv/bin/python PORT=8199

-include .byo-server.env

# Empty COMFY_DIR lets scripts/byo-server.sh auto-detect the checkout.
COMFY_DIR     ?=
COMFY_PYTHON  ?=
HOST          ?= 0.0.0.0
PORT          ?= 8188
LOG           ?= /tmp/loovie-comfy-$(PORT).log
START_TIMEOUT ?= 90

export COMFY_DIR COMFY_PYTHON HOST PORT LOG START_TIMEOUT

.PHONY: start stop restart status logs

start stop restart status logs:
	@./scripts/byo-server.sh $@
