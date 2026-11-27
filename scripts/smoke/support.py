#!/usr/bin/env python3
"""Set up isolated CLI sessions and local model stubs for smoke tests."""

import atexit
from functools import cache
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from threading import Thread
import unittest


ROOT = Path(__file__).resolve().parents[2]
PLUGINS = ("shunt", "steer", "personal-instructions")
MANIFESTS = {
    "claude": ".claude-plugin/plugin.json",
    "codex": ".codex-plugin/plugin.json",
    "copilot": "plugin.json",
    "devin": ".devin-plugin/plugin.json",
}
DONE = "DOTAI_SMOKE_OK"
RECAP = "Write a plain recap in a few sentences"
CODEX_FIXTURE_CALL = "call_smoke"


def plugins_for(harness):
    paths = (ROOT / "plugins" / name for name in PLUGINS)
    return {path.name: path for path in paths if (path / MANIFESTS[harness]).is_file()}


def hook_events(harness, plugin):
    manifest = json.loads((plugin / MANIFESTS[harness]).read_text())
    hooks = manifest.get("hooks", "hooks.json" if harness == "copilot" else "hooks/hooks.json")
    if isinstance(hooks, str):
        path = plugin / hooks
        hooks = json.loads(path.read_text()).get("hooks", {}) if path.is_file() else {}
    return hooks.keys()


def cli(args, env, cwd, *, private=False, timeout=45, payload=None):
    result = subprocess.run(
        args, env=env, cwd=cwd, timeout=timeout, input=payload,
        stdin=subprocess.DEVNULL if payload is None else None,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    if result.returncode:
        detail = "" if private else "\n" + result.stdout[-5000:]
        raise RuntimeError(f"{args[0]} exited {result.returncode}{detail}")
    return result.stdout


def codex_install(plugins, scratch, env, cwd):
    market = scratch / "market"
    config = market / ".agents/plugins"
    config.mkdir(parents=True)
    for name, src in plugins.items():
        shutil.copytree(src, market / "plugins" / name)
    (config / "marketplace.json").write_text(json.dumps({
        "name": "dotai-smoke",
        "plugins": [
            {"name": name, "source": {"source": "local", "path": f"./plugins/{name}"}}
            for name in plugins
        ],
    }))
    cli(["codex", "plugin", "marketplace", "add", str(market)], env, cwd)
    for name in plugins:
        cli(["codex", "plugin", "add", f"{name}@dotai-smoke"], env, cwd)


class Model(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "object": "list", "data": [{"id": self.server.model, "object": "model"}],
        }).encode())

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(body)
        step = len(self.server.requests)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        if self.server.harness == "claude":
            self.claude(step)
        elif self.server.harness == "codex":
            self.codex(step)
        else:
            self.copilot(step)

    def emit(self, event, **data):
        self.wfile.write(f"event: {event}\ndata: {json.dumps({'type': event, **data})}\n\n".encode())

    def claude(self, step):
        first = step == 1 and bool(self.server.command or self.server.markdown)
        self.emit("message_start", message={
            "id": f"msg_{step}", "type": "message", "role": "assistant", "model": self.server.model,
            "content": [], "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 0},
        })
        if first:
            tool = "Write" if self.server.markdown else "Bash"
            block = {"type": "tool_use", "id": "toolu_smoke", "name": tool, "input": {}}
            args = (
                {"file_path": str(self.server.markdown), "content": "Smoke fixture\n"}
                if self.server.markdown
                else {"command": self.server.command, "description": "Exercise the smoke fixture"}
            )
            delta = {"type": "input_json_delta", "partial_json": json.dumps(args)}
        else:
            block = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": DONE}
        self.emit("content_block_start", index=0, content_block=block)
        self.emit("content_block_delta", index=0, delta=delta)
        self.emit("content_block_stop", index=0)
        self.emit("message_delta", delta={
            "stop_reason": "tool_use" if first else "end_turn", "stop_sequence": None,
        }, usage={"output_tokens": 10})
        self.emit("message_stop")

    def codex(self, step):
        first = step == 1 and bool(self.server.command)
        if first:
            item = {
                "type": "function_call", "id": "fc_smoke", "call_id": CODEX_FIXTURE_CALL,
                "name": "exec_command", "arguments": json.dumps({"cmd": self.server.command}),
            }
        else:
            item = {
                "type": "message", "id": f"msg_{step}", "role": "assistant",
                "content": [{"type": "output_text", "text": DONE, "annotations": []}],
            }
        item["status"] = "completed"
        response = {
            "id": f"resp_{step}", "object": "response", "model": self.server.model,
            "status": "completed", "output": [item],
            "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
        }
        self.emit("response.created", response={**response, "output": [], "status": "in_progress"})
        self.emit("response.output_item.added", output_index=0, item=item)
        if first:
            self.emit("response.function_call_arguments.done", output_index=0,
                      item_id=item["id"], arguments=item["arguments"])
        else:
            self.emit("response.output_text.delta", output_index=0, content_index=0,
                      item_id=item["id"], delta=DONE)
        self.emit("response.output_item.done", output_index=0, item=item)
        self.emit("response.completed", response=response)

    def copilot(self, step):
        first = step == 1 and bool(self.server.command)
        if first:
            args = {"command": self.server.command, "description": "Exercise the smoke fixture"}
            delta = {"tool_calls": [{
                "index": 0, "id": "call_smoke", "type": "function",
                "function": {"name": "bash", "arguments": json.dumps(args)},
            }]}
        else:
            delta = {"content": DONE}
        for chunk_delta, finish in ((delta, None), ({}, "tool_calls" if first else "stop")):
            chunk = {
                "id": f"chatcmpl-{step}", "object": "chat.completion.chunk",
                "model": self.server.model,
                "choices": [{"delta": chunk_delta, "index": 0, "finish_reason": finish}],
            }
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")


