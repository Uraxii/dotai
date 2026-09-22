from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPOSITORY_ROOT / "scripts" / "generate-plugin-manifests.py"
PLUGIN_NAMES = {
    "artifact",
    "azure",
    "bd",
    "cbm",
    "llm-wiki",
    "mpocock",
    "notion",
    "proton",
    "pstack",
    "sandbox",
    "skills",
}


def run_generator(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GENERATOR), *arguments],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def generated_paths() -> list[Path]:
    paths = [
        REPOSITORY_ROOT / ".claude-plugin" / "marketplace.json",
        REPOSITORY_ROOT / ".agents" / "plugins" / "marketplace.json",
    ]
    for name in sorted(PLUGIN_NAMES):
        plugin_root = REPOSITORY_ROOT / "plugins" / name
        paths.append(plugin_root / "plugin.json")
        paths.append(plugin_root / ".claude-plugin" / "plugin.json")
        paths.append(plugin_root / ".codex-plugin" / "plugin.json")
    return paths


def snapshot() -> dict[Path, str]:
    return {path: path.read_text() for path in generated_paths()}


class GeneratorOutputTest(unittest.TestCase):
    def test_every_plugin_has_all_three_manifests(self) -> None:
        self.assertEqual(run_generator().returncode, 0)
        for name in sorted(PLUGIN_NAMES):
            plugin_root = REPOSITORY_ROOT / "plugins" / name
            for relative in (
                "plugin.json",
                ".claude-plugin/plugin.json",
                ".codex-plugin/plugin.json",
            ):
                with self.subTest(plugin=name, manifest=relative):
                    manifest = json.loads((plugin_root / relative).read_text())
                    self.assertEqual(manifest["name"], name)
                    self.assertTrue(manifest["version"])

    def test_both_marketplaces_list_every_plugin(self) -> None:
        self.assertEqual(run_generator().returncode, 0)
        for relative in (
            ".claude-plugin/marketplace.json",
            ".agents/plugins/marketplace.json",
        ):
            with self.subTest(marketplace=relative):
                document = json.loads((REPOSITORY_ROOT / relative).read_text())
                listed = {entry["name"] for entry in document["plugins"]}
                self.assertEqual(listed, PLUGIN_NAMES)

    def test_only_pstack_declares_hooks(self) -> None:
        self.assertEqual(run_generator().returncode, 0)
        for name in sorted(PLUGIN_NAMES):
            plugin_root = REPOSITORY_ROOT / "plugins" / name
            manifest = json.loads(
                (plugin_root / ".codex-plugin" / "plugin.json").read_text()
            )
            with self.subTest(plugin=name):
                if name == "pstack":
                    self.assertEqual(manifest["hooks"], "./hooks/codex-hooks.json")
                    self.assertTrue((plugin_root / "hooks/codex-hooks.json").is_file())
                    self.assertIn("Hooks", manifest["interface"]["capabilities"])
                else:
                    self.assertNotIn("hooks", manifest)
                    self.assertNotIn("Hooks", manifest["interface"]["capabilities"])

    def test_agents_marketplace_source_path_is_per_plugin(self) -> None:
        self.assertEqual(run_generator().returncode, 0)
        document = json.loads(
            (REPOSITORY_ROOT / ".agents/plugins/marketplace.json").read_text()
        )
        for entry in document["plugins"]:
            with self.subTest(plugin=entry["name"]):
                self.assertEqual(
                    entry["source"]["path"], f"plugins/{entry['name']}"
                )
                self.assertEqual(entry["source"]["ref"], "main")


class GeneratorRerunTest(unittest.TestCase):
    def test_second_run_changes_nothing(self) -> None:
        self.assertEqual(run_generator().returncode, 0)
        before = snapshot()
        self.assertEqual(run_generator().returncode, 0)
        self.assertEqual(snapshot(), before)

    def test_check_passes_on_generated_tree(self) -> None:
        self.assertEqual(run_generator().returncode, 0)
        result = run_generator("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_check_fails_after_a_hand_edit(self) -> None:
        self.assertEqual(run_generator().returncode, 0)
        edited = REPOSITORY_ROOT / "plugins" / "bd" / "plugin.json"
        original = edited.read_text()
        try:
            edited.write_text(original.replace('"bd"', '"bd-by-hand"'))
            result = run_generator("--check")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("plugins/bd/plugin.json", result.stdout)
        finally:
            edited.write_text(original)
            self.assertEqual(run_generator("--check").returncode, 0)


if __name__ == "__main__":
    unittest.main()
