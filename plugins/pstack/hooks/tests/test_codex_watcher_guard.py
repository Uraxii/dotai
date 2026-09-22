import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

# Checked for a route to the regex parse tree that is not private or
# deprecated: `sre_parse` is a deprecated shim (DeprecationWarning on
# 3.11+) that forwards to this module; the public `re` API (`re.compile`,
# `Pattern`/`Match`) exposes no node-level structure at all. `re._parser`
# is that shim's target: private (leading underscore) but not deprecated,
# and the only stdlib module that still returns this tree without a
# warning. There is no supported alternative, so use it directly.
import re._parser as regex_parser


HOOK_PATH = Path(__file__).resolve().parents[1] / "codex_watcher_guard.py"
REPOSITORY_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("codex_watcher_guard", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)


WATCHERS = ("pstack:developer-codex", "reviewer-codex")
REPO = "/repo"
OTHER_REPO = "/other-repo"
RUN = f"{REPO}/.nikki-agents/codex-runs/sample-run"
WORKTREE = f"{REPO}/.nikki-agents/worktrees/sample-run"


def writable_roots(repo: str = REPO, name: str = "sample-run") -> str:
    """The writer's `-c` flag granting the four git paths a commit writes."""
    return (
        "-c 'sandbox_workspace_write.writable_roots="
        f'["{repo}/.git/objects","{repo}/.git/refs","{repo}/.git/logs",'
        f'"{repo}/.git/worktrees/{name}"]\''
    )


ROOTS = writable_roots()


