#!/usr/bin/env python3
"""Read-only worktree prune audit.

Classifies every git worktree by size, merge state, uncommitted work,
remote/PR state, and the most recent chat that operated in it. Emits a table
sorted by size with a suggested bucket. Never deletes anything; deletion stays
a human-gated step in the playbook.

    worktree_audit.py [repo-path] [transcripts-path]

Python standard library only, forever. No pip dependency. `git`, `gh`, and
`du` stay external commands; JSON and the transcript scan are done here, so
this script degrades on neither `jq` nor `ripgrep`.
"""

from __future__ import annotations

import json
import locale
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "Discovery",
    "Row",
    "audit_lines",
    "classify_bucket",
    "human_size",
    "main",
    "parse_worktrees",
]

HEADER = ("SIZE\tAGE\tMERGED\tDIRTY\tREMOTE\tPR\tLAST_CHAT\tBUCKET"
          "\tWORKTREE")
UNKNOWN = "?"
BYTE_ROUND_TRIP = "surrogateescape"
ABSENT = "-"
FALLBACK_BASE_BRANCH = "main"
RECENT_CHAT_DAYS = 4
SECONDS_PER_DAY = 86400
PR_QUERY_LIMIT = "1000"
PR_QUERY_FIELDS = "number,state,headRefName,headRefOid"
TRANSCRIPTS_SUBPATH = Path(".claude") / "projects"
WORKTREE_FIELD_PREFIX = "worktree "
PRUNABLE_FIELD_PREFIX = "prunable"
SYMREF_HEAD = re.compile(r"ref: refs/heads/(.*)[ \t]HEAD$")
LEADING_NUMBER = re.compile(r"\d*\.?\d*")
SIZE_UNIT_ORDER = {
    "k": 1, "K": 1, "M": 2, "G": 3, "T": 4,
    "P": 5, "E": 6, "Z": 7, "Y": 8, "R": 9, "Q": 10,
}


@dataclass(frozen=True)
class Discovery:
    """Facts gathered once for the whole run, before any worktree is read.

    `pull_requests` is None when the `gh` payload could not be read as a JSON
    array, which leaves the PR column blank and the facts incomplete.
    """

    base_branch: str
    pull_requests: list[dict] | None
    known: bool


@dataclass(frozen=True)
class PullRequestFacts:
    """The PR column plus the two fields the safe bucket is decided from."""

    column: str
    state: str
    head_oid: str
    known: bool


@dataclass(frozen=True)
class Row:
    """One output line, before it is sorted by size."""

    size: str
    age: str
    merged: str
    dirty: str
    remote: str
    pull_request: str
    last_chat: str
    bucket: str
    worktree: str

    def rendered(self) -> str:
        """The tab-separated line, in header order."""
        return "\t".join([
            self.size, self.age, self.merged, self.dirty, self.remote,
            self.pull_request, self.last_chat, self.bucket, self.worktree,
        ])


def command_text(argv: list[str], stdout: int, stderr: int) -> tuple[int, str]:
    """Run `argv` and return its exit status with the captured stream.

    Exactly one of `stdout` and `stderr` is captured. A missing executable
    becomes status 127 and the OS error text, which is what a shell reports
    for the same call.

    Decoding is `surrogateescape`, the same handler argv arrives under, so a
    worktree path holding a byte that is not valid UTF-8 flows through this
    boundary and back out to the table instead of aborting the whole audit
    before its first line is printed.
    """
    try:
        done = subprocess.run(argv, stdout=stdout, stderr=stderr,
                              text=True, errors=BYTE_ROUND_TRIP, check=False)
    except OSError as error:
        return 127, str(error)
    captured = done.stdout if done.stdout is not None else done.stderr
    return done.returncode, (captured or "").rstrip("\n")


def stdout_of(argv: list[str]) -> tuple[int, str]:
    """Status and stdout of `argv`, discarding its stderr."""
    return command_text(argv, subprocess.PIPE, subprocess.DEVNULL)


def merged_output_of(argv: list[str]) -> tuple[int, str]:
    """Status of `argv` and its stdout and stderr as one stream."""
    return command_text(argv, subprocess.PIPE, subprocess.STDOUT)


def stderr_of(argv: list[str]) -> tuple[int, str]:
    """Status and stderr of `argv`, discarding its stdout."""
    return command_text(argv, subprocess.DEVNULL, subprocess.PIPE)


def warn(message: str) -> None:
    """Report a degraded fact on stderr without failing the run."""
    print(f"warn: {message}", file=sys.stderr)


