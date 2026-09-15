#!/usr/bin/env python3
"""Allow Codex watcher agents to use only their delegate playbook commands."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping


__all__ = ["guard", "main"]

DENIAL_REASON = (
    "codex watcher guard: {tool} call not in the delegate-to-codex allowlist; "
    "copy the playbook command exactly or send the fallback reply"
)
WATCHER_NAMES = frozenset({"developer-codex", "reviewer-codex"})
NAME = r"[A-Za-z0-9._-]+"
SLUG = r"[a-z0-9.-]+"
PATH_SEGMENT = r"(?!(?:\.\.)(?:/|$))[A-Za-z0-9._@+-]+"
PATH = rf"/(?:{PATH_SEGMENT})(?:/{PATH_SEGMENT})*"
RUN_PATH = rf"{PATH}/\.nikki-agents/codex-runs/{NAME}"
FORBIDDEN_COMMAND_CHARS = re.compile(r"[\n\r;&|$`>]")


def full_command(pattern: str) -> re.Pattern[str]:
    return re.compile(rf"{pattern}")


CODEX_EXEC_OPTIONS = (
    rf"(?: -c model_reasoning_effort=(?:low|medium|high))?"
    rf"(?: --add-dir {PATH})?"
    rf"|(?: --add-dir {PATH})?"
    rf"(?: -c model_reasoning_effort=(?:low|medium|high))?"
)
ALLOWED_BASH = (
    full_command(r"codex --version"),
    full_command(r"codex login status"),
    full_command(
        rf"codex exec -m {SLUG} -s (?:workspace-write|read-only) -C {PATH}"
        rf"(?:{CODEX_EXEC_OPTIONS})? -o {RUN_PATH}/report\.md - < {RUN_PATH}/prompt\.txt"
    ),
    full_command(rf"git -C {PATH} worktree add {PATH} -b agent/{NAME}"),
    full_command(rf"git -C {PATH} rev-parse HEAD"),
    full_command(rf"ls {RUN_PATH}/report\.md"),
)
ALLOWED_WRITE = full_command(rf"{RUN_PATH}/prompt\.txt")


def is_watcher(payload: Mapping[str, object]) -> bool:
    agent_type = payload.get("agent_type")
    return isinstance(agent_type, str) and agent_type.rpartition(":")[2] in WATCHER_NAMES


def deny(tool_name: str) -> str:
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": DENIAL_REASON.format(tool=tool_name),
            }
        }
    )


def allowed_bash(command: object) -> bool:
    if not isinstance(command, str) or FORBIDDEN_COMMAND_CHARS.search(command):
        return False
    normalized = re.sub(r" +", " ", command.strip())
    return any(pattern.fullmatch(normalized) for pattern in ALLOWED_BASH)


def allowed_write(file_path: object) -> bool:
    return isinstance(file_path, str) and ALLOWED_WRITE.fullmatch(file_path) is not None


def guard(payload: Mapping[str, object]) -> str:
    """Return a PreToolUse denial JSON line, or an empty string to allow."""
    if not is_watcher(payload):
        return ""
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, Mapping):
        return deny(tool_name if isinstance(tool_name, str) else "unknown")
    if tool_name == "Bash" and allowed_bash(tool_input.get("command")):
        return ""
    if tool_name == "Write" and allowed_write(tool_input.get("file_path")):
        return ""
    return deny(tool_name)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return
    if isinstance(payload, Mapping):
        output = guard(payload)
        if output:
            print(output)


if __name__ == "__main__":
    main()
