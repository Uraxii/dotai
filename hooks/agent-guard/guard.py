#!/usr/bin/env python3
"""agent-guard — PreToolUse hook shared by Claude Code and Copilot CLI.

Denies a write into the MAIN git checkout; agents work in their own
worktree.

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

CONTAINER_MARKERS = ("/run/.containerenv", "/.dockerenv")

MAIN_CHECKOUT_REASON = (
    "Main checkout ({root}) is read-only for agents. Work in your own git "
    "worktree (git worktree add ...) and report the branch."
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


def run_git(cwd: str, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def main_checkout_root(cwd: str) -> Path | None:
    if is_container():
        return None
    common = run_git(cwd, "rev-parse", "--git-common-dir")
    gitdir = run_git(cwd, "rev-parse", "--git-dir")
    if common is None or gitdir is None:
        return None
    common_path = (Path(cwd) / common).resolve()
    gitdir_path = (Path(cwd) / gitdir).resolve()
    return common_path.parent if common_path == gitdir_path else None


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
    root = main_checkout_root(target) if target else None
    return MAIN_CHECKOUT_REASON.format(root=root) if root else None


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
