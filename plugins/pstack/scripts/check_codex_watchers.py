#!/usr/bin/env python3
"""Run live writer and review checks in a preserved project-local fixture.

Set IMPLEMENTATION_BEAD to the claimed owner bead before running this check.
The owner store and actor remain separate from the fixture's bead store.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading


PLUGIN = Path(__file__).resolve().parents[1]
PROJECT = PLUGIN.parents[1]
HEARTBEAT_SECONDS = 120
RUN_TIMEOUT_SECONDS = 1200


def run(args: list[str], env: dict[str, str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, env=env, cwd=cwd, text=True,
                            capture_output=True, check=True)
    return result.stdout.strip()


def git(tree: Path, env: dict[str, str], *args: str) -> str:
    return run(["git", "-c", "core.hooksPath=/dev/null", "-c",
                "core.fsmonitor=false", "-C", str(tree), *args], env)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def watcher(plugin: Path, prompt: str, adapter: str, log: Path,
            scratch: dict[str, str], owner: dict[str, str], bead: str) -> None:
    stopped = threading.Event()

    def heartbeat() -> None:
        while not stopped.wait(HEARTBEAT_SECONDS):
            run(["bd", "heartbeat", bead], owner)

    run(["bd", "heartbeat", bead], owner)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    ask = (f"Call the Agent tool exactly once with subagent_type {adapter} "
           "and model sonnet. Wait for completion. Do no task work yourself. "
           "Reply done. The complete child prompt is this next line:\n" + prompt)
    try:
        with log.open("w") as output:
            subprocess.run(["claude", "-p", ask, "--plugin-dir", str(plugin),
                            "--model", "sonnet", "--strict-mcp-config",
                            "--setting-sources", "project", "--verbose",
                            "--output-format", "stream-json"], env=scratch,
                           cwd=plugin, stdout=output, stderr=subprocess.STDOUT,
                           check=True, timeout=RUN_TIMEOUT_SECONDS)
    finally:
        stopped.set()
        thread.join()
        run(["bd", "heartbeat", bead], owner)


def setup(root: Path, env: dict[str, str]) -> tuple[Path, Path, Path, str]:
    plugin, repo, tree = root / "plugin", root / "repo", root / "worktree"
    shutil.copytree(PLUGIN, plugin)
    manifest = plugin / ".claude-plugin/plugin.json"
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(json.dumps({"name": "pstack", "version": "0.0.0",
                                    "description": "Codex watcher check"}))
    run(["git", "init", "-q", "-b", "develop", str(repo)], env)
    git(repo, env, "config", "user.name", "Watcher check")
    git(repo, env, "config", "user.email", "check@example.invalid")
    git(repo, env, "commit", "-q", "--allow-empty", "-m",
        "chore(check): create fixture")
    git(repo, env, "config", "extensions.worktreeConfig", "true")
    remote = root / "remote.git"
    run(["git", "init", "-q", "--bare", str(remote)], env)
    git(repo, env, "remote", "add", "origin", str(remote))
    git(repo, env, "worktree", "add", "-q", "-b", "feat/codex-check", str(tree))
    store = root / "store"
    store.mkdir()
    run(["bd", "init", "--non-interactive", "--skip-agents", "--skip-hooks",
         "-p", "check"], env, store)
    bead = run(["bd", "create", "Write the check note", "-t", "task",
                "--description", "Create check-note.md with exactly the line "
                "Codex watcher check passed. Commit only that file. Do not push.",
                "--acceptance", "The file is committed, the worktree is clean, "
                "and stage=built records the local SHA.", "--silent"], env, store)
    run(["bd", "update", bead, "--append-notes",
         "Do not push. Stop at stage=built. The coordinator owns any push."], env)
    return plugin, repo, tree, bead


def check_run(root: Path, bead: str, role: str) -> Path:
    directory = root / "state/pstack/codex-runs" / bead / role
    marker = json.loads((directory / "codex.jsonl").read_text().splitlines()[-1])
    require(marker == {"pstack": "codex exited", "code": 0},
            f"{role} did not exit successfully")
    require(not (directory / "refused.txt").exists(), f"{role} was refused")
    return directory


def smoke(root: Path, owner: dict[str, str], owner_bead: str) -> None:
    scratch = dict(owner, XDG_STATE_HOME=str(root / "state"),
                   BEADS_DIR=str(root / "store/.beads"),
                   BEADS_ACTOR="codex-check-owner", BD_ACTOR="codex-check-owner")
    plugin, repo, tree, bead = setup(root, scratch)
    base = git(tree, scratch, "rev-parse", "HEAD")
    config = (repo / ".git/config").read_bytes()
    writer = f"Claim bead {bead} as developer-{bead}. Work in {tree}. Stop at stage=built."
    watcher(plugin, writer, "pstack:developer-codex", root / "writer-watcher.log",
            scratch, owner, owner_bead)
    sha = git(tree, scratch, "rev-parse", "HEAD")
    require(sha != base, "writer created no commit")
    require(git(tree, scratch, "show", "HEAD:check-note.md") ==
            "Codex watcher check passed.", "writer committed the wrong content")
    require(not git(tree, scratch, "status", "--porcelain"), "writer left changes")
    shown = json.loads(run(["bd", "show", bead, "--json"], scratch))
    shown = shown[0] if isinstance(shown, list) else shown
    require(shown["status"] != "closed" and "stage:built" in shown.get("labels", [])
            and not shown.get("assignee"), "writer did not record local built state")
    comments = json.loads(run(["bd", "comments", bead, "--json"], scratch))
    require(any(f"ready at {sha} on feat/codex-check" in row["text"]
                for row in comments), "writer did not record the SHA")
    check_run(root, bead, "writer")
    review = f"Review bead {bead} at {sha} in {tree}."
    watcher(plugin, review, "pstack:reviewer-codex", root / "review-watcher.log",
            scratch, owner, owner_bead)
    comments = json.loads(run(["bd", "comments", bead, "--json"], scratch))
    (root / "review-comments.json").write_text(json.dumps(comments, indent=2))
    require(any(row["text"].startswith(f"verdict pass at {sha}\n")
                for row in comments), "native review did not pass")
    require((check_run(root, bead, "reviewer") / "native.md").stat().st_size > 0,
            "native review output is empty")
    require(git(tree, scratch, "rev-parse", "HEAD") == sha and
            not git(tree, scratch, "status", "--porcelain"), "review changed Git")
    require((repo / ".git/config").read_bytes() == config, "shared config changed")
    require(not run(["git", f"--git-dir={root / 'remote.git'}", "for-each-ref"],
                    scratch), "writer pushed despite scope")
    run(["bd", "update", bead, "--status=open"], scratch)
    run(["bd", "update", bead, "--claim"], scratch)
    reason = root / "close-reason.txt"
    reason.write_text(f"Writer and native review passed at {sha}. "
                      f"No push occurred. Git and shared config are unchanged after review. Evidence: {root}\n")
    run(["bd", "close", bead, "--reason-file", str(reason)], scratch)
    print(f"Writer and review passed at {sha}. Evidence: {root}")


def main() -> int:
    owner = dict(os.environ)
    try:
        bead = owner["IMPLEMENTATION_BEAD"]
        require(bool(owner.get("BEADS_DIR") and owner.get("BEADS_ACTOR")),
                "owner bead environment is required")
        run(["codex", "login", "status"], owner)
        run(["claude", "--version"], owner)
        area = PROJECT / ".nikki-agents"
        area.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="codex-watcher-check-", dir=area))
        print(f"Preserved evidence directory: {root}", flush=True)
        smoke(root, owner, bead)
    except (KeyError, OSError, RuntimeError, ValueError,
            subprocess.SubprocessError) as error:
        print(f"Codex watcher check incomplete: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
