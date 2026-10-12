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


def run_hook(harness: str, event: str, fake_output: dict | None) -> dict:
    with tempfile.TemporaryDirectory() as bin_dir:
        fake = Path(bin_dir) / "codebase-memory-mcp"
        body = f"printf '%s' '{json.dumps(fake_output)}'" if fake_output else ":"
        fake.write_text(f"#!/bin/sh\n{body}\n")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
        result = subprocess.run(
            [sys.executable, str(HOOK), "--harness", harness, "--event", event],
            input=b"{}", capture_output=True, env=env, check=True,
        )
    return json.loads(result.stdout)


class LifecycleContextTest(unittest.TestCase):
    def test_claude_joins_instructions_and_graph_context_in_one_envelope(self):
        for event in ("SessionStart", "SubagentStart"):
            output = run_hook("claude", event, CLAUDE_AUGMENT)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertEqual(output["hookSpecificOutput"]["hookEventName"], event)
            self.assertIn(INSTRUCTIONS.strip(), context)
            self.assertTrue(context.endswith(GRAPH_MARKER))

    def test_copilot_uses_top_level_additional_context(self):
        output = run_hook("copilot", "SubagentStart", COPILOT_AUGMENT)
        self.assertEqual(list(output), ["additionalContext"])
        self.assertIn(INSTRUCTIONS.strip(), output["additionalContext"])
        self.assertTrue(output["additionalContext"].endswith(GRAPH_MARKER))

    def test_silent_hook_augment_still_yields_the_instructions(self):
        claude = run_hook("claude", "SessionStart", None)
        self.assertEqual(
            claude["hookSpecificOutput"]["additionalContext"], INSTRUCTIONS.strip()
        )
        copilot = run_hook("copilot", "SessionStart", None)
        self.assertEqual(copilot["additionalContext"], INSTRUCTIONS.strip())


if __name__ == "__main__":
    unittest.main()
