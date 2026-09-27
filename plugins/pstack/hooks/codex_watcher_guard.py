#!/usr/bin/env python3
"""Allow Codex watcher agents only Bash calls that keep the runs-root invariants."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial


__all__ = ["guard", "main"]

REVIEWER = "reviewer-codex"
DEVELOPER = "developer-codex"
WATCHER_NAMES = frozenset({DEVELOPER, REVIEWER})
SANDBOX_BY_KIND = {REVIEWER: "read-only", DEVELOPER: "workspace-write"}
RUNS_DIR_NAME = ".agent-runs"


@dataclass(frozen=True)
class Scope:
    """The watcher kind, the directory relative paths start from, and the
    `AGENT_RUNS_DIR` root when one is configured."""

    kind: str
    cwd: str
    configured_root: str | None

    def path(self, value: str, base: str | None = None) -> str:
        return os.path.normpath(os.path.join(base or self.cwd, value))

    def check_path(
        self, value: str, *, strict: bool, role: str = "path", base: str | None = None
    ) -> str | None:
        path = self.path(value, base)
        if not is_inside(path, self.configured_root, strict=False):
            return (
                f"{role} {path} is outside the runs root "
                f"({RUNS_DIR_NAME} or AGENT_RUNS_DIR)"
            )
        if strict and not is_inside(path, self.configured_root, strict=True):
            return f"{role} {path} is the runs root itself; name a directory inside it"
        return None


def is_inside(path: str, configured_root: str | None, *, strict: bool) -> bool:
    """Whether the normalized absolute `path` sits in its runs root.

    Without a configured root, the root is the path's own prefix through its
    first `.agent-runs` segment. A strict check excludes the root itself.
    """
    if not os.path.isabs(path):
        return False
    if configured_root is None:
        segments = path.split("/")
        if RUNS_DIR_NAME not in segments:
            return False
        root = "/".join(segments[: segments.index(RUNS_DIR_NAME) + 1])
    else:
        root = configured_root
    if path == root:
        return not strict
    return path.startswith(root + "/")


# These characters let the shell run, expand, or redirect something the
# token checks below never see. `~` is denied anywhere, because bash expands
# it after `=` too (`--add-dir=~/x`).
UNQUOTED_FORBIDDEN = frozenset(";&|>$`(){}*?[]!\\~")
DOUBLE_QUOTED_FORBIDDEN = frozenset("$`\\")


@dataclass(frozen=True)
class ShellCommand:
    words: tuple[str, ...]
    stdin: str | None


def parse_shell(raw: str) -> ShellCommand | str:
    """Split `raw` into words and at most one trailing stdin file, or say why not."""
    if any(ord(char) < 32 and char != "\t" for char in raw):
        return "control characters such as newlines are not allowed"
    quote = None
    redirects = []
    for index, char in enumerate(raw):
        if quote == "'":
            if char == "'":
                quote = None
        elif quote == '"':
            if char == '"':
                quote = None
            elif char in DOUBLE_QUOTED_FORBIDDEN:
                return f"`{char}` inside double quotes is not allowed"
        elif char in "'\"":
            quote = char
        elif char in UNQUOTED_FORBIDDEN:
            return f"`{char}` outside quotes is not allowed"
        elif char == "#" and (index == 0 or raw[index - 1].isspace()):
            return "a `#` comment is not allowed"
        elif char == "<":
            redirects.append(index)
    if len(redirects) > 1:
        return "only one `<` stdin redirect is allowed"
    text, stdin = raw, None
    if redirects:
        at = redirects[0]
        if at == 0 or not raw[at - 1].isspace():
            return "`<` must follow a space and redirect stdin only"
        try:
            target = shlex.split(raw[at + 1 :])
        except ValueError:
            return "the command does not parse as shell words"
        if len(target) != 1:
            return "`<` must be followed by exactly one file at the end of the command"
        text, stdin = raw[:at], target[0]
    try:
        words = tuple(shlex.split(text))
    except ValueError:
        return "the command does not parse as shell words"
    if not words:
        return "the command is empty"
    return ShellCommand(words, stdin)


Checker = Callable[[tuple[str, ...], Scope], "str | None"]


def check_read_paths(
    args: tuple[str, ...],
    scope: Scope,
    *,
    command: str,
    value_options: frozenset[str] = frozenset(),
) -> str | None:
    paths = []
    options_done = False
    remaining = iter(args)
    for arg in remaining:
        if options_done or arg == "-" or not arg.startswith("-"):
            paths.append(arg)
        elif arg == "--":
            options_done = True
        elif arg in value_options:
            next(remaining, None)
    if not paths:
        return f"{command} needs at least one path inside the runs root"
    for path in paths:
        if reason := scope.check_path(path, strict=False, role=f"{command} path"):
            return reason
    return None


def check_test(args: tuple[str, ...], scope: Scope) -> str | None:
    if len(args) != 2 or not re.fullmatch(r"-[A-Za-z]", args[0]):
        return "test takes one unary operator and one path, as in test -d PATH"
    return scope.check_path(args[1], strict=False, role="test path")


# sed's `e`, `w`, and `r` commands execute or write, so only a print of one
# line or address range is allowed.
SED_PRINT_SCRIPT = re.compile(r"(\d+|\$|/[^/]*/)(,(\d+|\$|/[^/]*/))?p")


def check_sed(args: tuple[str, ...], scope: Scope) -> str | None:
    if len(args) < 3 or args[0] != "-n" or not SED_PRINT_SCRIPT.fullmatch(args[1]):
        return (
            "sed allows only -n with one print script such as '1,/^---$/p' "
            "(no e, w, or r commands)"
        )
    for path in args[2:]:
        if path.startswith("-"):
            return f"sed option {path} is not allowed"
        if reason := scope.check_path(path, strict=False, role="sed path"):
            return reason
    return None


# `--output` writes a file, `--ext-diff` runs a configured program, and
# `--no-index` compares files outside any repository.
GIT_FORBIDDEN_ARGUMENT_PREFIXES = ("--output", "--ext-diff", "--no-index")


def check_git_read(args: tuple[str, ...], scope: Scope) -> str | None:
    for arg in args:
        if arg.startswith(GIT_FORBIDDEN_ARGUMENT_PREFIXES):
            return f"git option {arg} is not allowed"
    return None


def check_git_worktree(args: tuple[str, ...], scope: Scope) -> str | None:
    if not args or args[0] != "list":
        return "git worktree allows only list"
    return check_git_read(args[1:], scope)


GIT_SUBCOMMANDS: dict[str, Checker] = {
    "status": check_git_read,
    "log": check_git_read,
    "diff": check_git_read,
    "rev-parse": check_git_read,
    "show": check_git_read,
    "worktree": check_git_worktree,
}


def check_git(args: tuple[str, ...], scope: Scope) -> str | None:
    if len(args) < 3 or args[0] != "-C":
        return "git needs -C <directory in the runs root> as its only global option"
    if reason := scope.check_path(args[1], strict=False, role="git -C"):
        return reason
    subcommand = args[2]
    if subcommand.startswith("-"):
        return f"git global option {subcommand} is not allowed; only -C"
    checker = GIT_SUBCOMMANDS.get(subcommand)
    if checker is None:
        return (
            f"git {subcommand} is not allowed; only status, log, diff, "
            "rev-parse, show, and worktree list"
        )
    return checker(args[3:], scope)


# Value flags whose value the guard checks map to a CodexExec field; the rest
# map to None and only need their value consumed.
CODEX_VALUE_FLAGS = {
    "-m": None,
    "--model": None,
    "-s": "sandbox",
    "--sandbox": "sandbox",
    "-C": "cd",
    "--cd": "cd",
    "--add-dir": "add_dirs",
    "-o": "output",
    "--output-last-message": "output",
    "-c": "config",
    "--config": "config",
    "-i": None,
    "--image": None,
    "--color": None,
    "--output-schema": None,
}
CODEX_BARE_FLAGS = frozenset({"--skip-git-repo-check", "--json", "--ephemeral"})
CODEX_EXEC_SUBCOMMANDS = frozenset({"resume", "fork", "review", "help"})
# Any other config key can override the sandbox or the approval policy.
CODEX_CONFIG_KEY = "agents.enabled"


@dataclass(frozen=True)
class CodexExec:
    sandbox: tuple[str, ...]
    cd: tuple[str, ...]
    add_dirs: tuple[str, ...]
    output: tuple[str, ...]
    config: tuple[str, ...]
    positionals: tuple[str, ...]
    unknown: tuple[str, ...]


def parse_codex_exec(args: tuple[str, ...]) -> CodexExec | str:
    fields: dict[str, list[str]] = {
        "sandbox": [],
        "cd": [],
        "add_dirs": [],
        "output": [],
        "config": [],
        "positionals": [],
        "unknown": [],
    }
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        flag, has_inline, inline = (
            arg.partition("=") if arg.startswith("--") else (arg, "", "")
        )
        if flag in CODEX_VALUE_FLAGS:
            if has_inline:
                value = inline
            elif index < len(args):
                value = args[index]
                index += 1
            else:
                return f"codex exec {flag} needs a value"
            if not value or value.startswith("-"):
                return f"codex exec {flag} needs a value that does not start with -"
            if field := CODEX_VALUE_FLAGS[flag]:
                fields[field].append(value)
        elif arg in CODEX_BARE_FLAGS:
            continue
        elif arg == "-" or not arg.startswith("-"):
            fields["positionals"].append(arg)
        else:
            fields["unknown"].append(arg)
    return CodexExec(**{name: tuple(values) for name, values in fields.items()})


def check_codex_exec(args: tuple[str, ...], scope: Scope) -> str | None:
    parsed = parse_codex_exec(args)
    if isinstance(parsed, str):
        return parsed
    if parsed.unknown:
        return f"codex exec flag {parsed.unknown[0]} is not allowed"
    for setting in parsed.config:
        key = setting.partition("=")[0].strip()
        if key != CODEX_CONFIG_KEY:
            return f"codex exec -c {key} is not allowed; only -c {CODEX_CONFIG_KEY}"
    for positional in parsed.positionals:
        if positional in CODEX_EXEC_SUBCOMMANDS:
            return f"codex exec {positional} is not allowed; start a new exec run"
    if len(parsed.positionals) > 1:
        return "codex exec takes at most one prompt; pass - and redirect the brief on stdin"
    label = scope.kind.removesuffix("-codex")
    sandbox = SANDBOX_BY_KIND[scope.kind]
    if parsed.sandbox != (sandbox,):
        return f"{label} codex exec needs -s {sandbox}"
    for flag, values in (("-C", parsed.cd), ("-o", parsed.output)):
        if len(values) > 1:
            return f"codex exec gives {flag} more than once"
    cd = parsed.cd[0] if parsed.cd else None
    if scope.kind == DEVELOPER:
        if cd is None:
            return "developer codex exec needs -C <worktree inside the runs root>"
        if reason := scope.check_path(cd, strict=True, role="developer -C"):
            return reason
    # Codex may resolve a relative --add-dir or -o against -C rather than
    # its own working directory, so a relative one must hold from both.
    bases = (scope.cwd,) if cd is None else (scope.cwd, scope.path(cd))
    targets = [("--add-dir", path) for path in parsed.add_dirs]
    targets += [("-o", path) for path in parsed.output]
    for role, path in targets:
        for base in bases:
            if reason := scope.check_path(path, strict=True, role=role, base=base):
                return reason
    return None


def check_codex_version(args: tuple[str, ...], scope: Scope) -> str | None:
    return "codex --version takes no arguments" if args else None


def check_codex_login(args: tuple[str, ...], scope: Scope) -> str | None:
    return None if args == ("status",) else "codex login allows only status"


CODEX_SUBCOMMANDS: dict[str, Checker] = {
    "exec": check_codex_exec,
    "login": check_codex_login,
    "--version": check_codex_version,
    "-V": check_codex_version,
}


def check_codex(args: tuple[str, ...], scope: Scope) -> str | None:
    checker = CODEX_SUBCOMMANDS.get(args[0]) if args else None
    if checker is None:
        return "codex allows only exec, --version, and login status"
    return checker(args[1:], scope)


COMMANDS: dict[str, Checker] = {
    "codex": check_codex,
    "codex-agent": check_codex,
    "cat": partial(check_read_paths, command="cat"),
    "head": partial(
        check_read_paths, command="head", value_options=frozenset({"-n", "-c"})
    ),
    "ls": partial(check_read_paths, command="ls"),
    "test": check_test,
    "sed": check_sed,
    "git": check_git,
}


def check_bash(command: object, scope: Scope) -> str | None:
    """Return None to allow `command`, or one sentence naming the failed invariant."""
    if not isinstance(command, str):
        return "the Bash command is not a string"
    parsed = parse_shell(command)
    if isinstance(parsed, str):
        return parsed
    if parsed.stdin is not None and (
        reason := scope.check_path(parsed.stdin, strict=True, role="stdin file")
    ):
        return reason
    word, *args = parsed.words
    checker = COMMANDS.get(word)
    if checker is None:
        return f"{word} is not an allowed command"
    return checker(tuple(args), scope)


def watcher_scope(payload: Mapping[str, object], kind: str) -> Scope:
    cwd_value = payload.get("cwd")
    cwd = os.getcwd()
    if isinstance(cwd_value, str) and cwd_value:
        cwd = os.path.normpath(os.path.join(cwd, cwd_value))
    configured = os.environ.get("AGENT_RUNS_DIR", "")
    root = os.path.normpath(os.path.join(cwd, configured)) if configured else None
    return Scope(kind, cwd, root)


def watcher_kind(payload: Mapping[str, object]) -> str | None:
    agent_type = payload.get("agent_type")
    if not isinstance(agent_type, str):
        return None
    name = agent_type.rpartition(":")[2]
    return name if name in WATCHER_NAMES else None


def deny(reason: str) -> str:
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"codex watcher guard: {reason}",
            }
        }
    )


def _guard_watcher(payload: Mapping[str, object], kind: str) -> str:
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, Mapping):
        return deny("the tool call has no tool name or input")
    if tool_name != "Bash":
        return deny(f"{tool_name} is not allowed for a Codex watcher; only Bash is")
    if tool_input.get("run_in_background"):
        return deny("Bash must not run in the background")
    reason = check_bash(tool_input.get("command"), watcher_scope(payload, kind))
    return "" if reason is None else deny(reason)


def guard(payload: Mapping[str, object]) -> str:
    """Return a PreToolUse denial JSON line, or an empty string to allow.

    Fails closed: an exception raised while judging a watcher's payload
    denies the call instead of letting it through unguarded. A payload that
    does not name a watcher is not this guard's job, so it re-raises.
    """
    try:
        kind = watcher_kind(payload)
        if kind is None:
            return ""
        return _guard_watcher(payload, kind)
    except Exception:
        try:
            still_a_watcher = watcher_kind(payload) is not None
        except Exception:
            still_a_watcher = False
        if still_a_watcher:
            return deny("the call could not be checked, so it is denied")
        raise


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as error:
        print(
            f"codex watcher guard: cannot parse stdin as JSON: {error}", file=sys.stderr
        )
        raise SystemExit(2)
    if isinstance(payload, Mapping):
        output = guard(payload)
        if output:
            print(output)


if __name__ == "__main__":
    main()
