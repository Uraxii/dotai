"""prepare_codex_run.py turns a watcher's spawn prompt into one Codex run.

A stub `codex` on PATH records its argv, cwd, environment, and stdin, then
exits with a chosen code, so these tests run the real script and the real
`run.sh` it writes without a Codex login. The watcher half (launch detached,
wait with Monitor) is read from the agent files and run against the stub.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / "scripts/prepare_codex_run.py"
WATCHERS = [PLUGIN_ROOT / "agents/developer-codex.md", PLUGIN_ROOT / "agents/reviewer-codex.md"]
SHA = "0123456789abcdef0123456789abcdef01234567"

STUB = """#!/usr/bin/env python3
import json, os, sys
record = {"argv": sys.argv[1:], "cwd": os.getcwd(), "stdin": sys.stdin.read(),
          "env": {k: os.environ.get(k) for k in ("BEADS_DIR", "BEADS_ACTOR", "BD_ACTOR")}}
open(os.environ["STUB_RECORD"], "w").write(json.dumps(record))
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
"""


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


class Env:
    def __init__(self, root: Path, worktree_name: str = "linked") -> None:
        self.root = root
        self.main = root / "main"
        self.worktree = root / worktree_name
        self.beads_dir = root / "store" / ".beads"
        self.state = root / "state"
        self.record = root / "record.json"
        self.beads_dir.mkdir(parents=True)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        (bin_dir / "codex").write_text(STUB)
        (bin_dir / "codex").chmod(0o755)
        git("init", "-q", "-b", "develop", str(self.main), cwd=root)
        git("commit", "-q", "--allow-empty", "-m", "root", cwd=self.main)
        git("worktree", "add", "-q", "-b", "task", str(self.worktree), cwd=self.main)
        self.environ = {
            **os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "BEADS_DIR": str(self.beads_dir), "XDG_STATE_HOME": str(self.state),
            "STUB_RECORD": str(self.record),
        }

    def prepare(self, prompt: str, **overrides: str | None) -> subprocess.CompletedProcess:
        environ = {**self.environ, **overrides}
        environ = {k: v for k, v in environ.items() if v is not None}
        return subprocess.run(["python3", str(SCRIPT)], input=prompt, env=environ,
                              capture_output=True, text=True)

    def run_dir(self, bead: str, role: str) -> Path:
        return self.state / "pstack/codex-runs" / bead / role

    def writer_prompt(self, suffix: str = "") -> str:
        return f"Claim bead t-1 as developer-t-1. Work in {self.worktree}.{suffix}"

    def run(self, run_dir: Path, exit_code: int = 0) -> dict:
        environ = {**self.environ, "STUB_EXIT": str(exit_code)}
        subprocess.run(["bash", str(run_dir / "run.sh")], env=environ, check=True)
        return json.loads(self.record.read_text())


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def add_dirs(argv: list[str]) -> list[str]:
    return [argv[i + 1] for i, a in enumerate(argv) if a == "--add-dir"]


def test_writer_gets_the_base_grants(env: Env) -> None:
    result = env.prepare(env.writer_prompt())
    assert result.returncode == 0, result.stderr
    run_dir = Path(result.stdout.strip())
    assert run_dir == env.run_dir("t-1", "writer")

    seen = env.run(run_dir)

    common = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=env.worktree))
    gitdir = Path(git("rev-parse", "--path-format=absolute", "--git-dir", cwd=env.worktree))
    assert add_dirs(seen["argv"]) == [
        str(gitdir), str(common / "objects"), str(common / "refs"), str(common / "logs"),
        str(env.beads_dir.parent),
    ]
    assert seen["cwd"] == str(env.worktree)
    assert seen["argv"][:1] == ["exec"]
    assert ["-s", "workspace-write"] == seen["argv"][seen["argv"].index("-s"):][:2]
    assert "sandbox_workspace_write.network_access=true" in seen["argv"]
    assert "agents.enabled=false" in seen["argv"]
    assert seen["env"] == {"BEADS_DIR": str(env.beads_dir), "BEADS_ACTOR": "developer-t-1",
                           "BD_ACTOR": "developer-t-1"}
    assert seen["stdin"] == (run_dir / "prompt.md").read_text()


def test_codex_exit_lands_in_the_log(env: Env) -> None:
    run_dir = Path(env.prepare(env.writer_prompt()).stdout.strip())

    env.run(run_dir, exit_code=3)

    last = (run_dir / "codex.jsonl").read_text().splitlines()[-1]
    assert json.loads(last) == {"pstack": "codex exited", "code": 3}


def test_extra_grants_become_add_dirs(env: Env, tmp_path: Path) -> None:
    extra = [tmp_path / "remote.git", tmp_path / "other"]
    for path in extra:
        path.mkdir()
    prompt = env.writer_prompt(" Stop at stage=built. Grant: " + " ".join(map(str, extra)))

    run_dir = Path(env.prepare(prompt).stdout.strip())
    seen = env.run(run_dir)

    assert add_dirs(seen["argv"])[-2:] == [str(p) for p in extra]
    assert "git push origin HEAD" in (run_dir / "prompt.md").read_text()


def test_reviewer_has_no_git_grants_and_no_network(env: Env) -> None:
    result = env.prepare(f"Review bead t-1 at {SHA} in {env.worktree}.")
    assert result.returncode == 0, result.stderr
    run_dir = Path(result.stdout.strip())
    seen = env.run(run_dir)

    assert run_dir == env.run_dir("t-1", "reviewer")
    assert add_dirs(seen["argv"]) == [str(env.beads_dir.parent)]
    assert "sandbox_workspace_write.network_access=true" not in seen["argv"]
    assert "--skip-git-repo-check" in seen["argv"]
    assert Path(seen["cwd"]) == run_dir / "cwd"
    assert seen["env"]["BEADS_ACTOR"] == "reviewer-t-1"
    prompt = (run_dir / "prompt.md").read_text()
    assert f"verdict pass at {SHA}" in prompt and "bd comment t-1 --file" in prompt


def test_reviewer_accepts_a_main_checkout_and_extra_grant(env: Env, tmp_path: Path) -> None:
    extra = tmp_path / "scratch"
    extra.mkdir()
    result = env.prepare(f"Review bead t-1 at {SHA} in {env.main}. Grant: {extra}")
    assert result.returncode == 0, result.stderr
    assert add_dirs(env.run(Path(result.stdout.strip()))["argv"]) == [
        str(env.beads_dir.parent), str(extra)]


def test_writer_prompt_orders_claim_heartbeat_commit_close(env: Env) -> None:
    run_dir = Path(env.prepare(env.writer_prompt()).stdout.strip())
    prompt = (run_dir / "prompt.md").read_text()

    positions = [prompt.index(s) for s in (
        "bd update t-1 --claim", "bd heartbeat t-1", "git commit -m", "bd close t-1 --reason-file")]
    assert positions == sorted(positions)
    assert 'Executed-By: ${BD_ACTOR:?}' in prompt
    assert "stage=built" not in prompt


def test_stop_at_built_prompt_pushes_labels_comments_and_unassigns(env: Env) -> None:
    run_dir = Path(env.prepare(env.writer_prompt(" Stop at stage=built.")).stdout.strip())
    prompt = (run_dir / "prompt.md").read_text()

    positions = [prompt.index(s) for s in (
        "git push origin HEAD", "bd set-state t-1 stage=built", "bd comment t-1", 'bd update t-1 --assignee ""')]
    assert positions == sorted(positions)
    assert "bd close" not in prompt
    assert "push -u" not in prompt.replace("(no -u;", "")


@pytest.mark.parametrize("prompt", [
    "Do the thing",
    "Claim bead t-1 as developer-t-1. Work in relative/path.",
    "Claim bead t-1 as developer-t-1. Work in /w. Grant: relative/dir",
    "Claim bead t-1 as developer-t-1. Work in /w. Grant: ",
    "Review bead t-1 at nothex in /w.",
])
def test_malformed_prompt_is_refused(env: Env, prompt: str) -> None:
    result = env.prepare(prompt)

    assert result.returncode == 2
    assert "refused:" in result.stderr


def test_missing_grant_path_is_refused_with_a_record(env: Env, tmp_path: Path) -> None:
    result = env.prepare(env.writer_prompt(f" Grant: {tmp_path}/nope"))

    assert result.returncode == 2
    assert "does not exist" in (env.run_dir("t-1", "writer") / "refused.txt").read_text()


@pytest.mark.parametrize("beads", [None, "relative/.beads"])
def test_unusable_beads_dir_is_refused(env: Env, beads: str | None) -> None:
    result = env.prepare(env.writer_prompt(), BEADS_DIR=beads)

    assert result.returncode == 2
    assert "BEADS_DIR" in (env.run_dir("t-1", "writer") / "refused.txt").read_text()


def test_non_git_worktree_is_refused(env: Env, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    result = env.prepare(f"Claim bead t-1 as developer-t-1. Work in {plain}.")

    assert result.returncode == 2
    assert "not a git worktree" in result.stderr


def test_writer_in_a_main_checkout_is_refused(env: Env) -> None:
    result = env.prepare(f"Claim bead t-1 as developer-t-1. Work in {env.main}.")

    assert result.returncode == 2
    assert "main checkout" in result.stderr


def test_per_worktree_config_layout_is_refused(env: Env) -> None:
    git("config", "extensions.worktreeConfig", "true", cwd=env.main)

    result = env.prepare(env.writer_prompt())

    assert result.returncode == 2
    assert "worktreeConfig" in result.stderr


@pytest.mark.parametrize("grant", [".git", ".git/hooks", ".git/config"])
def test_grant_over_hooks_or_config_is_refused(env: Env, grant: str) -> None:
    target = env.main / grant
    result = env.prepare(env.writer_prompt(f" Grant: {target}"))

    assert result.returncode == 2
    assert "writable" in result.stderr


def test_beads_parent_over_the_git_dir_is_refused(env: Env) -> None:
    result = env.prepare(env.writer_prompt(), BEADS_DIR=str(env.main / ".beads"))

    assert result.returncode == 2
    assert "writable" in result.stderr


def test_live_run_is_refused(env: Env) -> None:
    run_dir = Path(env.prepare(env.writer_prompt()).stdout.strip())
    (run_dir / "run.sh").write_text("#!/usr/bin/env bash\nsleep 30\n")
    live = subprocess.Popen(["bash", str(run_dir / "run.sh")])
    try:
        time.sleep(0.3)
        result = env.prepare(env.writer_prompt())
    finally:
        live.kill()
        live.wait()

    assert result.returncode == 2
    assert "already live" in result.stderr


def test_rerun_empties_the_run_dir(env: Env) -> None:
    run_dir = Path(env.prepare(env.writer_prompt()).stdout.strip())
    (run_dir / "stale.txt").write_text("old")
    (run_dir / "codex.jsonl").write_text("old")

    again = env.prepare(env.writer_prompt())

    assert again.returncode == 0
    assert not (run_dir / "stale.txt").exists()
    assert not (run_dir / "codex.jsonl").exists()


def test_paths_with_spaces_and_quotes_reach_codex_intact(tmp_path: Path) -> None:
    env = Env(tmp_path, worktree_name="my 'linked' tree")
    extra = tmp_path / "grant's"
    extra.mkdir()

    result = env.prepare(f"Claim bead t-1 as developer-t-1. Work in {env.worktree}. Grant: {extra}")
    assert result.returncode == 0, result.stderr
    seen = env.run(Path(result.stdout.strip()))

    assert seen["cwd"] == str(env.worktree)
    assert seen["argv"][seen["argv"].index("-C") + 1] == str(env.worktree)
    assert add_dirs(seen["argv"])[-1] == str(extra)
    assert str(env.worktree) in seen["stdin"]


def fenced_commands(agent: Path) -> list[str]:
    return re.findall(r"```\n(.*?)```", agent.read_text(), re.S)


@pytest.mark.parametrize("agent", WATCHERS, ids=lambda p: p.stem)
@pytest.mark.parametrize("exit_code", [0, 3])
def test_watcher_commands_launch_detached_and_wait_for_the_exit(
    agent: Path, exit_code: int, tmp_path: Path,
) -> None:
    env = Env(tmp_path)
    prompt = (env.writer_prompt() if agent.stem == "developer-codex"
              else f"Review bead t-1 at {SHA} in {env.worktree}.")
    run_dir = Path(env.prepare(prompt).stdout.strip())
    [launch] = [c for c in fenced_commands(agent) if "run.sh" in c and "setsid" in c]
    [wait] = [c for c in fenced_commands(agent) if "codex exited" in c]
    environ = {**env.environ, "STUB_EXIT": str(exit_code)}
    (env.root / "bin" / "codex").write_text(
        STUB.replace("sys.exit(", "import time; time.sleep(1.5); sys.exit("))

    subprocess.run(["bash", "-c", launch.replace("<run dir>", shlex.quote(str(run_dir)))],
                   env=environ, check=True, timeout=10)
    waited = subprocess.run(["bash", "-c", wait.replace("<run dir>", shlex.quote(str(run_dir)))],
                            env=environ, capture_output=True, text=True, timeout=30)

    assert waited.stdout.splitlines() == ["codex exited"]
    last = (run_dir / "codex.jsonl").read_text().splitlines()[-1]
    assert json.loads(last)["code"] == exit_code


@pytest.mark.parametrize("agent", WATCHERS, ids=lambda p: p.stem)
def test_watcher_holds_only_bash_and_monitor_on_haiku(agent: Path) -> None:
    head = agent.read_text().split("---")[1]

    assert re.search(r"^tools: Bash, Monitor$", head, re.M)
    assert re.search(r"^model: haiku$", head, re.M)
