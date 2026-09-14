import json
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
REPOSITORY_ROOT = PLUGIN_ROOT.parents[1]
GENERATOR = SKILL_ROOT / "scripts" / "generate-models.py"
ARCHITECT_SKILL = PLUGIN_ROOT / "skills" / "architect" / "SKILL.md"

sys.path.insert(0, str(GENERATOR.parent))
import importlib.util

_spec = importlib.util.spec_from_file_location("generate_models", GENERATOR)
generate_models = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generate_models)


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

    def test_stamped_block_lists_the_referenced_role_per_harness(self) -> None:
        text = ARCHITECT_SKILL.read_text()

        self.assertIn("<!-- dotai:models:start -->", text)
        self.assertIn(
            "`arena runners`: On Claude Code: `opus`, `sonnet`. "
            "On Codex: `gpt-5.5`. "
            "On Copilot CLI: `claude-opus-5`, `claude-sonnet-5`, `gpt-5.5`.",
            text,
        )
        self.assertIn("<!-- dotai:models:end -->", text)


class ValidateModelsJsonTests(unittest.TestCase):
    """Unit tests against the pure validation seam, no subprocess needed."""

    def base_data(self) -> dict:
        return {
            "available": {
                "claude": [{"label": "Opus 5", "slug": "opus"}],
                "codex": [{"label": "GPT-5.5", "slug": "gpt-5.5"}],
                "copilot": [{"label": "Opus 5", "slug": "claude-opus-5"}],
            },
            "panels": {},
            "roles": [
                {
                    "role": "some role",
                    "models": {"claude": ["opus"], "codex": ["gpt-5.5"], "copilot": ["claude-opus-5"]},
                }
            ],
        }

    def test_valid_data_passes(self) -> None:
        generate_models.validate_models_json(self.base_data())  # raises on failure

    def test_unknown_harness_key_in_role_errors(self) -> None:
        data = self.base_data()
        data["roles"][0]["models"]["opencode"] = ["opus"]

        with self.assertRaises(ValueError) as ctx:
            generate_models.validate_models_json(data)
        self.assertIn("opencode", str(ctx.exception))

    def test_unknown_harness_key_in_available_errors(self) -> None:
        data = self.base_data()
        data["available"]["opencode"] = [{"label": "X", "slug": "x"}]

        with self.assertRaises(ValueError) as ctx:
            generate_models.validate_models_json(data)
        self.assertIn("opencode", str(ctx.exception))

    def test_slug_not_in_harness_available_errors(self) -> None:
        data = self.base_data()
        # Plant a Codex slug under the claude harness: this is the mistake
        # the check exists to catch.
        data["roles"][0]["models"]["claude"] = ["gpt-5.5"]

        with self.assertRaises(ValueError) as ctx:
            generate_models.validate_models_json(data)
        self.assertIn("gpt-5.5", str(ctx.exception))
        self.assertIn("claude", str(ctx.exception))

    def test_check_is_nonzero_when_a_gpt_slug_is_planted_under_claude(self) -> None:
        original = json.loads((PLUGIN_ROOT / "models.json").read_text())
        planted = json.loads(json.dumps(original))
        planted["roles"][0]["models"]["claude"].append("gpt-5.5")
        models_path = PLUGIN_ROOT / "models.json"
        original_text = models_path.read_text()
        try:
            models_path.write_text(json.dumps(planted, indent=2))

            result = run_generator("--check")

            self.assertNotEqual(0, result.returncode)
        finally:
            models_path.write_text(original_text)


if __name__ == "__main__":
    unittest.main()
