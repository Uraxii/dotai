#!/usr/bin/env python3
"""Exercise the installed plugin hooks through real CLI sessions."""

import argparse
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


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ("shunt", "steer", "personal-instructions")
MANIFESTS = {
    "claude": ".claude-plugin/plugin.json",
    "codex": ".codex-plugin/plugin.json",
    "copilot": "plugin.json",
    "devin": ".devin-plugin/plugin.json",
}
DONE = "DOTAI_SMOKE_OK"
RECAP = "Write a plain recap in a few sentences"


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
                "type": "function_call", "id": "fc_smoke", "call_id": "call_smoke",
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


def check(ok, description):
    if not ok:
        raise RuntimeError(description)
    print(f"PASS {description}", flush=True)


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


def check_copilot_recap(steer, env, cwd, model, expected, actual):
    path = Path(env["HOME"]) / "stop-probe.jsonl"
    observations = [json.loads(line) for line in path.read_text().splitlines()]
    check(bool(observations), "copilot: observed agentStop")
    if actual == expected and (expected or observations[0]["transcript_exists"]):
        check(True, f"copilot: {model} turn receives {expected} recap continuation(s)")
        return
    if actual or observations[0]["transcript_exists"]:
        check(False, f"copilot: {model} received {actual} recap continuation(s), expected {expected}")

    manifest = json.loads((steer / "plugin.json").read_text())
    hooks = json.loads((steer / manifest["hooks"]).read_text())
    commands = hooks["hooks"]["agentStop"]
    payload = observations[0]["payload"]
    check(Path(payload["transcriptPath"]).is_file(), "copilot: saved the transcript after agentStop")
    print(f"SKIP copilot: {model} live recap assertion (agentStop ran before the transcript existed)")
    output = [
        cli(["bash", "-c", hook["bash"]], {**env, "PLUGIN_ROOT": str(steer)}, cwd,
            payload=json.dumps(payload)) for hook in commands
    ]
    check(sum(RECAP in result for result in output) == expected,
          f"copilot: {model} agentStop replay requests {expected} recap continuation(s)")


def offline_smoke(harness, plugins, scratch, env, cwd):
    if harness == "codex":
        codex_home = Path(env["HOME"]) / ".codex"
        codex_home.mkdir()
        env["CODEX_HOME"] = str(codex_home)
        if plugins:
            codex_install(plugins, scratch, env, cwd)

    def events(plugin):
        return hook_events(harness, plugins[plugin]) if plugin in plugins else ()

    has_shunt = any(name.lower() == "pretooluse" for name in events("shunt"))
    has_stop = any(name.lower() in ("stop", "agentstop") for name in events("steer"))
    has_instructions = any(name.lower() == "sessionstart" for name in events("personal-instructions"))
    copilot_stop = harness == "copilot" and has_stop
    observation = Path(env["HOME"]) / "stop-probe.jsonl"
    if copilot_stop:
        plugins = {**plugins, "stop-observer": copilot_observer(scratch)}
    (cwd / "large.txt").write_text("large read fixture\n" * 500)
    requests = offline_run(harness, plugins, env, cwd, "claude-fable-5",
                           "cat large.txt" if has_shunt else None)
    if has_shunt:
        check(any("bulk-reader" in req and "500-line file" in req for req in requests),
              f"{harness}: Shunt denied the 500-line read")
    if has_instructions:
        for name in ("instructions.md", "main-agent-instructions.md"):
            source = plugins["personal-instructions"] / name
            marker = next((line for line in source.read_text().splitlines()
                           if line.startswith(("## ", "- "))), None)
            check(marker and any(marker in req for req in requests),
                  f"{harness}: Personal Instructions injected {name}")
    if has_stop:
        if copilot_stop:
            check_copilot_recap(plugins["steer"], env, cwd, "read-only Fable", 0,
                                sum(RECAP in req for req in requests))
        else:
            check(not any(RECAP in req for req in requests), f"{harness}: a read-only Fable turn skips recap")
        for model, expected in (("claude-opus-5", 1), ("claude-fable-5", 1), ("claude-sonnet-5", 0)):
            target = cwd / f"{model}.txt"
            observation.unlink(missing_ok=True)
            requests = offline_run(harness, plugins, env, cwd, model, f"touch {target.name}")
            check(target.is_file(), f"{harness}: {model} wrote the fixture")
            actual = sum(RECAP in req for req in requests)
            if copilot_stop:
                check_copilot_recap(plugins["steer"], env, cwd, model, expected, actual)
            else:
                check(actual == expected,
                      f"{harness}: {model} mutation receives {expected} recap continuation(s)")
    if harness == "claude" and "PreToolUse" in events("steer"):
        target = cwd / "smoke.md"
        offline_run(harness, plugins, env, cwd, "claude-sonnet-5", markdown=target,
                    prompt="Report the test status. Do not change any files.")
        check(not target.exists(), "claude: Steer denied an unrequested first-tool Markdown write")
        offline_run(harness, plugins, env, cwd, "claude-sonnet-5", markdown=target,
                    prompt="Please write to smoke.md.")
        check(target.is_file(), "claude: Steer allowed an explicitly requested Markdown write")
    for available, label in ((has_shunt, "Shunt large-read hook"), (has_stop, "Steer Stop"),
                             (has_instructions, "Personal Instructions session hook")):
        if not available:
            print(f"SKIP {harness}: no {label} in this checkout")


