"""The real Codex watcher, run by a real `claude -p`, outlives a shrunk Bash timeout.

Opt-in: set PSTACK_WATCHER_E2E=1. It spends model tokens and needs `claude`, `bd`,
and a logged-in Claude Code. A stub `codex` sleeps past the shrunk Bash timeout,
commits in a linked worktree, and exits 0. The watcher must still reply with
that exit code and commit.

BASH_DEFAULT_TIMEOUT_MS and BASH_MAX_TIMEOUT_MS shrink the foreground Bash
timeout, so a Bash call that runs Codex inline moves to the background after a
few seconds. No variable shrinks the background time limit itself (30 minutes,
10 under `claude -p`; BASH_DEFAULT_TIMEOUT_MS can only raise it), so this test
cannot prove survival past that limit. The watcher never keeps Codex in a shell
that limit could kill, because it launches Codex detached.

PSTACK_WATCHER_E2E_PLUGIN_DIR points the run at another pstack tree, for
example an extracted older release, to confirm the test fails on it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = Path(os.environ.get("PSTACK_WATCHER_E2E_PLUGIN_DIR", PLUGIN_ROOT))
BASH_LIMIT_MS = 3000
STUB_SECONDS = 40
CLAUDE_TIMEOUT_SECONDS = 150

pytestmark = pytest.mark.skipif(
    os.environ.get("PSTACK_WATCHER_E2E") != "1"
    or shutil.which("claude") is None
    or shutil.which("bd") is None,
    reason="set PSTACK_WATCHER_E2E=1 with claude and bd on PATH",
)

STUB_CODEX = f"""#!/bin/bash
case "$1" in
  --version) echo "codex-cli stub"; exit 0 ;;
  login) echo "Logged in using stub"; exit 0 ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in -C) worktree=$2; shift ;; -o) last=$2; shift ;; esac
  shift
done
bead=$(sed -n 's/^Do the task in bead \\([^ .]*\\)\\..*/\\1/p' | head -1)
sleep {STUB_SECONDS}
echo stub > "$worktree/stub-output"
git -c core.hooksPath=/dev/null -C "$worktree" add stub-output
git -c core.hooksPath=/dev/null -C "$worktree" commit -q -m "stub work ($bead)"
echo "stub finished" > "$last"
"""


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def make_bead(store: Path) -> str:
    store.mkdir()
    git("init", "-q", cwd=store)
    env = {**os.environ, "BEADS_DIR": str(store / ".beads")}
    subprocess.run(["bd", "init", "-q", "--prefix", "t"], cwd=store, env=env, check=True, capture_output=True)
    created = subprocess.run(
        ["bd", "create", "-t", "task", "--title", "stub task", "--description", "write a file",
         "--acceptance", "a commit", "--silent"],
        cwd=store, env=env, check=True, capture_output=True, text=True,
    )
    return created.stdout.strip()


def test_watcher_survives_shrunk_bash_timeout(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    git("commit", "-q", "--allow-empty", "-m", "init", cwd=repo)
    worktree = tmp_path / "worktree"
    git("worktree", "add", "-q", "-b", "task", str(worktree), cwd=repo)
    before = git("rev-parse", "HEAD", cwd=worktree)

    bead = make_bead(tmp_path / "store")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "codex"
    stub.write_text(STUB_CODEX)
    stub.chmod(0o755)

    actor = f"developer-{bead}"
    watcher_prompt = f"Claim bead {bead} as {actor}. Work in {worktree}."
    ask = (
        "Call the Agent tool exactly once with subagent_type pstack:developer-codex and this "
        f"prompt, verbatim: {watcher_prompt}\n"
        "Wait for the agent to finish. Then print its final reply verbatim and nothing else."
    )
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "BEADS_DIR": str(tmp_path / "store" / ".beads"),
        "BASH_DEFAULT_TIMEOUT_MS": str(BASH_LIMIT_MS),
        "BASH_MAX_TIMEOUT_MS": str(BASH_LIMIT_MS),
    }
    result = subprocess.run(
        ["claude", "-p", ask, "--plugin-dir", str(PLUGIN_DIR), "--setting-sources", "project",
         "--permission-mode", "bypassPermissions", "--model", "sonnet"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_SECONDS,
    )
    reply = result.stdout

    commit = git("log", "-1", "--format=%H %s", cwd=worktree)
    assert commit.endswith(f"stub work ({bead})"), f"stub never committed: {commit}\n{reply}"
    sha = commit.split()[0]
    assert sha != before
    assert re.search(r"^fallback: none$", reply, re.M), reply
    assert re.search(r"^exit code: 0$", reply, re.M), reply
    assert re.search(rf"^commit: {sha}$", reply, re.M), reply
