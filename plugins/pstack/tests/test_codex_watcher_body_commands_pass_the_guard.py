"""The watcher body's step 6 commands must survive `codex_watcher_guard.py`.

The guard matches a whole command against a regex, so the watcher body's
prose is the guard's contract. One extra space, a reordered flag, or double
quotes where the regex wants single ones ships a watcher whose every Codex
run is denied, with every other test still green.

This test therefore reads the commands out of the watcher body instead of
restating them. A doc edit the guard cannot match fails here.
"""

import importlib.util
import re
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
BODY = PLUGIN_ROOT / "skills/poteto-mode/references/codex-watcher-body.md"
HOOK_PATH = PLUGIN_ROOT / "hooks/codex_watcher_guard.py"
SPEC = importlib.util.spec_from_file_location("codex_watcher_guard", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)

REPO = "/workspace/repo"
RUN_NAME = "sample-run"
WORKTREE = f"{REPO}/.nikki-agents/worktrees/{RUN_NAME}"
# The watcher body writes DIR's basename as its own placeholder, because git
# keys `.git/worktrees/<...>` on that basename and not on the run name.
WORKTREE_BASENAME = WORKTREE.rsplit("/", 1)[1]
CODEX = "codex-agent"
MODEL = "gpt-5.6-terra"

STEP_COMMAND = re.compile(r"`(CODEX exec [^`]+)`")
ROOTS_LINE = "-c 'sandbox_workspace_write.writable_roots="
PLACEHOLDER = re.compile(r"<[A-Za-z][A-Za-z -]*>")


def roots_flag(text: str) -> str:
    """The one fenced ROOTS line the watcher body tells a writer to type."""
    lines = [line.strip() for line in text.splitlines()]
    flags = [line for line in lines if line.startswith(ROOTS_LINE)]
    assert len(flags) == 1, f"{BODY} holds {len(flags)} ROOTS lines, expected 1"
    return flags[0]


def step_commands(text: str) -> dict[str, str]:
    """The step 6 `codex exec` templates, keyed by sandbox mode."""
    found = STEP_COMMAND.findall(text)
    assert len(found) == 2, f"{BODY} holds {len(found)} step 6 commands, expected 2"
    return {
        "read-only" if "-s read-only" in command else "workspace-write": command
        for command in found
    }


def fill(template: str, *, directory: str, roots: str) -> str:
    """The template as a watcher would type it, with every value filled in."""
    filled = template.replace(" ROOTS", f" {roots}" if roots else "")
    for token, value in (
        ("CODEX", CODEX),
        ("<MODEL>", MODEL),
        ("<DIR>", directory),
        ("<RUN>", f"{REPO}/.nikki-agents/codex-runs/{RUN_NAME}"),
        ("<repo>", REPO),
        ("<name>", RUN_NAME),
        ("<basename of DIR>", WORKTREE_BASENAME),
    ):
        filled = filled.replace(token, value)
    return filled


class CodexWatcherBodyCommandsTests(unittest.TestCase):
    def setUp(self) -> None:
        text = BODY.read_text()
        self.roots = roots_flag(text)
        self.commands = step_commands(text)

    def assert_allowed(self, agent_type: str, command: str) -> None:
        self.assertEqual(
            "",
            HOOK.guard(
                {
                    "agent_type": agent_type,
                    "tool_name": "Bash",
                    "tool_input": {"command": command},
                }
            ),
            f"the guard denies a command taken verbatim from {BODY}: {command}",
        )

    def writer_command(self, *, roots: str | None = None) -> str:
        return fill(
            self.commands["workspace-write"],
            directory=WORKTREE,
            roots=self.roots if roots is None else roots,
        )

    def test_every_value_in_the_body_commands_is_substituted(self) -> None:
        # A new placeholder in the body would otherwise reach the guard
        # literally, and a guard that rejects it would look like a doc bug.
        for command in (
            self.writer_command(),
            fill(self.commands["read-only"], directory=REPO, roots=""),
        ):
            with self.subTest(command=command):
                self.assertIsNone(PLACEHOLDER.search(command))
                self.assertNotIn("ROOTS", command)

    def test_the_body_writer_command_is_allowed(self) -> None:
        self.assert_allowed("pstack:developer-codex", self.writer_command())

    def test_the_body_reviewer_command_is_allowed(self) -> None:
        self.assert_allowed(
            "pstack:reviewer-codex",
            fill(self.commands["read-only"], directory=REPO, roots=""),
        )

    def test_the_body_writer_command_without_roots_is_denied(self) -> None:
        # The grant is what lets a writer commit, so a body that stopped
        # printing it would silently ship writers that cannot commit.
        output = HOOK.guard(
            {
                "agent_type": "pstack:developer-codex",
                "tool_name": "Bash",
                "tool_input": {"command": self.writer_command(roots="")},
            }
        )
        self.assertIn("not in the delegate-to-codex allowlist", output)


if __name__ == "__main__":
    unittest.main()
