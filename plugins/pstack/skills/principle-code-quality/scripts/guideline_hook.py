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
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
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
PATCH_MARKERS = ("*** Begin Patch", "*** End Patch")
END_OF_FILE = "*** End of File"
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


def patched_realpath(path: str, unlinked: Collection[str] = ()) -> str:
    """The real path, through the symlinks the patch has not deleted."""
    for _ in range(40):
        if path in unlinked:
            return path
        parent = os.path.realpath(os.path.dirname(path))
        path = os.path.join(parent, os.path.basename(path))
        if path in unlinked or not os.path.islink(path):
            return path
        path = os.path.normpath(os.path.join(parent, os.readlink(path)))
    return path


def with_link_targets(
    files: list[Neutral], cwd: str, root: str,
    unlinked: frozenset[str] | set[str] = frozenset(),
    reals: Mapping[str, str] | None = None,
) -> list[Neutral]:
    """A file edited through a symlink, or a symlinked folder, is also
    checked at its real path, with that path's own lint settings."""
    named = {os.path.normpath(os.path.join(cwd, str(file["path"]))) for file in files}
    lexical, top = os.path.normpath(root), Path(root).resolve()
    extra: list[Neutral] = []
    for change in files:
        full = os.path.normpath(os.path.join(cwd, str(change["path"])))
        if change.get("after") is None:
            continue
        # A path's real path when it was written, before later deletes.
        real = (reals or {}).get(full) or patched_realpath(full, unlinked)
        # The same name below a symlinked root is the same file.
        same = Path(full).is_relative_to(lexical) and Path(real) == top / os.path.relpath(full, lexical)
        if real == full or same or real in named or top not in Path(real).parents:
            continue
        named.add(real)
        # A moved file keeps the baseline of the path it was moved from.
        source = str(change.get("source") or "")
        moved = source and os.path.normpath(os.path.join(cwd, source)) != full
        extra.append(change | {"path": real, "source": source if moved else real})
    return files + extra


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
        "root": os.environ.get("CLAUDE_PROJECT_DIR") or project_root(cwd),
    }


def project_root(cwd: str) -> str:
    """The nearest folder above cwd with a .git, else cwd: Codex sends the
    folder it runs in, which can be below the project root."""
    start = Path(cwd)
    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return str(directory)
    return cwd


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
    cwd, root = str(base["cwd"]), str(base["root"])
    disk = read_disk(raw, cwd, root)
    if name == "PostToolUse":
        return {"kind": "post_write",
                "files": with_link_targets([written(raw, disk)], cwd, root)}
    if name != "PreToolUse":
        return None
    known = tool == "Write" or not disk.problem
    after = pending_write(tool, tool_input, disk.text) if known else None
    if after is None:
        return {"kind": "pre_write", "files": [unbuilt(raw, disk)]}
    change = {"path": raw, "before": disk.text, "after": after,
              "before_problem": disk.problem}
    return {"kind": "pre_write",
            "files": with_link_targets([change], cwd, root)}


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
    bodies: list[list[str]] = []
    lines = [line.removesuffix("\r") for line in patch.split("\n")]
    if lines[-1] == "":
        lines.pop()
    for line in lines:
        # Codex trims a header line, but in an update body an indented
        # line is context, and a move comes right after its header.
        update = bool(files) and files[-1].action == "Update File"
        directive = line.rstrip() if update else line.strip()
        header = PATCH_HEADER.match(directive)
        move = header is not None and header.group(1) == "Move to"
        if move and update and not bodies[-1]:
            files[-1] = files[-1]._replace(target=header.group(2))
        elif header and not move:
            path = header.group(2)
            files.append(PatchFile(header.group(1), path, path, ()))
            bodies.append([])
        elif files and directive not in PATCH_MARKERS:
            bodies[-1].append(line)
    return [
        file._replace(body=tuple(body)) for file, body in zip(files, bodies)
    ]


class Hunk(NamedTuple):
    anchor: str
    rows: list[str]
    at_end: bool


