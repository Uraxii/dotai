"""Pin the two CI commands that went quietly narrow when the plugins split.

Both failures looked identical from the outside: a green run that had stopped
looking at most of the repository. `pytest plugins/pstack scripts` collected
122 of 202 tests, and `validate-skills.py plugins/pstack/skills` inspected 44
of 55 skills. Neither said so.

A number to compare against would churn on every test added. What actually
broke was the enumeration, so these tests forbid the enumeration.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"

RUN_RE = re.compile(r"^\s*run:\s*(.+?)\s*$", re.MULTILINE)


def run_commands() -> list[str]:
    return RUN_RE.findall(WORKFLOW.read_text())


def command_starting_with(prefix: str) -> str:
    matches = [line for line in run_commands() if line.startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one {prefix!r} step, found {matches}")
    return matches[0]


class CiWorkflowTests(unittest.TestCase):
    def test_pytest_names_no_paths(self) -> None:
        command = command_starting_with("pytest")

        arguments = command.split()[1:]
        self.assertEqual(
            ["-q"],
            arguments,
            "pytest collects from the repository root so a new plugin's "
            "tests run without anyone editing this file. Adding a path here "
            "silently drops everything outside it.",
        )

    def test_skill_validation_covers_every_plugin(self) -> None:
        command = command_starting_with("python3 scripts/validate-skills.py")

        self.assertIn(
            "plugins/*/skills",
            command,
            "one run over every tree, because cross-plugin citations and "
            "pre-split deletions are invisible to a per-plugin loop",
        )

    def test_generated_manifests_are_checked(self) -> None:
        command_starting_with("python3 scripts/generate-plugin-manifests.py --check")

    def test_checkout_keeps_the_full_history(self) -> None:
        # validate-skills.py learns deleted skill names from git log.
        self.assertIn("fetch-depth: 0", WORKFLOW.read_text())


if __name__ == "__main__":
    unittest.main()
