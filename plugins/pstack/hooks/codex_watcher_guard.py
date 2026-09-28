#!/usr/bin/env python3
"""Allow a Codex watcher agent one command: `pstack-codex-run <RUN>`.

The CLI checks RUN against the runs root, so this guard only pins the
command's shape. A path made of plain path characters leaves the shell
nothing to expand, chain, or redirect.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping


__all__ = ["guard", "main"]

WATCHER_NAMES = frozenset({"developer-codex", "reviewer-codex"})
ALLOWED_COMMAND = re.compile(r"pstack-codex-run /[A-Za-z0-9._/@+-]+")


def watcher_kind(payload: Mapping[str, object]) -> str | None:
    agent_type = payload.get("agent_type")
    if not isinstance(agent_type, str):
        return None
    name = agent_type.rpartition(":")[2]
    return name if name in WATCHER_NAMES else None


def deny(reason: str) -> str:
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"codex watcher guard: {reason}",
            }
        }
    )


def check_watcher_call(payload: Mapping[str, object]) -> str | None:
    """Return None to allow the call, or one sentence saying why not."""
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if tool_name != "Bash":
        return f"{tool_name} is not allowed for a Codex watcher; only Bash is"
    if not isinstance(tool_input, Mapping):
        return "the Bash call has no input"
    if tool_input.get("run_in_background"):
        return "Bash must not run in the background"
    command = tool_input.get("command")
    if not isinstance(command, str) or not ALLOWED_COMMAND.fullmatch(command):
        return (
            "the only allowed command is pstack-codex-run followed by one "
            "absolute run directory"
        )
    return None


def guard(payload: Mapping[str, object]) -> str:
    """Return a PreToolUse denial JSON line, or an empty string to allow.

    Fails closed: an exception raised while judging a watcher's payload
    denies the call instead of letting it through unguarded. A payload that
    does not name a watcher is not this guard's job, so it re-raises.
    """
    try:
        if watcher_kind(payload) is None:
            return ""
        reason = check_watcher_call(payload)
        return "" if reason is None else deny(reason)
    except Exception:
        try:
            still_a_watcher = watcher_kind(payload) is not None
        except Exception:
            still_a_watcher = False
        if still_a_watcher:
            return deny("the call could not be checked, so it is denied")
        raise


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as error:
        print(
            f"codex watcher guard: cannot parse stdin as JSON: {error}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if isinstance(payload, Mapping):
        output = guard(payload)
        if output:
            print(output)


if __name__ == "__main__":
    main()