def hunks(body: Sequence[str]) -> Iterator[Hunk]:
    """Split an Update File body at its `@@` lines. The text after `@@ `
    is an anchor line that Codex finds before it looks for the hunk."""
    hunk: Hunk | None = None
    for line in body:
        directive = line.rstrip()
        if directive.startswith("@@"):
            if hunk is not None:
                yield hunk
            anchor = directive[3:] if directive.startswith("@@ ") else ""
            hunk = Hunk(anchor, [], False)
        elif directive == END_OF_FILE:
            hunk = (hunk or Hunk("", [], False))._replace(at_end=True)
        else:
            hunk = hunk or Hunk("", [], False)
            hunk.rows.append(line or " ")
    if hunk is not None:
        yield hunk


CODEX_PUNCTUATION = str.maketrans({
    **dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2015\u2212", "-"),
    **dict.fromkeys("\u2018\u2019\u201a\u201b", "'"),
    **dict.fromkeys("\u201c\u201d\u201e\u201f", '"'),
    **dict.fromkeys(
        "\u00a0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009"
        "\u200a\u202f\u205f\u3000", " ",
    ),
})
LINE_MATCHES: tuple[Callable[[str], str], ...] = (
    lambda line: line, str.rstrip, str.strip,
    lambda line: line.strip().translate(CODEX_PUNCTUATION),
)


def find_lines(
    lines: list[str], wanted: list[str], start: int,
    forms: dict[int, list[str]] | None = None,
) -> int | None:
    """Find the context the way Codex does: exact, then without trailing
    whitespace, then without any surrounding whitespace, then with Unicode
    dashes, quotes and spaces read as ASCII."""
    last = len(lines) - len(wanted)
    if not wanted:
        return start if start <= last else None
    # The normalized file, made once per form for all hunks.
    forms = {} if forms is None else forms
    for rank, normalize in enumerate(LINE_MATCHES):
        target = [normalize(line) for line in wanted]
        if rank not in forms:
            forms[rank] = lines if rank == 0 else [normalize(x) for x in lines]
        normal = forms[rank]
        index = start
        for _ in range(64):
            try:
                index = normal.index(target[0], index, last + 1)
            except ValueError:
                break
            if normal[index:index + len(wanted)] == target:
                return index
            index += 1
        else:
            # A first line found at many places: a linear search.
            found = search_lines(normal, target, index, last)
            if found is not None:
                return found
    return None


def search_lines(
    lines: list[str], wanted: list[str], start: int, last: int,
) -> int | None:
    """The first index from start to last where wanted begins
    (Knuth-Morris-Pratt), in time linear in both lengths."""
    fallback = [0] * len(wanted)
    size = 0
    for at in range(1, len(wanted)):
        while size and wanted[at] != wanted[size]:
            size = fallback[size - 1]
        if wanted[at] == wanted[size]:
            size += 1
        fallback[at] = size
    size = 0
    for at in range(start, last + len(wanted)):
        while size and lines[at] != wanted[size]:
            size = fallback[size - 1]
        if lines[at] == wanted[size]:
            size += 1
        if size == len(wanted):
            return at - size + 1
    return None


def find_hunk(
    lines: list[str], hunk: Hunk, old: list[str], cursor: int,
    forms: dict[int, list[str]],
) -> int | None:
    """Codex looks for an End of File hunk at the end of the file only."""
    start = len(lines) - len(old) if hunk.at_end else cursor
    return find_lines(lines, old, max(start, 0), forms)


def changed_runs(rows: list[str]) -> list[tuple[int, int, list[str]]]:
    """One replacement per run of `-` and `+` rows, as Codex splits a hunk
    at its context lines: the run's offset in the hunk's old lines, how
    many lines it removes, and the lines it adds. Context keeps the file's
    text."""
    runs: list[tuple[int, int, list[str]]] = []
    offset = 0
    previous = " "
    for row in rows:
        if row[0] in "-+" and previous == " ":
            runs.append((offset, 0, []))
        if row[0] == "-":
            start, length, new = runs[-1]
            runs[-1] = (start, length + 1, new)
        elif row[0] == "+":
            runs[-1][2].append(row[1:])
        offset += row[0] in " -"
        previous = " " if row[0] == " " else "-"
    return runs


