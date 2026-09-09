"""Shared behaviour matrix for agent_isolation.py, run against both harness dialects.

Each Case in CASES describes one write or Bash command in one location.
build_payload() translates it into the Claude and the Copilot wire shape;
the same expect_deny lands on both, which is the "same behaviour" proof.
"""

from __future__ import annotations

import io
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


def commit_repo(root: Path) -> Path:
    run_git(["config", "user.email", "a@example.com"], root)
    run_git(["config", "user.name", "agent-isolation tests"], root)
    (root / "f.txt").write_text("x")
    run_git(["add", "."], root)
    run_git(["commit", "-q", "-m", "init"], root)
    return root


@pytest.fixture
def repo(tmp_path: Path) -> SimpleNamespace:
    main = tmp_path / "main"
    main.mkdir()
    run_git(["init", "-q"], main)
    commit_repo(main)
    worktree = tmp_path / "wt"
    run_git(["worktree", "add", "-q", str(worktree), "-b", "wt-branch"], main)
    return SimpleNamespace(main=main, worktree=worktree)


def deny_reason(harness: str, result: dict | None) -> str | None:
    if result is None:
        return None
    if harness == "claude":
        result = result["hookSpecificOutput"]
    if result["permissionDecision"] != "deny":
        return None
    return result["permissionDecisionReason"]


def is_deny(harness: str, result: dict | None) -> bool:
    return deny_reason(harness, result) is not None


@dataclass
class Case:
    name: str
    op: str  # "write" or "bash"
    command: str | None
    location: str
    expect_deny: bool
    reason_has: str = ""


MAIN = "Main checkout"
MISPLACED = "every agent worktree must live"
UNHOOKED = "WorktreeCreate hook"
UNLOCATABLE = "stops this guard locating the main checkout"

CASES = [
    Case("main-root-write", "write", None, "main_root", True, MAIN),
    Case("main-subdir-write", "write", None, "main_subdir", True, MAIN),
    Case("scratch-write", "write", None, "scratch", False),
    Case("scratch-bash", "bash", "tee -a notes.md", "scratch", False),
    Case("scratch-lookalike-write", "write", None, "scratch_lookalike", True, MAIN),
    Case("stray-worktree-write", "write", None, "stray", True, MISPLACED),
    Case("based-worktree-write", "write", None, "based", False),
    Case("escaping-worktree-write", "write", None, "escaping", True, MISPLACED),
    Case("claude-worktree-write", "write", None, "claude_default", True, UNHOOKED),
    Case("tmp-write", "write", None, "outside", False),
    Case("not-a-repo-write", "write", None, "not_repo", False),
    Case("container-write", "write", None, "container", False),
    Case("readonly-git-bash", "bash", "git status", "main_root", False),
    Case("merge-ffonly-bash", "bash", "git merge --ff-only other", "main_root", False),
    Case("commit-bash", "bash", "git commit -m x", "main_root", True, MAIN),
    Case("based-commit-bash", "bash", "git commit -m x", "based", False),
]


def add_worktree(repo: SimpleNamespace, path: Path, branch: str) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        run_git(["worktree", "add", "-q", str(path), "-b", branch], repo.main)
    return path


def location_dir(location: str, repo: SimpleNamespace, tmp_path: Path) -> Path:
    if location in ("main_root", "container"):
        return repo.main
    if location == "main_subdir":
        sub = repo.main / "sub"
        sub.mkdir(exist_ok=True)
        return sub
    if location == "stray":
        return repo.worktree
    if location == "scratch":
        scratch = repo.main / ".nikki-agents" / ".kb" / "wiki"
        scratch.mkdir(parents=True, exist_ok=True)
        return scratch
    if location == "scratch_lookalike":
        # Same prefix, different directory: must not inherit the allowance.
        lookalike = repo.main / ".nikki-agents-notes"
        lookalike.mkdir(exist_ok=True)
        return lookalike
    if location == "based":
        base = repo.main / ".nikki-agents" / "worktrees"
        return add_worktree(repo, base / "ok", "based-branch")
    if location == "escaping":
        # Lexically under the base, actually outside it once ".." resolves.
        add_worktree(repo, tmp_path / "escape", "escape-branch")
        inside = location_dir("based", repo, tmp_path)
        return inside / ".." / ".." / ".." / ".." / "escape"
    if location == "claude_default":
        claude = repo.main / ".claude" / "worktrees"
        return add_worktree(repo, claude / "agent-x", "claude-branch")
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
    reason = deny_reason(harness, result)
    assert (reason is not None) == case.expect_deny
    if case.reason_has:
        assert case.reason_has in reason