def offline_run(harness, plugins, env, cwd, model, command=None, *, markdown=None, prompt=None):
    with ThreadingHTTPServer(("127.0.0.1", 0), Model) as stub:
        stub.harness, stub.model, stub.command, stub.requests = harness, model, command, []
        stub.markdown = markdown
        thread = Thread(target=stub.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{stub.server_port}"
        prompt = prompt or "Exercise the temporary test fixture and reply."
        try:
            if harness == "claude":
                env = {**env, "ANTHROPIC_BASE_URL": base, "ANTHROPIC_API_KEY": "local-stub",
                       "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
                args = ["claude", "-p", "--model", model, "--setting-sources", "user"]
                if command:
                    args += ["--allowedTools", f"Bash({command})"]
                if markdown:
                    args += ["--allowedTools", "Write"]
                for plugin in plugins.values():
                    args += ["--plugin-dir", str(plugin)]
                args += ["--", prompt]
            elif harness == "codex":
                env = {**env, "SMOKE_API_KEY": "local-stub"}
                args = [
                    "codex", "exec", "--skip-git-repo-check", "--dangerously-bypass-hook-trust",
                    "--sandbox", "workspace-write", "--model", model,
                    "-c", 'model_provider="stub"', "-c", 'model_providers.stub.name="Stub"',
                    "-c", f'model_providers.stub.base_url="{base}/v1"',
                    "-c", 'model_providers.stub.env_key="SMOKE_API_KEY"', prompt,
                ]
            else:
                env = {**env, "COPILOT_OFFLINE": "true", "COPILOT_PLUGIN_DIR_ONLY": "true",
                       "COPILOT_PROVIDER_BASE_URL": f"{base}/v1"}
                args = ["copilot", "--trust-folder", "--model", model]
                if command:
                    args += ["--allow-tool", f"shell({command.split()[0]})"]
                for plugin in plugins.values():
                    args += ["--plugin-dir", str(plugin)]
                args += ["-p", prompt]
            output = cli(args, env, cwd)
        finally:
            stub.shutdown()
            thread.join()
    if DONE not in output or not stub.requests:
        raise RuntimeError(f"{harness} did not complete the stub turn\n{output[-1800:]}")
    return [json.dumps(body, ensure_ascii=False) for body in stub.requests]


def codex_fixture_output(requests):
    for request in reversed(requests):
        for item in reversed(json.loads(request).get("input", [])):
            if item.get("type") == "function_call_output" and item.get("call_id") == CODEX_FIXTURE_CALL:
                return str(item.get("output", ""))[-2000:]
    return "No tool result reached the local model stub."


def copilot_observer(scratch):
    path = scratch / "stop-observer"
    path.mkdir()
    (path / "plugin.json").write_text(json.dumps(
        {"name": "dotai-stop-observer", "version": "1.0.0", "hooks": "./hooks.json"}
    ))
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), "copilot-stop-observer"])
    (path / "hooks.json").write_text(json.dumps(
        {"version": 1, "hooks": {"agentStop": [{"type": "command", "bash": command}]}}
    ))
    return path


