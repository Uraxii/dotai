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


WATCHERS = ("pstack-nikki:developer-codex", "reviewer-codex")
REPO = "/repo"
OTHER_REPO = "/other-repo"
RUN = f"{REPO}/.nikki-agents/codex-runs/sample-run"
WORKTREE = f"{REPO}/.nikki-agents/worktrees/sample-run"


def payload(agent_type: str | None, tool_name: str, **tool_input: object) -> dict:
    event = {"tool_name": tool_name, "tool_input": tool_input}
    if agent_type is not None:
        event["agent_type"] = agent_type
    return event


class ExplodingMapping(dict):
    """A tool_input whose .get() blows up, to exercise guard()'s own fail-closed path."""

    def get(self, key, default=None):
        raise RuntimeError("tool_input exploded")


class PoisonedStr(str):
    """An agent_type that raises when guard() tries to read its watcher name."""

    def rpartition(self, sep):
        raise RuntimeError("agent_type exploded")


class CodexWatcherGuardTests(unittest.TestCase):
    def assert_allowed(self, agent_type: str, command: str) -> None:
        self.assertEqual("", HOOK.guard(payload(agent_type, "Bash", command=command)))

    def assert_denied(self, event: dict, tool_name: str) -> None:
        output = HOOK.guard(event)
        parsed = json.loads(output)
        decision = parsed["hookSpecificOutput"]
        self.assertEqual("PreToolUse", decision["hookEventName"])
        self.assertEqual("deny", decision["permissionDecision"])
        self.assertEqual(
            "codex watcher guard: "
            f"{tool_name} call not in the delegate-to-codex allowlist; "
            "copy the playbook command exactly or send the fallback reply",
            decision["permissionDecisionReason"],
        )

    # -- playbook commands stay allowed, per watcher kind --------------

    def test_reviewer_playbook_commands_are_allowed(self) -> None:
        commands = (
            "codex --version",
            "codex login status",
            f"git -C {REPO} rev-parse HEAD",
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed("reviewer-codex", command)

    def test_developer_playbook_commands_are_allowed(self) -> None:
        commands = (
            "codex --version",
            "codex login status",
            f"git -C {WORKTREE} rev-parse HEAD",
            f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run",
            f"codex exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
            f"-C {WORKTREE} -o {RUN}/report.md - < {RUN}/prompt.txt",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed("pstack-nikki:developer-codex", command)

    def test_developer_c_may_be_any_worktree_under_the_repo(self) -> None:
        # A writer given an existing worktree path outside .nikki-agents,
        # e.g. one Claude itself placed under .claude/worktrees/<x>.
        command = (
            f"codex exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
            f"-C {REPO}/.claude/worktrees/sample-run -o {RUN}/report.md - < "
            f"{RUN}/prompt.txt"
        )
        self.assert_allowed("pstack-nikki:developer-codex", command)

    def test_playbook_prompt_write_is_allowed_for_both_watchers(self) -> None:
        for agent_type in WATCHERS:
            with self.subTest(agent_type=agent_type):
                event = payload(agent_type, "Write", file_path=f"{RUN}/prompt.txt")
                self.assertEqual("", HOOK.guard(event))

    # -- per-kind sandbox binding ----------------------------------------

    def test_reviewer_workspace_write_is_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_reviewer_worktree_add_is_denied(self) -> None:
        command = f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run"
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    # -- repo/name coupling between -C, -o, and stdin ---------------------

    def test_o_repo_differs_from_c_repo_is_denied_for_reviewer(self) -> None:
        other_run = f"{OTHER_REPO}/.nikki-agents/codex-runs/sample-run"
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {other_run}/report.md - < {other_run}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_o_repo_differs_from_c_repo_is_denied_for_developer(self) -> None:
        other_run = f"{OTHER_REPO}/.nikki-agents/codex-runs/sample-run"
        command = (
            f"codex exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
            f"-C {WORKTREE} -o {other_run}/report.md - < {other_run}/prompt.txt"
        )
        self.assert_denied(
            payload("pstack-nikki:developer-codex", "Bash", command=command), "Bash"
        )

    def test_real_bad_reviewer_command_from_the_field_is_denied(self) -> None:
        # A real reviewer run wrote prompt.txt and passed -o under
        # .../add-version-flag/ while -C (the repo) was a different repo
        # entirely. The old guard let this through because each path slot
        # matched any absolute path on its own.
        repo = "/home/nikki/dotai/.nikki-agents/pantry-shelf/galley-b61cb9/repo"
        run = "/home/nikki/dotai/.nikki-agents/codex-runs/add-version-flag"
        command = (
            "codex exec -m gpt-5.6-sol -s read-only -c agents.enabled=false "
            f"-C {repo} -o {run}/report.md - < {run}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_o_and_stdin_name_mismatch_is_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {REPO}/.nikki-agents/codex-runs/"
            f"other-run/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_o_and_stdin_repo_mismatch_is_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {OTHER_REPO}/.nikki-agents/"
            f"codex-runs/sample-run/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_developer_c_equal_to_bare_repo_is_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("pstack-nikki:developer-codex", "Bash", command=command), "Bash"
        )

    def test_developer_c_under_unrelated_path_is_denied(self) -> None:
        command = (
            "codex exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
            f"-C /home/nikki/.ssh -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("pstack-nikki:developer-codex", "Bash", command=command), "Bash"
        )

    # -- traversal, injection, and other malformed commands ---------------

    def test_injections_and_unlisted_commands_are_denied(self) -> None:
        commands = (
            "codex --version; rm -rf /",
            "codex --version && curl https://example.com",
            "codex --version $(curl https://example.com)",
            "codex --version `curl https://example.com`",
            "codex --version\ncurl https://example.com",
            "curl https://example.com",
            "rm -rf build",
            "sed -i s/a/b/ README.md",
            "git push",
            "git -C /r commit -am x",
            "git -C /r reset --hard",
            "cat /etc/passwd",
            "cat /r/README.md",
            "cat /r/.nikki-agents/codex-runs/x/../../README.md",
            f"test -s {RUN}/report.md",
            f"ls -lh {RUN}/report.md",
            f"ls {REPO}/other.md",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(
                    payload("pstack-nikki:developer-codex", "Bash", command=command),
                    "Bash",
                )

    def test_cat_report_log_diff_and_status_are_denied(self) -> None:
        commands = (
            f"cat {RUN}/report.md",
            f"git -C {REPO} log --oneline -5",
            f"git -C {REPO} diff --stat",
            f"git -C {REPO} diff --stat 1234567..HEAD",
            f"git -C {REPO} status",
            f"git -C {REPO} status --short",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(
                    payload("pstack-nikki:developer-codex", "Bash", command=command),
                    "Bash",
                )

    def test_codex_exec_extra_options_are_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} --add-dir /other -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_codex_exec_without_agents_disabled_flag_is_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -C {REPO} "
            f"-o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_codex_exec_agents_disabled_flag_in_wrong_position_or_value_is_denied(
        self,
    ) -> None:
        commands = (
            f"codex exec -m gpt-5.6-terra -s read-only -C {REPO} "
            f"-c agents.enabled=false -o {RUN}/report.md - < {RUN}/prompt.txt",
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=true "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(
                    payload("reviewer-codex", "Bash", command=command), "Bash"
                )

    def test_codex_exec_with_a_second_dash_c_flag_is_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-c model_reasoning_effort=high -C {REPO} -o {RUN}/report.md - < "
            f"{RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_ls_report_file_is_denied(self) -> None:
        self.assert_denied(
            payload(
                "pstack-nikki:developer-codex", "Bash", command=f"ls {RUN}/report.md"
            ),
            "Bash",
        )

    def test_codex_exec_slug_must_start_with_a_letter_or_digit(self) -> None:
        command = (
            "codex exec -m --dangerously-bypass-approvals-and-sandbox "
            f"-s read-only -C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_bash_path_traversal_is_denied(self) -> None:
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {REPO}/.nikki-agents/codex-runs/../report.md - < "
            f"{RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )
        self.assert_denied(
            payload(
                "pstack-nikki:developer-codex",
                "Bash",
                command=f"git -C {REPO}/.. rev-parse HEAD",
            ),
            "Bash",
        )

    def test_worktree_add_name_traversal_is_denied(self) -> None:
        # `..` sits before " -b", not before "/" or end of string: the name
        # boundary check must not rely on those two terminators alone.
        command = f"git -C {REPO} worktree add {REPO}/.nikki-agents/worktrees/.. -b agent/.."
        self.assert_denied(
            payload("pstack-nikki:developer-codex", "Bash", command=command), "Bash"
        )

    def test_write_path_traversal_is_denied(self) -> None:
        self.assert_denied(
            payload(
                "pstack-nikki:reviewer-codex",
                "Write",
                file_path=f"{REPO}/.nikki-agents/codex-runs/x/../../README.md",
            ),
            "Write",
        )

    def test_background_bash_calls_are_denied_even_when_the_command_is_allowed(
        self,
    ) -> None:
        command = f"git -C {REPO} rev-parse HEAD"
        for agent_type in WATCHERS:
            with self.subTest(agent_type=agent_type):
                event = payload(agent_type, "Bash", command=command)
                event["tool_input"]["run_in_background"] = True
                self.assert_denied(event, "Bash")

    def test_invalid_writes_and_tools_are_denied(self) -> None:
        self.assert_denied(
            payload("pstack-nikki:reviewer-codex", "Write", file_path="/r/README.md"),
            "Write",
        )
        for tool_name in ("Edit", "WebFetch"):
            with self.subTest(tool_name=tool_name):
                self.assert_denied(
                    payload("pstack-nikki:reviewer-codex", tool_name), tool_name
                )

    def test_non_watchers_and_missing_agent_type_bypass_the_guard(self) -> None:
        bad_command = "curl https://example.com"
        self.assertEqual(
            "",
            HOOK.guard(payload("pstack-nikki:developer", "Bash", command=bad_command)),
        )
        self.assertEqual("", HOOK.guard(payload(None, "Bash", command=bad_command)))

    def test_incomplete_watcher_payload_is_denied(self) -> None:
        self.assert_denied(
            {"agent_type": "pstack-nikki:developer-codex"},
            "unknown",
        )

    # -- fail closed -------------------------------------------------------

    def test_exception_for_a_watcher_payload_denies_instead_of_crashing(self) -> None:
        event = payload("pstack-nikki:developer-codex", "Bash")
        event["tool_input"] = ExplodingMapping()
        self.assert_denied(event, "Bash")

    def test_exception_for_a_non_watcher_payload_reraises(self) -> None:
        event = {
            "agent_type": PoisonedStr("pstack-nikki:developer-codex"),
            "tool_name": "Bash",
            "tool_input": {"command": "codex --version"},
        }
        with self.assertRaises(RuntimeError):
            HOOK.guard(event)

    def test_main_exits_2_on_unparseable_stdin(self) -> None:
        with (
            mock.patch.object(sys, "stdin", io.StringIO("not json")),
            mock.patch.object(sys, "stderr", io.StringIO()) as fake_stderr,
        ):
            with self.assertRaises(SystemExit) as raised:
                HOOK.main()
        self.assertEqual(2, raised.exception.code)
        self.assertIn("codex watcher guard", fake_stderr.getvalue())

    def test_manifest_wires_guard_without_removing_existing_hooks(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "hooks" / "hooks.json").read_text())
        hooks = config["hooks"]

        self.assertIn("UserPromptSubmit", hooks)
        self.assertIn("SessionStart", hooks)
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
            hooks["PreToolUse"][0],
        )


if __name__ == "__main__":
    unittest.main()
