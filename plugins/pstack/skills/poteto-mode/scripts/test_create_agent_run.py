"""Tests for creating per-task agent run directories.

Everything here drives the real script against a real temp repository, the
same shape as `test_worktree_audit.py`: a throwaway `git init` stands in for
the main checkout, and no test touches the user's own repo, home directory,
or transcripts. A fixed git identity is set through environment variables so
the suite passes on a machine with no configured `user.name`/`user.email`.
The exact-bytes test builds its expected `brief.md` independently from the
contract text rather than importing the script's own renderer, so a
regression in that renderer has something real to fail against.
"""

from __future__ import annotations

import io
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import create_agent_run

SCRIPT = Path(__file__).resolve().parent / "create_agent_run.py"
POTETO_MODE_SKILL = SCRIPT.parent.parent / "SKILL.md"
LOG_DECISION_SCRIPT = (
    SCRIPT.parent.parent.parent
    / "show-me-your-work/scripts/log_decision.py")
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*-[0-9a-f]{8}$")
GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "agent-runs-tests",
    "GIT_AUTHOR_EMAIL": "agent-runs-tests@example.invalid",
    "GIT_COMMITTER_NAME": "agent-runs-tests",
    "GIT_COMMITTER_EMAIL": "agent-runs-tests@example.invalid",
}


def git(repo: Path, *arguments: str) -> str:
    """Run git in `repo` under a fixed test identity; return its stdout."""
    done = subprocess.run(["git", "-C", str(repo), *arguments],
                          capture_output=True, text=True, check=True,
                          env=dict(os.environ, **GIT_IDENTITY))
    return done.stdout.strip()


def build_repository(root: Path) -> Path:
    """A one-commit repo at `root/repo`, standing in for the main checkout."""
    repo = root / "repo"
    subprocess.run(["git", "init", "--quiet", "-b", "main", str(repo)],
                   check=True)
    (repo / "file.txt").write_text("one\n")
    git(repo, "add", "file.txt")
    git(repo, "commit", "--quiet", "-m", "one")
    return repo


def run_script(arguments: list[str], *, cwd: Path, stdin: str,
              agent_runs_dir: str | None = None
              ) -> subprocess.CompletedProcess[str]:
    """Invoke the script the way a spawner would and capture the result."""
    environment = dict(os.environ, **GIT_IDENTITY)
    environment.pop("AGENT_RUNS_DIR", None)
    if agent_runs_dir is not None:
        environment["AGENT_RUNS_DIR"] = agent_runs_dir
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments], cwd=str(cwd), input=stdin,
        capture_output=True, text=True, check=False, env=environment)


def expected_brief(*, kind: str, worktree: Path, branch: str, base: str,
                   model: str | None, run_id: str, run_dir: Path,
                   task: str) -> str:
    """The contract's `brief.md` text, built independently of the script."""
    lines = [
        "---",
        f"kind: {kind}",
        f"worktree: {worktree}",
        f"branch: {branch}",
        f"base: {base}",
    ]
    if model is not None:
        lines.append(f"model: {model}")
    lines.append("---")
    lines += [
        "",
        f"# Agent run {run_id}",
        "",
        "This brief is read-only. Later instructions arrive as files in "
        "`corrections/`.",
        "",
        "1. If you have not loaded the poteto-mode skill yet, read the "
        "Non-negotiables and Principles sections of "
        f"`{POTETO_MODE_SKILL}`, then only the skills and playbook steps "
        "this brief names. Search with `rg -n` and read narrow line "
        "ranges, not whole files.",
        f"2. Read every file in `{run_dir}/corrections/` in name order. A "
        "correction overrides this brief and every correction before it.",
        f"3. Read `{run_dir}/progress.md` if it exists. Earlier agents on "
        "this run logged their finished steps there. Continue from it and "
        "do not redo those steps.",
        f"4. Work only in `{worktree}`.",
        "5. After each step, append one line to "
        f"`{run_dir}/progress.md` that says what you finished.",
    ]
    decisions_step = (
        f"Log each decision in `{run_dir}/decisions.tsv` in the "
        "show-me-your-work format with "
        f"`{LOG_DECISION_SCRIPT}`. That means one tab-separated row per "
        "decision with the columns `ts phase decision why evidence "
        "result`, append-only. Log forks you chose, units finished with "
        "their check result, pivots and reverts, and blockers. Skip "
        "trivial actions.")
    report_step = f"End with your report. Write it to `{run_dir}/agent-report.md`."
    if kind == "writer":
        lines += [
            "6. Commit your work yourself with git.",
            f"7. {decisions_step}",
            f"8. {report_step}",
        ]
    else:
        lines += [
            f"6. {decisions_step}",
            f"7. {report_step}",
        ]
    lines += [
        "",
        "## Task",
        "",
        task,
        "",
    ]
    return "\n".join(lines)


