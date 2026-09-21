#!/usr/bin/env python3
"""Flag context pressure before a harness compacts the session.

Claude and Codex run this on UserPromptSubmit in context mode. Copilot runs it
on agentStop in stop mode because its command UserPromptSubmit hooks cannot
inject context.

This file is the only copy. Every harness reaches it through a plugin manifest
in this repository, so a per-machine copy under a user's home directory is a
fork waiting to happen, not an install step. Point the wiring at the plugin.

Reads the session transcript path from stdin JSON, sums the last recorded
`message.usage` input/cache token counts as a proxy for current context
size, and injects an instruction into the agent's context the first time
that size crosses the 200k soft limit (and again every +50k band after,
so the nag does not repeat every turn within the same band).

Rationale: the agent cannot self-measure its own context size. This hook
measures it externally from the transcript and injects a instruction to
offer a handoff at the next natural stopping point.

Hook protocol:
- stdin: a Claude-compatible snake_case or Copilot camelCase JSON envelope.
- stdout in context mode: text injected into the current turn.
- stdout in stop mode: a JSON block decision that requests one continuation.
- exit code: always 0. Any error/missing data -> exit 0, print nothing.
  Never crash the session.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

THRESHOLD = 200_000
BAND = 50_000


def _last_usage_tokens(transcript_path: Path) -> int | None:
    """Read the latest Claude or Codex context usage from a transcript."""
    last_tokens: int | None = None
    with transcript_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            claude_usage = obj.get("message", {}).get("usage")
            if claude_usage:
                last_tokens = (
                    claude_usage.get("input_tokens", 0)
                    + claude_usage.get("cache_read_input_tokens", 0)
                    + claude_usage.get("cache_creation_input_tokens", 0)
                )
                continue

            payload = obj.get("payload", {})
            if (
                obj.get("type") == "event_msg"
                and payload.get("type") == "token_count"
            ):
                usage = payload.get("info", {}).get("last_token_usage", {})
                if usage:
                    last_tokens = usage.get("input_tokens", 0)
            elif obj.get("type") == "token_usage_record":
                usage = payload.get("usage", {})
                if usage:
                    last_tokens = usage.get("input_tokens", 0)

    if last_tokens is not None:
        return last_tokens

    # Copilot exposes a transcript path but does not document token usage in
    # that file. Its UTF-8 byte count divided by four is a conservative signal
    # that still comes from outside the model.
    return transcript_path.stat().st_size // 4


def _state_file(session_id: str, state_directory: Path | None = None) -> Path:
    """Per-session band tracker in the OS temp dir."""
    # ponytail: minimal sanitize, only used as a filename fragment
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    safe_id = safe_id or "unknown"
    directory = state_directory or Path(tempfile.gettempdir())
    return directory / f"dotai-handoff-flag-{safe_id}.txt"


def _read_last_band(state_file: Path) -> int:
    """Last-flagged band, or -1 if no valid state recorded yet."""
    if not state_file.exists():
        return -1
    try:
        return int(state_file.read_text().strip())
    except ValueError:
        return -1


def _build_message(tokens: int) -> str:
    """Injection text for a new band crossing."""
    k = round(tokens / 1000)
    return (
        f"[handoff-token-flag] Main session context ~{k}k tokens, past the "
        "200k soft limit. At the next natural stopping point, suggest "
        "writing a handoff doc via the `handoff` skill (follow that skill's "
        "location rules: `.handoffs/` at the project root, never /tmp) and "
        "closing this session; if the user agrees, report the "
        ".handoffs/handoff_*.md path as the first line. Do not start major "
        "new work. Do not silently rely on auto-compact."
    )


def _response_for_crossing(
    tokens: int,
    session_id: str,
    mode: str,
    state_directory: Path | None = None,
) -> str:
    if tokens < THRESHOLD:
        return ""

    band = (tokens - THRESHOLD) // BAND
    state_file = _state_file(session_id, state_directory)
    if band <= _read_last_band(state_file):
        return ""

    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(str(band))
    message = _build_message(tokens)
    if mode == "stop":
        return json.dumps({"decision": "block", "reason": message})
    return message


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("context", "stop"), default="context")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    payload = json.loads(sys.stdin.read())
    transcript_path_value = payload.get("transcript_path") or payload.get(
        "transcriptPath"
    )
    transcript_path = Path(transcript_path_value)
    session_id = (
        payload.get("session_id") or payload.get("sessionId") or "unknown"
    )

    if options.mode == "stop" and (
        payload.get("stop_hook_active") or payload.get("stopHookActive")
    ):
        return 0

    tokens = _last_usage_tokens(transcript_path)
    if tokens is None:
        return 0

    response = _response_for_crossing(tokens, session_id, options.mode)
    if response:
        print(response)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # ponytail: fail-safe per hook contract — any error means exit 0,
        # silent. Never crash the session over a token-count nudge.
        sys.exit(0)
