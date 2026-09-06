"""Shared behaviour matrix for agent_isolation.py, run against both harness dialects.

Each Case in CASES describes one write or Bash command in one location.
build_payload() translates it into the Claude and the Copilot wire shape;
the same expect_deny lands on both, which is the "same behaviour" proof.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

TESTS_DIR = Path(__file__).parent
AGENT_ISOLATION_PATH = TESTS_DIR.parent / "agent_isolation.py"
sys.path.insert(0, str(AGENT_ISOLATION_PATH.parent))
import agent_isolation  # noqa: E402


def run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> SimpleNamespace:
    main = tmp_path / "main"
    main.mkdir()
    run_git(["init", "-q"], main)
    run_git(["config", "user.email", "a@example.com"], main)
    run_git(["config", "user.name", "agent-isolation tests"], main)
    (main / "f.txt").write_text("x")
    run_git(["add", "."], main)
    run_git(["commit", "-q", "-m", "init"], main)
    worktree = tmp_path / "wt"
    run_git(["worktree", "add", "-q", str(worktree), "-b", "wt-branch"], main)
    return SimpleNamespace(main=main, worktree=worktree)


def is_deny(harness: str, result: dict | None) -> bool:
    if result is None:
        return False
    if harness == "claude":
        return result["hookSpecificOutput"]["permissionDecision"] == "deny"
    return result["permissionDecision"] == "deny"


@dataclass
class Case:
    name: str
    op: str  # "write" or "bash"
    command: str | None
    location: str
    expect_deny: bool


CASES = [
    Case("main-root-write", "write", None, "main_root", True),
    Case("main-subdir-write", "write", None, "main_subdir", True),
    Case("worktree-write", "write", None, "worktree", False),
    Case("tmp-write", "write", None, "outside", False),
    Case("not-a-repo-write", "write", None, "not_repo", False),
    Case("container-write", "write", None, "container", False),
    Case("readonly-git-bash", "bash", "git status", "main_root", False),
    Case("merge-ffonly-bash", "bash", "git merge --ff-only other", "main_root", False),
    Case("commit-bash", "bash", "git commit -m x", "main_root", True),
]


def location_dir(location: str, repo: SimpleNamespace, tmp_path: Path) -> Path:
    if location in ("main_root", "container"):
        return repo.main
    if location == "main_subdir":
        sub = repo.main / "sub"
        sub.mkdir(exist_ok=True)
        return sub
    if location == "worktree":
        return repo.worktree
    if location == "outside":
        d = tmp_path / "outside"
        d.mkdir(exist_ok=True)
        return d
    if location == "not_repo":
        d = tmp_path / "not_repo"
        d.mkdir(exist_ok=True)
        return d
    raise ValueError(location)


def build_payload(harness: str, case: Case, target_dir: Path, actor_key: str) -> dict:
    cwd = str(target_dir)
    if case.op == "write":
        path = str(target_dir / "new.txt")
        if harness == "claude":
            return {
                "agent_id": actor_key, "cwd": cwd,
                "tool_name": "Write", "tool_input": {"file_path": path},
            }
        return {
            "sessionId": actor_key, "cwd": cwd,
            "toolName": "create", "toolArgs": {"path": path},
        }
    if harness == "claude":
        return {
            "agent_id": actor_key, "cwd": cwd,
            "tool_name": "Bash", "tool_input": {"command": case.command},
        }
    return {
        "sessionId": actor_key, "cwd": cwd,
        "toolName": "bash", "toolArgs": {"command": case.command},
    }


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
@pytest.mark.parametrize("harness", ["claude", "copilot"])
def test_matrix(harness, case, repo, tmp_path, monkeypatch):
    if case.location == "container":
        marker = tmp_path / "containerenv"
        marker.write_text("")
        monkeypatch.setattr(agent_isolation, "CONTAINER_MARKERS", (str(marker),))
    target_dir = location_dir(case.location, repo, tmp_path)
    payload = build_payload(harness, case, target_dir, f"{harness}-{case.name}")
    result = agent_isolation.process(harness, payload)
    assert is_deny(harness, result) == case.expect_deny


def test_main_thread_never_denied(repo):
    payload = {
        "agent_id": None, "cwd": str(repo.main),
        "tool_name": "Write", "tool_input": {"file_path": str(repo.main / "x.txt")},
    }
    assert not is_deny("claude", agent_isolation.process("claude", payload))


def test_crash_path_exits_zero():
    result = subprocess.run(
        [sys.executable, str(AGENT_ISOLATION_PATH), "--harness", "claude"],
        input="not json {{{", capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_hooks_configs_are_valid_json():
    root = AGENT_ISOLATION_PATH.parent.parent.parent
    json.loads((root / "hooks" / "hooks.json").read_text())
    json.loads((root / "hooks.json").read_text())
