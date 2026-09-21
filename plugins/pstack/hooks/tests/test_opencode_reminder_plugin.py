"""Static checks for the opencode plugin shim.

opencode plugins run under Bun; nothing on this machine installs opencode or
Bun (see /home/nikki/dotai's dev-machine rules), so this cannot be exercised
live. `node --experimental-strip-types` type-strips and loads the file the
same way Bun would, without executing any hook body (the file only defines
and exports the plugin, it never calls it), so a clean exit proves the
syntax and the type-only import are both valid. Skips instead of failing
where `node` itself is absent, matching this repo's LIVE-UNVERIFIED stance
for harnesses that cannot be installed.
"""

import shutil
import subprocess
import unittest
from pathlib import Path

PLUGIN_PATH = Path(__file__).resolve().parents[1] / "opencode-reminder-plugin.ts"
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node not on PATH; cannot run the static load check")
class OpencodeReminderPluginTests(unittest.TestCase):
    def test_loads_cleanly_under_node_type_stripping(self) -> None:
        result = subprocess.run(
            [NODE, "--experimental-strip-types", str(PLUGIN_PATH)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(0, result.returncode, result.stderr)

    def test_shells_out_to_session_start_context_with_opencode_harness(self) -> None:
        source = PLUGIN_PATH.read_text()

        self.assertIn("session_start_context.py", source)
        self.assertIn("--harness opencode", source)
        self.assertIn("experimental.chat.system.transform", source)


if __name__ == "__main__":
    unittest.main()
