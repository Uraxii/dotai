#!/usr/bin/env python3
"""Emit the session reminder in the target tool's hook format."""

import argparse
import json

REMINDER_TEXT = """You have poteto-mode.

Before starting any non-trivial task, a feature, bug fix, refactor, debugging, delegation, or multi-step change, load the `poteto-mode` skill and follow it. It carries the trigger list, the principle index, the agent roster and spawn contract, and the playbook index.

Pure questions and trivial one-line edits do not need it. If you were dispatched to execute one scoped brief, poteto-mode already shaped that brief; work the brief instead.

CLAUDE.md, AGENTS.md, and direct instructions from the user override this reminder."""



def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', choices=('claude', 'codex', 'copilot'),
                        required=True)
    parser.add_argument('--event', choices=('SessionStart',),
                        default='SessionStart')
    options = parser.parse_args()
    if options.harness == 'codex':
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': options.event,
            'additionalContext': REMINDER_TEXT,
        }}))
    elif options.harness == 'copilot':
        print(json.dumps({'additionalContext': REMINDER_TEXT}))
    else:
        print(REMINDER_TEXT)


if __name__ == '__main__':
    main()
