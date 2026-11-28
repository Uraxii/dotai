"""Detector runners for the guideline hooks.

Each runner checks file content it is given and never reads the disk copy.
A project's own tool config wins over the defaults here: when one exists
the tool runs with it, and a rule the project ignores is never selected.
"""

from __future__ import annotations

import fnmatch
import functools
import json
import os
import re
import shutil
import subprocess
import time
import tomllib
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import NamedTuple

from code_quality import check_source

RUNNER_TIMEOUT_S = 1.5
DEFAULT_LINE_LENGTH = 80
# In ruff's order of precedence within one directory.
RUFF_CONFIG_NAMES = (".ruff.toml", "ruff.toml", "pyproject.toml")
ESLINT_CONFIG_PATTERN = re.compile(
    r"^(eslint\.config\.[cm]?[jt]s|\.eslintrc(\.(js|cjs|json|ya?ml))?)$"
)
IGNORE_KEYS = ("ignore", "extend-ignore")
SELECT_KEYS = ("select", "extend-select")
RUFF_EXTENDS_MAX = 10
EDITORCONFIG_LINE_LENGTH = re.compile(
    r"^\s*max_line_length\s*=\s*(\d+)\s*$", re.MULTILINE
)
SKIPPED_FOR_BUDGET = "budget"
ESLINT_ERROR = 2


class Finding(NamedTuple):
    tool: str
    code: str
    line: int
    blocks: bool = True
    """False when the project's own config makes this finding a warning."""


class RunResult(NamedTuple):
    findings: tuple[Finding, ...] | None
    problem: str


class Target(NamedTuple):
    content: str
    path: Path
    codes: frozenset[str]
    root: Path


class Runner(NamedTuple):
    tool: str
    languages: frozenset[str]
    probe: tuple[str, ...]
    expect: str
    run: Callable[[str, Target], RunResult] | None


def glob_matches(rel: str, glob: str) -> bool:
    return fnmatch.fnmatchcase(rel, glob) or fnmatch.fnmatchcase(
        rel, "*/" + glob
    )


def parents_within(path: Path, root: Path) -> Iterator[Path]:
    """Yield the file's directory, then each parent, ending at root."""
    for directory in path.parents:
        yield directory
        if directory == root:
            return


@functools.cache
def ruff_lint_tables(config: Path) -> tuple[Mapping[str, object], ...]:
    """Return the config's ruff tables, or () when it has no ruff section."""
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ({},)
    if config.name == "pyproject.toml":
        tool = data.get("tool")
        section = tool.get("ruff") if isinstance(tool, dict) else None
        if not isinstance(section, dict):
            return ()
        data = section
    lint = data.get("lint")
    return (data, lint) if isinstance(lint, dict) else (data,)


def ruff_config(path: Path, root: Path) -> Path | None:
    for directory in parents_within(path, root):
        for name in RUFF_CONFIG_NAMES:
            candidate = directory / name
            if candidate.is_file() and ruff_lint_tables(candidate):
                return candidate
    return None


def as_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def ruff_chain(config: Path) -> Iterator[Path]:
    """The config, then each config it `extend`s, as ruff loads them."""
    seen: set[Path] = set()
    current: Path | None = config
    while current is not None and current not in seen and (
        len(seen) < RUFF_EXTENDS_MAX
    ):
        seen.add(current)
        yield current
        tables = ruff_lint_tables(current)
        extend = tables[0].get("extend") if tables else None
        current = (
            (current.parent / extend).resolve()
            if isinstance(extend, str) else None
        )


def ruff_tables(config: Path) -> Iterator[Mapping[str, object]]:
    for linked in ruff_chain(config):
        yield from ruff_lint_tables(linked)


def selected_by(code: str, selectors: frozenset[str]) -> bool:
    return any(
        selector == "ALL" or code.startswith(selector)
        for selector in selectors
    )


def matches_code(tool: str, found: str, selector: str) -> bool:
    """Ruff codes match by prefix (`PTH` selects PTH123); other tools'
    rule ids match exactly."""
    return found.startswith(selector) if tool == "ruff" else found == selector


def line_length(root: Path) -> int:
    try:
        text = (root / ".editorconfig").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return DEFAULT_LINE_LENGTH
    match = EDITORCONFIG_LINE_LENGTH.search(text)
    return int(match.group(1)) if match else DEFAULT_LINE_LENGTH


