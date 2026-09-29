#!/usr/bin/env python3
"""Create a per-task agent run directory.

    create_agent_run.py --slug SLUG --kind {writer,reviewer}
                        (--base COMMIT-ISH | --worktree PATH)
                        [--model MODEL] < task.md

A run directory (`RUN`) holds a spawner-written `brief.md`, an empty
`corrections/` directory the spawner appends to later, and, for a fresh
writer, a new worktree on branch `agent/<run id>`. `--worktree` reuses an
existing checkout instead of creating one. The task body is read from stdin;
`RUN` is the only thing printed on stdout, so a caller can capture it
directly.

Python standard library only, forever. Git stays an external command; this
script only shapes the paths and the brief text around it.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CreationFailure",
    "Request",
    "brief_text",
    "build_parser",
    "main",
]

KINDS = ("writer", "reviewer")
SLUG_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
AGENT_RUNS_DIR_VAR = "AGENT_RUNS_DIR"
RUNS_SUBDIR = ".agent-runs"
GITIGNORE_NAME = ".gitignore"
GITIGNORE_BODY = "*\n"
DETACHED = "(detached)"
BRIEF_MODE = 0o444
RUN_ID_SUFFIX_BYTES = 4


@dataclass(frozen=True)
class Request:
    """One validated invocation, immutable once argument parsing is done.

    `worktree` is already made absolute and, when given, already confirmed
    to be a real git work tree. `task` is the stdin body with trailing
    whitespace stripped and confirmed non-empty.
    """

    slug: str
    kind: str
    base: str | None
    worktree: Path | None
    model: str | None
    task: str


class CreationFailure(Exception):
    """Something failed once `RUN` existed; the caller cleans up and exits 1."""


def oneline(text: str) -> str:
    """Collapse `text` to one line for a single-line stderr report."""
    return " ".join(text.split())


def run_capture(argv: list[str]) -> tuple[int, str]:
    """Run `argv` and return its status with stdout and stderr combined."""
    try:
        done = subprocess.run(argv, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              check=False)
    except OSError as error:
        return 127, str(error)
    return done.returncode, (done.stdout or "").strip()


def absolute_path(path: Path) -> Path:
    """`path`, made absolute against the current directory and normalized."""
    return Path(os.path.abspath(path))


def is_git_worktree(path: Path) -> bool:
    """Whether `path` exists and git recognizes it as a work tree."""
    if not path.is_dir():
        return False
    status, output = run_capture(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"])
    return status == 0 and output == "true"


def slug_type(value: str) -> str:
    """Validate `--slug` against the contract's kebab-case pattern."""
    if not SLUG_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            f"invalid --slug {value!r}; expected [a-z0-9]+(-[a-z0-9]+)*")
    return value


def build_parser() -> argparse.ArgumentParser:
    """The CLI surface: two required flags, one exclusive pair, one optional."""
    parser = argparse.ArgumentParser(
        description="Create a per-task agent run directory.")
    parser.add_argument("--slug", required=True, type=slug_type,
                        help="kebab-case topic; becomes the run id prefix")
    parser.add_argument("--kind", required=True, choices=KINDS)
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--base", metavar="COMMIT-ISH",
                        help="writer only: create a fresh worktree here")
    origin.add_argument("--worktree", metavar="PATH", type=Path,
                        help="reuse an existing checkout or worktree")
    parser.add_argument("--model", help="recorded in brief.md when given")
    return parser


def parse_request(argv: list[str], stdin_text: str,
                  parser: argparse.ArgumentParser) -> Request:
    """Validate `argv` and the stdin body into one immutable `Request`.

    Every rejection here goes through `parser.error`, which prints usage and
    exits 2, matching every other argparse failure.
    """
    args = parser.parse_args(argv)
    if args.base is not None and args.kind != "writer":
        parser.error("--base requires --kind writer")
    worktree = None
    if args.worktree is not None:
        worktree = absolute_path(args.worktree)
        if not is_git_worktree(worktree):
            parser.error(
                f"--worktree {worktree} does not exist or is not a git "
                "work tree")
    task = stdin_text.rstrip()
    if not task:
        parser.error("the task body on stdin must not be empty")
    return Request(slug=args.slug, kind=args.kind, base=args.base,
                   worktree=worktree, model=args.model, task=task)


