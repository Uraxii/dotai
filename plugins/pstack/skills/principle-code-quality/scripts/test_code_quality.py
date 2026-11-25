"""Tests for code_quality.py, run as its users run it: a subprocess."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "code_quality.py"

FLATTENING_COMPREHENSION = """\
def pages(paths):
    return tuple(page for path in paths for page in parse_page(_read(path)))
"""

EXPLICIT_LOOP = """\
def pages(paths):
    found = []
    for path in paths:
        text = _read(path)
        found.extend(parse_page(text))
    print(len(found))
    return tuple(found)
"""

CQ001_LINE = (
    "pages.py:2: CQ001 comprehension has 2 for-clauses (limit 1); "
    "rewrite as an explicit for loop"
)
CQ002_LINE = (
    "pages.py:2: CQ002 call takes a call as argument inside a comprehension; "
    "bind the inner result to a name in an explicit for loop"
)


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, check=False,
    )


class CodeQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)

    def write(self, name: str, text: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_flattening_comprehension_fails_both_rules(self) -> None:
        self.write("pages.py", FLATTENING_COMPREHENSION)
        result = run(self.root, "pages.py")
        self.assertEqual(result.stdout, f"{CQ001_LINE}\n{CQ002_LINE}\n")
        self.assertEqual(result.returncode, 1)

    def test_explicit_loop_is_clean(self) -> None:
        self.write("pages.py", EXPLICIT_LOOP)
        result = run(self.root, ".")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_unparseable_file_exits_2_naming_it(self) -> None:
        self.write("broken.py", "def (:\n")
        result = run(self.root, "broken.py")
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.startswith("broken.py: cannot parse"))

    def test_missing_path_exits_2_naming_it(self) -> None:
        result = run(self.root, "absent.py")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stderr, "absent.py: no such file or directory\n"
        )

if __name__ == "__main__":
    unittest.main()
