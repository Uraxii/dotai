import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
REPOSITORY_ROOT = PLUGIN_ROOT.parents[1]
GENERATOR = SKILL_ROOT / "scripts" / "generate-models.py"
ARCHITECT_SKILL = PLUGIN_ROOT / "skills" / "architect" / "SKILL.md"


def run_generator(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GENERATOR), *arguments],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class GenerateModelsTests(unittest.TestCase):
    def test_check_passes_on_the_committed_tree(self) -> None:
        result = run_generator("--check")

        self.assertEqual(0, result.returncode, result.stderr)

    def test_regenerating_twice_changes_nothing(self) -> None:
        before = ARCHITECT_SKILL.read_text()

        first = run_generator()
        after_first = ARCHITECT_SKILL.read_text()
        second = run_generator()
        after_second = ARCHITECT_SKILL.read_text()

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(before, after_first)
        self.assertEqual(after_first, after_second)

    def test_check_fails_on_a_hand_edited_stamped_block(self) -> None:
        original = ARCHITECT_SKILL.read_text()
        try:
            tampered = original.replace("`gpt-5.5`", "`gpt-5.5`, `tampered-model`", 1)
            self.assertNotEqual(original, tampered)
            ARCHITECT_SKILL.write_text(tampered)

            result = run_generator("--check")

            self.assertNotEqual(0, result.returncode)
            self.assertIn("architect/SKILL.md", result.stderr)
        finally:
            ARCHITECT_SKILL.write_text(original)

    def test_stamped_block_lists_the_referenced_role(self) -> None:
        text = ARCHITECT_SKILL.read_text()

        self.assertIn("<!-- dotai:models:start -->", text)
        self.assertIn("`arena runners`: `claude-opus-5`, `claude-sonnet-5`, `gpt-5.5`", text)
        self.assertIn("<!-- dotai:models:end -->", text)


if __name__ == "__main__":
    unittest.main()
