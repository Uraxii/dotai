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
MODULE_SUFFIXES = ("", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".json")
CONFIG_MODULES_MAX = 50
QUOTED = re.compile(r"""['"]([^'"\n]{1,200})['"]""")
PACKAGE_NAME = re.compile(r"^(@[\w.-]+/)?[\w.-]+$")
# In ruff's order of precedence within one directory.
RUFF_CONFIG_NAMES = (".ruff.toml", "ruff.toml", "pyproject.toml")
ESLINT_CONFIG_PATTERN = re.compile(
    r"^(eslint\.config\.[cm]?[jt]s|\.eslintrc(\.(js|cjs|json|ya?ml))?)$"
)
FLAT_ESLINT_CONFIG = re.compile(r"^eslint\.config\.[cm]?[jt]s$")
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
    # A [lint] setting replaces the same deprecated top-level setting.
    lint = data.get("lint")
    return ({**data, **lint},) if isinstance(lint, dict) else (data,)


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
        # Ruff expands `~` and environment variables in `extend`.
        current = (
            (current.parent / os.path.expandvars(
                os.path.expanduser(extend)
            )).resolve()
            if isinstance(extend, str) else None
        )


def ruff_tables(config: Path) -> Iterator[Mapping[str, object]]:
    for linked in ruff_chain(config):
        yield from ruff_lint_tables(linked)


def ruff_live_tables(config: Path) -> list[Mapping[str, object]]:
    """The tables whose rule selectors still count: a config that sets
    `select` resets what the configs it extends selected and ignored."""
    live: list[Mapping[str, object]] = []
    for linked in ruff_chain(config):
        tables = ruff_lint_tables(linked)
        live += tables
        if any("select" in table for table in tables):
            break
    return live


def setting_tools(
    setting: Path, code: Path, language: str, root: Path, text: str | None
) -> frozenset[str]:
    """The detectors whose result for the code file can change when the
    same edit changes this other file."""
    if language == "python" and ruff_setting(setting, code, root, text):
        return frozenset({"ruff"})
    if language in SCRIPT_LANGUAGES and eslint_setting(
        setting, code, root, text
    ):
        return frozenset({"eslint"})
    return frozenset()


def ruff_setting(
    setting: Path, code: Path, root: Path, text: str | None
) -> bool:
    """A config in the Ruff chain of the code file, or a Ruff config at
    the current one or closer to the code, which Ruff would use instead."""
    config = ruff_config(code, root)
    if config is not None and setting in {
        linked.resolve() for linked in ruff_chain(config)
    }:
        return True
    if setting.name == ".editorconfig":
        return config is None and setting == root / ".editorconfig"
    if setting.name not in RUFF_CONFIG_NAMES:
        return False
    nearer = parents_within(code, config.parent if config else root)
    if config is not None and setting.parent == config.parent and (
        RUFF_CONFIG_NAMES.index(setting.name)
        > RUFF_CONFIG_NAMES.index(config.name)
    ):
        return False
    return setting.parent in list(nearer) and (
        setting.name != "pyproject.toml" or bool(ruff_lint_tables(setting))
        or "tool.ruff" in (text or "")
    )


def eslint_setting(
    setting: Path, code: Path, root: Path, text: str | None
) -> bool:
    """An ESLint config the code file uses or would use instead, the
    .eslintignore in legacy mode, or a file the config loads."""
    mode = eslint_config(code, root)
    folders = list(parents_within(code, root))
    name = setting.name
    flat_name = FLAT_ESLINT_CONFIG.match(name) is not None
    legacy_name = ESLINT_CONFIG_PATTERN.match(name) is not None or (
        name == ".eslintignore"
    ) or (name == "package.json" and (
        "eslintConfig" in (text or "") or package_eslint_config(setting)
    ))
    if mode is None:
        return (flat_name or legacy_name) and setting.parent in folders
    if mode.flat:
        if flat_name and setting.parent in list(
            parents_within(code, mode.folder)
        ):
            return True
        configs = [
            entry for entry in mode.folder.iterdir()
            if FLAT_ESLINT_CONFIG.match(entry.name)
        ]
    else:
        if legacy_name and setting.parent in folders:
            return True
        configs = [
            directory / entry for directory in folders if directory.is_dir()
            for entry in os.listdir(directory)
            if ESLINT_CONFIG_PATTERN.match(entry) or entry == "package.json"
        ]
    files, packages = config_modules(configs, root)
    return setting in files or any(
        package in setting.parents for package in packages
    )


