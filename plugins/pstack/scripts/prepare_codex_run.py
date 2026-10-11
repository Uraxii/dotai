#!/usr/bin/env python3
"""Build one Codex run from a watcher's spawn prompt.

Usage: prepare_codex_run.py [--launch] < request
BEADS_DIR must be absolute. --launch starts the prepared script detached.

The spawn prompt is one line in one of two forms, read on stdin:

  Claim bead <id> as <actor>. Work in <worktree>.[ Stop at stage=built.][ Grant: <path>...]
  Review bead <id> at <SHA> in <worktree>.[ Grant: <path>...]

Grant paths are absolute, exist, and hold no spaces.
Writer grants become extra --add-dir arguments. Native review stays read-only.
On success the script empties and recreates
`${XDG_STATE_HOME:-~/.local/state}/pstack/codex-runs/<id>/<role>/`, writes
`prompt.md` and `run.sh` there, prints the run dir, and exits 0. `run.sh` runs
`codex exec` (a writer) or `codex review` (a reviewer, which records its output as the bead comment) and appends `{"pstack":"codex exited","code":N}` to `codex.jsonl`.

Exit 2, with the reason on stderr and in `<run dir>/refused.txt` once a bead id
parsed, when the run must not start: the prompt does not parse, BEADS_DIR is
missing or relative, the worktree is not a git worktree, a writer targets a main
checkout, a grant would make the git hooks dir or shared config writable
(the coordinator later runs git outside
the sandbox in that repo), or a run is already live in this run dir.
"""

from __future__ import annotations

import argparse
import fcntl
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
STOP_LINE = "PSTACK_CODEX_STOP"

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


class RunArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise Refusal(message)


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
    if "\n" in line or "\r" in line:
        raise Refusal("the request must be one line")
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
    if any(not p.is_absolute() for p in extra):
        raise Refusal("Grant paths must be absolute")
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