def whole_days(seconds: int) -> int:
    """Whole days in `seconds`, truncated toward zero as the shell does."""
    days = abs(seconds) // SECONDS_PER_DAY
    return -days if seconds < 0 else days


def parse_worktrees(porcelain: str) -> list[tuple[str, str]]:
    """Return (path, state) for every record of `git worktree list -z`.

    A blank field terminates each record. The caller drops the first record,
    which is always the primary worktree.
    """
    records: list[tuple[str, str]] = []
    path = ""
    state = "ok"
    for field in porcelain.split("\0")[:-1]:
        if not field:
            if path:
                records.append((path, state))
            path = ""
            state = "ok"
        elif field.startswith(WORKTREE_FIELD_PREFIX):
            path = field[len(WORKTREE_FIELD_PREFIX):]
        elif field.startswith(PRUNABLE_FIELD_PREFIX):
            state = "prunable"
    if path:
        records.append((path, state))
    return records


def classify_bucket(dirty: str, pr_state: str, recent: bool, ancestry: str,
                    merged_head_match: bool, facts_known: bool) -> str:
    """Decide from explicit facts. Unknown facts can never establish safe."""
    if dirty.startswith("wip:"):
        return "hold-wip"
    if pr_state == "OPEN":
        return "hold-open-pr"
    if recent:
        return "verify-recent-chat"
    if not facts_known:
        return "review"
    if ancestry == "YES":
        return "safe"
    if pr_state == "MERGED" and merged_head_match:
        return "safe"
    return "review"


def discover_base_branch() -> str:
    """Name the trunk the remote publishes, falling back to main.

    Assuming main leaves every worktree unresolved on a repo that trunks
    elsewhere; main is the last resort, when the remote publishes no usable
    HEAD.
    """
    _, text = stdout_of(["git", "ls-remote", "--symref", "origin", "HEAD"])
    names = [match.group(1) for line in text.split("\n")
             if (match := SYMREF_HEAD.match(line))]
    return "\n".join(names) or FALLBACK_BASE_BRANCH


def read_pull_requests(payload: str) -> list[dict] | None:
    """Parse the `gh pr list` array, or None when it is not one."""
    try:
        entries = json.loads(payload)
    except ValueError:
        return None
    return entries if isinstance(entries, list) else None


def discover() -> Discovery:
    """Gather the run-wide facts, warning on each one that stays unknown."""
    base_branch = discover_base_branch()
    known = True
    refspec = f"+refs/heads/{base_branch}:refs/remotes/origin/{base_branch}"
    status, errors = stderr_of(["git", "fetch", "origin", refspec])
    if status != 0:
        known = False
        warn(f"could not fetch origin/{base_branch}; merged column may be "
             f"stale: {errors}")
    status, payload = merged_output_of([
        "gh", "pr", "list", "--author", "@me", "--state", "all",
        "--limit", PR_QUERY_LIMIT, "--json", PR_QUERY_FIELDS,
    ])
    if status != 0:
        known = False
        warn(f"gh pr list failed; PR column will be empty: {payload}")
        payload = "[]"
    return Discovery(base_branch, read_pull_requests(payload), known)


def size_column(worktree: str) -> str:
    """The `du -sh` size of `worktree`, or ? when du refuses."""
    status, text = stdout_of(["du", "-sh", worktree])
    if status != 0:
        return UNKNOWN
    fields = text.split()
    return fields[0] if fields else UNKNOWN


def head_facts(worktree: str, now: int) -> tuple[str, str, bool]:
    """The worktree HEAD, its age in days, and whether both are known."""
    status, head = stdout_of(["git", "-C", worktree, "rev-parse", "HEAD"])
    if status != 0:
        return UNKNOWN, UNKNOWN, False
    status, stamp = stdout_of(
        ["git", "-C", worktree, "log", "-1", "--format=%ct", "HEAD"])
    if status != 0:
        return head, UNKNOWN, False
    return head, f"{whole_days(now - int(stamp))}d", True


def ancestry_of(head: str, base_branch: str) -> tuple[str, bool]:
    """Whether `head` is already on the trunk, and whether git could say."""
    if head == UNKNOWN:
        return UNKNOWN, False
    status, _ = stdout_of(["git", "merge-base", "--is-ancestor", head,
                           f"origin/{base_branch}"])
    if status == 0:
        return "YES", True
    if status == 1:
        return "no", True
    return UNKNOWN, False


