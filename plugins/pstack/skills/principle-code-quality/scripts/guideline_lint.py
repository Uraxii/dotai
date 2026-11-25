#!/usr/bin/env python3
"""Check a folder of guideline files against the frontmatter rules.

Usage: guideline_lint.py [--parse-only] [DIRECTORY]

DIRECTORY defaults to the skill's guidelines folder. --parse-only reports
only files the hooks would skip. Prints one line per problem.
Exit status: 0 clean, 1 problems.
"""

from __future__ import annotations

import sys
import tomllib
from collections import Counter
from collections.abc import Iterator, Sequence
from pathlib import Path

from guideline_files import Guideline, GuidelineError, parse_guideline
from guideline_runners import RUNNERS

SKILL = Path(__file__).resolve().parent.parent
MAX_BODY_LINES = 4
MOTIVATING_ID = "py.comprehension.one-for"
MOTIVATING_WORDS = ("for", "loop")


def known_languages() -> tuple[frozenset[str], list[str]]:
    """Return the language ids and a problem per doubly mapped extension."""
    tables = tomllib.loads((SKILL / "languages.toml").read_text("utf-8"))
    counts = Counter(
        extension for table in tables.values()
        for extension in table["extensions"]
    )
    problems = [
        f"languages.toml: extension {extension} maps to two languages"
        for extension, count in sorted(counts.items()) if count > 1
    ]
    return frozenset(tables), problems


def own_problems(
    name: str, guideline: Guideline, languages: frozenset[str]
) -> Iterator[str]:
    """Problems that one file shows without looking at the others."""
    if name != guideline.id.replace(".", "-") + ".md":
        yield f"file name does not match id {guideline.id}"
    for language in sorted(guideline.languages - languages):
        yield f"unknown language {language}"
    contextual = guideline.scope == "contextual"
    if contextual and not (guideline.detectors or guideline.keywords):
        yield "contextual guideline has no detector and no keyword"
    if contextual and guideline.severity == "block" and not guideline.detectors:
        yield "block guideline has no detector"
    for tool, _ in guideline.detectors:
        if tool not in RUNNERS:
            yield f"detector tool {tool} has no runner table entry"
    if any(keyword != keyword.lower() for keyword in guideline.keywords):
        yield "keywords must be lowercase"
    if len(guideline.body.splitlines()) > MAX_BODY_LINES:
        yield f"body is longer than {MAX_BODY_LINES} lines"
    if guideline.id == MOTIVATING_ID and not all(
        word in guideline.body for word in MOTIVATING_WORDS
    ):
        yield "body must name `for` and `loop`"


def shared_problems(parsed: dict[str, Guideline]) -> Iterator[str]:
    """Problems between files: a repeated id or a repeated detector."""
    owners: dict[str, str] = {}
    for name, guideline in parsed.items():
        keys = [f"id {guideline.id}"] + [
            f"detector {tool}:{code}" for tool, code in guideline.detectors
        ]
        for key in keys:
            if key in owners:
                yield f"{name}: {key} is also in {owners[key]}"
            owners.setdefault(key, name)


def lint(directory: Path, parse_only: bool) -> list[str]:
    languages, extension_problems = known_languages()
    problems: list[str] = []
    parsed: dict[str, Guideline] = {}
    for path in sorted(directory.glob("*.md")):
        try:
            parsed[path.name] = parse_guideline(path.read_text("utf-8"))
        except (GuidelineError, ValueError) as error:
            problems.append(f"{path.name}: {error}")
    if parse_only:
        return problems
    for name, guideline in parsed.items():
        problems += [
            f"{name}: {problem}"
            for problem in own_problems(name, guideline, languages)
        ]
    return extension_problems + problems + list(shared_problems(parsed))


def main(arguments: Sequence[str]) -> int:
    parse_only = "--parse-only" in arguments
    paths = [argument for argument in arguments if argument != "--parse-only"]
    directory = Path(paths[0]) if paths else SKILL / "guidelines"
    if not directory.is_dir():
        print(f"{directory}: not a directory", file=sys.stderr)
        return 1
    problems = lint(directory, parse_only)
    if problems:
        print(*problems, sep="\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
