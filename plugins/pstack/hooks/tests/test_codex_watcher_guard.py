import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


HOOK_PATH = Path(__file__).resolve().parents[1] / "codex_watcher_guard.py"
REPOSITORY_ROOT = HOOK_PATH.parents[1]
SPEC = importlib.util.spec_from_file_location("codex_watcher_guard", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# dataclasses look their module up in sys.modules while building the class.
sys.modules[SPEC.name] = HOOK
SPEC.loader.exec_module(HOOK)


DEVELOPER = "pstack:developer-codex"
REVIEWER = "reviewer-codex"
WATCHERS = (DEVELOPER, REVIEWER)
MAIN_CHECKOUT = "/repo"
ROOT = f"{MAIN_CHECKOUT}/.agent-runs"
RUN = f"{ROOT}/sample-run-0a1b2c3d"
EARLIER_RUN = f"{ROOT}/earlier-run-9f8e7d6c"
WORKTREE = f"{RUN}/worktree"
OUTSIDE = "outside the runs root"
# The command shapes watchers ran before run directories existed.
LEGACY_RUN = f"{MAIN_CHECKOUT}/codex-runs/sample-run"
LEGACY_WORKTREE = f"{MAIN_CHECKOUT}/worktrees/sample-run"


def reviewer_exec(**overrides: str) -> str:
    flags = {
        "-m": "gpt-5.6-terra",
        "-s": "read-only",
        "-c": "agents.enabled=false",
        "-C": MAIN_CHECKOUT,
        "-o": f"{RUN}/report.md",
    }
    return exec_command(flags, overrides)


def writer_exec(**overrides: str) -> str:
    flags = {
        "-m": "gpt-5.6-terra",
        "-s": "workspace-write",
        "-c": "agents.enabled=false",
        "-C": WORKTREE,
        "--add-dir": RUN,
        "-o": f"{RUN}/report.md",
    }
    return exec_command(flags, overrides)


def exec_command(flags: dict[str, str], overrides: dict[str, str]) -> str:
    """A `codex-agent exec` command; an override of None drops that flag.

    Override keys use underscores for dashes: `add_dir` is `--add-dir`,
    `stdin` is the `<` file, `codex` is the command word.
    """
    options = dict(flags)
    stdin = overrides.pop("stdin", f"{RUN}/brief.md")
    codex = overrides.pop("codex", "codex-agent")
    for key, value in overrides.items():
        flag = "--add-dir" if key == "add_dir" else f"-{key}"
        options[flag] = value
    words = [codex, "exec"]
    for flag, value in options.items():
        if value is not None:
            words += [flag, value]
    words.append("-")
    command = " ".join(words)
    return command if stdin is None else f"{command} < {stdin}"


def payload(
    agent_type: str | None, tool_name: str, cwd: str | None = None, **tool_input: object
) -> dict:
    event = {"tool_name": tool_name, "tool_input": tool_input}
    if agent_type is not None:
        event["agent_type"] = agent_type
    if cwd is not None:
        event["cwd"] = cwd
    return event


class ExplodingMapping(dict):
    """A tool_input whose .get() blows up, to exercise guard()'s own fail-closed path."""

    def get(self, key, default=None):
        raise RuntimeError("tool_input exploded")


class PoisonedStr(str):
    """An agent_type that raises when guard() tries to read its watcher name."""

    def rpartition(self, sep):
        raise RuntimeError("agent_type exploded")


class GuardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("AGENT_RUNS_DIR", None)

    def assert_allowed(
        self, agent_type: str, command: str, cwd: str | None = None
    ) -> None:
        self.assertEqual(
            "", HOOK.guard(payload(agent_type, "Bash", cwd=cwd, command=command))
        )

    def assert_denied(self, event: dict, reason: str) -> None:
        decision = json.loads(HOOK.guard(event))["hookSpecificOutput"]
        self.assertEqual("PreToolUse", decision["hookEventName"])
        self.assertEqual("deny", decision["permissionDecision"])
        self.assertTrue(
            decision["permissionDecisionReason"].startswith("codex watcher guard: "),
            decision["permissionDecisionReason"],
        )
        self.assertIn(reason, decision["permissionDecisionReason"])

    def assert_bash_denied(
        self, agent_type: str, command: str, reason: str, cwd: str | None = None
    ) -> None:
        self.assert_denied(
            payload(agent_type, "Bash", cwd=cwd, command=command), reason
        )

    def assert_all_denied(
        self, agent_type: str, cases: dict[str, str], cwd: str | None = None
    ) -> None:
        """`cases` maps each command to the reason fragment its denial must name."""
        for command, reason in cases.items():
            with self.subTest(command=command):
                self.assert_bash_denied(agent_type, command, reason, cwd=cwd)


class CodexExecTests(GuardTestCase):
    def test_canonical_exec_commands_are_allowed(self) -> None:
        self.assert_allowed(REVIEWER, reviewer_exec())
        self.assert_allowed(DEVELOPER, writer_exec())

    def test_version_and_login_status_are_allowed_for_both_watchers(self) -> None:
        for agent_type in WATCHERS:
            for command in (
                "codex --version",
                "codex-agent --version",
                "codex -V",
                "codex login status",
                "codex-agent login status",
            ):
                with self.subTest(agent_type=agent_type, command=command):
                    self.assert_allowed(agent_type, command)

    def test_exec_variants_that_keep_the_invariants_are_allowed(self) -> None:
        variants = (
            writer_exec(codex="codex"),
            writer_exec(m=None),
            writer_exec(c=None),
            (
                f"codex-agent exec --add-dir {RUN} -o {RUN}/report.md -C {WORKTREE} "
                f"-s workspace-write - < {RUN}/brief.md"
            ),
            (
                f"codex exec --sandbox=workspace-write --cd={WORKTREE} "
                f"--add-dir={RUN} --output-last-message={RUN}/report.md "
                f"--model gpt-5.6-terra - < {RUN}/brief.md"
            ),
            (
                f"codex exec --sandbox workspace-write --cd {WORKTREE} "
                "--skip-git-repo-check --json --ephemeral --color never "
                f"--config agents.enabled=false - < {RUN}/brief.md"
            ),
            (
                f"codex exec -s workspace-write -C {WORKTREE} --add-dir {RUN} "
                f"--add-dir {EARLIER_RUN} 'Read the brief and follow it.'"
            ),
            (
                f"codex exec -s workspace-write -C {EARLIER_RUN}/worktree "
                f"--add-dir {RUN} - < {RUN}/brief.md"
            ),
            f"codex exec -s workspace-write -C {RUN} - < {RUN}/brief.md",
        )
        for command in variants:
            with self.subTest(command=command):
                self.assert_allowed(DEVELOPER, command)

    def test_reviewer_c_may_be_anywhere_and_add_dir_inside_is_allowed(self) -> None:
        for directory in (MAIN_CHECKOUT, WORKTREE, "/elsewhere/checkout"):
            with self.subTest(directory=directory):
                self.assert_allowed(REVIEWER, reviewer_exec(C=directory))
        self.assert_allowed(REVIEWER, reviewer_exec(C=None))
        self.assert_allowed(REVIEWER, reviewer_exec(add_dir=RUN))
        self.assert_allowed(REVIEWER, f"codex exec --sandbox=read-only {RUN}/brief.md")

    def test_sandbox_must_match_the_watcher_kind(self) -> None:
        self.assert_all_denied(
            REVIEWER,
            {
                reviewer_exec(
                    s="workspace-write"
                ): "reviewer codex exec needs -s read-only",
                reviewer_exec(s="danger-full-access"): "needs -s read-only",
                reviewer_exec(s=None): "needs -s read-only",
                writer_exec(): "needs -s read-only",
                reviewer_exec().replace(
                    " exec ", " exec -s read-only "
                ): "needs -s read-only",
            },
        )
        self.assert_all_denied(
            DEVELOPER,
            {
                writer_exec(
                    s="read-only"
                ): "developer codex exec needs -s workspace-write",
                writer_exec(s="danger-full-access"): "needs -s workspace-write",
                writer_exec(s=None): "needs -s workspace-write",
            },
        )

    def test_flags_that_escape_the_sandbox_or_approvals_are_denied(self) -> None:
        for flag in (
            "--full-auto",
            "--dangerously-bypass-approvals-and-sandbox",
            "--dangerously-bypass-hook-trust",
            "--oss",
            "--worktree",
            "--approve-for-me",
            "--ignore-rules",
            "-p",
            "--profile",
            "--enable",
            "--disable",
            "--",
            "-s=read-only",
        ):
            with self.subTest(flag=flag):
                self.assert_bash_denied(
                    DEVELOPER,
                    writer_exec().replace(" exec ", f" exec {flag} "),
                    f"codex exec flag {flag} is not allowed",
                )

    def test_profile_with_a_value_names_the_profile_flag(self) -> None:
        self.assert_bash_denied(
            REVIEWER,
            reviewer_exec().replace(" exec ", " exec -p safe "),
            "flag -p is not allowed",
        )

    def test_config_other_than_agents_enabled_is_denied(self) -> None:
        for setting in (
            "sandbox_mode=danger-full-access",
            "approval_policy=never",
            "sandbox_workspace_write.network_access=true",
        ):
            with self.subTest(setting=setting):
                self.assert_bash_denied(
                    DEVELOPER,
                    writer_exec().replace(" exec ", f" exec -c {setting} "),
                    "only -c agents.enabled",
                )

    def test_exec_subcommands_and_extra_prompts_are_denied(self) -> None:
        self.assert_all_denied(
            DEVELOPER,
            {
                "codex exec resume -s workspace-write -C "
                f"{WORKTREE}": "codex exec resume is not allowed",
                f"codex exec -s workspace-write -C {WORKTREE} review": "codex exec review",
                f"codex exec -s workspace-write -C {WORKTREE} fork": "codex exec fork",
                f"codex exec -s workspace-write -C {WORKTREE} one two": "at most one prompt",
            },
        )

    def test_value_flags_need_a_value_that_is_not_a_flag(self) -> None:
        self.assert_all_denied(
            DEVELOPER,
            {
                f"codex exec -s workspace-write -C {WORKTREE} -m": "-m needs a value",
                f"codex exec -s workspace-write -C {WORKTREE} -m "
                "--dangerously-bypass-approvals-and-sandbox": "does not start with -",
                f"codex exec -s workspace-write --cd= -C {WORKTREE}": "--cd needs a value",
            },
        )

    def test_developer_c_must_be_strictly_inside_the_runs_root(self) -> None:
        self.assert_all_denied(
            DEVELOPER,
            {
                writer_exec(C=MAIN_CHECKOUT): f"developer -C /repo is {OUTSIDE}",
                writer_exec(C="/root/.ssh"): OUTSIDE,
                writer_exec(
                    C=ROOT
                ): "developer -C /repo/.agent-runs is the runs root itself",
                writer_exec(C=f"{ROOT}/"): "is the runs root itself",
                writer_exec(C=None): "developer codex exec needs -C",
                writer_exec().replace(
                    " exec ", f" exec -C {WORKTREE} "
                ): "gives -C more than once",
            },
        )

    def test_write_targets_must_be_strictly_inside_the_runs_root(self) -> None:
        self.assert_all_denied(
            DEVELOPER,
            {
                writer_exec(add_dir=MAIN_CHECKOUT): f"--add-dir /repo is {OUTSIDE}",
                writer_exec(
                    add_dir=ROOT
                ): "--add-dir /repo/.agent-runs is the runs root itself",
                writer_exec(o="/tmp/report.md"): f"-o /tmp/report.md is {OUTSIDE}",
                writer_exec(
                    stdin="/etc/passwd"
                ): f"stdin file /etc/passwd is {OUTSIDE}",
                writer_exec(
                    stdin=ROOT
                ): "stdin file /repo/.agent-runs is the runs root itself",
            },
        )
        self.assert_all_denied(
            REVIEWER,
            {
                reviewer_exec(add_dir="/repo/src"): f"--add-dir /repo/src is {OUTSIDE}",
                reviewer_exec(
                    o=f"{MAIN_CHECKOUT}/report.md"
                ): f"-o /repo/report.md is {OUTSIDE}",
                reviewer_exec(
                    stdin=f"{MAIN_CHECKOUT}/brief.md"
                ): f"stdin file /repo/brief.md is {OUTSIDE}",
            },
        )

    def test_dot_dot_cannot_escape_the_runs_root(self) -> None:
        self.assert_all_denied(
            DEVELOPER,
            {
                writer_exec(C=f"{ROOT}/../src"): f"developer -C /repo/src is {OUTSIDE}",
                writer_exec(add_dir=f"{RUN}/../.."): f"--add-dir /repo is {OUTSIDE}",
                writer_exec(o=f"{RUN}/../../../etc/x"): f"-o /etc/x is {OUTSIDE}",
                writer_exec(
                    stdin=f"{ROOT}/../brief.md"
                ): f"stdin file /repo/brief.md is {OUTSIDE}",
                writer_exec(C=f"{RUN}/.."): "is the runs root itself",
            },
        )

    def test_dotted_names_that_are_not_dot_segments_are_allowed(self) -> None:
        root = f"{MAIN_CHECKOUT}/.hidden/...three/a.b/.agent-runs"
        run = f"{root}/sample-run-0a1b2c3d"
        self.assert_allowed(
            DEVELOPER,
            writer_exec(
                C=f"{run}/worktree",
                add_dir=run,
                o=f"{run}/report.md",
                stdin=f"{run}/brief.md",
            ),
        )

    def test_relative_paths_resolve_against_the_payload_cwd(self) -> None:
        relative = "codex exec -s workspace-write -C worktree --add-dir . -o report.md - < brief.md"
        self.assert_allowed(DEVELOPER, relative, cwd=RUN)
        self.assert_bash_denied(
            DEVELOPER,
            relative,
            f"stdin file /repo/brief.md is {OUTSIDE}",
            cwd=MAIN_CHECKOUT,
        )
        self.assert_allowed(REVIEWER, "cat brief.md progress.md", cwd=RUN)
        self.assert_bash_denied(
            REVIEWER, "cat ../../README.md", f"/repo/README.md is {OUTSIDE}", cwd=RUN
        )

    def test_relative_write_target_must_hold_from_both_cwd_and_c(self) -> None:
        # From the cwd, ../../x stays in the runs root; from -C it does not.
        command = f"codex exec -s workspace-write -C {RUN} --add-dir ../../x - < {RUN}/brief.md"
        self.assert_allowed(
            DEVELOPER, command.replace("../../x", "../x"), cwd=f"{RUN}/worktree/sub"
        )
        self.assert_bash_denied(
            DEVELOPER,
            command,
            f"--add-dir /repo/x is {OUTSIDE}",
            cwd=f"{RUN}/worktree/sub",
        )


class RunsRootTests(GuardTestCase):
    def test_agent_runs_dir_is_the_only_root_when_set(self) -> None:
        run = "/srv/runs/sample-run-0a1b2c3d"
        command = writer_exec(
            C=f"{run}/worktree",
            add_dir=run,
            o=f"{run}/report.md",
            stdin=f"{run}/brief.md",
        )
        for configured in ("/srv/runs", "/srv/runs/", "/srv//runs"):
            with self.subTest(configured=configured):
                os.environ["AGENT_RUNS_DIR"] = configured
                self.assert_allowed(DEVELOPER, command)
                self.assert_allowed(REVIEWER, f"ls {run} /srv/runs")
                self.assert_bash_denied(
                    DEVELOPER, writer_exec(), f"stdin file {RUN}/brief.md is {OUTSIDE}"
                )
                self.assert_bash_denied(
                    DEVELOPER,
                    writer_exec(stdin=None),
                    f"developer -C {WORKTREE} is {OUTSIDE}",
                )
                self.assert_bash_denied(
                    DEVELOPER,
                    command.replace(f"-C {run}/worktree", "-C /srv/runs"),
                    "is the runs root itself",
                )
                self.assert_bash_denied(REVIEWER, "cat /srv/runs2/x", OUTSIDE)

    def test_relative_agent_runs_dir_joins_the_payload_cwd(self) -> None:
        os.environ["AGENT_RUNS_DIR"] = "runs"
        self.assert_allowed(REVIEWER, "cat /srv/runs/x/brief.md", cwd="/srv")
        self.assert_bash_denied(
            REVIEWER, "cat /srv/runs/x/brief.md", OUTSIDE, cwd="/elsewhere"
        )

    def test_empty_agent_runs_dir_falls_back_to_the_agent_runs_segment(self) -> None:
        os.environ["AGENT_RUNS_DIR"] = ""
        self.assert_allowed(DEVELOPER, writer_exec())
        self.assert_bash_denied(REVIEWER, "cat /repo/runs/x/brief.md", OUTSIDE)

    def test_a_segment_must_be_exactly_agent_runs(self) -> None:
        for directory in (
            "/repo/agent-runs/x",
            "/repo/.agent-runs-old/x",
            "/repo/x.agent-runs/y",
        ):
            with self.subTest(directory=directory):
                self.assert_bash_denied(REVIEWER, f"cat {directory}/brief.md", OUTSIDE)
        self.assert_allowed(REVIEWER, "cat /any/where/.agent-runs/x/brief.md")


class ReadCommandTests(GuardTestCase):
    def test_orientation_reads_inside_the_runs_root_are_allowed(self) -> None:
        commands = (
            f"cat {RUN}/brief.md",
            f"cat -n {RUN}/brief.md {RUN}/progress.md",
            f"head -n 20 {RUN}/brief.md",
            f"head -c 100 {RUN}/report.md",
            f"ls {ROOT}",
            f"ls -la {RUN} {RUN}/corrections",
            f"test -d {WORKTREE}",
            f"test -s {RUN}/report.md",
            f"sed -n '1,/^---$/p' {RUN}/brief.md",
            f"sed -n 1,20p {RUN}/brief.md",
            f"sed -n '$p' {RUN}/progress.md",
            f"sed -n '/^## Task/,$p' {RUN}/brief.md",
            f'cat "{RUN}/brief.md"',
        )
        for agent_type in WATCHERS:
            for command in commands:
                with self.subTest(agent_type=agent_type, command=command):
                    self.assert_allowed(agent_type, command)

    def test_reads_outside_the_runs_root_are_denied(self) -> None:
        self.assert_all_denied(
            REVIEWER,
            {
                "cat /etc/passwd": f"cat path /etc/passwd is {OUTSIDE}",
                f"cat {RUN}/brief.md /repo/README.md": f"/repo/README.md is {OUTSIDE}",
                "head -n 5 /repo/README.md": f"head path /repo/README.md is {OUTSIDE}",
                "ls /repo": f"ls path /repo is {OUTSIDE}",
                "ls -la": "ls needs at least one path",
                "cat -- -n": f"cat path /-n is {OUTSIDE}",
                "test -d /repo": f"test path /repo is {OUTSIDE}",
                f"test {RUN}": "test takes one unary operator and one path",
                f"test -d {RUN} {RUN}": "test takes one unary operator",
                "sed -n 1p /etc/passwd": f"sed path /etc/passwd is {OUTSIDE}",
            },
            cwd="/",
        )

    def test_sed_scripts_other_than_a_print_are_denied(self) -> None:
        reason = "sed allows only -n with one print script"
        self.assert_all_denied(
            REVIEWER,
            {
                f"sed -n '1e id' {RUN}/brief.md": reason,
                f"sed -n '1w /tmp/x' {RUN}/brief.md": reason,
                f"sed -n '1r /etc/passwd' {RUN}/brief.md": reason,
                f"sed -n '1,$p;w /tmp/x' {RUN}/brief.md": reason,
                f"sed -n 1p {RUN}/brief.md -i": "sed option -i is not allowed",
                f"sed -i -n 1p {RUN}/brief.md": reason,
                f"sed -n -e 1p {RUN}/brief.md": reason,
                f"sed 1p {RUN}/brief.md": reason,
                "sed -n '1,/^---$/p'": reason,
            },
        )


class GitTests(GuardTestCase):
    def test_read_only_git_inside_the_runs_root_is_denied(self) -> None:
        for agent_type in WATCHERS:
            for sub in (
                "status",
                "status --short",
                "log --oneline -5",
                "diff --stat",
                "diff --stat 1234567..HEAD",
                "rev-parse HEAD",
                "show --stat HEAD",
                "worktree list",
            ):
                with self.subTest(agent_type=agent_type, sub=sub):
                    self.assert_bash_denied(
                        agent_type,
                        f"git -C {WORKTREE} {sub}",
                        "git is not an allowed command",
                    )

    def test_git_in_a_repo_planted_under_the_runs_root_is_denied(self) -> None:
        # A workspace-write run can plant a repo whose config names
        # core.fsmonitor, diff.external, or a textconv driver; any git call
        # the watcher makes there would run that program unsandboxed.
        for agent_type in WATCHERS:
            with self.subTest(agent_type=agent_type):
                self.assert_bash_denied(
                    agent_type, f"git -C {RUN}/x status", "git is not an allowed command"
                )

    def test_git_mutations_and_global_options_are_denied(self) -> None:
        self.assert_all_denied(
            DEVELOPER,
            {
                f"git -C {WORKTREE} {sub}": "git is not an allowed command"
                for sub in (
                    "commit -am x",
                    "reset --hard",
                    "push",
                    "worktree add /tmp/x",
                    "config a b",
                    "-c core.pager=id log",
                    "diff --ext-diff",
                )
            }
            | {"git status": "git is not an allowed command"},
        )


class ShellSafetyTests(GuardTestCase):
    def test_shell_metacharacters_outside_quotes_are_denied(self) -> None:
        brief = f"{RUN}/brief.md"
        self.assert_all_denied(
            DEVELOPER,
            {
                f"cat {brief}; rm -rf /": "`;` outside quotes",
                f"cat {brief} && curl example.com": "`&` outside quotes",
                f"cat {brief} | sh": "`|` outside quotes",
                f"cat {brief} > /tmp/x": "`>` outside quotes",
                f"cat {brief} >> {RUN}/progress.md": "`>` outside quotes",
                f"cat $(echo {brief})": "`$` outside quotes",
                f"cat `echo {brief}`": "outside quotes",
                f"cat {RUN}/*.md": "`*` outside quotes",
                f"cat {RUN}/brief.m?": "`?` outside quotes",
                f"cat {RUN}/[b]rief.md": "`[` outside quotes",
                f"cat {RUN}/{{brief,report}}.md": "`{` outside quotes",
                "cat ~/.ssh/id_rsa": "`~` outside quotes",
                writer_exec(add_dir="~/x"): "`~` outside quotes",
                f"cat {brief} !": "`!` outside quotes",
                f"cat {RUN}/brief\\.md": "`\\` outside quotes",
                f"cat {brief}\nrm -rf /": "control characters",
                f"cat {brief}\rrm": "control characters",
                f"cat {brief} # comment": "`#` comment",
                'cat "$HOME/x"': "`$` inside double quotes",
                'cat "`id`"': "inside double quotes",
                f"cat '{brief}": "does not parse",
                "cat << EOF": "only one `<`",
                f"cat 0< {brief}": "`<` must follow a space",
                f"cat < {brief} {brief}": "exactly one file at the end",
                "cat <": "exactly one file at the end",
                "": "the command is empty",
            },
        )

    def test_metacharacters_inside_single_quotes_stay_literal(self) -> None:
        self.assert_allowed(
            DEVELOPER,
            f"codex exec -s workspace-write -C {WORKTREE} 'Fix it; then run $TESTS | tee *'",
        )

    def test_unknown_commands_and_prefixes_are_denied(self) -> None:
        self.assert_all_denied(
            REVIEWER,
            {
                "curl https://example.com": "curl is not an allowed command",
                "rm -rf build": "rm is not an allowed command",
                f"/bin/cat {RUN}/brief.md": "/bin/cat is not an allowed command",
                "AGENT_RUNS_DIR=/ codex --version": "is not an allowed command",
                f"cd {RUN}": "cd is not an allowed command",
                "echo x": "echo is not an allowed command",
                "codex": "codex allows only exec, --version, and login status",
                "codex login": "codex login allows only status",
                "codex --version extra": "takes no arguments",
                "codex review": "codex allows only exec",
            },
        )


class LegacyShapeTests(GuardTestCase):
    def test_legacy_codex_runs_exec_shapes_are_denied(self) -> None:
        reviewer = (
            "codex-agent exec -m gpt-5.6-terra -s read-only -c agents.enabled=false "
            f"-C {MAIN_CHECKOUT} -o {LEGACY_RUN}/report.md - < {LEGACY_RUN}/prompt.txt"
        )
        writer = (
            "codex-agent exec -m gpt-5.6-terra -s workspace-write "
            f"-c agents.enabled=false -C {LEGACY_WORKTREE} "
            f"-o {LEGACY_RUN}/report.md - < {LEGACY_RUN}/prompt.txt"
        )
        self.assert_bash_denied(
            REVIEWER, reviewer, f"stdin file {LEGACY_RUN}/prompt.txt is {OUTSIDE}"
        )
        self.assert_bash_denied(
            DEVELOPER, writer, f"stdin file {LEGACY_RUN}/prompt.txt is {OUTSIDE}"
        )

    def test_legacy_git_commands_are_denied_for_both_watchers(self) -> None:
        for agent_type in WATCHERS:
            self.assert_all_denied(
                agent_type,
                {
                    f"git -C {MAIN_CHECKOUT} rev-parse HEAD": "git is not an allowed command",
                    f"git -C {MAIN_CHECKOUT} worktree add {LEGACY_WORKTREE} "
                    "-b agent/sample-run develop": "git is not an allowed command",
                    f"git -C {WORKTREE} worktree add {RUN}/wt "
                    "-b agent/sample-run develop": "git is not an allowed command",
                },
            )


class ToolShapeTests(GuardTestCase):
    def test_background_bash_is_denied_even_when_the_command_is_allowed(self) -> None:
        for agent_type, command in (
            (REVIEWER, reviewer_exec()),
            (DEVELOPER, writer_exec()),
        ):
            with self.subTest(agent_type=agent_type):
                self.assert_allowed(agent_type, command)
                event = payload(agent_type, "Bash", command=command)
                event["tool_input"]["run_in_background"] = True
                self.assert_denied(event, "Bash must not run in the background")

    def test_every_write_by_a_watcher_is_denied(self) -> None:
        for agent_type in (*WATCHERS, "pstack:reviewer-codex", "developer-codex"):
            for file_path in (
                f"{RUN}/progress.md",
                f"{RUN}/report.md",
                f"{WORKTREE}/x.py",
                f"{LEGACY_RUN}/prompt.txt",
            ):
                with self.subTest(agent_type=agent_type, file_path=file_path):
                    self.assert_denied(
                        payload(agent_type, "Write", file_path=file_path, content="x"),
                        "Write is not allowed for a Codex watcher",
                    )

    def test_other_tools_are_denied(self) -> None:
        for tool_name in ("Edit", "Read", "WebFetch"):
            with self.subTest(tool_name=tool_name):
                self.assert_denied(
                    payload(REVIEWER, tool_name, file_path=f"{RUN}/brief.md"),
                    f"{tool_name} is not allowed for a Codex watcher",
                )

    def test_non_watchers_and_missing_agent_type_bypass_the_guard(self) -> None:
        for agent_type in ("pstack:developer", "codex", None):
            with self.subTest(agent_type=agent_type):
                self.assertEqual(
                    "",
                    HOOK.guard(payload(agent_type, "Bash", command="curl example.com")),
                )
                self.assertEqual(
                    "", HOOK.guard(payload(agent_type, "Write", file_path="/r/x.md"))
                )

    def test_incomplete_watcher_payload_is_denied(self) -> None:
        self.assert_denied({"agent_type": DEVELOPER}, "no tool name or input")

    def test_non_string_command_is_denied(self) -> None:
        self.assert_bash_denied(DEVELOPER, ["codex", "--version"], "not a string")

    def test_exception_for_a_watcher_payload_denies_instead_of_crashing(self) -> None:
        event = payload(DEVELOPER, "Bash")
        event["tool_input"] = ExplodingMapping()
        self.assert_denied(event, "could not be checked")

    def test_exception_for_a_non_watcher_payload_reraises(self) -> None:
        event = {
            "agent_type": PoisonedStr(DEVELOPER),
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
        # Write stays in the matcher so a watcher's Write reaches the guard
        # and is denied instead of skipping it.
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


if __name__ == "__main__":
    unittest.main()
