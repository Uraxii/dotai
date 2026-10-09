#!/usr/bin/env python3
"""Build one Codex run from a watcher's spawn prompt.

Usage: prepare_codex_run.py < spawn-prompt        (env: BEADS_DIR, absolute)

The spawn prompt is one line in one of two forms, read on stdin:

  Claim bead <id> as <actor>. Work in <worktree>.[ Stop at stage=built.][ Grant: <path>...]
  Review bead <id> at <SHA> in <worktree>.[ Grant: <path>...]

Grant paths are absolute, exist, and hold no spaces. Each becomes an extra
`--add-dir`. On success the script empties and recreates
`${XDG_STATE_HOME:-~/.local/state}/pstack/codex-runs/<id>/<role>/`, writes
`prompt.md` and `run.sh` there, prints the run dir, and exits 0. `run.sh` runs
`codex exec` and appends `{"pstack":"codex exited","code":N}` to `codex.jsonl`.

Exit 2, with the reason on stderr and in `<run dir>/refused.txt` once a bead id
parsed, when the run must not start: the prompt does not parse, BEADS_DIR is
missing or relative, the worktree is not a git worktree, a writer targets a main
checkout, the repo uses a per-worktree config file, a grant would make the git
hooks dir or the shared config writable (the coordinator later runs git outside
the sandbox in that repo), or a run is already live in this run dir.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


__all__ = ["Refusal", "Request", "parse_request", "prepare", "main"]

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
EXIT_MARKER = "codex exited"

TOKEN = r"[A-Za-z0-9][A-Za-z0-9._-]*"
GRANTS = r"(?: Grant: (?P<grants>/\S+(?: /\S+)*))?"
WRITER = re.compile(
    rf"Claim bead (?P<bead>{TOKEN}) as (?P<actor>{TOKEN})\. "
    rf"Work in (?P<worktree>/.+?)\.(?P<stop> Stop at stage=built\.)?{GRANTS}"
)
REVIEWER = re.compile(
    rf"Review bead (?P<bead>{TOKEN}) at (?P<sha>[0-9a-f]{{7,40}}) in "
    rf"(?P<worktree>/.+?)\.{GRANTS}"
)


class Refusal(Exception):
    pass


@dataclass(frozen=True)
class Request:
    role: str
    bead: str
    actor: str
    worktree: Path
    sha: str | None
    stop_at_built: bool
    grants: tuple[Path, ...]


def parse_request(text: str) -> Request:
    line = text.strip()
    if match := WRITER.fullmatch(line):
        role, actor, sha = "writer", match["actor"], None
    elif match := REVIEWER.fullmatch(line):
        role, actor, sha = "reviewer", f"reviewer-{match['bead']}", match["sha"]
    else:
        raise Refusal(
            'the prompt matches neither "Claim bead <id> as <actor>. Work in '
            '<worktree>." nor "Review bead <id> at <SHA> in <worktree>."'
        )
    bead = match["bead"]
    extra = tuple(Path(p) for p in (match["grants"] or "").split())
    return Request(
        role=role, bead=bead, actor=actor, worktree=Path(match["worktree"]),
        sha=sha, stop_at_built=bool(match.groupdict().get("stop")),
        grants=extra,
    )


@dataclass(frozen=True)
class GitLayout:
    git_dir: Path
    common_dir: Path
    hooks_dirs: tuple[Path, ...]

    @property
    def config_files(self) -> tuple[Path, ...]:
        return (self.common_dir / "config",)

    @property
    def git_grants(self) -> tuple[Path, ...]:
        common = self.common_dir
        return (self.git_dir, common / "objects", common / "refs", common / "logs")


def git(worktree: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(worktree), *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise Refusal(f"{worktree} is not a git worktree: {result.stderr.strip()}")
    return result.stdout.strip()


def worktree_config_enabled(worktree: Path) -> bool:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(worktree),
         "config", "--type=bool", "--get", "extensions.worktreeConfig"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() == "true"


def read_layout(worktree: Path) -> GitLayout:
    def path(*args: str) -> Path:
        return Path(git(worktree, "rev-parse", "--path-format=absolute", *args))

    common_dir = path("--git-common-dir")
    configured = subprocess.run(
        ["git", "-C", str(worktree), "config", "--get", "core.hooksPath"],
        capture_output=True, text=True,
    ).stdout.strip()
    hooks_dirs = (common_dir / "hooks",)
    if configured:
        hooks_dirs += (worktree / configured,)
    return GitLayout(git_dir=path("--git-dir"), common_dir=common_dir, hooks_dirs=hooks_dirs)


def check_layout(request: Request, layout: GitLayout, grants: tuple[Path, ...]) -> None:
    if request.role == "writer" and layout.git_dir == layout.common_dir:
        raise Refusal(
            f"{layout.git_dir} is a main checkout's git dir; run Codex in a linked "
            "worktree",
        )
    if worktree_config_enabled(request.worktree):
        raise Refusal(
            "the repo sets extensions.worktreeConfig=true; a writable per-worktree "
            "config could set core.hooksPath for later git commands",
        )
    for protected in (*layout.hooks_dirs, *layout.config_files):
        for grant in grants:
            if protected.is_relative_to(grant) or grant.is_relative_to(protected):
                raise Refusal(f"grant {grant} would make {protected} writable")


def ere_escape(text: str) -> str:
    return re.sub(r"([.\[\]()*+?{}|^$\\])", r"\\\1", text)


def check_not_live(run_dir: Path) -> None:
    pattern = f"^bash {ere_escape(str(run_dir))}/run\\.sh$"
    if subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0:
        raise Refusal(f"a Codex run is already live in {run_dir}")


def model_for(role: str) -> str:
    row = "feature, refactoring" if role == "writer" else "judgment and prose"
    roles = json.loads((PLUGIN_ROOT / "models.json").read_text())["roles"]
    [entry] = [r for r in roles if r["role"] == row]
    return entry["models"]["codex"][0]


def writer_prompt(request: Request) -> str:
    bead, actor, tree = request.bead, request.actor, request.worktree
    heartbeat_loop = f"(while sleep 120; do bd heartbeat {bead}; done) & hb=$!; <command>; kill $hb"
    if request.stop_at_built:
        finish = (
            f"5. Push the branch: `git push origin HEAD` (no -u; the repository config is "
            f"read-only to you). Leave the bead open and run, in order: set the stage label, "
            f'`bd set-state {bead} stage=built --reason "ready at <SHA>"`; add a comment, '
            f'`bd comment {bead} "ready at <SHA> on <branch>"`; clear the assignee, '
            f'`bd update {bead} --assignee ""`.'
        )
    else:
        finish = (
            f"5. Close the bead. Write a reason that says what changed, each check you ran "
            f"with its result, and the commit SHA to a file (`mktemp`), then run "
            f"`bd close {bead} --reason-file <file>`."
        )
    return f"""You are the writer for bead {bead}. Your actor is {actor}. BEADS_DIR, BEADS_ACTOR, and BD_ACTOR are already set. Work only in {tree}. Run every step yourself, in order. If a bd or git command exits non-zero and you cannot fix the cause inside {tree}, skip to step 6. A command that exits 0 succeeded, even when it prints a warning such as `Unable to create ... packed-refs.lock`; git prints that one from the sandbox on a good commit.

