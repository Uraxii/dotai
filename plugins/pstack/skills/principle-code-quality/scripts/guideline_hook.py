#!/usr/bin/env python3
"""Deliver code-quality guidelines from a harness hook, or on demand.

Usage:
  guideline_hook.py --harness claude|codex|neutral   hook payload on stdin
  guideline_hook.py check PATH...                    exit 1 on a block hit,
                                                     3 on a missing path
  guideline_hook.py --language PATH                  print the language id

A hook call prints one JSON object for the harness, or nothing, and exits 0
even when the engine fails. It denies a pending write only when a detector
finds a new hit on a block guideline.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
import tempfile
import time
import traceback
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))  # python -I leaves the script dir out

from guideline_core import (  # noqa: E402
    MAX_CONTENT_CHARS, MAX_TEXT_CHARS, Config, Result, default_data_directory,
    event_from_json, handle, resolve_in_root,
)
from guideline_files import language_of, load_extensions  # noqa: E402

MAX_PAYLOAD_BYTES = 16_000_000
WRITE_TOOLS = ("Write", "Edit", "MultiEdit")
SESSION_KINDS = {"clear": "cleared", "compact": "compacted"}
PATCH_HEADER = re.compile(
    r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$"
)
PATCH_MARKERS = ("*** Begin Patch", "*** End Patch", "*** End of File")
EXIT_BLOCK_FINDING = 1
EXIT_MISSING_PATH = 3
EXIT_USAGE = 64
MAX_LOG_BYTES = 200_000
OVERSIZE_MESSAGE = (
    f"pstack guideline hook skipped this call: its input is larger than "
    f"{MAX_PAYLOAD_BYTES // 1_000_000} MB, so code-quality guidelines were "
    f"not checked."
)
UNREADABLE_MESSAGE = (
    "pstack guideline hook skipped this call: its input is not a UTF-8 "
    "JSON object, so code-quality guidelines were not checked."
)
FAILURE_MESSAGE = (
    "pstack guideline hook failed; code-quality guidelines were not checked "
    "for this call."
)

Neutral = dict[str, object]
Payload = dict[str, object]


def text_of(value: object) -> str:
    return value if isinstance(value, str) else ""


def table_of(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def config() -> Config:
    skill = SCRIPTS.parent
    guidelines = os.environ.get("PSTACK_GUIDELINES_DIR")
    data = os.environ.get("PSTACK_GUIDELINE_DATA") or os.environ.get(
        "CLAUDE_PLUGIN_DATA"
    )
    return Config(
        Path(guidelines) if guidelines else skill / "guidelines",
        skill / "languages.toml",
        Path(data) if data else default_data_directory(),
    )


class Disk(NamedTuple):
    """A project file's text, or why it could not be read."""
    text: str | None
    problem: str = ""


def read_disk(raw: str, cwd: str, root: str) -> Disk:
    """Read a project file as UTF-8 with its own line endings.

    A missing file or one outside the root gives no text and no problem.
    """
    path = resolve_in_root(raw, cwd, root)
    if path is None or not path.is_file():
        return Disk(None)
    try:
        if path.stat().st_size > MAX_CONTENT_CHARS:
            return Disk(None, "it is larger than 1 MB")
        with path.open(encoding="utf-8", newline="") as handle:
            return Disk(handle.read())
    except UnicodeDecodeError:
        return Disk(None, "it is not UTF-8 text")
    except (OSError, ValueError) as error:
        return Disk(None, f"it could not be read ({type(error).__name__})")


def written(raw: str, disk: Disk) -> Neutral:
    return {"path": raw, "after": disk.text, "problem": disk.problem}


def unbuilt(raw: str, disk: Disk) -> Neutral:
    problem = disk.problem or "could not build the text this edit leaves"
    return {"path": raw, "before": disk.text, "after": None,
            "problem": problem}


def apply_edit(current: str | None, edit: object) -> str | None:
    """Build the text one Edit leaves; None when the tool would refuse."""
    fields = table_of(edit)
    old, new = fields.get("old_string"), fields.get("new_string")
    if not isinstance(old, str) or not isinstance(new, str):
        return None
    if current is None:
        return new if old == "" else None
    if old not in current and "\r\n" in current:
        old, new = (text.replace("\n", "\r\n") for text in (old, new))
    if old == "" or old not in current:
        return None
    if fields.get("replace_all") is True:
        return current.replace(old, new)
    return current.replace(old, new, 1) if current.count(old) == 1 else None


def pending_write(
    tool: str, tool_input: dict[str, object], before: str | None
) -> str | None:
    """Build the file text a Write, Edit or MultiEdit call would leave."""
    if tool == "Write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else None
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    if not isinstance(edits, list) or not edits:
        return None
    after = before
    for edit in edits:
        after = apply_edit(after, edit)
        if after is None:
            return None
    return after


def common_fields(payload: Payload) -> Neutral:
    cwd = text_of(payload.get("cwd")) or os.getcwd()
    return {
        "session": text_of(payload.get("session_id")),
        "agent": text_of(payload.get("agent_id")),
        "cwd": cwd,
        "root": os.environ.get("CLAUDE_PROJECT_DIR") or cwd,
    }