class DefaultRunsRootTest(unittest.TestCase):
    """The runs root a linked worktree resolves to with no override."""

    def test_default_root_is_under_the_main_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            repo = build_repository(root)
            git(repo, "worktree", "add", "--quiet", "-b", "feature",
               str(root / "linked"), "main")
            done = run_script(
                ["--slug", "linked-check", "--kind", "reviewer",
                 "--worktree", "."],
                cwd=root / "linked", stdin="Check the default root.\n")
            self.assertEqual(done.returncode, 0, done.stderr)
            run_dir = Path(done.stdout.strip())
            self.assertEqual(run_dir.parent, repo / ".agent-runs")


class RunsRootOverrideTest(unittest.TestCase):
    """`AGENT_RUNS_DIR` overriding the default root."""

    def test_agent_runs_dir_relocates_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            repo = build_repository(root)
            override = root / "elsewhere"
            done = run_script(
                ["--slug", "override-check", "--kind", "reviewer",
                 "--worktree", str(repo)],
                cwd=repo, stdin="Check the override.\n",
                agent_runs_dir=str(override))
            self.assertEqual(done.returncode, 0, done.stderr)
            run_dir = Path(done.stdout.strip())
            self.assertEqual(run_dir.parent, override)
            self.assertNotEqual(run_dir.parent, repo / ".agent-runs")


class GitignoreTest(unittest.TestCase):
    """The blanket `.gitignore` the runs root gets on first use."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = build_repository(self.root)
        self.runs_root = self.root / "runs"

    def create_a_run(self) -> None:
        done = run_script(
            ["--slug", "gitignore-check", "--kind", "reviewer",
             "--worktree", str(self.repo)],
            cwd=self.repo, stdin="Check gitignore.\n",
            agent_runs_dir=str(self.runs_root))
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_missing_gitignore_is_written_as_a_blanket_ignore(self) -> None:
        self.create_a_run()
        self.assertEqual((self.runs_root / ".gitignore").read_text(), "*\n")

    def test_an_existing_gitignore_is_left_alone(self) -> None:
        self.runs_root.mkdir(parents=True)
        (self.runs_root / ".gitignore").write_text("custom\n")
        self.create_a_run()
        self.assertEqual((self.runs_root / ".gitignore").read_text(),
                         "custom\n")


class BaseFlagTest(unittest.TestCase):
    """A fresh writer worktree created from `--base`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        cls.repo = build_repository(root)
        cls.base_sha = git(cls.repo, "rev-parse", "HEAD")
        cls.runs_root = root / "runs"
        cls.result = run_script(
            ["--slug", "base-check", "--kind", "writer", "--base", "main"],
            cwd=cls.repo, stdin="Build the feature.\n",
            agent_runs_dir=str(cls.runs_root))
        cls.run_dir = (Path(cls.result.stdout.strip())
                       if cls.result.returncode == 0 else None)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_the_run_succeeds(self) -> None:
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_stdout_is_the_run_directory_alone(self) -> None:
        self.assertEqual(self.result.stdout, f"{self.run_dir}\n")

    def test_the_run_id_matches_the_contract_pattern(self) -> None:
        self.assertRegex(self.run_dir.name, RUN_ID_PATTERN)

    def test_corrections_directory_exists(self) -> None:
        self.assertTrue((self.run_dir / "corrections").is_dir())

    def test_brief_is_read_only(self) -> None:
        mode = stat.S_IMODE((self.run_dir / "brief.md").stat().st_mode)
        self.assertEqual(mode, 0o444)

    def test_the_worktree_is_created_under_run(self) -> None:
        self.assertTrue((self.run_dir / "worktree").is_dir())

    def test_the_worktree_branch_is_agent_slash_run_id(self) -> None:
        branch = git(self.run_dir / "worktree", "branch", "--show-current")
        self.assertEqual(branch, f"agent/{self.run_dir.name}")

    def test_the_worktree_head_is_the_base_sha(self) -> None:
        head = git(self.run_dir / "worktree", "rev-parse", "HEAD")
        self.assertEqual(head, self.base_sha)


