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
import sys
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
import guideline_runners
from guideline_runners import (
    SKIPPED_FOR_BUDGET, Detection, Finding, Target, detect, glob_matches,
    matches_code, runs_on, setting_tools,
)

EXCLUDED_DIRECTORIES = frozenset({
    ".git", "node_modules", ".venv", "venv", "site-packages", "__pycache__",
})
EXCLUDED_AT_ROOT = frozenset({"dist", "build", "vendor"})
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
DROPPED_NOTICE_CHARS = 600
NOTICE_COUNT_CHARS = 60
DROPPED_FILES_NAMED = 3
MAX_CONTENT_CHARS = 1_000_000
MAX_PROMPT_CHARS = 100_000
MAX_FILES_PER_EVENT = 50
MAX_NOTICES_KEPT = 200
MAX_NAME_CHARS = 80
STATE_MAX_AGE_SEC = 7 * 24 * 60 * 60
# The ESLint traces end this long after the detector budget, inside the
# 10 s hook timeout.
TRACE_GRACE_S = 4.0
BUDGET_SEC = {"pre_write": 2.5, "post_write": 5.0, "check": 30.0}
EVENT_KINDS = frozenset({
    "session_start", "cleared", "compacted", "prompt", "pre_write",
    "post_write", "post_read", "check",
})
MAIN_AGENT = "main"
PATH_IN_PROMPT = re.compile(r"[\w./\\-]*\.\w+(?:\.\w+)*")
SHEBANG_LANGUAGES = {"python": "python", "node": "javascript"}
UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_-]")


def resolve_in_root(
    raw: str, cwd: str, root: str, follow: bool = True,
) -> Path | None:
    """Resolve a payload path; None when it leaves the project root.
    Without follow, a path below the root keeps its own names, also of
    symlinks, as linters see it."""
    try:
        top = Path(root).resolve()
        full = Path(os.path.normpath(Path(cwd) / raw))
        lexical = Path(os.path.normpath(root))
        if follow:
            resolved = full.resolve()
        elif full.is_relative_to(lexical):
            resolved = top / full.relative_to(lexical)
        else:
            resolved = full.parent.resolve() / full.name
        inside = resolved.is_relative_to(top)
    except (OSError, ValueError):
        return None
    return resolved if inside else None


def safe_name(raw: str) -> str:
    return UNSAFE_NAME_CHARS.sub("_", raw)[:MAX_NAME_CHARS] or "unknown"


class FileChange(NamedTuple):
    path: str
    before: str | None
    after: str | None
    problem: str = ""
    before_problem: str = ""
    source: str = ""


class Event(NamedTuple):
    kind: str
    session: str
    agent: str
    cwd: str
    root: str
    prompt: str = ""
    files: tuple[FileChange, ...] = ()
    channel: bool = True
    skipped: tuple[str, ...] = ()
    # The changes past the file limit, still read for lint settings.
    unchecked: tuple[FileChange, ...] = ()


class Result(NamedTuple):
    deny: str | None = None
    context: str | None = None
    notice: str | None = None


def optional_text(value: object) -> str | None:
    if isinstance(value, str) and len(value) <= MAX_CONTENT_CHARS:
        return value
    return None


def file_change(item: dict[str, object]) -> FileChange:
    after = item.get("after")
    problem = item.get("problem")
    if isinstance(after, str) and len(after) > MAX_CONTENT_CHARS:
        problem = "it is larger than 1 MB"
    before_problem = item.get("before_problem")
    source = item.get("source")
    return FileChange(
        str(item["path"]), optional_text(item.get("before")),
        optional_text(after), problem if isinstance(problem, str) else "",
        before_problem if isinstance(before_problem, str) else "",
        source if isinstance(source, str) else "",
    )


def file_changes(raw: object) -> tuple[FileChange, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        file_change(item) for item in raw
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    )


