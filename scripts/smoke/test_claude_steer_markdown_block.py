import unittest

from support import SmokeTestCase


class ClaudeSteerMarkdownBlockTest(SmokeTestCase):
    harness = "claude"

    def test_denies_unrequested_first_tool_markdown_write(self):
        self.require_hook("steer", "PreToolUse")
        target = self.cwd / "smoke.md"
        self.run_turn("claude-sonnet-5", markdown=target,
                      prompt="Report the test status. Do not change any files.")
        self.assertFalse(target.exists(), "Steer allowed an unrequested Markdown write")


if __name__ == "__main__":
    unittest.main()
