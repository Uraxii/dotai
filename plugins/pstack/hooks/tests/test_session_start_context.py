import importlib.util
import json
import unittest
from pathlib import Path


HOOK_PATH = Path(__file__).resolve().parents[1] / "session_start_context.py"
REPOSITORY_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("session_start_context", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


class SessionStartContextTests(unittest.TestCase):
    def test_claude_output_is_plain_reminder_text(self) -> None:
        output = HOOK.build_output("claude", None)

        self.assertEqual(HOOK.REMINDER_TEXT, output)

    def test_codex_output_is_one_json_line(self) -> None:
        output = HOOK.build_output("codex", "SessionStart")

        self.assertEqual(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": HOOK.REMINDER_TEXT,
                }
            },
            json.loads(output),
        )

    def test_claude_manifest_wires_session_start(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "hooks" / "hooks.json").read_text())

        session_start = config["hooks"]["SessionStart"][0]
        self.assertEqual("startup|clear|compact", session_start["matcher"])
        session_command = session_start["hooks"][0]["command"]
        self.assertIn("session_start_context.py --harness claude", session_command)

    def test_copilot_output_is_additional_context_json(self) -> None:
        output = HOOK.build_output("copilot", "SessionStart")
        parsed = json.loads(output)

        self.assertEqual({"additionalContext": HOOK.REMINDER_TEXT}, parsed)

    def test_opencode_output_is_plain_reminder_text(self) -> None:
        output = HOOK.build_output("opencode", None)

        self.assertEqual(HOOK.REMINDER_TEXT, output)

    def test_hermes_output_injects_context_on_first_turn(self) -> None:
        output = HOOK.build_hermes_output({"extra": {"is_first_turn": True}})

        self.assertEqual({"context": HOOK.REMINDER_TEXT}, json.loads(output))

    def test_hermes_output_is_noop_on_later_turns(self) -> None:
        output = HOOK.build_hermes_output({"extra": {"is_first_turn": False}})

        self.assertEqual({}, json.loads(output))

    def test_hermes_output_is_noop_when_extra_is_missing(self) -> None:
        # A malformed or unexpected payload must never risk injecting the
        # reminder on every turn; treat "unknown" the same as "not first".
        output = HOOK.build_hermes_output({})

        self.assertEqual({}, json.loads(output))

    def test_copilot_manifest_wires_session_start(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "hooks.json").read_text())

        session_start = config["hooks"]["sessionStart"][0]
        self.assertIn(
            "--harness copilot --event SessionStart",
            session_start["bash"],
        )
        self.assertIn(
            '"$PLUGIN_ROOT/hooks/session_start_context.py"',
            session_start["bash"],
        )

    def test_codex_manifest_wires_session_start_only(self) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / "hooks" / "codex-hooks.json").read_text()
        )

        entry = config["hooks"]["SessionStart"][0]
        self.assertNotIn("matcher", entry)
        self.assertIn(
            "session_start_context.py --harness codex --event SessionStart",
            entry["hooks"][0]["command"],
        )
        self.assertNotIn("PostCompact", config["hooks"])


if __name__ == "__main__":
    unittest.main()
