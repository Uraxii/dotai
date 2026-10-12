#!/usr/bin/env python3
"""Emit one SessionStart or SubagentStart context for Claude Code or Copilot CLI.

`codebase-memory-mcp install` gives a harness a global instruction file and a
lifecycle hook that runs `codebase-memory-mcp hook-augment`. A plugin cannot
write the instruction file, and two hooks on one event inject two contexts.
This hook joins instructions.md with hook-augment's graph context, so each
event injects one context into the session and into every subagent.

The hook always exits 0 and prints nothing it cannot build.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

INSTRUCTIONS = Path(__file__).resolve().parent / "instructions.md"
AUGMENT_TIMEOUT_SECONDS = 4


def augment_command(harness: str, event: str) -> list[str]:
    command = ["codebase-memory-mcp", "hook-augment"]
    if harness == "copilot":
        command += ["--event", event, "--dialect", "copilot"]
    return command


def graph_context(harness: str, event: str, hook_input: bytes) -> str:
    try:
        result = subprocess.run(
            augment_command(harness, event),
            input=hook_input,
            capture_output=True,
            timeout=AUGMENT_TIMEOUT_SECONDS,
            check=False,
        )
        payload = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    if harness == "claude":
        payload = payload.get("hookSpecificOutput") or {}
    context = payload.get("additionalContext")
    return context if isinstance(context, str) else ""


def build_output(harness: str, event: str, text: str) -> str:
    if harness == "claude":
        return json.dumps(
            {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
        )
    return json.dumps({"additionalContext": text})


def main(arguments: list[str] | None = None, hook_input: bytes = b"") -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--harness", choices=("claude", "copilot"), required=True)
    parser.add_argument("--event", choices=("SessionStart", "SubagentStart"), required=True)
    options = parser.parse_args(arguments)
    instructions = INSTRUCTIONS.read_text(encoding="utf-8")
    parts = [instructions.strip(), graph_context(options.harness, options.event, hook_input)]
    text = "\n\n".join(part for part in parts if part)
    if text:
        print(build_output(options.harness, options.event, text))
    return 0


if __name__ == "__main__":
    try:
        main(hook_input=sys.stdin.buffer.read())
    except SystemExit:
        pass
    except Exception as error:
        print(f"lifecycle_context: {type(error).__name__}: {error}", file=sys.stderr)
    sys.exit(0)