def devin_smoke(plugins, env, cwd, credentials):
    if not plugins:
        print("SKIP devin: no native smoke plugins in this checkout")
        return
    data_home = Path(env["HOME"]) / ".local/share"
    dest = data_home / "devin/credentials.toml"
    dest.parent.mkdir(parents=True, mode=0o700)
    with open(dest, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as target:
        target.write(Path(credentials).read_bytes())
    env["XDG_DATA_HOME"] = str(data_home)
    cli(["devin", "auth", "--process-model", "in-process", "status"], env, cwd, private=True)
    for name, plugin in plugins.items():
        cli(["devin", "plugins", "install", "--local", "--yes",
             "--process-model", "in-process", str(plugin)], env, cwd, private=True)
        print(f"PASS devin: installed {name} locally")
    loaded = cli(["devin", "plugins", "list"], env, cwd, private=True)
    check(all(name in loaded for name in plugins), "devin: native plugins appear in the isolated install list")
    output = cli(["devin", "--process-model", "in-process", "--respect-workspace-trust", "false",
                  "-p", f"Do not use tools. Reply with exactly {DONE}."],
                 env, cwd, private=True, timeout=120)
    check(DONE in output, "devin: authenticated headless prompt completed with the native plugins installed")


def main():
    if sys.argv[1:] == ["copilot-stop-observer"]:
        observe_copilot_stop()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("harness", choices=MANIFESTS)
    parser.add_argument("--npm-package", help="install this CLI into the temporary smoke home")
    args = parser.parse_args()
    harness = args.harness
    credentials = os.getenv("DEVIN_SMOKE_CREDENTIALS_FILE")
    if harness == "devin" and not credentials:
        print("SKIP devin: set DEVIN_SMOKE_CREDENTIALS_FILE to enable authenticated smoke")
        return
    if not args.npm_package and not shutil.which(harness):
        parser.exit(1, f"ERROR: {harness} CLI is not on PATH\n")
    plugins = plugins_for(harness)
    with tempfile.TemporaryDirectory(prefix="dotai-smoke-") as directory:
        scratch = Path(directory)
        home, cwd = scratch / "home", scratch / "workspace"
        home.mkdir()
        cwd.mkdir()
        env = {"PATH": os.environ["PATH"], "HOME": str(home)}
        try:
            if args.npm_package:
                prefix = home / "npm"
                cli(["npm", "install", "--global", "--prefix", str(prefix), "--no-audit", "--no-fund",
                     f"--allow-scripts={args.npm_package.rsplit('@', 1)[0]}",
                     args.npm_package], env, cwd)
                env["PATH"] = str(prefix / "bin") + os.pathsep + env["PATH"]
            if harness == "devin":
                devin_smoke(plugins, env, cwd, credentials)
            else:
                offline_smoke(harness, plugins, scratch, env, cwd)
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            parser.exit(1, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
