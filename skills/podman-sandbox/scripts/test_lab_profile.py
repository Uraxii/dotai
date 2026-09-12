"""Tests for profile discovery, manifest parsing, and directory hashing.

These need no podman. Everything podman does is proved by running `lab`
against real podman, not simulated here.
"""

from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lab_profile

RECIPE = "FROM debian:13-slim\n"


def write_profile(parent: Path, name: str, recipe: str = RECIPE) -> Path:
    """Create a minimal profile directory and return it."""
    directory = parent / name
    directory.mkdir(parents=True)
    (directory / "Containerfile").write_text(recipe, encoding="utf-8")
    return directory


class HashDirectoryTest(unittest.TestCase):
    """`hash_directory` is the whole converge check, so it is tested first."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def test_same_content_hashes_the_same(self) -> None:
        first = write_profile(self.root, "first")
        second = write_profile(self.root, "second")
        self.assertEqual(
            lab_profile.hash_directory(first),
            lab_profile.hash_directory(second),
        )

    def test_changed_content_changes_the_hash(self) -> None:
        directory = write_profile(self.root, "edited")
        before = lab_profile.hash_directory(directory)
        (directory / "Containerfile").write_text("FROM debian:13\n")
        self.assertNotEqual(before, lab_profile.hash_directory(directory))

    def test_owner_execute_bit_changes_the_hash(self) -> None:
        directory = write_profile(self.root, "hooked")
        hook = directory / "setup"
        hook.write_text("#!/bin/sh\n", encoding="utf-8")
        hook.chmod(0o644)
        without = lab_profile.hash_directory(directory)
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
        self.assertNotEqual(without, lab_profile.hash_directory(directory))

    def test_hash_ignores_the_order_files_were_created(self) -> None:
        forwards = self.root / "forwards"
        backwards = self.root / "backwards"
        names = ["Containerfile", "alpha.txt", "zulu.txt"]
        for directory, order in ((forwards, names), (backwards, names[::-1])):
            directory.mkdir()
            for name in order:
                (directory / name).write_text(name, encoding="utf-8")
        self.assertEqual(
            lab_profile.hash_directory(forwards),
            lab_profile.hash_directory(backwards),
        )

    def test_a_nested_file_reaches_the_hash(self) -> None:
        directory = write_profile(self.root, "nested")
        before = lab_profile.hash_directory(directory)
        (directory / "assets").mkdir()
        (directory / "assets" / "icon.txt").write_text("x", encoding="utf-8")
        self.assertNotEqual(before, lab_profile.hash_directory(directory))


class ParseManifestTest(unittest.TestCase):
    """profile.json is the one untyped boundary, so every shape is checked."""

    def test_empty_text_means_every_default(self) -> None:
        self.assertEqual(
            lab_profile.parse_manifest(""),
            {
                "port": None,
                "setup": (),
                "ready": (),
                "ready_timeout_sec": lab_profile.DEFAULT_READY_TIMEOUT_SEC,
            },
        )

    def test_whitespace_only_file_means_every_default(self) -> None:
        self.assertEqual(
            lab_profile.parse_manifest("  \n\t\n"),
            lab_profile.parse_manifest(""),
        )

    def test_every_key_is_read(self) -> None:
        text = (
            '{"port": 6551, "setup": ["/s"], "ready": ["/r", "--now"],'
            ' "ready_timeout_sec": 42}'
        )
        self.assertEqual(
            lab_profile.parse_manifest(text),
            {
                "port": 6551,
                "setup": ("/s",),
                "ready": ("/r", "--now"),
                "ready_timeout_sec": 42,
            },
        )

    def test_malformed_json_is_rejected(self) -> None:
        with self.assertRaises(lab_profile.ProfileError):
            lab_profile.parse_manifest('{"port": 6551,}')

    def test_a_json_list_is_rejected(self) -> None:
        with self.assertRaises(lab_profile.ProfileError):
            lab_profile.parse_manifest("[1, 2]")

    def test_an_unknown_key_is_rejected(self) -> None:
        with self.assertRaises(lab_profile.ProfileError) as caught:
            lab_profile.parse_manifest('{"prt": 6551}')
        self.assertIn("prt", str(caught.exception))

    def test_a_wrong_type_is_rejected_for_each_key(self) -> None:
        wrong = [
            '{"port": "6551"}',
            '{"port": true}',
            '{"ready_timeout_sec": 1.5}',
            '{"setup": "/s"}',
            '{"ready": {"cmd": "/r"}}',
            '{"setup": ["/s", 7]}',
            '{"ready": [""]}',
        ]
        for text in wrong:
            with self.subTest(text=text):
                with self.assertRaises(lab_profile.ProfileError):
                    lab_profile.parse_manifest(text)


class LoadTest(unittest.TestCase):
    """Discovery takes the first match, nearest the project."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.repo = self.root / "repo"
        self.user = self.root / "user"
        self.builtin = self.root / "builtin"
        self.user.mkdir()
        self.builtin.mkdir()
        self.project = self.repo / lab_profile.PROJECT_PROFILES_SUBPATH
        patches = mock.patch.multiple(
            lab_profile,
            USER_PROFILES_DIR=self.user,
            BUILTIN_PROFILES_DIR=self.builtin,
        )
        patches.start()
        self.addCleanup(patches.stop)

    def test_search_path_runs_project_then_user_then_builtin(self) -> None:
        self.assertEqual(
            lab_profile.search_path(self.repo),
            (self.project, self.user, self.builtin),
        )

    def test_the_project_profile_wins(self) -> None:
        for parent in (self.project, self.user, self.builtin):
            write_profile(parent, "demo", f"FROM {parent.name}\n")
        self.assertEqual(
            lab_profile.load("demo", self.repo).directory,
            self.project / "demo",
        )

    def test_the_user_profile_beats_the_builtin_one(self) -> None:
        for parent in (self.user, self.builtin):
            write_profile(parent, "demo")
        self.assertEqual(
            lab_profile.load("demo", self.repo).directory, self.user / "demo"
        )

    def test_the_builtin_profile_is_the_last_resort(self) -> None:
        write_profile(self.builtin, "demo")
        self.assertEqual(
            lab_profile.load("demo", self.repo).directory,
            self.builtin / "demo",
        )

    def test_a_directory_holding_only_a_containerfile_is_complete(
        self,
    ) -> None:
        write_profile(self.builtin, "bare")
        profile = lab_profile.load("bare", self.repo)
        self.assertEqual(profile.port, None)
        self.assertEqual(profile.setup, ())
        self.assertEqual(profile.image, "podman-sandbox/bare:latest")

    def test_a_missing_profile_names_what_exists(self) -> None:
        write_profile(self.builtin, "base")
        with self.assertRaises(lab_profile.ProfileError) as caught:
            lab_profile.load("absent", self.repo)
        self.assertIn("base", str(caught.exception))

    def test_a_directory_without_a_containerfile_is_rejected(self) -> None:
        (self.builtin / "empty").mkdir()
        with self.assertRaises(lab_profile.ProfileError):
            lab_profile.load("empty", self.repo)

    def test_a_broken_manifest_names_its_own_path(self) -> None:
        directory = write_profile(self.builtin, "broken")
        (directory / "profile.json").write_text("{", encoding="utf-8")
        with self.assertRaises(lab_profile.ProfileError) as caught:
            lab_profile.load("broken", self.repo)
        self.assertIn("profile.json", str(caught.exception))

    def test_available_lists_every_profile_once(self) -> None:
        write_profile(self.user, "shared")
        write_profile(self.builtin, "shared")
        write_profile(self.builtin, "base")
        self.assertEqual(
            lab_profile.available(self.repo), ("shared", "base")
        )


if __name__ == "__main__":
    unittest.main()
