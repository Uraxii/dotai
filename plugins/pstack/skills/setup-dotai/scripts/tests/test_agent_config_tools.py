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

    def test_named_agents_are_thin_poteto_agent_bodies(self) -> None:
        result = run_script(GENERATOR, "--check")
        self.assertEqual(0, result.returncode, result.stderr)

        references = SKILL_ROOT / "references"
        plugin_root = SKILL_ROOT.parents[1]
        body = (references / "poteto-agent-body.md").read_text().rstrip()
        # The watchers' body is the reference file the manifest points at,
        # not the playbook it was split out of.
        watcher_body = (
            plugin_root
            / "skills"
            / "poteto-mode"
            / "references"
            / "codex-watcher-body.md"
        ).read_text().rstrip()

        for name in WORKER_NAMES:
            generated = (plugin_root / "agents" / f"{name}.md").read_text()
            self.assertIn(body, generated)

        for name in ("developer-codex", "reviewer-codex"):
            generated = (plugin_root / "agents" / f"{name}.md").read_text()
            frontmatter, body = generated.split("---\n\n", maxsplit=1)
            self.assertIn("tools: Bash, Write\n", frontmatter)
            self.assertEqual(watcher_body, body.rstrip())
            stray_toml = SKILL_ROOT / "assets" / "codex-agents" / f"{name}.toml"
            self.assertFalse(stray_toml.exists())

        contract_files = {path.name for path in references.glob("*contract*")}
        self.assertEqual(set(), contract_files)


class CodexAgentInstallerTests(unittest.TestCase):
    def test_installs_workers_without_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            arguments = ("--codex-home", directory)

            first = run_script(INSTALLER, *arguments)
            second = run_script(INSTALLER, *arguments)

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            installed = list((codex_home / "agents").glob("*.toml"))
            self.assertEqual(WORKER_NAMES, {path.stem for path in installed})

    def test_writes_nothing_into_the_users_global_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            own_notes = codex_home / "AGENTS.md"
            own_notes.write_text("my own global instructions\n")

            result = run_script(INSTALLER, "--codex-home", directory)

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("my own global instructions\n", own_notes.read_text())

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


if __name__ == "__main__":
    unittest.main()
