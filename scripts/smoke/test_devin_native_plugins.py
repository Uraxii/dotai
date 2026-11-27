import os
from pathlib import Path
import unittest

from support import DONE, SmokeTestCase, cli


class DevinNativePluginsTest(SmokeTestCase):
    harness = "devin"

    def setUp(self):
        self.credentials = os.getenv("DEVIN_SMOKE_CREDENTIALS_FILE")
        if not self.credentials:
            self.skipTest("Set DEVIN_SMOKE_CREDENTIALS_FILE to enable authenticated smoke")
        super().setUp()
        if not self.plugins:
            self.skipTest("No native smoke plugins in this checkout")

    def test_loads_native_plugins_in_headless_session(self):
        data_home = self.home / ".local/share"
        dest = data_home / "devin/credentials.toml"
        dest.parent.mkdir(parents=True, mode=0o700)
        with open(dest, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as target:
            target.write(Path(self.credentials).read_bytes())
        self.env["XDG_DATA_HOME"] = str(data_home)
        cli(["devin", "auth", "--process-model", "in-process", "status"], self.env, self.cwd, private=True)
        for plugin in self.plugins.values():
            cli(["devin", "plugins", "install", "--local", "--yes", "--process-model", "in-process", str(plugin)],
                self.env, self.cwd, private=True)
        loaded = cli(["devin", "plugins", "list"], self.env, self.cwd, private=True)
        for name in self.plugins:
            self.assertTrue(name in loaded, f"Native plugin {name} is not in the isolated install list")
        output = cli(["devin", "--process-model", "in-process", "--respect-workspace-trust", "false",
                      "-p", f"Do not use tools. Reply with exactly {DONE}."],
                     self.env, self.cwd, private=True, timeout=120)
        self.assertTrue(DONE in output, "Authenticated headless prompt did not return the smoke marker")


if __name__ == "__main__":
    unittest.main()
