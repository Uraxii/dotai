import json
from pathlib import Path
import unittest

from support import RECAP, SmokeTestCase, copilot_observer, replay_copilot_stop


class CopilotSteerRecapTest(SmokeTestCase):
    harness = "copilot"

    def assert_recap_count(self, requests, expected, scenario):
        observed = self.home / "stop-probe.jsonl"
        self.assertTrue(observed.is_file(), "Did not observe Copilot agentStop")
        observation = json.loads(observed.read_text().splitlines()[0])
        actual = sum(RECAP in request for request in requests)
        if actual or observation["transcript_exists"]:
            self.assertEqual(actual, expected, scenario)
            return

        payload = observation["payload"]
        self.assertTrue(Path(payload["transcriptPath"]).is_file(), "Copilot did not save the transcript")
        print(f"\n{scenario}: Copilot ran agentStop before saving the transcript; replaying the event.", flush=True)
        output = replay_copilot_stop(self.plugins["steer"], self.env, self.cwd, payload)
        self.assertEqual(sum(RECAP in result for result in output), expected, f"{scenario}: agentStop replay")

    def test_recaps_only_mutations_on_supported_models(self):
        self.require_hook("steer", "agentStop")
        self.plugins["stop-observer"] = copilot_observer(self.scratch)
        (self.cwd / "small.txt").write_text("read-only fixture\n")
        readonly = self.run_turn(command="cat small.txt")
        self.assert_recap_count(readonly, 0, "Read-only Fable turn")
        observed = self.home / "stop-probe.jsonl"
        for model, expected in (("claude-opus-5", 1), ("claude-fable-5", 1), ("claude-sonnet-5", 0)):
            with self.subTest(model=model):
                target = self.cwd / f"{model}.txt"
                observed.unlink(missing_ok=True)
                requests = self.run_turn(model, f"touch {target.name}")
                self.assertTrue(target.is_file(), f"{target.name} was not written")
                self.assert_recap_count(requests, expected, model)


if __name__ == "__main__":
    unittest.main()
