#!/usr/bin/env python3
"""Print the `--add-dir` grants a Codex writer needs to commit in a worktree.

Usage: codex_writer_grants.py <worktree>

On success, prints one shell-quoted line of `--add-dir <path>` pairs and
exits 0. Codex's `workspace-write` sandbox keeps `.git` read-only, and these
grants reopen only what a commit writes: the shared objects, refs, and logs,
plus the worktree's own gitdir.

Exits 1 with the reason on stderr, printing nothing on stdout, when Codex
must not run there: the target is a main checkout, whose gitdir is the
whole `.git`, or a grant would cover the hooks dir or the shared `config`. The watcher
runs git outside the sandbox after Codex exits, so a hook or config Codex
could write would run with the watcher's rights.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


__all__ = ["GitLayout", "grants", "refusal", "main"]


@dataclass(frozen=True)
class GitLayout:
    git_dir: Path
    common_dir: Path
    hooks_dir: Path
    config_files: tuple[Path, ...]


def read_git(worktree: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(worktree), *args],
        capture_output=True, text=True,
    )


def git_path(worktree: Path, *args: str) -> Path:
    result = read_git(worktree, "rev-parse", "--path-format=absolute", *args)
    result.check_returncode()
    return Path(result.stdout.strip())


def read_layout(worktree: Path) -> GitLayout:
    git_dir = git_path(worktree, "--git-dir")
    common_dir = git_path(worktree, "--git-common-dir")
    config_files = (common_dir / "config",)
    return GitLayout(
        git_dir=git_dir,
        common_dir=common_dir,
        hooks_dir=git_path(worktree, "--git-path", "hooks"),
        config_files=config_files,
    )


def grants(layout: GitLayout) -> tuple[Path, ...]:
    common = layout.common_dir
    return (common / "objects", common / "refs", common / "logs",
            layout.git_dir)


def refusal(layout: GitLayout) -> str | None:
    """Why Codex must not get these grants, or None when it may."""
    if layout.git_dir == layout.common_dir:
        return (f"{layout.git_dir} is a main checkout's git dir; "
                "run Codex in a linked worktree")
    for protected in (layout.hooks_dir, *layout.config_files):
        for grant in grants(layout):
            if protected.is_relative_to(grant):
                return f"grant {grant} would make {protected} writable"
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: codex_writer_grants.py <worktree>", file=sys.stderr)
        return 1
    try:
        layout = read_layout(Path(argv[1]))
    except subprocess.CalledProcessError as error:
        print(error.stderr.strip(), file=sys.stderr)
        return 1
    reason = refusal(layout)
    if reason is not None:
        print(f"refused: {reason}", file=sys.stderr)
        return 1
    print(" ".join(f"--add-dir {shlex.quote(str(path))}"
                   for path in grants(layout)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
