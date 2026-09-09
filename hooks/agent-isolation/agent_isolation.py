#!/usr/bin/env python3
"""agent-isolation — PreToolUse hook shared by Claude Code and Copilot CLI.

In plain words: this refuses an AI agent's edits unless they come from the
agent's own private copy of the repo, kept in one agreed folder. Edits to
the real project folder, and edits from a copy someone put elsewhere, are
turned down with a message saying how to get it right.

Denies a write into the MAIN git checkout, a write from a linked worktree
outside the base that worktree_location names, and a write from a repo
whose main checkout git cannot name: a rule that cannot evaluate itself
refuses. Outside a repo there is nothing to judge, so that allows. The one
exception is the SCRATCH_DIR scratch space, which agents are told to keep
their notes and knowledgebase in and which is never committed.

Every path exits 0. Copilot fails CLOSED on a non-zero exit, so a crash in
here must never deny the whole session; a caught exception falls through to
allow. See docs/payloads.md for the measured wire shapes this codes against.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from worktree_location import base_for, git, is_inside_base, main_checkout_root

CONTAINER_MARKERS = ("/run/.containerenv", "/.dockerenv")
CLAUDE_DEFAULT_BASE = ".claude/worktrees"
SCRATCH_DIR = ".nikki-agents"

MAIN_CHECKOUT_REASON = (
    "Main checkout ({root}) is read-only for agents. Create your worktree "
    "under {base} (git worktree add {base}/<branch> -b <branch>), work "
    "there, and report the branch."
)

MISPLACED_WORKTREE_REASON = (
    "This worktree ({top}) sits outside {base}, the directory every agent "
    "worktree must live under. Redo this work in a correctly placed one: "
    "git worktree add {base}/<branch> -b <branch>"
)

CLAUDE_DEFAULT_WORKTREE_REASON = (
    "This worktree ({top}) is where Claude Code puts worktrees on its own, "
    "so the WorktreeCreate hook that would have placed it under {base} "
    "never ran: the dotai plugin is disabled, the session is in safe or "
    "--bare mode, or hooks are disabled by policy. Tell the user that. It "
    "is a broken setup, only she can fix it, and you must not work around "
    "it by moving or recreating the worktree yourself."
)

UNLOCATABLE_ROOT_REASON = (
    "{cwd} is inside a git repository whose layout stops this guard "
    "locating the main checkout, so it cannot judge whether writing here "
    "is allowed, and refuses rather than guess. Report this to the user: "
    "only she can fix the layout, and nothing you do here works around it."
)

WRITE_TOOLS = {"claude": ("Write", "Edit", "NotebookEdit"), "copilot": ("create", "edit")}
BASH_TOOLS = {"claude": ("Bash",), "copilot": ("bash", "powershell")}
GIT_ALWAYS_MUTATES = {
    "add", "commit", "checkout", "switch", "reset", "rebase", "merge",
    "push", "pull", "stash", "apply", "am", "mv", "rm", "restore", "clean",
    "tag",
}
NON_GIT_MUTATES = {"rm", "mv", "cp", "touch", "mkdir", "tee"}
# ponytail: redirect detection is a heuristic (misses e.g. `exec 3>file`),
# upgrade if a real false negative shows up.
REDIRECT_RE = re.compile(r"(?<!\d)>>?(?!&)")
SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||[;|\n]")


def is_container() -> bool:
    return any(Path(marker).exists() for marker in CONTAINER_MARKERS)


class Checkout(NamedTuple):
    """Where a path sits: main checkout root, its own working tree top."""

    root: Path
    top: Path
    is_main: bool


class UnlocatableCheckout(NamedTuple):
    """A repo whose main checkout git cannot name, so nothing can be judged."""

    cwd: Path


def in_a_repo(cwd: str) -> bool:
    try:
        return git(cwd, "rev-parse", "--is-inside-work-tree") == "true"
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return False


def checkout_at(cwd: str) -> Checkout | UnlocatableCheckout | None:
    """Where cwd sits, or None when there is genuinely nothing to judge.

    Outside a repo, and in a container, there is no checkout to be in the
    wrong half of: allow. Inside a repo the guard must reach a verdict, so
    a repo whose root worktree_location.main_checkout_root cannot name
    (--separate-git-dir seen from a linked worktree) is unjudgeable rather
    than uninteresting, and comes back as UnlocatableCheckout.
    """
    if is_container() or not in_a_repo(cwd):
        return None
    try:
        root = main_checkout_root(cwd).resolve()
        top = Path(git(cwd, "rev-parse", "--show-toplevel")).resolve()
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return UnlocatableCheckout(Path(cwd).resolve())
    return Checkout(root, top, top == root)


def is_scratch(target: Path, root: Path) -> bool:
    """True when target is in the checkout's gitignored scratch space.

    Every project here keeps agent notes, decision logs and a knowledgebase
    under SCRATCH_DIR and never commits it, so the read-only rule over the
    main checkout must not cover it. Both sides resolve first, so a path
    that only looks like scratch until ".." unwinds does not qualify.
    """
    return target.resolve().is_relative_to((root / SCRATCH_DIR).resolve())


def placement_reason(
    checkout: Checkout | UnlocatableCheckout, target: Path
) -> str | None:
    """Why writing to target from this checkout is refused, or None if fine."""
    if isinstance(checkout, UnlocatableCheckout):
        return UNLOCATABLE_ROOT_REASON.format(cwd=checkout.cwd)
    base = base_for(checkout.root)
    if checkout.is_main:
        if is_scratch(target, checkout.root):
            return None
        return MAIN_CHECKOUT_REASON.format(root=checkout.root, base=base)
    if is_inside_base(checkout.top, checkout.root):
        return None
    claude_default = (checkout.root / CLAUDE_DEFAULT_BASE).resolve()
    template = (
        CLAUDE_DEFAULT_WORKTREE_REASON
        if checkout.top.is_relative_to(claude_default)
        else MISPLACED_WORKTREE_REASON
    )
    return template.format(top=checkout.top, base=base)


def git_segment_mutates(tokens: list[str]) -> bool:
    if not tokens:
        return False
    sub = tokens[0]
    if sub in ("merge", "pull") and "--ff-only" in tokens:
        return False
    if sub == "branch":
        return "-d" in tokens or "-D" in tokens
    if sub in ("worktree", "fetch", "cherry-pick"):
        return False
    return sub in GIT_ALWAYS_MUTATES


def segment_mutates(segment: str) -> bool:
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    if not tokens:
        return False
    if tokens[0] == "git":
        return git_segment_mutates(tokens[1:])
    if tokens[0] in NON_GIT_MUTATES:
        return True
    if tokens[0] == "sed" and any(t.startswith("-i") for t in tokens[1:]):
        return True
    return bool(REDIRECT_RE.search(segment))


def command_mutates(command: str) -> bool:
    return any(segment_mutates(seg) for seg in SEGMENT_SPLIT_RE.split(command))


def first_present(mapping: dict, *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value:
            return value
    return None


def write_target(harness: str, tool_name: str, tool_args: dict, cwd: str) -> str | None:
    if tool_name in WRITE_TOOLS[harness]:
        if harness == "claude":
            file_path = tool_args.get("file_path")
        else:
            file_path = first_present(tool_args, "path", "file_path", "filePath")
        return (os.path.dirname(file_path) or cwd) if file_path else None
    if tool_name in BASH_TOOLS[harness]:
        if harness == "claude":
            command = tool_args.get("command", "")
        else:
            command = first_present(tool_args, "command", "cmd")
        return cwd if command and command_mutates(command) else None
    return None


def evaluate(harness: str, tool_name: str, tool_args: dict, cwd: str) -> str | None:
    target = write_target(harness, tool_name, tool_args, cwd)
    checkout = checkout_at(target) if target else None
    if checkout is None:
        return None
    return placement_reason(checkout, Path(target))


def deny_payload(harness: str, reason: str) -> dict:
    if harness == "claude":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}


def process(harness: str, payload: dict) -> dict | None:
    cwd = payload.get("cwd", "")
    if harness == "claude":
        agent_id = payload.get("agent_id")
        if agent_id is None:
            return None
        tool_name = payload.get("tool_name", "")
        tool_args = payload.get("tool_input") or {}
        reason = evaluate("claude", tool_name, tool_args, cwd)
    else:
        tool_name = payload.get("toolName", "")
        tool_args = payload.get("toolArgs") or {}
        reason = evaluate("copilot", tool_name, tool_args, cwd)
    return deny_payload(harness, reason) if reason else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", choices=("claude", "copilot"), required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        result = process(args.harness, payload)
    except Exception:
        result = None
    if result is not None:
        sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
