"""Harness-neutral core of the code-quality guideline hooks.

It takes one neutral event and returns one neutral result: which guideline
files to deliver, and whether a pending write is denied. It never reads a
harness payload; guideline_hook.py holds the adapters.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tempfile
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import NamedTuple

from guideline_files import (
    Guideline, keyword_matches, language_of, load_extensions,
    load_guidelines,
)
from guideline_runners import (
    SKIPPED_FOR_BUDGET, Detection, Finding, Target, detect, glob_matches,
    project_disables,
)

EXCLUDED_DIRECTORIES = frozenset({
    ".git", "node_modules", ".venv", "venv", "site-packages", "dist",
    "build", "vendor", "__pycache__",
})
EXCLUDED_SUFFIX = ".min.js"
OVERRIDE_LINE = "Project standards, configs and lints override these defaults."
CONTEXT_HEADER = f"Code-quality guidelines (pstack):\n{OVERRIDE_LINE}"
DENY_HEADER = (
    "Blocked: this edit adds code that breaks a block guideline. "
    f"Fix it, then retry the edit.\n{OVERRIDE_LINE}"
)
UNAVAILABLE_LABEL = "warn (detector unavailable)"
RESEND_AFTER_PROMPTS = 20
MAX_TEXT_CHARS = 9000
MAX_CONTENT_CHARS = 1_000_000
MAX_PROMPT_CHARS = 100_000
MAX_FILES_PER_EVENT = 50
MAX_NOTICES_KEPT = 200
MAX_NAME_CHARS = 80
STATE_MAX_AGE_SEC = 7 * 24 * 60 * 60
BUDGET_SEC = {"pre_write": 2.5, "post_write": 5.0, "check": 30.0}
EVENT_KINDS = frozenset({
    "session_start", "cleared", "compacted", "prompt", "pre_write",
    "post_write", "post_read", "check",
})
MAIN_AGENT = "main"
PATH_IN_PROMPT = re.compile(r"[\w./\\-]*\.[\w.]+")
UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_-]")


def resolve_in_root(raw: str, cwd: str, root: str) -> Path | None:
    """Resolve a payload path; None when it leaves the project root."""
    try:
        resolved = (Path(cwd) / raw).resolve()
        inside = resolved.is_relative_to(Path(root).resolve())
    except (OSError, ValueError):
        return None
    return resolved if inside else None


def safe_name(raw: str) -> str:
    return UNSAFE_NAME_CHARS.sub("_", raw)[:MAX_NAME_CHARS] or "unknown"


class FileChange(NamedTuple):
    path: str
    before: str | None
    after: str | None


class Event(NamedTuple):
    kind: str
    session: str
    agent: str
    cwd: str
    root: str
    prompt: str = ""
    files: tuple[FileChange, ...] = ()
    channel: bool = True


class Result(NamedTuple):
    deny: str | None = None
    context: str | None = None
    notice: str | None = None


def optional_text(value: object) -> str | None:
    if isinstance(value, str) and len(value) <= MAX_CONTENT_CHARS:
        return value
    return None


def file_changes(raw: object) -> tuple[FileChange, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        FileChange(item["path"], optional_text(item.get("before")),
                   optional_text(item.get("after")))
        for item in raw[:MAX_FILES_PER_EVENT]
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    )


def event_from_json(data: object) -> Event | None:
    """Parse an untrusted NeutralEvent; None when it is not one."""
    if not isinstance(data, dict) or data.get("kind") not in EVENT_KINDS:
        return None
    texts = {
        key: data.get(key, "")
        for key in ("session", "agent", "cwd", "root", "prompt")
    }
    if not all(isinstance(value, str) for value in texts.values()):
        return None
    if not texts["cwd"]:
        return None
    return Event(
        kind=data["kind"],
        session=safe_name(texts["session"]),
        agent=safe_name(texts["agent"] or MAIN_AGENT),
        cwd=texts["cwd"],
        root=texts["root"] or texts["cwd"],
        prompt=texts["prompt"][:MAX_PROMPT_CHARS],
        files=file_changes(data.get("files")),
        channel=data.get("channel") is not False,
    )


@dataclass
class State:
    prompt: int = 0
    languages: list[str] = field(default_factory=list)
    sent: dict[str, int] = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return None


def load_state(path: Path) -> State:
    """Read one agent's state; a missing or corrupt file gives a new one."""
    data = read_json(path)
    try:
        state = State(**data)  # type: ignore[arg-type]
        valid = isinstance(state.prompt, int) and all(
            isinstance(key, str) and isinstance(value, int)
            for key, value in state.sent.items()
        ) and all(
            isinstance(item, str)
            for item in state.languages + state.notices + state.pending
        )
    except (TypeError, AttributeError):
        return State()
    return state if valid else State()