def observe_copilot_stop():
    payload = json.load(sys.stdin)
    with (Path.home() / "stop-probe.jsonl").open("a") as stream:
        print(json.dumps({
            "payload": payload,
            "transcript_exists": Path(payload["transcriptPath"]).is_file(),
        }), file=stream)


def replay_copilot_stop(steer, env, cwd, payload):
    manifest = json.loads((steer / "plugin.json").read_text())
    hooks = json.loads((steer / manifest["hooks"]).read_text())
    return [
        cli(["bash", "-c", hook["bash"]], {**env, "PLUGIN_ROOT": str(steer)}, cwd,
            payload=json.dumps(payload)) for hook in hooks["hooks"]["agentStop"]
    ]


@cache
def install_claude(package):
    directory = tempfile.TemporaryDirectory(prefix="dotai-smoke-claude-")
    atexit.register(directory.cleanup)
    home = Path(directory.name)
    prefix = home / "npm"
    cli(["npm", "install", "--global", "--prefix", str(prefix), "--no-audit", "--no-fund",
         f"--allow-scripts={package.rsplit('@', 1)[0]}", package],
        {"PATH": os.environ["PATH"], "HOME": str(home)}, home)
    return str(prefix / "bin")


class SmokeTestCase(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory(prefix="dotai-smoke-"))
        self.scratch = Path(directory)
        self.home = self.scratch / "home"
        self.cwd = self.scratch / "workspace"
        self.home.mkdir()
        self.cwd.mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home)}
        self.plugins = plugins_for(self.harness)
        if self.harness == "claude" and (package := os.getenv("DOTAI_SMOKE_CLAUDE_PACKAGE")):
            self.env["PATH"] = install_claude(package) + os.pathsep + self.env["PATH"]
        if not shutil.which(self.harness, path=self.env["PATH"]):
            self.fail(f"{self.harness} CLI is not on PATH")
        if self.harness == "codex":
            codex_home = self.home / ".codex"
            codex_home.mkdir()
            self.env["CODEX_HOME"] = str(codex_home)
            if self.plugins:
                codex_install(self.plugins, self.scratch, self.env, self.cwd)

    def require_hook(self, plugin, event):
        if plugin not in self.plugins or not any(
            name.lower() == event.lower() for name in hook_events(self.harness, self.plugins[plugin])
        ):
            self.skipTest(f"No {plugin} {event} hook in this checkout")

    def run_turn(self, model="claude-fable-5", command=None, **kwargs):
        return offline_run(self.harness, self.plugins, self.env, self.cwd, model, command, **kwargs)


def instruction_marker(source):
    return next((line for line in source.read_text().splitlines() if line.startswith(("## ", "- "))), "")


if __name__ == "__main__" and sys.argv[1:] == ["copilot-stop-observer"]:
    observe_copilot_stop()
