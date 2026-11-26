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
import re
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
write_event = {**session, "tool_name": "write", "tool_input": {"path": "new file.py", "content": ""}}
patch_event = {
    **session, "tool_name": "apply_patch", "tool_use_id": "patch-id",
    "tool_input": {"input": """*** Begin Patch
*** Add File: new file.py
+first
+
+*** Delete File: literal.py
*** Update File: existing.py
@@
-before
+after
 context
-old
+new
@@ next section
+inserted
*** End of File

*** Delete File: obsolete.py
*** End Patch
"""},
}


def adapter_call(event, payload, result=None, *, results=None, cwd=plugin):
    stdout, stderr = StringIO(), StringIO()
    with (
        patch.dict(os.environ, {"OX_VIBESEC_API_KEY": test_key, "DEVIN_PROJECT_DIR": str(cwd)}),
        patch.object(sys, "argv", ["hook.py", event]),
        patch.object(sys, "stdin", StringIO(json.dumps(payload))),
        patch.object(vibesec.Runtime, "run", return_value=result, side_effect=results) as runtime,
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

accepted = Mock(returncode=0, stdout="")
project = tempfile.TemporaryDirectory()
root = Path(project.name)
existing = root / "existing.py"
existing_before = "before\ncontext\nold\nnext section\n"
existing_after = "after\ncontext\nnew\nnext section\ninserted\n"
added_content = "first\n\n*** Delete File: literal.py\n"
existing.write_text(existing_before)
(root / "obsolete.py").touch()
for event in ("PreToolUse", "PostToolUse"):
    response = {"tool_response": {"success": True, "output": "ok"}} if event == "PostToolUse" else {}
    for name in ("exec", "edit", "write", "apply_patch"):
        assert re.fullmatch(hooks[event][0]["matcher"], name)
    code, stdout, stderr, runtime = adapter_call(event, {**write_event, **response}, accepted)
    assert (code, stdout, stderr) == (0, "", "")
    assert runtime.call_args.args[0]["tool_name"] == "Write"
    assert runtime.call_args.args[0]["tool_input"] == {"file_path": "new file.py", "content": ""}
    if response:
        existing.write_text(existing_after)
        (root / "new file.py").write_text(added_content)
        (root / "obsolete.py").unlink()
    code, stdout, stderr, runtime = adapter_call(event, {**patch_event, **response}, accepted, cwd=root)
    assert (code, stdout, stderr) == (0, "", "")
    sent = [call.args[0] for call in runtime.call_args_list]
    assert [payload["tool_use_id"] for payload in sent] == ["patch-id:1", "patch-id:2"]
    assert [(p["tool_name"], p["tool_input"]) for p in sent] == [
        ("Write", {"file_path": "new file.py", "content": added_content}),
        ("Write", {"file_path": "existing.py", "content": existing_after}),
    ]
    assert all(payload["hook_event_name"] == event for payload in sent)
    if response:
        assert all(payload["tool_response"] == {"success": True, "stdout": "ok", "stderr": ""}
                   for payload in sent)

existing.write_text(existing_before)
code, stdout, stderr, runtime = adapter_call("PreToolUse", patch_event, cwd=root, results=[
    Mock(returncode=1), Mock(returncode=2, stderr=f"Blocked {test_key}\n"),
])
assert (code, stdout, stderr) == (2, "", "Blocked [redacted]\n")
assert runtime.call_count == 2
code, stdout, stderr, runtime = adapter_call("PreToolUse", patch_event, cwd=root, results=[
    accepted,
    vendor_reply({"permissionDecision": "deny", "permissionDecisionReason": "Second file"}),
])
assert code == 0 and json.loads(stdout) == {"decision": "block", "reason": "Second file"} and not stderr
assert runtime.call_count == 2
for invalid, warning in (
    ({"patch": patch_event["tool_input"]["input"]}, ""),
    ({"input": "*** Begin Patch"}, "OX VibeSec could not parse patch; check skipped.\n"),
    ({"input": patch_event["tool_input"]["input"].replace("-before", "-not present")},
     "OX VibeSec could not parse patch; check skipped.\n"),
    ({"input": "*** Begin Patch\n*** Update File: existing.py\n@@\n*** End Patch"},
     "OX VibeSec could not parse patch; check skipped.\n"),
):
    code, stdout, stderr, runtime = adapter_call(
        "PreToolUse", {**patch_event, "tool_input": invalid}, accepted, cwd=root,
    )
    assert (code, stdout, stderr) == (0, "", warning)
    runtime.assert_not_called()
print("PASS  ox-vibesec: dispatches full-file patch writes and blocks on a later file")

delete_patch = {
    **patch_event,
    "tool_input": {"input": "*** Begin Patch\n*** Delete File: obsolete.py\n*** End Patch"},
}
(root / "obsolete.py").touch()
for event in ("PreToolUse", "PostToolUse"):
    response = {}
    if event == "PostToolUse":
        (root / "obsolete.py").unlink()
        response = {"tool_response": {"success": True}}
    code, stdout, stderr, runtime = adapter_call(event, {**delete_patch, **response}, accepted, cwd=root)
    assert (code, stdout, stderr) == (0, "", "")
    runtime.assert_not_called()
print("PASS  ox-vibesec: skips delete-only patches without a warning")

eof_patch = {
    **patch_event,
    "tool_input": {
        "input": "*** Begin Patch\n*** Update File: eof.txt\n@@\n c\n-d\n+D\n*** End of File\n*** End Patch",
    },
}
for before, after in (
    ("a\nb\nc\nd\n\n", "a\nb\nc\nD\n\n"),
    ("c\nd\nc\nd\n", "c\nd\nc\nD\n"),
):
    (root / "eof.txt").write_text(before)
    code, stdout, stderr, runtime = adapter_call("PreToolUse", eof_patch, accepted, cwd=root)
    assert (code, stdout, stderr) == (0, "", "")
    runtime.assert_called_once()
    assert runtime.call_args.args[0]["tool_input"] == {"file_path": "eof.txt", "content": after}
print("PASS  ox-vibesec: prefers EOF matches and falls back to searching earlier lines")

manifest_patch = {
    **patch_event,
    "tool_input": {"input": """*** Begin Patch
*** Update File: package.json
@@
-    "alpha": "1.0.0",
+    "alpha": "2.0.0",
@@
-    "gamma": "1.0.0"
+    "gamma": "2.0.0"
*** Update File: ./package.json
@@
-    "alpha": "2.0.0",
+    "alpha": "3.0.0",
*** End Patch
"""},
}
manifest = root / "package.json"
before = '{\n  "dependencies": {\n    "alpha": "1.0.0",\n    "beta": "1.0.0",\n    "gamma": "1.0.0"\n  }\n}\n'
after = before.replace('"alpha": "1', '"alpha": "3').replace('"gamma": "1', '"gamma": "2')
manifest.write_text(before)
code, stdout, stderr, runtime = adapter_call("PreToolUse", manifest_patch, accepted, cwd=root)
assert (code, stdout, stderr) == (0, "", "")
runtime.assert_called_once()
pre = runtime.call_args.args[0]
assert pre["tool_name"] == "Write"
assert pre["tool_input"] == {"file_path": "./package.json", "content": after}
assert manifest.read_text() == before
manifest.write_text(after)
with patch.object(hook, "monotonic", side_effect=[100, 101]):
    code, stdout, stderr, runtime = adapter_call("PostToolUse", {
        **manifest_patch, "tool_response": {"success": True},
    }, vendor_reply({"hookEventName": "PostToolUse", "additionalContext": "One finding"}), cwd=root)
assert (code, stderr) == (0, "")
assert json.loads(stdout)["hookSpecificOutput"]["additionalContext"] == "One finding"
runtime.assert_called_once()
post = runtime.call_args.args[0]
assert runtime.call_args.kwargs["deadline"] == 123
assert (post["tool_name"], post["tool_input"], post["tool_use_id"]) == (
    pre["tool_name"], pre["tool_input"], pre["tool_use_id"],
)
code, stdout, stderr, runtime = adapter_call("PostToolUse", {
    **manifest_patch, "tool_response": {"success": False},
}, accepted, cwd=root)
assert (code, stdout, stderr) == (0, "", "")
runtime.assert_not_called()
print("PASS  ox-vibesec: replays multiple sections in order and reports a post-tool finding once")

wrapped = "\n".join([
    "apply_patch <<'PATCH'", "*** Begin Patch", "", "*** Update File:  old file.py  ",
    "*** Move to:  moved file.py  ", "@@ second section", "-before", r"\ No newline at end of file",
    "+after", "*** End Patch", "PATCH",
])
old = root / "old file.py"
old.write_text("first section\nbefore\nsecond section\nbefore")
moved_content = "first section\nbefore\nsecond section\nafter\n"
for event in ("PreToolUse", "PostToolUse"):
    response = {}
    if event == "PostToolUse":
        old.unlink()
        (root / "moved file.py").write_text(moved_content)
        response = {"tool_response": {"success": True}}
    code, stdout, stderr, runtime = adapter_call(event, {
        **patch_event, "tool_input": {"input": wrapped}, **response,
    }, accepted, cwd=root)
    assert (code, stdout, stderr) == (0, "", "")
    runtime.assert_called_once()
    payload = runtime.call_args.args[0]
    assert payload["tool_name"] == "Write"
    assert payload["tool_input"] == {"file_path": "moved file.py", "content": moved_content}
print("PASS  ox-vibesec: uses anchors for repeated text and writes moved files under their final path")

with patch.object(hook, "monotonic", side_effect=[100, 101, 123]):
    code, stdout, stderr, runtime = adapter_call("PreToolUse", patch_event, accepted, cwd=root)
assert (code, stdout, stderr) == (0, "", "OX VibeSec: check skipped (time budget)\n")
assert runtime.call_count == 1 and runtime.call_args.kwargs["deadline"] == 123
with patch.object(hook, "monotonic", side_effect=[100, 101, 122, 123]):
    code, stdout, stderr, runtime = adapter_call("PreToolUse", patch_event, cwd=root, results=[
        accepted, subprocess.TimeoutExpired("vendor hook", 1),
    ])
assert (code, stdout, stderr) == (0, "", "OX VibeSec: check skipped (time budget)\n")
assert runtime.call_count == 2
print("PASS  ox-vibesec: stops patch checks when the shared time budget expires")

guidance = vendor_reply({"hookEventName": "PreToolUse", "additionalContext": f"Keep {test_key}"})
code, stdout, stderr, runtime = adapter_call("PreToolUse", patch_event, cwd=root, results=[
    guidance, Mock(returncode=1),
])
assert code == 0 and stderr == "OX VibeSec hook unavailable.\n" and runtime.call_count == 2
assert json.loads(stdout) == {"hookSpecificOutput": {
    "hookEventName": "PreToolUse", "additionalContext": "Keep [redacted]",
}}
print("PASS  ox-vibesec: retains guidance when another patch check fails")
project.cleanup()

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
    chosen = subprocess.run(
        command, shell=True, cwd=home, env={**env, "PLUGIN_ROOT": str(home / "invalid")},
        capture_output=True, text=True,
    )
    assert chosen.returncode == 0 and chosen.stdout == "DEVIN_PLUGIN_ROOT\n" and not chosen.stderr
    for variable in roots:
        chosen = subprocess.run(command, shell=True, cwd=home, env=env, capture_output=True, text=True)
        assert chosen.returncode == 0 and chosen.stdout == variable + "\n" and not chosen.stderr
        env.pop(variable)

    install_bin = home / "fresh install" / "bin"
    install_bin.mkdir(parents=True)
    (install_bin / "ox-vibesec-hook").symlink_to(plugin / "bin/ox-vibesec-hook")
    installed = subprocess.run(
        hooks["UserPromptSubmit"][0]["hooks"][0]["command"], shell=True, cwd=home,
        env={**env, "PATH": f"{install_bin}:{env['PATH']}", "OX_VIBESEC_API_KEY": test_key},
        input=json.dumps({**session, "prompt": "test"}), capture_output=True, text=True,
    )
    assert installed.returncode == 0 and not installed.stdout, installed
    assert installed.stderr == "OX VibeSec runtime is not initialized; check skipped.\n", installed
    print("PASS  ox-vibesec: packaged PATH launcher reaches the adapter without a plugin root")

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
        input="fallback\n", capture_output=True, text=True,
    )
    assert invalid.returncode == 0 and invalid.stdout == f"{event}:fallback\n" and not invalid.stderr
    print("PASS  ox-vibesec: root precedence, stale-root recovery, PATH fallback, and missing-root diagnostics")

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

        warning = StringIO()
        with redirect_stderr(warning), patch.object(vibesec.subprocess, "run", side_effect=fetch) as download:
            assert vibesec.verified_installer(home / "missing.sh", dest, env).read_bytes() == installer
            download.assert_called_once()
        assert warning.getvalue() == "OX_VIBESEC_INSTALLER file not found; downloading the installer.\n"
        print("PASS  ox-vibesec: missing staged installer warns and downloads")

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
    assert runtime.env["HTTPS_PROXY"] == "http://LOCALHOST:3128"
    print("PASS  ox-vibesec: lowercases only the forwarded proxy scheme")
    with (
        patch.object(runtime, "installed", return_value=["sh", vibesec.LAUNCHER]),
        patch.object(vibesec.subprocess, "run") as run,
    ):
        runtime.run({}, home, "test-token")
        assert run.call_args.kwargs["env"]["NODE_USE_ENV_PROXY"] == "1"
    print("PASS  ox-vibesec: hook subprocess enables the environment for an unauthenticated proxy")

    proxy = "http://localhost:3128"
    for bypass in (
        "api.cloud.ox.security", "API.CLOUD.OX.SECURITY:443", ".ox.security",
        "ox.security", "cloud.ox.security", ".ox.security:443",
    ):
        with patch.dict(os.environ, {"HTTPS_PROXY": proxy, "NO_PROXY": bypass}, clear=True):
            runtime = vibesec.Runtime(home / "runtime", staged)
        assert runtime.env["NO_PROXY"] == bypass
        assert runtime.env["no_proxy"] == f"{bypass},api.cloud.ox.security:443"
        assert runtime.env["NODE_USE_ENV_PROXY"] == "1"
    with patch.dict(os.environ, {"HTTPS_PROXY": proxy, "NO_PROXY": "*"}, clear=True):
        runtime = vibesec.Runtime(home / "runtime", staged)
    assert runtime.env["NO_PROXY"] == "*" and "no_proxy" not in runtime.env
    for bypass in ("*.ox.security", ".other.example, api.cloud.ox.security:80"):
        with patch.dict(os.environ, {
            "HTTPS_PROXY": proxy, "NO_PROXY": "*", "no_proxy": bypass,
        }, clear=True):
            runtime = vibesec.Runtime(home / "runtime", staged)
        assert runtime.env["no_proxy"] == bypass
    with patch.dict(os.environ, {
        "HTTPS_PROXY": proxy, "NO_PROXY": "ox.security", "no_proxy": "",
    }, clear=True):
        runtime = vibesec.Runtime(home / "runtime", staged)
    assert "api.cloud.ox.security:443" in runtime.env["no_proxy"].split(","), runtime.env["no_proxy"]
    print("PASS  ox-vibesec: empty lowercase no_proxy inherits the API bypass")
    print("PASS  ox-vibesec: preserves NO_PROXY suffix bypasses for the OX installer")

    launcher = ["sh", vibesec.LAUNCHER]
    for proxy, lowercase in (
        ("http://localhost:3128", {}),
        ("http://test-user:test-password@localhost:3128", {
            "https_proxy": "http://localhost:3129", "http_proxy": "", "no_proxy": "",
        }),
    ):
        uppercase = {"HTTPS_PROXY": proxy, "HTTP_PROXY": proxy, "NO_PROXY": ".other.example"}
        with patch.dict(os.environ, {**uppercase, **lowercase}, clear=True):
            runtime = vibesec.Runtime(home / "runtime", staged)
        with (
            patch.object(vibesec, "verified_installer", return_value=dest),
            patch.object(runtime, "installed", side_effect=[None, launcher]),
            patch.object(vibesec.subprocess, "run", return_value=Mock(returncode=0)) as run,
        ):
            assert runtime.start("test-token") == launcher
            args, kwargs = run.call_args
            assert "--proxy" not in args[0] and all(proxy not in arg for arg in args[0])
            for name, value in uppercase.items():
                assert kwargs["env"][name] == value
                assert kwargs["env"][name.lower()] == (lowercase.get(name.lower()) or value)
            assert kwargs["env"]["NODE_USE_ENV_PROXY"] == "1"
            assert kwargs["input"] == "test-token\n"
    print("PASS  ox-vibesec: installer mirrors uppercase proxy variables without overriding lowercase")

    proxy_with_bracket = "http://test-user:test[password@localhost:3128"
    with patch.dict(os.environ, {"HTTPS_PROXY": proxy_with_bracket}, clear=True):
        runtime = vibesec.Runtime(home / "runtime", staged)
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
    with patch.object(vibesec, "monotonic", side_effect=[100, 102]), patch.object(
        vibesec.subprocess, "run", return_value=Mock(returncode=0),
    ) as launch:
        runtime.run({}, home, "test-token", deadline=105)
    assert [call.kwargs["timeout"] for call in launch.call_args_list] == [5, 3]
    print("PASS  ox-vibesec: runtime checks and launcher share the same deadline")
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

    for entry in (
        "not-a-hook", {"hooks": ["not-a-hook"]}, {"hooks": {"command": "true"}}, {"command": False},
        {"type": "command"}, {"type": "prompt"}, {"type": "prompt", "prompt": False}, {"type": "other"},
    ):
        (bare / "hooks.json").write_text(json.dumps({"SessionStart": [entry]}))
        result = subprocess.run(["bash", lint, "--root", home], capture_output=True, text=True)
        assert result.returncode == 1 and not result.stderr, result
        assert "contains an invalid hook entry" in result.stdout, result.stdout
    (bare / "hooks.json").write_text(json.dumps({"SessionStart": [{"command": "true"}]}))
    (wrapped / "hooks.json").write_text(json.dumps({"hooks": {"preToolUse": ["not-a-hook"]}}))
    result = subprocess.run(["bash", lint, "--root", home], capture_output=True, text=True)
    assert result.returncode == 1 and not result.stderr, result
    assert "cannot read hook commands" in result.stdout and "1 commands checked, 1 failed" in result.stdout
    print("PASS  ox-vibesec: hook lint rejects invalid entries and reports command extraction failures")

    (wrapped / "hooks.json").write_text(json.dumps({"hooks": {}}))
    (bare / "hooks.json").write_text(json.dumps({"UserPromptSubmit": [{"hooks": [
        {"type": "prompt", "prompt": "Check the request"},
        {"type": "prompt", "prompt": "Check again", "command": 'echo "${UNKNOWN_PLUGIN_ROOT}"'},
        {"type": "command", "command": "true"},
    ]}]}))
    result = subprocess.run(["bash", lint, "--root", home], capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr, result
    assert "1 commands checked, 0 failed" in result.stdout, result.stdout
    print("PASS  ox-vibesec: hook lint skips prompt hooks and still checks commands")

print("PASS  ox-vibesec: plugin-relative hooks, no-secret startup, edit mapping, installer verification, authenticated proxy environment")
PY
