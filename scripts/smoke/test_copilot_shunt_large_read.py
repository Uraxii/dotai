import unittest

from support import SmokeTestCase


class CopilotShuntLargeReadTest(SmokeTestCase):
    harness = "copilot"

    def test_large_read_is_denied(self):
        self.require_hook("shunt", "PreToolUse")
        (self.cwd / "large.txt").write_text("large read fixture\n" * 500)
        requests = self.run_turn(command="cat large.txt")
        self.assertTrue(
            any("bulk-reader" in request and "500-line file" in request for request in requests),
            "Shunt did not send a large-read denial to the model",
        )


if __name__ == "__main__":
    unittest.main()