def write_json(path: Path, data: object) -> None:
    """Replace the file atomically; only the owner can read it."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    descriptor = os.open(temporary, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    os.replace(temporary, path)


def prune_old_sessions(state_root: Path) -> None:
    if not state_root.is_dir():
        return
    oldest_kept = time.time() - STATE_MAX_AGE_SEC
    for entry in state_root.iterdir():
        stale = entry.is_dir() and entry.stat().st_mtime < oldest_kept
        if stale and not entry.is_symlink():
            shutil.rmtree(entry, ignore_errors=True)


class Config(NamedTuple):
    guidelines: Path
    languages: Path
    data: Path


def default_data_directory() -> Path:
    """Make a private state directory for a harness that names none."""
    user = os.getuid() if hasattr(os, "getuid") else "user"
    directory = Path(tempfile.gettempdir()) / f"pstack-guideline-state-{user}"
    directory.mkdir(mode=0o700, exist_ok=True)
    status = directory.lstat()
    owned = not hasattr(os, "getuid") or status.st_uid == os.getuid()
    if not stat.S_ISDIR(status.st_mode) or not owned:
        raise PermissionError(f"{directory} is not a directory we own")
    return directory


class CodeFile(NamedTuple):
    path: Path
    rel: str
    language: str
    guidelines: tuple[Guideline, ...]


class Hit(NamedTuple):
    guideline: Guideline
    finding: Finding
    rel: str
    text: str
    severity: str = "warn"

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.finding.tool, self.finding.code, self.text)


def line_text(content: str, line: int) -> str:
    lines = content.splitlines()
    return lines[line - 1].strip() if 0 < line <= len(lines) else ""


def guideline_for(
    finding: Finding, guidelines: Iterable[Guideline]
) -> Guideline | None:
    """Map a finding to the guideline with the longest matching code."""
    best: tuple[int, Guideline] | None = None
    for guideline in guidelines:
        for tool, code in guideline.detectors:
            matches = tool == finding.tool and finding.code.startswith(code)
            if matches and (best is None or len(code) > best[0]):
                best = (len(code), guideline)
    return best[1] if best else None


def new_hits(after: list[Hit], before: list[Hit]) -> list[Hit]:
    """Hits the edit adds: the multiset difference by line text."""
    remaining = Counter(hit.identity for hit in before)
    added = []
    for hit in after:
        if remaining[hit.identity] > 0:
            remaining[hit.identity] -= 1
        else:
            added.append(hit)
    return added


class Engine:
    """One hook call: reads state, handles the event, writes state."""

    def __init__(self, event: Event, config: Config) -> None:
        self.event = event
        self.guidelines, self.notices = load_guidelines(config.guidelines)
        self.extensions = load_extensions(config.languages)
        self.state_root = config.data / "guideline-state"
        session = self.state_root / event.session
        self.state_path = session / f"{event.agent}.json"
        self.probes_path = session / "tools.json"
        self.state = load_state(self.state_path)
        cached = read_json(self.probes_path)
        self.probes: dict[str, list[str]] = (
            cached if isinstance(cached, dict) else {}
        )
        budget = BUDGET_SEC.get(event.kind, 0.0)
        self.budget_sec = budget
        self.deadline = time.monotonic() + budget
        self.hits: list[Hit] = []
        self.fulls: dict[str, str] = {}
        self.blocked = False

    def code_file(self, raw: str) -> CodeFile | None:
        """Describe a payload path, or None when no guideline covers it."""
        path = resolve_in_root(raw, self.event.cwd, self.event.root)
        language = language_of(Path(raw).name, self.extensions)
        if path is None or language is None:
            return None
        root = Path(self.event.root).resolve()
        rel = path.relative_to(root).as_posix()
        parts = set(rel.split("/")[:-1])
        if parts & EXCLUDED_DIRECTORIES or rel.endswith(EXCLUDED_SUFFIX):
            return None
        applicable = tuple(
            guideline for guideline in self.guidelines
            if guideline.enabled and language in guideline.languages
            and self.applies(guideline, path, rel, root)
        )
        return CodeFile(path, rel, language, applicable)

    @staticmethod
    def applies(guideline: Guideline, path: Path, rel: str, root: Path) -> bool:
        in_paths = not guideline.paths or any(
            glob_matches(rel, glob) for glob in guideline.paths
        )
        excluded = any(glob_matches(rel, glob) for glob in guideline.exclude)
        disabled = any(
            project_disables(tool, code, path, root)
            for tool, code in guideline.detectors
        )
        return in_paths and not excluded and not disabled

    def note_language(
        self, language: str, guidelines: Iterable[Guideline]
    ) -> None:
        """On a language's first sighting, queue its ambient guidelines."""
        if language in self.state.languages:
            return
        self.state.languages.append(language)
        for guideline in guidelines:
            if guideline.ambient:
                self.fulls.setdefault(guideline.id, guideline.label)

    def for_language(self, language: str) -> list[Guideline]:
        return [
            guideline for guideline in self.guidelines
            if guideline.enabled and language in guideline.languages
        ]

    def report_problem(self, file: CodeFile, tool: str, problem: str) -> None:
        if problem == SKIPPED_FOR_BUDGET:
            later = "; PostToolUse checks it" * (self.event.kind == "pre_write")
            self.notices.append(
                f"Notice: skipped {tool}, the {self.budget_sec:g} s budget "
                f"was spent{later}"
            )
            return
        affected = [
            guideline for guideline in file.guidelines
            if any(owner == tool for owner, _ in guideline.detectors)
        ]
        codes = sorted(
            f"{owner}:{code}" for guideline in affected
            for owner, code in guideline.detectors if owner == tool
        )
        self.notices.append(
            f"Notice: {tool} {problem}, so detectors {', '.join(codes)} did "
            "not run. Their guidelines follow as warnings."
        )
        for guideline in affected:
            self.fulls[guideline.id] = UNAVAILABLE_LABEL

    def scan(
        self, file: CodeFile, content: str, quiet: bool = False
    ) -> tuple[list[Hit], set[str]]:
        """Run the file's detectors; return hits and the tools that failed."""
        codes: dict[str, set[str]] = {}
        for guideline in file.guidelines:
            for tool, code in guideline.detectors:
                codes.setdefault(tool, set()).add(code)
        target = Target(
            content, file.path, frozenset(), Path(self.event.root).resolve()
        )
        frozen = {tool: frozenset(found) for tool, found in codes.items()}
        results = detect(Detection(target, frozen, self.deadline, self.probes))
        hits, failed = [], set()
        for tool, result in results.items():
            if result.findings is None:
                failed.add(tool)
                if not quiet:
                    self.report_problem(file, tool, result.problem)
                continue
            for finding in result.findings:
                owner = guideline_for(finding, file.guidelines)
                if owner is not None:
                    text = line_text(content, finding.line)
                    hits.append(Hit(owner, finding, file.rel, text))
        return hits, failed

    def pre_write(self, change: FileChange) -> None:
        file = self.code_file(change.path)
        if file is None or change.after is None:
            return
        self.note_language(file.language, file.guidelines)
        hits, _ = self.scan(file, change.after)
        old: list[Hit] = []
        failed: set[str] = set()
        if change.before is not None and hits:
            old, failed = self.scan(file, change.before, quiet=True)
        added = [
            hit for hit in new_hits(hits, old)
            if hit.guideline.severity == "block"
            and hit.finding.tool not in failed
        ]
        if added:
            self.blocked = True
            self.hits += [
                hit._replace(severity="block") if hit in added else hit
                for hit in hits
            ]
        lowered = change.after.lower()
        for guideline in file.guidelines:
            if any(keyword_matches(k, lowered) for k in guideline.keywords):
                self.fulls.setdefault(guideline.id, guideline.label)

    def post_write(self, change: FileChange) -> None:
        file = self.code_file(change.path)
        if file is None:
            return
        self.note_language(file.language, file.guidelines)
        if change.after is None or self.event.kind == "post_read":
            return
        hits, _ = self.scan(file, change.after)
        if self.event.kind == "check":
            hits = [
                hit._replace(severity=hit.guideline.severity) for hit in hits
            ]
            self.blocked |= any(hit.severity == "block" for hit in hits)
        self.hits += hits

    def prompt(self) -> None:
        if self.event.agent == MAIN_AGENT:
            self.state.prompt += 1
        for token in PATH_IN_PROMPT.findall(self.event.prompt):
            language = language_of(token, self.extensions)
            if language is not None:
                self.note_language(language, self.for_language(language))
        lowered = self.event.prompt.lower()
        for guideline in self.guidelines:
            known = guideline.languages & set(self.state.languages)
            if guideline.enabled and known and any(
                keyword_matches(k, lowered) for k in guideline.keywords
            ):
                self.fulls.setdefault(guideline.id, guideline.label)

    def compacted(self) -> None:
        """Compaction can drop sent guidance, so send the globals again."""
        self.state.sent = {}
        for language in self.state.languages:
            for guideline in self.for_language(language):
                if guideline.ambient:
                    self.fulls.setdefault(guideline.id, guideline.label)

    def suppressed(self, guideline_id: str) -> bool:
        if guideline_id not in self.state.sent:
            return False
        age = self.state.prompt - self.state.sent[guideline_id]
        return self.event.agent != MAIN_AGENT or age < RESEND_AFTER_PROMPTS

    def hit_item(self, hit: Hit) -> str:
        finding = hit.finding
        head = (
            f"[{hit.guideline.id}] {hit.severity}: {finding.tool}:"
            f"{finding.code} at {hit.rel}:{finding.line}"
        )
        if self.suppressed(hit.guideline.id):
            return f"{head} (guidance sent earlier)"
        return f"{head}\n{hit.guideline.body}"

    def add(self, items: list[str], text: str) -> bool:
        """Append the item when the whole text stays under the size cap."""
        used = sum(len(item) + 2 for item in items)
        if used + len(text) > MAX_TEXT_CHARS:
            return False
        items.append(text)
        return True

    def add_notices(self, items: list[str]) -> list[str]:
        """Add each notice this agent has not seen; return those added."""
        added = [
            notice for notice in dict.fromkeys(self.notices)
            if notice not in self.state.notices and self.add(items, notice)
        ]
        self.state.notices += added
        return added

    def add_hits(self, items: list[str]) -> None:
        ordered = sorted(self.hits, key=lambda hit: (
            hit.severity != "block", hit.rel, hit.finding.line,
            hit.guideline.id,
        ))
        for hit in ordered:
            repeated = self.suppressed(hit.guideline.id)
            if self.add(items, self.hit_item(hit)) and not repeated:
                self.state.sent[hit.guideline.id] = self.state.prompt

    def add_fulls(self, items: list[str]) -> None:
        """Add queued and new guidelines in full; keep what does not fit."""
        by_id = {guideline.id: guideline for guideline in self.guidelines}
        queued = {**dict.fromkeys(self.state.pending, ""), **self.fulls}
        self.state.pending = []
        for guideline_id in sorted(queued):
            guideline = by_id.get(guideline_id)
            if guideline is None or self.suppressed(guideline_id):
                continue
            label = queued[guideline_id] or guideline.label
            text = f"[{guideline_id}] {label}\n{guideline.body}"
            if self.add(items, text):
                self.state.sent[guideline_id] = self.state.prompt
            else:
                self.state.pending.append(guideline_id)

    def queue_fulls(self) -> None:
        """Keep guidelines this call could not deliver for the next call."""
        self.state.pending += [
            guideline_id for guideline_id in self.fulls
            if guideline_id not in self.state.pending
            and not self.suppressed(guideline_id)
        ]

    def result(self) -> Result:
        kind = self.event.kind
        if self.blocked and kind == "pre_write":
            self.queue_fulls()
            items = [DENY_HEADER]
            self.add_hits(items)
            return Result(deny="\n\n".join(items))
        if not self.event.channel:
            self.queue_fulls()
            return Result()
        if kind == "pre_write":
            self.hits = []
        items = [] if kind == "check" else [CONTEXT_HEADER]
        notices = self.add_notices(items)
        self.add_hits(items)
        self.add_fulls(items)
        if kind == "check":
            text = "\n\n".join([*items, OVERRIDE_LINE])
            return Result(text if self.blocked else None, text)
        if len(items) == 1:
            return Result()
        return Result(None, "\n\n".join(items), "\n".join(notices) or None)

    def run(self) -> Result:
        kind = self.event.kind
        if kind == "session_start":
            prune_old_sessions(self.state_root)
        elif kind == "cleared":
            self.state = State()
        elif kind == "compacted":
            self.compacted()
        elif kind == "prompt":
            self.prompt()
        for change in self.event.files:
            if kind == "pre_write":
                self.pre_write(change)
            elif kind in ("post_write", "post_read", "check"):
                self.post_write(change)
        result = self.result()
        del self.state.notices[:-MAX_NOTICES_KEPT]
        write_json(self.state_path, asdict(self.state))
        write_json(self.probes_path, self.probes)
        return result


def handle(event: Event, config: Config) -> Result:
    return Engine(event, config).run()
