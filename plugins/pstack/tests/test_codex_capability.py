"""Codex writers can do their job in every git layout the watcher meets.

What a `developer-codex` run needs, read from agents/developer-codex.md and
the delegate-to-codex playbook:

- edit files inside the worktree (`-s workspace-write -C <worktree>`)
- `git add`, `git switch -c`, `git commit`: write loose objects, the branch
  ref, the reflogs, and the worktree's own gitdir (index, HEAD, locks)
- run the project's tests from the worktree
- never write the shared `config` or `hooks`, which the watcher's own git
  commands would later run with its rights

These tests run the real grants script on real repositories, then perform the
commit and assert every file git changed sits under a grant. The opt-in
end-to-end test runs the watcher's real `codex exec -c agents.enabled=false` command shape.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import pytest

from test_codex_writer_git_isolation import (
    GRANTS_SCRIPT, WATCHER, PLUGIN_ROOT, git, granted_paths, run_grants,
)


Setup = Callable[[Path, Path], None]


def with_worktree_config(main: Path, worktree: Path) -> None:
    git("config", "extensions.worktreeConfig", "true", cwd=main)


def with_upstream(main: Path, worktree: Path) -> None:
    git("push", "-q", "-u", "origin", "HEAD", cwd=worktree)


def with_both(main: Path, worktree: Path) -> None:
    with_worktree_config(main, worktree)
    with_upstream(main, worktree)


def with_packed_refs(main: Path, worktree: Path) -> None:
    git("pack-refs", "--all", cwd=main)


def with_hooks_path_in_worktree(main: Path, worktree: Path) -> None:
    git("config", "core.hooksPath", ".githooks", cwd=main)


LAYOUTS: dict[str, tuple[Setup, str]] = {
    "plain": (lambda main, worktree: None, "linked"),
    "worktree-config": (with_worktree_config, "linked"),
    "upstream": (with_upstream, "linked"),
    "worktree-config-and-upstream": (with_both, "linked"),
    "packed-refs": (with_packed_refs, "linked"),
    "hooks-path-in-worktree": (with_hooks_path_in_worktree, "linked"),
    "path-with-spaces": (lambda main, worktree: None, "my linked tree"),
}


@pytest.fixture(params=LAYOUTS)
def worktree(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    setup, dirname = LAYOUTS[request.param]
    remote, main = tmp_path / "remote.git", tmp_path / "main"
    worktree = tmp_path / dirname
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    git("init", "-q", "-b", "develop", str(main), cwd=tmp_path)
    git("config", "gc.auto", "0", cwd=main)
    git("config", "maintenance.auto", "false", cwd=main)
    (main / "test_unit.py").write_text(
        "import unittest\n\n\nclass T(unittest.TestCase):\n"
        "    def test_ok(self):\n        self.assertTrue(True)\n"
    )
    git("add", "test_unit.py", cwd=main)
    git("-c", "user.name=t", "-c", "user.email=t@example.com",
        "commit", "-q", "-m", "root", cwd=main)
    git("remote", "add", "origin", str(remote), cwd=main)
    git("worktree", "add", "-q", "-b", "fix/unit", str(worktree), cwd=main)
    setup(main, worktree)
    return worktree


def snapshot(root: Path) -> dict[Path, tuple[int, int]]:
    return {
        path: (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*") if path.is_file()
    }


def common_dir(worktree: Path) -> Path:
    return Path(git("rev-parse", "--path-format=absolute",
                    "--git-common-dir", cwd=worktree))


def test_grant_script_accepts_the_layout(worktree: Path) -> None:
    result = run_grants(worktree)

    assert result.returncode == 0, result.stderr
    assert len(granted_paths(result.stdout)) == 4


def test_every_path_a_commit_writes_is_granted(worktree: Path) -> None:
    result = run_grants(worktree)
    assert result.returncode == 0, result.stderr
    grants = granted_paths(result.stdout)
    shared = common_dir(worktree)
    before = snapshot(shared)

    (worktree / "feature.txt").write_text("work\n")
    committer = ["-c", "user.name=t", "-c", "user.email=t@example.com",
                 "-c", "core.hooksPath=/dev/null"]
    git(*committer, "switch", "-q", "-c", "unit/codex", cwd=worktree)
    git(*committer, "add", "feature.txt", cwd=worktree)
    git(*committer, "commit", "-q", "-m", "work (x.1)", cwd=worktree)

    after = snapshot(shared)
    written = [path for path, stat in after.items() if before.get(path) != stat]
    assert written, "the commit changed nothing under the git dirs"
    uncovered = [
        path for path in written
        if not any(path.is_relative_to(grant) for grant in grants)
    ]
    assert uncovered == []
    assert git("log", "-1", "--format=%s", cwd=worktree) == "work (x.1)"


def test_grants_leave_config_and_hooks_read_only(worktree: Path) -> None:
    result = run_grants(worktree)
    assert result.returncode == 0, result.stderr
    grants = granted_paths(result.stdout)
    shared = common_dir(worktree)

    for protected in (shared / "config", shared / "hooks"):
        assert not any(protected.is_relative_to(grant) for grant in grants)


def test_project_tests_run_in_the_worktree(worktree: Path) -> None:
    result = subprocess.run(
        ["python3", "-m", "unittest", "-q"], cwd=worktree,
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr


def test_main_checkout_is_refused(tmp_path: Path) -> None:
    git("init", "-q", "-b", "develop", str(tmp_path / "main"), cwd=tmp_path)

    result = run_grants(tmp_path / "main")

    assert result.returncode != 0
    assert "main checkout" in result.stderr


def codex_command(worktree: Path, tmp: Path) -> str:
    """The watcher's `codex exec -c agents.enabled=false` line, with its placeholders filled in."""
    [command] = re.findall(
        r"codex exec -m <MODEL> -s workspace-write .*?(?=; RC=)",
        WATCHER.read_text(),
    )
    models = json.loads((PLUGIN_ROOT / "models.json").read_text())["roles"]
    [model] = [r["models"]["codex"][0] for r in models
               if r["role"] == "feature, refactoring"]
    grants = run_grants(worktree)
    assert grants.returncode == 0, grants.stderr
    adddirs = grants.stdout.strip()
    for placeholder, value in {
        "<MODEL>": model, "<worktree>": shlex.quote(str(worktree)),
        "<ADDDIRS>": adddirs, "<TMP>": shlex.quote(str(tmp)),
    }.items():
        command = command.replace(placeholder, value)
    return command