def writer_exec(
    directory: str,
    *,
    codex: str = "codex-agent",
    roots: str = ROOTS,
    run: str = RUN,
) -> str:
    """The developer watcher's `codex-agent exec` step, run from `directory`."""
    flag = f" {roots}" if roots else ""
    return (
        f"{codex} exec -m gpt-5.6-terra -s workspace-write "
        f"-c agents.enabled=false{flag} -C {directory} "
        f"-o {run}/report.md - < {run}/prompt.txt"
    )


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
            "codex-agent --version",
            "codex-agent login status",
            f"git -C {REPO} rev-parse HEAD",
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed("reviewer-codex", command)

    def test_developer_playbook_commands_are_allowed(self) -> None:
        commands = (
            "codex-agent --version",
            "codex-agent login status",
            f"git -C {WORKTREE} rev-parse HEAD",
            f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run develop",
            writer_exec(WORKTREE),
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_allowed("pstack:developer-codex", command)

    def test_developer_c_may_be_any_worktree_under_the_repo(self) -> None:
        # A writer given an existing worktree path outside .nikki-agents,
        # e.g. one Claude itself placed under .claude/worktrees/<x>.
        command = writer_exec(f"{REPO}/.claude/worktrees/sample-run")
        self.assert_allowed("pstack:developer-codex", command)

    def test_bare_codex_command_is_allowed_for_both_watchers(self) -> None:
        # `codex-agent` is a machine-local wrapper that isolates CODEX_HOME;
        # it exists on no machine by default. The watcher body falls back to
        # the bare `codex` binary when the wrapper is missing, so both
        # command words must reach the same allowlisted commands.
        reviewer_exec = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        developer_exec = writer_exec(WORKTREE, codex="codex")
        for agent_type in WATCHERS:
            with self.subTest(agent_type=agent_type):
                self.assert_allowed(agent_type, "codex --version")
                self.assert_allowed(agent_type, "codex login status")
        self.assert_allowed("reviewer-codex", reviewer_exec)
        self.assert_allowed("pstack:developer-codex", developer_exec)

    def test_bare_codex_exec_still_enforces_repo_containment(self) -> None:
        # The `codex` word must be subject to the same repo/name coupling as
        # `codex-agent`, not a looser check that happens to share a prefix.
        other_run = f"{OTHER_REPO}/.nikki-agents/codex-runs/sample-run"
        command = (
            f"codex exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {other_run}/report.md - < {other_run}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_existing_worktree_must_sit_inside_the_repo(self) -> None:
        # `worktree: <existing absolute path>` in the CODEX RUN header. `-C`
        # is the directory a workspace-write Codex session may write to, so
        # the guard keeps it inside the repo that receives the report. A
        # sibling worktree beside the repo looks legitimate and is still
        # outside that boundary.
        self.assert_allowed("pstack:developer-codex", writer_exec(f"{REPO}/wt/sample-run"))
        self.assert_denied(
            payload(
                "pstack:developer-codex",
                "Bash",
                command=writer_exec(f"{REPO}-worktrees/sample-run"),
            ),
            "Bash",
        )

    def test_dot_segment_worktree_is_denied(self) -> None:
        # `<repo>/.` names the repo root itself, so "repo plus at least one
        # segment" does not by itself keep a workspace-write sandbox out of
        # the main checkout. A `.` segment is rejected wherever a `..`
        # segment is, and a real worktree name still passes.
        self.assert_allowed("pstack:developer-codex", writer_exec(f"{REPO}/wt/sample-run"))
        for directory in (f"{REPO}/.", f"{REPO}/./.", f"{REPO}/wt/."):
            with self.subTest(directory=directory):
                self.assert_denied(
                    payload(
                        "pstack:developer-codex", "Bash", command=writer_exec(directory)
                    ),
                    "Bash",
                )

    def test_playbook_prompt_write_is_allowed_for_both_watchers(self) -> None:
        for agent_type in WATCHERS:
            with self.subTest(agent_type=agent_type):
                event = payload(agent_type, "Write", file_path=f"{RUN}/prompt.txt")
                self.assertEqual("", HOOK.guard(event))

    # -- per-kind sandbox binding ----------------------------------------

    def test_reviewer_workspace_write_is_denied(self) -> None:
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s workspace-write -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_reviewer_worktree_add_is_denied(self) -> None:
        command = f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run develop"
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    # -- worktree add's trailing base commit-ish ---------------------------

    def test_worktree_add_without_a_base_is_denied(self) -> None:
        # The pre-fix form: no start point, so `git worktree add` branches
        # from the watcher's own checkout instead of the requested base.
        command = f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run"
        self.assert_denied(
            payload("pstack:developer-codex", "Bash", command=command), "Bash"
        )

    def test_worktree_add_base_may_be_a_branch_sha_or_namespaced_branch(self) -> None:
        for base in ("develop", "agent/pr2-split", "1a2b3c4"):
            with self.subTest(base=base):
                command = f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run {base}"
                self.assert_allowed("pstack:developer-codex", command)

    def test_worktree_add_base_starting_with_a_dash_is_denied(self) -> None:
        # A base of `--foo` would be read as a git option, not a commit-ish,
        # at the end of the command line.
        command = f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run --foo"
        self.assert_denied(
            payload("pstack:developer-codex", "Bash", command=command), "Bash"
        )

    def test_worktree_add_base_with_a_space_is_denied(self) -> None:
        command = f"git -C {REPO} worktree add {WORKTREE} -b agent/sample-run bad base"
        self.assert_denied(
            payload("pstack:developer-codex", "Bash", command=command), "Bash"
        )

    # -- repo/name coupling between -C, -o, and stdin ---------------------

    def test_o_repo_differs_from_c_repo_is_denied_for_reviewer(self) -> None:
        other_run = f"{OTHER_REPO}/.nikki-agents/codex-runs/sample-run"
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {other_run}/report.md - < {other_run}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_o_repo_differs_from_c_repo_is_denied_for_developer(self) -> None:
        other_run = f"{OTHER_REPO}/.nikki-agents/codex-runs/sample-run"
        command = writer_exec(WORKTREE, run=other_run)
        self.assert_denied(
            payload("pstack:developer-codex", "Bash", command=command), "Bash"
        )

    def test_real_bad_reviewer_command_from_the_field_is_denied(self) -> None:
        # A real reviewer run wrote prompt.txt and passed -o under
        # .../add-version-flag/ while -C (the repo) was a different repo
        # entirely. The old guard let this through because each path slot
        # matched any absolute path on its own.
        repo = "/repo/.nikki-agents/pantry-shelf/galley-b61cb9/repo"
        run = "/repo/.nikki-agents/codex-runs/add-version-flag"
        command = (
            "codex-agent exec -m gpt-5.6-sol -s read-only -c agents.enabled=false "
            f"-C {repo} -o {run}/report.md - < {run}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_o_and_stdin_name_mismatch_is_denied(self) -> None:
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {REPO}/.nikki-agents/codex-runs/"
            f"other-run/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_o_and_stdin_repo_mismatch_is_denied(self) -> None:
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {RUN}/report.md - < {OTHER_REPO}/.nikki-agents/"
            f"codex-runs/sample-run/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_developer_c_equal_to_bare_repo_is_denied(self) -> None:
        self.assert_denied(
            payload("pstack:developer-codex", "Bash", command=writer_exec(REPO)),
            "Bash",
        )

    def test_developer_c_under_unrelated_path_is_denied(self) -> None:
        self.assert_denied(
            payload("pstack:developer-codex", "Bash", command=writer_exec("/root/.ssh")),
            "Bash",
        )

    # -- the writer's writable-roots flag ---------------------------------

    def test_writer_command_with_the_four_roots_is_allowed(self) -> None:
        self.assert_allowed("pstack:developer-codex", writer_exec(WORKTREE))

    def test_writer_command_without_the_roots_flag_is_denied(self) -> None:
        # Without the flag Codex's workspace-write sandbox denies every write
        # under .git, so the writer cannot commit. The flag is required, not
        # optional, so the guard rejects the pre-fix command shape.
        self.assert_denied(
            payload(
                "pstack:developer-codex", "Bash", command=writer_exec(WORKTREE, roots="")
            ),
            "Bash",
        )

    def test_writer_roots_under_a_different_repo_are_denied(self) -> None:
        # A root the guard does not pin to this run's repo would hand a
        # write-enabled Codex session another tree's git directory.
        for roots in (
            writable_roots(repo=OTHER_REPO),
            ROOTS.replace(f"{REPO}/.git/refs", f"{OTHER_REPO}/.git/refs"),
            ROOTS.replace(f"{REPO}/.git/logs", f"{OTHER_REPO}/.git/logs"),
            ROOTS.replace(
                f"{REPO}/.git/worktrees", f"{OTHER_REPO}/.git/worktrees"
            ),
        ):
            with self.subTest(roots=roots):
                self.assert_denied(
                    payload(
                        "pstack:developer-codex",
                        "Bash",
                        command=writer_exec(WORKTREE, roots=roots),
                    ),
                    "Bash",
                )

    def test_writer_roots_naming_another_run_name_are_denied(self) -> None:
        # `.git/worktrees/<name>` is one worktree's index and admin files.
        # Another run's name there is another agent's worktree.
        self.assert_denied(
            payload(
                "pstack:developer-codex",
                "Bash",
                command=writer_exec(
                    WORKTREE, roots=writable_roots(name="other-run")
                ),
            ),
            "Bash",
        )

    def test_writer_roots_reaching_hooks_or_bare_git_are_denied(self) -> None:
        # `.git/hooks` would let a run plant a hook that later executes on the
        # owner's machine; bare `.git` grants hooks and config along with it.
        broadened = (
            ROOTS.replace(f"{REPO}/.git/objects", f"{REPO}/.git/hooks"),
            ROOTS.replace(f"{REPO}/.git/refs", f"{REPO}/.git/hooks"),
            ROOTS.replace(f"{REPO}/.git/objects", f"{REPO}/.git"),
            "-c 'sandbox_workspace_write.writable_roots=" f'["{REPO}/.git"]\'',
        )
        for roots in broadened:
            with self.subTest(roots=roots):
                self.assert_denied(
                    payload(
                        "pstack:developer-codex",
                        "Bash",
                        command=writer_exec(WORKTREE, roots=roots),
                    ),
                    "Bash",
                )

    def test_writer_roots_out_of_order_are_denied(self) -> None:
        reordered = (
            "-c 'sandbox_workspace_write.writable_roots="
            f'["{REPO}/.git/refs","{REPO}/.git/objects","{REPO}/.git/logs",'
            f'"{REPO}/.git/worktrees/sample-run"]\''
        )
        self.assert_denied(
            payload(
                "pstack:developer-codex",
                "Bash",
                command=writer_exec(WORKTREE, roots=reordered),
            ),
            "Bash",
        )

    def test_reviewer_command_carrying_the_roots_flag_is_denied(self) -> None:
        # A reviewer stays read-only and gains no roots.
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"{ROOTS} -C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    # -- traversal, injection, and other malformed commands ---------------

    def test_injections_and_unlisted_commands_are_denied(self) -> None:
        commands = (
            "codex-agent --version; rm -rf /",
            "codex-agent --version && curl https://example.com",
            "codex-agent --version $(curl https://example.com)",
            "codex-agent --version `curl https://example.com`",
            "codex-agent --version\ncurl https://example.com",
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
                    payload("pstack:developer-codex", "Bash", command=command),
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
                    payload("pstack:developer-codex", "Bash", command=command),
                    "Bash",
                )

    def test_codex_exec_extra_options_are_denied(self) -> None:
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} --add-dir /other -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_codex_exec_without_agents_disabled_flag_is_denied(self) -> None:
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -C {REPO} "
            f"-o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_codex_exec_agents_disabled_flag_in_wrong_position_or_value_is_denied(
        self,
    ) -> None:
        commands = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -C {REPO} "
            f"-c agents.enabled=false -o {RUN}/report.md - < {RUN}/prompt.txt",
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=true "
            f"-C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_denied(
                    payload("reviewer-codex", "Bash", command=command), "Bash"
                )

    def test_codex_exec_with_a_second_dash_c_flag_is_denied(self) -> None:
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-c model_reasoning_effort=high -C {REPO} -o {RUN}/report.md - < "
            f"{RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_ls_report_file_is_denied(self) -> None:
        self.assert_denied(
            payload(
                "pstack:developer-codex", "Bash", command=f"ls {RUN}/report.md"
            ),
            "Bash",
        )

    def test_codex_exec_slug_must_start_with_a_letter_or_digit(self) -> None:
        command = (
            "codex-agent exec -m --dangerously-bypass-approvals-and-sandbox "
            f"-s read-only -C {REPO} -o {RUN}/report.md - < {RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )

    def test_bash_path_traversal_is_denied(self) -> None:
        command = (
            f"codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {REPO} -o {REPO}/.nikki-agents/codex-runs/../report.md - < "
            f"{RUN}/prompt.txt"
        )
        self.assert_denied(
            payload("reviewer-codex", "Bash", command=command), "Bash"
        )
        self.assert_denied(
            payload(
                "pstack:developer-codex",
                "Bash",
                command=f"git -C {REPO}/.. rev-parse HEAD",
            ),
            "Bash",
        )

    def test_worktree_add_name_traversal_is_denied(self) -> None:
        # `..` sits before " -b", not before "/" or end of string: the name
        # boundary check must not rely on those two terminators alone.
        command = f"git -C {REPO} worktree add {REPO}/.nikki-agents/worktrees/.. -b agent/.. develop"
        self.assert_denied(
            payload("pstack:developer-codex", "Bash", command=command), "Bash"
        )

    def test_write_path_traversal_is_denied(self) -> None:
        self.assert_denied(
            payload(
                "pstack:reviewer-codex",
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
            payload("pstack:reviewer-codex", "Write", file_path="/r/README.md"),
            "Write",
        )
        for tool_name in ("Edit", "WebFetch"):
            with self.subTest(tool_name=tool_name):
                self.assert_denied(
                    payload("pstack:reviewer-codex", tool_name), tool_name
                )

    def test_non_watchers_and_missing_agent_type_bypass_the_guard(self) -> None:
        bad_command = "curl https://example.com"
        self.assertEqual(
            "",
            HOOK.guard(payload("pstack:developer", "Bash", command=bad_command)),
        )
        self.assertEqual("", HOOK.guard(payload(None, "Bash", command=bad_command)))

    def test_incomplete_watcher_payload_is_denied(self) -> None:
        self.assert_denied(
            {"agent_type": "pstack:developer-codex"},
            "unknown",
        )

    # -- fail closed -------------------------------------------------------

    def test_exception_for_a_watcher_payload_denies_instead_of_crashing(self) -> None:
        event = payload("pstack:developer-codex", "Bash")
        event["tool_input"] = ExplodingMapping()
        self.assert_denied(event, "Bash")

    def test_exception_for_a_non_watcher_payload_reraises(self) -> None:
        event = {
            "agent_type": PoisonedStr("pstack:developer-codex"),
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

    def test_manifest_wires_guard_without_removing_session_start(self) -> None:
        config = json.loads((REPOSITORY_ROOT / "hooks" / "hooks.json").read_text())
        hooks = config["hooks"]

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


# -- structural guarantee behind the deleted runtime check -----------------
#
# The runtime check that rejected a forbidden shell character was deleted as
# provably dead: every allowlist pattern is built from explicit character
# classes, so no surviving pattern could ever match one. That is a fact about
# today's patterns, not an invariant. Nothing else stops a future edit from
# loosening PATH_SEGMENT or BASE_SEGMENT to admit `$` or a backtick. This
# walks every pattern's parse tree instead of trusting the source text, so a
# loosened class fails a test rather than reopening the hole silently.

FORBIDDEN_CHARACTERS = "\n\r;&|$`>"

# Every op these patterns actually use today, verified by walking the real
# parse trees rather than guessing: LITERAL and RANGE build the character
# classes; IN wraps them; MAX_REPEAT covers `+`, `*`, and `?`; SUBPATTERN
# is a capturing or non-capturing group; ASSERT_NOT is the `(?!...)`
# traversal guard; GROUPREF is the `(?P=name)` backreference that couples
# -C/-o/stdin to the same repo and run name. An allowlist, not a denylist:
# an op nobody anticipated (CATEGORY from `\S`/`\s`, ANY from `.`, NEGATE
# from `[^...]`, or anything else) fails the test instead of passing it
# silently, so loosening a class to use one requires touching this list.
ALLOWED_PARSE_TREE_OPS = frozenset(
    {
        regex_parser.LITERAL,
        regex_parser.RANGE,
        regex_parser.IN,
        regex_parser.MAX_REPEAT,
        regex_parser.SUBPATTERN,
        regex_parser.ASSERT_NOT,
        regex_parser.GROUPREF,
    }
)


def _iter_nodes(parsed):
    """Yield every node reachable from `parsed`, including composite ones.

    Descends into branches, repeats, subpatterns, lookaheads, and character
    classes: every construct in these patterns that can hold a nested node
    or a character acceptor. A composite node is yielded itself and then
    recursed into, so both the container and its contents are checked.
    """
    for op, argument in parsed:
        yield op, argument
        if op is regex_parser.BRANCH:
            for branch in argument[1]:
                yield from _iter_nodes(branch)
        elif op in (regex_parser.MAX_REPEAT, regex_parser.MIN_REPEAT):
            yield from _iter_nodes(argument[2])
        elif op is regex_parser.SUBPATTERN:
            yield from _iter_nodes(argument[3])
        elif op in (regex_parser.ASSERT, regex_parser.ASSERT_NOT):
            yield from _iter_nodes(argument[1])
        elif op is regex_parser.IN:
            yield from argument


class AllowlistCharacterClassTests(unittest.TestCase):
    def all_patterns(self):
        patterns = []
        for bucket in HOOK.ALLOWED_BASH_BY_KIND.values():
            patterns.extend(bucket)
        patterns.append(HOOK.ALLOWED_WRITE)
        return patterns

    def test_no_allowlist_pattern_can_match_a_forbidden_character(self) -> None:
        for pattern in self.all_patterns():
            parsed = regex_parser.parse(pattern.pattern)
            for op, argument in _iter_nodes(parsed):
                with self.subTest(pattern=pattern.pattern, op=op):
                    self.assertIn(
                        op,
                        ALLOWED_PARSE_TREE_OPS,
                        f"unexpected parse-tree op {op} in {pattern.pattern!r}; "
                        "extend ALLOWED_PARSE_TREE_OPS deliberately if this "
                        "op is legitimate, after checking what characters it "
                        "can admit",
                    )
                    if op is regex_parser.LITERAL:
                        self.assertNotIn(chr(argument), FORBIDDEN_CHARACTERS)
                    elif op is regex_parser.RANGE:
                        low, high = argument
                        for character in FORBIDDEN_CHARACTERS:
                            self.assertFalse(
                                low <= ord(character) <= high,
                                f"range {low}-{high} admits {character!r}",
                            )


if __name__ == "__main__":
    unittest.main()
