"""Where an agent worktree is allowed to live, and what counts as inside it.

In plain words: these tests pin the one rule every tool shares - agent
worktrees go in a fixed folder under the repo - and check that a path
dressed up with ".." to look like it is in that folder is caught.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
sys.path.insert(0, str(TESTS_DIR.parent))
import worktree_location  # noqa: E402


def test_default_base_sits_under_nikki_agents(tmp_path: Path) -> None:
    expected = tmp_path / ".nikki-agents" / "worktrees"
    assert worktree_location.base_for(tmp_path) == expected


def test_env_override_is_read_relative_to_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOTAI_WORKTREE_BASE", "scratch/trees")
    expected = tmp_path / "scratch" / "trees"
    assert worktree_location.base_for(tmp_path) == expected


def test_child_of_base_is_inside(tmp_path: Path) -> None:
    target = worktree_location.base_for(tmp_path) / "agent-42"
    assert worktree_location.is_inside_base(target, tmp_path)


def test_dot_dot_escape_from_base_is_outside(tmp_path: Path) -> None:
    base = worktree_location.base_for(tmp_path)
    escape = base / "x" / ".." / ".." / ".." / "elsewhere"
    assert not worktree_location.is_inside_base(escape, tmp_path)


def test_sibling_of_base_is_outside(tmp_path: Path) -> None:
    sibling = tmp_path / "elsewhere"
    assert not worktree_location.is_inside_base(sibling, tmp_path)


def test_absolute_base_override_is_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOTAI_WORKTREE_BASE", "/abs/trees")
    with pytest.raises(ValueError, match="DOTAI_WORKTREE_BASE"):
        worktree_location.base_for(tmp_path)


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True, capture_output=True, text=True,
    )
    return done.stdout.strip()


def commit_repo(root: Path) -> Path:
    git(root, "config", "user.email", "a@example.com")
    git(root, "config", "user.name", "worktree-location tests")
    (root / "f.txt").write_text("x")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "init")
    return root


def test_main_checkout_root_of_a_plain_repo_is_the_checkout(tmp_path) -> None:
    root = (tmp_path / "main").resolve()
    root.mkdir()
    git(root, "init", "-q")
    commit_repo(root)
    assert worktree_location.main_checkout_root(root) == root


def test_main_checkout_root_seen_from_a_linked_worktree(tmp_path) -> None:
    root = (tmp_path / "main").resolve()
    root.mkdir()
    git(root, "init", "-q")
    commit_repo(root)
    linked = (tmp_path / "linked").resolve()
    git(root, "worktree", "add", "-q", str(linked), "-b", "side")
    assert worktree_location.main_checkout_root(linked) == root


def test_main_checkout_root_of_a_submodule_is_the_submodule(tmp_path) -> None:
    sub = (tmp_path / "sub").resolve()
    sub.mkdir()
    git(sub, "init", "-q")
    commit_repo(sub)
    root = (tmp_path / "main").resolve()
    root.mkdir()
    git(root, "init", "-q")
    commit_repo(root)
    git(root, "-c", "protocol.file.allow=always",
        "submodule", "-q", "add", str(sub), "vendor")
    git(root, "commit", "-q", "-m", "add submodule")
    inside = root / "vendor"
    assert worktree_location.main_checkout_root(inside) == inside


def test_main_checkout_root_with_a_separate_git_dir(tmp_path) -> None:
    root = (tmp_path / "main").resolve()
    root.mkdir()
    admin = (tmp_path / "admin").resolve()
    git(root, "init", "-q", f"--separate-git-dir={admin}")
    commit_repo(root)
    assert worktree_location.main_checkout_root(root) == root


def test_separate_git_dir_seen_from_a_linked_worktree_refuses(tmp_path) -> None:
    """git itself cannot name that main checkout, so refuse, never guess."""
    root = (tmp_path / "main").resolve()
    root.mkdir()
    git(root, "init", "-q", f"--separate-git-dir={tmp_path / 'admin'}")
    commit_repo(root)
    linked = (tmp_path / "linked").resolve()
    git(root, "worktree", "add", "-q", str(linked), "-b", "side")
    with pytest.raises(ValueError):
        worktree_location.main_checkout_root(linked)
