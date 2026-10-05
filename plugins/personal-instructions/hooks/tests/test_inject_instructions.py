import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REAL_PLUGIN_ROOT = Path(__file__).resolve().parents[2]
HOOK_NAME = "inject_instructions.py"
FIXTURE_TEXT = "# Fixture rules\n\n- Say \"hi\" first.\n- Line with a \\ backslash."
MAIN_FIXTURE_TEXT = "# Main agent fixture rules"
MAIN_FILE = "main-agent-instructions.md"


def make_plugin_root(
    directory: str, instructions: str | bytes | None, main_instructions: str | None = None
) -> Path:
    root = Path(directory)
    (root / "hooks").mkdir()
    shutil.copy(REAL_PLUGIN_ROOT / "hooks" / HOOK_NAME, root / "hooks" / HOOK_NAME)
    if isinstance(instructions, bytes):
        (root / "instructions.md").write_bytes(instructions)
    elif instructions is not None:
        (root / "instructions.md").write_text(instructions)
    if main_instructions is not None:
        (root / MAIN_FILE).write_text(main_instructions)
    return root


def run_hook(root: Path, *arguments: str, cwd: str | None = None):
    return subprocess.run(
        [sys.executable, str(root / "hooks" / HOOK_NAME), *arguments],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


class InjectInstructionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = make_plugin_root(self.directory.name, FIXTURE_TEXT, MAIN_FIXTURE_TEXT)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_claude_session_output_is_the_file_text(self) -> None:
        result = run_hook(self.root, "--harness", "claude", "--event", "SessionStart")

        self.assertEqual(0, result.returncode)
        self.assertEqual(FIXTURE_TEXT + "\n", result.stdout)

    def test_hook_specific_json_echoes_the_event(self) -> None:
        cases = [
            ("claude", "SubagentStart"),
            ("codex", "SessionStart"),
            ("codex", "SubagentStart"),
        ]
        for harness, event in cases:
            with self.subTest(harness=harness, event=event):
                result = run_hook(self.root, "--harness", harness, "--event", event)

                self.assertEqual(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": event,
                            "additionalContext": FIXTURE_TEXT,
                        }
                    },
                    json.loads(result.stdout),
                )

    def test_copilot_output_is_additional_context_json(self) -> None:
        for event in ("SessionStart", "SubagentStart"):
            with self.subTest(event=event):
                result = run_hook(self.root, "--harness", "copilot", "--event", event)

                self.assertEqual({"additionalContext": FIXTURE_TEXT}, json.loads(result.stdout))

    def test_file_argument_selects_the_main_agent_file(self) -> None:
        result = run_hook(self.root, "--harness", "claude", "--file", MAIN_FILE)

        self.assertEqual(MAIN_FIXTURE_TEXT + "\n", result.stdout)

    def test_unknown_file_name_is_rejected(self) -> None:
        (self.root / "other.md").write_text("leaked")
        for name in ("other.md", "../instructions.md", "hooks/inject_instructions.py"):
            with self.subTest(name=name):
                result = run_hook(self.root, "--harness", "claude", "--file", name)

                self.assertEqual(0, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertIn("invalid choice", result.stderr)

    def test_missing_main_file_prints_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_plugin_root(directory, FIXTURE_TEXT)
            result = run_hook(root, "--harness", "codex", "--file", MAIN_FILE)

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_finds_file_from_a_different_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as elsewhere:
            result = run_hook(self.root, "--harness", "claude", cwd=elsewhere)

        self.assertEqual(FIXTURE_TEXT + "\n", result.stdout)

    def test_missing_or_empty_file_prints_nothing_and_exits_zero(self) -> None:
        for label, instructions in (("missing", None), ("empty", ""), ("blank", " \n\n")):
            with tempfile.TemporaryDirectory() as directory:
                root = make_plugin_root(directory, instructions)
                for harness in ("claude", "codex", "copilot"):
                    with self.subTest(file=label, harness=harness):
                        result = run_hook(root, "--harness", harness, "--event", "SubagentStart")

                        self.assertEqual(0, result.returncode)
                        self.assertEqual("", result.stdout)
                        self.assertEqual("", result.stderr)

    def test_unreadable_file_exits_zero_with_one_stderr_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_plugin_root(directory, b"\xff\xfe not utf-8")
            result = run_hook(root, "--harness", "claude")

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual(1, len(result.stderr.splitlines()))
        self.assertIn("UnicodeDecodeError", result.stderr)

    def test_session_start_injects_both_files_and_subagent_start_only_shared(self) -> None:
        wiring = {
            "hooks/claude-hooks.json": ("command", "SessionStart", "SubagentStart"),
            "hooks/codex-hooks.json": ("command", "SessionStart", "SubagentStart"),
            "hooks.json": ("bash", "sessionStart", "subagentStart"),
        }
        with tempfile.TemporaryDirectory() as parent:
            spaced_root = Path(parent) / "plugin root with spaces"
            spaced_root.mkdir()
            make_plugin_root(str(spaced_root), FIXTURE_TEXT, MAIN_FIXTURE_TEXT)
            environment = {
                "PATH": "/usr/bin:/bin",
                "PLUGIN_ROOT": str(spaced_root),
                "CLAUDE_PLUGIN_ROOT": str(spaced_root),
            }
            for manifest, (key, session_event, subagent_event) in wiring.items():
                config = json.loads((REAL_PLUGIN_ROOT / manifest).read_text())
                self.assertEqual(sorted([session_event, subagent_event]), sorted(config["hooks"]))
                expected = {
                    session_event: [["# Fixture rules"], ["# Main agent"]],
                    subagent_event: [["# Fixture rules"]],
                }
                for event, expected_injections in expected.items():
                    with self.subTest(manifest=manifest, event=event):
                        injections = []
                        for entry in config["hooks"][event]:
                            for hook in entry.get("hooks", [entry]):
                                with tempfile.TemporaryDirectory() as elsewhere:
                                    result = subprocess.run(
                                        ["bash", "-c", hook[key]],
                                        capture_output=True,
                                        text=True,
                                        cwd=elsewhere,
                                        env=environment,
                                    )
                                self.assertEqual(0, result.returncode, result.stderr)
                                injections.append(
                                    [m for m in ("# Fixture rules", "# Main agent") if m in result.stdout]
                                )

                        self.assertEqual(expected_injections, injections)

    def test_claude_session_start_entries_share_one_matcher(self) -> None:
        config = json.loads((REAL_PLUGIN_ROOT / "hooks/claude-hooks.json").read_text())
        matchers = {entry["matcher"] for entry in config["hooks"]["SessionStart"]}
        self.assertEqual(1, len(matchers), matchers)


if __name__ == "__main__":
    unittest.main()
