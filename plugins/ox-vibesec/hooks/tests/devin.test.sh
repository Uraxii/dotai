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
import runpy
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

repo = plugin.parents[1]
generator = runpy.run_path(str(repo / "scripts/generate-plugin-manifests.py"))
ox = next(entry for entry in generator["PLUGINS"] if entry["name"] == "ox-vibesec")
with patch.dict(ox, {"version": "2.0.0"}):
    files = generator["wanted_files"](repo)
    assert json.loads(files[Path("plugins/ox-vibesec/.devin-plugin/plugin.json")])["version"] == "2.0.0"
print("PASS  ox-vibesec: Devin manifest version comes from the generator")

try:
    generator["hook_wiring_paths"]({**ox, "hooks": ["copilot", "devin"]})
except ValueError as error:
    assert str(error) == "ox-vibesec: copilot and devin hooks both use hooks.json"
else:
    raise AssertionError("accepted conflicting hook wiring")
print("PASS  ox-vibesec: generator rejects conflicting Copilot and Devin hooks")

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

code, stdout, stderr, _ = adapter_call("PreToolUse", exec_event, Mock(returncode=2, stderr="  \n"))
assert code == 2 and not stdout and stderr == "OX VibeSec blocked this action.\n"
code, stdout, stderr, _ = adapter_call(
    "PreToolUse", exec_event, Mock(returncode=2, stderr=f"Vendor blocked {test_key}\n"),
)
assert code == 2 and not stdout and stderr == "Vendor blocked [redacted]\n"
print("PASS  ox-vibesec: forwards redacted exit-code-2 reason or a generic fallback")

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

code, stdout, stderr, _ = adapter_call("PreToolUse", exec_event, None)
assert code == 0 and not stdout
assert stderr == "OX VibeSec runtime is not initialized; check skipped.\n"
code, stdout, stderr, _ = adapter_call("SessionStart", session, None)
assert code == 0 and not stdout and not stderr
print("PASS  ox-vibesec: warns on uninitialized runtime without blocking")

