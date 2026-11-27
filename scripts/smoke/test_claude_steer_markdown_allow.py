import unittest

from support import SmokeTestCase


class ClaudeSteerMarkdownAllowTest(SmokeTestCase):
    harness = "claude"

    def test_allows_requested_first_tool_markdown_write(self):
        self.require_hook("steer", "PreToolUse")
        target = self.cwd / "smoke.md"
        self.run_turn("claude-sonnet-5", markdown=target, prompt="Please write to smoke.md.")
        self.assertTrue(target.is_file(), "Steer blocked an explicitly requested Markdown write")


if __name__ == "__main__":
    unittest.main()
