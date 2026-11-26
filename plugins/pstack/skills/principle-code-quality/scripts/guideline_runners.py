"""Detector runners for the guideline hooks.

Each runner checks file content it is given and never reads the disk copy.
A project's own tool config wins over the defaults here: when one exists
the tool runs with it, and a rule the project ignores is never selected.
"""

from __future__ import annotations

import fnmatch
import functools
import json
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
PER_FILE_KEYS = ("per-file-ignores", "extend-per-file-ignores")
EDITORCONFIG_LINE_LENGTH = re.compile(
    r"^\s*max_line_length\s*=\s*(\d+)\s*$", re.MULTILINE
)
SKIPPED_FOR_BUDGET = "budget"


class Finding(NamedTuple):
    tool: str
    code: str
    line: int


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


def ruff_ignored(path: Path, root: Path) -> frozenset[str]:
    """Rule selectors the project's ruff config ignores for this file."""
    config = ruff_config(path, root)
    if config is None:
        return frozenset()
    rel = path.relative_to(config.parent).as_posix()
    ignored: set[str] = set()
    for table in ruff_lint_tables(config):
        for key in IGNORE_KEYS:
            ignored.update(as_strings(table.get(key)))
        for key in PER_FILE_KEYS:
            per_file = table.get(key)
            if not isinstance(per_file, dict):
                continue
            for glob, codes in per_file.items():
                if glob_matches(rel, str(glob)):
                    ignored.update(as_strings(codes))
    return frozenset(ignored)


def project_disables(tool: str, code: str, path: Path, root: Path) -> bool:
    """True when the project's own config turns this detector off."""
    if tool != "ruff":
        # shortcut: only ruff's ignore lists are read, add a reader per
        # tool when another one stores them in a format stdlib can parse.
        return False
    return any(
        selector == "ALL" or code.startswith(selector)
        for selector in ruff_ignored(path, root)
    )


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


def wanted(code: object, codes: frozenset[str]) -> bool:
    return isinstance(code, str) and any(
        code.startswith(selector) for selector in codes
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
    codes = ",".join(sorted(target.codes))
    if ruff_config(target.path, target.root) is not None:
        return ["--verbose", "--force-exclude", "--extend-select", codes]
    length = str(line_length(target.root))
    return ["--isolated", "--line-length", length, "--select", codes]


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
            for row in rows if wanted(row["code"], target.codes)
        )
        unparsed = any(row["code"] in (None, "invalid-syntax") for row in rows)
    except (ValueError, TypeError, KeyError):
        return NOT_UNDERSTOOD
    if unparsed:
        return RunResult(None, f"could not parse {target.path.name}")
    return RunResult(findings, "")


def eslint_config(path: Path, root: Path) -> bool:
    return any(
        ESLINT_CONFIG_PATTERN.match(entry.name)
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
            Finding("eslint", message["ruleId"], int(message["line"]))
            for message in messages
            if wanted(message.get("ruleId"), target.codes)
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
            Runner(tool, frozenset(), (), "", None)
            for tool in (
                "mypy", "pylint", "lizard", "complexipy", "opengrep",
                "semgrep", "gdlint", "roslyn", "stylecop", "godot", "tsc",
            )
        ),
    )
}


def locate(tool: str, root: Path) -> str | None:
    """Find an installed tool: the project's own copy first, then PATH."""
    for local in ("node_modules/.bin", ".venv/bin"):
        candidate = root / local / tool
        if candidate.is_file():
            return str(candidate)
    return shutil.which(tool)


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
    if not problem.startswith("timed out"):
        detection.probes[tool] = [executable, problem]
    if problem or runner.run is None:
        return RunResult(None, problem)
    target = detection.target._replace(codes=detection.codes_by_tool[tool])
    return runner.run(executable, target)


def detect(detection: Detection) -> dict[str, RunResult]:
    """Run each tool in order; code_quality first, it is the fastest."""
    order = sorted(detection.codes_by_tool, key=lambda t: t != "code_quality")
    return {tool: run_one(tool, detection) for tool in order}
