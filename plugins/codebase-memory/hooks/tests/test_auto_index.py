import fcntl
import importlib.util
import os
import subprocess
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

    def test_worktree_uses_main_checkout_project_name(self) -> None:
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

            self.assertEqual(root.resolve(), resolved)
            self.assertEqual(
                HOOK.project_name(root.resolve()),
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


if __name__ == "__main__":
    unittest.main()