def session_or_prompt(payload: Payload) -> Neutral | None:
    """Map the two events Claude Code and Codex share."""
    name = payload.get("hook_event_name")
    if name == "SessionStart":
        source = text_of(payload.get("source"))
        return {"kind": SESSION_KINDS.get(source, "session_start")}
    if name == "UserPromptSubmit":
        return {"kind": "prompt", "prompt": text_of(payload.get("prompt"))}
    return None


def claude_tool_event(payload: Payload, base: Neutral) -> Neutral | None:
    name, tool = payload.get("hook_event_name"), payload.get("tool_name")
    tool_input = table_of(payload.get("tool_input"))
    raw = text_of(tool_input.get("file_path"))
    if not raw or not isinstance(tool, str):
        return None
    if name == "PostToolUse" and tool == "Read":
        return {"kind": "post_read", "files": [{"path": raw}]}
    if tool not in WRITE_TOOLS:
        return None
    disk = read_disk(raw, str(base["cwd"]), str(base["root"]))
    if name == "PostToolUse":
        return {"kind": "post_write", "files": [written(raw, disk)]}
    if name != "PreToolUse":
        return None
    known = tool == "Write" or not disk.problem
    after = pending_write(tool, tool_input, disk.text) if known else None
    if after is None:
        return {"kind": "pre_write", "files": [unbuilt(raw, disk)]}
    change = {"path": raw, "before": disk.text, "after": after,
              "before_problem": disk.problem}
    return {"kind": "pre_write", "files": [change]}


def claude_event(payload: Payload) -> Neutral | None:
    base = common_fields(payload)
    event = session_or_prompt(payload) or claude_tool_event(payload, base)
    return {**base, **event} if event else None


class PatchFile(NamedTuple):
    action: str
    source: str
    target: str
    body: tuple[str, ...]


def parse_patch(patch: str) -> list[PatchFile]:
    """Split an apply_patch text into one entry per file."""
    files: list[PatchFile] = []
    for line in patch.splitlines():
        header = PATCH_HEADER.match(line)
        if header and header.group(1) == "Move to" and files:
            files[-1] = files[-1]._replace(target=header.group(2))
        elif header:
            path = header.group(2)
            files.append(PatchFile(header.group(1), path, path, ()))
        elif files and line not in PATCH_MARKERS:
            files[-1] = files[-1]._replace(body=(*files[-1].body, line))
    return files


def hunks(body: Sequence[str]) -> Iterator[list[str]]:
    hunk: list[str] = []
    for line in body:
        if line.startswith("@@"):
            if hunk:
                yield hunk
            hunk = []
        else:
            hunk.append(line or " ")
    if hunk:
        yield hunk


LINE_MATCHES: tuple[Callable[[str], str], ...] = (
    lambda line: line, str.rstrip, str.strip,
)


def find_lines(lines: list[str], wanted: list[str], start: int) -> int | None:
    """Find the context the way Codex does: exact, then without trailing
    whitespace, then without any surrounding whitespace."""
    last = len(lines) - len(wanted)
    for normalize in LINE_MATCHES:
        target = [normalize(line) for line in wanted]
        for index in range(start, last + 1):
            window = lines[index:index + len(wanted)]
            if [normalize(line) for line in window] == target:
                return index
    return None


def apply_update(current: str, body: Sequence[str]) -> str | None:
    """Apply the hunks in memory; None when one does not match the file."""
    ending = "\r\n" if "\r\n" in current else "\n"
    lines = current.split(ending)
    cursor = 0
    for hunk in hunks(body):
        old = [line[1:] for line in hunk if line[0] in " -"]
        new = [line[1:] for line in hunk if line[0] in " +"]
        index = find_lines(lines, old, cursor) if old else len(lines) - 1
        if index is None:
            return None
        lines[index:index + len(old)] = new
        cursor = index + len(new)
    return ending.join(lines)


def patch_change(file: PatchFile, base: Neutral) -> Neutral:
    disk = read_disk(file.source, str(base["cwd"]), str(base["root"]))
    if file.action == "Add File":
        added = "".join(line[1:] + "\n" for line in file.body)
        return {"path": file.target, "before": disk.text, "after": added,
                "before_problem": disk.problem}
    after = None if disk.text is None else apply_update(disk.text, file.body)
    if after is None:
        return unbuilt(file.target, disk)
    return {"path": file.target, "before": disk.text, "after": after}


def codex_tool_event(payload: Payload, base: Neutral) -> Neutral | None:
    name = payload.get("hook_event_name")
    command = text_of(table_of(payload.get("tool_input")).get("command"))
    files = [f for f in parse_patch(command) if f.action != "Delete File"]
    cwd, root = str(base["cwd"]), str(base["root"])
    if name == "PostToolUse":
        return {"kind": "post_write", "files": [
            written(file.target, read_disk(file.target, cwd, root))
            for file in files
        ]}
    if name != "PreToolUse":
        return None
    changes = [patch_change(file, base) for file in files]
    return {"kind": "pre_write", "files": changes}


