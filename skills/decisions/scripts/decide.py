#!/usr/bin/env python3
"""Append-only decision log: one row per settled decision, per project.

The newest row for a topic is the decision in force, so nothing is ever
edited and nothing can go stale. Superseding a decision means appending a
newer row under the same topic. Examples:

    decide.py record api-auth "session cookies" "simpler for one client" \\
        "commit 9f1c2ab"
    decide.py now
    decide.py log api-auth
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = ("ts", "topic", "decision", "why", "evidence")
LOG_NAME = ".decisions.tsv"
# A leading =, +, - or @ makes a spreadsheet treat the cell as a formula.
FORMULA_LEADS = ("=", "+", "-", "@")
COLUMN_GAP = "  "


def repo_root() -> Path | None:
    """The git work tree containing the current directory, if any."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if done.returncode != 0:
        return None
    return Path(done.stdout.strip())


def default_log() -> Path:
    return (repo_root() or Path.cwd()) / LOG_NAME


def clean(value: str) -> str:
    """Flatten a cell to one line and defuse spreadsheet formulas."""
    cell = value.replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return f"'{cell}" if cell.startswith(FORMULA_LEADS) else cell


def ignore_in_git(path: Path) -> None:
    """Add the log to .gitignore when it sits inside a repo."""
    root = repo_root()
    if root is None:
        return
    try:
        entry = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return
    gitignore = root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""
    if entry in existing.splitlines():
        return
    lead = "\n" if existing and not existing.endswith("\n") else ""
    with gitignore.open("a", encoding="utf-8") as handle:
        handle.write(f"{lead}{entry}\n")


def record(path: Path, cells: list[str]) -> None:
    """Append one decision row, writing the header on first use."""
    topic, decision = cells[0].strip(), cells[1].strip()
    if not topic or not decision:
        sys.exit("a decision needs both a topic and a decision, one line each")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8") as handle:
        if fresh:
            handle.write("\t".join(COLUMNS) + "\n")
        handle.write("\t".join([stamp, *(clean(c) for c in cells)]) + "\n")
    ignore_in_git(path)
    print(path)


def read_rows(path: Path) -> list[list[str]]:
    """Every recorded row, oldest first, each padded to five cells."""
    if not path.exists():
        sys.exit(f"no decision log at {path}; record one first")
    rows = [
        line.split("\t")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if rows and rows[0][: len(COLUMNS)] == list(COLUMNS):
        rows = rows[1:]
    width = len(COLUMNS)
    return [(row + [""] * width)[:width] for row in rows]


def render(rows: list[list[str]]) -> None:
    table = [list(COLUMNS), *rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(COLUMNS))]
    for row in table:
        cells = (cell.ljust(width) for cell, width in zip(row, widths))
        print(COLUMN_GAP.join(cells).rstrip())


def show_now(path: Path) -> None:
    """One row per topic: the decision in force right now, newest first."""
    rows = read_rows(path)
    if not rows:
        sys.exit(f"no decisions recorded yet in {path}")
    in_force = {row[1]: row for row in rows}
    render(sorted(in_force.values(), key=lambda row: row[0], reverse=True))


def show_log(path: Path, topic: str) -> None:
    """Every row for one topic, oldest first, so the chain reads forward."""
    rows = [row for row in read_rows(path) if row[1] == topic]
    if not rows:
        sys.exit(f"no decisions recorded for topic '{topic}' in {path}")
    render(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record and read a project's settled decisions.",
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    new = verbs.add_parser("record", help="append one decision")
    for name, helptext in (
        ("topic", "stable key grouping one decision chain, slug-shaped"),
        ("decision", "what was chosen, one line"),
        ("why", "the reason in plain words, one line"),
        ("evidence", "a pointer: commit SHA, PR number, file:line, path"),
    ):
        new.add_argument(name, help=helptext)

    current = verbs.add_parser("now", help="the decision in force per topic")

    chain = verbs.add_parser("log", help="one topic's decisions over time")
    chain.add_argument("topic", help="the topic to walk")

    for verb in (new, current, chain):
        verb.add_argument(
            "file", nargs="?", help=f"log file (default: <repo>/{LOG_NAME})"
        )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    path = Path(args.file) if args.file else default_log()
    if args.verb == "record":
        record(path, [args.topic, args.decision, args.why, args.evidence])
    elif args.verb == "now":
        show_now(path)
    else:
        show_log(path, args.topic)


if __name__ == "__main__":
    main()
