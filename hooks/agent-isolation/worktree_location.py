"""One placement rule for agent git worktrees, shared by every tool.

In plain words: this says where an AI agent's private copy of the repo goes -
a fixed folder inside the repo instead of wherever each tool would pick - so
the copies are all in one predictable place and easy to find or delete.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BASE_ENV_VAR = "DOTAI_WORKTREE_BASE"
DEFAULT_BASE = ".nikki-agents/worktrees"
GIT_CALL_TIMEOUT_SEC = 10


def base_for(repo_root: Path | str) -> Path:
    """Directory holding every agent worktree of the repo at repo_root."""
    relative = os.environ.get(BASE_ENV_VAR) or DEFAULT_BASE
    if Path(relative).is_absolute():
        raise ValueError(
            f"{BASE_ENV_VAR}={relative} must be relative to the repo root"
        )
    return Path(repo_root) / relative


def is_inside_base(target: Path | str, repo_root: Path | str) -> bool:
    """True when target lands inside the base once ".." and links resolve."""
    base = base_for(repo_root).resolve()
    return Path(target).resolve().is_relative_to(base)


def git(cwd: Path | str, *args: str) -> str:
    """Run one git command, or raise ValueError carrying git's own reason."""
    done = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True, text=True, timeout=GIT_CALL_TIMEOUT_SEC,
    )
    if done.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def worktree_entries(cwd: Path | str) -> list[tuple[Path, str | None]]:
    """Every worktree of the repo at cwd as (path, branch), main first.

    Branch is None for a detached HEAD. Order is git's own: "git worktree
    list" always names the main worktree first. The path git prints for the
    MAIN worktree is its admin directory whenever that is not <root>/.git,
    so use main_checkout_root rather than reading entry zero directly.
    """
    listing = git(cwd, "worktree", "list", "--porcelain")
    entries: list[tuple[Path, str | None]] = []
    for line in listing.splitlines():
        if line.startswith("worktree "):
            entries.append((Path(line[len("worktree "):]), None))
        elif line.startswith("branch ") and entries:
            ref = line[len("branch "):]
            entries[-1] = (entries[-1][0], ref.removeprefix("refs/heads/"))
    if not entries:
        raise ValueError(f"git names no worktree for {cwd}")
    return entries


def main_checkout_root(cwd: Path | str) -> Path:
    """Working directory of the repo's MAIN worktree, seen from cwd.

    Three inferences that look right and are not, all verified against real
    repos: the git admin directory's parent (wrong for a submodule, whose
    admin dir lives under the superproject, and for --separate-git-dir);
    --show-toplevel alone (from a linked worktree that names the LINKED
    worktree); and "git worktree list" entry zero (for the main worktree
    git prints the admin directory, not the checkout, in both of those
    layouts). So: --show-toplevel when cwd is itself in the main worktree,
    and the toplevel of entry zero when cwd is in a linked one.
    """
    git_dir, common_dir, toplevel = git(
        cwd, "rev-parse", "--git-dir", "--git-common-dir", "--show-toplevel"
    ).splitlines()
    if git_dir == common_dir:
        return Path(toplevel)
    main_entry = worktree_entries(cwd)[0][0]
    return Path(git(main_entry, "rev-parse", "--show-toplevel"))
