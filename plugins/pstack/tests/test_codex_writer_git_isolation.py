"""The developer-codex watcher keeps Codex-written git hooks out of its reach.

Codex runs `-s workspace-write` with `--add-dir` grants into the git dir so
it can commit. The watcher then runs git outside the sandbox. In a main
checkout the gitdir grant is the whole `.git`, so Codex could plant a hook
the watcher's `git push` would run. These tests run the watcher's own
grants script and its own git commands, read from the agent definition,
against real repositories. The `git commit` form in the agent definition is
Codex's, runs inside the sandbox, and is covered by test_commit_trailer_block.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
GRANTS_SCRIPT = PLUGIN_ROOT / "scripts/codex_writer_grants.py"
WATCHER = PLUGIN_ROOT / "agents/developer-codex.md"
HOOKS_OFF = "-c core.hooksPath=/dev/null"
CODEX_COMMIT = "git commit "


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> dict[str, Path]:
    """A main checkout with an `origin` remote and one linked worktree."""
    remote = tmp_path / "remote.git"
    main = tmp_path / "main"
    worktree = tmp_path / "linked"
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    git("init", "-q", "-b", "develop", str(main), cwd=tmp_path)
    git("-c", "user.name=t", "-c", "user.email=t@example.com",
        "commit", "-q", "--allow-empty", "-m", "root", cwd=main)
    git("remote", "add", "origin", str(remote), cwd=main)
    git("worktree", "add", "-q", "-b", "fix/unit", str(worktree), cwd=main)
    return {"remote": remote, "main": main, "worktree": worktree}


def run_grants(target: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(GRANTS_SCRIPT), str(target)],
        capture_output=True, text=True,
    )


def granted_paths(stdout: str) -> list[Path]:
    words = shlex.split(stdout)
    assert words[0::2] == ["--add-dir"] * (len(words) // 2)
    return [Path(word) for word in words[1::2]]


def watcher_git_commands() -> list[str]:
    spans = re.findall(r"`([^`\n]+)`", WATCHER.read_text())
    return [
        span for span in spans
        if span.startswith("git ") and not span.startswith(CODEX_COMMIT)
    ]


def test_main_checkout_is_refused(repo: dict[str, Path]) -> None:
    result = run_grants(repo["main"])

    assert result.returncode != 0
    assert result.stdout == ""
    assert "main checkout" in result.stderr


def test_linked_worktree_grants_skip_hooks_and_config(
    repo: dict[str, Path],
) -> None:
    common = repo["main"] / ".git"

    result = run_grants(repo["worktree"])

    assert result.returncode == 0, result.stderr
    grants = granted_paths(result.stdout)
    assert grants == [
        common / "objects",
        common / "refs",
        common / "logs",
        common / "worktrees" / "linked",
    ]
    for forbidden in (common / "hooks", common / "config"):
        assert not any(forbidden.is_relative_to(grant) for grant in grants)


def test_worktree_config_layout_is_granted(
    repo: dict[str, Path],
) -> None:
    git("config", "extensions.worktreeConfig", "true", cwd=repo["main"])

    result = run_grants(repo["worktree"])

    assert result.returncode == 0, result.stderr
    grants = granted_paths(result.stdout)
    shared = repo["main"] / ".git"
    for protected in (shared / "config", shared / "hooks"):
        assert not any(protected.is_relative_to(grant) for grant in grants)


def test_every_watcher_git_command_disables_hooks() -> None:
    commands = watcher_git_commands()

    assert len(commands) >= 5
    assert [cmd for cmd in commands if HOOKS_OFF not in cmd] == []


def test_watcher_push_skips_a_planted_pre_push_hook(
    repo: dict[str, Path], tmp_path: Path,
) -> None:
    worktree = repo["worktree"]
    marker = tmp_path / "hook-ran"
    hooks_dir = Path(
        git("rev-parse", "--path-format=absolute", "--git-path", "hooks",
            cwd=worktree)
    )
    hook = hooks_dir / "pre-push"
    hook.write_text(f"#!/bin/sh\ntouch {shlex.quote(str(marker))}\nexit 1\n")
    hook.chmod(0o755)
    planted = subprocess.run(
        ["git", "hook", "run", "pre-push"], cwd=worktree, capture_output=True
    )
    assert planted.returncode != 0 and marker.exists(), "hook is live"
    marker.unlink()
    [push] = [cmd for cmd in watcher_git_commands() if " push " in cmd]

    result = subprocess.run(
        ["bash", "-c", push.replace("<worktree>", shlex.quote(str(worktree)))],
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert git("rev-parse", "refs/heads/fix/unit", cwd=repo["remote"])
