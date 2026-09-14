#!/usr/bin/env python3
"""Validate plugins/pstack-nikki/skills: links resolve inside the tree, and
every SKILL.md frontmatter names its own directory and carries a
description."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


__all__ = ["main", "validate_skills_tree"]

LINK_RE = re.compile(r"\]\(([^)\n]*)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def strip_fenced_code(text: str) -> str:
    # Replace fenced content with a same-length run of newlines so line
    # numbers in reported problems still point at the right source line.
    return FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def link_targets(text: str) -> list[str]:
    targets = []
    for match in LINK_RE.finditer(strip_fenced_code(text)):
        raw = match.group(1).strip()
        if raw.startswith("<"):
            end = raw.find(">")
            raw = raw[1:end] if end != -1 else raw[1:]
        targets.append(raw.split()[0] if raw.split() else raw)
    return targets


def path_is_inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def link_problems(skills_dir: Path) -> list[str]:
    root = skills_dir.resolve()
    problems = []
    for path in sorted(root.rglob("*.md")):
        for target in link_targets(path.read_text()):
            if not target or target.startswith("#"):
                continue
            scheme = re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target)
            if scheme:
                continue
            encoded = target.split("?")[0].split("#")[0]
            if not encoded:
                continue
            decoded = unquote(encoded)
            resolved = (path.parent / decoded).resolve()
            if Path(decoded).is_absolute() or not path_is_inside(root, resolved):
                problems.append(f"{path.relative_to(root)} -> {target} (escapes skills tree)")
            elif not resolved.exists():
                problems.append(f"{path.relative_to(root)} -> {target} (missing)")
    return problems


def frontmatter_value(text: str, key: str) -> str | None:
    block = FRONTMATTER_RE.match(text)
    if not block:
        return None
    for line in block.group(1).split("\n"):
        if line.startswith(f"{key}: "):
            return line[len(key) + 2 :]
    return None


def skill_metadata_problems(skills_dir: Path) -> list[str]:
    problems = []
    for entry in sorted(skills_dir.iterdir()):
        skill_md = entry / "SKILL.md"
        if not entry.is_dir() or not skill_md.exists():
            continue
        text = skill_md.read_text()
        name = frontmatter_value(text, "name")
        if name != entry.name:
            problems.append(
                f'{entry.name}/SKILL.md: frontmatter name "{name}" '
                f'!= directory "{entry.name}"'
            )
        description = frontmatter_value(text, "description")
        if not description:
            problems.append(f"{entry.name}/SKILL.md: no description frontmatter")
    return problems


def validate_skills_tree(skills_dir: Path) -> list[str]:
    return link_problems(skills_dir) + skill_metadata_problems(skills_dir)


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    default_dir = Path(__file__).resolve().parents[3] / "skills"
    skills_dir = Path(arguments[0]) if arguments else default_dir
    problems = validate_skills_tree(skills_dir)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print(f"ok: {skills_dir} links resolve and every SKILL.md is named right")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
