#!/usr/bin/env python3
"""Append one well-formed row to a show-me-your-work decision log (TSV).

    log_decision.py <logfile> <phase> <decision> <why> <evidence> <result>

Python standard library only, forever. No pip dependency.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["clean", "append_row", "main"]

USAGE = ("usage: log_decision.py <logfile> <phase> <decision> <why> "
         "<evidence> <result>")
COLUMNS = ("ts", "phase", "decision", "why", "evidence", "result")
CELL_COUNT = len(COLUMNS) - 1
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ROW_BREAKING = str.maketrans("\t\n\r", "   ")
FORMULA_LEADS = ("=", "+", "-", "@")
FORMULA_GUARD = "'"


def clean(value: str) -> str:
    """Flatten `value` into one cell no spreadsheet will execute.

    A leading `=`, `+`, `-` or `@` gains a single quote. This log is meant
    to be opened in a spreadsheet and its cells carry text an attacker
    chooses (PR titles, filenames, generated output), so the guard is the
    difference between reading a row and running it.
    """
    flat = value.translate(ROW_BREAKING)
    if flat.startswith(FORMULA_LEADS):
        return FORMULA_GUARD + flat
    return flat


def append_row(logfile: Path, cells: list[str], stamped_at: datetime) -> None:
    """Append one cleaned row, writing the header when `logfile` is new."""
    logfile.parent.mkdir(parents=True, exist_ok=True)
    if not logfile.is_file():
        logfile.write_text("\t".join(COLUMNS) + "\n", encoding="utf-8")
    row = [stamped_at.strftime(TIMESTAMP_FORMAT)] + [clean(c) for c in cells]
    with logfile.open("a", encoding="utf-8") as stream:
        stream.write("\t".join(row) + "\n")


def main(argv: list[str]) -> int:
    """Append one row, or print the usage line and fail on a bad arg count."""
    if len(argv) != CELL_COUNT + 1:
        print(USAGE, file=sys.stderr)
        return 1
    append_row(Path(argv[0]), argv[1:], datetime.now(timezone.utc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
