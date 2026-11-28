#!/usr/bin/env python3
"""Flag Python comprehensions that should be explicit for loops.

Usage: code_quality.py PATH...

CQ001: comprehension with more than one for clause.
CQ002: call that takes a call as argument inside a comprehension.
Exit status: 0 clean, 1 findings, 2 missing path or unparseable file.
"""

from __future__ import annotations

import ast
import os
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

SKIPPED_DIRS = frozenset({".git", "node_modules", ".venv", "venv"})
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
MAX_FOR_CLAUSES = 1
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_INPUT_ERROR = 2


class Finding(NamedTuple):
    path: Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule} {self.message}"


def has_call_argument(call: ast.Call) -> bool:
    arguments = [*call.args, *(keyword.value for keyword in call.keywords)]
    unstarred = [
        argument.value if isinstance(argument, ast.Starred) else argument
        for argument in arguments
    ]
    return any(isinstance(argument, ast.Call) for argument in unstarred)


def check_source(source: str, path: Path) -> list[Finding]:
    """Return findings for one module; raise SyntaxError if unparseable."""
    findings = []
    nested_calls: set[ast.Call] = set()
    tree = ast.parse(source.removeprefix("\ufeff"), str(path))
    for node in ast.walk(tree):
        if not isinstance(node, COMPREHENSIONS):
            continue
        clauses = len(node.generators)
        if clauses > MAX_FOR_CLAUSES:
            findings.append(Finding(
                path, node.lineno, "CQ001",
                f"comprehension has {clauses} for-clauses (limit "
                f"{MAX_FOR_CLAUSES}); rewrite as an explicit for loop",
            ))
        nested_calls.update(
            inner for inner in ast.walk(node)
            if isinstance(inner, ast.Call) and has_call_argument(inner)
        )
    for call in nested_calls:
        findings.append(Finding(
            path, call.lineno, "CQ002",
            "call takes a call as argument inside a comprehension; bind the "
            "inner result to a name in an explicit for loop",
        ))
    return sorted(findings)


def python_files(target: Path) -> Iterator[Path]:
    if target.is_file():
        yield target
        return
    for root, dirs, files in os.walk(target):
        dirs[:] = sorted(name for name in dirs if name not in SKIPPED_DIRS)
        python_names = sorted(name for name in files if name.endswith(".py"))
        yield from (Path(root) / name for name in python_names)


def main(targets: Sequence[str]) -> int:
    if not targets:
        print("usage: code_quality.py PATH...", file=sys.stderr)
        return EXIT_INPUT_ERROR
    status = EXIT_CLEAN
    for target in map(Path, targets):
        if not target.exists():
            print(f"{target}: no such file or directory", file=sys.stderr)
            status = EXIT_INPUT_ERROR
            continue
        for path in python_files(target):
            try:
                findings = check_source(path.read_text(encoding="utf-8"), path)
            except (OSError, SyntaxError, ValueError) as error:
                print(f"{path}: cannot parse: {error}", file=sys.stderr)
                status = EXIT_INPUT_ERROR
                continue
            if findings:
                print(*findings, sep="\n")
                status = max(status, EXIT_FINDINGS)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
