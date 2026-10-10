"""Tests for the log_decision executable's TSV row contract."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


LOG_DECISION = Path(__file__).resolve().parent / "log_decision.py"
HEADER = "ts\tphase\tdecision\twhy\tevidence\tresult"
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class LogDecisionTest(unittest.TestCase):
    """Exercise log_decision through its executable boundary."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.logfile = self.root / "decisions.tsv"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def log(self, *cells: str,
            logfile: Path | None = None) -> subprocess.CompletedProcess[str]:
        target = self.logfile if logfile is None else logfile
        return subprocess.run(
            [sys.executable, str(LOG_DECISION), str(target), *cells],
            capture_output=True,
            check=False,
            text=True,
        )

    def rows(self) -> list[list[str]]:
        text = self.logfile.read_text(encoding="utf-8")
        return [line.split("\t") for line in text.splitlines()]

    def test_writes_the_header_once_across_appends(self) -> None:
        self.log("build", "first", "why", "evidence", "result")
        self.log("build", "second", "why", "evidence", "result")

        text = self.logfile.read_text(encoding="utf-8")

        self.assertEqual(text.count(HEADER), 1)
        self.assertTrue(text.startswith(HEADER + "\n"))
        self.assertEqual([row[2] for row in self.rows()[1:]],
                         ["first", "second"])

    def test_keeps_a_header_the_caller_already_wrote(self) -> None:
        self.logfile.write_text(HEADER + "\n", encoding="utf-8")

        self.log("build", "only", "why", "evidence", "result")

        self.assertEqual(self.logfile.read_text(encoding="utf-8").count(HEADER),
                         1)

    def test_guards_every_cell_a_spreadsheet_would_run(self) -> None:
        self.log("=cmd|'/bin/sh'!A1", "+formula", "-minus", "@import",
                 "plain")

        self.assertEqual(self.rows()[1][1:],
                         ["'=cmd|'/bin/sh'!A1", "'+formula", "'-minus",
                          "'@import", "plain"])

    def test_guards_a_formula_hidden_behind_leading_whitespace(self) -> None:
        for lead in ("\t", "\r", "\n", " ", " \t\r\n "):
            for character in ("=", "+", "-", "@"):
                payload = f"{lead}{character}HYPERLINK(\"http://x\",\"c\")"
                with self.subTest(lead=lead, character=character):
                    self.logfile.unlink(missing_ok=True)

                    self.log("phase", payload, "why", "evidence", "result")

                    self.assertTrue(self.rows()[1][2].startswith("'"),
                                    self.rows()[1][2])

    def test_guards_only_the_first_character(self) -> None:
        self.log("phase", "a=b", "c+d", "e-f", "g@h")

        self.assertEqual(self.rows()[1][1:],
                         ["phase", "a=b", "c+d", "e-f", "g@h"])

    def test_flattens_row_breaking_characters_to_single_spaces(self) -> None:
        self.log("phase", "one\ttwo", "three\nfour", "five\rsix", "result")

        self.assertEqual(self.rows()[1][1:],
                         ["phase", "one two", "three four", "five six",
                          "result"])
        self.assertEqual(len(self.rows()), 2)

    def test_stamps_the_row_in_iso8601_utc(self) -> None:
        self.log("phase", "decision", "why", "evidence", "result")

        self.assertRegex(self.rows()[1][0], STAMP)

    def test_creates_the_parent_directory(self) -> None:
        nested = self.root / "trail" / "deep" / "decisions.tsv"

        result = self.log("phase", "decision", "why", "evidence", "result",
                          logfile=nested)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(nested.is_file())

    def test_writes_a_cell_whose_bytes_are_not_utf8(self) -> None:
        result = subprocess.run(
            [sys.executable, str(LOG_DECISION), str(self.logfile),
             b"phase", b"caf\xe9", b"why", b"evidence", b"result"],
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        written = self.logfile.read_bytes().splitlines()
        self.assertEqual(len(written), 2)
        self.assertEqual(written[1].split(b"\t")[2], b"caf\xe9")

    def test_rejects_a_wrong_argument_count(self) -> None:
        for cells in (("phase", "decision", "why", "evidence"),
                      ("phase", "decision", "why", "evidence", "result",
                       "extra")):
            with self.subTest(cells=cells):
                result = self.log(*cells)

                self.assertEqual(result.returncode, 1)
                self.assertIn("usage: log_decision.py", result.stderr)
                self.assertFalse(self.logfile.exists())


if __name__ == "__main__":
    unittest.main()
