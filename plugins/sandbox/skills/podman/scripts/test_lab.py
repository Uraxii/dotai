"""Tests that the blank-frame gate rejects a capture nothing painted into.

The numbers below are not invented. Each one was measured by running
`lab shot` against a real podman lab on 2026-09-12, one case per capture:

    nothing ran          stddev=0        colors=1    bytes=250
    command exited       stddev=0        colors=1    bytes=250
    dialog box only      stddev=5213.05  colors=2    bytes=444
    real test pattern    stddev=19661.3  colors=530  bytes=8852

The third case is the one that matters. A frame that is 99% one colour with
one small widget in the middle passed a `stddev == 0` gate, so a window that
never painted was reported as a successful screenshot. These tests pin the
rule that separates it from the real capture.

They need no podman: the gate reads the text of one `identify` line.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.machinery
import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lab_container

# `lab` is a command, so it carries no `.py` suffix and a plain import misses
# it. Name its loader instead of guessing one from the extension.
LOADER = importlib.machinery.SourceFileLoader(
    "lab", str(Path(__file__).resolve().parent / "lab")
)
SPEC = importlib.util.spec_from_loader("lab", LOADER)
lab = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(lab)

NOTHING_RAN = "stddev=0 colors=1 bytes=250"
COMMAND_EXITED = "stddev=0 colors=1 bytes=250"
DIALOG_ONLY = "stddev=5213.05 colors=2 bytes=444"
REAL_PATTERN = "stddev=19661.3 colors=530 bytes=8852"


class IsBlankTest(unittest.TestCase):
    """The four measured captures, and the rule that sorts them."""

    def test_a_display_nothing_ran_on_is_blank(self) -> None:
        self.assertTrue(lab.is_blank(NOTHING_RAN))

    def test_a_command_that_exited_without_painting_is_blank(self) -> None:
        self.assertTrue(lab.is_blank(COMMAND_EXITED))

    def test_a_frame_holding_only_a_dialog_box_is_blank(self) -> None:
        self.assertTrue(lab.is_blank(DIALOG_ONLY))

    def test_a_real_multicolour_capture_is_not_blank(self) -> None:
        self.assertFalse(lab.is_blank(REAL_PATTERN))

    def test_three_colours_is_the_first_frame_that_passes(self) -> None:
        self.assertTrue(lab.is_blank("stddev=1 colors=2 bytes=9"))
        self.assertFalse(lab.is_blank("stddev=1 colors=3 bytes=9"))

    def test_a_line_without_a_colour_count_is_an_error(self) -> None:
        with self.assertRaises(lab_container.LabError):
            lab.is_blank("stddev=19661.3 bytes=8852")


class ShotCommandConvergeTest(unittest.TestCase):
    """`up` reconciles `lab-shot`, including into a lab it did not create."""

    def test_up_copies_the_shot_command_into_an_unchanged_lab(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            definition = repo / lab_container.DEFINITION_SUBPATH
            definition.mkdir(parents=True)
            (definition / "Containerfile").write_text("FROM debian:13-slim\n")
            subprocess.run(["git", "init", "--initial-branch=main", str(repo)],
                           check=True, capture_output=True, text=True)
            for key, value in (("user.email", "test@example.com"),
                               ("user.name", "Test")):
                subprocess.run(["git", "config", key, value], cwd=str(repo),
                               check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "initial"],
                           cwd=str(repo), check=True, capture_output=True,
                           text=True)
            installed: list[str] = []
            patches = mock.patch.multiple(
                lab_container,
                require_podman=lambda: "5.0.0",
                build_image=lambda definition: False,
                read_spec=lambda lab: MatchingSpec(),
                create_container=fail_on_create,
                start_container=lambda lab: False,
                install_shot_command=lambda lab: installed.append(lab.name),
                sync_clone=lambda lab, repo, branch, head: False,
                run_setup=lambda lab, definition, workdir: False,
                wait_ready=lambda lab, definition: False,
            )
            patches.start()
            self.addCleanup(patches.stop)
            args = argparse.Namespace(name="demo", repo=str(repo), branch=None,
                                      port=None)

            with contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(lab.command_up(args), 0)

            self.assertEqual(installed, ["demo"])
            self.assertIn("changed=0", printed.getvalue())


class MatchingSpec:
    """Stand in for a stored spec that equals whatever `up` wants."""

    def __eq__(self, other: object) -> bool:
        return True


def fail_on_create(*args: object) -> None:
    raise AssertionError("the container already matched the wanted spec")


class GitWorktreeTest(unittest.TestCase):
    """A linked worktree clones from its shared git directory."""

    def test_the_common_git_directory_clones_a_detached_worktree_head(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            repo = parent / "repo"
            worktree = parent / "worktree"
            subprocess.run(["git", "init", str(repo)], check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=str(repo), check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                           cwd=str(repo), check=True, capture_output=True, text=True)
            (repo / "tracked").write_text("tracked\n")
            subprocess.run(["git", "add", "tracked"], cwd=str(repo), check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=str(repo),
                           check=True, capture_output=True, text=True)
            subprocess.run(["git", "worktree", "add", "--detach", str(worktree)],
                           cwd=str(repo), check=True, capture_output=True, text=True)
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(worktree),
                                  check=True, capture_output=True, text=True).stdout.strip()
            common = lab.resolve_git_common_dir(worktree)
            clone = parent / "clone"
            subprocess.run(["git", "clone", str(common), str(clone)], check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "fetch", str(common), head], cwd=str(clone),
                           check=True, capture_output=True, text=True)
            subprocess.run(["git", "cat-file", "-e", f"{head}^{{commit}}"],
                           cwd=str(clone), check=True, capture_output=True, text=True)


class GitReferenceTest(unittest.TestCase):
    """A tag resolves to the commit the lab checks out."""

    def test_an_annotated_tag_resolves_to_its_commit_and_displays_a_short_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            subprocess.run(["git", "init", "--initial-branch=main", str(repo)],
                           check=True, capture_output=True, text=True)
            for key, value in (("user.email", "test@example.com"),
                               ("user.name", "Test")):
                subprocess.run(["git", "config", key, value], cwd=str(repo),
                               check=True, capture_output=True, text=True)
            (repo / "tracked").write_text("tracked\n")
            subprocess.run(["git", "add", "tracked"], cwd=str(repo), check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=str(repo),
                           check=True, capture_output=True, text=True)
            subprocess.run(["git", "tag", "-a", "v1", "-m", "v1"], cwd=str(repo),
                           check=True, capture_output=True, text=True)
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                                    check=True, capture_output=True, text=True).stdout.strip()

            branch, head = lab.resolve_branch(repo, "v1")

            self.assertEqual(branch, "refs/tags/v1")
            self.assertEqual(head, commit)
            self.assertIn(" main ", lab.describe_repo(str(repo)))


if __name__ == "__main__":
    unittest.main()
