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
REVIEWER = "reviewer-codex"
DEVELOPER = "developer-codex"
WATCHER_NAMES = frozenset({DEVELOPER, REVIEWER})
# A `..` or `.` segment is rejected wherever it ends, not only when the next
# character happens to be `/` or the string's own end: some of these names
# and segments are followed mid-command by a space (`worktree add NAME -b`).
NAME = r"(?!\.\.?(?![A-Za-z0-9._-]))[A-Za-z0-9._-]+"
SLUG = r"[a-z0-9][a-z0-9.-]*"
PATH_SEGMENT = r"(?!\.\.?(?![A-Za-z0-9._@+-]))[A-Za-z0-9._@+-]+"
PATH = rf"/(?:{PATH_SEGMENT})(?:/{PATH_SEGMENT})*"
FORBIDDEN_COMMAND_CHARS = re.compile(r"[\n\r;&|$`>]")

# Both `codex-agent`, the machine-local wrapper that isolates `CODEX_HOME`,
# and bare `codex` are allowed: the wrapper is preferred, but a machine
# without it must still let the watcher fall back to the real binary.
CODEX = r"codex(?:-agent)?"

# Commands both watcher kinds share: no repo/name coupling to enforce.
COMMON_BASH = (
    re.compile(rf"{CODEX} --version"),
    re.compile(rf"{CODEX} login status"),
    re.compile(rf"git -C {PATH} rev-parse HEAD"),
)

# A reviewer never writes: read-only sandbox, `-C` is the bare repo, and the
# report/prompt paths must sit under that same repo and run name.
REVIEWER_BASH = COMMON_BASH + (
    re.compile(
        rf"{CODEX} exec -m {SLUG} -s read-only -c agents\.enabled=false"
        rf" -C (?P<repo>{PATH})"
        rf" -o (?P=repo)/\.nikki-agents/codex-runs/(?P<name>{NAME})/report\.md"
        rf" - < (?P=repo)/\.nikki-agents/codex-runs/(?P=name)/prompt\.txt"
    ),
)

# A developer writes inside a worktree under the repo (never the repo
# itself), and its report/prompt paths must still sit under the repo and
# run name the `-C` worktree belongs to.
DEVELOPER_BASH = COMMON_BASH + (
    re.compile(
        rf"{CODEX} exec -m {SLUG} -s workspace-write -c agents\.enabled=false"
        rf" -C (?P<repo>{PATH})/{PATH_SEGMENT}(?:/{PATH_SEGMENT})*"
        rf" -o (?P=repo)/\.nikki-agents/codex-runs/(?P<name>{NAME})/report\.md"
        rf" - < (?P=repo)/\.nikki-agents/codex-runs/(?P=name)/prompt\.txt"
    ),
    re.compile(
        rf"git -C (?P<repo>{PATH}) worktree add"
        rf" (?P=repo)/\.nikki-agents/worktrees/(?P<name>{NAME}) -b agent/(?P=name)"
    ),
)

ALLOWED_BASH_BY_KIND = {REVIEWER: REVIEWER_BASH, DEVELOPER: DEVELOPER_BASH}
ALLOWED_WRITE = re.compile(rf"{PATH}/\.nikki-agents/codex-runs/{NAME}/prompt\.txt")


def watcher_kind(payload: Mapping[str, object]) -> str | None:
    agent_type = payload.get("agent_type")
    if not isinstance(agent_type, str):
        return None
    name = agent_type.rpartition(":")[2]
    return name if name in WATCHER_NAMES else None


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


def safe_tool_name(payload: Mapping[str, object]) -> str:
    tool_name = payload.get("tool_name")
    return tool_name if isinstance(tool_name, str) else "unknown"


def allowed_bash(command: object, kind: str) -> bool:
    if not isinstance(command, str) or FORBIDDEN_COMMAND_CHARS.search(command):
        return False
    normalized = re.sub(r" +", " ", command.strip())
    return any(pattern.fullmatch(normalized) for pattern in ALLOWED_BASH_BY_KIND[kind])


def allowed_write(file_path: object) -> bool:
    return isinstance(file_path, str) and ALLOWED_WRITE.fullmatch(file_path) is not None


def _guard_watcher(payload: Mapping[str, object], kind: str) -> str:
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, Mapping):
        return deny(safe_tool_name(payload))
    if (
        tool_name == "Bash"
        and not tool_input.get("run_in_background")
        and allowed_bash(tool_input.get("command"), kind)
    ):
        return ""
    if tool_name == "Write" and allowed_write(tool_input.get("file_path")):
        return ""
    return deny(tool_name)


def guard(payload: Mapping[str, object]) -> str:
    """Return a PreToolUse denial JSON line, or an empty string to allow.

    Fails closed: an exception raised while judging a watcher's payload
    denies the call instead of letting it through unguarded. A payload that
    does not name a watcher is not this guard's job, so it re-raises.
    """
    try:
        kind = watcher_kind(payload)
        if kind is None:
            return ""
        return _guard_watcher(payload, kind)
    except Exception:
        try:
            still_a_watcher = watcher_kind(payload) is not None
        except Exception:
            still_a_watcher = False
        if still_a_watcher:
            return deny(safe_tool_name(payload))
        raise


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as error:
        print(f"codex watcher guard: cannot parse stdin as JSON: {error}", file=sys.stderr)
        raise SystemExit(2)
    if isinstance(payload, Mapping):
        output = guard(payload)
        if output:
            print(output)


if __name__ == "__main__":
    main()