def test_main_checkout_reason_names_the_destination(repo):
    payload = {
        "agent_id": "a", "cwd": str(repo.main),
        "tool_name": "Write", "tool_input": {"file_path": str(repo.main / "x.txt")},
    }
    reason = deny_reason("claude", agent_isolation.process("claude", payload))
    base = repo.main / ".nikki-agents" / "worktrees"
    assert f"git worktree add {base}/" in reason


def write_payload(cwd: Path) -> dict:
    return {
        "agent_id": "a", "cwd": str(cwd),
        "tool_name": "Write", "tool_input": {"file_path": str(cwd / "x.txt")},
    }


def test_separate_git_dir_reason_names_the_checkout(tmp_path):
    """--separate-git-dir moves the admin directory out of the checkout."""
    root = (tmp_path / "main").resolve()
    root.mkdir()
    run_git(["init", "-q", f"--separate-git-dir={tmp_path / 'admin'}"], root)
    commit_repo(root)
    result = agent_isolation.process("claude", write_payload(root))
    reason = deny_reason("claude", result)
    assert reason is not None
    assert f"Main checkout ({root})" in reason
    assert str(root / ".nikki-agents" / "worktrees") in reason


def test_worktree_under_a_submodule_base_is_allowed(tmp_path):
    """A submodule keeps its admin directory under the superproject."""
    sub = (tmp_path / "sub").resolve()
    sub.mkdir()
    run_git(["init", "-q"], sub)
    commit_repo(sub)
    root = (tmp_path / "main").resolve()
    root.mkdir()
    run_git(["init", "-q"], root)
    commit_repo(root)
    run_git(
        ["-c", "protocol.file.allow=always",
         "submodule", "-q", "add", str(sub), "vendor"],
        root,
    )
    run_git(["commit", "-q", "-m", "add submodule"], root)
    vendor = root / "vendor"
    placed = vendor / ".nikki-agents" / "worktrees" / "ok"
    run_git(["worktree", "add", "-q", str(placed), "-b", "agent/ok"], vendor)
    result = agent_isolation.process("claude", write_payload(placed))
    assert deny_reason("claude", result) is None


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
    claude = json.loads((root / "hooks" / "hooks.json").read_text())
    json.loads((root / "hooks.json").read_text())
    for event in ("WorktreeCreate", "WorktreeRemove"):
        commands = [
            hook["command"]
            for entry in claude["hooks"][event]
            for hook in entry["hooks"]
        ]
        assert commands
        assert all(c.startswith("${CLAUDE_PLUGIN_ROOT}/") for c in commands)


def test_linked_worktree_of_a_separate_git_dir_repo_denies(tmp_path):
    """Repo present, root unnameable: a rule that cannot judge must refuse."""
    root = (tmp_path / "main").resolve()
    root.mkdir()
    run_git(["init", "-q", f"--separate-git-dir={tmp_path / 'admin'}"], root)
    commit_repo(root)
    linked = (root / ".nikki-agents" / "worktrees" / "ok").resolve()
    linked.parent.mkdir(parents=True)
    run_git(["worktree", "add", "-q", str(linked), "-b", "agent/ok"], root)
    result = agent_isolation.process("claude", write_payload(linked))
    reason = deny_reason("claude", result)
    assert reason is not None
    assert UNLOCATABLE in reason
    assert str(linked) in reason


def test_scratch_write_from_outside_the_scratch_directory_is_allowed(repo):
    """The agent's cwd is the main checkout; only the target decides."""
    scratch = repo.main / ".nikki-agents" / ".kb"
    scratch.mkdir(parents=True)
    payload = {
        "agent_id": "a", "cwd": str(repo.main),
        "tool_name": "Write", "tool_input": {"file_path": str(scratch / "note.md")},
    }
    assert deny_reason("claude", agent_isolation.process("claude", payload)) is None


def test_scratch_allowance_does_not_reach_a_traversal_out_of_it(repo):
    """A path that only looks like scratch until ".." resolves still denies."""
    scratch = repo.main / ".nikki-agents" / ".kb"
    scratch.mkdir(parents=True)
    escaped = scratch / ".." / ".." / "src.txt"
    payload = {
        "agent_id": "a", "cwd": str(repo.main),
        "tool_name": "Write", "tool_input": {"file_path": str(escaped)},
    }
    assert MAIN in deny_reason("claude", agent_isolation.process("claude", payload))


def test_an_exception_inside_the_guard_falls_through_to_allow(monkeypatch, capsys):
    """Copilot fails closed on a non-zero exit, so a crash must never deny."""
    def explode(*_args, **_kwargs):
        raise RuntimeError("guard is broken")

    monkeypatch.setattr(agent_isolation, "process", explode)
    monkeypatch.setattr(sys, "argv", ["agent_isolation.py", "--harness", "claude"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"agent_id": "a"})))
    assert agent_isolation.main() == 0
    assert capsys.readouterr().out == ""
