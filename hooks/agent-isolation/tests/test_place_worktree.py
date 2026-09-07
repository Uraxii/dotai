"""The WorktreeCreate / WorktreeRemove hook, run as Claude Code runs it.

In plain words: these tests make a throwaway git repo, feed the hook the same
message Claude Code sends it, and check that the agent's private copy of the
repo really appears in the folder we chose - and that a bad request is
refused instead of quietly landing somewhere else.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

TESTS_DIR = Path(__file__).parent
PLACE_WORKTREE_PATH = TESTS_DIR.parent / "place_worktree.py"
sys.path.insert(0, str(TESTS_DIR.parent))
import worktree_location  # noqa: E402


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True, capture_output=True, text=True,
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> SimpleNamespace:
    root = (tmp_path / "main").resolve()
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "a@example.com")
    git(root, "config", "user.name", "place-worktree tests")
    (root / "f.txt").write_text("x")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "init")
    return SimpleNamespace(root=root, head=git(root, "rev-parse", "HEAD"))


def run_hook(event: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PLACE_WORKTREE_PATH), "--event", event],
        input=json.dumps(payload), capture_output=True, text=True, timeout=60,
    )


def create(repo: SimpleNamespace, name: str) -> subprocess.CompletedProcess:
    return run_hook("create", {
        "session_id": "s1", "transcript_path": "/dev/null",
        "cwd": str(repo.root), "hook_event_name": "WorktreeCreate", "name": name,
    })


def printed_path(done: subprocess.CompletedProcess) -> Path:
    lines = [line.strip() for line in done.stdout.splitlines() if line.strip()]
    return Path(lines[-1])


def test_create_puts_the_worktree_in_the_base(repo) -> None:
    done = create(repo, "agent-1")
    assert done.returncode == 0, done.stderr
    dest = printed_path(done)
    assert dest == worktree_location.base_for(repo.root) / "agent-1"
    assert dest.is_dir()
    assert str(dest) in git(repo.root, "worktree", "list")


def test_create_checks_out_an_agent_branch(repo) -> None:
    dest = printed_path(create(repo, "agent-1"))
    assert git(dest, "rev-parse", "--abbrev-ref", "HEAD") == "agent/agent-1"
    assert git(dest, "rev-parse", "HEAD") == repo.head


def test_create_twice_returns_the_same_path(repo) -> None:
    first = create(repo, "agent-1")
    second = create(repo, "agent-1")
    assert second.returncode == 0, second.stderr
    assert printed_path(second) == printed_path(first)
    assert second.stderr == ""


def test_taken_branch_name_falls_back_to_a_sha_suffix(repo) -> None:
    git(repo.root, "branch", "agent/agent-1")
    dest = printed_path(create(repo, "agent-1"))
    branch = git(dest, "rev-parse", "--abbrev-ref", "HEAD")
    assert branch == "agent/agent-1-" + repo.head[:7]


def test_create_leaves_the_main_checkout_clean(repo) -> None:
    create(repo, "agent-1")
    assert git(repo.root, "status", "--porcelain") == ""


def worktree_git_dir(dest: Path) -> Path:
    return Path(git(dest, "rev-parse", "--absolute-git-dir"))


def exclude_file(repo: SimpleNamespace) -> Path:
    return repo.root / ".git" / "info" / "exclude"


def test_git_exclude_hides_the_base_under_our_own_marker(repo) -> None:
    create(repo, "agent-1")
    create(repo, "agent-2")
    text = exclude_file(repo).read_text()
    assert text.count("# dotai-worktrees") == 1
    assert "/.nikki-agents/" in text
    assert "# claude-code-runtime" not in text


def test_base_commit_is_recorded_in_the_worktree_admin_dir(repo) -> None:
    dest = printed_path(create(repo, "agent-1"))
    assert (worktree_git_dir(dest) / "CLAUDE_BASE").read_text().strip() == repo.head


def test_local_claude_settings_are_copied_into_the_worktree(repo) -> None:
    settings = repo.root / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    settings.write_text('{"permissions": {}}')
    dest = printed_path(create(repo, "agent-1"))
    copied = dest / ".claude" / "settings.local.json"
    assert copied.read_text() == '{"permissions": {}}'


def test_symlinked_claude_settings_are_left_behind(repo, tmp_path) -> None:
    real = tmp_path / "elsewhere.json"
    real.write_text("{}")
    settings = repo.root / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    settings.symlink_to(real)
    dest = printed_path(create(repo, "agent-1"))
    assert not (dest / ".claude" / "settings.local.json").exists()


def test_worktreeinclude_paths_are_copied(repo) -> None:
    (repo.root / ".worktreeinclude").write_text("notes.txt\nconf/\n")
    (repo.root / "notes.txt").write_text("carry me")
    (repo.root / "conf").mkdir()
    (repo.root / "conf" / "a.ini").write_text("k=v")
    dest = printed_path(create(repo, "agent-1"))
    assert (dest / "notes.txt").read_text() == "carry me"
    assert (dest / "conf" / "a.ini").read_text() == "k=v"


def test_relative_hooks_path_becomes_absolute(repo) -> None:
    git(repo.root, "config", "core.hooksPath", ".githooks")
    dest = printed_path(create(repo, "agent-1"))
    hooks_path = git(dest, "config", "--get", "core.hooksPath")
    assert hooks_path == str(repo.root / ".githooks")


def remove(repo: SimpleNamespace, target: Path) -> subprocess.CompletedProcess:
    return run_hook("remove", {
        "session_id": "s1", "transcript_path": "/dev/null",
        "cwd": str(repo.root), "hook_event_name": "WorktreeRemove",
        "worktree_path": str(target),
    })


def branches(repo: SimpleNamespace) -> str:
    return git(repo.root, "branch", "--list", "--format=%(refname:short)")


# Inverse of test_crash_path_exits_zero in test_agent_isolation.py, on
# purpose: that hook must never deny a session by crashing, this one must
# never let a worktree be created somewhere we did not choose. Do not
# "fix" the mismatch.
def test_unreadable_payload_refuses_and_prints_no_path() -> None:
    done = subprocess.run(
        [sys.executable, str(PLACE_WORKTREE_PATH), "--event", "create"],
        input="not json {{{", capture_output=True, text=True, timeout=30,
    )
    assert done.returncode != 0
    assert done.stdout == ""
    assert done.stderr.strip() != ""


def test_create_outside_a_repo_refuses_and_prints_no_path(tmp_path) -> None:
    loose = tmp_path / "loose"
    loose.mkdir()
    done = run_hook("create", {
        "cwd": str(loose), "hook_event_name": "WorktreeCreate", "name": "agent-1",
    })
    assert done.returncode != 0
    assert done.stdout == ""


def test_remove_deletes_a_worktree_from_the_base(repo) -> None:
    dest = printed_path(create(repo, "agent-1"))
    done = remove(repo, dest)
    assert done.returncode == 0, done.stderr
    assert not dest.exists()
    assert str(dest) not in git(repo.root, "worktree", "list")


def test_remove_refuses_a_path_outside_the_base(repo, tmp_path) -> None:
    stray = tmp_path / "stray"
    git(repo.root, "worktree", "add", "-q", str(stray), "-b", "stray-branch")
    done = remove(repo, stray)
    assert done.returncode != 0
    assert stray.is_dir()


def test_remove_drops_a_merged_agent_branch(repo) -> None:
    dest = printed_path(create(repo, "agent-1"))
    remove(repo, dest)
    assert "agent/agent-1" not in branches(repo)


def test_remove_keeps_a_branch_holding_unmerged_work(repo) -> None:
    dest = printed_path(create(repo, "agent-1"))
    (dest / "new.txt").write_text("agent work")
    git(dest, "add", ".")
    git(dest, "commit", "-q", "-m", "agent work")
    remove(repo, dest)
    assert "agent/agent-1" in branches(repo)
