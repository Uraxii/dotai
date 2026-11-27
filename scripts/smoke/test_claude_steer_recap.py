import unittest

from support import RECAP, SmokeTestCase


class ClaudeSteerRecapTest(SmokeTestCase):
    harness = "claude"

    def test_recaps_only_mutations_on_supported_models(self):
        self.require_hook("steer", "Stop")
        (self.cwd / "small.txt").write_text("read-only fixture\n")
        readonly = self.run_turn(command="cat small.txt")
        self.assertEqual(sum(RECAP in request for request in readonly), 0, "Read-only Fable turn recapped")
        for model, expected in (("claude-opus-5", 1), ("claude-fable-5", 1), ("claude-sonnet-5", 0)):
            with self.subTest(model=model):
                target = self.cwd / f"{model}.txt"
                requests = self.run_turn(model, f"touch {target.name}")
                self.assertTrue(target.is_file(), f"{target.name} was not written")
                self.assertEqual(sum(RECAP in request for request in requests), expected)


if __name__ == "__main__":
    unittest.main()
