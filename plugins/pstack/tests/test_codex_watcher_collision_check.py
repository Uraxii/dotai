"""Regression tests for the collision check in `delegate-to-codex.md`.

A plain `pgrep -af "codex exec"` has two failure modes: it can self-match an
ancestor process whose own command line happens to carry that text, and it
false-positives on any unrelated process carrying the same substring. The
playbook keys the check to the worktree instead, since `-C <worktree>`
survives verbatim into the live process's argv once `codex-agent` execs the
codex binary. These tests run the playbook's own pattern against real
processes, not just against the pattern text.
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = PLUGIN_ROOT / "skills/poteto-mode/playbooks/delegate-to-codex.md"


def collision_check_template() -> str:
    """The worktree-keyed `pgrep` command, read from the playbook.

    Reading it from the file, instead of keeping a hardcoded copy here,
    keeps this test honest if the playbook's pattern ever changes.
    """
    text = PLAYBOOK.read_text()
    match = re.search(r"`(pgrep -af -- \"codex exec[^`]*)`", text)
    assert match, "delegate-to-codex.md has no worktree-keyed pgrep command"
    return match.group(1)


def run_collision_check(worktree: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    """Run the playbook's collision check for `worktree` from a script file.

    A literal `bash -c "pgrep -af -- \\"codex exec...\\""` would put the text
    `codex exec` into bash's own argv, the exact false match this check
    exists to avoid. A script file's invoking process is `bash <script>`,
    which carries none of that text.
    """
    command = collision_check_template().replace("<worktree>", re.escape(str(worktree)))
    script = tmp_path / "check.sh"
    script.write_text(f"#!/bin/sh\n{command}\n")
    return subprocess.run(["bash", str(script)], capture_output=True, text=True)


def test_pattern_and_codex_agent_exec_do_not_contain_each_other() -> None:
    # Keying the check on codex-agent's own exec'd argv only works because
    # "codex exec" and "codex-agent exec" are different strings: neither
    # one is a substring of the other, so the check can never match
    # codex-agent's own invocation instead of the codex binary it execs.
    assert "codex exec" not in "codex-agent exec"
    assert "codex-agent exec" not in "codex exec"


def test_collision_check_finds_nothing_when_no_run_holds_the_worktree(tmp_path) -> None:
    worktree = tmp_path / "worktrees" / "sample-run"
    worktree.mkdir(parents=True)

    result = run_collision_check(worktree, tmp_path)

    assert result.returncode == 1
    assert result.stdout == ""


def test_collision_check_ignores_an_unrelated_process_with_the_same_text(tmp_path) -> None:
    worktree = tmp_path / "worktrees" / "sample-run"
    worktree.mkdir(parents=True)
    decoy = subprocess.Popen(["bash", "-c", 'exec -a "codex exec decoy" sleep 5'])
    try:
        time.sleep(0.3)  # let the decoy's argv land before pgrep looks for it
        result = run_collision_check(worktree, tmp_path)
    finally:
        decoy.terminate()
        decoy.wait()

    assert result.returncode == 1
    assert result.stdout == ""


def test_collision_check_finds_a_real_run_holding_the_worktree(tmp_path) -> None:
    worktree = tmp_path / "worktrees" / "sample-run"
    worktree.mkdir(parents=True)
    argv0 = (
        "codex exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
        f"-C {worktree} -o /tmp/report.md"
    )
    run = subprocess.Popen(["bash", "-c", f'exec -a "{argv0}" sleep 5'])
    try:
        time.sleep(0.3)
        result = run_collision_check(worktree, tmp_path)
    finally:
        run.terminate()
        run.wait()

    assert result.returncode == 0
    assert str(worktree) in result.stdout
