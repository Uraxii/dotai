#!/usr/bin/env python3
"""Run one poteto-agent brief as a Codex session (`codex exec`) on GPT.

Picks the model from `models.json`'s codex row for the target agent
(`developer-codex` or `reviewer-codex`, or any explicit role label), builds
the poteto-agent prompt (preamble plus the brief verbatim), calls
`codex exec`, and prints Codex's final message to stdout. Non-zero exit on
`codex` failure, with its stderr tail printed to stderr.

See playbooks/delegate-to-codex.md for when and how to use this.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

__all__ = ["main", "pick_model", "build_prompt", "build_command", "run_relay"]

STDERR_TAIL_LINES = 40

# developer-codex and reviewer-codex are the two named Claude-side agents
# that follow the delegate-to-codex playbook (see poteto-mode SKILL.md's
# agent roster). Their model row and sandbox are fixed by that contract.
AGENT_DEFAULTS: dict[str, dict[str, str]] = {
    "developer-codex": {
        "role": "feature, refactoring",
        "sandbox": "workspace-write",
    },
    "reviewer-codex": {
        "role": "judgment and prose",
        "sandbox": "read-only",
    },
}


class RelayError(Exception):
    """A brief, a model row, or a codex invocation could not be resolved."""


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def pick_model(models_path: Path, role_label: str) -> str:
    """Return the first codex slug models.json lists for role_label."""
    data = json.loads(models_path.read_text())
    panels = data.get("panels", {})
    for row in data["roles"]:
        if row["role"] != role_label:
            continue
        models = row["models"]
        if isinstance(models, str):
            models = panels[models]
        slugs = models.get("codex", [])
        if not slugs:
            raise RelayError(
                f"role {role_label!r} has no codex models in {models_path}"
            )
        return slugs[0]
    raise RelayError(f"no role {role_label!r} in {models_path}")


def build_prompt(brief_text: str, skill_path: Path) -> str:
    """Poteto-agent preamble (pointed at skill_path, not the skill name,
    since pstack-nikki's poteto-mode may not be installed in Codex) plus
    the brief verbatim.
    """
    preamble = (
        "You are operating as poteto-mode's full agent style. Read the "
        f"poteto-mode skill at {skill_path} in full before doing any work, "
        "including its inline Principles index. Navigate to a leaf "
        "`principle-*` skill whenever you apply that principle."
    )
    return f"{preamble}\n\n{brief_text}"


def build_command(
    *,
    codex_bin: str,
    model: str,
    sandbox: str,
    cwd: Path,
    prompt: str,
    output_file: Path,
    add_dirs: list[str],
    skip_git_repo_check: bool,
    reasoning_effort: str | None,
) -> list[str]:
    cmd = [codex_bin, "exec", "-m", model, "-s", sandbox, "-C", str(cwd)]
    for add_dir in add_dirs:
        cmd += ["--add-dir", add_dir]
    if skip_git_repo_check:
        cmd.append("--skip-git-repo-check")
    if reasoning_effort:
        cmd += ["-c", f"model_reasoning_effort={reasoning_effort}"]
    cmd += ["-o", str(output_file), prompt]
    return cmd


def resolve_role_and_sandbox(args: argparse.Namespace) -> tuple[str, str]:
    if args.agent:
        defaults = AGENT_DEFAULTS[args.agent]
        return defaults["role"], args.sandbox or defaults["sandbox"]
    if not args.sandbox:
        raise RelayError(
            "--sandbox is required when --role is used without --agent"
        )
    return args.role, args.sandbox


def read_brief(brief_file: str) -> str:
    if brief_file == "-":
        return sys.stdin.read()
    return Path(brief_file).read_text()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--agent", choices=sorted(AGENT_DEFAULTS))
    target.add_argument("--role", help="models.json role label, verbatim")
    parser.add_argument(
        "--brief-file", required=True, help="path, or - for stdin"
    )
    parser.add_argument(
        "--cwd", required=True, help="worktree or checkout codex runs in"
    )
    parser.add_argument(
        "--sandbox",
        choices=["read-only", "workspace-write", "danger-full-access"],
    )
    parser.add_argument("--model", help="override the models.json lookup")
    parser.add_argument(
        "--models-json", help="default: plugin_root/models.json"
    )
    parser.add_argument(
        "--skill-path",
        help="default: plugin_root/skills/poteto-mode/SKILL.md",
    )
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--add-dir", action="append", default=[], dest="add_dirs")
    parser.add_argument("--skip-git-repo-check", action="store_true")
    parser.add_argument("--reasoning-effort")
    return parser.parse_args(argv)


Runner = Callable[..., subprocess.CompletedProcess]


def run_relay(args: argparse.Namespace, run: Runner = subprocess.run) -> int:
    root = plugin_root()
    role, sandbox = resolve_role_and_sandbox(args)
    models_path = (
        Path(args.models_json) if args.models_json else root / "models.json"
    )
    skill_path = (
        Path(args.skill_path)
        if args.skill_path
        else root / "skills" / "poteto-mode" / "SKILL.md"
    )
    model = args.model or pick_model(models_path, role)
    brief_text = read_brief(args.brief_file)
    prompt = build_prompt(brief_text, skill_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = Path(tmp_dir) / "codex-last-message.txt"
        cmd = build_command(
            codex_bin=args.codex_bin,
            model=model,
            sandbox=sandbox,
            cwd=Path(args.cwd),
            prompt=prompt,
            output_file=output_file,
            add_dirs=args.add_dirs,
            skip_git_repo_check=args.skip_git_repo_check,
            reasoning_effort=args.reasoning_effort,
        )
        completed = run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            tail_lines = completed.stderr.splitlines()[-STDERR_TAIL_LINES:]
            print(
                f"codex exec failed (exit {completed.returncode}):",
                file=sys.stderr,
            )
            print("\n".join(tail_lines), file=sys.stderr)
            return completed.returncode
        print(output_file.read_text())
        return 0


def main(argv: list[str] | None = None, run: Runner = subprocess.run) -> int:
    try:
        args = parse_args(argv)
        return run_relay(args, run=run)
    except RelayError as error:
        print(f"codex_relay: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