def config_text(config: Path) -> str:
    """A config's text; of a package.json only its eslintConfig."""
    try:
        text = config.read_text(encoding="utf-8")
        if config.name == "package.json":
            data = json.loads(text)
            return json.dumps(
                data.get("eslintConfig") if isinstance(data, dict) else None
            )
    except (OSError, ValueError):
        return ""
    return text


def module_candidates(base: Path) -> list[Path]:
    """The files a relative module name can load, as Node resolves it."""
    return [
        base.with_name(base.name + suffix) for suffix in MODULE_SUFFIXES
    ] + [base / f"index{suffix}" for suffix in MODULE_SUFFIXES[1:]]


def workspace_package(name: str, start: Path, root: Path) -> Path | None:
    """The project folder of a package a config names, when the package
    is part of the project (a workspace package linked in node_modules)."""
    parts = name.split("/")
    package = "/".join(parts[:2] if name.startswith("@") else parts[:1])
    if not PACKAGE_NAME.match(package):
        return None
    shorthand = () if package.startswith("@") else (f"eslint-config-{package}",)
    for directory in parents_within(start / "_", root):
        for candidate in (package, *shorthand):
            linked = directory / "node_modules" / candidate
            if linked.is_dir():
                real = linked.resolve()
                return real if root in real.parents else None
    return None