def run_tool(
    argv: list[str], target: Target
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            argv, input=target.content, cwd=target.root, text=True,
            capture_output=True, check=False, timeout=RUNNER_TIMEOUT_S,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


NOT_UNDERSTOOD = RunResult(None, "output was not understood")
RUFF_EXCLUDED = "Ignored path via"
RUFF_EXCLUDED_PROBLEM = (
    "skips this file under its exclude settings "
    "(the project's or ruff's defaults)"
)


def wanted(tool: str, code: object, codes: frozenset[str]) -> bool:
    return isinstance(code, str) and any(
        matches_code(tool, code, selector) for selector in codes
    )


def run_code_quality(executable: str, target: Target) -> RunResult:
    try:
        found = check_source(target.content, target.path)
    except (SyntaxError, ValueError):
        return RunResult(None, f"could not parse {target.path.name}")
    return RunResult(tuple(
        Finding("code_quality", finding.rule, finding.line)
        for finding in found if finding.rule in target.codes
    ), "")


def ruff_arguments(target: Target) -> list[str]:
    """Select the guideline codes the project's config does not name, so a
    code it selects or ignores, in any config it extends, is ruff's call."""
    codes = ",".join(sorted(target.codes))
    config = ruff_config(target.path, target.root)
    if config is not None:
        tables = list(ruff_tables(config))
        named = frozenset(
            selector for table in tables
            for key in (*SELECT_KEYS, *IGNORE_KEYS)
            for selector in as_strings(table.get(key))
        )
        added = sorted(
            code for code in target.codes if not selected_by(code, named)
        )
        # A selector on the command line beats the config, so the config's
        # narrower ignores under an added code go on the command line too,
        # unless the config selects that rule again at least as narrowly.
        selects = [
            selector for table in tables for key in SELECT_KEYS
            for selector in as_strings(table.get(key))
        ]
        narrower = sorted(
            selector for table in tables for key in IGNORE_KEYS
            for selector in as_strings(table.get(key))
            if any(selector.startswith(code) for code in added)
            and not any(again.startswith(selector) for again in selects)
        )
        preview = any("preview" in table for table in tables)
        return [
            "--verbose", "--force-exclude",
            *([] if preview else ["--preview"]),
            *(["--extend-select", ",".join(added)] if added else []),
            *(["--extend-ignore", ",".join(narrower)] if narrower else []),
        ]
    length = str(line_length(target.root))
    return [
        "--isolated", "--preview", "--line-length", length, "--select", codes,
    ]


def run_ruff(executable: str, target: Target) -> RunResult:
    process = run_tool([
        executable, "check", *ruff_arguments(target), "--output-format",
        "json", "--stdin-filename", str(target.path), "-",
    ], target)
    if process is None:
        return RunResult(None, f"timed out after {RUNNER_TIMEOUT_S} s")
    if RUFF_EXCLUDED in process.stderr:
        return RunResult(None, RUFF_EXCLUDED_PROBLEM)
    try:
        rows = json.loads(process.stdout)
        findings = tuple(
            Finding("ruff", row["code"], int(row["location"]["row"]))
            for row in rows if wanted("ruff", row["code"], target.codes)
        )
        unparsed = any(row["code"] in (None, "invalid-syntax") for row in rows)
    except (ValueError, TypeError, KeyError):
        return NOT_UNDERSTOOD
    if unparsed:
        return RunResult(None, f"could not parse {target.path.name}")
    return RunResult(findings, "")


def package_eslint_config(package: Path) -> bool:
    """True when package.json holds an eslintConfig (legacy config)."""
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and "eslintConfig" in data


def eslint_config(path: Path, root: Path) -> bool:
    return any(
        ESLINT_CONFIG_PATTERN.match(entry.name) or (
            entry.name == "package.json" and package_eslint_config(entry)
        )
        for directory in parents_within(path, root)
        if directory.is_dir()
        for entry in directory.iterdir()
    )


def run_eslint(executable: str, target: Target) -> RunResult:
    if not eslint_config(target.path, target.root):
        return RunResult(None, "has no project config")
    process = run_tool([
        executable, "--stdin", "--stdin-filename", str(target.path),
        "-f", "json",
    ], target)
    if process is None:
        return RunResult(None, f"timed out after {RUNNER_TIMEOUT_S} s")
    try:
        messages = json.loads(process.stdout)[0]["messages"]
        unparsed = any(message.get("fatal") for message in messages)
        findings = tuple(
            Finding(
                "eslint", message["ruleId"], int(message["line"]),
                blocks=message.get("severity") == ESLINT_ERROR,
            )
            for message in messages
            if wanted("eslint", message.get("ruleId"), target.codes)
        )
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        return NOT_UNDERSTOOD
    if unparsed:
        return RunResult(None, f"could not parse {target.path.name}")
    return RunResult(findings, "")


SCRIPT_LANGUAGES = frozenset({"typescript", "javascript"})
RUNNERS: dict[str, Runner] = {
    runner.tool: runner for runner in (
        Runner("code_quality", frozenset({"python"}), (), "",
               run_code_quality),
        Runner("ruff", frozenset({"python"}), ("--version",), r"^ruff \d",
               run_ruff),
        Runner("eslint", SCRIPT_LANGUAGES, ("--version",), r"^v\d",
               run_eslint),
        *(
            Runner(tool, frozenset(languages), (), "", None)
            for tool, languages in (
                ("mypy", {"python"}), ("pylint", {"python"}),
                ("complexipy", {"python"}), ("lizard", ()),
                ("opengrep", ()), ("semgrep", ()),
                ("gdlint", {"gdscript"}), ("godot", {"gdscript"}),
                ("roslyn", {"csharp"}), ("stylecop", {"csharp"}),
                ("tsc", {"typescript"}),
            )
        ),
    )
}


def runs_on(tool: str, language: str) -> bool:
    """False when the tool checks only other languages. A tool with no
    runner yet still "runs" on its languages, so its notice is shown."""
    runner = RUNNERS.get(tool)
    return runner is None or not runner.languages or (
        language in runner.languages
    )


def locate(tool: str, root: Path) -> str | None:
    """Find an installed tool: the project's own copy first, then PATH.
    `which` adds Windows extensions, so npm's eslint.cmd is found there."""
    local = os.pathsep.join(
        str(root / folder)
        for folder in ("node_modules/.bin", ".venv/bin", ".venv/Scripts")
    )
    return shutil.which(tool, path=local) or shutil.which(tool)


def probe(runner: Runner, root: Path) -> tuple[str, str]:
    """Return (executable, problem); problem is empty when usable."""
    if runner.run is None:
        return "", "has no runner yet"
    if not runner.probe:
        return runner.tool, ""
    executable = locate(runner.tool, root)
    if executable is None:
        return "", "is not installed"
    try:
        process = subprocess.run(
            [executable, *runner.probe], capture_output=True, text=True,
            check=False, timeout=RUNNER_TIMEOUT_S, cwd=root,
        )
    except subprocess.TimeoutExpired:
        return "", f"timed out after {RUNNER_TIMEOUT_S} s"
    except OSError:
        return "", "is not installed"
    if not re.search(runner.expect, process.stdout):
        return "", "is not the expected program"
    return executable, ""


class Detection(NamedTuple):
    """One request to run tools on one file's content before a deadline."""
    target: Target
    codes_by_tool: Mapping[str, frozenset[str]]
    deadline: float
    probes: dict[str, list[str]]


def run_one(tool: str, detection: Detection) -> RunResult:
    runner = RUNNERS.get(tool)
    if runner is None:
        return RunResult(None, "has no runner yet")
    if time.monotonic() >= detection.deadline:
        return RunResult(None, SKIPPED_FOR_BUDGET)
    executable, problem = detection.probes.get(tool) or probe(
        runner, detection.target.root
    )
    if not problem:
        detection.probes[tool] = [executable, problem]
    if problem or runner.run is None:
        return RunResult(None, problem)
    target = detection.target._replace(codes=detection.codes_by_tool[tool])
    return runner.run(executable, target)


def detect(detection: Detection) -> dict[str, RunResult]:
    """Run each tool in order; code_quality first, it is the fastest."""
    order = sorted(detection.codes_by_tool, key=lambda t: t != "code_quality")
    return {tool: run_one(tool, detection) for tool in order}
