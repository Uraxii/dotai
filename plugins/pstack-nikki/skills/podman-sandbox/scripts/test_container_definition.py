"""Tests for the repository's container definition: discovery, hooks, hashing.

These need no podman. Everything podman does is proved by running `lab`
against real podman, not simulated here.
"""

from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

import lab_container

RECIPE = "FROM debian:13-slim\n"


def write_definition(repo: Path, recipe: str = RECIPE) -> Path:
    """Create `<repo>/.sandbox-container` holding a Containerfile."""
    directory = repo / lab_container.DEFINITION_SUBPATH
    directory.mkdir(parents=True)
    (directory / "Containerfile").write_text(recipe, encoding="utf-8")
    return directory


class LoadDefinitionTest(unittest.TestCase):
    """One fixed directory in the repository, no search and no fallback."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.repo = self.root / "myrepo"
        self.repo.mkdir()

    def test_the_definition_is_read_from_the_repository(self) -> None:
        directory = write_definition(self.repo)

        definition = lab_container.load_definition(self.repo)

        self.assertEqual(definition.directory, directory)

    def test_a_repository_without_the_directory_names_the_path(self) -> None:
        with self.assertRaises(lab_container.LabError) as caught:
            lab_container.load_definition(self.repo)

        self.assertEqual(
            str(caught.exception).splitlines(),
            [
                f"no container definition at {self.repo}/.sandbox-container",
                "create that directory and write a Containerfile in it. "
                "Executables named setup and ready beside it are optional",
            ],
        )

    def test_a_directory_without_a_containerfile_names_the_path(self) -> None:
        directory = self.repo / lab_container.DEFINITION_SUBPATH
        directory.mkdir()

        with self.assertRaises(lab_container.LabError) as caught:
            lab_container.load_definition(self.repo)

        self.assertEqual(
            str(caught.exception).splitlines(),
            [
                f"no Containerfile in {directory}",
                "write one there. Executables named setup and ready beside "
                "it are optional",
            ],
        )

    def test_a_bare_containerfile_leaves_both_hooks_empty(self) -> None:
        write_definition(self.repo)

        definition = lab_container.load_definition(self.repo)

        self.assertEqual(definition.setup_command, ())
        self.assertEqual(definition.ready_command, ())

    def test_the_hooks_are_found_by_name_and_run_from_the_mount(self) -> None:
        directory = write_definition(self.repo)
        for name in ("setup", "ready"):
            hook = directory / name
            hook.write_text("#!/bin/sh\n", encoding="utf-8")
            hook.chmod(0o755)

        definition = lab_container.load_definition(self.repo)

        self.assertEqual(
            definition.setup_command,
            ("/src-ro/.sandbox-container/setup",),
        )
        self.assertEqual(
            definition.ready_command,
            ("/src-ro/.sandbox-container/ready",),
        )

    def test_the_image_tag_names_the_directory_and_the_recipe(self) -> None:
        write_definition(self.repo)

        definition = lab_container.load_definition(self.repo)

        self.assertEqual(
            definition.image,
            f"podman-sandbox/myrepo-{definition.recipe_sha256[:12]}:latest",
        )

    def test_an_illegal_character_in_the_directory_name_is_replaced(self) -> None:
        repo = self.root / "My Repo+2"
        repo.mkdir()
        write_definition(repo)

        definition = lab_container.load_definition(repo)

        self.assertTrue(
            definition.image.startswith("podman-sandbox/my-repo-2-"),
            definition.image,
        )

    def test_two_repositories_of_one_name_get_different_image_tags(self) -> None:
        images = []
        for parent, recipe in (("left", RECIPE), ("right", "FROM debian:13\n")):
            repo = self.root / parent / "myrepo"
            repo.mkdir(parents=True)
            write_definition(repo, recipe)
            images.append(lab_container.load_definition(repo).image)

        self.assertNotEqual(images[0], images[1])

    def test_a_directory_name_of_separators_falls_back_to_a_stem(self) -> None:
        repo = self.root / "-.-"
        repo.mkdir()
        write_definition(repo)

        definition = lab_container.load_definition(repo)

        self.assertTrue(
            definition.image.startswith("podman-sandbox/repo-"),
            definition.image,
        )


class HashDirectoryTest(unittest.TestCase):
    """`hash_directory` is the whole converge check, so it is tested first."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def write(self, name: str, recipe: str = RECIPE) -> Path:
        repo = self.root / name
        repo.mkdir()
        return write_definition(repo, recipe)

    def test_same_content_hashes_the_same(self) -> None:
        self.assertEqual(
            lab_container.hash_directory(self.write("first")),
            lab_container.hash_directory(self.write("second")),
        )

    def test_changed_content_changes_the_hash(self) -> None:
        directory = self.write("edited")
        before = lab_container.hash_directory(directory)
        (directory / "Containerfile").write_text("FROM debian:13\n")
        self.assertNotEqual(before, lab_container.hash_directory(directory))

    def test_owner_execute_bit_changes_the_hash(self) -> None:
        directory = self.write("hooked")
        hook = directory / "setup"
        hook.write_text("#!/bin/sh\n", encoding="utf-8")
        hook.chmod(0o644)
        without = lab_container.hash_directory(directory)
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
        self.assertNotEqual(without, lab_container.hash_directory(directory))

    def test_hash_ignores_the_order_files_were_created(self) -> None:
        names = ["Containerfile", "alpha.txt", "zulu.txt"]
        digests = []
        for repo, order in (("forwards", names), ("backwards", names[::-1])):
            directory = self.root / repo / lab_container.DEFINITION_SUBPATH
            directory.mkdir(parents=True)
            for name in order:
                (directory / name).write_text(name, encoding="utf-8")
            digests.append(lab_container.hash_directory(directory))
        self.assertEqual(digests[0], digests[1])

    def test_a_nested_file_reaches_the_hash(self) -> None:
        directory = self.write("nested")
        before = lab_container.hash_directory(directory)
        (directory / "assets").mkdir()
        (directory / "assets" / "icon.txt").write_text("x", encoding="utf-8")
        self.assertNotEqual(before, lab_container.hash_directory(directory))


if __name__ == "__main__":
    unittest.main()
