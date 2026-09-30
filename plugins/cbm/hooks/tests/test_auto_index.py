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


class AutoIndexTests(unittest.TestCase):
    def test_non_git_cwd_does_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {"PATH": ""}
            self.assertFalse(HOOK.run(directory, environment))

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
            root.mkdir()
            bin_directory.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            binary = bin_directory / "codebase-memory-mcp"
            binary.write_text(
                "#!/bin/sh\n"
                "printf 'spawned\\n' >> \"$SPAWN_MARKER\"\n"
                "exec /bin/sleep 2\n"
            )
            binary.chmod(0o755)
            environment = {
                "PATH": str(bin_directory),
                "CBM_CACHE_DIR": str(cache),
                "SPAWN_MARKER": str(marker),
            }

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                self.assertTrue(HOOK.run(str(root), environment))
                self.assertFalse(HOOK.run(str(root), environment))
            deadline = time.monotonic() + 1
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)

            self.assertTrue(marker.exists())
            self.assertEqual(["spawned"], marker.read_text().splitlines())

            time.sleep(2.1)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                self.assertTrue(HOOK.run(str(root), environment))
            deadline = time.monotonic() + 1
            while len(marker.read_text().splitlines()) < 2 and time.monotonic() < deadline:
                time.sleep(0.01)

            self.assertEqual(["spawned", "spawned"], marker.read_text().splitlines())
            time.sleep(2.1)


if __name__ == "__main__":
    unittest.main()
