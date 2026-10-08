#!/usr/bin/env python3
"""Add `-c agents.enabled=false` to every `codex exec` a Bash call runs.

Without the flag, Codex 0.154.0 exposes `collaboration.spawn_agent`,
`followup_task`, and `send_message`, so a `codex exec` can hand the prompt
to a helper agent instead of doing the work itself. This applies everywhere,
main thread or any subagent, not only the `delegate-to-codex` watchers,
because any Bash call can run `codex exec` by hand.

This is not a security gate: an unparseable or non-matching command passes
through untouched, and a command that already carries the flag is left
alone. It only rewrites `command` via `hookSpecificOutput.updatedInput`
(https://code.claude.com/docs/en/hooks, PreToolUse decision control table,
fetched 2026-09-29: "`updatedInput` | Modifies the tool's input parameters
before execution. ... Claude Code evaluates permission rules ... against the
input your hook returns, not the input Claude sent."). No `permissionDecision`
is set, so the rewritten command still goes through the normal permission
flow instead of being auto-approved.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping


__all__ = ["rewrite_command", "main"]

FLAG = "-c agents.enabled=false"
FLAG_MARKER = "agents.enabled=false"

# A `codex` invocation starts right after the string start or a shell
# separator (`;`, `&`, `|`, a backtick, a newline, or an opening paren),
# with optional whitespace in between, never mid-word. `echo codex exec`
# (codex is an argument to echo, not a command) and `/tmp/codex/exec.sh`
# (codex is a path segment) both fail this on purpose: neither has one of
# those separators right before `codex`.
#
# ponytail: this is a regex heuristic, not a shell parser. A command
# substitution, an alias, or a `codex` reached through a variable can still
# slip past it either way. Upgrade to a real shell tokenizer if a live
# command trips it.
CODEX_INVOCATION = re.compile(r"(?:\A|[;&|`\n(])\s*codex\b")
SEGMENT_END = re.compile(r"[;&|`\n)]")
EXEC_WORD = re.compile(r"\bexec\b")


def rewrite_command(command: str) -> str:
    """Add the no-helper-agents flag to every `codex exec` in `command`.

    Each `codex ...` invocation, up to the next shell separator or the end
    of the string, is one segment. A segment that contains `exec` as its
    own word gets `-c agents.enabled=false` right after that `exec`, unless
    the segment already carries the flag. `codex login status` or
    `codex --version`, with no `exec` in their own segment, are untouched.

    The flag goes after `exec`, not after `codex`, so the rewritten argv
    still reads `codex exec`, which the delegate-to-codex collision check
    `codex exec.*-C <worktree>` matches.
    """
    pieces: list[str] = []
    cursor = 0
    for match in CODEX_INVOCATION.finditer(command):
        codex_end = match.end()
        if codex_end < cursor:
            continue  # inside a segment this loop already rewrote
        boundary = SEGMENT_END.search(command, codex_end)
        segment_end = boundary.start() if boundary else len(command)
        segment = command[codex_end:segment_end]
        exec_word = EXEC_WORD.search(segment)
        if exec_word and FLAG_MARKER not in segment:
            exec_end = codex_end + exec_word.end()
            pieces.append(command[cursor:exec_end])
            pieces.append(f" {FLAG}")
            cursor = exec_end
    pieces.append(command[cursor:])
    return "".join(pieces)


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