def without_final_empty(rows: list[str]) -> list[str]:
    """The rows less the final empty old line, and an empty added line
    after it, for Codex's retry without a trailing empty line."""
    last = max(i for i, row in enumerate(rows) if row[0] in " -")
    kept = rows[:last] + rows[last + 1:]
    if rows[last][0] == "-" and kept and kept[-1] == "+":
        kept = kept[:-1]
    return kept


def apply_update(current: str, body: Sequence[str]) -> str | None:
    """Apply the hunks in memory the way Codex does; None when a hunk or
    its anchor does not match the file. Codex finds every hunk in the
    original lines, without a final empty one, then replaces from the
    end, and always ends the file with a newline."""
    # Codex splits at LF, CRLF and a bare CR, and matches the lines
    # without their terminators; the file's own terminators are kept.
    lines = SOURCE_LINE.findall(current)
    keys = [line.rstrip("\r\n") for line in lines]
    # New lines take the file's first line ending, as in Codex.
    first = LINE_ENDING.search(current)
    ending = first.group() if first else "\n"
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += ending
    replacements: list[tuple[int, int, list[str]]] = []
    forms: dict[int, list[str]] = {}
    cursor = 0
    for hunk in hunks(body):
        if hunk.anchor:
            anchor = find_lines(keys, [hunk.anchor], cursor, forms)
            if anchor is None:
                return None
            cursor = anchor + 1
        rows = hunk.rows
        old = [row[1:] for row in rows if row[0] in " -"]
        if not old:
            replacements += [
                (len(lines), 0, terminated(new, ending))
                for _, _, new in changed_runs(rows)
            ]
            continue
        index = find_hunk(keys, hunk, old, cursor, forms)
        if index is None and old[-1] == "":
            rows = without_final_empty(rows)
            old = old[:-1]
            index = find_hunk(keys, hunk, old, cursor, forms)
        if index is None:
            return None
        replacements += [
            (index + offset, length, terminated(new, ending))
            for offset, length, new in changed_runs(rows)
        ]
        cursor = index + len(old)
    # Codex applies from the end, so hunks at one offset keep patch order.
    for start, length, new in sorted(
        replacements, key=lambda item: item[0]
    )[::-1]:
        lines[start:start + length] = new
    return "".join(lines)


SOURCE_LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$")
LINE_ENDING = re.compile(r"\r\n|\r|\n")


def terminated(lines: list[str], ending: str) -> list[str]:
    return [line + ending for line in lines]


def patch_change(
    file: PatchFile, base: Neutral, prior: Neutral | None = None
) -> Neutral:
    """The change one file section makes. A later section for the same
    file starts from the text the earlier ones leave, as Codex applies
    them in order, and keeps the original text as the baseline."""
    if prior is not None:
        if not isinstance(prior.get("after"), str):
            return prior
        change = patch_change(file, base | {"disk": prior["after"]})
        return change | {
            key: prior[key] for key in ("before", "before_problem", "source")
            if key in prior
        }
    disk = read_disk(file.source, str(base["cwd"]), str(base["root"]))
    if isinstance(base.get("disk"), str):
        disk = Disk(str(base["disk"]))
    if file.action == "Add File":
        added = "".join(line[1:] + "\n" for line in file.body)
        return {"path": file.target, "before": disk.text, "after": added,
                "before_problem": disk.problem}
    after = None if disk.text is None else apply_update(disk.text, file.body)
    if after is None:
        return unbuilt(file.target, disk)
    return {"path": file.target, "before": disk.text, "after": after,
            "source": file.source}


