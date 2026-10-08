"""Tests for the final-verdict extraction the reviewer-codex watcher runs.

The reviewer-codex agent definition names the exact command line, so the CLI
tests read it from there and run it against real message files.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

import final_verdict

SCRIPT = Path(__file__).with_name("final_verdict.py")
AGENT = Path(__file__).resolve().parents[3] / "agents" / "reviewer-codex.md"

EARLIER_BLOCK_THEN_INDENTED_FINAL = """\
Findings:

1. Missing test for the retry path.

verdict: fail
reason: no test covers the retry path

After re-checking the diff, the test exists.

  verdict: pass
  reason: the retry test is in the diff after all
"""


def run_cli(message: str, tmp_path: Path, sha: str = "abc1234") -> subprocess.CompletedProcess:
    path = tmp_path / "last-message.md"
    path.write_text(message)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), sha], capture_output=True, text=True
    )


def test_indented_final_reason_wins_over_an_earlier_block() -> None:
    assert final_verdict.final_verdict(EARLIER_BLOCK_THEN_INDENTED_FINAL) == (
        "pass",
        "the retry test is in the diff after all",
    )


def test_unindented_final_block_is_read() -> None:
    message = "verdict: fail\nreason: first\n\nverdict: pass\nreason: second\n"
    assert final_verdict.final_verdict(message) == ("pass", "second")


def test_reason_is_the_one_after_the_last_verdict_not_a_later_stray_line() -> None:
    message = "reason: stray\nverdict: pass\nreason: real\n"
    assert final_verdict.final_verdict(message) == ("pass", "real")


@pytest.mark.parametrize(
    "message",
    [
        "no verdict here\nreason: orphan\n",
        "verdict: pass\n",
        "verdict: maybe\nreason: unclear\n",
        "verdict: pass\nreason:\n",
        "verdict: fail\nreason: early\n\nverdict: pass\n",
    ],
)
def test_missing_or_invalid_verdict_returns_none(message: str) -> None:
    assert final_verdict.final_verdict(message) is None


def test_cli_prints_the_bead_comment_text(tmp_path) -> None:
    result = run_cli(EARLIER_BLOCK_THEN_INDENTED_FINAL, tmp_path)

    assert result.returncode == 0
    assert result.stdout == "verdict pass at abc1234: the retry test is in the diff after all\n"


def test_cli_exits_1_with_no_output_when_there_is_no_verdict(tmp_path) -> None:
    result = run_cli("just prose\n", tmp_path)

    assert result.returncode == 1
    assert result.stdout == ""


def test_agent_definition_runs_this_script() -> None:
    text = AGENT.read_text()
    assert re.search(r"scripts/final_verdict\.py <TMP>/last-message\.md <SHA>", text)
