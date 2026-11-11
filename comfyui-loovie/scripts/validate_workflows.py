#!/usr/bin/env python3
"""Check every shipped workflow against a running ComfyUI's `/object_info`.

Unit tests cover the registry and the route layer; they cannot see ComfyUI
itself. This script closes that gap: it loads each JSON under `workflows/` and
verifies that every node class exists, that every input the graph sets is a real
input of that class (including autogrow and dynamic-combo slots), and that every
link points at an existing node with enough outputs.

Run it against the release you are about to pin, before bumping
`COMFYUI_REF` in `docker/Dockerfile`:

    python comfyui-loovie/scripts/validate_workflows.py http://127.0.0.1:8188

Exit code 0 means the whole shipped set is loadable on that ComfyUI.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / "workflows"
DEFAULT_BASE = "http://127.0.0.1:8188"


def _expand(name: str, spec: object) -> set[str]:
    """Input names a V3 node accepts, including autogrow and dynamic-combo slots."""
    out = {name}
    if not isinstance(spec, list) or not spec:
        return out
    kind = spec[0]
    opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
    if kind == "COMFY_AUTOGROW_V3":
        template = opts.get("template", {})
        names = template.get("names")
        if names:
            out.update(f"{name}.{slot}" for slot in names)
        else:
            prefix, limit = template.get("prefix", ""), template.get("max", 0)
            out.update(f"{name}.{prefix}{i}" for i in range(1, limit + 1))
    elif kind == "COMFY_DYNAMICCOMBO_V3":
        for option in opts.get("options", []):
            out.add(f"{name}.{option.get('key')}")
            for section in ("required", "optional"):
                for sub in option.get("inputs", {}).get(section, {}):
                    out.add(f"{name}.{sub}")
    return out


def _input_names(info: dict) -> tuple[set[str], set[str]]:
    def names(section: dict) -> set[str]:
        out: set[str] = set()
        for input_name, spec in section.items():
            out |= _expand(input_name, spec)
        return out

    declared = info.get("input", {})
    return names(declared.get("required", {})), names(declared.get("optional", {}))


def validate(base: str) -> list[str]:
    with urllib.request.urlopen(f"{base}/object_info", timeout=120) as response:
        object_info = json.load(response)

    failures: list[str] = []
    known: dict[str, tuple[set[str], set[str]]] = {}

    for path in sorted(WORKFLOWS.glob("*.json")):
        graph = json.loads(path.read_text())
        for node_id, node in graph.items():
            class_type = node["class_type"]
            if class_type not in object_info:
                failures.append(f"{path.name}:{node_id}: unknown node class {class_type}")
                continue
            if class_type not in known:
                known[class_type] = _input_names(object_info[class_type])
            required, optional = known[class_type]
            for key, value in node.get("inputs", {}).items():
                if key not in required and key not in optional:
                    failures.append(f"{path.name}:{node_id}: {class_type} has no input {key!r}")
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                    upstream = graph.get(value[0])
                    if upstream is None:
                        failures.append(
                            f"{path.name}:{node_id}: {key} links to missing node {value[0]}"
                        )
                        continue
                    out_type = upstream["class_type"]
                    outputs = object_info.get(out_type, {}).get("output", [])
                    if value[1] >= len(outputs):
                        failures.append(
                            f"{path.name}:{node_id}: {key} wants output {value[1]} of "
                            f"{out_type} which only has {len(outputs)}"
                        )
    return failures


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    try:
        failures = validate(base)
        with urllib.request.urlopen(f"{base}/system_stats", timeout=60) as response:
            version = json.load(response)["system"]["comfyui_version"]
    except OSError as exc:
        print(f"cannot reach {base}: {exc}", file=sys.stderr)
        return 2

    print(f"checked {len(list(WORKFLOWS.glob('*.json')))} workflows against ComfyUI {version}")
    if failures:
        print(f"{len(failures)} problem(s):")
        for line in failures:
            print(f" - {line}")
        return 1
    print("all node classes, inputs and links resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
