"""Tests for the worktree prune audit.

The bucket table is the part that decides whether a human deletes a
directory, so its two safety invariants are asserted over every combination
of its six inputs. The ordering is checked differentially against the GNU
`sort` the shell version piped through. The rest of the suite drives the real
script against a real repository with real worktrees: a local bare remote
stands in for origin and a stub `gh` on PATH stands in for the API, so nothing
here touches the network, the user's checkout, or the user's transcripts.
"""

from __future__ import annotations

import contextlib
import io
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import locale
from unittest import mock

import worktree_audit

SCRIPT = Path(__file__).resolve().parent / "worktree_audit.py"
EXPECTED_HEADER = ("SIZE\tAGE\tMERGED\tDIRTY\tREMOTE\tPR\tLAST_CHAT"
                   "\tBUCKET\tWORKTREE")
SORT_COMMAND = ["sort", "-t\t", "-k1,1", "-rh"]
SIZE_ORDER_MEGA = 2
COLLATION_LOCALES = ("C", "C.UTF-8", "en_US.UTF-8")

BUCKETS = {"safe", "review", "hold-wip", "hold-open-pr", "verify-recent-chat"}
DIRTY_STATES = ("clean", "wip:1", "wip:12", "scratch:3", "unknown")
PR_STATES = ("-", "OPEN", "MERGED", "CLOSED")
ANCESTRIES = ("YES", "no", "?")
TRUTH = (True, False)

PR_NUMBER_OPEN = 11
PR_NUMBER_MERGED = 12
RECENT_TRANSCRIPT = "recent.jsonl"
STALE_TRANSCRIPT = "stale.jsonl"
STALE_MTIME_EPOCH = 1_700_000_000
METACHARACTER_DIRECTORY = "wt-a+b[c].d"
UNDECODABLE_DIRECTORY = os.fsdecode(b"wt-\xff-bad")
WORKTREE_BRANCHES = {
    "wt-clean": "clean-branch",
    "wt-wip": "wip-branch",
    "wt-scratch": "scratch-branch",
    "wt-gone": "gone-branch",
    METACHARACTER_DIRECTORY: "metacharacter-branch",
}


def every_combination() -> list[tuple[str, str, bool, str, bool, bool]]:
    """Every input tuple `classify_bucket` can be called with."""
    return list(itertools.product(DIRTY_STATES, PR_STATES, TRUTH, ANCESTRIES,
                                  TRUTH, TRUTH))


class ClassifyBucketTest(unittest.TestCase):
    """The decision table, by exhaustion and by named precedence."""

    def test_every_combination_names_one_known_bucket(self) -> None:
        for arguments in every_combination():
            with self.subTest(arguments=arguments):
                self.assertIn(worktree_audit.classify_bucket(*arguments),
                              BUCKETS)

    def test_unknown_facts_never_establish_safe(self) -> None:
        for arguments in every_combination():
            if arguments[5]:
                continue
            with self.subTest(arguments=arguments):
                self.assertNotEqual(
                    worktree_audit.classify_bucket(*arguments), "safe")

    def test_safe_needs_every_holding_fact_to_be_absent(self) -> None:
        for arguments in every_combination():
            dirty, pr_state, recent, ancestry, _, _ = arguments
            if worktree_audit.classify_bucket(*arguments) != "safe":
                continue
            with self.subTest(arguments=arguments):
                self.assertFalse(dirty.startswith("wip:"))
                self.assertNotEqual(pr_state, "OPEN")
                self.assertFalse(recent)
                self.assertTrue(ancestry == "YES" or pr_state == "MERGED")

    def test_uncommitted_tracked_work_holds_before_anything_else(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("wip:2", "OPEN", True, "YES",
                                           True, True),
            "hold-wip")

    def test_an_open_pr_holds_before_a_recent_chat(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("clean", "OPEN", True, "YES",
                                           True, True),
            "hold-open-pr")

    def test_a_recent_chat_outranks_a_merged_ancestor(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("clean", "-", True, "YES",
                                           False, True),
            "verify-recent-chat")

    def test_an_ancestor_of_the_trunk_is_safe(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("clean", "-", False, "YES",
                                           False, True),
            "safe")

    def test_a_merged_pr_at_the_same_head_is_safe(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("scratch:3", "MERGED", False, "no",
                                           True, True),
            "safe")

    def test_a_merged_pr_at_a_different_head_needs_review(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("clean", "MERGED", False, "no",
                                           False, True),
            "review")

    def test_a_matching_head_without_a_merged_pr_needs_review(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("clean", "CLOSED", False, "no",
                                           True, True),
            "review")

    def test_untracked_scratch_alone_does_not_hold(self) -> None:
        self.assertEqual(
            worktree_audit.classify_bucket("scratch:9", "-", False, "YES",
                                           False, True),
            "safe")

    def test_only_the_wip_marker_holds_on_dirtiness(self) -> None:
        for dirty in ("wipe", "swip:1", "clean", "unknown"):
            with self.subTest(dirty=dirty):
                self.assertNotEqual(
                    worktree_audit.classify_bucket(dirty, "-", False, "YES",
                                                   False, True),
                    "hold-wip")


