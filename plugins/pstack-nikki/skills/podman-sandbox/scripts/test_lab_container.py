"""Tests that a hostile branch name reaches podman as inert argv.

The previous version of this skill interpolated a branch name into a remote
`bash -lc` string, so a branch called `x;rm -rf /` ran. These tests pin the
replacement: every element of every podman call is a separate argv element,
and no shell ever parses one. They need no podman: the one subprocess call
site, `lab_container.run`, is replaced by a recorder.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lab_container
import lab_profile

HOSTILE_BRANCH = "x;rm -rf / #$(touch /tmp/lab-injection-proof)`id`"
HOSTILE_BRANCH_REF = f"refs/heads/{HOSTILE_BRANCH}"
HEAD = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
SHORT_SHA = HEAD[:12]
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


class SetupPodman(FakePodman):
    """Record setup calls for one running container start."""

    def __init__(self) -> None:
        super().__init__()
        self.started_at = "2026-09-14T12:00:00.000000000Z"

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(list(args))
        if args[:2] == ["inspect", "lab-demo"]:
            return subprocess.CompletedProcess(args, 0, self.started_at, "")
        if args[-3:-1] == ["test", "-f"]:
            return subprocess.CompletedProcess(
                args, 0 if args[-1] in self.existing_paths else 1, "", ""
            )
        if args[-2:] == ["touch", args[-1]]:
            self.existing_paths.add(args[-1])
        return subprocess.CompletedProcess(args, 0, "", "")


class HostileBranchTest(unittest.TestCase):
    """A branch name is data. It never becomes part of a command string."""

    def setUp(self) -> None:
        self.podman = FakePodman()
        patch = mock.patch.object(lab_container, "run", self.podman)
        patch.start()
        self.addCleanup(patch.stop)
        self.lab = lab_container.Lab("demo")

    def test_sync_clone_passes_the_branch_as_one_argument(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH_REF, HEAD)
        self.assertIn(HOSTILE_BRANCH, self.podman.elements())

    def test_no_argument_mixes_the_branch_with_anything_else(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH_REF, HEAD)
        for element in self.podman.elements():
            if element != HOSTILE_BRANCH:
                self.assertNotIn("rm -rf", element)
                self.assertNotIn("$(", element)

    def test_no_call_asks_for_a_shell(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH_REF, HEAD)
        for element in self.podman.elements():
            self.assertNotIn(element, SHELL_WORDS)

    def test_the_branch_is_checked_out_by_name(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH_REF, HEAD)
        checkouts = [call for call in self.podman.calls if "checkout" in call]
        self.assertEqual(len(checkouts), 1)
        self.assertEqual(checkouts[0][-2:], [HOSTILE_BRANCH, HEAD])

    def test_the_clone_is_made_from_the_read_only_mount(self) -> None:
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH_REF, HEAD)
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
        lab_container.sync_clone(self.lab, REPO, HOSTILE_BRANCH_REF, HEAD)
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
        self.podman = SetupPodman()
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

    def test_an_external_restart_reruns_setup(self) -> None:
        self.assertTrue(lab_container.run_setup(self.lab, self.profile, "/work/myrepo"))
        self.podman.started_at = "2026-09-14T12:00:01.000000000Z"

        changed = lab_container.run_setup(self.lab, self.profile, "/work/myrepo")

        self.assertTrue(changed)
        self.assertEqual(self.podman.elements().count("start-app"), 2)

    def test_an_unchanged_running_container_skips_setup(self) -> None:
        self.assertTrue(lab_container.run_setup(self.lab, self.profile, "/work/myrepo"))

        changed = lab_container.run_setup(self.lab, self.profile, "/work/myrepo")

        self.assertFalse(changed)
        self.assertEqual(self.podman.elements().count("start-app"), 1)

    def test_a_retry_after_up_failed_before_setup_reruns_setup(self) -> None:
        self.assertTrue(lab_container.run_setup(self.lab, self.profile, "/work/myrepo"))
        # A failed `up` started the container again, then raised before setup.
        self.podman.started_at = "2026-09-14T12:05:00.000000000Z"

        changed = lab_container.run_setup(self.lab, self.profile, "/work/myrepo")

        self.assertTrue(changed)
        self.assertEqual(self.podman.elements().count("start-app"), 2)


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

    def test_sync_clone_detaches_for_an_empty_reference(self) -> None:
        lab_container.sync_clone(self.lab, REPO, "", HEAD)

        checkout = [call for call in self.podman.calls if "checkout" in call][0]
        self.assertEqual(checkout[-4:], ["checkout", "--quiet", "--detach", HEAD])

    def test_sync_clone_detaches_for_a_short_sha_reference(self) -> None:
        lab_container.sync_clone(self.lab, REPO, SHORT_SHA, HEAD)

        checkout = [call for call in self.podman.calls if "checkout" in call][0]
        self.assertEqual(checkout[-4:], ["checkout", "--quiet", "--detach", HEAD])

    def test_a_detached_clone_at_the_requested_sha_is_current(self) -> None:
        detached = DetachedHeadPodman()
        with mock.patch.object(lab_container, "run", detached):
            current = lab_container.at_revision(
                self.lab, "/work/myrepo", "HEAD", HEAD
            )

        self.assertTrue(current)


class LocalGitClone:
    """Run the container's git argv against a local clone."""

    def __init__(self, source: Path, clone: Path) -> None:
        self.source = source
        self.clone = clone

    def path(self, value: str) -> str:
        if value == lab_container.MOUNT_GIT_COMMON_READONLY:
            return str(self.source)
        if value == lab_container.MOUNT_WORK:
            return str(self.clone.parent)
        if value.startswith("/work/repo"):
            return str(self.clone) + value[len("/work/repo"):]
        return value

    def capture(self, _lab: lab_container.Lab, argv: list[str], workdir: str) -> str:
        done = subprocess.run(
            [self.path(value) for value in argv],
            cwd=self.path(workdir), capture_output=True, text=True, check=False,
        )
        if done.returncode:
            raise lab_container.LabError(done.stderr.strip())
        return done.stdout.strip()

    def status(self, _lab: lab_container.Lab, argv: list[str], workdir: str) -> int:
        return subprocess.run(
            [self.path(value) for value in argv],
            cwd=self.path(workdir), capture_output=True, text=True, check=False,
        ).returncode


