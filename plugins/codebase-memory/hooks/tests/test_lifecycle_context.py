import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "lifecycle_context.py"
INSTRUCTIONS = (HOOK.parent / "instructions.md").read_text(encoding="utf-8")
GRAPH_MARKER = "GRAPH-CONTEXT-MARKER"
CLAUDE_AUGMENT = {"hookSpecificOutput": {"hookEventName": "x", "additionalContext": GRAPH_MARKER}}
COPILOT_AUGMENT = {"additionalContext": GRAPH_MARKER}


REMINDER = (
    "codebase-memory auto-indexing is off, so new checkouts and worktrees have no "
    "graph until indexed. Mention this to the user once, and suggest they run "
    "`codebase-memory-mcp config set auto_index true`. Do not run it yourself."
)
CONFIG_ARGV = "config get auto_index"


def run_hook(
    harness: str,
    event: str,
    fake_output: dict | None,
    config_script: str = "echo true",
    install_binary: bool = True,
) -> tuple[dict, list[str]]:
    """Run the hook against a fake binary; return its output and the argv of each call."""
    with tempfile.TemporaryDirectory() as bin_dir:
        calls = Path(bin_dir) / "calls.log"
        fake = Path(bin_dir) / "codebase-memory-mcp"
        augment = f"printf '%s' '{json.dumps(fake_output)}'" if fake_output else ":"
        if install_binary:
            fake.write_text(
                "#!/bin/sh\n"
                f'echo "$*" >> "{calls}"\n'
                f'if [ "$1" = config ]; then {config_script}; else {augment}; fi\n'
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        path = f"{bin_dir}:{os.environ['PATH']}" if install_binary else bin_dir
        result = subprocess.run(
            [sys.executable, str(HOOK), "--harness", harness, "--event", event],
            input=b"{}", capture_output=True, env={**os.environ, "PATH": path}, check=True,
        )
        argv = calls.read_text().splitlines() if calls.exists() else []
    return json.loads(result.stdout), argv


class LifecycleContextTest(unittest.TestCase):
    def test_claude_joins_instructions_and_graph_context_in_one_envelope(self):
        for event in ("SessionStart", "SubagentStart"):
            output, _ = run_hook("claude", event, CLAUDE_AUGMENT)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertEqual(output["hookSpecificOutput"]["hookEventName"], event)
            self.assertIn(INSTRUCTIONS.strip(), context)
            self.assertTrue(context.endswith(GRAPH_MARKER))

    def test_copilot_uses_top_level_additional_context(self):
        output, _ = run_hook("copilot", "SubagentStart", COPILOT_AUGMENT)
        self.assertEqual(list(output), ["additionalContext"])
        self.assertIn(INSTRUCTIONS.strip(), output["additionalContext"])
        self.assertTrue(output["additionalContext"].endswith(GRAPH_MARKER))

    def test_silent_hook_augment_still_yields_the_instructions(self):
        claude, _ = run_hook("claude", "SessionStart", None)
        self.assertEqual(
            claude["hookSpecificOutput"]["additionalContext"], INSTRUCTIONS.strip()
        )
        copilot, _ = run_hook("copilot", "SessionStart", None)
        self.assertEqual(copilot["additionalContext"], INSTRUCTIONS.strip())

    def test_session_start_reminds_when_auto_index_is_off(self):
        for harness, augment in (("claude", CLAUDE_AUGMENT), ("copilot", COPILOT_AUGMENT)):
            output, argv = run_hook(harness, "SessionStart", augment, "echo false")
            context = (
                output["hookSpecificOutput"]["additionalContext"]
                if harness == "claude" else output["additionalContext"]
            )
            self.assertEqual(
                context, f"{INSTRUCTIONS.strip()}\n\n{GRAPH_MARKER}\n\n{REMINDER}"
            )
            self.assertIn(CONFIG_ARGV, argv)

    def test_session_start_adds_nothing_when_auto_index_is_on(self):
        output, argv = run_hook("claude", "SessionStart", CLAUDE_AUGMENT, "echo true")
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(context, f"{INSTRUCTIONS.strip()}\n\n{GRAPH_MARKER}")
        self.assertIn(CONFIG_ARGV, argv)

    def test_session_start_adds_nothing_when_the_check_fails(self):
        failures = {
            "non-zero exit": "echo false; exit 1",
            "unexpected output": "echo maybe",
            "timeout": "exec sleep 30",
        }
        for name, config_script in failures.items():
            with self.subTest(name):
                output, argv = run_hook("claude", "SessionStart", None, config_script)
                self.assertEqual(
                    output["hookSpecificOutput"]["additionalContext"], INSTRUCTIONS.strip()
                )
                self.assertIn(CONFIG_ARGV, argv)

    def test_session_start_adds_nothing_when_the_binary_is_missing(self):
        output, argv = run_hook("claude", "SessionStart", None, install_binary=False)
        self.assertEqual(output["hookSpecificOutput"]["additionalContext"], INSTRUCTIONS.strip())
        self.assertEqual(argv, [])

    def test_subagent_start_never_runs_the_check(self):
        for harness, augment in (("claude", CLAUDE_AUGMENT), ("copilot", COPILOT_AUGMENT)):
            output, argv = run_hook(harness, "SubagentStart", augment, "echo false")
            self.assertNotIn(REMINDER, json.dumps(output))
            self.assertEqual(len(argv), 1)
            self.assertTrue(argv[0].startswith("hook-augment"), argv)


if __name__ == "__main__":
    unittest.main()