@pytest.mark.skipif(
    os.environ.get("PSTACK_CODEX_E2E") != "1" or shutil.which("codex") is None,
    reason="set PSTACK_CODEX_E2E=1 with codex installed to run",
)
@pytest.mark.parametrize("layout", ["plain", "worktree-config"])
def test_codex_creates_and_commits_with_the_watcher_command(
    layout: str, tmp_path: Path,
) -> None:
    setup, dirname = LAYOUTS[layout]
    remote, main = tmp_path / "remote.git", tmp_path / "main"
    worktree, out = tmp_path / dirname, tmp_path / "out"
    out.mkdir()
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    git("init", "-q", "-b", "develop", str(main), cwd=tmp_path)
    git("-c", "user.name=t", "-c", "user.email=t@example.com",
        "commit", "-q", "--allow-empty", "-m", "root", cwd=main)
    git("worktree", "add", "-q", "-b", "fix/unit", str(worktree), cwd=main)
    setup(main, worktree)
    (out / "prompt.md").write_text(
        "Create a file named hello.txt containing the word hello in the "
        "current directory. Run `python3 -c 'print(1)'` to prove you can run "
        "a command. Then commit with `git add hello.txt && git commit -m "
        "'add hello (e2e.1)'`. Reply in one line.\n"
    )
    before = git("rev-parse", "HEAD", cwd=worktree)
    environment = {**os.environ, "GIT_AUTHOR_NAME": "t",
                   "GIT_AUTHOR_EMAIL": "t@example.com",
                   "GIT_COMMITTER_NAME": "t",
                   "GIT_COMMITTER_EMAIL": "t@example.com"}

    result = subprocess.run(
        ["bash", "-c", f"{codex_command(worktree, out)} "
                       f"< {shlex.quote(str(out / 'prompt.md'))}"],
        capture_output=True, text=True, env=environment, timeout=600,
    )

    log = result.stdout + result.stderr
    assert result.returncode == 0, log
    assert git("rev-parse", "HEAD", cwd=worktree) != before, log
    assert git("log", "-1", "--format=%s", cwd=worktree).endswith("(e2e.1)")
    assert git("show", "HEAD:hello.txt", cwd=worktree).strip() == "hello"
