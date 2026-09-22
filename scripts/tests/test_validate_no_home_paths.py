"""Tests for the machine-specific home-path check.

The reject fixtures below never write a real account-name path as a literal
string. `home_path` assembles one from parts (`"home"`, `"alice"`) at test
run time, so the only thing this file's own source carries is the
placeholder shape `/{root}/{segment}` before substitution, which the rule
under test allows on its own terms. That is what keeps this file from
tripping the very check it exercises, without special-casing its filename.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY_ROOT / "scripts" / "validate-no-home-paths.py"

_spec = importlib.util.spec_from_file_location("validate_no_home_paths", VALIDATOR)
validate_no_home_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_no_home_paths)


def home_path(root: str, segment: str, rest: str = "") -> str:
    """Build `/root/segment/rest` without ever spelling it as one literal."""
    return f"/{root}/{segment}{rest}"


def run_validator(root: Path, script: Path = VALIDATOR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def script_copy_in(root: Path) -> Path:
    """A copy of the validator whose `parents[1]` is `root`.

    `main`'s default root comes from the running script's own path
    (`REPOSITORY_ROOT = Path(__file__).resolve().parents[1]`), the same
    pattern `generate-plugin-manifests.py` uses. Running a copy placed at
    `root/scripts/...` makes that default resolve to the throwaway
    repository instead of the real one, with no CLI flag needed.
    """
    destination = root / "scripts" / VALIDATOR.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(VALIDATOR.read_text())
    return destination


def init_git_repo(root: Path) -> None:
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "user.name", "Test"],
    ):
        subprocess.run(command, cwd=root, check=True, capture_output=True)


def commit_file(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    subprocess.run(["git", "add", relative], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", relative],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return path


class LineViolationsTests(unittest.TestCase):
    """Unit tests against the pure detection seam, no subprocess needed."""

    def test_rejects_account_names_under_home_roots(self) -> None:
        cases = {
            "home": home_path("home", "alice", "/x"),
            "Users": home_path("Users", "bob", "/x"),
            "var/home": home_path("var/home", "nicole", "/Projects/lodestar"),
        }
        for label, line in cases.items():
            with self.subTest(root=label):
                self.assertTrue(
                    validate_no_home_paths.offending_matches(line),
                    f"expected a violation in {line!r}",
                )

    def test_accepts_placeholder_segments(self) -> None:
        lines = [
            "/home/<name>",
            "/Users/{user}",
            home_path("home", "${USER}"),
            home_path("home", "$USER", "/bin"),
            "/home/.../x",
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual([], validate_no_home_paths.offending_matches(line))

    def test_accepts_placeholder_immediately_before_an_escaped_newline(self) -> None:
        # A placeholder sitting right before a literal "\n" escape sequence
        # in source text is how this file itself first failed its own
        # check: nothing but whitespace stopped the captured segment, so
        # "<name>" plus the two backslash-n characters no longer matched
        # the placeholder shape.
        line = "Examples: /repo/x, /root/.ssh, /home/<name>\n"
        self.assertEqual([], validate_no_home_paths.offending_matches(line))

    def test_accepts_root_and_repo_and_project_conventions(self) -> None:
        lines = [
            "/root/.ssh",
            "/root/x",
            "/repo/x",
            "<repo>/x",
            ".nikki-agents/scratch",
            "~/.claude/settings.json",
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual([], validate_no_home_paths.offending_matches(line))

    def test_reports_one_based_line_number(self) -> None:
        text = "first line\nsecond line\n" + home_path("home", "alice")
        violations = validate_no_home_paths.line_violations(Path("f.txt"), text)

        self.assertEqual([3], [violation.line_number for violation in violations])

    def test_skips_undecodable_bytes_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            binary = root / "blob.bin"
            binary.write_bytes(b"\xff\xfe\x00\x01")
            subprocess.run(
                ["git", "add", "blob.bin"], cwd=root, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", "binary"],
                cwd=root,
                check=True,
                capture_output=True,
            )

            violations, scanned = validate_no_home_paths.find_violations(root)

            self.assertEqual([], violations)
            self.assertEqual(0, scanned)


class ValidatorCommandTests(unittest.TestCase):
    """Integration tests against a throwaway repository, not the live one."""

    def test_passes_on_the_real_repository(self) -> None:
        result = run_validator(REPOSITORY_ROOT)

        self.assertEqual(0, result.returncode, result.stderr)

    def test_fails_on_a_violation_outside_plugins(self) -> None:
        # The historical leaks landed under plugins/, so the regression this
        # test guards is a per-tree loop that never looks at scripts/ or a
        # top-level markdown file.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            commit_file(
                root,
                "NOTES.md",
                f"See {home_path('home', 'nicole', '/Projects/lodestar')}\n",
            )
            script = script_copy_in(root)

            result = run_validator(root, script)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("NOTES.md:1", result.stderr)

    def test_passes_when_only_placeholders_are_committed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git_repo(root)
            commit_file(
                root,
                "README.md",
                "Examples: /repo/x, /root/.ssh, /home/<name>\n",
            )
            script = script_copy_in(root)

            result = run_validator(root, script)

            self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