class CommaRadixSizeTest(unittest.TestCase):
    """Sizes as `du -sh` prints them where the locale decimal point is a comma.

    No comma-decimal locale is guaranteed installed, so the radix is taken
    from a stubbed `localeconv`, which is the boundary the real code reads
    it from.
    """

    def setUp(self) -> None:
        patch = mock.patch.object(worktree_audit.locale, "localeconv",
                                  return_value={"decimal_point": ","})
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_comma_decimal_size_keeps_its_magnitude(self) -> None:
        self.assertEqual(worktree_audit.human_size("1,5M"),
                         (SIZE_ORDER_MEGA, 1.5))

    def test_a_comma_decimal_size_outranks_a_smaller_one(self) -> None:
        self.assertGreater(worktree_audit.human_size("2,4M"),
                           worktree_audit.human_size("1,5M"))

    def test_a_megabyte_still_outranks_a_kilobyte(self) -> None:
        self.assertGreater(worktree_audit.human_size("1,5M"),
                           worktree_audit.human_size("900,0K"))


class ParseWorktreesTest(unittest.TestCase):
    """The NUL-delimited porcelain parser."""

    def test_each_blank_field_closes_one_record(self) -> None:
        porcelain = ("worktree /w/one\0HEAD abc\0branch refs/heads/one\0\0"
                     "worktree /w/two\0HEAD def\0detached\0\0")
        self.assertEqual(worktree_audit.parse_worktrees(porcelain),
                         [("/w/one", "ok"), ("/w/two", "ok")])

    def test_a_prunable_record_carries_its_state(self) -> None:
        porcelain = ("worktree /w/one\0HEAD abc\0\0"
                     "worktree /w/gone\0HEAD def\0prunable gitdir file "
                     "points to non-existent location\0\0")
        self.assertEqual(worktree_audit.parse_worktrees(porcelain),
                         [("/w/one", "ok"), ("/w/gone", "prunable")])

    def test_prunable_does_not_leak_into_the_next_record(self) -> None:
        porcelain = ("worktree /w/gone\0prunable\0\0worktree /w/live\0\0")
        self.assertEqual(worktree_audit.parse_worktrees(porcelain),
                         [("/w/gone", "prunable"), ("/w/live", "ok")])

    def test_a_record_left_unterminated_still_arrives(self) -> None:
        porcelain = "worktree /w/one\0\0worktree /w/two\0HEAD abc\0"
        self.assertEqual(worktree_audit.parse_worktrees(porcelain),
                         [("/w/one", "ok"), ("/w/two", "ok")])

    def test_a_path_holding_spaces_survives(self) -> None:
        self.assertEqual(
            worktree_audit.parse_worktrees("worktree /w/two words\0\0"),
            [("/w/two words", "ok")])

    def test_no_worktrees_is_no_records(self) -> None:
        self.assertEqual(worktree_audit.parse_worktrees(""), [])


class HumanSizeTest(unittest.TestCase):
    """Sizes order the way a human-numeric sort reads them."""

    def test_a_unit_outranks_a_plain_byte_count(self) -> None:
        self.assertGreater(worktree_audit.human_size("4.0K"),
                           worktree_audit.human_size("512"))

    def test_units_rank_against_each_other(self) -> None:
        sizes = ["1.0G", "31M", "8.0K", "512", "2.4M"]
        sizes.sort(key=worktree_audit.human_size, reverse=True)
        self.assertEqual(sizes, ["1.0G", "31M", "2.4M", "8.0K", "512"])

    def test_magnitudes_inside_one_unit_rank_numerically(self) -> None:
        self.assertGreater(worktree_audit.human_size("31M"),
                           worktree_audit.human_size("2.4M"))

    def test_an_unknown_size_ranks_with_a_zero_byte_count(self) -> None:
        for size in ("?", "-"):
            with self.subTest(size=size):
                self.assertEqual(worktree_audit.human_size(size),
                                 worktree_audit.human_size("0"))
                self.assertLess(worktree_audit.human_size(size),
                                worktree_audit.human_size("1"))