def shebang_language(content: str | None) -> str | None:
    """The language a `#!` line names, for a file with no extension."""
    if content is None or not content.startswith("#!"):
        return None
    words = content[2:].partition("\n")[0].split()
    if words and words[0].endswith("/env"):
        words = [word for word in words[1:] if not word.startswith("-")]
    if not words:
        return None
    name = words[0].rsplit("/", 1)[-1].rstrip("0123456789.")
    return SHEBANG_LANGUAGES.get(name)


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
    files = file_changes(data.get("files"))
    limit = len(files) if data["kind"] == "check" else MAX_FILES_PER_EVENT
    return Event(
        kind=data["kind"],
        session=safe_name(texts["session"]),
        agent=safe_name(texts["agent"] or MAIN_AGENT),
        cwd=texts["cwd"],
        root=texts["root"] or texts["cwd"],
        prompt=texts["prompt"][:MAX_PROMPT_CHARS],
        files=files[:limit],
        channel=data.get("channel") is not False,
        skipped=tuple(change.path for change in files[limit:]),
        unchecked=tuple(files[limit:]),
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
    def rule(self) -> tuple[str, str]:
        return (self.finding.tool, self.finding.code)


def guideline_for(
    finding: Finding, guidelines: Iterable[Guideline]
) -> Guideline | None:
    """Map a finding to the guideline with the longest matching code."""
    best: tuple[int, Guideline] | None = None
    for guideline in guidelines:
        for tool, code in guideline.detectors:
            matches = tool == finding.tool and matches_code(
                tool, finding.code, code
            )
            if matches and (best is None or len(code) > best[0]):
                best = (len(code), guideline)
    return best[1] if best else None


def new_hits(after: list[Hit], before: list[Hit]) -> list[Hit]:
    """Hits of each rule the edit finds more often than before. An edit
    that keeps a rule's count, such as a changed comment or a changed
    line next to an old finding, adds none of it. Of a grown rule, the
    hits on lines that the old findings did not have are named."""
    grown = Counter(hit.rule for hit in after)
    grown.subtract(hit.rule for hit in before)
    old_lines = Counter((hit.rule, hit.text) for hit in before)
    added = []
    for rule in (rule for rule, extra in grown.items() if extra > 0):
        hits = [hit for hit in after if hit.rule == rule]
        fresh = []
        for hit in hits:
            if old_lines[rule, hit.text] > 0:
                old_lines[rule, hit.text] -= 1
            else:
                fresh.append(hit)
        added += fresh or hits
    return added


def dropped_notice(dropped: dict[str, int]) -> str:
    """Count the findings that did not fit and name whole files to check,
    within DROPPED_NOTICE_CHARS less its separator."""
    return name_files(
        f"Notice: {sum(dropped.values())} more findings did not fit in "
        f"this message. Run the check command on ",
        list(dropped), " to see all of them.", "the edited files",
    )


ANNOUNCE_PREFIX = (
    "Start your next message to the user with this line exactly as written, "
    "on its own first line and with nothing appended to it, so the developer "
    "can see which pstack code-quality guidelines were issued. This printed "
    "line is all they need about guidelines, so there's no need to add, "
    "anywhere in your reply, which ones applied: "
)


def announcement(issued: list[str]) -> str:
    """The exact line the agent prints so the user sees every guideline
    this call issued."""
    unique = list(dict.fromkeys(issued))
    noun = "guideline" if len(unique) == 1 else "guidelines"
    named = ", ".join(unique)
    return f"{ANNOUNCE_PREFIX}pstack code quality: {named} {noun} provided"


def name_files(head: str, files: list[str], tail: str, fallback: str) -> str:
    """Join head, the first whole file paths that fit, and tail, within
    DROPPED_NOTICE_CHARS less its separator; use `fallback` when no path
    fits."""
    for shown in range(min(len(files), DROPPED_FILES_NAMED), 0, -1):
        others = len(files) - shown
        named = ", ".join(files[:shown])
        named += f" and {others} more files" * (others > 0)
        if len(head + named + tail) <= DROPPED_NOTICE_CHARS - 2:
            return head + named + tail
    return head + fallback + tail


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
        self.cap = sys.maxsize if event.kind == "check" else MAX_TEXT_CHARS
        self.issued: list[str] = []

    def classify(self, raw: str, content: str | None) -> CodeFile | str:
        """Describe a payload path, or say why no guideline covers it."""
        path = resolve_in_root(
            raw, self.event.cwd, self.event.root, follow=False
        )
        if path is None:
            return "it is outside the project"
        language = language_of(Path(raw).name, self.extensions)
        if language is None and not Path(raw).suffix:
            language = shebang_language(content)
        if language is None:
            return "no guideline covers its file type"
        root = Path(self.event.root).resolve()
        rel = path.relative_to(root).as_posix()
        directories = rel.split("/")[:-1]
        if set(directories) & EXCLUDED_DIRECTORIES or (
            directories and directories[0] in EXCLUDED_AT_ROOT
        ):
            return "it is in a dependency or build directory"
        if rel.endswith(EXCLUDED_SUFFIX):
            return "it is minified"
        applicable = (
            self.applicable(guideline, path, rel, root)
            for guideline in self.guidelines
            if guideline.enabled and language in guideline.languages
        )
        return CodeFile(path, rel, language, tuple(filter(None, applicable)))

    def code_file(self, change: FileChange) -> CodeFile | None:
        known = change.before if change.after is None else change.after
        file = self.classify(change.path, known)
        if isinstance(file, CodeFile):
            if change.problem:
                self.report_unbuilt(file.rel, change.problem)
            return file
        if self.event.kind == "check":
            reason = change.problem or file
            notice = f"Notice: did not check {change.path}: {reason}"
            self.notices.append(notice)
        return None

    def report_unbuilt(self, rel: str, problem: str) -> None:
        later = ", so PostToolUse checks it" * (self.event.kind == "pre_write")
        self.notices.append(f"Notice: did not check {rel}: {problem}{later}")

    @staticmethod
    def applicable(
        guideline: Guideline, path: Path, rel: str, root: Path
    ) -> Guideline | None:
        """The guideline minus detectors the project turns off; None when
        it is out of scope or the project turns off every detector."""
        in_paths = not guideline.paths or any(
            glob_matches(rel, glob) for glob in guideline.paths
        )
        excluded = any(glob_matches(rel, glob) for glob in guideline.exclude)
        if excluded or not in_paths:
            return None
        return guideline

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
            "not run. Their guidelines apply as warnings."
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
                if runs_on(tool, file.language):
                    codes.setdefault(tool, set()).add(code)
        target = Target(
            content, file.path, frozenset(), Path(self.event.root).resolve()
        )
        frozen = {tool: frozenset(found) for tool, found in codes.items()}
        results = detect(Detection(target, frozen, self.deadline, self.probes))
        hits, failed = [], set()
        lines = content.split("\n")
        for tool, result in results.items():
            if result.problem and not quiet:
                self.report_problem(file, tool, result.problem)
            if result.findings is None:
                failed.add(tool)
                continue
            for finding in result.findings:
                owner = guideline_for(finding, file.guidelines)
                if owner is not None:
                    line = finding.line
                    text = lines[line - 1] if 0 < line <= len(lines) else ""
                    hits.append(Hit(owner, finding, file.rel, text.strip()))
        return hits, failed

    def pre_write(self, change: FileChange) -> None:
        file = self.code_file(change)
        if file is None or change.after is None:
            return
        self.note_language(file.language, file.guidelines)
        hits, _ = self.scan(file, change.after)
        old: list[Hit] = []
        failed: set[str] = set()
        if change.before is not None and hits:
            # A moved file's old findings come from its old path's rules.
            moved = change.source and change.source != change.path
            source = self.code_file(
                change._replace(path=change.source, after=change.before)
            ) if moved else file
            if source is not None:
                old, failed = self.scan(source, change.before, quiet=True)
        blocking = [
            hit for hit in new_hits(hits, old)
            if hit.guideline.severity == "block" and hit.finding.blocks
        ]
        added = [hit for hit in blocking if hit.finding.tool not in failed]
        unproven = sorted({
            hit.finding.tool for hit in blocking if hit.finding.tool in failed
        })
        if unproven:
            self.notices.append(
                f"Notice: {', '.join(unproven)} could not check the current "
                f"{file.rel}, so its findings in this edit are warnings."
            )
        root = Path(self.event.root).resolve()
        guideline_runners.trace_deadline = self.deadline + TRACE_GRACE_S
        settings: dict[str, frozenset[str]] = {}
        # A file can be its own lint config, so it is not left out.
        for other in (*self.event.files, *self.event.unchecked) if added else ():
            for raw in {other.path, other.source} - {""}:
                # The code file keeps its names through symlinked folders,
                # so a setting counts by its own names or its real path.
                real = resolve_in_root(raw, self.event.cwd, self.event.root)
                names = {real, resolve_in_root(
                    raw, self.event.cwd, self.event.root, follow=False,
                )} - {None}
                tools = frozenset().union(*(
                    setting_tools(
                        setting, file.path, file.language, root, other.after
                    ) for setting in names
                ))
                if tools:
                    shown = real or next(iter(names))
                    settings[shown.relative_to(root).as_posix()] = tools
        changed = frozenset().union(*settings.values())
        held = sorted({hit.finding.tool for hit in added} & changed)
        if held:
            self.notices.append(
                f"Notice: this edit also changes {', '.join(sorted(settings))},"
                f" so {', '.join(held)} findings in {file.rel} are warnings "
                "until it is written."
            )
            if "eslint" in held and guideline_runners.trace_failed:
                self.notices.append(
                    "Notice: the files ESLint reads for its config could not "
                    "be listed, so any changed script or data file counts."
                )
            added = [hit for hit in added if hit.finding.tool not in changed]
        if added and change.before_problem:
            self.notices.append(
                f"Notice: could not read the current {file.rel}: "
                f"{change.before_problem}, so its findings are warnings."
            )
            added = []
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
        file = self.code_file(change)
        if file is None:
            return
        self.note_language(file.language, file.guidelines)
        if change.after is None or self.event.kind == "post_read":
            return
        hits, _ = self.scan(file, change.after)
        if self.event.kind == "check":
            hits = [
                hit._replace(severity=hit.guideline.severity)
                if hit.finding.blocks else hit
                for hit in hits
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

    @staticmethod
    def hit_head(hit: Hit) -> str:
        finding = hit.finding
        return (
            f"[{hit.guideline.id}] {hit.severity}: {finding.tool}:"
            f"{finding.code} at {hit.rel}:{finding.line}"
        )

    def hit_item(self, hit: Hit) -> str:
        head = self.hit_head(hit)
        if self.suppressed(hit.guideline.id):
            return f"{head} (guidance sent earlier)"
        return f"{head}\n{hit.guideline.body}"

    def add(
        self, items: list[str], text: str, reserve: int = 0,
        issues: str | None = None,
    ) -> bool:
        """Append the item when the whole text, plus `reserve` characters
        kept free, stays under the size cap. Once this call issues a
        guideline (`issues` names one), the announcement that names every
        issued guideline must fit too."""
        used = sum(len(item) + 2 for item in items)
        issued = [*self.issued, *([issues] if issues else [])]
        if issued and self.cap != sys.maxsize:
            reserve += len(announcement(issued)) + 2
        if used + len(text) + reserve > self.cap:
            return False
        items.append(text)
        return True

    def add_notices(self, items: list[str], reserve: int = 0) -> list[str]:
        """Add every notice of this call, keeping `reserve` characters free
        for what follows; return the notices new to this agent.

        A notice is one line, so it repeats on each call it applies to.
        Only the message to the user is sent once.
        """
        unique = list(dict.fromkeys(self.notices))
        added = [
            notice for notice in unique
            if self.add(items, notice, reserve + NOTICE_COUNT_CHARS)
        ]
        if len(added) < len(unique):
            self.add(items, (
                f"Notice: {len(unique) - len(added)} more notices did not fit "
                f"in this message."
            ), reserve)
        new = [notice for notice in added if notice not in self.state.notices]
        self.state.notices += new
        return new

    def add_hits(self, items: list[str], reserve: int = 0) -> None:
        """Add each hit in full, or as its rule and line when the full
        text does not fit; keep `reserve` characters free after them."""
        ordered = sorted(self.hits, key=lambda hit: (
            hit.severity != "block", hit.rel, hit.finding.line,
            hit.guideline.id,
        ))
        dropped: dict[str, int] = {}
        for hit in ordered:
            repeated = self.suppressed(hit.guideline.id)
            kept = DROPPED_NOTICE_CHARS + reserve
            issues = None if repeated else hit.guideline.id
            if self.add(items, self.hit_item(hit), kept, issues):
                if not repeated:
                    self.state.sent[hit.guideline.id] = self.state.prompt
                    self.issued.append(hit.guideline.id)
            elif not self.add(items, self.hit_head(hit), kept):
                dropped[hit.rel] = dropped.get(hit.rel, 0) + 1
        if dropped:
            self.add(items, dropped_notice(dropped), reserve)

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
            if self.add(items, text, issues=guideline_id):
                self.state.sent[guideline_id] = self.state.prompt
                self.issued.append(guideline_id)
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
            self.add_hits(items, NOTICE_COUNT_CHARS * bool(self.notices))
            self.add_notices(items)
            self.announce(items)
            return Result(deny="\n\n".join(items))
        if not self.event.channel:
            self.queue_fulls()
            return Result()
        if kind == "pre_write":
            self.hits = []
        items = [] if kind == "check" else [CONTEXT_HEADER]
        if kind != "check" and self.notices:
            self.cap -= NOTICE_COUNT_CHARS
        notices = self.add_notices(
            items, DROPPED_NOTICE_CHARS * bool(self.hits)
        )
        self.add_hits(items)
        self.add_fulls(items)
        if kind == "check":
            text = "\n\n".join([*items, OVERRIDE_LINE])
            return Result(text if self.blocked else None, text)
        if len(items) == 1:
            return Result()
        self.announce(items)
        return Result(None, "\n\n".join(items), "\n".join(notices) or None)

    def announce(self, items: list[str]) -> None:
        """Ask the agent to tell the user which guidelines this call
        issued; add() keeps room for it."""
        if self.issued:
            items.insert(1, announcement(self.issued))

    def run(self) -> Result:
        kind = self.event.kind
        if self.event.skipped:
            self.notices.append(name_files(
                f"Notice: did not check {len(self.event.skipped)} more "
                f"files: a hook call checks at most {MAX_FILES_PER_EVENT}. "
                f"Run the check command on ",
                list(self.event.skipped), ".", "the files after the "
                f"first {MAX_FILES_PER_EVENT} in this edit",
            ))
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