class SyncedCommitTest(unittest.TestCase):
    """A lab preserves commits not contained by a head it previously synced."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.repo = self.parent / "repo"
        self.clone = self.parent / "clone"
        self.git("init", "--initial-branch=main", str(self.repo), cwd=self.parent)
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.commit("initial")
        self.lab = lab_container.Lab("demo")
        self.local = LocalGitClone(self.repo, self.clone)
        self.capture = mock.patch.object(
            lab_container, "exec_capture", self.local.capture
        )
        self.status = mock.patch.object(lab_container, "exec_status", self.local.status)
        self.capture.start()
        self.status.start()
        self.addCleanup(self.capture.stop)
        self.addCleanup(self.status.stop)

    def git(self, *args: str, cwd: Path | None = None) -> str:
        done = subprocess.run(
            ["git"] + list(args), cwd=str(cwd or self.repo), capture_output=True,
            text=True, check=True,
        )
        return done.stdout.strip()

    def commit(self, name: str) -> str:
        (self.repo / name).write_text(name + "\n")
        self.git("add", name)
        self.git("commit", "-m", name)
        return self.git("rev-parse", "HEAD")

    def sync(self, branch: str, head: str) -> bool:
        return lab_container.sync_clone(self.lab, self.repo, branch, head)

    def sync_main(self) -> str:
        head = self.git("rev-parse", "HEAD")
        self.sync("refs/heads/main", head)
        return head

    def rescue(self, refusal: lab_container.LabError) -> list[str]:
        """Run each command line the refusal prints; return the saved commits."""
        bundle = str(self.parent / "demo.bundle")
        saved = []
        for line in str(refusal).splitlines()[1:]:
            argv = line.replace("/tmp/demo.bundle", bundle).split()
            if argv[:4] == ["scripts/lab", "exec", "demo", "git"]:
                self.git(*argv[4:], cwd=self.clone)
            elif argv[:2] == ["git", "fetch"]:
                self.git(*argv[1:])
                saved.append(self.git("rev-parse", argv[-1].split(":")[1]))
            else:
                self.assertEqual(argv[:2], ["podman", "cp"], line)
        return saved

    def test_recipe_in_skill_matches_the_refusal(self) -> None:
        self.sync_main()
        self.git("checkout", "--detach", cwd=self.clone)
        self.commit_in_clone("lab-only")
        with self.assertRaises(lab_container.LabError) as raised:
            self.sync("refs/heads/main", self.commit("host-next"))

        skill = (Path(__file__).parent.parent / "SKILL.md").read_text()
        recipe = skill.split("## Save commits from a lab")[1].split("```")[1]
        templates = recipe.strip().splitlines()
        printed = str(raised.exception).splitlines()[1:]
        self.assertEqual(len(templates), len(printed))
        for template, line in zip(templates, printed):
            pattern = re.escape(template).replace("NAME", "demo")
            pattern = pattern.replace("REF", "HEAD").replace("SHA", "[0-9a-f]{12}")
            self.assertRegex(line, "^" + pattern + "$")

    def test_allows_a_host_amend_after_the_old_head_becomes_unreachable(self) -> None:
        self.sync_main()
        (self.repo / "initial").write_text("amended\n")
        self.git("add", "initial")
        self.git("commit", "--amend", "-m", "amended")

        self.assertTrue(self.sync("refs/heads/main", self.git("rev-parse", "HEAD")))

    def test_allows_switching_away_from_a_synced_sha(self) -> None:
        self.sync_main()
        self.git("checkout", "-b", "pull-request")
        synced = self.commit("pull-request")
        self.git("update-ref", "refs/pull/1/head", synced)
        self.git("checkout", "main")
        self.git("branch", "-D", "pull-request")
        self.git("fetch", str(self.repo), synced, cwd=self.clone)
        self.sync("origin/pr", synced)
        target = self.commit("main-next")

        self.assertTrue(self.sync("refs/heads/main", target))

    def test_refuses_to_drop_a_commit_on_an_inactive_lab_branch(self) -> None:
        target = self.sync_main()
        self.git("checkout", "-b", "feat", cwd=self.clone)
        (self.clone / "lab-only").write_text("lab-only\n")
        self.git("add", "lab-only", cwd=self.clone)
        self.git("commit", "-m", "lab-only", cwd=self.clone)
        self.git("checkout", "main", cwd=self.clone)

        with self.assertRaisesRegex(lab_container.LabError, "refs/heads/feat"):
            self.sync("refs/heads/feat", target)

    def test_allows_rescued_commit_on_the_target_branch(self) -> None:
        self.sync_main()
        saved = self.commit_in_clone("lab-only")
        target = self.commit("host-next")

        with self.assertRaises(lab_container.LabError) as raised:
            self.sync("refs/heads/main", target)

        self.assertEqual(self.rescue(raised.exception), [saved])
        self.assertTrue(self.sync("refs/heads/main", target))

    def test_allows_target_reset_when_current_branch_keeps_the_commit(self) -> None:
        self.sync_main()
        saved = self.commit_in_clone("lab-only")
        self.git("checkout", "-b", "feat", cwd=self.clone)
        target = self.commit("host-next")

        self.assertTrue(self.sync("refs/heads/main", target))
        self.assertEqual(self.git("rev-parse", "feat", cwd=self.clone), saved)

    def test_allows_two_successive_bundle_rescues(self) -> None:
        self.sync_main()
        on_main = self.commit_in_clone("lab-main")
        self.git("checkout", "--detach", "HEAD~1", cwd=self.clone)
        on_head = self.commit_in_clone("lab-detached")
        target = self.commit("host-next")

        with self.assertRaises(lab_container.LabError) as raised:
            self.sync("refs/heads/main", target)

        self.assertEqual(self.rescue(raised.exception), [on_main, on_head])
        self.assertTrue(self.sync("refs/heads/main", target))

    def test_allows_rescuing_the_same_ref_again_later(self) -> None:
        self.sync_main()
        for name in ("first", "second"):
            self.git("checkout", "--detach", cwd=self.clone)
            saved = self.commit_in_clone("lab-" + name)
            target = self.commit("host-" + name)
            with self.assertRaises(lab_container.LabError) as raised:
                self.sync("refs/heads/main", target)

            self.assertEqual(self.rescue(raised.exception), [saved])
            self.assertTrue(self.sync("refs/heads/main", target))

    def test_prunes_host_refs_when_a_branch_becomes_a_directory(self) -> None:
        self.git("branch", "a")
        self.sync_main()
        self.git("branch", "x")
        self.sync("refs/heads/main", self.commit("next"))
        self.git("branch", "-D", "a")
        self.git("branch", "a/b")

        self.assertTrue(self.sync("refs/heads/main", self.commit("next2")))

    def test_allows_commit_on_a_non_target_branch(self) -> None:
        self.sync_main()
        self.git("checkout", "-b", "feat", cwd=self.clone)
        saved = self.commit_in_clone("lab-only")
        self.git("checkout", "main", cwd=self.clone)
        target = self.commit("host-next")

        self.assertTrue(self.sync("refs/heads/main", target))
        self.assertEqual(self.git("rev-parse", "feat", cwd=self.clone), saved)

    def test_allows_branch_switch_that_preserves_main(self) -> None:
        target = self.sync_main()
        self.git("branch", "other")
        saved = self.commit_in_clone("lab-only")

        self.assertTrue(self.sync("refs/heads/other", target))
        self.assertEqual(self.git("rev-parse", "main", cwd=self.clone), saved)

    def test_refuses_to_drop_a_commit_on_the_target_branch(self) -> None:
        self.git("branch", "feat")
        target = self.git("rev-parse", "feat")
        self.sync("refs/heads/feat", target)
        self.commit_in_clone("lab-only")
        self.git("checkout", "feat")
        target = self.commit("host-next")

        command = (
            "scripts/lab exec demo git bundle create /tmp/demo.bundle "
            "refs/heads/feat"
        )
        with self.assertRaisesRegex(lab_container.LabError, command):
            self.sync("refs/heads/feat", target)

    def test_refuses_to_drop_a_commit_from_detached_head(self) -> None:
        self.sync_main()
        self.git("checkout", "--detach", cwd=self.clone)
        self.commit_in_clone("lab-only")
        target = self.commit("host-next")

        command = "git bundle create /tmp/demo.bundle HEAD"
        with self.assertRaisesRegex(lab_container.LabError, command):
            self.sync("refs/heads/main", target)

    def test_refusal_bundle_command_has_no_trailing_punctuation(self) -> None:
        self.sync_main()
        self.git("checkout", "--detach", cwd=self.clone)
        self.commit_in_clone("lab-only")
        target = self.commit("host-next")

        with self.assertRaises(lab_container.LabError) as raised:
            self.sync("refs/heads/main", target)

        commands = [
            line for line in str(raised.exception).splitlines()
            if "git bundle create" in line
        ]
        self.assertEqual(commands, [
            "scripts/lab exec demo git bundle create /tmp/demo.bundle HEAD"
        ])

    def test_allows_rescued_commit_from_detached_head(self) -> None:
        self.sync_main()
        self.git("checkout", "--detach", cwd=self.clone)
        saved = self.commit_in_clone("lab-only")
        target = self.commit("host-next")

        with self.assertRaises(lab_container.LabError) as raised:
            self.sync("refs/heads/main", target)

        self.assertEqual(self.rescue(raised.exception), [saved])
        self.assertTrue(self.sync("refs/heads/main", target))

    def test_fetches_an_advertised_non_branch_head_before_comparing(self) -> None:
        self.sync_main()
        target = self.commit("pull-request")
        self.git("update-ref", "refs/pull/1/head", target)
        self.git("reset", "--hard", "HEAD^")

        self.assertTrue(self.sync("refs/pull/1/head", target))

    def commit_in_clone(self, name: str) -> str:
        (self.clone / name).write_text(name + "\n")
        self.git("add", name, cwd=self.clone)
        self.git("commit", "-m", name, cwd=self.clone)
        return self.git("rev-parse", "HEAD", cwd=self.clone)


if __name__ == "__main__":
    unittest.main()