def config_modules(
    configs: list[Path], root: Path
) -> tuple[set[Path], set[Path]]:
    """The files ESLint configs load by relative path, followed through
    those files, and the folders of workspace packages they name. Every
    quoted string counts, so a name in a rule option can add a file:
    a false match only makes a finding a warning."""
    files: set[Path] = set()
    packages: set[Path] = set()
    pending = [config.resolve() for config in configs]
    read: set[Path] = set()
    while pending and len(read) < CONFIG_MODULES_MAX:
        current = pending.pop()
        if current in read:
            continue
        read.add(current)
        files.add(current)
        for name in QUOTED.findall(config_text(current)):
            if name.startswith(("./", "../")):
                candidates = [
                    candidate.resolve()
                    for candidate in module_candidates(current.parent / name)
                ]
                files.update(candidates)
                pending += [c for c in candidates if c.is_file()]
            elif (package := workspace_package(
                name, current.parent, root
            )) is not None:
                packages.add(package)
    return files, packages


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
    argv: list[str], target: Target, cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str] | None:
    # Bytes, so the source reaches the tool as UTF-8 without the newline
    # changes of text mode on Windows.
    try:
        process = subprocess.run(
            argv, input=target.content.encode("utf-8", "surrogateescape"),
            cwd=cwd or target.root, env=env, capture_output=True,
            check=False, timeout=RUNNER_TIMEOUT_S,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    return subprocess.CompletedProcess(
        process.args, process.returncode,
        process.stdout.decode("utf-8", "replace"),
        process.stderr.decode("utf-8", "replace"),
    )


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


def ruff_ignores(rule: str, tables: list[Mapping[str, object]]) -> bool:
    """Whether the config's last word on the rule is an ignore. Ruff reads
    the extended configs first; in one config the most specific selector
    wins, and an ignore wins a tie."""
    ignored = False
    for table in reversed(tables):
        covering = [
            (0 if selector == "ALL" else len(selector), key in IGNORE_KEYS)
            for key in (*SELECT_KEYS, *IGNORE_KEYS)
            for selector in as_strings(table.get(key))
            if selector == "ALL" or rule.startswith(selector)
        ]
        if covering:
            ignored = max(covering)[1]
    return ignored


def ruff_arguments(target: Target) -> list[str]:
    """Select the guideline codes the project's config does not name, so a
    code it selects or ignores, in any config it extends, is ruff's call."""
    codes = ",".join(sorted(target.codes))
    config = ruff_config(target.path, target.root)
    if config is not None:
        tables = ruff_live_tables(config)
        named = frozenset(
            selector for table in tables
            for key in (*SELECT_KEYS, *IGNORE_KEYS)
            for selector in as_strings(table.get(key))
        )
        added = sorted(
            code for code in target.codes if not selected_by(code, named)
        )
        # A selector on the command line beats the config, so a narrower
        # rule the config ends up ignoring goes on the command line too.
        narrower = sorted({
            selector for table in tables for key in IGNORE_KEYS
            for selector in as_strings(table.get(key))
            if any(selector.startswith(code) for code in added)
            and ruff_ignores(selector, tables)
        })
        # A rule the config selects again inside such an ignore is selected
        # on the command line too, where the more specific selector wins.
        added += sorted({
            selector for table in tables for key in SELECT_KEYS
            for selector in as_strings(table.get(key))
            if any(selector.startswith(code) for code in narrower)
            and selector not in narrower
            and not ruff_ignores(selector, tables)
        })
        preview = any("preview" in table for table in ruff_tables(config))
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
        return RunResult((), RUFF_EXCLUDED_PROBLEM)
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


class EslintMode(NamedTuple):
    folder: Path
    flat: bool


def eslint_config(path: Path, root: Path) -> EslintMode | None:
    """Where and in which config mode ESLint runs, or None without a
    config. A flat config loads from the working folder, so ESLint runs
    in the nearest one. A legacy config cascades and its .eslintignore is
    read from the working folder, so it runs at the root in legacy mode,
    also when the project turns flat mode off."""
    flat_allowed = os.environ.get("ESLINT_USE_FLAT_CONFIG") != "false"
    legacy = False
    for directory in parents_within(path, root):
        names = [e.name for e in directory.iterdir()] if (
            directory.is_dir()
        ) else []
        if flat_allowed and any(
            FLAT_ESLINT_CONFIG.match(name) for name in names
        ):
            return EslintMode(directory, flat=True)
        legacy = legacy or any(
            ESLINT_CONFIG_PATTERN.match(name) or (
                name == "package.json"
                and package_eslint_config(directory / name)
            )
            for name in names
        )
    return EslintMode(root, flat=False) if legacy else None


def run_eslint(executable: str, target: Target) -> RunResult:
    mode = eslint_config(target.path, target.root)
    if mode is None:
        return RunResult(None, "has no project config")
    env = None if mode.flat else os.environ | {"ESLINT_USE_FLAT_CONFIG": "false"}
    process = run_tool([
        executable, "--stdin", "--stdin-filename", str(target.path),
        "-f", "json",
    ], target, mode.folder, env)
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


def locate(tool: str, path: Path, root: Path) -> str | None:
    """Find an installed tool: the nearest project copy at or above the
    file, as in a monorepo package, then PATH. `which` adds Windows
    extensions, so npm's eslint.cmd is found there."""
    local = os.pathsep.join(
        str(directory / folder)
        for directory in parents_within(path, root)
        for folder in ("node_modules/.bin", ".venv/bin", ".venv/Scripts")
    )
    return shutil.which(tool, path=local) or shutil.which(tool)


def probe(runner: Runner, executable: str | None, root: Path) -> tuple[str, str]:
    """Return (executable, problem); problem is empty when usable."""
    if runner.run is None:
        return "", "has no runner yet"
    if not runner.probe:
        return runner.tool, ""
    if executable is None:
        return "", "is not installed"
    try:
        process = subprocess.run(
            [executable, *runner.probe], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
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
    found = locate(tool, detection.target.path, detection.target.root)
    key = f"{tool} {found}"
    executable, problem = detection.probes.get(key) or probe(
        runner, found, detection.target.root
    )
    if not problem:
        detection.probes[key] = [executable, problem]
    if problem or runner.run is None:
        return RunResult(None, problem)
    target = detection.target._replace(codes=detection.codes_by_tool[tool])
    return runner.run(executable, target)


def detect(detection: Detection) -> dict[str, RunResult]:
    """Run each tool in order; code_quality first, it is the fastest."""
    order = sorted(detection.codes_by_tool, key=lambda t: t != "code_quality")
    return {tool: run_one(tool, detection) for tool in order}
