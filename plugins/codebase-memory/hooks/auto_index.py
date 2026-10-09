#!/usr/bin/env python3
"""Start detached fast indexes for the current or newly created checkouts."""

import fcntl
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def project_name(repository_root: Path) -> str:
    return repository_root.as_posix().lstrip("/").replace("/", "-")


def cache_directory(environment: dict[str, str]) -> Path:
    return Path(
        environment.get(
            "CBM_CACHE_DIR", str(Path.home() / ".cache/codebase-memory-mcp")
        )
    )


def repository_root(cwd: str) -> Path | None:
    command = [
        "git",
        "-C",
        cwd,
        "rev-parse",
        "--show-toplevel",
    ]
    result = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def acquire_lock(cache_root: Path, name: str) -> int | None:
    cache_root.mkdir(parents=True, exist_ok=True)
    lock_path = cache_root / f"{name}.index.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor


def event_cwd(event: dict) -> str:
    cwd = event.get("cwd")
    return cwd if isinstance(cwd, str) and cwd else os.getcwd()


def run(cwd: str, environment: dict[str, str]) -> bool:
    root = repository_root(cwd)
    binary = shutil.which("codebase-memory-mcp", path=environment.get("PATH"))
    if root is None or binary is None:
        return False

    cache_root = cache_directory(environment)
    name = project_name(root)
    descriptor = acquire_lock(cache_root, name)
    if descriptor is None:
        return False

    try:
        subprocess.Popen(
            [
                binary,
                "cli",
                "index_repository",
                json.dumps({"repo_path": str(root), "mode": "fast"}),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=environment,
            pass_fds=(descriptor,),
        )
    except OSError:
        return False
    finally:
        os.close(descriptor)
    return True


def index_worktrees(cwd: str, environment: dict[str, str]) -> None:
    result = subprocess.run(
        ["git", "-C", cwd, "worktree", "list", "--porcelain", "-z"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return
    cache_root = cache_directory(environment)
    for field in result.stdout.split("\0"):
        if field.startswith("worktree "):
            root = Path(field.removeprefix("worktree ")).resolve()
            if not (cache_root / f"{project_name(root)}.db").exists():
                run(str(root), environment)


def main() -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return 0
        if event.get("hook_event_name") == "PostToolUse":
            tool_input = event.get("tool_input")
            command = (
                tool_input.get("command") if isinstance(tool_input, dict) else None
            )
            if not isinstance(command, str) or "worktree add" not in command:
                return 0
            index_worktrees(event_cwd(event), dict(os.environ))
        else:
            run(event_cwd(event), dict(os.environ))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
