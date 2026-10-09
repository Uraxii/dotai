"""The real Codex watcher, run by a real `claude -p`, launches Codex and ends with the bead done.

Opt-in: set PSTACK_WATCHER_E2E=1. It spends model tokens and needs `claude`, `bd`,
and a logged-in Claude Code. A stub `codex` stands in for Codex: it sleeps past
the shrunk Bash timeout, then does Codex's part with real `bd` and `git` (claim,
commit, close). The watcher returns no reply, so the test asserts the bead
outcome and the commit.

BASH_DEFAULT_TIMEOUT_MS and BASH_MAX_TIMEOUT_MS shrink the foreground Bash
timeout, so a Bash call that runs Codex inline moves to the background after a
few seconds. The watcher never keeps Codex in a shell that limit could kill,
because it launches Codex detached.

An empty ZDOTDIR keeps the user's .zshrc out of the first Bash call, and
--strict-mcp-config skips MCP server startup. The parent runs on Haiku to speed up
token processing.

PSTACK_WATCHER_E2E_PLUGIN_DIR points the run at another pstack tree.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = Path(os.environ.get("PSTACK_WATCHER_E2E_PLUGIN_DIR", PLUGIN_ROOT))
BASH_LIMIT_MS = 1000
STUB_SECONDS = 15
CLAUDE_TIMEOUT_SECONDS = 150
FAST_MODEL = "haiku"

pytestmark = pytest.mark.skipif(
    os.environ.get("PSTACK_WATCHER_E2E") != "1"
    or shutil.which("claude") is None
    or shutil.which("bd") is None,
    reason="set PSTACK_WATCHER_E2E=1 with claude and bd on PATH",
)

STUB_CODEX = f"""#!/bin/bash
while [ $# -gt 0 ]; do
  case "$1" in -C) worktree=$2; shift ;; -o) last=$2; shift ;; esac
  shift
done
bead=$(sed -n 's/^You are the writer for bead \\([^ ]*\\) *\\. .*/\\1/p' | head -1)
sleep {STUB_SECONDS}
bd update "$bead" --claim
echo stub > "$worktree/stub-output"
git -C "$worktree" add stub-output
git -C "$worktree" commit -q -m "stub work ($bead)" --trailer "Executed-By: $BD_ACTOR"
bd close "$bead" --reason "stub done"
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
        "Wait for the agent to finish, then reply with the word done."
    )
    zdotdir = tmp_path / "zdotdir"
    zdotdir.mkdir()
    env = {
        **os.environ,
        "ZDOTDIR": str(zdotdir),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "BEADS_DIR": str(tmp_path / "store" / ".beads"),
        "BASH_DEFAULT_TIMEOUT_MS": str(BASH_LIMIT_MS),
        "BASH_MAX_TIMEOUT_MS": str(BASH_LIMIT_MS),
    }
    result = subprocess.run(
        ["claude", "-p", ask, "--plugin-dir", str(PLUGIN_DIR), "--setting-sources", "project",
         "--permission-mode", "bypassPermissions", "--model", FAST_MODEL,
         "--strict-mcp-config"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, result.stderr

    commit = git("log", "-1", "--format=%H %s", cwd=worktree)
    assert commit.endswith(f"stub work ({bead})"), f"stub never committed: {commit}\n{result.stdout}"
    assert commit.split()[0] != before
    shown = json.loads(subprocess.run(["bd", "show", bead, "--json"], env=env, capture_output=True,
                                      text=True, check=True).stdout)
    assert (shown[0] if isinstance(shown, list) else shown)["status"] == "closed"