def codex_tool_event(payload: Payload, base: Neutral) -> Neutral | None:
    name = payload.get("hook_event_name")
    command = text_of(table_of(payload.get("tool_input")).get("command"))
    sections = parse_patch(command)
    files = [f for f in sections if f.action != "Delete File"]
    cwd, root = str(base["cwd"]), str(base["root"])
    if name == "PostToolUse":
        return {"kind": "post_write", "files": with_link_targets([
            written(target, read_disk(target, cwd, root))
            for target in dict.fromkeys(file.target for file in files)
        ], cwd, root)}
    if name != "PreToolUse":
        return None
    # Keyed by real path, as `./a.py`, `$PWD/a.py` and a symlink to it
    # are one file.
    changes: dict[str, Neutral] = {}
    deleted: set[str] = set()
    moved_away: set[str] = set()
    # Symlinks the patch deletes; their paths no longer lead to the target.
    unlinked: set[str] = set()
    # The symlink paths each file was edited through, by real path.
    link_names: dict[str, list[str]] = {}
    # Those paths with their folders resolved.
    through: set[str] = set()
    # The real path each written path led to when its section was applied.
    reals: dict[str, str] = {}

    def named(path: str) -> str:
        return os.path.join(
            os.path.realpath(os.path.dirname(path)), os.path.basename(path),
        )

    for file in sections:
        source, target = (
            patched_realpath(path, unlinked)
            for path in (
                os.path.normpath(os.path.join(cwd, name))
                for name in (file.source, file.target)
            )
        )
        link = os.path.normpath(os.path.join(cwd, file.source))
        if file.action == "Delete File" and os.path.islink(link):
            # Deleting a symlink leaves its target as it is; an earlier
            # change made through the symlink stays at the target's path.
            source = target = link
            unlinked |= {link, named(link)}
            for key, change in list(changes.items()) if named(link) in through else ():
                path = os.path.normpath(os.path.join(cwd, str(change["path"])))
                if key != link and named(path) == named(link):
                    source_of = os.path.normpath(
                        os.path.join(cwd, str(change.get("source") or path))
                    )
                    changes[key] = change | {"path": key} | (
                        {"source": key} if named(source_of) == named(link) else {}
                    )
        # A moved symlink leaves its target, and the target's change, in place.
        moves_link = (
            file.action != "Delete File"
            and link != os.path.normpath(os.path.join(cwd, file.target))
            and link not in unlinked and os.path.islink(link)
        )
        dest = os.path.normpath(os.path.join(cwd, file.target))
        if (
            file.action != "Delete File" and not moves_link and dest != link
            and dest not in unlinked and os.path.islink(dest) and target == source
        ):
            # Moved onto a symlink to itself: Codex writes through the
            # symlink, then removes the file, so the text is lost.
            changes[source] = {"path": file.source, "before": None,
                               "after": None, "source": file.source}
            deleted.add(source)
            continue
        if file.action != "Delete File":
            reals[dest] = target
        if file.action != "Delete File" and dest not in unlinked and target != dest:
            link_names.setdefault(target, []).append(dest)
            through.add(named(dest))
        prior = changes.get(source) if moves_link else changes.pop(source, None)
        if file.action == "Delete File":
            # Kept, as a deleted file can be a lint setting of the others;
            # a moved file keeps the path it was moved from.
            changes[target] = {
                "path": file.target, "before": None, "after": None,
                "source": str((prior or {}).get("source") or file.source),
            }
            deleted.add(target)
            continue
        if source in deleted:
            prior = None
            deleted.discard(source)
        # A path a move or a symlink delete left empty starts empty.
        start = base | {"disk": ""} if (
            prior is None and source in moved_away | unlinked
        ) else base
        changes[target] = patch_change(file, start, prior)
        deleted.discard(target)
        # Moving a symlink removes the symlink, not its target: the moved
        # text was the target's, and the target is checked at its own path.
        if moves_link:
            moved_away.add(link)
            unlinked |= {link, named(link)}
            changes[target] = changes[target] | {"source": source}
            if prior is not None and source != target:
                changes[source] = prior | {"path": source, "source": source}
        elif source != target:
            moved_away.add(source)
    # A path a move left empty is deleted, also when another section
    # moved a file there first.
    for source in moved_away - changes.keys():
        changes[source] = {"path": source, "before": None, "after": None}
    files = list(changes.values())
    # Each symlink the file was edited through has its own lint settings.
    for key, names in link_names.items():
        change = changes.get(key)
        if change is None or change.get("after") is None:
            continue
        own = os.path.normpath(os.path.join(cwd, str(change["path"])))
        files += [
            change | {"path": name, "source": name}
            for name in dict.fromkeys(names)
            if name != own and name not in unlinked
            and patched_realpath(name, unlinked) == key
        ]
    return {"kind": "pre_write",
            "files": with_link_targets(files, cwd, root, unlinked, reals)}


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
