#!/usr/bin/env python3
"""recap_on_stop — Stop hook asking for a plain-English recap of the turn.

Wired in the plugin's `hooks/hooks.json` under `Stop`.

Fires when Claude tries to end its turn. Returns `{"decision": "block"}`,
which does not stop at all: it hands Claude one more instruction, to write
a short recap for someone who has not read the code. Every stop gets one
as long as the model that answered matches `opus-5|fable`; that and the
loop guard below are the whole gate. Every invocation appends one line to
an audit log so a declined gate never looks like a hook that never ran.

Rationale: a consistent close-out enforced by the harness, instead of the
user remembering to ask for a summary every time.

Hook protocol (Claude Code):
- stdin: JSON envelope w/ stop_hook_active, transcript_path.
- stdout: `{"decision": "block", "reason": ...}` blocks the stop and feeds
          `reason` back as Claude's next instruction; print nothing to let
          the turn end.
- exit code: always 0. Any error/missing data/declined gate -> exit 0,
  print nothing. Never crash the session.

LOOP GUARD — do not remove. Blocking the stop means Claude works on and
hits Stop again, with stop_hook_active set on that second pass. Ignore it
and the session can never end.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# A prompt, not config. Keep it short; it is injected on every turn.
RECAP_INSTRUCTION = (
    "Type a clean recap. Keep it short, light, and plain — a few sentences "
    "of what changed and what it means, not a report. Write for someone who "
    "has not read the code: no file paths, no function or variable names, no "
    "line numbers, no code blocks, and assume nothing about what they already "
    "know of the internals. Skip the caveats and next-steps unless something "
    "is genuinely broken or unfinished. If they want the detail, they will ask."
)


def _log(message: str) -> None:
    """Append one audit line. Logging must never break the hook."""
    path = os.environ.get("CLEAN_RECAP_LOG") or str(
        Path.home() / ".claude" / "clean-recap.log"
    )
    try:
        stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{stamp} {message}\n")
    except OSError:
        pass


def _current_model(transcript_path: Path) -> str:
    """The model of the last main-agent reply, or "-" if there is none.

    Subagent (isSidechain) replies do not count: a delegate running on
    another model must not decide whether this session gets a recap.
    """
    lines = transcript_path.read_text(encoding="utf-8", errors="replace")
    for line in reversed(lines.splitlines()):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("isSidechain"):
            continue
        if entry.get("type") == "assistant":
            return entry.get("message", {}).get("model") or "-"
    return "-"


def main() -> int:
    payload = json.loads(sys.stdin.read())

    if payload.get("stop_hook_active"):
        _log("fired  stop_hook_active=true -> stand down (recap already written)")
        return 0

    transcript = payload.get("transcript_path") or ""
    if not transcript or not Path(transcript).is_file():
        _log("fired  no readable transcript_path -> allow")
        return 0

    pattern = os.environ.get("CLEAN_RECAP_MODEL_PATTERN") or "opus-5|fable"
    model = _current_model(Path(transcript))

    if not re.search(pattern, model, re.IGNORECASE):
        _log(
            f"fired  model={model} -> allow "
            f"(model does not match '{pattern}')"
        )
        return 0

    _log(f"fired  model={model} -> BLOCK (requesting recap)")
    print(json.dumps({"decision": "block", "reason": RECAP_INSTRUCTION}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # ponytail: fail-safe per hook contract — any error means exit 0,
        # silent. A hook that cannot run must never wedge the session.
        sys.exit(0)
