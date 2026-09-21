#!/usr/bin/env python3
"""Validate plugins/pstack/skills: links resolve inside the tree, skill
names cited in bold or backticks resolve to a skill directory, and every
SKILL.md frontmatter names its own directory and carries a description.

Deleting a skill is what leaves a dead reference behind, so the names git has
carried under this directory decide which emphasised words are skill names."""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote


__all__ = ["main", "validate_skills_tree"]

LINK_RE = re.compile(r"\]\(([^)\n]*)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# Skills are cited as **name** or `name`, never as markdown links.
EMPHASIS_RE = re.compile(r"\*\*([^*\n]+)\*\*|`([^`\n]+)`")
SKILL_FRAME_RE = re.compile(r"(?:\*\*([^*\n]+)\*\*|`([^`\n]+)`)\s+skill\b")
SKILL_NAME_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+")

# Skills that ship with the harness or another plugin, including two this
# plugin dropped but upstream still carries, so they are named here on purpose
# but never resolve inside this tree.
EXTERNAL_SKILLS = frozenset(
    {
        "babysit",
        "bro",
        "databricks-use-dbt-models",
        "loop",
        "recall",
        "teach",
        "verify",
        "writing-skills",
    }
)


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


def skill_names(skills_dir: Path) -> set[str]:
    return {
        entry.name
        for entry in skills_dir.iterdir()
        if entry.is_dir() and (entry / "SKILL.md").exists()
    }


def skill_families(names: set[str]) -> set[str]:
    # A prefix shared by two or more real skill directories, such as
    # "principle", marks a naming family. A hyphenated token in that family
    # is a skill reference; "read-only" and other hyphenated prose is not.
    prefixes = Counter(name.split("-")[0] for name in names if "-" in name)
    return {prefix for prefix, count in prefixes.items() if count >= 2}


def skill_names_in_history(skills_dir: Path) -> set[str]:
    """Every name that held a SKILL.md in this directory at any commit.

    "Answer in **caveman** register" reads as prose until you know caveman was
    a skill here, which is why this set, and not the shape of the word, is what
    exposes a stale reference in every citation syntax.

    Returns nothing when git cannot answer, as in a shallow clone or outside a
    checkout. The remaining rules still apply.
    """
    try:
        listing = subprocess.run(
            ["git", "log", "--all", "--format=", "--name-only", "--relative", "--", "."],
            cwd=skills_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {
        path.split("/")[0]
        for path in listing.split("\n")
        if path.endswith("/SKILL.md") and path.count("/") == 1
    }


def referenced_skills(text: str, families: set[str], historical: set[str]) -> set[str]:
    body = strip_fenced_code(text)
    references = set()
    for match in EMPHASIS_RE.finditer(body):
        token = (match.group(1) or match.group(2)).strip()
        if token in historical:
            references.add(token)
        elif SKILL_NAME_RE.fullmatch(token) and token.split("-")[0] in families:
            references.add(token)
    for match in SKILL_FRAME_RE.finditer(body):
        token = (match.group(1) or match.group(2)).strip()
        if ":" in token or "*" in token:
            continue
        if re.fullmatch(r"[a-z][a-z0-9-]*", token):
            references.add(token)
    return references - EXTERNAL_SKILLS


def documents_naming_skills(skills_dir: Path) -> list[Path]:
    documents = list(skills_dir.rglob("*.md"))
    agents_dir = skills_dir.parent / "agents"
    if agents_dir.is_dir():
        documents.extend(agents_dir.rglob("*.md"))
    return sorted(documents)


def skill_reference_problems(skills_dir: Path) -> list[str]:
    root = skills_dir.resolve()
    names = skill_names(root)
    families = skill_families(names)
    historical = skill_names_in_history(root) - EXTERNAL_SKILLS
    problems = []
    for path in documents_naming_skills(root):
        inside = path_is_inside(root, path)
        label = path.relative_to(root if inside else root.parent)
        for reference in sorted(referenced_skills(path.read_text(), families, historical)):
            if reference not in names:
                problems.append(f"{label} -> **{reference}** (no such skill directory)")
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
    return (
        link_problems(skills_dir)
        + skill_reference_problems(skills_dir)
        + skill_metadata_problems(skills_dir)
    )


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    default_dir = Path(__file__).resolve().parents[1] / "plugins" / "pstack" / "skills"
    skills_dir = Path(arguments[0]) if arguments else default_dir
    problems = validate_skills_tree(skills_dir)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print(f"ok: {skills_dir} links and skill references resolve, every SKILL.md is named right")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
