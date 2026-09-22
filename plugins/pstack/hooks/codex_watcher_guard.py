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

# The commit-ish `git worktree add` starts the new worktree from: a plain
# branch name (`develop`), a branch with a namespace (`agent/pr2-split`), or
# a hex SHA. Each segment must start with a letter or digit, which both
# blocks git-option injection (a value beginning with `-`) and rejects a
# bare `.` or `..` segment, so no separate lookahead is needed here.
BASE_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._-]*"
BASE = rf"{BASE_SEGMENT}(?:/{BASE_SEGMENT})*"

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

# Codex's `workspace-write` sandbox denies writes under any `.git`
# directory, so a writer cannot commit until its command names the git paths
# a commit writes. This flag is the only way to grant them, which makes it
# the guard's job to pin every root it grants. Each root is tied by
# backreference to the `-C` directory itself, so a watcher cannot hand a
# write-enabled Codex session a directory outside this run's repo. The set
# is exactly four paths in a fixed order. `.git/hooks` and `.git/config` are
# not among them, so a hostile run cannot plant a hook that later executes
# on the owner's machine.
#
# The ref and reflog roots stop at `refs/heads/agent`, not at `refs` and
# `logs`, which would hand every writer write access to `main`, `develop`,
# and every other agent's branch and reflog in the owner's real checkout.
# The narrow roots create an invariant: a Codex writer can commit only to a
# branch under `agent/`, which is what step 3 of the watcher body creates,
# and a writer handed an existing worktree on a branch outside `agent/`
# cannot commit. Measured with everything else under `.git` made read-only,
# a linked-worktree commit writes only `objects`, `refs/heads/<branch>`,
# `logs/refs/heads/<branch>`, and `worktrees/<basename>`.
#
# Git keys a linked worktree's admin directory on the worktree directory's
# basename, not on its branch or the run name: `git worktree add
# <repo>/m/custom-dir -b agent/sample-run` creates
# `.git/worktrees/custom-dir`. The `worktree` group is that basename, taken
# from `-C`, so the fourth root can only be the admin directory git will
# actually write to. A regex backreference reads backwards only, which is
# why this flag has to follow `-C` in the command.
WRITABLE_ROOTS = (
    r" -c 'sandbox_workspace_write\.writable_roots="
    r"\[\"(?P=repo)/\.git/objects\""
    r",\"(?P=repo)/\.git/refs/heads/agent\""
    r",\"(?P=repo)/\.git/logs/refs/heads/agent\""
    r",\"(?P=repo)/\.git/worktrees/(?P=worktree)\"\]'"
)

# A developer writes inside a worktree under the repo (never the repo
# itself), and its report/prompt paths must still sit under the repo and
# run name the `-C` worktree belongs to.
DEVELOPER_BASH = COMMON_BASH + (
    re.compile(
        rf"{CODEX} exec -m {SLUG} -s workspace-write -c agents\.enabled=false"
        rf" -C (?P<repo>{PATH})/(?:{PATH_SEGMENT}/)*(?P<worktree>{PATH_SEGMENT})"
        rf"{WRITABLE_ROOTS}"
        rf" -o (?P=repo)/\.nikki-agents/codex-runs/(?P<name>{NAME})/report\.md"
        rf" - < (?P=repo)/\.nikki-agents/codex-runs/(?P=name)/prompt\.txt"
    ),
    re.compile(
        rf"git -C (?P<repo>{PATH}) worktree add"
        rf" (?P=repo)/\.nikki-agents/worktrees/(?P<name>{NAME}) -b agent/(?P=name)"
        rf" {BASE}"
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
    if not isinstance(command, str):
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