class WorktreeReuseTest(unittest.TestCase):
    """Reusing an existing worktree records its real branch and HEAD."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        cls.repo = build_repository(root)
        cls.linked = root / "linked"
        git(cls.repo, "worktree", "add", "--quiet", "-b", "in-review",
           str(cls.linked), "main")
        (cls.linked / "extra.txt").write_text("more\n")
        git(cls.linked, "add", "extra.txt")
        git(cls.linked, "commit", "--quiet", "-m", "extra")
        cls.head = git(cls.linked, "rev-parse", "HEAD")
        cls.result = run_script(
            ["--slug", "reuse-check", "--kind", "reviewer",
             "--worktree", str(cls.linked)],
            cwd=cls.repo, stdin="Review the branch.\n",
            agent_runs_dir=str(root / "runs"))
        cls.run_dir = (Path(cls.result.stdout.strip())
                       if cls.result.returncode == 0 else None)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def brief_field(self, name: str) -> str:
        """The value on the `name:` line of the frontmatter."""
        text = (self.run_dir / "brief.md").read_text()
        match = re.search(rf"^{name}: (.*)$", text, re.MULTILINE)
        self.assertIsNotNone(match, f"no {name}: line in brief.md")
        return match.group(1)

    def test_the_run_succeeds(self) -> None:
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_the_worktree_field_is_the_reused_path(self) -> None:
        self.assertEqual(self.brief_field("worktree"), str(self.linked))

    def test_the_branch_field_is_the_checked_out_branch(self) -> None:
        self.assertEqual(self.brief_field("branch"), "in-review")

    def test_the_base_field_is_the_worktree_head(self) -> None:
        self.assertEqual(self.brief_field("base"), self.head)

    def test_no_new_worktree_directory_is_created_under_run(self) -> None:
        self.assertFalse((self.run_dir / "worktree").exists())


class RelativeWorktreeTest(unittest.TestCase):
    """A relative `--worktree` is recorded as a normalized absolute path."""

    def test_dot_dot_is_resolved_in_the_worktree_field(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            repo = build_repository(root)
            linked = root / "linked"
            git(repo, "worktree", "add", "--quiet", "-b", "relative",
               str(linked), "main")
            done = run_script(
                ["--slug", "relative-check", "--kind", "reviewer",
                 "--worktree", "../linked"],
                cwd=repo, stdin="Review the branch.\n",
                agent_runs_dir=str(root / "runs"))
            self.assertEqual(done.returncode, 0, done.stderr)
            text = (Path(done.stdout.strip()) / "brief.md").read_text()
            self.assertIn(f"\nworktree: {linked.resolve()}\n", text)


class DetachedWorktreeReuseTest(unittest.TestCase):
    """A reused worktree with no checked-out branch reads as detached."""

    def test_a_detached_head_reads_as_detached(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            repo = build_repository(root)
            head = git(repo, "rev-parse", "HEAD")
            detached = root / "detached"
            git(repo, "worktree", "add", "--quiet", "--detach",
               str(detached), head)
            done = run_script(
                ["--slug", "detached-check", "--kind", "reviewer",
                 "--worktree", str(detached)],
                cwd=repo, stdin="Review at a fixed commit.\n",
                agent_runs_dir=str(root / "runs"))
            self.assertEqual(done.returncode, 0, done.stderr)
            run_dir = Path(done.stdout.strip())
            text = (run_dir / "brief.md").read_text()
            self.assertIn("\nbranch: (detached)\n", text)


class BriefContentExactTest(unittest.TestCase):
    """The exact bytes of `brief.md`, with and without `--model`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        cls.repo = build_repository(root)
        cls.head = git(cls.repo, "rev-parse", "HEAD")
        cls.runs_root = root / "runs"
        cls.task_input = ("Investigate the thing.\n\nSee the details "
                          "above.\n\n   \n")
        cls.task_expected = "Investigate the thing.\n\nSee the details above."

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def run_for_brief(self, model: str | None,
                      kind: str = "reviewer") -> tuple[Path, str]:
        """Create one run and return its directory and `brief.md` text."""
        arguments = ["--slug", "exact-brief", "--kind", kind,
                    "--worktree", str(self.repo)]
        if model is not None:
            arguments += ["--model", model]
        done = run_script(arguments, cwd=self.repo, stdin=self.task_input,
                          agent_runs_dir=str(self.runs_root))
        self.assertEqual(done.returncode, 0, done.stderr)
        run_dir = Path(done.stdout.strip())
        return run_dir, (run_dir / "brief.md").read_text()

    def test_the_brief_matches_byte_for_byte_without_a_model(self) -> None:
        run_dir, text = self.run_for_brief(None)
        expected = expected_brief(
            kind="reviewer", worktree=self.repo, branch="main",
            base=self.head, model=None, run_id=run_dir.name,
            run_dir=run_dir, task=self.task_expected)
        self.assertEqual(text, expected)

    def test_the_brief_matches_byte_for_byte_with_a_model(self) -> None:
        run_dir, text = self.run_for_brief("claude-opus-4-6")
        expected = expected_brief(
            kind="reviewer", worktree=self.repo, branch="main",
            base=self.head, model="claude-opus-4-6", run_id=run_dir.name,
            run_dir=run_dir, task=self.task_expected)
        self.assertEqual(text, expected)

    def test_a_writer_brief_adds_the_commit_step(self) -> None:
        run_dir, text = self.run_for_brief(None, kind="writer")
        expected = expected_brief(
            kind="writer", worktree=self.repo, branch="main",
            base=self.head, model=None, run_id=run_dir.name,
            run_dir=run_dir, task=self.task_expected)
        self.assertEqual(text, expected)


