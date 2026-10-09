#!/usr/bin/env python3
"""Add `-c agents.enabled=false` to every `codex exec` a Bash call runs.

Without the flag, Codex 0.154.0 exposes `collaboration.spawn_agent`,
`followup_task`, and `send_message`, so a `codex exec` can hand the prompt
to a helper agent instead of doing the work itself. This applies everywhere,
main thread or any subagent, not only the `delegate-to-codex` watchers,
because any Bash call can run `codex exec` by hand.

This is not a security gate: an unparseable or non-matching command passes
through untouched, and a command that already carries the flag is left
alone. It only rewrites `command` via `hookSpecificOutput.updatedInput`
(https://code.claude.com/docs/en/hooks, PreToolUse decision control table,
fetched 2026-09-29: "`updatedInput` | Modifies the tool's input parameters
before execution. ... Claude Code evaluates permission rules ... against the
input your hook returns, not the input Claude sent."). No `permissionDecision`
is set, so the rewritten command still goes through the normal permission
flow instead of being auto-approved.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping


__all__ = ["rewrite_command", "main"]

FLAG = "-c agents.enabled=false"
FLAG_MARKER = "agents.enabled=false"

# A `codex` invocation starts right after the string start or a shell
# separator (`;`, `&`, `|`, a backtick, a newline, or an opening paren),
# with optional whitespace in between, never mid-word. `echo codex exec`
# (codex is an argument to echo, not a command) and `/tmp/codex/exec.sh`
# (codex is a path segment) both fail this on purpose: neither has one of
# those separators right before `codex`.
#
# ponytail: this is a regex heuristic, not a shell parser. A command
# substitution, an alias, or a `codex` reached through a variable can still
# slip past it either way. Upgrade to a real shell tokenizer if a live
# command trips it.
CODEX_INVOCATION = re.compile(r"(?:\A|[;&|`\n(])\s*codex\b")
HEREDOC_OPERATOR = re.compile(r"<<(-?)[ \t]*(['\"]?)(\w+)\2")
WORD_START = frozenset(" \t\n;&|()<>=`")
SEGMENT_END = re.compile(r"[;&|`\n)]")
EXEC_WORD = re.compile(r"\bexec\b")
TOKEN = re.compile(r"\S+")
VALUE_OPTIONS = frozenset({
    "-C", "--cd", "-c", "--config", "-m", "--model", "-p", "--profile",
    "-i", "--image", "-s", "--sandbox", "--add-dir", "--color",
    "--output-schema", "-o", "--output-last-message", "--enable", "--disable",
})


def exec_end(segment: str) -> int | None:
    """Offset just past `exec` when it is the subcommand, else None."""
    skip_value = False
    for token in TOKEN.finditer(segment):
        word = token.group()
        if skip_value:
            skip_value = False
        elif word.startswith("-"):
            skip_value = word in VALUE_OPTIONS
        else:
            return token.end() if word == "exec" else None
    return None


def closing_quote(command: str, start: int) -> int:
    """Index of the quote closing the one at `start`, or -1."""
    if command[start] == "'":
        return command.find("'", start + 1)
    i = start + 1
    while i < len(command):
        if command[i] == "\\":
            i += 1
        elif command[i] == '"':
            return i
        i += 1
    return -1


def substitution_spans(body: str) -> list[tuple[int, int]]:
    """Spans of `$(...)` in an unquoted heredoc body, which bash executes."""
    spans = []
    i = body.find("$(")
    while i != -1:
        depth, j = 1, i + 2
        while j < len(body) and depth:
            depth += (body[j] == "(") - (body[j] == ")")
            j += 1
        spans.append((i, j))
        i = body.find("$(", j)
    return spans


def mask_text(command: str) -> str:
    """Same-length copy with text the command only writes or prints blanked.

    Heredoc bodies, quoted strings, and `#` comments are not invocations.
    A heredoc body is blanked only when its closing delimiter exists, and an
    unquoted body keeps its `$(...)` substitutions. A quote or `#` counts
    only at the start of a word, `\\x` escapes are skipped, and `<<<` and
    `<<` inside `$((...))` are not heredocs. Blanking keeps offsets valid.
    ponytail: `bash -c "codex exec ..."` is blanked too and passes through
    unrewritten; unwrap `-c` strings if that matters.
    """
    out = list(command)
    n = len(command)

    def blank(start: int, end: int) -> None:
        for k in range(start, end):
            if out[k] != "\n":
                out[k] = " "

    def consume_heredoc(start: int, dash: str, quote: str, delim: str) -> int:
        """Blank the body starting at `start`; return where scanning resumes."""
        pos = start
        while pos <= n:
            eol = command.find("\n", pos)
            eol = n if eol == -1 else eol
            line = command[pos:eol]
            if (line.lstrip("\t") if dash else line) == delim:
                blank(start, eol)
                if not quote:
                    body = command[start:pos]
                    for a, b in substitution_spans(body):
                        out[start + a:start + b] = body[a:b]
                return eol
            if eol == n:
                return start
            pos = eol + 1
        return start

    pending: list[tuple[str, str, str]] = []
    i = 0
    while i < n:
        c = command[i]
        at_word = i == 0 or command[i - 1] in WORD_START
        if c == "\\":
            i += 2
        elif c == "#" and at_word:
            eol = command.find("\n", i)
            eol = n if eol == -1 else eol
            blank(i, eol)
            i = eol
        elif c in "'\"" and at_word and (end := closing_quote(command, i)) != -1:
            blank(i, end + 1)
            i = end + 1
        elif command.startswith("$((", i):
            end = command.find("))", i)
            i = n if end == -1 else end + 2
        elif command.startswith("<<<", i):
            i += 3
        elif c == "<" and (op := HEREDOC_OPERATOR.match(command, i)):
            pending.append(op.groups())
            i = op.end()
        elif c == "\n" and pending:
            i += 1
            for dash, quote, delim in pending:
                i = consume_heredoc(i, dash, quote, delim)
                i = min(i + 1, n) if command.startswith("\n", i) else i
            pending.clear()
        else:
            i += 1
    return "".join(out)


def rewrite_command(command: str) -> str:
    """Add the no-helper-agents flag to every `codex exec` in `command`.

    Each `codex ...` invocation, up to the next shell separator or the end
    of the string, is one segment. A segment that contains `exec` as its
    own word gets `-c agents.enabled=false` right after `exec` when `exec`
    is the subcommand, else right after `codex`, unless the segment already
    carries the flag. `codex login status` or
    `codex --version`, with no `exec` in their own segment, are untouched.

    The flag goes after `exec`, not after `codex`, so the rewritten argv
    still reads `codex exec`.
    """
    pieces: list[str] = []
    cursor = 0
    for match in CODEX_INVOCATION.finditer(mask_text(command)):
        codex_end = match.end()
        if codex_end < cursor:
            continue  # inside a segment this loop already rewrote
        boundary = SEGMENT_END.search(command, codex_end)
        segment_end = boundary.start() if boundary else len(command)
        segment = command[codex_end:segment_end]
        exec_word = EXEC_WORD.search(segment)
        if exec_word and FLAG_MARKER not in segment:
            subcommand_end = exec_end(segment)
            insert_at = codex_end + (subcommand_end or 0)
            pieces.append(command[cursor:insert_at])
            pieces.append(f" {FLAG}")
            cursor = insert_at
    pieces.append(command[cursor:])
    return "".join(pieces)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, Mapping):
            return
        if payload.get("tool_name") != "Bash":
            return
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, Mapping):
            return
        command = tool_input.get("command")
        if not isinstance(command, str):
            return
        rewritten = rewrite_command(command)
        if rewritten == command:
            return
        updated_input = dict(tool_input)
        updated_input["command"] = rewritten
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated_input,
            }
        }))
    except Exception:
        # Never block a Bash call over a rewrite that could not be
        # computed; the flag is a convenience, not a permission boundary.
        return


if __name__ == "__main__":
    main()
