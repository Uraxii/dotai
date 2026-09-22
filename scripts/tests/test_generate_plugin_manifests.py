"""Check the generator against a copy of the tree, never the tree itself.

Write mode used to run against the checkout the script lives in, so running
this file rewrote all 36 generated files, `README.md` among them, and threw
away whatever the person running it had not committed. Every test here
generates into a temporary directory instead, and `setUpModule` records the
working tree so `tearDownModule` fails if anything in this file writes to it.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPOSITORY_ROOT / "scripts" / "generate-plugin-manifests.py"
MANIFEST_NAMES = (
    "plugin.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
)


def load_generator():
    specification = importlib.util.spec_from_file_location(
        "generate_plugin_manifests", GENERATOR
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


generator = load_generator()
PLUGIN_NAMES = {str(plugin["name"]) for plugin in generator.PLUGINS}


def working_tree_state() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


WORKING_TREE_BEFORE = ""


def setUpModule() -> None:
    global WORKING_TREE_BEFORE
    WORKING_TREE_BEFORE = working_tree_state()


def tearDownModule() -> None:
    after = working_tree_state()
    if after == WORKING_TREE_BEFORE:
        return
    raise AssertionError(
        "a test in this file wrote into the real checkout at "
        f"{REPOSITORY_ROOT}. `git status --porcelain` changed while this "
        "module ran, from:\n"
        f"{WORKING_TREE_BEFORE or '(clean)'}\nto:\n{after or '(clean)'}\n"
        "Generate into a temporary directory: pass `root=` to the "
        "generator's `main`, never the repository root."
    )


@dataclass(frozen=True)
class GeneratorRun:
    """What one in-process `main` call returned and printed."""

    returncode: int
    stdout: str


def run_generator(root: Path, *arguments: str) -> GeneratorRun:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        returncode = generator.main(list(arguments), root=root)
    return GeneratorRun(returncode, captured.getvalue())


def generation_root(case: unittest.TestCase) -> Path:
    """A throwaway tree holding the one file the generator reads back."""
    root = Path(case.enterContext(tempfile.TemporaryDirectory()))
    (root / "README.md").write_text((REPOSITORY_ROOT / "README.md").read_text())
    return root


def generated_paths(root: Path) -> list[Path]:
    paths = [
        root / ".claude-plugin" / "marketplace.json",
        root / ".agents" / "plugins" / "marketplace.json",
        root / "README.md",
    ]
    for name in sorted(PLUGIN_NAMES):
        for relative in MANIFEST_NAMES:
            paths.append(root / "plugins" / name / relative)
    return paths


def snapshot(root: Path) -> dict[Path, str]:
    return {path: path.read_text() for path in generated_paths(root)}


class GeneratorOutputTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = generation_root(self)
        self.assertEqual(run_generator(self.root).returncode, 0)

    def test_every_plugin_has_all_three_manifests(self) -> None:
        for name in sorted(PLUGIN_NAMES):
            plugin_root = self.root / "plugins" / name
            for relative in MANIFEST_NAMES:
                with self.subTest(plugin=name, manifest=relative):
                    manifest = json.loads((plugin_root / relative).read_text())
                    self.assertEqual(manifest["name"], name)
                    self.assertTrue(manifest["version"])

    def test_both_marketplaces_list_every_plugin(self) -> None:
        for relative in (
            ".claude-plugin/marketplace.json",
            ".agents/plugins/marketplace.json",
        ):
            with self.subTest(marketplace=relative):
                document = json.loads((self.root / relative).read_text())
                listed = {entry["name"] for entry in document["plugins"]}
                self.assertEqual(listed, PLUGIN_NAMES)

    def test_only_pstack_declares_hooks(self) -> None:
        for name in sorted(PLUGIN_NAMES):
            manifest = json.loads(
                (
                    self.root / "plugins" / name / ".codex-plugin" / "plugin.json"
                ).read_text()
            )
            with self.subTest(plugin=name):
                if name == "pstack":
                    self.assertEqual(manifest["hooks"], "./hooks/codex-hooks.json")
                    self.assertTrue(
                        (
                            REPOSITORY_ROOT / "plugins/pstack/hooks/codex-hooks.json"
                        ).is_file()
                    )
                    self.assertIn("Hooks", manifest["interface"]["capabilities"])
                else:
                    self.assertNotIn("hooks", manifest)
                    self.assertNotIn("Hooks", manifest["interface"]["capabilities"])

    def test_agents_marketplace_source_path_is_per_plugin(self) -> None:
        document = json.loads(
            (self.root / ".agents/plugins/marketplace.json").read_text()
        )
        for entry in document["plugins"]:
            with self.subTest(plugin=entry["name"]):
                self.assertEqual(
                    entry["source"]["path"], f"plugins/{entry['name']}"
                )
                self.assertEqual(entry["source"]["ref"], "main")


class GeneratorRerunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = generation_root(self)
        self.assertEqual(run_generator(self.root).returncode, 0)

    def test_second_run_changes_nothing(self) -> None:
        before = snapshot(self.root)
        self.assertEqual(run_generator(self.root).returncode, 0)
        self.assertEqual(snapshot(self.root), before)

    def test_check_passes_on_generated_tree(self) -> None:
        result = run_generator(self.root, "--check")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_check_fails_after_a_hand_edit(self) -> None:
        edited = self.root / "plugins" / "bd" / "plugin.json"
        edited.write_text(edited.read_text().replace('"bd"', '"bd-by-hand"'))
        result = run_generator(self.root, "--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugins/bd/plugin.json", result.stdout)


if __name__ == "__main__":
    unittest.main()
