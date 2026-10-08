"""Pin the CI commands that went quietly narrow or quietly missing.

The two narrowings looked identical from the outside: a green run that had
stopped looking at most of the repository. `pytest plugins/pstack scripts`
collected 122 of 202 tests, and `validate-skills.py plugins/pstack/skills`
inspected 44 of 55 skills. Neither said so.

A number to compare against would churn on every test added. What actually
broke was the enumeration, so these tests forbid the enumeration.

Forbidding it in `ci.yml` only guards one spelling. `PytestCollectsEveryTest`
below measures the effect instead: it runs collection and compares what the
repository root sees against what each test directory sees on its own.

The bd and bun steps guard the other silent pass. The bd-backed modules skip
when bd is not on PATH, and no step ran a `*.test.ts` at all.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
BD_INSTALLER = REPOSITORY_ROOT / "scripts" / "install-bd.sh"
BD_VERSION = "1.3.1"
BD_CONCURRENCY_CHECK = (
    "python3 plugins/pstack/skills/poteto-mode/scripts/check_bd_concurrency.py"
)
MOST_CONCURRENCY_ROUNDS_IN_A_MINUTE = 3

def command_starting_with_workflow(prefix: str) -> str:
    matches = [line for line in run_commands() if line.startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one {prefix!r} step, found {matches}")
    return matches[0]


RUN_RE = re.compile(r"^\s*run:\s*(.+?)\s*$", re.MULTILINE)


def run_commands() -> list[str]:
    return RUN_RE.findall(WORKFLOW.read_text())


def directories_holding_tests() -> list[Path]:
    """Every directory holding a `test_*.py`, relative to the root.

    Swept, not listed. A hand-kept list here would go stale the first time a
    plugin arrives with tests, which is the drift this file exists to catch.
    """
    found = {
        path.parent.relative_to(REPOSITORY_ROOT)
        for path in REPOSITORY_ROOT.rglob("test_*.py")
        if "__pycache__" not in path.parts and ".git" not in path.parts
    }
    return sorted(found)


def bun_test_files() -> list[Path]:
    """Every `*.test.ts` in the repository, relative to the root.

    A `fixtures` directory holds input for an eval, not a suite to run.
    """
    skipped = {"node_modules", ".git", "fixtures"}
    return sorted(
        path.relative_to(REPOSITORY_ROOT)
        for path in REPOSITORY_ROOT.rglob("*.test.ts")
        if not skipped.intersection(path.parts)
    )


def collected_node_ids(*paths: str) -> list[str]:
    """Node ids pytest collects for `paths`, or for the root when empty.

    `--collect-only` imports the test modules and runs none of them, so this
    cannot recurse into itself however many times pytest nests.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            *paths,
        ],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"collecting {paths or ('the repository root',)} failed with exit "
            f"{result.returncode}:\n{result.stdout}\n{result.stderr}"
        )
    return [line for line in result.stdout.splitlines() if "::" in line]


CHECK = REPOSITORY_ROOT / "scripts" / "check"


def check_commands() -> list[str]:
    """The `run` lines of scripts/check, in order, one per stage."""
    return [
        line.strip()
        for line in CHECK.read_text().splitlines()
        if line.startswith(("run ", "optional "))
    ]


def command_starting_with(prefix: str) -> str:
    matches = [line for line in check_commands() if prefix in line]
    if len(matches) != 1:
        raise AssertionError(f"expected one {prefix!r} stage, found {matches}")
    return matches[0]


