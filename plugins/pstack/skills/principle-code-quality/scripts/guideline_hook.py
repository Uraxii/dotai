#!/usr/bin/env python3
"""Deliver code-quality guidelines from a harness hook, or on demand.

Usage:
  guideline_hook.py --harness claude|codex|neutral   hook payload on stdin
  guideline_hook.py check PATH...                    exit 1 on a block hit
  guideline_hook.py --language PATH                  print the language id

A hook call prints one JSON object for the harness, or nothing. It denies a
pending write only when a detector finds a new hit on a block guideline.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))  # python -I leaves the script dir out

from guideline_core import (  # noqa: E402
    MAX_CONTENT_CHARS, Config, Result, default_data_directory,
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


def read_disk(raw: str, cwd: str, root: str) -> str | None:
    """Read a project file as UTF-8; None when missing, big, or outside."""
    path = resolve_in_root(raw, cwd, root)
    if path is None or not path.is_file():
        return None
    try:
        if path.stat().st_size > MAX_CONTENT_CHARS:
            return None
        return path.read_text("utf-8")
    except (OSError, ValueError):
        return None


def apply_edit(current: str | None, edit: object) -> str | None:
    """Build the text one Edit leaves; None when the tool would refuse."""
    fields = table_of(edit)
    old, new = fields.get("old_string"), fields.get("new_string")
    if not isinstance(old, str) or not isinstance(new, str):
        return None
    if current is None:
        return new if old == "" else None
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
    disk = read_disk(raw, str(base["cwd"]), str(base["root"]))
    if name == "PostToolUse" and tool == "Read":
        return {"kind": "post_read", "files": [{"path": raw}]}
    if tool not in WRITE_TOOLS:
        return None
    if name == "PostToolUse":
        return {"kind": "post_write", "files": [{"path": raw, "after": disk}]}
    after = pending_write(tool, tool_input, disk)
    if name != "PreToolUse" or after is None:
        return None
    change = {"path": raw, "before": disk, "after": after}
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


def find_lines(lines: list[str], wanted: list[str], start: int) -> int | None:
    last = len(lines) - len(wanted)
    for index in range(start, last + 1):
        if lines[index:index + len(wanted)] == wanted:
            return index
    return None


def apply_update(current: str, body: Sequence[str]) -> str | None:
    """Apply the hunks in memory; None when one does not match the file."""
    lines = current.split("\n")
    cursor = 0
    for hunk in hunks(body):
        old = [line[1:] for line in hunk if line[0] in " -"]
        new = [line[1:] for line in hunk if line[0] in " +"]
        index = find_lines(lines, old, cursor) if old else len(lines) - 1
        if index is None:
            return None
        lines[index:index + len(old)] = new
        cursor = index + len(new)
    return "\n".join(lines)


def patch_change(file: PatchFile, base: Neutral) -> Neutral | None:
    disk = read_disk(file.source, str(base["cwd"]), str(base["root"]))
    if file.action == "Add File":
        added = "".join(line[1:] + "\n" for line in file.body)
        return {"path": file.target, "before": disk, "after": added}
    if file.action != "Update File" or disk is None:
        return None
    after = apply_update(disk, file.body)
    if after is None:
        return None
    return {"path": file.target, "before": disk, "after": after}


def codex_tool_event(payload: Payload, base: Neutral) -> Neutral | None:
    name = payload.get("hook_event_name")
    command = text_of(table_of(payload.get("tool_input")).get("command"))
    files = [f for f in parse_patch(command) if f.action != "Delete File"]
    cwd, root = str(base["cwd"]), str(base["root"])
    if name == "PostToolUse":
        written = [
            {"path": file.target, "after": read_disk(file.target, cwd, root)}
            for file in files
        ]
        return {"kind": "post_write", "files": written}
    if name != "PreToolUse":
        return None
    changes = [patch_change(file, base) for file in files]
    return {"kind": "pre_write", "files": [c for c in changes if c]}


def codex_event(payload: Payload) -> Neutral | None:
    base = common_fields(payload)
    event = session_or_prompt(payload) or codex_tool_event(payload, base)
    return {**base, **event} if event else None


def hook_output(
    result: Result, event_name: str, show_notice: bool
) -> Neutral | None:
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
    if result.notice and show_notice:
        output["systemMessage"] = result.notice
    return output


ADAPTERS: dict[str, Callable[[Payload], Neutral | None]] = {
    "claude": claude_event,
    "codex": codex_event,
    "neutral": lambda payload: payload,
}


def run_hook(harness: str) -> int:
    raw = sys.stdin.buffer.read(MAX_PAYLOAD_BYTES + 1)
    try:
        payload = json.loads(raw) if len(raw) <= MAX_PAYLOAD_BYTES else None
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    event = event_from_json(ADAPTERS[harness](payload))
    if event is None:
        return 0
    result = handle(event, config())
    if harness == "neutral":
        output: Neutral | None = result._asdict()
    else:
        name = text_of(payload.get("hook_event_name"))
        output = hook_output(result, name, show_notice=harness == "claude")
    if output is not None:
        print(json.dumps(output))
    return 0


def check(paths: Sequence[str]) -> int:
    """Print guidelines and findings for files; exit 1 on a block hit."""
    cwd = os.getcwd()
    files = [
        {"path": path, "after": read_disk(path, cwd, cwd)} for path in paths
    ]
    with tempfile.TemporaryDirectory() as fresh_state:
        event = event_from_json({
            "kind": "check", "session": "check", "cwd": cwd, "files": files,
        })
        if event is None:
            return 0
        result = handle(event, config()._replace(data=Path(fresh_state)))
    print(result.context)
    return EXIT_BLOCK_FINDING if result.deny is not None else 0


def main(arguments: Sequence[str]) -> int:
    match arguments:
        case ["--harness", harness] if harness in ADAPTERS:
            return run_hook(harness)
        case ["check", *paths] if paths:
            return check(paths)
        case ["--language", path]:
            extensions = load_extensions(SCRIPTS.parent / "languages.toml")
            print(language_of(Path(path).name, extensions) or "")
            return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
