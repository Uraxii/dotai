"""Tests that a hostile branch name reaches podman as inert argv.

The previous version of this skill interpolated a branch name into a remote
`bash -lc` string, so a branch called `x;rm -rf /` ran. These tests pin the
replacement: every element of every podman call is a separate argv element,
and no shell ever parses one. They need no podman: the one subprocess call
site, `lab_container.run`, is replaced by a recorder.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest import mock

import lab_container
import lab_profile

HOSTILE_BRANCH = "x;rm -rf / #$(touch /tmp/lab-injection-proof)`id`"
HEAD = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
REPO = Path("/src/myrepo")
GIT_COMMON = Path("/src/myrepo.git")
SHELL_WORDS = ("bash", "sh", "-c", "-lc", "eval")


class FakePodman:
    """Record every podman call and answer as a container with no clone."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.existing_paths: set[str] = set()

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(list(args))
        absent_clone = "test" in args and args[-1] not in self.existing_paths
        return subprocess.CompletedProcess(
            args, 1 if absent_clone else 0, "", ""
        )

    def elements(self) -> list[str]:
        """Every argument of every recorded call, flattened."""
        return [element for call in self.calls for element in call]


class DetachedHeadPodman(FakePodman):
    """Report a clone whose detached HEAD already names the requested commit."""

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        done = super().__call__(args)
        if args[-2:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, HEAD, "")
        if args[-3:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        return done


class ExistingClonePodman(FakePodman):
    """Record a clone whose current commit differs from the requested one."""

    def __init__(self, container_only: bool) -> None:
        super().__init__()
        self.container_only = container_only

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        done = super().__call__(args)
        if args[-3:-1] == ["test", "-d"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[-2:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, "container-head", "")
        if args[-3:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(args, 0, "main", "")
        if "for-each-ref" in args:
            return subprocess.CompletedProcess(
                args, 0, "refs/remotes/lab-host/main", ""
            )
        if "rev-list" in args:
            return subprocess.CompletedProcess(
                args, 0, "container-only" if self.container_only else "", ""
            )
        return done


class HostileBranchTest(unittest.TestCase):
    """A branch name is data. It never becomes part of a command string."""

    def setUp(self) -> None:
        self.podman = FakePodman()
        patch = mock.patch.object(lab_container, "run", self.podman)
        patch.start()
        self.addCleanup(patch.stop)
        self.lab = lab_container.Lab("demo")

    def test_sync_clone_passes_the_branch_as_one_argument(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH, HEAD)
        self.assertIn(HOSTILE_BRANCH, self.podman.elements())

    def test_no_argument_mixes_the_branch_with_anything_else(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH, HEAD)
        for element in self.podman.elements():
            if element != HOSTILE_BRANCH:
                self.assertNotIn("rm -rf", element)
                self.assertNotIn("$(", element)

    def test_no_call_asks_for_a_shell(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH, HEAD)
        for element in self.podman.elements():
            self.assertNotIn(element, SHELL_WORDS)

    def test_the_branch_is_checked_out_by_name(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH, HEAD)
        checkouts = [call for call in self.podman.calls if "checkout" in call]
        self.assertEqual(len(checkouts), 1)
        self.assertEqual(checkouts[0][-2:], [HOSTILE_BRANCH, HEAD])

    def test_the_clone_is_made_from_the_read_only_mount(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH, HEAD)
        clones = [call for call in self.podman.calls if "clone" in call]
        self.assertEqual(
            clones[0][-2:],
            [lab_container.MOUNT_GIT_COMMON_READONLY, "/work/myrepo"],
        )

    def test_create_mounts_the_common_git_directory_read_only(self) -> None:
        spec = lab_container.LabSpec(
            repo=str(REPO), branch="main", profile="base", port=None,
            image="test:latest", recipe_sha256="deadbeef",
            git_common_dir=str(GIT_COMMON),
        )

        lab_container.create_container(self.lab, spec, REPO, GIT_COMMON)

        create = [call for call in self.podman.calls if call[0] == "create"][0]
        self.assertIn(
            f"{GIT_COMMON}:{lab_container.MOUNT_GIT_COMMON_READONLY}:ro", create
        )

    def test_a_hostile_hook_argv_stays_argv(self) -> None:
        profile = lab_profile.Profile(
            name="evil",
            directory=Path("/tmp/evil"),
            port=None,
            setup=(HOSTILE_BRANCH,),
            ready=(),
            ready_timeout_sec=1,
            recipe_sha256="deadbeef",
        )
        lab_container.run_setup(self.lab, profile, "/work/myrepo")
        self.assertIn(HOSTILE_BRANCH, self.podman.elements())
        for element in self.podman.elements():
            self.assertNotIn(element, SHELL_WORDS)

    def test_the_injection_never_ran(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH, HEAD)
        self.assertFalse(Path("/tmp/lab-injection-proof").exists())


class NameTest(unittest.TestCase):
    """The lab's name is the only identity; the rest is derived from it."""

    def test_podman_object_names_come_from_the_lab_name(self) -> None:
        lab = lab_container.Lab("demo")
        self.assertEqual(lab.container, "lab-demo")
        self.assertEqual(lab.volume, "lab-demo-work")
        self.assertEqual(lab.clone_path(REPO), "/work/myrepo")


class SetupRestartTest(unittest.TestCase):
    """A restarted container needs its setup-launched process again."""

    def setUp(self) -> None:
        self.podman = FakePodman()
        patch = mock.patch.object(lab_container, "run", self.podman)
        patch.start()
        self.addCleanup(patch.stop)
        self.lab = lab_container.Lab("demo")
        self.profile = lab_profile.Profile(
            name="app",
            directory=Path("/tmp/app"),
            port=None,
            setup=("start-app",),
            ready=(),
            ready_timeout_sec=1,
            recipe_sha256="deadbeef",
        )

    def test_a_started_container_reruns_setup_despite_its_sentinel(self) -> None:
        sentinel = lab_container.SETUP_SENTINEL_PREFIX + "deadbeef"
        self.podman.existing_paths.add(sentinel)

        changed = lab_container.run_setup(
            self.lab, self.profile, "/work/myrepo", force=True
        )

        self.assertTrue(changed)
        self.assertIn("start-app", self.podman.elements())


class DetachedHeadTest(unittest.TestCase):
    """A revision without a local branch stays detached."""

    def setUp(self) -> None:
        self.podman = FakePodman()
        patch = mock.patch.object(lab_container, "run", self.podman)
        patch.start()
        self.addCleanup(patch.stop)
        self.lab = lab_container.Lab("demo")

    def test_sync_clone_checks_out_a_detached_revision(self) -> None:
        lab_container.sync_clone(self.lab, REPO, "HEAD", HEAD)

        checkout = [call for call in self.podman.calls if "checkout" in call][0]
        self.assertEqual(checkout[-4:], ["checkout", "--quiet", "--detach", HEAD])

    def test_a_detached_clone_at_the_requested_sha_is_current(self) -> None:
        detached = DetachedHeadPodman()
        with mock.patch.object(lab_container, "run", detached):
            current = lab_container.at_revision(
                self.lab, "/work/myrepo", "HEAD", HEAD
            )

        self.assertTrue(current)


class ContainerCommitTest(unittest.TestCase):
    """Host branch switches preserve commits that only the lab can reach."""

    def setUp(self) -> None:
        self.podman = ExistingClonePodman(container_only=True)
        patch = mock.patch.object(lab_container, "run", self.podman)
        patch.start()
        self.addCleanup(patch.stop)
        self.lab = lab_container.Lab("demo")

    def test_sync_refuses_to_drop_a_container_only_commit(self) -> None:
        with self.assertRaisesRegex(lab_container.LabError, "lab demo.*git bundle"):
            lab_container.sync_clone(self.lab, REPO, "main", HEAD)

        self.assertFalse(any("checkout" in call for call in self.podman.calls))

    def test_sync_allows_a_branch_switch_without_container_only_commits(self) -> None:
        no_private_commit = ExistingClonePodman(container_only=False)
        with mock.patch.object(lab_container, "run", no_private_commit):
            changed = lab_container.sync_clone(self.lab, REPO, "main", HEAD)

        self.assertTrue(changed)
        self.assertTrue(any("checkout" in call for call in no_private_commit.calls))


if __name__ == "__main__":
    unittest.main()
