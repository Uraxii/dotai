import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


HOOK_PATH = Path(__file__).resolve().parents[1] / "opus_5_reduce_output.py"
REPOSITORY_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("opus_5_reduce_output", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


def assistant(model="claude-opus-5", tools=(), sidechain=False):
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {
            "model": model,
            "content": [{"type": "tool_use", "name": name} for name in tools],
        },
    }


def user_prompt(text="do the thing"):
    return {"type": "user", "message": {"content": text}}


WORKING_TURN = [
    user_prompt(),
    assistant(tools=["Read", "Grep", "Edit", "Bash", "Edit", "Bash"]),
]


class Opus5ReduceOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(
            self.enterContext(tempfile.TemporaryDirectory())
        )
        # Never let a test touch the user's real ~/.claude/clean-recap.log,
        # and never let an ambient override decide a gate under test.
        environment = {**os.environ, "CLEAN_RECAP_LOG": str(self.log_path)}
        environment.pop("CLEAN_RECAP_MODEL_PATTERN", None)
        self.environment = environment
        self.enterContext(mock.patch.dict(os.environ, environment, clear=True))

    @property
    def log_path(self) -> Path:
        return self.directory / "clean-recap.log"

    def transcript(self, name: str, entries: list[dict]) -> str:
        path = self.directory / f"{name}.jsonl"
        path.write_text(
            "\n".join(json.dumps(entry) for entry in entries) + "\n",
            encoding="utf-8",
        )
        return str(path)

    def decide(self, payload: dict) -> str:
        """Run the hook's main() on a Stop envelope; "block" or "allow"."""
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))):
            with redirect_stdout(stdout):
                exit_code = HOOK.main()

        self.assertEqual(0, exit_code, "a Stop hook must always exit 0")
        printed = stdout.getvalue().strip()
        if not printed:
            return "allow"
        self.assertEqual(
            {"decision": "block", "reason": HOOK.RECAP_INSTRUCTION},
            json.loads(printed),
        )
        return "block"

    # -- manifest wiring ---------------------------------------------------

    def test_claude_manifest_installs_the_stop_hook_without_a_matcher(
        self,
    ) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / "hooks" / "hooks.json").read_text()
        )

        stop_entries = config["hooks"]["Stop"]
        # One entry only: a duplicated Stop key silently loses a hook.
        self.assertEqual(1, len(stop_entries))
        stop_entry = stop_entries[0]
        # Stop is not tied to a tool, so it takes no matcher.
        self.assertNotIn("matcher", stop_entry)
        hook = stop_entry["hooks"][0]
        self.assertEqual("command", hook["type"])
        self.assertEqual(
            "${CLAUDE_PLUGIN_ROOT}/hooks/opus_5_reduce_output.py", hook["command"]
        )
        self.assertEqual(10, hook["timeout"])
        self.assertTrue(HOOK_PATH.is_file())
        self.assertTrue(os.access(HOOK_PATH, os.X_OK))

    def test_sibling_manifests_do_not_install_the_stop_hook(self) -> None:
        # Codex documents no turn-end event, and Copilot's agentStop envelope
        # is camelCase, so its stopHookActive loop guard would never trip.
        codex = json.loads(
            (REPOSITORY_ROOT / "hooks" / "codex-hooks.json").read_text()
        )
        copilot = json.loads((REPOSITORY_ROOT / "hooks.json").read_text())

        self.assertNotIn("Stop", codex["hooks"])
        self.assertNotIn("opus_5_reduce_output", json.dumps(copilot))

    # -- the gate ----------------------------------------------------------

    def test_fresh_turn_of_real_work_blocks(self) -> None:
        payload = {"transcript_path": self.transcript("work", WORKING_TURN)}

        self.assertEqual("block", self.decide(payload))
        self.assertIn("BLOCK", self.log_path.read_text(encoding="utf-8"))

    def test_a_turn_that_did_nothing_still_asks_for_a_recap(self) -> None:
        """The regression the edit gate caused: this user delegates every
        edit to a subagent, so the main turn window sees no edits and no
        tool calls. The old gate allowed all 198 logged invocations."""
        entries = [user_prompt(), assistant(tools=[])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("idle", entries)}),
        )

    def test_a_read_only_turn_asks_for_a_recap(self) -> None:
        """Replaces the old "wrote no code allows" case. Writing code is no
        longer part of the gate."""
        entries = [user_prompt(), assistant(tools=["Read"] * 8)]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("read", entries)}),
        )

    def test_a_two_tool_turn_asks_for_a_recap(self) -> None:
        """Replaces the old tool-call floor case. There is no floor."""
        entries = [user_prompt(), assistant(tools=["Edit", "Bash"])]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("small", entries)}),
        )

    # -- loop guard --------------------------------------------------------

    def test_second_stop_allows_so_the_session_can_end(self) -> None:
        payload = {
            "stop_hook_active": True,
            "transcript_path": self.transcript("work", WORKING_TURN),
        }

        self.assertEqual("allow", self.decide(payload))
        self.assertIn("stand down", self.log_path.read_text(encoding="utf-8"))

    def test_absent_stop_hook_active_still_blocks(self) -> None:
        payload = {"transcript_path": self.transcript("work", WORKING_TURN)}

        self.assertNotIn("stop_hook_active", payload)
        self.assertEqual("block", self.decide(payload))

    def test_stop_hook_active_as_a_string_allows(self) -> None:
        payload = {
            "stop_hook_active": "true",
            "transcript_path": self.transcript("work", WORKING_TURN),
        }

        self.assertEqual("allow", self.decide(payload))

    # -- malformed input ---------------------------------------------------

    def test_empty_payload_allows(self) -> None:
        self.assertEqual("allow", self.decide({}))

    def test_missing_transcript_file_allows(self) -> None:
        self.assertEqual(
            "allow",
            self.decide({"transcript_path": str(self.directory / "gone.jsonl")}),
        )
        self.assertIn(
            "no readable transcript_path",
            self.log_path.read_text(encoding="utf-8"),
        )

    def test_transcript_path_pointing_at_a_directory_allows(self) -> None:
        self.assertEqual(
            "allow", self.decide({"transcript_path": str(self.directory)})
        )

    # -- model matching ----------------------------------------------------

    def test_unmatched_model_allows(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                model="claude-sonnet-4-5",
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
            ),
        ]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("sonnet", entries)}),
        )
        self.assertIn(
            "model does not match", self.log_path.read_text(encoding="utf-8")
        )

    def test_fable_model_blocks(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                model="claude-fable-5-1",
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
            ),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("fable", entries)}),
        )

    def test_opus_5_model_still_blocks(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                model="claude-opus-5",
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
            ),
        ]

        self.assertEqual(
            "block",
            self.decide({"transcript_path": self.transcript("opus", entries)}),
        )

    def test_sidechain_work_does_not_count(self) -> None:
        entries = [
            user_prompt(),
            assistant(
                tools=["Read", "Edit", "Bash", "Edit", "Read", "Bash"],
                sidechain=True,
            ),
        ]

        self.assertEqual(
            "allow",
            self.decide({"transcript_path": self.transcript("side", entries)}),
        )

    def test_the_model_read_is_the_one_that_answered_last(self) -> None:
        entries = [
            user_prompt("older turn"),
            assistant(model="claude-sonnet-5", tools=["Read"]),
            user_prompt("this turn"),
            assistant(model="claude-opus-5", tools=["Read"]),
        ]

        self.assertEqual(
            "claude-opus-5",
            HOOK._current_model(Path(self.transcript("order", entries))),
        )

    def test_no_assistant_reply_leaves_the_model_unknown(self) -> None:
        entries = [user_prompt("hi")]

        self.assertEqual(
            "-", HOOK._current_model(Path(self.transcript("bare", entries)))
        )

    # -- logging and real invocation ---------------------------------------

    def test_every_decision_is_logged_to_the_configured_path(self) -> None:
        self.decide({"transcript_path": self.transcript("work", WORKING_TURN)})
        self.decide({})

        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(2, len(lines))
        self.assertIn("BLOCK", lines[0])
        self.assertIn("allow", lines[1])

    def test_runs_as_an_executable_the_way_the_manifest_invokes_it(self) -> None:
        result = subprocess.run(
            [str(HOOK_PATH)],
            input=json.dumps(
                {"transcript_path": self.transcript("work", WORKING_TURN)}
            ),
            capture_output=True,
            text=True,
            env=self.environment,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            {"decision": "block", "reason": HOOK.RECAP_INSTRUCTION},
            json.loads(result.stdout),
        )


if __name__ == "__main__":
    unittest.main()
