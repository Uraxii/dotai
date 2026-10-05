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


def make_plugin_root(directory: str, instructions: str | bytes | None) -> Path:
    root = Path(directory)
    (root / "hooks").mkdir()
    shutil.copy(REAL_PLUGIN_ROOT / "hooks" / HOOK_NAME, root / "hooks" / HOOK_NAME)
    if isinstance(instructions, bytes):
        (root / "instructions.md").write_bytes(instructions)
    elif instructions is not None:
        (root / "instructions.md").write_text(instructions)
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
        self.root = make_plugin_root(self.directory.name, FIXTURE_TEXT)

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

    def test_every_wired_command_injects_the_file_from_another_cwd(self) -> None:
        wiring = {
            "hooks/claude-hooks.json": ("command", ["SessionStart", "SubagentStart"]),
            "hooks/codex-hooks.json": ("command", ["SessionStart", "SubagentStart"]),
            "hooks.json": ("bash", ["sessionStart", "subagentStart"]),
        }
        with tempfile.TemporaryDirectory() as parent:
            spaced_root = Path(parent) / "plugin root with spaces"
            spaced_root.mkdir()
            make_plugin_root(str(spaced_root), FIXTURE_TEXT)
            environment = {
                "PATH": "/usr/bin:/bin",
                "PLUGIN_ROOT": str(spaced_root),
                "CLAUDE_PLUGIN_ROOT": str(spaced_root),
            }
            for manifest, (key, events) in wiring.items():
                config = json.loads((REAL_PLUGIN_ROOT / manifest).read_text())
                self.assertEqual(sorted(events), sorted(config["hooks"]))
                for event in events:
                    with self.subTest(manifest=manifest, event=event), tempfile.TemporaryDirectory() as elsewhere:
                        entry = config["hooks"][event][0]
                        entry = entry["hooks"][0] if "hooks" in entry else entry
                        result = subprocess.run(
                            ["bash", "-c", entry[key]],
                            capture_output=True,
                            text=True,
                            cwd=elsewhere,
                            env=environment,
                        )

                        self.assertEqual(0, result.returncode, result.stderr)
                        self.assertIn("# Fixture rules", result.stdout)


if __name__ == "__main__":
    unittest.main()
