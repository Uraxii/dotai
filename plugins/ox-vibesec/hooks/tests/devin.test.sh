#!/bin/bash
set -euo pipefail

plugin=$(cd "$(dirname "$0")/../.." && pwd)
python3 -B - "$plugin" <<'PY'
from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch

plugin = Path(sys.argv[1])
sys.path.insert(0, str(plugin / "bin"))
import hook
import vibesec

manifest = json.loads((plugin / ".devin-plugin/plugin.json").read_text())
assert manifest["skills"] == []
assert (plugin / "skills/update/SKILL.md").is_file()
print("PASS  ox-vibesec: Devin disables skill loading; Claude updater remains bundled")

hooks = json.loads((plugin / "hooks.json").read_text())
session = {"session_id": "devin-test"}
assert set(hooks) == {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"}
assert hook.ox_payload("PreToolUse", {
    **session, "tool_name": "edit", "tool_input": {"path": "test.py", "content": "pass"},
}, plugin)["tool_name"] == "Write"
assert hook.ox_payload("PreToolUse", {
    **session, "tool_name": "edit", "tool_input": {"path": "test.py", "patch": "ignored"},
}, plugin) is None
assert hook.ox_payload("PreToolUse", {
    **session, "tool_name": "edit",
    "tool_input": {"path": "test.py", "old_string": "before", "new_string": "after"},
}, plugin)["tool_input"] == {"file_path": "test.py", "old_string": "before", "new_string": "after"}

test_key = "test-vibesec-secret"
exec_event = {**session, "tool_name": "exec", "tool_input": {"command": "true"}}


def adapter_call(event, payload, result):
    stdout, stderr = StringIO(), StringIO()
    with (
        patch.dict(os.environ, {"OX_VIBESEC_API_KEY": test_key, "DEVIN_PROJECT_DIR": str(plugin)}),
        patch.object(sys, "argv", ["hook.py", event]),
        patch.object(sys, "stdin", StringIO(json.dumps(payload))),
        patch.object(vibesec.Runtime, "run", return_value=result) as runtime,
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        code = hook.run()
    return code, stdout.getvalue(), stderr.getvalue(), runtime


def vendor_reply(output):
    return Mock(returncode=0, stdout=json.dumps({"hookSpecificOutput": output}))


code, stdout, stderr, runtime = adapter_call("PreToolUse", exec_event, vendor_reply({
    "permissionDecision": "deny", "permissionDecisionReason": f"Blocked {test_key}",
}))
assert code == 0 and not stderr
assert json.loads(stdout) == {"decision": "block", "reason": "Blocked [redacted]"}
runtime.assert_called_once_with({
    "hook_event_name": "PreToolUse", "session_id": session["session_id"], "cwd": str(plugin),
    "tool_name": "Bash", "tool_input": {"command": "true"},
}, plugin, test_key, initialize=False)

code, stdout, stderr, _ = adapter_call("PreToolUse", exec_event, Mock(returncode=2))
assert code == 2 and not stdout and stderr == "OX VibeSec blocked this action.\n"

post_event = {**exec_event, "tool_response": {"success": True, "output": "out", "error": "err"}}
context = {"hookEventName": "PostToolUse", "additionalContext": f"Guidance {test_key}"}
code, stdout, stderr, runtime = adapter_call("PostToolUse", post_event, vendor_reply(context))
assert code == 0 and not stderr
assert json.loads(stdout) == {"hookSpecificOutput": {
    "hookEventName": "PostToolUse", "additionalContext": "Guidance [redacted]",
}}
assert runtime.call_args.args[0]["tool_response"] == {"success": True, "stdout": "out", "stderr": "err"}
code, stdout, stderr, _ = adapter_call("PreToolUse", exec_event, vendor_reply(context))
assert code == 0 and not stdout and not stderr

code, stdout, stderr, runtime = adapter_call("PreToolUse", {**exec_event, "session_id": "../bad"}, None)
assert code == 0 and not stdout and not stderr
runtime.assert_not_called()
print("PASS  ox-vibesec: block decisions, key redaction, exec and edit mapping, PostToolUse, invalid session rejection")

with tempfile.TemporaryDirectory() as temp:
    home = Path(temp)
    env = os.environ.copy()
    env.pop("OX_VIBESEC_API_KEY", None)
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

    for variable in ("DEVIN_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT"):
        env.pop(variable, None)
    command = hooks["SessionStart"][0]["hooks"][0]["command"].replace(
        "/opt/.devin/plugins_cache/cache/", '"$HOME/cache/"',
    )
    missing = subprocess.run(command, shell=True, cwd=home, env=env, capture_output=True, text=True)
    assert missing.returncode == 1
    assert missing.stderr == "ox-vibesec: plugin root not found\n"

    cache = home / "cache/github.com_Uraxii_dotai_plugins_ox-vibesec-test"
    for revision, timestamp in (("zz-old", 1), ("aa-new", 2)):
        script = cache / revision / "bin/hook.py"
        script.parent.mkdir(parents=True)
        script.write_text(f"print({revision!r})\n")
        os.utime(script, (timestamp, timestamp))
    newest = subprocess.run(command, shell=True, cwd=home, env=env, capture_output=True, text=True)
    assert newest.returncode == 0 and newest.stdout == "aa-new\n" and not newest.stderr
    print("PASS  ox-vibesec: cache fallback chooses the newest hook and reports a missing root")

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

    with patch.dict(os.environ, {"HTTPS_PROXY": "HTTP://LOCALHOST:3128"}, clear=True):
        runtime = vibesec.Runtime(home / "runtime", staged)
    assert runtime.proxy_args == ["--proxy", "http://LOCALHOST:3128"]
    print("PASS  ox-vibesec: lowercases only the forwarded proxy scheme")
    with (
        patch.object(runtime, "installed", return_value=["sh", vibesec.LAUNCHER]),
        patch.object(vibesec.subprocess, "run") as run,
    ):
        runtime.run({}, home, "test-token")
        assert run.call_args.kwargs["env"]["NODE_USE_ENV_PROXY"] == "1"
    print("PASS  ox-vibesec: hook subprocess enables the environment for an unauthenticated proxy")

    proxy = "http://test-user:test-password@localhost:3128"
    with patch.dict(os.environ, {"HTTPS_PROXY": proxy}, clear=True):
        runtime = vibesec.Runtime(home / "runtime", staged)
    launcher = ["sh", vibesec.LAUNCHER]
    with (
        patch.object(vibesec, "verified_installer", return_value=dest),
        patch.object(runtime, "installed", side_effect=[None, launcher]),
        patch.object(vibesec.subprocess, "run", return_value=Mock(returncode=0)) as run,
    ):
        assert runtime.start("test-token") == launcher
        args, kwargs = run.call_args
        assert "--proxy" not in args[0] and all(proxy not in arg for arg in args[0])
        assert kwargs["env"]["HTTPS_PROXY"] == proxy
        assert kwargs["env"]["NODE_USE_ENV_PROXY"] == "1"
        assert kwargs["input"] == "test-token\n"

    proxy_with_bracket = "http://test-user:test[password@localhost:3128"
    with patch.dict(os.environ, {"HTTPS_PROXY": proxy_with_bracket}, clear=True):
        runtime = vibesec.Runtime(home / "runtime", staged)
    assert runtime.proxy_args == []
    assert runtime.env["HTTPS_PROXY"] == proxy_with_bracket
    assert runtime.env["NODE_USE_ENV_PROXY"] == "1"
    print("PASS  ox-vibesec: proxy passwords with brackets reach the Node environment fallback")

    lint = plugin.parents[1] / "scripts/lint-hook-references.sh"
    bare = home / "plugins/bare"
    bare.mkdir(parents=True)
    (bare / "hooks.json").write_text(json.dumps({"SessionStart": [{"hooks": [
        {"type": "command", "command": 'echo "${DEVIN_PLUGIN_ROOT}"'},
    ]}]}))
    wrapped = home / "plugins/wrapped"
    (wrapped / ".devin-plugin").mkdir(parents=True)
    (wrapped / ".devin-plugin/plugin.json").write_text("{}")
    (wrapped / "hooks.json").write_text(json.dumps({
        "version": 1, "hooks": {"preToolUse": [{"bash": "true"}]},
    }))
    result = subprocess.run(["bash", lint, "--root", home], capture_output=True, text=True)
    assert result.returncode == 1 and not result.stderr, result
    assert "is missing beside bash" in result.stdout, result.stdout
    assert "2 commands checked, 1 failed" in result.stdout, result.stdout
    print("PASS  ox-vibesec: hook lint distinguishes bare and wrapped schemas regardless of manifest")

print("PASS  ox-vibesec: plugin-relative hooks, no-secret startup, edit mapping, installer verification, authenticated proxy environment")
PY