def git(repo: Path, *arguments: str) -> str:
    """Run git in `repo` and return its stdout, raising on failure."""
    done = subprocess.run(["git", "-C", str(repo), *arguments],
                          capture_output=True, text=True, check=True)
    return done.stdout.strip()


def build_repository(root: Path) -> Path:
    """Create a repo whose worktrees cover every column the audit prints."""
    origin = root / "origin.git"
    repo = root / "repo"
    subprocess.run(["git", "init", "--quiet", "--bare", "-b", "main",
                    str(origin)], check=True)
    subprocess.run(["git", "init", "--quiet", "-b", "main", str(repo)],
                   check=True)
    git(repo, "config", "user.email", "audit@example.invalid")
    git(repo, "config", "user.name", "audit")
    (repo / "file.txt").write_text("one\n")
    git(repo, "add", "file.txt")
    git(repo, "commit", "--quiet", "-m", "one")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "--quiet", "origin", "main")
    git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    for name, branch in WORKTREE_BRANCHES.items():
        git(repo, "worktree", "add", "--quiet", str(repo / name), "-b",
            branch, "main")
    (repo / "wt-wip" / "file.txt").write_text("changed\n")
    (repo / "wt-scratch" / "untracked-one").write_text("x\n")
    (repo / "wt-scratch" / "untracked-two").write_text("y\n")
    shutil.rmtree(repo / "wt-gone")
    return repo


def build_stub_gh(root: Path, pull_requests: list[dict]) -> Path:
    """Write a `gh` on PATH that answers `pr list` with `pull_requests`."""
    directory = root / "stub-bin"
    directory.mkdir()
    stub = directory / "gh"
    stub.write_text("#!/usr/bin/env python3\n"
                    "import sys\n"
                    f"sys.stdout.write({json.dumps(json.dumps(pull_requests))})"
                    "\n")
    stub.chmod(0o755)
    return directory


def build_transcripts(root: Path, recent_for: Path, stale_for: Path) -> Path:
    """Write two transcripts, one touched now and one long stale."""
    directory = root / "transcripts" / "-encoded-cwd"
    directory.mkdir(parents=True)
    recent = directory / RECENT_TRANSCRIPT
    recent.write_text(json.dumps({"cwd": f"{recent_for}/"}) + "\n")
    stale = directory / STALE_TRANSCRIPT
    stale.write_text(json.dumps({"cwd": str(stale_for)}) + "\n")
    os.utime(stale, (STALE_MTIME_EPOCH, STALE_MTIME_EPOCH))
    return root / "transcripts"


