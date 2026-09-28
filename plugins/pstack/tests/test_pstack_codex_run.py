"""`bin/pstack-codex-run` against a fake `codex` that records each call."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "bin/pstack-codex-run"
RULES_FILE = PLUGIN_ROOT / "bin/pstack-codex-writer.rules"
FAKE_CODEX = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
record = {
    "argv": args,
    "codex_home": os.environ.get("CODEX_HOME"),
    "stdin": sys.stdin.read(),
}
with open(os.environ["FAKE_CODEX_RECORD"], "a") as out:
    out.write(json.dumps(record) + "\\n")
print("codex noise on stdout")
print("codex noise on stderr", file=sys.stderr)
failing = os.environ.get("FAKE_CODEX_FAIL")
sys.exit(1 if failing and " ".join(args).startswith(failing) else 0)
"""


class Sandbox:
    """A runs root with one run, a fake codex on PATH, and a codex home."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "repo" / ".agent-runs"
        self.run = self.root / "sample-run-0a1b2c3d"
        self.worktree = self.run / "worktree"
        self.worktree.mkdir(parents=True)
        (self.worktree / ".git").write_text("gitdir: elsewhere\n")
        self.codex_home = tmp_path / "codex-home"
        self.record = tmp_path / "calls.jsonl"
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake = fake_bin / "codex"
        fake.write_text(FAKE_CODEX)
        fake.chmod(0o755)
        self.env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"AGENT_RUNS_DIR", "FAKE_CODEX_FAIL"}
        }
        self.env.update(
            PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            PSTACK_CODEX_HOME=str(self.codex_home),
            FAKE_CODEX_RECORD=str(self.record),
        )

    @property
    def installed_rules(self) -> Path:
        return self.codex_home / "rules" / "pstack-codex-writer.rules"

    def brief(self, *lines: str, body: str = "Do the task.\n") -> str:
        text = "\n".join(("---", *lines, "---", "", body))
        (self.run / "brief.md").write_text(text)
        return text

    def writer_brief(self, *extra: str) -> str:
        return self.brief("kind: writer", f"worktree: {self.worktree}", *extra)

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(CLI), *args], capture_output=True, text=True, env=self.env
        )

    def calls(self) -> list[dict]:
        if not self.record.exists():
            return []
        return [json.loads(line) for line in self.record.read_text().splitlines()]


def keyed(stdout: str) -> dict[str, str]:
    return dict(line.split(": ", 1) for line in stdout.splitlines())


@pytest.fixture
def box(tmp_path: Path) -> Sandbox:
    return Sandbox(tmp_path)


def assert_refused(result: subprocess.CompletedProcess, reason_part: str) -> None:
    assert result.returncode == 1
    lines = keyed(result.stdout)
    assert lines["fallback"] == "claude"
    assert lines["command"] == "(none)"
    assert lines["exit code"] == "(none)"
    assert reason_part in lines["reason"]


def test_writer_runs_preflight_then_exec_with_the_exact_argv(box) -> None:
    brief = box.writer_brief("model: gpt-5.6-terra")

    result = box.cli(str(box.run))

    expected = [
        "exec", "-m", "gpt-5.6-terra", "-s", "workspace-write",
        "-c", "agents.enabled=false", "-C", str(box.worktree),
        "--add-dir", str(box.run), "-o", f"{box.run}/report.md", "-",
    ]
    calls = box.calls()
    assert [call["argv"] for call in calls] == [
        ["--version"], ["login", "status"], expected
    ]
    assert {call["codex_home"] for call in calls} == {str(box.codex_home)}
    assert calls[2]["stdin"] == brief
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "fallback: none",
        "command: codex " + " ".join(expected),
        "exit code: 0",
    ]


def assert_bundled_rules_installed(box) -> None:
    rules = box.installed_rules
    assert not rules.is_symlink()
    assert rules.is_file()
    assert rules.read_bytes() == RULES_FILE.read_bytes()
    assert [p.name for p in rules.parent.iterdir()] == [rules.name]


def test_writer_copies_the_bundled_rules_into_codex_home(box) -> None:
    box.writer_brief()

    box.cli(str(box.run))

    assert_bundled_rules_installed(box)


# The atomic os.replace is not race-tested on purpose: a race test would be
# flaky. It matters because parallel writers share one CODEX_HOME, and none of
# them may see the rules file missing or half-written.
@pytest.mark.parametrize("stale_kind", ["symlink", "stale-file"])
def test_writer_replaces_old_rules(box, tmp_path, stale_kind) -> None:
    box.writer_brief()
    box.installed_rules.parent.mkdir(parents=True)
    stale = tmp_path / "stale.rules"
    stale.write_text("# stale\n")
    if stale_kind == "symlink":
        box.installed_rules.symlink_to(stale)
    else:
        box.installed_rules.write_text("# stale\n")

    box.cli(str(box.run))

    assert_bundled_rules_installed(box)
    assert stale.read_text() == "# stale\n"


def test_reviewer_runs_read_only_without_rules(box, tmp_path) -> None:
    reviewed = tmp_path / "anywhere"
    reviewed.mkdir()
    box.brief("kind: reviewer", f"worktree: {reviewed}")

    result = box.cli(str(box.run))

    assert result.returncode == 0
    assert box.calls()[2]["argv"] == [
        "exec", "-s", "read-only", "--ignore-rules",
        "-c", "agents.enabled=false", "-C", str(reviewed),
        "-o", f"{box.run}/report.md", "-",
    ]
    assert not box.codex_home.exists()


def test_no_model_means_no_model_flag(box) -> None:
    box.writer_brief()

    box.cli(str(box.run))

    exec_argv = box.calls()[2]["argv"]
    assert "-m" not in exec_argv
    assert exec_argv[1:3] == ["-s", "workspace-write"]


def test_codex_output_goes_to_the_log_not_stdout(box) -> None:
    box.writer_brief()

    result = box.cli(str(box.run))

    assert "noise" not in result.stdout + result.stderr
    log = (box.run / "codex-exec.log").read_text()
    assert log.count("codex noise on stdout") == 3


@pytest.mark.parametrize(
    "run_of",
    [
        lambda box, tmp: tmp / "elsewhere",
        lambda box, tmp: box.root,
        lambda box, tmp: Path(f"{box.run}/../.."),
    ],
    ids=["outside-root", "root-itself", "dotdot-escape"],
)
def test_run_outside_the_runs_root_is_refused(box, tmp_path, run_of) -> None:
    run = run_of(box, tmp_path)
    run.mkdir(exist_ok=True)

    result = box.cli(str(run))

    assert_refused(result, "not inside the runs root")
    assert box.calls() == []


def test_relative_run_is_refused(box) -> None:
    box.writer_brief()

    assert_refused(box.cli("sample-run-0a1b2c3d"), "not an absolute path")


def test_agent_runs_dir_replaces_the_default_root(box, tmp_path) -> None:
    box.writer_brief()
    box.env["AGENT_RUNS_DIR"] = str(tmp_path / "configured")

    assert_refused(box.cli(str(box.run)), "not inside the runs root")

    box.env["AGENT_RUNS_DIR"] = str(box.run.parent.parent)
    assert box.cli(str(box.run)).returncode == 0


def test_writer_worktree_outside_the_runs_root_is_refused(box, tmp_path) -> None:
    outside = tmp_path / "outside-worktree"
    outside.mkdir()
    (outside / ".git").write_text("gitdir: elsewhere\n")
    box.brief("kind: writer", f"worktree: {outside}")

    assert_refused(box.cli(str(box.run)), "not inside the runs root")
    assert box.calls() == []
    assert not box.codex_home.exists()


def test_writer_worktree_without_git_is_refused(box) -> None:
    (box.worktree / ".git").unlink()
    box.writer_brief()

    assert_refused(box.cli(str(box.run)), "has no .git")


@pytest.mark.parametrize(
    "write_brief, reason_part",
    [
        (None, "brief.md cannot be read"),
        ("no frontmatter here\n", "no frontmatter"),
        ("---\nkind: writer\n", "no frontmatter"),
        ("---\nworktree: /x\n---\n", "is not writer or reviewer"),
        ("---\nkind: writer\n---\n", "no absolute worktree"),
    ],
    ids=["missing", "no-fence", "unclosed", "no-kind", "no-worktree"],
)
def test_bad_brief_is_refused(box, write_brief, reason_part) -> None:
    if write_brief is not None:
        (box.run / "brief.md").write_text(write_brief)

    assert_refused(box.cli(str(box.run)), reason_part)
    assert box.calls() == []


def test_failed_login_status_stops_before_exec(box) -> None:
    box.writer_brief()
    box.env["FAKE_CODEX_FAIL"] = "login status"

    result = box.cli(str(box.run))

    assert result.returncode == 1
    lines = keyed(result.stdout)
    assert lines["fallback"] == "claude"
    assert lines["command"] == "codex login status"
    assert lines["exit code"] == "1"
    assert [call["argv"][0] for call in box.calls()] == ["--version", "login"]


def test_failed_exec_falls_back_with_its_command(box) -> None:
    box.writer_brief()
    box.env["FAKE_CODEX_FAIL"] = "exec"

    result = box.cli(str(box.run))

    assert result.returncode == 1
    lines = keyed(result.stdout)
    assert lines["fallback"] == "claude"
    assert lines["command"].startswith("codex exec ")
    assert f"-C {box.worktree} " in lines["command"]
    assert lines["exit code"] == "1"


def test_missing_codex_falls_back(box, tmp_path) -> None:
    box.writer_brief()
    python_only = tmp_path / "python-only"
    python_only.mkdir()
    (python_only / "python3").symlink_to(sys.executable)
    box.env["PATH"] = str(python_only)

    result = box.cli(str(box.run))

    lines = keyed(result.stdout)
    assert lines["command"] == "codex --version"
    assert lines["exit code"] == "(none)"
    assert lines["reason"] == "codex is not on PATH"


RULE_CASES = {
    "git add src/a.gd": "allow",
    "git commit -m probe": "allow",
    "git push origin main": None,
    "git -C /tmp/x commit -m x": None,
    "git -c core.hooksPath=/tmp commit -m x": None,
    "git reset --hard": None,
}


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex not on PATH")
@pytest.mark.parametrize("command, decision", RULE_CASES.items())
def test_rules_allow_only_plain_git_add_and_commit(command, decision) -> None:
    result = subprocess.run(
        ["codex", "execpolicy", "check", "--rules", str(RULES_FILE), "--",
         *command.split()],
        capture_output=True, text=True, check=True,
    )

    assert json.loads(result.stdout).get("decision") == decision
