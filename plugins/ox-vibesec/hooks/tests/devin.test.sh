#!/bin/bash
set -euo pipefail

plugin=$(cd "$(dirname "$0")/../.." && pwd)
python3 -B - "$plugin" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

plugin = Path(sys.argv[1])
sys.path.insert(0, str(plugin / "bin"))
import hook
import vibesec

hooks = json.loads((plugin / "hooks.json").read_text())
session = {"session_id": "devin-test"}
assert set(hooks) == {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"}
assert hook.ox_payload("PreToolUse", {
    **session, "tool_name": "edit", "tool_input": {"path": "test.py", "content": "pass"},
}, plugin)["tool_name"] == "Write"
assert hook.ox_payload("PreToolUse", {
    **session, "tool_name": "edit", "tool_input": {"path": "test.py", "patch": "ignored"},
}, plugin) is None

with tempfile.TemporaryDirectory() as temp:
    home = Path(temp)
    env = os.environ.copy()
    env.pop("OX_API_KEY", None)
    env.update(HOME=temp, DEVIN_PLUGIN_ROOT=str(plugin))
    for groups in hooks.values():
        command = groups[0]["hooks"][0]["command"]
        completed = subprocess.run(
            command, shell=True, cwd=home, env=env,
            input=json.dumps(session), capture_output=True, text=True,
        )
        assert completed.returncode == 0, completed.stderr
        assert not completed.stdout and not completed.stderr
    assert not list(home.iterdir())

    installer = b"fake installer"
    digest = hashlib.sha256(installer).hexdigest()
    staged = home / "staged.sh"
    dest = home / "install.sh"
    staged.write_bytes(installer)
    with patch.object(vibesec, "INSTALLER_SHA256", digest):
        with patch.object(vibesec.subprocess, "run") as download:
            assert vibesec.verified_installer(staged, dest, env).read_bytes() == installer
            download.assert_not_called()

        staged.unlink()

        def fetch(args, **kwargs):
            assert args[-1] == vibesec.INSTALLER_URL
            Path(args[args.index("-o") + 1]).write_bytes(installer)

        with patch.object(vibesec.subprocess, "run", side_effect=fetch) as download:
            assert vibesec.verified_installer(staged, dest, env).read_bytes() == installer
            download.assert_called_once()

        staged.write_bytes(b"modified installer")
        with patch.object(vibesec.subprocess, "run") as download:
            try:
                vibesec.verified_installer(staged, dest, env)
            except RuntimeError as error:
                assert str(error) == "OX installer checksum mismatch"
            else:
                raise AssertionError("accepted a modified installer")
            download.assert_not_called()

print("PASS  ox-vibesec: plugin-relative hooks, no-secret startup, edit mapping, staged/downloaded installer verification")
PY