def git(worktree: Path, *args: str, hooks_path: str = "/dev/null") -> str:
    override = ["-c", f"core.hooksPath={hooks_path}"] if hooks_path else []
    result = subprocess.run(
        ["git", *override, "-C", str(worktree), *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise Refusal(f"{worktree} is not a git worktree: {result.stderr.strip()}")
    return result.stdout.strip()


def read_layout(worktree: Path) -> GitLayout:
    def path(*args: str, **kwargs: str) -> Path:
        return Path(git(worktree, "rev-parse", "--path-format=absolute", *args, **kwargs))

    common_dir = path("--git-common-dir")
    hooks_dirs = (common_dir / "hooks", path("--git-path", "hooks", hooks_path=""))
    return GitLayout(git_dir=path("--git-dir"), common_dir=common_dir, hooks_dirs=hooks_dirs)


def resolved_grants(request: Request, layout: GitLayout, beads_dir: Path) -> tuple[Path, ...]:
    grants = [*(layout.git_grants if request.role == "writer" else ()),
              beads_dir.parent, *request.grants]
    return tuple(grant.resolve() for grant in grants)


def check_layout(request: Request, layout: GitLayout, grants: tuple[Path, ...]) -> None:
    if request.role == "writer" and layout.git_dir == layout.common_dir:
        raise Refusal(
            f"{layout.git_dir} is a main checkout's git dir; run Codex in a linked "
            "worktree",
        )
    roots = (*grants, request.worktree.resolve()) if request.role == "writer" else grants
    for protected in (*layout.hooks_dirs, *layout.config_files):
        protected = protected.resolve()
        for root in roots:
            if protected.is_relative_to(root) or root.is_relative_to(protected):
                raise Refusal(f"{root} would make {protected} writable")


def ere_escape(text: str) -> str:
    return re.sub(r"([.\[\]()*+?{}|^$\\])", r"\\\1", text)


def is_live(run_dir: Path) -> bool:
    pattern = f"^bash {ere_escape(str(run_dir))}/run\\.sh$"
    code = subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode
    if code not in (0, 1):
        raise Refusal(f"pgrep failed with exit code {code}")
    return code == 0


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
            f"5. If commits and pushes are permitted by the scope and notes, push with "
            f"`git push origin HEAD` (no -u; the repository config is "
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

Scope and notes control the finish steps. If they say Do not push, run no push command. If the scope forbids commits, use the starting HEAD as the reported SHA and leave Git unchanged. Apply these conditions before steps 4 and 5.

1. Claim the bead: `bd update {bead} --claim`. If it exits non-zero, another actor holds it. End with the error it printed and run nothing else.
2. Read the scope and the done-when: `bd show {bead}`. Read its NOTES too; a reopened bead keeps the reopen reason there. Read `bd comments {bead}`. Before any work, record the starting HEAD and Git status for the scope checks at finish. If the last `verdict fail at <SHA>` or `tests fail at <SHA>` comment is newer than any pass, this is a fix round: fix each must-fix item and each failing test, never weaken or delete a test the tester committed (if a test is wrong, say why in a comment and leave it for the reviewer), and fix each should-fix-or-explain item or answer it with a comment line `answered: <item>: <reason>` (`bd comment {bead} --file <file>`).
3. Follow the bead's test policy and the existing project checks. Do the work in {tree}. The claim's lease expires 5 minutes after the claim or the last heartbeat. Send a heartbeat, `bd heartbeat {bead}`, at least every 3 minutes: before and after each build or test run, and between edits. Run any command that can take longer than 3 minutes as `{heartbeat_loop}`.
4. If the scope forbids commits, create only the requested external artifacts. Report the starting HEAD. Check that HEAD and the worktree are unchanged. Otherwise, commit the scoped work. Write the subject as a Conventional Commit, `<type>(<scope>): <description>`, and put the why in the body: `git commit -m "<type>(<scope>): <description>" -m "<why>"`. Leave the working tree clean: `git status --porcelain` prints nothing.
{finish}
6. If you could not finish, write `codex could not finish: <what failed, the command, its error>` to a file and run `bd comment {bead} --file <file>`. Leave the bead claimed.
7. End with a last message of at most five lines: what changed, and the SHA.
"""


def reviewer_prompt(request: Request) -> str:
    bead, sha = request.bead, request.sha
    return f"""You are the reviewer for bead {bead} at commit {sha}. Do not edit any file.

1. Review `git diff <base>..{sha}` against the scope and the done-when of the bead. They are in the bead text appended below this brief. `<base>` is `{sha}^` unless that text names an earlier base for the bead's commits. Run read-only checks if they help.
2. The appended bead comments hold the earlier rounds. The last failed round is the most recent `verdict fail at <old SHA>` or `tests fail at <old SHA>`; each failing test in a tester failure is one must-fix item. If there is one, check each of its items at {sha}, check that no test the tester committed was weakened or deleted without a reason you accept, and read `git diff <old SHA>..{sha}` closely, because those commits are the fixes. Step 1 still covers the full diff, because a fix can break code an earlier round passed.
3. Read `{PLUGIN_ROOT / "skills" / "principle-skeptical-review" / "SKILL.md"}` and judge the diff by it. The diff is an `architect` sketch or code. Put each finding in one of its tiers: Must-fix, Should-fix-or-explain, or Worth-noting.
4. Report each Must-fix and each Should-fix-or-explain finding as a native review finding, and begin its body with its tier word and a period, for example `Must-fix. <why>`. Leave Worth-noting items in the summary. Mark each item from the last failed round `fixed`, `answered: <reason>`, or `still open`; a `still open` item is a Must-fix finding. End the native review summary with a line containing exactly PSTACK_REVIEW_COMPLETE. This marks a complete review. The recorded verdict line is added from your findings: `verdict fail at {sha}` when any finding begins `Must-fix.`, otherwise `verdict pass at {sha}`.
"""


def run_script(request: Request, run_dir: Path, beads_dir: Path, grants: tuple[Path, ...]) -> str:
    q = lambda value: shlex.quote(str(value))
    env = f"export BEADS_DIR={q(beads_dir)} BEADS_ACTOR={q(request.actor)} BD_ACTOR={q(request.actor)}"
    done = lambda code: f"""printf '{{"pstack":"{EXIT_MARKER}","code":%d}}\\n' {code} >> {q(run_dir / "codex.jsonl")}"""
    if request.role == "reviewer":
        bead, tree, review = request.bead, request.worktree, run_dir / "review.md"
        stderr, context = q(run_dir / "codex.stderr"), q(run_dir / "context.md")
        return f"""#!/usr/bin/env bash
{env}
review() {{
  cd {q(tree)} || return 1
  [ "$(git rev-parse --verify -q {q(request.sha)}^{{commit}})" = "$(git rev-parse HEAD)" ] || return 1
  {{ cat {q(run_dir / "prompt.md")} && bd show {q(bead)} && bd comments {q(bead)}; }} > {context} 2> {stderr} || return 1
  codex review -c model={q(model_for("reviewer"))} -c sandbox_mode=read-only - < {context} > {q(run_dir / "native.md")} 2>> {stderr} || return $?
  grep -q '^PSTACK_REVIEW_COMPLETE$' {q(run_dir / "native.md")} || return 1
  priorities=$(grep -cE '\\[P[0-3]\\]' {q(run_dir / "native.md")})
  tiers=$(grep -cE '(Must-fix|Should-fix-or-explain)[.]' {q(run_dir / "native.md")})
  [ "$priorities" -le "$tiers" ] || return 1
  verdict=pass
  grep -qE '(^|[[:space:]*-])Must-fix[.]' {q(run_dir / "native.md")} && verdict=fail
  {{ echo "verdict $verdict at {request.sha}"; echo; cat {q(run_dir / "native.md")}; }} > {q(review)}
}}
review
code=$?
[ $code -eq 0 ] || {{ echo "codex could not finish: HEAD is not {request.sha}, the bead text did not load, or codex review failed"; tail -n 20 {stderr}; }} > {q(review)}
bd comment {q(bead)} --file {q(review)} || code=1
{done("$code")}
exit "$code"
"""
    flags = [
        "-m", model_for(request.role), "-s", "workspace-write",
        "-c", "agents.enabled=false",
        "-c", "sandbox_workspace_write.network_access=true",
        "-C", request.worktree,
    ]
    for grant in grants:
        flags += ["--add-dir", grant]
    command = " ".join(q(f) for f in flags)
    return f"""#!/usr/bin/env bash
{env}
if cd {q(request.worktree)}; then
  codex exec {command} --json -o {q(run_dir / "last-message.md")} - < {q(run_dir / "prompt.md")} > {q(run_dir / "codex.jsonl")} 2> {q(run_dir / "codex.stderr")}
  code=$?
else
  code=$?
fi
{done("$code")}
exit "$code"
"""


def run_dir_for(request: Request) -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    if not state.is_absolute():
        raise Refusal("XDG_STATE_HOME must be absolute")
    return state / "pstack/codex-runs" / request.bead / request.role


def prepare_request(request: Request, beads_env: str | None) -> Path:
    run_dir = run_dir_for(request)
    live = is_live(run_dir)
    if live:
        raise Refusal(f"a Codex run is already live in {run_dir}")
    try:
        review_skill = PLUGIN_ROOT / "skills/principle-skeptical-review/SKILL.md"
        if request.role == "reviewer" and not review_skill.is_file():
            raise Refusal(f"required review skill is missing: {review_skill}")
        if not beads_env or not os.path.isabs(beads_env):
            raise Refusal("BEADS_DIR must be set to an absolute path")
        beads_dir = Path(beads_env)
        for grant in request.grants:
            if not grant.exists():
                raise Refusal(f"Grant path does not exist: {grant}")
        layout = read_layout(request.worktree)
        grants = resolved_grants(request, layout, beads_dir)
        check_layout(request, layout, grants)
    except Refusal as refusal:
        if not live:
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "refused.txt").write_text(f"{refusal}\n")
        raise
    script = run_script(request, run_dir, beads_dir, grants)
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "cwd").mkdir(parents=True)
    prompt = writer_prompt(request) if request.role == "writer" else reviewer_prompt(request)
    (run_dir / "prompt.md").write_text(prompt)
    (run_dir / "run.sh").write_text(script)
    return run_dir


def prepare(text: str, beads_env: str | None, launch: bool = False) -> Path:
    request = parse_request(text)
    run_dir = run_dir_for(request)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    lock_path = run_dir.parent / f".{request.role}.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        run_dir = prepare_request(request, beads_env)
        if launch:
            with (run_dir / "launch.stderr").open("w") as stderr:
                subprocess.Popen(
                    ["bash", str(run_dir / "run.sh")],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=stderr, start_new_session=True,
                )
    return run_dir


def main() -> int:
    parser = RunArgumentParser(description=__doc__)
    parser.add_argument("--launch", action="store_true")
    try:
        args = parser.parse_args()
        if args.launch and not shutil.which("codex"):
            raise Refusal("codex is not on PATH")
        run_dir = prepare(sys.stdin.read(), os.environ.get("BEADS_DIR"), args.launch)
        print(run_dir)
    except Exception as refusal:
        print(STOP_LINE)
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
