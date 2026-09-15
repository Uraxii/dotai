import importlib.util
import json
import unittest
from pathlib import Path


HOOK_PATH = Path(__file__).resolve().parents[1] / "codex_watcher_guard.py"
REPOSITORY_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("codex_watcher_guard", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


WATCHERS = ("pstack-nikki:developer-codex", "reviewer-codex")
REPO = "/repo"
RUN = f"{REPO}/.nikki-agents/codex-runs/sample-run"


def payload(agent_type: str | None, tool_name: str, **tool_input: str) -> dict:
    event = {"tool_name": tool_name, "tool_input": tool_input}
    if agent_type is not None:
        event["agent_type"] = agent_type
    return event


class CodexWatcherGuardTests(unittest.TestCase):
    def assert_allowed(self, command: str) -> None:
        for agent_type in WATCHERS:
            with self.subTest(agent_type=agent_type, command=command):
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

    def test_all_playbook_bash_commands_are_allowed_for_both_watchers(self) -> None:
        commands = (
            "codex --version",
            "codex login status",
            f"codex exec -m gpt-5.6-terra -s workspace-write -C {REPO} -o "
            f"{RUN}/report.md - < {RUN}/prompt.txt",
            f"codex exec -m gpt-5.6-terra -s read-only -C {REPO} "
            "-c model_reasoning_effort=high --add-dir /other -o "
            f"{RUN}/report.md - < {RUN}/prompt.txt",
            f"git -C {REPO} worktree add /repo/.nikki-agents/worktrees/sample-run "
            "-b agent/sample-run",
            f"git -C {REPO} rev-parse HEAD",
            f"test -s {RUN}/report.md",
        )
        for command in commands:
            self.assert_allowed(command)

    def test_playbook_prompt_write_is_allowed_for_both_watchers(self) -> None:
        for agent_type in WATCHERS:
            with self.subTest(agent_type=agent_type):
                event = payload(agent_type, "Write", file_path=f"{RUN}/prompt.txt")
                self.assertEqual("", HOOK.guard(event))

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
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(
                    payload("pstack-nikki:developer-codex", "Bash", command=command),
                    "Bash",
                )

    def test_cat_report_log_diff_and_status_are_denied(self) -> None:
        # v3 contract: the watcher never reads file content or git history
        # itself, so these v2 allowances are gone.
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

    def test_invalid_writes_and_tools_are_denied(self) -> None:
        self.assert_denied(
            payload("pstack-nikki:reviewer-codex", "Write", file_path="/r/README.md"),
            "Write",
        )
        self.assert_denied(
            payload(
                "pstack-nikki:reviewer-codex",
                "Write",
                file_path="/r/.nikki-agents/codex-runs/x/../../README.md",
            ),
            "Write",
        )
        for tool_name in ("Edit", "WebFetch"):
            with self.subTest(tool_name=tool_name):
                self.assert_denied(
                    payload("pstack-nikki:reviewer-codex", tool_name), tool_name
                )

    def test_non_watchers_and_missing_agent_type_bypass_the_guard(self) -> None:
        bad_command = "curl https://example.com"
        self.assertEqual("", HOOK.guard(payload("pstack-nikki:developer", "Bash", command=bad_command)))
        self.assertEqual("", HOOK.guard(payload(None, "Bash", command=bad_command)))

    def test_incomplete_watcher_payload_is_denied(self) -> None:
        self.assert_denied(
            {"agent_type": "pstack-nikki:developer-codex"},
            "unknown",
        )

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