1. Claim the bead: `bd update {bead} --claim`. If it exits non-zero, another actor holds it. End with the error it printed and run nothing else.
2. Read the scope and the done-when: `bd show {bead}`. Read its NOTES too; a reopened bead keeps the reopen reason there.
3. Do the work in {tree}. The claim's lease expires 5 minutes after the claim or the last heartbeat. Send a heartbeat, `bd heartbeat {bead}`, at least every 3 minutes: before and after each build or test run, and between edits. Run any command that can take longer than 3 minutes as `{heartbeat_loop}`.
4. Commit. End each subject with ` ({bead})` and put the why in the body: `git commit -m "<subject> ({bead})" -m "<why>" --trailer "Executed-By: ${{BD_ACTOR:?}}"`. Put no trailer in the -m text. Leave the working tree clean: `git status --porcelain` prints nothing.
{finish}
6. If you could not finish, write `codex could not finish: <what failed, the command, its error>` to a file and run `bd comment {bead} --file <file>`. Leave the bead claimed.
7. End with a last message of at most five lines: what changed, and the SHA.
"""


def reviewer_prompt(request: Request) -> str:
    bead, sha, tree = request.bead, request.sha, request.worktree
    return f"""You are the reviewer for bead {bead} at commit {sha}. Your actor is {request.actor}. BEADS_DIR and BEADS_ACTOR are already set. Do not edit any file in {tree}.

