import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PLUGIN = ROOT / 'plugins/pstack'
HOOK = PLUGIN / 'hooks/session_start_context.py'
SPEC = importlib.util.spec_from_file_location(
    'manifests', ROOT / 'scripts/generate-plugin-manifests.py'
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class SessionReminderTests(unittest.TestCase):
    def run_hook(self, target: str) -> str:
        result = subprocess.run(
            [sys.executable, str(HOOK), '--harness', target,
             '--event', 'SessionStart'],
            input='{}', text=True, capture_output=True, check=True,
        )
        self.assertEqual('', result.stderr)
        return result.stdout.strip()

    def test_target_context_contracts(self) -> None:
        plain = self.run_hook('claude')
        self.assertIn('You have poteto-mode.', plain)
        self.assertIn('load the `poteto-mode` skill', plain)
        self.assertEqual(
            {'hookSpecificOutput': {
                'hookEventName': 'SessionStart', 'additionalContext': plain,
            }}, json.loads(self.run_hook('codex')),
        )
        self.assertEqual(
            {'additionalContext': plain}, json.loads(self.run_hook('copilot')),
        )

    def test_wired_commands_deliver_context(self) -> None:
        for target, filename, variable in (
            ('claude', 'hooks/claude-hooks.json', 'CLAUDE_PLUGIN_ROOT'),
            ('codex', 'hooks/codex-hooks.json', 'PLUGIN_ROOT'),
            ('copilot', 'hooks.json', 'PLUGIN_ROOT'),
        ):
            with self.subTest(target=target):
                config = json.loads((PLUGIN / filename).read_text())
                event = 'sessionStart' if target == 'copilot' else 'SessionStart'
                self.assertEqual({event}, set(config['hooks']))
                entry = config['hooks'][event][0]
                command = entry['bash'] if target == 'copilot' else entry['hooks'][0]['command']
                result = subprocess.run(
                    command, shell=True, text=True, capture_output=True,
                    env={**os.environ, variable: str(PLUGIN)},
                    input='{}', check=True,
                )
                self.assertEqual(self.run_hook(target), result.stdout.strip())


class ManifestDriftTests(unittest.TestCase):
    def test_declared_wiring_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(ROOT / 'README.md', root / 'README.md')
            GENERATOR.main([], root=root)
            self.assertEqual(2, GENERATOR.main(['--check'], root=root))
            for plugin in GENERATOR.PLUGINS:
                for target in plugin.get('hooks', []):
                    path = root / 'plugins' / plugin['name'] / GENERATOR.HOOK_WIRING_PATHS[target]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    source = ROOT / path.relative_to(root)
                    shutil.copyfile(source, path)
            self.assertEqual(0, GENERATOR.main(['--check'], root=root))
            self.assertEqual([], GENERATOR.write(GENERATOR.wanted_files(root), root))
            manifest = root / 'plugins/pstack/plugin.json'
            manifest.write_text('{}\n')
            self.assertEqual(2, GENERATOR.main(['--check'], root=root))
            GENERATOR.main([], root=root)
            (root / 'plugins/pstack/hooks.json').unlink()
            self.assertEqual(2, GENERATOR.main(['--check'], root=root))


if __name__ == '__main__':
    unittest.main()
