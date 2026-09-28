import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


HOOK_PATH = Path(__file__).resolve().parents[1] / "codex_watcher_guard.py"
REPOSITORY_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("codex_watcher_guard", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


DEVELOPER = "pstack:developer-codex"
REVIEWER = "reviewer-codex"
WATCHERS = (DEVELOPER, REVIEWER)
RUN = "/repo/.agent-runs/sample-run-0a1b2c3d"
ALLOWED = f"pstack-codex-run {RUN}"
ONLY_COMMAND = "the only allowed command is pstack-codex-run"


def payload(agent_type: object, tool_name: str = "Bash", **tool_input) -> dict:
    return {
        "agent_type": agent_type,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def bash(agent_type: object, command: object, **extra) -> dict:
    return payload(agent_type, "Bash", command=command, **extra)


class ExplodingMapping(dict):
    """A tool_input whose .get() raises, to reach guard()'s fail-closed path."""

    def get(self, key, default=None):
        raise RuntimeError("tool_input exploded")


class PoisonedStr(str):
    """An agent_type that raises when guard() reads its watcher name."""

    def rpartition(self, sep):
        raise RuntimeError("agent_type exploded")


class GuardTests(unittest.TestCase):
    def assert_denied(self, event: dict, reason: str) -> None:
        decision = json.loads(HOOK.guard(event))["hookSpecificOutput"]
        self.assertEqual("PreToolUse", decision["hookEventName"])
        self.assertEqual("deny", decision["permissionDecision"])
        stated = decision["permissionDecisionReason"]
        self.assertTrue(stated.startswith(f"codex watcher guard: {reason}"), stated)

    def test_the_cli_on_an_absolute_run_is_allowed(self) -> None:
        for agent in WATCHERS:
            for run in (RUN, "/tmp/x/.agent-runs/a.b@c+d-e_f", f"{RUN}/"):
                with self.subTest(agent=agent, run=run):
                    self.assertEqual(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "allow",
                                "permissionDecisionReason": (
                                    "codex watcher guard: pstack-codex-run "
                                    "on one run directory"
                                ),
                            }
                        },
                        json.loads(HOOK.guard(bash(agent, f"pstack-codex-run {run}"))),
                    )

    def test_every_other_command_shape_is_denied(self) -> None:
        commands = (
            "codex exec -s workspace-write -C /tmp -",
            f"git -C {RUN}/worktree commit -m x",
            f"cat {RUN}/brief.md",
            f"pstack-codex-run {RUN}; rm -rf /",
            f"pstack-codex-run {RUN} && true",
            f"pstack-codex-run {RUN} | tee /tmp/x",
            f"pstack-codex-run {RUN} > /tmp/x",
            f"pstack-codex-run '{RUN}'",
            f'pstack-codex-run "{RUN}"',
            f"pstack-codex-run {RUN}$(id)",
            "pstack-codex-run ~/.agent-runs/x",
            "pstack-codex-run .agent-runs/sample-run",
            f"pstack-codex-run {RUN} {RUN}",
            f"pstack-codex-run {RUN} --extra",
            f"pstack-codex-run  {RUN}",
            f" pstack-codex-run {RUN}",
            f"pstack-codex-run {RUN}\n",
            f"pstack-codex-run {RUN}\nid",
            f"/usr/bin/pstack-codex-run {RUN}",
            f"PATH=/tmp pstack-codex-run {RUN}",
            "pstack-codex-run",
            "",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(bash(DEVELOPER, command), ONLY_COMMAND)

    def test_non_string_command_is_denied(self) -> None:
        self.assert_denied(bash(REVIEWER, ["pstack-codex-run", RUN]), ONLY_COMMAND)

    def test_background_bash_is_denied_even_for_the_allowed_command(self) -> None:
        event = bash(DEVELOPER, ALLOWED, run_in_background=True)
        self.assert_denied(event, "Bash must not run in the background")

    def test_other_tools_are_denied(self) -> None:
        for tool in ("Write", "Read", "Edit", "Agent"):
            with self.subTest(tool=tool):
                self.assert_denied(
                    payload(REVIEWER, tool, file_path=f"{RUN}/report.md"),
                    f"{tool} is not allowed for a Codex watcher",
                )

    def test_watcher_call_without_input_is_denied(self) -> None:
        event = {"agent_type": DEVELOPER, "tool_name": "Bash"}
        self.assert_denied(event, "the Bash call has no input")

    def test_non_watchers_are_not_guarded(self) -> None:
        for agent in (None, "pstack:developer", "reviewer", "codex", "x:y"):
            with self.subTest(agent=agent):
                self.assertEqual("", HOOK.guard(bash(agent, "rm -rf /")))
        self.assertEqual("", HOOK.guard({"tool_name": "Bash"}))

    def test_exception_for_a_watcher_payload_denies(self) -> None:
        event = payload(DEVELOPER)
        event["tool_input"] = ExplodingMapping()
        self.assert_denied(event, "the call could not be checked")

    def test_exception_for_a_non_watcher_payload_reraises(self) -> None:
        with self.assertRaises(RuntimeError):
            HOOK.guard(bash(PoisonedStr(DEVELOPER), ALLOWED))

    def test_main_exits_2_on_unparseable_stdin(self) -> None:
        with (
            mock.patch.object(sys, "stdin", io.StringIO("not json")),
            mock.patch.object(sys, "stderr", io.StringIO()) as fake_stderr,
        ):
            with self.assertRaises(SystemExit) as raised:
                HOOK.main()
        self.assertEqual(2, raised.exception.code)
        self.assertIn("codex watcher guard", fake_stderr.getvalue())

    def test_manifest_wires_the_guard_before_bash_and_write(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "hooks" / "hooks.json").read_text())
        self.assertIn("SessionStart", config["hooks"])
        self.assertEqual(
            {
                "matcher": "Bash|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/codex_watcher_guard.py",
                        "timeout": 5,
                    }
                ],
            },
            config["hooks"]["PreToolUse"][0],
        )


if __name__ == "__main__":
    unittest.main()
