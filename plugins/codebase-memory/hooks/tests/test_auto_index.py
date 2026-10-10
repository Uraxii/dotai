import fcntl
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import warnings
from pathlib import Path


HOOK_PATH = Path(__file__).resolve().parents[1] / "auto_index.py"
SPEC = importlib.util.spec_from_file_location("auto_index", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


def write_indexer(bin_directory: Path) -> None:
    """A stub indexer that logs its start, then holds the lock until released."""
    bin_directory.mkdir()
    binary = bin_directory / "codebase-memory-mcp"
    binary.write_text(
        "#!/bin/sh\n"
        'if [ -n "$ARGV_MARKER" ]; then printf "%s\\n" "$@" > "$ARGV_MARKER"; fi\n'
        "printf 'spawned\\n' >> \"$SPAWN_MARKER\"\n"
        "read _ < \"$RELEASE_FIFO\"\n"
    )
    binary.chmod(0o755)


def release(fifo: Path) -> None:
    """Let the indexer blocked on `fifo` exit; it reads end-of-file."""
    deadline = time.monotonic() + 30
    while True:
        try:
            os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
            return
        except OSError:  # no reader has opened the fifo yet
            if time.monotonic() > deadline:
                raise
            time.sleep(0.01)


def wait_for_unlock(lock_path: Path) -> None:
    """Return once no process holds `lock_path`."""
    descriptor = os.open(lock_path, os.O_WRONLY)
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.01)
    finally:
        os.close(descriptor)


class AutoIndexTests(unittest.TestCase):
    def test_non_git_cwd_does_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory) / "not-a-repository"
            cwd.mkdir()
            cache = Path(directory) / "cache"
            bin_directory = Path(directory) / "bin"
            write_indexer(bin_directory)
            environment = {"PATH": str(bin_directory), "CBM_CACHE_DIR": str(cache)}

            self.assertFalse(HOOK.run(str(cwd), environment))
            self.assertFalse(cache.exists())

    def test_worktree_uses_its_own_project_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "main-checkout"
            worktree = Path(directory) / "linked-worktree"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "tracked.txt").write_text("tracked\n")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-qm",
                    "initial",
                ],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "worktree", "add", "-q", str(worktree)],
                check=True,
            )

            resolved = HOOK.repository_root(str(worktree))

            self.assertEqual(worktree.resolve(), resolved)
            self.assertEqual(
                HOOK.project_name(worktree.resolve()),
                HOOK.project_name(resolved),
            )

    def test_lock_follows_indexer_lifetime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            cache = Path(directory) / "cache"
            bin_directory = Path(directory) / "bin"
            marker = Path(directory) / "spawned"
            fifo = Path(directory) / "release"
            root.mkdir()
            os.mkfifo(fifo)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            write_indexer(bin_directory)
            environment = {
                "PATH": str(bin_directory),
                "CBM_CACHE_DIR": str(cache),
                "SPAWN_MARKER": str(marker),
                "RELEASE_FIFO": str(fifo),
            }
            lock = cache / f"{HOOK.project_name(root.resolve())}.index.lock"

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                self.assertTrue(HOOK.run(str(root), environment))
                self.assertFalse(HOOK.run(str(root), environment))
            release(fifo)
            wait_for_unlock(lock)

            self.assertEqual(["spawned"], marker.read_text().splitlines())

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                self.assertTrue(HOOK.run(str(root), environment))
            release(fifo)
            wait_for_unlock(lock)

            self.assertEqual(["spawned", "spawned"], marker.read_text().splitlines())


class WorktreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.directory / "main-checkout"
        self.worktree = self.directory / "linked worktree"
        self.cache = self.directory / "cache"
        self.marker = self.directory / "spawned"
        self.argv = self.directory / "argv"
        self.fifo = self.directory / "release"
        self.root.mkdir()
        self.cache.mkdir()
        os.mkfifo(self.fifo)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(
            [
                "git", "-C", str(self.root),
                "-c", "user.name=Test", "-c", "user.email=test@example.com",
                "commit", "--allow-empty", "-qm", "initial",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "worktree", "add", "-q",
             "-b", "agent", str(self.worktree)],
            check=True,
        )
        bin_directory = self.directory / "bin"
        write_indexer(bin_directory)
        self.environment = {
            **os.environ,
            "PATH": f"{bin_directory}{os.pathsep}{os.environ['PATH']}",
            "CBM_CACHE_DIR": str(self.cache),
            "SPAWN_MARKER": str(self.marker),
            "ARGV_MARKER": str(self.argv),
            "RELEASE_FIFO": str(self.fifo),
        }
        (self.cache / f"{HOOK.project_name(self.root.resolve())}.db").touch()

    def invoke_event(self, event: dict) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            env=self.environment,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def assert_worktree_indexed(self) -> None:
        lock = self.cache / f"{HOOK.project_name(self.worktree.resolve())}.index.lock"
        release(self.fifo)
        wait_for_unlock(lock)
        arguments = self.argv.read_text().splitlines()
        self.assertEqual(arguments[:2], ["cli", "index_repository"])
        self.assertEqual(
            json.loads(arguments[2]),
            {"repo_path": str(self.worktree.resolve()), "mode": "fast"},
        )
        self.assertEqual(self.marker.read_text().splitlines(), ["spawned"])

    def test_session_start_inside_worktree_indexes_worktree(self) -> None:
        nested = self.worktree / "src"
        nested.mkdir()
        self.invoke_event({"hook_event_name": "SessionStart", "cwd": str(nested)})
        self.assert_worktree_indexed()

    def test_both_harnesses_register_only_session_start(self) -> None:
        for harness in ("claude", "codex"):
            with self.subTest(harness=harness):
                document = json.loads(
                    (HOOK_PATH.parent / f"{harness}-hooks.json").read_text()
                )
                self.assertEqual(list(document["hooks"]), ["SessionStart"])


if __name__ == "__main__":
    unittest.main()
