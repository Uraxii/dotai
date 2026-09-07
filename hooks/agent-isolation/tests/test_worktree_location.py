"""Where an agent worktree is allowed to live, and what counts as inside it.

In plain words: these tests pin the one rule every tool shares - agent
worktrees go in a fixed folder under the repo - and check that a path
dressed up with ".." to look like it is in that folder is caught.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
sys.path.insert(0, str(TESTS_DIR.parent))
import worktree_location  # noqa: E402


def test_default_base_sits_under_nikki_agents(tmp_path: Path) -> None:
    expected = tmp_path / ".nikki-agents" / "worktrees"
    assert worktree_location.base_for(tmp_path) == expected


def test_env_override_is_read_relative_to_repo_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOTAI_WORKTREE_BASE", "scratch/trees")
    assert worktree_location.base_for(tmp_path) == tmp_path / "scratch" / "trees"


def test_child_of_base_is_inside(tmp_path: Path) -> None:
    target = worktree_location.base_for(tmp_path) / "agent-42"
    assert worktree_location.is_inside_base(target, tmp_path)


def test_dot_dot_escape_from_base_is_outside(tmp_path: Path) -> None:
    base = worktree_location.base_for(tmp_path)
    escape = base / "x" / ".." / ".." / ".." / "elsewhere"
    assert not worktree_location.is_inside_base(escape, tmp_path)


def test_sibling_of_base_is_outside(tmp_path: Path) -> None:
    assert not worktree_location.is_inside_base(tmp_path / "elsewhere", tmp_path)