class CiWorkflowTests(unittest.TestCase):
    def test_ci_runs_scripts_check_and_nothing_else_to_check(self) -> None:
        commands = run_commands()

        self.assertIn("scripts/check", commands)
        self.assertNotIn("pytest", " ".join(commands).replace("pytest-", ""))
        self.assertIn(
            'CHECK_REQUIRE_ALL: "1"',
            WORKFLOW.read_text(),
            "without it a missing bd or bun skips instead of failing",
        )
        self.assertTrue(os.access(CHECK, os.X_OK))

    def test_pytest_names_no_paths(self) -> None:
        command = command_starting_with("run pytest")

        self.assertEqual("run pytest pytest -q -n auto", command)

    def test_skill_validation_covers_every_plugin(self) -> None:
        self.assertIn(
            "plugins/*/skills",
            command_starting_with("scripts/validate-skills.py"),
            "one run over every tree, because cross-plugin citations and "
            "pre-split deletions are invisible to a per-plugin loop",
        )

    def test_generated_manifests_are_checked(self) -> None:
        command_starting_with("scripts/generate-plugin-manifests.py --check")

    def test_home_paths_are_checked(self) -> None:
        command_starting_with("scripts/validate-no-home-paths.py")

    def test_checkout_keeps_the_full_history(self) -> None:
        # validate-skills.py learns deleted skill names from git log.
        self.assertIn("fetch-depth: 0", WORKFLOW.read_text())

    def test_every_step_runs_from_the_repository_root(self) -> None:
        self.assertNotIn(
            "working-directory",
            WORKFLOW.read_text(),
            "every check here takes the whole repository as its subject. A "
            "step that runs somewhere else narrows pytest collection and "
            "the plugins/*/skills glob without naming a single path, which "
            "no test outside this file can see.",
        )

    def test_bd_installs_the_pinned_release_onto_the_path(self) -> None:
        installer = BD_INSTALLER.read_text()

        self.assertIn("$GITHUB_PATH", command_starting_with_workflow("scripts/install-bd.sh"))
        self.assertIn(f"VERSION={BD_VERSION}\n", installer)
        self.assertRegex(installer, r"\nSHA256=[0-9a-f]{64}\n")
        self.assertIn("sha256sum -c", installer)

    def test_bd_concurrency_runs_before_pytest(self) -> None:
        commands = check_commands()
        self.assertLess(
            commands.index(command_starting_with(BD_CONCURRENCY_CHECK)),
            commands.index(command_starting_with("run pytest")),
            "the concurrency check fails without bd, so running it before "
            "pytest proves the bd-backed modules saw bd",
        )

    def test_bd_concurrency_check_runs_a_few_rounds(self) -> None:
        rounds = re.fullmatch(r".* --rounds (\d+)", command_starting_with(BD_CONCURRENCY_CHECK))
        self.assertIsNotNone(
            rounds,
            "without --rounds the check runs its default ten rounds, "
            "several minutes of CI",
        )
        self.assertLessEqual(int(rounds.group(1)), MOST_CONCURRENCY_ROUNDS_IN_A_MINUTE)

    def test_bun_is_pinned(self) -> None:
        text = WORKFLOW.read_text()

        self.assertRegex(text, r"uses: oven-sh/setup-bun@v\d+\.\d+\.\d+\n")
        self.assertRegex(text, r"bun-version: \d+\.\d+\.\d+\n")
        self.assertIn("--frozen-lockfile", command_starting_with("bun install"))

    def test_bun_runs_every_bun_test_file(self) -> None:
        roots = command_starting_with("bun test").split("bun test")[1].strip(" '").split()
        self.assertTrue(roots, "bun test from the root also runs fixtures")
        for path in bun_test_files():
            with self.subTest(path=path.as_posix()):
                self.assertTrue(
                    any(path.is_relative_to(root) for root in roots),
                    f"{path} is outside every path the bun stage names "
                    f"({roots}), so CI never runs it",
                )

    def test_no_step_swallows_its_own_failure(self) -> None:
        self.assertNotIn(
            "continue-on-error",
            WORKFLOW.read_text(),
            "a step marked continue-on-error reports green whatever it "
            "found, which is the same silent pass as collecting no tests.",
        )


class PytestCollectsEveryTest(unittest.TestCase):
    """Guard the collection itself, not the way `ci.yml` spells the command.

    Moving the enumeration out of `ci.yml` reproduced the original defect
    with every workflow test passing. A `pyproject.toml` holding
    `testpaths = ["scripts"]` took collection from 213 node ids to 56.
    `working-directory: scripts` on the step does the same.

    Both shrink what the repository root collects and leave each directory's
    own collection whole, so the root total and the sum of the parts stop
    agreeing. Neither assertion below carries a number to update when
    somebody adds a test.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.directories = directories_holding_tests()
        cls.from_root = collected_node_ids()

    def test_every_test_directory_reaches_the_root_collection(self) -> None:
        for directory in self.directories:
            prefix = f"{directory.as_posix()}/"
            with self.subTest(directory=prefix):
                self.assertTrue(
                    any(node.startswith(prefix) for node in self.from_root),
                    f"{prefix} holds a test_*.py and contributed no node id "
                    "to a collection from the repository root. Something "
                    "outside this directory narrowed the run: a testpaths or "
                    "addopts setting, a changed working directory, or a path "
                    "argument.",
                )

    def test_the_root_collects_as_much_as_the_parts_together(self) -> None:
        parts = {
            directory: len(collected_node_ids(directory.as_posix()))
            for directory in self.directories
        }
        self.assertEqual(
            len(self.from_root),
            sum(parts.values()),
            "collecting from the repository root found "
            f"{len(self.from_root)} tests, but the directories collected one "
            f"at a time found {sum(parts.values())} between them: "
            f"{ {str(k): v for k, v in parts.items()} }. A root collection "
            "smaller than the sum means a repository-wide setting is "
            "dropping tests that still run when named directly.",
        )


if __name__ == "__main__":
    unittest.main()