def dirty_of(worktree: str) -> tuple[str, bool]:
    """Uncommitted work in `worktree`: clean, wip:N, scratch:N, or unknown."""
    status, porcelain = stdout_of(
        ["git", "-C", worktree, "status", "--porcelain"])
    if status != 0:
        return "unknown", False
    if not porcelain:
        return "clean", True
    lines = porcelain.split("\n")
    tracked = sum(1 for line in lines if not line.startswith("??"))
    if tracked:
        return f"wip:{tracked}", True
    return f"scratch:{len(lines)}", True


def branch_of(worktree: str) -> tuple[str, bool]:
    """The checked-out branch, empty when detached or unreadable."""
    status, branch = stdout_of(
        ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"])
    if status != 0:
        return "", False
    return ("" if branch == "HEAD" else branch), True


def remote_of(worktree: str, branch: str, head: str) -> tuple[str, bool]:
    """How `branch` relates to its origin ref: pushed, aheadN, or no-remote."""
    if not branch:
        return "detached", True
    status, remote_sha = stdout_of(
        ["git", "-C", worktree, "for-each-ref", "--format=%(objectname)",
         f"refs/remotes/origin/{branch}"])
    if status != 0:
        return "unknown", False
    if not remote_sha:
        return "no-remote", True
    if remote_sha == head:
        return "pushed", True
    status, ahead = stdout_of(["git", "-C", worktree, "rev-list", "--count",
                               f"origin/{branch}..HEAD"])
    if status != 0:
        return "unknown", False
    return f"ahead{ahead}", True


def tsv_value(value: object) -> str:
    """Render a JSON field the way `jq @tsv` does, with null as empty."""
    return "" if value is None else str(value)


def pull_request_facts(branch: str,
                       pull_requests: list[dict] | None) -> PullRequestFacts:
    """The PR for `branch`, taking the first when the author has several."""
    if not branch:
        return PullRequestFacts(ABSENT, ABSENT, ABSENT, True)
    if pull_requests is None:
        return PullRequestFacts(ABSENT, ABSENT, ABSENT, False)
    for entry in pull_requests:
        if entry.get("headRefName") != branch:
            continue
        number = tsv_value(entry.get("number"))
        state = tsv_value(entry.get("state"))
        head_oid = tsv_value(entry.get("headRefOid")) or ""
        return PullRequestFacts(f"#{number}/{state}", state, head_oid, True)
    return PullRequestFacts(ABSENT, ABSENT, ABSENT, True)


def transcript_files(root: Path) -> tuple[list[Path], bool]:
    """Every visible file under `root`, and whether the walk hit no error.

    Hidden entries are skipped, matching the search this replaced. Symlinked
    directories are not followed.
    """
    files: list[Path] = []
    readable = True

    def unreadable(_error: OSError) -> None:
        nonlocal readable
        readable = False

    for parent, directories, names in os.walk(root, onerror=unreadable):
        directories[:] = sorted(name for name in directories
                                if not name.startswith("."))
        files += [Path(parent) / name for name in sorted(names)
                  if not name.startswith(".")]
    return files, readable


def chat_stamps(worktrees: list[str],
                transcripts: Path) -> tuple[dict[str, int], bool]:
    """Newest transcript mtime per worktree, and whether the scan was clean.

    Transcripts live at `<transcripts>/<encoded-cwd>/<uuid>.jsonl`, where
    `<encoded-cwd>` is a session's cwd with every "/" turned into "-". A
    session run inside a worktree lives under that worktree's own directory,
    so the whole tree is scanned, not one repo's.

    Paths are matched literally, so regex metacharacters in a worktree path
    are inert.
    """
    stamps = {worktree: 0 for worktree in worktrees}
    if not transcripts.is_dir():
        return stamps, True
    needles = {worktree: (f"{worktree}/".encode(errors=BYTE_ROUND_TRIP),
                          f'{worktree}"'.encode(errors=BYTE_ROUND_TRIP))
               for worktree in worktrees}
    files, known = transcript_files(transcripts)
    for path in files:
        try:
            data = path.read_bytes()
            stamp = int(path.stat().st_mtime)
        except OSError:
            known = False
            continue
        for worktree, pair in needles.items():
            if stamp > stamps[worktree] and any(one in data for one in pair):
                stamps[worktree] = stamp
    return stamps, known


def chat_columns(stamp: int, now: int) -> tuple[str, bool]:
    """The LAST_CHAT date and whether that chat counts as recent."""
    if stamp <= 0:
        return ABSENT, False
    last = datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d")
    return last, whole_days(now - stamp) <= RECENT_CHAT_DAYS


def audit_row(worktree: str, discovery: Discovery, chat_stamp: int,
              chat_known: bool, now: int) -> Row:
    """Read every fact about one live worktree and bucket it."""
    head, age, head_known = head_facts(worktree, now)
    ancestry, ancestry_known = ancestry_of(head, discovery.base_branch)
    dirty, dirty_known = dirty_of(worktree)
    branch, branch_known = branch_of(worktree)
    remote, remote_known = remote_of(worktree, branch, head)
    pull = pull_request_facts(branch, discovery.pull_requests)
    known = all([discovery.known, chat_known, head_known, ancestry_known,
                 dirty_known, branch_known, remote_known, pull.known])
    last_chat, recent = chat_columns(chat_stamp, now)
    merged_head_match = (pull.state == "MERGED" and head != UNKNOWN
                         and pull.head_oid == head)
    bucket = classify_bucket(dirty, pull.state, recent, ancestry,
                             merged_head_match, known)
    return Row(size_column(worktree), age, ancestry, dirty, remote,
               pull.column, last_chat, bucket, worktree)


def prunable_row(worktree: str) -> Row:
    """The fixed row for a worktree whose directory is already gone."""
    return Row(ABSENT, UNKNOWN, ABSENT, ABSENT, ABSENT, ABSENT, ABSENT,
               "prunable", worktree)


def human_size(size: str) -> tuple[int, float]:
    """Unit order and magnitude of a size, as `sort -h` reads it.

    A size with no digits, or one whose digits are all zero, carries order 0,
    so `?` and `-` sort against a plain byte count rather than against a unit.
    """
    text = size.lstrip(" \t")
    sign = -1 if text.startswith("-") else 1
    digits = text[1:] if sign < 0 else text
    number = LEADING_NUMBER.match(digits).group()
    unit = digits[len(number):len(number) + 1]
    magnitude = float(number) if number.strip(".") else 0.0
    order = SIZE_UNIT_ORDER.get(unit, 0) if magnitude else 0
    return sign * order, sign * magnitude


def size_sort_key(row: Row) -> tuple[int, float, str]:
    """Sort rows by human-readable size, breaking ties on the whole line.

    Equal sizes are settled by collating the whole line, which is what a
    size-keyed sort falls back to. The collation follows LC_COLLATE, so two
    rows of the same size land in the order the environment asks for.
    """
    order, magnitude = human_size(row.size)
    return order, magnitude, locale.strxfrm(row.rendered())


def audit_lines(records: list[tuple[str, str]], discovery: Discovery,
                transcripts: Path, now: int) -> list[str]:
    """Render every record as a row, largest first."""
    live = [worktree for worktree, state in records if state != "prunable"]
    stamps, chat_known = chat_stamps(live, transcripts)
    rows = [
        prunable_row(worktree) if state == "prunable"
        else audit_row(worktree, discovery, stamps[worktree], chat_known, now)
        for worktree, state in records
    ]
    rows.sort(key=size_sort_key, reverse=True)
    return [row.rendered() for row in rows]


def repo_root() -> str:
    """The enclosing repository's root, empty when there is none."""
    status, root = stdout_of(["git", "rev-parse", "--show-toplevel"])
    return root if status == 0 else ""


def main(argv: list[str]) -> int:
    """Audit every worktree of the repo and print the table."""
    try:
        locale.setlocale(locale.LC_COLLATE, "")
    except locale.Error:
        pass
    repo = (argv[0] if argv and argv[0] else "") or repo_root()
    if not repo:
        print("not in a git repo; pass a repo path", file=sys.stderr)
        return 1
    try:
        os.chdir(repo)
    except OSError as error:
        print(f"cannot enter {repo}: {error}", file=sys.stderr)
        return 1
    transcripts = Path(argv[1]) if len(argv) > 1 and argv[1] else (
        Path.home() / TRANSCRIPTS_SUBPATH)
    now = int(time.time())
    discovery = discover()
    _, porcelain = stdout_of(["git", "worktree", "list", "--porcelain", "-z"])
    print(HEADER)
    for line in audit_lines(parse_worktrees(porcelain)[1:], discovery,
                            transcripts, now):
        print(line)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors=BYTE_ROUND_TRIP)
    sys.stderr.reconfigure(errors=BYTE_ROUND_TRIP)
    sys.exit(main(sys.argv[1:]))