1. Read the scope and the done-when: `bd show {bead}`.
2. `git -C {shlex.quote(str(tree))} log --grep '({bead})' {sha}` lists the bead's commits. Review their combined diff against the scope and the done-when. Look for wrong behavior, a missed requirement, and a claim the diff does not back. Run read-only checks if they help.
3. Record the verdict. Write a file whose first line is `verdict pass at {sha}` or `verdict fail at {sha}`, followed by the reasons, then run `bd comment {bead} --file <file>`.
4. If you could not review, write `codex could not finish: <what failed>` to a file and run `bd comment {bead} --file <file>`.
"""


def run_script(request: Request, run_dir: Path, beads_dir: Path, layout: GitLayout) -> str:
    q = lambda value: shlex.quote(str(value))
    writer = request.role == "writer"
    cwd = request.worktree if writer else run_dir / "cwd"
    grants = [*(layout.git_grants if writer else ()), beads_dir.parent, *request.grants]
    flags = [
        "-m", model_for(request.role), "-s", "workspace-write",
        "-c", "agents.enabled=false",
        *(["-c", "sandbox_workspace_write.network_access=true"] if writer else ["--skip-git-repo-check"]),
        "-C", cwd,
    ]
    for grant in grants:
        flags += ["--add-dir", grant]
    command = " ".join(q(f) for f in flags)
    return f"""#!/usr/bin/env bash
cd {q(cwd)}
export BEADS_DIR={q(beads_dir)} BEADS_ACTOR={q(request.actor)} BD_ACTOR={q(request.actor)}
codex exec {command} --json -o {q(run_dir / "last-message.md")} - < {q(run_dir / "prompt.md")} > {q(run_dir / "codex.jsonl")} 2> {q(run_dir / "codex.stderr")}
printf '{{"pstack":"{EXIT_MARKER}","code":%d}}\\n' $? >> {q(run_dir / "codex.jsonl")}
"""


def run_dir_for(request: Request) -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return state / "pstack/codex-runs" / request.bead / request.role


def prepare(text: str, beads_env: str | None) -> Path:
    request = parse_request(text)
    run_dir = run_dir_for(request)
    try:
        if not beads_env or not os.path.isabs(beads_env):
            raise Refusal("BEADS_DIR must be set to an absolute path")
        beads_dir = Path(beads_env)
        for grant in request.grants:
            if not grant.exists():
                raise Refusal(f"Grant path does not exist: {grant}")
        layout = read_layout(request.worktree)
        grants = [*(layout.git_grants if request.role == "writer" else ()),
                  beads_dir.parent, *request.grants]
        check_layout(request, layout, tuple(grants))
        check_not_live(run_dir)
    except Refusal as refusal:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "refused.txt").write_text(f"{refusal}\n")
        raise
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "cwd").mkdir(parents=True)
    prompt = writer_prompt(request) if request.role == "writer" else reviewer_prompt(request)
    (run_dir / "prompt.md").write_text(prompt)
    (run_dir / "run.sh").write_text(run_script(request, run_dir, beads_dir, layout))
    return run_dir


def main() -> int:
    try:
        print(prepare(sys.stdin.read(), os.environ.get("BEADS_DIR")))
    except Refusal as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
