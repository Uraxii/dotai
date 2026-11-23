"""Add the skill-quality guidance to the agent's context when it edits a
SKILL.md or a reference Markdown file in a skill directory.

Usage: skill_quality_guidance.py --harness claude|codex|copilot
- claude: PreToolUse on Write|Edit|MultiEdit, path in tool_input.file_path.
- codex: PreToolUse on apply_patch, paths in the patch's file headers.
- copilot: postToolUse on edit|create, path in toolArgs.path, a JSON string.
  Copilot's preToolUse cannot add context, so the guidance follows the first
  edit.
The guidance is added once per session for each skill directory. The hook
never blocks: every path exits 0 with no output on failure, because a Copilot
hook that fails can deny the call.
"""

import json
import os
import re
import sys
import tempfile
import zlib

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(HOOKS_DIR, "..", "skills", "skill-quality")
HARNESSES = ("claude", "codex", "copilot")
PATCH_HEADER = re.compile(r"\*\*\* (?:Add File|Update File|Move to): (.*)")
ABSOLUTE = re.compile(r"/|[A-Za-z]:[/\\]")
SKILL_PREFIX = re.compile(r"(.*/skills/[^/]+)/.+")
SESSION_ID = re.compile(r"[A-Za-z0-9_.-]+")


def text(value):
    # Numbers stay as their JSON text (parse_int and parse_float keep it), as
    # `jq -r` printed them for the bash hook.
    if value is True:
        return "true"
    return value if isinstance(value, str) else ""


def parse(raw):
    return json.loads(raw, parse_int=str, parse_float=str)


def edited_paths(harness, event):
    if harness == "claude":
        return text((event.get("tool_input") or {}).get("file_path"))
    if harness == "codex":
        command = text((event.get("tool_input") or {}).get("command"))
        headers = (PATCH_HEADER.fullmatch(line) for line in command.split("\n"))
        return "\n".join(match.group(1) for match in headers if match)
    args = event.get("toolArgs")
    if isinstance(args, str):
        args = parse(args)
    return text(args.get("path")) if isinstance(args, dict) else ""


def skill_dir(path):
    """The outermost skills/NAME directory that holds a SKILL.md, or the one
    whose SKILL.md this edit creates."""
    found = None
    rest = path
    match = SKILL_PREFIX.fullmatch(rest)
    while match:
        rest = match.group(1)
        if os.path.isfile(rest + "/SKILL.md") or path == rest + "/SKILL.md":
            found = rest
        match = SKILL_PREFIX.fullmatch(rest)
    return found


def first_time(session, directory):
    if not SESSION_ID.fullmatch(session):
        return True
    checksum = zlib.crc32(directory.encode("utf-8"))
    marker = os.path.join(tempfile.gettempdir(), "skill-quality-%s-%d" % (session, checksum))
    # O_EXCL makes the check and the create one step, so parallel edits cannot
    # both add the guidance.
    try:
        os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except OSError:
        return False
    return True


def without_frontmatter(markdown):
    lines = markdown.split("\n")
    if lines[0] != "---":
        return markdown
    for end in range(1, len(lines)):
        if lines[end] == "---":
            return "\n".join(lines[end + 1 :])
    return ""


def main(argv):
    harness = argv[1] if len(argv) > 1 and argv[0] == "--harness" else ""
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    if harness not in HARNESSES or not os.path.isfile(skill_md):
        return
    event = parse(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(event, dict):
        return
    cwd = text(event.get("cwd"))
    session = text(event.get("sessionId" if harness == "copilot" else "session_id"))

    dirs = []
    for path in edited_paths(harness, event).split("\n"):
        if path.endswith("\r"):
            path = path[:-1]
        if not path:
            continue
        if not ABSOLUTE.match(path) and cwd:
            path = cwd + "/" + path
        path = path.replace("\\", "/")
        if not path.endswith(".md"):
            continue
        directory = skill_dir(path)
        if directory and first_time(session, directory) and directory not in dirs:
            dirs.append(directory)
    if not dirs:
        return

    with open(skill_md, encoding="utf-8", errors="replace") as file:
        body = without_frontmatter(file.read()).rstrip("\n")
    lint = os.path.join(os.path.abspath(os.path.join(SKILL_DIR, "scripts")), "lint-skills.sh")
    context = (
        "You are editing a skill. Follow this skill-quality guidance.\n\n%s\n\n"
        "The verification script is %s. Run it on each skill directory you change:" % (body, lint)
    )
    context += "".join("\n- " + directory for directory in dirs)

    if harness == "copilot":
        output = {"additionalContext": context}
    else:
        output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": context}}
    sys.stdout.buffer.write((json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except BaseException:
        pass
    os._exit(0)
