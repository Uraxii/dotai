#!/usr/bin/env python3
"""Put the `codex` shim first on PATH for every Bash call that mentions codex.

Without `-c agents.enabled=false`, Codex 0.154.0 exposes
`collaboration.spawn_agent`, `followup_task`, and `send_message`, so a
`codex exec` can hand the prompt to a helper agent instead of doing the work
itself. This applies everywhere, main thread or any subagent, because any
Bash call can run `codex exec` by hand.

The hook never edits the command text and never parses shell. It prepends
`PATH=<plugin root>/shims:"$PATH";` to a command containing `codex`. The shim
`shims/codex` adds the flag when it is actually run as `codex exec`, so
heredocs, quotes, `$(...)`, and `bash -c` all behave as the shell decides.

This is not a security gate: a command that already carries the prefix, or
that never mentions codex, passes through untouched. It rewrites `command`
via `hookSpecificOutput.updatedInput`
(https://code.claude.com/docs/en/hooks, PreToolUse decision control table,
fetched 2026-09-29: "`updatedInput` | Modifies the tool's input parameters
before execution. ... Claude Code evaluates permission rules ... against the
input your hook returns, not the input Claude sent."). No `permissionDecision`
is set, so the rewritten command still goes through the normal permission
flow instead of being auto-approved.
"""

from __future__ import annotations

import json
import shlex
import sys
from collections.abc import Mapping
from pathlib import Path


__all__ = ["rewrite_command", "main"]

SHIMS_DIR = Path(__file__).resolve().parents[1] / "shims"


def rewrite_command(command: str) -> str:
    """Prepend the shim dir to PATH when `command` mentions codex."""
    prefix = f"PATH={shlex.quote(str(SHIMS_DIR))}:\"$PATH\"; "
    if "codex" not in command or command.startswith(prefix):
        return command
    return prefix + command


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, Mapping):
            return
        if payload.get("tool_name") != "Bash":
            return
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, Mapping):
            return
        command = tool_input.get("command")
        if not isinstance(command, str):
            return
        rewritten = rewrite_command(command)
        if rewritten == command:
            return
        updated_input = dict(tool_input)
        updated_input["command"] = rewritten
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated_input,
            }
        }))
    except Exception:
        # Never block a Bash call over a rewrite that could not be
        # computed; the flag is a convenience, not a permission boundary.
        return


if __name__ == "__main__":
    main()
