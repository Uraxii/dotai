import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HOOK_PATH = Path(__file__).resolve().parents[1] / "handoff-token-flag.py"
REPOSITORY_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("handoff_token_flag", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


class HandoffTokenFlagTests(unittest.TestCase):
    def test_plugin_manifests_install_the_hook(self) -> None:
        claude = json.loads(
            (REPOSITORY_ROOT / "hooks" / "hooks.json").read_text()
        )
        codex_manifest = json.loads(
            (REPOSITORY_ROOT / ".codex-plugin" / "plugin.json").read_text()
        )
        codex = json.loads(
            (REPOSITORY_ROOT / "hooks" / "codex-hooks.json").read_text()
        )
        copilot = json.loads((REPOSITORY_ROOT / "hooks.json").read_text())

        self.assertEqual("./hooks/codex-hooks.json", codex_manifest["hooks"])
        for config in (claude, codex):
            prompt_hooks = config["hooks"]["UserPromptSubmit"]
            prompt_command = prompt_hooks[0]["hooks"][0]["command"]
            self.assertIn("handoff-token-flag.py --mode context", prompt_command)

        stop_hooks = copilot["hooks"]["agentStop"]
        stop_command = stop_hooks[0]["bash"]
        self.assertIn("handoff-token-flag.py --mode stop", stop_command)

    def test_reads_claude_usage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "transcript.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "message": {
                            "usage": {
                                "input_tokens": 100_000,
                                "cache_read_input_tokens": 90_000,
                                "cache_creation_input_tokens": 20_000,
                            }
                        }
                    }
                )
                + "\n"
            )

            self.assertEqual(210_000, HOOK._last_usage_tokens(transcript))

    def test_reads_codex_usage_without_double_counting_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "rollout.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "last_token_usage": {
                                    "input_tokens": 210_000,
                                    "cached_input_tokens": 150_000,
                                }
                            },
                        },
                    }
                )
                + "\n"
            )

            self.assertEqual(210_000, HOOK._last_usage_tokens(transcript))

    def test_falls_back_to_transcript_size_when_usage_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "session.jsonl"
            transcript.write_text("x" * 840_000)

            self.assertEqual(210_000, HOOK._last_usage_tokens(transcript))

    def test_stop_mode_forces_one_continuation_per_band(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_directory = Path(directory) / "state"
            first = HOOK._response_for_crossing(
                tokens=210_000,
                session_id="session-1",
                mode="stop",
                state_directory=state_directory,
            )
            repeated = HOOK._response_for_crossing(
                tokens=220_000,
                session_id="session-1",
                mode="stop",
                state_directory=state_directory,
            )

            self.assertEqual("block", json.loads(first)["decision"])
            self.assertEqual("", repeated)


if __name__ == "__main__":
    unittest.main()
