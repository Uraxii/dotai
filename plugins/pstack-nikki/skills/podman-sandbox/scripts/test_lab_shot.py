"""Tests for the lab-shot executable's Xvfb ownership checks."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


LAB_SHOT = Path(__file__).parents[1] / "profiles" / "base" / "lab-shot"
DISPLAY = ":4917"
LOCK = Path("/tmp/.X4917-lock")


class LabShotTest(unittest.TestCase):
    """Exercise lab-shot through its executable boundary with stub programs."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.marker = self.root / "import-ran"
        self.output = self.root / "shot.png"
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.bin_dir) + os.pathsep + self.env["PATH"]
        self.env["LAB_SHOT_TEST_MARKER"] = str(self.marker)
        self.env["LAB_SHOT_TEST_MODE"] = "run"
        self.write_stubs()
        self.remove_lock()

    def tearDown(self) -> None:
        self.remove_lock()
        self.tempdir.cleanup()

    def remove_lock(self) -> None:
        if LOCK.exists():
            LOCK.unlink()

    def write_stubs(self) -> None:
        self.write_executable(
            "Xvfb",
            """
            import os
            import sys
            import time
            from pathlib import Path

            if os.environ["LAB_SHOT_TEST_MODE"] == "die":
                raise SystemExit(1)
            Path("/tmp/.X4917-lock").write_text(str(os.getpid()))
            time.sleep(30)
            """,
        )
        self.write_executable(
            "xdpyinfo",
            """
            import os
            import time
            from pathlib import Path

            if os.environ["LAB_SHOT_TEST_MODE"] == "die":
                raise SystemExit(0)
            for _ in range(50):
                if Path("/tmp/.X4917-lock").exists():
                    raise SystemExit(0)
                time.sleep(0.01)
            raise SystemExit(1)
            """,
        )
        self.write_executable(
            "import",
            """
            import os
            import sys
            from pathlib import Path

            Path(os.environ["LAB_SHOT_TEST_MARKER"]).touch()
            Path(sys.argv[-1]).write_bytes(b"png")
            """,
        )
        self.write_executable(
            "identify",
            "print(\"1280x720 stddev=1 colors=3 bytes=3\")",
        )

    def write_executable(self, name: str, body: str) -> None:
        executable = self.bin_dir / name
        executable.write_text(
            "#!/usr/bin/env python3\n" + textwrap.dedent(body).lstrip()
        )
        executable.chmod(0o755)

    def run_lab_shot(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(LAB_SHOT), str(self.output), DISPLAY, "0", "true"],
            capture_output=True,
            check=False,
            env=self.env,
            text=True,
        )

    def test_exits_when_xvfb_dies_while_another_server_answers(self) -> None:
        self.env["LAB_SHOT_TEST_MODE"] = "die"

        result = self.run_lab_shot()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Xvfb failed to start on :4917", result.stderr)
        self.assertFalse(self.marker.exists())

    def test_removes_stale_lock_without_an_xvfb_owner(self) -> None:
        LOCK.write_text(str(os.getpid()))

        result = self.run_lab_shot()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker.exists())

    def test_rejects_lock_owned_by_a_live_xvfb(self) -> None:
        owner_dir = self.root / "owner-bin"
        owner_dir.mkdir()
        owner = owner_dir / "Xvfb"
        owner.symlink_to(shutil.which("sleep") or "/bin/sleep")
        process = subprocess.Popen([str(owner), "30"])
        try:
            time.sleep(0.1)
            LOCK.write_text(str(process.pid))

            result = self.run_lab_shot()

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already owned by Xvfb", result.stderr)
            self.assertFalse(self.marker.exists())
        finally:
            process.terminate()
            process.wait()


if __name__ == "__main__":
    unittest.main()
