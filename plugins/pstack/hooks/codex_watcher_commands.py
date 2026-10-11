#!/usr/bin/env python3
"""Restrict tool calls from the two Codex watchers."""

import json
import os
from pathlib import Path
import re
import shlex
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

WATCHERS = {
    "developer-codex": "writer",
    "pstack:developer-codex": "writer",
    "reviewer-codex": "reviewer",
    "pstack:reviewer-codex": "reviewer",
}


def launch_allowed(command: str, role: str) -> bool:
    from prepare_codex_run import parse_request

    builder = shlex.quote(str(PLUGIN_ROOT / "scripts/prepare_codex_run.py"))
    prefix = f"python3 {builder} --launch <<'PSTACK_REQUEST'\n"
    suffix = "\nPSTACK_REQUEST"
    if not command.startswith(prefix) or not command.endswith(suffix):
        return False
    request = parse_request(command[len(prefix):-len(suffix)])
    return request.role == role


def wait_allowed(command: str, role: str) -> bool:
    prefix = "until grep -qs '\"pstack\":\"codex exited\"' "
    suffix = "; do sleep 5; done; echo codex exited"
    if not command.startswith(prefix) or not command.endswith(suffix):
        return False
    quoted = command[len(prefix):-len(suffix)]
    paths = shlex.split(quoted)
    if len(paths) != 1 or quoted != shlex.quote(paths[0]):
        return False
    path = Path(paths[0])
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    root = state / "pstack/codex-runs"
    if not root.is_absolute() or not path.is_absolute():
        return False
    relative = path.relative_to(root)
    parts = relative.parts
    return (len(parts) == 3 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", parts[0])
            is not None and parts[1:] == (role, "codex.jsonl")
            and path.resolve().is_relative_to(root.resolve()))


def decision(payload: dict) -> bool:
    role = WATCHERS[payload["agent_type"]]
    command = payload["tool_input"]["command"]
    if not isinstance(command, str):
        return False
    tool = payload["tool_name"]
    if tool == "Bash":
        return launch_allowed(command, role)
    if tool == "Monitor":
        return wait_allowed(command, role)
    return False


def main() -> int:
    allowed = False
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be an object")
        if payload.get("agent_type") not in WATCHERS:
            return 0
        allowed = decision(payload)
    except Exception:
        allowed = False
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow" if allowed else "deny",
        "permissionDecisionReason": "Codex watchers can only launch the builder or wait for its exit.",
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
