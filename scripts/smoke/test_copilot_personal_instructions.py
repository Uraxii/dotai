import unittest

from support import SmokeTestCase, instruction_marker


class CopilotPersonalInstructionsTest(SmokeTestCase):
    harness = "copilot"

    def test_injects_both_instruction_sources(self):
        self.require_hook("personal-instructions", "SessionStart")
        requests = self.run_turn()
        for name in ("instructions.md", "main-agent-instructions.md"):
            with self.subTest(source=name):
                marker = instruction_marker(self.plugins["personal-instructions"] / name)
                self.assertTrue(marker and any(marker in request for request in requests),
                                f"Did not send {name} to the model")


if __name__ == "__main__":
    unittest.main()
