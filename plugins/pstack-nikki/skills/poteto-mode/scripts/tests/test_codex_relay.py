import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "codex_relay.py"

_spec = importlib.util.spec_from_file_location("codex_relay", SCRIPT)
codex_relay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codex_relay)


MODELS_JSON = {
    "available": {"codex": [{"label": "GPT-5.5", "slug": "gpt-5.5"}]},
    "roles": [
        {
            "role": "feature, refactoring",
            "models": {"codex": ["gpt-5.5", "gpt-5.4"]},
        },
        {
            "role": "judgment and prose",
            "models": {"codex": ["gpt-5.5", "gpt-5.4"]},
        },
        {"role": "read-only role", "models": {"claude": ["opus"]}},
    ],
}


class PickModelTests(unittest.TestCase):
    def test_returns_first_codex_slug_for_the_role(self) -> None:
        path = self._write_models_json()

        model = codex_relay.pick_model(path, "feature, refactoring")

        self.assertEqual("gpt-5.5", model)

    def test_raises_when_role_missing(self) -> None:
        path = self._write_models_json()

        with self.assertRaises(codex_relay.RelayError):
            codex_relay.pick_model(path, "no such role")

    def test_raises_when_role_has_no_codex_models(self) -> None:
        path = self._write_models_json()

        with self.assertRaises(codex_relay.RelayError):
            codex_relay.pick_model(path, "read-only role")

    def _write_models_json(self) -> Path:
        import tempfile

        tmp = Path(tempfile.mkdtemp()) / "models.json"
        tmp.write_text(json.dumps(MODELS_JSON))
        return tmp


class BuildPromptTests(unittest.TestCase):
    def test_points_at_the_skill_path_not_the_skill_name(self) -> None:
        prompt = codex_relay.build_prompt("GOAL: do the thing.", Path("/x/SKILL.md"))

        self.assertIn("/x/SKILL.md", prompt)
        self.assertIn("GOAL: do the thing.", prompt)
        self.assertTrue(prompt.rstrip().endswith("GOAL: do the thing."))


class BuildCommandTests(unittest.TestCase):
    def test_assembles_model_sandbox_cwd_and_output_flags(self) -> None:
        cmd = codex_relay.build_command(
            codex_bin="codex",
            model="gpt-5.5",
            sandbox="workspace-write",
            cwd=Path("/repo"),
            prompt="do it",
            output_file=Path("/tmp/out.txt"),
            add_dirs=[],
            skip_git_repo_check=False,
            reasoning_effort=None,
        )

        self.assertEqual(
            [
                "codex",
                "exec",
                "-m",
                "gpt-5.5",
                "-s",
                "workspace-write",
                "-C",
                "/repo",
                "-o",
                "/tmp/out.txt",
                "do it",
            ],
            cmd,
        )

    def test_adds_optional_flags_only_when_given(self) -> None:
        cmd = codex_relay.build_command(
            codex_bin="codex",
            model="gpt-5.5",
            sandbox="read-only",
            cwd=Path("/repo"),
            prompt="do it",
            output_file=Path("/tmp/out.txt"),
            add_dirs=["/repo/.git/worktrees/x"],
            skip_git_repo_check=True,
            reasoning_effort="high",
        )

        self.assertIn("--add-dir", cmd)
        self.assertIn("/repo/.git/worktrees/x", cmd)
        self.assertIn("--skip-git-repo-check", cmd)
        self.assertIn("model_reasoning_effort=high", cmd)


def _fake_run(returncode: int, stderr: str = ""):
    def run(cmd, **kwargs):
        output_index = cmd.index("-o") + 1
        Path(cmd[output_index]).write_text("poteto-agent report: done\n")
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr=stderr)

    return run


class RunRelayTests(unittest.TestCase):
    def _args(self, tmp_path: Path, brief_path: Path, **overrides):
        argv = [
            "--agent",
            "developer-codex",
            "--brief-file",
            str(brief_path),
            "--cwd",
            str(tmp_path),
            "--models-json",
            str(self._models_json(tmp_path)),
            "--skill-path",
            "/plugins/pstack-nikki/skills/poteto-mode/SKILL.md",
        ]
        args = codex_relay.parse_args(argv)
        for key, value in overrides.items():
            setattr(args, key, value)
        return args

    def _models_json(self, tmp_path: Path) -> Path:
        path = tmp_path / "models.json"
        path.write_text(json.dumps(MODELS_JSON))
        return path

    def _brief(self, tmp_path: Path) -> Path:
        path = tmp_path / "brief.txt"
        path.write_text("GOAL: add hello.txt and commit it.")
        return path

    def test_prints_codex_final_message_on_success(self) -> None:
        import io
        import tempfile
        import contextlib

        tmp_path = Path(tempfile.mkdtemp())
        args = self._args(tmp_path, self._brief(tmp_path))

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = codex_relay.run_relay(args, run=_fake_run(0))

        self.assertEqual(0, code)
        self.assertIn("poteto-agent report: done", buffer.getvalue())

    def test_developer_codex_picks_the_feature_role_and_workspace_write(self) -> None:
        import tempfile

        tmp_path = Path(tempfile.mkdtemp())
        args = self._args(tmp_path, self._brief(tmp_path))
        seen = {}

        def spy_run(cmd, **kwargs):
            seen["cmd"] = cmd
            output_index = cmd.index("-o") + 1
            Path(cmd[output_index]).write_text("ok\n")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        codex_relay.run_relay(args, run=spy_run)

        self.assertIn("gpt-5.5", seen["cmd"])
        self.assertIn("workspace-write", seen["cmd"])

    def test_nonzero_exit_on_codex_failure(self) -> None:
        import io
        import tempfile
        import contextlib

        tmp_path = Path(tempfile.mkdtemp())
        args = self._args(tmp_path, self._brief(tmp_path))

        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            code = codex_relay.run_relay(
                args, run=_fake_run(17, stderr="boom: sandbox denied write\n")
            )

        self.assertEqual(17, code)
        self.assertIn("boom: sandbox denied write", stderr_buffer.getvalue())

    def test_reviewer_codex_defaults_to_read_only(self) -> None:
        import tempfile

        tmp_path = Path(tempfile.mkdtemp())
        argv = [
            "--agent",
            "reviewer-codex",
            "--brief-file",
            str(self._brief(tmp_path)),
            "--cwd",
            str(tmp_path),
            "--models-json",
            str(self._models_json(tmp_path)),
            "--skill-path",
            "/x/SKILL.md",
        ]
        args = codex_relay.parse_args(argv)
        seen = {}

        def spy_run(cmd, **kwargs):
            seen["cmd"] = cmd
            output_index = cmd.index("-o") + 1
            Path(cmd[output_index]).write_text("ok\n")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        codex_relay.run_relay(args, run=spy_run)

        self.assertIn("read-only", seen["cmd"])


class MainTests(unittest.TestCase):
    def test_relay_error_exits_nonzero_with_message(self) -> None:
        import io
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = codex_relay.main(
                [
                    "--role",
                    "no such role",
                    "--sandbox",
                    "read-only",
                    "--brief-file",
                    "-",
                    "--cwd",
                    "/tmp",
                ],
                run=_fake_run(0),
            )

        self.assertEqual(1, code)
        self.assertIn("no such role", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
