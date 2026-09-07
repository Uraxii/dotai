#!/usr/bin/env python3
"""WorktreeCreate / WorktreeRemove hook: put agent worktrees in one place.

In plain words: when Claude Code starts an agent that needs its own copy of
the repo, this decides where that copy goes and makes it, so every agent
lands in the same predictable folder instead of one the tool picks.

Registering WorktreeCreate replaces Claude's own worktree setup, so this
also redoes the parts of that setup which matter (see post_create).

Failure is fail-closed and deliberate: no stdout, reason on stderr, non-zero
exit, which aborts worktree creation. That is the INVERSE of the sibling
PreToolUse hook, which always exits 0 (see agent_isolation.py). Do not
"fix" one to match the other: echoing a fallback path here would silently
put the agent back in Claude's own directory.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from worktree_location import (
    GIT_CALL_TIMEOUT_SEC,
    base_for,
    is_inside_base,
    main_checkout_root,
    worktree_entries,
)

BRANCH_PREFIX = "agent/"
EXCLUDE_MARKER = "# dotai-worktrees"
BASE_COMMIT_FILE = "CLAUDE_BASE"
LOCAL_SETTINGS = Path(".claude") / "settings.local.json"


class HookError(Exception):
    """A reason the hook must refuse, reported on stderr."""


def git(cwd: Path | str, *args: str) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True, text=True, timeout=GIT_CALL_TIMEOUT_SEC,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HookError(f"git {' '.join(args)} failed: {exc}") from exc
    if done.returncode != 0:
        raise HookError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def git_common_dir(cwd: Path | str) -> Path:
    """Admin dir shared by the checkout and all its linked worktrees."""
    return Path(cwd, git(cwd, "rev-parse", "--git-common-dir")).resolve()


def hide_base_from_git(common_dir: Path, root: Path) -> None:
    """Keep the worktree base out of the main checkout's status, once."""
    exclude = common_dir / "info" / "exclude"
    text = exclude.read_text() if exclude.is_file() else ""
    if EXCLUDE_MARKER in text:
        return
    top = base_for(root).relative_to(root).parts[0]
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a") as handle:
        handle.write(f"\n{EXCLUDE_MARKER}\n/{top}/\n")


def copy_local_settings(root: Path, dest: Path) -> None:
    source = root / LOCAL_SETTINGS
    if not source.is_file() or source.is_symlink():
        return
    target = dest / LOCAL_SETTINGS
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def post_create(root: Path, dest: Path, base_sha: str) -> None:
    """Redo the parts of Claude's own worktree setup that matter."""
    admin_dir = Path(git(dest, "rev-parse", "--absolute-git-dir"))
    base_file = admin_dir / BASE_COMMIT_FILE
    if not base_file.exists():
        base_file.write_text(f"{base_sha}\n")
    copy_local_settings(root, dest)


def reusable(cwd: Path, dest: Path, branch: str) -> bool:
    """True when dest is already this agent's worktree, refusing near-misses.

    A directory being there proves nothing: it can be a bare "mkdir .git"
    git owns no worktree for, a tree left behind by a failed removal, or
    another agent's checkout. Anything but an exact match is refused, since
    handing back an unregistered path gives the agent work it can never land.
    """
    if not dest.exists():
        return False
    resolved = dest.resolve()
    for path, checked_out in worktree_entries(cwd):
        if path.resolve() != resolved:
            continue
        if checked_out == branch:
            return True
        raise HookError(
            f"refusing {dest}: on branch {checked_out}, not {branch}"
        )
    raise HookError(f"refusing {dest}: exists but git owns no worktree there")


def discard_worktree(cwd: Path, dest: Path, branch: str) -> None:
    """Undo a worktree add, so a half-finished create leaves nothing behind."""
    git(cwd, "worktree", "remove", "--force", str(dest))
    git(cwd, "branch", "-D", branch)


def create(payload: dict) -> Path:
    cwd = Path(payload["cwd"])
    name = payload["name"]
    root = main_checkout_root(cwd)
    branch = f"{BRANCH_PREFIX}{name}"
    dest = base_for(root) / name
    base_sha = git(cwd, "rev-parse", "HEAD")
    if reusable(cwd, dest, branch):
        post_create(root, dest, base_sha)
        return dest
    hide_base_from_git(git_common_dir(cwd), root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(cwd, "worktree", "add", "-b", branch, str(dest), base_sha)
    try:
        post_create(root, dest, base_sha)
    except (HookError, OSError):
        discard_worktree(cwd, dest, branch)
        raise
    return dest


def head_branch(worktree: Path) -> str | None:
    try:
        return git(worktree, "rev-parse", "--abbrev-ref", "HEAD")
    except HookError:
        return None


def remove(payload: dict) -> None:
    cwd = Path(payload["cwd"])
    target = Path(payload["worktree_path"])
    root = main_checkout_root(cwd)
    if not is_inside_base(target, root):
        raise HookError(
            f"refusing to remove {target}: outside {base_for(root)}"
        )
    branch = head_branch(target)
    git(cwd, "worktree", "remove", "--force", str(target))
    if branch and branch.startswith(BRANCH_PREFIX):
        try:
            git(root, "branch", "-d", branch)
        except HookError:
            return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=("create", "remove"), required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if args.event == "create":
            sys.stdout.write(f"{create(payload)}\n")
        else:
            remove(payload)
    except (HookError, OSError, ValueError, KeyError) as failure:
        sys.stderr.write(f"{failure}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
