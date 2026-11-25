"""Tests for guideline_lint.py, run as its users run it: a subprocess.

Guideline files are written here at test time. Only one test reads the
real guidelines folder, and it checks only that every file parses.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "guideline_lint.py"

ONE_FOR = """\
---
id: py.comprehension.one-for
languages: python
scope: contextual
severity: block
enabled: true
detectors: code_quality:CQ001
keywords: flatten
---
Use one `for` clause per comprehension; else write an explicit loop.
"""
NO_STAR = """\
---
id: py.import.no-star
languages: python
scope: contextual
severity: block
enabled: true
detectors: ruff:F403
---
Import names explicitly.
"""


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, check=False,
    )


class GuidelineLintTest(unittest.TestCase):
    def setUp(self) -> None:
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.folder = Path(workspace.name)
        self.write("py-comprehension-one-for.md", ONE_FOR)
        self.write("py-import-no-star.md", NO_STAR)

    def write(self, name: str, text: str) -> None:
        (self.folder / name).write_text(text, encoding="utf-8")

    def lint_output(self) -> tuple[int, str]:
        result = run(str(self.folder))
        return (result.returncode, result.stdout)

    def test_valid_folder_is_clean(self) -> None:
        self.assertEqual(self.lint_output(), (0, ""))

    def test_missing_key_is_named(self) -> None:
        self.write(
            "py-import-no-star.md", NO_STAR.replace("severity: block\n", "")
        )
        self.assertEqual(
            self.lint_output(),
            (1, "py-import-no-star.md: missing key severity\n"),
        )

    def test_unknown_and_duplicate_keys_are_named(self) -> None:
        self.write(
            "py-import-no-star.md", NO_STAR.replace("enabled:", "events:")
        )
        self.write(
            "py-comprehension-one-for.md",
            ONE_FOR.replace("keywords:", "scope:"),
        )
        self.assertEqual(self.lint_output(), (
            1,
            "py-comprehension-one-for.md: duplicate key scope\n"
            "py-import-no-star.md: unknown key events\n",
        ))

    def test_bad_values_are_named(self) -> None:
        self.write(
            "py-import-no-star.md",
            NO_STAR.replace("severity: block", "severity: error"),
        )
        self.assertEqual(
            self.lint_output(),
            (1, "py-import-no-star.md: bad value for severity\n"),
        )

    def test_file_name_must_match_id(self) -> None:
        self.write("star.md", NO_STAR.replace("no-star", "star-import"))
        self.assertEqual(self.lint_output(), (
            1,
            "star.md: file name does not match id py.import.star-import\n"
            "star.md: detector ruff:F403 is also in py-import-no-star.md\n",
        ))

    def test_contextual_block_guideline_needs_a_detector(self) -> None:
        self.write(
            "py-import-no-star.md",
            NO_STAR.replace("detectors: ruff:F403", "detectors:"),
        )
        name = "py-import-no-star.md"
        self.assertEqual(self.lint_output(), (
            1,
            f"{name}: contextual guideline has no detector and no keyword\n"
            f"{name}: block guideline has no detector\n",
        ))

    def test_unknown_language_tool_and_uppercase_keyword(self) -> None:
        changed = NO_STAR.replace("python", "python, klingon").replace(
            "ruff:F403", "sonar:S100\nkeywords: Star"
        )
        self.write("py-import-no-star.md", changed)
        name = "py-import-no-star.md"
        self.assertEqual(self.lint_output(), (
            1,
            f"{name}: unknown language klingon\n"
            f"{name}: detector tool sonar has no runner table entry\n"
            f"{name}: keywords must be lowercase\n",
        ))

    def test_long_body_and_weak_motivating_body(self) -> None:
        self.write("py-import-no-star.md", NO_STAR + "a\nb\nc\nd\n")
        self.write(
            "py-comprehension-one-for.md",
            ONE_FOR.replace("explicit loop", "plain statement"),
        )
        self.assertEqual(self.lint_output(), (
            1,
            "py-comprehension-one-for.md: body must name `for` and `loop`\n"
            "py-import-no-star.md: body is longer than 4 lines\n",
        ))

    def test_real_guidelines_folder_parses(self) -> None:
        result = run("--parse-only")
        self.assertEqual((result.returncode, result.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
