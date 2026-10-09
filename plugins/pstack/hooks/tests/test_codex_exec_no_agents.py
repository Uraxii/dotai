import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HOOK_PATH = Path(__file__).resolve().parents[1] / "codex_exec_no_agents.py"
SHIM_PATH = HOOK_PATH.parents[1] / "shims" / "codex"
SPEC = importlib.util.spec_from_file_location("codex_exec_no_agents", HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HOOK)

FLAG = ["-c", "agents.enabled=false"]
SH = shutil.which("sh")


def payload(command: object, tool_name: str = "Bash", **extra) -> dict:
    return {"tool_name": tool_name, "tool_input": {"command": command, **extra}}


def run_hook(event: dict) -> str:
    stdin = io.StringIO(json.dumps(event))
    stdout = io.StringIO()
    with mock.patch.object(sys, "stdin", stdin), \
        mock.patch.object(sys, "stdout", stdout):
        HOOK.main()
    return stdout.getvalue()


class FakeCodexEnv:
    """A temp dir with a fake real `codex` that appends its argv to a log."""

    def __init__(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.real_dir = self.dir / "real"
        self.real_dir.mkdir()
        self.log = self.dir / "argv.log"
        fake = self.real_dir / "codex"
        fake.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" >> "$FAKE_LOG"\necho fake-out\n'
        )
        fake.chmod(0o755)

    def env(self) -> dict:
        return {
            **os.environ,
            "FAKE_LOG": str(self.log),
            "PATH": f"{self.real_dir}:{os.environ['PATH']}",
        }

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []

    def cleanup(self) -> None:
        shutil.rmtree(self.dir)


class RewriteCommandTests(unittest.TestCase):
    def test_a_command_mentioning_codex_gets_the_shim_path_prefix(self) -> None:
        command = "codex exec 'do the thing'"
        rewritten = HOOK.rewrite_command(command)
        self.assertTrue(rewritten.endswith(f"; {command}"))
        self.assertIn(f"PATH={HOOK.SHIMS_DIR}:\"$PATH\"", rewritten)

    def test_the_command_text_is_never_edited(self) -> None:
        for command in (
            "cat > doc.md <<'EOF'\nrun codex exec go\nEOF",
            'echo "codex exec is a subcommand"',
            'out="$(codex exec go)"',
        ):
            with self.subTest(command=command):
                self.assertTrue(HOOK.rewrite_command(command).endswith(command))

    def test_a_command_without_codex_is_unchanged(self) -> None:
        self.assertEqual(HOOK.rewrite_command("git status"), "git status")

    def test_an_already_prefixed_command_is_not_prefixed_twice(self) -> None:
        once = HOOK.rewrite_command("codex exec go")
        self.assertEqual(HOOK.rewrite_command(once), once)

    def test_a_shim_dir_path_with_spaces_is_quoted(self) -> None:
        with mock.patch.object(HOOK, "SHIMS_DIR", Path("/a b/shims")):
            self.assertTrue(
                HOOK.rewrite_command("codex x").startswith(
                    "PATH='/a b/shims':\"$PATH\"; "
                )
            )


class ShimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeCodexEnv()
        self.addCleanup(self.fake.cleanup)
        env = self.fake.env()
        env["PATH"] = f"{SHIM_PATH.parent}:{env['PATH']}"
        self.env = env

    def run_shim(self, *args: str, env: dict | None = None):
        return subprocess.run(
            [SH, str(SHIM_PATH), *args],
            env=env or self.env, capture_output=True, text=True,
        )

    def test_exec_gets_the_flag_right_after_exec(self) -> None:
        self.run_shim("exec", "resume", "--last")
        self.assertEqual(
            self.fake.calls(), [" ".join(["exec", *FLAG, "resume", "--last"])]
        )

    def test_exec_with_the_flag_already_present_still_runs(self) -> None:
        self.run_shim("exec", *FLAG, "go")
        self.assertEqual(len(self.fake.calls()), 1)
        self.assertIn("agents.enabled=false", self.fake.calls()[0])

    def test_other_subcommands_pass_through_unchanged(self) -> None:
        for args in (["--version"], ["login", "status"]):
            with self.subTest(args=args):
                self.run_shim(*args)
                self.assertEqual(self.fake.calls()[-1], " ".join(args))

    def test_no_real_codex_exits_127_with_an_error(self) -> None:
        env = {**os.environ, "PATH": str(SHIM_PATH.parent)}
        result = self.run_shim("exec", "go", env=env)
        self.assertEqual(result.returncode, 127)
        self.assertIn("no codex", result.stderr)


def shells() -> list[str]:
    return [s for s in ("sh", "bash", "zsh") if shutil.which(s)]


class HookedCommandInRealShellTests(unittest.TestCase):
    """The hook-rewritten command, run by real shells with a fake codex."""

    def setUp(self) -> None:
        self.fake = FakeCodexEnv()
        self.addCleanup(self.fake.cleanup)

    def run_hooked(self, shell: str, command: str, cwd: Path | None = None):
        return subprocess.run(
            [shell, "-c", HOOK.rewrite_command(command)],
            env=self.fake.env(), capture_output=True, text=True,
            cwd=cwd or self.fake.dir,
        )

    def assert_flagged_call(self, shell: str, command: str) -> None:
        result = self.run_hooked(shell, command)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.fake.calls()
        self.assertEqual(len(calls), 1, f"{shell}: {calls}")
        self.assertEqual(calls[0].split()[:3], ["exec", *FLAG])

    def test_real_invocations_get_the_flag_in_every_shell(self) -> None:
        cases = {
            "plain call": "codex exec go",
            "command substitution in double quotes":
                'out="$(codex exec -c agents.enabled=false go)"',
            "backticks in double quotes": 'out="`codex exec go`"',
            "substitution in unquoted heredoc":
                "cat <<EOF > /dev/null\n$(codex exec go)\nEOF",
            "nested shell": 'bash -c "codex exec go"',
            "after an apostrophe comment": "# don't break\ncodex exec go",
            "after an arithmetic shift": "x=$((1<<2))\ncodex exec go",
        }
        for shell in shells():
            for name, command in cases.items():
                with self.subTest(shell=shell, case=name):
                    self.fake.log.unlink(missing_ok=True)
                    self.assert_flagged_call(shell, command)

    def test_a_heredoc_writing_a_doc_leaves_it_unchanged_and_runs_no_codex(
        self,
    ) -> None:
        body = "run any `codex exec -c agents.enabled=false` that lacks it\ncodex exec go\n"
        command = f"cat > doc.md <<'EOF'\n{body}EOF"
        for shell in shells():
            with self.subTest(shell=shell):
                result = self.run_hooked(shell, command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.fake.dir / "doc.md").read_text(), body)
                self.assertEqual(self.fake.calls(), [])


class MainHookTests(unittest.TestCase):
    def test_a_bash_codex_call_is_rewritten_via_updated_input(self) -> None:
        event = payload("codex exec 'go'", description="run codex",
                        timeout=600000)
        decision = json.loads(run_hook(event))["hookSpecificOutput"]
        self.assertEqual("PreToolUse", decision["hookEventName"])
        self.assertNotIn("permissionDecision", decision)
        self.assertEqual(
            HOOK.rewrite_command("codex exec 'go'"),
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
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO("not json")), \
            mock.patch.object(sys, "stdout", stdout):
            HOOK.main()
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