def main_checkout() -> Path:
    """The parent of the enclosing repo's shared `.git` directory."""
    status, output = run_capture(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
    if status != 0:
        raise CreationFailure(f"not in a git repo: {oneline(output)}")
    return Path(output).parent


def resolve_runs_root() -> Path:
    """`$AGENT_RUNS_DIR` when set, else `<main checkout>/.agent-runs`."""
    value = os.environ.get(AGENT_RUNS_DIR_VAR, "")
    if value:
        return absolute_path(Path(value))
    return main_checkout() / RUNS_SUBDIR


def ensure_gitignore(runs_root: Path) -> None:
    """Write a blanket `.gitignore` under `runs_root` unless one exists."""
    gitignore = runs_root / GITIGNORE_NAME
    if not gitignore.exists():
        gitignore.write_text(GITIGNORE_BODY)


def create_run_dir(runs_root: Path, slug: str) -> tuple[str, Path]:
    """Create a fresh `RUN` directory, retrying the id on a collision."""
    while True:
        run_id = f"{slug}-{secrets.token_hex(RUN_ID_SUFFIX_BYTES)}"
        run_dir = runs_root / run_id
        try:
            run_dir.mkdir()
        except FileExistsError:
            continue
        return run_id, run_dir


def add_worktree(checkout: Path, run_dir: Path, run_id: str,
                 base: str) -> Path:
    """Create `<run_dir>/worktree` on branch `agent/<run id>` at `base`."""
    worktree = run_dir / "worktree"
    status, output = run_capture([
        "git", "-C", str(checkout), "worktree", "add", str(worktree),
        "-b", f"agent/{run_id}", base,
    ])
    if status != 0:
        raise CreationFailure(f"git worktree add failed: {oneline(output)}")
    return worktree


def discard_worktree(checkout: Path, run_dir: Path, run_id: str) -> None:
    """Undo `add_worktree`, best-effort.

    `shutil.rmtree` alone deletes the directory but leaves git's own
    worktree-admin entry and the branch it created behind, so both are
    asked for explicitly first. Either git call is allowed to fail; the
    caller's `rmtree` cleans up the directory regardless.
    """
    run_capture(["git", "-C", str(checkout), "worktree", "remove",
                "--force", str(run_dir / "worktree")])
    run_capture(["git", "-C", str(checkout), "branch", "-D",
                f"agent/{run_id}"])


def branch_of(worktree: Path) -> str:
    """The branch checked out in `worktree`, or `(detached)` when there is none."""
    status, output = run_capture(
        ["git", "-C", str(worktree), "branch", "--show-current"])
    if status != 0:
        raise CreationFailure(
            f"git branch --show-current failed: {oneline(output)}")
    return output or DETACHED


def head_sha_of(worktree: Path) -> str:
    """The full SHA of `worktree`'s current HEAD."""
    status, output = run_capture(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"])
    if status != 0:
        raise CreationFailure(f"git rev-parse HEAD failed: {oneline(output)}")
    return output


def brief_text(request: Request, run_id: str, run_dir: Path, worktree: Path,
               branch: str, base: str, poteto_mode_skill: Path,
               log_decision_script: Path) -> str:
    """Render `brief.md` exactly, per the agent-runs contract.

    Pure: every fact it needs (the run id, the resolved worktree, its branch
    and base SHA, and where the poteto-mode skill and the decision-logging
    script live) is passed in, so this never touches git or the filesystem.
    """
    frontmatter = [
        "---",
        f"kind: {request.kind}",
        f"worktree: {worktree}",
        f"branch: {branch}",
        f"base: {base}",
    ]
    if request.model is not None:
        frontmatter.append(f"model: {request.model}")
    frontmatter.append("---")
    steps = [
        "If you have not loaded the poteto-mode skill yet, read the "
        "Non-negotiables and Principles sections of "
        f"`{poteto_mode_skill}`, then only the skills and playbook steps "
        "this brief names. Search with `rg -n` and read narrow line "
        "ranges, not whole files.",
        f"Read every file in `{run_dir}/corrections/` in name order. A "
        "correction overrides this brief and every correction before it.",
        f"Read `{run_dir}/progress.md` if it exists. Earlier agents on "
        "this run logged their finished steps there. Continue from it and "
        "do not redo those steps.",
        f"Work only in `{worktree}`.",
        "After each step, append one line to "
        f"`{run_dir}/progress.md` that says what you finished.",
    ]
    if request.kind == "writer":
        steps.append("Commit your work yourself with git.")
    steps.append(
        f"Log each decision in `{run_dir}/decisions.tsv` in the "
        "show-me-your-work format with "
        f"`{log_decision_script}`. That means one tab-separated row per "
        "decision with the columns `ts phase decision why evidence "
        "result`, append-only. Log forks you chose, units finished with "
        "their check result, pivots and reverts, and blockers. Skip "
        "trivial actions.")
    steps.append(
        "End with your report. Write it to "
        f"`{run_dir}/agent-report.md`.")
    body = [
        "",
        f"# Agent run {run_id}",
        "",
        "This brief is read-only. Later instructions arrive as files in "
        "`corrections/`.",
        "",
        *(f"{number}. {step}" for number, step in enumerate(steps, 1)),
        "",
        "## Task",
        "",
        request.task,
        "",
    ]
    return "\n".join(frontmatter + body)


def create_run(request: Request) -> Path:
    """Build one `RUN` directory end to end, cleaning up on any failure.

    `RUN` is created exclusively before anything else this call adds, so a
    failure past that point removes exactly what this invocation created:
    the worktree it added (its git-level bookkeeping first, then whatever
    `rmtree` leaves for `RUN` itself to clean up).
    """
    run_dir: Path | None = None
    checkout: Path | None = None
    run_id: str | None = None
    added_worktree = False
    try:
        runs_root = resolve_runs_root()
        runs_root.mkdir(parents=True, exist_ok=True)
        ensure_gitignore(runs_root)
        run_id, run_dir = create_run_dir(runs_root, request.slug)
        (run_dir / "corrections").mkdir()
        if request.base is not None:
            checkout = main_checkout()
            worktree = add_worktree(checkout, run_dir, run_id, request.base)
            added_worktree = True
        else:
            assert request.worktree is not None
            worktree = request.worktree
        branch = branch_of(worktree)
        base_sha = head_sha_of(worktree)
        poteto_mode_skill = Path(__file__).resolve().parents[1] / "SKILL.md"
        log_decision_script = (
            Path(__file__).resolve().parents[3]
            / "skills/show-me-your-work/scripts/log_decision.py")
        text = brief_text(request, run_id, run_dir, worktree, branch,
                          base_sha, poteto_mode_skill, log_decision_script)
        brief_path = run_dir / "brief.md"
        brief_path.write_text(text)
        brief_path.chmod(BRIEF_MODE)
        return run_dir
    except (CreationFailure, OSError) as error:
        if run_dir is not None:
            if added_worktree:
                assert checkout is not None and run_id is not None
                discard_worktree(checkout, run_dir, run_id)
            shutil.rmtree(run_dir, ignore_errors=True)
        raise CreationFailure(oneline(str(error))) from error


def main(argv: list[str]) -> int:
    """Parse, build the run, and print `RUN` alone on success."""
    parser = build_parser()
    request = parse_request(argv, sys.stdin.read(), parser)
    try:
        run_dir = create_run(request)
    except CreationFailure as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