def codex_event(payload: Payload) -> Neutral | None:
    base = common_fields(payload)
    event = session_or_prompt(payload) or codex_tool_event(payload, base)
    return {**base, **event} if event else None


def hook_output(result: Result, event_name: str) -> Neutral | None:
    """Render a result in the output shape Claude Code and Codex share."""
    if result.deny is not None:
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": result.deny,
        }}
    if result.context is None:
        return None
    output: Neutral = {"hookSpecificOutput": {
        "hookEventName": event_name, "additionalContext": result.context,
    }}
    notice = fit_notice(result.notice or "", MAX_TEXT_CHARS - len(result.context))
    if notice:
        output["systemMessage"] = notice
    return output


def fit_notice(notice: str, room: int) -> str:
    """Keep the notice lines that fit in `room` characters; count the rest.
    The agent's context holds every notice."""
    lines = notice.split("\n")
    for kept in range(len(lines), -1, -1):
        rest = len(lines) - kept
        tail = [f"Notice: {rest} more notices; the agent has them."] * (rest > 0)
        text = "\n".join(lines[:kept] + tail)
        if len(text) <= room:
            return text
    return ""


ADAPTERS: dict[str, Callable[[Payload], Neutral | None]] = {
    "claude": claude_event,
    "codex": codex_event,
    "neutral": lambda payload: payload,
}


def run_hook(harness: str) -> int:
    raw = sys.stdin.buffer.read(MAX_PAYLOAD_BYTES + 1)
    if len(raw) > MAX_PAYLOAD_BYTES:
        print(json.dumps({"systemMessage": OVERSIZE_MESSAGE}))
        return 0
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        print(json.dumps({"systemMessage": UNREADABLE_MESSAGE}))
        return 0
    event = event_from_json(ADAPTERS[harness](payload))
    if event is None:
        return 0
    result = handle(event, config())
    if harness == "neutral":
        output: Neutral | None = result._asdict()
    else:
        name = text_of(payload.get("hook_event_name"))
        output = hook_output(result, name)
    if output is not None:
        print(json.dumps(output))
    return 0


def path_problem(path: Path) -> str:
    """Why `check` cannot read a path; empty for a regular file."""
    try:
        mode = path.stat().st_mode
    except FileNotFoundError:
        return "no such file"
    except OSError as error:
        return f"its status could not be read ({type(error).__name__})"
    if stat.S_ISREG(mode):
        return ""
    if stat.S_ISDIR(mode):
        return "it is a directory"
    return "it is not a regular file"


def check(paths: Sequence[str]) -> int:
    """Print guidelines and findings for files; exit 1 on a block hit."""
    cwd = os.getcwd()
    problems = {
        path: problem for path in paths
        if (problem := path_problem(Path(cwd) / path))
    }
    files = [
        {"path": path, "problem": problems[path]} if path in problems
        else written(path, read_disk(path, cwd, cwd))
        for path in paths
    ]
    with tempfile.TemporaryDirectory() as fresh_state:
        event = event_from_json({
            "kind": "check", "session": "check", "cwd": cwd, "files": files,
        })
        if event is None:
            return EXIT_USAGE
        result = handle(event, config()._replace(data=Path(fresh_state)))
    print(result.context)
    if result.deny is not None:
        return EXIT_BLOCK_FINDING
    return EXIT_MISSING_PATH if problems else 0


def log_failure(harness: str) -> Path:
    """Append the traceback to errors.log; refuse a planted symlink."""
    log = config().data / "guideline-state" / "errors.log"
    log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    user = os.getuid() if hasattr(os, "getuid") else None
    for directory in (log.parent.parent, log.parent):
        owner = directory.lstat().st_uid
        if directory.is_symlink() or user not in (None, owner):
            raise PermissionError(f"{directory} is not owned by this user")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    for extra in ("O_NOFOLLOW", "O_NONBLOCK"):
        flags |= getattr(os, extra, 0)
    descriptor = os.open(log, flags, 0o600)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise PermissionError(f"{log} is not a regular file")
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        if handle.tell() > MAX_LOG_BYTES:
            handle.truncate(0)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        handle.write(f"{stamp} {harness}\n{traceback.format_exc()}\n")
    return log


def fail_open(harness: str) -> int:
    """Tell the user a hook call failed; never block their work."""
    try:
        details = f" Details: {log_failure(harness)}"
    except Exception:  # noqa: BLE001  the log is best effort
        details = ""
    print(json.dumps({"systemMessage": FAILURE_MESSAGE + details}))
    return 0


def main(arguments: Sequence[str]) -> int:
    match arguments:
        case ["--harness", harness] if harness in ADAPTERS:
            try:
                return run_hook(harness)
            except Exception:  # noqa: BLE001  a hook must fail open
                return fail_open(harness)
        case ["check", *paths] if paths:
            return check(paths)
        case ["--language", path]:
            extensions = load_extensions(SCRIPTS.parent / "languages.toml")
            print(language_of(Path(path).name, extensions) or "")
            return 0
    print(__doc__, file=sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
