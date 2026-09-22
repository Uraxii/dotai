#!/usr/bin/env python3
"""Ban machine-specific home-directory paths from every committed file.

This repository is public. A path such as `/home/<name>/project` or
`/Users/<name>/code` names a real machine, and the segment after the home
root is often a real person's account name, not a fixture. That exact
mistake reached a committed file three separate times, caught only by three
separate human reviewers after the fact, because nothing enforced it between
reviews. This script is that enforcement: it fails a path whose root is a
per-user home directory (`/home/<seg>`, `/Users/<seg>`, `/var/home/<seg>`)
unless `<seg>` is a placeholder (`<user>`, `{user}`, `${USER}`, `$USER`,
`...`) rather than an account name. `/root/...` and `/repo/...` are not
per-user home roots and are never flagged.

One run scans every file `git ls-files` tracks, not a per-plugin loop: the
three leaks landed in different trees (a skill, a hook test, and a plugin
manifest), and a loop bounded to one tree is blind to the next one.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


__all__ = ["main", "find_violations", "line_violations", "REPOSITORY_ROOT"]

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

# Root then the first path segment. Written so no alternative on its own
# spells "/home/", "/Users/", or "/var/home/": each root name only meets its
# trailing slash through the shared group, so this file never matches its
# own rule.
PATH_ROOT_RE = re.compile(r"/(?:var/home|home|Users)/([^/\\\s'\"`),;:\]]+)")

# A segment shaped like one of these carries no machine-specific
# information, even though it sits where an account name would.
PLACEHOLDER_RE = re.compile(
    r"^(?:<[^<>]+>|\$\{[^{}]+\}|\{[^{}]+\}|\$[A-Za-z_][A-Za-z0-9_]*|\.\.\.)$"
)


class Violation(NamedTuple):
    path: Path
    line_number: int
    text: str


def tracked_files(root: Path) -> list[Path]:
    listing = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [Path(line) for line in listing.splitlines() if line]


def offending_matches(line: str) -> list[str]:
    return [
        match.group(0)
        for match in PATH_ROOT_RE.finditer(line)
        if not PLACEHOLDER_RE.match(match.group(1))
    ]


def line_violations(path: Path, text: str) -> list[Violation]:
    violations = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for offending in offending_matches(line):
            violations.append(Violation(path, line_number, offending))
    return violations


def find_violations(root: Path) -> tuple[list[Violation], int]:
    """Violations across every tracked file, and how many files were read.

    A file `git ls-files` tracks but this process cannot decode as UTF-8 is
    binary and is skipped; nothing else is skipped, so a violation outside
    `plugins/` is caught the same as one inside it.
    """
    violations = []
    scanned = 0
    for relative in tracked_files(root):
        path = root / relative
        try:
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned += 1
        violations += line_violations(relative, text)
    return violations, scanned


def main(arguments: list[str] | None = None, root: Path = REPOSITORY_ROOT) -> int:
    del arguments
    violations, scanned = find_violations(root)
    for violation in violations:
        print(
            f"FAIL: {violation.path}:{violation.line_number}: {violation.text}",
            file=sys.stderr,
        )
    if violations:
        count = len(violations)
        noun = "path" if count == 1 else "paths"
        print(
            f"FAIL: {count} machine-specific home {noun} in "
            f"{scanned} files scanned. Replace the account-name segment "
            "with a placeholder such as <user>, {user}, or $USER.",
            file=sys.stderr,
        )
        return 1
    print(f"ok: no machine-specific home paths in {scanned} files scanned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
