"""Codex does the bead and git work itself, inside the sandbox the script builds.

Opt-in: set PSTACK_CODEX_LIVE=1 with `codex` (logged in), `bd`, and `jq` on PATH.
It spends Codex tokens. Each case builds a fixture under ~/.cache (Codex's
workspace-write sandbox already makes /tmp writable, which would hide a missing
grant), runs the real `prepare_codex_run.py` and the real `run.sh`, and asserts
only from outside the sandbox: the bead state, the bead comments, and the bare
remote. A scratch CODEX_HOME (auth symlinked, one-line config) keeps the run
from appending trust entries to ~/.codex/config.toml.
"""

from __future__ import annotations

import json
import re
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / "scripts/prepare_codex_run.py"
MODEL = os.environ.get("CODEX_MODEL", "gpt-5.6-terra")

pytestmark = pytest.mark.skipif(
    os.environ.get("PSTACK_CODEX_LIVE") != "1"
    or any(shutil.which(tool) is None for tool in ("codex", "bd")),
    reason="set PSTACK_CODEX_LIVE=1 with codex and bd on PATH",
)


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    return subprocess.run(
        list(args), cwd=cwd, env=env, check=True, capture_output=True, text=True,
    ).stdout.strip()


class Fixture:
    def __init__(self) -> None:
        cache = Path.home() / ".cache"
        cache.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="pstack-codex-live.", dir=cache))
        self.remote, self.repo = self.root / "remote.git", self.root / "repo"
        self.worktree, self.store = self.root / "wt", self.root / "store"
        base = {k: v for k, v in os.environ.items() if k not in {"BEADS_DIR", "BEADS_ACTOR", "BD_ACTOR"}}
        self.env = {**base, "BEADS_DIR": str(self.store / ".beads"),
                    "XDG_STATE_HOME": str(self.root / "state"),
                    "CODEX_HOME": str(self.root / "codex-home")}
        run("git", "init", "-q", "--bare", str(self.remote), cwd=self.root)
        run("git", "init", "-q", "-b", "main", str(self.repo), cwd=self.root)
        run("git", "-c", "user.name=t", "-c", "user.email=t@example.com",
            "commit", "-q", "--allow-empty", "-m", "init", cwd=self.repo)
        run("git", "remote", "add", "origin", str(self.remote), cwd=self.repo)
        run("git", "push", "-q", "origin", "main", cwd=self.repo)
        self.store.mkdir()
        init_env = {k: v for k, v in self.env.items() if k != "BEADS_DIR"}
        run("bd", "init", "-q", "--non-interactive", "-p", "live", cwd=self.store, env=init_env)
        run("bd", "hooks", "install", cwd=self.repo, env=self.env)
        run("git", "worktree", "add", "-q", str(self.worktree), "-b", "live-branch", cwd=self.repo)
        home = self.root / "codex-home"
        home.mkdir()
        (home / "auth.json").symlink_to(Path.home() / ".codex/auth.json")
        (home / "config.toml").write_text(f'model = "{MODEL}"\n')
        self.bead = json.loads(run(
            "bd", "create", "append a line to probe.txt", "--json",
            "--description", "Append the line `change` to probe.txt in the worktree root, creating it.",
            "--acceptance", "probe.txt holds the line `change`, committed.",
            cwd=self.repo, env=self.env,
        ))["id"]

    def bd(self, *args: str) -> str:
        return run("bd", *args, cwd=self.repo, env=self.env)

    def launch(self, prompt: str) -> None:
        prepared = subprocess.run(["python3", str(SCRIPT)], input=prompt, env=self.env,
                                  capture_output=True, text=True)
        assert prepared.returncode == 0, prepared.stderr
        run_dir = Path(prepared.stdout.strip())
        subprocess.run(["bash", str(run_dir / "run.sh")], env=self.env, timeout=900)
        log = (run_dir / "codex.jsonl").read_text()
        self.log = log + (run_dir / "codex.stderr").read_text()
        assert '"code":0' in log.splitlines()[-1], self.log

    def bead_json(self) -> dict:
        shown = json.loads(self.bd("show", self.bead, "--json"))
        return shown[0] if isinstance(shown, list) else shown

    def comments(self) -> str:
        return " | ".join(c["text"] for c in json.loads(self.bd("comments", self.bead, "--json")))

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


@pytest.fixture
def fixture():
    made = Fixture()
    yield made
    made.close()


def test_writer_claims_commits_and_closes(fixture: Fixture) -> None:
    fixture.launch(f"Claim bead {fixture.bead} as developer-{fixture.bead}. Work in {fixture.worktree}.")

    bead = fixture.bead_json()
    assert bead["status"] == "closed", fixture.log
    subject = run("git", "log", "-1", "--format=%s", cwd=fixture.worktree)
    assert re.fullmatch(r"[a-z]+(\([^)]+\))?: .+", subject), subject
    assert fixture.bead not in subject
    sha = run("git", "rev-parse", "HEAD", cwd=fixture.worktree)
    assert sha[:7] in bead["close_reason"]
    assert run("git", "show", "HEAD:probe.txt", cwd=fixture.worktree) == "change"
    assert run("git", "status", "--porcelain", cwd=fixture.worktree) == ""


def test_writer_stops_at_built_with_the_branch_on_the_remote(fixture: Fixture) -> None:
    fixture.launch(
        f"Claim bead {fixture.bead} as developer-{fixture.bead}. Work in {fixture.worktree}. "
        f"Stop at stage=built. Grant: {fixture.remote}"
    )

    sha = run("git", "rev-parse", "HEAD", cwd=fixture.worktree)
    bead = fixture.bead_json()
    assert bead["status"] != "closed", fixture.log
    assert "stage:built" in bead.get("labels", []), fixture.log
    assert not bead.get("assignee")
    assert f"ready at {sha} on live-branch" in fixture.comments()
    assert run("git", "rev-parse", "live-branch", cwd=fixture.remote) == sha


def test_reviewer_records_a_verdict_and_edits_nothing(fixture: Fixture) -> None:
    worktree_file = fixture.worktree / "probe.txt"
    worktree_file.write_text("change\n")
    run("git", "add", "probe.txt", cwd=fixture.worktree)
    run("git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q",
        "-m", "feat: append change", cwd=fixture.worktree)
    sha = run("git", "rev-parse", "HEAD", cwd=fixture.worktree)

    fixture.launch(f"Review bead {fixture.bead} at {sha} in {fixture.worktree}.")

    assert f"verdict pass at {sha}" in fixture.comments() or f"verdict fail at {sha}" in fixture.comments(), fixture.log
    assert run("git", "status", "--porcelain", cwd=fixture.worktree) == ""
    assert run("git", "rev-parse", "HEAD", cwd=fixture.worktree) == sha
