import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


PLUGIN = Path(__file__).resolve().parents[1]


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = self.root / "plugin"
        shutil.copytree(PLUGIN, self.plugin)
        self.builder = self.plugin / "scripts/prepare_codex_run.py"
        self.repo = self.root / "repo"
        self.tree = self.root / "tree with spaces"
        self.git("init", "-q", "-b", "develop", str(self.repo))
        self.git("-C", str(self.repo), "-c", "user.name=Test", "-c",
                 "user.email=test@example.invalid", "commit", "-q",
                 "--allow-empty", "-m", "chore(test): create fixture")
        self.git("-C", str(self.repo), "config", "extensions.worktreeConfig", "true")
        self.git("-C", str(self.repo), "worktree", "add", "-q", "-b",
                 "feature", str(self.tree))
        self.sha = self.git("-C", str(self.tree), "rev-parse", "HEAD").stdout.strip()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.stub("codex", """#!/usr/bin/env python3
import json, os, pathlib, sys, time
while os.environ.get('STUB_RELEASE_FILE') and not pathlib.Path(os.environ['STUB_RELEASE_FILE']).exists():
    time.sleep(0.02)
time.sleep(float(os.environ.get('STUB_DELAY', '0')))
pathlib.Path(os.environ['ARGV_LOG']).write_text(json.dumps({
    'argv': sys.argv[1:], 'actor': os.environ['BD_ACTOR'],
    'beads': os.environ['BEADS_DIR'], 'input': sys.stdin.read()}))
if sys.argv[1] == 'review':
    print(os.environ.get('REVIEW_OUTPUT', 'No findings.\\nPSTACK_REVIEW_COMPLETE'))
sys.exit(int(os.environ.get('STUB_CODE', '0')))
""")
        self.stub("bd", """#!/usr/bin/env python3
import os, pathlib, sys
if os.environ.get('CONTEXT_FAIL') and sys.argv[1] == 'show':
    sys.exit(1)
if sys.argv[1] == 'comment':
    pathlib.Path(os.environ['COMMENT_LOG']).write_text(
        pathlib.Path(sys.argv[sys.argv.index('--file') + 1]).read_text())
else:
    print('scope and notes')
""")
        self.env = dict(os.environ, XDG_STATE_HOME=str(self.root / "state"),
                        BEADS_DIR=str(self.root / "store/.beads"),
                        PATH=f"{self.bin}:{os.environ['PATH']}",
                        ARGV_LOG=str(self.root / "argv.json"),
                        COMMENT_LOG=str(self.root / "comment.txt"))

    def git(self, *args):
        return subprocess.run(["git", *args], check=True, text=True,
                              capture_output=True)

    def stub(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def request(self, role="writer", tree=None):
        tree = tree or self.tree
        if role == "writer":
            return f"Claim bead fixture-one as developer-fixture-one. Work in {tree}. Stop at stage=built."
        return f"Review bead fixture-one at {self.sha} in {tree}."

    def prepare(self, request=None, launch=False):
        return subprocess.run(["python3", str(self.builder), *(["--launch"] if launch else [])],
                              input=request or self.request(), env=self.env,
                              text=True, capture_output=True)

    def execute(self, role="writer"):
        result = self.prepare(self.request(role))
        self.assertEqual(result.returncode, 0, result.stderr)
        run = Path(result.stdout.strip())
        result = subprocess.run(["bash", str(run / "run.sh")], env=self.env,
                                capture_output=True, text=True)
        marker = json.loads((run / "codex.jsonl").read_text().splitlines()[-1])
        self.assertEqual(marker, {"pstack": "codex exited", "code": result.returncode})
        return result, run

    def test_writer_config_grants_model_and_scope(self):
        config = (self.repo / ".git/config").read_bytes()
        git_dir = Path(self.git("-C", str(self.tree), "rev-parse", "--absolute-git-dir").stdout.strip())
        (git_dir / "config.worktree").write_text("[core]\n\tbare = false\n")
        models = json.loads((self.plugin / "models.json").read_text())
        models["roles"][0]["models"]["codex"] = ["fixture-model"]
        (self.plugin / "models.json").write_text(json.dumps(models))
        result, run = self.execute()
        self.assertEqual(result.returncode, 0)
        recorded = json.loads((self.root / "argv.json").read_text())
        argv = recorded["argv"]
        self.assertEqual(argv[argv.index("-m") + 1], "fixture-model")
        self.assertIn("agents.enabled=false", argv)
        self.assertIn(str(git_dir), argv)
        for leaf in ("objects", "refs", "logs"):
            self.assertIn(str(self.repo / ".git" / leaf), argv)
        self.assertIn(str(self.root / "store"), argv)
        self.assertNotIn(str(self.repo / ".git"), argv)
        self.assertEqual(recorded["actor"], "developer-fixture-one")
        prompt = (run / "prompt.md").read_text()
        self.assertIn("Do not push", prompt)
        self.assertIn("forbids commits", prompt)
        self.assertNotIn("skills/write-tests/SKILL.md", prompt)
        self.assertEqual((self.repo / ".git/config").read_bytes(), config)

    def test_refusal_launches_nothing(self):
        for request in (self.request(tree=self.repo),
                        self.request() + f" Grant: {self.repo / '.git'}",
                        "invalid request"):
            with self.subTest(request=request):
                result = self.prepare(request, launch=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout.strip(), "PSTACK_CODEX_STOP")
                self.assertTrue(result.stderr)
                self.assertFalse((self.root / "argv.json").exists())

    def test_missing_review_skill_refuses_without_launch(self):
        skill = self.plugin / "skills/principle-skeptical-review/SKILL.md"
        skill.unlink()
        result = self.prepare(self.request("reviewer"), launch=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout.strip(), "PSTACK_CODEX_STOP")
        self.assertIn("principle-skeptical-review", result.stderr)
        self.assertFalse((self.root / "argv.json").exists())
        self.assertEqual(self.prepare().returncode, 0)

    def test_nonzero_exit_reaches_caller(self):
        self.env["STUB_CODE"] = "7"
        result, _ = self.execute()
        self.assertEqual(result.returncode, 7)

    def test_review_verdicts_and_failures(self):
        for output, expected in (("No findings.\nPSTACK_REVIEW_COMPLETE", "verdict pass"),
                                 ("- [P1] Bug\n  Must-fix. Broken.\nPSTACK_REVIEW_COMPLETE", "verdict fail"),
                                 ("- [P1] Bug\nNo tier.\nPSTACK_REVIEW_COMPLETE", "codex could not finish"),
                                 ("unexpected output", "codex could not finish"),
                                 ("", "codex could not finish")):
            with self.subTest(output=output):
                self.env["REVIEW_OUTPUT"] = output
                result, _ = self.execute("reviewer")
                self.assertIn(expected, (self.root / "comment.txt").read_text())
                argv = json.loads((self.root / "argv.json").read_text())["argv"]
                self.assertEqual(argv[0], "review")
                self.assertIn("sandbox_mode=read-only", argv)
                self.assertNotIn("--add-dir", argv)
                self.assertEqual(result.returncode, int(expected == "codex could not finish"))
        self.env["CONTEXT_FAIL"] = "1"
        (self.root / "argv.json").unlink()
        result, _ = self.execute("reviewer")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.root / "argv.json").exists())
        self.assertIn("codex could not finish", (self.root / "comment.txt").read_text())

    def test_launch_survives_and_live_duplicate_keeps_output(self):
        release = self.root / "release"
        self.env["STUB_RELEASE_FILE"] = str(release)
        self.addCleanup(release.touch)
        result = self.prepare(launch=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        run = Path(result.stdout.strip())
        prompt = (run / "prompt.md").read_bytes()
        duplicate = self.prepare(launch=True)
        self.assertEqual(duplicate.returncode, 2, duplicate.stderr)
        self.assertEqual((run / "prompt.md").read_bytes(), prompt)
        self.assertFalse((run / "refused.txt").exists())
        release.touch()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if '"codex exited"' in (run / "codex.jsonl").read_text():
                break
            time.sleep(0.05)
        self.assertIn('"codex exited"', (run / "codex.jsonl").read_text())
        (run / "refused.txt").write_text("stale refusal")
        self.assertEqual(self.prepare().returncode, 0)
        self.assertFalse((run / "refused.txt").exists())

    def test_missing_model_and_bad_option_emit_stop(self):
        models = json.loads((self.plugin / "models.json").read_text())
        models["roles"][0]["models"]["codex"] = []
        (self.plugin / "models.json").write_text(json.dumps(models))
        result = self.prepare(launch=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), "PSTACK_CODEX_STOP")
        self.assertFalse((self.root / "argv.json").exists())
        result = subprocess.run(["python3", str(self.builder), "--invalid"],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), "PSTACK_CODEX_STOP")

    def test_effective_hooks_and_bead_store_overlaps_are_refused(self):
        self.git("-C", str(self.repo), "config", "core.hooksPath", "../tree with spaces/task-hooks")
        self.assertEqual(self.prepare().stdout.strip(), "PSTACK_CODEX_STOP")
        self.git("-C", str(self.repo), "config", "--unset", "core.hooksPath")
        self.env["BEADS_DIR"] = str(self.repo / ".git/.beads")
        self.assertEqual(self.prepare().stdout.strip(), "PSTACK_CODEX_STOP")

    def test_worktree_config_absent_and_false_are_supported(self):
        for value in ("false", None):
            if value:
                self.git("-C", str(self.repo), "config", "extensions.worktreeConfig", value)
            else:
                self.git("-C", str(self.repo), "config", "--unset", "extensions.worktreeConfig")
            result = self.prepare()
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_review_cli_failure_wrong_head_and_main_checkout(self):
        self.env["STUB_CODE"] = "9"
        result, _ = self.execute("reviewer")
        self.assertEqual(result.returncode, 9)
        self.assertIn("codex could not finish", (self.root / "comment.txt").read_text())
        self.env["STUB_CODE"] = "0"
        self.assertEqual(self.prepare(self.request("reviewer", self.repo)).returncode, 0)
        self.sha = "0000000"
        (self.root / "argv.json").unlink()
        result, _ = self.execute("reviewer")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.root / "argv.json").exists())



if __name__ == "__main__":
    unittest.main()
