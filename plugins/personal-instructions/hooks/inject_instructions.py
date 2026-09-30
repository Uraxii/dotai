#!/usr/bin/env python3
"""Inject the plugin's instructions.md into the root session and its subagents.

Root session hook text does not reach subagents, so each harness wires both a
session-start and a subagent-start hook to this script. Subagents are covered
only where the harness fires a subagent-start hook. Known gaps: Copilot's
built-in `general-purpose` agent fires no subagentStart; Copilot has no
documented re-inject after compaction; Codex subagents get nothing after
compaction.
- claude SessionStart: plain text. Claude ignores plain stdout on
  SubagentStart, so that event gets the hookSpecificOutput JSON line.
- codex: one hookSpecificOutput JSON line, hookEventName set to --event.
- copilot: one {"additionalContext": ...} JSON line.
A missing or empty instructions.md prints nothing and exits 0. Any other error
prints nothing on stdout, one line on stderr, and exits 0.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

INSTRUCTIONS_PATH = Path(__file__).resolve().parent.parent / "instructions.md"


def build_output(harness: str, event: str, text: str) -> str:
    if harness == "codex" or (harness == "claude" and event == "SubagentStart"):
        return json.dumps(
            {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
        )
    if harness == "copilot":
        return json.dumps({"additionalContext": text})
    return text


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("claude", "codex", "copilot"), required=True)
    parser.add_argument("--event", choices=("SessionStart", "SubagentStart"), default="SessionStart")
    options = parser.parse_args(arguments)
    if not INSTRUCTIONS_PATH.is_file():
        return 0
    text = INSTRUCTIONS_PATH.read_text(encoding="utf-8").strip()
    if text:
        print(build_output(options.harness, options.event, text))
    return 0


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception as error:
        print(f"inject_instructions: {type(error).__name__}: {error}", file=sys.stderr)
    sys.exit(0)
