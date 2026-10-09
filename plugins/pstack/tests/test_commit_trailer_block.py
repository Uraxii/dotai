"""Regression tests for the commit form in the beads work loop.

bd's `prepare-commit-msg` hook appends `Executed-By: <actor>` after a blank
line, which splits the trailer block and hides `Co-Authored-By` from
`git interpret-trailers --parse`. The hook skips when the message already
carries `Executed-By:`. The documented commit form writes both trailers with
`git commit --trailer`. These tests read each documented form from its file and
run it against the real hook installed by `bd hooks install --chain`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WORK_LOOP = PLUGIN_ROOT / "skills/poteto-mode/references/beads-work-loop.md"
ACTOR = "developer-test.1"
ATTRIBUTION = "Co-Authored-By: Test Model <test@example.com>"

pytestmark = pytest.mark.skipif(shutil.which("bd") is None, reason="bd is not installed")


def work_loop_form() -> str:
    text = WORK_LOOP.read_text()
    match = re.search(r"^\s*(git commit -m .*)$", text, re.MULTILINE)
    assert match, "beads-work-loop.md has no git commit form"
    return match.group(1)


def codex_form() -> str:
    sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
    import prepare_codex_run

    request = prepare_codex_run.parse_request("Claim bead test.1 as developer-x. Work in /w.")
    match = re.search(r"`(git commit -m [^`]*)`", prepare_codex_run.writer_prompt(request))
    assert match, "the writer prompt has no git commit form"
    return match.group(1)


def fill(form: str) -> str:
    replacements = {"<subject>": "subject", "<id>": "test.1", "<why>": "why",
                    "<attribution>": "Test Model <test@example.com>"}
    for placeholder, value in replacements.items():
        form = form.replace(placeholder, value)
    return form


def env(actor: str | None) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if k not in {"BD_ACTOR", "BEADS_ACTOR", "BEADS_DIR"}}
    base.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                 "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})
    if actor:
        base["BD_ACTOR"] = actor
    return base


def make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["bd", "hooks", "install", "--chain"], cwd=tmp_path, env=env(None),
                   check=True, capture_output=True)
    (tmp_path / "f").write_text("x")
    subprocess.run(["git", "add", "f"], cwd=tmp_path, check=True)
    return tmp_path


def commit(repo: Path, form: str, actor: str | None) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", "-c", fill(form)], cwd=repo, env=env(actor),
                          capture_output=True, text=True)


def parsed_trailers(repo: Path) -> list[str]:
    message = subprocess.run(["git", "log", "-1", "--format=%B"], cwd=repo,
                             capture_output=True, text=True, check=True).stdout
    out = subprocess.run(["git", "interpret-trailers", "--parse"], input=message,
                         capture_output=True, text=True, check=True).stdout
    return out.splitlines()


def test_work_loop_form_yields_one_trailer_block(tmp_path):
    repo = make_repo(tmp_path)
    result = commit(repo, work_loop_form(), ACTOR)
    assert result.returncode == 0, result.stderr
    assert parsed_trailers(repo) == [ATTRIBUTION, f"Executed-By: {ACTOR}"]


def test_codex_form_yields_executed_by_in_the_block(tmp_path):
    repo = make_repo(tmp_path)
    result = commit(repo, codex_form(), ACTOR)
    assert result.returncode == 0, result.stderr
    assert parsed_trailers(repo) == [f"Executed-By: {ACTOR}"]


def test_unset_actor_refuses_to_commit(tmp_path):
    repo = make_repo(tmp_path)
    for form in (work_loop_form(), codex_form()):
        result = commit(repo, form, None)
        assert result.returncode != 0
    log = subprocess.run(["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True)
    assert log.returncode != 0 or log.stdout.strip() == ""
