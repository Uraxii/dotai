#!/usr/bin/env python3
"""Regenerate references/tools.json from the binary's own MCP tools/list.

Rerun after upgrading codebase-memory-mcp.

Python standard library only, forever. No pip dependency.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

__all__ = ["run_handshake", "responses_with_id", "tool_count", "main"]

BINARY = "codebase-memory-mcp"
TIMEOUT_SEC = 20
LIST_REQUEST_ID = 2
OUTPUT_PATH = Path(__file__).parent / ".." / "references" / "tools.json"
COMPACT = (",", ":")
PROTOCOL_VERSION = "2024-11-05"
CLIENT_NAME = "dump_schemas"
CLIENT_VERSION = "0"
TIMEOUT_EXIT = 124
NOT_FOUND_EXIT = 127

HANDSHAKE = (
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                "clientInfo": {"name": CLIENT_NAME,
                               "version": CLIENT_VERSION}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": LIST_REQUEST_ID, "method": "tools/list"},
)


def run_handshake() -> subprocess.CompletedProcess[str]:
    """Speak the MCP handshake to the binary and capture its stdout.

    The binary's stderr is discarded: it carries only the `mem.init` log
    line, and this script's own output is the file it writes.
    """
    requests = "".join(
        json.dumps(message, separators=COMPACT) + "\n"
        for message in HANDSHAKE
    )
    return subprocess.run(
        [BINARY],
        capture_output=True,
        check=False,
        input=requests,
        text=True,
        timeout=TIMEOUT_SEC,
    )


def responses_with_id(stdout: str, wanted: int) -> list[dict]:
    """Parse `stdout` as one JSON message per line, keeping id `wanted`."""
    messages = [json.loads(line) for line in stdout.splitlines() if line]
    return [message for message in messages if message.get("id") == wanted]


def tool_count(responses: list[dict]) -> str:
    """The tool count for the report line, empty when nothing answered.

    An empty count is what the shell version printed when the binary sent
    no matching response, because it counted an empty file. Preserved
    rather than turned into a failure, so the two versions report alike.

    A response carrying `error` instead of `result` counts as zero tools,
    which is what `jq '.result.tools|length'` yielded on the same payload.
    A version-skewed binary answering the request it does not know is the
    case that reaches this, and it must report, not crash.
    """
    if not responses:
        return ""
    result = responses[0].get("result") or {}
    return str(len(result.get("tools") or []))


def main(argv: list[str]) -> int:
    """Rewrite tools.json and report its path and tool count."""
    with OUTPUT_PATH.open("w", encoding="utf-8") as stream:
        try:
            done = run_handshake()
        except FileNotFoundError:
            print(f"{BINARY} is not on PATH", file=sys.stderr)
            return NOT_FOUND_EXIT
        except subprocess.TimeoutExpired:
            print(f"{BINARY} answered nothing in {TIMEOUT_SEC}s",
                  file=sys.stderr)
            return TIMEOUT_EXIT
        responses = responses_with_id(done.stdout, LIST_REQUEST_ID)
        for message in responses:
            stream.write(json.dumps(message, ensure_ascii=False,
                                    separators=COMPACT) + "\n")
    if done.returncode != 0:
        return done.returncode
    print(f"wrote {OUTPUT_PATH}: {tool_count(responses)} tools")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
