import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
REPOSITORY_ROOT = PLUGIN_ROOT.parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "validate-models.py"

_spec = importlib.util.spec_from_file_location("validate_models", VALIDATOR)
validate_models = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_models)


def run_validator(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *arguments],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


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
        validate_models.validate_models_json(self.base_data())  # raises on failure

    def test_unknown_harness_key_in_role_errors(self) -> None:
        data = self.base_data()
        data["roles"][0]["models"]["opencode"] = ["opus"]

        with self.assertRaises(ValueError) as ctx:
            validate_models.validate_models_json(data)
        self.assertIn("opencode", str(ctx.exception))

    def test_unknown_harness_key_in_available_errors(self) -> None:
        data = self.base_data()
        data["available"]["opencode"] = [{"label": "X", "slug": "x"}]

        with self.assertRaises(ValueError) as ctx:
            validate_models.validate_models_json(data)
        self.assertIn("opencode", str(ctx.exception))

    def test_unknown_panel_name_errors(self) -> None:
        data = self.base_data()
        data["roles"][0]["models"] = "no-such-panel"

        with self.assertRaises(ValueError) as ctx:
            validate_models.validate_models_json(data)
        self.assertIn("no-such-panel", str(ctx.exception))

    def test_slug_not_in_harness_available_errors(self) -> None:
        data = self.base_data()
        # Plant a Codex slug under the claude harness: this is the mistake
        # the check exists to catch.
        data["roles"][0]["models"]["claude"] = ["gpt-5.5"]

        with self.assertRaises(ValueError) as ctx:
            validate_models.validate_models_json(data)
        self.assertIn("gpt-5.5", str(ctx.exception))
        self.assertIn("claude", str(ctx.exception))


class ValidatorCommandTests(unittest.TestCase):
    def test_committed_models_json_passes(self) -> None:
        result = run_validator()

        self.assertEqual(0, result.returncode, result.stderr)

    def test_nonzero_when_a_gpt_slug_is_planted_under_claude(self) -> None:
        models_path = PLUGIN_ROOT / "models.json"
        original_text = models_path.read_text()
        planted = json.loads(original_text)
        planted["roles"][0]["models"]["claude"].append("gpt-5.5")
        try:
            models_path.write_text(json.dumps(planted, indent=2))

            result = run_validator()

            self.assertNotEqual(0, result.returncode)
            self.assertIn("gpt-5.5", result.stderr)
        finally:
            models_path.write_text(original_text)


if __name__ == "__main__":
    unittest.main()
