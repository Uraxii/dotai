import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = SKILL_ROOT.parents[1]
GENERATOR = SKILL_ROOT / "scripts" / "generate-agent-configs.py"
INSTALLER = SKILL_ROOT / "scripts" / "install-codex-agents.py"
WORKER_NAMES = {
    "architect",
    "developer",
    "explorer",
    "orchestrator",
    "researcher",
    "reviewer",
    "tester",
}


def run_script(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class AgentConfigGeneratorTests(unittest.TestCase):
    def test_generated_files_match_platform_neutral_definitions(self) -> None:
        result = run_script(GENERATOR, "--check")

        self.assertEqual(0, result.returncode, result.stderr)
        codex_files = list(
            (SKILL_ROOT / "assets" / "codex-agents").glob("*.toml")
        )
        self.assertEqual(WORKER_NAMES, {path.stem for path in codex_files})

        for path in codex_files:
            config = tomllib.loads(path.read_text())
            self.assertEqual(path.stem, config["name"])
            self.assertIn("description", config)
            self.assertIn("developer_instructions", config)
            self.assertNotIn("model", config)
            self.assertNotIn("model_reasoning_effort", config)


class CodexAgentInstallerTests(unittest.TestCase):
    def test_installs_workers_and_zakia_without_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            arguments = ("--codex-home", directory, "--install-zakia")

            first = run_script(INSTALLER, *arguments)
            second = run_script(INSTALLER, *arguments)

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            installed = list((codex_home / "agents").glob("*.toml"))
            self.assertEqual(WORKER_NAMES, {path.stem for path in installed})
            instructions = (codex_home / "AGENTS.md").read_text()
            self.assertEqual(1, instructions.count("<!-- dotai:zakia:start -->"))
            self.assertEqual(1, instructions.count("<!-- dotai:zakia:end -->"))
            self.assertIn("Zakia: fully capable coding agent", instructions)

    def test_refuses_to_replace_a_changed_personal_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            arguments = ("--codex-home", directory)
            first = run_script(INSTALLER, *arguments)
            changed = Path(directory) / "agents" / "developer.toml"
            changed.write_text("personal changes\n")

            refused = run_script(INSTALLER, *arguments)

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertNotEqual(0, refused.returncode)
            self.assertIn("developer.toml", refused.stderr)
            self.assertEqual("personal changes\n", changed.read_text())

            forced = run_script(INSTALLER, *arguments, "--force")

            self.assertEqual(0, forced.returncode, forced.stderr)
            self.assertNotEqual("personal changes\n", changed.read_text())

    def test_malformed_zakia_markers_leave_workers_uninstalled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            (codex_home / "AGENTS.md").write_text(
                "<!-- dotai:zakia:start -->\nunterminated\n"
            )

            refused = run_script(
                INSTALLER,
                "--codex-home",
                directory,
                "--install-zakia",
            )

            self.assertNotEqual(0, refused.returncode)
            self.assertIn("malformed Zakia markers", refused.stderr)
            self.assertFalse((codex_home / "agents").exists())


if __name__ == "__main__":
    unittest.main()
