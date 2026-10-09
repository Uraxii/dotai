"""The Codex watchers launch Codex detached, so killing the launching shell is harmless.

Claude Code kills a watcher's wrapper shell once its background-shell time
limit passes. The watcher's launch command must start Codex in its own
session and leave its exit code in `<TMP>/exit-code`, and the documented
Monitor loop must read that code. These tests read both commands from the
agent definitions and run them against a stub `codex`.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WATCHERS = ["developer-codex", "reviewer-codex"]
STUB_EXIT_CODE = 7


def fenced_commands(watcher: str) -> tuple[str, str]:
    text = (PLUGIN_ROOT / f"agents/{watcher}.md").read_text()
    launch = re.search(r"^   (?:export [^\n]*; )?(setsid nohup [^\n]*)$", text, re.M)
    wait = re.search(r"^   (until \[ -e [^\n]*)$", text, re.M)
    assert launch and wait, f"{watcher}.md lacks a detached launch or an until-loop wait"
    return launch.group(0).strip(), wait.group(1)


def fill(command: str, tmp: Path) -> str:
    return (
        command.replace("<TMP>", str(tmp))
        .replace("<actor>", "developer-x")
        .replace("<id>", "x-1")
        .replace("<MODEL>", "m")
        .replace("<worktree>", str(tmp))
        .replace("<ADDDIRS>", "")
    )


def processes_naming(tmp: Path) -> list[str]:
    result = subprocess.run(["pgrep", "-f", str(tmp)], capture_output=True, text=True)
    return result.stdout.split()


@pytest.mark.parametrize("watcher", WATCHERS)
def test_codex_survives_launching_shell_kill(
    watcher: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    started = tmp_path / "started"
    stub = bin_dir / "codex"
    stub.write_text(f"#!/bin/bash\ntouch {started}\nsleep 2\nexit {STUB_EXIT_CODE}\n")
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    work = tmp_path / "work"
    work.mkdir()
    (work / "prompt.md").write_text("task")

    launch, wait = fenced_commands(watcher)
    shell = subprocess.Popen(
        ["bash", "-c", f"{fill(launch, work)}\nsleep 30"], start_new_session=True
    )
    deadline = time.monotonic() + 5
    while not started.exists():
        assert time.monotonic() < deadline, "stub codex never started"
        time.sleep(0.05)

    os.killpg(shell.pid, signal.SIGKILL)
    shell.wait()

    waited = subprocess.run(
        ["bash", "-c", fill(wait, work)], capture_output=True, text=True, timeout=10
    )
    assert waited.stdout.strip() == str(STUB_EXIT_CODE)
    assert (work / "exit-code").read_text().strip() == str(STUB_EXIT_CODE)

    deadline = time.monotonic() + 3
    while processes_naming(work):
        assert time.monotonic() < deadline, "launch or heartbeat process outlived codex"
        time.sleep(0.1)
