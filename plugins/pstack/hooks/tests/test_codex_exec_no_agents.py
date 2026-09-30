import importlib.util
import json
import unittest
from pathlib import Path


HOOK_PATH = Path(__file__).resolve().parents[1] / "codex_exec_no_agents.py"
SPEC = importlib.util.spec_from_file_location("codex_exec_no_agents", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


def payload(command: object, tool_name: str = "Bash", **extra) -> dict:
    tool_input = {"command": command, **extra}
    return {"tool_name": tool_name, "tool_input": tool_input}


def run_hook(event: dict) -> str:
    """The hook's stdout for `event`, run in-process against its own main()."""
    import io
    import sys
    from unittest import mock

    stdin = io.StringIO(json.dumps(event))
    stdout = io.StringIO()
    with mock.patch.object(sys, "stdin", stdin), \
        mock.patch.object(sys, "stdout", stdout):
        HOOK.main()
    return stdout.getvalue()


class RewriteCommandTests(unittest.TestCase):
    """`rewrite_command` directly, the matching logic under test."""

    def test_a_plain_codex_exec_gets_the_flag(self) -> None:
        self.assertEqual(
            HOOK.rewrite_command("codex exec 'do the thing'"),
            "codex -c agents.enabled=false exec 'do the thing'",
        )

    def test_a_codex_exec_with_flags_before_exec_gets_it_right_after_codex(
        self,
    ) -> None:
        self.assertEqual(
            HOOK.rewrite_command("codex -m gpt-5.6-terra exec 'go'"),
            "codex -c agents.enabled=false -m gpt-5.6-terra exec 'go'",
        )

    def test_codex_exec_resume_gets_the_flag(self) -> None:
        self.assertEqual(
            HOOK.rewrite_command("codex exec resume --last"),
            "codex -c agents.enabled=false exec resume --last",
        )

    def test_a_command_that_already_has_the_flag_is_unchanged(self) -> None:
        command = "codex exec -c agents.enabled=false 'do the thing'"
        self.assertEqual(HOOK.rewrite_command(command), command)

    def test_two_chained_codex_exec_calls_both_get_the_flag(self) -> None:
        self.assertEqual(
            HOOK.rewrite_command("codex exec A && codex exec B"),
            "codex -c agents.enabled=false exec A && "
            "codex -c agents.enabled=false exec B",
        )

    def test_codex_review_gets_the_flag(self) -> None:
        self.assertEqual(
            HOOK.rewrite_command("codex -s read-only review --base develop"),
            "codex -c agents.enabled=false -s read-only review --base develop",
        )

    def test_codex_review_with_the_flag_is_unchanged(self) -> None:
        command = "codex -c agents.enabled=false review --base develop"
        self.assertEqual(HOOK.rewrite_command(command), command)

    def test_codex_without_exec_is_unchanged(self) -> None:
        for command in ("codex --version", "codex login status"):
            with self.subTest(command=command):
                self.assertEqual(HOOK.rewrite_command(command), command)

    def test_echo_codex_exec_in_quotes_is_not_mangled(self) -> None:
        command = 'echo "codex exec is a subcommand"'
        self.assertEqual(HOOK.rewrite_command(command), command)

    def test_a_path_containing_codex_exec_is_not_mangled(self) -> None:
        command = "/tmp/codex/exec.sh --help"
        self.assertEqual(HOOK.rewrite_command(command), command)

    def test_a_non_codex_command_is_unchanged(self) -> None:
        command = "git status"
        self.assertEqual(HOOK.rewrite_command(command), command)


class MainHookTests(unittest.TestCase):
    """The hook's stdin/stdout contract, including passthrough."""

    def test_a_bash_codex_exec_call_is_rewritten_via_updated_input(self) -> None:
        event = payload("codex exec 'go'", description="run codex",
                        timeout=600000)
        output = run_hook(event)
        decision = json.loads(output)["hookSpecificOutput"]
        self.assertEqual("PreToolUse", decision["hookEventName"])
        self.assertNotIn("permissionDecision", decision)
        self.assertEqual(
            "codex -c agents.enabled=false exec 'go'",
            decision["updatedInput"]["command"],
        )
        self.assertEqual("run codex", decision["updatedInput"]["description"])
        self.assertEqual(600000, decision["updatedInput"]["timeout"])

    def test_a_non_matching_command_prints_nothing(self) -> None:
        self.assertEqual(run_hook(payload("git status")), "")

    def test_a_non_bash_tool_prints_nothing(self) -> None:
        self.assertEqual(
            run_hook(payload("codex exec x", tool_name="Write")), "")

    def test_malformed_json_prints_nothing(self) -> None:
        import io
        import sys
        from unittest import mock

        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO("not json")), \
            mock.patch.object(sys, "stdout", stdout):
            HOOK.main()
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
