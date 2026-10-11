import json
import os
from pathlib import Path
import shlex
import subprocess
import unittest


PLUGIN = Path(__file__).resolve().parents[1]
GUARD = PLUGIN / "hooks/codex_watcher_commands.py"
STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
RUN = STATE / "pstack/codex-runs/fixture-one/writer"
LAUNCH = (f"python3 {shlex.quote(str(PLUGIN / 'scripts/prepare_codex_run.py'))}"
          " --launch <<'PSTACK_REQUEST'\n"
          "Claim bead fixture-one as developer-fixture-one. Work in /example/tree.\n"
          "PSTACK_REQUEST")
WAIT = (f"until grep -qs '\"pstack\":\"codex exited\"' {shlex.quote(str(RUN / 'codex.jsonl'))};"
        " do sleep 5; done; echo codex exited")


class GuardTests(unittest.TestCase):
    def check_call(self, tool, command, agent="pstack:developer-codex"):
        result = subprocess.run(["python3", str(GUARD)], input=json.dumps({
            "agent_type": agent, "tool_name": tool,
            "tool_input": {"command": command}}), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] if result.stdout else None

    def test_only_launch_and_fixed_wait_are_allowed(self):
        for agent in ("developer-codex", "pstack:developer-codex"):
            self.assertEqual(self.check_call("Bash", LAUNCH, agent), "allow")
            self.assertEqual(self.check_call("Monitor", WAIT, agent), "allow")
        for tool, command in (("Bash", "touch task.md"), ("Bash", "git status"),
                              ("Bash", LAUNCH + "\ngit status"),
                              ("Bash", LAUNCH.replace("'PSTACK_REQUEST'", "PSTACK_REQUEST")),
                              ("Bash", LAUNCH.replace("/example/tree", "$(touch task.md)")),
                              ("Bash", WAIT), ("Monitor", WAIT + "; touch task.md"),
                              ("Monitor", WAIT.replace(str(RUN), "/tmp/escape")),
                              ("Write", LAUNCH), ("Agent", LAUNCH)):
            with self.subTest(tool=tool, command=command):
                self.assertEqual(self.check_call(tool, command), "deny")

    def test_other_callers_have_no_output(self):
        for agent in ("", "poteto-agent", "pstack:poteto-agent", "other:developer-codex"):
            self.assertIsNone(self.check_call("Bash", "git status", agent))

    def test_invalid_hook_input_denies(self):
        for payload in ("broken JSON", "[]", json.dumps({"agent_type": "reviewer-codex"})):
            result = subprocess.run(["python3", str(GUARD)], input=payload,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_review_adapter_and_stateless_repeated_calls(self):
        launch = LAUNCH.replace(
            "Claim bead fixture-one as developer-fixture-one. Work in /example/tree.",
            "Review bead fixture-one at abc1234 in /example/tree.")
        wait = WAIT.replace("/writer/", "/reviewer/")
        for agent in ("reviewer-codex", "pstack:reviewer-codex"):
            self.assertEqual(self.check_call("Bash", launch, agent), "allow")
            self.assertEqual(self.check_call("Monitor", wait, agent), "allow")
            self.assertEqual(self.check_call("Bash", LAUNCH, agent), "deny")
            self.assertEqual(self.check_call("Bash", "touch task.md", agent), "deny")
            self.assertEqual(self.check_call("Bash", launch, agent), "allow")
            self.assertEqual(self.check_call("Bash", "git commit", agent), "deny")


if __name__ == "__main__":
    unittest.main()
