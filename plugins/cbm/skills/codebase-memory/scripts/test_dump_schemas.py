"""Tests for the dump_schemas executable, against a stub MCP binary.

dump_schemas writes beside its own file, so every run here works on a copy
of the script in a temporary directory. Nothing touches the committed
references/tools.json.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


DUMP_SCHEMAS = Path(__file__).resolve().parent / "dump_schemas.py"
BINARY = "codebase-memory-mcp"
TOOLS = [{"name": "list_projects"}, {"name": "index_repository"}]
LIST_RESPONSE = {"jsonrpc": "2.0", "id": 2, "result": {"tools": TOOLS}}
INIT_RESPONSE = {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {}}}
ERROR_RESPONSE = {"jsonrpc": "2.0", "id": 2,
                  "error": {"code": -32601, "message": "no such method"}}
BANNER_LINE = "codebase-memory-mcp v9 starting up"
PARSE_ERROR_EXIT = 5


class DumpSchemasTest(unittest.TestCase):
    """Exercise dump_schemas through its executable boundary."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.scripts = self.root / "scripts"
        self.scripts.mkdir()
        (self.root / "references").mkdir()
        self.script = self.scripts / DUMP_SCHEMAS.name
        shutil.copyfile(DUMP_SCHEMAS, self.script)
        self.output = self.root / "references" / "tools.json"
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.bin_dir)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_stub(self, body: str) -> None:
        stub = self.bin_dir / BINARY
        stub.write_text(
            f"#!{sys.executable}\n"
            "import json, sys\n"
            "sys.stdin.read()\n"
            + textwrap.dedent(body).lstrip()
        )
        stub.chmod(0o755)

    def write_replying_stub(self, *messages: dict) -> None:
        lines = "\n".join(json.dumps(message) for message in messages)
        self.write_stub(f"print({lines!r})\n")

    def run_dump(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.script)],
            capture_output=True,
            check=False,
            env=self.env,
            text=True,
        )

    def test_writes_the_tools_list_response_as_one_compact_line(self) -> None:
        self.write_replying_stub(INIT_RESPONSE, LIST_RESPONSE)

        result = self.run_dump()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text(encoding="utf-8"),
                         json.dumps(LIST_RESPONSE, separators=(",", ":"))
                         + "\n")

    def test_reports_the_output_path_and_tool_count(self) -> None:
        self.write_replying_stub(INIT_RESPONSE, LIST_RESPONSE)

        result = self.run_dump()

        self.assertEqual(
            result.stdout,
            f"wrote {self.scripts / '..' / 'references' / 'tools.json'}: "
            f"{len(TOOLS)} tools\n",
        )

    def test_keeps_non_ascii_text_unescaped(self) -> None:
        named = {"jsonrpc": "2.0", "id": 2,
                 "result": {"tools": [{"name": "café ✓"}]}}
        self.write_replying_stub(named)

        self.run_dump()

        self.assertIn("café ✓", self.output.read_text(encoding="utf-8"))

    def test_propagates_a_failing_binary_and_leaves_the_output_untouched(
        self,
    ) -> None:
        self.output.write_text("stale contents", encoding="utf-8")
        self.write_stub("raise SystemExit(3)\n")

        result = self.run_dump()

        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.output.read_text(encoding="utf-8"), "stale contents")

    def test_an_error_response_counts_as_no_tools(self) -> None:
        self.write_replying_stub(INIT_RESPONSE, ERROR_RESPONSE)

        result = self.run_dump()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.rstrip("\n").endswith(": 0 tools"),
                        result.stdout)

    def test_a_line_that_is_not_json_fails_the_way_jq_did(self) -> None:
        self.output.write_text("stale contents", encoding="utf-8")
        self.write_stub(f"print({BANNER_LINE!r})\n"
                        f"print({json.dumps(LIST_RESPONSE)!r})\n")

        result = self.run_dump()

        self.assertEqual(result.returncode, PARSE_ERROR_EXIT)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.output.read_text(encoding="utf-8"), "stale contents")

    def test_leaves_the_output_untouched_when_the_binary_is_absent(self) -> None:
        self.output.write_text("stale contents", encoding="utf-8")

        result = self.run_dump()

        self.assertEqual(result.returncode, 127)
        self.assertIn(BINARY, result.stderr)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "stale contents")

    def test_leaves_the_output_untouched_on_a_nonzero_exit_with_a_reply(
        self,
    ) -> None:
        # The binary answers tools/list and then still exits non-zero (e.g.
        # a crash after replying). The reply parsed clean, but a non-zero
        # exit is still a failed run. The prior tools.json must survive it.
        self.output.write_text("stale contents", encoding="utf-8")
        self.write_stub(
            f"print({json.dumps(INIT_RESPONSE)!r})\n"
            f"print({json.dumps(LIST_RESPONSE)!r})\n"
            "sys.exit(9)\n"
        )

        result = self.run_dump()

        self.assertEqual(result.returncode, 9)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "stale contents")


if __name__ == "__main__":
    unittest.main()