with tempfile.TemporaryDirectory() as temp:
    home = Path(temp)
    env = os.environ.copy()
    env.pop("OX_VIBESEC_API_KEY", None)
    roots = ("PLUGIN_ROOT", "DEVIN_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT")
    for variable in roots:
        env.pop(variable, None)
    env.update(HOME=temp, PLUGIN_ROOT=str(plugin))
    for groups in hooks.values():
        command = groups[0]["hooks"][0]["command"]
        completed = subprocess.run(
            command, shell=True, cwd=home, env=env,
            input=json.dumps(session), capture_output=True, text=True,
        )
        assert completed.returncode == 0, completed.stderr
        assert not completed.stdout and not completed.stderr
    assert not list(home.iterdir())

    command = hooks["SessionStart"][0]["hooks"][0]["command"]
    for variable in roots:
        script = home / variable / "bin/hook.py"
        script.parent.mkdir(parents=True)
        script.write_text(f"print({variable!r})\n")
        env[variable] = str(script.parents[1])
    for variable in roots:
        chosen = subprocess.run(command, shell=True, cwd=home, env=env, capture_output=True, text=True)
        assert chosen.returncode == 0 and chosen.stdout == variable + "\n" and not chosen.stderr
        env.pop(variable)

    env["PATH"] = str(home)
    missing = subprocess.run(command, shell=True, cwd=home, env=env, capture_output=True, text=True)
    assert missing.returncode == 0 and not missing.stdout
    assert missing.stderr == "ox-vibesec: plugin root not found\n"
    launcher = home / "ox-vibesec-hook"
    launcher.write_text('#!/bin/sh\nread -r payload\nprintf "%s:%s\\n" "$1" "$payload"\n')
    launcher.chmod(0o755)
    for event, groups in hooks.items():
        command = groups[0]["hooks"][0]["command"]
        chosen = subprocess.run(
            command, shell=True, cwd=home, env=env, input="payload\n", capture_output=True, text=True,
        )
        assert chosen.returncode == 0 and chosen.stdout == f"{event}:payload\n" and not chosen.stderr
    invalid = subprocess.run(
        command, shell=True, cwd=home, env={**env, "PLUGIN_ROOT": str(home / "invalid")},
        capture_output=True, text=True,
    )
    assert invalid.returncode == 0 and not invalid.stdout
    assert invalid.stderr == "ox-vibesec: plugin root not found\n"
    print("PASS  ox-vibesec: plugin root precedence, PATH fallback, and missing-root diagnostics")

    installer = b"fake installer"
    digest = hashlib.sha256(installer).hexdigest()
    staged = home / "staged.sh"
    dest = home / "install.sh"
    staged.write_bytes(installer)
    with patch.object(vibesec, "INSTALLER_SHA256", digest):
        with patch.object(vibesec.subprocess, "run") as download:
            assert vibesec.verified_installer(staged, dest, env).read_bytes() == installer
            download.assert_not_called()

        def fetch(args, **kwargs):
            assert args[-1] == vibesec.INSTALLER_URL
            Path(args[args.index("-o") + 1]).write_bytes(installer)

        with patch.object(vibesec.subprocess, "run", side_effect=fetch) as download:
            assert vibesec.verified_installer(None, dest, env).read_bytes() == installer
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

    proxy = "http://localhost:3128"
    for bypass in ("api.cloud.ox.security", "API.CLOUD.OX.SECURITY:443", ".ox.security", "*.ox.security", "*"):
        with patch.dict(os.environ, {"HTTPS_PROXY": proxy, "NO_PROXY": bypass}, clear=True):
            runtime = vibesec.Runtime(home / "runtime", staged)
        assert runtime.proxy_args == []
        assert runtime.env["NO_PROXY"] == bypass
        assert runtime.env["NODE_USE_ENV_PROXY"] == "1"
    with patch.dict(os.environ, {
        "HTTPS_PROXY": proxy, "NO_PROXY": "*", "no_proxy": ".other.example, api.cloud.ox.security:80",
    }, clear=True):
        runtime = vibesec.Runtime(home / "runtime", staged)
    assert runtime.proxy_args == ["--proxy", proxy]
    print("PASS  ox-vibesec: leaves OX API proxy bypass to the vendor runtime when NO_PROXY matches")

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

    runtime_home = home / "runtime with spaces"
    vendor_hook = runtime_home / ".claude/hooks/ox_mind.js"
    vendor_hook.parent.mkdir(parents=True)
    vendor_hook.touch()
    (vendor_hook.parent.parent / ".ox.json").write_text(json.dumps({"access_token": "test-token"}))
    nodes = {}
    for version, mode in (("v24.9", 0o755), ("v24.10", 0o644)):
        node = runtime_home / f".ox/node/{version}/bin/node"
        node.parent.mkdir(parents=True)
        node.write_text(f"#!/bin/sh\necho {version}\n")
        node.chmod(mode)
        nodes[version] = node
    runtime = vibesec.Runtime(runtime_home, None)
    assert runtime.installed("test-token") == ["sh", vibesec.LAUNCHER]
    result = runtime.run({}, home, "test-token")
    assert result.returncode == 0 and result.stdout == "v24.9\n" and not result.stderr
    nodes["v24.10"].chmod(0o755)
    result = runtime.run({}, home, "test-token")
    assert result.returncode == 0 and result.stdout == "v24.10\n" and not result.stderr
    for node in nodes.values():
        node.chmod(0o644)
    assert runtime.run({}, home, "test-token") is None
    print("PASS  ox-vibesec: readiness and launcher resolve the newest executable Node")

    lint = plugin.parents[1] / "scripts/lint-hook-references.sh"
    bare = home / "plugins/bare"
    bare.mkdir(parents=True)
    (bare / "hooks.json").write_text(json.dumps({"SessionStart": [{"hooks": [
        {"type": "command", "command": 'echo "${PLUGIN_ROOT}" "${DEVIN_PLUGIN_ROOT}" "${CLAUDE_PLUGIN_ROOT}"'},
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

    (bare / "hooks.json").write_text(json.dumps({
        "description": "not an event", "SessionStart": [{"hooks": [{"command": "true"}]}],
    }))
    result = subprocess.run(["bash", lint, "--root", home], capture_output=True, text=True)
    assert result.returncode == 1 and not result.stderr, result
    assert "must map hook event names to arrays" in result.stdout, result.stdout
    print("PASS  ox-vibesec: hook lint rejects non-array values in bare event maps")

print("PASS  ox-vibesec: plugin-relative hooks, no-secret startup, edit mapping, installer verification, authenticated proxy environment")
PY