class AuditOutputTest(unittest.TestCase):
    """The table the script prints for a real repository."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        cls.repo = build_repository(root)
        clean_head = git(cls.repo / "wt-clean", "rev-parse", "HEAD")
        cls.stub_bin = build_stub_gh(root, [
            {"number": PR_NUMBER_OPEN, "state": "OPEN",
             "headRefName": WORKTREE_BRANCHES["wt-wip"],
             "headRefOid": clean_head},
            {"number": PR_NUMBER_MERGED, "state": "MERGED",
             "headRefName": "branch-nobody-checked-out",
             "headRefOid": clean_head},
        ])
        cls.transcripts = build_transcripts(
            root, cls.repo / "wt-clean", cls.repo / METACHARACTER_DIRECTORY)
        cls.home = root / "home"
        cls.home.mkdir()
        cls.rows = cls.audit()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def audit(cls) -> list[str]:
        """Run the script against the fixture and return its stdout lines."""
        environment = dict(os.environ)
        environment["PATH"] = f"{cls.stub_bin}{os.pathsep}{environment['PATH']}"
        environment["HOME"] = str(cls.home)
        done = subprocess.run(
            [sys.executable, str(SCRIPT), str(cls.repo), str(cls.transcripts)],
            capture_output=True, text=True, check=True, env=environment)
        cls.errors = done.stderr
        return done.stdout.splitlines()

    def column(self, worktree: str, index: int) -> str:
        """One column of the row for `worktree`, by header position."""
        suffix = f"\t{self.repo / worktree}"
        matches = [row for row in self.rows if row.endswith(suffix)]
        self.assertEqual(len(matches), 1, f"no single row for {worktree}")
        return matches[0].split("\t")[index]

    def test_the_header_names_every_column_in_order(self) -> None:
        self.assertEqual(self.rows[0], EXPECTED_HEADER)

    def test_the_primary_worktree_is_not_listed(self) -> None:
        own_row = f"\t{self.repo}"
        self.assertEqual([row for row in self.rows[1:]
                          if row.endswith(own_row)], [])

    def test_a_worktree_git_lost_the_directory_for_is_prunable(self) -> None:
        gone = self.repo / "wt-gone"
        self.assertIn(f"-\t?\t-\t-\t-\t-\t-\tprunable\t{gone}", self.rows)

    def test_a_worktree_with_nothing_uncommitted_reads_clean(self) -> None:
        self.assertEqual(self.column("wt-clean", 3), "clean")

    def test_a_modified_tracked_file_reads_as_work_in_progress(self) -> None:
        self.assertEqual(self.column("wt-wip", 3), "wip:1")

    def test_untracked_files_alone_read_as_scratch(self) -> None:
        self.assertEqual(self.column("wt-scratch", 3), "scratch:2")

    def test_tracked_work_holds_the_worktree(self) -> None:
        self.assertEqual(self.column("wt-wip", 7), "hold-wip")

    def test_an_open_pr_on_the_branch_holds_the_worktree(self) -> None:
        self.assertEqual(self.column("wt-wip", 5), f"#{PR_NUMBER_OPEN}/OPEN")

    def test_a_branch_with_no_pr_leaves_the_column_empty(self) -> None:
        self.assertEqual(self.column("wt-scratch", 5), "-")

    def test_a_chat_from_today_marks_the_worktree_for_a_check(self) -> None:
        self.assertEqual(self.column("wt-clean", 7), "verify-recent-chat")

    def test_a_long_stale_chat_still_shows_its_date(self) -> None:
        self.assertEqual(self.column(METACHARACTER_DIRECTORY, 6), "2023-11-14")

    def test_a_stale_chat_does_not_hold_the_worktree(self) -> None:
        self.assertEqual(self.column(METACHARACTER_DIRECTORY, 7), "safe")

    def test_a_worktree_no_chat_names_has_no_date(self) -> None:
        self.assertEqual(self.column("wt-scratch", 6), "-")

    def test_a_branch_never_pushed_has_no_remote(self) -> None:
        self.assertEqual(self.column("wt-clean", 4), "no-remote")

    def test_a_worktree_on_the_trunk_is_merged(self) -> None:
        self.assertEqual(self.column("wt-clean", 2), "YES")

    def test_nothing_is_warned_about_when_every_fact_is_readable(self) -> None:
        self.assertEqual(self.errors, "")


def gnu_sort_available() -> bool:
    """Whether a GNU `sort` this test can compare against is on PATH."""
    try:
        done = subprocess.run(["sort", "--version"], capture_output=True,
                              text=True, check=False)
    except OSError:
        return False
    return done.returncode == 0 and "GNU coreutils" in done.stdout


def sort_fixture_lines() -> list[str]:
    """Rows spanning several sizes, with deliberate ties inside each size.

    The tied rows differ in columns the size key never reads, so only a
    fallback that collates the whole line can order them. They are listed
    here in no particular order; the test asserts nothing about this order.
    """
    spread = ["1.0G", "31M", "2.4M", "8.0K", "8.0K", "8.0K", "512", "512",
              "0", "-", "?"]
    return [
        "\t".join([size, f"{index}d", "YES", "clean", "no-remote", "-", "-",
                    "safe", f"/w/tree-{chr(ord('a') + index)}"])
        for index, size in enumerate(spread)
    ]


@unittest.skipUnless(gnu_sort_available(), "needs GNU sort to compare against")
class SortFidelityTest(unittest.TestCase):
    """The row order, against the GNU sort the shell version piped through.

    The oracle is `sort -t$'\\t' -k1,1 -rh` itself, run as a subprocess, so
    nothing here can agree with the implementation by construction. Ties on
    the size key are the point: GNU sort settles them by collating the whole
    line under LC_COLLATE, which is the behaviour `size_sort_key` models.
    """

    def gnu_sorted(self, lines: list[str], name: str) -> list[str]:
        done = subprocess.run(
            SORT_COMMAND, input="\n".join(lines) + "\n", capture_output=True,
            text=True, check=True, env=dict(os.environ, LC_ALL=name))
        return done.stdout.splitlines()

    def python_sorted(self, lines: list[str]) -> list[str]:
        rows = [worktree_audit.Row(*line.split("\t")) for line in lines]
        rows.sort(key=worktree_audit.size_sort_key, reverse=True)
        return [row.rendered() for row in rows]

    def test_the_order_matches_gnu_sort_in_every_usable_locale(self) -> None:
        lines = sort_fixture_lines()
        self.addCleanup(locale.setlocale, locale.LC_COLLATE,
                        locale.setlocale(locale.LC_COLLATE))
        compared = 0
        for name in COLLATION_LOCALES:
            try:
                locale.setlocale(locale.LC_COLLATE, name)
            except locale.Error:
                continue
            compared += 1
            with self.subTest(collation=name):
                self.assertEqual(self.python_sorted(lines),
                                 self.gnu_sorted(lines, name))
        self.assertGreater(compared, 0, "no collation locale was usable")

    def test_the_fixture_actually_ties_and_actually_spreads(self) -> None:
        sizes = [line.split("\t")[0] for line in sort_fixture_lines()]

        self.assertLess(len(set(sizes)), len(sizes))
        self.assertGreater(len(set(sizes)), 1)


class UndecodablePathTest(unittest.TestCase):
    """A worktree path holding a byte that is not UTF-8."""

    def test_the_table_still_prints_and_carries_the_raw_bytes(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        repo = build_repository(root)
        odd = repo / UNDECODABLE_DIRECTORY
        git(repo, "worktree", "add", "--quiet", str(odd), "-b",
            "undecodable-branch", "main")
        transcripts = build_transcripts(root, repo / "wt-clean", odd)
        stub_bin = build_stub_gh(root, [])
        home = root / "home"
        home.mkdir()

        done = subprocess.run(
            [sys.executable, str(SCRIPT), str(repo), str(transcripts)],
            capture_output=True, check=False,
            env=dict(os.environ, HOME=str(home),
                     PATH=f"{stub_bin}{os.pathsep}{os.environ['PATH']}"))

        rows = done.stdout.splitlines()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(rows[0], worktree_audit.HEADER.encode())
        self.assertEqual(len(rows), len(WORKTREE_BRANCHES) + 2)
        self.assertTrue(any(row.endswith(b"\t" + os.fsencode(str(odd)))
                            for row in rows[1:]), done.stdout)


class AuditArgumentTest(unittest.TestCase):
    """What the script does when it is pointed somewhere unusable."""

    def test_a_path_holding_no_worktrees_prints_only_the_header(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            done = subprocess.run(
                [sys.executable, str(SCRIPT), str(empty), str(empty)],
                capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stdout.splitlines(), [worktree_audit.HEADER])

    def test_no_repository_anywhere_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            done = subprocess.run(
                [sys.executable, str(SCRIPT)], cwd=empty,
                capture_output=True, text=True, check=False,
                env=dict(os.environ, GIT_CEILING_DIRECTORIES=empty))
        self.assertEqual(done.returncode, 1)
        self.assertIn("not in a git repo", done.stderr)


class MainCallTest(unittest.TestCase):
    """`main` called as a function, with only the real arguments."""

    def test_the_repo_and_transcripts_are_read_from_the_front(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        repo = build_repository(root)
        transcripts = build_transcripts(root, repo / "wt-clean",
                                        repo / "wt-scratch")
        stub_bin = build_stub_gh(root, [])
        self.addCleanup(os.chdir, os.getcwd())
        self.addCleanup(os.environ.__setitem__, "PATH", os.environ["PATH"])
        os.environ["PATH"] = f"{stub_bin}{os.pathsep}{os.environ['PATH']}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            status = worktree_audit.main([str(repo), str(transcripts)])
        rows = printed.getvalue().splitlines()
        clean = [row for row in rows[1:]
                 if row.endswith(f"\t{repo / 'wt-clean'}")]
        self.assertEqual(status, 0)
        self.assertEqual(rows[0], worktree_audit.HEADER)
        self.assertEqual(len(clean), 1)
        self.assertNotEqual(clean[0].split("\t")[6], "-")


if __name__ == "__main__":
    unittest.main()
