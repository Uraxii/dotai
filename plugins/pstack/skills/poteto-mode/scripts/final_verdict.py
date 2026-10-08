"""Print the bead comment for the last verdict in a Codex review message.

Usage: final_verdict.py <last-message.md> <sha>

The verdict is the last `verdict: pass` or `verdict: fail` line, indented or
not. The reason is the first `reason:` line after it. Prints
`verdict <value> at <sha>: <reason>` and exits 0. Exits 1 with no output when
the message has no verdict line or no reason after the last one.
"""

from __future__ import annotations

import re
import sys

VERDICT = re.compile(r"^\s*verdict:\s*(pass|fail)\s*$")
REASON = re.compile(r"^\s*reason:\s*(\S.*?)\s*$")


def final_verdict(message: str) -> tuple[str, str] | None:
    lines = message.splitlines()
    last = max((i for i, line in enumerate(lines) if VERDICT.match(line)), default=None)
    if last is None:
        return None
    for line in lines[last + 1 :]:
        reason = REASON.match(line)
        if reason:
            return VERDICT.match(lines[last]).group(1), reason.group(1)
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: final_verdict.py <last-message.md> <sha>", file=sys.stderr)
        return 2
    path, sha = argv
    with open(path, encoding="utf-8") as handle:
        found = final_verdict(handle.read())
    if found is None:
        return 1
    verdict, reason = found
    print(f"verdict {verdict} at {sha}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