class UsageErrorTest(unittest.TestCase):
    """Argument combinations the contract calls out as usage errors."""

    def test_base_with_kind_reviewer_is_a_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as cwd:
            done = run_script(
                ["--slug", "bad-combo", "--kind", "reviewer",
                 "--base", "main"], cwd=Path(cwd), stdin="Task.\n")
        self.assertEqual(done.returncode, 2)
        self.assertIn("--base requires --kind writer", done.stderr)

    def test_an_empty_stdin_body_is_a_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as cwd:
            done = run_script(
                ["--slug", "bad-body", "--kind", "writer", "--base", "main"],
                cwd=Path(cwd), stdin="   \n\n")
        self.assertEqual(done.returncode, 2)
        self.assertIn("must not be empty", done.stderr)


class BadBaseCleanupTest(unittest.TestCase):
    """A `--base` that git rejects leaves no trace behind."""

    def test_an_invalid_base_leaves_no_run_dir_and_no_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            repo = build_repository(root)
            runs_root = root / "runs"
            done = run_script(
                ["--slug", "bad-base", "--kind", "writer",
                 "--base", "does-not-exist-ref"],
                cwd=repo, stdin="Task.\n", agent_runs_dir=str(runs_root))
            self.assertEqual(done.returncode, 1)
            self.assertEqual(sorted(p.name for p in runs_root.iterdir()),
                             [".gitignore"])
            worktrees = git(repo, "worktree", "list", "--porcelain")
            self.assertNotIn(str(runs_root), worktrees)


class WorktreeAddFailureCleanupTest(unittest.TestCase):
    """A failure that strikes after `git worktree add` still leaves no trace.

    Calls `main()` in-process so the id can be pinned (`secrets.token_hex`
    patched to a fixed value) and a later step forced to fail
    (`head_sha_of` patched to raise), which a subprocess run could not do
    without its own patching hook.
    """

    def test_a_failure_after_the_worktree_is_added_discards_it(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            repo = build_repository(root)
            runs_root = root / "runs"
            branch = "agent/cleanup-check-deadbeef"
            original_cwd = os.getcwd()
            self.addCleanup(os.chdir, original_cwd)
            self.addCleanup(os.environ.pop, "AGENT_RUNS_DIR", None)
            os.chdir(repo)
            os.environ["AGENT_RUNS_DIR"] = str(runs_root)
            argv = ["--slug", "cleanup-check", "--kind", "writer",
                   "--base", "main"]
            with mock.patch.object(create_agent_run.secrets, "token_hex",
                                   return_value="deadbeef"), \
                mock.patch.object(create_agent_run, "head_sha_of",
                                  side_effect=OSError("boom")), \
                mock.patch.object(sys, "stdin", io.StringIO("Task.\n")):
                status = create_agent_run.main(argv)
            self.assertEqual(status, 1)
            self.assertEqual(sorted(p.name for p in runs_root.iterdir()),
                             [".gitignore"])
            worktrees = git(repo, "worktree", "list", "--porcelain")
            self.assertNotIn(str(runs_root), worktrees)
            self.assertEqual(git(repo, "branch", "--list", branch), "")


if __name__ == "__main__":
    unittest.main()
