#!/usr/bin/env python3
"""Remind the agent to load poteto-mode at the start of a session.

Claude Code runs this on SessionStart (matcher startup|clear|compact); its
plain stdout is added to context automatically, no envelope needed. Codex
runs it separately on SessionStart and on PostCompact, and expects one JSON
line shaped like `{"hookSpecificOutput": {"hookEventName": ...,
"additionalContext": ...}}`. Copilot CLI runs it on its own `sessionStart`
hook and expects `{"additionalContext": ...}` on stdout (docs.github.com,
Copilot CLI hooks reference, "Hook event input payloads" / `sessionStart`;
SDK doc `docs/hooks/session-lifecycle.md` shows the same field for the
programmatic form; fetched 2026-09-14). opencode has no event that fires
once at session start and can inject text, so its plugin
(`opencode-reminder-plugin.ts`, same directory) calls this script once at
plugin load and pushes the plain text onto the system prompt on every LLM
request instead (see that file's docstring for citations). Hermes runs it on
`pre_llm_call` and expects `{"context": ...}` only on a session's first
turn, `{}` otherwise, read from stdin JSON.

Hook protocol:
- stdin: unused, except --harness hermes, which reads the shell-hook JSON
  envelope Hermes sends on every `pre_llm_call`.
- stdout for --harness claude / opencode: the reminder text, nothing else.
- stdout for --harness codex: one JSON line, hookEventName set to --event.
- stdout for --harness copilot: one JSON line, `{"additionalContext": ...}`.
- stdout for --harness hermes: one JSON line, `{"context": ...}` on the
  first turn of a session, `{}` on every later turn.
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
    """Reminder text for Claude/opencode, or one JSON line for Codex/Copilot."""
    if harness == "codex":
        payload = {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": REMINDER_TEXT,
            }
        }
        return json.dumps(payload)
    if harness == "copilot":
        return json.dumps({"additionalContext": REMINDER_TEXT})
    return REMINDER_TEXT


def build_hermes_output(payload: dict) -> str:
    """One JSON line for Hermes's `pre_llm_call` shell hook.

    `pre_llm_call` fires once per user turn, not once per session (Hermes
    docs, "Hooks", lines 681 and 677; fetched into the clone at
    NousResearch/hermes-agent@498abb6 2026-09-14). Inject the reminder only
    on the session's first turn (`extra.is_first_turn`); every later turn,
    and any payload where that flag cannot be read, gets a no-op `{}` so the
    reminder never repeats or risks firing every turn on a shape change.
    """
    if payload.get("extra", {}).get("is_first_turn") is True:
        return json.dumps({"context": REMINDER_TEXT})
    return json.dumps({})


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--harness",
        choices=("claude", "codex", "copilot", "opencode", "hermes"),
        required=True,
    )
    parser.add_argument("--event", choices=("SessionStart", "PostCompact"))
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    if options.harness == "hermes":
        payload = json.loads(sys.stdin.read())
        print(build_hermes_output(payload))
        return 0
    print(build_output(options.harness, options.event))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # ponytail: fail-safe per hook contract — any error means exit 0,
        # silent. Never crash the session over a reminder.
        sys.exit(0)
