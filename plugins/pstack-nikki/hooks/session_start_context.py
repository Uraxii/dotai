#!/usr/bin/env python3
"""Remind the agent to load poteto-mode at the start of a session.

Claude Code runs this on SessionStart (matcher startup|clear|compact); its
plain stdout is added to context automatically, no envelope needed. Codex
runs it separately on SessionStart and on PostCompact, and expects one JSON
line shaped like `{"hookSpecificOutput": {"hookEventName": ...,
"additionalContext": ...}}`.

Hook protocol:
- stdin: unused.
- stdout for --harness claude: the reminder text, nothing else.
- stdout for --harness codex: one JSON line, hookEventName set to --event.
- exit code: always 0. Any error -> exit 0, print nothing. Never crash the
  session.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys

REMINDER_TEXT = """You have poteto-mode.

Before starting any non-trivial task, a feature, bug fix, refactor, debugging, delegation, or multi-step change, load the `poteto-mode` skill and follow it. It carries the trigger list, the principle index, the agent roster and spawn contract, and the playbook index.

Pure questions and trivial one-line edits do not need it. If you were dispatched to execute one scoped brief, poteto-mode already shaped that brief; work the brief instead.

CLAUDE.md, AGENTS.md, and direct instructions from the user override this reminder."""


def build_output(harness: str, event: str | None) -> str:
    """Reminder text for Claude, or one JSON line for Codex."""
    if harness == "codex":
        payload = {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": REMINDER_TEXT,
            }
        }
        return json.dumps(payload)
    return REMINDER_TEXT


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("claude", "codex"), required=True)
    parser.add_argument("--event", choices=("SessionStart", "PostCompact"))
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    print(build_output(options.harness, options.event))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # ponytail: fail-safe per hook contract — any error means exit 0,
        # silent. Never crash the session over a reminder.
        sys.exit(0)
