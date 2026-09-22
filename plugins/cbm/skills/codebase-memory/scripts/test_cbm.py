"""Tests for the cbm executable, against a stub codebase-memory-mcp."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path


CBM = Path(__file__).resolve().parent / "cbm"
BINARY = "codebase-memory-mcp"
INIT_LOG = "level=info msg=mem.init store=/tmp/x"
OTHER_LOG = "level=warn msg=index.stale"
ANSWER = {"b": 1, "a": [1, 2], "u": "café ✓", "n": None, "e": {}, "l": []}
PROGRESS_LOG = "level=info msg=index.progress files=1200"
RELEASE_AFTER_SEC = 10.0


class CbmTest(unittest.TestCase):
    """Exercise cbm through its executable boundary with a stub binary."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.seen = self.root / "seen-argv"
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.bin_dir)
        self.env["CBM_TEST_SEEN"] = str(self.seen)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_stub(self, body: str) -> None:
        stub = self.bin_dir / BINARY
        stub.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['CBM_TEST_SEEN']).write_text(json.dumps(sys.argv[1:]))\n"
            f"print({INIT_LOG!r}, file=sys.stderr)\n"
            f"print({OTHER_LOG!r}, file=sys.stderr)\n"
            + textwrap.dedent(body).lstrip()
        )
        stub.chmod(0o755)

    def write_answering_stub(self, answer: object = ANSWER) -> None:
        self.write_stub(f"print({json.dumps(answer)!r})\n")

    def run_cbm(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CBM), *args],
            capture_output=True,
            check=False,
            env=self.env,
            text=True,
        )

    def argv_seen(self) -> list[str]:
        return json.loads(self.seen.read_text(encoding="utf-8"))

    def test_pretty_prints_the_answer(self) -> None:
        self.write_answering_stub()

        result = self.run_cbm("some_tool")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout,
                         json.dumps(ANSWER, ensure_ascii=False, indent=2)
                         + "\n")

    def test_drops_only_the_init_log_line(self) -> None:
        self.write_answering_stub()

        result = self.run_cbm("some_tool")

        self.assertEqual(result.stderr, OTHER_LOG + "\n")

    def test_passes_the_tool_and_arguments_through(self) -> None:
        self.write_answering_stub()

        self.run_cbm("who_calls", '{"symbol":"main"}')

        self.assertEqual(self.argv_seen(),
                         ["cli", "who_calls", '{"symbol":"main"}'])

    def test_defaults_the_arguments_to_an_empty_object(self) -> None:
        for given in ([], [""]):
            with self.subTest(given=given):
                self.write_answering_stub()

                self.run_cbm("list_projects", *given)

                self.assertEqual(self.argv_seen(),
                                 ["cli", "list_projects", "{}"])

    def test_exits_with_the_binarys_status_not_the_printers(self) -> None:
        self.write_stub('print(\'{"error":"no such project"}\')\n'
                        "raise SystemExit(3)\n")

        result = self.run_cbm("some_tool")

        self.assertEqual(result.returncode, 3)
        self.assertIn('"error": "no such project"', result.stdout)

    def test_prints_nothing_when_the_binary_answers_nothing(self) -> None:
        self.write_stub("raise SystemExit(4)\n")

        result = self.run_cbm("some_tool")

        self.assertEqual(result.returncode, 4)
        self.assertEqual(result.stdout, "")

    def test_fails_on_an_answer_that_is_not_json(self) -> None:
        self.write_stub("print('not json at all')\n")

        result = self.run_cbm("some_tool")

        self.assertEqual(result.returncode, 5)
        self.assertEqual(result.stdout, "")
        self.assertIn("did not answer JSON", result.stderr)

    def test_relays_stderr_while_the_binary_is_still_running(self) -> None:
        gate = self.root / "gate"
        self.write_stub(
            "import os, time\n"
            f"print({PROGRESS_LOG!r}, file=sys.stderr, flush=True)\n"
            f"while not os.path.exists({str(gate)!r}):\n"
            "    time.sleep(0.01)\n"
            f"print({json.dumps(ANSWER)!r})\n")
        released = threading.Event()

        def release() -> None:
            released.set()
            gate.write_text("go")

        watchdog = threading.Timer(RELEASE_AFTER_SEC, release)
        watchdog.start()
        self.addCleanup(watchdog.cancel)
        process = subprocess.Popen(
            [sys.executable, str(CBM), "index_repository"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self.env)
        self.addCleanup(process.wait)

        relayed = [process.stderr.readline(), process.stderr.readline()]
        arrived_before_the_binary_could_exit = not released.is_set()
        release()
        process.wait()

        self.assertTrue(arrived_before_the_binary_could_exit,
                        "stderr only arrived once the binary had exited")
        self.assertEqual(relayed[0].rstrip("\n"), OTHER_LOG)
        self.assertEqual(relayed[1].rstrip("\n"), PROGRESS_LOG)

    def test_reports_a_missing_binary(self) -> None:
        result = self.run_cbm("some_tool")

        self.assertEqual(result.returncode, 127)
        self.assertIn(BINARY, result.stderr)


if __name__ == "__main__":
    unittest.main()
