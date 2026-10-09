"""The Codex watchers launch Codex detached, so killing the launching shell is harmless.

Claude Code kills a watcher's wrapper shell once its background-shell time
limit passes. The watcher's launch command must start Codex in its own
session and leave its exit code in `<TMP>/exit-code`, and the documented
pgrep wait must end with that code, or print `lost` when the wrapper died
without writing one. These tests read the run script and both commands from
the agent definitions and run them against a stub `codex`.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import textwrap
import time
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WATCHERS = ["developer-codex", "reviewer-codex"]
STUB_EXIT_CODE = 7
SHELLS = [["bash", "-c", "set -m; "], ["zsh", "-c", ""]]


@pytest.fixture(params=SHELLS, ids=["bash-job-control", "zsh"])
def shell_argv(request: pytest.FixtureRequest) -> list[str]:
    if shutil.which(request.param[0]) is None:
        pytest.skip(f"{request.param[0]} not installed")
    return request.param


def read_definition(watcher: str) -> str:
    return (PLUGIN_ROOT / f"agents/{watcher}.md").read_text()


def run_script(watcher: str) -> str:
    block = re.search(r"^   codex exec .*?^   mv [^\n]*", read_definition(watcher), re.M | re.S)
    assert block, f"{watcher}.md lacks a run.sh block"
    return textwrap.dedent(block.group(0)) + "\n"


def launch_command(watcher: str) -> str:
    launch = re.search(
        r"^   (?:export [^\n]*; )?(setsid nohup bash <TMP>/run\.sh [^\n]*)$",
        read_definition(watcher),
        re.M,
    )
    assert launch, f"{watcher}.md lacks a detached launch"
    return launch.group(0).strip()


def wait_command(watcher: str) -> str:
    wait = re.search(r"^   (sleep 1; while pgrep [^\n]*)$", read_definition(watcher), re.M)
    assert wait, f"{watcher}.md lacks a pgrep wait"
    return wait.group(1).replace("sleep 5", "sleep 0.2").replace("sleep 1;", "sleep 0.1;")


def fill(command: str, tmp: Path, adddirs: str = "", worktree: Path | None = None) -> str:
    return (
        command.replace("<TMP>", str(tmp))
        .replace("<actor>", "developer-x")
        .replace("<id>", "x-1")
        .replace("<MODEL>", "m")
        .replace("<worktree>", str(worktree or tmp))
        .replace("<ADDDIRS>", adddirs)
    )


def processes_naming(tmp: Path) -> list[str]:
    result = subprocess.run(["pgrep", "-f", str(tmp)], capture_output=True, text=True)
    return result.stdout.split()


def wrapper_pids(tmp: Path) -> list[int]:
    result = subprocess.run(["pgrep", "-f", f"^bash {tmp}/run\\.sh"], capture_output=True, text=True)
    return [int(pid) for pid in result.stdout.split()]


def wait_for(path: Path, what: str) -> None:
    deadline = time.monotonic() + 5
    while not path.exists():
        assert time.monotonic() < deadline, what
        time.sleep(0.05)


def wait_until_gone(tmp: Path, what: str) -> None:
    deadline = time.monotonic() + 3
    while processes_naming(tmp):
        assert time.monotonic() < deadline, what
        time.sleep(0.1)


def launch(
    watcher: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stub_seconds: int,
    shell_argv: list[str],
    worktree: Path | None = None,
    adddirs: str = "",
    linger: bool = True,
) -> tuple[Path, subprocess.Popen]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "codex"
    stub.write_text(
        "#!/bin/bash\n"
        f"printf '%s\\n' \"$@\" > {tmp_path}/work/args\n"
        f"echo $$ > {tmp_path}/work/stub-pid\n"
        f"sleep {stub_seconds}\n"
        f"exit {STUB_EXIT_CODE}\n"
    )
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    work = tmp_path / "work"
    work.mkdir()
    (work / "prompt.md").write_text("task")
    (work / "run.sh").write_text(fill(run_script(watcher), work, adddirs, worktree))
    script = fill(launch_command(watcher), work)
    if linger:
        script += "\nsleep 30"
    shell = subprocess.Popen([*shell_argv[:-1], shell_argv[-1] + script], start_new_session=True)
    wait_for(work / "stub-pid", "stub codex never started")
    return work, shell


@pytest.mark.parametrize("watcher", WATCHERS)
def test_codex_survives_launching_shell_kill(
    watcher: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shell_argv: list[str]
) -> None:
    work, shell = launch(watcher, tmp_path, monkeypatch, stub_seconds=2, shell_argv=shell_argv)
    os.killpg(shell.pid, signal.SIGKILL)
    shell.wait()

    waited = subprocess.run(
        ["bash", "-c", fill(wait_command(watcher), work)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert waited.stdout.split() == ["exited", str(STUB_EXIT_CODE)]
    assert (work / "exit-code").read_text().strip() == str(STUB_EXIT_CODE)
    assert not wrapper_pids(work)
    wait_until_gone(work, "launch or heartbeat process outlived codex")


@pytest.mark.parametrize("watcher", WATCHERS)
def test_dead_wrapper_ends_loops_and_prints_lost(
    watcher: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shell_argv: list[str]
) -> None:
    work, shell = launch(watcher, tmp_path, monkeypatch, stub_seconds=30, shell_argv=shell_argv, linger=False)
    wrappers = wrapper_pids(work)
    assert wrappers, "no live run.sh wrapper to kill"
    for pid in [*wrappers, int((work / "stub-pid").read_text())]:
        os.kill(pid, signal.SIGKILL)

    waited = subprocess.run(
        ["bash", "-c", fill(wait_command(watcher), work)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert waited.stdout.split() == ["exited", "lost"]
    assert not (work / "exit-code").exists()
    shell.wait()
    wait_until_gone(work, "heartbeat loop outlived the dead wrapper")


def test_worktree_and_adddirs_with_spaces_reach_codex_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shell_argv: list[str]
) -> None:
    worktree = tmp_path / "my work tree"
    worktree.mkdir()
    work, shell = launch(
        "developer-codex",
        tmp_path,
        monkeypatch,
        stub_seconds=0,
        shell_argv=shell_argv,
        worktree=worktree,
        adddirs=f"--add-dir '{tmp_path}/grant dir'",
    )
    subprocess.run(
        ["bash", "-c", fill(wait_command("developer-codex"), work)],
        capture_output=True,
        timeout=5,
    )
    args = (work / "args").read_text().splitlines()
    assert args[args.index("-C") + 1] == str(worktree)
    assert args[args.index("--add-dir") + 1] == f"{tmp_path}/grant dir"
    os.killpg(shell.pid, signal.SIGKILL)
    shell.wait()
