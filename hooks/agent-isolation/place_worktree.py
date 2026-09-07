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

from worktree_location import base_for, is_inside_base

GIT_TIMEOUT_SEC = 55
BRANCH_PREFIX = "agent/"
EXCLUDE_MARKER = "# dotai-worktrees"
BASE_COMMIT_FILE = "CLAUDE_BASE"
LOCAL_SETTINGS = Path(".claude") / "settings.local.json"
INCLUDE_LIST = ".worktreeinclude"


class HookError(Exception):
    """A reason the hook must refuse, reported on stderr."""


def git(cwd: Path | str, *args: str) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_SEC,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HookError(f"git {' '.join(args)} failed: {exc}") from exc
    if done.returncode != 0:
        raise HookError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def git_common_dir(cwd: Path | str) -> Path:
    """Admin dir shared by the checkout and all its linked worktrees."""
    return Path(git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def config_value(cwd: Path, key: str) -> str | None:
    try:
        return git(cwd, "config", "--get", key) or None
    except HookError:
        return None


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


def add_worktree(cwd: Path, dest: Path, name: str, base_sha: str) -> None:
    """Add the worktree, retrying once when the branch name is taken."""
    candidates = (
        f"{BRANCH_PREFIX}{name}",
        f"{BRANCH_PREFIX}{name}-{base_sha[:7]}",
    )
    for branch in candidates:
        try:
            git(cwd, "worktree", "add", "-b", branch, str(dest), base_sha)
            return
        except HookError as failure:
            last = failure
    raise last


def copy_local_settings(root: Path, dest: Path) -> None:
    source = root / LOCAL_SETTINGS
    if not source.is_file() or source.is_symlink():
        return
    target = dest / LOCAL_SETTINGS
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def absolutize_hooks_path(root: Path) -> None:
    """Make a relative core.hooksPath resolve the same from a worktree.

    Git keeps one config for a checkout and its linked worktrees unless
    extensions.worktreeConfig is on, so the value is rewritten in place. It
    names the same directory as before for the main checkout.
    """
    value = config_value(root, "core.hooksPath")
    if value is None or Path(value).is_absolute():
        return
    git(root, "config", "core.hooksPath", str(root / value))


def copy_included_paths(root: Path, dest: Path) -> None:
    """Copy the plain paths listed in .worktreeinclude into the worktree.

    Plain path entries only. Claude's own reader matches gitignore patterns;
    reimplementing that matcher is out of scope, so a pattern entry is
    treated as a path and skipped when no such path exists.
    """
    listing = root / INCLUDE_LIST
    if not listing.is_file():
        return
    for line in listing.read_text().splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        source = (root / entry).resolve()
        if not source.exists() or not source.is_relative_to(root.resolve()):
            continue
        target = dest / source.relative_to(root.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)


def post_create(root: Path, dest: Path, base_sha: str) -> None:
    """Redo the parts of Claude's own worktree setup that matter."""
    admin_dir = Path(git(dest, "rev-parse", "--absolute-git-dir"))
    (admin_dir / BASE_COMMIT_FILE).write_text(f"{base_sha}\n")
    copy_local_settings(root, dest)
    absolutize_hooks_path(root)
    copy_included_paths(root, dest)


def create(payload: dict) -> Path:
    cwd = Path(payload["cwd"])
    name = payload["name"]
    common_dir = git_common_dir(cwd)
    root = common_dir.parent
    dest = base_for(root) / name
    if (dest / ".git").exists():
        return dest
    base_sha = git(cwd, "rev-parse", "HEAD")
    hide_base_from_git(common_dir, root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    add_worktree(cwd, dest, name, base_sha)
    post_create(root, dest, base_sha)
    return dest


def head_branch(worktree: Path) -> str | None:
    try:
        return git(worktree, "rev-parse", "--abbrev-ref", "HEAD")
    except HookError:
        return None


def drop_merged_branch(root: Path, branch: str) -> None:
    """Delete the agent branch only when its work is already merged.

    Unmerged agent work is unrecoverable once the worktree is gone, so a
    branch git refuses to delete with -d is left in place.
    """
    if not branch.startswith(BRANCH_PREFIX):
        return
    try:
        git(root, "branch", "-d", branch)
    except HookError:
        return


def remove(payload: dict) -> None:
    cwd = Path(payload["cwd"])
    target = Path(payload["worktree_path"])
    root = git_common_dir(cwd).parent
    if not is_inside_base(target, root):
        raise HookError(
            f"refusing to remove {target}: outside {base_for(root)}"
        )
    branch = head_branch(target)
    try:
        git(cwd, "worktree", "remove", "--force", str(target))
    except HookError:
        git(cwd, "worktree", "prune")
    if branch:
        drop_merged_branch(root, branch)


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
