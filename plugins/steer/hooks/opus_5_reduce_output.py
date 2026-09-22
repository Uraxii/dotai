#!/usr/bin/env python3
"""opus_5_reduce_output — Stop hook asking for a plain-English recap of the turn.

Wired in the plugin's `hooks/hooks.json` under `Stop`.
`CLEAN_RECAP_*` and `clean-recap.log` retain their original names deliberately.

Env vars, all optional:
- CLEAN_RECAP_LOG - path to the audit log. Default ~/.claude/clean-recap.log.
- CLEAN_RECAP_LOG_MAX_BYTES - size at which the log rolls over. Default 1,000,000.
- CLEAN_RECAP_MODEL_PATTERN - regex the current model must match to trigger
  a recap. Default "opus-5|fable".

Fires when Claude tries to end its turn. Returns `{"decision": "block"}`,
which does not stop at all: it hands Claude one more instruction, to write
a short recap for someone who has not read the code. Three gates decide,
in order: the loop guard below, the model that answered matching
`opus-5|fable`, and the turn having changed something. A turn that mutated
nothing has nothing to recap, so it is allowed to end silently. Every
invocation appends one line to an audit log so a declined gate never looks
like a hook that never ran.

Rationale: a consistent close-out enforced by the harness, instead of the
user remembering to ask for a summary every time.

Hook protocol (Claude Code):
- stdin: JSON envelope w/ stop_hook_active, transcript_path.
- stdout: `{"decision": "block", "reason": ...}` blocks the stop and feeds
          `reason` back as Claude's next instruction; print nothing to let
          the turn end.
- exit code: always 0. Any error/missing data/declined gate -> exit 0,
  print nothing. Never crash the session.

LOOP GUARD — do not remove. Blocking the stop means Claude works on and
hits Stop again, with stop_hook_active set on that second pass. Ignore it
and the session can never end.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path

# The audit log rolls over once it reaches this size instead of growing
# forever. It rolls over once, with no numbered backups, because it is an
# audit trail for the current stretch of sessions, not a record kept
# across rollovers.
DEFAULT_LOG_MAX_BYTES = 1_000_000
DEFAULT_MODEL_PATTERN = "opus-5|fable"

# Tools whose presence alone means the turn changed something. Agent and
# Task are in here because a delegate's own edits never reach this
# transcript, so a turn that spawned one has to be assumed to have changed
# something. Bash is deliberately absent: it is classified by its command.
MUTATING_TOOLS = frozenset({"Write", "Edit", "NotebookEdit", "Agent", "Task"})

# Bash is classified by a DENYLIST of mutating shapes rather than an
# allowlist of safe ones, because an unrecognised command is far more
# likely to be a read-only inspection than a mutation, and the two ways of
# being wrong do not cost the same. A wrong skip costs one missing recap.
# A wrong recap is the bug this gate exists to fix, and it lands on every
# turn. So the unknown command falls on the recap side.
MUTATING_COMMANDS = frozenset(
    {
        "rm", "rmdir", "mv", "cp", "mkdir", "touch", "install", "ln",
        "tee", "dd", "truncate", "chmod", "chown", "patch",
    }
)

# Editors that only mutate when asked to edit in place.
IN_PLACE_EDITORS = frozenset({"sed", "perl", "ruby"})

# Programs that run another program. The wrapped name is the one to classify.
COMMAND_WRAPPERS = frozenset({"sudo", "env", "command", "nohup", "time", "xargs"})

# Global options sit between a program and its verb, so `git -C <dir> push`
# has to reach the same verdict as `git push`. These take a value, so both
# tokens go; any other leading option is dropped on its own.
GLOBAL_OPTIONS_TAKING_A_VALUE = frozenset(
    {"-C", "-R", "-c", "--repo", "--git-dir", "--work-tree"}
)

# Mutating verbs that live one or two tokens past the program name.
MUTATING_COMMAND_PREFIXES = (
    ("git", "add"), ("git", "am"), ("git", "apply"), ("git", "cherry-pick"),
    ("git", "checkout"), ("git", "clean"), ("git", "commit"), ("git", "merge"),
    ("git", "mv"), ("git", "push"), ("git", "rebase"), ("git", "reset"),
    ("git", "restore"), ("git", "revert"), ("git", "rm"), ("git", "stash"),
    ("git", "switch"), ("git", "tag"),
    ("git", "branch", "-D"), ("git", "branch", "-d"),
    ("git", "branch", "-M"), ("git", "branch", "-m"),
    ("git", "worktree", "add"), ("git", "worktree", "remove"),
    ("git", "worktree", "prune"),
    ("gh", "pr", "create"), ("gh", "pr", "merge"), ("gh", "pr", "close"),
    ("gh", "pr", "edit"), ("gh", "pr", "comment"),
    ("gh", "repo", "create"), ("gh", "release", "create"),
)

# Redirecting to /dev/null discards output rather than writing it, and it is
# one of the commonest read-only idioms there is. Stripped before the write
# check so only the discard is excused, never a redirect later in the line.
DISCARD_REDIRECT = re.compile(r">{1,2}\s*/dev/null\b")

# Shell redirection into a file, including the `1>` and `&>` spellings. Only
# a trailing `&` means a descriptor dup rather than a write, so `2>&1` and
# `>&2` are excluded there. The lookbehind drops `>=` and a `->` arrow.
REDIRECT_TO_FILE = re.compile(r"(?<![-=<>!])>{1,2}(?![&=])")

# A chain runs every segment, so every segment gets classified.
COMMAND_SEPARATOR = re.compile(r"&&|\|\||;|\||\n")

# A prompt, not config. Keep it short; it is injected on every turn.
RECAP_INSTRUCTION = (
    "Type a clean recap. Keep it short, light, and plain — a few sentences "
    "of what changed and what it means, not a report. Write for someone who "
    "has not read the code: no file paths, no function or variable names, no "
    "line numbers, no code blocks, and assume nothing about what they already "
    "know of the internals. Skip the caveats and next-steps unless something "
    "is genuinely broken or unfinished. If they want the detail, they will ask."
)


def _log(message: str) -> None:
    """Append one audit line, rolling the log over once it grows too big.

    Logging must never break the hook. The bound is a plain size check: if
    the file is already at or past the limit, this write opens it in "w"
    mode instead of "a", truncating it, so the log restarts from this line
    rather than growing without limit across a machine's whole lifetime.
    """
    path = os.environ.get("CLEAN_RECAP_LOG") or str(
        Path.home() / ".claude" / "clean-recap.log"
    )
    try:
        try:
            max_bytes = int(
                os.environ.get("CLEAN_RECAP_LOG_MAX_BYTES") or DEFAULT_LOG_MAX_BYTES
            )
        except ValueError:
            max_bytes = DEFAULT_LOG_MAX_BYTES
        stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        mode = "a"
        rolled_over = False
        try:
            if Path(path).stat().st_size >= max_bytes:
                mode = "w"
                rolled_over = True
        except OSError:
            pass
        with open(path, mode, encoding="utf-8") as f:
            if rolled_over:
                f.write(f"{stamp} clean-recap.log rolled over; earlier lines were dropped\n")
            f.write(f"{stamp} {message}\n")
    except OSError:
        pass


def _current_model(transcript_path: Path) -> str:
    """The model of the last main-agent reply, or "-" if there is none.

    Subagent (isSidechain) replies do not count: a delegate running on
    another model must not decide whether this session gets a recap.
    """
    lines = transcript_path.read_text(encoding="utf-8", errors="replace")
    for line in reversed(lines.splitlines()):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("isSidechain"):
            continue
        if entry.get("type") == "assistant":
            return entry.get("message", {}).get("model") or "-"
    return "-"


def _is_real_user_prompt(entry: dict) -> bool:
    """True for a typed prompt, false for a tool result or an injection.

    Both arrive as `type: "user"`. A tool result carries only `tool_result`
    blocks, and harness injections such as a loaded skill carry `isMeta`.
    Treating either as a turn boundary would cut the turn at its first tool
    call, so the gate would see no tools and skip every recap.
    """
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return True
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "text"
        for block in content
    )


def _current_turn_tool_uses(transcript_path: Path) -> list[dict] | None:
    """Tool calls made since the last real user prompt, or None if unreadable.

    None means the gate cannot see the turn: an unparseable transcript, or
    one with no user prompt in it at all. The caller must then fall through
    to requesting the recap. A gate that cannot see must not suppress.
    """
    try:
        lines = transcript_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    tool_uses: list[dict] = []
    for line in reversed(lines.splitlines()):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("isSidechain"):
            continue
        if _is_real_user_prompt(entry):
            return tool_uses
        if entry.get("type") == "assistant":
            content = entry.get("message", {}).get("content")
            if not isinstance(content, list):
                continue
            tool_uses.extend(
                block
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_use"
            )
    return None


def _without_global_options(arguments: list[str]) -> list[str]:
    """The arguments from the first non-option token on, so a verb is found.

    `git -C <dir> push` and `gh -R <repo> pr create` mutate exactly as much
    as the bare forms do. Stops at the first non-option, so a flag that is
    part of the verb itself, as in `git branch -D`, survives.
    """
    rest = list(arguments)
    while rest and rest[0].startswith("-"):
        del rest[: 2 if rest[0] in GLOBAL_OPTIONS_TAKING_A_VALUE else 1]
    return rest


def _command_mutates(command: str) -> bool:
    """True when any segment of a shell command line writes something."""
    for segment in COMMAND_SEPARATOR.split(command):
        segment = DISCARD_REDIRECT.sub("", segment)
        if REDIRECT_TO_FILE.search(segment):
            return True
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        # Drop wrappers and leading VAR=value assignments so the program
        # name is the token actually classified.
        while tokens and (
            Path(tokens[0]).name in COMMAND_WRAPPERS or "=" in tokens[0]
        ):
            tokens.pop(0)
        if not tokens:
            continue
        program = Path(tokens[0]).name
        if program in MUTATING_COMMANDS:
            return True
        if program in IN_PLACE_EDITORS and any(
            token.startswith("-i") for token in tokens[1:]
        ):
            return True
        normalized = (program, *_without_global_options(tokens[1:]))
        if any(
            normalized[: len(prefix)] == prefix
            for prefix in MUTATING_COMMAND_PREFIXES
        ):
            return True
    return False


def _turn_mutated(tool_uses: list[dict]) -> bool:
    """True when the turn ran at least one tool that changed something."""
    for block in tool_uses:
        name = block.get("name")
        if name in MUTATING_TOOLS:
            return True
        if name == "Bash":
            command = (block.get("input") or {}).get("command")
            if isinstance(command, str) and _command_mutates(command):
                return True
    return False


def main() -> int:
    payload = json.loads(sys.stdin.read())

    if payload.get("stop_hook_active"):
        _log("fired  stop_hook_active=true -> stand down (recap already written)")
        return 0

    transcript = payload.get("transcript_path") or ""
    if not transcript or not Path(transcript).is_file():
        _log("fired  no readable transcript_path -> allow")
        return 0

    pattern = os.environ.get("CLEAN_RECAP_MODEL_PATTERN") or DEFAULT_MODEL_PATTERN
    model = _current_model(Path(transcript))

    try:
        matched = re.search(pattern, model, re.IGNORECASE)
    except re.error as error:
        _log(
            f"fired  CLEAN_RECAP_MODEL_PATTERN {pattern!r} rejected ({error}) "
            f"-> using default {DEFAULT_MODEL_PATTERN!r}"
        )
        pattern = DEFAULT_MODEL_PATTERN
        matched = re.search(pattern, model, re.IGNORECASE)

    if not matched:
        _log(
            f"fired  model={model} -> allow "
            f"(model does not match '{pattern}')"
        )
        return 0

    tool_uses = _current_turn_tool_uses(Path(transcript))
    if tool_uses is None:
        _log(
            f"fired  model={model} -> BLOCK (requesting recap; "
            "no user prompt found, turn boundary unknown)"
        )
    elif not _turn_mutated(tool_uses):
        _log(
            f"fired  model={model} -> allow "
            "(turn used no mutating tool, nothing to recap)"
        )
        return 0
    else:
        _log(f"fired  model={model} -> BLOCK (requesting recap)")

    print(json.dumps({"decision": "block", "reason": RECAP_INSTRUCTION}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # ponytail: fail-safe per hook contract — any error means exit 0,
        # silent. A hook that cannot run must never wedge the session.
        sys.exit(0)
